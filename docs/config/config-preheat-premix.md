# Preset preheat — ĐẦU ĐỐT PREMIX

Lưu ngày **2026-07-13**. Preset preheat theo **LOẠI ĐẦU ĐỐT**, chọn **lúc chạy** qua HMI — **KHÔNG build riêng**.

## Máy biết là premix qua đâu?

Thanh ghi HMI **`burnerPremix_R`** (địa chỉ nội `burnerPremix_W = 29`, "Burner selection"):
- **0** = đầu đốt thường (khuếch tán) — lúc charge phải **chờ tín hiệu lửa** mới set gas.
- **1** = đầu đốt premix (khí+gió trộn sẵn) — **không chờ**, set gas charge thẳng ([Program.h STP_GAS](../../include/Program.h)).

**1 firmware chạy cả 2 loại.** Ở `WU_IDLE` (lúc preheat nhận quyền), `Preheat_PID.h` đọc `burnerPremix_R` rồi override 4 tham số preheat sang bộ PREMIX nếu =1, ngược lại giữ bộ THƯỜNG. Người vận hành chỉ **cài trên HMI**, khỏi build lại, khỏi lo quên đổi Config. Log in `PREHEAT-PID: burner=PREMIX/NORMAL` để xác nhận.

> Chỉ liên quan `PREHEAT_USE_PID = 1` (preheat PID kiểu Artisan → [include/Preheat_PID.h](../../include/Preheat_PID.h)). Máy premix đầu tiên: [config-6kg-auto-philipines.md](config-6kg-auto-philipines.md).

## Vì sao premix cần bộ riêng

Rút từ log thực máy 6kg (2026-07-13):

- **Turndown hẹp, phi tuyến mạnh:** lửa nhỏ (gas ~25%) chỉ đủ tới trần ~160°C; lửa lớn (100%) bắn BT lên ~19°C/phút. Yếu ở dưới, rất khỏe ở trên.
- **Mồi chậm ~40s** (phải trộn khí trước khi cháy) → cần nới timeout mồi.
- **Dễ limit-cycle khi GIỮ nhiệt:** P/D mạnh làm gas đập 0↔35% → BT dao động ±5°C. Phải làm dịu vòng HOLD.
- **Autotune nhạy điều kiện:** chỉ ra gains đẹp khi chạy **NGUỘI** (BT thấp hơn SV_tune ≥30°C); chạy nóng → gains rác (ki vọt).

## Bộ tham số — 2 cột trong Config.h, runtime chọn

4 tham số này có cặp: `PH_xxx` (THƯỜNG) + `PH_xxx_PREMIX`. `Preheat_PID.h` chọn theo `burnerPremix_R`.

| Tham số | THƯỜNG (`PH_xxx`) | PREMIX (`PH_xxx_PREMIX`) | Lý do khác |
|---------|-------------------|--------------------------|------------|
| `PH_TUNE_GAS_HI`  | 25 | **40** | Lửa tune vượt hẳn trần SV_tune → chạm sớm, dao động cân đối, ZN đo chuẩn |
| `PH_PID_KP_HOLD`  | 5000 | **2000** | P mạnh xoay ±44 đập gas 0↔35 gây limit-cycle ±5°C lúc giữ → hạ để bớt slam rail |
| `PH_PID_KD_HOLD`  | 15000 | **6000** | D swing ±10 mỗi chu kỳ góp vào sóng → bớt D cho êm |
| `PH_IGNITE_TMO`   | 60 | **65** | Premix mồi chậm ~40s → nới timeout tránh báo lỗi mồi sai |

Các tham số **không đổi theo đầu đốt** (dùng chung 1 giá trị):
- `PH_PID_KI_HOLD = 100` — giữ nguyên (triệt lệch tĩnh chậm, chống windup).
- `PH_EMA_OUT_ALPHA = 75` — **ĐỪNG hạ**: thử 0.50 thêm trễ pha → BT limit-cycle ±5°C (đã kiểm chứng), áp cho cả 2 loại.
- KP/KI/KD HEATING, TUNE_*, forecast, deadline, airflow... giữ mặc định gốc.

**Chỗ chọn:** `Preheat_PID.h` case `WU_IDLE` — đọc `burnerPremix_R`, gán `phTuneGasHi / phIgniteTmo / phKpH / phKdH`.

## Bộ gains autotune ĐÃ CHỨNG MINH chạy đẹp (chạy NGUỘI)

Mẻ preheat nguội đầu tiên (BT khởi động 92°C, SV=200, SV_tune=160 LowPV) cho kết quả BT mượt, không sóng, holdDev nhỏ:

```
a=101  Pu=50  →  kp=3750  ki=73  kd=11456
```

→ Nếu muốn máy premix **khỏi autotune mỗi lần khởi động nguội**, seed sẵn `/pid_pre.txt` trên SD với bộ này (gain scheduling khớp SV ±15°C). ⚠️ **Bộ ki=114** (đo lúc chạy nóng, gas 40%) là **RÁC** — nếu file SD lỡ lưu bộ này thì **xóa file** để tune lại từ nguội.

## Quy trình test preheat premix

1. Trên HMI cài **Burner selection = 1** (premix). Kiểm log có `burner=PREMIX`.
2. **Xóa `/pid_pre.txt`** trên thẻ SD trước khi test lại (nếu đang giữ bucket gains rác).
3. Preheat từ máy **NGUỘI** (BT thấp hơn SV ≥30°C) — điều kiện sống còn của autotune.
4. Thu log, kỳ vọng: tune nhanh (gas 40% chạm SV sớm), HEAT + HOLD **không limit-cycle**, BT mượt ±1–2°C.
5. Còn sóng → hạ tiếp `PH_PID_KP_HOLD_PREMIX` (2000→1500). Vọt lúc tune là bình thường (đang đo biên độ).

## Máy đầu đốt THƯỜNG

Chỉ cần cài **Burner selection = 0** trên HMI — cùng firmware, tự dùng cột THƯỜNG. Không đụng Config, không build lại.
