# Rà soát HIỂN THỊ · GIAO DIỆN · CHUYỂN ĐỘNG · ĐỒNG BỘ TAB — 08/09/2026

Tiếp nối `2026-09-08-roast-workflow-audit.md` của Codex. Bản đó đi theo **luồng
nghiệp vụ** (14 lỗi RF-01…RF-14: chuyển trạng thái, xác nhận lệnh, vòng đời dữ
liệu). Bản này đi mảng còn lại mà chưa ai đo: **cách app hiện lên mắt và tay thợ**
— hiển thị, tương phản, chuyển động, và tính đồng bộ giữa các tab.

Nguồn thiết kế: bản mirror Claude Design `docs/ui/design-web/Rang - Sua lai.dc.html`
(project `Menu cài đặt nhanh - Lỗi thiết kế`). Đã đối chiếu danh sách file trên
Claude Design — không có bản mới hơn bản kéo về 07/09.

## Cách đo

Viết bộ kiểm mới `tools/test_ui_motion_sync.py`, đo bằng máy trên Chromium, cộng
**chụp hình 12 màn** (6 tab × sáng/tối) để nhìn những thứ máy không bắt được.

Bộ kiểm dựng **7 kịch bản** và in ra kịch bản nào thật sự chạy được — một phép
kiểm âm thầm bỏ qua thì nguy hiểm hơn là không có phép kiểm nào.

**Bốn lần bộ đo tự nó sai, đã bắt và sửa trước khi báo cáo.** Ghi lại vì cùng
loại bẫy sẽ quay lại với người sau:

| Lỗi của bộ đo | Hậu quả nếu tin luôn |
|---|---|
| Ghép nền: gặp lớp mờ đầu tiên đã chồng lên trắng | **22 lỗi tương phản MA** trên nền tối |
| Chromium mới gắn `cssRules` rỗng cho mọi luật CSS | Nhảy qua **cả 1624 luật**, báo "không thấy gì" |
| `el.focus()` bằng script không bật `:focus-visible` | Báo oan 14 nút "không có viền chọn" |
| Không cài cầu `pywebview` giả | Báo oan "mất kết nối vẫn hiện số cũ" — app xử lý ĐÚNG |

Bài học chung: **bộ đo báo lỗi hàng loạt thì nghi bộ đo trước, đừng nghi app.**

## Đã sửa (có đo lại xác nhận)

### D-01 · P1 — Trục thời gian đồ thị in đè thành một số vô nghĩa

- **Nguồn:** `OTL Roast Lab.html` · `drawChart()`, đoạn vẽ vạch thời gian.
- **Hiện tượng:** góc trái dưới đồ thị hiện `−0:3000:00`. Nhãn mốc nạp `00:00` và
  nhãn mép trái `−0:30` vẽ chồng lên nhau vì `−0:30` được vẽ **vô điều kiện**.
  Xảy ra ở **cả nền sáng lẫn nền tối**, và ở **mọi mẻ chưa nạp hạt** — tức là
  đúng lúc thợ đứng chờ nhìn màn nhiều nhất.
- **Vì sao lọt:** không bộ kiểm nào đọc chữ vẽ trong canvas; nhìn ảnh nhỏ thì hai
  nhãn dính nhau trông như một nhãn dài.
- **Đã sửa:** đo bề rộng hai chữ rồi mới vẽ; hết chỗ thì bỏ nhãn `−0:30`, vạch mốc
  nạp vẫn còn nguyên.

### D-02 · P2 — Ba con số thợ nhìn nhiều nhất lấy màu ĐƯỜNG VẼ làm màu chữ

- **Nguồn:** khối áp bản thiết kế, `--oc` dùng chung cho thanh mức và chữ.
- **Đo được trên nền sáng:** gas `42` **2,66:1** · gió `61` **2,72:1** · trống `55`
  **1,91:1**. Chữ to cần tối thiểu 3:1. Số tốc độ trống gần như chìm vào thẻ trắng.
