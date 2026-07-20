# PC_Link — Công thức truyền/nhận (Modbus RTU) giữa app OTL Roast Lab ↔ máy rang

> Giao thức trên dây cho [include/PC_Link.h](../../include/PC_Link.h). App PC là **Modbus RTU master**,
> STM32 là **slave** (dùng chung con `mbs` với Artisan). Cổng vật lý: FT232/MAX3232 → `Serial2` (SerialComputer).
>
> Cập nhật: 2026-07-20.

---

## 0.0 NGUỒN SỰ THẬT DUY NHẤT — sửa bản đồ register ở đâu

**Không sửa địa chỉ/hệ số/bit cờ trực tiếp trong code nữa.** Tất cả nằm ở
[`protocol/pc_link.json`](../../protocol/pc_link.json); chạy generator để 3 phía cùng đổi một lượt:

```bash
python protocol/gen_pc_link.py          # sinh lại cả 3
python protocol/gen_pc_link.py --check  # kiểm tra đồng bộ (exit 1 nếu lệch)
```

| Phía | File SINH TỰ ĐỘNG — đừng sửa tay | Ai dùng |
|---|---|---|
| Firmware C++ | `include/PC_Link_Map.h` | `include/PC_Link.h` |
| Tool Python | `tools/pc_link_map.py` | `tools/otl_link.py` (poll + giải mã) |
| Giao diện JS | khối `PC_LINK MAP` trong `OTL Roast Lab.html` | lớp DataSource (mốc theo `progStep`) |

`--check` còn **đối chiếu `progStep` với `#define STP_*` trong `include/Define.h`** — đổi
quy trình rang mà quên cập nhật giao thức là bị chặn ngay. Nó chạy sẵn trong
`python tools/test_otl_link.py` (mục 7).

Bảng dưới đây là **mô tả trên dây** (frame byte thật) để tra tay khi debug; con số gốc
luôn lấy từ JSON.

---

## 0. Tham số link

| Mục | Giá trị | Ghi chú |
|---|---|---|
| Khung UART | **8 data, No parity, 1 stop (8N1)** | chuẩn Modbus RTU |
| Baud | **9600** mặc định | đổi qua HMI (`modbusBaud_R`); khuyến nghị nâng 115200 nếu MAX3232 chịu (xem §6) |
| Slave ID | **1** mặc định | đổi qua HMI (`modbusID_R`) |
| Thứ tự byte | **big-endian** trong mỗi register (hi trước lo) | riêng CRC đi **lo trước, hi sau** |
| Kiểu register | Holding register (func 0x03 đọc, 0x06/0x10 ghi) | |

Toàn bộ ví dụ dưới dùng **ID = 1**. Byte in HEX.

---

## 1. CRC16 (Modbus) — bắt buộc cả 2 chiều

Đa thức `0xA001` (đảo bit của 0x8005), khởi tạo `0xFFFF`. Kết quả ghép vào cuối frame **byte thấp trước, byte cao sau**.

```python
def crc16(data: bytes) -> bytes:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if (crc & 1) else (crc >> 1)
    return bytes([crc & 0xFF, (crc >> 8) & 0xFF])   # lo, hi
```

Nhận frame: tách 2 byte CRC cuối, tự tính CRC phần còn lại, so khớp → sai thì **bỏ frame + đếm lỗi** (không parse).

---

## 2. NHẬN — đọc khối live (STM32 → app)

Đọc **15 register liền khối** (100–114) trong **1 frame** → toàn bộ số live 1 vòng round-trip.

### 2.1 Request (app gửi)

```
ID   FUNC  ADDR_HI ADDR_LO  QTY_HI QTY_LO  CRC_LO CRC_HI
01   03    00      64       00     0F      44     11
```
- FUNC `03` = read holding registers
- ADDR = `0x0064` = **100** (reg đầu khối)
- QTY  = `0x000F` = **15**

**Frame thực tế:** `01 03 00 64 00 0F 44 11`

### 2.2 Response (STM32 trả)

