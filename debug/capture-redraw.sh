#!/bin/bash
# Record everything dvtm writes to the terminal, plus the environment it
# depends on, so a redraw bug seen on a real terminal can be replayed and
# inspected elsewhere.
#
# Usage: debug/capture-redraw.sh [dvtm arguments...]
#
# Output goes to logs/redraw/ (overwritten on each run):
#   env.txt      versions, TERM, locale, terminfo capabilities
#   typescript   raw bytes dvtm sent to the terminal
#   timing       script(1) timing data, for scriptreplay
#   sizes        outer terminal size over time ("EPOCH ROWS COLS"), since
#                script(1) records the size only once, at the start
#   exit.txt     dvtm's exit status

set -u

# Inside dvtm, TERM is dvtm's own and the outer dvtm takes the MOD key, so
# quitting the capture quits the outer session instead.
if [ -n "${DVTM-}" ]; then
	echo "capture-redraw: run this outside dvtm (and abduco)," \
		"from a plain shell in the terminal emulator" >&2
	exit 1
fi

here=$(cd "$(dirname "$0")/.." && pwd)
out="$here/logs/redraw"
mkdir -p "$out"
rm -f "$out"/typescript "$out"/timing "$out"/sizes "$out"/exit.txt

# Not $DVTM: dvtm exports that to its children, set to its version string.
dvtm=${DVTM_BIN:-$(command -v dvtm)}

{
	echo "date: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
	echo "uname: $(uname -a)"
	echo "dvtm binary: $dvtm"
	echo "dvtm version: $("$dvtm" -v 2>&1)"
	echo "repo commit: $(git -C "$here" rev-parse HEAD 2>&1)"
	echo "TERM: ${TERM-unset}"
	echo "COLORTERM: ${COLORTERM-unset}"
	echo "LANG: ${LANG-unset} LC_ALL: ${LC_ALL-unset}"
	echo "LC_CTYPE: ${LC_CTYPE-unset}"
	echo "locale charmap: $(locale charmap 2>&1)"
	echo "terminal size: $(stty size 2>&1)"
	echo "claude version: $(claude --version 2>&1)"
	echo "infocmp version: $(infocmp -V 2>&1)"
	echo "--- linked curses libraries"
	ldd "$dvtm" 2>&1 | grep -Ei 'curses|tinfo'
	echo "--- infocmp -1 $TERM"
	infocmp -1 "$TERM" 2>&1
} > "$out/env.txt"

# Poll the outer terminal's size and log each change, so a resize during the
# run can be told apart from dvtm being handed a wrong size. The first line
# is written as script(1) starts, so it serves as time 0 of the timing file,
# to within a few milliseconds.
outer_tty=$(tty)
(
	last=
	while :; do
		size=$(stty -F "$outer_tty" size 2>&1)
		if [ "$size" != "$last" ]; then
			echo "$(date +%s.%N) $size"
			last=$size
		fi
		sleep 0.05
	done
) > "$out/sizes" &
poller=$!

# --timing lets scriptreplay(1) reproduce the byte stream at its original
# pace; -f flushes after every write so nothing is lost if dvtm is killed.
script -q -f --timing="$out/timing" -c "$(printf '%q ' "$dvtm" "$@")" \
	"$out/typescript"
status=$?
kill "$poller"
echo "dvtm exit status (via script): $status" > "$out/exit.txt"
echo "Capture written to $out"
