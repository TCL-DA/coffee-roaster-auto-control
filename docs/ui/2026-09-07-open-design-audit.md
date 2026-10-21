# Rà soát Roast Lab theo Open Design

Phạm vi: quan sát sáu tab trong trình duyệt cô lập ở 1440×900, kiểm tra cột rang ở bốn kích thước, tái hiện trạng thái mất kết nối tại 1366×768 và đối chiếu mã nguồn. Không sửa giao diện hoặc gửi lệnh máy thật. Kho trong trình duyệt không có cầu desktop nên chưa kết luận về bố cục khi có dữ liệu kho thật.

Áp dụng Open Design craft/state-coverage.md và typography-hierarchy.md; không chạy engine AI. Tham khảo thêm nguyên tắc hiển thị trạng thái và phòng ngừa nhầm thao tác: https://www.nngroup.com/articles/ten-usability-heuristics/.

## Ưu tiên 1: trạng thái và ý nghĩa thao tác

1. Mất kết nối vẫn hiện “chưa có lửa”. Đã tái hiện DS.state=error, DS.snap=null. Cần trạng thái “Không xác định — mất kết nối”, không suy diễn dữ liệu thiếu thành tắt.
2. “Kết thúc mẻ” trong cmdDrop vừa toggle cửa drop vừa chốt mẻ khi đang rang. Nút không diễn đạt hết tác động; cần tên thao tác rõ và thể hiện trạng thái cửa, xác nhận phù hợp khi mở xả kết thúc mẻ. Giữ thao tác đóng cửa và tự xả đúng ngữ nghĩa, không thêm trì hoãn đồng loạt.
3. Xả liệu và Kết thúc mẻ vẫn giống nhau về kiểu nút. Cần phân biệt bằng nhãn đầy đủ và mô tả tác động, không chỉ màu hoặc khoảng cách.
4. ET bị lệch màu: biến --c-et là #1673b1 nhưng liveET thực tế rgb(158,16,25). Cần thống nhất màu đường biểu đồ, chú giải và giá trị từ một nguồn; tránh CSS ghi đè rải rác.

## Ưu tiên 2: bố cục và khả năng đọc

5. Thiết bị phụ chỉ còn khoảng 131 px tại 1366×768. Cuộn và chạm cuối danh sách vẫn đạt test; đây là hạn chế khả năng quan sát, không phải mất nút. Cần hiện số thiết bị đang bật, dấu hiệu cuộn và quyền thu gọn ngay tại tiêu đề.
6. Header hai hàng, dòng hướng dẫn và dải mốc chiếm nhiều chiều cao laptop. Cần gom vùng hướng dẫn, giảm khoảng cách; không thu nhỏ chữ để lấy chỗ.
7. Hồ sơ ở 1440×900 chỉ thấy một thẻ đầy đủ và đầu thẻ tiếp theo. Thẻ chứa khoảng trống đường cong cùng nút nạp toàn chiều ngang. Cần thẻ gọn với thông số chính, chi tiết mở khi chọn.
8. Bộ chọn ngày Lịch sử hiện dd-----yyyy khó hiểu. Cần kiểm riêng thành phần ngày trong Chromium/WebView, nhãn định dạng và đủ chỗ cho từng phần ngày/tháng/năm.
9. Các nhãn “Nhiệt charge”, “Calib gas”, “Model nhiệt”, “Drum RPM @ 50Hz” chưa nhất quán. Dùng tiếng Việt cho nhãn chính, đơn vị và thuật ngữ kỹ thuật ở phần phụ.
10. Dải TP/DE/FCs/DEV/DROP thiếu giải thích; trong trạng thái chưa có mẻ, nhiều dấu gạch ngang không giúp ra quyết định. Cần tên dễ hiểu và trạng thái chờ có lời dẫn ngắn.
11. Cài đặt có Hủy/Áp dụng/Lưu nhưng lời giải thích phạm vi áp dụng quá nhỏ. Cần nêu rõ áp dụng máy đang chạy hay lưu cấu hình và hiển thị trạng thái chưa lưu.

## Ưu tiên 3: tính nhất quán thị giác

12. Trang Rang nền phẳng trong khi các trang khác còn nền loang; icon lẫn SVG, emoji và ký tự. Cần chung bộ bề mặt, icon và độ bo góc. Đây là đánh giá thẩm mỹ theo mục tiêu giao diện tối giản của người dùng.
13. Chưa có đủ bằng chứng để khẳng định mọi chữ đạt tương phản: cần đo chữ phụ, placeholder, trạng thái vô hiệu ở cả sáng/tối và màu cá nhân hóa. Không dùng kết quả test hình học để kết luận khả năng đọc của người 70 tuổi.

Thứ tự đề xuất: sửa bốn vấn đề trạng thái/ngữ nghĩa trước; tiếp đến header và thiết bị phụ, trang hồ sơ, ngày và ngôn ngữ; cuối cùng thống nhất phong cách. Chưa cần thêm animation khi các vấn đề này chưa được giải quyết.
