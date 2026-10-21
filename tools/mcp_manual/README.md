# MCP `otl-manual` — dựng tài liệu manual OTL

Gói bốn thao tác tay (nối engine → chạy Illustrator qua COM → render PNG → đếm chữ từng
trang) thành một lệnh gọi. Dùng chung engine và quy ước trình bày với skill `manual-otl`.

## Công cụ

| Công cụ | Việc |
|---|---|
| `manual_dung` | Dựng một tài liệu từ file `content*.jsx` → `.ai` + `.pdf`, **gắn bookmark**, render PNG, rà trang thưa chữ |
| `manual_ra_soat` | Rà lại PDF đã dựng sẵn mà không dựng lại |
| `manual_bookmark` | Gắn / đọc bookmark cho một PDF đã dựng từ trước |
| `manual_kiem_chuoi_cam` | Bản OEM: bóc chữ trong PDF xem còn sót dấu vết thương hiệu gốc không |
| `manual_kiem_tra` | Kiểm nhanh có engine, có thư mục gốc, có pymupdf chưa |

## Cấu hình

Đã khai trong `.mcp.json` của dự án, không cần biến môi trường. Muốn trỏ chỗ khác:

| Biến | Mặc định |
|---|---|
| `OTL_MANUAL_ENGINE` | `.claude\skills\manual-otl\assets\engine.jsx` |
| `OTL_MANUAL_GOC` | `F:\Project\112_Quanly\122_Manual_AI` — gốc cho đường dẫn tương đối |

Cần Illustrator đang cài và `pip install pymupdf`.

## Dùng

```
manual_dung(content="airlock-repair-en/content.jsx")

manual_dung(content=["airlock-repair-en/content.jsx",          # nhiều bản một lượt,
                     "airlock-repair-en/content-vi.jsx"],      # chung một phiên
            nhanh=True)                                        # bản nháp: bỏ lưu .ai
```

## Tốc độ

Đo thật 30/09/2026 trên tài liệu 15 trang. Thời gian dồn gần hết vào Illustrator:
khởi động **nguội ~32 s**, đóng tài liệu cũ ~2 s (**~9 s** nếu để dồn), vẽ ~4 s,
lưu `.ai` ~1,2 s, lưu `.pdf` ~1,0 s. Render PNG và rà soát cộng lại **chưa tới 0,5 s** —
tối ưu hai khâu đó là vô nghĩa.

Server làm sẵn ba việc: đóng tài liệu ngay trong lần chạy đó, dựng nhiều tài liệu trong
**một** phiên PowerShell, và `nhanh=true` bỏ bước lưu `.ai`.

**17 s → 9 s mỗi tài liệu.** ⛔ Đừng tắt Illustrator giữa chừng — bật lại mất 32 giây,
nhiều hơn cả việc dựng.

Code dựng dùng chung với `make.py` của skill `manual-otl` (server nạp thẳng file đó),
nên không nuôi hai bản lệch nhau.

Trả về số trang, đường dẫn PDF, danh sách cảnh báo trang thưa chữ, và cảnh báo sớm chỗ
thiếu dấu cách trước `\u2013` — lỗi dính chữ từng lọt ra tận bìa tài liệu gửi khách.

## Giới hạn phải nhớ

⛔ **PDF giao khách bắt buộc có bookmark.** Illustrator xuất PDF từ artboard nên
không bao giờ tự sinh bookmark. `manual_dung` tự gắn bằng `bookmark.py` của skill và
trả về `bookmark.so_bookmark` kèm lần đọc lại trên chính file. **`so_bookmark = 0` là
chưa xong**, không được giao — thường do tài liệu tự vẽ tiêu đề bằng `mkText` thay vì
dùng `H1()` / `H2()`.

⚠ **Máy chỉ bắt được trang THƯA CHỮ.** Chồng chữ, tràn khung, logo chạm tiêu đề thì nó
không thấy. Dựng xong **vẫn phải xem ảnh PNG bằng mắt** rồi mới giao — đây là bước bắt
buộc của skill `manual-otl`, MCP này không thay thế được.

Server **không viết nội dung tài liệu**. Nội dung nằm trong `content*.jsx`; API engine,
quy ước trình bày và các bẫy đã trả giá nằm trong skill `manual-otl` — đọc skill đó trước.

## Bản OEM mang thương hiệu đối tác

Bản OEM là bản **sinh ra bằng script** từ bản gốc, không chép ra sửa tay hai nơi. Trước khi
gửi, chạy `manual_kiem_chuoi_cam` trên chính file PDF: đọc mã nguồn là chưa đủ, vì ảnh bìa
cũ vẫn có thể mang dấu nhận dập trên tôn máy.

Thông tin thương hiệu từng đối tác để **ngoài repo** (repo này từng để PUBLIC).
