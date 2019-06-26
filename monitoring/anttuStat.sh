#!/bin/bash

# stat.sh - Check foundational node status/statistics

echo -e '\n    Date and time     :  \c' && date

# Check if there is bingos in the last 40 lines of the log
working=`tail -n 40 latest/* |grep BINGO`

if [[ "$working" != "" ]]
  then
    echo '    Node status       :  Validating OK! '
  else
    echo '    Not validating!!!'
fi

# Find and show the first time stamp of the log
created=`grep -i -m 1 allocated latest/* |cut -f 7-9 -d ":" |cut -f 1 -d "." |cut -c 2-`

echo -e '    Logging started   :  \c'
echo $created

# Count bingos in the log
echo -e '    Bingos in the log :  \c'
grep -ci bingo latest/*

# Show balances
./wallet.sh balances --address one1kyyt7j29h4uhtnuhfar5wmngntx4gterrkd8q9 |grep -i shard |cut -f 1 -d ","

# Find and show the time of the latest bingo
latest=` cat latest/* |grep -i bingo |tail -n 1 |cut -f 2 -d 'T' |cut -c 1-8`
echo -e '    Latest bingo      :  \c' && echo $latest

# Fetch the time/seconds of the last two bingos
bingos=` cat latest/* |grep -i bingo |tail -n 2 |cut -f 2 -d 'T' |cut -c 1-8`
bingos=` cat latest/* |grep -i bingo |tail -n 2 |cut -f 2 -d 'T' |cut -c 7-8`

bingo1=`echo $bingos |cut -c 1-2`
bingo2=`echo $bingos |cut -c 4-5`

# Delete leading zero
bingo11=`echo $bingo1 |cut -c 1`
if [[ $bingo11 -eq "0" ]]
  then
    bingo1=`echo $bingo1 |cut -c 2`
fi

# Delete leading zero
bingo21=`echo $bingo2 |cut -c 1`
if [[ $bingo21 -eq "0" ]]
  then
    bingo2=`echo $bingo2 |cut -c 2`
fi

# Ensure bingo2 is greater than bingo 1
if [[ $bingo2 -le $bingo1 ]]
  then
    let bingo2+=60
fi

# Calculate and show the time difference
let interval=$bingo2-$bingo1

echo -e '    Bingo interval    : ' $interval 'seconds'
echo
