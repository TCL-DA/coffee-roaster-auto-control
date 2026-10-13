# *Refactoring UI* (Wathan & Schoger) — CHỈ là bản tóm tắt của Bookey

Nguồn: `F:\Project\112_Quanly\Book\Design\849866466-Refactoring-UI-PDF.pdf` (36 trang, đọc 100%).
⚠ File KHÔNG phải sách gốc (~218 trang): 4 trang quảng cáo, 3 trang bị cắt ("Install Bookey App to Unlock Full Text"),
không có hình ví dụ nào của tác giả. Lời văn là của người tóm tắt → chỉ rút được luật chung, độ tin thấp hơn hai nguồn kia.
Muốn có chiến thuật cụ thể của sách (thang khoảng cách, chọn sắc độ màu, nhấn/giảm nhấn…) cần bản gốc.

## Luật chung rút được (`data/design-books.csv`)
- Ngôn ngữ hình ảnh nhất quán = style guide/design system: nút chính/phụ cố định, cỡ chữ tiêu đề/thân cố định, cùng thanh điều hướng mọi trang (`style-guide-system`, `consistent-nav-bar`).
- Khoảng trắng là phần tử tích cực; lưới + căn hàng; phân cấp bằng cỡ/đậm/màu/vị trí; phần phụ nhỏ hơn, nhạt hơn (`whitespace-hierarchy`).
- Ít màu gốc rồi sinh sắc độ; nền trung tính để điểm nhấn nổi; màu cho trạng thái và hành động chính/phụ; đỏ = lỗi, xanh lá = thành công; tương phản WCAG; không dựa màu đơn thuần; thử ở nhiều màn hình/ánh sáng (`limited-palette`, `color-not-sole`).
- Chữ: đọc được là trên hết; thang cỡ chữ nhất quán; line-height đủ.
- Dashboard: cái quan trọng trước, đào sâu khi cần; đừng nhồi tính năng (`dashboard-important-first`).
- Lặp + thử với người dùng; khảo sát, phỏng vấn, quan sát; RICE để xếp ưu tiên; làm từng đợt nhỏ.

## ⛔ Bác bỏ cho OTL
- "Bóng, viền mảnh, gradient nhẹ để tạo chiều sâu" → **trái bộ áo OTL** (phẳng, cấm gradient/bóng). Chuẩn chủ máy thắng.
- "Xanh lá = thành công" → trên HMI, trạng thái chạy/tắt dùng độ sáng + chữ (Hollifield), không dùng xanh/đỏ.
