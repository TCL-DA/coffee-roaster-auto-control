# Bảng tham số — nhãn UI ↔ biến ↔ mặc định ↔ dòng code

Đường dẫn gốc: `_external/artisan-master/artisan-master/src/artisanlib/`. Số dòng theo bản trong repo (đọc
2026-07-30); code dịch chuyển thì tìm theo tên biến bằng `Grep`, đừng tin số dòng.

## Quy đổi UI ↔ nội bộ

Mọi cửa sổ làm mượt phải **lẻ**, nên UI chỉ cho nhập nửa:

```
nội bộ = UI × 2 + 1        curves.py:2422 (DeltaBTfilter), :2440 (DeltaETfilter), :2504 (Filter)
UI     = round((nội bộ − 1) / 2)   curves.py:360, :366, :387
```

| Nhãn UI | UI | Nội bộ |
|---|---|---|
| Smoothing (mặc định) | 3 | `deltaBTfilter = 7` |
| Smooth Curves (mặc định) | 1 | `curvefilter = 3` |
| Smoothing (ảnh chụp) | 30 | 61 |
| Smooth Curves (ảnh chụp) | 2 | 5 |

## Tab RoR

| Nhãn UI | Biến | Mặc định | Nguồn |
|---|---|---|---|
| Δ ET / Δ BT (vẽ đường) | `DeltaETflag` / `DeltaBTflag` | — | `canvas.py` |
| ET / BT Projection | `ETprojectFlag` / `BTprojectFlag` | — | `canvas.py:6704` |
| kiểu chiếu (linear/quadratic) | `projectionmode` | `0` = linear | `canvas.py:1754` — **newton đã vô hiệu** |
| Δ Projection | `projectDeltaFlag` | — | `canvas.py:4541` |
| Δ ET Y(x) / Δ BT Y(x) | `DeltaETfunction` / `DeltaBTfunction` | rỗng | `canvas.py:5049-5058`, biến `R1`/`R2` |

## Tab Filters — Input Filter

| Nhãn UI | Biến | Mặc định | Nguồn |
|---|---|---|---|
| Interpolate Duplicates | `dropDuplicates` | tắt | `canvas.py:2234` |
| …ngưỡng | `dropDuplicatesLimit` | **0.54** (ảnh chụp: 0.30) | `canvas.py:2235`, dùng ở `:4555` |
| Drop Spikes | `dropSpikes` | tắt | `canvas.py:2233` — ⚠ điều kiện không bao giờ đúng, xem [bo-loc.md](bo-loc.md) 1c |
| …chu kỳ so | `filterDropOut_spikeRoR_period` | 3 mẫu | `canvas.py:2214` |
| …ngưỡng lệch RoR | `filterDropOut_spikeRoR_dRoR_limit` | 4.2 °C/s · 7 °F/s | `canvas.py:2223-2224` |
| Limits | `minmaxLimits` | — | dùng ở `canvas.py:4559` |
| …min / max | `filterDropOut_tmin` / `_tmax` | 0 / **700 °C** · 0 / 1292 °F | `canvas.py:2219-2222` |
| ET ↔ BT | `swapETBT` | tắt | — |

## Tab Filters — Curve Filter / Display Filter

| Nhãn UI | Biến | Mặc định | Nguồn |
|---|---|---|---|
| Smooth Curves | `curvefilter` | 3 nội bộ = **UI 1** | `canvas.py:1696` |
| Smooth Spikes | `filterDropOuts` | **bật** | `canvas.py:2228` |
| …cửa sổ trung vị đường | `median_filter_factor` | 5 (lẻ) | `canvas.py:2238` |
| …cửa sổ trung vị RoR | `median_filter_factor_RoR` | 3 | `canvas.py:2239` |
| Show Full | — | bật | — |
| Interpolate Drops | `interpolateDropsflag` | **bật** | `canvas.py:1684` |

## Tab Filters — Rate of Rise Filter

