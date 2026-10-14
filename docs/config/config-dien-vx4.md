# Config preset — Máy rang ĐIỆN, đồng hồ nhiệt buồng VX4

Máy rang **tự động như máy gas, nhưng nguồn nhiệt là điện trở**. Đồng hồ **Hanyoung VX4** đọc nhiệt **buồng rang** và
tự chạy PID đóng cắt điện trở; firmware chỉ **ghi SV** cho VX4. Lấy từ firmware máy 1 kg
(`F:\Project\96_Auto_1kg_2025 - Copilot`, hàm `readWriteChamber`), đưa vào firmware chung ngày 14/10/2026.

Cùng một mã nguồn với máy gas — chỉ khác **một cờ lúc dựng** và **file HMI**.

## Nạp

| Phần | Lệnh / file |
|---|---|
| Firmware | `pio run -e dien -t upload` (ST-Link). Dựng thử: `pio run -e dien` |
| HMI DOP-110WS | `113_HMI\…\AP4\R0-1014-ZOOM97-DIEN-110WS.dpa` |
| HMI DOP-110CS | `113_HMI\…\AP4\R0-1014-ZOOM97-DIEN-110CS.dpa` |
| Sinh lại HMI từ bản chung mới | `python _script\ui_bien_the_dien.py <bản ZOOM chung>.dpa <thư mục ra>` |

Env `dien` (platformio.ini) đặt `MACHINE_HEAT_ELECTRIC_VX4=1`. Bản gas (`genericSTM32F103RC`) không có code VX4.

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
| Tín hiệu lửa | máy điện KHÔNG có: `gasSignal` = đang bật `Lệnh nhiệt` → chốt mồi hụt 75 s / chờ lửa không cắt nhầm |

Relay CH1 (`Lệnh gas` cũ): **tạm thời thợ bấm tay** (chủ máy 14/10). Đi dây contactor điện trở qua CH1 thì lệnh nhiệt tắt /
lỗi VX4 sẽ cắt hẳn nguồn điện trở — nên làm khi lắp máy thật.

## HMI máy điện (khác bản gas)

| Chỗ | Gas | Điện |
|---|---|---|
| Ô nhiệt màn rang | Gas · Thực xx % | **Nhiệt** · **Buồng xxx,x °C** (đọc W40097) |
| Dock | Lệnh gas · Có lửa / Không lửa | **Lệnh nhiệt** · **Đang nung / Tắt nhiệt** |
| Nút Dừng | Gas sẽ tắt / Gas vẫn bật | Nhiệt sẽ tắt / Nhiệt vẫn bật |
| Chú giải đồ thị | Gas % | Nhiệt % |
| Cảnh báo | — | **298** mất kết nối VX4 |
| 110CS | — | đổi model DOP-110CS (cùng 1024 × 600); không cổng mạng → dòng địa chỉ web tự ẩn |

## Đã kiểm (14/10/2026)

- `pio run -e dien`: đạt — RAM 83,6 %, Flash 43,2 %. Bản gas dựng lại: chỉ khác bộ lọc mã (mở 298), `test_stt_queue` đạt.
- HMI 110WS + 110CS: DIAScreen biên dịch đạt.
- **CHƯA thử với VX4 thật** (bàn thử không có VX4). Trước khi giao máy: cắm VX4, xem PV lên HMI, đổi `Nhiệt %` thấy SV
  trên VX4 đổi, rút cáp RS485 VX4 thấy mã 298 + relay CH1 cắt; nạp HMI 110CS lên panel 110CS thật.
