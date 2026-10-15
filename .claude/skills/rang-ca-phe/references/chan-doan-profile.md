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

## Cách tính David — hằng số truyền nhiệt k

Dùng khi người dùng nói "cách tính David", hoặc khi mẻ không lặp lại được, Agtron lệch, RoR cuối mẻ vẫn cao dù đã giảm lửa, nhất là sau cúp điện / sửa đường gas. Nguồn: phân tích 6 mẻ thật của một khách máy 3 kg (10/2026).

**Công thức** (mô hình Newton): `RoR = k × (ET − BT)` → **`k = RoR / (ET − BT)`** (RoR °C/phút, ET/BT °C).

**Cách làm:**
1. Lấy mẻ mẫu tốt và các mẻ nghi lỗi (.alog hoặc ảnh Artisan), cùng máy, cùng cỡ mẻ.
2. Đọc ET, BT, RoR tại nhiều mốc dọc mẻ (vd 3:00, 6:00, 9:00, 11:00, cuối phát triển), tính k từng mốc.
3. Mẻ mẫu chuẩn: k gần phẳng suốt mẻ (ca gốc: 0,13 → 0,11 → 0,12 → 0,128 ở 11:00).
4. Mẻ nghi lỗi: xem k có vọt lên ở cuối mẻ không (ca gốc sau cúp điện: 0,280 / 0,295 / 0,186–0,231). Kiểm chéo ca gốc mẻ 12/10 lúc ~11:00: ET≈238, BT≈206, RoR≈9 → k≈0,28; mẻ mẫu ET≈247, BT≈200, RoR≈5,5 → k≈0,12.

**Luật suy luận:**
- Lô nhân xanh khác → k khác, nhưng vẫn là một hằng số; k không thể tăng trong lúc rang.
- k tăng cuối mẻ = hạt nhận nhiều nhiệt hơn mức ET−BT giải thích → nhiệt đi đường ET không thấy: **thành trống (dẫn nhiệt)**, không phải không khí.
- k vọt mạnh nhất đúng lúc lửa thấp nhất (vd B19 → B5) = ngọn lửa đáng lẽ rất nhỏ lại đốt nhiều nhất → **gas thực > lệnh ở mức thấp** → nghi **điểm 0 van gas lệch**, không phải sai lệch 5 % ở thang đo.

**Giới hạn và giả thuyết cạnh tranh:** k không tuyệt đối hằng (phụ thuộc gió, tốc độ trống, ẩm hạt, nhiệt sinh lúc nổ) — chỉ so giữa các mẻ cùng máy, cùng gió/trống; mẻ mẫu cũng qua nổ mà k vẫn phẳng thì phép so mới có giá trị. Phải loại trừ:

| Giả thuyết | Dấu hiệu phân biệt |
|---|---|
| Lệch điểm 0 van gas tỷ lệ | Lửa to bất thường chỉ ở mức thấp; áp gas bình thường |
| Van giảm áp hỏng, áp gas cao | Lửa to ở mọi mức; đồng hồ áp cao hơn lúc lắp máy |
| Đầu dò ET bẩn / lệch vị trí | k cao cả mẻ, không chỉ cuối mẻ |
| Gió yếu (nghẹt cyclone, ống vỏ lụa) | Áp âm / tần số quạt đổi; ET thấp hơn mọi mức lửa |

**Xác nhận:** máy nóng, không hạt, cho lửa 0 → 5 → 20 → 50 → 100 %, mỗi mức quay ngọn lửa + đồng hồ áp ~30 s, so với áp chuẩn lúc lắp máy.