| Nhãn UI | Biến | Mặc định | Nguồn |
|---|---|---|---|
| Delta Span Δ ET | `deltaETspan` | **20 s** | `canvas.py:1698` |
| Delta Span Δ BT | `deltaBTspan` | **20 s** | `canvas.py:1699` |
| (suy ra) số mẫu | `deltaETsamples` / `deltaBTsamples` | 6 khởi tạo, tính lại theo chu kỳ đọc | `canvas.py:1701-1702`, `:2811-2818` |
| Smoothing Δ ET | `deltaETfilter` | 7 nội bộ = UI 3 | — |
| Smoothing Δ BT | `deltaBTfilter` | 7 nội bộ = **UI 3** | `canvas.py:1695` |
| Polyfit computation | `polyfitRoRcalc` | — | `util.py:1264` |
| Optimal Smoothing Post Roast | `optimalSmoothing` | **tắt** | `canvas.py:1707` |
| Limits RoR max | `RoRlimit` | **45 °C/min** (81 °F/min) | `canvas.py:2016` |
| Limits RoR min | `RoRlimitm` | **−10 °C/min** (−18 °F/min) | `canvas.py:2017` |
| (trần cứng) | `maxRoRlimit` | chồng lên trần người dùng | `canvas.py:5095-5098` |

**Lưu ý về trần RoR:** ảnh chụp hộp thoại là `±95 C/min`, còn mặc định hiện tại trong code là
`45 / −10`. Comment ngay tại đó ghi `# was 95F/min` và `# was: -95F/min` → Artisan **đã siết mặc định
lại**, giá trị ±95 là bản cũ hoặc do thợ tự đặt. Firmware OTL đang kẹp ±95 °C/min, tức **rộng hơn mặc
định Artisan hiện nay khá nhiều** — xem [doi-chieu-otl.md](doi-chieu-otl.md).

## Chuyển đổi đơn vị RoR giữa °C và °F

Artisan không nhân 1.8 trơn cho RoR. Có hàm riêng `RoRfromCtoFstrict` (dùng ở `canvas.py:2016-2017`) —
RoR là **hiệu** nhiệt độ nên chỉ nhân tỉ lệ, **không** cộng 32. Đổi tay bằng `°F/min = °C/min × 1.8`;
nhầm sang công thức nhiệt độ tuyệt đối là lệch 32 đơn vị.

## Nơi neo trong code

| Việc | Hàm | File:dòng |
|---|---|---|
| Lọc số thô từng mẫu | `inputFilter` | `canvas.py:4550` |
| RoR trực tiếp | `compute_ror`, `compute_ror_simple` | `canvas.py:4682` |
| Làm mượt RoR trực tiếp | `decay_average` | `canvas.py:4628`, gọi ở `:5079`, `:5085` |
| Kẹp RoR trực tiếp | — | `canvas.py:5094-5098` |
| Điểm bắt đầu vẽ RoR | — | `canvas.py:5111`, `:5117` |
| Chiếu nhiệt | `updateProjection` | `canvas.py:6704` |
| Làm mượt ET/BT + gọi tính RoR | `smoothETBT` | `canvas.py:9081` |
| Span → số mẫu | `updateDeltaSamples` | `canvas.py:2811` |
| Tính lại toàn bộ RoR | `recomputeDeltas` | `canvas.py:8718` |
| **Toàn bộ toán RoR** | `computeDeltas` | `util.py:1255` |
| Hồi quy bậc 1 từng điểm | `polyRoR` | `util.py:1215` |
| Hai điểm mút | `arrayRoR` | `util.py:1228` |
| Cuộn cửa sổ hanning | `smooth` | `util.py:1025` |
| Lọc trung vị | `medfilt` | `util.py:1060` |
| Lấy mẫu lại + lọc + mượt 1 đoạn | `smooth_slice` | `util.py:1083` |
| Tách đoạn mất tín hiệu rồi mượt | `smooth_list` | `util.py:1158` |
| Hộp thoại Curves | — | `curves.py` |
