# Đặc tính HMI Delta DOP (DOPSoft)

Tài liệu tham chiếu các đặc tính, thanh ghi điều khiển và quy ước của HMI Delta dòng DOP, lập trình bằng phần mềm DOPSoft. Dùng cho dự án OTL-06ALS (HMI nối Modbus, slave ID 1, USART1 @115200).

---

## Control Block (Khối điều khiển)

Control Block là dãy thanh ghi **liên tiếp** trên PLC/controller (hoặc bộ nhớ nội bộ HMI) cho phép điều khiển HMI từ bên ngoài. Bật trong DOPSoft: **[Options] > [Configuration] > [Control Status Block] > [Control Block]**, đặt Start Address (ví dụ `{Link2}1@D0` hoặc `$n` nội bộ).

Cấu hình hiện tại của dự án (Start Address `{Link2}1@W40050`):

| Offset | Địa chỉ | Mục | Bật |
|--------|---------|-----|-----|
| +0 | W40050 | **Screen No.** (số màn hình) | ✅ |
| +1 | W40051 | General Control | ✅ |
| +2 | W40052 | Curve Control | ✅ |
| +3 | W40053 | Sampling History Buffer | ✅ |
| +4 | W40054 | Clearing History Buffer | ✅ |
| +5 | W40055 | Recipe Control | ✅ |
| +6 | W40056 | Recipe Group Number | ✅ |
| +7 | W40057 | System Control | ✅ |
| — | — | Enhanced Recipe Control | ❌ |
| — | — | Enhanced Recipe Group Number | ❌ |

> Mỗi mục được tick sẽ chiếm 1 Word liên tiếp tính từ Start Address theo đúng thứ tự trên. Bỏ tick mục nào thì mục đó **không** chiếm địa chỉ (các mục sau dồn lên).

---

## Thanh ghi Screen No. (Số thứ tự màn hình)

Thành phần quan trọng nhất trong Control Block — điều khiển chuyển trang giao diện HMI từ controller bên ngoài (PLC) hoặc từ bộ nhớ nội bộ HMI.

### Chức năng
- Ghi một **số ID màn hình** vào thanh ghi này → HMI **lập tức** chuyển sang trang có ID tương ứng.
- Ví dụ: Screen No. map tới `D0`, ghi `1` vào `D0` → HMI nhảy về màn hình số 1.
- Ứng dụng: PLC tự đổi giao diện theo điều kiện vận hành (vd: tự nhảy trang "Cảnh báo" khi máy sự cố).

### Thông số kỹ thuật
- **Kiểu dữ liệu:** Word (16-bit). Toàn bộ bit b0–b15 đại diện số thứ tự màn hình.
- **Vị trí:** thanh ghi **đầu tiên** (offset +0) trong Control Block.
- Screen No. phải **duy nhất** cho mỗi trang, **không lặp lại** trong project.

### Giám sát (Status Block)
- Status Block (Status Area) có 1 thanh ghi tương ứng để **monitor** màn hình đang mở → PLC biết người vận hành đang ở trang nào.
- ⚠️ Địa chỉ Screen No. trong **Status Block KHÔNG được trùng** với Control Block (tránh xung đột dữ liệu ghi/đọc).

### Liên hệ phần tử khác
- Nút nhấn **Goto Screen** trên giao diện: chuyển trang trực tiếp tới một Screen No. đã định nghĩa (không cần qua PLC).

---

## Thanh ghi General Control (W40051)

Word 16-bit điều khiển chung — **mỗi bit là 1 chức năng** (bit-control), khác Screen No. (dùng cả Word làm số).

| Bit | Chức năng | Ý nghĩa |
|-----|-----------|---------|
| b0 | Enable/disable communication | Bật/tắt truyền thông |
| b1 | Enable/disable backlight | Bật/tắt đèn nền màn hình |
| b2 | Enable/disable buzzer | Bật/tắt còi buzzer |
| b3 | Clear alarm buffer | Xóa bộ đệm cảnh báo |
| b4 | Clear alarm counter | Xóa bộ đếm cảnh báo |
| b5 | Write to external storage immediately | Ghi ngay ra bộ nhớ ngoài (SD/USB) |
| b6 | Lock remote monitoring | Khóa giám sát từ xa |
| b8–b11 | Set user level | Đặt cấp người dùng (user level) |

> Lưu ý: bit-control nên dùng lệnh set/clear từng bit, tránh ghi cả Word đè mất các bit khác. b7 và b12–b15 không định nghĩa (reserved).

---

## Thanh ghi Curve Control (W40052)

Word 16-bit điều khiển vẽ/xóa đồ thị Curve — **bit-control**, mỗi bit ứng với 1 curve.

