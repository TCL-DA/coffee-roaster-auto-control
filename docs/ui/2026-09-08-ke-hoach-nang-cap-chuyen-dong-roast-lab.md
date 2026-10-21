# Kế hoạch nâng cấp chuyển động và tương tác Roast Lab

Ngày lập: 08/09/2026. Người lập: Codex. Người triển khai dự kiến: Claude Code.

**Bản soát 08/09/2026 — Claude Code, hai vòng.**

*Vòng một, đối chiếu với mã.* Mọi mốc dòng và tên hàm trong mục 3 đều ĐÚNG, mọi file
tham chiếu đều tồn tại; sơ hở nằm ở *tiền đề và phạm vi*, không ở dữ kiện. Kết quả ở
**mục 3.1** (12 điểm can thiệp bị bỏ sót, mã S1–S12) và các đoạn **[SOÁT 08/09]**.

*Vòng hai, đối chiếu với nguồn Claude Design.* Kéo về từ project `Menu cài đặt nhanh
- Lỗi thiết kế`, đọc cả mã tương tác lẫn 14 ảnh chủ máy dán vào để chỉ lỗi. Kết quả
đảo ngược trọng tâm của kế hoạch: **bản thiết kế được duyệt không có chuyển động** và
tồn tại để chữa lỗi chữ bị cắt. Kết quả ở **mục 3.2**, và thứ tự các đợt ở mục 6 đã
được xếp lại theo đó.

Đọc mục 3.2 rồi tới 3.1 TRƯỚC khi bắt tay bất cứ đợt nào.

## 1. Mục tiêu và phạm vi bàn giao

Áp dụng các ý tưởng tương tác trong danh sách hiệu ứng Apple để Roast Lab dễ theo dõi, thao tác rõ ràng và chuyển màn mượt hơn. Giữ bản sắc Than hồng, chữ IBM Plex và bố cục đã thống nhất trong Claude Design.

Tài liệu này là kế hoạch triển khai, không phải báo cáo tính năng đã hoàn thành. Codex đã kiểm tra mã nguồn và tài liệu; chưa chạy app, chưa đo hiệu năng hoặc kiểm chứng cảm ứng trong đợt lập kế hoạch. Chỉ tạo tài liệu này, không sửa app, firmware hay khoá giao diện.

Phạm vi mặc định: triển khai P0–P5 bên dưới theo thứ tự. Các mục tuỳ chọn ở phần 9 không thuộc đợt mặc định. Không bổ sung nhận diện khuôn mặt, thu âm, tích hợp iOS hay thay đổi giao thức điều khiển chỉ để phục vụ hiệu ứng.

**[SOÁT 08/09 — vòng hai] Phạm vi mặc định đã đổi.** Đối chiếu với nguồn thiết kế cho
thấy mục tiêu ở trên đặt sai trọng tâm: bản thiết kế chủ máy duyệt không xin hiệu ứng,
nó xin chữ đọc được và một cái chốt an toàn (mục 3.2). Phạm vi mặc định mới là
**PD → P1 → P3**, theo thứ tự đó. **P2, P4 và P5 chuyển sang diện chờ chủ máy duyệt**
vì cả ba đều thêm thứ không có trong bản thiết kế, riêng P5 còn đi ngược nó. Mục tiêu
của đợt vì thế đọc lại là: *làm app khớp bản thiết kế đã duyệt, rồi mới chuẩn hoá
chuyển động quanh phần đã khớp*.

## 2. Nguồn cần đọc và quy tắc cộng tác

Trước khi viết mã:

1. Đọc `AGENTS.md`, `CLAUDE.md` và `docs/ui/UI-LOCK.md` hiện hành.
2. Đọc `docs/ui/2026-09-07-design-spec.md` và bản mirror `docs/ui/design-web/Rang - Sua lai.dc.html`. Không sửa mirror. Đặc tả có thể chậm hơn mã; xác minh các mục ghi còn thiếu trước khi sửa.
   **[SOÁT 08/09]** Đọc mirror cho hết, kể cả khối `<script type="text/x-dc">` ở cuối
   file — đó không phải mã khung sườn mà là **đặc tả tương tác**: bậc nhảy nút, nhịp
   lặp khi giữ, và cơ chế giữ-1-giây để xác nhận. Xem thêm `uploads/` trong cùng thư
   mục: 14 ảnh chủ máy dán vào để chỉ lỗi, có ảnh ông tự vẽ mũi tên đỏ. Đó là lời
   phàn nàn gốc, đọc trước khi quyết làm gì.
3. Áp dụng Open Design tại `F:/Project/open-design/craft/animation-discipline.md`, `state-coverage.md` và `accessibility-baseline.md`. Nói rõ nếu chỉ dùng quy tắc mà không chạy engine.
4. Kiểm tra `git status`, giữ mọi thay đổi đang có. Không khôi phục toàn file từ bản sao cũ và không dùng `git add -A`.
5. Xử lý khoá trước khi sửa HTML hoặc `tools/test_ui_*`, sao lưu trước mỗi đợt lớn vào `docs/ui/backup/`, ghi phạm vi và kết quả rồi trả khoá theo quy ước dự án.

Tại thời điểm kiểm tra, `UI-LOCK.md` ghi **CODEX ĐANG GIỮ** cho tích hợp trợ lý. Đây là thông tin để Claude kiểm tra lại chủ sở hữu trước khi sửa, không phải quyền tự xoá khoá. Yêu cầu người dùng hiện tại là lập kế hoạch để Claude code; nếu có bàn giao quyền sửa rõ ràng từ người dùng thì áp dụng quy tắc ưu tiên người dùng trong AGENTS.md. Không suy ra khoá hết hiệu lực chỉ từ ngày cũ.

Chú thích và tài liệu mới dùng tiếng Việt có dấu, UTF-8. Giữ tên biến, định danh và chuỗi debug bằng tiếng Anh. Báo cáo chỉ bằng chữ; không tạo bộ ảnh, GIF hoặc video bàn giao. Có thể kiểm tra hình ảnh nội bộ khi cần.

## 3. Hiện trạng đã xác minh từ mã

Các số dòng dưới đây là mốc tìm kiếm tại thời điểm lập kế hoạch; tìm bằng tên hàm/selector vì file đang được chỉnh sửa.

| Vị trí | Hiện trạng | Hệ quả triển khai |
|---|---|---|
| `OTL Roast Lab.html`, khoảng dòng 1562–1679 | Chuyển pane, overlay, nền tab; `data-motion="full/reduced"`; media query giảm chuyển động | Mở rộng cơ chế hiện có, không thêm hệ tuỳ chọn trùng lặp |
| `#pane-rang` | Chuyển mờ riêng, không dịch chuyển cả màn | Giữ cụm điều khiển ổn định |
| `#stage`, khoảng dòng 135 | `touch-action:none` | Rà toàn chuỗi phần tử cha khi mở cuộn/zoom cảm ứng |
| Sự kiện `wheel`, khoảng dòng 3879 | Chặn `Ctrl + wheel` toàn tài liệu | Phân định zoom đồ thị và hành vi toàn app trước khi sửa |
| `gotoTab()`, khoảng dòng 3910 | Điểm chuyển màn | Móc vòng đời chuyển cảnh và thanh theo dõi mẻ |
| `applyMachine()`, khoảng dòng 5438 | Điểm cập nhật dữ liệu máy | Dùng trạng thái thật, giữ cách xử lý dữ liệu thiếu |
| `drawChart()`, khoảng dòng 7262; `#chart` | Đồ thị rang chính | Tách vùng xem khỏi dữ liệu và điều khiển máy |
| `drawBatchCurve()`, khoảng dòng 4374; `#bdCanvas`, `#cmpCanvas` | Đồ thị chi tiết mẻ và so sánh | Bắt đầu zoom ở đây trước đồ thị trực tiếp |
| `#peCurve` | Canvas trong trình sửa hồ sơ | Chưa bật cử chỉ zoom mặc định nếu xung đột thao tác sửa điểm |
| `personalSet()`, khoảng dòng 8743 | Tuỳ chọn chuyển động đang tồn tại | Giữ tương thích cấu hình đã lưu |
| Các vùng dùng `backdrop-filter` | Đã có kính mờ | Không coi blur hiện tại là khúc xạ Liquid Glass hoàn chỉnh |
| `tools/roast_assistant_ui.js` | Module trợ lý riêng đang có trong worktree | Đọc đường tích hợp thực tế trước khi thêm chuyển cảnh |

