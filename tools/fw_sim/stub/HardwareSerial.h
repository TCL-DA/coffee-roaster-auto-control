// Print / Stream / HardwareSerial kiểu STM32duino cho board ảo.
#pragma once
#include "Arduino.h"

// Gửi/nhận byte thật nằm ở sim_core.cpp (port = số USART: 1..5; 0 = Serial USB)
void sim_serial_write(int port, uint8_t b);
int sim_serial_available(int port);
int sim_serial_read(int port);
int sim_serial_peek(int port);

class Print {
  public:
    virtual ~Print() {}
    virtual size_t write(uint8_t b) = 0;
    virtual size_t write(const uint8_t *buf, size_t n)
    {
        size_t k = 0;
        while (n--)
            k += write(*buf++);
        return k;
    }
    size_t write(const char *s) { return s ? write((const uint8_t *)s, strlen(s)) : 0; }
    size_t write(const char *s, size_t n) { return write((const uint8_t *)s, n); }

    size_t print(const char *s) { return write(s); }
    size_t print(const String &s) { return write(s.c_str()); }
    size_t print(char c) { return write((uint8_t)c); }
    size_t print(unsigned char v, int base = DEC) { return print((unsigned long)v, base); }
    size_t print(int v, int base = DEC) { return print((long)v, base); }
    size_t print(unsigned int v, int base = DEC) { return print((unsigned long)v, base); }
    size_t print(short v, int base = DEC) { return print((long)v, base); }
    size_t print(unsigned short v, int base = DEC) { return print((unsigned long)v, base); }
    size_t print(long v, int base = DEC)
    {
        if (base == DEC) {
            char b[32];
            snprintf(b, sizeof(b), "%ld", v);
            return write(b);
        }
        return print((unsigned long)v, base);
    }
    size_t print(unsigned long v, int base = DEC) { return write(String::unum(v, (unsigned char)base).c_str()); }
    size_t print(long long v, int base = DEC) { return print((long)v, base); }
    size_t print(unsigned long long v, int base = DEC) { return print((unsigned long)v, base); }
    size_t print(double v, int digits = 2)
    {
        char b[64];
        snprintf(b, sizeof(b), "%.*f", digits, v);
        return write(b);
    }
    size_t print(float v, int digits = 2) { return print((double)v, digits); }

    size_t println() { return write("\r\n"); }
    template <typename T> size_t println(const T &v) { size_t n = print(v); return n + println(); }
    template <typename T> size_t println(const T &v, int fmt) { size_t n = print(v, fmt); return n + println(); }

    size_t printf(const char *fmt, ...)
    {
        char b[512];
        va_list ap;
        va_start(ap, fmt);
        vsnprintf(b, sizeof(b), fmt, ap);
        va_end(ap);
        return write(b);
    }
};

class Stream : public Print {
  public:
    unsigned long _timeout = 1000;
    virtual int available() = 0;
    virtual int read() = 0;
    virtual int peek() = 0;
    virtual void flush() {}
    void setTimeout(unsigned long t) { _timeout = t; }
    String readStringUntil(char term)
    {
        String r;
        int c;
        while ((c = read()) >= 0 && c != term)
            r += (char)c;
        return r;
    }
    String readString()
    {
        String r;
        int c;
        while ((c = read()) >= 0)
            r += (char)c;
        return r;
    }
    size_t readBytes(char *buf, size_t n)
    {
        size_t k = 0;
        int c;
        while (k < n && (c = read()) >= 0)
            buf[k++] = (char)c;
        return k;
    }
    size_t readBytesUntil(char term, char *buf, size_t n)
    {
        size_t k = 0;
        int c;
        while (k < n && (c = read()) >= 0 && c != term)
            buf[k++] = (char)c;
        return k;
    }
};

#define SERIAL_8N1 0x06
#define SERIAL_8E1 0x26
#define SERIAL_8O1 0x36
#define SERIAL_8N2 0x0E

class HardwareSerial : public Stream {
  public:
    int port;
    unsigned long baud = 0;
    explicit HardwareSerial(USART_TypeDef *u) : port(u ? u->id : 0) {}
    HardwareSerial(uint32_t rx, uint32_t tx) : port(100 + (int)rx) { (void)tx; }
    void begin(unsigned long b, uint8_t cfg = SERIAL_8N1) { baud = b; (void)cfg; }
    void end() {}
    void setRx(uint32_t) {}
    void setTx(uint32_t) {}
    using Print::write;
    size_t write(uint8_t b) override { sim_serial_write(port, b); return 1; }
    int available() override { return sim_serial_available(port); }
    int read() override { return sim_serial_read(port); }
    int peek() override { return sim_serial_peek(port); }
    void flush() override {}
    operator bool() const { return true; }
};

extern HardwareSerial Serial;   // USB/Serial mặc định của core
extern HardwareSerial Serial2;  // core STM32duino tạo sẵn Serial2 (USART2)
