# Roaster Thermal Analysis
**File dữ liệu:** `testnhiet.csv`  
**Ngày phân tích:** 2026-05-07  
**Điều kiện:** Máy không tải — worst case noise test  
**Giai đoạn hợp lệ:** 00:00 → 31:23 (1884 điểm, 1s/điểm)

---

## 1. Vị trí cảm biến & chuỗi nhân quả

| Cảm biến | Vị trí | Đo gì |
|----------|--------|-------|
| **BT** | Trong lồng rang | Nhiệt độ sản phẩm (khi có hạt) / không khí lồng rang (khi không tải) |
| **ET** | Ống khí thải | Nhiệt độ khí thoát ra sau khi đi qua lồng rang |

```
                    ┌──────────────────────────────────────────────┐
                    │                                              │
  Burner (Gas%) ────┤──[lag 3-6s]──► RoR_ET ──[lag 3-5s]──► RoR_BT ──[∫dt]──► BT
                    │                   ▲
  Airflow (Air%) ───┤──[lag 2-8s]───────┘
                    │
                    └──────────────────────────────────────────────┘
```

- **Gas** và **Airflow** là 2 đầu vào điều khiển — cả hai cùng ảnh hưởng ET
- **ET** là tín hiệu trung gian — phản ứng nhanh hơn BT 3-5s
- **RoR_ET** dùng làm early warning cho RoR_BT **chỉ khi airflow ổn định**
- **BT** là kết quả tích lũy — là tích phân của RoR_BT theo thời gian

---

## 2. Steady State — Gas cố định, RoR_BT ổn định ở đâu?

| Gas% | RoR_BT trung bình | RoR_BT min | RoR_BT max | BT tương ứng |
|------|------------------|-----------|-----------|--------------|
| 65%  | ~140°C/min       | —         | —         | 60–95°C      |
| 47%  | **27.8°C/min**   | 18.4      | 46.6      | 161–192°C    |
| 35%  | **2.1°C/min**    | -4.2      | 5.8       | 208–222°C    |
| 18%  | **-3.0°C/min**   | -10.0     | 0.6       | 227–231°C    |
| 8%   | **-5.9°C/min**   | -19.0     | -0.2      | 181–217°C    |

- Gas ~35% là **điểm cân bằng nhiệt** ở vùng 210–220°C → RoR_BT ≈ 0
- Gas > 35% → RoR_BT > 0 → BT tăng
- Gas < 35% → RoR_BT < 0 → BT giảm

---

## 3. Step Response — Burner thay đổi → RoR_BT phản ứng thế nào?

### Gas 41% → 35% (giảm 6%) tại BT=202°C
| +Δt | RoR_BT (10s) | ΔROR |
|-----|-------------|------|
| +0s | 14.4 | -0.6 |
| +6s | 9.6 | **-5.4** ← phản ứng rõ |
| +12s | 3.0 | -12.0 |
| +15s | 4.8 | -10.2 (ổn định) |

→ **Lag: 5–6s | Ổn định: ~15s | Không overshoot**

### Gas 23% → 37% (tăng 14%) tại BT=188°C
| +Δt | RoR_BT (10s) | ΔROR |
|-----|-------------|------|
| +0s | 5.4 | 0 |
| +6s | 13.8 | **+9.0** ← phản ứng rõ |
| +15s | 27.6 | **+22.8** ← plateau |
| +30s | 23.4 | +18.6 (giảm nhẹ) |

→ **Lag: 3–6s | Ổn định: ~15s | Có overshoot nhẹ**

### Bất đối xứng tăng/giảm Gas

| | Tăng gas | Giảm gas |
|--|----------|---------|
| Lag | 3–6s | 5–6s |
| Ổn định | ~15s | 15–60s |
| Overshoot RoR | Có | Không |
| Phụ thuộc BT | Ít | Nhiều |

---

## 4. Độ nhạy Gas → RoR_BT

| Sự kiện | ΔGas | BT | RoR trước | RoR sau 30s | ΔROR | Độ nhạy |
|---------|------|----|----------|------------|------|---------|
| 46→41% | -5% | 202°C | 13.0 | 6.0 | -7.0 | **1.4 °C/min/%Gas** |
| 35→18% | -17% | 237°C | 17.4 | -10.0 | -27.4 | **1.6** |
| 23→37% | +14% | 188°C | 9.2 | 24.2 | +15.0 | **1.1** |
| 18→8%  | -10% | 229°C | 1.6 | -20.0 | -21.6 | **2.2** |

