# Ánh xạ spec ↔ code & cách sửa an toàn

## 1. Bảng dòng code

`include/Program.h` — số dòng tại 2026-07-30. Khi code dịch chuyển, tìm bằng `Grep` theo `case STP_` hoặc theo comment mốc thay vì tin số dòng.

| Phần spec | Dòng | Neo tìm kiếm |
|---|---|---|
| Vào `programScan()` | 1388 | `void programScan(){` |
| Bật cưỡng chế trống/quạt | 1390 | `forceDrumFanOnFlag` |
| Cắt gas an toàn | 1406 | `fireCutFlag` |
| Gọi `preheat()` | 1424 | `if (START_BTN_R == 0)` |
| Mở switch chính | 1446 | `if(START_BTN_R == 1){` |
| `STP_DATA` | 1448 | `case STP_DATA:` |
| `STP_COOL_DOWN` | 1514 | `case STP_COOL_DOWN:` |
| `STP_GAS` | 1536 | `case STP_GAS:` |
| `STP_CHECK` | 1556 | `case STP_CHECK:` |
| `STP_CHARGE` | 1576 | `case STP_CHARGE:` |
| `STP_TP` | 1621 | `case STP_TP:` |
| `STP_YELLOW` | 1642 | `case STP_YELLOW:` |
| `STP_FCS` | 1656 | `case STP_FCS:` |
| `STP_DEV` | 1670 | `case STP_DEV:` |
| `STP_LOOP_1` | 1679 | `case STP_LOOP_1:` |
| `STP_LOOP_2` | 1715 | `case STP_LOOP_2:` |
| Bật đồ thị sớm | 1739 | `trendPreStarted` |
| Kích auto-loader ở FCS | 1748 | `if(progStep==STP_FCS)` |
| Khối DROP | 1771 | `//Check drop` |
| Khối huỷ / AB kích | 1839 | `if(progStep>=1){` |
| `aLoaderStep` switch | 1878 | `switch(aLoaderStep)` |
| Cắt feeder theo cân | 1970 | `netW100 <= ((int32_t)difNetW` |
| Timer charge | 2090 | `Auto close charge` |
| Timer drop | 2109 | `Auto close drop` |
| Timer AB | 2133 | `Auto close AB` |
| Huỷ chuỗi cooling | 2151 | `Huỷ quy trình cooling` |
| Timer destoner | 2163 | `Auto close destoner` |
| Escape khi có PC | 2181 | `if(PC_CONTROL_BTN_R==1)` |
| Điều hướng `naviSource*` | 2203 | `Điều hướng gas analog source` |
| `abStep` switch | 2233 | `switch(abStep)` |
| `coolStep` switch | 2268 | `switch(coolStep)` |

Hằng số state: `include/Define.h` dòng 226–251. Bộ đếm giây: `timerPoll_1000ms()` (ISR, xem `[[feedback_isr_no_modbus]]`).

## 2. Checklist khi **thêm một bước** vào `progStep`

Bước mới nên nhận **số chưa dùng** (2, hoặc 15 trở lên) thay vì chèn giữa, vì HMI và app OTL Roast Lab đọc `progStep` theo giá trị số và nhiều chỗ so sánh theo thứ tự (`progStep >= STP_YELLOW`, `progStep < STP_LOOP_1`, `STP_GAS ≤ progStep < STP_TP`).

1. `Define.h`: thêm `#define STP_...` — **không** đổi số của bước cũ.
2. `Program.h`: thêm `case`, đặt `STEP_STRING` (nhãn HMI) và `setMachineStatus(STT_...)`.
3. Sửa bước trước để trỏ sang bước mới; sửa bước mới để trỏ tiếp.
4. **Soát mọi so sánh khoảng** `progStep` xem bước mới có rơi đúng bên trong/ngoài:
   ```
   Grep "progStep\s*[<>=]" include/Program.h
   ```
   Đặc biệt: `progStep >= STP_YELLOW` (bật khối DROP), `progStep < STP_LOOP_1` (còn trong mẻ), `progStep >= STP_TP` (cho phép AB), `progStep >= 1` (khối huỷ).
5. Nếu bước mới cần trạng thái mới thì thêm `STT_*` và báo để cập nhật app/HMI.
6. Cập nhật `quy-trinh-chinh.md` (khối bước + bản đồ) và bảng tóm tắt `rang-ca-phe/references/roast-flow.md`.

## 3. Checklist khi **thêm timeout** cho một bước

Đây là loại sửa hay cần nhất. Khuôn mẫu khớp với code hiện có:

1. Thêm biến đếm + cờ vào `Define.h` (kiểu `int16_t`, cặp `xxxTi` / `xxxTiEn`) — chú ý RAM, STM32F103RC chỉ 48 KB và ngưỡng nguy hiểm là RAM tĩnh > 88 %, xem `[[reference_ram_threshold]]`.
2. Tăng biến trong `timerPoll_1000ms()` khi cờ bật (chỉ tăng, **không** Modbus/SD/delay trong ISR).
3. Bật cờ ở lối **vào** bước; reset cờ + biến ở lối **ra** (mọi lối ra).
4. Nhánh hết giờ: đặt an toàn trước (tắt gas nếu liên quan lửa), `setMachineStatus(STT_...)` báo lỗi rõ nguyên nhân, rồi mới chuyển bước.
5. Đưa ngưỡng thành `#define` (hoặc thanh ghi `$M` nếu chủ máy cần chỉnh trên HMI) — đừng chôn số trần trong `if`.

## 4. Bẫy đã gãy thật, đừng lặp lại

- **Ghi thanh ghi HMI lệch 1**: hầu hết lệnh ghi dùng `nodeHMI.writeSingleRegister(XXX_W - 1, v)` (địa chỉ ghi trừ 1), nhưng các ô cấu hình dùng `XXX_W + 2000` (ví dụ `maxGasSet_W + 2000`, `loop_W + 2000`, `vacuumSetFlag_W + 2000`). Copy dòng lệnh từ chỗ khác thì soát lại đúng dạng.
- **Quên reset ô lệnh PC**: sau khi tự đóng charge/drop/escape phải `Charge_btn_PC = 0; mbs.Hreg(CHARGE_artisan_W, 0);` — nếu không, lệnh kế tiếp từ app bị coi là "không đổi" và mất tác dụng.
- **`delay(1)` sau lệnh ghi Modbus** là cố ý (giãn bus), không phải rác — đừng dọn.
- **Khối đọc/ghi PC_Link không được đè nhau**: reg đọc 100–121, ghi 140–160. Đã có lần khối đọc đè base 120 làm gas/gió chết, xem `[[project_pc_link]]`.
- **Không thêm việc nặng vào giữa switch**: vòng loop đang ~130 ms, `mbs.task()` được gọi sau `programScan()` để app không bị treo lúc ghi SD. Thêm ghi SD trong case là kéo dài loop, xem `[[project_loop_latency]]`.
- **`preheat()` và rang loại trừ nhau** qua `START_BTN_R`. Thêm bước sấy vào quy trình rang thì phải quyết ai giữ quyền gas, không được để hai bộ cùng ghi.

## 5. Sau khi sửa

1. Build + kiểm RAM/Flash: skill `flash-build`.
2. Soát cờ nguy hiểm trước khi nạp máy thật: skill `release-check` (`enDebug`, trần gas, timing).
3. Trace lại luồng bằng skill `state-trace` nếu có log serial.
4. Ghi dòng mới vào "Lịch sử sửa quy trình" của file spec đã sửa.
