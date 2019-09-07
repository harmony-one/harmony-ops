#!/usr/bin/env bash

SHARDS=4
month=$(date +%m)
day=$(date +%d)
hour=$(date +%H)
minute=$(date +%M)
date=$(date +"%a %b $day $hour:$minute:00 UTC %Y")
capture_loc="captures/$month/$day/$hour/$minute"
textfile="generated/network.txt"
csvfile="generated/network.csv"
jsonfile="generated/network.json"
sectionhead="==================================================================="
leaders=( 3.18.213.133 54.229.185.178 54.244.174.138 18.207.224.141 )
addresses=$(curl -sL https://bit.ly/pga-keys | grep Address)
internal=$(curl -sL https://bit.ly/pge-keys | grep Address | cut -d '"' -f 6)
onlinetxt="generated/online-"
offlinetxt="generated/offline-"

function check_online () {
    log=$(./extras/node_ssh.sh -p pangaea ${leaders[$1]} tail -n 1250 ../tmp_log/*/zerolog*.log)
    online=$(echo "$log" | grep Prepare | grep -oE "\"validatorPubKey\":\"[a-zA-Z0-9]*\"" | cut -d '"' -f 4 | sort -u)
    #echo "$online" > test-online-$1.txt
    overlap=$(echo "$log" | grep Prepare | grep Already | grep -oE "\"validatorPubKey\":\"[a-zA-Z0-9]*\"" | cut -d '"' -f 4 | sort -u)
    #echo "$overlap" > test-overlap-$1.txt
    bls=$(./extras/run_on_shard.sh -T $1 'ls *.key' | grep -oE "^[a-zA-Z0-9]{96}" | grep -v -f <(echo "$internal"))
    #echo "$bls" > test-bls-$1.txt
    external=$(printf "$online" | grep -v -f <(echo "$bls") | sort -u)
    #echo "$external" > test-external-$1.txt
    if [[ $(printf "$external$overlap" | wc -c) = 0 ]]; then
        printf "" > $onlinetxt$1.txt
        sleep 5
    else
        grep -f <(printf "$external\n$overlap") <(echo "$addresses") | cut -d '"' -f 6 > $onlinetxt$1.txt
    fi
}

function print_txt {
    for (( num=0; num < $SHARDS; num++ )); do
        # Get only shard addresses
        data=$(grep -f $prefix$num.txt extras/pangaea.go |\
               grep -oE "one[0-9a-zA-Z]*" | sort)
        numAddresses=$(echo "$data" | wc -l)
        printf "\nShard $num: $numAddresses nodes\n---------------\n" >> $textfile
        # If there are none, print "None"
        if [[ $(printf "$data" | wc -c) = 0 ]]; then
            printf "$none\n" >> $textfile
        else
            printf "$data\n" >> $textfile
        fi
    done
}

function gentxt {
    printf "[$date]\n" > $textfile

    printf "\nSHARD STATUS\n$sectionhead\n" >> $textfile
    echo "$leader_data" >> $textfile

    none="None..."
    prefix="$onlinetxt"
    printf "\nONLINE: $(cat $prefix* | wc -l) total\n$sectionhead" >> $textfile
    print_txt

    ### Offline portion
    none="None!"
    prefix="$offlinetxt"
    printf "\nOFFLINE: $(cat $prefix* | wc -l) total\n$sectionhead" >> $textfile
    print_txt

    mkdir -p $capture_loc
    cat $textfile > $capture_loc/$textfile
}

### Generate csvfile
function gencsv {
    # Header
    printf "Address,Shard,Online\n" > $csvfile

    # Print online addresses
    for (( num=0; num < $SHARDS; num++ )); do
        grep -f $onlinetxt$num.txt extras/pangaea.go |\
        grep -oE "one[0-9a-zA-Z]*" | sort |\
        awk '{print $1, "'"$num"'", "true"}' | sed 's/\ /,/g' >> $csvfile
    done

    # Print online addresses
    for (( num=0; num < $SHARDS; num++ )); do
        grep -f $offlinetxt$num.txt extras/pangaea.go |\
        grep -oE "one[0-9a-zA-Z]*" | sort |\
        awk '{print $1, "'"$num"'", "false"}' | sed 's/\ /,/g' >> $csvfile
    done

    cat $csvfile > $capture_loc/$csvfile
}

### Generate jsonfile
function genjson {
    {
    # Header
    echo "{"

    # Total Node Count
    echo "\"node_count\": {"
    echo "\"online\": $(cat $onlinetxt*.txt | wc -l),"
    echo "\"offline\": $(cat $offlinetxt*.txt | wc -l)"
    echo "},"

    # Shards
    echo "\"shards\": {"
    {
    for (( num=0; num < $SHARDS; num++ )); do
        data=$(grep "Shard $num" <(echo "$leader_data"))
        echo "\"$num\": {"
        echo "\"shard_number\": $num,"
        echo "\"block_number\": $(echo $data | cut -d "." -f 1 |\
                                  cut -d " " -f 6),"
        echo "\"status\": \"$(echo $data | grep -oE "(OFF|ON)LINE" |\
                              tr '[:upper:]' '[:lower:]')\","
        echo "\"last_updated\": \"$(date -d "$(echo $data |\
                                               sed 's/.*updated: //' |\
                                               sed 's/)//')" +%FT%T%:z)\","
        echo "\"node_count\": {"
        echo "\"online\": $(cat $onlinetxt$num.txt | wc -l),"
        echo "\"offline\": $(cat $offlinetxt$num.txt | wc -l)"
        echo "},"
        echo "\"nodes\": {"
        echo "\"online\": ["
        grep -f $onlinetxt$num.txt extras/pangaea.go |\
        grep -oE "one[0-9a-zA-Z]*" | sort | awk '{print "\""$1"\","}' |\
        sed '$s/,$//'
        echo "],"
        echo "\"offline\": ["
        grep -f $offlinetxt$num.txt extras/pangaea.go |\
        grep -oE "one[0-9a-zA-Z]*" | sort | awk '{print "\""$1"\","}' |\
        sed '$s/,$//'
        echo "]"
        echo "}"
        echo "},"
    done
    } | sed '$s/,$//'
    echo "}"
    echo "}"
    } | jq '.' > $jsonfile

    cat $jsonfile > $capture_loc/$jsonfile
}

function check_leader_status
{
    s=0
    for ip in ${leaders[@]}; do
        block=$(./extras/node_ssh.sh -p pangaea ec2-user@$ip 'tac /home/tmp_log/*/zerolog-validator-*.log | grep -m 1 -F HOORAY | jq .blockNum')
        time=$(./extras/node_ssh.sh -p pangaea ec2-user@$ip 'tac /home/tmp_log/*/zerolog-validator-*.log | grep -m 1 -F HOORAY | jq .time' | sed 's/Z//' | tr T \ | tr \" \ )
        if [[ -z $block ]]; then
            block=0
        fi
        printf "Shard $s leader is on Block $block. Status is: "
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

function find_offline_keys
{
    local shard=$1
    local file=${2:-$onlinetxt${shard}.txt}
    i=0
    while read bls; do
        key=$(echo $bls | cut -f1 -d\.)
        shardid=$( expr $i % 4 )
        if [ $shardid == $shard ]; then
            if ! grep -q $key $file; then
                echo $key
            fi
        fi
        (( i++ ))
    done < "./extras/pangaea-keys.txt"
}

for (( num=0; num < $SHARDS; num ++)); do
    check_online $num
    find_offline_keys $num > $offlinetxt$num.txt
done

leader_data=$(check_leader_status)
gentxt
gencsv
genjson