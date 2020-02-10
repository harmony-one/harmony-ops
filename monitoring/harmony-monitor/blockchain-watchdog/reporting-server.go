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
	metadataRPC        = "hmy_getNodeMetadata"
	blockHeaderRPC     = "hmy_latestHeader"
	cxPendingRPC       = "hmy_getPendingCxReceipts"
	blockHeaderReport  = "block-header"
	nodeMetadataReport = "node-metadata"
	timeFormat         = "15:04:05 Jan _2 MST" // https://golang.org/pkg/time/#Time.Format
)

type nodeMetadata struct {
	BLSPublicKey   string `json:"blskey"`
	Version        string `json:"version"`
	NetworkType    string `json:"network"`
	IsLeader       bool   `json:"is-leader"`
	ShardID        uint32 `json:"shard-id"`
	NodeRole       string `json:"role"`
	BlocksPerEpoch int    `json:"blocks-per-epoch"`
	ChainConfig    struct {
		ChainID         int `json:"chain-id"`
		CrossLinkEpoch  int `json:"cross-link-epoch"`
		CrossTxEpoch    int `json:"cross-tx-epoch"`
		Eip155Epoch     int `json:"eip155-epoch"`
		PreStakingEpoch int `json:"prestaking-epoch"`
		S3Epoch         int `json:"s3-epoch"`
		StakingEpoch    int `json:"staking-epoch"`
	} `json:"chain-config"`
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

//NOTE: maps for marshalling RPC request body
var (
	cxRequestFields = map[string]interface{}{
		"jsonrpc": versionJSONRPC,
		"method":  cxPendingRPC,
		"params":  []interface{}{},
	}
	nodeRequestFields = map[string]interface{}{
		"jsonrpc": versionJSONRPC,
		"method":  metadataRPC,
		"params":  []interface{}{},
	}
	blockHeaderRequestFields = map[string]interface{}{
		"jsonrpc": versionJSONRPC,
		"method":  blockHeaderRPC,
		"params":  []interface{}{},
	}
)

func identity(x interface{}) interface{} {
	return x
}

const (
	metaSumry               = "node-metadata"
	headerSumry             = "block-header"
	chainSumry              = "chain-config"
	blockMax                = "block-max"
	timestamp               = "timestamp"
	consensusWarningMessage = `
Consensus stuck on shard %s!

Block height stuck at %d starting at %s

Block Hash: %s

Leader: %s

Leader-Location: %s

ViewID: %d

Epoch: %d

Block Timestamp: %s

LastCommitSig: %s

LastCommitBitmap: %s

Time since last new block: %d seconds (%f minutes)

See: http://watchdog.hmny.io/report-%s

--%s
`
	cxPendingPoolWarning = `
Cx Transaction Pool too large on shard %s!

Count: %d
`
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
	sum := summary{metaSumry: map[string]interface{}{}, headerSumry: map[string]interface{}{}, chainSumry: map[string]interface{}{}}
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

	linq.From(metas).GroupBy(
		func(node interface{}) interface{} { return node.(metadataRPCResult).Payload.ShardID }, identity,
	).ForEach(func(value interface{}) {
		shardID := value.(linq.Group).Key.(uint32)
		sample := linq.From(value.(linq.Group).Group).FirstWith(func(c interface{}) bool {
			return c.(metadataRPCResult).Payload.ShardID == shardID
		})
		sum[chainSumry][strconv.Itoa(int(shardID))] = any{
			"chain-id":          sample.(metadataRPCResult).Payload.ChainConfig.ChainID,
			"cross-link-epoch":  sample.(metadataRPCResult).Payload.ChainConfig.CrossLinkEpoch,
			"cross-tx-epoch":    sample.(metadataRPCResult).Payload.ChainConfig.CrossTxEpoch,
			"eip155-epoch":      sample.(metadataRPCResult).Payload.ChainConfig.Eip155Epoch,
			"s3-epoch":          sample.(metadataRPCResult).Payload.ChainConfig.S3Epoch,
			"pre-staking-epoch": sample.(metadataRPCResult).Payload.ChainConfig.PreStakingEpoch,
			"staking-epoch":     sample.(metadataRPCResult).Payload.ChainConfig.StakingEpoch,
			"blocks-per-epoch":  sample.(metadataRPCResult).Payload.BlocksPerEpoch,
		}
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
	t, e := template.New("report").Parse(reportPage(m.chain))
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
	if len(report.ConsensusProgress) != 0 {
		for k, v := range report.ConsensusProgress {
			if report.Summary[chainSumry][k] != nil {
				report.Summary[chainSumry][k].(any)["consensus-status"] = v
			}
		}
	}
	t.ExecuteTemplate(w, "report", v{
		LeftTitle:  []interface{}{report.Chain},
		RightTitle: []interface{}{report.Build, time.Now().Format(time.RFC3339)},
		Summary:    report.Summary,
		NoReply:    report.NoReplies,
		DownMachineCount: linq.From(report.NoReplies).Select(
			func(c interface{}) interface{} { return c.(noReply).IP },
		).Distinct().Count(),
	})
	m.inUse.Lock()
	m.summaryCopy(report.Summary)
	m.NoReplySnapshot = append([]noReply{}, report.NoReplies...)
	m.inUse.Unlock()
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
			m.inUse.Lock()
			sum := m.SummarySnapshot[headerSumry][shard[0]].(any)["records"].([]interface{})
			for _, v := range sum {
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
			m.inUse.Unlock()
		case nodeMetadataReport:
			filename = nodeMetadataReport + ".csv"
			records = append(records, nodeMetadataCSVHeader)

			vrs, ex := req.URL.Query()["vrs"]
			if !ex {
				http.Error(w, "version not chosen in query param", http.StatusBadRequest)
				return
			}
			m.inUse.Lock()
			// FIXME: Bandaid
			if m.SummarySnapshot[metaSumry][vrs[0]] != nil {
				recs := m.SummarySnapshot[metaSumry][vrs[0]].(map[string]interface{})["records"].([]interface{})
				for _, v := range recs {
					row := []string{
						v.(metadataRPCResult).IP,
						v.(metadataRPCResult).Payload.BLSPublicKey,
						v.(metadataRPCResult).Payload.Version,
						v.(metadataRPCResult).Payload.NetworkType,
						strconv.FormatUint(uint64(v.(metadataRPCResult).Payload.ChainConfig.ChainID), 10),
						strconv.FormatBool(v.(metadataRPCResult).Payload.IsLeader),
						strconv.FormatUint(uint64(v.(metadataRPCResult).Payload.ShardID), 10),
						v.(metadataRPCResult).Payload.NodeRole,
					}
					records = append(records, row)
				}
			}
			m.inUse.Unlock()
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
	inUse               sync.Mutex
	WorkingMetadata     MetadataContainer
	WorkingBlockHeader  BlockHeaderContainer
	MetadataSnapshot    MetadataContainer
	BlockHeaderSnapshot BlockHeaderContainer
	SummarySnapshot     map[string]map[string]interface{}
	NoReplySnapshot     []noReply
	consensusProgress   map[string]bool
}

type work struct {
	address      string
	rpc          string
	body         []byte
	replyChannel chan reply
	syncGroup    *sync.WaitGroup
}

type reply struct {
	address    string
	rpc        string
	rpcPayload []byte
	rpcResult  []byte
	oops       error
}

func (m *monitor) worker(jobs chan work) {
	for j := range jobs {
		result := reply{address: j.address, rpc: j.rpc}
		result.rpcResult, result.rpcPayload, result.oops = request(
			"http://"+j.address, j.body)
		j.replyChannel <- result
		j.syncGroup.Done()
	}
}

func (m *monitor) findLeader(
	interval uint64, nodeList *[]string, poolSize int,
) map[int][]string {
	jobs := make(chan work, len(*nodeList))

	replyChannel := make(chan reply, len(*nodeList))
	var mGroup sync.WaitGroup

	for i := 0; i < poolSize; i++ {
		go m.worker(jobs)
	}

	type result struct {
		Result nodeMetadata `json:"result"`
	}

	leaders := make(map[int][]string)

	queryID := 0
	// Send requests to find potential shard leaders
	for n := range *nodeList {
		nodeRequestFields["id"] = strconv.Itoa(queryID)
		requestBody, _ := json.Marshal(nodeRequestFields)
		jobs <- work{(*nodeList)[n], metadataRPC, requestBody, replyChannel, &mGroup}
		queryID++
		mGroup.Add(1)
	}
	mGroup.Wait()
	close(replyChannel)

	for d := range replyChannel {
		if d.oops == nil {
			oneReport := result{}
			json.Unmarshal(d.rpcResult, &oneReport)
			if oneReport.Result.IsLeader {
				shard := int(oneReport.Result.ShardID)
				if _, exists := leaders[shard]; exists {
					leaders[shard] = append(leaders[shard], d.address)
				} else {
					leaders[shard] = []string{d.address}
				}
			}
		}
	}
	replyChannel = make(chan reply, len(*nodeList))
	return leaders
}

func (m *monitor) consensusMonitor(
	interval uint64, poolSize int, pdServiceKey, chain string, nodeList []string,
) {
	jobs := make(chan work, len(nodeList))

	replyChannel := make(chan reply, len(nodeList))
	var bhGroup sync.WaitGroup

	for i := 0; i < poolSize; i++ {
		go m.worker(jobs)
	}

	type s struct {
		Result headerInformation `json:"result"`
	}

	type lastSuccessfulBlock struct {
		Height uint64
		TS     time.Time
	}

	lastShardData := make(map[string]lastSuccessfulBlock)
	consensusStatus := make(map[string]bool)

	for now := range time.Tick(time.Duration(interval) * time.Second) {
		queryID := 0
		for n := range nodeList {
			blockHeaderRequestFields["id"] = strconv.Itoa(queryID)
			requestBody, _ := json.Marshal(blockHeaderRequestFields)
			jobs <- work{nodeList[n], blockHeaderRPC, requestBody, replyChannel, &bhGroup}
			queryID++
			bhGroup.Add(1)
		}
		bhGroup.Wait()
		close(replyChannel)

		monitorData := BlockHeaderContainer{}
		for d := range replyChannel {
			if d.oops != nil {
				monitorData.Down = append(m.WorkingBlockHeader.Down,
					noReply{d.address, d.oops.Error(), string(d.rpcPayload)})
			} else {
				oneReport := s{}
				json.Unmarshal(d.rpcResult, &oneReport)
				monitorData.Nodes = append(monitorData.Nodes, headerInfoRPCResult{
					oneReport.Result,
					d.address,
				})
			}
		}

		blockHeaderData := any{}
		blockHeaderSummary(monitorData.Nodes, true, blockHeaderData)

		currentUTCTime := now.UTC()

		for shard, summary := range blockHeaderData {
			currentBlockHeight := summary.(any)[blockMax].(uint64)
			currentBlockHeader := summary.(any)["latest-block"].(headerInfoRPCResult)
			if lastBlock, exists := lastShardData[shard]; exists {
				if currentBlockHeight <= lastBlock.Height {
					timeSinceLastSuccess := currentUTCTime.Sub(lastBlock.TS)
					if uint64(timeSinceLastSuccess.Seconds()) > interval {
						// Do a quick, concurrent metadata pass
						leader := m.findLeader(interval, &nodeList, poolSize)

						shardAsInt, _ := strconv.Atoi(shard)

						message := fmt.Sprintf(consensusWarningMessage,
							shard, currentBlockHeight, lastBlock.TS.Format(timeFormat),
							currentBlockHeader.Payload.BlockHash,
							currentBlockHeader.Payload.Leader,
							leader[shardAsInt],
							currentBlockHeader.Payload.ViewID,
							currentBlockHeader.Payload.Epoch,
							currentBlockHeader.Payload.Timestamp,
							currentBlockHeader.Payload.LastCommitSig,
							currentBlockHeader.Payload.LastCommitBitmap,
							int64(timeSinceLastSuccess.Seconds()), timeSinceLastSuccess.Minutes(),
							chain, fmt.Sprintf(nameFMT, chain))
						incidentKey := fmt.Sprintf("%s Shard %s consensus stuck!", chain, shard)
						err := notify(pdServiceKey, incidentKey, chain, message)
						if err != nil {
							errlog.Print(err)
						} else {
							stdlog.Print("Sent PagerDuty alert! %s", incidentKey)
						}
						consensusStatus[shard] = false
						continue
					}
				}
			}
			lastShardData[shard] = lastSuccessfulBlock{currentBlockHeight, time.Unix(currentBlockHeader.Payload.UnixTime, 0).UTC()}
			consensusStatus[shard] = true
		}
		stdlog.Printf("Total no reply machines: %d", len(monitorData.Down))
		stdlog.Print(lastShardData)
		stdlog.Print(consensusStatus)

		m.inUse.Lock()
		m.consensusProgress = consensusStatus
		m.inUse.Unlock()
		replyChannel = make(chan reply, len(nodeList))
	}
}

func (m *monitor) cxMonitor(interval uint64, poolSize int, pdServiceKey, chain string, nodeList []string) {
	jobs := make(chan work, len(nodeList))
	metadataReplyChannel := make(chan reply, len(nodeList))
	cxPendingReplyChannel := make(chan reply, len(nodeList))
	var mGroup sync.WaitGroup
	var cxGroup sync.WaitGroup

	for i := 0; i < poolSize; i++ {
		go m.worker(jobs)
	}

	type r struct {
		Result nodeMetadata `json:"result"`
	}

	type a struct {
		Result uint64 `json:"result"`
	}

	for range time.Tick(time.Duration(interval) * time.Second) {
		queryID := 0
		// Send requests to find potential shard leaders
		for n := range nodeList {
			nodeRequestFields["id"] = strconv.Itoa(queryID)
			requestBody, _ := json.Marshal(nodeRequestFields)
			jobs <- work{nodeList[n], metadataRPC, requestBody, metadataReplyChannel, &mGroup}
			queryID++
			mGroup.Add(1)
		}
		mGroup.Wait()
		close(metadataReplyChannel)

		leaders := make(map[int][]string)
		for d := range metadataReplyChannel {
			if d.oops == nil {
				oneReport := r{}
				json.Unmarshal(d.rpcResult, &oneReport)
				if oneReport.Result.IsLeader {
					shard := int(oneReport.Result.ShardID)
					if _, exists := leaders[shard]; exists {
						leaders[shard] = append(leaders[shard], d.address)
					} else {
						leaders[shard] = []string{d.address}
					}
				}
			}
		}

		// What do in case of no leader shown (skip cycle for shard)
		// No reply also skip
		queryID = 0
		for _, node := range leaders {
			for _, n := range node {
				cxRequestFields["id"] = strconv.Itoa(queryID)
				requestBody, _ := json.Marshal(cxRequestFields)
				jobs <- work{n, cxPendingRPC, requestBody, cxPendingReplyChannel, &cxGroup}
				queryID++
				cxGroup.Add(1)
			}
		}
		cxGroup.Wait()
		close(cxPendingReplyChannel)

		cxPoolSize := make(map[int][]uint64)
		for i := range cxPendingReplyChannel {
			if i.oops == nil {
				report := a{}
				json.Unmarshal(i.rpcResult, &report)
				shard := 0
				for s, v := range leaders {
					for _, n := range v {
						if n == i.address {
							shard = s
							break
						}
					}
				}
				if _, exists := cxPoolSize[shard]; exists {
					cxPoolSize[shard] = append(cxPoolSize[shard], report.Result)
				} else {
					cxPoolSize[shard] = []uint64{report.Result}
				}
				if report.Result > uint64(1000) {
					message := fmt.Sprintf(cxPendingPoolWarning, shard, report.Result)
					incidentKey := fmt.Sprintf("%s Shard %s cx transaction pool size > 1000!", chain, shard)
					err := notify(pdServiceKey, incidentKey, chain, message)
					if err != nil {
						errlog.Print(err)
					} else {
						stdlog.Print("Sent PagerDuty alert! %s", incidentKey)
					}
				}
			}
		}

		stdlog.Print(leaders)
		stdlog.Print(cxPoolSize)

		metadataReplyChannel = make(chan reply, len(nodeList))
		cxPendingReplyChannel = make(chan reply, len(nodeList))
	}
}

func (m *monitor) manager(
	jobs chan work, interval int, nodeList []string,
	rpc string, group *sync.WaitGroup,
	channel chan reply,
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
			jobs <- work{nodeList[n], rpc, requestBody, channel, group}
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
		close(channel)

		first := true
		switch rpc {
		case metadataRPC:
			for d := range channel {
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
			m.inUse.Lock()
			m.metadataCopy(m.WorkingMetadata)
			m.inUse.Unlock()
		case blockHeaderRPC:
			for d := range channel {
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
			m.inUse.Lock()
			m.blockHeaderCopy(m.WorkingBlockHeader)
			m.inUse.Unlock()
		}
		channel = make(chan reply, len(nodeList))
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

	metadataReplyChannel := make(chan reply, len(nodeList))
	blockHeaderReplyChannel := make(chan reply, len(nodeList))
	var mGroup sync.WaitGroup
	var bhGroup sync.WaitGroup

	for i := 0; i < params.Performance.WorkerPoolSize; i++ {
		go m.worker(jobs)
	}

	for _, rpc := range rpcs {
		switch rpc {
		case metadataRPC:
			go m.manager(
				jobs, params.InspectSchedule.NodeMetadata, nodeList,
				rpc, &mGroup, metadataReplyChannel,
			)
		case blockHeaderRPC:
			go m.manager(
				jobs, params.InspectSchedule.BlockHeader, nodeList, rpc,
				&bhGroup, blockHeaderReplyChannel,
			)
			go m.consensusMonitor(
				uint64(params.ShardHealthReporting.Consensus.Warning),
				params.Performance.WorkerPoolSize,
				params.Auth.PagerDuty.EventServiceKey,
				params.Network.TargetChain,
				nodeList,
			)
			go m.cxMonitor(
				uint64(params.InspectSchedule.CxPending),
				params.Performance.WorkerPoolSize,
				params.Auth.PagerDuty.EventServiceKey,
				params.Network.TargetChain,
				nodeList,
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
	m.inUse.Lock()
	sum := summaryMaps(m.MetadataSnapshot.Nodes, m.BlockHeaderSnapshot.Nodes)
	m.inUse.Unlock()
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
	m.inUse.Lock()
	for key, value := range m.consensusProgress {
		cnsProgressCpy[key] = value
	}
	totalNoReplyMachines := []noReply{}
	totalNoReplyMachines = append(
		append(totalNoReplyMachines, m.MetadataSnapshot.Down...), m.BlockHeaderSnapshot.Down...,
	)
	m.inUse.Unlock()
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
