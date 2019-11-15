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
	includeRecords, includeTS bool,
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
		}
		if includeTS {
			sum[shardID].(any)[timestamp] = time.Unix(linq.From(value.(linq.Group).Group).Select(
				func(c interface{}) interface{} {
					return c.(headerInfoRPCResult).Payload.UnixTime
				}).Distinct().Max().(int64), 0)
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
	blockHeaderSummary(headers, true, false, sum[headerSumry])
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
	m.use()
	sum := summaryMaps(m.MetadataSnapshot.Nodes, m.BlockHeaderSnapshot.Nodes)
	m.done()
	leaders := make(map[string][]string)
	linq.From(sum[metaSumry]).ForEach(func(v interface{}) {
		linq.From(sum[metaSumry][v.(linq.KeyValue).Key.(string)].(map[string]interface{})["records"]).Where(func(n interface{}) bool {
			return n.(metadataRPCResult).Payload.IsLeader
		}).ForEach(func(n interface{}) {
			shardID := strconv.FormatUint(uint64(n.(metadataRPCResult).Payload.ShardID), 10)
			leaders[shardID] = append(leaders[shardID], n.(metadataRPCResult).IP)
		})
	})
	for i, _ := range leaders {
		// FIXME: Remove when hmy_getNodeMetadata RPC is fixed & deployed
		if sum[headerSumry][i] != nil {
			sum[headerSumry][i].(any)["shard-leader"] = leaders[i]
		}
	}
	m.use()
	cnsMsg := "Consensus Progress not known yet"
	if len(m.consensusProgress) != 0 {
		cM, _ := json.Marshal(m.consensusProgress)
		cnsMsg = fmt.Sprintf("Consensus Progress: %s", cM)
	}
	totalNoReplyMachines := []noReply{}
	totalNoReplyMachines = append(totalNoReplyMachines, m.MetadataSnapshot.Down...)
	totalNoReplyMachines = append(totalNoReplyMachines, m.BlockHeaderSnapshot.Down...)
	m.done()
	t.ExecuteTemplate(w, "report", v{
		LeftTitle:  []interface{}{m.chain, cnsMsg},
		RightTitle: []interface{}{buildVersion, time.Now().Format(time.RFC3339)},
		Summary:    sum,
		NoReply:    totalNoReplyMachines,
		DownMachineCount: linq.From(totalNoReplyMachines).Select(
			func(c interface{}) interface{} { return c.(noReply).IP },
		).Distinct().Count(),
	})
	m.use()
	m.summaryCopy(sum)
	m.NoReplySnapshot = append([]noReply{}, totalNoReplyMachines...)
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
			for _, v := range m.SummarySnapshot[headerSumry][shard[0]].(any)["records"].([]interface{}) {
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
			for _, v := range m.SummarySnapshot[metaSumry][vrs[0]].(map[string]interface{})["records"].([]interface{}) {
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

func (m* monitor) worker(jobs chan work, channels map[string](chan reply), groups map[string]*sync.WaitGroup) {
	for j := range jobs {
		result := reply{address : j.address, rpc : j.rpc}
		result.rpcResult, result.rpcPayload, result.oops = request(
			"http://" + j.address, j.body)
		channels[j.rpc] <- result
		groups[j.rpc].Done()
	}
}

func (m* monitor) manager(jobs chan work, interval int, nodeList []string,
					rpc string, group *sync.WaitGroup, channels map[string](chan reply)) {
	requestFields := map[string]interface{} {
		"jsonrpc": versionJSONRPC,
		"method":  rpc,
		"params":  []interface{}{},
	}
	for now := range time.Tick(time.Duration(interval) * time.Second) {
		queryID := 0
		for _, n := range nodeList {
			requestFields["id"] = strconv.Itoa(queryID)
			requestBody, _ := json.Marshal(requestFields)
			jobs <- work {n, rpc, requestBody}
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
		}
		channels[rpc] = make(chan reply, len(nodeList))
	}
}

func (m *monitor) update(params watchParams, superCommittee map[int]committee, rpcs []string) {
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
			go m.manager(jobs, params.InspectSchedule.NodeMetadata, nodeList, rpc, syncGroups[rpc], replyChannels)
		case blockHeaderRPC:
			go m.manager(jobs, params.InspectSchedule.BlockHeader, nodeList, rpc, syncGroups[rpc], replyChannels)
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

func (m *monitor) watchShardHealth(pdServiceKey, chain string, warning, redline int) {
	sumCopy := func(prevS, newS any) {
		for key, value := range newS {
			prevS[key] = value
		}
	}
	// WARN Pay attention to the work here
	liviness := func(message string, interval int) {
		previousSummary := any{}
		currentSummary := any{}
		m.use()
		blockHeaderSummary(m.BlockHeaderSnapshot.Nodes, false, true, previousSummary)
		m.done()
		for range time.Tick(time.Duration(interval) * time.Second) {
			m.use()
			blockHeaderSummary(m.BlockHeaderSnapshot.Nodes, false, true, currentSummary)
			m.done()
			for shard, currentDetails := range currentSummary {
				sName := fmt.Sprintf("shard-%s", shard)
				nowDets, asrtOk1 := currentDetails.(any)
				thenDets, asrtOk2 := previousSummary[shard].(any)
				if asrtOk1 && asrtOk2 {
					if latestCount, ok := nowDets[blockMax]; ok {
						if prevCount, ok := thenDets[blockMax]; ok {
							thenTS := thenDets[timestamp].(time.Time)
							nowTS := nowDets[timestamp].(time.Time)
							elapsed := int64(nowTS.Sub(thenTS).Seconds())
							nowC := latestCount.(uint64)
							prevC := prevCount.(uint64)
							consensusProg := true
							if !(nowC > prevC) && int(elapsed) >= interval {
								name := fmt.Sprintf(nameFMT, chain)
								notify(pdServiceKey,
									fmt.Sprintf(`
%s: Liviness problem on shard %s

previous height %d at %s
current height %d at %s

Difference in seconds: %d

See: http://watchdog.hmny.io/report-%s

--%s
`, message, shard, prevC, thenTS, nowC, nowTS, elapsed, chain, name))
								consensusProg = false
							}
							m.use()
							m.consensusProgress[sName] = consensusProg
							m.done()
						}
					}
				}
			}
			sumCopy(previousSummary, currentSummary)
		}
	}
	go liviness("Warning", warning)
	// go liviness("Redline", redline)
}

func (m *monitor) startReportingHTTPServer(instrs *instruction) {
	client = fasthttp.Client{
		Dial: func(addr string) (net.Conn, error) {
			return fasthttp.DialTimeout(addr, time.Second * time.Duration(instrs.Performance.HTTPTimeout))
		},
		MaxConnsPerHost: 2048,
	}
	go m.update(instrs.watchParams, instrs.superCommittee, []string{blockHeaderRPC, metadataRPC})
	go m.watchShardHealth(
		instrs.Auth.PagerDuty.EventServiceKey,
		instrs.Network.TargetChain,
		instrs.ShardHealthReporting.Consensus.Warning,
		instrs.ShardHealthReporting.Consensus.Redline,
	)
	http.HandleFunc("/report-"+instrs.Network.TargetChain, m.renderReport)
	http.HandleFunc("/report-download", m.produceCSV)
	http.ListenAndServe(":"+strconv.Itoa(instrs.HTTPReporter.Port), nil)
}
