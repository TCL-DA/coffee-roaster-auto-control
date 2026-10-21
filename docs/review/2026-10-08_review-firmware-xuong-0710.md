# Review an toàn 3 commit firmware ngày 07/10/2026 + kiểm trước khi nạp

Soạn 08/10/2026 (đêm, Claude). Phạm vi: `51eba14` (bíp khi bấm nhanh, đồ thị bật sớm, max RoR + mốc lên HMI),
`d9b59e7` (tắt đồ thị trễ sau Drop), `6e33f60` (giữ mốc 15 s). Chỉ đọc mã + build, **không nạp, không sửa mã**.

## Kết luận

**Không có lỗi chặn nạp.** Một điểm nên sửa trước khi giao máy khách (mục 1), các mục còn lại nhẹ hoặc có từ trước.

## Phát hiện

| # | Mức | Chỗ | Vấn đề | Đề nghị |
|---|---|---|---|---|
| 1 | Vừa | `Modbus_Master.h` `readWriteDrumINV()` | Ghi tần số trống hụt thì **thử lại mãi** mỗi ~2 s (SV BT thì có trần 3 lần). Nếu biến tần trả lời lệnh đọc nhưng lệnh ghi bị quá giờ (2 s), vòng lặp đứng 2 s lặp lại liên tục: HMI chậm, đọc nhiệt thưa. Không cắt gas (xem "Đã kiểm") nhưng báo STT 284 liên tục. | Thêm trần 3 lần như SV BT; hết trần thì bỏ, chờ thợ đổi tốc độ mới ghi lại. |
| 2 | Nhẹ | `Program.h` `roastMarkTask()` | `sentMax` / `sentSec` cập nhật kể cả khi ghi HMI thất bại → HMI giữ số cũ tới lần đổi sau. | Chỉ cập nhật khi `writeSingleRegister` trả `ku8MBSuccess`. |
| 3 | Nhẹ | `roastMarkTask()` | Hai mốc cách nhau < 15 s thì mốc trước bị ghi đè trên W40046…49 (thực tế rang không xảy ra). | Ghi nhận, không cần sửa. |
| 4 | Nhẹ — có từ trước | `Program.h` ~dòng 222–236 (dự đoán giờ Yellow / FCs, chạy trong ngắt 1 s) | Chia cho `rorBT/10`: RoR < 0,1 °C/phút (thang ×100 < 10) thì chia cho 0. Cortex-M3 mặc định trả 0, không treo, nhưng số dự đoán sai; RoR âm (crash) cho số âm. | Chặn `rorBT/10 > 0` trước khi chia. |
| 5 | Nhẹ — có từ trước | `Modbus_Master.h` khởi động (~1305) | In `SerialComputer` lúc kiểm thẻ SD không có `if(enDebug)` (quy ước CLAUDE.md). Chỉ lúc khởi động. | Bọc `if(enDebug)`. |

Hai lỗi tìm ra ở **HMI / Lua** khi soát web (không phải firmware): Lua ghi giây Drop = 0 và đồng hồ giây của Lua chậm ~6 %.
Web đã tự bù; sửa gốc ở đợt HMI sau (xem bộ nhớ phiên 08/10).

## Đã kiểm, đạt

- **ISR** `timerPoll_1000ms` (173 dòng): không Serial, không Modbus, không `delay`, không SD. `roastMarkTask()` và `setTrendSample()` chỉ gọi từ `loop()` / `programScan()`.
- **Cắt gas do lỗi Modbus**: ghi trống hụt gọi `modbusNoteFailure(MB_DEV_DRUM)`, nhưng lệnh đọc trống thành công ngay trước đó đã đặt lại bộ đếm → không bao giờ đủ 5 lần liên tiếp → không cắt gas nhầm. Lỗi đọc thật vẫn cắt như cũ.
- **Mốc giả**: các ô `*_SAVE` (profileData) chỉ được ghi trong lúc rang (Charge / TP / Yellow / FCs / Drop, xoá ở STP_DATA); không có chỗ đọc SD nào ghi vào → chọn hồ sơ hay khởi động không phát mốc giả.
- **Tắt đồ thị trễ**: huỷ / reset gọi `trendStopCancel()` rồi tắt ngay; bật mẻ mới huỷ hẹn tắt. `reset_update()` tắt lại một lần nữa — vô hại.
- **SV BT**: thử tối đa 3 lần, `svRetry` đặt lại khi thành công hoặc bỏ.
- **Gas**: `maxGasSet_R` chặn 0…100 (`Modbus_Master.h:302-303`); giới hạn tốc độ đổi gas còn nguyên (tăng 100 %/3 s, giảm 100 %/5 s, `AnalogConfig.h`).

## Checklist trước khi nạp (release-check)

```
🚀 RELEASE CHECK — OTL-30A cacao (6e33f60)

✅ Build success (pio run -e genericSTM32F103RC)
✅ RAM 73,0 % (35 900 / 49 152 B), Flash 40,7 % (106 720 / 262 144 B)
✅ enDebug = 0 trong mã nguồn (Define.h:131) — board bàn đang chạy bản enDebug=1, NHỚ nạp lại bản sạch khi giao
✅ maxGasSet_R chặn 0…100; giới hạn tốc độ gas còn
✅ PC_CONTROL mặc định 0 (dAddress khởi tạo 0); ID / baud Artisan lấy từ ô HMI — kiểm trên panel
⚠  Timer van (charge / drop / escape / làm mát) là ô $M trên HMI — không kiểm được bằng mã, xem trên panel
✅ Biến thể V400 (Config.h:48), cờ máy M03: relay IO, cân, áp hút, 30 kg
✅ Không còn mã thử: delay(1000) duy nhất là tiếng bíp sẵn sàng lúc khởi động
✅ include/ và src/ sạch so với 6e33f60 (repo còn file khác chưa commit — skills, tools — không vào firmware)

KẾT QUẢ: PASS có điều kiện — nạp được; nên sửa mục 1 trước bản giao khách.
```
