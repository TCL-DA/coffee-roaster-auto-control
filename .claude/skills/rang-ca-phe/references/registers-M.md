# Bảng thanh ghi $M HMI — tham số cấu hình rang (iMemHMI[])

Nguồn: `include/Define.h`, khối `//Define $M HMI` (dòng ~627–798).
Mỗi tham số có 3 dạng:
- `xxx_W` = **chỉ số ghi** (index trong mảng, dùng khi HMI/app ghi xuống, ví dụ `$M1`).
- `xxx_R` = **giá trị đọc** ↔ `iMemHMI[xxx_W]` (firmware đọc ra để dùng).
- `xxx_R_CP` = **bản chụp** (`iMemHMI_CP[...]`) để dò xem giá trị có đổi không (change-detect).

Nhiều tham số khi so sánh nhiệt được firmware nhân ×10 (`_CV`) vì BT/ET lưu dạng phần-mười độ (2150 = 215.0°C). Cột "Đơn vị" ghi giá trị người dùng nhập trên HMI.

> ⚠️ Cảnh báo comment cũ trong Define.h: `loop_W` chú thích "Sample" nhưng **thực tế là số mẻ rang lặp lại**; `FcsCalib_W` chú thích "$M5" là chép nhầm, đúng ra là $M31; `autoLoader_W` chú thích "auto burner" nhưng code dùng làm **cờ auto-loader (nạp tự động)**. Bảng dưới đã sửa theo code thật.

---

> ## ⛔ ĐẨY SỐ THANH GHI TỪ v3.10.0 (10/09/2026) — ĐỌC TRƯỚC KHI TRA
>
> Chèn `dropTrim` vào **$M54** nên **7 thanh ghi sau nó lùi một bậc**:
>
> | $M | Trước v3.10.0 | Từ v3.10.0 |
> |----|----|----|
> | 54 | preheatDeadline | **`dropTrim`** (MỚI) |
> | 55 | preheatHoldSettle | preheatDeadline |
> | 56 | preheatTargetBand | preheatHoldSettle |
> | 57 | developmentWarn | preheatTargetBand |
> | 58 | autoDropMin | developmentWarn |
> | 59 | manualEscapeExtra | autoDropMin |
> | 60 | loopDoorStuck | manualEscapeExtra |
> | 61 | — | loopDoorStuck |
>
> Khung đọc `rwMemHMI()` nới **60 → 61** thanh ghi (buffer ModbusMaster 64, còn dư 3 ô).
> `iMemHMI[]` nới lên **[62]**, `PCL_CFG_MAXIDX` = **61**.
>
> **Firmware và màn HMI PHẢI nạp THÀNH CẶP.** Nạp firmware mới với màn cũ thì ô cũ của
> `preheatHoldSettle` (10–30) rơi vào `preheatDeadline` ⇒ hạn sấy lồng 10–30 giây ⇒
> **preheat báo lỗi mọi mẻ**. Firmware có kẹp cứng `dropTrim` về dải 0..10 nên ô 54 sai
> thì chỉ TẮT tính năng, không dịch nhiệt xả — nhưng các ô còn lại KHÔNG có chốt đó.
>
> Xem [[project_khach_balan_dev_stall]], [[project_auto_stall_cuoi_me]].

## 1. Timer xy-lanh & cơ cấu (đơn vị: GIÂY — tick trong `timerPoll_1000ms()`)

| $M | Tên | Đơn vị | Ý nghĩa (theo code) |
|----|-----|--------|----------------------|
| 1 | `chargeDuration` | giây | Thời gian giữ xy-lanh **nạp (charge)** mở. `Program.h:2090` chargeTimer≥ giá trị này → đóng cửa nạp. |
| 2 | `dropDuration` | giây | Thời gian giữ xy-lanh **xả (drop)** mở để cà phê rơi hết ra khay nguội. |
| 3 | `escapeDuration` | giây | Thời gian giữ cửa **thoát/escape** (xả khay nguội / nhả mẻ). Có mốc phụ `-5` giây để làm việc trước khi đóng. |
| 14 | `feederSet` | giây | Thời gian **thổi feeder** (nạp liệu vào silo). `feederSet>0` mới chạy. |
| 19 | `destonerSet` | giây | Thời gian chạy **destoner (tách đá/tạp chất)**. |
| 22 | `coolTimer` | giây | Thời gian chạy **làm nguội + trộn (mixer)** sau khi xả mẻ. |
| 26 | `destonerPre` | giây | **Bù thời điểm bật destoner** trước khi hết cool: `coolTimer ≥ (coolTimer_R - destonerPre_R)`. |
| 27 | `afterburnerNext` | giây | **Trễ bật lại afterburner** (đốt khói) — abTimer≥ giá trị này. |
| 46 | `autoFill_Time` | giây | Thời gian **tự động fill** cà phê từ destoner lên silo rồi tự tắt. |

