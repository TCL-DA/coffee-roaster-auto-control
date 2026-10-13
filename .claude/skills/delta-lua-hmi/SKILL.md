---
name: delta-lua-hmi
description: Viết, tra cứu và ghi chép Lua macro cho HMI Delta dòng DOP (DIAScreen/DOPSoft). Dùng khi cần soạn macro (account/login, đọc-ghi dữ liệu $n, chuyển màn, recipe, history buffer) hoặc khi user paste tài liệu hàm Lua để lưu vào reference.
allowed-tools: Read, Edit, Write, Grep
---

Hỗ trợ Lua macro cho HMI Delta trong dự án OTL-06ALS. HMI nối Modbus (slave ID 1, USART1 @115200), bộ nhớ nội bộ dạng `$n` (`mem.inter.*`), `$Mn` (`mem.static.*`), thanh ghi controller dạng `{Link2}1@W...`.

## Nguồn tham chiếu (đọc TRƯỚC khi làm)

1. [ref-hmi-lua-macro.md](../../../docs/ref/ref-hmi-lua-macro.md) — **danh sách hàm Lua đầy đủ** (mem.inter/static, account, screen, sys, string, math, table, convert/text, draw + cú pháp nền).
2. [ref-hmi-delta-dop.md](../../../docs/ref/ref-hmi-delta-dop.md) — Control Block / Status Block / thanh ghi điều khiển (W40050+), bit map.

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
4. Macro đọc/ghi register controller → đối chiếu [ref-hmi-delta-dop.md](../../../docs/ref/ref-hmi-delta-dop.md), tránh đụng Control/Status Block; khớp địa chỉ với Define.h của firmware.

### B. Ghi tài liệu hàm Lua (user paste vào)
1. Phân loại vào đúng mục trong [ref-hmi-lua-macro.md](../../../docs/ref/ref-hmi-lua-macro.md) (mem / account / screen / sys / string / math / table / convert / draw...). Thiếu mục → tạo mới.
2. Ghi gọn: signature + bảng tham số/trả về + 1 ví dụ. Giữ nguyên ngữ nghĩa manual, chú thích tiếng Việt, KHÔNG thêm tham số ngoài manual, KHÔNG nhồi raw dump dài.
3. Nếu hàm mới làm rõ chỗ "cần xác nhận" trước đó → cập nhật luôn ví dụ đó cho đúng API.
4. Dùng `Edit` (không `Write` đè) để khỏi mất nội dung cũ. **Không dán tài liệu thô vào SKILL.md** — chỉ vào reference.

## ⛔ Luật đo trên panel DOP-110WS thật + HMIApp (06–07/10/2026, bản thử OTL-30A T-B8L…T-B14)

- **HMIApp (máy ảo) KHÔNG có `pcall`** → `attempt to call a nil value (global 'pcall')`, Lua chết ở dòng đó; hộp lỗi bị thu xuống đáy màn nên dễ tưởng đang chạy. **Panel thật CÓ `pcall`**. Viết: `local thu = pcall or function(f, ...) f(...) return true end` rồi gọi `thu(...)`; ghi cờ `pcall and 1 or 2` ra một ô `$` để biết đang chạy ở đâu.
- **`os.date` làm máy Lua của panel SẬP** (pcall không đỡ, mất phần ghi EM chưa xong). Lấy giờ từ ô `$` do macro chép, không gọi `os.date`.
- `mem.em.Write(0, địa_chỉ, giá_trị)` / `mem.em.Read(0, địa_chỉ)` chỉ chạy khi panel CÓ USB/thẻ cho EM0; máy ảo không có USB thì vòng Lua đứng ở lệnh EM đầu tiên.
- `sys.Sleep(n)` chỉ là thời gian NGỦ, thời gian xử lý cộng thêm: vòng 4 × `sys.Sleep(250)` đếm "1 giây" thực ra ~1,05 s (đo 19 nhịp/20 s) — đồng hồ đếm bằng vòng Lua trôi ~5 %. **Macro đồng hồ (macro thường) chạy ~1,95 lần/giây** — đếm thời gian bằng số lần chạy phải nhân đúng nhịp đo được, đừng coi 1 lần = 1 s.
- Kiểm "Lua còn sống" bằng ô đếm nhịp + ô cờ do Lua ghi (vd `$510` tăng, `$515` ≠ 0), không phải bằng việc màn còn đổi.
- Điều khiển History (điều kiện ghi, lệnh xoá) không đọc được từ `{Link2}` trên panel thật — chép sang `$` rồi trỏ vào bit `$n.0` (xem skill `dopsoft-dpa` → `references/do-thi-lich-su-9-1.md`).

