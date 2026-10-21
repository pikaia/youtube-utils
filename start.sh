#!/usr/bin/env bash
# Start the subtitle web page and share it through a free Cloudflare quick tunnel.
# The password comes from $SUBS_PASSWORD or, if unset, the .subs_password file.
# The current public link is written to current_link.txt; logs go to logs/.
set -uo pipefail
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
mkdir -p logs
echo $$ > logs/start.pid

WEB_PID=""
TUNNEL_PID=""
cleanup() {
    kill $WEB_PID $TUNNEL_PID 2>/dev/null
    rm -f logs/start.pid
    exit 0
}
trap cleanup INT TERM EXIT

python web.py >> logs/web.log 2>&1 &
WEB_PID=$!

while true; do
    "$CLOUDFLARED" tunnel --no-autoupdate --url "http://127.0.0.1:$SUBS_PORT" > logs/tunnel.log 2>&1 &
    TUNNEL_PID=$!

    link=""
    for _ in $(seq 1 60); do
        link="$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' logs/tunnel.log | head -1)"
        [ -n "$link" ] && break
        kill -0 "$TUNNEL_PID" 2>/dev/null || break
        sleep 1
    done

    if [ -n "$link" ]; then
        echo "$link" > current_link.txt
        echo "$(date '+%Y-%m-%d %H:%M') $link" >> logs/links.log
        echo "Public link: $link"
    else
        echo "Tunnel didn't start; see logs/tunnel.log" >&2
    fi

    wait "$TUNNEL_PID"
    echo "Tunnel stopped; restarting in 10 seconds..." >&2
    sleep 10
done
