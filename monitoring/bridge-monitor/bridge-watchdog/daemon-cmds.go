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
	dm, err := daemon.New(nameFMT, description, dependencies...)
	if err != nil {
		return err
	}
	cw.Service = &Service{dm}
	_, err = cw.Start()
	if err != nil {
		return err
	}

	err = cw.monitorNetwork()

	return nil
}

func init() {
	install := &cobra.Command{
		Use:   "install",
		Short: installD,
		RunE:  w.install,
	}
	rootCmd.AddCommand([]*cobra.Command{install, {
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
}
