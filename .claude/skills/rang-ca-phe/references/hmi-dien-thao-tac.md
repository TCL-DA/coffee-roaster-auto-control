# Giáo trình THAO TÁC + ĐỌC 100 % HMI máy rang ĐIỆN VX4 — cho OTL Hồng (Modbus TCP, không chạm màn)

Soạn 15/10/2026 từ: bản HMI đang nạp `113_HMI\…\AP4\nap\T-R0-1014-LO99-DIEN.dpa` (30 màn, 2567 phần tử, 115 macro, 1 Lua 907 dòng,
309 cảnh báo), firmware `include/*.h` (env `dien`), `tools/hong_qua_panel.py`. Công cụ đi kèm: **`tools/hmi_dien.py`**.
Đường lái DUY NHẤT của Hồng: **Modbus TCP 169.254.116.153:502**. KHÔNG VNC, KHÔNG chuột / phím, KHÔNG COM13.

Ký hiệu: `$n` = ô nội bộ panel · `$Mn` = ô giữ khi mất điện · `W400nn` = địa chỉ board (Link2) · **TCP** = số thanh ghi PDU
(0-based) Hồng đọc/ghi · ⚠ = có rủi ro · ⛔ = cấm / cần anh Thành duyệt · **CHƯA XÁC MINH** = mới đọc code / file, chưa đo trên panel.

---

## 0. Bản HMI đang nạp — đã kiểm

| Kiểm | Kết quả |
|---|---|
| Bảng Modbus TCP | `T-R0-1014-LO99-DIEN.dpa` mở **`$0..$1023` (TCP 0..1023) + `$M0..$M1023` (TCP 2000..3023) + `$1100..$1105`** + coil. Bản giao `DIEN-110WS.dpa` / `NAP-R0-1014-ZOOM99-DIEN-110WS.dpa` chỉ mở `$300..399, $500..515, $819..847, $M32` |
| Đo 15/10 15:38 (chỉ đọc) | đọc được `$0..$1023`, `$M0..$M1023` (≈ 50 ms / 18 giao dịch) ⇒ panel đang chạy **LO99-DIEN** (bản giao sẽ báo ngoại lệ 2) |
| `dpa_diff` LO99-DIEN ↔ DIEN-110WS | màn, 517 địa chỉ, cảnh báo, 62 macro **trùng hết** — chỉ khác bảng TCP. Giáo trình này đúng cho cả bản giao (trừ phần TCP) |
| Ô đánh dấu `$819` | = 820 (khối v28 đã dời, ZOOM51+) |
| Board (đọc 15:42) | máy 30 kg cấu hình `$M62 = 34496` = đã cấu hình + đốt khói + tách đá; **không** VR, vacuum, loader, cân, relay ngoài |

---

## 1. Luật địa chỉ + luật ghi qua TCP (đọc kỹ trước khi ghi bất cứ ô nào)

1. **Panel là Modbus RTU SLAVE của board; board là MASTER.** Bộ nhớ chung: `{Link2}1@W400nn ≡ $(nn−1)`. Board đọc / ghi chính các
   ô `$` đó qua RS485 115200. Hồng ghi `$n` qua TCP = đúng như người bấm nút ghi `W400(n+1)`.
2. Board **đọc** panel mỗi vòng (~130 ms): `$0..$39` (khối nút; `$0..$11` đọc nhanh 4 lần/vòng), `$M1..$M63`, coil B1..B20.
   Board **ghi** lên panel: `$40` mã, `$59..$96` số đo, `$102..$124` hồ sơ / tiến trình, `$150` (tắt nút Start lúc hết mẻ),
   `$600..$810` ngày giờ hồ sơ, `$M23` (lúc nạp hồ sơ), `$0/$1/$6/$7/…` (khi máy tự bấm). Ô ngoài các vùng này là của HMI
   (macro / Lua tính). ⇒ Ghi một ô board không đọc (vd `$106`, `$150`) **không có tác dụng gì** với máy.
3. TCP: `$n` (n ≤ 1023) ↔ thanh ghi n · `$Mn` (n ≤ 1023) ↔ 2000 + n · `$1100..$1105` ↔ 1100..1105.
   **KHÔNG đọc được**: `$1024+` (trừ 1100..1105) — vd `$1110` chữ IP, `$1124..$1126` giờ con trỏ đồ thị, `$1700+` đồ thị,
   `$3010..$3044` bảng so sánh màn 19 — và `$M1024+` (bảng PIN `$M1510..`, vai `$M1520..`, ngôn ngữ `$M1535`, khoá web `$M1500`).
4. ⛔ **Ghi TCP BỎ QUA mọi thứ của nút**: khoá liên động (Interlock), cấp bảo mật (Level), min/max ô nhập, popup xác nhận,
   macro trước/sau khi bấm (BeforeExec/AfterExec). Macro NỀN (Background), macro ĐỒNG HỒ (Clock, 100 ms) và Lua (250 ms) VẪN chạy.
   ⇒ Hồng phải **tự làm** phần kiểm của nút (mục 4 ghi rõ từng nút) và **tự chép** việc macro sau-bấm làm (nếu cần).
5. Khoá liên động: **bấm được khi bit khoá = `InterLockLevel`** (bảng ghi `IL=$x.0/lv0` = bấm được khi `$x = 0`). Ẩn / hiện:
   `VIS=$x.b(cond c)` = **ẨN khi bit = c**. (Firmware Define.h ghi chú 03/10/2026 "đừng đảo lại".)
6. Kiểu số: `memfmt 2` = không dấu 16 bit, `memfmt 1` = có dấu (đổi `s16`). **Số hiện = thô × GainValue / 10^DotNum**
   (vd RoR `$62` gain 0,1, 1 lẻ ⇒ thô / 100). Chuỗi ASCII: 2 ký tự / word, **byte thấp trước** (đo `$M220..221` = "thu1").
7. Nút đa trạng thái 2 trạng thái: chạm = ghi trạng thái kế (0 ↔ 1). Qua TCP ghi thẳng giá trị đích. Nút "+ / −": cộng/trừ
   bước (5 hoặc 1) tới giới hạn. Nút "đặt giá trị" (SETVAL): ghi hằng.
8. Sau MỖI lần ghi: **đọc lại ô đó** (và ô hệ quả nếu có) trong ≤ 1,5 s. `tools/hmi_dien.py` làm sẵn (`_ghi_kiem`).

---

## 2. Màn hình, chuyển màn, đăng nhập

### 2.1 Bảng 30 màn
Màn **chính** (thay cả trang): 2, 6, 12, 13, 15, 22, 23, 26. Còn lại là **màn phụ (popup)** mở chồng lên màn chính.

| Màn | Tên | Loại | Tới từ | Ra |
|---|---|---|---|---|
| 2 | Vận hành — màn rang chính (mặc định) | chính | dock "Vận hành", mọi nút "Vận hành" | dock |
| 26 | Nền Cài đặt (dock + nền) | chính | dock "Cài đặt" ($10) | — |
| 1 | SELECT · cài đặt nhanh | phụ | dock "Cài đặt" (macro mở 26 + 1) | 2, 5, 14, 31 |
| 5 / 24 / 25 | Thông số 1/3 · 2/3 · 3/3 | phụ | màn 1 "Thông số", màn 9, 30, 36 | vòng 5→24→25→5, 9, 2, 32/33/34 |
| 9 | Hệ thống | phụ | 5 / 24 / 25 "Hệ thống" | 2, 5, 10, 30, 36 |
| 30 | Cân / hút liệu | phụ | 9, 36 | 2, 5, 35 |
| 36 | Cấu hình máy | phụ | 9 (chỉ Chuyên gia) | 2, 5, 30 |
| 32–35 | Giải thích (cửa+nhiệt · charge+tách đá · đồng hồ+đầu đốt · cân+hút) | phụ | 5 / 24 / 25 / 30 | màn gọi, 2 |
| 14 | Làm nóng trống | phụ | màn 1 "Mở làm nóng" | 2, 1 |
| 31 | Tài khoản | phụ | màn 1 "T.khoản"; tự mở khi phải đổi PIN | 2 |
| 6 / 12 / 13 | Hồ sơ trang 1/3 (1–10) · 2/3 (11–20) · 3/3 (21–30) | chính | dock "Hồ sơ" | 2, 8, 11, 19, trang kế |
| 8 / 11 | Hỏi xoá 1 hồ sơ / xoá TẤT CẢ | phụ | 6/12/13 | tự đóng |
| 16 | Hỏi ghi đè hồ sơ (bấm Bắt đầu mẻ khi RANG LƯU có hồ sơ) | phụ | nút Start màn 2 | tự đóng |
| 17 / 18 | Báo chế độ AUTO / RANG LƯU | phụ | nút chế độ màn 2 | tự đóng |
| 19 | So sánh mẻ ↔ hồ sơ | phụ | 6/12/13 | 2, 6 |
| 20 | Đang dò PID gió | phụ | màn 9 "Bắt đầu dò" | tự đóng |
| 10 / 21 | Số liệu mẻ (bảng) / Đồ thị mẻ cũ | phụ | 9, 22, 23 | 2, 9, qua lại |
| 22 / 23 | Nhật ký thao tác / Cảnh báo | chính | dock "Cảnh báo" | 2, 10, qua lại |
| 15 | Đăng nhập / khoá | chính | macro nền khi chưa đăng nhập | tự về 2 khi đăng nhập |

