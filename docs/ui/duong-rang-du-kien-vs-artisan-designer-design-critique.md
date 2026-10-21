# Đánh giá đường rang dự kiến so với Artisan Designer

Ngày đánh giá: 12/09/2026

## Kết luận

Đường rang dự kiến của Roast Lab phù hợp hơn Artisan Designer cho thợ rang cần tạo hồ sơ nhanh và vận hành hằng ngày. Artisan Designer mạnh hơn khi chuyên gia muốn tự định hình chính xác đường BT/ET bằng nhiều điểm điều khiển.

Hai tính năng không hoàn toàn tương đương. Roast Lab hiện là trình dựng mục tiêu có hướng dẫn bằng một mô hình tham số; Artisan là trình biên tập đường cong.

## So sánh chức năng

| Tiêu chí | Roast Lab | Artisan Designer |
|---|---|---|
| Cách nhập | Nhiệt nạp, nhiệt xả, tổng thời gian; DE, FCs và phát triển là tùy chọn | Kéo trực tiếp nhiều điểm BT/ET và nhập chính xác các mốc |
| Cách dựng đường | Năm neo CHARGE, TP, DE, FCs, DROP; nội suy Hermite đơn điệu | Spline qua các điểm do người dùng đặt |
| Mức linh hoạt | Thấp đến vừa; không thêm điểm hay định thời DE/FCs trực tiếp | Cao; thêm, xóa và kéo điểm tự do |
| RoR | Đạo hàm của BT ước tính | Đạo hàm của đường BT/ET do người dùng thiết kế |
| Nhập mẻ cũ | Mẻ nền dùng để phát lại gas, gió và trống; biểu đồ mục tiêu hiện chưa lấy hình dạng BT của mẻ nền | Có thể xấp xỉ profile đã rang thành các điểm Designer |
| Đầu ra | Dùng chung cho biểu đồ lúc rang, mốc, đếm ngược và giọng nói | Chuyển thành profile lấy mẫu mỗi giây để lưu hoặc dùng làm background |
| Người dùng chính | Thợ rang, vận hành sản xuất | Người thiết kế profile có chuyên môn |

## Bằng chứng từ công thức hiện tại

Khi chỉ nhập CHARGE 160°C, DROP 200°C và 12:00, không nhập ba mục tiêu tùy chọn, ứng dụng suy:

- FCs = DROP − 8°C = 192°C và thời gian FCs = 90% tổng thời gian = 10:48.
- DE = FCs − 46°C = 146°C và thời gian DE = 64% thời gian tới FCs = 06:55.
- TP = 60% nhiệt DE = 88°C và thời gian TP = 16% thời gian tới FCs = 01:44.
- DEV nằm giữa FCs và DROP = 196°C tại 11:24.

Đây chính là toàn bộ các số đang xuất hiện trong ảnh. Đường cong an toàn về mặt hình học vì nội suy đơn điệu không vượt các neo, nhưng độ chính xác thực tế chưa được suy từ công suất máy, khối lượng cà, mật độ, độ ẩm hay mẻ nền.

## Điểm mạnh của Roast Lab

- Giao diện dẫn dắt tốt: người dùng đổi vài thông số quen thuộc và thấy kết quả ngay.
- Ba vùng Sấy, Maillard và Phát triển cùng phần trăm giúp đọc nhanh hơn giao diện Designer của Artisan.
- Các thẻ TP, DE, FCs, DEV và DROP biến biểu đồ thành kế hoạch vận hành rõ ràng.
- Một mô hình mục tiêu được dùng xuyên suốt màn sửa hồ sơ và màn rang, giảm nguy cơ hai màn cho kết quả khác nhau.
- Khóa đường cong đơn điệu hạn chế việc người dùng vô tình tạo hình dạng phi thực tế.

## Khoảng trống cần xử lý

1. Tên “đường rang dự kiến” và độ chi tiết của biểu đồ tạo cảm giác đây là dự báo vật lý. Nên gọi là **Đường BT mục tiêu** hoặc **Đường rang mục tiêu**, đồng thời đặt nhãn **Ước tính theo công thức** ngay cạnh tiêu đề khi còn mốc tự suy.

2. Cảnh báo “App tự ước” hiện nằm nhỏ dưới biểu đồ. Trạng thái của từng mốc nên xuất hiện ngay trên thẻ, ví dụ `DE · Ước tính` và `FCs · Đã đặt`. Đây là thông tin quyết định mức tin cậy, không phải ghi chú phụ.

3. Mẻ nền không tham gia tạo hình dạng đường BT đang xem. Khi đã chọn mẻ nền, giao diện cần nói rõ: mẻ nền cung cấp lịch gas/gió/trống; đường BT vẫn là mục tiêu ước tính. Phương án tốt hơn là cho phép chọn **Lấy đường BT từ mẻ nền**.

4. RoR dùng thang đối xứng theo cực trị toàn mẻ. Cú rơi CHARGE→TP tạo biên ±55°C/phút, làm RoR sau TP bị nén gần thành đường phẳng. Nên cho RoR vận hành bắt đầu từ TP, hoặc cung cấp thang riêng tập trung vào đoạn sau TP.

5. Biểu đồ thiếu chú giải rõ cho nét cam và nét vàng đứt. Thêm `BT mục tiêu` và `RoR mục tiêu` sẽ giảm việc người dùng phải suy đoán.

6. Nhãn FCs, DEV và DROP dồn ở góc phải và đã bắt đầu va nhau. Cần thuật toán tránh va chạm hoặc đặt nhãn theo các tầng cố định.

7. Biểu đồ chỉ đọc, trong khi mức hoàn thiện thị giác gợi ý có thể kéo các điểm. Nếu chưa cho kéo, nên tránh con trỏ hay hiệu ứng giống điểm điều khiển. Nếu bổ sung chế độ nâng cao, chỉ cần cho kéo TP, DE và FCs trước; không cần sao chép toàn bộ độ phức tạp của Artisan.

8. Modal dài khiến nút Lưu rơi dưới màn hình. Footer Hủy/Lưu nên bám đáy để phản hồi tức thời trên biểu đồ không bị ngắt bởi thao tác cuộn dài.

## Hướng phát triển đề xuất

Giữ trải nghiệm hiện tại làm chế độ **Nhanh**. Thêm chế độ **Tinh chỉnh đường** với số điểm rất giới hạn:

- Cho nhập thời gian DE và FCs độc lập.
- Cho kéo TP, DE và FCs; khóa thứ tự thời gian và giới hạn nhiệt hợp lệ.
- Thêm tối đa một hoặc hai điểm BT trung gian để chỉnh RoR.
- Cho lấy đường BT từ mẻ nền rồi đơn giản hóa thành ít điểm.
- Luôn phân biệt mốc người dùng đặt, mốc lấy từ mẻ nền và mốc do app ước tính.

Cách này giữ ưu thế dễ dùng của Roast Lab, đồng thời lấy đúng phần có giá trị nhất từ Artisan Designer: khả năng điều chỉnh hình dạng đường BT và quan sát RoR phản hồi ngay.

## Nguồn đối chiếu

- `OTL Roast Lab.html`: `buildTarget()` và `peDrawPreview()`.
- Artisan `canvas.py`: `fit_spline_to_profile()`, `on_motion()` và `convert_designer()`.
- Open Design: quy tắc về phân cấp thông tin, trạng thái, khả năng nhận biết và hành động trong modal.
