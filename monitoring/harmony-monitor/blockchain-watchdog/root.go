package main

import (
	"bufio"
	"encoding/json"
	"errors"
	"fmt"
	"io/ioutil"
	"log"
	"net"
	"os"
	"os/signal"
	"path"
	"strconv"
	"strings"
	"sync"
	"syscall"

	"github.com/spf13/cobra"
	"github.com/takama/daemon"
	"gopkg.in/yaml.v2"
)

const (
	nameFMT     = "harmony-watchdogd@%s"
	description = "Monitor the Harmony blockchain -- `%i`"
	spaceSep    = " "
)

var (
	sep       = []byte("\n")
	recordSep = []byte(spaceSep)
	rootCmd   = &cobra.Command{
		Use:          "harmony-watchdogd",
		SilenceUsage: true,
		Long:         "Monitor a Harmony blockchain",
		Run: func(cmd *cobra.Command, args []string) {
			cmd.Help()
		},
	}
	w               *cobraSrvWrapper = &cobraSrvWrapper{nil}
	monitorNodeYAML string
	stdlog          *log.Logger
	errlog          *log.Logger
	// Add services here that we might want to depend on, see all services on
	// the machine with systemctl list-unit-files
	dependencies    = []string{}
	errSysIntrpt    = errors.New("daemon was interruped by system signal")
	errDaemonKilled = errors.New("daemon was killed")
)

// Indirection for cobra
type cobraSrvWrapper struct {
	*Service
}

// Service has embedded daemon
type Service struct {
	daemon.Daemon
	*monitor
	*instruction
}

func (service *Service) compareIPInShardFileWithNodes() error {
	requestBody, _ := json.Marshal(map[string]interface{}{
		"jsonrpc": versionJSONRPC,
		"id":      strconv.Itoa(queryID),
		"method":  blockHeaderRPC,
		"params":  []interface{}{},
	})
	type t struct {
		addr       string
		rpcPayload []byte
		rpcResult  []byte
		oops       error
	}
	type s struct {
		Result headerInformation `json:"result"`
	}
	type hooligans [][2]string
	const unreachableShard = -1
	results := sync.Map{}
	wait := sync.WaitGroup{}
	results.Store(unreachableShard, hooligans{})

	for shardID, subcommittee := range service.superCommittee {
		results.Store(shardID, hooligans{})
		for _, nodeIP := range subcommittee.members {
			wait.Add(1)
			go func(shardID int, nodeIP string) {
				defer wait.Add(-1)
				result := t{addr: nodeIP}
				url := "http://" + result.addr
				result.rpcResult, result.rpcPayload, result.oops = request(url, requestBody)
				if result.oops != nil {
					noReply, _ := results.Load(unreachableShard)
					results.Store(unreachableShard, append(
						noReply.(hooligans),
						[2]string{strconv.Itoa(shardID), nodeIP + "-" + result.oops.Error()},
					),
					)
					return
				}
				oneReport := s{}
				json.Unmarshal(result.rpcResult, &oneReport)
				if oneReport.Result.ShardID != uint32(shardID) {
					// I should be shardID but actually I was in Result.ShardID and my address is nodeIP
					naughty, _ := results.Load(shardID)
					results.Store(
						shardID, append(
							naughty.(hooligans), [2]string{strconv.Itoa(int(oneReport.Result.ShardID)), nodeIP},
						),
					)
				}
			}(shardID, nodeIP)
		}
	}

	wait.Wait()

	type wrongSpot struct {
		InShard string
		Addr    string
	}
	plainMap := map[string][]wrongSpot{}
	results.Range(func(key, value interface{}) bool {
		misplaced := make([]wrongSpot, len(value.(hooligans)))
		for i, pair := range value.(hooligans) {
			misplaced[i] = wrongSpot{pair[0], pair[1]}
		}
		switch k := key.(int); k {
		case unreachableShard:
			plainMap["no-reply-nodes"] = misplaced
		default:

		}
		return true
	})

	mapDump, _ := json.Marshal(plainMap)
	fmt.Println(string(mapDump))
	return nil
}

func (service *Service) monitorNetwork() error {
	interrupt := make(chan os.Signal, 1)
	signal.Notify(interrupt, os.Interrupt, os.Kill, syscall.SIGTERM)
	// Set up listener for defined host and port
	listener, err := net.Listen(
		"tcp",
		":"+strconv.Itoa(service.instruction.HTTPReporter.Port+1),
	)
	if err != nil {
		return err
	}
	// set up channel on which to send accepted connections
	listen := make(chan net.Conn, 100)
	go service.startReportingHTTPServer(service.instruction)
	go acceptConnection(listener, listen)
	// loop work cycle with accept connections or interrupt
	// by system signal
	for {
		select {
		case killSignal := <-interrupt:
			stdlog.Println("Got signal:", killSignal)
			stdlog.Println("Stoping listening on ", listener.Addr())
			listener.Close()
			if killSignal == os.Interrupt {
				return errSysIntrpt
			}
			return errDaemonKilled
		}
	}
	return nil
}

// Accept a client connection and collect it in a channel
func acceptConnection(listener net.Listener, listen chan<- net.Conn) {
	for {
		conn, err := listener.Accept()
		if err != nil {
			continue
		}
		listen <- conn
	}
}

