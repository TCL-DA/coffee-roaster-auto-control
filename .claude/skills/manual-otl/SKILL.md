---
name: manual-otl
description: Dựng tài liệu hướng dẫn sử dụng máy rang O Tesla bằng Illustrator — chạy script JSX qua COM, tự dàn trang A4 đúng style bộ manual OTL (bìa, header/footer xanh, hộp cảnh báo ISO 3864, bảng, sơ đồ trạng thái, ảnh có khung chú thích đánh số), xuất .ai + .pdf. Dùng khi người dùng nói "làm hướng dẫn sử dụng", "viết manual", "thêm chương vào manual", "hướng dẫn chức năng ... cho khách", "dựng tài liệu bằng Illustrator", "làm catalogue/tờ hướng dẫn cho máy", hoặc đưa ảnh chụp màn hình HMI kèm yêu cầu soạn tài liệu. KHÔNG dùng cho thiết kế logo/banner (xem skill design).
---

Skill dựng manual máy rang OTL bằng Illustrator. Nội dung viết ra file `content.jsx`, phần
dàn trang do `assets/engine.jsx` lo — không tự vẽ tay từng khung chữ trong Illustrator.

## Khi nào dùng
- Viết chương mới cho bộ manual máy rang (tiếng Việt hoặc tiếng Anh).
- Cập nhật/dựng lại một chương đã có khi chức năng máy đổi.
- Làm tờ hướng dẫn ngắn kèm ảnh màn hình HMI cho khách.

## Quy trình 7 bước

1. **Hỏi cho rõ trước khi dựng** — viết cho máy nào (OTL-06/12, Auto, hay máy riêng của
   khách), độ dày mong muốn, ảnh minh hoạ lấy từ đâu. Khác máy là khác giao diện HMI.
2. **Lấy nội dung từ nguồn thật, không bịa số.** Thông số vận hành đọc thẳng từ firmware
   (`include/Config.h`, `include/Preheat_PID.h`, `include/Program.h`), không lấy từ trí nhớ.
   Số nào không tra được thì hỏi, đừng đoán.
3. **Đối chiếu ảnh màn hình với văn bản.** Luồng thao tác phải khớp đúng giao diện thật —
   xem ảnh trước, viết bước sau. Đây là lỗi hay gặp nhất: viết theo suy đoán rồi phải sửa lại
   toàn bộ chương.
4. **Viết `content.jsx`** gọi các hàm của engine (xem bảng API bên dưới). Tham khảo
   [content-mau-preheat.jsx](references/content-mau-preheat.jsx) — chương 15 trang đã giao khách.
5. **Dựng và soi lại**: nối engine + content → chạy qua COM → xuất PDF → **render từng trang
   ra PNG và xem bằng mắt**. Bắt buộc, vì lỗi tràn khung/chồng chữ không hiện ra ở log.
6. **Giao hàng**: copy `.ai` + `.pdf` ra thư mục gốc của tài liệu, mở file trong Illustrator
   cho người dùng xem, gửi kèm cả hai file.
