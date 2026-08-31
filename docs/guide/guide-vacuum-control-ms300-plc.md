# Vacuum Control đọc qua biến tần MS300 (biến tần Airflow)
### Tài liệu nguyên lý + hướng dẫn viết lại bằng Ladder / SCL trên PLC

> Nguồn: firmware OTL-06ALS đang chạy thật trên máy rang.
> File gốc: `include/Modbus_Master.h` (hàm `readUnder()`), `include/PID_Airflow.h`,
> `include/AnalogConfig.h`, `include/Config.h`.
> Ngày biên soạn: 2026-08-28.

---

## MỤC LỤC

1. Tóm tắt nguyên lý trong 10 dòng
2. Đường đi tín hiệu vật lý
3. Vì sao đọc áp hút qua biến tần thay vì AI của PLC
4. Phần cứng: đấu cảm biến vào ngõ ACI của MS300
5. Bản đồ thanh ghi Modbus đang dùng thật
6. Khung truyền Modbus RTU cụ thể (byte-by-byte)
7. Bước 1 — Đọc giá trị thô
8. Bước 2 — Lọc nhiễu (Kalman và bản rút gọn cho PLC)
9. Bước 3 — Quy đổi raw sang Pa
10. Bước 4 — Vòng điều khiển: Step Controller, KHÔNG phải PID
11. Bảng Feed-Forward và cơ chế snap
12. Factory Auto-Tune — quét đặc tuyến máy
13. Ngõ ra: từ Air% ra tốc độ quạt
14. Code SCL đầy đủ cho S7-1200 / S7-1500
15. Bản Ladder tương đương
16. An toàn, xử lý lỗi, tranh chấp quyền điều khiển
17. Bảng tham số tinh chỉnh
18. Checklist đưa vào vận hành
19. Bẫy thường gặp
20. Những điểm CHƯA kiểm chứng — phải tự xác nhận

---

## 1. Tóm tắt nguyên lý trong 10 dòng

1. Cảm biến áp suất chênh áp (áp hút / underpressure) **không nối vào PLC**, mà nối vào **ngõ analog ACI của biến tần MS300 điều khiển quạt hút**.
2. Biến tần MS300 số hoá tín hiệu ACI đó và **công bố nó ra một thanh ghi Modbus** dưới dạng số nguyên `0…10000` (tức 0.00…100.00 % thang đo).
3. PLC (hoặc firmware) làm **Modbus RTU Master trên RS485**, hỏi biến tần thanh ghi đó mỗi vòng quét truyền thông.
4. Giá trị thô đó **nhiễu** (quạt, rung, xoáy khí) nên phải **lọc** trước khi dùng — firmware dùng Kalman một tầng, PLC dùng IIR bậc 1 là đủ tương đương.
5. Sau lọc, **nội suy tuyến tính** raw `0…10000` về đơn vị kỹ thuật **Pa**, dùng 2 mốc `minPT` / `maxPT` do người vận hành khai báo trên HMI (chính là 2 đầu thang cảm biến).
6. Đó là **PV (process value)** của vòng điều khiển áp hút.
7. **SV (setpoint)** là áp hút mong muốn (Pa) do thợ rang đặt, ví dụ 120 Pa.
8. Cơ cấu chấp hành là **% tốc độ quạt hút (Air%)**, xuất ra biến tần bằng analog 0–10 V hoặc bằng lệnh tần số qua Modbus.
9. Bộ điều khiển **không phải PID cổ điển**: nó là **step controller** — sai lệch ngoài vùng chết ±3 Pa thì nhích Air% đúng **1 %** rồi nghỉ (cooldown 1.5–3 s tuỳ sai lệch lớn nhỏ). Lý do: quạt + đường ống là khâu quán tính lớn, phi tuyến, và độ phân giải cơ cấu chỉ 1 %.
10. Để không phải bò từ từ mỗi lần đổi setpoint, hệ có **bảng feed-forward (Pa → Air%)** tự học và một lần **auto-tune quét 0→100 %** để dựng sẵn bảng đó.

---

## 2. Đường đi tín hiệu vật lý

```
   Ống khói / buồng rang
          │  (áp suất âm, vài chục → vài trăm Pa)
          ▼
  ┌─────────────────────┐
  │ Cảm biến chênh áp   │   ngõ ra 4–20 mA (hoặc 0–10 V)
  │ (pressure transmit.)│
  └──────────┬──────────┘
             │  2 dây dòng
             ▼
  ┌──────────────────────────────────────────┐
  │  BIẾN TẦN DELTA MS300  (quạt hút / air)  │
  │                                          │
  │   ACI ●──── tín hiệu vào                 │
  │   ACM ●──── mass analog                  │
  │                                          │
  │   ADC nội bộ → thanh ghi monitor 0..10000│
  │                                          │
  │   RS485  SG+ / SG-  (Modbus RTU slave 5) │
  └──────────┬───────────────────────────────┘
             │  RS485 xoắn đôi có màn
             ▼
  ┌──────────────────────────────────────────┐
  │  PLC (Modbus RTU Master)                 │
  │   ├─ đọc raw ACI  → lọc → quy đổi Pa     │
  │   ├─ so với setpoint → step controller   │
  │   └─ xuất Air% ─┐                        │
  └─────────────────┼────────────────────────┘
                    │
        ┌───────────┴────────────┐
        │                        │
   AO 0–10 V vào AVI       hoặc  ghi tần số qua Modbus
   của chính MS300              (thanh ghi lệnh tần số)
        │                        │
        └───────────┬────────────┘
                    ▼
             Quạt hút chạy nhanh/chậm
                    │
                    ▼
             Áp hút thay đổi  ──►  vòng kín khép lại tại cảm biến
```

**Điểm mấu chốt để hiểu:** vòng kín này khép qua **chính con biến tần** — nó vừa là **thiết bị đo** (cầm cảm biến ở ngõ ACI) vừa là **cơ cấu chấp hành** (kéo quạt). PLC chỉ là bộ não ở giữa.

---

## 3. Vì sao đọc áp hút qua biến tần thay vì AI của PLC

| Tiêu chí | Đọc qua ACI biến tần (cách đang dùng) | Đọc bằng module AI của PLC |
|---|---|---|
| Chi phí | **0 đồng** — ngõ ACI có sẵn, không dùng thì bỏ phí | Tốn 1 module AI (SM 1231 / EM AM06…) |
| Số dây kéo về tủ | Cảm biến nằm ngay cạnh biến tần → dây analog ngắn | Phải kéo dây analog dài về tủ PLC |
| Chống nhiễu | Dây analog **ngắn**, đoạn dài về PLC là **RS485 số** → miễn nhiễm nhiễu | Dây analog dài chạy song song dây động lực → dễ ăn nhiễu |
| Tốc độ lấy mẫu | Bị giới hạn bởi chu kỳ Modbus (~50–200 ms) | Nhanh, đồng bộ theo chu kỳ quét PLC (ms) |
| Độ phân giải | 0…10000 → **0.01 %** thang, thừa dùng | 0…27648 (Siemens) |
| Rủi ro | **Mất Modbus là mất luôn PV** — đo và điều khiển chết cùng lúc | Mất Modbus vẫn còn đo được |
| Chẩn đoán | Xem được giá trị ngay trên màn hình biến tần | Phải vào PLC/HMI mới thấy |

> **Kết luận thiết kế:** cách này rất hợp lý về chi phí và chống nhiễu, nhưng phải **chấp nhận một điểm hỏng chung**: đứt RS485 thì vừa mất số đo vừa mất quyền lái quạt. Mục 16 nói cách xử lý.

---

## 4. Phần cứng: đấu cảm biến vào ngõ ACI của MS300

### 4.1 Đấu dây

| Chân MS300 | Nối tới | Ghi chú |
|---|---|---|
| `ACI` | Tín hiệu (+) của cảm biến | Ngõ analog nhận dòng/áp |
| `ACM` | Tín hiệu (−) / 0 V analog | Mass analog, **không** đấu chung mass động lực |
| `+10V` hoặc nguồn 24 V ngoài | Cấp nguồn cảm biến | Cảm biến 4–20 mA 2 dây thường cần 24 V |
| `SG+` `SG-` | RS485 về PLC | Xoắn đôi có màn, màn nối đất **một đầu** |

