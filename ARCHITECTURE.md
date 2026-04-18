# Kiến trúc hệ thống: OTL-06ALS Coffee Roaster CMS

> Firmware điều khiển máy rang cà phê — PlatformIO / Arduino / STM32F103RC

---

## 1. Tổng quan

Hệ thống CMS (Control & Monitoring System) điều khiển toàn bộ quá trình rang cà phê từ giao tiếp HMI, đọc cảm biến nhiệt, điều khiển bếp gas / gió / trống, ghi log SD card, đến tích hợp phần mềm rang Artisan (PC).

| Thành phần      | Chi tiết                              |
|----------------|---------------------------------------|
| MCU            | STM32F103RC (ARM Cortex-M3, 72 MHz)   |
| Framework      | Arduino (PlatformIO)                  |
| Board          | genericSTM32F103RC                    |
| Hardware variant | V300 / V400 (define trong `Define.h`) |

---

## 2. Cấu trúc file

```
├── platformio.ini          # Cấu hình build, dependencies
├── src/
│   └── main.cpp            # Entry point: setup() + loop()
└── include/
    ├── Define.h            # Global state: tất cả biến, macro, pin (~2000 dòng)
    ├── IOConfig.h          # GPIO init + relay control
    ├── AnalogConfig.h      # DAC output + ADC input + slew rate
    ├── PID_Airflow.h       # Vacuum PID + FF table + factory auto-tune
    ├── ScaleFeeder.h       # Bluetooth scale parser
    ├── Modbus_Slave.h      # Artisan PC interface (Modbus RTU slave)
    ├── Modbus_Master.h     # HMI + sensor + inverter (Modbus RTU master)
    └── Program.h           # Business logic: roasting state machine + SD log
```

### Thứ tự include trong `main.cpp`

```
main.cpp
 ├── <Arduino.h>, <HardwareSerial.h>
 ├── <ModbusMaster.h>          ← lib: 4-20ma/ModbusMaster
 ├── <Wire.h>, <Adafruit_MCP4725.h>  ← lib: adafruit/Adafruit MCP4725
 ├── <ModbusRTU.h>             ← lib: Modbus slave (ESP MTlab)
 ├── <SPI.h>, <SD.h>           ← lib: arduino-libraries/SD
 ├── <STM32TimerInterrupt.h>   ← lib: STM32_TimerInterrupt-1.3.0
 ├── <SimpleKalmanFilter.h>    ← lib: denyssene/SimpleKalmanFilter
 └── "Define.h"
      ├── "IOConfig.h"
      ├── "PID_Airflow.h"
      ├── "AnalogConfig.h"
      ├── "ScaleFeeder.h"
      ├── "Modbus_Slave.h"
      ├── "Modbus_Master.h"
      └── "Program.h"
```

---

## 3. Kiến trúc phân tầng

```
┌──────────────────────────────────────────────────────────────┐
│                        main.cpp                              │
│                   setup()  +  loop()                         │
└────────────┬──────────────┬──────────────┬───────────────────┘
             │              │              │
     ┌───────▼───────┐ ┌────▼────────┐ ┌──▼──────────────┐
     │  Program.h    │ │Modbus_      │ │ Modbus_Slave.h  │
     │ (Business     │ │Master.h     │ │ (Artisan PC /   │
     │  Logic +      │ │(HMI/Sensor/ │ │  Modbus RTU     │
     │  State        │ │ Inverter    │ │  Slave)         │
     │  Machine)     │ │ Transport)  │ └─────────────────┘
     └───────┬───────┘ └────┬────────┘
             │              │
             └──────┬───────┘
                    ▼
     ┌──────────────────────────────────────────────────────┐
     │                    Define.h                          │
     │          Global State — biến, macro, pin             │
     └────┬──────────┬──────────┬──────────┬────────────────┘
          ▼          ▼          ▼          ▼
    ┌──────────┐ ┌────────┐ ┌────────┐ ┌────────────┐
    │ IOConfig │ │Analog  │ │  PID   │ │ScaleFeeder │
    │ .h       │ │Config.h│ │Airflow │ │.h          │
    │ (GPIO +  │ │(DAC +  │ │.h      │ │(Bluetooth  │
    │  relay)  │ │ ADC)   │ │(Vacuum)│ │ scale)     │
    └──────────┘ └────────┘ └────────┘ └────────────┘
```

