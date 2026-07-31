# Kế Hoạch Sửa Auto Replay Profile Rang

## Mục Tiêu

Nâng cấp chế độ rang auto để máy có thể chạy lại profile phức tạp hơn, bao gồm:

- BT sau TP có thể tăng, giảm, rồi tăng lại trước khi DROP.
- Thợ rang có thể tắt lửa thật trong một đoạn rang, sau đó bật lại.
- Auto không DROP sớm chỉ vì BT chạm nhiệt DROP trước thời điểm DROP mẫu.
- File CSV cũ vẫn đọc được để không làm hỏng profile đang dùng.

## Hiện Trạng Code

Chế độ auto hiện tại chạy theo profile SD theo từng giây:

- `sdGas[t]`, `sdAirflow[t]`, `sdDrum[t]`: lấy lại gas, gió, trống từ profile.
- `sdBT[t]`: dùng làm BT mục tiêu để bù gas sau TP.
- `DROP_PRO_R`: dùng làm điều kiện auto drop theo nhiệt.

Điểm yếu chính:

- Auto drop chỉ dựa vào `Temperature_BT >= DROP_PRO_R`, nên có thể DROP sớm nếu profile có đoạn BT vượt nhiệt DROP trước thời điểm DROP thật.
- CSV chỉ lưu `Burner(%)`, chưa lưu trạng thái bật/tắt lửa thật.
- Khi profile gas = 0%, thuật toán bù gas vẫn có thể tự cộng gas nếu BT thật thấp hơn BT profile.
- Phase `DRY End`, `FCs`, `DROP` hiện thiên về ngưỡng nhiệt, chưa đủ tốt cho profile BT không đơn điệu.

## Nguyên Tắc Thiết Kế

- Không sửa file CSV cũ khi chạy auto.
- Không dùng `String`, không thêm buffer lớn.
- Không thêm SD, Modbus, Serial vào ISR.
- Giữ tương thích CSV cũ: nếu thiếu cột mới thì dùng hành vi cũ hoặc hành vi an toàn.
- Ưu tiên điều kiện theo thời gian profile cho các sự kiện đã lưu từ mẻ mẫu.
- Chỉ cho phép auto drop khi đã gần hoặc vượt thời điểm DROP mẫu.

## Ghi Chú Tương Thích CSV Cũ

Kế hoạch này không được làm hỏng hoặc tự ý chuyển đổi file CSV cũ.

- Khi chạy auto hoặc load profile, firmware chỉ đọc CSV, không ghi đè CSV gốc.
- Chỉ khi người dùng chạy manual save vào đúng slot thì file CSV của slot đó mới bị ghi mới.
- CSV cũ không có cột `GasOn` vẫn phải đọc được theo format cũ.
- CSV mới có cột `GasOn` phải đọc được theo format mới.
- Parser phải phát hiện cột theo header, không được giả định cứng vị trí làm lệch `Drum(%)`, `VacFlag`, `VacSP(Pa)`.
- Parser phải bỏ qua các cột lạ không dùng, ví dụ `Start`, `Charge`, `Drop`, `Vacuum(Pa)`, `VS(Pa)` từ log ngoài hoặc file test.
- File CSV thiếu `CHARGE`, thiếu `Time2` sau CHARGE, hoặc thiếu `DROP` vẫn phải báo profile không hợp lệ, không được ép chạy auto.

Ví dụ file log chỉ có `TP`, toàn bộ `Time2` rỗng, không có `CHARGE` và `DROP` không phải profile auto hợp lệ. Firmware phải giữ nguyên file đó và báo load fail thay vì sửa nội dung file.

## Thiết Kế CSV Mới

Giữ các cột hiện tại:

```text
Time1	Time2	ET	BT	Event	Air(%)	Burner(%)	Drum(%)	VacFlag	VacSP(Pa)
```

Đề xuất thêm cột sau `Burner(%)` hoặc cuối dòng:

```text
GasOn
```

Nguồn dữ liệu chính để ghi cột này là:

```cpp
START_GAS_BTN_R
```

Giá trị:

