/*
 * m5stamp_fxs_exchange.ino
 * ---------------------------------------------------------------------------
 * M5StampS3 (ESP32-S3) 制御 2ポート疑似交換機 ファームウェア雛形
 *
 * 対象基板: SLIC2PORT-FXS (KS0835F x2 + 74HCT244 + G5V-2 リレー)
 * 設計書:   ../DESIGN.md (GPIO 割り当ては DESIGN.md 6.2 と一致)
 *
 * 動作:
 *   - 片ポートがオフフック -> ダイヤルトーン送出 + DTMF 受付
 *   - 相手ポートをリング (20Hz, 1秒ON/2秒OFF) + 発信側へ呼出音
 *   - 相手応答 (リングトリップ) -> 音声クロス接続 (リレーで SEL 切替)
 *   - どちらかがオンフック -> 解放
 *
 * 注意:
 *   - 本スケッチは雛形であり、実機での調整 (DTMF しきい値、リングトリップ
 *     判定時間、トーンレベル) が必要。
 *   - Arduino core for ESP32 は 3.x 系 API (ledcAttach) を使用。
 *     2.x 系では ledcSetup/ledcAttachPin に読み替えること。
 * ---------------------------------------------------------------------------
 */

#include <Arduino.h>
#include <math.h>

// ledcAttach / ledcWrite(pin) は Arduino-ESP32 3.x。core 2.x (platform-espressif32 7.0.1 等) では未宣言。
#if !defined(ESP_ARDUINO_VERSION_MAJOR) || ESP_ARDUINO_VERSION_MAJOR < 3
#error "Arduino-ESP32 3.x required (ledcAttach). Use platform = espressif32@8.0.0"
#endif

// ===========================================================================
// GPIO 定義 (DESIGN.md 6.2)
// ===========================================================================
static const int PIN_MON_A   = 1;   // ADC1_CH0 : ポートA 音声モニタ/DTMF
static const int PIN_MON_B   = 2;   // ADC1_CH1 : ポートB 音声モニタ/DTMF
static const int PIN_LED_ST  = 4;   // ステータス LED
static const int PIN_TONE    = 6;   // LEDC PWM 400Hz -> トーンバス
static const int PIN_SHK_A   = 7;   // ポートA フック検出 (分圧済 3.3V系)
static const int PIN_RM_A    = 8;   // ポートA リングモード   -> HCT244
static const int PIN_FR_A    = 9;   // ポートA 極性/リング    -> HCT244
static const int PIN_SHK_B   = 10;  // ポートB フック検出
static const int PIN_RM_B    = 11;  // ポートB リングモード   -> HCT244
static const int PIN_FR_B    = 12;  // ポートB 極性/リング    -> HCT244
static const int PIN_SEL_A   = 13;  // ポートA 音声選択 (L=相手VX, H=トーン)
static const int PIN_SEL_B   = 14;  // ポートB 音声選択
static const int PIN_PD_EN   = 15;  // SLIC PD 引き下げ (2N7002 ゲート, 既定 OFF)

// ===========================================================================
// チューニング定数
// ===========================================================================
static const uint32_t HOOK_DEBOUNCE_MS   = 15;    // SHK デバウンス (DS: 10ms)
static const uint32_t RELEASE_HOOK_MS    = 500;   // 通話中オンフック確定
static const uint32_t RING_FREQ_HZ       = 20;    // リング周波数 (SLIC 制約 20-25Hz)
static const uint32_t RING_ON_MS         = 1000;  // 日本パターン 1秒ON
static const uint32_t RING_OFF_MS        = 2000;  //           2秒OFF
static const uint32_t RING_TRIP_MS       = 10;    // リング中 SHK 継続で応答判定
// Ag1171 §3.3: F/R=H 固定後 >10ms 待ってから RM=L。
static const uint32_t RING_SETTLE_MS     = 15;
static const uint32_t RING_TIMEOUT_MS    = 45000; // 無応答タイムアウト
static const uint32_t DIAL_NODIGIT_MS    = 6000;  // 数字なしで発信扱いにする時間
static const uint32_t DIAL_INTERDIGIT_MS = 2500;  // 最後の数字からの確定待ち
static const uint32_t BUSY_TONE_MS       = 5000;  // 話中音の最大送出時間
static const uint32_t TONE_FREQ_HZ       = 400;   // DT/RBT/BT 共通

