#pragma once

/*
 * Cấu hình máy rang
 * Cấu hình hiện tại (20/09/2026) — firmware v3.12.0: máy 30 kg tự động rang cacao,
 *   mã hồ sơ M03 (docs/config/config-30kg-cacao-M03.md). CÓ loader (đầu cân
 *   Bluetooth), CÓ vacuum (cảm biến áp đấu ACI biến tần GIÓ slave 5), CÓ biến tần
 *   drum, KHÔNG biến trở VR vật lý (setpoint drum/gió/gas lấy từ HMI), CÓ module IO
 *   relay ngoài Modbus ID 7 (CH1 Trống/Quạt, CH2 Khuấy — mixer tách dây riêng, không
 *   đấu chung cooling), HMI đời cũ chưa có ô $M53.
 *   (02/10/2026 đổi sang bộ phần cứng này — trùng bộ của v3.11.0, trên nền code v3.12.0.)
 *   v3.12.0 so với v3.11.0: RoR BT/ET tính theo chuỗi Artisan (mẫu 1s, Delta Span 10s,
 *   Smoothing 3, Smooth Curves 2 — xem khối ROR_* cuối file), bỏ Kalman; trần RoR ET
 *   ±20 → ±95 °C/phút; watchdog PC_Link đóng gas thay vì gạt nút PC control.
 *   Preheat KHÔNG đổi: đọc rorBT_ph/rorET_ph tính đúng cách cũ (3s + Kalman).
 *   VR: sửa tự học mốc 100% — đỗ VR 90–97% không còn tự nhảy 100% / tụt về 0%.
 *   RoR: span 40s + smoothing 12 — giật 0,05 °C/phút, đổi lại trễ ~30s.
 * (Bản trước) v3.11.0 15/09/2026: 30 kg auto, loader + vacuum gió, KHÔNG VR,
 *   CÓ IO relay Modbus ngoài (ID 7) — gói ở 112_Quanly/43_Update_CMS_26/150926.
 * (Bản trước) 30 kg noVacuum nền preset M06 — giao v3.10.0 10/09/2026, Config.h lưu
 *   kèm ở 112_Quanly/43_Update_CMS_26/100926.
 *   Cấu hình máy 15 kg M09 xem docs/config/config-15kg-auto-M09.md.
 * (Header cũ) máy rang OTL-15-AUTO (15 kg, tự động) — mã hồ sơ M09.
 *   Cụm đi kèm: OL-120-AUTO (hút liệu 120 kg) + OD-15-V2 (tách đá) + AF-15-ĐỨNG (đốt khói).
 *   Bộ nạp liệu OL-120-AUTO dùng XI LANH ĐIỆN 30 mm/s, hành trình 30 mm.
 *   (Seri máy và khách hàng: xem bảng tra ngoài repo, 112_Quanly\BANG-TRA-MA-MAY.md)
 * CÓ vacuum control (cảm biến áp hút + PID gió qua biến tần gió RS485),
 * CÓ biến tần drum, CÓ đầu cân Bluetooth cho auto-loader.
 * KHÔNG module IO relay ngoài (relay qua GPIO onboard).
 * Loại đầu đốt do HMI chọn lúc chạy (reg 29) — không khoá lúc build.
 *
 * Đổi file này khi build firmware cho từng model máy rang khác nhau.
 * Các tùy chọn dạng bật/tắt nên giữ giá trị 0/1, trừ khi dòng chú thích
 * nói rõ cách dùng khác.
 */

// ---------------------------------------------------------------------------
// Phiên bản board phần cứng.
// Chỉ được bật đúng 1 dòng V300, V350 hoặc V400.
// ---------------------------------------------------------------------------
// #define V300 true
// #define V350 true
#define V400 true