---

## 4. Phần cứng & giao tiếp

### UART / Serial

| Port    | Tốc độ   | Kết nối                        | Biến alias        |
|---------|----------|-------------------------------|-------------------|
| USART1  | 115200   | Delta HMI touchscreen (RS485) | `SerialHmi`       |
| USART2  | 38400    | RS485 bus: sensor + inverter  | `SerialModbus`    |
| UART4   | 9600     | PC debug / Artisan (Modbus Slave) | `SerialComputer` |
| USART3  | 2400     | Bluetooth scale               | `SerialBluetooth` |

> **V300**: SerialModbus = Serial4, SerialComputer = Serial2 (ngược lại V400)

### Modbus RTU Master — `SerialHmi` (node HMI) + `SerialModbus` (các node còn lại)

| Node          | Slave ID | Đối tượng                   |
|---------------|----------|-----------------------------|
| `nodeHMI`     | 1        | Delta HMI (registers & coils) |
| `nodeBT`      | 1        | Thermocouple BT (Bean Temp) |
| `nodeET`      | 2        | Thermocouple ET (Env Temp)  |
| `nodeAir`     | 5        | Airflow inverter            |
| `nodeDrum`    | 4        | Drum inverter               |
| `nodeIORelay` | 7        | IO relay module 8 kênh      |

### Modbus RTU Slave — `SerialComputer`

- Object: `ModbusRTU mbs`
- Slave ID & baudrate: cấu hình từ HMI (`modbusID_R`, `modbusBaud_R`), hot-reload khi thay đổi
- 27 holding registers cho Artisan PC đọc/ghi

### I2C (Wire)

| Địa chỉ | Thiết bị               | Mục đích           |
|---------|------------------------|--------------------|
| `0x60`  | Adafruit MCP4725 DAC   | Điều khiển airflow |
| `0x61`  | Adafruit MCP4725 DAC   | Điều khiển gas     |

### SPI — SD card

- CS pin: PC5 (V400), PC4 (V300)
- Lưu profile rang (`.txt`), CSV log (`.csv`), FF table PID (`/pid_ff.txt`)

### Digital I/O (V400)

| Pin   | Hướng  | Chức năng             |
|-------|--------|-----------------------|
| PA0   | OUT    | CH1_RL — Gas solenoid |
| PA1   | OUT    | CH2_RL — Cooling motor|
| PD2   | OUT    | CH3_RL — Charge cylinder |
| PC12  | OUT    | CH4_RL — Drop cylinder|
| PC4   | OUT    | CH5_RL — Escape cylinder |
| PB0   | OUT    | CH6_RL — Afterburner  |
| PB1   | OUT    | CH7_RL — Destoner     |
| PB2   | OUT    | CH8_RL — Feeder motor |
| PB12–15, PA11, PA15 | IN | CH1–CH6 Digital inputs |
| PC3   | AIN    | CH1_ANALOG — Airflow VR |
| PC2   | AIN    | CH2_ANALOG — Drum VR  |
| PC1   | AIN    | CH3_ANALOG — Gas VR   |
| PA4   | OUT    | BUZZER                |
| PC13  | OUT    | ERROR LED             |

---

## 5. Vòng lặp chính

### setup()

```
SerialComputer.begin(9600)   // PC debug
ConfigIO()                   // GPIO init
analogConfig()               // DAC I2C init
ModbusRS485Config()          // UART + Modbus nodes init
configTimer()                // STM32 TIM1 ISR @ 1kHz
checkError()                 // System self-test
rwMemHMI()                   // Load config từ HMI $M registers
ModbusSlaveConfig()          // Artisan Modbus slave init
pidLoadFromSD()              // Đọc FF table PID từ SD
reset_update()               // Clear trạng thái HMI
```

### loop() — ~20–100 ms/cycle

