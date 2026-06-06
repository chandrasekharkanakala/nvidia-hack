# NemoTron & NemoClaw — Detailed Specification

---

## 1. NemoTron Model Selection for DGX Spark

### DGX Spark Hardware Constraints
| Spec | Value |
|------|-------|
| Unified Memory | 128GB LPDDR5X (shared CPU+GPU, coherent) |
| Memory Bandwidth | 273 GB/s |
| GPU | Blackwell (6144 CUDA cores, 384 Tensor Cores 5th Gen, 48 SMs) |
| FP4 Compute | 1 PetaFLOP (1000 TOPS) |
| Max Model (FP4) | ~200B parameters |
| Max Model (FP16) | ~70B parameters |
| NVLink-C2C | Zero-copy CPU↔GPU memory access |

### Available NemoTron 3 Models

| Model | Total Params | Active Params (MoE) | Memory Needed | Context Window | Fits DGX Spark? |
|-------|-------------|---------------------|---------------|----------------|-----------------|
| **Nemotron 3 Nano** | 30B | 3-3.5B | 25-40GB (FP16) | 1M tokens | ✅ YES — Comfortably |
| **Nemotron 3 Super** | 120B | 12B | ~87GB (FP16) | 1M tokens | ✅ YES — Tight but works |
| **Nemotron 3 Ultra** | 550B | 55B | 350-500GB | 1M tokens | ❌ NO — Multi-GPU required |

### Recommended: **Nemotron 3 Super** (Primary) + **Nemotron 3 Nano** (Fast mode)

**Why Super for Primary (Deep Agent):**
- 120B total / 12B active — fits in 128GB unified memory (~87GB model weight)
- Leaves ~40GB for FAISS index, embeddings, conversation context, OS
- Hybrid Mamba-2 + Transformer architecture = fast inference with quality reasoning
- 1M token context = can hold entire datasets in context if needed
- Tool-calling capability built in

**Why Nano for Secondary (Light Agent):**
- 30B total / 3-3.5B active — only 25-40GB memory
- Extremely fast (low-latency for simple queries)
- Leaves 80-100GB for everything else
- Perfect for the "Light Agent" mode in UI

### Memory Budget (with Nemotron 3 Super)

```
┌─────────────────────────────────────────────────┐
│         128GB Unified Memory Budget              │
├─────────────────────────────────────────────────┤
│                                                   │
│  Nemotron 3 Super (FP16)         ~87 GB          │
│  ─────────────────────────────────────           │
│  NV-Embed-v2 (FP16)             ~16 GB          │
│  ─────────────────────────────────────           │
│  FAISS Index (City data)          ~4 GB          │
│  ─────────────────────────────────────           │
│  DuckDB (in-memory tables)        ~3 GB          │
│  ─────────────────────────────────────           │
│  Conversation Memory + Context    ~2 GB          │
│  ─────────────────────────────────────           │
│  Application + OS Overhead        ~8 GB          │
│  ─────────────────────────────────────           │
│  Safety Buffer                    ~8 GB          │
│  ─────────────────────────────────────           │
│  TOTAL                          ~128 GB          │
└─────────────────────────────────────────────────┘
```

> ⚠️ **TIGHT FIT** — Super + NV-Embed-v2 together consumes ~103GB. This works but leaves little headroom.

### Alternative Memory Budget (Conservative — Nano + NV-Embed)

```
┌─────────────────────────────────────────────────┐
│         128GB Unified Memory (Conservative)      │
├─────────────────────────────────────────────────┤
│                                                   │
│  Nemotron 3 Nano (FP16)          ~35 GB          │
│  ─────────────────────────────────────           │
│  NV-Embed-v2 (FP16)             ~16 GB          │
│  ─────────────────────────────────────           │
│  FAISS Index (City data)          ~4 GB          │
│  ─────────────────────────────────────           │
│  DuckDB (in-memory tables)        ~5 GB          │
│  ─────────────────────────────────────           │
│  Conversation Memory + Context    ~4 GB          │
│  ─────────────────────────────────────           │
│  Vision Model (optional)         ~10 GB          │
│  ─────────────────────────────────────           │
│  Application + OS Overhead        ~8 GB          │
│  ─────────────────────────────────────           │
│  Safety Buffer                   ~46 GB          │
│  ─────────────────────────────────────           │
│  TOTAL                          ~128 GB          │
└─────────────────────────────────────────────────┘
```