// ---------------------------------------------------------------------------
// Phần cứng/ngoại vi có lắp trên máy.
// 1 = có lắp và firmware sẽ đọc/ghi thiết bị đó.
// 0 = không lắp, firmware bỏ qua các luồng chính liên quan.
// ---------------------------------------------------------------------------
#define MACHINE_HAS_AIRFLOW_CONTROL       1  // Điều khiển gió bằng DAC/phần trăm gió
#define MACHINE_HAS_GAS_CONTROL           1  // Điều khiển gas bằng DAC và relay gas
#define MACHINE_HAS_DRUM_SPEED_CONTROL    1  // Điều khiển tốc độ drum bằng biến tần (slave 4)
#define MACHINE_HAS_AIR_INVERTER          1  // Biến tần quạt gió nối RS485 Modbus (cần cho vacuum)
#define MACHINE_HAS_VACUUM_SENSOR         1  // CÓ cảm biến áp hút — PID gió qua biến tần gió
#define MACHINE_HAS_SCALE_FEEDER          1  // CÓ đầu cân Bluetooth cho auto-loader
#define MACHINE_HAS_IO_RELAY_MODULE       1  // M03 CÓ module relay ngoài Modbus (ID 7): CH1 Trống/Quạt, CH2 Khuấy
#define MACHINE_HAS_BT_TEMP_CONTROLLER    1  // Đồng hồ nhiệt BT có nối RS485 Modbus
#define MACHINE_HAS_ET_TEMP_CONTROLLER    1  // Đồng hồ nhiệt ET có nối RS485 Modbus
#define MACHINE_BATCH_KG                  30 // Khối lượng mẻ rang danh định (kg) — máy 30 kg
// KHOÁ LOẠI ĐẦU ĐỐT LÚC BUILD.
//   1 = ÉP đầu đốt THƯỜNG (khuếch tán), BỎ QUA thanh ghi HMI 29. Dùng cho máy chắc chắn
//       không phải premix — nhất là HMI đời cũ không có ô chọn bếp, đọc reg 29 ra rác thì
//       firmware sẽ nhảy nhầm sang bộ tham số PREMIX (gains HOLD yếu + timeout mồi 65s).
//   0 = theo HMI như cũ (1 firmware chạy được cả 2 loại bếp).
// Máy 30kg M03: HMI có ô chọn bếp → để 0, theo HMI như cũ.
#define MACHINE_BURNER_FORCE_STANDARD     0

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
#define MACHINE_VACUUM_FROM_DRUM          0  // cảm biến áp đấu ACI biến tần GIÓ (slave 5)

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
#define MACHINE_VR_SOURCE_FROM_HMI        1  // M03 KHÔNG có biến trở vật lý — setpoint lấy từ HMI

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
// ── dif THỦ CÔNG + TỰ HIỆU CHUẨN TRONG RAM (2026-09-05) ────────────────────
// FEEDER_DIF_MANUAL
//   1 = dif tính bằng công thức dưới đây, tự chỉnh theo sai số đo được sau MỖI mẻ.
//       KHÔNG tra bảng /loadcfg.csv, KHÔNG ghi thẻ SD — loader không đụng thẻ.
//   0 = quay lại hành vi cũ (tra bảng + tự học, có ghi thẻ). Đổi 1 số này là lùi được ngay.
//
// dif = lượng cắt SỚM để bù coast (cà còn rơi trong lúc cửa phễu đóng):
//
//     dif (×100 kg) = coastBase100 + set(kg) × FEEDER_COAST_PER_KG / 1000
//                     └── biến RAM, TỰ HỌC ──┘   └── độ dốc theo cỡ mẻ, cố định ──┘
//
// MỘT FIRMWARE CHO CẢ XI LANH KHÍ LẪN XI LANH ĐIỆN. coastBase100 khởi động từ SEED rồi
// tự bò về đúng giá trị của máy: sau mỗi mẻ firmware đã đo được sai số (err = thực tế −
// đích, >0 là hút thiếu) nên chỉ việc kéo base đi ngược lại sai số đó.
//
// Vì sao PHẢI tự học chứ không đặt sẵn 2 bộ số: coast KHÔNG suy ra được từ tốc độ đóng.
// Đo thật cùng mẻ 10 kg: xi lanh KHÍ (đóng ~0,5 s) coast 1,00 kg, xi lanh ĐIỆN (đóng 1,0 s)
// coast 0,79 kg — đóng CHẬM hơn mà coast NHỎ hơn, ngược hẳn mô hình lưu-lượng×thời-gian.
// Coast còn phụ thuộc hình học cửa, độ chân không, độ ẩm hạt... nên chỉ có đo trên máy
// mới ra đúng. Firmware tự đo thì lắp cơ cấu gì cũng chạy, khỏi hiệu chuẩn tay.
//
// Dữ liệu đã đo (dùng để chọn SEED và độ dốc):
//   xi lanh ĐIỆN 30 mm/s × 30 mm — 18 mẻ 05/09/2026:
//     mẻ 2 kg → coast 0,70 · 5 kg → 0,78 · 10 kg → 0,79 · 15 kg → 0,82   (dốc rõ)
//   xi lanh KHÍ — 7 mẻ log serial + 18 lần cân tay 17/08/2026:
//     mẻ 5/10/20 kg → coast ≈ 1,00 ở cả ba mức (phẳng, lệch chuẩn 0,05)
// SEED 85 = điểm giữa hai máy → mẻ đầu sau khi bật điện lệch nhiều nhất 0,15 kg về một
// phía bất kỳ, thay vì 0,29 kg nếu ghim theo một loại máy.
//
// PER_KG giữ cố định 8 (0,008 kg mỗi kg mẻ): độ dốc chỉ đáng 0,12 kg trên toàn dải 2–15 kg,
// nhỏ hơn nhiều so với chênh lệch base giữa hai máy (0,29 kg) nên không đáng học riêng —
// học 2 tham số cùng lúc sẽ chậm hội tụ và dễ đuổi theo nhiễu. Đặt 0 là bỏ độ dốc.
//
// CHỈNH KHI CẦN:
//   • Máy hụt/dư ĐỀU ở mọi cỡ mẻ → KHÔNG cần làm gì, firmware tự sửa trong 2–3 mẻ.
//   • Mẻ NHỎ đúng mà mẻ LỚN lệch (hoặc ngược lại) → đổi PER_KG. Tăng 10 thì mẻ 15 kg hụt
//     thêm 0,10 kg so với mẻ 5 kg.
//   • Chạy ổn định rồi, muốn hết cả sai số mẻ đầu → đọc "base=" trong log LDR rồi chép
//     con số đó vào SEED và build lại.
#define FEEDER_DIF_MANUAL                 1
#define FEEDER_COAST_SEED100              85    // ×100 kg: base lúc khởi động (điểm giữa khí↔điện)
#define FEEDER_COAST_PER_KG               8     // ×0.001 kg: dif tăng thêm cho MỖI kg cỡ mẻ

