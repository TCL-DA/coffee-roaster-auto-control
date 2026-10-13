# PROBAT — xử lý khí thải, bụi, ồn và năng lượng

Tóm lược có diễn giải. Liên quan trực tiếp buồng đốt khói/afterburner OTL, nhưng mọi nhiệt độ, lưu lượng dưới đây là của hệ PROBAT; thiết kế OTL phải theo manual và đo kiểm riêng.

## 1. Nguồn phát thải và khung quy định (PYv2KCPh02A, aF8nX9mRqn8, a6RpYK9yNtQ)

- Khói và mùi sinh từ **quá trình rang cà**, không từ nhiên liệu → máy điện vẫn cần xử lý nếu địa phương yêu cầu. Chất mùi chủ yếu hợp chất nitơ và lưu huỳnh. Lượng tăng theo độ đậm, thời gian, loại cà, sản lượng.
- Bốn nhóm phát thải: khí thải rang, khí thải làm nguội (mùi), bụi, tiếng ồn — cả ra môi trường lẫn trong xưởng.
- Đức: TA Luft (khí, bụi), TA Lärm (ồn), quy định an toàn lao động. Xưởng ≥0,5 tấn/ngày cần giấy phép; thành phần đo: bụi, NOx, formaldehyde, CO, VOC/tổng carbon. Giới hạn tổng C với hệ nhiệt/xúc tác: 50 → **20 mg/m³** từ 12/2021 → nhiều afterburner cũ không đạt.
- Demo camera trên mái (P-series): không xử lý thì khói bắt đầu ~10′, nhiều nhất quanh FCs ~12′.
- Kiểm tra yêu cầu địa phương (ống khói, mùi) **trước** khi lắp.

## 2. Yêu cầu với hệ xử lý (aF8nX9mRqn8)

- Giảm hay loại bỏ hoàn toàn khói/mùi; dễ dùng/bảo trì; an toàn; **ít ảnh hưởng quá trình rang** — lọc gây tổn thất áp sẽ đổi điều kiện áp, mẻ không lặp lại; chi phí; chỗ đặt và ống khói.
- Luôn dùng **đầu đốt riêng** cho xử lý khí, tách đầu đốt rang, để chỉnh xử lý khí không làm đổi quá trình rang.
- Máy dòng rang + nguội chung → khí thải nguội hơn; máy tách riêng → khí rang nóng hơn → ảnh hưởng chọn giải pháp. Cyclone riêng (ngoài) cho khí vào hệ xử lý ít hạt rắn; cyclone trong gây vấn đề cho xúc tác.

## 3. Các giải pháp khí thải rang

| Giải pháp | Nguyên lý / nhiệt độ (PROBAT) | Hiệu quả và lưu ý |
|---|---|---|
| Lọc mùi thụ động (shop) | Lọc bụi/dầu + hạt zeolite/than hoạt tính phủ chịu nhiệt sau cyclone | Không cần điện; chỉ **giảm** (~70–75% mùi), còn khói nhẹ; than thường chỉ chịu 50–60 °C; thay hạt P12 ~4 t cà, P5 ~2 t, P25 ~8–10 t |
| Afterburner nhiệt (TNV/TVR) | Đầu đốt thứ hai nâng khí ~180 → ~450 °C | ~400 °C chỉ giảm khói; muốn hết khói + mùi cần ≥600 °C (shop) → tốn gas; không đạt TA Luft mới |
| Nhiệt + xúc tác (NVK) | ~450 °C qua cassette phủ kim loại quý, phản ứng đẩy lên ~630 °C | Hết mùi đặc trưng, không thấy khói; **NOx tăng** (có bản low-NOx); 1 xúc tác/1 máy; bảo hành cassette 3 năm/12.000 h, có nơi dùng 10 năm; khu vực ~450 °C → ống lên mái phải chịu nhiệt |
| Xúc tác nhiệt thấp | Nâng khí ~320 °C (300–400) thay 450–600 | Tiết kiệm tới ~30% so xúc tác thường |
| Xúc tác điện ReCatino (shop, 2024) | Quạt thổi nhiệt điện, khí sau cyclone 150–180 °C → làm việc ~230–250 °C | Không mùi, không khói, tiết kiệm >50% so afterburner 600–700 °C; tiền lọc vệ sinh 1–2 ngày/lần (45–60 s); hộp xúc tác ~30.000 h; 450: max 11 kW (TB ~8) cho P5/P12/UG15, 600: max 17 kW cho UG22/P25; cần **hai ống thoát riêng**, ống khói sạch, chịu 230–250 °C, to hơn 1–2 cỡ (P12: 150 → 200 mm), cyclone ngoài |
| PROFORTE (FRTO) | Giường gốm lõi ~900–1100 °C, khí bẩn tự duy trì oxy hoá, đảo chiều van định kỳ, bồn đệm giữ khí bẩn lúc đảo rồi hồi xử lý lại | Đạt mọi giá trị TA Luft; khí vào ~200–230 °C, ra chỉ nóng hơn ~50 °C; hiệu suất nhiệt tới ~98%; không NOx nhiệt, khử CO; nhược: gốm phải giữ nóng qua đêm/cuối tuần; 1 hệ cho 1–3 máy; có bản điện hoàn toàn |

