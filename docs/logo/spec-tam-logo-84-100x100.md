# Tấm logo +84 — 100×100 mm gắn máy rang

File artwork: `112_Quanly	9_sample_100x100\` (bản chính thức).
Bản nháp 3D kèm theo nằm trong `112_QuanlyQ_Inventor_3D\_luu_tru\CAD_tu_repo_firmware_260826.zip`.

## ⚠️ Nguồn artwork

Dấu hiệu +84 trong bộ file này là **bản vector dựng lại từ ảnh raster**, chưa
đối chiếu với file gốc của thương hiệu. Trước khi đặt sản xuất hàng loạt phải
xin file vector gốc (.ai/.eps/.svg) và thay vào.

Lưu ý: `Phepro_100x100.pdf` (F:\File-AI\172_Logo_MrY) là logo **Phê Pro** —
thương hiệu khác, không liên quan tới dấu +84.

## Quy ước đọc file

| Trong file | Trên tấm thật |
|---|---|
| Vùng màu `#262223` | Có mực / có khắc |
| Vùng màu trắng `#FFFFFF` | **KHÔNG in — để lộ inox trần** |

Xưởng in tuyệt đối không được hiểu vùng trắng là "in mực trắng".

## Ba mẫu

| Mẫu | File | Mô tả |
|---|---|---|
| A | `UV-inox_logo84_A_in-duong-ban` | Inox trần làm nền, chỉ in dấu hiệu rộng 78 mm. Ít mực nhất → bền nhất. |
| B | `UV-inox_logo84_B_in-nen-logo-inox` | In kín nền than chì (bo góc R6, lùi mép 4 mm), dấu hiệu 58 mm để lộ inox ánh kim. Có 4 lỗ bắt vít. |
| C | `UV-inox_logo84_C_huy-hieu-tron` | Đĩa mực Ø92 trên tấm Ø100, vành chỉ 0,8 mm + dấu hiệu 50 mm lộ inox. |

Bộ `logo84_*` (không có tiền tố `UV-inox_`) là bản cũ dành cho khắc laser,
mực tràn sát mép — chỉ dùng khi chọn phương án khắc.

## Vật liệu & gia công

- Inox 304, bề mặt xước hairline, dày 1,0–1,5 mm.
- Khổ tấm: mẫu A/B 100×100 mm, mẫu C Ø100 mm.
- Mực: **1 màu** than chì `#262223` (≈ CMYK 0/10/8/85). Đây là màu tối, in
  thẳng lên inox không cần lót trắng — ánh kim xuyên qua nhẹ, nhìn sang.
- Lùi mép 4 mm: mực không chạy ra cạnh tấm, tránh bong mép khi va chạm.

### Lỗ bắt vít (chỉ mẫu B)

- Ø4,5 mm, tâm tại (12,12) · (88,12) · (12,88) · (88,88) tính từ góc.
- **Khoan trước, in sau.** Quanh mỗi lỗ chừa quầng không mực Ø6,5 mm để dung
  sai canh in không làm mực lem vào mép lỗ.

## ⚠️ Giới hạn nhiệt — chọn đúng chỗ gắn

Mực in UV chỉ chịu được khoảng **80 °C liên tục**. Quá ngưỡng sẽ ngả vàng,
giòn rồi bong.

| Vị trí gắn | Nhiệt | Phương án |
|---|---|---|
| Tủ điện, vỏ ngoài, chân máy | < 60 °C | ✅ In UV — dùng bộ `UV-inox_*` |
| Mặt che, ốp hông cách buồng rang | 60–80 °C | ⚠️ In UV được nhưng nên dán bằng vít, không dùng keo |
| Thân buồng rang, mặt trống, gần ống khói | > 100 °C | ❌ Không in UV. Chuyển sang **khắc laser** hoặc **ăn mòn hoá học** — dùng bộ `logo84_*` |

## Cách lắp

- Dán: 3M VHB 5952, chỉ khi bề mặt < 80 °C. Lau cồn IPA trước khi dán.
- Bắt vít: vít M4 đầu trụ inox, đệm vênh. Nên đệm silicon 0,5 mm sau tấm để
  chống rung và tránh ăn mòn tiếp xúc khác kim loại.
