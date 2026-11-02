#!/usr/bin/env bash
# Launch a separate, task-owned Chrome profile after the scientist chooses this route.
set -euo pipefail
PORT="${1:-9222}"
[[ "$PORT" =~ ^[0-9]+$ ]] && (( PORT >= 1024 && PORT <= 65535 )) || { echo "Choose a port from 1024 to 65535" >&2; exit 1; }
if curl -fsS --max-time 2 "http://127.0.0.1:$PORT/json/version" >/dev/null 2>&1; then
  echo "Port already belongs to a browser. Choose a different port." >&2; exit 1
fi
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
[[ -x "$CHROME" ]] || { echo "Google Chrome is not installed" >&2; exit 1; }
PROFILE="$(mktemp -d "${TMPDIR:-/tmp}/science-literature.XXXXXX")"
printf '%s\n' "$PORT" > "$PROFILE/science-literature-port"
"$CHROME" --remote-debugging-port="$PORT" --remote-debugging-address=127.0.0.1 --user-data-dir="$PROFILE" --no-first-run --no-default-browser-check about:blank >"$PROFILE/browser.log" 2>&1 &
PID=$!
printf '%s\n' "$PID" > "$PROFILE/science-literature-pid"
for attempt in 1 2 3 4 5; do
  if curl -fsS --max-time 2 "http://127.0.0.1:$PORT/json/version" >/dev/null 2>&1; then
    printf 'PROFILE=%s\nPID=%s\nPORT=%s\n' "$PROFILE" "$PID" "$PORT"
    exit 0
  fi
  sleep 1
done
printf 'Chrome did not become ready. Inspect %s/browser.log; task PID is %s.\n' "$PROFILE" "$PID" >&2
exit 1
