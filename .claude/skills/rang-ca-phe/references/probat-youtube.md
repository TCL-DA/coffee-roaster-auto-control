# Kho tri thức PROBAT — cổng vào

Tổng hợp **toàn bộ** nguồn công khai của PROBAT đã quét (16–17/09/2026): 300 video YouTube của 3 kênh chính thức (PROBAT Global 171 gồm 56 livestream, Probat USA 59, Probat Indonesia 70), 103 video bên thứ ba, 21 video Bilibili, 115 trang kỹ thuật probat.com. Nội dung là tóm lược diễn giải tiếng Việt, không chép nguyên văn. Độ phủ chi tiết, video không lấy được và cách tra lại gốc: [probat-nguon-danh-muc.md](probat-nguon-danh-muc.md).

## Định tuyến theo câu hỏi

| Cần gì | Đọc |
|---|---|
| Đối lưu/dẫn nhiệt, tổn thất áp, quạt, slide gate, độ cao; cấu tạo trống 2 vách, đầu đốt premix/UG, flavor wheel; vị trí và tốc độ đầu dò; máy điện, hydro, LPG | [probat-vat-ly-thiet-bi.md](probat-vat-ly-thiet-bi.md) |
| Bám BT vs RoR, supply-air control, REFLEX, dải + control point, chuyển recipe giữa máy, Colour/Moisture Control, digital twin/MPC, giao diện alarm, Norm Roast, dữ liệu | [probat-dieu-khien-du-lieu.md](probat-dieu-khien-du-lieu.md) |
| Preheat 40–60′, mẻ đầu, cỡ mẻ, số liệu thực hành P5/Px120, giới hạn drop; hạt xanh (độ tươi, mùa vụ, bảo quản, sơ chế); blend trước/sau; vị khói; làm nguội; lắp đặt; tắt máy | [probat-van-hanh-hat-xanh.md](probat-van-hanh-hat-xanh.md) |
| Phản ứng thu/tỏa nhiệt, quench, khử khí CO2, bảo quản, vận chuyển hạt rang, xay, capsule, acrylamide | [probat-sau-rang-xay-khu-khi.md](probat-sau-rang-xay-khu-khi.md) |
| Afterburner, xúc tác, ReCatino, PROFORTE, PROAIR, lọc mùi, bụi/ATEX, ồn, năng lượng, hồi lưu, preheater hạt xanh | [probat-khi-thai-nang-luong.md](probat-khi-thai-nang-luong.md) |
| Lịch bảo trì, ống/quạt bẩn làm trôi recipe, mã lỗi 110/112/115/116, áp gas/áp âm, điện cực, khe trống, bạc, dây lỏng, an toàn thiết bị, **mâu thuẫn giữa nguồn** | [probat-bao-tri-ma-loi.md](probat-bao-tri-ma-loi.md) |
| Cacao nguyên hạt vs nib, máy liên tục ngược dòng, khử khuẩn, kiềm hoá, ổn định bột cacao; hạt béo, malt, chicory | [probat-cacao-san-pham-khac.md](probat-cacao-san-pham-khac.md) |

## Mười bài học cốt lõi cho OTL

