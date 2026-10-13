# An toàn và bảo trì

## Luật cứng

- AI không vô hiệu hóa/trì hoãn/thay E-stop, flame supervision, gas cutoff, over-temperature, motor/damper feedback, watchdog hoặc emergency quench.
- Telemetry mất/stale, sensor phi lý hoặc mất lease phải về trạng thái đã được kỹ sư an toàn xác nhận; không “đoán tiếp”.
- Không tự hiệu chỉnh VR1/VR2, van/burner/áp suất gas, khe trống, điện 400 V hoặc chữa cháy từ xa. Chỉ người đủ chuyên môn theo manual đúng model và đo tại máy.
- Không bê ngưỡng Probat/Loring sang OTL. Logic chẩn đoán PROBAT (mã lỗi 110/112/115/116, interlock áp âm, áp gas, điện cực, khe trống, dây lỏng) và bảng mâu thuẫn giữa các nguồn: `probat-bao-tri-ma-loi.md`.

## Rủi ro

OTL-120 liệt kê R01–R18: cháy trống/cyclone; nổ bụi; rò/nổ gas; cháy không hoàn toàn/CO; bỏng; điện giật; kẹp cơ khí; lỗi điều khiển an toàn; E-stop; quá nhiệt; khí nén; thiếu nước chữa cháy; mất pha/quá tải motor; EMC; an ninh mạng; mất feedback damper; phát thải; tiếng ồn. Với tự động hóa, ánh xạ từng lệnh AI tới hazard và interlock độc lập chặn hậu quả.

## Trước mẻ

Xác nhận thông gió/gas/lửa/motor/airflow/cooling/damper; cyclone không đầy, ống không tắc; gate/feedback đúng; nước/PCCC sẵn theo cấu hình; không còn alarm; đúng model, cỡ mẻ và giới hạn.

## Lịch tham khảo OTL

- chaff mỗi 4–6 mẻ; bụi dưới trống hằng ngày;
- khay làm nguội, dưới khay/burner, lọc gió khoảng 5–7 ngày;
- buồng quạt và ống xả khoảng 3–4 tuần;
- buồng đốt/motor khoảng 4–6 tháng;
- hệ đốt, van gas, đánh lửa, điện khoảng 6–12 tháng;
- dầu/bôi trơn theo manual; lịch tổng quát nêu 8.000 giờ hoặc 2 năm.

Đây không thay manual đúng serial/model. Kinh nghiệm PROBAT: ống/quạt hút bẩn làm gió giảm dần nên recipe trôi mà thợ không nhận ra, vệ sinh xong lại đổi đột ngột; đổ vỏ lụa trước và sau ca; tắt burner về 0 và chờ nguội trước khi tắt máy, không dùng E-stop để tắt thường ngày. Bụi/dầu/chaff làm đổi airflow, truyền nhiệt, độ lặp và nguy cơ cháy; phải loại trừ bẩn/tắc/hao mòn trước khi chữa curve bằng AI. Khi có khói/cháy hoặc alarm nghiêm trọng, ưu tiên quy trình khẩn cấp tại máy và lực lượng ứng cứu, không ứng biến trái manual.
