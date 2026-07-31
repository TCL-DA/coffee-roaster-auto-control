---
name: artisan-ror
description: Toàn bộ cách Artisan tính RoR (tốc độ tăng nhiệt) và lọc nhiệt độ — 4 thuật toán RoR (arrayRoR / polyRoR / Savitzky-Golay / decay), thứ tự áp bộ lọc, ý nghĩa từng ô trong hộp Curves → RoR và Curves → Filters, bảng tham số mặc định kèm quy đổi UI↔nội bộ, và đối chiếu với firmware OTL + tools/roast_derive.py. Dùng skill này bất cứ khi nào nói tới "RoR", "Delta BT", "ΔBT", "tốc độ tăng nhiệt", "delta span", "smoothing", "làm mượt đường rang", "lọc nhiễu cảm biến", "drop spikes", "median filter", "Savitzky-Golay", "polyfit RoR", "projection nhiệt", "RoR sao khác Artisan", "RoR giật/nhiễu", "chỉnh mượt đường delta", hay khi cần chép/đối chiếu công thức RoR của Artisan sang firmware/app OTL — kể cả khi không nhắc chữ Artisan.
allowed-tools: Read, Grep, Glob
---

Skill này đúc kết từ **source thật** của Artisan trong repo: `_external/artisan-master/artisan-master/src/artisanlib/`
(`util.py` giữ toàn bộ phần toán, `canvas.py` giữ đường chạy trực tiếp và bộ lọc đầu vào,
`curves.py` là hộp thoại Curves mà thợ nhìn thấy). Mọi số và công thức dưới đây đọc từ code,
không lấy từ tài liệu — code là sự thật.

## Vì sao cần skill này

RoR là con số quyết định cả mẻ rang, nhưng "RoR" của Artisan **không phải một công thức** — nó là
một chuỗi 4 tầng, mỗi tầng có bộ lọc riêng, và kết quả đổi rất nhiều tuỳ cấu hình. Firmware OTL và
`tools/roast_derive.py` dùng một công thức khác hẳn (cửa sổ 3 giây + Kalman). Muốn so số của mình với
Artisan, hay muốn chép cách làm của họ, phải biết đang so tầng nào.

## Bốn tầng — phải nhớ đúng thứ tự

Đây là xương sống; sai thứ tự là giải thích sai mọi hiện tượng:

```
1. LỌC ĐẦU VÀO      inputFilter()      canvas.py:4550   ← trên số THÔ, lúc đọc từng mẫu
   trùng lặp → giới hạn min/max → gai nhiễu

2. LÀM MƯỢT ĐƯỜNG   smoothETBT()       canvas.py:9081   ← ET/BT thành stemp1/stemp2
   vá lỗ hổng → lọc trung vị → cuộn cửa sổ hanning

3. TÍNH RoR         computeDeltas()    util.py:1255     ← TỪ ĐƯỜNG ĐÃ MƯỢT, không phải số thô
   chọn 1 trong 4 thuật toán → công thức tự đặt → làm mượt RoR

4. CẮT & KẸP        computeDeltas()    util.py:1342     ← bỏ ngoài CHARGE..DROP, kẹp trần RoR
```

