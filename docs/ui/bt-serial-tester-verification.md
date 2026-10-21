# Kiểm chứng nâng cấp BT Serial Tester

Ngày 10/09/2026. Kiểm thử dùng dữ liệu biểu đồ tổng hợp, không mở COM thật.

## Trước thay đổi

Cửa sổ 1366×768, biểu đồ 850 điểm và năm mốc. Gọi `_move_marker` rồi xử lý
idle của Tk trong 30 lần đo:

- Trung vị: 55,82 ms/lần cập nhật.
- P95: 65,85 ms/lần cập nhật.
- Kích thước canvas: 1270×330 px.

Mã cũ yêu cầu vẽ lại cả biểu đồ qua `draw_idle`. Phép đo này là thời gian cập
nhật ứng dụng, không phải đo tần số quét vật lý của màn hình. Ngân sách mục
tiêu cho 60 lần cập nhật/giây là khoảng 16,7 ms.

## Phạm vi nghiệm thu

Kiểm tra bố cục Light/Dark, thu gọn log, đổi kích thước, tải biểu đồ, điều
khiển replay bằng thiết bị giả, giữ dữ liệu/profile và nhịp gửi lệnh.
Đo lại thời gian vẽ và nhịp callback trên bản mới trước khi kết luận.
