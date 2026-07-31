# Quyết định chờ code — chốt với chủ máy 2026-07-30

**Toàn bộ file này là Ý ĐỊNH, chưa có dòng code nào.** Firmware đang chạy trên máy (build +
nạp 30/07/2026) mới có R1–R6; mọi mục dưới đây là **thêm/đổi so với bản đó**. Khi code xong
mục nào thì ghi ngày + chuyển nội dung vào [quy-trinh-chinh.md](quy-trinh-chinh.md) và xoá
khỏi đây, đừng để hai chỗ cùng mô tả một việc.

Nguồn: phiên thảo luận 2026-07-30 với chủ máy, sau khi rà bước 1 và bước 3.

---

## ⛔ 0a. LÀM TRƯỚC TIÊN — hồi quy R7 đang nằm trên máy

Bản vá R2 lớp 2 sáng 30/07 hạ cổng khối DROP xuống `progStep >= STP_CHARGE`, mà đó là bước **chờ
thợ nạp** → auto-drop có thể **mở cửa xả khi lồng còn trống** (hồ sơ ca cao xả thấp hơn nạp,
charge tay giữ nóng 220, hoặc ngay sau nạp khi BT chưa tụt). **Firmware trên máy đang có lỗi
này.** Chi tiết + cách sửa: [rui-ro-va-de-xuat.md](rui-ro-va-de-xuat.md) mục **R7**. Sửa mục này
trước mọi mục khác trong file, và **đừng chạy mẻ AUTO nào** cho tới khi sửa xong.

---

## 0. Hai nguyên tắc chung

**Kẹp về biên gần nhất.** Mọi ô `$M` có dải: nhập ngoài dải thì máy **tự sửa về biên gần
nhất** rồi kêu chuông báo. Ví dụ dải 150–230: nhập 140 → 150, nhập 240 → 230. Lý do chọn kẹp
thay vì từ chối: máy không được đứng giữa ca vì một ô cài sai, và app hiện số mới nên thợ
thấy ngay là bị kéo.

**Chốt chặn thật nằm ở firmware.** App làm nút xám / ô mờ cho thợ dễ hiểu, nhưng HMI ghi
thẳng `$M` được nên **firmware phải tự kẹp lúc nhận** (`Modbus_Master.h`, chỗ tính `_CV`).
Chặn chỉ ở app là chặn nửa vời.

---

## 1. Loại hạt — thanh ghi MỚI `$M17`

`0 = cà phê · 1 = ca cao`. Ô `$M17` và `$M18` là hai ô **duy nhất còn trống** trong 1..52 (đã
tra 30/07: app dùng 50 ô, `iMemHMI[60]` còn chỗ, `DATE_PROFILE_W 17`/`DEL_PROFILE_W 18` thuộc
dãy `40017/40018` khác họ nên không đụng).

Loại hạt quyết định **dải nhiệt nạp**, và dải đó lại quyết định **khi nào cho bấm charge**:

| Loại hạt | Dải nhiệt nạp | Cho bấm charge khi |
|---|---|---|
| Cà phê (0) | 150–230 °C | BT trong 150–230 |
| Ca cao (1) | **130**–230 °C | BT trong 130–230 |

Ngoài dải (dưới sàn **hoặc trên 230**) → nút Nạp hạt trên app **xám, bấm không được**, và
firmware **bỏ qua** lệnh charge kèm chuông báo bị từ chối.

---

## 2. Dải và nhãn tham số

| Ô | Hiện tại | Đổi thành |
|---|---|---|
| `turnGasPoint` (`$M9`) | dải 0–300, mặc định **90** | dải **10–30**, mặc định **20** |
| `chargeTemp` (`$M23`) | dải 0–300, mặc định 200 | **theo loại hạt** (mục 1) |
| Nhiệt charge trong hồ sơ app | `naOpt(...,100,260)` | cùng dải với `$M23` |

**Nhãn `turnGasPoint` phải đổi:** "Nhiệt bật gas" → **"Lùi nhiệt bật gas (dưới nhiệt nạp)"**.
Nó là *khoảng lùi*, không phải nhiệt tuyệt đối — cái tên cũ chính là lý do mặc định bị để 90
(gấp 3–9 lần ý định). Đổi ở cả app, màn HMI, và
[rang-ca-phe/references/registers-M.md](../../rang-ca-phe/references/registers-M.md).

---

