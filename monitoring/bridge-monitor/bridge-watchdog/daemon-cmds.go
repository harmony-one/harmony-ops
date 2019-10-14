package main

import (
	"fmt"

	"github.com/spf13/cobra"
	"github.com/takama/daemon"
)

const (
	installD = "install the harmony-watchdog service"
	removeD  = "remove the harmony-watchdog service"
	startD   = "start the harmony-watchdog service"
	stopD    = "stop the harmony-watchdog service"
	statusD  = "check status of the harmony-watchdog service"
	mCmd     = "monitor"
	mFlag    = "yaml-config"
	mDescr   = "yaml detailing what to watch [required]"
)

func (cw *cobraSrvWrapper) install(cmd *cobra.Command, args []string) error {
	// Check that file exists
	r, err := cw.Install(mCmd)
	if err != nil {
		return err
	}
	fmt.Println(r)
	return nil
}

func (cw *cobraSrvWrapper) remove(cmd *cobra.Command, args []string) error {
	r, err := cw.Remove()
	if err != nil {
		return err
	}
	fmt.Println(r)
	return nil
}

func (cw *cobraSrvWrapper) stop(cmd *cobra.Command, args []string) error {
	r, err := cw.Stop()
	if err != nil {
		return err
	}
	fmt.Println(r)
	return nil
}

func (cw *cobraSrvWrapper) status(cmd *cobra.Command, args []string) error {
	r, err := cw.Status()
	if err != nil {
		return err
	}
	fmt.Println(r)
	return nil
}

func (cw *cobraSrvWrapper) start(cmd *cobra.Command, args []string) error {
	_, err := cw.Start()
	if err != nil {
		return err
	}
	return nil
}

func (cw *cobraSrvWrapper) preRunInit(cmd *cobra.Command, args []string) error {
	dm, err := daemon.New(nameFMT, description, dependencies...)
	if err != nil {
		return err
	}
	cw.Service = &Service{dm}
	return nil
}

func (cw *cobraSrvWrapper) doMonitor(cmd *cobra.Command, args []string) error {
	err := cw.monitorNetwork()
	if err != nil {
		return err
	}
	return nil
}

func serviceCmd() *cobra.Command {
	daemonCmd := &cobra.Command{
		Use:               "service",
		Short:             "Control the daemon functionality of bridge-watchd",
		PersistentPreRunE: w.preRunInit,
		Run: func(cmd *cobra.Command, args []string) {
			cmd.Help()
		},
	}

	daemonCmd.AddCommand([]*cobra.Command{{
		Use:   "install",
		Short: installD,
		RunE:  w.install,
	}, {
		Use:   "start",
		Short: startD,
		RunE:  w.start,
	}, {
		Use:   "remove",
		Short: removeD,
		RunE:  w.remove,
	}, {
		Use:   "stop",
		Short: stopD,
		RunE:  w.stop,
	}, {
		Use:   "status",
		Short: statusD,
		RunE:  w.status,
	}}...)

	return daemonCmd
}
