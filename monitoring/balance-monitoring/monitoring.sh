#!/usr/bin/env bash

# monitoring.sh - Contains date checking constants and printing functions

FILE=balances.txt
ADDRESSES=generated/addresses.txt
OFFLINE=generated/offline.txt

# Get current time
hour=$(date +%H)
minute=$(date +%M)
current=$(sort captures/$hour/$minute/$FILE)
date=$(date +"%a %b %d $hour:$minute:00 UTC %Y")

### Create header
function header {
    # Calculate validating
    echo "[$date]" > $textfile
    total=$(wc -l < $ADDRESSES)
    num_off=$(wc -l < $OFFLINE)
    num_on=$((total - num_off))
    percent=$(echo "$num_on/$total * 100" | bc -l)
    echo "Nodes validating: $num_on/$total = $(printf "%.2f%%\n" $percent)"\
        >> $textfile
}

### Format offline nodes
function print_txt {
    ### Find shard 0
    printf "Shard 0\n-------\n" >> $textfile
    # Get only shard 0 addresses
    zero=$(echo "$data" | awk -F " " '$2 == 0' | awk '{print $1, $3}' |\
           sed 's/\ /:\ /')
    # If there are none, print "None"
    if [[ $(printf "$zero" | wc -c) = 0 ]]; then
        printf "$none\n\n" >> $textfile
    else
        printf "$zero\n\n" >> $textfile
    fi

    ### Find shard 1
    printf "Shard 1\n-------\n" >> $textfile
    # Get only shard 1 addresses
    one=$(echo "$data" | awk -F " " '$2 == 1' | awk '{print $1, $3}' |\
          sed 's/\ /:\ /')
    # If there are none, print "None"
    if [[ $(printf "$one" | wc -c) = 0 ]]; then
        printf "$none\n\n" >> $textfile
    else
        printf "$one\n\n" >> $textfile
    fi

    ### Find shard 2
    printf "Shard 2\n-------\n" >> $textfile
    # Get only shard 2 addresses
    two=$(echo "$data" | awk -F " " '$2 == 2' | awk '{print $1, $3}' |\
          sed 's/\ /:\ /')
    # If there are none, print "None"
    if [[ $(printf "$two" | wc -c) = 0 ]]; then
        printf "$none\n\n" >> $textfile
    else
        printf "$two\n\n" >> $textfile
    fi

    ### Find shard 3 
    printf "Shard 3\n-------\n" >> $textfile
    # Get only shard 3 addresses
    three=$(echo "$data" | awk -F " " '$2 == 3' | awk '{print $1, $3}' |\
            sed 's/\ /:\ /')
    # If there are none, print "None"
    if [[ $(printf "$three" | wc -c) = 0 ]]; then
        printf "$none\n" >> $textfile
    else
        printf "$three\n" >> $textfile
    fi
}

### Generate textfile
function gentxt {
    ### Online portion
    header
    printf "\nONLINE\n==========\n\n" >> $textfile

    # Sort online addresses by balances
    data=$(grep -v -f $OFFLINE <(echo "$result") | sort -r -k 3,3)
    none="None..."
    print_txt

    printf "\nOFFLINE\n==========\n\n" >> $textfile

    # Sort offline addresses by balances
    data=$(grep -f $OFFLINE <(echo "$result") | sort -r -k 3,3)
    none="None!"
    print_txt
}

### Generate csvfile
function gencsv {
    printf "Address,Shard,$csvextra,Online\n" > $csvfile

    # Print online addresses to csvfile
    grep -v -f $OFFLINE <(echo "$result") |\
    awk '{print $1, $2, $3,"true"}' | sed 's/\ /,/g' >> $csvfile

    # Print offline addresses to csvfile
    grep -f $OFFLINE <(echo "$result") |\
    awk '{print $1, $2, $3,"false"}' | sed 's/\ /,/g' >> $csvfile
}

### Generate jsonfile
function genjson {
    # Header
    printf "{\n  " > $jsonfile

    # Date
    printf "\"date\": \"$date\",\n  " >> $jsonfile

    ### Online Nodes
    printf "\"onlineNodes\": [\n    " >> $jsonfile
    firsttime=true
    data=$(grep -v -f $OFFLINE <(echo "$result"))
    # Loop through all data
    while read -r line; do
        if [[ $firsttime = true ]]; then
            firsttime=false
        else
            printf ",\n    " >> $jsonfile
        fi
        printf "{\n      " >> $jsonfile
        printf "\"address\": \"$(echo $line | cut -d " " -f 1)\",\n      "\
               >> $jsonfile
        printf "\"shard\": \"$(echo $line | cut -d " " -f 2)\",\n      "\
               >> $jsonfile
        printf "\"$jsonextra\": \"$(echo $line | cut -d " " -f 3)\",\n    "\
               >> $jsonfile
        printf "}" >> $jsonfile
    done <<< "$data"
    # Closing lines
    printf "\n  " >> $jsonfile
    printf "],\n  " >> $jsonfile

    ### Offline Nodes
    printf "\"offlineNodes\": [\n    " >> $jsonfile
    firsttime=true
    data=$(grep -f $OFFLINE <(echo "$result"))
    # Loop through all data
    while read -r line; do
        if [[ $firsttime = true ]]; then
            firsttime=false
        else
            printf ",\n    " >> $jsonfile
        fi
        printf "{\n      " >> $jsonfile
        printf "\"address\": \"$(echo $line | cut -d " " -f 1)\",\n      "\
               >> $jsonfile
        printf "\"shard\": \"$(echo $line | cut -d " " -f 2)\",\n      "\
               >> $jsonfile
        printf "\"$jsonextra\": \"$(echo $line | cut -d " " -f 3)\",\n    "\
               >> $jsonfile
        printf "}" >> $jsonfile
    done <<< "$data"
    # Closing lines
    printf "\n  " >> $jsonfile
    printf "]\n" >> $jsonfile

    # Footer
    printf "}" >> $jsonfile
}
