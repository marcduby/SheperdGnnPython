# SHEPHERD CPU / Python 3.10 Migration

## Why

The upstream repository is pinned to an older CUDA-era stack:

- `python=3.8.8`
- `pytorch=1.8.0`
- `pytorch-lightning==1.4.5`
- `cudatoolkit=10.2.89`
- `faiss-gpu=1.7.0`
- `allennlp==2.4.0`
- a legacy `install_pyg.sh` flow for PyG 1.7.2

That stack is not a straightforward fit for a CPU-only Python 3.10 setup. This migration keeps changes narrow and additive:

- new CPU/Python 3.10 environment files
- targeted code compatibility patches
- preserved CLI entry points via root wrappers: `pretrain.py`, `train.py`, `predict.py`

## New Setup

Recommended environment files:

- `environment.cpu-py310.yml`
- `requirements.cpu-py310.txt`
- `install_cpu_py310.sh`

### Conda path

```bash
conda env create -f environment.cpu-py310.yml
conda activate shepherd-cpu-py310
```

### Existing virtualenv path used for validation

```bash
. ~/Energy/VirtualEnv/sheperdgnn_310/bin/activate
python -m pip install -r requirements.cpu-py310.txt
```

### Data path

`project_config.py` now resolves `PROJECT_DIR` from `SHEPHERD_DATA_DIR`, defaulting to `./data` under the repo:

```bash
export SHEPHERD_DATA_DIR=/path/to/shepherd-data
```

## What Changed

### Dependencies

- Removed CUDA-only requirements from the new setup.
- Dropped `allennlp` from the CPU/Python 3.10 environment.
- Replaced the legacy PyG install flow with pinned pip requirements for CPU wheels.
- Kept the stack conservative:
  - `torch==2.1.2`
  - `pytorch-lightning==1.9.5`
  - `torch-geometric==2.5.3`
- Removed unnecessary `torchvision` and `torchaudio` from the new environment because this machine's Python 3.10.8 build is missing `_lzma`, and newer `torchmetrics` pulled `torchvision` during Lightning import.
- Pinned `torchmetrics==0.11.4` to keep Lightning importable without that `lzma` path.

### Code patches

- Added local attention implementations in `shepherd/attention.py` to replace the small AllenNLP attention surface used by the task heads.
- Added `shepherd/compat.py` for CPU/GPU trainer selection and path resolution.
- Switched Lightning trainer construction away from `gpus=...` to `accelerator` / `devices` kwargs.
- Changed default hyperparameters to use CPU automatically when CUDA is unavailable.
- Fixed `get_pretrain_hparams()` so `pretrain.py --max_epochs` is respected.
- Added a bounded `--debug` mode to `pretrain.py` for fast smoke tests.
- Replaced deprecated/internal PyG imports:
  - `torch_geometric.loader.DataLoader`
  - local `EdgeIndex` / `Adj` wrappers instead of internal PyG sampler types
- Fixed a hardcoded degree-dictionary path in `shepherd/train.py` to use `project_config.KG_DIR`.
- Fixed `HeterogeneousEdgeIndex.to()` to return the correct type.
- Removed an in-place tensor mutation in `shepherd/node_embedder_model.py` that caused a backward-pass autograd failure during CPU pretraining.
- Updated `trainer.test(...)` usage for Lightning 1.9 compatibility and made the post-fit checkpoint selection robust for smoke runs.
- Added root wrapper scripts:
  - `pretrain.py`
  - `train.py`
  - `predict.py`
- Fixed `shepherd/predict.py` to import from `shepherd.train` instead of the new root wrapper.

## Validation Log

Validation was run with:

```bash
. ~/Energy/VirtualEnv/sheperdgnn_310/bin/activate
```

### 1. Syntax check

Command:

```bash
python -m py_compile project_config.py pretrain.py train.py predict.py shepherd/*.py shepherd/task_heads/*.py shepherd/utils/*.py
```

Result:

- success

### 2. Import smoke test

Command:

```bash
python - <<'PY'
mods = ['torch','pytorch_lightning','torch_geometric','wandb','pytorch_metric_learning','numpy']
for name in mods:
    mod = __import__(name)
    print(name, getattr(mod, '__version__', 'n/a'))
PY
```

Result:

```text
torch 2.1.2
pytorch_lightning 1.9.5
torch_geometric 2.5.3
wandb 0.18.1
pytorch_metric_learning 1.7.3
numpy 1.26.4
```

### 3. CLI smoke tests

Commands:

```bash
python pretrain.py --help
python train.py --help
python predict.py --help
```

Result:

- all three entry points started successfully and printed argparse help

### 4. Real KG-backed CPU smoke test

Command:

```bash
export SHEPHERD_DATA_DIR=/Users/mduby/Data/Broad/PortalAI/Sheperd/OriginalFromHU
export WANDB_MODE=offline
. ~/Energy/VirtualEnv/sheperdgnn_310/bin/activate

python pretrain.py \
  --edgelist /Users/mduby/Data/Broad/PortalAI/Sheperd/OriginalFromHU/knowledge_graph/8.9.21_kg/KG_edgelist_mask.txt \
  --node_map /Users/mduby/Data/Broad/PortalAI/Sheperd/OriginalFromHU/knowledge_graph/8.9.21_kg/KG_node_map.txt \
  --save_dir /tmp/shepherd-smoke \
  --max_epochs 3 \
  --debug
```

Result:

- success
- completed sanity check
- completed 3 bounded train/validation epochs on CPU
- restored the best checkpoint from `/tmp/shepherd-smoke/checkpoints/...`
- completed a 1-batch test pass
- produced test metrics without crashing

## Known Limitations

- No end-to-end train or predict run was executed here because the required SHEPHERD datasets / checkpoints were not available in this workspace.
- The exported data path used for validation contains the knowledge graph files, but not the expected `patients/` and `checkpoints/` subtrees for the higher-level training and prediction CLIs.
- `project_config.py` still contains legacy dataset examples for `MY_TEST_DATA` / SPL-related paths; those are not rewritten automatically and should be overridden with your own data path configuration when used.
- This migration targets CPU execution and import/runtime compatibility, not numerical parity with the original CUDA-era environment.

## Recommended Smoke Test After Data Is Present

```bash
export SHEPHERD_DATA_DIR=/path/to/shepherd-data
. ~/Energy/VirtualEnv/sheperdgnn_310/bin/activate

python pretrain.py --help
python train.py --help
python predict.py --help
```

If checkpoints and data are available, the next practical smoke test is:

```bash
python predict.py \
  --run_type causal_gene_discovery \
  --patient_data my_data \
  --edgelist KG_edgelist_mask.txt \
  --node_map KG_node_map.txt \
  --saved_node_embeddings_path checkpoints/pretrain.ckpt \
  --best_ckpt checkpoints/causal_gene_discovery.ckpt
```
