# Nghiên cứu chuyên sâu PID của Artisan

Tài liệu này phân tích PID trong source Artisan nằm tại `artisan-4.0.2/`. Mục tiêu là hiểu đúng bản chất thuật toán, luồng dữ liệu, cơ chế bảo vệ, cách cấu hình, cách kết nối thiết bị ngoài, và ý nghĩa nếu muốn port hoặc mô phỏng trên firmware STM32 của CMS.

## 1. Phạm vi và nguồn đọc

Các file chính đã đọc:

| File | Vai trò |
|---|---|
| `artisan-4.0.2/src/artisanlib/pid.py` | Lõi thuật toán PID phần mềm. |
| `artisan-4.0.2/src/artisanlib/pid_control.py` | Điều phối PID, chọn internal/external PID, SV mode, output mapping. |
| `artisan-4.0.2/src/artisanlib/pid_dialogs.py` | UI cấu hình PID, các tham số người dùng có thể chỉnh. |
| `artisan-4.0.2/src/artisanlib/canvas.py` | Sampling loop: chọn PV, cập nhật PID, cập nhật SV theo Ramp/Soak hoặc background. |
| `artisan-4.0.2/src/artisanlib/main.py` | Artisan command: `PIDon`, `PIDoff`, `p-i-d(...)`, `pidSV(...)`, `pidSource(...)`. |
| `artisan-4.0.2/src/artisanlib/modbusport.py` | Ghi SV/P/I/D ra PID ngoài qua Modbus. |
| `artisan-4.0.2/src/test/unitary/artisanlib/test_pid.py` | Unit test cho lõi PID. |
| `artisan-4.0.2/src/test/uat/artisanlib/test_pid_uat.py` | User-acceptance/destructive tests cho luồng dùng thực tế. |

Các file firmware CMS liên quan để đối chiếu:

| File | Vai trò |
|---|---|
| `include/Preheat_PID.h` | PID preheat của CMS, mô phỏng một phần triết lý Artisan. |
| `include/Config.h` | Tham số preheat PID CMS, trong đó có bộ `Kp/Ki/Kd` giống Artisan C-mode. |
| `include/Modbus_Slave.h` | Cầu nối Artisan PC qua Modbus RTU slave. |
| `include/AnalogConfig.h` | Chọn nguồn Air/Gas/Drum từ VR/HMI/PC/AUTO. |

## 2. Kết luận tổng quan

PID của Artisan không phải là PID cổ điển tối giản kiểu:

```text
out = Kp*e + Ki*sum(e) + Kd*d(e)
```

Nó là một bộ điều khiển phần mềm có nhiều lớp:

1. PID 2DOF: có trọng số setpoint riêng cho P và D.
2. Gain scheduling: nội suy nhiều bộ `Kp/Ki/Kd` theo SV hoặc PV.
3. Anti-windup nâng cao: chống tích phân sai khi output bị bão hòa.
4. Back-calculation: kéo I-term ngược lại khi output bị clamp.
5. Derivative kick prevention: giảm D khi setpoint thay đổi mạnh hoặc sensor bị spike.
6. Filter: IIR Butterworth cho derivative và output.
7. Bumpless transfer: PID vẫn update khi OFF để tránh giật khi bật ON.
8. SV engine: manual, Ramp/Soak, Background Follow có lookahead.
9. Output mapping: duty không nhất thiết là gas; có thể map dương/âm sang các event slider.
10. External bridge: cùng UI có thể lái internal software PID, Modbus PID, S7 PID, TC4 PID, Kaleido PID, Fuji/Delta PID.

Điều quan trọng: nếu chỉ copy `Kp=15`, `Ki=0.01`, `Kd=20` thì chưa copy được "PID Artisan". Phần quan trọng nằm ở lifecycle, anti-windup, lọc, cách chọn PV/SV và cách map output.

## 3. Kiến trúc tổng thể

Luồng chạy giản lược:

```text
Thiết bị / sensor / Modbus / simulator
        |
        v
canvas.py sampling loop
        |
        +--> làm mượt BT/ET/extra curves
        |
        +--> chọn PV theo pidSource
        |
        +--> qmc.pid.update(PV)
        |
        +--> nếu PID active: callback control(duty)
        |
        v
PIDcontrol.setEnergy(duty)
        |
        +--> map duty dương sang slider positive target
        +--> map duty âm sang slider negative target
        |
        v
Event slider / command output / thiết bị rang
```

Đường cập nhật SV:

```text
PID_DlgControl / Artisan command / SV slider
        |
        v
PIDcontrol.setSV(...)
        |
        +--> internal software PID: qmc.pid.setTarget(SV)
        +--> external Modbus PID: modbus.setTarget(SV)
        +--> S7 PID: s7.setTarget(SV)
        +--> TC4 PID: gửi "PID;SV;..."
        +--> Kaleido: kaleido.setSV(...)
```

Đường auto SV:

```text
Sampling loop
        |
        +--> nếu svMode = Ramp/Soak: calcSV(time)
        +--> nếu svMode = Background Follow: lấy curve nền tại time + lookahead
        |
        v
PIDcontrol.setSV(SV mới)
```

## 4. Lõi thuật toán trong `pid.py`

### 4.1. Class PID

Class `PID` có `__slots__`, nghĩa là trạng thái được định nghĩa chặt chẽ để giảm overhead và tránh thuộc tính động. Các nhóm biến chính:

