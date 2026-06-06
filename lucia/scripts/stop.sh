#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
PID_FILE="$LOG_DIR/pids.txt"
LOGFILE="$LOG_DIR/stop_$(date +%Y%m%d_%H%M%S).log"

# Redirect ALL output (stdout + stderr) to logfile AND terminal
exec > >(tee -a "$LOGFILE") 2>&1

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "$msg"
}

log_error() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1"
    echo "$msg" >&2
}

trap 'log_error "Command failed at line $LINENO (exit code $?): ${BASH_COMMAND}"' ERR

log "=== Stopping Lucia Services ==="

if [ ! -f "$PID_FILE" ]; then
    log "No PID file found at $PID_FILE"
    log "Nothing to stop."
    exit 0
fi

stopped=0
already_dead=0

while read -r line; do
    [ -z "$line" ] && continue
    pid=$(echo "$line" | awk '{print $1}')
    name=$(echo "$line" | awk '{print $2}')
    port=$(echo "$line" | awk '{print $3}')

    if kill -0 "$pid" 2>/dev/null; then
        kill "$pid"
        log "STOPPED: $name (PID $pid, port $port)"
        stopped=$((stopped + 1))
    else
        log "SKIP: $name (PID $pid) already terminated"
        already_dead=$((already_dead + 1))
    fi
done < "$PID_FILE"

# Clean up PID file
rm -f "$PID_FILE"

log ""
log "Stopped: $stopped | Already dead: $already_dead"
log "PID file removed."
