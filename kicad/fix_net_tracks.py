# -*- coding: utf-8 -*-
"""Post-process fix_net_format.py output for KiCad 10.0.6 compatibility.

Empirically verified on KiCad 10.0.6 (2026-10-31):
- (net N "NAME") combined form: accepted in the net table and in pads,
  but REJECTED by the parser inside (segment ...), (via ...) and
  (zone ...) blocks ("Expecting ')'" parse failure).
- (net N) code-only: accepted in segments/vias (resolves via the
  table), but IGNORED in zones (zone loads with empty net).
- (net "NAME") name-only: accepted everywhere; it is KiCad 10's
  native form for zones.

So the loadable hybrid is:
  table + pads : (net N "NAME")   (from fix_net_format.py)
  segment/via  : (net N)          (rewritten here)
  zone         : (net "NAME")     (rewritten here)

Usage: fix_net_tracks.py <input.kicad_pcb> <output.kicad_pcb>
(input = output of fix_net_format.py). Verify by reloading with
pcbnew and running kicad-cli DRC (unconnected count must match the
pre-conversion board)."""
import re, sys

src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding="utf-8").read()

def block_spans(text, kw):
    pat = "\n\t(" + kw
    spans = []
    i = 0
    while True:
        j = text.find(pat, i)
        if j < 0:
            break
        depth = 0
        k = j + 1
        inq = False
        while k < len(text):
            c = text[k]
            if inq:
                if c == "\\":
                    k += 1
                elif c == '"':
                    inq = False
            else:
                if c == '"':
                    inq = True
                elif c == "(":
                    depth += 1
                elif c == ")":
                    depth -= 1
                    if depth == 0:
                        break
            k += 1
        spans.append((j, k + 1))
        i = k + 1
    return spans

jobs = []
for kw in ("segment", "via"):
    for (a, b) in block_spans(s, kw):
        jobs.append((a, b, "code"))
for (a, b) in block_spans(s, "zone"):
    jobs.append((a, b, "name"))
jobs.sort()
out = []
pos = 0
n_code = n_name = 0
for (a, b, mode) in jobs:
    out.append(s[pos:a])
    blk = s[a:b]
    if mode == "code":
        blk, cnt = re.subn(r'\(net (\d+) "[^"]+"\)', r'(net \1)', blk)
        n_code += cnt
    else:
        blk, cnt = re.subn(r'\(net (\d+) "([^"]+)"\)', r'(net "\2")', blk)
        n_name += cnt
    out.append(blk)
    pos = b
out.append(s[pos:])
open(dst, "w", encoding="utf-8").write("".join(out))
print("track refs -> code-only:", n_code, "; zone refs -> name-only:", n_name)
