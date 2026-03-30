#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


EDGE_KEY = ["x_idx", "y_idx", "full_relation"]
FULL_KEY = ["x_idx", "y_idx", "full_relation", "mask"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Report and optionally deduplicate SHEPHERD KG edge list rows."
    )
    parser.add_argument("--input", required=True, help="Path to KG_edgelist_mask.txt")
    parser.add_argument(
        "--output",
        help="Optional output path for deduplicated edge list. If omitted, only a report is produced.",
    )
    parser.add_argument(
        "--conflict-policy",
        choices=["keep-first", "prefer-train", "prefer-val", "prefer-test"],
        default="keep-first",
        help="How to resolve split conflicts for the same typed edge.",
    )
    return parser.parse_args()


def resolve_conflicts(df: pd.DataFrame, policy: str) -> pd.DataFrame:
    if policy == "keep-first":
        return df.drop_duplicates(subset=EDGE_KEY, keep="first")

    priority_map = {
        "prefer-train": {"train": 0, "val": 1, "test": 2},
        "prefer-val": {"val": 0, "train": 1, "test": 2},
        "prefer-test": {"test": 0, "val": 1, "train": 2},
    }[policy]

    ranked = df.copy()
    ranked["_mask_rank"] = ranked["mask"].map(priority_map).fillna(99)
    ranked = ranked.sort_values(by=EDGE_KEY + ["_mask_rank"])
    ranked = ranked.drop_duplicates(subset=EDGE_KEY, keep="first")
    return ranked.drop(columns=["_mask_rank"])


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    df = pd.read_csv(input_path, sep="\t")

    required_cols = set(FULL_KEY)
    missing = required_cols - set(df.columns)
    if missing:
        raise SystemExit(f"Missing required columns: {sorted(missing)}")

    exact_duplicate_rows = int(df.duplicated(subset=FULL_KEY, keep=False).sum())
    exact_duplicate_groups = (
        df[df.duplicated(subset=FULL_KEY, keep=False)]
        .groupby(FULL_KEY, dropna=False)
        .size()
        .reset_index(name="count")
    )

    split_conflicts = (
        df.groupby(EDGE_KEY, dropna=False)["mask"]
        .nunique()
        .reset_index(name="n_masks")
    )
    split_conflicts = split_conflicts[split_conflicts["n_masks"] > 1]

    print(f"Input rows: {len(df)}")
    print(f"Exact duplicate rows (same edge + same mask): {exact_duplicate_rows}")
    print(f"Exact duplicate groups: {len(exact_duplicate_groups)}")
    print(f"Split conflict groups (same typed edge, multiple masks): {len(split_conflicts)}")

    if len(exact_duplicate_groups) > 0:
        print("\nSample exact duplicate groups:")
        print(exact_duplicate_groups.head(10).to_string(index=False))

    if len(split_conflicts) > 0:
        print("\nSample split conflicts:")
        sample_conflicts = split_conflicts.head(10).merge(
            df, on=EDGE_KEY, how="left"
        ).sort_values(by=EDGE_KEY + ["mask"])
        print(sample_conflicts.to_string(index=False))

    if not args.output:
        return 0

    deduped = df.drop_duplicates(subset=FULL_KEY, keep="first")
    deduped = resolve_conflicts(deduped, args.conflict_policy)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    deduped.to_csv(output_path, sep="\t", index=False)

    print(f"\nWrote deduplicated edge list: {output_path}")
    print(f"Output rows: {len(deduped)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
