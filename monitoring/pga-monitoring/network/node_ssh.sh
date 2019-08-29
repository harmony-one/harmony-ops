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
. "${progdir}/util.sh"
. "${progdir}/log.sh"

log_define node_ssh

print_usage() {
	cat <<- ENDEND
		usage: ${progname} ${common_usage} [-M] [-o opt] [user@]ipaddr [command]

		${common_usage_desc}

		options:
		-o opt		add an extra ssh(1) option
		-p profile	use specified profile
		-M		use opportunistic ssh connection multiplexing
		 		(helps back-to-back invocations); -M -M uses fresh mux

		arguments:
		user		remote username (default: same as local)
		ipaddr		IP address of the node
		command		the shell command to run on the host;
		 		if not given, use interactive shell
	ENDEND
}

unset -v use_ssh_mux exit_mux_first ssh_opts
use_ssh_mux=false
exit_mux_first=false
ssh_opts=""

unset -v OPTIND OPTARG opt
OPTIND=1
while getopts ":o:M${common_getopts_spec}" opt
do
	! process_common_opts "${opt}" || continue
	case "${opt}" in
	'?') usage "unrecognized option -${OPTARG}";;
	':') usage "missing argument for -${OPTARG}";;
	o) ssh_opts="${ssh_opts} $(shell_quote "${OPTARG}")";;
	M) exit_mux_first="${use_ssh_mux}"; use_ssh_mux=true;;
	*) err 70 "unhandled option -${OPTARG}";;
	esac
done
shift $((${OPTIND} - 1))
default_common_opts

unset -v userip user ip cmd_quoted
userip="${1-}"
shift 1 2> /dev/null || usage "missing IP address"
case "${userip}" in
*@*)
	user="${userip%%@*}"
	ip="${userip#*@}"
	;;
*)
	user=$(id -un)
	ip="${userip}"
	;;
esac
cmd_quoted=$(shell_quote "$@")

unset -v key_file
key_file="${progdir}/keys/harmony-node.pem"

unset -v dist_config line name_tag
dist_config="${logdir}/distribution_config.txt"
line=$(awk -v ip="${ip}" '$1 == ip { print $4, $5; }' "${dist_config}" | head -1)
case "${line}" in
"")
	node_ssh_info "${ip} not found in ${dist_config}; assuming it is a Terraform-deployed node"
	;;
*)
	name_tag="${line#* }"
	unset -v region_code region_config key_name
	region_code="${name_tag%%-*}"
	region_config="${progdir}/configuration.txt"
	key_name=$(awk -F , -v code="${region_code}" '$1 == code { print $3; }' "${region_config}" | head -1)
	case "${key_name}" in
	"") node_ssh_fatal 69 "region code ${region_code} not found in ${region_config}";;
	esac
	key_file="${progdir}/keys/${key_name}.pem"
	;;
esac
node_ssh_info "autodetected key file $(shell_quote "${key_file}")"

if ${use_ssh_mux}
then
	mkdir -p ~/.ssh/ctl
fi

unset -v known_hosts_file
known_hosts_file="${logdir}/known_hosts"

set -- \
	-F /dev/null \
	-o GlobalKnownHostsFile=/dev/null \
	-o UserKnownHostsFile="${known_hosts_file}" \
	-o StrictHostKeyChecking=no \
	-o ServerAliveInterval=60 \
	-o ConnectTimeout=10

if ${use_ssh_mux}
then
	set -- "$@" \
		-o ControlPath='~/.ssh/ctl/%r@%h[%p]' \
		-o ControlMaster=auto \
		-o ControlPersist=yes
fi

if [ -f "${key_file}" ]
then
	set -- "$@" -i "${key_file}"
else
	node_ssh_info "key file does not exist; proceeding without one"
fi

if ${exit_mux_first}
then
	ssh "$@" -O exit "${userip}" || :
fi

eval 'set -- "$@" '"${ssh_opts}"
set -- "$@" "${userip}"
eval 'set -- "$@" '"${cmd_quoted}"
exec ssh "$@"
