# Program.h — bộ não firmware (19 hàm)

Nguồn: `include/Program.h` (~2467 dòng). File điều khiển toàn bộ logic rang: đọc/ghi SD, gas AUTO, auto-loader tự học, và máy trạng thái mẻ rang.

## Tổng quan 6 nhóm

| # | Nhóm | Hàm |
|---|------|-----|
| ① | Nhịp thời gian (ISR) | `timerPoll_1000ms` |
| ② | Thẻ SD / hồ sơ | `sdLogWrite`, `sdRead`, `loadAllProfileDates`, `_tsvNext` |
| ③ | Gas AUTO | `calibProgram` |
| ④ | Auto-loader tự học | `loaderParseScaled`, `loaderQuantize`, `loaderCfgFind`, `loaderCfgNearest`, `loaderCfgSeed`, `loaderCfgLoad`, `loaderCfgSave`, `loaderLogTrim`, `loaderLogEvent`, `loaderAdapt` |
| ⑤ | Debug / cờ pha | `debugRoastStatus`, `updateRoastPhaseFlags` |
| ⑥ | Máy trạng thái chính | `programScan` |

---

## ① Nhịp thời gian

### `timerPoll_1000ms()` — dòng 9
ISR chạy **mỗi 1 giây**. KHÔNG gọi Modbus/SD/delay trong đây — chỉ set flag (xem `[[feedback_isr_no_modbus]]`).
- **An toàn cắt gas:** BT>250°C hoặc ET>350°C (hoặc ET>300 & BT<150) → `gasPercent=0` + `fireCutFlag`.
- **Ép drum+fan:** khi BT/ET >80°C mà quạt tắt → `forceDrumFanOnFlag`.
- Đếm tất cả timer cơ cấu (charge/drop/escape/cool/ab/feeder/destoner/buzzer/fill…) bằng lambda `handleTimer` — đây là lý do các timer `$M` tính bằng **giây**.
- Đếm `timeRoast`, `timeAbsolute` (kích ghi SD).

---

## ② Thẻ SD / hồ sơ rang

### `sdLogWrite()` — dòng 190
Ghi log dữ liệu mẻ rang ra thẻ SD (đường cong BT/ET/gas theo thời gian).

### `sdRead()` — dòng 394
Đọc file profile AUTO từ SD, nạp các mốc (charge/TP/DE/FCs/DEV/drop) + bảng gas mẫu để `calibProgram()` dùng.

### `loadAllProfileDates()` — dòng 914
Quét SD lấy danh sách ngày các hồ sơ rang (cho HMI chọn file).

### `_tsvNext()` — dòng 385 (static helper)
Parser tách trường TSV khi đọc file profile.

---

## ③ Gas AUTO

### `calibProgram()` — dòng 794
Tính gas tự động: feed-forward theo `sdGas[]` + bù lệch BT so profile mẫu. Trần bậc tăng gas mỗi vùng dùng `TpCalib`/`DeCalib`/`FcsCalib`. Có thể tự bật vacuum PID giữa mẻ rồi trả về trạng thái ban đầu. Xem `[[project_gas_calib_auto]]`, `[[project_ror_gas_cut_crack]]`.

---

## ④ Auto-loader tự học (nạp liệu theo cân)

Bảng dif `(cân, ror)→dif` tự học lưu `/loadcfg.csv`. Xem `[[project_loader_dif_tuning]]`.

| Hàm | Dòng | Việc |
|-----|------|------|
| `loaderParseScaled` | 1078 | Parse số có scale từ file |
| `loaderQuantize` | 1098 | Lượng tử hoá (cân, ror) về ô lưới |
| `loaderCfgFind` | 1108 | Tìm ô khớp chính xác trong bảng |
| `loaderCfgNearest` | 1115 | Tìm ô gần nhất khi thiếu |
| `loaderCfgSeed` | 1128 | Tạo bảng dif mặc định ban đầu |
| `loaderCfgLoad` | 1147 | Nạp bảng từ SD (tạo mới nếu thiếu) |
| `loaderCfgSave` | 1204 | Ghi bảng xuống SD |
| `loaderLogTrim` | 1220 | Cắt log cũ (stream qua `/loader.tmp`, tiết kiệm RAM) |
| `loaderLogEvent` | 1259 | Ghi 1 sự kiện nạp (final/target/err) |
| `loaderAdapt` | 1289 | Cập nhật bảng dif sau mỗi lần nạp (học) |

---