// Tốc độ tự học base. err (×100 kg) đo được sau mỗi mẻ → base -= err × GAIN / 100.
//   GAIN 60 = sửa 60% sai số mỗi mẻ. Máy lệch 0,29 kg hội tụ sau 2 mẻ (0,29 → 0,12 → lọt
//   deadband). Cao hơn thì đuổi theo nhiễu cân (độ lặp lại đo được của máy là ±0,035 kg),
//   thấp hơn thì mẻ đầu ngày lệch lâu. Deadband dùng chung tiêu chí "hút OK" sẵn có
//   (lệch ≤ 0,09 kg thì coi như đạt, KHÔNG sửa base) nên base đứng yên khi máy đang chạy đúng.
#define FEEDER_LEARN_GAIN                 60
#define FEEDER_COAST_MIN100               40    // kẹp dưới base (×100 kg) — chặn học loạn
#define FEEDER_COAST_MAX100              150    // kẹp trên base (×100 kg)
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
#define PH_TUNE_GAS_HI                    25     // gas mức cao khi BT<SV_tune (%)
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
#define PH_HOLD_SETTLE_SEC                45     // mặc định khi M55=0 (HMI cũ)

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
#define PH_DEADLINE_SEC                   180   // mặc định khi M54=0; deadline đạt target
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
#define PH_TARGET_BAND                    30    // mặc định khi M56=0; ±3°C

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
// Mức gas khi MỒI LỬA (%). Mức này dùng cho cả trạng thái IGNITE lẫn mức gas khởi đầu
// ngay sau khi bắt được lửa (không cho tụt xuống dưới mức vừa mồi được, tránh tắt lửa
// ngay sau khi mồi). Máy 30kg M03: giữ 30 — đúng con số ghi cứng trong bản đã chạy máy.
#define PH_IGNITE_GAS                     30

// Chờ tín hiệu lửa tối đa bao nhiêu giây trước khi retry
#define PH_IGNITE_TMO                     60     // bộ THƯỜNG (mồi nhanh)
#define PH_IGNITE_TMO_PREMIX             65     // PREMIX: mồi chậm ~40s → nới timeout tránh báo lỗi mồi sai

// Số lần thử mồi tối đa trước khi báo lỗi IGNITE_FAIL
#define PH_IGNITE_RETRY                   3

