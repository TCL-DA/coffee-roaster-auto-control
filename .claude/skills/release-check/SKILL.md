---
name: release-check
description: Checklist an toàn trước khi flash firmware lên máy rang thật. Kiểm tra debug flags, gas limits, SD files, timing, và các cài đặt nguy hiểm nếu để sai khi vận hành thực tế.
allowed-tools: Read, Grep, Bash
---

Chạy checklist trước khi flash firmware OTL-06ALS lên máy rang thật.

⚠️  **QUAN TRỌNG**: Không flash lên máy đang có cà phê hoặc đang nóng nếu chưa pass hết checklist này.

---

## Bước 1 — Build production

Chạy build và kiểm tra thành công:
```
pio run -e genericSTM32F103RC 2>&1
```

Nếu có lỗi → **DỪNG**. Báo lỗi, không tiếp tục.

Chạy kiểm tra size:
```
pio run -e genericSTM32F103RC --target size 2>&1
```

RAM > 90% (18.4 KB) → **CẢNH BÁO ĐỎ** — nguy cơ stack overflow khi chạy.

---

## Bước 2 — Kiểm tra debug flags

Đọc `include/Define.h` và `src/main.cpp`.

| Item | Yêu cầu | Kiểm tra |
|------|---------|---------|
| `enDebug` default value | `= 0` hoặc `= false` | Grep `enDebug` trong Define.h |
| `// enDebug = true` | Không có dòng bật debug hardcode | Grep trong tất cả .h và .cpp |
| Serial print trong ISR | Không có | Grep `SerialComputer.print` trong `timerPoll_1000ms` |

Debug bật khi vận hành → tốn CPU → loop time tăng → nhiệt độ đọc chậm.

---

## Bước 3 — Kiểm tra gas safety limits

Đọc `include/Define.h` tìm `maxGasSet_R` default value.

| Item | Yêu cầu | Ghi chú |
|------|---------|---------|
| `maxGasSet_R` default | ≤ 100, > 0 | Giới hạn DAC gas tối đa |
| Gas slew rate constants | Không bị comment out | Trong `AnalogConfig.h` |
| `GAS_CALIB_STEP_PCT` | ≤ 10 | Bước nhảy gas auto tối đa |

Gas limit = 0 → gas không hoạt động. Gas limit > 100 → không có giới hạn (nguy hiểm).

---

## Bước 4 — Kiểm tra Modbus slave config

Đọc `include/Modbus_Slave.h` và `include/Define.h`.

| Item | Yêu cầu |
|------|---------|
| `modbusBaud_R` default | Khớp với cài đặt Artisan PC (thường 9600 hoặc 38400) |
| `modbusID_R` default | Khớp với cài đặt Artisan (thường 1) |
| `PC_CONTROL_BTN_R` default | `= 0` (HMI control, không phải PC) |

PC_CONTROL = 1 khi khởi động → Artisan có thể bật gas ngẫu nhiên.

---

## Bước 5 — Kiểm tra timer defaults

Tìm trong `include/Define.h` các giá trị default của timers:

| Timer | Giá trị hợp lý | Ghi chú |
|-------|---------------|---------|
| `chargeDuration_R` | 3–10 giây | Thời gian van charge mở |
| `dropDuration_R` | 3–10 giây | Thời gian van drop mở |
| `escapeDuration_R` | 10–60 giây | Thời gian van escape |
| `coolTimer_R` | 60–300 giây | Thời gian quạt làm mát |
| `timerLimit` | 3000 | Không đổi |

Timer = 0 → van không bao giờ tự đóng (van mở mãi).

---

## Bước 6 — Kiểm tra hardware variant

Đọc đầu `include/Define.h`:

```cpp
// #define V300 true
// #define V400 true   ← cái nào đang active?
```

Xác nhận variant đang dùng khớp với phần cứng thực tế (V300 hay V400).
Sai variant → pin assignment sai → relay đấu nhầm → nguy hiểm.

---

## Bước 7 — Kiểm tra không có code test/debug hardcode

Grep trong tất cả file `include/*.h` và `src/*.cpp`:

```
Tìm: delay(1000)    → delay lớn bất thường trong production code
Tìm: while(1)       → infinite loop không có thoát
Tìm: for(;;)        → tương tự
Tìm: TEST           → biến hoặc flag test
Tìm: HACK           → workaround tạm thời
Tìm: TODO           → chức năng chưa hoàn thiện
```

Mỗi kết quả → xem xét có an toàn không.

---

## Bước 8 — Kiểm tra git status

Chạy:
```
git status
git diff --stat
```

- Có file bị sửa chưa commit → nhắc commit trước khi flash
- Xác nhận đang ở đúng branch

---

## Bước 9 — Tổng kết checklist

```
🚀 RELEASE CHECK — OTL-06ALS

✅ / ❌ Build success
✅ / ❌ RAM < 90% (XX KB / 20 KB)
✅ / ❌ enDebug = 0
✅ / ❌ maxGasSet_R hợp lệ
✅ / ❌ PC_CONTROL default = 0
✅ / ❌ modbusBaud & ID hợp lệ
✅ / ❌ Timer defaults hợp lý
✅ / ❌ Hardware variant đúng (V300/V400)
✅ / ❌ Không có debug/test hardcode
✅ / ❌ Git clean / đã commit

KẾT QUẢ: [PASS ✅ — an toàn để flash] / [FAIL ❌ — xem lại các mục đỏ]
```

Nếu có bất kỳ ❌ → **không flash** cho đến khi xử lý xong.
