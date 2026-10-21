# Áp dụng feedback qua Open Design — lượt đầu

## Cập nhật bố cục lượt hai

Đã áp dụng thêm `typography-hierarchy.md` của Open Design: BT là điểm nhìn chính, thời gian mẻ có kích thước lớn, thiết bị phụ có vùng cuộn riêng ở cột phải. Ba đầu ra cùng cột với biểu đồ; thanh thao tác xếp Xả liệu và Kết thúc mẻ về bên phải, tách khoảng cách. Màu mặc định OTL dùng cam ấm cho điểm nhấn, BT cam và ET xanh; vẫn giữ lựa chọn màu riêng. Màn thấp dùng thẻ thời gian ngang để dành chỗ cho thiết bị phụ.

Đạt thêm test_ui_roast_columns ở bốn kích thước: căn cột, cuộn và chạm các thiết bị cuối danh sách, thu gọn/mở lại. Các kiểm tra consistency, toolbar, workflow, dialog_layout, personalization và open_design_feedback đều đạt. Không thay logic gửi lệnh hoặc tự xả.

Nguồn tham khảo: `claude-design-feedback/Menu cài đặt nhanh - Lỗi thiết kế (1)/Rang - Sửa lại.dc.html`.
Đã sử dụng tài nguyên Open Design tại `F:/Project/open-design/craft`: accessibility-baseline, animation-discipline và state-coverage. Mục design-review là bản giới thiệu upstream, không phải workflow đã được chạy. Không chạy engine AI của ứng dụng Open Design trong lượt này.

## Đã sửa

- Menu nhanh có tiêu đề, nhóm tùy chọn, nhóm điện thoại và nhóm tài khoản; chiều cao theo vùng màn hình còn lại, không tràn ngang.
- Địa chỉ LAN xuống dòng riêng, nút sao chép riêng; nút bật web và âm thanh có trạng thái switch cho công cụ hỗ trợ.
- Đăng xuất trung tính, thoát ứng dụng có đường viền riêng; menu thoát từ chối khi đang rang, vẫn xác nhận hai lần khi máy rảnh.
- Gas/gió/trống xếp nhãn trên số, giảm bề ngang nút ± nhưng giữ vùng chạm tối thiểu. Thiếu dữ liệu có mô tả và ẩn đơn vị phần trăm.
- Thiết bị phụ thu gọn thành hàng có khoảng cách; kết thúc mẻ tách khoảng và viền khỏi các thao tác khác.
- Đồng hồ trên cùng chỉ hiện giờ/phút. Vùng chọn hồ sơ giữ hai lựa chọn nhanh và một nút mở danh sách, tránh cắt hàng thứ hai ở màn thấp.
- Ghi nhớ yêu cầu sử dụng Open Design trong AGENTS cá nhân và dự án.

## Kiểm chứng

Đạt test_ui_consistency, test_ui_toolbar, test_ui_dialog_layout, test_ui_workflow và test_ui_open_design_feedback. Các kiểm tra dùng trình duyệt và cầu máy giả lập; không gửi lệnh tới máy rang thật. Đã xem ảnh nội bộ để kiểm bố cục; không tạo bộ ảnh bàn giao.

## Phạm vi

Đây là lượt áp dụng ưu tiên menu nhanh và màn rang, chưa sao chép toàn bộ màn tổng quan của bản mẫu. Chưa thay hành vi Xả liệu/Kết thúc mẻ thành giữ một giây; đó là thay đổi luồng vận hành cần kiểm chứng riêng với các trạng thái cửa đang mở/đóng và tự xả. Không sửa firmware, không đổi cấu hình hay dữ liệu cá nhân hóa đã lưu.
