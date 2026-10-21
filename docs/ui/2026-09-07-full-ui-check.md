# Rà soát giao diện Roast Lab — 07/09/2026

Áp dụng quy tắc Open Design cục bộ về bố cục, phân cấp, khả năng thao tác và trạng thái dữ liệu. Không chạy engine Open Design.

## Phạm vi đã kiểm

- Sáu tab chính và bảy trang cài đặt; nền sáng/tối tại 1920×1080, 1366×768 và 1280×800.
- Mười hộp thoại tại bốn kích thước; cá nhân hóa có thêm kích thước điện thoại.
- Tìm/lọc/so sánh hồ sơ; lịch sử rỗng, lỗi, phân trang, chống phản hồi cũ ghi đè.
- Luồng làm nóng, lưu mẻ, ghi chú và hồ sơ chuẩn; quyền không đổi hồ sơ giữa mẻ.
- Màn Rang, menu bổ sung, chế độ đơn giản, nhập mức trực tiếp, thiết bị phụ, mất kết nối.
- Cổng serial giả, gió theo Pa, RoR, tự xả; không gửi lệnh đến máy thật.
- Từ điển 167 khóa mỗi ngôn ngữ và chuyển ngôn ngữ trên sáu tab.

## Sửa trong đợt này

- Ẩn chú giải đồ thị khi chưa chọn hồ sơ.
- Dịch tiêu đề thiết bị phụ và nhãn xác nhận khi chuyển ngôn ngữ.
- Tăng vùng bấm chip kết nối và ô chọn hồ sơ theo tỷ lệ thu phóng, đạt 44 px trong bài kiểm tra.

## Kết quả

Các bộ kiểm tra `consistency`, `dialog_layout`, `workflow`, `personalization`,
`layout_motion`, `open_design_feedback`, `portpick`, `roast_columns`,
`match_reference`, `vacuum`, `ror`, `autodrop` và `audit` đạt.
Kiểm tra toàn tab không phát hiện tràn/chồng phần tử; bài kiểm ngôn ngữ không còn nhãn hệ thống tiếng Việt trên các màn tiếng Anh đã quét.

Đây là phạm vi kiểm thử cụ thể, không phải cam kết mọi trạng thái phần mềm đều không có lỗi. Chưa xác nhận vận hành phần cứng thật hay toàn bộ cấu hình Windows/DPI của khách hàng.
