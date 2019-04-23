#!/bin/bash

mkdir /home/ec2-user/$(date +%Y%m%d_%H%M%S)

ps -ef | grep harmony

grep panic /home/ec2-user/soldier-*.log
