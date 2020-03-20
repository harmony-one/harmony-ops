package main

import (
	"encoding/json"
	"fmt"
	"strconv"
	"sync"
	"time"
)

// Only need to query leader on Shard 0
func (m *monitor) crossLinkMonitor(interval uint64, poolSize int, pdServiceKey, chain string, shardMap map[string]int) {
	crossLinkRequestFields := getRPCRequest(LastCrossLinkRPC)
	nodeRequestFields := getRPCRequest(NodeMetadataRPC)

	jobs := make(chan work, len(shardMap))
	replyChannels := make(map[string](chan reply))
	syncGroups := make(map[string]*sync.WaitGroup)

	for _, rpc := range []string{NodeMetadataRPC, LastCrossLinkRPC} {
		replyChannels[rpc] = make(chan reply, len(shardMap))
		switch rpc {
		case NodeMetadataRPC:
			var mGroup sync.WaitGroup
			syncGroups[rpc] = &mGroup
		case LastCrossLinkRPC:
			var lGroup sync.WaitGroup
			syncGroups[rpc] = &lGroup
		}
	}

	for i := 0; i < poolSize; i++ {
		go m.worker(jobs, replyChannels, syncGroups)
	}

	type r struct {
		Result NodeMetadataReply `json:"result"`
	}

	type processedCrossLink struct {
		BlockNum  int
		CrossLink CrossLink
		TS        time.Time
	}

	lastProcessed := make(map[int]processedCrossLink)
	for now := range time.Tick(time.Duration(interval) * time.Second) {
		queryID := 0
		// Send requests to find potential shard 0 leaders
		for n := range shardMap {
			if shardMap[n] == 0 {
				nodeRequestFields["id"] = strconv.Itoa(queryID)
				requestBody, _ := json.Marshal(nodeRequestFields)
				jobs <- work{n, NodeMetadataRPC, requestBody}
				queryID++
				syncGroups[NodeMetadataRPC].Add(1)
			}
		}
		syncGroups[NodeMetadataRPC].Wait()
		close(replyChannels[NodeMetadataRPC])

		leader := []string{}
		for d := range replyChannels[NodeMetadataRPC] {
			if d.oops == nil {
				oneReport := r{}
				json.Unmarshal(d.rpcResult, &oneReport)
				if oneReport.Result.IsLeader {
					leader = append(leader, d.address)
				}
			}
		}

		queryID = 0
		// Request from all potential leaders
		for _, l := range leader {
			crossLinkRequestFields["id"] = strconv.Itoa(queryID)
			requestBody, _ := json.Marshal(crossLinkRequestFields)
			jobs <- work{l, LastCrossLinkRPC, requestBody}
			queryID++
			syncGroups[LastCrossLinkRPC].Add(1)
		}
		syncGroups[LastCrossLinkRPC].Wait()
		close(replyChannels[LastCrossLinkRPC])

		for i := range replyChannels[LastCrossLinkRPC] {
			if i.oops == nil {
				crossLinks := LastCrossLinkReply{}
				json.Unmarshal(i.rpcResult, &crossLinks.CrossLinks)
				for _, result := range crossLinks.CrossLinks {
					if entry, exists := lastProcessed[result.ShardID]; exists {
						if result.BlockNumber <= entry.BlockNum {
							elapsedTime := now.Sub(entry.TS)
							message := fmt.Sprintf(crossLinkMessage, result.ShardID,
								result.Hash, result.ShardID, result.BlockNumber, result.ShardID,
								result.EpochNumber, result.Signature, result.SignatureBitmap,
								elapsedTime.Seconds(), elapsedTime.Minutes())
							incidentKey := fmt.Sprintf("Chain: %s, Shard %d, CrossLinkMonitor", chain, result.ShardID)
							err := notify(pdServiceKey, incidentKey, chain, message)
							if err != nil {
								errlog.Print(err)
							} else {
								stdlog.Print("Sent PagerDuty alert! %s", incidentKey)
							}
							continue
						}
					}
					lastProcessed[result.ShardID] = processedCrossLink{
						result.BlockNumber,
						result,
						now,
					}
				}
			}
		}
		stdlog.Print(lastProcessed)
		replyChannels[NodeMetadataRPC] = make(chan reply, len(shardMap))
		replyChannels[LastCrossLinkRPC] = make(chan reply, len(shardMap))
	}
}
