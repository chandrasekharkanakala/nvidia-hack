#!/usr/bin/env python3
"""Full ingestion pipeline for Lucia datasets.

Reads from data/raw/*.csv, routes through DuckDB and/or FAISS embedding paths.
Idempotent: skips already-ingested tables.
"""

import os
import sys
import glob
import logging
import hashlib
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import duckdb
import pandas as pd
import numpy as np

# Project paths
PROJECT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_DIR / "data" / "raw"
PROCESSED_DIR = PROJECT_DIR / "data" / "processed"
EMBEDDINGS_DIR = PROJECT_DIR / "data" / "embeddings"
LOG_DIR = PROJECT_DIR / "logs"
DB_PATH = PROJECT_DIR / "data" / "lucia.duckdb"

# Ensure directories exist
for d in [PROCESSED_DIR, EMBEDDINGS_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Logging setup
log_file = LOG_DIR / f"ingest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


class RoutePath(Enum):
    A = "duckdb"        # Structured → DuckDB only
    B = "embed"         # Text → FAISS embeddings only
    AB = "both"         # Both paths


@dataclass
class DatasetConfig:
    filename: str
    table_name: str
    route: RoutePath
    text_columns: list[str]
    description: str


# Dataset registry with routing
DATASET_REGISTRY: list[DatasetConfig] = [
    # Transport (Path A - structured)
    DatasetConfig("congestion_charge_vehicles.csv", "congestion_charge", RoutePath.A, [], "Congestion charge vehicle data"),
    DatasetConfig("public_transport_journeys.csv", "transport_journeys", RoutePath.A, [], "Public transport journey counts"),
    DatasetConfig("cycle_hires.csv", "cycle_hires", RoutePath.A, [], "Santander cycle hire data"),
    DatasetConfig("road_collisions.csv", "road_collisions", RoutePath.AB, ["description", "location"], "Road collision incidents"),
    DatasetConfig("walking_cycling_borough.csv", "walking_cycling", RoutePath.A, [], "Walking and cycling by borough"),
    DatasetConfig("ptals_accessibility.csv", "ptals", RoutePath.A, [], "Public transport accessibility levels"),
    # Energy & Environment (Path A/AB)
    DatasetConfig("road_energy_consumption.csv", "road_energy", RoutePath.A, [], "Road transport energy consumption"),
    DatasetConfig("underground_temperatures.csv", "underground_temps", RoutePath.A, [], "Underground temperature readings"),
    DatasetConfig("buses_by_type.csv", "buses_by_type", RoutePath.A, [], "Bus fleet composition by type"),
    DatasetConfig("air_quality_borough.csv", "air_quality", RoutePath.A, [], "Air quality measurements by borough"),
    DatasetConfig("reservoir_levels.csv", "reservoir_levels", RoutePath.A, [], "Reservoir water levels"),
    DatasetConfig("greenhouse_gas_emissions.csv", "ghg_emissions", RoutePath.A, [], "Greenhouse gas emissions data"),
    # Urban (Path AB - both structured and text)
    DatasetConfig("fly_tipping_incidents.csv", "fly_tipping", RoutePath.AB, ["description", "location"], "Fly-tipping incidents"),
    DatasetConfig("public_realm_trees.csv", "trees", RoutePath.AB, ["species", "location"], "Public realm tree inventory"),
    DatasetConfig("solar_opportunity.csv", "solar_opportunity", RoutePath.A, [], "Solar energy opportunity mapping"),
    DatasetConfig("green_infrastructure.csv", "green_infra", RoutePath.AB, ["description", "name"], "Green infrastructure assets"),
    # Planning (Path AB)
    DatasetConfig("planning_applications.csv", "planning_apps", RoutePath.AB, ["description", "proposal"], "Planning applications"),
    DatasetConfig("brownfield_register.csv", "brownfield", RoutePath.AB, ["site_name", "notes"], "Brownfield land register"),
    DatasetConfig("affordable_housing.csv", "affordable_housing", RoutePath.A, [], "Affordable housing delivery"),
    DatasetConfig("building_stock_model.csv", "building_stock", RoutePath.A, [], "Building stock energy model"),
    # Safety (Path AB)
    DatasetConfig("crime_geographic.csv", "crime", RoutePath.AB, ["description", "location"], "Crime data by geography"),
    DatasetConfig("fire_brigade_incidents.csv", "fire_incidents", RoutePath.AB, ["description", "incident_type"], "Fire brigade incidents"),
    DatasetConfig("fire_brigade_mobilisation.csv", "fire_mobilisation", RoutePath.A, [], "Fire brigade mobilisation times"),
]


def get_file_hash(filepath: Path) -> str:
    """Get MD5 hash of first 10KB for change detection."""
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        h.update(f.read(10240))
    return h.hexdigest()


def table_exists(con: duckdb.DuckDBPyConnection, table_name: str) -> bool:
    """Check if a table already exists in DuckDB."""
    result = con.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
        [table_name],
    ).fetchone()
    return result[0] > 0


