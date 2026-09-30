# CLAUDE.md — OTL-06ALS Coffee Roaster CMS

Firmware điều khiển máy rang cà phê chạy trên STM32F103RC, dùng PlatformIO + Arduino framework.

---

## Build & Flash

```bash
# Build
pio run -e genericSTM32F103RC

# Flash qua ST-Link
pio run -e genericSTM32F103RC --target upload

# Kiểm tra kích thước RAM/Flash
pio run -e genericSTM32F103RC --target size

# Monitor serial debug (UART4, 9600 baud)
pio device monitor --baud 9600
```

---

## Hardware Constraints

| Tài nguyên | Giới hạn | Ghi chú |
|-----------|---------|---------|
| Flash     | 256 KB  | Firmware + SD lib + Modbus libs |
| RAM       | 20 KB   | **Rất hạn chế** — cẩn thận mảng lớn |
| EEPROM    | Không có | Dùng SD card để lưu persistent data |
| CPU       | 72 MHz ARM Cortex-M3 | Không có FPU |

### Mảng lớn cần chú ý (khai báo trong Define.h)
- `sdBT[1500]`, `sdET[1500]` — 3000 bytes mỗi mảng (int16_t)
- `sdAirflow[1500]`, `sdGas[1500]`, `sdDrum[1500]` — ~1500 bytes mỗi mảng
- `iMemHMI[60]`, `dAddress[200]` + bản sao `_CP[]` — ~1 KB
- Tổng ước tính mảng SD: **~15 KB** → gần hết RAM

---

## Kiến trúc file

```
src/main.cpp          — Entry point, setup() + loop()
include/Define.h      — Global state: tất cả biến, macro, pin (~2000 dòng)
include/IOConfig.h    — GPIO init + relay control
include/AnalogConfig.h — DAC (MCP4725 I2C) + ADC + slew rate gas
include/PID_Airflow.h — Vacuum PID step controller + FF table + auto-tune
include/ScaleFeeder.h — Bluetooth scale parser ("GS,NN.N,kg")
include/Modbus_Slave.h — Artisan PC interface (ModbusRTU slave, 27 regs)
include/Modbus_Master.h — HMI + sensor + inverter (ModbusMaster library)
include/Program.h     — Business logic: roasting state machine + SD log
```

Tài liệu đầy đủ: [ARCHITECTURE.md](ARCHITECTURE.md)

---

## Modbus Nodes (RS485)

| Node | Slave ID | Serial | Baud | Thiết bị |
|------|---------|--------|------|---------|
| nodeHMI | 1 | SerialHmi (USART1) | 115200 | Delta HMI |
| nodeBT | 1 | SerialModbus (USART2) | 38400 | Thermocouple BT |
| nodeET | 2 | SerialModbus | 38400 | Thermocouple ET |
| nodeDrum | 4 | SerialModbus | 38400 | Drum inverter |
| nodeAir | 5 | SerialModbus | 38400 | Airflow inverter |
| nodeIORelay | 7 | SerialModbus | 38400 | IO relay 8ch |
| mbs (slave) | configurable | SerialComputer (UART4) | configurable | Artisan PC |

---

## Naming Conventions

- `*_R` — giá trị đang dùng (ví dụ: `btSV_R`)
- `*_R_CP` — bản copy từ HMI để so sánh (ví dụ: `btSV_R_CP`)
- `*_R_CV` — giá trị đã convert (×10) để tính toán nội bộ (ví dụ: `btSV_R_CV`)
- `*_W` — địa chỉ Modbus register để ghi (ví dụ: `BT_HMI_W`)
- `*En` — flag bật/tắt (ví dụ: `chargeTimerEn`)
- `*Ti` / `*Timer` — biến đếm thời gian (ví dụ: `chargeTimer`)
- `STP_*` — bước trong state machine (ví dụ: `STP_CHARGE`)
- `STT_*` — trạng thái chương trình (ví dụ: `STT_PROGRAM_AUTO`)
- `SOURCE_AI_*` — nguồn điều khiển (VR / PC / AUTO)

---

## ISR Safety

- `timerPoll_1000ms()` chạy trong ISR (TIM1, 1kHz)
- **Không gọi SD / Modbus / Serial trong ISR**
- Dùng flag pattern: ISR set `selfTuneTickEn = true`, logic nặng chạy trong `loop()`
- Biến dùng chung giữa ISR và loop cần khai báo `volatile`

---

## Đơn vị dữ liệu

- Nhiệt độ: lưu dạng **×10** (ví dụ: 1850 = 185.0°C)
- Thời gian rang: **giây** (ví dụ: `timeRoast = 245` = 4 phút 5 giây)
- Gas/Airflow/Drum: **% nguyên** (0–100)
- Áp suất chân không: **Pa** (ví dụ: `Diff_Air = -80`)
- Cân: **×10** (ví dụ: `netW = 617` = 61.7 kg)

---

## SD Card Files

