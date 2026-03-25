
Yes. The repo’s rebuild path for those two files is:

1. Build the KG shortest-path matrix
2. Derive the patient-level SPL artifacts from it

The exact scripts are:

- `data_prep/shortest_paths/shortest_paths.py`
- `data_prep/shortest_paths/add_spl_to_patients.py`

What each one does:

- `shortest_paths.py`
  - Reads the KG
  - Computes all-pairs shortest paths
  - Writes `KG_shortest_path_matrix_onlyphenotypes.npy` in `project_config.KG_DIR`

- `add_spl_to_patients.py`
  - Reads your patient JSONL files
  - Reads `KG_shortest_path_matrix_onlyphenotypes.npy`
  - Aggregates phenotype-to-gene shortest path values per patient
  - Writes:
    - `*_spl_matrix.npy`
    - `*_spl_index_dict.pkl`

The output naming is defined directly in `data_prep/shortest_paths/add_spl_to_patients.py`:

- Matrix:
  - `project_config.MY_DATA_DIR / f'{args.save_prefix}_agg={args.agg_type}_spl_matrix.npy'`

- Index dict:
  - `project_config.MY_DATA_DIR / f'{args.save_prefix}_spl_index_dict.pkl'`


## How do I modify `project_config.py` for the newly generated train, val, and test data?

Point the `MY_*` paths at your new cohort directory under `patients/`.

In `project_config.py`, set:

```python
MY_DATA_DIR = Path("my_cohort")
MY_TRAIN_DATA = MY_DATA_DIR / "train.jsonl"
MY_VAL_DATA = MY_DATA_DIR / "val.jsonl"
MY_TEST_DATA = MY_DATA_DIR / "test.jsonl"

MY_SPL_DATA = MY_DATA_DIR / "test_agg=mean_spl_matrix.npy"
MY_SPL_INDEX_DATA = MY_DATA_DIR / "test_spl_index_dict.pkl"

- These should be relative to PROJECT_DIR / 'patients'
  - $SHEPHERD_DATA_DIR/patients/my_cohort/train.jsonl
  - $SHEPHERD_DATA_DIR/patients/my_cohort/val.jsonl
  - $SHEPHERD_DATA_DIR/patients/my_cohort/test.jsonl