- `1`: lửa/bếp đang bật.
- `0`: yêu cầu tắt lửa thật.
- Rỗng hoặc thiếu cột: tương thích profile cũ, suy luận theo chế độ hiện tại.

Header mới đề xuất:

```text
Time1	Time2	ET	BT	Event	Air(%)	Burner(%)	GasOn	Drum(%)	VacFlag	VacSP(Pa)
```

Lý do đặt `GasOn` ngay sau `Burner(%)`: dễ hiểu khi đọc log và dễ kiểm tra thao tác lửa.

## Dữ Liệu Cần Thêm Trong RAM

Thêm mảng nhỏ theo profile:

```cpp
uint8_t sdGasOn[PROFILE_MAX_SECONDS];
```

Giá trị:

- `0`: tắt lửa thật.
- `1`: bật lửa.
- `2`: không có dữ liệu, dùng tương thích cũ.

Nếu RAM cần tiết kiệm hơn, có thể dùng bitset, nhưng giai đoạn đầu nên dùng `uint8_t` để code rõ và ít rủi ro. Với `PROFILE_MAX_SECONDS` khoảng 1500, tăng RAM khoảng 1.5 KB.

## Logic Ghi Profile Manual Save

Khi ghi CSV trong `sdLogWrite()`:

- Ghi thêm `GasOn`.
- `GasOn` lấy trực tiếp từ `START_GAS_BTN_R`.
- Khi `START_GAS_BTN_R == 1`, ghi `GasOn = 1`.
- Khi `START_GAS_BTN_R == 0`, ghi `GasOn = 0`.
- Nếu phần cứng không có gas control thật, ghi `1` khi `gasPercent > 0`, ghi `0` khi `gasPercent == 0`.

Ví dụ dòng mới:

```text
05:20	05:00	180.5	165.2		45.0	20.0	1	70.0	0	0
06:00	05:40	182.0	166.0		50.0	0.0	0	70.0	0	0
```

## Logic Đọc Profile

Trong `sdRead()`:

- Parser cần nhận cả CSV cũ và CSV mới.
- Nếu header có `GasOn`, đọc cột đó vào `sdGasOn[t]`.
- Nếu không có `GasOn`, set `sdGasOn[t] = 2`.
- Sửa lỗi đọc ET để ET thống nhất đơn vị x10 như BT.
- Đọc cột theo tên header, không theo vị trí tuyệt đối, để CSV có thêm cột lạ vẫn không làm lệch dữ liệu chính.
- Các cột bắt buộc cho auto vẫn là `Time1`, `Time2`, `ET`, `BT`, `Air(%)`, `Burner(%)`, `Drum(%)`; `GasOn`, `VacFlag`, `VacSP(Pa)` là cột mở rộng có fallback.

Quy tắc tương thích:

```text
GasOn thiếu:
  sdGasOn[t] = 2
  auto giữ hành vi cũ

GasOn = 0:
  auto tắt lửa thật, không cho bù gas tự cộng lại

GasOn = 1:
  auto cho phép burner theo profile và cho phép bù gas nếu cần
```

## Logic Auto Gas

Trong `calibProgram()`:

1. Lấy dữ liệu nền theo thời gian:

```cpp
gasPercent = sdGas[lastTimeSD];
```

2. Nếu `sdGasOn[lastTimeSD] == 0`:

- Ghi tắt `START_GAS_BTN_W - 1`.
- Ép `gasPercent = 0`.
- Không chạy bù gas BT trong giây đó.
- Có thể set status riêng để HMI biết đang tắt lửa theo profile.

3. Nếu `sdGasOn[lastTimeSD] == 1`:

- Ghi bật `START_GAS_BTN_W - 1` nếu `START_GAS_BTN_R == 0`.
- Cho phép bù gas như hiện tại.

4. Nếu `sdGasOn[lastTimeSD] == 2`:

- Chạy tương thích cũ.

## Giai Đoạn Nhạy Cảm Nhiệt

Đặt tên giai đoạn:

```text
Giai đoạn nhạy cảm nhiệt
```

Bắt đầu từ mốc chung:

```text
BT >= 180°C
```

Trong code:

```cpp
Temperature_BT >= 1800
```