// ===========================================================================
// ポート管理
// ===========================================================================
struct Port {
  const char *name;
  int shkPin, rmPin, frPin, selPin, adcPin;
  bool rawHook;          // SHK 生値 (H=オフフック)
  bool hook;             // デバウンス済フック状態
  uint32_t rawChangedAt; // 生値が最後に変化した時刻
  uint32_t hookSince;    // hook 状態が継続している開始時刻
};

static Port ports[2] = {
  { "A", PIN_SHK_A, PIN_RM_A, PIN_FR_A, PIN_SEL_A, PIN_MON_A, false, false, 0, 0 },
  { "B", PIN_SHK_B, PIN_RM_B, PIN_FR_B, PIN_SEL_B, PIN_MON_B, false, false, 0, 0 },
};

// SHK を読んでデバウンス済 hook を更新する
static void updateHook(Port &p, uint32_t now) {
  bool raw = (digitalRead(p.shkPin) == HIGH);
  if (raw != p.rawHook) { p.rawHook = raw; p.rawChangedAt = now; }
  if (p.hook != p.rawHook && (now - p.rawChangedAt) >= HOOK_DEBOUNCE_MS) {
    p.hook = p.rawHook;
    p.hookSince = now;
    Serial.printf("[HOOK] port %s -> %s\n", p.name, p.hook ? "OFF-HOOK" : "ON-HOOK");
  }
}

static void setFR(Port &p, bool high) { digitalWrite(p.frPin, high ? HIGH : LOW); }
static void setRM(Port &p, bool high) { digitalWrite(p.rmPin, high ? HIGH : LOW); }
static void setSelTone(Port &p, bool tone) { digitalWrite(p.selPin, tone ? HIGH : LOW); }

// ===========================================================================
// トーン生成 (LEDC 400Hz 矩形波 -> 基板上の RC フィルタで正弦波化)
// ===========================================================================
static bool toneOut = false;
static void toneSet(bool on) {
  if (on == toneOut) return;
  toneOut = on;
  ledcWrite(PIN_TONE, on ? 128 : 0);   // core 3.x: チャネルではなくピン指定
}

// ===========================================================================
// リングエンジン (被呼ポートに対して RM/FR を駆動)
// ===========================================================================
struct RingEngine {
  bool active = false;
  int callee = -1;
  uint32_t startedAt = 0;
  bool phaseOn = false;   // 現在バースト中か (呼出音同期用)
  bool rmHigh = false;
  bool frLevel = true;
  uint32_t lastToggle = 0;

  void start(int calleeIdx, uint32_t now) {
    active = true; callee = calleeIdx; startedAt = now;
    phaseOn = false; frLevel = true; lastToggle = now;
  }
  // 停止時のみ最大15msの待機。DTMFサンプリングはリング中には実行しない。
  void stopBurst() {
    if (callee < 0) return;
    setFR(ports[callee], true);
    frLevel = true;
    if (rmHigh) {
      delay(RING_SETTLE_MS);
      setRM(ports[callee], false);
      rmHigh = false;
    }
  }
  void stop() {
    stopBurst();
    active = false; callee = -1; phaseOn = false;
  }
  // 毎ループ呼ぶ。戻り値: 現在のバースト ON 相かどうか
  bool update(uint32_t now) {
    if (!active) return false;
    uint32_t ph = (now - startedAt) % (RING_ON_MS + RING_OFF_MS);
    bool on = (ph < RING_ON_MS);
    Port &p = ports[callee];
    if (on) {
      if (!phaseOn) { lastToggle = now; frLevel = true; setFR(p, true); }
      setRM(p, true);
      rmHigh = true;
      if (now - lastToggle >= (1000 / (RING_FREQ_HZ * 2))) {
        frLevel = !frLevel;
        setFR(p, frLevel);
        lastToggle = now;
      }
    } else {
      stopBurst();
    }
    phaseOn = on;
    return on;
  }
};
static RingEngine ring;

