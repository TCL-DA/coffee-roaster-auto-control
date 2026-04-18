# CLAUDE.md — OTL-06ALS Coffee Roaster CMS

Firmware điều khiển máy rang cà phê chạy trên STM32F103RC, dùng PlatformIO + Arduino framework.

---

## Build & Flash

```bash
# Build
pio run -e genericSTM32F103RC

# Flash qua ST-Link
pio run -e genericSTM32F103RC --target upload

# Kiểm tra kích thước RAM/Flash
pio run -e genericSTM32F103RC --target size

# Monitor serial debug (UART4, 9600 baud)
pio device monitor --baud 9600
```

---

## Hardware Constraints

| Tài nguyên | Giới hạn | Ghi chú |
|-----------|---------|---------|
| Flash     | 256 KB  | Firmware + SD lib + Modbus libs |
| RAM       | 20 KB   | **Rất hạn chế** — cẩn thận mảng lớn |
| EEPROM    | Không có | Dùng SD card để lưu persistent data |
| CPU       | 72 MHz ARM Cortex-M3 | Không có FPU |

### Mảng lớn cần chú ý (khai báo trong Define.h)
- `sdBT[1500]`, `sdET[1500]` — 3000 bytes mỗi mảng (int16_t)
- `sdAirflow[1500]`, `sdGas[1500]`, `sdDrum[1500]` — ~1500 bytes mỗi mảng
- `iMemHMI[60]`, `dAddress[200]` + bản sao `_CP[]` — ~1 KB
- Tổng ước tính mảng SD: **~15 KB** → gần hết RAM

---

## Kiến trúc file

```
src/main.cpp          — Entry point, setup() + loop()
include/Define.h      — Global state: tất cả biến, macro, pin (~2000 dòng)
include/IOConfig.h    — GPIO init + relay control
include/AnalogConfig.h — DAC (MCP4725 I2C) + ADC + slew rate gas
include/PID_Airflow.h — Vacuum PID step controller + FF table + auto-tune
include/ScaleFeeder.h — Bluetooth scale parser ("GS,NN.N,kg")
include/Modbus_Slave.h — Artisan PC interface (ModbusRTU slave, 27 regs)
include/Modbus_Master.h — HMI + sensor + inverter (ModbusMaster library)
include/Program.h     — Business logic: roasting state machine + SD log
```

Tài liệu đầy đủ: [ARCHITECTURE.md](ARCHITECTURE.md)

---

## Modbus Nodes (RS485)

| Node | Slave ID | Serial | Baud | Thiết bị |
|------|---------|--------|------|---------|
| nodeHMI | 1 | SerialHmi (USART1) | 115200 | Delta HMI |
| nodeBT | 1 | SerialModbus (USART2) | 38400 | Thermocouple BT |
| nodeET | 2 | SerialModbus | 38400 | Thermocouple ET |
| nodeDrum | 4 | SerialModbus | 38400 | Drum inverter |
| nodeAir | 5 | SerialModbus | 38400 | Airflow inverter |
| nodeIORelay | 7 | SerialModbus | 38400 | IO relay 8ch |
| mbs (slave) | configurable | SerialComputer (UART4) | configurable | Artisan PC |

---

## Naming Conventions

- `*_R` — giá trị đang dùng (ví dụ: `btSV_R`)
- `*_R_CP` — bản copy từ HMI để so sánh (ví dụ: `btSV_R_CP`)
- `*_R_CV` — giá trị đã convert (×10) để tính toán nội bộ (ví dụ: `btSV_R_CV`)
- `*_W` — địa chỉ Modbus register để ghi (ví dụ: `BT_HMI_W`)
- `*En` — flag bật/tắt (ví dụ: `chargeTimerEn`)
- `*Ti` / `*Timer` — biến đếm thời gian (ví dụ: `chargeTimer`)
- `STP_*` — bước trong state machine (ví dụ: `STP_CHARGE`)
- `STT_*` — trạng thái chương trình (ví dụ: `STT_PROGRAM_AUTO`)
- `SOURCE_AI_*` — nguồn điều khiển (VR / PC / AUTO)

---

## ISR Safety

- `timerPoll_1000ms()` chạy trong ISR (TIM1, 1kHz)
- **Không gọi SD / Modbus / Serial trong ISR**
- Dùng flag pattern: ISR set `selfTuneTickEn = true`, logic nặng chạy trong `loop()`
- Biến dùng chung giữa ISR và loop cần khai báo `volatile`

---

## Đơn vị dữ liệu

- Nhiệt độ: lưu dạng **×10** (ví dụ: 1850 = 185.0°C)
- Thời gian rang: **giây** (ví dụ: `timeRoast = 245` = 4 phút 5 giây)
- Gas/Airflow/Drum: **% nguyên** (0–100)
- Áp suất chân không: **Pa** (ví dụ: `Diff_Air = -80`)
- Cân: **×10** (ví dụ: `netW = 617` = 61.7 kg)

---

## SD Card Files

| File | Mục đích |
|------|---------|
| `0.txt` – `15.txt` | Profile rang (format cũ) |
| `0.csv` – `15.csv` | Log Artisan CSV (format mới) |
| `/pid_ff.txt` | FF table PID vacuum (Pa → Air%) |

---

## Debug

Bật debug: đặt `enDebug = 1` trong code hoặc từ HMI.

Output qua `SerialComputer` (UART4, 9600 baud):
```
Loop: 87ms | Charge: 12 | Roast: 245 | CalSD: 34
```

**Quy tắc SerialComputer:**
- Tất cả string in ra `SerialComputer` phải bằng **tiếng Anh**
- Chỉ in khi `enDebug = 1`: `if(enDebug) SerialComputer.println("...")`

---

## Workflow gợi ý

- Trước khi sửa code lớn: dùng `/plan` để thiết kế
- Sau khi sửa: chạy `/simplify` để review chất lượng
- Kiểm tra RAM: chạy `/memory-check`
- Kiểm tra Modbus: chạy `/modbus-audit`
- Phân tích PID: chạy `/pid-analysis`
- Trace state machine: chạy `/state-trace`
- Commit: dùng `/commit`