```
ID  FUNC  BYTECNT  [15 × (hi lo)]                              CRC_LO CRC_HI
01  03    1E       ...30 byte dữ liệu...                       xx     xx
```
- BYTECNT = `0x1E` = **30** (15 reg × 2 byte)

**Frame ví dụ** (BT=215.3°C, ET=198.0°C, rorBT=12.50°C/min, gas40 gió55 drum60, SV=210.0, áp=−30Pa, step=9, roast=754s, phase=DEV, flags=0x42, hb=123):

```
01 03 1E  08 69  07 BC  04 E2  00 00  00 00  00 28  00 37  00 3C
          08 34  FF E2  00 09  02 F2  00 07  00 42  00 7B   29 9C
```

### 2.3 Giải mã (offset trong response, byte đầu dữ liệu = index 3)

| Reg | Offset byte | Tên | Công thức → giá trị thật | Kiểu |
|---|---|---|---|---|
| 100 | 3–4  | BT      | `raw / 10` °C            | uint16 |
| 101 | 5–6  | ET      | `raw / 10` °C            | uint16 |
| 102 | 7–8  | rorBT   | `int16(raw) / 100` °C/min | **có dấu** |
| 103 | 9–10 | rorET   | `int16(raw) / 100`       | có dấu |
| 104 | 11–12| rorBT_pro | `int16(raw) / 100`     | có dấu |
| 105 | 13–14| gas     | `raw` %                  | uint16 |
| 106 | 15–16| gió     | `raw` %                  | uint16 |
| 107 | 17–18| drum    | `raw` %                  | uint16 |
| 108 | 19–20| SV_BT   | `raw / 10` °C            | uint16 |
| 109 | 21–22| áp hút  | `int16(raw)` Pa (âm=hút) | **có dấu** |
| 110 | 23–24| progStep| `raw`                    | uint16 |
| 111 | 25–26| roast   | `raw` giây               | uint16 |
| 112 | 27–28| phase   | bit0=Dry, bit1=Maillard, bit2=DEV | bitmask |
| 113 | 29–30| flags   | xem §4                   | bitmask |
| 114 | 31–32| heartbeat | `raw` tăng 1 mỗi vòng loop | uint16 |

> **Có dấu:** ép kiểu `int16` trước khi chia. Python: `v-0x10000 if v>=0x8000 else v`.
> **Heartbeat:** nếu 2 lần đọc liên tiếp mà reg 114 KHÔNG đổi → firmware treo/mất nhịp → cảnh báo.

---

## 3. TRUYỀN — ghi điều khiển (app → STM32)

Chỉ có tác dụng khi **nút PC control trên HMI đang bật** (`PC_CONTROL_BTN_R == 1`). Tắt → STM32 bỏ qua lệnh ghi (và tự phản chiếu setpoint máy vào khối 120–130 để app hiển thị đúng).

Khối ghi **liền mạch 120–130** (11 reg):

| Reg | Addr hex | Lệnh | Miền hợp lệ | Mã hóa |
|---|---|---|---|---|
| 120 | 0x0078 | gas    | 0–100 | `%` |
| 121 | 0x0079 | gió    | 0–100 | `%` |
| 122 | 0x007A | drum   | 0–100 | `%` |
| 123 | 0x007B | SV     | 0–3000 | `°C × 10` |
| 124 | 0x007C | vacuum SV | 90–250 | `Pa` |
| 125 | 0x007D | ignition (gas on/off) | 0/1 | |
| 126 | 0x007E | charge | 0/1 | |
| 127 | 0x007F | drop   | 0/1 | |
| 128 | 0x0080 | escape | 0/1 | |
| 129 | 0x0081 | cool   | 0/1 | |
| 130 | 0x0082 | auto (START) | 0/1 | ⚠ bật rang tự động từ xa |

STM32 **edge-gate**: chỉ áp dụng ô nào app vừa ĐỔI giá trị (so với vòng trước). Kẹp miền ngay tại firmware. charge/drop/escape kèm timer tự đóng + buzzer.

### 3.1 Ghi 1 register — func 0x06

