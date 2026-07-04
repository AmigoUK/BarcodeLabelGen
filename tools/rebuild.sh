#!/usr/bin/env bash
# Rebuild the stack and immediately reclaim the disk the build churned.
#
# Every `docker compose up -d --build` leaves the previous image dangling and
# grows the build cache; on this host that repeatedly filled the root volume
# (see docs/UAT.md section E3 / the disk-pressure history). Use this wrapper
# instead of a bare compose build so cleanup is never forgotten.
#
#   tools/rebuild.sh            # rebuild every service
#   tools/rebuild.sh web        # rebuild one service
set -euo pipefail

cd "$(dirname "$0")/.."

echo "== disk before =="
df -h / | tail -1

echo "== docker compose up -d --build $* =="
docker compose up -d --build "$@"

echo "== pruning dangling images + unused build cache =="
# image prune -f  → drops the now-untagged previous image(s); never touches
#                   images a running container uses.
# builder prune -f → clears build cache NOT used by the latest build (keeps
#                   the fresh layers so the next rebuild still has some cache).
docker image prune -f
docker builder prune -f

echo "== disk after =="
df -h / | tail -1
