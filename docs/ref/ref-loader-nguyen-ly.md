# Bộ nạp liệu tự động (auto-loader) máy rang OTL — nguyên lý & hướng dẫn

Tài liệu này giải thích **bộ hút cà từ phễu nguồn lên lồng rang**: nó làm việc theo nguyên lý nào,
tại sao lại cắt trước khi đủ cân, kỹ thuật viên chỉnh được những gì, và khi sai cân thì xử lý ra sao.

**Tài liệu chia làm 2 phần — đọc đúng phần của mình:**

| Phần | Dành cho | Nội dung |
|------|----------|----------|
| **A** (mục A1–A10) | **Kỹ thuật viên lắp máy, bảo trì, vận hành** | Nguyên lý bằng lời thường, ví dụ số cụ thể, chỉnh máy, xử lý sự cố. **Không cần biết lập trình.** |
| **B** (mục B1–B9) | Người sửa firmware | Công thức trong code, tên hàm, số dòng, cách tự học, bẫy khi sửa |

- Bản tóm tắt cũ + lịch sử tinh chỉnh: [ref-loader-autolearn.md](ref-loader-autolearn.md)
- Cập nhật: 2026-08-29. Áp dụng cho máy **có cân điện tử ở phễu nguồn** (máy không cân thì không có chức năng này).

---
---

# PHẦN A — DÀNH CHO KỸ THUẬT VIÊN

---

## A1. Bộ nạp liệu gồm những gì

```
        ┌─────────────────────────┐
        │   Phễu chứa trên máy    │
        └───────────┬─────────────┘
                    │  cửa nạp (charge) mở → cà vào lồng rang
                    ▼
              ┌───────────┐
              │ Lồng rang │
              └───────────┘

   Ống hút  ▲
            │  quạt hút (vacuum) kéo cà đi lên
   ┌────────┴────────┐
   │   Phễu nguồn    │  ← cà nhân để dưới đất
   └────────┬────────┘
   ╔════════╧════════╗
   ║  CÂN điện tử    ║  ← cân này cân CẢ PHỄU NGUỒN, gửi số về máy qua Bluetooth
   ╚═════════════════╝
```

**Nguyên tắc đo quan trọng nhất:** máy **không cân được lượng cà đã hút lên**.
Nó chỉ biết **phễu nguồn nhẹ đi bao nhiêu**. Hút 20 kg lên trên = phễu nguồn nhẹ đi 20 kg.

Ba thiết bị tham gia:

| Thiết bị | Vai trò | Hỏng thì hiện tượng gì |
|----------|---------|------------------------|
| Cân điện tử + Bluetooth | báo cân phễu nguồn về máy, liên tục | máy tắt hút và báo lỗi cân sau 5 giây mất tín hiệu |
| Quạt hút (vacuum) | kéo cà lên | không lên cà, hết giờ hút → báo lỗi loader |
| Van/cửa phễu | đóng mở đường cà | đóng chậm → hút dư; kẹt → sai cân lung tung |

Quạt hút bật/tắt bằng **rơ-le CH8** trên bo IO. Bo mạch **không** đóng rơ-le thẳng — nó ra lệnh cho màn
hình HMI, rồi **đọc ngược** trạng thái nút từ HMI về mới đóng rơ-le. Nghĩa là **màn hình HMI mất kết nối
thì bộ hút không chạy**, dù bo mạch vẫn sống.

---

## A2. Một mẻ hút diễn ra như thế nào

Kể theo thời gian, tính từ lúc bộ hút được bật (tự động hoặc bấm tay):

| Thời điểm | Máy làm gì |
|-----------|-----------|
| Trước khi bật | Ghi nhớ **cân đích** = cân hiện tại − lượng cần hút. Ví dụ phễu 30,0 kg, cần hút 20,0 kg → đích **10,0 kg**. |
| 0 giây | Bật quạt hút. Ghi nhớ cân lúc bắt đầu. |
| ~3 giây | Lực hút đã ổn định nhưng **cà chưa chảy** → máy đo phần **cân bị sai do lực hút** (mục A3.2) và ghi nhớ. |
| ~5 giây | Cửa phễu mở, cà bắt đầu chảy lên. Cân bắt đầu tụt. |
| Suốt lúc hút | Mỗi vòng quét máy so cân hiện tại với **ngưỡng cắt** (mục A4). |
| Chạm ngưỡng | **Tắt quạt hút.** Nhưng cà chưa dừng ngay — còn chảy thêm (mục A3.1). |
| +1,5 đến 15 giây | Chờ cân **đứng yên** rồi mới đọc số cuối. Nếu 15 giây cân vẫn nhảy thì đọc đại. |
| Đọc xong | Chấm điểm mẻ hút (mục A5) và ghi vào thẻ nhớ nếu bật ghi log. |

**Vì sao phải chờ cân đứng yên mới đọc:** ngay sau khi tắt quạt, cà còn rơi và phễu còn rung — đọc lúc đó
là đọc số rác. Điều kiện đứng yên: cân thay đổi chậm hơn **0,2 kg/phút**.

---

## A3. Hai hiện tượng vật lý mà máy phải bù

### A3.1. Cà chạy thêm sau khi tắt quạt (tiếng Anh trong máy gọi là **coast**)

Tắt quạt **không** làm cà dừng ngay, vì:

- van/cửa đóng mất **0,5–0,7 giây** (van chỉ có đóng/mở, không có đóng từ từ);
- cột cà đang bay trong ống vẫn rơi nốt;
- cà lơ lửng ở cửa hút chưa rơi xuống hết.

**Đo thực tế trên máy 30 kg (ngày 17/08/2026, 7 mẻ):** lượng chạy thêm là
0,94 / 0,98 / 0,98 / 0,98 / 1,00 / 1,04 / 1,08 kg → **trung bình đúng 1,00 kg**.

Kiểm chứng thêm bằng 18 lần cân tay của thợ rang ở các mức 5 / 10 / 20 kg: cũng ra **≈ 1,00 kg ở cả ba mức**
— tức lượng chạy thêm **không phụ thuộc** hút nhiều hay hút ít.

