# Đánh giá luồng Hồ sơ → Rang trên bản web

Ngày đánh giá: 07/09/2026  
Ngữ cảnh: Chrome trên laptop Windows, giao diện web tại `192.168.1.44:8555`.

## Kết luận

Luồng có hai hành vi khác nhau cần phân biệt:

- Bấm tab **Rang** trên thanh điều hướng chỉ chuyển màn hình. Nếu chưa chọn hồ sơ, trạng thái **Chưa chọn hồ sơ rang** là đúng.
- Bấm **Nạp & rang** trong thẻ hồ sơ phải gọi `loadProfile(index)`, mang hồ sơ đã chọn sang màn Rang và chuyển trạng thái sang sẵn sàng. Nếu vẫn thấy **Chưa chọn hồ sơ rang**, đó là lỗi mất lựa chọn hoặc bản web đang dùng HTML/cache cũ.

## Điểm hoạt động tốt

- Trang Hồ sơ cho thấy rõ tên, mức rang, nhiệt nạp, nhiệt xả và thời gian trước khi chọn.
- Nút **Nạp & rang** có độ nổi bật cao và nằm trong chính thẻ hồ sơ, nên quan hệ giữa đối tượng và hành động rõ ràng theo nguyên tắc Gestalt về vùng chung.
- Màn Rang có trạng thái rỗng kèm giải thích và hành động **Chọn hồ sơ rang**, không để người dùng mắc kẹt.
- Kiểm thử hiện có xác nhận `loadProfile()` chọn đúng hồ sơ, khóa đổi hồ sơ khi mẻ đang chạy, không tràn tên dài và không phát sinh lỗi JavaScript.

## Lỗi và điểm yếu

### P0 — Cần xác nhận hành vi sau nút “Nạp & rang”

Ảnh màn Rang đang ở `NOSEL`. Nếu ảnh này xuất hiện sau khi bấm nút cam **Nạp & rang** thì luồng chính đã hỏng: lựa chọn không được mang sang màn Rang. Nếu người dùng chỉ bấm tab Rang thì đây không phải lỗi.

Hướng sửa: kiểm thử trên đúng đường web HTTP, bấm nút của một hồ sơ cụ thể, rồi xác nhận `R.profName`, `R.profNo` và `R.phase === "IDLE"`. Đồng thời kiểm tra cache của web clone khi HTML desktop vừa được cập nhật.

### P1 — Tỷ lệ đọc giữa Hồ sơ và Rang thiếu nhất quán

Trang Hồ sơ dùng thẻ lớn, chữ tên và thông số dễ đọc. Sang Rang, cùng màn hình lại phải chứa dải mốc, đồ thị, bốn thẻ số, thiết bị phụ, ba bộ điều khiển và sáu nút đáy. Kết quả là chữ ở cột phải, trạng thái thiết bị và các nút điều khiển nhỏ hơn rõ rệt.

Đây là vấn đề chức năng vì màn Rang là nơi cần đọc nhanh và chạm chính xác. Hướng sửa: tạo breakpoint riêng cho viewport thấp của laptop; ưu tiên BT, ET, thời gian, gas, gió và trống; thu gọn thiết bị phụ theo mặc định; giảm chi tiết thứ cấp trước khi giảm cỡ chữ.

### P1 — Dùng khung 2560×1440 rồi co toàn bộ làm suy giảm khả năng đọc

Hàm `fit()` giữ stage cao 1440 và dùng `transform: scale(...)`. Khi Chrome còn thanh địa chỉ và Windows còn taskbar, chiều cao khả dụng thấp nên toàn bộ giao diện bị co. Các biến bù `--read-main`, `--read-small` chỉ hỗ trợ một phần; nhiều nhãn của màn Rang vẫn dùng cỡ chữ riêng.

Hướng sửa: ở bản web, dùng bố cục responsive theo chiều cao thực thay vì chỉ co nguyên khung. Không nên giải quyết bằng cách tiếp tục tăng riêng từng cỡ chữ.

### P2 — Trạng thái mất kết nối cạnh tranh sự chú ý với tác vụ chính

Nhãn đỏ **Mất kết nối** nổi bật đúng về cảnh báo, nhưng màn Rang vẫn trình bày toàn bộ điều khiển như đang sẵn sàng. Người vận hành phải tự suy ra nút nào còn tác dụng.

Hướng sửa: khi mất kết nối, giữ số liệu cuối với nhãn thời điểm cập nhật, vô hiệu hóa rõ các lệnh ghi và đặt một hành động khôi phục kết nối gần cảnh báo.

### P2 — Không gian dọc bị trình duyệt và taskbar lấy mất

Ảnh cho thấy Chrome chưa toàn màn hình và taskbar vẫn hiện. Đây không phải lỗi của ứng dụng, nhưng làm nặng thêm lỗi co tỷ lệ và giảm vùng chạm.

Hướng xử lý: hỗ trợ một nút **Toàn màn hình** dễ thấy trên web, đồng thời vẫn phải bảo đảm bố cục dùng được khi không toàn màn hình.

## Thứ tự sửa đề nghị

1. Xác nhận đường bấm **Nạp & rang** trên chính bản web đang chạy và xử lý cache nếu trạng thái vẫn là `NOSEL`.
2. Thêm breakpoint theo chiều cao cho màn Rang; thu gọn thiết bị phụ và nội dung thứ cấp.
3. Đồng nhất ngưỡng chữ đọc được và vùng chạm giữa Hồ sơ và Rang.
4. Làm rõ trạng thái điều khiển khi mất kết nối.

Đánh giá áp dụng các quy tắc Open Design về khả năng đọc, vùng chạm, trạng thái và tải nhận thức. Chỉ dùng quy tắc thiết kế; không chạy engine Open Design.