## 3. Charge TAY — nút riêng, không gõ 0 nữa

**Cờ:** giữ `chargeTemp = 0` làm cờ "charge tay" (khỏi tốn ô `$M` mới), nhưng thợ **không tự
gõ 0**; app có **nút "Charge tay"** cạnh ô nhiệt nạp, bật nút thì ô nhiệt nạp **xám lại** và
app ghi 0 xuống máy.

**Đổi hành vi so với hiện tại:** bây giờ `chargeTemp == 0` làm máy **nhảy thẳng bước 1 → 5**,
bỏ luôn bước 3 và 4, tức **không mồi lửa, không gia nhiệt** — thợ phải tự bật gas tay
(`Program.h:1557`). Theo quyết định mới, charge tay vẫn đi **đủ 1 → 3 → 4**.

### Charge tay là VÒNG GIỮ NÓNG, không phải quãng leo một chiều

Chốt cuối (30/07, sau khi gỡ hai chỗ tự đá nhau): máy **đốt để giữ lồng nóng chờ thợ nạp**,
dao động trong một dải có trễ (hysteresis):

| Mốc | Máy làm |
|---|---|
| BT **≥ 220 °C** | **tắt lửa** (`START_GAS_BTN_W = 0`), vẫn ở bước 4, để lồng nguội dần |
| BT **< 150 °C** | **mồi lại** — chạy lại chuỗi mồi ở mục 5 |
| BT **> 230 °C** | đã tắt gas mà BT vẫn leo → có vấn đề thật → cắt gas, **cờ lỗi chốt** (mục 6), chờ Xoá lỗi |
| **Không có trần thời gian** | thợ được chờ bao lâu cũng được (trần 5 phút chỉ áp cho charge auto) |

Hai chỗ đã phải gỡ vì tự đá nhau, ghi lại để đừng lặp:
- Ban đầu chốt "charge tay gia nhiệt tới 230, **lố 230 thì báo lỗi**". Nhưng giữ nóng thì máy
  phải **tự tắt lửa ở đầu trên**; nếu chạm 230 là báo lỗi thì mẻ tay nào cũng khoá máy sau vài
  phút. → tách thành **hai số**: 220 tắt lửa, 230 báo lỗi.
- Trần 5 phút từ lúc có lửa sẽ khoá máy đúng lúc máy đang giữ nóng đàng hoàng. → **chỉ áp cho
  charge auto**.

**Còn lại là suy ra, cần chủ máy xác nhận khi code:**
1. Ở **bước 1** với charge tay, ngưỡng chờ nguội lấy **220 °C** (trùng điểm tắt lửa): lồng nóng
   hơn 220 thì gió max chờ nguội tới 220 rồi mới mồi. Không dùng công thức `chargeTemp − lùi
   nhiệt` vì `chargeTemp = 0` cho ra ngưỡng âm → máy đứng vĩnh viễn.
2. Ngưỡng **mồi lại 150** nên đi theo **loại hạt** như dải cho bấm charge (cà phê 150, **ca cao
   130**) để cả máy chỉ có một luật, thay vì hằng số 150 cứng.

### Nút nạp và tín hiệu gọi thợ

- Nút Nạp hạt trên app: **xám** khi BT ngoài dải theo loại hạt, **nhấp nháy** khi BT trong dải.
  Máy **không tự mở cửa nạp** — thợ bấm.
- Máy **kêu một nhịp chuông** lúc BT vào dải, cho thợ đứng ở tủ điện biết (nháy chỉ có trên app
  — chốt "nháy trên app thôi", không sửa màn HMI).

*(Nhắc để khỏi tìm: không có "bước 2" — số 2 là ô trống của một bước đã gỡ. Chuỗi là 1 → 3 → 4.)*

---

## 4. Charge AUTO

- Trong lúc chờ BT leo tới nhiệt nạp, nút Nạp hạt trên app **cũng nhấp nháy** báo đang chờ nạp.
- **Cho bấm charge sớm** (khi BT trong dải theo loại hạt): hồ sơ ghi `BT_CHARGE` **theo đúng
  lúc bấm sớm đó**, đồng hồ mẻ và đường cong chạy từ đó.
  **Đây là bịt lỗ thật, không phải thêm tiện nghi:** hiện tại bấm charge ở bước 4 thì cửa nạp
  mở, hạt vào lồng, nhưng máy vẫn đứng ở bước 4 → đồng hồ mẻ không chạy, mốc charge không ghi,
  đường cong không bật. Mẻ đó mất dữ liệu.
