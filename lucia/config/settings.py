"""LUCIA — Application Settings. Single source of truth for all configuration.
All values read from .env file (LUCIA_ prefix). Never hardcode secrets."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ElevenLabs (Voice)
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"
    elevenlabs_model_stt: str = "scribe_v1"
    elevenlabs_model_tts: str = "eleven_multilingual_v2"

    # Model serving endpoints
    vllm_base_url: str = "http://localhost:8001/v1"
    embed_base_url: str = "http://localhost:8002/v1"
    vision_base_url: str = "http://localhost:8003/v1"
    nemoclaw_url: str = "http://localhost:8080"

    # Model names
    llm_model: str = "nvidia/Nemotron-Mini-4B-Instruct"
    safety_model: str = "nemotron-content-safety-4b"
    embed_model: str = "intfloat/e5-large-v2"
    vision_model: str = "neva-7b"

    # Data paths
    data_dir: str = "./data"
    raw_data_dir: str = "./data/raw"
    processed_data_dir: str = "./data/processed"
    embeddings_dir: str = "./data/embeddings"
    duckdb_path: str = "./data/lucia.duckdb"
    faiss_index_path: str = "./data/embeddings/lucia.faiss"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Agent
    light_max_steps: int = 3
    deep_max_steps: int = 5
    light_temperature: float = 0.3
    deep_temperature: float = 0.7
    tool_timeout_seconds: int = 30

    # FAISS
    embedding_dim: int = 4096
    faiss_top_k: int = 10

    # Guardrails
    guardrails_config_path: str = "./config/guardrails"

    # External APIs (optional)
    tfl_app_key: str = ""
    openweather_api_key: str = ""

    model_config = {"env_prefix": "LUCIA_", "env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
