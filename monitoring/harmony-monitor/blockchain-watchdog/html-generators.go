package main

import "fmt"

func reportPage(chain string) string {
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
.report-wrapper > label {color: #AFCAC5;}
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
.stat-field {
	display: flex;
	justify-content:space-between;
}
.flex-both {
	display: flex;
	flex-direction: column;
}
@media only screen and (min-width: 670px) {
	.flex-both {
		display: flex;
		flex-direction: row;
	}
}
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

.stat-box > p {
  display:flex;
  justify-content: space-between;
  width: 100%%;
}
{{ with (index .Summary "block-header") }}
{{range $key, $value := .}}
#curr-hn-toggle-{{$key}}:checked ~ * .curr-harmony-node-{{$key}}-true {
  display: table-row;
}
#curr-hn-toggle-{{$key}}:not(checked) ~ * .curr-harmony-node-{{$key}}-true {
  display: none;
}
#prev-hn-toggle-{{$key}}:checked ~ * .prev-harmony-node-{{$key}}-true {
  display: table-row;
}
#prev-hn-toggle-{{$key}}:not(checked) ~ * .prev-harmony-node-{{$key}}-true {
  display: none;
}
{{end}}
{{end}}
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
      <div class="build-stat flex-both">
        {{$root := .}}
        {{ with (index .Summary "chain-config") }}
        {{range $key, $value := .}}
          <div class="flex-col center stat-box">
            <a href="#shard-{{$key}}">Shard-{{$key}}</a>
            <p><span>Consensus:</span><span> {{index $value "consensus-status"}}</span></p>
            <p><span>Chain ID:</span><span> {{index $value "chain-id"}}</span></p>
            <p><span>Cross Link Epoch:</span><span>{{index $value "cross-link-epoch"}}</span></p>
            <p><span>Cross Tx Epoch:</span><span>{{index $value "cross-tx-epoch"}}</span></p>
            <p><span>Eip155 Epoch:</span><span>{{index $value "eip155-epoch"}}</span></p>
            <p><span>S3 Epoch:</span><span>{{index $value "s3-epoch"}}</span></p>
            <p><span>Pre-Staking Epoch:</span><span>{{index $value "pre-staking-epoch"}}</span></p>
            <p><span>Staking Epoch:</span><span>{{index $value "staking-epoch"}}</span></p>
            <p><span>Blocks Per Epoch:</span><span>{{index $value "blocks-per-epoch"}}</span></p>
            <p><span>DNS Zone:</span><span>{{index $value "dns-zone"}}</span></p>
            {{ if $root.SuperCommittee.CurrentCommittee.Deciders }}
              <a href="#current-committee-{{$key}}">Current Committee</a>
            {{end}}
            {{ if $root.SuperCommittee.PreviousCommittee.Deciders }}
              <a href="#previous-committee-{{$key}}">Previous Committee</a>
            {{end}}
          </div>
        {{end}}
        {{end}}
      </div>
      <div class="build-stat flex-both">
        {{ with (index .Summary "block-header") }}
        {{range $key, $value := .}}
          <div class="flex-col center stat-box">
            <a href="#shard-{{$key}}">Shard-{{$key}}</a>
            <p><span>Node Count:</span><span>{{ len (index $value "records") }}</span></p>
            <p><span>Max Block:</span><span>{{index $value "block-max"}}</span></p>
            <p><span>Max Epoch:</span><span>{{index $value "epoch-max"}}</span></p>
            <p><span>Leader:</span><span>{{index $value "shard-leader"}}</span></p>
          </div>
        {{end}}
        {{end}}
      </div>
      <div class="build-stat flex-both">
        {{ with (index .Summary "node-metadata") }}
        {{range $key, $value := .}}
          <div class="flex-col center stat-box">
            <a href="#version-{{$key}}">Version-{{$key}}</a>
            <p>
              Node Count:{{ len (index $value "records") }}
              {{ with getCommitId $key }}
                <a href="https://github.com/harmony-one/harmony/commit/{{.}}">commit</a>
              {{end}}
            <p>
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
            <p>Distinct down machine count: {{ .DownMachineCount }} </p>
          </div>
        </div>
      </div>
      <table class="sortable-theme-bootstrap report-table" data-sortable>
        <thead>
          <tr>
            <th>IP</th>
            <th>Intended ShardID</th>
            <th>RPC Payload</th>
            <th>Failure Reason</th>
          </tr>
        </thead>
        <tbody>
        {{range .NoReply}}
          <tr style="background-color:#F0B4B4;">
            <td>{{.IP}}</td>
            <td>{{.ShardID}}</td>
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
            <a href="/report-download-%s?report=%s&shard={{$key}}">Download CSV</a>
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
            <a href="/report-download-%s?report=%s&vrs={{$key}}">Download CSV</a>
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
	    <th>ShardID</th>
	    <th>Role</th>
	    <th>IsArchivalNode</th>
	  </tr>
        </thead>
        <tbody>
          {{ with (index $value "records") }}
          {{range .}}
          <tr class="{{if .Payload.IsLeader}}is-leader{{end}}">
            <td>{{ .IP }}</td>
            <td>{{ .Payload.BLSPublicKey }}</td>
            <td>{{ .Payload.Version }}</td>
            <td>{{ .Payload.NetworkType }}</td>
            <td>{{ .Payload.ChainConfig.ChainID }}</td>
            <td>{{ .Payload.ShardID }}</td>
            <td>{{ .Payload.NodeRole }}</td>
            <td>{{ .Payload.ArchivalNode }}</td>
          </tr>
          {{end}}
          {{end}}
        </tbody>
      </table>
    </section>
		{{ end }}
		{{ end }}

		{{ with .SuperCommittee }}
    {{ range .CurrentCommittee.Deciders}}
    {{ with . }}
    {{ $Decider := . }}
    <section class="report-wrapper" id="current-committee-{{ .ShardID }}">
      <input type="checkbox" id="curr-hn-toggle-{{.ShardID}}">
      <label for="curr-hn-toggle-{{.ShardID}}">show harmony nodes</label>
      <div class="summary-details">
        <div class="flex-col">
          <div class="flex-row">
            <h3>
              Shard {{ .ShardID }} Current Commitee <span><a href="#top-of-page">(Top)</a></span>
           </h3>
          </div>
          <div class="flex-row">
						<div class="flex-col">
					  	<p> policy: {{ .PolicyType }} </p>
              <p> member count: {{ .MemberCount }} </p>
						</div>
						<div class="flex-col">
            	<p> harmony voting power: {{ .HarmonyPower }} </p>
            	<p> staked voting power: {{ .StakedPower }} </p>
            	<p> total raw stake: {{ .TotalRawStake }} </p>
          	</div>
					</div>
        </div>
      </div>
      <table class="sortable-theme-bootstrap report-table" data-sortable>
        <thead>
	  <tr>
			<th>Address</th>
	    <th>BLSKey</th>
	    <th>Is Harmony Node</th>
	    <th>Voting Power</th>
	    <th>External Vote Power</th>
	    <th>Effective Stake</th>
	  </tr>
        </thead>
        <tbody>
          {{ range .Committee }}
          {{ with . }}
					<tr class="curr-harmony-node-{{$Decider.ShardID}}-{{.IsHarmonyNode}}">
            <td>{{.Address}}</td>
            <td>{{.BLSKey}}</td>
            <td>{{.IsHarmonyNode}}</td>
            <td>{{.VotingPower}}</td>
            <td>{{.RawPercent}}</td>
            <td>{{.EffectiveStake}}</td>
          </tr>
          {{end}}
          {{end}}
        </tbody>
      </table>
    </section>
		{{end}}
    {{end}}
		{{end}}

		{{ with .SuperCommittee }}
		{{ range .PreviousCommittee.Deciders}}
		{{ with . }}
    {{ $Decider := . }}
		<section class="report-wrapper" id="previous-committee-{{ .ShardID }}">
      <input type="checkbox" id="prev-hn-toggle-{{ .ShardID }}">
      <label for="prev-hn-toggle-{{.ShardID}}">show harmony nodes</label>
			<div class="summary-details">
				<div class="flex-col">
					<div class="flex-row">
						<h3>
							Shard {{ .ShardID }} Previous Commitee <span><a href="#top-of-page">(Top)</a></span>
					 </h3>
					</div>
					<div class="flex-row">
						<div class="flex-col">
							<p> policy: {{ .PolicyType }} </p>
              <p> member count: {{ .MemberCount }} </p>
						</div>
						<div class="flex-col">
							<p> harmony voting power: {{ .HarmonyPower }} </p>
							<p> staked voting power: {{ .StakedPower }} </p>
							<p> total raw stake: {{ .TotalRawStake }} </p>
						</div>
					</div>
				</div>
			</div>
			<table class="sortable-theme-bootstrap report-table" data-sortable>
				<thead>
		<tr>
			<th>Address</th>
			<th>BLSKey</th>
			<th>Is Harmony Node</th>
			<th>Voting Power</th>
			<th>External Vote Power</th>
			<th>Effective Stake</th>
		</tr>
				</thead>
				<tbody>
					{{ range .Committee }}
					{{ with . }}
					<tr class="prev-harmony-node-{{$Decider.ShardID}}-{{.IsHarmonyNode}}">
						<td>{{.Address}}</td>
						<td>{{.BLSKey}}</td>
						<td>{{.IsHarmonyNode}}</td>
						<td>{{.VotingPower}}</td>
						<td>{{.RawPercent}}</td>
						<td>{{.EffectiveStake}}</td>
					</tr>
					{{end}}
					{{end}}
				</tbody>
			</table>
		</section>
		{{end}}
		{{end}}
		{{end}}

    </main>
<script>
setInterval(() => window.location.reload(true),  1000 * 120);
</script>
  </body>
</html>
`, chain, blockHeaderReport, chain, nodeMetadataReport)
}