### 4.2 Cài biến tần

Trên MS300, ngõ ACI có **công tắc gạt phần cứng** chọn chế độ `0–10 V` hay `4–20 mA` — gạt sai thì đọc ra số vô nghĩa dù tham số đúng. Sau khi gạt đúng, còn phải:

* đặt **nhóm tham số analog input** cho ACI đúng dải tín hiệu và đúng chức năng. Nếu chỉ dùng để **đo và báo về Modbus**, tuyệt đối không để ACI thành nguồn lệnh tần số — nếu không quạt sẽ tự chạy theo áp suất, tranh quyền với PLC;
* đặt **truyền thông**: địa chỉ slave, baud, khung dữ liệu, giao thức **Modbus RTU**;
* nếu muốn PLC ghi tần số: đặt **nguồn lệnh tần số = truyền thông RS485**.

Trên máy đang chạy, thông số bus là:

```
Slave ID biến tần gió   : 5
Slave ID biến tần drum  : 4
Baud                    : 38400
Khung                   : 8-N-1  (xem mục 20 — cần xác nhận parity thực tế)
Giao thức               : Modbus RTU
```

*(Nguồn: `include/Config.h` — `AIR_INV_MODBUS_ID 5`, `DRUM_INV_MODBUS_ID 4`, `MACHINE_RS485_BAUD 38400`)*

### 4.3 Trường hợp đặc biệt: cảm biến cắm vào biến tần DRUM

Có máy (bản cacao) đấu cảm biến áp suất vào ngõ ACI của **biến tần lồng rang (slave 4)** chứ không phải biến tần gió. Firmware xử lý bằng cờ biên dịch:

```c
#define MACHINE_VACUUM_FROM_DRUM  0   // 0 = đọc slave 5 (gió), 1 = đọc slave 4 (drum)
```

Trên PLC, việc này chỉ là **đổi Slave ID trong khối Modbus master** — địa chỉ thanh ghi giữ nguyên vì hai biến tần cùng dòng.

---

## 5. Bản đồ thanh ghi Modbus đang dùng thật

| Chức năng | Địa chỉ DEC | Địa chỉ HEX | FC | Chiều | Ghi chú |
|---|---|---|---|---|---|
| **Giá trị analog ACI (áp hút)** | **8716** | **0x220C** | 03 | Đọc | **0…10000 = 0.00…100.00 %** — thanh ghi trung tâm của tài liệu này |
| Tần số ngõ ra hiện tại | 8451 | 0x2103 | 03 | Đọc | Giám sát tốc độ quạt / lồng |
| Lệnh tần số (ghi tốc độ) | 8193 | 0x2001 | 06 | Ghi | Thang 0.01 Hz: 5000 = 50.00 Hz |
| Tham số P08-00 | 2048 | 0x0800 | 03 | Đọc | Firmware chỉ **đọc giám sát** khối PID nội bộ biến tần |

*(Nguồn: `include/Config.h` — `AIR_INV_ACI_RAW_REGISTER 8716`, `AIR_INV_FREQ_READ_REGISTER 8451`, `DRUM_INV_FREQ_WRITE_REGISTER 8193`, `AIR_INV_PID_0800_REGISTER 2048`)*

### 5.1 Quy đổi địa chỉ sang Siemens — RẤT DỄ SAI

Thư viện `ModbusMaster` trên firmware gửi **thẳng** con số 8716 vào khung Modbus. Nhưng khối `MB_MASTER` / `Modbus_Master` của Siemens dùng **địa chỉ kiểu 4xxxx (1-based)**:

```
MB_DATA_ADDR = 40001 + (địa chỉ Modbus thật)
```

| Thanh ghi | Địa chỉ Modbus thật | `MB_DATA_ADDR` trên Siemens |
|---|---|---|
| ACI raw (áp hút) | 8716 | **48717** |
| Tần số ngõ ra | 8451 | **48452** |
| Lệnh tần số | 8193 | **48194** |

> Sai một đơn vị ở đây là đọc trúng thanh ghi bên cạnh và **ra số hợp lý nhưng sai ý nghĩa** — loại lỗi khó phát hiện nhất. Luôn kiểm chứng bằng cách bịt/hở ống cho áp suất đổi và xem con số có nhúc nhích đúng chiều không.

---

## 6. Khung truyền Modbus RTU cụ thể (byte-by-byte)

Đọc 1 thanh ghi ACI của biến tần gió (slave 5, địa chỉ 0x220C):

**PLC gửi đi (request):**

```
05      Slave ID = 5
03      Function code 03 = Read Holding Registers
22 0C   Địa chỉ đầu = 0x220C  (8716)
00 01   Số thanh ghi = 1
xx xx   CRC16 (low byte trước)
```

**Biến tần trả về (response), giả sử raw = 3500 (0x0DAC):**

```
05      Slave ID
03      Function code
02      Số byte dữ liệu = 2
0D AC   Giá trị = 3500  → 35.00 % thang đo
xx xx   CRC16
```

Thời gian một khung ở 38400 baud, 8-N-1 (10 bit/byte):

* Request 8 byte ≈ 2.1 ms, response 7 byte ≈ 1.8 ms
* Cộng thời gian xử lý của biến tần (thường 5–20 ms) và **khoảng lặng 3.5 ký tự** giữa 2 khung (≈ 0.9 ms)
* → Thực tế mỗi lần đọc tốn khoảng **10–25 ms**

Firmware chèn `delay(1)` trước và sau mỗi giao dịch để giữ khoảng lặng khung RS485 (trước đây 5 ms, siết xuống 1 ms ngày 2026-07-23 để giảm chu kỳ vòng quét).

**Trên PLC:** không được gọi `MB_MASTER` liên tiếp cho nhiều slave trong cùng một chu kỳ mà không chờ `DONE`/`ERROR`. Phải làm **máy trạng thái tuần tự** (xem mục 14.4).

---

## 7. Bước 1 — Đọc giá trị thô

```c
result = nodeVacuum.readHoldingRegisters(AIR_INV_ACI_RAW_REGISTER, 1);
if (result == nodeVacuum.ku8MBSuccess) {
    raw_Diff_Air = nodeVacuum.getResponseBuffer(0);   // 0..10000
}
```

Ý nghĩa con số:

| raw | % thang đo | Ý nghĩa với cảm biến 4–20 mA |
|---|---|---|
| 0 | 0.00 % | 4 mA — đầu thang dưới |
| 2500 | 25.00 % | 8 mA |
| 5000 | 50.00 % | 12 mA — giữa thang |
| 10000 | 100.00 % | 20 mA — đầu thang trên |

**Cảnh báo quan trọng:** nếu cảm biến chọn chế độ **4–20 mA** thì **đứt dây = 0 mA**, và biến tần vẫn báo raw ≈ 0 — trùng với "áp suất đầu thang dưới hợp lệ". Nên cấu hình biến tần để phân biệt được **0 mA (lỗi)** với **4 mA (giá trị hợp lệ nhỏ nhất)**, hoặc ít nhất báo lỗi khi raw dính 0 quá lâu **trong lúc quạt đang chạy** (mục 16).

---

## 8. Bước 2 — Lọc nhiễu (Kalman và bản rút gọn cho PLC)

### 8.1 Vì sao phải lọc

Áp hút đo trong ống khói có quạt ly tâm thổi qua thì **dao động vài chục Pa** mỗi giây do xoáy khí và rung cơ khí. Nếu đưa thẳng vào bộ điều khiển, Air% sẽ nhảy loạn (limit cycle), gây rung cơ cấu và mài mòn.

### 8.2 Firmware làm gì

Firmware dùng **một tầng** Kalman vô hướng (`SimpleKalmanFilter`), tham số:

```
e_mea = 50    // sai số phép đo
e_est = 50    // sai số ước lượng ban đầu
q     = 1.0   // nhiễu quá trình
```

Thuật toán mỗi chu kỳ:

```
p     := p + q                    // độ bất định tăng theo thời gian
K     := p / (p + e_mea)          // Kalman gain
est   := est + K * (raw - est)    // cập nhật ước lượng
p     := (1 - K) * p              // độ bất định giảm sau khi có phép đo
```

### 8.3 Điều quan trọng nhất cho người viết PLC

Với 3 tham số cố định trên, **Kalman gain K hội tụ về một hằng số**. Giải phương trình dừng:

đặt `s = p + q`, ta có `K = s/(s+50)` và `p = (1−K)·s = 50s/(s+50)`, mà `p = s − q = s − 1`, suy ra

```
s² − s − 50 = 0   →   s = 7.589   →   K∞ = 7.589 / 57.589 ≈ 0.132
```

Nghĩa là **sau vài chục chu kỳ, bộ lọc Kalman này y hệt một bộ lọc IIR bậc 1 (EMA) với hệ số α ≈ 0.13**:

```
filtered := filtered + 0.13 * (raw − filtered)
```

Đối chiếu với **bộ tham số cũ** (`e_mea=200, e_est=5, q=0.1`): `s² − 0.1s − 20 = 0 → s = 4.52 → K∞ ≈ 0.022` — chậm hơn khoảng **6 lần**, đúng như ghi chú trong code rằng bản cũ "phản hồi rất chậm".

> **Khuyến nghị cho PLC:** đừng cố bê Kalman vào SCL. **Dùng thẳng IIR bậc 1 với α = 0.13** — kết quả ở trạng thái xác lập là như nhau, code ngắn hơn, dễ giải thích cho người bảo trì, và không có biến trạng thái `p` để mà trôi.

### 8.4 Chọn α theo chu kỳ lấy mẫu

Hằng số thời gian của bộ lọc:

```
τ ≈ T_mẫu / α
```

| Chu kỳ đọc `T_mẫu` | α = 0.13 → τ | Nhận xét |
|---|---|---|
| 100 ms | ≈ 0.77 s | Giống firmware hiện tại |
| 200 ms | ≈ 1.5 s | Vẫn chấp nhận được |
| 500 ms | ≈ 3.8 s | Quá chậm — tăng α lên ~0.3 |

Muốn chọn α cho một τ mong muốn:

```
α = T_mẫu / τ        (đúng khi α ≤ 0.3)
```

Ví dụ PLC đọc mỗi 200 ms, muốn τ = 1 s → α = 0.2.

### 8.5 Lọc thêm gai đơn lẻ (khuyến nghị bổ sung)

Firmware **không có** lọc trung vị. Trên PLC nên thêm **median-of-3** trước IIR — rất rẻ và diệt sạch gai đơn do lỗi khung Modbus hoặc xung nhiễu:

```
median3(a,b,c) = a + b + c − max(a,b,c) − min(a,b,c)
```

---

## 9. Bước 3 — Quy đổi raw sang Pa

```c
Diff_Air = minPT_R + (filtered / 10000.0) * (maxPT_R - minPT_R);
```

| Ký hiệu | Nguồn | Ý nghĩa |
|---|---|---|
| `minPT_R` | HMI, thanh ghi 49 | Áp suất ứng với **đầu thang dưới** của cảm biến |
| `maxPT_R` | HMI, thanh ghi 50 | Áp suất ứng với **đầu thang trên** |
| `filtered` | sau bộ lọc | 0…10000 |
| `Diff_Air` | kết quả | **Pa** — chính là PV |

### Ví dụ số, cảm biến ±500 Pa

| filtered | Diff_Air |
|---|---|
| 0 | −500 Pa |
| 2500 | −250 Pa |
| 5000 | 0 Pa |
| 7500 | +250 Pa |
| 10000 | +500 Pa |

### Ví dụ số, cảm biến 0…1000 Pa (`minPT=0`, `maxPT=1000`)

| filtered | Diff_Air |
|---|---|
| 0 | 0 Pa |
| 1200 | 120 Pa |
| 5000 | 500 Pa |

### Lưu ý dấu

Trong firmware, `Diff_Air` được coi là **số dương** khi có áp hút (setpoint kiểu 120 Pa; factory-tune chỉ ghi nhận điểm có `avgPa > 2.0`). Nghĩa là **cảm biến đã được đấu/khai báo sao cho hút mạnh → số lớn**. Nếu trên PLC bạn khai `minPT = −500`, `maxPT = 0` thì mọi so sánh trong bộ điều khiển sẽ đảo chiều — **hãy giữ nguyên quy ước "hút mạnh = số Pa lớn hơn"** để bê nguyên logic bên dưới.

### Chú ý kiểu dữ liệu trên PLC

* Kết quả trung gian **phải là REAL**. Nếu làm số nguyên: `(filtered / 10000) * range` sẽ ra 0 với mọi filtered < 10000.
* Đọc từ Modbus là `WORD`. Nếu thang có giá trị âm thì phải diễn giải là `INT` (có dấu) — riêng thanh ghi ACI 0…10000 luôn dương nên `WORD → INT` an toàn.
* Nên **kẹp** `filtered` vào `[0, 10000]` trước khi nội suy, đề phòng khung lỗi.

---

## 10. Bước 4 — Vòng điều khiển: Step Controller, KHÔNG phải PID

### 10.1 Vì sao không dùng PID kinh điển

| Đặc điểm đối tượng | Hệ quả |
|---|---|
| Quạt + ống + lồng rang có **quán tính lớn**, có trễ vận chuyển | Thành phần D vô dụng, chỉ khuếch đại nhiễu áp |
| Quan hệ Air% → Pa **phi tuyến mạnh** (gần bậc hai) | Một bộ Kp cố định thì vùng gió thấp lờ đờ, vùng gió cao dao động |
| Cơ cấu chỉ nhận **số nguyên %** | Đầu ra PID lẻ 47.3 % vẫn ra 47 % — tích phân sẽ dồn (windup) |
| Setpoint đổi theo mốc rang, không đổi liên tục | Cần hội tụ nhanh sau bậc nhảy hơn là bám sát tuyệt đối |

→ Giải pháp: **feed-forward (bảng đặc tuyến) lo phần thô + step controller lo phần tinh.**

### 10.2 Luật điều khiển

```
error = setpoint − Diff_Air        (Pa)

|error| ≤ 3 Pa      →  KHÔNG làm gì (vùng chết)
error > +3 Pa       →  hút chưa đủ  →  Air% += 1
error < −3 Pa       →  hút quá mạnh →  Air% −= 1

Sau mỗi lần nhích: KHOÁ lại một khoảng cooldown, không nhích tiếp.
```

### 10.3 Cooldown động — chi tiết dễ bỏ sót nhất

Cooldown **không cố định**, mà **nội suy tuyến tính theo độ lớn sai lệch**:

```
absErr   = min(|error|, 30)                       // kẹp ở ngưỡng "xa"
t        = (absErr − 3) / (30 − 3)                // 0…1
cooldown = 3000 − t * (3000 − 1500)   [ms]
```

| \|error\| | t | cooldown | Tốc độ nhích |
|---|---|---|---|
| 3 Pa (vừa ra khỏi vùng chết) | 0.00 | 3000 ms | 1 %/3 s — rón rén |
| 10 Pa | 0.26 | 2611 ms | |
| 20 Pa | 0.63 | 2056 ms | |
| ≥ 30 Pa (xa) | 1.00 | 1500 ms | 1 %/1.5 s — nhanh gấp đôi |

Ý nghĩa vật lý: **xa thì đi nhanh, gần thì đi chậm** — đây chính là vai trò của thành phần P trong PID, nhưng thực hiện bằng **tần suất bước** thay vì **biên độ bước**. Cách này miễn nhiễm với phi tuyến của quạt, vì biên độ bước luôn là 1 %, không phụ thuộc gain.