- **Trung bình dùng cho control: ~1.5 °C/min per %Gas** (vùng BT 180–240°C)
- Độ nhạy cao hơn khi giảm gas và khi BT cao

---

## 5. Step Response — Airflow thay đổi → ET và RoR_ET phản ứng thế nào?

### Air 0% → 18% | Gas=35%, BT=210°C
| +Δt | ET | RoR_ET (10s) | Nhận xét |
|-----|----|-------------|---------|
| +0s | 199.9 | 5.4 | baseline |
| +6s | 201.4 | 11.4 | tăng rõ |
| +10s | 202.0 | **12.6** | đỉnh |
| +25s | 203.9 | 8.4 | ổn định ~7 |
| +40s | 205.6 | 6.6 | plateau +6°C |

→ **Airflow thấp: ET tăng — kéo thêm khí nóng từ burner | Lag 2-3s**

### Air 18% → 40% | Gas=35%, BT=217°C
| +Δt | ET | RoR_ET (10s) | Nhận xét |
|-----|----|-------------|---------|
| +0s | 210.8 | 6.0 | baseline |
| +10s | 211.7 | 5.4 | bắt đầu giảm |
| +15s | 211.9 | 1.8 | **giảm mạnh** |
| +30s | 212.2 | 1.2 | plateau thấp |

→ **Airflow tăng mạnh: RoR_ET giảm từ 6 xuống 1.2 | Lag 5-8s**

### Air 40% → 60% | Gas=35%, BT=221°C
| +Δt | ET | RoR_ET (10s) | Nhận xét |
|-----|----|-------------|---------|
| +0s | 221.2 | 5.4 | baseline |
| +12s | 221.2 | -1.2 | **RoR_ET âm** |
| +28s | 221.1 | 0 | ET dừng hoàn toàn |

→ **Airflow cao: ET bị kéo xuống, gas không đủ bù | Lag 5-8s**

### Air 60% → 0% | Gas=35%, BT=220°C
| +Δt | ET | RoR_ET (10s) | Nhận xét |
|-----|----|-------------|---------|
| +0s | 222.2 | 2.4 | baseline |
| +14s | 223.3 | 7.2 | tăng mạnh |
| +20s | 224.7 | **14.4** | đỉnh |
| +30s | 226.8 | 12.6 | ET vẫn tăng |

→ **Tắt airflow: ET tăng vọt +14°C/min, nhiệt không thoát được | Lag 8-10s**

### Tóm tắt airflow step response

| ΔAir% | ET thay đổi | RoR_ET sau 15s | Lag |
|-------|------------|----------------|-----|
| 0→18% | +6°C | 9.0 | 2-3s |
| 18→40% | ~0 | 1.8 | 5-8s |
| 40→60% | -0.1°C | -2.4 | 5-8s |
| 60→0% | +6°C | 12.0 | 8-10s |

**Điểm inflection:** Air ~18-20% với gas=35% — ET tăng nhẹ và ổn định

---

## 6. Airflow tác động BT gián tiếp qua ET

- Air 18→40%: BT **dừng tăng** sau 7s
- Air 40→60%: BT **bắt đầu giảm** sau 8s
- Air 60→0%: BT **tăng vọt** 220→231°C trong 30s

→ **Airflow ảnh hưởng BT chậm hơn ET ~3-5s**

---

## 7. dRoR/dt — Gia tốc RoR dự đoán chiều BT

| dRoR/dt | Ý nghĩa | BT sẽ đi đâu |
|---------|---------|-------------|
| > +5°C/min² | RoR tăng nhanh | BT UP mạnh |
| +1 đến +5 | RoR tăng nhẹ | BT UP chậm |
| -1 đến +1 | RoR ổn định | BT theo quán tính |
| -1 đến -5 | RoR giảm | BT sắp chậm lại |
| < -5°C/min² | RoR giảm nhanh | BT sắp đỉnh hoặc đảo chiều |

**Ví dụ từ dữ liệu:**
```
t=10:15 | BT:221.4 | RoR:4.6 | dRoR:+2.2  → BT DOWN ✓ (RoR sắp đảo chiều)
t=10:45 | BT:220.0 | RoR:-2.8| dRoR:-7.4  → BT DOWN ✓
t=07:45 | BT:217.0 | RoR:5.4 | dRoR:+2.0  → BT DOWN ✓
```
→ dRoR/dt đổi dấu **trước khi BT đổi chiều** — dùng làm early warning

---

## 8. Dự đoán BT 30 giây tới

```
BT_pred(t+30s) = BT(t) + RoR_BT(t) × 0.5
```