## 2. Nhiệt & mốc rang

| $M | Tên | Đơn vị | Ý nghĩa |
|----|-----|--------|---------|
| 7 | `afterburnerSet` | °C | Nhiệt vận hành **afterburner** (so sánh ×10). |
| 9 | `turnGasPoint` | °C | **Nhiệt bật gas** — dưới mốc này chưa lên gas chính (so sánh ×10). |
| 20 | `yellowPhase` | °C | Mốc nhiệt **DE / chuyển vàng** (kết thúc pha sấy). Cũng làm ranh giới đổi `maxStep` gas AUTO. |
| 21 | `fcsPhase` | °C | Mốc nhiệt **FCs (nổ lần 1)**. |
| **54** | `dropTrim` | 0.1 °C | **Biên chỉnh nhiệt xả theo sai lệch THỜI GIAN** (v3.10.0+). Thợ cài 0.0–1.0 °C; `0` = tắt. Lê hơn giờ xả mẫu > 15 s → nhiệt xả **− dropTrim**; nhanh hơn > 15 s → **+ dropTrim**. Chỉ chạy khi DEV đã quá 3 phút. Firmware **kẹp cứng 0..10**, ngoài dải coi như 0. Mục đích: giữ **Agtron không vọt lố** khi thời gian rang trôi lệch — màu hạt do TỔNG NHIỆT hấp thụ quyết định, phụ thuộc cả thời gian lẫn nhiệt độ. ⚠ Là **bậc thang, không tỉ lệ**: lệch 16 s và 120 s bù giống nhau. |
| 23 | `chargeTemp` | °C | **Nhiệt nạp mẻ** — lồng phải đạt mức này (±`chTolerange`) mới cho charge. |
| 10 | `chTolerange` | °C | **Dung sai nhiệt nạp** quanh `chargeTemp` (so sánh ×10). Xem memory profile charge −1/+3. |
| 24 | `btSV` | °C | **Set value BT** ghi cho bộ điều khiển nhiệt Delta (so sánh ×10). |
| 25 | `btSVReg` | địa chỉ | **Địa chỉ thanh ghi** trên Delta để ghi `btSV` vào. |
| 6 | `tempRegister` | địa chỉ | **Địa chỉ đọc** BT/ET trên bộ điều khiển Delta (`nodeBT/nodeET.readHoldingRegisters`). |
| 51 | `wuTime` | phút | **Thời gian hâm nóng (warm-up/preheat)**. Code: `wuTime_R * 60` → giây. |
| 52 | `wuTemp` | °C | **Nhiệt đích hâm nóng** (targetBT = `wuTemp_R * 10`). Setpoint preheat. |

## 3. Gas / lửa

| $M | Tên | Đơn vị | Ý nghĩa |
|----|-----|--------|---------|
| 8 | `preGas` | % | **Gas mồi/nạp (BBP)** đặt lúc charge (`gasPercent = preGas_R`). |
| 4 | `TpCalib` | % (bậc) | **Trần bậc tăng gas AUTO trước DE** — giới hạn `numIncGas`. `RoR_Control.h`: `maxStep` khi BT<DE. |
| 5 | `DeCalib` | % (bậc) | **Trần bậc tăng gas AUTO từ DE→FCs**. |
| 31 | `FcsCalib` | % (bậc) | **Trần bậc tăng gas AUTO sau FCs**. ⛔ **PHẢI ≥ 5** — bậc bù nhỏ nhất là 5% (sàn cứng bếp NP), đặt 1–4 là bộ bù CHẾT. Trần chỉ cắn khi lệch ≥ (M31/5)×0.5 °C, nên M31=30 ≈ không có trần trong dải thực tế. Xem `[[project_gas_calib_auto]]`. |
| 28 | `maxGasSet` | % | **Trần gas tuyệt đối** — map DAC: `4095 * maxGasSet/100`. Chặn cả gas AUTO load từ SD. |
| 36 | `burnerValue` | % | **Đặt gas thủ công** (chế độ manual: `gasPercent = constrain(burnerValue,0,100)`). |
| 37 | `autoOff` | 0/1 | **Tự cắt lửa** khi kết thúc (cool). |
| 29 | `burnerPremix` | chọn | **Chọn loại đầu đốt** lúc runtime (premix vs khác). Đổi tham số preheat, xem `[[project_premix_preheat_tune]]`. |

