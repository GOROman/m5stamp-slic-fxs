#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLIC2PORT-FXS v3: build .kicad_pcb from the v0.2 SKiDL netlist (JSON)
with scripted placement. Round 4 (2026-10-31): regenerated from GitHub main
(142 parts / 76 nets, SKiDL source with socket-mounted U1).

Design changes vs v2 (round 3):
  - CD4053B removed; audio cross-connect is Omron G5V-2 relays K1/K2
    + 2N7002 drivers Q3/Q4 + 1N4007 flyback diodes U45/U49.
    SEL_Z jumper J7 removed.
  - Test points 3 -> 34 (TP1-TP34), each labelled in silk with its net
    name; TIP/RING TPs (TP4/5/12/13) carry HV warning silk.
  - 1N4004 -> 1N4007, ferrite beads -> BK2125HS601-T (same 0805 land).
  - U1 (M5StampS3) is SOCKET-mounted (user instruction): footprint
    SLIC2PORT:Stamp-S3-Socket = 1.27mm-pitch female headers 17P + 11P.
    The module floats above the board; its courtyard is kept empty and
    wide routing channels are left around the socket rows.
  - Anonymous U## / R## refdes are re-assigned by SKiDL every regen, so
    placement groups below are by connectivity (function), not by the
    refdes roles of earlier rounds.
Board outline 120x90 mm (was 100x80 in v1/v2, 120x80 in the first v3
attempt): 142 parts (+34% vs v2), two ~21x11mm relays, 34 TPs with silk
labels, and the U1 socket keep-out could not be packed into 120x80
without courtyard regressions (38 overlap pairs vs 17 in v2), so the
bottom band was extended by 10mm. See CAD_REPORT round 4.
Round 5 (2026-10-31): v3.1 - decoupling caps moved next to their loads
(measured on v3, footprint-centre / pad distances):
  - C6  -> directly beside U2 (74HCT244) pin 20 (VCC).
  - C23 -> just above MOD_B pin 10 (+5V_PB), its own rail's module pin.
  - C10 -> B.Cu directly under U1 socket pin 13 (+5V): the socket is
    hemmed in by U2 / J2 / board edge on the top side, so the classic
    back-side bypass position is used (single bottom-side part).
  - C14 -> under MOD_A pin 10 (+5V_PA), 3.7mm from the pad.
  - C13/C22 bulk swap: C13 (+5V_PA) takes C22's v3 slot on the port-A
    side next to K1; C22 (+5V_PB) moves under MOD_B, 10.3mm from pin 10.
  - C3/C4/C5 verified clustered with the VAUD/VREF divider network
    (4.7-10.4mm), left as-is.
All other placements keep their exact v3 coordinates (C14/C10 keep
their v3 shelf-pack slots as empty space; they are relocated after
packing by the round-5 block below).
Round 6 (2026-10-31): v3.2 - hardware status LEDs (DESIGN 5.7).
Netlist is now netlist_v32.json (156 parts / 84 nets): +6 LEDs
(D4-D9), +6 current-limit resistors (R_LED3-R_LED8), +2 buffer FETs
(Q5/Q6 for the HOOK LEDs). All v3.1 placements keep their exact
coordinates; the 14 new parts go into the free strip along the top
edge (freescan-verified empty: y 6-15 above the protection shelves),
grouped per port next to its RJ11: row 1 = HOOK/RING pairs,
row 2 = HOOK buffer FET + LINK pair, each LED with a role silk
label (HOOK_x / RING_x / LINK_x). Branch feat/status-leds (PR).
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
BOARD_PATH = os.path.join(WORK, "build", "SLIC2PORT-FXS-v3.2.kicad_pcb")
LIBBASE = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/"
LOCALPRETTY = os.path.join(PROJ, "SLIC2PORT.pretty")

data = json.load(open(os.path.join(WORK, "netlist_v32.json")))
COMPS = data["comps"]
NETS = data["nets"]

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

# ---------------------------------------------------------------- placement
def bbox(fp):
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
    fp.SetPosition(VECTOR2I(int(FromMM(x) - bb[0]), int(FromMM(y) - bb[1])))
    board.Add(fp)

def place_anchor(ref, x, y, rot=0):
    fp = fps[ref]
    fp.SetOrientationDegrees(rot)
    fp.SetPosition(VECTOR2I(FromMM(x), FromMM(y)))
    board.Add(fp)

