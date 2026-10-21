# OTL Roast Lab — tối ưu hiệu năng ngày 28/09/2026

## Kết quả

Giảm cập nhật DOM không cần thiết và dừng vòng vẽ đồ thị khi hộp chi tiết/so sánh đã đóng. Phản hồi API của lượt xem cũ không còn ghi đè lượt mới hoặc khởi động lại việc vẽ sau khi đóng hộp.

Đo bằng Chromium qua Playwright, cửa sổ 1366×768, trang riêng với dữ liệu giả lập. Đối chiếu nguồn trước khi sửa tại `backup/OTL Roast Lab.pre-performance-20260928-204300.html`.

| Phép đo | Trước | Sau |
|---|---:|---:|
| Quét trợ năng toàn trang trong 5 giây nhàn rỗi | 26 | 0 |
| Số lần thay DOM khi ghi cùng một nhãn 1.000 lần | 1.000 | 0 |
| Số lượt gọi vẽ trong 1,1 giây sau 5 yêu cầu vẽ canvas đã đóng | 340 | 5, không lặp tiếp |

Đây là số lượng công việc thừa trong các tình huống tái hiện; không phải mức tăng tốc tổng thể của ứng dụng. Chưa đo trực tiếp trên WebView2 hay máy rang thật.

## Thay đổi

- `txt()` và nhãn định kỳ chỉ thay nội dung khi chuỗi hiển thị đổi; giữ nguyên xử lý số 0, giá trị rỗng và dấu thiếu dữ liệu.
- Observer trợ năng chỉ quét nhánh phần tử mới thêm, gồm chính phần tử gốc và trường nhập cha. Cập nhật chữ đơn thuần không kích hoạt quét. Nhãn sinh tự động tránh trùng ID.
- Mỗi canvas chi tiết/so sánh giữ tối đa một lịch vẽ chờ. Đóng hộp hủy lịch và làm hết hiệu lực lượt tải đang chờ.
- Callback chuyển cảnh không mở lại hộp đã đóng. API trả nhanh vẫn đợi hộp mở rồi vẽ.
- So sánh hồ sơ và so sánh lịch sử dùng chung số lượt, tránh kết quả cũ ghi đè hộp mới. Thu phóng lấy bộ dữ liệu hiện tại.

Quy tắc Open Design được đọc từ `F:/Project/open-design/craft/animation-discipline.md` và `laws-of-ux.md`; chỉ áp dụng quy tắc cục bộ, không chạy engine. Không thay đổi nhịp điều khiển máy hay firmware.

## Kiểm chứng

Tám bộ kiểm đạt:

1. `tools/test_ui_performance.py`: 13 phép kiểm hiệu năng, nhãn/điều khiển động, Enter/Space, đóng/mở lại, chuyển cảnh trì hoãn và phản hồi cũ giữa hai luồng so sánh.
2. `tools/test_ui_review_0914.py`: luồng rang, mất kết nối, xác nhận xả, phản hồi lệch thứ tự, tên/tiêu điểm/Tab của hộp thoại.
3. `tools/test_ui_touch_real.py`: cử chỉ cảm ứng CDP, trượt ngón hủy lệnh, gas, phím tắt, tablet.
4. `tools/test_ui_hold_confirm.py`: giữ đủ thời gian mới gửi lệnh, nhả/kéo ra hủy, khóa thoát khi rang.
5. `tools/test_ui_smooth.py`: chuyển tab đồng bộ, hiệu ứng đóng, chế độ giảm chuyển động.
6. `tools/test_ui_ror.py`: công thức RoR, lọc, giới hạn và dữ liệu rỗng.
7. `tools/test_ui_profile_target.py`: mục tiêu, mốc rang, kéo biểu đồ và chỉnh hồ sơ.
8. `tools/test_ui_caidat_tuluu.py`: tự lưu, hoàn tác, nhập/xuất và khóa đổi cổng khi đang rang.

Bộ kiểm hiệu năng được chạy trên bản trước khi sửa và bắt đúng năm nhóm lỗi. Bản sửa đạt cả 13 phép kiểm; các bộ trên không phát sinh lỗi JavaScript. Đã kiểm cú pháp Python và khoảng trắng của diff.

PyInstaller đã tạo bản staging rồi cập nhật bản dùng chính tại `tools/dist/OTL Roast Lab HMI.exe`; bản cũ giữ ở `tools/dist/OTL Roast Lab HMI.before-performance-20260929.exe`. `tools/test_exe_end_to_end.py` đạt: EXE mở cổng 8555, chứa HTML mới, giữ nút ± đúng nhịp và giữ nút xả đúng 1 giây.

Giới hạn còn lại: nếu hộp vẫn mở nhưng canvas luôn có chiều rộng bằng 0, mã giữ một lịch RAF thử lại. Không có giới hạn cứng về số lần thử trong trường hợp đó.

## Đợt tiếp theo — 29/09/2026

- `drawChart()` chỉ cấp lại backing store khi kích thước thật hoặc device pixel ratio đổi. Mười lần vẽ cùng kích thước tạo **0** lần cấp lại; bản sao trước sửa tạo **20**.
- `uxAccountSave()` dùng cờ thay đổi. Hai mươi lần gọi liên tiếp khi không đổi chỉ stringify gói phong cách **1** lần; bản sao trước sửa tạo **21** lần, có thể bao gồm ảnh nền gần 1 MB.
- Cả hai điểm đều nằm ngoài đường điều khiển máy; không thay đổi nhịp snapshot, RoR hay lệnh Modbus.

Sao lưu đợt này: `backup/OTL Roast Lab.pre-performance2-20260929-090308.html`.

PyInstaller đã tạo lại và cập nhật `tools/dist/OTL Roast Lab HMI.exe`; bản trước đợt này giữ ở `tools/dist/OTL Roast Lab HMI.before-performance2-20260929.exe`. Bản EXE mới 52,467,608 byte, SHA-256 của HTML nhúng `b25616135efa68ae2c62a97e9693002c5539803b3bc9c5e3013493283bcbcb7b`; HTML nhúng khớp file nguồn. `tools/test_exe_end_to_end.py` đạt sau khi cập nhật.
