---
name: rang-ca-phe
description: Kiến thức nền về quy trình rang cà phê máy OTL-06ALS và ý nghĩa các tham số cấu hình. Dùng khi cần tra ý nghĩa/đơn vị của thanh ghi $M (iMemHMI), giải thích luồng rang (charge → TP → DE/yellow → FCs → DEV → drop), hay tư vấn chỉnh gas/gió/thời gian xy-lanh cho máy rang.
allowed-tools: Read, Grep
---

Skill kiến thức rang cà phê cho dự án OTL-06ALS. Tra cứu nhanh ý nghĩa tham số và luồng rang.

## Khi nào dùng
- Người dùng hỏi "thanh ghi này để làm gì", "đơn vị của tham số X", "chỉnh cái nào để...".
- Cần giải thích một mốc rang (TP/DE/FCs/DEV) hoặc luật chỉnh gas AUTO.
- Rà soát cấu hình một máy cụ thể (đối chiếu docs/config/config-*.md).

## Tài nguyên
- **Bảng thanh ghi $M đầy đủ:** [references/registers-M.md](references/registers-M.md) — 52 tham số cấu hình HMI ghi xuống firmware (`iMemHMI[]`), kèm đơn vị và ý nghĩa.
- **19 hàm trong Program.h:** [references/program-functions.md](references/program-functions.md) — bộ não firmware (SD/hồ sơ, gas AUTO, auto-loader tự học, máy trạng thái `programScan` 11 bước).
- **Hồ sơ rang trên app (cấu hình + lưu CSV):** [references/profile-format.md](references/profile-format.md) — 9 trường công thức + quy ước lưu CSV vào thư mục `hồ sơ rang csv`.
- **Luồng rang 11 bước:** [references/roast-flow.md](references/roast-flow.md) — máy trạng thái `programScan()` (DATA→COOL_DOWN→GAS→CHECK→CHARGE→TP→YELLOW→FCS→DEV→DROP→LOOP), kèm dòng code & điều kiện chuyển.
- **App rang cà phê (app lái toàn bộ):** [references/app-roast-flow.md](references/app-roast-flow.md) — kiến trúc & luồng rang TRÊN APP OTL Roast Lab (chốt 2026-07-25): cấm SD, hồ sơ CSV, app giữ trọn state machine, firmware = tay chân + 2 chốt an toàn. Khác luồng firmware ở roast-flow.md.
- **RoR & lọc nhiễu nhiệt độ:** dùng skill `artisan-ror` — cách Artisan tính RoR (4 thuật toán), thứ tự 4 tầng bộ lọc, và đối chiếu với công thức cửa sổ 3 giây + Kalman của mình.
- **Sửa quy trình điều khiển:** dùng skill `quy-trinh-dieu-khien-may-rang` — bản spec đầy đủ 13 bước `progStep` + 3 máy phụ + bảng timer, kèm checklist áp thay đổi vào `Program.h`. File `roast-flow.md` ở đây chỉ là bản tóm tắt tra nhanh.
- Nguồn gốc: `include/Define.h` khối `//Define $M HMI` (dòng ~627); logic ở `include/Program.h`. Mỗi `_W` (chỉ số ghi) có bản `_R` (`iMemHMI[...]`) để firmware đọc và `_R_CP` để dò đổi.
- Cấu hình thực tế từng máy: `docs/config/config-*.md`.

## Các mốc rang (glossary)
| Mốc | Nghĩa | Ghi chú |
|-----|-------|---------|
| **Charge** | Đổ nhân vào lồng | nhiệt lồng phải đạt `chargeTemp` ±`chTolerange` |
| **TP** (Turning Point) | Điểm quay đầu — BT thấp nhất rồi bật lên | firmware tự bắt |
| **DE / Yellow** | Kết thúc pha sấy, nhân chuyển vàng | mốc `yellowPhase` (°C) |
| **FCs** (First Crack start) | Nổ lần 1 | mốc `fcsPhase` (°C) |
| **DEV** (Development) | Pha phát triển sau FCs | tính theo % tổng thời gian |
| **Drop** | Xả mẻ ra làm nguội | theo nhiệt xả hoặc lệnh |

## Nguyên tắc quan trọng
- Chỉnh gas AUTO dùng bậc feed-forward + bù lệch BT; giới hạn bậc tăng gas mỗi pha là `TpCalib`/`DeCalib`/`FcsCalib`. Xem memory `[[project_gas_calib_auto]]`, `[[project_ror_gas_cut_crack]]`.
- Đơn vị nhiệt = °C nguyên; `turnGasPoint` được firmware ×10 khi so sánh (xem `Modbus_Master.h`).
- Sửa comment/tài liệu tiếng Việt: theo skill `vietnamese-comments` (giữ dấu, UTF-8).
