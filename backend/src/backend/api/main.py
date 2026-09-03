from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routers import chat, health, recipes, restaurants, stats
from backend.core.config import get_settings
from backend.core.logging import configure_logging
from backend.mcp.client import MCPClient

configure_logging()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """One MCP server subprocess + client connection for the app's lifetime,
    so the RAG embedding models are loaded once at startup rather than cold-
    loaded (with slow HF Hub cache-validation round trips) on every request."""
    async with MCPClient() as client:
        app.state.mcp_client = client
        yield


app = FastAPI(title="Restaurant Recommendation API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(chat.router)
app.include_router(restaurants.router)
app.include_router(recipes.router)
app.include_router(stats.router)


def run() -> None:
    """Entry point for `uv run api` (see pyproject.toml [project.scripts]).

    No --reload: the lifespan spawns an MCP server subprocess, and uvicorn's
    file-watcher reload hangs that subprocess spawn on Windows (the old worker
    silently keeps serving while the new one never finishes starting). Restart
    the process manually after backend code changes instead."""
    import uvicorn

    uvicorn.run("backend.api.main:app", host="0.0.0.0", port=8000)
