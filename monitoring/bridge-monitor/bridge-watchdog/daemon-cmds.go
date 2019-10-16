package main

import (
	"fmt"
	"os"
	"errors"

	"github.com/spf13/cobra"
	"github.com/takama/daemon"
)

const (
	installD = "install the bridge-watchdog service"
	removeD  = "remove the bridge-watchdog service"
	startD   = "start the bridge-watchdog service"
	stopD    = "stop the bridge-watchdog service"
	statusD  = "check status of the bridge-watchdog service"
	mCmd     = "monitor"
	mFlag    = "bnbPath"
	mDescr   = "path to bnbcli binary [required]"
)

func (cw *cobraSrvWrapper) install(cmd *cobra.Command, args []string) error {
	// Check that file exist
	_, e := os.Stat(bnbcliPath)
	if os.IsNotExist(e) {
		return errors.New("invalid bnbcli path provided")
	}
	r, err := cw.Install(mCmd, "--" + mFlag, bnbcliPath)
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

func monitorCmd() *cobra.Command {
	monCmd := &cobra.Command {
			Use:               mCmd,
			Short:             "start watching the bnbbridge for discrepency",
			PersistentPreRunE: w.preRunInit,
			RunE:              w.doMonitor,
	}
	monCmd.Flags().StringVar(&bnbcliPath, mFlag, "", mDescr)
	monCmd.MarkFlagRequired(mFlag)
	return monCmd
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
	install := &cobra.Command{
		Use:   "install",
		Short: installD,
		RunE:  w.install,
	}
	install.Flags().StringVar(&bnbcliPath, mFlag, "", mDescr)
	install.MarkFlagRequired(mFlag)
	daemonCmd.AddCommand([]*cobra.Command{install, {
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