Có sẵn `tools/test_ui_layout_motion.py` kiểm tra nền tab, giảm chuyển động và màn rang không trượt. Các kiểm thử hiện có là điểm xuất phát, không phải bằng chứng đã đạt trong đợt này.

## 3.1. [SOÁT 08/09] Điểm can thiệp bị bỏ sót

Mười hai mục dưới đây kiểm chứng bằng cách đọc mã ngày 08/09/2026. Chúng làm đổi
phạm vi của P2, P3, P4 và P5, nên phải xử lý trong P0 chứ không để phát hiện giữa đợt.

| # | Sự thật trong mã | Vì sao kế hoạch cần sửa |
|---|---|---|
| S1 | `tools/roast_lab_hmi.py` khoảng dòng 1659–1667 phục vụ **chính** `OTL Roast Lab.html` cho điện thoại/tablet, đóng dấu `window._OTL_WEBCLONE` rồi chèn `/assistant.js` | Mọi hiệu ứng đều xuất xưởng kèm bản web. P4 (pinch) và P5 (kính) sẽ chạy trên Safari iOS và Chrome Android, không chỉ WebView2 |
| S2 | `grep assistant "OTL Roast Lab.html"` = **0 kết quả**. Trợ lý chỉ tồn tại ở bản web; `#ra-panel` là `position:fixed; z-index:99999`, nằm **ngoài** `#stage`, đo bằng pixel thật | Genie và Orb ở mục 4/9 hiện chỉ áp được cho bản web. Chuyển cảnh giữa panel pixel-thật và nút trong stage đã scale phải quy đổi hệ số |
| S3 | `fit()` khoảng dòng 3846–3858 đặt `#stage` rộng 2260–3440 px, cao 1440, rồi `transform:scale(k)`; `odPositionMenu()` cuối file đã phải tính `k = r.width / stage.offsetWidth` | Zoom quanh con trỏ ở P4 phải chia toạ độ cho `k`. Đo phần tử phải dùng `offsetWidth/offsetHeight`, không dùng thẳng `getBoundingClientRect()` |
| S4 | Hai canvas dùng `devicePixelRatio` đơn thuần (`drawBatchCurve` ~4378, `drawChart` ~7264), **không** nhân `k` | Trên màn 4K `k` có thể ≈ 1,5 nên canvas bị kéo giãn. Tiêu chí "canvas nét đúng tỉ lệ điểm ảnh" của P4 sẽ đạt sai nếu không sửa cùng lúc |
| S5 | Khối `CHỐT CHẶN TOUCH` khoảng dòng 3876–3881 chặn toàn tài liệu **năm** thứ: `contextmenu`, `gesturestart`, `Ctrl+wheel`, `dblclick`, `Ctrl` + `= - + 0` | Kế hoạch mới chỉ thấy `Ctrl+wheel`. `gesturestart` giết pinch trên iPad/iPhone; `dblclick` giết cử chỉ chạm đúp để về toàn mẻ |
| S6 | `Ctrl` + `+ - 0` đã bị chặn từ trước, tức **zoom trợ năng của trình duyệt đã tắt theo chủ ý kiosk** | Câu ở P4 "tránh phá zoom truy cập ngoài đồ thị" dựa trên tiền đề sai. Phải chốt rõ giữ nguyên hay mở lại, và ghi lý do |
| S7 | Khoảng dòng 3869–3874: `Escape` bật/tắt toàn màn hình qua pywebview, chỉ nhường khi có `.overlay.on`, `dialog[open]` hoặc `.usermenu.on` | Bảng chi tiết mới của P2/P3 nếu không mang đúng một trong ba dấu hiệu đó thì `Escape` sẽ nhảy fullscreen thay vì đóng bảng — trái yêu cầu 5.3 |
| S8 | Hai cơ chế đè-giữ đang chạy: tooltip `data-help` bật sau 700 ms (~8675) và nút `±` gas/gió/trống tự lặp lệnh sau 450 ms rồi mỗi 250 ms (~5782–5790) | Pinch trên đồ thị có tổ tiên `data-help` sẽ bật tooltip giữa chừng. Mở `touch-action:pan-y` ở vùng chứa nút `±` sẽ sinh `pointercancel` cắt chuỗi lặp — chiều ngược lại của "cuộn không biến thành nhấn thẻ" |
| S9 | Trong 26 khai báo `animation` chỉ có **10** luật gắn `html[data-motion="full"]`. Tám animation `infinite` (`lkblink` 174, `igBreath` 420, `igHeat` 428, `dropPulse` 483, `flameblink` 612, `chargePulse` 635, `fbPulse` 935, `phblink` 1165) chỉ tắt được bằng media query hệ điều hành (958, 1679) | Tuỳ chọn **Giảm chuyển động trong app** hiện phủ chưa tới nửa. Nghiệm thu P1 đang viết như thể việc này đã chạy; thực tế là việc phải làm, và đo được bằng con số 10/26 |
| S10 | Dòng ~2053 `#topbar .livetemps{display:none}` **không** có tiền tố `html:has(#pane-rang.on)` nên ẩn toàn app; markup BT/ET ở ~2722–2725 không bao giờ hiện. Thêm `@media(max-width:1700px)` (~1926–1929) đẩy topbar xuống hai hàng | Tiền đề "vùng thanh đầu có chỗ" của P2 sai theo cả hai chiều: chỗ đang bị chiếm bởi mã chết, và trên gần như mọi laptop topbar đã phải xuống hàng. **Đính chính ở mục 3.2:** thiết kế không đặt BT/ET trên thanh đầu, nên `display:none` là đúng — xoá markup chết, đừng hồi sinh |
| S11 | Toàn bộ giao diện nằm trong `#stage` rộng 2260–3440 px, nhưng các `@media(max-width:…)` lại đo **cửa sổ thật** | Ngưỡng đáp ứng mới phải bám biến do `fit()` đặt hoặc container query. Thêm media query nữa là lặp lại bẫy cũ của dự án |
| S12 | App dịch bằng `I18N[LANG]` + 147 thuộc tính `data-i18n` + hàm `t(vi,en)` (~4845–4853); `tools/test_ui_audit.py` giữ hàm `PROBE` bắt tràn `min-width:auto` và được các bộ kiểm khác nhập lại | Chuỗi mới ở P2/P4 chưa có đường vào i18n; phần tử mới ở topbar chưa có ai bắt nó qua `PROBE` |

## 3.2. [SOÁT 08/09] Đối chiếu với nguồn Claude Design

Nguồn: project `Menu cài đặt nhanh - Lỗi thiết kế`
(`3c3a6a49-faff-4902-a214-f071ccd6006f`), mirror ở `docs/ui/design-web/`. Bản mirror
ngày 07/09 trùng khớp danh sách file trên nguồn nên không cần kéo lại.

### Bản thiết kế được duyệt là bản TĨNH

Đo trên toàn file `Rang - Sua lai.dc.html`:

| Thứ | Số lần trong bản thiết kế |
|---|---|
| `transition:` | **0** |
| `animation:` và `@keyframes` | **0** |
| `backdrop-filter`, `blur()` | **0** |
| `transform:` | **1** — đúng một cái, là `scale()` để vừa màn |

Nền panel trong thiết kế là màu đặc: `#15151A`, `#16161B`, `#101013`. Vì vậy câu mở
đầu mục 1 — "giữ bố cục đã thống nhất trong Claude Design" — chưa được kiểm chứng khi
viết kế hoạch, và **P5 Liquid Glass mâu thuẫn trực tiếp với nguồn thiết kế**.

### Tương tác DUY NHẤT được thiết kế, mà kế hoạch bỏ sót

Thiết kế quy định **giữ 1 giây để xác nhận**, có thanh tiến trình đỏ chạy trong lòng
nút (`width: {{ dumpProgress }}`, nền `#D93A32` opacity 0,22), huỷ khi nhả tay, và bốn
trạng thái nhãn. Áp cho ba hành động:

| Hành động | Chuỗi nhãn theo thiết kế |
|---|---|
| Xả liệu | `Xả liệu` → `Đang giữ…` → `Đã xả liệu` |
| Kết thúc mẻ | `Kết thúc mẻ` → `Đang giữ…` → `Đã kết thúc mẻ` |
| Thoát ứng dụng | `Giữ 1 giây để thoát` → `Đang giữ…` → `Đang tắt…`; khi đang rang thì chặn hẳn, nhãn `Không thể tắt khi đang rang`, con trỏ `not-allowed` |

