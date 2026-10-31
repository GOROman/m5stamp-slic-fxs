import wx, json, math
_app = wx.App(False)
import pcbnew

W = "/Users/goroman/slic-board-work/"
B32 = W + "build/SLIC2PORT-FXS-v3.2.kicad_pcb"
B31 = W + "build/SLIC2PORT-FXS-v3.1.kicad_pcb"
b = pcbnew.LoadBoard(B32)
data = json.load(open(W + "netlist_v32.json"))
comps, nets = data["comps"], data["nets"]
pinmap = {}
for nname, nodes in nets.items():
    for ref, pin in nodes: pinmap.setdefault(ref, {})[str(pin)] = nname

fps = {fp.GetReference(): fp for fp in b.GetFootprints()}
print("footprints on board:", len(fps), "(expect 160 = 156 comps + 4 MH)")
print("comps missing from board:", [r for r in comps if r not in fps])

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

print("C10 layer: B_Cu" if fps["C10"].GetLayer() == pcbnew.B_Cu else "C10 layer: NOT B_Cu", "| IsFlipped:", fps["C10"].IsFlipped())
bcu = sorted(fp.GetReference() for fp in b.GetFootprints() if fp.GetLayer() == pcbnew.B_Cu)
print("B.Cu footprints:", bcu)

tbad = []
for i in range(1, 35):
    ref = "TP%d" % i
    vt = fps[ref].Value()
    if vt.GetText() != pinmap[ref]["1"] or vt.GetLayer() != pcbnew.F_SilkS:
        tbad.append(ref)
print("TP silk labels bad:", tbad if tbad else "NONE")

def cybox(fp, layer):
    try:
        bb = fp.GetCourtyard(layer).BBox()
        if bb.GetWidth() > 0 and bb.GetHeight() > 0:
            return (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom())
    except Exception:
        pass
    return None

def side_pairs(board):
    fmap = {fp.GetReference(): fp for fp in board.GetFootprints()}
    out = set()
    for side_layer, cy_layer in ((pcbnew.F_Cu, pcbnew.F_CrtYd), (pcbnew.B_Cu, pcbnew.B_CrtYd)):
        refs = [r for r, fp in fmap.items() if fp.GetLayer() == side_layer]
        boxes = {}
        for r in refs:
            bx = cybox(fmap[r], cy_layer)
            if bx: boxes[r] = bx
        rs = sorted(boxes)
        for i, r1 in enumerate(rs):
            for r2 in rs[i+1:]:
                a, c = boxes[r1], boxes[r2]
                if a[0] < c[2] and c[0] < a[2] and a[1] < c[3] and c[1] < a[3]:
                    out.add((r1, r2))
    return out

p32 = side_pairs(b)
b31 = pcbnew.LoadBoard(B31)
p31 = side_pairs(b31)
print("courtyard pairs (layer-aware): v3.1 =", len(p31), sorted(p31))
print("courtyard pairs (layer-aware): v3.2 =", len(p32), sorted(p32))
print("NEW pairs in v3.2 vs v3.1:", sorted(p32 - p31) if p32 - p31 else "NONE")

# ---- new parts: position / layer report ----
def ctr(fmap, ref):
    p = fmap[ref].GetPosition(); return (p.x/1e6, p.y/1e6)
NEW32 = ["D4","D5","D6","D7","D8","D9","Q5","Q6",
         "R_LED3","R_LED4","R_LED5","R_LED6","R_LED7","R_LED8"]
for r in NEW32:
    print("v3.2 %s center = (%.2f, %.2f) layer F:%s" % (
        r, ctr(fps, r)[0], ctr(fps, r)[1], fps[r].GetLayer() == pcbnew.F_Cu))

# LED role silk labels present?
texts = set()
for t in b.GetDrawings():
    if isinstance(t, pcbnew.PCB_TEXT):
        texts.add(t.GetText())
want = {"HOOK_A","RING_A","LINK_A","HOOK_B","RING_B","LINK_B"}
print("LED silk labels missing:", sorted(want - texts) if want - texts else "NONE")

# ---- nothing else moved vs v3.1 ----
f31 = {fp.GetReference(): fp for fp in b31.GetFootprints()}
moved = []
for r in comps:
    if r in NEW32: continue
    a, c = ctr(f31, r), ctr(fps, r)
    if abs(a[0]-c[0]) > 0.01 or abs(a[1]-c[1]) > 0.01: moved.append(r)
print("non-target parts moved vs v3.1:", moved if moved else "NONE")
