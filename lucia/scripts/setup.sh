#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"
LOGFILE="$LOG_DIR/setup_$(date +%Y%m%d_%H%M%S).log"

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

check_cmd() {
    command -v "$1" &>/dev/null
}

log "=== DGX Spark Setup Starting ==="
log "Project directory: $PROJECT_DIR"

# --- Python 3.12+ ---
if check_cmd python3 && python3 -c "import sys; exit(0 if sys.version_info >= (3,12) else 1)" 2>/dev/null; then
    log "SKIP: Python 3.12+ already installed ($(python3 --version))"
else
    log "Installing Python 3.12..."
    sudo apt-get update -qq && sudo apt-get install -y python3.12 python3.12-venv python3.12-dev python3-pip
    log "DONE: Python installed ($(python3 --version))"
fi

# --- Python dev headers (needed for native extensions like annoy) ---
if [ -f "/usr/include/python3.12/Python.h" ] || [ -f "/usr/include/python3/Python.h" ]; then
    log "SKIP: Python dev headers already present"
else
    log "Installing Python dev headers (required for nemoguardrails/annoy)..."
    sudo apt-get install -y python3.12-dev python3-dev build-essential
    log "DONE: Python dev headers installed"
fi

# --- Node.js 22+ ---
if check_cmd node && node -e "process.exit(parseInt(process.version.slice(1))>=22?0:1)" 2>/dev/null; then
    log "SKIP: Node.js 22+ already installed ($(node --version))"
else
    log "Installing Node.js 22..."
    curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
    sudo apt-get install -y nodejs
    log "DONE: Node.js installed ($(node --version))"
fi

# --- Docker/Podman ---
if check_cmd docker || check_cmd podman; then
    log "SKIP: Container runtime already installed ($(docker --version 2>/dev/null || podman --version 2>/dev/null))"
else
    log "Installing Docker..."
    sudo apt-get install -y docker.io
    sudo systemctl enable --now docker
    sudo usermod -aG docker "$USER"
    log "DONE: Docker installed ($(docker --version))"
fi

# --- Python virtual environment ---
VENV_DIR="$PROJECT_DIR/.venv"
if [ -d "$VENV_DIR" ] && [ -f "$VENV_DIR/bin/activate" ]; then
    log "SKIP: Virtual environment already exists at $VENV_DIR"
else
    log "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    log "DONE: Virtual environment created"
fi

source "$VENV_DIR/bin/activate"

# --- Pip packages ---
install_pip_pkg() {
    local pkg="$1"
    local import_name="${2:-$1}"
    if python3 -c "import $import_name" 2>/dev/null; then
        log "SKIP: $pkg already installed"
    else
        log "Installing $pkg..."
        pip install --quiet "$pkg"
        log "DONE: $pkg installed"
    fi
}

log "Installing pip packages..."
pip install --quiet --upgrade pip setuptools wheel

PACKAGES=(
    "fastapi:fastapi"
    "uvicorn[standard]:uvicorn"
    "websockets:websockets"
    "pydantic-settings:pydantic_settings"
    "nemoguardrails:nemoguardrails"
    "duckdb:duckdb"
    "pyarrow:pyarrow"
    "pandas:pandas"
    "openpyxl:openpyxl"
    "faiss-gpu:faiss"
    "numpy:numpy"
    "openai:openai"
    "aiohttp:aiohttp"
    "beautifulsoup4:bs4"
    "networkx:networkx"
    "statsmodels:statsmodels"
    "structlog:structlog"
    "rich:rich"
    "python-dotenv:dotenv"
    "pytest:pytest"
    "pytest-asyncio:pytest_asyncio"
    "httpx:httpx"
    "pytest-mock:pytest_mock"
)

for entry in "${PACKAGES[@]}"; do
    pkg="${entry%%:*}"
    import_name="${entry##*:}"
    install_pip_pkg "$pkg" "$import_name"
done

# --- vLLM ---
if python3 -c "import vllm" 2>/dev/null; then
    log "SKIP: vLLM already installed"
else
    log "Installing vLLM..."
    pip install --quiet vllm
    log "DONE: vLLM installed"
fi

# --- NeMo Guardrails (verify) ---
if check_cmd nemoguardrails; then
    log "SKIP: NeMo Guardrails CLI already available"
else
    log "NeMo Guardrails CLI will be available after install completes"
fi

# --- NemoClaw CLI ---
if check_cmd nemoclaw; then
    log "SKIP: NemoClaw CLI already installed"
else
    log "Installing NemoClaw CLI..."
    pip install --quiet nemoclaw 2>/dev/null || log "WARN: NemoClaw not available in PyPI, may need manual install"
fi

# --- NVIDIA Skills ---
log "Installing NVIDIA skills..."
cd "$PROJECT_DIR"
if [ -f "package.json" ]; then
    npx skills add 2>/dev/null || log "WARN: NVIDIA skills installation skipped (npx skills not available)"
else
    log "SKIP: No package.json found, skipping NVIDIA skills"
fi

# --- Frontend ---
UI_DIR="$PROJECT_DIR/ui"
if [ -d "$UI_DIR" ] && [ -f "$UI_DIR/package.json" ]; then
    if [ -d "$UI_DIR/node_modules" ]; then
        log "SKIP: Frontend dependencies already installed"
    else
        log "Installing frontend dependencies..."
        cd "$UI_DIR" && npm install
        log "DONE: Frontend dependencies installed"
    fi
else
    log "SKIP: No ui/ directory with package.json found"
fi

cd "$PROJECT_DIR"

# --- Data directories ---
for dir in data/raw data/processed data/embeddings data/output; do
    if [ -d "$dir" ]; then
        log "SKIP: $dir already exists"
    else
        mkdir -p "$dir"
        log "DONE: Created $dir"
    fi
done

# --- .env file ---
if [ -f "$PROJECT_DIR/.env" ]; then
    log "SKIP: .env already exists"
elif [ -f "$PROJECT_DIR/.env.example" ]; then
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    log "DONE: Copied .env.example to .env"
else
    log "SKIP: No .env.example found to copy"
fi

# --- Final Verification ---
log ""
log "=== Final Verification ==="
log "Python: $(python3 --version 2>&1)"
log "Node.js: $(node --version 2>&1 || echo 'not installed')"
log "Pip packages: $(pip list --format=columns 2>/dev/null | tail -n +3 | wc -l | tr -d ' ') installed"
if check_cmd nvidia-smi; then
    log "GPU: $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || echo 'query failed')"
else
    log "GPU: nvidia-smi not available"
fi
log ""
log "=== Setup Complete ==="
log "Log saved to: $LOGFILE"
