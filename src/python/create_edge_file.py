
from pathlib import Path
import argparse
import csv
import random
import re

hp_pattern = re.compile(r'^(HP)_(\d{7})_')


def normalize_name(value: str):
    return re.sub(r'[^a-z0-9]+', '_', value.strip().lower()).strip('_')

# TO CREATE READEABLE GENE/TRAIT FILE
#
#   python3 src/python/create_edge_file.py \
#     --mode pigean-gene \
#     --src /Users/mduby/Data/Broad/PortalAI/Sheperd/DccPigeanData/all.gene_stats.large.gt1.out \
#     --kg-node-map /Users/mduby/Data/Broad/PortalAI/Sheperd/OriginalFromHU/knowledge_graph/8.9.21_kg/KG_node_map.txt \
#     --out /Users/mduby/Data/Broad/PortalAI/Sheperd/DccPigeanData/gene_edge_list.txt

# TO CREATE A NEW EDGE FILE FOR TRAINING/VAL
# 
#   python3 src/python/create_edge_file.py \
#     --mode add-pigean-kg-edges \
#     --gene-edge-list /Users/mduby/Data/Broad/PortalAI/Sheperd/HuAndPigeanHpData/knowledge_graph/1.1.0_kg/gene_edge_list.txt \
#     --kg-node-map /Users/mduby/Data/Broad/PortalAI/Sheperd/HuAndPigeanHpData/knowledge_graph/1.1.0_kg/KG_node_map.txt \
#     --kg-edgelist /Users/mduby/Data/Broad/PortalAI/Sheperd/HuAndPigeanHpData/knowledge_graph/1.1.0_kg/HU_original_KG_edgelist_mask.txt \
#     --out /Users/mduby/Data/Broad/PortalAI/Sheperd/HuAndPigeanHpData/knowledge_graph/1.1.0_kg/KG_edgelist_mask.txt \
#     --train-frac 0.8 \
#     --val-frac 0.2 \
#     --test-frac 0.0 \
#     --seed 33


def parse_args():
    parser = argparse.ArgumentParser(description="Create edge files from source datasets.")
    parser.add_argument("--mode", required=True, choices=["pigean-gene", "pigean-go-hp", "add-pigean-kg-edges"], help="Edge file creation mode.")
    parser.add_argument("--src", help="Input tab-delimited gene stats file.")
    parser.add_argument("--gene-edge-list", help="Input tab-delimited gene edge list from pigean-gene mode.")
    parser.add_argument("--kg-node-map", required=True, help="KG node map file used to resolve node IDs.")
    parser.add_argument("--kg-edgelist", help="Input KG_edgelist_mask.txt path.")
    parser.add_argument("--out", required=True, help="Output edge list path.")
    parser.add_argument("--train-frac", type=float, default=0.8, help="Fraction of new rows assigned to train.")
    parser.add_argument("--val-frac", type=float, default=0.2, help="Fraction of new rows assigned to val.")
    parser.add_argument("--test-frac", type=float, default=0.0, help="Fraction of new rows assigned to test.")
    parser.add_argument("--seed", type=int, default=33, help="Random seed for splitting new rows.")
    parser.add_argument(
        "--include-reverse",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Also add reverse gene-to-phenotype KG edges.",
    )
    return parser.parse_args()


def load_gene_to_ncbi_map(kg_node_map: Path):
    gene_to_ncbi = {}
    with kg_node_map.open(newline='') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            if row.get('node_type') != 'gene/protein':
                continue
            gene_name = row['node_name'].strip()
            ncbi_id = row['node_id'].strip()
            gene_to_ncbi[gene_name] = ncbi_id
    return gene_to_ncbi


def hpo_to_node_id(hpo_id: str):
    match = re.fullmatch(r'HP:(\d{7})', hpo_id)
    if not match:
        return None
    return str(int(match.group(1)))


def load_kg_node_indexes(kg_node_map: Path):
    hpo_to_idx = {}
    ncbi_gene_to_idx = {}
    with kg_node_map.open(newline='') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            node_type = row['node_type']
            if node_type == 'effect/phenotype':
                hpo_id = f"HP:{int(row['node_id']):07d}"
                hpo_to_idx[hpo_id] = row['node_idx']
            elif node_type == 'gene/protein':
                ncbi_gene_to_idx[row['node_id'].strip()] = row['node_idx']
    return hpo_to_idx, ncbi_gene_to_idx


