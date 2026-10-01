---
name: youtube-otl
description: Làm việc với kênh YouTube của công ty qua MCP `otl-youtube` — đọc kênh/video/số liệu/bình luận, và SỬA tiêu đề, mô tả, tag, chế độ riêng tư của video đã đăng. Gồm cả cách cấp quyền OAuth, cách AI "xem" một video bằng cắt khung hình, và cách viết tiêu đề/mô tả có mốc chương cho video gửi đối tác. Dùng khi người dùng nói "kênh youtube", "video trên kênh", "đổi tên video", "đặt tiêu đề video", "viết mô tả video", "video này quay gì", "xem giùm cái video", "thêm mốc chương", "số liệu kênh", "bình luận video", "cấp quyền youtube", "token youtube hết hạn", hoặc đưa link/mã video của kênh. KHÔNG đăng video mới, KHÔNG xoá video — cố ý không mở.
allowed-tools: Read, Grep, Bash
---

# Kênh YouTube của công ty

Server MCP `otl-youtube` (`tools/mcp_youtube/server.py`) nối vào kênh bằng OAuth.
Đọc được mọi thứ, **ghi được thông tin video đã đăng**. Cố ý KHÔNG mở: đăng video mới,
xoá video, trả lời bình luận.

## Luôn làm trước

Gọi `youtube_kiem_tra` trước khi kết luận bất cứ điều gì về kết nối. Đừng đoán từ lỗi.

## Mười ba công cụ

| Công cụ | Việc |
|---|---|
| `youtube_kiem_tra` | Đã nối chưa, đang nối vào kênh nào |
| `youtube_kenh` | Tên kênh, ngày lập, người đăng ký, tổng video, tổng lượt xem |
| `youtube_video` | Liệt kê video, **mới nhất trước** |
| `youtube_so_lieu` | Số liệu người xem theo khoảng ngày |
| `youtube_binh_luan` | Đọc bình luận một video |
| ✍️ `youtube_sua_video` | **GHI:** tiêu đề / mô tả / tag / chế độ riêng tư |
| `youtube_loi_thoai` | Lời thoại + mốc giờ. **Không cần OAuth**, chạy cả trên video người khác |
| `youtube_danh_sach_phat` | Playlist của kênh, hoặc video trong một playlist |
| `youtube_tim_cong_khai` | Tìm video công khai của **người khác** (cần `api_key.txt`) |
| `youtube_phu_de` | Phụ đề chính thức trên kênh — cần thêm quyền `force-ssl` |
| ✍️ `youtube_thay_hang_loat` | **GHI:** thay chữ trên **nhiều video**. Mặc định chỉ xem trước |
| ✍️ `youtube_anh_bia` | **GHI:** đặt ảnh bìa mới |
| ✍️ `youtube_tra_loi_binh_luan` | **GHI:** trả lời bình luận — cần thêm quyền `force-ssl` |

Công cụ nào nhận mã video thì nhận luôn link dán nguyên từ trình duyệt.

⛔ `youtube_thay_hang_loat` gọi lần đầu là **chỉ xem trước**. Đưa chủ máy duyệt danh
sách rồi mới gọi lại với `thuc_thi=true`. Mỗi video ghi tốn 50 đơn vị hạn mức ngày.

⛔ `youtube_sua_video` **hiện ngay với người xem**. Đưa chủ máy duyệt chữ rồi mới gọi.
Lưu snippet cũ ra file trước khi ghi — để hoàn tác được.

## Quyền OAuth

Ba scope đang dùng: `youtube.readonly`, `yt-analytics.readonly`, `youtube`.
Google **không có** quyền hẹp kiểu "chỉ sửa mô tả" — `youtube` là mức hẹp nhất ghi được,
vẫn hẹp hơn `youtube.force-ssl`.

⛔ **Thêm scope phải làm đủ 4 việc**, sót một cái là "chạy không lỗi mà chẳng đổi gì":

1. thêm scope vào `cap_quyen.py`
2. thêm scope vào `QUYEN` trong `server.py`
3. **xoá `token.json`** rồi chạy lại `cap_quyen.py` — không xoá thì Google trả bộ quyền cũ
4. **khởi động lại Claude Code** — MCP chỉ nạp lúc mở phiên

**Kiểm quyền THẬT SỰ được cấp** (đừng tin mỗi file token):

```bash
# hỏi thẳng Google xem access token đang mang scope nào
curl -s "https://oauth2.googleapis.com/tokeninfo?access_token=<token>"
```

`captions()` (đọc phụ đề tự động) đòi `youtube.force-ssl` — scope đó cho phép cả **xoá video**,
nên đừng tự thêm, phải hỏi chủ máy.

## Bẫy đã trả giá

