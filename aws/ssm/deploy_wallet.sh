#!/bin/bash


cd /home/ec2-user

curl -O https://raw.githubusercontent.com/harmony-one/harmony/master/scripts/wallet.sh

chmod +x wallet.sh

./wallet.sh -d