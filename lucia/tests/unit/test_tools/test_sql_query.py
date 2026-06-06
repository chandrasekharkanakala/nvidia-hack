"""Unit tests for the SQL query tool."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestSqlQueryExecute:
    """Tests for sql_query.execute()."""

    @pytest.mark.asyncio
    @patch("tools.sql_query.AsyncOpenAI")
    @patch("tools.sql_query.duckdb")
    async def test_generates_and_executes_sql(self, mock_duckdb, mock_openai_cls, test_db):
        llm = AsyncMock()
        llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(
                    content="SELECT mode, SUM(journeys_millions) as total FROM transport_journeys GROUP BY mode"
                ))]
            )
        )
        mock_openai_cls.return_value = llm
        mock_duckdb.connect.return_value = test_db

        from tools.sql_query import execute

        result = await execute("What are total journeys by transport mode?")

        assert result["error"] is None
        assert "columns" in result
        assert "rows" in result
        assert result["row_count"] > 0
        assert "sql" in result

    @pytest.mark.asyncio
    @patch("tools.sql_query.AsyncOpenAI")
    @patch("tools.sql_query.duckdb")
    async def test_blocks_dangerous_sql(self, mock_duckdb, mock_openai_cls, test_db):
        llm = AsyncMock()
        llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(
                    content="DROP TABLE transport_journeys"
                ))]
            )
        )
        mock_openai_cls.return_value = llm
        mock_duckdb.connect.return_value = test_db

        from tools.sql_query import execute

        result = await execute("Delete all data")

        assert result.get("error") is not None or result.get("rows") == []

    @pytest.mark.asyncio
    @patch("tools.sql_query.AsyncOpenAI")
    @patch("tools.sql_query.duckdb")
    async def test_blocks_insert_statement(self, mock_duckdb, mock_openai_cls, test_db):
        llm = AsyncMock()
        llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(
                    content="INSERT INTO transport_journeys VALUES (2025, 'Q1', 'Bus', 500, 'Westminster')"
                ))]
            )
        )
        mock_openai_cls.return_value = llm
        mock_duckdb.connect.return_value = test_db

        from tools.sql_query import execute

        result = await execute("Add fake data")

        assert result.get("error") is not None

    @pytest.mark.asyncio
    @patch("tools.sql_query.AsyncOpenAI")
    @patch("tools.sql_query.duckdb")
    async def test_limits_result_rows(self, mock_duckdb, mock_openai_cls, test_db):
        llm = AsyncMock()
        llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(
                    content="SELECT * FROM transport_journeys"
                ))]
            )
        )
        mock_openai_cls.return_value = llm
        mock_duckdb.connect.return_value = test_db

        from tools.sql_query import execute

        result = await execute("Show all journeys")

        assert result["row_count"] <= 100

    @pytest.mark.asyncio
    @patch("tools.sql_query.AsyncOpenAI")
    @patch("tools.sql_query.duckdb")
    async def test_handles_invalid_sql(self, mock_duckdb, mock_openai_cls, test_db):
        llm = AsyncMock()
        llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(
                    content="SELCT * FORM nonexistent_table"
                ))]
            )
        )
        mock_openai_cls.return_value = llm
        mock_duckdb.connect.return_value = test_db

        from tools.sql_query import execute

        result = await execute("Bad query")

        assert result.get("error") is not None

    @pytest.mark.asyncio
    @patch("tools.sql_query.AsyncOpenAI")
    @patch("tools.sql_query.duckdb")
    async def test_aggregate_query(self, mock_duckdb, mock_openai_cls, test_db):
        llm = AsyncMock()
        llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(
                    content="SELECT COUNT(*) as total FROM transport_journeys WHERE year = 2023"
                ))]
            )
        )
        mock_openai_cls.return_value = llm
        mock_duckdb.connect.return_value = test_db

        from tools.sql_query import execute

        result = await execute("How many journeys in 2023?")

        assert result["error"] is None
        assert result["row_count"] == 1
        assert result["rows"][0][0] == 6  # 6 rows for 2023 in test fixture

    @pytest.mark.asyncio
    @patch("tools.sql_query.AsyncOpenAI")
    @patch("tools.sql_query.duckdb")
    async def test_returns_column_names(self, mock_duckdb, mock_openai_cls, test_db):
        llm = AsyncMock()
        llm.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(
                    content="SELECT year, borough FROM air_quality LIMIT 3"
                ))]
            )
        )
        mock_openai_cls.return_value = llm
        mock_duckdb.connect.return_value = test_db

        from tools.sql_query import execute

        result = await execute("Show air quality years and boroughs")

        assert "year" in result["columns"]
        assert "borough" in result["columns"]