## ⑤ Debug / cờ pha

### `debugRoastStatus()` — dòng 999
In trạng thái rang ra serial debug (gate bằng `enDebug`).

### `updateRoastPhaseFlags()` — dòng 1372
Set cờ pha theo BT: Dry (charge→DE), Maillard (DE→FCs), DEV (FCs→drop) — cho HMI hiển thị điểm mốc.

---

## ⑥ Máy trạng thái chính

### `programScan()` — dòng 1388 (~1020 dòng, 1388→2409)
Trái tim điều khiển mẻ rang. Chạy máy trạng thái `progStep` **11 bước**:

```
STP_DATA → STP_CHECK → STP_CHARGE → STP_TP → STP_GAS
         → STP_YELLOW → STP_FCS → STP_DEV → STP_COOL_DOWN
         → STP_LOOP_1 / STP_LOOP_2 (rang mẻ tiếp nếu loop_R>1)
```

Nhãn hiển thị HMI (`STEP_STRING`): `WAIT CHARGE`, `BT COOLS DOWN`, `CHECK TP`, `WAITGAS`, `WAIT YELLOW`, `WAIT FCS`, `DEV`, `DROP`, `LOOP`, `WCANCEL`, `RESET DATA`, `BT HEATUP`, `WAIT TP`, `NONE`.

Ngoài chuyển bước, `programScan()` còn điều khiển các cơ cấu theo timer (giây):
- Xy-lanh **nạp/xả/thoát** (charge/drop/escape)
- **Feeder** thổi liệu, **destoner** tách đá
- **Cooling + mixer** làm nguội, **afterburner** đốt khói
- **Buzzer** báo, **auto-fill** silo, **vacuum PID**

Tất cả tham số điều khiển lấy từ thanh ghi `$M` — xem [registers-M.md](registers-M.md).

---

## Ánh xạ sang app OTL Roast Lab (KHÔNG có thẻ SD)

App Python (`tools/roast_lab_hmi.py`) **không dùng SD**. Nhóm "② Thẻ SD / hồ sơ" ở firmware tách thành **2 kho riêng, 2 chỗ khác nhau** — đừng lẫn:

| Firmware (SD) | App tương đương | Lưu ở đâu |
|---------------|-----------------|-----------|
| `sdRead()` — đọc **profile mục tiêu** (công thức charge/TP/DE/FCs/DEV/drop + gas mẫu) | **Hồ sơ rang / recipe** (`profiles`) | **THƯ MỤC người dùng tự chọn** → `profiles.json` |
| `sdLogWrite()` — ghi **đường cong thực tế** (BT/ET/gas theo giây) | **Log mẻ** (`batches`) | **SQLite `batches.db`** ở `%LOCALAPPDATA%\OTL Roast Lab HMI` |
| `loadAllProfileDates()` — liệt kê hồ sơ | list profiles (json) + `db.latest()` | 2 nguồn trên |

**Hồ sơ công thức → thư mục** (`roast_lab_hmi.py:668+`):
- File `profiles.json`, ghi tạm rồi thay (chống hỏng). Thư mục nhớ ở `app_config.json` (`prof_dir`) + `settings.ini [HoSo] thu_muc`; chọn qua folder dialog `prof_dir_pick()`.
- localStorage = **cache** hằng ngày; thư mục = bản **bền**, copy/backup/chia sẻ được. Web LAN đọc **chung** `profiles.json`.

**Log mẻ thực → SQLite** (`roast_db.py`), KHÔNG để thư mục chọn:
- `batches.db` (WAL, không mất mẻ). File hỏng tự đổi tên `batches.hong-*.db` giữ bằng chứng; backup ngày `batches-YYYYMMDD.db`. Export CSV thì mới ra `prof_dir`.

> Nguyên tắc: **công thức** cần di chuyển/chia sẻ → để thư mục (dễ copy). **Log mẻ** là bằng chứng sản xuất → khoá trong DB an toàn, tránh lỡ tay xoá/sửa. Xem `[[project_sd_auto_pclink]]`, `[[project_gd123_done]]`.

## Ghi chú
- Toàn bộ mốc rang: **Charge → TP → DE(yellow) → FCs → DEV → Drop**.
- `loop_R` = số mẻ rang lặp lại (đếm lùi), KHÔNG phải "Sample".
- Firmware STM32F103RC RAM 48KB rất chật → auto-loader stream file qua `.tmp`, xem `[[reference_ram_threshold]]`.
