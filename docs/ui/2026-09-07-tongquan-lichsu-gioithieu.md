# Dựng nốt bản thiết kế: Tổng quan · Lịch sử · Giới thiệu

Ngày 07/09/2026. Nguồn: bản thiết kế Claude Design "Rang - Sửa lại", mirror ở
`docs/ui/design-web/`. Đặc tả: [2026-09-07-design-spec.md](2026-09-07-design-spec.md).

Sao lưu trước khi sửa: `docs/ui/backup/OTL Roast Lab.pre-overview-history-0907-1852.html`.
Không thay firmware, không gửi lệnh tới máy rang thật.

---

## 1. Màn Tổng quan

Bốn thẻ điều hướng cũ (Bắt đầu rang / Hồ sơ / Lịch sử / Cài đặt) **bỏ hẳn**,
thay bằng khối **"Chuẩn bị mẻ rang"** ba bước như bản thiết kế:

| Bước | Trạng thái lấy từ đâu |
|---|---|
| 1 · Làm nóng máy | `dsLive()` + `DS.snap.bt` so với `R.chargeT` của hồ sơ |
| 2 · Chọn hồ sơ | `R.phase === 'NOSEL'` → "Chưa chọn", ngược lại là tên hồ sơ |
| 3 · Nạp hạt | đủ nhiệt thì "Sẵn sàng nạp", đang rang thì "Đang rang" |

Chỉ **một** bước sáng tại một thời điểm — bước chưa xong đầu tiên. Sáng nhiều chỗ
thì mất tác dụng dẫn đường.

Lời dẫn dưới tiêu đề và nút "Mở điều khiển rang" **dùng lại nguyên** máy trạng
thái sẵn có trong `uxTick()` (biến `message` / `action`), trước đây ghi vào thẻ
`.ovcard.primary`. Không viết logic thứ hai chạy song song.

Mất kết nối thì bước 1 ghi **"Chưa có dữ liệu máy"** — không suy diễn dữ liệu
thiếu thành máy nguội hay đã tắt (đúng mục 1 của bản rà soát Open Design).

Thêm:
- **Ngày đầy đủ tiếng Việt** ở góc phải lời chào ("Thứ Hai, 07/09/2026").
- **Ba lối đi nhanh** ở cuối cột phải: Hồ sơ rang · Lịch sử mẻ · Kho & Kinh doanh.
- **"Mẻ gần nhất"** từ một dòng tóm tắt nâng thành **bảng ba mẻ** (mã · hồ sơ ·
  thời gian · nhiệt xả · phát triển · ngày), bấm dòng nào mở mẻ đó, kèm lối
  "Xem lịch sử →". Hai nút *Xem mẻ mới nhất* / *Rang lại* giữ nguyên.
- Thẻ hồ sơ hay dùng đủ ba dòng: tên · mức rang · dòng số `nạp … · xả … · thời gian`.
  Ô nào hồ sơ chưa đặt thì **bỏ khỏi dòng**, không in "—" cho đủ chỗ.
- Đổi tên khối "Hồ sơ trong tầm tay" → **"Hồ sơ hay dùng"** theo bản thiết kế.

## 2. Màn Lịch sử

Bảng vào **thẻ bo góc**: hàng tiêu đề có nền riêng và **dính đỉnh** khi cuộn,
phân trang chuyển **vào trong thẻ, ở đáy** (trước đây nằm phía trên bảng).
Hàng bộ lọc vẫn ở ngay dưới tiêu đề trang.

Nhãn hai ô ngày ghi thêm định dạng: **"Từ ngày (dd/mm/yyyy)"**.

## 3. Hộp Giới thiệu (mới)

Mở từ menu tài khoản → **Giới thiệu**. Có logo O Tesla, dòng ghi rõ phần mềm
thuộc sở hữu của công ty, và bốn mục:

1. **Nhà sản xuất & liên hệ** — tên công ty, văn phòng, nhà máy, điện thoại,
   WhatsApp, email, mã số thuế.
2. **Tác giả** — người viết và chức danh.
3. **Nền công nghệ** — giao diện HTML/CSS/JS thuần không framework, đồ thị tự vẽ
   bằng Canvas, vỏ Python + pywebview đóng gói PyInstaller, kho SQLite chế độ WAL,
   nối máy bằng Modbus RTU tự viết, firmware STM32F103RC PlatformIO + Arduino.
4. **Ứng dụng trí tuệ nhân tạo** — nêu đích danh Claude (Anthropic) qua Claude Code
   và Codex (OpenAI), kèm câu nói rõ phần thiết kế, quyết định kỹ thuật và kiểm
   chứng trên máy thật là do tác giả làm.

