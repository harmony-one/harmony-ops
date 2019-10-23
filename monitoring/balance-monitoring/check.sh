#!/usr/bin/env bash

ADDR=address.$$.txt
### Get addresses from file 
keys=$(curl -sL https://harmony.one/fn-keys | tac | sed -e '/var /q' | tac |\
       grep Address)
echo "$keys" |  awk -F'"' '{print $4, $2 % 4}' > $ADDR

### Save hour/minute
date +%H > generated/hour.txt
date +%M > generated/minute.txt

# Get functions and constants
source monitoring.sh

# Place balances file in dated directory
mkdir -p captures/$hour/$minute
if [[ -f "captures/$hour/$minute/$FILE" ]]; then
    mv -f captures/$hour/$minute/$FILE captures/$hour/$minute/temp.txt
    touch captures/$hour/$minute/$FILE
fi

while read add; do
   address=$(echo "$add" | cut -d " " -f 1)
   shard=$(echo "$add" | cut -d " " -f 2)
   result=$(LD_LIBRARY_PATH=wallet_files wallet_files/hmy balance -n http://s${shard}.t.hmny.io:9500 "$address" | jq '.[].amount' | tr "\n" + | sed s/+$//)
   amount=$(echo "$result" | bc -l)
   if [ -n "$amount" ]; then
      echo "$address $shard $amount" >> captures/$hour/$minute/$FILE
   else
      echo "$address -1 0" >> captures/$hour/$minute/$FILE
   fi
   sleep 1
done < $ADDR

rm $ADDR
