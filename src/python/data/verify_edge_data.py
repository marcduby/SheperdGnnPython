

import json, pickle
from pathlib import Path

root = Path("/home/ubuntu/Data/Sheperd/HuAndPigeanHpData")
with open(root / "knowledge_graph/8.9.21_kg/hpo_to_idx_dict_8.9.21_kg.pkl", "rb") as f:
    hpo = pickle.load(f)
with open(root / "patients/my_cohort/train.jsonl") as f:
    rec = json.loads(next(f))

vals = rec["positive_phenotypes"]
print("sample hpo keys:", list(hpo.keys())[:10])
print("sample patient phenotypes:", vals[:10])
print("mapped", sum(v in hpo for v in vals), "of", len(vals))


root = Path("/home/ubuntu/Data/Sheperd/HuAndPigeanHpData")
p = root / "knowledge_graph/8.9.21_kg/hpo_to_idx_dict_8.9.21_kg.pkl"

with open(p, "rb") as f:
    hpo = pickle.load(f)

keys = list(hpo.keys())[:20]
print(keys)
print("hp-style keys:", sum(str(k).startswith("HP:") for k in keys), "of", len(keys))

