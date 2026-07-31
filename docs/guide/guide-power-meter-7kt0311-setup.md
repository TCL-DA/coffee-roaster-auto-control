# Hướng dẫn cài đồng hồ điện SMART 7KT0311 — máy rang OTL

Cấu hình cụ thể cho lần lắp này:

| Hạng mục | Giá trị thực tế |
|----------|-----------------|
| Điện áp vào | **400 V** 3 pha (L-L), 230 V pha–trung tính |
| Tần số | **50 Hz** |
| CT | **PE301.50 — 50/5A**, Class 3, VA 1, ×3 cái (3 pha) |
| Kiểu đấu | 3 pha 4 dây (3P4W) — đấu áp **trực tiếp, không qua PT** |

> Đồng hồ: Siemens SMART 7KT0311, Modbus RTU / RS485, đo True RMS, Class 0.5s.
> CT tỉ số 50/5A = **10:1**. Toàn bộ độ chính xác hệ bị giới hạn bởi CT Class 3 (±3%).

---

## 1. Bảng thông số nên cài

Cài bằng phím trên mặt máy, hoặc ghi qua Modbus (thanh ghi Integer dải 40000, FC06/16).

| Trang phím | Thông số | **Giá trị cài** | Thanh ghi Modbus (Hex) | Giải thích |
|-----------|----------|-----------------|------------------------|-----------|
| 2 | Network Selection | **3P4W** | 40001 = **0** | 3 pha 4 dây (có trung tính) |
| 3 | CT Secondary | **5** | 40002 = **5** | thứ cấp CT = 5 A |
| 4 | CT Primary | **50** | 40003 = **50** | sơ cấp CT = 50 A |
| 5 | PT Secondary | **400** (= Primary) | 40004 = 400 | đấu trực tiếp → tỉ số 1:1 |
| 6 | PT Primary | **400** (= Secondary) | 40005 = 400 | đấu trực tiếp → tỉ số 1:1 |
| 7 | Slave ID | **1** (độc lập) / **6** (vào bus máy rang) | 40007 | tránh trùng ID khác trên bus |
| 8 | Baud Rate | **9600** (độc lập) / **19200** (vào bus) | 40008 = 5 (9600) / 6 (19200) | xem mục 4 |
| 9 | Parity | **None** | 40009 = 0 | |
| 10 | Stop Bit | **1** | 40010 = 0 | |
| 11 | Back Light | **0** (sáng liên tục) | 40011 = 0 | hoặc đặt giây tự tắt |
| 12 | Page Mode | **Auto** | 40014 = 0 | trang tự cuộn 5 giây |

**Tần số 50 Hz KHÔNG cần cài** — đồng hồ tự nhận tần số lưới (dải 45–65 Hz).

---

## 2. ⚠️ Quan trọng về cài PT (điện áp 400V)

- 400V L-L nằm trong dải đo trực tiếp của đồng hồ (max **415V L-L / 240V L-N**) → **đấu áp thẳng vào V1/V2/V3/N, KHÔNG cần biến áp đo lường (PT/VT)**.
- Khi đấu trực tiếp, **PT Primary PHẢI bằng PT Secondary** (tỉ số 1:1). Đặt cả hai = **400**.
- **BẪY thường gặp:** nếu để PT Primary = 400 mà PT Secondary = 350 (giá trị mặc định) → tỉ số 1.14 → điện áp hiển thị **sai cao ~14%**. Nhớ chỉnh cả hai bằng nhau.

---

## 3. ⚠️ An toàn & đấu dây CT (3 cái)

