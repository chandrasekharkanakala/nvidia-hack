#!/usr/bin/env python3
"""Full ingestion pipeline for Lucia datasets.

Reads from data/raw/*.{csv,xlsx,xls,json,pdf}, routes through DuckDB and/or FAISS embedding paths.

INCREMENTAL MODE (default):
- DuckDB: UPSERT new rows (detect changes via file hash). Replaces table only if file changed.
- FAISS: Always rebuilds index from ALL embedded chunks (append new, keep old).
- Parquet metadata tracks per-file hashes for deduplication.

FORCE MODE (--force):
- Drops and recreates all tables and indices from scratch.
"""

import os
import sys
import logging
import hashlib
import json
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
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
HASH_REGISTRY = PROCESSED_DIR / "file_hashes.json"

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

# Suppress noisy HTTP debug logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

# Capture unhandled exceptions into the log
def _exception_handler(exc_type, exc_value, exc_tb):
    logger.error("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))

sys.excepthook = _exception_handler


class RoutePath(Enum):
    A = "duckdb"        # Structured → DuckDB only
    B = "embed"         # Text → FAISS embeddings only
    AB = "both"         # Both paths


@dataclass
class DatasetConfig:
    filename: str
    table_name: str
    route: RoutePath
    text_columns: list[str] = field(default_factory=list)
    description: str = ""


# Dataset registry with routing
# Filenames MUST match what's placed in data/raw/
DATASET_REGISTRY: list[DatasetConfig] = [
    # Transport — Traffic & Flow
    DatasetConfig("traffic_flows_borough.csv", "traffic_flows", RoutePath.A, [], "Traffic flows by borough"),
    DatasetConfig("traffic_counts_baseline.csv", "traffic_counts_baseline", RoutePath.A, [], "Baseline & post-scheme traffic counts"),
    DatasetConfig("congestion_charge.csv", "congestion_charge", RoutePath.A, [], "Congestion charge vehicle data"),
    DatasetConfig("licensed_vehicles.csv", "licensed_vehicles", RoutePath.A, [], "Licensed vehicles by type and borough"),
    # Transport — Public Transport & Cycling
    DatasetConfig("public_transport_journeys.csv", "transport_journeys", RoutePath.A, [], "Public transport journey counts"),
    DatasetConfig("cycle_hires.xlsx", "cycle_hires", RoutePath.A, [], "Santander cycle hire data"),
    DatasetConfig("cycling_infrastructure.csv", "cycling_infrastructure", RoutePath.AB, ["description", "feature"], "Cycling infrastructure database"),
    DatasetConfig("walking_cycling_borough.csv", "walking_cycling", RoutePath.A, [], "Walking and cycling by borough"),
    DatasetConfig("ptals.csv", "ptals", RoutePath.A, [], "Public transport accessibility levels"),
    DatasetConfig("airport_passengers.csv", "airport_passengers", RoutePath.A, [], "Busiest airports by passenger traffic"),
    DatasetConfig("buses_by_type.csv", "buses_by_type", RoutePath.A, [], "Bus fleet composition by type"),
    # Transport — Other
    DatasetConfig("road_collisions.csv", "road_collisions", RoutePath.AB, ["description", "location"], "Road safety collisions"),
    DatasetConfig("road_energy_consumption.csv", "road_energy", RoutePath.A, [], "Road transport energy consumption"),
    DatasetConfig("underground_temps.csv", "underground_temps", RoutePath.A, [], "Underground temperature readings"),
    # Environment & Air Quality
    DatasetConfig("air_quality_gla.csv", "air_quality_gla", RoutePath.AB, ["summary", "notes"], "GLA air quality data"),
    DatasetConfig("london_air_kcl.csv", "london_air_kcl", RoutePath.A, [], "London Air KCL network readings"),
    DatasetConfig("laei_borough_aq.csv", "laei_borough_aq", RoutePath.AB, ["methodology", "notes"], "LAEI borough air quality"),
    DatasetConfig("laei_emissions.csv", "laei_emissions", RoutePath.A, [], "Atmospheric emissions inventory"),
    DatasetConfig("reservoir_levels.csv", "reservoir_levels", RoutePath.A, [], "Reservoir water levels"),
    DatasetConfig("leggi_emissions.csv", "ghg_emissions", RoutePath.AB, ["notes", "policy_context"], "Greenhouse gas emissions data"),
    DatasetConfig("fly_tipping.csv", "fly_tipping", RoutePath.A, [], "Fly-tipping incidents"),
    DatasetConfig("green_infrastructure.csv", "green_infra", RoutePath.AB, ["description", "name"], "Green infrastructure assets"),
    DatasetConfig("public_trees.csv", "trees", RoutePath.AB, ["species", "location"], "Public realm tree inventory"),
    DatasetConfig("solar_opportunity.csv", "solar_opportunity", RoutePath.A, [], "Solar energy opportunity mapping"),
    # Planning & Housing
    DatasetConfig("planning_applications.csv", "planning_apps", RoutePath.AB, ["description", "decision_reason"], "Planning applications"),
    DatasetConfig("brownfield_register.csv", "brownfield", RoutePath.AB, ["site_name", "notes"], "Brownfield land register"),
    DatasetConfig("affordable_housing.csv", "affordable_housing", RoutePath.A, [], "Affordable housing delivery"),
    DatasetConfig("building_stock.csv", "building_stock", RoutePath.A, [], "Building stock energy model"),
    # Safety & Emergency
    DatasetConfig("mps_crime.csv", "crime", RoutePath.AB, ["description", "location"], "Crime data by geography"),
    DatasetConfig("fire_incidents.csv", "fire_incidents", RoutePath.AB, ["description", "incident_type"], "Fire brigade incidents"),
    DatasetConfig("fire_mobilisation.csv", "fire_mobilisation", RoutePath.A, [], "Fire brigade mobilisation times"),
]


def get_file_hash(filepath: Path) -> str:
    """Get SHA256 hash of full file for change detection."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def load_hash_registry() -> dict:
    """Load previously recorded file hashes."""
    if HASH_REGISTRY.exists():
        return json.loads(HASH_REGISTRY.read_text())
    return {}


def save_hash_registry(registry: dict) -> None:
    """Save file hash registry."""
    HASH_REGISTRY.write_text(json.dumps(registry, indent=2))


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
        con.execute(ddl)


def load_file_to_df(filepath: Path) -> pd.DataFrame:
    """Load any supported file format into a DataFrame."""
    suffix = filepath.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(filepath, low_memory=False)
    elif suffix in (".xlsx", ".xls"):
        return pd.read_excel(filepath)
    elif suffix in (".json", ".geojson"):
        return pd.read_json(filepath)
    else:
        raise ValueError(f"Unsupported file type for DuckDB: {suffix}")


def ingest_to_duckdb(con: duckdb.DuckDBPyConnection, config: DatasetConfig, df: pd.DataFrame, force: bool = False) -> bool:
    """Load structured data into DuckDB. Returns True if table was updated."""
    if table_exists(con, config.table_name) and not force:
        # Table exists — drop and replace with new data (file hash already confirmed changed)
        con.execute(f"DROP TABLE IF EXISTS {config.table_name}")
        logger.info(f"Dropping old table {config.table_name} for re-ingestion")

    logger.info(f"Ingesting {config.table_name} into DuckDB ({len(df)} rows, {len(df.columns)} cols)")

    # Sanitize column names
    df.columns = [c.strip().replace(" ", "_").replace("-", "_").replace("(", "").replace(")", "").lower() for c in df.columns]
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
    return True


def extract_text_chunks(df: pd.DataFrame, text_columns: list[str], table_name: str) -> list[dict]:
    """Extract text chunks from specified columns."""
    chunks = []
    available_cols = [c for c in text_columns if c in df.columns]
    if not available_cols:
        # Try sanitized column names
        sanitized_map = {c.strip().replace(" ", "_").replace("-", "_").lower(): c for c in df.columns}
        available_cols = [sanitized_map[tc] for tc in text_columns if tc in sanitized_map]

    if not available_cols:
        return chunks

    for idx, row in df.iterrows():
        for col in available_cols:
            text = str(row[col]) if pd.notna(row.get(col)) else ""
            if len(text.strip()) > 10:
                chunks.append({
                    "id": f"{table_name}_{idx}_{col}",
                    "text": text.strip()[:512],
                    "source_table": table_name,
                    "source_column": col,
                    "source_row": int(idx),
                })
    return chunks


def embed_chunks(chunks: list[dict]) -> Optional[np.ndarray]:
    """Generate embeddings for text chunks. Returns None if service unavailable."""
    if not chunks:
        return None

    try:
        from openai import OpenAI
        client = OpenAI(base_url="http://localhost:8002/v1", api_key="local")
        texts = [c["text"] for c in chunks]
        batch_size = 32
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = client.embeddings.create(model="intfloat/e5-large-v2", input=batch)
            all_embeddings.extend([e.embedding for e in response.data])
            if (i + batch_size) % 320 == 0:
                logger.info(f"  Embedded {min(i + batch_size, len(texts))}/{len(texts)} chunks...")
        return np.array(all_embeddings, dtype=np.float32)
    except Exception as e:
        logger.warning(f"Embedding failed: {e}")
        return None


def rebuild_faiss_index(all_chunks: list[dict], all_embeddings: np.ndarray, index_name: str = "lucia") -> None:
    """Build a SINGLE unified FAISS index from all embedded chunks.

    Always rebuilds from scratch to ensure consistency after new data is added.
    """
    import faiss

    index_path = EMBEDDINGS_DIR / f"{index_name}.faiss"
    meta_path = EMBEDDINGS_DIR / f"{index_name}_meta.parquet"

    dim = all_embeddings.shape[1]
    n_vectors = all_embeddings.shape[0]

    # Normalize for cosine similarity
    faiss.normalize_L2(all_embeddings)

    # Choose index type based on size
    if n_vectors < 1000:
        index = faiss.IndexFlatIP(dim)
        index.add(all_embeddings)
    else:
        n_clusters = min(int(np.sqrt(n_vectors)), max(1, n_vectors // 39))
        n_clusters = max(1, n_clusters)
        quantizer = faiss.IndexFlatIP(dim)
        index = faiss.IndexIVFFlat(quantizer, dim, n_clusters)
        # Try GPU
        try:
            res = faiss.StandardGpuResources()
            gpu_index = faiss.index_cpu_to_gpu(res, 0, index)
            gpu_index.train(all_embeddings)
            gpu_index.add(all_embeddings)
            index = faiss.index_gpu_to_cpu(gpu_index)
            logger.info(f"Built GPU FAISS index: {n_vectors} vectors, dim={dim}, {n_clusters} clusters")
        except Exception:
            index.train(all_embeddings)
            index.add(all_embeddings)
            logger.info(f"Built CPU FAISS index: {n_vectors} vectors, dim={dim}, {n_clusters} clusters")

    faiss.write_index(index, str(index_path))
    logger.info(f"Saved FAISS index: {index_path}")

    # Save metadata
    meta_df = pd.DataFrame(all_chunks)
    meta_df.to_parquet(meta_path, index=False)
    logger.info(f"Saved chunk metadata: {meta_path} ({len(all_chunks)} entries)")


def run_ingestion(force: bool = False) -> None:
    """Main ingestion pipeline.

    INCREMENTAL (default): Only re-ingests files whose hash has changed.
    DuckDB tables are replaced. FAISS is rebuilt with all chunks (old + new).

    FORCE (--force): Re-ingests everything from scratch.
    """
    logger.info("=== Lucia Ingestion Pipeline Starting ===")
    logger.info(f"Mode: {'FORCE (full rebuild)' if force else 'INCREMENTAL (changed files only)'}")
    logger.info(f"Raw data directory: {RAW_DIR}")
    logger.info(f"Database path: {DB_PATH}")

    # Discover all data files
    supported_exts = ("*.csv", "*.xlsx", "*.xls", "*.json", "*.geojson")
    raw_files = []
    for ext in supported_exts:
        raw_files.extend(RAW_DIR.glob(ext))
    logger.info(f"Found {len(raw_files)} data files in data/raw/")

    if not raw_files:
        logger.warning("No data files found. Download data to data/raw/ first.")
        return

    # Load hash registry for deduplication
    hash_registry = load_hash_registry() if not force else {}

    con = duckdb.connect(str(DB_PATH))
    create_system_tables(con)

    # --- Check if embedding service is available ---
    import socket
    embedding_available = False
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    try:
        sock.connect(("localhost", 8002))
        sock.close()
        embedding_available = True
        logger.info("Embedding service detected on :8002 ✓")
    except (ConnectionRefusedError, OSError):
        sock.close()
        logger.info("Embedding service not running on :8002 — skipping embeddings")
        logger.info("  (Run 'bash scripts/start.sh' first, then re-run ingest to build FAISS index)")

    ingested = 0
    skipped = 0
    failed = 0
    all_chunks: list[dict] = []

    # Load existing chunks if doing incremental and embedding available
    existing_meta_path = EMBEDDINGS_DIR / "lucia_meta.parquet"
    if not force and existing_meta_path.exists() and embedding_available:
        try:
            existing_meta = pd.read_parquet(existing_meta_path)
            all_chunks = existing_meta.to_dict("records")
            logger.info(f"Loaded {len(all_chunks)} existing chunks from previous index")
        except Exception:
            pass

    new_chunks_added = False

    for config in DATASET_REGISTRY:
        filepath = RAW_DIR / config.filename
        if not filepath.exists():
            # Try alternate extensions
            found = False
            stem = filepath.stem
            for ext in [".csv", ".xlsx", ".xls", ".json"]:
                alt_path = RAW_DIR / f"{stem}{ext}"
                if alt_path.exists():
                    filepath = alt_path
                    found = True
                    break
            if not found:
                logger.debug(f"SKIP: {config.filename} not in data/raw/")
                skipped += 1
                continue

        # Check if file has changed (deduplication)
        current_hash = get_file_hash(filepath)
        if not force and hash_registry.get(config.filename) == current_hash:
            logger.info(f"SKIP (unchanged): {config.filename}")
            skipped += 1
            continue

        try:
            df = load_file_to_df(filepath)
            logger.info(f"Loaded {filepath.name}: {len(df)} rows × {len(df.columns)} cols")

            # Phase 1: DuckDB ingestion
            if config.route in (RoutePath.A, RoutePath.AB):
                ingest_to_duckdb(con, config, df, force=force)

            # Phase 2: Extract text chunks for embedding
            if embedding_available and config.route in (RoutePath.B, RoutePath.AB):
                chunks = extract_text_chunks(df, config.text_columns, config.table_name)
                if chunks:
                    logger.info(f"Extracted {len(chunks)} text chunks from {config.table_name}")
                    # Remove old chunks from same table (replace, don't duplicate)
                    all_chunks = [c for c in all_chunks if c.get("source_table") != config.table_name]
                    all_chunks.extend(chunks)
                    new_chunks_added = True

            # Update hash registry
            hash_registry[config.filename] = current_hash
            ingested += 1

        except Exception as e:
            logger.error(f"FAIL: {config.filename} - {e}", exc_info=True)
            failed += 1

    # Also ingest any unregistered files found in raw/
    registered_filenames = {c.filename for c in DATASET_REGISTRY}
    for filepath in raw_files:
        if filepath.name in registered_filenames:
            continue
        current_hash = get_file_hash(filepath)
        if not force and hash_registry.get(filepath.name) == current_hash:
            continue

        try:
            table_name = filepath.stem.replace(" ", "_").replace("-", "_").lower()
            df = load_file_to_df(filepath)
            logger.info(f"[Unregistered] Loaded {filepath.name}: {len(df)} rows × {len(df.columns)} cols")

            # Sanitize and ingest to DuckDB
            df.columns = [c.strip().replace(" ", "_").replace("-", "_").replace("(", "").replace(")", "").lower() for c in df.columns]
            if table_exists(con, table_name):
                con.execute(f"DROP TABLE IF EXISTS {table_name}")
            con.execute(f"CREATE TABLE {table_name} AS SELECT * FROM df")

            parquet_path = PROCESSED_DIR / f"{table_name}.parquet"
            con.execute(f"COPY {table_name} TO '{parquet_path}' (FORMAT PARQUET)")

            hash_registry[filepath.name] = current_hash
            ingested += 1
            logger.info(f"[Unregistered] Ingested {filepath.name} → {table_name}")
        except Exception as e:
            logger.warning(f"[Unregistered] SKIP {filepath.name}: {e}")

    # Phase 3: Rebuild FAISS index if chunks changed
    if embedding_available and new_chunks_added and all_chunks:
        logger.info(f"Rebuilding FAISS index with {len(all_chunks)} total chunks...")
        embeddings = embed_chunks(all_chunks)
        if embeddings is not None:
            rebuild_faiss_index(all_chunks, embeddings)
    elif embedding_available and not new_chunks_added:
        logger.info("No new text chunks — FAISS index unchanged")

    # Save hash registry
    save_hash_registry(hash_registry)

    # Record ingestion metrics
    next_id = con.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM sys_metrics").fetchone()[0]
    con.execute(
        "INSERT INTO sys_metrics (id, metric_name, metric_value, metadata) VALUES (?, ?, ?, ?)",
        [next_id, "ingestion_run", ingested, f'{{"skipped": {skipped}, "failed": {failed}, "mode": "{"force" if force else "incremental"}"}}'],
    )

    con.close()

    logger.info("")
    logger.info("=== Ingestion Summary ===")
    logger.info(f"Mode: {'FORCE' if force else 'INCREMENTAL'}")
    logger.info(f"Ingested: {ingested} | Skipped (unchanged): {skipped} | Failed: {failed}")
    logger.info(f"DuckDB: {DB_PATH}")
    logger.info(f"Parquet files: {len(list(PROCESSED_DIR.glob('*.parquet')))}")
    logger.info(f"FAISS index vectors: {len(all_chunks)}")
    logger.info(f"Log: {log_file}")


if __name__ == "__main__":
    force_mode = "--force" in sys.argv
    run_ingestion(force=force_mode)
