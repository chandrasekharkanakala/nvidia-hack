# NVIDIA Build Skills — What We Can Naturally Use

> Source: [build.nvidia.com/skills](https://build.nvidia.com/skills) + [github.com/NVIDIA/skills](https://github.com/NVIDIA/skills)

---

## What Are NVIDIA Skills?

Skills are **portable, reusable instruction sets** that teach AI agents how to use NVIDIA's CUDA-X libraries, NIMs, and platform tools. They're installable via CLI and can be plugged directly into NemoClaw/OpenClaw or NeMo Agent Toolkit agents.

```bash
# Install skills CLI
npx skills add nvidia/skills --list          # Browse catalog
npx skills add nvidia/skills --skill <name>  # Install specific skill
```

---

## Skills Directly Relevant to LUCIA (Urban Intelligence Agent)

### ⭐ Tier 1: Must-Use (High scoring, directly relevant)

| Skill / NIM | Category | What it Does | How LUCIA Uses It |
|-------------|----------|-------------|-------------------|
| **Nemotron 3 Nano** | LLM (NIM) | 30B-param reasoning, tool-calling, planning | Core agent brain (fast mode) |
| **Nemotron 3 Super** | LLM (NIM) | 120B-param deep reasoning | Core agent brain (deep mode) |
| **NV-EmbedQA (NV-Embed-v2)** | Embedding (NIM) | Text → dense vector embeddings | RAG: embed London datasets for search |
| **NeMo Retriever Reranker** | Reranker (NIM) | Score & reorder search results by relevance | RAG: improve retrieval precision |
| **Nemotron Speech ASR 0.6B** | Speech-to-Text (NIM) | Real-time audio → text (160ms latency) | Voice input for the agent |
| **Magpie TTS** | Text-to-Speech (NIM) | Text → natural speech audio (multilingual) | Agent speaks responses |
| **Nemotron 3.5 Content Safety** | Guardrails (NIM) | Detect unsafe/biased content | Output safety filter |
| **cuOpt Routing** | Optimization (Skill) | Vehicle routing, scheduling, TSP | Traffic rerouting simulation |
| **rag-blueprint** | RAG (Skill) | Full RAG pipeline deployment & config | Our RAG pipeline architecture |
| **NemoClaw Agent Skills** | Agent (Skill) | NemoClaw integration & orchestration | Agent runtime setup |

### 🟠 Tier 2: Should-Use (Strong differentiation)

| Skill / NIM | Category | What it Does | How LUCIA Uses It |
|-------------|----------|-------------|-------------------|
| **Earth2Studio** | Weather/Climate (Skill) | AI weather forecasting (FourCastNet, CorrDiff) | Predict weather impact on traffic/AQ |
| **cuDF** | Data Processing (Skill) | GPU-accelerated DataFrames | Fast ETL on London CSV data |
| **Nemotron Nano Omni (Vision)** | Multimodal (NIM) | Understand images + text + audio | Traffic camera image analysis |
| **Llama Nemotron Rerank VL 1B** | Vision Reranker (NIM) | Rerank results with image understanding | Multimodal RAG on planning docs |
| **cuOpt Numerical Optimization** | Optimization (Skill) | LP, MILP, QP solver | What-if optimization scenarios |
| **DeepStream** | Video Analytics (Skill) | Real-time video processing pipeline | Traffic camera feed analysis |

### 🟢 Tier 3: Nice-to-Have (Bonus points)

| Skill / NIM | Category | What it Does | How LUCIA Uses It |
|-------------|----------|-------------|-------------------|
| **cuGraph** | Graph Analytics (Skill) | GPU-accelerated graph processing | Road network graph analysis |
| **Cosmos3-Nano** | World Models (NIM) | Physical world simulation | Traffic flow simulation (stretch) |
| **DALI** | Data Loading (Skill) | Fast GPU data loading & augmentation | Accelerate data pipeline |
| **Holoscan SDK** | Sensor/Edge (Skill) | Real-time sensor data processing | IoT traffic sensor integration |

---

## NIM Models — Complete Catalog for Our Use Case

### LLMs (Text Generation)
| Model | Params | Context | Local/API | Our Use |
|-------|--------|---------|-----------|---------|
| `nvidia/nemotron-3-nano` | 30B (3.5B active) | 1M | Local on Spark ✅ | Light agent mode |
| `nvidia/nemotron-3-super` | 120B (12B active) | 1M | Local on Spark ✅ | Deep agent mode |
| `nvidia/nemotron-3-ultra` | 550B (55B active) | 1M | API only ❌ | Too large for Spark |

### Embeddings
| Model | Params | Dimensions | Local/API | Our Use |
|-------|--------|-----------|-----------|---------|
| `nvidia/nv-embedqa-mistral7b-v2` | 7.85B | 4096 | Local on Spark ✅ | Primary embedding model |
| `nvidia/llama-nemotron-embed-vl-1b` | 1B | 2048 | Local ✅ | Lightweight alt + vision embed |

### Rerankers
| Model | Params | Modality | Local/API | Our Use |
|-------|--------|----------|-----------|---------|
| `nvidia/nemo-retriever-reranker` | ~1B | Text | Local ✅ | RAG result reranking |
| `nvidia/llama-nemotron-rerank-vl-1b-v2` | 1B | Text + Image | Local ✅ | Multimodal reranking |

### Speech
| Model | Params | Latency | Local/API | Our Use |
|-------|--------|---------|-----------|---------|
| `nvidia/nemotron-speech-asr-0.6b` | 0.6B | ~160ms | Local ✅ | Voice input (STT) |
| `nvidia/magpie-tts` | 357M | Low | Local ✅ | Voice output (TTS) |

### Safety/Guardrails
| Model | Params | Capability | Local/API | Our Use |
|-------|--------|-----------|-----------|---------|
| `nvidia/nemotron-3.5-content-safety` | 4B | Content moderation (12 langs) | Local ✅ | Output safety |
| `nvidia/llama-nemotron-content-safety-8b` | 8B | Unsafe content + PII detection | Local ✅ | Deep safety check |

### Vision/Multimodal
| Model | Params | Modality | Local/API | Our Use |
|-------|--------|----------|-----------|---------|
| `nvidia/nemotron-nano-omni` | 30B | Text+Image+Audio+Video | Local ✅ | Traffic cam analysis |
| `nvidia/cosmos3-nano` | ~8B | Physical world model | Local ✅ | Traffic simulation |

---

## CUDA-X Agent Skills Deep Dive

### cuOpt (Route & Schedule Optimization)
```
Skill: cuopt-routing-api-python
Skill: cuopt-numerical-optimization-api-python
```

| Capability | Application to LUCIA |
|-----------|---------------------|
| Vehicle Routing Problem (VRP) | Optimal traffic rerouting during road closures |
| Travelling Salesman (TSP) | Shortest path calculations for citizen queries |
| Scheduling optimization | Optimal construction timing recommendations |
| Linear Programming (LP) | Resource allocation for city services |
| Mixed-Integer Programming (MILP) | Infrastructure investment decisions |

**Why this scores points**: cuOpt is a core NVIDIA CUDA-X library. Using it for traffic optimization is a natural, impressive demo.

**Example integration:**
```python
from cuopt import routing

# Agent tool: "What's the optimal diversion if we close London Bridge?"
solver = routing.Solver()
solver.set_network(london_road_graph)
solver.add_constraint(road_closure="London Bridge", duration_hrs=3)
result = solver.solve()
# → Returns optimal rerouting + estimated delays
```

---

### Earth2Studio (Weather Intelligence)
```
Skill: earth2studio
GitHub: https://github.com/NVIDIA/earth2studio
```

| Capability | Application to LUCIA |
|-----------|---------------------|
| AI weather forecasting (0-15 days) | Predict rain impact on traffic patterns |
| Nowcasting (0-6 hours, km-scale) | Real-time weather alerts for transport ops |
| Downscaling (high-res local) | Hyper-local weather for specific London roads |
| Climate pattern analysis | Historical correlation: weather ↔ incidents |

**Why this scores points**: Earth2Studio is cutting-edge NVIDIA AI. Combining weather predictions with traffic data creates non-obvious insights (exactly what judges want).

**Example integration:**
```python
from earth2studio.models import FourCastNet
from earth2studio.data import GFS

# Agent tool: "Will it rain near London Bridge at 5pm Friday?"
model = FourCastNet.load()
forecast = model.predict(
    location=(51.5074, -0.0878),  # London Bridge
    horizon_hours=72
)
# → Returns precipitation probability + intensity
```

---

### cuDF (GPU DataFrames)
```
Skill: cudf-dataframe
GitHub: https://github.com/rapidsai/cudf
```

| Capability | Application to LUCIA |
|-----------|---------------------|
| GPU-accelerated CSV/Parquet read | Fast ingestion of London transport data |
| Pandas-compatible API | Drop-in replacement for data processing |
| GPU joins, groupby, aggregations | Real-time analytics on large datasets |
| String/datetime operations | Parse timestamps from traffic sensors |

**Example:**
```python
import cudf

# 10x faster than pandas on Spark GPU
traffic_df = cudf.read_csv("london_traffic_2024.csv")
hourly_avg = traffic_df.groupby(['road', 'hour']).agg({'flow': 'mean'})
```

---

### DeepStream (Video Analytics)
```
Skill: deepstream-dev
Skill: deepstream-import-vision-model
```

| Capability | Application to LUCIA |
|-----------|---------------------|
| Real-time video stream processing | Analyze TfL traffic camera feeds |
| Object detection & tracking | Count vehicles, detect congestion |
| Custom model import | Use fine-tuned traffic models |
| Multi-stream parallel processing | Multiple camera feeds simultaneously |

---

## Memory Budget with All Skills Active

### Recommended Configuration (Skills-aware)

```
┌──────────────────────────────────────────────────────────────────┐
│           128GB Unified Memory — Skill-Aware Budget               │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│  CORE LLM                                                         │
│  ├── Nemotron 3 Nano (reasoning)              35 GB              │
│  │                                                                │
│  RETRIEVAL                                                        │
│  ├── NV-Embed-v2 (embeddings)                 16 GB              │
│  ├── NeMo Reranker (1B)                        2 GB              │
│  ├── FAISS GPU Index                           4 GB              │
│  │                                                                │
│  SPEECH                                                           │
│  ├── Nemotron ASR 0.6B (STT)                   2 GB              │
│  ├── Magpie TTS 357M                           1 GB              │
│  │                                                                │
│  SAFETY                                                           │
│  ├── Nemotron 3.5 Content Safety (4B)          8 GB              │
│  │                                                                │
│  DATA PROCESSING                                                  │
│  ├── DuckDB (structured queries)               5 GB              │
│  ├── cuDF buffers (if used)                    3 GB              │
│  │                                                                │
│  OPTIMIZATION (cuOpt - loaded on demand)                          │
│  ├── cuOpt solver runtime                      2 GB              │
│  │                                                                │
│  APPLICATION                                                      │
│  ├── NemoClaw runtime                          1 GB              │
│  ├── FastAPI + WebSocket                       0.5 GB            │
│  ├── Conversation memory (SQLite)              0.1 GB            │
│  │                                                                │
│  OS + OVERHEAD                                                    │
│  ├── Linux + drivers                           6 GB              │
│  │                                                                │
│  ═══════════════════════════════════════════                      │
│  TOTAL USED                                  ~85.6 GB            │
│  FREE                                        ~42.4 GB            │
│  (Available for: Vision model on-demand,                          │
│   Earth2Studio, larger context windows)                           │
│                                                                    │
└──────────────────────────────────────────────────────────────────┘
```

---

## Skill Integration Map → Architecture Boxes

```
┌─────────────────────────────────────────────────────────────────┐
│                LUCIA Architecture × NVIDIA Skills                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ PRESENTATION LAYER                                       │    │
│  │  Voice In  → nvidia/nemotron-speech-asr-0.6b            │    │
│  │  Voice Out → nvidia/magpie-tts                          │    │
│  │  Vision In → nvidia/nemotron-nano-omni (multimodal)     │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ AGENT ORCHESTRATOR                                       │    │
│  │  Brain     → nvidia/nemotron-3-nano (light mode)        │    │
│  │           → nvidia/nemotron-3-super (deep mode)         │    │
│  │  Runtime  → NemoClaw (sandbox + policy)                 │    │
│  │  Safety   → nvidia/nemotron-3.5-content-safety          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ TOOL LAYER (Agent Skills)                                │    │
│  │                                                          │    │
│  │  RAG Search   → nvidia/nv-embedqa + nemo-reranker       │    │
│  │               → rag-blueprint skill                     │    │
│  │                                                          │    │
│  │  SQL Query    → DuckDB (+ cudf skill for acceleration)  │    │
│  │                                                          │    │
│  │  Weather      → earth2studio skill (AI forecast)        │    │
│  │               → web_scraper (live data fallback)        │    │
│  │                                                          │    │
│  │  Simulator    → cuopt-routing-api-python skill          │    │
│  │               → cuopt-numerical-optimization skill      │    │
│  │                                                          │    │
│  │  Predictor    → earth2studio (weather prediction)       │    │
│  │               → custom time-series (traffic)            │    │
│  │                                                          │    │
│  │  Vision       → deepstream-dev skill                    │    │
│  │               → nvidia/nemotron-nano-omni               │    │
│  │                                                          │    │
│  │  Graph        → cuGraph skill (road network analysis)   │    │
│  │                                                          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ DATA LAYER                                               │    │
│  │  Ingestion → cudf skill (GPU-accelerated loading)       │    │
│  │  Vectors   → FAISS-GPU                                  │    │
│  │  Structured→ DuckDB (Parquet/CSV analytics)             │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Scoring Impact of Each Skill

| Skill Used | NVIDIA Stack Points | Innovation Points | Insight Quality | Total Impact |
|-----------|--------------------|--------------------|-----------------|-------------|
| Nemotron 3 (LLM) | ⭐⭐⭐ Core | - | - | Mandatory |
| NemoClaw (Agent) | ⭐⭐⭐ Core | - | - | Mandatory |
| NV-Embed + Reranker | ⭐⭐ Supporting | - | ⭐ Better retrieval | High |
| Nemotron ASR + Magpie TTS | ⭐⭐ Supporting | ⭐ Multimodal | - | High |
| cuOpt (routing/optimization) | ⭐⭐⭐ CUDA-X | ⭐⭐ Novel | ⭐⭐ Non-obvious insights | Very High |
| Earth2Studio (weather AI) | ⭐⭐⭐ CUDA-X | ⭐⭐⭐ Very novel | ⭐⭐⭐ Weather+traffic correlation | **Highest** |
| cuDF (GPU DataFrames) | ⭐⭐ RAPIDS | ⭐ Performance | - | Medium |
| Content Safety (Guardrails) | ⭐⭐ NIM | - | - | Medium |
| DeepStream (video) | ⭐⭐ CUDA-X | ⭐⭐ Novel | ⭐ Real-time vision | High |
| cuGraph (network) | ⭐⭐ RAPIDS | ⭐ Novel | ⭐ Graph insights | Medium |

---

## Recommended Skill Priority for 12-Hour Hackathon

### Phase 1 (Hours 0-5): Foundation
1. ✅ `nvidia/nemotron-3-nano` — Core LLM
2. ✅ `nvidia/nv-embedqa-mistral7b-v2` — Embeddings
3. ✅ `rag-blueprint` — RAG pipeline
4. ✅ `nemoclaw-user-agent-skills` — Agent runtime

### Phase 2 (Hours 5-9): Differentiation
5. ✅ `nvidia/nemotron-speech-asr-0.6b` — Voice input
6. ✅ `nvidia/magpie-tts` — Voice output
7. ✅ `cuopt-routing-api-python` — Traffic optimization
8. ✅ `nvidia/nemotron-3.5-content-safety` — Safety rails

### Phase 3 (Hours 9-12): Wow Factor
9. 🎯 `earth2studio` — AI weather forecasting (killer differentiator)
10. 🎯 `nvidia/nemotron-nano-omni` — Image understanding
11. 🎯 `cudf` — GPU data processing demo

---

## Quick Reference: All URLs

| Resource | URL |
|----------|-----|
| NVIDIA Skills Catalog (build.nvidia.com) | https://build.nvidia.com/skills |
| NVIDIA Skills GitHub | https://github.com/NVIDIA/skills |
| NVIDIA NIM Model Catalog | https://build.nvidia.com/nim |
| Earth2Studio GitHub | https://github.com/NVIDIA/earth2studio |
| cuOpt Developer Blog | https://developer.nvidia.com/blog/optimize-supply-chain-decision-systems-using-nvidia-cuopt-agent-skills/ |
| RAPIDS cuDF | https://github.com/rapidsai/cudf |
| RAPIDS cuGraph | https://github.com/rapidsai/cugraph |
| NeMo Retriever Embedding Docs | https://docs.nvidia.com/nim/nemo-retriever/text-embedding/latest/overview.html |
| NeMo Retriever Reranking Docs | https://docs.nvidia.com/nim/nemo-retriever/text-reranking/latest/overview.html |
| NeMo Guardrails Docs | https://docs.nvidia.com/nemo/guardrails/latest/index.html |
| Skills CLI Docs | https://docs.nvidia.com/skills/ |
