#!/usr/bin/env bash
# Stop the web page and tunnel started by start.sh (including the auto-start one).
cd "$(dirname "$0")"
if [ -f logs/start.pid ]; then
    kill "$(cat logs/start.pid)" 2>/dev/null
    rm -f logs/start.pid
fi
# Background launches from Windows can leave the tunnel without a parent; clean it up too.
taskkill //F //IM cloudflared.exe > /dev/null 2>&1
for pid in $(powershell.exe -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"name='python.exe'\" | Where-Object CommandLine -like '*web.py*' | ForEach-Object ProcessId" 2>/dev/null | tr -d '\r'); do
    taskkill //F //PID "$pid" > /dev/null 2>&1
done
rm -f current_link.txt
echo "Stopped."