7. **Chốt phiên bản**: cập nhật số phiên bản ở bìa + trang công ty, ghi một dòng vào
   `LICH-SU-PHIEN-BAN.md`, chép bản vừa giao vào `phat-hanh\` kèm số phiên bản.
   Chi tiết: [references/quan-ly-phien-ban.md](references/quan-ly-phien-ban.md).

## Lệnh chạy

```bash
# 1. nối engine + nội dung
cat engine.jsx content.jsx > manual.jsx
```

```powershell
# 2. chạy qua COM (Illustrator tự mở nếu chưa chạy)
$ai = New-Object -ComObject Illustrator.Application
while ($ai.Documents.Count -gt 0) { $ai.ActiveDocument.Close(2) }   # dọn doc lỗi của lần trước
$ai.DoJavaScriptFile("<đường dẫn tuyệt đối>\manual.jsx")
```

```bash
# 3. render ra PNG để soi bố cục
python -c "import fitz; d=fitz.open('ten.pdf');
[d[i].get_pixmap(dpi=78).save(f'p_{i+1:02d}.png') for i in range(d.page_count)]"
```

Script trả về chuỗi `OK pages=N | thieu anh: ...` — dòng "thiếu ảnh" liệt kê file chưa có,
engine tự vẽ ô nét đứt thay chỗ nên vẫn dựng được khi ảnh chưa đủ.

## API của engine

| Hàm | Dùng để |
|-----|---------|
| `coverImage = "ten-anh.png"` | Chọn ảnh máy in lên bìa — đặt TRƯỚC `COVER()` (`may-rang-auto-bia.png` = máy Auto, `may-rang-bia.png` = máy 06/12) |
| `COVER(kicker, title, subtitle, machine, footline)` | Trang bìa (phải gọi ĐẦU TIÊN, thay `newDoc`) |
| `COMPANY(tên, mô_tả, [[nhãn, giá_trị], ...], tiêu_đề_lưu_ý, thân_lưu_ý)` | Trang thông tin nhà sản xuất |
| `TOCRESERVE()` … `TOCDRAW(tiêu_đề, "PH-")` | Mục lục: giữ chỗ ngay sau trang công ty, gọi `TOCDRAW` TRƯỚC khi xuất file — số trang tự điền từ các `H1` |
| `newDoc()` | Mở tài liệu không có bìa |
| `chapterHeader = "..."; addPage();` | Sang trang mới; **gán header TRƯỚC `addPage`** |
| `H1 / H2(số, chữ) / H3` | Tiêu đề chương / mục có huy hiệu tròn xanh / tiêu đề nhỏ |
| `P / PI / BUL([...])` | Đoạn canh đều / ghi chú nghiêng xám / danh sách gạch đầu dòng |
| `STEP(n, chữ)` | Bước đánh số |
| `STEPIMG(n, chữ, file, chữ_sau, rộng)` | Bước có ảnh nút bấm bên dưới |
| `IMG(file, rộng, chú_thích)` | Ảnh căn giữa |
| `IMGC(file, rộng, chú_thích, marks, legend)` | Ảnh + khung đỏ đánh số; `marks=[[x,y,w,h,"1"],...]` theo **tỉ lệ 0–1** của ảnh |
| `TABLE(cols, rows, widths)` | Bảng (tổng `widths` = 435.28); tự lặp lại hàng tiêu đề khi sang trang |
| `SAFETY(loại, tiêu_đề, thân)` | Hộp cảnh báo; loại: `nguyhiem` đỏ / `canhbao` cam / `thantrong` vàng / `luuy` xanh |
| `STATEFLOW([[tên, mô_tả, thời_gian], ...])` | Sơ đồ các bước nối bằng mũi tên |
| `RULE()` / `GAPV(h)` | Đường kẻ ngang / chừa khoảng trắng |

Engine tự đo chiều cao chữ và tự sang trang, nên **không tự tính toạ độ y**.

## Bẫy đã trả giá — đọc trước khi sửa engine

- **Canvas Illustrator chỉ 16384 pt.** Xếp artboard một hàng ngang là gãy từ trang 13 với lỗi
  `AOoC`. Engine xếp lưới `COLS = 5` — đừng đổi về hàng ngang.
- **`textFrame.paragraphs[0]` ném lỗi 1302** khi khung chữ rỗng. Luôn dùng
  `textRange.paragraphAttributes` bọc `try/catch`.
- **`position` của text frame là góc trái-TRÊN**, không phải baseline. Tính theo baseline là
  chữ tụt nửa dòng khỏi thanh màu.
- **KHÔNG sửa file .jsx tiếng Việt bằng `sed` hay `perl -i`** — hỏng encoding UTF-8 và nuốt
  escape `\uXXXX`. Sửa bằng công cụ Write (ghi lại nguyên file) hoặc Python đọc/ghi UTF-8.
- **Chữ canh đều** phải dùng `FULLJUSTIFYLASTLINELEFT`, không phải `FULLJUSTIFY` — nếu không
  dòng cuối mỗi đoạn bị kéo giãn hết chiều ngang.

## Tài nguyên có sẵn

- Bộ dàn trang: [assets/engine.jsx](assets/engine.jsx) — copy sang thư mục build của tài liệu mới.
- Bản tiếng Anh làm mẫu: [references/content-mau-preheat-EN.jsx](references/content-mau-preheat-EN.jsx).
- **Thông tin công ty** — CHỦ MÁY ĐÃ XÁC NHẬN 30/08/2026, dùng thẳng, KHÔNG hỏi lại:
  CÔNG TY TNHH CÔNG NGHIỆP O TESLA — VP 44 Đường N5, KP. Tân Phước, P. Tân Đông Hiệp, TP. HCM
  — Nhà máy 398/33 ĐT743B, KP Đông Thành, P. Tân Đông Hiệp, TP. HCM — **ĐT 0936 198 938
  (+84 936 198 938)** — **WhatsApp cùng số +84 936 198 938** — **otlpro.com@gmail.com**
  — MST 0314844413.
  Trang nhà sản xuất nên có thêm dòng WhatsApp vì khách nước ngoài hay liên hệ qua kênh này.
  ⚠ Phiếu báo giá `105_Bao_gia\OTL_PhieuBaoGia_Trong.xlsx` còn ghi email CŨ
  `otesla.vn@gmail.com` — ĐỪNG chép lại. Gặp số `938 198 938` ở đâu thì đó là SAI, đúng là `936`.
- Quy cách trình bày (khổ, lề, cỡ chữ, màu): [references/style-otl.md](references/style-otl.md).
- Icon/logo/ảnh máy trích sẵn từ manual cũ:
  `F:\Project\112_Quanly\122_Manual_AI\preheat-vi\images\_tu-manual-cu\`
- Bộ manual gốc để đối chiếu style: `F:\Project\112_Quanly\122_Manual_AI\*.pdf`
  (2 file này KHÔNG có lớp chữ — phải render trang ra ảnh mới đọc được).

## Phiên bản và tài liệu song ngữ

**Tài liệu đã giao khách thì không sửa đè lặng lẽ.** Sửa nhỏ (chính tả, liên hệ, ảnh) tăng số
lẻ 1.0 → 1.1; sửa nội dung vận hành/an toàn/thông số tăng số chẵn 1.1 → 2.0. Số phiên bản phải
khớp ở **ba chỗ**: chân trang bìa, dòng "Phiên bản" trong trang công ty, và bảng trong
`LICH-SU-PHIEN-BAN.md`.

**VI và EN luôn cùng một phiên bản** — sửa một bên là phải dựng lại cả hai, không có ngoại lệ.
Sau khi dựng, so số trang hai bản và kiểm lại trang công ty của cả hai.

Toàn bộ quy tắc + lệnh chép bản phát hành:
[references/quan-ly-phien-ban.md](references/quan-ly-phien-ban.md).

## Bộ trang chuẩn của một tài liệu hoàn chỉnh

Bìa → trang thông tin nhà sản xuất → mục lục → nội dung → phụ lục. Thiếu một trong ba trang
đầu là tài liệu chưa giao được cho khách.

## Giọng văn

Tiếng Việt cho thợ vận hành: câu ngắn, chủ ngữ rõ ("máy tự...", "người vận hành phải..."),
không dùng từ kỹ thuật lập trình. Tên nút và tên ô trên màn hình giữ **nguyên tiếng Anh như
trên HMI** (Set temp, Bean temp, Burner, Airflow) để thợ nhìn máy là khớp ngay.
