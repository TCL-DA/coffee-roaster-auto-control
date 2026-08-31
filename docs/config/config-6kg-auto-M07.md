# Config preset — 6kg auto M07

Lưu ngày **2026-07-13**.

Máy rang **6kg auto** xuất Philippines — **không module IO relay ngoài**, **không cân serial** (feeder chạy theo timer), có **afterburner** + **destoner** (relay onboard), **vacuum đọc từ biến tần gió**, có **drum speed**, dùng **bếp premix** (mồi lửa chậm ~40s).

## Đặc thù cấu hình

| Mục | Giá trị | `#define` |
|-----|---------|-----------|
| Mẻ danh định | 6 kg | `MACHINE_BATCH_KG 6` |
| Điều khiển | **Có biến trở vật lý** | `MACHINE_VR_SOURCE_FROM_HMI 0` — drum/air/gas đọc từ VR trên board, không lấy từ HMI |
| **IO relay module** | **TẮT** | `MACHINE_HAS_IO_RELAY_MODULE 0` — relay đi qua GPIO onboard, không có node Modbus ngoài |
| **Afterburner** | **Có** | Relay onboard CH6 (`AB_BTN_R` → `CH6_RL`), không cần define riêng |
| **Destoner** | **Có** | Relay onboard CH7 (`DESTONER_BTN_R` → `CH7_RL`), không cần define riêng |
| Cân / auto-loader | **TẮT** | `MACHINE_HAS_SCALE_FEEDER 0` — feeder chạy theo timer, không đọc cân Bluetooth |
| Nguồn đọc vacuum | **Gió (slave 5)** | `MACHINE_VACUUM_FROM_DRUM 0` — cảm biến áp suất đấu vào ngõ ACI biến tần gió |
| Vacuum sensor | Có | `MACHINE_HAS_VACUUM_SENSOR 1`, PID gió |
| Air inverter | Có | `MACHINE_HAS_AIR_INVERTER 1` — RS485 Modbus, cần để đọc ACI vacuum |
| Drum speed | Có | `MACHINE_HAS_DRUM_SPEED_CONTROL 1` — biến tần drum |
| Gas / Airflow | Có | `MACHINE_HAS_GAS_CONTROL 1`, `MACHINE_HAS_AIRFLOW_CONTROL 1` |
| BT / ET thermocouple | Có | `MACHINE_HAS_BT_TEMP_CONTROLLER 1`, `MACHINE_HAS_ET_TEMP_CONTROLLER 1` |
| Board | V400 | `#define V400 true` |
| Preheat | PID kiểu Artisan | `PREHEAT_USE_PID 1` |
| **Bếp premix** | Mồi chậm | `PH_IGNITE_TMO 65` — premix mồi ~40s, nới timeout tránh báo lỗi mồi sai |

> **Ghi chú afterburner/destoner:** hai thiết bị này chạy qua relay onboard (CH6/CH7) trong
> `controlIO()`, **không** liên quan tới `MACHINE_HAS_IO_RELAY_MODULE`. Vì máy này TẮT IO module,
> toàn bộ relay (gas, cooling, charge, drop, escape, afterburner, destoner, feeder) đi qua GPIO
> onboard — đúng như mong muốn.

## Thermal model tham chiếu (máy 6kg)

Chưa có log mẻ rang thật của máy Philippines này. Lấy tạm thermal model máy 6kg trong
[analysis-roaster-thermal.md](../analysis/analysis-roaster-thermal.md) làm điểm khởi đầu
(gas gain ~1.5 °C/min/%, cân bằng gas~35% / air~18% @ BT~215°C, không tải). **Phải chạy
autotune PID preheat và thu log mẻ thật để calibrate lại** vì buồng đốt/gió mỗi máy khác nhau.

## Cách load lại

Chép **toàn bộ** khối dưới đè lên [include/Config.h](../../include/Config.h) rồi build:

```bash
pio run -e genericSTM32F103RC
```