```
analogIn()              ← Đọc VR/PID/PC → airflowPercent, gasPercent, drumPercent
analogOut()             ← DAC gas (slew rate) + DAC airflow
readTempET()            ← Modbus đọc ET từ nodeET
readTempBT()            ← Modbus đọc BT từ nodeBT
readWriteDrumINV()      ← Modbus đọc/ghi tần số trống [if chDrumFlag]
readUnder()             ← Modbus đọc Diff_Air (áp suất chân không) [if chAirFlag]
readWriteAirINV_PID()   ← Modbus cập nhật airflow inverter theo PID [if chAirFlag]
handle_Modbus_Slave()   ← Artisan: publish telemetry, nhận setpoints/buttons
readScale()             ← Bluetooth: parse "GS,NN.N,kg" → netW
rwHMICoil()             ← Đọc coils HMI (B1–B20)
rwMemHMI()              ← Đọc $M1–$M51 HMI config
rwHMI_1()               ← Đọc 40001–40033: nút bấm + ghi BT/ET lên HMI
rwHMI_2()               ← Đọc 40060–40086: ghi gas%, drum%, RoR, milestones
rwIORelayCoil()         ← Cập nhật IO relay Modbus [if chIORelayFlag]
programScan()           ← State machine rang cà phê
controlIO()             ← Map button states → relay outputs
calTime = millis()-timeMillis  ← Đo loop time
pidSelfTuneTask()       ← Self-learning PID (ngoài ISR)
pidSDTask()             ← Ghi/đọc FF table SD (non-blocking)
```

### ISR — TIM1, 1 kHz

```
timerPoll_1000ms() {
    countTimer++
    handleTimer(...)         ← Tăng tất cả các bộ đếm thời gian
    selfTuneTickEn = true    ← Set flag để pidSelfTuneTask() xử lý
    timeRoast++              ← Đếm giây rang (nếu timeRoastEn)
    sdLogDataEn = 1          ← Trigger ghi CSV (nếu progStatus == SAVE)
    calibGasProgramEn = 1    ← Trigger calib gas (nếu AUTO mode)
    // Tính RoR mỗi 3 giây (Kalman filter)
    rorBT = rorBTKalmanFilter.updateEstimate(raw_rorBT)
    rorET = rorETKalmanFilter.updateEstimate(raw_rorET)
}
```

---

## 6. State machine rang cà phê (`programScan`)

### Các bước (`progStep`)

```
STP_DATA (0)
  └─► STP_COOL_DOWN (1)   ← Chờ BT giảm về nhiệt charge (nếu có auto charge)
       └─► STP_GAS (3)    ← Kiểm tra gas đã bật
            └─► STP_CHECK (4)  ← Chờ BT đạt chargeTemp ± tolerance
                 └─► STP_CHARGE (5)  ← Chờ người dùng bấm CHARGE
                      └─► STP_TP (6)      ← Phát hiện turning point
                           └─► STP_YELLOW (7) ← Phát hiện Yellow phase
                                └─► STP_FCS (8)  ← Phát hiện First Crack Start
                                     └─► STP_DEV (9)  ← Tính Development %
                                          └─► STP_DROP (10) ← Bấm DROP
                                               └─► STP_COOLING (11)
                                                    └─► STP_ESCAPE (12)
                                                         └─► STP_LOOP_1 (13)
                                                              └─► STP_LOOP_2 (14)
```

### Ba chế độ vận hành (`progStatus`)

| Chế độ | Giá trị | Mô tả |
|--------|---------|-------|
| Manual Save | `STT_PROGRAM_SAVE` | Operator điều khiển, ghi SD |
| Auto | `STT_PROGRAM_AUTO` | Chạy theo profile SD, auto gas |
| Remote (PC) | — | Artisan PC gửi lệnh qua Modbus |

### Nguồn điều khiển (`naviSource*`)

| Giá trị | Ý nghĩa |
|---------|---------|
| `SOURCE_AI_VR (0)` | Manual — đọc từ biến trở (potentiometer) |
| `SOURCE_AI_PC (1)` | Remote — nhận từ Artisan PC qua Modbus |
| `SOURCE_AI_AUTO (2)` | Auto — theo profile SD card |

---

## 7. Module PID Airflow — Vacuum Pressure Control

File: [include/PID_Airflow.h](include/PID_Airflow.h)

### Kiến trúc

