# PROBAT — vật lý máy rang, cấu tạo và nguồn nhiệt

Tóm lược có diễn giải từ video/web PROBAT (không phải trích nguyên văn). Mã trong ngoặc là video YouTube, tra lại ở `artifacts/probat-youtube-corpus-20260914/transcripts/<id>.txt`. Con số là **của máy PROBAT**; dùng để hiểu cơ chế, không bê làm thông số OTL.

## 1. Truyền nhiệt (A6qXyYOPf_A, 503cxjURIZA, e3A6OdVI0C8)

- Dẫn nhiệt qua vỏ: `Q̇ = λ·A·ΔT/d`. Vỏ nhiều lớp (kim loại – cách nhiệt – kim loại) cần thời gian dài mới đạt phân bố nhiệt ổn định; chưa ổn định thì mẻ khó đoán.
- Đối lưu: `Q̇ = α·A·ΔT`. Có hai núm: tăng **ΔT** (lửa) hoặc tăng **α** (α tăng theo vận tốc khí qua hạt). Bức xạ ∝ T⁴ nhưng trên máy trống chỉ khoảng 10% tổng. Trống PROBAT được nói là >90% đối lưu.
- Cùng năng lượng vào hạt đạt được bằng nhiều cặp (α, ΔT), quan hệ không tuyến tính. Nhiều gió thường hiệu quả hơn nhiều lửa, nhưng gió max + lửa max là phí nhiệt ra ống khói.
- Trong hạt có gradient ngoài → lõi. Rang gắt thì ngoài quá, lõi non. Hạt đặc cần thêm thời gian. Không thể rang chín đều trong 3 phút trên máy trống.
- Hạt vừa nhận nhiệt vừa làm nguội dòng khí (CFD thấy xoáy lạnh sau hạt).
- Máy khối nhiệt lớn thì phần tiếp xúc/bức xạ lớn. Kỹ thuật "soaking" (dựa nhiệt kim loại tích sẵn) kém hiệu quả trên máy khối nhiệt thấp chủ yếu đối lưu → đổi máy phải đổi tư duy điều khiển.
- Tốc độ trống chậm → tỷ lệ dẫn nhiệt tăng; nhanh → đối lưu tăng. Quá nhanh thì hạt ly tâm dính vỏ, gần như không đối lưu. Quá chậm/quá tải thì đống hạt lăn, không có hạt bay qua dòng khí. Khí đi đường dễ nhất (phía trên đống hạt), nên cần hạt "chắn" đường khí.

## 2. Dòng khí, áp suất, quạt (A6qXyYOPf_A, 7qI-Mpbts2Q)

