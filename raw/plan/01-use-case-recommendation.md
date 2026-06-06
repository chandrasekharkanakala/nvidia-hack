# Use Case Recommendation

## Recommended Track: Urban Operations

### Why Urban Operations Wins on Judging Criteria

| Criterion | Why Urban Ops Scores High |
|-----------|--------------------------|
| Technical Depth (15pts) | Complex pipeline: real-time data ingestion → geospatial processing → simulation → prediction → agent reasoning |
| Spark Story (15pts) | 128GB unified memory holds city-scale graph + LLM context simultaneously; local inference for low-latency real-time decisions |
| Insight Quality (10pts) | Non-obvious correlations (e.g., "Tuesday market on Borough High St causes 23-min cascade delay on A3 southbound by 4:47pm") |
| Creativity (10pts) | Combine transport + weather + events + air quality data with temporal reasoning |
| Usability (10pts) | City planner can ask "What happens if we close London Bridge for 2 hours on Saturday?" and get a simulation |

---

## Proposed Use Case: London Urban Intelligence Agent ("LUCIA")

**One-liner**: An agentic system that ingests City of London open data (transport, air quality, planning, events) and lets urban planners ask natural-language questions, get non-obvious insights, run what-if simulations, and receive predictions — all running locally on DGX Spark.

### User Personas
1. **City Planner** — "If I approve this construction permit, what's the traffic impact?"
2. **Transport Operator** — "Predict congestion hotspots for next Monday given forecasted rain"
3. **Citizen** — "Best time to cycle from Shoreditch to Bank avoiding pollution?"

### Interaction Modes
- **Chat** (web UI)
- **Voice** (ElevenLabs TTS + Whisper STT)
- **API** (REST/gRPC for integrations)
- **Image input** (upload traffic camera stills, planning documents)

### Key Capabilities
1. **Insight Engine** — Historical pattern mining, anomaly detection
2. **Prediction Engine** — Time-series forecasting (traffic flow, air quality)
3. **Simulation Engine** — What-if scenario modelling
4. **Recommendation Engine** — Actionable next steps with confidence scores

---

## Data Sources (City of London Open Data)

| Dataset | Use |
|---------|-----|
| TfL Traffic Flow | Real-time + historical traffic volumes |
| Air Quality Monitoring | PM2.5, NO2 sensor readings |
| Planning Applications | Construction/road works schedules |
| Road Collision Data | Safety pattern analysis |
| Events Calendar | Predict demand spikes |
| Weather (scraped) | Correlation with all above |

---

## Decision

Proceed with **Urban Operations — LUCIA** unless overridden.
