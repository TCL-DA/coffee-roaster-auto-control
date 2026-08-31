# Quy cách trình bày manual OTL

Rút từ 2 bộ manual gốc `User-manual-OTL-06-12-1.0.1_ENG.pdf` và `User-manual-Auto-v1.0.4_ENG.pdf`
(thư mục `F:\Project\112_Quanly\122_Manual_AI\`). Engine đã cài sẵn đúng các số dưới đây.

## Khổ trang

| Mục | Giá trị |
|-----|---------|
| Khổ | A4 — 595.28 × 841.89 pt (bản Auto gốc dùng Letter, bản mới thống nhất A4) |
| Lề trái/phải | 80 pt → cột chữ rộng 435.28 pt |
| Vùng chữ | y = 96 … 780 pt |
| Logo | góc trên trái, rộng 34 pt, đặt tại (80, 32) |
| Header | tên chương, canh phải, Arial 10 pt, màu xanh |
| Footer | trái `Copyright (c) O Tesla Industry CO., Ltd`, phải số trang — Arial 9 pt xanh, y = 800 |

## Chữ

| Vai trò | Font | Cỡ | Giãn dòng | Canh |
|---------|------|-----|-----------|------|
| Tiêu đề chương (H1) | Arial Bold | 19 | 24 | giữa |
| Tiêu đề mục (H2) | Arial Bold | 12.5 | 17 | trái, kèm huy hiệu tròn xanh Ø21 |
| Tiêu đề nhỏ (H3) | Arial Bold | 11.5 | 17 | trái |
| Thân bài | Arial | 11 | 18 | **đều, dòng cuối canh trái** |
| Ghi chú | Arial Italic | 10 | 16 | trái, xám |
| Chú thích ảnh | Arial Italic | 9.5 | 14 | giữa, xám |
| Ô bảng | Arial | 9.5 | 14 | trái |

Arial có đủ dấu tiếng Việt. **Arial Black thì không** — đừng dùng cho tiêu đề tiếng Việt.

## Màu

| Tên | RGB | Dùng cho |
|-----|-----|----------|
| Xanh OTL | 46, 116, 181 | header, footer, tiêu đề bảng, hộp LƯU Ý |
| Xanh huy hiệu | 74, 135, 199 | huy hiệu số mục, sơ đồ trạng thái |
| Đỏ | 192, 0, 0 | hộp NGUY HIỂM, khung chú thích trên ảnh |
| Cam | 226, 108, 10 | hộp CẢNH BÁO |
| Vàng | 255, 192, 0 | hộp THẬN TRỌNG (chữ tiêu đề màu đen) |
| Chữ thân bài | 35, 35, 35 | |
| Xám ghi chú | 120, 120, 120 | |
| Nền hàng bảng lẻ | 244, 247, 251 | |

## Phân cấp cảnh báo (ISO 3864 / ANSI Z535)

| Từ tín hiệu | Khi nào dùng |
|-------------|--------------|
| **NGUY HIỂM** (đỏ) | Nguy cơ chết người hoặc thương tích nặng, gần như chắc chắn xảy ra nếu làm sai — ví dụ nổ khí gas |
| **CẢNH BÁO** (cam) | Có thể chết người hoặc thương tích nặng — bề mặt nóng, máy tự khởi động |
| **THẬN TRỌNG** (vàng) | Thương tích nhẹ hoặc hỏng máy |
| **LƯU Ý** (xanh) | Không nguy hiểm, chỉ ảnh hưởng chất lượng mẻ rang hoặc tuổi thọ máy |

Mỗi hộp: một dòng nêu hậu quả trước, rồi các gạch đầu dòng nêu việc phải làm.

## Bố cục quen thuộc của bộ manual gốc

- Mục con đánh số bằng **huy hiệu tròn xanh** ①②③ đặt trước tiêu đề.
- Bước thao tác: **ảnh nút bấm nằm ngay dưới câu lệnh**, không nằm chen giữa dòng chữ.
- Ảnh màn hình lớn thì khoanh **khung đỏ bo góc + huy hiệu số**, bên dưới liệt kê giải nghĩa
  từng số (hàm `IMGC`).
- Bảng sự cố luôn 3 cột: Hiện tượng | Nguyên nhân có thể | Cách xử lý.
- Chương kết thúc bằng phụ lục tham số kỹ thuật, ghi rõ chỉ kỹ thuật viên được đổi.

## Đánh số trang

Chương rời cắm vào bộ manual chung thì đánh số riêng theo tiền tố chương
(ví dụ `PH-1`, `PH-2`…) để không đụng số trang của bộ gốc. Sửa ở hàm `decorate()` trong engine.