// ===========================================================================
// DTMF 受信 (Goertzel, 発信側ポートの MON を 8kHz サンプリング)
// ===========================================================================
// 対応する DTMF (tests/dtmf_window_test.cpp で窓位置を総当たり):
//   最短音長 70ms、数字間隔 40ms 以上、各成分の正規化振幅 0.20 以上、無雑音、8kHz。
//   205 サンプル窓 (25.6ms) を連続 2 窓一致で確定する。40ms 音は窓位置によって
//   確定しない。40ms 対応は製品要件ではない (調査の結論)。
static const int   DTMF_FS   = 8000;
static const int   DTMF_N    = 205;                 // 約 25.6ms 窓
static const float DTMF_ROW[4] = { 697, 770, 852, 941 };
static const float DTMF_COL[4] = { 1209, 1336, 1477, 1633 };
static const char  DTMF_MAP[4][4] = {
  { '1', '2', '3', 'A' },
  { '4', '5', '6', 'B' },
  { '7', '8', '9', 'C' },
  { '*', '0', '#', 'D' },
};
// しきい値 (要実機調整): 正規化振幅 (0..1 目安) に対する下限
static const float DTMF_MAG_MIN = 0.12f;

static float goertzel(const uint16_t *x, int n, float freq) {
  float k = roundf((float)n * freq / (float)DTMF_FS);
  float w = 2.0f * PI * k / (float)n;
  float cw = cosf(w), coeff = 2.0f * cw;
  float q0 = 0, q1 = 0, q2 = 0;
  for (int i = 0; i < n; i++) {
    q0 = coeff * q1 - q2 + ((float)x[i] - 2048.0f) / 2048.0f;
    q2 = q1; q1 = q0;
  }
  float power = q1 * q1 + q2 * q2 - coeff * q1 * q2;
  return sqrtf(fmaxf(power, 0.0f)) / ((float)n / 2.0f);
}

// 1 窓分サンプリングして DTMF 数字を判定。無ければ '\0'
static char dtmfScanOnce(int adcPin) {
  static uint16_t buf[DTMF_N];
  uint32_t nextUs = micros();
  for (int i = 0; i < DTMF_N; i++) {
    buf[i] = (uint16_t)analogRead(adcPin);
    nextUs += 1000000UL / DTMF_FS;
    int32_t wait = (int32_t)(nextUs - micros());
    if (wait > 0) delayMicroseconds((uint32_t)wait);
  }
  float rMag[4], cMag[4];
  int rBest = -1, cBest = -1;
  float rMax = 0, cMax = 0, rSecond = 0, cSecond = 0;
  for (int i = 0; i < 4; i++) {
    rMag[i] = goertzel(buf, DTMF_N, DTMF_ROW[i]);
    cMag[i] = goertzel(buf, DTMF_N, DTMF_COL[i]);
    if (rMag[i] > rMax) { rSecond = rMax; rMax = rMag[i]; rBest = i; }
    else if (rMag[i] > rSecond) { rSecond = rMag[i]; }
    if (cMag[i] > cMax) { cSecond = cMax; cMax = cMag[i]; cBest = i; }
    else if (cMag[i] > cSecond) { cSecond = cMag[i]; }
  }
  if (rMax < DTMF_MAG_MIN || cMax < DTMF_MAG_MIN) return '\0';
  if (rMax < 1.8f * rSecond || cMax < 1.8f * cSecond) return '\0';  // ツイスト/分離
  return DTMF_MAP[rBest][cBest];
}

// 数字の確定管理 (連続2窓で確定、消滅で再アーム)
struct DtmfReceiver {
  char candidate = '\0';
  char armed = '\0';        // 現在「押下中」とみなしている数字
  String digits;
  uint32_t lastDigitAt = 0;
  void reset() { candidate = armed = '\0'; digits = ""; lastDigitAt = 0; }
  void feed(char d, uint32_t now) {
    if (d == '\0') { candidate = '\0'; armed = '\0'; return; }
    if (d == armed) { lastDigitAt = now; return; } // 押下継続
    if (d == candidate) {                      // 2窓連続 -> 確定
      armed = d;
      if (digits.length() < 64) digits += d;
      lastDigitAt = now;
      Serial.printf("[DTMF] digit '%c' (total: %s)\n", d, digits.c_str());
    } else {
      candidate = d;
    }
  }
};
static DtmfReceiver dtmf;

// ===========================================================================
// 交換機 状態機械
// ===========================================================================
enum ExState { EX_IDLE, EX_DIAL, EX_RINGING, EX_CONNECTED, EX_BUSY,
               EX_WAIT_ONHOOK, EX_RING_TEST };
static ExState exState = EX_IDLE;
static int caller = -1;                 // 発信側ポート index (0=A, 1=B)
static uint32_t stateSince = 0;
static uint32_t dialStartedAt = 0;