GAP = 0.8

def shelf_pack(refs, rect):
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
place_anchor("J_4", 102, 7.2, 0)     # RJ11 port B
place_anchor("MOD_A", 26, 34, 180)   # line pins at left end
place_anchor("MOD_B", 94, 47, 0)     # line pins at right end
place_anchor("U1", 50, 77, 0)        # M5StampS3 on socket, antenna end (+y) at bottom edge
place_anchor("J1", 16, 85.1, 180)    # USB-C, mating face at bottom edge
place_anchor("J2", 30, 86, 0)        # terminal block

# --- majors (bbox placement) ---
place("U2", 27.5, 70.5, 0)           # 74HCT244 SOIC-20, left of U1 socket (channel kept open)
place("K1", 30, 53.5, 90)            # relay A (G5V-2, rotated: 20.9 x 10.7)
place("K2", 98, 30, 90)              # relay B (G5V-2, rotated)
place("Q3", 66, 53, 0)               # relay A driver 2N7002
place("U45", 66, 57.5, 0)            # relay A flyback 1N4007
place("R13", 74, 53, 0)              # SEL_A_5V gate pull-down
place("TP33", 82, 53, 0)             # VR_A_IN (relay A COM)
place("C13", 20, 61, 0)              # 470uF port A bulk (round5: was on B side; takes C22 v3 slot, port-A side next to K1)
place("Q4", 110, 54, 0)              # relay B driver 2N7002
place("Q2", 110, 58.5, 0)            # PD pull-down FET
place("R14", 110, 63.5, 0)           # SEL_B_5V gate pull-down
place("R15", 110, 67, 0)             # PD_EN pull-down
place("U49", 85.5, 63, 0)            # relay B flyback 1N4007
place("C22", 51.6, 52.7, 0)          # 470uF port B bulk (round5: was on A side; now under MOD_B near pin 10)
place("C23", 51.5, 41.3, 0)          # +5V_PB decoupling (round5: just above MOD_B pin 10)
place("C6", 32.75, 67.98, 0)         # U2 decoupling (round5: beside U2 pin 20 VCC)
place("R8", 58, 62.3, 0)             # EN pull-up (above U1 socket pads, channel side)
place("J5", 85, 83, 90)              # expansion header 2x5 (rotated)
place("J6", 115.5, 61.5, 0)          # UART header 1x4
place("SW1", 66, 73, 0)
place("SW2", 74.5, 73, 0)
place("D2", 66, 82.5, 0)
place("R_LED1", 71.5, 82.5, 0)
place("D3", 76.5, 82.5, 0)
place("R_LED2", 80, 82.5, 0)

# --- round 6: status LEDs (top-edge strip, grouped per port) ---
# (place() takes courtyard top-left; strip y 7.2 / 11.0, labels below)
for ref, x, y in [
    # port A (x0 = 40): row1 HOOK pair + RING pair, row2 FET + LINK pair
    ("R_LED3", 40.0, 7.2), ("D4", 43.8, 7.2),
    ("R_LED4", 48.6, 7.2), ("D5", 52.4, 7.2),
    ("Q5", 40.2, 11.0), ("R_LED5", 45.2, 11.0), ("D6", 49.0, 11.0),
    # port B (x0 = 66): same pattern, clear of TP12/TP13 at x 86/91.5
    ("R_LED6", 66.0, 7.2), ("D7", 69.8, 7.2),
    ("R_LED7", 74.6, 7.2), ("D8", 78.4, 7.2),
    ("Q6", 66.2, 11.0), ("R_LED8", 71.2, 11.0), ("D9", 75.0, 11.0),
]:
    place(ref, x, y, 0)

# --- test points (explicit, grouped by function; labels added below) ---
for ref, x, y in [
    ("TP4", 30, 10.8), ("TP5", 35.5, 10.8),         # TIP_A / RING_A (HV!)
    ("TP12", 86, 10.8), ("TP13", 91.5, 10.8),       # TIP_B / RING_B (HV!)
    ("TP20", 24.5, 52.8), ("TP21", 24.5, 57.2),     # VIN_RAW / VIN_F
    ("TP34", 98, 41.0),                             # VR_B_IN (relay B COM)
    ("TP3", 86, 78.5), ("TP25", 91.5, 78.5),        # TONE_BUS / TONE_5V
    ("TP24", 99.5, 80.8), ("TP2", 104.5, 80.8),     # GND (extra) / GND
    ("TP1", 104.5, 85.5),                           # +5V
]:
    place(ref, x, y, 0)

