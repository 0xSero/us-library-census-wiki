#!/usr/bin/env bash
# launch.sh — Serve the US Library Census Wiki and open it in the browser.
#
# Usage:
#   bash wiki/launch.sh          # serve on port 8124 and open browser
#   bash wiki/launch.sh --no-open # serve without opening a browser
#
# To stop the server later:
#   bash wiki/launch.sh --stop
#   (or just kill the python3 -m http.server process on port 8124)

set -euo pipefail

WIKI_DIR="$(cd "$(dirname "$0")" && pwd)"
PORT="${WIKI_PORT:-8124}"
URL="http://localhost:${PORT}"

# --stop: kill anything listening on the port
if [[ "${1:-}" == "--stop" ]]; then
  echo "Stopping any server on port ${PORT}..."
  lsof -ti "tcp:${PORT}" 2>/dev/null | xargs kill 2>/dev/null || true
  echo "Stopped."
  exit 0
fi

# Kill anything already on the port
lsof -ti "tcp:${PORT}" 2>/dev/null | xargs kill 2>/dev/null || true

echo "=== US Library Census Wiki ==="
echo "  Directory: ${WIKI_DIR}"
echo "  URL:       ${URL}"
echo "  Stop with: bash wiki/launch.sh --stop"
echo ""

# Open the browser (unless --no-open)
if [[ "${1:-}" != "--no-open" ]]; then
  # Give the server a moment to start, then open
  ( sleep 1 && open "${URL}" 2>/dev/null || xdg-open "${URL}" 2>/dev/null || true ) &
fi

cd "${WIKI_DIR}"
exec python3 -m http.server "${PORT}" --bind 127.0.0.1
