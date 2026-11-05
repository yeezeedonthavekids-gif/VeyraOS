#!/usr/bin/env bash
# Runs ShellCheck on every shell script in the repository (bash/sh; OpenRC scripts and
# the busybox-ash initcpio hook are checked as POSIX sh).
set -uo pipefail
TOP=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$TOP" || exit 1
command -v shellcheck >/dev/null || { echo "  skip shellcheck (not installed)"; exit 0; }
mapfile -t all < <(grep -rlE '^#!\s*/(usr/)?bin/(env )?(ba)?sh|^#!/usr/bin/(ash|openrc-run)|shell=(bash|dash)' \
                       build src tests tools 2>/dev/null | grep -v '\.py$' | sort -u)
posix=() other=()
for f in "${all[@]}"; do
    case $f in */init.d/*|*/initcpio/hooks/*) posix+=("$f") ;; *) other+=("$f") ;; esac
done
rc=0
shellcheck -S warning "${other[@]}" || rc=1
shellcheck -S warning -s sh -e SC2034,SC3043 "${posix[@]}" || rc=1
((rc == 0)) && echo "  ok   shellcheck (${#all[@]} scripts)"
exit $rc