| Nhóm | Biến tiêu biểu | Ý nghĩa |
|---|---|---|
| Giới hạn output | `outMin`, `outMax`, `dutyMin`, `dutyMax` | Clamp thuật toán và clamp duty thực gửi. |
| Tham số PID | `Kp`, `Ki`, `Kd` | Bộ PID chính. |
| 2DOF | `beta`, `gamma` | Trọng số setpoint cho P và D. |
| Term runtime | `Pterm`, `Iterm`, `Dterm` | Kết quả từng thành phần. |
| Lịch sử | `lastError`, `lastInput`, `lastOutput`, `lastTime`, `lastTarget` | Tính dt, D, duty step, setpoint change. |
| Filter | `output_filter`, `derivative_filter`, `*_filter_level` | Lọc output và D. |
| Safety | `derivative_limit`, `measurement_history`, `integral_windup_prevention` | Chống D kick, chống windup. |
| Gain scheduling | `Kp1/Ki1/Kd1`, `Kp2/Ki2/Kd2`, `Schedule0..2` | Nội suy tham số. |

### 4.2. Công thức 2DOF

Trong mỗi lần update hợp lệ:

```text
error = SV - PV

Pterm = Kp(PV/SV) * (beta * SV - PV)
Iterm = Iterm + Ki(PV/SV) * error * dt
Dterm = Kd(PV/SV) * d(gamma * SV - PV) / dt

output_raw = Pterm + Iterm + Dterm
```

Trong đó `Kp(PV/SV)`, `Ki(PV/SV)`, `Kd(PV/SV)` có thể là tham số cố định hoặc tham số sau gain scheduling.

Ý nghĩa `beta`:

| `beta` | Hành vi |
|---:|---|
| `1` | P-on-error cổ điển: P phản ứng đầy đủ với thay đổi SV. |
| `0` | P-on-measurement: P không bị kick trực tiếp khi đổi SV. |
| `0..1` | Giảm dần setpoint kick của P. |
| `>1` | Khuếch đại phản ứng P theo SV, rủi ro overshoot cao hơn. |

Ý nghĩa `gamma`:

| `gamma` | Hành vi |
|---:|---|
| `1` | D-on-error cổ điển: D phản ứng với thay đổi SV và PV. |
| `0` | D-on-measurement: D chỉ phản ứng theo PV, chống derivative kick tốt hơn. |
| `0..1` | Giảm dần derivative kick khi đổi SV. |

Trong UI, Artisan gọi các mode này là:

| Mode | Nghĩa |
|---|---|
| PoE | Proportional on Error, thường tương ứng `beta=1`. |
| PoM | Proportional on Measurement, thường tương ứng `beta=0`. |
| DoE | Derivative on Error, thường tương ứng `gamma=1`. |
| DoM | Derivative on Measurement, thường tương ứng `gamma=0`. |

### 4.3. Khác PID cổ điển ở đâu?

PID cổ điển:

```text
P = Kp * (SV - PV)
D = Kd * d(SV - PV)/dt
```

Artisan:

```text
P = Kp * (beta*SV - PV)
D = Kd * d(gamma*SV - PV)/dt
```

Do đó, người vận hành có thể làm PID bớt "đá" khi đổi SV mà không cần giảm toàn bộ `Kp/Kd`.

Trong rang cà phê, SV thường đổi theo profile hoặc Ramp/Soak. Nếu D-on-error hoàn toàn, mỗi bước SV có thể gây xung D lớn. DoM hoặc gamma thấp thường hợp lý hơn cho hệ nhiệt có quán tính lớn.

## 5. Vòng `update(PV)` chi tiết

Pseudo-code gần logic thực:

```text
function update(PV):
    nếu PV là None hoặc -1:
        bỏ qua

    nếu PID đang OFF:
        target = PV              # bumpless transfer

    nếu chưa có lastTime/lastError:
        seed lastTime, lastError, lastInput
        return

    dt = now - lastTime
    nếu dt < 0.05:
        return                   # giới hạn tần số update hữu hiệu

    setpoint_change = target - lastTarget
    nếu setpoint_change đáng kể:
        set flag giảm D
        nếu bật IRoC:
            reset hoặc giảm Iterm

    Pterm = Kp * (beta*target - PV)

    output_before_integration = Pterm + Iterm
    nếu nên tích phân:
        Iterm += Ki * error * dt
        clamp Iterm theo integral limits

    Dterm = calculate_derivative(PV, dt)
    cập nhật measurement history

    output = Pterm + Iterm + Dterm
    output = output_filter(output) nếu bật

    output_clamped = clamp(output, outMin, outMax)
    back_calculate_integral(output, output_clamped)

    final_output = clamp(output_clamped, dutyMin, dutyMax)

    nếu active và duty thay đổi đủ lớn hoặc đã quá force_duty cycle:
        gọi control(final_output)
```

### 5.1. Bỏ qua input lỗi

`update()` bỏ qua `None` và `-1`. Trong Artisan, `-1` thường đại diện cho giá trị sensor lỗi hoặc chưa có dữ liệu.

Điểm yếu còn lại: một số destructive/fuzz test cho thấy cần thận trọng với NaN/Inf. Test UAT có fuzz float để đảm bảo output không NaN/Inf, nhưng với port firmware nên tự clamp/validate mọi input.

### 5.2. Ngưỡng `dt >= 0.05`

PID chỉ tính khi ít nhất 50 ms trôi qua. Đây là guard chống gọi quá dày. Trong thực tế Artisan thường sampling theo chu kỳ lớn hơn nhiều, ví dụ 1 giây.

Ý nghĩa cho STM32:

1. Không cần tính PID ở mọi loop.
2. Nên có chu kỳ cố định, ví dụ 1 giây cho hệ nhiệt rang.
3. Nếu `dt` không ổn định, D và I sẽ nhiễu.

