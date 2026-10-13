# PROBAT — bảo trì, mã lỗi, áp suất và an toàn thiết bị

Tóm lược có diễn giải từ kênh PROBAT, Probat USA (kỹ thuật viên), Probat Indonesia và vài kênh đại lý. Dùng để hiểu **logic chẩn đoán**; mã lỗi, giá trị áp, khe hở là của máy PROBAT P-series, không áp nguyên cho OTL. Việc gas, điện, burner phải do người đủ chuyên môn làm theo manual đúng model.

## 1. Nguyên tắc lập lịch (EFlimcdVmsQ, 0DmGTSMShBc, HrUUR5Z_xF0)

- Không có chu kỳ cố định cho mọi xưởng: bắt đầu theo giờ khuyến nghị trong manual, mở ra kiểm tra, ghi lại, rồi tự dựng lịch theo sản lượng và độ đậm (rang đậm, nhiệt cao bám dầu nhiều hơn). Bảo trì trước mùa cao điểm.
- Trọn gói ~2 h khi quen; lần đầu/lâu không làm nửa tới một ngày.
- Phụ tùng nên sẵn: 2 điện cực kèm vít, gioăng đầu đốt, mỡ chịu nhiệt, chổi, máy hút bụi tốt. Hoá chất tiếp xúc hạt phải an toàn thực phẩm. Phụ tùng "critical" xét theo **thời gian giao hàng**, không chỉ xác suất hỏng.

## 2. Lịch tham khảo P-series (19NmsDlAZLE manual P5 III, EFlimcdVmsQ, 3jXJbi_5rMk, lJbzjR2Ci98)

| Tần suất | Việc |
|---|---|
| Mỗi 2–4 (tới 3–8) mẻ, đổ cuối ngày | Thùng vỏ lụa cyclone; khay vỏ lụa cạnh máy. Đầy thì vỏ lấp ống trong cyclone → mất lưu thông khí, nguy cơ cháy |
| Hằng ngày / giữa ca | Ngăn hứng mảnh lọt khe trống–tấm trước (không để rơi vào đầu đốt); cần gạt/van lấy mẫu; hopper hút bụi |
| Hằng tháng | Chổi thông ống, damper |
| 3–4 tháng (giãn dần nếu mỡ còn tốt) | Bơm mỡ bạc trước (mỡ chịu nhiệt; lau mỡ cũ đen, vón) |
| ≥ 6 tháng | Mở quạt hút + ống giữa máy và cyclone (~1 h trên P5); quạt cyclone |
| Hằng năm | Kiểm bẩn động cơ, quạt rang/nguội; thay lọc; functional check an toàn |
| 10.000 h hoặc tối đa 2 năm | Thay dầu hộp số động cơ trống (thay lúc dầu còn ấm, đúng loại dầu chịu nhiệt trên nhãn) |
| Khi cần (thường ≥ 2 năm) | Điện cực đánh lửa/cảm biến lửa (vật tư hao mòn) |

- Lọc gió đầu đốt: thổi khí nén từ trong ra, dùng lại vài lần rồi thay; gần như vĩnh viễn trừ khi dính dầu/ướt.
- Khay nguội: bánh lăn thông lỗ từng hàng; bật quạt nguội rồi quét cặn dưới sàng cho quạt hút đi.
- Trống không cần vệ sinh nếu chỉ rang cà (hạt tự mài). Cần vệ sinh khi rang organic có chứng nhận hoặc sản phẩm gây dị ứng (hạt điều, hạt dẻ…); đổi loại thì chạy một mẻ hột cherry lau cơ học.
- Kính quan sát: nước rửa bát/tẩy dầu, cạo cẩn thận. Bánh quạt: ngâm nước ấm + nước rửa bát qua đêm. Vệ sinh quạt/cyclone dễ nhất khi còn ấm ~80–90 °C (dầu mềm) — cẩn thận bỏng.
- Bạc sau P-series là bạc graphite/kín mỡ khô, **không bảo trì**; kêu rào rạo lúc nguội hoặc khi có tải là bình thường, kêu mãi mới gọi hãng. (Đại lý Wolff nói "thay bạc sau mỗi ~2.000 giờ" — mâu thuẫn với hãng, xem mục 8.)

