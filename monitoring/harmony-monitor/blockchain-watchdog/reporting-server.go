package main

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"html/template"
	"net"
	"net/http"
	"reflect"
	"strconv"
	"sync"
	"time"

	"github.com/ahmetb/go-linq"
	"github.com/valyala/fasthttp"
)

const (
	badVersionString   = "BAD_VERSION_STRING"
	versionJSONRPC     = "2.0"
	blocksPerEpoch     = 16384
	blockTime          = time.Second * 15 // Come back to this
	metadataRPC        = "hmy_getNodeMetadata"
	blockHeaderRPC     = "hmy_latestHeader"
	blockHeaderReport  = "block-header"
	nodeMetadataReport = "node-metadata"
)

type nodeMetadata struct {
	BLSPublicKey string `json:"blskey"`
	Version      string `json:"version"`
	NetworkType  string `json:"network"`
	ChainID      string `json:"chainid"`
	IsLeader     bool   `json:"is-leader"`
	ShardID      uint32 `json:"shard-id"`
}

type headerInformation struct {
	BlockHash        string `json:"blockHash"`
	BlockNumber      uint64 `json:"blockNumber"`
	ShardID          uint32 `json:"shardID"`
	Leader           string `json:"leader"`
	ViewID           uint64 `json:"viewID"`
	Epoch            uint64 `json:"epoch"`
	Timestamp        string `json:"timestamp"`
	UnixTime         int64  `json:"unixtime"`
	LastCommitSig    string `json:"lastCommitSig"`
	LastCommitBitmap string `json:"lastCommitBitmap"`
}

type any map[string]interface{}

var (
	buildVersion               = versionS()
	queryID                    = 0
	nodeMetadataCSVHeader      = []string{"IP"}
	headerInformationCSVHeader = []string{"IP"}
	post                       = []byte("POST")
	client                     fasthttp.Client
)

func identity(x interface{}) interface{} {
	return x
}

const (
	metaSumry   = "node-metadata"
	headerSumry = "block-header"
	blockMax    = "block-max"
	timestamp   = "timestamp"
)

func init() {
	h := reflect.TypeOf((*headerInformation)(nil)).Elem()
	n := reflect.TypeOf((*nodeMetadata)(nil)).Elem()
	for i := 0; i < h.NumField(); i++ {
		headerInformationCSVHeader = append(headerInformationCSVHeader, h.Field(i).Name)
	}
	for i := 0; i < n.NumField(); i++ {
		nodeMetadataCSVHeader = append(nodeMetadataCSVHeader, n.Field(i).Name)
	}
}

func blockHeaderSummary(
	headers []headerInfoRPCResult,
	includeRecords bool,
	sum map[string]interface{},
) {
	linq.From(headers).GroupBy(
		// Group by ShardID
		func(node interface{}) interface{} { return node.(headerInfoRPCResult).Payload.ShardID },
		identity,
	).ForEach(func(value interface{}) {
		shardID := strconv.FormatUint(uint64(value.(linq.Group).Key.(uint32)), 10)
		block := linq.From(value.(linq.Group).Group).Select(func(c interface{}) interface{} {
			return c.(headerInfoRPCResult).Payload.BlockNumber
		})
		epoch := linq.From(value.(linq.Group).Group).Select(func(c interface{}) interface{} {
			return c.(headerInfoRPCResult).Payload.Epoch
		})
		uniqEpochs := []uint64{}
		uniqBlockNums := []uint64{}
		epoch.Distinct().ToSlice(&uniqEpochs)
		block.Distinct().ToSlice(&uniqBlockNums)
		sum[shardID] = any{
			"block-min":   block.Min(),
			blockMax:      block.Max(),
			"epoch-min":   epoch.Min(),
			"epoch-max":   epoch.Max(),
			"uniq-epochs": uniqEpochs,
			"uniq-blocks": uniqBlockNums,
		}
		if includeRecords {
			sum[shardID].(any)["records"] = value.(linq.Group).Group
			sum[shardID].(any)["latest-block"] = linq.From(value.(linq.Group).Group).FirstWith(func(c interface{}) bool {
				return c.(headerInfoRPCResult).Payload.BlockNumber == block.Max()
			})
		}
	})
}