### 5.3. Bumpless transfer

Khi PID chưa active:

```text
target = PV
```

Điều này làm PID "bám" nhiệt hiện tại khi OFF. Khi bật ON, PID không lập tức thấy sai số lớn do target cũ.

Đây là điểm rất quan trọng nếu firmware có mode chuyển tay/tự động. Không có bumpless transfer thì khi chuyển từ HMI/PC/manual sang PID, output có thể giật gas/air.

## 6. P-term

Công thức:

```text
Pterm = Kp * (beta * SV - PV)
```

Nếu `beta=1`:

```text
Pterm = Kp * (SV - PV)
```

Nếu `beta=0`:

```text
Pterm = -Kp * PV
```

P-on-measurement nhìn lạ nếu đọc riêng lẻ, nhưng I-term sẽ bù offset. Lợi ích là khi SV nhảy, P-term không nhảy theo, giảm shock.

### 6.1. Với máy rang

Máy rang có quán tính nhiệt lớn. P quá mạnh thường gây:

1. Gas tăng quá sớm.
2. BT/ET không phản ứng ngay.
3. Người tune tưởng thiếu gas, tăng tiếp.
4. Khi nhiệt bắt đầu phản ứng thì overshoot.

Do đó Artisan thêm beta để người dùng giảm phản ứng trực tiếp theo SV mà vẫn giữ phản ứng theo PV.

## 7. I-term và anti-windup

### 7.1. Vấn đề windup

Trong hệ rang, khi BT thấp hơn SV rất xa, output có thể bị clamp ở 100%. Nếu vẫn tích phân liên tục, I-term sẽ phình lớn. Khi BT gần tới SV, I-term vẫn đẩy gas cao, gây overshoot.

Artisan xử lý bằng hai lớp:

1. Không tích phân khi output đang bão hòa và error làm bão hòa nặng hơn.
2. Back-calculation khi output bị clamp.

### 7.2. Điều kiện có được tích phân

Logic:

```text
nếu output_before_clamp > outMax và error > 0:
    không tích phân

nếu output_before_clamp < outMin và error < 0:
    không tích phân

ngược lại:
    cho tích phân
```

Ý nghĩa:

| Tình huống | Hành động |
|---|---|
| Output đã max, BT vẫn thấp hơn SV | Dừng tích phân. |
| Output đã min, BT vẫn cao hơn SV | Dừng tích phân. |
| Output max nhưng error đổi chiều | Cho tích phân để kéo output về. |
| Output chưa bão hòa | Cho tích phân. |

### 7.3. Integral limits động

Hàm `_calculate_integral_limits(outMin, outMax, integral_limit_factor)` trả giới hạn I-term theo khoảng output.

Ví dụ:

| `outMin/outMax` | `ILF` | I min | I max |
|---|---:|---:|---:|
| `0..100` | `1.0` | `0` | `100` |
| `-100..0` | `0.6` | `-60` | `0` |
| `-50..50` | `1.0` | `-50` | `50` |

Với output chỉ dương, I-term không âm. Với output hai chiều, I-term cân quanh 0.

### 7.4. Back-calculation

Sau khi có output:

```text
output_before = output_raw
output_after  = clamp(output_raw)
excess = output_before - output_after
Iterm -= excess * back_calculation_factor
```

`back_calculation_factor` mặc định `0.5`.

Ví dụ:

```text
output_raw = 130
outMax = 100
excess = 30
Iterm -= 15
```

Back-calculation giúp I-term không bị kẹt cao sau giai đoạn output bão hòa.

### 7.5. IRoC: Integral Reset on setpoint change

Nếu bật `pidIRoC`, Artisan xử lý setpoint change:

| Mức đổi SV | Hành động |
|---|---|
| `abs(change) > threshold` | Reset I-term về 0. |
| `threshold/2 < abs(change) <= threshold` | Giảm I-term còn 50%. |
| Nhỏ hơn | Giữ I-term. |

Mặc định `pidIRoC = False`, threshold mặc định `30`.

Ý nghĩa:

1. Nếu đang follow profile, SV đổi dần, không nhất thiết reset I.
2. Nếu operator nhảy SV lớn, I cũ có thể không còn phù hợp.
3. IRoC giúp tránh carry-over I-term sai bối cảnh.

## 8. D-term và chống derivative kick

### 8.1. Công thức D

Trong `_calculate_derivative()`:

```text
error_now  = gamma * target     - current_input
error_prev = gamma * lastTarget - lastInput
derror = (error_now - error_prev) / dt
Dterm = Kd * derror
```

Nếu `gamma=1`, D phản ứng với cả SV và PV.

Nếu `gamma=0`:

```text
error_now  = -PV_now
error_prev = -PV_prev
derror = -(PV_now - PV_prev) / dt
```

Đó là derivative on measurement.

### 8.2. Derivative filter

Nếu bật `derivative_filter_level > 0`, `derror` đi qua IIR low-pass:

```text
derivativeFilter(sampling_rate): cutoff 0.1 Hz
```

Hệ rang nhiệt chậm, nên D rất dễ khuếch đại noise sensor. Lọc D là hợp lý.

### 8.3. Derivative limit

Artisan clamp `derror` trước khi nhân `Kd`:

```text
if abs(derror) > derivative_limit:
    derror = sign(derror) * derivative_limit
```

Mặc định trong `PID`: `100.0`.
Mặc định trong `PIDcontrol`: `pidDlimit = 500.0`, khi cấu hình software PID sẽ set xuống lõi.
UI giới hạn `Dlimit` trong `0..999`.

