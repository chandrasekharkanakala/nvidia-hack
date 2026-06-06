"""Ingestion module — Multi-format data loading into DuckDB and FAISS."""

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


async def load_xlsx_to_duckdb(filepath: str | Path, table_name: str, db: duckdb.DuckDBPyConnection) -> int:
    """Load an Excel (.xlsx/.xls) file into DuckDB. Returns row count."""
    try:
        import pandas as pd

        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Excel file not found: {filepath}")

        df = pd.read_excel(filepath)
        # Sanitize column names for SQL
        df.columns = [c.strip().replace(" ", "_").replace("-", "_").lower() for c in df.columns]

        db.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM df")
        row_count = db.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        logger.info(f"Loaded {row_count} rows from {filepath} into '{table_name}'")
        return row_count

    except Exception as e:
        logger.exception(f"Failed to load Excel '{filepath}' into '{table_name}'")
        raise


async def load_json_to_duckdb(filepath: str | Path, table_name: str, db: duckdb.DuckDBPyConnection) -> int:
    """Load a JSON file into DuckDB. Handles both array-of-objects and nested JSON."""
    try:
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"JSON file not found: {filepath}")

        # Try DuckDB's native JSON reader first
        try:
            db.execute(f"""
                CREATE OR REPLACE TABLE {table_name} AS
                SELECT * FROM read_json_auto('{filepath}')
            """)
        except Exception:
            # Fallback: load with pandas for complex/nested JSON
            import pandas as pd
            df = pd.read_json(filepath)
            df.columns = [c.strip().replace(" ", "_").replace("-", "_").lower() for c in df.columns]
            db.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM df")

        row_count = db.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        logger.info(f"Loaded {row_count} rows from {filepath} into '{table_name}'")
        return row_count

    except Exception as e:
        logger.exception(f"Failed to load JSON '{filepath}' into '{table_name}'")
        raise


async def load_pdf_to_text(filepath: str | Path) -> str:
    """Extract text from a PDF file for embedding/RAG."""
    try:
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"PDF file not found: {filepath}")

        try:
            import pymupdf
            doc = pymupdf.open(str(filepath))
            text = ""
            for page in doc:
                text += page.get_text() + "\n"
            doc.close()
        except ImportError:
            # Fallback to pypdf
            from pypdf import PdfReader
            reader = PdfReader(str(filepath))
            text = ""
            for page in reader.pages:
                text += (page.extract_text() or "") + "\n"

        logger.info(f"Extracted {len(text)} chars from PDF: {filepath.name}")
        return text.strip()

    except Exception as e:
        logger.exception(f"Failed to extract text from PDF '{filepath}'")
        raise


async def load_image_description(filepath: str | Path) -> str:
    """Get text description of an image using the vision model (for embedding)."""
    try:
        import base64
        import httpx

        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Image not found: {filepath}")

        suffix = filepath.suffix.lower()
        mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}
        mime = mime_map.get(suffix, "image/png")

        image_b64 = base64.b64encode(filepath.read_bytes()).decode()

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.vision_base_url}/chat/completions",
                json={
                    "model": settings.vision_model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Describe this image in detail for a London urban planning context."},
                                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_b64}"}},
                            ],
                        }
                    ],
                    "max_tokens": 500,
                },
            )
            response.raise_for_status()
            description = response.json()["choices"][0]["message"]["content"]

        logger.info(f"Got description for image: {filepath.name} ({len(description)} chars)")
        return description

    except Exception as e:
        logger.exception(f"Failed to describe image '{filepath}'")
        raise


async def ingest_file(filepath: str | Path, table_name: str | None = None, db: duckdb.DuckDBPyConnection | None = None) -> dict:
    """Auto-detect file type and ingest appropriately.
    
    - CSV/XLSX/JSON → DuckDB (structured data for sql_query tool)
    - PDF/Images → Text extraction → FAISS embedding (for rag_search tool)
    
    Returns: {"type": "structured"|"text", "table": str|None, "rows": int|None, "text_length": int|None}
    """
    filepath = Path(filepath)
    suffix = filepath.suffix.lower()

    if table_name is None:
        table_name = filepath.stem.replace(" ", "_").replace("-", "_").lower()

    # Structured data → DuckDB
    if suffix == ".csv":
        if db is None:
            db = duckdb.connect(settings.duckdb_path)
        rows = await load_csv_to_duckdb(filepath, table_name, db)
        return {"type": "structured", "table": table_name, "rows": rows, "text_length": None}

    elif suffix in (".xlsx", ".xls"):
        if db is None:
            db = duckdb.connect(settings.duckdb_path)
        rows = await load_xlsx_to_duckdb(filepath, table_name, db)
        return {"type": "structured", "table": table_name, "rows": rows, "text_length": None}

    elif suffix in (".json", ".geojson"):
        if db is None:
            db = duckdb.connect(settings.duckdb_path)
        rows = await load_json_to_duckdb(filepath, table_name, db)
        return {"type": "structured", "table": table_name, "rows": rows, "text_length": None}

    # Text/context → FAISS embedding
    elif suffix == ".pdf":
        text = await load_pdf_to_text(filepath)
        return {"type": "text", "table": None, "rows": None, "text_length": len(text), "text": text}

    elif suffix in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
        description = await load_image_description(filepath)
        return {"type": "text", "table": None, "rows": None, "text_length": len(description), "text": description}

    else:
        raise ValueError(f"Unsupported file type: {suffix}")


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
