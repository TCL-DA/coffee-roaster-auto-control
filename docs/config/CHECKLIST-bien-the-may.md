# Bảng hỏi phần cứng — BẮT BUỘC trước khi làm biến thể máy mới

Rút từ máy điện VX4 ngày 14/10/2026. Mình đoán sai lần lượt 5 điều, mỗi điều tốn một vòng nạp và đọc COM:
1. "3 s sau có phản hồi": mình hiểu là có dây tín hiệu lửa, thực tế là không có.
2. Bus RS485: mình giả định nối cổng Modbus như máy gas, thực tế nối cổng loader-cân.
3. VX4: mình giả định chung bus, thực tế nằm ở cổng riêng.
4. Tốc độ VX4: mình giả định 38400, thực tế 9600.
5. Biến tần gió: mình giả định analog, thực tế chạy RS485 ở 45–60 Hz.

Hỏi **một lượt** bằng AskUserQuestion, ghi câu trả lời vào `docs/config/config-<máy>.md`, rồi mới sửa code.

## 1. Cổng serial — thiết bị nào nối CỔNG nào

| Thiết bị | Cổng nào? (Modbus cũ / loader-cân / máy tính) | ID | Baud |
|---|---|---|---|
| Đồng hồ BT | | 1 | |
| Đồng hồ ET | | 2 | |
| Biến tần trống | | 4 | |
| Biến tần gió | | 5 | |
| Module relay ngoài | (có / không) | 7 | |
| Đồng hồ buồng / thiết bị riêng (VX4…) | | | |
| Cân / loader | (có / không) | | |
| Artisan / app (cổng máy tính) | | | |

Board V400 có 4 UART: USART1 = HMI, USART2 = Modbus cũ, USART3 = Bluetooth / cân / loader, UART4 = máy tính (debug).
Mỗi thiết bị dùng **một cổng**. Hai chức năng dùng chung một cổng thì phải tắt một bên trong code (`Modbus_Slave.h` `slaveQuaCongCan`).

## 2. Nguồn nhiệt

- Gas hay điện? Có **dây tín hiệu lửa / phản hồi** về chân CH1 không? (máy điện VX4: **KHÔNG** → `ELEC_HEAT_ON_DELAY_MS`)
- Ai điều khiển nhiệt: van gas (DAC) hay đồng hồ PID (ghi SV)? Dải SV?
- Relay CH1 = bật / tắt nhiên liệu? Có contactor qua CH1 không?

## 3. Gió và trống

- Gió: analog DAC hay biến tần RS485? Có cảm biến vacuum không? Dải Hz? (máy điện: RS485, 45–60 Hz, không vacuum)
- Trống: biến tần RS485 (dải 30–50 Hz như cũ) hay cố định?
- Drum/fan, tay đảo (mixer): điều khiển riêng (cần module relay ngoài ID 7) hay chạy chung relay quạt nguội?

## 4. Màn hình và cấu hình `$M62`

- Panel 110WS (có cổng mạng) hay 110CS (không cổng mạng)?
- Bit `$M62`: cỡ máy · vacuum · loader · cân · relay ngoài · đốt khói · tách đá · tay đảo riêng · núm vặn.

## 5. Sau khi nạp

Đọc COM debug 15 s: mọi thiết bị phải in `=> X OK`, cách đọc mã `0xe2` và `0xe0` ở skill `flash-stm32`.
Sau đó hỏi chủ máy kiểm trên máy: tần số biến tần, SV trên đồng hồ, dock "Đang nung".
