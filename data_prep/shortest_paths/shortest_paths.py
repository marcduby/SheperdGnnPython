import argparse
import numpy as np
import sys
import time
import pandas as pd
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import shortest_path

import sys
#sys.path.insert(0, '..') # add config to path
sys.path.insert(0, '../..') # add config to path
import project_config

def parse_args():
    parser = argparse.ArgumentParser(description="Compute KG shortest path matrices.")
    parser.add_argument("--suffix", default="", help="Optional KG filename suffix, e.g. '_noGO'")
    return parser.parse_args()


def main():
    args = parse_args()

    suffix = args.suffix
    edgelist_f = f"KG_edgelist_mask{suffix}.txt"
    nodemap_f = f"KG_node_map{suffix}.txt"
    spl_mat_all_f = f"KG_shortest_path_matrix{suffix}.npy"
    spl_mat_onlyphenotypes_f = f"KG_shortest_path_matrix_onlyphenotypes{suffix}.npy"

    print("Filenames:")
    print(edgelist_f)
    print(nodemap_f)
    print(spl_mat_all_f)
    print(spl_mat_onlyphenotypes_f)

    print("Starting to calculate shortest paths...")

    node_map = pd.read_csv(project_config.KG_DIR / nodemap_f, sep="\t")
    edge_df = pd.read_csv(project_config.KG_DIR / edgelist_f, sep="\t")

    t0 = time.time()

    n_nodes = len(node_map)
    print(f'There are {n_nodes} nodes in the graph')
    assert node_map["node_idx"].max() == n_nodes - 1

    rows = edge_df["x_idx"].to_numpy(dtype=np.int64)
    cols = edge_df["y_idx"].to_numpy(dtype=np.int64)
    data = np.ones(len(edge_df), dtype=np.float32)
    adjacency = coo_matrix((data, (rows, cols)), shape=(n_nodes, n_nodes))
    adjacency = adjacency.maximum(adjacency.transpose()).tocsr()

    all_shortest_paths = shortest_path(adjacency, directed=False, unweighted=True)
    print(all_shortest_paths.shape)
    t1 = time.time()
    print(f'It took {t1-t0:0.4f}s to calculate the shortest paths')

    if "noGO" not in spl_mat_all_f:
        np.save(project_config.KG_DIR / spl_mat_all_f, all_shortest_paths)

    desired_idx = node_map[node_map["node_type"] == "effect/phenotype"]["node_idx"].tolist()
    all_shortest_paths_to_phens = all_shortest_paths[:, desired_idx]
    with open(project_config.KG_DIR / spl_mat_onlyphenotypes_f, "wb") as f:
        np.save(f, all_shortest_paths_to_phens)


if __name__ == "__main__":
    main()
