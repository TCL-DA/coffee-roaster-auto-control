# Kế hoạch nâng cấp OTL Roast Lab — GĐ5 → GĐ8 (TRẢI NGHIỆM NGƯỜI DÙNG)

> Nối tiếp `plan-hmi-roadmap.md`. Cập nhật: 2026-07-24 (viết lại — lấy TRẢI NGHIỆM
> thợ rang làm trung tâm, không phải tính năng kinh doanh).

## La bàn: thực tế của người thợ

- **Mắt thợ ở TRỐNG, không ở màn hình.** Họ nhìn màu hạt, nghe tiếng crack, ngửi khói,
  rút trier — panel chỉ liếc. App bắt dán mắt vào màn = sai.
- **Đứng cách panel 1–2m**, cạnh burner nóng, khói mờ, đèn chói, RS485 nhiễu.
- **Tay bận & bẩn**, đeo găng, cầm trier/xẻng; lặp cùng thao tác **~60 lần/ngày**, nhiều
  ca, mỏi mắt cuối ca.
- **Một mẻ 12–18 phút căng thẳng** — sai 10 giây là hỏng cả mẻ (bản ghi kinh doanh).

→ 4 giai đoạn dưới đi theo đúng thứ tự giác quan của thợ: **NGHE → NHÌN LƯỚT → CHẠM →
THOẢI MÁI**. Mỗi cái làm app *dễ chịu hơn khi dùng*, không thêm việc.

| GĐ | Tên | Một câu |
|---|---|---|
| **5** | **Rang không cần nhìn màn** | App "nói" cho thợ nghe, mắt để trên trống |
| **6** | **Liếc một cái là hiểu** | Số to, màu vùng, đọc được từ xa qua khói-chói |
| **7** | **Ít chạm, nhanh tay, tha lỗi** | Đeo găng vẫn mượt, lỡ tay hoàn tác được |
| **8** | **Thoải mái cả ngày & dễ học** | Hợp từng thợ, thợ mới cũng chạy được ngay |

> Âm chạm kim loại (vừa làm) là **viên gạch đầu** của GĐ5 — đúng hướng này.

---

## GĐ5 — Rang không cần nhìn màn (tai thay mắt)

> **Điểm đau:** đang canh crack thì phải liếc màn xem giây/nhiệt → rời mắt khỏi trống →
> lỡ khoảnh khắc. Giải: cho thợ **NGHE** thay vì nhìn.

1. **Âm mốc rang riêng biệt** — mỗi mốc một tiếng kim loại khác nhau: quay đầu (TP),
   khô vàng, **crack đầu (FCs)**, crack sau, tới nhiệt xả. Thợ nghe là biết, không liếc.
2. **Giọng nói tiếng Việt** báo mốc + đếm ngược: *"Crack đầu"*, *"Còn 30 giây"*, *"Xả mẻ!"*.
   Rảnh tay, mắt trên trống — đây là thứ thợ mê nhất.
3. **Chuông báo động khác hẳn** khi bất thường (RoR gãy, nhiệt vọt, mất kết nối giữa mẻ)
   — tiếng gắt để giật mình đúng lúc, không lẫn tiếng thường.
4. **Nhịp "tick" theo RoR** (như nhịp tim) — tick nhanh/chậm cho biết RoR lên/xuống mà
   khỏi nhìn số. Bật/tắt riêng.
5. **Âm cho hành động chính** — START, DROP, lưu hồ sơ có tiếng xác nhận riêng (mở rộng
   âm chạm đã có). Chỉnh **âm lượng** + tắt từng loại.

**Vì sao trước tiên:** rẻ (đã có nền Web Audio), tác động lớn nhất tới cách thợ *thật sự*
đứng máy. Không cần phần cứng mới.

---

## GĐ6 — Liếc một cái là hiểu (nhìn-từ-xa)

> **Điểm đau:** đứng xa 1–2m, khói mờ, đèn chói → số nhỏ đọc không ra, phải bước lại gần.

1. **Số khổng lồ nhìn-từ-xa** — BT & RoR to hết cỡ, đọc được từ đầu kia xưởng.
2. **RoR đổi MÀU theo vùng** (xanh đẹp / vàng chớm / đỏ vọt) — nhận ra "đang ổn hay hỏng"
   bằng màu, khỏi đọc số. (Kèm chữ/biểu tượng cho thợ mù màu.)
3. **Đếm ngược tới mốc kế** — *"tới crack ~1:20"*, *"xả sau ~40s"* — thợ chủ động canh.
4. **Chế độ "màn to" 1 chạm** — ẩn hết, chỉ còn BT · RoR · phase · đồng hồ, chữ cực lớn.
   Dành lúc canh crack căng thẳng.