👉 Vì vậy máy được cài **cắt sớm 1,00 kg**. Số này trong máy gọi là **`dif`** (đọc là "díp", nghĩa là *lượng
cắt sớm*). Cắt sớm 1,00 kg + chạy thêm 1,00 kg = vừa đúng.

### A3.2. Lực hút làm cân báo nặng giả

Khi quạt hút chạy, luồng khí và ống mềm kéo/đẩy phễu nguồn → **cân báo sai lệch** vài lạng so với lúc đứng yên.
Máy tự đo phần sai lệch này ở **giây thứ 3** (lúc quạt đã ổn định mà cà chưa chảy) và trừ ra khi so ngưỡng cắt.

- Phần bù này bị **giới hạn tối đa 0,30 kg** — đo ra lớn hơn thì máy chỉ lấy 0,30 kg (chống trường hợp đo lỗi
  làm cắt sai hoàn toàn).
- Nếu lực hút làm cân báo **nhẹ đi** (âm) thì máy **bỏ qua**, coi như bằng 0.

> ⚠️ Cửa sổ 3 giây này rất hẹp và có chủ ý: sớm hơn thì quạt chưa đủ lực, muộn hơn thì cà đã chảy và máy sẽ
> tưởng lượng cà chảy là sai lệch của cân. **Nếu thay quạt/ống khác làm thời gian lên lực đổi nhiều thì phải
> báo lại để chỉnh con số 3 giây này trong firmware.**

---

## A4. Máy quyết định cắt lúc nào — công thức bằng lời + ví dụ

**Công thức bằng lời:**

> Tắt quạt khi: **cân hiện tại ≤ cân đích + lượng cắt sớm + phần nặng giả do lực hút**

**Ví dụ số thật** (mẻ 20 kg, phễu ban đầu 30,00 kg):

| Đại lượng | Giá trị | Ở đâu ra |
|-----------|---------|----------|
| Cân phễu lúc đầu | 30,00 kg | cân đọc về |
| Lượng cần hút | 20,00 kg | **kỹ thuật viên cài trên HMI** |
| → Cân đích | **10,00 kg** | 30,00 − 20,00 |
| Lượng cắt sớm (`dif`) | 1,00 kg | cài trong firmware, xem A3.1 |
| Nặng giả do lực hút | 0,12 kg | máy tự đo ở giây thứ 3 |
| **→ Ngưỡng cắt** | **11,12 kg** | 10,00 + 1,00 + 0,12 |

Diễn biến:

1. Cân **hiển thị** tụt dần: 30,12 → 25,12 → … → **11,12 kg** → máy tắt quạt.
   (Lúc này cân **thật** là 11,00 kg, vì đang bị lực hút cộng thêm 0,12.)
2. Cà chạy thêm 1,00 kg → cân thật còn **10,00 kg**.
3. Quạt tắt → hết nặng giả → cân hiển thị = cân thật = **10,00 kg** = **đúng đích**. ✔

**Đọc ngược lại để hiểu lỗi:**

| Nếu… | Kết quả |
|------|---------|
| Cắt sớm nhiều hơn lượng chạy thêm | **hút thiếu** — phễu nguồn còn nặng hơn đích. Máy ghi nhãn `UNDER` |
| Cắt sớm ít hơn lượng chạy thêm | **hút dư** — hút quá tay. Máy ghi nhãn `OVER` |
| Cắt sớm = lượng chạy thêm | đúng cân. Nhãn `OK` |

Nói gọn: **sai số cuối mẻ = lượng cắt sớm − lượng chạy thêm.**

---

## A5. Máy tự chấm điểm mỗi mẻ hút

Sau khi cân đứng yên, máy so cân thật với đích:

- **Lệch** = cân cuối − cân đích. Lệch **dương** = hút thiếu; **âm** = hút dư.
- **Điểm** = 10 điểm trừ đi mỗi 10 gam lệch trừ 0,1 điểm.
  - lệch 0 g → **10,0 điểm**
  - lệch 50 g → 9,5 điểm
  - lệch 100 g → 9,0 điểm
  - lệch 500 g → 5,0 điểm
- **Đạt** = từ **9,1 điểm** trở lên, tức lệch không quá **90 gam**.

Nhãn kết quả máy ghi ra: `OK` (đạt) · `UNDER` (hút thiếu) · `OVER` (hút dư) · `SMALL` (mẻ hút dưới 0,5 kg —
máy coi là nhiễu chứ không phải mẻ thật, bỏ qua không tính).

**Kết quả nghiệm thu trên máy 30 kg ngày 17/08/2026** (7 mẻ, mức 15 và 20 kg): lệch +30 / −20 / −10 / +100 /
−30 / +20 / −10 gam → 6 trên 7 mẻ dưới 30 gam, tệ nhất 100 gam, **điểm trung bình 9,7**.
(Trước lần chỉnh đó: điểm dao động 2,6–9,7, có mẻ lệch tới **760 gam**.)

---

## A6. Kỹ thuật viên chỉnh được gì — và không chỉnh được gì

### A6.1. Bốn ô chỉnh trên màn hình HMI

| Ô trên HMI | Thanh ghi | Đơn vị | Ý nghĩa | Cài sai thì sao |
|------------|-----------|--------|---------|-----------------|
| Lượng cà cần hút | 32 | kg | mỗi lần hút bao nhiêu | quá lớn so với phễu → không bao giờ đủ, hết giờ → báo lỗi |
| Thời gian hút tối đa | 14 | giây | quá giờ này chưa cắt được thì **báo lỗi loader** | quá ngắn → mẻ đang hút bình thường cũng bị báo lỗi; quá dài → tắc ống mà máy vẫn chạy hoài |
| Ngưỡng lực kéo vacuum | 44 | kg | dưới mức này thì cột cà quá thấp, quạt không kéo nổi | đặt cao quá → chưa hút đủ đã chuyển sang chế độ dọn phễu; thấp quá → quạt chạy không tải |
| Bật auto-loader | 33 | 0/1 | cho phép máy tự hút mẻ kế tiếp | tắt thì phải hút tay |

