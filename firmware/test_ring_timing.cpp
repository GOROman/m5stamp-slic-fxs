// Host-side check of the ring cadence the sketch drives.
// Build: g++ -std=c++17 -Wall -Wextra -o /tmp/test_ring_timing test_ring_timing.cpp
#include "ring_timing.h"

#include <stdio.h>

static int fails = 0;

#define CHECK(cond)                                                            \
  do {                                                                         \
    if (!(cond)) {                                                             \
      printf("FAIL %s (%s:%d)\n", #cond, __FILE__, __LINE__);                  \
      fails++;                                                                 \
    }                                                                          \
  } while (0)

int main() {
  CHECK(RING_HALF_MS == 25);
  CHECK(ringPhase(0) == RING_PHASE_TOGGLE);
  CHECK(ringPhase(979) == RING_PHASE_TOGGLE);
  CHECK(ringPhase(980) == RING_PHASE_HOLD);
  CHECK(ringPhase(999) == RING_PHASE_HOLD);
  CHECK(ringPhase(1000) == RING_PHASE_OFF);
  CHECK(ringPhase(2999) == RING_PHASE_OFF);
  CHECK(ringPhase(3000) == RING_PHASE_TOGGLE);

  // RM is high only during toggle+hold, which together are exactly RING_ON_MS.
  int rmHigh = 0;
  for (uint32_t t = 0; t < RING_ON_MS + RING_OFF_MS; t++) {
    RingPhase p = ringPhase(t);
    if (p == RING_PHASE_TOGGLE || p == RING_PHASE_HOLD) rmHigh++;
    if (p == RING_PHASE_HOLD || p == RING_PHASE_OFF) {
      // F/R is parked in these phases; the hold is long enough to decay.
    }
  }
  CHECK(rmHigh == (int)RING_ON_MS);
  int hold = 0;
  for (uint32_t t = 0; t < RING_ON_MS; t++) {
    if (ringPhase(t) == RING_PHASE_HOLD) hold++;
  }
  CHECK(hold == (int)RM_HOLD_AFTER_FR_MS);
  CHECK(hold > 10);

  if (fails) {
    printf("%d failed\n", fails);
    return 1;
  }
  printf("ok\n");
  return 0;
}
