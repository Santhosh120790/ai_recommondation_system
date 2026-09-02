"""Query-time similarity retrieval with optional metadata filtering.

Query embeddings must use the same encoders as indexing: MiniLM for article
text, CLIP for images (either the vision tower for image->image, or the text
tower for cross-modal text->image, which `rag/fusion.py` uses).
"""

from pathlib import Path
from typing import Any

from backend.rag.embeddings import embed_images, embed_texts, embed_texts_clip
from backend.rag.vectorstore import IMAGE_COLLECTION, RESTAURANT_COLLECTION, get_client


class Hit(dict):
    """A single retrieval result: {id, document, metadata, distance}."""


def _unwrap(chroma_result: dict) -> list[Hit]:
    ids = chroma_result["ids"][0]
    documents = chroma_result["documents"][0]
    metadatas = chroma_result["metadatas"][0]
    distances = chroma_result["distances"][0]
    return [
        Hit(id=i, document=d, metadata=m, distance=dist)
        for i, d, m, dist in zip(ids, documents, metadatas, distances, strict=True)
    ]


def retrieve_articles(query: str, k: int = 5, where: dict[str, Any] | None = None) -> list[Hit]:
    collection = get_client().get_collection(RESTAURANT_COLLECTION)
    query_embedding = embed_texts([query])[0].tolist()
    result = collection.query(query_embeddings=[query_embedding], n_results=k, where=where)
    return _unwrap(result)


def retrieve_images_by_text(query: str, k: int = 5, where: dict[str, Any] | None = None) -> list[Hit]:
    collection = get_client().get_collection(IMAGE_COLLECTION)
    query_embedding = embed_texts_clip([query])[0].tolist()
    result = collection.query(query_embeddings=[query_embedding], n_results=k, where=where)
    return _unwrap(result)


def retrieve_images_by_image(image_path: Path, k: int = 5, where: dict[str, Any] | None = None) -> list[Hit]:
    collection = get_client().get_collection(IMAGE_COLLECTION)
    query_embedding = embed_images([image_path])[0].tolist()
    result = collection.query(query_embeddings=[query_embedding], n_results=k, where=where)
    return _unwrap(result)