### 8.4. Giảm D sau setpoint change

Khi SV thay đổi lớn hơn `significant_setup_change_limit`:

```text
derror *= 1 - clamp(gamma, 0, 1)/2
```

Nếu `gamma=1`, D giảm tối đa 50%.
Nếu `gamma=0`, không cần giảm vì DoM vốn không bị SV kick.

### 8.5. Phát hiện discontinuity của measurement

Artisan giữ `measurement_history` 5 mẫu. Nếu mẫu mới nhảy lớn hơn:

```text
current_change > 2.5 * avg_recent_change
và current_change > 1.0
```

thì xem là discontinuity. Khi đó:

```text
derror *= 0.3
```

Tức D giảm 70%.

Điều này rất thực dụng với thermocouple/RTD:

1. Nhiễu điện.
2. Mất gói Modbus.
3. Sensor đổi thang hoặc trả mẫu lỗi.
4. Spike khi relay/inverter nhiễu.

## 9. Filter output

Nếu bật `output_filter_level > 0`, output đi qua IIR low-pass:

```text
outputFilter(sampling_rate): cutoff 0.35 Hz
```

Lọc output giúp slider/gas không nhấp nhô theo noise. Tuy nhiên lọc output cũng thêm delay. Với máy rang có quán tính nhiệt lớn, delay nhỏ này thường chấp nhận được.

So sánh:

| Filter | Cutoff | Tác dụng |
|---|---:|---|
| Derivative filter | `0.1 Hz` | Làm mượt D mạnh hơn. |
| Output filter | `0.35 Hz` | Làm mượt duty nhẹ hơn. |

## 10. Gain scheduling

### 10.1. Vấn đề

Một bộ `Kp/Ki/Kd` có thể không phù hợp cho toàn roast:

1. Đầu roast: hạt lạnh, hấp thụ nhiệt mạnh, hệ phản ứng khác.
2. Giữa roast: RoR ổn hơn.
3. Sau first crack: hạt tỏa nhiệt, hệ dễ overshoot.
4. Gas/air hiệu quả thay đổi theo nhiệt, tải, khối lượng, trạng thái drum.

Artisan hỗ trợ gain scheduling để tham số PID thay đổi theo SV hoặc PV.

### 10.2. Cách hoạt động

Có bộ chính:

```text
Kp, Ki, Kd tại Schedule0
```

Và bộ thứ hai:

```text
Kp1, Ki1, Kd1 tại Schedule1
```

Nếu bật quadratic:

```text
Kp2, Ki2, Kd2 tại Schedule2
```

Hàm `getParameter(PV, y0, y1, y2)` sẽ:

1. Chọn biến quan sát: SV hoặc PV.
2. Fit tuyến tính hoặc bậc hai.
3. Tính tham số tại điểm hiện tại.
4. Clamp tham số trong min/max của các bộ cấu hình.

### 10.3. Tuyến tính

Nếu không quadratic:

```text
Kp_current = linear_interpolate(Schedule0, Kp, Schedule1, Kp1)
```

Tương tự cho Ki/Kd.

### 10.4. Bậc hai

Nếu quadratic:

```text
Kp_current = quadratic_fit(
    (Schedule0, Kp),
    (Schedule1, Kp1),
    (Schedule2, Kp2)
)
```

Sau đó clamp để không vượt khỏi min/max của ba giá trị cấu hình.

### 10.5. Rủi ro

Gain scheduling rất mạnh nhưng dễ sai:

1. Nếu schedule point trùng nhau, fit lỗi hoặc không ổn định.
2. Nếu tham số thay đổi quá dốc, output có thể giật.
3. Nếu dùng PV làm biến schedule, noise PV có thể làm tham số dao động.
4. Nếu dùng SV, tham số thay đổi mượt hơn khi SV mượt.

Với STM32 RAM thấp, gain scheduling tuyến tính 2 điểm là hợp lý hơn quadratic.

## 11. Output limits và duty logic

Artisan có hai lớp giới hạn:

| Lớp | Biến | Ý nghĩa |
|---|---|---|
| Algorithm output | `outMin`, `outMax` | Giới hạn output PID trước duty. |
| Duty output | `dutyMin`, `dutyMax` | Giới hạn duty thực gửi ra control callback. |

Trong `PIDcontrol.confSoftwarePID()`:

```text
outMin = -100 nếu có negative target, ngược lại 0
outMax = 100 nếu có positive target, ngược lại 0
```

Điều này nghĩa là nếu không chọn slider đích dương/âm, PID sẽ không sinh output theo hướng đó.

`dutySteps` quy định thay đổi duty tối thiểu để gọi control callback. Mặc định `1`.

`force_duty = 3` trong lõi PID đảm bảo dù duty không đổi đủ `dutySteps`, sau vài vòng vẫn gửi lại output để đồng bộ.

## 12. Mapping duty sang hành động rang

Artisan tách thuật toán PID khỏi thiết bị. Lõi PID chỉ sinh duty. `PIDcontrol.setEnergy()` mới map duty sang slider.

### 12.1. Positive target

Nếu duty dương và `pidPositiveTarget` trỏ tới một event slider:

```text
raw_heat = interp(duty, [0, 100], [slider_min, slider_max])
```

Nếu bật range limit:

```text
raw_heat = interp(duty, [0, 100], [positiveTargetMin, positiveTargetMax])
```

Sau đó Artisan apply step size của slider rồi phát event.

### 12.2. Negative target

Nếu duty âm và `pidNegativeTarget` trỏ tới một event slider:

```text
raw_cool = interp(duty, [-100, 0], [cool_max, cool_min])
```

