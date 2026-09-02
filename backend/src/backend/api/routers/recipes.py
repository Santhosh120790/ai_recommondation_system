import json

from fastapi import APIRouter

from backend.core.config import get_settings
from backend.data_pipeline.schemas import Recipe

router = APIRouter(prefix="/recipes", tags=["recipes"])


@router.get("")
def list_recipes() -> list[Recipe]:
    path = get_settings().processed_data_dir / "augmented_food_recipe.json"
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [Recipe.model_validate(r) for r in raw]
