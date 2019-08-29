msg() {
	case $# in
	[1-9]*)
		#echo "${progname+"${progname}: "}$*" >&2
		;;
	esac
}

err() {
	local status
	status="${1-1}"
	shift 1 2> /dev/null || :
	#msg "$@"
	exit "${status}" || exit 1
}

msg_exit() {
	err "$@"
}