Điều này cho phép output âm tăng airflow hoặc damper để hạ nhiệt.

### 12.3. Khác biệt với CMS

Trong `include/Preheat_PID.h`, output được dùng trực tiếp:

```text
out >= 0: gas = out, air = base
out < 0 : gas = 0, air = base - out
```

Artisan linh hoạt hơn:

1. Output dương có thể là Burner, Power, Heater, Gas.
2. Output âm có thể là Air, Damper, Fan.
3. Range có thể giới hạn riêng.
4. Có thể không dùng output âm hoặc dương.

## 13. SV engine

### 13.1. Manual mode

Người dùng set SV trực tiếp qua:

1. PID dialog.
2. SV slider.
3. Artisan command `pidSV(...)` hoặc `pidSVC(...)`.

Manual mode thường dùng khi operator muốn giữ một nhiệt mục tiêu cụ thể.

### 13.2. Ramp/Soak mode

Ramp/Soak có 8 segment. Mỗi segment có:

| Trường | Ý nghĩa |
|---|---|
| SV | Nhiệt mục tiêu. |
| Ramp | Thời gian ramp tới SV. |
| Soak | Thời gian giữ SV. |
| Action | Alarm/action khi qua segment. |
| Beep | Báo âm. |
| Description | Ghi chú. |

Trong ramp:

```text
SV(t) = SV_start + slope * (t - t_start)
```

Trong soak:

```text
SV(t) = SV_segment
```

Ramp/Soak time có thể tính từ PID ON hoặc từ CHARGE tùy logic hiện hành.

### 13.3. Background Follow

Background Follow lấy SV từ profile nền. Nếu `svLookahead = n`:

```text
SV = background_curve(time + n)
```

Ý nghĩa:

1. PID phản ứng sớm hơn đường nền.
2. Nếu máy có delay nhiệt lớn, lookahead giúp giảm trễ.
3. Nếu lookahead quá lớn, PID có thể đốt quá sớm và overshoot.

Trong CMS, `PH_PID_LOOKAHEAD_SEC = 6` đang mô phỏng ý tưởng này cho preheat.

### 13.4. SV smoothing

Nếu bật `sv_filter`, Artisan dùng smoothing trên SV trước đó trong `PIDcontrol.smooth_sv()`. Mặc định số mẫu decay là `5`.

Tác dụng:

1. Giảm bậc thang SV.
2. Giảm kick P/D.
3. Làm Ramp/Soak hoặc Background Follow mượt hơn.

## 14. PID source

Trong internal software PID:

| `pidSource` | Nguồn PV |
|---:|---|
| `1` hoặc `0` | BT |
| `2` | ET |
| `3` | Extra device 0 channel 1 |
| `4` | Extra device 0 channel 2 |
| `5` | Extra device 1 channel 1 |
| `6` | Extra device 1 channel 2 |

Trong UI có chi tiết hơi dễ nhầm:

1. Combo hiển thị curve names.
2. ET/BT có thứ tự UI khác thứ tự internal.
3. Code có comment: `pidSource = 1` là BT, `2` là ET.

Khi port sang firmware, nên tránh ambiguous mapping. Nên định nghĩa enum rõ:

```text
PID_SRC_BT = 1
PID_SRC_ET = 2
PID_SRC_EXTRA1 = 3
```

## 15. External PID bridge

`PIDcontrol.externalPIDControl()` trả:

| Giá trị | Loại PID |
|---:|---|
| `0` | Internal software PID. |
| `1` | MODBUS external PID. |
| `2` | S7 external PID. |
| `3` | TC4 PID firmware. |
| `4` | Kaleido PID. |

### 15.1. Modbus external PID

Nếu `PID_device_ID != 0`, Artisan xem là external Modbus PID. Khi set SV:

```text
modbus.setTarget(sv)
```

Tùy cấu hình:

1. Ghi single register.
2. Ghi long.
3. Ghi float.
4. Nhân multiplier `1`, `10`, hoặc `100`.

Khi set P/I/D:

```text
writeSingleRegister(PID_p_register, p * multiplier)
writeSingleRegister(PID_i_register, i * multiplier)
writeSingleRegister(PID_d_register, d * multiplier)
```

Điểm quan trọng cho CMS: `include/Modbus_Slave.h` hiện chưa có register để Artisan ghi trực tiếp `Kp/Ki/Kd` cho PID firmware. CMS chỉ nhận Air/Gas/Drum/SV/Vacuum và nút bấm.

### 15.2. S7 external PID

Tương tự Modbus nhưng qua `s7.setTarget()` và `s7.setPID()`.

### 15.3. TC4 PID firmware

Artisan gửi lệnh serial:

```text
PID;T;kp;ki;kd
PID;CHAN;source
PID;CT;cycle
PID;LIMIT;min;max
PID;ON
PID;OFF
PID;SV;sv
```

### 15.4. Kaleido

Kaleido có PID mode riêng, Artisan đồng bộ ON/OFF và SV qua API của module `kaleido.py`.

## 16. Artisan commands liên quan PID

Các lệnh được xử lý trong `main.py`:

| Lệnh | Ý nghĩa |
|---|---|
| `PIDon` | Bật PID. |
| `PIDoff` | Tắt PID. |
| `PIDtoggle` | Đảo trạng thái PID. |
| `pidmode(0)` | Manual mode. |
| `pidmode(1)` | Ramp/Soak mode. |
| `pidmode(2)` | Background Follow. |
| `p-i-d(kp,ki,kd)` | Cấu hình PID. |
| `pidWeights(beta,gamma)` | Cấu hình 2DOF weights. |
| `pidSV(value)` | Set SV theo đơn vị hiện tại. |
| `pidSVC(value)` | Set SV bằng Celsius, tự convert nếu Artisan đang Fahrenheit. |
| `pidRS(n)` | Chọn Ramp/Soak pattern. |
| `pidSource(n)` | Chọn nguồn input, lệnh dùng 0-based nhưng internal cộng thêm 1. |
| `pidLookahead(n)` | Cấu hình lookahead giây. |