- Đây đúng là loại lỗi đã có quy ước từ trước: *màu đường vẽ đừng dùng làm màu chữ*.
  App đã có sẵn bộ mực `--bt-ink`/`--amber-ink`/`--ok-ink` chính vì việc này.
- **Đã sửa:** tách `--oci` (mực của số) khỏi `--oc` (màu thanh). Nền tối giữ nguyên
  màu thiết kế; nền sáng hạ độ sáng vừa đủ qua ngưỡng, **giữ nguyên tông**:
  `#ea7005` (3,10) · `#219cd6` (3,10) · `#38a75c` (3,07). Thanh mức và chấm màu
  không đổi một pixel.

### D-03 · P2 — Số TĂNG NHIỆT (RoR) cũng dính đúng lỗi đó

- Màu `#6fcf8e` (màu đường vẽ) làm màu chữ 40px → **1,91:1** trên nền sáng.
- RoR là số thợ nhìn nhiều thứ hai sau BT.
- **Đã sửa:** nền sáng dùng `#2f8f4d`; nền tối giữ nguyên.

### D-04 · P3 — Nhãn "Cần xác nhận" và chỉ báo lửa dưới ngưỡng đọc

- `Cần xác nhận` 4,32 (sáng) / 4,39 (tối) — chữ 15px cần 4,5.
  Một màu gạch duy nhất không kham nổi cả hai nền → tách theo nền.
- `Không lửa` **4,16** trên nền tối: `.flamebadge` lấy `--danger`/`--ok` (màu ĐÈN)
  làm màu chữ. **Đã sửa:** chữ dùng `--red-ink`/`--ok-ink`, viền và nền giữ màu gốc.

### D-05 · P3 — Chỉ báo trạng thái làm nóng MẤT CHẤM MÀU, chỉ báo màu thành mã chết

- **Nguồn:** `uxPreheat()` ghi `#phStatus` bằng `textContent`, xoá luôn
  `<span class="d">`; trong khi `setPhStatus()` thì giữ.
- **Đo được:** ngay **nhịp cập nhật đầu tiên** (1 giây sau khi mở app có nối máy)
  là chấm biến mất và không bao giờ quay lại. Kéo theo các luật
  `#preheatPanel.running #phStatus .d` (chấm vàng nhấp nháy lúc đang làm nóng) và
  `.done .d` (chấm xanh lúc xong) **không còn chỗ bám — thành mã chết**.
- Không lỗi, không cảnh báo, chỉ lặng lẽ mất chỉ báo. Trên trình duyệt thuần thì
  không thấy vì không có cầu nên `uxPreheat()` không chạy — chỉ bản chạy thật dính.
- **Đã sửa:** mọi chỗ ghi trạng thái đi qua `phStatusSet()`, giữ nguyên nút chấm.
- **Đã chứng minh phép kiểm không vô dụng:** gỡ bản vá ra là H4 hỏng ngay.

### D-06 · P3 — Ba nút bị khoá mà không nói vì sao

`So sánh hồ sơ`, `← Trước`, `Sau →` xám câm. Thợ bấm hoài tưởng app treo.
**Đã sửa:** mỗi nút nói rõ lý do khi bị khoá (chọn đủ 2 hồ sơ / đang ở trang đầu /
không còn mẻ phía sau).

## Ghi nhận — CỐ Ý KHÔNG SỬA

### N-01 · Thanh mức chạy bằng `width` (3 chỗ)

`.outrow .obar i`, `.phbarfill`, `#tabnav::before` đặt `transition` trên `width`,
tức mỗi khung hình trình duyệt phải dựng lại bố cục thay vì chỉ ghép hình.

**Nhưng đo thật thì không có hại:** chạy 6 gói dữ liệu như máy thật trong 3 giây
rang, `PerformanceObserver` bắt được **0 tác vụ khoá luồng >50 ms**.

