"""Download the public synthetic PaySim dataset from Kaggle."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import kagglehub

DATASET_HANDLE = "ealaxi/paysim1"


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("data/raw"))
    args = parser.parse_args()

    cache_path = Path(kagglehub.dataset_download(DATASET_HANDLE))
    csv_files = sorted(cache_path.rglob("*.csv"))
    if len(csv_files) != 1:
        raise RuntimeError(f"Expected exactly one CSV below {cache_path}, found {len(csv_files)}.")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    destination = args.output_dir / "paysim.csv"
    shutil.copy2(csv_files[0], destination)
    metadata = {
        "dataset_handle": DATASET_HANDLE,
        "source_filename": csv_files[0].name,
        "local_filename": destination.name,
        "sha256": sha256_file(destination),
        "synthetic_data": True,
    }
    (args.output_dir / "source_metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