unplaced = []
# TP group B: above MOD_B
unplaced += shelf_pack(["TP14", "TP15", "TP16", "TP17", "TP18", "TP19",
                        "TP30", "TP32"], (60, 38.8, 96, 43))
# TP group A: right of MOD_B
unplaced += shelf_pack(["TP6", "TP7", "TP8", "TP9"], (98.5, 44.8, 118, 51))
unplaced += shelf_pack(["TP10", "TP11", "TP29", "TP31"], (98.5, 52, 107.5, 66))
# TP group mid-left: VAUD/VREF/TONE_AC/SEL
unplaced += shelf_pack(["TP22", "TP23", "TP26", "TP27", "TP28"], (24.5, 44.3, 44, 52.6))

# --- clusters (shelf-packed, grouped by connectivity; refs per current netlist) ---
unplaced += shelf_pack(["U55", "U56", "U57", "U58", "U59", "U60", "R16", "C11", "C12"],
                       (3, 15.0, 58, 29.0))     # protection A
unplaced += shelf_pack(["U82", "U83", "U84", "U85", "U86", "U87", "R24", "C20", "C21"],
                       (62, 15.0, 117, 29.0))   # protection B
unplaced += shelf_pack(["C3", "C4", "C5", "C7", "C8", "C9", "R4", "R5", "R6",
                        "R7", "R9", "R10", "R11", "R12", "R21", "R27", "R29", "R31"],
                       (2, 29.5, 23, 43.5))     # VAUD/VREF/tone
unplaced += shelf_pack(["C14", "C15", "C16", "C17", "C18", "C19", "C10",
                        "R17", "R18", "R19", "R20", "R22", "R23", "U64"],
                       (77, 26.0, 97, 38.2))    # port A small-signal + bead A
unplaced += shelf_pack(["C24", "C25", "C26", "C27", "C28",
                        "R25", "R26", "R28", "R30", "U79", "U91", "U106"],
                       (2, 44.5, 24, 57.5))     # port B small-signal + bead B + PD diodes
unplaced += shelf_pack(["C1", "F1", "D1", "Q1", "R1", "R2", "R3", "C2"],
                       (2, 57.5, 19.5, 76))     # power input
unplaced += shelf_pack(["R32", "R33", "R34", "R35", "R36", "R37", "R38"],
                       (24, 38.5, 60, 41.5))    # HCT244 input pull-downs

print("UNPLACED:", unplaced)
for ref in unplaced:
    place(ref, 30 + 4 * unplaced.index(ref), 20, 0)

