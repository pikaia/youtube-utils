#!/usr/bin/env bash
# Start the subtitle web page and share it through a free Cloudflare quick tunnel.
# The password comes from $SUBS_PASSWORD or, if unset, the .subs_password file.
set -euo pipefail
cd "$(dirname "$0")"

if [ -z "${SUBS_PASSWORD:-}" ] && [ -f .subs_password ]; then
    SUBS_PASSWORD="$(tr -d '\r\n' < .subs_password)"
fi
if [ -z "${SUBS_PASSWORD:-}" ]; then
    echo "No password set. Put one in .subs_password or set SUBS_PASSWORD." >&2
    exit 1
fi
export SUBS_PASSWORD
export SUBS_PORT="${SUBS_PORT:-8080}"

CLOUDFLARED="$(command -v cloudflared || echo "/c/Program Files (x86)/cloudflared/cloudflared.exe")"

python web.py &
WEB_PID=$!
trap 'kill $WEB_PID 2>/dev/null' EXIT

echo "Starting tunnel... look for the https://....trycloudflare.com link below."
"$CLOUDFLARED" tunnel --no-autoupdate --url "http://127.0.0.1:$SUBS_PORT"
