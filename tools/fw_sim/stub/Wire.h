#pragma once
#include "Arduino.h"

class TwoWire {
  public:
    void begin() {}
    void begin(uint8_t) {}
    void setClock(uint32_t) {}
    void setSDA(uint32_t) {}
    void setSCL(uint32_t) {}
    void beginTransmission(uint8_t) {}
    uint8_t endTransmission(bool = true) { return 0; }
    size_t write(uint8_t) { return 1; }
    uint8_t requestFrom(uint8_t, uint8_t) { return 0; }
    int available() { return 0; }
    int read() { return -1; }
};
extern TwoWire Wire;
