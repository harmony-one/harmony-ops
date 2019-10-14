package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"math/big"
	"net"
	"net/http"
	"os"
	"os/exec"
	"os/signal"
	"path"
	"strings"
	"syscall"
	"time"

	"github.com/PuerkitoBio/goquery"
	"github.com/spf13/cobra"
	"github.com/takama/daemon"
)

const (
	nameFMT     = "bridge-watchd"
	description = "Monitor something -- `%i`"
	spaceSep    = " "
)

var (
	sep       = []byte("\n")
	recordSep = []byte(spaceSep)
	rootCmd   = &cobra.Command{
		Use:          nameFMT,
		SilenceUsage: true,
		Long:         description,
		Run: func(cmd *cobra.Command, args []string) {
			cmd.Help()
		},
	}
	w      *cobraSrvWrapper = &cobraSrvWrapper{nil}
	stdlog *log.Logger
	errlog *log.Logger
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
}

// Manage by daemon commands or run the daemon
func (service *Service) monitorNetwork() error {
	interrupt := make(chan os.Signal, 1)
	signal.Notify(interrupt, os.Interrupt, os.Kill, syscall.SIGTERM)
	// Set up listener for defined host and port
	listener, err := net.Listen("tcp", ":12500")
	if err != nil {
		return err
	}

	go func() {
		// Our polling logic
		expectedBalance, _ := NewDecFromStr("152818477.146499980000000000")
		thresholdBalance, _ := NewDecFromStr("152000000")
		base := NewDecFromBigInt(big.NewInt(100000000))
		tryAgainCounter := 0

		for range time.Tick(time.Duration(60) * time.Second) {
			// If EtherSite fetch fail, wait 10 iterations
			if tryAgainCounter > 0 {
				tryAgainCounter--
				if tryAgainCounter > 0 {
					continue
				}
			}
			// Calculate balance
			bnb, oops := pullBNB()
			if oops != nil {
				// If BNB CLI fetch fail, quit
				notify(pdServiceKey, fmt.Sprintf(`
						BNB CLI fetch failed. %s
						`, oops))
				os.Exit(-1)
			}

			normed := bnb.Quo(base)
			ethSiteBal, err := pullEtherScan()
			if err != nil {
				notify(pdServiceKey, fmt.Sprintf(`
						EtherScan balance fetch failed. %s
						`, err))
				tryAgainCounter = 10
			}

			totalBalance := normed.Add(ethSiteBal)

			diff := totalBalance.Sub(expectedBalance).Abs()

			// Check if below threshold
			if expectedBalance.Sub(diff).LT(thresholdBalance) {
				// Send PagerDuty message
				notify(pdServiceKey, fmt.Sprintf(`
						Mismatch detected!

						BNB Value: %s

						EtherScan Value: %s

						Expected Balance: %s

						Calculated Balance: %s = (%s / %s) + %s

						Deviation: %s
						`, normed, ethSiteBal, expectedBalance, totalBalance, bnb, base, ethSiteBal, diff))
			}
		}
	}()

	// set up channel on which to send accepted connections
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

func versionS() string {
	return fmt.Sprintf(
		"Harmony (C) 2019. %v, version %v-%v (%v %v)",
		path.Base(os.Args[0]), version, commit, builtBy, builtAt,
	)
}

func pullBNB() (Dec, error) {
	here, _ := os.Getwd()
	cmd := exec.Command("./bnbcli", []string{
		"--node=https://dataseed5.defibit.io:443",
		"account",
		"bnb1xwvm73088qrhq8aykcunsq25x2ymxc7pyg7tpj",
		"--chain-id=Binance-Chain-Tigris",
	}...)

	cmd.Dir = here
	out, err := cmd.Output()

	if err != nil {
		return ZeroDec(), err
	}

	type t struct {
		Value struct {
			Base struct {
				Coins []struct {
					Amount string `json:"amount"`
					Denom  string `json:"denom"`
				} `json:"coins"`
			} `json:"base"`
		} `json:"value"`
	}

	query := t{}
	errM := json.Unmarshal(out, &query)
	if errM != nil {
		return ZeroDec(), errM
	}
	const targetCoin = "ONE-5F9"
	for _, coin := range query.Value.Base.Coins {
		if coin.Denom == targetCoin {
			return NewDecFromStr(coin.Amount)
		}
	}
	const oops = "could not find right coin from bnbcli"
	return ZeroDec(), errors.New(oops)
}

const etherScan = "https://etherscan.io/token/0x799a4202c12ca952cb311598a024c80ed371a41e?a=0x6750DB41334e612a6E8Eb60323Cb6579f0a66542"

func pullEtherScan() (Dec, error) {
	res, err := http.Get(etherScan)
	if err != nil {
		return ZeroDec(), err
	}
	defer res.Body.Close()
	if res.StatusCode != 200 {
		msg := fmt.Sprintf("status code error: %d %s", res.StatusCode, res.Status)
		return ZeroDec(), errors.New(msg)
	}

	// Load the HTML document
	doc, err := goquery.NewDocumentFromReader(res.Body)
	if err != nil {
		return ZeroDec(), err
	}

	balance := ""
	doc.Find(".card-body div").Each(func(i int, s *goquery.Selection) {
		t := strings.TrimSpace(s.First().Text())
		t = strings.ReplaceAll(t, "\n", " ")
		if strings.HasPrefix(t, "Balance") {
			tokens := strings.Split(t, " ")
			if len(tokens) > 2 {
				balance = strings.ReplaceAll(tokens[1], ",", "")
			}
		}
	})

	if balance == "" {
		return ZeroDec(), errors.New("Could not find balance on EtherScan")
	}
	return NewDecFromStr(balance)
}

const pdServiceKey = "bc654ea11237451f86714192f692ffe1"

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

}
