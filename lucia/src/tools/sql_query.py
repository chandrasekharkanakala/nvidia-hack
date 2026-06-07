"""SQL query tool — LLM generates SQL from natural language, executes on DuckDB."""

import logging

import duckdb
from openai import AsyncOpenAI

from config.settings import settings

logger = logging.getLogger(__name__)


def _get_schema_context() -> str:
    """Fetch actual table schemas from DuckDB for the LLM prompt."""
    try:
        db_path = settings.duckdb_path if hasattr(settings, "duckdb_path") else "data/lucia.duckdb"
        conn = duckdb.connect(db_path, read_only=True)
        tables = [t[0] for t in conn.execute("SHOW TABLES").fetchall()]

        schema_parts = []
        for table in tables:
            if table.startswith("sys_") or table in ("metrics", "conversations", "data_catalog", "chat_messages"):
                continue
            try:
                cols = conn.execute(f"DESCRIBE {table}").fetchall()
                col_desc = ", ".join(f"{c[0]} ({c[1]})" for c in cols[:15])
                row_count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                # Get sample row to help LLM understand the data
                sample = conn.execute(f"SELECT * FROM {table} LIMIT 1").fetchone()
                sample_str = ""
                if sample:
                    col_names = [c[0] for c in cols[:15]]
                    sample_str = " | Example: " + ", ".join(f"{col_names[i]}={sample[i]}" for i in range(min(len(col_names), len(sample), 6)))
                schema_parts.append(f"  {table} [{row_count} rows]: {col_desc}{sample_str}")
            except Exception:
                schema_parts.append(f"  {table}: (schema unavailable)")

        conn.close()
        return "\n".join(schema_parts) if schema_parts else "No tables available."
    except Exception as e:
        logger.warning(f"Could not fetch schema: {e}")
        return "Schema unavailable."


SYSTEM_PROMPT_TEMPLATE = """You are a SQL expert. Generate a DuckDB-compatible SQL query to answer the user's question.

Available tables with columns and sample data:
{schema}

Rules:
- Return ONLY the SQL query, no explanation, no markdown, no backticks.
- Use ONLY the exact column names shown above. Do NOT invent columns.
- If the table doesn't have the specific column the user asks about (e.g., "rush hour", "peak"), use what IS available (e.g., total volume, yearly data).
- Use appropriate aggregations (SUM, AVG, COUNT, MAX, MIN) with GROUP BY.
- Always LIMIT to 50 rows.
- If unsure which table to use, pick the most relevant one based on the question topic.
- For borough comparisons, GROUP BY the borough column and ORDER BY the metric DESC.

Examples of correct queries:
{few_shots}
"""

# Few-shot examples that teach the LLM correct SQL patterns for our data
FEW_SHOT_EXAMPLES = [
    {
        "question": "Which borough has the highest traffic volume?",
        "sql": "SELECT borough, SUM(all_vehicles_km) as total_km FROM traffic_flows GROUP BY borough ORDER BY total_km DESC LIMIT 10"
    },
    {
        "question": "How many licensed vehicles are there in Westminster?",
        "sql": "SELECT * FROM licensed_vehicles WHERE borough ILIKE '%westminster%' LIMIT 20"
    },
    {
        "question": "Show me cycle hire trends",
        "sql": "SELECT * FROM cycle_hires ORDER BY day DESC LIMIT 30"
    },
    {
        "question": "Compare air quality across boroughs",
        "sql": "SELECT borough, AVG(no2) as avg_no2, AVG(pm25) as avg_pm25 FROM air_quality_gla GROUP BY borough ORDER BY avg_no2 DESC LIMIT 20"
    },
    {
        "question": "What are the crime rates by borough?",
        "sql": "SELECT borough, COUNT(*) as incidents FROM crime GROUP BY borough ORDER BY incidents DESC LIMIT 15"
    },
    {
        "question": "Show fire incidents by type",
        "sql": "SELECT incident_type, COUNT(*) as count FROM fire_incidents GROUP BY incident_type ORDER BY count DESC LIMIT 20"
    },
    {
        "question": "How much fly-tipping in Hackney?",
        "sql": "SELECT * FROM fly_tipping WHERE borough ILIKE '%hackney%' LIMIT 20"
    },
    {
        "question": "What public transport accessibility levels exist?",
        "sql": "SELECT * FROM ptals LIMIT 30"
    },
    {
        "question": "Compare congestion charge data over time",
        "sql": "SELECT year, SUM(vehicles) as total_vehicles FROM congestion_charge GROUP BY year ORDER BY year LIMIT 30"
    },
    {
        "question": "Show me greenhouse gas emissions by borough",
        "sql": "SELECT borough, SUM(emissions) as total FROM ghg_emissions GROUP BY borough ORDER BY total DESC LIMIT 15"
    },
]