Thông tin liên hệ lấy đúng bản chủ máy xác nhận 30/08/2026 (`0936 198 938`,
`otlpro.com@gmail.com`). Bộ kiểm chặn sẵn hai lỗi từng gặp: số `0938` và email cũ
`otesla.vn@gmail.com`.

**Sửa tên tác giả ở đúng một chỗ:** hằng `APP_AUTHOR` trong `OTL Roast Lab.html`.
Thông tin công ty ở hằng `APP_OWNER` ngay bên cạnh.

## 4. Ô ngày `dd-----yyyy` — KHÔNG phải lỗi của app

Bản rà soát 07/09 (mục 8) xếp việc ô ngày Lịch sử hiện `dd-----yyyy` là lỗi giao
diện. Đo lại thì **không phải**:

- Bản Chromium headless mà bộ kiểm dùng thiếu dữ liệu ICU nên rơi về định dạng
  `dd-MMM-yyyy`. Chỗ tháng là placeholder ba dấu gạch → đọc thành `dd-----yyyy`;
  điền giá trị vào thì ra `01-Sep-2026`, tháng bằng tiếng Anh.
- Đã thử `locale` **vi-VN, en-GB, en-US** — ra **y hệt nhau**, nên không phải do
  ngôn ngữ trang.
- Thuộc tính `lang` đặt trên chính ô input **không đổi được gì** — Chromium lấy
  locale của trình duyệt, không đọc `lang`.
- App đóng gói chạy WebView2 của Windows, có đủ ICU, nên hiện `dd/mm/yyyy`.

Kết luận: **không vá gì trong code**. Chỉ ghi định dạng vào nhãn cho chắc ăn ở
mọi máy, và ghi chú lại ngay cạnh chỗ tạo ô để lần sau khỏi đuổi theo lần nữa.

## 5. Đợt hai — màn Hồ sơ, khối lượng mẻ, số đếm thật

### 5.1 Màn Hồ sơ: lưới ba cột, thẻ gọn

Đây là khoảng cách lớn nhất còn lại so với bản thiết kế. Thiết kế xếp **3 cột
thẻ gọn** (6 hồ sơ trong một màn); app đang **1 thẻ mỗi hàng**, ở 1600px chỉ
thấy một thẻ rưỡi — đúng mục 7 bản rà soát Open Design.

Nguyên nhân: `.profgrid` để 2 cột, và `@media(max-width:1700px)` còn ép xuống
**1 cột**. Đo theo bề rộng **cửa sổ** là sai công cụ ở đây — lưới nằm trong
`#stage` cố định **2560×1440** rồi mới thu nhỏ cả sân khấu, nên cửa sổ nhỏ không
có nghĩa là lưới hẹp. Nay: **3 cột**, chỉ hạ còn 2 cột ở màn thật sự thấp.

Thẻ dựng lại theo thiết kế: chỉ còn **huy hiệu mức rang** ở đầu thẻ; ba số
nạp/xả/thời gian vào **một ô lõm chia đều ba cột**; vùng đường cong hạ từ 100px
xuống 64px và dòng "chưa có đường cong" căn trái thay vì là một ô trống to giữa
thẻ; **sao · sửa · xoá dời xuống hàng thao tác ở đáy** cạnh nút *Nạp & rang*,
mỗi nút 56px cho ngón tay đeo găng. `margin-top:auto` ghim hàng nút xuống đáy để
các thẻ cùng hàng có nút thẳng nhau dù ghi chú dài ngắn khác nhau.

Tiêu đề trang đổi thành **"Hồ sơ rang"** theo thiết kế, và đổi theo tab con
(sang *Công thức nạp* thì tiêu đề đổi theo, trước đây tên chung nên không cần).

### 5.2 Cột "Khối lượng" — đã làm, số do THỢ nhập

Thêm cột `charge_kg REAL` vào bảng `batches`. Kho đã tạo từ bản cũ thì
`CREATE TABLE IF NOT EXISTS` không đụng tới nữa, nên có bước **tự thêm cột**
(`_them_cot_thieu`) — chỉ thêm, không bao giờ xoá hay đổi cột cũ.

**Số này do thợ nhập, KHÔNG lấy từ cân.** PC_Link có trường `scale` (cân phễu
`netW100`), nhưng cân đo lượng **còn trong phễu** chứ không phải lượng đã vào
trống; quy ra khối lượng mẻ là đoán hành vi máy. Nên panel *sau mẻ* có thêm một
ô nhập kg + nút Lưu, chặn dải 0–1000 kg ở **cả hai phía** (JS và
`roast_db.set_weight`). Bỏ trống = xoá số đã ghi.

Cột hiện trong bảng Lịch sử; ô nào chưa ghi thì để `—`.

API mới: `db_batch_set_weight(bid, kg)`.

### 5.3 Số đếm mẻ thật

