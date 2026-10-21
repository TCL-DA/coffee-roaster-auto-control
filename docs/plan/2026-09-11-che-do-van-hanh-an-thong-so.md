# Chế độ VẬN HÀNH — ẩn thông số mẻ rang, chỉ cho nhân viên thấy tiến độ

> Yêu cầu khách (11/09/2026): chủ máy rang ~10 mẻ mẫu bằng **chế độ rang lưu
> chương trình** → giao máy cho nhân viên chạy tự động. Nhân viên **không được
> thấy** thông số mẻ (nhiệt, giờ mốc, mức lửa, đường cong), chỉ thấy **tiến độ**
> và **biết xử lý khi lỗi** (máy tự tắt lửa; rang lố thì tự xả + báo động).
>
> Máy: **30 kg CMS bản rang ca cao**, **có cân + auto-loader + cảm biến áp hút**.
> Ngân sách: 10 địa chỉ HMI — thiết kế chốt dùng **8**, dư 2.
> Trạng thái: **CHƯA CODE**.

---

## 0. Mười lăm quyết định đã chốt (11/09/2026)

| # | Chốt |
|---|------|
| 1 | Giữ chốt 30/07: `$M17` = loại hạt (để dành), `$M18` = cờ lỗi + Xoá lỗi — **code `$M18` trong đợt này** |
| 2 | Máy **có cân + loader + cảm biến áp hút thật** ⇒ phải dựng `Config.h` riêng (`SCALE_FEEDER = 1`, `VACUUM_SENSOR = 1`), **không ô `$M` nào chết** |
| 3 | Lỗi nặng: **quá nhiệt → GIỮ hạt** (cắt lửa, trống + quạt chạy) · **hỏng cảm biến / mất Modbus → XẢ hạt** |
| 4 | **XẢ KHẨN dùng được bất cứ lúc nào** |
| 5 | **Nhân viên chỉ dùng HMI.** App là của chủ máy |
| 6 | Màn vận hành có 6 nhóm nút: Bắt đầu · Xả khẩn · Tắt lửa · Sấy lồng · Làm nguội/Xả khay · Tắt chuông/Xoá lỗi |
| 7 | Màn HMI: **copy** `112_Quanly\43_Update_CMS_26\100926\OTL-30H-100926_CMS.dpa` rồi sửa trên bản copy |
| 8 | **Không đụng cổng PC** (app + Artisan giữ nguyên). Rủi ro ghi vào **biên bản bàn giao** |
| 9 | Nhân viên được đổi: **số mẻ cả ca (`$M11`)**, **gạt nạp tay ↔ tự động (`$M33`)**, **kg mẻ (`$M32`)**, **chọn hồ sơ ngay trên HMI** |
| 10 | Nạp hạt **cả hai kiểu tuỳ ca** — nhân viên tự gạt |
| 11 | Giữa 2 mẻ: **nạp tự động → chạy tiếp luôn · nạp tay → chờ bấm TIẾP** |
| 12 | **Xả khẩn huỷ luôn cả chuỗi mẻ**, máy về chờ |
| 13 | Báo động: **chuông HMI là đủ**, không thêm còi/đèn ngoài |
| 14 | Mở khoá bằng **tài khoản có sẵn của HMI** (Delta security) ⇒ **không cần thanh ghi PIN** |
| 15 | **Bổ sung 10 dòng cảnh báo 413–422** vào bảng alarm của màn — vá luôn lỗ đang tồn tại |

---

## 1. La bàn

| | Việc | Ai làm |
|---|------|--------|
| **A** | **Ẩn số** — máy ngừng phát số liệu lên HMI khi đang khoá | firmware (chính) + HMI |
| **B** | **Tiến độ** — thay số bằng % + tên giai đoạn + thời gian còn lại | firmware tính, HMI vẽ |
| **C** | **Lỗi** — rút ~380 mã `STT_*` xuống **9 mã E** nhân viên hiểu được, kèm hành động máy tự làm | firmware |

Nguyên tắc: **ẩn ở firmware, không chỉ ẩn ở HMI.** Ẩn bằng cách xoá ô hiển thị là
ẩn giả — nạp lại màn cũ là số hiện lại hết.

Phạm vi đã khoanh theo chốt #8: **cổng PC không nằm trong phạm vi**. Việc ẩn này
chống **nhân viên đứng máy**, không chống người có laptop.

---

## 2. Tám thanh ghi

### 2.1. Bốn ô cấu hình `$M62..$M65` — vùng giữ khi mất điện

