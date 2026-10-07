// Board ảo OTL — lớp giả Arduino/STM32duino để biên dịch firmware THẬT chạy trên PC.
// Chỉ phần API firmware OTL-06ALS dùng. Hành vi phần cứng nằm trong sim_core.cpp.
#pragma once

#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstdarg>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

typedef bool boolean;
typedef uint8_t byte;
typedef uint16_t word;

#define HIGH 1
#define LOW 0
#define INPUT 0
#define OUTPUT 1
#define INPUT_PULLUP 2
#define INPUT_PULLDOWN 3
#define INPUT_ANALOG 4
#define OUTPUT_OPEN_DRAIN 5

#define DEC 10
#define HEX 16
#define OCT 8
#define BIN 2

#define PI 3.1415926535897932384626433832795
#define DEG_TO_RAD 0.017453292519943295769236907684886
#define RAD_TO_DEG 57.295779513082320876798154814105

#define F(x) (x)
#define PROGMEM
#define pgm_read_byte(a) (*(const uint8_t *)(a))
#define pgm_read_word(a) (*(const uint16_t *)(a))
#define pgm_read_dword(a) (*(const uint32_t *)(a))

// Chân STM32: PA0..PA15 = 0..15, PB = 16..31, PC = 32..47, PD = 48..63
enum {
    PA0 = 0, PA1, PA2, PA3, PA4, PA5, PA6, PA7, PA8, PA9, PA10, PA11, PA12, PA13, PA14, PA15,
    PB0, PB1, PB2, PB3, PB4, PB5, PB6, PB7, PB8, PB9, PB10, PB11, PB12, PB13, PB14, PB15,
    PC0, PC1, PC2, PC3, PC4, PC5, PC6, PC7, PC8, PC9, PC10, PC11, PC12, PC13, PC14, PC15,
    PD0, PD1, PD2, PD3, PD4, PD5, PD6, PD7, PD8, PD9, PD10, PD11, PD12, PD13, PD14, PD15,
    SIM_NUM_PINS
};

// Ký hiệu ngoại vi (chỉ để hàm khởi tạo nhận vào)
struct USART_TypeDef { int id; };
struct TIM_TypeDef { int id; };
extern USART_TypeDef *USART1, *USART2, *USART3, *UART4, *UART5;
extern TIM_TypeDef *TIM1, *TIM2, *TIM3, *TIM4;

uint32_t millis();
uint32_t micros();
void delay(uint32_t ms);
void delayMicroseconds(uint32_t us);
void yield();

void pinMode(uint32_t pin, uint32_t mode);
void digitalWrite(uint32_t pin, uint32_t val);
int digitalRead(uint32_t pin);
int analogRead(uint32_t pin);
void analogWrite(uint32_t pin, int val);
void analogReadResolution(int bits);
void analogWriteResolution(int bits);

long random(long howbig);
long random(long howsmall, long howbig);
void randomSeed(unsigned long seed);

inline long map(long x, long in_min, long in_max, long out_min, long out_max)
{
    if (in_max == in_min)
        return out_min;
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min;
}

char *dtostrf(double val, signed char width, unsigned char prec, char *sout);
// itoa/ltoa/ultoa: msvcrt (MinGW) đã khai báo sẵn trong stdlib.h — không khai báo lại.

inline void noInterrupts() {}
inline void interrupts() {}
inline void __disable_irq() {}
inline void __enable_irq() {}

#define lowByte(w) ((uint8_t)((w) & 0xff))
#define highByte(w) ((uint8_t)((w) >> 8))
#define bitRead(value, bit) (((value) >> (bit)) & 0x01)
#define bitSet(value, bit) ((value) |= (1UL << (bit)))
#define bitClear(value, bit) ((value) &= ~(1UL << (bit)))
#define bitWrite(value, bit, bitvalue) ((bitvalue) ? bitSet(value, bit) : bitClear(value, bit))
#define bit(b) (1UL << (b))

// Arduino định nghĩa min/max/abs/constrain là MACRO (chấp nhận trộn kiểu int/float)
#ifdef min
#undef min
#endif
#ifdef max
#undef max
#endif
#define min(a, b) ((a) < (b) ? (a) : (b))
#define max(a, b) ((a) > (b) ? (a) : (b))
// Lõi STM32duino còn có std::min/std::max cho dạng có tham số mẫu: max<int16_t>(x, 0) (Program.h roastMarkTask) —
// tên theo sau là '<' nên macro không nở, phải tra được hàm.
using std::min;
using std::max;
#define constrain(amt, low, high) ((amt) < (low) ? (low) : ((amt) > (high) ? (high) : (amt)))
#define sq(x) ((x) * (x))
// round(): dùng hàm của math.h (trả double) như STM32duino/newlib — KHÔNG định nghĩa macro.
// ⚠ Header chuẩn nào cần dùng sau đây phải #include TRƯỚC file này (macro min/max).

#include "WString.h"
#include "HardwareSerial.h"