type summary map[string]map[string]interface{}

// WARN Be careful, usage of interface{} can make things explode in the goroutine with bad cast
func summaryMaps(metas []metadataRPCResult, headers []headerInfoRPCResult) summary {
	sum := summary{metaSumry: map[string]interface{}{}, headerSumry: map[string]interface{}{}}
	for i, n := range headers {
		if s := n.Payload.LastCommitSig; len(s) > 0 {
			shorted := s[:5] + "..." + s[len(s)-5:]
			headers[i].Payload.LastCommitSig = shorted
		}
	}

	linq.From(metas).GroupBy(
		func(node interface{}) interface{} { return parseVersionS(node.(metadataRPCResult).Payload.Version) }, identity,
	).ForEach(func(value interface{}) {
		vrs := value.(linq.Group).Key.(string)
		sum[metaSumry][vrs] = map[string]interface{}{"records": value.(linq.Group).Group}
	})
	blockHeaderSummary(headers, true, sum[headerSumry])
	return sum
}

func request(node string, requestBody []byte) ([]byte, []byte, error) {
	const contentType = "application/json"
	req := fasthttp.AcquireRequest()
	req.SetBody(requestBody)
	req.Header.SetMethodBytes(post)
	req.Header.SetContentType(contentType)
	req.SetRequestURIBytes([]byte(node))
	res := fasthttp.AcquireResponse()
	if err := client.Do(req, res); err != nil {
		return nil, requestBody, err
	}
	c := res.StatusCode()
	if c != 200 {
		return nil, requestBody, fmt.Errorf("http status code not 200, received: %d", c)
	}
	fasthttp.ReleaseRequest(req)
	body := res.Body()
	if len(body) == 0 {
		return nil, requestBody, fmt.Errorf("empty reply received")
	}
	result := make([]byte, len(body))
	copy(result, body)
	fasthttp.ReleaseResponse(res)
	return result, nil, nil
}

func (m *monitor) renderReport(w http.ResponseWriter, req *http.Request) {
	t, e := template.New("report").Parse(reportPage())
	if e != nil {
		fmt.Println(e)
		http.Error(w, "could not generate page:"+e.Error(), http.StatusInternalServerError)
		return
	}
	type v struct {
		LeftTitle, RightTitle []interface{}
		Summary               interface{}
		NoReply               []noReply
		DownMachineCount      int
	}
	report := m.networkSnapshot()
	cnsMsg := "Consensus Progress not known yet"
	if len(report.ConsensusProgress) != 0 {
		cM, _ := json.Marshal(m.consensusProgress)
		cnsMsg = fmt.Sprintf("Consensus Progress: %s", cM)
	}
	t.ExecuteTemplate(w, "report", v{
		LeftTitle:  []interface{}{report.Chain, cnsMsg},
		RightTitle: []interface{}{report.Build, time.Now().Format(time.RFC3339)},
		Summary:    report.Summary,
		NoReply:    report.NoReplies,
		DownMachineCount: linq.From(report.NoReplies).Select(
			func(c interface{}) interface{} { return c.(noReply).IP },
		).Distinct().Count(),
	})
	m.use()
	m.summaryCopy(report.Summary)
	m.NoReplySnapshot = append([]noReply{}, report.NoReplies...)
	m.done()
}