| File | Mục đích |
|------|---------|
| `0.txt` – `15.txt` | Profile rang (format cũ) |
| `0.csv` – `15.csv` | Log Artisan CSV (format mới) |
| `/pid_ff.txt` | FF table PID vacuum (Pa → Air%) |

---

## Debug

Bật debug: đặt `enDebug = 1` trong code hoặc từ HMI.

Output qua `SerialComputer` (UART4, 9600 baud):
```
Loop: 87ms | Charge: 12 | Roast: 245 | CalSD: 34
```

**Quy tắc SerialComputer:**
- Tất cả string in ra `SerialComputer` phải bằng **tiếng Anh**
- Chỉ in khi `enDebug = 1`: `if(enDebug) SerialComputer.println("...")`

---

## Quản lý file 3D / Inventor / STEP / EPLAN

- **Quy ước đầy đủ (bản gốc, cho cả Claude lẫn Codex): `F:\Project\112_Quanly\121_Inventor_3D\AGENTS.md`** — đọc file đó trước khi tạo, đổi tên hay di chuyển bất cứ file 3D nào.
- Không lưu các file này trong repository firmware.
- Inventor và STEP cho EPLAN: `F:\Project\112_Quanly\121_Inventor_3D`; vật tư theo mã nằm trong `03_VatTu_3D_theo_ma\<Hang.Ma>`.
- STEP gốc của hãng đặt trong `STEP_Hang`; IPT đã xử lý, preview và STEP AP214 Pro Panel đặt ở thư mục mã vật tư.
- Macro, part data, gói EDZ và build EPLAN đặt tại `F:\Project\112_Quanly\EDZ`.
- Nếu dùng repository firmware làm nơi tạm thì phải chuyển kết quả sang `112_Quanly` và dọn bản tạm khi hoàn tất.

---

## Workflow gợi ý

- Trước khi sửa code lớn: dùng `/plan` để thiết kế
- Sau khi sửa: chạy `/simplify` để review chất lượng
- Kiểm tra RAM: chạy `/memory-check`
- Kiểm tra Modbus: chạy `/modbus-audit`
- Phân tích PID: chạy `/pid-analysis`
- Trace state machine: chạy `/state-trace`
- Commit: dùng `/commit`

---

## Dựng tài liệu cho khách (manual, hướng dẫn sửa)

Quy ước đầy đủ nằm trong skill [`manual-otl`](.claude/skills/manual-otl/SKILL.md). Tóm tắt:

- **Bắt đầu tài liệu mới** thì chép
  [`references/content-mau-toi-thieu.jsx`](.claude/skills/manual-otl/references/content-mau-toi-thieu.jsx)
  — bộ khung chạy được ngay, có đủ hàm dàn trang và chú thích từng hàm. Hai file
  `content-mau-preheat*.jsx` cạnh đó là ví dụ dày hơn, lấy từ chương đã giao khách.
- **Dựng bằng một lệnh**: `python .claude/skills/manual-otl/assets/make.py <content>.jsx`,
  hoặc qua MCP `otl-manual` (`tools/mcp_manual/`), công cụ `manual_dung`.

⛔ **Ba luật không được bỏ qua:**

1. **`OK pages=N` KHÔNG có nghĩa là tài liệu xong.** Dòng đó chỉ nói script chạy trót lọt.
   Máy chỉ rà được trang thưa chữ; chồng chữ, tràn khung, logo chạm tiêu đề thì nó không thấy.
   **Phải render PNG và soi bằng mắt** rồi mới được nói là xong.
2. **KHÔNG viết tên, địa chỉ hay liên hệ của đối tác vào repo này** — repo từng để PUBLIC.
   Thông tin thương hiệu từng đối tác để ở `112_Quanly\122_Manual_AI\BAN-OEM-DOI-TAC.md`.
3. **Bản OEM là bản SINH RA bằng script, không sửa tay.** Sửa bản gốc rồi chạy lại script.
   Script phải tự dừng khi còn sót dấu vết thương hiệu gốc, và phải kiểm lại **trên chính
   file PDF** (`manual_kiem_chuoi_cam`) — đọc mã nguồn là chưa đủ, ảnh bìa cũ vẫn có thể mang
   dấu nhận dập trên tôn máy.

---

## Giao diện app Roast Lab — làm chung với Codex

Trước khi sửa `OTL Roast Lab.html` hoặc `tools/test_ui_*`:

1. Đọc khoá `docs/ui/UI-LOCK.md` — nếu Codex đang giữ thì KHÔNG sửa.
2. Đọc đặc tả thiết kế `docs/ui/2026-09-07-design-spec.md`.
3. Bản thiết kế gốc mirror ở `docs/ui/design-web/` (kéo về bằng `DesignSync`).

Quy ước đầy đủ cho cả hai bên: mục "Bản thiết kế Claude Design và cách Claude +
Codex làm chung trên app" trong [AGENTS.md](AGENTS.md).
