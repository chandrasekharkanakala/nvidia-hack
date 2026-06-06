# NVIDIA GitHub Repos, Playbooks & Blueprints — Reference Guide

> All repos below are directly relevant to our hackathon build. Organized by what we need them for.

---

## 🏗️ DGX Spark Playbooks (Primary Reference)

### Repository: [NVIDIA/dgx-spark-playbooks](https://github.com/NVIDIA/dgx-spark-playbooks)

Step-by-step guides specifically for DGX Spark (GB10). **Start here.**

| Playbook | What it covers | We use for |
|----------|---------------|-----------|
| `nvidia/nemotron/` | Running Nemotron 3 family on Spark | LLM setup (Nano/Super) |
| `nemotron-3-nano-with-llama.cpp/` | Nemotron Nano via llama.cpp | Fallback: lightweight model serving |
| `vllm-for-inference/` | vLLM optimized for GB10 Blackwell | Primary model serving engine |
| `sglang-for-inference/` | SGLang engine on Spark | Alternative to vLLM |
| `trt-llm-for-inference/` | TensorRT-LLM inference | Optimized serving (if time) |
| `rag-application-in-ai-workbench/` | End-to-end RAG on Spark | RAG pipeline reference |
| `open-webui/` | Chat UI connected to local models | Quick UI fallback |
| `connect-to-your-spark/` | SSH, networking, port-forward | Day-0 device access |
| `unsloth-on-dgx-spark/` | Efficient fine-tuning | Stretch: fine-tune on London data |
| `cli-coding-agent/` | Running coding agents locally | Agent pattern reference |

**Clone command:**
```bash
git clone https://github.com/NVIDIA/dgx-spark-playbooks.git
```

---

## 🤖 NemoClaw (Mandatory — Agent Security Runtime)

### Repository: [NVIDIA/NemoClaw](https://github.com/NVIDIA/NemoClaw)

Secure sandbox for running AI agents (wraps OpenClaw).

| Resource | URL |
|----------|-----|
| GitHub Repo | https://github.com/NVIDIA/NemoClaw |
| Official Docs | https://docs.nvidia.com/nemoclaw/user-guide/openclaw/home |
| Quick Start Guide | https://deepwiki.com/NVIDIA/NemoClaw/2.2-quick-start-guide |
| Setup walkthrough | https://www.scoutos.com/blog/nemoclaw-secure-agents |
| Local vLLM sandbox guide | https://codersera.com/blog/nvidia-nemoclaw-openclaw-secure-sandbox-guide-for-local-vllm-agents/ |
| Architecture deep-dive | https://betterstack.com/community/guides/ai/nvidia-nemoclaw/ |

**Install:**
```bash
curl -fsSL https://nvidia.com/nemoclaw.sh | bash
```

**Prerequisites:**
- Docker or Colima (container runtime)
- Node.js v22.16+ & npm v10+
- Linux kernel 5.13+ (DGX Spark has 6.17 ✅)
- API key for inference provider (local vLLM = no external key needed)

**Quick setup flow:**
```bash
# Install
curl -fsSL https://nvidia.com/nemoclaw.sh | bash

# Onboard agent
nemoclaw onboard
# → Name: lucia-agent
# → Provider: Local (vLLM)
# → Model: nemotron-3-nano
# → Policies: custom YAML

# Launch
nemoclaw launch lucia-agent

# Connect
nemoclaw connect lucia-agent
```

---

## 🧠 NeMo Agent Toolkit (Agent Orchestration Framework)

### Repository: [NVIDIA/NeMo-Agent-Toolkit](https://github.com/NVIDIA/NeMo-Agent-Toolkit)

Framework-agnostic agent orchestration. **Alternative/complement to NemoClaw for multi-agent workflows.**

| Resource | URL |
|----------|-----|
| GitHub Repo | https://github.com/NVIDIA/NeMo-Agent-Toolkit |
| UI Repo | https://github.com/NVIDIA/NeMo-Agent-Toolkit-UI |
| Docs | https://docs.nvidia.com/nemo/agent-toolkit/ |
| Releases/Changelog | https://github.com/NVIDIA/NeMo-Agent-Toolkit/releases |

**Key features we'd use:**
- Multi-agent orchestration (router → planner → executor)
- Framework agnostic (works with LangChain, LlamaIndex, custom Python)
- Agent Performance Primitives (parallel execution, speculative branching)
- Built-in observability & tracing
- MCP server publishing

**Install:**
```bash
pip install nemo-agent-toolkit
# or with specific plugins:
pip install nemo-agent-toolkit[langchain,evaluation]
```

**Python 3.12+ required.** Uses `uv` package manager.

---

## 📘 NVIDIA AI Blueprints (Reference Architectures)

### Organization: [NVIDIA-AI-Blueprints](https://github.com/NVIDIA-AI-Blueprints/)
### Catalog: [build.nvidia.com/blueprints](https://build.nvidia.com/blueprints)

Production-ready reference implementations. **Copy patterns, not code.**