Thêm `RoastDb.count(query, date_from, date_to)` và `db_batch_count`. Trước đây
`db_batch_list` chỉ trả từng trang nên không chỗ nào lấy được số tổng — bản
thiết kế ghi "127 mẻ đã lưu" thì app phải ghi mô tả thay. Giờ lối đi nhanh
*Lịch sử mẻ* và dòng phụ trang Lịch sử đều ghi số thật. Chưa đọc được kho thì
vẫn quay về ghi mô tả, **không đoán bừa một con số**.

## 6. Đợt ba — dọn nốt bản rà soát Open Design

### 6.1 Màu BT/ET — gom về MỘT nguồn

Bản rà soát ghi "ET lệch màu: `--c-et` là `#1673b1` nhưng `liveET` ra
`rgb(158,16,25)`". Đo lại thì **nặng hơn thế**: ở màu chủ đạo OTL nền sáng,
thanh trên cùng hiện **BT xanh / ET đỏ** trong khi khung Rang hiện **BT cam /
ET xanh** — hai chỗ trong cùng một app, ý nghĩa màu **đảo ngược nhau**.

Ba nguồn mâu thuẫn cùng tồn tại:

| Nơi | BT | ET |
|---|---|---|
| `:root` (lối cũ) | `#2563eb` xanh | `#ef4444` đỏ |
| `#pane-rang` nền tối | `#fa7b0c` cam | `#30a7df` xanh |
| Thanh trên cùng | tô cứng `--blue-ink` | tô cứng `--red-ink` |

Mực chung `--blue-ink`/`--red-ink` còn dùng cho **nút xoá, báo lỗi, nút lửa** —
mượn vào cho BT/ET là màu dữ liệu đi theo những việc chẳng liên quan.

Đã gom: `:root` giữ **BT cam · ET xanh** cho mọi màu chủ đạo, thêm hai mực riêng
`--bt-ink`/`--et-ink` **bằng chính màu chuỗi** — đo được **5,07:1** và **5,10:1**
trên nền thẻ sáng, **7,36:1** và **7,91:1** trên nền tối, đều qua chuẩn 4,5:1 nên
không cần mực mượn nữa. Bỏ hết bản sao rải rác ở `data-accent="otl"` và
`#pane-rang`. Sửa luôn hai chỗ tô sai nghĩa: nhiệt **xả** (số của BT) trước đây
tô bằng màu ET.

Kết quả đo lại: BT và ET **giống hệt nhau** ở `:root`, `#pane-rang`, thanh trên
cùng và thẻ số — qua cả 3 màu chủ đạo × 2 nền.

### 6.2 Thiết bị phụ ở màn thấp — thêm dấu hiệu cuộn

Ở 1366×768 khối cao ~239px mà chứa ~654px nội dung (**7 thiết bị, thấy 2**).
Đếm số đang bật và nút thu gọn thì các đợt trước đã làm; **thiếu đúng dấu hiệu
cuộn** — không có gì báo còn thiết bị bên dưới, buồng đốt khói nằm cuối danh sách
coi như không tồn tại.

Thêm vệt mờ ở mép trên/dưới, **chỉ hiện khi phía đó còn nội dung** (hết cuộn là
tắt, không phải trang trí), và nhãn đếm ghi cả tổng: **"0/6 đang bật"**.

### 6.3 Lỗi có sẵn lộ ra: một gói thiếu trường làm chết cả vòng cập nhật

Thêm bộ theo dõi cuộn làm `test_ui_personalization` hỏng **chập chờn ~50%** với
lỗi `Cannot read properties of undefined (reading 'toFixed')`. Chạy lại bản cũ
4 lần đều đạt → đúng là do đợt này. Nhưng lỗi **không nằm trong code mới**:

`applyMachine(d)` gọi thẳng `d.bt.toFixed(1)` ngay dòng đầu, không kiểm gì. Gói
dữ liệu nào thiếu `bt`/`et`/`gas` là **ném lỗi ngay dòng đầu**, nên toàn bộ phần
còn lại của hàm — gas/gió/trống, nút nạp/xả, trạng thái lửa — **không chạy nữa**.
Trên máy thật, một gói Modbus thiếu trường là màn Rang **đứng hình** giữa lúc máy
đang chạy mà thợ không hề biết. Bộ theo dõi cuộn chỉ xê dịch nhịp làm nó lộ ra.

Đã vá: ô nào thiếu thì ghi `—` đúng quy ước, **các ô khác vẫn cập nhật**; mức
gas/gió/trống thiếu thì **giữ giá trị đang có** thay vì gán `undefined`. Kiểm
bằng gói đủ / thiếu bt+et / rỗng hẳn. Chạy lại bộ chập chờn **6/6 đạt**.

### 6.4 Hai bộ kiểm "hỏng sẵn" — là GIẢ ĐỊNH sai, không phải lỗi app

