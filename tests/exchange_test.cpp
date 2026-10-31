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
  // DTMF hold refreshes the interdigit timer; digit storage is bounded.
  dtmf.reset(); dtmf.feed('1',1); dtmf.feed('1',2); dtmf.feed('1',3000);
  assert(dtmf.lastDigitAt==3000 && dtmf.digits=="1");
  for (int i=0;i<100;++i) { dtmf.feed(0,i); dtmf.feed('2',i); dtmf.feed('2',i); }
  assert(dtmf.digits.length()==64);
  // Ring-test off-hook must not place a new call on the other port.
  for (int idx = 0; idx < 2; ++idx) {
    resetAt();
    for (int p = 0; p < 64; ++p) pins[p] = LOW;
    ringTest(idx, millis());
    loop();
    pins[ports[idx].shkPin] = HIGH;
    loop();
    delay(RING_TRIP_MS);
    loop();
    assert(exState == EX_WAIT_ONHOOK);
    assert(ports[idx].hook);
    assert(!ring.active);
    assert(pins[ports[idx].rmPin] == LOW);
    delay(DIAL_NODIGIT_MS + 1000);
    for (int n = 0; n < 4; ++n) loop();
    assert(exState == EX_WAIT_ONHOOK);
    assert(pins[ports[1 - idx].rmPin] == LOW);
  }
  std::cout << "exchange regression scenarios passed\n";
}
