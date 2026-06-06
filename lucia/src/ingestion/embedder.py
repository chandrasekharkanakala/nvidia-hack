"""Embedder module — text chunking, embedding, and FAISS index management."""

import logging
from pathlib import Path

import httpx
import numpy as np

from config.settings import settings

logger = logging.getLogger(__name__)


def chunk_text(text: str, max_tokens: int = 256, overlap: int = 32) -> list[str]:
    """Split text into overlapping chunks by approximate token count."""
    # Approximate: 1 token ≈ 4 characters
    chars_per_token = 4
    max_chars = max_tokens * chars_per_token
    overlap_chars = overlap * chars_per_token

    if not text:
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars

        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence-ending punctuation near the end
            for sep in [". ", ".\n", "\n\n", "\n", " "]:
                last_sep = text.rfind(sep, start + max_chars // 2, end)
                if last_sep != -1:
                    end = last_sep + len(sep)
                    break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = end - overlap_chars
        if start <= 0 and end >= len(text):
            break

    return chunks


async def embed_texts(texts: list[str]) -> np.ndarray:
    """Batch embed texts via NV-Embed-v2. Returns array of shape (n, dim)."""
    try:
        batch_size = 32
        all_embeddings = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                response = await client.post(
                    f"{settings.embed_base_url}/embeddings",
                    json={"model": "NV-Embed-v2", "input": batch},
                )
                response.raise_for_status()
                data = response.json()
                batch_embeddings = [item["embedding"] for item in data["data"]]
                all_embeddings.extend(batch_embeddings)

        return np.array(all_embeddings, dtype=np.float32)

    except Exception as e:
        logger.exception("Embedding failed")
        raise


def build_faiss_index(vectors: np.ndarray):
    """Build an IVF-Flat FAISS index (GPU if available)."""
    import faiss

    dim = vectors.shape[1]
    n_vectors = vectors.shape[0]

    # Choose number of clusters
    n_clusters = min(int(np.sqrt(n_vectors)), max(1, n_vectors // 39))
    n_clusters = max(1, n_clusters)

    if n_vectors < n_clusters * 39:
        # Not enough vectors for IVF, use flat index
        index = faiss.IndexFlatL2(dim)
        index.add(vectors)
        return index

    quantizer = faiss.IndexFlatL2(dim)
    index = faiss.IndexIVFFlat(quantizer, dim, n_clusters)

    # Try GPU
    try:
        res = faiss.StandardGpuResources()
        gpu_index = faiss.index_cpu_to_gpu(res, 0, index)
        gpu_index.train(vectors)
        gpu_index.add(vectors)
        # Convert back to CPU for saving
        index = faiss.index_gpu_to_cpu(gpu_index)
        logger.info(f"Built GPU FAISS index with {n_vectors} vectors, {n_clusters} clusters")
    except Exception:
        # Fallback to CPU
        index.train(vectors)
        index.add(vectors)
        logger.info(f"Built CPU FAISS index with {n_vectors} vectors, {n_clusters} clusters")

    return index


def save_index(index, path: str | Path) -> None:
    """Save FAISS index to disk."""
    import faiss

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(path))
    logger.info(f"Saved FAISS index to {path}")


def load_index(path: str | Path):
    """Load FAISS index from disk."""
    import faiss

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"FAISS index not found: {path}")
    index = faiss.read_index(str(path))
    logger.info(f"Loaded FAISS index from {path} ({index.ntotal} vectors)")
    return index
