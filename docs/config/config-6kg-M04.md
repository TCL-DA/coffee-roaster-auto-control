# Cấu hình máy 6kg auto của M04, 2021

File này lưu snapshot cấu hình để copy vào `include/Config.h` khi build firmware cho máy 6kg auto 2021 của M04.

> **⚠️ CHƯA XÁC NHẬN PHẦN CỨNG:** Phần Config.h bên dưới chưa được điền — cần xác nhận
> hardware thực tế của máy (board version, thiết bị lắp) trước khi dùng để flash.
> Thermal model đã có từ đo thực (xem `analysis-roaster-thermal.md`).

---

## Thông tin máy

| Trường | Giá trị |
|--------|---------|
| Mã máy | M04 |
| Năm sản xuất | 2021 |
| Dung tích | 6 kg |
| Loại | Auto |
| Tình trạng config | 🔴 Chưa xác nhận hardware |

---

## Thermal model đo thực (không tải, 2026-05-07)

Nguồn: `analysis-roaster-thermal.md` — dữ liệu `testnhiet.csv`, 1884 điểm 1s.

| Tham số | Giá trị | Ghi chú |
|---------|---------|---------|
| Gas gain | ~1.5 °C/min per %Gas | Vùng BT 180–240°C; cao hơn khi giảm gas |
| Gas lag | 3–6s | |
| Gas time const | ~15s | |
| Air lag | 2–8s (tăng) / 8–10s (giảm) | |
| Air time const | ~20–25s | |
| Điểm cân bằng | Gas ~35%, Air ~18% → RoR_BT≈0 tại BT~215°C | Không tải |
| ET–BT correlation | r=0.767 tại lag=0 | ET không phải predictor tương lai của BT |

**Khi có sản phẩm (ước tính):** gas lag 15–25s, time const 45–75s, gain giảm còn 0.3–0.8.
Cần log mẻ rang thật để calibrate.

---

## Config.h — CẦN XÁC NHẬN PHẦN CỨNG TRƯỚC KHI DÙNG

> Cập nhật 2026-06-30: khối dưới là **toàn bộ Config.h** theo cấu trúc mới nhất nên copy đè cả file là build được ngay. Các dòng **phần cứng** vẫn còn `TODO` — phải xác nhận với máy thật rồi sửa trước khi flash. Phần preheat PID / feeder adapt / autotune để mặc định, tinh chỉnh sau khi đo mẻ thật.

```cpp
#pragma once

/*
 * Cấu hình máy rang
 * Cấu hình: máy 6kg auto 2021 của M04.
 *
 * TODO: xác nhận từng mục PHẦN CỨNG bên dưới với máy thực tế.
 */

// ---------------------------------------------------------------------------
// Phiên bản board phần cứng — TODO: xác nhận V300/V350/V400
// ---------------------------------------------------------------------------
// #define V300 true
// #define V350 true
#define V400 true  // TODO: xác nhận

// ---------------------------------------------------------------------------
// Phần cứng/ngoại vi — TODO: xác nhận từng mục theo dây đấu thực tế
// ---------------------------------------------------------------------------
#define MACHINE_HAS_AIRFLOW_CONTROL       1  // TODO: xác nhận
#define MACHINE_HAS_GAS_CONTROL           1  // TODO: xác nhận
#define MACHINE_HAS_DRUM_SPEED_CONTROL    0  // TODO: xác nhận (6kg có biến tần drum không?)
#define MACHINE_HAS_AIR_INVERTER          0  // TODO: xác nhận
#define MACHINE_HAS_VACUUM_SENSOR         0  // TODO: xác nhận
#define MACHINE_HAS_SCALE_FEEDER          0  // TODO: xác nhận
#define MACHINE_HAS_IO_RELAY_MODULE       0  // TODO: xác nhận
#define MACHINE_HAS_BT_TEMP_CONTROLLER    1  // TODO: xác nhận
#define MACHINE_HAS_ET_TEMP_CONTROLLER    1  // TODO: xác nhận
#define MACHINE_BATCH_KG                  6  // máy 6kg (dùng suy ngưỡng auto-loader nếu có cân)

// ---------------------------------------------------------------------------
// Baud rate — thường giữ nguyên trừ khi thiết bị khác
// ---------------------------------------------------------------------------
#define HMI_SERIAL_BAUD                   115200UL
#define MACHINE_RS485_BAUD                38400UL
#define DEBUG_SERIAL_BAUD                 9600UL
#define SCALE_SERIAL_BAUD                 2400UL
#define ARTISAN_MODBUS_BAUD_DEFAULT       9600UL

// ---------------------------------------------------------------------------
// Modbus ID — TODO: xác nhận địa chỉ slave thực tế của từng thiết bị
// ---------------------------------------------------------------------------
#define HMI_MODBUS_ID                     1
#define BT_TEMP_MODBUS_ID                 1
#define ET_TEMP_MODBUS_ID                 2
#define DRUM_INV_MODBUS_ID                4  // TODO: nếu có
#define AIR_INV_MODBUS_ID                 5  // TODO: nếu có
#define IO_RELAY_MODBUS_ID                7  // TODO: nếu có
#define ARTISAN_MODBUS_SLAVE_ID_DEFAULT   1

// ---------------------------------------------------------------------------
// Modbus register biến tần gió — TODO: xác nhận nếu có biến tần
// ---------------------------------------------------------------------------
#define AIR_INV_FREQ_READ_REGISTER        8451
#define AIR_INV_PID_0800_REGISTER         2048
#define AIR_INV_ACI_RAW_REGISTER          8716

// ---------------------------------------------------------------------------
// Nguồn đọc cảm biến vacuum (tín hiệu ACI):
//   0 = đọc từ biến tần quạt gió (slave 5, nodeAir) — mặc định
//   1 = đọc từ biến tần drum    (slave 4, nodeDrum)
// ---------------------------------------------------------------------------
#define MACHINE_VACUUM_FROM_DRUM          0

// ---------------------------------------------------------------------------
// Modbus register biến tần drum — TODO: xác nhận nếu có biến tần
// ---------------------------------------------------------------------------
#define DRUM_INV_FREQ_READ_REGISTER       8451
#define DRUM_INV_FREQ_WRITE_REGISTER      8193

#define MACHINE_VR_SOURCE_FROM_HMI        0

// ---------------------------------------------------------------------------
// AUTO-DIF FEEDER (chỉ dùng khi có cân) — để mặc định, tinh chỉnh sau.
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
// PREHEAT CONFIG — để mặc định; autotune sẽ tự tinh chỉnh theo gas gain máy 6kg.
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
#define PH_IGNITE_TMO                     65
#define PH_IGNITE_RETRY                   3

#if MACHINE_VR_SOURCE_FROM_HMI
#define SOURCE_AI_VR_FROM_HMI true
#endif
```

---

## Checklist trước khi flash

- [ ] Xác nhận board version (V300/V350/V400)
- [ ] Xác nhận có/không biến tần drum
- [ ] Xác nhận có/không biến tần gió + ID Modbus
- [ ] Xác nhận có/không cảm biến vacuum
- [ ] Xác nhận Modbus ID của từng thiết bị
- [ ] Chạy autotune PID preheat (máy Danh 6kg có gas gain khác máy Đức 12kg)
- [ ] Thu thập log mẻ rang có sản phẩm để calibrate thermal model
