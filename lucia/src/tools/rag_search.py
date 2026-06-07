"""RAG search tool using FAISS index and NV-Embed-v2."""

import logging
from pathlib import Path

import httpx
import numpy as np
import pandas as pd

from config.settings import settings

logger = logging.getLogger(__name__)

_index = None
_metadata = None

INDEX_PATH = Path(settings.faiss_index_path) if hasattr(settings, "faiss_index_path") else Path("data/embeddings/lucia.faiss")
METADATA_PATH = INDEX_PATH.parent / f"{INDEX_PATH.stem}_meta.parquet"


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
            df = pd.read_parquet(METADATA_PATH)
            _metadata = df.to_dict("records")
            logger.info(f"Loaded {len(_metadata)} metadata entries from {METADATA_PATH}")
        else:
            # Fallback: try JSON format
            json_path = INDEX_PATH.parent / "metadata.json"
            if json_path.exists():
                import json
                with open(json_path) as f:
                    _metadata = json.load(f)
            else:
                _metadata = []
                logger.warning("No metadata file found for FAISS index")
    except Exception as e:
        logger.error(f"Failed to load FAISS index: {e}")
        _index = None
        _metadata = []


async def execute(query: str, top_k: int = 10) -> dict:
    """Embed query via embedding model and search FAISS index."""
    try:
        _lazy_load()

        if _index is None or not _metadata:
            return {"results": [], "error": "FAISS index not available"}

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{settings.embed_base_url}/embeddings",
                json={"model": settings.embed_model, "input": [query]},
            )
            response.raise_for_status()
            data = response.json()

        query_vector = np.array([data["data"][0]["embedding"]], dtype=np.float32)

        # Normalize for cosine similarity (index was built with normalized vectors)
        norm = np.linalg.norm(query_vector)
        if norm > 0:
            query_vector = query_vector / norm

        distances, indices = _index.search(query_vector, top_k)

        results = []
        for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
            if idx == -1:
                continue
            if idx < len(_metadata):
                meta = _metadata[idx]
                results.append({
                    "text": meta.get("text", ""),
                    "score": float(dist),  # Already cosine sim (IP) from normalized vectors
                    "source": meta.get("source_table", meta.get("source", "unknown")),
                })

        return {"results": results, "query": query, "error": None}

    except Exception as e:
        logger.exception("RAG search failed")
        return {"results": [], "error": str(e)}