Dock 9 nút đáy (có ở 2, 6, 12, 13, 22, 23, 26): Cài đặt · Hồ sơ · Cảnh báo · Lệnh nhiệt · Nạp liệu · Mở cửa trống (xả) ·
Mở cửa xả khay · Quạt làm nguội · Tay đảo (ẩn ở máy điện) · Phụ trợ.

### 2.2 Chuyển màn từ xa
- **Ghi `$49` (TCP 49, W40050 = Control Block "Screen No.") = số màn** ⇒ panel chuyển màn. Đọc **`$21` (W40022, Status Block)** = màn
  đang hiện; `$20` (W40021) bit 0 = đang chuyển trang. Đã dùng thật 14/10 (`Panel.dang_nhap()` ghi `$49 = 2`).
- Board cũng đọc `$21` (firmware `SCRNUM_R`): **nạp hồ sơ chỉ chạy khi `$21` ∈ {6, 12, 13}**.
- Màn phụ qua `$49`: **ĐÃ XÁC MINH 15/10 15:52** — `$49 = 14` ⇒ `$21 = 14` (giữ sau 1 s), `$49 = 2` ⇒ về 2. ⚠ Bộ lái nào có luật "màn ≠ 2 ⇒ dừng" sẽ TẮT nhiệt khi chính Hồng đổi màn (15:52 bộ giữ 170 tự tắt) — phải miễn khi đổi màn có chủ đích.
  Các nút "Cài đặt" thật làm: `$10 = 1` + macro `OPENSCREEN(26)` `OPENSCREEN(1)` — macro này KHÔNG chạy khi ghi `$10` qua TCP.
- `$10` chỉ là cờ "đang mở Cài đặt" của HMI (board đọc W40011 nhưng không dùng). `$811` = bảng Phụ trợ mở (HMI). `$940` = 1 khi đang
  ở màn cài đặt (1, 5, 9, 14, 24–26, 30–36).
- Macro nền: **chưa đăng nhập ⇒ tự `OPENSCREEN(15)` liên tục** ⇒ mọi lệnh đổi màn khác bị kéo về 15.

### 2.3 Đăng nhập / khoá / vai
| Ô | Ý nghĩa |
|---|---|
| `$955` | ô nhập PIN (ghi PIN ⇒ macro nền so với `$M1510..$M1519`, xong tự về 0) — `Panel.dang_nhap()` dùng PIN ở `~/.otl/panel_pin.txt` |
| `$950` 1 = đã đăng nhập · `$952` số người 1..10 · `$956` vai 0 tắt / 1 Tiêu chuẩn / 2 Chuyên gia · `$951` 1 = Chuyên gia | |
| `$926` = `$950 − $951` | **1 = thợ Tiêu chuẩn** (khoá công thức, hiện màn thợ) · 0 = Chuyên gia (hoặc chưa đăng nhập) |
| `$959` | lỗi: 1 sai PIN · 2 đang khoá · 4 vừa khôi phục bằng mã OTL · `$957` số lần sai · `$859` giây khoá còn lại (5 lần sai ⇒ khoá 30 s; **đang có mẻ / làm nóng thì không khoá**) |
| `$929` | 1 = PIN tạm, phải đổi ⇒ macro tự mở 26 + 31, khoá dock (IL `$929`) |
| `$958 = 1` | đăng xuất (macro: `$952 = 0`, đóng 31 / 1) ⇒ về màn 15. ⛔ Không đăng xuất khi máy đang chạy |
| `$863` 1 = chế độ khôi phục PIN · `$864/$865` mã thử · `$866/$867` mã OTL · `$868 = 1` OK · `$858` PIN tạm · `$869` kết quả | ⛔ việc của chủ máy |
Sau khi panel khởi động / nạp lại: `$21 = 15` ⇒ `Panel().dang_nhap()` ⇒ kiểm `$21 = 2`, `$950 = 1`.

---

## 3. ĐỌC 100 % — mọi ô có nghĩa (gom theo khối đọc liền)

`python tools/hmi_dien.py doc [--json] [--ho_so]` đọc hết trong ~10 giao dịch. Khối: TCP **0–125**, 149–151, **200–229**, 450–467,
500–515, **811–999**, 1100–1105, M **0–63**, M **1000–1014**; thêm `--ho_so`: 600–810 + M100–999.

### 3.1 Khối nút lệnh `$0..$39` (board đọc mỗi vòng)
| TCP | W | Tên firmware | Ý nghĩa giá trị | Ai ghi |
|---|---|---|---|---|
| 0 | 40001 | START_BTN | 1 = chương trình (mẻ) đang chạy | HMI / board (tắt lúc hết mẻ) |
| 1 | 40002 | START_GAS_BTN | **Lệnh nhiệt** (relay CH1 + VX4). Máy điện: bật đủ 3 s ⇒ `$59 = 1` | HMI / board |
| 2 | 40003 | DRUM_FAN_BTN | trống + quạt hút (relay ngoài; máy điện ẩn). Firmware tự bật khi BT/ET > 80 °C | HMI / board |
| 3 | 40004 | MIXER_BTN | tay đảo (ẩn khi không relay riêng) | HMI / board |
| 4 | 40005 | COOLING_BTN | quạt làm nguội (relay CH2) | HMI / board |
| 5 | 40006 | FEEDER_BTN | hút liệu (CH8) | HMI / board |
| 6 | 40007 | CHARGE_BTN | xi-lanh **nạp** (CH3) | HMI / board |
| 7 | 40008 | DROP_BTN | cửa **xả trống** (CH4) | HMI / board |
| 8 | 40009 | ESCAPE_BTN | cửa **xả khay** nguội (CH5) | HMI / board |
| 9 | 40010 | DESTONER_BTN | tách đá (CH7) | HMI / board |
| 10 | 40011 | DISCHARGE_BTN | (board không dùng) — HMI dùng làm cờ "Cài đặt đang mở" | HMI |
| 11 | 40012 | AB_BTN | đốt khói (CH6) | HMI / board |
| 12 | 40013 | SAVE_BTN | không nút nào ghi; board chỉ chép | — |
| 13 | 40014 | PC_CONTROL_BTN | 1 = board nghe PC (Artisan / PC_Link) — **Hồng cần 0** | HMI |
| 14 | 40015 | CONTROL_NAVI | nguồn nhiệt: 0 tay/HMI · 1 PC · 2 AUTO (máy giữ quyền) | board |
| 15 | 40016 | SELECT_FILE | hồ sơ đang chọn 1..30 (0 = không) | HMI macro |
| 16 | 40017 | DATE_PROFILE | board ghi 1 lúc lưu hồ sơ xong ⇒ macro nền xoá chọn (`$15 = 0`, `$200..229 = 0`) rồi về 0 | board |
| 17 / 18 | 40018 / 40019 | DEL_PROFILE / DEL_ALLPROFILE | đổi giá trị ⇒ board xoá hồ sơ đang chọn / xoá hết `0..30.csv/.txt` ⛔ | HMI |
| 19 | 40020 | SAVE_PROPERTIES | không dùng | — |
| 20 | 40021 | (Status Block General) | bit 0 = HMI đang chuyển trang | HMI hệ thống |
| 21 | 40022 | SCRNUM | **màn đang hiện** | HMI hệ thống |
| 22 | 40023 | MANUAL_AUTO | 0 = **RANG LƯU** (`STT_PROGRAM_SAVE`, ghi hồ sơ) · 1 = **AUTO** theo hồ sơ | HMI |
| 30 | 40031 | AUTO_FS_BTN | tự đổ silo sau tách đá | board / HMI |
| 31 | 40032 | AUTO_PID_AIR_TU | 1 = dò PID gió đang chạy ⛔ | HMI |
| 32..37 | 40033..38 | HOUR..YEAR | đồng hồ HMI → board: giờ, phút, giây, ngày, tháng, năm | HMI |
| 38 | 40039 | REFRESH_LOAD_PF | đổi giá trị ⇒ board nạp lại ngày giờ 30 hồ sơ | HMI |
| 39 | 40040 | WU | 1 = **làm nóng trống** đang chạy (board tự về 0 khi xong / lỗi) | HMI / board |

