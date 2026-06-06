"""Test factories for generating test data."""

import uuid
import random
from datetime import datetime, timedelta
from typing import Optional


def make_session_id() -> str:
    """Generate a new session UUID."""
    return str(uuid.uuid4())


def make_message(
    role: str = "user",
    content: str = "What is the air quality in Westminster?",
    mode: str = "chat",
    session_id: Optional[str] = None,
) -> dict:
    """Create a message dict."""
    return {
        "role": role,
        "content": content,
        "mode": mode,
        "session_id": session_id or make_session_id(),
        "timestamp": datetime.utcnow().isoformat(),
    }


def make_tool_result(
    tool: str = "sql_query",
    success: bool = True,
    data: Optional[dict] = None,
    duration_ms: float = 45.2,
) -> dict:
    """Create a tool result dict."""
    return {
        "tool": tool,
        "success": success,
        "data": data or {"rows": [], "columns": []},
        "duration_ms": duration_ms,
        "timestamp": datetime.utcnow().isoformat(),
    }


def make_plan_step(
    tool: str = "sql_query",
    params: Optional[dict] = None,
    depends_on: Optional[list[int]] = None,
) -> dict:
    """Create a plan step dict."""
    return {
        "tool": tool,
        "params": params or {"query": "SELECT 1"},
        "depends_on": depends_on or [],
        "status": "pending",
    }


def make_traffic_rows(n: int = 100) -> list[dict]:
    """Generate synthetic traffic data rows."""
    modes = ["Underground", "Bus", "Overground", "DLR", "Tram", "Elizabeth line"]
    boroughs = [
        "Westminster", "Camden", "Hackney", "Southwark", "Islington",
        "Tower Hamlets", "Lambeth", "Newham", "Lewisham", "Greenwich",
    ]
    years = [2020, 2021, 2022, 2023, 2024]
    quarters = ["Q1", "Q2", "Q3", "Q4"]

    rows = []
    for _ in range(n):
        rows.append({
            "year": random.choice(years),
            "quarter": random.choice(quarters),
            "mode": random.choice(modes),
            "journeys_millions": round(random.uniform(10.0, 500.0), 1),
            "borough": random.choice(boroughs),
            "date": (
                datetime(2020, 1, 1) + timedelta(days=random.randint(0, 1600))
            ).strftime("%Y-%m-%d"),
        })
    return rows
