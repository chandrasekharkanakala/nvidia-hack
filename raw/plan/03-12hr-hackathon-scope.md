# 12-Hour Hackathon — Feasible Scope

## Philosophy
Build the **full pipeline end-to-end first** (even if shallow), then deepen each layer. A working demo beats a half-built masterpiece.

---

## What's IN (12hr)

### Hour 0-1: Foundation
- [x] Repo structure + boilerplate
- [x] SSH into DGX Spark, validate GPU access
- [x] Install core deps (NeMo, RAPIDS, FastAPI)
- [x] Download 2-3 key datasets (traffic + air quality + events)

### Hour 1-3: Data Pipeline
- [ ] ETL: Load CSVs → DuckDB (structured queries)
- [ ] Chunk text data → generate embeddings (NV-Embed) → FAISS index
- [ ] Data catalog (simple JSON manifest of available datasets)

### Hour 3-5: Agent Core
- [ ] NemoTron model serving (local inference via NIM or vLLM)
- [ ] NemoClaw agent orchestrator setup (router + planner + executor)
- [ ] 3 core tools: RAG search, SQL query, web scraper (weather)
- [ ] Basic conversation memory (SQLite)

### Hour 5-7: API + Basic UI
- [ ] FastAPI backend with WebSocket for streaming responses
- [ ] Simple React chat UI (can be Vite + Tailwind, minimal)
- [ ] Connect UI ↔ Backend ↔ Agent pipeline
- [ ] Test full flow: user asks question → agent reasons → returns answer

### Hour 7-9: Depth & Differentiation
- [ ] Prediction tool (simple time-series on traffic data)
- [ ] What-if simulation (parameter perturbation on traffic model)
- [ ] Multi-step reasoning demo (complex query decomposition)
- [ ] Image input support (upload traffic camera image → Vision model)

### Hour 9-10: Voice + Polish
- [ ] ElevenLabs TTS integration (agent speaks responses)
- [ ] Whisper STT (voice input)
- [ ] Light/Deep agent toggle in UI

### Hour 10-11: Observability & Eval
- [ ] Basic eval: response quality scoring
- [ ] Hallucination check (compare agent claims vs source data)
- [ ] Latency + token usage logging
- [ ] Performance metrics display in UI

### Hour 11-12: Demo Prep
- [ ] 3 compelling demo scenarios scripted
- [ ] Slides (minimal — system speaks for itself)
- [ ] Record backup video in case of live demo failure

---

## What's OUT (12hr)

| Feature | Why Deferred |
|---------|-------------|
| Fine-tuning NemoTron on London data | Time constraint — RAG is sufficient |
| Full RAPIDS cuDF pipeline | DuckDB + pandas adequate for dataset size |
| Production auth/security | Demo context, not production |
| Mobile UI | Desktop browser sufficient for demo |
| Multi-user sessions | Single-user demo sufficient |
| Custom model training | Pre-trained models + prompting |

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| NemoTron too large for Spark | Fall back to smaller NemoTron variant (8B) |
| NemoClaw setup complexity | Fall back to LangGraph or custom orchestration |
| Dataset quality issues | Pre-validate during Hour 0, have backup datasets |
| SSH/network issues | All computation on Spark, minimal network dependency |
| Model hallucination | Ground all responses in source data citations |

---

## Demo Scenarios (3 compelling stories)

### Demo 1: "The Rain Insight"
> Planner asks: "What happens to traffic on London Bridge when it rains on a Friday?"
> Agent: Queries weather history + traffic data → reveals non-obvious pattern → shows prediction for next Friday

### Demo 2: "The Construction What-If"
> Planner asks: "If I approve closing Threadneedle St for 3 weeks, what's the impact?"
> Agent: Runs simulation → shows cascade effects on surrounding roads → recommends optimal timing

### Demo 3: "The Image + Voice"
> Planner uploads traffic camera image → speaks: "Is this normal for 3pm Tuesday?"
> Agent: Vision model identifies congestion level → compares to historical baseline → explains anomaly
