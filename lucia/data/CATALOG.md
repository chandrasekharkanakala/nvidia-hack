# LUCIA Data Catalog — All Sources

## Ingestion Strategy

Data is split into TWO paths based on what LUCIA needs from it:

### Path A: Structured → DuckDB (for SQL tool — metrics, counts, time-series)
Data where the VALUE is in the numbers/relationships. Agent generates SQL to query.

### Path B: Text/Context → Embed → FAISS (for RAG tool — reasoning, thinking, explanations)
Data where the VALUE is in understanding context, patterns, narrative. Agent retrieves
chunks to reason over, synthesize insights, and make non-obvious connections.

### Path C: Real-time → Live API (for web_scraper tool — current state)
Data that changes minute-to-minute. Agent fetches on-demand.

---

## Dataset Registry

### TRANSPORT — Traffic & Flow

| # | Dataset | Source URL | Format | Path | Why |
|---|---------|-----------|--------|------|-----|
| 1 | Traffic Flows by Borough | https://data.london.gov.uk/dataset/traffic-flows-borough-v8pow/ | CSV | A (DuckDB) | Traffic volume by borough — congestion analysis |
| 2 | Traffic Datasets (tagged) | https://data.london.gov.uk/dataset/?tag=traffic | CSV/XLS | A (DuckDB) | Collection of traffic-related datasets (browse & select relevant files) |
| 3 | Transport Spreadsheets | https://data.london.gov.uk/dataset/?topics=transport&format=spreadsheet | XLS/CSV | A (DuckDB) | Broader transport data in spreadsheet format |
| 4 | Baseline & Post-scheme Traffic Counts | https://data.london.gov.uk/dataset/baseline-and-post-scheme-implementation-traffic-counts-for-londo-2lwg8/ | CSV | A (DuckDB) | Before/after traffic counts for scheme impact analysis |
| 5 | Congestion Charge Zone Vehicles | https://data.london.gov.uk/dataset/camera-captures-and-confirmed-vehicles-seen-in-the-congestion-ch-2r88d/ | CSV | A (DuckDB) | Time-series of vehicle counts — queries like "how many vehicles in Jan vs Jul?" |
| 6 | Licensed Vehicles by Type & Borough | https://data.london.gov.uk/dataset/licensed-vehicles-type-borough-2l873/ | CSV | A (DuckDB) | Vehicle registrations by type per borough |

### TRANSPORT — Public Transport & Cycling

| # | Dataset | Source URL | Format | Path | Why |
|---|---------|-----------|--------|------|-----|
| 7 | Public Transport Journeys by Type | https://data.london.gov.uk/dataset/public-transport-journeys-by-type-of-transport-ep8ow | CSV | A (DuckDB) | Structured: bus/tube/DLR journeys by period — trend analysis |
| 8 | Santander Cycle Hires | https://data.london.gov.uk/dataset/number-bicycle-hires | CSV | A (DuckDB) | Daily counts — correlate with weather, events |
| 9 | Cycling Infrastructure Database | https://data.london.gov.uk/dataset/cycling-infrastructure-database-23n1k/ | CSV/GeoJSON | A+B | Cycle lanes, parking, signals — infrastructure coverage analysis |
| 10 | Walking & Cycling by Borough | https://data.london.gov.uk/dataset/walking-and-cycling-by-borough-vd6j4 | CSV | A (DuckDB) | Borough-level proportions — spatial analysis |
| 11 | Public Transport Accessibility (PTALs) | https://data.london.gov.uk/dataset/public-transport-accessibility-levels-24rz6 | CSV | A+B | Scores + methodology text for reasoning about access gaps |
| 12 | Busiest Airports by Passenger Traffic | https://data.london.gov.uk/dataset/busiest-airports-by-passenger-traffic-em8jg/ | CSV | A (DuckDB) | Airport passenger volumes — aviation demand |
| 13 | Number of Buses by Type | https://data.london.gov.uk/dataset/number-of-buses-by-type-of-bus-in-london-e791n | CSV | A (DuckDB) | Fleet composition over time |

### TRANSPORT — Live TfL Feeds & Disruptions

