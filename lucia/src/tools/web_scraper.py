"""Web scraper tool — fetch live data from external APIs."""

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
}


async def execute(source: str, params: dict = None) -> dict:
    """Fetch live data from external sources."""
    if source not in SOURCES:
        return {"source": source, "data": None, "fetched_at": None, "error": f"Unknown source: {source}"}

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

        return {
            "source": source,
            "data": data,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching {source}: {e.response.status_code}")
        return {"source": source, "data": None, "fetched_at": None, "error": f"HTTP {e.response.status_code}"}
    except Exception as e:
        logger.exception(f"Web scraper failed for {source}")
        return {"source": source, "data": None, "fetched_at": None, "error": str(e)}
