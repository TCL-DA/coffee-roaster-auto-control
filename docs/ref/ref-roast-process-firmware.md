# Quy trình vận hành máy rang — state machine firmware (`progStep`)

Tài liệu **nguồn sự thật** về quy trình rang, đúc kết từ `programScan()` trong
`include/Program.h` + định nghĩa `STP_*` trong `include/Define.h`.

> Đây là quy trình THẬT do firmware STM32 chạy. Mọi lớp hiển thị (HMI, Artisan)
> chỉ **phản chiếu** state machine này, KHÔNG tự chạy logic rang. Xem
> `docs/ref/ref-roast-lab-hmi-architecture.md` §6 cho phần HMI phản chiếu.
>
> Cập nhật: 2026-07-14.

---

## 1. Danh sách trạng thái (`progStep`)

Định nghĩa ở `Define.h`. Lưu ý **số 2 bị bỏ** (không dùng), giữ nguyên theo code.

| Hằng | Giá trị | `STEP_STRING` | Ý nghĩa |
|---|---|---|---|
| `STP_DATA` | 0 | `RESET DATA` / `NONE` | Nghỉ / reset dữ liệu mẻ mới |
| `STP_COOL_DOWN` | 1 | `BT COOLS DOWN` | Chờ trống hạ nhiệt về mức charge (auto-charge) |
| `STP_GAS` | 3 | `WAITGAS` | Chờ tín hiệu lửa sau khi mồi |
| `STP_CHECK` | 4 | `BT HEATUP` | Chờ BT vào cửa sổ nhiệt charge |
| `STP_CHARGE` | 5 | `WAIT CHARGE` | Chờ đổ hạt vào trống |
| `STP_TP` | 6 | `WAIT TP` / `CHECK TP` | Bắt Turning Point |
| `STP_YELLOW` | 7 | `WAIT YELLOW` | Chờ Dry End (hạt vàng) |
| `STP_FCS` | 8 | `WAIT FCS` | Chờ First Crack |
| `STP_DEV` | 9 | `DEV` | Pha phát triển (tới khi DROP) |
| `STP_DROP` | 10 | `DROP` | (mốc xả — xử lý ngoài switch) |
| `STP_COOLING` | 11 | — | (dùng cho `coolStep` phụ) |
| `STP_ESCAPE` | 12 | — | (dùng cho xả khí) |
| `STP_LOOP_1` | 13 | `LOOP` / `NONE` | Quyết định rang tiếp hay dừng (AUTO) |
| `STP_LOOP_2` | 14 | `WCANCEL` | Chờ van drop đóng để rang mẻ kế |

State machine phụ chạy song song: `aLoaderStep` (auto-loader), `coolStep`
(cooling), `abStep` (afterburner).

---

## 2. Luồng chính (chỉ chạy khi `START_BTN_R == 1`)

