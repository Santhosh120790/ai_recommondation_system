"""Vision captioning pipeline (Module 1, Lab 2 equivalent).

Captions recipe photos (local files, base64-encoded) and user-review photos
(remote URLs, passed straight through) using a vision-capable chat model, and
merges the captions back into the recipe / review records.
"""

import base64
import logging
from pathlib import Path

from langchain_core.language_models import BaseChatModel
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.data_pipeline.schemas import Recipe, Review

logger = logging.getLogger(__name__)

RECIPE_CAPTION_PROMPT = (
    "Describe this dish photo in 1-2 sentences for a restaurant recommendation system. "
    "Focus on visible ingredients, plating/presentation, and cooking style. "
    "Do not mention that it is a photo or image — describe the dish itself."
)


def _review_caption_prompt(review_text: str) -> str:
    return (
        "Describe this photo from a customer review in 1-2 sentences, focusing on the food, "
        "drink, or setting shown. If it's relevant, connect what's visible to the reviewer's "
        f"comments below. Do not mention that it is a photo or image.\n\nReview text: {review_text}"
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _caption_image_url(llm: BaseChatModel, prompt: str, image_url: str) -> str:
    message = {
        "role": "user",
        "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": image_url}},
        ],
    }
    response = llm.invoke([message])
    return str(response.content).strip()


def _local_image_data_url(image_path: Path) -> str:
    suffix = image_path.suffix.lstrip(".").lower() or "png"
    encoded = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    return f"data:image/{suffix};base64,{encoded}"


def caption_recipe_image(llm: BaseChatModel, image_path: Path) -> str:
    data_url = _local_image_data_url(image_path)
    return _caption_image_url(llm, RECIPE_CAPTION_PROMPT, data_url)


def caption_review_image(llm: BaseChatModel, image_url: str, review_text: str) -> str:
    return _caption_image_url(llm, _review_caption_prompt(review_text), image_url)


def augment_recipes(llm: BaseChatModel, recipes: list[dict], images_dir: Path) -> list[Recipe]:
    augmented: list[Recipe] = []
    for raw in recipes:
        image_path = images_dir / f"recipe{raw['id']}.png"
        description = None
        if image_path.exists():
            try:
                description = caption_recipe_image(llm, image_path)
                logger.info("Captioned recipe %d (%s): %s", raw["id"], raw["name"], description)
            except Exception:
                logger.exception("Failed to caption recipe %d image at %s", raw["id"], image_path)
        else:
            logger.warning("No image found for recipe %d at %s", raw["id"], image_path)

        augmented.append(
            Recipe(
                **raw,
                image_path=str(image_path.relative_to(images_dir.parent)) if image_path.exists() else None,
                image_description=description,
            )
        )
    return augmented


def augment_reviews(llm: BaseChatModel, reviews: list[dict]) -> list[Review]:
    augmented: list[Review] = []
    for raw in reviews:
        images = raw.get("images") or []
        captions: list[str] = []
        for url in images:
            try:
                caption = caption_review_image(llm, url, raw["text"])
                captions.append(caption)
                logger.info("Captioned review %d image: %s", raw["reviewId"], caption)
            except Exception:
                logger.exception("Failed to caption review %d image at %s", raw["reviewId"], url)

        augmented.append(
            Review(
                review_id=raw["reviewId"],
                user_id=raw["userId"],
                item_id=raw["itemId"],
                title=raw["title"],
                text=raw["text"],
                date=raw["date"],
                rating=raw["rating"],
                language=raw["language"],
                images=images,
                image_captions=captions,
            )
        )
    return augmented