```
Pressure Transmitter (Diff_Air, Pa)
        │
        ▼
  Kalman Filter (e=70, q=70, r=0.2)  ← làm mượt tín hiệu
        │
        ▼
  ┌─────────────────────────────────────┐
  │        pidAirflowUpdate()           │
  │                                     │
  │  SP → ffLookup(SP) → Air% init      │  ← Feed-Forward snap khi đổi SP
  │                                     │
  │  |err| ≤ 5 Pa  → giữ nguyên         │  ← Deadband
  │  err < -5 Pa   → airflow += 1%      │  ← Step tăng
  │  err > +5 Pa   → airflow -= 1%      │  ← Step giảm
  └─────────────────────────────────────┘
        │
        ▼
  airflowPercent → analogOut() → MCP4725 → Airflow Inverter
```

### FF Table (Feed-Forward)

| Thông số | Giá trị |
|----------|---------|
| Dung lượng tối đa | 50 entries |
| File lưu trữ | `/pid_ff.txt` trên SD |
| Match threshold | ±3 Pa |
| Drift threshold | 3% — re-learn nếu hệ thống thay đổi |
| Stable time để học | 10 giây |
| Lưu SD định kỳ | mỗi 60 giây (nếu dirty) |

### Factory Auto-Tune

```
Bấm AUTO_PID_AIR_TU trên HMI
  └─► pidFactoryTuneStart()
       └─► Quét Air% 0 → 100%, bước 1%, mỗi bước 2s
            └─► Đo Pa trung bình ở giây cuối
                 └─► Ghi vào ffMap[]
                      └─► Lưu /pid_ff.txt
                           └─► Tắt tuning trên HMI
```
Tổng thời gian: ~3 phút 22 giây (101 bước × 2s)

---

## 8. Giao tiếp Artisan PC — `Modbus_Slave.h`

### Các register (27 holding registers)

| Register | Địa chỉ | Hướng | Nội dung |
|----------|---------|-------|----------|
| `BT_show_artisan` | 0 | R | Bean Temperature (×10) |
| `ET_show_artisan` | 1 | R | Env Temperature (×10) |
| `AIRshow_artisan` | 2 | R | Airflow % |
| `GAS_show_artisan` | 3 | R | Gas % |
| `DRUM_show_artisan` | 4 | R | Drum % |
| `UNDER_show_artisan` | 9 | R | Vacuum pressure (Pa) |
| `SV_show_artisan` | 19 | R | BT Setpoint |
| `AIR_artisan_W` | 10 | R/W | Artisan → airflow setpoint |
| `GAS_artisan_W` | 11 | R/W | Artisan → gas setpoint |
| `IGNITION_artisan_W` | 12 | R/W | Artisan → bật/tắt gas |
| `CHARGE_artisan_W` | 14 | R/W | Artisan → charge |
| `DROP_artisan_W` | 15 | R/W | Artisan → drop |

### Hai chế độ

| `PC_CONTROL_BTN_R` | Ý nghĩa |
|--------------------|---------|
| `1` | Artisan điều khiển: gửi nút bấm & setpoints → Arduino sync sang HMI |
| `0` | HMI điều khiển: Artisan chỉ đọc telemetry, không nhận lệnh |

---

## 9. SD Card — Profile & Logging

### Format profile (`.txt`)

```
R<time>,<BT>,<ET>,<Air>,<Gas>,<Drum>,<RoR>,<VacFlag>,<VacSP>E
P<ChargeBT>,<TP_BT>,<TP_time>,<DE_BT>,<DE_time>,<FCS_BT>,<FCS_time>,
  <DEV_BT>,<DEV_time>,<DROP_BT>,<DROP_time>E
```

- Thời gian: giây (index = second)
- Nhiệt độ: ×10 (1850 = 185.0°C)
- VacFlag: 0 = airflow direct, 1 = PID vacuum control

### Format CSV log (Artisan-compatible)

```
Date:01.01.2024    Unit:C    CHARGE:MM:SS    TP:MM:SS    DRYe:MM:SS    FCs:MM:SS    DROP:MM:SS
Time1  Time2  ET   BT   Event  Drum(%)  Airflow(%)  Burner(%)  Drum(RPM)  SV(C)  RoR  VacFlag  VacSP
```

