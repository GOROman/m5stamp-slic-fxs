#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLIC2PORT-FXS v2: build .kicad_pcb from the PR-merged SKiDL netlist (JSON)
with scripted placement. Round 3 (2026-10-31): regenerated from GitHub main
(PR #1 + PR #3 merged, 106 parts / 76 nets).

Differences vs the round-1 script, per CAD_REPORT "notes after PR adoption":
  1. NO diode/LED pin swap: PR #1 fixed the SKiDL templates to 1=K/2=A
     (KiCad footprint convention); the old swap would now invert polarity.
  2. NO RJ11 pad shrink: PR #1 fixed the library footprint itself to
     1.1x1.6mm oval pads; use them as-is.
  3. USB-C nets come from the netlist with real pad names (A1/A4/A5/...);
     no logical-pin mapping table. Shield pads (SH / unnumbered) -> GND.
New parts R31-R37 (HCT244 input pull-downs 100K) are shelf-packed in the
free strip between the two SLIC modules.
Run with KiCad's bundled python on the Mac.
"""
import json, os, sys, math

try:
    import wx
    _app = wx.App(False)
except Exception as e:
    print("wx init skipped:", e)

import pcbnew
from pcbnew import FromMM, VECTOR2I

WORK = os.path.expanduser("~/slic-board-work")
PROJ = os.path.join(WORK, "repo-v2", "kicad")
BOARD_PATH = os.path.join(WORK, "build", "SLIC2PORT-FXS-v2.kicad_pcb")
LIBBASE = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
LOCALPRETTY = os.path.join(PROJ, "SLIC2PORT.pretty")

data = json.load(open(os.path.join(WORK, "netlist_v2.json")))
COMPS = data["comps"]          # ref -> {value, footprint}
NETS = data["nets"]            # netname -> [[ref, pin], ...]

# pin -> nets per component
pinmap = {}
for nname, nodes in NETS.items():
    for ref, pin in nodes:
        pinmap.setdefault(ref, {})[str(pin)] = nname

board = pcbnew.NewBoard(BOARD_PATH)

# ---------------------------------------------------------------- footprints
def load_fp(libid):
    lib, name = libid.split(":", 1)
    path = LOCALPRETTY if lib == "SLIC2PORT" else os.path.join(LIBBASE, lib + ".pretty")
    fp = pcbnew.FootprintLoad(path, name)
    if fp is None:
        raise RuntimeError("cannot load footprint " + libid)
    return fp

fps = {}
for ref, info in COMPS.items():
    fp = load_fp(info["footprint"])
    fp.SetReference(ref)
    fp.SetValue(info["value"] or "")
    fps[ref] = fp

# RJ11: library footprint (repo-v2) already has 1.1x1.6mm oval pads (PR #1).
# No board-side pad shrink (round-1 deviation retired).

# ---------------------------------------------------------------- placement
def bbox(fp):
    """(minx, miny, maxx, maxy) in IU from courtyard graphics, else pads."""
    xs, ys = [], []
    for it in fp.GraphicalItems():
        if it.GetLayer() == pcbnew.F_CrtYd:
            bb = it.GetBoundingBox()
            xs += [bb.GetLeft(), bb.GetRight()]
            ys += [bb.GetTop(), bb.GetBottom()]
    if not xs:
        for p in fp.Pads():
            bb = p.GetBoundingBox()
            xs += [bb.GetLeft(), bb.GetRight()]
            ys += [bb.GetTop(), bb.GetBottom()]
    if not xs:
        return (0, 0, 0, 0)
    return (min(xs), min(ys), max(xs), max(ys))

def place(ref, x, y, rot=0):
    fp = fps[ref]
    fp.SetOrientationDegrees(rot)
    bb = bbox(fp)
    # position so that bbox top-left lands on (x, y)
    fp.SetPosition(VECTOR2I(int(FromMM(x) - bb[0]), int(FromMM(y) - bb[1])))
    board.Add(fp)

def place_anchor(ref, x, y, rot=0):
    """position by footprint origin (for modules/connectors with known geometry)"""
    fp = fps[ref]
    fp.SetOrientationDegrees(rot)
    fp.SetPosition(VECTOR2I(FromMM(x), FromMM(y)))
    board.Add(fp)

GAP = 0.8  # mm between courtyards in shelf packing

def shelf_pack(refs, rect):
    """rect = (x0, y0, x1, y1) mm. Returns list of unplaced refs."""
    x0, y0, x1, y1 = rect
    items = []
    for ref in refs:
        fp = fps[ref]
        fp.SetOrientationDegrees(0)
        bb = bbox(fp)
        w0 = (bb[2] - bb[0]) / 1e6; h0 = (bb[3] - bb[1]) / 1e6
        items.append((ref, w0, h0))
    items.sort(key=lambda t: -t[2])
    cx, cy, row_h = x0, y0, 0.0
    unplaced = []
    for ref, w0, h0 in items:
        done = False
        # only consider 90deg rotation when the part is taller than wide
        rots = [(0, (w0, h0))] + ([(90, (h0, w0))] if h0 > w0 else [])
        for attempt in range(3):
            for rot, (w, h) in rots:
                if cx + w <= x1 and cy + h <= y1:
                    fp = fps[ref]
                    fp.SetOrientationDegrees(rot)
                    bb = bbox(fp)
                    fp.SetPosition(VECTOR2I(int(FromMM(cx) - bb[0]), int(FromMM(cy) - bb[1])))
                    board.Add(fp)
                    cx += w + GAP
                    row_h = max(row_h, h)
                    done = True
                    break
            if done:
                break
            cx = x0
            cy += row_h + GAP
            row_h = 0.0
        if not done:
            unplaced.append(ref)
    return unplaced

# --- majors (anchor placement, geometry known) ---
place_anchor("J_3", 18, 7.2, 0)      # RJ11 port A, opening at top edge
place_anchor("J_4", 82, 7.2, 0)      # RJ11 port B
place_anchor("MOD_A", 26, 34, 180)   # line pins at left end
place_anchor("MOD_B", 74, 47, 0)     # line pins at right end
place_anchor("U1", 50, 67, 0)        # M5StampS3, antenna end (+y) at bottom edge
place_anchor("J1", 16, 75.1, 180)    # USB-C, mating face at bottom edge
place_anchor("J2", 32, 76, 0)        # terminal block

# --- majors (bbox placement) ---
place("U2", 30.5, 60.5, 0)           # 74HCT244 SOIC-20
place("U3", 77.5, 61.5, 0)           # CD4053B SOIC-16
place("C13", 79, 52.5, 0)            # 470uF port A (near MOD_A VDC)
place("C22", 20, 59.5, 0)            # 470uF port B
place("U72", 64.5, 39.5, 0)          # PD diode A (near MOD_A pin11)
place("U99", 26.5, 55.5, 0)          # PD diode B
place("C6", 22.5, 69.5, 0)           # U2 decoupling
place("C10", 72.5, 59.5, 0)          # U3 decoupling
place("Q2", 67, 58.5, 0)             # PD pull-down FET
place("R14", 71.5, 58.5, 0)
place("R13", 84.5, 56.5, 0)          # SEL_Z pull-down
place("J7", 89, 55.5, 0)             # SEL_Z jumper
place("J5", 90.5, 60.5, 0)           # expansion header 2x5
place("J6", 96.3, 62, 0)             # UART header 1x4
place("SW1", 61.5, 63, 0)
place("SW2", 69.5, 63, 0)
place("D2", 61.5, 72.5, 0)
place("R_LED1", 66, 72.5, 0)
place("D3", 70.5, 72.5, 0)
place("R_LED2", 75, 72.5, 0)
place("R8", 35.5, 56.5, 0)           # EN pull-up
place("TP1", 95.5, 53.5, 0)
place("TP2", 20, 52.5, 0)
place("TP3", 91.5, 74.5, 0)

# --- clusters (shelf-packed passives) ---
unplaced = []
unplaced += shelf_pack(["U48", "U49", "U50", "U51", "U52", "U53", "R15", "C11", "C12"],
                       (3, 15.0, 48, 29.0))     # protection A
unplaced += shelf_pack(["U75", "U76", "U77", "U78", "U79", "U80", "R23", "C20", "C21"],
                       (52, 15.0, 97, 29.0))    # protection B
unplaced += shelf_pack(["R4", "R5", "C3", "C4", "R6", "R7", "C5",
                        "R9", "R10", "C7", "C8", "R11", "R12", "C9"],
                       (2, 29.5, 23, 40.5))     # VAUD/VREF/tone
unplaced += shelf_pack(["C14", "R16", "R17", "C15", "C16", "R18", "R19",
                        "C17", "R20", "R21", "C18", "C19", "R22", "U57"],
                       (79, 28, 98, 51))        # port A small-signal
unplaced += shelf_pack(["C23", "R24", "R25", "C24", "C25", "R26", "R27",
                        "C26", "R28", "R29", "C27", "C28", "R30", "U84"],
                       (2, 41, 22, 53))         # port B small-signal
unplaced += shelf_pack(["C1", "F1", "D1", "Q1", "R1", "R2", "R3", "C2"],
                       (2, 57, 20, 75.5))       # power input

unplaced += shelf_pack(["R31", "R32", "R33", "R34", "R35", "R36", "R37"],
                       (24, 38.5, 74, 43.5))     # HCT244 input pull-downs (new in PR #1)

print("UNPLACED:", unplaced)
for ref in unplaced:  # last-resort: park at spare area bottom-right of modules band
    place(ref, 30 + 4 * unplaced.index(ref), 20, 0)

# ---------------------------------------------------------------- nets
netinfo = {}
for nname in NETS:
    if not nname:
        continue
    ni = pcbnew.NETINFO_ITEM(board, nname)
    board.Add(ni)
    netinfo[nname] = ni

def get_pad(fp, number):
    for p in fp.Pads():
        if p.GetNumber() == str(number):
            return p
    return None

# Net assignment is fully generic from the new netlist: PR #1 aligned the
# SKiDL templates with the KiCad footprints (diode/LED 1=K/2=A, USB-C real
# pad names), so no pin swapping or per-connector mapping tables remain.
warnings = []
for ref, pins in pinmap.items():
    fp = fps[ref]
    for pin, nname in pins.items():
        if ref == "J1" and pin == "S1":
            continue  # netlist shield name; footprint uses SH (assigned below)
        # assign ALL pads with this number: SW_PUSH_6mm (SW1/SW2) has each
        # terminal duplicated on two pads; round 1 left the duplicates
        # unassigned, which would confuse the router.
        matched = [p for p in fp.Pads() if p.GetNumber() == str(pin)]
        if not matched:
            warnings.append("no pad %s %s for net %s" % (ref, pin, nname))
            continue
        for pad in matched:
            pad.SetNet(netinfo[nname])

# USB-C shell: footprint shield pads are named SH plus one unnumbered pad.
for pad in fps["J1"].Pads():
    if pad.GetNumber() in ("SH", ""):
        pad.SetNet(netinfo["GND"])
# USB-C A6/A7/A8/B6/B7/B8 (DP/DN/SBU) intentionally left unconnected:
# J1 is a power-only connector in this design (same as round 1).

print("ASSIGN WARNINGS:", warnings)

# M5Stamp footprint pads 29/30/31 are underside GND pads (not in netlist) -> GND
for pad in fps["U1"].Pads():
    if pad.GetNumber() in ("29", "30", "31"):
        pad.SetNet(netinfo["GND"])

# ---------------------------------------------------------------- outline, holes
def seg(x1, y1, x2, y2, layer):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(VECTOR2I(FromMM(x1), FromMM(y1)))
    s.SetEnd(VECTOR2I(FromMM(x2), FromMM(y2)))
    s.SetLayer(layer)
    s.SetWidth(FromMM(0.1))
    board.Add(s)

for (a, b, c, d) in [(0, 0, 100, 0), (100, 0, 100, 80), (100, 80, 0, 80), (0, 80, 0, 0)]:
    seg(a, b, c, d, pcbnew.Edge_Cuts)

MHLIB = os.path.join(LIBBASE, "MountingHole.pretty")
for i, (hx, hy) in enumerate([(4, 4), (96, 4), (4, 76), (96, 76)], start=1):
    mh = pcbnew.FootprintLoad(MHLIB, "MountingHole_3.2mm_M3")
    mh.SetReference("H%d" % i)
    mh.SetPosition(VECTOR2I(FromMM(hx), FromMM(hy)))
    board.Add(mh)

def silk(text, x, y, size, layer, mirrored=False):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(text)
    t.SetPosition(VECTOR2I(FromMM(x), FromMM(y)))
    t.SetLayer(layer)
    t.SetMirrored(mirrored)
    t.SetTextSize(VECTOR2I(FromMM(size), FromMM(size)))
    t.SetTextThickness(FromMM(0.22))
    board.Add(t)

silk("PORT A", 14.5, 14.9, 1.1, pcbnew.F_SilkS)
silk("PORT B", 78.5, 14.9, 1.1, pcbnew.F_SilkS)
silk("SLIC2PORT-FXS  LOCAL LINE ONLY", 50, 18, 2.2, pcbnew.B_SilkS, mirrored=True)
silk("DO NOT CONNECT TO PUBLIC NETWORK (PSTN)", 50, 23, 2.2, pcbnew.B_SilkS, mirrored=True)
silk("RING VOLTAGE UP TO 135Vp-p - CAUTION", 50, 28, 2.2, pcbnew.B_SilkS, mirrored=True)

board.BuildListOfNets()

# ---------------------------------------------------------------- net classes (for DSN export)
ds = board.GetDesignSettings()
ns = ds.m_NetSettings

def mkclass(name, clr, track, via_d, via_dr):
    nc = pcbnew.NETCLASS(name)
    nc.SetClearance(FromMM(clr))
    nc.SetTrackWidth(FromMM(track))
    nc.SetViaDiameter(FromMM(via_d))
    nc.SetViaDrill(FromMM(via_dr))
    nc.SetuViaDiameter(FromMM(0.3))
    nc.SetuViaDrill(FromMM(0.1))
    ns.SetNetclass(name, nc)
    return nc

dflt = ns.GetDefaultNetclass()
dflt.SetClearance(FromMM(0.2)); dflt.SetTrackWidth(FromMM(0.25))
dflt.SetViaDiameter(FromMM(0.6)); dflt.SetViaDrill(FromMM(0.3))
mkclass("Power", 0.25, 0.6, 0.9, 0.45)
mkclass("HV", 0.5, 0.5, 0.8, 0.4)

POWER_NETS = ["+5V", "+5V_PA", "+5V_PB", "VIN_RAW", "VIN_F", "GND"]
HV_NETS = ["TIP_A", "RING_A", "TIP_B", "RING_B", "BRP_A", "BRM_A", "BRP_B", "BRM_B"]
for n in POWER_NETS:
    ns.SetNetclassPatternAssignment(n, "Power")
    netinfo[n].SetNetClass(ns.GetNetClassByName("Power"))
for n in HV_NETS:
    ns.SetNetclassPatternAssignment(n, "HV")
    netinfo[n].SetNetClass(ns.GetNetClassByName("HV"))
ns.RecomputeEffectiveNetclasses()

pcbnew.SaveBoard(BOARD_PATH, board)
print("board saved:", BOARD_PATH)

ok = pcbnew.ExportSpecctraDSN(board, os.path.join(WORK, "build", "SLIC2PORT-FXS-v2.dsn"))
print("DSN export:", ok)

conn = board.GetConnectivity()
print("unconnected count (pre-route):", conn.GetUnconnectedCount(False))
