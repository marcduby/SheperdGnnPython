# Shepherd GNN Codex — KG Refresh & Training Pipeline

## Assumptions

| Variable | Value |
|---|---|
| Repo root | `~/Code/SheperdGnnCodex` |
| Data root | `$SHEPHERD_DATA_DIR` |
| KG path | `$SHEPHERD_DATA_DIR/knowledge_graph/8.9.21_kg` |

---

## Environment Setup

```bash
export SHEPHERD_DATA_DIR=/path/to/data-root
export WANDB_MODE=offline
. ~/Energy/VirtualEnv/sheperd_31012/bin/activate
cd ~/Code/SheperdGnnCodex
```

---

## Step 1 — Report Duplicate / Conflicting Edges

```bash
python src/python/dedupe_kg_edges.py \
  --input "$SHEPHERD_DATA_DIR/knowledge_graph/8.9.21_kg/KG_edgelist_mask.txt"
```

---

## Step 2 — Write a Cleaned Edge List

> **Recommended policy:** `prefer-train`

```bash
python src/python/dedupe_kg_edges.py \
  --input  "$SHEPHERD_DATA_DIR/knowledge_graph/8.9.21_kg/KG_edgelist_mask.txt" \
  --output "$SHEPHERD_DATA_DIR/knowledge_graph/8.9.21_kg/KG_edgelist_mask_dedup.txt" \
  --conflict-policy prefer-train
```

If the report looks good, replace the working file:

```bash
cp "$SHEPHERD_DATA_DIR/knowledge_graph/8.9.21_kg/KG_edgelist_mask.txt" \
   "$SHEPHERD_DATA_DIR/knowledge_graph/8.9.21_kg/KG_edgelist_mask.backup.txt"

cp "$SHEPHERD_DATA_DIR/knowledge_graph/8.9.21_kg/KG_edgelist_mask_dedup.txt" \
   "$SHEPHERD_DATA_DIR/knowledge_graph/8.9.21_kg/KG_edgelist_mask.txt"
```

---

## Step 3 — Recompute KG Shortest Paths

```bash
cd data_prep/shortest_paths
python shortest_paths.py
```

**Regenerates:**

- `KG_shortest_path_matrix_onlyphenotypes.npy`

---

## Step 4 — Recompute Patient SPL Artifacts

**Train / val SPL:**

```bash
python add_spl_to_patients.py \
  --save_prefix train_val \
  --agg_type mean \
  --only_train_val_data
```

**Test SPL:**

```bash
python add_spl_to_patients.py \
  --save_prefix test \
  --agg_type mean \
  --only_test_data
```

**Produces:**

- `patients/my_cohort/train_val_agg=mean_spl_matrix.npy`
- `patients/my_cohort/train_val_agg=mean_spl_index_dict.pkl`
- `patients/my_cohort/test_agg=mean_spl_matrix.npy`
- `patients/my_cohort/test_agg=mean_spl_index_dict.pkl`

---

## Step 5 — Pretrain on the Deduplicated / Augmented KG

Return to repo root:

```bash
cd ~/Code/SheperdGnnCodex
```

**Optional smoke test first:**

```bash
python pretrain.py \
  --edgelist KG_edgelist_mask.txt \
  --node_map KG_node_map.txt \
  --save_dir /tmp/shepherd-pretrain \
  --max_epochs 3 \
  --debug
```

**Full pretrain run:**

```bash
python pretrain.py \
  --edgelist KG_edgelist_mask.txt \
  --node_map KG_node_map.txt \
  --save_dir /tmp/shepherd-pretrain
```

Copy the chosen checkpoint:

```bash
mkdir -p "$SHEPHERD_DATA_DIR/checkpoints"
cp /tmp/shepherd-pretrain/checkpoints/<BEST_PRETRAIN_CKPT>.ckpt \
   "$SHEPHERD_DATA_DIR/checkpoints/pretrain.ckpt"
```

---

## Step 6 — Train Causal Gene Discovery

```bash
python train.py \
  --edgelist KG_edgelist_mask.txt \
  --node_map KG_node_map.txt \
  --patient_data my_data \
  --run_type causal_gene_discovery \
  --saved_node_embeddings_path checkpoints/pretrain.ckpt
```

---

## Step 7 — Predict on Held-Out Test

After training, locate the best model checkpoint under:

```
$SHEPHERD_DATA_DIR/checkpoints/aligner/<run_name>/
```

Then run:

```bash
python predict.py \
  --run_type causal_gene_discovery \
  --patient_data my_data \
  --edgelist KG_edgelist_mask.txt \
  --node_map KG_node_map.txt \
  --saved_node_embeddings_path checkpoints/pretrain.ckpt \
  --best_ckpt checkpoints/aligner/<run_name>/<best_model>.ckpt
```

**Uses:**

- `test.jsonl`
- `test_agg=mean_spl_matrix.npy`
- `test_agg=mean_spl_index_dict.pkl`
