"""Unit tests for the RAG search tool."""

import pytest
import numpy as np
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_faiss_index():
    """Mock FAISS index with known vectors."""
    index = MagicMock()
    # Return distances and indices for 3 results
    index.search.return_value = (
        np.array([[0.1, 0.5, 1.2]], dtype=np.float32),  # distances
        np.array([[0, 2, 1]], dtype=np.int64),  # indices
    )
    index.ntotal = 100
    return index


@pytest.fixture
def mock_metadata():
    """Mock metadata for FAISS results."""
    return [
        {"text": "Congestion charge reduces traffic by 15% in central London", "source": "tfl_report.pdf"},
        {"text": "Bus routes cover 95% of London boroughs", "source": "tfl_network.pdf"},
        {"text": "ULEZ has improved air quality by 20% since 2019", "source": "gla_environment.pdf"},
    ]


class TestRagSearchExecute:
    """Tests for rag_search.execute()."""

    @pytest.mark.asyncio
    @patch("tools.rag_search._lazy_load")
    @patch("tools.rag_search.httpx.AsyncClient")
    async def test_returns_ranked_results(self, mock_client_cls, mock_load, mock_faiss_index, mock_metadata):
        # Setup embedding API mock
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=MagicMock(
            status_code=200,
            json=lambda: {"data": [{"embedding": np.random.randn(4096).tolist()}]},
        ))
        mock_client_cls.return_value = mock_client

        with patch("tools.rag_search._index", mock_faiss_index), \
             patch("tools.rag_search._metadata", mock_metadata):
            from tools.rag_search import execute

            result = await execute("congestion charge impact")

        assert "results" in result
        assert len(result["results"]) > 0
        assert result["error"] is None

    @pytest.mark.asyncio
    @patch("tools.rag_search._lazy_load")
    @patch("tools.rag_search._index", None)
    async def test_no_index_returns_error(self, mock_load):
        mock_load.side_effect = FileNotFoundError("Index not found")
        from tools.rag_search import execute

        result = await execute("test query")

        assert result.get("error") is not None or result.get("results") == []

    @pytest.mark.asyncio
    @patch("tools.rag_search._lazy_load")
    @patch("tools.rag_search.httpx.AsyncClient")
    async def test_results_have_required_fields(self, mock_client_cls, mock_load, mock_faiss_index, mock_metadata):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=MagicMock(
            status_code=200,
            json=lambda: {"data": [{"embedding": np.random.randn(4096).tolist()}]},
        ))
        mock_client_cls.return_value = mock_client

        with patch("tools.rag_search._index", mock_faiss_index), \
             patch("tools.rag_search._metadata", mock_metadata):
            from tools.rag_search import execute

            result = await execute("London transport policy")

        for item in result.get("results", []):
            assert "text" in item
            assert "score" in item
            assert "source" in item

    @pytest.mark.asyncio
    @patch("tools.rag_search._lazy_load")
    @patch("tools.rag_search.httpx.AsyncClient")
    async def test_scores_between_zero_and_one(self, mock_client_cls, mock_load, mock_faiss_index, mock_metadata):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=MagicMock(
            status_code=200,
            json=lambda: {"data": [{"embedding": np.random.randn(4096).tolist()}]},
        ))
        mock_client_cls.return_value = mock_client

        with patch("tools.rag_search._index", mock_faiss_index), \
             patch("tools.rag_search._metadata", mock_metadata):
            from tools.rag_search import execute

            result = await execute("air quality trends")

        for item in result.get("results", []):
            assert 0.0 <= item["score"] <= 1.0

    @pytest.mark.asyncio
    @patch("tools.rag_search._lazy_load")
    @patch("tools.rag_search.httpx.AsyncClient")
    async def test_top_k_limits_results(self, mock_client_cls, mock_load, mock_faiss_index, mock_metadata):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=MagicMock(
            status_code=200,
            json=lambda: {"data": [{"embedding": np.random.randn(4096).tolist()}]},
        ))
        mock_client_cls.return_value = mock_client

        # Limit to 2 results
        mock_faiss_index.search.return_value = (
            np.array([[0.1, 0.5]], dtype=np.float32),
            np.array([[0, 1]], dtype=np.int64),
        )

        with patch("tools.rag_search._index", mock_faiss_index), \
             patch("tools.rag_search._metadata", mock_metadata):
            from tools.rag_search import execute

            result = await execute("query", top_k=2)

        assert len(result.get("results", [])) <= 2