Tốc độ tối đa của hệ: **1 %/1.5 s** → đi hết dải 0→100 % mất 150 s. Đây là **giới hạn cứng của thiết kế** — nếu quy trình cần đổi gió nhanh hơn thì phải dựa vào cơ chế snap (mục 11), không phải hạ cooldown.

### 10.4 Vùng chết ±3 Pa

Hằng số `AIR_DEADBAND = 3.0f`.

> **Bẫy đã có thật trong code:** phần chú thích đầu file `PID_Airflow.h` vẫn ghi "±5 Pa" — đó là chú thích cũ chưa cập nhật. **Giá trị đúng đang chạy là ±3 Pa.** Khi chép sang PLC, lấy theo hằng số, không lấy theo chú thích.

Vùng chết quá nhỏ → cơ cấu rung liên tục; quá lớn → sai số tĩnh lớn. 3 Pa trên setpoint 120 Pa là **±2.5 %**, hợp lý.

---

## 11. Bảng Feed-Forward và cơ chế snap

### 11.1 Bảng FF là gì

Một bảng tối đa 60 dòng, mỗi dòng:

```
{ sp : áp suất Pa ,  air : Air% tương ứng ,  count : số lần đã học }
```

Nghĩa là: *"muốn 120 Pa thì mở gió khoảng 43 %"*. Bảng lưu trên thẻ SD ở `/pid_ff.txt`; **trên PLC nên lưu vào DB retentive** hoặc recipe.

Tra bảng:

* Tìm dòng có `|sp_bảng − sp_cần|` nhỏ nhất và **≤ 3 Pa** → lấy `air` của dòng đó.
* Không có dòng nào khớp → ước lượng tuyến tính dự phòng: `air = sp * 100/120`, kẹp trong 0…100.

### 11.2 Snap — nhảy tắt khi đổi setpoint

Khi setpoint **thay đổi**, gọi `pidAirflowReset()`:

```
delta = |sp_mới − sp_cũ|

delta ≤ 30 Pa   →  KHÔNG snap, để step controller bò từ từ
delta > 30 Pa   →  snap:
     nếu sp tăng: Air% mới = FF(sp_mới) − snapBuffer,
                  nhưng kẹp trong [Air%_hiện tại , Air%_hiện tại + 20]
     nếu sp giảm: Air% mới = FF(sp_mới) + snapBuffer,
                  nhưng kẹp trong [0 , Air%_hiện tại]
```

Ba ý đồ thiết kế cần hiểu rõ khi viết lại:

1. **Cố ý snap "hụt" một khoảng `snapBuffer`** thay vì nhảy đúng giá trị bảng. Lý do: bảng học được có sai số, nhảy đúng dễ vọt lố (overshoot). Nhảy hụt rồi để step controller bù nốt ~20 Pa cuối bằng những bước 1 % → **không bao giờ vọt lố**.
2. **Kẹp bước nhảy ≤ 20 %** mỗi lần đổi setpoint — chống sốc cơ khí cho quạt và đường ống.
3. **Hướng snap quyết định bằng setpoint mới so với setpoint cũ**, *không* bằng Air% hiện tại. Code có ghi rõ lý do: Air% hiện tại có thể đang lệch khỏi bảng, dùng nó làm mốc sẽ **snap sai chiều**.

`snapBuffer` mặc định 15 %, và được **tính lại tự động sau auto-tune** (mục 12.3), kẹp trong [8, 25] %.

### 11.3 Tự học khi ổn định

Mỗi giây, nếu đang bật điều khiển áp hút:

```
nếu |Diff_Air − setpoint| ≤ 3 Pa  →  stableTimer++
    khi stableTimer == 10  →  ghi vào bảng FF: (setpoint, Air% hiện tại)
    mỗi 60 s và bảng có thay đổi → lưu xuống SD
ngược lại → stableTimer = 0
```

Cách cập nhật một dòng đã có:

```
drift = |air_trong_bảng − air_mới|

drift ≥ 3 %   →  hệ thống đã đổi (lưới lọc bẩn, nhiệt độ khác…)
                 → học lại nhanh: air = (air_cũ + air_mới)/2 ; count = 2
drift < 3 %   →  trung bình động có trọng số:
                 cnt = min(count, 30)
                 air = (air*cnt + air_mới)/(cnt+1) ; count = cnt+1
```

`min(count, 30)` là để bảng **không bao giờ đóng băng** — dù đã học 500 lần, một giá trị mới vẫn có trọng số 1/31, hệ vẫn theo kịp máy khi bẩn dần theo thời gian.

---

## 12. Factory Auto-Tune — quét đặc tuyến máy

### 12.1 Quy trình

Người vận hành bấm nút Tune trên HMI:

```
1. Hạ Air% về 0 ngay
2. Chờ 15 s (FT_WARMUP_SEC) cho áp suất về nền
3. Xoá sạch bảng FF
4. Quét Air% = 0, 2, 4, ... 100  (bước 2 % → 51 điểm)
   Mỗi điểm giữ 3 s:
      giây 0    : đặt Air%, xoá bộ tích luỹ
      giây 1    : chờ ổn định, KHÔNG lấy mẫu
      giây 2..3 : lấy mẫu Pa, cộng dồn
   Hết 3 s: avgPa = tổng/số mẫu
      nếu avgPa > 2 Pa → ghi vào bảng: (avgPa, Air%)
   Cập nhật % tiến trình lên HMI
5. Xong: tính lại snapBuffer, lưu SD, tự tắt nút Tune trên HMI, trả Air% về 50 %
```

Tổng thời gian: 15 s + 51 × 3 s ≈ **2 phút 48 giây**.

### 12.2 Chi tiết dễ sai

* Bảng có **60 chỗ**, quét ra **51 điểm** — vừa đủ. Nếu ai đổi bước quét từ 2 % xuống 1 % thì thành 101 điểm, **tràn bảng**. Code đã có cờ `ffTableFull` để báo lỗi thay vì im lặng bỏ qua — bản PLC **phải giữ cảnh báo này**, vì tràn bảng làm mất hẳn vùng gió cao mà giao diện vẫn báo "tune xong 100 %".
* Bỏ qua điểm có `avgPa ≤ 2 Pa`: ở gió thấp cảm biến chưa nhúc nhích, ghi vào chỉ làm bẩn bảng.
* Bảng được **lập chỉ mục theo Pa đo được**, không theo Air% — vì tra cứu luôn đi theo chiều "cần bao nhiêu Pa → mở bao nhiêu %".

### 12.3 Tính snapBuffer sau tune

```
airRange = max(air) − min(air)
paRange  = max(Pa)  − min(Pa)
bỏ qua nếu airRange < 5 % hoặc paRange < 10 Pa (dữ liệu vô nghĩa)

sensitivity = paRange / airRange        [Pa mỗi 1 %]
snapBuffer  = 20 / sensitivity          [%]  ← để step controller bù đúng ~20 Pa
snapBuffer  = clamp(snapBuffer, 8, 25)
```

Ví dụ máy có paRange = 300 Pa trên airRange = 90 % → sensitivity = 3.33 Pa/% → snapBuffer = 6 % → bị kẹp lên **8 %**.

---

## 13. Ngõ ra: từ Air% ra tốc độ quạt

### 13.1 Cách firmware làm — analog

```c
mapDAC_airflow = map(airflowPercent, 0, 100, 0, 4095);
dac_airflow.setVoltage(mapDAC_airflow, false);   // MCP4725, I2C 0x60
```

→ DAC 12 bit ra điện áp analog đưa vào ngõ **AVI** của biến tần; biến tần cài "nguồn lệnh tần số = AVI".

### 13.2 Cách nên làm trên PLC — chọn 1 trong 2

**Phương án A — Analog (giống hiện trạng):**

* Module AO của PLC → AVI của MS300
* Ưu: điều khiển liên tục, không phụ thuộc chu kỳ Modbus, **quạt vẫn chạy nếu RS485 đứt**
* Nhược: tốn 1 kênh AO, có sai số/trôi analog
* Quy đổi Siemens: `Air% 0…100` → `0…27648` (word AO) → `0…10 V`

