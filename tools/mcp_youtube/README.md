# MCP `otl-youtube` — đọc kênh YouTube của công ty

**CHỈ ĐỌC.** Không đăng, không sửa, không xoá gì trên kênh.

## Công cụ

| Công cụ | Việc |
|---|---|
| `youtube_kiem_tra` | Đã nối được chưa, đang nối vào kênh nào. Gọi trước khi báo lỗi |
| `youtube_kenh` | Tên kênh, mô tả, ngày lập, người đăng ký, tổng video, tổng lượt xem |
| `youtube_video` | Danh sách video mới nhất trước, kèm lượt xem/thích/bình luận/thời lượng |
| `youtube_so_lieu` | Số liệu người xem theo khoảng ngày — gộp cả kênh, tách theo ngày, hoặc tách theo video |
| `youtube_binh_luan` | Đọc bình luận một video |

## Khoá để ở đâu

⛔ **Ngoài repo**, mặc định `F:\Project\114_Youtube\`:

| File | Là gì |
|---|---|
| `client_secret.json` | Tải từ Google Cloud Console, kiểu **Desktop app** |
| `token.json` | Sinh ra khi chạy `cap_quyen.py`, **chìa khoá vào kênh** |

Đổi chỗ khác thì đặt biến `OTL_YT_DIR`. Hai file này đã có trong `.gitignore`;
ai cầm được `token.json` là vào kênh như chủ.

Cách lấy khoá: `F:\Project\114_Youtube\HUONG-DAN.md`.

## Vì sao `youtube_kenh` báo 0 video mà `youtube_video` vẫn ra video

Không phải lỗi. `statistics.videoCount` của Google **chỉ đếm video CÔNG KHAI**, còn
`youtube_video` đọc playlist "uploads" nên thấy cả video **riêng tư và không công khai**.

Hai số vênh nhau nghĩa là video trên kênh đang để riêng tư hoặc không công khai. Cũng vì
vậy mà `viewCount` của kênh bằng 0 trong khi từng video vẫn có lượt xem.

## Ba bẫy đã gặp thật

1. **403 access_denied — "Đã chặn quyền truy cập".** Email đăng nhập chưa nằm trong
   **Test users**. Màn hình này KHÔNG có nút bấm qua. Sửa ở Google Cloud Console →
   *Google Auth Platform → Audience → Test users → Add users*, thêm đúng email sẽ đăng nhập.
   Khác hẳn màn hình đỏ *"Google hasn't verified this app"* — cái đó bấm **Advanced** là qua.
2. **Token chết sau 7 ngày** khi app để ở chế độ *Testing*. Muốn dùng lâu dài thì
   *Audience → Publish app*: vẫn hiện cảnh báo chưa xác minh (bấm Advanced là qua),
   giới hạn 100 người dùng, nhưng token không hết hạn theo tuần nữa.
3. **Cấp quyền đúng tài khoản.** Tài khoản đăng nhập phải là chủ kênh, không thì
   cấp quyền xong vẫn không thấy kênh nào.

## Muốn đăng video thì sao

Sửa `QUYEN` trong `cap_quyen.py`, **xoá `token.json`**, cấp quyền lại. Nhưng biết trước:

- App chưa qua kiểm duyệt Google thì **video đăng qua API bị khoá private**.
- Hạn mức 10.000 đơn vị/ngày, mỗi lần đăng tốn ~1.600 → khoảng **6 video/ngày**.
- Trình cắt video của Studio, phần lớn cài đặt kiếm tiền và một số mục kiểm duyệt
  **không có API** — vẫn phải làm tay.

Server này cố ý không có công cụ ghi. Thêm quyền upload mà không sửa server thì vẫn
không đăng được gì — đó là chủ ý.