- Tổn thất áp mỗi chi tiết: `Δp = ζ·ρ·w²/2` (lưới sau trống, ống, cyclone, ống khói…). Đường đặc tính hệ thống Δp–V̇ dạng bình phương; giao với đường quạt ly tâm là **điểm làm việc**.
- Tấm chặn gió (slide gate) đổi ζ, dịch điểm làm việc; dùng để **hiệu chỉnh máy theo đường ống lúc lắp đặt**, chỉnh xong thì không đụng nữa (xê dịch là mọi profile cũ đổi). Điều gió hằng ngày nên bằng biến tần quạt.
- P-series mặc định quạt ~65%. Gió quá mạnh thì hạt nhẹ cuối mẻ bị hút sang cyclone → giảm quạt, không đụng slide gate.
- Đầu đốt: ngọn lửa ~1800 °C trộn khí lạnh do quạt hút vào thành nhiệt khí cấp. Đổi quạt với cùng lửa là đổi lượng khí lạnh, tức đổi nhiệt khí cấp (trừ khi có vòng điều khiển giữ supply-air temp).
- Độ cao/nhiệt môi trường: quạt giữ cùng thể tích nhưng khí loãng hơn → lưu lượng khối và Δp khác → không so profile giữa hai nơi được dù máy giống hệt. Ví dụ Lhasa 3661 m (P05e): 100% công suất 20 phút mà khí cấp chỉ ~260 °C; tăng tần số quạt khí cấp 40→50 Hz thì nhiệt khí và RoR lên đủ (~24 °C/phút), 55 Hz đạt đỉnh 26–28 (web: customer-project-ks-espresso). Độ ẩm không khí ảnh hưởng ít vì khí cháy gas đã nhiều hơi nước.
- Hai máy cùng model vẫn khác vì ống khói, tuổi máy, độ cao, phòng.
- Áp âm trong trống là biến quan sát chính: P-series xuất xưởng −2 mbar đo ở nhiệt phòng; UG khuyến nghị ~110–120 Pa (có chế độ giữ Pa, máy tự đổi % quạt). Thời tiết đổi (mưa ↔ nắng) đổi điều kiện hút → theo dõi áp âm.
- Tấm gió máy rang mẫu điện (0,48–0,555): mở quá thì hút mất hạt, đóng quá thì vỏ lụa nằm lại trong trống. G60: đóng flap trong lúc nạp (không thì hút mất hạt), tới FCs nhiều người tăng hút để kéo vỏ lụa/khói.
- Nắp nhựa gần buồng đốt bị chảy có thể do thiếu gió → quá nhiệt cục bộ.
- Sample roaster điện nhiều lồng dùng chung một bộ điều khiển + SSR được vì điện đồng đều; bản gas mỗi lồng phải riêng.
- Kiểm tra gió bằng bật lửa ở cửa lấy mẫu chỉ khi không có đồng hồ áp, làm lúc máy nguội, không hạt, không đầu đốt.

## 3. Cấu tạo máy trống PROBAT (FPOAPrp65bo, zdEXgD9jwCs, gVbKt1jQyvY, Q8zWVguQT0E)

- **Trống hai vách**: vách ngoài nhận nhiệt, khe khí ~1 cm, vách trong thép mỏng <5 mm nóng êm hơn → giảm cháy xém/tipping. Vật liệu trống là thép đặc biệt, không phải gang; gang chỉ ở tấm trước, tay quay, gối trục. Tấm trước gang giữ nhiệt, là phần nóng nhất (>100 °C); vỏ trống ngoài ~60–70 °C.
- **Cánh đảo chéo**: hạt vừa xoay quanh trục vừa đi tới–lui → trộn đều, ít vỡ.
- **Đầu đốt P-series (premix)**: quạt trộn gas + gió trước, qua lưới kim loại thành nhiều ngọn nhỏ; lửa không chạm trống, nung KHÍ → đối lưu; công suất tuyến tính 1–100% bước 1%. P5 14 kW, P12 28 kW (P25 ra mắt 48 kW, sau nâng 60 kW vì xu hướng rang ngắn).
- **Đầu đốt UG (flat-bed dưới trống)**: *atmospheric* (khí mồi hút bằng áp âm máy, chịu áp gas dao động, thợ địa phương dễ chỉnh) hoặc *blower* (quạt trộn tỷ lệ cố định, cần áp gas ổn định).
- **UG "Aromarad"/flavor wheel** 3 vị trí: *Espresso* (khí xuyên trống, đối lưu chính), *Extern* (khí đi vòng ngoài nung vỏ trống → dẫn nhiệt, dùng đầu mẻ giữ ẩm), *Aroma* (trộn hai kiểu, chỉ dùng SAU FCs vì trước đó vỏ lụa không được hút ra). Luôn còn lỗ tối thiểu, không bịt hẳn (yêu cầu an toàn). P-series không có; muốn đổi tỷ lệ đối lưu/dẫn nhiệt thì dùng VFD trống + quạt.
- Đời máy: Probatone 1 và L-series dùng burner atmospheric, không phần mềm, L-series không có cyclone riêng; Probatone 2 → P-series III giữ cùng burner, trống, cánh, đường khí, khác màn hình/phần mềm, cách nhiệt, đường khí ít thất thoát.
- Cyclone tách rời máy: cháy vỏ lụa thì hỏng cyclone chứ máy rang vẫn an toàn; ống khói ít bám.
- Công suất danh định PROBAT là mức **tối ưu** (trống đầy vẫn còn chỗ cho hạt lưu thông). Mẻ nhỏ/quá tải: xem `probat-van-hanh-hat-xanh.md`.
- Máy lớn: Px120 (60–120 kg, 6–20′), Neptune 1000–4000 (110–880 kg), Jupiter tiếp tuyến (buồng tĩnh + cánh quay, 2–18′, gió rộng nhất, rang được hạt kém), Saturn ly tâm (bát quay, 4,5–15′, rất đều nhưng cần hạt tốt), G45–G120, P60, Cx70 (35–77 kg), Burns (trống đục lỗ). Tất cả tách trộn cơ khí khỏi cấp nhiệt để chỉnh nhiệt độc lập. Neptune cần ít gió → rang dài; Jupiter nhiều gió → rang ngắn. Máy công nghiệp: burner modulating điều theo nhiệt khí cấp 400–500 °C (không phải 800 °C); máy khí nóng/tiếp tuyến rang 2–3′ bằng nhiều gió và khí cấp thấp hơn (250–300 °C).
- Hồi lưu một phần khí thải về lò: tiết kiệm tới ~30% (Px120/Neptune/Jupiter/Saturn), Cx70 tới ~20%.

