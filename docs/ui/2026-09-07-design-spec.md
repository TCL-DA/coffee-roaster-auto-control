# Bản thiết kế "Rang - Sửa lại" — đặc tả để áp vào app

Nguồn gốc: project **Claude Design** `Menu cài đặt nhanh - Lỗi thiết kế`
(`3c3a6a49-faff-4902-a214-f071ccd6006f`), file `Rang - Sửa lại.dc.html`.

Bản mirror trên đĩa: **`docs/ui/design-web/`** — mở `Rang - Sua lai.dc.html` bằng
trình duyệt là xem được đầy đủ, không cần mạng, không cần tài khoản.

> Codex đọc thẳng thư mục mirror này. Chỉ Claude Code mới gọi được công cụ
> `DesignSync` để kéo bản mới; khi cần đồng bộ thì nhờ Claude làm mới mirror.
> Bản mirror hiện tại kéo lúc **07/09/2026 13:17** (80.946 byte).

---

## 1. Bộ màu (đã áp vào app)

Toàn bộ bảng màu của bản thiết kế đã vào app dưới dạng **một tuỳ chọn màu chủ đạo
mới**: `data-accent="ember"`, nhãn **Than hồng / Ember**. Chọn ở thanh công cụ
hoặc trang Cá nhân hoá. Bề mặt chỉ đổi khi đang ở **theme tối**; theme sáng chỉ
mượn màu cam để không phá nền sáng.

| Vai trò | Token | Giá trị |
|---|---|---|
| Nền ngoài cùng | `--bg` | `#08080A` |
| Nền phong bì | `--letter` | `#050506` |
| Nền panel | `--panel` | `#101013` |
| Nền thẻ | `--card` | `#16161B` |
| Nền lõm | `--inset` | `#0C0C0F` |
| Đường kẻ | `--hair` / `--hair-2` | `#23232A` / `#3A3A44` |
| Chữ chính | `--txt` | `#F2F2F3` |
| Chữ phụ | `--dim` / `--mute` / `--faint` | `#BDBDC6` / `#84848F` / `#4A4A54` |
| Cam nhấn | `--accent` / `--accent-ink` | `#F2761A` / `#1A0F04` |
| Xanh OK | `--ok` / `--ok-ink` / `--green-ink` | `#6FCF8E` |
| Đỏ nguy | `--danger` / `--red-ink` | `#D93A32` / `#E8756D` |

**Chữ:** bản thiết kế dùng IBM Plex Sans + IBM Plex Mono. **ĐÃ NHÚNG XONG** —
15 tệp woff2 dạng base64 ngay trong `OTL Roast Lab.html`, chạy offline không cần
Google Fonts. (Đoạn cũ ghi "chưa làm" đã lạc hậu.)

**Khung gốc:** bản thiết kế vẽ cứng 1920×1080 rồi co giãn bằng `fitScale`. App
thật dùng bố cục co giãn thật — **không chép cách này**, chỉ lấy tỉ lệ và thứ bậc.

---

## 2. Bốn màn đã thiết kế — **ĐÃ ÁP XONG CẢ BỐN** (07/09/2026)

> Rang và Hồ sơ áp lúc 14:0x–14:5x; Tổng quan và Lịch sử áp lúc 18:5x, xem
> [2026-09-07-tongquan-lichsu-gioithieu.md](2026-09-07-tongquan-lichsu-gioithieu.md).
> Cột **KHỐI LƯỢNG** cũng đã làm: thêm `charge_kg` vào bảng `batches`, số do
> **thợ nhập** ở panel sau mẻ (cân phễu đo lượng còn trong phễu, không phải
> lượng đã vào trống — suy ra là đoán sai). Màn **Hồ sơ** về đúng **lưới 3 cột**
> thẻ gọn ở đợt hai cùng ngày.

Bản thiết kế có 4 màn: `overview` · `rang` · `profiles` · `history`.
Hai màn **Kho & Kinh doanh** và **Cài đặt** chưa được vẽ.

### Tổng quan (`overview`)
- Lời chào theo tên thợ + vai trò + máy + ngày đầy đủ tiếng Việt.
- Khối **"Chuẩn bị mẻ rang"** dạng 3 bước có trạng thái: `Làm nóng máy` (Đang chạy · 128/150°C) → `Chọn hồ sơ` (Chưa chọn) → `Nạp hạt` (Chờ bước 2).
- Thẻ **Hồ sơ hay dùng**: 3 hồ sơ + link "Xem tất cả 7 hồ sơ →".
- Thẻ **Mẻ gần nhất** + link "Xem lịch sử →".
- Ba số tóm tắt: `7 hồ sơ · quản lý đường cong`, `127 mẻ đã lưu`, `3 đơn tới hạn tuần này`.

