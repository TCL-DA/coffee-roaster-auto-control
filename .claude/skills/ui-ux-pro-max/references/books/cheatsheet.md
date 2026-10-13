# Cheatsheet — luật quyết định từ 3 nguồn (HMI · web · app)

Rút từ: Norman *The Design of Everyday Things* (2013) · Hollifield *A High Performance HMI* (ISA 2012) ·
bản tóm tắt Bookey của *Refactoring UI*. Tra chi tiết: `python scripts/search.py "<từ khoá>" --domain book`.
Bộ áo OTL (phẳng, không gradient/bóng, bảng màu đỏ·đen nhám·xám·nâu·xanh dương) luôn THẮNG nếu nguồn nói khác.

## 1. Luật "khi X → làm Y"

| Khi | Làm | Vì |
|---|---|---|
| Một giá trị quan trọng hiện dạng số trơn | Đặt nó cạnh dải bình thường / mục tiêu / trend | "Thông tin = dữ liệu có ngữ cảnh" — người vận hành không phải nhớ "bản đồ bình thường" trong đầu |
| Thiết bị đang chạy / tắt | Sáng hơn nền + chữ "RUNNING" / tối hơn nền + chữ "STOPPED" | Đỏ/xanh cho trạng thái bình thường làm hỏng nghĩa màu báo động |
| Có báo động | Ký hiệu theo MỨC ƯU TIÊN (hình + màu + số) ngay cạnh giá trị, nháy tới khi xác nhận | Mắt thấy chuyển động ở góc nhìn, không thấy đổi màu |
| Muốn thêm hiệu ứng động | Chỉ khi nó báo "cần chú ý" (báo động chưa xác nhận) hoặc là phản hồi nhấn | Chuyển động = tín hiệu khẩn |
| Màn có chế độ (AUTO/MANUAL/PC, dự phòng) | Chế độ hiện TO, cố định, mỗi chế độ trông khác hẳn | Mode error: cùng nút khác nghĩa |
| Mất cảm biến / dữ liệu cũ / đang ước lượng | Băng báo rõ (màu + icon + chữ + tuổi dữ liệu) | Tự động hoá hỏng không báo → người "ngoài vòng" |
| Lệnh nguy hiểm, không đảo ngược | Làm khó ĐÚNG bước đó (giữ 1 s, nắp che, PIN) + hiện ĐỐI TƯỢNG bị tác động | Hộp "Bạn chắc chứ?" bị bấm OK theo quán tính |
| Lệnh thường, đảo ngược được | Không hỏi lại; cho Hoàn tác | Undo mạnh hơn xác nhận |
| Giá trị nhập bất thường (ngoài dải hay dùng) | Hỏi lại, nêu dải thường | Kiểm tra hợp lý (sensibility check) |
| Người dùng nhập đúng nghĩa nhưng khác định dạng | Tự chuyển (1:30 / 90s / 1,5 / 1.5) | Không có "lỗi người dùng" |
| Nhiều người cùng bấm nhầm một chỗ | Sửa thiết kế (5 Why), không đào tạo lại | Lỗi lặp = lỗi thiết kế |
| Quy trình hiếm (hiệu chuẩn, reset) | Khác quy trình hằng ngày NGAY từ bước đầu + danh sách bước trên màn | Capture slip ở người thạo |
| Nút khác mục đích nằm cạnh nhau | Khác hình + khác chỗ + chữ; nút nguy hiểm tách xa | Description-similarity slip |
| Hành động không hợp lệ ở trạng thái hiện tại | Khoá/ẩn TRƯỚC, kèm lý do | Ràng buộc nhìn thấy trước > báo lỗi sau |
| Thông tin quan trọng (lỗi, báo động) | Giữ tới khi xác nhận + có lịch sử | Bộ nhớ ngắn 3–5 mục, mất khi bị ngắt |
| Cần tách hai nhóm nút / báo mục đang chọn | Đổi NỀN cả ô, màu icon/chữ, khoảng cách + vạch ngăn GIỮA nhóm; đang chọn = đảo màu cả ô | ⛔ Chủ máy cấm vạch/dải màu ở mép nút hay thẻ (11/10/2026) |
| Người bị ngắt giữa chừng | Hiện bước hiện tại + việc còn lại; giữ trạng thái khi chuyển màn/tải lại | Chi phí quay lại > chi phí ngắt |

