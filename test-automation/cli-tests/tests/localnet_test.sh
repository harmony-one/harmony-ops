#!/usr/bin/env bash

until $(curl --silent --location --request POST "localhost:9500" \
   --header "Content-Type: application/json" \
   --data '{"jsonrpc":"2.0","method":"net_version","params":[],"id":1}' > HTML_Output)
do
    echo "Trying to connect..."
    sleep 3
done

valid=False
until $valid
do
    result=$(curl --silent --location --request POST "localhost:9500" \
        --header "Content-Type: application/json" \
        --data '{"jsonrpc":"2.0","method":"hmy_blockNumber","params":[],"id":1}' \
         | jq | jq '.result')
    if [ "$result" = "\"0x0\"" ]; then
        echo "Waiting for localnet to boot..."
        sleep 3
    else
        valid=True
    fi
done

python3 testHmy.py