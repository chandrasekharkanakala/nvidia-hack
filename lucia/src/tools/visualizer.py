"""Visualization tool — generates charts from query results using matplotlib."""

import base64
import io
import logging

import duckdb

from config.settings import settings

logger = logging.getLogger(__name__)

CHART_TYPES = {
    "bar": "bar chart",
    "line": "line chart",
    "pie": "pie chart",
    "heatmap": "heatmap",
    "scatter": "scatter plot",
    "histogram": "histogram",
}


def _infer_chart_type(sql: str, columns: list[str], rows: list) -> str:
    """Infer best chart type from data shape."""
    if len(columns) == 2 and len(rows) <= 20:
        # Category + value → bar or pie
        return "pie" if len(rows) <= 8 else "bar"
    elif len(columns) >= 2 and any(k in columns[0].lower() for k in ("year", "month", "date", "quarter")):
        return "line"
    elif len(columns) == 3:
        return "bar"
    return "bar"


async def execute(query: str, chart_type: str | None = None) -> dict:
    """Generate a chart from data. Runs SQL, then plots with matplotlib.

    Params:
        query: Natural language or SQL query to visualize
        chart_type: Optional - bar, line, pie, heatmap, scatter, histogram

    Returns: {chart_base64: str, chart_type: str, sql: str, error: str|None}
    """
    try:
        from tools.sql_query import execute as sql_execute

        # First, get the data via sql_query tool
        sql_result = await sql_execute(query)

        if sql_result.get("error") or sql_result["row_count"] == 0:
            return {
                "chart_base64": None,
                "chart_type": None,
                "sql": sql_result.get("sql", ""),
                "description": "No data available to visualize.",
                "error": sql_result.get("error") or "No rows returned",
            }

        columns = sql_result["columns"]
        rows = sql_result["rows"]

        # Infer chart type if not specified
        if not chart_type:
            chart_type = _infer_chart_type(sql_result["sql"], columns, rows)

        # Generate chart
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(10, 6))
        fig.patch.set_facecolor("#1a1a2e")
        ax.set_facecolor("#16213e")
        ax.tick_params(colors="white")
        ax.xaxis.label.set_color("white")
        ax.yaxis.label.set_color("white")
        ax.title.set_color("white")
        for spine in ax.spines.values():
            spine.set_color("#333")

        if chart_type == "pie" and len(columns) >= 2:
            labels = [str(r[0]) for r in rows[:10]]
            values = [float(r[1]) if r[1] else 0 for r in rows[:10]]
            ax.pie(values, labels=labels, autopct="%1.1f%%", colors=plt.cm.Set3.colors)
            ax.set_title(f"{columns[1]} by {columns[0]}")

        elif chart_type == "line" and len(columns) >= 2:
            x = [str(r[0]) for r in rows]
            y = [float(r[1]) if r[1] else 0 for r in rows]
            ax.plot(x, y, color="#00d4aa", linewidth=2, marker="o", markersize=4)
            ax.set_xlabel(columns[0])
            ax.set_ylabel(columns[1])
            ax.set_title(f"{columns[1]} over {columns[0]}")
            plt.xticks(rotation=45, ha="right")

        elif chart_type == "scatter" and len(columns) >= 2:
            x = [float(r[0]) if r[0] else 0 for r in rows]
            y = [float(r[1]) if r[1] else 0 for r in rows]
            ax.scatter(x, y, color="#00d4aa", alpha=0.7)
            ax.set_xlabel(columns[0])
            ax.set_ylabel(columns[1])
            ax.set_title(f"{columns[1]} vs {columns[0]}")

        else:  # bar chart (default)
            labels = [str(r[0])[:20] for r in rows[:15]]
            values = [float(r[1]) if r[1] else 0 for r in rows[:15]]
            bars = ax.barh(labels, values, color="#00d4aa")
            ax.set_xlabel(columns[1] if len(columns) > 1 else "Value")
            ax.set_title(f"{columns[1] if len(columns) > 1 else 'Value'} by {columns[0]}")

        plt.tight_layout()

        # Convert to base64
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        chart_b64 = base64.b64encode(buf.read()).decode("utf-8")

        description = f"Generated {chart_type} chart with {len(rows)} data points. X-axis: {columns[0]}, Y-axis: {columns[1] if len(columns) > 1 else 'count'}"

        return {
            "chart_base64": chart_b64,
            "chart_type": chart_type,
            "sql": sql_result["sql"],
            "columns": columns,
            "row_count": len(rows),
            "description": description,
            "error": None,
        }

    except Exception as e:
        logger.exception("Visualization failed")
        return {
            "chart_base64": None,
            "chart_type": None,
            "sql": "",
            "description": "",
            "error": str(e),
        }
