---
name: state-trace
description: Trace và phân tích state machine rang cà phê (progStep). Từ serial debug log hoặc code, xác định luồng chuyển trạng thái, phát hiện bước bị kẹt, thiếu điều kiện thoát, hay vòng lặp vô hạn.
allowed-tools: Read, Grep
---

Phân tích state machine trong `include/Program.h` (`programScan()` và các hàm liên quan).

## Bước 1 — Map toàn bộ states

Đọc `include/Define.h` và `include/Program.h`, liệt kê tất cả:

**progStep states:**
```
STP_DATA        (0)
STP_COOL_DOWN   (1)
STP_GAS         (3)
STP_CHECK       (4)
STP_CHARGE      (5)
STP_TP          (6)
STP_YELLOW      (7)
STP_FCS         (8)
STP_DEV         (9)
STP_DROP        (10)
STP_COOLING     (11)
STP_ESCAPE      (12)
STP_LOOP_1      (13)
STP_LOOP_2      (14)
```

Xác nhận không có số bị bỏ sót (2 bị skip?).

## Bước 2 — Vẽ sơ đồ chuyển trạng thái

Với mỗi `case STP_*` trong `programScan()`, xác định:
- **Điều kiện vào** (condition để chuyển từ state trước)
- **Hành động** thực hiện trong state này
- **Điều kiện thoát** → chuyển sang state nào
- **Deadlock risk**: state có thể kẹt mãi không?

Vẽ dạng:
```
[STP_CHARGE]
  Entry condition : CHARGE_BTN_R == 1
  Actions         : BT_CHARGE_SAVE=Temperature_BT, chargeTimerEn=1, timeRoastEn=1
  Exit condition  : → STP_TP (ngay lập tức)
  Deadlock risk   : Không — thoát ngay
```

## Bước 3 — Phân tích deadlock risks

Kiểm tra các state có điều kiện thoát phụ thuộc nhiều yếu tố:

**STP_COOL_DOWN**: Chờ `Temperature_BT <= chargeTemp_R_CV - turnGasPoint_R_CV`
- Nếu `chargeTemp_R_CV = 0` → skip (OK)
- Nếu BT không giảm (nhiệt quá cao) → kẹt mãi?
- Có timeout không?

**STP_CHECK**: Chờ `Temperature_BT` trong range `chargeTemp ± chTolerange`
- Nếu nhiệt tăng quá nhanh vượt range → có fallback không?
- Code hiện tại: `if(Temperature_BT > chargeTemp + chTolerange*5)` → reset về STP_DATA ✓

**STP_TP**: Chờ turning point
- Điều kiện: `timeRoast > ulimitTPTime && BT <= BT_TP_Pre`
- Nếu BT không bao giờ giảm → kẹt ở STP_TP?
- Có timeout escape không?

**STP_LOOP_1/2**: 
- Điều kiện thoát là gì?
- Có bị kẹt nếu sensor lỗi không?

## Bước 4 — Kiểm tra timer-based transitions

Tìm các state dùng timer để tự động chuyển:
- `chargeTimerEn` / `chargeTimer` → CHARGE valve tự đóng sau `chargeDuration_R`
- `dropTimerEn` / `dropTimer` → DROP valve tự đóng
- `escapeTimerEn` / `escapeTimer`
- `coolTimerEn` / `coolTimer`

Với mỗi timer: xác nhận timer được reset đúng chỗ, không bị enable/disable nhầm.

## Bước 5 — Phân tích sub-state machines

Kiểm tra các state machine phụ:

**coolStep** (cooling sequence):
- Liệt kê các bước `STP_COOLING`, `STP_ESCAPE_ON`, `STP_ESCAPE_OFF`
- Điều kiện thoát từng bước

**abStep** (afterburner):
- `STP_ON_AB`, `STP_WAIT_AB`, `STP_DELAY_AB`

**aLoaderStep** (auto loader):
- Các bước feeder/destoner

## Bước 6 — Kiểm tra concurrent state

Xác nhận các state machine chạy song song (`progStep`, `coolStep`, `abStep`) không conflict:
- Có race condition trên shared variables không? (`gasPercent`, `airflowPercent`)
- `naviSourceGAS` được đặt đúng trong từng state không?

## Bước 7 — Nếu có serial log

Nếu người dùng cung cấp serial log (chuỗi `STEP_STRING`), parse và trace:
```
RESET DATA → BT COOLS DOWN → WAITGAS → BT HEATUP → WAIT CHARGE → CATCH TP → CATCH YELLOW → ...
```
Xác định bước nào mất thời gian bất thường, bước nào bị repeat.

## Bước 8 — Tổng kết

Đưa ra:
- Danh sách state có nguy cơ deadlock + đề xuất thêm timeout
- State machine diagram dạng text
- Gợi ý thêm debug output tại các điểm chuyển trạng thái quan trọng
