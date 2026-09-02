"""Late-fusion multimodal ranking (the M2L3 lab the course notebooks never shipped).

Retrieves top-k article candidates and top-k image candidates independently,
converts each modality's distances to similarity scores, min-max normalizes
within each modality (so one modality can't dominate purely from scale),
applies a weighted combination, and merges both candidate pools into one
ranked list.
"""

from typing import Any, Literal, TypedDict

from backend.rag.retrieval import Hit, retrieve_articles, retrieve_images_by_text


class FusedHit(TypedDict):
    modality: Literal["article", "image"]
    id: str
    name: str
    similarity: float
    normalized_score: float
    fused_score: float
    metadata: dict[str, Any]


def _to_similarity(distance: float) -> float:
    """Chroma cosine-space distance -> cosine similarity."""
    return 1.0 - distance


def _minmax(values: list[float]) -> list[float]:
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi == lo:
        return [1.0 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


def _score_modality(hits: list[Hit], modality: Literal["article", "image"], weight: float) -> list[FusedHit]:
    similarities = [_to_similarity(h["distance"]) for h in hits]
    normalized = _minmax(similarities)
    return [
        FusedHit(
            modality=modality,
            id=hit["id"],
            name=hit["metadata"].get("name", hit["document"]),
            similarity=sim,
            normalized_score=norm,
            fused_score=norm * weight,
            metadata=hit["metadata"],
        )
        for hit, sim, norm in zip(hits, similarities, normalized, strict=True)
    ]


def fuse_rank(
    query: str,
    k: int = 10,
    w_text: float = 0.5,
    w_img: float = 0.5,
    article_where: dict[str, Any] | None = None,
    image_where: dict[str, Any] | None = None,
) -> list[FusedHit]:
    article_hits = retrieve_articles(query, k=k, where=article_where)
    image_hits = retrieve_images_by_text(query, k=k, where=image_where)

    scored = _score_modality(article_hits, "article", w_text) + _score_modality(image_hits, "image", w_img)
    return sorted(scored, key=lambda h: h["fused_score"], reverse=True)