Đổi sang `transform:scaleX` sẽ **bóp méo bo góc** — nhất là `.phbarfill` cao 26px
bo `--r-md`. Đổi một thứ đã đo là không hại, để lấy về một thứ chưa đo được, mà
phải trả bằng rủi ro méo giao diện chủ máy vừa duyệt — không đáng. Ghi lại đây để
nếu sau này chạy trên máy tính công nghiệp yếu mà thấy giật thì biết chỗ mà vào.

### N-02 · Hoạt ảnh vô hạn hoạt hoá `box-shadow` (7 nút)

`chargePulse`, `dropPulse`, `igBreath` làm nút thở/nhấp nháy bằng `box-shadow` —
tô lại mỗi khung hình. Cùng lý do N-01: **đo được 0 tác vụ dài**. Con số "8 hoạt
ảnh cùng lúc" trong bộ kiểm là do **tự ép trạng thái xấu nhất**; chạy thật thường
chỉ 2–3 cái.

### N-03 · Đổi sang tab Hồ sơ mất ~61–68 ms

Sát ngưỡng thấy khựng (60 ms), đo lệch giữa các lần chạy. Chỉ xảy ra ở tab Hồ sơ
vì nó vẽ lại toàn bộ lưới thẻ. Chưa đủ nặng để đụng vào.

## Đã kiểm và ĐẠT — không phải lỗi

| Kịch bản | Kết quả đo |
|---|---|
| Đứng ở Tổng quan, máy đổi nhiệt 120→205°C | Khối "Chuẩn bị mẻ rang" **tự đổi chữ** — `ovPrepRender()` chạy trong `uxTick` mỗi giây, không chờ vào lại tab |
| Cùng một con số ở nhiều nơi | gas máy = 37 → `ovBurner` = 37, khớp |
| Đổi tên hồ sơ ở tab Hồ sơ rồi sang Rang | Màn Rang hiện **tên mới** ngay |
| Mất kết nối | Mọi ô số về `—`, không tab nào giữ số ma |
| Cuộn giữa bảng Lịch sử, đi tab khác rồi quay lại | Không mất chỗ đang đọc |
| Đi bằng bàn phím | **0/14** nút thiếu viền chọn |
| Bật "Giảm chuyển động" | Tắt sạch, không sót hoạt ảnh nào |
| Chữ NaN / undefined / \[object Object\] | Không có ở tab nào, nền nào |
| Chữ bị cắt không có dấu … | Không có |

Ba mục cuối cần nói rõ: **đổi hồ sơ giữa mẻ bị từ chối** và **mất kết nối vẫn
hiện số trên trình duyệt thuần** ban đầu bị bộ đo báo là lỗi. Truy ra thì cả hai
là hành vi **đúng** của app (chốt an toàn, và nhánh mô phỏng dành cho trình duyệt
không có cầu). Bộ kiểm đã sửa lại cho khớp bối cảnh thật.

## Chưa kết luận được

- **Tab Kho & Kinh doanh gần như trống**, chỉ một dòng xám "Chỉ xem trong app"
  giữa vùng trắng lớn. Trên bản EXE có đủ cầu dữ liệu thì có thể đã đầy. **Cần mở
  EXE thật xem** rồi mới kết luận là thiếu trạng thái rỗng hay không.
- **`Nhiệt nạp —` rỗng ở mọi hồ sơ mẫu**: 4 hồ sơ mặc định không có trường nhiệt
  nạp, nên cột này luôn trống. Là thiếu dữ liệu mẫu, không phải lỗi hiển thị —
  nhưng người mới mở app lần đầu sẽ thấy một cột chẳng bao giờ có số.

## Trùng với bản của Codex

