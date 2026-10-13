---
name: youtube-otl
description: Làm việc với kênh YouTube của công ty qua MCP `otl-youtube` — đọc kênh/video/số liệu/bình luận, và SỬA tiêu đề, mô tả, tag, chế độ riêng tư của video đã đăng. Gồm cả cách cấp quyền OAuth, cách AI "xem" một video bằng cắt khung hình, và cách viết tiêu đề/mô tả có mốc chương cho video gửi đối tác. Dùng khi người dùng nói "kênh youtube", "video trên kênh", "đổi tên video", "đặt tiêu đề video", "viết mô tả video", "video này quay gì", "xem giùm cái video", "thêm mốc chương", "số liệu kênh", "bình luận video", "cấp quyền youtube", "token youtube hết hạn", hoặc đưa link/mã video của kênh. ĐĂNG được video mới (có soát xác minh kênh, quyền và mốc chương trước khi tải). KHÔNG xoá video — cố ý không mở.
allowed-tools: Read, Grep, Bash
---

# Kênh YouTube của công ty

Server MCP `otl-youtube` (`tools/mcp_youtube/server.py`) nối vào kênh bằng OAuth.
Đọc được mọi thứ, **ghi được thông tin video đã đăng**, và **đăng được video mới**
(mở 01/10/2026 theo yêu cầu chủ máy). Cố ý KHÔNG mở: **xoá video** — đăng nhầm thì
vào Studio xoá tay, máy không được phép.

## Luôn làm trước

Gọi `youtube_kiem_tra` trước khi kết luận bất cứ điều gì về kết nối. Đừng đoán từ lỗi.

## Mười lăm công cụ

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
| ⬆️ `youtube_dang_video` | **GHI:** đăng video MỚI. Mặc định `private` |
| ✍️ `youtube_phu_de_them` | **GHI:** gắn `.srt` vào video ĐÃ đăng — cần `force-ssl` |
| ✍️ `youtube_thay_hang_loat` | **GHI:** thay chữ trên **nhiều video**. Mặc định chỉ xem trước |
| ✍️ `youtube_anh_bia` | **GHI:** đặt ảnh bìa mới |
| ✍️ `youtube_tra_loi_binh_luan` | **GHI:** trả lời bình luận — cần thêm quyền `force-ssl` |

Công cụ nào nhận mã video thì nhận luôn link dán nguyên từ trình duyệt.

⛔ `youtube_thay_hang_loat` gọi lần đầu là **chỉ xem trước**. Đưa chủ máy duyệt danh
sách rồi mới gọi lại với `thuc_thi=true`. Mỗi video ghi tốn 50 đơn vị hạn mức ngày.

⛔ `youtube_sua_video` **hiện ngay với người xem**. Đưa chủ máy duyệt chữ rồi mới gọi.
Lưu snippet cũ ra file trước khi ghi — để hoàn tác được.

## Đăng video mới — đo rồi mới nói nhanh hay chậm

`youtube_dang_video(tep=, tieu_de=, mo_ta=, che_do=, tag=, ngon_ngu=, phu_de=)`.
Mặc định `private`; `public` phải nói rõ. Server **không có** công cụ xoá.

### Số đo thật (01/10/2026, video sửa van khoá khí, 1080×1920 · 30 ph)

| Việc | Số đo |
|---|---|
| Tốc độ tải lên thật | **1,68 MB/s** (13,4 Mbps) — 3,02 GB mất **30 phút** |
| NVENC `cq 21` (bản đã dùng) | 3,02 GB → 30 ph tải |
| NVENC `cq 26` | 1,60 GB → **16 ph** tải, chữ vẫn sắc |
| NVENC `cq 29` | 1,11 GB → 11 ph tải, nền bắt đầu bệt |
| Encode lại cả phim bằng NVENC | ~3 phút |

