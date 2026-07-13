# KẾ HOẠCH REDESIGN PREHEAT — OTL-06ALS

> Cập nhật: 2026-05-29 (v3)
> **Trạng thái: PROTOTYPE — đang code, chưa flash field test**
> File chính: `include/Preheat.h`

## TRẠNG THÁI DỰ ÁN (v3)

| Mức | Tiêu chí | Hiện tại |
|-----|----------|---------|
| Prototype | Code build OK, chưa flash | **← đang ở đây** |
| Bench test | Flash + test có giám sát, có thể dừng tay | Chưa |
| Field test | Chạy thật với giám sát thợ rang | Chưa |
| Production | Pass 5 lần/case × 6 case + fault injection | Chưa |

---

## QUYẾT ĐỊNH ĐÃ CHỐT

| # | Vấn đề | Quyết định |
|---|--------|-----------|
| 1 | Triết lý điều khiển | **Hybrid** (Rule-based + PI nhẹ trong PRECISION) |
| 2 | Precision mode | **State mới WU_PRECISION** |
| 3 | Start mode | **Phân loại rõ Cold/Hot/Cool** trong WU_IDLE |
| 4 | CSV log | **Per-5s** (60 dòng/preheat) |
| 5 | Pre-ignite | **Có WU_PRE_IGNITE** (thổi sạch buồng đốt) |
| 6 | ADAPT mở rộng | **Thêm lossRate + gasGain** |

---

## I. DỮ LIỆU NỀN TẢNG

### 1.1 Từ 7 lần preheat tay của người vận hành

| Tiêu chí | Kết quả |
|----------|---------|
| Phanh tiếp cận | Xuất sắc — overshoot luôn ≤3°C |
| Gas khởi động | Scale theo gap ≈ `gap/2 + 15` |
| Gas HOLDING | Scale theo target ≈ `target/10 + 4` |
| Hai vòng phản hồi | Gas loop trước, Air loop sau (KHÔNG bao giờ Air trước) |
| Nguyên lý RECOVERY | BT vọt → hạ gas mạnh ngay → dùng air theo rorBT |

### 1.2 Bảng dữ liệu thực nghiệm 7 lần

| # | Target | BT Start | Loại | Overshoot | Gas HOLDING | Air HOLDING | Ổn định |
|---|--------|----------|------|-----------|-------------|-------------|---------|
| 1 | 200°C | 120°C | Cold | +2°C | 25% | 30% | Tốt |
| 2 | 180°C | 120°C | Cold | +1°C | 10% | 40-50% | TB |
| 3 | 160°C | 120°C | Cold | +3°C | 0% | 65% | Kém |
| 4 | 220°C | 160°C | Hot | +2°C | 15-20% | 30% | TB |
| 5 | 210°C | 160°C | Hot | +2°C | 10-25% | 20% | Tốt |
| 6 | 150°C | 215°C | Cool | +15°C | 0% | 100% | Kém |
| 7 | 230°C | 155°C | Hot | ~0°C | 25-35% | 40-50% | Tốt nhất |

### 1.3 Công thức rút ra

**Gas khởi động (gap = target − BT start):**
```
B = gap/2 + 15
```
- gap 40°C → B35
- gap 72°C → B50
- gap 100°C → B80

**Gas HOLDING theo target:**
```
Gas = target/10 + 4
```
- 160°C → ~20%
- 200°C → ~24%
- 230°C → ~27%

**Air/Gas tổng (HOLDING):**
- 190-200°C: Gas+Air ≈ 55-65%
- 220-230°C: Gas+Air ≈ 65-75%

### 1.4 Kết quả test code tự động

| Lần | Target | BT Start | Overshoot | Gas HOLDING | Kết luận |
|-----|--------|----------|-----------|-------------|----------|
| 1 | 200°C | 170°C | +6°C | offset +5°C suốt 4 phút | btError -50 quá rộng |
| 2 | 190°C | 116°C | **+30°C** | B30-B59 quá cao | RECOVERY thiếu |
| 3 | 195°C | 115°C | **+33°C** | B30-B59 quá cao | RECOVERY chưa hoạt động |

---

## II. MỤC TIÊU PREHEAT

### 60% thời gian đầu (3 phút) — RAMP MODE
- Chấp nhận overshoot ≤5°C
- Ưu tiên đạt target nhanh
- Gas có thể cao, air dao động mạnh
- Rule-based với feedforward

### 40% thời gian cuối (2 phút) — PRECISION MODE
- Yêu cầu ±2°C dao động
- Kết thúc đúng target ±1°C
- PI controller nhẹ để khử offset
- Học FF table

---

## III. MÔ HÌNH VẬT LÝ MÁY

**Chuỗi nhiệt:** `Gas → Đầu đốt → Chamber → Trống rang → BT sensor`

Hệ thống 3 bậc nối tiếp, có 3 thermal lag tách biệt:

```
Gas%                      (input, instant)
 │
 ▼  lag ~2-3s (gas → flame stable)
[Đầu đốt: flame intensity]
 │
 ▼  lag ~5-10s (flame → chamber air)
[Chamber temp ≈ ET sensor]
 │
 ▼  lag ~15-20s (chamber → drum metal)
[Drum temp ≈ BT sensor]
```

**Air% ảnh hưởng:**
- Air kéo nhiệt từ chamber qua trống ra ống thải
- Air thấp → nhiệt ở lại chamber lâu → ET cao, BT chậm tăng
- Air cao → nhiệt cuốn qua trống nhanh → ET thấp, BT tăng nhanh hơn
- Air rất cao + gas thấp → cuốn cả nhiệt dư ra → làm nguội

