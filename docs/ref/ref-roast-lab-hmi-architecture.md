# Kiến trúc — OTL Roast Lab HMI

Tài liệu thiết kế cho app giao diện cảm ứng **OTL Roast Lab** (máy rang cà phê/ca cao).
Nguồn: `OTL Roast Lab.html` (gốc repo) + vỏ desktop `tools/roast_lab_hmi.py`.

> 👉 **Cần biết LÀM GÌ / thứ tự nào? → `docs/plan/plan-hmi-roadmap.md`** (bối cảnh
> 16h/ngày + lộ trình 3 GĐ + cut-line MVP). File này là **chi tiết thiết kế** để tra
> khi implement, KHÔNG phải để đọc từ đầu tới cuối.

> Cập nhật: 2026-07-14. Doc gồm **HAI phần**: (a) **kiến trúc hiện trạng** — cái
> đang chạy (sim HTML + vỏ pywebview), và (b) **thiết kế nâng cấp** — chưa code
> (§14–19 và các mục đánh ⭐). Mục ⭐ **phần lớn NGOÀI MVP GĐ1** (xem cut-line ở
> roadmap). Nếu doc thấy quá đồ sộ, đó là chủ ý ghi lại tầm nhìn — việc cần code
> trước nằm gọn trong roadmap.

---

## 0. Bối cảnh vận hành & lộ trình → đã tách ra `plan-hmi-roadmap.md`

> **La bàn của toàn bộ thiết kế** (app nối **máy rang thật, 16h/ngày**, thứ tự ưu
> tiên sản xuất-first) + **lộ trình 3 GĐ + cut-line MVP** nay nằm ở
> **`docs/plan/plan-hmi-roadmap.md`** — file ngắn để **mở hằng ngày khi code**.
>
> Doc này (kiến trúc) là **chi tiết thiết kế** để tra khi implement. Muốn biết
> **làm gì / thứ tự nào** → đọc roadmap trước.

---

## 1. Triết lý thiết kế

Năm nguyên tắc **giao diện** (đã đạt, giữ nguyên) + ba nguyên tắc **hệ thống**
(hướng thương mại hóa, xem §14–18). Cột "Hướng nâng cấp" ghi rõ điều gì thay đổi
khi lên bản bán được — để nguyên tắc cũ không bị hiểu là bất biến.

| Nguyên tắc | Chi tiết | Hướng nâng cấp |
|---|---|---|
| **Vanilla, 1 file** | Toàn bộ UI (HTML + CSS + JS) trong **một file** `OTL Roast Lab.html`. Không framework, không bundler, không bước build cho giao diện. | Giữ. Đây là lợi thế bảo trì — nâng cấp KHÔNG đổi sang framework (roadmap §1.1). |
| **Offline hoàn toàn** | Không CDN, Google Fonts hay API ngoài. Font hệ thống (Bahnschrift/Segoe UI), nhúng `.woff2` base64 nếu cần. | Giữ. Xưởng rang không có internet ổn định; license/update đều làm **offline** (§16.4). |
| **Scale-to-fit** | Authoring khung cố định **2560×1440**, co vừa mọi màn bằng `transform: scale`. | Giữ. |
| **Cảm ứng trước** | Nút to, vùng chạm rộng, bàn phím ảo riêng; nhắm panel công nghiệp FHD 1920×1080 (~10–15.6″). | Giữ. Bổ sung kiosk hardening (khóa thoát, watchdog — §16.6). |
| **Lưu tại chỗ** | Mọi dữ liệu (hồ sơ, lịch sử, tài khoản, cấu hình) trong `localStorage`. Không server. | **Đổi**: dữ liệu quan trọng xuống **SQLite tầng Python** (§16.2); localStorage chỉ giữ theme/lang. |
| **Tin cậy đặt đúng tầng** | *(mới)* UI **không giữ bí mật, không tự quyết**. Xác thực, nhật ký, license nằm ở tầng người dùng **không chạm được**. | Kéo trust boundary từ JS xuống Python (§15). Lý do: xem 9 lỗ hổng §14. |
| **Rang theo mục tiêu** | *(mới)* Hồ sơ = **đường cong mục tiêu**, không phải metadata thuần. Nạp hồ sơ → curve mờ hiện nền, rang bám theo, xả mẻ đối chiếu ngay. | Hồ sơ mang `curve`+`target` (§18.3, 18.5, 18.6). |
| **An toàn phân tầng** | *(mới)* HMI chỉ **giám sát + ra lệnh có kiểm soát**; vòng điều khiển + giới hạn cứng nằm ở **firmware STM32**. HMI chết thì mẻ vẫn an toàn. | Clamp lệnh 2 tầng + heartbeat khi nối Modbus (§16.7). |

**Nâng lên đẳng cấp thế giới — 4 nguyên tắc bổ sung** (biến "đẹp/tiện" thành
"chuẩn công nghiệp bền 10 năm"):

- **Fail-safe là mặc định**: mọi trạng thái không chắc chắn (mất kết nối, thiếu
  dữ liệu, lỗi cảm biến) đều **rơi về phía an toàn** và **nói rõ** — không bao giờ
  im lặng đoán. Thiết kế cho lúc hỏng, không chỉ lúc chạy tốt.
- **Đo được (observability)**: mọi sự kiện quan trọng để lại dấu (audit §16.3,
  alarm §19, checkpoint §6) — sự cố ở xưởng khách **tái dựng được từ log**, không
  phải đoán qua điện thoại.
- **Trải nghiệm ngang app tiêu dùng**: 60fps, phản hồi <100ms, chuyển cảnh mượt,
  chạm là thấy — thợ rang không cảm giác đang dùng "máy công nghiệp thô". Đây là
  khác biệt bán hàng so với HMI Delta/PLC truyền thống.
- **Bền qua thời gian (10 năm)**: nền chuẩn web (không khoá framework theo mốt),
  dữ liệu có schema_version + migration, cập nhật offline ký số — máy bán 2026 vẫn
  nâng cấp được tới 2030+ mà không viết lại.

### 1.1 UI/UX cho MỌI người — đơn giản, đẹp, ai cũng xài được ⭐

Nguyên tắc nền, áp **mọi màn** (không phải tính năng riêng): thợ trẻ hay chủ lớn
tuổi, mắt tốt hay cận/lão thị, đều dùng được mà không thấy rối.

- **Đơn giản mặc định, sâu khi cần (progressive disclosure)**: mỗi màn chỉ show
  việc chính + 1 hành động nổi bật; tùy chọn nâng cao gấp sau nút "Nâng cao". Người
  mới không ngợp, người rành vẫn tới được chỗ sâu. (Đã áp §9.1/§9.2/§8.4.)
- **Chữ to, đọc được cho mắt kém**: cỡ chữ nền ≥ 16px thật trên FHD (§3), có **thanh
  chỉnh cỡ chữ toàn app** (100–150%) lưu theo tài khoản; theme `clarity` cho lão
  thị (chữ XL, tương phản AAA — §4.2). Không phụ thuộc người dùng đeo kính.
- **Tương phản & màu an toàn**: chữ ≥ 4.5:1 mọi theme; trạng thái **không chỉ bằng
  màu** mà kèm icon + chữ (an toàn cho mù màu); đỏ/amber/xanh dùng nhất quán.
- **Vùng chạm rộng**: nút ≥ 44px, cách nhau đủ — tay to, tay run, đeo găng đều
  trúng; không có mục tiêu chạm tí hon.
- **Nhất quán tuyệt đối**: cùng một kiểu thẻ/overlay/numpad/nút cho mọi thư viện
  (Preheat §7.1, Mục tiêu §8.3, Phase §8.4) — **học 1 lần, dùng mọi nơi**, không
  phải nhớ mỗi màn một kiểu.
- **Đẹp nhưng phục vụ chức năng**: khoảng thở, phân cấp thị giác rõ, chuyển động có
  ý nghĩa (§7.1.1) — đẹp để **dễ đọc dễ dùng**, không phải trang trí gây nhiễu.
- **Tha thứ lỗi**: xác nhận việc nguy hiểm, Hoàn tác khi sửa (§8.3), nhắc gợi ý
  thay vì chặn cứng — người dùng không sợ bấm sai.
- **Ít chữ, nhiều hình + ngôn ngữ đời thường**: dùng icon + số lớn + câu dễ hiểu
  (như alarm §19), tránh thuật ngữ/mã kỹ thuật ở lớp mặt; đa ngôn ngữ (§4.3).

---

## 2. Ngăn xếp & đóng gói

```
┌─────────────────────────────────────────────┐
│  OTL Roast Lab HMI.exe  (PyInstaller onefile)│
│  ┌───────────────────────────────────────┐  │
│  │  roast_lab_hmi.py  (pywebview)        │  │
│  │  · mở cửa sổ fullscreen               │  │
│  │  · nạp HTML từ _MEIPASS (bundle)      │  │
│  │  · private_mode=False + storage_path  │  │
│  │    %LOCALAPPDATA%\OTL Roast Lab HMI   │  │
│  │  ┌─────────────────────────────────┐  │  │
│  │  │  WebView2 (Edge Chromium)       │  │  │
│  │  │  render: OTL Roast Lab.html     │  │  │
│  │  └─────────────────────────────────┘  │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

- **Vỏ desktop**: `pywebview` mở cửa sổ native, backend WebView2 (có sẵn trên Win10/11).
- **Đóng gói**: `tools/RoastLabHMI.spec` → `dist/OTL Roast Lab HMI.exe`. HTML nhúng trong bundle, lấy ra qua `sys._MEIPASS`.
- **Bền dữ liệu**: pywebview mặc định `private_mode=True` (xoá localStorage khi đóng). App **tắt** chế độ ẩn danh + trỏ `storage_path` cố định để giữ PIN/hồ sơ/lịch sử.
- **Cầu JS↔Python**: `Api.toggle_fullscreen()` — hiện chỉ bật/tắt fullscreen. Đây là **điểm mở rộng** để sau này nối Modbus/serial thật.

**Ranh giới tin cậy hiện tại vs mục tiêu** (chi tiết §14–16):

```
HIỆN TẠI (mọi thứ ở tầng UI — người dùng chạm được)
  exe ─▶ pywebview (chỉ fullscreen) ─▶ WebView2 ─▶ HTML/JS + localStorage
                                                    ▲ auth, audit, config, curve
                                                    │ đều nằm ở đây → §14 lỗ hổng

MỤC TIÊU (kéo bí mật xuống tầng Python — xem §15)
  exe ─▶ core Python  (auth · store SQLite · audit · license · modbus)
           ▲ js_api whitelist, validate
           └─ WebView2 ─▶ HTML/JS  (chỉ hiển thị + nhập)
```

- **Cầu JS↔Python** mở rộng từ 1 hàm `toggle_fullscreen()` thành **API whitelist**
  (`login`, `load_*`, `save_*`, `audit`, `set_burner`…), mỗi hàm **validate tham
  số** trước khi chạm dữ liệu/serial. Không expose hàm tùy tiện ra `window`.
- **Đóng gói bản bán**: thêm ký số Authenticode + `.pyd` cho `auth`/`license`
  (§16.5) — onefile hiện tại trích xuất được bằng `pyinstxtractor` (§14 #6).
- **Một exe, hai chế độ**: demo (sim) và máy thật dùng chung binary, chọn nguồn
  dữ liệu runtime qua interface `DataSource` (§16.7) — không build 2 bản.

**Hiện đại hóa — trụ được tới 2030+:**

- **WebView2 evergreen**: bám runtime Edge Chromium tự cập nhật của Windows → nền
  web luôn mới (CSS/JS đời mới) mà không phải nhúng trình duyệt riêng; nhẹ, vá bảo
  mật theo Windows.
- **Tính nặng đẩy sang WASM/Python**: nội suy curve, AUC, lọc RoR, phát hiện mốc
  chạy ở tầng Python hoặc WebAssembly — mượt cả trên panel yếu, tách khỏi luồng vẽ.
- **Cập nhật OTA offline, ký số + bản vá delta**: gói `.otlpkg` ký Ed25519 (§16.5),
  chỉ tải phần thay đổi; cài từ USB hoặc mạng nội bộ; **rollback** nếu bản mới lỗi.
- **Build tái lập + CI**: spec + lockfile pin phiên bản, dựng trong CI cho ra binary
  **reproducible** (băm khớp) — bán hàng loạt vẫn truy vết được đúng bản nào ở máy nào.
- **Sẵn đường đa nền tảng**: lõi tách tầng (UI web thuần + core Python) cho phép
  sau này chạy panel **ARM/Linux** hoặc vỏ **Tauri/Rust** nhẹ hơn mà **không viết
  lại UI** — không khoá cứng vào Windows/pywebview.
- **Telemetry chọn tham gia**: (khi khách đồng ý) gửi ẩn danh chỉ số sức khoẻ máy
  về OTL để cải tiến — mặc định tắt, hợp quyền riêng tư.

### 2.1 Yêu cầu phi chức năng (NFR)

Doc trước chỉ nói tính năng; phần này chốt **giới hạn vận hành** để không thiết kế
vượt sức phần cứng panel.

- **Cấu hình panel tối thiểu** (chốt trước khi mua panel): CPU 2 nhân ~1.5GHz, RAM
  ≥4GB, disk ≥32GB, WebView2 runtime, Win10/11. Nếu panel yếu hơn → giảm animation
  (dùng theme `clarity`/reduce-motion), tách canvas nền (§6.2).
- **Ngân sách hiệu năng**: vẽ lại chart ≤ **16ms/khung** (60fps) lúc rang; cập nhật
  số live **1s**; poll Modbus không được làm treo UI (§16.9). Panel yếu: chấp nhận
  30fps, vẫn phải mượt khi chạm.
- **Ngân sách bộ nhớ**: HTML + i18n(vi/en) + theme ≤ vài chục MB; buffer curve mẻ
  đang chạy ~320 điểm × 6 giá trị (RAM không đáng kể).
- **Bền vận hành**: chạy **24/7 nhiều ngày** không rò bộ nhớ (watchdog §16.6 là
  lưới an toàn, không phải cái cớ để rò); mất điện đột ngột **không hỏng dữ liệu**
  (§16.2).
- Các con số trên là **mốc kiểm thử**, đo thật trên panel đích trước khi chốt.

### 2.2 Mô hình 3 tầng · định vị · đồng bộ với máy ⭐

Đúc kết một buổi thảo luận — **nền tảng để hiểu app này là gì và làm được tới đâu.**

**Máy rang có 3 tầng, app OTL là tầng ③ (lớp thông minh), KHÔNG thay tầng ②:**

```
① Firmware STM32           bộ não: vòng điều khiển + AN TOÀN (cắt gas, giới hạn cứng)
② HMI trên máy (Delta DOP) bàn tay cơ bản: charge/drop/gas — LUÔN có, chạy độc lập
③ App PC (OTL Roast Lab)   lớp THÔNG MINH: hồ sơ, curve, lịch sử, phân tích, quản lý
```

- **③ là lớp CỘNG THÊM, không phải điểm chết**: ① + ② giữ máy rang được **dù PC
  tắt/treo/đang update**. → App PC được phép tham vọng (business layer, phân tích)
  mà không gánh "sập là máy đứng". Yêu cầu uptime (§2.1) vì thế **nhẹ hơn**: mất app
  thì thợ quay lại Delta HMI xả mẻ tay, **mẻ không mất**.

**Định vị**: firmware **đã có sẵn khe "PC điều khiển"** (`STT_GAS_SOURCE_PC`,
`STT_PC_CONTROL_ON`, `STT_HMI_PC_CMD_*` trong `MachineStatus.h` — vốn cho Artisan).
App OTL **thay/nâng cấp khe Artisan-trên-PC** — may đo cho máy OTL, tiếng Việt, +
lớp quản lý. **Không phải "HMI thay Delta"** (Delta là nền an toàn), mà là **"phần
mềm PC thông minh cắm vào máy — làm mọi thứ Artisan làm + hơn"**.

**Hai ngữ cảnh chạy (cùng một app)**: vì là app desktop, không khoá vào panel cứng:

| Chạy ở | Ngữ cảnh | Làm gì | Điều khiển máy? |
|---|---|---|---|
| **Panel cạnh máy** (nối Modbus) | Vận hành | Rang, control, số live, đọc-từ-xa | Có (khi PC control ON) |
| **PC văn phòng** (không nối máy) | Quản lý | Kế hoạch SX, kho, cupping, báo cáo, xem lại | Không (đọc/quản lý) |

→ Việc bàn giấy (kế hoạch/kho/cupping — GĐ4) thiết kế cho **màn văn phòng**, KHÔNG
cho panel nóng-bụi cạnh lò. Đa-bản chia sẻ dữ liệu = lý do thật của **cloud opt-in**.

**Đồng bộ với máy = cùng đọc/ghi MỘT bảng thanh ghi firmware** (không phải P2P):

```
   Firmware register map = SỰ THẬT DUY NHẤT
   (CHARGE_BTN_R/W · DROP_BTN · gas · progStep · BT/ET · profile values…)
        ▲                              ▲
   Delta HMI (view+control)      App PC (view+control)
