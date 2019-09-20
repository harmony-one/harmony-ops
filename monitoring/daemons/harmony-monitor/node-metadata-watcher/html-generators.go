package main

import "fmt"

func blockHeaderTable() string {
	return `
    <table class="sortable-theme-bootstrap report-table" data-sortable>
      <thead>
	<tr>
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
  <td>{{.BlockHash}} </td>
  <td>{{.BlockNumber}} </td>
  <td>{{.ShardID}} </td>
  <td>{{.Leader}} </td>
  <td>{{.ViewID}} </td>
  <td>{{.Epoch}} </td>
  <td>{{.Timestamp}} </td>
  <td>{{.UnixTime}} </td>
  <td>{{.LastCommitSig}} </td>
  <td>{{.LastCommitBitmap}} </td>
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
	  <th>BLS Key</th>
	  <th>Version</th>
	  <th>Network Type</th>
	  <th>ChainID</th>
	</tr>
      </thead>
      <tbody>
{{range .NodesMetadata}}
<tr>
  <td>{{.BLSPublicKey}} </td>
  <td>{{.Version}} </td>
  <td>{{.NetworkType}} </td>
  <td>{{.ChainID}} </td>
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
header { padding: 10px; display:flex; justify-content:space-between;}
</style>
  </head>
  <body>
  <header>
{{range .Title}}
  <span>{{.}}</span>
{{end}}
</header>

<section class="report-wrapper">
<div class="report-descr">
<h3>Block Header</h3>
<a href="/report-download?report=%s">Download CSV</a>
</div>
%s
</section>

<section class="report-wrapper">
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
