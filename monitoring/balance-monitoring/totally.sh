#!/usr/bin/env bash

# Generates hourly report
prefix=generated/balances/balances
textfile=$prefix.txt
csvfile=$prefix.csv
jsonfile=$prefix.json
csvextra="Total Balance"
jsonextra="totalBalance"

# Get functions and constants
source monitoring.sh

### Combine balance data from both files and subtract both
result=$current

# Run generation scripts
gentxt
gencsv
genjson