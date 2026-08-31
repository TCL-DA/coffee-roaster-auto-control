---
name: modbus-audit
description: Kiểm tra toàn bộ Modbus calls trong dự án: địa chỉ register, error handling, timeout, node ID. Phát hiện địa chỉ sai, thiếu xử lý lỗi, ghi đè không cần thiết.
allowed-tools: Read, Grep
---

Thực hiện audit toàn bộ giao tiếp Modbus trong dự án OTL-06ALS.

## Bước 1 — Thu thập tất cả Modbus calls

Tìm trong `include/Modbus_Master.h` và `include/Program.h`:
- `readHoldingRegisters(`
- `writeSingleRegister(`
- `writeSingleCoil(`
- `readCoils(`
- `getResponseBuffer(`

Liệt kê từng call: file, dòng, node, địa chỉ, số lượng register.

## Bước 2 — Kiểm tra địa chỉ register

Đọc `include/Define.h` để lấy danh sách `#define *_W` và `#define *_R`.

Với mỗi `writeSingleRegister(ADDR-1, val)`:
- Kiểm tra `ADDR` có được define không
- Xác nhận `-1` offset (Delta HMI dùng 1-based, ModbusMaster dùng 0-based)
- Cảnh báo nếu dùng địa chỉ literal (magic number) thay vì macro

Với mỗi `readHoldingRegisters(fst_address, Numaddress)`:
- Kiểm tra range `fst_address` đến `fst_address+Numaddress-1` có hợp lệ không
- Kiểm tra `getResponseBuffer(i)` có vượt quá `Numaddress` không

## Bước 3 — Kiểm tra error handling

Với mỗi Modbus call, kiểm tra:
```cpp
if(result == node.ku8MBSuccess) { ... }
else { errorCount++; ... }
```

Báo cáo:
- Call nào **thiếu** kiểm tra kết quả
- Call nào có error handler nhưng **không có recovery** (chỉ buzz rồi tiếp tục)
- `errorCount` được reset ở đâu trong loop

## Bước 4 — Kiểm tra timing & delay

Tìm tất cả `delay()` trong Modbus_Master.h và Program.h.
- Tính tổng delay tối đa trong 1 vòng loop
- Cảnh báo nếu tổng > 200ms (ảnh hưởng tới ISR timer accuracy)
- Đặc biệt chú ý `delay(100)` trong error handler (BUZZ_ON/OFF)

## Bước 5 — Kiểm tra node config

Đọc hàm `ModbusRS485Config()` trong Modbus_Master.h:
- Xác nhận slave ID của từng node (nodeBT=1, nodeET=2, nodeDrum=4, nodeAir=5, nodeIORelay=7, nodeHMI=1)
- Lưu ý: `nodeBT` và `nodeHMI` **cùng ID=1** nhưng khác Serial bus — xác nhận điều này
- Kiểm tra `preTransmission` / `postTransmission` callback cho RS485 direction control

## Bước 6 — Tổng kết

Trình bày bảng:
| Vấn đề | Mức độ | File:Dòng | Mô tả |
|--------|--------|-----------|-------|
| Critical | 🔴 | ... | ... |
| Warning  | 🟡 | ... | ... |
| Info     | 🟢 | ... | ... |
