// Window-phase sweep of the sketch's Goertzel + two-window DTMF lock.
// Supported contract: 70 ms tone, >=40 ms gap, amplitude 0.20 per component.
// 40 ms is intentionally not required.
#include <cmath>
#include <iostream>

#include "../firmware/m5stamp_fxs_exchange.ino"

static char scanWindow(int start, int duration, float amp) {
  uint16_t b[DTMF_N];
  for (int i = 0; i < DTMF_N; i++) {
    int n = start + i;
    double t = n / double(DTMF_FS);
    double s = 0;
    if (n >= 0 && n < duration)
      s = amp * (std::sin(2 * PI * 697 * t) + std::sin(2 * PI * 1209 * t));
    int sample = 2048 + static_cast<int>(2048 * s);
    if (sample < 0) sample = 0;
    if (sample > 4095) sample = 4095;
    b[i] = static_cast<uint16_t>(sample);
  }
  float rMax = 0, cMax = 0, rSecond = 0, cSecond = 0;
  int rBest = 0, cBest = 0;
  for (int j = 0; j < 4; j++) {
    float r = goertzel(b, DTMF_N, DTMF_ROW[j]);
    float c = goertzel(b, DTMF_N, DTMF_COL[j]);
    if (r > rMax) { rSecond = rMax; rMax = r; rBest = j; }
    else if (r > rSecond) rSecond = r;
    if (c > cMax) { cSecond = cMax; cMax = c; cBest = j; }
    else if (c > cSecond) cSecond = c;
  }
  if (rMax < DTMF_MAG_MIN || cMax < DTMF_MAG_MIN) return '\0';
  if (rMax < 1.8f * rSecond || cMax < 1.8f * cSecond) return '\0';
  return DTMF_MAP[rBest][cBest];
}

static int misses(int ms) {
  int missed = 0;
  const int duration = ms * DTMF_FS / 1000;
  for (int offset = 0; offset < DTMF_N; offset++) {
    dtmf.reset();
    for (int start = -offset; start < duration + 2 * DTMF_N; start += DTMF_N)
      dtmf.feed(scanWindow(start, duration, 0.20f), static_cast<uint32_t>(start + DTMF_N));
    if (dtmf.digits != "1") missed++;
  }
  return missed;
}

int main() {
  const int miss40 = misses(40);
  const int miss70 = misses(70);
  const int miss100 = misses(100);
  std::cout << "40ms missed " << miss40 << "/" << DTMF_N
            << "  70ms missed " << miss70 << "  100ms missed " << miss100 << "\n";
  if (miss70 != 0 || miss100 != 0) return 1;
  if (miss40 == 0) {
    std::cout << "40ms unexpectedly reliable; revisit the documented minimum\n";
    return 1;
  }
  std::cout << "dtmf window contract passed\n";
  return 0;
}
