"""Ingestion module — CSV loading and Parquet export."""

import logging
from pathlib import Path

import duckdb

from config.settings import settings

logger = logging.getLogger(__name__)


async def load_csv_to_duckdb(filepath: str | Path, table_name: str, db: duckdb.DuckDBPyConnection) -> int:
    """Load a CSV file into DuckDB. Returns row count."""
    try:
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"CSV file not found: {filepath}")

        db.execute(f"""
            CREATE OR REPLACE TABLE {table_name} AS
            SELECT * FROM read_csv_auto('{filepath}', header=true)
        """)

        row_count = db.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        logger.info(f"Loaded {row_count} rows from {filepath} into '{table_name}'")
        return row_count

    except Exception as e:
        logger.exception(f"Failed to load CSV '{filepath}' into '{table_name}'")
        raise


async def export_parquet(table_name: str, db: duckdb.DuckDBPyConnection) -> Path:
    """Export a DuckDB table to Parquet format. Returns output path."""
    try:
        output_dir = Path(settings.data_dir if hasattr(settings, "data_dir") else "data") / "parquet"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{table_name}.parquet"

        db.execute(f"COPY {table_name} TO '{output_path}' (FORMAT PARQUET)")
        logger.info(f"Exported '{table_name}' to {output_path}")
        return output_path

    except Exception as e:
        logger.exception(f"Failed to export '{table_name}' to Parquet")
        raise
