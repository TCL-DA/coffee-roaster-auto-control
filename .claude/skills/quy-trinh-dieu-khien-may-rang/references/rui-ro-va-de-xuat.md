# Rủi ro kẹt & đề xuất — việc còn mở

Rà từ code `programScan()` ngày 2026-07-30. **R1–R6 ĐÃ CODE hết ngày 2026-07-30, firmware build OK
(RAM 81,4%) — CHƯA NẠP MÁY THẬT, chưa commit.** Phần "Đề xuất" của mỗi mục giữ lại làm hồ sơ
quyết định; đọc dòng tiêu đề để biết đã làm theo phương án nào. Mỗi mục ghi rõ triệu chứng để đối chiếu với hiện tượng máy thật, và phương án đề xuất để chủ máy chốt.

Trạng thái: 🔴 chưa quyết · 🟡 đã chốt phương án, chưa code · 🟢 đã code

---

## R1 · `STP_GAS` chờ lửa vô thời hạn 🟢 ĐÃ CODE 2026-07-30

**Triệu chứng máy thật**: bấm Start, lồng nguội xong, nghe tiếng gas mở nhưng HMI đứng ở `WAITGAS` mãi. Gas vẫn ở 50 % từ `STP_COOL_DOWN` mà không có lửa → xả gas không cháy vào buồng đốt.

**Nguyên nhân**: bếp thường (`burnerPremix_R == 0`) chờ `READ_CH1 == LOW` mà không có trần thời gian. Trong khi đó `preheat()` **đã có** chốt `PH_IGNITE_TMO` (65 giây, nới cho bếp premix mồi chậm ~40 s) — quy trình rang thiếu đúng chốt tương đương.

**Đề xuất**: đếm `gasWaitTi` từ lúc vào `STP_GAS`; quá `PH_IGNITE_TMO` (dùng lại cùng hằng số cho nhất quán) mà `READ_CH1` chưa LOW → `START_GAS_BTN_W = 0`, `gasPercent = 0`, `setMachineStatus` mã lỗi mồi hụt, và **về `STP_DATA`** (không tự thử lại vô hạn — mồi hụt lặp lại là dấu hiệu hỏng bếp, cần người xem).

Cần chốt: có tự thử mồi lại 1 lần trước khi báo lỗi, hay báo lỗi ngay?

---

## R2 · `STP_TP` không bắt được TP → máy không tự xả 🟢 ĐÃ CODE 2026-07-30 (cả 2 lớp)

**Đây là mục nặng nhất.**

**Triệu chứng**: mẻ chạy bình thường, HMI đứng ở `WAIT TP` suốt mẻ, các mốc DE/FCs không hiện, và **auto-drop không kích** dù BT đã vượt `DROP_PRO_R` → hạt cháy tới khi thợ bấm xả tay.

**Nguyên nhân**: điều kiện xét TP là `timeRoast > ulimitTPTime && BT < ulimitTPTemp`. Hai chặn này là AND, nên nếu BT leo qua `ulimitTPTemp` **trước** khi `timeRoast` vượt `ulimitTPTime` (mẻ nhẹ, lồng nóng, hoặc `ulimitTPTime` cài quá dài) thì cửa sổ xét không bao giờ mở. Hậu quả lan sang khối DROP vì nó gác `progStep >= STP_YELLOW`.

**Đề xuất — 2 lớp, làm cả hai**:
1. **Cứu TP**: khi `timeRoast > ulimitTPTime` mà `BT ≥ ulimitTPTemp` (tức đã trượt cửa sổ) → chốt TP theo `BT_TP_Pre` đang giữ, ghi event `"TP"` kèm cờ "TP suy đoán" để hồ sơ biết số này không chắc, rồi sang `STP_YELLOW`. Lý do chọn cách này: `BT_TP_Pre` vẫn là đáy thật đã ghi được, chỉ là chưa thấy nhịp bật lên.
2. **Chốt an toàn độc lập**: hạ điều kiện khối DROP từ `progStep >= STP_YELLOW` xuống `progStep >= STP_CHARGE`. Auto-drop khi `BT ≥ DROP_PRO_R` phải đúng bất kể máy có bắt được mốc hay không — cháy mẻ vì không bắt được TP là không đáng.

