#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KS0835F / RJ11_6P6C_TH フットプリント生成スクリプト
出典: R-Tone KS0835F データシート V1.3 の Package Size / PCB Decal 図

RJ11 は指定部品 (秋月 100954 = Neltron 7002-6P6C) のメーカー図面仕様
(下記 RJ11_* 定数の根拠コメント参照)。
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
# RJ11 6P6C 端子まわりの寸法仕様 (2026-10-31 v3.4.2 是正: 秋月 100954 指定)
#
# 指定部品: 秋月電子 100954 = Neltron 7002-6P6C (サイドエントリ、基板用)。
# 寸法の正はメーカー図面 research/neltron-7002-XPXC.pdf (秋月商品ページ
# 掲載の Neltron 公式図面)。旧仕様 (単列 1.27mm ピッチ、Issue #6) は
# 一般的な横型ジャックの想定であり、実部品とは端子配置そのものが違う
# (千鳥2列) ため本是正で置き換えた。
#
# 図面寸法 (mm):
#   接点ピッチ 1.02 TYP (千鳥配置: 隣接接点の横方向オフセット)
#   列間隔 2.54、推奨穴径 ø0.90 (PCB Layout 図)
#   位置決めペグ ø2.30 x2、ピッチ 12.00 (= Dim.C)
#   開口面 -> ペグ中心線 6.00、ペグ中心線 -> 近列 2.10
#     => 開口面から 近列 (pin2,4,6) 8.10 / 遠列 (pin1,3,5) 10.64
#   本体: 幅 12.20 (Dim.A、フランジ付きは 14.20 = Dim.D) x 奥行 15.00
#         x 高さ 14.35±0.25 (基板面から)
#   pin1 は下面図の "Pin 1" 指示で遠列の端 (基板上面から開口を手前に
#   見たとき右端)。中央ペア pin3=RING / pin4=TIP は DESIGN §5.1。
#
# ローカル座標: 原点 = ペグ中心線の中点、+y = 奥行方向 (背面側)。
#   開口面 y=-6.00、背面 y=+9.00、近列 y=+2.10、遠列 y=+4.64。
#
# パッド設計 (JLCPCB 2層1oz: 環状銅箔 絶対最小 0.18 / 銅間隔 最小 0.127):
#   パッド ø1.50 / ドリル ø0.90 => 環状銅箔 (1.50-0.90)/2 = 0.30
#     (絶対最小 0.18 だけでなく推奨 0.25 も満たす)
#   同列隣接間隔 = 2*1.02 - 1.50 = 0.54 (>= 0.127)
#   列間斜め間隔 = sqrt(1.02^2 + 2.54^2) - 1.50 = 1.24 (>= 0.127)
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

RJ11_PITCH = 1.02        # 接点ピッチ (千鳥の横方向オフセット, 図面 1.02 TYP)
RJ11_ROW_GAP = 2.54      # 列間隔
RJ11_DRILL = 0.90        # 図面推奨穴径 (PCB Layout: ø0.90)
RJ11_PAD = 1.50          # 円形パッド径
RJ11_PEG_DRILL = 2.30    # 位置決めペグ穴径 (NPTH)
RJ11_PEG_PITCH = 12.00   # ペグピッチ (Dim.C)
RJ11_PEG_TO_NEAR = 2.10  # ペグ中心線 -> 近列 (pin2,4,6)
RJ11_FACE_TO_PEG = 6.00  # 開口面 -> ペグ中心線
RJ11_BODY_W = 12.20      # 本体幅 (Dim.A)
RJ11_BODY_D = 15.00      # 本体奥行 (開口面 -> 背面)

def _rj11_pad_xy(n):
    # pin n (1..6): 横位置は接点順に 1.02mm ずつ、奇数ピンは遠列・偶数ピンは近列
    x = 2.55 - (n - 1) * RJ11_PITCH
    y = RJ11_PEG_TO_NEAR + (RJ11_ROW_GAP if n % 2 == 1 else 0.0)
    return x, y

