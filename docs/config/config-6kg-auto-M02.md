# Config preset — 6kg M02

Lưu ngày **2026-08-20**.

Máy rang **6kg M02**, board **V300**. **KHÔNG drum control**, **KHÔNG vacuum
control**, **KHÔNG cân loader**. Relay đi qua GPIO onboard (không module IO ngoài), gas/gió
điều khiển bằng DAC, đọc mức từ **biến trở vật lý** trên board.

## Đặc thù cấu hình

| Mục | Giá trị | `#define` |
|-----|---------|-----------|
| Board | **V300** | `#define V300 true` — V300 đảo cổng: `SerialModbus = Serial4 (UART4)`, `SerialComputer = Serial2 (USART2)`, HMI vẫn Serial1. Thang ADC VR max 630 count |
| Mẻ danh định | 6 kg | `MACHINE_BATCH_KG 6` |
| **Drum speed** | **TẮT** | `MACHINE_HAS_DRUM_SPEED_CONTROL 0` — không biến tần drum, `drumPercent` bị ép 0, không ghi node 4 |
| **Vacuum** | **TẮT** | `MACHINE_HAS_VACUUM_SENSOR 0` — không cảm biến áp hút, **không chạy PID gió theo vacuum**; gió chạy theo % đặt |
| **Air inverter (RS485)** | **TẮT** | `MACHINE_HAS_AIR_INVERTER 0` — chỉ cần khi đọc ACI vacuum. Gió vẫn điều khiển bằng DAC 0–10V |
| **Cân / auto-loader** | **TẮT** | `MACHINE_HAS_SCALE_FEEDER 0` — feeder chạy theo timer, không đọc cân |
| IO relay module | TẮT | `MACHINE_HAS_IO_RELAY_MODULE 0` — toàn bộ relay qua GPIO onboard CH1–CH8 |
| Điều khiển | Có biến trở vật lý | `MACHINE_VR_SOURCE_FROM_HMI 0` — gió/gas đọc VR trên board |
| Gas / Airflow | Có | `MACHINE_HAS_GAS_CONTROL 1`, `MACHINE_HAS_AIRFLOW_CONTROL 1` |
| BT / ET thermocouple | Có | `MACHINE_HAS_BT_TEMP_CONTROLLER 1` (ID 1), `MACHINE_HAS_ET_TEMP_CONTROLLER 1` (ID 2) |
| Preheat | PID kiểu Artisan | `PREHEAT_USE_PID 1`; loại đầu đốt chọn runtime bằng `burnerPremix_R` ($M addr 29) |

**Bus RS485 còn lại chỉ 2 node**: BT (ID 1) và ET (ID 2) — bỏ hẳn drum (4), gió (5), IO (7)
→ vòng quét nhẹ hơn hẳn so với các máy full option.

## Kết quả build

```
pio run -e genericSTM32F103RC
RAM:   81.4% (40012 / 49152 B)
Flash: 38.3% (100396 / 262144 B)
[SUCCESS]
```

Đã build ngày 2026-08-20 — **CHƯA FLASH, CHƯA test trên máy thật**.

## Việc cần kiểm khi lắp máy

- Board V300 dùng **Serial2 làm cổng debug** (không phải UART4 như V400) — cắm đúng chân khi
  monitor 9600 baud.
- Thang ADC biến trở V300 = **630 count** (`CH1AInMax`/`CH2AInMax`/`CH3AInMax`), khác V400 (650).
  Nếu VR không lên nổi 100% thì hiệu chỉnh lại phần này.
- Baud Modbus Artisan mặc định đang **9600** (`ARTISAN_MODBUS_BAUD_DEFAULT`) — HMI ghi đè được
  bằng `modbusBaud_R`.
- Preheat PID chưa calibrate cho buồng đốt M02 — chạy autotune + lấy log mẻ thật.

## Cách load lại

Chép **toàn bộ** khối dưới đè lên [include/Config.h](../../include/Config.h) rồi build:

```bash
pio run -e genericSTM32F103RC
```

