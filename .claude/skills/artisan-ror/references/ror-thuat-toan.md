# Thuật toán RoR của Artisan

Nguồn: `_external/artisan-master/artisan-master/src/artisanlib/util.py` (phần `### RoR computation`, dòng 1211→1348)
và `canvas.py` (đường chạy trực tiếp, dòng 4682→5102).

## Mục lục
- [1. Bốn thuật toán](#1-bon-thuat-toan)
- [2. Làm mượt RoR sau khi tính](#2-lam-muot-ror)
- [3. Cắt & kẹp](#3-cat-kep)
- [4. Công thức tự đặt (symbolic)](#4-cong-thuc-tu-dat)
- [5. Phép chiếu nhiệt — projection](#5-phep-chieu-nhiet)
- [6. RoR bắt đầu vẽ từ đâu](#6-ror-bat-dau-ve-tu-dau)

---

## 1. Bốn thuật toán

`computeDeltas()` chọn nhánh theo hai cờ `optimal_smoothing` (ô *Optimal Smoothing Post Roast*) và
`polyfit_ror` (ô *Polyfit computation*) — `util.py:1280-1321`:

| `optimal_smoothing` | `polyfit_ror` | Thuật toán |
|---|---|---|
| ✓ | ✓ | **Savitzky-Golay** (cần scipy) |
| ✗ | ✓ | **polyRoR** — hồi quy bậc 1 từng điểm |
| — | ✗ | **arrayRoR** — hai điểm mút |
| bất kỳ | ✓ | **arrayRoR** nếu polyfit ném lỗi (bẫy SVD của numpy/OpenBLAS trên Windows 10 2004) |

### 1a. `arrayRoR` — hai điểm mút (mặc định, đơn giản nhất)

`util.py:1228-1233`. Đây là thứ gần nhất với cách firmware OTL đang làm.

```python
(temp[wsize:] - temp[:-wsize]) / ((tx[wsize:] - tx[:-wsize]) / 60.)
```

Nghĩa là `RoR[i] = (T[i] − T[i−ds]) / ((t[i] − t[i−ds]) / 60)` với `ds = deltaBTsamples`. Chỉ dùng
**hai** mẫu ở hai đầu cửa sổ, mọi mẫu giữa bị bỏ — nên rẻ nhưng ăn trọn nhiễu của đúng 2 điểm đó.
Mảng kết quả ngắn hơn `ds` phần tử, được đắp bù ở đầu bằng giá trị đầu tiên (`util.py:1325-1326`).

### 1b. `polyRoR` — hồi quy bậc 1 (mượt hơn, đắt hơn)

`util.py:1215-1225`. Mỗi điểm `i` khớp một đường thẳng bình phương tối thiểu qua **toàn bộ** cửa sổ
`[i−wsize, i]` rồi lấy độ dốc:

```python
LS_fit = numpy.polynomial.polynomial.polyfit(tx[left:i+1], temp[left:i+1], 1)
return LS_fit[1] * 60.
```

Dùng hết số liệu trong cửa sổ nên chịu nhiễu tốt hơn `arrayRoR` rõ rệt. Cửa sổ **lùi về sau** (chỉ nhìn
quá khứ) nên vẫn chạy được lúc đang rang, nhưng bị **trễ pha** khoảng nửa cửa sổ. Điểm `i = 0` được
nhân bản từ `i = 1` thay vì trả 0.

### 1c. Savitzky-Golay — chỉ sau khi rang

`util.py:1280-1300`. Đây là "Optimal Smoothing": vừa làm mượt vừa lấy đạo hàm trong một phép.

```python
dss = ds + 1 if ds % 2 == 0 else ds        # cửa sổ phải LẺ
ntemp_lin = numpy.interp(lin, timex, ntemp) # lấy mẫu lại theo thời gian ĐỀU
dist = (lin[-1] - lin[0]) / (len(lin) - 1)  # bước thời gian sau khi lấy mẫu lại
z1 = savgol_filter(ntemp_lin, dss, 1, deriv=1, delta=dss)
z1 = z1 * (60. / dist) * dss
```

Ba điều đáng chú ý:
- **Bắt buộc lấy mẫu lại về thời gian đều** trước khi lọc — Savitzky-Golay giả định bước đều. Nhịp
  đọc thật của Modbus không bao giờ đều, nên bước này không bỏ được.
- Cửa sổ đối xứng (nhìn cả trước và sau) → **không trễ pha**, nhưng vì cần dữ liệu tương lai nên chỉ
  dùng được khi xem lại. Đúng lý do ô này tên là *Post Roast*.
- Nhân `dss` rồi lại truyền `delta=dss` là bù trừ cho nhau — đừng "dọn" một trong hai.
- Thiếu scipy hoặc mẫu ít hơn cửa sổ → tự rơi về `polyRoR`, rồi rơi tiếp về `arrayRoR`.

### 1d. Đường chạy trực tiếp lúc đang rang

`canvas.py:4682` `compute_ror()` / `compute_ror_simple()`. Khác biệt đáng chú ý so với offline: điểm
**bên trái** của cửa sổ được lấy trung bình 3 hoặc 5 mẫu quanh nó, còn điểm bên phải là mẫu mới nhất
nguyên bản:

```python
(temp[-1] - (temp[-l-2] + temp[-l-1] + temp[-l] + temp[-l+1] + temp[-l+2]) / 5.) / timed * 60.
```

Lý do (comment ngay trên chỗ đó): *"average the left point of the RoR interval without introducing a
delay"* — làm mượt được một nửa cửa sổ mà **không** thêm trễ cho số hiện tại. Đây là mẹo hay, đáng
chép sang app OTL. Nếu mẫu nào bằng `-1` (mất tín hiệu) thì **lặp lại RoR trước** thay vì trả 0.

---

## 2. Làm mượt RoR

Sau khi có RoR thô, làm mượt bằng `smooth_list()` (`util.py:1158`) với cửa sổ khác nhau tuỳ chế độ —
`util.py:1334-1339`:

```python
if optimal_smoothing:  user_filter = delta_filter          # cửa sổ ĐẦY
else:                  user_filter = round(delta_filter/2) # cửa sổ NỬA
smooth_list(..., window_len=user_filter, decay_smoothing=(not optimal_smoothing))
```

**Hai kiểu làm mượt** (`util.py:1114-1144`):

- **hanning (đối xứng)** — `numpy.convolve(w/w.sum(), s, mode='valid')` với `w = numpy.hanning(n)`,
  mép được vá bằng cách phản chiếu dữ liệu (`util.py:1033`). Mượt nhất, **không lệch pha**, nhưng cần
  cả hai chiều → chỉ offline.
- **decay (trọng số tăng dần)** — trọng số `1, 2, 3, … n`, mẫu càng mới càng nặng:
  `numpy.average(seq, weights=w)` (`util.py:1130-1138`). Nhân quả nên chạy được trực tiếp; đây là thứ
  đang chạy lúc rang (`canvas.py:5079`, `:5085` gọi `decay_average`).

Trước cả hai còn một bước **lấy mẫu lại về thời gian đều** rồi **lấy mẫu ngược về mốc gốc**
(`util.py:1090-1095` và `:1146-1147`). Bỏ bước này thì cửa sổ cuộn bị méo vì nhịp đọc không đều.

Đoạn nào mất tín hiệu (`-1`) được **tách ra** bằng mask trước khi làm mượt, và trả về `NaN` chứ không
bị kéo trung bình cùng số thật (`util.py:1184-1200`). Chi tiết này quan trọng: nó ngăn một lần mất
tín hiệu làm hỏng cả một đoạn RoR quanh nó.

---

## 3. Cắt & kẹp

`util.py:1342-1347` — bước cuối, làm cùng một lượt:

```python
d if ((roast_start_idx <= i <= roast_end_idx) and
      (d is not None and (not limit_ror or ror_limit_min < d < ror_limit_max)))
else None
```

- Ngoài khoảng CHARGE→DROP → `None` (không vẽ, không phải 0).
- Ngoài trần RoR → `None`. **Vượt trần thì mất điểm, không bị kẹp về biên** — nên đường RoR sẽ *đứt*
  chứ không *phẳng đầu*. Nhìn thấy RoR đứt đoạn là biết đã vượt trần, không phải mất tín hiệu.

Lúc đang rang, phép kẹp ở `canvas.py:5094-5098` có thêm một trần cứng `maxRoRlimit` chồng lên trần
người dùng: `max(-maxRoRlimit, RoRlimitm) < v < min(maxRoRlimit, RoRlimit)`.

---

## 4. Công thức tự đặt

Ô **ΔET Y(x)** / **ΔBT Y(x)** ở tab RoR. Áp **sau khi** tính RoR và **trước khi** làm mượt RoR —
offline ở `util.py:1328-1332`, trực tiếp ở `canvas.py:5049-5058`. Biến của công thức là `R1` (ΔET) và
`R2` (ΔBT).

Thứ tự đó có hệ quả thật: công thức `x/2` để đổi RoR sang °C/30giây sẽ **cùng bị làm mượt** như RoR
gốc. Còn phép chiếu nhiệt lại dùng bản **chưa** qua công thức (xem mục 5).

---

## 5. Phép chiếu nhiệt

`canvas.py:6704` `updateProjection()`. Chỉ vẽ sau CHARGE và trước DROP. Ô chọn kiểu ở tab RoR
(`linear` / `quadratic`); **`newton` đã bị vô hiệu trong code** — `canvas.py:1754`:
`# 0 = linear; 1 = quadratic; # 2 = newton#disabled`.

**Tuyến tính** (mặc định, và cả kiểu quadratic trong 5 phút đầu):

```python
BTprojection = ctemp2[-1] + unfiltereddelta2_pure[-1] * (right - left) / 60.
```

Dùng `unfiltereddelta*_pure` — RoR **chưa làm mượt và chưa qua công thức tự đặt**
(`canvas.py:5045-5046`). Cố ý: phép chiếu cần phản ứng tức thì, làm mượt vào là chiếu bị trễ.

**Bậc hai** — chỉ bật sau 5 phút từ CHARGE (`canvas.py:6759`). Ước lượng RoRoR (đạo hàm của RoR) trên
cửa sổ `max(10, deltaBTsamples)` mẫu, kẹp `±0.002 °C/giây²`, rồi tích luỹ từng bước thời gian. Kẹp đó
là để một nhịp nhiễu không làm đường chiếu bay lên trời.

---

## 6. RoR bắt đầu vẽ từ đâu

Hay bị hỏi "sao đầu mẻ không có RoR" — có hai lý do khác nhau:

- **Sau khi rang**: RoR bắt đầu tính từ **10 mẫu sau CHARGE** —
  `RoR_start = min(timeindex[0] + 10, len(timex) - 1)` (`canvas.py:9115-9117`), comment ghi rõ *"to
  avoid this initial peak"*. Lúc hạt vào lồng, BT tụt dốc đứng, RoR ở đó là gai vô nghĩa.
- **Lúc đang rang**: điểm bắt đầu vẽ lùi thêm cả cửa sổ lọc (`canvas.py:5111`, `:5117`):
  `max(charge, charge + round(filter/2) + max(2, samples + 1))`. Với Smoothing 30 (nội bộ 61) và span
  20 s ở chu kỳ 1 s: `31 + 21 = 52` mẫu ≈ **52 giây đầu mẻ không có đường RoR**. Đây là hành vi đúng
  theo thiết kế, không phải lỗi — nhưng cần biết để khỏi đi tìm bug.
