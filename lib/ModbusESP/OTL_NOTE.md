# ModbusESP — bản đóng băng cho firmware OTL

Thư viện Modbus RTU **slave** dùng cho cổng Artisan PC (`include/Modbus_Slave.h`).

Nguồn gốc: `emelianov/modbus-esp8266`, phiên bản **4.0.0-DEV** (file gốc 19/11/2021).

## Vì sao chép vào repo thay vì khai trong `lib_deps`

Trước đây `platformio.ini` **không khai** thư viện này. Nó được lấy ngầm từ kho lib
toàn cục của máy lập trình (`~/.platformio/lib/`), mà ở đó tồn tại **hai** bản khác
nhau cùng cung cấp `ModbusRTU.h`:

| Thư mục | Phiên bản | Ghi chú |
|---|---|---|
| `ModbusESP` | 4.0.0-DEV (11/2021) | **bản đang được nạp trên máy khách** |
| `modbus-esp8266-master` | 4.0.0 | mới hơn, khác ở MỌI file trong `src/` |

Bản nào thắng là do thứ tự quét thư viện của PlatformIO quyết định, không phải do
chủ ý. Hậu quả: clone repo sang máy khác thì **gãy build**, hoặc tệ hơn là biên dịch
trót lọt bằng bản Modbus khác → cổng Artisan chạy khác đi mà không ai biết.

Bản chép vào đây là **đúng bản đã kiểm chứng đang chạy trên máy**. Giữ nguyên như vậy.

## Trước khi nâng cấp lên bản mới

Phải thử lại cổng Artisan trên máy thật: kết nối, đọc BT/ET, đổi baud/ID từ HMI, và
gạt `swSignal` để đổi giữa cổng Bluetooth (Serial3) và cổng máy tính.

Lưu ý sẵn có trong code: trên STM32, `mbs.begin()` ghim timing khung theo 9600 nên
`Modbus_Slave.h` phải gọi `mbs.setBaudrate(baud)` để tính lại t3.5.
