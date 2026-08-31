# Quản lý phiên bản tài liệu

Tài liệu đã giao cho khách thì **không được sửa đè lặng lẽ**. Mỗi lần sửa phải để lại dấu vết,
vì khách và thợ ngoài xưởng đang cầm bản in cũ trong tay.

## Đánh số phiên bản

Dạng `X.Y` — ví dụ `1.0`, `1.1`, `2.0`.

| Loại thay đổi | Tăng số | Ví dụ |
|---------------|---------|-------|
| Sửa lỗi chính tả, đổi ảnh cho nét, sửa thông tin liên hệ | **Y** (1.0 → 1.1) | đổi email công ty |
| Thêm/bớt bước vận hành, đổi thông số, thêm chương, sửa nội dung an toàn | **X** (1.1 → 2.0) | firmware đổi thời gian mồi lửa |

Bản đầu tiên giao khách là `1.0`. Bản nháp chưa giao thì cứ giữ `1.0` và sửa thoải mái —
chỉ bắt đầu tăng số **sau khi đã gửi khách hoặc đã in**.

## Ba chỗ phải khớp nhau

Sửa phiên bản là phải sửa đủ cả ba, nếu không tài liệu tự mâu thuẫn:

1. Dòng chân trang bìa — tham số cuối của `COVER(...)`: `"Phiên bản 1.1 – 09/2026 …"`
2. Dòng `["Phiên bản", "1.1 – 09/2026"]` trong `COMPANY(...)`
3. Bảng lịch sử trong `LICH-SU-PHIEN-BAN.md` của thư mục tài liệu

## Lịch sử phiên bản

Mỗi thư mục tài liệu có một file `LICH-SU-PHIEN-BAN.md`. Ghi **ngay khi dựng lại**, đừng để
dồn. Mẫu:

```markdown
# Lịch sử phiên bản — <tên tài liệu>

| Phiên bản | Ngày | Thay đổi | Người yêu cầu |
|-----------|------|----------|---------------|
| 1.1 | 2026-09-02 | Đổi email công ty sang otlpro.com@gmail.com | chủ máy |
| 1.0 | 2026-08-20 | Bản đầu tiên: 17 trang, VI + EN | — |
```

## Lưu bản đã giao

Bản nào đã gửi khách hoặc đã in thì chép vào thư mục `phat-hanh\` kèm số phiên bản trong tên
file, và **không bao giờ ghi đè lên nó**:

```
preheat-vi\
  Huong-dan-Lam-nong-may-VI.pdf          ← bản hiện hành, dựng lại là ghi đè
  Preheat-Warm-up-Manual-EN.pdf
  phat-hanh\
    Huong-dan-Lam-nong-may-VI_v1.0.pdf   ← bản đã giao, giữ nguyên vĩnh viễn
    Preheat-Warm-up-Manual-EN_v1.0.pdf
```

Lệnh chép sau khi dựng xong một phiên bản mới:

```bash
V=1.1
cp Huong-dan-Lam-nong-may-VI.pdf   "phat-hanh/Huong-dan-Lam-nong-may-VI_v$V.pdf"
cp Preheat-Warm-up-Manual-EN.pdf   "phat-hanh/Preheat-Warm-up-Manual-EN_v$V.pdf"
```

## Bản nhiều thứ tiếng

VI và EN là **cùng một phiên bản**, luôn dựng lại cả hai cùng lúc. Sửa một bên mà quên bên kia
là lỗi nặng nhất của tài liệu song ngữ — khách nước ngoài và thợ trong xưởng sẽ làm theo hai
hướng dẫn khác nhau.

Kiểm tra nhanh sau khi dựng:

```bash
python -c "import fitz
a=fitz.open('ban-VI.pdf'); b=fitz.open('ban-EN.pdf')
print('so trang:', a.page_count, b.page_count)   # phải bằng nhau
for d in (a,b): print([l for l in d[1].get_text().split(chr(10)) if 'gmail' in l or '198' in l])"
```

## Việc phải làm mỗi lần sửa tài liệu đã giao

1. Hỏi chủ máy: sửa này có cần tăng phiên bản không (bản đã in ngoài xưởng chưa?).
2. Sửa nội dung trong `content.jsx` **và** `content-en.jsx`.
3. Cập nhật số phiên bản ở cả ba chỗ nêu trên.
4. Dựng lại cả hai ngôn ngữ, render PNG soi lại trang bìa + trang công ty.
5. Ghi một dòng vào `LICH-SU-PHIEN-BAN.md`.
6. Chép bản mới vào `phat-hanh\` kèm số phiên bản.
