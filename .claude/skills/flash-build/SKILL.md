---
name: flash-build
description: Build firmware PlatformIO, kiểm tra RAM/Flash usage, parse lỗi compiler và báo cáo rõ ràng. Dùng trước khi flash lên STM32F103RC.
allowed-tools: Bash, Read
---

Build firmware và kiểm tra kết quả cho dự án OTL-06ALS (STM32F103RC).

## Bước 1 — Build

Chạy:
```
pio run -e genericSTM32F103RC 2>&1
```

Lưu toàn bộ output.

## Bước 2 — Phân tích kết quả build

**Nếu BUILD FAILED:**

Parse output tìm tất cả dòng `error:` và `warning:`. Với mỗi lỗi:
- File và dòng số
- Mô tả lỗi
- Đề xuất fix ngắn gọn (1 dòng)

Trình bày dạng bảng:
| File:Line | Loại | Mô tả | Gợi ý fix |
|-----------|------|-------|-----------|

Dừng tại đây và báo lỗi cho user.

**Nếu BUILD SUCCESS:**

Tiếp tục bước 3.

## Bước 3 — Kiểm tra RAM/Flash

Chạy:
```
pio run -e genericSTM32F103RC --target size 2>&1
```

Parse output dạng:
```
Memory region         Used Size  Region Size  %age Used
           FLASH:       XXXXX B       256 KB     XX.XX%
             RAM:       XXXXX B        20 KB     XX.XX%
```

Đánh giá:
| Tài nguyên | Đã dùng | Giới hạn | % | Trạng thái |
|-----------|---------|---------|---|-----------|
| FLASH | X KB | 256 KB | X% | 🟢/🟡/🔴 |
| RAM   | X KB | 20 KB  | X% | 🟢/🟡/🔴 |

Ngưỡng cảnh báo:
- 🟢 < 75% — an toàn
- 🟡 75–90% — cần chú ý
- 🔴 > 90% — nguy hiểm, có thể crash lúc runtime

## Bước 4 — Kiểm tra warnings quan trọng

Từ output build, lọc các warning liên quan đến:
- `unused variable` trong ISR hoặc interrupt handler
- `integer overflow` hoặc implicit conversion
- `array subscript out of bounds`
- `comparison between signed and unsigned`
- `-Wmaybe-uninitialized`

Liệt kê nếu có, bỏ qua các warning từ thư viện bên thứ ba (`.pio/libdeps/`).

## Bước 5 — Tổng kết

```
✅ BUILD SUCCESS
📦 Flash: XX KB / 256 KB (XX%)
🧠 RAM:   XX KB / 20 KB  (XX%)
⚠️  Warnings: N (N liên quan đến code dự án)
```

Nếu RAM > 15 KB (75%), nhắc chạy `/memory-check` để phân tích chi tiết.