**Hằng số máy:**

| Hằng số | Cách đo | Ý nghĩa |
|---------|--------|---------|
| `tau_chamber` | ET tăng 63% khi tăng gas | ~5-10s |
| `tau_drum` | Lag BT so với ET (peak shift) | ~15-25s |
| `loss_rate` | °C/min BT giảm khi gas=0, air=20 | ~1.2°C/min |
| `gas_gain` | °C/min RoR BT trên 1% gas (steady) | ~3-5 |
| `air_cooling` | °C/min BT giảm trên 10% air tăng | ~0.5-1 |

---

## IV. KIẾN TRÚC STATE MACHINE MỚI

```
┌─────────────┐
│  WU_IDLE    │ ←──────────────────────────────────────┐
└──────┬──────┘                                         │
       │ phân loại COLD/HOT/COOL                       │
       ├─────────────┐                                  │
       │ COOL?       │ YES                              │
       │             ▼                                  │
       │      ┌─────────────┐                          │
       │      │ WU_COOLING  │ (gas=0, air cao)         │
       │      └──────┬──────┘                          │
       │             │ BT ≤ target+5 AND ET ≥ target-20│
       │             ▼                                  │
       │      ┌─────────────┐                          │
       │      │ WU_IDLE     │ (re-classify)            │
       │      └──────┬──────┘                          │
       │ NO          │                                 │
       ▼             │                                 │
┌─────────────┐     │                                 │
│ WU_PRE_     │ ←───┘ (NEW: thổi sạch chamber)        │
│ IGNITE      │                                       │
└──────┬──────┘                                        │
       │ air settled, 5-10s                            │
       ▼                                                │
┌─────────────┐                                        │
│ WU_IGNITE   │                                        │
└──────┬──────┘                                        │
       │ gasSignal=1                                   │
       ▼                                                │
┌─────────────┐                                        │
│ WU_HEATING  │ ─┐                                     │
│ (FAR/APPR)  │  │ RECOVERY (sub-mode khi BT vọt)     │
└──────┬──────┘  │                                     │
       │ btErr ≤ 5                                     │
       ▼          │                                     │
┌─────────────┐  │                                     │
│ WU_HOLDING  │ ─┤                                     │
│ (STABLE/REC)│  │                                     │
└──────┬──────┘  │                                     │
       │ elapsed ≥ 60%×totalTime                       │
       ▼                                                │
┌─────────────┐                                        │
│ WU_PRECISION│ (NEW: PI controller, FF learning)     │
└──────┬──────┘                                        │
       │ elapsed ≥ totalTime                           │
       └──────────────────────────────────────────────┘
```

---

## V. CHI TIẾT TỪNG STATE

### A. WU_IDLE — Phân loại Start Mode

**Logic:**
```cpp
enum WuStartMode { START_COLD, START_HOT, START_COOL };

WuStartMode classify(int16_t btNow, int16_t targetBT10) {
    if (btNow > targetBT10 + 200)  return START_COOL;  // > target+20°C
    if (btNow > targetBT10 - 500)  return START_HOT;   // gap < 50°C
    return START_COLD;
}
```

**Hành động theo mode:**

| Mode | Next state | Gas khởi đầu | Air khởi đầu |
|------|-----------|--------------|--------------|
| COLD | WU_PRE_IGNITE | gap/2 + 15 (cap 80) | A30 |
| HOT | WU_PRE_IGNITE | 25-40 (cap 50) | A35 |
| COOL | WU_COOLING | 0 | A60-A100 theo btAbove |

---

### B. WU_PRE_IGNITE (MỚI) — Thổi sạch chamber

**Mục đích:** Loại bỏ gas tồn đọng trong chamber, tránh ignite mạnh đột ngột.

**Logic:**
```cpp
case WU_PRE_IGNITE: {
    static uint16_t preIgniteTimer = 0;
    
    // Phase 1: Thổi mạnh (5 giây)
    if (preIgniteTimer < 5) {
        wuAirPercent = 70;
        airflowPercent = 70;
        gasPercent = 0;
    }
    // Phase 2: Giảm về A30 (5 giây)
    else if (preIgniteTimer < 10) {
        wuAirPercent = constrain(70 - (preIgniteTimer - 5) * 8, 30, 70);
        airflowPercent = wuAirPercent;
        gasPercent = 0;
    }
    // Phase 3: Chuyển sang IGNITE
    else {
        preIgniteTimer = 0;
        wuState = WU_IGNITE;
        nodeHMI.writeSingleRegister(START_GAS_BTN_W - 1, 1);
    }
    preIgniteTimer++;
}
```

**Tổng thời gian:** 10s

---

### C. WU_IGNITE — Mồi lửa (giữ logic hiện tại)

Không thay đổi. Giữ retry 3 lần.

---

### D. WU_HEATING — Tách FAR / APPROACH

**Sub-mode FAR (btError > 30°C):**
```cpp
// Gas theo công thức gap/2 + 15
int16_t gap = btError;  // °C × 10
int16_t targetGas;
if (startMode == START_COLD) {
    targetGas = constrain(gap/20 + 15, 30, 80);
} else { // HOT
    targetGas = constrain(gap/30 + 20, 25, 50);
}
wuGasPercent = targetGas;
wuAirPercent = 25; // A25 cố định trong FAR
```

**Sub-mode APPROACH (5 < btError ≤ 30°C):**
```cpp
// Predict BT 30s tới
int16_t btPredict = btNow + rorNow / 2; // rorBT/min × 0.5
if (btPredict > targetBT10) {
    int16_t excess = (btPredict - targetBT10) / 50; // mỗi 5°C
    wuGasPercent = constrain(wuGasPercent - excess * 5, 0, 100);
}
// Air tăng dần
if (wuAirPercent < 40) wuAirPercent = constrain(wuAirPercent + 5, 0, 40);
```

