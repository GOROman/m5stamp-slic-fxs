#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Issue #12: verify that build_pcb_v32.py regenerates the shipped board.

Regenerates the board into a temp directory from the checked-in netlist
JSON, then compares it against kicad/SLIC2PORT-FXS.kicad_pcb:
  - placement (anchor x/y, rotation, layer) of every footprint; the parts
    audited in rounds 6-8 (TARGETS) must match exactly, any other drift is
    reported as a warning;
  - pad net assignment and component value for every part (must match);
  - pad size/drill of the RJ11 and U1 socket footprints (must match).

Run with the KiCad bundled python:
  python3 kicad/check_regen.py [--keep]
Exit code 0 = regeneration reproduces the shipped board.
"""
import json
import os
import subprocess
import sys
import tempfile

import wx
_app = wx.App(False)
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
SHIPPED = os.path.join(HERE, "SLIC2PORT-FXS.kicad_pcb")
TARGETS = {"J1", "J2", "U2", "C6", "C13", "K1", "C10", "SW1", "SW2",
           "J_3", "J_4", "U1", "MOD_A", "MOD_B"}
PADCHECK = {"J_3", "J_4", "U1"}


def dump(path):
    b = pcbnew.LoadBoard(path)
    out = {}
    for fp in b.GetFootprints():
        ref = str(fp.GetReference())
        pos = fp.GetPosition()
        pads = {}
        geom = {}
        for p in fp.Pads():
            if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                continue  # NPTH mounting holes have no copper: a net on them is
                # a serialization artifact (KiCad drops it for numbered files,
                # keeps it for name-only files) and is not compared.
            pads.setdefault(str(p.GetNumber()), []).append(str(p.GetNetname()))
            s = p.GetSize()
            geom.setdefault(str(p.GetNumber()), []).append(
                (round(pcbnew.ToMM(s.x), 3), round(pcbnew.ToMM(s.y), 3),
                 round(pcbnew.ToMM(p.GetDrillSize().x), 3)))
        for d in (pads, geom):
            for k in d:
                d[k] = sorted(d[k])
        out[ref] = {"x": round(pcbnew.ToMM(pos.x), 3), "y": round(pcbnew.ToMM(pos.y), 3),
                    "rot": round(fp.GetOrientationDegrees(), 2),
                    "layer": "B" if fp.GetLayer() == pcbnew.B_Cu else "F",
                    "value": str(fp.GetValue()), "pads": pads, "geom": geom}
    return out


def main():
    keep = "--keep" in sys.argv
    tmp = tempfile.mkdtemp(prefix="slic-regen-")
    regen_path = os.path.join(tmp, "regen.kicad_pcb")
    r = subprocess.run([sys.executable, os.path.join(HERE, "build_pcb_v32.py"), regen_path],
                       capture_output=True, text=True)
    print(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "")
    if r.returncode != 0:
        print(r.stderr[-2000:])
        print("REGENERATION FAILED")
        return 1
    ship = dump(SHIPPED)
    regen = dump(regen_path)
    errors, warnings = [], []
    for ref in sorted(set(ship) | set(regen)):
        a, b = ship.get(ref), regen.get(ref)
        if a is None or b is None:
            errors.append("%s: missing in %s" % (ref, "shipped" if b is None else "regen"))
            continue
        if (abs(a["x"] - b["x"]) > 0.011 or abs(a["y"] - b["y"]) > 0.011
                or abs(a["rot"] - b["rot"]) > 0.01 or a["layer"] != b["layer"]):
            msg = "%s: placement ship=(%.3f,%.3f,%.1f,%s) regen=(%.3f,%.3f,%.1f,%s)" % (
                ref, a["x"], a["y"], a["rot"], a["layer"], b["x"], b["y"], b["rot"], b["layer"])
            (errors if ref in TARGETS else warnings).append(msg)
        if a["pads"] != b["pads"]:
            diff = {k: (a["pads"].get(k), b["pads"].get(k))
                    for k in set(a["pads"]) | set(b["pads"])
                    if a["pads"].get(k) != b["pads"].get(k)}
            errors.append("%s: pad nets differ %s" % (ref, diff))
        if a["value"] != b["value"]:
            errors.append("%s: value ship=%r regen=%r" % (ref, a["value"], b["value"]))
        if ref in PADCHECK and a["geom"] != b["geom"]:
            errors.append("%s: pad geometry differs ship=%s regen=%s" % (ref, a["geom"], b["geom"]))
    for w in warnings:
        print("WARN:", w)
    for e in errors:
        print("ERROR:", e)
    print("placement warnings: %d, errors: %d (regen at %s)" % (len(warnings), len(errors), regen_path if keep else tmp))
    if not keep:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
