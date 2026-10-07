// ModbusMaster 2.0.1 (4-20ma) — bản giả cho board ảo.
// Mỗi giao dịch được chuyển cho sim_modbus_transact() ở sim_core.cpp, nơi định tuyến
// theo (cổng nối tiếp, ID slave): HMI -> bộ mô phỏng Delta; đồng hồ nhiệt/biến tần/
// relay -> mô hình trong board ảo.
#pragma once
#include "Arduino.h"

// fc: 1 đọc coil, 3 đọc thanh ghi, 5 ghi 1 coil, 6 ghi 1 thanh ghi, 15 ghi nhiều coil, 16 ghi nhiều thanh ghi
// Trả mã kết quả kiểu ModbusMaster (0 = thành công).
uint8_t sim_modbus_transact(int port, uint8_t slave, uint8_t fc, uint16_t addr, uint16_t qty,
                            const uint16_t *tx, uint16_t *rx, uint16_t rx_cap);

class ModbusMaster {
  public:
    static const uint8_t ku8MBIllegalFunction = 0x01;
    static const uint8_t ku8MBIllegalDataAddress = 0x02;
    static const uint8_t ku8MBIllegalDataValue = 0x03;
    static const uint8_t ku8MBSlaveDeviceFailure = 0x04;
    static const uint8_t ku8MBSuccess = 0x00;
    static const uint8_t ku8MBInvalidSlaveID = 0xE0;
    static const uint8_t ku8MBInvalidFunction = 0xE1;
    static const uint8_t ku8MBResponseTimedOut = 0xE2;
    static const uint8_t ku8MBInvalidCRC = 0xE3;
    static const uint8_t ku8MaxBufferSize = 64;

    uint8_t _slave = 1;
    Stream *_serial = nullptr;
    uint16_t _rx[ku8MaxBufferSize] = {0};
    uint16_t _tx[ku8MaxBufferSize] = {0};
    void (*_pre)() = nullptr;
    void (*_post)() = nullptr;
    void (*_idle)() = nullptr;

    void begin(uint8_t slave, Stream &serial)
    {
        _slave = slave;
        _serial = &serial;
    }
    void preTransmission(void (*f)()) { _pre = f; }
    void postTransmission(void (*f)()) { _post = f; }
    void idle(void (*f)()) { _idle = f; }

    uint16_t getResponseBuffer(uint8_t i) { return i < ku8MaxBufferSize ? _rx[i] : 0xFFFF; }
    void clearResponseBuffer() { memset(_rx, 0, sizeof(_rx)); }
    uint8_t setTransmitBuffer(uint8_t i, uint16_t v)
    {
        if (i >= ku8MaxBufferSize)
            return ku8MBIllegalDataAddress;
        _tx[i] = v;
        return ku8MBSuccess;
    }
    void clearTransmitBuffer() { memset(_tx, 0, sizeof(_tx)); }

    int port() const { return _serial ? ((HardwareSerial *)_serial)->port : -1; }

    uint8_t readCoils(uint16_t a, uint16_t q) { return x(1, a, q); }
    uint8_t readDiscreteInputs(uint16_t a, uint16_t q) { return x(2, a, q); }
    uint8_t readHoldingRegisters(uint16_t a, uint16_t q) { return x(3, a, q); }
    uint8_t readInputRegisters(uint16_t a, uint16_t q) { return x(4, a, q); }
    uint8_t writeSingleCoil(uint16_t a, uint8_t v)
    {
        uint16_t t = v ? 0xFF00 : 0;
        return x(5, a, 1, &t);
    }
    uint8_t writeSingleRegister(uint16_t a, uint16_t v) { return x(6, a, 1, &v); }
    uint8_t writeMultipleCoils(uint16_t a, uint16_t q) { return x(15, a, q, _tx); }
    uint8_t writeMultipleRegisters(uint16_t a, uint16_t q) { return x(16, a, q, _tx); }

  private:
    uint8_t x(uint8_t fc, uint16_t a, uint16_t q, const uint16_t *tx = nullptr)
    {
        if (_pre)
            _pre();
        uint8_t r = sim_modbus_transact(port(), _slave, fc, a, q, tx, _rx, ku8MaxBufferSize);
        if (_post)
            _post();
        return r;
    }
};