**RF-07** (Tổng quan vừa cảnh báo chưa sẵn sàng vừa báo "Sẵn sàng nạp") — đã **xác
nhận độc lập bằng mã nguồn**: trong `ovPrepRender()`, `hot = bt>=chargeT-1` không
có cận trên, còn dòng hướng dẫn trong `uxTick()` thì có nhánh `bt>chargeT+3`. Hai
chỗ dùng hai phép kiểm khác nhau cho cùng một câu hỏi.

**Không sửa ở đợt này** — RF-07 đã có người nhận trong kế hoạch bàn giao của Codex
(mục 3). Hai bên cùng sửa một chỗ theo hai cách là hỏng.

## Bộ kiểm mới

`tools/test_ui_motion_sync.py` — chạy `--report` để xem bảng, không cờ để bắt lỗi.

| Mã | Đo gì |
|---|---|
| M1–M3 | transition/hoạt ảnh đặt trên thuộc tính dựng lại bố cục hoặc tô lại nặng |
| M4 | bật "Giảm chuyển động" có tắt sạch không |
| M5 | thời gian khoá luồng khi đổi tab |
| M6 | tác vụ dài >50 ms trong lúc đang rang |
| H1–H3 | chữ hỏng · chữ bị cắt · tương phản WCAG ở 6 tab × 2 nền |
| H4 | chỉ báo trạng thái còn giữ chấm màu không |
| S1–S5 | đồng bộ giữa các tab: tự cập nhật · khớp số · theo bản mới · sạch khi mất kết nối · giữ chỗ cuộn |
| X1–X3 | nút khoá có nói lý do · viền chọn bàn phím · trạng thái rỗng |

## Hồi quy

**17/17 bộ kiểm giao diện hiện có ĐẠT** sau khi sửa: `test_ui_consistency`,
`match_reference`, `roast_columns`, `dialog_layout`, `workflow`, `hold_confirm`,
`step_accel`, `touch_hold`, `overview_history`, `live`, `audit`, `compat_roast`,
`autodrop`, `toolbar`, `personalization`, `layout_motion`, `motion_sync` (mới).

## Giới hạn

Đo trên **Chromium 149 headless với cầu máy giả**. Máy chủ máy chạy **WebView2
152** — cùng nhân, bản máy mới hơn. **CHƯA build EXE, CHƯA chạy với máy rang
thật.** Các số tương phản là tính toán trên màu tô, chưa phải đo bằng máy đo trên
màn hình cảm ứng ngoài xưởng — chỗ có nắng chói thì ngưỡng thật còn khắt khe hơn.
Không đụng firmware nên không build firmware.


---

# Đợt 2 — HIỆU ỨNG LÚC RANG · MÀU · CHỮ · FONT · POPUP

Chủ máy giao tiếp: soi hiệu ứng trong lúc rang, rồi soi toàn bộ màu sắc, màu chữ,
font, popup — đặc biệt trong quá trình rang. Hai bộ kiểm mới:
`tools/test_ui_roast_effects.py` và `tools/test_ui_colors_fonts.py`.

## Vì sao đợt 1 không thấy những lỗi này

Đợt 1 quét 6 tab ở trạng thái **đứng yên**. Nghĩa là **13 hộp thoại đều đang
đóng** nên không phần tử nào bên trong được đo, màn Rang **chưa vào mẻ** nên các
trạng thái nóng chưa hiện, và **không mẻ nào chạy** nên không hiệu ứng nào nổ.
Ba vùng lớn nằm ngoài tầm với.

## Đã sửa

### R-01 · P1 — Thợ KHÔNG BAO GIỜ nghe được "Crack đầu"

- **Nguồn:** `mileWatch()` gọi `say()` riêng cho từng mốc; `say()` lại gọi
  `speechSynthesis.cancel()` ngay trước khi nói, theo chủ ý "tin mới đè tin cũ".
