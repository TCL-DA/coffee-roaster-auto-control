# CS-01 — Mẻ AUTO đứng sát nhiệt xả, máy không tự DROP

**Mã case:** CS-01 · **Máy:** OTL-30 (30 kg, bếp gas NP, không vacuum, không cân loader) · **Nơi:** đại lý châu Âu
**Báo lỗi:** đầu 09/2026 (video của người dùng cuối) · **Sửa ở:** firmware v3.10.0 (10/09/2026), còn nguyên trong v3.14
**Tài liệu kỹ thuật:** [docs/plan/2026-09-10-auto-stall-cuoi-me.md](../plan/2026-09-10-auto-stall-cuoi-me.md)

> Dùng case này để **thử máy trước khi giao** và **thử lại sau mỗi lần sửa bộ bù gas / đọc hồ sơ**.
> Mục 5 là bài thử, làm được trên bàn thử (board + panel + mạch giả lập BT/ET), không cần lửa.

---

## 1. Khách báo gì

- Chạy **AUTO** theo hồ sơ mẫu: DEV khoảng 4 phút, FCs 199 °C → DROP 217,0 °C.
- Gần cuối mẻ, BT **đứng ở 216,5 °C**, RoR tụt xuống **~1 °C/phút**, gas hiện **0 %**.
- Máy **không bao giờ tự xả**. Thợ phải đứng chờ rồi xả tay.
- Lệch giữa BT và mục tiêu chỉ **0,2 °C**, nhưng bộ bù gas **không phản ứng gì**.
- Kèm theo: bồn làm nguội chạy sớm khoảng **1 °C trước khi xả**, dù thợ chỉ cài 0,1 °C.
- Người dùng cuối cố ý rang **RoR rất thấp ở cuối mẻ** (1–2 °C/phút). Đó là phong cách rang của họ,
  không bắt họ đổi hồ sơ được, nên phải sửa firmware.
- Mẻ xảy ra khi trời lạnh: nhiệt độ môi trường ~8 °C, trong khi mẻ mẫu ghi ở ~25 °C.
  Máy mất nhiệt nhiều hơn mẫu khoảng 9 %.

## 2. Vì sao máy không xả

Bốn lỗi **độc lập**, cho ra cùng một triệu chứng. Vá một lỗi rồi tưởng xong là lý do mẻ vẫn treo.

| # | Lỗi | Cơ chế | Dấu hiệu nhận ra tại máy |
|:--|:--|:--|:--|
| A | **Vùng mù của bộ bù gas** | Hết hồ sơ thì mục tiêu BT **chính là nhiệt xả**, sai lệch chỉ co lại. Bộ bù đòi lệch > 0,6 °C **liên tục 10 s** mới bù, nên trong 0,6 °C cuối nó **không bao giờ chạy**. Hồ sơ vuốt gas về 0 % thì gas nằm ở 0 %. | BT kẹt dưới nhiệt xả < 0,6 °C, gas = gas hồ sơ (thường 0–5 %), không có mã báo. |
| B | **Đuôi làm nguội trong file hồ sơ** | File `.csv` xuất từ Artisan ghi tiếp pha làm nguội sau DROP (gas 0 %, gió mở hết). Mẻ chạy chậm hơn mẫu là máy đọc lố sang đoạn đó: **cắt gas, mở hết gió** trong khi hạt còn đang rang. | Ô Gió (Thực) **nhảy lên tối đa** ngay sau giây xả của mẫu. File do máy tự ghi (SAVE) không dính lỗi này. |
| C | **Làm nguội sớm ×10** | Ô "bật làm nguội sớm" bị nhân 10: cài 0,1 °C nhưng máy chạy 1,0 °C. Bồn nguội hút nhiệt đúng đoạn cuối. | Quạt làm nguội bật khi BT còn cách nhiệt xả ~1 °C. |
| D | **Thời gian DEV không reset đầu mẻ** | Biến thời gian DEV giữ số của mẻ trước, làm sai nấc deadband và nhiệt xả động. | Mẻ thứ hai liên tiếp: DEV đếm không bắt đầu từ 0. |

Thêm một điểm: bước `STP_DEV` **không có điều kiện thoát** theo thời gian. BT không chạm nhiệt xả thì máy cứ
rang mãi. Đây là chủ ý: tự xả một mẻ chưa tới nhiệt là làm hỏng mẻ.

## 3. Đã sửa gì (v3.10.0, còn trong bản hiện tại)