static void toIdle(uint32_t now) {
  ring.stop();
  toneSet(false);
  for (int i = 0; i < 2; i++) {
    setRM(ports[i], false);
    setFR(ports[i], true);
    setSelTone(ports[i], false);
  }
  caller = -1;
  exState = (!ports[0].hook && !ports[1].hook) ? EX_IDLE : EX_WAIT_ONHOOK;
  stateSince = now;
  dtmf.reset();
  Serial.println(exState == EX_IDLE ? "[EX] -> IDLE" : "[EX] -> WAIT_ONHOOK");
}

static void startDial(int c, uint32_t now) {
  caller = c;
  exState = EX_DIAL;
  stateSince = now;
  dialStartedAt = now;
  dtmf.reset();
  setSelTone(ports[c], true);           // ダイヤルトーンを発信側へ
  toneSet(true);                        // ダイヤルトーン (連続)
  Serial.printf("[EX] -> DIAL (caller=%s)\n", ports[c].name);
}

static void startRinging(uint32_t now) {
  int callee = 1 - caller;
  exState = EX_RINGING;
  stateSince = now;
  toneSet(false);
  ring.start(callee, now);
  Serial.printf("[EX] -> RINGING (callee=%s)\n", ports[callee].name);
}

static void startConnected(uint32_t now) {
  ring.stop();
  toneSet(false);
  setSelTone(ports[0], false);          // 両ポートとも相手 VX へ (クロス接続)
  setSelTone(ports[1], false);
  exState = EX_CONNECTED;
  stateSince = now;
  Serial.println("[EX] -> CONNECTED");
}

static void exchangeUpdate(uint32_t now) {
  Port &A = ports[0], &B = ports[1];
  switch (exState) {
    case EX_IDLE: {
      if (A.hook && B.hook) { caller = 0; startConnected(now); }
      else if (A.hook) startDial(0, now);
      else if (B.hook) startDial(1, now);
      break;
    }
    case EX_DIAL: {
      Port &cp = ports[caller];
      Port &op = ports[1 - caller];
      if (!cp.hook) { toIdle(now); break; }        // 発信側が戻した
      if (op.hook) { startConnected(now); break; } // 相手が既に受話器を上げた
      // DTMF 受付
      char d = dtmfScanOnce(cp.adcPin);
      dtmf.feed(d, now);
      if (dtmf.digits.length() > 0) toneSet(false);  // 最初の数字で DT 停止
      if (dtmf.digits.length() > 0 && (now - dtmf.lastDigitAt) >= DIAL_INTERDIGIT_MS) {
        startRinging(now);
      } else if (dtmf.digits.length() == 0 && (now - dialStartedAt) >= DIAL_NODIGIT_MS) {
        startRinging(now);                          // 数字なし発信 (手動FAX送信等)
      }
      break;
    }
    case EX_RINGING: {
      Port &cp = ports[caller];
      Port &op = ports[1 - caller];
      if (!cp.hook) { toIdle(now); break; }         // 発信側キャンセル
      // リングトリップ判定: 被呼側 SHK の生値が継続したら応答
      if (op.rawHook && (now - op.rawChangedAt) >= RING_TRIP_MS) {
        op.hook = true; op.hookSince = now;         // フック状態を確定させる
        startConnected(now);
        break;
      }
      bool burst = ring.update(now);
      toneSet(burst);                               // 呼出音をリングに同期
      if ((now - stateSince) >= RING_TIMEOUT_MS) {  // 無応答
        ring.stop();
        exState = EX_BUSY;
        stateSince = now;
        Serial.println("[EX] -> BUSY (no answer)");
      }
      break;
    }
    case EX_CONNECTED: {
      // どちらかがオンフック (hook=false に遷移) して RELEASE_HOOK_MS
      // 経過したら解放する。接続時は両ポートがオフフック済み。
      for (int i = 0; i < 2; i++) {
        if (!ports[i].hook &&
            (now - ports[i].hookSince) >= RELEASE_HOOK_MS) {
          toIdle(now);
          break;
        }
      }
      break;
    }
    case EX_WAIT_ONHOOK: {
      // 残ったオフフックを新規発信として扱わず、両端が戻るのを待つ。
      if (!A.hook && !B.hook) { exState = EX_IDLE; stateSince = now; }
      break;
    }
    case EX_RING_TEST: {
      if (ring.callee < 0) { toIdle(now); break; }
      Port &target = ports[ring.callee];
      // raw の 10ms 確定は hook デバウンス (15ms) より早い。hook を立てずに
      // IDLE へ戻すと、次ループでオフフックを新規発信と誤認する。
      if (target.rawHook && (now - target.rawChangedAt) >= RING_TRIP_MS) {
        target.hook = true;
        target.hookSince = now;
        toIdle(now);
        break;
      }
      if ((now - stateSince) >= RING_TIMEOUT_MS) { toIdle(now); break; }
      ring.update(now);
      break;
    }
    case EX_BUSY: {
      Port &cp = ports[caller];
      // 話中音: 0.25s ON / 0.25s OFF
      toneSet(((now / 250) % 2) == 0);
      if (!cp.hook || (now - stateSince) >= BUSY_TONE_MS) toIdle(now);
      break;
    }
  }
}

