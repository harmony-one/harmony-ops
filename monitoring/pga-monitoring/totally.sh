#!/usr/bin/env bash

# totally.sh - Generates report of all balances

# Specific interval constants
prefix=generated/balances/balances
textfile=$prefix.txt
csvfile=$prefix.csv
jsonfile=$prefix.json
csvextra="Total Balance"
jsonextra="totalBalance"

### Get functions and constants
source monitoring.sh

### Just grab total balances
result=$current

### Run generation scripts
gentxt
gencsv
genjson