- **Lố nhiệt:** `BT > nhiệt nạp + 10 °C` → **tắt lửa, về bước 1** (chờ nguội rồi mồi lại).
  Khác hiện tại hai điểm: ngưỡng lố **cố định +10** thay cho `5 × chTolerange`, và về **bước 1**
  thay vì bước 0 (bước 0 xoá sạch mốc + clear đồ thị + khoá lại HMI, mà hạt chưa vào lồng thì
  chẳng có gì phải xoá). `chTolerange` vẫn dùng cho cửa sổ bắt nhiệt nạp (±dung sai).
- **Lố 2 lần trong một mẻ → khoá** (cờ lỗi mục 6). Chặn vòng lặp vọt → về 1 → mồi → vọt lại:
  van gas kẹt hở hoặc BT lệch thì máy sẽ đạp vòng đó cả buổi, mỗi vòng một chuỗi mồi, gas đốt thật.

---

## 4a. Bước 1 — gió MAX lúc chờ nguội

Chờ nguội thì **đẩy gió lên 100 %** cho lồng nguội nhanh (máy không có trần gió riêng như trần
gas; `airMin/airMax` trong `AnalogConfig.h` chỉ là dải hiệu chuẩn DAC). Ba việc kèm theo, hai
cái đầu **bắt buộc**:

1. **Hạ gió về mức cũ TRƯỚC khi mồi lửa.** Đủ nguội là máy mở gas mồi ngay — mồi với gió 100 %
   thì **thổi tắt lửa**, mồi hụt 2 lần rồi báo `GASFAIL` oan. Trình tự: đủ nguội → hạ gió về mức
   trước đó → mới bật gas mồi. (Khớp luật xả khí: lúc mồi gió chỉ +10 %, sàn 25 %.)
2. **Tạm chuyển quyền gió sang máy + treo PID áp hút**, y như lúc xả khí (mục 5) — bước 1 không
   chốt `naviSourceAIR` nên gió đang thuộc biến trở; ghi 100 % mà không đổi quyền thì DAC vẫn lấy
   theo biến trở.
3. Hệ quả: **thợ xoay gió lúc chờ nguội sẽ không có tác dụng** cho tới khi đủ nguội. Đã báo với
   chủ máy.

---

## 4b. Bước 4 — chi tiết

Ba chỗ rà ra ở bước 4, **cả ba đã chốt**:

**(1) Gia nhiệt bằng `preGas` mà thợ không can thiệp được → bò chậm.** Bước 3 đặt
`gasPercent = preGas` (mặc định 30 %) rồi bước 4 **không đổi gas nữa**, mà quyền gas latch ở
AUTO nên biến trở và app đều vô hiệu. Charge tay đích 230 °C thì quãng bò càng dài. Nghi đây là
lý do thực tế thợ hay bấm nạp sớm.

→ **CHỐT:** `preGas` đã cài chuẩn, **không nhả quyền cho thợ**. Thay vào đó: chờ **60 giây tính
từ lúc có tín hiệu lửa** mà chưa nạp → **+10 % gas, MỘT LẦN DUY NHẤT** (không bậc thang). Áp cho
cả charge auto và charge tay. Không cần trần `preGas + 30 %` nữa vì `preGas + 10` vốn dưới
`maxGasSet`.

→ **CHỐT:** **bỏ qua cú tăng nếu BT đã vào 10 °C cuối** trước nhiệt nạp. Lý do phải có chốt này:
gas cao hơn thì BT dễ vọt quá `nhiệt nạp + 10` → tắt lửa về bước 1 → **đủ 2 lần là khoá máy**,
tức luật bù gas tự đưa máy vào trạng thái lỗi nếu không chặn ở đoạn cuối.

**(2) Cửa sổ bắt nhiệt nạp là cửa sổ HAI ĐẦU → trượt được.** `chargeTemp ± chTolerange` rộng
đúng 6 °C với dung sai 3; BT leo 2–3 °C/giây thì hai lần đọc liên tiếp nhảy qua cửa sổ, máy
không bắt được, chỉ còn nhánh vọt cứu. **Đúng cái bẫy đã làm hỏng R2.**