Lưu ý bảo mật/kỹ thuật: nhiều lệnh dùng `eval()` trên phần argument. Trong bối cảnh Artisan là desktop app và command thường do user cấu hình, điều này linh hoạt nhưng không phù hợp để copy sang firmware hoặc môi trường nhận input không tin cậy.

## 17. PID dialog và tham số người dùng

### 17.1. Tab cấu hình chính

Người dùng có thể chỉnh:

| Tham số | Range UI | Ý nghĩa |
|---|---:|---|
| `kp` | `0..9999` | Proportional gain. |
| `ki` | `0..9999` | Integral gain. |
| `kd` | `0..9999` | Derivative gain. |
| `Cycle` | `0..99999 ms` | Dùng cho TC4/Kaleido external PID. |
| `Input` | BT/ET/extra | Nguồn PV. |
| Positive target | None/Event slider | Slider cho duty dương. |
| Negative target | None/Event slider | Slider cho duty âm. |
| Min/Max duty | `-100..100` | Clamp duty. |
| Duty steps | Theo UI | Ngưỡng thay đổi để gửi output. |

### 17.2. Config advanced

| Tham số | Ý nghĩa |
|---|---|
| `P setpoint weight` | `beta`. |
| `D setpoint weight` | `gamma`. |
| `Derivative Filter` | Bật lọc D. |
| `ILF` | Integral limit factor. |
| `Dlimit` | Giới hạn derivative. |
| `IWP` | Integral Windup Prevention. |
| `IRoC` | Integral Reset on setpoint Change. |
| `SP threshold` | Ngưỡng reset I khi SV đổi lớn. |

### 17.3. Flags

| Flag | Ý nghĩa |
|---|---|
| Start PID on CHARGE | Tự bật PID khi bấm CHARGE. |
| Stop PID on DROP | Tự tắt PID khi DROP. |
| Create Events | Ghi event khi PID thay slider. |
| Load p-i-d from background | Nạp PID từ profile nền. |

## 18. Tự bật/tắt theo sự kiện roast

Trong `canvas.py`:

1. Khi CHARGE, nếu `pidOnCHARGE` và PID chưa active, gọi `pidOn()`.
2. Khi DROP, nếu `pidOffDROP` và PID đang active, gọi `pidOff()`.

Điều này phù hợp workflow rang:

```text
PREHEAT / CHARGE chuẩn bị
        |
        v
CHARGE: bật PID hoặc Ramp/Soak
        |
        v
Roast: PID theo BT/ET/background
        |
        v
DROP: tắt PID, tránh tiếp tục đốt/lái sau khi xả
```

Với firmware CMS, release safety cũng cần đảm bảo PC control/PID không tự bật ngoài ý muốn.

## 19. Large LCD và telemetry PID

Artisan có các hàm đọc:

| Hàm | Trả về |
|---|---|
| `piddutycycle()` | Duty và SV hiện tại. |
| `pidPtermIterm()` | I-term và P-term. |
| `pidDtermError()` | Error và D-term. |

Điều này giúp debug PID trực tiếp bằng curve/LCD, rất hữu ích khi tune.

Gợi ý cho CMS: nếu port PID sâu hơn, nên có debug register hoặc Serial gated by `enDebug` cho:

```text
SV, PV, error, P, I, D, output_raw, output_clamped, gas, air, mode
```

## 20. Test coverage nói gì về thiết kế PID

### 20.1. Unit tests

`test_pid.py` kiểm tra:

1. Khởi tạo default/custom.
2. Set parameter và clamp non-negative.
3. ON/OFF/isActive.
4. Filter on/off.
5. Numerical stability với giá trị nhỏ/lớn.
6. Derivative kick prevention.
7. Measurement discontinuity.
8. Derivative limit.
9. Integral windup prevention.
10. Back-calculation.
11. Integral limits cho output dương/âm/đối xứng.

### 20.2. UAT tests

`test_pid_uat.py` mô phỏng:

1. Workflow rang hoàn chỉnh: set target, bật PID, feed nhiệt, nhận duty, tắt PID.
2. Safety limits: output phải nằm trong duty clamp.
3. Tuning workflow: đổi Kp/Ki/Kd trong lúc chạy.
4. Derivative filtering với input nhiễu.
5. Robustness/fuzz với float ngẫu nhiên.

### 20.3. Ý nghĩa

Các test phản ánh triết lý thiết kế:

1. PID phải an toàn khi input lỗi.
2. PID không được vượt giới hạn output.
3. PID phải chịu được thay đổi tham số runtime.
4. PID phải ổn định số học.
5. PID phải chống D kick và windup vì đây là lỗi thực tế dễ gặp.

## 21. So sánh với `include/Preheat_PID.h`

### 21.1. Điểm giống

CMS preheat PID đã lấy nhiều ý tưởng đúng:

| Artisan | CMS Preheat PID |
|---|---|
| `Kp=15`, `Ki=0.01`, `Kd=20` C-mode | `PH_PID_KP=15000`, `PH_PID_KI=10`, `PH_PID_KD=20000`. |
| Lookahead | `PH_PID_LOOKAHEAD_SEC`. |
| Anti-windup | Có logic không tích phân khi bão hòa. |
| D-on-measurement | D tính theo delta BT. |
| D spike reduction | Có history 5 mẫu và giảm D. |
| Output filter | EMA output. |
| Back-calculation | Có trừ bớt I khi clamp. |

