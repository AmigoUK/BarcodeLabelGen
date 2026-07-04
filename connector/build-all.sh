#!/usr/bin/env bash
# Cross-compile blg-connector for every supported desktop target.
# Pure Go, zero cgo → each target builds unchanged. Output → dist/.
set -euo pipefail
cd "$(dirname "$0")"

out=dist
rm -rf "$out"
mkdir -p "$out"

# GOOS GOARCH  output-name
targets=(
  "windows amd64 blg-connector-windows-amd64.exe"
  "darwin  amd64 blg-connector-macos-intel"
  "darwin  arm64 blg-connector-macos-apple"
  "linux   amd64 blg-connector-linux-amd64"
  "linux   arm64 blg-connector-linux-arm64"
  "linux   arm   blg-connector-linux-arm"
)

for t in "${targets[@]}"; do
  read -r goos goarch name <<<"$t"
  echo "→ $goos/$goarch → $name"
  GOOS="$goos" GOARCH="$goarch" CGO_ENABLED=0 \
    go build -trimpath -ldflags="-s -w" -o "$out/$name" .
done

echo
echo "Built $(ls "$out" | wc -l) binaries in $out/:"
ls -lh "$out"