def create_system_tables(con: duckdb.DuckDBPyConnection) -> None:
    """Create system tables for tracking metrics, conversations, and catalog."""
    system_tables = {
        "sys_metrics": """
            CREATE TABLE IF NOT EXISTS sys_metrics (
                id INTEGER PRIMARY KEY,
                metric_name VARCHAR NOT NULL,
                metric_value DOUBLE,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata JSON
            )
        """,
        "sys_conversations": """
            CREATE TABLE IF NOT EXISTS sys_conversations (
                id VARCHAR PRIMARY KEY,
                session_id VARCHAR NOT NULL,
                messages JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
        "sys_data_catalog": """
            CREATE TABLE IF NOT EXISTS sys_data_catalog (
                table_name VARCHAR PRIMARY KEY,
                source_file VARCHAR,
                row_count INTEGER,
                column_count INTEGER,
                file_hash VARCHAR,
                ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                route VARCHAR,
                description VARCHAR
            )
        """,
    }

    for name, ddl in system_tables.items():
        if not table_exists(con, name):
            con.execute(ddl)
            logger.info(f"Created system table: {name}")
        else:
            logger.info(f"SKIP: System table {name} already exists")


def ingest_to_duckdb(con: duckdb.DuckDBPyConnection, config: DatasetConfig, df: pd.DataFrame) -> None:
    """Phase 1: Load structured data into DuckDB and export parquet."""
    if table_exists(con, config.table_name):
        logger.info(f"SKIP: Table {config.table_name} already exists in DuckDB")
        return

    logger.info(f"Ingesting {config.table_name} into DuckDB ({len(df)} rows, {len(df.columns)} cols)")
    con.execute(f"CREATE TABLE {config.table_name} AS SELECT * FROM df")

    # Export parquet
    parquet_path = PROCESSED_DIR / f"{config.table_name}.parquet"
    con.execute(f"COPY {config.table_name} TO '{parquet_path}' (FORMAT PARQUET)")
    logger.info(f"Exported parquet: {parquet_path}")

    # Update catalog
    file_hash = get_file_hash(RAW_DIR / config.filename)
    con.execute(
        """INSERT OR REPLACE INTO sys_data_catalog
           (table_name, source_file, row_count, column_count, file_hash, route, description)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        [config.table_name, config.filename, len(df), len(df.columns),
         file_hash, config.route.value, config.description],
    )


def extract_text_chunks(df: pd.DataFrame, text_columns: list[str], table_name: str) -> list[dict]:
    """Extract text chunks from specified columns."""
    chunks = []
    available_cols = [c for c in text_columns if c in df.columns]
    if not available_cols:
        return chunks

    for idx, row in df.iterrows():
        for col in available_cols:
            text = str(row[col]) if pd.notna(row.get(col)) else ""
            if len(text.strip()) > 10:
                chunks.append({
                    "id": f"{table_name}_{idx}_{col}",
                    "text": text.strip(),
                    "source_table": table_name,
                    "source_column": col,
                    "source_row": int(idx),
                })
    return chunks