type watchParams struct {
	Auth struct {
		PagerDuty struct {
			EventServiceKey string `yaml:"event-service-key"`
		} `yaml:"pagerduty"`
	} `yaml:"auth"`
	Network struct {
		TargetChain string `yaml:"target-chain"`
		RPCPort     int    `yaml:"public-rpc"`
	} `yaml:"network-config"`
	// Assumes Seconds
	InspectSchedule struct {
		BlockHeader  int `yaml:"block-header"`
		NodeMetadata int `yaml:"node-metadata"`
	} `yaml:"inspect-schedule"`
	Performance struct {
		WorkerPoolSize int `yaml:"num-workers"`
		HTTPTimeout    int `yaml:"http-timeout"`
	} `yaml:"performance"`
	HTTPReporter struct {
		Port int `yaml:"port"`
	} `yaml:"http-reporter"`
	ShardHealthReporting struct {
		Consensus struct {
			Warning int `yaml:"warning"`
			Redline int `yaml:"redline"`
		} `yaml:"consensus"`
	} `yaml:"shard-health-reporting"`
	DistributionFiles struct {
		MachineIPList []string `yaml:"machine-ip-list"`
	} `yaml:"node-distribution"`
}

type committee struct {
	file    string
	members []string
}

type instruction struct {
	watchParams
	superCommittee map[int]committee
}

func newInstructions(yamlPath string) (*instruction, error) {
	rawYAML, err := ioutil.ReadFile(yamlPath)
	if err != nil {
		return nil, err
	}
	t := watchParams{}
	err = yaml.UnmarshalStrict(rawYAML, &t)
	if err != nil {
		return nil, err
	}
	oops := t.sanityCheck()
	if oops != nil {
		return nil, oops
	}
	byShard := make(map[int]committee, len(t.DistributionFiles.MachineIPList))
	for _, file := range t.DistributionFiles.MachineIPList {
		shard := path.Base(strings.TrimSuffix(file, path.Ext(file)))
		id, err := strconv.Atoi(string(shard[len(shard)-1]))
		if err != nil {
			return nil, err
		}
		ipList := []string{}
		f, err := os.Open(file)
		if err != nil {
			return nil, nil
		}
		defer f.Close()
		scanner := bufio.NewScanner(f)
		for scanner.Scan() {
		 	ipList = append(ipList, scanner.Text()+":"+strconv.Itoa(t.Network.RPCPort))
		}
		err = scanner.Err()
		if err != nil {
			return nil, err
		}
		byShard[id] = committee{file, ipList}
	}
	dups := []string{}
	nodeList := make(map[string]bool)
	for _, s := range byShard {
		for _, m := range s.members {
			if _, check := nodeList[m]; check {
				dups = append(dups, m)
			} else {
				nodeList[m] = true
			}
		}
	}
	if len(dups) > 0  {
		return nil, errors.New("Duplicate IPs detected. " + strings.Join(dups, "\n"))
	}
	return &instruction{t, byShard}, nil
}

func (w *watchParams) sanityCheck() error {
	errList := []string{}
	if w.Network.RPCPort == 0 {
		errList = append(errList, "Missing public-rpc under network-config in yaml config")
	}
	if w.InspectSchedule.BlockHeader == 0 {
		errList = append(errList, "Missing block-header under inspect-schedule in yaml config")
	}
	if w.InspectSchedule.NodeMetadata == 0 {
		errList = append(errList, "Missing node-metadata under inspect-schedule in yaml config")
	}
	if w.Performance.WorkerPoolSize == 0 {
		errList = append(errList, "Missing num-workers under performance in yaml config")
	}
	if w.Performance.HTTPTimeout == 0 {
		errList = append(errList, "Missing http-timeout under performance in yaml config")
	}
	if w.HTTPReporter.Port == 0 {
		errList = append(errList, "Missing port under http-reporter in yaml config")
	}
	if w.ShardHealthReporting.Consensus.Warning == 0 {
		errList = append(errList, "Missing warmomg under shard-health-reporting, consensus in yaml config")
	}
	if w.ShardHealthReporting.Consensus.Redline == 0 {
		errList = append(errList, "Missing Redline under shard-health-reporting, consensus in yaml config")
	}
	if len(errList) == 0 {
		return nil
	}
	return errors.New(strings.Join(errList, "\n"))
}

func versionS() string {
	return fmt.Sprintf(
		"Harmony (C) 2019. %v, version %v-%v (%v %v)",
		path.Base(os.Args[0]), version, commit, builtBy, builtAt,
	)
}

func parseVersionS(v string) string {
	const versionSpot = 5
	const versionSep = "-"
	chopped := strings.Split(v, spaceSep)
	if len(chopped) < versionSpot {
		return badVersionString
	}
	return chopped[versionSpot]
}

func init() {
	stdlog = log.New(os.Stdout, "", log.Ldate|log.Ltime)
	errlog = log.New(os.Stderr, "", log.Ldate|log.Ltime)
	rootCmd.AddCommand(&cobra.Command{
		Use:   "version",
		Short: "Show version",
		Run: func(cmd *cobra.Command, args []string) {
			fmt.Fprintf(os.Stderr, versionS()+"\n")
			os.Exit(0)
		},
	})
	rootCmd.AddCommand(serviceCmd())
	rootCmd.AddCommand(monitorCmd())
	rootCmd.AddCommand(validateMachineIPList())
	rootCmd.AddCommand(generateSampleYAML())
}