### 21.2. Điểm thiếu so với Artisan

| Artisan | CMS hiện tại |
|---|---|
| `beta/gamma` tùy chỉnh | Chưa có 2DOF đầy đủ. |
| Gain scheduling | Chưa có. |
| IIR Butterworth | EMA đơn giản. |
| SV modes đầy đủ | Preheat có lookahead riêng, không phải Ramp/Soak engine đầy đủ. |
| Output mapping linh hoạt | Quy ước cố định `out dương = gas`, `out âm = air`. |
| Duty step và force duty | Chưa tương đương đầy đủ. |
| Bumpless transfer tổng quát | Có reset state khi vào mode, nhưng chưa cùng logic Artisan. |
| External PID bridge P/I/D | Modbus_Slave chưa expose PID Kp/Ki/Kd. |

### 21.3. Điểm lệch cần kiểm tra

Trong `include/Config.h` có:

```text
PH_PID_DLIMIT
```

Nhưng trong `include/Preheat_PID.h`, derivative đang clamp bằng `PH_PID_IMAX`, không dùng `PH_PID_DLIMIT`.

Ý nghĩa:

1. Tài liệu cấu hình nói có D limit riêng.
2. Code đang dùng chung giới hạn với I max.
3. Nếu người dùng chỉnh `PH_PID_DLIMIT`, có thể không có tác dụng.

Đây là một điểm nên sửa nếu tiếp tục hoàn thiện PID CMS.

## 22. Đánh giá tham số mặc định Artisan cho máy rang

### 22.1. `Kp=15`

Với đơn vị Celsius, error 1°C tạo P khoảng 15% duty nếu `beta=1`. Đây là khá mạnh nếu output trực tiếp là gas, nhưng Artisan thường map qua slider/range và có filter/limit.

Trong CMS preheat, error dùng đơn vị `0.1°C` và hệ số `×1000`, nên đã chia scale để tương đương.

### 22.2. `Ki=0.01`

I rất nhỏ, phù hợp hệ nhiệt chậm. I-term chủ yếu bù sai số ổn định, không dùng để kéo nhanh.

Nếu tăng Ki quá cao:

1. Overshoot sau giai đoạn bão hòa.
2. Dao động chậm.
3. Đặc biệt nguy hiểm nếu không có anti-windup.

### 22.3. `Kd=20`

D khá lớn so với Ki. Artisan bù bằng D filter, D limit, setpoint-change reduction và discontinuity reduction.

Nếu port sang firmware mà chỉ lấy Kd cao nhưng thiếu filter/D limit thì rất dễ rung output.

### 22.4. `pidSource=BT`

Mặc định điều khiển theo BT. Với rang thực tế:

| PV | Ưu điểm | Nhược điểm |
|---|---|---|
| BT | Bám trực tiếp hạt, phù hợp profile | Trễ lớn, dễ cần lookahead. |
| ET | Phản ứng nhanh hơn | Không trực tiếp là nhiệt hạt, dễ lệch theo airflow/gas. |
| Extra/RoR | Có thể tối ưu riêng | Cần filter tốt, rủi ro noise. |

## 23. Các lỗi tune thường gặp theo logic Artisan

### 23.1. Output giật khi đổi SV

Nguyên nhân:

1. `beta=1`, P kick mạnh.
2. `gamma=1`, D kick.
3. SV không smooth.

Cách giảm:

1. Giảm beta.
2. Dùng DoM hoặc giảm gamma.
3. Bật SV filter.
4. Bật derivative filter.
5. Dùng Ramp/Soak thay vì nhảy SV.

### 23.2. Overshoot sau khi output max lâu

Nguyên nhân:

1. I-term windup.
2. Ki quá cao.
3. Back-calculation không đủ.
4. Output filter quá chậm.

Cách giảm:

1. Bật IWP.
2. Giảm Ki.
3. Giảm integral limit factor.
4. Bật IRoC nếu hay nhảy SV lớn.

### 23.3. Output rung theo sensor

Nguyên nhân:

1. D quá cao.
2. Sensor noise.
3. Derivative filter tắt.
4. PV là ET/extra curve nhiễu.

Cách giảm:

1. Bật derivative filter.
2. Giảm Kd hoặc Dlimit.
3. Dùng DoM.
4. Làm mượt PV upstream.

### 23.4. PID phản ứng chậm

Nguyên nhân:

1. Kp thấp.
2. Output filter quá chậm.
3. SV lookahead quá thấp với hệ trễ lớn.
4. Duty range bị giới hạn quá hẹp.

Cách tăng:

1. Tăng Kp từng bước.
2. Tăng lookahead.
3. Mở range positive target.
4. Kiểm tra output mapping có thật sự tác động gas không.

## 24. Port sang STM32: nên copy gì?

Vì STM32F103RC RAM chặt, không nên copy nguyên xi Python/Scipy/IIR/gain scheduling bậc hai. Nên chọn theo mức ưu tiên.

### 24.1. Mức 1: Bắt buộc nếu muốn PID ổn

1. Chu kỳ tính cố định 1 giây.
2. Clamp input và output.
3. Anti-windup điều kiện.
4. Back-calculation.
5. D-on-measurement hoặc gamma có thể cấu hình.
6. D limit thật sự dùng macro riêng.
7. Reset/bump-less khi chuyển mode.
8. Debug P/I/D/output gated by `if(enDebug)`.

