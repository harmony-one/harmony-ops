#!/usr/bin/env bash

# Generates hourly report
prefix=generated/1h/1h
textfile=$prefix.txt
csvfile=$prefix.csv
jsonfile=$prefix.json
csvextra="ONEs Per Hour"
jsonextra="ONEsPerHour"

# Get functions and constants
source monitoring.sh

# Get 1 hour before current time
if [[ $hour = 00 ]]; then
    prevhr="23"
elif [[ $hour < 11 ]]; then
    prevhr="0$(echo "$hour - 1" | bc)"
else
    prevhr=$((hour - 1))
fi

### Combine balance data from both files and subtract both
previous=$(sort captures/$prevhr/$minute/$FILE | cut -d " " -f 3)
result=$(paste <(echo "$current") <(echo "$previous") | awk '{print $1, $2, $3 - $4}')

# Run generation scripts
gentxt
gencsv
genjson
