#!/bin/bash

ME=$(basename $0)
ACTION=${1}
HOSTS=${2:-hosts.txt}
OUT=${3}

declare -A OPS
OPS[ps]="ps -ef | grep harmony"
OPS[viewid]='tail -n 50 ../tmp_log/log-*/*.log | grep -o "myViewID.:[0-9]*" | tail -n 1'
OPS[soldier]='tail -n 3 soldier-*.log'
OPS[kill]='sudo pkill harmony'
OPS[nodelog]='tail -n 20 ../tmp_log/log-*/*.log'
OPS[cleandb]="sudo rm -rf harmony_db_*"
OPS[upgrade]="mv -f harmony harmony.orig && s3 cp s3://pub.harmony.one/release/linux-x86_64/drum/harmony . && chmod +x harmony"

declare -A USAGE
USAGE[ps     ]="run ps command to check existence of harmony process"
USAGE[viewid ]="find the latest viewid from the log"
USAGE[soldier]="print latest soldier log"
USAGE[kill   ]="kill the harmony process on node"
USAGE[nodelog]="print latest harmony node log"
USAGE[cleandb]="remove existing harmony_db"
USAGE[upgrade]="download latest harmony binary from s3://pub.harmony.one"

function do_op_cmd
{
   op=$1
   outdir=${2:-$op}
   pssh -l ec2-user -h $HOSTS -o $outdir "${OPS[$op]}"
}

function check_env
{
   pssh --version 2>&1 > /dev/null
   if [ "$?" != "0" ]; then
      echo "Please install pssh to continue"
      exit 1
   fi
   if [ -e "$ACTION" ]; then
      usage
   fi
}

function usage
{
   cat<<EOT
Usage: $ME action [host_file] [output_dir]

Actions:

EOT
   for action in "${!USAGE[@]}"; do
      echo -e "\t$action\t\t${USAGE[$action]}"
   done
   echo
}

check_env

actions=" ${!OPS[@]} "

if [[ $actions =~ " $ACTION " ]]; then
   do_op_cmd $ACTION $OUT
else
   usage
fi
