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
                col_desc = ", ".join(f"{c[0]} ({c[1]})" for c in cols[:12])
                row_count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                schema_parts.append(f"  {table} [{row_count} rows]: {col_desc}")
            except Exception:
                schema_parts.append(f"  {table}: (schema unavailable)")

        conn.close()
        return "\n".join(schema_parts) if schema_parts else "No tables available."
    except Exception as e:
        logger.warning(f"Could not fetch schema: {e}")
        return "Schema unavailable."


SYSTEM_PROMPT_TEMPLATE = """You are a SQL expert. Generate a DuckDB-compatible SQL query to answer the user's question.

Available tables with columns:
{schema}

Rules:
- Return ONLY the SQL query, no explanation or markdown.
- Use appropriate aggregations, filters, and joins.
- Limit results to 100 rows unless the user asks for more.
- Do not use DROP, DELETE, INSERT, UPDATE, or any DDL statements.
- Use actual column names shown above — do NOT guess column names.
"""


async def execute(question: str) -> dict:
    """Generate SQL from natural language and execute on DuckDB."""
    try:
        schema = _get_schema_context()
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(schema=schema)

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
                "error": None,
            }
        finally:
            conn.close()

    except Exception as e:
        if "sql" in dir() and sql:
            logger.error(f"DuckDB error: {e}")
            return {"sql": sql, "columns": [], "rows": [], "row_count": 0, "error": str(e)}
        logger.exception("SQL query tool failed")
        return {"sql": "", "columns": [], "rows": [], "row_count": 0, "error": str(e)}