### 3.2 Khối số đo `$40..$125` (board ghi)
| TCP | Nội dung | Đổi đơn vị |
|---|---|---|
| 40 | **mã trạng thái** (bảng 3.6) | — |
| 41 / 42 | gương trống-quạt / tay đảo | 0/1 |
| 43 / 44 | RoR BT lớn nhất TP→FCs · giây TP→RoR max | /100 °C/ph (có dấu) · s |
| 45..48 | mốc vừa chạm (giữ 15 s): BT · RoR · **mã mốc 1 Charge 2 TP 3 DE 4 FCs 5 Drop** · giây | /10 · /100 · — · s |
| 49 / 50 / 51 / 53 | Control Block: đổi màn · General (b1 đèn nền, b2 còi, b3/b4 xoá cảnh báo) · Curve · xoá đồ thị (STP_DATA) | ⛔ chỉ `$49` |
| 54 / 55 / 56 | Recipe ctrl · Recipe no · System ctrl (byte thấp = ngôn ngữ, macro chép từ `$M1535`) | — |
| 57 | cờ ghi đồ thị (word của coil B1) | 0/1 |
| 59 | **đang nung** (máy điện: Lệnh nhiệt ≥ 3 s) | 0/1 |
| 60 / 61 | **BT / ET** | /10 °C (có dấu) |
| 62 / 63 | **RoR BT / RoR ET** (= 0 khi chưa vào mẻ) | /100 °C/ph (có dấu) |
| 64 / 65 / 66 | gió / trống / **Nhiệt %** THỰC | /10 % |
| 67 / 68 | phút / giây rang (từ CHARGE) | — |
| 69 / 70 / 71 | TP: BT · phút · giây | /10 °C |
| 72 / 73 / 74 | DE (hết sấy): BT · phút · giây | /10 °C |
| 75 / 76 / 77 | FCs: BT · phút · giây | /10 °C |
| 78 / 79 / 80 | DEV: ‰ (185 = 18,5 %) · phút · giây | /10 % |
| 81 / 82 | BT lúc CHARGE / lúc DROP (≠ 0 = đã nạp / đã xả) | /10 °C |
| 83 | cân (khối lượng trên cân) | /100 kg |
| 84 | tần số trống | /100 Hz; × 0,0098 = rpm |
| 85 | áp hút (chênh áp) | Pa có dấu |
| 86..90 | cờ vacuum PID · PID 0800 KP KI KD · RoR theo kg | — |
| 91 | STATUS_MC: 1 = máy sẵn sàng | 0/1 |
| 92..95 | cờ hiện mốc Charge / pha **Sấy / Maillard / Phát triển** | 0/1 |
| 96 | **nhiệt buồng VX4** (PV) | /10 °C |
| 99..101 | hao hụt khối lượng / ẩm / tỉ trọng (macro cũ) | — |
| 102..117 | **hồ sơ đã nạp**: charge BT; TP BT/ph/s; DE BT/ph/s; FCs BT/ph/s; DEV ‰/ph/s; DROP BT/ph/s | /10 °C, DEV ‰ |
| 118 | 1 = hồ sơ **hợp lệ** (đủ CHARGE, TP, DROP ≥ 60 s, BT DROP) | 0/1 |
| 120 | % nạp hồ sơ (100 = xong & hợp lệ, 0 = hỏng) | % |
| 123 | hút liệu thiếu hạt (cân < 24 kg — macro) | 0/1 |
| 124 | % tiến trình dùng chung (dò PID / làm nóng) | % |
| 149 / 150 / 151 | ô giả của nút Dừng dò / **nút Bắt đầu mẻ** / Ghi đè–OK (macro ghi) | — |

### 3.3 Hồ sơ (`--ho_so`)
- `$200..$229` = nút chọn hồ sơ 1..30 (1 = đang chọn). `$15` = số hồ sơ. `$M1000..$M1014` = **tên hồ sơ đang chọn** (chuỗi, submacro 11 chép).
- Tên hồ sơ n: `$M(100 + 30(n−1))`, 15 word (30 ký tự). Ngày giờ hồ sơ n: `$(600 + 7(n−1))` … +6 = ngày, tháng, năm (2 số), giờ charge,
  phút charge, phút rang, giây rang (0 = không có tệp). `$810` = lệnh nạp lại ngày giờ (board).
- Tệp trên thẻ SD: **`n.csv`** (n = 1..30; cũ `n.txt`). (CLAUDE.md còn ghi 0–15 — đã cũ.)

### 3.4 Khối HMI tính `$811..$999` (macro nền / đồng hồ / Lua — chỉ đọc, trừ ô ghi rõ)
| TCP | Ý nghĩa |
|---|---|
| 811 | bảng Phụ trợ đang mở (nút dock "Phụ trợ" ghi) · 814 ô giả chặn chạm · 816 gợi ý "đồ thị tự ghi trước khi nạp" · 817 nhấp nháy |
| 819 | = 820 dấu bản HMI |
| 820..836 | gương board cho web/Lua: 820 đang nung, 821 BT, 822 ET, 823 RoR BT, 824 RoR ET, 825 gió, 826 trống, 827 nhiệt %, 828/829 ph/s rang, 830/831 RoR max, 832..834/836 mốc (BT, RoR, mã, giây), 835 ghi đồ thị |
| 837/838 | cắt tệp USB khi hết ghi đồ thị · 839 = số người đăng nhập · 840..845 giờ board (giờ, phút, giây, ngày, tháng, năm) · 846 = mã `$40` · 847 khoá web · 848 = START · 849 mồi lửa hỏng (mã 25) |
| 850..873 | tài khoản (mục 2.3); 854 kết quả đổi PIN 1 OK / 2 sai PIN cũ / 4 không hợp lệ / 8 trùng; 855 lỗi bảng người dùng (bit0 ngắn, bit1 trùng, bit2 phải còn 1 Chuyên gia); 860 cách hiện PIN; 861/862 sự kiện tài khoản; 870..872 gương Lệnh nhiệt / START / làm nóng |
| 880..883 | cờ pha Sấy / Maillard / Phát triển / quạt nguội |
| 884 | **giai đoạn (màn thợ)**: 0 chờ · 1 làm nóng · 2 làm khô · 3 chuyển nâu · 4 phát triển · 5 làm nguội · 6 xong mẻ |
| 885/886 | khung ảnh kính / chấm động · **887** câu hướng dẫn (= giai đoạn, 7 = chưa có hồ sơ) · **890..893** mức 1..5 nhiệt BT / nhiệt % / gió / trống |
| 894..898 | làm nóng: 894 thanh (0..10) · **895 trạng thái 0 dừng / 1 mồi / 2 làm nóng / 3 đạt / 4 lỗi mồi** · 898 **%** tiến trình (= (BT−30)/(đích−30)) |
| 899 / 913 | khoá nút ± nhiệt khi nguồn AUTO (Chuyên gia) |
| 900..910 | thanh pha (từ CHARGE): 900..902 bước 0..60 · **903/904/905 Sấy ph/s/%** · **906/907/908 Maillard ph/s/%** · **909/910 Phát triển ph/s** |
| 911/912, 914..919 | tính phụ (làm nóng; gương phút/giây rang, hết Sấy, FCs) |
| **920** | khoá PC control (= thợ HOẶC đang có mẻ) · 921 khoá nhiệt gốc · **922 đang có mẻ (= START)** |
| **923** | **khoá Start**: 1 khi (AUTO mà `$118 ≠ 1`) hoặc cửa xả trống mở, lúc chưa chạy |
| **924** | khoá Xoá hồ sơ (đang chạy hoặc chưa chọn) · 925 = AUTO · 926 thợ Tiêu chuẩn · **927 khoá đổi chế độ** (thợ, hoặc Chuyên gia khi có mẻ) · 928 = AUTO (khoá ô nhiệt charge) · 929 phải đổi PIN |
| 930 / 931 | nhóm gió là áp hút (vacuum) / là % gió |
| 932 | đang có mẻ · 933 nguồn nhiệt AUTO · 934 AUTO đã nạp chưa xả · 935 AUTO chưa hồ sơ · 936 cửa xả mở · 937 AUTO chạy mà hồ sơ lỗi · **938 đã qua TP** · **939 đã xả** · 940 đang ở màn cài đặt · 942 ghi đồ thị · 943 mã cuối |
| 944..949 | khung đồ thị tự giãn (18 → 25 phút) |
| 950..959 | tài khoản (2.3) |
| 962 / 967 / 968 / 969 | **đếm ngược (s)** cửa nạp / xả trống / xả khay / làm nguội (chỉ khi board tự làm trong chuỗi mẻ) · **963** bit đang đếm (1 nạp, 2 xả, 4 khay, 8 nguội, 16 tay đảo, 32 hút, 64 đốt khói, 128 tách đá) · 994..997 tay đảo / hút liệu / đốt khói / tách đá |
| 964..966 | số phụ màn 2 (ô 1×1 / dưới đốt khói, tách đá) — **CHƯA XÁC MINH** ai ghi (không thấy trong macro / Lua) |
| **970** | **MẤT KẾT NỐI BOARD** (giây rang đứng ≥ 2 s lúc đang rang) |
| 971..986 | bộ đếm giây; 980..986 giờ hệ thống panel (năm, tháng, ngày, thứ, giờ, phút, giây) |
| **990 / 991** | **mã nghiêm trọng chốt chờ xác nhận** (401..414, 417) / cờ có mã — ghi `$990 = 0` = nút "Xác nhận đã xem" |
| 998 / 999 | đếm ngược chờ lửa (s) / cờ "Chờ lửa" (máy điện: hầu như không dùng) |