→ **CHỐT: đổi sang điều kiện một chiều** `BT ≥ chargeTemp − chTolerange`. Hành vi thực tế không
đổi (máy vốn mở cửa nạp ở mép dưới vì BT đang leo lên), chỉ khác là không thể trượt.

**(3) Bước 4 không có trần thời gian.** Bếp yếu / gió quá lớn / lồng hở → BT cân bằng nhiệt rồi
đứng, không lên cũng không vọt → chờ vô thời hạn, gas vẫn đốt, HMI vẫn báo đang gia nhiệt.

→ **CHỐT: trần 5 phút tính từ lúc có tín hiệu lửa.** Hết 5 phút mà chưa nạp → cắt gas, báo lỗi,
vào cờ lỗi chờ Xoá lỗi.
⚠ **Đã cảnh báo chủ máy, chủ máy vẫn chọn 5 phút:** charge tay đích 230 °C mà lồng còn nguội thì
leo lên 230 có thể **quá 5 phút** → trần này sẽ cắt giữa lúc máy đang làm đúng việc. Nếu chạy
thật mà bị cắt oan thì nới số (một dòng trong `Config.h`). Xưởng luôn sấy lồng trước khi bấm
Start thì 5 phút thoải mái.

**(4) Trend sớm** (`TREND_PRECHARGE_BAND` 10 °C, bật `SAMPLE_COIL_W` trước charge) — chủ máy nói
"bỏ" vì đồ thị app đã luôn ghi từ −30 s. Nhưng đó là **trend của màn HMI**, không phải đồ thị
app. → **CHỐT: chỉ bỏ dòng mô tả khỏi trang tài liệu, GIỮ NGUYÊN CODE** — trend HMI vẫn có đoạn
tiến tới charge.

---

## 4c. Bước 5 — chốt trước khi nhận nạp

Hiện `case STP_CHARGE` chỉ có `if(CHARGE_BTN_R == 1)` — **bấm là nhận, không kiểm gì cả**.

| Tình huống | CHỐT |
|---|---|
| **Cửa xả đang mở** (`DROP_BTN_R == 1`) | **từ chối nạp + chuông**. Máy *không* tự đóng cửa xả — đóng cơ cấu cơ khí mà không nhìn thấy hiện trường có thể kẹp tay thợ |
| **Trống/quạt chưa chạy** (`DRUM_FAN_BTN_R == 0`) | **máy tự bật rồi nhận nạp** (vô hại, đúng tinh thần chốt cưỡng chế bật trống khi BT > 80 °C) |
| **BT ngoài dải theo loại hạt** | firmware bỏ qua lệnh + chuông; nút trên app xám (mục 1) |
| **Phễu rỗng / cân không có hạt** | **KHÔNG kiểm** — chủ máy chốt bỏ qua, mẻ rỗng là việc của app |

**Xi-lanh nạp `chargeDuration` ($M1): sàn 10 giây** (dải 10–60), **mặc định đổi 5 → 10**.
⚠ Theo luật kẹp về biên, **máy đang cài 5 sẽ bị kéo lên 10** → cửa nạp mở lâu gấp đôi hiện nay.
Đã báo chủ máy; chưa nghe phản hồi ngược nên giữ 10.

**Việc code, không cần chủ máy quyết:** toàn bộ khối ghi mốc + mở cửa + bật đồng hồ đang nằm
trong `case STP_CHARGE`; vì bước 4 giờ cũng nhận lệnh nạp (cho bấm sớm) nên phải **gom thành một
hàm `doCharge()` dùng chung** — chép hai bản là kiểu bug sửa một chỗ quên chỗ kia. Dọn kèm:
`buzzerTimerEn = 1` đang set **hai lần** trong cùng khối (`Program.h` 1653 và 1668).

---

## 5. Chuỗi mồi lửa

### Bếp NP (`burnerPremix = 0`) — mồi 2 lần, nhịp 10 giây

| Giây | Máy làm |
|---|---|
| 0 | Bật relay gas, **gas 50 %** — lần mồi 1, chờ 10 giây |
| 10 | Chưa có lửa → **tắt gas, xả khí 10 giây** |
| 20 | Bật lại relay, **gas 60 %** — lần mồi 2, chờ 10 giây |
| 30 | Vẫn không lửa → **cắt gas, tắt Start, mở khoá HMI**, chuông, nhãn `GASFAIL`, về bước 0 và đứng đó |