Trong app, `#btnEscape` (~3138) và `#btnDrop` (~3146) là `onclick` thẳng; `cmdDrop`
(~5890) gọi `machCmd` ngay, không giữ và không hỏi lại. `askConfirm` hiện chỉ dùng cho
xoá hồ sơ và cho ca "chưa có lửa vẫn mở cửa nạp".

Đây vừa là mục duy nhất của kế hoạch có chỗ dựa trong nguồn thiết kế, vừa là mục có
hậu quả vật lý nặng nhất nếu bỏ qua. Nó thành đợt **PD** ở mục 6.

### Bảng lệch giữa thiết kế và app

| Điểm | Thiết kế | App | Xử lý |
|---|---|---|---|
| BT/ET/đồng hồ trên thanh đầu | **không có**; thanh đầu chỉ có logo, nav, nhãn kết nối. BT 86 px, ET 42 px, đồng hồ 72 px nằm ở cột phải màn Rang | markup còn nhưng bị `display:none` (S10) | Luật `display:none` đang **thi hành đúng thiết kế**. Xoá hẳn markup chết, **không** hồi sinh — đính chính khuyến nghị ở S10 |
| Bậc nhảy nút `±` | chạm ±10, giữ lặp ±5 mỗi **130 ms** | ~~chạm ±1~~ → **ĐÍNH CHÍNH: chạm ±5**, giữ lặp ±5 mỗi 250 ms | `data-d="1"` chỉ là CHIỀU, độ lớn nằm ở `OUT_STEP=5`. Bản soát đầu đọc nhầm `data-d` thành bậc nhảy. **Đã chốt và đã làm 08/09** — xem PD-4 ở mục 6 |
| Kích thước nút `±` | 68 px trên khung 1920 | 92 px trên khung 2560 | **Khớp** (68 × 1,353). Phần hình học port rất trung thực, không đụng tới |
| Khung cơ sở | 1920 × 1080, letterbox thuần | 2560 × 1440, nở ngang 2260–3440 | Mọi px lấy từ thiết kế phải **nhân 1,333** trước khi dùng |
| Làm nóng | thiết kế hiện "còn ~5 phút", quy từ chênh nhiệt | — | Bảng trạng thái ở P2 lại **cấm** quy nhiệt độ thành thời gian. Về kỹ thuật kế hoạch đúng, nhưng nó đang bác một thứ chủ máy đã duyệt — phải hỏi, không tự bỏ |

### Chủ máy thật sự phàn nàn chuyện gì

Từ ảnh trong `docs/ui/design-web/uploads/`:

- Số bị bóp mất sạch: hàng điều khiển chỉ còn `Mức gas ——%`, `Lượng gió ——%`,
  `Tốc độ trống ——%`; nhãn và dấu `%` còn, con số biến mất.
- Nhãn bị cắt cụt giữa chữ: `Nhiệt hạt (BT`, `Nhiệt khí (ET`.
- Menu cài đặt nhanh tràn ngang: IP cụt thành `192.168.1.44:8…`, có thanh cuộn ngang
  trong menu, chữ "Web điện thoại" gãy ba dòng.
- Mũi tên đỏ chủ máy tự vẽ, chỉ vào khối `THIẾT BỊ PHỤ` đang bị thu gọn khó thấy.
- Biểu tượng thành ô vuông vì thiếu glyph.

Không mục nào là chuyển động. Tất cả là **chữ bị cắt và ô bị bóp** — đúng nhóm mà hàm
`PROBE` trong `tools/test_ui_audit.py` bắt được. Một phần đã được vá trong các đợt
07/09; đợt này phải xác nhận lại bằng bộ kiểm chứ không tin vào nhật ký.

## 4. Ma trận 15 nhóm hiệu ứng

| Nhóm | Quyết định | Vị trí và giới hạn |
|---|---|---|
| Genie | Tuỳ chọn | Thu bảng trợ lý về nút mở; ưu tiên scale/translate đơn giản, không uốn toàn cửa sổ |
| Cover Flow | Tuỳ chọn | Duyệt hồ sơ dạng thẻ đường cong; lưới vẫn mặc định; không tự chạy carousel |
| Parallax | Hoãn | Chỉ cân nhắc nền đăng nhập/Giới thiệu; không dùng tại màn Rang |
| Rubber-band/Bounce | Tuỳ chọn | Kéo bảng phụ tới giới hạn; không ảnh hưởng nút điều khiển hoặc bảng số |
| Inertial Scrolling | P3 | Cuộn danh sách và hội thoại bằng nền tảng; không viết bộ vật lý cuộn toàn app |
| Pinch-to-Zoom | P4 | Lịch sử, so sánh rồi đồ thị trực tiếp; có thao tác chuột và bàn phím tương đương |
| App Zoom | P3 | Từ thẻ/dòng đã chọn mở chi tiết; đóng về nguồn khi nguồn còn tồn tại |
| Card Transition | P3 | Chuyển chi tiết và bảng phụ; huỷ chuyển cảnh cũ khi người dùng chuyển nhanh |
| Dynamic Island | P2 | Ô trạng thái thu gọn/mở rộng nằm trong app, không mô phỏng phần khoét camera |
| Liquid Glass | P5 | Menu, điều hướng, bảng nổi; nền số đo và đồ thị giữ kín |
| Live Activities | P2 | Theo dõi mẻ khi đang ở màn khác, dùng chung ô trạng thái |
| Face ID animation | P1/P3 | Mượn vòng chờ/dấu kiểm cho xác nhận; không giả có sinh trắc học |
| Siri waveform/orb | Tuỳ chọn | Phản hồi trợ lý xử lý; không hiện sóng ghi âm nếu chưa có thu âm thật |
| Activity rings | Hoãn | Chỉ xem xét cho mục tiêu sản lượng khi đã có dữ liệu/mục tiêu rõ |
| Message effects | Hoãn | Không confetti khi đang rang; chưa cần trong phạm vi mặc định |

Các tên Apple là nguồn cảm hứng. Dynamic Island/Live Activities ở đây là giao diện trong Roast Lab, không phải tích hợp API hệ thống Apple. Không cam kết tái tạo chính xác hiệu ứng độc quyền/native trên WebView2.

**[SOÁT 08/09 — vòng hai] Bảng trên được xếp lại theo nguồn thiết kế:**

| Nhóm | Quyết định cũ | Quyết định mới | Lý do |
|---|---|---|---|
| **Giữ 1 giây để xác nhận** | *không có trong bảng* | **PD — làm đầu tiên** | Tương tác động DUY NHẤT bản thiết kế quy định, và app đang thiếu (mục 3.2) |
| Face ID animation | P1/P3 | **PD** | Đây chính là "vòng chờ" mà thiết kế đã vẽ sẵn dưới dạng thanh tiến trình giữ. Không cần mượn ẩn dụ sinh trắc học nữa, cứ theo thiết kế |
| Dynamic Island | P2 | **Chờ chủ máy duyệt** | Thiết kế không có ô trạng thái; và nó thêm lại đúng thứ thiết kế vừa gỡ khỏi thanh đầu |
| Live Activities | P2 | **Chờ chủ máy duyệt** | Như trên, cùng một widget |
| Pinch-to-Zoom | P4 | **Chờ chủ máy duyệt** | Thiết kế vẽ đường cong bằng `polyline` tĩnh, không có vùng xem tách rời. Không phải sai, nhưng là phát minh ngoài thiết kế |
| Liquid Glass | P5 | **BỎ** | Thiết kế có 0 điểm blur và dùng nền đặc. Chỉ làm nếu chủ máy đổi ý bằng lời |
| Inertial Scrolling · App Zoom · Card Transition | P3 | **P3, giữ nguyên** | Không mâu thuẫn thiết kế, và chữa đúng lời phàn nàn "khối Thiết bị phụ bị thu gọn khó thấy" |

Ba nhóm còn lại của diện tuỳ chọn (Cover Flow, Rubber-band, Siri orb) và ba nhóm hoãn
(Parallax, Activity rings, Message effects) giữ nguyên trạng thái cũ.