## 2. Cây quyết định — báo động / thông báo

- Cần người vận hành LÀM GÌ đó không?
  - Không → KHÔNG phải báo động; ghi nhật ký hoặc hiện kín đáo.
  - Có → Hậu quả nếu chậm?
    - Nguy hiểm người/máy, phải làm ngay → **P1** ô vuông đỏ "1" + âm báo.
    - Hỏng mẻ / thiết bị trong vài phút → **P2** tam giác vàng "2".
    - Cần xử lý trong ca → **P3** tam giác ngược cam "3".
    - Chẩn đoán / bảo trì → **P4** thoi hồng "4" (không âm thanh).
- Mọi mức: nháy khi chưa xác nhận → đứng yên khi đã xác nhận → biến mất khi hết điều kiện; truy được nguyên nhân · hậu quả · cách xử lý.

## 3. Phân cấp màn (Hollifield L1–L4)

| Mức | Nội dung | OTL |
|---|---|---|
| L1 | Tổng quan toàn phạm vi, KPI, không điều khiển | Trang chủ web/app: các máy, mẻ, cảnh báo |
| L2 | Một màn đủ thông tin + điều khiển cho hầu hết việc | Màn rang (AUTO+MANUAL chung) |
| L3 | Chi tiết 1 thiết bị, chẩn đoán, interlock | Đầu đốt, biến tần, cân |
| L4 | Hỗ trợ, quy trình, chẩn đoán sâu | Hiệu chuẩn, cài đặt nhà máy |

## 4. Ngưỡng & mặc định

- Phản hồi nhấn ≤ 100 ms; việc > 1 s có tiến trình + ước lượng thời gian (nói hơi dài hơn thực).
- Bộ nhớ làm việc: tính 3–5 mục; không bắt mang số từ màn này sang màn khác.
- Mỗi màn vận hành: 1–2 trend nhúng sẵn, có lịch sử khi mở, vạch giới hạn nét đứt + dải bình thường nhạt.
- Thử dùng: 5 người / vòng, sửa, 5 người khác; thử theo cặp, nói to.
- Khoá vì sai PIN: ngắn (OTL: 30 s), không khoá khi đang rang / làm nóng.

## 5. Dấu hiệu xấu (thấy là sửa)

- ⛔ Vạch đỏ / dải màu dán ở cạnh trên, cạnh dưới, cạnh trái của nút hay thẻ; gạch chân màu cho mục đang chọn → chủ máy CẤM tuyệt đối.
- ⛔ Mặt nút, dock, dải trạng thái màu đen → chủ máy đã bỏ màu đen (11/10/2026).

- Giấy note dán cạnh nút / người hỏi "bấm đâu?" → thiếu signifier.
- Hàng nút giống hệt nhau, chỉ khác chữ nhỏ → sắp có bấm nhầm.
- Màn toàn số, không trend, không dải bình thường → vận hành theo báo động.
- Bơm/quạt quay, lửa động, bình 3D chói → 90% diện tích cho tranh, 10% cho dữ liệu.
- Màu đỏ dùng trang trí / cho trạng thái thường → màu báo động mất nghĩa.
- Báo động kêu cùng lúc, cùng tiếng, người ta tắt tiếng → hệ báo động hỏng.
- Toast lỗi tự biến mất → người không kịp đọc.
- Chế độ chỉ báo bằng chữ nhỏ ở góc → mode error đang chờ.
