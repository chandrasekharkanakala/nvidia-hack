# Repository Structure

```
nvidia-hack/
├── .github/
│   └── copilot-instructions.md          # Copilot context for this repo
├── raw/
│   ├── initial-notes.md                  # Original requirements
│   └── plan/                             # Architecture & planning docs
│       ├── 01-use-case-recommendation.md
│       ├── 02-e2e-architecture.md
│       ├── 03-12hr-hackathon-scope.md
│       ├── 04-repo-structure.md
│       ├── 05-tech-decisions.md
│       └── 06-nvidia-stack-usage.md
├── docs/
│   ├── setup.md                          # How to set up the DGX Spark env
│   ├── api.md                            # API documentation
│   └── demo-script.md                    # Demo walkthrough
├── data/
│   ├── raw/                              # Original downloaded datasets
│   ├── processed/                        # Cleaned/transformed data
│   ├── embeddings/                       # FAISS indices
│   └── catalog.json                      # Dataset metadata manifest
├── src/
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py                   # Pydantic settings (env vars)
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── loader.py                     # CSV/Excel/API data loaders
│   │   ├── embedder.py                   # Text → embedding pipeline
│   │   └── catalog.py                    # Data catalog management
│   ├── models/
│   │   ├── __init__.py
│   │   ├── serve.py                      # Model serving (NIM/vLLM)
│   │   └── registry.py                   # Model registry & health checks
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── orchestrator.py               # NemoClaw agent orchestration
│   │   ├── router.py                     # Intent classification & routing
│   │   ├── planner.py                    # Query decomposition
│   │   ├── executor.py                   # Tool execution engine
│   │   ├── reflector.py                  # Output validation & hallucination check
│   │   └── memory.py                     # Conversation memory management
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── rag_search.py                 # Vector similarity search
│   │   ├── sql_query.py                  # DuckDB analytical queries
│   │   ├── web_scraper.py                # Real-time data fetcher (weather)
│   │   ├── simulator.py                  # What-if scenario engine
│   │   ├── predictor.py                  # Time-series forecasting
│   │   ├── vision.py                     # Image understanding
│   │   └── calculator.py                 # Numerical computations
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py                       # FastAPI app entry point
│   │   ├── routes/
│   │   │   ├── chat.py                   # Chat endpoints (REST + WebSocket)
│   │   │   ├── voice.py                  # Voice endpoints (STT/TTS)
│   │   │   └── health.py                 # Health check endpoints
│   │   └── middleware/
│   │       ├── logging.py                # Request/response logging
│   │       └── metrics.py                # Latency & token tracking
│   ├── voice/
│   │   ├── __init__.py
│   │   ├── stt.py                        # Speech-to-text (Whisper)
│   │   └── tts.py                        # Text-to-speech (ElevenLabs)
│   └── eval/
│       ├── __init__.py
│       ├── quality.py                    # Response quality scorer
│       ├── hallucination.py              # Fact-check vs source data
│       └── metrics.py                    # Performance metrics collector
├── ui/
│   ├── package.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── App.tsx                       # Main app component
│   │   ├── components/
│   │   │   ├── ChatPanel.tsx             # Chat interface
│   │   │   ├── VoiceButton.tsx           # Push-to-talk
│   │   │   ├── AgentToggle.tsx           # Light/Deep mode switch
│   │   │   ├── MetricsPanel.tsx          # Observability display
│   │   │   └── MapView.tsx               # Geospatial visualization
│   │   └── hooks/
│   │       ├── useWebSocket.ts           # WS connection management
│   │       └── useVoice.ts               # Voice recording hook
│   └── public/
├── scripts/
│   ├── setup_spark.sh                    # DGX Spark environment setup
│   ├── download_data.sh                  # Fetch datasets
│   ├── ingest.py                         # Run full ingestion pipeline
│   └── serve_model.sh                    # Start model serving
├── tests/
│   ├── test_ingestion.py
│   ├── test_agent.py
│   ├── test_tools.py
│   └── test_api.py
├── pyproject.toml                        # Python project config
├── requirements.txt                      # Python dependencies
├── docker-compose.yml                    # Local dev (optional)
├── Makefile                              # Common commands
└── README.md                             # Project overview
```

## Key Design Principles

1. **Modular**: Each component is independently testable and replaceable
2. **Config-driven**: All settings via environment variables (Pydantic BaseSettings)
3. **Tool-based Agent**: Tools are pure functions with clear interfaces — easy to add new ones
4. **Separation**: Data pipeline ≠ Agent logic ≠ API layer ≠ UI
5. **Observable**: Every request tracked end-to-end with latency, tokens, quality score
