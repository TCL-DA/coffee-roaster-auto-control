# Nâng cấp OTL Roast Lab — 07/09/2026

Bản nâng cấp nằm trong `OTL Roast Lab.html`, cầu desktop `tools/roast_lab_hmi.py`
và phần truy vấn lịch sử `tools/roast_db.py`. Không thay firmware trong đợt này.

## Những thay đổi sử dụng được

- **Tổng quan:** hồ sơ yêu thích, mẻ gần nhất, mở chi tiết và chuẩn bị rang lại.
  Thẻ chính hướng dẫn chọn hồ sơ, kết nối máy, làm nóng hoặc xem tổng kết tùy trạng thái.
- **Màn rang:** chế độ Tập trung tự bật trên màn dưới 1600 px, có nút đổi và nhớ
  lựa chọn. Đồng hồ, đánh lửa và gas/gió/trống được cố định; thông số phụ cuộn riêng
  khi thiếu chỗ. Dải thiết bị vẫn có nút ghim/thu gọn.
- **Hướng dẫn thao tác:** thông báo thiếu kết nối, quyền PC control, nhiệt BT hoặc
  nhiệt nạp. Nhiệt đạt ngưỡng chỉ là điều kiện về BT; người vận hành vẫn kiểm tra
  máy và chủ động bắt đầu.
- **Lệnh máy:** hiện đang gửi, cầu nối đã nhận, trạng thái máy đã khớp hoặc chưa xác
  nhận sau 10 giây. Cần snapshot mới sau khi cầu nhận lệnh; cờ thiếu/null không được
  hiểu là trạng thái TẮT. Những lệnh không có giá trị phản hồi tương ứng không được
  báo đã xác nhận.
- **Hồ sơ:** tìm theo tên/mức rang/ghi chú/thợ, không phân biệt dấu; chọn hai hồ sơ
  để so sánh. Thẻ có đường BT thu nhỏ từ dữ liệu đã ghi hoặc mẻ nền đã ghim; thiếu
  dữ liệu thì ghi rõ. So sánh có cả nhiệt nạp, nhiệt xả đặt, thời gian đặt và ghi chú.
- **Lịch sử:** tìm mã mẻ/hồ sơ/thợ trong toàn kho SQLite; lọc khoảng ngày, phân trang
  50 mẻ. Giữ lựa chọn so sánh khi sang trang khác. Kho rỗng/lỗi không hiện mẻ mẫu.
- **Sau mẻ:** đường BT đã ghi, thời gian, nhiệt xả và DTR; thiếu FCs hoặc thiếu mẫu
  nhiệt thì để trống phần không tính được. Ghi chú lưu cùng mẻ và xem lại trong
  chi tiết/QC. Có thể tạo hồ sơ chuẩn mới từ mẻ thật đã lưu hoặc chuẩn bị rang lại.
- **Phong cách:** Studio, Night, Cát ấm, Rừng sâu; lưu tối đa 12 phong cách có tên;
  nhập/xuất JSON chứa giao diện, ảnh nền và âm thanh. Desktop dùng hộp lưu Windows.
  Gói nhập không thay tài khoản, cấu hình hay quyền điều khiển máy.
- **Theo tài khoản:** giao diện và âm thanh tự nhớ theo tên người đăng nhập trên
  thiết bị. Ảnh nền vẫn chịu giới hạn dung lượng lưu cục bộ; nếu đầy, app báo lỗi.

## Lỗi được xử lý

- Không đổi hoặc xóa hồ sơ trong lúc đang rang, tránh thay chỉ số hồ sơ của mẻ dở.
- Bảng làm nóng chuyển sang đọc BT thật khi có cầu máy; mô phỏng được ghi rõ và
  dừng ngay khi cầu xuất hiện. Nhiệt tham chiếu tại bảng này không phải lệnh đặt máy.
- Khi mất kết nối, số nhiệt trực tiếp không chuyển sang đường nhiệt mô phỏng.
- Tổng kết không lấy FCs dự kiến để tính DTR thực tế; tránh chia cho 0.
- Lỗi lưu cache không chặn thao tác chốt mẻ xuống kho thật.
- Kết quả tìm kiếm cũ không ghi đè kết quả của bộ lọc mới.
- Nhập phong cách kiểm cấu trúc, dải giá trị và ảnh; lỗi dung lượng khôi phục giá trị
  lưu trước đó. Đổi tài khoản hoặc chọn phong cách mới hủy lượt áp dụng ảnh cũ.
- Cụm điều khiển không bị cắt dưới mép màn, kể cả khi có áp hút và chỉ báo lửa.

## Kiểm chứng và phạm vi

Kiểm bằng Chromium, WebView2 và SQLite tạm; cầu Modbus được mô phỏng. Không phát
lệnh tới máy thật và không flash firmware. Các bộ kiểm mới:

```powershell
python tools/test_ui_workflow.py
python tools/test_roast_history_search.py
python tools/test_style_export.py
```

Đã chạy lại các kiểm tra cá nhân hóa, bố cục/chuyển động, toolbar, RoR, áp hút,
tự xả, dữ liệu live, chế độ tương thích, chọn cổng và giải mã PC_Link.
Bố cục kiểm ở 1920×1080, 1366×768 và 1280×800; bảng cá nhân hóa kiểm thêm màn hẹp.
Bộ kiểm cũ vẫn có nhắc nhở kích thước một số nút phụ; cần phân biệt với lỗi tràn/đè.

Mở lại bản phát triển bằng `python tools/roast_lab_hmi.py` để nạp cả HTML và API mới.
Nếu dùng `.exe` cũ, cần đóng gói lại vì HTML được nhúng trong gói. Không khởi động
lại ứng dụng giữa một mẻ đang chạy.

Báo cáo bàn giao chỉ bằng chữ theo tùy chọn của người dùng; không tạo ảnh/video review.