Ô `$450..$467` (Lua cấu hình máy): `$450..$458` bản nháp bit (núm gas+gió, núm trống, vacuum, loader, cân, relay ngoài, đốt khói, tách đá,
tay đảo riêng) · `$459` lệnh 1 lưu / 2 huỷ ⛔ · `$460` theo núm vặn · `$461` **gương lắp đặt** (bit 0 đã cấu hình · 1 vacuum · 2 loader ·
3 cân · 4 VR gas+gió · 5 VR trống · 6 đốt khói · 7 tách đá · 8 tay đảo riêng · 9 relay ngoài) · `$462` kết quả lưu (1 chưa lưu, 2 đã lưu,
4 tay đảo cần relay, 8 núm trống cần núm gas, 16 máy đang chạy) · `$463` thẻ Phụ trợ hiện (bit 0 hút, 1 đốt khói, 2 tách đá) ·
`$464/465/466` khoá ô Nhiệt / Gió / Trống · `$467` hiện nút ± (bit 0 nhiệt, 1 gió, 2 trống).
Ô `$500..$515` web/Lua (EM thẻ nhớ USB): 506/507 tổng bản ghi, 508 số mẻ, 509 1 = Lua chạy, 510 nhịp sống, 513/514 số sự kiện.
⛔ Không ghi `$500..$503` (giao thức đọc EM của web 6081).

### 3.5 `$M` — tham số (board đọc `$M1..$M63`; giữ khi mất điện)
Đầy đủ ý nghĩa: `registers-M.md`. Hồng dùng nhiều: `$M34` trống % · `$M35` gió % (≥ 34 = 50 Hz) · `$M36` **Nhiệt %** · `$M23` nhiệt charge
×10 · `$M20/$M21` ngưỡng DE / FCs °C · `$M22` làm nguội s · `$M11` số mẻ lặp · `$M28` trần nhiệt % (đọc 15/10 = 50, và `$M29 = 1`
⇒ macro nền kẹp `$M28 ≤ 50` — **CHƯA XÁC MINH** tác dụng thật lên VX4) · `$M51/$M52` làm nóng phút / đích · `$M53` tự xả khay ·
`$M54` biên nhiệt xả ×10 · `$M62` cấu hình máy · `$M63` điều khiển trên HMI.

### 3.6 Mã trạng thái `$40` (= bảng Cảnh báo, 309 dòng trên W40041)
Bảng đầy đủ = `include/MachineStatus.h` (`hmi_dien.py` tự đọc tệp này ⇒ `ma_y_nghia`). Dải: 1–13 hệ thống · 21–50 làm nóng · 51–67 bước rang
(52 INIT, 53 COOLDOWN, 54 WAITGAS, 55 CHECK, 56 WAIT CHARGE, 57 TP, 58 YELLOW, 59 FCS, 60 DEV, 61 DROP, 62 COOLING, 63 ESCAPE, 64/65 LOOP) ·
81–96 sự kiện mốc / cửa · 101–120 thẻ SD (102 nạp OK, 103 hỏng, 111 bắt đầu ghi, 113 ghi xong, 120 không có tệp) · 121–136 vacuum ·
141–178 nút / nguồn · 201–235 cơ cấu · 241–249 cân · **261–273 nhiệt / cảm biến** · **281–298 Modbus (298 mất VX4)** · 301–320 khởi động ·
321–364 bộ RoR / học nhiệt · 381–385 hồ sơ không hợp lệ · **401–430 LỖI NGHIÊM TRỌNG** (401 cháy BT > 250, 413 RoR > 500, 414 chờ lửa
quá lâu, 417 cửa xả kẹt, 422 chưa cấu hình, 423 cấu hình bị từ chối). Mã nghiêm trọng 401–414, 417 còn chốt ở `$990`.

### 3.7 Không đọc được qua TCP (dùng đường khác)
| Thứ | Ở đâu | Cách khác |
|---|---|---|
| Đồ thị xu hướng (màn 2, 21), bảng số liệu mẻ (màn 10) | History H0001 (`$1700`, 12,5 s), H0002 (`$820`, 1 s), H0003 — bộ nhớ panel / USB | Artisan `.alog` (đường chính); số tức thời ở `$820..$836` |
| Bảng cảnh báo hiện tại / lịch sử (màn 23), nhật ký thao tác (màn 22) | bộ nhớ panel | `$40`, `$943`, `$990`; sự kiện mã ghi vào EM USB (web 6081) |
| Bảng so sánh màn 19 | `$3010..$3044` | tự tính từ `$102..$117` (hồ sơ) và `$67..$80` (mẻ) |
| Giờ tại con trỏ đồ thị · chữ IP · ngôn ngữ · PIN | `$1124..1126`, `$1110`, `$M1535`, `$M1510+` | — (không cần) |

---

## 4. THAO TÁC từng màn — mọi phần tử tương tác (363 phần tử / 30 màn)

Cột "Hồng làm" = ghi gì qua TCP + đọc lại gì. "Khoá" = điều kiện HMI (Hồng tự kiểm vì TCP bỏ qua).

### 4.1 Dock (màn 2, 6, 12, 13, 22, 23, 26 — giống nhau)
| Nhãn | Ghi | Kiểu | Khoá / macro | Firmware | Hồng làm |
|---|---|---|---|---|---|
| Cài đặt | `$10` | đảo 0/1 | IL `$929` (phải đổi PIN thì khoá). Trước: đóng mọi popup; sau: `$10=1` ⇒ mở 26 + 1, `$10=0` ⇒ đóng | không | `$49 = 26` (popup 1: CHƯA XÁC MINH) |
| Hồ sơ | đổi màn 6 | goto | IL `$929`; đóng popup | — | `$49 = 6`, đọc `$21` |
| Cảnh báo | đổi màn 23 | goto | IL `$929` | — | `$49 = 23` |
| Lệnh nhiệt | `$1` (W40002) | đảo | — | relay CH1 + VX4 SV; 3 s ⇒ `$59 = 1` (Đang nung). Trong COOL_DOWN / GAS board tự đóng-mở | `$1 = 1/0` → đọc `$1`, sau 3 s `$59`; đèn `$820` |
| Nạp liệu | `$6` (W40007) | đảo | — | CH3 mở xi-lanh nạp. **Ngoài chương trình KHÔNG tự đóng**; trong chương trình (bước CHARGE) tự đóng sau `$M1` s | ⚠ `$6 = 1` rồi `$6 = 0`; đọc `$6` |
| Mở cửa trống (xả) | `$7` (W40008) | đảo | — | CH4. Trong mẻ (bước ≥ CHARGE): = **DROP** (lưu mốc, kết thúc ghi hồ sơ, tự đóng sau `$M2` s, chạy làm nguội). Ngoài mẻ: chỉ mở cửa | ⚠ `$7 = 1`; ngoài mẻ tự ghi `$7 = 0` |
| Mở cửa xả khay | `$8` (W40009) | đảo | — | CH5. `$M53 = 0`: xả tay tự đóng sau `$M3 + $M60` s | ⚠ `$8 = 1/0` |
| Quạt làm nguội | `$4` (W40005) | đảo | — | CH2 (huỷ chuỗi làm nguội nếu về 0) | `$4 = 1/0` |
| Tay đảo | `$3` (W40004) | đảo | ẨN khi `$461` bit 8 = 0 (máy điện) | relay ngoài | không dùng |
| Phụ trợ | `$811` (màn 26: `$814` + macro `$811=1`, mở 2) | đảo | — | không | đọc `$811`; không cần ghi |
| Bảng Phụ trợ: Hút liệu / Đốt khói / Tách đá | `$5` / `$11` / `$9` | đảo | ẨN theo `$463` bit 0/1/2 | CH8 / CH6 / CH7; tự tắt theo `$M14` / `$M27` / `$M19` | ⚠ ⛔ không cần cho bài nhiệt |
| Đèn | `$59` lửa/nung · `$820` "Đang nung/Tắt nhiệt" · `$999/$998` chờ lửa · `$962..$997` đếm ngược · `$940` Cài đặt mở | | | | đọc |

