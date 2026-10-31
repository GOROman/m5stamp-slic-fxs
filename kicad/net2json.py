#!/usr/bin/env python3
"""Regenerate the placement JSON (netlist_v32.json) from the checked-in SKiDL netlist.

Usage: python3 kicad/net2json.py [src.net] [dst.json]
Defaults: kicad/skidl/m5stamp_slic2port.net -> kicad/netlist_v32.json

The placement scripts (build_pcb_v32.py / check_v32.py) read the JSON, so it
must be regenerated whenever the saved netlist changes; tests/test_hardware.py
verifies that the JSON and the netlist agree on values, footprints and nets.
"""
import json
import sys
from pathlib import Path

import sexpdata

ROOT = Path(__file__).resolve().parent


def fields(node):
    return {str(i[0]): i[1:] for i in node[1:] if isinstance(i, list)}


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "skidl/m5stamp_slic2port.net"
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "netlist_v32.json"
    d = fields(sexpdata.loads(src.read_text()))
    comps = {}
    for e in d["components"]:
        f = fields(e)
        comps[str(f["ref"][0])] = {"footprint": str(f["footprint"][0]), "value": str(f["value"][0])}
    nets = {}
    for e in d["nets"]:
        f = fields(e)
        name = str(f["name"][0])
        nodes = []
        for i in e[1:]:
            if isinstance(i, list) and str(i[0]) == "node":
                n = fields(i)
                nodes.append([str(n["ref"][0]), str(n["pin"][0])])
        nets[name] = nodes
    dst.write_text(json.dumps({"comps": comps, "nets": nets}, indent=1, sort_keys=True))
    print("wrote", dst, len(comps), "comps", len(nets), "nets")


if __name__ == "__main__":
    main()