## 3. Vì sao ống/quạt bẩn làm trôi recipe (EFlimcdVmsQ, 7CdUy9hvNfs)

Cặn dầu + bụi bám dần như sơn → **gió giảm** → máy lấy ít nhiệt ra → nhiệt tăng nhanh hơn → recipe trôi dần mà không nhận ra, thợ chỉnh bù dần; vệ sinh xong gió tăng đột ngột → recipe đổi hẳn. Quạt bẩn còn **mất cân bằng** → rung, ồn, "cyclone nhảy". Có roastery giữ bánh quạt dự phòng để thay nhanh mùa cao điểm.

Đoạn ống có slide gate: chụp ảnh trước khi tháo, lắp lại đúng chiều (ngược chiều thì bám nhiều và kẹt).

## 4. Mã lỗi P-series (Probat USA: q-POR3fsvYs, bWhufDJpF1w, QJ7_vlmdjpU, eyJ7KZQvJDQ, nLOYAoZbBQY, pHt4AoumGBI, 9zmNNZRDIpI; Indonesia qWWKmCfC5Yw)

| Mã | Nghĩa | Trình tự kiểm |
|---|---|---|
| **110** | Sự cố truyền động **trống** (bảo vệ động cơ MCP nhảy vì động cơ gặp cản) | Hay gặp nhất: trống nóng giãn cạ tấm gang trước → đo **khe trống**. Kẹp ampe dây ra MCP, so dòng với nhãn động cơ; dòng cao → dây lỏng, tụ động cơ hỏng (P12 động cơ 1 pha có tụ trong hộp đấu dây), hiếm khi bạc; động cơ mòn kéo dòng cao |
| **112** | Sự cố **quạt rang/quạt cyclone** | Như 110 + làm sạch ống + đo áp âm trống bằng manometer (mục 5); lệch thì chỉnh damper hoặc tăng VFD quạt |
| **115** | Sự cố **bộ đánh lửa tự động** (phổ biến nhất) | (1) áp gas cấp; (2) công tắc áp gas thấp (LED sáng = đủ); (3) công tắc áp hỗn hợp gas; (4) công tắc áp âm khí thải (LED sáng = đạt); (5) vị trí/tình trạng điện cực; (6) giữ nút reset đỏ trên bộ đánh lửa 5 s → máy thử đánh lửa lại |
| **116** | **Áp âm khí thải thấp** | Vật cản thông gió; vệ sinh ống (cặn từ hạt bám dần); thùng vỏ lụa trống, lắp khít, khoá đúng (hở là lọt khí, tụt áp). Báo 116 đúng lúc **xả hạt** làm tắt gas: đang chạy áp sát ngưỡng, mở cửa xả khí tràn vào → tăng quạt hút một chút khi xả |
| Khác | Alarm lúc bật máy; "Communication fault to PLC" | Kiểm áp gas cấp + đèn vàng ở firing unit; kiểm cáp PLC–I/O ở hộp đấu nối bên hông |

- **Interlock áp âm**: dưới ngưỡng thì gas train không đánh lửa; đang cháy mà tụt dưới ngưỡng thì gas train tắt. Lý do: khí dễ cháy từ gas train tích trong vùng rang là nguy hiểm, phải hút ra. Áp cao hơn ngưỡng không nguy hiểm nhưng **đổi mẻ rang**.
- Khởi động/tắt máy sai quy trình (tắt bằng E-stop, burner khác 0) dễ sinh 115/116 lần sau.

## 5. Kiểm áp gas và áp âm (NsCu0lCCjgM, 9pzzO6CcrUE, 4g-dFECjmyA, XhAM5UKLbbc)

