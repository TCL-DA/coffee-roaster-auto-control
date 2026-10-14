---
name: flash-stm32
description: Build RỒI FLASH (upload) firmware lên STM32F103RC thật qua ST-Link cho dự án OTL-06ALS. Dùng khi user nói "flash", "nạp firmware", "build và flash", "upload lên máy", "nạp code lên STM32". Khác flash-build (chỉ build + báo cáo, KHÔNG nạp).
allowed-tools: Bash, Read, Skill
---

Build rồi **NẠP (upload)** firmware lên STM32F103RC thật cho dự án OTL-06ALS.

> ⚠️ Đây là thao tác GHI LÊN MÁY THẬT. Firmware sai (debug flags, giới hạn gas,
> timer) khi vận hành có thể gây nguy hiểm. Nếu user chưa chạy `release-check`
> trong phiên này và đang nạp lên máy đang dùng thật, NHẮC họ cân nhắc chạy
> `/release-check` trước (không bắt buộc khi test bench).

## Chọn ENV đúng máy (14/10/2026)

| Máy | Env | Ghi chú |
|---|---|---|
| Gas (mặc định) | `genericSTM32F103RC` | |
| Điện — đồng hồ buồng VX4 | `dien` | BT/ET/biến tần qua cổng loader-cân, VX4 riêng cổng Modbus cũ 9600, gió RS485 45–60 Hz, không tín hiệu lửa — `docs/config/config-dien-vx4.md` |

Biến thể máy MỚI: trả lời hết [bảng hỏi phần cứng](../../../docs/config/CHECKLIST-bien-the-may.md) TRƯỚC khi sửa code.

## Sau khi nạp: ĐỌC COM khởi động (bắt buộc, 15 s)

Cổng debug USB-serial (Prolific, hiện là COM13) 9600: board in `=> BT OK`, `=> ET OK`, … `=> SD OK`. Treo ở dòng lặp:

| Dòng | Nghĩa | Kiểm |
|---|---|---|
| `LOI X \| 0xe2 - Qua thoi gian cho` | KHÔNG ai trả lời | thiết bị có điện? nối đúng CỔNG serial nào? địa chỉ ID? |
| `LOI X \| 0xe0 - Sai ID slave` | CÓ trả lời nhưng khung sai | thường lệch BAUD (VX4 máy điện: 38400 → 0xe0, 9600 → OK) |
| `LOI SD - waiting for card` | thẻ SD | cắm lại thẻ (SD bắt buộc lúc khởi động) |

```
python -c "import serial,time;s=serial.Serial('COM13',9600,timeout=0.5);t=time.time();b=b''
while time.time()-t<15: b+=s.read(4096)
print(b.decode('ascii','ignore')[:1500])"
```
Thử baud / ID khác KHÔNG cần sửa file: `PLATFORMIO_BUILD_FLAGS="-DVX4_SERIAL_BAUD=9600UL" pio run -e dien -t upload`
(các hằng `MACHINE_RS485_BAUD`, `VX4_SERIAL_BAUD`, `VX4_MODBUS_ID` đều `#ifndef`). Tìm ra rồi thì ghi vào env + commit, nạp lại bản chuẩn.

## Đường dẫn PlatformIO (QUAN TRỌNG)

`pio`/`platformio` KHÔNG có trong PATH của shell này. Luôn gọi qua đường dẫn đầy đủ:

```
PIO=~/.platformio/penv/Scripts/platformio.exe
```

Kiểm nhanh: `ls ~/.platformio/penv/Scripts/platformio.exe`. Nếu không có, thử
`"$USERPROFILE/.platformio/penv/Scripts/platformio.exe"`.

## Bước 1 — Build (bắt buộc trước khi flash)

```
"$PIO" run -e genericSTM32F103RC 2>&1 | tail -45
```

**Bẫy đã gặp — `SemanticVersionError: Invalid simple block '...'`:**
Do file cache `.pio/libdeps/genericSTM32F103RC/integrity.dat` giữ lại version spec
CŨ/HỎNG (ví dụ chữ tiếng Việt lọt vào `lib_deps` của `platformio.ini`). Xử lý:
1. Kiểm `platformio.ini` mục `lib_deps` có version lạ không (vd `@^0.1.0 lên`) → sửa sạch.
2. Xoá cache: `rm -f .pio/libdeps/genericSTM32F103RC/integrity.dat`
3. Build lại.

**Nếu BUILD FAILED:** parse các dòng `error:`, trình bày bảng
`| File:Line | Loại | Mô tả | Gợi ý fix |`, **DỪNG** (không flash firmware lỗi).
Bỏ qua warning từ `.pio/libdeps/` (thư viện bên thứ ba, vd `ADDREG redefined`).

**Nếu BUILD SUCCESS:** đọc dòng RAM/Flash từ output:
```
RAM:   [....] XX.X% (used NNNNN bytes from 49152 bytes)
Flash: [....] XX.X% (used NNNNN bytes from 262144 bytes)
```
STM32F103RC ở dự án này: **RAM 48KB (49152)**, Flash 256KB. Ngưỡng:
- 🟢 RAM < 82% (free > ~9KB) — ok
- 🟡 82–88% — chú ý
- 🔴 > 88% (free < 6KB) — nguy hiểm, dễ crash runtime → nhắc chạy `/memory-check`, cân nhắc KHÔNG flash.

## Bước 2 — Flash (upload)

```
"$PIO" run -e genericSTM32F103RC -t upload 2>&1 | tail -35
```

- Board mặc định dùng `upload_protocol = stlink` (OpenOCD hla_swd). Cần **ST-Link cắm
  vào SWD** + máy cấp nguồn. Các protocol khác có sẵn: dfu, serial, jlink, cmsis-dap.
- **Thành công** khi thấy: `** Verified OK **` và `[SUCCESS]`. `Warn: Adding extra
  erase range` là bình thường (không phải lỗi).
- **Thất bại thường gặp:**
  | Triệu chứng | Nguyên nhân | Xử lý |
  |---|---|---|
  | `Error: unable to find CMSIS-DAP` / `open failed` | ST-Link chưa cắm / driver | Cắm ST-Link, kiểm Device Manager |
  | `Error: init mode failed` / `target not halted` | máy chưa cấp nguồn / dây SWD lỏng | cấp nguồn, kiểm SWDIO/SWCLK/GND |
  | treo ở `Programming` | reset/nguồn chập chờn | thử lại, giữ nguồn ổn định |

  Nếu upload lỗi vì cổng/ST-Link, KHÔNG tự đổi `upload_protocol` — báo user kiểm phần cứng.
  | `jtag status contains invalid mode value` / `** Verify Failed **` | đứt giữa chừng (dây SWD / nguồn chập chờn) | ⛔ board có thể đang NẠP DỞ — nạp lại NGAY; vẫn lỗi thì báo user |

## Bước 3 — Tổng kết

```
✅ BUILD + FLASH OK
📦 Flash: XX KB / 256 KB (XX%)
🧠 RAM:   XX KB / 48 KB  (XX%)
🔌 Đã nạp qua ST-Link — Verified OK, target reset.
```

Nếu chỉ cần build + báo cáo RAM/Flash (KHÔNG nạp), dùng skill `flash-build` thay vì skill này.
