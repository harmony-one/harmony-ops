#!/usr/bin/env bash

# set -x

function usage() {
   ME=$(basename "$0")
   cat<<-EOT
Usage:
   $ME [options] action

Options:
   -h             print this help message
   -B blocks      trigger view change after #blocks from current block height (default: $AFTER_BLOCK)
   -S num         specify shard number
   -I ip          specify the IP address
   -m method      specify the method to send
   -p params      specify the parameters to the method
   -L             send to leader only (default: $LEADER)

Note:
   This command assumes the stn network

   -S / -I        please specify one of them

Actions:
   vc1            trigger vc test after $AFTER_BLOCK blocks (kill on commit)
   vc2            trigger vc test after $AFTER_BLOCK blocks (kill on prepare)
   vc3            trigger vc test after $AFTER_BLOCK blocks (kill on announce)
   vc4            trigger vc test (instant kill)

Examples:
   $ME -I 34.220.233.31 -m getLatestChainHeaders
   $ME -I 52.33.12.218 -m killNode -p true
   $ME -I 52.33.12.218 -m killNodeCond -p 'true, "*", "*", 43480, 60, true'
   $ME -I 34.220.233.31 -m killNodeCond -p 'true, "Commit", "*", 219800, 60, false'

# send to leader only on shard 1
   $ME -S 1 -L vc1
EOT
   exit 0
}

function send_cmd() {
   local ip=$1
   local method=$2
   local params=$3

   CURL="-s --request POST http://${ip}:9500/"
   tmpfile=$(mktemp)

   cat<<-EOT > $tmpfile
   [
      {
         "jsonrpc": "2.0",
         "method": "hmyv2_${method}",
         "params": [${params}],
         "id": 1
      }
   ]
EOT

   echo "curl $CURL --header \"Content-Type: application/json\" --data @$tmpfile" > /dev/stderr
   curl "$CURL" --header "Content-Type: application/json" --data @"$tmpfile" | jq .[0].result

   rm -f "$tmpfile"
}

function do_test() {
   if [ -n "$IP" ]; then
      send_cmd "$IP" "$METHOD" "$PARAMS"
   fi

   if [ -n "$SHARD" ]; then
      if $LEADER; then
         send_cmd "$LIP" "$METHOD" "$PARAMS"
      else
         for i in "${HOSTS[@]}"; do
            send_cmd "$i" "$METHOD" "$PARAMS"
         done
      fi
   fi
}

function get_leader_ip() {
   for ip in "${HOSTS[@]}"; do
      result=$(send_cmd "$ip" getNodeMetadata "")
      leader=$(echo "$result" | jq -r '.["is-leader"]')
      if $leader; then
         echo "$ip"
         return
      fi
   done
}

function get_host_ips() {
   local shard=$1
   ansible "stn${shard}" --list-hosts | grep -v hosts | tr -d ' ' | tr '\n' ' '
}

function get_current_block() {
   ip=$1
   result=$(send_cmd "$ip" getLatestChainHeaders "")
   height=$(echo "$result" | jq '.["shard-chain-header"]' | jq '.["block-number"]' )
   echo "$height"
}

function get_current_block_from_shard() {
   height=-1
   for ip in "${HOSTS[@]}"; do
      h=$( get_current_block "$ip" )
      if [ "$h" -gt "$height" ]; then
         height=$h
      fi
   done
   echo "$height"
}

function do_vcX() {
   phase=$1

   cur_block=-1
   if [ -n "$IP" ]; then
      cur_block=$(get_current_block "$IP")
   fi
   if [ -n "$SHARD" ]; then
      cur_block=$(get_current_block_from_shard "$SHARD")
   fi
   if [ "$cur_block" == "-1" ]; then
      echo can\'t get current block number, exiting ...
      return
   fi

   new_block=$(( cur_block + AFTER_BLOCK ))
   if [ -n "$IP" ]; then
      send_cmd "$IP" killNodeCond "true, \"$phase\", \"*\", $new_block, 60, false"
   fi
   if [ -n "$SHARD" ]; then
      if $LEADER; then
         send_cmd "$LIP" killNodeCond "true, \"$phase\", \"*\", $new_block, 60, false"
      else
         for i in "${HOSTS[@]}"; do
            send_cmd "$i" killNodeCond "true, \"$phase\", \"*\", $new_block, 60, false"
         done
      fi
   fi
}

function do_vc1() {
   do_vcX "Commit"
}

function do_vc2() {
   do_vcX "Prepare"
}

function do_vc3() {
   do_vcX "Annouce"
}

function do_vc4() {
   if [ -n "$IP" ]; then
      send_cmd "$IP" killNode 'true'
   fi
   if [ -n "$SHARD" ]; then
      cur_block=$(get_current_block_from_shard "$SHARD")
      if $LEADER; then
         send_cmd "$LIP" killNode 'true'
      else
         for i in "${HOSTS[@]}"; do
            send_cmd "$i" killNode 'true'
         done
      fi
   fi
}

AFTER_BLOCK=5
LEADER=false
HOSTS=()

while getopts ":h:B:S:I:m:p:L" opt; do
   case $opt in
      B) AFTER_BLOCK=$OPTARG ;;
      S) SHARD=$OPTARG ;;
      I) IP=$OPTARG ;;
      m) METHOD=$OPTARG ;;
      p) PARAMS="$OPTARG" ;;
      L) LEADER=true ;;
      *) usage ;;
   esac
done

shift $(( OPTIND - 1 ))

if [[ -z "$IP" && -z "$SHARD" ]]; then
   usage
fi

if [ -n "$SHARD" ]; then
   HOSTS=( $(get_host_ips "$SHARD") )
fi

if $LEADER; then
   LIP=$(get_leader_ip "$SHARD")
fi

ACTION=$1

case $ACTION in
   vc1) do_vc1 ;;
   vc2) do_vc2 ;;
   vc3) do_vc3 ;;
   vc4) do_vc4 ;;
   *) do_test ;;
esac

################