- Hai thông số quan trọng nhất: **áp gas** và **áp âm khí thải**. Theo thời gian điện lực đổi áp gas, đường gas có vấn đề, ống thải/mái bị cản → kiểm định kỳ.
- Đồng hồ gas sau máy chỉ tương đối (VD đồng hồ 16 vs manometer 18,56 inWC) → dùng manometer, zero trước; gas đơn vị inWC, áp âm mbar; vặn vít cổng đo đúng ~2 vòng, đo xong siết lại.
- Áp gas cấp: Probat USA nêu 10–20 inWC ở một video, 10–12 inWC để chạy 100% ở video khác, lý tưởng ~14 inWC ở video thứ ba; công tắc áp gas thấp đặt 5 inWC. Indonesia nêu 30–50 mbar (thị trường đó). → **Không có một con số chung**; theo manual và loại gas.
- Áp âm: xuất xưởng −2 mbar, đo ở nhiệt phòng (máy nóng số đổi là bình thường). Công tắc áp là linh kiện cơ điện, 5–20 năm có thể hỏng → kiểm chéo bằng manometer. Series III đọc áp âm ngay trên HMI.
- Thay công tắc áp khí thải: vặn vít + đai ốc đồng có gai vào vỏ trước cho gai cắm chặt, rồi mới luồn dây siết.

## 6. Đầu đốt và điện cực (2Isz-wd0Kmc, pHt4AoumGBI, EFlimcdVmsQ, YL-sdHO3on0, sH0HzlVvgNA)

- Điện cực có 2 chức năng: **mồi lửa** và **cảm biến lửa**.
- Vệ sinh bằng giấy nhám rất mịn, nhẹ tay, không làm xê dịch. Probat USA: khe **1,5 mm**, góc **45°** hướng về vách trong. Video PROBAT DE: khe đầu điện cực – đầu đốt 3–5 mm, điện cực nằm trên mép đầu đốt (khác đời/khác cách đo → theo manual).
- Chỉnh vị trí: nới ra rồi đặt lại; bẻ cong bằng lực thì khi nóng tự về vị trí cũ.
- Thay: cờ lê vòng 12 mm (cờ lê miệng dễ trờn), siết nhẹ; cắm lại đầu cáp phải nghe **click thứ hai**.
- Tháo đầu đốt: 4 vít, hút bụi, kiểm gioăng trước khi lắp.
- Máy sample roaster điện: ghim bấm từ túi mẫu rơi vào đầu đốt gây chập, cháy gốm.

## 7. Cơ khí trống (girTWOFUNjc, 4UMU5RkfOog, dW-aPlICWdA, DQhfClOEUY0, lKQ-hvdIEqo, RnBHDGLkE_k, GUoLCQbKGpI)

- **Khe trống – tấm trước**: quá rộng → ảnh hưởng luồng gió, hạt nguyên lọt xuống ngăn kéo; quá hẹp → trống cạ tấm trước, tải động cơ, nhảy CB/lỗi 110. Dấu hiệu: tiếng cạ phía trước, hạt vỡ lớn ở cần lấy mẫu, nhiều mảnh lọt.
- Đo: nới vít chìm trước khi mở cửa xả (không thì phá chốt), tháo cửa xả + hopper, thước lá; đo trái–phải–dưới (phía trên hở hơn **chủ ý** theo thiết kế). Đúng khi thước lá kẹt chặt không trượt.
- Chỉnh: **luôn nới 3 vít chặn** (lục giác chữ T 2,5 mm) trước, vặn đai ốc chỉnh bạc trước (vào đẩy trống ra sau, ra kéo trống lên trước), chỉnh xong **siết lại** — quên siết thì trống xê dịch dần khi rang.
- Thay bạc trước: tháo phanh hãm, cảo 3 chấu; khi lắp chặn trục trống phía sau (trục trượt được), để lộ 3 ren trên đai ốc chỉnh, gõ bạc đều, rồi chỉnh khe.
- Tháo động cơ trống: rút giắc, tháo phanh hãm, kéo thẳng cả động cơ + hộp số. Kẹt thì **không đập** (cong trục); dùng cảo. Lắp lại: đánh sạch trục, vệ sinh then, bôi chống kẹt food-grade.
- Động cơ khuấy khay nguội: kiểm dầu ở vít mức; côn trượt thì siết núm; vẫn kêu mà tay khuấy không quay là hộp số hỏng.
- **Dây lỏng** là lỗi phổ biến nhất máy vài năm tuổi (rung 10–20 năm). Trình tự: CB 24 V cấp PLC/HMI → MCP bảo vệ động cơ (cần gạt nằm ngang = đã nhảy) → nút tiếp điểm tay trên MCP (động cơ chạy = dây tới động cơ tốt) → contactor, kéo nhẹ từng dây → đo dòng dưới MCP (chỉ bật máy khi đã chắc dây chặt).
- HMI P-series II tự về °C mỗi lần bật → hết pin CR2032 sau màn.