1. ⛔ **Đừng cắt đuôi danh sách rồi kết luận.** `youtube_video` trả **mới nhất trước**;
   cho chạy qua `tail` là đọc nhầm sang video **cũ nhất**. Đã có lần vì vậy mà tưởng kênh
   chỉ có 5 video (thật ra hơn 80) rồi đi đổi tên nhầm 4 video cũ nhất.
2. ⛔ **YouTube từ chối dấu `<` và `>`** trong tiêu đề lẫn mô tả → `400 invalidDescription`,
   thông báo không hề nhắc ký tự nào. `server.py` đã chặn trước, báo đúng chỗ sai.
3. ⛔ **Đọc lại bằng `videos().list()` ngay sau khi ghi ra BẢN CŨ** (bộ nhớ đệm vài giây)
   → tưởng ghi hỏng trong khi đã xong. Lấy kết quả từ chính `videos().update()` trả về.
4. **`statistics.videoCount` chỉ đếm video CÔNG KHAI.** Kênh báo 0 video mà playlist uploads
   có hàng chục cái nghĩa là chúng đang private/unlisted — không phải lỗi.
5. **Studio và API đếm khác nhau:** tab Video của Studio không tính Shorts, playlist uploads thì có.
6. ⛔ **403 `access_denied`** khi cấp quyền = email chưa nằm trong **Test users**
   (Google Cloud Console → Google Auth Platform → Audience). Màn hình này **không có nút bấm qua**,
   khác màn hình đỏ *"Google hasn't verified this app"* (cái đó Advanced → Go to… là qua được).
7. **Token chết sau 7 ngày** khi app ở chế độ *Testing*. Muốn dùng lâu: Audience → **Publish app**.

## Cho AI "xem" một video

**Thử `youtube_loi_thoai` TRƯỚC.** Video có phụ đề thì nó trả về cả lời thoại kèm mốc
giờ, không cần file gốc, không cần OAuth, không tốn hạn mức API — đủ để viết mô tả và
dựng mốc chương. Chỉ khi video không có phụ đề, hoặc cần nhìn thao tác tay chứ không
phải nghe nói, mới phải cắt khung hình theo cách dưới đây.

⛔ **Không tải được video từ YouTube.** `yt-dlp` trả *"This video is not available"*; đổi
`player_client` chỉ còn storyboard vì YouTube bật **SABR-only streaming**. Storyboard `.mhtml`
tách ra là mảnh vụn, giải mã ra rác. → **Phải có file gốc trên đĩa.**

Có file rồi thì chạy:

```bash
python .claude/skills/youtube-otl/scripts/xem_video.py "<file.mp4>" --giay 10
```

Script tự: kiểm có tiếng không, cắt khung hình, ghép lưới có ghi mốc thời gian, và
**chặn ảnh quá khổ**. Sau đó dùng Read đọc từng tấm ghép.

⛔ **Ảnh ghép phải ≤ 2000 px MỖI CHIỀU.** Lỡ đọc một ảnh rộng hơn là **cả phiên sau đó không
gửi thêm được ảnh nào**, kể cả ảnh 300 px — ảnh quá khổ nằm lại trong lịch sử hội thoại và
không gỡ ra được. Phải mở phiên mới. Kiểm cỡ TRƯỚC khi đọc.

⛔ **Cắt 30 giây là không đủ** để dựng mốc chương: đã từng lệch mốc 1–2 phút và bỏ sót hẳn
một bước thao tác. **Dùng 10 giây.**

Video không có luồng audio thì không bóc lời được — kiểm trước bằng
`ffprobe -select_streams a`, đừng để `faster_whisper` chạy rồi mới báo `IndexError`.

## Viết tiêu đề và mô tả

- Tiêu đề ≤ 100 ký tự, mô tả ≤ 5000, tổng tag ≤ 500.
- **Mốc chương**: mốc đầu phải là `0:00`, tối thiểu 3 mốc, cách nhau ≥ 10 giây. Dựng mốc từ
  khung hình 10 giây, đừng đoán.
- Video **gửi đối tác** thì viết **tiếng Anh trước, tiếng Việt sau**, và **không ghi tên
  thương hiệu của ta lẫn tên đối tác** — để trung tính, chủ máy muốn thêm thì thêm.
- Video không có tiếng thì **nói rõ "NO SOUND"** ngay đầu mô tả, và bù bằng mốc chương.
- Cái gì không đọc được từ hình thì **đừng bịa** — thiếu tên người, thiếu cỡ máy thì bỏ trống
  và hỏi, đừng điền bừa cho đẹp.

## Khoá để ngoài repo

⛔ Repo này **PUBLIC**. Không bao giờ ghi vào đây: `client_secret.json`, `token.json`,
email tài khoản, mã kênh, **mã video unlisted** (đưa lên là lộ link cho cả thiên hạ),
tên/địa chỉ đối tác.

Khoá và hướng dẫn cấp quyền để ở `F:\Project\114_Youtube\`. Chi tiết từng kênh, từng video
nằm trong bộ nhớ dự án, không nằm ở đây.
