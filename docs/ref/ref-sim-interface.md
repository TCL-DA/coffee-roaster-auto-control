# ref-sim-interface — Giao tiếp firmware ↔ app mô phỏng máy rang

Tài liệu này mô tả **mặt giao tiếp** mà firmware OTL-06ALS phơi ra ngoài, để app
mô phỏng đóng vai máy rang. Dữ liệu máy đọc được kèm theo:
[`tools/sim/register_map.json`](tools/sim/register_map.json).

> Mục tiêu: app đọc `gas%`/`air%` firmware tính ra → chạy model nhiệt → trả
> `BT`/`ET` về cho firmware đọc. Vòng kín, không cần máy rang thật.

---

## 1. Firmware nói chuyện ra ngoài qua đâu

Toàn bộ I/O phần cứng nằm gọn ở đầu `loop()` (xem [src/main.cpp](src/main.cpp)),
qua **3 bus**. Mô phỏng máy rang chỉ cần **2 bus đầu**:

| Bus | UART | Baud | Vai trò app | Thiết bị app đóng vai |
|-----|------|------|-------------|------------------------|
| sensor_bus | USART2 | 38400 | **Slave** | Can nhiệt BT(1), ET(2), biến tần drum(4)/gió(5), IO relay(7) |
| hmi_bus    | USART1 | 115200 | **Slave** | HMI Delta (id 1) — firmware là master |
| artisan_bus| UART4 | 9600 | bỏ qua | Firmware là slave, Artisan PC là master |

---

## 2. Vòng kín mô phỏng (cốt lõi)

```
   firmware                              app mô phỏng
   --------                              ------------
   tính gas%, air%  ──ghi HMI bus reg 67/65──►  đọc gas%, air%
                                                      │
                                                model nhiệt:
                                                gas% → RoR → BT, ET
                                                      │
   đọc BT, ET  ◄──trả trên sensor bus (id 1/2)──  cấp BT, ET
   tính lại gas%  ─────────────────────────────►  (lặp mỗi giây)
```

**Mấu chốt:** lệnh gas firmware tính ra được *mirror sẵn* lên HMI bus tại
`GAS_HMI` (reg 67, đơn vị %×10) và `AIRFLOW_HMI` (reg 65). App **không cần đọc
I2C/DAC** — chỉ đọc 2 register này là biết firmware đang ra lệnh gas/gió bao nhiêu.

---

## 3. Quy ước hướng (direction)

Tính theo **góc nhìn của app**, không phải firmware:

| direction | Nghĩa |
|-----------|-------|
| `sim_provides` | Firmware **đọc** → app phải cấp giá trị (vd nhiệt độ, nút bấm) |
| `sim_captures` | Firmware **ghi** → app đọc để chạy model (vd gas%, relay) |
| `sim_serves`   | App giữ trạng thái, firmware đọc/ghi tuỳ lúc |

---

## 4. Bus cảm biến (app làm slave)

| Node | ID | Register | Hướng | Ghi chú |
|------|----|----------|-------|---------|
| BT   | 1  | `tempRegister` (1 reg) | provides | trả **BT×10** cho mọi lần đọc 1 reg |
| ET   | 2  | `tempRegister` (1 reg) | provides | trả **ET×10** |
| drum | 4  | 8451 đọc / 8193 ghi | provides / captures | freq drum |
| air  | 5  | 8451 đọc | provides | freq quạt gió |
| air  | 5  | **8716 (ACI)** | provides | cảm biến **chân không** — app sinh áp suất giả từ air% |
| relay| 7  | coil 0–7 | captures | CH1=drum/fan, CH2=mixer… |

> ⚠️ `tempRegister` là **địa chỉ cấu hình lúc chạy** (= `iMemHMI[6]`, nạp từ
> HMI/SD). App là slave nên cứ trả `BT×10` cho lệnh đọc-1-reg của node id 1,
> `ET×10` cho id 2 — không cần biết chính xác địa chỉ.

---

## 5. Bus HMI (app làm slave, đóng vai HMI)

Firmware là **master**, đọc nút bấm và ghi giá trị hiển thị.

### App PHẢI cấp (firmware đọc) — đây là chỗ thay nút bấm HMI
Khối `iMemHMI` (địa chỉ 1-based, $M HMI):

