"""Unit tests for the web scraper tool."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_weather_response():
    """Mock weather API response."""
    resp = MagicMock(
        status_code=200,
        json=lambda: {
            "main": {"temp": 15.2, "humidity": 72},
            "weather": [{"description": "light rain"}],
            "wind": {"speed": 5.1},
            "name": "London",
        },
    )
    resp.raise_for_status = MagicMock()
    return resp


@pytest.fixture
def mock_tfl_disruptions_response():
    """Mock TfL disruptions API response."""
    resp = MagicMock(
        status_code=200,
        json=lambda: [
            {
                "id": "northern",
                "name": "Northern",
                "lineStatuses": [{"statusSeverityDescription": "Minor Delays", "reason": "Signal failure"}],
            },
            {
                "id": "victoria",
                "name": "Victoria",
                "lineStatuses": [{"statusSeverityDescription": "Good Service"}],
            },
        ],
    )
    resp.raise_for_status = MagicMock()
    return resp


class TestWebScraperExecute:
    """Tests for web_scraper.execute()."""

    @pytest.mark.asyncio
    @patch("tools.web_scraper.httpx.AsyncClient")
    async def test_weather_source(self, mock_client_cls, mock_weather_response):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_weather_response)
        mock_client_cls.return_value = mock_client

        from tools.web_scraper import execute

        result = await execute(source="weather")

        assert result["source"] == "weather"
        assert result["data"] is not None
        assert result["error"] is None
        assert "fetched_at" in result

    @pytest.mark.asyncio
    @patch("tools.web_scraper.httpx.AsyncClient")
    async def test_tfl_disruptions_source(self, mock_client_cls, mock_tfl_disruptions_response):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_tfl_disruptions_response)
        mock_client_cls.return_value = mock_client

        from tools.web_scraper import execute

        result = await execute(source="tfl_disruptions")

        assert result["source"] == "tfl_disruptions"
        assert result["data"] is not None

    @pytest.mark.asyncio
    @patch("tools.web_scraper.httpx.AsyncClient")
    async def test_unknown_source_returns_error(self, mock_client_cls):
        from tools.web_scraper import execute

        result = await execute(source="nonexistent_api")

        assert result.get("error") is not None

    @pytest.mark.asyncio
    @patch("tools.web_scraper.httpx.AsyncClient")
    async def test_api_timeout_handled(self, mock_client_cls):
        import httpx

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Connection timed out"))
        mock_client_cls.return_value = mock_client

        from tools.web_scraper import execute

        result = await execute(source="weather")

        assert result.get("error") is not None
        assert result["data"] is None

    @pytest.mark.asyncio
    @patch("tools.web_scraper.httpx.AsyncClient")
    async def test_api_error_status_handled(self, mock_client_cls):
        import httpx

        mock_resp = MagicMock(status_code=500, text="Internal Server Error")
        mock_resp.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError("Server Error", request=MagicMock(), response=mock_resp)
        )
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        from tools.web_scraper import execute

        result = await execute(source="weather")

        assert result.get("error") is not None

    @pytest.mark.asyncio
    @patch("tools.web_scraper.httpx.AsyncClient")
    async def test_params_passed_to_request(self, mock_client_cls, mock_weather_response):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_weather_response)
        mock_client_cls.return_value = mock_client

        from tools.web_scraper import execute

        await execute(source="weather", params={"city": "London"})

        # Verify the request was made
        mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    @patch("tools.web_scraper.httpx.AsyncClient")
    async def test_fetched_at_is_iso_timestamp(self, mock_client_cls, mock_weather_response):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_weather_response)
        mock_client_cls.return_value = mock_client

        from tools.web_scraper import execute
        from datetime import datetime

        result = await execute(source="weather")

        if result.get("fetched_at"):
            # Should be parseable ISO format
            datetime.fromisoformat(result["fetched_at"].replace("Z", "+00:00"))
