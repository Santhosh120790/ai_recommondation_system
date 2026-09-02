import asyncio
import json
import logging

import typer

from backend.core.config import get_settings
from backend.core.llm import get_chat_model, get_vision_model
from backend.core.logging import configure_logging
from backend.data_pipeline import captioning, fetch, repository, structuring
from backend.agents.graph import run_recommendation
from backend.mcp.client import MCPClient
from backend.rag import fusion, retrieval, vectorstore

configure_logging()
logger = logging.getLogger(__name__)

app = typer.Typer(help="Data pipeline and restaurant management CLI.")
restaurants_app = typer.Typer(help="Browse, add, edit, and delete restaurant records.")
app.add_typer(restaurants_app, name="restaurants")


@app.command("fetch-data")
def fetch_data(force: bool = typer.Option(False, help="Re-download even if files already exist.")) -> None:
    """Download the raw datasets (culinary map, recipes, reviews, images) into data/raw."""
    fetch.fetch_all(force=force)
    typer.echo("Done.")


@app.command("structure-restaurants")
def structure_restaurants() -> None:
    """Run the LLM structuring pipeline over the raw culinary map text."""
    settings = get_settings()
    raw_path = settings.raw_data_dir / "California-Culinary-Map.txt"
    if not raw_path.exists():
        typer.echo(f"Raw file not found at {raw_path}. Run `fetch-data` first.", err=True)
        raise typer.Exit(1)

    raw_text = raw_path.read_text(encoding="utf-8")
    llm = get_chat_model(temperature=0)
    restaurants = structuring.structure_all(llm, raw_text)

    out_path = settings.processed_data_dir / "structured_restaurant_data.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps([r.model_dump() for r in restaurants], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    typer.echo(f"Wrote {len(restaurants)} restaurants to {out_path}")


@app.command("caption-recipes")
def caption_recipes() -> None:
    """Caption recipe images and merge into an augmented recipe file."""
    settings = get_settings()
    recipes_path = settings.raw_data_dir / "Recipes.json"
    images_dir = settings.raw_data_dir / "images"
    if not recipes_path.exists() or not images_dir.exists():
        typer.echo("Recipes.json or images/ not found. Run `fetch-data` first.", err=True)
        raise typer.Exit(1)

    raw_recipes = json.loads(recipes_path.read_text(encoding="utf-8"))
    llm = get_vision_model()
    augmented = captioning.augment_recipes(llm, raw_recipes, images_dir)

    out_path = settings.processed_data_dir / "augmented_food_recipe.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps([r.model_dump() for r in augmented], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    typer.echo(f"Wrote {len(augmented)} recipes to {out_path}")


@app.command("caption-reviews")
def caption_reviews() -> None:
    """Caption review images (from remote URLs) and merge into an augmented review file."""
    settings = get_settings()
    reviews_path = settings.raw_data_dir / "Synthetic-User-Reviews.json"
    if not reviews_path.exists():
        typer.echo("Synthetic-User-Reviews.json not found. Run `fetch-data` first.", err=True)
        raise typer.Exit(1)

    raw_reviews = json.loads(reviews_path.read_text(encoding="utf-8"))
    for review in raw_reviews:
        images = review.get("images")
        if isinstance(images, str):
            import ast

            review["images"] = ast.literal_eval(images) if images.strip() else []

    llm = get_vision_model()
    augmented = captioning.augment_reviews(llm, raw_reviews)

    out_path = settings.processed_data_dir / "augmented_user_review.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps([r.model_dump() for r in augmented], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    typer.echo(f"Wrote {len(augmented)} reviews to {out_path}")


@restaurants_app.command("list")
def restaurants_list() -> None:
    for r in repository.load_restaurants():
        typer.echo(f"{r.item_id}  {r.name:<30}  {r.location:<20}  {r.food_style}")


@restaurants_app.command("get")
def restaurants_get(item_id: int) -> None:
    try:
        restaurant = repository.get_restaurant(item_id)
    except repository.RestaurantNotFoundError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    typer.echo(restaurant.model_dump_json(indent=2))


