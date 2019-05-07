#!/bin/bash


curl -O https://raw.githubusercontent.com/harmony-one/harmony/master/scripts/wallet.sh

mkdir /home/ec2-user/$(date +%Y%m%d_%H%M%S)



ps -ef | grep harmony

grep panic /home/ec2-user/soldier-*.log