### A6.2. Cái KHÔNG chỉnh được từ HMI

**Lượng cắt sớm 1,00 kg (`dif`) nằm trong firmware, không có ô trên HMI.**
Muốn đổi phải sửa dòng `#define FEEDER_DIF_FIXED 100` trong `include/Config.h` rồi nạp lại firmware
(số 100 = 1,00 kg; đơn vị là **phần trăm ki-lô-gam**, tức 20 = 0,20 kg).

👉 Nếu ngoài hiện trường thấy máy **lệch đều một chiều**, hãy đo lấy vài mẻ rồi **báo về xưởng con số lệch
trung bình** — người nạp firmware chỉnh đúng bằng lượng lệch đó:

- máy **hút thiếu** trung bình 0,20 kg → **giảm** số đó đi 20 (100 → 80);
- máy **hút dư** trung bình 0,15 kg → **tăng** lên 15 (100 → 115).

Không cần đụng gì khác.

---

## A7. Khi nào máy tự hút, và tại sao nó không chịu hút

Bộ hút **tự chạy** chỉ khi hội đủ **tất cả** các điều kiện sau:

1. Máy đang chạy chương trình **rang tự động** (không phải rang tay);
2. Ô **auto-loader** trên HMI đang bật;
3. Còn **ít nhất 2 mẻ** trong số mẻ đã cài (mẻ cuối thì khỏi hút thêm);
4. Mẻ đang rang đã qua mốc **nổ 1 (FCs)** — máy hút mẻ sau **trong lúc** mẻ này còn đang rang;
5. Cân **đang gửi số bình thường** (không mất Bluetooth, không âm);
6. Phễu nguồn **còn ít nhất 80 % một mẻ**. Máy 12 kg → phải còn ≥ 9,6 kg; máy 30 kg → ≥ 24 kg.

Thiếu điều kiện 5 hoặc 6 → máy **báo lỗi loader và huỷ mẻ kế tiếp** (tắt nút START, mở khoá chọn hồ sơ).
Đây là chủ ý: **thà dừng còn hơn rang một mẻ thiếu cà.**

---

## A8. Sự cố thường gặp — kiểm tra theo thứ tự

| Hiện tượng | Kiểm tra theo thứ tự này |
|------------|--------------------------|
| Máy báo **lỗi cân** rồi tắt hút | 1) cân còn pin/nguồn? 2) module Bluetooth có sáng/kết nối? 3) dây/khoảng cách. Mất tín hiệu **5 giây** là máy tắt hút ngay |
| Báo **cân âm** | cân chưa trừ bì (tare) hoặc phễu bị kênh, kê vướng khung |
| Báo **lỗi loader** dù cà còn nhiều | 1) phễu còn ≥ 80 % một mẻ chưa? 2) thời gian hút tối đa (reg 14) có bị cài quá ngắn? 3) tắc ống / quạt yếu |
| **Hút dư** đều tay | lượng chạy thêm lớn hơn 1,00 kg — van đóng chậm (kiểm khí nén, xi-lanh), hoặc phải tăng số cắt sớm (A6.2) |
| **Hút thiếu** đều tay | van đóng nhanh hơn / ống thoáng hơn → giảm số cắt sớm (A6.2) |
| Lệch **lung tung** ±0,1 kg, không theo chiều nào | **bình thường** — đây là trần của phần cứng, xem A9 |
| Mẻ nhỏ 2–3 kg luôn sai nhiều | xem A9, đây là hạn chế đã biết |
| Quạt chạy mãi rồi tự tắt, không tính điểm | phễu đã xuống dưới **ngưỡng lực kéo** (reg 44) → máy chuyển sang **chế độ dọn phễu**: hút nốt **10 giây** rồi tắt. Không phải lỗi |
| Cân trên HMI hiện số lạ (ví dụ 6135) | HMI hiển thị **số nguyên nhân 100**: 6135 = 61,35 kg. Xem A9 |

---

## A9. Những giới hạn phải chấp nhận (phần mềm không sửa được)

- **Chính xác nhất chỉ tới khoảng ±0,1 kg.** Van chỉ có đóng/mở, thời gian đóng dao động 0,5–0,7 giây;
  riêng cái dao động đó đã tạo ra ±0,15 kg ngẫu nhiên. Muốn chính xác hơn phải **thêm van đóng nhanh
  dưới 0,1 giây** — là việc của cơ khí, không phải phần mềm.
- **Mẻ 2–3 kg sai nhiều là cố hữu.** Bấm hút xong khoảng 7 giây cửa mới mở; mẻ nhỏ cà chỉ chảy 2–3 giây,
  chưa kịp vào nhịp ổn định thì đã phải cắt.
- **Cân mất tín hiệu là mất mẻ hút** — máy không có cách nào đoán cân, chỉ có thể dừng an toàn.
- **Số hiển thị nhân 10 hoặc 100.** Bộ điều khiển không dùng số thập phân, nên: cân ×100 (6135 = 61,35 kg),
  nhiệt độ ×10 (1850 = 185,0 °C), tốc độ hút ×100 (2000 = 20,00 kg/phút).

---

## A10. Bảng thuật ngữ (mọi từ lạ xuất hiện trong máy và trong tài liệu này)

