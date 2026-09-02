"""Modality-specific embedders: MiniLM for text, CLIP for images.

Each modality gets its own encoder and its own vector space (no premature
fusion here — that happens later, at query time, in `rag/fusion.py`). Both
outputs are L2-normalized so cosine similarity behaves consistently.
"""

from functools import lru_cache
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from sentence_transformers import SentenceTransformer
from transformers import CLIPModel, CLIPProcessor

TEXT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
TEXT_EMBEDDING_DIM = 384

IMAGE_MODEL_NAME = "openai/clip-vit-base-patch32"
IMAGE_EMBEDDING_DIM = 512


def _l2_normalize(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vectors / norms


@lru_cache
def get_text_encoder() -> SentenceTransformer:
    return SentenceTransformer(TEXT_MODEL_NAME)


@lru_cache
def _get_clip() -> tuple[CLIPModel, CLIPProcessor]:
    model = CLIPModel.from_pretrained(IMAGE_MODEL_NAME)
    processor = CLIPProcessor.from_pretrained(IMAGE_MODEL_NAME)
    model.eval()
    return model, processor


def embed_texts(texts: list[str]) -> np.ndarray:
    encoder = get_text_encoder()
    vectors = encoder.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    return _l2_normalize(vectors.astype(np.float32))


def _pooled(model_output) -> torch.Tensor:
    """`CLIPModel.get_*_features` returns a `BaseModelOutputWithPooling` in this
    transformers version, with the projected embedding in `.pooler_output`."""
    return model_output.pooler_output if hasattr(model_output, "pooler_output") else model_output


def embed_images(image_paths: list[Path]) -> np.ndarray:
    model, processor = _get_clip()
    images = [Image.open(p).convert("RGB") for p in image_paths]
    inputs = processor(images=images, return_tensors="pt")
    with torch.no_grad():
        features = _pooled(model.get_image_features(**inputs))
    return _l2_normalize(features.numpy().astype(np.float32))


def embed_texts_clip(texts: list[str]) -> np.ndarray:
    """Embed text into CLIP's *image* space, for cross-modal text -> image search."""
    model, processor = _get_clip()
    inputs = processor(text=texts, return_tensors="pt", padding=True, truncation=True)
    with torch.no_grad():
        features = _pooled(model.get_text_features(**inputs))
    return _l2_normalize(features.numpy().astype(np.float32))
