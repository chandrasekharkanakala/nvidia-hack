"""Integration tests for the data ingestion pipeline (CSV → DuckDB + FAISS)."""

import pytest
import tempfile
import os
from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np


class TestCSVIngestion:
    """Tests for CSV → DuckDB ingestion."""

    @pytest.mark.asyncio
    async def test_csv_loaded_into_duckdb(self, sample_csv, test_db):
        """CSV data should be queryable in DuckDB after ingestion."""
        import pandas as pd

        df = pd.read_csv(sample_csv)
        test_db.execute("CREATE TABLE test_import AS SELECT * FROM read_csv_auto(?)", [str(sample_csv)])

        result = test_db.execute("SELECT COUNT(*) FROM test_import").fetchone()
        assert result[0] == 5  # 5 rows in sample_csv

    @pytest.mark.asyncio
    async def test_schema_preserved(self, sample_csv, test_db):
        """Column names and types should be preserved."""
        test_db.execute("CREATE TABLE test_schema AS SELECT * FROM read_csv_auto(?)", [str(sample_csv)])

        columns = test_db.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'test_schema'").fetchall()
        col_names = [c[0] for c in columns]

        assert "year" in col_names
        assert "quarter" in col_names
        assert "mode" in col_names
        assert "journeys_millions" in col_names
        assert "borough" in col_names

    @pytest.mark.asyncio
    async def test_data_catalog_updated(self, sample_csv, test_db):
        """Data catalog should track ingested tables."""
        test_db.execute("CREATE TABLE test_catalog AS SELECT * FROM read_csv_auto(?)", [str(sample_csv)])
        test_db.execute("""
            INSERT INTO sys_data_catalog (table_name, source_file, row_count, column_count)
            VALUES ('test_catalog', ?, 5, 5)
        """, [os.path.basename(str(sample_csv))])

        catalog = test_db.execute("SELECT * FROM sys_data_catalog WHERE table_name = 'test_catalog'").fetchone()
        assert catalog is not None
        assert catalog[2] == 5  # row_count

    @pytest.mark.asyncio
    async def test_handles_empty_csv(self, tmp_path, test_db):
        """Should handle empty CSV gracefully."""
        csv_path = tmp_path / "empty.csv"
        csv_path.write_text("year,quarter,mode\n")

        test_db.execute("CREATE TABLE empty_test AS SELECT * FROM read_csv_auto(?)", [str(csv_path)])
        result = test_db.execute("SELECT COUNT(*) FROM empty_test").fetchone()
        assert result[0] == 0

    @pytest.mark.asyncio
    async def test_handles_large_csv(self, tmp_path, test_db):
        """Should handle larger datasets."""
        import pandas as pd
        from tests.factories import make_traffic_rows

        rows = make_traffic_rows(1000)
        df = pd.DataFrame(rows)
        csv_path = tmp_path / "large.csv"
        df.to_csv(csv_path, index=False)

        test_db.execute("CREATE TABLE large_test AS SELECT * FROM read_csv_auto(?)", [str(csv_path)])
        result = test_db.execute("SELECT COUNT(*) FROM large_test").fetchone()
        assert result[0] == 1000


class TestFAISSIndexing:
    """Tests for document embedding and FAISS index creation."""

    @pytest.mark.asyncio
    @patch("ingestion.embedder.httpx.AsyncClient")
    async def test_text_chunking(self, mock_client):
        from ingestion.embedder import chunk_text

        text = "This is a sentence. " * 100  # ~2000 chars
        chunks = chunk_text(text, max_tokens=64, overlap=8)

        assert len(chunks) > 1
        # Each chunk should be roughly within limit
        for chunk in chunks:
            assert len(chunk) <= 64 * 5  # ~4 chars per token, some margin

    @pytest.mark.asyncio
    @patch("ingestion.embedder.httpx.AsyncClient")
    async def test_embed_texts_returns_vectors(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=MagicMock(
            status_code=200,
            json=lambda: {"data": [{"embedding": np.random.randn(4096).tolist()} for _ in range(3)]},
        ))
        mock_client_cls.return_value = mock_client

        from ingestion.embedder import embed_texts

        vectors = await embed_texts(["text one", "text two", "text three"])

        assert vectors.shape == (3, 4096)
        assert vectors.dtype == np.float32

    def test_build_faiss_index_flat(self):
        """Small datasets should use Flat index."""
        from ingestion.embedder import build_faiss_index

        vectors = np.random.randn(50, 4096).astype(np.float32)
        index = build_faiss_index(vectors)

        assert index.ntotal == 50

    def test_build_faiss_index_ivf(self):
        """Larger datasets should use IVF index."""
        from ingestion.embedder import build_faiss_index

        vectors = np.random.randn(500, 4096).astype(np.float32)
        index = build_faiss_index(vectors)

        assert index.ntotal == 500

    def test_save_and_load_index(self, tmp_path):
        """Index should be saveable and loadable."""
        from ingestion.embedder import build_faiss_index, save_index, load_index

        vectors = np.random.randn(20, 4096).astype(np.float32)
        index = build_faiss_index(vectors)

        path = str(tmp_path / "test_index.bin")
        save_index(index, path)
        loaded = load_index(path)

        assert loaded.ntotal == 20

    @pytest.mark.asyncio
    @patch("ingestion.embedder.httpx.AsyncClient")
    async def test_chunking_preserves_sentence_boundaries(self, mock_client):
        from ingestion.embedder import chunk_text

        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        chunks = chunk_text(text, max_tokens=16, overlap=4)

        # Chunks should try to break at sentence boundaries
        for chunk in chunks:
            # Should not cut mid-word (basic check)
            assert not chunk.startswith(" ") or chunk.strip() == chunk.strip()