@restaurants_app.command("add")
def restaurants_add(
    text: str = typer.Argument(..., help="Raw unstructured restaurant description."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt."),
) -> None:
    llm = get_chat_model(temperature=0)
    structured = repository.structure_new_restaurant(llm, text)
    typer.echo(f"Structured: {structured.model_dump_json(indent=2)}")

    if not yes and not typer.confirm("Save this restaurant?"):
        typer.echo("Cancelled.")
        raise typer.Exit(0)

    saved = repository.save_new_restaurant(structured, confirm=True)
    typer.echo(f"Saved item_id={saved.item_id}")


@restaurants_app.command("delete")
def restaurants_delete(
    item_id: int,
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt."),
) -> None:
    if not yes and not typer.confirm(f"Delete restaurant item_id={item_id}?"):
        typer.echo("Cancelled.")
        raise typer.Exit(0)
    try:
        repository.delete_restaurant(item_id, confirm=True)
    except repository.RestaurantNotFoundError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"Deleted restaurant item_id={item_id}")


@app.command("build-index")
def build_index() -> None:
    """Build and persist the Chroma text + image vector collections."""
    article_count, image_count = vectorstore.build_all_indexes()
    typer.echo(f"Indexed {article_count} restaurant articles and {image_count} food images")


@app.command("search-articles")
def search_articles(
    query: str,
    k: int = typer.Option(5, help="Number of results."),
    location: str = typer.Option(None, help="Filter by exact location metadata."),
) -> None:
    where = {"location": location} if location else None
    for hit in retrieval.retrieve_articles(query, k=k, where=where):
        typer.echo(f"{hit['distance']:.4f}  {hit['metadata']['name']:<30}  {hit['metadata']['location']}")


@app.command("search-images")
def search_images(query: str, k: int = typer.Option(5, help="Number of results.")) -> None:
    for hit in retrieval.retrieve_images_by_text(query, k=k):
        typer.echo(f"{hit['distance']:.4f}  {hit['metadata']['name']}")


@app.command("fuse-search")
def fuse_search(
    query: str,
    k: int = typer.Option(5, help="Top-k per modality before fusion."),
    w_text: float = typer.Option(0.5, help="Weight for article/text results."),
    w_img: float = typer.Option(0.5, help="Weight for image results."),
) -> None:
    for hit in fusion.fuse_rank(query, k=k, w_text=w_text, w_img=w_img):
        typer.echo(f"{hit['fused_score']:.4f}  [{hit['modality']:<7}]  {hit['name']}")


@app.command("mcp-test")
def mcp_test(
    tool: str = typer.Option(None, help="Call this tool by name after connecting."),
    args: str = typer.Option("{}", help="JSON-encoded arguments for --tool."),
) -> None:
    """Connect to the MCP server, list tools/resources, and optionally call one tool."""

    async def _run() -> None:
        async with MCPClient() as client:
            tools = await client.list_tools()
            typer.echo(f"Connected. Tools: {tools}")
            if tool:
                result = await client.call_tool(tool, json.loads(args))
                typer.echo(f"Result: {result}")

    asyncio.run(_run())


@app.command("recommend")
def recommend(user_input: str) -> None:
    """Run the full multi-agent recommendation workflow for a user's stated preferences."""

    async def _run() -> None:
        result = await run_recommendation(user_input)
        typer.echo("\n=== USER PROFILE ===\n" + result.get("user_profile", ""))
        typer.echo("\n=== CANDIDATES ===\n" + result.get("candidates", ""))
        typer.echo("\n=== TREND ANALYSIS ===\n" + result.get("trend_analysis", ""))
        typer.echo("\n=== STYLE ANALYSIS ===\n" + result.get("style_analysis", ""))
        typer.echo("\n=== NUTRITION ANALYSIS ===\n" + result.get("nutrition_analysis", ""))
        typer.echo("\n=== FINAL RECOMMENDATION ===\n" + result.get("final_recommendation", ""))

    asyncio.run(_run())


def run() -> None:
    app()


if __name__ == "__main__":
    run()
