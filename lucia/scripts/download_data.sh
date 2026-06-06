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

# Fresh URLs resolved from data.london.gov.uk API (June 2026)
# Parallel arrays for bash 3+ compatibility
FILENAMES=(
    "congestion_charge.csv"
    "public_transport_journeys.csv"
    "cycle_hires.xlsx"
    "walking_cycling_borough.csv"
    "ptals.csv"
    "road_energy_consumption.csv"
    "underground_temps.csv"
    "buses_by_type.csv"
    "reservoir_levels.csv"
    "leggi_emissions.csv"
    "fly_tipping.csv"
    "green_infrastructure.csv"
    "public_trees.csv"
    "solar_opportunity.csv"
    "brownfield_register.csv"
    "affordable_housing.csv"
    "building_stock.csv"
    "mps_crime.csv"
    "fire_incidents.csv"
    "fire_mobilisation.csv"
)

URLS=(
    "https://data.london.gov.uk/download/2r88d/601a15a2-352c-46be-adae-e049556314a3/tfl-vehicles-c-charge-zone.csv"
    "https://data.london.gov.uk/download/ep8ow/06a805f6-77c6-481a-8b08-ddef56afffdd/tfl-journeys-type.csv"
    "https://data.london.gov.uk/download/2r84d/ac29363e-e0cb-47cc-a97a-e216d900a6b0/tfl-daily-cycle-hires.xlsx"
    "https://data.london.gov.uk/download/vd6j4/c7ae3969-9d32-40ab-8407-589464030231/Walking-Cycling.csv"
    "https://data.london.gov.uk/download/24rz6/4dbb3747-590b-44a4-adbc-906f48eee14f/LSOA2001%20AvPTAI2015.csv"
    "https://data.london.gov.uk/download/v8pmm/242b8608-19aa-4a93-926f-59f848bf30cb/road-transport-energy-consumption.csv"
    "https://data.london.gov.uk/download/epr8d/531e627d-5779-4ae1-bf72-ffa981e13d6e/lu-average-monthly-temperatures%202013-2024.csv"
    "https://data.london.gov.uk/download/e791n/ff855b47-3faa-48de-87c7-18c1165b5945/tfl%20buses%20type.csv"
    "https://data.london.gov.uk/download/24ry5/778eefb5-8cef-4d16-a4c8-77dee7ce7e81/london_reservoir_levels.csv"
    "https://data.london.gov.uk/download/2ko63/2d6ee3f1-e928-48a9-8eab-01748c65ac6f/energy-consumption-borough-leggi.csv"
    "https://data.london.gov.uk/download/e5myg/536278ff-a391-4f20-bc79-9e705c9b3ec0/fly-tipping-borough.csv"
    "https://data.london.gov.uk/download/e70pq/qy9/LGIF%20hex%20results%20(01.04.26).csv"
    "https://data.london.gov.uk/download/2r45m/a2a0ae91-cdf5-4bcd-8b23-2a40f1d854e9/Borough_tree_list_2021July.csv"
    "https://data.london.gov.uk/download/vdxyl/rdc/LSOM_by_TOID.csv"
    "https://data.london.gov.uk/download/2og9g/7ef14d04-8347-4133-b8a7-7c72415f25f1/Brownfield_Register_tbl.csv"
    "https://data.london.gov.uk/download/e64g0/9d975263-dc3a-45c9-9236-dcc15d9e55d2/dclg-affordable-housing-borough.csv"
    "https://data.london.gov.uk/download/2k55d/1eeafdd4-c822-4a96-9578-052f0d90ab39/LBSMv2_Barnet.csv"
    "https://data.london.gov.uk/download/exy3m/276/MPS%20LSOA%20Level%20Crime%20(Historical).csv"
    "https://data.london.gov.uk/download/em8xy/73728cf4-b70e-48e2-9b97-4e4341a2110d/LFB%20Incident%20data%20from%202009%20-%202017.csv"
    "https://data.london.gov.uk/download/24r65/3ff29fb5-3935-41b2-89f1-38571059237e/LFB%20Mobilisation%20data%20from%202021%20-%202024.csv"
)