### Rang (`rang`)
- Dải mốc `TP · DE · FCs · DEV · DROP`.
- Khi **chưa nạp**: banner `BƯỚC 1 / 3 — Chọn hồ sơ rang để nạp mẻ`.
- Ba thanh điều khiển: `MỨC GAS` (kèm "hồ sơ 45% · giữ để chạy nhanh"), `LƯỢNG GIÓ` ("hồ sơ 55%"), `TỐC ĐỘ TRỐNG`.
- Bốn ô số lớn: `NHIỆT HẠT · BT`, `TĂNG NHIỆT (°C/phút)`, `NHIỆT KHÍ · ET`, `THỜI GIAN MẺ` (mục tiêu 11:00).
- Khối `THIẾT BỊ PHỤ` thu gọn được, tiêu đề hiện **số thiết bị đang bật**.

### Hồ sơ (`profiles`)
- Hai tab con: **Hồ sơ rang** / **Công thức nạp**.
- Ô tìm + lọc `Tất cả · Nhạt · Vừa · Đậm`; nút `So sánh hồ sơ`, `+ Hồ sơ mới`.
- Thẻ hồ sơ: tên 22px, ghi chú hạt 17px, huy hiệu mức rang, khối 3 số
  `NHIỆT NẠP · NHIỆT XẢ · THỜI GIAN` (24px mono), dòng "Đã ghi N mẻ · lần cuối …",
  nút `Nạp & rang` + sao yêu thích + `Sửa`.

### Lịch sử (`history`)
- Tiêu đề + "127 mẻ đã lưu · đang xem 5 mẻ gần nhất", nút `Xuất CSV`.
- Ô tìm + lọc ngày `Từ … đến …` + `Xóa bộ lọc`.
- Bảng cột `MÃ MẺ · HỒ SƠ · PHÁT TRIỂN · KHỐI LƯỢNG · NGÀY`.
- Phân trang `Trang 1 / 26 · ← Trước · Sau →`.

---

## 3. Bản thiết kế tự sửa 2 lỗi nặng của bản rà soát 07/09

Đối chiếu `docs/ui/2026-09-07-open-design-audit.md`:

1. **Mất kết nối** — có trạng thái riêng: chấm `#D93A32` + chữ "Mất kết nối",
   mọi số liệu về `—` màu `#66666F`. Không còn báo nhầm thành "chưa có lửa".
2. **Xả liệu vs Kết thúc mẻ** — chuyển sang **giữ nút 1 giây** mới ăn, có vòng
   tiến trình chạy + dòng `KHÔNG HOÀN TÁC ĐƯỢC · GIỮ 1 GIÂY`. Nút "Tắt hẳn ứng
   dụng" bị khoá (`not-allowed`) khi đang rang.

Còn lại từ bản rà soát mà thiết kế **chưa** đụng tới: màu ET không đồng nhất,
mật độ vùng Thiết bị phụ ở 1366×768.

Riêng mục "ô ngày Lịch sử hiện `dd-----yyyy`" thì **đo lại thấy không phải lỗi
của app** — do bản Chromium headless của bộ kiểm thiếu dữ liệu ICU nên rơi về
định dạng `dd-MMM-yyyy` (thử vi-VN / en-GB / en-US ra y hệt nhau). WebView2 trên
Windows có đủ ICU nên hiện `dd/mm/yyyy`. Đã ghi định dạng vào nhãn ô, không vá code.
**Hợp đồng nhãn chốt 14/09/2026 (review Codex RF-11):** ghi thứ tự ngày bằng CHỮ —
`Từ ngày (ngày/tháng/năm)` / `From (day/month/year)` — vì ô date hiện `dd/mm/yyyy` hay
`dd-----yyyy` tuỳ cấu hình Windows từng máy khách. `test_ui_overview_history` giữ hợp đồng này.

---

## 4. Việt hoá thuật ngữ (theo bản thiết kế)

| Cũ trong app | Theo thiết kế |
|---|---|
| Nhiệt charge | **Nhiệt nạp** |
| RoR / ΔBT | **Tăng nhiệt** (°C/phút) |
| BT | **Nhiệt hạt · BT** |
| ET | **Nhiệt khí · ET** |
| Airflow | **Lượng gió** |
| Gas | **Mức gas** |
| Drum | **Tốc độ trống** |
