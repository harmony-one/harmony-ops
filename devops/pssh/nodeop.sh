#!/bin/bash

ME=$(basename $0)
ACTION=${1}
HOSTS=${2:-hosts.txt}
OUT=${3}
EXTRA=${4}

declare -A OPS
OPS[ps]="pgrep PROCESS | grep ^[0-9]"
OPS[viewid]='tail -n 50 ../tmp_log/log-*/*.log | grep -o "myViewID.:[0-9]*" | tail -n 1'
OPS[soldier]='tail -n 3 soldier-*.log'
OPS[kill]='sudo pkill PROCESS'
OPS[nodelog]='tail -n 20 ../tmp_log/log-*/*.log'
OPS[cleandb]="sudo rm -rf harmony_db_*"
OPS[mvharmony]="sudo mv -f harmony harmony.orig"
OPS[upgrade]="aws s3 cp s3://pub.harmony.one/release/linux-x86_64/drum/harmony . ; chmod +x harmony"

declare -A USAGE
USAGE[ps     ]="run ps command to check existence of PROCESS"
USAGE[viewid ]="find the latest viewid from the log"
USAGE[soldier]="print latest soldier log"
USAGE[kill   ]="kill the PROCESS on node"
USAGE[nodelog]="print latest harmony node log"
USAGE[cleandb]="remove existing harmony_db"
USAGE[mvharmony]="move harmony to harmony.orig"
USAGE[upgrade]="download latest harmony binary from s3://pub.harmony.one"

function do_op_cmd
{
   op=$1
   outdir=${2:-$op}

   case $op in
      ps|kill)
         extra=${3:-harmony}
         CMD=$(echo ${OPS[$op]} | sed s/PROCESS/$extra/)
         ;;
      *)
         CMD=${OPS[$op]}
         ;;
   esac

   pssh -l ec2-user -h $HOSTS -o $outdir "$CMD"
}

function check_env
{
   pssh --version 2>&1 > /dev/null
   if [ "$?" != "0" ]; then
      echo "Please install pssh to continue"
      exit 1
   fi
   if [ -z "$ACTION" ]; then
      usage
   fi
}

function usage
{
   cat<<EOT
Usage: $ME action [host_file] [output_dir] [extra_param_to_cmd]

Actions:

EOT
   for action in "${!USAGE[@]}"; do
      echo -e "\t$action\t\t${USAGE[$action]}"
   done
   cat<<EOT

Examples:

   $ME ps all-host.txt allhost soldier

EOT
   exit 0
}

check_env

actions=" ${!OPS[@]} "

if [[ $actions =~ " $ACTION " ]]; then
   do_op_cmd $ACTION $OUT $EXTRA
else
   usage
fi