## 4. Động cơ / biến tần

| $M | Tên | Đơn vị | Ý nghĩa |
|----|-----|--------|---------|
| 34 | `drumSpeed` | % | **Tốc độ lồng rang** (biến tần) chế độ manual: `constrain(drumSpeed,0,100)`. |
| 35 | `airSpeed` | % | **Tốc độ quạt gió (airflow)** chế độ manual. |
| 15 | `idDrum` | ID | **Modbus slave ID** biến tần lồng rang. |
| 16 | `regDrum` | địa chỉ | **Thanh ghi ghi tốc độ** trên biến tần lồng. |

## 5. Cân / auto-loader

| $M | Tên | Đơn vị | Ý nghĩa |
|----|-----|--------|---------|
| 32 | `netWTG` | kg (×10) | **Khối lượng đích** để thổi/nạp (Setup kg trên HMI, gửi PC_Link ×10). |
| 33 | `autoLoader` | 0/1 | **Bật auto-loader** (nạp tự động theo cân) — cờ `PCLF_AUTOLOADER`. |
| 38 | `wThresholdHigh` | kg | **Ngưỡng cân cao** — chọn bảng dif tương ứng. |
| 39 | `wThresholdMedium` | kg | **Ngưỡng cân trung**. |
| 40 | `wThresholdLow` | kg | **Ngưỡng cân thấp**. |
| 41 | `difHigh` | kg | **Dung sai nạp** ứng với ngưỡng cao (coast/độ vọt cửa). |
| 42 | `difMedium` | kg | **Dung sai nạp** ngưỡng trung. Xem `[[project_loader_dif_tuning]]`. |
| 43 | `difLow` | kg | **Dung sai nạp** ngưỡng thấp. |

## 6. Vacuum / áp suất (PID airflow)

| $M | Tên | Đơn vị | Ý nghĩa |
|----|-----|--------|---------|
| 44 | `vacuumTraction` | kg (×10) | **Ngưỡng khối lượng còn đủ lực kéo vacuum**: `netW100 > vacuumTraction*10`. |
| 47 | `vacuumSetFlag` | 0/1 | **Bật PID vacuum** (chân không). AUTO do `calibProgram()` set. |
| 48 | `vacuumSetpoint` | Pa | **Setpoint chân không** cho `pidAirflowUpdate()`. |
| 49 | `minPT` | Pa | **Giới hạn dưới cảm biến áp** (VD −500Pa). Quy đổi ACI 0~10000 → thực. |
| 50 | `maxPT` | Pa | **Giới hạn trên cảm biến áp** (VD +500Pa). `Diff_Air = minPT + (raw/10000)*(maxPT−minPT)`. |

## 7. Hệ thống / vận hành

