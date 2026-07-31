# Findings — Kiểm kê tính năng CÓ SẴN & điểm ma sát UX

> Nguồn: đọc trực tiếp `OTL Roast Lab.html` + roast_lab_hmi.py (phiên 2026-07-24).
> Mục tiêu: nâng UX cho **cái đã có**, không thêm module kinh doanh mới.

## La bàn người dùng
Thợ rang: mắt ở TRỐNG/hạt/trier (không ở màn), đứng cách panel 1–2m, tay bận+đeo găng,
xưởng nóng-ồn-chói, lặp ~60 thao tác/ngày, mẻ 12–18′ căng, nhiều ca/nhiều thợ.

## Kiểm kê tính năng hiện có (6 tab + xuyên suốt)

| Tab / Vùng | Đang có gì | Ma sát UX quan sát được |
|---|---|---|
| **Tổng quan** | Dashboard liếc nhanh | Chưa rõ số nào là "phải nhìn" khi rang |
| **Rang** | BT/ET/RoR live, chart, phase, nút máy (gas/gió/trống, nạp/xả/nguội/afterburner), mốc TP/DE/FCs/DROP | Số chưa đủ to để đọc từ xa; đổi mốc chỉ báo bằng MẮT; nút máy cần liếc; canh crack phải dán mắt |
| **Hồ sơ** | Thư viện hồ sơ, sửa, xuất CSV/PDF, lưu thư mục, nhiệt charge/xả | Nhập liệu bằng bàn phím; nhiều bước lưu |
| **Lịch sử** | Mẻ từ SQLite, modal stats (DTR/AUC/RoR), so ≤6 mẻ, xuất CSV, cupping (mới) | Bảng nhiều cột; thao tác xem chi tiết nhiều chạm |
| **Kho & Kinh doanh** (mới GĐ4) | Lô/đơn/chi phí/cupping, báo cáo | Nhập liệu nặng (đã tính cho web phụ) |
| **Cài đặt** | Kết nối COM/baud, calib gas, model nhiệt, log, nhật ký, tài khoản | Khoá sau PIN; ít đụng khi rang |
| **Xuyên suốt** | Auth PIN, theme (accent + sáng/tối), i18n vi/en, web LAN clone, **âm chạm (mới)**, banner FAULT, demo, `data-help` (chú thích) | Phản hồi chủ yếu THỊ GIÁC; chưa dùng tai; chưa có nhìn-từ-xa; chưa tối ưu găng tay |

## Tài sản có thể TÁI DÙNG cho nâng UX (không phải làm từ đầu)
- **Web Audio đã dựng** (`SND`/`_metal`/`snd`) → mở rộng ra âm mốc rang + nhịp RoR.
- **Web Speech API** (trình duyệt WebView2 có sẵn) → giọng nói tiếng Việt, không cần thư viện.
- **Design tokens** (`--fs-*`,`--ok/warn/danger`,`--accent`) → phóng to số, tô màu vùng RoR dễ.
- **Bus sự kiện + snapshot mỗi giây** → biết mốc/RoR real-time để phát âm/đổi màu.
- **`data-help` sẵn khắp nút** → nâng thành tour/chế độ mới-tập, không phải gắn lại.
- **Chart canvas + phase state** → thêm đếm ngược mốc, thanh tiến trình.
- **localStorage per-thiết bị + state.json** → hồ sơ theo thợ (theme/âm/bố cục/tay thuận).

## Nguyên tắc
- Nâng UX = làm cái đã có DỄ DÙNG HƠN, KHÔNG thêm việc/không thêm module kinh doanh.
- Ưu tiên: **tai thay mắt → nhìn-lướt-từ-xa → ít chạm/tha lỗi → thoải mái/dễ học**.
- Mọi thứ offline, giữ 1-file HTML, dùng token, cấm gradient nút, giữ theme workshop.
