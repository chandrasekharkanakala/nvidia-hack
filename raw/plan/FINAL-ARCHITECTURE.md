# LUCIA — Final E2E Architecture (Consolidated)

> London Urban City Intelligence Agent — NVIDIA Hackathon 2026
> Track: Urban Operations | Hardware: DGX Spark (128GB Unified Memory)

---

## System Architecture (Single Diagram)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              LUCIA — E2E                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │  PRESENTATION (React + Vite + TailwindCSS)                           │    │
│  │  Chat │ Voice (Whisper STT + ElevenLabs TTS) │ Image Upload │ Maps   │    │
│  └────────────────────────────────┬─────────────────────────────────────┘    │
│                                   │ WebSocket + REST                          │
│                                   ▼                                           │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │  FastAPI Gateway (:8000)                                              │    │
│  │  Sessions │ Routing │ Streaming │ Metrics Middleware                   │    │
│  └────────────────────────────────┬─────────────────────────────────────┘    │
│                                   ▼                                           │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │  NeMo Guardrails (Input + Output Rails)                               │    │
│  │  ┌────────────────────────────────────────────────────────────────┐   │    │
│  │  │  INPUT:  PII Scan → Jailbreak Detect → Topic Control           │   │    │
│  │  │  OUTPUT: PII Redact → Hallucination Check → Content Safety     │   │    │
│  │  └────────────────────────────────────────────────────────────────┘   │    │
│  │  Model: Nemotron Content Safety Reasoning 4B (shared via vLLM)        │    │
│  └────────────────────────────────┬─────────────────────────────────────┘    │
│                                   ▼                                           │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │  NemoClaw Agent Runtime (OpenShell Sandbox)                           │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                            │    │
│  │  │  Router  │→ │ Planner  │→ │ Executor │  ← All use NemoTron Nano   │    │
│  │  │ (intent  │  │ (decomp  │  │ (tools)  │    as reasoning backbone   │    │
│  │  │  + mode) │  │  deep    │  │          │                            │    │
│  │  │          │  │  only)   │  │          │                            │    │
│  │  └──────────┘  └──────────┘  └──────────┘                            │    │
│  │                                                                        │    │
│  │  Mode: LIGHT → Router → 1 tool call → respond (<2s)                  │    │
│  │  Mode: DEEP  → Router → Planner → up to 5 tool calls → reflect (5-15s)│   │
│  │                                                                        │    │
│  │  Policy: filesystem + network + tool allow-lists (YAML)               │    │
│  └────────────────────────────────┬─────────────────────────────────────┘    │
│                                   ▼                                           │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │  Tool Layer (each tool = pure function, policy-gated by NemoClaw)     │    │
│  │                                                                        │    │
│  │  rag_search   → FAISS-GPU + NV-Embed-v2                               │    │
│  │  sql_query    → DuckDB (NemoTron generates SQL)                        │    │
│  │  web_scraper  → aiohttp + BeautifulSoup (weather, TfL live)           │    │
│  │  simulator    → NumPy + NetworkX (traffic redistribution)             │    │
│  │  predictor    → statsmodels/Prophet (time-series)                     │    │
│  │  vision       → NeVA-7B always loaded (:8003)                       │    │
│  └────────────────────────────────┬─────────────────────────────────────┘    │
│                                   ▼                                           │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │  Data Layer (DuckDB is the single store — no SQLite, no Redis)        │    │
│  │                                                                        │    │
│  │  DuckDB (:memory: + Parquet on disk)                                  │    │
│  │    • Structured city data tables (traffic, air quality, events)        │    │
│  │    • Conversation history & session state                             │    │
│  │    • Metrics & eval scores                                            │    │
│  │    • Data catalog (metadata about all ingested datasets)              │    │
│  │                                                                        │    │
│  │  FAISS-GPU (vector index on disk, GPU-resident at runtime)            │    │
│  │    • Embedded chunks from all text/document data                      │    │
│  │    • 4096-dim vectors from NV-Embed-v2                                │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                                                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │  Model Layer — ALL served via single vLLM instance (:8001)            │    │
│  │                                                                        │    │
│  │  Nemotron 3 Nano (30B/3.5B active)  — reasoning, planning, routing   │    │
│  │  Nemotron Content Safety 4B          — guardrails (PII + toxicity)    │    │
│  │  NV-Embed-v2 (7.85B)               — embeddings (served on :8002)    │    │
│  │  NeVA-7B (always loaded)              — vision (traffic cams, docs)  │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                                                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │  Observability (built into FastAPI middleware — no separate system)    │    │
│  │  structlog → DuckDB metrics table                                     │    │
│  │  Tracked: latency, tokens, hallucination score, tool success rates    │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Deduplication Decisions

