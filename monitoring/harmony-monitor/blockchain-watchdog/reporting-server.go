package main

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"html/template"
	"net"
	"net/http"
	"reflect"
	"sort"
	"strconv"
	"sync"
	"time"

	"github.com/ahmetb/go-linq"
	"github.com/valyala/fasthttp"
)

const (
	badVersionString   = "BAD_VERSION_STRING"
	blockHeaderReport  = "block-header"
	nodeMetadataReport = "node-metadata"
	timeFormat         = "15:04:05 Jan _2 MST" // https://golang.org/pkg/time/#Time.Format
)

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
	metaSumry               = "node-metadata"
	headerSumry             = "block-header"
	chainSumry              = "chain-config"
	committeeSumry          = "staking-committee"
	blockMax                = "block-max"
	timestamp               = "timestamp"
	consensusWarningMessage = `
Consensus stuck on shard %s!

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
`
	cxPendingPoolWarning = `
Cx Transaction Pool too large on shard %s!

Count: %d
`
)

func init() {
	h := reflect.TypeOf((*BlockHeader)(nil)).Elem()
	for i := 0; i < h.NumField(); i++ {
		headerInformationCSVHeader = append(headerInformationCSVHeader, h.Field(i).Name)
	}
	n := reflect.TypeOf((*NodeMetadata)(nil)).Elem()
	for i := 0; i < n.NumField(); i++ {
		nodeMetadataCSVHeader = append(nodeMetadataCSVHeader, n.Field(i).Name)
	}
}

func blockHeaderSummary(
	headers []BlockHeader,
	includeRecords bool,
	sum map[string]interface{},
) {
	linq.From(headers).GroupBy(
		// Group by ShardID
		func(node interface{}) interface{} { return node.(BlockHeader).Payload.ShardID },
		identity,
	).ForEach(func(value interface{}) {
		shardID := strconv.FormatUint(uint64(value.(linq.Group).Key.(uint32)), 10)
		block := linq.From(value.(linq.Group).Group).Select(func(c interface{}) interface{} {
			return c.(BlockHeader).Payload.BlockNumber
		})
		epoch := linq.From(value.(linq.Group).Group).Select(func(c interface{}) interface{} {
			return c.(BlockHeader).Payload.Epoch
		})
		uniqEpochs := []uint64{}
		uniqBlockNums := []uint64{}
		epoch.Distinct().ToSlice(&uniqEpochs)
		block.Distinct().ToSlice(&uniqBlockNums)

		sort.SliceStable(uniqEpochs, func(i, j int) bool {
			return uniqEpochs[i] > uniqEpochs[j]
		})

		sort.SliceStable(uniqBlockNums, func(i, j int) bool {
			return uniqBlockNums[i] > uniqBlockNums[j]
		})

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
				return c.(BlockHeader).Payload.BlockNumber == block.Max()
			})
		}
	})
}

type summary map[string]map[string]interface{}

