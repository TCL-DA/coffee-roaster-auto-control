# Đợt 14 — Cài đặt tự lưu, xuất/nhập file cài đặt, trục khung dự kiến, con trỏ lag

14/09/2026 chiều. Chủ máy giao, Claude làm. Phạm vi: `OTL Roast Lab.html`, `tools/roast_lab_hmi.py`,
bộ kiểm mới `tools/test_ui_caidat_tuluu.py`. Sao lưu trước khi sửa:
`docs/ui/backup/OTL Roast Lab.pre-caidat-tuluu-0914.html` (bung từ EXE đang dùng, md5 `4b866211…`).

## 1. Trục nhiệt độ + trục RoR của khung "Đường rang dự kiến" theo Cài đặt

Trước: khung xem trước trong hộp **Sửa hồ sơ** tự co giãn trục theo dữ liệu (nhiệt ±12 °C quanh
đường, RoR ±trị tuyệt đối lớn nhất) — cùng một hồ sơ nhìn khác hẳn đồ thị lúc rang.

Nay dùng đúng luật đồ thị màn Rang, đọc từ **Cài đặt → Model nhiệt**:

| Ô cài đặt | Khung dự kiến |
|---|---|
| Nhiệt tối thiểu / tối đa | biên trục nhiệt |
| Tự nới theo mẻ = Tự động | đường vượt khung thì trục chỉ NỚI ra (bội số 50 °C), không bao giờ mất đường |
| Tự nới theo mẻ = Cố định | khoá cứng, điểm ngoài khung bị kẹp vào mép |
| RoR tối thiểu / tối đa | biên trục RoR, luôn cố định; nhãn phải ghi `RoR +max`, `0`, `−min` |

Tiêu đề hai mục trong Cài đặt ghi rõ "đồ thị màn Rang và khung “Đường rang dự kiến”".

## 2. Con trỏ chuột lag sau khi mở app

### Cách đo

Chromium không đầu (Playwright) mở app ở trạng thái giống máy chủ máy (cầu nối báo lỗi COM9 chưa
cắm), rê chuột liên tục, đo khoảng cách giữa các khung hình (`requestAnimationFrame`) và độ trễ
`pointermove`. Chạy 2 cấu hình: vẽ bằng phần mềm (gần với GPU tích hợp yếu) và GPU rời thật.

Loại trừ trước:
- Luồng JS nhàn rỗi: không có long task sau khởi động; tải script ~25 ms / 6 giây mỗi tab.
- WebView2 của app đang chạy trên máy: ~0,05 s CPU / 10 giây.
- Cầu nối: chỉ mở đúng cổng đã chọn (COM9), thiếu cổng thì hỏng ngay, không dò cổng Bluetooth.

### Nguyên nhân

Màn đăng nhập (màn đầu tiên khi mở app) có:
- lớp phủ toàn màn `backdrop-filter: blur(12px)`;
- hộp đăng nhập `blur(26px)` nằm đè lên đường cong nền **vẽ dần trong ~17 giây**.

Blur phía sau phải tính lại mỗi khi thứ gì bên dưới vẽ lại. Kết quả: mỗi khung hình trong 17 giây
đầu, rồi mỗi giây một lần (đồng hồ).

| Màn đăng nhập, rê chuột 5 giây | Khung > 34 ms | p95 khung | Trễ pointermove TB |
|---|---|---|---|
| Trước, vẽ phần mềm | 100/100 | 117 ms | 29 ms |
| Trước, tắt blur (thử) | 6/420 | 17 ms | 10 ms |
| **Sau khi sửa, vẽ phần mềm** | **0/436** | **17 ms** | **8 ms** |
| Trước, GPU rời GTX 1650 Ti | 1/421 | 17 ms | 9 ms |

Các tab sau đăng nhập đều mượt ở cả hai cấu hình (0 khung chậm), trước và sau.

### Sửa

- `.overlay`, `.loginbox`, `#personalDialog::backdrop`: bỏ `backdrop-filter`, nền pha đặc hơn
  (lớp phủ 55% → 80%, hộp đăng nhập 72% → 93%) để chữ phía sau không đọc lẫn.
- `tools/roast_lab_hmi.py`: thôi xoá thư mục `GPUCache` mỗi lần mở app (đó là bộ đệm shader của card
  đồ hoạ, không chứa trang cũ). Vẫn xoá `Cache`, `Code Cache`, `Service Worker` như trước.