| Sửa | Ở đâu | Tóm tắt |
|:--|:--|:--|
| **Chốt cứu đoạn cuối** (A) | `Program.h` `endBatchRescue()`, tham số `END_*` trong `Config.h` | Trong **2,0 °C cuối**, máy tính ETA = (số 0,1 °C còn thiếu) × (số giây giữa 2 lần BT nhích). ETA > **30 s** là bơm gas ngay, không chờ BT đứng hẳn. Gas nền < 10 % thì bơm **+10 %**, ngược lại **+5 %**. Giữ ≥ **10 s** rồi mới xét. Sau **35 s** mà vẫn chưa kịp thì cộng một bậc, trần **15 %**. Hết trần thì **chuông + mã 421**, **KHÔNG tự xả**. Lấy giá trị lớn hơn giữa chốt cứu và bộ bù thường, không cộng dồn. Mẻ đang nóng hơn mẫu thì chốt cứu đứng im. Mã 420 hiện khi đang bù. |
| **Chặn đọc lố hồ sơ** (B) | `sdProfileEndTi` (`Define.h`, `Program.h`) | Điểm cuối hồ sơ chốt tại **giây xả** (`rtDROP` / `DROP_PRO_S_R`), không phải dòng cuối file. |
| **Làm nguội sớm đúng số cài** (C) | `Modbus_Master.h` (`preCool_R_CV = preCool_R`) | Bám đúng số thợ cài. Mức tối thiểu 0,2 °C đặt ở ô nhập trên HMI. |
| **Reset thời gian DEV** (D) | khối khởi tạo mẻ, `Program.h` | Mỗi mẻ DEV bắt đầu từ 0. |
| **Siết deadband 3 nấc** | `CALIB_DEADBAND_*` | ±1,0 °C trước FCs → ±0,6 °C tới hết phút 2 của DEV → **±0,3 °C** từ phút 2. Bậc bù nhỏ nhất vẫn 5 % (sàn cứng của bếp NP). |
| **Nhiệt xả động** | `$M54` `dropTrim` (0,0–1,0 °C, 0 = tắt) | DEV đã quá 3 phút: mẻ trễ hơn mẫu > 15 s thì xả sớm hơn `dropTrim`, sớm hơn mẫu > 15 s thì xả muộn hơn. Giữ màu hạt khi mẻ lê. |

⚠ v3.10.0 chèn `dropTrim` vào `$M54`, **đẩy số 7 thanh ghi $M54–$M61**. Firmware và HMI phải nạp **thành cặp**.
Nạp lệch thì ô cũ `preheatHoldSettle` (10–30) rơi vào `preheatDeadline`, và preheat báo lỗi mọi mẻ.

## 4. Kết quả trên máy thật (10/09/2026)

- Chủ máy thử 2 mẻ RoR **3 và 4 °C/phút** ở pha phát triển: **cả hai tự xả, đạt**.
- Xấu nhất trễ **~33 s** so với giờ xả mẫu khi máy thiếu nhiệt nặng. Mục tiêu đặt ra là 30 s, nên kết quả sát biên.
- 33 s cho thấy **trễ nhiệt bếp → hạt của máy 30 kg khoảng 35–40 s**, cao hơn con số 30 s dùng lúc thiết kế.
  Muốn siết dưới 30 s thì phải chỉnh `END_ESCALATE` hoặc bước bơm đầu, không chỉnh bằng ngưỡng phát hiện.
- **Chưa ai đo trễ nhiệt thật của máy 30 kg.** Cách đo: máy nóng ổn định → tăng gas +10 % một lần →
  đếm số giây tới khi BT tăng tốc rõ. Ghi kết quả vào case này.

## 5. Bài thử để nghiệm thu máy

### Chuẩn bị

- Board + panel đúng **cặp** firmware/HMI sắp giao, chế độ **AUTO**, một hồ sơ có đủ mốc FCs và DROP
  (ví dụ FCs 199,0 °C, DROP 217,0 °C).
- Mạch giả lập BT/ET (ESP32, COM3, 9600 baud, DTR/RTS tắt; lệnh `B<x10>\nE<x10>\n`).
  Mở COM3 có thể làm board báo 403, nên báo người đứng máy trước.
- Bàn thử không có lửa: theo dõi **Gas (Thực)**, **mã trạng thái** và **cửa trống**, không cần lửa thật.
  Mẹo bỏ chờ nguội: đặt nhiệt nạp `$M23 = 0` **sau khi** hồ sơ đã nạp (nạp hồ sơ sẽ ghi đè `$M23`).
