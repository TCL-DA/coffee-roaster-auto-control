# Thợ rang dùng thử Roast Lab — 14/09/2026

**Cách làm.** Đóng vai một thợ rang (dùng skill `rang-ca-phe`) đi trọn một mẻ trên app ở màn
1920×1080, có máy ảo bơm số liệu như máy thật: làm nóng → chọn hồ sơ → bắt đầu → chỉnh gas
giữa mẻ → vào nổ → xả → tổng kết → xem lại lịch sử. Mỗi bước chụp ảnh rồi đối chiếu với bản
thiết kế Claude Design.

Bản thiết kế dùng để đối chiếu là **bản trên đĩa `docs/ui/design-web/`**. Vân tay md5 khớp
`SOURCE.md`, tức chưa bị sửa. Project trên mây (`3c3a6a49…`) hiện báo **404**. Cần URL
`claude.ai/design/p/<uuid>` mới thì mới kéo bản mới về hoặc đẩy ngược lên được.

## Kết luận nhanh

Nhịp chính **dễ xài**: chọn hồ sơ, bấm BẮT ĐẦU, chỉnh gas ±, giữ để xả. Số to, nút to, đọc được
từ xa. Chỗ khó chịu thường không nằm ở hình thức, mà ở hai loại tình huống:

- **App tự làm thay thợ mà không báo trước**, như tự xả theo nhiệt hồ sơ.
- **App nói bằng chữ của lập trình viên**, như bảng làm nóng, chip DEV, đường vẽ không tên.

Có **một lỗi nguy hiểm**: nút "Kết thúc mẻ" có thể đóng cửa xả giữa lúc đang trút hạt.

## Nhật ký đi mẻ — thấy gì, thợ khó chịu ở đâu, đã sửa ra sao

| # | Bước | Thấy gì | Vì sao khó chịu | Đã sửa |
|---|---|---|---|---|
| 1 | Tổng quan | Hai nút cam "Mở điều khiển rang" giống hệt. Bảng làm nóng ghi *"BT từ máy · nhiệt đặt ở đây chỉ để tham chiếu; thời gian mô phỏng không áp dụng"*. Ô "Thời gian 12 phút" bấm không làm gì. Thanh tiến độ ghi "BT trực tiếp" | Không biết bấm nút nào, không biết máy còn phải chờ bao lâu | Khi nối máy: ẩn nút trùng và ô thời gian vô tác dụng. Ô tiến độ ghi **"còn khoảng N phút"**, tính từ độ dốc BT thật 90 giây gần nhất, như bản thiết kế. Câu chữ viết lại cho thợ đọc |
| 2 | Hồ sơ | Hàng `📅 — · 👤 —` rỗng. Nút 🗑 xoá nằm sát ✎ sửa | Hàng rỗng là rác. Đeo găng quệt trượt là mất hồ sơ | Không có dữ liệu thì không hiện hàng đó; có thì ghi "Rang lần cuối … · thợ …". Nút xoá tách hẳn sang mép phải |
| 3 | Rang, lúc chờ | Toast *"Xả tự động tại 206°C theo hồ sơ"* hiện 2 giây rồi mất. Dải pha ghi "Sấy 06:12 56%" như số đã rang | Quên ngay chuyện app sẽ tự xả. Nhầm số kế hoạch thành số thật | Ô DROP ghi **"tự xả →206°"** suốt mẻ. Pha chưa chạy tới ghi **"dự kiến"** |
| 4 | Giữa mẻ | Có một đường hồng bậc thang và một đường cam mảnh trên đồ thị, chú giải chỉ có Nền/BT/ET | "Đường hồng là gì?" | Chú giải thêm **Tăng nhiệt** và **Gas**, bấm vào nhãn để ẩn/hiện đường đó. ABT/ΔET vẫn ở menu Thao tác |
| 5 | Vào nổ | Ô DEV lặp nguyên giờ + nhiệt của FCs | Ô vô nghĩa, trong khi đây là lúc thợ cần số nhất | Theo bản thiết kế: DEV = **thời gian phát triển đang chạy + %** |
| 6 | Gần xả | Mẻ tự kết thúc lúc 10:01 dù mục tiêu là 11:00, không có báo trước | Thợ đứng hình, không hiểu vì sao | Còn 3°C là tới ngưỡng thì báo một lần (chữ + giọng *"Sắp tự xả"*), kèm cách đổi/bỏ ngưỡng |
| 7 | ⛔ Sau tự xả | Thợ giữ "Kết thúc mẻ" cho chắc, app gửi **drop=0**. Băng lệnh ghi "Kết thúc mẻ = 0" | **Đóng cửa xả giữa lúc hạt đang trút**, firmware huỷ luôn timer xả | Nút hiện dòng **"● Cửa xả đang mở"**. Giữ nút lúc đó phải xác nhận *"Đóng cửa xả ngay?"* (mặc định "Để máy tự đóng") |
| 8 | Tổng kết | Toast "Đã lưu curve…" che đúng hàng nút "Lưu ghi chú · Lưu hồ sơ chuẩn mới" | Muốn bấm mà không thấy nút | Khi bảng tổng kết đang mở, toast chuyển lên góc trái trên |
| 9 | Lịch sử | Cả hàng tiêu đề cột lệch khỏi dữ liệu. Ô tích đè lên mã mẻ. Ngày dạng `2026-09-13` | Đọc nhầm cột. Ngày không giống chỗ khác trong app | Cột chọn khai cùng bề rộng ở tiêu đề và thân bảng (92px). Ngày đổi sang dd/mm/yyyy |