```
STP_DATA(0)  RESET: xoá mốc, timeRoast=0, rorCtrl_reset, clear trend, KHOÁ nút HMI
   │         AUTO → nạp maxGas từ profile · SAVE → bật ghi log SD
   ▼
STP_COOL_DOWN(1)  Nếu chargeTemp>0: chờ BT ≤ (chargeTemp − turnGasPoint)
   │   ├─ đủ nguội + có lửa (READ_CH1=HIGH) → gas=50%, mở gas → STP_GAS
   │   └─ chargeTemp=0 (charge tay) → nhảy thẳng → STP_CHARGE
   ▼
STP_GAS(3)  Bếp thường (burnerPremix=0): chờ READ_CH1=LOW (có lửa) → gas=preGas → STP_CHECK
   │        Bếp premix: không chờ, gas=preGas → STP_CHECK
   ▼
STP_CHECK(4)  Chờ BT vào cửa sổ: chargeTemp ± chTolerance → tự MỞ CHARGE + buzzer → STP_CHARGE
   │   ⚠ BT vọt > chargeTemp + 5×chTolerance → CẮT GAS, quay lại STP_DATA (làm lại)
   ▼
STP_CHARGE(5)  Đặt nguồn điều khiển: AUTO→auto, SAVE→VR tay
   │   Khi CHARGE mở: lưu BT_CHARGE, chạy timeRoast, bật trend sample, buzzer,
   │   bật chargeTimer (van tự đóng), ghi mốc CHARGE (RTC giờ/phút) → STP_TP
   ▼
STP_TP(6)  Chờ timeRoast>ulimitTPTime & BT<ulimitTPTemp; theo BT giảm (BT_TP_Pre)
   │   BT ngừng giảm & tăng lại → lưu TP (nhiệt+thời gian) → STP_YELLOW
   ▼
STP_YELLOW(7)  BT ≥ yellowPhase → lưu Dry End → STP_FCS
   ▼
STP_FCS(8)  BT ≥ fcsPhase → lưu FCs → STP_DEV
   │   (AUTO + autoLoader: tại đây bắt đầu auto-cân mẻ kế nếu phễu đủ)
   ▼
STP_DEV(9)  Liên tục tính TIME_DEV = timeRoast − TIME_FCS; %DEV = devTime×1000/timeRoast
   │   Ở đây cho tới khi DROP
   ▼
── DROP (xử lý ngoài switch, khi progStep ≥ STP_YELLOW) ──
   AUTO: BT ≥ DROP_PRO_R → tự MỞ DROP; BT ≥ (DROP_PRO_R − preCool) → tự bật cooling/mixer
   Khi DROP (nút hoặc auto): lưu BT_DROP/time, trả điều khiển về VR, khôi phục vacuum PID,
   dừng đồng hồ, tắt trend, bật cooling, buzzer, bật dropTimer
   ├─ SAVE → tắt START, hoàn tất log SD (progStep=0)
   └─ AUTO → STP_LOOP_1
   ▼
STP_LOOP_1(13)  loop_R ≤ 1 → hết mẻ: tắt START, mở khoá HMI, về STP_DATA
   │            loop_R > 1 → loop_R−−, → STP_LOOP_2
   │            (loader FAIL → huỷ rang, về STP_DATA)
   ▼
STP_LOOP_2(14)  Chờ van drop đóng hẳn (waitDropcloseTi>20) → STP_DATA → TỰ rang mẻ kế
   │            (START=0 giữa chừng → huỷ, mở khoá)
```

**Bật trend SỚM**: khi `progStep≥STP_GAS` và BT còn cách charge ≤ `TREND_PRECHARGE_BAND`
(10°C), bật sample để ghi cả đoạn tiến tới charge (mỗi mẻ 1 lần, `trendPreStarted`).

---

## 3. Lớp an toàn chạy SONG SONG (ưu tiên cao nhất, mỗi vòng quét)

Chạy **trước** switch `progStep`, không phụ thuộc chế độ:

- **Trống/quạt cưỡng bức** (`forceDrumFanOnFlag`): BT **hoặc** ET > 80°C mà quạt tắt
  → tự bật quạt/trống. Không để trống nóng đứng im.
- **Cắt lửa khẩn** (`fireCutFlag`, set bởi ISR): cắt gas ngay + báo nguyên nhân:
  - BT > 250°C → `STT_ERR_FIRE_ALARM` (401).
  - ET > 300°C & BT < 150°C → `STT_TEMP_DIVERGENCE` (267) — nghi lỗi cảm biến.
  - ET > 350°C → `STT_TEMP_ET_HIGH` (264).
- **Preheat** (`preheat()`): chỉ chạy khi **không** rang (`START_BTN_R==0`).
- **Van tự đóng theo timer**: `chargeTimer` / `dropTimer` / `escapeTimer` / `coolTimer`
  — mỗi van mở xong tự đếm rồi đóng, không cần thao tác tay.

---

## 4. Hai chế độ vận hành (`progStatus`)

| Chế độ | Nguồn điều khiển | Hành vi |
|---|---|---|
| **AUTO** (`STT_PROGRAM_AUTO`) | Tự động theo **profile SD** | Auto-charge (chờ đạt nhiệt), auto-drop (`BT≥DROP_PRO_R`), auto pre-cool, **auto-loop nhiều mẻ** (`loop_R`), auto-cân nạp mẻ kế; áp trần gas `maxGas` từ profile |
| **SAVE** (`STT_PROGRAM_SAVE`) | **Biến trở tay (VR)** | Thợ chỉnh gas/gió/drum bằng tay; firmware **ghi lại** curve thành profile mới trên SD (log theo giây) |

