#!/usr/bin/env bash

# monitoring.sh - Contains date checking constants and printing functions

FILE=balances.txt
OFFLINE=generated/offline.txt
sectionhead="==================================================================="
leaders=( 52.77.216.144 54.190.25.207 34.221.150.79 13.228.72.14 )

# Get current time
hour=$(< generated/hour.txt)
minute=$(< generated/minute.txt)
if [[ "$0" != "./check.sh" ]]; then
    date=$(date +"%a %b %d $hour:$minute:00 UTC %Y")
    if [[ $(($(date +%M) % 15)) != 0 ]]; then
        date=$(date +"%a %b %d %H:%M:00 UTC %Y")
    fi
    current=$(sort captures/$hour/$minute/$FILE)
fi

### Get difference
function getdiff {
    previous=$(sort captures/$prevhr/$prevmin/$FILE)
    caddrs=$(printf "$current" | cut -d " " -f 1)
    paddrs=$(printf "$previous" | cut -d " " -f 1)
if [[ $(diff <(printf "$paddrs") <(printf "$caddrs")) != "" ]]; then
    newaddrs=$(grep -v -f <(printf "$paddrs") <(printf "$caddrs"))
    extra=$(grep -f <(printf "$newaddrs") <(printf "$current"))
    curr=$(grep -v -f <(printf "$newaddrs") <(printf "$current"))
    prev=$(grep -f <(printf "$caddrs") <(printf "$previous"))
    result=$(paste <(printf "$curr") <(printf "$prev") |\
             awk '{print $1, $2, $3 - $6}' && printf "$extra")
else
    result=$(paste <(printf "$current") <(printf "$previous") |\
             awk '{print $1, $2, $3 - $6}')
fi
}

function check_leader_status
{
    s=0
    for ip in ${leaders[@]}; do
        block=$(./extras/node_ssh.sh ec2-user@$ip \
        'tac /home/tmp_log/*/zerolog-validator-*.log | grep -m 1 -F HOORAY |
        jq .blockNum')
        time=$(./extras/node_ssh.sh ec2-user@$ip \
        'tac /home/tmp_log/*/zerolog-validator-*.log | grep -m 1 -F HOORAY |
        jq .time' | sed 's/Z//' | tr T \ | tr \" \ )
        printf "Shard $s is on Block $block. Status is: "
        time1=$(date -d "$time" +%s)
        rawtime=$(date +%s)
        time2=$(($rawtime - 60))
        if [[ $time1 -ge $time2 ]]; then
           printf "ONLINE!   "
        else
           printf "OFFLINE..."
        fi
        printf " (Last updated: $(date -d "$time"))\n"
        (( s++ ))
    done
}

### Create header
function header {
    echo "[$date]" > $textfile

    # Calculate validating w/ new
    total=$(echo "$current" | wc -l)
    num_off=$(wc -l < $OFFLINE)
    num_on=$((total - num_off))
    percent=$(echo "$num_on/$total * 100" | bc -l)
    pctfmt=$(printf "%.2f%%\n" $percent)
    echo "Nodes validating w/ new: $num_on/$total = $pctfmt" >> $textfile

    # Calculate validating w/o new
    new=$(echo "$current" | grep -c -e "-1")
    total=$((total - new))
    num_off=$(wc -l < $OFFLINE)
    num_on=$((total - num_off + new))
    percent=$(echo "$num_on/$total * 100" | bc -l)
    pctfmt=$(printf "%.2f%%\n" $percent)
    echo "Nodes validating w/o new: $num_on/$total = $pctfmt" >> $textfile
    if [[ "$0" = "./totally.sh" ]]; then
        network_total=$(echo "$result" | cut -d " " -f 3 | tr "\n" "+" | \
        sed '$s/+$/\n/' | bc)
        echo "Total ONEs in FN network: $network_total" >> $textfile
    fi

    printf "\nSHARD STATUS\n$sectionhead\n" >> $textfile
    if [[ ! -f generated/leader.txt ]]; then
        check_leader_status >> generated/leader.txt
    fi
    cat generated/leader.txt >> $textfile
}

### Format offline nodes
function print_txt {
    ### Find shard 0
    printf "Shard 0\n--------\n" >> $textfile
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
    printf "Shard 1\n--------\n" >> $textfile
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
    printf "Shard 2\n--------\n" >> $textfile
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
    printf "Shard 3\n--------\n" >> $textfile
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
    printf "\nONLINE (updates every 15 minutes)\n$sectionhead\n" >> $textfile

    # Sort online addresses by balances
    data=$(grep -v -f $OFFLINE <(echo "$result") | sort -nr -k 3,3)
    none="None..."
    print_txt

    ### Offline portion
    printf "\nOFFLINE\n$sectionhead\n" >> $textfile

    # Sort offline addresses by balances
    data=$(grep -f $OFFLINE <(echo "$result") | sort -nr -k 3,3)
    none="None!"
    print_txt

    ### Newly added portion
    printf "\nNEWLY ADDED\n$sectionhead\n" >> $textfile
    new=$(echo "$data" | awk -F " " '$2 == -1' | awk '{print $1}')
    # If there are none, print "None"
    if [[ $(printf "$new" | wc -c) = 0 ]]; then
        printf "$none\n" >> $textfile
    else
        printf "$new\n" >> $textfile
    fi
}

### Generate csvfile
function gencsv {
    # Header
    printf "Address,Shard,$csvextra,Online\n" > $csvfile

    # Print online addresses
    grep -v -f $OFFLINE <(echo "$result") |\
    awk '{print $1, $2, $3,"true"}' | sed 's/\ /,/g' >> $csvfile

    # Print offline addresses
    grep -f $OFFLINE <(echo "$result") |\
    awk '{print $1, $2, $3,"false"}' | sed 's/\ /,/g' >> $csvfile
}

### Generate jsonfile
function genjson {
    # Header
    printf "{\n  " > $jsonfile

    # Date
    printf "\"date\": \"$date\",\n  " >> $jsonfile

    ### Online nodes
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
        printf "\"$jsonextra\": \"$(echo $line | cut -d " " -f 3)\"\n    "\
               >> $jsonfile
        printf "}" >> $jsonfile
    done <<< "$data"
    # Closing lines
    printf "\n  " >> $jsonfile
    printf "],\n  " >> $jsonfile

    ### Offline nodes
    printf "\"offlineNodes\": [\n    " >> $jsonfile
    firsttime=true
    data=$(grep -f $OFFLINE <(echo "$result") | grep -v -e "-1")
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
        printf "\"$jsonextra\": \"$(echo $line | cut -d " " -f 3)\"\n    "\
               >> $jsonfile
        printf "}" >> $jsonfile
    done <<< "$data"
    # Closing lines
    printf "\n  " >> $jsonfile
    printf "],\n  " >> $jsonfile

    ### Newly added nodes
    printf "\"newlyAddedNodes\": [\n    " >> $jsonfile
    firsttime=true
    data=$(grep -e "-1" <(echo "$result"))
    # Loop through all data
    while read -r line; do
        if [[ $firsttime = true ]]; then
            firsttime=false
        else
            printf ",\n    " >> $jsonfile
        fi
        printf "{\n      " >> $jsonfile
        printf "\"address\": \"$(echo $line | cut -d " " -f 1)\"\n    "\
               >> $jsonfile
        printf "}" >> $jsonfile
    done <<< "$data"
    # Closing lines
    printf "\n  " >> $jsonfile
    printf "]\n" >> $jsonfile

    # Footer
    printf "}" >> $jsonfile
}