```

- Bấm **CHARGE trên PC** → ghi `CHARGE_BTN_W` → firmware xử lý → Delta HMI đọc **cùng
  register** ở vòng kế → nút cũng sáng. **Tự khớp vì chung nguồn**, firmware phân xử.
- **"PC control ON"** = cho phép app **ghi** register điều khiển (`naviSource=PC`);
  tắt → app chỉ đọc, Delta/biến trở cầm lái. **Hai chiều**: app đẩy cả **lệnh** lẫn
  **dữ liệu hiển thị** (tên hồ sơ, mốc mục tiêu) lên register để Delta hiện.
- **4 điều phải đúng**: (1) poll ~4–10Hz để "thấy" đồng bộ ~100–250ms; (2) **ghi
  xong đọc lại** xác nhận (cặp `_R`/`_W`); (3) **firmware gác xung đột** — `progScan()`
  chỉ nhận lệnh đúng bước, hai bên bấm loạn không phá nhau; (4) **register map =
  hợp đồng** → cần version handshake (§16.9), lệch map là bấm nhầm nút.

> Chi tiết nối firmware ở §13, §16.7, §16.9. Quy trình rang gốc (14 bước `progStep`)
> ở `docs/ref/ref-roast-process-firmware.md`.

---

## 3. Bố cục file HTML

```
OTL Roast Lab.html  (~2500 dòng)
├── <head>
│   └── <style>                     — toàn bộ CSS
│       ├── :root + [data-theme]    — biến màu, font (theo preset, xem §4.2)
│       ├── [data-accent]           — tông màu chủ đạo + custom (hue)
│       ├── layout khung + topbar
│       ├── .pane (mỗi tab)         — Tổng quan / Rang / Hồ sơ / Lịch sử / Cài đặt
│       ├── component styles        — thẻ, nút, bảng, biểu đồ, overlay…
│       └── @media override FHD     — phóng chữ ≥16px khi co 0.75×
├── <body>
│   ├── SVG sprite <symbol>         — bộ icon OTL (charge, flame, drop, cool…)
│   ├── #app                        — khung chính (topbar + tabnav + panes)
│   │   ├── #pane-tongquan
│   │   ├── #pane-rang              — state machine rang + preheat panel ở tongquan
│   │   ├── #pane-hoso
│   │   ├── #pane-lichsu
│   │   └── #pane-caidat            — subnav: Kết nối/Calib/Model/Nhật ký/Tài khoản
│   ├── overlays                    — #numpad #keyboard #picker #profedit #roastmgr
│   │                                 (+ #targetmgr §8.3 · #preheatmgr §7.1 · #phasemgr §8.4 · #axes §9.1)
│   │                                 (+ #profview §18.6 · #compare §18.2 · #stats §18.7 · #alarmlog §19)
│   ├── #login                      — màn đăng nhập PIN
│   └── <script>                    — toàn bộ JS (xem §5)
```

> **Nguyên tắc bố cục khi mở rộng**: mọi tính năng mới ở §18 đều **thêm overlay**
> (`#profview`, `#compare`) và **thêm lớp vẽ** vào `drawChart`, KHÔNG đẻ file mới —
> giữ đúng triết lý 1 file (§1). CSS theme mới (§4.2) là các khối `[data-theme=…]`
> nối tiếp, không sửa cấu trúc DOM.

> **Nguồn nhiều file → ship 1 file (khi tới hạn ~2500 dòng)**: ~2500 dòng hiện tại
> + i18n + theme + ~12 overlay dễ lên 15–20k dòng — sửa bằng str-replace thành ác
> mộng. Giải: viết `scripts/assemble.py` **nối** `src/*.css` + `src/*.js` +
> `index.html` thành **đúng một** `OTL Roast Lab.html` lúc build. Đây **KHÔNG phải
> bundler** (không transpile/minify/tree-shake/resolve import) — chỉ nối văn bản
> theo thứ tự. Sản phẩm ship vẫn **1 file** (đúng §1, roadmap §1.1), nhưng nguồn tách nhỏ
> để người còn đọc/sửa nổi. Đằng nào đã có bước build PyInstaller rồi, thêm bước
> nối này gần như miễn phí.

---

## 4. Hệ thống nền tảng

### 4.1 Layout scale-to-fit
- `fit()` tính tỉ lệ = min(vw/2560, vh/1440), áp `transform: scale` cho `#app`.
- `refit()` gọi lại `fit()` + vẽ lại biểu đồ (debounce 60ms) khi resize/xoay màn/`ResizeObserver`.
- **Lưu ý vùng chạm dưới `transform: scale`**: nút "thấy" 44px nhưng khi co 0.75×
  thì vùng chạm vật lý còn ~33px — phải **thiết kế nút đủ to Ở KHUNG 2560** để sau
  khi co vẫn ≥44px thật trên panel đích (§1.1). Toạ độ chạm/tooltip trên canvas
  phải **chia lại theo tỉ lệ scale** (điểm chuột / scale) — dễ lệch nếu quên. Bắt
  buộc **test chạm thật trên FHD**, không chỉ xem ở khung 2K.

### 4.2 Theme & màu chủ đạo

**Hiện tại**: `html[data-theme]` sáng/tối (lưu `otl_theme`) + `html[data-accent]`
6 tông (otl/emerald/azure/teal/violet/amber) + custom theo hue (lưu `otl_accent`/
`otl_hue`), mặc định **otl** (đỏ + xanh theo logo). Màu chuỗi dữ liệu (BT/ET/ABT/
RoR/Burner) giữ **cố định** mọi theme để đọc biểu đồ nhất quán.

**Nâng cấp — bộ PRESET theo nhóm người dùng** (user yêu cầu 2026-07-13). Máy rang
bán cho nhiều đối tượng rất khác nhau; mỗi **preset** không chỉ đổi màu mà gói cả
**5 trục**: bảng màu · font · độ tương phản · mật độ (spacing) · bo góc — chọn 1
phát ra "cá tính" phù hợp. Kỹ thuật: `html[data-theme="<preset>"]` set trọn bộ
biến CSS `--bg/--panel/--txt/--radius/--fs-scale/--gap/--font`; lưu `otl_theme`.

| Preset | Nhóm nhắm tới | Đặc trưng thị giác |
|---|---|---|
| **`workshop`** (mặc định máy) | Thợ rang tại xưởng | Tương phản CAO, nền trung tính ấm chống lóa, nút to, ít trang trí — đọc được dưới đèn xưởng, tay đeo găng vẫn chạm trúng. |
| **`executive`** | Chủ doanh nghiệp | Nền than + nhấn **vàng đồng**, sang trọng, số liệu nổi bật (dashboard-forward), font serif nhẹ ở tiêu đề. |
| **`elegant`** | Phụ nữ trẻ | Pastel hồng/kem, bo góc lớn, khoảng thở rộng, font tròn mềm — nhẹ nhàng, hiện đại. |
| **`warm`** | Phụ nữ lớn tuổi | Tông đất ấm (terracotta/kem), **chữ to hơn 1 bậc**, tương phản dịu mắt, chuyển động tối giản — dễ chịu, không gắt. |
| **`sharp`** | Đàn ông khó tính | Đơn sắc đen-trắng, cạnh vuông, không đổ bóng thừa, mọi chỉ số căn lưới chính xác — "công cụ", không màu mè. |
| **`vibrant`** | Người trẻ năng động | Nền tối + nhấn neon (lime/cyan/magenta), hiệu ứng nhấn nảy, năng lượng cao. |
| **`clarity`** | Người già / thích đơn giản | **Chữ XL**, tương phản tối đa (WCAG AAA), nút cực to, bỏ bớt thành phần phụ, mỗi màn 1 việc chính — chống rối. |
| **`engineer`** | Kỹ sư / kỹ thuật viên | Xanh xám lạnh, **font số monospace**, mật độ dày (nhiều số/màn), hiện thêm RoR/ΔBT/áp suất — dữ liệu là trên hết. |

- **Trục dữ liệu bất biến**: dù preset nào, màu BT/ET/RoR và ngưỡng an toàn
  (amber/đỏ cảnh báo) **không đổi** — an toàn vận hành không phụ thuộc gu thẩm mỹ.
  Mỗi preset chỉ cần đạt **tương phản ≥ 4.5:1** cho chữ, kiểm bằng công thức của
  skill `ui-ux-pro-max`/`dataviz` khi chốt bảng màu.
- **Gợi ý theo vai trò**: lần đầu đăng nhập, `operator` → `workshop`, `master` →
  `executive`; người dùng đổi tuỳ ý ở Cài đặt, lưu **theo tài khoản** (không phải
  toàn máy) để mỗi người một gu trên cùng panel.
- **Chọn nhanh**: ô xem trước (swatch + chữ mẫu) trong Cài đặt → Giao diện, chạm
  là áp ngay (live preview), không cần khởi động lại.
- Tách preset thành **block CSS độc lập** (`[data-theme="warm"]{…}`) nối tiếp nhau
  — thêm preset sau này không đụng DOM/JS, đúng triết lý 1 file (§1, §3).

### 4.3 Đa ngôn ngữ (i18n)

**Hiện tại**: `I18N = {vi, en}`, key dạng `nhóm.tên` (vd `rang.start`, `ph.title`);
`applyLang()` quét mọi `[data-i18n]` gán text theo `LANG` (lưu `otl_lang`); chuỗi
động tra `I18N[LANG][key]` lúc runtime.

**Nâng cấp — kiến trúc chừa 7 slot, NHƯNG chỉ ship vi/en** (chốt lại sau review
2026-07-13). Dịch là **cam kết bảo trì** (mỗi lần thêm chuỗi phải dịch lại 7 bản),
không phải tính năng bật một lần. Máy chưa có đơn xuất đi Ý/Thái mà gánh 5 bản dịch
chết là tự đeo đá. Vậy: **`I18N` thiết kế sẵn 7 slot** (fallback, tách khối, `Intl`
format), nhưng **GĐ1 chỉ điền vi/en**; zh/th/fr/it/pt **kích hoạt khi có đơn xuất
khẩu** nước đó (roadmap §2), lúc đó mới thuê/nhờ dịch và cam kết duy trì.

| Mã | Ngôn ngữ | Ghi chú |
|---|---|---|
| `vi` | **Tiếng Việt** | **MẶC ĐỊNH** (thị trường gốc). |
| `en` | English | Ngôn ngữ dự phòng (fallback) khi thiếu key. |
| `zh` | 中文 (Trung) | Cần font CJK — nhúng subset `.woff2` (không dùng font hệ thống được đủ). |
| `th` | ไทย (Thái) | Chữ Thái cao dòng — nới `line-height` riêng để không cắt dấu. |
| `fr` | Français | Chuỗi dài hơn ~20% so với vi/en — kiểm tràn nút (xem dưới). |
| `it` | Italiano | Tương tự fr về độ dài. |
| `pt` | Português | Tương tự fr về độ dài. |

- **Chuỗi dài & bố cục**: fr/it/pt dài hơn đáng kể → nút và nhãn phải co chữ
  (`min` font-size) hoặc xuống dòng gọn, KHÔNG tràn. Test trước bằng ngôn ngữ dài
  nhất, không chỉ vi.
- **Font**: vi/en/fr/it/pt dùng Latin (font hiện tại đủ dấu); **zh cần font CJK**,
  **th cần font Thái** — nhúng subset base64 để giữ offline (§1). Tải font theo
  ngôn ngữ đang chọn, không nhồi hết vào bundle.
- **Fallback theo key**: thiếu key ở ngôn ngữ nào → tự lấy `en` rồi `vi`, không
  hiện key thô ra màn. Có script kiểm "key nào thiếu bản dịch" trước khi phát hành.
- **Cấu trúc**: `I18N` phình to → tách phần dịch thành khối riêng trong `<script>`
  (vẫn 1 file), mỗi ngôn ngữ một object, gộp lúc nạp. Số/nhiệt/thời gian format
  theo `Intl` của ngôn ngữ (dấu thập phân, 24h/12h).
- **Chọn nhanh**: cờ + tên bản ngữ ở topbar (thay toggle vi/en 2 trạng thái hiện
  tại bằng picker 7 mục), lưu theo tài khoản như theme (§4.2).

### 4.4 Điều hướng tab & tương tác thông minh

**Hiện tại**: `gotoTab(name)` ẩn mọi `.pane`, hiện `#pane-<name>`, cập nhật tab
active; hook theo tab: `rang`→`updateRoastLive()`, `hoso`→`renderProfiles()`,
`lichsu`→`renderHistory()`, `caidat`→`enterSettings()`.

**Nâng cấp — điều hướng bám ngữ cảnh vận hành** (không chỉ chuyển tab thụ động):

- **Khóa an toàn khi đang rang**: phase RUNNING mà bấm rời tab Rang → **xác nhận**
  ("Đang rang, rời màn?") và giữ **thanh mini vẫn hiện BT + thời gian + nút Xả**
  ở topbar dù ở tab khác — không bao giờ "mất dấu" mẻ đang chạy.
- **Tab động theo tiến trình**: app tự đưa người dùng tới nơi cần: xong Preheat →
  gợi sang Rang; ở NOSEL bấm rang → nhảy Hồ sơ; xả mẻ (DONE) → nút "Xem tổng kết"
  giữ tại chỗ, không đá đi. Mọi cú nhảy đều có nút Quay lại.
- **Nhớ ngữ cảnh**: mở lại app về đúng tab/hồ sơ đang dở (trừ khi mẻ đã xong);
  master và operator có tab mặc định riêng (§4.2).
- **Cảnh báo chủ động (toast/banner)**: mất kết nối serial, RoR vọt bất thường,
  gần mốc FCs, nhiệt vượt ngưỡng → banner ưu tiên cao đẩy lên bất kể đang ở tab
  nào. Khung thông báo chung này chi tiết ở **§19 (Alarm)** — nguồn từ `STT_W`.
- **Cử chỉ cảm ứng**: vuốt ngang đổi tab (trừ khi đang rang), chạm-giữ số liệu để
  xem chi tiết/đổi đơn vị — hợp thao tác tay trên panel.
- Hàm liên quan (mới): `navGuard()` (chặn rời khi RUNNING) · `pushToast(level,msg)`
  · `miniLiveBar()` (thanh mẻ nổi ở topbar).

---

## 5. Tổ chức JavaScript

Script chia theo cụm chức năng (không module, cùng scope global):

| Cụm | Hàm/biến chính |
|---|---|
| Layout | `fit` `refit` `gotoTab` `tickClock` |
| Hồ sơ | `loadProfiles/saveProfiles` `renderProfiles` `editProfile` `newProfile` `deleteProfile` `saveProfEdit` `setProfFilter` `cycleSort` |
| Mức rang | `loadRoasts/saveRoasts` `openRoastMgr` `addRoast` `removeRoast` |
| Lịch sử | `loadHist/saveHist` `renderHistory` `nextBatchCode` |
| **Rang (state machine)** | `R` (state) `MILES` `curveAt` `startRoast` `roastTick` `togglePause` `finishRoast` `newRoast` `loadProfile` `updateRoastLive` `updatePhaseBar` `drawChart` |
| **Preheat** | `PH` (state) `phStep` `phRender` `phStart` `phTick` `phDone` `phStop` `phToggle` |
| Điều khiển output | `toggleMode` `stepOut` `toggleView` `toggleDev` |
| Theme/i18n | `setTheme` `setAccent` `setCustomAccent` `applyLang` `toggleLang` |
| Cấu hình | `CFG` `loadCfg` `initConfig` `settingsSave` `openPick` `openNumpadFor` |
| Nhập liệu | `openKb`/`okKb` (bàn phím) · `buildNumPad`/`openNumpadFor` (numpad số) |
| Auth | `pbkdf2` `loadUsers` `renderLogin` `loginSubmit` `pushAudit` `getLock/registerFail` |

**Nâng cấp — quy ước namespace khi file phình** (thêm so-mẻ §18, bridge Python
§15, 7 ngôn ngữ §4.3 sẽ làm script lớn nhanh). Chưa cần bundler, nhưng gom mỗi
cụm vào **một object toàn cục** để khỏi đụng tên và đọc rõ ranh giới:

| Namespace | Gói | Ghi chú |
|---|---|---|
| `RNG.*` | state machine rang, `curveAt`, `drawChart` | trái tim app (§6) |
| `PROF.*` | hồ sơ + curve mục tiêu + view chi tiết | §8.1, §18.3, §18.6 |
| `CMP.*` | so sánh mẻ, bảng DONE vs mục tiêu | §18.2, §18.5 |
| `PH.*` | preheat (đã là object) | §7 |
| `UI.*` | theme/i18n/toast/nav guard/overlay | §4.2–4.4 |
| `NET.*` | cầu tới Python (`api.*`), nguồn dữ liệu | §2, §15 |

- **Ranh giới lớp**: `NET.*` là **chỗ DUY NHẤT** gọi `pywebview.api` — không rải
  lời gọi Python khắp nơi, để đổi sim↔thật (§16.7) chỉ đụng một chỗ.
- **Vẽ dùng chung**: tách phần vẽ series của `drawChart` thành `RNG.drawSeries
  (ctx, pts, style)` để chart chính, nền mục tiêu (§18.3), overlay so sánh
  (§18.2) và view hồ sơ (§18.6) **cùng một hàm** — như `curveAt` đang dùng chung.
- **Sự kiện**: gom lắng nghe (resize, visibility, key, touch) vào `UI.bindEvents()`
  gọi 1 lần lúc khởi động, thay vì rải `addEventListener` rải rác.
- **Store phản ứng nhỏ (nguồn sự thật duy nhất)**: ~12 overlay + nhiều namespace →
  dễ **desync** (badge alarm, thanh mini live, theme, trạng thái kết nối hiện ở
  nhiều nơi). Thêm một **observable store tí hon** (`STATE` + `subscribe`): đổi state
  ở một chỗ → mọi nơi hiển thị tự cập nhật. Không cần thư viện (~30 dòng JS thuần),
  vẫn 1 file. Tránh bug "chỗ này đổi mà chỗ kia quên cập nhật".
- Vẫn **1 file** (§1); "module hóa" ở đây là kỷ luật đặt tên, không phải import.

---

## 6. State machine màn Rang

Trái tim của app. Trạng thái lưu trong object `R`, phản ánh ra DOM qua thuộc tính
`#pane-rang[data-phase]` (CSS ẩn/hiện overlay theo phase).

```
        loadProfile(idx)          startRoast()         Xả mẻ / hết curve
 NOSEL ───────────────► IDLE ──────────────► RUNNING ──────────────► DONE
   ▲   (chọn hồ sơ ở      │  (BẮT ĐẦU)          │ roastTick 1s/lần      │
   │    tab Hồ sơ)        │                     │ togglePause freeze    │
   └─────────────────────┘◄────────────────────┴───────────────────────┘
       (chưa có hồ sơ)          newRoast() — giữ hồ sơ, KHÔNG về NOSEL
```

| Phase | Ý nghĩa | UI |
|---|---|---|
| `NOSEL` | Chưa chọn hồ sơ (mặc định) | Overlay "Chưa chọn hồ sơ rang" + nút → tab Hồ sơ. Ẩn nút BẮT ĐẦU. |
| `IDLE` | Đã nạp hồ sơ, chờ bắt đầu | Nút tròn **BẮT ĐẦU** + tên hồ sơ + nút "Đổi hồ sơ". |
| `RUNNING` | Đang rang | Curve vẽ dần, số liệu live, mốc + phase bar sáng theo tiến độ. `roastTimer` = `setInterval(roastTick, 1000)`. |
| `DONE` | Đã xả mẻ | Banner tổng kết (mã mẻ, thời gian, nhiệt xả, dev%, mốc) + nút Mẻ mới / Về Tổng quan. Tự lưu Lịch sử. |

Biến phụ trợ: `started = (phase==='RUNNING'||phase==='DONE')` dùng để cổng logic
"đã bắt đầu mẻ chưa" (đồng hồ, mốc, số live, phase bar).

**Nâng cấp — state machine "biết nghĩ"** (không chỉ chuyển phase thụ động):

- **Đồng hồ theo mốc thật, không đếm tick**: `R.elapsed` tính bằng
  `Date.now() − startTs` (trừ thời gian pause), `setInterval` chỉ là nhịp vẽ —
  tránh **drift** của `setInterval(1000)` và việc WebView2 **throttle** timer khi
  mất focus. Bắt buộc khi nối máy thật để mốc mẻ khớp giây thực.
- **Phase phụ theo dữ liệu**: RUNNING tự nhận biết sự kiện từ curve — chạm TP
  (RoR đổi dấu), vào FCs (theo nhiệt/thời gian mục tiêu) → **tự đánh dấu mốc** +
  đẩy toast (§4.4), không chờ người bấm.
- **Cổng an toàn ở chuyển phase**: startRoast chặn nếu chưa Preheat đạt nhiệt hoặc
  mất kết nối; finishRoast xác nhận nếu xả **quá sớm** so với mục tiêu (tránh chạm
  nhầm). Mọi cổng ghi lý do vào `pushAudit`.
- **Khôi phục sau mất điện/crash**: RUNNING ghi checkpoint nhẹ (elapsed, mốc, mode)
  mỗi vài giây; mở lại app giữa mẻ → hỏi "Tiếp tục mẻ đang dở?" thay vì mất trắng.
- **Trạng thái lỗi tường minh**: thêm nhánh `FAULT` (mất serial / cảm biến lỗi /
  vượt ngưỡng an toàn) — hiện banner đỏ + giữ số cuối cùng, không im lặng.

### 6.1 Mô hình đường cong (sim)
- **`curveAt(m)`** — hàm **thuần**, trả `{bt,et,abt,ror,burner}` tại tiến độ `m ∈ [0,1]`.
  Dùng **chung** cho cả `drawChart()` (vẽ) lẫn `updateRoastLive()` (số live) → hình và số **luôn khớp**.
- **`ROAST_SECS = 642`** (10:42) — tổng thời gian mẻ mẫu; `R.prog = R.elapsed / ROAST_SECS`.
- **`MILES[]`** — 5 mốc TP/DE/FCs/DEV/DROP theo giây; tự chuyển `todo→now→done` khi `elapsed` vượt.
- **`PH_BOUND`** — biên 3 pha Sấy `[0,372]` / Maillard `[372,580]` / Phát triển `[580,642]` giây;
  `updatePhaseBar()` sáng pha đang chạy, mờ pha chưa tới.

**Nâng cấp — tách nguồn curve, sim chỉ là một `DataSource`:**

- `curveAt` (sim) và BT/ET thực (Modbus) **cùng ký giao diện** `sample(t) →
  {bt,et,abt,ror,burner}` qua interface `DataSource` (§16.7). `drawChart`/
  `updateRoastLive` không biết đang sim hay thật — đổi nguồn runtime, không sửa UI.
- **RoR làm mượt**: RoR thực nhiễu (xem đường tím răng cưa trong ảnh §18.6) →
  lọc trượt (cửa sổ ~5–15 s, cùng tinh thần `rorBT_pro` firmware) trước khi vẽ,
  giữ số gốc cho tính toán. Sim thì mượt sẵn.
- **Mốc từ hồ sơ mục tiêu**: `MILES`/`PH_BOUND` không còn là hằng của curve mẫu —
  đọc từ `R.target[]` (§18.3) để phase bar và mốc bám đúng hồ sơ đã chọn.
- **Pha cài được, không cứng 3 pha**: `PH_BOUND` thay bằng `phaseScheme` (§8.4) —
  số pha 2–4, tên/màu/ranh giới cài qua `#phasemgr`; ca cao định mốc theo nhiệt/
  thời gian thay vì crack. `updatePhaseBar()` đọc scheme này.

### 6.2 Biểu đồ (`drawChart`)
- Canvas + DPR scaling. Trục nhiệt (trái) / RoR (phải) / thời gian (dưới), tự-scale hoặc cố định theo `CFG.ch_*`.
- Now-line theo `R.prog`; chỉ vẽ curve khi `prog>0` (`hasData`); ẩn now-line khi DONE.

**Nâng cấp — biểu đồ nhiều lớp, một hàm vẽ:**

- **Lớp vẽ chồng** (dưới → trên): (1) dải pha nền, (2) **curve mục tiêu mờ + nét
  đứt** (§18.3), (3) curve thực đậm, (4) mốc + nhãn, (5) now-line. Cùng bộ trục.
- **Một hàm series dùng chung** `RNG.drawSeries(ctx, pts, style)` (§5) cho cả
  chart chính, nền mục tiêu, overlay so sánh (§18.2), view hồ sơ (§18.6).
- **Vẽ mượt & tiết kiệm**: chỉ vẽ lại khi có điểm mới hoặc resize (`requestAnimation
  Frame` gộp), giảm tải cho panel yếu; tách canvas nền (dải pha + mục tiêu, ít đổi)
  khỏi canvas động (curve thực) để khỏi vẽ lại toàn khung mỗi giây.
- **Đọc dễ khi vận hành**: chạm-giữ trên curve hiện tooltip {giờ, BT, RoR}; ΔBT so
  mục tiêu (§18.3) tô ngay trên đường — thợ rang thấy lệch mà không cần đọc số.

### 6.3 Điều khiển output
- `R.mode` MANUAL/AUTO; MANUAL cho chỉnh Burner/Airflow/Drum bằng nút ± bước `OUT_STEP=5`.
- `OUT_MAX` = Burner/Air 0–100%, Drum 0–200 rpm. Loop chỉ bật ở AUTO.
- `DEV{}` — trạng thái thiết bị phụ (Drum-Fan/Mixer/Cooling/Afterburner/Loader/Destoner).

---

## 7. Preheat (làm nóng máy)

Panel ở tab **Tổng quan** (thay panel "Trạng thái máy" cũ). State trong object `PH`.

```
 Sẵn sàng ──phStart()──► Đang làm nóng ──cur≥tempSet──► Đã đạt nhiệt
   (idle)   (LÀM NÓNG)     (running)      phDone()        (done)
      ▲                        │
      └───────phStop()─────────┘  (DỪNG giữa chừng)
```

- Đặt **Nhiệt đích** (`phStep('temp',±5)`, 80–230°C) và **Thời gian** (`±1`, 3–40 phút) bằng nút ±.
- START → `phTick` mỗi giây tăng `PH.cur` thêm `PH_RATE=6°C/s` (demo nhanh) tới đích; thanh Process = `(cur−start)/(tgt−start)`.
- Đây là **sim** — chưa nối gas thật; nối firmware sau ở `phTick`.

**Nâng cấp — giao diện phản chiếu firmware, không giành quyền điều khiển:**

- **HMI KHÔNG tự chạy logic gas**: firmware đã có state machine preheat hoàn chỉnh
  (Preheat.h RoR-based / Preheat_PID.h — xem repo). Khi nối thật, `phTick`
  **đọc** giai đoạn + nhiệt + gas/gió firmware đang chạy và **hiển thị**, không tự
  tăng `PH_RATE` hay đẩy gas — tránh **2 bộ não** giành nhau (§13 đã theo nguyên tắc này).
- **Bám 4 giai đoạn firmware**: hiện đúng GĐ đang chạy (WARMUP/IGNITE/RAMP/HOLD…)
  + thời gian còn lại ước tính, thay vì chỉ 1 thanh %. Người vận hành thấy máy
  đang ở đâu trong quy trình mồi lửa.
- **Trực quan sẵn sàng rang**: preheat đạt nhiệt + ổn định → thẻ chuyển xanh +
  gợi "Có thể vào mẻ" (nối cổng an toàn startRoast §6). Chưa đạt mà bấm rang →
  cảnh báo.
- **An toàn hiển thị rõ**: mất lửa / quá nhiệt / |ET−BT| vượt ngưỡng (guard
  firmware) → banner đỏ + lý do, không để người dùng đoán.
- Vẫn giữ **sim độc lập** cho demo bán hàng (không có tủ điện): `PH_RATE` chỉ
  dùng khi `DataSource = Sim` (§16.7).

### 7.1 Thư viện Hồ sơ Preheat ⭐

Hiện preheat chỉ đặt tay **nhiệt đích + thời gian** mỗi lần. Nâng thành **bộ kịch
bản preheat** quản lý được, cùng khuôn thư viện Mục tiêu rang (§8.3). Lưu
`otl_preheats`. Lý do: mỗi dòng hạt / mức rang / mùa cần nhiệt trống trước khi vào
mẻ khác nhau; lưu sẵn để **chọn 1 phát**, không dò lại.

**Tối đa 6 kịch bản** (user chốt) — dạng **6 ô cố định** (như preset radio), không
phải thư viện vô hạn: đủ dùng, chọn nhanh bằng mắt, không rối. Giao sẵn vài kịch
bản mẫu trong `DEF_PREHEATS` (vd "Rang nhạt 190°", "Rang đậm 205°", "Tiết kiệm",
"Vào mẻ nhanh"), khách **đổi tên + sửa** thoải mái; ô trống thì hiện "+ Thêm kịch
bản". Mỗi ô hiện **tên + nhiệt đích + ngày sửa gần nhất**.

```
preheat = { id, name, note, customer,
            createdAt, updatedAt,
            targetTemp,        // nhiệt trống đích trước khi charge (°C)
            soakMin,           // giữ ổn định bao lâu trước khi cho vào mẻ
            rampMode,          // NHANH / TIẾT KIỆM / NHẸ NHÀNG (gợi ý cho firmware)
            burnerType }       // premix / thường (map burnerPremix_R, xem repo)
```

**Thông minh hơn:**

- **Tự gợi ý theo Mục tiêu rang**: chọn hồ sơ rang → app đề xuất `targetTemp` từ
  `chargeTemp` của mục tiêu (trống thường **nóng hơn** nhiệt charge một khoảng
  theo model). Không phải nhớ "hạt này charge bao nhiêu".
- **Sẵn sàng = đạt nhiệt + ỔN ĐỊNH**, không chỉ chạm số: bám pha HOLDING/PRECISION
  của firmware (Preheat.h/Preheat_PID.h) — hết `soakMin` mà nhiệt dao động nhỏ mới
  báo "Sẵn sàng vào mẻ" (nối cổng an toàn startRoast §6). Tránh charge lúc trống
  chưa đều nhiệt.
- **ETA đếm ngược**: ước tính "còn ~X phút tới sẵn sàng" theo tốc độ lên nhiệt
  thực — thợ rang canh việc khác, không đứng nhìn.
- **Giữ ấm giữa các mẻ (idle warm)**: rang xong không để nguội hẳn; hồ sơ preheat
  biết **hồi nhiệt về mức charge** cho mẻ kế — rang liên tục nhanh hơn, đỡ tốn gas
  so với đun lại từ nguội.
- **Chế độ tiết kiệm**: `rampMode = TIẾT KIỆM` lên nhiệt chậm hơn nhưng ít gas;
  `NHANH` khi cần vào mẻ gấp. Chỉ là **gợi ý** xuống firmware, firmware quyết cuối.
- **Quản lý 6 ô**: **đặt tên** từng kịch bản, **sửa** mọi tham số, **nhân bản** vào
  ô trống, **xoá** (ô về "+ Thêm"); chặn tạo ô thứ 7. Mỗi ô hiện **ngày sửa gần
  nhất** (`updatedAt`). Sửa qua overlay `#preheatmgr` (bản nháp, Huỷ/Lưu), Lưu cập
  nhật `updatedAt` + ghi `pushAudit`.
- **Nhắc thân thiện, không chặn cứng**: `targetTemp` quá cao/thấp so với model →
  chip vàng gợi ý; chỉ chặn khi vượt trần an toàn firmware.
- **Vẫn phản chiếu firmware** (§7): hồ sơ preheat chỉ **đặt mục tiêu + gợi ý**;
  vòng điều khiển gas/gió do firmware chạy. HMI không tự đẩy gas.
- Hàm mới: `loadPreheats/savePreheats` · `openPreheatMgr` · `newPreheat/editPreheat/
  clonePreheat/deletePreheat` · `suggestPreheat(target)` (gợi ý từ mục tiêu rang).

#### 7.1.1 UI/UX — lưới 6 thẻ kịch bản, đẹp & dễ chạm

Bố cục **lưới thẻ 3×2** (FHD ngang) / **2×3** (dọc), thẻ to cho tay đeo găng, mỗi
thẻ là một "kịch bản" tự kể nội dung bằng hình — chọn bằng mắt, không phải đọc.

```
┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
│ ◔ Rang nhạt         │ │ ◕ Rang đậm      ●SEL │ │ ⌁ Vào mẻ nhanh      │
│                     │ │                     │ │                     │
│    190°   ╱▔▔       │ │    205°   ╱▔▔▔      │ │    200°   ╱▔ (dốc)  │
│    soak 3′  ·nhẹ    │ │    soak 4′  ·tiết k.│ │    soak 2′  ·NHANH  │
│  sửa 07/11      ✎   │ │  sửa hôm nay    ✎   │ │  sửa 05/11      ✎   │
└─────────────────────┘ └─────────────────────┘ └─────────────────────┘
┌─────────────────────┐ ┌─────────────────────┐ ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐
│ Ca cao 30kg         │ │ Giữ ấm (idle)       │    +  Thêm kịch bản
│    210°   ...       │ │    170°   ...       │   (ô trống, viền đứt)
└─────────────────────┘ └─────────────────────┘ └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘
```

Chi tiết thị giác & tương tác:

- **Mini "ramp sparkline"** trên mỗi thẻ: đường lên nhiệt tượng trưng theo `rampMode`
  — NHANH dốc đứng, TIẾT KIỆM thoải, NHẸ NHÀNG cong mềm. Thấy tính cách kịch bản
  ngay, không cần đọc chữ.
- **Mã màu theo `rampMode`** (viền/chip trái thẻ): NHANH = cam/đỏ ấm, TIẾT KIỆM =
  xanh lá, NHẸ NHÀNG = xanh dương. Nhất quán với trục màu bất biến (§4.2).
- **Nhiệt đích là số LỚN** (nhân vật chính của thẻ); tên ở trên, `soak` + mode ở
  dưới, **ngày sửa** cỡ nhỏ mờ ở chân — phân cấp thị giác rõ.
- **1 chạm = chọn** (viền sáng accent + dấu ●SEL + nảy nhẹ); **nút ✎** hoặc chạm-giữ
  → mở `#preheatmgr` sửa. Không lẫn chọn với sửa.
- **Ô trống**: viền đứt mờ + "＋ Thêm kịch bản", nhấp nháy nhẹ mời tạo — không bao
  giờ là khoảng trống chết.

**Trạng thái SỐNG khi đang làm nóng** (thẻ đang chọn "biến hình"):

- Thẻ nở rộng thành **thẻ tiến trình**: **vòng/thanh nhiệt đổ đầy** từ nhiệt hiện
  tại → đích, số nhiệt chạy mượt, **ETA đếm ngược** to ("còn ~4′"), nhãn pha
  firmware (WARMUP/RAMP/HOLDING).
- **Đạt + ổn định** → thẻ **chuyển xanh, tick ✓, chữ "Sẵn sàng vào mẻ"** + nhịp
  thở nhẹ (pulse) mời charge; nối cổng an toàn startRoast (§6).
- **Sự cố** (mất lửa/quá nhiệt) → thẻ **đỏ + rung nhẹ 1 lần** + lý do; không im lặng.
- Chuyển động **có ý nghĩa, không màu mè**: fill/ease ~200–300ms, tôn trọng mật độ
  của theme (§4.2) và giảm hiệu ứng ở theme `clarity` (người lớn tuổi) — chữ XL,
  bỏ pulse gây rối.

**Dễ dùng hơn:**

- **Gợi ý ngay trên lưới**: khi đã chọn Mục tiêu rang, kịch bản **khớp `chargeTemp`
  nhất** được viền gợi ý + nhãn "Đề xuất" — mắt biết chọn cái nào.
- **Sửa tại chỗ nhanh**: chỉnh nhiệt/soak bằng **nút ± to** hoặc numpad (§11); kéo
  không bắt buộc. Xem trước ramp cập nhật tức thì.
- **Trải nghiệm nhất quán**: `#preheatmgr` dùng lại khuôn overlay + numpad + kiểu
  thẻ của `#targetmgr` (§8.3) — học 1 lần, dùng mọi nơi.

---

## 8. Mô hình dữ liệu & lưu trữ

**Hiện tại**: tất cả trong `localStorage`, **không schema version** (điểm yếu khi
nâng cấp — xem §14 #7).

| Key | Nội dung | Fallback khi trống |
|---|---|---|
| `otl_profiles` | Mảng hồ sơ rang `{name,notes,roast,temp,time,color,date,roaster}` | `DEF_PROFILES` (4 mẫu) khi `null`; mảng rỗng → **empty state** mời tạo |
| `otl_roasts` | Danh sách mức rang (Nhạt/Vừa/Đậm…) | `DEF_ROASTS` (3 mức) |
| `otl_history` | Mảng mẻ đã rang `{code,name,color,time,temp,dev,date}`, mới nhất đầu, tối đa 50 | `DEF_HIST` (5 mẫu) |
| `otl_users2` | Tài khoản `{name,role,salt,pin(hash),perms,enabled}` | `null` → chế độ tạo master lần đầu |
| `otl_audit2` | Nhật ký thao tác `{ts,user,action,field,old,new}` | `[]` |
| `otl_cfg2` | Cấu hình (Kết nối/Calib/Model/Trục biểu đồ) | `CFG_DEFAULT` |
| `otl_locks` | Khoá đăng nhập `{name:{fails,until}}` | `{}` |
| `otl_theme` `otl_accent` `otl_hue` `otl_lang` | Tuỳ biến giao diện | mặc định otl/dark/vi |

**Nâng cấp — tách 3 lớp dữ liệu theo độ nhạy** (nền cho §15–16):

| Lớp | Gồm | Đích | Lý do |
|---|---|---|---|
| **Bí mật** | `users` (hash PIN), `audit` (hash-chain), `license`, `locks` | **SQLite tầng Python** ở `%PROGRAMDATA%`, pepper/key bọc DPAPI | Người dùng không được sửa (§14 #1,#2,#4) |
| **Nghiệp vụ** | `targets` (curve+mốc, §8.3), `profiles` (trỏ `targetId`), `preheats` (≤6, §7.1), `phaseScheme` (§8.4), `machine` (tùy chọn phần cứng, §9.2), `history` (+`batch_curves`), `alarms` (§19), `roasts`, `cfg` | **SQLite** cùng DB, có `schema_version` + migration + backup | Dữ liệu khách phải sống qua nâng cấp + so mẻ (§18) |
| **Sở thích** | `theme`, `accent`, `hue`, `lang` | **theo tài khoản → bảng `users` (SQLite)**; localStorage chỉ giữ **lựa chọn của lần đăng nhập cuối** làm mặc định màn Login | Gu mỗi người khác nhau trên cùng máy |

> **Làm rõ (sửa mâu thuẫn)**: §4.2/4.3 nói theme/lang "theo tài khoản" — vậy chúng
> phải nằm trong bảng `users` bên SQLite (nạp khi login, lưu khi đổi), KHÔNG phải
> localStorage-theo-máy. localStorage chỉ giữ **preset của phiên đăng nhập gần nhất**
> để màn Login (trước khi biết là ai) hiển thị đúng gu, rồi login xong nạp gu thật
> của tài khoản. Đây là ngoại lệ nhỏ, không mâu thuẫn "bí mật xuống Python".

- **Schema version + migration**: mỗi bảng mang `schema_version`; nâng app chạy
  migration tự động lúc khởi động. Di trú **một lần** từ localStorage cũ qua
  `api.migrate(payload)` — khách cũ không mất hồ sơ (§16.2).
- **Sao lưu/khôi phục**: `.otlbak` (zip + checksum) xuất USB; lịch sử mẻ xuất thêm
  **CSV tương thích Artisan** dùng chung dữ liệu `batch_curves` (§18.1).
- **Toàn vẹn**: audit là chuỗi HMAC (§16.3); backup có checksum để phát hiện hỏng.

### 8.1 Hồ sơ (CRUD)
- **Đọc/ghi**: `loadProfiles`/`saveProfiles`. Render `renderProfiles()` (lọc theo mức rang, sort tên/nhiệt/thời gian).
- **Sửa**: `editProfile(i)` → modal `#profedit` (bản nháp `peTmp`), 7 field (Tên/Ghi chú/Mức rang/Nhiệt xả/Thời gian/Ngày/Thợ). `saveProfEdit()` ghi lại.
- **Tạo**: `newProfile()` — hồ sơ trắng mặc định, chỉ ghi storage khi bấm Lưu (`peIdx=-1` → push).
- **Xoá**: `deleteProfile(i)` có xác nhận. Xoá hết → empty state có nút tạo (không kẹt).
- **Xem chi tiết** (nâng cấp, xem §18.6): mỗi thẻ thêm nút **kính lúp** → phóng
  hiệu ứng ra overlay `#profview` xem curve mục tiêu + mốc + phase breakdown.

**Nâng cấp — hồ sơ = nhận diện + TRỎ tới một Mục tiêu rang** (user chốt
2026-07-13). Đường cong/mốc mục tiêu **KHÔNG** nhúng trong hồ sơ nữa mà nằm ở
**thư viện Mục tiêu rang** (§8.3); hồ sơ chỉ giữ `targetId`. Nhiều hồ sơ (khác
khách/lô/dòng hạt) **dùng chung** một mục tiêu được — sửa mục tiêu 1 lần, mọi hồ
sơ liên quan cập nhật theo.

```
profile = { name, notes, roast(mức), tags[],   // nhận diện
            beanW, moisture, date, roaster,     // thông tin mẻ
            targetId }                          // ← TRỎ Mục tiêu rang (§8.3)
```

- **Tạo hồ sơ cực gọn**: nhập **Tên + Mức rang**, **chọn Mục tiêu rang** từ thư
  viện (picker có xem trước curve) → **xong**. Các field hạt/tag là tuỳ chọn.
- **`loadProfile()`** đọc `targetId` → nạp `target.curve` của mục tiêu vào
  `R.target[]` (nền mờ §18.3, bảng DONE §18.5, view §18.6).
- **Nhân bản**: "Tạo từ hồ sơ này" clone nhận diện, giữ hoặc đổi `targetId`.
- **Gắn thẻ & tìm nhanh**: `tags[]` (vùng trồng, khách, lô) + ô tìm; lọc/sort mở
  rộng theo tag. Xưởng nhiều hồ sơ vẫn ra ngay.
- **Nhập/xuất hồ sơ** `.otlprof` (JSON ký checksum): xuất **kèm** mục tiêu đang
  trỏ để máy nhận không thiếu curve; nhập kiểm chữ ký + gộp mục tiêu vào thư viện.
- **schema_version** cho mỗi hồ sơ (§8) để nhập từ máy khác không vỡ.

### 8.2 Vòng đời mẻ → Lịch sử
`finishRoast()` sinh bản ghi: mã `nextBatchCode()` tự tăng `#B-xxxx`, dev% = `(dropSec−FCs)/dropSec`,
nhiệt xả = `curveAt(prog).bt`, ngày `dd/mm` → `unshift` vào `otl_history` + `pushAudit`.
Hỗ trợ **xả sớm** (prog theo `elapsed` thật, không cứng 10:42).

### 8.3 Thư viện Mục tiêu rang (CRUD) ⭐

Thực thể **quản lý riêng**, cùng khuôn với "Mức rang" (`#roastmgr`) nhưng giàu hơn
vì mang **đường cong + mốc**. Lưu `otl_targets` (fallback `DEF_TARGETS` vài mẫu
theo dòng hạt phổ biến). Mở qua nút **"Mục tiêu rang"** (tab Hồ sơ hoặc Cài đặt).

```
target = { id, name, roast(mức gợi ý), note,
           customer,                                  // thông tin khách hàng
           createdAt, updatedAt,                      // ngày tạo · sửa gần nhất
           chargeTemp, dropTemp, totalTime, devPct,   // tham số chính
           miles:{tp,de,fcs,drop},                    // mốc: {t, temp}
           curve:[ {t,bt,et,ror,burner}, … ] }        // ĐƯỜNG nền mờ
```

**CRUD cơ bản:**
- **Nhân bản** (`cloneTarget`): copy toàn bộ, tên "… (bản sao)", `createdAt` mới,
  `updatedAt` = nay — nhanh cho một dòng hạt nhiều biến thể.
- **Xoá** (`deleteTarget`) có xác nhận; đang có hồ sơ trỏ tới → cảnh báo + hỏi gỡ
  liên kết trước.
- **Sửa**: overlay `#targetmgr` (bản nháp `tgTmp`, nút Huỷ/Lưu, cờ `dirty` như
  `#profedit`); mỗi lần Lưu cập nhật `updatedAt` + ghi ai sửa vào `pushAudit`.
- **3 cách nạp `curve`**: (1) **từ mẻ thật** — DONE/Lịch sử → "Lưu thành mục tiêu
  rang" copy `batch_curves` (§18.1), cách chính; (2) **nhân bản** rồi tinh chỉnh;
  (3) **từ đầu** — nhập `chargeTemp/dropTemp/devPct` + mốc → app nội suy `curve`.

**Thông minh & thân thiện hơn** (user yêu cầu):

- **Thư viện dạng thẻ có ảnh curve thu nhỏ** (sparkline): nhìn hình dáng đường rang
  ngay trên thẻ, không cần mở — chọn bằng mắt nhanh hơn đọc tên.
- **Tìm & lọc & sort tức thì**: ô tìm theo tên/khách/note; lọc theo mức rang, khách
  hàng, tag; sort **Mới sửa / Tên / Hay dùng**. Xưởng nhiều mục tiêu vẫn ra ngay.
- **"Dùng ở đâu"**: mỗi mục tiêu hiện **số hồ sơ đang trỏ tới** + danh sách; xoá/sửa
  biết ngay ảnh hưởng ai — không xoá nhầm cái đang chạy.
- **Ghim yêu thích** (`pinned`): mục tiêu hay dùng ghim lên đầu; gợi ý mục tiêu
  gần đây khi tạo hồ sơ.
- **Trợ lý tạo từ đầu (wizard 3 bước)**: (1) chọn mức rang → nạp **giá trị mặc định
  hợp lý** (charge/drop/dev theo mức); (2) chỉnh mốc; (3) xem trước curve + xác
  nhận. Người mới không phải đối mặt bảng trắng.
- **Sửa trực quan, có Hoàn tác**: kéo mốc TP/DE/FCs/DROP ngay trên biểu đồ (snap
  lưới, hiện giá trị khi kéo), curve nội suy vẽ lại tức thì; **Undo/Redo** trong
  phiên sửa. Chỉnh số ở panel và kéo trên chart đồng bộ hai chiều.
- **Nhắc nhở thân thiện, không chặn cứng**: cảnh báo **gợi ý** (dev% hơi cao, RoR
  âm ở cuối…) hiện dạng chip vàng cạnh field; chỉ **chặn** khi vô lý thật sự
  (DROP < FCs, thời gian 0). Lời văn hướng dẫn, không phải mã lỗi.
- **So hai mục tiêu**: chọn 2 mục tiêu → overlay chồng curve (tái dùng
  `drawCompare` §18.2) để thấy khác nhau chỗ nào trước khi chọn.
- **Đặt tên gợi ý tự động**: "{Dòng hạt} · {Mức} · {phút}′" điền sẵn, sửa được.
- **An toàn thao tác**: rời khi `dirty` → hỏi lưu; Huỷ khôi phục bản gốc; Lưu là
  hành động rõ ràng (không tự lưu ngầm gây mất kiểm soát).
- **Nhập/xuất** `.otltarget` (ký checksum) để OTL phát hành "mục tiêu mẫu theo
  dòng hạt" và khách chia sẻ giữa máy.
- Hàm mới: `loadTargets/saveTargets` · `openTargetMgr` · `newTarget/editTarget/
  cloneTarget/deleteTarget/pinTarget` · `saveTargetEdit` · `drawTargetEdit`
  (kéo mốc + undo) · `targetUsage(id)` · `compareTargets(a,b)`.

### 8.4 Cài đặt Phase rang (phase scheme) ⭐

Hiện 3 pha bị **cứng** trong `PH_BOUND` (§6.1). Nâng thành **bộ phase cài được** vì
mỗi loại hạt định pha khác nhau — đặc biệt dự án này là **ca cao**, không có "crack"
rõ như cà phê nên mốc phải định theo **nhiệt/thời gian**, không theo tiếng nổ.

**Nền tảng (để cài cho đúng):**

- **Cà phê — 3 pha chuẩn** (Scott Rao / Artisan), phân bởi mốc:
  | Pha | Từ → đến | Ý nghĩa | Tỉ lệ điển hình |
  |---|---|---|---|
  | **Sấy** (Drying) | CHARGE → Dry End (~150–160°C, hạt vàng) | Bay hơi ẩm, thu nhiệt | ~50% |
  | **Maillard** (Browning) | Dry End → FCs (First Crack) | Phản ứng Maillard/caramel, tạo tiền chất hương | ~30% |
  | **Phát triển** (Development) | FCs → DROP | Định vị hương cuối; đo bằng **DTR** | ~15–25% |
- **Mốc**: CHARGE · TP (Turning Point) · Dry End · FCs · (FCe/SCs) · DROP.
- **DTR** (Development Time Ratio) = tg phát triển / tổng — chỉ số then chốt: quá
  ngắn → chua/ngái, quá dài → nhạt/"baked".
- **RoR** (°C/phút) nên **giảm mượt** suốt mẻ; tránh "flick" (RoR vọt gần FC) và
  "crash" (RoR sụt) — sinh lỗi vị.
- **Ca cao khác**: nhiệt thấp hơn, lâu hơn, mốc định theo **nhiệt đạt / thời gian**
  (vd "đạt 130°C", "phút 12") thay cho crack; mục tiêu là đuổi acid, tạo vị chocolate.

**Cần cài cái gì** (`phaseScheme`, gắn theo Mục tiêu rang §8.3, có scheme mặc định máy):

```
phaseScheme = {
  preset,                         // CÀ PHÊ 3 pha / CA CAO 3 pha / ĐƠN GIẢN 2 pha / TUỲ BIẾN
  phases: [ { name, color,        // tên + màu dải (đổi được)
              startAt,            // mốc mở đầu: {kind:'milestone'|'temp'|'time', val}
              targetPct | targetDur,   // mục tiêu: % tổng HOẶC thời lượng mm:ss
              rorMin, rorMax,     // dải RoR mong muốn của pha (°C/phút)
              warnPct } ],        // lệch quá bao nhiêu thì báo amber
  dtrTarget }                     // DTR mục tiêu cho pha phát triển
```

- **Số pha 2–4**, đặt tên + màu từng pha; định **mốc phân định** bằng milestone
  (cà phê) hoặc **nhiệt/thời gian** (ca cao).
- Mỗi pha đặt **mục tiêu thời lượng (% hoặc mm:ss)**, **dải RoR**, **ngưỡng cảnh báo**.
- **DTR mục tiêu** riêng cho pha phát triển.

**Giao diện thông minh, dễ xài** (overlay `#phasemgr`):

- **Thanh pha ngang kéo được**: một thanh chia 2–4 đoạn màu, **kéo vạch ngăn** để
  đổi ranh giới; **% và thời lượng cập nhật tức thì** khi kéo (như kéo mốc §8.3).
  Trực quan hơn gõ số nhiều lần.
- **Preset 1 chạm**: "Cà phê 3 pha (Rao)", "Ca cao 3 pha", "Đơn giản 2 pha" — nạp
  sẵn tên/màu/tỉ lệ hợp lý; sửa tiếp nếu muốn. Người mới không đối mặt bảng trắng.
- **Xem trước trực tiếp trên curve mục tiêu**: dải pha vẽ đè lên biểu đồ (như
  §18.6), thấy ngay pha rơi vào đoạn curve nào — chỉnh bằng mắt.
- **Bảng tỉ lệ sống**: dưới thanh hiện % + mm:ss + DTR, ô lệch ngoài ngưỡng tô
  amber ngay khi cài — biết cấu hình có "cân" không.
- **Gợi ý thông minh**: cảnh báo chip vàng nếu tỉ lệ lệch chuẩn (vd Dev 8% quá
  ngắn, Sấy 65% quá dài) — **gợi ý, không chặn**, vì ca cao/thử nghiệm có thể cố ý.
- **Áp mọi nơi tự động**: phase cài xong dùng chung cho **phase bar khi rang**
  (§6.1), **breakdown ở view chi tiết** (§18.6) và **bảng DONE** (§18.5) — cài 1
  chỗ, cả app theo.
- **Cảnh báo lúc rang** (nối §4.4): sắp chuyển pha / RoR ra ngoài dải pha → toast,
  giúp thợ can thiệp kịp.
- Hàm mới: `loadPhaseScheme/savePhaseScheme` · `openPhaseMgr` · `drawPhaseEditor`
  (thanh kéo + preview) · `applyPreset(name)` · `phaseStats()` (tính %/DTR sống).

**Thông minh hơn nữa:**

- **Học từ mẻ đẹp (đề xuất scheme)**: chọn 1 mẻ lịch sử ưng ý → app **đọc mốc thật**
  (TP/DE/FCs/DROP từ `batch_curves` §18.1) và **đề xuất tỉ lệ pha + dải RoR** khớp
  mẻ đó. Thay vì tự đoán, học từ cái đã làm được.
- **Tự nhận mốc từ đường cong**: khi nội suy/đọc curve, app tự tìm **Dry End** (RoR
  đổi độ cong / hạt vàng theo nhiệt) và **FCs** (theo nhiệt/thời gian mục tiêu) để
  đặt vạch ngăn sẵn — kéo tinh chỉnh sau, không phải căn từ số 0.
- **Nhắc theo ngữ cảnh loại hạt**: đã chọn preset "Ca cao" → dải RoR/tỉ lệ mặc định
  hạ theo (nhiệt thấp, mẻ dài); "Rang nhạt/đậm" nới pha phát triển tương ứng. Gợi ý
  bám thực tế loại hạt, không dùng chuẩn cà phê cho mọi thứ.
- **Cảnh báo dự báo (không chỉ hiện tại)**: lúc rang, nếu đà RoR cho thấy **sẽ vào
  pha kế sớm/muộn** so mục tiêu → nhắc trước vài chục giây để thợ chỉnh gas kịp,
  thay vì báo khi đã lệch (nối `STT_ROR_OVERSHOOT_WARN`/`crash` firmware §19).
- **Kiểm chéo với mục tiêu**: cài phase mà lệch nhiều so `target` đang gắn → chip
  gợi ý "khác mục tiêu, có chủ ý không?" — tránh cấu hình vênh âm thầm.
- **Mẫu theo dòng hạt của OTL**: nhập kèm khi OTL phát hành mục tiêu mẫu (§8.3),
  scheme đi cùng — khách nhập là có ngay bộ pha hợp lý.

---

## 9. Cấu hình (tab Cài đặt)

- **`CFG`** (đã lưu) vs **`CFG_EDIT`** (đang sửa) — tách để có nút Huỷ/Lưu, cờ `dirty`.
- Nhóm field: `CFG_FIELDS` = Kết nối (COM/baud) · Calib gas · Model nhiệt + Trục biểu đồ.
- Nhập: `openPick` (chọn danh sách), `openNumpadFor` (số có min/max/đơn vị).
- `settingsSave(persist)` áp `CFG_EDIT`→`CFG`, ghi `otl_cfg2`, vẽ lại biểu đồ.

**Nâng cấp — cấu hình an toàn, ít sai, phân quyền rõ:**

- **Kiểm & chặn giá trị nguy hiểm**: mọi field có min/max **theo model máy** (đọc
  từ DB, không cho vượt); cảnh báo trước khi lưu giá trị sát ngưỡng an toàn (gas
  max, nhiệt trần). Cấu hình sai không xuống được máy (nối §16.7).
- **Phân quyền theo field**: Kết nối/Calib/Model chỉ **master** sửa; operator xem.
  Mọi thay đổi ghi `pushAudit` (ai, khi nào, cũ→mới) — truy vết được.
- **Trợ lý kết nối**: nút "Dò cổng COM" tự liệt kê cổng + test Modbus (đọc thử 1
  register) báo xanh/đỏ ngay, thay vì gõ tay COM/baud rồi đoán. Hiện trạng kết nối
  hiện thường trực ở topbar.
- **Preset theo model máy**: chọn model (6kg/12kg/30kg…) nạp sẵn bộ giới hạn +
  calib gốc; khách chỉ tinh chỉnh. Giảm rủi ro nhập nhầm từ số 0.
- **Sao lưu/khôi phục cấu hình** + "Khôi phục mặc định nhà máy" (có PIN master) —
  gỡ nhanh khi chỉnh sai. Cấu hình vào chung `.otlbak` (§8).
- **Áp mềm**: đổi COM/baud không cắt mẻ đang chạy — chờ mẻ xong hoặc cảnh báo rõ.

### 9.1 Trục biểu đồ (Axes) ⭐

Hiện chỉ có 4 field thô (`ch_auto/ch_tmax/ch_rmax/ch_time`). Nâng thành hộp Axes
đầy đủ như Artisan (ảnh mẫu) nhưng **để người thường không bao giờ phải mở**:

```
axes = {
  time:  { auto, min, max, step, lock },       // trục thời gian (mm:ss)
  temp:  { min, max, step },                    // trục nhiệt (°C)
  ror:   { auto, min, max, step, showBT, showET },   // trục RoR/Δ (°C/phút)
  grid:  { style, width, opacity, showTime, showTemp },
  legend } // vị trí chú giải
```

**Thông minh — mặc định TỰ VỪA, ẩn phức tạp** (99% người dùng không cần mở hộp):

- **Auto-fit là mặc định**: trục tự co ôm **cả curve thực lẫn curve mục tiêu**,
  chừa lề đẹp, **làm tròn mốc chia** (5/10/20…) cho dễ đọc — đường luôn đầy khung,
  không tràn/tí hon. Đây là điểm khác Artisan (bắt tự chỉnh).
- **Tự nới khi sắp tràn giữa mẻ**: nhiệt/RoR gần chạm mép → trục **giãn mượt**
  (animate), đường không bao giờ đâm ra ngoài khung.
- **Preset theo loại hạt của mục tiêu đang gắn**: ca cao ~180 / rang nhạt ~230 /
  đậm ~250 — không phải nhớ số. Kèm **"Nạp từ hồ sơ"** lấy dải trục từ mục tiêu (§8.3).
- **Ẩn nâng cao**: trục Δ/RoR, grid, legend gom sau **"Nâng cao"** — màn chính chỉ
  còn **Auto + Preset + "Vừa khung"**. Không dội tuỳ chọn.

**Dễ xài & chất lượng:**

- **Zoom/pan cử chỉ**: chụm–mở phóng, kéo dời; nút **"Vừa khung"** về auto-fit tức
  thì — hợp cảm ứng, nhanh hơn gõ Min/Max.
- **Chạm số trên trục để sửa nhanh**: chạm nhãn Max/Min ngay trên biểu đồ → numpad,
  không cần vào hộp Axes.
- **Xem trước sống**: kéo Min/Max/Step trong hộp → chart nhỏ vẽ lại tức thì.
- **Khoá khi rang (Lock)**: tự bật lúc RUNNING; đổi trục giữa mẻ phải mở khoá có
  chủ đích. **Khôi phục mặc định** 1 nút (Restore Defaults).
- **Nét vẽ sắc** (DPR §6.2): grid mảnh, chữ trục rõ mọi theme (§4.2) kể cả `clarity`.
  Nhớ theo tài khoản.
- **Áp mọi biểu đồ**: chart chính, view hồ sơ (§18.6), so sánh (§18.2), thống kê
  (§18.7) — cài 1 chỗ, đồng bộ.
- Hàm mới: `openAxes()` · `axesAutoFit()` · `axesFromProfile()` · `applyAxesPreset`
  · `drawAxesPreview()`; overlay `#axes`.

### 9.2 Tùy chọn phần cứng máy (capability matrix) ⭐

Mỗi máy rang lắp khác nhau — có/không vacuum, có/không biến tần drum, có/không cân
tự động, có/không biến trở (VR)… Hiện các cờ này **cứng trong `Config.h`** (biên
dịch). Nâng thành **bảng tích tùy chọn** trong HMI: tích đúng máy có gì → HMI **hiện
đúng control, ẩn cái không có**, không rối và không lỡ tay ra lệnh cho thiết bị
không tồn tại. Lưu `otl_machine`.

**Các tùy chọn (map thẳng macro `Config.h` thật):**

| Tùy chọn HMI | Cờ firmware (`Config.h`) | Khi TẮT, HMI ẩn/đổi gì |
|---|---|---|
| Điều khiển tốc độ trống (biến tần) | `MACHINE_HAS_DRUM_SPEED_CONTROL` | Ẩn nút Drum RPM (§6.3), bỏ alarm biến tần drum |
| Biến tần quạt gió RS485 | `MACHINE_HAS_AIR_INVERTER` | Gió về on/off; khoá điều kiện cho vacuum |
| Cảm biến vacuum + PID gió | `MACHINE_HAS_VACUUM_SENSOR` | Ẩn cài PID gió / áp hút, alarm vacuum |
| ↳ Nguồn đọc vacuum | `MACHINE_VACUUM_FROM_DRUM` (0=quạt gió·1=biến tần drum) | Chỉ hiện khi có vacuum; chọn nguồn ACI |
| Đầu cân Bluetooth / auto-loader | `MACHINE_HAS_SCALE_FEEDER` | Ẩn auto-loader, cân, ngưỡng nạp (§ loader) |
| Biến trở vật lý (VR) trên board | `MACHINE_VR_SOURCE_FROM_HMI` (0=có VR·1=setpoint từ HMI) | Xem "VR vs no-VR" bên dưới |
| Loại đầu đốt (thường/premix) | `burnerPremix_R` (runtime, addr 29) | Đã chọn được lúc chạy; ảnh hưởng preheat (§7.1) |
| Khối lượng mẻ danh định (kg) | `MACHINE_BATCH_KG` | Suy ngưỡng auto-loader, preset trục/nhiệt |
| Thiết bị phụ: Afterburner · Destoner · Feeder · Mixer/Cooling | relay onboard (`IOConfig.h`) | Ẩn nút tương ứng ở dải thiết bị (§6.3) |

**Thông minh — giao diện suy từ khả năng máy (capability-driven UI):**

- **Tích là ẩn/hiện**: HMI không hiện nút/cài/alarm của thứ máy không có. Máy không
  drum-speed → mất luôn Drum RPM; không vacuum → mất tab PID gió; không cân → mất
  auto-loader. Gọn đúng máy, người vận hành không bối rối.
- **Ràng buộc phụ thuộc**: vacuum **cần** air inverter → tắt air inverter thì vacuum
  tự mờ + nhắc lý do; "nguồn đọc vacuum" chỉ hiện khi có vacuum. Không cho cấu hình
  mâu thuẫn.
- **VR vs no-VR** (đúng biến thể `code-no-potentionmeter`): **có VR** → gas/gió/drum
  điều khiển bằng biến trở vật lý, HMI **chỉ hiển thị** giá trị (nút ± mờ/ẩn, tránh
  người tưởng chỉnh được mà VR ghi đè); **no-VR** → HMI là **nguồn setpoint**, nút
  ± hoạt động thật. UI phản ánh đúng nguồn điều khiển, không đánh lừa.
- **Preset theo model máy** (6/12/30kg): 1 chạm tích sẵn đúng bộ tùy chọn + đặt
  `MACHINE_BATCH_KG` — khách không phải hiểu từng cờ.
- **Đọc từ firmware để KHÔNG lệch** (khi nối thật): HMI đọc capability firmware phơi
  qua register và **cảnh báo nếu cấu hình HMI khác build firmware** — chặn cảnh
  "HMI hiện nút mà máy không có" hoặc ngược lại. Firmware là chuẩn, HMI khớp theo.
- **Trợ lý cài lần đầu (installer wizard)**: đi qua từng nhóm, **giải thích bằng
  hình + câu đời thường** ("Máy có đo áp hút không? → nhìn có cảm biến áp suất trên
  ống khói"), tick dần; không bắt hiểu tên macro.
- **Quyền & an toàn**: chỉ **master/installer** sửa ma trận này (đổi phần cứng là
  việc lắp máy); mọi thay đổi ghi `pushAudit`. Đổi tùy chọn giữa mẻ → chặn/hoãn.
- Hàm mới: `loadMachine/saveMachine` · `openMachineOpts` · `capUiApply()` (ẩn/hiện
  theo cờ) · `capValidateDeps()` · `capSyncFromFirmware()` (đối chiếu khi nối).

> Lưu ý ranh giới: đây là **cấu hình HMI phản ánh phần cứng**, KHÔNG bật/tắt được
> phần cứng thật. Máy có gì là do lắp đặt + build firmware; ma trận này để HMI
> **hiển thị đúng** và (khi nối) **kiểm khớp** với firmware, tránh vênh.
>
> **Quy tắc phân xử xung đột (chốt để khỏi cãi sau)**: **có kết nối firmware →
> firmware là chuẩn, tự động OVERRIDE `otl_machine`** (HMI đọc capability thật từ
> register, đồng bộ vào cấu hình, cảnh báo nếu người dùng từng tick khác). Cấu hình
> `otl_machine` do người dùng tick **chỉ có hiệu lực khi `DataSource = SimSource`**
> (demo/bán hàng, không có máy thật để hỏi). Không bao giờ để tick tay đè lên phần
> cứng thật.

---

## 10. Bảo mật & phân quyền (HIỆN TRẠNG)

> Lưu ý: đây là **lớp tiện lợi PC** đang chạy trong bản sim, **không phải** bảo mật
> cấp thiết bị. Các lỗ hổng của nó + bản **thiết kế lại** (auth về Python, DPAPI,
> per-call check…) xem **§14 (lỗ hổng) và §16 (redesign)**. Mục này chỉ mô tả cái
> hiện có.

- **PIN 4 số** qua `crypto.subtle` **PBKDF2** (salt ngẫu nhiên), lưu hash trong `otl_users2`.
- **Lần đầu**: chưa có user → màn tạo **master** (nhập PIN 2 lần xác nhận).
- **Đăng nhập**: chọn tài khoản + PIN; đủ 4 số tự vào (không cần Enter); 1 tài khoản thì tự chọn.
- **Khoá**: sai 7 lần → chờ 1′/3′/5′ rồi 5′ mỗi lần (`otl_locks`).
- **Vai trò**: `master` thấy tab Tài khoản + Nhật ký; thao tác quan trọng ghi `pushAudit`.
- **Phiên**: biến `session` (RAM, không lưu). Đăng xuất → về màn Login.

---

## 11. Thành phần nhập liệu dùng chung

| Overlay | Dùng cho | API |
|---|---|---|
| `#keyboard` | Nhập chữ/chuỗi (tên, ghi chú, thời gian mm:ss) | `openKb(init)` → Promise; hàng số + phím `/ : · _` |
| `#numpad` | Nhập số cấu hình (min/max/đơn vị) | `openNumpadFor(id)` gắn với `CFG_EDIT` |
| `#picker` | Chọn từ danh sách | `openPick(el, opts)` |
| `#profedit` `#roastmgr` | Modal sửa hồ sơ / quản lý mức rang | — |
| `#targetmgr` | Quản lý + sửa Mục tiêu rang (curve, mốc, khách hàng) | `openTargetMgr()` (§8.3) |
| `#preheatmgr` | Sửa kịch bản Preheat (≤6 ô) | `openPreheatMgr(slot)` (§7.1) |
| `#phasemgr` | Cài phase rang (thanh kéo, preset, RoR/DTR) | `openPhaseMgr()` (§8.4) |
| `#axes` | Cài trục biểu đồ (Auto-fit, preset, nâng cao) | `openAxes()` (§9.1) |
| `#machineopts` | Tùy chọn phần cứng máy (vacuum/drum/loader/VR…) | `openMachineOpts()` (§9.2) |
| `#stats` | Thống kê mẻ rang (phase, AUC, nhận xét) | `openStats(batch)` (§18.7) |
| `#alarmlog` | Nhật ký cảnh báo máy | `openAlarmLog()` (§19) |
| `#profview` | Xem chi tiết curve hồ sơ (kính lúp phóng) | `openProfView(i)` (§18.6) |
| `#compare` | So sánh nhiều mẻ đã rang | `openCompare()` (§18.2) |

---

## 12. Luồng chính (end-to-end)

```
Đăng nhập (PIN)
   │
   ▼
Tổng quan ──(Preheat: LÀM NÓNG → Đã đạt nhiệt)
   │
   ├─► Hồ sơ ──[Nạp & rang]──► loadProfile() ─┐
   │      └─[+ Hồ sơ mới / ✎ Sửa / 🗑 Xoá]     │
   ▼                                           ▼
 Rang:  NOSEL → IDLE → RUNNING → DONE ──► tự lưu ──► Lịch sử
            (BẮT ĐẦU)  (Xả mẻ)                        (xem lại)
```

**Nâng cấp — luồng "1 chạm tới mẻ", ít bước, chặn lỗi ở từng nút:**

```
Đăng nhập (PIN — Python xác thực §16.1)
   │  session theo vai trò → tab & theme mặc định (§4.2/4.4)
   ▼
Tổng quan  ── nút LỚN "Bắt đầu mẻ" (một điểm vào duy nhất)
   │            │
   │            ├─ chưa Preheat  → tự mở Preheat, đạt nhiệt xong quay lại
   │            ├─ chưa chọn hồ sơ → mở Hồ sơ (nhớ hồ sơ dùng gần nhất → gợi trước)
   │            └─ sẵn sàng      → vào thẳng Rang, nền mục tiêu đã hiện (§18.3)
   ▼
Rang:  IDLE ─BẮT ĐẦU─► RUNNING ─Xả mẻ─► DONE
   │     ▲ cổng an toàn      │ bám mục tiêu + toast mốc     │ bảng Thực tế vs
   │     (Preheat/kết nối)   │ ΔBT xanh/amber (§18.3)       │ Mục tiêu (§18.5)
   │     │                   └─ mất kết nối → FAULT (§6)     │ 1 chạm "Lưu thành
   └── FAULT: banner đỏ + giữ số cuối ──────────────────────┘   hồ sơ mục tiêu"
                                                                 tự lưu Lịch sử
```

Nguyên tắc luồng thông minh:

- **Giảm số chạm**: từ Tổng quan tới bắt đầu mẻ tối đa vài chạm; app tự lấp bước
  còn thiếu (preheat/chọn hồ sơ) thay vì bắt người dùng tự đi tìm. Nhớ hồ sơ +
  mức rang gần nhất, gợi sẵn.
- **Chặn lỗi tại từng nút** (giảm rủi ro hỏng mẻ): không cho rang khi chưa đủ nhiệt
  hoặc mất kết nối; xác nhận khi xả quá sớm; mọi giá trị điều khiển clamp trước khi
  xuống máy (§16.7); firmware vẫn là chốt cứng cuối.
- **Không bao giờ mất dấu mẻ**: rời tab khi RUNNING vẫn có thanh mini (BT + thời
  gian + Xả) ở topbar (§4.4); mất điện giữa mẻ → hỏi tiếp tục (§6).
- **Khép vòng học**: DONE → so mục tiêu → nếu mẻ đẹp, 1 chạm biến nó thành hồ sơ
  mục tiêu cho lần sau (§8.1, §18.5) — càng rang càng chuẩn.

---

## 13. Điểm mở rộng (nối firmware thật) — tóm tắt

App hiện **mô phỏng** hoàn toàn (curve, preheat, số liệu). Việc nối máy STM32 thật
là **GĐ3** và đã được thiết kế chi tiết ở §15–16 + §16.9; mục này chỉ là bản đồ:

1. **Cầu dữ liệu**: interface `DataSource` — sim đổi sang `ModbusSource`, **không
   thay** `curveAt`/`roastTick` mà **đổi nguồn** chúng đọc (§6.1, §16.7, §16.9).
2. **Rang**: BT/ET/RoR thực từ register map (`ref-artisan-modbus-map.txt`,
   `ref-sim-interface.md`), qua luồng poll một-chủ-serial (§16.9).
3. **Preheat**: `phTick` **CHỈ đọc + hiển thị** giai đoạn/nhiệt firmware đang chạy;
   **KHÔNG tự đẩy gas** — vòng gas do firmware (§7). Đây là điểm sửa so với bản cũ.
4. **Output**: `stepOut`/`toggleDev` gửi lệnh qua `api.*` → `modbus.py` **clamp 2
   tầng** trước khi ghi register (§16.7). UI không ghi thô.
5. **Schema version + di trú**: đã thiết kế ở §16.2 (SQLite + migration), không còn
   là "migration thủ công".

---

## 14. Thương mại hóa — đánh giá lỗ hổng hiện trạng

> UI đã đạt chuẩn bán được; vấn đề là **ranh giới tin cậy đặt sai chỗ** — mọi thứ
> đáng giá (auth, audit, config) nằm ở tầng JS/localStorage là tầng người dùng
> chạm được. Các mục **§14–19** là thiết kế nâng cấp, chưa code (2026-07-14);
> thứ tự làm thực tế xem **roadmap §2**.

| # | Lỗ hổng | Kịch bản khai thác | Mức |
|---|---|---|---|
| 1 | Tài khoản/PIN trong `localStorage` (leveldb plaintext ở `%LOCALAPPDATA%\OTL Roast Lab HMI\EBWebView\`) | **Xóa thư mục storage → `otl_users2` = null → app về màn "tạo master lần đầu" → chiếm quyền master trong 10 giây** | Nghiêm trọng |
| 2 | Khóa brute-force (`otl_locks`) cũng ở localStorage | Xóa key → thử PIN vô hạn (4 số = 10.000 tổ hợp) | Nghiêm trọng |
| 3 | Xác thực chạy hoàn toàn ở JS client | Sửa HTML (trích từ exe) hoặc sửa localStorage để bypass `loginSubmit` | Cao |
| 4 | Nhật ký `otl_audit2` sửa/xóa tùy ý | Xóa dấu vết thao tác → audit vô giá trị truy vết | Cao |
| 5 | Không license/khóa máy | Copy exe sang máy khác chạy bình thường | Cao (kinh doanh) |
| 6 | PyInstaller onefile trích xuất được (`pyinstxtractor`) | Lộ HTML + bytecode → clone sản phẩm dễ | Trung bình |
| 7 | Không schema version cho `otl_*` | Nâng cấp đổi cấu trúc → hỏng dữ liệu khách | Trung bình |
| 8 | Exe chưa ký số | SmartScreen cảnh báo "unknown publisher" | Trung bình |
| 9 | Nối Modbus: JS gửi lệnh gas trực tiếp qua bridge | Bug UI / storage bị sửa → lệnh gas sai xuống máy | Nghiêm trọng (an toàn) |

---

## 15. Kiến trúc mục tiêu — 3 tầng tin cậy

```
┌────────────────────────────────────────────────────────────┐
│ TẦNG 1 · UI (OTL Roast Lab.html — GIỮ vanilla 1 file)       │
│ Chỉ hiển thị + nhập liệu. KHÔNG giữ bí mật, KHÔNG tự quyết. │
│ localStorage chỉ còn: theme, accent, lang (tùy biến vô hại) │
└──────────────────────┬─────────────────────────────────────┘
                       │ js_api (pywebview) — API whitelist, có validate
┌──────────────────────▼─────────────────────────────────────┐
│ TẦNG 2 · Lõi Python (roast_lab_hmi/ — tách module)          │
│ · auth.py     — verify PIN, lockout, session timeout        │
│ · store.py    — SQLite + schema_version + migration + backup│
│ · audit.py    — nhật ký chuỗi hash (tamper-evident)         │
│ · license.py  — verify license Ed25519 + khóa máy           │
│ · modbus.py   — (GĐ 3) đọc/ghi serial, CLAMP mọi lệnh ghi   │
└──────────────────────┬─────────────────────────────────────┘
                       │ Modbus RTU (serial)
┌──────────────────────▼─────────────────────────────────────┐
│ TẦNG 3 · Firmware STM32 (đã có)                             │
│ Vòng điều khiển + giới hạn cứng gas/nhiệt — chốt an toàn    │
│ cuối. HMI chết thì mẻ rang vẫn an toàn (HMI chỉ giám sát).  │
└────────────────────────────────────────────────────────────┘
```

Cấu trúc thư mục đề xuất (thay `tools/roast_lab_hmi.py` đơn lẻ):

```
tools/roast_lab_hmi/
├── app.py            — entry: tạo cửa sổ, nạp HTML, khởi động core
├── api.py            — lớp Api lộ ra JS: CHỈ hàm whitelist, validate tham số
├── core/
│   ├── store.py      — SQLite (%PROGRAMDATA%\OTL\roastlab.db), migration
│   ├── auth.py       — pbkdf2_hmac, lockout, session
│   ├── audit.py      — chuỗi HMAC append-only
│   ├── license.py    — Ed25519 verify, machine_id, expiry
│   └── machine.py    — MachineGuid + volume serial
└── RoastLabHMI.spec
```

UI vẫn là **một file HTML duy nhất** — chỉ đổi chỗ gọi: `loadUsers()` /
`loadProfiles()` / `pushAudit()`… chuyển từ localStorage sang `pywebview.api.*`
(đều đã gom sẵn thành hàm load/save nên điểm chạm ít, xem §5).

---

## 16. Thiết kế bảo mật chi tiết

### 16.1 Xác thực (sửa lỗ hổng #1 #2 #3)
- PIN verify **ở Python**: `hashlib.pbkdf2_hmac('sha256', pin, salt, ≥200k vòng)`.
  JS chỉ gửi `api.login(user, pin)` → nhận `{ok, role, perms}`. Hash không bao giờ
  xuống UI.
- Bảng `users` nằm trong SQLite ở `%PROGRAMDATA%` (ACL chỉ Administrators ghi),
  kèm **pepper** bọc bằng **DPAPI** (`CryptProtectData`, scope machine) — copy
  file DB sang máy khác không dùng lại được.
- **Installer chạy elevated, runtime chạy user thường** (vá lỗ hổng triển khai):
  app chạy quyền user **không tạo được** `HKLM\SOFTWARE\OTL` hay đặt ACL
  "chỉ Administrators ghi" trên DB. Vậy **bộ cài (installer) chạy elevated MỘT LẦN**
  tạo: registry key khởi tạo, file DB ở `%PROGRAMDATA%`, và ACL cho nó. App runtime
  chỉ **đọc/ghi trong phạm vi đã cấp** (bảng nghiệp vụ ghi được; cờ khởi tạo +
  cấu trúc bảo mật chỉ đọc). Không tính trước là GĐ1 vấp ngay chỗ này.
- **Session giữ SERVER-SIDE ở Python, không tin token từ JS** (sống còn): HTML
  trích/sửa được (§14 #6) → kẻ xấu gọi thẳng `pywebview.api.save_users(...)` bỏ qua
  UI, và nếu token do JS giữ thì HTML độc cũng có token. Vì **chỉ 1 cửa sổ / 1
  người dùng**, Python **tự giữ session hiện tại** (ai đang đăng nhập, role, hạn) —
  **không nhận token nào từ JS**. **Mỗi hàm bridge** kiểm session + role phía Python
  TRƯỚC khi làm; ẩn nút ở UI chỉ là **mỹ phẩm**. Đăng nhập/đăng xuất đổi session
  server-side, không phải biến JS.
- **Chống mất pepper = brick toàn bộ login** (lỗ hổng vận hành): pepper bọc DPAPI
  machine-scope — **re-image máy / profile Windows hỏng → pepper mất → không verify
  được PIN nào** (reset-master chỉ tạo master mới, không cứu hash cũ). Vậy pepper
  phải có **đường escrow**: OTL giữ (hoặc nhúng trong `license.lic` ký số §16.4) một
  **pepper phục hồi** tính từ machine_id; mất DPAPI → nhập license/mã OTL để khôi
  phục pepper, login cũ dùng lại được. Không có đường này thì sự cố Windows = mất
  sạch tài khoản khách.
- **Chống reset-về-master**: trạng thái "đã khởi tạo" ghi cả trong DB **và**
  registry `HKLM\SOFTWARE\OTL\RoastLab`. Mất DB → app vào chế độ **khôi phục có
  mã** (mã reset do OTL cấp, tính từ machine_id), không tự mở màn tạo master.
- Lockout lưu trong DB + RAM: sai 7 lần giữ nguyên bậc chờ 1′/3′/5′ như hiện tại,
  nhưng xóa file không còn gỡ được khóa.
- **Session timeout — nhưng TREO khi RUNNING** (vá xung đột vận hành): tự đăng xuất
  sau N phút không chạm (mặc định 15′, master chỉnh được), NHƯNG **đang rang thì
  không đăng xuất** — nếu không, thợ bị khóa ngoài đúng lúc cần bấm Xả. Quy tắc:
  RUNNING → **treo timeout**; hoặc nhẹ hơn, chỉ khóa thao tác **cấu hình**, còn
  **Xả/Pause luôn bấm được** không cần đăng nhập lại. Hết mẻ (DONE) mới tính lại giờ.
- PIN master nâng lên **6 số**; operator giữ 4 số cho nhanh ở xưởng.

### 16.2 Lưu trữ dữ liệu (sửa #7, nền cho mọi thứ khác)
- Chuyển `otl_profiles / otl_roasts / otl_history / otl_users2 / otl_audit2 /
  otl_cfg2 / otl_locks` → **SQLite**, mỗi nhóm một bảng, có cột
  `schema_version` + hàm migration chạy lúc khởi động.
- **Bền với mất điện đột ngột** (quan trọng — máy rang hay cúp điện): SQLite bật
  **WAL mode** + `PRAGMA synchronous=NORMAL` (cân bằng bền/tốc độ), **checkpoint
  định kỳ**; lúc boot chạy `PRAGMA integrity_check`, **hỏng → tự khôi phục từ
  `.otlbak` gần nhất** + báo cảnh báo. Không có bước này thì một lần cúp điện giữa
  ghi = mất/hỏng dữ liệu khách.
- **Di trú một lần — có giao dịch, idempotent**: bản mới lần đầu chạy, JS đọc
  localStorage cũ đẩy qua `api.migrate(payload)`; migration chạy **trong 1
  transaction** (fail thì rollback, không để nửa vời), **idempotent** (chạy lại
  không nhân đôi), và **sao lưu localStorage ra `.otlbak` TRƯỚC khi xoá**. Khách cũ
  không mất hồ sơ kể cả khi di trú lỗi.
- **Sao lưu**: `api.backup_to_usb()` xuất file `.otlbak` (zip + checksum),
  `api.restore()` nhập lại; **backup tự động xoay vòng** (giữ N bản gần nhất) làm
  nguồn khôi phục cho integrity_check ở trên. Lịch sử mẻ xuất thêm **CSV tương thích
  Artisan**.
- localStorage chỉ còn theme/accent/lang — mất cũng vô hại.

### 16.3 Nhật ký chống sửa (sửa #4)
- `audit.py` ghi append-only: mỗi bản ghi kèm
  `hmac = HMAC(key_dpapi, hmac_trước + nội_dung)` → sửa/xóa giữa chừng là đứt
  chuỗi, tab Nhật ký hiện cảnh báo "chuỗi không toàn vẹn từ dòng N".
- **Số thứ tự đơn điệu (seq) song song timestamp**: đồng hồ hệ thống có thể sai/lùi
  (§16.4) → giờ hiển thị sai. Mỗi bản ghi audit/alarm mang thêm **`seq` tăng dần
  không lặp** (nguồn sự thật về *thứ tự*); `ts` chỉ để hiển thị. Chuỗi hash tính
  theo seq nên đúng thứ tự dù đồng hồ lộn xộn. Áp cho cả `alarms` (§19.3).
- Xuất nhật ký ký kèm checksum để gửi về OTL khi bảo hành/tranh chấp.

### 16.4 License & khóa máy (sửa #5)
- File `license.lic` = JSON `{customer, machine_id, model, expiry, features}`
  + chữ ký **Ed25519**; app nhúng **public key**, OTL giữ private key để phát hành.
- `machine_id` = SHA256(MachineGuid + volume serial) — hiện sẵn trên màn About
  để khách đọc qua điện thoại khi mua, OTL ký license offline gửi lại (không
  cần internet, hợp môi trường xưởng).
- Chống lùi đồng hồ: lưu `last_seen_time` (DPAPI), thời gian hệ thống nhỏ hơn →
  cảnh báo + đếm hạn theo mốc đã thấy.
- Hết hạn/không license → **chế độ xem** (giám sát được, không điều khiển) thay
  vì khóa trắng — an toàn hơn cho máy đang có mẻ.

### 16.5 Đóng gói & phân phối (sửa #6 #8)
- **Ký số Authenticode** (chứng thư OV) cho exe → hết cảnh báo SmartScreen.
- Nâng cấp có phiên bản + gói update offline `.otlpkg` ký Ed25519, cài từ USB
  (khách không có internet); app kiểm chữ ký trước khi thay exe.
- Chống trích xuất: chấp nhận HTML không phải bí mật; riêng `license.py` +
  `auth.py` biên dịch **Nuitka/Cython** thành `.pyd` để không decompile trực
  tiếp được. Không đầu tư DRM nặng — mục tiêu là chặn sao chép tiện tay, không
  chặn reverse chuyên nghiệp.

### 16.6 Kiosk hardening
- DevTools đã tắt (pywebview `debug=False` mặc định) — giữ nguyên khi build.
- JS chặn `contextmenu`, chọn text, kéo-thả file vào cửa sổ.
- Thoát fullscreen/đóng app yêu cầu PIN master (hook `window.events.closing`).
- Tự khởi động cùng Windows (Task Scheduler) + **watchdog**: process giám sát
  khởi động lại app nếu crash, ghi crash log để chẩn đoán từ xa.
- Nút "Xuất gói hỗ trợ": zip log + config (đã ẩn bí mật) để khách gửi về OTL.

### 16.7 An toàn lệnh điều khiển khi nối máy thật (sửa #9 — GĐ 3)
- UI **không bao giờ** gửi giá trị thô: `api.set_burner(x)` → `modbus.py` clamp
  theo bảng giới hạn từng model máy (đọc từ DB, không từ UI) rồi mới ghi register.
- Firmware giữ giới hạn cứng riêng (đã có) — hai tầng độc lập.
- **Heartbeat**: HMI ghi nhịp vào 1 register; firmware không thấy nhịp N giây →
  tự giữ chế độ an toàn. HMI treo không được phép làm hỏng mẻ.
- Tách nguồn dữ liệu thành interface `DataSource` (SimSource / ModbusSource) —
  chọn runtime, demo bán hàng và máy thật dùng chung một exe.

### 16.8 Kiểm thử (bắt buộc cho tầng chạm gas)

Sản phẩm thương mại điều khiển gas mà không có test là rủi ro. **Không cần test UI**
(HTML tự kiểm bằng mắt/Playwright khi cần), nhưng **lõi Python phải có unit test**
ở đúng ba chỗ bug = nguy hiểm:

- **`modbus.py` — bảng clamp** (ưu tiên cao nhất): test mọi giá trị biên/ngoài dải
  cho từng model máy → đảm bảo **không bao giờ ghi register vượt trần gas/nhiệt**.
  Đây là chỗ bug biến thành lệnh gas sai xuống máy.
- **`auth.py`**: PBKDF2 verify đúng/sai, lockout đúng bậc, session token hết hạn,
  per-call role check từ chối đúng.
- **`license.py`**: chữ ký Ed25519 hợp lệ/giả, hết hạn, chống lùi đồng hồ, machine_id.
- Chạy trong CI cùng build tái lập (§2). Test là **điều kiện xong GĐ1**, không phải
  "làm nếu có thời gian".

### 16.9 Mô hình luồng, serial & giao thức (backend runtime)

Vá các lỗ hổng runtime mà thiết kế "cầu JS↔Python" chưa nói.

- **`js_api` không được làm treo UI** (async): pywebview gọi API **đồng bộ** →
  SQLite write / Modbus read dài sẽ **đơ giao diện**. Quy tắc: hàm API **trả nhanh**
  (nhận lệnh, trả "đã nhận"); việc nặng chạy ở **luồng nền**, xong đẩy kết quả về JS
  qua `window.evaluate_js`/callback. UI không bao giờ chờ I/O.
- **Một chủ sở hữu serial + hàng đợi** (Modbus là tài nguyên đơn): heartbeat + đọc
  data + ghi lệnh **tranh chấp một dây**. `modbus.py` chạy **một luồng poll duy
  nhất** sở hữu cổng: vòng lặp đọc BT/ET/RoR/trạng thái theo **nhịp cố định**, chèn
  lệnh ghi (clamp §16.7) + heartbeat vào **hàng đợi** của luồng đó. Không nơi nào
  khác chạm serial.
- **Định nhịp poll theo băng thông**: ở 38400 baud, mỗi giao dịch Modbus ~vài ms →
  chốt **poll ~4–10 Hz** cho số live (UI cập nhật 1s vẫn dư), heartbeat ~1–2s. Đo
  thật, đừng để hàng đợi dồn.
- **Version handshake HMI↔firmware** (chống đọc nhầm thanh ghi): lúc kết nối, HMI
  đọc **register "phiên bản map/giao thức"** của firmware. Lệch phiên bản HMI hỗ trợ
  → **từ chối điều khiển + báo "cần cập nhật HMI/firmware"**, không đoán bừa địa chỉ.
  Firmware đổi register map phải tăng version này. (Firmware là chuẩn — §9.2.)
- **Khôi phục khi HMI/Python restart giữa mẻ**: watchdog (§16.6) restart process →
  heartbeat gián đoạn → firmware **tự về an toàn** (đúng fail-safe §1). HMI bật lại
  đọc trạng thái thật từ firmware + checkpoint (§6) để **nối lại hiển thị**, không
  tự ý phát lệnh. Vòng điều khiển luôn ở firmware nên mẻ không hỏng vì HMI restart.

---

## 17. Lộ trình + Cut-line MVP → đã tách ra `plan-hmi-roadmap.md`

> **Lộ trình 3 giai đoạn (sản xuất-first), "những gì cố tình không làm", và
> cut-line MVP GĐ1 (in/out)** nay nằm ở **`docs/plan/plan-hmi-roadmap.md`**.
>
> Tóm tắt để khỏi lật: **GĐ1 = chạy máy thật hằng ngày** (an toàn + dữ liệu bền +
> không mất mẻ + uptime 16h); **GĐ2 = bán cho người khác** (auth/DPAPI/license/ký
> số); **GĐ3 = mở rộng** (stats/so mẻ/alarm push/đa theme-ngôn ngữ, theo yêu cầu
> thật). Các mục ⭐ trong doc mặc định **OUT khỏi GĐ1** — chi tiết ở roadmap.
>
> Ghi chú: nhãn "GĐ 3 — nối máy thật" cũ rải rác trong §13/§16.7 nay hiểu là **GĐ1**.

---

## 18. Tính năng so sánh mẻ rang (thiết kế, chưa code)

> Tính năng bán hàng chủ lực: thợ rang kiểm soát **độ lặp lại giữa các mẻ** —
> đúng bài toán QC của xưởng ca cao/cà phê. Gồm 2 chế độ dùng.

### 18.1 Điều kiện tiên quyết — Lịch sử phải lưu CURVE

Hiện `otl_history` chỉ lưu tóm tắt `{code,name,color,time,temp,dev,date}` —
**không so sánh đường cong được**. Cần mở rộng model dữ liệu:

```
batches        — bản ghi mẻ (như otl_history) + mốc giây TP/DE/FCs/DROP
batch_curves   — mẫu curve theo mẻ: (code, t_sec, bt, et, ror, burner, air, drum)
                 lấy mẫu 2 s/điểm (642 s ≈ 320 điểm/mẻ — đủ mịn để vẽ)
```

- **Ghi lúc nào**: `roastTick` đang chạy mỗi 1 s → cứ 2 nhịp đẩy 1 điểm vào
  buffer RAM; `finishRoast()` ghi trọn gói vào storage cùng bản ghi mẻ.
- **Dung lượng & giới hạn (chốt số)**: 320 điểm × 6 giá trị/mẻ ≈ 2k số/mẻ.
  **GĐ localStorage: giữ curve của 20 mẻ gần nhất** (mẻ cũ rụng curve, giữ tóm
  tắt) — an toàn với giới hạn ~5MB của localStorage. **GĐ SQLite (§16.2): bỏ giới
  hạn 20**, giữ theo chính sách retention dưới. (Con số 20 dùng nhất quán ở §18.4.)
- **Retention/archival trên panel disk hữu hạn** (SQLite): `batch_curves` tăng
  không giới hạn là rủi ro. Chính sách: **giữ curve N mẻ gần nhất** (mặc định ~500,
  master chỉnh) + tóm tắt mẻ giữ lâu hơn; mẻ quá cũ **nén/archival ra `.otlbak`**
  rồi rụng curve khỏi DB nóng. Cảnh báo khi disk sắp đầy. Xuất CSV Artisan dùng lại
  đúng dữ liệu này.
- **Mốc mẻ**: lưu thêm giây thật của TP/DE/FCs/DROP vào bản ghi mẻ (hiện `MILES[]`
  chỉ là hằng của hồ sơ mẫu) — cần cho căn pha và bảng chỉ số.

### 18.2 Chế độ A — So sánh sau rang (tab Lịch sử)

```
Lịch sử: [☑] #B-0212  Colombia Huila   10:42 …
         [☑] #B-0211  Colombia Huila   10:55 …
         [ ] #B-0210  Sumatra No.4     11:20 …
                     └──► nút [So sánh (2)] → overlay #compare
```

- Mỗi dòng lịch sử thêm ô chọn; chọn **2–4 mẻ** → nút "So sánh" hiện số lượng.
- Overlay `#compare` (fullscreen, cùng khuôn `#profedit`):
  - **Biểu đồ overlay**: BT các mẻ chồng lên nhau, mỗi mẻ một màu lấy từ
    `color` của mẻ; ET/RoR bật tắt bằng chip legend. Tái dùng hạ tầng
    `drawChart` (trục, DPR, scale) — tách phần vẽ series thành hàm nhận mảng
    điểm để cả hai màn dùng chung, như cách `curveAt` dùng chung hiện nay.
  - **Căn trục thời gian**: mặc định t=0 tại CHARGE; toggle "Căn theo FCs"
    (dời mỗi curve sao cho FCs trùng nhau) — so pha phát triển giữa các mẻ.
  - **Bảng chỉ số cạnh nhau** (mỗi mẻ 1 cột): tổng thời gian · nhiệt xả · dev% ·
    thời lượng 3 pha Sấy/Maillard/Dev · RoR trung bình từng pha · mốc
    TP/DE/FCs/DROP. Ô lệch quá ngưỡng so với mẻ đầu (cột chuẩn) tô **amber**
    — nhìn 1 giây biết mẻ nào trôi.
- Hàm mới: `cmpSel{}` (bộ mẻ đã chọn) · `openCompare()` · `drawCompare()` ·
  `cmpAlign` (charge/fcs) · `renderCmpTable()`.

### 18.3 Background profile — mẻ mục tiêu chính là hồ sơ đã chọn ⭐

> Đây là **mô hình trung tâm** (giống *background profile* của Artisan — xem ảnh
> mẫu). Không phải "chọn thêm mẻ tham chiếu": **hồ sơ đã nạp trỏ tới một Mục tiêu
> rang** (§8.3), curve của mục tiêu đó hiện mờ dưới nền ngay từ lúc nạp và xuyên
> suốt mẻ rang.

Luồng:
1. **Chọn hồ sơ ở tab Hồ sơ → `loadProfile()`** đọc `profile.targetId` → nạp
   **curve mục tiêu** `target.curve[]` (§8.3) vào `R.target[]`. Ngay ở phase IDLE,
   `drawChart` đã vẽ curve mục tiêu **mờ + nét đứt** làm nền — thợ rang thấy trước
   "mình sẽ rang theo đường nào".
2. **RUNNING**: curve BT/ET thực vẽ **đậm đè lên** nền mục tiêu (đúng như ảnh:
   nền xám/đỏ nhạt = mục tiêu, đường đậm = mẻ đang chạy). Mốc mục tiêu
   TP/DE/FCs/DROP hiện sẵn trên nền để biết còn bao xa tới mốc kế.
3. Thẻ **ΔBT** cạnh số live: `BT hiện tại − BT mục tiêu tại cùng giây`, tô xanh
   trong ±2°C, amber ngoài — rang **đuổi theo** đường mục tiêu bằng mắt.
   (Cùng triết lý `rorBT_pro` bên firmware — HMI làm bản trực quan.)
4. **DONE**: bảng đối chiếu §18.5 so thẳng mẻ vừa xong với chính curve mục tiêu
   này — không phải chọn lại nguồn nào nữa.

- State: thêm `R.target[]` (mảng điểm mục tiêu, sao từ `target.curve` của mục tiêu
  hồ sơ trỏ tới) nạp trong `loadProfile()`, giữ đến hết mẻ. Không đụng state
  machine (phase vẫn NOSEL→IDLE→RUNNING→DONE như §6); chỉ `drawChart` thêm lớp nền.
- Vì mỗi hồ sơ luôn trỏ một mục tiêu, **mọi mẻ đều có nền mục tiêu** mà không cần
  thao tác thêm — đây là lý do gộp §18.3 cũ (chọn mẻ tham chiếu) vào đây.

### 18.4 Phân kỳ & giới hạn

| Bước | Nội dung |
|---|---|
| Ngay được (sim) | Ghi curve từ `roastTick`+`curveAt` vào localStorage (giới hạn **20 mẻ có curve**, mẻ cũ rụng curve giữ tóm tắt); chế độ A + B chạy trên dữ liệu sim — demo bán hàng dùng được liền |
| GĐ 1 (SQLite) | Chuyển `batch_curves` sang SQLite, bỏ giới hạn 20 mẻ, migration kèm §16.2 |
| GĐ 3 (máy thật) | Curve ghi từ BT/ET thực qua `DataSource` — chế độ B thành công cụ vận hành thật |

- Không cần quyền master — so sánh là thao tác xem, mọi vai trò dùng được.
- i18n: thêm nhóm key `cmp.*` (vi/en) như các nhóm hiện có.
- Không làm ở bước đầu: so sánh >4 mẻ, thống kê tổng hợp theo tháng, export
  ảnh biểu đồ — để sau khi khách dùng thật có phản hồi.

### 18.5 Bảng tổng kết Thực tế vs Mục tiêu (màn DONE — ưu tiên làm trước)

Đây là bảng hiện **ngay khi xả mẻ**: đối chiếu mẻ vừa xong với **curve Mục tiêu
rang** mà hồ sơ đang trỏ (`R.target[]` ở §18.3, §8.3) — cùng một đường mờ đã chạy
nền suốt mẻ, nên DONE chỉ là "chốt sổ" so sánh đó thành bảng số, không chọn lại
nguồn nào.

Bổ sung vào banner DONE (§6.2, `.roast-done`), ngay dưới 3 chỉ số hiện có:

```
             THỰC TẾ      MỤC TIÊU     LỆCH
Tổng thời gian  10:48       10:42       +0:06   ✓
Nhiệt xả        212.4°C     211°C       +1.4    ✓
Dev %           21.8%       20.0%       +1.8    ⚠
TP (Turn)       1:32        1:30        +0:02   ✓
FCs             8:40        8:55        −0:15   ⚠
Sấy / Maillard  6:12 / 2:28 6:12 / 2:43 …       ✓
```

- **Cột MỤC TIÊU** lấy mốc từ `R.target[]` (curve hồ sơ); ô LỆCH tô **xanh**
  trong ngưỡng, **amber** ngoài ngưỡng (ngưỡng để trong `CFG`, mặc định ±0:10
  thời gian, ±2°C nhiệt, ±2% dev).
- Kèm **biểu đồ overlay nhỏ** trong banner: curve BT thực (đậm) chồng lên curve
  mục tiêu (mờ, nét đứt) — chính là ảnh chụp lại của nền đã chạy suốt mẻ (§18.3),
  tái dùng lớp vẽ nền của `drawChart`.
- Dòng kết luận 1 câu: "Đạt mục tiêu" / "Lệch ở: Dev, FCs" (liệt kê ô amber).
- Hàm mới: `renderDoneCompare()` gọi trong `finishRoast()` sau khi chốt bản ghi;
  mục tiêu từ `R.target[]`, thực tế từ chính mẻ vừa lưu.

**Điều kiện tiên quyết — Mục tiêu rang phải có curve + mốc** (§8.3). Hồ sơ chỉ
trỏ `targetId`; curve/mốc mục tiêu nằm ở thư viện Mục tiêu rang, lấy được theo 3
cách ở §8.3 (từ mẻ thật / nhân bản / nội suy từ mốc nhập tay).

- **Cột MỤC TIÊU** đọc `target.miles` + `target.devPct` + `target.dropTemp` của
  mục tiêu hồ sơ trỏ tới.
- Trước mắt (sim): mục tiêu chưa có `curve` → sinh tạm từ `curveAt`/`MILES[]` để
  nền và bảng vẫn chạy — demo dùng được ngay, không chặn.
- **Đánh dấu CẢ BẢNG "so với mục tiêu dự kiến" khi target chưa có curve thật** (vá
  niềm tin): số LỆCH ✓/⚠ **trông có thẩm quyền hơn bản chất** nếu mục tiêu chỉ là
  nội suy. Vậy khi `target.curve` là sinh tạm (chưa lưu từ mẻ thật), header bảng ghi
  rõ **"Mục tiêu (dự kiến)"** + đổi tông ✓/⚠ sang trung tính — không chỉ dán nhãn ở
  chart (§18.6) mà ở cả bảng số. Có curve thật rồi mới hiện ✓/⚠ đầy đủ thẩm quyền.
- Khi thêm auto-replay profile (§8.1 ghi chú cải thiện), `target.curve` dùng chung
  luôn cho điều khiển bám mục tiêu ở AUTO — một nguồn, hai công dụng.
- Chỉ số **thực tế** lấy từ mẻ vừa lưu: mốc thật đã ghi ở §18.1 (giây TP/DE/FCs/
  DROP), dev% và nhiệt xả `finishRoast()` đã tính sẵn.

Ưu tiên: **làm §8.3 + 18.3 + 18.5 trước §18.2** — thư viện mục tiêu + nền + bảng
DONE là giá trị lõi (mọi mẻ đều thấy); so-nhiều-mẻ (§18.2) làm sau.

### 18.6 Xem chi tiết hồ sơ — kính lúp phóng curve

Ở tab **Hồ sơ**, mỗi thẻ hồ sơ hiện chỉ show metadata (tên/mức rang/nhiệt/thời
gian). Vì hồ sơ trỏ tới Mục tiêu rang có curve (§8.3), thêm **nút kính lúp** trên
mỗi thẻ → bấm **phóng hiệu ứng** (scale-up từ vị trí thẻ) ra overlay chi tiết
`#profview`, đúng bố cục ảnh mẫu "OTL Roaster Profile" (vẽ curve của mục tiêu hồ
sơ trỏ tới). Overlay `#targetmgr` (§8.3) dùng lại đúng bố cục này cho việc sửa.

- **Biểu đồ đầy đủ**: BT (đậm) · ET · RoR (nét đứt) · Air · Burner, legend bật/tắt
  từng series. Trục nhiệt trái / RoR phải / thời gian dưới (tính từ CHARGE).
- **Dải pha nền**: Dry / Maillard / Dev tô 3 màu (xanh lá / hổ phách / hồng),
  mỗi dải ghi thời lượng + % (vd `Dry · 9:04 · 50.3%`).
- **Nhãn mốc trên curve**: CHARGE / TP / DE / FCs / DROP, mỗi nhãn kèm thời gian
  + nhiệt (vd `TP 1:32 · 84°C`).
- **Panel dưới**: cột **MILESTONES** (liệt kê 5 mốc: nhiệt + giờ) và
  **PHASE BREAKDOWN** (3 thẻ Dry/Maillard/Dev với % to + thời lượng).

- Tái dùng `drawChart` nhưng vẽ từ `target.curve` (không phải `curveAt` sim) —
  tách phần vẽ series thành hàm nhận mảng điểm để chart chính, nền mục tiêu
  (§18.3), overlay so sánh (§18.2) và profview dùng **chung một** hàm vẽ.
- Hiệu ứng phóng: CSS `transform: scale` + `transform-origin` tại tâm thẻ được
  bấm, `transition` ~200ms (cùng hệ overlay `#profedit` hiện có, xem §11).
- Chỉ xem — không sửa ở đây; nút "Sửa hồ sơ" mở `#profedit`, "Sửa mục tiêu" mở
  `#targetmgr` (§8.3) nếu cần.
- Hàm mới: `openProfView(i)` · `drawProfCurve()` · `renderProfMilestones()`.
- Mục tiêu chưa có `curve` (chưa lưu từ mẻ thật): sinh tạm từ mốc để vẫn xem được,
  kèm nhãn "curve dự kiến" cho khỏi nhầm với đường đã rang thật.

### 18.7 Thống kê mẻ rang (Statistics) ⭐

Tương đương hộp *Statistics* của Artisan (phase stats + AUC) nhưng **thân thiện
hơn**: giải thích thuật ngữ bằng tiếng Việt, **tự nhận xét**, so thẳng với mục
tiêu. Mở từ nút **"Thống kê"** ở màn DONE hoặc mỗi mẻ trong Lịch sử (overlay
`#stats`). Tính từ `batch_curves` (§18.1) + `phaseScheme` (§8.4).

**1. Bảng pha** (map Time/Bar/ΔC/C-min của Artisan) — mỗi pha theo `phaseScheme`:

| Pha | Thời lượng | % | ΔNhiệt (°C tăng) | RoR TB (°C/phút) |
|---|---|---|---|---|
| Sấy | 6:12 | 50.3% | 84→160 (+76) | 12.3 |
| Maillard | 4:38 | 25.7% | 160→195 (+35) | 7.6 |
| Phát triển | 4:20 | 24.0% | 195→215 (+20) | 4.6 |

- Kèm **thanh ngang màu** (Bar) tỉ lệ 3 pha nhìn phát hiểu; cột lệch so mục tiêu
  (§18.5) tô amber.

**2. Chỉ số tổng**: tổng thời gian · nhiệt xả · **DTR%** · RoR đỉnh/trung bình ·
phát hiện **"flick"/"crash"** (RoR vọt/sụt bất thường) kèm mốc thời gian.

**3. Mốc**: nhiệt + thời gian + RoR tại mỗi mốc CHARGE/TP/DE/FCs/DROP.

**4. AUC — diện tích dưới đường** (chỉ số "năng lượng nhiệt", giải thích rõ):

- **AUC là gì**: diện tích giữa đường BT và một **mức nền** (Base, vd 100°C), tính
  **từ một mốc** (From: TP/CHARGE/DE…) tới **đích** (Target). Đại diện **tổng nhiệt
  nạp vào mẻ** — hai mẻ cùng AUC thường **giống vị** → dùng để **rang lặp lại đều**.
- Cài (mặc định hợp lý sẵn, mỗi tuỳ chọn có **tooltip giải thích**, không bắt hiểu
  jargon): `From` (mốc bắt đầu) · `Base` (nhiệt nền) · `Target` · From Event ·
  hiện **vùng tô trên biểu đồ** (Show Area) để thấy AUC bằng mắt.
- **So AUC với mục tiêu / mẻ trước**: lệch bao nhiêu %, tô xanh/amber.

**5. Nhận xét tự động (điểm thông minh)** — dịch số thành câu người đọc hiểu:

> "Pha phát triển 24% — hơi dài, cà phê dễ mất hương trái. RoR crash nhẹ ở phút 8
> (12→6°C/phút) rồi hồi. AUC 1180 — cao hơn mẻ chuẩn 6%, mẻ này đậm hơn."

- Sinh từ luật đơn giản trên chỉ số (DTR ngoài dải, RoR crash/flick, AUC lệch,
  pha lệch mục tiêu) — không phải AI, chạy offline, giải thích được.
- **Cảnh giác: nhận xét trông như lời khuyên có thẩm quyền về gas** — một luật sai
  làm thợ chỉnh gas sai. Vậy: (1) **validate ngưỡng luật trên dữ liệu rang thật**
  trước khi bật, không chế số bừa; (2) văn phong **"gợi ý cân nhắc"**, không mệnh
  lệnh; (3) hiện **cơ sở của nhận xét** (số nào vượt ngưỡng nào) để thợ tự phán.
  Mỗi câu là **cụm chuỗi i18n** (7 slot) → thêm lý do **GĐ1 chỉ vi/en** (§4.3, roadmap §2).

**Thân thiện & dễ xài:**

- **Xem theo tầng**: mở ra là **thẻ tóm tắt + nhận xét** trước (đủ cho thợ rang);
  ai cần sâu bấm "Chi tiết" mới hiện bảng pha/AUC/mốc đầy đủ — không dội số.
- **Bật/tắt hạng mục** (như Display của Artisan) nhưng **nhớ theo tài khoản**:
  người xem đơn giản ẩn AUC, kỹ sư bật hết.
- **Vẽ trực quan trên chart**: chọn AUC → tô vùng; chọn pha → sáng đoạn tương ứng.
- **Xuất**: 1 chạm ra CSV/`.otlbak` (§8) hoặc ảnh tóm tắt để gửi khách.
- Hàm mới: `openStats(batch)` · `calcPhaseStats()` · `calcAUC(from,base,target)` ·
  `detectFlickCrash()` · `statsInsights()` (nhận xét) · `drawStatsOverlay()`.

---

## 19. Cảnh báo máy rang (Alarm) ⭐

Nguồn sự thật là **firmware**: `MachineStatus.h` phát ~380 mã trạng thái qua thanh
ghi **`STT_W`**, đã lọc **whitelist người vận hành** (`sttIsOperatorVisible`), đẩy
**1 mã/giây** (hàng đợi 10, chống dội `sttLastSent`). HMI **đọc `STT_W`** → tra
**danh mục cảnh báo** → hiển thị thân thiện. HMI **không tự bịa** cảnh báo an toàn;
chỉ diễn giải mã firmware (đúng nguyên tắc phản chiếu §7, an toàn phân tầng §1).

### 19.1 Danh mục cảnh báo (alarm catalog)

Map mỗi mã STT → `{ mức độ, tiêu đề dễ hiểu, nguyên nhân, nên làm gì, mã kỹ thuật }`.
**3 mức** (bám ngữ nghĩa MachineStatus.h):

| Mức | Màu | Mã tiêu biểu (MachineStatus.h) | Hành vi |
|---|---|---|---|
| **NGUY HIỂM** | Đỏ | 401–413 (báo cháy, temp runaway, gas fault, sensor fault, ignition fail, RoR>500), 263/264 (BT>250/ET>350 đã tắt lửa) | Cắt ngang, **chiếm màn**, buzzer + đẩy điện thoại, buộc **xác nhận** |
| **CẢNH BÁO** | Amber | 48/49/50 (invariant/mất lửa/cảm biến nhảy), 267 (BT-ET lệch), 330 (RoR crash), 281–297 (Modbus lỗi), 303/306/309/312/315/318 (startup FAIL), 232/411 (loader) | Banner ưu tiên cao (§4.4), không cắt mẻ, ghi lịch sử |
| **THÔNG TIN** | Xanh | sự kiện thường (mốc rang 81–95, SD, preheat done…) | Toast nhẹ, tự tắt |

- Mỗi mã kèm **câu tiếng Việt đời thường + "nên làm gì"** (playbook). Ví dụ:
  - `410 IGNITION_FAIL` → "**Không mồi được lửa** (thử 3 lần). Kiểm tra: còn gas
    không, van gas mở chưa, đầu đánh lửa sạch chưa." + nút "Thử lại".
  - `330 ROR_CRASH_WARN` → "**Tốc độ tăng nhiệt tụt mạnh** — mẻ dễ bị 'baked'.
    Cân nhắc tăng nhẹ gas." (gắn ngữ cảnh: đang phút 8, pha Maillard).
  - `288+ Modbus CRC/timeout` → gộp thành "**Nhiễu đường truyền cảm biến**, kiểm
    tra cáp RS485" (không hiện từng mã kỹ thuật).

### 19.2 Thông minh & dễ hiểu

- **Ngôn ngữ đời thường + icon + màu**, KHÔNG hiện mã số trần; mã STT ẩn trong
  "Chi tiết kỹ thuật" cho thợ kỹ thuật/bảo hành. Đa ngôn ngữ theo §4.3.
- **Gom nhóm & chống dội**: cùng cảnh báo lặp → **1 dòng + đếm số lần** ("×4"),
  không spam. Nhiều lỗi Modbus rời rạc gộp 1 thẻ "mất kết nối".
- **Ngữ cảnh mẻ**: mỗi cảnh báo ghi kèm **đang rang mẻ nào, phút thứ mấy, pha nào**
  — đọc lại biết chuyện gì đã xảy ra.
- **Xác nhận (acknowledge)**: lỗi NGUY HIỂM buộc bấm "Đã hiểu / Đã xử lý"; ghi
  **ai xác nhận + lúc nào** (`pushAudit`, §16.3). Còi kêu tới khi xác nhận.
- **Playbook gợi ý xử lý**: mỗi mã có các bước khắc phục + link hướng dẫn; nút tắt
  nhanh nguồn nguy (nếu firmware cho phép) hoặc "Xuất gói hỗ trợ" (§16.6) gửi OTL.
- **Ưu tiên rõ**: NGUY HIỂM > CẢNH BÁO > THÔNG TIN; nhiều cảnh báo xếp theo mức.

### 19.3 Lịch sử cảnh báo

- Lưu `otl_alarms` (bảng SQLite §8): `{ts, code, level, batchCode, phase, count,
  ackBy, ackAt, resolved}`. Mới nhất đầu.
- Overlay **`#alarmlog`**: lọc theo **mức / ngày / mẻ / đã xử lý**; tìm; badge số
  cảnh báo chưa xác nhận ở topbar.
- **Toàn vẹn**: cảnh báo NGUY HIỂM nối vào **audit hash-chain** (§16.3) — không
  xoá/sửa được, dùng cho bảo hành & truy vết sự cố.
- **Thống kê sức khoẻ máy**: đếm cảnh báo theo loại/tháng → biết bộ phận nào hay
  lỗi (vd hay mất lửa → xem lại đầu đốt). Xuất `.otlbak`/CSV (§8).

### 19.4 Thông báo đẩy (push)

- **Tại máy**: buzzer + đèn báo (qua firmware) cho NGUY HIỂM; banner + âm HMI.
- **Ra ngoài** (khi có mạng): đẩy lỗi NGUY HIỂM tới **điện thoại chủ xưởng** —
  Telegram / Zalo / email / webhook (cấu hình ở Cài đặt). Chủ biết máy có sự cố dù
  không đứng cạnh.
- **Hợp môi trường xưởng không mạng**: đẩy là **tuỳ chọn**; offline thì **xếp hàng
  gửi lại** khi có mạng, không chặn vận hành. Bí mật kênh (token) bọc DPAPI (§16.1).
- **Chống làm phiền**: chỉ đẩy mức đã chọn (mặc định chỉ NGUY HIỂM), gộp/nhịp tối
  thiểu để không dội tin nhắn.

### 19.5 Kết nối phần còn lại

- **State `FAULT`** (§6): cảnh báo NGUY HIỂM đẩy màn Rang vào FAULT, giữ số cuối,
  banner đỏ + lý do.
- **Mất `STT_W`/serial** N giây (heartbeat §16.7) → tự sinh cảnh báo "mất kết nối
  máy" phía HMI (đây là ngoại lệ HMI tự phát, vì firmware không nói được khi đứt).
- Hàm mới: `ALARM.ingest(code)` (đọc STT_W) · `alarmCatalog[code]` · `pushAlarm` ·
  `ackAlarm(id)` · `openAlarmLog` · `alarmNotify(level)` (đẩy ngoài) ·
  `alarmHealthStats()`.

---

## Thuật ngữ (glossary)

Doc dùng nhiều thuật ngữ rang cà phê/ca cao và kỹ thuật — tra nhanh ở đây.

| Viết tắt | Nghĩa |
|---|---|
| **BT** | Bean Temp — nhiệt độ hạt (đầu dò trong khối hạt). Đường chính khi rang. |
| **ET** | Environment Temp — nhiệt môi trường/khí trong trống. |
| **RoR** | Rate of Rise — tốc độ tăng nhiệt BT (°C/phút). Lý tưởng giảm mượt. |
| **CHARGE** | Lúc đổ hạt vào trống (mốc t=0). |
| **TP** | Turning Point — điểm BT chạm đáy rồi tăng trở lại (~1–1.5′). |
| **DE / Dry End** | Kết thúc pha sấy, hạt ngả vàng (~150–160°C). |
| **FCs / FCe** | First Crack start / end — nổ lần một bắt đầu/kết thúc (~196–205°C BT). |
| **SCs** | Second Crack — nổ lần hai (rang đậm). |
| **DROP** | Xả mẻ ra làm nguội (mốc cuối). |
| **Maillard** | Pha phản ứng nâu hoá (Dry End→FCs), tạo tiền chất hương. |
| **DEV / Development** | Pha phát triển (FCs→DROP), định vị hương cuối. |
| **DTR** | Development Time Ratio = thời gian phát triển ÷ tổng. Chỉ số then chốt. |
| **AUC** | Area Under Curve — diện tích BT trên mức nền; đại diện tổng nhiệt nạp (§18.7). |
| **flick / crash** | RoR vọt lên / sụt mạnh bất thường — sinh lỗi vị. |
| **ACI** | Ngõ analog trên biến tần (đọc cảm biến vacuum) — xem `Config.h`. |
| **VR** | Variable Resistor — biến trở tay (chỉnh gas/gió/drum vật lý), §9.2. |
| **STT_W** | Thanh ghi HMI firmware ghi mã trạng thái (`MachineStatus.h`, §19). |
| **DPAPI** | Windows Data Protection API — bọc bí mật theo máy (§16.1). |
| **DataSource** | Interface nguồn dữ liệu: SimSource (demo) / ModbusSource (máy thật). |

---

## Liên quan
- `tools/roast_lab_hmi.py` — vỏ pywebview + cấu hình cửa sổ/storage.
- `tools/RoastLabHMI.spec` — cấu hình đóng gói PyInstaller.
- `include/MachineStatus.h` — ~380 mã trạng thái firmware qua `STT_W`, nguồn cho Alarm (§19).
- `include/Config.h` — cờ tùy chọn phần cứng (`MACHINE_HAS_*`, `MACHINE_VR_*`), nguồn cho §9.2.
- `docs/ref/ref-sim-interface.md`, `ref-artisan-modbus-map.txt` — giao tiếp sim/Modbus (khi nối thật).