- Sampling: 1 Hz (tối đa 1500 giây = 25 phút)
- Header được overwrite bằng `seek(0)` khi kết thúc DROP

---

## 10. Global State Management Pattern

Tất cả biến trạng thái trong [include/Define.h](include/Define.h).

### Read-Compare-Update Pattern

Mọi giá trị đọc từ HMI đều dùng cặp `_R` / `_R_CP`:

```cpp
// Trong rwMemHMI():
iMemHMI_CP[i] = nodeHMI.getResponseBuffer(i-1);  // đọc vào _CP

if (btSV_R != btSV_R_CP) {          // so sánh
    btSV_R    = btSV_R_CP;           // cập nhật giá trị chính
    btSV_R_CV = btSV_R * 10;         // convert (×10)
    SV_BT     = btSV_R_CV;
    svEn      = 1;                   // set flag
}
```

**Lợi ích**: Tránh ghi Modbus thừa, tránh reset baudrate liên tục.

### ISR → Loop Flag Pattern

```cpp
// Trong ISR (timerPoll_1000ms):
selfTuneTickEn = true;   // chỉ set flag

// Trong loop():
pidSelfTuneTask();        // logic nặng chạy ngoài ISR
```

**Lý do**: Tránh gọi SD / Modbus trong ngắt — gây deadlock.

### Non-blocking SD State Machine

```cpp
// sdRead() dùng sdReadStep
SD_1 → mở file & parse
SD_2 → xử lý lỗi
SD_3 → ghi data lên HMI
SD_4 → idle chờ

// pidSDTask() dùng sdPendingCmd
SD_IDLE → SD_LOAD_FF → SD_SAVE_FF
```

---

## 11. Kalman Filters

| Filter | Đối tượng | E, Q, R | Mục đích |
|--------|-----------|---------|----------|
| `rorBTKalmanFilter` | RoR Bean Temp | 1, 1, 0.01 | Tính tốc độ tăng nhiệt BT |
| `rorETKalmanFilter` | RoR Env Temp | 1, 1, 0.01 | Tính tốc độ tăng nhiệt ET |
| `diff_KalmanFilter` | Vacuum (Pa) | 70, 70, 0.2 | Làm mượt tín hiệu áp suất |

RoR được tính mỗi 3 giây:
```cpp
raw_rorBT = (Temperature_BT - rorBTSamp_1) * 20;  // °C/min × 10
rorBT = rorBTKalmanFilter.updateEstimate(raw_rorBT);
```

---

## 12. Slew Rate Limiter — Gas DAC

Để tránh thay đổi gas đột ngột gây nguy hiểm:

```
Gas relay OFF  → snap ngay về gasPercent (không ramp)
Gas relay ON   → ramp:
                   Tăng tối đa: +2% mỗi 100ms  (100% / 5s)
                   Giảm tối đa: -1% mỗi 100ms  (100% / 10s)
```

Sau khi qua slew limiter → map sang DAC 12-bit:
```cpp
int mapDAC_gas = map(gasCurrent, 0, 100, 0, (4095 * maxGasSet_R) / 100);
dac_gas.setVoltage(mapDAC_gas, false);
```

---

## 13. Dependencies (`platformio.ini`)

```ini
[env:genericSTM32F103RC]
platform   = ststm32
board      = genericSTM32F103RC
framework  = arduino
lib_deps   =
    arduino-libraries/SD@^1.2.4
    4-20ma/ModbusMaster@^2.0.1
    adafruit/Adafruit MCP4725@^2.0.0
    denyssene/SimpleKalmanFilter@^0.1.0
```

Ngoài ra dùng (bundled / local):
- `STM32_TimerInterrupt-1.3.0` — hardware timer ISR
- `ModbusRTU` (ESP MTlab) — Modbus slave

---

## 14. Debug

Bật debug bằng cờ `enDebug = 1` (từ HMI hoặc code):

```
Loop: 87ms | Feeder: 0 | Charge: 12 | Roast: 245 | CalSD: 34
```

Output qua `SerialComputer` (UART4, 9600 baud) → PC terminal.

---

*Cập nhật lần cuối: 2026-04-07*