## ⛔ Bổ sung tuần 05–12/10/2026 (bản OTL-30A v28 LO50…LO68) — bảng đầy đủ: skill `dopsoft-dpa` → `references/so-loi-tuan-0510-1210.md`

- **Kiểm Lua TRƯỚC khi dựng bản HMI** (dựng + biên dịch + bật máy mô phỏng ~7 phút mới thấy hộp lỗi Lua): MCP `dpa_lua_check` nay biên dịch thật bằng `lupa` (`pip install lupa`) và cảnh báo `os.date`, `pcall` trần, ghi EM không chặn, vòng ghi ≥ 30 ô EM một nhịp. Logic chạy thử được trên PC bằng `lupa`: giả `mem.em` / `mem.inter` bằng `dict`, `sys.Sleep` bằng hàm đẩy kịch bản rồi ném ngoại lệ để thoát vòng `while true` — mẫu: `113_HMI\…\thu-nghiem\AP4\thu_lua_vong.py` (14 bước; chạy cùng bài với Lua cũ phải ra LOI thì bài mới có giá trị).
- **Bảng trên thẻ nhớ (EM) phải có chặn hoặc ghi vòng.** Tóm tắt mẻ `EM 1000 + b×32` chạm vùng sự kiện `EM 100000` sau 3 092 mẻ và `moMe()` không chặn → đè sự kiện (~3,4 tháng nếu 30 mẻ / ngày). Sửa: ô `(b−1) % 3092 + 1`, dùng lại ô thì xoá ô 9..22 (mốc thiếu ở mẻ mới không mang số mẻ cũ; cờ 'xong' về 0 để `noiTiep` còn đúng). Bên đọc (web `panel_web.o_tom_tat`) dùng CÙNG công thức và chỉ quét 3 092 mẻ mới nhất. Số mẻ `EM[4]` là 16 bit — quay vòng sau 65 535 mẻ, chưa xử lý.
- **Ghi ~35 ô EM liền một nhịp → Lua của panel chạy lại giữa mẻ** (07/10). Mở mẻ chỉ ghi 9 ô đầu; việc nhiều ô chia theo nhịp 250 ms; Lua khởi động lại khi cờ ghi đang = 1 thì NỐI TIẾP mẻ chưa đóng.
- **Macro đồng hồ đã 489 / 512 dòng** (mỗi macro Delta tối đa 512 dòng — lỗi "Clock Macro Error, Line:512") → logic mới đặt ở Lua: cờ hiển thị do Lua ghi một ô `$`, phần tử ẩn / hiện theo bit `$n.0` (vd `$816` gợi ý đồ thị trống, `$817` chớp icon cảnh báo 0,5 s = 2 nhịp 250 ms).
- **Thứ quan trọng không được phụ thuộc Lua để HIỆN.** Chớp cảnh báo: nền đỏ + mã do macro / đèn đọc thẳng; Lua chỉ đảo bit cho một ô đè CÙNG MÀU nền che icon → Lua đứng thì cảnh báo vẫn còn nguyên.
- **Ô `$` cho Lua:** board ghi `$0–$439` và `$600–$810` (panel dùng chung bộ nhớ `W400nn` ≡ `$(nn−1)`) — không đặt ô Lua ở đó; Modbus TCP chỉ đọc được `$0…$1023`. Vùng trống hiện tại ghi trong sổ lỗi tuần (mục P).
- `mem.static` = `$M` (giữ điện) đọc / ghi được từ Lua; `mem.inter` = `$`; `sys.GetTick()` (ms) là đồng hồ đúng — đừng đếm giây bằng số vòng lặp khi vòng có việc nặng (vẽ lại đồ thị làm vòng chậm).
- Lua của bản dựng chứa số bí mật từng máy (tài khoản PIN) → bản dựng không commit; nguồn giữ chỗ `__BI_MAT_MAY__`.

## Lưu ý

- Reference là nguồn sự thật. Hàm không có trong đó = chưa xác nhận → hỏi, đừng chế.
- Xử lý theo từng nhóm hàm, đừng nhồi cả manual vào ngữ cảnh.
