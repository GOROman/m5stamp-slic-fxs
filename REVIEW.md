# v0.1 レビュー（2026-10-31）

対象: 初期コミット `fb54b23`。設計途中の回路・フットプリント・ファームウェアを照合した。以下の修正は発注可能・動作保証を意味しない。

| 優先度 | 問題 | 修正 |
|---|---|---|
| P1 | USB-Cの論理ピン1〜12と、指定フットプリントのA1/A4/A5/B5/S1等が不一致。VBUS/GND/CCが実パッドへ正しく割り当たらない | J1を公式フットプリントのパッド番号へ変更。両面VBUS/GND、各CCの5.1K、シールドを接続 |
| P1 | DIO/LED定義が1=A/2=Kだが、指定KiCadフットプリントは1=K/2=A。入力TVSやブリッジ等が逆向きになる | テンプレートを1=K/2=Aへ修正しネットリストを再生成 |
| P1 | Q1の入力=S、出力=Dでは逆接時にもボディダイオードが導通する | AO3401AのDを入力、Sを保護後の+5Vへ接続 |
| P1 | HCT244のOEは常時有効なのに、ESP32リセット中の制御入力が浮遊。RMが不定になる | 使用7入力に100Kプルダウンを追加 |
| P1 | RJ11の1.27mmピッチに幅1.6mmのパッドを配置し、隣接パッドの銅箔が0.33mm重なる | パッド幅を1.1mmへ縮小（間隔0.17mm）。穴・ボディは仮寸法なので実部品の選定は別途必要 |
| P1 | リング停止でRM=Lを先に出し、F/R=Hからの待機もない。80ms連続SHK条件はリング中のパルスを取り逃がす | 10msのSHK確認後、F/R=H→15ms待機→RM=L。バースト終了・キャンセル・応答・タイムアウトへ共通適用 |
| P2 | トーンバスの100nFシャントが400Hzを過大に減衰し、RC側へのDC経路で2.5Vバイアスも崩れる | 100nFを直列AC結合へ移動、RCを10K/47nF×2へ変更。片ポート時の線形計算は約0.22Vrms、実測調整は未実施 |
| P2 | SEL_Zのジャンパ先が2.5Vバイアス。5V動作CD4053BのH入力として保証されない | ジャンパ先を+5Vへ変更 |
| P2 | 片側切断後、残ったオフフックを新規発信として再呼出し。無応答後も同じループになる | 両端オンフックまで待つ状態を追加 |
| P2 | 単体リング試験が通常発信の「発信側オンフックでキャンセル」により即停止 | 独立したリング試験状態を追加 |
| P2 | 時刻を直接大小比較しておりmillis()周回付近で切断等が失敗する | 経過時間の符号なし差分を使用。DTMF保持中のタイマー更新と記録長制限も追加 |

## 検証

```bash
python -m pip install -r tests/requirements.txt
python -m unittest discover -s tests -v
g++ -std=c++17 -Wall -Wextra -Werror -Itests tests/exchange_test.cpp -o /tmp/exchange-test
/tmp/exchange-test
```

- Python 7テスト: ソースを一時ディレクトリで再実行し、生成ネットと同梱ネットの接続・値・フットプリントを比較。USB実パッド、極性、FET、プルダウン、トーン結合、BOM整合、RJ11クリアランスを検査。
- C++ホストテスト: 実際の`.ino`をArduinoスタブ上でコンパイル・実行。双方向の発信、SHK応答と停止順、バースト間隔、単体試験、無応答、片側切断、再発呼防止、millis()周回、DTMF保持・記録上限を検査。
- SKiDL 1.2.1の簡易ERCはエラー/警告0件。ただし全ピンPASSIVE定義なので、電圧・駆動競合・極性の保証には使えない。KiCad標準ライブラリ未インストールの環境警告は別途出る。
- GitHub Actionsに上記の回帰検査を追加。

ネットリスト/BOMの再生成:

```bash
(cd kicad/skidl && python m5stamp_slic2port.py)
python kicad/skidl/export_bom.py
python kicad/gen_footprints.py
```

## 残る確認事項

- ESP32-S3実ターゲットのArduino core 3.xビルド・書き込み、ADCサンプリング周期、DTMFしきい値、リングトリップ波形、トーンレベル、FAX T.30通信は未検証。ホストテストは実機タイミングやアナログ特性を保証しない。
- リング停止時の15ms待機は意図した同期処理。通常の呼出しループは2ms待機、発信受付中のDTMF取得は約26msのブロッキング窓。
- KS0835F/RJ11の実寸、購入する各部品とフットプリントの一致、Stamp-S3の追加パッド29〜31、配置配線・DRCは引き続き未確認。基板・ガーバーは未作成。
- SMBJ5.0Aは7V絶対最大を守る過電圧遮断器ではない。誤った電源や持続過電圧も許容する要件なら別途保護回路を設計する。
- USB-CはCCのRdのみ。電源の供給可能電流を判定する実装はないため、指定の5V電源で電源バジェットを満たすことを確認する。

## 照合資料

- [Silvertel Ag1171データシート §3.3、Figure 3](https://www.silvertel.com/images/datasheets/Ag1171-datasheet-Low-cost-ringing-SLIC-with-single-supply.pdf): SHK persistenceとF/R→RM停止順。保存済み`research/Ag1171-datasheet.txt`とも照合。
- [KiCad公式 USB-Cフットプリント](https://github.com/KiCad/kicad-footprints/blob/master/Connector_USB.pretty/USB_C_Receptacle_HRO_TYPE-C-31-M-12.kicad_mod): J1の実パッド番号。
- [KiCad公式 DO-41フットプリント](https://github.com/KiCad/kicad-footprints/blob/master/Diode_THT.pretty/D_DO-41_SOD81_P10.16mm_Horizontal.kicad_mod)、[SMB](https://github.com/KiCad/kicad-footprints/blob/master/Diode_SMD.pretty/D_SMB.kicad_mod)、[LED 0805](https://github.com/KiCad/kicad-footprints/blob/master/LED_SMD.pretty/LED_0805_2012Metric.kicad_mod): カソードのパッド1。
- [AOS AO3401A](https://www.aosmd.com/pdfs/datasheet/AO3401A.pdf): SOT-23ピン配置・P-FETボディダイオード。
- [TI CD4053B](https://www.ti.com/lit/ds/symlink/cd4053b.pdf): 制御入力レベル。