1. **KHÔNG BAO GIỜ để hở thứ cấp CT (S1–S2) khi sơ cấp đang mang dòng.** Hở mạch → sinh điện áp cao nguy hiểm chết người, hỏng CT. Trước khi tháo dây khỏi đồng hồ phải **nối tắt S1–S2**.
2. **Đúng cực tính & đúng pha:** dòng đi vào **P1 → ra P2**. Thứ cấp **S1/S2** của CT pha nào đấu đúng vào ngõ dòng I1/I2/I3 cùng pha với áp V1/V2/V3. Sai cực → công suất/PF ra **âm hoặc sai lệch**.
3. Mỗi CT **chỉ ôm 1 dây pha** (không ôm cả bó dây).
4. **Dây thứ cấp CT ngắn, tiết diện đủ:** CT chỉ có VA = 1 (gánh nhỏ) → dây dài/nhỏ làm sụt áp, sai số tăng. Đi dây ngắn nhất có thể.
5. Nên có **cầu chì ngoài 0.5A loại gG** cho mạch áp (đồng hồ không có cầu chì trong).
6. Ngắt điện trước khi đấu; đấu theo đúng sơ đồ 3P4W-3CT trong manual.

---

## 3b. Sơ đồ đấu đầu cực (3P4W + 3 CT)

Đồng hồ cần **nguồn nuôi phụ (Vaux 95–240V AC)** riêng, KHÔNG lấy từ mạch đo.

| Nhóm đầu cực | Đấu vào | Ghi chú |
|--------------|---------|---------|
| **Nguồn nuôi** L, N | 230V AC (1 pha + trung tính) | qua cầu chì 0.5A gG; nuôi mạch điện tử đồng hồ |
| **Áp đo** V1, V2, V3 | 3 pha L1, L2, L3 (trực tiếp) | mỗi pha 1 dây; qua cầu chì/CB nhỏ |
| **Áp đo** N | trung tính | bắt buộc cho 3P4W |
| **Dòng I1** (S1, S2) | thứ cấp CT pha L1 | S1 vào, S2 ra — đúng cực |
| **Dòng I2** (S1, S2) | thứ cấp CT pha L2 | |
| **Dòng I3** (S1, S2) | thứ cấp CT pha L3 | |
| **RS485** +, − | bus Modbus (nếu dùng) | điện trở cuối 120Ω |
| **DI** +, − | ngõ vào số (tuỳ chọn) | 24V DC ngoài, max 30V |
| **DO** + | ngõ ra xung kWh (tuỳ chọn) | max 30V, 130mA |

**Nguyên tắc bắt buộc:** CT ở pha nào thì ngõ dòng của pha đó phải cùng pha với áp
(CT L1 → I1 và V1 cùng là pha L1). Lẫn pha giữa dòng và áp → công suất từng pha sai
dù tổng có thể gần đúng.

---

## 4. Nếu đấu vào bus RS485 của máy rang

Bus RS485 hiện tại của firmware chạy **38400 baud**, các Slave ID đang dùng: **1** (HMI/BT), **2** (ET), **4** (drum), **5** (air), **7** (relay).

- **Baud:** đồng hồ 7KT0311 **chỉ hỗ trợ tối đa 19200** → KHÔNG chạy được ở 38400. Hai lựa chọn:
  - Cho đồng hồ một **cổng RS485 riêng** (khuyên dùng, khỏi đụng bus máy rang), hoặc
  - Hạ baud cả bus máy rang xuống 19200 (phải sửa `MACHINE_RS485_BAUD` và mọi thiết bị trên bus — ảnh hưởng lớn, cân nhắc kỹ).
- **Slave ID:** đặt **6** hoặc **8** (tránh 1/2/4/5/7).
- **Đọc dữ liệu:** đo lường nằm ở dải **3xxxx = Input Register, đọc bằng FC04** (khác `readHoldingRegisters` đang dùng cho biến tần). Mỗi giá trị là **Float 32-bit = 2 register**; thứ tự word (endianness) manual không ghi rõ, phải thử lúc chạy.

Thanh ghi đo hay dùng (Float, Hex offset):
| Hex | Thông số |
|-----|----------|
| 0x2A | Total kW (công suất tác dụng) |
| 0x2C | Total kVA |
| 0x2E | Total kVAr |
| 0x36 | Average PF |
| 0x38 | Frequency |
| 0x3A | Total net kWh (điện năng) |

---

## 5. Kiểm tra dải đo CT có hợp tải không