| Từ | Đọc/hiểu là | Giải thích |
|----|-------------|-----------|
| **loader** / **feeder** | bộ nạp liệu / bộ hút | cùng chỉ cụm hút cà từ phễu nguồn lên máy |
| **coast** | lượng cà chạy thêm | phần cà vẫn rơi sau khi đã tắt quạt (~1,00 kg) |
| **dif** | lượng cắt sớm | cắt trước đích bao nhiêu để bù coast |
| **target** | đích | cân phễu nguồn PHẢI CÒN LẠI khi hút xong |
| **offset** | phần nặng giả | cân sai lệch do lực hút, đo ở giây thứ 3 |
| **err** | lệch | cân cuối − đích. Dương = thiếu, âm = dư |
| **score** | điểm | 10 điểm trừ dần theo lệch; ≥ 9,1 là đạt |
| **OK / UNDER / OVER / SMALL** | đạt / thiếu / dư / mẻ rác | nhãn kết quả từng lần hút |
| **ror** (rorKG) | tốc độ hút | cà đang rời phễu nhanh cỡ nào, đơn vị kg/phút |
| **netW** | cân tịnh | số cân của phễu nguồn (đã trừ bì) |
| **settle** | lắng | chờ cà rơi hết + phễu hết rung mới đọc cân |
| **HMI** | màn hình điều khiển | màn Delta trên tủ điện |
| **thanh ghi (register)** | ô nhớ trên HMI | mỗi ô một chức năng, đánh số: 14, 32, 33, 44… |
| **firmware** | phần mềm trong bo mạch | phải nạp lại bằng máy tính mới đổi được |
| **FCs** | nổ 1 | mốc hạt nổ lần đầu trong quá trình rang |

---
---

# PHẦN B — DÀNH CHO NGƯỜI SỬA FIRMWARE

Từ đây trở xuống là chi tiết code: tên hàm, số dòng, đơn vị nội bộ, cơ chế tự học.
Kỹ thuật viên hiện trường **không cần đọc phần này**.

---

## B1. Bản đồ code — chỗ nào làm việc gì

Toàn bộ loader nằm trong `include/Program.h` (trừ 3 dòng cuối bảng). Số dòng theo bản hiện tại của repo.

| Hàm / khối | Dòng | Làm gì |
|------------|------|--------|
| `timerPoll_1000ms()` → khối "RoR cân" | 148–160 | tính `rorKG` (tốc độ hút) mỗi 1 giây |
| `loaderParseScaled()` | 1092 | tự đọc số thập phân trong CSV (không dùng `sscanf %f`) |
| `loaderQuantize()` | 1112 | snap (cân, ror) về tâm ô lưới |
| `loaderCfgFind()` | 1122 | tra ô **khớp đúng** trong bảng học |
| `loaderCfgNearest()` | 1129 | tra ô **đã học gần nhất** khi không khớp |
| `loaderCfgSeed()` | 1142 | dựng bảng mặc định (12 dòng) khi chưa có file |
| `loaderCfgLoad()` | 1161 | nạp `loadcfg.csv` vào RAM lúc boot + mồi `loaderSeq` |
| `loaderCfgSave()` | 1219 | ghi đè `loadcfg.csv` sau mỗi lần học |
| `loaderLogTrim()` | 1237 | cắt bớt `loader.csv` còn 400 dòng |
| `loaderLogEvent()` | 1276 | ghi 1 dòng log cho mỗi lần hút (16 cột) |
| `loaderAdapt()` | 1312–1393 | chờ cân lắng → chấm điểm → học `dif` → ghi log |
| `programScan()` → `case STP_LOOP_1` | 1808–1818 | loader FAIL thì huỷ chuỗi mẻ |
| `programScan()` → khối "Check auto cân" | 1899–1924 | khởi động auto-loader ở bước `STP_FCS` |
| `programScan()` → `switch(aLoaderStep)` | 2078–2101 | máy trạng thái loader (ON/WAIT/FAIL/OK) |
| `programScan()` → kiểm tra mất dữ liệu cân | 2116–2126 | bluetooth im 5 s → tắt feeder, báo lỗi |
| `programScan()` → latch `feederWasOff` | 2117–2130 | bắt đầu mẻ hút, chốt `adaptStartMs` / `adaptStartW100` |
| `programScan()` → đo offset lực hút | 2131–2142 | sau 3 s: đo `suctionOffset100`, chốt lại `wStart` |
| `programScan()` → tính `difNetW` | 2143–2151 | chốt cân đích (chỉ khi nút hút TẮT) |
| `programScan()` → chọn `dif100` | 2153–2172 | tra bảng / công thức / số ghim |
| `programScan()` → điều kiện cắt | 2175–2205 | so ngưỡng, tắt feeder, vào pha học |
| `programScan()` → khối "Debug loader" | 2207–2239 | in 1 dòng/giây ra `SerialComputer` |
| `programScan()` → dọn phễu | 2241–2250 | hút nốt 10 s khi phễu quá nhẹ |
| `programScan()` → "Auto close feeder - timer" | 2277–2290 | hết `feederSet_R` giây chưa cắt được → FAIL |
| `readScale()` — `ScaleFeeder.h` | 60 | đọc khung `GS,   61.7,kg` → `netW100` / `netW` |
| `controlIO()` — `IOConfig.h` | 88 | `FEEDER_BTN_R = 1` → đóng relay CH8 (quạt hút) |
| `rwHMI_1()` — `Modbus_Master.h` | 560 | đồng bộ `FEEDER_BTN_R` với HMI |

---

## B2. Đường tín hiệu và đơn vị nội bộ

```
Program.h  nodeHMI.writeSingleRegister(FEEDER_BTN_W-1, 1|0)   → HMI reg 40006
hàm rwHMI_1()  ──đọc lại qua Modbus──▶  FEEDER_BTN_R      (Modbus_Master.h, dòng 560)
hàm controlIO(): FEEDER_BTN_R == 1 → CH8_RL_ON            (IOConfig.h, dòng 88 — relay quạt hút)
```

> ⚠️ Firmware **không** bật relay trực tiếp — nó ghi vào HMI rồi **đọc ngược** trạng thái về.
> Vì vậy mọi thứ trong loader đều phải chịu được trễ 1 vòng Modbus và trường hợp **lỡ mất cạnh 0→1**
> (xử lý bằng latch `feederWasOff`, mục B4).

Đường đọc cân: cân bluetooth gửi khung ASCII `GS,   61.7,kg` → hàm `readScale()` (`ScaleFeeder.h`, dòng 60).

