#!/usr/bin/env bash
set -e

delay=25
iters=20
wait=120
doStaking=false

while getopts hw:d:i:s option
do 
 case "${option}" 
 in
 w) wait=${OPTARG};;
 d) delay=${OPTARG};;
 i) iters=${OPTARG};;
 s) doStaking=true;;
 h) echo "Options:"
    echo ""
    echo "  Example: ./localnet_test.sh -w 0 -d 30 -i 5 -s"
    echo ""
    echo "    -w <int>  Delay (in seconds) before starting the test. Default is 120 seconds."
    echo "    -d <int>  Cx delay (in seconds) between send and check for tests. Default is 30 seconds."
    echo "    -i <int>  Max number of iterations before success. Default is 20."
    echo "    -s        Toggle (on) staking test. "
    echo "    -h        Help."
    exit 0 ;; 
 esac 
done 

until $(curl --silent --location --request POST "localhost:9500" \
   --header "Content-Type: application/json" \
   --data '{"jsonrpc":"2.0","method":"net_version","params":[],"id":1}' > /dev/null)
do
    echo "Trying to connect..."
    sleep 3
done

valid=false
until $valid
do
    result=$(curl --silent --location --request POST "localhost:9500" \
        --header "Content-Type: application/json" \
        --data '{"jsonrpc":"2.0","method":"hmy_blockNumber","params":[],"id":1}' \
         | jq '.result')
    if [ "$result" = "\"0x0\"" ]; then
        echo "Waiting for localnet to boot..."
        sleep 3
    else
        valid=true
    fi
done

echo "Localnet booted."
echo "Sleeping ${wait} seconds to generate some funds..."
sleep $wait

python3 -m pip install pyhmy

echo "Testing Cx from s0 to s1"
if [ "$doStaking" == "true" ]; then
    python3 test.py --test_dir=./tests/no-explorer/ --rpc_endpoint_src="http://localhost:9500/" \
        --rpc_endpoint_dst="http://localhost:9501/" --keystore=./LocalnetValidatorKeys/ \
        --chain_id="localnet" --delay=${delay} --iterations=${iters}
else
    python3 test.py --test_dir=./tests/no-explorer/ --rpc_endpoint_src="http://localhost:9500/" \
        --rpc_endpoint_dst="http://localhost:9501/" --keystore=./LocalnetValidatorKeys/ \
        --chain_id="localnet" --delay=${delay} --iterations=${iters} --ignore_staking_test
fi

echo "Testing Cx from s1 to s0"
if [ "$doStaking" == "true" ]; then
    python3 test.py --test_dir=./tests/no-explorer/ --rpc_endpoint_src="http://localhost:9501/" \
        --rpc_endpoint_dst="http://localhost:9500/" --keystore=./LocalnetValidatorKeys/ \
        --chain_id="localnet" --delay=${delay} --iterations=${iters}
else
    python3 test.py --test_dir=./tests/no-explorer/ --rpc_endpoint_src="http://localhost:9501/" \
        --rpc_endpoint_dst="http://localhost:9500/" --keystore=./LocalnetValidatorKeys/ \
        --chain_id="localnet" --delay=${delay} --iterations=${iters} --ignore_staking_test
fi