### 4.2 Màn 2 — Vận hành (30 tương tác)
| Nhãn | Ghi | Kiểu / giới hạn | Khoá | Macro sau bấm | Firmware | Hồng làm |
|---|---|---|---|---|---|---|
| **Bắt đầu mẻ / Dừng chương trình** | `$150` (W40151) | đảo | IL `$923` (khoá Start) | `$150=1`: AUTO cần `$118=1` ⇒ `$0=1`, không thì `$150=0`; RANG LƯU + `$15>0` + chưa chạy ⇒ mở **16 (Ghi đè?)**; còn lại ⇒ `$0=1`. `$150=0` ⇒ `$0=0` | `$0` chạy máy trạng thái (mục 5) | ⛔ ghi THẲNG `$0` sau khi tự kiểm (`bat_dau()` / `dung_chuong_trinh()`); KHÔNG ghi `$150` (vô tác dụng qua TCP) |
| Chế độ (RANG LƯU / AUTO) | `$22` (W40023) | đảo | IL `$927` (thợ; Chuyên gia khi có mẻ) | mở 17 (AUTO) / 18 (LƯU) — chỉ là thông báo | đổi `progStatus` NGAY, kể cả giữa mẻ ⚠ | `che_do()` — chỉ khi `$0 = 0` |
| Ô **Nhiệt %** | `$M36` (TCP 2036) | 0..100, bước ± 5 | IL `$464` (núm vặn / nguồn AUTO); nút ± ẩn khi `$467` bit 0 = 0 | — | nguồn VR/HMI: `gasPercent = $M36` ⇒ SV VX4 = 130 + % × 2,2 °C. Bỏ qua khi nguồn AUTO (`$14 = 2`) hoặc PC | `Panel.dat_nhiet()`; đọc `$M36`, `$66/10` |
| Ô Gió % | `$M35` (2035) | 0..100 ± 5 (Hồng ≥ 34) | IL `$465` (thợ / núm); ẩn khi `$930 = 1` | — | `airflowPercent` → biến tần ID 5 45–60 Hz | `dat_gio()`; đọc `$64/10` |
| Ô Áp hút Pa | `$M48` | 50..250 ± 5 | ẩn khi `$931 = 1` (máy điện: ẩn); IL `$926` | — | setpoint PID vacuum | không dùng |
| Ô Trống % | `$M34` (2034) | 0..100 ± 5 | IL `$466` | — | biến tần ID 4 | `dat_trong()`; đọc `$65/10`, `$84` |
| Ngưỡng DE °C ("Drying end") | `$M20` | 1..300 | IL `$926` (Chuyên gia) | — | `yellowPhase_R` — mốc DE trong mẻ | chỉ khi máy rảnh ⚠ |
| Ngưỡng FCs °C | `$M21` | 1..300 | IL `$926` | — | `fcsPhase_R` — mốc FCs | chỉ khi máy rảnh ⚠ |
| Nút Cài đặt / Hồ sơ / Cảnh báo + dock | mục 4.1 | | | | | |
| Đèn / số (chỉ đọc) | BT `$60` · ET `$61` · RoR `$62/$63` · thực nhiệt (máy điện = buồng `$96`) · gió `$64` · trống rpm `$84` · giờ `$67:$68` · mốc TP/DE/FCs/Xả `$69..$82` · hồ sơ `$15` + tên `$M1000` · giai đoạn `$887` · thanh pha `$900..$910` · nguồn `$14` · cảnh báo `$991/$990` · "MẤT KẾT NỐI BOARD" `$970` | | | | | đọc |

### 4.3 Màn 6 / 12 / 13 — Hồ sơ (43–44 tương tác mỗi trang)
| Nhãn | Ghi | Kiểu | Khoá | Macro sau bấm | Firmware | Hồng làm |
|---|---|---|---|---|---|---|
| Nút chọn hồ sơ n (10/trang) | `$(199+n)` (W402xx) | đảo | IL `$922` (có mẻ) | `$15 = n`, xoá `$200..229`, `$(199+n) = 1`. Macro ĐỒNG HỒ: `$15 = n` mà `$(199+n) = 0` ⇒ **`$15 = 0`** | `$15` đổi & `$21 ∈ {6,12,13}` ⇒ đọc `n.csv` ⇒ `$102..$117`, `$118`, `$120`, **ghi đè `$M23`** = charge của tệp (hỏng ⇒ 180,0) | `chon_ho_so(n)`: đứng đúng trang → `$200..229` một-nóng → `$15 = n` → chờ `$120`/`$118`/`$40` |
| Tên hồ sơ (ô chữ) | `$M(100+30(n−1))` | chuỗi 30 ký tự | IL `$926` | — | không (chỉ HMI, firmware không ghi SD) | `dat_ten_ho_so(n, ten)` — ĐÃ XÁC MINH 15/10 16:50: ghi slot 1/2 "1510 M1 500g" / "1510 M2 700g", còn sau Làm mới. LUẬT: mỗi mẻ RANG LƯU xong đặt tên `<ddmm> M<số> <g>g` |
| Ô DE °C / FCs °C của hồ sơ | `$106` / `$109` | 0,0..300,0 | IL `$926` | ⚠ `if $M5 > 0 ⇒ $M4 = 0` (xoá trần bù trước DE!) | **board không đọc lại `$102..$117`** ⇒ vô tác dụng, bị ghi đè khi nạp lại | KHÔNG ghi |
| Ô Nhiệt charge | `$M23` | 0,0..250,0 (×10) | IL `$928` (AUTO thì khoá) | — | nhiệt nạp: COOL_DOWN / CHECK / tự CHARGE ở `$M23 ± $M10` | `nhiet_charge(°C)` — SAU khi chọn hồ sơ |
| Làm mới | `$38` | đảo | — | — | nạp lại ngày giờ 30 hồ sơ | `lam_moi_ho_so()` |
| Xoá hồ sơ | mở 8 | goto | ẩn với thợ; IL `$924` | đóng 11 | — | ⛔ |
| Xoá toàn bộ | mở 11 | goto | ẩn với thợ; IL `$922` | đóng 8 | — | ⛔ |
| So sánh | mở 19 | goto | ẩn với thợ | — | — | đọc thay (3.7) |
| Trước / Sau / Vận hành | 6↔12↔13, 2 | goto | — | — | — | `$49` |
| Đọc | tên `$M1000`, hợp lệ `$118`, % `$120`, mốc hồ sơ `$102..$117`, ngày giờ `$600..$809`, khoá `$922` | | | | | `hmi_dien.py ho_so` |

### 4.4 Popup hỏi (8, 11, 16, 17, 18, 20)
| Màn · nút | Ghi | Macro | Firmware | Hồng |
|---|---|---|---|---|
| 8 · Xoá | `$17` (W40018) đảo | đóng 8; `FILL($M100, 0, 30)` (xoá **tên hồ sơ 1**, không phải hồ sơ đang chọn — nghi lỗi HMI) | `$17` đổi ⇒ `sdLogStartEn` = **xoá `n.csv` rồi mở tệp mới trống**, ghi `$17 = 0` | ⛔ |
| 8 / 11 · Huỷ | `$777` (ô giả) | đóng | — | — |
| 11 · Xoá toàn bộ | `$18` (W40019) đảo | `FILL($M100, 0, 900)` xoá 30 tên; đóng | xoá `0..30.csv/.txt`, nạp lại ngày | ⛔ |
| 16 · Ghi đè | `$151` | `$0 = 1`, `$150 = 1`, đóng, `$151 = 0` | bắt đầu mẻ RANG LƯU vào hồ sơ `$15` | Hồng = người xác nhận ⇒ cần anh duyệt rồi ghi `$0 = 1` |
| 16 · Huỷ | `$151` | `$150 = 0`, `$0 = 0` | — | — |
| 17 / 18 · Đã hiểu | `$151` | đóng; `$10 = 0` | — | — |
| 20 · Dừng dò | `$149` | `$31 = 0`, `$149 = 0`, đóng 20 | dừng dò PID gió | an toàn: ghi `$31 = 0` |

### 4.5 Màn 1 — SELECT (cài đặt nhanh, 15 tương tác)
| Nhãn | Ghi | Kiểu / giới hạn | Khoá / ẩn | Firmware | Hồng |
|---|---|---|---|---|---|
| Mở làm nóng trống | mở 14 (đóng 1, `$10=0`) | goto | — | — | `$49 = 14` (CHƯA XÁC MINH) |
| Điều khiển từ PC | `$13` | đảo | IL `$920` | 1 ⇒ nguồn nhiệt/gió/trống = PC (Artisan / PC_Link); HMI ± bị lờ | giữ **0** (`pc_control(0)`) |
| Làm nguội sau xả (s) | `$M22` | 0..900 | IL `$926` | thời gian làm nguội + tay đảo sau DROP | máy rảnh |
| Khối lượng hút mỗi mẻ | `$M32` | 0,0..30,0 kg (×10) | macro kẹp ≤ cân | loader | ⛔ máy điện không loader |
| Hút liệu tự động | `$M33` | đảo | ẩn khi `$461` bit 2 = 0 | — | — |
| Hút liệu / Tách đá / Trống + quạt hút | `$5` / `$9` / `$2` | đảo | ẩn theo `$461` bit 2 / 7 / 9 | relay | ⚠ |
| Thông số / Vận hành / T.khoản | mở 5 / 2 / 31 | goto | Thông số ẩn với thợ | — | `$49` |
| Khoá web | `$M1500` | đảo | — | web 6081 khoá điều khiển | ⛔ TCP không tới `$M1500` |
| Tiếng Việt / English | `$M1535` = 1 / 0 | SETVAL | — | — | ⛔ TCP không tới |
| Ô IP | `$1110` | chữ 24 | ẩn khi `$1122 = 0` | Lua tự ghi | — |