5. **Chống chói / ca tối** — nút tăng sáng-tương phản nhanh; theme workshop độ nét cao;
   tự dịu màn ban đêm. Đọc rõ dù nắng hắt hay đèn vàng.
6. **Thanh tiến trình mẻ** — nhìn phát biết đang ở phase nào, còn bao xa tới xả.

**Vì sao:** cùng trục "khỏi dán mắt" với GĐ5 nhưng cho phần *phải nhìn* — nhìn nhanh, xa,
qua khói. Vẫn rẻ, toàn CSS/canvas.

---

## GĐ7 — Ít chạm, nhanh tay, tha lỗi (đeo găng vẫn mượt)

> **Điểm đau:** lặp 60 lần/ngày, đeo găng bấm trượt, lỡ tay là hỏng, popup phiền giữa mẻ.

1. **Luồng mẻ 1 chạm** — nút to *"Bắt đầu mẻ"* lo hết: preheat → charge theo nhiệt → chạy;
   xong mẻ này gợi ý mẻ kế (back-to-back), không phải bấm 5 bước.
2. **Nút to hợp găng tay** — target lớn, cách nhau chống bấm nhầm, vùng chạm nới rộng quá
   viền nhìn thấy; chống double-tap.
3. **Cử chỉ** — vuốt đổi tab, vuốt xuống đóng modal, **giữ để xác nhận** (thay popup) —
   một tay, không cần ngắm.
4. **Thanh tác vụ nhanh luôn hiện** — Bắt đầu / Xả / Mẻ mới bám đáy màn ở MỌI tab, không
   phải quay về tab Rang.
5. **Tha lỗi** — **Hoàn tác** thao tác lỡ (đổi gas nhầm, xoá nhầm); xác nhận CHỈ ở việc
   thật nguy hiểm; báo lỗi kèm cách sửa, không chặn cụt.
6. **Bàn phím số to hợp găng** khi cần nhập; nhập ít nhất có thể.

**Vì sao:** đây là chỗ mỏi mệt tích luỹ cả ngày. Giảm ma sát 60 lần/ngày = đỡ mệt thật.

---

## GĐ8 — Thoải mái cả ngày & dễ học (hợp từng người)

> **Điểm đau:** nhiều ca/nhiều thợ, có thợ mới; dùng 16h liên tục mỏi mắt.

1. **Hồ sơ theo thợ** — mỗi thợ nhớ theme, âm lượng, bố cục, **tay thuận trái/phải** (đảo
   panel điều khiển sang tay thuận).
2. **Chế độ "mới tập"** — gợi ý ngữ cảnh, nhắc bước kế, khoá thao tác nguy hiểm; thợ mới
   không sợ bấm sai. (Nâng `data-help` sẵn có thành tour lần đầu + trợ giúp bật/tắt.)
3. **Chế độ tập trung khi rang** — lúc mẻ chạy, ẩn nhiễu, chống chạm nhầm ngoài vùng cần.
4. **Dễ nhìn cho mọi mắt** — cỡ chữ lớn hơn tuỳ chọn; màu thân thiện mù màu (không chỉ
   dựa màu để hiểu). Nghỉ mắt: tự dịu chói theo giờ.
5. **Nhất quán = trí nhớ cơ** — nút ở đúng chỗ mọi màn, thao tác giống nhau → tay tự biết,
   không phải tìm.

**Vì sao:** giữ thợ dùng thoải mái ca dài, và để **bán cho xưởng khác** thì thợ lạ cũng
cầm là chạy — trải nghiệm chính là thứ khách nhớ.

---

## Thứ tự khuyến nghị

1. **Chốt nền trước** — test máy thật · commit (đừng nâng cấp trên nền chưa vững).
2. **GĐ5** — giọng nói + âm mốc rang: rẻ nhất, thợ *cảm* được ngay, đúng cách họ đứng máy.
3. **GĐ6** — số to + màu vùng RoR + màn-to: cũng rẻ, "wow" khi đứng xa.
4. **GĐ7** — ít chạm + tha lỗi: đỡ mệt cả ngày.
5. **GĐ8** — cá nhân hoá + dễ học: chốt trải nghiệm, sẵn sàng bán.

> **Không lạc hướng:** kho FULL / cloud / P&L / AI lái máy là **tính năng kinh doanh** —
> để riêng, KHÔNG trộn vào 4 GĐ trải nghiệm này. Ở đây chỉ lo **thợ dùng sướng**.