| # | Dataset | Source URL | Format | Path | Why |
|---|---------|-----------|--------|------|-----|
| 14 | TfL Live Traffic Disruptions | https://data.london.gov.uk/dataset/tfl-live-traffic-disruptions-248xn/ | JSON/API | C (Live) | Real-time road disruption events |
| 15 | TfL Live Traffic Cameras | https://data.london.gov.uk/dataset/tfl-live-traffic-cameras-2kmnd/ | JSON/API | C (Live) | Live camera feeds for traffic monitoring |
| 16 | TfL Live Roadside Message Signs | https://data.london.gov.uk/dataset/tfl-live-roadside-message-signs-2983o/ | JSON/API | C (Live) | Electronic message sign content |

### TRANSPORT — Other

| # | Dataset | Source URL | Format | Path | Why |
|---|---------|-----------|--------|------|-----|
| 17 | Road Safety / Collisions | https://data.london.gov.uk/dataset/road-collision-severity | CSV | A+B | Structured (counts by severity) + Text (descriptions for reasoning about causes) |
| 18 | Road Transport Energy Consumption | https://data.london.gov.uk/dataset/road-transport-energy-consumption-borough-v8pmm | CSV | A (DuckDB) | Fuel consumption by borough — sustainability queries |
| 19 | London Underground Temperatures | https://data.london.gov.uk/dataset/london-underground-average-monthly-temperatures-epr8d | CSV | A (DuckDB) | Monthly temps — heat correlations |

### ENVIRONMENT & AIR QUALITY

| # | Dataset | Source URL | Format | Path | Why |
|---|---------|-----------|--------|------|-----|
| 20 | London Air Quality (GLA) | https://data.london.gov.uk/air-quality/ | CSV/XLSX/JSON/PDF | A+B | GLA air quality dashboard data — pollutants by site and time |
| 21 | London Air (KCL Network) | https://londonair.org.uk/london/asp/datadownload.asp | CSV/XLSX | A (DuckDB) | ⚠️ **Manual download required**: (1) Select "Site Group" dropdown → choose network, (2) Select "Date Range" picker → set start/end, (3) Check pollutant species checkboxes, (4) Click "Download Data" button. Exports CSV/XLSX. |
| 22 | LAEI Borough Air Quality | https://data.london.gov.uk/dataset/laei-2022-borough-air-quality-data-for-llaqm | CSV/XLSX/ZIP | A+B | Pollutant concentrations (structured) + methodology (reasoning context) |
| 23 | London Atmospheric Emissions Inventory | https://data.london.gov.uk/dataset/london-atmospheric-emissions-inventory--laei--2022 | CSV/XLSX/ZIP | A (DuckDB) | Emissions by source, pollutant, geography |
| 24 | London Reservoir Levels | https://data.london.gov.uk/dataset/london-reservoir-levels-24ry5 | CSV/XLSX | A (DuckDB) | Daily levels since 1989 — drought/flood reasoning |
| 25 | London Energy & GHG Inventory (LEGGI) | https://data.london.gov.uk/dataset/london-energy-and-greenhouse-gas-inventory-leggi-2ko63 | CSV/XLSX/PDF | A+B | Emissions data + policy context for climate reasoning |
| 26 | Fly-tipping Incidents | https://data.london.gov.uk/dataset/fly-tipping-incidents-e5myg | CSV/XLSX | A (DuckDB) | Incident counts by borough — urban cleanliness |
| 27 | London Green Infrastructure (LGIF) | https://data.london.gov.uk/dataset/london-green-infrastructure-framework-lgif-e70pq | CSV/XLSX/PDF/JSON | B (RAG) | Framework methodology — reasoning about green space planning |
| 28 | London Public Realm Trees | https://data.london.gov.uk/dataset/london-public-realm-trees-2r45m | CSV/XLSX/JSON | A (DuckDB) | 1.14M trees with species + location — urban ecology |
| 29 | London Solar Opportunity Map | https://data.london.gov.uk/dataset/london-solar-opportunity-map-lsom-vdxyl | CSV/XLSX/JSON | A (DuckDB) | Solar potential by area |

### PLANNING & HOUSING

