# Hollifield — *A High Performance HMI: Better Graphics for Operations Effectiveness* (ISA 2012)

Nguồn: `F:\Project\112_Quanly\Book\Design\The High Performance HMI Pages 1-27 - Flip PDF Download _ FlipHTML5.pdf`.
⚠ Đây là BÀI BÁO 27 trang (đã đọc 27/27 qua ảnh), KHÔNG phải cả cuốn *The High Performance HMI Handbook* (2008).
Luật đã vào `data/design-books.csv`.

## Ý chính
- **"Information is data in context made useful."** Màn toàn số bắt người vận hành so từng số với bản đồ trong đầu → phụ thuộc kinh nghiệm, khó đào tạo, phát hiện sự cố chậm (`information-not-data`).
- Màn "flashy": 90% diện tích vẽ thiết bị 3D, 10% dữ liệu. >90% màn hình thực tế không có trend, không chỉ báo tình trạng. Thử nghiệm EPRI/ASM: màn HP phát hiện bất thường TRƯỚC báo động.
- Trở ngại chính là **quán tính, không phải chi phí**.

## Lỗi thường gặp (p8)
Sơ đồ P&ID phủ số; ít trend; bơm quay/băng tải chạy/lửa động; bình 3D màu chói; tô ống theo chất; mức lỏng tô chói cả bề rộng;
đường cắt nhau, chiều dòng lộn xộn; mã màu không nhất quán; dùng màu báo động sai chỗ; điều hướng lung tung; không phân cấp màn.

## Màn High-Performance có (p8–17)
- Nền xám, 2D tương phản thấp, ít màu, màu rất cụ thể + nhất quán (`gray-background`, `no-3d-flashy`).
- **Màu chói chỉ cho bất thường; màu báo động chỉ cho báo động; màu không bao giờ là cách phân biệt duy nhất** (`color-for-abnormal-only`, `color-not-sole`).
- Trạng thái chạy/tắt = độ sáng + chữ RUNNING/STOPPED (`run-state-brightness`).
- **Báo động theo mức ưu tiên**: P1 ô vuông đỏ, P2 tam giác vàng, P3 tam giác ngược cam, P4 thoi hồng, "S" bị nén; nháy khi chưa xác nhận; truy được nguyên nhân · hậu quả · cách xử lý · thời gian phản ứng (ANSI/ISA-18.2) (`alarm-priority-symbols`).
- **Không animation** trừ hành vi báo động (`motion-only-for-alarm`).
- **Trend nhúng**: 1–2 trend/màn, có lịch sử khi mở, dải bình thường + vạch giới hạn; "bấm 1 cái ra trend" thực tế là 10–20 thao tác (`embedded-trends`).
- **Chỉ báo analog**: dải xám = vùng báo động, dải xanh nhạt = vùng mong muốn, tam giác = giá trị + số; quét 1–2 s (`analog-indicator`).
- Thanh đầy biến mất khi giá trị thấp → dùng con trỏ trên thang (`pointer-not-bar`).
- Bảng/checklist: chỉ mục bất thường nổi lên (`abnormal-pops-out`).

## Phân cấp + điều hướng (p18–20)
- **L1** tổng quan (KPI, không điều khiển) · **L2** điều khiển cụm — đủ cho hầu hết việc trên 1 màn · **L3** chi tiết thiết bị · **L4** hỗ trợ/chẩn đoán (`display-hierarchy-l1-l4`).
- Thanh điều hướng giống nhau ở mọi màn (`consistent-nav-bar`). Lệnh tới hạn (SHUTDOWN/FREEZE/ISOLATE) là nút lớn hình riêng; bảng interlock Initiator · Value · Action · Status (`big-command-buttons`).
- Sơ đồ mạng/ống: tô-pô kiểu bản đồ tàu điện, chỉ giữ cái nhiệm vụ cần (`topology-not-geography`).
- Tiêu chuẩn (API-RP-1165) viết đúng nhưng ví dụ vi phạm → theo NGUYÊN TẮC, không chép ví dụ.

## Quy trình 7 bước (p26) (`hmi-design-process`)
1. Triết lý + style guide bằng văn bản · 2. Chấm hiện trạng so triết lý · 3. Mục tiêu vận hành mọi chế độ ·
4. Phân tích nhiệm vụ → nội dung L2/L3/L4 · 5. Thiết kế theo guide · 6. Lắp, chạy thử, đào tạo · 7. Duy trì + đánh giá lại.
