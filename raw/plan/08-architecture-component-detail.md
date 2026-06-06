# Architecture Component Detail — Tools, Software & Models per Box

---

## Master Architecture with Memory & Tech per Component

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    LUCIA — Component-Level Detail                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Layer 1: Presentation Layer

### Box 1.1: Web Chat UI
| Attribute | Detail |
|-----------|--------|
| Software | React 18+ , Vite 5+, TailwindCSS 3 |
| Libraries | @tanstack/react-query, react-markdown, lucide-react, leaflet (maps) |
| Connection | WebSocket to backend (streaming tokens) |
| Memory (on Spark) | ~50MB (Node.js dev server) |
| Runs on | DGX Spark (served via port-forward to user's browser) |

### Box 1.2: Voice I/O
| Attribute | Detail |
|-----------|--------|
| STT Software | OpenAI Whisper (whisper-large-v3) |
| STT Model Size | ~3GB (FP16) |
| STT Memory | ~4GB loaded |
| TTS Software | ElevenLabs API (cloud) |
| TTS Memory | Negligible (API call, no local model) |
| Audio Format | WebM/Opus (browser) → WAV (Whisper) |
| Latency Target | STT: <1s, TTS: <2s |

### Box 1.3: REST API
| Attribute | Detail |
|-----------|--------|
| Software | FastAPI 0.100+, uvicorn, pydantic v2 |
| Protocol | REST (JSON) + WebSocket (streaming) |
| Memory | ~100MB (Python process) |
| Endpoints | /chat, /voice, /health, /metrics |

---

## Layer 2: API Gateway / Session Manager

| Attribute | Detail |
|-----------|--------|
| Software | FastAPI (same process as REST API) |
| Session Store | SQLite (file-based, zero-config) |
| Auth | None for hackathon (single-user demo) |
| Rate Limiting | None for hackathon |
| Memory | Included in API process (~100MB) |
| Responsibilities | Route requests, manage chat sessions, WebSocket lifecycle |

---

## Layer 3: Agent Orchestrator (NemoClaw + OpenClaw)

### Box 3.1: Router (Intent Classifier)
| Attribute | Detail |
|-----------|--------|
| Software | NemoClaw policy engine + NemoTron (few-shot classification) |
| Model Used | Nemotron 3 Nano (fast classification) |
| Memory | Shared with main LLM (no extra) |
| Input | User message + conversation history |
| Output | Intent label: `insight` / `predict` / `simulate` / `recommend` / `simple_qa` |
| Latency Target | <500ms |

### Box 3.2: Planner (Query Decomposer)
| Attribute | Detail |
|-----------|--------|
| Software | OpenClaw planner module (NemoClaw-wrapped) |
| Model Used | Nemotron 3 (Nano or Super depending on mode) |
| Memory | Shared with main LLM |
| Input | User query + intent + available tools manifest |
| Output | Ordered list of tool calls with parameters |
| Example | "Get weather → Get traffic → Correlate → Generate insight" |

### Box 3.3: Executor (Tool Runner)
| Attribute | Detail |
|-----------|--------|
| Software | NemoClaw OpenShell sandbox |
| Model Used | None (executes tool code) |
| Memory | ~500MB overhead for sandbox runtime |
| Input | Tool call sequence from Planner |
| Output | Tool results (JSON) |
| Security | Sandboxed filesystem, network allow-list, seccomp |

### Box 3.4: Reflector (Output Validator)
| Attribute | Detail |
|-----------|--------|
| Software | Custom Python module + NemoTron |
| Model Used | Nemotron 3 Nano (quick validation pass) |
| Memory | Shared with main LLM |
| Input | Generated response + source data used |
| Output | Confidence score + hallucination flags |
| Checks | Factual grounding, source citation, logical consistency |

---

## Layer 4: Tool Layer

### Box 4.1: RAG Search (Vector Retrieval)
| Attribute | Detail |
|-----------|--------|
| Software | FAISS (faiss-gpu) |
| Model for Embeddings | NV-Embed-v2 (7.85B params) |
| Index Type | IVF-Flat or HNSW (GPU-accelerated) |
| Memory (Index) | ~4GB (for ~2M vectors × 4096 dim, FP16) |
| Memory (Embedding Model) | ~16-25GB |
| Input | Text query |
| Output | Top-K relevant chunks with metadata + scores |
| Latency Target | <200ms for top-10 retrieval |

### Box 4.2: SQL Query (Analytical)
| Attribute | Detail |
|-----------|--------|
| Software | DuckDB 0.10+ (in-process) |
| Storage Format | Parquet files (columnar, compressed) |
| Memory | ~3-5GB (loaded tables) |
| Input | Natural language → NemoTron generates SQL → DuckDB executes |
| Output | Query results (JSON/DataFrame) |
| Data Size | ~500MB-2GB raw CSV → ~200MB Parquet |
| Capabilities | Aggregations, joins, window functions, time-series |

### Box 4.3: Web Scraper (Real-time Data)
| Attribute | Detail |
|-----------|--------|
| Software | aiohttp + BeautifulSoup4 |
| Model Used | None |
| Memory | ~50MB |
| Input | URL + extraction schema |
| Output | Structured data (JSON) |
| Sources | Weather APIs, TfL live feeds, london.gov.uk |
| Network | Allowed through NemoClaw policy (specific domains only) |

### Box 4.4: Simulator (What-If Engine)
| Attribute | Detail |
|-----------|--------|
| Software | Custom Python (NumPy + NetworkX) |
| Model Used | None (statistical/graph-based) |
| Memory | ~1-2GB (city road network graph) |
| Input | Scenario parameters (e.g., "close road X for Y hours") |
| Output | Predicted impact metrics (delay, rerouting, affected areas) |
| Method | Graph-based traffic redistribution + historical pattern matching |

### Box 4.5: Predictor (Time-Series Forecasting)
| Attribute | Detail |
|-----------|--------|
| Software | statsmodels or Prophet (lightweight) |
| Model Used | ARIMA/Prophet (statistical, not DL) |
| Memory | ~200MB |
| Input | Time-series data + forecast horizon |
| Output | Predictions with confidence intervals |
| Use Case | "Predict traffic on London Bridge next Friday 5pm" |

### Box 4.6: Vision (Image Understanding)
| Attribute | Detail |
|-----------|--------|
| Software | Transformers (HuggingFace) or NeMo Multimodal |
| Model Used | NeVA or LLaVA-NeMo (~7B-13B params) |
| Memory | ~10-15GB (FP16) |
| Input | Image (traffic camera, planning document) |
| Output | Description, object counts, anomaly detection |
| Note | Only loaded on-demand (memory constraint with Super model) |

### Box 4.7: Calculator
| Attribute | Detail |
|-----------|--------|
| Software | Python (NumPy, SciPy) |
| Memory | Negligible |
| Input | Mathematical expression or statistical operation |
| Output | Numerical result |

---

## Layer 5: Data & Memory Layer

### Box 5.1: Vector Store
| Attribute | Detail |
|-----------|--------|
| Software | FAISS (faiss-gpu 1.7+) |
| Storage | Disk-backed with GPU-resident index |
| Memory | ~4GB (index) + NV-Embed model separately |
| Vectors | ~2M chunks (from all datasets) |
| Dimensions | 4096 (NV-Embed-v2 output) |
| Persistence | Serialized to `/data/embeddings/` |

### Box 5.2: Structured Store
| Attribute | Detail |
|-----------|--------|
| Software | DuckDB 0.10+ |
| Storage | Parquet files on disk, memory-mapped |
| Memory | ~3-5GB (active query buffers) |
| Tables | traffic_flow, air_quality, planning_apps, collisions, events |
| Query Interface | SQL (generated by NemoTron via tool) |

### Box 5.3: Conversation Memory
| Attribute | Detail |
|-----------|--------|
| Software | SQLite 3 |
| Memory | ~100MB |
| Schema | sessions, messages, tool_calls, evaluations |
| Retention | Full session history (for demo) |
| Context Window | Last N messages + summarized older context |

---

## Layer 6: Model Layer

### Box 6.1: NemoTron (LLM — Reasoning)
| Attribute | Detail |
|-----------|--------|
| Software | vLLM 0.5+ or NVIDIA NIM |
| Model | Nemotron 3 Nano (30B/3.5B active) — primary |
| Model Alt | Nemotron 3 Super (120B/12B active) — deep mode |
| Memory (Nano) | ~35GB |
| Memory (Super) | ~87GB |
| Context | 1M tokens max (practically use 32K-128K) |
| Serving | OpenAI-compatible API on :8001 |
| Quantization | FP16 (default), FP8 if memory-constrained |
| Key Capabilities | Tool calling, reasoning, planning, code generation |

### Box 6.2: Embedding Model
| Attribute | Detail |
|-----------|--------|
| Software | Custom serve script or TEI (Text Embedding Inference) |
| Model | NV-Embed-v2 (7.85B params, Mistral-7B base) |
| Memory | ~16-25GB (FP16) |
| Output Dim | 4096 |
| Max Seq Length | 32,768 tokens |
| Serving | REST API on :8002 |
| Throughput | ~100-500 embeddings/sec (batched) |

### Box 6.3: Vision Model (Optional)
| Attribute | Detail |
|-----------|--------|
| Software | Transformers or NeMo Multimodal |
| Model | NeVA-7B or LLaVA-NeMo |
| Memory | ~10-15GB |
| Capability | Image captioning, VQA, object detection |
| Serving | Loaded on-demand (memory management) |
| Note | Cannot coexist with Nemotron Super — use with Nano only |

---

## Layer 7: Observability Layer

| Attribute | Detail |
|-----------|--------|
| Software | structlog (Python), custom metrics module |
| Storage | SQLite (metrics table) + JSON logs |
| Memory | ~50MB |
| Metrics Tracked | |
| | - Token usage per request (prompt + completion) |
| | - Latency per stage (routing, planning, tool exec, generation) |
| | - Hallucination score per response |
| | - Context window utilization (%) |
| | - Tool call success/failure rates |
| | - User satisfaction (thumbs up/down in UI) |
| Display | MetricsPanel component in React UI |

---

## Total Memory Budget Summary

### Configuration A: Nemotron Nano + Vision (Recommended for Hackathon)

| Component | Memory |
|-----------|--------|
| Nemotron 3 Nano (FP16) | 35 GB |
| NV-Embed-v2 (FP16) | 20 GB |
| Whisper Large v3 | 4 GB |
| FAISS GPU Index | 4 GB |
| DuckDB | 5 GB |
| Vision Model (on-demand) | 12 GB |
| Application Stack | 2 GB |
| OS + Overhead | 6 GB |
| **TOTAL** | **88 GB** |
| **Free** | **40 GB** |

### Configuration B: Nemotron Super (Maximum Quality)

| Component | Memory |
|-----------|--------|
| Nemotron 3 Super (FP16) | 87 GB |
| NV-Embed-v2 (FP16) | 20 GB |
| Whisper Large v3 | 4 GB |
| FAISS GPU Index | 4 GB |
| DuckDB | 3 GB |
| Application Stack | 2 GB |
| OS + Overhead | 6 GB |
| **TOTAL** | **126 GB** |
| **Free** | **2 GB** ⚠️ |

> **Recommendation**: Start with Config A (Nano). If stable and demo goes well, attempt Config B (Super) for "Deep Mode" demo only.

---

## Port Map

| Service | Port | Protocol |
|---------|------|----------|
| React UI | 3000 | HTTP |
| FastAPI Backend | 8000 | HTTP + WS |
| NemoTron (vLLM) | 8001 | HTTP (OpenAI compat) |
| NV-Embed-v2 | 8002 | HTTP |
| NemoClaw Agent | 8080 | HTTP |
| Whisper STT | 8003 | HTTP |

All accessible via SSH port-forward from user's laptop.
