# Cảm biến nhiệt độ (Thermocouple) — OTL-06ALS

Thông số cảm biến nhiệt đang dùng cho máy rang, đo nhiệt độ hạt (BT) và
nhiệt độ môi trường buồng rang (ET). Dùng để tra khi thay thế, đặt hàng,
hoặc kiểm tra khi số đọc bị sai.

---

## 1. Thông số chung

| Mục | Giá trị |
|-----|---------|
| Loại cặp nhiệt | K-Type (NiCr-Ni) Simplex |
| Kiểu mối nối (Junction) | Ungrounded (không tiếp mass vỏ) |
| Vỏ bọc (Sheath) | Inconel 600 |
| Vật liệu cách điện trong sheath | MgO (Magnesium Oxide) |
| Cấp chính xác | IEC 60584-1, Class 1 |
| Dải nhiệt độ làm việc | 0 – 600 °C |
| Chiều dài tổng | 2 mét (2 MTR) |

---

## 2. Giải thích từng thông số

### K-Type (NiCr-Ni) Simplex
- Cặp nhiệt loại K: dây dương là hợp kim **NiCr (Chromel)**, dây âm là
  **Ni (Alumel)**. Đây là loại phổ biến nhất cho rang cà phê vì dải rộng,
  rẻ, bền, tuyến tính tốt trong vùng 0–500 °C.
- **Simplex** = 1 cặp nhiệt (1 điểm đo) trong 1 vỏ. (Duplex = 2 cặp.)

### Junction Ungrounded (mối nối không tiếp mass)
- Điểm nối 2 dây **không** dính vào vỏ Inconel, được cách ly bằng MgO.
- Ưu điểm: **chống nhiễu điện** (ground loop) khi gắn lên khung máy kim
  loại, an toàn khi đi chung máng với dây động lực biến tần.
- Nhược điểm: đáp ứng nhiệt **chậm hơn một chút** so với loại grounded
  (vì nhiệt phải qua lớp cách điện). Với rang cà phê thì chấp nhận được.

### Vỏ Inconel 600 + cách điện MgO
- Inconel 600: hợp kim niken-crom, chịu nhiệt và chống oxy hóa tốt tới
  hơn 1000 °C → dư sức cho vùng rang.
- MgO: bột cách điện chịu nhiệt, ép chặt quanh dây bên trong sheath.

### Cấp chính xác — IEC 60584-1, Class 1
- Class 1 là cấp chính xác **cao hơn** Class 2.
- Sai số cho phép loại K, Class 1:
  - **±1.5 °C** trong dải −40 … +375 °C
  - **±0.004 × |t|** ở trên 375 °C
- Trong vùng rang thực tế (BT/ET ~ 20–250 °C) → sai số ≤ **±1.5 °C**.
  Đây là dung sai của riêng cảm biến, chưa gồm sai số của bộ transmitter
  và bù nhiệt đầu lạnh (cold junction).

### Dải 0 – 600 °C
- Nhiệt rang cà phê/ca cao thường 20–250 °C → còn rất nhiều biên an toàn,
  cảm biến không bị chạy sát trần.

---

## 3. Cáp tín hiệu

| Mục | Giá trị |
|-----|---------|
| Mã cáp | GG-465-2K-0.22L |
| Cách điện | Đơn và chung, bằng Teflon (PTFE) |
| Tiết diện dây | 2 × 0.22 mm² |
| Mã màu | IEC 60584-3 |
| Dây dương (+) | **GREEN (xanh lá)** |
| Dây âm (−) | **WHITE (trắng)** |

> Lưu ý đấu nối: theo chuẩn IEC 60584-3, vỏ ngoài cáp bù loại K màu
> **xanh lá**. Khi đấu vào transmitter phải đúng cực **(+) xanh lá,
> (−) trắng** — đấu ngược cực sẽ làm số đọc sai/âm.

---

## 4. Cấu tạo cơ khí (từ đầu ra xuống đầu đo)

1. **Đầu cốt bấm (Crimped lugs)** — phần đầu ~50.0 mm, để bắt vào terminal.
2. **Ống co nhiệt (Heat shrinking tube)** — bảo vệ điểm nối cáp.
3. **Đoạn cáp GG-465** — thân dài (tổng thành phẩm 2 m).
4. **Lò xo chống gãy (Strain relief spring)** — tại gốc sheath, chống gãy
   dây do rung/uốn.
5. **Sheath Inconel 600** — phần que kim loại cắm vào buồng rang.
6. **Bản ép / phiên bản góc vuông (Press bracket / Angle version)** —
   đầu đo bẻ góc 90° để gá cố định.

---

## 5. Kích thước vỏ bọc & mã đặt hàng

| SL.NO | Đường kính sheath (Ø) | Chiều dài sheath | Art Number |
|-------|-----------------------|------------------|------------|
| 01 | 2.0 mm | 50 mm | 2-01-2000-10109 |
| 02 | 3.2 mm | 100 mm | 2-01-2000-10110 |

- Sheath **Ø2.0 / 50 mm**: mảnh, đáp ứng nhanh → hợp đo **BT** (cắm vào
  dòng hạt).
- Sheath **Ø3.2 / 100 mm**: to, chắc hơn → thường đo **ET** (nhiệt khí
  môi trường).
- (Việc gán BT/ET tùy vị trí lắp thực tế trên máy — mục này chỉ là gợi ý
  thông thường.)

---

## 6. Ghi chú tích hợp với firmware

- Cảm biến K-type nối qua **module transmitter → Modbus RTU**, không đọc
  điện áp mV trực tiếp trên STM32.
- Trong hệ Modbus (xem CLAUDE.md):
  - `nodeBT` — Slave ID 1, SerialModbus (USART2), 38400 baud
  - `nodeET` — Slave ID 2, cùng bus, 38400 baud
- Nhiệt độ đọc về lưu dạng **×10** (ví dụ 1850 = 185.0 °C).
- Nếu số đọc **âm hoặc nhảy loạn** → kiểm tra đấu cực (+xanh lá / −trắng)
  và kiểu bù cold-junction trên transmitter.
