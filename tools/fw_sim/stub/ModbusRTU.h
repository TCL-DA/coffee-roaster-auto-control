// ModbusRTU (lib/ModbusESP, emelianov) — bản giả cho board ảo: chỉ giữ bảng Hreg.
// Firmware dùng mbs làm slave cho Artisan / app OTL Roast Lab. Board ảo mở bảng này ra
// Modbus TCP (sim_core.cpp, cổng OTL_FW_SLAVE_PORT, mặc định 1502) để app nối vào được.
#pragma once
#include "Arduino.h"

void sim_mbs_bind(class ModbusRTU *m);

class ModbusRTU {
  public:
    uint16_t regs[65536 / 4] = {0};  // đủ cho dải PC_Link/Artisan (dưới 16384)
    bool has[65536 / 4] = {false};
    uint8_t id = 1;
    ModbusRTU() { sim_mbs_bind(this); }
    bool begin(HardwareSerial *, int16_t txPin = -1, bool direct = true)
    {
        (void)txPin;
        (void)direct;
        return true;
    }
    bool begin(Stream *, int16_t txPin = -1, bool direct = true)
    {
        (void)txPin;
        (void)direct;
        return true;
    }
    void setBaudrate(uint32_t) {}
    void slave(uint8_t s) { id = s; }
    uint8_t slave() const { return id; }
    bool addHreg(uint16_t off, uint16_t value = 0, uint16_t num = 1)
    {
        for (uint16_t i = 0; i < num; i++) {
            uint32_t k = (uint32_t)off + i;
            if (k < sizeof(regs) / sizeof(regs[0])) {
                has[k] = true;
                regs[k] = value;
            }
        }
        return true;
    }
    bool Hreg(uint16_t off, uint16_t value)
    {
        if (off >= sizeof(regs) / sizeof(regs[0]) || !has[off])
            return false;
        regs[off] = value;
        return true;
    }
    uint16_t Hreg(uint16_t off)
    {
        return (off < sizeof(regs) / sizeof(regs[0]) && has[off]) ? regs[off] : 0;
    }
    void task();
};
