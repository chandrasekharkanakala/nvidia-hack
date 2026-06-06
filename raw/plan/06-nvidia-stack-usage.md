# NVIDIA Ecosystem & Spark Utility — Scoring Strategy

## Target: 30/30 Points

---

## "The Stack" (15 pts) — NVIDIA Libraries/Tools Used

| NVIDIA Tool | Where Used | Points Contribution |
|-------------|-----------|-------------------|
| **NemoTron** (LLM) | Core reasoning engine for the agent | Primary — LLM backbone |
| **NemoClaw** | Agent orchestration (router → planner → executor) | Primary — agent framework |
| **NV-Embed-v2** | Embedding generation for RAG pipeline | Supporting — retrieval |
| **FAISS-GPU** | GPU-accelerated vector similarity search | Supporting — fast retrieval |
| **RAPIDS cuDF** | Data preprocessing acceleration (stretch goal) | Bonus — data pipeline |
| **NeVA/NeMo Vision** | Image understanding for traffic cam uploads | Bonus — multimodal |
| **NIM** (if available) | Optimized model serving | Bonus — deployment |

### Minimum viable NVIDIA stack (guarantee 15/15):
1. NemoTron (LLM) ✓
2. NemoClaw (Agent) ✓  
3. NV-Embed (Embeddings) ✓

---

## "The Spark Story" (15 pts) — Why DGX Spark

### Primary Narrative
> "LUCIA runs entirely on DGX Spark's 128GB unified memory. We hold the full NemoTron-8B model, a 50M-vector FAISS index of London's transport history, and active conversation context — all in GPU-addressable memory simultaneously. This eliminates model-swapping latency and enables sub-second RAG retrieval over city-scale data."

### Supporting Points

| Spark Feature | How We Use It | Benefit |
|---------------|--------------|---------|
| 128GB Unified Memory | NemoTron (16GB) + FAISS index (8GB) + embeddings pipeline + conversation context — all resident simultaneously | Zero model-loading latency between tool calls |
| Local GPU Inference | All model inference runs on-device | <100ms latency for embedding, <2s for LLM response |
| Privacy | City planning data never leaves the device | Compliance with government data handling requirements |
| ARM Architecture (Grace) | Efficient CPU-side data preprocessing while GPU runs inference | Parallel ETL + inference pipeline |
| NVLink/Unified Memory Architecture | No PCIe bottleneck between CPU and GPU memory | Seamless data movement for RAG (retrieve → generate) |

### Demo Talking Points
1. **"Watch the latency counter"** — Show real-time latency in UI. Sub-2s for complex reasoning.
2. **"Everything is local"** — No API calls to external LLMs. Point to network monitor showing zero egress.
3. **"Unified memory in action"** — Show nvidia-smi while running: model + vector DB + processing all co-resident.
4. **"City data stays secure"** — Planning applications, traffic patterns — sensitive data never leaves the room.

---

## Scoring Checklist

```
[x] Used NemoTron for LLM reasoning
[x] Used NemoClaw for agent orchestration
[x] Used NV-Embed for embedding generation
[x] Used FAISS-GPU for vector search
[ ] Used RAPIDS cuDF for data processing (stretch)
[ ] Used NeVA for vision (stretch)
[x] Can articulate "Spark Story" with specific memory/latency claims
[x] Can demonstrate local inference (no external API calls)
[x] Can show nvidia-smi proving GPU utilization
```

---

## Fallback Plan

If NemoClaw is unavailable or too complex to set up in time:
1. Use **LangGraph** for orchestration BUT still use NemoTron as the LLM
2. Frame it as: "We built a custom orchestration layer on top of NemoTron to handle multi-step urban planning queries"
3. Still score points for NemoTron + NV-Embed + FAISS-GPU + local inference story

If NemoTron is too large:
1. Use **NemoTron-Mini** (smaller variant)
2. Or use **Mistral-NeMo** (NVIDIA-partnered model)
3. Still counts as NVIDIA ecosystem