**[SOÁT 08/09]** Hai điều chỉnh nữa. Thứ nhất, Genie và Siri orb hiện chỉ
áp được cho **bản web** vì trợ lý chưa có trong HTML (S2); nếu Codex tích hợp xong
vào HTML thì mới xét lại phạm vi. Thứ hai, mọi nhóm đều có hai đích chạy chứ không
một: WebView2 trên máy vận hành **và** trình duyệt điện thoại qua web clone (S1) —
quyết định "làm" cho một nhóm là cam kết cho cả hai, hoặc phải ghi rõ nhóm đó tắt ở
bản web và tắt bằng cách nào.

## 5. Quy tắc thiết kế và hành vi chung

### 5.1. Bộ chuyển động

- Phản hồi nhấn: 80–120 ms; không trì hoãn xử lý sự kiện để đợi chuyển động.
- Xác nhận trạng thái: khoảng 150 ms.
- Mở menu/bảng: 200–280 ms; đóng 150–220 ms.
- Mở thẻ thành chi tiết: 250–350 ms; không thêm màn chờ giả.
- Màn Rang: chỉ fade ngắn, tối đa khoảng 180 ms; không scale/trượt vùng thao tác máy.
- Ưu tiên `transform` và `opacity`; giới hạn animate kích thước ở ô trạng thái nhỏ có vùng bố trí ổn định. Không animate blur toàn màn hay vẽ lại toàn trang mỗi khung hình.
- Không tự chuyển chế độ Giảm chuyển động về Mượt mà khi nâng cấp. Tôn trọng cả tuỳ chọn app và hệ điều hành, trong đó yêu cầu giảm chuyển động luôn được ưu tiên.
- Khi giảm chuyển động: bỏ dịch chuyển, phóng, xoay và bounce; trạng thái vẫn hiện bằng chữ/biểu tượng. Cử chỉ zoom do người dùng điều khiển trực tiếp vẫn phải dùng được, bỏ phần quán tính/chuyển cảnh phụ.
- Dừng animation và dọn listener/timer khi đóng bảng, đổi màn hoặc huỷ tác vụ. Kiểm tra cả animation bằng JavaScript, không chỉ CSS.

### 5.2. Tính đúng của điều khiển

- Tách **đã nhấn**, **đang gửi**, **đã được xác nhận**, **lỗi/hết thời gian** theo khả năng API hiện tại.
- Đọc lại hợp đồng API để biết kết quả nào chỉ là đã nhận yêu cầu, kết quả nào là máy xác nhận. Không tự gắn nhãn “máy đã thực hiện” khi backend chưa cung cấp bằng chứng đó.
- Không optimistic success cho lệnh máy. Có thể phản hồi nhấn ngay nhưng chỉ báo thành công theo xác nhận thực tế.
- Không đổi thời gian giữ nút, điều kiện interlock, quyền điều khiển, chống gửi lặp hoặc cơ chế mất kết nối.
- Không đợi `animationend` để gửi lệnh, cập nhật số đo hoặc hiển thị cảnh báo.
- Không nội suy BT/ET/RoR thành số giả. Số và đồ thị phản ánh mẫu nhận được.
- Cảnh báo lỗi ưu tiên cao hơn trạng thái đẹp; mất kết nối không được hiểu thành tắt lửa hay máy dừng.

### 5.3. Khả năng đọc và truy cập

- Giữ màu BT/ET và token hiện có; không dùng kính làm thay đổi ý nghĩa màu.
- Nút chính giữ kích thước chạm tối thiểu theo hệ thống hiện tại. Không thu nhỏ để nhường chỗ cho ô trạng thái.
- Menu/bảng mở bằng bàn phím được; quản lý focus, Escape và trả focus về nguồn mở.
- Thông báo không khẩn cấp dùng vùng trạng thái phù hợp; không đọc lại BT mỗi mẫu qua screen reader.
- Mọi thao tác vuốt/zoom đều có nút hoặc phím tương đương, có focus nhìn thấy.

### 5.4. [SOÁT 08/09] Bốn ràng buộc kỹ thuật bắt buộc

Áp cho mọi đợt, không riêng đợt nào:

- **Quy đổi toạ độ.** Mọi mã đọc `clientX/clientY` hay `getBoundingClientRect()` để
  tính vị trí bên trong `#stage` phải chia cho hệ số scale của `fit()` (S3). Viết
  **một** hàm dùng chung, không rải phép chia ra từng chỗ.
- **Dấu hiệu để Escape hoạt động.** Mỗi bảng/overlay mới phải là `dialog[open]` hoặc
  mang lớp `.overlay.on`, nếu không phím Escape sẽ nhảy toàn màn hình (S7).
- **Chuỗi song ngữ.** Mọi chuỗi người dùng nhìn thấy phải có khoá trong `I18N` cho cả
  `vi` và `en`, hoặc dùng `t('…','…')`. Không ghi chữ thẳng vào HTML/JS (S12).
- **Không thêm media query mới.** Dùng biến từ `fit()` hoặc container query (S11).

## 6. Các đợt triển khai

### P0 — Chốt nền và đường kiểm thử

**Công việc:** đọc lại mã mới nhất, giải quyết khoá, sao lưu, lập danh sách hiệu ứng CSS/JS đang hoạt động. Kiểm tra cách đóng gói HTML/module vào EXE và phiên bản WebView2 thực tế. Chạy kiểm thử nền phù hợp; ghi riêng lỗi có sẵn.

**Đầu ra:** danh sách điểm can thiệp và kết quả nền bằng chữ. Chọn dữ liệu giả/cổng giả; không kết nối hay gửi lệnh tới máy rang thật để thử giao diện.

**[SOÁT 08/09] Ba việc chốt trước, làm ngay trong P0:**

1. **Quyết số phận `#topbar .livetemps`** (S10). Hoặc hồi sinh (đổi luật ~2053 thành
   có tiền tố `html:has(#pane-rang.on)`), hoặc bỏ hẳn markup 2722–2725. Chưa chốt
   việc này thì chưa bàn được ô trạng thái của P2, vì hai thứ tranh cùng một chỗ.
2. **Viết hàm quy đổi toạ độ theo hệ số scale** (S3) và sửa luôn hai canvas nhân
   thêm hệ số đó (S4). Đây là nền của P4, và S4 là lỗi có sẵn — ghi riêng, đừng trộn
   vào công lao của đợt.
3. **Lập bảng "năm chốt chặn touch — giữ cái nào, mở cái nào"** (S5, S6) rồi mới lên
   lịch P4. Mỗi dòng ghi: chặn ở đâu, ảnh hưởng gì trên WebView2, ảnh hưởng gì trên
   trình duyệt điện thoại, quyết định, lý do.

Ngoài ra P0 phải xác định luôn: bản web clone có nằm trong phạm vi đợt này không
(S1). Nếu có thì bổ sung bề rộng điện thoại vào ma trận thử; nếu không thì ghi rõ
cách tắt các hiệu ứng mới khi `window._OTL_WEBCLONE` bật.

**Nghiệm thu:** hiểu luồng dữ liệu và quyền điều khiển; có bản sao khôi phục đúng đợt; không bỏ sót thay đổi của tác nhân khác; ba việc chốt ở trên đã có câu trả lời bằng chữ.

### PD — [SOÁT 08/09] Khớp lại bản thiết kế đã duyệt — ✅ ĐÃ LÀM 08/09/2026

