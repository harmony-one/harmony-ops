#!/bin/bash

function usage
{
   ME=$(basename $0)
   cat<<EOT

This script is the 1st step of Harmony devop automation.
It can be used to check the host uptime, existence of soldier/harmony process.
Or to start soldier/harmony process, and check the log files on a host file.

Usage:

   $ME [options] host_file

Options:
   -h                print this help message
   -a action         individual action to be executed
   -p profile        launch profile (default: $PROFILE)

Actions:
   uptime            check the uptime
   soldier           check the pid of the soldier process
   harmony           check the pid of the harmony process
   start_soldier     start the soldier process
   start_harmony     reinit/start the harmony process
   log               print the last 10/x lines of validator-*.log
   hooray            grep the HOORAY from the last 1000 lines of validator-*.log
   bingo             grep the BINGO from the last 1000 lines of validator-*.log
   workflow_1        workflow of checking and restarting soldier/harmony process (DEFAULT)

Examples:

# host_file contains a list of IP addresses of the host to be examined
# one IP address per line

   $ME -a uptime host-1.txt

   $ME -a log host-2.txt 100

EOT
   exit 0
}

function uptime
{
   echo ============================
   read -p "checking uptime (y/n)?" yn
   if [[ "$yn" == "y" || "$yn" == "Y" ]]; then
      for i in $(cat $HOST); do
         echo $i
         ${SSH} -p $PROFILE ec2-user@$i 'uptime';
      done
   fi
}

function soldier
{
   echo ============================
   read -p "checking soldier process (y/n)?" yn
   if [[ "$yn" == "y" || "$yn" == "Y" ]]; then
      for i in $(cat $HOST); do
         echo $i
         ${SSH} -p $PROFILE ec2-user@$i 'pgrep soldier';
      done
   fi
}

function harmony
{
   echo ============================
   read -p "checking harmony process (y/n)?" yn
   if [[ "$yn" == "y" || "$yn" == "Y" ]]; then
      for i in $(cat $HOST); do
         echo $i
         ${SSH} -p $PROFILE ec2-user@$i 'pgrep harmony';
      done
   fi
}

function start_soldier
{
   echo ============================
   read -p "restart soldier (y/n)?" yn
   if [[ "$yn" == "y" || "$yn" == "Y" ]]; then
      for i in $(cat $HOST); do
         echo $i
         ${SSH} -p $PROFILE ec2-user@$i "nohup sudo /home/ec2-user/soldier -ip $i -port 9000 > soldier-restart.log 2> soldier-restart.err < /dev/null &";
      done
   fi
}

function start_harmony
{
   echo ============================
   read -p "restart harmony process (y/n)?" yn
   if [[ "$yn" == "y" || "$yn" == "Y" ]]; then
      ./go.sh -p $PROFILE reinit $(cat $HOST | tr "\n" " ")
   fi
}

function log
{
   num=${1:-10}
   echo ============================
   read -p "checking last $num lines of logs (y/n)?" yn
   if [[ "$yn" == "y" || "$yn" == "Y" ]]; then
      for i in $(cat $HOST); do
         echo "********** checking $i ***********";
         ${SSH} -p $PROFILE ec2-user@$i "tail -n $num ../tmp_log/*/validator*.log ";
         echo;
      done
   fi
}

function bingo
{
   echo ============================
   read -p "checking BINGO (y/n)?" yn
   if [[ "$yn" == "y" || "$yn" == "Y" ]]; then
      echo sleeping 30 sec ...
      sleep 30
      for i in $(cat $HOST); do
         echo "********** checking $i ***********";
         ${SSH} -p $PROFILE ec2-user@$i 'tac ../tmp_log/*/validator*.log | grep -m 1 BINGO ';
         echo;
      done
   fi
}

function hooray
{
   echo ============================
   read -p "checking HOORAY (y/n)?" yn
   if [[ "$yn" == "y" || "$yn" == "Y" ]]; then
      echo sleeping 30 sec ...
      sleep 30
      for i in $(cat $HOST); do
         echo "********** checking $i ***********";
         ${SSH} -p $PROFILE ec2-user@$i 'tac ../tmp_log/*/validator*.log | grep -m 1 HOORAY';
         echo;
      done
   fi
}

function do_workflow_one
{
   uptime
   soldier
   harmony
   start_soldier
   soldier
   start_harmony
   harmony
   log
   bingo
}

function check_env
{
   if [ ! -e ${SSH} ]; then
      echo "missing ${SSH} file, please run this script in experiment-deploy/pipeline directory"
      exit 2
   fi
   if [ ! -f ${HOST} ]; then
      echo "missing ${HOST} file"
      exit 2
   fi
}

############ main #############
ACTION=workflow_1
PROFILE=r3
SSH=./node_ssh.sh

while getopts ":ha:p:" opt; do
   case $opt in
      a) ACTION=$OPTARG ;;
      p) PROFILE=$OPTARG ;;
      *) usage ;;
   esac
done
shift $(($OPTIND - 1))

HOST=$1
shift

if [ -z "$HOST" ]; then
   usage
fi

check_env

case $ACTION in
   uptime) uptime ;;
   soldier) soldier ;;
   harmony) harmony ;;
   start_soldier) start_soldier ;;
   start_harmony) start_harmony ;;
   log) log $*;;
   bingo) bingo ;;
   hooray) hooray ;;
   workflow_1) do_workflow_one ;;
esac