| $M | Tên | Dải | Mặc định | Ý nghĩa |
|----|-----|-----|---------|---------|
| 62 | `opMode` | 0/1 | 0 | `1` = ĐANG KHOÁ. Màn HMI ghi `0` sau khi đăng nhập đúng tài khoản (chốt #14) |
| 63 | `opProfileMask` | bit 0–15 | 1023 | Hồ sơ nào nhân viên được chọn — bit0 = hồ sơ 1 … bit15 = hồ sơ 16. Chủ máy đặt trên app |
| 64 | `opOverTemp` | 0–200 | 50 | Biên **rang lố theo nhiệt**, ×0.1 °C trên nhiệt xả → tự xả. `0` = tắt |
| 65 | `opOverTime` | 0–600 | 90 | Biên **rang lố theo giờ**, giây trễ hơn hồ sơ → tự xả. `0` = tắt |

`$M66`, `$M67` **để trống dự phòng**.

Không còn ô PIN: đăng nhập dùng **tài khoản/security level của HMI** (chốt #14).
Màn `Login` (id 15) trong file .dpa hiện là **vỏ rỗng** — 7 hình chữ nhật + 1 nút
chuyển màn, chưa có ô nhập nào — nên phần này phải dựng thật, không phải chỉ sửa.

Mask 16 bit phủ hồ sơ 1–16. Hồ sơ giao khách **phải nằm trong slot 1–16** (chủ
máy chọn slot lúc bấm Lưu hồ sơ) — ghi vào tài liệu bàn giao.

### 2.2. Một ô đã chốt từ 30/07, code trong đợt này

| $M | Tên | Ý nghĩa |
|----|-----|---------|
| 18 | `errClear` | Ghi `1` = xoá cờ lỗi chốt; firmware xoá xong tự đưa về `0`. Lỗi 🔴 **không xoá được** khi điều kiện lỗi còn |

`$M18` nằm **trong khung 61 thanh ghi đang đọc** ⇒ không tốn khung, không tốn ô
ngân sách. `$M17` (loại hạt) vẫn để dành.

### 2.3. Bốn ô hiển thị `40126..40129` — firmware chỉ GHI

| Địa chỉ | Tên | Nội dung |
|---------|-----|---------|
| 126 | `OP_PROGRESS_W` | Tiến độ mẻ, 0–100 % |
| 127 | `OP_PHASE_W` | Mã giai đoạn 0–9 (HMI đổi ra chữ qua Text Table) |
| 128 | `OP_REMAIN_W` | Ước tính còn lại, **giây** (0 = sắp xong) |
| 129 | `OP_ALARM_W` | Mã lỗi rút gọn E1–E9, `0` = bình thường |

Đã soát: **126–150 trống hoàn toàn** (125 = `TUNE_PERCENT_W`, 151–152 =
`warnDeleteProfile` / `turnON40001`). Ghi kiểu đổi-mới-ghi → không thêm khung.

### 2.4. Ô dùng lại, không tốn địa chỉ mới

| $M | Dùng làm gì trên màn vận hành |
|----|------------------------------|
| 11 | Ô nhập **số mẻ cả ca** (chốt #9). Firmware kẹp **1–20** |
| 32 | Ô nhập **kg mẻ**. HMI hiện **chưa có ô này** → phải thêm. ⚠ *Giả định chờ xác nhận:* firmware kẹp **±20 % quanh 30 kg (24–36)** — hồ sơ rang soạn theo đúng kg đó, lệch nhiều là lệch chất lượng mà không ai biết tại sao |
| 33 | Ô gạt **nạp tay ↔ nạp tự động** (chốt #10) |
| 16 (`SELECT_FILE`) | Số hồ sơ đang chọn — nhận từ 10 nút "Mẻ 1..10" trên màn vận hành, lọc qua `$M63` |

### 2.5. Kết quả soát `$M` hiện trạng (11/09)

Soát toàn bộ `$M1..$M61` đối chiếu mọi lần đọc trong `include/` + `src/`:

- **Không ô nào chết** — cả 61 ô đều có chỗ đọc thật.
- **Chỉ 2 ô trống**: `$M17`, `$M18` — cả hai đã bị chốt từ 30/07.
- Ô *chết theo cấu hình* (`#if MACHINE_HAS_*`): `$M32/33/38–43` (cân + loader),
  `$M44/47–50` (vacuum). **Máy này bật đủ cả hai** ⇒ không ô nào chết. Kể cả có,
  **không tái dùng** — để `$M` mang cùng một nghĩa trên mọi máy.

⚠ **Bẫy khung Modbus:** `rwMemHMI()` (gọi **mỗi vòng lặp**, `main.cpp:122`) đọc
**61** thanh ghi, trần buffer `ModbusMaster` là **64**. Bốn ô mới đẩy lên 65 →
**vượt trần**. Cách làm: thêm `rwMemHMICfg()` đọc riêng `$M62..$M65` nhịp
**2 giây/lần**. Chi phí ≈ 3 ms mỗi 2 giây.

`iMemHMI[62]` → `iMemHMI[66]`; `PCL_CFG_MAXIDX` 61 → 65.

> Số cũ **không bị đẩy** (chỉ thêm đuôi 62–65), nên màn cũ + firmware mới vẫn
> chạy — chỉ là `$M62` đọc về 0 ⇒ **máy không khoá**. Fail-open, cố ý.

---

## 3. Tiến độ tính thế nào

```
progress% = timeRoast * 100 / rtDROP        (kẹp 0..99 cho tới khi xả thật)
remain_s  = rtDROP - timeRoast              (kẹp ≥ 0)
```

`rtDROP` = giây xả của mẻ mẫu, `sdRead()` đã có sẵn. Hai chốt để thanh tiến độ
không nói dối:

1. **Không bao giờ lùi.** Giữ `opProgLast`, chỉ cho tăng.
2. **Neo theo mốc thật.** Đạt DE / FCs / DEV thì kéo % lên ít nhất bằng % của mốc
   đó trong hồ sơ mẫu.

Mẻ lê quá giờ (`endBatchRescue` đang bù gas) → `remain = 0`, HMI hiện "sắp xong",
không hiện số âm.

Giai đoạn `OP_PHASE_W`:

| Mã | Chữ trên màn | Suy từ |
|----|-------------|--------|
| 0 | Nghỉ | `START_BTN_R = 0`, `wuState = WU_IDLE` |
| 1 | Đang sấy lồng | `wuState != WU_IDLE` |
| 2 | Chờ nạp hạt | `STP_CHECK` / `STP_CHARGE` (nạp tay) |
| 3 | Đang nạp hạt | `aLoaderStep` đang chạy (nạp tự động) |
| 4 | Sấy hạt | `STP_TP` |
| 5 | Chuyển vàng | `STP_YELLOW` |
| 6 | Sắp nổ | `STP_FCS` |
| 7 | Phát triển | `STP_DEV` |
| 8 | Đang xả / Làm nguội | `STP_DROP` · `coolStep != 0` · `STP_ESCAPE` |
| 9 | Xong mẻ | `STP_LOOP_1/2`, chờ mẻ kế |

---

## 4. Bảng lỗi cho nhân viên (9 mã)

Ánh xạ trong file mới `include/OperatorMode.h`, hàm `opAlarmFromStt(uint16_t)`.
Mức: 🔴 dừng máy · 🟠 máy tự xử lý rồi báo · 🟡 theo dõi.
Hành động theo **chốt #3**: quá nhiệt **giữ hạt**, máy mù **xả hạt**.

| E | Mức | Chữ trên màn | Gộp từ `STT_*` | Máy TỰ làm | Nhân viên làm |
|---|-----|-------------|---------------|-----------|--------------|
| 1 | 🔴 | QUÁ NHIỆT — ĐÃ TẮT LỬA | 401, 413, 263, 264 | Cắt gas · **GIỮ hạt** · trống + quạt chạy tiếp | **Không mở cửa.** Gọi kỹ thuật |
| 2 | 🔴 | LỬA KHÔNG LÊN | 410, 414, 403, 164 | Cắt gas, huỷ mẻ | Kiểm bình gas / van. Gọi kỹ thuật |
| 3 | 🔴 | HỎNG CẢM BIẾN NHIỆT | 404, 405, 265, 266, 271 | Cắt gas · **XẢ hạt** · chạy bồn nguội | Để riêng mẻ đó. Gọi kỹ thuật |
| 4 | 🔴 | MẤT KẾT NỐI THIẾT BỊ | 281–287, 406, 407, 408 | Cắt gas · **XẢ hạt** nếu đang có mẻ | Tắt nguồn 10 s rồi bật lại. Còn lỗi → gọi |
| 5 | 🟠 | RANG LỐ — ĐÃ XẢ | mã mới **422** | Cắt gas + mở cửa xả + chuông | Để riêng mẻ này, không trộn lô. Báo chủ |
| 6 | 🟠 | MẺ LÊ, KHÔNG LÊN NHIỆT | 421, 327 | Bù gas hết mức rồi báo | Xem bình gas còn không. Báo chủ |
| 7 | 🔴 | CỬA XẢ KHÔNG ĐÓNG | 417 | Dừng, **không cho nạp mẻ mới** | Nhìn cửa xả, gọi kỹ thuật |
| 8 | 🔴 | LỖI HỒ SƠ / THẺ NHỚ | 103, 120, 381–385, 409 | Không cho bấm BẮT ĐẦU | Chọn mẻ khác, hoặc gọi chủ máy |
| 9 | 🟡 | MẺ ĐANG DÀI HƠN MẪU | 416 | Chuông 1 nhịp, vẫn chạy tiếp | Theo dõi, không cần làm gì |

Chỉ mã **nặng nhất còn hiệu lực** nằm trong `OP_ALARM_W`. Xoá bằng nút **Xoá lỗi**
(`$M18 = 1`): 🟠/🟡 xoá ngay; 🔴 **chỉ xoá được khi điều kiện lỗi đã hết**.

> Vì sao cảm biến hỏng thì xả mà quá nhiệt thì giữ: mở cửa lúc đang cháy là đưa
> thêm oxy vào buồng; còn máy mù thì rang tiếp chắc chắn hỏng mẻ.

### 4.1. Vá lỗ đang tồn tại: 10 dòng cảnh báo thiếu (chốt #15)

Bảng alarm của màn (đọc `W40041` = `STT_W`) có **275 dòng, chỉ tới mã 412**.
Firmware đã bắn 9 mã sau từ 30/07 và 10/09 mà **màn không có chữ nào** — bắn ra
là màn im lặng:

| Mã | Nội dung (lấy từ `MachineStatus.h`) |
|----|------------------------------------|
| 413 | BÁO CHÁY: tốc độ tăng nhiệt BT > 500 °C/min — đã tắt lửa |
| 414 | Chờ lửa quá lâu ở bước chờ gas — đã cắt gas, huỷ mẻ |
| 415 | Trượt cửa sổ bắt TP — chốt TP theo đáy đã ghi (số ước lượng) |
| 416 | Pha phát triển vượt ngưỡng — kiểm nhiệt xả |
| 417 | Cửa xả không đóng lại sau khi xả — đã dừng, không nạp mẻ mới |
| 418 | Đang sấy lồng — đã huỷ tự chỉnh gió (dùng chung ô tiến trình) |
| 419 | Bảng học gió đã đầy — dữ liệu quét bị thiếu |
| 420 | BT đứng sát nhiệt xả — đang bù thêm gas để về đích |
| 421 | Bù hết mức mà BT vẫn không lên — kiểm gas/béc, cân nhắc xả tay |
| **422** | **RANG LỐ — đã cắt gas và xả mẻ** (mã mới của đợt này) |

Việc này **áp cho mọi máy 30 kg**, không riêng khách này.

---

## 5. Ba chốt chống rang lố

Đặt **trước `switch(progStep)`** trong `programScan()`, cạnh `fireCutFlag` — để
đúng kể cả khi máy trạng thái kẹt (bài học R2 / R7).

Cổng chung: `timeRoastEn == 1 && timeRoast > autoDropMinSec()`.

| # | Điều kiện | Hành động |
|---|-----------|----------|
| 1 | `BT ≥ dropTempTarget() + opOverTemp` | Cắt gas → `DROP_BTN_W = 1` → `E5` (422) + chuông |
| 2 | AUTO có hồ sơ và `timeRoast > rtDROP + opOverTime` | Cắt gas → xả → `E5` + chuông |
| 3 | `opMode = 1` mà hồ sơ chưa nạp được (`sdProfileLoadOK = 0`) | Chặn `START` → `E8` |

Chốt 1 và 2 **độc lập** với auto-drop hiện có — auto-drop là đường chạy bình
thường, hai chốt này là lưới an toàn khi nó không nổ.

`STT_WARN_DEV_TOO_LONG` (416) giữ ở mức **chỉ báo** (= E9).

---

## 6. Màn VẬN HÀNH

**Thấy:** vòng tiến độ % · tên giai đoạn · thời gian còn lại · "Mẻ số N" · số mẻ
còn lại của ca · đèn 3 màu · vùng chữ mã lỗi E1–E9.
**Không thấy:** mọi con số nhiệt, giờ mốc, mức lửa/gió/trống, ngày giờ hồ sơ,
đường cong.

| Thành phần | Hành vi |
|-----------|---------|
| **10 nút "Mẻ 1..10"** | Ghi `SELECT_FILE`; nút nào không có bit trong `$M63` thì ẩn/xám |
| **Ô số mẻ cả ca** | Ghi `$M11`, firmware kẹp 1–20 |
| **Ô kg mẻ** | Ghi `$M32`, firmware kẹp 24–36 *(giả định chờ xác nhận)* |
| **Gạt nạp tay ↔ tự động** | Ghi `$M33` |
| **BẮT ĐẦU** | Bật `START_BTN`. Bị chặn khi có lỗi 🔴 |
| **TIẾP** | Chỉ hiện khi đang nạp TAY và vừa xong một mẻ (chốt #11) |
| **XẢ KHẨN** | Mở cửa xả bất cứ lúc nào; **huỷ cả chuỗi mẻ**, `$M11` về 1, máy về chờ (chốt #12) |
| **TẮT LỬA** | `START_GAS_BTN = 0` ngay, không hỏi |
| **SẤY LỒNG** | Preheat theo `$M51/$M52`; chỉ hiện "Đang sấy lồng" + % |
| **LÀM NGUỘI / XẢ KHAY** | Bật bồn nguội, mở cửa khay |
| **TẮT CHUÔNG / XOÁ LỖI** | `$M18 = 1` |

Giữa 2 mẻ (chốt #11): `$M33 = 1` (tự động) → chạy tiếp luôn như `$M11` hiện nay;
`$M33 = 0` (nạp tay) → dừng ở "Xong mẻ", chờ bấm **TIẾP**.

---

## 7. Khoá cái gì khi `opMode = 1`

| Đường rò | Xử lý |
|---------|-------|
| Ô số trên HMI (BT / ET / RoR / gas / gió / trống — reg 60–92) | Firmware **ngừng ghi**, ghi 0 một lần khi vào khoá |
| Thông số hồ sơ (reg 103–118) | Ngừng ghi, ghi 0 |
| Mốc mẻ đang chạy (reg 70–83) | Ngừng ghi, ghi 0 |
| Bảng ngày giờ hồ sơ (reg 600–809) | **Ngừng đẩy** — `loadAllProfileDates()` bỏ qua khi khoá |
| Đồ thị xu hướng | `SAMPLE_COIL = 0` |
| Màn PROFILE (6, 12, 13), History (10), Comparator (19) | **Khoá bằng security level của HMI** (chốt #14) — không vào được khi chưa đăng nhập |
| Nút thủ công khác | `LOCK_BUTTON = 1` ngay khi vào khoá; chừa đúng các nút ở §6 |
| Xoá hồ sơ | `DEL_PROFILE` / `DEL_ALLPROFILE` bị firmware bỏ qua |
| Chọn hồ sơ ngoài danh sách | `SELECT_FILE` không có bit trong `$M63` → firmware từ chối, giữ giá trị cũ |
| Chế độ rang | Ép `progStatus = STT_PROGRAM_AUTO` — cấm rang tay ghi hồ sơ |
| **Cổng PC (app + Artisan)** | **KHÔNG đụng** (chốt #8) |

**Tự khoá lại**: sau `OP_RELOCK_SEC` (`Config.h`, mặc định 600 s) không chạm màn
thì firmware ghi `$M62 = 1`. **Không** tự khoá khi đang rang hoặc đang sấy lồng.

---

## 8. Nhật ký `/oplog.csv` (chốt #3 nhật ký)

Màn 23 "Operation logging" đã có bảng lịch sử cảnh báo, nhưng không gắn được số
hồ sơ và khó mang đi. Thêm file riêng, mỗi dòng một sự kiện:

```
DD/MM/YY,HH:MM:SS,SUKIEN,HOSO,MAE
11/09/26,08:14:02,UNLOCK,,
11/09/26,08:21:37,BATCH_START,3,
11/09/26,08:36:10,OVER_ROAST,3,5
11/09/26,08:36:12,EMERGENCY_DROP,3,
11/09/26,17:02:55,LOCK,,
```

Chỉ ghi mốc quan trọng (mở khoá, khoá lại, bắt đầu/kết thúc mẻ, lỗi 🔴, xả khẩn,
rang lố) — vài chục dòng mỗi ngày, không đụng luồng ghi CSV của mẻ. Ghi qua
`sdEnsure()` sẵn có, có cắt file khi quá 2000 dòng.

---

## 9. Giới hạn bảo mật — ghi vào biên bản bàn giao

Mức **chống nhân viên đứng máy**, không chống người có laptop:

- **Cổng PC để mở theo yêu cầu chủ máy** (chốt #8). Cắm laptop chạy Artisan vào
  UART4 là đọc được BT / ET / gas thật kể cả khi màn đang khoá.
- **Thẻ SD là lỗ to nhất.** Hồ sơ CSV nằm nguyên trên thẻ. Mã hoá trên STM32F103
  không đáng làm (RAM 20 KB, sát trần).
- **Đầu cắm RS485 trong tủ** — cắm thẳng vào bus là đọc được đồng hồ nhiệt BT/ET.
- **Tài khoản HMI** chỉ mạnh bằng cách chủ máy giữ mật khẩu; ai có DIAScreen +
  cáp vẫn mở được file màn.

⇒ Mấy lỗ này bịt bằng **khoá tủ điện + niêm phong**, không bịt bằng phần mềm.

---

## 10. Các bước làm

| GĐ | Việc | File đụng tới | Ước lượng |
|----|------|--------------|----------|
| **1** | Spec trước khi code | `quy-trinh-dieu-khien-may-rang/references/quy-trinh-phu.md` (máy phụ `opState`) + `quyet-dinh-cho-code.md` (đánh dấu `$M18` đã làm), `rang-ca-phe/references/registers-M.md` | 0.5 ngày |
| **2** | `Config.h` riêng cho máy này | Bật `MACHINE_HAS_SCALE_FEEDER` + `MACHINE_HAS_VACUUM_SENSOR`, thêm `MACHINE_HAS_OPERATOR_MODE`, `OP_RELOCK_SEC`, 2 mặc định biên. **Đo RAM ngay** — bật cân + vacuum là thêm mảng loader | 0.5 ngày |
| **3** | Nền thanh ghi | `Define.h` (8 địa chỉ + `$M18`, `iMemHMI[66]`), `MachineStatus.h` (mã 422 + whitelist) | 0.5 ngày |
| **4** | `include/OperatorMode.h` — file mới | `opTick()` tiến độ/giai đoạn · `opAlarmFromStt()` 9 mã · `opErrLatch()/opErrClear()` (`$M18`) · `opMaskHmi()` ngừng ghi số · `opOverRoastGuard()` 3 chốt · `opErrAction()` giữ-hay-xả · `opLogWrite()` oplog.csv | 2 ngày |
| **5** | Móc vào luồng | `Program.h` (guard cạnh `fireCutFlag`, `opTick()`, chặn `loadAllProfileDates`, nhánh TIẾP giữa 2 mẻ, xả khẩn huỷ chuỗi), `Modbus_Master.h` (`rwMemHMICfg()` + chặn ghi số + kẹp dải `$M11/$M32` + lọc `SELECT_FILE` theo mask) | 1.5 ngày |
| **6** | Màn HMI | Copy `100926/OTL-30H-100926_CMS.dpa`; dựng màn VẬN HÀNH (10 nút mẻ + 3 ô nhập + 6 nhóm nút + vòng %); dựng thật màn Login (đang là vỏ rỗng) + gán security level cho màn 6/10/12/13/19; **thêm 10 dòng alarm 413–422**; Text Table giai đoạn + 9 mã E. Skill `dopsoft-dpa`, xuất ảnh duyệt trước khi nạp | 2 ngày |
| **7** | App + API | `PC_Link_Map.h` `MAXIDX` 61→65, `protocol/pc_link.json` + `gen_pc_link.py`, `tools/pc_link_map.py`; app thêm ô **"Bàn giao ca"**: tích hồ sơ cho phép → `$M63`, nút KHOÁ MÁY → `$M62 = 1` | 1 ngày |
| **8** | Test | `tools/roaster_sim` 12 kịch bản (lố nhiệt, lố giờ, mất lửa, rơi cảm biến, mất Modbus, cửa kẹt, hồ sơ hỏng, chọn hồ sơ ngoài mask, xả khẩn giữa chuỗi, nạp tay vs tự động giữa 2 mẻ, mất điện giữa mẻ, tự khoá lại) → **2 mẻ máy thật** | 1.5 ngày |
| **9** | Tài liệu | 1 trang A4 dán cạnh máy (9 mã lỗi + các nút) bằng skill `manual-otl`; 2 trang cho chủ máy; **biên bản bàn giao** ghi §9 | 1 ngày |

Tổng ≈ **10,5 ngày công**.

---

## 11. Rủi ro & bẫy đã biết

| Rủi ro | Vì sao | Chặn thế nào |
|--------|--------|-------------|
| Khung `$M` vượt buffer 64 | `rwMemHMI()` đã 61/64, gọi mỗi vòng lặp | Khung riêng `rwMemHMICfg()` 4 ô, nhịp 2 s |
| **Hết RAM** | Bật `SCALE_FEEDER` + `VACUUM_SENSOR` kéo theo mảng loader + PID gió, **cộng** với tính năng mới. RAM tĩnh vốn đã sát trần | Đo `/memory-check` **ngay sau GĐ2**, trước khi viết `OperatorMode.h`. Nếu vượt 88 % thì phải hạ `PROFILE_MAX_SECONDS` trước |
| Chốt tự xả bắn oan | Hồ sơ ca cao xả **thấp hơn** nhiệt nạp — đã mất mẻ vì chuyện này (R7), mà máy này đúng là bản ca cao | Cổng `timeRoastEn && timeRoast > autoDropMinSec()`; `opOverTemp` tính trên `dropTempTarget()` |
| Nhân viên đổi kg làm lệch chất lượng | Hồ sơ soạn theo đúng kg đó | Kẹp ±20 % *(chờ anh xác nhận)*; ghi kg vào `oplog.csv` để truy được |
| Tự khoá lại cắt tay chủ máy | Đang chỉnh thì màn nhảy về | Không tự khoá khi `START_BTN_R = 1` hoặc `wuState != WU_IDLE` |
| Nhân viên kẹt vì máy khoá cứng | Lỗi 🔴 chặn START | XẢ KHẨN + TẮT LỬA **luôn sống** |
| Xoá lỗi thành nút "bịt mắt" | Bấm xoá rồi chạy tiếp khi máy vẫn hỏng | Mã 🔴 chỉ xoá được khi điều kiện lỗi đã hết |
| Màn cũ + firmware mới | `$M62` đọc về 0 | Mặc định **không khoá** (fail-open) — cố ý |
| Sửa nhầm màn đang chạy của khách | Màn gốc là bản 10/09 đang dùng thật | Làm trên **bản copy**, tên theo ngày mới, giữ nguyên bản 100926 |
| Thẻ SD treo máy khi ghi oplog | Đã có ca treo giữa lúc hút | Dùng `sdEnsure()` + giới hạn ghi theo sự kiện, **không** ghi mỗi giây |

---

## 12. Còn chờ xác nhận

1. **Dải kg cho nhân viên nhập** — đang giả định 24–36 kg (±20 % quanh 30 kg).

---

## Rev 2 — soát lại ngày 08/10/2026 (đêm, Claude) + lát code 1

### Đã đổi so với 11/09

| Mục kế hoạch | Hiện trạng 08/10 | Hệ quả |
|---|---|---|
| §4.1 vá 10 dòng cảnh báo 413–422 | HMI v28 (AP4I) đã có chữ cho **413–421** (đợt L45); rà 08/10: 174 mã firmware được hiện, HMI thiếu **0** dòng | Chỉ còn **422** (mã mới của chế độ này) |
| Chốt #7: sửa trên bản copy `OTL-30H-100926_CMS.dpa` | Dòng HMI mới là **v28** (OTL-30A, đã 22+ màn, có khoá liên động, cảnh báo chốt, đồ thị mốc) | **Cần chủ máy quyết**: dựng màn VẬN HÀNH trên v28 hay trên bản 100926 cũ |
| §2.3 W40126…129, §2.1 `$M62…65` | Soát 08/10: **vẫn trống** ở firmware `6e33f60` và HMI AP4I | Giữ nguyên địa chỉ |
| §2.1 `iMemHMI[62]`, khung `rwMemHMI` 61/64 | Không đổi | Vẫn cần khung riêng `rwMemHMICfg()` |
| Chốt #2 `Config.h` riêng (cân + áp hút) | `Config.h` hiện tại (máy M03) **đã bật** cân + áp hút + relay IO, RAM 73 % | Đo RAM khi thêm tính năng, ngưỡng 88 % |
| §9 giới hạn bảo mật | Từ 07/10 có thêm **web 6081** (số liệu sống, Excel, báo cáo theo mẫu) và **Lua ghi mẻ ra USB** trên panel | Hai đường lộ số MỚI, phải ghi vào biên bản bàn giao — hoặc: khi `opMode = 1` thì web chỉ hiện tiến độ, Lua không ghi đường cong |

### Lát 1 đã làm (chờ duyệt, CHƯA commit, CHƯA nạp)

Bản vá `docs/plan/2026-10-08_che-do-van-hanh_lat-1.patch` (gốc `6e33f60`, 186 dòng, áp sạch):

- `include/OperatorMode.h` (mới): hàm THUẦN `opPhase()` (giai đoạn 0–9), `opProgress()` (không lùi, neo mốc, chưa xả thì ≤ 99 %),
  `opRemain()`, `opAlarmFromStt()` (9 mã E theo §4), `opMucE()`, `opNangHon()`, `opXoaDuoc()` (đỏ chỉ xoá khi hết điều kiện),
  `opCanXaHat()` (quá nhiệt GIỮ hạt, máy mù XẢ — chốt #3). **Chưa gọi ở đâu.**
- `Define.h`: khai báo `OP_PROGRESS_W 126 … OP_ALARM_W 129` (chưa ghi).
- `tools/op_mode_test/`: test trên PC (zig c++), STP_* trích thẳng từ `Define.h` — **31/31**; ca phá (cho E1 thành xả hạt) bị bắt.
- Build ARM: RAM 35 900 B / Flash 106 720 B — **trùng từng byte bản gốc** → lát 1 không đổi hành vi máy.

### Cần chủ máy quyết trước lát 2

1. Màn VẬN HÀNH dựng trên **v28** (đề nghị — cùng dòng đang phát triển, đã có cảnh báo chốt + đăng nhập) hay trên bản 100926?
2. Web 6081 + Lua USB khi máy đang khoá: **ẩn** (web chỉ tiến độ, Lua không ghi đường cong) hay **giữ** (ghi vào biên bản)?
3. Dải kg nhân viên được nhập (§12, vẫn giả định 24–36 kg).

## Rev 3 — yêu cầu khách "Master / Công nhân" (08/10/2026)

Khách muốn phân quyền: **Master** (thợ rang giỏi) toàn quyền; **công nhân** chỉ rang auto, **không được xem giản đồ, nhiệt độ, gas, gió** — chỉ biết đang rang **hồ sơ số mấy**, không biết thông số hồ sơ. Đúng là chế độ VẬN HÀNH của kế hoạch này; chủ máy chốt thêm 4 điểm:

| # | Chốt 08/10 | Thay đổi so với Rev 2 |
|---|---|---|
| 16 | **Mỗi công nhân một PIN** (biết ai rang mẻ nào) | Chốt #6 cũ "không có ô PIN" chỉ còn đúng cho **Master** (mở khoá bằng tài khoản HMI). Công nhân: chọn tên → PIN 6 số → vào màn VẬN HÀNH (vẫn ẩn số). Tên công nhân ghi vào ô "người vận hành" + `oplog.csv` + nhật ký web. Cách lưu PIN theo kết quả đo tài khoản Delta (kế hoạch tài khoản T-ACC-01, Q12): dùng tài khoản Delta cấp 1, hoặc bảng PIN trong Recipe so bằng macro (đường lui) |
| 17 | **Web 6081: công nhân chỉ thấy tiến độ như HMI** | Bổ sung §9 Rev 2: tài khoản web "Công nhân" chỉ xem màn VẬN HÀNH; thanh số liệu trên cùng, danh sách mẻ, báo cáo / Excel, xuất Artisan, thẻ nhớ **chỉ Master**. Khi `opMode = 1` board ghi 0 nên web / Lua cũng trống ở nguồn — lớp web là lớp thứ hai cho dữ liệu mẻ **cũ** đã lưu trên PC |
| 18 | **30 hồ sơ** (khớp 3 trang hồ sơ v28) | Mặt nạ 30 bit cần **2 ô**: `$M63` (hồ sơ 1–16) + ô mới `$M66` (17–30) → `iMemHMI` thêm 1 ô, khung `rwMemHMICfg()` 5 ô. Màn VẬN HÀNH: lưới nút "Hồ sơ N" chỉ hiện số được Master tích |
| 19 | **Dựng trên HMI v28** | Trả lời câu 1 "Cần chủ máy quyết trước lát 2" — dùng dòng v28 (đã có cảnh báo chốt, đồ thị mốc, khoá liên động) |

**Thêm vào khoá khi `opMode = 1`** (§7): Lua ghi mẻ ra USB **không ghi đường cong** (chỉ ghi số mẻ, hồ sơ số, giờ bắt đầu / kết thúc, mã lỗi); web 6081 theo chốt #17.

**Chủ máy chốt thêm 08/10/2026 (thay "giả định 24–36" ở §6, §12):**

| # | Chốt | Ghi chú |
|---|------|---------|
| 20 | Công nhân nhập kg mẻ **trong dải Master đặt** (min / max theo máy; ngoài dải máy từ chối, giữ số cũ) | thêm 2 ô cấu hình min / max (mặc định máy 30 kg = 24 / 36) → khung `rwMemHMICfg()` thành **7 ô**; chọn số `$M` khi code, soát `[[pc_link_shared_map]]` trước |
| 21 | Công nhân chỉnh được **số mẻ cả ca `$M11`** và **nạp tay ↔ tự động `$M33`** — không gì khác | giữ như §6 |
| 22 | Đang rang từ xa mà web rớt mạng > 60 s → **rang tiếp** theo hồ sơ, khoá tăng gas, chuông + chữ "Mất kết nối web" trên panel | Q15 kế hoạch tài khoản (gói R1) |
| 23 | **Gói VH làm TRƯỚC gói R1** — tuần 45–51/2026 | chỉ cần R0 (đăng nhập web theo người) |

**Công thêm:** web ~2 ngày + PIN / 30 hồ sơ ~1 ngày → tổng ≈ **13,5 ngày công**. Trong kế hoạch tài khoản (`113_HMI\…\bao-cao\DE-XUAT_quan-ly-tai-khoan_chuan-EU.md`) đây là gói bán riêng **VH — Master / Công nhân**.

## Lịch sử

- **2026-10-08** — Rev 3b: chốt #20–#23 (dải kg Master đặt, công nhân chỉnh số mẻ ca + nạp tay/tự động, rớt mạng rang tiếp, VH trước R1).
- **2026-10-08** — Rev 3: yêu cầu khách Master / Công nhân; chốt #16–#19 (PIN công nhân, web chỉ tiến độ, 30 hồ sơ, dựng trên v28).
- **2026-10-08** — Rev 2: soát lại theo hiện trạng (v28, FW `6e33f60`, web 6081); lát code 1 (hàm thuần + test 31/31), chưa móc vào luồng.

- **2026-09-11** — Lập kế hoạch; soát hết `$M1..$M61` (không ô nào chết; chỉ
  `$M17/$M18` trống và đã bị chốt trước); soát file `.dpa` 10/09 (phát hiện bảng
  cảnh báo thiếu mã 413–421, màn Login là vỏ rỗng, đã có màn Operation logging).
  Chốt 15 quyết định với chủ máy, ngân sách còn **8/10 ô**.
  **Chưa code, chưa build, chưa flash.**
