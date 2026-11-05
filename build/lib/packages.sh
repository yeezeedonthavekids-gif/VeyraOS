# shellcheck shell=bash
# Package manifest resolution. Sourced by build-iso.sh and by tests.
#
# resolve_manifests <index-file> <out-file> <manifest...>
#   <index-file> contains one available package name per line (from
#   `pacman -Sl` / `pacman -Sg`). Writes resolved names (one per line, sorted,
#   unique) to <out-file>. Returns non-zero if any required entry is missing.

build_package_index() {
    # build_package_index <pacman.conf> <out-file>
    local conf=$1 out=$2
    {
        pacman --config "$conf" -Sl | awk '{print $2}'
        pacman --config "$conf" -Sg | awk '{print $1}'
    } | sort -u > "$out"
    [[ -s $out ]] || die "package index is empty — did 'pacman -Sy' succeed?"
}

resolve_manifests() {
    local index=$1 out=$2; shift 2
    local manifest entry optional alt chosen rc=0
    local -a alts resolved=() missing=() skipped=()
    declare -A avail=()
    while IFS= read -r entry; do avail[$entry]=1; done < "$index"

    for manifest in "$@"; do
        [[ -f $manifest ]] || { warn "manifest not found: $manifest"; rc=1; continue; }
        while IFS= read -r entry; do
            optional=0
            if [[ $entry == \?* ]]; then optional=1; entry=${entry#\?}; fi
            IFS='|' read -r -a alts <<< "$entry"
            chosen=''
            for alt in "${alts[@]}"; do
                alt=${alt//[[:space:]]/}
                [[ -n $alt ]] || continue
                if [[ -n ${avail[$alt]:-} ]]; then chosen=$alt; break; fi
            done
            if [[ -n $chosen ]]; then
                resolved+=("$chosen")
                ((${#alts[@]} > 1)) && [[ $chosen != "${alts[0]//[[:space:]]/}" ]] && \
                    msg2 "$(basename "$manifest"): '$entry' -> using '$chosen'"
            elif ((optional)); then
                skipped+=("$entry ($(basename "$manifest"))")
            else
                missing+=("$entry ($(basename "$manifest"))")
            fi
        done < <(read_manifest "$manifest")
    done

    local s
    for s in "${skipped[@]}"; do warn "optional package unavailable, skipped: $s"; done
    if ((${#missing[@]})); then
        for s in "${missing[@]}"; do printf '%s==> MISSING:%s %s\n' "$_c_err" "$_c_off" "$s" >&2; done
        rc=1
    fi
    printf '%s\n' "${resolved[@]}" | sort -u > "$out"
    return $rc
}
