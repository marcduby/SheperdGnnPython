#!/usr/bin/env python3
from __future__ import annotations

import os
import pickle
from pathlib import Path

import pandas as pd


CURR_KG = "8.9.21_kg"


def get_root() -> Path:
    value = os.environ.get("SHEPHERD_DATA_DIR")
    if not value:
        raise SystemExit("SHEPHERD_DATA_DIR is not set")
    return Path(value).expanduser()


def save_pickle(obj, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as handle:
        pickle.dump(obj, handle)


def build_maps(node_map_path: Path, edge_list_path: Path) -> list[Path]:
    nodes = pd.read_csv(node_map_path, sep="\t")
    edges = pd.read_csv(edge_list_path, sep="\t")

    phen = nodes[nodes["node_type"] == "effect/phenotype"]
    genes = nodes[nodes["node_type"] == "gene/protein"]
    diseases = nodes[nodes["node_type"] == "disease"]

    # phen["node_id"].astype(str) — takes the node_id column from a DataFrame called phen and converts all values to strings (e.g., "HP:0001234").
    # phen["node_idx"] — takes the node_idx column, which contains integer index values.
    # zip(..., ...) — pairs up each node_id with its corresponding node_idx at the same row position, producing tuples like ("HP:0001234", 42).
    # dict(...) — converts those pairs into a dictionary, so you end up with something like:
    
    hpo_to_idx = dict(zip(phen["node_id"].astype(str), phen["node_idx"]))
    hpo_to_name = dict(zip(phen["node_id"].astype(str), phen["node_name"].astype(str)))
    ensembl_to_idx = dict(zip(genes["node_id"].astype(str), genes["node_idx"]))
    mondo_to_idx = dict(zip(diseases["node_id"].astype(str), diseases["node_idx"]))
    mondo_to_name = dict(zip(diseases["node_id"].astype(str), diseases["node_name"].astype(str)))

    degree_counts: dict[int, int] = {}
    for node_idx in pd.concat([edges["x_idx"], edges["y_idx"]]).astype(int):
        degree_counts[node_idx] = degree_counts.get(node_idx, 0) + 1

    kg_dir = node_map_path.parent
    outputs = [
        (hpo_to_idx, kg_dir / f"hpo_to_idx_dict_{CURR_KG}.pkl"),
        (hpo_to_name, kg_dir / f"hpo_to_name_dict_{CURR_KG}.pkl"),
        (ensembl_to_idx, kg_dir / f"ensembl_to_idx_dict_{CURR_KG}.pkl"),
        (mondo_to_idx, kg_dir / f"mondo_to_idx_dict_{CURR_KG}.pkl"),
        (mondo_to_name, kg_dir / f"mondo_to_name_dict_{CURR_KG}.pkl"),
        (degree_counts, kg_dir / f"degree_dict_{CURR_KG}.pkl"),
    ]

    written = []
    for obj, path in outputs:
        save_pickle(obj, path)
        written.append(path)
    return written


def main() -> int:
    root = get_root()
    kg_dir = root / "knowledge_graph" / CURR_KG
    node_map_path = kg_dir / "KG_node_map.txt"
    edge_list_path = kg_dir / "KG_edgelist_mask.txt"

    if not node_map_path.exists():
        raise SystemExit(f"Missing node map: {node_map_path}")
    if not edge_list_path.exists():
        raise SystemExit(f"Missing edge list: {edge_list_path}")

    written = build_maps(node_map_path, edge_list_path)
    print("Wrote:")
    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
