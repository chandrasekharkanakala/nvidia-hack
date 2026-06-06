#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
DATA_DIR="$PROJECT_DIR/data/raw"
mkdir -p "$LOG_DIR" "$DATA_DIR"
LOGFILE="$LOG_DIR/download_$(date +%Y%m%d_%H%M%S).log"

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

BASE_URL="https://data.london.gov.uk/download"

declare -A DATASETS=(
    ["congestion_charge_vehicles.csv"]="congestion-charge-vehicles/resource/csv"
    ["public_transport_journeys.csv"]="public-transport-journeys/resource/csv"
    ["cycle_hires.csv"]="cycle-hires/resource/csv"
    ["road_collisions.csv"]="road-collisions/resource/csv"
    ["walking_cycling_borough.csv"]="walking-cycling-borough/resource/csv"
    ["ptals_accessibility.csv"]="ptals-accessibility/resource/csv"
    ["road_energy_consumption.csv"]="road-energy-consumption/resource/csv"
    ["underground_temperatures.csv"]="underground-temperatures/resource/csv"
    ["buses_by_type.csv"]="buses-by-type/resource/csv"
    ["air_quality_borough.csv"]="air-quality-borough/resource/csv"
    ["reservoir_levels.csv"]="reservoir-levels/resource/csv"
    ["greenhouse_gas_emissions.csv"]="greenhouse-gas-emissions/resource/csv"
    ["fly_tipping_incidents.csv"]="fly-tipping-incidents/resource/csv"
    ["public_realm_trees.csv"]="public-realm-trees/resource/csv"
    ["solar_opportunity.csv"]="solar-opportunity/resource/csv"
    ["green_infrastructure.csv"]="green-infrastructure/resource/csv"
    ["planning_applications.csv"]="planning-applications/resource/csv"
    ["brownfield_register.csv"]="brownfield-register/resource/csv"
    ["affordable_housing.csv"]="affordable-housing/resource/csv"
    ["building_stock_model.csv"]="building-stock-model/resource/csv"
    ["crime_geographic.csv"]="crime-geographic/resource/csv"
    ["fire_brigade_incidents.csv"]="fire-brigade-incidents/resource/csv"
    ["fire_brigade_mobilisation.csv"]="fire-brigade-mobilisation/resource/csv"
)

log "=== Data Download Starting ==="
log "Target directory: $DATA_DIR"
log "Datasets to download: ${#DATASETS[@]}"
log ""

success_count=0
skip_count=0
fail_count=0

for filename in "${!DATASETS[@]}"; do
    filepath="$DATA_DIR/$filename"
    url="$BASE_URL/${DATASETS[$filename]}"

    if [ -f "$filepath" ] && [ -s "$filepath" ]; then
        size=$(stat -f%z "$filepath" 2>/dev/null || stat -c%s "$filepath" 2>/dev/null || echo "unknown")
        log "SKIP: $filename already exists (${size} bytes)"
        skip_count=$((skip_count + 1))
        continue
    fi

    log "Downloading: $filename"
    if curl -fsSL --max-time 120 -o "$filepath" "$url" 2>/dev/null; then
        size=$(stat -f%z "$filepath" 2>/dev/null || stat -c%s "$filepath" 2>/dev/null || echo "unknown")
        if [ -s "$filepath" ]; then
            log "SUCCESS: $filename (${size} bytes)"
            success_count=$((success_count + 1))
        else
            log "FAIL: $filename (empty file)"
            rm -f "$filepath"
            fail_count=$((fail_count + 1))
        fi
    else
        log "FAIL: $filename (download error)"
        rm -f "$filepath"
        fail_count=$((fail_count + 1))
    fi
done

# --- Final Summary ---
log ""
log "=== Download Summary ==="
total_files=$(find "$DATA_DIR" -name "*.csv" -type f | wc -l | tr -d ' ')
total_size=$(du -sh "$DATA_DIR" 2>/dev/null | cut -f1)
log "Files in data/raw: $total_files"
log "Total size: $total_size"
log "Downloaded: $success_count | Skipped: $skip_count | Failed: $fail_count"
log "Log saved to: $LOGFILE"

if [ "$fail_count" -gt 0 ]; then
    exit 1
fi
