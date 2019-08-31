. "${progdir}/msg.sh"

while_preserving() {
	local name names ret type opt OPTIND
	OPTIND=1
	while getopts : opt
	do
		case "${opt}" in
		'?')
			msg "while_preserving: unrecognized option -$OPTARG" >&2
			return 64
			;;
		':')
			msg "while_preserving: missing argument for -$OPTARG" >&2
			return 64
			;;
		esac
	done
	shift $(($OPTIND - 1))
	names=""
	while :
	do
		case $(($# > 0)) in
		0)
			break
			;;
		esac
		name="${1}"
		shift 1
		case "${name}" in
		--)
			break
			;;
		[^A-Za-z_]*|*[^A-Za-z0-9_]*)
			echo "while_preserving: invalid name \"${name}\"" >&2
			return 64
			;;
		name|names|ret|type|*__type|*__value)
			echo "while_preserving: reserved name \"${name}\"" >&2
			return 64
			;;
		esac
		names="${names} ${name}"
	done
	for name in ${names}
	do
		eval "local ${name}__type ${name}__value"
		eval "type=\"\${${name}-x}\${${name}-y}\""
		case "${type}" in
		xy)
			eval "${name}__type=unset"
			;;
		*)
			eval "${name}__value=\"\${${name}}\""
			if printenv | grep -q "^${name}="
			then
				eval "${name}__type=exported"
			else
				eval "${name}__type=set"
			fi
			;;
		esac
	done
	ret=0
	"$@" || ret=$?
	for name in ${names}
	do
		eval "unset ${name}"
		eval "type=\"\${${name}__type}\""
		case "${type}" in
		set|exported)
			eval "${name}=\"\${${name}__value}\""
			;;
		esac
		case "${type}" in
		exported)
			eval "export ${name}"
			;;
		esac
	done
	return "${ret}"
}

unexport() {
	local opt name ret val
	while getopts : opt
	do
		case "${opt}" in
		'?')
			echo "unexport: unrecognized option -$OPTARG" >&2
			return 64
			;;
		':')
			echo "unexport: missing argument for -$OPTARG" >&2
			return 64
			;;
		esac
	done
	shift $(($OPTIND - 1))
	ret=0
	for name
	do
		case "${name}" in
		[^A-Za-z_]*|*[^A-Za-z0-9_]*)
			echo "unexport: invalid name \"${name}\"" >&2
			ret=$((${ret} + 1))
			continue
			;;
		opt|name|val|ret) # local names
			echo "unexport: reserved name \"${name}\"" >&2
			ret=$((${ret} + 1))
			continue
			;;
		esac
		eval "val=\"\${${name}}\""
		eval "unset ${name}"
		eval "${name}=\"\${val}\""
	done
}

is_set() {
	local is_set
	eval "is_set=\"\${$1-x}\${$1-y}\""
	case "${is_set}" in
	xy)
		return 1
		;;
	esac
	return 0
}

bool() {
	if "$@"
	then
		echo true
	else
		echo false
	fi
}

shell_quote() {
	local r sep
	sep=""
	for r
	do
		echo -n "${sep}'"
		sep=" "
		while :
		do
			# avoid ${r} from being interpreted as echo option
			case "${r}" in
			*"'"*)
				echo -n "X${r%%"'"*}'\\''" | sed 's/^X//'
				r="${r#*"'"}"
				;;
			*)
				echo -n "X${r}" | sed 's/^X//'
				break
				;;
			esac
		done
		echo -n "'"
	done
}

bre_escape() {
	case $# in
	0)
		sed 's:[.^[$*\]:\\&:g'
		;;
	*)
		echo "$*" | bre_escape
		;;
	esac
}

ere_escape() {
	case $# in
	0)
		sed 's:[.^[$()|*+?{\]:\\&:g'
		;;
	*)
		echo "$*" | ere_escape
		;;
	esac
}
