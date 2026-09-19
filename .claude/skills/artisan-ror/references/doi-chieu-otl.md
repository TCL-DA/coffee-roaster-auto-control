# Đối chiếu RoR: Artisan ↔ firmware OTL ↔ app

Nguồn phía mình: `include/Program.h:107-118` (firmware), `tools/roast_derive.py` (bản Python cho app),
`protocol/pc_link.json` mục `derive` (tham số dùng chung). Phía Artisan: xem
[ror-thuat-toan.md](ror-thuat-toan.md).

## 1. Công thức của mình

> **HIỆN TẠI — firmware v3.12.0 (20/09/2026):** `rorBT` **và** `rorET` chạy **y hệt chuỗi lúc-đang-rang
> của Artisan** — `rorArtisanStep()` trong `Program.h`, tham số ở `Config.h`: `ROR_SAMPLE_SEC 1`,
> `ROR_DELTA_SPAN_SEC 10`, `ROR_SMOOTHING 3`, `ROR_CURVE_SMOOTH 2`. Không còn Kalman cho BT/ET.
> `rorBT_pro` chạy cùng chuỗi trên `sdBT[]`. Bản C số nguyên lệch mô hình Artisan ≤ 0,015 °C/phút.
> Trần BT và ET đều ±95 °C/phút (ET trước đây ±20). Chọn 1s/10/3 sau 3 mẻ giả tưởng: bản 20s/30 trễ ~30 s,
> có lúc BT tụt 38 s mà HMI vẫn báo RoR dương; bản 1s/10/3 trễ 7–8 s, giật < 0,3 °C/phút.
> **Mục 1–2 dưới đây là lịch sử** (3 s + Kalman → hồi quy 11 mẫu → Artisan 20s/30 → 1s/10/3, cùng ngày).
> **Preheat KHÔNG dùng bộ lọc mới:** `Preheat.h` đọc `rorBT_ph`/`rorET_ph` — tính đúng cách cũ (hiệu 3 s +
> Kalman q 0.005/0.01, trần ±95/±20), vì preheat đặt ngưỡng 0,1–0,5 °C/phút theo tín hiệu cũ.
> `tools/roast_derive.py` + `pc_link.json` **CHƯA đổi theo**.

Firmware BT — `Program.h`, trong `timerPoll_1000ms()`, **mỗi giây**:

```cpp
// đệm vòng 11 mẫu BT (×10); trọng số (i−5), D = 110
num = Σ (i−5) · BT[i]          // i = 0 là mẫu cũ nhất
raw_rorBT = num * 6 / 11;      // = num/110 × 60 → °C/phút ×10
rorBT = rorBTKalmanFilter.updateEstimate(raw_rorBT);   // q = 0.05
if(rorBT > 950) rorBT = 950;   // trần 95.0 °C/phút
```

Đây chính là `polyRoR` của Artisan (mục 1b), viết bằng số nguyên. Cửa sổ ~11 s ≈ nửa Delta Span
mặc định của Artisan.

Firmware ET và `tools/roast_derive.py` (bản CŨ) vẫn là hiệu 2 điểm 3 s:

```cpp
raw_rorET = (Temperature_ET - rorETSamp_1) * 20;   // mỗi 3 giây
```

`tools/roast_derive.py` là **bản Python y hệt bản CŨ** (kể cả lớp `Kalman` sao theo
`SimpleKalmanFilter` của firmware), dùng khi máy chạy khối tương thích không đẩy RoR ra.

Thang đo: `Temperature_BT` ×10, nhân 20 cho cửa sổ 3 giây (`60/3 = 20`) → **`rorBT` = °C/phút ×10**.
Trần 950 = 95,0 °C/phút.

Tham số ở `pc_link.json`: `ror_window_s = 3`, `ror_gain = 20`, `ror_bt_clamp = 95.0`,
`ror_et_clamp = 20.0`, `kalman_bt = [1.0, 1.0, 0.005]`, `kalman_et = [1.0, 1.0, 0.01]`.