### 4.6 Màn 14 — Làm nóng trống (9 tương tác)
| Nhãn | Ghi | Giới hạn | Khoá | Macro | Firmware | Hồng |
|---|---|---|---|---|---|---|
| Bắt đầu / Dừng làm nóng | `$39` (W40040) | đảo | — | `$31 = 0`, `$149 = 0`, đóng 20 | `preheat()` (chỉ khi `$0 = 0`): giữ quyền **nhiệt + gió** (PID của firmware — được phép), BT về `$M52`, giữ tới hết `$M51` phút ⇒ mã 30, board ghi `$39 = 0`. Ghi 0 ⇒ huỷ (mã 31) | `lam_nong(1/0)` ⛔ cần quyền lái |
| Nhiệt độ đích | `$M52` | 150..230 °C, ± 1 | IL `$922` | — | `wuTemp_R` | ghi trước khi bật |
| Thời gian | `$M51` | 2..60 phút (nút − dừng ở 5) | IL `$922` | — | `wuTime_R` | ghi trước khi bật |
| Vận hành / Trước | 2 / 1 | goto | | | | |
| Đọc | `$898` %, `$895` trạng thái, `$894`, `$849` lỗi mồi, BT `$60`, `$40` (21–50) | | | | | |

### 4.7 Màn 5 / 24 / 25 / 30 — Thông số (⛔ cấu hình — chủ máy / Chuyên gia; Hồng chỉ ĐỌC)
| Màn | Ô (giới hạn) |
|---|---|
| 5 | `$M1` mở cửa nạp 10..100 s · `$M2` mở cửa trống 15..100 · `$M3` xả khay 15..250 · `$M4/$M5/$M31` trần bù nhiệt trước DE / DE→FCs / sau FCs 10..50 % · Bảng mật khẩu (Level 3) · "Set Low Security" (macro `BITOFF $5000.0` — CHƯA XÁC MINH) · Trước/Sau/Hệ thống/Vận hành/Giải thích |
| 24 | `$M10` dung sai nạp 1..10 °C · `$M8` nhiệt chờ nạp 5..100 % · `$M9` lùi bật lại nhiệt 10..100 °C · `$M7` đốt khói bật 100..500 °C · `$M27` đốt khói thêm 0..180 s · `$M30` làm nguội sớm 0,0..1,0 °C · `$M19` tách đá 0..500 s · `$M26` tách đá sớm 0..15 s · `$M28` trần nhiệt 10..100 % |
| 25 | `$M6` thanh ghi BT/ET 0..65534 · `$M24` SV đồng hồ BT 180..300 · `$M25` thanh ghi SV · `$M12` ID PC 1..99 · `$M13` baud 9600..57600 · `$M37` tự tắt nhiệt khi xả/dừng · `$M29` premix (máy điện: "bỏ tín hiệu lửa, trần 50 %") · `$M47` vacuum (ẩn) · `$M11` số mẻ lặp 1..15 (chỉ bấm được khi AUTO, IL `$928` lv1). Khoá `$922` cho các ô hệ thống |
| 30 | `$M44` còn lại tối thiểu 0..99,9 kg · `$M14` thổi cấp liệu 0..300 s (macro kẹp `$M32`) |

### 4.8 Màn 9 — Hệ thống · 36 — Cấu hình máy · 31 — Tài khoản · 15 — Đăng nhập (⛔ trừ đăng nhập)
| Màn | Phần tử | Ghi chú |
|---|---|---|
| 9 | Menu panel · Độ sáng · Báo cáo · Ngày giờ (đối tượng hệ thống Delta, IL `$922`) | không có địa chỉ — chỉ chạm tay ⛔ |
| 9 | `$M49 / $M50` giới hạn cảm biến áp −2000..2000 Pa (IL `$922`) · **Bắt đầu dò PID gió `$31`** (+ mở 20) ⛔ · `$M53` chế độ xả khay · Xem đồ thị mẻ cũ (mở 10) · Cân (30) · Cấu hình (36, Chuyên gia) · `$M1500` | |
| 36 | nháp `$450..$458` (IL `$926`) · **Lưu `$459 = 1`** ⇒ Lua ghi `$M62` (⚠ ép cỡ máy = 30 kg, bit 6–8 = 3) · `$M63` điều khiển trên HMI · `$M1500` | ⛔ đổi cấu hình máy |
| 31 | đổi PIN của mình `$850/$851/$852` + Lưu `$853` ⇒ `$854` · bảng 10 người (PIN `$M1510+`, vai `$M1520+` — ngoài TCP) · Hiện PIN `$873` · Đăng xuất `$958` | ⛔ |
| 15 | PIN `$955` · khôi phục `$863`, mã OTL `$866/$867`, OK `$868` · ngôn ngữ | Hồng: chỉ `dang_nhap()` |

### 4.9 Màn 10, 19, 21, 22, 23, 32–35 — xem / điều hướng
- 10 (bảng số liệu mẻ), 21 (đồ thị mẻ cũ), 22 (nhật ký thao tác): chỉ nút Trước / Vận hành / Đồ thị / Bảng số / Cảnh báo / Số liệu mẻ. Dữ liệu ngoài TCP.
- 19 So sánh: Vận hành / Trước. Đọc: `$15`, `$M1000`, `$67/$68`; bảng `$3010..` ngoài TCP.
- 23 Cảnh báo: **Xác nhận đã xem = `$990 = 0`** (`xac_nhan_canh_bao()`); bảng hiện tại + lịch sử ngoài TCP; dock.
- 32–35 Giải thích: Quay lại / Vận hành.

---

## 5. QUY TRÌNH đầy đủ (mỗi bước: ghi → đọc lại → mới sang bước kế)

**Điều kiện chung trước MỌI quy trình ghi**: `$21` đúng màn · `$950 = 1` · `$13 = 0` · `$40` không ở 401–430 · `$970 = 0` ·
Artisan đang ghi (luật Hồng) · anh Thành đã cho quyền đúng phạm vi. Huỷ an toàn chung: `python tools/hong_qua_panel.py an_toan`
(tắt nhiệt + làm mát) — và `$0 = 0` nếu chương trình đang chạy.

### 5.1 Chọn hồ sơ n (1..30) — `chon_ho_so(n)`
1. Kiểm `$0 = 0`, `$39 = 0` (khoá HMI `$922`).
2. `$49 = 6 / 12 / 13` (trang chứa n) → chờ `$21` = trang đó (board chỉ nạp khi đứng màn Hồ sơ).
3. Ghi `$200..$229` = 1 ở vị trí n, 0 chỗ khác (MỘT lệnh ghi 30 ô) → đọc lại.
4. Ghi `$15 = n` → đọc lại (nếu về 0 ⇒ bước 3 chưa đúng: macro đồng hồ đã trả về).
5. Chờ ≤ 15 s: `$40` = 101 → 102 (OK) / 103, 120, 381–385 (hỏng); `$120` = 100 & `$118` = 1 = hợp lệ.
6. Đọc `$102..$117` (mốc hồ sơ) + **`$M23`** (đã bị ghi = charge của tệp, hỏng ⇒ 1800) + tên `$M1000`.
- Rủi ro: thấp (không cơ cấu). Đổi `$M23`. Huỷ: `bo_chon_ho_so()` (`$200..229 = 0`, `$15 = 0` ⇒ macro nền xoá `$102..$117`).
- Đã thấy 15/10 15:21: `$15 = 1` ở màn 2 ⇒ đọc lại 0 — giải thích: thiếu `$200 = 1` (macro đồng hồ) **và** đang ở màn 2 (board không nạp).

### 5.2 RANG LƯU chương trình vào hồ sơ n (SAVE) — ⛔ cần anh duyệt (ghi đè `n.csv`, máy tự CHARGE)
1. Hạt đã sẵn trong phễu nạp (máy sẽ TỰ mở cửa nạp). Cửa xả `$7 = 0`. Thẻ SD tốt (không mã 11 / 106).
2. `chon_ho_so(n)` (5.1) — hồ sơ trống / chưa có tệp vẫn được (mã 120, `$118 = 0`).
3. `che_do(save)`: `$22 = 0` → đọc lại.
4. `nhiet_charge(T)`: `$M23 = T × 10` → đọc lại (SAU bước 2 vì nạp hồ sơ ghi đè). Kiểm `$M9` (lùi bật lại), `$M10` (dung sai), `$M8`.
5. Đặt sẵn gió / trống `$M35` / `$M34` (sau CHARGE nguồn = HMI).
6. `bat_dau()`: `$0 = 1` (TCP không qua popup 16 "Ghi đè?" — Hồng là người xác nhận). Đọc `$0 = 1`, `$40` = 52 → 111 (bắt đầu ghi SD).
7. Máy tự làm: DATA (xoá `n.csv`, ghi tiêu đề) → COOL_DOWN (BT > T − `$M9` ⇒ **tắt nhiệt** chờ nguội; đủ nguội ⇒ **nhiệt 50 % AUTO**, `$14 = 2`)
   → GAS (máy điện: 3 s) → CHECK (BT ∈ T ± `$M10` ⇒ **tự mở cửa nạp + còi**, đóng sau `$M1` s; vọt > T + 5 × `$M10` ⇒ tắt nhiệt, làm lại)
   → CHARGE: đồng hồ mẻ chạy, nguồn nhiệt/gió/trống = **HMI** (`$M36/$M35/$M34`, Hồng lái MPC) → TP / DE (`$M20`) / FCs (`$M21`) tự chốt.
   Trong COOL_DOWN → CHECK nguồn nhiệt là AUTO (latched): ghi `$M36` KHÔNG có tác dụng.
