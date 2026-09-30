# MCP `otl-manual` — dựng tài liệu manual OTL

Gói bốn thao tác tay (nối engine → chạy Illustrator qua COM → render PNG → đếm chữ từng
trang) thành một lệnh gọi. Dùng chung engine và quy ước trình bày với skill `manual-otl`.

## Công cụ

| Công cụ | Việc |
|---|---|
| `manual_dung` | Dựng một tài liệu từ file `content*.jsx` → `.ai` + `.pdf`, render PNG, rà trang thưa chữ |
| `manual_ra_soat` | Rà lại PDF đã dựng sẵn mà không dựng lại |
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
```

Trả về số trang, đường dẫn PDF, danh sách cảnh báo trang thưa chữ, và cảnh báo sớm chỗ
thiếu dấu cách trước `\u2013` — lỗi dính chữ từng lọt ra tận bìa tài liệu gửi khách.

## Giới hạn phải nhớ

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
