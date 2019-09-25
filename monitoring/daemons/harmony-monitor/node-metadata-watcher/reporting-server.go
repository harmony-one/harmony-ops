package main

import (
	"bytes"
	"encoding/csv"
	"encoding/json"
	"fmt"
	"html/template"
	"io/ioutil"
	"net/http"
	"reflect"
	"strconv"
	"sync"
	"time"

	"github.com/ahmetb/go-linq"
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
}

type headerInformation struct {
	BlockHash        string `json:"blockHash"`
	BlockNumber      uint64 `json:"blockNumber"`
	ShardID          uint32 `json:"shardID"`
	Leader           string `json:"leader"`
	ViewID           uint64 `json:"viewID"`
	Epoch            uint64 `json:"epoch"`
	Timestamp        string `json:"timestamp"`
	UnixTime         uint64 `json:"unixtime"`
	LastCommitSig    string `json:"lastCommitSig"`
	LastCommitBitmap string `json:"lastCommitBitmap"`
}

type any map[string]interface{}

var (
	queryID                    = 0
	nodeMetadataCSVHeader      []string
	headerInformationCSVHeader []string
)

func identity(x interface{}) interface{} {
	return x
}

const (
	metaSumry   = "node-metadata"
	headerSumry = "block-header"
	blockMax    = "block-max"
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
		var uniqEpochs []uint64 = []uint64{}
		var uniqBlockNums []uint64 = []uint64{}
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
	linq.From(metas).GroupByT(
		func(node metadataRPCResult) string { return parseVersionS(node.Payload.Version) }, identity,
	).ForEach(func(value interface{}) {
		vrs := value.(linq.Group).Key.(string)
		sum[metaSumry][vrs] = map[string]interface{}{"records": value.(linq.Group).Group}
	})
	blockHeaderSummary(headers, true, sum[headerSumry])
	return sum
}

func request(node, rpcMethod string) ([]byte, error) {
	requestBody, _ := json.Marshal(map[string]interface{}{
		"jsonrpc": versionJSONRPC,
		"id":      strconv.Itoa(queryID),
		"method":  rpcMethod,
		"params":  []interface{}{},
	})
	const cT = "application/json"
	resp, err := http.Post(node, cT, bytes.NewBuffer(requestBody))
	// fmt.Printf("URL: <%s>, Request Body: %s\n\n", node, string(requestBody))
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	queryID++
	// fmt.Printf("URL: %s, Response Body: %s\n\n", node, string(body))
	return body, nil
}

// TODO Make this be separate template parsed, not sure how to get it right
const shardJumpRow = `
{{define "shard-jump-row"}}
<div>
  {{ with (index .Summary "block-header") }}
  {{range $key, $value := .}}
    <a href=shard-{{$key}}> {{$key}} </a>
  {{end}}
  {{end}}
</div>
{{end}}
`

func (m *monitor) renderReport(w http.ResponseWriter, req *http.Request) {
	t, e := template.New("report").Parse(reportPage())
	if e != nil {
		fmt.Println(e)
		http.Error(w, "could not generate page:"+e.Error(), http.StatusInternalServerError)
		return
	}
	type v struct {
		Title   []string
		Summary interface{}
	}
	sum := summaryMaps(m.MetadataSnapshot.Nodes, m.BlockHeaderSnapshot.Nodes)
	t.ExecuteTemplate(w, "report", v{
		Title:   []string{m.chain, time.Now().Format(time.RFC3339), versionS()},
		Summary: sum,
	})
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
		case nodeMetadataReport:
			filename = nodeMetadataReport + ".csv"
			records = append(records, nodeMetadataCSVHeader)
		}
	default:
		http.Error(w, "report not chosen in query param", http.StatusBadRequest)
		return
	}
	w.Header().Set("Content-Type", "text/csv")
	w.Header().Set("Content-Disposition", "attachment;filename="+filename)
	wr := csv.NewWriter(w)
	// records := [][]string{
	// 	{"first_name", "last_name", "username"},
	// 	{"Rob", "Pike", "rob"},
	// 	{"Ken", "Thompson", "ken"},
	// 	{"Robert", "Griesemer", "gri"},
	// }
	err := wr.WriteAll(records)
	if err != nil {
		http.Error(w, "Error sending csv: "+err.Error(), http.StatusInternalServerError)
	}
}

