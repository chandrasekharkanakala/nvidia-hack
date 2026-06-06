# LUCIA — London Urban City Intelligence Agent

> An agentic AI system that runs entirely on NVIDIA DGX Spark. Ask questions about London's traffic, air quality, planning, and city operations — get non-obvious insights, simulations, and predictions.

---

## Quick Start (DGX Spark)

```bash
# 1. Clone and enter
git clone <repo-url> lucia && cd lucia

# 2. Copy environment config (EDIT THIS with your ElevenLabs key)
cp .env.example .env
nano .env    # Set LUCIA_ELEVENLABS_API_KEY=sk_your_key_here

# 3. Setup (installs everything — idempotent, safe to re-run)
bash scripts/setup.sh

# 4. Download London datasets (~24 files from data.london.gov.uk)
bash scripts/download_data.sh

# 5. Ingest data (loads into DuckDB + builds FAISS vector index)
python scripts/ingest.py

# 6. Start all services
bash scripts/start.sh

# 7. Open in browser (via SSH port-forward)
# From your laptop:
ssh -L 3000:localhost:3000 -L 8000:localhost:8000 user@dgx-spark
# Then open: http://localhost:3000
```

---

## What You Can Ask

| Mode | Example | Response Time |
|------|---------|---------------|
| ⚡ Light | "Traffic on London Bridge right now?" | < 2s |
| ⚡ Light | "Air quality in Westminster?" | < 2s |
| 🧠 Deep | "What happens to traffic when it rains on a Friday?" | 5-15s |
| 🧠 Deep | "If I close Threadneedle St for 3 weeks, what's the impact?" | 5-15s |
| 🧠 Deep | "Predict congestion next Monday given rain forecast" | 5-15s |
| 📷 Image | Upload traffic camera → "Is this normal for 3pm?" | < 5s |
| 🎤 Voice | Hold mic button → speak → get spoken response | < 4s |

---

## Architecture

```
User (Browser) ←→ React UI (:3000)
                      ↕
              FastAPI Backend (:8000)
                      ↕
            NeMo Guardrails (PII, Safety, Topic)
                      ↕
            NemoClaw Agent Sandbox (:8080)
              ↕           ↕           ↕
     ┌────────┴──┐  ┌────┴────┐  ┌───┴───┐
     │ RAG Search │  │SQL Query│  │Simulate│  ...
     │ (FAISS GPU)│  │(DuckDB) │  │(Graph) │
     └────────────┘  └─────────┘  └────────┘
                      ↕
           Models (all local on DGX Spark)
     ┌──────────────────────────────────────┐
     │ NemoTron Nano (35GB) — reasoning     │
     │ Content Safety 4B (8GB) — guardrails │
     │ NV-Embed-v2 (20GB) — embeddings     │
     │ NeVA-7B (12GB) — vision             │
     └──────────────────────────────────────┘
```

---

## Services & Ports

| Port | Service | Purpose |
|------|---------|---------|
| 3000 | React UI | Chat interface |
| 8000 | FastAPI | REST + WebSocket API |
| 8001 | vLLM | NemoTron Nano + Content Safety |
| 8002 | vLLM | NV-Embed-v2 (embeddings) |
| 8003 | vLLM | NeVA-7B (vision) |
| 8080 | NemoClaw | Agent sandbox runtime |

---

## Configuration

**All secrets and config live in `.env`** (copied from `.env.example`):

| Variable | Purpose | Required |
|----------|---------|----------|
| `LUCIA_ELEVENLABS_API_KEY` | Voice STT + TTS | Yes (for voice) |
| `LUCIA_ELEVENLABS_VOICE_ID` | TTS voice selection | No (has default) |
| `LUCIA_VLLM_BASE_URL` | LLM endpoint | No (default localhost:8001) |
| `LUCIA_TFL_APP_KEY` | TfL live data | No (free tier works) |
| `LUCIA_OPENWEATHER_API_KEY` | Weather data | No (optional) |

