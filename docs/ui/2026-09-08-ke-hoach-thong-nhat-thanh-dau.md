# KẾ HOẠCH — thống nhất THANH ĐẦU giữa màn Rang và 5 tab còn lại

Trạng thái: **CHƯA VÁ.** Chủ máy dặn "từ từ hãy vá" — bản này chỉ chẩn đoán và
đề xuất, chờ chốt hướng rồi mới đụng vào mã.

Nguồn thiết kế: Claude Design, project `Menu cài đặt nhanh - Lỗi thiết kế`,
file `Rang - Sửa lại.dc.html`. **Đã kéo bản mới nhất về đối chiếu ngày 08/09:
md5 `bd3a10d0…` — trùng khít với mirror `docs/ui/design-web/`, tức thiết kế không
đổi gì từ 07/09.** Mọi con số dưới đây quy về hệ toạ độ app (×1,333 vì khung
thiết kế 1920 còn sân khấu app 2560).

## Hiện tượng chủ máy thấy

Đổi qua lại giữa màn Rang và các tab khác thì cả thanh đầu **nhảy và đổi dáng**:
logo đổi, chữ tab đổi cỡ, cụm tab lúc có khung lúc không, nội dung bên dưới xê dịch.

## Đo được

| | Màn Rang | 5 tab còn lại | Thiết kế |
|---|---|---|---|
| Cao thanh đầu | 75 px màn (=100 sân khấu) | 83 px màn (=111) | **74 (=98,7)** |
| Cụm tab | không khung, trong suốt | khung `--inset`, bo 20px | **không khung** |
| Cỡ chữ tab | 26 | 24 | **20 (=26,7)** |
| Logo | ẩn logo chuẩn, vẽ chữ "R" bằng `:before` | logo 47×38 | **ô 26×26 nền `#D93A32` chữ "R"** |
| Đồng hồ | 24 | 32 | **18 (=24) — IBM Plex Mono** |
| Chip kết nối | 157×45 | 179×53 | pill 7×12, chữ 16 (=21) |
| Nội dung bắt đầu | y=75 | y=83 | — |

**Kết luận ngược với trực giác: MÀN RANG MỚI LÀ ĐÚNG THIẾT KẾ.** Năm tab còn lại
đang dùng thanh đầu đời cũ, có từ trước đợt áp bản thiết kế. Màn Rang đã được
dựng lại theo thiết kế ngày 07/09, nhưng thanh đầu dùng chung thì chưa ai kéo theo.

## Nguyên nhân trong mã

**16 luật CSS** tồn tại chỉ để dựng "thanh đầu thứ hai" khi màn Rang đang mở —
`html:has(#pane-rang.on) …` ở các dòng 2105–2121, 2212–2215, 2276. Chúng ẩn logo
chuẩn rồi vẽ lại một logo khác bằng `:before`, đổi cỡ đồng hồ, thu chip kết nối,
gỡ khung cụm tab, và **tắt luôn viên thuốc trượt** (`#tabnav:before{display:none}`).

Nói cách khác: app đang **nuôi hai thanh đầu** và đổi qua lại theo tab đang mở.

## Ba hướng

### A · Kéo 5 tab kia về đúng thiết kế (ĐỀ XUẤT)

Bỏ 16 luật riêng cho màn Rang, đưa thanh đầu chuẩn về đúng thông số thiết kế, rồi
mọi tab dùng chung một thanh.

- **Được:** hết nhảy, hết đổi cỡ chữ, xoá 16 luật đặc biệt, và 5 màn về đúng
  thiết kế. Về sau thêm tab mới không phải nhớ "màn Rang thì khác".
- **Mất:** dáng thanh đầu của 5 màn đổi thấy rõ — mất khung bo tròn quanh cụm tab,
  logo nhỏ lại, đồng hồ nhỏ lại. Chủ máy đã quen mắt với dáng cũ.
- **Rủi ro:** vừa phải. Có bộ kiểm giữ, nhưng là thay đổi nhìn thấy được.

### B · Chỉ bỏ CÚ NHẢY, giữ hai dáng

Ghim cao thanh đầu và cỡ chữ tab về một giá trị; vẫn cho màn Rang bỏ khung cụm tab.

- **Được:** hết nhảy 8px và hết đổi cỡ chữ — đúng hai thứ khó chịu nhất. Ít rủi ro.
- **Mất:** vẫn còn hai dáng logo/đồng hồ khác nhau; vẫn còn 16 luật riêng.

### C · Kéo màn Rang về giống 5 tab kia

- **Không đề xuất:** đi ngược thiết kế, và ngược yêu cầu "thu gọn nav" của chính
  chủ máy hôm 07/09.

## Nếu chọn A — thứ tự làm

1. Sao lưu `docs/ui/backup/OTL Roast Lab.pre-header-unify.html`.
2. Sửa **thanh đầu chuẩn** cho khớp thiết kế: cao 98,7; logo ô 34,7 nền `#D93A32`
   chữ "R"; tên "Roast Lab" 25,3; tab là chip rời `padding 21,3×26,7` bo 13,3 chữ
   26,7, cách nhau 5,3, **không khung bọc**; đồng hồ 24 **IBM Plex Mono**; chip kết
   nối pill; nút tài khoản cao 74,7 avatar 45,3.
3. Giữ **viên thuốc trượt** `#tabnav:before` cho mọi tab — thiết kế vẽ nền riêng
   cho từng tab, viên thuốc trượt là bản có chuyển động của đúng ý đó, và cử chỉ
   kéo (đã làm 08/09) cần nó.
4. Xoá 16 luật `html:has(#pane-rang.on)` về thanh đầu. Giữ các luật khác của màn Rang.
5. Đo lại: cao thanh đầu và cỡ chữ tab **bằng nhau ở cả 6 tab**; `test_ui_motion_sync`
   phải hết mục M5; chạy đủ 22 bộ kiểm.
6. Chụp 12 màn đối chiếu trước/sau.

Ước tính: một buổi, phần lớn là đo lại và chụp đối chiếu.

## Việc đã làm rồi trong lúc dò (không nằm trong kế hoạch này)

- **Vá lỗi hiển thị "chưa có dữ liệu"**: dấu `—` ở ô BT bị vẽ ở cỡ 112px màu cam,
  ra một **khối đặc 63×97 px** — nhìn như thanh mức hỏng. Nay thu về 34px và dùng
  mực chữ phụ. Sửa ở hàm `txt()` nên ăn cho cả 74 chỗ.
- **Thêm cử chỉ kéo viên thuốc** cho cả 6 cụm nút chọn (xem mục dưới).

## Ghi chú cho người làm tiếp

Đừng sửa `MILE_STEP` hay bản đồ progStep để "cho gọn" — nó bám firmware.
Và đừng đem `--faint` làm màu chữ: đó là màu nét mảnh, chỉ được 1,7–2,2:1.