// WARN Be careful, usage of interface{} can make things explode in the goroutine with bad cast
func summaryMaps(metas []NodeMetadata, headers []BlockHeader) summary {
	sum := summary{metaSumry: map[string]interface{}{},
		headerSumry: map[string]interface{}{},
		chainSumry: map[string]interface{}{},
		committeeSumry: map [string]interface{}{},
	}
	for i, n := range headers {
		if s := n.Payload.LastCommitSig; len(s) > 0 {
			shorted := s[:5] + "..." + s[len(s)-5:]
			headers[i].Payload.LastCommitSig = shorted
		}
	}

	linq.From(metas).GroupBy(
		func(node interface{}) interface{} { return parseVersionS(node.(NodeMetadata).Payload.Version) }, identity,
	).ForEach(func(value interface{}) {
		vrs := value.(linq.Group).Key.(string)
		sum[metaSumry][vrs] = map[string]interface{}{"records": value.(linq.Group).Group}
	})

	linq.From(metas).GroupBy(
		func(node interface{}) interface{} { return node.(NodeMetadata).Payload.ShardID }, identity,
	).ForEach(func(value interface{}) {
		shardID := value.(linq.Group).Key.(uint32)
		sample := linq.From(value.(linq.Group).Group).FirstWith(func(c interface{}) bool {
			return c.(NodeMetadata).Payload.ShardID == shardID
		})
		sum[chainSumry][strconv.Itoa(int(shardID))] = any{
			"chain-id":          sample.(NodeMetadata).Payload.ChainConfig.ChainID,
			"cross-link-epoch":  sample.(NodeMetadata).Payload.ChainConfig.CrossLinkEpoch,
			"cross-tx-epoch":    sample.(NodeMetadata).Payload.ChainConfig.CrossTxEpoch,
			"eip155-epoch":      sample.(NodeMetadata).Payload.ChainConfig.Eip155Epoch,
			"s3-epoch":          sample.(NodeMetadata).Payload.ChainConfig.S3Epoch,
			"pre-staking-epoch": sample.(NodeMetadata).Payload.ChainConfig.PreStakingEpoch,
			"staking-epoch":     sample.(NodeMetadata).Payload.ChainConfig.StakingEpoch,
			"blocks-per-epoch":  sample.(NodeMetadata).Payload.BlocksPerEpoch,
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
		SuperCommittee        SuperCommitteeReply
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
		LeftTitle:        []interface{}{report.Chain},
		RightTitle:       []interface{}{report.Build, time.Now().Format(time.RFC3339)},
		Summary:          report.Summary,
		SuperCommittee:   m.SuperCommittee,
		NoReply:          report.NoReplies,
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
					v.(BlockHeader).IP,
					v.(BlockHeader).Payload.BlockHash,
					strconv.FormatUint(v.(BlockHeader).Payload.BlockNumber, 10),
					shard[0],
					v.(BlockHeader).Payload.Leader,
					strconv.FormatUint(v.(BlockHeader).Payload.ViewID, 10),
					strconv.FormatUint(v.(BlockHeader).Payload.Epoch, 10),
					v.(BlockHeader).Payload.Timestamp,
					strconv.FormatInt(v.(BlockHeader).Payload.UnixTime, 10),
					v.(BlockHeader).Payload.LastCommitSig,
					v.(BlockHeader).Payload.LastCommitBitmap,
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
						v.(NodeMetadata).IP,
						v.(NodeMetadata).Payload.BLSPublicKey,
						v.(NodeMetadata).Payload.Version,
						v.(NodeMetadata).Payload.NetworkType,
						strconv.FormatUint(uint64(v.(NodeMetadata).Payload.ChainConfig.ChainID), 10),
						strconv.FormatBool(v.(NodeMetadata).Payload.IsLeader),
						strconv.FormatUint(uint64(v.(NodeMetadata).Payload.ShardID), 10),
						v.(NodeMetadata).Payload.NodeRole,
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
	m.MetadataSnapshot.Nodes = append([]NodeMetadata{}, newData.Nodes...)
	m.MetadataSnapshot.Down = append([]noReply{}, newData.Down...)
}

func (m *monitor) blockHeaderCopy(newData BlockHeaderContainer) {
	m.BlockHeaderSnapshot.TS = newData.TS
	m.BlockHeaderSnapshot.Nodes = append([]BlockHeader{}, newData.Nodes...)
	m.BlockHeaderSnapshot.Down = append([]noReply{}, newData.Down...)
}

type noReply struct {
	IP            string
	FailureReason string
	RPCPayload    string
}

type MetadataContainer struct {
	TS    time.Time
	Nodes []NodeMetadata
	Down  []noReply
}

type BlockHeaderContainer struct {
	TS    time.Time
	Nodes []BlockHeader
	Down  []noReply
}

type monitor struct {
	chain               string
	inUse               sync.Mutex
	WorkingMetadata     MetadataContainer
	WorkingBlockHeader  BlockHeaderContainer
	MetadataSnapshot    MetadataContainer
	BlockHeaderSnapshot BlockHeaderContainer
	SuperCommittee      SuperCommitteeReply
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

func (m *monitor) consensusMonitor(interval uint64, poolSize int, pdServiceKey, chain string, nodeList []string) {
	jobs := make(chan work, len(nodeList))
	replyChannels := make(map[string](chan reply))
	syncGroups := make(map[string]*sync.WaitGroup)

	replyChannels[BlockHeaderRPC] = make(chan reply, len(nodeList))
	var bhGroup sync.WaitGroup
	syncGroups[BlockHeaderRPC] = &bhGroup

	for i := 0; i < poolSize; i++ {
		go m.worker(jobs, replyChannels, syncGroups)
	}

	requestFields := map[string]interface{}{
		"jsonrpc": JSONVersion,
		"method":  BlockHeaderRPC,
		"params":  []interface{}{},
	}

	type s struct {
		Result BlockHeaderReply `json:"result"`
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
			requestFields["id"] = strconv.Itoa(queryID)
			requestBody, _ := json.Marshal(requestFields)
			jobs <- work{nodeList[n], BlockHeaderRPC, requestBody}
			queryID++
			syncGroups[BlockHeaderRPC].Add(1)
		}
		syncGroups[BlockHeaderRPC].Wait()
		close(replyChannels[BlockHeaderRPC])

		monitorData := BlockHeaderContainer{}
		for d := range replyChannels[BlockHeaderRPC] {
			if d.oops != nil {
				monitorData.Down = append(m.WorkingBlockHeader.Down,
					noReply{d.address, d.oops.Error(), string(d.rpcPayload)})
			} else {
				oneReport := s{}
				json.Unmarshal(d.rpcResult, &oneReport)
				monitorData.Nodes = append(monitorData.Nodes, BlockHeader{
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
			currentBlockHeader := summary.(any)["latest-block"].(BlockHeader)
			if lastBlock, exists := lastShardData[shard]; exists {
				if currentBlockHeight <= lastBlock.Height {
					timeSinceLastSuccess := currentUTCTime.Sub(lastBlock.TS)
					if uint64(timeSinceLastSuccess.Seconds()) > interval {
						message := fmt.Sprintf(consensusWarningMessage,
							shard, currentBlockHeight, lastBlock.TS.Format(timeFormat),
							currentBlockHeader.Payload.BlockHash, currentBlockHeader.Payload.Leader,
							currentBlockHeader.Payload.ViewID, currentBlockHeader.Payload.Epoch,
							currentBlockHeader.Payload.Timestamp, currentBlockHeader.Payload.LastCommitSig,
							currentBlockHeader.Payload.LastCommitBitmap,
							int64(timeSinceLastSuccess.Seconds()), timeSinceLastSuccess.Minutes(),
							chain, fmt.Sprintf(nameFMT, chain))
						incidentKey := fmt.Sprintf("Shard %s consensus stuck!", shard)
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
		replyChannels[BlockHeaderRPC] = make(chan reply, len(nodeList))
	}
}

func (m *monitor) cxMonitor(interval uint64, poolSize int, pdServiceKey, chain string, nodeList []string) {
	cxRequestFields := map[string]interface{}{
		"jsonrpc": JSONVersion,
		"method":  PendingCxRPC,
		"params":  []interface{}{},
	}
	nodeRequestFields := map[string]interface{}{
		"jsonrpc": JSONVersion,
		"method":  NodeMetadataRPC,
		"params":  []interface{}{},
	}

	jobs := make(chan work, len(nodeList))
	replyChannels := make(map[string](chan reply))
	syncGroups := make(map[string]*sync.WaitGroup)
	for _, rpc := range []string{NodeMetadataRPC, PendingCxRPC} {
		replyChannels[rpc] = make(chan reply, len(nodeList))
		switch rpc {
		case NodeMetadataRPC:
			var mGroup sync.WaitGroup
			syncGroups[rpc] = &mGroup
		case PendingCxRPC:
			var cxGroup sync.WaitGroup
			syncGroups[rpc] = &cxGroup
		}
	}

	for i := 0; i < poolSize; i++ {
		go m.worker(jobs, replyChannels, syncGroups)
	}

	type r struct {
		Result NodeMetadataReply`json:"result"`
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
			jobs <- work{nodeList[n], NodeMetadataRPC, requestBody}
			queryID++
			syncGroups[NodeMetadataRPC].Add(1)
		}
		syncGroups[NodeMetadataRPC].Wait()
		close(replyChannels[NodeMetadataRPC])

		leaders := make(map[int][]string)
		for d := range replyChannels[NodeMetadataRPC] {
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
				jobs <- work{n, PendingCxRPC, requestBody}
				queryID++
				syncGroups[PendingCxRPC].Add(1)
			}
		}
		syncGroups[PendingCxRPC].Wait()
		close(replyChannels[PendingCxRPC])

		cxPoolSize := make(map[int][]uint64)
		for i := range replyChannels[PendingCxRPC] {
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
					incidentKey := fmt.Sprintf("Shard %s cx transaction pool size > 1000!", shard)
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

		replyChannels[NodeMetadataRPC] = make(chan reply, len(nodeList))
		replyChannels[PendingCxRPC] = make(chan reply, len(nodeList))
	}
}

func (m *monitor) stakingCommitteeUpdate(beaconChainNode string) {
	committeeRequestFields := map[string]interface{}{
		"jsonrpc": JSONVersion,
		"method":  SuperCommitteeRPC,
		"params":  []interface{}{},
	}

	committeeRequestFields["id"] = "0"
	requestBody, _ := json.Marshal(committeeRequestFields)
	result, _, oops := request("http://" + beaconChainNode, requestBody)

	type s struct {
		Result SuperCommitteeReply `json:"result"`
	}

	if oops != nil {
		stdlog.Println("Unable to update Staking Committee")
		stdlog.Print(oops)
		return
	} else {
		committeeReply := s{}
		json.Unmarshal(result, &committeeReply)
		m.SuperCommittee = committeeReply.Result
		stdlog.Println("Updated Staking Committee information")
	}
}

func (m *monitor) manager(
	jobs chan work, interval int, nodeList []string,
	rpc string, group *sync.WaitGroup,
	channels map[string](chan reply),
) {
	requestFields := map[string]interface{}{
		"jsonrpc": JSONVersion,
		"method":  rpc,
		"params":  []interface{}{},
	}

	prevEpoch := uint64(0)
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
		case NodeMetadataRPC:
			m.WorkingMetadata.TS = now
		case BlockHeaderRPC:
			m.WorkingBlockHeader.TS = now
		}
		group.Wait()
		close(channels[rpc])

		first := true
		switch rpc {
		case NodeMetadataRPC:
			for d := range channels[rpc] {
				if first {
					m.WorkingMetadata.Down = []noReply{}
					m.WorkingMetadata.Nodes = []NodeMetadata{}
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
		case BlockHeaderRPC:
			for d := range channels[rpc] {
				if first {
					m.WorkingBlockHeader.Down = []noReply{}
					m.WorkingBlockHeader.Nodes = []BlockHeader{}
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
			if len(m.WorkingBlockHeader.Nodes) > 0 {
				for _, n := range m.WorkingBlockHeader.Nodes {
					if n.Payload.ShardID == 0 {
						if n.Payload.Epoch > prevEpoch {
							prevEpoch = n.Payload.Epoch
							go m.stakingCommitteeUpdate(nodeList[0])
						}
						break
					}
				}
			}
			m.blockHeaderCopy(m.WorkingBlockHeader)
			m.inUse.Unlock()
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
		case NodeMetadataRPC:
			var mGroup sync.WaitGroup
			syncGroups[rpc] = &mGroup
		case BlockHeaderRPC:
			var bhGroup sync.WaitGroup
			syncGroups[rpc] = &bhGroup
		}
	}

	for i := 0; i < params.Performance.WorkerPoolSize; i++ {
		go m.worker(jobs, replyChannels, syncGroups)
	}

	for _, rpc := range rpcs {
		switch rpc {
		case NodeMetadataRPC:
			go m.manager(
				jobs, params.InspectSchedule.NodeMetadata, nodeList,
				rpc, syncGroups[rpc], replyChannels,
			)
		case BlockHeaderRPC:
			go m.manager(
				jobs, params.InspectSchedule.BlockHeader, nodeList, rpc,
				syncGroups[rpc], replyChannels,
			)
			go m.stakingCommitteeUpdate(nodeList[0])
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
		Result NodeMetadataReply`json:"result"`
	}
	type s struct {
		Result BlockHeaderReply `json:"result"`
	}
	switch rpc {
	case NodeMetadataRPC:
		oneReport := r{}
		json.Unmarshal(payload, &oneReport)
		m.WorkingMetadata.Nodes = append(m.WorkingMetadata.Nodes, NodeMetadata{
			oneReport.Result,
			addr,
		})
	case BlockHeaderRPC:
		oneReport := s{}
		json.Unmarshal(payload, &oneReport)
		m.WorkingBlockHeader.Nodes = append(m.WorkingBlockHeader.Nodes, BlockHeader{
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
			Where(func(n interface{}) bool { return n.(NodeMetadata).Payload.IsLeader }).
			ForEach(func(n interface{}) {
				shardID := strconv.FormatUint(uint64(n.(NodeMetadata).Payload.ShardID), 10)
				leaders[shardID] = append(leaders[shardID], n.(NodeMetadata).IP)
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
	go m.update(instrs.watchParams, instrs.superCommittee, []string{BlockHeaderRPC, NodeMetadataRPC})
	http.HandleFunc("/report-"+instrs.Network.TargetChain, m.renderReport)
	http.HandleFunc("/report-download-"+instrs.Network.TargetChain, m.produceCSV)
	http.HandleFunc("/network-"+instrs.Network.TargetChain, m.networkSnapshotJSON)
	http.ListenAndServe(":"+strconv.Itoa(instrs.HTTPReporter.Port), nil)
}