**NemoClaw policy** (permissions for agent sandbox):
```
config/nemoclaw/agent-policy.yaml
```
Currently open (any-to-any). Edit `permissions.network.allow` and `permissions.filesystem.read/write` to restrict before demo.

---

## Scripts

| Command | What It Does |
|---------|-------------|
| `bash scripts/setup.sh` | Install all dependencies (idempotent) |
| `bash scripts/download_data.sh` | Fetch London datasets (skips existing) |
| `python scripts/ingest.py` | Load data → DuckDB + FAISS (skips done) |
| `bash scripts/start.sh` | Start all services (skips running) |
| `bash scripts/stop.sh` | Stop all services |
| `bash scripts/test.sh` | Run all tests |
| `bash scripts/test.sh quick` | Unit + integration only (fast) |
| `bash scripts/test.sh perf` | Performance benchmarks |

All scripts log to `logs/` with timestamps.

---

## Testing

```bash
bash scripts/test.sh unit          # Mocked, no services needed
bash scripts/test.sh integration   # Mocked, no services needed
bash scripts/test.sh e2e           # Requires running services
bash scripts/test.sh perf          # Performance benchmarks
bash scripts/test.sh file tests/unit/test_router.py  # Single file
```

---

## Project Structure

```
lucia/
├── .env.example          ← Copy to .env, add your keys
├── .github/
│   └── copilot-instructions.md
├── .spec/                ← Spec-kit specs (plan before code)
├── config/
│   ├── settings.py       ← Pydantic settings (reads .env)
│   ├── guardrails/       ← NeMo Guardrails (PII, safety, topic)
│   └── nemoclaw/         ← Agent sandbox policy (edit to restrict)
├── src/
│   ├── agent/            ← Orchestrator (router, planner, executor, reflector, synthesizer)
│   ├── api/              ← FastAPI (chat, voice, sessions, metrics)
│   ├── tools/            ← RAG, SQL, scraper, simulator, predictor, vision, calculator
│   ├── voice/            ← ElevenLabs STT + TTS
│   └── ingestion/        ← CSV → DuckDB + FAISS pipeline
├── ui/                   ← React chat UI
├── scripts/              ← Operational scripts (setup, download, ingest, start, stop, test)
├── tests/                ← Unit, integration, e2e, performance
├── data/                 ← Downloaded + processed data (gitignored)
└── logs/                 ← Runtime logs (gitignored)
```

---

## NVIDIA Stack (Hackathon Scoring)

| NVIDIA Tool | Role | Points |
|-------------|------|--------|
| Nemotron 3 Nano | LLM (reasoning, planning, SQL gen) | ✅ Primary |
| Nemotron Content Safety 4B | PII + toxicity + safety | ✅ Primary |
| NeMo Guardrails | Input/output safety rails | ✅ Primary |
| NemoClaw | Agent sandbox + orchestration | ✅ Primary |
| NV-Embed-v2 | RAG embeddings | ✅ Primary |
| NeVA-7B | Vision (traffic cams) | ✅ Primary |
| FAISS-GPU | Vector search | ✅ Supporting |

**Spark Story**: "LUCIA runs 4 NVIDIA models simultaneously in 128GB unified memory. Zero external LLM API calls. City data never leaves the device."

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Port already in use | `bash scripts/stop.sh` then retry |
| Model download slow | Models cached after first download |
| Out of GPU memory | Check `nvidia-smi`, reduce `--gpu-memory-utilization` in start.sh |
| ElevenLabs 401 | Check `LUCIA_ELEVENLABS_API_KEY` in .env |
| No data in responses | Run `python scripts/ingest.py` |
| UI not loading | Check port-forward: `ssh -L 3000:localhost:3000 user@dgx` |

---

## License

Hackathon project — NVIDIA Hackathon 2026.