**Phương án B — Ghi tần số qua Modbus:**

* Ghi FC06 vào thanh ghi lệnh tần số `0x2001` (`MB_DATA_ADDR 48194`), thang **0.01 Hz** (5000 = 50.00 Hz)
* Ưu: không tốn dây analog, độ phân giải 0.01 Hz, đọc lại xác nhận được
* Nhược: **RS485 đứt là mất luôn quyền lái quạt** — bắt buộc phải cài **timeout truyền thông trong biến tần** để nó tự dừng hoặc giữ tần số an toàn

Firmware đang dùng phương án B cho **biến tần lồng rang**:

```c
drumHz = map(drumPercent, 0, 100, 3000, 5000);   // 30.00 → 50.00 Hz
nodeDrum.writeSingleRegister(8193, drumHz);
```

Chú ý: **0 % không phải 0 Hz mà là 30 Hz** — vì lồng rang có tốc độ tối thiểu. Với quạt gió, hãy tự quyết dải `Hz_min…Hz_max` theo máy, **đừng bê thang 3000–5000 sang**.

### 13.3 Giới hạn tốc độ đổi (khuyến nghị thêm)

Firmware chỉ đổi 1 %/1.5 s nên không cần ramp. Nếu bản PLC cho phép nhảy snap 20 %, nên chèn **ramp giới hạn** ở đầu ra, ví dụ tối đa 20 %/giây, để không gây sốc dòng khởi động.

---

## 14. Code SCL đầy đủ cho S7-1200 / S7-1500

### 14.1 Kiểu dữ liệu tham số — `typeVacCfg`

```pascal
TYPE "typeVacCfg"
STRUCT
    // --- Thang đo cảm biến (khai báo từ HMI) ---
    minPT           : REAL := -500.0;   // Pa ứng với raw = 0
    maxPT           : REAL := 500.0;    // Pa ứng với raw = 10000

    // --- Lọc ---
    filtAlpha       : REAL := 0.13;     // IIR bậc 1, tương đương Kalman firmware
    useMedian3      : BOOL := TRUE;     // lọc trung vị 3 mẫu trước IIR

    // --- Step controller ---
    deadband        : REAL := 3.0;      // Pa   (KHÔNG phải 5, xem mục 10.4)
    stepSize        : REAL := 1.0;      // %
    coolNear_ms     : DINT := 3000;     // sai lệch nhỏ → chậm
    coolFar_ms      : DINT := 1500;     // sai lệch lớn → nhanh
    coolFarErr      : REAL := 30.0;     // Pa, ngưỡng "xa"
    airMin          : REAL := 0.0;
    airMax          : REAL := 100.0;

    // --- Feed-forward / snap ---
    snapBuffer      : REAL := 15.0;     // % nhảy hụt cố ý
    snapDeltaMin    : REAL := 30.0;     // Pa — dưới ngưỡng này thì không snap
    snapMaxJump     : REAL := 20.0;     // % — trần một lần nhảy
    ffMatchPa       : REAL := 3.0;      // 2 setpoint cách ≤ 3 Pa coi là một
    ffDriftPct      : REAL := 3.0;      // lệch ≥ 3 % thì học lại nhanh
    stableSecToLearn: INT  := 10;       // ổn định 10 s mới ghi bảng

    // --- An toàn ---
    commFailMax     : INT  := 5;        // số lần đọc lỗi liên tiếp → FAULT
    rawStuckSec     : INT  := 20;       // raw đứng yên bao lâu thì nghi hỏng cảm biến
    airOnFault      : REAL := 60.0;     // % gió giữ khi mất tín hiệu (fail-safe)
END_STRUCT
END_TYPE
```

### 14.2 FB đọc và quy đổi — `FB_VacRead`

```pascal
FUNCTION_BLOCK "FB_VacRead"
{ S7_Optimized_Access := 'TRUE' }
VAR_INPUT
    rawWord   : WORD;    // giá trị đọc từ Modbus, thanh ghi 8716
    rawValid  : BOOL;    // TRUE khi giao dịch Modbus vừa rồi thành công
    cfg       : "typeVacCfg";
END_VAR
VAR_OUTPUT
    pv_Pa     : REAL;    // áp hút đã lọc, đơn vị Pa → PV của vòng điều khiển
    rawFilt   : REAL;    // 0..10000 sau lọc (để chẩn đoán)
    sensorOK  : BOOL;
END_VAR
VAR
    m1, m2, m3 : REAL;   // 3 mẫu gần nhất cho median
    filtInit   : BOOL;
    filt       : REAL;
    failCnt    : INT;
    stuckTmr   : TON_TIME;
    lastRaw    : REAL;
END_VAR
VAR_TEMP
    rawR   : REAL;
    med    : REAL;
    mx, mn : REAL;
END_VAR

BEGIN
    // ---------- 1. Đếm lỗi truyền thông ----------
    IF NOT #rawValid THEN
        IF #failCnt < 32767 THEN #failCnt := #failCnt + 1; END_IF;
        // KHÔNG cập nhật pv — giữ giá trị cuối cùng còn tin được
        #sensorOK := (#failCnt < #cfg.commFailMax);
        RETURN;
    END_IF;
    #failCnt := 0;

    // ---------- 2. Kẹp dải hợp lệ ----------
    #rawR := WORD_TO_REAL(#rawWord);
    IF #rawR < 0.0     THEN #rawR := 0.0;     END_IF;
    IF #rawR > 10000.0 THEN #rawR := 10000.0; END_IF;

    // ---------- 3. Median-of-3 (diệt gai đơn) ----------
    #m3 := #m2;  #m2 := #m1;  #m1 := #rawR;
    IF #cfg.useMedian3 THEN
        #mx := #m1;
        IF #m2 > #mx THEN #mx := #m2; END_IF;
        IF #m3 > #mx THEN #mx := #m3; END_IF;
        #mn := #m1;
        IF #m2 < #mn THEN #mn := #m2; END_IF;
        IF #m3 < #mn THEN #mn := #m3; END_IF;
        #med := #m1 + #m2 + #m3 - #mx - #mn;
    ELSE
        #med := #rawR;
    END_IF;

    // ---------- 4. IIR bậc 1  (tương đương Kalman K∞ ≈ 0.13) ----------
    IF NOT #filtInit THEN
        #filt     := #med;          // nạp thẳng mẫu đầu, tránh vọt từ 0
        #filtInit := TRUE;
    ELSE
        #filt := #filt + #cfg.filtAlpha * (#med - #filt);
    END_IF;
    #rawFilt := #filt;

    // ---------- 5. Nội suy sang Pa ----------
    #pv_Pa := #cfg.minPT + (#filt / 10000.0) * (#cfg.maxPT - #cfg.minPT);

    // ---------- 6. Phát hiện cảm biến chết (raw đứng im tuyệt đối) ----------
    #stuckTmr(IN := (ABS(#rawR - #lastRaw) < 1.0),
              PT := INT_TO_TIME(#cfg.rawStuckSec) * 1000);
    IF ABS(#rawR - #lastRaw) >= 1.0 THEN #lastRaw := #rawR; END_IF;

    #sensorOK := NOT #stuckTmr.Q;
END_FUNCTION_BLOCK
```

### 14.3 FB điều khiển — `FB_VacCtrl`

