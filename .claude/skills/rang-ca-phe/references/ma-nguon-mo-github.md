# Kiến thức rút từ mã nguồn mở GitHub về rang cà phê (đợt 16, 18/10/2026)

Nguồn: 41 repo có giấy phép mở, zip nằm ở `F:\Research\Coffee-Roasting\datasets\github\`, danh mục +
SHA256 trong `indexes/github_roaster_repositories.csv`, báo cáo `BAO_CAO_DOT_16.md`. Repo nặng ký nhất:
**tilauscope_fork** (lớp "dẫn mẻ" dựng trên Artisan, AGPL-3.0 — tài liệu `docs/*.md` rất kỹ), **LibreRoaster**
(firmware Rust, lớp an toàn), **RoastCurve** (app + cầu ESP32, Modbus TCP), **kaffelogic-klog** (công thức chỉ số),
**roastronaut** (micro + camera), **Artisan** gốc.

## 0. Đọc trước — giới hạn khi áp cho OTL

- Phần lớn số đo đến từ **máy gia đình 150–450 g** (Skywalker V2 điện bức xạ, popper, Gene Cafe). Máy OTL là trống
  6–30 kg, lửa gas hoặc điện VX4, quán tính nhiệt lớn hơn nhiều. **Học cách nghĩ và cấu trúc, không bê con số.**
- **Luật OTL thắng khi mâu thuẫn**: rang chỉ MPC, không PID khi lái mẻ; charge theo `dieu-khien-nhiet.md` 7e; ngưỡng
  Maillard / DE sớm theo 7g; chẩn đoán crash/flick theo `chan-doan-profile.md`; an toàn gas theo firmware + manual OTL.
- **Không lấy ngưỡng an toàn từ đây** để đặt cho máy OTL. Mục 5 chỉ là danh mục *loại* bảo vệ nên có.
- AGPL/GPL: chỉ học ý tưởng, **không chép mã** vào firmware / Roast Lab.
- Khi dẫn lại cho anh Thành, ghi nguồn: "theo ma-nguon-mo-github.md › mục X (tilauscope, máy Skywalker)".

## 1. Lập kế hoạch mẻ trước khi nạp (tilauscope `the-roast-plan.md`, `preparing-a-roast.md`)

### 1a. Đầu vào — mỗi thông số lái một thứ riêng
- **Khối lượng mẻ**, **mục đích pha** (Filter < Omni < Espresso về thời gian phát triển), **mức rang đích (Agtron)**,
  **phòng** (nhiệt độ phòng dời nhiệt nạp; độ cao dời FC).
- **Ẩm (moisture %) ≠ hoạt độ nước (aw)** — dùng CẢ HAI, không suy cái này từ cái kia:
  - Ẩm = *bao nhiêu* nước ⇒ quyết định lửa đầu, nhiệt nạp, lực đẩy qua FC, đà trôi cuối mẻ. Ẩm cao ⇒ **nhiều năng lượng
    lúc đầu, không phải sấy lâu hơn** (trên máy họ, thời gian sấy theo khối lượng + giống + sơ chế, gần như không theo ẩm).
  - aw = nước thoát *dễ hay khó* ⇒ quyết định **gió**.
- **Sơ chế đặt trần nhiệt nạp** (natural/honey đường trên vỏ dễ cháy ⇒ nạp nguội hơn washed). **Họ giống** (theo Rob Hoos:
  Typica/Ethiopia muốn nhanh, Bourbon muốn chậm, lai đọc theo bố/mẹ không phải Timor) chỉ xê dịch ~4 °C **bên trong**
  trần đó (≈15 s sấy). Trọng số: 1 giống = đủ, blend = ½, không rõ giống = 0 — và nói rõ "không biết, dùng nhịp chuẩn".
- **Tỷ trọng thắng độ cao.** Độ cao chỉ đoán "có lẽ cứng"; kiểm trên dữ liệu thật, độ cao đúng hướng chỉ ~⅕ số lần.
  Có tỷ trọng thì **bỏ hẳn độ cao**; chỉ có độ cao thì xê ~1 °C, tỷ trọng thật xê tới ~7 °C.
- **Vùng giữa = không thông tin.** ~4/5 lô nằm ở dải giữa (vd 710 vs 730 g/L) — chênh 20 điểm thường do cách đo của nhà cung
  cấp. Chỉ chỉnh khi lô **rõ mềm** (nạp nguội, ít lửa đầu, dễ cháy mặt) hoặc **rõ cứng** (nạp nóng, được vượt khoảng thường).
- Đo tỷ trọng tự làm đáng giá hơn số trên bao: ống 50 ml đổ 40 ml nước, thả hạt tới vạch 50 ml, cân hạt (đo khô tính cả không khí).
- Độ cao nơi rang: FC sớm ~**1 °C mỗi 300 m** (≈8 °C ở 2 500 m) — nước sôi thấp hơn. (Việt Nam phần lớn gần mực biển,
  Đà Lạt ~1 500 m ⇒ ~5 °C.)
- Độ ẩm phòng: ghi lại nhưng **không** chỉnh kế hoạch; nó tác động lên hạt xanh *giữa các mẻ* (kho), xem mục 4.

### 1b. Mốc, giai đoạn, TP
- Kế hoạch gồm: nhiệt nạp, DE, FC (nhiệt + giờ), DROP; thời gian sấy / Maillard / phát triển / tổng; đường BT + RoR dự kiến;
  hao hụt đích và khối lượng ra.
- **Maillard luôn ngắn hơn sấy một khoảng thật** (4:00/3:00, 5:00/4:00). Hai nửa bằng nhau ⇒ RoR không kịp hạ. Mẻ nhỏ TP cao
  làm phép tính đảo ngược ⇒ **Maillard nhường** (giữ RoR cao hơn), sấy giữ thời lượng theo cỡ mẻ.
- **TP tra bảng theo mức tải, không theo công thức**: ¼, ⅝, ⅞, đầy trống mỗi mức một số đo thật; giữa hai mức nội suy;
  ngoài khoảng thì lặp số gần nhất (không kéo dài đường dốc). Ghi theo **tỉ lệ** (phần trống, phần nhiệt nạp) để dùng được
  cho máy khác. Mẻ nhỏ TP cao hơn mẻ đầy ~25 °C cùng nhiệt nạp; dưới ~¼ trống TP gần như không sâu thêm.
- **RoR sấy phụ thuộc cỡ mẻ**: leo dài ⇒ RoR trung bình cao hơn. Skywalker: 400 g ≈ 13,5 °C/phút (TP→DE), 250 g ≈ 10.
  ⇒ Không hứa với mẻ nhỏ một thời gian sấy nó không giữ được. Mẻ nhỏ chạm sàn tốc độ sấy ⇒ nâng DE vài độ.
- Áp OTL: dựng **bảng TP theo % tải cho từng máy** (6 / 12 / 15 / 30 kg) từ log thật — hợp với "Bảng mức giữ" của Hồng.

### 1c. RoR đích — 4 con số giảm dần
- Đích RoR Maillard (trung bình), **RoR tới FC** (giá trị *đến*, quyết định FC), RoR phát triển, RoR lúc DROP. Bốn số phải
  giảm dần; kế hoạch nào RoR dev > RoR tại FC thì **báo ra** (đường tăng tốc sau nổ), không in lặng lẽ.
- Máy bức xạ (Skywalker): rời TP ~16 °C/phút, vào Maillard ~12, qua 8 khoảng 1 phút trước FC, tới FC 5–6.
  **Vào FC ở 8 thay vì 5 ⇒ ra medium dù dev chỉ 1 phút.**

### 1d. DTR là KẾT QUẢ, không phải nút vặn
- Phát triển được lập = thời lượng ở đúng nhiệt + RoR; DTR là số rơi ra, biết trước khi nạp.
- DTR lệch khoảng thường của mức rang ⇒ **nhìn đầu mẻ (sấy/Maillard), không sửa đoạn dev**.
- Máy điện bức xạ: dev ngắn hơn bảng chung — light 0:45–1:00, medium-light ~1:30; giữ light 2:00 sau FC thường ra medium.
  Tổng thời gian giữ nguyên, phần dư dồn về Maillard.
- **Development rise** (°C BT tăng từ FC tới DROP) đi cặp với DTR: cùng DTR mà một mẻ tăng gấp đôi độ ⇒ kết quả khác hẳn.

### 1e. Thang lửa và gió
- **Giảm lửa lập TRƯỚC FC**, bậc cuối "n giây trước FC". Cắt sau FC = tới muộn, làm bẹt đường.
- Trước DE thường **không giảm**; chỉ giảm khi lô này từng cho RoR bẹt sớm — và *học* từ chính các mẻ trước (bắt đầu lúc nào,
  bậc bao nhiêu, đứng ở đâu lúc DE). Lô chưa từng phải sửa ⇒ không lập bậc nào.
- **Sàn công suất của máy**: dưới mức đó phần tử vẫn nóng nhưng không còn nuôi phản ứng ⇒ RoR sụt (Skywalker V2: 45 %;
  45–50 % = vùng biên mỏng, ghi chú chứ không cấm). Sàn áp cho mọi pha và cho cả số học từ lịch sử. → OTL: đo sàn "nuôi
  phản ứng" cho từng máy / từng cỡ mẻ (gắn với chẩn đoán baked).
- Mỗi bậc là **một lần đổi rồi giữ để đọc tác dụng**, không trượt liên tục. Bảng ghi **trị số lúc vào pha** (charge, DE, FC),
  không ghi trung bình pha. Lửa lúc charge = lúc DE (giữ lửa sấy qua DE, hạ ngay sau).
- Gió leo lên mức Maillard **từng nấc khi gần DE**, không nhảy một phát ở mốc. Gió đi theo màu nâu; đoạn dev lửa nhẹ đi, gió đỡ.
- **Tốc độ trống là quyết định trước mẻ** (tính từ khối lượng + tỷ trọng, đặt lúc CHARGE rồi để yên). Máy mà đổi trống làm
  nhiễu đầu dò ⇒ không đề xuất đổi giữa mẻ.
- Mỗi lệnh kèm **lý do** ("giảm 10 % trước 45 s để kiểm soát lúc vào FC"). Kế hoạch có **điểm rủi ro CRASH/FLICK** biết trước
  theo lịch sử lô này.

### 1f. Học từ lịch sử — đúng cách
- Mỗi số ghi **nguồn**: `grid` (bảng chuẩn), `reference only (n=1)`, `grid/profile blend (n=2)`, `medoid (n=N)`,
  `operator reference (n=N)`, `skeleton (n=N)` (mẻ không ghi thao tác tay — chỉ lấy mốc, không lấy lửa/gió).
- Nhãn mức tin: **consistent history / partial history / grid only** — mô tả lượng dữ liệu, **không phải xác suất đúng**.
- Chỉ lấy mẻ **cùng lô (theo mã, không theo tên giống giống)** và **cỡ mẻ tương đương** (250 g không làm mẫu cho 450 g).
- **Không ghép trung vị từng thông số** (ra một mẻ ảo chưa ai rang). Chọn **một mẻ thật đại diện (medoid)**: n ≥ 3 lấy mẻ có
  khoảng cách tổng nhỏ nhất tới các mẻ khác (thời lượng pha, lửa, gió, FC, drop, RoR cuối). n = 1 ⇒ vẫn theo bảng chuẩn; n = 2 ⇒
  pha thận trọng mẻ gần nhất với bảng.
- **Mẻ chuẩn ★** (đã nếm "Yes") đứng trên hết, kể cả n = 1; nếm lại "Almost/No" ⇒ thôi dùng.
- **Mùa vụ mới** của cùng lô: mang sang *lịch* (nhiệt FC, thời lượng sấy/Maillard, drop cho màu đích) vì theo giống + sơ chế;
  **không** mang sang lửa (phụ thuộc ẩm + tỷ trọng lô mới). Đủ 2 mẻ mùa mới thì dùng riêng mùa mới, không trộn.
- **Lửa khởi đầu** học từ tập rộng hơn: mọi mẻ **cùng sơ chế + cùng cỡ mẻ** (máy không quan tâm hạt nào, chỉ cỡ mẻ + sơ chế).
  Lửa Maillard / dev vẫn học riêng theo lô (theo màu đích).
- Chặn biên: giá trị ngoài khoảng chuyên nghiệp ⇒ bỏ, quay về bảng. **Một mẻ hỏng không dời kế hoạch; thói quen nhất quán mới dời.**
  Nút **"Loại khỏi dữ liệu học"** cho mẻ hỏng vì lý do ngoài hạt (gián đoạn, nhầm thao tác, đầu dò lỗi).
- Đòi hỏi không thể đạt cho lô + cỡ mẻ này ⇒ in **OUT OF SCOPE**, không vẽ đường không theo được.
- **Đóng băng dự báo trước CHARGE** (DE, FC, drop, màu đích, lửa/gió tại mốc) rồi so với thực tế ⇒ đo sai số dự báo thật.
  Chỉ khi đủ dữ liệu mới gắn nhãn tin cậy low/medium/high.
- Áp Hồng: khi lập đề / kế hoạch mẻ, **in nguồn + n** cho từng số như trên; sổ mẻ cần cột "loại khỏi học" và "mẻ chuẩn".

## 2. Dẫn mẻ khi trống đang quay (tilauscope `the-guided-roast.md`)

- **Trợ lý chỉ khuyên, không chạm cần gạt.** Một trang theo pha: chờ / preheat / sấy / Maillard / phát triển / nguội.
  Hai chế độ xem: **Coach** (1 lời khuyên + nhận định pha) và **Expert** (mọi số).
- Lệnh viết thành **thao tác máy làm được**: "tăng 1 nấc lửa" (1 nấc = 5 %), không phải phân tích.
- Lời khuyên **theo quán tính nhiệt máy**: trống nặng ⇒ báo hạ lửa sớm để kiểm soát lúc vào FC; máy bức xạ còn sớm hơn.
- **Báo trước bậc giảm lửa**: "kế tiếp 48 % @170 °C" (mức + nhiệt BT kích).
- Gió theo pha: sấy "giữ thấp để giữ nhiệt" / "vừa để sấy đều"; Maillard "tăng để quản lý màu nâu & vỏ lụa"; cảnh báo "gió
  tác động mạnh — tránh đổi để RoR mượt".
- Lời khuyên theo hạt: chắc ⇒ cần nhiệt bền; mềm ⇒ truyền nhiệt nhanh; ẩm ⇒ RoR vừa, sấy dài; khô ⇒ coi chừng sấy chớp;
  natural/honey ⇒ sấy dài hơn.
- **Đứng ở đâu so với kế hoạch**: "plan +0:15" / ON PLAN ✓. **RoR xét theo dải tại điểm đang đứng** ("lý tưởng 12–15 °/phút")
  — không gọi "quá nhanh" khi đúng là độ dốc kế hoạch đòi ở đoạn đó. Kèm hệ quả: "RoR cao ⇒ thất thoát hương", "RoR thấp ⇒
  nguy cơ baked", "RoR đang tăng — chú ý độ dốc".
- **Mốc do máy dò, người xác nhận** (nút sáng + bíp 1 lần). Mỗi mốc xác nhận ⇒ **lập lại phần còn lại** theo thực tế. Hủy mốc
  sai ⇒ quay về pha cũ, bỏ phần lập lại. Charge nhầm ⇒ nút "Hủy charge" 15 s.
- **Đếm ngược DROP** có tính đoạn đường chững cuối mẻ; dưới 20 s nói thẳng "DROP trong < 20 s — chuẩn bị!".
- Trạng thái DTR sống: ON TARGET / near / OFF / DRIFTING. Có cảm biến màu: "trong khoảng đích ⇒ cân nhắc DROP" (thêm một
  đầu vào, không thay quyết định).
- **Bảng cảnh báo kèm cách sửa** (cảnh báo không làm gì được = nhiễu):

| Cảnh báo | Nghĩa / việc làm |
|---|---|
| RoR crash — DROP ngay hoặc tăng nhiệt lại | Hai lối ra, nói cả hai |
| Hồi phục — RoR dựng lại sau TP | **Không phải lỗi** |
| Sấy kéo dài ~5:30 so với 4:45 — nguy cơ baked, tăng lửa | |
| Maillard kéo dài — nguy cơ baked, tăng lửa hoặc đón FCs | |
| Nâu sớm | Ngược lại: lên màu quá sớm |
| Nguy cơ sấy chớp — kiểm công suất | Vỏ khô trước lõi |
| **Giữ lửa — lô ẩm (12,4 %) TP cao rồi kháng nhiệt** | Lô ướt nhận nhiệt nhanh nên TP cao hơn kế hoạch, rồi kháng khi nước bắt đầu thoát. **Cắt lửa vì TP cao là cách kinh điển để hụt nhiệt giữa mẻ ⇒ baked.** Chỉ hiện khi có ẩm đo + TP thật cao hơn kế hoạch |
| Khoảng ET/BT nguy hiểm | Chỉ trên máy có đầu dò khí |
| **Mất BT — tạm ngưng khuyên tới khi có số mới** | Không lặp lời khuyên dựa trên nhiệt cũ |

- Đang chạy trợ lý ⇒ **tắt alarm hành động của Artisan** để hai nguồn lệnh không cãi nhau.
- Làm nguội: "mở cửa, giữ trống quay, không cắt điện tới BT < 50"; trạng thái COOLING / NOT COOLING; không nguội ⇒
  "**HẠT KHÔNG NGUỘI — NGUY CƠ CHÁY**".
- **Mẻ kế trên máy nóng**: "Restart batch" — dưới ngưỡng nguội thì chạy ngay, trên ngưỡng thì **lên cò**, tự bắn khi qua ngưỡng;
  bấm lần 2 hủy. Nạp lại cùng lô, cùng khối lượng, ẩm / tỷ trọng / nhiệt hạt xanh.
- **Machine response** = RoR của ET: nhúc nhích vài giây sau khi đổi lửa — dấu hiệu sớm nhất "máy đã nghe", **không** nói mẻ
  tốt/xấu. **Quán tính nhiệt**: trống lớn còn nhả nhiệt sau khi giảm ⇒ giảm sớm hơn.
- Alarm viết thành câu: "khi CHARGE +2:00 **hoặc** ngay khi BT > 190 ⇒ …"; alarm có **guard** ("nếu #3 đã bắn", "BT > +10 kể
  từ lúc đó"); alarm thiếu cả trễ lẫn điều kiện bị đánh dấu là không bao giờ chạy.
- Áp Hồng: khi báo từng lượt cho anh Thành, dùng đúng khuôn này — **1 câu Coach + số so kế hoạch + mốc kế tiếp + bậc lửa sắp tới**.

## 3. Sau mẻ — chấm và khép vòng (tilauscope `after-the-roast.md`)

- **Một câu kết luận**: có theo kế hoạch không, **một** lệch quan trọng nhất, **một** việc đổi lần sau. Mọi thứ dưới là bằng chứng.
- Dải pha (thời lượng + %), bảng mốc (CHARGE, TP, DE, FC, DROP) kèm **lệch so kế hoạch**: DE/FC lệch theo **giờ**, DROP lệch theo
  **nhiệt** (vì đó là cách mỗi mốc được lái).
- **Bốn số**: DTR, development rise, RoR đỉnh, hao hụt — mỗi số kèm đích hoặc khoảng thường của mức rang.
  Mức rang **đọc từ mẻ** (dev bao lâu + rời ở nhiệt nào, đã trừ lệch đầu dò máy), **không** từ màu đo sau.
- **Hao hụt đích không phải một số cố định**: bắt đầu từ ẩm của lô (lô khô ít nước để mất) + phần cháy theo mức rang và dev.
  Thêm 40 s sau FC ⇒ hao hụt thêm ~1,5 điểm. Chỉ lên tiếng khi lệch rõ (mẻ nhỏ 1 điểm chỉ vài gam).
- **Màu: báo, không kê đơn.** Không khuyên "drop nóng/nguội hơn để sửa màu" vì chưa có quan hệ tin cậy drop → màu; bịa còn tệ
  hơn im lặng. Nhưng màu đo được **sửa nhiệt drop đích của kế hoạch kế tiếp cho lô đó** (học theo bảng của chính mình).
- "Average rise" (độ tăng / thời lượng pha, từ TP tới DROP) **khác** RoR vẽ trên đường.
- Kiểm chéo **drop + DTR** để bắt mẻ thiếu/dư phát triển khi từng số riêng trông ổn. Chỉ nêu **một** tai nạn rõ nhất quanh FC
  (stall / crash / flick) kèm giờ để tự xem.
- **Phân tích profile**: so RoR với đường xu hướng (bậc 2/3/log), mẻ trước cùng lô, hoặc mẻ chuẩn ★ (căn theo CHARGE). Kỳ: DE→DROP
  hoặc 2 phút trước FC→DROP. Ba số: **RMS lệch BT (°C)**, lệch RoR trung bình, **lệch tại FC (vàng khi ≥ 2 °C/phút)**.
  Crash/flick chỉ gọi tên khi RoR đo **tự** sụt/dựng ≥ 2 °C/phút về đúng phía xác nhận; RoR không giảm suốt kỳ ⇒ cờ.
  Mọi kết luận kết thúc bằng "**xác nhận trong ly**".
- Phiếu kết quả: khối lượng rang + **khối lượng hạt lỗi**, màu nguyên hạt + màu bột, ghi chú, dấu **Tipping** (cháy đầu hạt:
  nhiệt đầu mẻ quá mạnh) / **Scorching** (mảng cháy mặt phẳng: nạp quá nóng hoặc trống quay chậm).
- **Nếm sau khi nghỉ** → "Rang y vậy lần sau?" Yes / Almost / No + chọn vị lệch ⇒ **một** đổi duy nhất cho mẻ sau:

| Vị lệch | Lần sau |
|---|---|
| Cháy | Nạp nguội hơn 3 °C |
| Đắng, khói | Hạ 1 nấc lửa trước FC |
| Bẹt, giấy | Giữ lửa cao hơn 1 nấc sau FC |
| Bánh mì, đục | Khởi đầu lửa cao hơn 1 nấc |
| Cỏ, sống | Dev thêm 20 s sau FC |
| Chua, mỏng | Drop muộn hơn 2 °C |

  (1 nấc = 5 %.) Chọn nhiều vị ⇒ vị **đứng trên trong bảng** quyết định — **mỗi lần đổi một thứ**, xét ở mẻ sau. Chỉ lần nếm
  của mẻ **mới nhất** có hiệu lực. → Đây là bảng của máy gia đình; Hồng đối chiếu với `cupping-sca.md` (lỗi rang → note) trước khi dùng.
- **Baked** khó thấy nhất: trống còn bức xạ nên BT và RoR có thể **trông hoàn hảo** trong khi phản ứng bên dưới đã đình.
  **Đường mượt không chứng minh mẻ đang được nuôi.** (Khớp "Cách tính David" — k vọt khi lửa thấp.)
- Thẻ chia sẻ PNG dọc 2160×3240 (BT + RoR cùng trục giờ). Tóm tắt AI có nút "**cái gì được gửi**" — hiện đúng văn bản sẽ gửi.

## 4. Kho hạt xanh và bảo quản (tilauscope `beancave.md`, `sacks-and-storage.md`)

- Mỗi lô có **mã định danh**; mọi mẻ trỏ về đó ⇒ trừ kho khi rang, kế hoạch học theo lô, lịch sử theo lô.
  Lô đang rang hết kho vẫn hiện trong danh sách (đánh dấu "kho rỗng").
- Nhập bao mới 3 tình huống: **lô mới** / **bổ sung cùng vụ** (chỉ cộng cân) / **vụ mới cùng lô** (thừa kế danh tính, tên giữ, khác năm vụ).
- **Bảng aw hạt xanh**:

| aw | Trạng thái |
|---|---|
| < 0,45 | Quá khô — hương dễ mất, nhanh cũ |
| 0,45 – 0,60 | Tối ưu |
| 0,60 – 0,65 | Theo dõi, đo lại sớm |
| ≥ 0,65 | **Nguy cơ mốc** — ủ lại hoặc rang ưu tiên; đưa ẩm kho < 60 % RH |

- **Conditioning** (hút chân không / túi van / hũ kín / bao vải hở): kín thì giữ aw của hạt, hở thì trôi theo ẩm phòng.
  **EMC** = ẩm hạt sẽ tiến tới nếu để mãi trong điều kiện phòng hiện tại — hướng trôi của bao hở, không phải số đo hạt.
- RoastCurve + CoffeeBeanTracker: rang xong **tự trừ hạt xanh + nhập kho hạt rang**. Nhãn bao có QR, nhãn chuyển sang bao mới khi bao cũ hết.

## 5. Lớp an toàn — danh mục *loại* bảo vệ (LibreRoaster, RoastCurve, Skywalker, TilauPID)

Số dưới đây là của máy SSR điện nhỏ, **chỉ để biết loại bảo vệ**; ngưỡng OTL theo firmware + manual OTL.

| Loại bảo vệ | Cách họ làm |
|---|---|
| Quá nhiệt | Cắt ở 260 °C BT; nhiệt đọc ngoài −50…350 °C = số rác |
| RoR chạy loạn | Mềm 30 °C/phút phải kéo dài ~3,7 s (12 nhịp) mới chốt; cứng 60 °C/phút chốt sau 3 nhịp (~1 s) — tránh bắn vì 1 gai nhiễu |
| Nhiệt treo (stale) | Không có số mới > 1 s ⇒ coi như mất cảm biến; 5 lỗi đọc liên tiếp ⇒ dừng |
| **Đầu dò kẹt** | Lửa ≥ 50 % mà BT dao động < 1 °C trong 120 s ⇒ cặp nhiệt chập (đọc phẳng ~0 °C *hợp lệ*) hoặc đứt |
| **SSR dính / nguồn nhiệt sai** | So lệnh nhiệt với cảm biến dòng (có nhiệt thật?) trong 100 ms |
| Mất liên lạc PC | Skywalker: không nhận lệnh 10 s ⇒ tắt; LibreRoaster: 15 s rảnh |
| Dừng khẩn | Tắt nhiệt **thử lại 3 lần**, ép quạt 100 % **thử lại 3 lần** ("không quạt khi hạt nóng = không an toàn") |
| Watchdog | Hai lớp: phần mềm + phần cứng |
| Thời gian mẻ tối đa | 30 phút |
| Quạt tối thiểu | 20 % khi đang nhiệt |
| Nhả làm nguội | BT < 60 °C |
| Dò CHARGE | BT sụt > 6 °C trong 3 s (dấu vết vật lý 2–3 °C/s khi đổ hạt) |

- **RoastCurve "watchdog v2"** — mất liên lạc xử lý theo trạng thái: **chỉ về an toàn khi đang đốt** (SV ≥ nhiệt an toàn);
  đang chờ thì giữ nguyên, không tự đốt. Sau khi về an toàn, app hỏi "giữ tiếp" / "hạ ngay" — người quyết. Đang bám đường cong
  mà mất mạng ⇒ **máy tự chạy hết đường** rồi tự hạ (SV 25 °C, quạt 25 %, chỉnh được); **chặn cứng ≥ 250 °C liên tục 5 s**.
  App và Web UI là hai lối bám riêng, **chỉ dùng một lối mỗi lúc**.
- **TilauPID preheat**: số đọc mất / sai / đổi nhanh hơn vật lý cho phép ⇒ nhiệt về 0 ngay; 1 số xấu ⇒ giữ 0 tới khi có **3 số
  tốt liên tiếp**; số chập chờn tốt-xấu xen kẽ cũng dừng. Nút "**Heat cut**" (giữ nút ngọn lửa gạch): dừng mọi tự động, lửa 0,
  gió + hút mở hết, **trống vẫn quay, hạt vẫn trong trống** (xả là việc của người).
- **loring-link** (Loring S7/S15/S35, PLC Koyo, UDP 28784, giao thức dò ngược): lệnh gas %, quạt nguội (nhấn-nhả), DROP — trên HMI
  thật DROP phải **giữ 1,2 s**; web UI của họ bắt giữ 1,5 s. Khớp luật "giữ 1 s" của OTL.
- Áp Hồng: khi đọc máy thấy **BT phẳng lúc lửa cao** hoặc **không có số mới** ⇒ nghi đầu dò trước khi nghi nhiệt động học;
  ngưng khuyên dựa trên số cũ (mục 2).

## 6. Preheat tự học (TilauPID — `preparing-a-roast.md`)

- Hai thứ học lại sau mỗi lần preheat **ở cùng setpoint**: **công suất giữ** nhiệt đó và **độ sớm phải nhả** để không vọt.
  Thuộc về máy + phòng, đo chứ không giả định.
- Nhãn kinh nghiệm: *Learning* (setpoint mới) → *Estimated* (mượn điểm gần / đặc tính chung) → *Tuned* (đã có preheat thật ở
  đúng setpoint) → *Calibrated* (đủ nhiều, ổn định — không phải để đuổi theo).
- Điều kiện một lần preheat được tính: ≥ 1 phút quan sát, cửa sổ nhiệt đủ, giữ ổn định liên tục quanh setpoint. Giới hạn mỗi
  phiên được dời bao nhiêu — 1 gai đầu dò không chi phối mô hình.
- Học riêng **theo máy + theo kênh BT/ET**; nội suy liên tục giữa các setpoint đã học (không nhảy ở mốc 10 °C); ngoài vùng học
  thì phai dần về mặc định trong 15 °C; hai điểm cách > 40 °C không nối (khác chế độ nhiệt).
- Mô hình nhiệt mới dựng offline phải qua **shadow validation**: 3 lần preheat thật liên tiếp chỉ *dự đoán* (không điều khiển),
  sai số trong giới hạn mới được dùng. → Khớp cách Hồng học mô hình trễ Nhiệt% → SV → buồng → ET → BT.
- Lời nhắc preheat: "PID đang lên — để nó làm, nạp khi BT ổn ± 2°" → "gần SV — PID sẽ cắt, vọt nhẹ là bình thường" → "✅ đạt SV
  — ổn rồi nạp". Nút charge chỉ mở khi BT ổn định.

## 7. Chỉ số, định dạng log, dữ liệu

- **kaffelogic-klog** (`.klog` là TSV, cột có tiền tố `#`, `=`, `^`):
  - **TP** = hàng có `meanTemp` thấp nhất trong **5–60 s** đầu.
  - **FC** = hàng đầu tiên `temp` **đã lọc** ≥ `expect_fc`. **Không dùng `meanTemp`** — trung bình trễ báo FC muộn **5–20 s**.
  - **Drop** = hàng cuối sau khi cắt ở `roast_end`; không có dấu thì cắt ở đỉnh `temp` nếu đạt nhiệt drop đích; không thì giữ hết (log dở).
  - Hao hụt % = (xanh − rang) / xanh × 100 — chỉ số theo cân, không có trong log.
  - "Vân tay mẻ": DTR, RoR TB trước FC, RoR TB đoạn dev, hao hụt (vd Kenya: 15,4 % / 28,6 / 7,2 °C/phút / 11,67 %).
  - Bài học chung: **mốc dò bằng nhiệt trung bình trễ luôn trễ** — dò mốc trên nhiệt đã lọc nhẹ, không trên trung bình dài.
- **RoastCurve**: RoR = sai phân trung tâm cửa sổ ±15 s (bỏ khi dt < 1 s để khỏi nổ số); EMA α 0,35 cho RoR hiển thị;
  **làm mượt SV kiểu Artisan `smooth_sv()`** (trung bình trọng số 1..n, mới nặng hơn) — biến bậc thang của mẫu thành dốc thoải;
  gió thích nghi theo RoR đích của mẫu. Mẫu lưu gió dạng điểm neo thưa (chỉ điểm đổi ≥ 2 %).
- **Đọc log máy khác** để nhận khách đổi máy: Kaffelogic `.klog` (kaffelogic-klog), Aillio RoasTime (roastime-data → CSV có
  ambient, humidity), Ikawa (libikawa, giao thức BLE dò ngược), Hottop (pyhottop), FreshRoast SR700; Artisan nhập Cropster,
  ROEST CSV, Stronghold. RoastCurve nhập `.alog` cả sự kiện.
- **CQI** (jldbc/coffee-quality-database): 1 312 Arabica + 28 Robusta, điểm Aroma/Flavor/Aftertaste/Acidity/Body/Balance/
  Uniformity/Clean Cup/Sweetness + Moisture, Defects, sơ chế, màu, quốc gia, độ cao, vùng (cào 01/2018, form 2004 — không trộn với CVA,
  xem `cupping-sca.md`).
- Đo cỡ xay bằng ảnh điện thoại trên tờ giấy in mẫu (jantielens): r = 0,99 với nấc xay, CV ~4,6 %; **bắt buộc đèn flash**
  (không flash r tụt 0,854); watershed cổ điển thắng Cellpose (học sâu) cả độ chính xác lẫn tốc độ ×30.

## 8. Cảm biến mới và mức rang (roastronaut, Artisan)

- **Micro I2S INMP441** nghe nổ; **camera trong buồng** chấm màu ~mỗi 10 s; LLM viết nhận xét sau mẻ. (Repo đang ở giai đoạn
  kế hoạch — chưa chứng minh.)
- ADR 0001: **nhiệt drop chỉ là số đại diện cho mức rang, không phải sự thật** — chấm model camera theo người đọc hạt, không theo
  BT drop (nếu không thì camera thừa). Drop vẫn giữ làm kiểm tra nhanh.
- ADR 0002: mức rang "quan sát" đọc trên **hạt đã nguội, đã nghỉ**; đọc trong buồng là thứ được đo, không phải chuẩn.
- ADR 0003: thang 9 bậc = 1 hạt xanh + 8 ô Agtron SCA (#95 Very Light → #25 Very Dark). So mắt với ô màu sai ~**1 ô**.
  Bộ ô SCA ~290 USD, máy đo màu từ ~750 USD, thẻ in ~20 USD.
- Artisan 3.x: cảm biến màu ColorTrack, ghi khối lượng hạt lỗi, phát lại sự kiện có tăng dần (ramping), quản lý lô mẻ, lập lịch
  rang, công tơ năng lượng, thí nghiệm lên men nhiều ngày.

## 9. Năng lượng (tilauscope `energy.md`, Artisan 3.4)

- Đo **công suất thật** từ công tơ (MQTT; Shelly) từ lúc bật theo dõi: tách **trước CHARGE / trong mẻ / sau DROP**,
  **kWh trên 1 kg hạt xanh**, CO₂; hút khói đo riêng (sensor `extractor`). Mẻ cũ có số công tơ cũng tính lại được.
- Không có công tơ ⇒ ước từ công suất danh định (đánh dấu là *ước*). Luôn ghi **nguồn** của số năng lượng.
- Đây là điện tiêu thụ của cả hệ, **không** phải nhiệt hạt hấp thụ. → OTL đã có hướng dẫn công tơ 7KT0311: tính kWh/kg + gas
  theo mẻ để so mẻ, so preheat, và báo cho khách.

## 10. Giao diện, quy trình phát triển đáng học

- Lái từ điện thoại (tilauscope): ghép bằng **QR hạn ngắn**, cùng mạng LAN; điện thoại mới ghép **chỉ xem**, phải "nhận quyền"
  mới lái; **1 tháng không kết nối ⇒ tự mất ghép**; đổi tên / thu hồi tức thì. (Liên quan PC_control / cấp quyền lái của OTL.)
- Web UI chạy trên chính cầu ESP32 (RoastCurve): **làm mới / khóa màn / đổi máy vẫn khôi phục giờ, sự kiện, đường cong**; vẽ đường
  BT bằng điểm neo kéo thả, lưu làm mẫu và bám; xuất zip.
- Cầu ESP32 thay bộ chuyển RS485-WiFi: gateway Modbus TCP↔RTU chuẩn (sai CRC / không trả lời ⇒ trả khung exception, không treo),
  cài WiFi qua điểm phát riêng, OTA, đèn trạng thái theo màu, cổng HTTP trả JSON `rssi/uptime/client`, chân GPIO đổi được,
  giữ BOOT 3 s về mặc định.
- LibreRoaster: chế độ **cảm biến giả trên phần cứng thật**, 735 test chạy trên máy tính, ví dụ HIL từng khối; lệnh `STATUS` trả
  20 trường (nhiệt, cơ cấu, watchdog, PID, độ trễ, cờ khẩn). Telemetry chủ động `#` mặc định TẮT (Artisan tự hỏi `READ`).
- Artisan GitHub (issue, phản hồi người dùng): xem `artisan-github.md`.
