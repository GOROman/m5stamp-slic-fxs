#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLIC2PORT-FXS : M5StampS3 制御 2ポート疑似交換機
SKiDL 回路定義 (ネットリスト生成 + 簡易 ERC)

設計書: ../../DESIGN.md
使い方:
    python3 m5stamp_slic2port.py
    -> m5stamp_slic2port.net (KiCad ネットリスト) を生成し ERC を実行する

注意:
  - 部品はすべて SKIDL ネイティブ定義 (ライブラリ不要)。
  - フットプリント文字列の一部は KiCad 標準ライブラリ名の「想定」であり、
    実装前に KiCad 側で実在確認すること (README_CAD.md 参照)。
  - KS0835F / RJ11 / Stamp-S3-Socket は本プロジェクトのローカルライブラリ
    (SLIC2PORT.pretty / 同梱シンボル) を指す。
"""

from skidl import *

reset()

# ---------------------------------------------------------------------------
# フットプリント (想定含む)
# ---------------------------------------------------------------------------
FP_R0805   = "Resistor_SMD:R_0805_2012Metric"
FP_C0805   = "Capacitor_SMD:C_0805_2012Metric"
FP_C1206   = "Capacitor_SMD:C_1206_3216Metric"
FP_ELEC    = "Capacitor_THT:CP_Radial_D8.0mm_P3.50mm"
FP_DO41    = "Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal"
FP_SMB     = "Diode_SMD:D_SMB"
FP_SMC     = "Diode_SMD:D_SMC"
FP_LED0805 = "LED_SMD:LED_0805_2012Metric"
FP_BEAD    = "Inductor_SMD:L_0805_2012Metric"          # フェライトビーズ想定
FP_FUSE    = "Fuse:Fuse_1812_4532Metric"               # 想定
FP_SOT23   = "Package_TO_SOT_SMD:SOT-23"
FP_SOIC20  = "Package_SO:SOIC-20W_7.5x12.8mm_P1.27mm"
FP_SOIC16  = "Package_SO:SOIC-16_3.9x9.9mm_P1.27mm"
FP_USBC    = "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12"  # 想定
FP_TERM2   = "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2_1x02_P5.00mm_Horizontal"  # 想定
FP_HDR2X5  = "Connector_PinHeader_2.54mm:PinHeader_2x05_P2.54mm_Vertical"
FP_HDR1X4  = "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical"
FP_HDR1X2  = "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical"
FP_HDR1X1  = "Connector_PinHeader_2.54mm:PinHeader_1x01_P2.54mm_Vertical"
FP_TACT    = "Button_Switch_THT:SW_PUSH_6mm"
FP_KS0835F = "SLIC2PORT:KS0835F"
FP_RJ11    = "SLIC2PORT:RJ11_6P6C_TH"
FP_STAMP   = "SLIC2PORT:Stamp-S3-Socket"  # ソケット実装 (直接はんだ付けしない)

# ---------------------------------------------------------------------------
# テンプレート部品
# ---------------------------------------------------------------------------
def tmpl(name, pin_specs, footprint):
    # PASSIVE 指定: SKIDL ネイティブ定義では pin function を与えないと
    # UNSPECIFIED 同士の conflict 警告が大量に出るため、受動扱いにする。
    # この ERC は未接続等の簡易検査のみ。電圧/駆動能力/極性/パッド対応は別途検証する。
    pins = [Pin(num=num, name=nm, func=Pin.PASSIVE) for num, nm in pin_specs]
    return Part(tool=SKIDL, name=name, dest=TEMPLATE, pins=pins,
                footprint=footprint)

RES   = tmpl("R",    [(1, "1"), (2, "2")], FP_R0805)
CAP   = tmpl("C",    [(1, "1"), (2, "2")], FP_C0805)
CAPL  = tmpl("C",    [(1, "1"), (2, "2")], FP_C1206)
ELEC  = tmpl("C",    [(1, "+"), (2, "-")], FP_ELEC)
DIO   = tmpl("D",    [(1, "K"), (2, "A")], FP_DO41)
# 注意: DIO()/BEAD() の各インスタンスには基板 v3.4 のシルク番号に合わせた
# ref を明示すること。SKiDL の自動採番は生成時の部品順序で変動し、保存
# ネットリスト/基板と番号がドリフトした前例がある (U 系 18 部品)。
# 対象: 還流 U45/U49、保護 U55-U60/U82-U87、ビード U64/U91、PD U79/U106。     # 1N400x 等 (調達は 1N4007: 1N4004 の上位互換)
LED   = tmpl("LED",  [(1, "K"), (2, "A")], FP_LED0805)
BEAD  = tmpl("FB",   [(1, "1"), (2, "2")], FP_BEAD)
FUSEP = tmpl("F",    [(1, "1"), (2, "2")], FP_FUSE)
SOT23 = tmpl("Q",    [(1, "G"), (2, "S"), (3, "D")], FP_SOT23)
TACT  = tmpl("SW",   [(1, "1"), (2, "2")], FP_TACT)
TP    = tmpl("TP",   [(1, "1")], FP_HDR1X1)

KS0835F = tmpl("KS0835F",
               [(1, "RING"), (2, "TIP"), (3, "FR"), (4, "RM"), (5, "SHK"),
                (6, "VR"), (7, "VX"), (8, "NC"), (9, "GND"), (10, "VDC"),
                (11, "PD")], FP_KS0835F)

RJ11 = tmpl("RJ11_6P6C",
            [(i, str(i)) for i in range(1, 7)], FP_RJ11)

# M5StampS3 公式シンボル (M5_Hardware) のピン対応:
#  1:G1 2:G2 3:G3 4:G4 5:G5 6:G6 7:G7 8:G8 9:G9 10:G10 11:GND 12:G11
#  13:5V 14:G12 15:G13 16:G14 17:G15 18:GND 19:G39 20:G0 21:G40 22:EN
#  23:G41 24:G44 25:G42 26:G43 27:G46 28:3V3
STAMP_PINS = [(1, "G1"), (2, "G2"), (3, "G3"), (4, "G4"), (5, "G5"),
              (6, "G6"), (7, "G7"), (8, "G8"), (9, "G9"), (10, "G10"),
              (11, "GND"), (12, "G11"), (13, "5V"), (14, "G12"),
              (15, "G13"), (16, "G14"), (17, "G15"), (18, "GND"),
              (19, "G39"), (20, "G0"), (21, "G40"), (22, "EN"),
              (23, "G41"), (24, "G44"), (25, "G42"), (26, "G43"),
              (27, "G46"), (28, "3V3")]
STAMP = tmpl("M5STAMPS3", STAMP_PINS, FP_STAMP)

HCT244 = tmpl("74HCT244",
              [(1, "1OE"), (2, "1A1"), (3, "2Y4"), (4, "1A2"), (5, "2Y3"),
               (6, "1A3"), (7, "2Y2"), (8, "1A4"), (9, "2Y1"), (10, "GND"),
               (11, "2A1"), (12, "1Y4"), (13, "2A2"), (14, "1Y3"),
               (15, "2A3"), (16, "1Y2"), (17, "2A4"), (18, "1Y1"),
               (19, "2OE"), (20, "VCC")], FP_SOIC20)

# Omron G5V-2 (DPDT 信号リレー) 端子番号はデータシート (bottom view) 準拠:
#   コイル: 1 / 16 (標準タイプは無極性)
#   極1: COM=4, NC=6, NO=8    極2: COM=13, NC=11, NO=9
FP_G5V2 = "Relay_THT:Relay_DPDT_Omron_G5V-2"
G5V2 = tmpl("G5V-2",
            [(1, "COIL1"), (16, "COIL2"),
             (4, "COM1"), (6, "NC1"), (8, "NO1"),
             (13, "COM2"), (11, "NC2"), (9, "NO2")], FP_G5V2)

# HRO TYPE-C-31-M-12 / KiCad 公式フットプリントの実パッド番号。
USBC = tmpl("USB_C",
            [("A1", "GND_A1"), ("A12", "GND_A12"),
             ("B1", "GND_B1"), ("B12", "GND_B12"),
             ("A4", "VBUS_A4"), ("A9", "VBUS_A9"),
             ("B4", "VBUS_B4"), ("B9", "VBUS_B9"),
             ("A5", "CC1"), ("B5", "CC2"),
             ("A6", "DP_A"), ("B6", "DP_B"),
             ("A7", "DN_A"), ("B7", "DN_B"),
             ("A8", "SBU1"), ("B8", "SBU2"), ("S1", "SHIELD")], FP_USBC)

TERM2 = tmpl("TB", [(1, "+"), (2, "-")], FP_TERM2)
HDR2X5 = tmpl("HDR", [(i, str(i)) for i in range(1, 11)], FP_HDR2X5)
HDR1X4 = tmpl("HDR", [(i, str(i)) for i in range(1, 5)], FP_HDR1X4)
HDR1X2 = tmpl("HDR", [(i, str(i)) for i in range(1, 3)], FP_HDR1X2)

# ---------------------------------------------------------------------------
# RefDes カウンタ付き生成ヘルパ
# ---------------------------------------------------------------------------
_cnt = {}
def _mk(t, prefix, value, ref=None):
    p = t()
    if ref:
        p.ref = ref
    else:
        _cnt[prefix] = _cnt.get(prefix, 0) + 1
        p.ref = "%s%d" % (prefix, _cnt[prefix])
    p.value = value
    return p

def R(value, ref=None):  return _mk(RES, "R", value, ref)
def C(value, ref=None):  return _mk(CAP, "C", value, ref)
def CL(value, ref=None): return _mk(CAPL, "C", value, ref)
def CE(value, ref=None): return _mk(ELEC, "C", value, ref)

def conn(net, *pins):
    for pin in pins:
        net += pin

def between(part, a, b):
    """2端子部品をネット a-b 間に接続"""
    a += part[1]
    b += part[2]

# ---------------------------------------------------------------------------
# 共通ネット
# ---------------------------------------------------------------------------
GND      = Net("GND")
P5V      = Net("+5V")
P3V3     = Net("+3V3")
VIN_RAW  = Net("VIN_RAW")
VIN_F    = Net("VIN_F")
VAUD     = Net("VAUD")
VREF165  = Net("VREF165")
TONE_BUS = Net("TONE_BUS")
PD_BUS   = Net("PD_BUS")

# ===========================================================================
# 電源入力
# ===========================================================================
j_usb = USBC(); j_usb.ref = "J1"; j_usb.value = "USB-C_PWR"
for n in ("A1", "A12", "B1", "B12", "S1"):
    GND += j_usb[n]
for n in ("A4", "A9", "B4", "B9"):
    VIN_RAW += j_usb[n]
for n in ("A6", "B6", "A7", "B7", "A8", "B8"):
    j_usb[n] += NC
between(R("5.1K"), j_usb["CC1"], GND)
between(R("5.1K"), j_usb["CC2"], GND)

j_term = TERM2(); j_term.ref = "J2"; j_term.value = "DC5V_IN"
VIN_RAW += j_term["+"]
GND += j_term["-"]

f1 = FUSEP(); f1.ref = "F1"; f1.value = "Polyfuse_2A"
between(f1, VIN_RAW, VIN_F)

q1 = SOT23(); q1.ref = "Q1"; q1.value = "AO3401A"
# P-FET のボディダイオードを入力 D -> 出力 S とする。
VIN_F += q1["D"]
P5V += q1["S"]
n_qg = Net("Q1_GATE")
n_qg += q1["G"]
between(R("100K"), n_qg, GND)

d_tvs = DIO(); d_tvs.ref = "D1"; d_tvs.value = "SMBJ5.0A"
d_tvs.footprint = FP_SMB
P5V += d_tvs["K"]
GND += d_tvs["A"]

between(CE("1000uF/10V"), P5V, GND)   # 入力バルク (+/- は between では極性不問接続)
c_in2 = C("100nF"); between(c_in2, P5V, GND)

# ===========================================================================
# VAUD (2.5V 音声バイアス) / VREF165 (1.65V ADC バイアス)
# ===========================================================================
between(R("4.7K"), P5V, VAUD)
between(R("4.7K"), VAUD, GND)
between(CL("10uF"), VAUD, GND)
between(C("100nF"), VAUD, GND)

between(R("47K"), P3V3, VREF165)
between(R("47K"), VREF165, GND)
between(C("100nF"), VREF165, GND)

# ===========================================================================
# M5StampS3 (U1) -- ソケット実装
# ===========================================================================
# U1 は基板へ直接はんだ付けせず、1.27mm ピッチ メスピンヘッダ (17P + 11P、
# 列間 17.2mm) のソケットで接続する。フットプリント SLIC2PORT:Stamp-S3-Socket
# のパッド位置は M5Stack 公式 Stamp-S3-SMD フットプリントから実測した
# (左列 pins 1-17 / 右列 pins 18-28、右列の -y 側 6 位置はモジュールの
# アンテナ側で欠け)。Stamp 本体側には 1.27mm オスピンをキャスタレーションへ
# はんだ付けして差し込む。ベアモジュール下面の GND パッド (29-31) は
# ソケット構成では未接続になる (GND は pins 11/18 で確保)。
u1 = STAMP(); u1.ref = "U1"; u1.value = "M5StampS3/S3A"
GND += u1[11]; GND += u1[18]
P5V += u1[13]
P3V3 += u1[28]

N = {}
def mknet(name):
    n = Net(name)
    N[name] = n
    return n

MON_A    = mknet("MON_A");    MON_B = mknet("MON_B")
TONE33   = mknet("TONE_PWM_33")
SHK_A_33 = mknet("SHK_A_33"); SHK_B_33 = mknet("SHK_B_33")
RM_A_33  = mknet("RM_A_33");  RM_B_33 = mknet("RM_B_33")
FR_A_33  = mknet("FR_A_33");  FR_B_33 = mknet("FR_B_33")
SEL_A_33 = mknet("SEL_A_33"); SEL_B_33 = mknet("SEL_B_33")
PD_EN    = mknet("PD_EN")
GPIO0    = mknet("GPIO0");    EN_NET = mknet("EN")
GPIO3    = mknet("GPIO3");    GPIO4 = mknet("GPIO4"); GPIO5 = mknet("GPIO5")
GPIO39   = mknet("GPIO39");   GPIO40 = mknet("GPIO40")
GPIO41   = mknet("GPIO41");   GPIO42 = mknet("GPIO42"); GPIO46 = mknet("GPIO46")
GPIO43   = mknet("GPIO43");   GPIO44 = mknet("GPIO44")

MON_A += u1["G1"];   MON_B += u1["G2"]
GPIO3 += u1["G3"];   GPIO4 += u1["G4"];  GPIO5 += u1["G5"]
TONE33 += u1["G6"]
SHK_A_33 += u1["G7"];  RM_A_33 += u1["G8"];  FR_A_33 += u1["G9"]
SHK_B_33 += u1["G10"]; RM_B_33 += u1["G11"]; FR_B_33 += u1["G12"]
SEL_A_33 += u1["G13"]; SEL_B_33 += u1["G14"]; PD_EN += u1["G15"]
GPIO39 += u1["G39"]; GPIO0 += u1["G0"]; GPIO40 += u1["G40"]
EN_NET += u1["EN"];  GPIO41 += u1["G41"]; GPIO44 += u1["G44"]
GPIO42 += u1["G42"]; GPIO43 += u1["G43"]; GPIO46 += u1["G46"]

# EN プルアップ + リセット/ブート スイッチ
between(R("10K"), P3V3, EN_NET)
sw_rst = TACT(); sw_rst.ref = "SW1"; sw_rst.value = "RST"
between(sw_rst, EN_NET, GND)
sw_boot = TACT(); sw_boot.ref = "SW2"; sw_boot.value = "BOOT"
between(sw_boot, GPIO0, GND)

# ステータス LED (GPIO4) / 電源 LED
n_leda = Net("LED_ST_A")
r_led2 = R("470", ref="R_LED2")
GPIO4 += r_led2[1]
n_leda += r_led2[2]
d_led2 = LED(); d_led2.ref = "D3"; d_led2.value = "LED_GRN"
n_leda += d_led2["A"]; GND += d_led2["K"]

n_ledp = Net("LED_PWR_A")
r_led1 = R("1K", ref="R_LED1")
P5V += r_led1[1]; n_ledp += r_led1[2]
d_led1 = LED(); d_led1.ref = "D2"; d_led1.value = "LED_RED"
n_ledp += d_led1["A"]; GND += d_led1["K"]

# 拡張 / デバッグ ヘッダ
j_exp = HDR2X5(); j_exp.ref = "J5"; j_exp.value = "EXPANSION"
P3V3 += j_exp[1]; GND += j_exp[2]; GPIO4 += j_exp[3]; GPIO5 += j_exp[4]
GPIO39 += j_exp[5]; GPIO40 += j_exp[6]; GPIO41 += j_exp[7]
GPIO42 += j_exp[8]; GPIO46 += j_exp[9]; GPIO3 += j_exp[10]

j_dbg = HDR1X4(); j_dbg.ref = "J6"; j_dbg.value = "UART_DBG"
GND += j_dbg[1]; GPIO43 += j_dbg[2]; GPIO44 += j_dbg[3]; P3V3 += j_dbg[4]

# テストポイント
tp1 = TP(); tp1.ref = "TP1"; P5V += tp1[1]
tp2 = TP(); tp2.ref = "TP2"; GND += tp2[1]
tp3 = TP(); tp3.ref = "TP3"; TONE_BUS += tp3[1]

# ===========================================================================
# 74HCT244 レベル変換 (U2)
# ===========================================================================
u2 = HCT244(); u2.ref = "U2"; u2.value = "74HCT244"
GND += u2["1OE"]; GND += u2["2OE"]; GND += u2["GND"]; GND += u2["2A4"]
# 未使用チャネル (2A4 入力 / 2Y4 出力): 入力 2A4 は上のとおり GND に落としてある。
# 出力 2Y4 (パッド3) はオープンが正しい。CAD 側 DRC で「U2.3 未接続」と
# 検出されるが、フローティング入力ではなく意図的な無接続なので対処不要。
u2["2Y4"] += NC
P5V += u2["VCC"]
FR_A_5V  = mknet("FR_A_5V");  RM_A_5V = mknet("RM_A_5V")
SEL_A_5V = mknet("SEL_A_5V"); TONE_5V = mknet("TONE_5V")
FR_B_5V  = mknet("FR_B_5V");  RM_B_5V = mknet("RM_B_5V")
SEL_B_5V = mknet("SEL_B_5V")
FR_A_33 += u2["1A1"]; FR_A_5V += u2["1Y1"]
RM_A_33 += u2["1A2"]; RM_A_5V += u2["1Y2"]
SEL_A_33 += u2["1A3"]; SEL_A_5V += u2["1Y3"]
TONE33 += u2["1A4"];  TONE_5V += u2["1Y4"]
FR_B_33 += u2["2A1"]; FR_B_5V += u2["2Y1"]
RM_B_33 += u2["2A2"]; RM_B_5V += u2["2Y2"]
SEL_B_33 += u2["2A3"]; SEL_B_5V += u2["2Y3"]
between(C("100nF"), P5V, GND)   # U2 デカップリング

# ===========================================================================
# トーン生成チェーン (TONE_5V -> RC x2 -> TONE_BUS)
# ===========================================================================
TN1 = Net("TONE_N1"); TN2 = Net("TONE_N2"); TONE_AC = Net("TONE_AC")
between(R("10K"), TONE_5V, TN1)
between(C("47nF"), TN1, GND)
between(R("10K"), TN1, TN2)
between(C("47nF"), TN2, GND)
between(R("47K"), TONE_AC, TONE_BUS)
between(R("100K"), TONE_BUS, VAUD)
# フィルタ出力のDCを切り、TONE_BUSをVAUDへバイアスする。
# TONE_BUSからVAUDへ100nFを並列に入れると400Hzも強く減衰する。
between(C("100nF"), TN2, TONE_AC)

# ===========================================================================
# 音声クロス接続リレー (K1/K2)
# 秋月電子の簡易擬似電話交換機キットと同様、通話路はリレー接点で切り替える。
# リレー: Omron G5V-2 DC5 (DPDT、コイル 50ohm / 100mA @5V)。
#   SEL_x = L (無励磁): NC 接点 = 相手 VX (クロス接続。電源断時もこの状態)
#   SEL_x = H (励磁)  : NO 接点 = TONE_BUS
# ファームウェアの SEL 意味論 (L=相手VX / H=トーン) は CD4053 版と同一で変更不要。
# 2 極は同一ネットへ並列接続し、接点抵抗と信頼性を稼ぐ。
# ドライバはキット (2SC2712) と同じローサイド方式: 2N7002 + 還流ダイオード。
# 旧 CD4053 の Z チャネル (AUX_TP モニタ) は、TP 増設で各音声ノードを直接
# 測れるようになったため廃止した (TP3 は TONE_BUS に割当変更)。
# ===========================================================================
VR_A_IN = mknet("VR_A_IN"); VR_B_IN = mknet("VR_B_IN")
RLY = {}
for s, sel5v in (("A", SEL_A_5V), ("B", SEL_B_5V)):
    k = G5V2(); k.ref = "K%s" % ("1" if s == "A" else "2"); k.value = "G5V-2_DC5"
    RLY[s] = k
    VR_IN_REF = VR_A_IN if s == "A" else VR_B_IN
    VR_IN_REF += k["COM1"]; VR_IN_REF += k["COM2"]
    TONE_BUS += k["NO1"]; TONE_BUS += k["NO2"]
    # NC 接点 (相手 VX) はポートループ後に VXIN が確定してから接続する
    P5V += k["COIL1"]
    n_coil = mknet("RLY_%s_COIL" % s)
    n_coil += k["COIL2"]
    q = SOT23(); q.ref = "Q%s" % ("3" if s == "A" else "4"); q.value = "2N7002"
    sel5v += q["G"]
    GND += q["S"]
    n_coil += q["D"]
    between(R("100K"), sel5v, GND)          # ゲートプルダウン
    d_fl = DIO(); d_fl.ref = {"A": "U45", "B": "U49"}[s]; d_fl.value = "1N4007"  # コイル還流ダイオード
    P5V += d_fl["K"]; n_coil += d_fl["A"]
between(C("100nF"), P5V, GND)   # リレー駆動部デカップリング

# ===========================================================================
# PD 引き下げ (Q2)
# ===========================================================================
q2 = SOT23(); q2.ref = "Q2"; q2.value = "2N7002"
PD_EN += q2["G"]
GND += q2["S"]
PD_BUS += q2["D"]
between(R("100K"), PD_EN, GND)

# ===========================================================================
# ポート x2 (A / B)
# ===========================================================================
FR_5V = {"A": FR_A_5V, "B": FR_B_5V}
RM_5V = {"A": RM_A_5V, "B": RM_B_5V}
SHK_33 = {"A": SHK_A_33, "B": SHK_B_33}
MON = {"A": MON_A, "B": MON_B}
VR_IN = {"A": VR_A_IN, "B": VR_B_IN}
VXIN = {}   # リレー入力ノード (ポート毎)
PN = {}     # ポート毎ネット (TP 割当用)

for s in ("A", "B"):
    TIP = mknet("TIP_%s" % s); RING = mknet("RING_%s" % s)
    SHKRAW = mknet("SHK_%s_RAW" % s)
    P5VP = mknet("+5V_P%s" % s)
    PDX = mknet("PD_%s" % s)
    BRP = mknet("BRP_%s" % s); BRM = mknet("BRM_%s" % s)
    VXAUD = mknet("VX_%s_AUD" % s)
    VXIN[s] = mknet("VX_%s_IN" % s)
    TAPN = mknet("TAP_%s_N" % s)

    mod = KS0835F(); mod.ref = "MOD_%s" % s; mod.value = "KS0835F"
    RING += mod["RING"]; TIP += mod["TIP"]
    FR_5V[s] += mod["FR"]; RM_5V[s] += mod["RM"]
    SHKRAW += mod["SHK"]
    GND += mod["GND"]; P5VP += mod["VDC"]; PDX += mod["PD"]
    mod["NC"] += NC

    rj = RJ11(); rj.ref = "J_%s" % ("3" if s == "A" else "4"); rj.value = "RJ11_6P6C"
    RING += rj[3]; TIP += rj[4]
    for n in (1, 2, 5, 6):
        rj[n] += NC

    # --- 保護回路 (KS0835F Typical Connection Diagram / Ag1171 Fig.4) ---
    d_thy = DIO(); d_thy.ref = {"A": "U55", "B": "U82"}[s]; d_thy.value = "P3100SC"; d_thy.footprint = FP_SMC
    TIP += d_thy["A"]; RING += d_thy["K"]     # 双方向サイリスタ (極性不問)
    d_b1 = DIO(); d_b1.ref = {"A": "U56", "B": "U83"}[s]; d_b1.value = "1N4007"; TIP += d_b1["A"]; BRP += d_b1["K"]
    d_b2 = DIO(); d_b2.ref = {"A": "U57", "B": "U84"}[s]; d_b2.value = "1N4007"; RING += d_b2["A"]; BRP += d_b2["K"]
    d_b3 = DIO(); d_b3.ref = {"A": "U58", "B": "U85"}[s]; d_b3.value = "1N4007"; BRM += d_b3["A"]; TIP += d_b3["K"]
    d_b4 = DIO(); d_b4.ref = {"A": "U59", "B": "U86"}[s]; d_b4.value = "1N4007"; BRM += d_b4["A"]; RING += d_b4["K"]
    d_z = DIO(); d_z.ref = {"A": "U60", "B": "U87"}[s]; d_z.value = "BZT03C82"; BRP += d_z["K"]; BRM += d_z["A"]
    between(R("27K"), TIP, RING)                       # CLI バイアス
    c_e1 = C("10nF"); c_e1.footprint = FP_C1206
    between(c_e1, TIP, GND)                            # EMI (要 250V 品)
    c_e2 = C("10nF"); c_e2.footprint = FP_C1206
    between(c_e2, RING, GND)

    # --- 電源 (ポート個別) ---
    fb = BEAD(); fb.ref = {"A": "U64", "B": "U91"}[s]; fb.value = "BK2125HS601-T"   # 600ohm@100MHz, 2012 ランド互換 (BLM21AG601SN1D でも可)
    P5V += fb[1]; P5VP += fb[2]
    between(CE("470uF/10V"), P5VP, GND)
    between(C("100nF"), P5VP, GND)

    # --- SHK 分圧 ---
    between(R("10K"), SHKRAW, SHK_33[s])
    between(R("18K"), SHK_33[s], GND)
    between(C("1nF"), SHK_33[s], GND)

    # --- 音声: VX (モジュール -> 基板) ---
    vx_pin_net = mknet("VX_%s_PIN" % s)
    vx_pin_net += mod["VX"]
    between(C("100nF"), vx_pin_net, VXAUD)
    between(R("100K"), VXAUD, VAUD)
    between(R("0R"), VXAUD, VXIN[s])                   # レベル調整用パッド

    # --- 音声: ADC タップ ---
    between(C("100nF"), VXAUD, TAPN)
    between(R("100K"), TAPN, VREF165)
    between(R("10K"), TAPN, MON[s])
    between(C("1nF"), MON[s], GND)

    # --- 音声: VR (基板 -> モジュール) ---
    vr_pin_net = mknet("VR_%s_PIN" % s)
    vr_pin_net += mod["VR"]
    between(C("100nF"), VR_IN[s], vr_pin_net)
    between(R("100K"), VR_IN[s], VAUD)

    # --- PD (ダイオード経由でのみ引き下げ) ---
    # PD 引き下げダイオード: v3.4 で 1N5819 (ショットキー) に変更。
    # 1N4007 では PD ピンの Low が約 0.67V となり Ag1171 の VIL(max) 0.5V を
    # 超えるため (第7ラウンド監査)。1N5819 の Vf 約 0.3V なら規格内。
    d_pd = DIO(); d_pd.ref = {"A": "U79", "B": "U106"}[s]; d_pd.value = "1N5819"
    PDX += d_pd["A"]; PD_BUS += d_pd["K"]

    PN[s] = {"TIP": TIP, "RING": RING, "SHKRAW": SHKRAW, "PDX": PDX,
             "VXAUD": VXAUD, "VXPIN": vx_pin_net, "VRPIN": vr_pin_net,
             "P5VP": P5VP}

# リレー NC 接点 = 相手 VX (クロス接続)
VXIN["B"] += RLY["A"]["NC1"]; VXIN["B"] += RLY["A"]["NC2"]
VXIN["A"] += RLY["B"]["NC1"]; VXIN["A"] += RLY["B"]["NC2"]

# ESP32 リセット/書き込み中も HCT 入力を確定させる。特に RM の浮遊を防止。
for control in (FR_A_33, RM_A_33, SEL_A_33, TONE33,
                FR_B_33, RM_B_33, SEL_B_33):
    between(R("100K"), control, GND)

# ===========================================================================
# テストポイント増設 (TP4-TP34、既存 TP1=+5V / TP2=GND / TP3=TONE_BUS)
# デバッグ優先で主要信号を一通り引き出す。TIP/RING は回線高電圧
# (リング時 最大約135Vp-p) が現れるため、基板シルクに高電圧注意を入れること。
# ===========================================================================
TP_LIST = [
    (PN["A"]["TIP"],    "TIP_A"),     (PN["A"]["RING"],   "RING_A"),
    (FR_5V["A"],        "FR_A_5V"),   (RM_5V["A"],        "RM_A_5V"),
    (PN["A"]["SHKRAW"], "SHK_A_RAW"), (PN["A"]["VXPIN"],  "VX_A_PIN"),
    (PN["A"]["VRPIN"],  "VR_A_PIN"),  (PN["A"]["VXAUD"],  "VX_A_AUD"),
    (PN["B"]["TIP"],    "TIP_B"),     (PN["B"]["RING"],   "RING_B"),
    (FR_5V["B"],        "FR_B_5V"),   (RM_5V["B"],        "RM_B_5V"),
    (PN["B"]["SHKRAW"], "SHK_B_RAW"), (PN["B"]["VXPIN"],  "VX_B_PIN"),
    (PN["B"]["VRPIN"],  "VR_B_PIN"),  (PN["B"]["VXAUD"],  "VX_B_AUD"),
    (VIN_RAW,           "VIN_RAW"),   (VIN_F,             "VIN_F"),
    (VAUD,              "VAUD"),      (VREF165,           "VREF165"),
    (GND,               "GND"),
    (TONE_5V,           "TONE_5V"),   (TONE_AC,           "TONE_AC"),
    (SEL_A_5V,          "SEL_A_5V"),  (SEL_B_5V,          "SEL_B_5V"),
    (MON["A"],          "MON_A"),     (MON["B"],          "MON_B"),
    (PN["A"]["PDX"],    "PD_A"),      (PN["B"]["PDX"],    "PD_B"),
    (VR_IN["A"],        "VR_A_IN"),   (VR_IN["B"],        "VR_B_IN"),
]
for _i, (_net, _label) in enumerate(TP_LIST):
    _tp = TP(); _tp.ref = "TP%d" % (_i + 4)
    _net += _tp[1]

# ===========================================================================
# 動作チェック用ステータス LED (D4-D9: ポート毎に HOOK / RING / LINK)
# ファームウェア変更不要のハードウェア連動表示。既存の D2 (電源) /
# D3 (GPIO4 ステータス) とは役割が別で、通電したまま各ポートの状態を
# 目視確認するためのもの。シルクに HOOK_x / RING_x / LINK_x の
# 役割ラベルを付ける (基板生成スクリプト側で配置)。
#
# HOOK (緑): オフフック表示。SHK は Ag1171 の仕様で 100uA max 出力
#   (3.3K 内蔵プルアップから供給) しかなく LED を直接駆動できない
#   ため、2N7002 (Q5/Q6) でバッファする。ゲート = SHK_x_RAW で、
#   既存の SHK 分圧 (10K/18K) が DC 経路を兼ねるためゲートは浮かない。
#   点灯経路: +5V_Px -> R_LED -> LED -> FET -> GND (SHK=H で点灯)。
# RING (黄): リンギング表示。RM_x_5V は 74HCT244 の出力 (IOH/IOL
#   ±6mA 定格) なので、抵抗経由で直接駆動する (約2mA)。
# LINK (青): リレー励磁表示。SEL_x_5V (コイル駆動ライン) から直接
#   駆動する。SEL=H で点灯 = リレー励磁中 (トーンバス選択中)。
#   通話中のクロス接続は SEL=L (無励磁) なので、その間は消灯する。
# LED 電流はいずれも約2mA (0805 高効率品想定)。
# ===========================================================================
SEL_5V = {"A": SEL_A_5V, "B": SEL_B_5V}

def _status_led_hook(s, dref, rref, qref):
    global GND
    n_top = Net("LED_HK_%s" % s)
    n_sw = Net("HK_%s_DRV" % s)
    r = R("1.5K", ref=rref)
    PN[s]["P5VP"] += r[1]; n_top += r[2]
    d = LED(); d.ref = dref; d.value = "LED_GRN"
    n_top += d["A"]; n_sw += d["K"]
    q = SOT23(); q.ref = qref; q.value = "2N7002"
    PN[s]["SHKRAW"] += q["G"]; GND += q["S"]; n_sw += q["D"]

def _status_led_direct(sig, s, role, dref, dval, rref, rval):
    global GND
    n_top = Net("LED_%s_%s" % (role, s))
    r = R(rval, ref=rref)
    sig += r[1]; n_top += r[2]
    d = LED(); d.ref = dref; d.value = dval
    n_top += d["A"]; GND += d["K"]

_status_led_hook("A", "D4", "R_LED3", "Q5")
_status_led_direct(RM_5V["A"], "A", "RG", "D5", "LED_YEL", "R_LED4", "1.5K")
_status_led_direct(SEL_5V["A"], "A", "LK", "D6", "LED_BLU", "R_LED5", "1K")
_status_led_hook("B", "D7", "R_LED6", "Q6")
_status_led_direct(RM_5V["B"], "B", "RG", "D8", "LED_YEL", "R_LED7", "1.5K")
_status_led_direct(SEL_5V["B"], "B", "LK", "D9", "LED_BLU", "R_LED8", "1K")

# ===========================================================================
# ERC + ネットリスト
# ===========================================================================
ERC()
generate_netlist(file_="m5stamp_slic2port.net", tool=KICAD)
print("netlist written: m5stamp_slic2port.net")
