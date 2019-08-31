#!/bin/sh

set -eu

unset -v progname progdir
progname="${0##*/}"
case "${0}" in
*/*) progdir="extras";;
*) progdir="extras";;
esac

. "${progdir}/msg.sh"
. "${progdir}/usage.sh"
. "${progdir}/common_opts.sh"
. "${progdir}/util.sh"
. "${progdir}/log.sh"

log_define -v sync_logs_log_level -l DEBUG sl

: ${WHOAMI=`id -un`}
export WHOAMI

unset -v default_bucket default_owner
default_bucket=unique-bucket-bin
default_owner="${WHOAMI}"

print_usage() {
	cat <<- ENDEND
		usage: ${progname} ${common_usage} [-q] [-o owner] [-b bucket] [-f folder]

		${common_usage_desc}

		options:
		-q		quick mode; do not download logs or databases
		-o owner	owner name (default: ${default_owner})
		-b bucket	bucket to configure into profile json (default: ${default_bucket})
		-f folder	folder to configure into profile json (default: same as owner)
	ENDEND
}

unset -v bucket folder owner quick
quick=false

unset -v OPTIND OPTARG opt
OPTIND=1
while getopts ":b:f:o:q${common_getopts_spec}" opt
do
	! process_common_opts "${opt}" || continue
	case "${opt}" in
	'?') usage "unrecognized option -${OPTARG}";;
	':') usage "missing argument for -${OPTARG}";;
	o) owner="${OPTARG}";;
	b) bucket="${OPTARG}";;
	f) folder="${OPTARG}";;
	q) quick=true;;
	*) err 70 "unhandled option -${OPTARG}";;
	esac
done
shift $((${OPTIND} - 1))
default_common_opts

: ${owner="${default_owner}"}
: ${bucket="${default_bucket}"}
: ${folder="${owner}"}

sl_info "fetching latest timestamp from S3 log folder"
unset -v latest_uri timestamp session_id
latest_uri="s3://harmony-benchmark/logs/latest-${owner}-${profile}.txt"
timestamp=$(aws s3 cp "${latest_uri}" -) || err 69 "cannot fetch latest timestamp"
sl_debug "timestamp=$(shell_quote "${timestamp}")"
session_id=$(echo "${timestamp}" | sed -n 's@^\([0-9][0-9][0-9][0-9]\)/\([0-9][0-9]\)/\([0-9][0-9]\)/\([0-9][0-9][0-9][0-9][0-9][0-9]\)$@\1\2\3.\4@p')
case "${session_id}" in
"") err 69 "cannot convert timestamp $(shell_quote "${timestamp}") into session ID; is it in YYYY/MM/DD/HHMMSS format?";;
esac

sl_info "syncing logs from S3"
if ${quick}
then
	set -- --exclude='*/tmp_log/*' --exclude='*/db-*.tgz' --exclude='*/soldier-*.log'
else
	set --
fi
aws s3 sync "s3://harmony-benchmark/logs/${timestamp}" "${progdir}/logs/${session_id}" "$@"
sl_info "resetting log symlink"
rm -f "${progdir}/logs/${profile}"
ln -sf "${session_id}" "${progdir}/logs/${profile}"
sl_info "finished"