| Blueprint Repo | What it is | Relevant to us |
|---------------|-----------|---------------|
| [rag](https://github.com/NVIDIA-AI-Blueprints/rag) | Foundational RAG pipeline (multi-modal, document-based) | ⭐ Core RAG architecture |
| [aiq](https://github.com/NVIDIA-AI-Blueprints/aiq) | AI agents connected to enterprise data | ⭐ Agent reasoning patterns |
| [llm-router](https://github.com/NVIDIA-AI-Blueprints/llm-router) | Route LLM requests to best model per task | Light/Deep agent mode routing |
| [retail-shopping-assistant](https://github.com/NVIDIA-AI-Blueprints/retail-shopping-assistant) | Multi-agent assistant (LangGraph, streaming, image search) | Multi-agent orchestration pattern |
| [video-search-and-summarization](https://github.com/NVIDIA-AI-Blueprints/video-search-and-summarization) | Vision + AI for video analytics | Vision model integration pattern |
| [pdf-to-podcast](https://github.com/NVIDIA-AI-Blueprints/pdf-to-podcast) | Document → audio pipeline | Voice output pattern |
| [cuFOLIO](https://github.com/NVIDIA-AI-Blueprints/cuFOLIO) | GPU-accelerated portfolio optimization | RAPIDS/cuDF usage pattern |
| [Retail-Catalog-Enrichment](https://github.com/NVIDIA-AI-Blueprints/Retail-Catalog-Enrichment) | GenAI-driven catalog enrichment | Data ingestion pattern |

**Most relevant for our build:**
```bash
# RAG Blueprint — core reference
git clone https://github.com/NVIDIA-AI-Blueprints/rag.git

# AIQ Blueprint — agent reasoning
git clone https://github.com/NVIDIA-AI-Blueprints/aiq.git

# LLM Router — light/deep mode
git clone https://github.com/NVIDIA-AI-Blueprints/llm-router.git
```

---

## 📚 GenerativeAIExamples (Comprehensive Examples)

### Repository: [NVIDIA/GenerativeAIExamples](https://github.com/NVIDIA/GenerativeAIExamples)

Broad collection of RAG, agent, and GenAI reference workflows.

| Example | Relevance |
|---------|-----------|
| `RAG/examples/basic_rag/langchain/` | Simple RAG pipeline starter |
| Multi-Agent Self-Corrective RAG | Self-healing agent pattern (reflector) |
| Knowledge Graph RAG | Graph-based reasoning over structured data |
| RAG Playground (Gradio) | Quick demo UI if React takes too long |

**Clone:**
```bash
git clone https://github.com/NVIDIA/GenerativeAIExamples.git
```

---

## 🛡️ NeMo Guardrails (Safety & Hallucination Control)

### Repository: [NVIDIA-NeMo/Guardrails](https://github.com/NVIDIA-NeMo/Guardrails)

Programmable guardrails for LLM-based systems.

| Resource | URL |
|----------|-----|
| GitHub Repo | https://github.com/NVIDIA-NeMo/Guardrails |
| Docs | https://docs.nvidia.com/nemo/guardrails/latest/index.html |
| Blueprint with NemoGuard NIMs | https://docs.nvidia.com/nemo/guardrails/0.19.0/user-guides/advanced/safeguarding-ai-virtual-assistant-blueprint.html |
| Tutorials | https://docs.nvidia.com/nemo/guardrails/tutorials.html |

**We use for:**
- Hallucination detection (fact-check against source data)
- Topic control (keep agent focused on urban operations)
- Jailbreak prevention
- Output validation rails

**Install:**
```bash
pip install nemoguardrails
```

---

## 🔧 Model Serving References

### vLLM on DGX Spark
| Resource | URL |
|----------|-----|
| DGX Spark Playbook | `dgx-spark-playbooks/vllm-for-inference/` |
| vLLM GitHub | https://github.com/vllm-project/vllm |
| vLLM + Nemotron Super guide | https://vllm-project.github.io/2026/03/11/nemotron-3-super.html |

**Serve Nemotron:**
```bash
# Nemotron 3 Nano via vLLM
vllm serve nvidia/nemotron-3-nano \
  --port 8001 \
  --gpu-memory-utilization 0.3 \
  --max-model-len 32768

# Nemotron 3 Super via vLLM (uses most of 128GB)
vllm serve nvidia/nemotron-3-super \
  --port 8001 \
  --gpu-memory-utilization 0.7 \
  --max-model-len 32768
```

### FAISS GPU
| Resource | URL |
|----------|-----|
| FAISS GitHub | https://github.com/facebookresearch/faiss |
| FAISS GPU Install | `pip install faiss-gpu` (CUDA 12+) |

---

## 📊 Data & Build Platform References

### NVIDIA RAPIDS (GPU-accelerated DataFrames)
| Resource | URL |
|----------|-----|
| RAPIDS GitHub | https://github.com/rapidsai |
| cuDF (GPU Pandas) | https://github.com/rapidsai/cudf |
| cuGraph (Graph Analytics) | https://github.com/rapidsai/cugraph |

**We might use for:**
- GPU-accelerated data loading of London transport CSVs
- Graph analytics on road network (cuGraph)
- Points in NVIDIA ecosystem scoring

### NVIDIA NIM (Inference Microservices)
| Resource | URL |
|----------|-----|
| NIM Catalog | https://build.nvidia.com/nim |
| NIM Docs | https://docs.nvidia.com/nim/ |

---

## 🗺️ How Repos Map to Our Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     LUCIA Architecture                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  PRESENTATION    → dgx-spark-playbooks/open-webui (fallback UI) │
│                  → NVIDIA-AI-Blueprints/retail-shopping-assistant│
│                    (React + streaming WebSocket pattern)          │
│                                                                   │
│  AGENT LAYER     → NVIDIA/NemoClaw (sandbox + security)         │
│                  → NVIDIA/NeMo-Agent-Toolkit (orchestration)    │
│                  → NVIDIA-AI-Blueprints/aiq (reasoning patterns)│
│                                                                   │
│  RAG/RETRIEVAL   → NVIDIA-AI-Blueprints/rag (RAG pipeline)     │
│                  → NVIDIA/GenerativeAIExamples (RAG examples)   │
│                  → dgx-spark-playbooks/rag-application-*/       │
│                                                                   │
│  MODEL SERVING   → dgx-spark-playbooks/vllm-for-inference/     │
│                  → dgx-spark-playbooks/nvidia/nemotron/         │
│                  → vllm-project/vllm                             │
│                                                                   │
│  GUARDRAILS      → NVIDIA-NeMo/Guardrails                       │
│                                                                   │
│  DATA PIPELINE   → rapidsai/cudf (GPU DataFrames)               │
│                  → NVIDIA-AI-Blueprints/cuFOLIO (RAPIDS pattern)│
│                                                                   │
│  VISION          → NVIDIA-AI-Blueprints/video-search-*          │
│                  → dgx-spark-playbooks (vision model playbook)  │
│                                                                   │
│  ROUTING         → NVIDIA-AI-Blueprints/llm-router              │
│                    (Light vs Deep agent mode)                     │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## ⚡ Priority Clone List (Hackathon Day-0)

Run these on DGX Spark immediately:

```bash
# 1. DGX Spark Playbooks (setup guides)
git clone https://github.com/NVIDIA/dgx-spark-playbooks.git

# 2. NemoClaw (agent runtime — mandatory)
git clone https://github.com/NVIDIA/NemoClaw.git

# 3. RAG Blueprint (RAG pipeline reference)
git clone https://github.com/NVIDIA-AI-Blueprints/rag.git

# 4. AIQ Blueprint (agent reasoning)
git clone https://github.com/NVIDIA-AI-Blueprints/aiq.git

# 5. NeMo Agent Toolkit (orchestration)
git clone https://github.com/NVIDIA/NeMo-Agent-Toolkit.git

# 6. NeMo Guardrails (safety)
git clone https://github.com/NVIDIA-NeMo/Guardrails.git

# 7. GenerativeAIExamples (broad reference)
git clone https://github.com/NVIDIA/GenerativeAIExamples.git
```

---

## 🔗 Quick Links Summary

| What | URL |
|------|-----|
| DGX Spark Playbooks | https://github.com/NVIDIA/dgx-spark-playbooks |
| NemoClaw | https://github.com/NVIDIA/NemoClaw |
| NeMo Agent Toolkit | https://github.com/NVIDIA/NeMo-Agent-Toolkit |
| NeMo Agent Toolkit UI | https://github.com/NVIDIA/NeMo-Agent-Toolkit-UI |
| AI Blueprints (org) | https://github.com/NVIDIA-AI-Blueprints/ |
| RAG Blueprint | https://github.com/NVIDIA-AI-Blueprints/rag |
| AIQ Blueprint | https://github.com/NVIDIA-AI-Blueprints/aiq |
| LLM Router Blueprint | https://github.com/NVIDIA-AI-Blueprints/llm-router |
| Retail Assistant Blueprint | https://github.com/NVIDIA-AI-Blueprints/retail-shopping-assistant |
| GenerativeAIExamples | https://github.com/NVIDIA/GenerativeAIExamples |
| NeMo Guardrails | https://github.com/NVIDIA-NeMo/Guardrails |
| RAPIDS cuDF | https://github.com/rapidsai/cudf |
| FAISS | https://github.com/facebookresearch/faiss |
| vLLM | https://github.com/vllm-project/vllm |
| NIM Catalog | https://build.nvidia.com/nim |
| Blueprints Catalog | https://build.nvidia.com/blueprints |
| NemoClaw Docs | https://docs.nvidia.com/nemoclaw/ |
| NeMo Guardrails Docs | https://docs.nvidia.com/nemo/guardrails/ |
| NeMo Agent Toolkit Docs | https://docs.nvidia.com/nemo/agent-toolkit/ |
