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

**Một lệnh, đứng ở thư mục chứa file nội dung:**

```bash
python "<skill>\assets\make.py" content.jsx
python "<skill>\assets\make.py" content.jsx content-vi.jsx   # nhiều bản, CHUNG một phiên
python "<skill>\assets\make.py" content.jsx --nhanh          # bản nháp: bỏ lưu .ai
```

### Dựng cho nhanh — đo thật 30/09/2026, tài liệu 15 trang

| Khâu | Thời gian |
|---|---|
| Illustrator khởi động **nguội** | **~32 s** — chỉ tốn một lần |
| Đóng tài liệu còn sót lại | ~2 s (**~9 s** nếu để dồn nhiều bản) |
| Vẽ 15 trang | ~4 s |
| Lưu `.ai` | ~1,2 s |
| Lưu `.pdf` | ~1,0 s |
| Render PNG + rà soát | ~0,5 s |

Ba việc `make.py` làm sẵn, không phải nhớ:

1. **Đóng tài liệu ngay trong lần chạy đó** — không để dồn sang lần sau.
2. **Nhiều file thì dùng chung một phiên PowerShell**, không bắt COM lại từng lần.
3. `--nhanh` bỏ bước lưu `.ai` khi chỉ cần xem bố cục.

Kết quả: **17 s → 11 s mỗi tài liệu** (`--nhanh`: **9 s**).

⛔ **Đừng tắt Illustrator giữa chừng** — bật lại mất 32 giây, nhiều hơn cả việc dựng.
Tối ưu render PNG hay khâu rà soát là vô nghĩa: cả hai cộng lại chưa tới 0,5 giây.

`make.py` làm liền một mạch: nối engine + nội dung → chạy Illustrator qua COM → render PNG →
rà máy tìm trang thưa chữ. Nhận nhiều file một lượt (`content.jsx content-vi.jsx`), có
`--khong-anh` để bỏ khâu render và `--dpi 110` khi cần soi kỹ. Nó cũng **cảnh báo sớm** chỗ
thiếu dấu cách trước `–` — lỗi dính chữ hay lọt ra tận bìa.

Kết quả in ra:

```
== content.jsx
  OK pages=15
  bookmark=20 (soat lai tren file: 20)
  khong co trang thua chu
```

`OK pages=N | thieu anh: ...` — dòng "thiếu ảnh" liệt kê file chưa có, engine tự vẽ ô nét đứt
thay chỗ nên vẫn dựng được khi ảnh chưa đủ.

⛔ **PDF giao khách BẮT BUỘC có bookmark.** Illustrator xuất PDF từ artboard nên
**không bao giờ tự sinh bookmark** — không gắn thì người đọc phải kéo 17 trang để tìm mục 3.3.
`make.py` tự gọi [`assets/bookmark.py`](assets/bookmark.py) ngay sau khi lưu PDF: nó đọc lại
chính file PDF, lọc chữ **Arial Bold 19 pt** làm mục 1 (H1) và **12,5 pt** làm mục 2 (H2),
đánh số 3.1 / 3.2 … đúng như huy hiệu tròn engine vẽ. Chạy riêng được cho PDF cũ:

```bash
python assets/bookmark.py tai-lieu.pdf
```

Dòng `bookmark=0` hoặc `! KHONG gan duoc bookmark` là **chưa xong**, không được giao.
Số trong ngoặc là lần đọc lại **trên chính file PDF** — hai số lệch nhau là có chuyện.

⚠ Máy rà chỉ bắt trang **thưa chữ**. Chồng chữ, tràn khung, logo chạm tiêu đề thì nó không
thấy — vẫn phải **soi PNG bằng mắt** trước khi giao.

<details><summary>Cách chạy tay từng bước (khi cần gỡ lỗi)</summary>

```bash
cat engine.jsx content.jsx > manual.jsx
```
```powershell
$ai = New-Object -ComObject Illustrator.Application
while ($ai.Documents.Count -gt 0) { $ai.ActiveDocument.Close(2) }   # dọn doc lỗi của lần trước
$ai.DoJavaScriptFile("<đường dẫn tuyệt đối>\manual.jsx")
```
```bash
python -c "import fitz; d=fitz.open('ten.pdf');
[d[i].get_pixmap(dpi=78).save(f'p_{i+1:02d}.png') for i in range(d.page_count)]"
```
</details>

## API của engine