DATASET_COUNT=${#FILENAMES[@]}

# --- Download with retry + backoff ---
MAX_RETRIES=3
INITIAL_DELAY=3        # seconds between downloads (avoid 429)
BACKOFF_MULTIPLIER=2   # exponential backoff on failure

download_file() {
    local filename="$1"
    local url="$2"
    local filepath="$DATA_DIR/$filename"
    local attempt=1
    local delay=$INITIAL_DELAY

    while [ $attempt -le $MAX_RETRIES ]; do
        log "  Attempt $attempt/$MAX_RETRIES ..."
        http_code=$(curl -sL --max-time 300 \
            -H "User-Agent: LUCIA-DGX-DataLoader/1.0" \
            -w "%{http_code}" -o "$filepath" "$url" 2>/dev/null) || http_code="000"

        if [ "$http_code" = "200" ] && [ -s "$filepath" ]; then
            size=$(stat -c%s "$filepath" 2>/dev/null || stat -f%z "$filepath" 2>/dev/null || echo "unknown")
            log "SUCCESS: $filename (${size} bytes, attempt $attempt)"
            return 0
        elif [ "$http_code" = "429" ]; then
            log "  Rate limited (HTTP 429). Waiting ${delay}s before retry..."
            rm -f "$filepath"
            sleep "$delay"
            delay=$((delay * BACKOFF_MULTIPLIER))
        elif [ "$http_code" = "404" ]; then
            log_error "  NOT FOUND (HTTP 404) - URL may have rotated"
            rm -f "$filepath"
            return 1
        elif [ "$http_code" = "000" ]; then
            log_error "  Connection failed (timeout/DNS). Waiting ${delay}s..."
            rm -f "$filepath"
            sleep "$delay"
            delay=$((delay * BACKOFF_MULTIPLIER))
        else
            log_error "  HTTP $http_code. Waiting ${delay}s before retry..."
            rm -f "$filepath"
            sleep "$delay"
            delay=$((delay * BACKOFF_MULTIPLIER))
        fi
        attempt=$((attempt + 1))
    done

    log_error "FAIL: $filename after $MAX_RETRIES attempts (last HTTP $http_code)"
    rm -f "$filepath"
    return 1
}

log "=== Data Download Starting ==="
log "Target directory: $DATA_DIR"
log "Datasets to download: $DATASET_COUNT"
log "Retry: up to $MAX_RETRIES attempts, ${INITIAL_DELAY}s between downloads"
log ""

success_count=0
skip_count=0
fail_count=0
failed_files=()

for i in $(seq 0 $((DATASET_COUNT - 1))); do
    filename="${FILENAMES[$i]}"
    url="${URLS[$i]}"
    filepath="$DATA_DIR/$filename"

    if [ -f "$filepath" ] && [ -s "$filepath" ]; then
        size=$(stat -c%s "$filepath" 2>/dev/null || stat -f%z "$filepath" 2>/dev/null || echo "unknown")
        log "SKIP: $filename already exists (${size} bytes)"
        skip_count=$((skip_count + 1))
        continue
    fi

    log "Downloading: $filename"
    log "  URL: $url"
    if download_file "$filename" "$url"; then
        success_count=$((success_count + 1))
    else
        fail_count=$((fail_count + 1))
        failed_files+=("$filename")
    fi

    # Polite delay between ALL downloads to avoid rate limiting
    sleep "$INITIAL_DELAY"
done

# --- Final Summary ---
log ""
log "=== Download Summary ==="
total_files=$(find "$DATA_DIR" -name "*.csv" -type f | wc -l | tr -d ' ')
total_size=$(du -sh "$DATA_DIR" 2>/dev/null | cut -f1)
log "Files in data/raw: $total_files"
log "Total size: $total_size"
log "Downloaded: $success_count | Skipped: $skip_count | Failed: $fail_count"

if [ "$fail_count" -gt 0 ]; then
    log ""
    log "=== Failed Downloads (re-run or check URLs) ==="
    for f in "${failed_files[@]}"; do
        log "  - $f"
    done
    log ""
    log "TIP: Some data.london.gov.uk URLs rotate UUIDs when datasets are republished."
    log "     Visit the dataset page and get the fresh CSV download link."
fi

log "Log saved to: $LOGFILE"

if [ "$fail_count" -gt 0 ]; then
    log "Exiting with partial success ($success_count/$((success_count+fail_count)) downloaded)"
    exit 1
fi
