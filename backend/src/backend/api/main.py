from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from langgraph.checkpoint.memory import InMemorySaver

from backend.agents.graph import build_graph
from backend.api.routers import chat, health, recipes, restaurants, stats
from backend.core.config import get_settings
from backend.core.llm import get_agent_model
from backend.core.logging import configure_logging
from backend.mcp.client import MCPClient

configure_logging()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """One MCP server subprocess + client connection, and one compiled agent
    graph, for the app's lifetime:
    - the RAG embedding models get loaded once at startup rather than cold-
      loaded (with slow HF Hub cache-validation round trips) on every request
    - the graph's checkpointer (conversation memory) must be the same object
      across requests to actually persist anything - building a fresh graph
      per request would give every chat message its own throwaway memory."""
    async with MCPClient() as client:
        app.state.mcp_client = client
        app.state.agent_graph = build_graph(client, get_agent_model(), checkpointer=InMemorySaver())
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

# Serve the recipe dataset's photos (data/raw/images/recipeN.png) so the frontend
# can render them directly by the image_path each Recipe already carries.
_images_dir = settings.raw_data_dir / "images" if settings.raw_data_dir else None
if _images_dir and _images_dir.is_dir():
    app.mount("/images", StaticFiles(directory=str(_images_dir)), name="images")


def run() -> None:
    """Entry point for `uv run api` (see pyproject.toml [project.scripts]).

    No --reload: the lifespan spawns an MCP server subprocess, and uvicorn's
    file-watcher reload hangs that subprocess spawn on Windows (the old worker
    silently keeps serving while the new one never finishes starting). Restart
    the process manually after backend code changes instead."""
    import uvicorn

    uvicorn.run("backend.api.main:app", host="0.0.0.0", port=8000)
