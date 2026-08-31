# Config preset — 3kg auto M01 (bản cũ)

Lưu ngày **2026-08-26**. Build: **RAM 81.4% (40016/49152 B), Flash 38.5% (100948/262144 B)** — SUCCESS, **CHƯA FLASH lên máy**.

Máy rang **3kg auto, bản cũ, của M01** — board **V400**, **không vacuum control**, **không module IO relay ngoài**, **có biến trở vật lý (VR)** trên board. Đặc thù: đầu đốt **THƯỜNG (không premix)**, phải đạt **tối thiểu 50% gas mới lên được lửa** (thử 40% vẫn không lên).

## Đặc thù cấu hình

| Mục | Giá trị | `#define` |
|-----|---------|-----------|
| Board | **V400** | `#define V400 true` — SerialModbus=USART2, SerialComputer=UART4 (ĐẢO so với V300/V350), ADC VR 650 count |
| Mẻ danh định | 3 kg | `MACHINE_BATCH_KG 3` |
| Nguồn điều khiển | **VR vật lý** | `MACHINE_VR_SOURCE_FROM_HMI 0` — gió/drum/gas đọc từ biến trở trên board |
| Vacuum sensor | **TẮT** | `MACHINE_HAS_VACUUM_SENSOR 0` — không PID gió theo áp hút |
| Air inverter (RS485) | **TẮT** | `MACHINE_HAS_AIR_INVERTER 0` — chỉ cần khi có vacuum |
| IO relay module | **TẮT** | `MACHINE_HAS_IO_RELAY_MODULE 0` — relay đi qua GPIO onboard |
| Cân / auto-loader | **TẮT** | `MACHINE_HAS_SCALE_FEEDER 0` — feeder chạy theo timer |
| Drum speed control | Có | `MACHINE_HAS_DRUM_SPEED_CONTROL 1` — biến tần drum slave 4 |
| Gas / Airflow | Có | `MACHINE_HAS_GAS_CONTROL 1`, `MACHINE_HAS_AIRFLOW_CONTROL 1` (DAC) |
| BT / ET thermocouple | Có | `MACHINE_HAS_BT_TEMP_CONTROLLER 1`, `MACHINE_HAS_ET_TEMP_CONTROLLER 1` |
| Preheat | PID kiểu Artisan | `PREHEAT_USE_PID 1` |
| **Gas mồi lửa** | **50%** | `PH_IGNITE_GAS 50` — **mới thêm** |
| Gas relay-autotune | **50%** (trước 25) | `PH_TUNE_GAS_HI 50` |
| **Loại đầu đốt** | **THƯỜNG, khoá lúc build** | `MACHINE_BURNER_FORCE_STANDARD 1` — **mới thêm** |

## Khối cần chép để load lại preset này

```cpp
// Board
// #define V300 true
// #define V350 true
#define V400 true

// Phần cứng/ngoại vi có lắp trên máy
#define MACHINE_HAS_AIRFLOW_CONTROL       1
#define MACHINE_HAS_GAS_CONTROL           1
#define MACHINE_HAS_DRUM_SPEED_CONTROL    1
#define MACHINE_HAS_AIR_INVERTER          0
#define MACHINE_HAS_VACUUM_SENSOR         0
#define MACHINE_HAS_SCALE_FEEDER          0
#define MACHINE_HAS_IO_RELAY_MODULE       0
#define MACHINE_HAS_BT_TEMP_CONTROLLER    1
#define MACHINE_HAS_ET_TEMP_CONTROLLER    1
#define MACHINE_BATCH_KG                  3

#define MACHINE_VACUUM_FROM_DRUM          0
#define MACHINE_VR_SOURCE_FROM_HMI        0

// Đầu đốt THƯỜNG (KHÔNG premix) — khoá lúc build, bỏ qua reg HMI 29
#define MACHINE_BURNER_FORCE_STANDARD     1

// Mồi lửa — bếp thường của máy này cần tối thiểu 50% gas
#define PH_IGNITE_GAS                     50
#define PH_TUNE_GAS_HI                    50
```

