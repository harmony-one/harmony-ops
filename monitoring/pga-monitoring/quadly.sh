#!/usr/bin/env bash

# quadly.sh - Generates quad-hourly report of balances

# Specific interval constants
prefix=generated/4h/4h
textfile=$prefix.txt
csvfile=$prefix.csv
jsonfile=$prefix.json
csvextra="ONEs Per Four Hours"
jsonextra="ONEsPerFourHours"

### Get functions and constants
source monitoring.sh

### Get 4 hours before current time
if [[ $hour < 04 ]]; then
    prevhr=$((hour + 20))
elif [[ $hour < 14 ]]; then
    prevhr="0$(echo "$hour - 4" | bc)"
else
    prevhr=$((hour - 4))
fi

### Set constants for previous then get the diff
prevmin=$minute
getdiff

# Run generation scripts
gentxt
gencsv
genjson
