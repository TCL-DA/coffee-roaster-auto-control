---
name: quy-trinh-dieu-khien-may-rang
description: Bản đặc tả (spec) TRÌNH TỰ ĐIỀU KHIỂN máy rang OTL — máy trạng thái progStep trong programScan() cùng 3 máy phụ coolStep/abStep/aLoaderStep và toàn bộ timer tự đóng. Đây là NƠI SỬA QUY TRÌNH: sửa spec trong references/ trước, rồi mới áp vào include/Program.h. Dùng skill này bất cứ khi nào người dùng nói "sửa quy trình rang", "đổi trình tự", "thêm bước", "bỏ bước", "thêm timeout", "máy kẹt ở bước nào", "tại sao chưa tự xả", "đổi điều kiện chuyển bước", "auto charge/auto drop/cooling/escape/destoner/afterburner/auto-loader chạy thế nào", hay hỏi bất kỳ điều gì về thứ tự hành động của máy rang tự động — kể cả khi họ không nhắc chữ "state machine" hay "progStep".
allowed-tools: Read, Grep, Edit, Write
---

Skill này giữ **bản đặc tả trình tự điều khiển** máy rang OTL-06ALS: máy muốn làm gì, theo thứ tự nào, với điều kiện nào. Firmware là bản *thực thi* của spec này.

## Vì sao tách spec ra khỏi code

Quy trình rang là thứ chủ máy sửa thường xuyên (thêm chốt an toàn, đổi thứ tự cooling, thêm timeout mồi lửa), còn `programScan()` dài ~1000 dòng và đan xen Modbus/SD/cân. Sửa trực tiếp trong code rất dễ làm rơi một nhánh huỷ timer hoặc một `setMachineStatus`. Nên quy ước:

1. **Sửa spec trước** trong `references/` — bàn cho xong logic ở dạng người đọc được.
2. **Rồi áp vào code** theo bảng ánh xạ trong [references/anh-xa-code.md](references/anh-xa-code.md).
3. Ghi ngày + lý do vào mục "Lịch sử sửa quy trình" ở cuối file spec tương ứng.

Nếu spec và code lệch nhau thì **code là sự thật, spec là ý định** — phát hiện lệch thì báo người dùng chọn: sửa code cho khớp spec, hay cập nhật spec cho khớp code.

## Tài nguyên

| File | Nội dung | Khi nào đọc |
|------|----------|-------------|
| [references/quy-trinh-chinh.md](references/quy-trinh-chinh.md) | 13 bước `progStep` — entry / hành động / điều kiện thoát của từng bước, khối DROP, khối chạy trước switch | Mọi câu hỏi/sửa đổi về trình tự rang |
| [references/quy-trinh-phu.md](references/quy-trinh-phu.md) | 3 máy phụ (`coolStep`, `abStep`, `aLoaderStep`) + toàn bộ timer tự đóng & nhánh huỷ | Làm mát, escape, destoner, afterburner, auto-loader, xy-lanh tự đóng |
| [references/anh-xa-code.md](references/anh-xa-code.md) | Spec ↔ dòng code trong `Program.h`, checklist khi thêm/sửa/xoá bước, các bẫy hay gãy | Trước khi sửa `Program.h` |
| [references/rui-ro-va-de-xuat.md](references/rui-ro-va-de-xuat.md) | Chỗ có nguy cơ kẹt, đề xuất timeout — **danh sách việc còn mở** | Người dùng hỏi "máy kẹt", "nên thêm gì" |
| [references/quyet-dinh-cho-code.md](references/quyet-dinh-cho-code.md) | **Ý ĐỊNH đã chốt nhưng CHƯA CODE** (chốt 2026-07-30): loại hạt `$M17`, dải nhiệt nạp theo loại hạt, charge tay có nút riêng, chuỗi mồi 2 lần bếp NP, cờ lỗi + xoá lỗi `$M18` | Trước khi sửa `Program.h`; khi hỏi "còn nợ gì", "đã chốt cái gì" |

Tra ý nghĩa/đơn vị thanh ghi `$M`: dùng skill `rang-ca-phe` ([registers-M.md](../rang-ca-phe/references/registers-M.md)). Skill đó là **kiến thức nền về rang**; skill này là **trình tự điều khiển**. `rang-ca-phe/references/roast-flow.md` là bản tóm tắt cũ 11 bước — khi sửa spec ở đây, cập nhật luôn file đó nếu nó lệch.

## Quy ước đọc spec

Mỗi bước viết theo khuôn này để so với code không phải suy diễn:

```
### STP_XXX (n) — Tên việc · nhãn HMI "STEP_STRING"
- Vào khi   : điều kiện bước trước chuyển sang
- Làm       : liệt kê hành động, ghi rõ thanh ghi/cờ bị đổi
- Thoát khi : điều kiện → bước kế
- Kẹt được? : có/không + có fallback gì
```

Ba quy ước số học phải nhớ, sai là lệch 10 lần:
- Nhiệt độ trong firmware là **×10** (`Temperature_BT` 1500 = 150 °C). Thanh ghi `$M` hậu tố `_CV` đã ×10 sẵn để so trực tiếp với BT; bản `_R` trơn là số nguyên °C người dùng nhập.
- Cân `netW` ×10 (kg), `netW100` ×100 — auto-loader tính ngưỡng cắt ở thang ×100.
- `PER_DEV_SAVE` là **phần nghìn** (`×1000/timeRoast`), không phải phần trăm.

## Nguyên tắc bất di bất dịch khi sửa quy trình

Đây là những thứ đã trả giá bằng máy thật, đừng "tối giản" chúng đi:

- **Mọi timer tự đóng phải có nhánh huỷ.** Cặp đôi luôn đi cùng nhau: `if(timerEn && timer>=set)` → hành động, và `if(timerEn && BTN_R==0 && timer>=1)` → reset. Thiếu nhánh sau thì thợ nhả nút bằng tay xong timer vẫn bắn lệnh đóng, gây kẹt van.
- **Chốt an toàn chạy TRƯỚC switch, không nằm trong case.** `forceDrumFanOnFlag` (BT/ET > 80 °C bật trống+quạt) và `fireCutFlag` (cắt gas) phải đúng bất kể `progStep` đang ở đâu, kể cả khi máy trạng thái bị kẹt.
- **Trả quyền điều khiển khi kết thúc/huỷ.** Rời mẻ mà không đặt `naviSourceGAS/AIR/DRUM = SOURCE_AI_VR` là thợ mất quyền xoay biến trở. Chỗ này lặp ở 3 nơi (DROP, `START_BTN_R==0`, LOOP_1) — sửa một nơi phải soát cả ba.
- **Mở khoá HMI khi thoát.** `LOCK_BUTTON_W = 0` ở mọi đường ra, nếu không HMI khoá cứng.
- **Không gọi Modbus/SD/`delay()` trong ISR.** `timerPoll_1000ms()` chỉ được set cờ, việc thật làm trong `programScan()`. Xem `[[feedback_isr_no_modbus]]`.
- **Bước mới phải xét được cả 2 chế độ** `progStatus`: `STT_PROGRAM_AUTO` (máy tự lái) và `STT_PROGRAM_SAVE` (thợ lái, chỉ ghi log). Nhiều nhánh trong code rẽ theo cờ này.

## Sau khi sửa code

Build kiểm RAM/Flash bằng skill `flash-build`; trước khi nạp máy thật chạy `release-check` (soát `enDebug`, trần gas, timing). Sửa comment tiếng Việt thì theo `vietnamese-comments` để không hỏng encoding UTF-8.
