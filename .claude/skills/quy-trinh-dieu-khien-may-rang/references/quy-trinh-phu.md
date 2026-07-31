# Quy trình phụ — `coolStep`, `abStep`, `aLoaderStep` & timer

Đối chiếu code: `include/Program.h` dòng 1878→2374. Ba máy này chạy **song song** với `progStep`, không nằm trong switch chính, nên vẫn hoạt động khi Start đã tắt (cố ý: làm mát và escape phải chạy xong sau khi mẻ kết thúc).

## Mục lục
- [1. coolStep — làm mát → escape → destoner](#1-coolstep)
- [2. abStep — afterburner](#2-abstep)
- [3. aLoaderStep — auto-loader / cân](#3-aloaderstep)
- [4. Bảng timer tự đóng](#4-bang-timer-tu-dong)
- [5. Chống xung đột giữa các máy](#5-chong-xung-dot)
- [Lịch sử sửa quy trình](#lich-su-sua-quy-trinh)

---

## 1. `coolStep`

Chuỗi làm mát sau khi xả. Kích từ 2 nơi: pre-cool (`BT ≥ DROP_PRO − preCool`) hoặc lúc bấm DROP. Cả hai đều có điều kiện `coolTimer_R > 0 && coolStep == 0` — `coolTimer_R == 0` nghĩa là chủ máy tắt hẳn chức năng làm mát tự động.

### COOL_STEP_COOLING — bật bồn nguội · `"ONCO"`
- `STT_ROAST_COOLING` + `STT_ACT_COOLING_ON`, ghi `COOLING_BTN_W = 1`.
- Mixer: bản có `SOURCE_AI_VR_FROM_HMI` (tách dây) phải ghi `MIXER_BTN_W = 1` riêng; bản đấu dây cũ mixer chung mạch với cooling nên không cần ghi.
- `coolTimer = 0`, `coolTimerEn = 1` → `COOL_STEP_ESCAPE_ON`.

### COOL_STEP_ESCAPE_ON — đếm thời gian nguội · `"WAESCAPE"` / `"WAESDES"`
- `coolTimer ≥ coolTimer_R − 5` → `buzzerTimerEn = 1` (báo trước 5 giây cho thợ tránh xa cửa escape).
- `destonerSet_R > 0` && `coolTimer ≥ coolTimer_R − destonerPre_R` → bật `destonerTimerEn = 1` + `DESTONER_BTN_W = 1` (`STT_DESTONER_ON`). Bật **trước** escape để quạt tách đá kịp đạt tốc độ khi hạt bắt đầu chảy.
- `coolTimer ≥ coolTimer_R` → `STT_ROAST_ESCAPE`, `ESCAPE_BTN_W = 1`, `escapeTimerEn = 1`, `STT_EVENT_ESCAPE_OPENED` → `COOL_STEP_ESCAPE_OFF`.

### COOL_STEP_ESCAPE_OFF — chờ xả hết rồi đóng · `"WAESCOFF"` / `"OFFESC"`
- `escapeTimer ≥ escapeDuration_R − 5` → buzzer báo trước.
- Nhánh **huỷ tay**: `escapeTimerEn ≥ 1 && ESCAPE_BTN_R == 0 && escapeTimer ≥ 1` → reset `escapeTimer/En` và `coolTimer/En`, buzzer, `coolStep = 0`.
- Nhánh **xong**: `escapeTimer ≥ escapeDuration_R` **hoặc** `ESCAPE_BTN_R == 0` → đóng escape, tắt cooling (+ mixer riêng nếu tách dây), `STT_EVENT_ESCAPE_CLOSED` + `STT_ACT_COOLING_OFF`, reset cả 2 timer, buzzer, `coolStep = 0`.

### Huỷ toàn chuỗi
`coolStep ≥ 1 && COOLING_BTN_R == 0 && coolTimer ≥ 1` (dòng 2151) → tắt mixer riêng nếu có, reset `coolStep/coolTimer/coolTimerEn`, nhãn `"NONE"`. Đây là đường thoát khi thợ tắt cooling bằng tay giữa chuỗi.

### Log
Khi `coolStep ≥ 1` và `enDebug`, in `Cool count: <coolTimer> / set: <coolTimer_R>` mỗi khi số giây đổi — hữu ích để soi chuỗi làm mát mà không cần nhìn HMI.

---

## 2. `abStep`

Afterburner (đốt khói). Kích từ [khối tình huống trong lúc rang](quy-trinh-chinh.md#6-khoi-huy): `afterburnerSet_R_CV > 0` && `timeRoast > 60` && `STP_TP ≤ progStep < STP_LOOP_1` && `BT ≥ afterburnerSet_R_CV`.

### STP_ON_AB · `"ONAB"`
`STT_ACT_AB_ON`, `AB_BTN_W = 1` → `STP_WAIT_AB`.

### STP_WAIT_AB · `"WDO"` / `"CACAB"`
- **Huỷ trước khi tự tắt**: `AB_BTN_R == 0 && dropTimerEn == 1` → reset `abTimer/En`, `abStep = 0`.
- **Khi DROP bật** (`DROP_BTN_R == 1 && abTimerEn == 0`):
  - `afterburnerNext_R > 0 && AB_BTN_R == 1` → `abTimerEn = 1` (chạy thêm `afterburnerNext_R` giây rồi tắt — vẫn còn khói tồn trong ống).
  - ngược lại → `AB_BTN_W = 0` ngay, `abStep = 0`.

### Tự đóng
`abTimerEn == 1 && abTimer ≥ afterburnerNext_R` → `STT_ACT_AB_OFF`, `AB_BTN_W = 0`, `abStep = 0`.
Nhánh huỷ: `abTimerEn == 1 && AB_BTN_R == 0 && abTimer ≥ 1` → reset hết.

---

## 3. `aLoaderStep`

Hút hạt lên phễu cho **mẻ sau**, kích tại `STP_FCS` (xem [quy-trinh-chinh.md](quy-trinh-chinh.md#3-nhom-rang)).

```
STP_NONE_LOADER(0) → STP_ON_LOADER(1) → STP_WAIT_LOADER(2) → STP_OK_LOADER(4)
                                                            ↘ STP_FAIL_LOADER(3) → huỷ mẻ ở LOOP_1
```

- **STP_ON_LOADER** · `"ONLOA"` — `FEEDER_BTN_W = 1` → `STP_WAIT_LOADER`.
- **STP_WAIT_LOADER** · `"WDO"` — chờ cân tụt đủ lượng.
- **STP_OK_LOADER** · `"OKLOA"` / **STP_FAIL_LOADER** · `"FLOA"` — trạng thái cuối; LOOP_1 đọc `FAIL` để huỷ cả mẻ.

### Điều kiện cắt feeder (dòng 1970)
`FEEDER_BTN_R == 1 && netWTG_R > 0 && scaleDataValid` và:
```
netW100 ≤ difNetW×10 + dif100 + suctionOffset100
```
- `difNetW` = cân đích cuối (`netW − netWTG_R`, tính khi feeder off).
- `dif100` = lượng cà **còn rơi** trong lúc xy-lanh đóng, lấy từ **bảng tự học** `/loadcfg.csv` (`loaderQuantize` → `loaderCfgFind`, không có ô thì `loaderCfgNearest`, bảng rỗng thì mồi bằng công thức `|rorKG|×feederTkg×wStart/60e6`). Kẹp trần `FEEDER_DIF_MAX×10`.
- `suctionOffset100` = sai số cân do lực hút thổi (đo sau `FEEDER_WSTART_DELAY_MS`, kẹp `[0, FEEDER_OFFSET_MAX100]`).
- So sánh ở thang **×100** để không giật bậc 0,1 kg.

Rẽ nhánh khi đạt ngưỡng:
- `netW100 > vacuumTraction_R×10` (còn đủ lực kéo) → tắt feeder, `STT_LOADER_OK` → `STP_OK_LOADER`, và nếu `adaptArmed` thì vào pha tự học `loaderAdaptPhase = 1`.
- ngược lại → `cleanFeederTiEn = 1` (dọn sạch phễu, **không** ghi log học).

### Bắt đầu mẻ hút bằng LATCH
`FEEDER_BTN_R == 0` → `feederWasOff = true`; thấy `FEEDER_BTN_R == 1 && feederWasOff && loaderAdaptPhase == 0` → chốt `adaptStartMs/adaptStartW100`, `adaptArmed = true`. Dùng latch thay vì bắt sườn 0→1 vì vòng quét Modbus có thể **lỡ cạnh** → sinh mẻ rác. Đừng đổi về dạng bắt sườn.

### Mất dữ liệu cân
`updateNetWTi ≥ 5` && không có byte Bluetooth → `scaleDataValid = false`; nếu đang `STP_WAIT_LOADER` thì tắt feeder + `STT_SCALE_DATA_INVALID` + `STP_FAIL_LOADER`.

---

## 4. Bảng timer tự đóng

Tất cả đếm bằng giây trong `timerPoll_1000ms()` (ISR — chỉ tăng biến, không Modbus). Mỗi timer có cặp **tự đóng** + **huỷ khi thợ nhả nút**; thiếu nhánh huỷ là kẹt van.

| Timer | Cờ / bộ đếm | Đóng khi | Việc lúc đóng | Nhánh huỷ |
|---|---|---|---|---|
| Cửa nạp | `chargeTimerEn` / `chargeTimer` | `≥ chargeDuration_R` | `CHARGE_BTN_W = 0`, reset ô lệnh PC (`Charge_btn_PC`, `Hreg`), `STT_EVENT_CHARGE_CLOSED`, buzzer | `CHARGE_BTN_R == 0 && chargeTimer ≥ 1` |
| Cửa xả | `dropTimerEn` / `dropTimer` | `≥ dropDuration_R` | `DROP_BTN_W = 0`, reset `Drop_btn_PC`, `STT_EVENT_DROP_CLOSED`, buzzer, nhãn `"NONE"`; nếu manual-save thì `loadAllProfileDates()` | `DROP_BTN_R == 0 && dropTimer ≥ 1` |
| Afterburner | `abTimerEn` / `abTimer` | `≥ afterburnerNext_R` | `AB_BTN_W = 0`, `abStep = 0` | `AB_BTN_R == 0 && abTimer ≥ 1` |
| Destoner | `destonerTimerEn` / `destonerTimer` | `≥ destonerSet_R` | `DESTONER_BTN_W = 0`; nếu `autoFill_R == 1` → bật `AUTO_FS_BTN_W = 1` | `DESTONER_BTN_R == 0 && destonerTimer ≥ 1` |
| Escape | `escapeTimerEn` / `escapeTimer` | `≥ escapeDuration_R` | `ESCAPE_BTN_W = 0`, reset `Escape_btn_PC`, `STT_EVENT_ESCAPE_CLOSED`, buzzer | `ESCAPE_BTN_R == 0 && escapeTimer ≥ 1` |
| Feeder | `feederTimerEn` / `feederTimer` | `≥ feederSet_R` (>0) | `FEEDER_BTN_W = 0`; nếu đang `STP_WAIT_LOADER` → `STT_LOADER_FAIL` + `STP_FAIL_LOADER` | `FEEDER_BTN_R == 0 && feederTimer ≥ 1` |
| Auto-fill silo | `fillerTiEn` / `fillerTi` | `≥ autoFill_Time_R` | `AUTO_FS_BTN_W = 0` | `AUTO_FS_BTN_R == 0 && fillerTi ≥ 1` |
| Dọn sạch feeder | `cleanFeederTiEn` / `cleanFeederTi` | `≥ 10` | `FEEDER_BTN_W = 0`; nếu `STP_WAIT_LOADER` → `STT_LOADER_OK` + `STP_OK_LOADER` | — (tự reset khi đóng) |
| Chờ cửa xả đóng | `waitDropcloseTiEn` / `waitDropcloseTi` | `> 20` | `progStep = STP_DATA` → mẻ mới | thợ tắt Start |

**Lưu ý escape**: khối huỷ + tự đóng ở dòng 2181–2200 nằm **trong** `if(PC_CONTROL_BTN_R == 1)`, còn `COOL_STEP_ESCAPE_OFF` xử lý escape khi không có PC. Sửa một trong hai phải soát cái còn lại, kẻo escape đóng 2 lần hoặc không đóng.

---

## 5. Chống xung đột

- **Ai được đặt `gasPercent`?** Chỉ nhánh AUTO: `COOL_DOWN` (50 %), `GAS` (`preGas_R`), và bộ chỉnh gas AUTO trong mẻ. Ngoài AUTO, `naviSourceGAS` rơi về `SOURCE_AI_PC`/`SOURCE_AI_VR` ở cuối `programScan()` nên giá trị `gasPercent` cũ không có tác dụng. Muốn thêm bước tự chỉnh gas thì phải đặt `naviSourceGAS = SOURCE_AI_AUTO` **trong bước đó**, mỗi vòng, vì khối cuối hàm sẽ giành lại quyền nếu thấy khác `AUTO`.
- **Trần gas** `maxGasSet_R` do hồ sơ áp ở `STP_DATA`, chỉ khi rang AUTO. `sdMaxGasLoaded == -1` = hồ sơ không khai báo → giữ trần cũ.
- **`coolStep` vs `progStep`**: cooling có thể còn chạy khi `progStep` đã về 0 (mẻ kết thúc). Đúng ý muốn — đừng thêm điều kiện `progStep ≥ 1` vào `coolStep`, sẽ cắt ngang chuỗi làm mát.
- **`abStep` chỉ chạy trong mẻ** (`progStep < STP_LOOP_1`) nhưng tắt trễ theo `dropTimerEn`, nên khối tự đóng AB nằm ngoài switch.
- **Vacuum PID**: trạng thái trước mẻ được lưu ở `STP_DATA` (`roastVacFlagSaved`) và khôi phục ở **cả hai** đường ra (DROP và huỷ Start). Thêm đường ra mới thì phải khôi phục ở đó nữa.

---

## Lịch sử sửa quy trình

| Ngày | Sửa gì | Lý do |
|------|--------|-------|
| 2026-07-30 | Lập spec đầu tiên từ code hiện có | Tách quy trình ra khỏi code |
