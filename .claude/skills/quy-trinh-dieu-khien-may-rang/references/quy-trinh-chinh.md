# Quy trình chính — máy trạng thái `progStep`

Đối chiếu code: `include/Program.h`, `programScan()` dòng 1388→2374. Cập nhật lần cuối: 2026-07-30.

## Mục lục
- [0. Bản đồ bước](#0-ban-do-buoc)
- [1. Khối chạy trước switch (luôn chạy)](#1-khoi-chay-truoc-switch-luon-chay)
- [2. Nhóm CHUẨN BỊ: DATA → COOL_DOWN → GAS → CHECK](#2-nhom-chuan-bi)
- [3. Nhóm RANG: CHARGE → TP → YELLOW → FCS → DEV](#3-nhom-rang)
- [4. Khối XẢ (DROP)](#4-khoi-xa-drop)
- [5. Nhóm LẶP MẺ: LOOP_1 → LOOP_2](#5-nhom-lap-me)
- [6. Khối huỷ & tình huống trong lúc rang](#6-khoi-huy)
- [Lịch sử sửa quy trình](#lich-su-sua-quy-trinh)

---

## 0. Bản đồ bước

Hằng số ở `include/Define.h` dòng 233–246.

```
STP_DATA(0) → STP_COOL_DOWN(1) → STP_GAS(3) → STP_CHECK(4) → STP_CHARGE(5)
   → STP_TP(6) → STP_YELLOW(7) → STP_FCS(8) → STP_DEV(9)
   → [khối DROP] → STP_LOOP_1(13) → STP_LOOP_2(14) → về STP_DATA(0)
```

Hai điều dễ hiểu sai:
- **Số 2 trống.** Không state nào mang giá trị 2 (bước cũ đã gỡ). Giữ nguyên các số hiện có, đừng dồn lại — HMI và app đọc `progStep` theo số này.
- **`STP_DROP(10)`, `STP_COOLING(11)`, `STP_ESCAPE(12)` được khai báo nhưng `progStep` KHÔNG bao giờ nhận.** Việc xả do [khối DROP](#4-khoi-xa-drop) lo, làm mát/escape do `coolStep` lo. Nếu muốn quy trình rõ hơn thì có thể đưa xả thành state thật, nhưng phải soát mọi so sánh `progStep<STP_LOOP_1` và `progStep>=STP_YELLOW` vì chúng đang dựa vào thứ tự số.

Toàn bộ switch chỉ chạy khi `START_BTN_R == 1`.

---

## 1. Khối chạy trước switch (luôn chạy)

Chạy mỗi vòng `loop()`, **kể cả khi không rang** — nên vẫn đúng khi máy trạng thái kẹt.

1. **Bật cưỡng chế trống + quạt** — `forceDrumFanOnFlag` do ISR set. Nếu `BT > 800` hoặc `ET > 800` (80 °C) mà `DRUM_FAN_BTN_R == 0` → ghi `DRUM_FAN_BTN_W = 1`, đồng bộ relay ngoài và `mbs.Hreg`. Lý do: lồng nóng mà trống dừng thì hạt/thành lồng cháy cục bộ.
2. **Cắt gas an toàn** — `fireCutFlag` do ISR set → ghi `START_GAS_BTN_W = 0`, `gasPercent = 0`, rồi phân loại nguyên nhân:
   | Điều kiện | Trạng thái báo |
   |---|---|
   | `BT > 2500` (250 °C) | `STT_ERR_FIRE_ALARM` (401) |
   | `ET > 3000` && `BT < 1500` | `STT_TEMP_DIVERGENCE` (267) — nghi tuột đầu dò BT |
   | còn lại (`ET > 350 °C`) | `STT_TEMP_ET_HIGH` (264) |
3. **`preheat()`** — chỉ khi `START_BTN_R == 0`, tức sấy lồng và rang loại trừ nhau.
4. **`calibProgram()`** nếu `calibGasProgramEn` (nạp bảng gas AUTO từ hồ sơ).
5. **`sdRead()`** — đọc hồ sơ/cấu hình trên thẻ.

Cuối hàm (sau mọi switch): `sdLogWrite()`, `analogCalProcessSD()`, và điều hướng `naviSourceGAS/AIR/DRUM` — bước nào **không** đặt `SOURCE_AI_AUTO` thì tự rơi về `SOURCE_AI_PC` (khi `PC_CONTROL_BTN_R==1`) hoặc `SOURCE_AI_VR`.

---

## 2. Nhóm CHUẨN BỊ

### STP_DATA (0) — Reset dữ liệu mẻ · `"RESET DATA"`
- Vào khi : bấm Start, hoặc quay về từ CHECK/LOOP_1/LOOP_2.
- Làm :
  - `setMachineStatus(STT_ROAST_INIT)`; lưu `roastVacFlagSaved = vacuumSetFlag_R` (khôi phục lúc DROP/huỷ).
  - Rang AUTO có hồ sơ: `maxGasSet_R = sdMaxGasLoaded` (0–100) và ghi lên HMI — áp **trần gas** của hồ sơ.
  - Rang manual-save: `sdLogStartEn = 1`, `timeAbsolute = 0`, `timeAbsoluteEn = 1`, `sdChargeHappened = false`.
  - `updateDateTimeEn = 1` (lấy giờ RTC từ HMI để ghi SD).
  - Xoá sạch mốc: `BT_CHARGE/TP/YELLOW/FCS/DROP_SAVE`, mọi `TIME_*_SAVE`, `PER_DEV_SAVE`, `timeTPAbsolute/timeDRYeAbsolute/timeFCsAbsolute/timeDROPAbsolute`, `timeRoast = 0`.
  - `rorCtrl_reset()`, `trendPreStarted = false`.
  - Clear đồ thị HMI (`CLEAR_HIS_CONTROL_W`), **khoá nút HMI** (`LOCK_BUTTON_W = 1`).
- Thoát khi : ngay lập tức → `STP_COOL_DOWN` (`STT_ROAST_COOLDOWN`).
- Kẹt được? : Không.

### STP_COOL_DOWN (1) — Hạ nhiệt về ngưỡng nạp · `"BT COOLS DOWN"`
- Vào khi : xong DATA.
- Làm :
  - `chargeTemp_R_CV == 0` → **bỏ hẳn auto-charge**, nhảy `STP_CHARGE` chờ thợ bấm tay.
  - Có cài nhiệt nạp: `BT > chargeTemp − turnGasPoint` → giữ `START_GAS_BTN_W = 0` (tắt gas cho nguội).
  - Đủ nguội (`BT ≤ chargeTemp − turnGasPoint`): nếu `READ_CH1 == HIGH` (chưa có lửa) → `naviSourceGAS = SOURCE_AI_AUTO`, `gasPercent = 50`, bật `START_GAS_BTN_W = 1`.
- Thoát khi : đủ nguội → `STP_GAS` (`STT_ROAST_WAITGAS`); hoặc `chargeTemp_R_CV == 0` → `STP_CHARGE`.
- **Đủ nguội** = `BT ≤ chargeTemp − turnGasPoint`. Đây là **khoảng lùi**, không phải nhiệt tuyệt đối: nạp 200 + lùi 20 → đủ nguội ở 180. Dải thợ được cài (chốt 30/07): nạp 150–230 (ca cao 130–230), lùi 10–30 → ngưỡng luôn trong 120–220. Mẻ liên tiếp lồng còn ~180–200 nên **qua ngay trong một vòng quét**; bước này chỉ dừng thật khi lồng nóng hơn nhiệt nạp quá mức lùi (sấy quá tay).
- Kẹt được? : Chỉ khi cài sai — `turnGasPoint ≥ chargeTemp` làm ngưỡng thành số âm, BT không bao giờ chạm, máy đứng im gas tắt mà không báo gì. Kẹp dải lúc nhận `$M` là hết (xem [quyet-dinh-cho-code.md](quyet-dinh-cho-code.md) mục 0 và 2).
- ⚠ **Ghi Modbus dội bus**: nhánh "chưa đủ nguội" ghi `START_GAS_BTN_W = 0` **mỗi vòng quét** (dòng 1555) — chờ nguội mấy phút là mấy nghìn khung thừa. Đã chốt sửa thành ghi một lần, chưa code.
- 🔧 **Chờ code**: `chargeTemp == 0` hiện nhảy thẳng sang `STP_CHARGE` (bỏ mồi lửa + gia nhiệt). Theo quyết định 30/07, charge tay vẫn đi đủ `1 → 3 → 4`, đích 230 °C — xem [quyet-dinh-cho-code.md](quyet-dinh-cho-code.md) mục 3.

### STP_GAS (3) — Chờ lửa bắt · `"WAITGAS"`
- Vào khi : COOL_DOWN đã hạ đủ nhiệt và ra lệnh bật gas.
- Làm :
  - Bếp thường (`burnerPremix_R == 0`): chờ `READ_CH1 == LOW` (cảm biến xác nhận có lửa) → `naviSourceGAS = SOURCE_AI_AUTO`, `gasPercent = preGas_R`.
  - Bếp premix (`burnerPremix_R == 1`): không chờ tín hiệu, đặt `gasPercent = preGas_R` luôn.
- Thoát khi : có lửa (hoặc premix) → `STP_CHECK` (`STT_ROAST_CHECK`).
- Kẹt được? : **ĐÃ VÁ 2026-07-30 (R1).** Trần `PH_IGNITE_TMO` (60 s) đếm bằng `gasWaitTi`: hết giờ → cắt gas, `gasPercent = 0`, trả quyền gas về VR, chuông, `STT_ERR_IGNITION_FAIL` + `STT_ERR_GAS_WAIT_TMO`, nhãn `GASFAIL`, **tắt `START_BTN_W`** + mở khoá HMI rồi về `STP_DATA`. Phải tắt Start, không thì về DATA là chạy lại vòng COOL_DOWN→GAS = mồi lại vô hạn.
- Sau khi có lửa, gas về `preGas` và **quyền gas thuộc máy tới lúc nạp**: `naviSourceGAS = SOURCE_AI_AUTO` được **latch**, khối điều hướng cuối `programScan()` (dòng 2327) chỉ đổi hướng khi source ≠ AUTO → biến trở của thợ **và** lệnh gas từ app đều không chen vào được. Bảng gas AUTO theo hồ sơ chỉ chạy sau khi nạp (`timeRoastEn`) nên cũng không đè.
- 🔧 **Chờ code (chốt 30/07)**: bếp NP **mồi 2 lần** nhịp 10 s (50 % → xả khí 10 s → 60 %), bếp premix **chờ lửa 65 s** rồi báo `BURNER LOCK`. Chi tiết + luật gió xả khí: [quyet-dinh-cho-code.md](quyet-dinh-cho-code.md) mục 5.

### STP_CHECK (4) — Gia nhiệt tới nhiệt nạp · `"BT HEATUP"`
- Vào khi : đã có lửa.
- Làm : theo dõi BT tăng. Gas giữ nguyên `preGas` — **bước này không đổi gas**, và quyền gas đang latch ở AUTO nên thợ không tăng được (xem STP_GAS).
- Thoát khi :
  - `chargeTemp − chTolerange ≤ BT ≤ chargeTemp + chTolerange` → **máy tự mở cửa nạp** `CHARGE_BTN_W = 1` + `buzzerTimerEn = 1` → `STP_CHARGE`.
  - `BT > chargeTemp + chTolerange×5` (vọt quá xa, không kịp bắt) → tắt gas, **về `STP_DATA`** làm lại từ đầu.
- Kẹt được? : **CÓ, hai đường chưa bịt** — cả hai nhánh ra đều đòi BT phải đi tiếp:
  1. **Không có trần thời gian.** Bếp yếu / gió quá lớn / lồng hở → BT lên tới một mức rồi **cân bằng nhiệt và đứng đó**, không lên cũng không vọt → chờ vô thời hạn, gas vẫn đốt, HMI vẫn báo đang gia nhiệt.
  2. **Cửa sổ bắt nhiệt nạp là cửa sổ HAI ĐẦU**, rộng đúng `2 × chTolerange` (6 °C với dung sai 3). Lồng rỗng gas cao, BT leo 2–3 °C/giây thì **hai lần đọc liên tiếp nhảy qua cửa sổ** → không bắt được, chỉ còn nhánh vọt cứu. Đúng cái bẫy đã làm hỏng R2 ở bước TP. Sửa rẻ: đổi thành điều kiện **một chiều** `BT ≥ chargeTemp − chTolerange`.
- 🔧 **Chờ code (chốt 30/07)**: nút Nạp hạt trên app **nhấp nháy** suốt quãng chờ; **cho bấm charge sớm** khi BT trong dải theo loại hạt (ghi `BT_CHARGE` + đồng hồ mẻ theo đúng lúc bấm — hiện bấm sớm ở bước này là **mất dữ liệu mẻ**, máy vẫn đứng ở bước 4); ngưỡng vọt đổi thành **`+10 °C` cố định** và **về `STP_COOL_DOWN`** thay vì `STP_DATA`; **vọt 2 lần trong một mẻ → khoá** bằng cờ lỗi. Charge tay đi đủ `1→3→4` với đích 230 °C. Xem [quyet-dinh-cho-code.md](quyet-dinh-cho-code.md) mục 3–4.
- 🔧 **Đang bàn, chưa chốt**: chờ 60 s chưa nạp thì **cho +10 % gas** (chủ máy chốt 30/07 là *có làm*, còn bốn chi tiết chưa quyết — xem cuối [quyet-dinh-cho-code.md](quyet-dinh-cho-code.md)).

### Bật đồ thị sớm (chạy sau switch, dòng 1739)
Khi `chargeTemp_R_CV > 0` và `STP_GAS ≤ progStep < STP_TP` và chưa `trendPreStarted` và `BT ≥ chargeTemp − TREND_PRECHARGE_BAND` (10 °C) → bật `SAMPLE_COIL_W = 1`. Mục đích: ghi được cả đoạn tiến tới charge, không mất phần đầu đường cong. Mỗi mẻ một lần; lúc bấm charge vẫn bật lại để phòng hờ.

---

## 3. Nhóm RANG

**Mốc thời gian gốc của mẻ là lúc CHARGE** (`timeRoastEn = 1`), không phải lúc bấm Start.

### STP_CHARGE (5) — Nạp nhân · `"WAIT CHARGE"`
- Vào khi : CHECK bắt được vùng nhiệt nạp, hoặc COOL_DOWN bỏ qua auto-charge.
- Làm (mỗi vòng, trước khi thấy nút):
  - `progStatus == STT_PROGRAM_SAVE` → `naviSourceGAS/DRUM/AIR = SOURCE_AI_VR` (thợ lái bằng biến trở).
  - `progStatus == STT_PROGRAM_AUTO` → cả ba `= SOURCE_AI_AUTO` (máy lái).
- Thoát khi `CHARGE_BTN_R == 1` :
  - `BT_CHARGE_SAVE = Temperature_BT`; `BT_TP_Pre = Temperature_BT` (hạt giống để dò TP).
  - `CHARGE_BTN_W = 1`, `buzzerTimerEn = 1`, `chargeTimerEn = 1` (tự đóng cửa sau `chargeDuration_R` giây).
  - `SAMPLE_COIL_W = 1` (ghi đường cong), `timeRoastEn = 1` (**đồng hồ mẻ chạy**).
  - `sdChargeHappened = true`, lưu `sdChargeHH/MM` từ RTC, `sdCsvPendingEvent = "CHARGE"`.
  - Trạng thái: `STT_EVENT_CHARGE_OPENED`, `STT_EVENT_ROAST_START` → `STP_TP` (`STT_ROAST_CATCH_TP`).
- Kẹt được? : Chờ nút vô thời hạn — đúng ý muốn (thợ chủ động nạp).

### STP_TP (6) — Bắt điểm quay đầu · `"WAIT TP"` / `"CHECK TP"`
- Vào khi : đã nạp nhân.
- Làm : chỉ xét khi **`timeRoast > ulimitTPTime` VÀ `BT < ulimitTPTemp`** (hai chặn để không bắt TP giả lúc mới đổ hạt). Trong vùng xét:
  - BT còn giảm (`BT ≤ BT_TP_Pre`) → cập nhật `BT_TP_Pre` = đáy mới, nhãn `"CHECK TP"`.
  - BT bật tăng (`BT > BT_TP_Pre`) → chốt `BT_TP_SAVE = BT_TP_Pre`, `TIME_TP_SAVE = timeRoast` (+ phút/giây), ghi event `"TP"`, `STT_EVENT_TP_REACHED`.
- Thoát khi : bắt được TP → `STP_YELLOW` (`STT_ROAST_YELLOW`).
- Kẹt được? : **ĐÃ VÁ 2026-07-30 (R2), hai lớp.** (1) *Cứu TP*: hết `ulimitTPTime` mà BT đã trượt qua `ulimitTPTemp` → chốt luôn `BT_TP_Pre` đang giữ làm TP, ghi kèm dấu "TP suy đoán", sang `STP_YELLOW`. (2) *Chốt độc lập*: khối DROP hạ cổng từ `STP_YELLOW` xuống **`STP_CHARGE`** — auto-drop đúng bất kể máy có bắt được mốc hay không. Trước khi vá: trượt cửa sổ là đứng ở TP suốt mẻ **và máy không tự xả** → cháy mẻ.

### STP_YELLOW (7) — Kết thúc pha sấy (DE / Dry End) · `"WAIT YELLOW"`
- Thoát khi : `BT ≥ yellowPhase_R_CV` → lưu `BT_YELLOW_SAVE`, `TIME_YELLOW_SAVE` (+ phút/giây), event `"DRY End"`, `STT_EVENT_YELLOW_REACHED` → `STP_FCS` (`STT_ROAST_FCS`).
- Kẹt được? : Nếu BT không lên tới mốc (gas quá thấp) thì chờ mãi. Từ bước này auto-drop **đã** hoạt động, nên thợ vẫn còn đường xả.

### STP_FCS (8) — Chờ nứt lần 1 (First Crack) · `"WAIT FCS"`
- Thoát khi : `BT ≥ fcsPhase_R_CV` → lưu `BT_FCS_SAVE`, `TIME_FCS_SAVE` (+ phút/giây), event `"FCs"`, `STT_EVENT_FCS_REACHED` → `STP_DEV` (`STT_ROAST_DEV`).
- Việc kèm — **kích auto-loader hút hạt cho mẻ sau** (chỉ tại bước này, dòng 1748): điều kiện `progStatus == AUTO` && `autoLoader_R == 1` && `aLoaderStep == 0` && `loop_R > 1`, rồi xét cân:
  | Tình huống | Kết quả |
  |---|---|
  | `!scaleDataValid` | `STT_SCALE_DATA_INVALID` → `aLoaderStep = STP_FAIL_LOADER` |
  | `netW < 0` | `STT_SCALE_NEGATIVE` → `STP_FAIL_LOADER` |
  | `netW ≥ LOADER_MIN_NETW` | `STT_LOADER_RUNNING` → `STP_ON_LOADER` (bắt đầu hút) |
  | còn lại (phễu nguồn thiếu liệu) | `STT_LOADER_FAIL` → `STP_FAIL_LOADER` |
  Chọn FCS làm mốc hút vì lúc này mẻ đang chạy đã qua pha nhạy nhất, còn đủ thời gian hút xong trước khi xả.

### STP_DEV (9) — Pha phát triển · `"DEV"`
- Làm (tính liên tục mỗi vòng):
  - `TIME_DEV_SAVE = timeRoast − TIME_FCS_SAVE` (+ phút/giây).
  - `PER_DEV_SAVE = TIME_DEV_SAVE × 1000 / timeRoast` — **phần nghìn**, ví dụ 185 = 18,5 %.
- Thoát khi : **không có điều kiện thoát trong case này.** Ra khỏi DEV bằng [khối DROP](#4-khoi-xa-drop).
- Kẹt được? : **ĐÃ VÁ 2026-07-30 (R3) — báo, không tự xả.** `PER_DEV_SAVE` vượt `DEV_WARN_PERMIL` → chuông + `setMachineStatus` cảnh báo **một lần trong mẻ** (cờ `devWarned`). Vẫn không có trần thời gian và **máy không tự xả**: tự xả một mẻ chưa tới nhiệt là làm hỏng mẻ, quyết định để cho thợ.

---

## 4. Khối XẢ (DROP)

Nằm **ngoài switch**, chạy khi **`progStep ≥ STP_CHARGE`** (hạ cổng từ `STP_YELLOW` ngày 2026-07-30, lớp 2 của R2). Đặt ngoài switch để bấm xả được ở bất kỳ bước nào từ lúc hạt vào lồng, không phải chờ tới DEV — và để auto-drop không phụ thuộc việc máy có bắt được mốc TP hay không.

### 4a. Tự động (chỉ khi `progStatus == STT_PROGRAM_AUTO`)
- **Auto drop**: `BT ≥ DROP_PRO_R` && `progStep < STP_LOOP_1` → `STT_ROAST_DROP`, ghi `DROP_BTN_W = 1` (máy tự bấm xả).
- **Pre-cool**: `BT ≥ DROP_PRO_R − preCool_R_CV` (khi `preCool_R_CV > 0`) → nếu `coolTimer_R > 0 && coolStep == 0` thì `coolStep = COOL_STEP_COOLING`. Mục đích: bồn nguội đã chạy sẵn trước lúc hạt rơi xuống.

### 4b. Khi `DROP_BTN_R == 1` && `progStep < STP_LOOP_1`
- Rẽ theo chế độ **trước tiên**: `progStatus == STT_PROGRAM_SAVE` → tắt `START_BTN_W`, tắt `warnDeleteProfile`, mở khoá HMI, `sdLogEndEn = 1`, `STT_EVENT_ROAST_END`, `progStep = 0`.
- `autoOff_R == 1` → tắt gas (`START_GAS_BTN_W = 0`).
- Lưu `BT_DROP_SAVE`, `TIME_DROP_SAVE`, event `"DROP"`, `sdLogDataEn = 1` (**flush ngay** để dòng ghi còn kịp có Time2 trước khi dừng đếm giờ).
- **Trả quyền**: `naviSourceGAS/DRUM/AIR = SOURCE_AI_VR`; khôi phục `vacuumSetFlag_R = roastVacFlagSaved` + ghi lên HMI.
- Bật cooling nếu chưa: `coolTimer_R > 0 && coolStep == 0` → `coolStep = COOL_STEP_COOLING`.
- `timeRoastEn = 0`, `SAMPLE_COIL_W = 0`, `timeAbsoluteEn = 0`, `buzzerTimerEn = 1`.
- `dropTimerEn = 1` (tự đóng cửa xả sau `dropDuration_R`), `DROP_BTN_W = 1`, `STT_EVENT_DROP_REACHED` + `STT_EVENT_DROP_OPENED`.
- Rẽ cuối: `progStatus == AUTO` → `progStep = STP_LOOP_1`.

---

## 5. Nhóm LẶP MẺ

### STP_LOOP_1 (13) — Quyết định có rang tiếp
- Vào khi : đã xả trong chế độ AUTO.
- Làm (`STT_ROAST_LOOP1`), xét theo thứ tự:
  1. `autoLoader_R == 1 && aLoaderStep == STP_FAIL_LOADER` → **huỷ**: tắt `START_BTN_W`, tắt `warnDeleteProfile`, mở khoá HMI, `aLoaderStep = STP_NONE_LOADER`, `progStep = STP_DATA`, nhãn `"NONE"`.
  2. `loop_R ≤ 1` → **hết mẻ**: tắt Start, mở khoá HMI, về `STP_DATA`, nhãn `"NONE"`.
  3. Còn mẻ → `aLoaderStep = STP_NONE_LOADER`, `progStep = STP_LOOP_2`, nhãn `"LOOP"`.
  4. Sau đó: `loop_R > 1` → `loop_R--`; `loop_R ≥ 0` → ghi số mẻ còn lại lên HMI.
- Kẹt được? : Không — thoát ngay trong một vòng.

### STP_LOOP_2 (14) — Chờ cửa xả đóng, cho phép huỷ · `"WCANCEL"`
- Làm (`STT_ROAST_LOOP2`): thấy `DROP_BTN_R == 0` → `waitDropcloseTiEn = 1`.
- Thoát khi :
  - `START_BTN_R == 0` (thợ huỷ trong cửa sổ này) → mở khoá HMI, `progStep = STP_DATA` (dừng hẳn, vì Start đã tắt nên switch không chạy nữa).
  - `waitDropcloseTi > 20` (≈20 giây) → `progStep = STP_DATA`, reset timer → **tự khởi động mẻ mới**.
- Kẹt được? : **ĐÃ VÁ 2026-07-30 (R4).** Thêm trần `LOOP2_STUCK_SEC` 60 s đếm bằng `loop2Ti` **từ lúc vào bước, bất kể nút báo gì**: hết 60 s mà cửa xả vẫn mở → báo trạng thái cửa xả kẹt, **tắt Start**, về `STP_DATA` — *không* tự nạp mẻ mới khi cửa còn mở. Trước khi vá: `waitDropcloseTiEn` chỉ bật khi thấy `DROP_BTN_R == 0` nên cửa kẹt mở là không bao giờ đếm.

---

## 6. Khối huỷ & tình huống trong lúc rang

Chạy khi `progStep ≥ 1` (dòng 1839–1874), ngoài switch.

- **Tắt Start giữa mẻ** (`START_BTN_R == 0`) → trả toàn bộ về không: `timeRoastEn = 0`, `timeAbsoluteEn = 0`, `progStep = 0`, `aLoaderStep = STP_NONE_LOADER`, `naviSource*` về `SOURCE_AI_VR`, khôi phục `vacuumSetFlag_R`, `SAMPLE_COIL_W = 0`, mở khoá HMI, nhãn `"NONE"`.
  Lưu ý: khối này **không** tắt gas và **không** bật cooling — chủ ý để thợ tự quyết khi dừng khẩn.
- **Tự bật afterburner**: `afterburnerSet_R_CV > 0` && `timeRoast > 60` && `STP_TP ≤ progStep < STP_LOOP_1` && `BT ≥ afterburnerSet_R_CV` && `abStep == 0` → `abStep = STP_ON_AB`. Chặn `timeRoast > 60` để không bật ngay lúc vừa nạp.

Chi tiết 3 máy phụ và toàn bộ timer: [quy-trinh-phu.md](quy-trinh-phu.md).

---

## Lịch sử sửa quy trình

| Ngày | Sửa gì | Lý do |
|------|--------|-------|
| 2026-07-30 | Lập spec đầu tiên từ code hiện có (`Program.h` 1388→2374) | Tách quy trình ra khỏi code để sửa an toàn |
| 2026-07-30 | **Code R1–R6** rồi build (RAM 81,4 %) và **nạp STM32**: trần chờ lửa 60 s, cứu TP + hạ cổng DROP xuống `STP_CHARGE`, cảnh báo DEV, trần LOOP_2 60 s, huỷ Start tắt gas theo `autoOff_R`, gộp escape. **Chưa chạy nghiệm thu trên mẻ thật.** | Sáu chỗ kẹt rà ra từ spec, chủ máy chốt "sửa hết rồi build" |
| 2026-07-30 | Đồng bộ spec theo code đã vá (bước 1, 3, 4, 6, 9, 14, khối DROP) | Spec đang tả bản trước khi vá — code là sự thật |
| 2026-07-30 | Thêm [quyet-dinh-cho-code.md](quyet-dinh-cho-code.md): loại hạt `$M17`, dải nhiệt nạp theo loại hạt, kẹp về biên gần nhất, charge tay có nút riêng đi đủ `1→3→4`, chuỗi mồi 2 lần bếp NP, premix `BURNER LOCK`, cờ lỗi + Xoá lỗi `$M18`, cho charge sớm | Phiên thảo luận với chủ máy — **ý định, chưa code dòng nào** |