| Reg | Tên | Ý nghĩa |
|-----|-----|---------|
| 1 | START_BTN | bật/tắt Auto |
| 2 | START_GAS_BTN | bật/tắt gas |
| 7 | **CHARGE_BTN** | xi lanh charge → mốc bắt đầu rang |
| 8 | DROP_BTN | xả mẻ |
| 16 | SELECT_FILE | chọn profile 0–15 |
| 23 | SW_M_AUTO | manual/auto |
| 39 | REFRESH_LOAD_PF | nạp profile từ SD |
| 40 | WU | warm up / preheat |

### App ĐỌC để chạy model (firmware ghi) — khối hiển thị

| Reg | Tên | Thang | Ghi chú |
|-----|-----|-------|---------|
| 61 | BT_HMI | ×10 | firmware echo BT (chỉ hiển thị) |
| 62 | ET_HMI | ×10 | |
| 63 | ROR_BT_HMI | | RoR BT firmware tự tính |
| 65 | **AIRFLOW_HMI** | %×10 | **dùng làm air% cho model** |
| 66 | DRUM_HMI | %×10 | |
| 67 | **GAS_HMI** | %×10 | **dùng làm gas% cho model** ⭐ |
| 68/69 | MIN/SEC_HMI | | thời gian rang |
| 41 | STT | | mã trạng thái máy |

> Khối `dAddress[500]` (40xxx) chứa **dữ liệu profile** (charge temp, TP, FCs…).
> Firmware đọc khi load profile và ghi khi cập nhật. App tối thiểu có thể trả 0
> cho cả khối; nếu muốn test luồng AUTO theo profile thì nạp giá trị thật vào đây.

---

## 6. Model nhiệt — app tự lo

Register map chỉ là "đường ống". Phần "máy rang phản ứng thế nào" do app tự
hiện thực. Tham khảo có sẵn trong repo:

- `preheat_pid_simulator.html`, `preheat_simulator.html` — công thức gas→nhiệt
- [analysis-roaster-thermal.md](analysis-roaster-thermal.md) — gas gain ~1.5 °C/min/%, điểm cân bằng
- [config-6kg-M04.md](config-6kg-M04.md), [config-12kg-M05.md](config-12kg-M05.md) — tham số từng máy
- `testnhiet.csv` — dữ liệu nhiệt đo thật để replay/đối chiếu

Hợp đồng tối thiểu của model: `f(gas%, air%, BT, ET, dt) → (BT', ET')` mỗi giây.

---

## 7. Những điều phải lưu ý khi mô phỏng

1. **`delay()` trong firmware**: `readTempBT/ET` có `delay(10)`, đọc lỗi có
   `delay(100)`×2 + buzzer. App phải **trả lời kịp** (timeout Modbus) nếu không
   firmware báo lỗi đọc BT/ET.
2. **Đơn vị**: nhiệt ×10, % trên HMI bus ×10 nhưng trên Artisan slave ×1.
3. **Artisan bus dùng chung UART4 với debug** — bật `enDebug` sẽ phá link Artisan.
   Không ảnh hưởng mô phỏng vì bus này được bỏ qua.
4. **Địa chỉ 1-based vs 0-based**: macro `*_W` trong Define.h là 1-based theo HMI
   Delta (40001…); code firmware thường trừ 1 khi gọi thư viện ModbusMaster
   (vd `nodeHMI.writeSingleRegister(GAS_HMI_W-1, …)`). App slave nhận theo
   0-based của lệnh Modbus trên dây — kiểm tra lệch 1 khi map.

---

## 8. Phần cứng cần cho mô phỏng đầy đủ (HIL)

- 1 board STM32F103 (trần, không cần tủ điện) nạp firmware thật.
- **2 bộ USB-RS485**: một cho HMI bus (115200), một cho sensor bus (38400) —
  vì là 2 UART vật lý riêng, baud khác nhau.
- App chạy `pymodbus` (hoặc tương đương) làm slave trên cả 2 cổng + model nhiệt.

Nguồn gốc dữ liệu: trích từ [include/Define.h](include/Define.h),
[include/Config.h](include/Config.h), [include/Modbus_Slave.h](include/Modbus_Slave.h),
[include/Modbus_Master.h](include/Modbus_Master.h). Khi đổi địa chỉ register trong
firmware, cập nhật lại `tools/sim/register_map.json`.