```
ID  FUNC  ADDR_HI ADDR_LO  VAL_HI VAL_LO  CRC_LO CRC_HI
```
- **Ví dụ gió = 55%** (reg 121=0x0079, val=0x0037): `01 06 00 79 00 37 19 C5`
- **Ví dụ charge = 1** (reg 126=0x007E, val=0x0001): `01 06 00 7E 00 01 28 12`

Response của 0x06 là **echo lại y hệt request** (8 byte). Khớp = ghi OK.

### 3.2 Ghi nhiều register 1 lần — func 0x10 (khuyến nghị cho nhóm setpoint)

Đẩy cả gas/gió/drum/SV/vacuum trong 1 frame:

```
ID  FUNC  ADDR_HI ADDR_LO  QTY_HI QTY_LO  BYTECNT  [N × (hi lo)]  CRC_LO CRC_HI
```
- **Ví dụ** ghi reg 120–124 = {gas 40, gió 55, drum 60, SV 2100, vacuum 150}:

```
01 10 00 78 00 05 0A  00 28  00 37  00 3C  08 34  00 96  52 87
```
- ADDR=`0x0078`(120), QTY=`0x0005`, BYTECNT=`0x0A`(10 byte)

Response 0x10 = `ID 10 ADDR_HI ADDR_LO QTY_HI QTY_LO CRC_LO CRC_HI` (8 byte): `01 10 00 78 00 05 ...`.

> **Nút bấm (125–130) nên dùng 0x06 riêng lẻ** — bấm cái nào ghi cái đó, tránh vô tình đổi nút khác.

---

## 4. Bit của reg 113 (flags)

| Bit | Mask | Ý nghĩa |
|---|---|---|
| 0 | 0x01 | AUTO đang chạy (START_BTN_R) |
| 1 | 0x02 | GAS đang bật (START_GAS_BTN_R) |
| 2 | 0x04 | CHARGE |
| 3 | 0x08 | DROP |
| 4 | 0x10 | ESCAPE |
| 5 | 0x20 | COOL |
| 6 | 0x40 | PC_CONTROL đang bật (app được phép điều khiển) |

Ví dụ `0x42` = bit1+bit6 = GAS bật + PC control bật.

---

## 5. Vòng poll khuyến nghị (master bên PC)

```
mỗi 250 ms (4 Hz):
    1. reset buffer vào
    2. gửi READ req (01 03 00 64 00 0F 44 11)
    3. đọc ĐÚNG 5 + 30 = 35 byte  (ID+FUNC+BYTECNT + 30 data + 2 CRC)
    4. kiểm CRC → sai thì bỏ + errors++; đúng thì parse theo §2.3, errors=0
    5. so heartbeat (reg 114) với lần trước → không đổi thì cũng cảnh báo
    6. nếu errors >= 5 → auto-reconnect cổng COM

khi user chỉnh setpoint / bấm nút trên app  → chèn 0x06 hoặc 0x10 giữa 2 vòng poll
```

Số byte response cố định: **READ 15 reg → 35 byte**; `0x06 → 8 byte`; `0x10 → 8 byte`. Đọc đúng số byte, đừng dùng readline.

---

## 6. Ghi chú tốc độ & an toàn

- **Latency timer FT232 = 1 ms** (Device Manager → COM → Advanced): giảm sàn trễ 16→1 ms, quan trọng hơn cả baud.
- **Baud:** 9600 mặc định an toàn; nâng lên 115200 được nếu MAX3232 + cáp sạch (MAX3232 trần ~235 kbps). Nâng baud phải đổi cả `modbusBaud_R` trên HMI cho khớp.
- **reg 130 (AUTO)** cho phép bật rang tự động từ xa — cân nhắc có mở cho app không; firmware vẫn là chốt an toàn cuối.
- Khi PC control TẮT, mọi lệnh ghi bị bỏ qua — app chỉ đọc.

---

## Liên quan
- [include/PC_Link.h](../../include/PC_Link.h) — firmware slave-side.
- [include/Modbus_Slave.h](../../include/Modbus_Slave.h) — map Artisan (reg 0–26), chạy song song.