## 2. Khác Artisan ở đâu

| | Artisan (mặc định) | OTL |
|---|---|---|
| Cửa sổ tính | **20 giây** | BT: **11 giây** · ET: 3 giây |
| Thuật toán | `arrayRoR` hai điểm mút; bật được polyfit / Savitzky-Golay | BT: **hồi quy bậc 1** (= polyRoR) · ET: hai điểm mút |
| Điểm bên trái cửa sổ | lúc rang **lấy trung bình 3-5 mẫu** quanh nó (`canvas.py:4682`) | một mẫu đơn |
| Tính RoR từ | lúc rang: **`tstemp2`** = BT qua decay 3 mẫu; offline: `stemp2` (hanning) | **BT thô** (hồi quy tự san nấc lượng tử) |
| Lọc RoR | trung bình trọng số tăng dần (trực tiếp) / hanning (offline) | **Kalman** đệ quy — BT `q = 0.05`, ET `q = 0.01` |
| Nhịp cập nhật | mỗi mẫu (mặc định **2 s**) | BT **mỗi giây** · ET mỗi 3 giây |
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

## 6. Số đo so sánh (20/09/2026)

Mô phỏng đúng chuỗi lúc-đang-rang của Artisan theo source (`tstemp` decay → `compute_ror_simple` trung
bình 5 điểm trái → decay RoR nửa cửa sổ) và đúng code firmware. BT độ phân giải 0,1 °C, nhiễu σ = 0,077 °C
(đo trên `data/roast_logs/testnhiet.csv`). Bước RoR 10 → 20 °C/phút:

| Cấu hình | Nhiễu ra (°C/ph) | τ63 | Đạt 90 % |
|---|---|---|---|
| Artisan mặc định, mẫu 2 s (span 20, smoothing 3, curve 1) | 0,13 | 16 s | 20 s |
| Artisan mặc định, mẫu 1 s | 0,14 | 14 s | 20 s |
| Artisan theo ảnh chụp (smoothing 30, curve 2), mẫu 1 s | 0,06 | 24 s | 34 s |
| OTL cũ — hiệu 3 s + Kalman q=0.005 | 0,14 | 20 s | 32 s |
| **OTL mới — hồi quy 11 mẫu + Kalman q=0.05** | 0,21 | **7 s** | **9 s** |

Hệ quả: chạy Artisan song song với HMI thì lúc RoR đổi nhanh (chỉnh gas, crack), số HMI **đi trước**
Artisan chừng 10 s. Không phải lệch sai — là Artisan chậm hơn.

### Quy đổi OTL ↔ ô Delta Span / Smoothing (Smooth Curves 2, Polyfit tắt)

Dò lưới cấu hình Artisan khớp đáp ứng bước + nhiễu gần nhất:

| | Mẫu 2 s (21/27 file .alog của mình) | Mẫu 1 s |
|---|---|---|
| OTL mới (hồi quy 11 + q=0.05) | Delta Span **10 s**, Smoothing **1–2** | Delta Span **10 s**, Smoothing **3** |
| OTL cũ (hiệu 3 s + q=0.005) | Delta Span 4 s, Smoothing 15 | Delta Span 2–4 s, Smoothing 40 |
| Ảnh chụp 20 s / 30 | 90 % sau **54 s**, RoR hiện sau CHARGE **82 s** | 90 % sau 33 s, hiện sau 51 s |

**Smoothing đếm theo SỐ MẪU, không theo giây**: lúc rang dùng `round((2·UI+1)/2)` ≈ UI giá trị RoR gần nhất,
trọng số 1..N, trễ trung bình (N−1)/3 mẫu. Smoothing 30 ở mẫu 2 s = trung bình 60 s lịch sử RoR.
Kalman của OTL tự thích nghi (bước lớn thì nhanh lên) nên quy đổi chỉ đúng cho đoạn giữa mẻ.
