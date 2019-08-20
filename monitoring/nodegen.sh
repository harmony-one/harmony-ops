#!/bin/bash

NODES=500
mkdir -p keypairs
rm -f nodes.csv keys.go
rm -rf generated
WalletPublicKey=""
BlsPublicKey=""
BlsPrivateKey=""
WalletFile=""
BlsFile=""

mkdir -p generated
printf "WalletPublicKey,BlsPublicKey,BlsPrivateKey,WalletFile,BlsFile\n" >> generated/nodes.csv

for (( NODE=0; NODE<NODES; NODE++ ))
do
    echo "Generating Node #$NODE"
    new=`./wallet.sh new --nopass`
    blsgen=`./wallet.sh blsgen --nopass`
    WalletPublicKey=`echo "$new" |grep "account" |cut -f 2 -d ":" |cut -c 2-`
    WalletFile=`echo "$new" |grep "URL" |cut -f 3 -d ":" |cut -c 3-`
    BlsPublicKey=`echo "$blsgen" |grep "Bls public" |cut -f 2 -d ":" |cut -c 2-`
    BlsPrivateKey=`echo "$blsgen" |grep "Bls private" |cut -f 2 -d ":" |cut -c 2-`
    BlsFile=`echo "$blsgen" |grep "File" |cut -f 2 -d ":" |cut -c 2-`
    mkdir -p "generated/keypairs/node-$NODE"
    mv "./$BlsFile" "generated/keypairs/node-$NODE/"
    mv "$WalletFile" "generated/keypairs/node-$NODE/"
    WalletFileCut=`echo "$WalletFile" | rev | cut -c -77 | rev`
    printf "$WalletPublicKey,$BlsPublicKey,$BlsPrivateKey,$WalletFileCut,$BlsFile\n" >> generated/nodes.csv
    printf "\t{Index:\"$NODE\", Address: \"$WalletPublicKey\", BlsPublicKey: \"$BlsPublicKey\"},\n" >> generated/keys.go
done
