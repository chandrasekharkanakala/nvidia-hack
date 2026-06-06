# Technology Decisions Log

## Core Stack

| Layer | Choice | Why | Alternatives Considered |
|-------|--------|-----|------------------------|
| LLM | NemoTron-8B (local on Spark) | NVIDIA ecosystem points; 128GB unified memory fits model + context; local = low latency + privacy | GPT-4 (no NVIDIA points), Llama (no NVIDIA brand) |
| Agent Framework | NemoClaw | NVIDIA ecosystem points; built for tool-calling agents | LangGraph, CrewAI, custom |
| Embeddings | NV-Embed-v2 | NVIDIA ecosystem; high quality; GPU-accelerated | OpenAI embeddings, sentence-transformers |
| Vector Store | FAISS (GPU) | Runs on Spark GPU; fast; no external service needed | Milvus (overkill), ChromaDB (no GPU) |
| Structured Data | DuckDB | Blazing fast analytics on CSV/Parquet; in-process; SQL interface | PostgreSQL (overhead), pandas only (no SQL tool) |
| API Framework | FastAPI | Async, WebSocket support, OpenAPI auto-docs, Python native | Flask (no async), Express (wrong language) |
| UI | React + Vite + TailwindCSS | Fast to build, modern, lightweight | Streamlit (limited), Gradio (limited) |
| Voice TTS | ElevenLabs API | High quality, easy integration | NVIDIA Riva (complex setup in 12hr) |
| Voice STT | Whisper (local on Spark) | NVIDIA GPU acceleration; no API dependency | Google STT (external), Riva (complex) |
| Vision | NeVA or LLaVA variant | NVIDIA ecosystem; multimodal understanding | GPT-4V (no NVIDIA points) |
| Data Processing | pandas + RAPIDS cuDF (if time) | NVIDIA ecosystem bonus for RAPIDS; GPU-accelerated | pandas only (fallback) |
| Conversation Memory | SQLite | Zero-config, file-based, sufficient for demo | Redis (overhead), PostgreSQL (overhead) |
| Observability | Custom (Python logging + metrics) | Minimal overhead, demo-appropriate | OpenTelemetry (overkill for 12hr) |

---

## Libraries & SDKs Tracker

### Python Backend
```
# Core
fastapi>=0.100.0          # API framework
uvicorn[standard]         # ASGI server
websockets                # WebSocket support
pydantic>=2.0             # Data validation & settings

# NVIDIA
nemo-toolkit              # NeMo framework
nemoclaw                  # Agent orchestration
nvidia-nim                # Model serving (if available)

# Data & ML
duckdb                    # Analytical SQL engine
faiss-gpu                 # Vector similarity search
pandas                    # Data manipulation
pyarrow                   # Parquet support
numpy                     # Numerical computing

# Ingestion
openpyxl                  # Excel file reading
requests                  # HTTP client
beautifulsoup4            # Web scraping
aiohttp                   # Async HTTP

# Voice
openai-whisper            # Speech-to-text (local)
elevenlabs                # Text-to-speech API

# Eval & Observability
rouge-score               # Response quality metrics
structlog                 # Structured logging

# Utilities
python-dotenv             # Environment variable loading
rich                      # CLI formatting
```

### Frontend (UI)
```
react                     # UI framework
vite                      # Build tool
tailwindcss               # Styling
@tanstack/react-query     # Data fetching
lucide-react              # Icons
react-markdown            # Markdown rendering
leaflet                   # Map visualization (if time)
```

---

## Key Architectural Decisions

### ADR-001: Local Model Inference vs API
**Decision**: Run NemoTron locally on DGX Spark
**Rationale**: 
- Maximizes "Spark Story" points (15pts)
- Demonstrates privacy/latency benefits
- No network dependency during demo
- 128GB unified memory is the key differentiator

### ADR-002: DuckDB over PostgreSQL
**Decision**: Use DuckDB for structured data queries
**Rationale**:
- In-process (no server to manage)
- Columnar analytics engine (perfect for CSV/time-series data)
- Zero-config deployment
- SQL interface enables the agent to write queries dynamically

### ADR-003: FAISS over Milvus/ChromaDB
**Decision**: Use FAISS with GPU acceleration
**Rationale**:
- GPU-accelerated search on Spark
- No external server needed
- Battle-tested at scale
- Part of NVIDIA ecosystem narrative

### ADR-004: React over Streamlit/Gradio
**Decision**: Custom React UI
**Rationale**:
- Full control over UX (voice button, agent toggle, map)
- WebSocket streaming support
- Demonstrates "real product" vs "prototype feel"
- Faster iteration with Vite hot reload

### ADR-005: Agent Mode Toggle (Light/Deep)
**Decision**: Offer two modes in UI
**Rationale**:
- Light: Single-step reasoning, fast response (< 2s)
- Deep: Multi-step planning + tool orchestration (5-15s)
- Demonstrates agent sophistication
- User chooses speed vs depth
