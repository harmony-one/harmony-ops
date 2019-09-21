package main

import "fmt"

func blockHeaderTable() string {
	return `
    <table class="sortable-theme-bootstrap report-table" data-sortable>
      <thead>
	<tr>
	  <th>IP</th>
	  <th>Block Hash</th>
	  <th>Block Number</th>
	  <th>ShardID</th>
	  <th>Leader</th>
	  <th>ViewID</th>
	  <th>Epoch</th>
	  <th>Timestamp</th>
	  <th>Unixtime</th>
	  <th>Last Commit Sig</th>
	  <th>Last Commit Bitmap</th>
	</tr>
      </thead>
      <tbody>
{{range .NodesHeader}}
<tr>
  <td>{{.IP}} </td>
  <td>{{.Payload.BlockHash}} </td>
  <td>{{.Payload.BlockNumber}} </td>
  <td>{{.Payload.ShardID}} </td>
  <td>{{.Payload.Leader}} </td>
  <td>{{.Payload.ViewID}} </td>
  <td>{{.Payload.Epoch}} </td>
  <td>{{.Payload.Timestamp}} </td>
  <td>{{.Payload.UnixTime}} </td>
  <td>{{.Payload.LastCommitSig}} </td>
  <td>{{.Payload.LastCommitBitmap}} </td>
</tr>
{{end}}
      </tbody>
    </table>
`
}

func nodeMetadataTable() string {
	return `
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
{{range .NodesMetadata}}
<tr>
  <td>{{.IP}} </td>
  <td>{{.Payload.BLSPublicKey}} </td>
  <td>{{.Payload.Version}} </td>
  <td>{{.Payload.NetworkType}} </td>
  <td>{{.Payload.ChainID}} </td>
</tr>
{{end}}
      </tbody>
    </table>
`
}

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
.report-wrapper {padding:17px;padding-bottom:30px;background-color:aliceblue;}
.report-table {width:100%%;}
.report-descr {display:flex; justify-content:space-between; padding-bottom: 15px;}
.build-stat { padding: 10px; display:flex; justify-content:space-between;}
</style>
  </head>
  <body>
  <header>
<div class="build-stat">
{{range .Title}}
  <span>{{.}}</span>
{{end}}
</div>
<a href="#metadata-table">Node Metadata</a>
</header>

<section class="report-wrapper" id="block-header-table">
<div class="report-descr">
<h3>Block Header</h3>
<a href="/report-download?report=%s">Download CSV</a>
</div>
%s
</section>

<section class="report-wrapper" id="metadata-table">
<div class="report-descr">
<h3>Node metadata</h3>
<a href="/report-download?report=%s">Download CSV</a>
</div>

%s
</section>

  </body>
</html>
`, blockHeaderReport, blockHeaderTable(), nodeMetadataReport, nodeMetadataTable())
}
