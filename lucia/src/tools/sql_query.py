"""SQL query tool — LLM generates SQL from natural language, executes on DuckDB."""

import logging

import duckdb
from openai import AsyncOpenAI

from config.settings import settings

logger = logging.getLogger(__name__)

AVAILABLE_TABLES = [
    "congestion_charge", "transport_journeys", "cycle_hires", "road_collisions",
    "walking_cycling", "ptals", "road_energy", "tube_temps", "buses", "air_quality",
    "reservoir_levels", "ghg_emissions", "fly_tipping", "trees", "solar",
    "planning_apps", "brownfield", "affordable_housing", "building_stock",
    "crime", "fire_incidents", "fire_mobilisation",
]

SYSTEM_PROMPT = f"""You are a SQL expert. Generate a DuckDB-compatible SQL query to answer the user's question.
Available tables: {', '.join(AVAILABLE_TABLES)}
Rules:
- Return ONLY the SQL query, no explanation or markdown.
- Use appropriate aggregations, filters, and joins.
- Limit results to 100 rows unless the user asks for more.
- Do not use DROP, DELETE, INSERT, UPDATE, or any DDL statements.
"""


async def execute(question: str) -> dict:
    """Generate SQL from natural language and execute on DuckDB."""
    try:
        llm_client = AsyncOpenAI(
            base_url=f"http://localhost:{settings.llm_port}/v1",
            api_key="not-needed",
        )

        response = await llm_client.chat.completions.create(
            model=settings.llm_model if hasattr(settings, "llm_model") else "meta/llama-3.1-70b-instruct",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ],
            temperature=0.0,
            max_tokens=512,
        )

        sql = response.choices[0].message.content.strip()
        sql = sql.strip("`").removeprefix("sql").strip()

        # Safety check
        forbidden = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE", "TRUNCATE"]
        sql_upper = sql.upper()
        for kw in forbidden:
            if kw in sql_upper and kw not in ("CREATE VIEW",):
                return {"sql": sql, "columns": [], "rows": [], "row_count": 0, "error": f"Forbidden keyword: {kw}"}

        db_path = settings.duckdb_path if hasattr(settings, "duckdb_path") else "data/lucia.duckdb"
        conn = duckdb.connect(db_path, read_only=True)
        try:
            result = conn.execute(sql)
            columns = [desc[0] for desc in result.description]
            rows = [list(row) for row in result.fetchall()]
            return {
                "sql": sql,
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
            }
        finally:
            conn.close()

    except duckdb.Error as e:
        logger.error(f"DuckDB error: {e}")
        return {"sql": sql if "sql" in dir() else "", "columns": [], "rows": [], "row_count": 0, "error": str(e)}
    except Exception as e:
        logger.exception("SQL query tool failed")
        return {"sql": "", "columns": [], "rows": [], "row_count": 0, "error": str(e)}
