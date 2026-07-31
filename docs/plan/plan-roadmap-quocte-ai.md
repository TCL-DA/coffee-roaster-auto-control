# Roadmap nâng cấp firmware OTL-06ALS lên mức quốc tế và sẵn sàng tích hợp AI

Tài liệu này lưu lại các điểm cần nâng cấp trước khi tách sang workspace mới. Mục tiêu là giữ code cũ ổn định, sau đó cải tiến từng phần trong nhánh/workspace riêng để giảm rủi ro cho firmware đang chạy máy thật.

## Các điểm cần nâng trước khi đưa lên tầm quốc tế

1. Giảm RAM: hiện build dùng `42,428 / 49,152 B = 86.3%`. Các mảng SD `2200` điểm trong `Define.h` là nguyên nhân lớn.
2. Bỏ `String` ở đường chạy lâu, nhất là SD/profile parse.
3. Tách logic lớn trong `Program.h` và `Modbus_Master.h` thành module `.cpp/.h` rõ ràng hơn.
4. Thêm timeout/fail-safe cho Modbus startup thay vì `while` vô hạn.
5. Tắt `enDebug` mặc định khi production.
6. Chuẩn hóa encoding UTF-8 vì nhiều comment tiếng Việt đang mojibake.
7. Làm lớp “AI/PC command contract”: PC/AI chỉ gửi setpoint có giới hạn; STM32 giữ quyền safety cuối cùng.
8. Thêm log lỗi có mã, timestamp, trạng thái cảm biến, trạng thái gas/relay.
9. Thêm test profile parser, Modbus address mapping, safety cutoff, gas slew rate.
10. Có tài liệu protocol để Artisan/Cropster/custom AI gateway đọc/ghi ổn định.

## Gợi ý thứ tự triển khai trong workspace mới

1. Chốt baseline: build, size, trạng thái RAM/Flash, và danh sách cảnh báo hiện tại.
2. Chuẩn hóa encoding và tắt debug mặc định để có nền production sạch.
3. Giảm RAM trước khi thêm tính năng mới.
4. Thay `String` bằng buffer cố định ở các đường SD/profile/log.
5. Tách module theo trách nhiệm: SD profile/logging, Modbus HMI, Modbus PC/Artisan, safety, control loop.
6. Bổ sung timeout/fail-safe, watchdog, và error log.
7. Viết protocol AI/PC rồi mới cho AI điều khiển thử ở shadow mode.
8. Thêm test và checklist trước khi flash máy thật.
