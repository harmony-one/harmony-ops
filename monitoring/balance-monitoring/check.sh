#!/usr/bin/env bash

### Get addresses from file 
# curl -sL https://harmony.one/fn-keys | grep Address | cut -d '"' -f 4
addresses=$(< generated/addresses.txt)

# Call wallet.sh on addresses to get balances and cut out unnecessary info
export LD_LIBRARY_PATH=$(pwd)/wallet_files
balances=$(echo "$addresses" | xargs -P 50 -i{} bash -c \
'wallet_files/wallet balances -address={} | tail -n +2 | grep -v ":  0.0000," |
tr -d "\n" | awk -F"[ :,]" "{print \$3, \$11, \$14}"')

# Place balances file in dated directory
hour=$(date +%H)
minute=$(date +%M)
mkdir -p captures/$hour/$minute
if [[ -f "captures/$hour/$minute/balances.txt" ]]; then
    mkdir -p captures/temp
    mv -f captures/$hour/$minute/balances.txt captures/temp/balances.txt
fi
echo "$balances" > captures/$hour/$minute/balances.txt