// ── Chốt an toàn máy trạng thái rang (thêm 2026-07-30, xem skill quy-trinh-dieu-khien-may-rang) ──
// Trần pha phát triển, PHẦN NGHÌN (300 = 30%). Chỉ kêu chuông + báo mã, KHÔNG tự xả —
// tự xả một mẻ chưa tới nhiệt là làm hỏng mẻ.
#define DEV_WARN_PERMIL                 300     // mặc định khi M57=0
// Giây đứng ở STP_LOOP_2 mà cửa xả vẫn mở → coi là xi-lanh kẹt, dừng, không nạp mẻ mới.
#define LOOP2_STUCK_SEC                  60      // mặc định khi M60=0
// R7: giây tối thiểu kể từ lúc NẠP mới cho auto-drop và bồn nguội sớm được kích.
// Không mẻ nào xả trong 2 phút đầu; chặn này phòng hồ sơ có nhiệt xả THẤP HƠN nhiệt nạp
// (rang nhẹ / ca cao) làm máy bắn lệnh xả ngay khi vừa đổ hạt.
#define DROP_MIN_SEC                    120      // mặc định khi M58=0
// ── CHỐT CỨU ĐOẠN CUỐI MẺ (thêm 2026-09-10) ─────────────────────────────────
// Bộ bù gas thường (calibGasByProfile) MÙ trong 0.6 °C cuối trước nhiệt xả: khi
// lastTimeSD đã đóng băng thì mục tiêu CHÍNH LÀ nhiệt xả, nên sai lệch chỉ co lại
// và cửa sổ xác nhận 10 s không bao giờ đóng được. Mẻ RoR thấp (hồ sơ vuốt gas về
// 0%, hoặc nhiệt độ môi trường thấp hơn mẻ mẫu) sẽ đứng lại và không tự xả.
// Khối này chạy ĐỘC LẬP, có bộ đếm riêng, KHÔNG dính deadband.
// Đặt END_RESCUE_EN = 0 để TẮT hoàn toàn.
// Xem docs/plan/2026-09-10-auto-stall-cuoi-me.md.
#define END_RESCUE_EN                     1
// Bước bơm phụ thuộc MỨC GAS NỀN của hồ sơ tại giây đó (sdGas[], TRƯỚC mọi bù):
//   gas nền THẤP  → bếp đang ở gần mức đóng, vùng phi tuyến, đáp ứng kém
//                   → phải bơm bước LỚN mới có tác dụng
//   gas nền đủ cao → bếp đang ở vùng tuyến tính, bước nhỏ đã đủ
// SÀN CỨNG 5%: trên bếp NP dưới 5% gas không có tác dụng (bếp premix có thể thấp
// hơn). Đây cũng là lý do numIncGas = calibGas*5 có sàn 1 bậc.
#define END_GAS_LOW_THR                   10    // % — ranh giới "gas nền thấp"
#define END_GAS_BUMP_LOW                  10    // % — bước khi gas nền < ngưỡng trên
#define END_GAS_BUMP_HI                   5     // % — bước khi gas nền >= ngưỡng trên
// Chỉ chạy trong ngần này (×0.1 °C) trước nhiệt xả. 20 = 2.0 °C.
#define END_GUARD_BAND                    20
// BT nhích ngần này (×0.1 °C) là coi như bù có tác dụng. 1 = 0.1 °C — đo trên 4 mẻ
// thật: BT KHÔNG BAO GIỜ đi xuống, nên 1 đơn vị đã đủ tin, không cần lọc thêm.
#define END_BT_TICK                       1
// TIÊU CHÍ DỰ BÁO (ETA) — ra tay TRƯỚC khi BT đứng hẳn.
// Chờ BT đứng hẳn rồi mới bơm là đã muộn: cửa sổ dò + trễ nhiệt bếp→hạt (~30 s) ăn
// hết ngân sách thời gian. Nên máy ước lượng "với nhịp này còn bao lâu tới nhiệt xả":
//     ETA = (số đơn vị 0.1 °C còn lại) × (số giây giữa 2 lần BT nhích)
// ETA vượt ngần này giây → coi là KHÔNG KỊP, bơm ngay, không chờ đứng hẳn.
// Tự co giãn: càng xa nhiệt xả càng ra tay sớm, sát đích thì rộng tay.
#define END_MAX_ETA                       30
// Sàn chống rung: ít nhất ngần này giây trong cửa sổ mới cho phép bơm lần đầu.
#define END_STALL_WATCH                   3
// Giữ tối thiểu ngần này giây rồi mới xét BT có nhích không (chủ máy chốt: ≥10 s).
#define END_PULSE_MIN                     10
// Chưa nhích sau ngần này giây thì cộng thêm một bước. Phải ≥ trễ nhiệt bếp→hạt
// (15–30 s), nếu không sẽ leo thang trước khi thấy kết quả bước trước → vọt nhiệt.
#define END_ESCALATE                      35
// Trần tổng cộng, %. 15 = 3 bước. Hết trần mà BT vẫn đứng → kêu chuông + báo mã,
// KHÔNG tự xả (xả một mẻ chưa tới nhiệt là hỏng mẻ — cùng nguyên tắc DEV_WARN).
#define END_RESCUE_MAX                    15