// ===========================================================================
// リング単体テスト (シリアルコマンド用)
// ===========================================================================
static void ringTest(int idx, uint32_t now) {
  if (exState != EX_IDLE) { Serial.println("[TEST] busy"); return; }
  if (ports[0].rawHook || ports[1].rawHook) {
    Serial.println("[TEST] both ports must be on-hook"); return;
  }
  exState = EX_RING_TEST;
  stateSince = now;
  ring.start(idx, now);
  Serial.printf("[TEST] ringing port %s (off-hook target, send r, or wait 45s)\n",
                ports[idx].name);
}

// ===========================================================================
// setup / loop
// ===========================================================================
void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println("\nSLIC2PORT-FXS exchange fw v0.1");

  for (int i = 0; i < 2; i++) {
    pinMode(ports[i].shkPin, INPUT);
    // Arduino-ESP32 3.x は pinMode 前の digitalWrite を無視する。
    // 起動からここまでの Hi-Z の間は、基板側のプルダウンが HCT 入力を安全側 (L) に固定する。
    // pinMode(OUTPUT) はいったん Low になるので、RM を先に出力 (Low) にしてから F/R を High にする。
    // RM=Low のままなら F/R が極短時間 Reverse でもリング電圧は出ない。(PR #2 から取り込み)
    pinMode(ports[i].rmPin, OUTPUT);
    setRM(ports[i], false);
    pinMode(ports[i].frPin, OUTPUT);
    setFR(ports[i], true);              // Forward (通常極性)
    pinMode(ports[i].selPin, OUTPUT);
    setSelTone(ports[i], false);
    analogSetPinAttenuation(ports[i].adcPin, ADC_11db);
  }
  pinMode(PIN_LED_ST, OUTPUT);
  digitalWrite(PIN_LED_ST, LOW);
  pinMode(PIN_PD_EN, OUTPUT);
  digitalWrite(PIN_PD_EN, LOW);         // 2N7002 OFF = PD 無効 (モジュール常時ON)

  // トーン PWM (ESP32 Arduino core 3.x API)
  ledcAttach(PIN_TONE, TONE_FREQ_HZ, 8);
  ledcWrite(PIN_TONE, 0);
  analogReadResolution(12);

  uint32_t now = millis();
  toIdle(now);
}

void loop() {
  uint32_t now = millis();
  updateHook(ports[0], now);
  updateHook(ports[1], now);
  exchangeUpdate(now);

  // ステータス LED: 接続中=点灯, 呼出中=点滅, 待機=消灯
  if (exState == EX_CONNECTED) digitalWrite(PIN_LED_ST, HIGH);
  else if (exState == EX_RINGING || exState == EX_RING_TEST) digitalWrite(PIN_LED_ST, (now / 300) % 2);
  else digitalWrite(PIN_LED_ST, LOW);

  // シリアルコマンド (デバッグ)
  if (Serial.available()) {
    char c = (char)Serial.read();
    if (c == 'a') ringTest(0, now);
    else if (c == 'b') ringTest(1, now);
    else if (c == 's') {
      Serial.printf("[STAT] state=%d A.hook=%d B.hook=%d digits=%s\n",
                    (int)exState, ports[0].hook, ports[1].hook, dtmf.digits.c_str());
    } else if (c == 'r') {
      toIdle(now);
    }
  }
  delay(2); // 呼出中のSHKポーリング。停止シーケンス中のみ15ms待機。
}