| Biến | Thang | Ghi chú |
|------|-------|---------|
| `netW100` | ×100 kg (`6135` = 61,35 kg) | **số dùng để cắt** — cần độ phân giải 0,01 kg |
| `netW` | ×10 kg | bản cũ, dùng cho HMI + ngưỡng "đủ liệu" |
| `rorKG` | ×100 kg/phút (`-2000` = hút 20 kg/phút) | hút ra = **âm** |
| `dif100` / `dif` | ×100 kg / ×10 kg | lượng cắt sớm |
| `suctionOffset100` | ×100 kg | nặng giả do lực hút |

> 🕳 Bẫy lịch sử: `netW100` từng bị mất khai báo → nếu chỉ khai báo cho qua build mà không gán thì
> `netW100 = 0 ≤ ngưỡng` → **cắt ngay khi vừa bật hút**, mẻ nào cũng thiếu — xem chú thích ngay chỗ khai báo
> `netW100` (`ScaleFeeder.h`, dòng 6–12).

**Mô hình vật lý ban đầu** — chép từ khối chú thích "AUTO-DIF FEEDER" trong `include/Config.h` (dòng 120–132),
dùng làm mồi khi bảng học còn rỗng:

```
dif (kg) = |rorKG| (kg/phút) × T_kg (ms/kg) × wStart (kg) / 60000
```

Ý: coast tỉ lệ **tốc độ hút** và **thời gian hiệu dụng**, mà thời gian hiệu dụng lại tỉ lệ **lượng cà trong
phễu**. Gộp hai thứ sau thành hằng số `T_kg` (ms trên mỗi kg cà); `FEEDER_TKG_DEFAULT = 190` = 19,0 ms/kg.
**Số liệu 2026-08 bác bỏ mô hình này** — coast thực đo ra gần như hằng số (xem A3.1, B6).

---

## B3. Tốc độ hút `rorKG` — chuỗi tính và các trần

**Ở đâu trong code:** hàm `timerPoll_1000ms()` — `include/Program.h`, khối "RoR cân", **dòng 150–160**.
Hàm này chạy **mỗi 1000 ms** trong ngắt timer (`#define TIMER0_INTERVAL_MS 1000` trong `Define.h`, dòng 1215):

```c
d = (netW100 − kgSamp_1) × 6;      // cửa sổ 1 giây
if (d >  600) d =  600;            // clamp TRƯỚC Kalman
if (d < -600) d = -600;
raw_rorKG = d;
rorKG = rorKGKalmanFilter.updateEstimate(raw_rorKG);   // q = 0.7 (bám nhanh)
rorKG = rorKG × 10;                                    // trả về thang ×100 kg/phút
kgSamp_1 = netW100;
```

Vì sao ×6 rồi ×10: `netW100` là ×100 kg; chênh lệch trong **1 giây** phải ×60 mới ra kg/phút.
Hệ số tổng ×60 được tách thành ×6 (trước lọc) và ×10 (sau lọc) → clamp ±600 tương đương **±60 kg/phút**.

Khác biệt so với RoR nhiệt: `rorBT/rorET` dùng cửa sổ **3 giây**, còn cân dùng **1 giây** với bộ đếm riêng
(`rorCountKG`) vì **mẻ nhỏ chỉ chảy 2–3 giây** — lọc chậm là ror chưa kịp lên thì đã cắt xong.

---

## B4. Ngưỡng cắt trong code

**Ở đâu:** hàm `programScan()` (`include/Program.h`), đoạn "Cân" — từ chỗ tính `difNetW` (**dòng 2143**)
tới lệnh tắt feeder khi chạm ngưỡng (**dòng 2205**). Bốn khối con chạy **tuần tự trong cùng một vòng quét**.

### B4.1. Đích `difNetW` chốt khi nút hút đang TẮT

```c
if (netW > netWTG_R && FEEDER_BTN_R == 0) difNetW = netW - netWTG_R;   // ×10 kg
else if (netW <= netWTG_R && FEEDER_BTN_R == 0) difNetW = 0;
```

Điều kiện `FEEDER_BTN_R == 0` khiến đích **đóng băng** suốt lúc hút — nếu không, phễu nhẹ dần sẽ kéo đích
nhẹ theo và không bao giờ chạm.

### B4.2. Chọn `dif100`

```c
rorMag = |rorKG|;
loaderQuantize(adaptStartW100, rorMag, &qw, &qr10);   // snap về ô lưới
ci = loaderCfgFind(qw, qr10);                         // ô khớp đúng
if (ci < 0) ci = loaderCfgNearest(qw, qr10);          // không có → ô đã học gần nhất
dif100 = (ci >= 0) ? cfgDif100[ci]
                   : rorMag × feederTkg × adaptStartW100 / 60000000;   // bảng rỗng → công thức B2
#if FEEDER_DIF_FIXED > 0
    dif100 = FEEDER_DIF_FIXED;                        // ← ĐANG BẬT: ghim 1,00 kg
#endif
clamp dif100 vào [0, FEEDER_DIF_MAX×10]               // trần 2,5 kg
```

Hằng số chia `60000000` chính là công thức B2 sau khi quy đổi thang:
`(rorMag/100) × (feederTkg/10) × (w100/100) / 60000` rồi ×100 để ra `dif100`.

### B4.3. Điều kiện cắt

```c
if (FEEDER_BTN_R == 1 && netWTG_R > 0 && scaleDataValid) {
    if (netW100 <= difNetW×10 + dif100 + suctionOffset100) {   // ← NGƯỠNG CẮT
        if (netW100 > vacuumTraction_R×10)  → CẮT BÌNH THƯỜNG (ghi HMI reg 6 = 0, vào pha học)
        else                                → CHẾ ĐỘ DỌN PHỄU (B4.5)
    }
}
```

So sánh ở thang ×100 là **có chủ ý**: bản cũ so ở ×10 nên ngưỡng nhảy bậc 0,1 kg.
**Cộng `suctionOffset100` vào vế phải = trừ offset khỏi cân.**

