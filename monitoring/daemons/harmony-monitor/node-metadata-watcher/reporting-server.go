package main

import (
	"encoding/json"
	"fmt"
	"html/template"
	"net/http"
)

const (
	reportTemplate = `
<!DOCTYPE html>
<html lang="en">
  <meta charset="utf-8" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=0" name="viewport">
  <head>
<style>
* {margin:0;padding:0;}

 .CenteredReport {
   display:flex;
 }

 .NodeDetail {
  background-color:aliceblue;
  display:flex;
  padding: 10px;
}
</style>

  </head>
  <body>
<div class="CenteredReport">
  <header>{{.Title}}</header>
  <p>First report</p>

{{range .Nodes}}
<div class="NodeDetail">
  <p>BLS public key: {{.BLSPublicKey}} </p>
  <p>Version: {{.Version}} </p>
  <p>NetworkType: {{.NetworkType}} </p>
  <p>ChainID: {{.ChainID}} </p>
</div>
{{end}}
</div>


  </body>
</html>
`
)

type nodeMetadata struct {
	BLSPublicKey string `json:"blskey"`
	Version      string `json:"version"`
	NetworkType  string `json:"network"`
	ChainID      string `json:"chainid"`
}

type report struct {
	Title string
	Nodes []nodeMetadata
}

func createReport(title string) report {
	type t struct {
		Result nodeMetadata `json:"result"`
	}
	nodeReport := baseRequest("http://localhost:9500")
	oneReport := t{}
	json.Unmarshal(nodeReport, &oneReport)
	fmt.Println(oneReport.Result)
	return report{"some-report-example", []nodeMetadata{oneReport.Result}}
}

func renderReport(w http.ResponseWriter, req *http.Request) {
	t, _ := template.New("report").Parse(reportTemplate)
	t.Execute(w, createReport("SHOULD COME FROM YAML CONFIG"))
}

func startReportingHTTPServer() {
	http.HandleFunc("/report", renderReport)
	http.ListenAndServe(":8080", nil)
}
