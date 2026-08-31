---
name: bug-report
description: Phân tích serial debug output từ máy rang để xác định nguyên nhân crash, freeze, hoặc hành vi sai. Nhận chuỗi log làm argument hoặc từ clipboard.
allowed-tools: Read, Grep
---

Phân tích serial debug log từ firmware OTL-06ALS để tìm nguyên nhân lỗi.

## Input

Log được cung cấp qua:
- **Argument trực tiếp**: `/bug-report <nội dung log>`
- **Hoặc**: user paste log vào chat sau khi gọi skill

Nếu không có log, hỏi user paste log serial (từ `pio device monitor` hoặc terminal 9600 baud).

## Bước 1 — Parse cấu trúc log

Nhận diện các loại dòng trong log:

**Dòng loop timing:**
```
Loop: 87ms | Charge: 12 | Roast: 245 | CalSD: 34
```
→ Trích: loop time, các timer đang chạy, thời gian rang hiện tại

**Dòng Modbus error:**
```
ERRO HMI DELTA 0 46
ERRO HMI INTERNAL MEMORY DELTA
ERROR READ BT
```
→ Xác định node lỗi (HMI / BT / ET / Drum / Air / Relay)

**Dòng state machine:**
```
RESET DATA
BT COOLS DOWN
WAITGAS
BT HEATUP
WAIT CHARGE
CATCH TP
CATCH YELLOW
...
```
→ Trace luồng `progStep`

**Dòng SD:**
```
OPEN OK / OPEN FAIL
SUCCESS / FAIL
REOK / READFAIL
DATA / PROPERTIES
```

**Dòng khởi động:**
```
=> Analog OK
=> Modbus Slave RTU OK
=> RESET DATA
```

## Bước 2 — Xác định vấn đề

Tìm các pattern bất thường:

**Loop time bất thường:**
- Loop > 200ms → Modbus timeout hoặc SD blocking
- Loop đột ngột tăng → tìm dòng trước đó, xác định function nào gây ra

**Modbus errors lặp lại:**
- Cùng node lỗi nhiều lần liên tiếp → cáp RS485 / địa chỉ sai / baud rate sai
- Lỗi xen kẽ thành công → nhiễu RS485, cần thêm termination resistor

**State machine bị kẹt:**
- Cùng một STEP_STRING lặp lại > 30 giây mà không chuyển → deadlock
- State nhảy lùi bất thường → điều kiện thoát bị vi phạm

**Crash / reset dấu hiệu:**
- Log đột ngột bắt đầu lại từ `=> Analog OK` → MCU reset (watchdog hoặc HardFault)
- Khoảng trống dài trong log → freeze (loop block)

**SD lỗi:**
- `OPEN FAIL` → SD card không có hoặc file corrupt
- `READFAIL` → profile số không tồn tại
- Nhiều `FAIL` liên tiếp → SD card bị nhả khi máy rung

## Bước 3 — Tra cứu context trong code

Dựa trên lỗi tìm được, đọc phần code liên quan trong:
- `include/Program.h` — state machine, SD read/write
- `include/Modbus_Master.h` — Modbus error handlers
- `include/Define.h` — giá trị các hằng số liên quan

## Bước 4 — Tính toán thống kê (nếu log đủ dài)

- Loop time: min / max / trung bình
- Modbus error rate: số lỗi / tổng lần gọi (ước tính)
- Thời gian ở mỗi state (từ STEP_STRING)

## Bước 5 — Báo cáo

Trình bày:

```
🔍 PHÂN TÍCH LOG

📊 Thống kê:
  - Thời gian log: X giây
  - Loop time: avg Xms, max Xms
  - Modbus errors: X lần

🐛 Vấn đề phát hiện:
  1. [CRITICAL] Mô tả — dòng log liên quan
  2. [WARNING]  Mô tả — dòng log liên quan
  3. [INFO]     Mô tả

🔧 Đề xuất xử lý:
  1. Vấn đề 1 → cách fix cụ thể (file:line nếu biết)
  2. Vấn đề 2 → ...

📋 Timeline rang (nếu có):
  00:00 CHARGE
  02:15 TP (185°C)
  05:30 YELLOW (165°C)
  ...
```