type metadataRPCResult struct {
	Payload nodeMetadata
	IP      string
}

type headerInfoRPCResult struct {
	Payload headerInformation
	IP      string
}

type monitor struct {
	chain            string
	MetadataSnapshot struct {
		TS    time.Time
		Nodes []metadataRPCResult
	}
	BlockHeaderSnapshot struct {
		TS    time.Time
		Nodes []headerInfoRPCResult
	}
	lock *sync.Mutex
	cond *sync.Cond
}

func (m *monitor) update(rpc string, every int, nodeList []string) {
	type t struct {
		addr      string
		rpcResult []byte
		oops      error
	}
	for now := range time.Tick(time.Duration(every) * time.Second) {
		switch rpc {
		case metadataRPC:
			m.MetadataSnapshot.Nodes = []metadataRPCResult{}
		case blockHeaderRPC:
			m.lock.Lock()
			m.BlockHeaderSnapshot.Nodes = []headerInfoRPCResult{}
		}
		go func(n time.Time) {
			payloadChan := make(chan t, len(nodeList))
			for _, nodeIP := range nodeList {
				go func(addr string) {
					result := t{addr: addr}
					result.rpcResult, result.oops = request("http://"+addr, rpc)
					payloadChan <- result
				}(nodeIP)
			}
			for range nodeList {
				it := <-payloadChan
				if it.oops != nil {
					// fmt.Println("Some log of oops\n\n", it.oops)
					continue
				}
				m.bytesToNodeMetadata(rpc, it.addr, it.rpcResult)
			}
			switch rpc {
			case blockHeaderRPC:
				m.lock.Unlock()
				if len(m.BlockHeaderSnapshot.Nodes) > 0 {
					m.cond.Broadcast()
				}
			}
			m.MetadataSnapshot.TS = n
		}(now)
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
		m.MetadataSnapshot.Nodes = append(m.MetadataSnapshot.Nodes, metadataRPCResult{
			oneReport.Result,
			addr,
		})
	case blockHeaderRPC:
		oneReport := s{}
		json.Unmarshal(payload, &oneReport)
		m.BlockHeaderSnapshot.Nodes = append(m.BlockHeaderSnapshot.Nodes, headerInfoRPCResult{
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
		m.lock.Lock()
		m.cond.Wait()
		blockHeaderSummary(m.BlockHeaderSnapshot.Nodes, false, previousSummary)
		m.lock.Unlock()
		for range time.Tick(time.Duration(interval) * time.Second) {
			m.lock.Lock()
			m.cond.Wait()
			blockHeaderSummary(m.BlockHeaderSnapshot.Nodes, false, currentSummary)
			m.lock.Unlock()
			for shard, details := range currentSummary {
				if latestCount, ok := details.(any)[blockMax]; ok {
					if prevCount, ok := previousSummary[shard].(any)[blockMax]; ok {
						nowC := latestCount.(uint64)
						prevC := prevCount.(uint64)
						if !(nowC > prevC) {
							notify(pdServiceKey,
								fmt.Sprintf(`
%s: Liviness problem on shard %s

previous height %d
current height %d

See: http://watchdog.hmny.io/report-%s

--%s
`, message, shard, prevC, nowC, chain, name))
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
	go m.update(metadataRPC, instrs.InspectSchedule.NodeMetadata, instrs.networkNodes)
	go m.update(blockHeaderRPC, instrs.InspectSchedule.BlockHeader, instrs.networkNodes)
	go m.watchShardHealth(
		instrs.Auth.PagerDuty.EventServiceKey,
		instrs.TargetChain,
		instrs.ShardHealthReporting.Consensus.Warning,
		instrs.ShardHealthReporting.Consensus.Redline,
	)
	http.HandleFunc("/report-"+instrs.TargetChain, m.renderReport)
	http.HandleFunc("/report-download", m.produceCSV)
	http.ListenAndServe(":"+strconv.Itoa(instrs.HTTPReporter.Port), nil)
}
