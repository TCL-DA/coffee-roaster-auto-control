# BT Serial Tester — đánh giá và chỉ dẫn nâng cấp

Yêu cầu ngày 10/09/2026: chỉnh UI/UX đẹp, dễ dùng, chuyển động hướng tới 60 Hz,
build EXE. Nguồn đúng: `tools/bt_serial_tester_glass.py` theo
`tools/BTSerialTester.spec`. Đây không phải OTL Serial Terminal hay Roast Lab.

## Quan sát và hướng sửa

- Ảnh người dùng: header và cấu hình chiếm gần 300 px chiều cao; nút đóng cổng
  nằm xa trạng thái kết nối. Gom tên app/trạng thái thành header gọn và đặt
  Open/Close cạnh cấu hình để quan hệ thao tác–kết quả rõ ràng.
- Biểu đồ chỉ cao khoảng 220 px giữa vùng replay rất rộng; mã root đặt weight
  ở hàng log thay vì vùng làm việc. Cho vùng replay/biểu đồ nhận chiều cao dư,
  log có chiều cao hữu hạn và có thể thu gọn.
- Chữ nhãn trạng thái và pha nhỏ; màu xám nhạt trên nền trắng khó đọc. Tăng chữ
  nhãn, nâng tương phản chữ phụ, nhóm BT thiết bị/BT mục tiêu/RoR/pha theo cùng
  nhịp khoảng cách và đơn vị rõ ràng.
- Start/Stop/Reset cùng hàng với tốc độ và trần RoR khiến vùng hẹp dễ tràn.
  Tách điều khiển chính khỏi thiết lập biểu đồ, giữ Stop dễ thấy ở mọi kích thước.
- Các dải pha và mốc CHARGE/TP/DE/FCs/DROP có ích cho người rang; giữ nội dung
  này, giảm sắc độ nền pha và tránh nhãn đè nhau/đụng mép trên biểu đồ.

Theo nguyên tắc phân cấp và nhóm gần nhau, ưu tiên đọc: kết nối → chỉ số →
đường cong → hành động. Phong cách đề xuất (lựa chọn thẩm mỹ): nền slate nhạt,
card trắng, xanh dương làm điểm nhấn; Dark dùng slate tối, giữ tương phản chữ.
Không cần ảnh trang trí, hiệu ứng trong suốt giả hay hoạt ảnh trên số đo.

## Hiệu năng và tiêu chí nghiệm thu

- Hiện `_move_marker` gọi `canvas.draw_idle()` mỗi lần; thay bằng background
  cache/blitting và con trỏ nội suy theo thời gian monotonic ở mục tiêu 60 Hz.
- Không tăng tần suất TX thiết bị lên 60 Hz. Giữ bước lệnh, tốc độ replay,
  giới hạn MAX_STEP_TENTHS và ngữ nghĩa thuật toán RoR.
- Thread replay không được gọi widget/Tk/after/messagebox; gửi dữ liệu UI qua
  queue, UI lấy mẫu và vẽ trên main thread. Stop phải đánh thức worker đang đợi.
- Khi nghỉ không chạy vòng vẽ 60 Hz vô ích. Resize/theme/profile change phải
  làm mới cache đúng, tránh bóng con trỏ cũ và giữ đúng vị trí replay.
- Bounded xử lý log mỗi nhịp và giới hạn lịch sử hiển thị để RX dồn không làm
  treo UI. Giữ thao tác gửi tay, hotkey, CSV, tốc độ tự do, trần RoR, offset.
- Kiểm tra bố cục ở 1040×820, 1366×768 và 1920×1080, cả Light/Dark.
- Đo khoảng thời gian callback và thời gian vẽ với dữ liệu giả, không mở COM
  thật. Báo số đo và giới hạn; không gọi timer16ms là bằng chứng 60Hz.
- Build PyInstaller, giữ bản dự phòng rồi thay đúng EXE shortcut.

## Nguồn đối chiếu

- [Fluent 2 Layout](https://fluent2.microsoft.design/layout): dùng khoảng cách
  để thể hiện nhóm chức năng và phân cấp.
- [Fluent 2 Typography](https://fluent2.microsoft.design/typography): căn hàng,
  chữ có phân cấp và dễ đọc.
- [Matplotlib blitting](https://matplotlib.org/stable/users/explain/animations/blitting.html):
  lưu nền tĩnh, chỉ vẽ lại thành phần thay đổi.

Tự rà: mỗi vấn đề trên có bằng chứng từ ảnh/mã và hướng sửa; bảng màu là lựa
chọn thẩm mỹ, hiệu năng cần xác minh bằng đo đạc. Ba ưu tiên là bố cục biểu đồ,
nhóm điều khiển và đường cập nhật UI có giới hạn thời gian.
