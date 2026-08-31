---
name: define-audit
description: Kiểm tra Define.h để tìm biến không dùng, biến thiếu cặp _CP, magic numbers, và dead variables tích lũy theo thời gian. Define.h có ~2000 dòng nên cần audit định kỳ.
allowed-tools: Read, Grep
---

Audit file `include/Define.h` cho dự án OTL-06ALS.

## Bước 1 — Thu thập tất cả tên biến trong Define.h

Đọc `include/Define.h` toàn bộ (dùng offset/limit 200 dòng mỗi lần).

Lập danh sách:
- Tất cả biến toàn cục (loại trừ phần bị comment out)
- Tất cả `#define` constants
- Tất cả macro (`BUZZ_ON`, `CH1_RL_ON`, ...)

## Bước 2 — Tìm biến thiếu cặp _CP

Naming convention: mọi biến đọc từ HMI đều có cặp `_R` + `_R_CP`.

Tìm tất cả biến có tên `*_R` (không phải `*_R_CP`, `*_R_CV`, `*_W`).
Với mỗi `foo_R`, kiểm tra xem `foo_R_CP` có được khai báo không.

Báo cáo các `_R` biến thiếu `_R_CP` tương ứng — đây thường là lỗi copy-paste.

## Bước 3 — Tìm biến không được dùng

Search tên từng biến trong toàn bộ source (trừ chỗ khai báo):
```
Grep pattern: tên_biến
Files: include/*.h, src/*.cpp
```

Biến không xuất hiện ở bất kỳ file nào ngoài Define.h → **dead variable**.

Ưu tiên kiểm tra:
- Biến có tên gợi ý feature cũ (VD: `damper_*`, `PLC_*`, `old_*`)
- Mảng lớn không được dùng (lãng phí RAM)
- Biến `bool` flag không bao giờ được set

## Bước 4 — Tìm magic numbers trong Define.h

Tìm các `#define` có giá trị số không có comment giải thích:
- Địa chỉ Modbus register (ví dụ: `#define SOME_W 42`)
- Timeout value (ví dụ: `#define TIMER_X 300`)
- Threshold nhiệt độ cứng

Kiểm tra các giá trị có ý nghĩa vật lý (°C, Pa, ms) nhưng không có đơn vị trong tên hoặc comment.

## Bước 5 — Kiểm tra nhóm biến SD arrays

Các mảng SD size 1500 là **~15 KB RAM**. Kiểm tra:
- `sdBT[1500]`, `sdET[1500]`, `sdAirflow[1500]`, `sdGas[1500]`, `sdDrum[1500]`
- `sdRorBT[1500]`, `sdVacuumSetFlag[1500]`, `sdVacuumSetpoint[1500]`

Tất cả 8 mảng có được dùng không? Nếu `sdVacuumSetFlag` hoặc `sdVacuumSetpoint` chỉ dùng một phần, tính RAM lãng phí.

Nếu rang tối đa 20 phút (1200 giây), size 1500 thừa 300 entries → có thể giảm xuống 1200 để tiết kiệm ~2.4 KB RAM.

## Bước 6 — Kiểm tra phần bị comment out

Đọc phần đầu Define.h (thường là ~200 dòng comment cũ).

Xác định:
- Đây có phải là "archive" intentional không?
- Có biến nào trong phần comment out vẫn cần thiết không?
- Nếu không cần → đề xuất xóa để giảm file size và confusion

## Bước 7 — Kiểm tra duplicate definitions

Tìm các `#define` bị định nghĩa 2 lần với giá trị khác nhau (compiler warning thường bỏ qua trên Arduino).

## Bước 8 — Tổng kết

```
📋 DEFINE.H AUDIT

📏 Thống kê:
  - Tổng biến khai báo: X
  - Tổng #define: X
  - Dòng bị comment out: X / tổng X dòng

🐛 Vấn đề:
  🔴 Critical (X):
     - foo_R thiếu foo_R_CP tại dòng X
  🟡 Warning (X):
     - biến dead: bar, baz, ...
     - magic number: #define X 42 (không có comment)
  🟢 Info (X):
     - SD arrays có thể giảm từ 1500 → 1200 (tiết kiệm X KB)

🗑  Đề xuất xóa:
  - Phần comment out dòng 1–199 (archive, không cần thiết)
  - Biến dead: [danh sách]
```
