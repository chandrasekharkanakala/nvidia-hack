#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"
LOGFILE="$LOG_DIR/start_$(date +%Y%m%d_%H%M%S).log"
PID_FILE="$LOG_DIR/pids.txt"

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

# Trap errors and log them with context
trap 'log_error "Command failed at line $LINENO (exit code $?): ${BASH_COMMAND}"' ERR

port_in_use() {
    lsof -i :"$1" &>/dev/null || ss -tlnp 2>/dev/null | grep -q ":$1 "
}

wait_for_port() {
    local port="$1"
    local name="$2"
    local timeout="${3:-30}"
    local elapsed=0

    while ! port_in_use "$port"; do
        sleep 1
        elapsed=$((elapsed + 1))
        if [ "$elapsed" -ge "$timeout" ]; then
            log "TIMEOUT: $name on port $port not reachable after ${timeout}s"
            return 1
        fi
    done
    log "READY: $name on port $port (${elapsed}s)"
    return 0
}

log "=== Starting Lucia Services ==="

# Clear previous PID file
> "$PID_FILE"

source "$PROJECT_DIR/.venv/bin/activate" 2>/dev/null || true

declare -A SERVICES=(
    ["vLLM"]=8001
    ["NV-Embed"]=8002
    ["NeVA"]=8003
    ["NemoClaw"]=8080
    ["FastAPI"]=8000
    ["React-UI"]=3000
)

# --- vLLM (port 8001) — Nemotron Nano (reasoning + planning) ---
if port_in_use 8001; then
    log "SKIP: vLLM already running on port 8001"
else
    log "Starting Nemotron Nano on port 8001..."
    python3 -m vllm.entrypoints.openai.api_server \
        --model nvidia/Nemotron-Mini-4B-Instruct \
        --port 8001 \
        --tensor-parallel-size 1 \
        --gpu-memory-utilization 0.3 \
        > "$LOG_DIR/vllm.log" 2>&1 &
    echo "$! vLLM 8001" >> "$PID_FILE"
    log "Started Nemotron Nano (PID: $!)"
fi

# --- NV-Embed-v2 (port 8002) — NVIDIA embeddings ---
if port_in_use 8002; then
    log "SKIP: NV-Embed already running on port 8002"
else
    log "Starting NV-Embed-v2 on port 8002..."
    python3 -m vllm.entrypoints.openai.api_server \
        --model nvidia/NV-Embed-v2 \
        --port 8002 \
        --gpu-memory-utilization 0.15 \
        > "$LOG_DIR/nv_embed.log" 2>&1 &
    echo "$! NV-Embed 8002" >> "$PID_FILE"
    log "Started NV-Embed-v2 (PID: $!)"
fi

# --- NeVA Vision (port 8003) — DISABLED (added to backlog) ---
# if port_in_use 8003; then
#     log "SKIP: NeVA already running on port 8003"
# else
#     log "Starting NeVA on port 8003..."
#     python3 -m vllm.entrypoints.openai.api_server \
#         --model nvidia/neva-22b \
#         --port 8003 \
#         --gpu-memory-utilization 0.10 \
#         > "$LOG_DIR/neva.log" 2>&1 &
#     echo "$! NeVA 8003" >> "$PID_FILE"
#     log "Started NeVA (PID: $!)"
# fi

# --- NemoClaw (port 8080) ---
if port_in_use 8080; then
    log "SKIP: NemoClaw already running on port 8080"
else
    log "Starting NemoClaw on port 8080..."
    if command -v nemoclaw &>/dev/null; then
        nemoclaw serve --port 8080 > "$LOG_DIR/nemoclaw.log" 2>&1 &
        echo "$! NemoClaw 8080" >> "$PID_FILE"
        log "Started NemoClaw (PID: $!)"
    else
        log "WARN: nemoclaw not found, skipping"
    fi
fi

# --- FastAPI Backend (port 8000) ---
if port_in_use 8000; then
    log "SKIP: FastAPI already running on port 8000"
else
    log "Starting FastAPI on port 8000..."
    cd "$PROJECT_DIR"
    PYTHONPATH="$PROJECT_DIR" uvicorn src.api.main:app --host 0.0.0.0 --port 8000 \
        > "$LOG_DIR/fastapi.log" 2>&1 &
    echo "$! FastAPI 8000" >> "$PID_FILE"
    log "Started FastAPI (PID: $!)"
fi

# --- React UI (port 3000) ---
if port_in_use 3000; then
    log "SKIP: React UI already running on port 3000"
else
    log "Starting React UI on port 3000..."
    if [ -d "$PROJECT_DIR/ui" ]; then
        cd "$PROJECT_DIR/ui"
        npm run dev -- --port 3000 > "$LOG_DIR/ui.log" 2>&1 &
        echo "$! React-UI 3000" >> "$PID_FILE"
        log "Started React UI (PID: $!)"
    else
        log "WARN: ui/ directory not found, skipping"
    fi
fi

cd "$PROJECT_DIR"

# --- Wait for services ---
log ""
log "Waiting for services to become ready..."
log "(vLLM models can take 3-10 minutes on first load while downloading weights)"
wait_for_port 8001 "vLLM" 600 || true
wait_for_port 8002 "NV-Embed" 600 || true
# wait_for_port 8003 "NeVA" 600 || true  # Vision disabled (backlog)
wait_for_port 8080 "NemoClaw" 30 || true
wait_for_port 8000 "FastAPI" 30 || true
wait_for_port 3000 "React UI" 15 || true

# --- Status table ---
log ""
log "=== Service Status ==="
printf "%-12s %-6s %-8s\n" "SERVICE" "PORT" "STATUS" | tee -a "$LOGFILE"
printf "%-12s %-6s %-8s\n" "-------" "----" "------" | tee -a "$LOGFILE"
for service in vLLM NV-Embed NeVA NemoClaw FastAPI React-UI; do
    port="${SERVICES[$service]}"
    if port_in_use "$port"; then
        status="✓ UP"
    else
        status="✗ DOWN"
    fi
    printf "%-12s %-6s %-8s\n" "$service" "$port" "$status" | tee -a "$LOGFILE"
done

# --- GPU Memory ---
log ""
if command -v nvidia-smi &>/dev/null; then
    log "GPU Memory:"
    nvidia-smi --query-gpu=index,name,memory.used,memory.total --format=csv,noheader | tee -a "$LOGFILE"
fi

log ""
log "PIDs saved to: $PID_FILE"
log "Log saved to: $LOGFILE"
