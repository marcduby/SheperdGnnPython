
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

  