Từ mốc này trở đi, cà phê được xem là bắt đầu nhạy hơn với nhiệt lượng lớn. Auto không được chỉ nhìn sai lệch BT để tăng gas, mà phải so thêm RoR BT hiện tại với RoR BT gốc trong profile.

Đơn vị RoR trong code đang dùng dạng x10. Vì vậy:

```text
2.0°C/phút = 20
```

Đề xuất cho thuật toán bù gas:

- Nếu `Temperature_BT < 1800`, cho phép bù gas như logic hiện tại.
- Nếu `Temperature_BT >= 1800`, bắt đầu giới hạn mức tăng gas theo RoR.
- Nếu `Temperature_BT >= 1800` và `rorBT` hiện tại cao hơn `sdRorBT[lastTimeSD]` từ `2.0°C/phút` trở lên, không được phép bù nhiệt thêm.
- Khi bị khóa bù nhiệt vì RoR cao, giữ gas theo nền profile hiện tại, không cộng `numIncGas`.
- Khi bị khóa bù nhiệt, phải bỏ qua cả giá trị `numIncGas` cũ còn sót từ chu kỳ trước để tránh vẫn tăng gas ngoài ý muốn.
- Nếu `Temperature_BT >= 1800` và BT đang đúng hoặc cao hơn profile, ưu tiên giảm/giữ gas để tránh RoR lao quá cao.

Mục tiêu là tránh tình huống auto bị trễ thời gian, tăng gas mạnh để bắt kịp BT, làm RoR vượt profile ở vùng nhạy nhiệt.

Pseudo logic:

```cpp
bool sensitiveHeat = ((int16_t)Temperature_BT >= 1800);
int16_t rorOver = rorBT - sdRorBT[lastTimeSD];

if (sensitiveHeat && rorOver >= 20) {
    allowBtCatchupGasBoost = false;
    gasBoostForThisTick = 0;
}
```

## Luật RoR Sau FCs

Sau FCs vẫn được phép bù nhiệt nếu BT đang trễ profile. Tuy nhiên bù nhiệt không được làm RoR BT hiện tại vượt RoR BT gốc quá `2.0°C/phút`.

Đề xuất dùng cùng ngưỡng RoR guard:

```text
AUTO_ROR_OVER_LIMIT_SENSITIVE = 2.0°C/phút
AUTO_ROR_OVER_LIMIT_POST_FCS  = 2.0°C/phút
```

Trong code:

```text
AUTO_ROR_OVER_LIMIT_SENSITIVE = 20
AUTO_ROR_OVER_LIMIT_POST_FCS  = 20
```

Luật sau FCs:

- Nếu chưa qua FCs nhưng `Temperature_BT >= 1800`, chỉ bù nhiệt khi `rorBT < sdRorBT[lastTimeSD] + 20`.
- Nếu đã qua FCs, chỉ bù nhiệt khi `rorBT < sdRorBT[lastTimeSD] + AUTO_ROR_OVER_LIMIT_POST_FCS`.
- Nếu sau FCs mà RoR BT hiện tại cao hơn RoR BT gốc từ `2.0°C/phút` trở lên, không được bù nhiệt thêm, dù BT đang trễ profile.
- Khi không được bù nhiệt, giữ gas theo profile nền hoặc theo mức gas đã bị giới hạn, không tăng thêm bằng `numIncGas`.
- Trạng thái "đã qua FCs" nên dựa vào `progStep >= STP_DEV` hoặc event/time FCs đã load từ profile, không chỉ dựa vào ngưỡng nhiệt tức thời.

Mục tiêu là vẫn cho máy kéo BT khi bị chậm, nhưng không bù lố làm RoR cao hơn profile quá nhiều trong đoạn sau FCs.

## Logic Auto Drop Mới

Không nên drop chỉ vì BT đạt `DROP_PRO_R`.

Đề xuất điều kiện mới:

```text
timeRoast >= dropProfileSec - dropEarlyWindow
AND Temperature_BT >= DROP_PRO_R
```

Trong đó:

- `dropProfileSec`: thời điểm DROP lấy từ profile, đang có `rtDROP` khi load.
- `dropEarlyWindow`: cửa sổ cho phép drop sớm, ví dụ 10 đến 20 giây.