| Bit | Chức năng | Ý nghĩa |
|-----|-----------|---------|
| b0 | Curve sampling flag 1 | Cờ lấy mẫu (vẽ) curve 1 |
| b1 | Curve sampling flag 2 | Cờ lấy mẫu (vẽ) curve 2 |
| b2 | Curve sampling flag 3 | Cờ lấy mẫu (vẽ) curve 3 |
| b3 | Curve sampling flag 4 | Cờ lấy mẫu (vẽ) curve 4 |
| b8 | Curve clear flag 1 | Cờ xóa curve 1 |
| b9 | Curve clear flag 2 | Cờ xóa curve 2 |
| b10 | Curve clear flag 3 | Cờ xóa curve 3 |
| b11 | Curve clear flag 4 | Cờ xóa curve 4 |

> Sampling flag (b0–b3) bật → curve bắt đầu lấy mẫu/vẽ; clear flag (b8–b11) bật → xóa curve tương ứng. b4–b7, b12–b15 không định nghĩa. Dùng set/clear từng bit, không ghi đè cả Word.

---

## Thanh ghi Sampling History Buffer (W40053)

Word 16-bit điều khiển lấy mẫu cho **History Buffer** — **bit-control**, mỗi bit bật lấy mẫu 1 buffer lịch sử.

| Bit | Chức năng |
|-----|-----------|
| b0 | Sampling flag 1 of history buffer |
| b1 | Sampling flag 2 of history buffer |
| b2 | Sampling flag 3 of history buffer |
| b3 | Sampling flag 4 of history buffer |
| b4 | Sampling flag 5 of history buffer |
| b5 | Sampling flag 6 of history buffer |
| b6 | Sampling flag 7 of history buffer |
| b7 | Sampling flag 8 of history buffer |
| b8 | Sampling flag 9 of history buffer |
| b9 | Sampling flag 10 of history buffer |
| b10 | Sampling flag 11 of history buffer |
| b11 | Sampling flag 12 of history buffer |

> b0–b11 = 12 history buffer (1–12); bật bit → buffer đó lấy mẫu. b12–b15 không định nghĩa.
> **Sampling Cycle** đặt kèm trong cấu hình (mặc định ảnh = 100 ms) — chu kỳ lấy mẫu của history buffer.

---

## Thanh ghi Clearing History Buffer (W40054)

Word 16-bit điều khiển **xóa** History Buffer — **bit-control**, mỗi bit xóa 1 buffer lịch sử (cùng đánh số 1–12 như Sampling History Buffer).

| Bit | Chức năng |
|-----|-----------|
| b0 | Clear flag 1 of history buffer |
| b1 | Clear flag 2 of history buffer |
| b2 | Clear flag 3 of history buffer |
| b3 | Clear flag 4 of history buffer |
| b4 | Clear flag 5 of history buffer |
| b5 | Clear flag 6 of history buffer |
| b6 | Clear flag 7 of history buffer |
| b7 | Clear flag 8 of history buffer |
| b8 | Clear flag 9 of history buffer |
| b9 | Clear flag 10 of history buffer |
| b10 | Clear flag 11 of history buffer |
| b11 | Clear flag 12 of history buffer |

> b0–b11 = 12 history buffer (1–12); bật bit → xóa buffer đó. b12–b15 không định nghĩa.
> Cặp đôi với W40053 (Sampling): W40053 lấy mẫu, W40054 xóa — cùng tập 12 buffer.

---

## Thanh ghi System Control (W40057)

Word 16-bit điều khiển hệ thống — **hỗn hợp**: b0–b7 là giá trị (byte), b8–b10 là bit-control.

| Bit | Chức năng | Ý nghĩa |
|-----|-----------|---------|
| b0–b7 | Multi-language set value | Giá trị chọn ngôn ngữ (byte: số thứ tự ngôn ngữ) |
| b8 | Printer flag | Cờ in (kích hoạt máy in) |
| b9 | Printer form feed flag | Cờ đẩy trang máy in (form feed) |
| b10 | Enable DHCP again | Bật lại DHCP (xin IP động lần nữa) |

> b0–b7 dùng như **số** (set value chọn ngôn ngữ), b8–b10 là **cờ bit** riêng lẻ → khi ghi phải cẩn thận: đổi ngôn ngữ ghi byte thấp, bật cờ in set bit b8/b9 mà không phá byte ngôn ngữ. b11–b15 không định nghĩa.

---

## Lua macro

Các hàm Lua macro (account, đọc/ghi dữ liệu...) tách riêng sang [ref-hmi-lua-macro.md](ref-hmi-lua-macro.md).

---

## Ghi chú dự án OTL-06ALS

- Firmware ghi xuống HMI qua Modbus. Quy ước offset địa chỉ ghi xem [CLAUDE.md](CLAUDE.md) (mục Naming Conventions: `*_W` là địa chỉ register để ghi; nhiều chỗ dùng `+2000` cho vùng ghi HMI, `-1` do lệch 0/1-based).
- Bản đồ ngày tháng profile lên HMI: [ref-hmi-profile-date-map.md](ref-hmi-profile-date-map.md).
