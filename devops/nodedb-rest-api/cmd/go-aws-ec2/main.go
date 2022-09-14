package main

import (
	"context"
	"crypto/tls"
	"crypto/x509"
	"encoding/json"
	"flag"
	"fmt"
	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/credentials"
	"github.com/aws/aws-sdk-go-v2/service/ec2"
	"log"
	"net"
	"net/http"
	"nodedb-rest-api/common"
	"os"
	"os/signal"
	"time"

	"github.com/gorilla/mux"
)

var serverCertificate string
var serverPrivateKey string
var serverMtls string

var gracefulTimeout time.Duration
var clientIpFile string
var serverPort int

var accessKey string
var secretAccessKey string
var sessionToken string

var _accessKey string
var _secretAccessKey string
var _sessionToken string

func main() {
	flag.StringVar(&serverCertificate, "server-certificate", "", "")
	flag.StringVar(&serverPrivateKey, "server-private-key", "", "")
	flag.StringVar(&serverMtls, "server-mtls", "", "")

	flag.StringVar(&serverCertificate, "server-certificate", "", "")
	flag.StringVar(&serverPrivateKey, "server-private-key", "", "")

	flag.DurationVar(&gracefulTimeout, "graceful-timeout", time.Second*15, "the duration for which the server gracefully gracefulTimeout for existing connections to finish - e.g. 15s or 1m")
	flag.StringVar(&clientIpFile, "client-ip", "client-ip.json", "client ip which allow to access")
	flag.IntVar(&serverPort, "server-port", 8080, "server port")

	flag.StringVar(&accessKey, "access-key", "", "")
	flag.StringVar(&secretAccessKey, "secret-access-key", "", "")
	flag.StringVar(&sessionToken, "session-token", "", "")

	_accessKey = os.Getenv("AWS_ACCESS_KEY_ID")
	_secretAccessKey = os.Getenv("AWS_SECRET_ACCESS_KEY")
	_sessionToken = os.Getenv("AWS_SESSION_TOKEN")

	flag.Parse()

	if accessKey != "" {
		_accessKey = accessKey
	}

	if secretAccessKey != "" {
		_secretAccessKey = secretAccessKey
	}

	if sessionToken != "" {
		_sessionToken = sessionToken
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
	_context := context.Background()

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

	var client *ec2.Client = nil
	if _accessKey != "" && _secretAccessKey != "" {
		_config := aws.Config{
			Region:      "us-west-2",
			Credentials: credentials.NewStaticCredentialsProvider(_accessKey, _secretAccessKey, _sessionToken),
		}
		client = ec2.NewFromConfig(_config)
	} else {
		_config, errorLoadDefaultConfig := config.LoadDefaultConfig(_context, func(options *config.LoadOptions) error {
			options.Region = "us-west-2"
			return nil
		})

		if errorLoadDefaultConfig != nil {
			w.WriteHeader(http.StatusInternalServerError)
			_, _ = fmt.Fprintln(w, errorLoadDefaultConfig.Error())
			return
		}

		client = ec2.NewFromConfig(_config)
	}

	_regions, errorDescribeRegions := client.DescribeRegions(_context, &ec2.DescribeRegionsInput{})

	if errorDescribeRegions != nil {
		w.WriteHeader(http.StatusInternalServerError)
		_, _ = fmt.Fprintln(w, errorDescribeRegions.Error())
		return
	}

	var _ec2s []common.Ec2Dto

	for _, region := range _regions.Regions {

		_describeInstancesInput := &ec2.DescribeInstancesInput{}

	NextRequest:

		_describeInstancesOutput, errorDescribeInstances := client.DescribeInstances(_context, _describeInstancesInput, func(options *ec2.Options) {
			options.Region = *region.RegionName
		})

		if errorDescribeInstances == nil {
			for _, reservation := range _describeInstancesOutput.Reservations {
				for _, instance := range reservation.Instances {
					_instanceId := *instance.InstanceId
					_publicIpAddress := ""
					_privateIpAddress := ""
					_tagName := ""
					if instance.PublicIpAddress != nil {
						_publicIpAddress = *instance.PublicIpAddress
					}
					if instance.PrivateIpAddress != nil {
						_privateIpAddress = *instance.PrivateIpAddress
					}
					for _, tag := range instance.Tags {
						if tag.Key != nil && *tag.Key == "Name" && tag.Value != nil {
							_tagName = *tag.Value
						}
					}
					_ec2s = append(_ec2s, common.Ec2Dto{
						TagName:    _tagName,
						InstanceId: _instanceId,
						PublicIP:   _publicIpAddress,
						PrivateIP:  _privateIpAddress,
						Region:     *region.RegionName,
					})
				}
			}
		} else {
			println(errorDescribeInstances.Error())
		}

		if _describeInstancesOutput.NextToken != nil {
			_describeInstancesInput = &ec2.DescribeInstancesInput{}
			_describeInstancesInput.NextToken = _describeInstancesOutput.NextToken
			goto NextRequest
		}
	}

	_json, errorMarshalIndent := json.MarshalIndent(_ec2s, "", "  ")

	if errorMarshalIndent != nil {
		w.WriteHeader(http.StatusInternalServerError)
		_, _ = fmt.Fprintln(w, errorMarshalIndent.Error())
		return
	}

	w.WriteHeader(http.StatusOK)
	w.Header().Add("Content-Type", "application/json")
	_, _ = w.Write(_json)
}
