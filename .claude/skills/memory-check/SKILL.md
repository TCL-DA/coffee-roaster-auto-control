---
name: memory-check
description: Kiểm tra RAM và Flash usage cho STM32F103RC. Phân tích mảng lớn trong Define.h, cảnh báo khi gần giới hạn 20KB RAM / 256KB Flash.
allowed-tools: Bash, Read, Grep
---

Phân tích memory usage cho dự án STM32F103RC này.

## Bước 1 — Build và lấy kích thước

Chạy lệnh:
```
pio run -e genericSTM32F103RC --target size
```

Nếu build fail, báo lỗi và dừng.

## Bước 2 — Phân tích mảng lớn trong Define.h

Đọc `include/Define.h` và tìm tất cả khai báo mảng (`[]`). Tính kích thước mỗi mảng:
- `int16_t arr[N]` = N × 2 bytes
- `uint16_t arr[N]` = N × 2 bytes
- `uint8_t arr[N]` = N × 1 byte
- `bool arr[N]` = N × 1 byte

Liệt kê theo thứ tự từ lớn đến nhỏ.

## Bước 3 — Đánh giá

So sánh với giới hạn phần cứng:
- **RAM**: 20480 bytes (20 KB) — cảnh báo nếu > 16 KB (80%)
- **Flash**: 262144 bytes (256 KB) — cảnh báo nếu > 210 KB (80%)

Chú ý đặc biệt các mảng sau (đã biết là lớn):
- `sdBT[1500]`, `sdET[1500]`, `sdAirflow[1500]`, `sdGas[1500]`, `sdDrum[1500]`, `sdRorBT[1500]`, `sdVacuumSetFlag[1500]`, `sdVacuumSetpoint[1500]`
- `iMemHMI[60]` + `iMemHMI_CP[60]`
- `dAddress[200]` + `dAddress_CP[200]`
- `cAddress[200]` + `cAddress_CP[200]`

## Bước 4 — Đề xuất tối ưu

Nếu RAM > 16 KB, đề xuất:
1. Giảm kích thước mảng SD (1500 → 900 nếu chỉ cần 15 phút rang)
2. Gộp mảng `_CP` vào 1 struct để tiết kiệm padding
3. Dùng `uint8_t` thay `uint16_t` cho các giá trị 0–100% (airflow, gas, drum)
4. Chuyển string debug sang `F()` macro để đưa vào Flash

Trình bày kết quả dạng bảng rõ ràng với tổng cộng ước tính.