```cpp
#pragma once

/*
 * Cấu hình máy rang
 * Cấu hình: máy 6kg auto xuất Philippines — không IO module, không cân serial,
 * có afterburner + destoner (relay onboard), vacuum đọc từ biến tần gió, có drum
 * speed, bếp premix. CÓ biến trở vật lý: gió/drum/gas đọc từ VR trên board.
 */

// ---------------------------------------------------------------------------
// Phiên bản board phần cứng. Chỉ bật đúng 1 dòng V300, V350 hoặc V400.
// ---------------------------------------------------------------------------
// #define V300 true
// #define V350 true
#define V400 true

// ---------------------------------------------------------------------------
// Phần cứng/ngoại vi có lắp trên máy.
// ---------------------------------------------------------------------------
#define MACHINE_HAS_AIRFLOW_CONTROL       1  // Điều khiển gió bằng DAC/phần trăm gió
#define MACHINE_HAS_GAS_CONTROL           1  // Điều khiển gas bằng DAC và relay gas
#define MACHINE_HAS_DRUM_SPEED_CONTROL    1  // Điều khiển tốc độ drum bằng biến tần
#define MACHINE_HAS_AIR_INVERTER          1  // Biến tần quạt gió có nối RS485 Modbus (cần cho vacuum)
#define MACHINE_HAS_VACUUM_SENSOR         1  // Có cảm biến áp suất hút/vacuum, dùng PID gió
#define MACHINE_HAS_SCALE_FEEDER          0  // KHÔNG cân Bluetooth — feeder chạy theo timer
#define MACHINE_HAS_IO_RELAY_MODULE       0  // KHÔNG module relay ngoài — relay qua GPIO onboard
#define MACHINE_HAS_BT_TEMP_CONTROLLER    1  // Đồng hồ nhiệt BT có nối RS485 Modbus
#define MACHINE_HAS_ET_TEMP_CONTROLLER    1  // Đồng hồ nhiệt ET có nối RS485 Modbus
#define MACHINE_BATCH_KG                  6  // Khối lượng mẻ rang danh định (kg) — máy 6kg

// ---------------------------------------------------------------------------
// Tốc độ truyền serial.
// ---------------------------------------------------------------------------
#define HMI_SERIAL_BAUD                   115200UL
#define MACHINE_RS485_BAUD                38400UL
#define DEBUG_SERIAL_BAUD                 9600UL
#define SCALE_SERIAL_BAUD                 2400UL
#define ARTISAN_MODBUS_BAUD_DEFAULT       9600UL

// ---------------------------------------------------------------------------
// Địa chỉ ID Modbus của từng thiết bị.
// ---------------------------------------------------------------------------
#define HMI_MODBUS_ID                     1  // HMI Delta
#define BT_TEMP_MODBUS_ID                 1  // Đồng hồ nhiệt BT
#define ET_TEMP_MODBUS_ID                 2  // Đồng hồ nhiệt ET
#define DRUM_INV_MODBUS_ID                4  // Biến tần drum
#define AIR_INV_MODBUS_ID                 5  // Biến tần quạt gió
#define IO_RELAY_MODBUS_ID                7  // Module relay ngoài (không dùng — IO tắt)
#define ARTISAN_MODBUS_SLAVE_ID_DEFAULT   1  // ID slave để Artisan/PC đọc Arduino

// ---------------------------------------------------------------------------
// Địa chỉ thanh ghi Modbus của biến tần quạt gió.
// ---------------------------------------------------------------------------
#define AIR_INV_FREQ_READ_REGISTER        8451
#define AIR_INV_PID_0800_REGISTER         2048
#define AIR_INV_ACI_RAW_REGISTER          8716

// ---------------------------------------------------------------------------
// Nguồn đọc cảm biến vacuum (tín hiệu ACI):
//   0 = đọc từ biến tần quạt gió (slave 5, nodeAir) — cấu hình này
//   1 = đọc từ biến tần drum    (slave 4, nodeDrum)
// ---------------------------------------------------------------------------
#define MACHINE_VACUUM_FROM_DRUM          0

// ---------------------------------------------------------------------------
// Địa chỉ thanh ghi Modbus của biến tần drum.
// ---------------------------------------------------------------------------
#define DRUM_INV_FREQ_READ_REGISTER       8451
#define DRUM_INV_FREQ_WRITE_REGISTER      8193

// ---------------------------------------------------------------------------
// Nguồn điều khiển khi chọn SOURCE_AI_VR.
// 0 = đọc VR vật lý trên chân analog của board.
// 1 = lấy setpoint từ HMI: airSpeed_R, drumSpeed_R, burnerValue_R.
// ---------------------------------------------------------------------------
#define MACHINE_VR_SOURCE_FROM_HMI        0  // máy có biến trở vật lý — drum/air/gas đọc từ VR trên board

// ---------------------------------------------------------------------------
// TREND bật SỚM trước charge (đơn vị 0.1°C).
// ---------------------------------------------------------------------------
#define TREND_PRECHARGE_BAND              100

// ---------------------------------------------------------------------------
// AUTO-DIF FEEDER — không dùng (không cân), để mặc định.
// ---------------------------------------------------------------------------
#define FEEDER_TKG_DEFAULT                190
#define FEEDER_DIF_MAX                    25
#define FEEDER_ADAPT_EN                   1
#define FEEDER_ADAPT_GAIN                 30
#define FEEDER_CFG_MAX                    48
#define FEEDER_W_BUCKET                   5
#define FEEDER_ROR_BUCKET10              25
#define FEEDER_SEED_WKG                  100
#define FEEDER_TKG_MIN                    20
#define FEEDER_TKG_MAX                    1000
#define FEEDER_STABLE_ROR                 20
#define FEEDER_SETTLE_TMO                 15
#define FEEDER_SETTLE_MIN_MS              1500
#define FEEDER_WSTART_DELAY_MS            3000
#define FEEDER_OFFSET_MAX100              30
#define LOADER_CSV_MAX                    400
#define FEEDER_MIN_BATCH100               50
#define LOADER_MIN_BATCH_PCT              80
#define LOADER_MIN_NETW                   (MACHINE_BATCH_KG * LOADER_MIN_BATCH_PCT / 10)

// ---------------------------------------------------------------------------
// Debug (production = 0)
// ---------------------------------------------------------------------------
#define PREHEAT_DEBUG_EN                  0
#define PIDTUNE_DEBUG_EN                  0

// ===========================================================================
// PREHEAT CONFIG — để mặc định; autotune tự tinh chỉnh theo gas gain máy 6kg.
// ===========================================================================
#define PREHEAT_USE_PID                   1

#define PH_PID_KP                         15000
#define PH_PID_KI                         150
#define PH_PID_KD                         20000
#define PH_PID_KP_HOLD                    5000
#define PH_PID_KI_HOLD                    100
#define PH_PID_KD_HOLD                    15000
#define PH_PID_IMAX                       100
#define PH_PID_EVAL_SEC                   1
#define PH_PID_LOOKAHEAD_SEC              6
#define PH_PID_BETA                       95
#define PH_PID_DLIMIT                     1000
#define PH_EMA_D_ALPHA                    40
#define PH_EMA_OUT_ALPHA                  75

#define PH_TUNE_GAS_HI                    25
#define PH_TUNE_GAS_LO                    0
#define PH_TUNE_AIR_HI                    20
#define PH_TUNE_AIR_LO                    100
#define PH_TUNE_CYCLES                    2
#define PH_TUNE_PEAK_MIN                  5
#define PH_TUNE_TIMEOUT_SEC               600
#define PH_TUNE_STUCK_SEC                 75
#define PH_TUNE_LOWPV_EN                  1
#define PH_TUNE_FRL                       -2000
#define PH_TUNE_HOLD_DEV                  20
#define PH_HOLD_SETTLE_SEC                45
#define PH_SV_TABLE_MAX                   8
#define PH_SV_MATCH                       150

#define PH_DIVERGE_LIMIT                  1600
#define PH_PID_OVERHEAT_GUARD             150
#define PH_PURGE_MS                       8000UL

#define PH_HEAT_STEP                      10
#define PH_GD4_ROR_LO                     1
#define PH_GD4_ROR_HI                     3
#define PH_GD4_STEP                       5
#define PH_GD4_DEAD                       1
#define PH_WARN_BAND                      50
#define PH_WARN_COOLDOWN                  10
#define PH_FC_WIN_SEC                     5
#define PH_FC_AHEAD_SEC                   60
#define PH_FC_SAFE_BAND                   100
#define PH_DSLOPE_GATE                    5
#define PH_HOLD_EXTRA_SEC                 900
#define PH_HOLD_BAND_NEAR                 30
#define PH_HOLD_BAND_FAR                  50
#define PH_FC_EMERGENCY_SEC               15
#define PH_EMERGENCY_STEP                 15
#define PH_DEADLINE_SEC                   180
#define PH_DEADLINE_STEP                  10
#define PH_DL_RATIO_LO                    80
#define PH_DL_RATIO_HI                    120
#define PH_OVER_ROR_LO                   -3
#define PH_OVER_ROR_HI                   -1
#define PH_OVER_STEP                      5
#define PH_BT_PHASE2                      1000
#define PH_APPROACH_BAND                  250
#define PH_TARGET_BAND                    30
#define PH_GAS_EVAL_SEC                   5
#define PH_AIR_COOLDOWN                   10
#define PH_AIR_BASE                       20
#define PH_AIR_PURGE                      60
#define PH_IGNITE_TMO                     65    // bếp premix mồi chậm ~40s — nới timeout
#define PH_IGNITE_RETRY                   3

#if MACHINE_VR_SOURCE_FROM_HMI
#define SOURCE_AI_VR_FROM_HMI true
#endif
```