### B4.4. `suctionOffset100`

**Ở đâu:** khối "chốt lại wStart + đo offset lực hút" trong `programScan()` — **dòng 2131–2142**:

```c
if (adaptWStartPending && FEEDER_BTN_R == 1 && millis() - adaptStartMs >= FEEDER_WSTART_DELAY_MS) {
    off = netW100 - adaptStartW100;              // chênh sau 3 s hút, cà CHƯA chảy
    clamp off vào [0, FEEDER_OFFSET_MAX100];     // 0 … 0,30 kg
    suctionOffset100 = off;
    adaptStartW100   = netW100;                  // chốt LẠI cân đầu (mốc sạch)
    adaptWStartPending = false;
}
```

### B4.5. Chế độ dọn phễu (`vacuumTraction_R`, HMI reg 44)

Khối "Tự tắt feeder sau khi dọn sạch" trong `programScan()` (**dòng 2241–2250**):

```c
if (FEEDER_BTN_R == 1 && cleanFeederTi >= 10 && cleanFeederTiEn) → tắt feeder, aLoaderStep = OK
```

Nhánh này **không chấm điểm, không ghi log, không học** (`CLEAN-FEEDER (NO LOG)`).

> 🕳 Comment trong code ghi "5 giây" nhưng `cleanFeederTi` đếm **1 đơn vị/giây** → thực tế là **10 giây**.
> Tương tự, comment "Tự động cập nhật cân sau 10 giây" ở khối kiểm tra mất dữ liệu cân (**dòng 2116**)
> thực tế là **5 giây** vì điều kiện là `updateNetWTi >= 5`.

### B4.6. Timeline một mẻ hút

| t | Sự kiện | Chỗ trong code (`programScan()` trừ khi ghi khác) |
|---|---------|------|
| −∞ | nút hút TẮT → `difNetW` cập nhật liên tục theo `netW` | khối tính `difNetW` — dòng 2145 |
| 0 s | `FEEDER_BTN_R = 1` **và** `feederWasOff` → chốt `adaptStartMs`, `adaptStartW100`, bật `adaptArmed`, `adaptWStartPending` | khối latch `feederWasOff` — dòng 2117–2130 |
| ~3 s | đo `suctionOffset100`, **chốt lại** `adaptStartW100` | khối đo offset — dòng 2131–2142 |
| ~5 s | cửa phễu mở, cà chảy → `rorKG` đi âm | — |
| chạy | tra `dif100` theo (cân, ror) rồi so ngưỡng cắt | khối chọn `dif100` — dòng 2153–2172 |
| T | chạm ngưỡng → HMI reg 6 = 0; chốt `adaptTarget/adaptSet/adaptRorMag/adaptDif100`; `loaderAdaptPhase = 1`; `adaptArmed = false` | khối cắt — dòng 2175–2199 |
| T+1,5 s… | chờ lắng: `elapsed ≥ 1500 ms` **và** `|rorKG| ≤ 20`, hoặc quá `15 s` | `loaderAdapt()` — dòng 1316–1321 |
| lắng xong | `final100 = netW100` → chấm điểm → học (B5) → ghi `loader.csv` → `loaderAdaptPhase = 0` | `loaderAdapt()` — dòng 1322–1392 |

**Vì sao dùng latch `feederWasOff`:** `FEEDER_BTN_R` đọc từ HMI qua Modbus, vòng quét có thể **lỡ mất** cạnh
0→1 → mẻ mới chạy với `adaptStartW100` của mẻ trước. **`adaptArmed`** đảm bảo mỗi sườn hút chỉ vào pha học
đúng một lần.

---

## B5. Vòng tự học `dif` — hàm `loaderAdapt()`

**Ở đâu:** hàm riêng `loaderAdapt()` — `include/Program.h`, **dòng 1312–1393**.
Gọi mỗi vòng quét từ `programScan()` (dòng 2112), thoát ngay nếu `loaderAdaptPhase != 1`.

```c
final100  = netW100;
target100 = adaptTarget × 10;
batch100  = adaptStartW100 − target100;
err100    = final100 − target100;         // >0 = hút THIẾU
score×10  = 100 − |err100|;
ok        = score×10 ≥ 91;                // lệch ≤ 0,09 kg
```

**Ba cổng chặn học:**

| Cổng | Ngưỡng | Lý do |
|------|--------|-------|
| `batch100 ≥ FEEDER_MIN_BATCH100` | 0,5 kg | nhiễu cân 0,05–0,25 kg từng kéo `dif` dao động |
| `ok == false` (deadband) | lệch > 0,09 kg | đạt rồi thì không đụng vào → chống giật |
| `adaptRorMag ≥ 100 && adaptStartW100 ≥ 100` | 1 kg/phút, 1 kg | điểm vận hành quá nhỏ thì số liệu vô nghĩa |

**Bảng lưới (cân, tốc độ hút)** — học bảng thưa chứ không học một số:

```
loaderQuantize: qw   = round(cân kg)    snap về bội số FEEDER_W_BUCKET      = 5 kg   (tối thiểu 5)
                qr10 = round(ror ×10)   snap về bội số FEEDER_ROR_BUCKET10  = 2,5 kg/phút
```

Tra ba tầng: **ô khớp đúng** → **ô đã học gần nhất** (khoảng cách bình phương theo *số bước lưới*) →
**công thức `T_kg`**. Chưa có file thì `loaderCfgSeed()` dựng 12 dòng mẫu tại cân tham chiếu 100 kg, `n = 0`.

**Cập nhật ô:**

```c
difReal100 = adaptDif100 − err100;     // dif LẼ RA đúng cho mẻ vừa rồi
clamp difReal100 vào [0, FEEDER_DIF_MAX×10];

ô mới, bảng còn chỗ  → tạo ô, lấy luôn difReal, n = 1
ô mới, bảng ĐẦY (48) → thay ô có n NHỎ NHẤT → không bao giờ ngừng học
ô đã có              → EMA:  cfgDif += FEEDER_ADAPT_GAIN × (difReal − cfgDif) / 100   // kéo 0,30/mẻ
→ loaderCfgSave()
```

