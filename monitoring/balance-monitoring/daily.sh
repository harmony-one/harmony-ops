#!/usr/bin/env bash

# Generates hourly report
prefix=generated/day/day
textfile=$prefix.txt
csvfile=$prefix.csv
jsonfile=$prefix.json
csvextra="ONEs Per Day"
jsonextra="ONEsPerDay"

# Get functions and constants
source monitoring.sh

### Combine balance data from both files and subtract both
previous=$(sort captures/temp/balances.txt | cut -d " " -f 3)
result=$(paste <(echo "$current") <(echo "$previous") | awk '{print $1, $2, $3 - $4}')

# Run generation scripts
gentxt
gencsv
genjson
