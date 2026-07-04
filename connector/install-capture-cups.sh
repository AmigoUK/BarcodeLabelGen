#!/usr/bin/env bash
# Create a CUPS raw print queue that forwards captured ZPL to a local
# blg-connector. Works on Linux and macOS (both ship CUPS + lpadmin).
#
# The queue is "raw" (-m raw): CUPS passes each job's bytes through with no
# filter to socket://127.0.0.1:9101, where the connector's capture listener
# picks it up. This only helps applications that ALREADY emit ZPL — generic
# apps (Word, browsers) print PostScript and the agent will reject them.
#
#   QUEUE=name TARGET=host:port ./install-capture-cups.sh
set -euo pipefail

QUEUE="${QUEUE:-BarcodeLabelGen-Capture}"
TARGET="${TARGET:-127.0.0.1:9101}"

if ! command -v lpadmin >/dev/null 2>&1; then
  echo "error: lpadmin not found — install CUPS first" >&2
  echo "  Debian/Ubuntu: sudo apt install cups cups-client" >&2
  echo "  Fedora:        sudo dnf install cups" >&2
  echo "  macOS:         CUPS is built in (check that printing is enabled)" >&2
  exit 1
fi

echo "→ creating raw queue '$QUEUE' → socket://$TARGET"
if ! lpadmin -p "$QUEUE" -E -v "socket://$TARGET" -m raw; then
  echo >&2
  echo "error: lpadmin failed — this usually means missing permissions." >&2
  echo "  Re-run with sudo, or add yourself to the CUPS admin group:" >&2
  echo "    Linux: sudo usermod -aG lpadmin \"\$USER\"  (log out/in after)" >&2
  echo "    macOS: sudo dseditgroup -o edit -a \"\$USER\" -t user _lpadmin" >&2
  exit 1
fi

echo
echo "Done. Queue '$QUEUE' forwards to socket://$TARGET."
echo "Make sure blg-connector runs with a capture.listen matching $TARGET."
echo
echo "Print a ZPL file to it:   lp -d \"$QUEUE\" label.zpl"
echo "Remove the queue:         lpadmin -x \"$QUEUE\""