func (m *monitor) produceCSV(w http.ResponseWriter, req *http.Request) {
	filename := ""
	records := [][]string{}
	switch keys, ok := req.URL.Query()["report"]; ok {
	case true:
		switch report := keys[0]; report {
		case blockHeaderReport:
			filename = blockHeaderReport + ".csv"
			records = append(records, headerInformationCSVHeader)

			shard, ex := req.URL.Query()["shard"]
			if !ex {
				http.Error(w, "shard not chosen in query param", http.StatusBadRequest)
				return
			}
			m.use()
			records := m.SummarySnapshot[headerSumry][shard[0]].(any)["records"].([]interface{})
			for _, v := range records {
				row := []string{
					v.(headerInfoRPCResult).IP,
					v.(headerInfoRPCResult).Payload.BlockHash,
					strconv.FormatUint(v.(headerInfoRPCResult).Payload.BlockNumber, 10),
					shard[0],
					v.(headerInfoRPCResult).Payload.Leader,
					strconv.FormatUint(v.(headerInfoRPCResult).Payload.ViewID, 10),
					strconv.FormatUint(v.(headerInfoRPCResult).Payload.Epoch, 10),
					v.(headerInfoRPCResult).Payload.Timestamp,
					strconv.FormatInt(v.(headerInfoRPCResult).Payload.UnixTime, 10),
					v.(headerInfoRPCResult).Payload.LastCommitSig,
					v.(headerInfoRPCResult).Payload.LastCommitBitmap,
				}
				records = append(records, row)
			}
			m.done()
		case nodeMetadataReport:
			filename = nodeMetadataReport + ".csv"
			records = append(records, nodeMetadataCSVHeader)

			vrs, ex := req.URL.Query()["vrs"]
			if !ex {
				http.Error(w, "version not chosen in query param", http.StatusBadRequest)
				return
			}
			m.use()
			// FIXME: Bandaid
			if m.SummarySnapshot[metaSumry][vrs[0]] != nil {
				recs := m.SummarySnapshot[metaSumry][vrs[0]].(map[string]interface{})["records"].([]interface{})
				for _, v := range recs {
					row := []string{
						v.(metadataRPCResult).IP,
						v.(metadataRPCResult).Payload.BLSPublicKey,
						v.(metadataRPCResult).Payload.Version,
						v.(metadataRPCResult).Payload.NetworkType,
						v.(metadataRPCResult).Payload.ChainID,
						strconv.FormatBool(v.(metadataRPCResult).Payload.IsLeader),
						strconv.FormatUint(uint64(v.(metadataRPCResult).Payload.ShardID), 10),
					}
					records = append(records, row)
				}
			}
			m.done()
		}
	default:
		http.Error(w, "report not chosen in query param", http.StatusBadRequest)
		return
	}
	w.Header().Set("Content-Type", "text/csv")
	w.Header().Set("Content-Disposition", "attachment;filename="+filename)
	wr := csv.NewWriter(w)
	err := wr.WriteAll(records)
	if err != nil {
		http.Error(w, "Error sending csv: "+err.Error(), http.StatusInternalServerError)
	}
}

func (m *monitor) use() {
	m.inUse.Wait()
	m.inUse.Add(1)
}

func (m *monitor) done() {
	m.inUse.Done()
}

func (m *monitor) summaryCopy(newData map[string]map[string]interface{}) {
	m.SummarySnapshot = make(map[string]map[string]interface{})
	for key, value := range newData {
		m.SummarySnapshot[key] = make(map[string]interface{})
		for k, v := range value {
			m.SummarySnapshot[key][k] = v
		}
	}
}

func (m *monitor) metadataCopy(newData MetadataContainer) {
	m.MetadataSnapshot.TS = newData.TS
	m.MetadataSnapshot.Nodes = append([]metadataRPCResult{}, newData.Nodes...)
	m.MetadataSnapshot.Down = append([]noReply{}, newData.Down...)
}

func (m *monitor) blockHeaderCopy(newData BlockHeaderContainer) {
	m.BlockHeaderSnapshot.TS = newData.TS
	m.BlockHeaderSnapshot.Nodes = append([]headerInfoRPCResult{}, newData.Nodes...)
	m.BlockHeaderSnapshot.Down = append([]noReply{}, newData.Down...)
}

type metadataRPCResult struct {
	Payload nodeMetadata
	IP      string
}

type headerInfoRPCResult struct {
	Payload headerInformation
	IP      string
}