Nếu muốn replay đúng kiểu thợ rang hơn, có thể dùng thêm timeout:

```text
Nếu timeRoast >= dropProfileSec + dropLateTimeout:
  báo status quá thời gian profile
  tùy cấu hình: auto drop hoặc chờ người vận hành
```

Đề xuất cấu hình ban đầu:

- `dropEarlyWindow = 10s`
- `dropLateTimeout = 60s`
- Khi quá timeout: báo lỗi/status, chưa tự drop nếu chưa được xác nhận yêu cầu vận hành.

## Logic Phase Theo Profile

Với profile BT tăng/giảm, phase nên ưu tiên thời gian đã lưu:

- `TP_PRO_M_R/S_R`: thời điểm TP mẫu.
- `DE_PRO_M_R/S_R`: thời điểm Dry End mẫu.
- `FCS_PRO_M_R/S_R`: thời điểm FCs mẫu.
- `DROP_PRO_M_R/S_R`: thời điểm DROP mẫu.

Đề xuất:

- Auto vẫn có thể dùng nhiệt để phát hiện nếu profile bình thường.
- Nhưng nếu chạy chế độ replay nâng cao, phase event nên khóa theo thời gian profile hoặc theo event trong CSV.
- Không nên cho `DRY End`/`FCs` nhảy sớm quá xa so với thời gian mẫu chỉ vì BT chạm ngưỡng.

## Chế Độ Vận Hành Đề Xuất

Thêm một tùy chọn cấu hình:

```text
AUTO_REPLAY_MODE
```

Các mode:

- `0`: hành vi cũ, drop theo nhiệt.
- `1`: drop theo nhiệt + cửa sổ thời gian profile.
- `2`: replay theo event/time profile, phù hợp profile BT lên xuống.

Nếu không muốn thêm HMI setting ngay, có thể compile-time bằng macro trước:

```cpp
#define AUTO_REPLAY_PROFILE_TIMED_DROP 1
```

## Thứ Tự Triển Khai

### Giai Đoạn 1: Sửa Rủi Ro Nền

- Bỏ `SerialBluetooth.available()` ra khỏi `timerPoll_1000ms()`.
- Guard chia cho 0 trong dự đoán YL/FCS khi `rorBT/10 == 0`.
- Sửa đọc ET CSV về đơn vị x10.
- Chặn auto start/drop khi profile load fail hoặc `DROP_PRO_R == 0`.

### Giai Đoạn 2: Timed Drop

- Lưu `dropProfileSec` sau khi load CSV/TXT.
- Đổi auto drop từ chỉ theo nhiệt sang nhiệt + thời gian.
- Thêm status khi quá thời gian profile.
- Kiểm tra profile cũ vẫn chạy được.

### Giai Đoạn 3: GasOn Trong CSV

- Thêm cột `GasOn` khi manual save, lấy từ `START_GAS_BTN_R`.
- Parser đọc được cả format cũ và mới.
- Thêm `sdGasOn[]`.
- Trong auto, nếu `GasOn == 0` thì ghi `START_GAS_BTN_W - 1 = 0`, tắt lửa thật và khóa bù gas.
- Trong auto, nếu `GasOn == 1` thì ghi `START_GAS_BTN_W - 1 = 1` khi cần bật lại lửa.

### Giai Đoạn 4: Replay Event Theo Thời Gian

- Dùng event `CHARGE`, `TP`, `DRY End`, `FCs`, `DROP` từ CSV để điều khiển phase.
- Cho phép profile BT tăng/giảm mà không làm phase/drop nhảy sớm.
- Thêm tùy chọn chọn mode nếu HMI còn địa chỉ trống.

### Giai Đoạn 5: RoR Guard Cho Vùng Nhạy Nhiệt

- Từ `Temperature_BT >= 1800`, bật luật "giai đoạn nhạy cảm nhiệt".
- So sánh `rorBT` hiện tại với `sdRorBT[lastTimeSD]`.
- Nếu `rorBT` cao hơn RoR profile từ `2.0°C/phút` trở lên, khóa bù gas tăng thêm.
- Sau FCs vẫn cho bù nhiệt, nhưng cũng khóa bù nếu `rorBT` cao hơn RoR profile từ `2.0°C/phút` trở lên.
- Kiểm tra tình huống mẻ auto bị chậm 30 giây nhưng RoR đã cao hơn profile: máy phải giữ gas nền, không tiếp tục cộng bù nhiệt.

