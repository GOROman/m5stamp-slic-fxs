#pragma once
#include <cstdint>
#include <string>
#include <vector>
constexpr int HIGH=1, LOW=0, INPUT=0, OUTPUT=1, ADC_11db=3;
constexpr float PI=3.14159265358979323846f;
struct String : std::string {
  using std::string::string;
  using std::string::operator=;
};
struct PinEvent { uint32_t at; int pin, value; };
inline uint64_t clockUs=0;
inline int pins[64]={};
inline int pwmDuty=0;
inline std::vector<PinEvent> events;
inline uint32_t millis() { return static_cast<uint32_t>(clockUs/1000); }
inline uint32_t micros() { return static_cast<uint32_t>(clockUs); }
inline void delay(uint32_t ms) { clockUs+=ms*1000ULL; }
inline void delayMicroseconds(uint32_t us) { clockUs+=us; }
inline void pinMode(int,int) {}
inline int digitalRead(int pin) { return pins[pin]; }
inline void digitalWrite(int pin,int value) {
  pins[pin]=value; events.push_back({millis(),pin,value});
}
inline int analogRead(int) { return 2048; }
inline void analogSetPinAttenuation(int,int) {}
inline void analogReadResolution(int) {}
inline bool ledcAttach(int,int,int) { return true; }
inline bool ledcWrite(int,int duty) { pwmDuty=duty; return true; }
struct SerialStub {
  void begin(int) {}
  void println(const char*) {}
  template<class... T> void printf(const char*,T...) {}
  int available() { return 0; }
  int read() { return -1; }
};
inline SerialStub Serial;
