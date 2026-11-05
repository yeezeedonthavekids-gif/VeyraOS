#!/usr/bin/env bash
# Build the VeyraOS ISO inside a disposable Artix container, from any Linux
# host with Docker (or Podman with `docker` alias). Needs network access to
# the Artix and Arch package mirrors.
#
#   build/build-in-docker.sh [build-iso.sh arguments...]
#
# The container is privileged because the build mounts proc/sys/dev into the
# target root and uses loop devices; nothing on the host is modified except
# ./out (ISO + logs) and the named volume holding the package cache.
set -euo pipefail
TOP=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
IMAGE=${VEYRA_BUILD_IMAGE:-artixlinux/artixlinux:base-devel}
ENGINE=${CONTAINER_ENGINE:-docker}

command -v "$ENGINE" >/dev/null || { echo "error: $ENGINE not found" >&2; exit 1; }
mkdir -p "$TOP/out"

exec "$ENGINE" run --rm --privileged \
    -v "$TOP:/veyra:ro" \
    -v "$TOP/out:/veyra-out" \
    -v veyra-pkgcache:/var/tmp/veyra-build/pkgcache \
    -e SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-$(git -C "$TOP" log -1 --format=%ct 2>/dev/null || date +%s)}" \
    "$IMAGE" \
    /veyra/build/build-iso.sh --out /veyra-out "$@"
