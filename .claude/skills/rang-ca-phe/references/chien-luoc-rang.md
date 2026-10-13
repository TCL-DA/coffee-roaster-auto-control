# Lập và chỉnh chiến lược rang

## Dữ liệu tối thiểu

Thu thập hạt/sơ chế/tuổi/moisture/density/size; máy và cỡ mẻ; charge, BT/ET, gas, airflow/vacuum, trống; TP/Yellow/FCs/Drop; màu, hao hụt, mục đích pha, cupping; preheat, thời gian giữa mẻ và vệ sinh. Thiếu gì phải ghi rõ giả định.

## Trước charge

- Preheat phải tạo trạng thái nhiệt ổn định, không chỉ chạm một số BT. Theo dõi BT đứng, ET–BT gap, RoR nhỏ và độ lặp lại.
- OTL SOP tham khảo: làm nóng ít nhất 15 phút và ổn định 3–5 phút; phải kiểm tra manual đúng model. PROBAT khuyên 40–60 phút với quạt max và coi khí thải đứng yên là dấu hiệu xong; cỡ mẻ quá nhỏ/quá tải và hạt cũ mất ẩm: `probat-van-hanh-hat-xanh.md`.
- Giữ cỡ mẻ, thời gian nạp và trạng thái damper giống nhau khi so sánh.

## Profile nền

1. Rang thủ công an toàn, ghi mọi thao tác/sự kiện.
2. Đủ động lượng đầu mẻ nhưng không quá tải bề mặt.
3. Giảm năng lượng theo dự báo; không chờ tới FCs mới xử lý nhiệt tích trữ.
4. Dùng airflow để cân bằng truyền nhiệt, thoát ẩm/khói/chaff và áp suất; không mặc định gió cao luôn làm nguội hoặc luôn tăng nhiệt.
5. Tốc độ trống hỗ trợ đảo hạt/thời gian tiếp xúc trong giới hạn cơ khí, không phải nút chữa mọi lỗi.
6. Drop theo mục tiêu cảm quan và trạng thái hạt, không chỉ theo nhiệt; làm nguội nhanh, đều và ghi thời gian.

## Cây quyết định khi chuyển lô

1. Nếu thiếu dữ liệu/profile của lô nền trên cùng máy, cỡ mẻ và trạng thái nhiệt: chạy một mẻ control có giám sát; không tự kê delta gas, charge hay drop.
2. Nếu lô mới nhanh/chậm hơn rõ trước Yellow hoặc FCs: xác minh preheat, cỡ mẻ, probe và thao tác; mẻ kế chỉ đổi một bước năng lượng **sớm** theo hướng cần kiểm chứng.
3. Nếu khói, chaff hoặc áp âm bất thường: kiểm tra cyclone/đường ống/vệ sinh và airflow trước khi chữa bằng profile.
4. Nếu độ đồng đều kém: kiểm tra sampling, defect, screen/density/moisture/aw và cân nhắc phân loại hoặc split roast; không đuổi theo một curve để che lô không đồng nhất.
5. Đánh giá delta bằng màu nguyên/xay, hao hụt, màu trong/ngoài và cupping mục tiêu. Không giữ cứng nhiệt FCs/drop hoặc DTR giữa hai lô.

Không bịa phần trăm gas hay số độ từ tên origin/process. Biên độ “một bước” phải theo độ phân giải actuator, profile nền và giới hạn của đúng máy OTL.

## Theo pha

- Đầu mẻ thiếu động lượng: xem charge state, gas đầu, cỡ mẻ, airflow; không vội nâng charge nếu có cháy mặt.
- Trước Yellow: thao tác sớm ảnh hưởng tới FCs; giảm gas quá sâu có thể thiếu năng lượng muộn.
- Browning: tránh chuỗi giảm–tăng do phản ứng với tín hiệu trễ.
- Trước FCs: dự báo nhiệt tích trữ; thay đổi 30–90 giây trước FCs có thể quan trọng hơn lệnh ngay FCs.
- Sau FCs: giữ đủ phát triển, kiểm soát khói/runaway; thay đổi mạnh dễ tạo crash rồi flick.

## Thử nghiệm và AI

Mỗi thử nghiệm có một giả thuyết, một biến chính, biến giữ nguyên, dự đoán curve/cảm quan và tiêu chí dừng.

- **Quan sát:** chuẩn hóa log, phát hiện sự kiện, sai lệch và sensor fault.
- **Tư vấn:** một thay đổi hữu hạn kèm lý do, confidence và cửa sổ áp dụng; người vận hành duyệt.
- **Tự động:** lệnh hữu hạn trong lease, giới hạn biên độ/tốc độ, watchdog, audit log và takeover. Không để mô hình thay safety PLC/firmware.