8. Xả: `$7 = 1` (DROP) ⇒ firmware: `$0 = 0`, ghi lại tiêu đề `n.csv` (mã 113), `$16 = 1` ⇒ HMI xoá chọn hồ sơ; `$M37 = 1` ⇒ tắt nhiệt;
   cửa xả tự đóng sau `$M2` s; làm nguội `$M22` s; `$M53 = 1` ⇒ tự xả khay.
9. Kiểm: `$40` 113, `hmi_dien.py ho_so` thấy ngày giờ hồ sơ n (sau Làm mới).
- Rủi ro: ghi đè tệp n; tự mở cửa nạp; nhiệt 50 % lúc gia nhiệt chờ nạp; mẻ > 50 phút ⇒ mã 96.
- Huỷ: `$0 = 0` (dừng ngay — **không tắt nhiệt, không làm nguội** ⇒ `an_toan`). Tệp `n.csv` đã bị xoá / ghi dở.
- `$15 = 0` mà vẫn START RANG LƯU ⇒ firmware ghi `0.csv` (CHƯA XÁC MINH có chủ ý).

### 5.3 Rang AUTO theo hồ sơ n — ⛔ cần anh duyệt (máy tự lái nhiệt/gió/trống, tự CHARGE, tự DROP)
1. Hạt sẵn, `$7 = 0`. `chon_ho_so(n)` ⇒ **bắt buộc `$118 = 1`** (khoá Start `$923` / `$935`).
2. `che_do(auto)`: `$22 = 1`. (`$M23` khoá trên HMI; dùng charge của hồ sơ.) `$M11` số mẻ lặp (1 = một mẻ).
3. `bat_dau()`: `$0 = 1` → `$40` 52 → 53/54/55 → 56. Trần nhiệt = MaxGas của hồ sơ.
4. Máy tự CHARGE (như 5.2) → nguồn AUTO (`$14 = 2`, `$933 = 1`): bám `sdBT[]` hồ sơ, bù nhiệt (trần `$M4/$M5/$M31`) → **tự DROP** khi BT ≥ nhiệt xả
   (± `$M54` theo lệch thời gian) → làm nguội → lặp nếu `$M11 > 1` (chờ cửa xả đóng 20 s rồi mẻ mới).
5. Hồng: CHỈ ĐỌC (`$40`, mốc, `$970`). Không ghi `$M34..36` (bị lờ khi AUTO).
- Huỷ: `$0 = 0` ⇒ trả nguồn về HMI, KHÔNG tắt nhiệt ⇒ `an_toan`. Đang trong cửa sổ LOOP_2 (20 s): `$0 = 0` = không chạy mẻ tiếp.

### 5.4 Rang MANUAL (ngoài chương trình — cách Hồng lái hiện nay)
`$0 = 0`. Hồng lái `$1`, `$M36`, `$M35`, `$M34` (nguồn HMI, `$14 = 0`). Nạp hạt: `$6 = 1` → sau ~`$M1` s **tự ghi `$6 = 0`** (firmware
không tự đóng ngoài chương trình). Xả: `$7 = 1` → `$7 = 0` sau ~`$M2` s. Làm nguội: `$4 = 1/0`. Xả khay `$8`.
Firmware KHÔNG chốt mốc, KHÔNG ghi SD (mốc `$69..$82` = 0) ⇒ Artisan là bản ghi; muốn có hồ sơ thì dựng `n.csv` từ `.alog` (định dạng ở `registers-M.md`).

### 5.5 Làm nóng trống (preheat của firmware) — `lam_nong(1, dich, phut)`
1. `$0 = 0`, `$39 = 0`, cửa đóng, trống chạy. 2. `$M52` = đích (150..230), `$M51` = phút (2..60) → đọc lại. 3. `$31` = 0 nếu đang 1.
4. `$39 = 1` → `$40` 21 → 27/28; `$895` 2 → 3 (đạt); `$898` %. Firmware giữ nhiệt + gió (PID — được phép trong preheat).
5. Hết giờ ⇒ mã 30, board ghi `$39 = 0` (nhiệt do firmware tắt / giữ theo preheat). Huỷ: `lam_nong(0)` ⇒ mã 31; kiểm `$1`, `$66`.

### 5.6 Charge / drop / làm mát / xả khay (lệnh đơn) — `co_cau(ten, 1/0)`
| Việc | Ghi | Đọc lại | Ghi chú |
|---|---|---|---|
| Nạp (charge) | `$6 = 1` … `$6 = 0` | `$6` (mã 201/202 firmware KHÔNG phát) | trong mẻ ở bước CHARGE = mốc CHARGE (đồng hồ mẻ chạy) |
| Xả trống (drop) | `$7 = 1` … `$7 = 0` | `$7`, `$82` (trong mẻ) | trong mẻ = DROP (tự đóng `$M2`) |
| Làm nguội | `$4 = 1 / 0` | `$4`, `$969` | |
| Xả khay | `$8 = 1 / 0` | `$8`, `$968` | `$M53 = 0`: tự đóng sau `$M3 + $M60` |
- ⛔ Mở cửa nạp khi lồng nóng không có hạt: BT tụt ~5 °C / 10 s (đo 14/10). Mở cửa xả khi đang rang = **xả mẻ**.

### 5.7 Xoá hồ sơ / xoá tất cả — ⛔ CHỈ chủ máy bấm tay trên panel
Đường máy: chọn n → màn 8 → Xoá ⇒ `$17` đổi ⇒ board xoá `n.csv` (tạo lại tệp trống) — và macro xoá **tên hồ sơ 1** (nghi lỗi HMI).
Xoá tất cả: màn 11 ⇒ `$18` ⇒ xoá 0..30 + 30 tên. `hmi_dien.py` cố ý KHÔNG có lệnh này.

### 5.8 Làm mới danh sách hồ sơ (refresh SD) — `lam_moi_ho_so()`
Đảo `$38` (bất kỳ màn nào; board không cần màn Hồ sơ) → board nạp lại ngày giờ (không phát mã riêng); đọc `$600..$809`. An toàn (chỉ đọc thẻ).

### 5.9 Đổi nhiệt charge / nhiệt xả
- Nhiệt charge: `nhiet_charge(T)` = `$M23 = T × 10`, chỉ khi `$0 = 0`; AUTO dùng charge của hồ sơ (nạp hồ sơ ghi đè `$M23`).
- **Nhiệt xả KHÔNG có ô nhập**: RANG LƯU / MANUAL = người xả (`$7`); AUTO = BT DROP của hồ sơ (`$115`, chỉ đọc) ± `$M54` (biên 0,0..1,0 °C, ⛔ cấu hình).
  Ô DE / FCs trên màn Hồ sơ (`$106`, `$109`) board không đọc — đừng dùng.

### 5.10 PC control
`$13 = 1` ⇒ board nghe PC (Artisan / PC_Link, mã 8); `$13 = 0` ⇒ nghe panel (mã 9). Hồng lái qua panel ⇒ **luôn 0**; thấy 1 ⇒ dừng lái, báo anh
(không tự tắt khi Artisan / app đang lái). Khoá HMI: `$920` (thợ hoặc có mẻ).

### 5.11 Tune (dò PID gió) — ⛔ không dùng ở máy điện
`$31 = 1` ⇒ gió quét 0→100 % từng 1 % (mã 128–131), `$124` %; máy điện không vacuum ⇒ vô nghĩa. Lỡ bật: `$31 = 0` (mã 132).

### 5.12 Đăng nhập lại / xác nhận cảnh báo
`Panel().dang_nhap()` (khi `$21 = 15`). Cảnh báo nghiêm trọng đã xử lý gốc ⇒ `xac_nhan_canh_bao()` (`$990 = 0`) — chỉ xoá chốt hiển thị.

---

