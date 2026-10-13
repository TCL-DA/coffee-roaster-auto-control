# PROBAT — điều khiển, chuyển recipe, cảm biến và dữ liệu

Tóm lược có diễn giải. Mã trong ngoặc là video YouTube trong `artifacts/probat-youtube-corpus-20260914/`; "web:" là trang probat.com.

## 1. Tiến hoá điều khiển (503cxjURIZA, WyOQ3IxMDx8, zdEXgD9jwCs)

- Đời cũ: AUTO chỉ **phát lại bước burner** của recipe (VD tới 150 °C giảm 80→60%) → không bù mùa, mật độ, ẩm; thợ phải canh.
- Đời mới (P01 → P25 chung phần mềm, gas/điện như nhau): AUTO **bám đường nhiệt sản phẩm** (product temp), burner tự tăng/giảm theo sai lệch. Trong AUTO thợ không chỉnh burner; burner mẻ mới khác mẻ gốc là bình thường. Drop sớm/muộn hơn recipe không làm hỏng recipe đã lưu.
- Mọi mẻ tự lưu history → gắn sao tạo recipe → dùng làm đường nền rang tay hoặc AUTO. Máy không kèm recipe; phải tự rang tay rồi tạo.
- Không lấy mẻ đầu ngày làm recipe gốc.

## 2. Vì sao bám BT chứ không bám RoR (503cxjURIZA)

RoR là đạo hàm của BT. Nếu mẻ đã lệch mà bộ điều khiển kéo RoR về đúng đích thì BT giữ **offset mãi**, không về lại đường mẫu. Bám BT thì vượt lố hiện ra thành lệch RoR và bộ điều khiển kéo BT về đường. RoR còn đổi theo tốc độ trống và gió.

Sau sai lệch: thừa năng lượng → rút ngắn/xả sớm một chút (màu có thể đậm 1–2 điểm); hụt → kéo dài một chút.

## 3. Điều khiển theo nhiệt khí cấp và REFLEX (_n6K5SBoUWw, 68jFMr-8irM, 3HXG9vEyLyc, UaSO05HMSYc)

- Máy công nghiệp và UG: thợ đặt **supply air temp**, burner modulating tự nhảy để giữ nhiệt khí cấp bất kể nhiệt ngoài trời, áp gas → lặp lại tốt hơn đặt % burner.
- Recipe công nghiệp (Pilot 2020): tab chung (khối lượng, tốc động cơ/quạt, trống, vị trí flap, lượng nước quench) + tới 19 bước giảm, mỗi bước theo product temp đặt supply air temp, lượng hồi lưu, quạt thải, khí tươi. Giảm hồi lưu phải tăng khí tươi; khí tươi làm cốc sạch hơn, bớt khói.
- UG: recipe 12 bước chuyển theo product temp (VD supply 410 °C tới 150 °C rồi bước sau); cửa sổ RoR chọn 15/30/60 s; trang F2 sửa khi AUTO thì lưu cho mẻ sau, trang F1 sửa thì **thoát AUTO** không quay lại trong mẻ đó; nhiệt tối đa nằm trang mật khẩu.
- **REFLEX**: kéo product temp về đường danh định bằng (1) hạ/tăng supply temp, (2) thừa năng lượng thì mở van bypass PR110 xả nhiệt ra ống thải (không có làm lạnh chủ động). Trễ kích hoạt 60 s sau nạp (giai đoạn nạp + tụt nhiệt không điều khiển). Hệ số cường độ 1 → 3–5 bám sớm hơn, chỉ admin/roast master được sửa. Gói Light/Comfort/Developer; Developer kéo tối đa 20 điểm sửa đường danh định thay vì rang thử. Đường vẽ lên xuống gắt máy không bám được vì khối thép/cách nhiệt.
- Dải chất lượng: vẽ vàng khi lệch trong dải (VD ±2 °C, chỉnh 1–5), đỏ khi ra ngoài; dải có thể rộng đầu mẻ (±10 °C tới 150 °C) và hẹp sau. **Control point**: "đạt X °C trong [t1, t2]" (VD 150 °C trong 390–450 s; 172 °C trong 210–220 s), tối đa 5 điểm; ngoài spec người duyệt vẫn có thể chấp nhận và ghi lại.
- Charge/end temp riêng cho 3–5 mẻ đầu ngày (bù máy chưa ấm). Mẻ đầu trên máy lớn có thể charge cao hơn máy nhỏ 10–15 °C, về sau gần lại.
- Curve design mode: kéo 3–20 điểm của một mẻ đã rang để tinh chỉnh; "online recipe" P60 cho thêm/bỏ điểm giảm ngay trong mẻ đang chạy.