> **Kết quả thực tế.** PD-1, PD-2, PD-3 và PD-5 đã xong; PD-4 còn treo chờ chủ máy.
> Chi tiết ở nhật ký `docs/ui/UI-LOCK.md`. Tóm tắt:
>
> - **PD-1 xong.** Xả liệu và Kết thúc mẻ phải giữ đủ 1 giây. Thanh chạy bằng
>   `transform:scaleX`. Nhả sớm, kéo ngón ra khỏi nút, hay `pointercancel` đều huỷ và
>   không gửi gì. Mốc thời gian do `setTimeout` giữ, cố ý KHÔNG dùng `transitionend`
>   làm mốc phát lệnh vì khi tắt chuyển động sự kiện đó không bao giờ tới.
> - **PD-2 xong**, nhưng nhẹ hơn dự đoán: `appExit` vốn ĐÃ chặn khi đang rang và đã
>   có xác nhận bấm-hai-lần. Việc thật là đổi sang cùng cử chỉ giữ để cả ba lệnh hệ
>   trọng dùng một cách, và chặn ngay lúc bắt đầu giữ thay vì để giữ xong mới báo.
>   Nút Thoát ở **màn đăng nhập** giữ nguyên bấm-hai-lần: chưa vào mẻ nào.
> - **PD-3 xong.** Bỏ sạch BT/ET trên thanh đầu: markup, hai chỗ ghi trong JS, và 9
>   luật CSS. Phát sinh: hai biến `bt`/`et` trong `applyMachine` thành thừa, đã bỏ.
> - **PD-5 xong.** 18/18 bộ kiểm giao diện đạt, gồm bộ mới `test_ui_hold_confirm.py`.
>   Sáu bộ kiểm cũ phải sửa vì chúng ghi lại hợp đồng CŨ ("chạm là lệnh đi") —
>   sửa bộ kiểm, không nới hành vi.
> - **PD-4 xong** (chủ máy chốt chiều 08/09, làm theo phương án của ông chứ không
>   theo thiết kế). **Đính chính một lỗi đọc mã của bản soát:** app KHÔNG chạy bậc
>   ±1 như đã ghi — `data-d="1"` chỉ là *chiều*, độ lớn nằm ở `OUT_STEP=5`, nên bậc
>   thật đang là **±5 mỗi chạm**. Phương án chủ máy chốt:
>   - Chạm một cái = **±1** (siết lại từ ±5, để chỉnh tinh được).
>   - Đè giữ = tự lặp mỗi 200 ms, bậc **lớn dần theo thời gian giữ**: ±1 → sau 1,2 s
>     thành ±5 → sau 3 s thành ±10.
>   - **Đang giữ thì chỉ đẩy xuống máy MỖI GIÂY một lần**, cộng một lần chốt ngay khi
>     nhả tay. Đây là phần quan trọng nhất: trước đây mỗi nấc là một lệnh Modbus, giữ
>     3 giây là 12 lệnh chen nhau trên dây 38400 và biến tần nhận nguyên chuỗi
>     setpoint rác trên đường tới con số thợ thật sự muốn. Nay giữ 2,6 giây đi được
>     39 nấc nhưng chỉ tốn **3 lệnh**.
>   - Bộ kiểm `tools/test_ui_step_accel.py` giữ luật này, gồm cả ca kéo ngón ra khỏi
>     nút giữa chừng vẫn phải chốt, và ca kẹp trần 100 không gửi giá trị vượt dải.
>
> Một đính chính so với mục 3.2: chú thích trong mã tại cụm nút nguy hiểm ghi rằng
> app "hỏi lại bằng hộp thoại". Đọc kỹ `cmdDrop`, `cmdEscape`, `cmdLatch` và
> `machCmd` thì **không có hộp thoại nào cả**. Chú thích đó đã được sửa.

Đợt này chèn vào giữa P0 và P1, và là đợt **quan trọng nhất** của kế hoạch. Nó không
thêm hiệu ứng nào; nó trả app về đúng thứ chủ máy đã duyệt (mục 3.2).

**PD-1. Giữ 1 giây để xác nhận cho Xả liệu và Kết thúc mẻ.** Theo đúng thiết kế:
`pointerdown` bắt đầu giữ, `pointerup`/`pointerleave`/`pointercancel` huỷ, đủ 1000 ms
mới gửi lệnh. Thanh tiến trình chạy trong lòng nút, nền `#D93A32` opacity 0,22 quy
theo token hiện có. Bốn trạng thái nhãn theo bảng ở mục 3.2.

Ràng buộc bắt buộc: **lệnh chỉ đi khi đủ 1 giây**, không gửi sớm rồi huỷ sau. Thanh
tiến trình là `transform: scaleX()` chứ không animate `width`. Khi Giảm chuyển động
thì bỏ thanh chạy nhưng **giữ nguyên yêu cầu giữ 1 giây** và thay bằng đếm chữ — đây
là chốt an toàn, không phải trang trí, nên không được tắt cùng hiệu ứng. Bàn phím
phải có đường tương đương (`Enter` giữ, hoặc hộp xác nhận) vì giữ phím không phát
`pointerdown`.

**PD-2. Thoát ứng dụng.** Cùng cơ chế, cộng trạng thái chặn khi đang rang: nhãn
`Không thể tắt khi đang rang`, con trỏ `not-allowed`, không nhận giữ. Kiểm tra xem
app đã chặn chưa; chưa thì đây là lỗ hổng thật, ghi vào mục 12.

**PD-3. Xoá markup BT/ET chết trên thanh đầu** (S10 + mục 3.2). Xoá cả markup lẫn hai
luật `display:none` đang che nó, để không ai hiểu nhầm là còn dùng được.

**PD-4. Chốt bậc nhảy và nhịp lặp nút `±`.** Trình bày cho chủ máy: thiết kế ±10 mỗi
chạm, app ±1. Không tự đổi — đây là con số ảnh hưởng tới mẻ đang chạy. Nếu chủ máy
giữ ±1 thì đề nghị hạ nhịp lặp 250 ms xuống quanh 130 ms như thiết kế, để giữ tay
không mất 2,5 giây cho 10%.

**PD-5. Chạy lại `tools/test_ui_audit.py` và `test_ui_consistency.py`** rồi đối chiếu
với 5 lời phàn nàn ở mục 3.2. Xác nhận bằng bộ kiểm chứ không tin nhật ký các đợt cũ.

**Nghiệm thu:** hai lệnh hệ trọng không thể phát ra bằng một chạm nhầm; giữ 1 giây vẫn
bắt buộc khi đã Giảm chuyển động; không còn markup BT/ET chết; bậc nhảy `±` có câu trả
lời của chủ máy bằng chữ; năm lời phàn nàn ở mục 3.2 có kết quả đạt/chưa đạt kèm bằng
chứng từ bộ kiểm.

### P1 — Chuẩn hoá chuyển động và phản hồi

**Công việc:** tạo token thời lượng/cách chuyển phù hợp style hiện có; thay các giá trị rải rác có liên quan, tránh refactor toàn HTML. Giữ hai lựa chọn Mượt mà/Giảm chuyển động. Rà các pulse của kết nối, lửa, nạp, xả và cảnh báo để tránh chuyển động dư thừa; nhãn trạng thái luôn tồn tại.

Áp vòng chờ/dấu kiểm cho thao tác lưu và kết nối có tín hiệu hoàn tất rõ. Với tác vụ không có tiến độ thật, dùng nhãn chờ thay vì phần trăm giả; khi lỗi/hết thời gian, dừng chuyển động và hiện cách thử lại phù hợp.

**[SOÁT 08/09]** Việc "rà các pulse" ở trên có khối lượng đo được: **10 trong 26**
khai báo `animation` đang gắn `data-motion`, tám animation `infinite` nằm ngoài (S9).
Tuỳ chọn Giảm chuyển động trong app hiện KHÔNG tắt được lửa, nạp, kết nối và cảnh
báo — chỉ tuỳ chọn của hệ điều hành mới tắt. Đây là lỗ hổng có sẵn, không phải việc
phát sinh; ghi rõ như vậy trong báo cáo đợt.

Lưu ý ngược lại khi vá: hai luật `*{animation:none!important}` toàn cục (958, 1679)
làm vòng chờ đứng hình khi hệ điều hành bật giảm chuyển động. Vòng chờ mới của P1 vì
thế bắt buộc phải có nhãn chữ đi kèm, nếu không người dùng nhìn thấy một vòng tròn
bất động và không biết máy đang làm gì.

**Nghiệm thu:** giảm chuyển động có hiệu lực với CSS, pseudo-element và JS; tỷ lệ animation được gắn `data-motion` đạt 26/26 hoặc liệt kê rõ cái nào cố ý để ngoài và vì sao; vòng chờ vẫn đọc được khi tắt hết chuyển động; không phát sinh lệnh lặp; số đo và cảnh báo cập nhật không chờ hiệu ứng; màn Rang không bị transform.

### P2 — Ô trạng thái mẻ xuyên màn — ⏸ CHỜ CHỦ MÁY DUYỆT

> **[SOÁT 08/09]** Đợt này ra khỏi phạm vi mặc định. Bản thiết kế được duyệt không có
> ô trạng thái, và thanh đầu trong thiết kế cố ý chỉ còn logo, nav và nhãn kết nối
> (mục 3.2). Thêm ô này là thêm lại đúng thứ vừa được gỡ đi. Nội dung bên dưới giữ
> nguyên để dùng ngay nếu chủ máy đồng ý — khi đó đọc kèm ghi chú "thanh đầu không
> còn chỗ" ở cuối phần Công việc.

