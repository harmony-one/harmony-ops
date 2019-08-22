#!/usr/bin/env bash

### Get addresses from file 
addresses=$(curl -sL https://harmony.one/fn-keys | tac | sed -e '/var /q' |\
            tac | grep Address | awk -F'"' '{print $4, $2 % 4}')

### Save hour/minute
date +%H > generated/hour.txt
date +%M > generated/minute.txt

# Get functions and constants
source monitoring.sh

# Call wallet.sh on addresses to get balances and cut out unnecessary info
export LD_LIBRARY_PATH=$(pwd)/wallet_files
raw=$(echo "$addresses" | xargs -P 50 -i{} bash -c \
'address=$(echo "{}" | cut -d " " -f 1); shard=$(echo "{}" | cut -d " " -f 2);
result=$(wallet_files/wallet balances -address="$address");
bal=$(echo "$result" | tail -n +2 | tr -d "\n" | awk -F"[ :,]" \
'"'"'{print $14, "+", $29, "+", $44, "+", $59}'"'"' | bc); 
echo "$address $shard $bal"')
balances=$(echo "$raw" | awk '{if ($3) print $0; else print $1, "-1", "0";}')

# Place balances file in dated directory
mkdir -p captures/$hour/$minute
if [[ -f "captures/$hour/$minute/$FILE" ]]; then
    mv -f captures/$hour/$minute/$FILE captures/$hour/$minute/temp.txt
fi
echo "$balances" > captures/$hour/$minute/$FILE