Gốc lỗi Lịch sử: `thead` và `tbody` là hai bảng `table-layout:fixed` riêng (để tiêu đề dính đỉnh),
nhưng ô tiêu đề cột chọn **thiếu lớp `.hsel`**. Ô đó chia đều bề ngang như mọi cột khác, nên cả
hàng tiêu đề lệch khỏi dữ liệu.

## Đối chiếu bản thiết kế Claude Design

- **Khớp thiết kế:**
  - thứ bậc màn Rang: 5 ô mốc, số BT/ET lớn, dải pha, 3 ô gas/gió/trống
  - cử chỉ giữ để xác nhận
  - thẻ hồ sơ 3 cột
  - thẻ "Chuẩn bị mẻ rang" 3 bước
- **App lệch thiết kế, đã kéo về theo thiết kế:**
  - ô DEV
  - bảng làm nóng: số lớn, còn bao lâu
  - định dạng ngày ở Lịch sử
- **App có mà thiết kế chưa vẽ** (giữ nguyên, chỉ gọi tên cho rõ):
  - đường tăng nhiệt và gas trên đồ thị
  - tự xả theo ngưỡng nhiệt
  - nút xoá trên thẻ hồ sơ
  - dòng "Đang chờ TỰ NẠP"
- **Cố ý giữ khác thiết kế:** thiết kế ghi "GIỮ 1 GIÂY", app giữ 0,5 giây theo chủ máy chốt 08/09.

## Chưa sửa — cần chủ máy quyết

1. **Có nên tự bật tự xả khi hồ sơ có nhiệt xả không?** Hiện nạp hồ sơ là tự bật. Mẻ thử kết
   thúc sớm hơn mục tiêu 59 giây vì BT chạm ngưỡng trước giờ. Đã thêm báo trước, nhưng câu hỏi
   "mặc định bật hay tắt" là quyết định vận hành, không phải việc của giao diện.
2. **% phát triển mục tiêu tự ước chỉ khoảng 9–10%** khi hồ sơ không đặt `devTarget`, thấp hơn
   nhiều so với cách máy đang rang. Đây là mô hình ước lượng (`buildTarget`), không phải lỗi
   hiển thị. Nên đặt `devTarget` trong hồ sơ, hoặc bàn lại công thức ước.
3. "Tăng nhiệt +54 °C/phút" lúc máy đang làm nóng, trước khi nạp: số đúng nhưng chói, kéo mắt
   sai chỗ lúc chờ.
4. Bong bóng trợ lý "Hồng" mặc định nằm mép trái, đè lên ô tích Lịch sử và mép thẻ hồ sơ. Kéo
   đi được, nhưng vị trí mặc định nên dời.
5. Chưa soi bằng mắt ở màn 1366×768 và chưa chạy trên máy rang thật.

## Kiểm thử

- **Soi bằng ảnh.** Chạy lại kịch bản máy ảo sau mỗi lượt sửa. Lần cuối:
  - không lỗi JS
  - sau tự xả, thợ giữ "Kết thúc mẻ" thì app hỏi lại; chọn "Để máy tự đóng" thì **không có
    lệnh drop=0 nào**
  - ô DEV (màn Rang và tổng kết) khớp % ở dải pha
  - bảng Lịch sử thẳng cột
- **Trọn bộ `tools/test_ui_*.py`: 31/31 ĐẠT.**
  - `test_ui_motion_sync` đã bắt được số BT trên viên trạng thái chỉ đạt 3,54:1. Nguyên nhân:
    viên có nền tối cố định mà màu chữ đi theo token của theme sáng. Đã đổi sang `#f58a35`,
    chạy lại thì đạt.
  - `test_ui_match_reference` sửa theo chỗ mới của nút Tăng nhiệt (chú giải thanh đầu).
- **Chưa làm:** soi bằng mắt ở màn 1366×768, chạy trên máy rang thật.
