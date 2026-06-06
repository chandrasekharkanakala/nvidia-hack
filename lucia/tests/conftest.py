"""Shared test fixtures for Lucia test suite."""

import uuid
import asyncio
from unittest.mock import AsyncMock, MagicMock
from typing import AsyncGenerator

import numpy as np
import duckdb
import pytest
import httpx


@pytest.fixture
def mock_llm():
    """AsyncMock returning canned chat completions."""
    mock = AsyncMock()
    mock.chat.completions.create.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(
                    role="assistant",
                    content="Based on the transport data, congestion charges have reduced traffic by 15% in central London.",
                    tool_calls=None,
                ),
                finish_reason="stop",
            )
        ],
        usage=MagicMock(prompt_tokens=150, completion_tokens=50, total_tokens=200),
        model="meta-llama/Llama-3.1-8B-Instruct",
    )
    return mock


@pytest.fixture
def mock_embeddings():
    """Returns random 4096-dim numpy vectors for embedding tests."""

    def _embed(texts: list[str]) -> np.ndarray:
        return np.random.randn(len(texts), 4096).astype(np.float32)

    return _embed


@pytest.fixture
def test_db():
    """In-memory DuckDB with schema and sample data."""
    con = duckdb.connect(":memory:")

    # Traffic data
    con.execute("""
        CREATE TABLE transport_journeys (
            year INTEGER,
            quarter VARCHAR,
            mode VARCHAR,
            journeys_millions DOUBLE,
            borough VARCHAR
        )
    """)
    con.execute("""
        INSERT INTO transport_journeys VALUES
        (2023, 'Q1', 'Underground', 320.5, 'Westminster'),
        (2023, 'Q1', 'Bus', 415.2, 'Camden'),
        (2023, 'Q2', 'Underground', 335.1, 'Westminster'),
        (2023, 'Q2', 'Bus', 420.8, 'Camden'),
        (2023, 'Q3', 'Underground', 310.0, 'Islington'),
        (2023, 'Q3', 'Overground', 89.4, 'Hackney'),
        (2024, 'Q1', 'Underground', 345.6, 'Westminster'),
        (2024, 'Q1', 'Bus', 398.3, 'Southwark')
    """)

    # Air quality data
    con.execute("""
        CREATE TABLE air_quality (
            year INTEGER,
            borough VARCHAR,
            pollutant VARCHAR,
            concentration DOUBLE,
            unit VARCHAR
        )
    """)
    con.execute("""
        INSERT INTO air_quality VALUES
        (2023, 'Westminster', 'NO2', 38.5, 'ug/m3'),
        (2023, 'Camden', 'NO2', 32.1, 'ug/m3'),
        (2023, 'Westminster', 'PM2.5', 12.3, 'ug/m3'),
        (2023, 'Hackney', 'NO2', 29.8, 'ug/m3'),
        (2023, 'Southwark', 'PM10', 22.4, 'ug/m3'),
        (2024, 'Westminster', 'NO2', 35.2, 'ug/m3'),
        (2024, 'Camden', 'PM2.5', 10.8, 'ug/m3')
    """)

    # System tables
    con.execute("""
        CREATE TABLE sys_data_catalog (
            table_name VARCHAR PRIMARY KEY,
            source_file VARCHAR,
            row_count INTEGER,
            column_count INTEGER,
            ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    con.execute("""
        INSERT INTO sys_data_catalog VALUES
        ('transport_journeys', 'public_transport_journeys.csv', 8, 5, CURRENT_TIMESTAMP),
        ('air_quality', 'air_quality_borough.csv', 7, 5, CURRENT_TIMESTAMP)
    """)

    yield con
    con.close()


@pytest.fixture
async def test_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """httpx AsyncClient with ASGI transport against FastAPI app."""
    try:
        from api.main import app

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    except ImportError:
        # Fallback if app not available
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            yield client


@pytest.fixture
def sample_messages() -> list[dict]:
    """4 realistic chat messages for testing."""
    return [
        {
            "role": "user",
            "content": "What are the busiest transport routes in London?",
            "session_id": str(uuid.uuid4()),
        },
        {
            "role": "assistant",
            "content": "Based on TfL data, the Underground carries over 300 million journeys per quarter.",
            "session_id": str(uuid.uuid4()),
        },
        {
            "role": "user",
            "content": "Show me air quality trends for Westminster borough",
            "session_id": str(uuid.uuid4()),
        },
        {
            "role": "user",
            "content": "Compare cycling infrastructure investment across boroughs",
            "session_id": str(uuid.uuid4()),
        },
    ]


@pytest.fixture
def sample_csv(tmp_path):
    """Creates a temp CSV with traffic data."""
    import pandas as pd

    data = {
        "year": [2022, 2022, 2023, 2023, 2024],
        "quarter": ["Q1", "Q2", "Q1", "Q2", "Q1"],
        "mode": ["Underground", "Bus", "Underground", "Bus", "Underground"],
        "journeys_millions": [298.5, 405.1, 320.5, 415.2, 345.6],
        "borough": ["Westminster", "Camden", "Westminster", "Camden", "Westminster"],
    }
    df = pd.DataFrame(data)
    csv_path = tmp_path / "transport_test.csv"
    df.to_csv(csv_path, index=False)
    return csv_path