```pascal
FUNCTION_BLOCK "FB_VacCtrl"
VAR_INPUT
    enable    : BOOL;    // cờ bật điều khiển áp hút (ứng với vacuumSetFlag)
    sp_Pa     : REAL;    // setpoint áp hút
    pv_Pa     : REAL;    // từ FB_VacRead
    sensorOK  : BOOL;
    tick_1s   : BOOL;    // xung 1 giây (dùng cho phần tự học)
    nowMs     : DINT;    // đồng hồ ms tự do của hệ thống
    cfg       : "typeVacCfg";
END_VAR
VAR_IN_OUT
    ffSp   : ARRAY[0..59] OF REAL;   // bảng FF — ĐỂ TRONG DB RETENTIVE
    ffAir  : ARRAY[0..59] OF REAL;
    ffCnt  : ARRAY[0..59] OF INT;
    ffSize : INT;
END_VAR
VAR_OUTPUT
    airPct   : REAL;     // 0..100 → đưa ra AO hoặc ghi tần số
    inBand   : BOOL;     // đang trong vùng chết → coi như đạt
    fault    : BOOL;
    tableFull: BOOL;     // bảng FF đầy — PHẢI báo lên HMI
END_VAR
VAR
    airCur      : REAL := 50.0;
    prevSp      : REAL := -1.0;
    coolUntil   : DINT;              // mốc thời gian hết cooldown (ms)
    stableSec   : INT;
    firstRun    : BOOL := TRUE;
END_VAR
VAR_TEMP
    err, absErr, t     : REAL;
    coolMs             : DINT;
    target, snapped, d : REAL;
    drift, cntR        : REAL;
    i, best            : INT;
    bestDist, dist     : REAL;
END_VAR

BEGIN
    // ================= 0. Trạng thái lỗi / tắt =================
    #fault := NOT #sensorOK;
    IF #fault THEN
        #airPct := #cfg.airOnFault;        // fail-safe: giữ gió an toàn, KHÔNG về 0
        #inBand := FALSE;
        RETURN;
    END_IF;

    IF NOT #enable THEN
        #prevSp := -1.0;                   // để lần bật lại sẽ snap
        RETURN;                            // Air% do khối khác (tay/preheat) lái
    END_IF;

    // ================= 1. Setpoint đổi → snap =================
    IF (#sp_Pa <> #prevSp) OR #firstRun THEN
        #firstRun := FALSE;

        // --- tra bảng FF ---
        #best := -1;  #bestDist := #cfg.ffMatchPa;
        FOR #i := 0 TO #ffSize - 1 DO
            #dist := ABS(#ffSp[#i] - #sp_Pa);
            IF #dist <= #bestDist THEN #bestDist := #dist; #best := #i; END_IF;
        END_FOR;

        IF #best >= 0 THEN
            #target := #ffAir[#best];
        ELSE
            #target := #sp_Pa * (100.0 / 120.0);      // ước lượng dự phòng
        END_IF;
        #target := LIMIT(MN := #cfg.airMin, IN := #target, MX := #cfg.airMax);

        // --- quyết định có snap không ---
        #snapped := #airCur;
        IF #prevSp >= 0.0 THEN #d := ABS(#sp_Pa - #prevSp); ELSE #d := 999.0; END_IF;

        IF #d > #cfg.snapDeltaMin THEN
            IF #sp_Pa > #prevSp THEN
                // Cần hút mạnh hơn → tăng gió, nhảy HỤT snapBuffer
                #snapped := #target - #cfg.snapBuffer;
                IF #snapped < #airCur THEN #snapped := #airCur; END_IF;
                IF #snapped > #airCur + #cfg.snapMaxJump
                   THEN #snapped := #airCur + #cfg.snapMaxJump; END_IF;
            ELSE
                // Cần hút nhẹ hơn → giảm gió, nhảy HỤT về phía trên
                #snapped := #target + #cfg.snapBuffer;
                IF #snapped > #airCur THEN #snapped := #airCur; END_IF;
                IF #snapped < #cfg.airMin THEN #snapped := #cfg.airMin; END_IF;
            END_IF;
        END_IF;

        #prevSp    := #sp_Pa;
        #airCur    := LIMIT(MN := #cfg.airMin, IN := #snapped, MX := #cfg.airMax);
        #stableSec := 0;
    END_IF;

    // ================= 2. Step controller + cooldown động =================
    #err    := #sp_Pa - #pv_Pa;
    #inBand := (ABS(#err) <= #cfg.deadband);

    IF (NOT #inBand) AND (#nowMs >= #coolUntil) THEN
        #absErr := ABS(#err);
        IF #absErr > #cfg.coolFarErr THEN #absErr := #cfg.coolFarErr; END_IF;
        #t      := (#absErr - #cfg.deadband) / (#cfg.coolFarErr - #cfg.deadband);
        #coolMs := #cfg.coolNear_ms
                 - REAL_TO_DINT(#t * DINT_TO_REAL(#cfg.coolNear_ms - #cfg.coolFar_ms));

        IF #err > 0.0 THEN
            #airCur := #airCur + #cfg.stepSize;      // hút yếu → thêm gió
        ELSE
            #airCur := #airCur - #cfg.stepSize;      // hút mạnh → bớt gió
        END_IF;
        #airCur    := LIMIT(MN := #cfg.airMin, IN := #airCur, MX := #cfg.airMax);
        #coolUntil := #nowMs + #coolMs;
    END_IF;

    #airPct := #airCur;

    // ================= 3. Tự học bảng FF khi ổn định =================
    IF #tick_1s THEN
        IF #inBand THEN
            #stableSec := #stableSec + 1;
            IF #stableSec = #cfg.stableSecToLearn THEN
                // --- tìm dòng khớp ---
                #best := -1;  #bestDist := #cfg.ffMatchPa;
                FOR #i := 0 TO #ffSize - 1 DO
                    #dist := ABS(#ffSp[#i] - #sp_Pa);
                    IF #dist <= #bestDist THEN #bestDist := #dist; #best := #i; END_IF;
                END_FOR;

                IF #best < 0 THEN
                    IF #ffSize < 60 THEN                    // thêm dòng mới
                        #ffSp[#ffSize]  := #sp_Pa;
                        #ffAir[#ffSize] := #airCur;
                        #ffCnt[#ffSize] := 1;
                        #ffSize := #ffSize + 1;
                    ELSE
                        #tableFull := TRUE;   // BẢNG ĐẦY → báo HMI, đừng im lặng bỏ qua
                    END_IF;
                ELSE
                    #drift := ABS(#ffAir[#best] - #airCur);
                    IF #drift >= #cfg.ffDriftPct THEN
                        #ffAir[#best] := (#ffAir[#best] + #airCur) / 2.0;
                        #ffCnt[#best] := 2;
                    ELSE
                        IF #ffCnt[#best] > 30 THEN #ffCnt[#best] := 30; END_IF;
                        #cntR := INT_TO_REAL(#ffCnt[#best]);
                        #ffAir[#best] := (#ffAir[#best] * #cntR + #airCur) / (#cntR + 1.0);
                        #ffCnt[#best] := #ffCnt[#best] + 1;
                    END_IF;
                    #ffSp[#best] := (#ffSp[#best] + #sp_Pa) / 2.0;
                END_IF;
            END_IF;
        ELSE
            #stableSec := 0;
        END_IF;
    END_IF;
END_FUNCTION_BLOCK
```

### 14.4 Máy trạng thái Modbus — bắt buộc phải tuần tự

`MB_MASTER` chỉ phục vụ **một giao dịch tại một thời điểm** trên cùng cổng. Với nhiều slave (BT, ET, biến tần), phải xoay vòng:

```pascal
CASE #mbStep OF
    0:  // đọc ACI biến tần gió (áp hút)
        "MB_MASTER"(REQ := #req, MB_ADDR := 5, MODE := 0,
                    DATA_ADDR := 48717, DATA_LEN := 1,
                    DATA_PTR := #bufVac, DONE => #done, ERROR => #errB);
        IF #done THEN
            #rawVac := #bufVac[0];  #rawValid := TRUE;
            #mbStep := 1;  #req := FALSE;
        ELSIF #errB THEN
            #rawValid := FALSE;
            #mbStep := 1;  #req := FALSE;
        END_IF;

    1:  // ghi tần số quạt (nếu dùng phương án B)
        // "MB_MASTER"(... MODE := 1, DATA_ADDR := 48194 ...)
        ;
    2:  // đọc tần số ngõ ra để giám sát
        ;
END_CASE;
```

Nhịp thực tế: mỗi giao dịch ~10–25 ms → vòng 3 giao dịch ~50–75 ms → **chu kỳ cập nhật PV khoảng 50–100 ms**, trùng với firmware. Với chu kỳ đó, `filtAlpha = 0.13` là đúng.

