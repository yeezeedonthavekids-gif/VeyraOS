#!/usr/bin/env bash
# Measure VeyraOS idle resource use on real hardware, for before/after
# comparisons of configuration changes (docs/PERFORMANCE.md).
#
#   tools/bench-idle.sh [LABEL]      -> ./bench-<LABEL>-<date>.json
#
# Run it from a terminal ~2 minutes after logging in, with no apps open
# except the terminal. It samples for 60 seconds.
set -euo pipefail
LABEL=${1:-run}
OUT=bench-$LABEL-$(date +%Y%m%d-%H%M%S).json
SAMPLE=${SAMPLE:-60}

# Boot time: kernel start -> OpenRC "default" runlevel reached (from rc.log)
boot_s=null
if [[ -r /var/log/rc.log ]]; then
    # rc.log is written until the default runlevel is reached, so its
    # modification time minus the kernel boot time approximates boot duration.
    btime=$(awk '/^btime/{print $2}' /proc/stat)
    last=$(stat -c %Y /var/log/rc.log)
    boot_s=$(( last - btime ))
fi

mem_used_mib=$(free -m | awk '/^Mem:/{print $3}')
mem_avail_mib=$(free -m | awk '/^Mem:/{print $7}')
swap_used_mib=$(free -m | awk '/^Swap:/{print $3}')

# Idle CPU %: average over SAMPLE seconds from /proc/stat
read -r _ u1 n1 s1 i1 w1 x1 y1 z1 _ < /proc/stat
sleep "$SAMPLE"
read -r _ u2 n2 s2 i2 w2 x2 y2 z2 _ < /proc/stat
busy=$(( (u2+n2+s2+x2+y2+z2) - (u1+n1+s1+x1+y1+z1) ))
total=$(( busy + (i2+w2) - (i1+w1) ))
cpu_pct=$(awk -v b=$busy -v t=$total 'BEGIN{printf "%.2f", t ? 100*b/t : 0}')

procs=$(ps -e --no-headers | wc -l)
services=$(rc-status --servicelist 2>/dev/null | grep -c started || true)
top_mem=$(ps -eo rss,comm --sort=-rss --no-headers | head -8 | awk '{printf "%s{\"name\":\"%s\",\"rss_mib\":%d}", (NR>1?",":""), $2, $1/1024}')

cat > "$OUT" <<EOF
{
  "label": "$LABEL",
  "date": "$(date -Is)",
  "kernel": "$(uname -r)",
  "boot_to_default_runlevel_s": $boot_s,
  "mem_used_mib": $mem_used_mib,
  "mem_available_mib": $mem_avail_mib,
  "swap_used_mib": $swap_used_mib,
  "idle_cpu_percent_${SAMPLE}s": $cpu_pct,
  "processes": $procs,
  "openrc_services_started": $services,
  "top_memory": [$top_mem]
}
EOF
cat "$OUT"