## 6. Hồng làm trên máy thật — tóm tắt lệnh `tools/hmi_dien.py`
| Việc | Lệnh | Quyền |
|---|---|---|
| Đọc hết / theo màn / hồ sơ | `doc [--json] [--ho_so]` · `doc_man <id>` · `ho_so` · `man` · `tho <ô> [n]` | luôn |
| Chuyển màn | `chuyen_man <id>` | `HONG_DUOC_THAO_TAC=1` |
| Hồ sơ | `chon_ho_so <n>` · `bo_chon_ho_so` · `lam_moi_ho_so` | `HONG_DUOC_THAO_TAC=1` |
| Chế độ / charge / PC / cảnh báo / dừng | `che_do save|auto` · `nhiet_charge <°C>` · `pc_control 0` · `xac_nhan_canh_bao` · `dung_chuong_trinh` | `HONG_DUOC_THAO_TAC=1` |
| Chạy máy | `bat_dau` · `lam_nong 1 --dich 210 --phut 15` · `co_cau nap|xa_trong|xa_khay|quat_nguoi 1|0` | + `HONG_DUOC_LAI=1` |
Mọi hàm ghi: kiểm điều kiện trước (không đạt ⇒ `TỪ CHỐI`, không ghi gì) → ghi → đọc lại ≤ 1,5 s → trả `(giá trị đọc lại, đạt?)`.

---

## 7. ⛔ CẤM / chỉ khi anh Thành duyệt rõ
| Nhóm | Ô / lệnh | Vì sao |
|---|---|---|
| Máy tự chạy cơ cấu | `$0 = 1` (START — tự nạp, tự gia nhiệt 50 %, AUTO tự xả) · `$39 = 1` (làm nóng) · `$6/$7/$8` cửa · `$5/$9/$11` hút / tách đá / đốt khói · `$2/$3` | hạt rơi, nhiệt, cơ cấu chạy |
| Xoá dữ liệu | `$17`, `$18` (xoá hồ sơ) · START RANG LƯU khi hồ sơ n đã có dữ liệu (ghi đè) · `$500..$503` · `$958` đăng xuất | mất hồ sơ / nhật ký |
| Đổi cấu hình máy | `$M1..$M63` ngoài `$M23/$M34/$M35/$M36/$M51/$M52` · `$450..$459` · `$M62` · `$M20/$M21` (mốc) · `$22` khi đang chạy | đổi hành vi máy, firmware + HMI phải khớp |
| Hệ thống | `$49` sang màn 9 / 36 / 31 / 5 để GHI · `$50..$56` Control Block (còi, đèn, ngôn ngữ) · `$31` dò PID · `$13 = 1` | |
| Tài khoản | `$850..$873`, `$955` với PIN người khác | |
| Luôn được (an toàn) | `$0 = 0`, `$1 = 0`, `$M36 = 0`, `$39 = 0`, `$31 = 0`, `$4 = 1` (làm nguội), `an_toan` | |

---

## 8. Kế hoạch ĐIỀU KHIỂN THỬ (sau mẻ, lồng KHÔNG hạt, KHÔNG bật nhiệt) — anh Thành cho phép trước khi chạy
Chuẩn bị: `doc` lưu ảnh đầu (`python tools/hmi_dien.py doc --json --ho_so > thu_0.json`), máy nguội < 60 °C hoặc đang làm nguội, `$1 = 0`,
`$0 = 0`, `$39 = 0`, cửa đóng. Mỗi bước: 1 ghi → đọc lại → ghi kết quả vào sổ; sai ⇒ hoàn tác ngay rồi dừng.

| # | Việc | Ghi | Đạt khi | Hoàn tác |
|---|---|---|---|---|
| 1 | Đọc 100 % + ghi sổ giá trị gốc | — | `doc` chạy, BT/ET/buồng khớp `hong_qua_panel.py doc` | — |
| 2 | Chuyển màn chính | `chuyen_man 6` rồi `chuyen_man 2` | `$21` = 6 rồi 2 | `$49 = 2` |
| 3 | Chuyển màn **phụ** (xác minh 2.2) | `chuyen_man 14` | ghi kết quả: `$21 = 14`? panel hiện gì (hỏi anh nhìn) | `$49 = 2` |
| 4 | Làm mới hồ sơ | `lam_moi_ho_so` | `$38` đổi; `$600..$809` khớp thẻ (`ho_so`) | — (vô hại) |
| 5 | Chọn hồ sơ có sẵn (vd 5 "thu1") | `chon_ho_so 5` | `$15 = 5`, `$204 = 1`, `$40` 102/103/120, `$M23` đổi | `bo_chon_ho_so`; `$M23` về giá trị gốc |
| 6 | Kiểm luật "$15 tự về 0" | ở màn 2: chỉ ghi `$15 = 5` (không `$204`) | đọc lại 0 trong < 1 s | — |
| 7 ✅ 15/10 | Đổi chế độ | `che_do auto` rồi `che_do save` | `$22` = 1 rồi 0; `$925`, `$928` theo | `che_do save` |
| 8 ✅ 15/10 | Đổi nhiệt charge | `nhiet_charge 175` | `$M23 = 1750` | ghi lại giá trị gốc |
| 9 ✅ 15/10 | Nút Quạt làm nguội (cơ cấu nhẹ, không nhiệt) | `HONG_DUOC_LAI=1 … co_cau quat_nguoi 1` rồi `0` | `$4` = 1, `$40` 210; rồi 0 / 211 | `co_cau quat_nguoi 0` |
| 10 | Xác nhận cảnh báo (nếu `$990 ≠ 0`) | `xac_nhan_canh_bao` | `$990 = 0`, `$991 = 0` | — |
| 11 ✅ 15/10 (2 mẻ thật) | START / Dừng KHÔNG nhiệt — chỉ khi anh cho riêng | `$M23 = 0` (bỏ auto-charge) → `bat_dau` → đọc `$40` 52→53/56 → **ngay** `dung_chuong_trinh` | `$0` 1 rồi 0; `$1` vẫn 0 | `dung_chuong_trinh`, `an_toan`, trả `$M23` |
| 12 | Trả máy | so `doc` với `thu_0.json` | mọi ô cấu hình như cũ | ghi lại ô lệch |
Bước 11 có rủi ro (RANG LƯU ⇒ xoá `0.csv`/`n.csv`): bỏ chọn hồ sơ trước, hoặc bỏ hẳn bước này nếu anh không muốn.

---

## 9. CHƯA XÁC MINH (cách kiểm)
1. ~~Đổi sang màn phụ bằng `$49`~~ — ĐÃ XÁC MINH 15/10 15:52: được (`$21 = 14`).
2. ~~`$49` cần về 0?~~ — ĐÃ XÁC MINH 15/10 16:53: panel tự trả `$49 = 0` sau khi chuyển màn ⇒ ghi lại cùng số vẫn chuyển.
3. ~~`chon_ho_so` đủ 2 ô~~ — ĐÃ XÁC MINH 15/10 15:52: `$200 = 1` rồi `$15 = 1` ở màn 6 ⇒ `$15` giữ 1 (cả sau khi về màn 2), board nạp ngay (mã 120 vì thẻ CHƯA có `1.csv`). Luật trả về cũng xác minh: ở màn 2 ghi `$15 = 2` khi `$201 = 0` ⇒ đọc lại 0 sau ~0,3 s. ⚠ Nạp (kể cả hỏng) ghi `$M23 = 1800` — có thể tới MUỘN sau khi về màn 2 (15:52:57 đã đặt 1700 vẫn bị đè 1800) ⇒ đặt `$M23` SAU khi `$40` báo xong nạp và đọc lại sau ≥ 3 s.
4. Chuỗi ASCII byte thấp trước — ĐÃ XÁC MINH phần máy 15/10 16:50 (ghi/đọc lại "1510 M1 500g", "thu1" khớp); còn chờ anh nhìn màn Hồ sơ.
5. ~~`$M29 = 1` + `$M28 = 50` kẹp Nhiệt %~~ — ĐÃ XÁC MINH 15/10: KHÔNG kẹp ở máy điện (`$M36 = 100` ⇒ `$66` đọc 100,0 lúc 15:04; đề 3 chạy 72 %).
6. START RANG LƯU khi `$15 = 0` ghi `0.csv` — ĐÚNG theo code (`Program.h:267`, không chốt `$15 ≥ 1`); không thử (xoá 0.csv). Luật: chọn hồ sơ trước khi START.
7. `$964..$966` — 15/10: 540/2089/1841 đứng yên khi số đo đổi, firmware không ghi ⇒ HMI tự tính; nguồn cụ thể phải mở .dpa.
8. Macro nút Xoá xoá tên hồ sơ 1 (`FILL($M100, 0, 30)`) thay vì hồ sơ đang chọn — xem trên giả lập, không thử máy thật.
9. ~~Ô `$106/$109` vô tác dụng~~ — ĐÃ XÁC MINH theo code 15/10: board chỉ đọc `$0..$40`, `$59..$85`, `$M1..$M63` (+ `$0..$11` nhanh).
10. Macro "Set Low Security" màn 5 (`BITOFF $5000.0`) làm gì.