**Chuyển sang HOLDING:** `btError ≤ 5°C` (50 đơn vị ×10)

---

### E. WU_HOLDING — RECOVERY + STABLE (đã code hôm qua)

**RECOVERY (BT > target+10°C HOẶC rorBT > 30):**
- Gas về holdGasMin ngay
- Air theo rorBT
- Exit: BT < target+5°C AND rorBT < 10 trong **5s liên tục** (thêm hysteresis)

**STABLE:**
- Step ±5% / 20s confirm
- airCap động

**Chuyển sang PRECISION:** `wuElapsed ≥ wuTime_R × 60 × 60 / 100` (60% tổng thời gian)

---

### F. WU_PRECISION (MỚI) — PI Controller nhẹ

**Mục đích:** Khử offset, đạt target ±1°C ở phút cuối.

**Logic PI:**
```cpp
case WU_PRECISION: {
    int16_t error = targetBT10 - (int16_t)Temperature_BT;  // °C × 10
    
    // P term: Kp × error, Kp = 1/gasGain
    int16_t pTerm = error / phAdaptGasGain10;  // phần trăm gas
    
    // I term: tích lũy chậm, anti-windup
    static int32_t iAccum = 0;
    iAccum += error;
    iAccum = constrain(iAccum, -1000, 1000);  // anti-windup
    int16_t iTerm = (int16_t)(iAccum / 200);  // Ki rất nhỏ
    
    // Tổng output (% gas điều chỉnh quanh holdGasMin)
    int16_t holdGasMin = constrain(targetBT10/100 + 4, 15, 35);
    int16_t baseGas = holdGasMin + 5;  // điểm cân bằng
    wuGasPercent = constrain(baseGas + pTerm + iTerm, holdGasMin, 45);
    
    // Air: cố định A25-A30, ít đổi
    wuAirPercent = 25;
    
    // Học FF table khi |error| < 10 và |rorBT| < 10 trong 10s liên tục
    if (abs(error) <= 100 && abs(rorBT) <= 100) {
        if (++phStableCount >= 10) {
            phFFLearn((int16_t)Temperature_BT, wuGasPercent);
            phStableCount = 0;
        }
    } else {
        phStableCount = 0;
    }
}
```

**Tham số mới:**
```cpp
static int32_t phPiIAccum = 0;
static int16_t phAdaptGasGain10 = 30;  // mặc định: 3% gas → 1°C/min
```

---

## VI. ADAPT MỞ RỘNG — 5 hằng số máy

### Tham số mới:

```cpp
static int16_t phAdaptLossRate10 = 12;  // °C/min × 10 — nhiệt tổn thất ở target
static int16_t phAdaptGasGain10  = 30;  // °C/min trên 1% gas × 10
```

### Cách học:

**phAdaptLossRate10** — học trong HOLDING khi gas = holdGasMin:
```
loss_rate = -rorBT (khi gas cung cấp = loss → tổng = 0)
Update: EMA 80/20
```

**phAdaptGasGain10** — học khi STABLE có gas step:
```
gain = |delta_rorBT| / |delta_gas|  (sau dead time)
Update: EMA 70/30
```

### Lưu vào /ph_adapt.txt:
```
gasBoost heatAir runs coastMul lossRate gasGain
```

---

## VII. CSV LOG PER-5s

### File: `/PH5S.CSV`

### Format:
```
runNo,t,bt,et,gas,air,rorBT,rorET,state,subMode
1,0,1200,1180,30,30,1500,1800,IGNITE,-
1,5,1450,1620,55,25,2200,3000,HEATING,FAR
1,10,1680,1880,60,25,2500,3500,HEATING,FAR
...
```

### Cấu trúc code:
```cpp
static uint16_t phCsvLastElapsed = 65535;
static File phCsvFile;

void phCsvLog() {
    if (wuElapsed == phCsvLastElapsed) return;
    if (wuElapsed % 5 != 0) return;
    phCsvLastElapsed = wuElapsed;
    
    if (!phCsvFile) {
        bool isNew = !SD.exists("/PH5S.CSV");
        phCsvFile = SD.open("/PH5S.CSV", FILE_WRITE);
        if (isNew && phCsvFile) phCsvFile.println("run,t,bt,et,gas,air,rorBT,rorET,state,sub");
    }
    if (!phCsvFile) return;
    
    phCsvFile.print(phAdaptRuns); phCsvFile.print(',');
    phCsvFile.print(wuElapsed);   phCsvFile.print(',');
    phCsvFile.print(Temperature_BT); phCsvFile.print(',');
    phCsvFile.print(Temperature_ET); phCsvFile.print(',');
    phCsvFile.print(gasPercent);     phCsvFile.print(',');
    phCsvFile.print(airflowPercent); phCsvFile.print(',');
    phCsvFile.print(rorBT);          phCsvFile.print(',');
    phCsvFile.print(rorET);          phCsvFile.print(',');
    phCsvFile.print((int)wuState);   phCsvFile.print(',');
    phCsvFile.println(phCurrentSubMode);
    phCsvFile.flush();
}
```

### Đóng file khi preheat xong:
```cpp
if (phCsvFile) { phCsvFile.close(); }
```

**Lưu ý ISR safety:** `phCsvLog()` chỉ gọi trong `preheat()` (loop), KHÔNG trong ISR.

---

## VIII. TRIỂN KHAI THEO PHASE

