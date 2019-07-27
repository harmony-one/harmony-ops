#!/usr/bin/env bash

# offline.sh - Generates offline addresses file

# Get file constants/date variables
source monitoring.sh

# Get 15 minutes before current time
if [[ $minute = 00 ]]; then
    prevmin="45"
    if [[ $hour = 00 ]]; then
        prevhr="23"
    elif [[ $hour < 11 ]]; then
        prevhr="0$(echo "$hour - 1" | bc)"
    else
	prevhr=$((hour - 1))
    fi
else
    if [[ $minute == 15 ]]; then
        prevmin="00"
    else
        prevmin=$((minute - 15))
    fi
    prevhr="$hour"
fi

### Combine balance data from both files and find difference
previous=$(sort captures/$prevhr/$prevmin/$FILE | cut -d " " -f 3)
result=$(paste <(echo "$current") <(echo "$previous") |\
	     awk '{print $1, $2, $3 - $4}')

# Find offline addresses
echo "$result" | awk -F " " '$3 == 0' | cut -d " " -f 1 > $OFFLINE