Chưa đo trực tiếp trong WebView2 của EXE trên máy xưởng — cần chủ máy mở app xác nhận.

## 3. Cài đặt tự lưu

- Bỏ bộ nút **Hủy / Áp dụng / Lưu**. Đổi ô nào thì 0,6 giây sau ô đó được lưu bền và áp ngay (y như
  bấm Lưu cũ). Bấm ± liền tay chỉ lưu một lần lúc ngừng tay → nhật ký một dòng.
- Chân trang: chấm + dòng trạng thái (xám chờ · cam đang lưu · xanh "Đã tự lưu N thay đổi · giờ" ·
  đỏ chưa lưu được khi cổng máy rang trùng cổng cân) và 3 nút **Hoàn tác · Nhập file · Xuất file**.
- **Hoàn tác** trả mọi ô về đúng như lúc vừa mở trang Cài đặt (hỏi xác nhận).
- Rời trang giữa nhịp chờ: lưu nốt ngay, không rơi thay đổi.
- **Đang rang hoặc đang làm nóng**: tự lưu KHÔNG đổi cổng/baud (cầu Modbus sẽ ngắt giữa mẻ) — ô trả
  về giá trị cũ và báo thợ.
- Cổng/baud chỉ đẩy xuống cầu nối khi lần lưu đó đổi đúng hai ô ấy. Trước đây mỗi lần Lưu đều so lại
  với cầu nối — với tự lưu, đổi một ô trục đồ thị cũng có thể kéo cầu nối về cổng cũ.

## 4. Xuất / nhập file cài đặt

File CSV chữ (UTF-8 có BOM — Excel mở không vỡ dấu), tên `OTL-cai-dat-YYYYMMDD-HHMM.csv`:

```
# OTL Roast Lab — file cài đặt app · định dạng otl-settings 1 · xuất lúc …
nhom,khoa,gia_tri,mo_ta
app,ch_tmax,300,Nhiệt tối đa (°C)
may,chargeDuration,5,Thời gian xi-lanh nạp · $M1 (giây)
```

- Nhóm `app` = mọi ô trang Cài đặt; nhóm `may` = form tham số $M.
- Nhập: tự nhận dấu `,` hoặc `;` (Excel đặt vùng Việt Nam) và số thập phân dấu phẩy. Số ngoài dải bị
  kẹp về dải của ô; khoá lạ và lựa chọn không có trong danh sách bị bỏ. Hộp xác nhận báo đủ các con số
  **trước khi** áp.
- **Không nhập** cổng COM và baud — số cổng là của từng máy tính.
- Tham số $M khi nhập **chỉ điền form** trang Cài đặt máy (ô khác máy hiện vàng), **không ghi xuống
  máy** kể cả khi đang nối máy. Ghi $M vẫn phải bấm "Ghi xuống máy".
- App dùng hộp Lưu/Mở của Windows (`settings_export` / `settings_import` trong `roast_lab_hmi.py`);
  web LAN / trình duyệt thì tải xuống và chọn file của trình duyệt.

## Bộ kiểm

- `tools/test_ui_caidat_tuluu.py` — 10 mục, 45 phép kiểm (có ca CSV kiểu ANSI dấu thanh rời), ĐẠT.
- `tools/test_settings_file.py` — hộp Lưu/Mở giả: BOM UTF-8, tên file sạch, file ANSI, trần 1 MB,
  huỷ, không cửa sổ — ĐẠT (cùng `test_style_export.py`).
- Toàn bộ 32 file `tools/test_ui_*.py` chạy tuần tự: ĐẠT. Lưu ý chạy bộ kiểm với
  `PYTHONIOENCODING=utf-8` khi dồn đầu ra vào file — 9 file không tự đặt UTF-8 cho stdout, in tiếng
  Việt ra file sẽ vỡ `UnicodeEncodeError` (lỗi của cách chạy, không phải của app).

## Build

`tools/dist/OTL Roast Lab HMI.exe` — md5 HTML nhúng `6daf7758…` khớp bản trên đĩa. Bản trước:
`tools/dist/OTL Roast Lab HMI.before-caidat-tuluu-20260914.exe`. Chưa commit.

## Chờ chủ máy

1. Mở app trên máy xưởng, xác nhận con trỏ hết lag.
2. Xuất file cài đặt, mở bằng Excel sửa thử một ô, nhập lại.
