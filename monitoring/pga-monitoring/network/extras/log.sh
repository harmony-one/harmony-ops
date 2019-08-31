. "${progdir}/msg.sh"
. "${progdir}/util.sh"

log() {
	local level priority level_ok priority_ok high_enough l
	level="${1-}"
	if ! shift 1
	then
		msg "log: level not specified"
		return 64
	fi
	priority="${1-}"
	if ! shift 1
	then
		msg "log: priority not specified"
		return 64
	fi
	level_ok=false
	priority_ok=false
	high_enough=
	for l in EMERGENCY ALERT CRITICAL ERROR WARNING NOTICE INFO DEBUG
	do
		case "${l}" in
		"${priority}")
			: ${high_enough:="true"}
			priority_ok=true
			;;
		esac
		case "${l}" in
		"${level}")
			: ${high_enough:="false"}
			level_ok=true
			;;
		esac
	done
	case "${level_ok}" in
	false)
		msg "log: unknown level ${level}"
		return 64
		;;
	esac
	case "${priority_ok}" in
	false)
		msg "log: unknown priority ${priority}"
		return 64
		;;
	esac
	case "${high_enough}" in
	true)
		msg "${priority}:" "$@"
		;;
	esac
}

log_define() {
	local func_prefix level_var func_prio func prio default_level opt
	OPTIND=1
	while getopts :f:v:l: opt "$@"
	do
		case "${opt}" in
		'?')
			msg "log_define: unrecognized option -${OPTARG}"
			return 64
			;;
		':')
			msg "log_define: missing argument for -${OPTARG}"
			return 64
			;;
		v)
			level_var="${OPTARG}"
			;;
		l)
			default_level="${OPTARG}"
			;;
		esac
	done
	shift $((${OPTIND} - 1))
	case $# in
	0)
		msg "log_define: function prefix is required"
		return 64
		;;
	esac
	func_prefix="${1}"
	: ${level_var:="${func_prefix}_log_level"}
	: ${default_level:="NOTICE"}
	for func_prio in emerg:EMERGENCY alert:ALERT crit:CRITICAL err:ERROR \
			 warning:WARNING notice:NOTICE info:INFO debug:DEBUG 
	do
		func="${func_prefix}_${func_prio%:*}"
		prio="$(shell_quote "${func_prio#*:}")"
		eval "
			${func}() {
				log \"\${${level_var}-${default_level}}\" \
					${prio} \"\$@\"
			}
		"
	done
	eval "
		${func_prefix}_fatal() {
			local code
			code=\"\${1-1}\"
			shift 1 2> /dev/null || :
			${func_prefix}_crit \"\$@\"
			exit \"\${code}\"
		}
	"
}

log_define -v log_level log

log_level_below() {
	case "${1-}" in
	EMERGENCY) echo ALERT;;
	ALERT) echo CRITICAL;;
	CRITICAL) echo ERROR;;
	ERROR) echo WARNING;;
	WARNING) echo NOTICE;;
	NOTICE) echo INFO;;
	INFO) echo DEBUG;;
	DEBUG) echo DEBUG;;
	*)
		msg "log_level_below: unknown level ${1-}"
		return 1
		;;
	esac
}

log_level_above() {
	case "${1-}" in
	DEBUG) echo INFO;;
	INFO) echo NOTICE;;
	NOTICE) echo WARNING;;
	WARNING) echo ERROR;;
	ERROR) echo CRITICAL;;
	CRITICAL) echo ALERT;;
	ALERT) echo EMERGENCY;;
	EMERGENCY) echo EMERGENCY;;
	*)
		msg "log_level_below: unknown level ${1-}"
		return 1
		;;
	esac
}