```cpp
#pragma once

/*
 * Cấu hình máy rang
 * Cấu hình hiện tại: máy rang 6kg M02 — board V300. KHÔNG drum control,
 * KHÔNG vacuum control (không cảm biến áp hút, không PID gió), KHÔNG cân loadcell/auto-loader,
 * không IO module (relay onboard). Gas/gió điều khiển bằng DAC; đọc từ biến trở vật lý trên board.
 *
 * Đổi file này khi build firmware cho từng model máy rang khác nhau.
 * Các tùy chọn dạng bật/tắt nên giữ giá trị 0/1, trừ khi dòng chú thích
 * nói rõ cách dùng khác.
 */

// ---------------------------------------------------------------------------
// Phiên bản board phần cứng.
// Chỉ được bật đúng 1 dòng V300, V350 hoặc V400.
// ---------------------------------------------------------------------------
#define V300 true
// #define V350 true
// #define V400 true

// ---------------------------------------------------------------------------
// Phần cứng/ngoại vi có lắp trên máy.
// 1 = có lắp và firmware sẽ đọc/ghi thiết bị đó.
// 0 = không lắp, firmware bỏ qua các luồng chính liên quan.
// ---------------------------------------------------------------------------
#define MACHINE_HAS_AIRFLOW_CONTROL       1  // Điều khiển gió bằng DAC/phần trăm gió
#define MACHINE_HAS_GAS_CONTROL           1  // Điều khiển gas bằng DAC và relay gas
#define MACHINE_HAS_DRUM_SPEED_CONTROL    0  // KHÔNG điều khiển tốc độ drum (drum chạy trực tiếp)
#define MACHINE_HAS_AIR_INVERTER          0  // KHÔNG đọc biến tần gió qua RS485 (chỉ cần khi có vacuum)
#define MACHINE_HAS_VACUUM_SENSOR         0  // KHÔNG cảm biến áp hút — tắt PID gió theo vacuum
#define MACHINE_HAS_SCALE_FEEDER          0  // KHÔNG cân loadcell — feeder chạy theo timer
#define MACHINE_HAS_IO_RELAY_MODULE       0  // KHÔNG module relay ngoài — relay qua GPIO onboard
#define MACHINE_HAS_BT_TEMP_CONTROLLER    1  // Đồng hồ nhiệt BT có nối RS485 Modbus
#define MACHINE_HAS_ET_TEMP_CONTROLLER    1  // Đồng hồ nhiệt ET có nối RS485 Modbus
#define MACHINE_BATCH_KG                  6  // Khối lượng mẻ rang danh định (kg) — máy 6kg M02
// Loại đầu đốt do HMI chọn lúc chạy qua thanh ghi burnerPremix_R (địa chỉ 29):
//   0 = đầu đốt thường (khuếch tán), 1 = đầu đốt premix (khí+gió trộn sẵn).
// KHÔNG có cờ compile — 1 firmware chạy cả 2 loại. Bộ tham số preheat tự đổi theo
// burnerPremix_R trong Preheat_PID.h (xem cặp PH_*_PREMIX bên dưới + docs/config/config-preheat-premix.md).

// ---------------------------------------------------------------------------
// Tốc độ truyền serial.
// HMI_SERIAL_BAUD: cổng HMI Delta.
// MACHINE_RS485_BAUD: bus RS485 nối đồng hồ nhiệt, biến tần, module relay.
// DEBUG_SERIAL_BAUD: cổng debug/monitor máy tính.
// SCALE_SERIAL_BAUD: đầu cân Bluetooth.
// ARTISAN_MODBUS_BAUD_DEFAULT: baud mặc định cho Modbus slave Artisan
//                              khi HMI chưa cài modbusBaud_R.
// ---------------------------------------------------------------------------
#define HMI_SERIAL_BAUD                   115200UL
#define MACHINE_RS485_BAUD                38400UL
#define DEBUG_SERIAL_BAUD                 9600UL
#define SCALE_SERIAL_BAUD                 2400UL
#define ARTISAN_MODBUS_BAUD_DEFAULT       9600UL    // CMS 12kg Auto — CHƯA XÁC NHẬN (bản 6kg dùng 38400); HMI cài modbusBaud_R vẫn ghi đè được

// ---------------------------------------------------------------------------
// Địa chỉ ID Modbus của từng thiết bị.
// Lưu ý: đây là ID slave trên đường Modbus, không phải địa chỉ thanh ghi.
// ---------------------------------------------------------------------------
#define HMI_MODBUS_ID                     1  // HMI Delta
#define BT_TEMP_MODBUS_ID                 1  // Đồng hồ nhiệt BT
#define ET_TEMP_MODBUS_ID                 2  // Đồng hồ nhiệt ET
#define DRUM_INV_MODBUS_ID                4  // Biến tần drum
#define AIR_INV_MODBUS_ID                 5  // Biến tần quạt gió
#define IO_RELAY_MODBUS_ID                7  // Module relay ngoài
#define ARTISAN_MODBUS_SLAVE_ID_DEFAULT   1  // ID slave để Artisan/PC đọc Arduino

// ---------------------------------------------------------------------------
// Địa chỉ thanh ghi Modbus của biến tần quạt gió.
// AIR_INV_FREQ_READ_REGISTER: đọc tần số hiện tại của biến tần gió.
// AIR_INV_PID_0800_REGISTER: đọc thanh ghi PID/parameter 0800 của biến tần gió.
// AIR_INV_ACI_RAW_REGISTER: đọc tín hiệu analog ACI nối cảm biến vacuum.
//                           Biến tần hiện tại trả về dải 0..10000 tại địa chỉ 8716.
// ---------------------------------------------------------------------------
#define AIR_INV_FREQ_READ_REGISTER        8451
#define AIR_INV_PID_0800_REGISTER         2048
#define AIR_INV_ACI_RAW_REGISTER          8716

// ---------------------------------------------------------------------------
// Nguồn đọc cảm biến vacuum (tín hiệu ACI):
//   0 = đọc từ biến tần quạt gió (slave 5, nodeAir) — mặc định
//   1 = đọc từ biến tần drum    (slave 4, nodeDrum)
// Dùng khi cảm biến áp suất nối vào ngõ analog ACI của biến tần drum thay vì quạt
// gió. Cùng địa chỉ thanh ghi (AIR_INV_ACI_RAW_REGISTER) vì 2 biến tần cùng model.
// ---------------------------------------------------------------------------
#define MACHINE_VACUUM_FROM_DRUM          0

// ---------------------------------------------------------------------------
// Địa chỉ thanh ghi Modbus của biến tần drum.
// DRUM_INV_FREQ_READ_REGISTER: đọc tần số hiện tại của biến tần drum.
// DRUM_INV_FREQ_WRITE_REGISTER: ghi tần số đặt cho biến tần drum.
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
// TREND bật SỚM trước charge.
// Sau khi bật lửa, BT tăng dần tới charge; khi BT còn cách charge ngưỡng này
// thì bật ghi trend (để đồ thị có sẵn đoạn tiến tới charge, giống Artisan).
// Đơn vị 0.1°C: 100 = 10°C, 150 = 15°C.
// ---------------------------------------------------------------------------
#define TREND_PRECHARGE_BAND              100

// ---------------------------------------------------------------------------
// AUTO-DIF FEEDER — đóng feeder sớm, tính theo VẬT LÝ (tốc độ hút × lượng cà):
//   dif (kg) = |rorKG| (kg/phút) × T_kg (ms/kg) × wStart (kg) / 60000
// Lý do: cà rơi tiếp trong lúc xi lanh đóng + cà lơ lửng gần cửa (cân giả). Cả 2 tỉ lệ
// tốc độ hút; thời gian hiệu dụng lại tỉ lệ LƯỢNG CÀ (cột cà nặng → trễ/cân giả lớn hơn).
// → gộp thành T_kg = thời gian hiệu dụng trên mỗi kg cà. Hút làm cân giảm → rorKG ÂM → |.|.
// FEEDER_TKG_DEFAULT = T_kg khởi đầu (×10 ms/kg); sau đó TỰ HỌC. 190 = 19.0 ms/kg.
// FEEDER_DIF_MAX = trần an toàn dif (×10 kg), chặn đóng quá sớm nếu rorKG vọt bất thường.
// ---------------------------------------------------------------------------
#define FEEDER_TKG_DEFAULT                190   // ×10 ms/kg (19.0) — KHỞI ĐẦU; sau tự học
#define FEEDER_DIF_MAX                    25    // trần dif ×10 (2.5 kg) — dư rộng sau khi nâng trần ror lên 60 kg/phút

// ---------------------------------------------------------------------------
// TỰ HỌC dif theo BẢNG điểm vận hành (cân, ror) — thay cho việc học 1 số T_kg.
// Mỗi mẻ hút: snap (cân, ror) về ô lưới rồi so final vs target:
//   - đạt (|lệch| ≤ ~0.09kg) → giữ nguyên dif của ô (deadband)
//   - lệch → kéo dif của ô về phía "dif lẽ ra đúng" (EMA theo GAIN)
// Bảng lưu /loadcfg.csv trên SD (tên 8.3 vì SD@1.2.4 không nhận tên dài; sống qua tắt nguồn), nạp TOÀN BỘ vào RAM lúc boot.
// Ô chưa học → mượn ô đã học gần nhất; bảng rỗng hoàn toàn → công thức T_kg ở trên làm default.
// Đọc "final" khi cân ổn định (|rorKG| ≤ STABLE) sau tối thiểu SETTLE_MIN_MS, timeout SETTLE_TMO.
// ---------------------------------------------------------------------------
#define FEEDER_ADAPT_EN                   1     // 1 = bật tự học dif
#define FEEDER_ADAPT_GAIN                 30    // ×100: 30 = EMA kéo 0.30/mẻ về dif đúng
#define FEEDER_CFG_MAX                    48    // số ô (điểm vận hành) tối đa giữ trong loadcfg.csv
#define FEEDER_W_BUCKET                   5     // bước lưới cân (kg) — snap cân về bội số này
#define FEEDER_ROR_BUCKET10              25     // bước lưới ror (×10 kg/phút = 2.5) — snap ror về bội số này
#define FEEDER_SEED_WKG                  100    // cân tham chiếu (kg) để nội suy dif mặc định khi CHƯA có file (chỉnh được)
#define FEEDER_TKG_MIN                    20    // kẹp dưới T_kg default fallback (×10 = 2.0)
#define FEEDER_TKG_MAX                    1000  // kẹp trên T_kg default fallback (×10 = 100.0)
#define FEEDER_STABLE_ROR                 20    // |rorKG| ≤ (×100, 0.2kg/ph) coi cân ổn định
#define FEEDER_SETTLE_TMO                 15    // timeout chờ ổn định (giây)
#define FEEDER_SETTLE_MIN_MS              1500  // chờ tối thiểu sau cắt cho cà lắng (ms)
#define FEEDER_WSTART_DELAY_MS            3000  // chờ sau khi bật hút rồi mới chốt wStart (ms):
                                                // lực hút ổn định ~2-3s; PHẢI chốt TRƯỚC khi cửa xả mở
                                                // (cửa mở ~5s, cà rớt) nếu không sẽ chốt nhằm lúc giao thời
#define FEEDER_OFFSET_MAX100              30    // ×100 kg: trần offset lực hút hợp lệ (0.30kg),
                                                // kẹp để mẫu đo lỗi không làm cắt quá sớm/muộn
// Log loader ra SerialComputer KHÔNG cần bật enDebug toàn cục (bản đi khảo sát sai lệch hút
// liệu 2026-08-17). In 1 dòng/giây CHỈ trong lúc nút feeder bật → không nặng vòng quét.
// Đặt về 0 khi giao máy production.
#define LOADER_DEBUG_EN                   0

// ── THẺ SD: chống treo máy (2026-08-17, sau ca treo giữa lúc hút) ───────────
// LOADER_SD_LOG_EN: 0 = loader KHÔNG đụng thẻ SD nữa (không ghi loader.csv, không trim).
//   Với dif cố định thì log này chỉ để xem, KHÔNG tham gia điều khiển — bỏ đi thì đường
//   hút liệu sạch bóng thao tác thẻ, thẻ dở chứng cũng không kéo được vòng quét.
//   Cần xem lại thì bật 1 (và nên bật LOADER_DEBUG_EN thay vì ghi thẻ).
// SD_INIT_RETRY: số lần thử khởi tạo thẻ lúc boot. HẾT lượt thì BÁO LỖI RỒI CHẠY TIẾP,
//   KHÔNG treo máy — mất log còn hơn mất cả ngày rang. (Trước đây while(!SD.begin())
//   quay vô hạn kèm còi → thẻ chết là máy không vào nổi chương trình.)
// SD_RETRY_MS: lúc chạy, thẻ hỏng thì cứ chừng này ms thử khởi tạo lại một lần.
#define LOADER_SD_LOG_EN                  0
#define SD_INIT_RETRY                     5
#define SD_RETRY_MS                       10000UL

// ── dif CỐ ĐỊNH (2026-08-17) ────────────────────────────────────────────────
// >0  = dùng thẳng số này làm dif (×100 kg), BỎ QUA bảng /loadcfg.csv lẫn công thức T_kg,
//       và KHÔNG học/ghi bảng nữa. Hằng số nên ngưỡng cắt đứng yên suốt mẻ.
// 0   = quay lại y hệt hành vi cũ (tra bảng + tự học). Đổi 1 số này là lùi được ngay.
//
// Vì sao 100 (=1.00 kg): coast — lượng cà còn rời phễu SAU lệnh cắt — đo trên 7 mẻ log
// serial ngày 2026-08-17 ra 0.94/0.98/0.98/0.98/1.00/1.04/1.08 → trung bình đúng 1.00,
// lệch chuẩn 0.05. Suy ngược từ 18 lần cân tay của thợ rang (mức 5/10/20 kg) cũng khớp:
// coast ≈ 1.00 ở CẢ BA mức. Sai số = dif − coast, nên dif = 1.00 → sai số ≈ 0.
//
// NGHIỆM THU TRÊN MÁY 2026-08-17 (7 mẻ, mức 15 và 20 kg): lệch +3/−2/−1/+10/−3/+2/−1
// (×0.01 kg) → 6/7 mẻ dưới 30 gam, tệ nhất 100 gam, điểm trung bình 9.7. Trước khi sửa:
// điểm 2.6–9.7, lệch tới 760 gam. dif in ra đứng yên suốt mẻ, ngưỡng cắt hết dao động.
//
// CHỈNH KHI LỆCH ĐỀU MỘT CHIỀU: hút thiếu → giảm số này; hút dư → tăng. Đúng bằng lượng
// lệch (0.20 kg = 20). KHÔNG cần đụng gì khác.
#define FEEDER_DIF_FIXED                  100
#define LOADER_CSV_MAX                    400   // số dòng hút gần nhất tối đa giữ trong loader.csv
#define FEEDER_MIN_BATCH100               50    // ×100 kg: mẻ hút nhỏ hơn 0.5kg coi là nhiễu → bỏ học+log (mẻ thật tối thiểu 1kg)
// Ngưỡng cho auto-loader chạy: phễu nguồn phải còn ≥ LOADER_MIN_BATCH_PCT% của 1 mẻ rang.
// netW đơn vị ×10 kg → ngưỡng = MACHINE_BATCH_KG × pct / 10. Máy 12kg @80% = 12×80/10 = 96 (9.6kg).
#define LOADER_MIN_BATCH_PCT              80    // % mẻ tối thiểu trong phễu nguồn mới cho auto-loader chạy
#define LOADER_MIN_NETW                   (MACHINE_BATCH_KG * LOADER_MIN_BATCH_PCT / 10)  // ×10 kg, suy từ batch

// ---------------------------------------------------------------------------
// Debug preheat riêng — cần enDebug=1 VÀ cờ này=1 mới in.
// 1 = in serial log preheat (APPR, HOLD_REC, PREC, MON...)
// 0 = im lặng hoàn toàn
// ---------------------------------------------------------------------------
#define PREHEAT_DEBUG_EN                  0

// ---------------------------------------------------------------------------
// Debug factory auto-tune PID gió — cần enDebug=1 VÀ cờ này=1 mới in.
// 1 = in heartbeat [PIDTUNE] mỗi giây + FT Air=/Snap calc khi đang tune
// 0 = im lặng (mặc định) — khi cần debug tune thì bật lên
// ---------------------------------------------------------------------------
#define PIDTUNE_DEBUG_EN                  0

// ===========================================================================
// PREHEAT CONFIG — Toàn bộ tham số điều khiển preheat
// Chỉnh ở đây, KHÔNG sửa trực tiếp Preheat.h / Preheat_PID.h
// ===========================================================================

// ---------------------------------------------------------------------------
// CHỌN LOẠI PREHEAT (chọn lúc build, mỗi firmware 1 loại):
//   0 = RoR-based forecast 4 giai đoạn  → include/Preheat.h
//   1 = PID cổ điển (BT→SV, gas+/air−)  → include/Preheat_PID.h
// ---------------------------------------------------------------------------
#define PREHEAT_USE_PID                   1

// ---------------------------------------------------------------------------
// PID PREHEAT (chỉ dùng khi PREHEAT_USE_PID = 1)
// kp/ki/kd ×1000 để tính số nguyên (không FPU). Output = gas% (dương) / air% (âm).
//   kp=15.0 → PH_PID_KP=15000 ; ki=0.01 → PH_PID_KI=10 ; kd=20.0 → PH_PID_KD=20000
// Sai số e tính bằng 0.1°C (như BT). out = (kp·e + ki·∫e + kd·de/dt) / 1000.
// ---------------------------------------------------------------------------
// Bộ hệ số HEATING: BT đang lên, cần phản ứng mạnh theo tiến độ
#define PH_PID_KP                         15000  // ×1000
#define PH_PID_KI                         150    // ×1000 (0.15 — đủ lớn để I kéo BT tới target, không kẹt)
#define PH_PID_KD                         20000  // ×1000
// Bộ hệ số HOLDING: BT đã đạt target, chỉ cần giữ yên — Kp nhỏ hơn tránh dao động,
// Ki lớn hơn để triệt tiêu lệch tĩnh, Kd lớn hơn để chặn BT trôi.
// HOLD gains: bộ THƯỜNG (đầu đốt khuếch tán). Bộ PREMIX ở cặp PH_*_PREMIX bên dưới,
// Preheat_PID.h chọn theo burnerPremix_R lúc bắt đầu preheat.
#define PH_PID_KP_HOLD                    5000   // ×1000 (kéo về SV, không bão hòa output ở lệch nhỏ → hết đập gas 0↔100)
#define PH_PID_KI_HOLD                    100    // ×1000 (0.10 — triệt lệch tĩnh chậm rãi, chống windup)
#define PH_PID_KD_HOLD                    15000  // ×1000 (dập dao động vừa đủ, bớt D giật so với 35000)
// PREMIX: turndown hẹp → P/D mạnh đập gas 0↔35 gây limit-cycle khi giữ.
// 3500/10000 vẫn còn ±6°C → hạ dứt khoát xuống 2000/6000 để cắt vòng rung (log 2026-07-13)
#define PH_PID_KP_HOLD_PREMIX             2000   // ×1000
#define PH_PID_KD_HOLD_PREMIX             6000   // ×1000
#define PH_PID_IMAX                       100    // kẹp tích phân (đơn vị output %)
#define PH_PID_EVAL_SEC                   1      // chu kỳ tính PID (giây)
// Lookahead (giây): SV hiệu dụng = điểm trên đường tiến độ tại (elapsed + lookahead).
// Giống Artisan "Lookahead 6s" — PID nhìn trước để phản ứng sớm, không đợi BT lệch.
// Chỉ áp dụng trong giai đoạn HEATING (đang lên); HOLDING dùng SV cố định = target.
#define PH_PID_LOOKAHEAD_SEC              6      // giây nhìn trước (Artisan mặc định 6s)
// beta — 2DOF P weighting (Artisan: beta, VX4: ALPHA ngược chiều).
// P = Kp × (beta × SV_eff − BT).  beta=100 → P on Error (mặc định PID thường).
// beta<100 → P term nhẹ hơn khi BT còn xa SV → giảm vọt đầu quá trình.
// Artisan mặc định beta=1.0 (=100). VX4 ALPHA=50% ≈ beta=50.
// Khuyên dùng 70-80 cho máy rang gas quán tính lớn.
// Đơn vị ×100 để tính số nguyên: 100 = 1.0, 70 = 0.70.
#define PH_PID_BETA                       95     // ×100 (0.95 — P kéo tới ~SV, chỉ giảm nhẹ sát đích)

// Tinh chỉnh derivative theo Artisan pid.py (DoM = derivative on measurement):
// D tính trên BT, không trên sai số → khi SV cố định, derror = −RoR (chống kick).
// PH_PID_DLIMIT: kẹp |derror| (0.1°C/giây) chống D giật khi BT nhảy.
// Discontinuity: nếu |ΔBT| hiện tại > 2.5× trung bình 4 mẫu gần & > 1.0°C
//                → coi là spike nhiễu, giảm D còn 30%.
#define PH_PID_DLIMIT                     1000   // 100°C/s (0.1°C/giây)

// EMA filter (thay IIR scipy của Artisan) — hệ số α ×100, α = alpha/100.
// α lớn → phản ứng nhanh; α nhỏ → mượt hơn. Artisan dùng Wn≈0.1Hz (≈α≈0.4) cho D
// và Wn≈0.35Hz (≈α≈0.75) cho output. Giá trị mặc định phù hợp chu kỳ 1s.
#define PH_EMA_D_ALPHA                    40     // α×100 cho D term  (0.40 ≈ Artisan D filter)
#define PH_EMA_OUT_ALPHA                  75     // α×100 cho output (0.75 ≈ Artisan). ĐỪNG hạ: thử 0.50 gây thêm trễ pha → BT limit-cycle ±5°C (log 2026-07-13)

// ---------------------------------------------------------------------------
// RELAY AUTOTUNE (Ziegler-Nichols) — chỉ chạy khi /pid_pre.txt CHƯA có trên SD.
// Cho gas dao động 2 mức quanh SV_tune để đo → tính kp/ki/kd → lưu SD.
//   BT < SV_tune → gas = PH_TUNE_GAS_HI ; BT > SV_tune → gas = 0 + gió mạnh
//   Ku = 4·d/(π·a) ; Kp = 0.6·Ku ; Ki = 2·Kp/Pu ; Kd = 0.125·Kp·Pu
// ---------------------------------------------------------------------------
#define PH_TUNE_GAS_HI                    25     // gas mức cao khi BT<SV_tune (%) — bộ THƯỜNG
#define PH_TUNE_GAS_HI_PREMIX             40     // PREMIX: 40% để lửa tune vượt hẳn trần SV_tune, chạm sớm & dao động cân đối
#define PH_TUNE_GAS_LO                    0      // gas tắt khi BT>SV_tune
#define PH_TUNE_AIR_HI                    20     // gió nền khi đang đốt (BT<SV_tune)
#define PH_TUNE_AIR_LO                    100    // gió tối đa hạ nhiệt (BT>SV_tune)
#define PH_TUNE_CYCLES                    2      // số chu kỳ dao động cần đo
#define PH_TUNE_PEAK_MIN                  5      // biên độ tối thiểu 1 đỉnh (0.1°C)
#define PH_TUNE_TIMEOUT_SEC               600    // quá lâu → bỏ tune, dùng Config
// Phát hiện relay KẸT: máy nóng sẵn, tắt gas + gió 100% mà BT không tụt nổi xuống
// dưới SV_tune (nhiệt dư cao hơn SV_tune). Nếu ở trạng thái LO liên tục quá lâu này
// (giây) mà chưa cắt xuống → bỏ tune, dùng Config gains (đã chứng minh chạy tốt).
#define PH_TUNE_STUCK_SEC                 75

// Low PV Autotune — giống Hanyoung VX4 "Low PV mode":
// Tune ở nhiệt độ THẤP HƠN SV thật → an toàn hơn, tránh vọt lố trên máy quán tính lớn.
// Công thức VX4: SV_tune = FRL + (SV − FRL) × 0.9
// FRL = Full Range Low của cảm biến (K-type: −200°C → ×10 = −2000 đơn vị 0.1°C)
// Ví dụ SV=190°C, FRL=−200°C: SV_tune = −200 + (190−(−200))×0.9 = 151°C
// 1 = Low PV mode (khuyên dùng cho máy gas quán tính lớn)
// 0 = Standard mode (tune ngay tại SV thật — rủi ro vọt như hôm test)
#define PH_TUNE_LOWPV_EN                  1
#define PH_TUNE_FRL                       -2000  // Full Range Low ×10 (K-type = -200°C)

// Tự đánh giá chất lượng tune khi kết thúc preheat (1 nút, không cần xóa file tay).
// Nếu kết quả TỆ → tự xóa /pid_pre.txt → lần preheat sau TỰ TUNE LẠI.
// Tiêu chí: đánh giá theo độ ỔN ĐỊNH KHI GIỮ NHIỆT (HOLD), KHÔNG phạt vọt lúc đi lên
// (anh cho phép lên nhanh + vọt nhẹ). Tệ khi:
//   • KHÔNG vào nổi HOLD (không đạt target trong thời gian preheat), HOẶC
//   • Độ lệch lớn nhất khi HOLD > PH_TUNE_HOLD_DEV (mục tiêu giữ SV ±2°C).
#define PH_TUNE_HOLD_DEV                  20     // lệch HOLD > 2°C (0.1°C) = tune chưa đạt
// Bỏ qua giai đoạn chuyển tiếp khi vừa vào HOLD (BT còn cách target tới ±3°C lúc
// mới vào, chưa kịp ổn định). Chỉ đo độ ổn định SAU khoảng này (giây).
#define PH_HOLD_SETTLE_SEC                45

// Gain scheduling theo mức SV (giống Hanyoung n.PID) — lưu nhiều bộ hệ số theo
// nhiệt độ. Khách luân phiên nhiều mức (vd 240/170): tune mỗi mức 1 lần, sau đó
// dùng lại, KHÔNG tune lại. SV chênh ≤ PH_SV_MATCH (0.1°C) coi là cùng 1 mức.
#define PH_SV_TABLE_MAX                   8     // số mức SV lưu tối đa
#define PH_SV_MATCH                       150   // ±15°C: coi cùng 1 mức SV

// ---------------------------------------------------------------------------
// AN TOÀN
// ---------------------------------------------------------------------------
// Hủy preheat ngay nếu |ET − BT| vượt ngưỡng này (đơn vị 0.1°C)
// Ví dụ: 1600 = 160°C
#define PH_DIVERGE_LIMIT                  1600

// Trần an toàn riêng cho preheat PID: BT vượt SV + ngưỡng này (0.1°C) → cắt gas
// ngay + gió mạnh, bất kể PID/relay đang tính gì. Chặn vọt lố. (150 = 15°C)
#define PH_PID_OVERHEAT_GUARD             150

// Gió thổi sạch buồng đốt trước khi mồi lửa (ms)
#define PH_PURGE_MS                       8000UL

// ---------------------------------------------------------------------------
// GĐ1/2/3 — HEATING (BT còn xa target, gap > PH_TARGET_BAND)
// Band RoR5 tính ĐỘNG từ deadline:
//   RoR5_cần = gap × 5 / time_remaining  (0.1°C/5s)
//   Dùng tolerance ±PH_DL_RATIO để làm band trên/dưới
// Không còn hardcode ROR_LO/HI theo từng giai đoạn
// ---------------------------------------------------------------------------
#define PH_HEAT_STEP                      10    // bước gas chỉnh khi lệch band (%)

// ---------------------------------------------------------------------------
// GĐ4 — GIỮ NHIỆT (trong target ±3°C)
// ---------------------------------------------------------------------------
#define PH_GD4_ROR_LO                     1     // 0.1°C/5s
#define PH_GD4_ROR_HI                     3     // 0.3°C/5s
#define PH_GD4_STEP                       5     // bước gas (%)

// Deadband ổn định: trong target ±3°C VÀ |RoR5| ≤ giá trị này → giữ gas
#define PH_GD4_DEAD                       1     // 0.1°C/5s

// Band cảnh báo ngoài: BT vọt ra ngoài ±3 nhưng còn trong ±5 → giảm gas, cooldown 10s
#define PH_WARN_BAND                      50    // ±5°C (0.1°C)
// Cooldown (giây) sau khi phản ứng band ±5°C
#define PH_WARN_COOLDOWN                  10

// Forecast window: dự báo BT sẽ ở đâu sau X giây.
// Slope dùng RoR5 (cửa sổ 5s, làm mượt nhẹ), tính lại MỖI GIÂY để kịp thời.
#define PH_FC_WIN_SEC                     5     // cửa sổ slope forecast (giây)
#define PH_FC_AHEAD_SEC                   60    // dự báo bao xa cho logic thường (giây)

// Vùng an toàn quanh target cho forecast 60s (0.1°C).
// Forecast nằm trong target ± dải này → coi như đúng tiến độ, GIỮ gas.
// Chỉ chỉnh gas khi forecast vọt ra ngoài dải này.
#define PH_FC_SAFE_BAND                   100   // ±10°C

// Tốc độ góc: |Δslope| trong 1 giây (0.1°C/5s). Nếu nhỏ hơn ngưỡng này
// → forecast đang đi đều → KHÔNG chỉnh gas dù lệch, tránh nhấp nhô.
// Chỉ phản ứng khi slope đổi mạnh (BT tăng/giảm đột ngột).
#define PH_DSLOPE_GATE                    5     // 0.5°C/5s thay đổi mỗi giây

// ---------------------------------------------------------------------------
// HOLD — GIỮ NHIỆT sau khi đạt target (phút 3 trở đi)
// Đuôi forecast kéo DÀI tới (thời gian preheat còn lại + PH_HOLD_EXTRA_SEC) để
// bắt cả độ trôi RoR rất nhỏ. Phễu an toàn loe tuyến tính: gốc (hiện tại) sát
// target ±PH_HOLD_BAND_NEAR, đuôi (cuối horizon) nới tới ±PH_HOLD_BAND_FAR.
// Forecast trong phễu → giữ gas. Lố mạnh+nhanh → chỉnh ngay (EMERGENCY).
// ---------------------------------------------------------------------------
#define PH_HOLD_EXTRA_SEC                 900   // kéo đuôi thêm 15 phút (giây)
#define PH_HOLD_BAND_NEAR                 30    // gốc phễu ±3°C (0.1°C)
#define PH_HOLD_BAND_FAR                  50    // đuôi phễu ±5°C (0.1°C)

// Emergency forecast: nếu BT sẽ vọt qua ±5°C trong vòng X giây → cắt gas ngay
// Kiểm tra mỗi giây (không chờ chu kỳ 5s)
#define PH_FC_EMERGENCY_SEC               15    // horizon khẩn cấp (giây)
#define PH_EMERGENCY_STEP                 15    // bước cắt gas khẩn cấp (%)

// Deadline 3 phút — ratio-based control cho GĐ1/2 (BT còn xa target)
// ratio = time_to_target / time_remaining
//   ratio < PH_DL_RATIO_LO  → quá nhanh → giảm gas
//   ratio > PH_DL_RATIO_HI  → quá chậm  → tăng gas
//   trong khoảng             → đúng tiến độ → giữ
// Kiểm tra mỗi 5 giây (cùng chu kỳ gas eval)
#define PH_DEADLINE_SEC                   180   // deadline đạt target (giây = 3 phút)
#define PH_DEADLINE_STEP                  10    // bước tăng/giảm gas (%)
#define PH_DL_RATIO_LO                    80    // ratio × 100: dưới ngưỡng này = quá nhanh
#define PH_DL_RATIO_HI                    120   // ratio × 100: trên ngưỡng này = quá chậm

// ---------------------------------------------------------------------------
// OVERSHOOT — BT vượt target + PH_TARGET_BAND
// RoR5 mục tiêu khi kéo BT xuống (âm = đang giảm)
// ---------------------------------------------------------------------------
#define PH_OVER_ROR_LO                   -3     // −0.3°C/5s (giảm quá nhanh → tăng gas)
#define PH_OVER_ROR_HI                   -1     // −0.1°C/5s (giảm chưa đủ → giảm gas)
#define PH_OVER_STEP                      5     // bước gas (%)

// ---------------------------------------------------------------------------
// NGƯỠNG CHUYỂN GIAI ĐOẠN
// ---------------------------------------------------------------------------
// BT < giá trị này → GĐ1 (đơn vị 0.1°C)
#define PH_BT_PHASE2                      1000  // 100°C

// Cách target ≤ giá trị này → GĐ3 (đơn vị 0.1°C)
#define PH_APPROACH_BAND                  250   // 25°C

// Cách target ≤ giá trị này → GĐ4 / vùng giữ (đơn vị 0.1°C)
#define PH_TARGET_BAND                    30    // ±3°C

// ---------------------------------------------------------------------------
// TIMING
// ---------------------------------------------------------------------------
// Chu kỳ chỉnh gas (giây) — mỗi bao nhiêu giây xem lại RoR5 và chỉnh gas
#define PH_GAS_EVAL_SEC                   5

// Cooldown airflow (giây) — sau mỗi lần đổi airflow, khóa bao lâu
#define PH_AIR_COOLDOWN                   10

// ---------------------------------------------------------------------------
// AIRFLOW
// ---------------------------------------------------------------------------
// Gió nền khi đang đốt bình thường (%)
#define PH_AIR_BASE                       20

// Gió thổi sạch buồng + làm nguội khi BT quá cao (%)
#define PH_AIR_PURGE                      60

// ---------------------------------------------------------------------------
// MỒI LỬA
// ---------------------------------------------------------------------------
// Chờ tín hiệu lửa tối đa bao nhiêu giây trước khi retry
#define PH_IGNITE_TMO                     60     // bộ THƯỜNG (mồi nhanh)
#define PH_IGNITE_TMO_PREMIX             65     // PREMIX: mồi chậm ~40s → nới timeout tránh báo lỗi mồi sai

// Số lần thử mồi tối đa trước khi báo lỗi IGNITE_FAIL
#define PH_IGNITE_RETRY                   3

// ── Chốt an toàn máy trạng thái rang (thêm 2026-07-30, xem skill quy-trinh-dieu-khien-may-rang) ──
// Trần pha phát triển, PHẦN NGHÌN (300 = 30%). Chỉ kêu chuông + báo mã, KHÔNG tự xả —
// tự xả một mẻ chưa tới nhiệt là làm hỏng mẻ.
#define DEV_WARN_PERMIL                 300
// Giây đứng ở STP_LOOP_2 mà cửa xả vẫn mở → coi là xi-lanh kẹt, dừng, không nạp mẻ mới.
#define LOOP2_STUCK_SEC                  60
// R7: giây tối thiểu kể từ lúc NẠP mới cho auto-drop và bồn nguội sớm được kích.
// Không mẻ nào xả trong 2 phút đầu; chặn này phòng hồ sơ có nhiệt xả THẤP HƠN nhiệt nạp
// (rang nhẹ / ca cao) làm máy bắn lệnh xả ngay khi vừa đổ hạt.
#define DROP_MIN_SEC                    120

#if MACHINE_VR_SOURCE_FROM_HMI
#define SOURCE_AI_VR_FROM_HMI true
#endif

// ---------------------------------------------------------------------------
// PCL_APP_WATCHDOG_EN: watchdog PC control (PC_Link).
//   1 = app im quá PCL_APP_TMO_S giây → firmware tự nhả PC control về HMI + còi.
//   0 = KHÔNG BAO GIỜ tự nhả (chủ máy yêu cầu 2026-07-22). Lưu ý: app treo giữa
//       mẻ thì máy chạy tiếp setpoint cuối vô thời hạn — thợ phải tự tắt PC
//       control trên HMI. Chốt MỒI HỤT ĐÓNG GAS vẫn hoạt động bình thường.
// ---------------------------------------------------------------------------
#define PCL_APP_WATCHDOG_EN               0
```
