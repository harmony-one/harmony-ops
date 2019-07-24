#!/usr/bin/env bash

# Generates hourly report
prefix=generated/4h/4h
textfile=$prefix.txt
csvfile=$prefix.csv
jsonfile=$prefix.json
csvextra="ONEs Per Four Hours"
jsonextra="ONEsPerFourHours"

# Get functions and constants
source monitoring.sh

# Get 4 hours before current time
if [[ $hour < 04 ]]; then
    prevhr=$((hour + 20))
elif [[ $hour < 14 ]]; then
    prevhr="0$(echo "$hour - 4" | bc)"
else
    prevhr=$((hour - 4))
fi

### Combine balance data from both files and subtract both
previous=$(sort captures/$prevhr/$minute/$FILE | cut -d " " -f 3)
result=$(paste <(echo "$current") <(echo "$previous") | awk '{print $1, $2, $3 - $4}')

# Run generation scripts
gentxt
gencsv
genjson