Bắt được lửa ở bất kỳ điểm nào → hạ gas về `preGas`, sang bước 4. Không có lần mồi thứ ba.

**Xả khí 10 giây:** gió **+10 %** so với mức đang chạy (2 bậc 5 %: 30→40, 40→50), **không dưới
25 %**, trên 90 % thì kẹp 100; xong trả gió về mức cũ. Hai việc bắt buộc kèm theo, nếu không
luật này vô hiệu:
1. **Tạm chuyển quyền gió sang máy** trong 10 giây đó — bước 1 và 3 không chốt `naviSourceAIR`,
   nên gió đang thuộc biến trở (hoặc app khi PC control); ghi `airflowPercent` mà không đổi
   quyền thì DAC vẫn lấy theo biến trở.
2. **Treo PID áp hút 10 giây** bằng cờ nội bộ, xả xong nhả ra + `pidAirflowReset()`. PID ghi
   `airflowPercent` mỗi vòng (`PID_Airflow.h:449`) nên sẽ kéo gió về trong vòng 1 giây.
   **Không đụng cờ "bật/tắt PID hút" của thợ** — app không được thấy nhấp nháy.

**Trần 60 giây (`PH_IGNITE_TMO`) giữ lại làm lớp ngoài**, phòng cảm biến lửa chập chờn làm
chuỗi mồi không thoát được.

### Bếp premix (`burnerPremix = 1`) — mồi 1 lần, không thử lại

Hiện tại premix **không kiểm tra cảm biến lửa**, mở gas là đi thẳng bước 4 → bếp bị khoá thì
máy treo ở "BT HEATUP" vô thời hạn, HMI vẫn báo đang gia nhiệt. (Có lớp đỡ: `pclSafety()`
trong PC_Link cắt gas sau 75 giây nếu relay gas bật mà không thấy lửa — nhưng nó chỉ đóng gas,
không gỡ máy ra khỏi bước 4.)

Đổi thành: chờ cảm biến lửa **65 giây** (dùng lại `PH_IGNITE_TMO_PREMIX`, premix mồi chậm
~40 giây nên phải cho rộng). Không có lửa → **bộ điều khiển bếp đã tự khoá**: cắt gas, tắt
Start, chuông, nhãn `BURNER LOCK`, và báo rõ **"bấm nút đỏ RESET BURNER trên cửa tủ điện"**.
**Không thử lại** — thử bằng phần mềm không có tác dụng khi bếp đã khoá cứng.

App cũng phải hiện câu nhắc đó ở badge mồi hụt (app đang có badge đỏ "Mồi hụt!" theo cờ
`flame_fail`, chỉ cần thêm câu chỉ việc).

### Sau khi có lửa — ĐÃ ĐÚNG SẴN, đừng sửa

Yêu cầu "về đúng `preGas`, thợ đổi cũng không được" **firmware đang làm đúng**: bước 3 chốt
`naviSourceGAS = SOURCE_AI_AUTO`, biến này **được latch** — khối điều hướng cuối `programScan()`
chỉ đổi hướng khi source **khác** AUTO (`Program.h:2327`). Nên suốt bước 3–4, biến trở của thợ
**và** lệnh gas từ app đều không chen vào được; bảng gas AUTO theo hồ sơ chỉ chạy sau khi nạp
(`timeRoastEn`) nên cũng không đè.

Còn **một lỗ nhỏ chưa quyết**: `preGas` ghi vào gas **một lần** lúc chuyển bước, nên thợ xoay
`preGas` trong lúc máy đang ở bước 4 thì phải sang mẻ sau mới ăn. Muốn "cài là ăn liền" thì
ghi lại mỗi vòng quét — 1 dòng. **Chờ chủ máy chốt.**

---

## 6. Cờ lỗi chốt + nút Xoá lỗi (`$M18`)

- Firmware giữ một **cờ lỗi latch**. Đang chốt thì **không nhận Start** — bấm Start cũng không
  chạy, HMI hiện nhãn lỗi.
- Kích cờ này: charge tay lố 230 (mục 3), charge auto lố 2 lần (mục 4).
- **Nút "Xoá lỗi" CHỈ đặt ở app** (chốt của chủ máy). Ghi `$M18 = 1` → firmware xoá cờ rồi tự
  đưa `$M18` về 0.
- Ô `$M18` đi qua khối cấu hình PC_Link, mà khối đó **chạy độc lập với nút "PC control"**
  (`pcLinkConfigTask()` gọi mọi vòng) → app xoá được lỗi kể cả khi máy không cho app điều khiển.