## 4. Đầu dò nhiệt (BV1MbsdeZEyg Bilibili, FPOAPrp65bo, vUR5xwN6Zj8, 7qI-Mpbts2Q)

- P-series chuẩn 2 đầu dò: **product** (ngay sau cần lấy mẫu, cắm trong đống hạt) và **exhaust roasting** (phía sau). Tuỳ chọn: **environmental** (khí trong trống ở chỗ không có hạt), **supply air** (khí từ nguồn nhiệt vào), **cooling exhaust** (khí đã hút qua khay nguội). Ký hiệu thường gặp: BT hạt, ET môi trường, XT khí thải.
- Đầu dò hạt đo **nhiệt hỗn hợp** hạt + khí + bức xạ thành buồng; lệch vài mm là ra số khác. P-series III dời đầu dò thấp vào khối hạt → FCs hiện thấp hơn ~5–10 °C so đời cũ (VD drop 210 cũ ≈ 200 mới), dù % lửa gần như giữ nguyên.
- RoR của nhiệt environmental giúp đoán trước FCs.
- Scott Rao (vUR5xwN6Zj8): đầu dò dày → trễ nhiệt; đặt quá cao/gần trục → mẻ nhỏ không ngập hạt → BT gợn, RoR "say rượu". Nên đặt ở tâm đống hạt khi trống quay đúng rpm (thử bằng cửa trong suốt), ngập được cả mẻ ~10% công suất, tránh cánh đảo. Đầu dò 3 mm so 1,5 mm cho TP khác hẳn; 6 mm đặt cạnh 3 mm thì đường 6 mm mượt "không có gì xảy ra", còn 3 mm lộ dip, "shelf" và crash cuối.
- TP là đặc tính phép đo (hạt thật vào ~20 °C tăng liên tục). Chỉ tin tương đối sau ~2,5–3′. Đỉnh RoR không có nghĩa tuyệt đối; "TP không được thấp hơn X °C" chỉ đúng cho đúng máy/hạt/mùa.
- Nửa mẻ: máy thừa năng lượng so tải → khí nóng hơn → đầu dò đọc cao hơn. P-series mới nửa mẻ vẫn phủ đầu dò, máy cũ có thể không.
- Mở cửa trống giữa mẻ để làm nguội máy nhỏ → khí lạnh hút đúng chỗ đầu dò → số đo sai, tự lừa mình.
- Bảo trì: lau đầu dò cẩn thận, lắp đúng chỗ ("lệch đầu dò là lệch cả mẻ"); hỗ trợ từ xa của hãng có bước hướng dẫn hiệu chuẩn lại thermocouple.

