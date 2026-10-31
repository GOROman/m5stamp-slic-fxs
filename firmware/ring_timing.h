#pragma once
/*
 * Ring cadence / ring-trip timing shared by the sketch and the host test.
 *
 * Ag1171 / KS0835F constraints (Ag1171 datasheet V1.6 §3.3, notes 7–8):
 *   - Toggle F/R only while RM is high, at 20–25 Hz.
 *   - SHK must be debounced at least 10 ms.
 *   - On ring trip, park F/R high first. Do not take RM low until >10 ms
 *     after that, and do take RM low within 500 ms of the off-hook edge.
 *     Dropping RM while F/R is still low leaves the line transient on the
 *     ringing battery (~75 V).
 *   - The last RM_HOLD_AFTER_FR_MS of each on-burst is that parked tail, so
 *     the 1 s / 2 s cadence does not add extra RM-high time.
 */
#include <stdint.h>

static const uint32_t RING_FREQ_HZ = 20;
static const uint32_t RING_ON_MS = 1000;
static const uint32_t RING_OFF_MS = 2000;
static const uint32_t RM_HOLD_AFTER_FR_MS = 20;  // >10 ms and <<500 ms
static const uint32_t RING_TRIP_MS = 80;         // SHK persistence (min 10 ms)
static const uint32_t RING_HALF_MS = 1000 / (RING_FREQ_HZ * 2);

static_assert(RING_HALF_MS * 2 * RING_FREQ_HZ == 1000, "half-period must be exactly 20 Hz");
static_assert(RM_HOLD_AFTER_FR_MS > 10, "RM must stay high >10 ms after F/R is parked");
static_assert(RM_HOLD_AFTER_FR_MS < 500, "RM must fall within 500 ms");
static_assert(RING_ON_MS > RM_HOLD_AFTER_FR_MS, "park tail must fit inside the on-burst");
static_assert(RING_TRIP_MS >= 10, "SHK debounce minimum");
static_assert(RING_TRIP_MS + RM_HOLD_AFTER_FR_MS < 500,
              "off-hook edge to RM low must be <500 ms");

enum RingPhase {
  RING_PHASE_TOGGLE = 0,  // RM high, F/R toggling
  RING_PHASE_HOLD = 1,    // RM high, F/R parked high
  RING_PHASE_OFF = 2      // RM low, F/R parked high
};

inline RingPhase ringPhase(uint32_t elapsedInCycle) {
  const uint32_t cycle = RING_ON_MS + RING_OFF_MS;
  const uint32_t ph = elapsedInCycle % cycle;
  if (ph < (RING_ON_MS - RM_HOLD_AFTER_FR_MS)) return RING_PHASE_TOGGLE;
  if (ph < RING_ON_MS) return RING_PHASE_HOLD;
  return RING_PHASE_OFF;
}
