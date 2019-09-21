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

type summary map[string]map[string]int

var (
	queryID                    = 0
	nodeMetadataCSVHeader      []string
	headerInformationCSVHeader []string
)

// Be careful, usage of interface{} can make things explode in the goroutine with bad cast
func counters(metas []metadataRPCResult, headers []headerInfoRPCResult) summary {
	const (
		metaSumry   = "node-metadata"
		headerSumry = "block-header"
	)
	sum := summary{metaSumry: map[string]int{}, headerSumry: map[string]int{}}
	linq.From(metas).GroupByT(
		func(node metadataRPCResult) string { return parseVersionS(node.Payload.Version) },
		func(node metadataRPCResult) string { return node.Payload.Version },
	).ForEach(func(value interface{}) {
		g := value.(linq.Group)
		sum[metaSumry][g.Key.(string)] = len(g.Group)
	})

	// Different Shards will have their own block height!
	headerS := linq.From(headers).GroupByT(
		// Group records by this value
		func(node headerInfoRPCResult) uint64 { return node.Payload.BlockNumber },
		// And collate the grouped values with this value
		func(node headerInfoRPCResult) string { return node.IP },
	).OrderByDescendingT(func(g linq.Group) int { return len(g.Group) })

	for _, value := range headerS.Results() {
		g := value.(linq.Group)
		sum[headerSumry][strconv.FormatUint(g.Key.(uint64), 10)] = len(g.Group)
	}

	return sum
}

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
		fmt.Println(err)
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

func (m *monitor) renderReport(w http.ResponseWriter, req *http.Request) {
	t, e := template.New("report").Parse(reportPage())
	if e != nil {
		fmt.Println(e)
		http.Error(w, "could not generate page:"+e.Error(), http.StatusInternalServerError)
		return
	}
	type v struct {
		Title         []string
		NodesMetadata []metadataRPCResult
		NodesHeader   []headerInfoRPCResult
	}
	for i, n := range m.BlockHeaderSnapshot.Nodes {
		shorted := n.Payload.LastCommitSig[:5] + "..." + n.Payload.LastCommitSig[len(n.Payload.LastCommitSig)-5:]
		m.BlockHeaderSnapshot.Nodes[i].Payload.LastCommitSig = shorted
	}

	highLevelSum := counters(m.MetadataSnapshot.Nodes, m.BlockHeaderSnapshot.Nodes)
	fmt.Println(highLevelSum)

	t.Execute(w, v{
		Title:         []string{m.chain, time.Now().Format(time.RFC3339), versionS()},
		NodesMetadata: m.MetadataSnapshot.Nodes,
		NodesHeader:   m.BlockHeaderSnapshot.Nodes,
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
	fmt.Println(req.URL.Query())
	fmt.Println(records)
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
					fmt.Println("Some log of oops", it.oops)
					continue
				}
				m.bytesToNodeMetadata(rpc, it.addr, it.rpcResult)
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

func (m *monitor) startReportingHTTPServer(instrs *instruction) {
	go m.update(metadataRPC, instrs.InspectSchedule.NodeMetadata, instrs.networkNodes)
	go m.update(blockHeaderRPC, instrs.InspectSchedule.BlockHeader, instrs.networkNodes)

	http.HandleFunc("/report-table", m.renderReport)
	http.HandleFunc("/report-download", m.produceCSV)
	http.ListenAndServe(":"+strconv.Itoa(instrs.HTTPReporter.Port), nil)
}
