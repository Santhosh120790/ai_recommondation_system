import json

from fastapi import APIRouter
from pydantic import BaseModel

from backend.core.config import get_settings
from backend.data_pipeline import repository

router = APIRouter(prefix="/stats", tags=["stats"])


class Stats(BaseModel):
    restaurants: int
    recipes: int
    reviews: int
    cuisines: int
    locations: int
    avg_rating: float | None


@router.get("")
def get_stats() -> Stats:
    settings = get_settings()
    restaurants = repository.load_restaurants()

    recipes_path = settings.processed_data_dir / "augmented_food_recipe.json"
    recipes_count = len(json.loads(recipes_path.read_text(encoding="utf-8"))) if recipes_path.exists() else 0

    reviews_path = settings.processed_data_dir / "augmented_user_review.json"
    reviews_count = len(json.loads(reviews_path.read_text(encoding="utf-8"))) if reviews_path.exists() else 0

    ratings = [r.rating for r in restaurants if r.rating is not None]

    return Stats(
        restaurants=len(restaurants),
        recipes=recipes_count,
        reviews=reviews_count,
        cuisines=len({r.food_style for r in restaurants}),
        locations=len({r.location for r in restaurants}),
        avg_rating=round(sum(ratings) / len(ratings), 2) if ratings else None,
    )
