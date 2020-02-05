#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

delay=30
iters=5
timeout_dir=60
wait=120

while getopts hw:t:d:i: option; do
  case "${option}" in

  w) wait=${OPTARG} ;;
  t) timeout_dir=${OPTARG} ;;
  d) delay=${OPTARG} ;;
  i) iters=${OPTARG} ;;
  h)
    echo "Options:"
    echo ""
    echo "  Example: ./localnet_test.sh -w 60 -t 60 -d 30 -i 5"
    echo ""
    echo "    -w <int>  Delay (in seconds) before starting the test. Default is 120 seconds."
    echo "    -t <int>  Timeout before localnet is spun up. Default is 60 seconds."
    echo "    -d <int>  Cx delay (in seconds) between send and check for tests. Default is 30 seconds."
    echo "    -i <int>  Max number of iterations before success. Default is 5."
    echo "    -h        Help."
    exit 0
    ;;
  esac
done

function tryConnect() {
  until $(curl --silent --location --request POST "localhost:9500" \
    --header "Content-Type: application/json" \
    --data '{"jsonrpc":"2.0","method":"net_version","params":[],"id":1}' >/dev/null); do
    echo "Trying to connect..."
    sleep 3
  done
}

function waitBoot() {
  echo "Waiting for localnet to boot..."
  valid=false
  until ${valid}; do
    result=$(curl --silent --location --request POST "localhost:9500" \
      --header "Content-Type: application/json" \
      --data '{"jsonrpc":"2.0","method":"hmy_blockNumber","params":[],"id":1}' |
      jq '.result')
    if [[ "$result" == "\"0x0\"" ]]; then
      sleep 3
    else
      valid=true
    fi
  done
  echo "Localnet booted..."
}

timeout "$timeout_dir" cat <( tryConnect )
timeout "$timeout_dir" cat <( waitBoot )

echo "Sleeping ${wait} seconds to generate some funds..."
sleep $wait

# TODO: Enable staking tests...
python3 -u ${DIR}/test.py --test_dir=./tests/no-explorer/ --rpc_endpoint_src="http://localhost:9500/" \
  --rpc_endpoint_dst="http://localhost:9501/" --delay=${delay} --iterations=${iters} --cli_passphrase='' \
  --ignore_staking_test