| Vùng | Gas% | MAE | Max Error |
|------|------|-----|-----------|
| BT đang leo | 47% | 3.67°C | 9.0°C |
| BT gần plateau | 35% | **1.23°C** | 4.1°C |
| BT đang giảm | 18% | 1.68°C | 3.1°C |
| BT giảm chậm | 8% | **0.90°C** | 4.1°C |

Cải thiện bằng cách thêm dRoR/dt:
```
BT_pred = BT + RoR_BT × 0.5 + dRoR × 0.125 × K
```

---

## 9. Điều kiện dùng ET làm early warning cho RoR_BT

**Được dùng khi:** Airflow ổn định ít nhất **20-30s**

**Không dùng khi:**
- Airflow đang thay đổi (ET bị nhiễu loạn)
- Air=0% (ET tăng vọt — không phản ánh nhiệt thực vào hạt)
- Gas và Airflow thay đổi đồng thời

---

## 10. Model tham số tổng hợp (điều kiện không tải)

```
┌──────────────────────────────────────────────────────────────┐
│  Gas(t)     ──[lag 3-6s]──┐                                  │
│                           ├──► RoR_ET ──[lag 3-5s]──► RoR_BT──[∫dt]──► BT
│  Airflow(t) ──[lag 2-8s]──┘                                  │
│                                                              │
│  Gas gain:       ~1.5 °C/min per %Gas (BT 180–240°C)        │
│  Gas lag:        3–6s | Gas time const: ~15s                 │
│  Air lag:        2–8s (tăng) / 8–10s (giảm)                 │
│  Air time const: ~20-25s                                     │
│  Equilibrium:    Gas~35%, Air~18% → RoR_BT≈0 tại BT~215°C  │
└──────────────────────────────────────────────────────────────┘
```

---

## 11. Hệ quả thiết kế controller

### Gas correction
```
Gas_correction = (RoR_target - RoR_actual) / 1.5
```
- Chờ **15s** trước khi đánh giá hiệu quả
- Clamp: ±5% gas mỗi lần

### Ngưỡng can thiệp
| Tình huống | Điều kiện | Hành động |
|-----------|-----------|----------|
| RoR quá cao | RoR > target + 3°C/min | Giảm gas 2% |
| RoR quá thấp | RoR < target - 3°C/min | Tăng gas 2% |
| RoR crash | dRoR/dt < -8°C/min² | Tăng gas ngay 3–5% |
| RoR spike | dRoR/dt > +10°C/min² | Outlier — bỏ qua |
| ET vọt cao | Air=0 và RoR_ET > 10 | Không dùng ET làm feedforward |

---

## 12. Khi có sản phẩm (ước tính)

| Tham số | Không tải | Có sản phẩm |
|---------|-----------|------------|
| Gas lag | 3–6s | **15–25s** |
| Gas time const | ~15s | **45–75s** |
| Gas gain | ~1.5°C/min/%Gas | **0.3–0.8** |
| Air lag | 2–8s | **10–20s** |
| Equilibrium gas | ~35% | **cao hơn** tùy khối lượng |
| ET vs BT | ET ≈ BT | **ET < BT** (hạt hấp thụ nhiệt) |
| BT pred MAE | 1–4°C | ~2–6°C |

> Tất cả tham số cần re-calibrate từ file log mẻ rang thật.

---

## 13. Mối quan hệ tổng hợp: Gas + Airflow → ET → BT

### 13.1 ET-BT gap theo giai đoạn vận hành

| Giai đoạn | Gas% | Air% | ET-BT avg | RoR_ET avg | RoR_BT avg | Nhận xét |
|-----------|------|------|-----------|-----------|-----------|---------|
| Khởi động | 65 | 0 | **+25.7°C** | 208 | 151 | ET dẫn xa — máy nguội, burner mạnh |
| Tăng nhiệt nhanh | 47 | 0 | -3.2°C | 21 | 34 | BT vượt ET — hạt (ko tải: lồng) đang hấp thụ nhiệt mạnh |
| Plateau | 35 | 0 | -11.3°C | 3.5 | 2.3 | BT > ET ~11°C — nhiệt tích lũy trong lồng |
| Air=18% bật | 35 | 18 | -7.2°C | 6.7 | 4.0 | ET tăng khi bật gió nhẹ, gap thu hẹp |
| Air=40% | 35 | 40 | -2.0°C | 3.8 | 1.8 | Gap gần 0 — airflow mạnh cân bằng nhiệt |
| Air=60% | 35 | 60 | **+1.4°C** | 0.5 | -1.7 | ET > BT — airflow quá mạnh, kéo nhiệt ra |
| Air tắt (spike) | 35 | 0 | -2.3°C | 11.0 | 17.8 | RoR_BT > RoR_ET — nhiệt tích lũy bùng phát |
| Cooling | 8 | 63-82 | **+8.0°C** | -3.3 | -4.1 | ET > BT khi làm nguội — khí thải lạnh hơn lồng |

