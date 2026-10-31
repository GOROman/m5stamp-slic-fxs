#include <cassert>
#include <iostream>
#include "../firmware/m5stamp_fxs_exchange.ino"

static void resetAt(uint32_t at=100) {
  clockUs=uint64_t(at)*1000;
  ring=RingEngine{};
  for (auto &p:ports) {
    p.rawHook=p.hook=false;
    p.rawChangedAt=p.hookSince=at;
    pins[p.shkPin]=LOW;
  }
  toIdle(millis());
  events.clear();
}
static void checkStopOrder(int idx) {
  int fr=-1, rm=-1;
  for (int i=0;i<int(events.size());++i) {
    if (events[i].pin==ports[idx].frPin && events[i].value==HIGH) fr=i;
    if (events[i].pin==ports[idx].rmPin && events[i].value==LOW) { rm=i; break; }
  }
  assert(fr>=0 && rm>fr);
  assert(uint32_t(events[rm].at-events[fr].at)>10);
}
int main() {
  setup();
  for (int c=0;c<2;++c) {
    resetAt();
    ports[c].rawHook=ports[c].hook=true;
    exchangeUpdate(millis());
    assert(exState==EX_DIAL && caller==c && pwmDuty==128);
    delay(DIAL_NODIGIT_MS);
    exchangeUpdate(millis());
    assert(exState==EX_RINGING);
    exchangeUpdate(millis());
    assert(pins[ports[1-c].rmPin]==HIGH && pwmDuty==128);
    // A 10ms SHK pulse must trip ringing; an 80ms requirement misses it.
    Port &answer=ports[1-c];
    answer.rawHook=true; answer.rawChangedAt=millis();
    delay(RING_TRIP_MS-1); exchangeUpdate(millis());
    assert(exState==EX_RINGING);
    delay(1); events.clear(); exchangeUpdate(millis());
    assert(exState==EX_CONNECTED && pwmDuty==0);
    checkStopOrder(1-c);
    // One side hangs up, remaining side must not redial automatically.
    ports[c].hook=false; ports[c].hookSince=millis();
    delay(RELEASE_HOOK_MS); exchangeUpdate(millis());
    assert(exState==EX_WAIT_ONHOOK);
    delay(DIAL_NODIGIT_MS+1); exchangeUpdate(millis());
    assert(exState==EX_WAIT_ONHOOK && !ring.active && pwmDuty==0);
    ports[1-c].hook=false; exchangeUpdate(millis());
    assert(exState==EX_IDLE);
  }
  resetAt(); ring.start(1,millis()); ring.update(millis());
  delay(25); ring.update(millis()); assert(pins[PIN_FR_B]==LOW);
  delay(975); events.clear(); ring.update(millis());
  assert(!ring.phaseOn && pins[PIN_RM_B]==LOW); checkStopOrder(1);
  // New burst starts with a complete half-period, independent of the 2s gap.
  clockUs=3100ULL*1000; ring.update(millis());
  assert(pins[PIN_FR_B]==HIGH); delay(24); ring.update(millis());
  assert(pins[PIN_FR_B]==HIGH); delay(1); ring.update(millis());
  assert(pins[PIN_FR_B]==LOW);
  for (int idx=0;idx<2;++idx) {
    resetAt(); ringTest(idx,millis()); exchangeUpdate(millis());
    assert(exState==EX_RING_TEST && pins[ports[idx].rmPin]==HIGH);
    delay(RING_TIMEOUT_MS); exchangeUpdate(millis());
    assert(exState==EX_IDLE && !ring.active);
  }
  resetAt(); ports[0].hook=ports[0].rawHook=true;
  startDial(0,millis()); startRinging(millis()); exchangeUpdate(millis());
  delay(RING_TIMEOUT_MS); exchangeUpdate(millis()); assert(exState==EX_BUSY);
  delay(BUSY_TONE_MS); exchangeUpdate(millis()); assert(exState==EX_WAIT_ONHOOK);
  // Caller cancellation uses the same F/R-before-RM shutdown.
  resetAt(); ports[0].hook=ports[0].rawHook=true;
  startDial(0,millis()); startRinging(millis()); exchangeUpdate(millis());
  ports[0].hook=ports[0].rawHook=false; events.clear(); exchangeUpdate(millis());
  assert(exState==EX_IDLE && !ring.active); checkStopOrder(1);
  // Ring trip also works when the SHK edge crosses millis() wraparound.
  resetAt(UINT32_MAX-30); ports[0].hook=ports[0].rawHook=true;
  startDial(0,millis()); startRinging(millis()); exchangeUpdate(millis());
  delay(40); ports[1].rawHook=true; ports[1].rawChangedAt=millis();
  delay(RING_TRIP_MS); exchangeUpdate(millis()); assert(exState==EX_CONNECTED);
  // Hang-up duration remains valid across millis() wraparound.
  resetAt(UINT32_MAX-200); ports[0].hook=ports[1].hook=true;
  caller=0; startConnected(millis());
  delay(300); // hook transition occurs after the counter wraps
  ports[1].hook=false; ports[1].hookSince=millis();
  delay(RELEASE_HOOK_MS); exchangeUpdate(millis());
  assert(exState==EX_WAIT_ONHOOK);
  // Issue #5: stopping a single-port ring test by taking the target
  // off-hook must not turn into a new call to the other port. Drives the
  // real loop()/updateHook() path (the ring-test stop used to skip the
  // hook sync that the EX_RINGING answer path performs, so toIdle()
  // dropped to EX_IDLE and the still-off-hook handset was picked up as
  // a fresh caller once the 15ms debounce confirmed).
  for (int idx=0;idx<2;++idx) {
    resetAt(); ringTest(idx,millis()); loop();
    assert(exState==EX_RING_TEST && pins[ports[idx].rmPin]==HIGH);
    pins[ports[idx].shkPin]=HIGH;      // target answers (off-hook)
    loop(); delay(8); loop();          // RING_TRIP_MS reached -> test stops
    assert(exState==EX_WAIT_ONHOOK);   // hook synced: NOT a fresh IDLE
    assert(ports[idx].hook && ports[idx].rawHook);
    // Well past DIAL_NODIGIT_MS (6s): the other port must never ring.
    for (int t=0;t<6500;t+=50) {
      delay(50); loop();
      assert(exState==EX_WAIT_ONHOOK);
      assert(pins[ports[1-idx].rmPin]==LOW && !ring.active && pwmDuty==0);
    }
    // Hanging the handset back up returns the exchange to IDLE.
    pins[ports[idx].shkPin]=LOW;
    loop();                            // register the raw on-hook change
    delay(HOOK_DEBOUNCE_MS+10); loop(); // debounce confirms -> IDLE
    assert(exState==EX_IDLE);
  }
  // DTMF hold refreshes the interdigit timer; digit storage is bounded.
  dtmf.reset(); dtmf.feed('1',1); dtmf.feed('1',2); dtmf.feed('1',3000);
  assert(dtmf.lastDigitAt==3000 && dtmf.digits=="1");
  for (int i=0;i<100;++i) { dtmf.feed(0,i); dtmf.feed('2',i); dtmf.feed('2',i); }
  assert(dtmf.digits.length()==64);
  std::cout << "exchange regression scenarios passed\n";
}