| # | Dataset | Source URL | Format | Path | Why |
|---|---------|-----------|--------|------|-----|
| 30 | Planning Applications (Datahub) | https://data.london.gov.uk/dataset/planning-applications-london | CSV/XLSX/JSON | A+B | Structured (status, dates, type) + Text (descriptions for reasoning about impact) |
| 31 | Brownfield Register | https://data.london.gov.uk/dataset/brownfield-register-2og9g | CSV/XLSX | A+B | Sites + context for development reasoning |
| 32 | Affordable Housing Supply | https://data.london.gov.uk/dataset/dclg-affordable-housing-supply-borough | CSV/XLSX | A (DuckDB) | Borough-level housing delivery |
| 33 | London Building Stock Model | https://data.london.gov.uk/dataset/london-building-stock-model-2-lbsm-2-2k55d | CSV/XLSX | A (DuckDB) | EPC ratings, heating, insulation — energy planning |

### SAFETY & EMERGENCY

| # | Dataset | Source URL | Format | Path | Why |
|---|---------|-----------|--------|------|-----|
| 34 | MPS Recorded Crime (Geographic) | https://data.london.gov.uk/dataset/mps-recorded-crime-geographic-breakdown-exy3m | CSV/XLSX | A (DuckDB) | Crime by borough/ward/LSOA — safety planning |
| 35 | London Fire Brigade Incidents | https://data.london.gov.uk/dataset/london-fire-brigade-incident-records-em8xy | CSV/XLSX | A+B | Structured incidents + narrative for causal reasoning |
| 36 | London Fire Brigade Mobilisation | https://data.london.gov.uk/dataset/london-fire-brigade-mobilisation-records-24r65 | CSV/XLSX | A (DuckDB) | Response times — service efficiency |

### REAL-TIME FEEDS (Path C — API at query time)

| # | Feed | Endpoint | Format | Refresh |
|---|------|----------|--------|---------|
| 37 | TfL Road Disruptions | https://api.tfl.gov.uk/Road/all/Disruption | JSON | 5 min |
| 38 | TfL Road Corridor Status | https://api.tfl.gov.uk/Road | JSON | Live |
| 39 | OpenWeatherMap London | https://api.openweathermap.org/data/2.5/weather?lat=51.5074&lon=-0.1278&units=metric | JSON | Live |
| 40 | TfL Air Quality Forecast | https://api.tfl.gov.uk/AirQuality | JSON | Hourly |
| 41 | TfL Cycle Hire Availability | https://api.tfl.gov.uk/BikePoint | JSON | Live |

---

## Ingestion Decision Matrix

```
For each dataset column, ask:

┌─────────────────────────────────────────────────────────────┐
│  Is the value in NUMBERS (counts, time-series, metrics)?     │
│  YES → Path A: DuckDB (Parquet) → sql_query tool            │
│                                                               │
│  Is the value in CONTEXT (descriptions, methodology, why)?   │
│  YES → Path B: Chunk → Embed → FAISS → rag_search tool      │
│                                                               │
│  Does it change in real-time?                                │
│  YES → Path C: API call at query time → web_scraper tool     │
│                                                               │
│  Does it have BOTH numbers AND text?                         │
│  YES → Path A + B: Numbers to DuckDB, text chunks to FAISS  │
└─────────────────────────────────────────────────────────────┘
```

### What goes to RAG (Path B) — for REASONING not metrics:
- Planning application DESCRIPTIONS (why was it approved/rejected?)
- Collision NARRATIVES (what caused this accident?)
- Policy documents and methodology explanations
- Green infrastructure framework rationale
- Air quality methodology and health guidance
- Fire incident DESCRIPTIONS (what happened, why?)

### What stays in DuckDB (Path A) — for ANALYSIS not reasoning:
- Time-series (vehicle counts, journey numbers, temperatures)
- Geographic aggregations (by borough, ward, LSOA)
- Numeric indicators (pollution levels, energy consumption)
- Status/category fields (crime type, bus type, EPC rating)

---

## Total Data Estimate

| Path | Datasets | Raw Size (est) | Processed Size |
|------|----------|---------------|----------------|
| A (DuckDB) | 24 tables | ~2-4 GB CSV | ~500MB-1GB Parquet |
| B (FAISS) | ~500K text chunks | N/A | ~4GB index (4096-dim × 500K vectors) |
| C (Live) | 5 API feeds | N/A | Fetched on demand |
