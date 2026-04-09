
import pandas as pd
from pathlib import Path

kg = Path("/home/ubuntu/Data/Sheperd/OriginalFromHU/knowledge_graph/8.9.21_kg")
raw = pd.read_csv(kg / "KG_node_map.txt", sep="\t")
print(raw[raw["node_type"]=="gene/protein"][["node_id","node_name"]].head(10).to_string(index=False))

ens = kg / "KG_node_map_ensembl_ids.txt"
print("has normalized map:", ens.exists())
if ens.exists():
    df = pd.read_csv(ens, sep="\t")
    print(df[df["node_type"]=="gene/protein"][["node_id","node_name"]].head(10).to_string(index=False))