## 4. Chuyển recipe giữa máy (7qI-Mpbts2Q, qRiHoUgYGJM, zXmmPYQIIKY, FPOAPrp65bo)

- Khó vì đường quạt, đường tổn thất áp, tấm gió, vị trí đầu dò, ống khói, khí hậu khác nhau. Mục tiêu chuyển là **cùng kết quả** (vị, màu, ẩm), không phải cùng đường nhiệt.
- Đại lượng thật cần giữ: **nhiệt truyền vào hạt**. Khí cấp mang nhiệt độ + lưu lượng khối, do 3 cơ cấu (burner, quạt, tấm gió) quyết định → 3 núm cho 2 biến → cần mô hình "flow state" riêng từng máy. Đồ thị **đẳng năng lượng** (vận tốc khí × chênh nhiệt): đi dọc đường đẳng thì cùng năng lượng vào hạt. Đường năng lượng theo hạt là phổ quát; đường theo máy phải đo.
- Thực hành PROBAT: P5 III → P25 III bằng AUTO thì đường bám nhưng FCs muộn và hạt sáng hơn; mẻ 2 rang tay theo đường mẫu + thêm năng lượng → đúng màu, đúng thời gian → lưu thành recipe P25. "Hai mẻ là chuyển xong", không plug-and-play.
- Mang sang máy mới: tổng thời gian, development, màu, dạng đường, sự kiện; **không** mang nhiệt tuyệt đối. Gợi ý drop khởi đầu 190–210 °C rồi chỉnh; giữ mẫu cũ để cupping so.
- **Phương pháp Backyard Coffee**: dựng trên mẫu 100 g rồi lên P12/P25. Đo màu (xay + rây lấy màu trung bình), TDS pha chuẩn hoá, cảm quan → Solubility Index + Development Index. "Central balance point" = độ hoà tan **cao nhất ở màu sáng nhất** (hạt chín đều trong–ngoài). Từ đó dựng ma trận 5 mức năng lượng × 5 điểm dừng = 25 profile; mỗi máy lệch một offset đo được. Liên kết máy bằng một cà tham chiếu ổn định. Chỉ làm được khi máy ổn định và preheat/BBP cố định (thiếu preheat chuẩn là lỗi phổ biến nhất).
- Anne Cooper (biz-skim-2): tài sản thật là **thời điểm các pha** xanh → nâu, chuyển được giữa máy, không phải đường trên màn hình.

## 5. Cảm biến quá trình (m8DEQc2AkCM, j7sUB4XNhOw, r0sxeu-IMKs, tradeshows-plant; web: colour-control, moisture-control, hotspot-detection, ground-coffee-degassing)

