# Bảng thanh ghi $M HMI — tham số cấu hình rang (iMemHMI[])

Nguồn: `include/Define.h`, khối `//Define $M HMI` (dòng ~627–798).
Mỗi tham số có 3 dạng:
- `xxx_W` = **chỉ số ghi** (index trong mảng, dùng khi HMI/app ghi xuống, ví dụ `$M1`).
- `xxx_R` = **giá trị đọc** ↔ `iMemHMI[xxx_W]` (firmware đọc ra để dùng).
- `xxx_R_CP` = **bản chụp** (`iMemHMI_CP[...]`) để dò xem giá trị có đổi không (change-detect).

Nhiều tham số khi so sánh nhiệt được firmware nhân ×10 (`_CV`) vì BT/ET lưu dạng phần-mười độ (2150 = 215.0°C). Cột "Đơn vị" ghi giá trị người dùng nhập trên HMI.

> ⚠️ Cảnh báo comment cũ trong Define.h: `loop_W` chú thích "Sample" nhưng **thực tế là số mẻ rang lặp lại**; `FcsCalib_W` chú thích "$M5" là chép nhầm, đúng ra là $M31; `autoLoader_W` chú thích "auto burner" nhưng code dùng làm **cờ auto-loader (nạp tự động)**. Bảng dưới đã sửa theo code thật.

---

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
| 31 | `FcsCalib` | % (bậc) | **Trần bậc tăng gas AUTO sau FCs**. Xem `[[project_gas_calib_auto]]`, `[[project_ror_gas_cut_crack]]`. |
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
| 30 | `preCool` | °C | **Bật làm nguội sớm** theo nhiệt (so sánh ×10). |
| 45 | `autoFill` | 0/1 | **Bật tự động fill** cà phê từ destoner → silo. |

---

## Ghi chú vận hành
- Timer đếm bằ**giây** vì `timerPoll_1000ms()` là ISR chạy mỗi 1s (không gọi Modbus trong đó — dùng flag). Xem `[[feedback_isr_no_modbus]]`.
- Chuỗi mốc rang: **Charge → TP → DE(yellow) → FCs → DEV → Drop**. `TpCalib/DeCalib/FcsCalib` = trần bậc tăng gas AUTO ứng 3 vùng BT<DE / DE→FCs / >FCs.
- BT/ET lưu ×10 (2150=215.0°C); nhiều `_CV` = giá trị HMI ×10 để so sánh cùng thang.
- Cân: `netW` giữ ×10 cho feeder/HMI, `netW100` ×100 cho auto-loader — xem `[[project_scale_precision]]`.