- Rombouts (Bỉ): Proforte đầu tiên 2003 dự kiến 7 năm, chạy gần 20 năm; chỉ vệ sinh ống 1 lần/năm.
- So sánh chi phí (l6KSzwlcRwQ): 2 × Neptune 1500, 5.280 h/năm → Proforte đầu tư cao hơn nhiều nhưng vận hành rẻ, hoà vốn ~2,5 năm. Nguyên tắc: so **TCO** chứ không chỉ giá mua.

## 4. Khí thải làm nguội — PROAIR (ljDcBLbrujw, DNuvjAE0zqE)

- Vấn đề: dù khí rang có xúc tác, khí nguội vẫn mang mùi ra khu dân cư.
- Plasma lạnh: khí ngoài trời → lọc 3 cấp (thô, HEPA, than) → sưởi điện giữ khô → module plasma tách O2/H2O thành oxy hoạt tính → phun phủ toàn tiết diện ống nguội → oxy hoá phân tử mùi; cần đoạn ống đủ dài cho ~1 s phản ứng.
- Bộ plasma chỉ bật trong lúc làm nguội (3–6′/mẻ); không dùng cho khí rang (quá nóng). Giảm đơn vị mùi 56–91% (mục tiêu ≥50%, web nói tới 95%); năng lượng ~0,2–0,5 kWh/100 kg xanh so xúc tác ~3,3 kWh/100 kg. Module 8.000 h/4 năm. Van một chiều: Proair hỏng không dừng rang.

## 5. Bụi và ồn (PYv2KCPh02A, web: dust-extraction)

- Bụi chủ yếu từ **hạt xanh** (chất lượng hạt quyết định) ở chỗ đổ bao, vận chuyển. Hút gió lưu lượng cao → cyclone → lọc túi <20 mg/m³ → lọc tinh <1 mg/m³ thì thải lại vào nhà giữ nhiệt. Ba cấp: >10 µm túi, 1–10 µm tinh, HEPA <1 µm; có giảm áp nổ bụi (ATEX). Chỉnh flap theo vận tốc khí trong ống: hút đủ bụi nhưng không hút mất hạt.
- Sơ đồ ATEX tô vùng: trạm đổ hạt xanh zone 22, vận chuyển zone 21 → làm việc với chính quyền sớm.
- Ồn ở mọi chỗ có dòng khí (quạt, blower, khí nén, ống): tiêu âm, bọc cách âm ống, giảm thanh miệng thải, vỏ bọc quạt. Trên shop roaster, ồn chủ yếu từ cyclone và hạt.

## 6. Năng lượng (Z9-x0jmOW9o, MmVuMpGIv74, eJFRbcAE6cA, DNuvjAE0zqE, j7sUB4XNhOw; web: green-coffee-preheating-rkv)

- Năng lượng rang ~300–500 kJ/kg hạt (Arabica, mật độ thấp ít hơn; rang nhanh/đậm tốn hơn). Shop roaster ~0,5 kWh/kg cả gas lẫn điện. Năng lượng làm nâu hạt gần như như nhau giữa các nguyên lý; rang ngắn tốn hơn chút.
- Với máy lớn, phần lớn năng lượng không dùng để rang mà để **làm sạch khí thải** → xử lý khí là đòn bẩy bền vững chính.
- Đòn bẩy: vận hành liên tục, ít standby/dừng; **hồi lưu** khí thải về lò (−30–40%); **preheater hạt xanh** (RKV) tới 90–100 °C bằng khí sạch sau xúc tác (−20% năng lượng, +20% công suất; với Proforte khí chỉ ~280 °C thì thêm điện trở để luôn trên điểm sương); xúc tác nhiệt thấp; chuỗi trao đổi nhiệt + ngưng tụ sau Proforte → nước nóng sấy khí tươi, sưởi xưởng. Kết hợp đủ chuỗi → khí ra ~50 °C, tiết kiệm >80% nhiệt so máy không hồi lưu + xúc tác thường.
- Gom rang ít ngày, rút ngắn nghỉ giữa mẻ; máy lớn ít mẻ hiệu quả hơn máy nhỏ nhiều mẻ.
- CO2: propane ~200+ g/kWh; điện lưới Mỹ trung bình ~390 g/kWh nhưng có thể về 0 với điện xanh. Một tách cà ~60 g CO2, rang + xay chỉ ~5% nhưng là khâu roastery kiểm soát được.
- Tối ưu hiệu suất trước (preheater, cách nhiệt, burner mức thấp, tái dùng nhiệt), đổi nguồn nhiệt sau.

## Áp dụng cho OTL

- Buồng đốt khói OTL phải có đầu đốt/điều khiển riêng và không tạo thêm tổn thất áp làm lệch mẻ; theo dõi áp âm trống trước/sau khi lắp.
- Tư vấn khách gần khu dân cư: khí nguội cũng mang mùi; tách ống rang và ống nguội.
- Không dùng nhiệt độ/tuổi thọ xúc tác PROBAT làm thông số bảo hành OTL.
