package main

import (
	"encoding/json"
	"bytes"
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
	"github.com/pkg/errors"
)

const (
	nameFMT      = "bridge-watchd"
	description  = "Monitor bridge discrepencies"
	spaceSep     = " "
	pdServiceKey = "bc654ea11237451f86714192f692ffe1"
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
	bnbcliPath string
	expectedBal int64
	stdLog *log.Logger
	errLog *log.Logger
	// Add services here that we might want to depend on, see all services on
	// the machine with systemctl list-unit-files
	dependencies    = []string{}
	errNoBalance    = errors.New("balance not found on EtherScan")
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
		expectedBalance := NewDecFromBigInt(big.NewInt(expectedBal))
		threshold := NewDecFromBigInt(big.NewInt(10))
		base := NewDecFromBigInt(big.NewInt(100000000))
		lastDiff := ZeroDec()
		tryAgainCounter := 0
		etherFailCounter := 0
		reportCounter := 0
		wifiDowntime := time.Time{}

		for range time.Tick(time.Duration(200) * time.Second) {
			// Track 30 minutes regardless of success
			reportCounter++
			// If EtherSite fetch fail, wait 10 iterations
			if tryAgainCounter > 0 {
				tryAgainCounter--
				if tryAgainCounter > 0 {
					continue
				}
			}
			// Check wifi by pinging Google DNS
			client := http.Client{
				Timeout: 5 * time.Second,
			}
			_, err := client.Get("https://8.8.8.8")
			if err != nil {
				errLog.Println("Google request failed.")
				wifiDowntime = time.Now()
				tryAgainCounter = 10
				continue
			} else {
				// Skip until wifi actually goes down once
				if !wifiDowntime.IsZero() {
					errLog.Printf("Google request success. Total time down: %s\n", time.Now().Sub(wifiDowntime))
					wifiDowntime = time.Time{}
				}
			}
			// Calculate balance
			bnb, oops := pullBNB()
			if oops != nil {
				// If BNB CLI fetch fail
				errLog.Println(oops)
				tryAgainCounter = 10
				continue
			}

			normed := bnb.Quo(base)
			data, err := reqEtherScan()
			if err != nil {
				etherFailCounter++
				if etherFailCounter > 6 {
					// If failing for 1 hour
					errLog.Println(err)
					etherFailCounter = 0
				}
				tryAgainCounter = 10
				continue
			}
			ethSiteBal, error := pullEtherScan(data)
			if error != nil {
				etherFailCounter++
				if etherFailCounter > 6 {
					errLog.Println(error)
					etherFailCounter = 0
				}
				tryAgainCounter = 10
				continue
			} else {
				// If balance fetch fully working, reset counter
				etherFailCounter = 0
			}

			totalBalance := normed.Add(ethSiteBal)
			diff := totalBalance.Sub(expectedBalance).Abs()
			if reportCounter > 30 {
				stdLog.Printf(`
Expected Balance: %s

Calculated Balance: %s = (%s / %s) + %s

Deviation: %s
						`, expectedBalance, totalBalance, bnb, base, ethSiteBal, diff)
				reportCounter = 0
			}
			// Check if below threshold
			if diff.GT(threshold) {
				if !diff.Equal(lastDiff) {
				 	// Send PagerDuty message
				 	e := notify(pdServiceKey, fmt.Sprintf(`
Mismatch detected!

BNB Value: %s

EtherScan Value: %s

Expected Balance: %s

Calculated Balance: %s = (%s / %s) + %s

Deviation: %s
`, normed, ethSiteBal, expectedBalance, totalBalance, bnb, base, ethSiteBal, diff))
					if e != nil {
						stdLog.Println(e)
					}
					lastDiff = diff
				}
			} else {
				lastDiff = ZeroDec()
			}
		}
	}()

	// set up channel on which to send accepted connections
	// loop work cycle with accept connections or interrupt
	// by system signal
	for {
		select {
		case killSignal := <-interrupt:
			stdLog.Println("Got signal:", killSignal)
			stdLog.Println("Stoping listening on ", listener.Addr())
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
	cmd := exec.Command(bnbcliPath, []string{
		"--node=https://dataseed5.defibit.io:443",
		"account",
		"bnb1xwvm73088qrhq8aykcunsq25x2ymxc7pyg7tpj",
		"--chain-id=Binance-Chain-Tigris",
	}...)

	cmd.Dir = here
	out, err := cmd.CombinedOutput()

	if err != nil {
		return ZeroDec(), errors.Wrapf(err, "raw output: %s", out)
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

func reqEtherScan() (string, error) {
	res, err := http.Get(etherScan)
	if err != nil {
		return "", err
	}
	defer res.Body.Close()
	if res.StatusCode != 200 {
		msg := fmt.Sprintf("status code error: %d %s", res.StatusCode, res.Status)
		return "", errors.New(msg)
	}

	buf := new(bytes.Buffer)
	buf.ReadFrom(res.Body)

	return buf.String(), nil
}

func pullEtherScan(data string) (Dec, error) {
	// Load the HTML document
	doc, err := goquery.NewDocumentFromReader(strings.NewReader(data))
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
		return ZeroDec(), errNoBalance
	}
	return NewDecFromStr(balance)
}

func init() {
	stdLog = log.New(os.Stdout, "", log.Ldate|log.Ltime)
	errLog = log.New(os.Stderr, "", log.Ldate|log.Ltime)
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
