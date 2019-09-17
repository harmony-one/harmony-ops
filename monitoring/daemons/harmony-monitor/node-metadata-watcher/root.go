package main

import (
	"errors"
	"fmt"
	"log"
	"net"
	"os"
	"os/signal"
	"path"
	"syscall"

	"github.com/spf13/cobra"
	"github.com/takama/daemon"
)

const (
	name        = "harmony-watchdog"
	description = "Monitor the Harmony blockchain"
	port        = ":9977"
)

//    dependencies that are NOT required by the service, but might be used
var (
	stdlog, errlog *log.Logger
	dependencies   = []string{"dummy.service"}
)

// Service has embedded daemon
type Service struct {
	daemon.Daemon
}

// Manage by daemon commands or run the daemon
func (service *Service) Manage() error {
	// service.Install()
	// service.Remove()
	// service.Start()
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
	go acceptConnection(listener, listen)
	// loop work cycle with accept connections or interrupt
	// by system signal
	for {
		select {
		case conn := <-listen:
			go handleClient(conn)
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

	// never happen, but need to complete code
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

func handleClient(client net.Conn) {
	for {
		buf := make([]byte, 4096)
		numbytes, err := client.Read(buf)
		if numbytes == 0 || err != nil {
			return
		}
		client.Write(buf[:numbytes])
	}
}

func init() {
	stdlog = log.New(os.Stdout, "", log.Ldate|log.Ltime)
	errlog = log.New(os.Stderr, "", log.Ldate|log.Ltime)
	rootCmd.AddCommand(&cobra.Command{
		Use:   "version",
		Short: "Show version",
		Run: func(cmd *cobra.Command, args []string) {
			fmt.Fprintf(os.Stderr,
				"Harmony (C) 2019. %v, version %v-%v (%v %v)\n",
				path.Base(os.Args[0]), version, commit, builtBy, builtAt)
			os.Exit(0)
		},
	})
	rootCmd.AddCommand(&cobra.Command{
		Use:   "monitor",
		Short: "watch the blockchain for problems",
		RunE: func(cmd *cobra.Command, args []string) error {
			srv, err := daemon.New(name, description, dependencies...)
			if err != nil {
				return err
			}
			service := &Service{srv}
			err = service.Manage()
			if err != nil {
				return err
			}
			return nil

		},
	})

}

var (
	rootCmd = &cobra.Command{
		Use:          "harmony-watchdog",
		SilenceUsage: true,
		Long:         "Monitor a blockchain",
		Run: func(cmd *cobra.Command, args []string) {
			cmd.Help()
		},
	}
)
