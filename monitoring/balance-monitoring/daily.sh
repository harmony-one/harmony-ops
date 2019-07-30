#!/usr/bin/env bash

# daily.sh - Generates daily report of balances

# Specific interval constants
prefix=generated/24h/24h
textfile=$prefix.txt
csvfile=$prefix.csv
jsonfile=$prefix.json
csvextra="ONEs Per Day"
jsonextra="ONEsPerDay"

# Get functions and constants
source monitoring.sh

### Combine balance data from both files and subtract both
previous=$(sort captures/temp/balances.txt | sort -nr -k 2,2 |\
           cut -d " " -f 3)
result=$(paste <(echo "$current") <(echo "$previous") |\
         awk '{print $1, $2, $3 - $4}')

# Run generation scripts
gentxt
gencsv
genjson