`test_api_scope` và `test_mcp_roaster` ghim cứng thư mục dữ liệu là
`tools/appdata`. Nhưng `app_data_dir()` trả **hai chỗ khác nhau**: chạy dev thì
`tools/appdata`, còn bản **EXE đóng gói để dữ liệu cạnh exe** (`tools/dist`).
App đang chạy là EXE → khoá do bộ kiểm tạo nằm chỗ máy chủ không đọc → **mọi
khoá hợp lệ bị 401**, báo sai 10 và 6 phép, trong khi phần phân quyền của app
vốn đúng.

Thêm `tools/otl_testdata.py`: **dò chứ không đoán** — tạo khoá chỉ-đọc tạm trong
từng thư mục ứng viên rồi gọi thử API, thư mục nào làm khoá có tác dụng thì đó là
thư mục thật; khoá tạm luôn được xoá, không để lại file khoá rỗng. Hai bộ kiểm
giờ **ĐẠT HẾT**.

⚠ Lưu ý khi chạy `test_api_scope`: nó gửi `POST /api/write {"name":"gas","value":0}`
**thật** vào app đang chạy. Lần này an toàn vì app không cấu hình cổng COM nào
(`app_config.json` rỗng, MCP báo `could not open port 'COM9'`). **Đừng chạy bộ
này khi app đang nối máy rang thật.**

## 7. Còn nợ

Hai màn **Kho & Kinh doanh** và **Cài đặt** thì bản thiết kế **chưa vẽ** — không
có gì để áp. Bản rà soát Open Design đến đây đã xử hết.

## 8. Kiểm chứng

Bộ kiểm mới: `tools/test_ui_overview_history.py` — soát ba bước chuẩn bị (chỉ một
bước sáng), ngày trong lời chào, ba lối đi nhanh, bảng ba mẻ, thẻ bảng Lịch sử
(tiêu đề dính đỉnh, phân trang ở đáy trong thẻ), và toàn bộ nội dung hộp Giới
thiệu. Quét tràn/chồng ở 1920×1080, 1366×768, 1280×800 × nền sáng/tối × VI/EN.

Chạy lại **16 bộ kiểm sẵn có**: `consistency`, `layout_motion`, `workflow`,
`dialog_layout`, `audit`, `open_design_feedback`, `personalization`,
`roast_columns`, `match_reference`, `toolbar`, `live`, `compat_roast`,
`portpick`, `ror`, `vacuum`, `autodrop` — **tất cả đạt**, không lỗi JS.

Đợt ba bổ sung vào bộ kiểm mới: màu BT/ET đồng nhất qua 3 màu chủ đạo × 2 nền,
dấu hiệu cuộn của Thiết bị phụ ở đầu/cuối danh sách, và `applyMachine` sống sót
với gói đủ / thiếu trường / rỗng.

Kho dữ liệu kiểm riêng trên kho giả dựng theo **schema cũ**: cột `charge_kg`
được thêm đúng, `count()` đúng cả khi lọc ngày/chữ, `set_weight` chặn số âm, 0,
>1000 và chữ, xoá về `NULL` chạy đúng.

**Chốt cuối: 28/28 bộ kiểm ĐẠT** — 17 giao diện + 11 còn lại
(`api_scope`, `mcp_roaster`, `apikey`, `web_pin`, `lease_t2`, `roast_derive`,
`style_export`, `config_api_mcp`, `telemetry_control_mcp`, `otl_link`,
`roast_history_search`). Không lỗi JS.

## 9. Đóng gói

Đã build đúng tên chuẩn **`tools/dist/OTL Roast Lab HMI.exe`** (46,2 MB).
Phải đóng app đang chạy trước (`WinError 5` — app chạy là khoá file exe); app
lúc đó **không nối máy nào** nên đóng an toàn, và đã mở lại, `:8555` trả lời
bình thường. Bản tên-có-ngày tạm thời đã xoá để khỏi lẫn.

Đã bung file HTML nhúng trong EXE ra đối chiếu: **md5 khớp** bản trên đĩa, có đủ
chuỗi mới (`Chuẩn bị mẻ rang`, `APP_AUTHOR`, `Khối lượng`, `--bt-ink`,
`aux-down`, `Giới thiệu`).

Lối tắt Start: đã có sẵn `OTL Roast Lab HMI.lnk` trỏ đúng exe chuẩn nên ô ghim
của chủ máy tự trỏ sang bản mới. Windows 10/11 **chặn ghim tile bằng script**
(bỏ verb `taskbandpin`) — tạo lối tắt trong danh sách ứng dụng là hết mức tự động.

Build có hai cảnh báo lành: `pycparser.lextab` / `pycparser.yacctab` không tìm
thấy — giống các bản build trước.

**CHƯA chạy với máy rang thật.**
