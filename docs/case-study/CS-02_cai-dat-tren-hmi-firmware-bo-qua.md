# CS-02 — Cài đặt có trên HMI mà firmware bỏ qua, hoặc firmware đọc mà HMI không có ô

**Mã case:** CS-02 · **Dòng máy:** OTL-30 HMI v28 (DOP-110WS) · **Phát hiện:** 21/10/2026, chủ máy soát panel bàn thử
**Sửa ở:** firmware env `genericSTM32F103RC` (cờ `MACHINE_HAS_AUTO_ESCAPE_SWITCH=1`) + HMI v28 **LO111** (trang Cài đặt mới, màn 39)

> Bài học của case: **firmware và HMI phải khớp từng ô cài đặt.** Một ô có trên màn mà firmware không nghe, hoặc firmware đọc
> mà màn không có ô, đều **không báo lỗi gì** — máy vẫn chạy, chỉ là chạy khác điều thợ tưởng.

---

## 1. Chủ máy hỏi gì

- *"Trên bản HMI đã nạp lên máy, tôi kiếm không ra cái giá trị cài đặt đó"* — ô **tự mở cửa xả** (`$M53`, làm cho máy 30 kg
  ngày 08/09, v3.9.0).
- *"Cài đặt `$M53` để cài bù nhiệt Agtron nữa, mới nhất không có à"* — ô **bù nhiệt xả theo thời gian** (`$M54` `dropTrim`,
  giữ màu Agtron khi mẻ lê, v3.10.0 — xem [CS-01](CS-01_auto-dung-sat-nhiet-xa-khong-drop.md)).

## 2. Soát ra gì (HMI LO110 + firmware 13b73e9)

Đối chiếu bảng `$M` firmware đọc (`include/Define.h`, `*_W`) với mọi ô trên HMI (`dpa_addresses`):

| `$M` | Thông số | HMI LO110 | Firmware | Hậu quả |
|:--|:--|:--|:--|:--|
| 53 | Chế độ xả khay (tự mở cửa xả khay sau làm nguội) | **có** — Cài đặt › Hệ thống, tên "Chế độ xả khay" | **bỏ qua** (build cờ = 0) | Gạt TẮT trên màn mà máy **vẫn tự xả khay** — công tắc đánh lừa thợ |
| 54 | Bù nhiệt xả theo thời gian (Agtron) | **không có** | đọc 0 = TẮT | Chức năng v3.10.0 **mất hẳn** trên dòng HMI v28 |
| 55–57 | Hạn / thời gian ổn định / dải giữ nhiệt làm nóng | không có | đọc 0 → số mặc định | Chạy an toàn, thợ không chỉnh được |
| 58 | Ngưỡng cảnh báo DEV | không có | 0 → 30 % | như trên |
| 59 | Khoá tự xả sau nạp | không có | 0 → 120 s | như trên |
| 60 | Cửa xả khay mở tay thêm | không có | **0 = không cộng thêm** | Cửa mở tay đóng ngay sau thời gian xả, không +15 s |
| 61 | Chờ cửa trống đóng | không có | 0 → 60 s | như trên |

Vì sao lọt: ô `$M53` có từ HMI đời CMS 110CS (v3.9.0); HMI v28 chép sang nhưng cờ build để mặc định 0 (dành cho HMI cũ chưa
có ô). `$M54`–`$M61` thêm vào firmware v3.10.0 (đẩy số `$M54`→`$M61`) chỉ kèm HMI 110CS của khách; dòng v28 dựng sau không
ai thêm ô.

## 3. Đã sửa

**Firmware** — `platformio.ini`: env `genericSTM32F103RC` (đi cặp HMI v28) build `-DMACHINE_HAS_AUTO_ESCAPE_SWITCH=1`.
Env `dien`, `may3kg` khai `build_flags` riêng nên vẫn = 0 (HMI của chúng chưa kiểm).

**HMI v28 LO111** (`113_HMI/_script/ui_trang_rang_tu_dong.py`, bước dựng Z68):

- Trang mới **Cài đặt · Rang tự động, an toàn** (màn 39), nằm trong chuỗi Trước / Sau: 5 → 24 → 25 → **39** → 5.
  8 thẻ `$M54`–`$M61`, cùng kiểu thẻ / khoá quyền dịch vụ với các trang cài đặt khác, đủ 14 ngôn ngữ.