| $M | Tên | Đơn vị | Ý nghĩa |
|----|-----|--------|---------|
| 11 | `loop` | mẻ | **Số mẻ rang lặp lại** (KHÔNG phải "Sample"). Đếm lùi mỗi mẻ; `>1` → rang tiếp (STP_LOOP_2), `≤1` → dừng. |
| 12 | `modbusID` | ID | **Slave ID** của board trên bus Modbus. |
| 13 | `modbusBaud` | mã | **Mã baudrate** Modbus. |
| 30 | `preCool` | 0.1 °C | **Bật làm nguội sớm** theo nhiệt: bật cooling+mixer khi `BT ≥ DROP_PRO − preCool`. Giá trị ở thang **×10** — HMI hiện `0.2` thì thanh ghi là `2` = 0.2 °C. ⛔ Firmware trước 10/09/2026 nhân 10 lần nữa nên hiểu thành 2.0 °C; máy nào chưa nạp bản vá thì ô này đang chạy gấp 10 lần số hiển thị. Từ v3.10.0 mốc so sánh là **nhiệt xả ĐÃ CHỈNH** theo `dropTrim`, không phải `DROP_PRO_R` thô. |
| 45 | `autoFill` | 0/1 | **Bật tự động fill** cà phê từ destoner → silo. |
| 53 | `autoEscape` | 0/1 | **Tự động mở cửa xả**. `1` = chạy đủ làm mát → tách đá → escape. `0` = chỉ thổi mát đủ `coolTimer` rồi tắt bồn nguội, không tách đá, không tự mở cửa — thợ xả tay. ⛔ HMI đời cũ chưa có ô gạt sẽ đọc về 0 ⇒ máy đó phải build với `MACHINE_HAS_AUTO_ESCAPE_SWITCH 0` để firmware bỏ qua thanh ghi và luôn tự xả. |

## 8. Ngưỡng an toàn & preheat (v3.10.0+, $M55–61)

Ô nào để **0** thì firmware dùng hằng mặc định trong `Config.h` (hàm bọc ở `Define.h`, ví dụ `autoDropMinSec()`), trừ `manualEscapeExtra` (0 = không cộng thêm).

| $M | Tên | Đơn vị | Ý nghĩa |
|----|-----|--------|---------|
| 55 | `preheatDeadline` | giây | Hạn để preheat đạt nhiệt; quá hạn → báo lỗi (mặc định `PH_DEADLINE_SEC`). |
| 56 | `preheatHoldSettle` | giây | Chờ ổn định trước khi đánh giá giữ nhiệt (`PH_HOLD_SETTLE_SEC`). |
| 57 | `preheatTargetBand` | 0.1 °C | Dải vào giữ nhiệt preheat (`PH_TARGET_BAND`). |
| 58 | `developmentWarn` | ‰ | Ngưỡng cảnh báo % phát triển (`PER_DEV_SAVE ≥` ngưỡng → báo 1 lần/mẻ). |
| 59 | `autoDropMin` | giây | Thời gian rang tối thiểu trước khi cho auto-drop — chặn xả mẻ ma/chưa nạp. |
| 60 | `manualEscapeExtra` | giây | Cộng thêm vào `escapeDuration` khi đóng escape tay. |
| 61 | `loopDoorStuck` | giây | Hạn chờ cửa drop đóng ở `STP_LOOP_2` trước khi coi là kẹt. |
| 62 | `mcOpt` (machineOptions) | bitmask | **Cấu hình máy** (13/10/2026, `include/MachineOpt.h`). Bit 0 VR gas+gió · 1 VR trống · 2 vacuum · 3 loader · 4 cân · 5 relay ngoài ID 7 · 6–8 cỡ máy (0=6 · 1=12 · 2=15 · 3=30 kg) · 9 đốt khói · 10 tách đá · 11 khuấy relay riêng (cần bit 5) · 15 đã cấu hình. **Bit 15 = 0 ⇒ chặn rang** (relay gas không đóng, nút gas/Start/làm nóng bị trả 0, mã 422). Cấu hình vô lý ⇒ mã 423, giữ cấu hình cũ. Chỉ chốt khi máy đứng yên. PC_Link CHỈ ĐỌC (min>max). ⛔ Firmware và HMI phải nạp thành cặp (khung `rwMemHMI` 62 ô). |

---

## Ghi chú vận hành
- Timer đếm bằ**giây** vì `timerPoll_1000ms()` là ISR chạy mỗi 1s (không gọi Modbus trong đó — dùng flag). Xem `[[feedback_isr_no_modbus]]`.
- Chuỗi mốc rang: **Charge → TP → DE(yellow) → FCs → DEV → Drop**. `TpCalib/DeCalib/FcsCalib` = trần bậc tăng gas AUTO ứng 3 vùng BT<DE / DE→FCs / >FCs.
- BT/ET lưu ×10 (2150=215.0°C); nhiều `_CV` = giá trị HMI ×10 để so sánh cùng thang.
- Cân: `netW` giữ ×10 cho feeder/HMI, `netW100` ×100 cho auto-loader — xem `[[project_scale_precision]]`.

