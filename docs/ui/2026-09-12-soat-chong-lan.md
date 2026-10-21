# Soát chồng lấn & tràn khung toàn app — 12/09/2026

Soát bằng máy: mở đúng file HTML của app trong Chromium 1920×1080, đi hết **màn
khoá + 6 màn chính + 12 hộp thoại**, mỗi chỗ dò cặp phần tử đè nhau, chữ bị cắt,
phần tử lòi ra ngoài mép, nút nhỏ hơn ngón tay, và lỗi JS. Bộ kiểm giữ lại ở
`tools/test_ui_overlap.py`.

## Hai lỗi thật, đã vá

### 1. Thông báo che bàn phím PIN

Gặp trên **máy thật** khi đang đăng nhập: dải `CẢM BIẾN: ET ngoài dải đo` nằm
đúng hàng phím **1-2-3**, và toast `Đã gửi: Gas = 100` che phím **5** (máy đo
được: phủ 37%). Cả hai đều `pointer-events:none` nên **bấm vẫn trúng** — nhưng
thợ không **nhìn** thấy phím, tức là hỏng đúng việc nó sinh ra để làm.

Gốc: `#toast` neo `bottom:170px` (màn Rang đẩy lên 470px) và `#faultBanner` neo
`bottom:250px`, đều **giữa màn** — đúng chỗ mọi hộp thoại ngồi.

Vá: khi có `.overlay.on` thì cả hai **nép góc trên bên trái**
(`top:26px` / `top:140px`, `left:26px`, bỏ `translateX(-50%)`).

Hai thứ đã thử và bỏ:
- *Giữa đỉnh màn* — dải báo động lại đè lên hàng mốc TP · DE · FCs · DEV · DROP (80%).
- *Chỉ viết `#stage:has(.overlay.on) #toast`* — thua luật `#stage:has(#pane-rang.on)`
  (hai id) nên trên màn Rang thông báo vẫn nằm giữa. Phải viết kèm biến thể có
  `#pane-rang` cho đủ trọng số.

### 2. Bảng "Thao tác" (màn Rang) mở ra là lòi khỏi màn

Bảng rộng 470 đơn vị neo `right:0` vào nút nằm sát **mép trái**, nên đổ ngược ra
ngoài: cắt mất **43 px** ở 1920, 36 px ở 1600, 30 px ở 1366 — chữ "Chọn hồ sơ",
"Burner" đứt đôi. Vá: neo `left:0` (bên phải còn cả nghìn pixel trống).

Không dùng `vw` để kẹp: `#stage` đang scale nên `vw` không cùng hệ toạ độ.

## Đợt 2 — ba lỗi chỉ lộ ra khi MÁY ĐANG CHẠY (chủ máy chụp ảnh gửi về)

Bài soát đợt 1 chạy ở trạng thái **tĩnh**: chưa nối máy, ba ô ghi "Chưa có dữ
liệu", không có lệnh nào đang bay. Ảnh chụp màn hình thật có số thật mới lộ ra:

### 3. Băng trạng thái lệnh đè ô TỐC ĐỘ TRỐNG

`Gas = 71 · Trạng thái máy đã khớp` nằm đè ô trống **251×21 px**, che đúng nút ±
và con số. Gốc: `.ux-roastbar` ghim `bottom:154px` — rơi vào giữa cụm ba ô.
Vá: `bottom:392px`, tức ngay TRÊN ba ô. Đè mép dưới đồ thị thì vô hại, đè nút
điều khiển thì không.

### 4. Gợi ý "mức lần trước" đẩy ba ô chui xuống dưới thanh nút

Đây là **lỗi tự gây** khi thêm tính năng nhớ mức hôm nay: dải gợi ý làm thành một
hàng riêng trong lưới, đẩy ba ô từ `[794..957]` xuống `[860..989]` — thò khỏi
khung 32 px và chui xuống dưới thanh nút đáy (`top 971`), cắt mất con số phần
trăm. Cụm này **cao cố định**, nên mọi thứ thêm vào phải tốn **0 px**.

Vá: bỏ hẳn dải riêng, đưa gợi ý vào **dòng chú thích sẵn có của từng ô**
("lần trước 71% · chạm để áp"). Chạm để áp **một** ngõ ra; gas hỏi lại, gió và
trống thì không — bắt xác nhận thứ vô hại chỉ dạy thợ bấm "Đồng ý" theo phản xạ.

Kèm một lỗi con: `.outlast{display:flex}` **đè thuộc tính `hidden`**, nên dải đó
không bao giờ ẩn được — nó hiện cả khi chưa có gì để gợi ý.

### 3b. Băng trạng thái lệnh: dời hẳn lên THANH ĐẦU

