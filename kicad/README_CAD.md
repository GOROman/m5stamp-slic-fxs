# CAD 成果物について（到達度と使い方）

## 到達度（正直な申告）

| 項目 | 状態 |
|------|------|
| 回路定義（SKiDL ソース） | ✅ 完了。全回路を `skidl/m5stamp_slic2port.py` に定義 |
| ERC | △ SKiDL 簡易 ERC はエラー/警告0件。ただし全ピンPASSIVE定義のため駆動競合・電圧・極性の保証はしない。追加の接続回帰検査は `tests/test_hardware.py` |
| KiCad ネットリスト | ✅ 生成済み `skidl/m5stamp_slic2port.net`（142 部品 / 76 ネット。SKiDL 再生成との位相一致を検証済み） |
| KiCad シンボル | ✅ M5STAMPS3 は M5Stack 公式ライブラリから抽出して同梱。その他の部品シンボルは未作成（回路図エディタで開く形にはなっていない） |
| KiCad フットプリント | △ KS0835F / RJ11 / Stamp-S3-Socket は自作、Stamp-S3-SMD は公式コピーを同梱（寸法実測の出典）。その他は標準ライブラリ名をネットリストに**文字列で指定**した状態（一部は想定名・要実在確認） |
| 回路図（.kicad_sch） | ❌ 未作成 |
| 基板（.kicad_pcb）・配置・配線 | △ 配置まで完了（`SLIC2PORT-FXS.kicad_pcb`、v3.1: 142部品全配置・未配線、120×90mm、U1 ソケット実装。v3.1 でパスコンを IC/モジュール電源ピン近傍へ是正 — C10 のみ U1 ソケット直下の裏面（B.Cu）配置）。生成は `build_pcb_v31.py`（KiCad Python、ネットリスト JSON は `netlist_v3.json`）、検証は `check_v31.py`（パッド↔ネット不一致 0 件、コートヤード重なりは v3 引継ぎの 2 組のみ・層別判定）。配線は EasyEDA に取り込んで仕上げる方針 |
| ガーバー | ❌ 未作成（発注は本タスク範囲外） |

この VM には KiCad 本体が無く、apt 導入も試みたがパッケージ取得が完了しなかったため、上記の「データとしての到達度」に留まる。ネットリストとソースの一致は接続検査で確認し、回路の電気的成立性はデータシート照合と実機で検証する。KiCad 側は下記の手順で取り込んで仕上げる想定。

## 使い方（KiCad 7/8 想定）

1. この `kicad/` フォルダを KiCad プロジェクトとして開く（`SLIC2PORT-FXS.kicad_pro`、fp-lib-table / sym-lib-table 同梱済み）。
2. PCB エディタ → 「ファイル → インポート → ネットリスト」で `skidl/m5stamp_slic2port.net` を読み込む。
   （回路図から起こす場合は、シンボルを割り当て直して同じネット構成にすること。SKiDL ソースが正。）
3. フットプリント割り当ての確認:
   - `SLIC2PORT:KS0835F` / `SLIC2PORT:RJ11_6P6C_TH` / `SLIC2PORT:Stamp-S3-SMD` / `SLIC2PORT:Stamp-S3-Socket` は同梱ライブラリ。
   - U1 は **ソケット実装**（`SLIC2PORT:Stamp-S3-Socket`、1.27mm ピッチ メスヘッダ 17P+11P）。ベアモジュール下面の GND 系パッド **29–31 はソケット構成では未接続**（GND はピン 11/18 で確保）。直接はんだ付けに戻す場合は `Stamp-S3-SMD` を使い、29–31 を GND へ割り当てること。
   - その他の標準ライブラリ名（R_0805 等）は KiCad 標準。**以下の想定名は実在確認が必要**:
     `Fuse:Fuse_1812_4532Metric`、`Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12`、`TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2_1x02_P5.00mm_Horizontal`、`Inductor_SMD:L_0805_2012Metric`（フェライトビーズ代用）、`Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal`（BZT03C82 の SOD-57 代用）。
4. 配置・配線は DESIGN.md §9 のレイアウト指針（高圧クリアランス 1.5mm、アンテナキープアウト、スターグラウンド等）に従う。

## フットプリントの前提（要実物確認）

