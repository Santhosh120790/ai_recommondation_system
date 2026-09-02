"""Build and persist the two modality-specific Chroma collections.

Text (restaurant articles) and images (recipe photos) get independent
collections with independent embedding spaces — see `rag/embeddings.py`.
Cross-modal comparison is deferred to query time (`rag/fusion.py`).
"""

import json
import logging
from pathlib import Path

import chromadb
from chromadb.api.models.Collection import Collection

from backend.core.config import get_settings
from backend.rag.embeddings import embed_images, embed_texts

logger = logging.getLogger(__name__)

RESTAURANT_COLLECTION = "restaurant_articles"
IMAGE_COLLECTION = "food_images"


def get_client() -> chromadb.ClientAPI:
    chroma_dir = get_settings().chroma_dir
    chroma_dir.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(chroma_dir))


def _restaurant_page_content(restaurant: dict) -> str:
    parts = [restaurant["name"], restaurant["food_style"], restaurant["type"], restaurant["location"]]
    if restaurant.get("vibe"):
        parts.append(restaurant["vibe"])
    if restaurant.get("signatures"):
        parts.append(", ".join(restaurant["signatures"]))
    return " | ".join(p for p in parts if p)


def build_restaurant_index(restaurants: list[dict]) -> Collection:
    client = get_client()
    client.delete_collection(RESTAURANT_COLLECTION) if RESTAURANT_COLLECTION in {
        c.name for c in client.list_collections()
    } else None
    collection = client.create_collection(RESTAURANT_COLLECTION, metadata={"hnsw:space": "cosine"})

    documents = [_restaurant_page_content(r) for r in restaurants]
    embeddings = embed_texts(documents)
    ids = [str(r["item_id"]) for r in restaurants]
    metadatas = [
        {
            "item_id": r["item_id"],
            "name": r["name"],
            "location": r["location"],
            "cuisine": r["food_style"],
            "type": r["type"],
            "price_range": r.get("price_range") or 0,
            "rating": r.get("rating") or 0.0,
            "source": "structured_restaurant_data",
        }
        for r in restaurants
    ]

    collection.add(ids=ids, embeddings=embeddings.tolist(), documents=documents, metadatas=metadatas)
    logger.info("Indexed %d restaurant articles", len(restaurants))
    return collection


def build_image_index(recipes: list[dict], images_root: Path) -> Collection:
    client = get_client()
    client.delete_collection(IMAGE_COLLECTION) if IMAGE_COLLECTION in {
        c.name for c in client.list_collections()
    } else None
    collection = client.create_collection(IMAGE_COLLECTION, metadata={"hnsw:space": "cosine"})

    valid = [r for r in recipes if r.get("image_path") and (images_root / Path(r["image_path"]).name).exists()]
    skipped = len(recipes) - len(valid)
    if skipped:
        logger.warning("Skipping %d recipes with no image on disk", skipped)

    image_paths = [images_root / Path(r["image_path"]).name for r in valid]
    embeddings = embed_images(image_paths)
    ids = [str(r["id"]) for r in valid]
    documents = [r["name"] for r in valid]
    metadatas = [
        {
            "recipe_id": r["id"],
            "name": r["name"],
            "cuisine": r["cuisine"],
            "image_path": r["image_path"],
            "image_description": r.get("image_description") or "",
            "source": "augmented_food_recipe",
        }
        for r in valid
    ]

    collection.add(ids=ids, embeddings=embeddings.tolist(), documents=documents, metadatas=metadatas)
    logger.info("Indexed %d food images", len(valid))
    return collection


def build_all_indexes() -> tuple[int, int]:
    settings = get_settings()
    restaurants = json.loads((settings.processed_data_dir / "structured_restaurant_data.json").read_text(encoding="utf-8"))
    recipes = json.loads((settings.processed_data_dir / "augmented_food_recipe.json").read_text(encoding="utf-8"))
    images_root = settings.raw_data_dir / "images"

    restaurant_collection = build_restaurant_index(restaurants)
    image_collection = build_image_index(recipes, images_root)
    return restaurant_collection.count(), image_collection.count()
