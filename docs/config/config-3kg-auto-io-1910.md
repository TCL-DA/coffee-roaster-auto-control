# Config preset — máy 3 kg, HMI đời cũ (19/10/2026)

Env PlatformIO **`may3kg`** — cùng mã nguồn bản chung, chỉ khác `build_flags` trong `platformio.ini`.

```
pio run -e may3kg            dựng
pio run -e may3kg -t upload  nạp (ST-Link)
```

Build 19/10/2026: **RAM 82,1 % (40372/49152 B), Flash 41,1 % (107864/262144 B)**.

## Phần cứng (chủ máy trả lời 19/10/2026)

| Mục | Giá trị |
|---|---|
| Board | V400 |
| HMI | **đời cũ — KHÔNG có màn Cấu hình máy ($M62)** |
| Núm vặn (VR) | không — gas / gió / trống đặt trên HMI |
| Vacuum | có — cảm biến áp đấu ngõ ACI **biến tần gió RS485 ID 5** |
| Trống | biến tần RS485 ID 4 |
| Module relay ngoài | có — ID 7 (CH1 trống/quạt, CH2 khuấy) |
| Loader | có — **không cân**, nạp theo số giây `feederSet_R` cài trên HMI |
| Cân Bluetooth | không |
| Đốt khói | có |
| Tách đá | có |
| Bếp | **THƯỜNG**, cần **50 % gas** mới lên lửa |

## Cờ build

| Cờ | Giá trị | Ý nghĩa |
|---|---|---|
| `MACHINE_OPT_FIXED` | `0x8E2C` | ghim cấu hình máy, bỏ qua $M62: bit 2 vacuum · 3 loader · 5 relay ngoài · 9 đốt khói · 10 tách đá · 11 khuấy riêng · 15 đã cấu hình |
| `MACHINE_BATCH_KG` | 3 | |
| `MACHINE_HAS_SCALE_FEEDER` | 0 | bỏ hẳn mã cân + tự học dif |
| `MACHINE_BURNER_FORCE_STANDARD` | 1 | ghim bếp thường, bỏ qua ô 29 |
| `PH_IGNITE_GAS` | 50 | gas mồi lửa preheat + mức khởi đầu sau khi bắt lửa |
| `PH_TUNE_GAS_HI` | 50 | relay-autotune đốt ở 50 % (25 % là tắt lửa giữa lúc tune) |

Không ghim thì HMI cũ đọc $M62 = 0 ⇒ firmware coi là "chưa cấu hình" ⇒ chặn gas / Start / làm nóng, mã 422.
Khi ghim, firmware cũng ghi số ghim vào ô $M62 nội bộ để app Roast Lab (PC_Link) thấy đúng cấu hình.

## Artisan — nút điều khiển (cổng Modbus slave)

| Ô | Nút |
|---|---|
| 12 | Ignition (gas) |
| 13 | Cooling |
| 14 | Charge |
| 15 | Drop |
| 16 | Escape |
| 17 | Start |
| **21** | **Mixer — mới 19/10/2026**, tách khỏi cooling 13 |

Ô 21 trước đây khai tên `vacuumC_show_artisan` nhưng không có code nào ghi — áp hút ra Artisan ở ô 9.
Artisan ghi được ô 12–21 chỉ khi HMI đang ở chế độ **PC control** (giống các nút cũ). Ở chế độ HMI, board báo trạng thái
mixer lên ô 21.

## Đối chiếu HMI cũ

So với bản nạp máy 3 kg ngày 09/07/2026 (`7e86993`): không địa chỉ thanh ghi HMI nào đổi số, chỉ thêm ô mới. Ô $M53–$M61 đọc 0
thì firmware dùng mặc định trong `Config.h`.

## Lưu ý chạy máy

- Luồng RANG mồi lửa ở 50 % gas ghi cứng (`Program.h`, `gasPercent = 50`) — đúng bằng ngưỡng của bếp này, không dư biên.
  Mồi trong lúc rang chập chờn thì nâng lên 60.
- Loader không cân: chưa cài số giây nạp (`feederSet_R` = 0) thì AUTO báo lỗi loader, không hút mù.
- Lần preheat đầu ra kết quả lạ: xoá `/pid_pre.txt` trên thẻ SD rồi tune lại khi máy NGUỘI.
