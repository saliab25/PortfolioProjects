"""Validate PaySim in chunks and write analysis-friendly Parquet parts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from fraud_system.data_contract import SOURCE_COLUMNS, validate_paysim_frame

DTYPES = {
    "step": "int32",
    "type": "string",
    "amount": "float64",
    "nameOrig": "string",
    "oldbalanceOrg": "float64",
    "newbalanceOrig": "float64",
    "nameDest": "string",
    "oldbalanceDest": "float64",
    "newbalanceDest": "float64",
    "isFraud": "int8",
    "isFlaggedFraud": "int8",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("data/raw/paysim.csv"))
    parser.add_argument(
        "--source-metadata",
        type=Path,
        default=Path("data/raw/source_metadata.json"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--chunk-size", type=int, default=250_000)
    parser.add_argument("--max-rows", type=int)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    expected_sha256 = json.loads(
        args.source_metadata.read_text(encoding="utf-8")
    )["sha256"]
    digest = hashlib.sha256()
    with args.input.open("rb") as source:
        while block := source.read(1024 * 1024):
            digest.update(block)
    if digest.hexdigest() != expected_sha256:
        raise RuntimeError(
            "Source checksum does not match source_metadata.json. "
            "Do not process an untracked dataset version."
        )

    accepted_dir = args.output_dir / "accepted"
    rejected_dir = args.output_dir / "rejected"
    accepted_dir.mkdir(parents=True, exist_ok=True)
    rejected_dir.mkdir(parents=True, exist_ok=True)
    existing_parts = [
        *accepted_dir.glob("part-*.parquet"),
        *rejected_dir.glob("part-*.parquet"),
    ]
    if existing_parts and not args.overwrite:
        raise FileExistsError(
            "Prepared parts already exist. Use --overwrite to explicitly "
            "replace derived Parquet parts."
        )
    for path in existing_parts:
        path.unlink()

    totals = {
        "source_rows": 0,
        "accepted_rows": 0,
        "rejected_rows": 0,
        "fraud_rows": 0,
        "flagged_rows": 0,
    }
    fingerprints: list[pd.Series] = []
    reader = pd.read_csv(
        args.input,
        usecols=list(SOURCE_COLUMNS),
        dtype=DTYPES,
        chunksize=args.chunk_size,
        nrows=args.max_rows,
    )
    for part_number, chunk in enumerate(reader):
        result = validate_paysim_frame(
            chunk,
            source_row_offset=totals["source_rows"],
        )
        accepted = result.accepted
        fingerprint = pd.util.hash_pandas_object(
            accepted.drop(columns=["source_row_number"]),
            index=False,
        )
        accepted.insert(1, "row_fingerprint", fingerprint.map(lambda value: f"{value:016x}"))
        fingerprints.append(fingerprint.reset_index(drop=True))

        accepted.to_parquet(
            accepted_dir / f"part-{part_number:05d}.parquet",
            index=False,
        )
        if not result.rejected.empty:
            result.rejected.to_parquet(
                rejected_dir / f"part-{part_number:05d}.parquet",
                index=False,
            )
        for key in totals:
            totals[key] += result.summary[key]

    all_fingerprints = pd.concat(fingerprints, ignore_index=True)
    totals["duplicate_content_rows"] = int(all_fingerprints.duplicated().sum())
    if totals["duplicate_content_rows"]:
        raise RuntimeError(
            "Cross-chunk duplicate content was detected. Inspect the prepared "
            "parts before allowing training or database ingestion."
        )
    (args.output_dir / "quality_summary.json").write_text(
        json.dumps(totals, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(totals, indent=2))


if __name__ == "__main__":
    main()
