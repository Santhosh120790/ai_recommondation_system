"""MCP server exposing the restaurant data/RAG layer as discoverable tools + a resource.

This is the data/tool access layer for the LangGraph agents (Phase 3): agent
nodes don't call `data_pipeline`/`rag` directly, they go through an MCP
client that talks to this server, so the tool surface is protocol-defined
and independently testable/connectable by any MCP client.
"""

import json
import logging

from mcp.server.mcpserver import MCPServer

from backend.core.config import get_settings
from backend.core.llm import get_chat_model
from backend.data_pipeline import repository
from backend.rag import fusion, retrieval

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = MCPServer(name="restaurant-recommendation", version="0.1.0")


@mcp.resource("culinary-map://california")
def culinary_map() -> str:
    """The raw California Culinary Map source text."""
    path = get_settings().raw_data_dir / "California-Culinary-Map.txt"
    return path.read_text(encoding="utf-8")


@mcp.tool()
def get_restaurant_info(name: str) -> str:
    """Look up a restaurant by partial name match. Returns JSON: a list of matches."""
    query = name.lower().strip()
    matches = [r.model_dump() for r in repository.load_restaurants() if query in r.name.lower()]
    return json.dumps(matches, ensure_ascii=False)


@mcp.tool()
def recommend_by_vibe(vibe: str, k: int = 5) -> str:
    """Recommend restaurants matching a vibe/mood description. Two-pass search: first
    against the structured `vibe` field, falling back to the raw source text if that
    doesn't fill k results. Returns JSON: a list of restaurants."""
    query = vibe.lower().strip()
    restaurants = repository.load_restaurants()

    vibe_matches = [r for r in restaurants if r.vibe and query in r.vibe.lower()]
    if len(vibe_matches) < k:
        seen_ids = {r.item_id for r in vibe_matches}
        text_matches = [
            r for r in restaurants if r.item_id not in seen_ids and query in r.source_text.lower()
        ]
        vibe_matches.extend(text_matches)

    results = [r.model_dump() for r in vibe_matches[:k]]
    return json.dumps(results, ensure_ascii=False)


@mcp.tool()
def get_review(restaurant_name: str) -> str:
    """Fetch the augmented user review(s) for a restaurant by name. Returns JSON."""
    settings = get_settings()
    reviews_path = settings.processed_data_dir / "augmented_user_review.json"
    if not reviews_path.exists():
        return json.dumps({"error": "No review data available. Run caption-reviews first."})

    matches = [r for r in repository.load_restaurants() if restaurant_name.lower() in r.name.lower()]
    if not matches:
        return json.dumps({"error": f"No restaurant found matching '{restaurant_name}'"})

    item_ids = {r.item_id for r in matches}
    all_reviews = json.loads(reviews_path.read_text(encoding="utf-8"))
    reviews = [r for r in all_reviews if r["item_id"] in item_ids]
    return json.dumps(reviews, ensure_ascii=False)


@mcp.tool()
def search_restaurants(query: str, k: int = 5, location: str | None = None, cuisine: str | None = None) -> str:
    """Semantic search over restaurant articles, with optional exact-match metadata
    filters. Returns JSON: a list of {name, location, cuisine, distance}."""
    where = None
    conditions = []
    if location:
        conditions.append({"location": location})
    if cuisine:
        conditions.append({"cuisine": cuisine})
    if len(conditions) == 1:
        where = conditions[0]
    elif len(conditions) > 1:
        where = {"$and": conditions}

    hits = retrieval.retrieve_articles(query, k=k, where=where)
    results = [{"name": h["metadata"]["name"], "location": h["metadata"]["location"],
                "cuisine": h["metadata"]["cuisine"], "distance": h["distance"]} for h in hits]
    return json.dumps(results, ensure_ascii=False)


@mcp.tool()
def search_food_images(query: str, k: int = 5) -> str:
    """Cross-modal semantic search: text query -> matching food/recipe images. Returns
    JSON: a list of {name, image_description, distance}."""
    hits = retrieval.retrieve_images_by_text(query, k=k)
    results = [{"name": h["metadata"]["name"], "image_description": h["metadata"]["image_description"],
                "distance": h["distance"]} for h in hits]
    return json.dumps(results, ensure_ascii=False)


@mcp.tool()
def fuse_search(query: str, k: int = 5, w_text: float = 0.5, w_img: float = 0.5) -> str:
    """Unified multimodal search: merges restaurant-article and food-image results into
    one fused-ranked list, weighted by w_text/w_img. Returns JSON."""
    hits = fusion.fuse_rank(query, k=k, w_text=w_text, w_img=w_img)
    results = [{"modality": h["modality"], "name": h["name"], "fused_score": h["fused_score"]} for h in hits]
    return json.dumps(results, ensure_ascii=False)


@mcp.tool()
def add_restaurant(raw_text: str, confirm: bool = False) -> str:
    """Structure a raw restaurant description via the LLM pipeline. With confirm=False
    (default), only previews the structured result without saving — call again with
    confirm=True to actually persist it. Returns JSON."""
    llm = get_chat_model(temperature=0)
    try:
        restaurant = repository.add_restaurant(llm, raw_text, confirm=confirm)
        return json.dumps({"saved": True, "restaurant": restaurant.model_dump()}, ensure_ascii=False)
    except repository.ConfirmationRequiredError:
        preview = repository.structure_new_restaurant(llm, raw_text)
        return json.dumps({"saved": False, "preview": preview.model_dump()}, ensure_ascii=False)


@mcp.tool()
def delete_restaurant(item_id: int, confirm: bool = False) -> str:
    """Delete a restaurant by item_id. Requires confirm=True to actually delete."""
    try:
        repository.delete_restaurant(item_id, confirm=confirm)
        return json.dumps({"deleted": True, "item_id": item_id})
    except repository.ConfirmationRequiredError as exc:
        return json.dumps({"deleted": False, "message": str(exc)})
    except repository.RestaurantNotFoundError as exc:
        return json.dumps({"deleted": False, "error": str(exc)})


if __name__ == "__main__":
    mcp.run(transport="stdio")
