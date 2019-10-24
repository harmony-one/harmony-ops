package main

import "fmt"

func reportPage() string {
	// Keep in mind that need extra % infront of % to escape fmt
	return fmt.Sprintf(`
<!DOCTYPE html>
<html lang="en">
  <meta charset="utf-8"
        content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=0"
        name="viewport">
  <head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/sortable/0.8.0/js/sortable.min.js"
        integrity="sha256-gCtdA1cLK2EhQZCMhhvGzUsWM/fsxtJ2IImUJ+4UOP8="
        crossorigin="anonymous"></script>
<link rel="stylesheet"
      href="https://cdnjs.cloudflare.com/ajax/libs/sortable/0.8.0/css/sortable-theme-bootstrap.min.css"
      integrity="sha256-S9t86HqhPL8nNR85dIjDQCJMPd9RULmRAub6xBksk9M="
      crossorigin="anonymous" />
<link href="https://fonts.googleapis.com/css?family=Open+Sans"
      rel="stylesheet"
      crossorigin="anonymous" />
<style>
* {margin:0;padding:0;}
body {font-family: "Open Sans", sans-serif;}
.report-wrapper {padding:17px;padding-bottom:30px;background-color:#344E4F;}
.report-table {width:100%%; table-layout:fixed;word-break:break-all;}
.report-descr {display:flex; justify-content:space-between; padding-bottom: 15px;}
.flex-col {display:flex;flex-direction:column;}
.flex-row {display:flex;justify-content:space-between;}
.build-stat {
  background-color:#E0EFC7;
  padding: 10px; display:flex; justify-content:space-between;
}
.build-stat-values {font-size: 15px; font-weight: bolder;}
.summary-details {
  background-color:#7F9A95;
  box-shadow: 0 2px 2px -1px rgba(0, 0, 0, 0.4);
  position: -webkit-sticky;
  position: sticky;
  top:0px;
  padding: 10px;
  height:95px;
}
.align-right { text-align: right; }
.space-between { justify-content:space-between; width: 100%% }
.is-leader { background-color: #c4b8b178; }
.center { align-items: center; }
.stat-box { box-shadow: 0 2px 2px 0px rgba(0, 0, 0, 0.9); padding: 10px; background-color:#7F9A95;}
th {
  background: #c9d1ac;
  position: sticky;
  top: 91px;
  box-shadow: 0 2px 2px -1px rgba(0, 0, 0, 0.4);
}
hr{
  overflow: visible; /* For IE */
  padding: 0;
  border: none;
  border-top: medium double #333;
  color: #333;
  text-align: center;
  height: 0px;
}
hr:after {
  content: "§";
  display: inline-block;
  position: relative;
  top: -0.7em;
  font-size: 1.5em;
  padding: 0 0.25em;
}
</style>
  </head>
  <body>
    <header id="top-of-page">
      <div class="build-stat">
        <div class="flex-row space-between">
          <div class="flex-col">
          {{range .LeftTitle}}
            <span class="build-stat-values">{{.}}</span>
          {{end}}
          </div>
          <div class="flex-col">
          {{range .RightTitle}}
            <span class="build-stat-values align-right">{{.}}</span>
          {{end}}
          </div>
        </div>
      </div>
      <hr/>
      <div class="build-stat">
        {{ with (index .Summary "block-header") }}
        {{range $key, $value := .}}
          <div class="flex-col center stat-box">
            <a href="#shard-{{$key}}">Shard-{{$key}}</a>
            <p>count:{{ len (index $value "records") }}</p>
            <p>max block: {{index $value "block-max"}}</p>
            <p>max epoch: {{index $value "epoch-max"}}</p>
            <p>leader: {{index $value "shard-leader"}}</p>
          </div>
        {{end}}
        {{end}}
      </div>
      <div class="build-stat">
        {{ with (index .Summary "node-metadata") }}
        {{range $key, $value := .}}
          <div class="flex-col center stat-box">
            <a href="#version-{{$key}}">Version-{{$key}}</a>
            <p>count:{{ len (index $value "records") }}</p>
          </div>
        {{end}}
        {{end}}
      </div>
    </header>
    <main>

    {{ if ne (len .NoReply) 0 }}
    <section class="report-wrapper">
      <div class="summary-details">
        <div class="flex-col">
          <div class="flex-row space-between">
            <h3>
              Down machines <span><a href="#top-of-page">(Top)</a></span>
            </h3>
            <p style="width: 375px;">
             Note: "dialing to the given TCP address timed out" failure could
             just mean that the HTTP RPC did not complete fast enough.
            </p>
          </div>
          <div class="flex-row">
            <p> distinct down machine count: {{ .DownMachineCount }} </p>
          </div>
        </div>
      </div>
      <table class="sortable-theme-bootstrap report-table" data-sortable>
        <thead>
          <tr>
            <th>IP</th>
            <th>RPC Payload</th>
            <th>Failure Reason</th>
          </tr>
        </thead>
        <tbody>
        {{range .NoReply}}
          <tr>
            <td>{{.IP}}</td>
            <td>{{.RPCPayload}}</td>
            <td>{{.FailureReason}}</td>
          </tr>
        {{end}}
        </tbody>
      </table>
    </section>
    {{end}}

    {{ with (index .Summary "block-header") }}
    {{range $key, $value := .}}
    <section class="report-wrapper" id="shard-{{$key}}">
      <div class="summary-details">
        <div class="flex-col">
          <div class="flex-row">
            <h3>
              Block Header <span><a href="#top-of-page">(Top)</a></span>
            </h3>
            <a href="/report-download?report=%s">Download CSV</a>
          </div>
          <div class="flex-row">
            <p> shard: {{ $key }} </p>
            <p> node count: {{ len (index $value "records") }} </p>
            <p> max block: {{index $value "block-max"}}</p>
            <p> min block: {{index $value "block-min"}}</p>
            <p> max epoch: {{index $value "epoch-max"}}</p>
            <p> min epoch: {{index $value "epoch-min"}}</p>
          </div>
          <div class="flex-row">
            <p> unique block: {{index $value "uniq-blocks"}}</p>
            <p> unique epochs: {{index $value "uniq-epochs"}}</p>
          </div>
        </div>
      </div>
      <table class="sortable-theme-bootstrap report-table" data-sortable>
        <thead>
	  <tr>
	    <th>IP</th>
	    <th>Block Hash</th>
	    <th>Epoch</th>
	    <th>Block Number</th>
	    <th>Leader</th>
	    <th>ViewID</th>
	    <th>Timestamp</th>
	    <th>Unixtime</th>
	    <th>Last Commit Sig</th>
	    <th>Last Commit Bitmap</th>
	  </tr>
        </thead>
        <tbody>
          {{ with (index $value "records") }}
          {{range .}}
          <tr>
            <td>{{.IP}} </td>
            <td>{{.Payload.BlockHash}} </td>
            <td>{{.Payload.Epoch}} </td>
            <td>{{.Payload.BlockNumber}} </td>
            <td>{{.Payload.Leader}} </td>
            <td>{{.Payload.ViewID}} </td>
            <td>{{.Payload.Timestamp}} </td>
            <td>{{.Payload.UnixTime}} </td>
            <td>{{.Payload.LastCommitSig}} </td>
            <td>{{.Payload.LastCommitBitmap}} </td>
          </tr>
          {{end}}
          {{end}}
        </tbody>
      </table>
    </section>

    {{end}}
    {{end}}

    {{ with (index .Summary "node-metadata") }}
    {{range $key, $value := .}}
    <section class="report-wrapper" id="version-{{$key}}">
      <div class="summary-details">
        <div class="flex-col">
          <div class="flex-row">
            <h3>
              Node Metadata <span><a href="#top-of-page">(Top)</a></span>
           </h3>
            <a href="/report-download?report=%s">Download CSV</a>
          </div>
          <div class="flex-row">
            <p> build version: {{ $key }} </p>
            <p> node count: {{ len (index $value "records") }} </p>
          </div>
        </div>
      </div>
      <table class="sortable-theme-bootstrap report-table" data-sortable>
        <thead>
	  <tr>
	    <th>IP</th>
	    <th>BLS Key</th>
	    <th>Version</th>
	    <th>Network Type</th>
	    <th>ChainID</th>
	  </tr>
        </thead>
        <tbody>
          {{ with (index $value "records") }}
          {{range .}}
          <tr class="{{if .Payload.IsLeader}}is-leader{{end}}">
            <td>{{.IP}} </td>
            <td>{{.Payload.BLSPublicKey}} </td>
            <td>{{.Payload.Version}} </td>
            <td>{{.Payload.NetworkType}} </td>
            <td>{{.Payload.ChainID}} </td>
          </tr>
          {{end}}
          {{end}}
        </tbody>
      </table>
    </section>
    {{end}}
    {{end}}
    </main>
<script>
setInterval(() => window.location.reload(true),  1000 * 120);
</script>
  </body>
</html>
`, blockHeaderReport, nodeMetadataReport)
}
