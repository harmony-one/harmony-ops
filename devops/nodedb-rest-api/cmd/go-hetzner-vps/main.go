package main

import (
	"context"
	"crypto/tls"
	"crypto/x509"
	"encoding/json"
	"flag"
	"fmt"
	"github.com/hetznercloud/hcloud-go/hcloud"
	"log"
	"net"
	"net/http"
	"nodedb-rest-api/common"
	"os"
	"os/signal"
	"time"

	"github.com/gorilla/mux"
)

var gracefulTimeout time.Duration
var clientIpFile string
var serverPort int

var serverCertificate string
var serverPrivateKey string
var serverMtls string

var accessToken string

var _accessToken string

func main() {
	flag.StringVar(&serverCertificate, "server-certificate", "", "")
	flag.StringVar(&serverPrivateKey, "server-private-key", "", "")
	flag.StringVar(&serverMtls, "server-mtls", "", "")

	flag.DurationVar(&gracefulTimeout, "graceful-timeout", time.Second*15, "the duration for which the server gracefully gracefulTimeout for existing connections to finish - e.g. 15s or 1m")
	flag.StringVar(&clientIpFile, "client-ip", "client-ip.json", "client ip which allow to access")
	flag.IntVar(&serverPort, "server-port", 8080, "server port")

	flag.StringVar(&accessToken, "access-token", "", "")

	_accessToken = os.Getenv("HCLOUD_ACCESS_TOKEN")

	flag.Parse()

	if accessToken != "" {
		_accessToken = accessToken
	}

	r := mux.NewRouter()

	// Add your routes as needed
	r.HandleFunc("/", Home)

	http.Handle("/", r)

	var srv *http.Server

	if serverCertificate != "" && serverPrivateKey != "" {
		var config *tls.Config
		if serverMtls != "" {
			mtlsCertificate, errorReadFile := os.ReadFile(serverMtls)
			if errorReadFile != nil {
				log.Println(errorReadFile.Error())
			} else {
				certPool := x509.NewCertPool()
				certPool.AppendCertsFromPEM(mtlsCertificate)
				config = &tls.Config{
					ClientCAs:  certPool,
					ClientAuth: tls.RequireAndVerifyClientCert,
				}
			}
		}
		srv = &http.Server{
			Addr: fmt.Sprintf("0.0.0.0:%d", serverPort),
			// Good practice to set timeouts to avoid Slowloris attacks.
			WriteTimeout: time.Second * 15,
			ReadTimeout:  time.Second * 15,
			IdleTimeout:  time.Second * 60,
			TLSConfig:    config,
			Handler:      r, // Pass our instance of gorilla/mux in.
		}
	} else {
		srv = &http.Server{
			Addr: fmt.Sprintf("0.0.0.0:%d", serverPort),
			// Good practice to set timeouts to avoid Slowloris attacks.
			WriteTimeout: time.Second * 15,
			ReadTimeout:  time.Second * 15,
			IdleTimeout:  time.Second * 60,
			Handler:      r, // Pass our instance of gorilla/mux in.
		}
	}

	// Run our server in a goroutine so that it doesn't block.
	go func() {
		common.InfoIP(serverPort)
		if serverCertificate != "" && serverPrivateKey != "" {
			if errorListenAndServe := srv.ListenAndServeTLS(serverCertificate, serverPrivateKey); errorListenAndServe != nil {
				log.Println(errorListenAndServe.Error())
			}
		} else {
			if errorListenAndServe := srv.ListenAndServe(); errorListenAndServe != nil {
				log.Println(errorListenAndServe.Error())
			}
		}
	}()

	c := make(chan os.Signal, 1)
	// We'll accept graceful shutdowns when quit via SIGINT (Ctrl+C)
	// SIGKILL, SIGQUIT or SIGTERM (Ctrl+/) will not be caught.
	signal.Notify(c, os.Interrupt)

	// Block until we receive our signal.
	<-c

	// Create a deadline to gracefulTimeout for.
	ctx, cancel := context.WithTimeout(context.Background(), gracefulTimeout)
	defer cancel()
	// Doesn't block if no connections, but will otherwise gracefulTimeout
	// until the timeout deadline.
	errorShutdown := srv.Shutdown(ctx)

	if errorShutdown != nil {
		println(errorShutdown.Error())
	}
	// Optionally, you could run srv.Shutdown in a goroutine and block on
	// <-ctx.Done() if your application should gracefulTimeout for other services
	// to finalize based on context cancellation.
	log.Println("shutting down")
	os.Exit(0)
}

func Home(w http.ResponseWriter, r *http.Request) {
	clientIp, _, errorSplitHostPort := net.SplitHostPort(r.RemoteAddr)
	if errorSplitHostPort != nil {
		w.WriteHeader(http.StatusInternalServerError)
		_, _ = fmt.Fprintln(w, errorSplitHostPort.Error())
		return
	}

	allow, errorAllowClient := common.AllowClient(clientIpFile, clientIp)

	if errorAllowClient != nil {
		w.WriteHeader(http.StatusInternalServerError)
		_, _ = fmt.Fprintln(w, errorAllowClient.Error())
		return
	}

	if !*allow {
		w.WriteHeader(http.StatusForbidden)
		_, _ = fmt.Fprintf(w, "Your IP Address %s is not allow", clientIp)
		return
	}

	client := hcloud.NewClient(hcloud.WithToken(_accessToken))

	_context := context.Background()

	var _servers []common.HetznerDto

	var _listServers []hcloud.Server

	_listOptions := hcloud.ServerListOpts{
		ListOpts: hcloud.ListOpts{
			PerPage: 200,
		},
	}

	// to be tested
	servers, _, errorList := client.Server.List(_context, _listOptions)
	if errorList != nil {
		w.WriteHeader(http.StatusInternalServerError)
		_, _ = fmt.Fprintln(w, errorSplitHostPort.Error())
		return
	}

	// append the current page's droplets to our list
	for _, server := range servers {
		_listServers = append(_listServers, *server)
	}

	for _, server := range _listServers {
		server.PrivateNet[0].IP.String()
		_publicIPv6Address := server.PublicNet.IPv6.IP.String()
		_publicIPv4Address := server.PublicNet.IPv4.IP.String()
		_region := ""
		var _privateIp []string

		if server.PrivateNet != nil {
			for _, privateNet := range server.PrivateNet {
				_privateIp = append(_privateIp, privateNet.IP.String())
			}
		}

		if server.Datacenter != nil {
			_region = server.Datacenter.Name
		}

		_servers = append(_servers, common.HetznerDto{
			Id:         server.ID,
			Region:     _region,
			Name:       server.Name,
			PrivateIP:  _privateIp,
			PublicIPv4: _publicIPv4Address,
			PublicIPv6: _publicIPv6Address,
		})
	}

	_json, errorMarshalIndent := json.MarshalIndent(_servers, "", "  ")

	if errorMarshalIndent != nil {
		w.WriteHeader(http.StatusInternalServerError)
		_, _ = fmt.Fprintln(w, errorMarshalIndent.Error())
		return
	}

	w.WriteHeader(http.StatusOK)
	w.Header().Add("Content-Type", "application/json")
	_, _ = w.Write(_json)
}
