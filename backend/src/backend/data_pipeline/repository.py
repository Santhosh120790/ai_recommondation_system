"""CRUD over the structured restaurant JSON knowledge base.

Every write is backed up first and gated behind an explicit `confirm=True`
(mirroring M1L3's confirmation-before-write safeguard). This module is the
single source of truth for restaurant data mutation — the FastAPI routers,
the CLI, and the MCP server tools all call into it rather than touching the
JSON file directly.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from langchain_core.language_models import BaseChatModel

from backend.core.config import get_settings
from backend.data_pipeline.schemas import Restaurant
from backend.data_pipeline.structuring import extract_restaurant

logger = logging.getLogger(__name__)


class ConfirmationRequiredError(Exception):
    """Raised when a write is attempted without confirm=True."""


class RestaurantNotFoundError(Exception):
    pass


def _data_path() -> Path:
    return get_settings().processed_data_dir / "structured_restaurant_data.json"


def _backup_dir() -> Path:
    backup_dir = get_settings().processed_data_dir / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def load_restaurants() -> list[Restaurant]:
    path = _data_path()
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [Restaurant.model_validate(r) for r in raw]


def _backup_current_file() -> Path | None:
    path = _data_path()
    if not path.exists():
        return None
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = _backup_dir() / f"structured_restaurant_data.{timestamp}.json"
    backup_path.write_bytes(path.read_bytes())
    return backup_path


def _save_restaurants(restaurants: list[Restaurant]) -> None:
    path = _data_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    backup = _backup_current_file()
    if backup:
        logger.info("Backed up %s -> %s", path, backup)
    payload = [r.model_dump() for r in restaurants]
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Saved %d restaurants to %s", len(restaurants), path)


def get_restaurant(item_id: int) -> Restaurant:
    for restaurant in load_restaurants():
        if restaurant.item_id == item_id:
            return restaurant
    raise RestaurantNotFoundError(f"No restaurant with item_id={item_id}")


def next_item_id(restaurants: list[Restaurant] | None = None) -> int:
    restaurants = restaurants if restaurants is not None else load_restaurants()
    if not restaurants:
        return 1_000_001
    return max(r.item_id for r in restaurants) + 1


def structure_new_restaurant(llm: BaseChatModel, raw_text: str) -> Restaurant:
    """Run the LLM structuring pipeline for a new entry without saving it (preview step)."""
    return extract_restaurant(llm, item_id=next_item_id(), raw_block=raw_text)


def save_new_restaurant(restaurant: Restaurant, *, confirm: bool = False) -> Restaurant:
    """Append an already-structured restaurant. Split from `add_restaurant` so a caller can
    preview the structured result once before deciding whether to save it."""
    if not confirm:
        raise ConfirmationRequiredError(
            f"Structured restaurant '{restaurant.name}' (item_id={restaurant.item_id}) — "
            "pass confirm=True to save."
        )
    restaurants = load_restaurants()
    restaurants.append(restaurant)
    _save_restaurants(restaurants)
    return restaurant


def add_restaurant(llm: BaseChatModel, raw_text: str, *, confirm: bool = False) -> Restaurant:
    """Structure a new raw description via the LLM pipeline and append it in one call."""
    restaurant = structure_new_restaurant(llm, raw_text)
    return save_new_restaurant(restaurant, confirm=confirm)


def update_restaurant(item_id: int, updates: dict, *, confirm: bool = False) -> Restaurant:
    restaurants = load_restaurants()
    for idx, restaurant in enumerate(restaurants):
        if restaurant.item_id == item_id:
            updated = restaurant.model_copy(update=updates)
            if not confirm:
                raise ConfirmationRequiredError(
                    f"Update to restaurant item_id={item_id} not saved — pass confirm=True to save."
                )
            restaurants[idx] = updated
            _save_restaurants(restaurants)
            return updated
    raise RestaurantNotFoundError(f"No restaurant with item_id={item_id}")


def delete_restaurant(item_id: int, *, confirm: bool = False) -> None:
    restaurants = load_restaurants()
    remaining = [r for r in restaurants if r.item_id != item_id]
    if len(remaining) == len(restaurants):
        raise RestaurantNotFoundError(f"No restaurant with item_id={item_id}")

    if not confirm:
        raise ConfirmationRequiredError(f"Delete of restaurant item_id={item_id} not saved — pass confirm=True.")

    _save_restaurants(remaining)
