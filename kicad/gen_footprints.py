#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KS0835F / RJ11_6P6C_TH フットプリント生成スクリプト
出典: R-Tone KS0835F データシート V1.3 の Package Size / PCB Decal 図

実物とズレがあった場合は GAP56 等の定数を直して再実行すること。
    python3 gen_footprints.py
"""
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "SLIC2PORT.pretty")

# KS0835F: 単列11ピン・2クラスタ (pin1-5 / pin6-11), ピッチ 2.54, ドリル 0.9
GAP56 = 20.3      # pin5-pin6 中心間距離 (図面値の解釈, 要実測)
PIN1_INSET = 1.5  # pin1 中心からモジュール右端まで
LAST_INSET = 5.54 # pin11 中心からモジュール左端まで (50.2 - 1.5 - 43.16)


def fp_line(x1, y1, x2, y2, layer="F.SilkS", w=0.12):
    return ('  (fp_line (start %.2f %.2f) (end %.2f %.2f) '
            '(stroke (width %s) (type solid)) (layer "%s"))'
            % (x1, y1, x2, y2, w, layer))


def gen_ks0835f():
    offsets = []
    for n in range(1, 12):
        if n == 1:
            offsets.append(0.0)
        elif n == 6:
            offsets.append(offsets[-1] + GAP56)
        else:
            offsets.append(offsets[-1] + 2.54)
    body_x0 = -(offsets[-1] + LAST_INSET)
    body_x1 = PIN1_INSET
    y0, y1 = -2.0, 4.6
    L = []
    L.append('(footprint "KS0835F"')
    L.append('  (version 20221018) (generator "pcbnew") (generator_version "7.0")')
    L.append('  (layer "F.Cu")')
    L.append('  (descr "KS0835F ringing SLIC module (R-Tone), 11-pin SIL 2-cluster, GAP56=%.1fmm - VERIFY against physical module before fabrication")' % GAP56)
    L.append('  (tags "SLIC KS0835F AG1171 FXS")')
    L.append('  (property "Reference" "REF**" (at 0 -4.5 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))')
    L.append('  (property "Value" "KS0835F" (at 0 6.2 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))')
    L.append('  (attr through_hole)')
    L.append(fp_line(body_x0, y0, body_x1, y0))
    L.append(fp_line(body_x1, y0, body_x1, y1))
    L.append(fp_line(body_x1, y1, body_x0, y1))
    L.append(fp_line(body_x0, y1, body_x0, y0))
    L.append('  (fp_circle (center 0 -3.6) (end 0.8 -3.6) (stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))')
    L.append(fp_line(body_x0 - 0.5, y0 - 0.5, body_x1 + 0.5, y0 - 0.5, "F.CrtYd", 0.05))
    L.append(fp_line(body_x1 + 0.5, y0 - 0.5, body_x1 + 0.5, y1 + 0.5, "F.CrtYd", 0.05))
    L.append(fp_line(body_x1 + 0.5, y1 + 0.5, body_x0 - 0.5, y1 + 0.5, "F.CrtYd", 0.05))
    L.append(fp_line(body_x0 - 0.5, y1 + 0.5, body_x0 - 0.5, y0 - 0.5, "F.CrtYd", 0.05))
    for i, off in enumerate(offsets):
        n = i + 1
        shape = "rect" if n == 1 else "circle"
        L.append('  (pad "%d" thru_hole %s (at %.2f 0) (size 1.7 1.7) (drill 0.9) (layers "*.Cu" "*.Mask"))' % (n, shape, -off))
    L.append(')')
    with open(os.path.join(OUT, "KS0835F.kicad_mod"), "w") as f:
        f.write("\n".join(L) + "\n")
    print("KS0835F.kicad_mod regenerated (GAP56=%.2f)" % GAP56)


def gen_rj11():
    L = []
    L.append('(footprint "RJ11_6P6C_TH"')
    L.append('  (version 20221018) (generator "pcbnew") (generator_version "7.0")')
    L.append('  (layer "F.Cu")')
    L.append('  (descr "Generic side-entry RJ11 6P6C PCB jack, single row 1.27mm pitch pins at rear - VERIFY against actual part")')
    L.append('  (tags "RJ11 6P6C modular")')
    L.append('  (property "Reference" "REF**" (at 0 -8.5 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))')
    L.append('  (property "Value" "RJ11_6P6C" (at 0 8.5 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))')
    L.append('  (attr through_hole)')
    L.append(fp_line(-6.75, -6.75, 6.75, -6.75))
    L.append(fp_line(6.75, -6.75, 6.75, 6.75))
    L.append(fp_line(6.75, 6.75, -6.75, 6.75))
    L.append(fp_line(-6.75, 6.75, -6.75, -6.75))
    for i in range(6):
        n = i + 1
        x = -3.175 + i * 1.27
        shape = "rect" if n == 1 else "circle"
        L.append('  (pad "%d" thru_hole %s (at %.3f 4.7) (size 1.6 1.6) (drill 0.9) (layers "*.Cu" "*.Mask"))' % (n, shape, x))
    L.append(')')
    with open(os.path.join(OUT, "RJ11_6P6C_TH.kicad_mod"), "w") as f:
        f.write("\n".join(L) + "\n")
    print("RJ11_6P6C_TH.kicad_mod regenerated")


if __name__ == "__main__":
    gen_ks0835f()
    gen_rj11()