## Checklist trước khi flash

- [ ] Xác nhận board V400 đúng phần cứng
- [ ] Biến tần gió ở Modbus ID 5, baud 38400; cảm biến vacuum đấu ngõ ACI biến tần gió (reg 8716)
- [ ] Biến tần drum ở Modbus ID 4
- [ ] Không có node relay ID 7 (IO module tắt) — không đưa vào health-check
- [ ] Afterburner đấu relay onboard CH6, destoner CH7 — kiểm tra dây đúng kênh
- [ ] Feeder chạy theo timer (không cân) — kiểm tra thời gian đóng/mở cửa nạp
- [ ] Chạy autotune PID preheat trên máy này (gas gain riêng)
- [ ] Thu log mẻ rang có sản phẩm để calibrate thermal model

## Lưu ý khi chạy máy thật

- `MACHINE_HAS_IO_RELAY_MODULE 0` → firmware **không** health-check node relay ID 7; mọi relay đi qua GPIO onboard. Nếu vô tình để `1` mà không lắp module sẽ báo `STARTUP_RELAY_FAIL`.
- `MACHINE_HAS_SCALE_FEEDER 0` → nhánh auto-dif trong `Program.h` bị `#if (MACHINE_HAS_SCALE_FEEDER && FEEDER_ADAPT_EN)` tắt; feeder điều khiển bằng timer, không đọc cân.
- `MACHINE_VACUUM_FROM_DRUM 0` → cảm biến áp suất phải đấu vào ngõ ACI của **biến tần gió** (slave 5); PID gió đọc `AIR_INV_ACI_RAW_REGISTER` (8716).
- Bếp premix mồi chậm: `PH_IGNITE_TMO 65` cho phép ~40s mồi lửa; nếu bếp mồi nhanh hơn có thể hạ lại 60.