Chuyển nguồn điều khiển (`naviSourceGAS/DRUM/AIR`): AUTO dùng `SOURCE_AI_AUTO`,
SAVE + lúc DROP/abort dùng `SOURCE_AI_VR` (trả quyền cho biến trở tay).

---

## 5. Mốc rang & cách phát hiện (quan trọng cho HMI)

| Mốc | Cách firmware phát hiện | Lưu vào |
|---|---|---|
| **CHARGE** | Nút CHARGE mở (tay hoặc auto ở STP_CHECK) | `BT_CHARGE_SAVE`, RTC giờ/phút |
| **TP** (Turning Point) | BT **ngừng giảm và tăng trở lại** (sau `ulimitTPTime`) | `BT_TP_SAVE`, `TIME_TP_SAVE` |
| **Dry End / Yellow** | BT ≥ `yellowPhase_R_CV` (ngưỡng nhiệt) | `BT_YELLOW_SAVE`, `TIME_YELLOW_SAVE` |
| **FCs** (First Crack) | BT ≥ `fcsPhase_R_CV` (ngưỡng nhiệt) | `BT_FCS_SAVE`, `TIME_FCS_SAVE` |
| **DROP** | BT ≥ `DROP_PRO_R` (AUTO) hoặc nút DROP | `BT_DROP_SAVE`, `TIME_DROP_SAVE` |
| **%DEV** | `(timeRoast − TIME_FCS) × 1000 / timeRoast` (per mille) | `PER_DEV_SAVE` |

> **Mốc do FIRMWARE quyết định**, không phải HMI. HMI đọc mốc qua mã trạng thái
> `STT_EVENT_*` (81–95) và các thanh ghi `*_SAVE`, **không tự tính lại**.

---

## 6. Huỷ / thoát

- **Huỷ bất kỳ lúc nào**: `START_BTN_R==0` khi đang rang → dừng mọi timer,
  `progStep=0`, `aLoaderStep=0`, trả điều khiển về VR, khôi phục vacuum PID, mở
  khoá nút HMI.
- **Auto-charge thất bại** (BT vọt quá nhanh ở STP_CHECK) → cắt gas, về STP_DATA.
- **Loader FAIL** (AUTO, cân lỗi/phễu thiếu) → huỷ rang ở STP_LOOP_1.

---

## 7. Rủi ro kẹt (deadlock) — soi bằng state-trace

Các state chờ điều kiện cảm biến, **chưa có timeout escape rõ ràng**:

- **STP_COOL_DOWN**: chờ BT hạ đủ. Nếu trống quá nóng và không hạ (gas rò, sensor
  lỗi) → có thể kẹt. Không thấy timeout riêng — dựa vào lớp cắt lửa khẩn.
- **STP_GAS**: bếp thường chờ `READ_CH1=LOW` (có lửa). Nếu mồi hoài không lên lửa
  → kẹt `WAITGAS`. Preheat có retry mồi, nhưng nhánh rang này nên có timeout.
- **STP_TP**: chờ BT ngừng giảm. Cảm biến kẹt/nhiễu có thể giữ mãi ở `CHECK TP`.
- **STP_YELLOW / STP_FCS**: chờ BT vượt ngưỡng. Nếu gas yếu/không đủ nhiệt, BT
  không tới ngưỡng → chờ vô hạn (nhưng thợ thấy và can thiệp tay được).

**Đề xuất**: thêm timeout + cảnh báo (STT) cho các state chờ-cảm-biến ở trên, để
HMI báo "kẹt ở bước X quá lâu" thay vì im lặng chờ. (Ghi nhận, chưa sửa firmware.)

---

## Liên quan
- `include/Program.h` — `programScan()`, nguồn của tài liệu này.
- `include/Define.h` — định nghĩa `STP_*`, `STT_PROGRAM_*`.
- `include/MachineStatus.h` — mã `STT_*` HMI đọc để hiển thị (§19 doc HMI).
- `docs/ref/ref-roast-lab-hmi-architecture.md` §6 — HMI phản chiếu state machine này.
