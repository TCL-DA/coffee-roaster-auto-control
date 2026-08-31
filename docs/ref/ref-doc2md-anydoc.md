# anydoc + `tools/doc2md.py` — chuyển tài liệu sang Markdown để tra cứu

Nguồn: <https://github.com/firecrawl/anydoc> (Rust, MIT). Cài 2026-08-28.

## Nó làm gì

Chuyển **PDF, Word, Excel, PowerPoint, OpenDocument, RTF, EPUB, CSV** sang GitHub-Flavored
Markdown — bảng ra bảng, tiêu đề ra tiêu đề, công thức ra LaTeX. Thuần offline, không gọi mạng
(trừ khi bật OCR). Tốc độ đo thực tế: datasheet Schneider 2 trang ≈ **0,23 s**; 38 tài liệu
trong `Manuals/` (có 2 manual gần 1000 trang) hết **159 s**.

Tiếng Việt có dấu ra **đúng**, kể cả PDF xuất từ Illustrator.

## Cài

```bash
npm install -g @firecrawl/anydoc     # đã cài sẵn trên máy này
```

Bản Python (`pip install firecrawl-anydoc`) và Rust (`cargo add anydoc`) cũng có, nếu sau này
muốn nhúng thẳng vào script thay vì gọi CLI.

## Dùng nhanh 1 file

```bash
anydoc datasheet.pdf                 # in ra màn hình
anydoc bao-gia.xlsx -o bao-gia.md
```

## Dùng hàng loạt — `tools/doc2md.py`

```bash
# Chuyển cả thư mục, kết quả vào <thư mục>/_md/ + INDEX.md
python tools/doc2md.py "F:/Project/112_Quanly/Manuals"

# Chỉ định thư mục đích, gửi PDF scan lên OCR của Firecrawl
python tools/doc2md.py "F:/Project/112_Quanly" -o "F:/Project/112_Quanly/_md" --ocr hosted

# Làm lại từ đầu
python tools/doc2md.py "<thư mục>" --force
```

Đặc điểm:

- Quét đệ quy, soi gương cây thư mục nguồn sang thư mục đích.
- **Tăng dần**: file nào đã có `.md` mới hơn nguồn thì bỏ qua → chạy lại rất nhanh.
- Bỏ qua file khoá Excel `~$...` và các thư mục `_md`, `.git`, `node_modules`.
- Sinh `INDEX.md`: danh sách file + kích thước + mục "Cần OCR" + mục "Lỗi chuyển".

## Đã áp dụng ở đâu

| Thư mục | Kết quả |
|---|---|
| `112_Quanly/Manuals/` | 35/38 file → `Manuals/_md/` (1,9 MB Markdown), 3 file cần OCR |

Tra thông số vật tư thì `grep` trong `_md/` trước, nhanh hơn mở PDF rất nhiều:

```bash
grep -ri "adjustment range" /f/Project/112_Quanly/Manuals/_md/
```

## Bẫy đã gặp

1. **Cả file bị từ chối chỉ vì vài trang scan.** Manual Delta VFD-MS300 dài 688 trang bị chặn
   vì đúng 3 trang (5, 7–8) là ảnh quét; Weidmüller UR20 978 trang bị chặn vì 3 trang.
   anydoc thoát mã 3 và **không xuất gì cả**, không có chế độ "bỏ qua trang scan".
2. **OCR hosted giới hạn 50 MB.** `--ocr hosted` với manual MS300 báo
   `Uploaded file exceeds maximum size of 50MB`. File lớn phải tách trang trước.
3. `--ocr hosted` gửi tài liệu **lên server Firecrawl**. Không dùng cho bản vẽ/báo giá của khách.
4. Excel ra một bảng Markdown phẳng theo sheet — công thức thành giá trị, merge cell thành ô
   trống. Đọc thì tốt, **không dùng để ghi ngược lại Excel**.
5. PDF nhiều cột (catalogue) đôi khi trộn dòng của 2 cột. Số nào quan trọng thì đối chiếu PDF gốc.

## Mã thoát của anydoc

| Mã | Nghĩa |
|---|---|
| 0 | Xong |
| 1 | Không đọc/chuyển được |
| 2 | Sai cú pháp lệnh |
| 3 | PDF cần OCR |
