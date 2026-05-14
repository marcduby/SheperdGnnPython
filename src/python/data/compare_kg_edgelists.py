from pathlib import Path
import argparse
import csv
from collections import Counter

#   python3 src/python/data/compare_kg_edgelists.py /path/to/KG_edgelist_a.txt /path/to/KG_edgelist_b.txt


def parse_args():
    parser = argparse.ArgumentParser(
        description="Compare total rows and full_relation counts between two KG edge list files."
    )
    parser.add_argument("kg_edgelist_a", help="Path to the first KG_edgelist_mask.txt file")
    parser.add_argument("kg_edgelist_b", help="Path to the second KG_edgelist_mask.txt file")
    return parser.parse_args()


def load_relation_counts(kg_edgelist: Path):
    relation_counts = Counter()
    total_rows = 0

    with kg_edgelist.open(newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        required_columns = {"x_idx", "y_idx", "full_relation", "mask"}
        missing_columns = required_columns.difference(reader.fieldnames or [])
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"{kg_edgelist} is missing required columns: {missing}")

        for row in reader:
            total_rows += 1
            relation_counts[row["full_relation"]] += 1

    return total_rows, relation_counts


def compare_kg_edgelists(kg_edgelist_a: Path, kg_edgelist_b: Path):
    total_rows_a, relation_counts_a = load_relation_counts(kg_edgelist_a)
    total_rows_b, relation_counts_b = load_relation_counts(kg_edgelist_b)

    relation_types_a = len(relation_counts_a)
    relation_types_b = len(relation_counts_b)
    all_relations = sorted(set(relation_counts_a) | set(relation_counts_b))

    print(f"File A: {kg_edgelist_a}")
    print(f"File B: {kg_edgelist_b}")
    print()
    print("Totals:")
    print(f"rows_a\t{total_rows_a}")
    print(f"rows_b\t{total_rows_b}")
    print(f"row_diff_b_minus_a\t{total_rows_b - total_rows_a}")
    print()
    print("Full relation types:")
    print(f"types_a\t{relation_types_a}")
    print(f"types_b\t{relation_types_b}")
    print(f"type_count_diff_b_minus_a\t{relation_types_b - relation_types_a}")
    print()
    print("Per-relation count differences (b - a):")
    print("full_relation\tcount_a\tcount_b\tdiff_b_minus_a")
    for relation in all_relations:
        count_a = relation_counts_a.get(relation, 0)
        count_b = relation_counts_b.get(relation, 0)
        print(f"{relation}\t{count_a}\t{count_b}\t{count_b - count_a}")


def main():
    args = parse_args()
    compare_kg_edgelists(Path(args.kg_edgelist_a), Path(args.kg_edgelist_b))


if __name__ == "__main__":
    main()