**Công việc:** bổ sung một ô trạng thái vào vùng thanh đầu có chỗ; khi màn hẹp dùng nhãn ngắn hoặc hàng riêng đã dành chỗ, không che nút. Gộp Dynamic Island và Live Activities, tránh hai widget trùng dữ liệu.

**[SOÁT 08/09] Thanh đầu KHÔNG còn chỗ trống — sửa lại cách làm.** Ba sự thật (S10):
BT/ET trong topbar đang bị `display:none` toàn app nên là mã chết; topbar khi ở màn
Rang đã phải thu nhỏ đồng hồ, giấu logo và giấu vạch ngăn để đủ chỗ; và
`@media(max-width:1700px)` đẩy topbar xuống hai hàng trên gần như mọi laptop.

Vì vậy ô trạng thái nên **thế vào chỗ `livetemps` đang bỏ trống** thay vì thêm phần
tử mới, và phải trả lời được: ô này hiện ở màn Rang nữa hay chỉ ở các màn khác (ở màn
Rang thì BT, đồng hồ và giai đoạn đã có sẵn cỡ lớn, nhắc lại là thừa). Phần tử mới
phải qua được hàm `PROBE` của `tools/test_ui_audit.py` (S12) và không được thêm media
query (S11).

Ví dụ nội dung thu gọn: `Đang rang · 08:42 · BT 186,5°C · Phát triển`. Khi bấm mở bảng chi tiết có tên hồ sơ, trạng thái dữ liệu và nút `Về màn Rang`. Bảng này chủ yếu để theo dõi, không nhân đôi điều khiển gas/xả.

| Trạng thái đầu vào | Hiển thị |
|---|---|
| Chưa có kết nối | Nhãn kết nối theo trạng thái thật; giá trị chưa biết là `—` |
| Đang làm nóng | Nhiệt hiện tại/mục tiêu khi có dữ liệu; không gọi tỷ lệ nhiệt là thời gian hoàn thành |
| Sẵn sàng | Nhãn sẵn sàng theo state machine hiện có |
| Đang rang | Đồng hồ, BT, giai đoạn; lấy cùng nguồn với màn Rang |
| Làm nguội/kết thúc | Chỉ hiển thị nếu trạng thái máy hoặc ứng dụng xác nhận; không suy đoán bằng animation |
| Dữ liệu trễ/mất kết nối | Nhãn rõ, áp quy tắc dữ liệu cũ hiện có; nếu chưa có ngưỡng, truy theo nhịp telemetry trước khi chọn |
| Có lỗi | Ưu tiên lỗi và lối tới thông tin lỗi; không thay thế banner lỗi chính |
| **[SOÁT 08/09]** Trợ lý AI đang giữ quyền lái máy | Nhãn rõ là người dùng không phải người đang điều khiển, kèm thời gian còn lại của lượt giữ quyền. Đây đúng là thứ cần thấy xuyên màn nhất mà bảng gốc bỏ sót |

**Nghiệm thu:** chuyển giữa các tab không mất hoặc nhân đôi widget; không tự điều hướng khi cập nhật; mở/đóng không làm xê dịch nút máy; không hiện thành công sai khi mất kết nối giữa tác vụ; ô trạng thái không nhắc lại số liệu đã hiện cỡ lớn ngay cạnh nó.

### P3 — Hồ sơ, Lịch sử, bảng phụ và cuộn

**Công việc:** dùng chuyển cảnh thẻ/dòng sang chi tiết khi hợp với luồng sẵn có. Khi đóng, trả về vị trí cuộn, bộ lọc và phần tử đã mở; nếu phần tử bị xoá/lọc mất thì trả focus về vùng danh sách. Dùng chuyển mờ dự phòng khi không xác định được nguồn.

Ưu tiên CSS/Web Animations và cấu trúc sẵn có, không thêm framework chỉ để tạo spring. Nếu dùng View Transitions, kiểm tra hỗ trợ và có đường dự phòng; không tạo hai bản DOM tương tác cùng lúc.

Rà `touch-action` theo vùng: danh sách cho phép cuộn phù hợp, đồ thị dành cử chỉ riêng, nút giữ vẫn giữ cơ chế hiện có. Không thay `#stage` một cách toàn cục mà chưa kiểm tra các điều khiển phụ thuộc. Không bắt wheel toàn trang để tạo quán tính giả.

**[SOÁT 08/09] Mở `touch-action` có tác dụng phụ theo chiều ngược lại.** Hiện
`#stage{touch-action:none}` khiến trình duyệt không bao giờ huỷ chuỗi con trỏ. Vừa
cho phép `pan-y` ở một vùng là trình duyệt bắt đầu bắn `pointercancel` khi ngón tay
trượt — mà nút `±` gas/gió/trống dùng đúng sự kiện đó để dừng chuỗi tự lặp 250 ms
(S8). Phải thử tay: đặt ngón lên nút `±` rồi kéo dọc, xem có nấc lệnh nào bị nuốt
hoặc bị lặp thêm không. Cùng lúc, tooltip `data-help` bật sau 700 ms giữ ngón sẽ chen
vào giữa thao tác cuộn chậm — kiểm luôn.

**Nghiệm thu:** nhấn mở/đóng liên tục không kẹt overlay; chọn hồ sơ khi đang rang giữ đúng bảo vệ hiện tại; có trạng thái tải/rỗng/lỗi; tên dài không tràn; cuộn không biến thành nhấn thẻ; bàn phím và Giảm chuyển động hoạt động đầy đủ.

### P4 — Zoom và kéo đồ thị — ⏸ CHỜ CHỦ MÁY DUYỆT

> **[SOÁT 08/09]** Ra khỏi phạm vi mặc định. Bản thiết kế vẽ đường cong bằng
> `polyline` tĩnh, không có khái niệm vùng xem tách khỏi dữ liệu. Zoom không mâu thuẫn
> thiết kế nhưng là phát minh ngoài nó, mà chi phí lại cao nhất trong cả kế hoạch (bốn
> đính chính ở dưới). Nếu chủ máy muốn, làm sau P3 và làm đúng thứ tự chi tiết mẻ →
> so sánh → trực tiếp.

**Thứ tự:** chi tiết mẻ → so sánh → đồ thị rang trực tiếp. Trình sửa hồ sơ `#peCurve` ngoài phạm vi mặc định vì có thể dùng kéo để sửa điểm.

**Công việc:** tách miền thời gian đang xem khỏi dữ liệu gốc; zoom trục thời gian trước, giữ cách chia trục nhiệt hiện có. Zoom quanh điểm chạm/con trỏ, giới hạn vùng xem trong dữ liệu hợp lệ; hai đường so sánh dùng cùng miền thời gian.

Thêm `Phóng to`, `Thu nhỏ`, `Về toàn mẻ`; hỗ trợ chuột và bàn phím. Quy định cử chỉ trong vùng đồ thị: hai ngón pinch, kéo để pan khi đã zoom; ngoài đồ thị cuộn vẫn bình thường. Rà cơ chế chặn Ctrl+wheel hiện tại, tránh phá phím tắt và zoom truy cập ngoài đồ thị.

**[SOÁT 08/09] Bốn đính chính cho đợt này:**

- **Phải quy đổi toạ độ.** "Zoom quanh điểm chạm" chỉ đúng nếu toạ độ con trỏ được
  chia cho hệ số scale của `#stage` (S3). Không có bước này thì tâm zoom lệch dần
  càng ra rìa càng lệch nhiều, và trên mỗi cỡ màn lệch một kiểu.
- **Tiêu chí canvas đang sai.** `devicePixelRatio` chưa đủ vì stage còn bị scale
  thêm (S4). Trên màn 4K hệ số có thể ≈ 1,5 nên nét vẽ bị kéo giãn dù `dpr` đã đúng.
  Sửa ở P0 rồi mới nghiệm thu ở đây.
- **Bốn chốt chặn khác cũng dính, không chỉ Ctrl+wheel** (S5): `gesturestart` bị
  chặn nên pinch chết trên iPad/iPhone của bản web; `dblclick` bị chặn nên mất cử
  chỉ chạm đúp về toàn mẻ; `contextmenu` bị chặn nên mất chuột phải.
