package main

import (
	"fmt"
	"sync"

	"github.com/spf13/cobra"
	"github.com/takama/daemon"
)

const (
	installD           = "install the harmony-watchdogd service"
	removeD            = "remove the harmony-watchdogd service"
	startD             = "start the harmony-watchdogd service"
	stopD              = "stop the harmony-watchdogd service"
	statusD            = "check status of the harmony-watchdogd service"
	mCmd               = "monitor"
	mMachineIPValidate = "validate-ip-in-shard"
	mFlag              = "yaml-config"
	mDescr             = "yaml detailing what to watch [required]"
)

func (cw *cobraSrvWrapper) install(cmd *cobra.Command, args []string) error {
	// Check that file exists
	r, err := cw.Install(mCmd, "--"+mFlag, monitorNodeYAML)
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

// NOTE Important function because downstream commands assume results of it
func (cw *cobraSrvWrapper) preRunInit(cmd *cobra.Command, args []string) error {
	instr, err := newInstructions(monitorNodeYAML)
	if err != nil {
		return err
	}
	dm, err := daemon.New(
		fmt.Sprintf(nameFMT, instr.Network.TargetChain),
		description,
		dependencies...,
	)
	if err != nil {
		return err
	}
	cw.Service = &Service{dm, nil, instr}
	return nil
}

func (cw *cobraSrvWrapper) start(cmd *cobra.Command, args []string) error {
	r, err := cw.Start()
	if err != nil {
		return err
	}
	fmt.Println(r)
	return nil
}

func (cw *cobraSrvWrapper) doMonitor(cmd *cobra.Command, args []string) error {
	lock := &sync.Mutex{}
	cw.monitor = &monitor{
		chain:             cw.Network.TargetChain,
		lock:              lock,
		cond:              sync.NewCond(lock),
		consensusProgress: map[string]bool{},
	}
	return cw.monitorNetwork()
}

func (cw *cobraSrvWrapper) validateShardFileWithReality(
	cmd *cobra.Command, args []string,
) error {
	return cw.compareIPInShardFileWithNodes()
}

func monitorCmd() *cobra.Command {
	monitorCmd := &cobra.Command{
		Use:               mCmd,
		Short:             "start watching the blockchain for problems",
		PersistentPreRunE: w.preRunInit,
		RunE:              w.doMonitor,
	}
	monitorCmd.Flags().StringVar(&monitorNodeYAML, mFlag, "", mDescr)
	monitorCmd.MarkFlagRequired(mFlag)
	return monitorCmd
}

func validateMachineIPList() *cobra.Command {
	const msg = "check if node in IP of shard file does not match what node reports"
	validateShardIP := &cobra.Command{
		Use:               mMachineIPValidate,
		Short:             msg,
		PersistentPreRunE: w.preRunInit,
		RunE:              w.validateShardFileWithReality,
	}
	validateShardIP.Flags().StringVar(&monitorNodeYAML, mFlag, "", mDescr)
	validateShardIP.MarkFlagRequired(mFlag)
	return validateShardIP
}

func serviceCmd() *cobra.Command {
	daemonCmd := &cobra.Command{
		Use:               "service",
		Short:             "Control the daemon functionality of harmony-watchdogd",
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
	install.Flags().StringVar(&monitorNodeYAML, mFlag, "", mDescr)
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