1. **Điều khiển năng lượng, không học thuộc % gas.** Nhiệt vào hạt phụ thuộc đồng thời chênh nhiệt và vận tốc khí; cùng lệnh quạt chưa chắc cùng airflow thật (tổn thất áp ∝ vận tốc²). Mô hình phải học `lệnh gas/quạt/trống → nhiệt khí + áp âm → BT/ET/RoR → kết quả`.
2. **Preheat là trạng thái phân bố nhiệt**, không phải chạm một số BT. PROBAT khuyên 40–60′ với quạt max; dấu hiệu xong là khí thải đứng yên vài phút. Mẻ đầu vẫn khác; bù bằng charge/end riêng cho vài mẻ đầu.
3. **Bám BT có dải theo pha, không bám RoR.** Bám RoR để lại offset BT vĩnh viễn. Dải rộng đầu mẻ, hẹp về sau; control point "đạt X °C trong [t1, t2]"; không điều khiển 60 s đầu sau charge.
4. **Tách mục tiêu quá trình khỏi actuator.** Máy công nghiệp đặt nhiệt khí cấp, burner tự điều chế. AI đề xuất mục tiêu hoặc thay đổi hữu hạn; tầng deterministic lo giới hạn và interlock.
5. **Chuyển recipe = giữ kết quả, không giữ đường nhiệt.** Mang thời gian pha, development, màu; chấp nhận 1–2 mẻ hiệu chỉnh. Đầu dò khác vị trí vài mm đã khác số.
6. **Đầu dò quyết định chất lượng dữ liệu.** Đầu dò dày/đặt cao → trễ, không ngập hạt mẻ nhỏ, RoR nhiễu. TP và đỉnh RoR không có nghĩa tuyệt đối. Mẫu hump–crash–flick của Scott Rao chỉ thấy được với đầu dò nhanh đặt đúng chỗ.
7. **Sự kiện vẫn cần người rang xác nhận.** PROBAT vẫn đánh dấu FCs bằng tay; nhận diện tiếng nổ còn thử nghiệm. Model âm thanh chỉ nên gợi ý xác suất + cửa sổ.
8. **Drop chưa phải hết truyền nhiệt.** Carry-over có thể +8,6 °C trong hạt; nguội < 5′. Sau FCs phản ứng tỏa nhiệt; máy lớn dùng quench và nước khẩn cấp.
9. **Bảo trì tạo model drift.** Ống/quạt bẩn giảm gió dần làm recipe trôi; vệ sinh xong gió tăng đột ngột. Ghi mọi sự kiện bảo trì thành mốc epoch và kiểm lại áp âm trước khi quy lỗi cho điều khiển.
10. **Hồi lưu, khí tươi, xử lý khí liên hệ nhau.** Giảm hồi lưu phải tăng khí tươi (cốc sạch hơn); hệ xử lý khí không được thêm tổn thất áp làm lệch mẻ; vị khói thường do rang quá đậm hoặc vỏ lụa cháy trong cyclone chứ không phải nhiên liệu.

## Kiến trúc AI OTL được củng cố

1. **Observer:** kiểm tra freshness/plausibility, nhận dạng pha, thermal state, lệch profile, bất thường thiết bị (áp âm, dòng động cơ).
2. **Predictor:** dự báo BT/RoR ngắn hạn (PROBAT + Cropster dự báo 120 s) và xác suất Yellow/FCs/Drop trong khoảng tin cậy.
3. **Advisor:** một thay đổi hữu hạn, giải thích nguyên nhân và ảnh hưởng dự kiến.
4. **Supervisor deterministic:** lease, slew/range limit, interlock, watchdog, fallback. PROBAT nhấn mạnh bên trong điều khiển máy chỉ dùng mô hình vật lý, không AI.
5. **Evaluator:** curve + actuator effort + màu + hao hụt + cupping + năng lượng/mẻ.

Không huấn luyện end-to-end từ curve sang lệnh gas khi thiếu trạng thái máy, airflow thật, lịch bảo trì và kết quả cảm quan.

## Giới hạn suy luận

- Nguồn là của hãng PROBAT và đại lý; có nội dung marketing (tiết kiệm năng lượng, "không khác vị", khấu hao máy). Không coi là bằng chứng độc lập.
- Phụ đề tự động (nhất là Indonesia, Trung, Đức) hay sai con số và tên linh kiện; con số dùng cho quyết định phải nghe lại đoạn gốc.
- Các nguồn PROBAT mâu thuẫn nhau ở khe trống, áp gas, bạc sau, khe điện cực — xem bảng trong `probat-bao-tri-ma-loi.md`.
- **Không** dùng ngưỡng an toàn, trình tự burner, áp gas, nhiệt xúc tác hay thông số quench của PROBAT cho OTL. Manual, source code và phép đo trên máy OTL mới xác định hệ thực tế.
