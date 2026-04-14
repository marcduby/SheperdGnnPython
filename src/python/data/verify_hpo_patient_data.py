

import json, pickle
from pathlib import Path
import os

# get root
ROOT_DATA = os.getenv('SHEPHERD_DATA_DIR', '/')
root = Path(ROOT_DATA)
print("using data root: {}".format(ROOT_DATA))

# get the files
with open(root / "knowledge_graph/8.9.21_kg/hpo_to_idx_dict_8.9.21_kg.pkl", "rb") as f:
    hpo = pickle.load(f)
with open(root / "patients/my_cohort/train.jsonl") as f:
    rec = json.loads(next(f))

vals = rec["positive_phenotypes"]
print("sample hpo keys:", list(hpo.keys())[:10])
print("sample patient phenotypes:", vals[:10])
print("mapped", sum(v in hpo for v in vals), "of", len(vals))


# get root
ROOT_DATA = os.getenv('SHEPHERD_DATA_DIR', '/')
root = Path(ROOT_DATA)
print("using data root: {}".format(ROOT_DATA))

p = root / "knowledge_graph/8.9.21_kg/hpo_to_idx_dict_8.9.21_kg.pkl"

with open(p, "rb") as f:
    hpo = pickle.load(f)

keys = list(hpo.keys())[:20]
print(keys)
print("hp-style keys:", sum(str(k).startswith("HP:") for k in keys), "of", len(keys))

