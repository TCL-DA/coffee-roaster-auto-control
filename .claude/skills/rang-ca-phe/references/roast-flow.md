# Luồng rang 11 bước — máy trạng thái programScan()

Nguồn: `include/Program.h`, hàm `programScan()` (dòng 1388→2409). Máy **tự bắt mốc theo nhiệt BT**; người vận hành chỉ cài ngưỡng qua thanh ghi `$M` (xem [registers-M.md](registers-M.md)), máy tự chuyển bước + tự chỉnh gas AUTO.

```
[CHUẨN BỊ]  DATA → COOL_DOWN → GAS → CHECK
[RANG]      CHARGE → TP → YELLOW(DE) → FCS → DEV
[KẾT THÚC]  DROP → LOOP_1 → LOOP_2 (rang mẻ tiếp)
```

## A. Chuẩn bị lồng (trước khi nạp)

| Bước | Nhãn HMI | Dòng | Điều kiện & việc |
|------|----------|------|------------------|
| **STP_DATA** | RESET DATA | 1448 | Xoá dữ liệu mẻ cũ, chờ bấm Start |
| **STP_COOL_DOWN** | BT COOLS DOWN | 1514 | Lồng còn nóng → chờ nguội xuống `chargeTemp − turnGasPoint`; đủ nguội → bật gas 50% AUTO → GAS |
| **STP_GAS** | WAITGAS | 1536 | Bếp thường (`burnerPremix=0`): chờ lửa bắt (`READ_CH1` LOW) rồi đặt `preGas`. Bếp premix: khỏi chờ → CHECK |
| **STP_CHECK** | BT HEATUP | 1556 | Chờ BT vào vùng `chargeTemp ± chTolerange` → **tự bật CHARGE + buzzer** → CHARGE. Nếu BT vọt quá (`+5×tolerance`) → tắt gas, quay lại DATA |

## B. Rang (trong mẻ — bắt đầu đếm giờ + ghi SD)

| Bước | Nhãn | Dòng | Mốc chuyển |
|------|------|------|-----------|
| **STP_CHARGE** | WAIT CHARGE | 1576 | **Nạp nhân**. Lưu `BT_CHARGE`, bật timer đóng cửa nạp, bật ghi đường cong (`SAMPLE_COIL`), `timeRoastEn=1` → TP |
| **STP_TP** | CHECK TP | 1621 | **Turning Point** — sau `ulimitTPTime` dò BT thấp nhất; khi BT bật tăng lại → lưu TP → YELLOW |
| **STP_YELLOW** | WAIT YELLOW | 1642 | **DE / Dry End** — `BT ≥ yellowPhase` → hết pha sấy (nhân vàng), ghi "DRY End" → FCS |
| **STP_FCS** | WAIT FCS | 1656 | **First Crack** (nổ lần 1) — `BT ≥ fcsPhase` → lưu FCs → DEV |
| **STP_DEV** | DEV | 1670 | **Development** — tính thời gian & **% phát triển** sau FCs = `timeDev×1000/timeRoast`. Chờ drop |

## C. Xả mẻ & lặp

| Bước | Nhãn | Dòng | Việc |
|------|------|------|------|
| **DROP** | DROP | 1786 | `BT ≥ DROP_PRO` (auto) hoặc bấm Drop → lưu `BT_DROP`, tắt gas nếu `autoOff=1`, **bật cooling+mixer**, timer đóng cửa xả, dừng đếm giờ, trả gas/gió/drum về biến trở, ghi SD "DROP" → LOOP_1 |
| **STP_LOOP_1** | LOOP / NONE | 1679 | Xét `loop_R` (số mẻ): **>1** → auto cân/nạp mẻ tiếp (chỉ khi phễu còn liệu `netW ≥ LOADER_MIN_NETW` & `scaleDataValid`); **≤1** → dừng, mở khoá select, về DATA. Lỗi feeder → huỷ |
| **STP_LOOP_2** | WCANCEL | 1715 | Chờ cửa xả (drop) đóng lại rồi rang tiếp mẻ mới |

## Auto drop & pre-cool (chạy khi progStep ≥ YELLOW, dòng 1771)
- Rang AUTO: `BT ≥ DROP_PRO` → tự bật DROP.
- `BT ≥ DROP_PRO − preCool` (nếu `preCool>0`) → bật sớm cooling+mixer trước khi xả.

## Chạy song song (theo timer giây, xem `timerPoll_1000ms`)
Cooling + mixer, afterburner (đốt khói), destoner (tách đá), auto-fill silo, vacuum PID — bật/tắt theo mốc rang và thanh ghi `$M`.

## Ghi chú
- Các ngưỡng nhiệt so sánh dạng `_CV` = giá trị `$M` ×10 (cùng thang BT ×10).
- Mốc mẻ (`CHARGE/TP/DE/FCs/DROP`) được ghi ra SD qua `sdCsvPendingEvent` — trên app là log SQLite, xem [program-functions.md](program-functions.md).
- Trạng thái đẩy HMI qua `setMachineStatus(STT_*)`; nhãn hiển thị qua `STEP_STRING`.
