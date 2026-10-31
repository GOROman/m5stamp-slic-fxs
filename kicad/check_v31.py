import wx, json, math
_app = wx.App(False)
import pcbnew

W = "/Users/goroman/slic-board-work/"
B31 = W + "build/SLIC2PORT-FXS-v3.1.kicad_pcb"
B3 = W + "build/SLIC2PORT-FXS-v3.kicad_pcb"
b = pcbnew.LoadBoard(B31)
data = json.load(open(W + "netlist_v3.json"))
comps, nets = data["comps"], data["nets"]
pinmap = {}
for nname, nodes in nets.items():
    for ref, pin in nodes: pinmap.setdefault(ref, {})[str(pin)] = nname

fps = {fp.GetReference(): fp for fp in b.GetFootprints()}
print("footprints on board:", len(fps), "(expect 146 = 142 comps + 4 MH)")
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
    """layer-aware: F-side fps compared on F_CrtYd, B-side on B_CrtYd."""
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

def naive_pairs(board):
    """v3-checker style: one box per fp (F_CrtYd, fallback full bbox), layer-blind."""
    fmap = {fp.GetReference(): fp for fp in board.GetFootprints()}
    boxes = {}
    for r, fp in fmap.items():
        bx = cybox(fp, pcbnew.F_CrtYd)
        if not bx:
            bb = fp.GetBoundingBox()
            bx = (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom())
        boxes[r] = bx
    out = set()
    rs = sorted(boxes)
    for i, r1 in enumerate(rs):
        for r2 in rs[i+1:]:
            a, c = boxes[r1], boxes[r2]
            if a[0] < c[2] and c[0] < a[2] and a[1] < c[3] and c[1] < a[3]:
                out.add((r1, r2))
    return out

p31 = side_pairs(b)
b3 = pcbnew.LoadBoard(B3)
p3 = side_pairs(b3)
print("courtyard pairs (layer-aware): v3 =", len(p3), sorted(p3))
print("courtyard pairs (layer-aware): v3.1 =", len(p31), sorted(p31))
print("NEW pairs in v3.1 (layer-aware):", sorted(p31 - p3) if p31 - p3 else "NONE")
print("resolved vs v3:", sorted(p3 - p31) if p3 - p31 else "NONE")
n31 = naive_pairs(b)
extra = sorted(n31 - p31)
print("naive layer-blind pairs in v3.1:", len(n31), "| extra vs layer-aware (opposite-side artifacts):", extra)

# ---- distance table (centres and pads), v3 vs v3.1 ----
def load_fps(path):
    bb = pcbnew.LoadBoard(path)
    return {fp.GetReference(): fp for fp in bb.GetFootprints()}
def ctr(fmap, ref):
    p = fmap[ref].GetPosition(); return (p.x/1e6, p.y/1e6)
def pad(fmap, ref, pin):
    for p in fmap[ref].Pads():
        if p.GetNumber() == str(pin):
            q = p.GetPosition(); return (q.x/1e6, q.y/1e6)
def d(a, c): return math.hypot(a[0]-c[0], a[1]-c[1])
f3 = load_fps(B3)
rows = [
    ("C6 ctr -> U2 ctr",        lambda f: d(ctr(f,"C6"), ctr(f,"U2"))),
    ("C6 ctr -> U2.20 pad",     lambda f: d(ctr(f,"C6"), pad(f,"U2","20"))),
    ("C6 pad1(+5V) -> U2.20",   lambda f: d(pad(f,"C6","1"), pad(f,"U2","20"))),
    ("C23 ctr -> MOD_B.10 pad", lambda f: d(ctr(f,"C23"), pad(f,"MOD_B","10"))),
    ("C10 ctr -> MOD_B ctr",    lambda f: d(ctr(f,"C10"), ctr(f,"MOD_B"))),
    ("C10 ctr -> U1.13 pad",    lambda f: d(ctr(f,"C10"), pad(f,"U1","13"))),
    ("C10 pad1(+5V) -> U1.13",  lambda f: d(pad(f,"C10","1"), pad(f,"U1","13"))),
    ("C14 ctr -> MOD_A.10 pad", lambda f: d(ctr(f,"C14"), pad(f,"MOD_A","10"))),
    ("C14 ctr -> K1 ctr",       lambda f: d(ctr(f,"C14"), ctr(f,"K1"))),
    ("C13 ctr -> MOD_A.10 pad", lambda f: d(ctr(f,"C13"), pad(f,"MOD_A","10"))),
    ("C13 ctr -> MOD_A ctr",    lambda f: d(ctr(f,"C13"), ctr(f,"MOD_A"))),
    ("C13 ctr -> K1 ctr",       lambda f: d(ctr(f,"C13"), ctr(f,"K1"))),
    ("C22 ctr -> MOD_B.10 pad", lambda f: d(ctr(f,"C22"), pad(f,"MOD_B","10"))),
    ("C22 ctr -> MOD_B ctr",    lambda f: d(ctr(f,"C22"), ctr(f,"MOD_B"))),
    ("C3 ctr -> R4/R5 mid",     lambda f: d(ctr(f,"C3"), ((ctr(f,"R4")[0]+ctr(f,"R5")[0])/2, (ctr(f,"R4")[1]+ctr(f,"R5")[1])/2))),
    ("C4 ctr -> R4/R5 mid",     lambda f: d(ctr(f,"C4"), ((ctr(f,"R4")[0]+ctr(f,"R5")[0])/2, (ctr(f,"R4")[1]+ctr(f,"R5")[1])/2))),
    ("C5 ctr -> R6/R7 mid",     lambda f: d(ctr(f,"C5"), ((ctr(f,"R6")[0]+ctr(f,"R7")[0])/2, (ctr(f,"R6")[1]+ctr(f,"R7")[1])/2))),
]
print()
print("%-26s %8s %8s" % ("metric", "v3", "v3.1"))
for name, fn in rows:
    print("%-26s %8.2f %8.2f" % (name, fn(f3), fn(fps)))
print()
for r in ["C6","C10","C13","C14","C22","C23"]:
    print("v3.1 %s center = (%.2f, %.2f)" % (r, ctr(fps, r)[0], ctr(fps, r)[1]))
# confirm nothing else moved: compare all centres v3 vs v3.1
moved = []
for r in comps:
    if r in ("C6","C10","C13","C14","C22","C23"): continue
    a, c = ctr(f3, r), ctr(fps, r)
    if abs(a[0]-c[0]) > 0.01 or abs(a[1]-c[1]) > 0.01: moved.append(r)
print("non-target parts moved:", moved if moved else "NONE")
