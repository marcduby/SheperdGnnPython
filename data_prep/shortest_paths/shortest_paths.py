import argparse
import multiprocessing
import numpy as np
import sys
import time
import snap
import pandas as pd

import sys
#sys.path.insert(0, '..') # add config to path
sys.path.insert(0, '../..') # add config to path
import project_config

def parse_args():
    parser = argparse.ArgumentParser(description="Compute KG shortest path matrices.")
    parser.add_argument("--suffix", default="", help="Optional KG filename suffix, e.g. '_noGO'")
    parser.add_argument("--processes", type=int, default=20, help="Worker processes for SNAP shortest paths")
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
    snap_graph = snap.LoadEdgeList(snap.PUNGraph, str(project_config.KG_DIR / edgelist_f), 0, 1)

    t0 = time.time()

    node_ids = np.sort([node.GetId() for node in snap_graph.Nodes()])
    n_nodes = len(node_map)
    print(n_nodes, len(list(snap_graph.Nodes())), len(node_ids))
    print(f'There are {n_nodes} nodes in the graph')
    assert max(node_ids) == n_nodes - 1
    if "noGO" not in edgelist_f:
        assert len(node_map) == len(node_ids)

    def get_shortest_path(node_id):
        n_id_to_dist = snap.TIntH()
        snap.GetShortPath(snap_graph, int(node_id), n_id_to_dist)
        paths = np.zeros((n_nodes))
        for dest_node in n_id_to_dist:
            paths[dest_node] = n_id_to_dist[dest_node]
        return paths

    with multiprocessing.Pool(processes=args.processes) as pool:
        shortest_paths = pool.map(get_shortest_path, node_ids)

    all_shortest_paths = np.stack(shortest_paths)
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

