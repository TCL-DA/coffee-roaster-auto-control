# Bảng hằng số PID_Airflow

Đọc từ `include/PID_Airflow.h` ngày 2026-07-30. **Chú thích trong file đã lệch ở vài chỗ** — bảng này
theo giá trị code thật, xem [rui-ro.md](rui-ro.md) R1.

## Step controller

| Hằng số | Dòng | Giá trị | Ý nghĩa & hệ quả khi đổi |
|---|---|---|---|
| `AIR_DEADBAND` | 49 | **3,0 Pa** | Trong dải này thì không nhích. **Hạ xuống** → đuổi theo nhiễu cảm biến, gió nhích qua nhích lại mãi. **Nâng lên** → áp hút đứng lệch đích luôn. Phải lớn hơn nhiễu còn lại sau Kalman. Chú thích ghi ±5 Pa là SAI. |
| `AIR_STEP` | 50 | **1,0 %** | Mỗi bước nhích. Nâng lên là vọt qua đích rồi dao động. |
| `AIR_COOL_NEAR_MS` | 51 | **3000 ms** | Nghỉ giữa 2 bước khi **gần** đích. |
| `AIR_COOL_FAR_MS` | 52 | **1500 ms** | Nghỉ giữa 2 bước khi **xa** đích. |
| `AIR_COOL_FAR_ERR` | 53 | **30,0 Pa** | Lệch từ mức này coi là "xa". Giữa 3 và 30 Pa thì nội suy tuyến tính. |
| `AIR_MIN` / `AIR_MAX` | 54-55 | **0 / 100 %** | Biên gió. |

**Tốc độ nhích thật** — con số hay bị hiểu sai nhất:

```
lệch ≥ 30 Pa : 1 % mỗi 1,5 s  = 0,67 %/giây   → đi 30 % mất  45 giây
lệch  ~3 Pa  : 1 % mỗi 3,0 s  = 0,33 %/giây   → đi 10 % mất  30 giây
```

Vòng loop khoảng 130 ms, nhưng **phần lớn các vòng không nhích gì** vì đang trong cooldown. Nói
"1 %/loop" là sai khoảng 20 lần.

## Bảng feed-forward

| Hằng số | Dòng | Giá trị | Ý nghĩa & hệ quả khi đổi |
|---|---|---|---|
| `FF_MAX_ENTRIES` | 58 | **50** | Trần số entry. Factory tune quét **101 bước** nên trần này nhỏ hơn số bước — xem [rui-ro.md](rui-ro.md) R3. |
| `FF_SP_MATCH` | 59 | **3,0 Pa** | Hai setpoint cách nhau trong khoảng này coi là **cùng một entry**. Biên thực tế hơi rộng hơn — xem R2. |
| `FF_DRIFT_THRESH` | 60 | **3,0 %** | Lệch từ mức này coi là hệ thống đã đổi → học lại nhanh (`count = 2`). Hạ xuống → bảng nhảy theo nhiễu; nâng lên → lưới lọc bẩn rồi mà bảng vẫn giữ số cũ. |
| `FF_FILE` | 61 | `/pid_ff.txt` | File trên thẻ. |
| `SNAP_BUF_DEFAULT` | 62 | **15,0 %** | Snap buffer khi chưa có dữ liệu thẻ. |
| (trần `count`) | 172 | **30** | Trọng số trung bình động chặn ở 30 để entry già không đóng băng. |
| (ước lượng khi thiếu) | 138 | **120 Pa ↔ 100 %** | Hệ số mồi `sp × 100/120`. **Phần cứng-cụ-thể** — máy khác quạt/lưới lọc thì phải xem lại. |
| (nhận `SNAPBUF`) | 232 | **[3 … 40]** | Ngoài dải thì bỏ, chặn file rác. |

## Factory auto-tune

| Hằng số | Dòng | Giá trị | Ý nghĩa |
|---|---|---|---|
| `FT_WARMUP_SEC` | 109 | **15 giây** | Hạ gió về 0 % rồi chờ lắng trước khi quét. |
| `FT_STEP_HOLD_SEC` | 65 | **3 giây** | Giữ mỗi mức gió. |
| `FT_SETTLE_SEC` | 66 | **2 giây** | Số giây **cuối** mỗi bước dùng để lấy mẫu → giây đầu bị bỏ để áp lắng. Đặt bằng `FT_STEP_HOLD_SEC` là mất hẳn phần chờ lắng. |
| `FT_AIR_START` … `END` / `STEP` | 67-69 | **0 → 100, bước 1** | 101 bước. |
| (ngưỡng ghi) | 357 | **`avgPa > 2 Pa`** | Dưới mức này coi là chưa đo được gì, không ghi entry. |
| (snap buffer tính lại) | 415-417 | **20 Pa / độ nhạy**, kẹp **[8 %, 25 %]** | Mục tiêu: để step controller tự bù đúng ~20 Pa cuối. |
| (điều kiện tính snap) | 411 | dải gió ≥ 5 % **và** dải áp ≥ 10 Pa | Mỏng hơn thì bỏ qua, giữ buffer cũ. |

**Tổng thời gian tune:** `15 + 101 × 3 = 318` giây ≈ **5 phút 18 giây**. Đổi `FT_STEP_HOLD_SEC` thì
nhân lại: mỗi giây thêm vào là **+101 giây** tổng.

## Biến trạng thái đáng nhớ

| Biến | Nghĩa |
|---|---|
| `air_current` | mức gió thật (float, khởi tạo 50 %); `airflowPercent` là bản ép về int đẩy ra ngoài |
| `prevSetpoint` | setpoint lần trước, khởi tạo **−1** để lần đầu luôn snap (delta = 999) |
| `stableTimer` | giây liên tục trong deadband; **`== 10`** thì học FF (đúng một lần mỗi đợt) |
| `saveTimer` | giây tích luỹ; **≥ 60** và bảng bẩn thì xin ghi thẻ |
| `stepCooldownMs` | mốc `millis()` được phép nhích tiếp |
| `ffDirty` | bảng có thay đổi chưa ghi |
| `pidSnapBuffer` | khoảng cố tình dừng thiếu khi snap |
| `ftState` | `FT_IDLE` / `FT_WARMUP` / `FT_RUNNING` / `FT_DONE` — khác `FT_IDLE` là lớp ③ giữ quyền |
| `selfTuneTickEn` | cờ ISR set, `pidSelfTuneTask()` tiêu thụ |
| `sdPendingCmd` | `SD_IDLE` / `SD_LOAD_FF` / `SD_SAVE_FF` |

## Cách tính nhanh khi chỉnh

**Muốn hội tụ nhanh hơn** — theo thứ tự nên thử:
1. Kiểm bảng FF có đúng chưa (snap sai là mọi thứ chậm theo). Chạy lại factory tune còn đáng hơn chỉnh
   hằng số.
2. Hạ `AIR_COOL_FAR_MS` (1500 → 1000) để đoạn xa đi nhanh hơn. Rủi ro thấp vì chỉ áp cho vùng lệch lớn.
3. Nâng `AIR_STEP` là lựa chọn **cuối** — nó tăng luôn biên độ vọt ở vùng gần đích.

**Muốn bớt dao động:**
1. Nâng `AIR_DEADBAND` (3 → 4-5 Pa) nếu nhiễu cảm biến lớn.
2. Nâng `AIR_COOL_NEAR_MS` (3000 → 4000) cho vùng gần đích bò chậm hơn.
3. Đừng hạ `AIR_STEP` xuống dưới 1 — `airflowPercent` là **int**, bước nhỏ hơn 1 % bị ép về 0 và
   controller đứng im.
