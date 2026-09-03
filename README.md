# Connoisseur — Multimodal AI Restaurant & Recipe Recommendation Platform

An end-to-end GenAI application: LLM-based data structuring, multimodal RAG
(text + image), a multi-agent recommendation engine built on LangGraph, and a
Model Context Protocol (MCP) server/client as the agents' tool-access layer —
fronted by a Next.js dashboard/chat/management UI.

## Architecture

```
apps/web/      Next.js frontend (dashboard, streaming chat, restaurant CRUD)
backend/       Python backend (uv-managed), single package with multiple entry points:
  core/            settings, AICredits LLM client factory, logging
  data_pipeline/   LLM text structuring + vision captioning + CRUD repository
  rag/             MiniLM/CLIP embeddings, Chroma vector store, retrieval, late-fusion ranking
  agents/          LangGraph multi-agent recommendation workflow
  mcp/             MCP server (tools/resources) + client (roots/sampling callbacks)
  api/             FastAPI app - REST + SSE-streamed chat, holds the long-lived MCP client
  cli/             Typer CLI mirroring every pipeline step
data/            raw/ (fetched), processed/ (generated), chroma/ (vector store) - all gitignored
```

The FastAPI backend is the MCP *host*: it holds one persistent MCP client
connection (spawned once at startup, not per-request) to an MCP *server*
subprocess that exposes the restaurant/recipe data and RAG retrieval as
discoverable tools. The LangGraph agent graph calls those tools through the
MCP client rather than importing the RAG/data modules directly, so MCP is the
actual data/tool access layer for the agents.

## Quick start (Docker)

```bash
cp backend/.env.example backend/.env   # fill in AICREDITS_BASE_URL / AICREDITS_API_KEY
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000 (docs at /docs)

The first backend startup is slower (loading the MiniLM/CLIP models); the
`data/` directory is bind-mounted so restaurant/recipe data and the vector
store persist across container restarts. If `data/processed` is empty, run
the data pipeline once (see below) before starting the app, so the dashboard
and chat have something to work with.

## Data pipeline (run once, or whenever the source data changes)

From `backend/`:

```bash
uv run backend-cli fetch-data              # downloads raw datasets into data/raw
uv run backend-cli structure-restaurants   # LLM text -> structured_restaurant_data.json
uv run backend-cli caption-recipes         # vision captions -> augmented_food_recipe.json
uv run backend-cli caption-reviews         # vision captions -> augmented_user_review.json
uv run backend-cli build-index             # builds the Chroma vector indexes
```

Other useful CLI commands: `restaurants list|get|add|delete`, `search-articles`,
`search-images`, `fuse-search`, `mcp-test`, `recommend "<preferences>"`.

## Local development (without Docker)

Backend:

```bash
cd backend
uv sync
cp .env.example .env   # fill in credentials
uv run api              # http://localhost:8000 (no --reload - see api/main.py's run())
```

Frontend:

```bash
cd apps/web
npm install
cp .env.example .env.local
npm run dev              # http://localhost:3000
```

## Notes

- `uv.lock` is the source of truth for backend dependencies (`pyproject.toml`
  + `uv.lock`); no `requirements.txt`.
- The backend's `run()` entry point intentionally does not pass `--reload` to
  uvicorn: the app's lifespan spawns an MCP server subprocess, and uvicorn's
  file-watcher reload was found to hang that subprocess spawn on Windows.
  Restart the process manually after backend code changes during development.