def load_hpo_and_go_node_maps(kg_node_map: Path):
    hpo_map = {}
    go_map = {}
    with kg_node_map.open(newline='') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            node_type = row['node_type']
            if node_type == 'effect/phenotype':
                hpo_accession = f"HP:{int(row['node_id']):07d}"
                hpo_map[hpo_accession] = {
                    'node_idx': row['node_idx'].strip(),
                    'node_id': row['node_id'].strip(),
                    'node_name': row['node_name'].strip(),
                }
            elif node_type in ('biological_process', 'molecular_function', 'cellular_component'):
                go_map[normalize_name(row['node_name'])] = {
                    'node_idx': row['node_idx'].strip(),
                    'node_id': row['node_id'].strip(),
                    'node_name': row['node_name'].strip(),
                }
    return hpo_map, go_map


def validate_split(train_frac: float, val_frac: float, test_frac: float):
    total = train_frac + val_frac + test_frac
    if abs(total - 1.0) > 1e-9:
        raise ValueError(f"train/val/test fractions must sum to 1.0; got {total}")
    if min(train_frac, val_frac, test_frac) < 0:
        raise ValueError("train/val/test fractions must be non-negative")


def split_masks(n_rows: int, train_frac: float, val_frac: float, test_frac: float, seed: int):
    validate_split(train_frac, val_frac, test_frac)
    masks = (
        ['train'] * int(n_rows * train_frac)
        + ['val'] * int(n_rows * val_frac)
    )
    masks += ['test'] * (n_rows - len(masks))
    if test_frac == 0 and any(mask == 'test' for mask in masks):
        masks = ['val' if mask == 'test' else mask for mask in masks]
    rng = random.Random(seed)
    rng.shuffle(masks)
    return masks


def create_pigean_gene_edge_file(src: Path, kg_node_map: Path, out: Path):
    gene_to_ncbi = load_gene_to_ncbi_map(kg_node_map)

    seen = set()
    rows = 0
    with src.open(newline='') as f, out.open('w', newline='') as g:
        reader = csv.DictReader(f, delimiter='\t')
        writer = csv.writer(g, delimiter='\t', lineterminator='\n')
        writer.writerow(['hpo_id', 'ncbi_gene_id', 'trait_name', 'gene_name'])
        for record in reader:
            trait_internal = record['Trait_Internal']
            match = hp_pattern.match(trait_internal)
            if not match:
                continue
            hpo_id = f'{match.group(1)}:{match.group(2)}'
            gene = record['Gene'].strip()
            ncbi_id = gene_to_ncbi.get(gene)
            if not ncbi_id:
                continue
            trait_name = record['Trait'].strip()
            key = (hpo_id, ncbi_id, trait_name, gene)
            if key in seen:
                continue
            seen.add(key)
            writer.writerow([hpo_id, ncbi_id, trait_name, gene])
            rows += 1

    print(f'wrote {rows} rows to {out}')


def create_pigean_go_hp_edge_file(src: Path, kg_node_map: Path, out: Path):
    hpo_map, go_map = load_hpo_and_go_node_maps(kg_node_map)

    seen = set()
    rows = 0
    dropped_missing_hpo = 0
    dropped_missing_go = 0
    with src.open(newline='') as f, out.open('w', newline='') as g:
        reader = csv.DictReader(
            f,
            delimiter='\t',
            fieldnames=[
                'Trait_Internal',
                'Trait_Group',
                'Trait',
                'Trait_Category',
                'Gene_Set',
                'Gene_Set_Source',
                'Direct',
                'Indirect',
            ],
        )
        writer = csv.writer(g, delimiter='\t', lineterminator='\n')
        writer.writerow(['hpo_idx', 'go_idx', 'hpo_id', 'go_id', 'trait_name', 'gene_set_name'])
        for record in reader:
            trait_internal = record['Trait_Internal']
            match = hp_pattern.match(trait_internal)
            if not match:
                continue

            hpo_accession = f'{match.group(1)}:{match.group(2)}'
            hpo_node = hpo_map.get(hpo_accession)
            if hpo_node is None:
                dropped_missing_hpo += 1
                continue

            gene_set_name = record['Gene_Set'].strip()
            go_node = go_map.get(normalize_name(gene_set_name))
            if go_node is None:
                dropped_missing_go += 1
                continue

            trait_name = record['Trait'].strip()
            key = (
                hpo_node['node_idx'],
                go_node['node_idx'],
                hpo_node['node_id'],
                go_node['node_id'],
                trait_name,
                gene_set_name,
            )
            if key in seen:
                continue
            seen.add(key)
            writer.writerow(key)
            rows += 1

    print(f'wrote {rows} rows to {out}')
    print(f'dropped {dropped_missing_hpo} rows with unreconciled HPO nodes')
    print(f'dropped {dropped_missing_go} rows with unreconciled GO nodes')


