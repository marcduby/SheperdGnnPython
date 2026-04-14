

import json, pickle
from pathlib import Path
import os

# get root
ROOT_DATA = os.getenv('SHEPHERD_DATA_DIR', '/')
root = Path(ROOT_DATA)
print("using data root: {}".format(ROOT_DATA))
# root = Path("/home/ubuntu/Data/Sheperd/HuAndPigeanHpData")

# get the files
with open(root / "knowledge_graph/8.9.21_kg/ensembl_to_idx_dict_8.9.21_kg.pkl", "rb") as f:
    gene_map = pickle.load(f)

with open(root / "patients/my_cohort/train.jsonl") as f:
    rec = json.loads(next(f))

candidate_genes = rec["all_candidate_genes"]
true_genes = rec["true_genes"]

print("sample gene map keys:", list(gene_map.keys())[:20])
print("sample candidate genes:", candidate_genes[:20])
print("mapped candidates:", sum(g in gene_map for g in candidate_genes), "of", len(candidate_genes))
print("sample true genes:", true_genes)
print("mapped true genes:", sum(g in gene_map for g in true_genes), "of", len(true_genes))


