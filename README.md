# nvidia-hack
Nvidia hackathon - 2026

## Project

See [lucia/README.md](lucia/README.md) for full architecture, setup, and usage docs.

## Quick Start

```bash
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