**Quy luật ET-BT gap:**
- **ET-BT > 0**: Nhiệt đang thoát ra nhanh hơn tích lũy (airflow cao hoặc gas thấp)
- **ET-BT < 0**: Nhiệt đang tích lũy trong lồng (gas cao, airflow thấp)
- **ET-BT ≈ 0**: Trạng thái cân bằng nhiệt động

---

### 13.2 RoR_ET là early warning cho RoR_BT — nhưng khi nào?

**Ví dụ rõ nhất: Gas tăng 23→37% tại t=28:37**

| +Δt sau gas change | RoR_ET | RoR_BT | ET-BT gap |
|-------------------|--------|--------|-----------|
| +4s | 11.4 | 9.6 | 13.6 |
| +6s | **24.6** | 13.8 | 15.0 |
| +8s | **36.0** | 18.6 | 15.9 |
| +10s | **46.2** | 22.2 | 16.9 |
| +14s | 56.4 (đỉnh) | **27.0** | 18.5 |
| +16s | 51.6 (giảm) | **27.6** (đỉnh) | 19.0 |

→ **RoR_ET đạt đỉnh trước RoR_BT ~2-4 giây**  
→ **Khi RoR_ET bắt đầu giảm → RoR_BT đang tiếp tục tăng** — early warning cụ thể

---

### 13.3 Correlation RoR_ET(t) vs RoR_BT(t+lag)

Pearson correlation trong vùng gas=35% ổn định:

| Lag | Correlation |
|-----|------------|
| 0s | **0.767** ← cao nhất |
| 1s | 0.739 |
| 3s | 0.679 |
| 5s | 0.617 |
| 10s | 0.471 |
| 15s | 0.333 |

**Kết luận quan trọng:**  
> Correlation cao nhất tại **lag=0** (r=0.767) — RoR_ET và RoR_BT tương quan chặt **cùng thời điểm**, không phải RoR_ET dẫn trước RoR_BT.

Điều này có nghĩa:
- **RoR_ET không phải predictor tốt cho RoR_BT tương lai**
- RoR_ET và RoR_BT **phản ánh cùng trạng thái nhiệt** nhưng từ 2 góc khác nhau
- **ET-BT gap** là chỉ số có ý nghĩa hơn: gap tăng → nhiệt thoát nhanh hơn tích lũy → BT sắp chậm lại

---

### 13.4 Tác động kết hợp Gas + Airflow

| Gas thay đổi | Airflow | Tác động ET | Tác động BT | Độ phức tạp |
|-------------|---------|------------|------------|-------------|
| Tăng | Cố định thấp | ET tăng nhanh | BT tăng theo | Dự đoán được |
| Tăng | Cố định cao | ET tăng ít | BT tăng yếu hơn | Airflow "hút" bớt nhiệt |
| Cố định | Tăng mạnh | ET giảm/dừng | BT giảm/dừng | ET mất ý nghĩa làm feedforward |
| Giảm | Tăng đồng thời | ET giảm mạnh | BT giảm mạnh | **Nguy hiểm — RoR crash** |
| Giảm | Giảm đồng thời | ET tăng vọt | BT tăng đột ngột | **Spike không kiểm soát** |

**Nguyên tắc vận hành an toàn:**
- Không thay đổi Gas và Airflow đồng thời — chờ 15-20s sau mỗi thay đổi để đánh giá
- Khi tăng airflow mạnh (>20%) → giảm gas trước hoặc ngay sau để bù
- ET-BT gap > +15°C → dấu hiệu airflow quá cao hoặc gas quá thấp
- ET-BT gap < -15°C → dấu hiệu gas quá cao hoặc airflow quá thấp

---

## 14. Cần thu thập thêm

- [ ] File log mẻ rang thật có sản phẩm — để đo lag time thực tế
- [ ] Ít nhất 3 mẻ cùng profile để đánh giá repeatability
- [ ] Ghi chú khối lượng mẻ và loại sản phẩm
- [ ] Mẻ với các mức airflow khác nhau để calibrate điểm inflection khi có tải
