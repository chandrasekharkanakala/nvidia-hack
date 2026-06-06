"""Analyzer tool — statistical analysis, trend detection, and cross-table correlations."""

import logging

import duckdb
from openai import AsyncOpenAI

from config.settings import settings

logger = logging.getLogger(__name__)

ANALYSIS_SYSTEM = """You are a data analyst. Given the user's question and available tables with schemas,
generate a DuckDB SQL query that performs the requested analysis.

You can use:
- JOINs across tables (match on common columns like borough, year, etc.)
- Window functions (LAG, LEAD, RANK, etc.)
- Aggregations with GROUP BY
- CTEs for complex multi-step analysis
- Statistical functions: STDDEV, VARIANCE, CORR, PERCENTILE_CONT

Output ONLY the SQL query, no explanation."""


def _get_schema() -> str:
    """Get table schemas for the analysis prompt."""
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
                schema_parts.append(f"  {table} [{row_count} rows]: {col_desc}")
            except Exception:
                pass
        conn.close()
        return "\n".join(schema_parts)
    except Exception:
        return "Schema unavailable."


async def execute(query: str, analysis_type: str = "auto") -> dict:
    """Perform statistical analysis on the data.

    Params:
        query: Natural language analysis request
        analysis_type: auto, trend, correlation, comparison, outlier

    Returns: {sql: str, columns: list, rows: list, analysis: str, error: str|None}
    """
    try:
        schema = _get_schema()
        system_prompt = f"{ANALYSIS_SYSTEM}\n\nAvailable tables:\n{schema}"

        llm_client = AsyncOpenAI(base_url=settings.vllm_base_url, api_key="not-needed")

        # Generate analytical SQL
        response = await llm_client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Analysis request: {query}\nAnalysis type: {analysis_type}"},
            ],
            temperature=0.2,
            max_tokens=800,
        )

        sql = response.choices[0].message.content.strip()
        sql = sql.strip("`").removeprefix("sql").strip()

        # Safety check
        forbidden = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE", "TRUNCATE"]
        for kw in forbidden:
            if kw in sql.upper():
                return {"sql": sql, "columns": [], "rows": [], "analysis": "", "error": f"Forbidden: {kw}"}

        # Execute
        db_path = settings.duckdb_path if hasattr(settings, "duckdb_path") else "data/lucia.duckdb"
        conn = duckdb.connect(db_path, read_only=True)
        try:
            result = conn.execute(sql)
            columns = [desc[0] for desc in result.description]
            rows = [list(row) for row in result.fetchall()]
        finally:
            conn.close()

        # Generate analysis narrative
        data_summary = f"Query returned {len(rows)} rows with columns: {columns}\n"
        if rows:
            data_summary += f"Sample: {rows[:5]}"

        try:
            analysis_response = await llm_client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": "You are a data analyst. Provide a brief insight from these query results. Be specific about numbers and trends."},
                    {"role": "user", "content": f"Original question: {query}\n\nSQL: {sql}\n\nResults ({len(rows)} rows):\nColumns: {columns}\nData: {rows[:20]}"},
                ],
                temperature=0.3,
                max_tokens=300,
            )
            analysis = analysis_response.choices[0].message.content.strip()
        except Exception:
            analysis = f"Analysis returned {len(rows)} rows across {len(columns)} dimensions."

        return {
            "sql": sql,
            "columns": columns,
            "rows": rows[:50],
            "row_count": len(rows),
            "analysis": analysis,
            "error": None,
        }

    except Exception as e:
        logger.exception("Analysis failed")
        return {
            "sql": sql if "sql" in dir() else "",
            "columns": [],
            "rows": [],
            "row_count": 0,
            "analysis": "",
            "error": str(e),
        }