Vá lần đầu chỉ dời băng từ `bottom:154px` lên `392px` — hết đè ô Tốc độ trống thì
quay ra đè hàng pha **Sấy · Maillard · Phát triển** (chủ máy chụp ảnh khoanh đỏ).
Kết luận: **thân màn Rang kín chỗ**, không có chỗ nào cho một băng chữ chạy ngang.

Nay băng đó sống trên **thanh đầu**, trong khoảng trống giữa dãy tab và chip
"Máy rang · trực tiếp" — và đó còn là chỗ đúng hơn về nghĩa: nó là trạng thái của
MÁY, nằm ngay cạnh chip kết nối máy. Câu dài nhất ("Chưa xác nhận từ máy · kiểm
tra trạng thái trước khi thao tác tiếp") tự cắt đuôi, rộng 390px, không xô hàng.

### 3d. Bỏ toast cho lệnh máy — một việc đừng báo hai chỗ

Dời băng lên thanh đầu xong thì lộ ra cái thứ hai: toast `Đã gửi: Trống = 49`
vẫn nổi giữa màn, nói **trùng** với băng `Trống = 49 · Trạng thái máy đã khớp`
ngay trên thanh đầu — mà băng còn nói kỹ hơn (có chặng máy xác nhận).

Nay `machCmd()` **không toast khi gửi được**. Lệnh HỎNG thì vẫn toast (máy từ
chối · chưa nối máy · lỗi gửi) — thứ đó phải đập vào mắt.

Bộ kiểm `test_ui_toolbar.py` có một phép canh "có báo cho thợ biết" soi vào
`#toast`; đã trỏ sang `#uxCommand`. **Ý của phép kiểm giữ nguyên**, chỉ đổi kênh.

### 3c. Ô ngày màn Lịch sử hiện `dd-----yyyy` — ĐÍNH CHÍNH ghi chú cũ

Ghi chú trong mã (07/09) nói đây chỉ là chuyện của Chromium headless lúc chạy
test, app đóng gói không bị. **Sai** — ảnh app thật 12/09 vẫn thấy, và tái lập
được trong **Edge thật** (cùng nhân WebView2).

Gốc: ô `<input type="date">` của Chromium lấy **định dạng ngày của Windows**, máy
xưởng đang đặt `sShortDate = dd-MMM-yy`. Đặt `lang` trên ô hay trên trang đều vô
ích (ghi chú cũ đã thử đúng, chỉ kết luận sai nguyên nhân).

Vá ở chỗ khởi động WebView2: thêm `--lang=vi-VN` → gợi ý thành `nn/mm/yyyy`.
Đã thử `en-GB`: **vẫn hỏng** — Chromium rơi về định dạng Windows khi locale cùng
hệ. Nhãn cạnh ô đổi sang **chữ** ("ngày/tháng/năm") thay vì mã chữ cái, để máy
khách đặt Windows kiểu nào nhãn cũng không nói sai.

### 5. Viên trợ lý đậu lên tiêu đề

Chủ máy kéo viên trợ lý lên sát mép trái phía trên; chỗ đó đè đúng tiêu đề của cả
bốn màn ("Chưa chọn hồ sơ", "☕ Hồ sơ rang", "3 mẻ đã lưu"). Kéo được nên không ai
gọi là lỗi, nhưng đã đậu là đậu mãi. Vá: **26% chiều cao trên cùng là vùng cấm
đậu** — đủ lọt thanh đầu + tiêu đề + phụ đề, vẫn còn gần hết mép trái cho thợ.

## Không phải lỗi

- **"Nút nhỏ 33 px"** — sân khấu scale 0,75 trên màn 1920, nên nút khai báo 44
  đơn vị đo ra 33 px thật. Không phải code sai; nếu muốn 44 px THẬT trên panel
  1920 thì phải nâng chuẩn lên ~59 đơn vị. **Chờ chủ máy quyết.**
- **Phần tử "tràn mép" khi bảng Thao tác đang đóng** — Chrome giữ hộp bố cục của
  `<details>` đóng (content-visibility), nên nó vẫn có toạ độ dù không được vẽ.
  Bộ dò phải lọc `details:not([open])`, không thì báo động giả tràn màn hình.
- **Thông báo đè lên nền phía sau hộp thoại** — nền đang bị làm mờ và không bấm
  được, đè lên đó không ảnh hưởng ai. Chỉ tính khi đè lên **thẻ hộp thoại**.

## Kết quả sau khi vá

40 phép đo trên 19 màn/hộp: **không chỗ nào chồng lấn, không gì lòi ra ngoài
màn, không lỗi JS**. Đã chứng minh bộ kiểm không vô dụng: gỡ bản vá số 2 ra là
nó bắt ngay (`[-43, 310, 1920]`).

Bản thiết kế gốc Claude Design **không kéo về được** trong phiên này —
`/design-login` chỉ chạy ở phiên tương tác (bẫy đã ghi trong
`docs/ui/` và trí nhớ). Đối chiếu theo bản mirror `docs/ui/design-web/`.