- **Mặc định lần đầu** (Lua `macDinhM`, cờ `$M1541 = 111`): ô nào đang 0 thì đặt — `$M53 = 1` (tự xả khay như cũ — nếu
  không, bật cờ firmware xong máy đang để 0 sẽ **ngừng xả khay**), `$M54 = 5` (0,5 °C, mức đã gợi ý khách 10/09),
  `$M55`–`$M61` = số mặc định của firmware (`$M60 = 15 s`). Chỉ chạy một lần — thợ đổi sau đó thì giữ nguyên.

| Thẻ | `$M` | Dải | Mặc định |
|:--|:--|:--|--:|
| Bù nhiệt xả theo thời gian (°C) | 54 | 0,0 … 1,0 °C | 0,5 |
| Khoá tự xả sau khi nạp (s) | 59 | 0 … 600 s | 120 |
| Ngưỡng cảnh báo phát triển (%) | 58 | 0,0 … 50,0 % | 30,0 |
| Hạn đạt nhiệt làm nóng (s) | 55 | 0 … 900 s | 180 |
| Thời gian ổn định làm nóng (s) | 56 | 0 … 300 s | 45 |
| Dải giữ nhiệt làm nóng (°C) | 57 | 0,0 … 10,0 °C | 3,0 |
| Cửa xả khay mở tay thêm (s) | 60 | 0 … 120 s | 15 |
| Chờ cửa trống đóng (s) | 61 | 0 … 300 s | 60 |

## 4. Bài thử (bàn thử: board + panel thật, tải đã ngắt, công tắc lửa CH1 bật)

21/10/2026 19:36–20:11, firmware env `genericSTM32F103RC` cờ `$M53` = 1 + HMI LO111. Hồ sơ mẫu ghi ở mẻ 1 (FCs 199 @ ~4:50,
xả 216,7 °C @ 8:41, DEV ~3:50). Làm nguội tạm 20 s cho nhanh (trả lại 240 s sau thử).

| Mẻ | Cài đặt | Kỳ vọng | Đo | Kết quả |
|:--|:--|:--|:--|:--|
| 1 · rang tay | xả khay `$M53 = 1` | làm nguội xong khay **tự mở**, tự đóng sau 55 s | khay mở ngay sau 20 s làm nguội, đóng sau ~55 s | ✅ |
| 2 · AUTO, chậm hơn mẫu 12 % | bù Agtron `$M54 = 0,5 °C`, xả khay `$M53 = 0` | tự xả ở **216,7 − 0,5 = 216,2 °C**; khay **không** tự mở; mở tay tự đóng sau 55 + 15 s | tự xả lúc 9:32 ở **216,2 °C**; khay không mở; mở tay đóng sau **69,1 s** | ✅ |
| 3 · AUTO đối chứng | `$M54 = 0` | tự xả đúng nhiệt hồ sơ **216,7 °C** | tự xả lúc 9:38 ở **216,7 °C** | ✅ |

Kèm theo: mã **416** (cảnh báo DEV) lên đúng một lần mỗi mẻ khi DEV vượt 30 % (`$M58 = 300`), máy không tự xả vì nó.
Mặc định lần đầu sau khi nạp LO111: `$M53..$M61` = 1, 5, 180, 45, 30, 300, 120, 15, 60 (đọc qua Modbus TCP).

**Thử lại khi nạp máy khách:** chạy đúng 3 mẻ trên (kịch bản `c13_thu_lo111.py` của bàn thử: mạch giả lập BT/ET, không lửa).

## 5. Việc soát cho mọi bản sau

1. Đối chiếu **toàn bộ** `$M` firmware đọc với ô HMI trước khi phát hành (`dpa_addresses` filter `$M` ↔ `grep _W include/Define.h`).
   Ô firmware đọc mà HMI không có → hoặc thêm ô, hoặc ghi rõ "dùng mặc định" trong ghi chú phát hành.
2. Mọi cờ build `MACHINE_HAS_*` liên quan tới **ô trên HMI** phải khớp với bản HMI đi cặp — ghi trong `platformio.ini` cạnh env.
3. Bật một ô firmware mới nghe mà giá trị 0 nghĩa là "tắt / dừng" → HMI phải đặt **mặc định lần đầu**, không thì máy đổi
   hành vi im lặng ngay khi nạp.
