// STM32_TimerInterrupt 1.3.0 — bản giả: ngắt timer được board ảo gọi bù theo thời gian thực
// ở mọi điểm firmware "chạm" vào thời gian (millis/delay/Modbus/...) — giống ngắt chen giữa lệnh.
#pragma once
#include "Arduino.h"

void sim_attach_isr(uint32_t interval_us, void (*cb)());

class STM32Timer {
  public:
    explicit STM32Timer(TIM_TypeDef *t) { (void)t; }
    bool attachInterruptInterval(uint32_t interval_us, void (*cb)())
    {
        sim_attach_isr(interval_us, cb);
        return true;
    }
    bool setInterval(uint32_t interval_us, void (*cb)()) { return attachInterruptInterval(interval_us, cb); }
    void stopTimer() { sim_attach_isr(0, nullptr); }
    void restartTimer() {}
    void detachInterrupt() { sim_attach_isr(0, nullptr); }
};
