#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KS0835F / RJ11_6P6C_TH フットプリント生成スクリプト
出典: R-Tone KS0835F データシート V1.3 の Package Size / PCB Decal 図

RJ11 の穴径/パッドは Issue #6 で是正した仕様 (下記 RJ11_* 定数の根拠コメント
参照)。実ジャックの実測で端子寸法が変わる場合は定数を直して再実行すること。
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


# ---------------------------------------------------------------------------
# RJ11 6P6C 端子まわりの寸法仕様 (Issue #6, 2026-10-31 是正)
#
# 端子: この種のサイドエントリ型ジャックのコンタクトは Ø0.46mm の丸線
#   (JST MOD-J6 シリーズ図面の ø0.46、中華系 52 シリーズ図面の φ0.46 と一致)。
# 穴径: JST MOD-J6 の推奨 PCB レイアウトは 6-ø0.8±0.05。帯域内 (0.75..0.85)
#   で、丸線 Ø0.46 に対し直径クリアランス 0.29mm を確保できる 0.75 を採用。
#   旧仕様の 0.9 は過大で、環状銅箔を圧迫していた。
# パッド: ピッチ 1.27mm 単列の制約下で、JLCPCB 2層1oz の
#   環状銅箔 (絶対最小 0.18mm / 推奨 0.25mm) と最小銅間隔 (0.10mm) の
#   両方に >=0.02mm のマージンを持たせる設計点:
#     短辺環状銅箔 = (1.15 - 0.75) / 2 = 0.20mm  (>= 0.18)
#     隣接パッド間隔 = 1.27 - 1.15     = 0.12mm  (>= 0.10)
#     長辺環状銅箔 = (1.70 - 0.75) / 2 = 0.475mm
#   推奨 0.25mm には W=1.25 が必要で間隔が 0.02mm となり両立しないため、
#   絶対最小 +0.02mm を設計判断とする (Issue #6 に記録)。
# 基板 (gerber/*.kicad_pcb) への反映は実ジャック実測後に監査側で行う。
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Stamp-S3-Socket (U1) 端子まわりの寸法仕様 (Issue #11, 2026-10-31 是正)
#
# 本フットプリントは生成対象ではなく SLIC2PORT.pretty/Stamp-S3-Socket.kicad_mod
# を直接管理する。寸法の正はここに記録し、ライブラリ・基板・本仕様の3者を
# tests/test_hardware.py の PTH 全数環状銅箔検査で同期確認する。
#
# 対象部品: M5Stamp S3 を受ける 1.27mm ピッチ メスヘッダ (左列 17P / 右列 11P、
#   列間 17.2mm)。ヘッダのはんだテールはこの種の標準品で 0.4mm 角〜Ø0.5mm。
# 穴径: テール対角 (0.4mm 角 -> 0.57mm) に対して標準的な 0.7mm を採用。
#   根拠なく小さくはしない (Issue #11 の条件)。
# パッド: ピッチ 1.27mm の制約下で、JLCPCB 2層1oz の環状銅箔
#   (絶対最小 0.18mm) と最小銅間隔 (0.10mm) を両立させる設計点:
#     環状銅箔     = (1.1 - 0.7) / 2 = 0.20mm  (>= 0.18)
#     隣接パッド間隔 = 1.27 - 1.1    = 0.17mm  (>= 0.10)
#   推奨 0.25mm にはパッド 1.2mm が必要で間隔が 0.07mm となり両立しないため、
#   RJ11 (Issue #6) と同じく絶対最小 +0.02mm を設計判断とする。
# 旧仕様 (パッド 1.0 / ドリル 0.7 = 環状 0.15mm) は e5a03df で是正済み。
# ---------------------------------------------------------------------------
SOCKET_PITCH = 1.27
SOCKET_DRILL = 0.7
SOCKET_PAD = 1.1    # 正方形パッド一辺

RJ11_PITCH = 1.27
RJ11_DRILL = 0.75
RJ11_PAD_W = 1.15   # ピッチ方向 (短辺)
RJ11_PAD_L = 1.70   # 奥行方向 (長辺)

def _check_rj11_spec():
    ring = (RJ11_PAD_W - RJ11_DRILL) / 2
    gap = RJ11_PITCH - RJ11_PAD_W
    assert ring >= 0.18, "RJ11 annular ring %.3f < JLCPCB abs min 0.18" % ring
    assert gap >= 0.10, "RJ11 pad gap %.3f < JLCPCB min spacing 0.10" % gap

def gen_rj11():
    _check_rj11_spec()
    L = []
    L.append('(footprint "RJ11_6P6C_TH"')
    L.append('  (version 20221018) (generator "pcbnew") (generator_version "7.0")')
    L.append('  (layer "F.Cu")')
    L.append('  (descr "Generic side-entry RJ11 6P6C PCB jack, single row 1.27mm pitch pins at rear. Contact wire dia 0.46 (JST MOD-J6 class); drill 0.75 / pad 1.15x1.70 per Issue #6 spec (annular ring 0.20mm) - VERIFY against actual part")')
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
        x = -3.175 + i * RJ11_PITCH
        shape = "rect" if n == 1 else "oval"
        L.append('  (pad "%d" thru_hole %s (at %.3f 4.7) (size %.2f %.2f) (drill %.2f) (layers "*.Cu" "*.Mask"))' % (n, shape, x, RJ11_PAD_W, RJ11_PAD_L, RJ11_DRILL))
    L.append(')')
    with open(os.path.join(OUT, "RJ11_6P6C_TH.kicad_mod"), "w") as f:
        f.write("\n".join(L) + "\n")
    print("RJ11_6P6C_TH.kicad_mod regenerated")


if __name__ == "__main__":
    gen_ks0835f()
    gen_rj11()