### Phase 1 — Foundation (ngày 1)
1. Thêm `WuStartMode` enum + phân loại trong WU_IDLE
2. Thêm WU_PRE_IGNITE state
3. Test ignite với pre-ignite mới

### Phase 2 — HEATING tách FAR/APPROACH (ngày 1-2)
1. Sub-mode FAR với gas = gap/2 + 15
2. Sub-mode APPROACH với predict-based phanh
3. Test cold start 200°C

### Phase 3 — HOLDING RECOVERY hysteresis (ngày 2)
1. Thêm phRecoveryExitCount = 5s hysteresis
2. Test recovery scenario (BT vọt 30°C)

### Phase 4 — WU_PRECISION với PI (ngày 3)
1. Thêm state mới
2. PI controller với gasGain học từ ADAPT
3. Test holding 4-5 phút

### Phase 5 — ADAPT mở rộng (ngày 3-4)
1. Thêm lossRate + gasGain
2. Update phAdaptSave/Load
3. Log vào PHALOG.CSV

### Phase 6 — CSV log per-5s (ngày 4)
1. Thêm phCsvLog()
2. Test SD write timing

### Phase 7 — Full integration test (ngày 5+)
- Test 6 case: 160°C cold, 190°C cold, 200°C cold, 210°C hot, 230°C hot, 150°C cool
- Mỗi case ≥ 8/10 điểm

---

## IX. RAM BUDGET CHI TIẾT

| Thành phần | Bytes | Note |
|-----------|-------|------|
| WuStartMode + phStartMode | 1 | enum |
| preIgniteTimer | 2 | uint16_t |
| phPiIAccum | 4 | int32_t |
| phAdaptLossRate10 | 2 | int16_t |
| phAdaptGasGain10 | 2 | int16_t |
| phRecoveryExitCount | 1 | uint8_t |
| phCsvFile | ~30 | File object |
| phCsvLastElapsed | 2 | uint16_t |
| phCurrentSubMode | 1 | enum |
| **TỔNG** | **~45** | Trong budget 200 bytes |

Flash: ~2KB cho code mới — vẫn trong budget.

---

## X. TIÊU CHÍ NGHIỆM THU

| Test case | Overshoot | Ổn định cuối | Điểm tối thiểu |
|-----------|-----------|-------------|----------------|
| 200°C cold (120→200) | ≤3°C | ±2°C, target ±1°C | 8/10 |
| 190°C cold (116→190) | ≤3°C | ±2°C | 8/10 |
| 160°C cold (120→160) | ≤3°C | ±2°C | 8/10 |
| 230°C hot (155→230) | ≤2°C | ±2°C | 9/10 |
| 210°C hot (160→210) | ≤2°C | ±2°C | 9/10 |
| 150°C cool (215→150) | ≤5°C | ±3°C | 7/10 |

**Mục tiêu trung bình:** ≥8.3/10 trên 6 case.

---

## XI. CHANGELOG TUNE TRƯỚC ĐÓ (2026-05-28)

1. `volatile` cho biến ISR-shared
2. `phBTNoRiseCount` increment đúng
3. HEATING→HOLDING clamp gas về holdGasMax=45
4. Range check thay `==` cho wuElapsed
5. `phFFSnapDone` flag cho FF snap-at-ignition
6. `phCoolDbgTimer` riêng cho COOLING debug
7. Cooling ignite: thêm check `ET ≥ target − 20°C`
8. holdGasMin động: `constrain(target/100+4, 15, 35)`
9. Air/gas coupling: airCap động
10. btError step ngưỡng: −50 → −30
11. Gas khởi động dynFloor: `gap/20 + 35`
12. HOLDING tách RECOVERY/STABLE

---

## XII. QUYẾT ĐỊNH CHI TIẾT (ĐÃ CHỐT)

| # | Vấn đề | Quyết định | Implementation |
|---|--------|-----------|----------------|
| 1 | PI integral reset | **Không bao giờ reset** | I term tự điều chỉnh, anti-windup bằng `constrain(iAccum, -1000, 1000)` |
| 2 | HMI hiển thị mode | **Không hiển thị** | Bỏ qua, không push STT_PREHEAT_FAR/APPROACH/PRECISION |
| 3 | Reset ADAPT button | **Không có nút** | User rút SD card xóa `/ph_ff.txt` và `/ph_adapt.txt` thủ công khi cần |
| 4 | CSV rotation | **Sau 50 lần preheat** | Khi `phAdaptRuns % 50 == 0` → xóa `/PH5S.CSV` cũ, tạo mới |
| 5 | PRE_IGNITE skip hot | **Bỏ qua khi hot start** | COLD → PRE_IGNITE → IGNITE; HOT → IGNITE trực tiếp |

### Code implementation chi tiết:

**1. PI không reset — chỉ anti-windup:**
```cpp
// Trong WU_PRECISION
static int32_t iAccum = 0;  // không reset khi vào state
iAccum += error;
iAccum = constrain(iAccum, -1000, 1000);  // anti-windup duy nhất
```

**4. CSV rotation:**
```cpp
// Trong phCsvLog(), khi mở file lần đầu mỗi run:
if (!phCsvFile) {
    if (phAdaptRuns > 0 && phAdaptRuns % 50 == 0 && SD.exists("/PH5S.CSV")) {
        SD.remove("/PH5S.CSV");  // xóa khi tròn 50 lần
    }
    bool isNew = !SD.exists("/PH5S.CSV");
    phCsvFile = SD.open("/PH5S.CSV", FILE_WRITE);
    if (isNew && phCsvFile) phCsvFile.println("run,t,bt,et,gas,air,rorBT,rorET,state,sub");
}
```

