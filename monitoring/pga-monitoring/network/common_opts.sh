. "${progdir}/msg.sh"
. "${progdir}/usage.sh"

: ${WHOAMI=`id -un`}
export WHOAMI

unset -v default_profile
default_profile="${HMY_PROFILE-"${WHOAMI}"}"

unset -v common_usage common_usage_desc
common_usage="[-h] [-d logdir] [-p profile]"
common_usage_desc="common options:
-d logdir	use the given logdir
-p profile	use the given profile (default: ${default_profile})
-h		print this help"

unset -v logdir profile

unset -v common_getopts_spec
common_getopts_spec=hd:p:

process_common_opts() {
	case "${1-}" in
	d) logdir="${OPTARG}";;
	p) profile="${OPTARG}";;
	h) print_usage; exit 0;;
	*) return 1;;
	esac
}

default_common_opts() {
	: ${profile="${default_profile}"}
	: ${logdir="logs/${profile}"}
}
