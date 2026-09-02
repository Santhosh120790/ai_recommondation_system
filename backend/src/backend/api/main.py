from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routers import health
from backend.core.config import get_settings
from backend.core.logging import configure_logging

configure_logging()
settings = get_settings()

app = FastAPI(title="Restaurant Recommendation API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)


def run() -> None:
    """Entry point for `uv run api` (see pyproject.toml [project.scripts])."""
    import uvicorn

    uvicorn.run("backend.api.main:app", host="0.0.0.0", port=8000, reload=True)
