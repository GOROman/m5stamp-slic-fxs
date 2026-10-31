#include <cassert>
#include <cmath>
#include <iostream>
#include <string>
#include <vector>
#include "../firmware/m5stamp_fxs_exchange.ino"

// Synthesize an ADC sample stream (8kHz, DC center 2048) and run it through
// the real DtmfScanner + DtmfReceiver path used by the firmware.
struct ToneSpec { float rowHz, colHz; int ms; float amp; };
static std::string receive(const std::vector<ToneSpec> &tones, int gapMs,
                           int leadSilenceSamples, float gapAmpUnused = 0) {
  (void)gapAmpUnused;
  dtmf.reset();
  dtmfScanner.reset();
  uint32_t sampleIdx = 0;
  auto pushSilence = [&](int n) {
    for (int i = 0; i < n; i++, sampleIdx++) {
      int d = dtmfScanner.push(2048);
      if (d >= 0) dtmf.feed((char)d, sampleIdx / 8);
    }
  };
  pushSilence(leadSilenceSamples);
  for (size_t t = 0; t < tones.size(); t++) {
    if (t > 0) pushSilence(gapMs * 8);
    int dur = tones[t].ms * 8;
    for (int n = 0; n < dur; n++, sampleIdx++) {
      double tt = n / double(DTMF_FS);
      double v = sin(2 * M_PI * tones[t].rowHz * tt) + sin(2 * M_PI * tones[t].colHz * tt);
      uint16_t s = (uint16_t)(2048 + int(2048 * tones[t].amp * v));
      int d = dtmfScanner.push(s);
      if (d >= 0) dtmf.feed((char)d, sampleIdx / 8);
    }
  }
  pushSilence(800);  // trailing silence: flush the sliding windows
  return dtmf.digits;
}

static void phaseSweep(int ms, float amp) {
  int misses = 0;
  for (int offset = 0; offset < 205; offset++) {
    std::string got = receive({{697, 1209, ms, amp}}, 0, offset);
    if (got != "1") {
      misses++;
      if (misses <= 3)
        std::cout << "  miss: " << ms << "ms amp=" << amp << " offset=" << offset
                  << " got=\"" << got << "\"\n";
    }
  }
  std::cout << ms << "ms digit '1', amplitude " << amp
            << " per component: missed " << misses << "/205 phases\n";
  assert(misses == 0);
}

int main() {
  // Issue #7 harness equivalent, but sample-level end-to-end: 40ms must be 0.
  phaseSweep(40, 0.20f);
  phaseSweep(70, 0.20f);
  phaseSweep(100, 0.20f);
  phaseSweep(40, 0.15f);   // lower level: still phase-independent?

  // All 16 digits at the minimum tone length.
  const float rows[4] = {697, 770, 852, 941};
  const float cols[4] = {1209, 1336, 1477, 1633};
  const char map[4][4] = {{'1','2','3','A'},{'4','5','6','B'},
                          {'7','8','9','C'},{'*','0','#','D'}};
  for (int r = 0; r < 4; r++)
    for (int c = 0; c < 4; c++)
      for (int off : {0, 37, 100, 204}) {
        std::string want(1, map[r][c]);
        std::string got = receive({{rows[r], cols[c], 40, 0.20f}}, 0, off);
        assert(got == want);
      }
  std::cout << "all 16 digits @40ms detected\n";

  // Digit sequences at minimum tone/gap (40ms / 40ms).
  assert(receive({{697,1209,40,0.20f},{697,1336,40,0.20f}}, 40, 10) == "12");
  assert(receive({{770,1209,40,0.20f},{770,1209,40,0.20f}}, 40, 10) == "44");
  std::cout << "40ms/40ms sequences incl. repeated digit ok\n";

  // Negatives: silence and single-frequency tones must not register.
  assert(receive({}, 0, 0).empty());
  assert(receive({{697, 0, 100, 0.20f}}, 0, 0).empty());
  assert(receive({{0, 1209, 100, 0.20f}}, 0, 0).empty());
  // A tone shorter than the 40ms spec (20ms) must not be guaranteed:
  // it may or may not register, but must never produce a *wrong* digit.
  for (int off = 0; off < 205; off += 17) {
    std::string got = receive({{697, 1209, 20, 0.20f}}, 0, off);
    assert(got.empty() || got == "1");
  }
  std::cout << "negative cases ok\n";
  std::cout << "dtmf regression scenarios passed\n";
}
