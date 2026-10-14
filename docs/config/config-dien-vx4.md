# Config preset — Máy rang ĐIỆN, đồng hồ nhiệt buồng VX4

Máy rang **tự động như máy gas, nhưng nguồn nhiệt là điện trở**. Đồng hồ **Hanyoung VX4** đọc nhiệt **buồng rang** và
tự chạy PID đóng cắt điện trở; firmware chỉ **ghi SV** cho VX4. Lấy từ firmware máy 1 kg
(`F:\Project\96_Auto_1kg_2025 - Copilot`, hàm `readWriteChamber`), đưa vào firmware chung ngày 14/10/2026.

Cùng một mã nguồn với máy gas — chỉ khác **một cờ lúc dựng** và **file HMI**.

## Nạp

| Phần | Lệnh / file |
|---|---|
| Firmware | `pio run -e dien -t upload` (ST-Link). Dựng thử: `pio run -e dien` |
| HMI DOP-110WS | `113_HMI\…\AP4\R0-1014-ZOOM99-DIEN-110WS.dpa` |
| HMI DOP-110CS | `113_HMI\…\AP4\R0-1014-ZOOM99-DIEN-110CS.dpa` |
| Sinh lại HMI từ bản chung mới | `python _script\ui_bien_the_dien.py <bản ZOOM chung>.dpa <thư mục ra>` |

Env `dien` (platformio.ini) đặt `MACHINE_HEAT_ELECTRIC_VX4=1` và `MACHINE_RS485_ON_SCALE_PORT=1`. Bản gas
(`genericSTM32F103RC`) không có code VX4.

**Bus RS485 (BT / ET / VX4 / biến tần) của máy điện đi dây vào CỔNG CÂN** (USART3, chủ máy 14/10). Env `dien` đổi chỗ:
Modbus master = USART3, cân / Artisan slave = cổng Modbus cũ (USART2 trên board V400). Đã nạp thử trên máy: BT OK, ET OK
qua cổng cân ở 38400.

## Cài đặt đồng hồ VX4 (phải khớp firmware)

| Mục | Giá trị | Hằng trong `include/Config.h` |
|---|---|---|
| Địa chỉ RS485 | **6** | `VX4_MODBUS_ID` |
| Tốc độ | **38400**, 8N1 (chung đường RS485 với BT / ET / biến tần) | `MACHINE_RS485_BAUD` |
| Số lẻ | **1 số lẻ** (0,1 °C) — PV và SV đều ×10 | |
| Thanh ghi PV (đọc) | **0** | `VX4_REG_PV` |
| Thanh ghi SV (ghi) | **103** | `VX4_REG_SV` |
| Cho ghi SV qua truyền thông | **BẬT** (COM write enable) | |
| PID / ngõ ra điện trở | VX4 tự lo (SSR) — tune trên VX4 | |

## Firmware làm gì

| Việc | Cách làm |
|---|---|
| Nhiệt buồng | đọc VX4 mỗi vòng quét → HMI **W40097**, Artisan thanh ghi slave **5** |
| SV | `Nhiệt %` 0…100 (ô Gas cũ — hồ sơ / AUTO / Artisan giữ nguyên) → **130,0 … 350,0 °C** |
| Tắt `Lệnh nhiệt` | ghi **SV = 0** (`VX4_SV_TAT_X10`) — VX4 không nung. Bản 1 kg cũ để 130 °C |
| Ghi lại SV | khi đổi + mỗi **5 s** (VX4 khởi động lại vẫn nhận lại) |
| Khởi động | chờ VX4 trả lời như BT / ET, rồi ghi SV tắt |
| Mất VX4 | đếm lỗi như thiết bị Modbus khác; **5 lần liền → cắt relay CH1 (lệnh nhiệt)**, mã **298** |
| Bật / tắt bếp | relay **CH1** như máy gas (`Lệnh nhiệt` = `Lệnh gas` cũ) |
| Phản hồi "bếp chạy" | chân phản hồi CH1, như tín hiệu lửa của máy gas: bật bếp **~3 s** sau là có → dock hiện **Đang nung**. Chốt mồi hụt / chờ lửa 75 s giữ nguyên (mất phản hồi = cắt lệnh như mất lửa) |
| Nạp liệu / xả trống | relay **charge / drop** như cũ |

Lắp máy: đi dây contactor điện trở qua relay CH1 thì tắt lệnh nhiệt / lỗi VX4 / mất phản hồi sẽ cắt hẳn nguồn điện trở.

## Cấu hình máy `$M62` (màn Cấu hình máy, Master chọn)

Máy điện **KHÔNG có module relay ngoài (ID 7)** — chủ máy 14/10: "ko điều khiển được drum/fan, ko có board IO nên ko điều
khiển riêng lẻ được mixer".

| Bit | Đặt | Kết quả |
|---|---|---|
| 5 — module relay ngoài ID 7 | **0** | không điều khiển drum/fan; công tắc "Trống + quạt hút" trên màn Cài đặt tự ẨN |
| 11 — tay đảo relay riêng | **0** | tay đảo chạy chung relay quạt nguội trên board; nút Tay đảo ở dock tự ẨN |
| 15 — đã cấu hình | **1** | chưa đặt thì board chặn rang (mã 422) |
| còn lại (cỡ máy, vacuum, nạp liệu, đốt khói, tách đá, núm vặn) | theo máy thật | |

## HMI máy điện (khác bản gas)

| Chỗ | Gas | Điện |
|---|---|---|
| Ô nhiệt màn rang | Gas · Thực xx % | **Nhiệt** · **Thực xxx,x °C** = nhiệt buồng (đọc W40097) |
| Dock | Lệnh gas · Có lửa / Không lửa | **Lệnh nhiệt** · **Đang nung / Tắt nhiệt** |
| Nút Dừng | Gas sẽ tắt / Gas vẫn bật | Nhiệt sẽ tắt / Nhiệt vẫn bật |
| Chú giải đồ thị | Gas % | Nhiệt % |
| Mọi nhãn khác (Cài đặt, thẻ giải thích, câu Auto…) | gas | nhiệt / heat (`van gas` → thang nhiệt, `tốn gas` → tốn điện, `nguồn gas` → nguồn điện trở) |
| Cảnh báo | — | **298** mất kết nối VX4 |
| 110CS | — | đổi model DOP-110CS (cùng 1024 × 600); không cổng mạng → dòng địa chỉ web tự ẩn |

## Đã kiểm (14/10/2026)

- `pio run -e dien`: đạt — RAM 83,6 %, Flash 43,2 %. Bản gas dựng lại: chỉ khác bộ lọc mã (mở 298), `test_stt_queue` đạt.
- HMI 110WS + 110CS: DIAScreen biên dịch đạt. Giả lập (bản bàn thử LO99-DIEN): ô Nhiệt hiện đúng 245,6 °C cả tiếng Anh +
  tiếng Việt, cảnh báo 298 lên bảng Cảnh báo; `dpa_lint_text_fit` không thêm chỗ tràn chữ nào so với bản gas.
- **CHƯA thử với VX4 thật** (bàn thử không có VX4). Trước khi giao máy: cắm VX4, xem PV lên HMI, đổi `Nhiệt %` thấy SV
  trên VX4 đổi, rút cáp RS485 VX4 thấy mã 298 + relay CH1 cắt; nạp HMI 110CS lên panel 110CS thật.