def _format_few_shots(question: str) -> str:
    """Select relevant few-shot examples based on the question."""
    lower_q = question.lower()
    # Score each example by keyword overlap
    scored = []
    for ex in FEW_SHOT_EXAMPLES:
        score = sum(1 for word in ex["question"].lower().split() if word in lower_q and len(word) > 3)
        scored.append((score, ex))
    # Take top 3 most relevant + always include 1 random for diversity
    scored.sort(key=lambda x: -x[0])
    selected = [ex for _, ex in scored[:3]]
    # Add one more if we don't have 3 relevant ones
    if scored[2][0] == 0:
        selected = [ex for _, ex in scored[:2]] + [FEW_SHOT_EXAMPLES[0]]

    lines = []
    for ex in selected:
        lines.append(f"Q: {ex['question']}\nSQL: {ex['sql']}")
    return "\n\n".join(lines)



async def execute(question: str) -> dict:
    """Generate SQL from natural language and execute on DuckDB."""
    try:
        schema = _get_schema_context()
        few_shots = _format_few_shots(question)
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(schema=schema, few_shots=few_shots)

        llm_client = AsyncOpenAI(
            base_url=settings.vllm_base_url,
            api_key="not-needed",
        )

        response = await llm_client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
            temperature=0.0,
            max_tokens=512,
        )

        sql = response.choices[0].message.content.strip()
        sql = sql.strip("`").removeprefix("sql").strip()
        # Remove markdown code block if present
        if sql.startswith("```"):
            sql = sql.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

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

            # If query returned 0 rows, try a fallback: find relevant table and SELECT *
            if not rows:
                fallback_result = _try_fallback_query(conn, question)
                if fallback_result:
                    return fallback_result

            return {
                "sql": sql,
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "error": None,
            }
        finally:
            conn.close()

    except Exception as e:
        # SQL execution failed — try fallback
        logger.warning(f"Primary SQL failed: {e}")
        try:
            db_path = settings.duckdb_path if hasattr(settings, "duckdb_path") else "data/lucia.duckdb"
            conn = duckdb.connect(db_path, read_only=True)
            fallback_result = _try_fallback_query(conn, question)
            conn.close()
            if fallback_result:
                return fallback_result
        except Exception:
            pass

        return {"sql": sql if "sql" in dir() else "", "columns": [], "rows": [], "row_count": 0, "error": str(e)}


def _try_fallback_query(conn, question: str) -> dict | None:
    """Fallback: find the most relevant table and return top rows."""
    lower_q = question.lower()
    tables = [t[0] for t in conn.execute("SHOW TABLES").fetchall()]

    # Score tables by keyword match
    keyword_map = {
        "traffic": ["traffic_flows", "congestion_charge", "traffic_counts"],
        "vehicle": ["licensed_vehicles", "congestion_charge"],
        "cycle": ["cycle_hires", "cycling_infrastructure", "walking_cycling"],
        "bus": ["buses_by_type", "transport_journeys"],
        "tube": ["underground_temps", "transport_journeys"],
        "transport": ["transport_journeys", "ptals", "traffic_flows"],
        "air": ["air_quality", "laei", "ghg_emissions"],
        "pollution": ["air_quality", "laei", "ghg_emissions"],
        "crime": ["crime"],
        "fire": ["fire_incidents", "fire_mobilisation"],
        "housing": ["affordable_housing", "brownfield"],
        "tree": ["trees"],
        "borough": ["traffic_flows", "licensed_vehicles", "crime", "fly_tipping"],
        "airport": ["airport_passengers"],
        "fly": ["fly_tipping"],
        "solar": ["solar_opportunity"],
        "green": ["green_infra"],
    }

    best_table = None
    for keyword, candidates in keyword_map.items():
        if keyword in lower_q:
            for candidate in candidates:
                if candidate in tables:
                    best_table = candidate
                    break
            if best_table:
                break

    if not best_table and tables:
        # No keyword match — pick first non-system table
        for t in tables:
            if not t.startswith("sys_") and t not in ("chat_messages",):
                best_table = t
                break

    if not best_table:
        return None

    try:
        result = conn.execute(f"SELECT * FROM {best_table} LIMIT 30")
        columns = [desc[0] for desc in result.description]
        rows = [list(row) for row in result.fetchall()]
        total = conn.execute(f"SELECT COUNT(*) FROM {best_table}").fetchone()[0]
        return {
            "sql": f"SELECT * FROM {best_table} LIMIT 30",
            "columns": columns,
            "rows": rows,
            "row_count": total,
            "error": None,
            "note": f"Showing data from '{best_table}' table ({total} rows total)",
        }
    except Exception:
        return None
