#!/usr/bin/env bash
# Manage the subtitle web page and its Cloudflare tunnel.
#
#   ./subs.sh password         set the shared password
#   ./subs.sh start            start in the background and print the link
#   ./subs.sh stop             stop everything
#   ./subs.sh restart          stop, then start (gives a new link)
#   ./subs.sh status           show whether it's running, and the link
#   ./subs.sh link             print the current link
#   ./subs.sh logs             show recent log output
#   ./subs.sh autostart on|off start automatically when you log in to Windows
set -uo pipefail
cd "$(dirname "$0")"

SHORTCUT_NAME="Subtitle Downloader.lnk"

is_running() {
    [ -f logs/start.pid ] && kill -0 "$(cat logs/start.pid)" 2>/dev/null
}

startup_dir() {
    cygpath -u "$(powershell.exe -NoProfile -Command "[Environment]::GetFolderPath('Startup')" | tr -d '\r')"
}

cmd_password() {
    read -rsp "New password: " pw1; echo
    read -rsp "Repeat it:    " pw2; echo
    if [ -z "$pw1" ] || [ "$pw1" != "$pw2" ]; then
        echo "Passwords were empty or didn't match; nothing changed." >&2
        return 1
    fi
    printf '%s\n' "$pw1" > .subs_password
    echo "Password saved. Run './subs.sh restart' if it's already running."
}

cmd_start() {
    if is_running; then
        echo "Already running."
        cmd_link
        return
    fi
    if [ ! -s .subs_password ] && [ -z "${SUBS_PASSWORD:-}" ]; then
        echo "No password set yet. Run './subs.sh password' first." >&2
        return 1
    fi
    rm -f current_link.txt
    # Launch through wscript so it keeps running after this terminal closes.
    wscript.exe autostart.vbs
    echo -n "Starting"
    for _ in $(seq 1 45); do
        [ -s current_link.txt ] && break
        echo -n "."
        sleep 1
    done
    echo
    if [ ! -s current_link.txt ]; then
        echo "No link yet. Check './subs.sh logs'." >&2
        return 1
    fi
    # New quick-tunnel links can take a minute before they're reachable.
    echo -n "Waiting for the link to go live"
    for _ in $(seq 1 30); do
        if [ "$(curl -s -o /dev/null -w '%{http_code}' "$(cat current_link.txt)/")" = "401" ]; then
            echo
            echo "Ready to share:"
            cmd_link
            return
        fi
        echo -n "."
        sleep 4
    done
    echo
    echo "The link isn't reachable yet; it may need another minute:" >&2
    cmd_link
}

cmd_stop() {
    if [ -f logs/start.pid ]; then
        kill "$(cat logs/start.pid)" 2>/dev/null
        rm -f logs/start.pid
    fi
    # Processes launched from Windows can outlive their parent; clean them up too.
    taskkill //F //IM cloudflared.exe > /dev/null 2>&1
    for pid in $(powershell.exe -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"name='python.exe'\" | Where-Object CommandLine -like '*web.py*' | ForEach-Object ProcessId" 2>/dev/null | tr -d '\r'); do
        taskkill //F //PID "$pid" > /dev/null 2>&1
    done
    rm -f current_link.txt
    echo "Stopped."
}

cmd_status() {
    if is_running; then
        echo "Running."
        cmd_link
    else
        echo "Not running."
    fi
    if [ -f "$(startup_dir)/$SHORTCUT_NAME" ]; then
        echo "Autostart: on"
    else
        echo "Autostart: off"
    fi
}

cmd_link() {
    if [ -s current_link.txt ]; then
        cat current_link.txt
    else
        echo "No link (not running, or still starting)." >&2
        return 1
    fi
}

cmd_logs() {
    for f in logs/links.log logs/web.log logs/tunnel.log; do
        [ -f "$f" ] || continue
        echo "== $f =="
        tail -n 15 "$f"
    done
}

cmd_autostart() {
    local shortcut
    shortcut="$(startup_dir)/$SHORTCUT_NAME"
    case "${1:-}" in
        on)
            powershell.exe -NoProfile -Command "
                \$s = (New-Object -ComObject WScript.Shell).CreateShortcut('$(cygpath -w "$shortcut")')
                \$s.TargetPath = \"\$env:WINDIR\System32\wscript.exe\"
                \$s.Arguments = '\"$(cygpath -w "$PWD/autostart.vbs")\"'
                \$s.WorkingDirectory = '$(cygpath -w "$PWD")'
                \$s.Save()"
            echo "Autostart on: it will start when you log in to Windows."
            ;;
        off)
            rm -f "$shortcut"
            echo "Autostart off."
            ;;
        *)
            echo "Usage: ./subs.sh autostart on|off" >&2
            return 1
            ;;
    esac
}

case "${1:-}" in
    password)  cmd_password ;;
    start)     cmd_start ;;
    stop)      cmd_stop ;;
    restart)   cmd_stop; cmd_start ;;
    status)    cmd_status ;;
    link)      cmd_link ;;
    logs)      cmd_logs ;;
    autostart) cmd_autostart "${2:-}" ;;
    *)         sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//' ;;
esac