- Script mẫu đẩy đường BT: `c11_me_gia_lap_o1.py` trong thư mục soát bàn thử 21/10/2026
  (nội suy BT/ET theo bảng điểm, có chốt huỷ khi relay gas bật).

### Các ca thử

| Ca | Làm gì | Đạt khi |
|:--|:--|:--|
| T1 · Đứng sát xả | Chạy theo hồ sơ tới DEV, rồi **giữ BT cố định 216,5 °C** (cách xả 0,5 °C). | Trong vài giây hiện **mã 420**, Gas (Thực) = gas hồ sơ **+10 %** (gas nền < 10 %) hoặc **+5 %**. |
| T2 · Leo thang | Tiếp T1, BT vẫn đứng. | Cứ mỗi **35 s** cộng thêm một bậc, **không vượt +15 %**. Hết trần thì **chuông + mã 421**. **Cửa trống KHÔNG mở.** |
| T3 · Bù có tác dụng | Lặp T1, sau khi có 420 thì cho BT nhích **+0,1 °C mỗi ≤ 5 s**. | Mức gas **giữ nguyên**, không leo thang. BT chạm 217,0 °C thì **máy tự xả**. |
| T4 · Mẻ đang nóng | Đẩy BT **cao hơn** đường mẫu > 0,6 °C trong 2 °C cuối. | Chốt cứu **không** bơm (không có 420), gas không tăng. |
| T5 · Hồ sơ có đuôi làm nguội | Nạp file `.csv` từ Artisan còn 60 s làm nguội sau DROP (gas 0, gió 100). Cho mẻ chạy **chậm hơn mẫu** 30 s. | Qua giây xả của mẫu, **Gió (Thực) KHÔNG nhảy lên tối đa**, gas **không về 0**. |
| T6 · Làm nguội sớm | Cài làm nguội sớm **0,2 °C**. | Quạt làm nguội bật khi BT ≥ nhiệt xả − 0,2 °C, **không** phải − 2,0 °C. |
| T7 · Hai mẻ liên tiếp | Chạy hai mẻ AUTO liền nhau. | Mẻ thứ hai: thời gian DEV bắt đầu từ **0**. |
| T8 · Nhiệt xả động | `$M54 = 5` (0,5 °C). Mẻ trễ hơn mẫu > 15 s, DEV > 3 phút. | Máy xả ở **216,5 °C**. Đặt `$M54 = 0` thì xả đúng 217,0 °C. |
| T9 · Không bắt được FCs | Hồ sơ hoặc mẻ **không qua mốc FCs** (FCs = 0 hoặc BT không chạm `$M21`). Giữ BT 216,5 °C. | **Ghi lại máy làm gì.** Chốt cứu chỉ mở khi đang ở `STP_DEV`. Nếu không có 420/421 thì máy treo như lỗi gốc, phải báo lại. |

**Tiêu chí chủ máy chốt:** bơm 5 %, giữ ≥ 10 s, BT nhích ≥ 0,1 °C là đạt. Trên máy thật: trễ so với giờ xả mẫu ≤ ~35 s.

### Ghi kết quả

Mỗi lần thử ghi: ngày, bản firmware + HMI, ca đạt/không đạt, ảnh màn rang lúc có 420/421, nhật ký rang
(Bảng số) quanh giây xả. Ca không đạt thì mở issue, gắn mã **CS-01**.

## 6. Bài học

- **Một triệu chứng, nhiều nguyên nhân.** "Không xả" ở đây là 4 lỗi chồng nhau. Sửa xong phải chạy **đủ** các ca
  ở mục 5, không chỉ ca đã thấy trong video.
- **Bộ bù có deadband thì luôn có vùng mù sát đích.** Mọi bộ điều khiển bám mục tiêu cố định đều phải có lối
  thoát riêng ở đoạn cuối.
- **Không tự xả mẻ chưa tới nhiệt.** Hết cách thì báo thợ (421 + chuông), để thợ quyết.
- **File hồ sơ nhập từ ngoài phải chặn tại DROP.** Đừng tin dòng cuối file.
- **Thử ở điều kiện xấu:** trời lạnh, hồ sơ RoR thấp, gas cuối mẻ về 0–5 %. Mẻ mẫu ghi ở ngày ấm sẽ không lộ lỗi này.