type noReply struct {
	IP            string
	FailureReason string
	RPCPayload    string
}

type MetadataContainer struct {
	TS    time.Time
	Nodes []metadataRPCResult
	Down  []noReply
}

type BlockHeaderContainer struct {
	TS    time.Time
	Nodes []headerInfoRPCResult
	Down  []noReply
}

type monitor struct {
	chain               string
	inUse               sync.WaitGroup
	WorkingMetadata     MetadataContainer
	WorkingBlockHeader  BlockHeaderContainer
	MetadataSnapshot    MetadataContainer
	BlockHeaderSnapshot BlockHeaderContainer
	SummarySnapshot     map[string]map[string]interface{}
	NoReplySnapshot     []noReply
	consensusProgress   map[string]bool
}

type work struct {
	address string
	rpc     string
	body    []byte
}

type reply struct {
	address    string
	rpc        string
	rpcPayload []byte
	rpcResult  []byte
	oops       error
}

func (m *monitor) worker(
	jobs chan work, channels map[string](chan reply), groups map[string]*sync.WaitGroup,
) {
	for j := range jobs {
		result := reply{address: j.address, rpc: j.rpc}
		result.rpcResult, result.rpcPayload, result.oops = request(
			"http://"+j.address, j.body)
		channels[j.rpc] <- result
		groups[j.rpc].Done()
	}
}

func (m *monitor) shardMonitor(
	ready chan bool, warning, redline int, pdServiceKey, chain string,
) {
	type a struct {
		blockHeight uint64
		timeStamp   time.Time
		warningSent bool
		lastRedline time.Time
	}
	// https://golang.org/pkg/time/#Time.Format
	timeFormat := "15:04:05 Jan _2 MST"
	lastSuccess := make(map[string]a)
	for range ready {
		current := any{}
		m.use()
		blockHeaderSummary(m.BlockHeaderSnapshot.Nodes, true, current)
		currTime := m.BlockHeaderSnapshot.TS
		m.done()
		for s, curr := range current {
			progress := true
			currHeight := curr.(any)[blockMax].(uint64)
			if last, exists := lastSuccess[s]; exists {
				if !(currHeight > last.blockHeight) {
					elapsedTime := int64(currTime.Sub(last.timeStamp).Seconds())
					name := fmt.Sprintf(nameFMT, chain)
					header := curr.(any)["latest-block"].(headerInfoRPCResult)
					message := fmt.Sprintf(`
Liviness problem on shard %s

Block height stuck at %d starting at %s

Block Hash: %s

Leader: %s

ViewID: %d

Epoch: %d

Block Timestamp: %s

LastCommitSig: %s

LastCommitBitmap: %s

Time since last new block: %d seconds (%f minutes)

See: http://watchdog.hmny.io/report-%s

--%s
`, s, currHeight, last.timeStamp.Format(timeFormat),
						header.Payload.BlockHash, header.Payload.Leader, header.Payload.ViewID,
						header.Payload.Epoch, header.Payload.Timestamp, header.Payload.LastCommitSig,
						header.Payload.LastCommitBitmap, elapsedTime,
						currTime.Sub(last.timeStamp).Minutes(), chain, name,
					)
					if elapsedTime > int64(warning) {
						progress = false
					}
					if elapsedTime > int64(warning) && !last.warningSent {
						notify(pdServiceKey, message)
						lastSuccess[s] = a{currHeight, last.timeStamp, true, time.Time{}}
						progress = false
					} else if elapsedTime > int64(redline) {
						if last.lastRedline.IsZero() || (!last.lastRedline.IsZero() &&
							int64(currTime.Sub(last.lastRedline).Seconds()) > int64(redline)) {
							notify(pdServiceKey, message)
							lastSuccess[s] = a{currHeight, last.timeStamp, true, currTime}
						}
						progress = false
					}
					m.use()
					m.consensusProgress[fmt.Sprintf("shard-%s", s)] = progress
					m.done()
					continue
				}
			}
			lastSuccess[s] = a{currHeight, currTime, false, time.Time{}}
			m.use()
			m.consensusProgress[fmt.Sprintf("shard-%s", s)] = progress
			m.done()
		}
	}
}