**Điểm dễ hiểu sai nhất:** RoR được tính từ **đường đã làm mượt** ở tầng 2, không phải từ số thô.
Chính tooltip của ô "Smooth Curves" nói vậy (`curves.py:381`: *"Resulting signal is used for RoR
computation"*). Nên đổi "Smooth Curves" là RoR đổi theo, dù ô đó nằm ở nhóm khác trong hộp thoại.

## Tài nguyên

| File | Nội dung | Khi nào đọc |
|------|----------|-------------|
| [references/ror-thuat-toan.md](references/ror-thuat-toan.md) | 4 thuật toán RoR kèm công thức thật, cách làm mượt RoR (hanning vs decay), phép chiếu nhiệt (projection) | Hỏi "RoR tính thế nào", cần chép công thức |
| [references/bo-loc.md](references/bo-loc.md) | Từng bộ lọc trong tab Filters: làm gì, ngưỡng nào, chạy lúc rang hay chỉ sau rang | Nhiễu cảm biến, đường giật, chọn bộ lọc |
| [references/tham-so.md](references/tham-so.md) | Bảng tham số: nhãn trên UI ↔ tên biến ↔ mặc định ↔ dòng code, kèm quy đổi UI↔nội bộ | Tra một ô trong hộp Curves, hoặc set giá trị |
| [references/doi-chieu-otl.md](references/doi-chieu-otl.md) | So RoR của Artisan với firmware OTL và `tools/roast_derive.py` — khác ở đâu, muốn khớp thì sửa gì | Số của mình lệch Artisan, hoặc muốn chép sang app |

## Ba quy đổi phải nhớ, sai là lệch hẳn

Ba cái này gây sai nhiều nhất khi đọc code hoặc set tham số:

- **Giá trị trên UI ≠ giá trị trong biến.** `nội bộ = UI × 2 + 1` (`curves.py:2422`, `:2504`); đọc
  ngược lại là `UI = round((nội bộ − 1) / 2)` (`curves.py:360`, `:366`, `:387`). Cửa sổ làm mượt phải
  **lẻ** nên mới có phép đó. Ví dụ ảnh chụp Smoothing 30 → `deltaBTfilter = 61`; Smooth Curves 2 →
  `curvefilter = 5`. Mặc định trong code là `deltaBTfilter = 7` (UI 3) và `curvefilter = 3` (UI 1).
- **Delta Span tính bằng GIÂY, thuật toán dùng SỐ MẪU.** `deltaBTsamples = max(1, round(deltaBTspan /
  interval))` (`canvas.py:2817`), với `interval` là chu kỳ lấy mẫu. Span 20 s ở chu kỳ 1 s → 20 mẫu;
  cùng span đó ở chu kỳ 2 s → 10 mẫu. **Đổi chu kỳ lấy mẫu là đổi luôn RoR** dù không chạm ô nào.
- **RoR luôn quy về °/phút**, còn nhiệt độ theo mẻ là °/giây — mọi công thức đều có `×60` hoặc `/60`
  ở đâu đó. Nhìn thấy 60 trong code thì đó là chỗ quy đổi, đừng "tối giản".

## Lúc rang khác hẳn sau khi rang

Nhiều bộ lọc **chỉ chạy khi xem lại**, nên số trên máy lúc đang rang không bao giờ trùng số sau khi
mở lại file. Cờ phân biệt là `self.flagon` (đang ghi) và `optimalSmoothing`:

| Việc | Lúc đang rang | Sau khi rang |
|------|---------------|--------------|
| Làm mượt ET/BT | **không** làm mượt, chỉ vá lỗ hổng (`canvas.py:9090`) | cuộn cửa sổ hanning theo `curvefilter` |
| Lọc trung vị (Smooth Spikes) | **không** (`filter_dropouts = filterDropOuts and not flagon`) | có, k = 5 cho đường / 3 cho RoR |
| Thuật toán RoR | hai điểm mút hoặc polyfit | thêm được Savitzky-Golay nếu bật Optimal Smoothing |
| Làm mượt RoR | decay (trọng số tăng dần, không trễ pha) | hanning đối xứng (mượt hơn nhưng cần biết tương lai) |
| Cửa sổ làm mượt RoR | `round(filter/2)` — **một nửa** | `filter` đầy đủ |

Lý do của cả bảng này: lúc đang rang không được nhìn tương lai, nên chỉ dùng lọc nhân quả (decay) và
cửa sổ nửa. Sau khi rang thì có cả hai chiều, dùng lọc đối xứng cho mượt hơn mà không lệch pha.

## Một chỗ Artisan có lỗi — đừng chép nguyên

Bộ lọc **Drop Spikes** ở `canvas.py:4592` có điều kiện:

```python
if (pRoR + dRoR_limit) < RoR < (pRoR - dRoR_limit):
```

Với `dRoR_limit > 0` (mặc định 4.2 °C/s) thì biên dưới luôn **lớn hơn** biên trên → điều kiện không
bao giờ đúng → **ô "Drop Spikes" thực tế không cắt gai nào**. Chép sang OTL thì phải sửa thành `RoR >
pRoR + dRoR_limit or RoR < pRoR - dRoR_limit`. Chi tiết ở [bo-loc.md](references/bo-loc.md) mục 1c.

## Liên quan trong repo

- Bộ suy diễn của mình: `tools/roast_derive.py`; tham số ở `protocol/pc_link.json` mục `derive`.
- RoR trong firmware: `include/Program.h` (`rorBT`, `rorBT_pro`) — xem skill `quy-trinh-dieu-khien-may-rang`.
- Ý nghĩa mốc rang & thanh ghi `$M`: skill `rang-ca-phe`.