**5. PRE_IGNITE skip cho hot start:**
```cpp
// Trong WU_IDLE sau khi classify:
if (mode == START_HOT) {
    wuState = WU_IGNITE;       // bỏ qua PRE_IGNITE
    nodeHMI.writeSingleRegister(START_GAS_BTN_W - 1, 1);
} else if (mode == START_COLD) {
    wuState = WU_PRE_IGNITE;   // có pre-ignite
}
```

---

**Plan đã hoàn chỉnh. Sẵn sàng triển khai từng phase theo mục VIII.**

---

## XIII. REVIEW v2 — 8 CẢI TIẾN QUAN TRỌNG (2026-05-29)

Sau khi review code Opus đã viết, phát hiện 8 vấn đề kỹ thuật cần sửa.

### 1. COOLING exit — thêm guard ET

**Vấn đề:** Code exit COOLING chỉ check BT ≤ target-5, không check ET. Nếu ET vẫn cao, ignite sẽ làm BT bùng lên ngay.

**Sửa:**
```cpp
if ((int16_t)Temperature_BT <= targetBT10 - 50 && rorBT <= 0
    && (int16_t)Temperature_ET >= targetBT10 - 200
    && (int16_t)Temperature_ET <= targetBT10 + 100) {  // ET không quá cao
    wuState = WU_IDLE;
}
```

---

### 2. PRE_IGNITE hot start — purge ngắn 4s (sửa quyết định 5)

**Vấn đề cũ:** Quyết định "bỏ qua PRE_IGNITE khi hot start" sai vì:
- Hot start vẫn có thể có gas tồn trong chamber từ lần rời trước
- Cần làm thoáng chamber để ignite ổn định

**Sửa:**
- COLD: PRE_IGNITE 10s (5s A70 + 5s A30)
- HOT: PRE_IGNITE 4s (2s A60 + 2s A30)
- COOL: sau cooling vẫn qua PRE_IGNITE 4s

---

### 3. PRE_IGNITE timer dùng millis()

**Vấn đề:** `timer++` mỗi loop sai vì:
- Loop chạy không đều
- Throttle 1Hz làm timer trễ khi SD write hoặc Modbus chậm
- Phụ thuộc tần suất gọi

**Sửa:** Dùng `millis()` snapshot:
```cpp
case WU_PRE_IGNITE: {
    static uint32_t preIgniteStartMs = 0;
    if (preIgniteStartMs == 0) preIgniteStartMs = millis();
    uint32_t elapsedMs = millis() - preIgniteStartMs;

    uint16_t totalMs  = (phStartMode == START_HOT) ? 4000 : 10000;
    uint16_t phase1Ms = totalMs / 2;

    if (elapsedMs < phase1Ms) {
        wuAirPercent = (phStartMode == START_HOT) ? 60 : 70;
    } else if (elapsedMs < totalMs) {
        wuAirPercent = 30;
    } else {
        preIgniteStartMs = 0;
        wuState = WU_IGNITE;
        nodeHMI.writeSingleRegister(START_GAS_BTN_W - 1, 1);
    }
    gasPercent = 0;
    airflowPercent = wuAirPercent;
}
```

---

### 4. PI integral RESET theo run/target/mode (sửa quyết định 1)

**Vấn đề cũ:** "Không bao giờ reset" sai vì:
- I term tích từ run trước với target khác → áp dụng sai cho run mới
- Đổi target 200→160 nhưng I vẫn nhớ offset 200 → gas sai
- Overshoot run trước → I âm tích → run này undershoot

**Sửa — reset I khi:**
1. Vào WU_PRECISION lần đầu mỗi run
2. Target thay đổi giữa các run (track `phPiLastTarget`)
3. RECOVERY trigger trong PRECISION (state cũ không còn đúng)

```cpp
static int16_t phPiLastTarget = 0;

// Khi vào PRECISION:
if (targetBT10 != phPiLastTarget) {
    phPiIAccum = 0;
    phPiLastTarget = targetBT10;
}

// Khi RECOVERY trong PRECISION:
if (inRecovery) phPiIAccum = 0;
```

---

### 5. PI scaling — sửa đơn vị đúng

**Vấn đề:** `pTerm = error / gasGain10` sai về đơn vị:
- error: °C × 10
- gasGain10: °C/min × 10 / %
- Chia → 0, không có ý nghĩa vật lý

**Sửa — Kp theo %/°C trực tiếp:**
```cpp
// P term: ~0.5% gas / 1°C error, cap ±5%
int16_t pTerm = (int16_t)((int32_t)error * 5 / 100);  // error/10 × 0.5 = error × 0.05
pTerm = constrain(pTerm, -5, 5);

// I term: tích lũy chậm, cap ±5%
phPiIAccum += error;
phPiIAccum = constrain(phPiIAccum, (int32_t)-2000, (int32_t)2000);
int16_t iTerm = (int16_t)(phPiIAccum / 400);
```

`gasGain10` vẫn dùng cho FF table và adaptive learning, không dùng trực tiếp trong PI.

---

### 6. ET/rorBT guard cho FAR và PRECISION (không hardcode air)

**Vấn đề:** `wuAirPercent = 25` cứng trong FAR và PRECISION sai khi:
- ET tăng vọt → cần tăng air để cân bằng
- rorBT âm → cần giảm air giữ nhiệt
- ET > target nhiều → cần air pha loãng

**Sửa FAR:**
```cpp
wuAirPercent = 25;  // default
if (rorET > 400)                                 wuAirPercent = 35;
if ((int16_t)Temperature_ET > targetBT10 + 200) wuAirPercent = 40;
if (rorBT < 0 && btError > 1000)                 wuAirPercent = 20;
```