- **Tiền đề "zoom truy cập" sai** (S6). `Ctrl` + `+ - 0` đã bị chặn từ trước: zoom
  trợ năng của trình duyệt hiện đã tắt hoàn toàn theo chủ ý kiosk. Không có gì để
  "tránh phá" — có một quyết định cũ cần xác nhận lại hoặc đảo. Chọn phím tắt cho
  `Phóng to`/`Thu nhỏ` phải tính đến việc bốn phím quen thuộc nhất đang bị nuốt.

Ở đồ thị trực tiếp, khi người dùng xem đoạn cũ: hiện `Đang xem đoạn trước` và nút `Theo dõi trực tiếp`. Tiếp tục nhận/lưu mẫu nhưng không tự giật vùng nhìn về cuối. Khi bật theo dõi lại, dùng dữ liệu mới nhất. Chế độ vùng xem không sửa profile, thời gian máy, thuật toán RoR hay bản ghi.

**Nghiệm thu:** dữ liệu rỗng, một mẫu, khoảng thời gian bằng không, dữ liệu dài và resize không sinh NaN/lỗi; zoom không chặn điều khiển khác; không sửa dữ liệu; canvas nét đúng tỉ lệ điểm ảnh; không tích luỹ listener qua nhiều lần mở.

### P5 — Kính nhẹ, hiệu năng và đóng gói — ❌ PHẦN KÍNH BỊ BỎ

> **[SOÁT 08/09]** Phần **kính mờ bị bỏ**: bản thiết kế được duyệt có **0** điểm
> `backdrop-filter`/`blur()` và dùng nền đặc `#15151A`, `#16161B`, `#101013` (mục 3.2).
> Làm kính là đi ngược nguồn thiết kế, chỉ làm nếu chủ máy đổi ý bằng lời.
>
> Hai phần còn lại của đợt **vẫn giữ và vẫn bắt buộc**: đo hiệu năng, và đóng gói EXE.
> Chúng không phụ thuộc vào kính. Đóng gói thì theo ghi chú bên dưới, áp cho từng đợt.

**Công việc:** dùng token nền/viền/bóng nhất quán cho thanh điều hướng và bảng nổi. Giữ nền kín tại BT/ET/RoR, đồ thị và thông báo quan trọng. Không chồng nhiều lớp blur; không animate giá trị blur hay khúc xạ toàn màn. Có fallback nền đặc khi không hỗ trợ hoặc người dùng giảm độ trong suốt qua tuỳ chọn hiện có; chỉ thêm tuỳ chọn nếu app chưa có cách tương đương.

Đo với chuyển động bật/tắt trên máy chạy app: FPS khi chuyển bảng, tác vụ JS dài và nhịp cập nhật telemetry. Mục tiêu khoảng 60 fps trên thiết bị phù hợp; đây là mục tiêu phải đo, không phải cam kết. So sánh cùng dữ liệu/kích thước cửa sổ; khi phát hiện giật, giảm blur/phạm vi chuyển cảnh trước.

**[SOÁT 08/09]** Hai chỗ cần cụ thể hơn. Thứ nhất, "đo FPS" phải nói rõ **bằng công
cụ nào**: Playwright chạy Chromium riêng nên không đo được WebView2 thật, chốt công
cụ trước khi đặt mục tiêu 60 fps, nếu không đo được thì ghi thẳng là chưa đo. Thứ
hai, đo phải làm trên **cả hai đích chạy** (S1) — điện thoại tầm trung là nơi nhiều
lớp `backdrop-filter` gãy trước nhất, không phải máy vận hành.

Về đóng gói: lệnh thường trực của chủ máy là **sửa xong app thì tự build EXE và tạo
lối tắt Start, không hỏi lại**. Việc này áp cho từng đợt P1–P5 chứ không dồn về cuối,
nếu không người dùng sẽ chạy bản EXE cũ suốt các đợt giữa. Bẫy đã biết: app đang chạy
sẽ khoá file EXE và gây `WinError 5` — đặt tên bản mới kèm ngày rồi báo người dùng,
đừng ép tắt app đang vận hành.

**Nghiệm thu:** không có suy giảm nhịp cập nhật do chuyển cảnh được quan sát trong kịch bản thử; ghi số đo thực tế và thiết bị/runtime; kiểm tra EXE chứa đúng HTML/module mới theo quy trình đóng gói dự án. Không ghi đè EXE đang chạy bằng cách ép tắt app vận hành.

## 7. Kế hoạch kiểm thử

Chỉ thêm kiểm thử hành vi có ý nghĩa. Không viết test chỉ để so chuỗi CSS hoặc trùng lặp triển khai. Tên file mới dưới đây là gợi ý, không phải file đã tồn tại.

| Hạng mục | Kiểm thử cần có |
|---|---|
| Nền chuyển động | Mở rộng `test_ui_layout_motion.py`: giảm chuyển động, màn Rang không transform, chuyển nhanh không kẹt |
| Cá nhân hoá | `test_ui_personalization.py`: cấu hình cũ còn đọc được, lựa chọn được lưu đúng |
| Ô theo dõi mẻ | Có thể thêm `test_ui_live_activity.py`: chuỗi trạng thái, thiếu trường, dữ liệu cũ, lỗi, chuyển tab |
| Thẻ/chi tiết | `test_ui_overview_history.py` và bài phù hợp: khôi phục cuộn/focus, lọc mất nguồn, mở/đóng liên tục |
| Zoom | Có thể thêm `test_ui_chart_navigation.py`: miền xem, dữ liệu không đổi, reset, tắt/bật theo dõi trực tiếp |
| Điều khiển | Chạy bài liên quan trong `test_ui_live.py`, `test_ui_compat_roast.py`, `test_ui_workflow.py`, `test_ui_autodrop.py` theo vùng sửa |
| Bố cục | Các bài dialog/toolbar/roast_columns phù hợp với phần thay đổi |
| **[SOÁT 08/09]** Tràn / đè | `tools/test_ui_audit.py` — hàm `PROBE` bắt `min-width:auto` thổi bung lưới. Bắt buộc chạy sau khi thêm bất kỳ phần tử nào vào topbar (S10, S12) |
| **[SOÁT 08/09]** Song ngữ | `tools/test_ui_consistency.py` — bắt chuỗi tiếng Anh sót và khoá `data-i18n` trỏ vào khoá rỗng. Dự án từng lọt 47 chuỗi |
| **[SOÁT 08/09] Giữ 1 giây (PD)** | Bài mới, ví dụ `test_ui_hold_confirm.py`. Bắt buộc có các ca: nhả tay trước 1 giây thì **không** lệnh nào được gửi; đủ 1 giây thì gửi đúng một lần; giữ rồi kéo ngón ra ngoài nút thì huỷ; bấm liên tiếp không gửi trùng; khi Giảm chuyển động thì vẫn phải giữ đủ 1 giây; nút Thoát bị chặn khi đang rang. Đây là bài quan trọng nhất của cả kế hoạch |

Các script Python hiện có có thể chạy trực tiếp, ví dụ `python tools/test_ui_layout_motion.py`. Kiểm tra phụ thuộc/môi trường dự án trước khi chạy; không coi test giả lập Chromium là đủ để xác nhận WebView2/cảm ứng thật.

Ma trận thủ công tối thiểu:

- 1366×768, 1280×800, 1920×1080; sáng/tối; tiếng Việt/Anh.
- Chuột, bàn phím; cảm ứng thật nếu có thiết bị, ghi chưa kiểm chứng nếu không có.
- Mượt mà, Giảm chuyển động trong app, giảm chuyển động từ hệ điều hành.
- Chưa kết nối, đang kết nối, đang rang, lỗi và mất kết nối giữa thao tác; dùng dữ liệu/cổng giả.
- Lịch sử rỗng, nhiều mẻ, tên dài, dữ liệu thiếu; trợ lý mở cùng lúc nếu có tích hợp.
- Chuyển tab nhanh, resize giữa chuyển cảnh, đóng bảng đang tải, thao tác tiếp ngay sau animation.

**[SOÁT 08/09] Ma trận trên thiếu ba trục:**

