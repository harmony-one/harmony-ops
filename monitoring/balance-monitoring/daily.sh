#!/usr/bin/env bash

# daily.sh - Generates daily report of balances

# Specific interval constants
prefix=generated/24h/24h
textfile=$prefix.txt
csvfile=$prefix.csv
jsonfile=$prefix.json
csvextra="ONEs Per Day"
jsonextra="ONEsPerDay"

### Get functions and constants
source monitoring.sh

### Set constants for previous then get the diff
file="temp.txt"
prevhr=$hour
prevmin=$minute
getdiff

### Run generation scripts
gentxt
gencsv
genjson

# Remove temp file
rm captures/$hour/$minute/temp.txt