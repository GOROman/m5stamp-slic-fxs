#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_net_format.py -- convert a .kicad_pcb whose pad nets are written in the
KiCad 10 name-only form  (net "NAME")  into the classic numbered form:

  - board-level declarations  (net 0 "") / (net N "NAME")  are inserted
    just before the first footprint, and
  - every pad net is rewritten to  (net N "NAME").

Why: KiCad 10.0.6's pcbnew (both the build scripts and a plain
LoadBoard -> SaveBoard round-trip) serializes pad nets by name only, with no
net table. KiCad itself reloads that fine (it rebuilds nets from the names),
but EasyEDA's KiCad importer expects the numbered form and silently drops
every net (imported board showed Nets = "None" only, 0 ratsnest lines,
autorouter placed 0 tracks). Boards v2/v3.1/v3.2 all had this defect; it was
invisible to our name-based checker. Fixed in board v3.3 (2026-10-31).

Net codes are assigned deterministically in first-appearance order.
Usage: fix_net_format.py <input.kicad_pcb> <output.kicad_pcb>
Verify the output by reloading it with pcbnew (net count / ratsnest) and by
grepping for '(net 0 "")' plus zero remaining '(net "' occurrences.
"""
import re, sys

src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding='utf-8').read()
names, seen = [], set()
for m in re.finditer(r'\(net "([^"]+)"\)', s):
    n = m.group(1)
    if n not in seen:
        seen.add(n); names.append(n)
code = {n: i + 1 for i, n in enumerate(names)}
print("distinct nets:", len(names))
s2 = re.sub(r'\(net "([^"]+)"\)',
            lambda m: '(net %d "%s")' % (code[m.group(1)], m.group(1)), s)
decls = '\t(net 0 "")\n' + ''.join('\t(net %d "%s")\n' % (code[n], n) for n in names)
idx = s2.index('\t(footprint ')
open(dst, 'w', encoding='utf-8').write(s2[:idx] + decls + s2[idx:])
print("written:", dst)