### KS0835F（`SLIC2PORT.pretty/KS0835F.kicad_mod`）
- 根拠: R-Tone KS0835F データシート V1.3 の Package Size / PCB Decal 図。
- ピン列は単列 11 本・2 クラスタ（1–5 / 6–11）、ピッチ 2.54mm、ドリル 0.9mm、パッド 1.7mm。
- **パラメータ `GAP56`（ピン5–ピン6 中心間）= 20.3mm は図面数値の解釈**。ズレがある場合は `kicad/gen_footprints.py` の定数を直して再実行すればフットプリントを再生成できる。
- 本体外形（シルク）: ピン1 を原点として x = +1.5 〜 −48.7mm、y = −2.0 〜 +4.6mm（Decal の 51.5×6.6mm ストリップ相当）。

### RJ11_6P6C_TH（`SLIC2PORT.pretty/RJ11_6P6C_TH.kicad_mod`）
- 一般的な横型 6P6C ジャックの**想定寸法**（背面単列 1.27mm ピッチ、パッド幅1.1mm（隣接銅箔間0.17mm）、本体約 13.5×13.5mm）。実在部品に合わせて要調整。
- ピン番号は「前面から見て左 = pin1」とした。モジュラージャックは製品により左右が逆になることがあるため、通電前にコードを挿して導通確認すること。なお本用途では中央ペア（pin3/pin4）しか使わず、FAX/モデムの DAA は極性不感が一般的なので、3/4 が入れ替わっても実害は小さい。

### Stamp-S3-Socket（自作、U1 用）
- 根拠: M5Stack 公式 `Stamp-S3-SMD` フットプリントのパッド座標を実測（左列ピン 1–17 / 右列ピン 18–28、ピッチ 1.27mm、列間隔 17.2mm、右列の −y 側 6 位置はアンテナ側で欠け）。
- TH パッドは drill 0.7mm / pad 1.0mm（KiCad の 1.27mm ピンヘッダ標準値）。基板側に 1.27mm メスピンヘッダ（分割可能なソケットレールで可）をはんだ付けし、Stamp 側キャスタレーションに 1.27mm オスピンを付けて差し込む。
- ソケット下（モジュール下面）は配線のみ可・部品配置不可。配置ではコートヤード内を空けている。

### Stamp-S3-SMD（公式コピー）
- 出典: https://github.com/m5stack/M5_Hardware `KiCad/Footprints/M5Stack.pretty/Stamp-S3-SMD.kicad_mod`（2026-10-31 取得、そのまま同梱）。
- シンボル `M5StampS3.kicad_sym` も同リポジトリの `KiCad/Symbols/M5Stack_Symbols.kicad_sym` から M5STAMPS3 のみを抽出したもの。
- Stamp-S3A でも共用できる前提（外形 26.0×18.0mm は S3 と同一）。実物で要確認。

## ファイル一覧

```
kicad/
├─ SLIC2PORT-FXS.kicad_pro     プロジェクト (スケルトン)
├─ SLIC2PORT-FXS.kicad_pcb     配置済み基板 (v3: 142部品・未配線・120x90mm、EasyEDA 仕上げ用)
├─ build_pcb_v2.py             基板生成スクリプト v2 (旧、PR マージ済み 106 部品版)
├─ netlist_v2.json             v2 用ネットリスト JSON
├─ build_pcb_v3.py             基板生成スクリプト v3 (現行、142 部品・120x90mm・ソケット)
├─ netlist_v3.json             skidl/m5stamp_slic2port.net の JSON 変換 (build_pcb_v3.py の入力)
├─ check_v3.py                 v3 基板の独立検証スクリプト
├─ fp-lib-table / sym-lib-table
├─ M5StampS3.kicad_sym         公式シンボル抽出 (M5STAMPS3, 28ピン)
├─ gen_footprints.py           KS0835F / RJ11 フットプリント生成 (要実測時は定数修正)
├─ SLIC2PORT.pretty/
│   ├─ KS0835F.kicad_mod       自作 (要実測確認)
│   ├─ RJ11_6P6C_TH.kicad_mod  自作 (想定寸法)
│   ├─ Stamp-S3-Socket.kicad_mod 自作 (公式フットプリントから実測、U1 ソケット用)
│   └─ Stamp-S3-SMD.kicad_mod  M5Stack 公式コピー
└─ skidl/
    ├─ m5stamp_slic2port.py    回路定義 (正)
    ├─ m5stamp_slic2port.net   生成ネットリスト
    └─ (実行時生成物: .erc / .log / _lib_sklib.py)
```
