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
	"strings"
	"syscall"

	"github.com/spf13/cobra"
	"github.com/takama/daemon"
	"gopkg.in/yaml.v2"
)

const (
	name        = "harmony-watchdog"
	description = "Monitor the Harmony blockchain"
	port        = ":9977"
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
	monitorNodeYAML string
	stdlog          *log.Logger
	errlog          *log.Logger
	//    dependencies that are NOT required by the service, but might be used
	dependencies = []string{"dummy.service"}
)

// Service has embedded daemon
type Service struct {
	daemon.Daemon
	*monitor
	*instruction
}

// Manage by daemon commands or run the daemon
func (service *Service) Manage() error {
	a, installE := service.Install()
	if installE != nil {
		return installE
	}
	// service.Remove()

	c, startE := service.Start()
	if startE != nil {
		return startE
	}

	fmt.Println(a, c)
	// service.Stop()
	// service.Status()
	// Do something, call your goroutines, etc
	// Set up channel on which to send signal notifications.
	// We must use a buffered channel or risk missing the signal
	// if we're not ready to receive when the signal is sent.
	interrupt := make(chan os.Signal, 1)
	signal.Notify(interrupt, os.Interrupt, os.Kill, syscall.SIGTERM)
	// Set up listener for defined host and port
	listener, err := net.Listen("tcp", port)
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
		case conn := <-listen:
			go handleClient(conn, service.instruction.Auth.PagerDuty.EventServiceKey)
		case killSignal := <-interrupt:
			stdlog.Println("Got signal:", killSignal)
			stdlog.Println("Stoping listening on ", listener.Addr())
			listener.Close()
			if killSignal == os.Interrupt {
				return errors.New("daemon was interruped by system signal")
			}
			return errors.New("daemon was killed")
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

func handleClient(client net.Conn, serviceKey string) {
	for {
		buf := make([]byte, 4096)
		numbytes, err := client.Read(buf)
		if numbytes == 0 || err != nil {
			return
		}
		cmd := strings.TrimSpace(string(bytes.Trim(buf, "\x00")))
		fmt.Println(cmd)
		switch cmd {
		case "work":
			// client.Write(baseRequest("http://localhost:9500"))
		case "pager":
			notifyTeam(serviceKey)
		default:
			client.Write(buf[:numbytes])
		}
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
	ReportWhen struct {
		BlockDeviation int `yaml:"block-deviation"`
		NodeThreshold  int `yaml:"threshold"`
	} `yaml:"report-when"`
	DistributionFiles struct {
		ConfigTxt string `yaml:"config-txt"`
		RawIPTxt  string `yaml:"raw-ip-txt"`
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
	nodesRecord, err2 := ioutil.ReadFile(t.DistributionFiles.ConfigTxt)
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

	monitor := &cobra.Command{
		Use:   "monitor",
		Short: "watch the blockchain for problems",
		RunE: func(cmd *cobra.Command, args []string) error {
			instr, err := newInstructions(monitorNodeYAML)
			if err != nil {
				return err
			}
			srv, err := daemon.New(name, description, dependencies...)
			if err != nil {
				return err
			}
			m := &monitor{chain: instr.TargetChain}
			service := &Service{srv, m, instr}
			err = service.Manage()
			if err != nil {
				return err
			}
			return nil
		},
	}

	rootCmd.AddCommand(monitor)
	descr := "yaml detailing what to watch"
	monitor.Flags().StringVar(&monitorNodeYAML, "watch", "", descr)
	monitor.MarkFlagRequired("watch")

}