## Test Cần Làm

### Test Build

```powershell
pio run -e genericSTM32F103RC
pio run -e genericSTM32F103RC --target size
```

Ghi lại RAM/Flash sau mỗi giai đoạn.

### Test Profile Cũ

- Load CSV cũ không có `GasOn`.
- Xác nhận `FA_SUC = 1`.
- Auto vẫn chạy như trước, trừ timed drop nếu bật mode mới.

### Test Profile BT Lên Xuống

Tạo profile mẫu:

```text
BT lên 200°C ở phút 10
BT giảm về 190°C ở phút 12
DROP thật ở phút 15 tại 198°C
```

Kỳ vọng:

- Máy không drop ở phút 10.
- Máy chỉ được xét drop khi gần phút 15.

### Test Tắt Lửa Giữa Mẻ

Tạo profile:

```text
Phút 6: GasOn=0, Burner=0
Phút 7: GasOn=1, Burner=20
```

Kỳ vọng:

- Phút 6 máy tắt lửa thật.
- Thuật toán bù gas không tự cộng gas trong đoạn `GasOn=0`.
- Phút 7 máy bật lại theo profile.

### Test Mẻ Auto Dài Hơn Profile

- Profile DROP ở phút 20.
- BT thật chưa đạt DROP ở phút 20.

Kỳ vọng:

- Máy không đọc tràn mảng.
- Gas/gió/trống giữ dòng cuối profile.
- Có status cảnh báo nếu vượt `dropLateTimeout`.

### Test RoR Guard Vùng Nhạy Nhiệt

Tạo tình huống:

```text
BT thật >= 180°C
BT thật đang thấp hơn BT profile nên có nhu cầu bù gas
RoR BT thật cao hơn RoR BT profile >= 2.0°C/phút
```

Kỳ vọng:

- Auto không cộng bù gas bằng `numIncGas`.
- Gas giữ theo nền profile hoặc mức đã bị giới hạn.
- Nếu RoR BT thật giảm xuống dưới ngưỡng, auto mới được bù gas lại nếu BT vẫn trễ.

### Test RoR Guard Sau FCs

Tạo tình huống:

```text
Đã qua FCs
BT thật đang trễ profile
RoR BT thật cao hơn RoR BT profile >= 2.0°C/phút
```

Kỳ vọng:

- Auto vẫn được phép bù nhiệt sau FCs khi RoR chưa vượt ngưỡng.
- Nếu RoR vượt ngưỡng `2.0°C/phút`, auto dừng bù thêm để tránh bù lố.

## Rủi Ro Cần Xác Nhận Trước Khi Code

- Xác nhận `START_GAS_BTN_R` là trạng thái lệnh bật/tắt lửa đúng để lưu vào profile.
- Xác nhận khi auto ghi `START_GAS_BTN_W - 1` thì trình tự bật/tắt bếp trên cả NP và premix vẫn an toàn.
- `READ_CH1` vẫn có thể dùng như phản hồi bếp cháy, nhưng không dùng làm dữ liệu profile chính.
- HMI còn địa chỉ để thêm mode replay hoặc timeout không.
- Khi quá thời gian profile mà BT chưa đạt drop, hành vi mong muốn là báo lỗi, chờ người vận hành, hay tự drop.
- Với bếp premix và NP, thao tác tắt/bật lửa giữa mẻ có trình tự an toàn khác nhau không.

## Kết Luận

Code hiện tại phù hợp với profile BT sau TP tăng dần đến DROP. Để hỗ trợ phong cách rang nâng cao như BT lên/xuống và tắt lửa giữa mẻ, cần đổi auto từ logic "đạt nhiệt là qua bước/drop" sang logic có nhận thức về thời gian/event của profile, đồng thời bổ sung trạng thái `GasOn` để phân biệt gas 0% với tắt lửa thật.