| Concern | Single Tool Handling It | Replaces |
|---------|------------------------|----------|
| PII detection + redaction | NeMo Guardrails (input/output rails) | Presidio, custom regex |
| Hallucination check | NeMo Guardrails (output rail) | Separate reflector module |
| Content safety / toxicity | Nemotron Content Safety 4B (via Guardrails) | Separate toxicity lib |
| Jailbreak / prompt injection | NeMo Guardrails (input rail) | Custom filter code |
| Structured data + sessions + metrics | DuckDB (single engine) | SQLite + Redis + separate metrics DB |
| Model serving | vLLM (multi-model) | NIM + custom scripts |
| Agent orchestration + sandboxing | NemoClaw (policy YAML) | LangGraph + custom security |
| Routing (light/deep) | NemoClaw router (NemoTron few-shot) | Separate LLM Router service |

---

## Consolidated Tech Stack (No Redundancy)

| Role | Tool | Why Only This |
|------|------|---------------|
| **LLM** | Nemotron 3 Nano | Single model for: routing, planning, tool-calling, SQL gen, response synthesis |
| **Safety** | NeMo Guardrails + Nemotron Content Safety 4B | Single framework for ALL input/output guardrails |
| **Agent Runtime** | NemoClaw | Orchestration + sandbox + policy — no separate security layer needed |
| **Embeddings** | NV-Embed-v2 | One model for all embedding needs (ingestion + query-time) |
| **Vector Search** | FAISS-GPU | Single index, GPU-accelerated |
| **All Structured Data** | DuckDB | Analytics + sessions + memory + metrics + catalog — one engine |
| **Model Serving** | vLLM | Serves Nano + Content Safety (multi-model on single port) |
| **API** | FastAPI | Gateway + sessions + metrics middleware — one process |
| **UI** | React + Vite | Chat + voice + maps + metrics panel — one app |
| **Voice** | Whisper (STT) + ElevenLabs (TTS) | Minimal — one local, one API |
| **Data Processing** | pandas (+ RAPIDS cuDF stretch) | Single ETL path |
| **Scraping** | aiohttp + BeautifulSoup | Single HTTP + parse combo |

---

## Data Ingestion Pipeline

```
Raw Sources                          Processing                    Storage
───────────                          ──────────                    ───────

CSV/Excel files ─┐
                 │    ┌──────────────────────────────────┐
TfL API feeds ───┤    │  ingestion/loader.py              │
                 ├──→ │  1. Read (pandas/openpyxl)        │
Weather scrape ──┤    │  2. Clean & normalize             │──→ DuckDB (Parquet tables)
                 │    │  3. PII scan (NeMo Guardrails)    │
Events calendar ─┘    │  4. Split: structured vs text     │
                      └──────────┬───────────────────────┘
                                 │
                                 │ text chunks
                                 ▼
                      ┌──────────────────────────────────┐
                      │  ingestion/embedder.py            │
                      │  1. Chunk (token-based splitter)  │──→ FAISS-GPU index
                      │  2. Embed (NV-Embed-v2 :8002)    │    (persisted to disk)
                      │  3. Index (FAISS IVF-Flat GPU)   │
                      └──────────────────────────────────┘
```

**Key: PII scanning happens AT INGESTION** — NeMo Guardrails scans raw text before it enters the vector store or DuckDB. No PII in the system from the start.

---

## NeMo Guardrails Configuration

