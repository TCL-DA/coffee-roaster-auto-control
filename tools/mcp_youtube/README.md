# MCP `otl-youtube` — kênh YouTube của công ty

Đọc mọi thứ, **sửa được thông tin video đã đăng**, và **lấy được lời thoại video**.
Không đăng video mới, không xoá video.

> **Bản 2.0** gộp việc của 5 dự án mã nguồn mở vào chung một server — xem
> [NGUON.md](NGUON.md) để biết lấy gì ở đâu, giấy phép ra sao, và chỗ nào cố ý làm
> khác bản gốc. Thư viện cần cài: [requirements.txt](requirements.txt).

## Công cụ

| Công cụ | Việc |
|---|---|
| `youtube_kiem_tra` | Đã nối được chưa, đang nối vào kênh nào. Gọi trước khi báo lỗi |
| `youtube_kenh` | Tên kênh, mô tả, ngày lập, người đăng ký, tổng video, tổng lượt xem |
| `youtube_video` | Danh sách video mới nhất trước, kèm lượt xem/thích/bình luận/thời lượng |
| `youtube_so_lieu` | Số liệu người xem theo khoảng ngày — gộp cả kênh, tách theo ngày, hoặc tách theo video |
| `youtube_binh_luan` | Đọc bình luận một video |
| ✍️ `youtube_sua_video` | **GHI:** đổi tiêu đề / mô tả / tag / chế độ riêng tư của video đã đăng |
| `youtube_loi_thoai` | Lời thoại video kèm mốc giờ. **Không cần OAuth** — chạy cả khi token hỏng, chạy cả trên video người khác |
| `youtube_danh_sach_phat` | Playlist của kênh, hoặc video bên trong một playlist |
| `youtube_tim_cong_khai` | Tìm video công khai của **người khác** (cần `api_key.txt`) |
| `youtube_phu_de` | Bản phụ đề chính thức đã tải lên kênh — cần thêm quyền `force-ssl` |
| ✍️ `youtube_thay_hang_loat` | **GHI:** thay chữ trong tiêu đề/mô tả của **nhiều video** cùng lúc. Mặc định chỉ xem trước |
| ✍️ `youtube_anh_bia` | **GHI:** đặt ảnh bìa mới cho video |
| ✍️ `youtube_tra_loi_binh_luan` | **GHI:** trả lời bình luận dưới tên kênh — cần thêm quyền `force-ssl` |

Mọi công cụ nhận mã video đều nhận luôn **link dán nguyên từ trình duyệt**.

### Muốn biết video quay gì thì dùng `youtube_loi_thoai`

Rẻ hơn hẳn cách cắt khung hình ra xem. Mốc `luc` trả về dán thẳng vào mô tả là
thành chương YouTube. Mặc định gộp lời thoại thành khối 30 giây cho gọn; đặt
`gop_giay` nhỏ hơn nếu cần mốc sát hơn, hoặc `chi_liet_ke=true` để xem video có
sẵn phụ đề tiếng gì.

### `youtube_thay_hang_loat` — luật dùng

Việc điển hình: đổi số điện thoại hay địa chỉ web cũ trên cả kênh.

- **Gọi lần đầu là chỉ XEM TRƯỚC**, không ghi gì. Đưa chủ máy duyệt danh sách rồi
  mới gọi lại với `thuc_thi=true`.
- Có trần `so_luong` (mặc định 20, tối đa 100) để lỡ tay cũng không sửa sạch cả kênh.
- Mỗi video ghi tốn **50 đơn vị** hạn mức ngày (cả ngày có 10.000, Google đặt lại
  lúc 14:00 giờ Việt Nam). Sửa 100 video là hết nửa hạn mức.

### Hai công cụ cần cấp thêm quyền

`youtube_phu_de` và `youtube_tra_loi_binh_luan` cần
`https://www.googleapis.com/auth/youtube.force-ssl`, chưa có trong `QUYEN`. Gọi thử
thì công cụ tự báo đúng các bước cần làm. Thêm quyền phải **xoá `token.json` và cấp
quyền lại** — token cũ không tự có thêm quyền được.

### `youtube_sua_video` — luật dùng

- Sửa xong **hiện ngay với người xem**. Phải đưa chủ máy đọc và duyệt chữ mới rồi mới gọi.
- Trường nào không truyền thì giữ nguyên; trả về cả `truoc` và `sau` để đối chiếu.
- `mo_ta` và `tag` **ghi đè cả khối**, không nối thêm — muốn giữ phần cũ thì đọc bằng
  `youtube_video` rồi gửi lại cả bài.
- Giới hạn của Google: tiêu đề ≤ 100 ký tự, mô tả ≤ 5000, tổng các tag ≤ 500.

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

Server này cố ý không có công cụ đăng/xoá. Thêm quyền `youtube.upload` mà không sửa server
thì vẫn không đăng được gì — đó là chủ ý.

## Thêm quyền thì phải làm đủ 3 việc

Sót một việc là "chạy không lỗi mà chẳng thấy gì đổi":

1. Thêm scope vào `QUYEN` trong `F:\Project\114_Youtube\cap_quyen.py`.
2. Thêm đúng scope đó vào `QUYEN` trong `server.py` của thư mục này.
3. **Xoá `token.json`** rồi chạy lại `cap_quyen.py` (bấm đồng ý trên trình duyệt) —
   không xoá thì Google trả lại đúng bộ quyền cũ.

Rồi **khởi động lại Claude Code**: server MCP nạp một lần lúc mở phiên, sửa `server.py`
giữa phiên thì công cụ mới chưa xuất hiện.

## Bẫy đã trả giá — đọc trước khi dùng

1. ⛔ **`youtube_video` trả MỚI NHẤT TRƯỚC.** Đừng cho chạy qua `tail` rồi kết luận — làm vậy
   là đọc nhầm sang video cũ nhất. Đã có lần vì vậy mà tưởng kênh chỉ có 5 video (thật ra hơn 80).
2. ⛔ **YouTube từ chối dấu `<` và `>`** trong tiêu đề lẫn mô tả, trả `400 invalidDescription`
   mà không nói ký tự nào. `youtube_sua_video` đã chặn trước và báo đúng chỗ sai.
3. ⛔ **Đừng đọc lại bằng `youtube_video` để xác nhận vừa ghi xong** — vài giây đầu YouTube
   còn trả bản cũ. Trường `sau` trong kết quả trả về mới là bản thật, lấy thẳng từ `videos().update()`.
4. **`statistics.videoCount` chỉ đếm video CÔNG KHAI**, và tab Video của Studio không tính Shorts
   trong khi playlist uploads thì có — hai chỗ đếm lệch nhau là bình thường.
5. **Thêm scope không tự có hiệu lực**: sửa `cap_quyen.py` + `QUYEN` trong `server.py`,
   **xoá `token.json`**, chạy lại `cap_quyen.py`, rồi **khởi động lại Claude Code**.
   Kiểm quyền thật sự được cấp bằng `oauth2.googleapis.com/tokeninfo`, đừng tin mỗi file token.
6. **Đọc phụ đề tự động** (`captions()`) đòi scope `youtube.force-ssl` — scope đó cho phép cả
   xoá video, nên không tự thêm.
7. ⛔ **Không tải được video từ YouTube về** (SABR-only streaming) — muốn xem nội dung thì
   phải có file gốc trên đĩa. Cách xem: skill [`youtube-otl`](../../.claude/skills/youtube-otl/SKILL.md).
