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

### TRANSPORT (Track: Urban Operations — Core)

| # | Dataset | Source URL | Format | Path | Why |
|---|---------|-----------|--------|------|-----|
| 1 | Congestion Charge Zone Vehicles | https://data.london.gov.uk/dataset/camera-captures-and-confirmed-vehicles-seen-in-the-congestion-ch-2r88d | CSV | A (DuckDB) | Time-series of vehicle counts — queries like "how many vehicles in Jan vs Jul?" |
| 2 | Public Transport Journeys by Type | https://data.london.gov.uk/dataset/public-transport-journeys-by-type-of-transport-ep8ow | CSV | A (DuckDB) | Structured: bus/tube/DLR journeys by period — trend analysis |
| 3 | Santander Cycle Hires | https://data.london.gov.uk/dataset/number-bicycle-hires | CSV | A (DuckDB) | Daily counts — correlate with weather, events |
| 4 | Road Safety / Collisions | https://data.london.gov.uk/dataset/road-collision-severity | CSV | A+B | Structured (counts by severity) + Text (descriptions for reasoning about causes) |
| 5 | Walking & Cycling by Borough | https://data.london.gov.uk/dataset/walking-and-cycling-by-borough-vd6j4 | CSV | A (DuckDB) | Borough-level proportions — spatial analysis |
| 6 | Public Transport Accessibility (PTALs) | https://data.london.gov.uk/dataset/public-transport-accessibility-levels-24rz6 | CSV | A+B | Scores + methodology text for reasoning about access gaps |
| 7 | Road Transport Energy Consumption | https://data.london.gov.uk/dataset/road-transport-energy-consumption-borough-v8pmm | CSV | A (DuckDB) | Fuel consumption by borough — sustainability queries |
| 8 | London Underground Temperatures | https://data.london.gov.uk/dataset/london-underground-average-monthly-temperatures-epr8d | CSV | A (DuckDB) | Monthly temps — heat correlations |
| 9 | Number of Buses by Type | https://data.london.gov.uk/dataset/number-of-buses-by-type-of-bus-in-london-e791n | CSV | A (DuckDB) | Fleet composition over time |

### ENVIRONMENT & AIR QUALITY

| # | Dataset | Source URL | Format | Path | Why |
|---|---------|-----------|--------|------|-----|
| 10 | LAEI Borough Air Quality | https://data.london.gov.uk/dataset/laei-2022-borough-air-quality-data-for-llaqm | CSV/ZIP | A+B | Pollutant concentrations (structured) + methodology (reasoning context) |
| 11 | London Atmospheric Emissions Inventory | https://data.london.gov.uk/dataset/london-atmospheric-emissions-inventory--laei--2022 | CSV/ZIP | A (DuckDB) | Emissions by source, pollutant, geography |
| 12 | London Reservoir Levels | https://data.london.gov.uk/dataset/london-reservoir-levels-24ry5 | CSV | A (DuckDB) | Daily levels since 1989 — drought/flood reasoning |
| 13 | London Energy & GHG Inventory (LEGGI) | https://data.london.gov.uk/dataset/london-energy-and-greenhouse-gas-inventory-leggi-2ko63 | CSV | A+B | Emissions data + policy context for climate reasoning |
| 14 | Fly-tipping Incidents | https://data.london.gov.uk/dataset/fly-tipping-incidents-e5myg | CSV | A (DuckDB) | Incident counts by borough — urban cleanliness |
| 15 | London Green Infrastructure (LGIF) | https://data.london.gov.uk/dataset/london-green-infrastructure-framework-lgif-e70pq | CSV | B (RAG) | Framework methodology — reasoning about green space planning |
| 16 | London Public Realm Trees | https://data.london.gov.uk/dataset/london-public-realm-trees-2r45m | CSV | A (DuckDB) | 1.14M trees with species + location — urban ecology |
| 17 | London Solar Opportunity Map | https://data.london.gov.uk/dataset/london-solar-opportunity-map-lsom-vdxyl | CSV | A (DuckDB) | Solar potential by area |

### PLANNING & HOUSING

| # | Dataset | Source URL | Format | Path | Why |
|---|---------|-----------|--------|------|-----|
| 18 | Planning Applications (Datahub) | https://data.london.gov.uk/dataset/planning-applications-london | CSV | A+B | Structured (status, dates, type) + Text (descriptions for reasoning about impact) |
| 19 | Brownfield Register | https://data.london.gov.uk/dataset/brownfield-register-2og9g | CSV | A+B | Sites + context for development reasoning |
| 20 | Affordable Housing Supply | https://data.london.gov.uk/dataset/dclg-affordable-housing-supply-borough | CSV | A (DuckDB) | Borough-level housing delivery |
| 21 | London Building Stock Model | https://data.london.gov.uk/dataset/london-building-stock-model-2-lbsm-2-2k55d | CSV | A (DuckDB) | EPC ratings, heating, insulation — energy planning |

### SAFETY & EMERGENCY

| # | Dataset | Source URL | Format | Path | Why |
|---|---------|-----------|--------|------|-----|
| 22 | MPS Recorded Crime (Geographic) | https://data.london.gov.uk/dataset/mps-recorded-crime-geographic-breakdown-exy3m | CSV | A (DuckDB) | Crime by borough/ward/LSOA — safety planning |
| 23 | London Fire Brigade Incidents | https://data.london.gov.uk/dataset/london-fire-brigade-incident-records-em8xy | CSV | A+B | Structured incidents + narrative for causal reasoning |
| 24 | London Fire Brigade Mobilisation | https://data.london.gov.uk/dataset/london-fire-brigade-mobilisation-records-24r65 | CSV | A (DuckDB) | Response times — service efficiency |

### REAL-TIME FEEDS (Path C — API at query time)

| # | Feed | Endpoint | Format | Refresh |
|---|------|----------|--------|---------|
| 25 | TfL Road Disruptions | https://api.tfl.gov.uk/Road/all/Disruption | JSON | 5 min |
| 26 | TfL Road Corridor Status | https://api.tfl.gov.uk/Road | JSON | Live |
| 27 | OpenWeatherMap London | https://api.openweathermap.org/data/2.5/weather?lat=51.5074&lon=-0.1278&units=metric | JSON | Live |
| 28 | TfL Air Quality Forecast | https://api.tfl.gov.uk/AirQuality | JSON | Hourly |
| 29 | TfL Cycle Hire Availability | https://api.tfl.gov.uk/BikePoint | JSON | Live |

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