**Sửa PRECISION — air linh hoạt 20-35 với slew rate:**
```cpp
int16_t airTarget = 25;
if (error >  100)                                airTarget = 22;
if (error < -100)                                airTarget = 30;
if (rorBT < -50)                                 airTarget = 20;
if ((int16_t)Temperature_ET > targetBT10 + 150) airTarget = 35;

// Slew rate: max ±2%/s
if      (wuAirPercent < airTarget) wuAirPercent = constrain(wuAirPercent + 2, 20, 40);
else if (wuAirPercent > airTarget) wuAirPercent = constrain(wuAirPercent - 2, 20, 40);
```

---

### 7. APPROACH dùng targetGas + slew rate

**Vấn đề:** `wuGasPercent -= cut * 5` mỗi giây sai:
- Trừ 5-20%/giây quá thô
- Tạo dao động khi predict thay đổi liên tục
- Không có điểm cân bằng

**Sửa — tính gas đích, slew rate đến đó:**
```cpp
int16_t btPredict = (int16_t)Temperature_BT + rorBT / 2;
int16_t overrun   = btPredict - targetBT10;

int16_t holdMin = constrain(targetBT10 / 100 + 4, 15, 35);
int16_t baseGas = holdMin + 10;  // baseline APPROACH
int16_t targetGas;

if (overrun > 0) {
    int16_t reduction = constrain(overrun / 50 * 5, 0, 30);
    targetGas = constrain(baseGas - reduction, holdMin, baseGas);
} else {
    targetGas = baseGas;
}

// Slew rate: gas ±3%/s, có deadband ±2
if      (wuGasPercent > targetGas + 2) wuGasPercent = constrain(wuGasPercent - 3, 0, 100);
else if (wuGasPercent < targetGas - 2) wuGasPercent = constrain(wuGasPercent + 3, 0, 100);
else                                    wuGasPercent = targetGas;
```

---

### 8. ADAPT chỉ học khi THẬT SỰ stable

**Vấn đề:** Học mỗi giây khi `|error| < 10 && |rorBT| < 100` quá lỏng:
- 1 lần preheat lệch → save → lần sau lệch hơn
- Không check air ổn định
- Không check không trong recovery
- Compound error qua các run

**Sửa — strict stable detection:**
```cpp
static uint8_t phStrictStableCount = 0;
static int16_t lastGas = 0, lastAir = 0;

bool isStrictStable =
    abs(error) <= 50 &&              // BT ±5°C target
    abs(rorBT) <= 30 &&              // RoR BT < 3°C/min
    abs(rorET) <= 50 &&              // không có ET spike
    wuGasPercent == lastGas &&       // gas không đổi
    wuAirPercent == lastAir &&       // air không đổi
    !inRecovery &&
    wuElapsed > 60;                  // qua 60s từ vào HOLDING

if (isStrictStable) {
    if (++phStrictStableCount >= 30) {  // 30s liên tục stable
        phFFLearn(...);
        if (wuGasPercent <= holdMin + 2) phLearnLossRate(rorBT);
        phStrictStableCount = 0;
    }
} else {
    phStrictStableCount = 0;
}
lastGas = wuGasPercent;
lastAir = wuAirPercent;
```

**Sanity check chặt hơn cho lossRate:**
```cpp
void phLearnLossRate(int16_t rorBtNow) {
    if (rorBtNow > 0 || rorBtNow < -50) return;
    int16_t newLoss = -rorBtNow;
    if (newLoss < 5 || newLoss > 30) return;  // physical range
    // EMA 90/10 — học chậm
    phAdaptLossRate10 = (int16_t)((int32_t)phAdaptLossRate10 * 9 / 10 + (int32_t)newLoss * 1 / 10);
}
```

---

### Bảng tổng kết 8 cải tiến

| # | Vấn đề | Nơi sửa |
|---|--------|---------|
| 1 | COOLING exit thiếu guard ET cao | WU_COOLING exit condition |
| 2 | PRE_IGNITE skip hot sai | Quyết định 5 (sửa) |
| 3 | Timer PRE_IGNITE dùng millis() | WU_PRE_IGNITE case |
| 4 | PI integral reset theo target | Quyết định 1 (sửa) |
| 5 | PI scaling đơn vị sai | WU_PRECISION PI calc |
| 6 | Air hardcode A25 trong FAR/PRECISION | FAR + PRECISION air logic |
| 7 | APPROACH thiếu slew rate | APPROACH gas calc |
| 8 | ADAPT học quá lỏng | phLearnLossRate + strict stable |

---

## XIV. QUYẾT ĐỊNH ĐÃ CHỈNH SỬA

| # | Vấn đề | Quyết định CŨ | Quyết định MỚI |
|---|--------|---------------|----------------|
| 1 | PI integral reset | Không reset | Reset khi đổi target, vào PRECISION lần đầu, RECOVERY trigger |
| 5 | PRE_IGNITE hot | Bỏ qua | Ngắn 4s (COLD: 10s, HOT: 4s) |

---

## XV. REVIEW v3 — 10 CẢI TIẾN KIẾN TRÚC (2026-05-29)

### 1. Trạng thái dự án: Prototype

Plan trước viết "sẵn sàng triển khai" → sai. Chuẩn hóa 4 mức ở đầu plan.

### 2. PHASE 0 — Safety/Fault Layer (TRƯỚC Phase 1)

**5 guard cần thiết:**

