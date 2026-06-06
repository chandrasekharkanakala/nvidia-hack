# nvidia-hack
Nvidia hackathon - 2026

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DGX Spark (Server)                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    WebSocket     ┌──────────────────────────────┐│
│  │   React UI   │◄───────────────►│   FastAPI (port 8000)         ││
│  │  (port 3000) │                  │   ├─ /ws (chat)              ││
│  │              │                  │   ├─ /api/sessions            ││
│  │  • Chat      │                  │   └─ /api/ingest             ││
│  │  • Charts    │                  └──────────┬───────────────────┘│
│  │  • History   │                             │                    │
│  └──────────────┘                             ▼                    │
│                                   ┌───────────────────────┐        │
│                                   │    Router / Agent      │        │
│                                   │  (intent detection)    │        │
│                                   └──────────┬────────────┘        │
│                                              │                     │
│                    ┌─────────────┬───────────┼───────────┬────────┐│
│                    ▼             ▼           ▼           ▼        ▼│
│            ┌───────────┐ ┌───────────┐ ┌─────────┐ ┌────────┐ ┌──┴──────┐│
│            │ SQL Tool  │ │ RAG Tool  │ │Visualize│ │  Web   │ │Analyzer ││
│            │ (DuckDB)  │ │ (FAISS)   │ │(matplot)│ │ Search │ │(stats)  ││
│            └─────┬─────┘ └─────┬─────┘ └────┬────┘ └────┬───┘ └────┬────┘│
│                  │             │             │           │          │     │
│                  ▼             ▼             ▼           ▼          ▼     │
│           ┌──────────────────────────────────────────────────────────┐   │
│           │              vLLM / NIM (LLM Inference)                   │   │
│           │              + NeMo Guardrails (safety)                   │   │
│           │              + NemoClaw (orchestration)                   │   │
│           └──────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │                      Data Layer                                   │    │
│  │  • data/raw/       → CSV, XLSX, JSON, PDF, images                │    │
│  │  • data/processed/ → cleaned parquet/DuckDB tables               │    │
│  │  • data/embeddings/→ FAISS vector index                          │    │
│  └──────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘

         SSH Tunnel: ssh -L 3000:localhost:3000 -L 8000:localhost:8000
```

## Quick Start

```bash
# On DGX Spark:
cd lucia
bash scripts/setup.sh    # Install all dependencies
bash scripts/ingest.sh   # Ingest data files
bash scripts/start.sh    # Start backend + UI
```

## Access (from laptop)

```bash
ssh -L 3000:localhost:3000 -L 8000:localhost:8000 user@dgx-spark
# Then open http://localhost:3000
```
