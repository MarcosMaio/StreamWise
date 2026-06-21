#!/usr/bin/env python3
"""Download MovieLens (latest-small) and export ratings/movies parquet for training."""

from __future__ import annotations

import argparse
import logging
import zipfile
from io import BytesIO
from pathlib import Path
from urllib.request import urlopen

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MOVIELENS_URL = "https://files.grouplens.org/datasets/movielens/ml-latest-small.zip"


def download_and_extract(target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    extract_dir = target_dir / "ml-latest-small"
    if extract_dir.exists():
        logger.info("MovieLens already present at %s", extract_dir)
        return extract_dir

    logger.info("Downloading MovieLens latest-small…")
    with urlopen(MOVIELENS_URL, timeout=120) as response:
        payload = BytesIO(response.read())

    with zipfile.ZipFile(payload) as archive:
        archive.extractall(target_dir)

    return extract_dir


def export_parquet(source_dir: Path, output_dir: Path, sample_size: int | None) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    ratings = pd.read_csv(source_dir / "ratings.csv")
    movies = pd.read_csv(source_dir / "movies.csv")
    links = pd.read_csv(source_dir / "links.csv")

    if sample_size is not None and sample_size < len(ratings):
        ratings = ratings.sample(n=sample_size, random_state=42)

    ratings.to_parquet(output_dir / "ratings.parquet", index=False)
    movies.to_parquet(output_dir / "movies.parquet", index=False)
    links.to_parquet(output_dir / "links.parquet", index=False)
    logger.info(
        "Exported %d ratings, %d movies, %d links to %s",
        len(ratings),
        len(movies),
        len(links),
        output_dir,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Import MovieLens dataset")
    parser.add_argument("--output-dir", type=Path, default=Path("ml/artifacts/movielens"))
    parser.add_argument("--sample-size", type=int, default=50000)
    args = parser.parse_args()

    source = download_and_extract(args.output_dir)
    export_parquet(source, args.output_dir, args.sample_size)


if __name__ == "__main__":
    main()
