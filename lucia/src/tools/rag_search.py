"""RAG search tool using FAISS index and NV-Embed-v2."""

import json
import logging
from pathlib import Path

import httpx
import numpy as np

from config.settings import settings

logger = logging.getLogger(__name__)

_index = None
_metadata = None

INDEX_PATH = Path(settings.faiss_index_path) if hasattr(settings, "faiss_index_path") else Path("data/faiss/index.bin")
METADATA_PATH = INDEX_PATH.parent / "metadata.json"


def _lazy_load():
    """Lazy load FAISS index and metadata from disk."""
    global _index, _metadata
    if _index is not None:
        return

    try:
        import faiss

        if INDEX_PATH.exists():
            _index = faiss.read_index(str(INDEX_PATH))
            logger.info(f"Loaded FAISS index with {_index.ntotal} vectors")
        else:
            logger.warning(f"FAISS index not found at {INDEX_PATH}")
            _index = None

        if METADATA_PATH.exists():
            with open(METADATA_PATH) as f:
                _metadata = json.load(f)
        else:
            _metadata = []
    except Exception as e:
        logger.error(f"Failed to load FAISS index: {e}")
        _index = None
        _metadata = []


async def execute(query: str, top_k: int = 10) -> dict:
    """Embed query via NV-Embed-v2 and search FAISS index."""
    try:
        _lazy_load()

        if _index is None:
            return {"results": [], "error": "FAISS index not available"}

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{settings.embed_base_url}/embeddings",
                json={"model": "NV-Embed-v2", "input": [query]},
            )
            response.raise_for_status()
            data = response.json()

        query_vector = np.array([data["data"][0]["embedding"]], dtype=np.float32)

        distances, indices = _index.search(query_vector, top_k)

        results = []
        for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
            if idx == -1:
                continue
            meta = _metadata[idx] if idx < len(_metadata) else {}
            results.append({
                "text": meta.get("text", ""),
                "score": float(1.0 / (1.0 + dist)),
                "source": meta.get("source", "unknown"),
            })

        return {"results": results, "error": None}

    except Exception as e:
        logger.exception("RAG search failed")
        return {"results": [], "error": str(e)}