# --- round 5: relocate shelf-packed decoupling caps next to their loads ---
# (C14/C10 were packed into the port-A cluster above; their v3 slots stay
# empty so every other part keeps its exact v3 coordinates.)
def cy_center(fp):
    for layer in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
        try:
            bb = fp.GetCourtyard(layer).BBox()
            if bb.GetWidth() > 0 and bb.GetHeight() > 0:
                return ((bb.GetLeft() + bb.GetRight()) // 2,
                        (bb.GetTop() + bb.GetBottom()) // 2)
        except Exception:
            pass
    bb = fp.GetBoundingBox()
    return ((bb.GetLeft() + bb.GetRight()) // 2,
            (bb.GetTop() + bb.GetBottom()) // 2)

def move_center(ref, cx, cy):
    fp = fps[ref]
    ccx, ccy = cy_center(fp)
    pos = fp.GetPosition()
    fp.SetPosition(VECTOR2I(int(pos.x + FromMM(cx) - ccx),
                            int(pos.y + FromMM(cy) - ccy)))

move_center("C14", 66.0, 37.66)   # +5V_PA 100nF: under MOD_A pin 10 (pad at 66.62,34)
fps["C10"].Flip(fps["C10"].GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
move_center("C10", 43.3, 82.1)    # +5V 100nF on B.Cu under U1 socket pin 13 (pad at 41.4,82.08)

# ---------------------------------------------------------------- TP silk labels
for i in range(1, 35):
    ref = "TP%d" % i
    fp = fps[ref]
    netname = pinmap.get(ref, {}).get("1", "")
    vt = fp.Value()
    vt.SetText(netname)
    vt.SetLayer(pcbnew.F_SilkS)
    vt.SetTextSize(VECTOR2I(FromMM(0.85), FromMM(0.85)))
    vt.SetTextThickness(FromMM(0.13))
    pos = fp.GetPosition()
    vt.SetPosition(VECTOR2I(pos.x, pos.y + FromMM(2.3)))

# ------------------------------------------------- status LED silk labels
def led_label(text, cx, cy):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(text)
    t.SetPosition(VECTOR2I(FromMM(cx), FromMM(cy)))
    t.SetLayer(pcbnew.F_SilkS)
    t.SetTextSize(VECTOR2I(FromMM(0.8), FromMM(0.8)))
    t.SetTextThickness(FromMM(0.13))
    t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
    board.Add(t)

# LED courtyard centres are ~1.5mm right of the place() x (top-left based)
led_label("HOOK_A", 45.3, 5.9); led_label("RING_A", 53.9, 5.9)
led_label("LINK_A", 50.5, 14.35)
led_label("HOOK_B", 71.3, 5.9); led_label("RING_B", 79.9, 5.9)
led_label("LINK_B", 76.5, 14.35)

# ---------------------------------------------------------------- nets
netinfo = {}
for nname in NETS:
    if not nname:
        continue
    ni = pcbnew.NETINFO_ITEM(board, nname)
    board.Add(ni)
    netinfo[nname] = ni

warnings = []
for ref, pins in pinmap.items():
    fp = fps[ref]
    for pin, nname in pins.items():
        if ref == "J1" and pin == "S1":
            continue
        matched = [p for p in fp.Pads() if p.GetNumber() == str(pin)]
        if not matched:
            warnings.append("no pad %s %s for net %s" % (ref, pin, nname))
            continue
        for pad in matched:
            pad.SetNet(netinfo[nname])

for pad in fps["J1"].Pads():
    if pad.GetNumber() in ("SH", ""):
        pad.SetNet(netinfo["GND"])

print("ASSIGN WARNINGS:", warnings)
# NOTE: U1 socket has no pads 29-31; the bare module's underside GND pads
# are unconnected in socket configuration (GND via pins 11/18). No
# board-side assignment is needed or possible.

# ---------------------------------------------------------------- outline, holes
def seg(x1, y1, x2, y2, layer):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(VECTOR2I(FromMM(x1), FromMM(y1)))
    s.SetEnd(VECTOR2I(FromMM(x2), FromMM(y2)))
    s.SetLayer(layer)
    s.SetWidth(FromMM(0.1))
    board.Add(s)

for (a, b, c, d) in [(0, 0, 120, 0), (120, 0, 120, 90), (120, 90, 0, 90), (0, 90, 0, 0)]:
    seg(a, b, c, d, pcbnew.Edge_Cuts)

MHLIB = os.path.join(LIBBASE, "MountingHole.pretty")
for i, (hx, hy) in enumerate([(4, 4), (116, 4), (4, 86), (116, 86)], start=1):
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
silk("PORT B", 98.5, 14.9, 1.1, pcbnew.F_SilkS)
silk("HV! TIP/RING", 33, 17.5, 1.0, pcbnew.F_SilkS)
silk("HV! TIP/RING", 89, 17.5, 1.0, pcbnew.F_SilkS)
silk("M5StampS3 SOCKET", 50, 63.8, 1.0, pcbnew.F_SilkS)
silk("SLIC2PORT-FXS  LOCAL LINE ONLY", 60, 18, 2.2, pcbnew.B_SilkS, mirrored=True)
silk("DO NOT CONNECT TO PUBLIC NETWORK (PSTN)", 60, 23, 2.2, pcbnew.B_SilkS, mirrored=True)
silk("RING VOLTAGE UP TO 135Vp-p - CAUTION", 60, 28, 2.2, pcbnew.B_SilkS, mirrored=True)

board.BuildListOfNets()

# ---------------------------------------------------------------- net classes
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

ok = pcbnew.ExportSpecctraDSN(board, os.path.join(WORK, "build", "SLIC2PORT-FXS-v3.2.dsn"))
print("DSN export:", ok)

conn = board.GetConnectivity()
print("unconnected count (pre-route):", conn.GetUnconnectedCount(False))
