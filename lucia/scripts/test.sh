#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

cd "$PROJECT_DIR"
source "$PROJECT_DIR/.venv/bin/activate" 2>/dev/null || true

MODE="${1:-all}"
FILE_PATH="${2:-}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

check_services() {
    local ports=(8000 8001 8002)
    for port in "${ports[@]}"; do
        if ! (lsof -i :"$port" &>/dev/null || ss -tlnp 2>/dev/null | grep -q ":$port "); then
            log "ERROR: Service on port $port not running. Start services first: bash scripts/start.sh"
            return 1
        fi
    done
    return 0
}

run_suite() {
    local suite="$1"
    local test_path="$2"
    local logfile="$LOG_DIR/test_${suite}_${TIMESTAMP}.log"

    log "Running $suite tests..."
    if pytest "$test_path" -v --tb=short 2>&1 | tee "$logfile"; then
        log "PASS: $suite"
        return 0
    else
        log "FAIL: $suite (see $logfile)"
        return 1
    fi
}

failed=0

case "$MODE" in
    all)
        run_suite "unit" "tests/unit/" || failed=$((failed + 1))
        run_suite "integration" "tests/integration/" || failed=$((failed + 1))
        if check_services; then
            run_suite "e2e" "tests/e2e/" || failed=$((failed + 1))
            run_suite "perf" "tests/performance/" || failed=$((failed + 1))
        else
            log "SKIP: e2e and perf tests (services not running)"
            failed=$((failed + 2))
        fi
        ;;
    unit)
        run_suite "unit" "tests/unit/" || failed=$((failed + 1))
        ;;
    integration)
        run_suite "integration" "tests/integration/" || failed=$((failed + 1))
        ;;
    e2e)
        if check_services; then
            run_suite "e2e" "tests/e2e/" || failed=$((failed + 1))
        else
            failed=$((failed + 1))
        fi
        ;;
    perf)
        if check_services; then
            run_suite "perf" "tests/performance/" || failed=$((failed + 1))
        else
            failed=$((failed + 1))
        fi
        ;;
    quick)
        run_suite "unit" "tests/unit/" || failed=$((failed + 1))
        run_suite "integration" "tests/integration/" || failed=$((failed + 1))
        ;;
    file)
        if [ -z "$FILE_PATH" ]; then
            log "ERROR: No file path specified. Usage: bash scripts/test.sh file <path>"
            exit 1
        fi
        run_suite "file" "$FILE_PATH" || failed=$((failed + 1))
        ;;
    *)
        log "Unknown mode: $MODE"
        log "Usage: bash scripts/test.sh [all|unit|integration|e2e|perf|quick|file <path>]"
        exit 1
        ;;
esac

log ""
if [ "$failed" -eq 0 ]; then
    log "=== ALL TESTS PASSED ==="
else
    log "=== $failed SUITE(S) FAILED ==="
fi

exit "$failed"
