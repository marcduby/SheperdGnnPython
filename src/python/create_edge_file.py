
from pathlib import Path
import argparse
import csv
import re

hp_pattern = re.compile(r'^(HP)_(\d{7})_')

# TO CREATE READEABLE GENE/TRAIT FILE
#
#   python3 src/python/create_edge_file.py \
#     --src /Users/mduby/Data/Broad/PortalAI/Sheperd/DccPigeanData/all.gene_stats.large.gt1.out \
#     --kg-node-map /Users/mduby/Data/Broad/PortalAI/Sheperd/OriginalFromHU/knowledge_graph/8.9.21_kg/KG_node_map.txt \
#     --out /Users/mduby/Data/Broad/PortalAI/Sheperd/DccPigeanData/gene_edge_list.txt

def parse_args():
    parser = argparse.ArgumentParser(description="Create an HPO-gene edge file from a PheGEnI-style stats table.")
    parser.add_argument("--src", required=True, help="Input tab-delimited gene stats file.")
    parser.add_argument("--kg-node-map", required=True, help="KG node map file used to map gene symbols to NCBI IDs.")
    parser.add_argument("--out", required=True, help="Output edge list path.")
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


def main():
    args = parse_args()
    src = Path(args.src)
    out = Path(args.out)
    kg_node_map = Path(args.kg_node_map)

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


if __name__ == "__main__":
    main()
