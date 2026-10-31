import wx, json
_app = wx.App(False)
import pcbnew

B3 = "/Users/goroman/slic-board-work/build/SLIC2PORT-FXS-v3.kicad_pcb"
B2 = "/Users/goroman/slic-board-work/build/SLIC2PORT-FXS-v2.kicad_pcb"
b = pcbnew.LoadBoard(B3)
data = json.load(open("/Users/goroman/slic-board-work/netlist_v3.json"))
comps, nets = data["comps"], data["nets"]
pinmap = {}
for nname, nodes in nets.items():
    for ref, pin in nodes: pinmap.setdefault(ref, {})[str(pin)] = nname

fps = {fp.GetReference(): fp for fp in b.GetFootprints()}
print("footprints on board:", len(fps), "(expect 146 = 142 comps + 4 MH)")
missing = [r for r in comps if r not in fps]
print("comps missing from board:", missing)

# outline
edges = [s for s in b.GetDrawings() if s.GetLayer() == pcbnew.Edge_Cuts]
xs = [min(s.GetStart().x, s.GetEnd().x) for s in edges] + [max(s.GetStart().x, s.GetEnd().x) for s in edges]
ys = [min(s.GetStart().y, s.GetEnd().y) for s in edges] + [max(s.GetStart().y, s.GetEnd().y) for s in edges]
print("outline: %.1f x %.1f mm" % ((max(xs)-min(xs))/1e6, (max(ys)-min(ys))/1e6))

# 1. pad-net verification
bad = []
for ref, pins in pinmap.items():
    fp = fps[ref]
    pads = {p.GetNumber(): p for p in fp.Pads()}
    for pin, nname in pins.items():
        if ref == "J1" and pin == "S1": continue
        p = pads.get(pin)
        if p is None: bad.append((ref, pin, nname, "NO PAD")); continue
        got = p.GetNetname()
        if got != nname: bad.append((ref, pin, nname, "got " + got))
print("pad-net mismatches:", bad if bad else "NONE")

nonet = []
for ref, fp in fps.items():
    for p in fp.Pads():
        if not p.GetNetname():
            nonet.append("%s.%s" % (ref, p.GetNumber() or "''"))
print("pads without net (%d):" % len(nonet), sorted(nonet))

def netof(ref, pin):
    for p in fps[ref].Pads():
        if p.GetNumber() == pin: return p.GetNetname()
    return None

spots = [("K1","1","+5V"),("K1","16","RLY_A_COIL"),("K1","4","VR_A_IN"),("K1","13","VR_A_IN"),
         ("K1","6","VX_B_IN"),("K1","11","VX_B_IN"),("K1","8","TONE_BUS"),("K1","9","TONE_BUS"),
         ("K2","1","+5V"),("K2","16","RLY_B_COIL"),("K2","4","VR_B_IN"),("K2","6","VX_A_IN"),
         ("Q3","1","SEL_A_5V"),("Q3","3","RLY_A_COIL"),("Q4","1","SEL_B_5V"),("Q4","3","RLY_B_COIL"),
         ("U45","1",None),("U49","1",None),
         ("TP4","1","TIP_A"),("TP5","1","RING_A"),("TP12","1","TIP_B"),("TP13","1","RING_B"),
         ("TP33","1","VR_A_IN"),("TP34","1","VR_B_IN"),("TP20","1","VIN_RAW"),("TP21","1","VIN_F"),
         ("U55","2","TIP_A"),("U82","1","RING_B"),("U64","1","+5V"),("U64","2","+5V_PA"),
         ("U91","2","+5V_PB"),("U79","2","PD_A"),("U106","2","PD_B"),
         ("D1","1","+5V"),("D2","1","GND"),("J1","A4","VIN_RAW"),("J1","SH","GND"),("U1","11","GND"),("U1","13","+5V"),("U1","28","+3V3"),
         ("MOD_A","1","RING_A"),("MOD_A","11","PD_A"),("MOD_B","10","+5V_PB"),("C7","1",None)]
for ref, pin, expect in spots:
    got = netof(ref, pin)
    ok = (expect is None and got) or got == expect
    print("spot %s.%s = %s %s" % (ref, pin, got, "OK" if ok else "MISMATCH exp " + str(expect)))

# U43/U47 must bridge coil nets
print("U45 nets:", sorted({p.GetNetname() for p in fps["U45"].Pads()}), "(expect +5V & RLY_A_COIL)")
print("U49 nets:", sorted({p.GetNetname() for p in fps["U49"].Pads()}), "(expect +5V & RLY_B_COIL)")
print("U1 footprint:", fps["U1"].GetFPID().GetLibItemName(), "| U1 pads:", len(fps["U1"].Pads()))

# 2. TP silk labels
tbad = []
for i in range(1, 35):
    ref = "TP%d" % i
    fp = fps[ref]
    vt = fp.Value()
    expect = pinmap[ref]["1"]
    if vt.GetText() != expect or vt.GetLayer() != pcbnew.F_SilkS:
        tbad.append((ref, vt.GetText(), expect, vt.GetLayer()))
print("TP silk labels bad:", tbad if tbad else "NONE (all 34 = net name on F.SilkS)")

# 3. courtyard overlaps
def cbox(fp):
    try:
        bb = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
        if bb.GetWidth() > 0 and bb.GetHeight() > 0:
            return (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom())
    except Exception:
        pass
    bb = fp.GetBoundingBox()
    return (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom())

def overlaps(board):
    fmap = {fp.GetReference(): fp for fp in board.GetFootprints()}
    refs = sorted(fmap)
    pairs = set()
    boxes = {r: cbox(fmap[r]) for r in refs}
    for i, r1 in enumerate(refs):
        for r2 in refs[i+1:]:
            a, c = boxes[r1], boxes[r2]
            if a[0] < c[2] and c[0] < a[2] and a[1] < c[3] and c[1] < a[3]:
                pairs.add((r1, r2))
    return pairs

ov3 = overlaps(b)
b2 = pcbnew.LoadBoard(B2)
ov2 = overlaps(b2)
print("courtyard overlap pairs: v2 =", len(ov2), " v3 =", len(ov3))
both_refs = set(comps) & {fp.GetReference() for fp in b2.GetFootprints()}
new_pairs = sorted(p for p in ov3 if p not in ov2)
print("pairs in v3 not in v2 (%d):" % len(new_pairs))
for p in new_pairs: print("  NEW", p)
gone = sorted(p for p in ov2 if p not in ov3 and p[0] in both_refs and p[1] in both_refs)
print("v2 pairs resolved in v3:", gone)