> **BẪY (ghi lại từ lần 12kg):** đừng chép nguyên file `Config.h` từ doc cũ đè lên — doc cũ thiếu các `#define` mới sinh sau đó (SD retry, dif cố định, chốt an toàn R7...) → gãy build. Chỉ chép các khối ở trên.

## Thay đổi mã nguồn kèm theo (dùng chung mọi máy)

`PH_IGNITE_GAS` là **define mới** — trước đây mức gas mồi lửa bị ghi cứng `30` trong code. Đã thay bằng define ở:

- [Preheat_PID.h:413](../../include/Preheat_PID.h#L413) — `gasPercent = PH_IGNITE_GAS` trong trạng thái `WU_IGNITE`
- [Preheat_PID.h](../../include/Preheat_PID.h) — 5 chỗ `wuGasPercent = PH_IGNITE_GAS` (mức gas khởi đầu khi vào `WU_HEATING`: sau mồi thành công ×2, sau tune xong/timeout/stuck ×3). Lý do đổi luôn cả 5: lửa vừa bắt được ở 50% mà thả xuống 30% là tắt ngay.
- [Preheat.h:1209](../../include/Preheat.h#L1209) — bản preheat RoR (không biên dịch khi `PREHEAT_USE_PID 1`, sửa cho đồng bộ)

`MACHINE_BURNER_FORCE_STANDARD` cũng là **define mới**, chốt tại đúng một chỗ — nơi đồng bộ reg 29 từ HMI trong [Modbus_Master.h:288](../../include/Modbus_Master.h#L288). Đặt 1 thì `burnerPremix_R` bị ghim về 0 mỗi vòng quét, nên mọi nơi đọc nó (`Preheat_PID.h`, `Program.h`, `Preheat.h`) đều thấy bếp THƯỜNG. Đặt 0 để quay lại hành vi cũ (theo HMI).

Máy khác giữ nguyên hành vi cũ bằng cách đặt `PH_IGNITE_GAS 30`.

> **Lịch sử chỉnh:** đặt 40% trước (2026-08-26), chạy thử **vẫn không lên lửa** → nâng lên **50%** cùng ngày.

## Lưu ý khi chạy máy thật

- **V400 đảo cổng serial**: Modbus RS485 chạy trên USART2, debug/Artisan trên UART4. Nạp nhầm firmware V300 vào board V400 (hoặc ngược lại) là **mất hết Modbus + debug** dù đèn vẫn sáng.
- `PH_TUNE_GAS_HI` nâng 25→50 vì relay-autotune đốt ở mức HI; để 25% trên đầu đốt cần ≥50% thì lửa tắt giữa lúc tune → tune ra hệ số rác. Nếu lần preheat đầu ra kết quả lạ, **xóa `/pid_pre.txt`** trên thẻ SD rồi tune lại (máy phải NGUỘI).
- **Bếp THƯỜNG, không phải premix.** HMI đời cũ có thể không có ô chọn bếp; đọc reg 29 ra rác là firmware nhảy nhầm sang bộ tham số PREMIX (`PH_PID_KP_HOLD_PREMIX` yếu hơn, `PH_IGNITE_TMO_PREMIX` 65s, `PH_TUNE_GAS_HI_PREMIX`). `MACHINE_BURNER_FORCE_STANDARD 1` chặn hẳn đường đó.
- Luồng RANG (không phải preheat) mồi lửa ở **50%** gas ghi cứng tại [Program.h:1593](../../include/Program.h#L1593) — vừa ĐÚNG BẰNG ngưỡng 50%, không còn dư biên. Nếu chạy máy thật thấy mồi lúc được lúc không **trong luồng rang** (preheat thì vẫn ổn), nâng số 50 ở dòng đó lên 60.
- `MACHINE_HAS_SCALE_FEEDER 0` → toàn bộ nhánh auto-dif/loader tắt; `LOADER_MIN_NETW` tính theo 3kg nhưng không dùng tới.
- `ARTISAN_MODBUS_BAUD_DEFAULT` đang là 9600 (thừa kế từ bản 12kg) — HMI cài `modbusBaud_R` vẫn ghi đè được. Xác nhận lại với máy M01 nếu nối Artisan.