func (m *monitor) manager(
	jobs chan work, interval int, nodeList []string,
	rpc string, group *sync.WaitGroup,
	channels map[string](chan reply), monitor chan bool,
) {
	requestFields := map[string]interface{}{
		"jsonrpc": versionJSONRPC,
		"method":  rpc,
		"params":  []interface{}{},
	}
	for now := range time.Tick(time.Duration(interval) * time.Second) {
		queryID := 0
		for n := range nodeList {
			requestFields["id"] = strconv.Itoa(queryID)
			requestBody, _ := json.Marshal(requestFields)
			jobs <- work{nodeList[n], rpc, requestBody}
			queryID++
			group.Add(1)
		}
		switch rpc {
		case metadataRPC:
			m.WorkingMetadata.TS = now
		case blockHeaderRPC:
			m.WorkingBlockHeader.TS = now
		}
		group.Wait()
		close(channels[rpc])

		first := true
		switch rpc {
		case metadataRPC:
			for d := range channels[rpc] {
				if first {
					m.WorkingMetadata.Down = []noReply{}
					m.WorkingMetadata.Nodes = []metadataRPCResult{}
					first = false
				}
				if d.oops != nil {
					m.WorkingMetadata.Down = append(m.WorkingMetadata.Down,
						noReply{d.address, d.oops.Error(), string(d.rpcPayload)})
				} else {
					m.bytesToNodeMetadata(d.rpc, d.address, d.rpcResult)
				}
			}
			m.use()
			m.metadataCopy(m.WorkingMetadata)
			m.done()
		case blockHeaderRPC:
			for d := range channels[rpc] {
				if first {
					m.WorkingBlockHeader.Down = []noReply{}
					m.WorkingBlockHeader.Nodes = []headerInfoRPCResult{}
					first = false
				}
				if d.oops != nil {
					m.WorkingBlockHeader.Down = append(m.WorkingBlockHeader.Down,
						noReply{d.address, d.oops.Error(), string(d.rpcPayload)})
				} else {
					m.bytesToNodeMetadata(d.rpc, d.address, d.rpcResult)
				}
			}
			m.use()
			m.blockHeaderCopy(m.WorkingBlockHeader)
			m.done()
			monitor <- true
		}
		channels[rpc] = make(chan reply, len(nodeList))
	}
}

func (m *monitor) update(
	params watchParams, superCommittee map[int]committee, rpcs []string,
) {
	nodeList := []string{}
	for _, v := range superCommittee {
		nodeList = append(nodeList, v.members...)
	}

	jobs := make(chan work, len(nodeList))
	replyChannels := make(map[string](chan reply))
	syncGroups := make(map[string]*sync.WaitGroup)
	for _, rpc := range rpcs {
		replyChannels[rpc] = make(chan reply, len(nodeList))
		switch rpc {
		case metadataRPC:
			var mGroup sync.WaitGroup
			syncGroups[rpc] = &mGroup
		case blockHeaderRPC:
			var bhGroup sync.WaitGroup
			syncGroups[rpc] = &bhGroup
		}
	}

	for i := 0; i < params.Performance.WorkerPoolSize; i++ {
		go m.worker(jobs, replyChannels, syncGroups)
	}

	for _, rpc := range rpcs {
		switch rpc {
		case metadataRPC:
			go m.manager(
				jobs, params.InspectSchedule.NodeMetadata, nodeList,
				rpc, syncGroups[rpc], replyChannels, nil,
			)
		case blockHeaderRPC:
			healthMonitorChan := make(chan bool)
			go m.manager(
				jobs, params.InspectSchedule.BlockHeader, nodeList, rpc,
				syncGroups[rpc], replyChannels, healthMonitorChan,
			)
			go m.shardMonitor(
				healthMonitorChan,
				params.ShardHealthReporting.Consensus.Warning,
				params.ShardHealthReporting.Consensus.Redline,
				params.Auth.PagerDuty.EventServiceKey,
				params.Network.TargetChain,
			)
		}
	}
}

