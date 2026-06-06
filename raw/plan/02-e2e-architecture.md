# E2E Architecture — Full Vision

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        LUCIA — Full Architecture                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐   │
│  │  Web UI      │    │  Voice I/O   │    │  REST API            │   │
│  │  (React/Next)│    │  (11Labs+    │    │  (FastAPI)           │   │
│  │              │    │   Whisper)   │    │                      │   │
│  └──────┬───────┘    └──────┬───────┘    └──────────┬───────────┘   │
│         │                   │                       │               │
│         └───────────────────┼───────────────────────┘               │
│                             ▼                                        │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │              API Gateway / Session Manager                    │    │
│  │              (FastAPI + WebSocket + Auth)                     │    │
│  └──────────────────────────┬──────────────────────────────────┘    │
│                             ▼                                        │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │           Agent Orchestrator (NemoClaw)                       │    │
│  │  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐   │    │
│  │  │ Router  │→ │ Planner  │→ │ Executor │→ │ Reflector  │   │    │
│  │  └─────────┘  └──────────┘  └──────────┘  └────────────┘   │    │
│  └──────────────────────────┬──────────────────────────────────┘    │
│                             ▼                                        │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    Tool Layer                                 │    │
│  │  ┌────────────┐ ┌────────────┐ ┌───────────┐ ┌──────────┐  │    │
│  │  │ RAG Search │ │ SQL Query  │ │ Simulator │ │ Predictor│  │    │
│  │  │ (Vector DB)│ │ (DuckDB)  │ │ (Custom)  │ │ (TS Mod) │  │    │
│  │  └────────────┘ └────────────┘ └───────────┘ └──────────┘  │    │
│  │  ┌────────────┐ ┌────────────┐ ┌───────────┐              │    │
│  │  │ Web Scrape │ │ Vision     │ │ Calculator│              │    │
│  │  │ (Weather)  │ │ (Image In) │ │           │              │    │
│  │  └────────────┘ └────────────┘ └───────────┘              │    │
│  └──────────────────────────┬──────────────────────────────────┘    │
│                             ▼                                        │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                  Data & Memory Layer                          │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │    │
│  │  │ Vector Store │  │ Structured   │  │ Conversation     │   │    │
│  │  │ (Milvus/    │  │ Store        │  │ Memory           │   │    │
│  │  │  FAISS)     │  │ (DuckDB/     │  │ (Redis/SQLite)   │   │    │
│  │  │             │  │  Parquet)    │  │                  │   │    │
│  │  └──────────────┘  └──────────────┘  └──────────────────┘   │    │
│  └──────────────────────────┬──────────────────────────────────┘    │
│                             ▼                                        │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                  Model Layer (on DGX Spark)                   │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │    │
│  │  │ NemoTron     │  │ Embedding    │  │ Vision Model     │   │    │
│  │  │ (LLM -      │  │ Model        │  │ (for image       │   │    │
│  │  │  reasoning) │  │ (NV-Embed)   │  │  understanding)  │   │    │
│  │  └──────────────┘  └──────────────┘  └──────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                  Observability Layer                          │    │
│  │  Eval • Hallucination Detection • Latency • Token Usage      │    │
│  │  Context Window Tracking • Response Quality Scoring           │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Presentation Layer
| Component | Tech | Purpose |
|-----------|------|---------|
| Web UI | React + TailwindCSS | Chat interface, visualizations, map overlays |
| Voice | ElevenLabs (TTS) + Whisper (STT) | Natural voice interaction |
| API | FastAPI OpenAPI | Programmatic access for integrations |

### 2. Agent Orchestrator (NemoClaw)
- **Router**: Classifies intent → selects agent mode (insight/predict/simulate/recommend)
- **Planner**: Decomposes complex queries into tool-call sequences
- **Executor**: Runs tool calls with retry/fallback logic
- **Reflector**: Validates output quality, detects hallucination, triggers re-planning if needed

### 3. Tool Layer
| Tool | Function |
|------|----------|
| RAG Search | Semantic search over ingested documents & datasets |
| SQL Query | Analytical queries on structured data (DuckDB) |
| Simulator | What-if modelling with parameter perturbation |
| Predictor | Time-series forecasting (traffic/AQ) |
| Web Scraper | Real-time data fetch (weather, live feeds) |
| Vision | Process uploaded images (traffic cams, documents) |

### 4. Data & Memory Layer
- **Vector Store**: FAISS (GPU-accelerated on Spark) for embeddings
- **Structured Store**: DuckDB for analytical queries on CSVs/Parquet
- **Conversation Memory**: SQLite for chat history + context management
- **Data Catalog**: Metadata about all ingested datasets

### 5. Model Layer (NVIDIA Stack)
| Model | Use | Why Spark |
|-------|-----|-----------|
| NemoTron-8B/70B | Reasoning, planning, tool-calling | 128GB unified memory holds large models |
| NV-Embed-v2 | Text embeddings for RAG | GPU-accelerated embedding generation |
| NeVA / LLaVA-NeMo | Vision understanding | Local multimodal inference |

### 6. Observability
- Token usage tracking per request
- Hallucination detection (fact-check against source data)
- Response latency monitoring
- Context window utilization alerts
- Eval framework for response quality scoring

---

## Data Flow

```
Raw Data (CSV/Excel/API)
    │
    ▼
ETL Pipeline (pandas/RAPIDS cuDF)
    │
    ├──→ Structured Store (DuckDB/Parquet)
    │
    ├──→ Chunking + Embedding → Vector Store (FAISS)
    │
    └──→ Metadata → Data Catalog
```

## Network Architecture (SSH Constraint)

```
┌──────────────────┐         SSH Tunnel          ┌──────────────────┐
│  User's Laptop   │ ◄──────────────────────────► │   DGX Spark      │
│                  │    Port Forward:             │                  │
│  Browser         │    localhost:3000 → :3000    │  Backend (8000)  │
│  (React UI)      │    localhost:8000 → :8000    │  UI Server (3000)│
│                  │                              │  Models (local)  │
└──────────────────┘                              └──────────────────┘
```

Option B: Run everything on Spark, serve UI via SSH port-forward. Browser connects to `localhost:3000` which tunnels to Spark.
