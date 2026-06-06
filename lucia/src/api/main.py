"""FastAPI application for LUCIA."""

import logging
from contextlib import asynccontextmanager

import duckdb
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from src.api.middleware import RequestLoggingMiddleware
from src.api.routes import chat, metrics, sessions, voice

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — init and teardown."""
    # Startup
    db_path = settings.duckdb_path if hasattr(settings, "duckdb_path") else "data/lucia.duckdb"
    db = duckdb.connect(db_path)

    # Create tables if not exist
    db.execute("""
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY,
            endpoint TEXT,
            method TEXT,
            status_code INTEGER,
            latency_ms FLOAT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            session_id TEXT,
            role TEXT,
            content TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS data_catalog (
            table_name TEXT PRIMARY KEY,
            description TEXT,
            row_count INTEGER,
            last_updated TIMESTAMP
        )
    """)

    app.state.db = db
    logger.info("LUCIA API started, DuckDB initialized")

    yield

    # Shutdown
    db.close()
    logger.info("LUCIA API shutdown, DuckDB closed")


app = FastAPI(
    title="LUCIA API",
    description="London Urban City Intelligence Agent",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middleware
app.add_middleware(RequestLoggingMiddleware)

# Routers
app.include_router(chat.router, tags=["chat"])
app.include_router(voice.router, prefix="/voice", tags=["voice"])
app.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
app.include_router(metrics.router, prefix="/metrics", tags=["metrics"])


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "lucia"}