- **Chấp nhận:** app không chạy (máy tính tắt, mất cáp) thì lỗi **không xoá được** — phải mở app
  hoặc tắt nguồn máy. Chủ máy đã đồng ý.
- **KHÁC nút đỏ RESET BURNER trên cửa tủ**: nút đỏ reset *bộ điều khiển bếp premix* (phần cứng,
  firmware không chạm tới). Bếp premix khoá thì phải bấm **cả hai**.

---

## 7. Dọn dẹp kèm theo

**Bước 1 đang dội bus Modbus:** nhánh "chưa đủ nguội" ghi `START_GAS_BTN_W = 0` **mỗi vòng
quét** (`Program.h:1555`), chờ nguội mấy phút là mấy nghìn khung ghi thừa. Đổi thành ghi **một
lần** khi trạng thái đổi — cùng loại việc đã dọn hồi siết loop 210 ms → 130 ms.

---

## Nơi phải sửa — checklist

| Chỗ | Việc |
|---|---|
| `include/Define.h` | thêm `$M17` loại hạt, `$M18` xoá lỗi; biến cờ lỗi latch, bộ đếm lố, bộ đếm chuỗi mồi |
| `include/Modbus_Master.h` | kẹp dải lúc nhận `$M`; đọc `$M17/$M18`; xoá cờ lỗi |
| `include/Program.h` | bước 1 (ghi tắt gas 1 lần), bước 3 (chuỗi mồi NP/premix + xả khí), bước 4 (nháy/chuông, cho charge sớm, lố +10 → bước 1, đếm 2 lần), charge tay đi đủ 1→3→4, chặn charge ngoài dải |
| `include/PID_Airflow.h` | cờ treo PID 10 giây lúc xả khí |
| `include/Config.h` | hằng số: `CHARGE_KEEPWARM_OFF 220` / `CHARGE_MANUAL_FAULT 230`, `CHARGE_OVERSHOOT 10`, `CHARGE_OVERSHOOT_MAX 2`, `CHARGE_WAIT_TMO 300` (5 phút, chỉ auto), `CHARGE_GAS_BUMP 10` + `CHARGE_BUMP_AFTER 60` + `CHARGE_BUMP_SKIP_BAND 10`, `HEATUP_AIR_MAX 100`, nhịp mồi 10 s, xả khí 10 s, gió xả `+10 %`/sàn 25 % |
| `OTL Roast Lab.html` | dải + nhãn `turnGasPoint`/`chargeTemp`; ô chọn loại hạt; nút "Charge tay"; nút Nạp hạt xám/nháy theo dải; nút "Xoá lỗi"; câu nhắc RESET BURNER ở badge mồi hụt |
| Màn HMI (DOPSoft) | siết dải nhập `$M9`/`$M23`; đổi nhãn; thêm nhãn lỗi `GASFAIL`/`BURNER LOCK` |
| `protocol/pc_link.json` | nếu cần đẩy cờ lỗi/loại hạt sang app qua khối đọc → sinh lại bằng `gen_pc_link.py` |
| skill `rang-ca-phe` | bảng `$M`: thêm 17/18, đổi nhãn 9 |
| skill này | chuyển từng mục sang `quy-trinh-chinh.md` khi code xong |
| `html/ref/quy-trinh-rang.html` | trang tài liệu: bỏ dấu 🔧 khi mục đó đã chạy thật |

---

## Còn mở, chưa chốt

1. **`preGas` có ghi lại mỗi vòng quét không** (mục 5, cuối).
2. **Gas mồi có cho thợ cài không** — phương án thêm `$M` "Gas mồi lúc rang" (mặc định 50).
   **Tạm hoãn:** chuỗi mồi mới đã cố định 50/60, thêm ô cài ngay lúc này sẽ rối; chạy thử vài
   mẻ thấy cần thì thêm.
3. **Ca cao thực tế nạp quanh bao nhiêu độ** — chủ máy chưa trả lời. Không chặn việc code vì
   dải ca cao đã mở xuống 130.
4. **Sấy lồng có hay mồi hụt lần đầu không** — để biết số 30 % của `preheat()` là đủ hay thiếu
   (luồng rang mồi ở 50 %, hai chỗ lệch nhau mà cùng một cái bếp).
