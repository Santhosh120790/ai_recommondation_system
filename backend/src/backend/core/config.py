from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# repo_root/backend/src/backend/core/config.py -> repo_root
REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_DATA_DIR = REPO_ROOT / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"
    log_level: str = "INFO"

    # AICredits gateway: OpenAI-compatible base_url + key, model name selects
    # the underlying provider (GPT vs Claude).
    aicredits_base_url: str
    aicredits_api_key: str
    aicredits_text_model: str = "gpt-4o-mini"
    aicredits_vision_model: str = "gpt-4o-mini"
    aicredits_agent_model: str = "gpt-4o-mini"

    data_dir: Path = DEFAULT_DATA_DIR
    raw_data_dir: Path = DEFAULT_DATA_DIR / "raw"
    processed_data_dir: Path = DEFAULT_DATA_DIR / "processed"
    chroma_dir: Path = DEFAULT_DATA_DIR / "chroma"

    mcp_server_command: str = "python"
    mcp_server_module: str = "backend.mcp.server"

    cors_origins: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
