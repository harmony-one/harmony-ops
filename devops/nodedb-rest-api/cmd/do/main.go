package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"github.com/digitalocean/godo"
	"io"
	"log"
	"net"
	"net/http"
	"net/url"
	"nodedb-rest-api/pkg/nodedb"
	"os"
	"os/signal"
	"strings"
	"time"

	"github.com/gorilla/mux"
)

var gracefulTimeout time.Duration

var serverCertificate string
var serverPrivateKey string
var serverMtls string

var clientIpFile string
var configurationFile string
var serverPort int

var accessToken string
var refreshToken string

func main() {
	flag.IntVar(&serverPort, "server-port", 8080, "server port")
	flag.StringVar(&serverCertificate, "server-certificate", "", "")
	flag.StringVar(&serverPrivateKey, "server-private-key", "", "")
	flag.StringVar(&serverMtls, "server-mtls", "", "")

	flag.DurationVar(&gracefulTimeout, "graceful-timeout", time.Second*15, "the duration for which the server gracefully gracefulTimeout for existing connections to finish - e.g. 15s or 1m")

	flag.StringVar(&clientIpFile, "client-ip", "client-ip.json", "client ip which allow to access")
	flag.StringVar(&configurationFile, "configuration", "configuration.json", "configuration")

	flag.Parse()

	r := mux.NewRouter()

	// Add your routes as needed
	r.HandleFunc("/", Home)
	r.HandleFunc("/callback", Callback)

	http.Handle("/", r)

	go RefreshToken()

	var hasTLS = false
	if serverCertificate != "" && serverPrivateKey != "" {
		hasTLS = true
	}

	var srv = nodedb.ConfigurationServer(serverPort, serverCertificate, serverPrivateKey, serverMtls)
	srv.Handler = r

	// Run our server in a goroutine so that it doesn't block.
	go func() {
		nodedb.InfoIP(hasTLS, serverPort)
		if hasTLS {
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

	allow, errorAllowClient := nodedb.AllowClient(clientIpFile, clientIp)

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

	if accessToken == "" {

		configuration, errorLookupConfiguration := LookupConfiguration()
		if errorLookupConfiguration != nil {
			w.WriteHeader(http.StatusInternalServerError)
			_, _ = fmt.Fprintln(w, errorLookupConfiguration.Error())
			return
		}

		http.Redirect(w, r, fmt.Sprintf("%s/authorize?client_id=%s&redirect_uri=%s&response_type=code", configuration.DigitalOcean.OAuthUrl, configuration.DigitalOcean.ClientId, configuration.RedirectUri), http.StatusSeeOther)
		return
	}

	client := godo.NewFromToken(accessToken)

	_context := context.Background()

	var _droplets []nodedb.DigitalOceanDto

	var _listDroplets []godo.Droplet

	_listOptions := &godo.ListOptions{}
	for {
		droplets, resp, errorList := client.Droplets.List(_context, _listOptions)
		if errorList != nil {
			w.WriteHeader(http.StatusInternalServerError)
			_, _ = fmt.Fprintln(w, errorSplitHostPort.Error())
			return
		}

		// append the current page's droplets to our list
		_listDroplets = append(_listDroplets, droplets...)

		// if we are at the last page, break out the for loop
		if resp.Links == nil || resp.Links.IsLastPage() {
			break
		}

		page, errorCurrentPage := resp.Links.CurrentPage()
		if errorCurrentPage != nil {
			w.WriteHeader(http.StatusInternalServerError)
			_, _ = fmt.Fprintln(w, errorCurrentPage.Error())
			return
		}

		// set the page we want for the next request
		_listOptions.Page = page + 1
	}

	for _, droplet := range _listDroplets {
		_publicIPv4Address, _ := droplet.PublicIPv4()
		_publicIPv6Address, _ := droplet.PublicIPv6()
		_privateIPv4Address, _ := droplet.PrivateIPv4()
		_droplets = append(_droplets, nodedb.DigitalOceanDto{
			Id:          droplet.ID,
			Region:      droplet.Region.Name,
			Name:        droplet.Name,
			PrivateIPv4: _privateIPv4Address,
			PublicIPv4:  _publicIPv4Address,
			PublicIPv6:  _publicIPv6Address,
			Tags:        droplet.Tags,
		})
	}

	_json, errorMarshalIndent := json.MarshalIndent(_droplets, "", "  ")

	if errorMarshalIndent != nil {
		w.WriteHeader(http.StatusInternalServerError)
		_, _ = fmt.Fprintln(w, errorMarshalIndent.Error())
		return
	}

	w.WriteHeader(http.StatusOK)
	w.Header().Add("Content-Type", "application/json")
	_, _ = w.Write(_json)
}

func Callback(w http.ResponseWriter, r *http.Request) {
	clientIp, _, errorSplitHostPort := net.SplitHostPort(r.RemoteAddr)
	if errorSplitHostPort != nil {
		w.WriteHeader(http.StatusInternalServerError)
		_, _ = fmt.Fprintln(w, errorSplitHostPort.Error())
		return
	}

	allow, errorAllowClient := nodedb.AllowClient(clientIpFile, clientIp)

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

	configuration, errorLookupConfiguration := LookupConfiguration()
	if errorLookupConfiguration != nil {
		w.WriteHeader(http.StatusInternalServerError)
		_, _ = fmt.Fprintln(w, errorLookupConfiguration.Error())
		return
	}

	code := r.URL.Query().Get("code")

	data := url.Values{}
	data.Set("grant_type", "authorization_code")
	data.Set("code", code)
	data.Set("client_id", configuration.DigitalOcean.ClientId)
	data.Set("client_secret", configuration.DigitalOcean.ClientSecret)
	data.Set("redirect_uri", configuration.RedirectUri)
	encode := data.Encode()
	body := strings.NewReader(encode)

	client := &http.Client{}
	request, errorNewRequest := http.NewRequest(http.MethodPost, fmt.Sprintf("%s/token", configuration.DigitalOcean.OAuthUrl), body)
	if errorNewRequest != nil {
		w.WriteHeader(http.StatusInternalServerError)
		_, _ = fmt.Fprintln(w, errorNewRequest.Error())
		return
	}
	request.Header.Add("Content-Type", "application/x-www-form-urlencoded")

	resp, errorDo := client.Do(request)

	if errorDo != nil {
		w.WriteHeader(http.StatusInternalServerError)
		_, _ = fmt.Fprintln(w, errorDo.Error())
		return
	}

	bodyContent, errorReadAll := io.ReadAll(resp.Body)

	if errorReadAll != nil {
		w.WriteHeader(http.StatusInternalServerError)
		_, _ = fmt.Fprintln(w, errorReadAll.Error())
		return
	}

	var oauthToken nodedb.DigitalOceanOAuthToken

	errorUnmarshal1 := json.Unmarshal(bodyContent, &oauthToken)

	if errorUnmarshal1 != nil {
		w.WriteHeader(http.StatusInternalServerError)
		_, _ = fmt.Fprintln(w, errorUnmarshal1.Error())
		return
	}

	accessToken = oauthToken.AccessToken
	refreshToken = oauthToken.RefreshToken

	http.Redirect(w, r, configuration.HomeUri, http.StatusSeeOther)
}

func RefreshToken() {
	for {
		if refreshToken != "" {

			configuration, errorLookupConfiguration := LookupConfiguration()
			if errorLookupConfiguration != nil {
				log.Println(errorLookupConfiguration.Error())
			} else {

				data := url.Values{}
				data.Set("grant_type", "refresh_token")
				data.Set("refresh_token", refreshToken)
				encode := data.Encode()
				body := strings.NewReader(encode)

				client := &http.Client{}
				request, errorNewRequest := http.NewRequest(http.MethodPost, fmt.Sprintf("%s/token", configuration.DigitalOcean.OAuthUrl), body)
				if errorNewRequest != nil {
					log.Println(errorNewRequest.Error())
				} else {
					request.Header.Add("Content-Type", "application/x-www-form-urlencoded")

					resp, errorDo := client.Do(request)

					if errorDo != nil {
						log.Println(errorDo.Error())
					} else {
						bodyContent, errorReadAll := io.ReadAll(resp.Body)
						if errorReadAll != nil {
							log.Println(errorReadAll.Error())
						} else {
							var oauthToken nodedb.DigitalOceanOAuthToken
							errorUnmarshal1 := json.Unmarshal(bodyContent, &oauthToken)
							if errorUnmarshal1 != nil {
								log.Println(errorUnmarshal1.Error())
							} else {
								accessToken = oauthToken.AccessToken
								refreshToken = oauthToken.RefreshToken
							}
						}
					}
				}
			}
		}
		time.Sleep(5 * 60 * 1000 * time.Millisecond)
	}
}

func LookupConfiguration() (*nodedb.ConfigurationDto, error) {
	configurationContent, errorReadFile := os.ReadFile(configurationFile)
	if errorReadFile != nil {
		return nil, errorReadFile
	}

	var dto nodedb.ConfigurationDto
	errorUnmarshal := json.Unmarshal(configurationContent, &dto)

	if errorUnmarshal != nil {
		return nil, errorUnmarshal
	}

	return &dto, nil
}
