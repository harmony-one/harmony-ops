package main

import (
	"bytes"
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
	"syscall"

	"github.com/spf13/cobra"
	"github.com/takama/daemon"
	"gopkg.in/yaml.v2"
)

const (
	nameFMT     = "harmony-watchdog@%s"
	description = "Monitor the Harmony blockchain -- `%i`"
	spaceSep    = " "
)

var (
	sep       = []byte("\n")
	recordSep = []byte(spaceSep)
	rootCmd   = &cobra.Command{
		Use:          "harmony-watchdog",
		SilenceUsage: true,
		Long:         "Monitor a blockchain",
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

// Manage by daemon commands or run the daemon
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
	TargetChain string `yaml:"target-chain"`
	// Assumes Seconds
	InspectSchedule struct {
		BlockHeader  int `yaml:"block-header"`
		NodeMetadata int `yaml:"node-metadata"`
	} `yaml:"inspect-schedule"`
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
		MachineIPList string `yaml:"machine-ip-list"`
	} `yaml:"node-distribution"`
}

type instruction struct {
	watchParams
	networkNodes []string
}

func newInstructions(yamlPath string) (*instruction, error) {
	rawYAML, err := ioutil.ReadFile(yamlPath)
	if err != nil {
		return nil, err
	}
	t := watchParams{}
	err = yaml.Unmarshal(rawYAML, &t)
	if err != nil {
		return nil, err
	}
	nodesRecord, err2 := ioutil.ReadFile(t.DistributionFiles.MachineIPList)
	if err2 != nil {
		return nil, err2
	}
	networkNodes := bytes.Split(bytes.Trim(nodesRecord, "\n"), sep)
	instr := &instruction{t, []string{}}
	for _, value := range networkNodes {
		instr.networkNodes = append(
			instr.networkNodes,
			// Trust the input because it is already trusted elsewhere,
			// if data malformed, then launch would have failed anyway
			strings.TrimSpace(string(bytes.Split(value, recordSep)[0]))+":9500",
		)
	}
	return instr, nil
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
}
