import json
import logging

import typer

from backend.core.config import get_settings
from backend.core.llm import get_chat_model, get_vision_model
from backend.core.logging import configure_logging
from backend.data_pipeline import captioning, fetch, repository, structuring

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


def run() -> None:
    app()


if __name__ == "__main__":
    run()