### 24.2. Mức 2: Nên có

1. `beta/gamma` cấu hình bằng số nguyên scale, ví dụ `0..100`.
2. EMA D filter và output filter.
3. SV lookahead cấu hình.
4. SV smoothing nhẹ.
5. Duty step để tránh ghi HMI/inverter quá dày.

### 24.3. Mức 3: Có thể làm sau

1. Gain scheduling tuyến tính 2 điểm.
2. Lưu/load PID tune từ SD.
3. Register Modbus để Artisan/PC đọc P/I/D/debug term.
4. Cho Artisan ghi Kp/Ki/Kd nếu bật quyền PC control.

### 24.4. Không nên copy trực tiếp

1. `eval()` command parsing.
2. SciPy IIR filter.
3. Numpy polyfit.
4. Cấu trúc dynamic list lớn.
5. External bridge quá tổng quát.

## 25. Đề xuất cấu trúc PID cho CMS nếu nâng cấp

### 25.1. State nhỏ gọn

```cpp
struct ThermalPID {
    int32_t kp;       // x1000
    int32_t ki;       // x1000
    int32_t kd;       // x1000
    int16_t beta;     // 0..100
    int16_t gamma;    // 0..100
    int32_t iTerm;    // output %
    int16_t lastPV10;
    int16_t lastSV10;
    int32_t emaD100;
    int32_t emaOut100;
    bool emaInit;
};
```

### 25.2. Công thức fixed-point đề xuất

Với `PV10`, `SV10` là `0.1°C`:

```text
P = kp * (beta*SV10/100 - PV10) / 10000
I += ki * (SV10 - PV10) * dt / 10000
D = kd * ((gamma*SV10/100 - PV10) - (gamma*lastSV10/100 - lastPV10)) / (10000*dt)
```

Nếu muốn DoM:

```text
gamma = 0
```

Nếu muốn DoE:

```text
gamma = 100
```

### 25.3. Output mapping cho CMS

Cho preheat:

```text
out > 0:
    gas = map(out, 0..100, gasMin..gasMax)
    air = airBase

out < 0:
    gas = 0
    air = map(-out, 0..100, airBase..airMax)
```

Cho roast control hoàn chỉnh sau này:

```text
positiveTarget = GAS hoặc DRUM hoặc custom
negativeTarget = AIR hoặc DAMPER hoặc custom
```

### 25.4. Modbus debug register nên thêm

Nếu RAM/địa chỉ cho phép:

| Register | Ý nghĩa |
|---|---|
| `PID_DBG_SV` | SV x10. |
| `PID_DBG_PV` | PV x10. |
| `PID_DBG_ERR` | Error x10. |
| `PID_DBG_P` | P %. |
| `PID_DBG_I` | I %. |
| `PID_DBG_D` | D %. |
| `PID_DBG_OUT` | Output %. |
| `PID_DBG_FLAGS` | Bit flags: clamp, D spike, I blocked. |

## 26. Đề xuất audit ngay cho code CMS

1. Sửa hoặc xác nhận `PH_PID_DLIMIT` có thật sự dùng trong `Preheat_PID.h`.
2. Kiểm tra tất cả comment bị mojibake trong `include/Define.h`, `include/PID_Airflow.h`, `include/Preheat_PID.h`, `include/Modbus_Slave.h`.
3. Tách debug PID preheat thành chuỗi ngắn, tránh in quá nhiều mỗi giây nếu RAM/Serial yếu.
4. Nếu muốn Artisan ghi PID tune, thêm register có gate bằng `PC_CONTROL_BTN_R`.
5. Không cho PC control mặc định bật khi boot.
6. Không thêm SD/Modbus/Serial trong ISR.

## 27. Checklist hiểu đúng PID Artisan

Trước khi nói "đã dùng PID Artisan", cần trả lời được:

1. Đang dùng PV nào: BT, ET hay extra?
2. SV đến từ đâu: manual, Ramp/Soak, background, HMI, SD profile?
3. Output dương lái gì?
4. Output âm lái gì?
5. `beta/gamma` là bao nhiêu?
6. Có bật D filter không?
7. D limit là bao nhiêu?
8. Có IWP không?
9. Có IRoC không?
10. Duty min/max có đang bó output không?
11. PID có update khi OFF để bumpless không?
12. Khi CHARGE/DROP có auto ON/OFF không?
13. Nếu external PID, Artisan chỉ ghi SV/P/I/D hay tự tính duty?
14. Nếu firmware nhận Artisan qua Modbus, có register nào cho P/I/D không?

## 28. Kết luận cuối

Artisan PID là một framework điều khiển nhiệt thực dụng cho rang cà phê, không chỉ là ba hệ số `Kp/Ki/Kd`. Lõi thuật toán có 2DOF PID, anti-windup, derivative kick protection, filter và gain scheduling. Lớp `PIDcontrol` biến output trừu tượng thành hành động rang qua slider/event hoặc bridge sang PID ngoài.

Đối với CMS STM32, hướng hợp lý là port có chọn lọc:

1. Giữ fixed-point integer.
2. Ưu tiên anti-windup, back-calculation, DoM/gamma, D limit, filter nhẹ.
3. Không đưa Numpy/SciPy/gain scheduling bậc hai.
4. Bổ sung debug term và register có kiểm soát nếu cần tune từ Artisan.

Nói ngắn gọn: bộ số `15 / 0.01 / 20` chỉ là bề mặt. "PID Artisan" thực sự nằm ở cách nó quản lý sai số, trạng thái, giới hạn, setpoint, output và workflow rang.
