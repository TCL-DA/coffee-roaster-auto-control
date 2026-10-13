# Chẩn đoán profile và lỗi vị

## Thứ tự

1. Xác minh probe, timestamp, đơn vị và bộ lọc.
2. Xác minh trạng thái nhiệt máy, cỡ mẻ, hạt và thao tác thật.
3. Chồng mẻ từ charge; so sự kiện và lệnh, không chỉ BT.
4. Tìm đầu vào thay đổi trước sai lệch theo đúng độ trễ máy.
5. Kiểm tra bằng màu, hao hụt và cupping; hình dạng curve không tự chứng minh khuyết tật.

| Hiện tượng | Cơ chế khả dĩ | Thử nghiệm phân định |
|---|---|---|
| RoR crash quanh FCs | cắt gas sớm/mạnh, đổi airflow, bay hơi và probe response | giữ hạt/preheat, giảm mức cắt hoặc đổi thời điểm một bước |
| Flick sau FCs | nhiệt tích trữ, tăng gas chữa crash, airflow đổi | bỏ lệnh tăng muộn, xử lý năng lượng sớm hơn |
| Baked/flat | thiếu năng lượng kéo dài/stall | tăng động lượng có kiểm soát trước chỗ hụt, giữ màu drop |
| Underdeveloped | lịch sử năng lượng hoặc phát triển chưa đủ | kiểm tra màu trong/ngoài; tăng phát triển hữu ích, không chỉ kéo dài |
| Scorching | trống/charge quá nóng, đảo kém | giảm tải dẫn nhiệt đầu mẻ hoặc chỉnh charge/RPM trong giới hạn |
| Tipping | tốc độ gia nhiệt bề mặt quá cao | giảm cường độ sớm; xét density/moisture/size |
| Smoky/ashy | thoát khói kém, rang sâu, hệ bẩn | vệ sinh và xác minh draft trước khi sửa profile |
| Mẻ sau nhanh hơn | máy chưa cân bằng nhiệt giữa mẻ | chuẩn hóa between-batch protocol |

## RoR

- Công thức cơ bản: `RoR = ΔBT / Δt × 60`, Δt bằng giây; luôn ghi cửa sổ và bộ lọc.
- Không điều khiển theo một điểm. Dùng xu hướng, độ dốc, độ trễ và confidence.
- Đánh dấu lệnh gas/gió/trống; tìm phản ứng sau lệnh thay vì gán mọi biến động cho FCs.
- So mẻ bằng BT, RoR, sự kiện, control trajectory và trạng thái máy. Một điểm “match %” có thể che sai lệch theo pha.

Mẫu hump–crash–flick (Scott Rao), ảnh hưởng vị của từng đoạn, vị trí/đường kính đầu dò và vì sao TP, đỉnh RoR không có nghĩa tuyệt đối: `probat-vat-ly-thiet-bi.md` mục 4. Vị khói do rang quá đậm hoặc vỏ lụa cháy trong cyclone: `probat-van-hanh-hat-xanh.md` mục 6. Vì sao không điều khiển bám RoR: `probat-dieu-khien-du-lieu.md` mục 2.

Nghi sensor khi có bước nhảy phi vật lý, flatline, BT/ET bất thường hoặc thay đổi lớn sau bảo trì probe. Nghi process khi sai lệch có quan hệ thời gian hợp lý với gas/gió/cỡ mẻ/preheat và lặp lại cùng điều kiện.