- **Colour Control**: cảm biến trong buồng rang, LED hồng ngoại, sợi quang, khí thổi purge liên tục chống bụi/hơi quench. Đường màu Px120: trống rỗng ~60, nạp hạt vọt ~400, đứng một đoạn, rồi giảm đều tới đích (VD 95) → quench; đo lại Colorette sau nguội 94 (±1). Dừng mẻ theo màu, đúng màu ngay mẻ đầu sau khởi động/đổi recipe. Lý do: nhiệt "sản phẩm" là nhiệt hỗn hợp nên nhiễu hơn màu.
- Thí nghiệm CTO: 3 profile khác nhau → đường màu trong mẻ khác nhau nhưng cùng màu cuối, cùng thời gian → vị có thể khác. Podcast Filter Stories: hai cà cùng màu có thể khác hương hoàn toàn theo đường rang.
- **Moisture Control**: cảm biến vi sóng sau làm nguội, giá trị trung bình **tự chỉnh lượng nước quench của mẻ sau** → ẩm thành phẩm ±0,1%; mục tiêu sát 5% ("sát 5% là tiền").
- **Hotspot**: camera nhiệt trên sàng nguội, ngưỡng theo thời gian nguội, vượt ≥3 s mới báo, 3 mức (báo động / nhắc kiểm tra chất lượng / chỉ ghi, VD sàng bẩn); lưu video theo mẻ.
- **CO trong ống thải** 2 ngưỡng: ngưỡng 1 kết thúc mẻ rồi dừng; ngưỡng 2 dừng toàn bộ + nước khẩn cấp. Giám sát tốc độ mọi bộ quay (kẹt), áp âm trống, lưu lượng ống (tắc), tắc vỏ lụa cyclone, rung quạt, nhiệt bạc.
- Smart dosing: cửa trượt có cảm biến vị trí, khe thô → tinh, thuật toán **tự học** theo tỷ trọng (cùng bài toán với bù quán tính auto-loader).
- Roastery thường >20.000 điểm dữ liệu cho 4 mục đích: chất lượng, điều khiển/hiệu suất, truy xuất, sẵn sàng máy.

## 6. Mô hình, digital twin, AI (503cxjURIZA, hv1z75fJVDs; web: how-mathematical-models)

- Hướng nghiên cứu: điều khiển theo **năng lượng** thay vì product temp. Mô hình gồm cân bằng năng lượng (khí vào/ra, kim loại, hạt, trao đổi hạt–kim loại, nhiệt **tỏa** của hạt cuối mẻ đậm), lưu lượng khí thật mỗi giây, hệ số truyền nhiệt từ CFD, mô hình hạt (tối thiểu ẩm ban đầu; mật độ/cỡ suy ra từ 2–3 mẻ thử). PROBAT nói rõ bên trong điều khiển máy chỉ dùng mô hình vật lý, không dùng AI.
- Hai digital twin (ĐH Bremen): máy (tải, công suất burner, vị trí flap, tốc quạt) và hạt (nhiệt **bề mặt** đo IR) → MPC dự đoán tương lai, tối ưu nhiệt nạp với năng lượng/chi phí tối thiểu; chuyển profile giữa máy có MPC vì dựa trên nhiệt nạp. Bộ điều khiển thường chỉ kéo về đường đích nhanh nhất, không tối ưu năng lượng.
- AI curve prediction (cùng Cropster): dự báo **120 giây tới** để phát hiện lệch sớm. Machine tuning: chạy mẻ tham chiếu + đưa máy vào vùng giới hạn → mô hình → cài đặt tối ưu cho tình trạng máy hiện tại.

## 7. Giao diện và quản lý alarm (L0P5Ae3nvoU, BvoyhFCWKjA, NhW8F1kej40, web: software-control-system)