> Nếu bạn để chu kỳ đọc chậm hơn hẳn (ví dụ 500 ms) thì **phải tăng `filtAlpha`** lên ~0.3, nếu không bộ lọc sẽ trễ tới 4 giây và step controller sẽ dao động vì "nhìn thấy quá khứ".

---

## 15. Bản Ladder tương đương

Cho người quen LAD hơn SCL. Phần lọc và nội suy nên gói vào một FC/FB dùng lệnh toán học; phần logic bước thì LAD rất tự nhiên:

```
NETWORK 1 — Đọc Modbus xong, hợp lệ
  |--[ MB_DONE ]--[ /MB_ERROR ]------------------------( MOVE  bufVac → rawVac )
  |                                                    ( S     rawValid       )

NETWORK 2 — Nội suy Pa   (dùng CALCULATE)
  |--[ rawValid ]---------------------------------( CALC )
  |     OUT := minPT + (rawFilt / 10000.0) * (maxPT - minPT)

NETWORK 3 — Vùng chết
  |--[ ABS(sp - pv) <= 3.0 ]----------------------------------------( inBand )

NETWORK 4 — Cho phép nhích (hết cooldown, ngoài vùng chết, đang bật, không lỗi)
  |--[ enable ]--[ /fault ]--[ /inBand ]--[ T_cool.Q ]--------------( stepEn )

NETWORK 5 — Nhích lên
  |--[ stepEn ]--[ sp > pv ]------------------( ADD  airCur + 1.0 → airCur )
  |                                           ( TON  T_cool, PT := coolMs  )

NETWORK 6 — Nhích xuống
  |--[ stepEn ]--[ sp < pv ]------------------( SUB  airCur - 1.0 → airCur )
  |                                           ( TON  T_cool, PT := coolMs  )

NETWORK 7 — Kẹp giới hạn
  |------------------------------------( LIMIT  0.0 ≤ airCur ≤ 100.0 )

NETWORK 8 — Tính cooldown động  (CALCULATE, chạy mỗi vòng)
  |     t      := (LIMIT(3.0, ABS(sp-pv), 30.0) - 3.0) / 27.0
  |     coolMs := 3000 - t * 1500

NETWORK 9 — Đếm ổn định để học FF
  |--[ inBand ]--[ tick_1s ]------------------------( CTU  stableSec )
  |--[ /inBand ]------------------------------------( R    stableSec )

NETWORK 10 — Xuất ra AO
  |--[ /fault ]---( NORM_X 0..100 → SCALE_X 0..27648 → QW_Airflow )
  |--[ fault  ]---( MOVE  airOnFault → airPct )
```

Phần **snap + bảng FF** có vòng lặp `FOR` tra bảng — trong LAD rất khó đọc. **Khuyến nghị: viết riêng phần đó bằng SCL** và gọi từ LAD. TIA Portal cho phép trộn ngôn ngữ theo từng khối.

---

## 16. An toàn, xử lý lỗi, tranh chấp quyền điều khiển

### 16.1 Mất truyền thông Modbus

| Tình huống | Firmware hiện tại | Khuyến nghị cho PLC |
|---|---|---|
| 1 khung lỗi | `errorCount++`, kêu còi 100 ms, **giữ nguyên `Diff_Air` cũ** | Giữ PV cũ, đếm lỗi |
| Lỗi liên tiếp ≥ 5 lần | (chưa có ngưỡng riêng) | Đặt `fault`, **giữ gió ở mức an toàn cố định** (`airOnFault`, ví dụ 60 %), báo HMI |
| Đứt hẳn | Máy vẫn chạy với số cũ | Bắt buộc có **timeout truyền thông trong biến tần** nếu dùng phương án ghi tần số qua Modbus |

**Nguyên tắc:** khi mất số đo, **không được để Air% về 0** — buồng rang mất hút là khói tràn ra xưởng và có nguy cơ cháy. Fail-safe đúng là **giữ mức gió trung bình đủ hút**.

### 16.2 Cảm biến hỏng

* raw đứng im tuyệt đối > 20 s **trong lúc Air% có thay đổi** → nghi hỏng
* raw = 0 kéo dài trong lúc quạt đang chạy > 50 % → nghi đứt dây 4–20 mA
* PV vượt ngoài `[minPT − 10 %, maxPT + 10 %]` → nghi sai thang hoặc lỏng dây

Firmware có sẵn các mã trạng thái tương ứng để báo HMI:

```
STT_VACUUM_HIGH        268   Áp hút vượt ngưỡng tối đa
STT_VACUUM_LOW         269   Áp hút dưới ngưỡng tối thiểu
STT_MB_VACUUM_ERROR    287   Lỗi Modbus với cảm biến áp hút
STT_ERR_VACUUM_FAULT   412   Hệ áp hút lỗi — kiểm tra cảm biến
```

### 16.3 Tranh chấp quyền lái Air%

Đây là bài học đắt giá đã có trong firmware: **nhiều khối cùng muốn ghi `airflowPercent`**.

```
Ưu tiên (cao → thấp):
  1. Sấy lồng / Preheat   — giữ quyền tuyệt đối, cất lệnh vacuum lại
  2. Điều khiển áp hút    — khi vacuumSetFlag = 1
  3. Chương trình rang    — Air% đặt trực tiếp theo hồ sơ
  4. Tay / biến trở VR    — mặc định
```

Cơ chế trong firmware:

```c
bool    phVacTaken;      // preheat đang giữ quyền
uint8_t phVacFlagSaved;  // cờ vacuum bị hoãn, sẽ trả lại khi preheat xong
```

Khi HMI đổi cờ vacuum lúc đang preheat, lệnh **không** áp ngay mà **cất vào `phVacFlagSaved`**, chờ `phVacRelease()` khi preheat kết thúc mới áp.

> **Trên PLC, hãy làm rõ ràng bằng một biến `airOwner : INT`** (0 = tay, 1 = rang, 2 = vacuum, 3 = preheat) và **một chỗ duy nhất ghi ra AO**. Nhiều khối cùng ghi thẳng vào cùng một thẻ là nguồn gốc của lỗi "gió tự nhiên nhảy" rất khó tìm.

### 16.4 Giới hạn setpoint

Mã trạng thái `STT_PID_VACUUM_CLAMPED` cho biết setpoint áp hút bị kẹp trong khoảng **90–250 Pa**. Trên PLC nên kẹp tương tự ở lớp HMI, và **báo cho người vận hành biết là đã bị kẹp** — đừng lặng lẽ sửa số họ nhập.

---

## 17. Bảng tham số tinh chỉnh

| Tham số | Mặc định | Tăng lên thì | Giảm xuống thì | Khi nào sửa |
|---|---|---|---|---|
| `filtAlpha` | 0.13 | Nhạy hơn, nhiễu hơn | Mượt hơn, trễ hơn | Chu kỳ đọc đổi, hoặc PV quá nhiễu/quá trễ |
| `deadband` | 3 Pa | Cơ cấu ít rung, sai số tĩnh lớn | Bám sát hơn, dễ rung | Thấy Air% nhấp nháy liên tục → tăng |
| `stepSize` | 1 % | Hội tụ nhanh, dễ vọt | Mượt, chậm | Hầu như **không nên đổi** |
| `coolNear_ms` | 3000 ms | Chậm, rất ổn định | Nhanh, dễ dao động quanh SP | Gần setpoint mà cứ đảo chiều → tăng |
| `coolFar_ms` | 1500 ms | Bậc nhảy hội tụ chậm | Hội tụ nhanh, sốc cơ khí | Đổi setpoint mà lâu quá → giảm nhẹ |
| `coolFarErr` | 30 Pa | Vùng "đi nhanh" hẹp lại | Vùng "đi nhanh" rộng ra | Theo dải áp thực tế của máy |
| `snapBuffer` | 15 % (auto 8–25) | Snap hụt nhiều, chậm nhưng chắc | Snap sát, nhanh nhưng dễ vọt lố | Để auto-tune tự tính |
| `snapDeltaMin` | 30 Pa | Ít snap hơn | Snap cả khi đổi SP nhỏ | Ít khi cần sửa |
| `snapMaxJump` | 20 % | Nhảy mạnh hơn | An toàn hơn cho quạt | Quạt lớn → giảm |
| `ffDriftPct` | 3 % | Bảng ổn định, chậm thích nghi | Nhạy với thay đổi máy | Lưới lọc bẩn nhanh → giảm |
| `stableSecToLearn` | 10 s | Học ít nhưng chắc | Học nhiều, dễ ghi nhầm giá trị chưa ổn định | Ít khi cần sửa |

