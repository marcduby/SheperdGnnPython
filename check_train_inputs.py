#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path


CURR_KG = "8.9.21_kg"


def env_path() -> Path:
    value = os.environ.get("SHEPHERD_DATA_DIR")
    if not value:
        raise SystemExit("SHEPHERD_DATA_DIR is not set")
    return Path(value).expanduser()


def check_exists(path: Path) -> tuple[bool, str]:
    return path.exists(), str(path)


def check_jsonl_sample(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, f"missing: {path}"
    try:
        first_line = path.read_text().splitlines()[0]
        record = json.loads(first_line)
    except Exception as exc:
        return False, f"invalid jsonl: {path} ({exc})"

    required = ["id", "positive_phenotypes", "all_candidate_genes", "true_genes"]
    missing = [key for key in required if key not in record]
    if missing:
        return False, f"missing fields {missing} in first record: {path}"
    if not record["positive_phenotypes"]:
        return False, f"empty positive_phenotypes in first record: {path}"
    return True, f"ok: {path}"


def main() -> int:
    root = env_path()

    checks = [
        ("KG edge list", root / "knowledge_graph" / CURR_KG / "KG_edgelist_mask.txt", check_exists),
        ("KG node map", root / "knowledge_graph" / CURR_KG / "KG_node_map.txt", check_exists),
        ("HPO idx map", root / "knowledge_graph" / CURR_KG / f"hpo_to_idx_dict_{CURR_KG}.pkl", check_exists),
        ("HPO name map", root / "knowledge_graph" / CURR_KG / f"hpo_to_name_dict_{CURR_KG}.pkl", check_exists),
        ("Ensembl idx map", root / "knowledge_graph" / CURR_KG / f"ensembl_to_idx_dict_{CURR_KG}.pkl", check_exists),
        ("MONDO idx map", root / "knowledge_graph" / CURR_KG / f"mondo_to_idx_dict_{CURR_KG}.pkl", check_exists),
        ("MONDO name map", root / "knowledge_graph" / CURR_KG / f"mondo_to_name_dict_{CURR_KG}.pkl", check_exists),
        ("Degree map", root / "knowledge_graph" / CURR_KG / f"degree_dict_{CURR_KG}.pkl", check_exists),
        ("Orphanet map", root / "preprocess" / "orphanet" / "orphanet_to_mondo_dict.pkl", check_exists),
        ("Train JSONL", root / "patients" / "my_cohort" / "train.jsonl", check_jsonl_sample),
        ("Val JSONL", root / "patients" / "my_cohort" / "val.jsonl", check_jsonl_sample),
        ("Test JSONL", root / "patients" / "my_cohort" / "test.jsonl", check_jsonl_sample),
        ("SPL matrix", root / "patients" / "my_cohort" / "test_agg=mean_spl_matrix.npy", check_exists),
        ("SPL index", root / "patients" / "my_cohort" / "test_agg=mean_spl_index_dict.pkl", check_exists),
        ("Pretrain checkpoint", root / "checkpoints" / "pretrain.ckpt", check_exists),
    ]

    failures = 0
    print(f"SHEPHERD_DATA_DIR={root}")
    for label, path, fn in checks:
        ok, detail = fn(path)
        status = "OK" if ok else "MISSING"
        print(f"[{status}] {label}: {detail}")
        if not ok:
            failures += 1

    if failures:
        print(f"\n{failures} required inputs are missing or invalid.")
        return 1

    print("\nAll checked inputs are present for train.py --patient_data my_data --run_type causal_gene_discovery")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
