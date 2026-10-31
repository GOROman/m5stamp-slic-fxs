#!/usr/bin/env python3
"""Regenerate bom.csv from the checked-in netlist, preserving notes by value."""
import csv
from collections import defaultdict
from pathlib import Path
import sexpdata

ROOT = Path(__file__).resolve().parents[2]

def fields(node):
    return {str(item[0]): item[1:] for item in node[1:] if isinstance(item, list)}

def read_netlist(path):
    data = fields(sexpdata.loads(path.read_text()))
    components = {}
    for entry in data['components']:
        f = fields(entry)
        components[str(f['ref'][0])] = (str(f['value'][0]), str(f['footprint'][0]))
    nets = {}
    for entry in data['nets']:
        f = fields(entry)
        name = str(f['name'][0])
        for item in entry[1:]:
            if isinstance(item, list) and str(item[0]) == 'node':
                n = fields(item)
                nets[(str(n['ref'][0]), str(n['pin'][0]))] = name
    return components, nets

if __name__ == '__main__':
    target = ROOT / 'bom.csv'
    with target.open(newline='') as f:
        notes = {row['Value']: row['Note'] for row in csv.DictReader(f)}
    components, _ = read_netlist(Path(__file__).with_name('m5stamp_slic2port.net'))
    groups = defaultdict(list)
    for ref, key in components.items():
        groups[key].append(ref)
    with target.open('w', newline='') as f:
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow(['Value', 'Footprint', 'Qty', 'Refs', 'Note'])
        for (value, footprint), refs in sorted(groups.items()):
            writer.writerow([value, footprint, len(refs), ' '.join(sorted(refs)), notes.get(value, '')])
