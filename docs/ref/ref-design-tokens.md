# Design Token — OTL Roast Lab (HMI Touch)

> Chuẩn hóa 2026-07-23. Nguồn: khối `:root` đầu file `OTL Roast Lab.html`.
> Luật chung: **sửa UI phải chọn từ thang token, không chế số mới.**

## Trước / sau

| Hạng mục | Trước | Sau |
|---|---|---|
| Cỡ chữ | 32 giá trị (13→150px) | 20 bậc `--fs-*` |
| Bo góc | 16 giá trị | 6 token `--r-*` |
| Màu trạng thái | 4 đỏ, 3 xanh lá, 5 cam lẫn lộn | `--ok` / `--warn` / `--danger` / `--amber-ink` |

## Màu trạng thái (semantic)

| Token | Giá trị | Nghĩa |
|---|---|---|
| `--ok` | `#0f9d6b` | kết nối OK, hoàn tất, thiết bị bật |
| `--warn` | `#d98a1a` | đang kết nối, preheat đang chạy, chờ |
| `--danger` | `#e11d2f` | lỗi, mất kết nối, nút xóa, STOP |
| `--amber-ink` | `#b8860b` | mực amber đọc được: giá trị gas, mốc preheat, độ lệch |
| `--tip-bg` | `#0f1620` | nền tooltip |

Alias cũ vẫn chạy (đừng dùng cho code mới): `--c-ok→--ok`, `--c-warn→--danger`, `--c-try→--warn`.

Màu **dữ liệu chart** giữ riêng, không gộp vào trạng thái: `--c-bt --c-et --c-abt --c-burner --c-ror --c-gas` (JS canvas đọc qua `css('--c-…')`).

## Thang cỡ chữ `--fs-*` (nền stage 2560×1440)

`14 16 18 20 22 24 26 28 30 32 36 40 44 48 52 56 72 80 100 150`

Vai trò gợi ý: 14–16 nhãn phụ/caption · 18–22 chữ UI, nút · 24–28 tiêu đề khối ·
30–40 tiêu đề lớn, đồng hồ · 44–56 số liệu to · 72–150 số nhiệt hero.

## Thang bo góc `--r-*`

| Token | px | Dùng cho |
|---|---|---|
| `--r-xs` | 4 | tick, thanh nhỏ |
| `--r-sm` | 10 | chip, badge, input nhỏ |
| `--r-md` | 15 | nút, ô nhập, chip lớn |
| `--r-lg` | 20 | card con, panel nhỏ |
| `--r-xl` | 26 | card lớn, modal |
| `--r-2xl` | 32 | khối hero |

## Chưa chuẩn hóa (chủ đích)

- **Spacing** (padding/gap): stage cố định 2560×1440, đổi hàng loạt dễ vỡ layout — để nguyên.
- `#fff`/`#000` trong `color-mix()` và chữ trên nền accent — nghĩa nhất quán, giữ.
- Palette accent (`data-accent`), bánh xe màu, theme sáng/tối — là *định nghĩa*, không phải giá trị lạc.

## Ghi chú kỹ thuật

- Script chuyển đổi 1 lần: `tools/tokenize_css.py` (đã chạy, giữ lại làm tư liệu).
- Backup trước chuyển đổi: `Temp/OTL Roast Lab.pre-token.bak.html`.
- Gập cỡ chữ lệch tối đa 2px **xuống** → không gây tràn chữ trong ô cố định.
- Nút STOP preheat đổi gradient đỏ → màu đặc `--danger` (theo luật màu đặc 2026-07-22).
- Sửa HTML xong nhớ build lại exe (`dist/OTL Roast Lab HMI.exe` đang là bản cũ).
