# Kiến trúc PID_Airflow

Nguồn: `include/PID_Airflow.h` (538 dòng, rà 2026-07-30). Đại lượng điều khiển là **`airflowPercent`
0–100 %**; phản hồi là **`Diff_Air`** (áp hút, Pa); đích là **`vacuumSetpoint_R`** (từ HMI, hoặc do
`calibProgram()` gán khi rang AUTO theo hồ sơ SD). Cờ bật/tắt cả module: **`vacuumSetFlag_R == 1`**.

## Mục lục
- [1. Step controller](#1-step-controller)
- [2. Bảng feed-forward](#2-bang-feed-forward)
- [3. Snap khi đổi setpoint](#3-snap-khi-doi-setpoint)
- [4. Factory auto-tune](#4-factory-auto-tune)
- [5. Lưu/đọc SD](#5-luu-doc-sd)
- [6. Tám điểm nối vào firmware](#6-tam-diem-noi-vao-firmware)

---

## 1. Step controller

`pidAirflowUpdate(setpoint, feedback)` — dòng 510. Gọi **mỗi loop** từ `analogIn()`.

```cpp
if (ftState != FT_IDLE) return;        // factory tune đang lái → không chạm
float error = setpoint - feedback;     // >0 = áp hút THẤP hơn đích → cần thêm gió
if (now >= stepCooldownMs) {
    if (error >  AIR_DEADBAND) air_current += AIR_STEP;   // rồi đặt cooldown
    if (error < -AIR_DEADBAND) air_current -= AIR_STEP;
}
airflowPercent = (int)air_current;
```

**Cooldown động** là phần quan trọng nhất và cũng hay bị bỏ qua nhất. Nội suy tuyến tính theo độ lệch:

```
|error| = AIR_DEADBAND (3 Pa)   → nghỉ AIR_COOL_NEAR_MS = 3000 ms
|error| ≥ AIR_COOL_FAR_ERR (30) → nghỉ AIR_COOL_FAR_MS  = 1500 ms
ở giữa: cooldown = 3000 − t×(3000−1500),  t = (|error|−3)/(30−3)
```

Nên **tốc độ nhích tối đa là 1 % / 1,5 giây ≈ 0,67 %/giây**, và khi đã gần đích thì chậm còn
1 % / 3 giây. Ý đồ rõ: đi nhanh khi còn xa, bò chậm khi gần để không vọt qua. Hệ quả cần biết: một
cú đổi setpoint cần 30 % gió sẽ mất **~45 giây** nếu không có snap.

Trong vùng deadband thì **giữ nguyên**, không nhích — đây là lúc lớp ② tính chuyện học.

## 2. Bảng feed-forward

Bảng `ffMap[50]`, mỗi entry là `{sp: Pa, air: %, count: số lần học}`.

**Tra cứu** — `ffLookup(sp)`, dòng 135:
- có entry khớp → trả `air` đã học.
- không có → ước lượng tuyến tính `sp × (100/120)`, tức **giả định 120 Pa ứng với 100 % gió**. Con số
  120 này là phần cứng-cụ-thể; máy khác quạt/khác lưới lọc thì sai, nên chỉ là mồi cho lần đầu.

**Tìm entry** — `ffFind(sp)`: quét cả bảng, lấy entry gần nhất. Lưu ý biên độ chấp nhận thực tế **lớn
hơn** `FF_SP_MATCH` một chút — xem [rui-ro.md](rui-ro.md) R2.

**Học** — `ffLearn(sp, air)`, dòng 144, ba nhánh:

| Tình huống | Xử lý |
|---|---|
| chưa có entry & bảng chưa đầy | thêm mới, `count = 1` |
| có entry, lệch **≥ `FF_DRIFT_THRESH`** (3 %) | coi như **hệ thống đã thay đổi** (lưới lọc bẩn, nhiệt độ khác) → lấy trung bình 2 giá trị rồi **đặt `count = 2`**, tức xoá gần hết ký ức cũ để học lại nhanh |
| có entry, lệch nhỏ | trung bình động có trọng số, `count` chặn ở **30** để entry già không đóng băng |

`ffMap[i].sp` cũng được trung bình lại mỗi lần học, nên tâm entry trôi dần theo thực tế.

**Ai gọi học?** `pidSelfTuneTick()` dòng 431: khi `|Diff_Air − setpoint| ≤ AIR_DEADBAND` thì
`stableTimer++`, và **đúng lúc `stableTimer == 10`** (10 giây ổn định) thì gọi `ffLearn`. So sánh `==`
nên mỗi đợt ổn định chỉ học **một lần** — ổn định 5 phút cũng không học lại. Ra khỏi deadband thì
`stableTimer = 0`.

Ghi thẻ: `saveTimer` chạy song song, cứ **≥ 60 giây** mà bảng còn `ffDirty` thì xin ghi một lần.

## 3. Snap khi đổi setpoint

`pidAirflowReset()` — dòng 482. Gọi khi **bật cờ vacuum** hoặc **setpoint đổi** (từ HMI, Modbus slave,
PC_Link, Preheat — xem mục 6).

```cpp
float target = ffLookup(sp);                       // mức gió đã học cho áp mới
float delta  = |sp − prevSetpoint|;                // lần đầu: 999 → luôn snap
if (delta > 30.0f) {                               // CHỈ snap khi đổi lớn
    if (sp > prevSetpoint) snapped = target − pidSnapBuffer;   // tăng áp: dừng NGẮN mức học
    else                   snapped = target + pidSnapBuffer;   // giảm áp: dừng TRÊN mức học
}
```

Hai chi tiết có chủ ý:

- **Cố tình dừng thiếu một khoảng `pidSnapBuffer`**, chứ không nhảy đúng mức đã học. Để step
  controller bù đoạn cuối — vừa tránh vọt, vừa cho lớp ② cơ hội học lại mức đúng.
- **Hướng snap tính theo setpoint cũ/mới, không theo `air_current`.** Comment tại dòng 480 nói rõ lý
  do: `air_current` có thể đang lệch so với bảng FF, dựa vào nó là snap sai chiều.

Kèm hai vòng kẹp để không nhảy quá xa trong một nhịp: khi tăng thì `constrain(snapped, air_current,
air_current + 20)`; khi giảm thì `constrain(snapped, AIR_MIN, air_current)`.

`pidSnapBuffer` mặc định 15 %, nhưng được **tính lại từ bảng FF** sau mỗi lần factory tune (mục 4).

## 4. Factory auto-tune

Máy tự quét toàn dải gió để dựng lại bảng FF từ đầu. Bấm từ HMI (`AUTO_PID_AIR_TU_R`).

```
FT_IDLE ──bấm BẬT──► FT_WARMUP ──15 giây──► FT_RUNNING ──quét xong──► FT_DONE ──1 nhịp──► FT_IDLE
   ▲                                                                                        │
   └────────────────────────── bấm TẮT bất kỳ lúc nào (pidFactoryTuneStop) ─────────────────┘
```

- **`FT_WARMUP`** — `pidFactoryTuneStart()` hạ gió **về 0 % ngay**, reset `tunePercent`, rồi đếm
  `FT_WARMUP_SEC = 15` giây cho hệ thống lắng hẳn trước khi quét.
- **`FT_RUNNING`** — mỗi bước gió giữ `FT_STEP_HOLD_SEC = 3` giây:

  | Giây trong bước | Việc |
  |---|---|
  | 0 | đặt `airflowPercent`, reset tích luỹ |
  | 1 | chờ áp lắng (bỏ qua số đo) |
  | 2–3 | lấy mẫu `Diff_Air` (chỉ nhận giá trị > 0) |
  | hết 3 giây | `avgPa` = trung bình; **chỉ ghi khi `avgPa > 2 Pa`**; sang bước kế |

  Bắt đầu quét thì **xoá sạch bảng cũ** (`ffMapSize = 0`). Tiến trình đẩy lên HMI qua `tunePercent`.
- **`FT_DONE`** — tính lại `pidSnapBuffer`, xin ghi SD, đặt `tunePercent = 100`, **tự tắt nút tuning
  trên HMI** (`AUTO_PID_AIR_TU_W = 0`), trả gió về 50 %.

**Tổng thời gian:** 15 s warmup + 101 bước × 3 s = **~5 phút 18 giây**.

**Tính lại snap buffer** — `_ftCalcSnapFactor()` dòng 398. Ý tưởng: muốn step controller tự bù đúng
khoảng **20 Pa cuối**.

```
độ nhạy (Pa/%) = (Pa lớn nhất − Pa nhỏ nhất) / (Air% lớn nhất − Air% nhỏ nhất)
snap buffer    = 20 Pa / độ nhạy,  kẹp trong [8 %, 25 %]
```

Bỏ qua nếu bảng có < 2 entry, hoặc dải gió < 5 %, hoặc dải áp < 10 Pa — dữ liệu mỏng thế thì độ nhạy
tính ra vô nghĩa.

## 5. Lưu/đọc SD

File `/pid_ff.txt`. Dòng đầu là snap buffer, các dòng sau là entry:

```
SNAPBUF:15.00
-30.0,15.20,8
-60.0,28.70,12
```

Hai chỗ đã phải vá vì thư viện STM32, **đừng "dọn" lại**:
- `dtostrf()` thay cho `%f` trong `snprintf` — Arduino STM32 mặc định **không hỗ trợ `%f`**.
- `strtok` + `atof` thay cho `sscanf("%f")` — `sscanf` với `%f` không chạy tin cậy trên STM32.

Khi đọc, `SNAPBUF` chỉ được nhận nếu nằm trong **[3, 40]** — chặn file rác làm snap loạn. Mỗi entry
chỉ nhận khi `sp > 0 && air >= 0 && count > 0`.

Ghi/đọc đều **không chạy trực tiếp**: đặt `sdPendingCmd` rồi `pidSDTask()` trong `loop()` mới thật sự
động vào thẻ. Lý do là ISR không được chạm SD.

## 6. Tám điểm nối vào firmware

Đã đối chiếu với code thật (không chỉ theo chú thích đầu file):

| Nơi gọi | Hàm | Việc |
|---|---|---|
| `src/main.cpp:69` | `pidLoadFromSD()` | nạp bảng lúc khởi động |
| `src/main.cpp:153` | `pidSelfTuneTask()` | nhịp 1 Hz ngoài ISR |
| `src/main.cpp:154` | `pidSDTask()` | thực thi đọc/ghi thẻ |
| `include/Program.h:40` | `selfTuneTickEn = true` | ISR **chỉ set cờ** |
| `include/AnalogConfig.h:296` / `:302` | `pidAirflowUpdate()` | mỗi loop, cả nhánh AUTO và nhánh tay |
| `include/Modbus_Master.h:385` | `pidAirflowReset()` | HMI đổi setpoint |
| `include/Modbus_Master.h:628-629` | `pidFactoryTuneStart/Stop()` | nút tuning trên HMI |
| `include/Modbus_Slave.h:249` · `PC_Link.h:334` · `Preheat.h:957` · `Preheat_PID.h:244` | `pidAirflowReset()` | Artisan / app / sấy lồng đổi setpoint |

Đáng chú ý: **`tunePercent` dùng chung** với tiến trình sấy lồng (`Preheat.h` ghi vào nó 6 chỗ) — xem
[rui-ro.md](rui-ro.md) R5.