| Hàm | Dùng để |
|-----|---------|
| `coverImage = "ten-anh.png"` | Chọn ảnh máy in lên bìa — đặt TRƯỚC `COVER()` (`may-rang-auto-bia.png` = máy Auto, `may-rang-bia.png` = máy 06/12, `may-rang-cms-bia.png` = bản CMS đã gỡ dấu nhận OEM) |
| `PGPREFIX = "AV-"` | Tiền tố số trang ở chân trang. Mặc định `"PH-"` (bộ preheat) — **tài liệu mới phải đặt lại**, nếu không mục lục và chân trang lệch nhau |
| `LOGO`, `LOGO_W_COVER`, `LOGO_W_HEAD` | Logo và bề ngang (pt) trên bìa / đầu trang. Mặc định `logo-otl.png` 58/34. Bản OEM: `logo-cms.png` **105**/78 — logo CMS nằm ngang, tỉ lệ 2,77:1 |
| `FOOTLINE` | Dòng bản quyền ở chân mọi trang. Mặc định O Tesla; bản OEM đổi sang tên đối tác |
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
| `IMG2(fileA, fileB, cao_max, chú_thích_A, chú_thích_B)` | Hai ảnh cạnh nhau, mỗi ảnh nửa cột, **cùng chiều cao** (mép trên/dưới thẳng hàng) — dùng cho ảnh dọc, so sánh V1/V2, trước/sau. Ảnh chụp đi đôi nên cắt cùng tỉ lệ trước (vd 4:3) để hai ảnh bằng nhau. Ảnh dọc đặt một mình là phí nửa trang |
| `H3TAG("V2", chữ)` | Tiêu đề nhỏ có nhãn màu phía trước — đánh dấu bước chỉ áp cho một bản/tuỳ chọn máy |
| `**chữ**` trong mọi chuỗi | In đậm đúng mấy chữ đó (P, STEP, BUL, ô bảng, hộp cảnh báo). Chỉ nhấn số liệu, hành động then chốt và chữ "không" — đậm cả câu là mất tác dụng |
| `TABLE(cols, rows, widths, [opts])` | Bảng (tổng `widths` = 435.28); tự lặp lại hàng tiêu đề khi sang trang. `opts = {grid: true, minRow: 30}` cho phiếu in ra ký tay (kẻ đủ ô, hàng cao tối thiểu) |
| `SAFETY(loại, tiêu_đề, thân, [biển])` | Hộp cảnh báo; loại: `nguyhiem` đỏ / `canhbao` cam / `thantrong` vàng / `luuy` xanh. `luuy` = hỏng máy/thông tin, **không có tam giác** (ISO 3864-2). `biển` = mảng file ISO 7010 trong IMGDIR, vd `["iso-w017.png"]` (bộ W001/W012/W017/W021 vẽ sẵn ở `ve-sinh-3kg-vi\images\`) — đặt dọc bên trái thân hộp |
| `ICONROW([[file, chú_thích], ...])` | Hàng biển cảnh báo có chú thích — dùng ở mục giải thích ký hiệu chương 1 |
| `STATEFLOW([[tên, mô_tả, thời_gian], ...])` | Sơ đồ các bước nối bằng mũi tên |
| `RULE()` / `GAPV(h)` | Đường kẻ ngang / chừa khoảng trắng |

Engine tự đo chiều cao chữ và tự sang trang, nên **không tự tính toạ độ y**.

## Bản OEM mang thương hiệu đối tác

⛔ **Tên, địa chỉ và liên hệ của đối tác KHÔNG viết vào file này** — skill nằm trong repo git.
Thông tin thương hiệu từng đối tác, tài nguyên logo và danh sách bản OEM đã làm nằm ở
`F:\Project\112_Quanly\122_Manual_AI\BAN-OEM-DOI-TAC.md` (ngoài repo). Đọc file đó trước khi
dựng bản OEM.

Kỹ thuật thì như sau:

- Nội dung kỹ thuật chỉ có **MỘT bản gốc**. Bản OEM là bản **sinh ra bằng script**, không chép
  ra rồi sửa tay hai nơi — sửa bản gốc xong chạy lại script là xong.
- Mẫu script: `122_Manual_AI\airlock-repair-en\lam-ban-cms.py` và `122_Manual_AI\tools\lam-ban-cms.py`.
- Script phải **tự kiểm trước khi ghi file**: còn sót `O Tesla` · `\bOTL\b` · `otlpro` · MST ·
  số điện thoại · địa chỉ nhà máy · `logo-otl.png` thì **dừng, không ghi**.
- Kiểm lại lần nữa **trên chính file PDF** (bóc chữ bằng PyMuPDF), đừng chỉ tin script — ảnh
  bìa cũ vẫn có thể mang dấu nhận OEM dập trên tôn máy mà script đọc mã nguồn không thấy.
- Bề ngang logo trên bìa phụ thuộc độ dài tiêu đề. Dựng xong **đo khe hở giữa tiêu đề và logo**;
  dưới ~25 pt là chật, phải thu logo. Đoạn đo có trong `BAN-OEM-DOI-TAC.md`.

## Xuống dòng thông minh và trình bày — chủ máy yêu cầu 07/10/2026

`mkText()` tự gọi `sapDong()`: dựng chữ xong thì **đọc lại từng dòng Illustrator đã ngắt**, gặp
chỗ xấu thì chèn xuống dòng mềm (ký tự 3) trước chữ cuối của dòng trên, lặp tới khi hết. Bốn chỗ xấu:
chữ mồ côi ở dòng cuối đoạn ("chương | 3."), số tách khỏi đơn vị ("90 | °C", "4–6 | mẻ"), tiền tố tách
khỏi số ("Hình | 4.1", "mục | 2.1"), dòng mới bắt đầu bằng "–". Chỉ áp khi khung rộng > 150 pt
(ô bảng hẹp để nguyên). Tắt bằng `SMARTBREAK = false`.

⛔ **Đừng quay lại cách dùng U+00A0 hay `noBreak`** — đo thật 07/10/2026: Illustrator VẪN ngắt ở U+00A0;
còn `characterAttributes.noBreak = true` thì giữ được nhưng để chữ **tràn ra ngoài lề phải** thay vì
đẩy xuống dòng.

Quy tắc trình bày rút ra từ đợt so với manual Probat:
- **Có một hình tổng thể đánh số bộ phận** ở chương 1, rồi dùng đúng số đó trong mọi bảng, bước, ảnh
  (khung đỏ `IMGC` mang cùng số). Bảng lịch có cột "Số" và cột "Mục" để người đọc nhảy thẳng tới.
- **Máy có nhiều bản/tuỳ chọn thì viết MỘT quy trình**, chỉ tách bước khác nhau bằng `H3TAG("V1"/"V2")`
  và một bảng so sánh ngắn ở chương 1 — không viết thành hai máy (chủ máy sửa 07/10/2026: "V1 và V2
  là một, khác option thôi").
- Ảnh dọc → `IMG2` ghép đôi; ảnh chụp lấy về ≤ 1100 px và đặt `PDFSaveOptions` downsample 200 dpi
  + JPEGHIGH ở cuối content (manual 3kg: 38 MB → 2 MB, gửi được qua Zalo).
- Trước khi viết manual cho một cỡ máy: **grep `112_Quanly\135_TaiLieu_Rang_VanHanh_AnToan\_md\`** —
  ở đó có manual cũ của từng máy (vd `OTL_OTL-03__...` cho 3kg) và phiếu bảo dưỡng có thời gian từng việc.

## Bẫy đã trả giá — đọc trước khi sửa engine

- **Canvas Illustrator chỉ 16384 pt.** Xếp artboard một hàng ngang là gãy từ trang 13 với lỗi
  `AOoC`. Engine xếp lưới `COLS = 5` — đừng đổi về hàng ngang.
  Tài liệu >100 trang: dò 27/09/2026 trên Illustrator 28, artboard nhận được trong x ≥ −7800, mép trên ≤ +8600,
  mép dưới ≥ −7742 (gốc lưới cũ ở 0,0 phí nửa canvas → chỉ ~108 trang). Dời gốc: `OX = -7700, OY = 4500`,
  `COLS = 20` → 280 trang. Không đẩy OY sát 8600 vì hàm đo chữ đặt khung tạm ở y = −3000…−4000.
  Mẫu: `112_Quanly\135_…\06_Rang-ca-phe\MillCityRoasters\build-v3\engine-mc.jsx`.
- **`textFrame.paragraphs[0]` ném lỗi 1302** khi khung chữ rỗng. Luôn dùng
  `textRange.paragraphAttributes` bọc `try/catch`.
- **`position` của text frame là góc trái-TRÊN**, không phải baseline. Tính theo baseline là
  chữ tụt nửa dòng khỏi thanh màu.
- **KHÔNG sửa file .jsx tiếng Việt bằng `sed` hay `perl -i`** — hỏng encoding UTF-8 và nuốt
  escape `\uXXXX`. Sửa bằng công cụ Write (ghi lại nguyên file) hoặc Python đọc/ghi UTF-8.
- **Chữ canh đều** phải dùng `FULLJUSTIFYLASTLINELEFT`, không phải `FULLJUSTIFY` — nếu không
  dòng cuối mỗi đoạn bị kéo giãn hết chiều ngang.
- **Tiêu đề mồ côi / mục bị xé đôi.** `H2` dự phòng **200 pt**, `H3` **150 pt** (30/09/2026, trước
  đó 46/34 rồi 110/88 vẫn xé). Mức thấp hơn thì một mục ngắn bị cắt: tiêu đề + 1 đoạn ở cuối trang,
  đoạn còn lại trôi sang trang sau nằm trơ. Trang vẫn hơi trống thì **thu ảnh trong mục đó** (ví dụ
  `IMG(..., 300 → 200)`) để kéo cả mục lên, thường bớt được nguyên một trang.
- **Công cụ Edit cắt khoảng trắng CUỐI chuỗi**, và không khớp được dòng chứa escape `\uXXXX`.
  Sửa `"Phiên bản 2.0 ` → `"Phiên bản 2.1 ` là mất dấu cách, PDF in ra `2.1– 09/2026` dính chữ,
  ngay trên **bìa**. Sửa các chuỗi này bằng **script Python ghi ra file** rồi chạy (KHÔNG dùng
  heredoc — hỏng chữ Việt có dấu). Trước khi giao, quét `(?<=[^\s"])(\\u2013)` trên mọi
  `content*.jsx` để bắt hết chỗ thiếu dấu cách.
- **PDF không bookmark là chưa xong.** Illustrator không tự sinh; `make.py` gắn hộ,
  nhưng phải nhìn dòng `bookmark=N` mới biết nó ăn. Tài liệu dùng tiêu đề tự vẽ bằng
  `mkText` thay vì `H1()`/`H2()` thì máy không thấy để làm bookmark.
- **Đừng tin dòng `OK pages=N`.** Nó không báo lỗi trình bày. Bắt buộc render PNG và **soi bằng mắt**;
  thêm bước rà bằng máy (đếm ký tự mỗi trang, cờ trang < 420 ký tự mà không có ảnh) để tìm nhanh
  trang thưa trước khi soi.

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
- ⛔ **KHO MANUAL CHÍNH (bản Dr.Explain `.gui` + PDF từng phiên bản): `F:\File-Manual\`** — chủ máy chỉ
  12/10/2026 sau khi AI tìm sót và báo nhầm "không có manual 1kg". Mỗi máy một thư mục đánh số:
  `8-User-manual-1kg` (User-manual-01 v1.0.x VIE/ENG + `1kgEU_manual_*.gui`), `9-User-manual-3kg`,
  `13_User-manual-60kg`, `14_Assembly-guide-60kg`, `18_User_manual_120`, `19/22/23_Manual_destoner…`,
  `21_Afterburner`, `24_OTL_06_12`, `25_OTL0_30`, `26_OTL_30`, `28_OTL_03v2`, `30_OTL-120-0925`, `31_Silo`,
  `37_OTL_120_SIE`, `41_OTL-06-Installation`, `42_User_manual_silo_120_FR_Sang`, `44_Cyclone_clean_guide`…
  **Làm lại manual một cỡ máy: liệt kê `F:\File-Manual` TRƯỚC, lấy bản số phiên bản cao nhất làm nguồn.**
  Tìm toàn ổ thì nhớ gồm `F:\File-Manual`, đừng chỉ tìm trong `F:\Project`.
- **Kho manual CŨ (2022–2024, Word/PDF/AI):** `F:\Vat-tu-Otesla\22_User_manual\`.
  - `Manual\OTL_USER_MANUAL.docx` (05/2024) + `_03_ENG.docx` = manual máy thường **OTL-03 (3kg)** — khung
    chương dùng chung cho máy nhỏ; còn địa chỉ Bình Dương + email `otesla.vn@gmail.com` CŨ, đừng chép lại.
  - `Manual\` còn: `LẮP RÁP 1KG.pdf`, `lắp ráp 2kg.pdf` (bản vẽ lắp tách rời, không có thông số),
    `3kg roi.pdf`, `30KG BALAN.pdf`, `5kg-overview.ai`, `panel-eu-otesla*.ai` (panel EU máy nhỏ) và ảnh
    minh hoạ thao tác (cong-tac-nguon, bat-gas, mix-cool, gap-drum, ve-sinh-cyclone…).
  - `Auto\` + gốc thư mục: manual Auto 2022 (EN/VI) — đã thay bằng `122_Manual_AI\auto-en`.
  - Manual 1kg thật nằm ở `F:\File-Manual\8-User-manual-1kg` (xem dòng trên), KHÔNG ở đây.
- Bản chép đã gom: `112_Quanly\135_TaiLieu_Rang_VanHanh_AnToan\01_Huong-dan-su-dung-OTL\` (grep `_md\`).

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