- Đường product temp chạy trên đường mục tiêu, **đổi màu khi ra khỏi dải**; tô màu từng pha (preheat, rang, xả); thanh tiến trình pha; KPI chính trên màn.
- Không để bảng alarm thường trực: thông báo trượt vào theo cấp info/warning/alarm. Alarm chia object (gắn thiết bị, nút đi tới thiết bị) và process. Mỗi alarm kèm **nguyên nhân + hậu quả**, người dùng đính ảnh/video/ghi chú cách xử lý → thành kho tri thức cho ca sau.
- Faceplate động cơ: điều kiện cho phép chạy, nguyên nhân lỗi, giờ chạy/số lần bật tắt, trend 30′.
- Version control mọi tham số recipe/máy; historian mọi tag; batch report gồm lab (ẩm, màu, mật độ, hao hụt) gắn đúng mẻ, so tối đa 10 mẻ, vẽ dải min–max.
- Điều khiển từ xa/tablet được nhưng **trạm điều khiển thật phải có dừng khẩn**; tablet để xem/nhập liệu. Nút dừng khẩn cạnh màn P-series III dễ bị chạm khi đi ngang → tắt máy hỏng mẻ.
- Cảnh báo âm thanh khi gần nhiệt drop/FCs/nhiệt tuỳ đặt để gọi thợ về máy (P25 III).
- P-series: dữ liệu lưu cục bộ, web UI chỉ hiển thị, export/import recipe, kết nối Cropster/Artisan qua IP. Máy đời cũ nối Artisan/Cropster bằng **thermocouple đầu ra kép** (một nhánh cho đồng hồ máy, một nhánh cho bộ chuyển đổi). Màn P-series III chọn bật/tắt từng thông số: thời gian, development time, product temp + RoR, khí thải + RoR, áp âm, supply air, environmental + RoR, khí nguội.
- Nhà máy (PILOT Plant, PRNsn0Jv-hY, i81dT3kbN3U, tradeshows-plant): hạt xanh vào **silo kiểm tra** chờ lab duyệt rồi mới làm sạch; khoá chất lượng silo; quản lý user theo khu (hạt xanh/rang/xay); luồng nhận hàng quét mã lệnh xác nhận đúng silo/loại/hợp đồng. Thiết bị làm sạch công suất 6–12 t/h cho nhà máy 3 t/h vì rang theo **mẻ** → mô phỏng thời gian trễ và đổi sản phẩm để tìm nút cổ chai.
- Retrofit hệ điều khiển (NhW8F1kej40): tủ điện mới, cảm biến mới, biến tần mọi động cơ (động cơ cũ không bảo vệ nhiệt có thể phải thay); ~6 tuần tại chỗ, khoảng một nửa giá và thời gian máy mới; hệ điều khiển sống 10–15 năm.

## 8. Dữ liệu, năng lượng mẻ và bảo trì dựa dữ liệu (MmVuMpGIv74, HrUUR5Z_xF0, biz-skim-2)

- **Norm Roast** (Marko Luther/Artisan): chuẩn đo tiêu thụ như WLTP — FCs ≈ 10:00, tổng 12:30, drop = FCs + 10 °C (tương đối), tính cả preheat, tối thiểu 4 mẻ (lý tưởng 10). Công suất burner/tải danh định chênh tới 4 lần giữa các hãng, không nói gì về hiệu suất. P5 thực tế dùng ~50% công suất danh định. Artisan có Energy calculator (giả định % gas tuyến tính — nhiều burner không tuyến tính). BBP thêm 5–10′/mẻ → thêm CO2.
- 3 kiểu bảo trì: reactive (tệ nhất), preventive (theo mức sử dụng thực: VD phụ tùng đến hạn sau 12 tuần thay vì 16), predictive (mẫu dữ liệu dài hạn). Gộp mọi việc cần dừng máy vào một lần dừng.
- Anne Cooper: rang → ghi dữ liệu gắn **sự kiện vật lý** (màu, mùi, nổ) → nếm → gom các mẻ thích → đặt **dải chấp nhận** cho từng độ rang/sản phẩm; đừng đuổi hoàn hảo tuyệt đối. Phần mềm treo thì phải cứu mẻ bằng đồng hồ + nhìn hạt. Ric Rhinehart: log 30 s/lần vô nghĩa nếu không có thời gian phân tích. Ngành thiếu chuẩn hoá dữ liệu (định nghĩa, đơn vị, dải trường màu/nhiệt).

## Áp dụng cho OTL

- Chế độ TỰ ĐỘNG theo mẻ nền nên bám BT có dải theo pha + control point thời gian, không bám RoR thuần; RoR dùng để cảnh báo/dự báo.
- Trễ kích hoạt sau charge (kiểu 60 s của REFLEX) và dải rộng đầu mẻ hợp với TP không tin cậy.
- Bảng cảnh báo trên app nên có "nguyên nhân – hậu quả – cách xử lý" và cho ghi chú; không che màn chính.
- Chuyển mẻ nền giữa hai máy OTL: giữ thời gian pha + màu; chấp nhận 1–2 mẻ hiệu chỉnh.
