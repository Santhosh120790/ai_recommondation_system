"""Text -> structured JSON extraction pipeline (Module 1, Lab 1 equivalent).

Splits the raw California Culinary Map text into per-restaurant paragraphs,
prompts the LLM to extract a fixed set of attributes as JSON, validates the
result against the `Restaurant` schema, and runs an LLM-based repair loop on
malformed output before giving up.
"""

import json
import logging
import re

from langchain_core.language_models import BaseChatModel
from pydantic import ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.data_pipeline.schemas import Restaurant

logger = logging.getLogger(__name__)

MAX_REPAIR_ATTEMPTS = 2

EXTRACTION_SYSTEM_PROMPT = """You are a data extraction engine. You convert a single restaurant \
description into a strict JSON object. Output ONLY the JSON object — no markdown fences, \
no commentary, no trailing text.

Required JSON shape:
{
  "name": string,
  "location": string,          // neighborhood or city mentioned in the text
  "type": string,               // e.g. "upscale bistro", "fast-casual", "fine dining"
  "food_style": string,         // cuisine, e.g. "Farm-to-Table Californian"
  "rating": number or null,     // the X.X out of 5 rating as a float, e.g. 4.5
  "price_range": integer or null,  // count of '$' symbols, 1-4
  "signatures": [string, ...],  // signature dishes mentioned, short phrases
  "vibe": string or null,       // mood/atmosphere adjectives, e.g. "bohemian chic"
  "environment": string,        // physical space / decor description
  "shortcomings": [string, ...] // any downsides mentioned (often empty)
}

Rules:
- If a field is not mentioned in the text, use null (or an empty list for list fields).
- "price_range" must be an integer between 1 and 4, derived from counting '$' characters.
- "rating" must be a float parsed from patterns like "4.5/5".
- Keep "signatures" and "shortcomings" as short phrases, not full sentences.

Example input:
"**The Gilded Artichoke** brings a **bohemian chic** energy to the hills of **Silver Lake**, \
operating as an **upscale bistro** that prioritizes **Farm-to-Table Californian** ingredients. \
The space feels like a high-end greenhouse with its reclaimed wood and floor-to-ceiling windows, \
perfectly complementing the **4.5/5** rating earned by its lavender-rubbed roasted chicken and \
delicate heirloom tomato tarts. Price range: $$$$"

Example output:
{"name": "The Gilded Artichoke", "location": "Silver Lake", "type": "upscale bistro", \
"food_style": "Farm-to-Table Californian", "rating": 4.5, "price_range": 4, \
"signatures": ["lavender-rubbed roasted chicken", "heirloom tomato tarts"], \
"vibe": "bohemian chic", "environment": "high-end greenhouse with reclaimed wood and \
floor-to-ceiling windows", "shortcomings": []}
"""

REPAIR_SYSTEM_PROMPT = """You are a JSON repair engine. You will be given the ORIGINAL source \
text, a JSON object that was extracted from it but fails schema validation, and the validation \
error. Fix the JSON so it validates AND accurately reflects the original source text — \
re-read the source text and derive the correct value for any field the error points to. Do \
NOT satisfy the schema by inserting an empty string, 0, or other placeholder value; only use \
null / an empty list where the source text truly has no such information. Output ONLY the \
corrected JSON object — no markdown fences, no commentary."""

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def split_restaurant_blocks(raw_text: str) -> list[str]:
    """Split the culinary map text into one paragraph per restaurant."""
    blocks = [b.strip() for b in re.split(r"\n\s*\n", raw_text)]
    return [b for b in blocks if b and not b.startswith("#")]


def _strip_code_fences(text: str) -> str:
    return _CODE_FENCE_RE.sub("", text.strip())


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _call_llm(llm: BaseChatModel, system_prompt: str, user_content: str) -> str:
    response = llm.invoke(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
    )
    return str(response.content)


def extract_restaurant(llm: BaseChatModel, item_id: int, raw_block: str) -> Restaurant:
    """Extract + validate one restaurant paragraph, repairing malformed JSON on failure."""
    raw_output = _call_llm(llm, EXTRACTION_SYSTEM_PROMPT, raw_block)

    last_error: ValidationError | json.JSONDecodeError | None = None
    for attempt in range(MAX_REPAIR_ATTEMPTS + 1):
        candidate = _strip_code_fences(raw_output)
        try:
            payload = json.loads(candidate)
            payload["item_id"] = item_id
            payload["source_text"] = raw_block
            return Restaurant.model_validate(payload)
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = exc
            if attempt == MAX_REPAIR_ATTEMPTS:
                break
            logger.warning("Restaurant #%d: repair attempt %d after error: %s", item_id, attempt + 1, exc)
            repair_input = (
                f"Original source text:\n{raw_block}\n\nInvalid JSON:\n{candidate}\n\nValidation error:\n{exc}"
            )
            raw_output = _call_llm(llm, REPAIR_SYSTEM_PROMPT, repair_input)

    raise ValueError(f"Restaurant #{item_id}: failed to extract valid JSON after repair attempts: {last_error}")


def structure_all(llm: BaseChatModel, raw_text: str) -> list[Restaurant]:
    blocks = split_restaurant_blocks(raw_text)
    results: list[Restaurant] = []
    failures: list[tuple[int, str]] = []

    for idx, block in enumerate(blocks, start=1):
        try:
            restaurant = extract_restaurant(llm, item_id=1_000_000 + idx, raw_block=block)
            results.append(restaurant)
            logger.info("Structured %d/%d: %s", idx, len(blocks), restaurant.name)
        except ValueError as exc:
            logger.error("Skipping restaurant #%d: %s", idx, exc)
            failures.append((idx, str(exc)))

    if failures:
        logger.warning("%d/%d restaurants failed to structure", len(failures), len(blocks))

    return results
