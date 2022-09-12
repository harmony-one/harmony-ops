package common

import (
	"encoding/json"
	"fmt"
	"github.com/aws/aws-sdk-go-v2/aws"
	"golang.org/x/exp/slices"
	"log"
	"net"
	"os"
)

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

func InfoIP(serverPort int) {
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
						if serverPort == 80 {
							log.Println(fmt.Sprintf("Listenning %s://%s", "http", ip.String()))
						} else {
							log.Println(fmt.Sprintf("Listenning %s://%s:%d", "http", ip.String(), serverPort))
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
