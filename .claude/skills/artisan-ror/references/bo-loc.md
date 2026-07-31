# Các bộ lọc của Artisan — tab Curves → Filters

Nguồn: `canvas.py:4550` (`inputFilter`), `canvas.py:9081` (`smoothETBT`), `util.py:1060-1208`.
Hộp thoại chia 4 nhóm; dưới đây theo đúng nhóm trên màn hình.

## Mục lục
- [1. Input Filter — lọc số thô lúc đọc](#1-input-filter)
- [2. Curve Filter — làm mượt đường ET/BT](#2-curve-filter)
- [3. Display Filter — chỉ ảnh hưởng hình vẽ](#3-display-filter)
- [4. Rate of Rise Filter](#4-rate-of-rise-filter)
- [5. Chọn bộ lọc theo triệu chứng](#5-chon-bo-loc-theo-trieu-chung)

---

## 1. Input Filter

Chạy trong `inputFilter()` trên **từng mẫu vừa đọc, trước khi lưu vào mảng**. Đây là tầng duy nhất
chạy y hệt cả lúc rang và lúc xem lại (vì nó xảy ra lúc đọc). Hàm trả về nhiệt độ đã sửa, hoặc `-1`
nghĩa là "bỏ mẫu này".

Cơ chế chung: phát hiện mẫu xấu → đặt `wrong_reading` (1 = vi phạm min/max, 2 = trùng lặp / gai) →
xử lý ở `canvas.py:4597-4609`. Với `wrong_reading = 2` thì **lặp lại mẫu tốt trước đó**; nhưng nếu 3
mẫu gần nhất đã bằng nhau (tức đã vá 2 lần liền) thì thôi, trả số thật — không vá vô hạn.

### 1a. Interpolate Duplicates

`canvas.py:4555`. Cắt mẫu gần như không đổi so với mẫu trước:

```python
abs(temp - tempx[-1]) <= dropDuplicatesLimit
```

Ngưỡng trong ảnh chụp là `0.30 C`; mặc định trong code là **0.54** (`canvas.py:2235`). Có xét cả trường
hợp mẫu trước là `-1` thì so với mẫu trước nữa.

Dùng khi đầu đọc trả số **bậc thang** (độ phân giải thô hơn thang đo) — đường bậc thang làm RoR nhảy
gai vuông. Có một phần vá ngược ở `canvas.py:4610-4617`: khi có mẫu thật mới, hai mẫu vừa bị lặp được
**nội suy lại** cho đường liền mạch thay vì giữ bậc.

### 1b. Limits (min / max)

`canvas.py:4559`. Ngoài `[filterDropOut_tmin, filterDropOut_tmax]` → `wrong_reading = 1` → trả `-1`,
tức mẫu bị **loại hẳn** chứ không vá. Mặc định `0 … 700 °C` (`1292 °F`) — `canvas.py:2219-2222`.

Đây là lưới bắt **tuột đầu dò / hở mạch** (đọc ra 0 hoặc số vô lý). Nên bật, ngưỡng rộng.

### 1c. Drop Spikes — ⚠ ĐANG KHÔNG CHẠY

`canvas.py:4563-4593`. Ý định: so RoR do mẫu mới tạo ra với RoR của `n = 3` mẫu trước
(`filterDropOut_spikeRoR_period`, `canvas.py:2214`); lệch quá `dRoR_limit` (4.2 °C/giây, hoặc 7 °F —
`canvas.py:2223-2224`) thì coi là gai.

Nhưng điều kiện viết ở `canvas.py:4592` là:

```python
RoR = dtemp/dtime
if (pRoR + dRoR_limit) < RoR < (pRoR - dRoR_limit):
    wrong_reading = 2
```

Với `dRoR_limit = 4.2 > 0` thì biên dưới `pRoR + 4.2` luôn **lớn hơn** biên trên `pRoR − 4.2` → chuỗi
so sánh **không bao giờ đúng**. Bật ô Drop Spikes trên UI thực tế **không cắt gai nào**. Bản cũ (còn
trong comment ở `canvas.py:4585-4588`) dùng trị tuyệt đối và chạy được:

```python
RoR = abs(dtemp/dtime)
if RoR > (pRoR + dRoR_limit):
    wrong_reading = 2
```

Chép sang OTL thì viết `RoR > pRoR + dRoR_limit or RoR < pRoR - dRoR_limit` (đối xứng, đúng ý định
của comment *"symmetric and more conservative"*). Đừng chép nguyên dòng hiện tại.

### 1d. ET ↔ BT (Swap)

Đổi chỗ hai kênh đọc. Chỉ dùng khi đấu dây/khai báo kênh ngược — không phải bộ lọc, nằm nhóm này vì
tiện.

---

## 2. Curve Filter

### Smooth Curves

Biến `curvefilter`, áp trong `smoothETBT()` → `smooth_list()` với cửa sổ **hanning**. Kết quả vào
`stemp1`/`stemp2`, và **đây là đường dùng để tính RoR** (`canvas.py:9117` truyền `stemp1/stemp2` vào
`recomputeDeltas`).

Nhớ: `nội bộ = UI × 2 + 1`. Mặc định nội bộ 3 (UI 1); ảnh chụp UI 2 → nội bộ 5.

**Không chạy khi đang rang** — `canvas.py:9089-9091`: `if self.flagon:` thì chỉ vá lỗ hổng, gán thẳng
`stemp1 = temp1_nogaps`. Nên đường trên máy lúc rang luôn gai hơn đường mở lại sau đó.

### Smooth Spikes

Biến `filterDropOuts`, bật **lọc trung vị** `medfilt` (`util.py:1060-1077`) trước khi cuộn cửa sổ —
`util.py:1101-1113`. Cửa sổ `k = 5` cho đường ET/BT (`median_filter_factor`) và `k = 3` cho RoR
(`median_filter_factor_RoR`) — `canvas.py:2238-2239`, comment ghi *"k=3 là bảo thủ, chưa bắt hết gai;
k=5 hoặc 7 thì ổn; 13 có lẽ là trần"*.

Lọc trung vị mạnh hơn hẳn cuộn cửa sổ ở việc cắt **gai đơn lẻ** mà không kéo lệch phần còn lại — cuộn
cửa sổ thì trải cái gai ra cả cửa sổ. Cũng **chỉ chạy sau khi rang**:
`filter_dropouts = self.filterDropOuts and not self.flagon` (`canvas.py:8752`, `:9095`).

Bản lọc trung vị trực tiếp cho RoR đã được viết nhưng **đang bị comment lại** (`canvas.py:5060-5067`),
kèm ghi chú *"RoR Smooth Spikes is only applied offline"*.

---

## 3. Display Filter

Hai ô này **không** đổi số liệu, chỉ đổi cách vẽ:

- **Interpolate Drops** (`interpolateDropsflag`, mặc định bật — `canvas.py:1684`): vá lỗ hổng bằng
  `fill_gaps()` để đường không đứt tại mẫu mất tín hiệu. Áp trước khi làm mượt (`canvas.py:9088`).
- **Show Full**: vẽ cả phần ngoài CHARGE→DROP (đoạn hâm lồng và sau khi xả), thay vì chỉ trong mẻ.

---

## 4. Rate of Rise Filter

| Ô | Biến | Việc |
|---|------|------|
| **Delta Span** | `deltaETspan` / `deltaBTspan` | Cửa sổ tính RoR, **tính bằng giây**; quy sang số mẫu theo chu kỳ đọc (`canvas.py:2817`) |
| **Smoothing** | `deltaETfilter` / `deltaBTfilter` | Cửa sổ làm mượt RoR (`nội bộ = UI×2+1`); offline dùng đầy, trực tiếp dùng nửa |
| **Polyfit computation** | `polyfitRoRcalc` | Đổi từ hai-điểm-mút sang hồi quy bậc 1 |
| **Optimal Smoothing Post Roast** | `optimalSmoothing` | Bật Savitzky-Golay; **chỉ dùng được khi Polyfit đang bật** (`curves.py:373`, `:2463`) và chỉ khi xem lại |
| **Limits min/max** | `RoRlimitm` / `RoRlimit` | Ngoài dải → điểm bị **bỏ** (đường đứt), không kẹp về biên |

Chi tiết công thức từng thuật toán: [ror-thuat-toan.md](ror-thuat-toan.md).

Lưu ý ràng buộc UI: bỏ tick Polyfit thì Optimal Smoothing bị tắt theo và khoá lại — không có tổ hợp
"Savitzky-Golay mà không Polyfit".

---

## 5. Chọn bộ lọc theo triệu chứng

| Triệu chứng | Nên chạm | Đừng chạm |
|---|---|---|
| RoR nhảy gai vuông, đường BT có bậc thang | **Interpolate Duplicates** (đầu đọc thô) | tăng Smoothing — chỉ che, không sửa |
| Một hai điểm bay vọt rồi về ngay | **Smooth Spikes** (lọc trung vị) | Drop Spikes — đang không chạy, xem 1c |
| Đọc ra 0 hoặc số vô lý khi tuột đầu dò | **Limits** min/max | |
| RoR mượt nhưng **trễ**, phản ứng chậm khi chỉnh gas | giảm **Smoothing**, giảm **Delta Span** | Optimal Smoothing (không chạy lúc rang) |
| RoR ồn quá không đọc được xu hướng | tăng **Delta Span** trước, rồi mới tới Smoothing | |
| Số lúc rang khác số khi mở lại file | không phải lỗi — xem bảng "lúc rang khác sau khi rang" ở SKILL.md | |
| Đường RoR **đứt đoạn** giữa mẻ | nới **Limits** RoR — điểm vượt trần bị bỏ | Interpolate Drops (đó là lỗ do mất tín hiệu, khác) |
| Đầu mẻ không có RoR | bình thường — xem [ror-thuat-toan.md](ror-thuat-toan.md) mục 6 | |

Nguyên tắc chung khi gỡ nhiễu: **sửa ở tầng thấp nhất có thể**. Nhiễu do đầu đọc thì lọc ở tầng đầu
vào; tăng Smoothing của RoR để che nhiễu cảm biến là đổi độ trễ lấy vẻ đẹp, và độ trễ đó làm thợ chỉnh
gas sai nhịp.