def embed_chunks(chunks: list[dict]) -> Optional[np.ndarray]:
    """Generate embeddings for text chunks using a simple fallback."""
    if not chunks:
        return None

    try:
        from openai import OpenAI
        client = OpenAI(base_url="http://localhost:8002/v1", api_key="local")
        texts = [c["text"][:512] for c in chunks]
        batch_size = 32
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = client.embeddings.create(model="nvidia/nv-embedqa-e5-v5", input=batch)
            all_embeddings.extend([e.embedding for e in response.data])
        return np.array(all_embeddings, dtype=np.float32)
    except Exception as e:
        logger.warning(f"Embedding service unavailable ({e}), using random vectors for development")
        dim = 4096
        return np.random.randn(len(chunks), dim).astype(np.float32)


def build_faiss_index(table_name: str, chunks: list[dict], embeddings: np.ndarray) -> None:
    """Phase 2: Build FAISS index from embeddings."""
    import faiss

    index_path = EMBEDDINGS_DIR / f"{table_name}.faiss"
    meta_path = EMBEDDINGS_DIR / f"{table_name}_meta.parquet"

    if index_path.exists() and meta_path.exists():
        logger.info(f"SKIP: FAISS index for {table_name} already exists")
        return

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    faiss.normalize_L2(embeddings)
    index.add(embeddings)

    faiss.write_index(index, str(index_path))
    logger.info(f"Built FAISS index: {index_path} ({len(chunks)} vectors, dim={dim})")

    meta_df = pd.DataFrame(chunks)
    meta_df.to_parquet(meta_path, index=False)
    logger.info(f"Saved chunk metadata: {meta_path}")


def run_ingestion() -> None:
    """Main ingestion pipeline."""
    logger.info("=== Lucia Ingestion Pipeline Starting ===")
    logger.info(f"Raw data directory: {RAW_DIR}")
    logger.info(f"Database path: {DB_PATH}")

    csv_files = list(RAW_DIR.glob("*.csv"))
    logger.info(f"Found {len(csv_files)} CSV files in data/raw/")

    if not csv_files:
        logger.warning("No CSV files found. Run scripts/download_data.sh first.")
        return

    con = duckdb.connect(str(DB_PATH))
    create_system_tables(con)

    ingested = 0
    skipped = 0
    failed = 0

    for config in DATASET_REGISTRY:
        filepath = RAW_DIR / config.filename
        if not filepath.exists():
            logger.warning(f"SKIP: {config.filename} not found in data/raw/")
            skipped += 1
            continue

        try:
            df = pd.read_csv(filepath, low_memory=False)
            logger.info(f"Loaded {config.filename}: {len(df)} rows × {len(df.columns)} cols")

            # Phase 1: DuckDB ingestion
            if config.route in (RoutePath.A, RoutePath.AB):
                ingest_to_duckdb(con, config, df)

            # Phase 2: Embedding + FAISS
            if config.route in (RoutePath.B, RoutePath.AB):
                chunks = extract_text_chunks(df, config.text_columns, config.table_name)
                if chunks:
                    logger.info(f"Extracted {len(chunks)} text chunks from {config.table_name}")
                    embeddings = embed_chunks(chunks)
                    if embeddings is not None:
                        build_faiss_index(config.table_name, chunks, embeddings)
                else:
                    logger.info(f"No text chunks extracted from {config.table_name}")

            ingested += 1
        except Exception as e:
            logger.error(f"FAIL: {config.filename} - {e}")
            failed += 1

    # Record ingestion metrics
    con.execute(
        "INSERT INTO sys_metrics (metric_name, metric_value, metadata) VALUES (?, ?, ?)",
        ["ingestion_run", ingested, f'{{"skipped": {skipped}, "failed": {failed}}}'],
    )

    con.close()

    logger.info("")
    logger.info("=== Ingestion Summary ===")
    logger.info(f"Ingested: {ingested} | Skipped: {skipped} | Failed: {failed}")
    logger.info(f"DuckDB: {DB_PATH}")
    logger.info(f"Parquet files: {len(list(PROCESSED_DIR.glob('*.parquet')))}")
    logger.info(f"FAISS indices: {len(list(EMBEDDINGS_DIR.glob('*.faiss')))}")
    logger.info(f"Log: {log_file}")


if __name__ == "__main__":
    run_ingestion()