```yaml
# config/guardrails/config.yml

models:
  - type: main
    engine: vllm
    parameters:
      base_url: http://localhost:8001/v1
      model: nemotron-3-nano

  - type: content_safety
    engine: vllm
    parameters:
      base_url: http://localhost:8001/v1
      model: nemotron-content-safety-reasoning-4b

rails:
  input:
    flows:
      - detect pii          # Block/redact PII in user messages
      - check jailbreak     # Reject prompt injection attempts
      - check topic allowed # Only urban operations / city planning topics

  output:
    flows:
      - redact pii              # Ensure no PII leaks in responses
      - check hallucination     # Validate claims against source data
      - check content safety    # Block toxic/harmful content

  config:
    pii:
      entities:
        - PERSON
        - EMAIL_ADDRESS
        - PHONE_NUMBER
        - UK_NHS_NUMBER
        - CREDIT_CARD
        - UK_POSTCODE
      action: redact  # or "block"

    topic:
      allowed:
        - urban planning
        - traffic analysis
        - air quality
        - city infrastructure
        - transport
        - public services
        - events impact
      blocked:
        - personal advice
        - medical
        - legal
        - financial trading
```

---

## NemoClaw Policy (Agent Sandbox)

```yaml
# config/nemoclaw/agent-policy.yaml

agent:
  name: lucia
  model: nemotron-3-nano
  endpoint: http://localhost:8001/v1

permissions:
  filesystem:
    read: ["/data/processed/*", "/data/embeddings/*"]
    write: ["/data/output/*", "/tmp/*"]
  network:
    allow:
      - "localhost:8001"          # vLLM (LLM)
      - "localhost:8002"          # NV-Embed
      - "api.openweathermap.org"  # Weather
      - "api.tfl.gov.uk"         # Transport for London
      - "api.elevenlabs.io"      # Voice TTS
    deny: ["*"]
  tools:
    enabled:
      - rag_search
      - sql_query
      - web_scraper
      - simulator
      - predictor
      - vision
      - calculator

inference:
  primary:
    model: nemotron-3-nano
    endpoint: http://localhost:8001/v1
  embedding:
    model: nv-embed-v2
    endpoint: http://localhost:8002/v1

audit:
  log_level: full
  store: duckdb  # Audit logs go to same DuckDB instance
```

---

## Memory Budget (Final — Config A: Nano)

```
┌─────────────────────────────────────────────────────┐
│         128GB Unified Memory                         │
├─────────────────────────────────────────────────────┤
│  Nemotron 3 Nano (FP16)              35 GB          │
│  Nemotron Content Safety 4B (FP16)    8 GB          │
│  NV-Embed-v2 (FP16)                 20 GB          │
│  FAISS-GPU Index                      4 GB          │
│  DuckDB (all tables + memory)         5 GB          │
│  Whisper Large v3 (STT)              4 GB          │
│  NeVA-7B (vision — always loaded)    12 GB          │
│  FAISS-GPU Index                      4 GB          │
│  DuckDB (all tables + memory)         5 GB          │
│  Application (FastAPI + NemoClaw)     2 GB          │
│  OS + Overhead                        6 GB          │
│  ─────────────────────────────────────────          │
│  TOTAL                              92 GB          │
│  FREE                               36 GB          │
└─────────────────────────────────────────────────────┘
```

---

## Port Map (Minimal)

| Service | Port | Notes |
|---------|------|-------|
| React UI (Vite) | 3000 | Frontend |
| FastAPI (API + WS + Guardrails) | 8000 | Single backend process |
| vLLM (Nano + Content Safety) | 8001 | Multi-model serving |
| NV-Embed-v2 (TEI) | 8002 | Embedding service |
| NeVA-7B (Vision) | 8003 | Vision model serving |
| NemoClaw Runtime | 8080 | Agent sandbox |

All via SSH port-forward from laptop.

---

## Startup Sequence (5 commands)

```bash
# 1. Serve models (Nano + Content Safety on one vLLM instance)
vllm serve nvidia/nemotron-3-nano,nvidia/nemotron-content-safety-4b \
  --port 8001 --gpu-memory-utilization 0.35

# 2. Serve embeddings
python -m src.models.embed_server --model nv-embed-v2 --port 8002

# 3. Serve vision model
python -m src.models.vision_server --model neva-7b --port 8003

# 4. Start NemoClaw agent
nemoclaw start --policy config/nemoclaw/agent-policy.yaml --port 8080

# 5. Start backend (FastAPI + Guardrails integrated)
uvicorn src.api.main:app --host 0.0.0.0 --port 8000

# 6. Start UI
cd ui && npm run dev -- --port 3000 --host 0.0.0.0
```

---

## Repo Structure (Updated — Flat, No Duplication)

