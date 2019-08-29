#!/usr/bin/env bash

SHARDS=4
date=$(date +"%a %b %d %H:%M:00 UTC %Y")
textfile=network.txt
sectionhead="==================================================================="
leaders=( 34.217.180.19 52.90.101.87 3.15.213.93 35.164.223.125 )
addresses=$(curl -sL https://bit.ly/pga-keys | grep Address)
internal=$(curl -sL https://bit.ly/pge-keys | grep Address | cut -d '"' -f 6)
function check_online () {
    log=$(./node_ssh.sh -p pangaea ${leaders[$1]} tail -n 10000 ../tmp_log/*/zerolog*.log)
    #lower=$(echo "$log" | grep -n "Sent Announce" | cut -d ":" -f 1 | head -1)
    #upper=$(echo "$log" | grep -n "Sent Announce" | cut -d ":" -f 1 | head -2 | tail -1)
    #length=$((upper - lower))
    #block=$(echo "$log" | awk "NR >=$lower && NR <=$upper")
    online=$(echo "$log" | grep Prepare | grep -oE "\"validatorPubKey\":\"[a-zA-Z0-9]*\"" | cut -d '"' -f 4 | sort -u)
    overlap=$(echo "$log" | grep Prepare | grep Already | grep -oE "\"validatorPubKey\":\"[a-zA-Z0-9]*\"" | cut -d '"' -f 4 | sort -u)
   	bls=$(./run_on_shard.sh -T $1 'ls *.key' | grep -oE "^[a-zA-Z0-9]{96}" | grep -v -f <(echo "$internal"))
    external=$(echo "$online" | grep -v -f <(echo "$bls") | sort -u)
    grep -f <(echo -e "$external\n$overlap") <(echo "$addresses") | cut -d '"' -f 6 > generated/online-ext-keys-sorted-$1.txt
}

function print_txt {
    for (( num=0; num < $SHARDS; num ++)); do
        # Get only shard addresses
        data=$(grep -f $prefix$num.txt pangaea.go | grep -oE "one[0-9a-zA-Z]*" | sort)
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

function check_leader_status
{
   s=0
   for ip in ${leaders[@]}; do
      block=$(./node_ssh.sh -p pangaea ec2-user@$ip 'tac /home/tmp_log/*/zerolog-validator-*.log | grep -m 1 -F HOORAY | jq .blockNum')
      time=$(./node_ssh.sh -p pangaea ec2-user@$ip 'tac /home/tmp_log/*/zerolog-validator-*.log | grep -m 1 -F HOORAY | jq .time' | sed 's/Z//' | tr T \ | tr \" \ )
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

function find_offline_keys
{
   local shard=$1
   local file=${2:-generated/online-ext-keys-sorted-${shard}.txt}
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
   done<"./pangaea-keys.txt"
}

for (( num=0; num < $SHARDS; num ++)); do
    check_online $num
    find_offline_keys $num > offline-ext-keys-$num.txt
done

printf "[$date]\n" > $textfile

printf "\nSHARD STATUS\n$sectionhead\n" >> $textfile
check_leader_status >> $textfile

none="None..."
prefix="online-ext-keys-sorted-"
printf "\nONLINE: $(cat $prefix* | wc -l) total\n$sectionhead" >> $textfile
print_txt

### Offline portion
none="None!"
prefix="offline-ext-keys-"
printf "\nOFFLINE: $(cat $prefix* | wc -l) total\n$sectionhead" >> $textfile
print_txt

mkdir -p captures/$(date +%H)/$(date +%M)
cat $textfile > captures/$(date +%H)/$(date +%M)/$textfile
