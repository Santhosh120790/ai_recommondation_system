from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# repo_root/backend/src/backend/core/config.py -> repo_root
# NOTE: this only holds for the local monorepo layout. In the Docker image,
# WORKDIR is /app and the package lives at /app/src/backend/... (one level
# shallower - no outer repo-root wrapper), so this heuristic resolves to the
# wrong place there. Docker sets DATA_DIR explicitly (see docker-compose.yml)
# to override it; every other data subpath derives from data_dir below so
# that one override is enough.
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
    raw_data_dir: Path | None = None
    processed_data_dir: Path | None = None
    chroma_dir: Path | None = None

    mcp_server_command: str = "python"
    mcp_server_module: str = "backend.mcp.server"

    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @model_validator(mode="after")
    def _derive_data_subpaths(self) -> "Settings":
        """Fill in raw/processed/chroma from data_dir unless explicitly overridden,
        so a single DATA_DIR override (Docker) cascades to all three."""
        if self.raw_data_dir is None:
            self.raw_data_dir = self.data_dir / "raw"
        if self.processed_data_dir is None:
            self.processed_data_dir = self.data_dir / "processed"
        if self.chroma_dir is None:
            self.chroma_dir = self.data_dir / "chroma"
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
