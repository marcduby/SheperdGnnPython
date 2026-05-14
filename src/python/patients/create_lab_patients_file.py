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
GENE_SAMPLE_SUFFIX_PATTERN = re.compile(r"_E\d+$")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create a SHEPHERD test.jsonl-style patient file by joining lab gene and phenotype TSVs."
    )
    parser.add_argument("gene_tsv", help="Path to the patient gene TSV file.")
    parser.add_argument("phenotype_tsv", help="Path to the patient phenotype TSV file.")
    parser.add_argument(
        "--output",
        help="Output JSONL path. Defaults to <phenotype_dir>/<phenotype_stem>_test.jsonl",
    )
    parser.add_argument(
        "--primary-hpo-column",
        default="HPO_add_parent",
        help="Preferred HPO column when present. Default: HPO_add_parent",
    )
    parser.add_argument(
        "--fallback-hpo-column",
        default="HPO_terms_clinithink",
        help="Fallback HPO column if the primary column is empty. Default: HPO_terms_clinithink",
    )
    parser.add_argument(
        "--gene-id-column",
        default="gene_id",
        help="Gene identifier column in the gene TSV. Default: gene_id",
    )
    return parser.parse_args()


def normalize_sample_id(sample_id: str):
    return GENE_SAMPLE_SUFFIX_PATTERN.sub("", sample_id.strip())


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


def pick_hpo_terms(row, primary_column: str, fallback_column: str):
    primary_terms = normalize_hpo_list(row.get(primary_column, ""))
    if primary_terms:
        return primary_terms, primary_column
    fallback_terms = normalize_hpo_list(row.get(fallback_column, ""))
    return fallback_terms, fallback_column


def load_gene_symbol_to_ensembl():
    gene_symbol_path = project_config.KG_DIR / f"gene_symbol_to_idx_dict_{project_config.CURR_KG}.pkl"
    ensembl_path = project_config.KG_DIR / f"ensembl_to_idx_dict_{project_config.CURR_KG}.pkl"

    with gene_symbol_path.open("rb") as handle:
        gene_symbol_to_idx = pickle.load(handle)
    with ensembl_path.open("rb") as handle:
        ensembl_to_idx = pickle.load(handle)

    idx_to_ensembl = {idx: ensembl for ensembl, idx in ensembl_to_idx.items()}
    gene_symbol_to_ensembl = {}
    for gene_symbol, idx in gene_symbol_to_idx.items():
        ensembl = idx_to_ensembl.get(idx)
        if ensembl is not None:
            gene_symbol_to_ensembl[gene_symbol] = ensembl
    return gene_symbol_to_ensembl, set(ensembl_to_idx.keys())


def load_patient_gene_candidates(gene_tsv: Path, gene_id_column: str):
    gene_symbol_to_ensembl, all_ensembl_ids = load_gene_symbol_to_ensembl()
    patient_to_genes = {}
    total_rows = 0
    dropped_missing_gene = 0

    with gene_tsv.open(newline="") as input_file:
        reader = csv.DictReader(input_file, delimiter="\t")
        required_columns = {"sample_id", gene_id_column}
        missing_columns = required_columns.difference(reader.fieldnames or [])
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"{gene_tsv} is missing required columns: {missing}")

        for row in reader:
            total_rows += 1
            normalized_sample_id = normalize_sample_id(row["sample_id"])
            raw_gene_id = row[gene_id_column].strip()
            if not raw_gene_id or raw_gene_id in MISSING_VALUES:
                dropped_missing_gene += 1
                continue

            if raw_gene_id in all_ensembl_ids:
                ensembl_id = raw_gene_id
            else:
                ensembl_id = gene_symbol_to_ensembl.get(raw_gene_id)

            if ensembl_id is None:
                dropped_missing_gene += 1
                continue

            patient_to_genes.setdefault(normalized_sample_id, set()).add(ensembl_id)

    return patient_to_genes, total_rows, dropped_missing_gene


def create_lab_patients_file(
    gene_tsv: Path,
    phenotype_tsv: Path,
    output_jsonl: Path,
    primary_hpo_column: str,
    fallback_hpo_column: str,
    gene_id_column: str,
):
    patient_to_genes, total_gene_rows, dropped_gene_rows = load_patient_gene_candidates(gene_tsv, gene_id_column)

    total_phenotype_rows = 0
    written_rows = 0
    dropped_missing_hpo = 0
    dropped_missing_genes = 0
    used_primary = 0
    used_fallback = 0

    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with phenotype_tsv.open(newline="") as input_file, output_jsonl.open("w") as output_file:
        reader = csv.DictReader(input_file, delimiter="\t")
        required_columns = {"sample_id", primary_hpo_column, fallback_hpo_column}
        missing_columns = required_columns.difference(reader.fieldnames or [])
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"{phenotype_tsv} is missing required columns: {missing}")

        for row in reader:
            total_phenotype_rows += 1
            sample_id = row["sample_id"].strip()
            positive_phenotypes, source_column = pick_hpo_terms(row, primary_hpo_column, fallback_hpo_column)
            if not positive_phenotypes:
                dropped_missing_hpo += 1
                continue

            candidate_genes = sorted(patient_to_genes.get(sample_id, set()))
            if not candidate_genes:
                dropped_missing_genes += 1
                continue

            if source_column == primary_hpo_column:
                used_primary += 1
            else:
                used_fallback += 1

            patient = {
                "id": sample_id,
                "positive_phenotypes": positive_phenotypes,
                "all_candidate_genes": candidate_genes,
                "true_genes": [],
            }
            json.dump(patient, output_file)
            output_file.write("\n")
            written_rows += 1

    print(f"Gene file: {gene_tsv}")
    print(f"Phenotype file: {phenotype_tsv}")
    print(f"Output file: {output_jsonl}")
    print(f"Total gene rows: {total_gene_rows}")
    print(f"Dropped gene rows with unmapped gene IDs: {dropped_gene_rows}")
    print(f"Patients with at least one mapped candidate gene: {len(patient_to_genes)}")
    print(f"Total phenotype rows: {total_phenotype_rows}")
    print(f"Wrote patients: {written_rows}")
    print(f"Dropped phenotype rows with no usable HPO terms: {dropped_missing_hpo}")
    print(f"Dropped phenotype rows with no mapped candidate genes: {dropped_missing_genes}")
    print(f"Rows using {primary_hpo_column}: {used_primary}")
    print(f"Rows using {fallback_hpo_column}: {used_fallback}")


def main():
    args = parse_args()
    gene_tsv = Path(args.gene_tsv)
    phenotype_tsv = Path(args.phenotype_tsv)
    default_output = phenotype_tsv.parent / f"{phenotype_tsv.stem}_test.jsonl"
    output_jsonl = Path(args.output) if args.output else default_output

    create_lab_patients_file(
        gene_tsv=gene_tsv,
        phenotype_tsv=phenotype_tsv,
        output_jsonl=output_jsonl,
        primary_hpo_column=args.primary_hpo_column,
        fallback_hpo_column=args.fallback_hpo_column,
        gene_id_column=args.gene_id_column,
    )


if __name__ == "__main__":
    main()
