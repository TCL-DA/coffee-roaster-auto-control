# OTL Serial Terminal — panel Modbus Relay

Bản thiết kế cho phần mới của `tools/otl_serial_terminal.py`: dò tìm, đọc/ghi cấu hình
và bật/tắt thử module relay 8 kênh Waveshare Modbus RTU Relay (B), giao thức V3.

- `main-window.html`: màn chính 1400×1000, có nút đổi tab và Light/Dark. Tham số URL:
  `?tab=scan|config|test`, `&theme=dark`, `&panel=only`.
- `relay-panel-states.html`: đặt 3 tab cạnh nhau để so sánh.

## Bố cục

- Thanh công cụ giữ nguyên bản cũ, có thêm công tắc **Modbus Relay** (mặc định bật).
- Hàng giữa gồm terminal bên trái (co giãn) và panel **Modbus Relay** bên phải, rộng 452 px.
  Tắt công tắc thì terminal chiếm lại toàn bộ bề ngang.
- Ô gửi thêm lựa chọn đuôi **+CRC16** để gõ tay khung Modbus mà không phải tự tính CRC.

## Panel

Đầu panel luôn hiện:
- chip trạng thái thiết bị (xanh khi đã xác nhận, xám khi chưa có, cam khi mất trả lời),
- ô **ID đích**,
- ô **Chờ trả lời (ms)**.

| Tab | Nội dung |
|---|---|
| Tìm thiết bị | Phạm vi (cổng đang chọn / mọi cổng) · cách dò (broadcast / hỏi từng ID + dải ID) · ô chọn baud × parity · nút Quét / Dừng · thanh tiến độ · danh sách kết quả, mỗi dòng có nút Dùng |
| Cấu hình | Cấu hình đang chạy: địa chỉ, tốc độ, parity, giá trị thô 0x2000, phiên bản, cổng đang giao tiếp · ghi cấu hình mới: mẫu có sẵn, địa chỉ, baud, parity, broadcast có cảnh báo, nút ghi bấm hai lần |
| Test relay | Tự đọc trạng thái mỗi 1 s · 8 ô kênh (Bật / Tắt / Đảo, ô xanh khi đang bật) · cả 8 kênh · nhấp nháy (kênh, kiểu, ms) · chạy thử lần lượt CH1→CH8 |

## Quy tắc tương tác

- Quét chỉ gửi lệnh ĐỌC (FC03 thanh ghi 0x4000). Thấy thiết bị ở một tổ hợp baud/parity thì
  dừng thử các tổ hợp còn lại.
- Thấy module thì tự dùng luôn: điền ID đích, giữ cổng ở cấu hình vừa tìm được, đồng bộ lại
  thanh công cụ, rồi đọc trạng thái 8 kênh.
- Ghi cấu hình phải bấm hai lần; lần bấm đầu đổi nút sang màu cam "Bấm lần nữa để ghi" trong 4 s.
  Ghi xong thì tool tự chuyển cổng sang cấu hình mới và đọc lại để xác nhận. Nếu module hiểu
  mã parity ngược tài liệu thì tool tự ghi lại cho đúng.
- Mọi khung TX/RX hiện trong terminal kèm chú thích. Riêng lúc quét và lúc tự đọc định kỳ thì
  chỉ ghi dòng tóm tắt, không in từng khung.
- Khi panel đang chạy tác vụ, lệnh qua API/MCP có đụng tới cổng sẽ bị trả `409 modbus_busy`.

## Token (trùng hằng số trong code)

| Token | Light | Dark | Hằng CTk |
|---|---|---|---|
| card | #FFFFFF | #2C2C2E | `GLASS_CARD` |
| inner | #F6F6FB | #242426 | `GLASS_INNER` |
| border | #E6E6EC | #3A3A3C | `CARD_BORDER` |
| field | #EFEFF4 | #3A3A3C | `FIELD_BG` |
| on-bg (ô kênh đang bật) | #EAF8EE | #1F3526 | `ON_BG` (mới) |
| seg-track | #E3E3E8 | #3A3A3C | `SEG_TRACK` (mới) |
| warn-bg / warn-text | #FFF4E5 / #8A4B00 | #3A2A12 / #FFB340 | `WARN_BG` / `WARN_TEXT` (mới) |
| blue / green / orange | #007AFF / #34C759 / #FF9500 | như Light | `BLUE` / `GREEN` / `ORANGE` |

Bo góc: card 18 · ô trong 14 · nút 12 · ô nhập 9. Font: Segoe UI và Consolas.
Không dùng bóng đổ, không dùng nút gradient.