- **Vì sao xảy ra ở MỌI mẻ, không phải ca hiếm:**
  `MILE_STEP={TP:7, DE:8, FCs:9, DEV:9, DROP:10}` — **FCs và DEV cùng progStep 9**.
  Nên hai mốc luôn được chốt trong CÙNG một `machSample`, `mileWatch` đọc thấy cả
  hai, nói "Crack đầu" rồi lập tức nói "Phát triển" — câu đầu bị cắt trong cùng
  một mili-giây, chưa kịp phát ra tiếng nào.
- **Đo được:** sổ ghi giọng nói cho thấy `noi("Crack đầu")` → `huy` cách 0 ms.
- **Nặng ở chỗ:** chính mã nguồn ghi FCs là *"MỐC QUAN TRỌNG NHẤT"*, và cả tính
  năng này sinh ra để **thợ không phải nhìn màn** (mắt ở trống). Hai bộ tiếng còn
  chồng lên nhau, mất luôn chất riêng vốn là cách tai phân biệt mốc trong xưởng ồn.
- **Đã sửa:** gom các mốc rơi cùng nhịp thành **một câu** ("Crack đầu, Phát triển")
  và chỉ phát bộ tiếng của mốc **nặng nhất** (`MILE_RANK`: FCs › DROP › TP › DE › DEV).
- **Đã chứng minh bộ kiểm không vô dụng:** gỡ bản vá ra là E2 hỏng ngay.

### R-02 · P2 — Nút và ô nhập vẽ chữ Việt bằng **Arial**

- **Đo được:** `#btnIgnite` ra `Arial`, trong khi `.tbtn` ngay sát bên ra
  `IBM Plex Sans`. Tổng **24 phần tử** lạc font trên 6 tab × 2 nền.
- **Nguyên nhân:** `button`/`input`/`select`/`textarea` **không kế thừa** font
  trang — trình duyệt tự gán font riêng. Chỗ nào quên đặt `font-family` là lệch.
- Đây là **bẫy đã dính từ 30/07/2026** và lại tái phát ở các nút thêm sau.
- **Đã sửa một luật, bịt vĩnh viễn:** `button,input,select,textarea,optgroup
  {font-family:inherit}`. Độ ưu tiên chỉ 0-0-1 nên mọi luật theo lớp đang có vẫn
  thắng — chỗ nào cố ý chọn font khác thì giữ nguyên. **24 → 0.**

### R-03 · P2 — Chữ biến mất ĐÚNG LÚC đầu đốt đang cháy

- Nút "Đánh lửa" khi có lửa ép nền **nâu đậm `#281b08` ở cả hai nền** (chủ ý thiết
  kế), nhưng chữ phụ bên trong vẫn lấy `--dim`; `--dim` của nền **sáng** là xám đậm.
- **Đo được:** `đang cháy` và `% giai đoạn` chỉ **1,85:1** — gần như vô hình, đúng
  vào lúc lửa đang cháy. Nền tối không dính vì `--dim` ở đó đã sáng.
- **Đã sửa:** ép mực ấm `#ac7f53` (4,75:1) cho chữ phụ trên các mảng nền nâu đó.

### R-04 · P2 — Mực màu chủ đạo chỉ được hiệu chuẩn cho MỘT mặt nền

- `personalContrast()` dò `--accent-txt` cho tới khi đạt 4,6:1 — nhưng **chỉ đối
  chiếu với `--card`**, mặt nền SÁNG NHẤT. Chữ accent còn nằm trên `--panel`,
  `--inset`, `--bg`; trên mặt lõm tối hơn thì tụt dưới ngưỡng.
- **Đo được** nhãn mức rang: azure **4,16** · amber **4,18** (cần 4,5), dù
  `--card` vẫn "đạt".
- **Đã sửa:** lấy mặt nền **tệ nhất** trong bốn mặt làm chuẩn. Đo lại **cả 7 màu
  chủ đạo × 2 nền**: thấp nhất 4,65 (azure 4,16→**5,10**, amber 4,18→**5,16**).