## Quy trình HMI: chọn / lưu / chạy hồ sơ (đọc code firmware 15/10/2026 — CHƯA chạy thử qua panel)
Panel: ô HMI `dAddress[n]` (W400nn) ≡ `$(n−1)` khi đọc/ghi Modbus TCP. Firmware đọc thay đổi ở `Modbus_Master.h` (so `_R` với `_R_CP`).

| Nút / ô trên HMI | Ô nhớ (Define.h) | Panel TCP | Firmware xử lý | Tác dụng phụ | Em làm |
|---|---|---|---|---|---|
| Chọn file hồ sơ 1–30 | `SELECT_FILE_W 16` | `$15` | `Modbus_Master.h:694` ⇒ `sdReadStep = 1`; `sdRead()` chỉ nạp khi màn `SCRNUM` = 6/12/13 (hoặc PC_Link) | nạp hồ sơ ⇒ ghi đè `$M23` chargeTemp = nhiệt CHARGE của file (không có ⇒ 180,0) + mốc TP/DE/FCs/DROP vào ô 103–118 | 15:21 ghi `$15 = 1` ở màn 2 ⇒ đọc lại 0 (HMI trả về). Phải đứng màn chọn file, hoặc qua PC_Link reg 17 (đường COM — cấm) |
| SAVE / AUTO | `MANUAL_AUTO_W 23` (= `SW_M_AUTO_W`) | `$22` | `Modbus_Master.h:737`: 0 ⇒ `STT_PROGRAM_SAVE` (rang lưu), 1 ⇒ `STT_PROGRAM_AUTO` (chạy theo hồ sơ) | AUTO: lúc CHARGE nguồn gas/gió/trống = AUTO, áp MaxGas của hồ sơ | ghi + đọc lại |
| START chương trình | `START_BTN_W 1` | `$0` | `Program.h:1838` máy trạng thái: DATA → COOL DOWN (lồng nóng: chờ nguội tới chargeTemp − turnGasPoint, rồi **gas 50 % AUTO**) → GAS → CHECK (BT vào chargeTemp ± chTolerange ⇒ **tự CHARGE + còi**; vọt > +5 × dung sai ⇒ tắt gas về DATA) | SAVE: `sdLogStartEn` ⇒ XOÁ `N.csv` rồi ghi mới từ lúc START (1 Hz, `Time1 Time2 ET BT Event Air Burner Drum VacFlag VacSP`), header viết lại lúc DROP | chỉ khi anh cho: lấy quyền lửa/gió/trống khỏi tay người |
| Lệnh nhiệt / gas | `START_GAS_BTN_W 2` | `$1` | bật/tắt gas (máy điện: Lệnh VX4) | — | đang dùng |
| Nhiệt charge | `chargeTemp_W 23` (iMemHMI, **×10**) | `$M23` (TCP 2023) | `Modbus_Master.h:267` | bị ghi đè mỗi lần nạp hồ sơ | 15:18 ghi 1700, đọc lại 1700 |
| Xoá 1 / tất cả hồ sơ | `DEL_PROFILE_W 18` / `DEL_ALLPROFILE_W 19` | `$17` / `$18` | xoá `N.csv` + `N.txt` | mất hồ sơ | không bao giờ tự ghi |

Trình tự "rang lưu vào hồ sơ N, charge T" (khi anh cho): `$M23 = T×10` → đứng màn chọn file + `$15 = N` → `$22 = 0` → `$0 = 1` (firmware tự đưa lồng về T rồi CHARGE)
→ đọc lại từng ô + mã `$40` (STT_SD_LOG_STARTED). Chạy theo hồ sơ N: `$15 = N` (chờ nạp xong, `LOADING_SHOW` = 100) → `$22 = 1` → `$0 = 1`.
Rang tay ngoài chương trình (như mẻ 15:2x): firmware KHÔNG ghi SD ⇒ dựng `N.csv` từ `.alog` theo đúng định dạng trên rồi chép vào SD.