def add_pigean_kg_edges(
    gene_edge_list: Path,
    kg_node_map: Path,
    kg_edgelist: Path,
    out: Path,
    train_frac: float,
    val_frac: float,
    test_frac: float,
    seed: int,
    include_reverse: bool,
):
    hpo_to_idx, ncbi_gene_to_idx = load_kg_node_indexes(kg_node_map)
    existing_rows = []
    edge_keys = set()
    skipped_duplicate_existing = 0

    with kg_edgelist.open(newline='') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            key = (row['x_idx'], row['y_idx'], row['full_relation'])
            if key in edge_keys:
                skipped_duplicate_existing += 1
                continue
            edge_keys.add(key)
            existing_rows.append(row)

    new_rows = []
    skipped_missing_nodes = 0
    skipped_existing_edges = 0
    skipped_duplicate_new = 0
    new_edge_keys = set()

    with gene_edge_list.open(newline='') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            hpo_idx = hpo_to_idx.get(row['hpo_id'].strip())
            gene_idx = ncbi_gene_to_idx.get(row['ncbi_gene_id'].strip())
            if hpo_idx is None or gene_idx is None:
                skipped_missing_nodes += 1
                continue

            candidate_edges = [
                (hpo_idx, gene_idx, 'effect/phenotype;phenotype_protein;gene/protein'),
            ]
            if include_reverse:
                candidate_edges.append((gene_idx, hpo_idx, 'gene/protein;phenotype_protein;effect/phenotype'))

            for x_idx, y_idx, relation in candidate_edges:
                key = (x_idx, y_idx, relation)
                if key in edge_keys:
                    skipped_existing_edges += 1
                    continue
                if key in new_edge_keys:
                    skipped_duplicate_new += 1
                    continue
                new_edge_keys.add(key)
                new_rows.append({'x_idx': x_idx, 'y_idx': y_idx, 'full_relation': relation})

    masks = split_masks(len(new_rows), train_frac, val_frac, test_frac, seed)
    for row, mask in zip(new_rows, masks):
        row['mask'] = mask

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['x_idx', 'y_idx', 'full_relation', 'mask'], delimiter='\t', lineterminator='\n')
        writer.writeheader()
        writer.writerows(existing_rows)
        writer.writerows(new_rows)

    print(f'wrote {len(existing_rows) + len(new_rows)} unique KG rows to {out}')
    print(f'added {len(new_rows)} new rows from {gene_edge_list}')
    print(f'skipped {skipped_duplicate_existing} duplicate rows from existing KG edge list')
    print(f'skipped {skipped_existing_edges} source rows already present in KG')
    print(f'skipped {skipped_duplicate_new} duplicate source rows')
    print(f'skipped {skipped_missing_nodes} source rows with missing HPO or NCBI gene nodes')


def main():
    args = parse_args()
    out = Path(args.out)
    kg_node_map = Path(args.kg_node_map)

    if args.mode == "pigean-gene":
        if not args.src:
            raise ValueError("--src is required for pigean-gene mode")
        src = Path(args.src)
        create_pigean_gene_edge_file(src, kg_node_map, out)
    elif args.mode == "pigean-go-hp":
        if not args.src:
            raise ValueError("--src is required for pigean-go-hp mode")
        src = Path(args.src)
        create_pigean_go_hp_edge_file(src, kg_node_map, out)
    elif args.mode == "add-pigean-kg-edges":
        if not args.gene_edge_list:
            raise ValueError("--gene-edge-list is required for add-pigean-kg-edges mode")
        if not args.kg_edgelist:
            raise ValueError("--kg-edgelist is required for add-pigean-kg-edges mode")
        add_pigean_kg_edges(
            gene_edge_list=Path(args.gene_edge_list),
            kg_node_map=kg_node_map,
            kg_edgelist=Path(args.kg_edgelist),
            out=out,
            train_frac=args.train_frac,
            val_frac=args.val_frac,
            test_frac=args.test_frac,
            seed=args.seed,
            include_reverse=args.include_reverse,
        )


if __name__ == "__main__":
    main()
