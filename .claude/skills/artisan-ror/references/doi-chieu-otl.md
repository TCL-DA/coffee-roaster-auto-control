# Đối chiếu RoR: Artisan ↔ firmware OTL ↔ app

Nguồn phía mình: `include/Program.h:107-118` (firmware), `tools/roast_derive.py` (bản Python cho app),
`protocol/pc_link.json` mục `derive` (tham số dùng chung). Phía Artisan: xem
[ror-thuat-toan.md](ror-thuat-toan.md).

## 1. Công thức của mình

Firmware — `Program.h:108-118`, chạy **mỗi 3 giây** (`rorCount == 3`):

```cpp
raw_rorBT = (Temperature_BT - rorBTSamp_1) * 20;   // Temperature_BT là ×10
rorBT = rorBTKalmanFilter.updateEstimate(raw_rorBT);
if(rorBT > 950) rorBT = 950;                        // trần 95.0 °C/phút
```

`tools/roast_derive.py` là **bản Python y hệt** (kể cả lớp `Kalman` sao theo
`SimpleKalmanFilter` của firmware), dùng khi máy chạy khối tương thích không đẩy RoR ra.

Thang đo: `Temperature_BT` ×10, nhân 20 cho cửa sổ 3 giây (`60/3 = 20`) → **`rorBT` = °C/phút ×10**.
Trần 950 = 95,0 °C/phút.

Tham số ở `pc_link.json`: `ror_window_s = 3`, `ror_gain = 20`, `ror_bt_clamp = 95.0`,
`ror_et_clamp = 20.0`, `kalman_bt = [1.0, 1.0, 0.005]`, `kalman_et = [1.0, 1.0, 0.01]`.

## 2. Khác Artisan ở đâu

| | Artisan (mặc định) | OTL |
|---|---|---|
| Cửa sổ tính | **20 giây** | **3 giây** |
| Thuật toán | `arrayRoR` hai điểm mút; bật được polyfit / Savitzky-Golay | hai điểm mút, không có lựa chọn khác |
| Điểm bên trái cửa sổ | lúc rang **lấy trung bình 3-5 mẫu** quanh nó (`canvas.py:4682`) | một mẫu đơn |
| Tính RoR từ | **đường BT đã làm mượt** (`stemp2`) | **BT thô** |
| Lọc RoR | trung bình trọng số tăng dần (trực tiếp) / hanning (offline) | **Kalman** đệ quy, `q = 0.005` |
| Nhịp cập nhật | mỗi mẫu | **mỗi 3 giây**, giữa các nhịp giữ số cũ |
| Trần | **+45 / −10** °C/phút (bất đối xứng) | **±95** °C/phút |
| Ngoài trần | **bỏ điểm** → đường đứt | **kẹp về biên** → đường phẳng đầu |
| Đầu mẻ | bỏ 10 mẫu sau CHARGE | tính từ đầu |
| Lọc trung vị | có (sau rang) | không |

## 3. Hệ quả thực tế của mấy khác biệt đó

Bốn cái đáng để ý khi thợ nói "số trên app không giống Artisan":

**Cửa sổ 3 giây so với 20 giây là khác biệt lớn nhất.** Cửa sổ ngắn thì nhạy hơn nhưng ồn hơn nhiều —
nhiễu chia cho khoảng thời gian nhỏ nên bị nhân lên. Đây chính là lý do phía mình **phải** có Kalman,
còn Artisan để mặc định 20 giây thì lọc nhẹ cũng đủ. Đừng bỏ Kalman mà giữ cửa sổ 3 giây.

**Kalman và trung bình trọng số không cùng tính chất.** Kalman là bộ lọc đệ quy một trạng thái: `q`
nhỏ (0,005) nghĩa là rất tin vào ước lượng cũ → mượt nhưng **trễ và bám dai** khi RoR đổi đột ngột
(đúng lúc crack). Trung bình trọng số tăng dần của Artisan có cửa sổ hữu hạn nên "quên" hẳn sau
`n` mẫu. Muốn so hai đường thì nhớ chúng phản ứng khác nhau ở đúng chỗ quan trọng nhất.

**Artisan tính RoR trên đường đã làm mượt, mình tính trên BT thô.** Nghĩa là Artisan lọc **hai tầng**
(mượt đường rồi mượt RoR), mình lọc **một tầng** (chỉ Kalman trên RoR). Muốn tiến gần Artisan mà không
đổi cửa sổ thì thêm một tầng làm mượt BT trước khi trừ — đó là thay đổi rẻ nhất.

**Trần bất đối xứng của Artisan (+45 / −10) là có chủ ý.** Sau TP thì BT chỉ tăng, RoR âm sâu là dấu
hiệu nhiễu chứ không phải hiện tượng rang. Trần ±95 của mình thả lỏng cả hai chiều nên gai âm vẫn lọt.
Ngoài ra `pc_link.json` đang kẹp ET ở ±20 — chặt hơn BT khá nhiều, hợp lý vì ET dao động theo lửa.

## 4. Nếu muốn tiến gần Artisan hơn

Xếp theo tỉ lệ lợi ích / rủi ro, **chưa cái nào được chốt** — cần chủ máy quyết vì đổi RoR là đổi cảm
nhận của thợ về máy:

1. **Làm mượt BT trước khi trừ** (rẻ nhất, không đổi độ trễ mấy). Trung bình 3 mẫu quanh **điểm bên
   trái** của cửa sổ như `compute_ror_simple` của Artisan — mẹo này giảm nhiễu nửa cửa sổ mà **không**
   thêm trễ cho số hiện tại, vì điểm bên phải vẫn là mẫu mới nhất.
2. **Siết trần âm** từ −95 xuống quanh −10…−20 °C/phút sau khi qua TP. Trước TP thì RoR âm sâu là
   thật (hạt lạnh vào lồng), nên chốt này phải theo mốc, không áp cả mẻ.
3. **Bỏ RoR mấy giây đầu sau charge** thay vì để gai tụt hiện lên đồ thị.
4. **Nới cửa sổ lên 5 giây** — bớt ồn rõ, thêm trễ ít. Cẩn thận: `ror_gain` phải đổi theo
   (`60 / cửa_sổ`), và **firmware, `roast_derive.py`, `pc_link.json` phải đổi cùng lúc**, không thì hai
   bên tính lệch nhau. Kèm theo là mọi ngưỡng dựa trên RoR (luật cắt gas ở crack, `rorBT_pro`) phải
   xem lại.
5. **Ngoài trần thì bỏ điểm thay vì kẹp về biên.** Kẹp làm đường phẳng đầu, trông như RoR thật đang ổn
   định ở 95 — dễ đọc sai. Bỏ điểm thì đường đứt, thợ thấy ngay là số không tin được.

Mục 4 là mục nặng nhất: nó chạm cả ba nơi và chạm luôn phần điều khiển gas. Xem
`[[project_gas_calib_auto]]` và `[[project_ror_gas_cut_crack]]` trước khi đụng.

## 5. Đừng chép nguyên hai chỗ này của Artisan

- **Drop Spikes** (`canvas.py:4592`) — điều kiện không bao giờ đúng, chi tiết ở
  [bo-loc.md](bo-loc.md) mục 1c. Chép nguyên là chép một bộ lọc chết.
- **Savitzky-Golay** — cần nhìn dữ liệu **tương lai**, nên không dùng được lúc đang rang, bất kể máy
  mạnh cỡ nào. Chỉ có nghĩa cho phần xem lại mẻ trong app (và cần scipy, hiện app không có).
