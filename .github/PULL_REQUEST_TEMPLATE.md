## Sửa cái gì

<!-- Một hai câu. Sửa cho máy nào, hay sửa chung cho mọi máy. -->

## Vì sao

<!-- Triệu chứng gặp trên máy thật, hoặc yêu cầu của chủ máy. -->

## Kiểm tra

- [ ] `pio run -e genericSTM32F103RC` — build sạch, không thêm cảnh báo mới
- [ ] `pio run -e genericSTM32F103RC --target size` — RAM còn dư, ghi số vào đây: …
- [ ] Đã chạy trên máy thật, hoặc trên máy rang ảo (`tools/`)
- [ ] Không gọi SD / Modbus / Serial / `delay()` trong ISR
- [ ] Chuỗi in ra cổng debug viết bằng tiếng Anh, chú thích trong code tiếng Việt có dấu

## Ảnh hưởng tới máy đang chạy

<!-- Máy nào cần nạp lại? Có đổi hành vi lúc vận hành không? Có cần dặn thợ gì không? -->

## Nếu hỏng thì lùi thế nào

<!-- Quay lại commit nào, hay có cờ nào tắt được trong Config.h. -->
