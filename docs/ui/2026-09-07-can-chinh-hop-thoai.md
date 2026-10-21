# Căn chỉnh bố cục và hộp thoại

Đã mở rộng kiểm tra từ các tab chính sang 10 hộp thoại: sửa hồ sơ, công thức nạp,
cân, mức rang, chi tiết mẻ, so sánh mẻ, cổng kết nối, xác nhận, bàn phím và bàn phím số.

Các sửa đổi:

- Giới hạn chiều cao hộp thoại theo khung chứa thay vì `vh`. Khung ứng dụng đã
  được thu nhỏ nên dùng `vh` tại đây làm vùng nhập liệu bị thu nhỏ thêm một lần.
- Hộp chi tiết/so sánh có chiều rộng riêng; nhãn dài được xuống dòng, không ép
  nút đóng ra ngoài khung.
- Căn cột nhãn và giá trị của biểu mẫu; cho nội dung co lại đúng chỗ. Cửa sổ dưới
  1100 px chuyển biểu mẫu hai cột thành một cột, phần xem trước nằm sau phần nhập.
- Nhóm hướng dẫn và phản hồi lệnh dùng chiều cao cố định. Thông báo xuất hiện
  không làm đổi vị trí cụm gas/gió/trống.
- Thống nhất khoảng cách của nhóm bộ lọc, phân trang và thanh hành động.

Kiểm chứng: `test_ui_consistency.py` kiểm 6 tab, 7 trang cài đặt, sáng/tối ở ba
kích thước. `test_ui_dialog_layout.py` kiểm 10 hộp thoại ở 1920×1080, 1366×768,
1280×800 và 1024×768; đo thêm vị trí điều khiển trước/sau khi hiện thông báo.
Các kiểm tra luồng rang và thao tác toolbar được chạy lại bằng cầu máy giả.

Không thay firmware, không phát lệnh máy thật và không tạo ảnh/video bàn giao.