## 5. Nguồn nhiệt (5JA8Wdot9Lg, WyOQ3IxMDx8, c85OMeT3BAc, lJbzjR2Ci98, QiEYXnpqves, ibmuIvdV5GI, j7sUB4XNhOw)

- Nguyên tắc: nguồn nhiệt chỉ nung khí, khí là môi chất mang năng lượng; giữ cùng cách ghép nguồn nhiệt vào buồng rang thì profile như nhau. Thí nghiệm: profile dựng trên P5 gas, copy sang P5 hydro và P5 điện chạy AUTO → 3 đường chồng khít, cupping mù không phân biệt. Hạng 2–3 giải vô địch rang Đức 2023 rang trên P05e.
- **Điện đời cũ** (điện trở cuộn tĩnh): phản ứng chậm như sữa sôi tràn, phải thao tác dự đoán trước → PROBAT từng ngừng bán ~10 năm. **Điện đời mới**: quạt thổi qua điện trở ("máy sấy tóc") → lên/xuống nhanh như gas.
- Máy điện **không cho chỉnh gió**: bộ thổi cần lưu lượng ổn định, thiếu hút thì tích nhiệt dưới trống. P5e chạy áp 2,6 mbar (gas 2,1). P5e 17 kW (dư để linh hoạt ngang gas 14 kW), 3 pha ≥380 V, cầu chì 32 A. P01 điện trở 11 kW, cầu chì 16 A. Tiêu thụ ~0,5 kWh/kg cả gas lẫn điện; điện thấp hơn ~5–10%.
- Giải vô địch rang châu Á (Vũ Hán, P01): gió cố định nên thí sinh dùng **tốc độ trống** làm biến điều nhịp (VD 80% trước TP, 75% tới FCs, 70% vào FCs) (Bilibili BV1yB8RehEGy).
- **Hydro**: nhiệt trị ~3 kWh/m³ (khí thiên nhiên ~10) → cần ~3 lần thể tích; lửa gần như không thấy → giám sát bằng **cảm biến UV**; không mùi → kiểm rò gas train bằng spray mỗi tháng; **xả nitơ** đường gas trước khi đánh lửa buổi sáng và sau khi tắt buổi tối (không phải mỗi mẻ); chùm bình đặt ngoài trời/phòng riêng có rào chắn va chạm; gas train mới rất kín; burner dual-fuel chạy NG/H2/trộn. NOx hơi cao hơn NG.
- **LPG**: nhiệt trị ~gấp đôi NG, lỏng ~10 bar; cần bồn, có thể cần bộ hoá hơi, van giảm áp; máy >10 năm có thể phải thay burner + gas train. PROBAT coi là giải pháp tạm thời. Ví dụ Probat USA: cháy toà nhà bên cạnh cắt nguồn khí thiên nhiên, hãng chuyển gấp máy khách sang propane để rang tiếp. Đổi NG ↔ propane làm được với vài bước chỉnh đầu đốt, kết quả rang như nhau.
- **Biogas**: nhiệt trị thấp/không ổn định, khó đảm bảo nguồn. Có ví dụ biogas từ bã cà đủ chạy một P25.
- Điện hoá máy công nghiệp: hàng trăm kW bật/tắt theo mẻ → vấn đề lưới điện (Jupiter 5000 cần ~3,2 MW). Điện chỉ giảm CO2 thực khi là điện xanh.

## Áp dụng cho OTL

- Mô hình hoá nên theo chuỗi `lệnh gas/quạt/trống → nhiệt khí + áp âm/lưu lượng thật → BT/ET/RoR`, không suy airflow từ % quạt khi chưa có áp âm hoặc calibration.
- Khi so hai máy OTL, ghi vị trí/đường kính đầu dò, tốc độ trống, áp âm, ống khói và độ cao; không so nhiệt tuyệt đối.
- Tấm gió/damper chỉnh lúc lắp đặt thì ghi lại vị trí và coi là tham số cấu hình máy, đổi là mở "epoch" dữ liệu mới.
