# Hướng Dẫn Waveshare Modbus RTU Relay (C)

Tài liệu này dùng cho AI, lập trình viên hoặc kỹ thuật viên khi cấu hình và điều khiển board **Waveshare Modbus RTU Relay (C)** qua **RS485 Modbus RTU**.

Mục tiêu chính:

- Hiểu nhanh cách đấu nối và nguyên lý relay.
- Cài board về cấu hình chuẩn của dự án: **slave ID = 7**, **baudrate = 38400**, **8N1**.
- Đọc trạng thái relay và điều khiển từng relay hoặc toàn bộ relay.
- Tránh lỗi phổ biến khi AI/chương trình tự động điều khiển relay.

---

## 1. Cấu Hình Chuẩn Của Dự Án

```yaml
device: Waveshare Modbus RTU Relay (C)
protocol: Modbus RTU
physical_layer: RS485
serial_config: 8N1
baudrate: 38400
slave_id: 7
relay_count: 8
relay_type: latching relay
```

Thông số mặc định thường gặp khi mới nhận module:

```yaml
default_baudrate: 9600
default_slave_id: 3
```

Nguồn cấp module:

```text
DC 7-36V
```

---

## 2. Nguyên Lý Relay Cần Nhớ

Relay trên board là **tiếp điểm đóng/ngắt**, không tự cấp điện ra tải.

Ví dụ điều khiển đèn 220VAC:

```text
L 220VAC  -> COM relay
NO relay  -> L của đèn
N 220VAC  -> N của đèn
```

Không được hiểu nhầm rằng chân `NO/NC/COM` tự xuất ra 220VAC hoặc 24VDC.

Board dùng **latching relay**, nên trạng thái relay có thể vẫn được giữ sau khi mất điện. Khi chương trình khởi động lại, nên làm theo quy trình an toàn:

```text
1. Đọc trạng thái relay hiện tại.
2. So sánh với trạng thái mong muốn.
3. Gửi lệnh ON hoặc OFF rõ ràng để đưa relay về trạng thái an toàn.
4. Đọc lại trạng thái để xác nhận.
```

---

## 3. Đấu Nối RS485

```text
Master RS485 A  ->  Board RS485 A
Master RS485 B  ->  Board RS485 B
GND             ->  Nối chung nếu hệ thống yêu cầu chung mass
```

Lưu ý:

- Không nối UART TTL trực tiếp vào chân A/B RS485.
- Nếu dùng STM32, ESP32, Arduino, Raspberry Pi hoặc máy tính, cần bộ chuyển đổi RS485 phù hợp.
- Nếu không có phản hồi, thử kiểm tra khả năng bị đảo A/B.

---

## 4. Địa Chỉ Relay

Trong Modbus, relay đầu tiên bắt đầu từ địa chỉ coil `0x0000`.

| Relay | Địa chỉ coil |
|---:|---:|
| Relay 1 / CH1 | `0x0000` |
| Relay 2 / CH2 | `0x0001` |
| Relay 3 / CH3 | `0x0002` |
| Relay 4 / CH4 | `0x0003` |
| Relay 5 / CH5 | `0x0004` |
| Relay 6 / CH6 | `0x0005` |
| Relay 7 / CH7 | `0x0006` |
| Relay 8 / CH8 | `0x0007` |
| Tất cả relay | `0x00FF` |

---

## 5. Function Code Cần Dùng

| Function code | Tên | Mục đích |
|---:|---|---|
| `01` | Read Coils | Đọc trạng thái relay |
| `03` | Read Holding Registers | Đọc register cấu hình |
| `05` | Write Single Coil | Ghi một relay |
| `06` | Write Single Register | Ghi một register cấu hình |
| `0F` | Write Multiple Coils | Ghi nhiều relay cùng lúc |

Giá trị điều khiển khi dùng function `05`:

| Giá trị | Ý nghĩa |
|---:|---|
| `FF 00` | Bật relay |
| `00 00` | Tắt relay |
| `55 00` | Đảo trạng thái relay |

Khuyến nghị cho AI/chương trình tự động: **ưu tiên ON/OFF rõ ràng, hạn chế dùng TOGGLE** vì toggle phụ thuộc trạng thái hiện tại.

---

## 6. Cấu Trúc Frame Modbus RTU

Frame ghi một relay hoặc một register:

```text
[Slave ID] [Function] [Address Hi] [Address Lo] [Data Hi] [Data Lo] [CRC Lo] [CRC Hi]
```

Ví dụ bật relay 1 khi slave ID = `03`:

```text
03 05 00 00 FF 00 8D D8
```

Giải thích:

```text
03       = slave ID
05       = Write Single Coil
00 00    = địa chỉ relay 1
FF 00    = bật relay
8D D8    = CRC16 Modbus, low byte trước
```