---

## B6. Chế độ `dif` cố định — trạng thái đang chạy

`include/Config.h` **dòng 193** — `#define FEEDER_DIF_FIXED 100` → **dif = 1,00 kg cho mọi mẻ**, bỏ qua bảng
lẫn công thức, **không học, không ghi bảng** (vẫn chấm điểm, vẫn log nếu bật log). Số liệu hiệu chuẩn và
nghiệm thu: xem A3.1 và A5.

Đi kèm: `LOADER_SD_LOG_EN 0` → loader **không đụng thẻ SD** nữa (từng có ca treo máy giữa lúc hút).
Muốn quay lại chế độ tự học: đặt `FEEDER_DIF_FIXED 0` và xoá `loadcfg.csv`.

> Bài học: ngưỡng cắt **đứng yên** suốt mẻ ăn đứt ngưỡng "thông minh" chạy theo `rorKG` nhiễu.

---

## B7. Máy trạng thái `aLoaderStep`

Mã trạng thái — các `#define STP_*_LOADER` trong `include/Define.h`, **dòng 244–248**:
`0 NONE` · `1 ON` · `2 WAIT` · `3 FAIL` · `4 OK`.

**Điểm khởi động** — khối "Check auto cân" trong `programScan()` (**dòng 1899–1924**):

```c
if (progStep == STP_FCS && progStatus == STT_PROGRAM_AUTO
    && autoLoader_R == 1 && aLoaderStep == 0 && loop_R > 1) {
        !scaleDataValid        → STT_SCALE_DATA_INVALID + FAIL
        netW < 0               → STT_SCALE_NEGATIVE     + FAIL
        netW ≥ LOADER_MIN_NETW → STT_LOADER_RUNNING     + STP_ON_LOADER
        còn lại (thiếu liệu)   → STT_LOADER_FAIL        + FAIL
}
```

`LOADER_MIN_NETW = MACHINE_BATCH_KG × LOADER_MIN_BATCH_PCT / 10` (×10 kg).

Chuyển bước — `switch(aLoaderStep)` trong `programScan()` (**dòng 2078–2101**):

| Bước | Việc làm | Thoát |
|------|----------|-------|
| `STP_ON_LOADER` | ghi HMI reg 6 = 1 | → `WAIT` ngay vòng sau |
| `STP_WAIT_LOADER` | chờ | cắt / dọn phễu → `OK`; mất cân hoặc hết `feederSet_R` giây → `FAIL` |
| `STP_FAIL_LOADER` | giữ nhãn `FLOA` | reset ở `STP_LOOP_1` |
| `STP_OK_LOADER` | nhãn `OKLOA` | reset ở `STP_LOOP_1` |

**Hệ quả FAIL**: `case STP_LOOP_1` (**dòng 1808–1818**) — tắt START, mở khoá select, **huỷ chuỗi mẻ**.

> 🕳 Máy **không có cân** (`MACHINE_HAS_SCALE_FEEDER 0`) thì cả khối này **không được biên dịch**
> (nhánh `#else`, **dòng 1918–1924**). Trước khi có nhánh đó, HMI đời cũ trả reg 33 = 1 làm máy không-cân
> chui vào loader rồi báo lỗi huỷ mẻ vô cớ. Cấu hình repo hiện tại — `#define MACHINE_HAS_SCALE_FEEDER 0`
> (`Config.h` **dòng 34**) — là máy 3 kg không cân → loader tắt hẳn.

---

## B8. File trên thẻ SD & log serial

Tên **8.3 bắt buộc** — SD lib 1.2.4 không nhận tên dài, tạo file thất bại **âm thầm**.

| File | Vai trò |
|------|---------|
| `loadcfg.csv` | bảng học `wKg,rorKgMin,dif,n`; nạp vào RAM lúc boot, ghi đè mỗi lần học. Xoá = học lại từ seed |
| `loader.csv` | log 1 dòng/lần hút, 16 cột: `STT,s,wStart,batch,set,secHut,rorKG,dif,offset,target,final,err,score,result,difOld,difNew` |
| `loader.tmp` | file trung gian khi trim (SD lib không có `rename`) |

- `loaderSeq` mồi lại từ dòng cuối `loader.csv` lúc boot → số thứ tự liên tục qua các lần tắt nguồn.
- `loaderLogTrim` giữ 400 dòng nhưng **cắt dư 40 dòng** mỗi lần → chỉ trim mỗi ~40 lần ghi.
- Header chỉ ghi khi `f.size() == 0` (không dùng `SD.exists()` vì hay false-negative sau remove/recreate).
- Thẻ hỏng: `sdEnsure()` thử lại mỗi `SD_RETRY_MS = 10 s`; boot thử `SD_INIT_RETRY = 5` lần rồi **chạy tiếp
  chứ không treo máy**.

**Log serial** — bật `enDebug = 1` hoặc `LOADER_DEBUG_EN 1`; tự in khi bấm loader, 1 dòng/giây, tắt 10 s sau
khi nút off và đã ghi log xong (khối "Debug loader", **dòng 2207–2239**):

```
LDR t=12 btn=1 vld=1 w=2787 set=300 dN=21 raw=-4440 ror=-4410 dif=126 thr=336 wS=3208 ph=0 arm=1 stp=0 cfg=48 qw=30 qr=45 ci=17
LDR >>> AUTO-CUT (normal path, will settle+log)
LDR >>> LOG: result=OK score=98 set=300 err=2 final=212 batch100=2998 secHut=43
```