**Đã bớt một phần phía app (2026-07-30):** app OTL Roast Lab từng gác luôn ngưỡng xả
theo mốc TP (`checkMileSets` thoát sớm khi `mileT.TP == null`), mà ở chế độ pclink mốc TP
lại suy từ `progStep = 7` — nên đúng lỗi này làm **mất cả hai lớp bảo vệ cùng lúc**. Đã bỏ
chốt đó: ngưỡng xả của app giờ là lưới độc lập, không phụ thuộc firmware có bắt được TP
hay không. **Firmware vẫn chưa sửa** — hai lớp đề xuất dưới đây còn nguyên giá trị.

Cần chốt: lớp 2 có làm luôn không (nó đổi hành vi ở YELLOW/FCS — về lý thuyết BT không thể tới `DROP_PRO_R` trước khi qua các mốc đó, nên rủi ro thấp).

---

## R3 · `STP_DEV` không có trần thời gian 🟢 ĐÃ CODE 2026-07-30 (báo, không tự xả)

**Triệu chứng**: `DROP_PRO_R` cài 0 hoặc quá cao → DEV chạy mãi, không tự xả.

**Đề xuất**: trần DEV theo **tỉ lệ** thay vì giây tuyệt đối cho khớp cách thợ nghĩ — ví dụ `PER_DEV_SAVE` vượt ngưỡng `maxDevPercent` (thanh ghi `$M` mới, mặc định 300 = 30 %) → buzzer liên tục + `setMachineStatus` cảnh báo. Có nên **tự xả** hay chỉ **báo**? Tự xả một mẻ chưa tới nhiệt là làm hỏng mẻ, nên nghiêng về báo trước.

Cần chốt: báo thôi, hay báo rồi tự xả sau thêm N giây?

---

## R4 · `STP_LOOP_2` kẹt nếu cửa xả không đóng 🟢 ĐÃ CODE 2026-07-30

**Triệu chứng**: HMI đứng ở `WCANCEL`, không sang mẻ mới.

**Nguyên nhân**: `waitDropcloseTiEn` chỉ bật khi thấy `DROP_BTN_R == 0`. Cửa xả kẹt mở (hoặc mất tín hiệu đọc nút) → không bao giờ đếm.

**Mức nghiêm trọng: thấp** — mẻ đã xả xong, thợ tắt Start là ra được, không có nguy cơ cháy. **Đề xuất**: đếm trần ~60 giây từ lúc vào LOOP_2 bất kể trạng thái nút; hết giờ mà vẫn thấy drop mở → báo `STT_*` cửa xả kẹt và về `STP_DATA` với Start tắt (không tự nạp mẻ mới khi cửa xả đang mở).

---

## R5 · Huỷ Start giữa mẻ không tắt gas 🟢 ĐÃ CODE 2026-07-30 (theo autoOff_R)

**Hiện tại**: khối `START_BTN_R == 0` (dòng 1842) trả `naviSource*` về biến trở, dừng đếm giờ, mở khoá HMI — nhưng **không** tắt gas và **không** bật cooling. Có hạt đang trong lồng.

Đây có thể là **cố ý** (thợ dừng để can thiệp tay, tắt gas đột ngột làm mất nhiệt lồng). Cần chủ máy xác nhận ý định:
- Giữ nguyên (thợ tự quyết), hay
- Tắt gas nếu `autoOff_R == 1` cho giống hành vi lúc DROP, hay
- Chỉ hạ gas về mức giữ nhiệt.

---

## R6 · Escape xử lý ở hai nơi 🟢 ĐÃ CODE 2026-07-30 (gate coolStep==0)

`COOL_STEP_ESCAPE_OFF` (dòng 2312) và khối trong `if(PC_CONTROL_BTN_R==1)` (dòng 2181) đều có logic tự đóng/huỷ escape. Chưa thấy lỗi thực tế, nhưng khi đang điều khiển bằng PC thì hai khối cùng chạy — đóng escape hai lần thì vô hại, còn reset `escapeTimer` chéo nhau thì có thể làm chuỗi `coolStep` không thoát.