def _check_rj11_spec():
    import math
    ring = (RJ11_PAD - RJ11_DRILL) / 2
    assert ring >= 0.18, "RJ11 annular ring %.3f < JLCPCB abs min 0.18" % ring
    pts = {n: _rj11_pad_xy(n) for n in range(1, 7)}
    for a in range(1, 7):
        for b in range(a + 1, 7):
            d = math.hypot(pts[a][0] - pts[b][0], pts[a][1] - pts[b][1]) - RJ11_PAD
            assert d >= 0.127, "RJ11 pad gap %d-%d %.3f < JLCPCB min 0.127" % (a, b, d)
    for n, (x, y) in pts.items():
        for px in (-RJ11_PEG_PITCH / 2, RJ11_PEG_PITCH / 2):
            d = math.hypot(x - px, y) - (RJ11_PAD + RJ11_PEG_DRILL) / 2
            assert d >= 0.127, "RJ11 pad-peg gap pin%d %.3f < 0.127" % (n, d)

def gen_rj11():
    _check_rj11_spec()
    L = []
    L.append('(footprint "RJ11_6P6C_TH"')
    L.append('  (version 20221018) (generator "pcbnew") (generator_version "7.0")')
    L.append('  (layer "F.Cu")')
    L.append('  (descr "Neltron 7002-6P6C side-entry modular jack (Akizuki 100954): staggered 2-row pins, contact pitch 1.02, row gap 2.54, drill 0.90 / pad 1.50 (annular 0.30), 2x NPTH peg holes dia 2.30 at 12.00 pitch, body 12.20x15.00. Per manufacturer drawing research/neltron-7002-XPXC.pdf (v3.4.2)")')
    L.append('  (tags "RJ11 6P6C modular Neltron 7002 Akizuki 100954")')
    L.append('  (property "Reference" "REF**" (at 0 10.6 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))')
    L.append('  (property "Value" "RJ11_6P6C" (at 0 -7.6 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))')
    L.append('  (attr through_hole)')
    x0, x1 = -RJ11_BODY_W / 2, RJ11_BODY_W / 2
    y0, y1 = -RJ11_FACE_TO_PEG, RJ11_BODY_D - RJ11_FACE_TO_PEG
    L.append(fp_line(x0, y0, x1, y0))
    L.append(fp_line(x1, y0, x1, y1))
    L.append(fp_line(x1, y1, x0, y1))
    L.append(fp_line(x0, y1, x0, y0))
    L.append('  (fp_circle (center 4.35 %.2f) (end 4.85 %.2f) (stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))' % (_rj11_pad_xy(1)[1], _rj11_pad_xy(1)[1]))
    cx, cy = RJ11_BODY_W / 2 + 0.25, RJ11_BODY_D / 2 - RJ11_FACE_TO_PEG
    L.append(fp_line(-cx, y0 - 0.3, cx, y0 - 0.3, "F.CrtYd", 0.05))
    L.append(fp_line(cx, y0 - 0.3, cx, y1 + 0.3, "F.CrtYd", 0.05))
    L.append(fp_line(cx, y1 + 0.3, -cx, y1 + 0.3, "F.CrtYd", 0.05))
    L.append(fp_line(-cx, y1 + 0.3, -cx, y0 - 0.3, "F.CrtYd", 0.05))
    for px in (-RJ11_PEG_PITCH / 2, RJ11_PEG_PITCH / 2):
        L.append('  (pad "" np_thru_hole circle (at %.2f 0) (size %.2f %.2f) (drill %.2f) (layers "*.Cu" "*.Mask"))' % (px, RJ11_PEG_DRILL, RJ11_PEG_DRILL, RJ11_PEG_DRILL))
    for n in range(1, 7):
        x, y = _rj11_pad_xy(n)
        shape = "rect" if n == 1 else "circle"
        L.append('  (pad "%d" thru_hole %s (at %.3f %.2f) (size %.2f %.2f) (drill %.2f) (layers "*.Cu" "*.Mask"))' % (n, shape, x, y, RJ11_PAD, RJ11_PAD, RJ11_DRILL))
    L.append(')')
    with open(os.path.join(OUT, "RJ11_6P6C_TH.kicad_mod"), "w") as f:
        f.write("\n".join(L) + "\n")
    print("RJ11_6P6C_TH.kicad_mod regenerated (Neltron 7002 / Akizuki 100954)")

if __name__ == "__main__":
    gen_ks0835f()
    gen_rj11()
