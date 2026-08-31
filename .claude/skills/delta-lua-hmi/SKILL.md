---
name: delta-lua-hmi
description: Viết, tra cứu và ghi chép Lua macro cho HMI Delta dòng DOP (DIAScreen/DOPSoft). Dùng khi cần soạn macro (account/login, đọc-ghi dữ liệu $n, chuyển màn, recipe, history buffer) hoặc khi user paste tài liệu hàm Lua để lưu vào reference.
allowed-tools: Read, Edit, Write, Grep
---

Hỗ trợ Lua macro cho HMI Delta trong dự án OTL-06ALS. HMI nối Modbus (slave ID 1, USART1 @115200), bộ nhớ nội bộ dạng `$n` (`mem.inter.*`), `$Mn` (`mem.static.*`), thanh ghi controller dạng `{Link2}1@W...`.

## Nguồn tham chiếu (đọc TRƯỚC khi làm)

1. [ref-hmi-lua-macro.md](ref-hmi-lua-macro.md) — **danh sách hàm Lua đầy đủ** (mem.inter/static, account, screen, sys, string, math, table, convert/text, draw + cú pháp nền).
2. [ref-hmi-delta-dop.md](ref-hmi-delta-dop.md) — Control Block / Status Block / thanh ghi điều khiển (W40050+), bit map.

Luôn `Read` 2 file này trước. **Chỉ dùng hàm CÓ trong reference** — KHÔNG bịa tên/tham số hàm Lua. Hàm cần dùng mà reference chưa có → dừng, nói rõ "chưa có trong tài liệu", hỏi user paste signature từ manual Delta rồi ghi bổ sung.

## Hàm hay dùng (chi tiết trong reference)

- Ghi/đọc số: `mem.inter.Read/Write`, `ReadDW/WriteDW`, `ReadFloat/WriteFloat`, `ReadBit/WriteBit`.
- **Ghi chuỗi** (vd tên login lên `$n`): `mem.inter.WriteAscii(idx, str, string.len(str))`.
- Account: `account.GetCurrentLogin()` → `ret,name,level`; `Login/Add/Delete/ChangeLevel/IsExist`.
- Màn: `screen.Open(id)`, `screen.IsOpened(id)`.
- Hệ thống: `sys.GetInterParam("ACCOUNT"|"NET1_IP1"|...)`, `sys.BuzzerOn`, `sys.GetTime/GetDate`.

## Hai chế độ làm việc

### A. Soạn macro cho 1 nhiệm vụ
Khi user mô tả việc cần (vd "show tên login lên $5000", "BT cao thì nhảy màn cảnh báo"):

1. Đọc reference, xác định hàm đúng. Thiếu hàm → hỏi, đừng đoán.
2. Viết macro, tuân thủ:
   - Địa chỉ nội bộ `$n` qua `mem.inter.*`; `$Mn` qua `mem.static.*`; controller qua `link.*` / `{Link2}@`.
   - Chuỗi: 1 word = 2 ký tự → nhắc user đặt ô Character/ASCII Display đủ word.
   - Chú thích macro bằng **tiếng Việt có dấu** (`--` cho comment Lua).
   - Kiểm `ret`/giá trị trả về trước khi dùng; tránh biến `nil` (Lua dừng giữa chừng).
3. Nêu **chỗ đặt macro** + đánh đổi: Background/Cycle (luôn cập nhật, tốn quét) vs On Screen Open / sự kiện nút (nhẹ, chạy 1 lần).
4. Macro đọc/ghi register controller → đối chiếu [ref-hmi-delta-dop.md](ref-hmi-delta-dop.md), tránh đụng Control/Status Block; khớp địa chỉ với Define.h của firmware.

### B. Ghi tài liệu hàm Lua (user paste vào)
1. Phân loại vào đúng mục trong [ref-hmi-lua-macro.md](ref-hmi-lua-macro.md) (mem / account / screen / sys / string / math / table / convert / draw...). Thiếu mục → tạo mới.
2. Ghi gọn: signature + bảng tham số/trả về + 1 ví dụ. Giữ nguyên ngữ nghĩa manual, chú thích tiếng Việt, KHÔNG thêm tham số ngoài manual, KHÔNG nhồi raw dump dài.
3. Nếu hàm mới làm rõ chỗ "cần xác nhận" trước đó → cập nhật luôn ví dụ đó cho đúng API.
4. Dùng `Edit` (không `Write` đè) để khỏi mất nội dung cũ. **Không dán tài liệu thô vào SKILL.md** — chỉ vào reference.

## Lưu ý

- Reference là nguồn sự thật. Hàm không có trong đó = chưa xác nhận → hỏi, đừng chế.
- Xử lý theo từng nhóm hàm, đừng nhồi cả manual vào ngữ cảnh.