- Cũng đổi `#matchRoast` từ `--accent` sang `--accent-txt` — token tự trộn, nên
  đúng cho cả 7 màu lẫn màu tuỳ chọn, không ghim cứng một mã.

### R-05 · P3 — Thông báo che mất nút điều khiển lúc đang rang

- **Đo được:** `#toast` đè lên **hai nút `±`** của gió/trống, 49×29 px, trong 2,2 s.
- Chạm vẫn trúng nút (`pointer-events:none`), nên đây là lỗi **che mắt** chứ không
  phải bấm nhầm — thợ đang vặn gas thì thấy nút biến mất.
- **Đã sửa:** trên màn Rang, đẩy thông báo lên đè mép dưới đồ thị. Mất một dải đồ
  thị 2 giây vô hại hơn nhiều. Đo lại: che **0** nút.

## Hiệu ứng lúc rang — đã kiểm và ĐẠT

Chạy trọn một mẻ 620 giây qua cầu máy giả, thay 4 hàm phát tiếng và
`speechSynthesis` bằng bản ghi sổ:

| | Kết quả |
|---|---|
| 5 mốc kêu đủ, đúng thứ tự TP→DE→FCs→DEV→DROP | ĐẠT |
| Mỗi mốc đúng một lần, không lặp | ĐẠT |
| Đếm ngược tới lúc xả | nghe đủ 60 / 30 / 10 giây |
| Nhịp tim theo RoR | chạy khi bật, **tắt hẳn** khi hết mẻ, không để timer mồ côi |
| Hết mẻ rồi | 0 tiếng, 0 lời nổ thêm |
| Tắt tiếng rồi chạy lại cả mẻ | 0 tiếng, 0 lời — im hoàn toàn |
| Chip mốc todo→now→done | cả 5 về `done`, không chip nào kẹt |
| Dải giai đoạn | không có 2 giai đoạn cùng sáng |
| Lỗi JavaScript suốt mẻ | không |

## Màu · chữ · font — phạm vi đã quét

- **6 tab × 2 nền × {chờ, đang rang}**
- **7 màu chủ đạo × 2 nền** trên màn Rang
- **13 hộp thoại × 2 nền** (profedit, napedit, scalebox, roastmgr, batchDetail,
  batchCompare, portpick, askbox, keyboard, numpad, picker, aboutbox, khoForm)

Kết quả cuối: **0 lỗi tương phản · 0 phần tử lạc font · 0 chữ quá nhỏ · 0 lỗi JS.**

## Ba lần nữa BỘ ĐO tự sai — đã bắt kịp

Cộng dồn với 4 lần ở đợt 1 là **bảy**. Ghi lại vì cùng loại bẫy sẽ quay lại:

| Lỗi của bộ đo | Nếu tin luôn |
|---|---|
| Quét cả trang khi mở hộp thoại | 221 mục, phần lớn là màn nền phía sau, lặp 13 lần |
| Ghim màu dự phòng **trắng** khi không gặp lớp nền đục | Nền tối báo 1,18:1 cho chữ trắng |
| Đo cả nội dung trong `<details>` **đang đóng** | Trình duyệt trả **màu cũ** → chữ nền tối nằm trên nền trắng |

Thêm một mục nữa: đo tiếng theo **từng nốt** thì vô nghĩa khi bộ kiểm tua nhanh cả
mẻ (mọi nốt rơi cùng một mili-giây) — phải đo ở **tầng công thức tiếng**.

## Hồi quy

**20/20 bộ kiểm giao diện ĐẠT**, gồm 2 bộ mới của đợt này.

`test_ui_motion_sync` đã tách **ghi nhận** (M1/M2/M3/M5 — đã cân nhắc, cố ý không
đổi) ra khỏi **lỗi**: vẫn in ra để không ai quên, nhưng không bắt bộ kiểm đỏ. Một
bộ kiểm lúc nào cũng đỏ thì chẳng ai còn đọc nó nữa.
