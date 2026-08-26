# Config preset — 3kg-auto-io

Lưu ngày **2026-07-09**.

Máy rang **3kg auto** — không biến trở (VR đọc từ HMI), có **module relay ngoài (IO)**, vacuum đọc từ **biến tần gió**, không cân.

## Đặc thù cấu hình

| Mục | Giá trị | `#define` |
|-----|---------|-----------|
| Mẻ danh định | 3 kg | `MACHINE_BATCH_KG 3` |
| Điều khiển | Auto, không VR | `MACHINE_VR_SOURCE_FROM_HMI 1` — setpoint gió/drum/gas lấy từ HMI, không đọc biến trở |
| **IO relay module** | **Có** | `MACHINE_HAS_IO_RELAY_MODULE 1` — slave ID 7, baud 38400 |
| Cân / auto-loader | **TẮT** | `MACHINE_HAS_SCALE_FEEDER 0` — feeder chạy theo timer |
| Nguồn đọc vacuum | **Gió (slave 5)** | `MACHINE_VACUUM_FROM_DRUM 0` — cảm biến áp suất đấu vào ngõ ACI biến tần gió |
| Vacuum sensor | Có | `MACHINE_HAS_VACUUM_SENSOR 1`, PID gió |
| Drum / Air inverter | Có | `MACHINE_HAS_DRUM_SPEED_CONTROL 1`, `MACHINE_HAS_AIR_INVERTER 1` — RS485 Modbus |
| Gas / Airflow | Có | `MACHINE_HAS_GAS_CONTROL 1`, `MACHINE_HAS_AIRFLOW_CONTROL 1` |
| BT / ET thermocouple | Có | `MACHINE_HAS_BT_TEMP_CONTROLLER 1`, `MACHINE_HAS_ET_TEMP_CONTROLLER 1` |
| Board | V400 | `#define V400 true` |
| Preheat | PID kiểu Artisan | `PREHEAT_USE_PID 1` |

Kết quả build đã flash (2026-07-09): RAM 80.8% (39700/49152 B), Flash 35.4% (92736/262144 B).

## Cách load lại

Đây khác preset khác **chỉ ở khối "Phần cứng/ngoại vi" và 2 dòng nguồn** trong [include/Config.h](include/Config.h). Chép khối dưới đè lên phần tương ứng, phần preheat/feeder giữ nguyên mặc định codebase, rồi build:

```bash
pio run -e genericSTM32F103RC
```

```cpp
// Phần cứng/ngoại vi có lắp trên máy
#define MACHINE_HAS_AIRFLOW_CONTROL       1  // Điều khiển gió bằng DAC/phần trăm gió
#define MACHINE_HAS_GAS_CONTROL           1  // Điều khiển gas bằng DAC và relay gas
#define MACHINE_HAS_DRUM_SPEED_CONTROL    1  // Điều khiển tốc độ drum bằng biến tần
#define MACHINE_HAS_AIR_INVERTER          1  // Biến tần quạt gió có nối RS485 Modbus (cần cho vacuum)
#define MACHINE_HAS_VACUUM_SENSOR         1  // Có cảm biến áp suất hút/vacuum, dùng PID gió
#define MACHINE_HAS_SCALE_FEEDER          0  // Có đầu cân Bluetooth cho auto loader
#define MACHINE_HAS_IO_RELAY_MODULE       1  // Có module relay ngoài qua Modbus
#define MACHINE_HAS_BT_TEMP_CONTROLLER    1  // Đồng hồ nhiệt BT có nối RS485 Modbus
#define MACHINE_HAS_ET_TEMP_CONTROLLER    1  // Đồng hồ nhiệt ET có nối RS485 Modbus
#define MACHINE_BATCH_KG                  3  // Khối lượng mẻ rang danh định (kg) — máy 3kg

// Nguồn đọc cảm biến vacuum: 0 = biến tần gió (slave 5), 1 = biến tần drum (slave 4)
#define MACHINE_VACUUM_FROM_DRUM          0

// Nguồn điều khiển SOURCE_AI_VR: 0 = VR vật lý, 1 = setpoint từ HMI
#define MACHINE_VR_SOURCE_FROM_HMI        1
```

## Lưu ý khi chạy máy thật

- **IO module bật** → node relay ngoài phải thực sự có ở Modbus ID 7 (baud 38400). Firmware đưa node này vào health-check lúc khởi động; thiếu sẽ báo `STARTUP_RELAY_FAIL`. Relay drum/fan (CH1) và mixer (CH2) đi qua module ngoài thay vì GPIO onboard.
- `MACHINE_VACUUM_FROM_DRUM 0` → cảm biến áp suất phải đấu vào ngõ ACI của **biến tần gió** (slave 5); PID gió đọc `AIR_INV_ACI_RAW_REGISTER` (8716).
- `MACHINE_HAS_SCALE_FEEDER 0` → nhánh auto-dif trong `Program.h` bị `#if (MACHINE_HAS_SCALE_FEEDER && FEEDER_ADAPT_EN)` tắt; ngưỡng `LOADER_MIN_NETW` tính theo 3kg nhưng không dùng đến.
