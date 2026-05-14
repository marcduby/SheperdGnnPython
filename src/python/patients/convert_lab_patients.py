from pathlib import Path
import argparse
import csv
import json
import pickle
import re
import sys

REPO_DIR = Path(__file__).resolve().parents[3]
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

import project_config


MISSING_VALUES = {"", "NA", "N/A", "na", "n/a", "null", "None"}
HPO_PATTERN = re.compile(r"^HP:\d{7}$")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Convert a lab TSV patient file into SHEPHERD JSONL format for prediction."
    )
    parser.add_argument(
        "input_tsv",
        help="Path to the lab TSV file with sample_id and HPO columns.",
    )
    parser.add_argument(
        "--output",
        help="Output JSONL path. Defaults to <input_dir>/crdc_26k_test.json",
    )
    parser.add_argument(
        "--primary-hpo-column",
        default="HPO_add_parent",
        help="Preferred HPO column to use when present. Default: HPO_add_parent",
    )
    parser.add_argument(
        "--fallback-hpo-column",
        default="HPO_terms_clinithink",
        help="Fallback HPO column if the primary column is empty. Default: HPO_terms_clinithink",
    )
    return parser.parse_args()


def normalize_hpo_list(raw_value: str):
    if raw_value is None:
        return []
    value = raw_value.strip()
    if value in MISSING_VALUES:
        return []

    terms = re.split(r"[;,]\s*", value)
    seen = set()
    normalized = []
    for term in terms:
        term = term.strip()
        if not term or term in MISSING_VALUES:
            continue
        if not HPO_PATTERN.fullmatch(term):
            continue
        if term in seen:
            continue
        seen.add(term)
        normalized.append(term)
    return normalized


def load_all_candidate_genes():
    ensembl_path = project_config.KG_DIR / f"ensembl_to_idx_dict_{project_config.CURR_KG}.pkl"
    with ensembl_path.open("rb") as handle:
        ensembl_to_idx = pickle.load(handle)
    return sorted(ensembl_to_idx.keys())


def pick_hpo_terms(row, primary_column: str, fallback_column: str):
    primary_terms = normalize_hpo_list(row.get(primary_column, ""))
    if primary_terms:
        return primary_terms, primary_column
    fallback_terms = normalize_hpo_list(row.get(fallback_column, ""))
    return fallback_terms, fallback_column


def convert_lab_patients(input_tsv: Path, output_jsonl: Path, primary_column: str, fallback_column: str):
    all_candidate_genes = load_all_candidate_genes()

    total_rows = 0
    written_rows = 0
    dropped_rows = 0
    used_primary = 0
    used_fallback = 0

    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with input_tsv.open(newline="") as input_file, output_jsonl.open("w") as output_file:
        reader = csv.DictReader(input_file, delimiter="\t")
        required_columns = {"sample_id", primary_column, fallback_column}
        missing_columns = required_columns.difference(reader.fieldnames or [])
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"{input_tsv} is missing required columns: {missing}")

        for row in reader:
            total_rows += 1
            positive_phenotypes, source_column = pick_hpo_terms(row, primary_column, fallback_column)
            if not positive_phenotypes:
                dropped_rows += 1
                continue

            if source_column == primary_column:
                used_primary += 1
            else:
                used_fallback += 1

            patient = {
                "id": row["sample_id"].strip(),
                "positive_phenotypes": positive_phenotypes,
                "all_candidate_genes": all_candidate_genes,
                "true_genes": [],
            }
            json.dump(patient, output_file)
            output_file.write("\n")
            written_rows += 1

    print(f"Input file: {input_tsv}")
    print(f"Output file: {output_jsonl}")
    print(f"Total input rows: {total_rows}")
    print(f"Wrote patients: {written_rows}")
    print(f"Dropped rows with no usable HPO terms: {dropped_rows}")
    print(f"Rows using {primary_column}: {used_primary}")
    print(f"Rows using {fallback_column}: {used_fallback}")
    print(f"Candidate genes per patient: {len(all_candidate_genes)}")


def main():
    args = parse_args()
    input_tsv = Path(args.input_tsv)
    output_jsonl = Path(args.output) if args.output else input_tsv.parent / "crdc_26k_test.json"
    convert_lab_patients(
        input_tsv=input_tsv,
        output_jsonl=output_jsonl,
        primary_column=args.primary_hpo_column,
        fallback_column=args.fallback_hpo_column,
    )


if __name__ == "__main__":
    main()
