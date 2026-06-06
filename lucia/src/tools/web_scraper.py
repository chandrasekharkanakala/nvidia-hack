"""Web scraper tool — fetch live data from external APIs and URLs."""

import logging
from datetime import datetime, timezone

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)

SOURCES = {
    "weather": "https://api.openweathermap.org/data/2.5/weather",
    "tfl_disruptions": "https://api.tfl.gov.uk/Road/all/Disruption",
    "tfl_road": "https://api.tfl.gov.uk/Road",
    "tfl_air_quality": "https://api.tfl.gov.uk/AirQuality",
    "tfl_bikes": "https://api.tfl.gov.uk/BikePoint",
    "tfl_tube_status": "https://api.tfl.gov.uk/Line/Mode/tube/Status",
    "tfl_bus_status": "https://api.tfl.gov.uk/Line/Mode/bus/Status",
}

# Keyword-to-source mapping for natural language routing
SOURCE_KEYWORDS = {
    "weather": ["weather", "temperature", "rain", "wind", "forecast"],
    "tfl_disruptions": ["disruption", "road closure", "traffic delay"],
    "tfl_road": ["road status", "road condition", "traffic"],
    "tfl_air_quality": ["air quality", "pollution", "pm2.5", "no2"],
    "tfl_bikes": ["bike", "cycle hire", "santander cycle", "bike point"],
    "tfl_tube_status": ["tube", "underground", "line status", "tube status"],
    "tfl_bus_status": ["bus status", "bus delay"],
}


def _infer_source(query: str) -> str | None:
    """Infer the best data source from natural language query."""
    lower = query.lower()
    for source, keywords in SOURCE_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return source
    return None


async def execute(query: str = "", source: str = "", params: dict = None) -> dict:
    """Fetch live data from external sources.

    Can be called with:
        - source="tfl_disruptions" (explicit source)
        - query="What's the tube status?" (auto-detect source from NL)
    """
    # Auto-detect source from query if not specified
    if not source and query:
        source = _infer_source(query) or "tfl_disruptions"

    if source not in SOURCES:
        return {"source": source, "data": None, "fetched_at": None, "error": f"Unknown source: {source}. Available: {list(SOURCES.keys())}"}

    params = params or {}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            url = SOURCES[source]

            if source == "weather":
                query_params = {
                    "q": params.get("city", "London,GB"),
                    "appid": settings.openweathermap_api_key if hasattr(settings, "openweathermap_api_key") else "",
                    "units": "metric",
                }
                resp = await client.get(url, params=query_params)
            elif source.startswith("tfl_"):
                query_params = {}
                if hasattr(settings, "tfl_app_key") and settings.tfl_app_key:
                    query_params["app_key"] = settings.tfl_app_key
                query_params.update(params)
                resp = await client.get(url, params=query_params)
            else:
                resp = await client.get(url, params=params)

            resp.raise_for_status()
            data = resp.json()

        # Truncate large responses for readability
        if isinstance(data, list) and len(data) > 20:
            data = data[:20]
            truncated = True
        else:
            truncated = False

        return {
            "source": source,
            "data": data,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "truncated": truncated,
            "error": None,
        }

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching {source}: {e.response.status_code}")
        return {"source": source, "data": None, "fetched_at": None, "error": f"HTTP {e.response.status_code}"}
    except Exception as e:
        logger.exception(f"Web scraper failed for {source}")
        return {"source": source, "data": None, "fetched_at": None, "error": str(e)}