⚡ **Xuất bằng `-cq 26` thay vì `-cq 21`**: tốn thêm 3 phút encode, bớt 14 phút tải,
YouTube mã lại hết nên không mất gì nhìn thấy được. Đừng đo tốc độ mạng bằng mẫu
10–15 giây — mẫu ngắn vớ phải lúc mạng nhanh thì lệch hơn gấp đôi; lấy
`dung lượng ÷ thời gian thật` của lần tải trước.

### Soát TRƯỚC khi tải (server tự làm, đừng bỏ qua)

- **Kênh có được đăng video dài không** — `channels.list(part="status")
  .longUploadsStatus`: `allowed` / `eligible` (chưa xác minh) / `disallowed`.
  Video > 15 phút mà kênh `eligible` thì server **chặn luôn**, không tải.
  ⛔ Đừng ghi cứng cảnh báo "kênh chưa xác minh" theo độ dài file — bản cũ làm vậy
  nên kêu sai cả khi đã xác minh rồi.
- **Scope phụ đề** — gắn `.srt` cần `youtube.force-ssl`. Gắn hụt lúc đăng thì
  dùng `youtube_phu_de_them` gắn lại sau, khỏi đăng lại cả file. Thiếu thì server bỏ bước
  phụ đề và báo ngay, thay vì ăn `403 insufficient scopes` sau 30 phút tải.
- **Lành file** — `ffmpeg -v error -i <file> -f null -` trước mọi lần đăng.

### Mốc chương

Hiện ra khi: mốc đầu **đúng 00:00**, từ **3 mốc**, mỗi đoạn **≥ 10 giây**.
⛔ **Ghép intro vào đầu là lệch hết mốc.** Intro 4 giây thì cộng 4 giây cho mọi mốc,
và **gộp mốc đầu về 00:00** — để `00:00 Mở đầu` dài 4 giây là YouTube bỏ cả thanh chương.

### Ảnh bìa

Video quay dọc 1080×1920 **không có khung 16:9 nào dùng lại được** — phải dựng riêng
bìa **1280×720** (trần 2 MB). Cách đã dùng: nửa trái thẻ chữ bộ "Than hồng / Ember"
render bằng Playwright, nửa phải khung hình bắt mắt nhất cắt từ phim. Tiêu đề 86 px
mới đọc được ở cỡ thật 320×180. Đo mép chữ bằng pixel, đừng nhìn áng chừng.
Gắn bằng `youtube_anh_bia`.

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


## Ảnh và video dung lượng lớn — quy tắc chung cho toàn bộ AI (03/10/2026)

- Áp dụng cho Codex, Claude Code và mọi AI làm việc trên máy. Ảnh/video nguồn, video tải về, bản dựng, render, frame trích xuất và tài sản media dung lượng lớn phải lưu ở `F:\Kho-anh`, không lưu lâu dài trong `F:\Project` hoặc repository mã nguồn.
- Video và bộ tài sản YouTube: `F:\Kho-anh\10_Video\<ten-du-an>`. Ảnh theo nhóm nội dung trong kho; kết quả Photoshop vẫn theo `99_Xuat-Photoshop` và quy tắc sao chép ảnh xuất hiện có. Đọc `F:\Kho-anh\AGENTS.md` trước khi chọn nơi lưu.
- Project giữ mã nguồn, cấu hình, tài liệu phát triển và asset nhỏ cần để ứng dụng chạy/đóng gói. Media lớn dùng đường dẫn đến kho; khi chuyển phải kiểm tra tham chiếu và giữ đường dẫn tương thích nếu cần. Không tự xoá/di chuyển hàng loạt tài sản khác.
- `F:\Project\114_Youtube` đã chuyển vật lý sang `F:\Kho-anh\10_Video\114_Youtube`. Đường dẫn cũ là junction để phần mềm tiếp tục hoạt động; không tạo lại một bản dữ liệu độc lập tại vị trí cũ. Token/OAuth trong bộ này là dữ liệu riêng, không đưa vào repository công khai.
- Không mặc định kho ảnh được Google Drive sao lưu: hiện `F:\Kho-anh` chưa đăng ký đồng bộ. Junction chỉ giữ tương thích đường dẫn; chưa xác nhận Google Drive có theo liên kết này hay không.