| Trường | Nghĩa |
|--------|-------|
| `t` | giây kể từ lúc bắt đầu hút |
| `w` / `wS` | cân hiện tại / cân đầu đã chốt (×100) |
| `set` / `dN` | lượng cần hút / cân đích còn lại (×10) |
| `raw` / `ror` | ror thô (đã ×10) / ror sau Kalman |
| `dif` / `thr` | dif đang dùng / **ngưỡng cắt** (×100) — cắt khi `w ≤ thr` |
| `ph` / `arm` / `stp` | pha học (0 rảnh, 1 chờ lắng) / armed / `aLoaderStep` |
| `qw` `qr` `ci` | ô lưới đang tra; `ci = -1` = đang rơi về công thức |

> ⚠️ In ~95 ms/giây ở 9600 baud → jitter thời điểm cắt ~0,08 kg. **Đừng đánh giá độ chính xác khi debug bật.**

---

## B9. Bảng tham số `Config.h` + danh sách bẫy

| Macro | Giá trị | Đơn vị | Ý nghĩa |
|-------|---------|--------|---------|
| `MACHINE_HAS_SCALE_FEEDER` | 0 | — | 0 = máy không cân → **cả loader không biên dịch** |
| `MACHINE_BATCH_KG` | 3 | kg | mẻ danh định, dùng suy `LOADER_MIN_NETW` |
| `LOADER_MIN_BATCH_PCT` | 80 | % | phễu phải còn ≥ 80 % một mẻ mới cho hút |
| `FEEDER_DIF_FIXED` | **100** | ×100 kg | >0 = ghim dif, bỏ qua học |
| `FEEDER_DIF_MAX` | 25 | ×10 kg | trần an toàn dif = 2,5 kg |
| `FEEDER_TKG_DEFAULT` | 190 | ×10 ms/kg | `T_kg` mồi cho công thức khi bảng rỗng |
| `FEEDER_ADAPT_EN` | 1 | — | bật vòng tự học |
| `FEEDER_ADAPT_GAIN` | 30 | ×100 | EMA kéo 0,30/mẻ |
| `FEEDER_CFG_MAX` | 48 | ô | kích thước bảng học |
| `FEEDER_W_BUCKET` | 5 | kg | bước lưới cân |
| `FEEDER_ROR_BUCKET10` | 25 | ×10 kg/phút | bước lưới ror = 2,5 |
| `FEEDER_SEED_WKG` | 100 | kg | cân tham chiếu dựng bảng seed |
| `FEEDER_STABLE_ROR` | 20 | ×100 kg/phút | ≤ 0,2 kg/phút coi là cân đứng yên |
| `FEEDER_SETTLE_MIN_MS` | 1500 | ms | chờ tối thiểu cho cà lắng |
| `FEEDER_SETTLE_TMO` | 15 | s | hết hạn chờ ổn định |
| `FEEDER_WSTART_DELAY_MS` | 3000 | ms | khe đo offset lực hút |
| `FEEDER_OFFSET_MAX100` | 30 | ×100 kg | trần offset hợp lệ 0,30 kg |
| `FEEDER_MIN_BATCH100` | 50 | ×100 kg | mẻ < 0,5 kg = nhiễu, không học |
| `LOADER_SD_LOG_EN` | 0 | — | 0 = loader không ghi thẻ |
| `LOADER_DEBUG_EN` | 0 | — | 1 = in log loader không cần `enDebug` |
| `LOADER_CSV_MAX` | 400 | dòng | trần log |

Thanh ghi HMI: **6** nút feeder · **14** timer hút tối đa · **32** lượng cần hút · **33** bật auto-loader ·
**44** ngưỡng lực kéo vacuum · **91** `rorKG` đẩy lên HMI.

**Bẫy khi sửa code:**

1. `netW100` không được gán → cắt ngay lập tức, mẻ nào cũng thiếu.
2. Bỏ điều kiện `FEEDER_BTN_R == 0` khi tính `difNetW` → đích trôi theo phễu, không bao giờ chạm.
3. Dùng sườn 1 vòng thay `feederWasOff` → lỡ cạnh Modbus là mẻ chạy với số liệu mẻ trước.
4. Bỏ `adaptArmed` → nhiều dòng học từ một mẻ.
5. Đổi `FEEDER_WSTART_DELAY_MS` lên > ~5 s → đo offset nhằm lúc cà đã chảy.
6. So ngưỡng ở thang ×10 → giật bậc 0,1 kg.
7. Tên file SD dài hơn 8.3 → tạo file **thất bại âm thầm**.
8. Bật lại `LOADER_SD_LOG_EN` → ghi thẻ trong lúc hút, nguy cơ kéo dài vòng quét / treo khi thẻ dở chứng.
9. Comment lệch thực tế ở hai chỗ đếm giây (B4.5) — tin hằng số, không tin comment.
10. Máy không cân mà quên `MACHINE_HAS_SCALE_FEEDER 0` → HMI cũ trả reg 33 = 1 → báo lỗi huỷ mẻ vô cớ.

---

## B10. Chỉnh nhanh phía firmware

(Phần chỉnh được ngoài hiện trường nằm ở **A6** và **A8** — bảng này chỉ dành cho người nạp firmware.)

| Triệu chứng | Xử lý |
|-------------|-------|
| Lệch đều một chiều (luôn thiếu / luôn dư) | chỉnh `FEEDER_DIF_FIXED` đúng bằng lượng lệch (0,20 kg = 20) |
| Lệch ngẫu nhiên ±0,1 kg | đã chạm trần phần cứng — đừng chỉnh phần mềm nữa (A9) |
| Mẻ nhỏ luôn dư | giữ dif cố định; **đừng** bật lại chế độ tra bảng theo `rorKG` |
| Muốn quay lại tự học | `FEEDER_DIF_FIXED 0` + xoá `loadcfg.csv` để học lại từ seed |
| Học mãi không hội tụ ở một ô | tăng `FEEDER_ADAPT_GAIN` (30 → 50) |
| Chờ quá lâu sau khi cắt mới chấm điểm | tăng `FEEDER_STABLE_ROR` (đổi lại: giảm chính xác) |
| Cần xem số liệu từng mẻ | bật `LOADER_DEBUG_EN 1` thay vì bật `LOADER_SD_LOG_EN` (tránh đụng thẻ lúc hút) |
