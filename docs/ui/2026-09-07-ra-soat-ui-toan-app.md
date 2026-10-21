# Rà soát và sửa giao diện toàn ứng dụng

## Nhận xét từ ảnh và kiểm tra trực quan

Mục tiêu là thao tác rang dễ hiểu, thông số rõ và phong cách nhất quán. Ảnh người
dùng cho thấy các nâng cấp trước đã làm tăng mật độ và hiệu ứng mà chưa thống nhất
thứ tự đọc. Các kiểm tra không tràn bố cục trước đó chưa đủ để kết luận giao diện tốt.

1. Lớp mờ của màn chưa chọn hồ sơ dùng tọa độ cố định, lệch khỏi biểu đồ sau khi
   thêm thanh hướng dẫn/chế độ tập trung. Đã đặt màn chờ vào đúng khung biểu đồ,
   dùng nền kín; màn đã chọn hồ sơ dùng thẻ chuẩn bị gọn, giữ đường nền rõ nét.
2. Bốn hồ sơ gợi ý xuống hàng không đều. Đã dùng lưới hai cột, tên có giới hạn dòng,
   một nút chọn hồ sơ chính và thứ tự: tiêu đề, hướng dẫn, gợi ý, hành động.
3. Chữ đậm, bóng phát sáng, gradient và nhiều màu cùng tranh sự chú ý. Đã thống nhất
   font giao diện/số, giảm độ đậm, bỏ bóng trang trí của thẻ và số; màu dữ liệu và
   cảnh báo vẫn giữ ý nghĩa. Chọn mức tiết chế này là quyết định thẩm mỹ; sự phân
   cấp rõ giữa hành động và thông tin là yêu cầu sử dụng.
4. Thông số trên thẻ hồ sơ dồn về trái. Đã chia ba cột bằng nhau; bảng lịch sử dùng
   chữ và màu trung tính, giảm các mảng màu không cần thiết.
5. Mất kết nối nhưng nhiệt và phần trăm đầu ra vẫn giữ số trước đó. Đã xóa số trực
   tiếp ở cả thanh đầu và màn rang khi mất kết nối; trang Kết nối không còn đèn
   xanh mặc định. Không xóa dữ liệu đường cong đã ghi của mẻ.
6. Thẻ chuẩn bị mẻ chứa quá nhiều chip dự kiến. Đã gom các thông số này vào phần
   mở rộng có nhãn rõ; nhiệt nạp và hành động bắt đầu vẫn ở ngoài.

## Phạm vi rà soát

Đã xem trực quan Tổng quan, Rang, Hồ sơ, Lịch sử, Kho & Kinh doanh, Cài đặt;
kiểm thêm màn chờ có hồ sơ và giao diện tối. Đã kiểm bố cục tự động cả bảy trang
cài đặt con ở 1920×1080, 1366×768 và 1280×800, sáng/tối. Dữ liệu kiểm là dữ liệu
thử riêng; chưa chạy trên máy rang thật.

Kiểm hồi quy: `test_ui_consistency.py`, `test_ui_toolbar.py`,
`test_ui_workflow.py`, `test_ui_layout_motion.py`, `test_ui_personalization.py`.
Không tạo ảnh/video bàn giao; ảnh kiểm nội bộ nằm trong thư mục tạm.

## Cơ sở thiết kế

Đối chiếu nguyên tắc phân cấp nội dung và điều khiển trong
[Apple Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines).
Áp dụng vào app bằng cách giảm vật trang trí, giữ hành động chính rõ và nhóm các
thông số liên quan. Đây là giao diện HMI trên Windows, không sao chép vật liệu kính
hoặc hiệu ứng nếu chúng làm giảm độ rõ của số máy.

Ba trọng tâm theo dõi sau khi dùng thực tế: độ dễ đọc khi đứng xa màn, số chạm để
chuẩn bị mẻ, và khả năng tìm đúng nút khi thao tác bằng găng tay.
