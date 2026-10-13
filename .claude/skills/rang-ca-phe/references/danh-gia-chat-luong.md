# Đánh giá chất lượng và học từ dữ liệu

## Bộ đo tối thiểu

- khối lượng xanh/rang; `% hao hụt = (xanh - rang) / xanh × 100`;
- màu hạt nguyên và xay, cùng thiết bị/cách chuẩn bị/thời điểm;
- thời gian làm nguội, độ đồng đều, quaker/scorching/tipping và màu trong/ngoài;
- cupping mù; với pha thực tế ghi recipe, TDS/extraction yield nếu có.

Không dùng hao hụt, Agtron hoặc DTR đơn độc để suy “đã phát triển”. Cách Backyard Coffee ghép màu (xay + rây) với TDS để tìm "central balance point" (hoà tan cao nhất ở màu sáng nhất), và khử khí/bảo quản trước cupping: `probat-dieu-khien-du-lieu.md` mục 4, `probat-sau-rang-xay-khu-khi.md`. Hai mẻ cùng màu ngoài vẫn có thể khác lịch sử nhiệt và vị.

## Cupping/CVA

- Ghi mô tả trước khi chấm thích/không thích.
- SCA CVA 2023 tách **descriptive**, **affective** và **extrinsic**; không trộn thuộc tính với giá trị thị trường.
- Giữ roast date/rest, grinder, nước, tỷ lệ, nhiệt và quy trình giống nhau; dùng đối chứng và lặp mẫu khi quyết định quan trọng.
- Rang mẫu nhằm so nguyên liệu dưới một protocol ổn định, không phải tối ưu profile sản xuất. Ghi máy sample roaster, charge, thời gian, màu, hao hụt và mọi lệch protocol.
- Khi chẩn đoán mẻ sản xuất, cup cùng màu/mức chiết xuất hợp lý nếu câu hỏi là tác động của profile; nếu không, khác biệt chiết xuất có thể bị nhầm thành khác biệt rang.
- Degassing và tốc độ ageing phụ thuộc mức rang, cấu trúc, bao bì, nhiệt độ và trạng thái nguyên hạt/xay. Không áp một số ngày nghỉ cố định cho mọi lô.

## Dataset AI

Mỗi mẻ cần:

1. **Context:** hạt/lô/sơ chế/moisture/density/size, máy, cỡ mẻ, môi trường.
2. **State:** preheat, BT/ET/pressure, burner/damper và thời gian giữa mẻ.
3. **Action:** gas, airflow, drum, sự kiện với timestamp thật.
4. **Outcome:** màu, hao hụt, lỗi, cupping, brew metrics và nhận xét.

Tách train/validation theo lô và ngày rang, không chia ngẫu nhiên các điểm của cùng mẻ. Bắt đầu bằng rules/thống kê; rồi dự báo BT/RoR và sự kiện; replay offline; shadow mode; tư vấn có duyệt; cuối cùng mới lệnh hữu hạn. Hàm mục tiêu phải gồm profile, giới hạn, độ mượt actuator, năng lượng, độ lặp và cảm quan, không chỉ MSE BT. Theo dõi drift khi đổi hạt, probe, burner, vệ sinh, mùa hoặc cỡ mẻ.
