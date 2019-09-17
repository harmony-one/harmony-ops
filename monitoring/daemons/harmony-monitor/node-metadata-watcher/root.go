package main

import (
	"github.com/spf13/cobra"
)

var (
	RootCmd = &cobra.Command{
		Use:          "harmony-watchdog",
		Short:        "Monitor stuff",
		SilenceUsage: true,
		Long:         "stuff",

		Run: func(cmd *cobra.Command, args []string) {
			cmd.Help()
		},
	}
)