```cpp
// 2.1 BT/ET sensor drop > 50°C/5s → fault flag, không trust giá trị
static int16_t btHistory[5] = {0};  // 5 mẫu BT × 1s
static int16_t etHistory[5] = {0};
static bool phSensorFault = false;
// Mỗi giây: shift array, check max-min > 500 → set fault

// 2.2 rorBT > 500°C/min → fire cut ngay (đột ngột bất thường)
if (rorBT_smooth > 5000) {  // ×10 unit
    fireCutFlag = true;
    setMachineStatus(STT_ROR_BT_EXTREME);
}

// 2.3 Gas signal mất giữa HEATING/HOLDING/PRECISION → retry IGNITE
if ((wuState >= WU_HEATING) && gasSignal == 0 && wuGasPercent > 5) {
    gasLostCount++;
    if (gasLostCount > 3) {
        setMachineStatus(STT_PREHEAT_GAS_LOST);
        wuState = WU_IGNITE;  // retry
    }
}

// 2.4 Modbus HMI timeout > 30s → giữ state, không reset
// Đã có trong code Modbus, chỉ thêm: nếu WU_R cuối cùng = 1 → giữ wuState

// 2.5 SD card unmount → skip log, không crash
// Trong phCsvLog(): check SD.card_present trước mỗi write
```

**Chi phí:** ~500 bytes Flash, ~30 bytes RAM (history arrays).

### 3. WU_COAST — state mới sau COOLING

**Tách rõ COOLING vs COAST:**

| | COOLING | COAST |
|--|---------|-------|
| Trigger | BT > target + 200 | BT vào [target-50, target+200] sau cooling |
| Gas | 0 | 0 |
| Air | 60-100% | 30-40% |
| Mục tiêu | Hút nhiệt nhanh | Chờ ET hội tụ với BT |
| Exit | BT ≤ target+200 | abs(ET-BT) < 50 AND ET trong [target-100, target+100] |

```cpp
case WU_COAST: {
    wuGasPercent = 0;
    int16_t etBtGap = (int16_t)Temperature_ET - (int16_t)Temperature_BT;

    // Air vừa phải để chờ hội tụ
    wuAirPercent = 35;

    // Exit: ET và BT đều trong vùng target ±10°C
    if (abs(etBtGap) < 50
        && (int16_t)Temperature_ET >= targetBT10 - 100
        && (int16_t)Temperature_ET <= targetBT10 + 100) {
        wuState = WU_PRE_IGNITE;  // sau coast luôn qua PRE_IGNITE 4s
        if (enDebug) SerialComputer.println("COAST -> PRE_IGNITE");
    }
    gasPercent = 0;
    airflowPercent = wuAirPercent;
}
break;
```

### 4. State Invariant cho mọi state

```cpp
bool validateInvariant() {
    switch (wuState) {
        case WU_IDLE:        return gasPercent == 0;
        case WU_COOLING:     return gasPercent == 0 && airflowPercent >= 40;
        case WU_COAST:       return gasPercent == 0 && airflowPercent >= 20 && airflowPercent <= 50;
        case WU_PRE_IGNITE:  return gasPercent == 0 && airflowPercent >= 25;
        case WU_IGNITE:      return airflowPercent >= 25 && airflowPercent <= 50;
        case WU_HEATING:     return airflowPercent <= 80;
        case WU_HOLDING:
        case WU_PRECISION:   return airflowPercent <= 40;
        default:             return true;
    }
}

// Gọi cuối preheat() trước khi return:
if (!validateInvariant()) {
    setMachineStatus(STT_PREHEAT_INVARIANT_FAIL);
    gasPercent = 0;
    airflowPercent = 30;
}
```

### 5. PI update theo millis(), không phụ thuộc loop

```cpp
static uint32_t phPiLastUpdateMs = 0;
uint32_t nowMs = millis();
uint32_t dt = nowMs - phPiLastUpdateMs;
if (dt < 950) {
    // Giữ output cũ
    gasPercent = constrain(wuGasPercent, 0, 100);
    airflowPercent = constrain(wuAirPercent, 0, 40);
    break;
}
phPiLastUpdateMs = nowMs;

// I term scale theo dt thực tế
phPiIAccum += (int32_t)error * (int32_t)dt / 1000;
```

### 6. rorBT_smooth — EMA filter 5s

```cpp
static int16_t rorBT_smooth = 0;
// Mỗi giây trong phThermalMonitor():
rorBT_smooth = (int16_t)((int32_t)rorBT_smooth * 8 / 10 + (int32_t)rorBT * 2 / 10);
// Tau ≈ 5s, giảm jitter cho RECOVERY trigger và predict
```

**Sử dụng `rorBT_smooth` cho:**
- RECOVERY trigger: `rorBT_smooth > 30`
- APPROACH predict: `btPredict = bt + rorBT_smooth / 2`
- PI controller error rate