## 8. Mâu thuẫn giữa các nguồn — đừng chọn bừa

| Mục | Nguồn A | Nguồn B | Cách xử lý |
|---|---|---|---|
| Khe trống – tấm trước | Manual/Indonesia: 0,5 mm | Probat USA thực tế: ~1,5 mm (0,06 in) đều các phía, vì trống nóng giãn | Theo manual đúng đời máy; nếu lỗi 110 lặp khi nóng thì xét khe giãn nở |
| Áp gas cấp | 10–20 inWC | 10–12 inWC / ~14 inWC lý tưởng; 30–50 mbar (Indonesia) | Theo manual + loại gas nơi lắp |
| Bạc sau | PROBAT DE/USA: không bảo trì | Đại lý Wolff: thay mỗi ~2.000 giờ | Theo hãng; nghe tiếng + nhiệt để quyết |
| Khe điện cực | USA: 1,5 mm, 45° | DE: 3–5 mm tới đầu đốt | Hai phép đo có thể khác điểm tham chiếu; theo manual |
| Tắt máy | Manual: burner 0 rồi chờ nguội | USA: chờ < 80–90 °C (chặt hơn manual) | Chọn mức chặt hơn |

## 9. An toàn thiết bị (3HXG9vEyLyc, r0sxeu-IMKs, service-chapters, QiEYXnpqves, Px120 _t-1ANcJws4)

- Mỗi máy test 1 mẻ trước khi giao: đúng loại gas, van và van chỉnh áp, phần mềm, **dòng điện từng động cơ** ghi biên bản, **chiều quay 3 pha**, burner đủ công suất.
- Nghiệm thu: safety checklist kiểm từng công tắc an toàn phần cứng + phần mềm theo chức năng (VD quá áp/quá nhiệt → cảnh báo → phun nước); khách phải tự làm **functional check an toàn mỗi năm**.
- Cyclone có đầu nối nước dập lửa; tuỳ chọn cảm biến nhiệt cyclone mở nước dập vỏ lụa. Hệ nước (water train) trên máy lớn: quench + nước khẩn cấp cho trống và khay nguội.
- Hệ ống nóng máy lớn đạt SIL 2 (đo nhiệt/áp kép kiểm chéo); smart thermocouple đạt mức safety-rated.
- Lọc bụi có dò tia lửa liên động máy rang; CO trong ống thải 2 ngưỡng (kết thúc mẻ / dừng tức thì + nước).
- Hỗ trợ từ xa: không sửa được thermocouple, bạc đạn từ xa → hướng dẫn khách tự làm hoặc cử thợ mang phụ tùng.
- Hydro: xem `probat-vat-ly-thiet-bi.md` mục 5.

## Áp dụng cho OTL

- Khi khách báo recipe "tự trôi", hỏi lần vệ sinh ống/quạt gần nhất và áp âm trước khi sửa profile hoặc đổ lỗi điều khiển.
- Ghi mọi sự kiện bảo trì (vệ sinh ống, chỉnh khe trống, thay điện cực, chỉnh damper) vào dataset như mốc đổi epoch.
- Thiết kế cảnh báo OTL nên phân biệt rõ: lỗi truyền động, lỗi quạt, lỗi đánh lửa, áp âm thấp — mỗi loại một trình tự kiểm như bảng mục 4.
