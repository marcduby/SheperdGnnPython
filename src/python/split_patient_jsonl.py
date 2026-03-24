#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


def read_jsonl(path: Path) -> list[dict]:
    records = []
    with path.open() as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_no} of {path}: {exc}") from exc
    return records


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for record in records:
            handle.write(json.dumps(record))
            handle.write("\n")


def validate(records: list[dict], label: str) -> None:
    ids = []
    for idx, record in enumerate(records):
        if "id" not in record:
            raise ValueError(f"{label}[{idx}] is missing 'id'")
        if "positive_phenotypes" not in record:
            raise ValueError(f"{label}[{idx}] is missing 'positive_phenotypes'")
        ids.append(record["id"])
    if len(set(ids)) != len(ids):
        raise ValueError(f"{label} contains duplicate patient ids")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create deterministic train/val/test JSONL splits for SHEPHERD.")
    parser.add_argument("--train-input", required=True, help="Existing train JSONL/TXT file")
    parser.add_argument("--val-input", required=True, help="Existing val JSONL/TXT file")
    parser.add_argument("--output-dir", required=True, help="Output cohort directory")
    parser.add_argument("--test-fraction", type=float, default=0.15, help="Fraction of combined pool to reserve for test")
    parser.add_argument("--seed", type=int, default=33, help="Random seed")
    parser.add_argument(
        "--split-source",
        choices=["train_only", "train_and_val"],
        default="train_only",
        help="Whether to carve test examples only from train, or from the combined train+val pool",
    )
    args = parser.parse_args()

    train_input = Path(args.train_input)
    val_input = Path(args.val_input)
    output_dir = Path(args.output_dir)

    train_records = read_jsonl(train_input)
    val_records = read_jsonl(val_input)
    validate(train_records, "train_input")
    validate(val_records, "val_input")

    rng = random.Random(args.seed)

    if args.split_source == "train_only":
        pool = list(train_records)
        pool_ids = {record["id"] for record in pool}
        if any(record["id"] in pool_ids for record in val_records):
            overlap = pool_ids.intersection({record["id"] for record in val_records})
            if overlap:
                raise ValueError(f"train/val overlap detected: {sorted(list(overlap))[:5]}")
        rng.shuffle(pool)
        test_size = max(1, round(len(pool) * args.test_fraction))
        test_records = pool[:test_size]
        new_train_records = pool[test_size:]
        new_val_records = list(val_records)
    else:
        pool = list(train_records) + list(val_records)
        ids = [record["id"] for record in pool]
        if len(set(ids)) != len(ids):
            raise ValueError("train+val combined pool contains duplicate patient ids")
        rng.shuffle(pool)
        test_size = max(1, round(len(pool) * args.test_fraction))
        val_size = max(1, len(val_records))
        test_records = pool[:test_size]
        remaining = pool[test_size:]
        if len(remaining) <= val_size:
            raise ValueError("Not enough examples remain after test split to rebuild train/val")
        new_val_records = remaining[:val_size]
        new_train_records = remaining[val_size:]

    validate(new_train_records, "train_output")
    validate(new_val_records, "val_output")
    validate(test_records, "test_output")

    train_out = output_dir / "train.jsonl"
    val_out = output_dir / "val.jsonl"
    test_out = output_dir / "test.jsonl"

    write_jsonl(train_out, new_train_records)
    write_jsonl(val_out, new_val_records)
    write_jsonl(test_out, test_records)

    print(f"Wrote {train_out} ({len(new_train_records)} records)")
    print(f"Wrote {val_out} ({len(new_val_records)} records)")
    print(f"Wrote {test_out} ({len(test_records)} records)")
    print(f"Split source: {args.split_source}")
    print(f"Seed: {args.seed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