**Đề xuất**: gộp về một chỗ duy nhất trong `coolStep`, khối PC chỉ set cờ. Việc dọn này nên làm **riêng một lần**, không kèm sửa quy trình khác, để dễ khoanh nếu hồi quy.

---

## R7 · 🔴 HỒI QUY DO CHÍNH LỚP 2 CỦA R2 — auto-drop bắn khi CHƯA CÓ HẠT

**Phát hiện 2026-07-30 (cùng ngày, sau khi đã nạp máy). Firmware trên máy ĐANG CÓ lỗi này.**

Lớp 2 của R2 hạ cổng khối DROP từ `progStep >= STP_YELLOW` xuống **`progStep >= STP_CHARGE`**
(`Program.h:1877`). Nhưng `STP_CHARGE` là bước **CHỜ THỢ NẠP** — lúc đó lồng đang ở nhiệt nạp và
**hạt chưa vào**. Khối auto-drop bên trong chỉ xét `Temperature_BT >= DROP_PRO_R`, không xét mẻ
đã bắt đầu hay chưa:

```cpp
if(progStep>=STP_CHARGE){                       // ← gồm cả bước 5 CHỜ NẠP
    if(progStatus == STT_PROGRAM_AUTO){
        if(Temperature_BT>=DROP_PRO_R && progStep<STP_LOOP_1){
            nodeHMI.writeSingleRegister(DROP_BTN_W-1, 1);   // MỞ CỬA XẢ
```

Lý lẽ tôi viết trong chú thích lúc vá — *"về lý thuyết BT không thể tới `DROP_PRO_R` trước khi
qua DE/FCs"* — **SAI**, vì nó chỉ đúng khi nhiệt xả cao hơn nhiệt nạp. Ba trường hợp bung:

1. **Ca cao / rang nhẹ**: hồ sơ nạp 180 °C mà xả 150 °C → ngay ở bước 5 đã có `BT ≥ DROP_PRO_R`
   → **cửa xả mở khi lồng còn trống**. Đây là máy ca cao, nên đây không phải trường hợp lý thuyết.
2. **Charge tay giữ nóng tới 220 °C** (chốt mới): gần như luôn ≥ nhiệt xả → xả ngay khi chờ nạp.
3. **Ngay sau khi nạp**, BT chưa kịp tụt (mất vài giây): hồ sơ nạp 200 / xả 195 → xả trong 1–2
   giây đầu → **mất trắng mẻ**.

Còn tệ hơn khi ghép với chốt mới ở [quyet-dinh-cho-code.md](quyet-dinh-cho-code.md) mục 4c: cửa
xả mở → **máy từ chối nạp** → thợ không nạp được, máy không tự đóng cửa xả → **kẹt cứng**.
Khối pre-cool ngay dưới (`BT ≥ DROP_PRO_R − preCool`) cũng bật bồn nguội sớm y như vậy.

**Cách sửa đề xuất** — giữ đúng ý R2 (auto-drop không phụ thuộc việc bắt được mốc) nhưng gác vào
*mẻ đã thật sự bắt đầu* thay vì gác vào số bước:
```
điều kiện = timeRoastEn == 1                    // đồng hồ mẻ đang chạy ⟺ đã nạp
         && timeRoast > DROP_MIN_SEC            // đề xuất 120 s: không mẻ nào xả trong 2 phút đầu
         && progStep < STP_LOOP_1
```
`timeRoastEn` bật đúng lúc bấm nạp và tắt lúc xả/huỷ, nên nó là cờ "đang có hạt trong lồng"
chính xác hơn `progStep`. Chặn `timeRoast > 120` là lớp thứ hai, phòng hồ sơ có nhiệt xả thấp
hơn nhiệt nạp.

**Cần chốt:** `DROP_MIN_SEC` = 120 giây có hợp không, và có áp cùng luật cho khối **pre-cool**
không (theo tôi là có — bật bồn nguội khi chưa nạp cũng vô nghĩa).

---

## Cách dùng file này

Chủ máy đọc, chốt từng mục (đổi 🔴 → 🟡 kèm quyết định), rồi mới code theo checklist ở [anh-xa-code.md](anh-xa-code.md) mục 3. Code xong đổi 🟡 → 🟢 và ghi ngày + số commit.
