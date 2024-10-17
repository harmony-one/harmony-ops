package nodedb

import (
	"crypto/tls"
	"crypto/x509"
	"encoding/json"
	"fmt"
	"github.com/aws/aws-sdk-go-v2/aws"
	"golang.org/x/exp/slices"
	"log"
	"net"
	"net/http"
	"os"
	"time"
)

func ConfigurationServer(serverPort int, serverCertificate string, serverPrivateKey string, serverMtls string) *http.Server {
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
		return &http.Server{
			Addr: fmt.Sprintf("0.0.0.0:%d", serverPort),
			// Good practice to set timeouts to avoid Slowloris attacks.
			WriteTimeout: time.Second * 15,
			ReadTimeout:  time.Second * 15,
			IdleTimeout:  time.Second * 60,
			TLSConfig:    config,
		}
	} else {
		return &http.Server{
			Addr: fmt.Sprintf("0.0.0.0:%d", serverPort),
			// Good practice to set timeouts to avoid Slowloris attacks.
			WriteTimeout: time.Second * 15,
			ReadTimeout:  time.Second * 15,
			IdleTimeout:  time.Second * 60,
		}
	}
}

func CheckIPv4AddressType(ip string) bool {
	if net.ParseIP(ip) == nil {
		return false
	}
	for i := 0; i < len(ip); i++ {
		switch ip[i] {
		case '.':
			return true
		}
	}
	return false
}

func InfoIP(hasTLS bool, serverPort int) {
	ifaces, errorInterfaces := net.Interfaces()
	if errorInterfaces != nil {
		log.Println(errorInterfaces.Error())
	} else {
		for _, i := range ifaces {
			addrs, errorAddrs := i.Addrs()
			if errorAddrs != nil {
				log.Println(errorAddrs.Error())
			} else {
				// handle err
				for _, addr := range addrs {
					var ip net.IP
					switch v := addr.(type) {
					case *net.IPNet:
						ip = v.IP
					case *net.IPAddr:
						ip = v.IP
					}
					if CheckIPv4AddressType(ip.String()) {
						if (hasTLS && serverPort == 443) || (!hasTLS && serverPort == 80) {
							if hasTLS {
								log.Println(fmt.Sprintf("Listenning %s://%s", "https", ip.String()))
							} else {
								log.Println(fmt.Sprintf("Listenning %s://%s", "http", ip.String()))
							}
						} else {
							if hasTLS {
								log.Println(fmt.Sprintf("Listenning %s://%s:%d", "https", ip.String(), serverPort))
							} else {
								log.Println(fmt.Sprintf("Listenning %s://%s:%d", "http", ip.String(), serverPort))
							}
						}
					}
				}
			}
		}
	}
}

func AllowClient(clientIpFile string, clientIp string) (*bool, error) {
	clientIpContent, errorReadFile := os.ReadFile(clientIpFile)

	if errorReadFile != nil {
		return nil, errorReadFile
	}

	var allowIps []string

	errorUnmarshal := json.Unmarshal(clientIpContent, &allowIps)

	if errorUnmarshal != nil {
		return nil, errorUnmarshal
	}

	return aws.Bool(slices.Contains(allowIps, clientIp)), nil
}
