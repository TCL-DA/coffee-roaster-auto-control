# Nguồn của thư mục này

Đây là **bản sao trên đĩa** của bản thiết kế giao diện Roast Lab trên Claude Design.
Mở `Rang - Sua lai.dc.html` bằng trình duyệt là xem đủ — **không cần mạng, không cần
tài khoản, không cần quyền gì**. Đó là lý do thư mục này tồn tại.

| | |
|---|---|
| Project | `Menu cài đặt nhanh - Lỗi thiết kế` |
| UUID (07/09/2026) | `3c3a6a49-faff-4902-a214-f071ccd6006f` |
| URL | `claude.ai/design/p/<uuid>` |
| Kéo về lúc | **07/09/2026 13:17** |
| Đối chiếu lại | **14/09/2026 12:05** — `get_file` bản trên mây **trùng từng byte** với bản trên đĩa (md5 `bd3a10d0…`), UUID trên đọc được lại sau `/design-login` |
| Kéo bằng | `DesignSync` (công cụ chỉ Claude Code gọi được) |
| Có gì trong bản này | 4 màn: `overview` · `rang` · `profiles` · `history` |
| **Thiếu** | Kho & Kinh doanh · Cài đặt · **hộp "Sửa hồ sơ"** |

## Vân tay — biết ngay bản trên đĩa có bị đụng vào không

```
80946  bd3a10d0  Rang - Sua lai.dc.html
69150  951ae391  support.js
4,2 MB  (14 ảnh)  uploads/
```

(Cột giữa là 8 ký tự đầu của md5. Lệnh kiểm: `md5sum "Rang - Sua lai.dc.html" support.js`.)

⚠ **Không sửa tay file trong thư mục này.** Đây là bản sao của nguồn; sửa vào đây thì
lần kéo sau ghi đè mất. Muốn đổi thiết kế thì đổi trên Claude Design rồi kéo lại.

---

## Làm mới bản sao — HAI đường, đường 2 không phụ thuộc tài khoản nào

### Đường 1 — `DesignSync` (nhanh, nhưng kén tài khoản)

Chỉ chạy được khi phiên Claude Code **đã đăng nhập bằng đúng tài khoản đang giữ
project**. Nhờ Claude làm; Codex không gọi được công cụ này.

Ba chỗ hay vấp:

1. `/design-login` **chỉ chạy trong phiên Claude Code tương tác** — AI không tự chạy
   thay được vì bước cuối là bấm **Authorize** trên trình duyệt. Cấp một lần thì các
   phiên nền sau dùng lại được.
2. Trên máy Windows của O Tesla, gõ `claude` trong PowerShell là gãy (ExecutionPolicy
   chặn `claude.ps1`). Gõ **`claude.cmd`**.
3. `list_projects` trả về **rỗng** là bình thường — nó chỉ kê project loại
   *design system*, project canvas không thuộc loại đó. Cứ truyền thẳng UUID cho
   `get_project` / `list_files` / `get_file`.

**Đã gặp 13/09/2026:** đăng nhập xong nhưng UUID trên trả `404 project not found`.
Nghĩa là project đã đổi UUID, bị xoá, hoặc **tài khoản vừa Authorize không phải tài
khoản giữ project**. Lấy UUID mới từ URL rồi sửa lại bảng trên.

### Đường 2 — tải tay (ai mở được design là làm được)

Không cần Claude, không cần DesignSync, không cần đúng tài khoản của Claude Code —
chỉ cần **một tài khoản bất kỳ mở được bản thiết kế**:

1. Mở project trên `claude.ai/design`, vào file thiết kế.
2. Lưu trang về (`Ctrl+S` → *Webpage, Complete*), hoặc dùng nút tải/xuất của Claude
   Design nếu có.
3. Chép đè `Rang - Sua lai.dc.html` + `support.js` + thư mục `uploads/` vào đây.
4. **Cập nhật lại bảng vân tay và ngày ở trên** — không cập nhật thì lần sau không ai
   biết bản này mới hay cũ.

Đường 2 mới là đường bảo đảm việc chung không đứt khi đổi tài khoản, đổi máy, hay
mất quyền. Đường 1 chỉ là lối tắt.

---

## Ai đọc cái gì

| Bên | Đọc | Ghi |
|---|---|---|
| Codex | thư mục này + `../2026-09-07-design-spec.md` | ✗ |
| Claude Code | thư mục này; kéo bản mới khi có quyền | chỉ khi làm mới bản sao |
| Người dùng | trình duyệt, mở thẳng file `.dc.html` | trên Claude Design |

Đặc tả rút gọn (token màu, từng màn, thuật ngữ) ở **`../2026-09-07-design-spec.md`** —
đọc file đó trước khi sửa giao diện, nhanh hơn đọc bản `.dc.html`.