---

## 18. Checklist đưa vào vận hành

**A. Phần cứng**

- [ ] Gạt đúng công tắc ACI (dòng hay áp) trên MS300
- [ ] Cảm biến có nguồn, đo được dòng 4–20 mA bằng đồng hồ khi bịt/hở ống
- [ ] RS485 xoắn đôi có màn, điện trở kết cuối 120 Ω ở **hai đầu** đường bus
- [ ] Màn chống nhiễu nối đất **một đầu duy nhất**

**B. Biến tần**

- [ ] Slave ID, baud, khung dữ liệu, giao thức Modbus RTU khớp với PLC
- [ ] ACI **không** được cấu hình làm nguồn lệnh tần số (tránh tranh quyền)
- [ ] Cài timeout truyền thông nếu PLC ghi tần số qua Modbus

**C. Đọc số**

- [ ] `MB_DATA_ADDR = 48717` (không phải 48716) — đọc ra số 0…10000
- [ ] Bịt ống → raw đổi **đúng chiều**; hở ống → raw về gần nền
- [ ] Khai `minPT`/`maxPT` đúng theo tem cảm biến, không đoán

**D. Hiệu chuẩn**

- [ ] Quạt tắt hẳn → ghi lại raw nền; PV phải ≈ 0 Pa
- [ ] Chạy auto-tune 0→100 % (~3 phút), kiểm tra bảng FF đơn điệu tăng
- [ ] Bảng FF được lưu vào vùng **retentive**, còn nguyên sau khi cắt điện

**E. Vòng kín**

- [ ] Đặt SP giữa dải (ví dụ 120 Pa) → PV vào ±3 Pa trong bao lâu? Ghi lại
- [ ] Đổi SP một bậc lớn (120 → 200 Pa) → xem snap có nhảy đúng chiều và không vọt lố
- [ ] Rút dây RS485 → PLC phải báo lỗi và giữ gió an toàn, **không** về 0
- [ ] Rút dây cảm biến → phải báo lỗi trong vòng ~20 s

---

## 19. Bẫy thường gặp

1. **Lệch địa chỉ 1 đơn vị** giữa quy ước thô (8716) và quy ước Siemens (48717) → đọc trúng thanh ghi khác, số vẫn "trông hợp lý".
2. **Chia số nguyên** trong công thức nội suy → PV luôn bằng `minPT`. Phải ép REAL.
3. **Lọc hai tầng chồng nhau** (EMA + Kalman) → trễ cộng dồn. Firmware đã từng dính lỗi này và đã bỏ một tầng. **Chỉ một tầng lọc.**
4. **Chú thích ±5 Pa trong `PID_Airflow.h` là sai** — giá trị đang chạy là **±3 Pa**.
5. **Cooldown không phải hằng số** — quên phần nội suy theo sai lệch thì hệ vừa chậm khi xa vừa rung khi gần.
6. **Snap sai chiều** nếu lấy Air% hiện tại làm mốc so sánh thay vì setpoint cũ.
7. **Bảng FF tràn** khi đổi bước quét từ 2 % xuống 1 % → mất vùng gió cao mà giao diện vẫn báo tune thành công.
8. **Mất Modbus = mất cả đo lẫn điều khiển** nếu dùng phương án ghi tần số qua Modbus. Cân nhắc giữ ngõ analog làm đường dự phòng.
9. **Nhiều khối cùng ghi Air%** — phải có biến quyền sở hữu duy nhất.
10. **Gọi nhiều `MB_MASTER` cùng lúc trên một cổng** → lỗi busy loạn xạ. Bắt buộc tuần tự.
11. **4–20 mA: đứt dây cho raw ≈ 0** trùng với giá trị hợp lệ nhỏ nhất. Phải phát hiện bằng logic, không dựa vào con số.
12. **Quạt 0 % không có nghĩa 0 Hz** — với lồng rang firmware map 0 % = 30 Hz. Kiểm tra dải Hz thực tế của quạt trước khi map.

---

## 20. Những điểm CHƯA kiểm chứng — phải tự xác nhận

Tài liệu này mô tả **đúng những gì firmware đang làm**. Các mục dưới đây **chưa đối chiếu với manual Delta MS300**, nhân viên phải tự xác nhận trước khi tin:

| Nội dung | Trạng thái |
|---|---|
| Thanh ghi `0x220C` = giá trị analog ACI, thang 0…10000 | **Đúng theo thực nghiệm trên máy đang chạy.** Chưa tra chéo với manual — nên kiểm chứng lại bằng cách thay đổi áp và xem số. |
| Thanh ghi `0x2103` = tần số ngõ ra, `0x2001` = lệnh tần số | Là quy ước chuẩn của dòng Delta, nhưng vẫn nên tra manual của **đúng model MS300** đang dùng. |
| Mã tham số cấu hình ACI (nhóm P03-xx) | **Chưa xác nhận.** Tài liệu này cố ý không ghi mã cụ thể để tránh dẫn sai — tra manual MS300 mục Analog Input. |
| Khung dữ liệu 8-N-1 | Suy đoán từ cấu hình phổ biến. **Phải đọc tham số truyền thông thực tế trong biến tần.** |
| Ngưỡng kẹp setpoint 90–250 Pa | Có trong mã trạng thái `STT_PID_VACUUM_CLAMPED` nhưng **không tìm thấy đoạn code thực thi** trong bản firmware hiện tại — có thể do HMI kẹp. Cần xác nhận. |
| Dải Hz của quạt gió | Firmware map dải 30–50 Hz cho **lồng rang**, không phải quạt. Dải quạt phải đo thực tế. |

---

## PHỤ LỤC — Đối chiếu tên biến firmware ↔ PLC

| Firmware (C) | Ý nghĩa | Tên gợi ý trên PLC |
|---|---|---|
| `raw_Diff_Air` | Giá trị thô 0…10000 từ ACI | `rawVac` |
| `Diff_Air` | Áp hút đã lọc, Pa — **PV** | `pv_Pa` |
| `minPT_R` / `maxPT_R` | Hai đầu thang cảm biến (HMI reg 49/50) | `cfg.minPT` / `cfg.maxPT` |
| `vacuumSetpoint_R` | Setpoint áp hút, Pa (HMI reg 48) | `sp_Pa` |
| `vacuumSetFlag_R` | Bật/tắt điều khiển áp hút (HMI reg 47) | `enable` |
| `airflowPercent` | Air% xuất ra cơ cấu | `airPct` |
| `air_current` | Air% nội bộ dạng REAL | `airCur` |
| `ffMap[]` | Bảng feed-forward Pa→Air% | `ffSp[] / ffAir[] / ffCnt[]` |
| `pidSnapBuffer` | Biên nhảy hụt khi snap | `cfg.snapBuffer` |
| `stableTimer` | Đếm giây ổn định để học | `stableSec` |
| `stepCooldownMs` | Mốc hết cooldown | `coolUntil` |
| `ftState` | Trạng thái auto-tune | `tuneState` |
| `AUTO_PID_AIR_TU_R` | Nút Tune trên HMI | `cmdTune` |

---

*Hết. Mọi thắc mắc về con số cụ thể, tra thẳng `include/PID_Airflow.h` và hàm `readUnder()` trong `include/Modbus_Master.h` — đó là nguồn sự thật.*