// ── DEADBAND BỘ BÙ GAS — siết dần về cuối mẻ ────────────────────────────────
// Đơn vị ×0.1 °C. Trước FCs dùng clRangeBt (=10, ±1.0 °C) khai trong Define.h.
// Càng về cuối càng siết vì sai số tích lũy ở đoạn này quyết chất hạt.
// ⚠ Bậc bù nhỏ nhất là 5% (sàn cứng bếp NP). Siết deadband xuống dưới 5 mà không
//   hạ được bậc bù thì tỉ lệ "phản ứng / kích hoạt" tăng lên — dễ hunting.
#define CALIB_DEADBAND_FCS                6     // ±0.6 °C — từ FCs tới hết phút 2 của DEV
#define CALIB_DEADBAND_LATE               3     // ±0.3 °C — DEV từ phút 2 trở đi
#define CALIB_LATE_DEV_SEC                120   // giây DEV để chuyển sang nấc siết

// ── NHIỆT XẢ ĐỘNG THEO SAI LỆCH THỜI GIAN (thêm 2026-09-10) ─────────────────
// Mẻ rang hấp thụ nhiệt theo CẢ thời gian lẫn nhiệt độ. Cùng một nhiệt xả, mẻ đi
// chậm hơn mẫu đã ngậm nhiều nhiệt hơn ⇒ nên xả SỚM hơn một chút; mẻ đi nhanh hơn
// mẫu thì ngậm ít hơn ⇒ xả TRỄ hơn một chút. Bù lại sai lệch thời gian bằng nhiệt.
//   trễ  hơn mẫu > ADAPT_DROP_DEV_SEC giây → nhiệt xả  −ADAPT_DROP_STEP
//   nhanh hơn mẫu > ADAPT_DROP_DEV_SEC giây → nhiệt xả  +ADAPT_DROP_STEP
//   trong khoảng đó → giữ nguyên nhiệt xả của hồ sơ
// CHỈ áp dụng khi pha phát triển ĐÃ DÀI hơn ADAPT_DROP_MIN_DEV — mẻ DEV ngắn thì
// vài giây lệch không đủ đổi chất hạt, chỉnh nhiệt xả chỉ thêm nhiễu.
// BIÊN CHỈNH nay do THỢ cài trên HMI qua $M54 (0.0–1.0 °C, 0 = TẮT).
// Hằng dưới chỉ là giá trị gợi ý để khởi tạo ô HMI mới — firmware KHÔNG dùng nó.
#define DROP_TRIM_DEFAULT           3     // ×0.1 °C — 3 = 0.3 °C
#define ADAPT_DROP_DEV_SEC                15    // giây lệch mới bắt đầu chỉnh
#define ADAPT_DROP_MIN_DEV                180   // giây — chỉ khi DEV đã quá 3 phút

// Chế độ "chỉ làm mát" ($M53 autoEscape = 1): chuỗi cooling KHÔNG mở escape nữa nên
// thợ xả tay. Cửa mở tay tự đóng sau escapeDuration_R + số giây này — xả tay chậm hơn
// xả tự động nên cộng thêm. Đặt 0 = đóng đúng bằng escapeDuration_R như xả tự động.
#define ESCAPE_MANUAL_EXTRA_SEC          15      // giá trị khởi tạo cho HMI mới; M59=0 là hợp lệ
// CÓ Ô GẠT $M53 TRÊN MÀN HMI CHƯA?
//   1 = HMI có ô gạt "TỰ ĐỘNG MỞ CỬA XẢ" ghi $M53 → firmware nghe theo ô đó
//       ($M53 = 1 tự mở escape + tách đá · $M53 = 0 chỉ làm mát, thợ xả tay).
//   0 = HMI ĐỜI CŨ chưa có ô này → firmware BỎ QUA $M53 và luôn tự mở escape như cũ.
// ⛔ Để 1 trên máy mà HMI chưa có ô gạt là $M53 đọc về 0 ⇒ MÁY NGỪNG TỰ XẢ, cà phê
//    nằm lì trong khay nguội mà không báo lỗi gì. Nạp máy khách thì kiểm ô gạt TRƯỚC.
#define MACHINE_HAS_AUTO_ESCAPE_SWITCH    0  // M03: HMI đời cũ chưa có ô gạt $M53 → luôn tự mở escape