CRC Modbus RTU luôn gửi **low byte trước, high byte sau**.

---

## 7. Cài Module Về ID 7 Và Baudrate 38400

Giả định module đang ở cấu hình mặc định:

```text
Baudrate: 9600
Serial:   8N1
Slave ID: 3
```

### Bước 1: Đổi slave ID từ 3 sang 7

Gửi ở cấu hình **9600, 8N1, ID = 3**:

```text
03 06 40 00 00 07 DC 2A
```

Ý nghĩa:

```text
03       = slave ID hiện tại
06       = Write Single Register
40 00    = register đổi slave ID
00 07    = slave ID mới = 7
DC 2A    = CRC
```

Sau lệnh này, board sẽ dùng **ID = 7**.

### Bước 2: Đổi baudrate từ 9600 sang 38400

Gửi ở cấu hình **9600, 8N1, ID = 7**:

```text
07 06 20 00 00 03 C2 6D
```

Ý nghĩa:

```text
07       = slave ID mới
06       = Write Single Register
20 00    = register đổi baudrate
00 03    = mã baudrate 38400
C2 6D    = CRC
```

Sau lệnh này, đổi master sang:

```text
Baudrate: 38400
Serial:   8N1
Slave ID: 7
```

Nếu không thấy phản hồi sau khi đổi baudrate, ngắt nguồn module rồi cấp lại.

---

## 8. Register Cấu Hình

### Baudrate

Register:

```text
0x2000
```

| Giá trị | Baudrate |
|---:|---:|
| `00 00` | 4800 |
| `00 01` | 9600 |
| `00 02` | 19200 |
| `00 03` | 38400 |
| `00 04` | 57600 |
| `00 05` | 115200 |
| `00 06` | 128000 |
| `00 07` | 256000 |

Ví dụ set baudrate 38400, ID = 7:

```text
07 06 20 00 00 03 C2 6D
```

### Slave ID

Register:

```text
0x4000
```

Giá trị hợp lệ:

```text
1-255
```

Ví dụ đổi ID từ 3 sang 7:

```text
03 06 40 00 00 07 DC 2A
```

---

## 9. Lệnh Test Sau Khi Cài ID 7, Baudrate 38400

Tất cả frame trong phần này gửi ở:

```text
38400, 8N1, slave ID 7
```

### Đọc trạng thái 8 relay

```text
07 01 00 00 00 08 3D AA
```

Response mẫu khi tất cả relay OFF:

```text
07 01 01 00 50 48
```

Response mẫu khi relay 1 ON:

```text
07 01 01 01 91 88
```

Cấu trúc response:

```text
07 01 01 [STATUS] [CRC Lo] [CRC Hi]
```

Ý nghĩa byte `STATUS`:

| Bit | Relay |
|---:|---|
| bit 0 | Relay 1 |
| bit 1 | Relay 2 |
| bit 2 | Relay 3 |
| bit 3 | Relay 4 |
| bit 4 | Relay 5 |
| bit 5 | Relay 6 |
| bit 6 | Relay 7 |
| bit 7 | Relay 8 |

Ví dụ:

```text
STATUS = 01 hex -> Relay 1 ON
STATUS = 03 hex -> Relay 1 và Relay 2 ON
STATUS = FF hex -> Relay 1 đến Relay 8 đều ON
```

### Điều khiển relay 1

```text
Bật relay 1:
07 05 00 00 FF 00 8C 5C

Tắt relay 1:
07 05 00 00 00 00 CD AC

Đảo trạng thái relay 1:
07 05 00 00 55 00 F2 FC
```

### Điều khiển tất cả relay

Dùng địa chỉ đặc biệt `0x00FF`.

```text
Bật tất cả relay:
07 05 00 FF FF 00 BD 8C

Tắt tất cả relay:
07 05 00 FF 00 00 FC 7C

Đảo trạng thái tất cả relay:
07 05 00 FF 55 00 C3 2C
```

---

## 10. Ghi Nhiều Relay Bằng Function 0F

Cấu trúc:

```text
[ID] [0F] [Start Address Hi] [Start Address Lo] [Quantity Hi] [Quantity Lo] [Byte Count] [Data] [CRC Lo] [CRC Hi]
```

Với 8 relay, bắt đầu từ relay 1:

```text
Start Address: 00 00
Quantity:      00 08
Byte Count:    01
Data:          bit mask relay
```

Frame mẫu:

```text
Bật tất cả relay:
07 0F 00 00 00 08 01 FF BF 53

Tắt tất cả relay:
07 0F 00 00 00 08 01 00 FF 13

Bật relay 1 và 2, tắt relay 3-8:
07 0F 00 00 00 08 01 03 BE D3
```

Cách hiểu byte data:

```text
00 hex -> tất cả OFF
01 hex -> chỉ relay 1 ON
03 hex -> relay 1 và 2 ON
05 hex -> relay 1 và 3 ON
FF hex -> relay 1 đến 8 đều ON
```

---

## 11. Hàm Tính CRC16 Modbus Bằng Python

Dùng hàm này để tạo frame Modbus RTU từ chuỗi hex chưa có CRC.

```python
def modbus_crc16(data: bytes) -> int:
    crc = 0xFFFF

    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
            crc &= 0xFFFF

    return crc


def build_frame(hex_without_crc: str) -> str:
    data = bytes.fromhex(hex_without_crc)
    crc = modbus_crc16(data)
    crc_low = crc & 0xFF
    crc_high = (crc >> 8) & 0xFF
    full = data + bytes([crc_low, crc_high])
    return " ".join(f"{byte:02X}" for byte in full)


print(build_frame("07 05 00 00 FF 00"))
# Output: 07 05 00 00 FF 00 8C 5C
```

---

## 12. Quy Trình Test Khuyến Nghị

Khi module đang ở cấu hình mặc định **ID = 3, baudrate = 9600**:

1. Kết nối RS485 và cấp nguồn module.
2. Mở phần mềm test Modbus/serial ở `9600, 8N1, ID 3`.
3. Test relay 1:

```text
Bật relay 1:
03 05 00 00 FF 00 8D D8

Tắt relay 1:
03 05 00 00 00 00 CC 28
```

4. Đổi ID sang 7:

```text
03 06 40 00 00 07 DC 2A
```

5. Đổi baudrate sang 38400:

```text
07 06 20 00 00 03 C2 6D
```

6. Đổi master sang `38400, 8N1, ID 7`.
7. Đọc trạng thái 8 relay:

```text
07 01 00 00 00 08 3D AA
```

8. Test lại relay 1:

```text
Bật relay 1:
07 05 00 00 FF 00 8C 5C

Tắt relay 1:
07 05 00 00 00 00 CD AC
```

---

## 13. Checklist Xử Lý Lỗi

### Không thấy phản hồi

Kiểm tra theo thứ tự:

```text
1. Đúng COM port chưa?
2. Đúng baudrate chưa?
3. Đúng 8N1 chưa?
4. Đúng slave ID chưa?
5. A/B RS485 có bị đảo không?
6. Board đã có nguồn DC 7-36V chưa?
7. Frame có gửi dạng HEX thật không, hay đang gửi ASCII text?
8. CRC đã đúng chưa?
```

### Đã đổi baudrate nhưng mất kết nối

Thử:

```text
1. Đổi master sang baudrate mới.
2. Giữ nguyên slave ID mới.
3. Ngắt nguồn module rồi cấp lại.
4. Gửi lệnh đọc trạng thái.
```

Ví dụ sau khi đổi sang **38400, ID = 7**:

```text
07 01 00 00 00 08 3D AA
```

### Không chắc ID hoặc baudrate hiện tại

Scan ID từ `1` đến `255` ở các baudrate phổ biến:

```text
9600
19200
38400
57600
115200
```

Frame scan có thể dùng lệnh đọc 8 relay:

```text
[ID] 01 00 00 00 08 [CRC Lo] [CRC Hi]
```

---

## 14. Tóm Tắt Cho AI

```yaml
device: Waveshare Modbus RTU Relay (C)
protocol: Modbus RTU over RS485
baudrate: 38400
serial_config: 8N1
slave_id: 7
relay_count: 8
relay_1_address: 0x0000
all_relays_address: 0x00FF

commands:
  read_all_relays: "07 01 00 00 00 08 3D AA"
  relay_1_on:      "07 05 00 00 FF 00 8C 5C"
  relay_1_off:     "07 05 00 00 00 00 CD AC"
  relay_1_toggle:  "07 05 00 00 55 00 F2 FC"
  all_relays_on:   "07 05 00 FF FF 00 BD 8C"
  all_relays_off:  "07 05 00 FF 00 00 FC 7C"

setup_from_default:
  default_baudrate: 9600
  default_slave_id: 3
  set_id_to_7:       "03 06 40 00 00 07 DC 2A"
  set_baud_to_38400: "07 06 20 00 00 03 C2 6D"
```

Quy tắc an toàn cho AI:

- Không dùng `toggle` nếu chưa đọc trạng thái relay hiện tại.
- Luôn ưu tiên lệnh ON/OFF rõ ràng.
- Sau khi ghi relay, đọc lại trạng thái để xác nhận.
- Không điều khiển tải AC nếu chưa xác nhận đấu nối, cách ly, cầu chì và dòng tải phù hợp.
- Khi khởi động chương trình, luôn đưa relay về trạng thái an toàn mong muốn.