```
lucia/
├── config/
│   ├── guardrails/            # NeMo Guardrails config (YAML + Colang)
│   │   ├── config.yml
│   │   └── rails/
│   │       ├── pii.co
│   │       ├── jailbreak.co
│   │       └── topic.co
│   ├── nemoclaw/
│   │   └── agent-policy.yaml  # NemoClaw sandbox policy
│   └── settings.py            # Pydantic BaseSettings (single config source)
├── src/
│   ├── ingestion/
│   │   ├── loader.py          # Read CSV/Excel/API → pandas DataFrame
│   │   └── embedder.py        # Chunk → NV-Embed → FAISS index
│   ├── agent/
│   │   └── orchestrator.py    # Thin wrapper: FastAPI ↔ NemoClaw ↔ Guardrails
│   ├── tools/
│   │   ├── rag_search.py      # FAISS query
│   │   ├── sql_query.py       # DuckDB query (NemoTron writes SQL)
│   │   ├── web_scraper.py     # aiohttp + BS4
│   │   ├── simulator.py       # NetworkX graph perturbation
│   │   ├── predictor.py       # statsmodels time-series
│   │   └── vision.py          # NeVA-7B (load on demand)
│   ├── api/
│   │   ├── main.py            # FastAPI app (chat, voice, health, metrics)
│   │   └── middleware.py      # Logging + metrics → DuckDB
│   └── voice/
│       ├── stt.py             # Whisper
│       └── tts.py             # ElevenLabs
├── ui/                        # React + Vite + Tailwind
│   └── src/
│       ├── App.tsx
│       └── components/        # ChatPanel, VoiceButton, AgentToggle, MetricsPanel
├── data/
│   ├── raw/                   # Downloaded datasets
│   ├── processed/             # Parquet files (DuckDB reads these)
│   └── embeddings/            # FAISS index files
├── scripts/
│   ├── setup.sh               # DGX Spark env setup (one script)
│   ├── ingest.py              # Run full ingestion pipeline
│   └── start.sh               # Launch all services (5 commands above)
├── tests/
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## NVIDIA Ecosystem Scoring (Target: 30/30)

| NVIDIA Tool | Role in LUCIA | Points |
|-------------|---------------|--------|
| Nemotron 3 Nano | LLM backbone (reasoning, planning, routing, SQL gen) | ✅ Primary |
| Nemotron Content Safety 4B | PII + toxicity + safety (via NeMo Guardrails) | ✅ Primary |
| NeMo Guardrails | Input/output rails framework | ✅ Primary |
| NemoClaw | Agent sandbox + orchestration | ✅ Primary |
| NV-Embed-v2 | Embedding generation | ✅ Supporting |
| FAISS-GPU | Vector search (GPU-accelerated on Spark) | ✅ Supporting |
| NeVA-7B | Vision (traffic cams, planning docs, image understanding) | ✅ Primary |
| RAPIDS cuDF | Data processing (stretch) | Bonus |

**Spark Story**: "LUCIA runs 5 NVIDIA models simultaneously in 128GB unified memory — Nano for reasoning, Content Safety for guardrails, NV-Embed for retrieval, NeVA for vision, and FAISS on GPU for sub-200ms search. Zero external API calls for inference. City data never leaves the device."

---

## What Each Component Does (No Overlap)

| Component | Sole Responsibility |
|-----------|---------------------|
| **vLLM** | Serve model weights, manage GPU memory, handle inference requests |
| **NeMo Guardrails** | ALL safety: PII, toxicity, jailbreak, hallucination, topic control |
| **NemoClaw** | ALL security: sandboxing, policy enforcement, tool permissions, audit |
| **NemoTron Nano** | ALL reasoning: intent routing, query planning, SQL generation, response synthesis |
| **NV-Embed-v2** | ALL embeddings: ingestion-time and query-time |
| **FAISS-GPU** | ALL vector operations: indexing and retrieval |
| **DuckDB** | ALL structured storage: city data, sessions, metrics, catalog, audit logs |
| **FastAPI** | ALL HTTP: REST, WebSocket, middleware, session management |
| **NeVA-7B** | ALL vision: traffic cam analysis, document reading, image understanding |
| **React** | ALL UI: chat, voice, maps, metrics display, agent mode toggle |
