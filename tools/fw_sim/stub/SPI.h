#pragma once
#include "Arduino.h"

class SPIClass {
  public:
    void begin() {}
    void end() {}
    void setMOSI(uint32_t) {}
    void setMISO(uint32_t) {}
    void setSCLK(uint32_t) {}
    uint8_t transfer(uint8_t b) { return b; }
};
extern SPIClass SPI;
