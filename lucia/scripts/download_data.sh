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

log "London Datastore + TfL data download script"

# Full URLs (verified against data.london.gov.uk and TfL)
# Format: filename -> full download URL
declare -A DATASETS=(
    # Crime & Safety
    ["mps_crime_borough.csv"]="https://data.london.gov.uk/download/mps-recorded-crime-geographic-borough/731d4bf2-b785-4ee6-8d53-eb1abe31ed27/borough_monthly_crime.csv"
    # Transport - TfL Cycle Hires
    ["cycle_hires.csv"]="https://data.london.gov.uk/download/number-bicycle-hires/ac29363e-e0cb-47cc-a97a-e216d900a6b0/tfl-daily-cycle-hires.csv"
    # Transport - Road Collisions
    ["road_collisions_attendant.csv"]="https://tfl.gov.uk/cdn/static/cms/documents/collision-data-attendant-jan-sep-2025.csv"
    ["road_collisions_casualty.csv"]="https://tfl.gov.uk/cdn/static/cms/documents/collision-data-casualty-jan-sep-2025.csv"
    ["road_collisions_vehicle.csv"]="https://tfl.gov.uk/cdn/static/cms/documents/collision-data-vehicle-jan-sep-2025.csv"
    # Transport - Bus journeys
    ["bus_journeys.csv"]="https://data.london.gov.uk/download/public-transport-journeys-type-transport/2e92cceb-4213-4ba9-abdc-6191e6b1181a/public-transport-journeys-type.csv"
    # Environment - Air Quality
    ["air_quality_monitoring.csv"]="https://data.london.gov.uk/download/london-average-air-quality-levels/57457024-89f7-4e7d-8c22-8efbf2218724/london-average-air-quality-levels.csv"
    # Environment - LAEI emissions
    ["laei_emissions_summary.csv"]="https://data.london.gov.uk/download/london-atmospheric-emissions-inventory--laei--2019/82b0925b-6c2d-4e53-a538-7c11b7922f11/LAEI2019_Summary.csv"
    # Housing - UK House Price Index London
    ["house_price_index.csv"]="https://data.london.gov.uk/download/uk-house-price-index/3ff6aa24-eb44-43a1-864e-87bdf99edfe4/land-registry-house-prices-london.csv"
    # Demographics - Population projections
    ["population_projections.csv"]="https://data.london.gov.uk/download/projections/f1cf4f7d-3d14-4963-8fa5-b3e78e2bda48/housing_led_projections_population.csv"
    # Fire Brigade
    ["fire_incidents.csv"]="https://data.london.gov.uk/download/london-fire-brigade-incident-records/6f1ccc3a-06b9-44e3-a3a6-4d6eeb31c53e/LFB-Incident-data-from-2018-onwards.csv"
    # Fly tipping
    ["fly_tipping.csv"]="https://data.london.gov.uk/download/fly-tipping-incidents/2ef1abb2-bc81-4fc5-a5b1-ce4b5bd5e5e2/fly-tipping-borough.csv"
    # Green infrastructure
    ["green_spaces.csv"]="https://data.london.gov.uk/download/green-and-blue-cover/bfa82d13-2fc1-4ec0-a5b5-2b1a5e2f6e65/Green_Blue_Cover_Borough.csv"
    # Economy
    ["economy_today.csv"]="https://data.london.gov.uk/download/londons-economy-today/bbd3cd44-83c3-4e19-9837-0e35dbb2dc08/LEI-data.csv"
    # State of London (indicators)
    ["state_of_london.csv"]="https://data.london.gov.uk/download/state-of-london/7e7af22c-1c5e-42e4-bef8-57ba3e2e1a4b/state-of-london-indicators.csv"
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
    url="${DATASETS[$filename]}"

    if [ -f "$filepath" ] && [ -s "$filepath" ]; then
        size=$(stat -c%s "$filepath" 2>/dev/null || stat -f%z "$filepath" 2>/dev/null || echo "unknown")
        log "SKIP: $filename already exists (${size} bytes)"
        skip_count=$((skip_count + 1))
        continue
    fi

    log "Downloading: $filename"
    log "  URL: $url"
    http_code=$(curl -sL --max-time 180 -w "%{http_code}" -o "$filepath" "$url" 2>&1)
    if [ "$http_code" = "200" ] && [ -s "$filepath" ]; then
        size=$(stat -c%s "$filepath" 2>/dev/null || stat -f%z "$filepath" 2>/dev/null || echo "unknown")
        log "SUCCESS: $filename (${size} bytes)"
        success_count=$((success_count + 1))
    else
        log_error "FAIL: $filename (HTTP $http_code)"
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
