#!/usr/bin/env bash
# this script is used to manage uptime robot monitors
#
# get the uptime monitor
# find the monitor id based on ip
# update the uptime monitor

ME=`basename $0`

# set -x

if [ "$(uname -s)" == "Darwin" ]; then
   TIMEOUT=gtimeout
else
   TIMEOUT=timeout
fi

function logging
{
   echo $(date) : $@
   SECONDS=0
}

function expense
{
   local step=$1
   local duration=$SECONDS
   logging $step took $(( $duration / 60 )) minutes and $(( $duration % 60 )) seconds
}

function errexit
{
   logging "$@ . Exiting ..."
   exit -1
}

function verbose
{
   [ $VERBOSE ] && echo $@
}

function usage
{
   cat<<EOF
Usage: $ME [Options] Command

OPTIONS:
   -h                         print this help message
   -v                         verbose mode
   -G                         do the real job
   -K keyfile                 specify the file holding the uptime robot api key
   -D dbdir                   specify the directory for the db
   -t tag                     specify the tag in the name of the monitor (default: $TAG)

COMMANDS:
   batchnew [shard] [file]    new uptime robot monitors, loading ip from [file]
   new [ip] [shard]           new uptime robot monitor
   get [shard]                get all uptime robot monitors from [shard]
   update [name] [ip] [shard] update the uptime robot monitor [name] using new ip/shard
   find [name]                find the details of monitor with [name]

EXAMPLES:

   $ME -v

EOF
   exit 0
}

function _get_monitor_name()
{
   local shard=$1
   local ip=$(echo $2 | cksum | awk ' { print $1 } ')

   echo "s-$shard-$TAG-$ip"
}

function new_monitors()
{
   local shard=$1
   local file=$2

   if [ ! -e $file ]; then
      errexit $file does not exist
   fi

   while read ip; do
      new_monitor $shard $ip
   done<$file
}

function new_monitor ()
{
	local shard=$1
	local ip=$2

   name=$(_get_monitor_name $shard $ip)

   $DRYRUN curl -X POST \
        -H "Cache-Control: no-cache" \
		  -H "Content-Type: application/x-www-form-urlencoded" \
        -d 'api_key='${api_key}'&format=json&type=4&sub_type=99&url='${ip}"&port=6000&friendly_name=${name}&alert_contacts=0754344_0_0-2840345_0_0-2840345_0_0-2842973_0_0" \
        "https://api.uptimerobot.com/v2/newMonitor"
}

function get_monitors()
{
   local shard=$1
   local LIMIT=50

   $DRYRUN curl -X POST \
        -H "Cache-Control: no-cache" \
		  -H "Content-Type: application/x-www-form-urlencoded" \
        -d "api_key=${api_key}&format=json&logs=1&limit=$LIMIT" "https://api.uptimerobot.com/v2/getMonitors" -o $DBDIR/uptime-0.json
   [ -n "$DRYRUN" ] && return
   total=$($JQ ".pagination.total" $DBDIR/uptime-0.json)
   pages=$(( $total / $LIMIT - 1 ))
   for page in $(seq 1 $pages); do
      offset=$(( $LIMIT * page ))
      $DRYRUN curl -X POST \
           -H "Cache-Control: no-cache" \
           -H "Content-Type: application/x-www-form-urlencoded" \
           -d "api_key=${api_key}&format=json&logs=1&offset=$offset&limit=$LIMIT" "https://api.uptimerobot.com/v2/getMonitors" -o $DBDIR/uptime-$page.json
   done

   for page in $(seq 0 $pages); do
      $DRYRUN $JQ ".monitors[] | {id:.id, ip:.url, name:.friendly_name} |[.id, .ip, .name] | @csv" $DBDIR/uptime-$page.json > $DBDIR/ids-$page.csv
   done

   cat $DBDIR/ids-*.csv > $DBDIR/ids.csv
}

function find_monitor()
{
   local name=$1
   id=$(grep -m 1 $name $DBDIR/ids.csv | cut -f1 -d,)
   echo $id
}

function update_monitor()
{
   local name=$1
   local ip=$2
   local shard=$3

   logging update monitor

   id=$(find_monitor $name)
   if [ -z "$id" ]; then
      errexit can not find monitor with name: $name
   fi
   name=$(_get_monitor_name $shard $ip)

   $DRYRUN curl -X POST \
        -H "Cache-Control: no-cache" \
		  -H "Content-Type: application/x-www-form-urlencoded" \
        -d "api_key=${api_key}&id=$id&url=$ip&friendly_name=${name}&format=json&logs=1&limit=$LIMIT" "https://api.uptimerobot.com/v2/editMonitor"
}

# sync the monitor db to/from s3
function _sync_backend()
{
	logging syncing backend
	expense 'syncing backend'
}

function _init
{
	if [ -f "$KEY" ]; then
		api_key=$(cat $KEY)
	else
		errexit can not find the api key file: $KEY
	fi

	if [ -z "$DRYRUN" ]; then
		_sync_backend
	fi

   mkdir -p $DBDIR
}

DRYRUN=echo
DBDIR=db
KEY=uptimerobot_api_key.txt
JQ='jq -M -r'
TAG=node

while getopts "hvGK:D:t:" option; do
   case $option in
      v) VERBOSE=-v ;;
      G) unset DRYRUN ;;
		K) KEY=$OPTARG ;;
      D) DBDIR=$OPTARG ;;
      t) TAG=$OPTARG ;;
      h|?|*) usage ;;
   esac
done

shift $(($OPTIND-1))

CMD=$1
shift

if [ -z "$CMD" ]; then
   usage
fi

_init

###############################################################################
case $CMD in
	batchnew)
		new_monitors $*
		;;
	new)
		new_monitor $*
		;;
	get)
		get_monitors $*
		;;
	update) 
		update_monitor $*
		;;
   find)
      find_monitor $*
      ;;
   *) usage ;;
esac

if [ ! -z $DRYRUN ]; then
   echo '***********************************'
   echo "Please use -G to do the real work"
   echo '***********************************'
	exit
fi

_sync_backend