func (m *monitor) bytesToNodeMetadata(rpc, addr string, payload []byte) {
	type r struct {
		Result nodeMetadata `json:"result"`
	}
	type s struct {
		Result headerInformation `json:"result"`
	}
	switch rpc {
	case metadataRPC:
		oneReport := r{}
		json.Unmarshal(payload, &oneReport)
		m.WorkingMetadata.Nodes = append(m.WorkingMetadata.Nodes, metadataRPCResult{
			oneReport.Result,
			addr,
		})
	case blockHeaderRPC:
		oneReport := s{}
		json.Unmarshal(payload, &oneReport)
		m.WorkingBlockHeader.Nodes = append(m.WorkingBlockHeader.Nodes, headerInfoRPCResult{
			oneReport.Result,
			addr,
		})
	}
}

type networkReport struct {
	Build             string                            `json:"watchdog-build-version"`
	Chain             string                            `json:"chain-name"`
	ConsensusProgress map[string]bool                   `json:"consensus-liviness"`
	Summary           map[string]map[string]interface{} `json:"summary-maps"`
	NoReplies         []noReply                         `json:"no-reply-machines"`
}

func (m *monitor) networkSnapshot() networkReport {
	m.use()
	sum := summaryMaps(m.MetadataSnapshot.Nodes, m.BlockHeaderSnapshot.Nodes)
	m.done()
	leaders := make(map[string][]string)
	linq.From(sum[metaSumry]).ForEach(func(v interface{}) {
		linq.From(sum[metaSumry][v.(linq.KeyValue).Key.(string)].(map[string]interface{})["records"]).
			Where(func(n interface{}) bool { return n.(metadataRPCResult).Payload.IsLeader }).
			ForEach(func(n interface{}) {
				shardID := strconv.FormatUint(uint64(n.(metadataRPCResult).Payload.ShardID), 10)
				leaders[shardID] = append(leaders[shardID], n.(metadataRPCResult).IP)
			})
	})
	for i := range leaders {
		// FIXME: Remove when hmy_getNodeMetadata RPC is fixed & deployed
		if sum[headerSumry][i] != nil {
			sum[headerSumry][i].(any)["shard-leader"] = leaders[i]
		}
	}
	cnsProgressCpy := map[string]bool{}
	m.use()
	for key, value := range m.consensusProgress {
		cnsProgressCpy[key] = value
	}
	totalNoReplyMachines := []noReply{}
	totalNoReplyMachines = append(
		append(totalNoReplyMachines, m.MetadataSnapshot.Down...), m.BlockHeaderSnapshot.Down...,
	)
	m.done()
	return networkReport{buildVersion, m.chain, cnsProgressCpy, sum, totalNoReplyMachines}
}

func (m *monitor) networkSnapshotJSON(w http.ResponseWriter, req *http.Request) {
	json.NewEncoder(w).Encode(m.networkSnapshot())
}

func (m *monitor) startReportingHTTPServer(instrs *instruction) {
	client = fasthttp.Client{
		Dial: func(addr string) (net.Conn, error) {
			return fasthttp.DialTimeout(addr, time.Second*time.Duration(instrs.Performance.HTTPTimeout))
		},
		MaxConnsPerHost: 2048,
	}
	go m.update(instrs.watchParams, instrs.superCommittee, []string{blockHeaderRPC, metadataRPC})
	http.HandleFunc("/report-"+instrs.Network.TargetChain, m.renderReport)
	http.HandleFunc("/report-download-"+instrs.Network.TargetChain, m.produceCSV)
	http.HandleFunc("/network-"+instrs.Network.TargetChain, m.networkSnapshotJSON)
	http.ListenAndServe(":"+strconv.Itoa(instrs.HTTPReporter.Port), nil)
}
