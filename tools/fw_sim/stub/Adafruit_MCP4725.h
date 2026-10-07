// Adafruit MCP4725 (DAC 12 bit) — bản giả: giá trị ra đưa vào mô hình máy (sim_core).
#pragma once
#include "Arduino.h"
#include "Wire.h"

void sim_dac_set(uint8_t i2c_addr, uint16_t value);

class Adafruit_MCP4725 {
  public:
    uint8_t addr = 0x62;
    bool begin(uint8_t a = 0x62, TwoWire *w = &Wire)
    {
        (void)w;
        addr = a;
        return true;
    }
    bool setVoltage(uint16_t output, bool writeEEPROM, uint32_t freq = 400000)
    {
        (void)writeEEPROM;
        (void)freq;
        sim_dac_set(addr, output > 4095 ? 4095 : output);
        return true;
    }
};