- **Bản web trên điện thoại thật** (S1): mở qua `http://` từ máy chạy app, thử ít
  nhất một Android và một iOS. Đây là nơi pinch, kính mờ và `gesturestart` gãy trước.
  Bề rộng cần thêm vào danh sách: khoảng 390 và 430 px.
- **Màn có hệ số scale lớn hơn 1** (S3, S4): màn 4K hoặc 2560×1440, để bắt lệch tâm
  zoom và canvas mờ. Ba cỡ đang liệt kê đều cho hệ số nhỏ hơn 1 nên không lộ lỗi.
- **Trợ lý AI đang giữ quyền lái máy**: ô trạng thái và các chuyển cảnh trong lúc
  người dùng không phải người điều khiển.

Ghi chú về công cụ: các bài kiểm nạp HTML qua `file://` nên luôn chạy ở chế độ không
có cầu pywebview và không có trợ lý (S2). Không suy ra từ kết quả xanh rằng bản EXE
hay bản web cũng đạt.

Không thay firmware trong kế hoạch này nên không yêu cầu build PlatformIO. Nếu phát sinh thay firmware ngoài dự kiến, tách phạm vi, tuân thủ AGENTS.md và chạy compile/size; không nạp phần cứng chỉ để thử hiệu ứng.

## 8. Cách chia thay đổi và điều kiện hoàn thành

Mỗi đợt P0–P5 có ghi chú ngắn: đã sửa gì, file nào, kiểm thử nào đạt/thất bại, giới hạn chưa kiểm chứng. Không đợi làm hết mới kiểm tra. Tách commit theo đợt nếu workflow yêu cầu commit và chỉ chọn file thuộc công việc.

Hoàn thành khi:

- **[SOÁT 08/09] PD đạt trọn vẹn** — không có PD thì không tính là hoàn thành, dù mọi đợt khác đã xong.
- Các nhóm còn trong phạm vi mặc định có hành vi đúng phạm vi hoặc ghi rõ trở ngại kỹ thuật với phương án thay thế đã thực hiện.
- Không thay semantics lệnh máy, giữ nút, quyền, mất kết nối và dữ liệu. **Ngoại lệ có chủ đích duy nhất: PD-1 và PD-2 làm hai lệnh hệ trọng khó phát ra hơn — đây là siết, không phải nới, và là yêu cầu của bản thiết kế.**
- Kiểm thử liên quan đạt; lỗi nền được phân biệt bằng bằng chứng, không bỏ qua âm thầm.
- Đã kiểm tra runtime thực tế nếu có thể; phần chưa có thiết bị ghi rõ.
- Có báo cáo bằng chữ, danh sách file thay đổi và cách tắt chuyển động khi cần.
- **[SOÁT 08/09] Có bảng đối chiếu lại với mục 3.2**: mỗi dòng lệch thiết kế–app ghi rõ đã khớp, hay chủ máy chọn giữ khác, hay còn treo.
- Trả khoá đúng quy ước; giữ bản thiết kế mirror nguyên vẹn.

**[SOÁT 08/09] Ưu tiên khi cần giảm phạm vi (thay bản cũ):** giữ **PD** bằng mọi giá,
rồi P1, rồi P3. P2, P4 và phần kính của P5 đã ra khỏi phạm vi mặc định nên không có gì
để cắt. Không bỏ kiểm thử điều khiển để dành thời gian cho hiệu ứng trang trí — và
trong đợt này, "hiệu ứng trang trí" nghĩa là mọi thứ ngoài PD.

## 9. Các mục chỉ triển khai khi được chọn thêm

- **Cover Flow:** chế độ duyệt hồ sơ bổ sung, không thay lưới; phải có nút trước/sau, không phụ thuộc vuốt và không auto-play.
- **Genie nhẹ cho trợ lý:** chỉ chuyển panel về nút mở; giữ nội dung chat, tác vụ đang chạy và focus. Không dùng mesh/WebGL chỉ để uốn cửa sổ.
- **Bounce bảng phụ:** giới hạn biên độ, không ảnh hưởng scroll danh sách và không chuyển động khi đã giảm motion.
- **Orb trợ lý:** trạng thái nghỉ đứng yên; chỉ chạy khi có yêu cầu đang xử lý, kết thúc theo phản hồi thực tế; có lỗi/hết thời gian rõ.

Parallax, activity rings và confetti tiếp tục hoãn. Không bật chúng chỉ để đủ danh sách 15 hiệu ứng.

## 10. Nguồn tham khảo

- **[SOÁT 08/09] Nguồn thiết kế, có thẩm quyền cao nhất trong tài liệu này:** Claude Design, project `Menu cài đặt nhanh - Lỗi thiết kế` (`3c3a6a49-faff-4902-a214-f071ccd6006f`). Mirror trên đĩa `docs/ui/design-web/` — file `Rang - Sua lai.dc.html` (đọc cả khối `x-dc` cuối file) và thư mục `uploads/` (14 ảnh chủ máy chỉ lỗi). Chỉ Claude Code kéo được bản mới bằng công cụ `DesignSync`; không sửa mirror.
- Open Design cục bộ: `F:/Project/open-design/craft/animation-discipline.md`, `state-coverage.md`, `accessibility-baseline.md`.
- Apple, cách sử dụng kính và phân lớp: https://developer.apple.com/videos/play/wwdc2025/219/
- Apple, vật liệu giao diện: https://developer.apple.com/design/human-interface-guidelines/materials
- MDN, quyền xử lý cử chỉ: https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/touch-action
- MDN, giảm chuyển động: https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/@media/prefers-reduced-motion

## 11. Lệnh bàn giao gợi ý cho Claude

> Đọc `docs/ui/2026-09-08-ke-hoach-nang-cap-chuyen-dong-roast-lab.md`, **mục 3.2 rồi 3.1 trước tiên**, rồi triển khai theo thứ tự **P0 → PD → P1 → P3**. PD là đợt bắt buộc: app đang cho phép một chạm là xả liệu, trong khi bản thiết kế đã duyệt yêu cầu giữ 1 giây — sửa việc đó trước mọi hiệu ứng. **Không** làm P2, P4 và phần kính của P5: cả ba đã ra khỏi phạm vi mặc định vì không có trong bản thiết kế, chờ chủ máy duyệt bằng lời. Kiểm tra khoá và thay đổi hiện tại trước khi sửa; dùng Open Design, đọc nguồn Claude Design cho hết kể cả khối `x-dc` và thư mục `uploads/`, không sửa mirror. Trả lời xong ba việc chốt của P0 rồi mới viết mã. Hoàn thiện từng đợt kèm kiểm thử và build EXE, bảo toàn logic điều khiển máy. Báo cáo bằng chữ, không tạo ảnh/video bàn giao. Ghi rõ phần chưa kiểm chứng trên WebView2, trên bản web điện thoại hoặc trên cảm ứng thật.

## 12. [SOÁT 08/09] Lỗi có sẵn phát hiện khi soát

Ba lỗi dưới đây tồn tại từ trước kế hoạch này. Sửa được trong lúc làm thì tốt, nhưng
phải ghi riêng trong báo cáo — không tính là thành quả của đợt nâng cấp chuyển động,
và cũng không được im lặng bỏ qua.

1. **BT/ET trên thanh đầu là mã chết.** Luật `#topbar .livetemps{display:none}` thiếu
   tiền tố phạm vi nên ẩn ở mọi màn, trong khi markup vẫn còn (S10). Người dùng mất
   chỗ xem nhiệt độ khi đang ở màn Hồ sơ, Lịch sử hay Kho.
2. **Canvas không tính hệ số scale của stage** nên mờ trên màn có hệ số lớn hơn 1 (S4).
3. **Tuỳ chọn "Giảm chuyển động" trong app phủ chưa tới nửa số animation** — người
   chọn nó vẫn thấy lửa, nạp, kết nối và cảnh báo nhấp nháy (S9).
4. **[Vòng hai] Xả liệu và Kết thúc mẻ phát lệnh bằng MỘT chạm**, trong khi bản thiết
   kế đã duyệt yêu cầu giữ 1 giây có thanh tiến trình (mục 3.2). Đây là lỗi nặng nhất
   tìm được trong cả hai vòng soát: hậu quả là vật lý, không phải thẩm mỹ. Đã thành
   đợt PD.
5. **[Vòng hai] Markup BT/ET trên thanh đầu là mã chết** — đúng theo thiết kế thì
   phải xoá, chứ không phải bật lại (S10, mục 3.2).
