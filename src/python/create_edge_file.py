
from pathlib import Path
import csv
import re

src = Path('/Users/mduby/Data/Broad/PortalAI/Sheperd/DccPigeanData/all.gene_stats.large.gt1.out')
out = Path('/Users/mduby/Data/Broad/PortalAI/Sheperd/DccPigeanData/gene_edge_list.txt')
kg_node_map = Path('/Users/mduby/Data/Broad/PortalAI/Sheperd/OriginalFromHU/knowledge_graph/8.9.21_kg/KG_node_map.txt')

hp_pattern = re.compile(r'^(HP)_(\d{7})_')

gene_to_ncbi = {}
with kg_node_map.open(newline='') as f:
    reader = csv.DictReader(f, delimiter='\t')
    for row in reader:
        if row.get('node_type') != 'gene/protein':
            continue
        gene_name = row['node_name'].strip()
        ncbi_id = row['node_id'].strip()
        gene_to_ncbi[gene_name] = ncbi_id

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