// ---------------------------------------------------------------------------
// RoR BT / ET — tính y hệt Artisan lúc đang rang (canvas.py sample_processing):
//   1. Smooth Curves: BT/ET → trung bình trọng số 1..(2·UI+1), mẫu mới nhất nặng nhất
//   2. Delta Span:    RoR = (mẫu mới nhất − TB 5 mẫu quanh điểm trái) / Delta Span
//   3. Smoothing:     trung bình trọng số 1..N trên N giá trị RoR gần nhất,
//                     N = round((2·UI+1)/2) kiểu Python = UI nếu chẵn, UI+1 nếu lẻ
// Ba ô dưới đây đặt ĐÚNG số trong hộp Curves → Filters của Artisan thì RoR trên HMI
// khớp Artisan. Smoothing đếm theo SỐ MẪU: Smoothing 30 ở mẫu 2s = 60s lịch sử RoR.
// Chốt 20/09/2026: mẫu 1s / span 40s / smoothing 12 / curve 2 — giật 0,05 °C/phút, trễ ~30s.
// Chủ máy yêu cầu lọc mạnh dần: span10/sm3 (giật 0,27) → span20/sm6 (0,13) → span40/sm12 (0,05).
// (Bản trước span 10 / smoothing 3: giật 0,27 — chủ máy thấy chưa mịn. Ở mẫu 1s, DELTA SPAN quyết
//  định độ giật, không phải SMOOTHING: span 10→20 giật giảm nửa, còn smoothing 3→6 chỉ 0,27→0,24.)
// Thử 3 mẻ giả tưởng (gas đổi thưa → gas nhảy 0↔100% ở 190-210 °C): bản 20s/30 trễ ~30s,
// có lúc BT tụt 38s mà HMI vẫn báo RoR dương; bản này bám đúng chiều ~90% thời gian.
// ---------------------------------------------------------------------------
#define ROR_SAMPLE_SEC                    1   // = Sampling Interval (giây) — đặt 2 nếu muốn khớp Artisan để mẫu 2s
#define ROR_DELTA_SPAN_SEC                40  // = ô Delta Span (giây) — ở mẫu 1s, ô NÀY quyết định độ giật
                                              //   (Artisan chỉ cho tới 30s; 40 là ngoài thang của Artisan)
#define ROR_SMOOTHING                     12  // = ô Smoothing (UI)
#define ROR_CURVE_SMOOTH                  2   // = ô Smooth Curves (UI)

#if MACHINE_VR_SOURCE_FROM_HMI
#define SOURCE_AI_VR_FROM_HMI true
#endif

// ---------------------------------------------------------------------------
// PCL_APP_WATCHDOG_EN: watchdog PC control (PC_Link) — THEO TẦNG, từ 2026-09-06.
//
// Bật (1) KHÔNG đổi gì với thợ lái app: watchdog chỉ siết khi phần mềm TỰ KHAI
// mình là tác nhân tự động (ghi PCL_W_AGENT = 1). Lệnh cũ của chủ máy — "người
// lái thì không bao giờ tự nhả" (2026-07-22) — vẫn giữ nguyên, vì thợ đứng ngay
// cạnh máy, nhả quyền giữa mẻ phiền hơn là giúp.
//
// Lý do phải có tầng cho tác nhân tự động: AI/script KHÔNG đứng cạnh máy. Nó
// treo, hết quota hay đứt mạng thì im lặng, mà máy không biết là nó đã im —
// gas cứ cháy ở mức lệnh cuối. Nên agent=1 thì siết PCL_AGENT_TMO_S giây.
// Cờ agent CÀI THEN: khai 1 rồi thì không hạ về 0 giữa phiên để né watchdog.
//
//   1 = bật tầng tác nhân tự động (KHUYẾN NGHỊ — không ảnh hưởng thợ lái tay)
//   0 = tắt hẳn, kể cả tác nhân tự động cũng không bị nhả quyền
//
// Chốt MỒI HỤT ĐÓNG GAS (PCL_FLAME_TMO_S) chạy độc lập, không liên quan cờ này.
// ---------------------------------------------------------------------------
#define PCL_APP_WATCHDOG_EN               1