**Giữ `rorBT` thô cho:**
- Debug log
- Fire cut alarm (#2.2)

### 7. Slew limit chung cho gas/air

```cpp
int16_t slewLimit(int16_t current, int16_t target, int16_t maxRate) {
    int16_t diff = target - current;
    if      (diff >  maxRate) return current + maxRate;
    else if (diff < -maxRate) return current - maxRate;
    return target;
}

// Cuối preheat() trước khi assign final:
int16_t gasRate = (wuState == WU_HOLDING && inRecovery) ? 30 : 5;  // RECOVERY allow fast cut
gasPercent     = slewLimit(gasPercent, constrain(wuGasPercent, 0, 100), gasRate);
airflowPercent = slewLimit(airflowPercent, constrain(wuAirPercent, 0, 80), 3);
```

### 8. ADAPT — chỉ save khi run tốt

```cpp
void phRunLearn(bool normalEnd) {
    // ... tính score như cũ
    int16_t score10 = ...;

    bool isBootstrap = (phAdaptRuns < 3);  // 3 lần đầu vẫn save để bootstrap
    bool isGoodRun   = (score10 >= 7);

    if (normalEnd && (isGoodRun || isBootstrap)) {
        // Update params + save
        if (changed) phAdaptSave();
    } else {
        if (enDebug) {
            SerialComputer.print("RUN bad score="); SerialComputer.print(score10);
            SerialComputer.println(" - not saving adapt");
        }
        // Vẫn log vào PHALOG.CSV để phân tích, chỉ không save ADAPT
    }
    if (normalEnd) phAdaptLog(...);
}
```

### 9. CSV mở rộng — reason/fault/score + rorBT_smooth

Format mới:
```
runNo,t,bt,et,gas,air,rorBT,rorBTsmooth,rorET,state,subMode,reason,fault,score
```

**Reason enum (1 byte):**
```
0=NORMAL       — không có sự kiện
1=APPR_BRAKE   — APPROACH phanh do predict vượt
2=RECOVERY     — RECOVERY active (HOLDING/PRECISION)
3=PI_P         — gas thay đổi chủ yếu do P term
4=PI_I         — gas thay đổi chủ yếu do I term
5=AIR_GUARD    — air guard kích hoạt (ET cao, etc.)
6=SLEW_LIMIT   — slew limit clamp gas/air
7=INVARIANT_FIX — invariant violation, force reset
```

**Fault bitfield (1 byte):**
```
bit 0: SENSOR_DROP (BT/ET drop bất thường)
bit 1: ROR_EXTREME (rorBT > 500°C/min)
bit 2: GAS_LOST    (gas signal mất)
bit 3: HMI_TIMEOUT (Modbus HMI > 30s không phản hồi)
bit 4: SD_FAIL     (SD card unmount)
```

**Score:** -1 cho mọi dòng giữa run, chỉ ghi giá trị thực ở dòng cuối (khi kết thúc).

### 10. Test scope

**Prototype phase (Phase 8):**
- 3 lần/case × 6 case = 18 lần preheat (~90 phút)
- Trung bình ≥ 8/10, worst ≥ 6/10
- Không có run nào vọt > 10°C

**Fault injection phase (Phase 9):**
- 4 case × 1 lần = 4 lần (~30 phút)
  - Rút SD card giữa run
  - Gas signal mất giữa HEATING
  - BT sensor cho giá trị âm
  - HMI mất kết nối

**Production approve (Phase 10):**
- 5 lần/case × 6 case = 30 lần preheat (~2.5 giờ)
- Trung bình ≥ 8.5/10, worst ≥ 7/10
- 0 lần thảm họa

---

## XVI. THỨ TỰ TRIỂN KHAI v3

```
Phase 0  — Safety/Fault Layer + rorBT_smooth + State Invariant   [PRIORITY]
Phase 1  — Foundation (StartMode, PRE_IGNITE millis-based 4s/10s)
Phase 2  — HEATING FAR/APPROACH (đã code, tinh chỉnh + air guard FAR)
Phase 2b — WU_COAST state mới
Phase 3  — HOLDING RECOVERY hysteresis exit
Phase 4  — PRECISION PI (đã code, sửa: PI millis-based, dùng rorBT_smooth)
Phase 5  — ADAPT save-only-good (bootstrap exception)
Phase 6  — CSV log: score/fault/reason/rorBT_smooth
Phase 7  — Slew limit chung (refactor cleanup)
Phase 8  — Prototype test 3 lần/case
Phase 9  — Fault injection
Phase 10 — Production test 5 lần/case → approve
```

---

## XVII. 4 QUYẾT ĐỊNH v3 (ĐÃ CHỐT)

| # | Câu hỏi | Quyết định | Lý do |
|---|---------|-----------|-------|
| 1 | Phase 0 cover bao nhiêu guard? | **Full 5 guard** | ~500 bytes Flash, mỗi cái 1 failure mode riêng — không nên cắt |
| 2 | WU_COAST tách state riêng? | **Tách state riêng** | Air range khác hẳn COOLING, exit condition khác, debug dễ hơn |
| 3 | CSV reason: enum hay string? | **Enum 0-7** | File 4x nhỏ hơn, parse PC dễ, map enum→tên trong tài liệu |
| 4 | Test scope mỗi case? | **3 lần prototype, 5 lần production** | 3 lần đủ phát hiện noise vs bug, 5 lần khi approve |

---

## XVIII. RAM/FLASH BUDGET v3

**Thêm so với v2:**

| Thành phần | RAM | Flash |
|-----------|-----|-------|
| btHistory[5] + etHistory[5] | 20 | ~80 |
| rorBT_smooth | 2 | ~30 |
| phSensorFault + gasLostCount | 2 | ~50 |
| WU_COAST case | 0 | ~150 |
| validateInvariant() | 0 | ~200 |
| slewLimit() function | 0 | ~80 |
| phPiLastUpdateMs | 4 | ~40 |
| ADAPT bootstrap logic | 0 | ~60 |
| CSV reason/fault tracking | 2 | ~120 |
| **TỔNG v3** | **~30** | **~810** |

**Cộng dồn:**
- RAM: 70.5% (đã có) + 30 bytes ≈ 70.6%
- Flash: 38.9% (đã có) + 810 bytes ≈ 39.2%

Vẫn an toàn trong budget.

---

**Plan v3 đã đầy đủ. Sẵn sàng triển khai từ Phase 0.**
