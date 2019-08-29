#!/bin/sh

set -eu

unset -v progname progdir
progname="${0##*/}"
case "${0}" in
*/*) progdir="${0%/*}";;
*) progdir=".";;
esac

. "${progdir}/msg.sh"
. "${progdir}/usage.sh"
. "${progdir}/common_opts.sh"

print_usage() {
	cat <<- ENDEND
		usage: ${progname} ${common_usage} shard ...

		${common_usage_desc}

		options:

		shard		the shard number, such as 0
	ENDEND
}

unset -v OPTIND OPTARG opt
OPTIND=1
while getopts :${common_getopts_spec} opt
do
	! process_common_opts "${opt}" || continue
	case "${opt}" in
	'?') usage "unrecognized option -${OPTARG}";;
	':') usage "missing argument for -${OPTARG}";;
	*) err 70 "unhandled option -${OPTARG}";;
	esac
done
shift $((${OPTIND} - 1))
default_common_opts

case $# in
0) usage "missing shard argument";;
esac

unset -v shard
for shard
do
	"${progdir}/run_on_shard.sh" -p "${profile}" -d "${logdir}"  -rTSE  "${shard}" '
		zcat ../tmp_log/*/zero*.log.gz latest/zero*.log.gz 2> /dev/null |
		cat - ../tmp_log/*/zero*.log latest/zero*.log 2> /dev/null |
		grep -F '\''"Add Peer to Node"'\''
	' > "raw-${shard}.txt" &
done
wait
