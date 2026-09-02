"""Download the raw source datasets into data/raw.

These are the same IBM Skills Network Cloud Object Storage assets the
original course notebooks fetch at runtime. We pull them once and commit
nothing but the URLs, so `data/raw` can always be regenerated.
"""

import logging
import shutil
import zipfile
from pathlib import Path

import requests

from backend.core.config import get_settings

logger = logging.getLogger(__name__)

CULINARY_MAP_URL = "https://cf-courses-data.s3.us.cloud-object-storage.appdomain.cloud/1r_mM6ZPYNxcFv65QkzubA/California-Culinary-Map.txt"
RECIPES_URL = "https://cf-courses-data.s3.us.cloud-object-storage.appdomain.cloud/hpTjb6liKBLVHQK0UgMi5A/Recipes.json"
REVIEWS_URL = "https://cf-courses-data.s3.us.cloud-object-storage.appdomain.cloud/fQUs9wQ6aB6ts6fmkD2V2w/Synthetic-User-Reviews.json"
RECIPE_IMAGES_ZIP_URL = "https://cf-courses-data.s3.us.cloud-object-storage.appdomain.cloud/5_Rr6ohviItzucyWk6nkrw/synthetic-recipe-images.zip"


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading %s -> %s", url, dest)
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    dest.write_bytes(response.content)


def fetch_all(force: bool = False) -> None:
    raw_dir = get_settings().raw_data_dir
    raw_dir.mkdir(parents=True, exist_ok=True)

    culinary_map = raw_dir / "California-Culinary-Map.txt"
    recipes = raw_dir / "Recipes.json"
    reviews = raw_dir / "Synthetic-User-Reviews.json"
    images_dir = raw_dir / "images"

    if force or not culinary_map.exists():
        _download(CULINARY_MAP_URL, culinary_map)
    if force or not recipes.exists():
        _download(RECIPES_URL, recipes)
    if force or not reviews.exists():
        _download(REVIEWS_URL, reviews)

    if force or not images_dir.exists() or not any(images_dir.glob("*.png")):
        zip_path = raw_dir / "synthetic-recipe-images.zip"
        _download(RECIPE_IMAGES_ZIP_URL, zip_path)
        extract_tmp = raw_dir / "_images_extract_tmp"
        if extract_tmp.exists():
            shutil.rmtree(extract_tmp)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extract_tmp)

        nested = extract_tmp / "synthetic_recipe_images"
        source_dir = nested if nested.exists() else extract_tmp
        if images_dir.exists():
            shutil.rmtree(images_dir)
        shutil.move(str(source_dir), str(images_dir))
        shutil.rmtree(extract_tmp, ignore_errors=True)
        zip_path.unlink()

    logger.info("All raw datasets present in %s", raw_dir)