- CT 50/5A đo tốt tới **50A × 120% = 60A** mỗi pha.
- Ở 400V 3 pha, 50A ≈ **√3 × 400 × 50 ≈ 34.6 kW** (PF≈1). → CT này hợp tải máy đến ~**35 kW/pha đầy tải**.
- Nếu tải thực **lớn hơn 50A** → CT bão hòa, đọc thiếu → phải đổi CT tỉ số lớn hơn (vd 75/5, 100/5) và chỉnh lại CT Primary.
- Nếu tải thường **rất nhỏ** (< ~0.5A sơ cấp = 1% dải) → sai số CT lớn ở vùng thấp.

---

## 6. Quy trình cài nhanh bằng phím

1. Giữ **F3 + F4 ~3 giây** → hiện trang password (0000).
2. Nhập **1000** (F1 dời con trỏ, F2/F3 tăng/giảm), nhấn **F4**.
3. Lần lượt qua từng trang, chỉnh theo bảng mục 1 (F2/F3 đổi giá trị, F4 sang trang).
4. Xong giữ **F3 + F4 ~3 giây** để lưu và thoát.
5. Kiểm tra: xem trang điện áp (phải đọc ~**400V L-L / 230V L-N**), trang dòng (đúng chiều, không âm), PF hợp lý (0.7–1.0 khi có tải).

> Nếu điện áp đúng mà **dòng/công suất âm hoặc lệch pha** → sai cực tính hoặc sai thứ tự pha CT. Đảo S1↔S2 của pha bị âm, hoặc kiểm tra lại CT nào ôm dây pha nào.

---

## 7. Checklist nghiệm thu (đánh dấu từng mục)

- [ ] Đã ngắt điện toàn bộ trước khi đấu dây.
- [ ] Nguồn nuôi L-N (230V) đấu riêng, qua cầu chì 0.5A.
- [ ] 3 CT ôm đúng 3 dây pha L1/L2/L3, mỗi CT 1 dây.
- [ ] Cực tính CT đúng chiều P1→P2 (mũi tên/nhãn hướng về tải).
- [ ] Thứ cấp CT (S1/S2) đúng pha với áp (I1↔V1, I2↔V2, I3↔V3).
- [ ] Không có CT nào hở mạch thứ cấp khi đóng điện.
- [ ] Network = 3P4W, CT 50/5, PT 400/400 (1:1).
- [ ] Đóng điện: áp đọc ~400V L-L / 230V L-N.
- [ ] Có tải: 3 dòng dương, PF 0.7–1.0, Total kW hợp lý.
- [ ] (Nếu dùng Modbus) Slave ID không trùng, baud khớp, đọc được thanh ghi.

---

## 8. Bảng lỗi thường gặp

| Hiện tượng | Nguyên nhân khả dĩ | Cách xử lý |
|-----------|-------------------|-----------|
| Điện áp hiển thị cao/thấp bất thường | PT Primary ≠ PT Secondary | Đặt cả hai = 400 (tỉ số 1:1) |
| 1 pha công suất/PF **âm** | CT pha đó ngược cực | Đảo S1↔S2 của pha đó |
| Công suất tổng đúng, từng pha lộn xộn | Lẫn pha giữa CT và áp | Rà lại CT nào ôm dây pha nào, khớp với V |
| Dòng đọc = 0 khi có tải | Hở/lỏng dây thứ cấp CT, hoặc CT không ôm dây pha | Kiểm tra đấu S1/S2, vị trí CT |
| Dòng đọc thiếu nhiều | Tải > 50A (CT bão hoà) | Đổi CT tỉ số lớn hơn, chỉnh CT Primary |
| Đồng hồ không lên nguồn | Thiếu nguồn nuôi Vaux L-N | Cấp 95–240V AC vào L/N nguồn nuôi |
| Không đọc được Modbus | Trùng Slave ID / sai baud / lệch parity | Đặt ID riêng, baud khớp, đọc FC04 dải 3xxxx |
| Số đọc Modbus vô nghĩa (float sai) | Sai thứ tự word 32-bit | Thử đảo word order khi ghép float |