> ✅ **SAFE** — Nano leaves 46GB headroom for vision model, larger datasets, and breathing room.

### Decision Matrix

| Scenario | Use Model | Rationale |
|----------|-----------|-----------|
| Demo is stable, memory verified early | Nemotron 3 Super | Maximum quality, impressive "Spark Story" |
| Memory pressure, need vision model too | Nemotron 3 Nano | Safe fit, still powerful with 3.5B active |
| Both modes needed simultaneously | Load Nano; swap to Super for Deep queries | Dynamic loading via NIM |

---

## 2. NemoClaw — Mandatory Agent Framework

### What NemoClaw IS
NemoClaw is **NOT** an orchestration framework like LangChain/LangGraph. It is:
- A **security wrapper + runtime** around OpenClaw (the open-source AI agent)
- Provides **sandboxed execution** for agent tool calls
- Enforces **policy-based access control** (which tools, which data, which models)
- Runs inside **OpenShell** (NVIDIA's hardened container runtime)

### NemoClaw Architecture

```
┌───────────────────────────────────────────────────────────┐
│                     NemoClaw Runtime                        │
├───────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │                   OpenClaw Agent                      │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │  │
│  │  │  Planner │  │ Tool     │  │ Memory Manager   │  │  │
│  │  │  (LLM    │  │ Executor │  │ (Conversation +  │  │  │
│  │  │  driven) │  │          │  │  Working Memory) │  │  │
│  │  └──────────┘  └──────────┘  └──────────────────┘  │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │              OpenShell (Sandbox Layer)                │  │
│  │  • Filesystem: /sandbox + /tmp only                  │  │
│  │  • Network: Deny-by-default, allow-list only         │  │
│  │  • Process: seccomp + Landlock isolation              │  │
│  │  • Inference: Policy-routed model access             │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │              Policy Engine (YAML-driven)              │  │
│  │  • Tool permissions (which tools agent can call)     │  │
│  │  • Data access (which datasets are visible)          │  │
│  │  • Model routing (local NemoTron vs fallback)        │  │
│  │  • Audit logging (every action recorded)             │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
└───────────────────────────────────────────────────────────┘
```

### NemoClaw Setup on DGX Spark

```bash
# 1. Install NemoClaw (single command)
curl -fsSL https://nvidia.com/nemoclaw.sh | bash

# 2. Configure agent policy (YAML)
cat > agent-policy.yaml << EOF
agent:
  name: lucia-urban-agent
  model: nemotron-3-super  # or nemotron-3-nano
  
permissions:
  filesystem:
    read: ["/sandbox/data/*"]
    write: ["/sandbox/output/*", "/tmp/*"]
  network:
    allow:
      - "api.openweathermap.org"      # Weather data
      - "data.london.gov.uk"          # City open data
      - "api.elevenlabs.io"           # Voice TTS
    deny: ["*"]                        # Everything else blocked
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
    model: nemotron-3-super
    endpoint: local
  fallback:
    model: nemotron-3-nano
    endpoint: local
  embedding:
    model: nv-embed-v2
    endpoint: local

audit:
  log_level: full
  retention: 7d
EOF

# 3. Start the agent runtime
nemoclaw start --policy agent-policy.yaml --port 8080
```

### NemoClaw Requirements
| Requirement | Spec |
|-------------|------|
| OS | Ubuntu 22.04+ (DGX Spark runs Ubuntu-based) |
| Kernel | 5.13+ (for Landlock — DGX Spark has 6.17) ✅ |
| RAM | 8GB+ (we have 128GB) ✅ |
| CPU | 4+ cores (we have 20) ✅ |
| Docker/Podman | Container runtime for OpenShell |
| Python | 3.10+ |

### How Tool Calling Works in NemoClaw

```
User Query: "What happens to traffic on London Bridge when it rains?"
                    │
                    ▼
┌──────────────────────────────────────────────┐
│  1. PLANNER (NemoTron reasoning)              │
│     Decomposes into steps:                    │
│     a) Get historical weather data            │
│     b) Get traffic data for London Bridge     │
│     c) Correlate rain events with traffic     │
│     d) Generate insight                       │
└──────────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────┐
│  2. TOOL EXECUTOR (Policy-checked)            │
│     Step a) → web_scraper tool (weather API)  │
│       └─ Policy check: network allow ✅        │
│     Step b) → sql_query tool (DuckDB)         │
│       └─ Policy check: filesystem read ✅      │
│     Step c) → calculator tool (correlation)   │
│       └─ Policy check: process allowed ✅      │
└──────────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────┐
│  3. RESPONSE GENERATOR (NemoTron)             │
│     Synthesizes tool outputs into insight     │
│     With source citations                     │
└──────────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────┐
│  4. AUDIT LOG                                 │
│     Every tool call, model inference,         │
│     and data access recorded                  │
└──────────────────────────────────────────────┘
```

---

## 3. NV-Embed-v2 — Embedding Model

| Spec | Value |
|------|-------|
| Base Architecture | Mistral-7B-v0.1 |
| Parameters | ~7.85B |
| Memory (FP16) | ~16-25GB |
| Memory (INT8) | ~8GB |
| Embedding Dimension | 4096 |
| Max Sequence Length | 32,768 tokens |
| Use | Generate embeddings for RAG vector search |

### Why NV-Embed-v2 over alternatives
- NVIDIA ecosystem points ✅
- GPU-accelerated on Spark ✅
- State-of-art retrieval quality (MTEB #1 at launch)
- High dimensionality (4096) = better semantic discrimination
- Fits alongside NemoTron in unified memory

---

## 4. Model Loading Strategy

### Option A: All-at-once (if using Nano)
```
Boot → Load NV-Embed-v2 (16GB) → Load Nemotron Nano (35GB) → Ready
Total: ~51GB resident, ~77GB free
Time to ready: ~2-3 minutes
```

### Option B: Dynamic swap (if using Super)
```
Boot → Load NV-Embed-v2 (16GB) → Load Nemotron Super (87GB) → Ready
Total: ~103GB resident, ~25GB free
Time to ready: ~4-5 minutes
⚠️ No room for vision model simultaneously
```

### Option C: Tiered loading (Recommended for hackathon)
```
Boot → Load NV-Embed-v2 (16GB) → Load Nemotron Nano (35GB)
     → [On "Deep Mode" request] → Swap to Super (if memory permits)
     → [On image upload] → Load vision model temporarily
Total: Dynamic, peaks at ~103GB
```

---

## 5. Serving Stack

| Component | How Served | Port |
|-----------|-----------|------|
| NemoTron (LLM) | vLLM or NIM container | :8001 |
| NV-Embed-v2 | TEI (Text Embedding Inference) or custom | :8002 |
| NemoClaw Agent | OpenShell container | :8080 |
| FastAPI Backend | uvicorn | :8000 |
| React UI | Vite dev server / nginx | :3000 |

### Startup Sequence
```bash
# 1. Start model serving
vllm serve nvidia/nemotron-3-nano --port 8001 --gpu-memory-utilization 0.3

# 2. Start embedding service
python -m src.models.embed_server --model nv-embed-v2 --port 8002

# 3. Start NemoClaw agent runtime
nemoclaw start --policy agent-policy.yaml --port 8080

# 4. Start FastAPI backend
uvicorn src.api.main:app --host 0.0.0.0 --port 8000

# 5. Start UI
cd ui && npm run dev -- --port 3000 --host 0.0.0.0
```
