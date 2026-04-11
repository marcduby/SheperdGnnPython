from pathlib import Path
import argparse
import csv
from collections import Counter

#   python3 src/python/data/summarize_kg_edgelist.py /path/to/KG_edgelist_mask.txt

def parse_args():
    parser = argparse.ArgumentParser(
        description="Summarize mask and full_relation counts in a KG_edgelist_mask.txt file."
    )
    parser.add_argument("kg_edgelist", help="Path to KG_edgelist_mask.txt")
    return parser.parse_args()


def summarize_kg_edgelist(kg_edgelist: Path):
    mask_counts = Counter()
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
            mask_counts[row["mask"]] += 1
            relation_counts[row["full_relation"]] += 1

    print(f"File: {kg_edgelist}")
    print(f"Total rows: {total_rows}")
    print()
    print("Mask counts:")
    for mask in ("train", "val", "test"):
        print(f"{mask}\t{mask_counts.get(mask, 0)}")
    for mask, count in sorted(mask_counts.items()):
        if mask not in {"train", "val", "test"}:
            print(f"{mask}\t{count}")

    print()
    print("Full relation counts:")
    for relation, count in sorted(relation_counts.items()):
        print(f"{relation}\t{count}")


def main():
    args = parse_args()
    summarize_kg_edgelist(Path(args.kg_edgelist))


if __name__ == "__main__":
    main()
