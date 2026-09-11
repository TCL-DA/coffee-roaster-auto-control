# Kế hoạch — Chống lê/stall đoạn cuối mẻ AUTO

**Ngày:** 10/09/2026 · **Trạng thái:** CHƯA CODE — 4 quyết định thiết kế ĐÃ CHỐT 10/09/2026
**Liên quan:** [plan-auto-profile-replay.md](plan-auto-profile-replay.md) (lo chiều RoR **vượt cao**; bản này lo chiều RoR **tụt** + đuôi file)
**Chạm vào:** `include/Program.h`, `include/Define.h`, `include/Config.h`, `include/RoR_Control.h`

---

## 1. Triệu chứng khởi nguồn

Mẻ AUTO, hồ sơ mẫu DEV 4 phút (FCs 199 °C → DROP 217 °C). Gần xả, BT đứng ở
216 °C và RoR đột ngột tụt dưới 2 °C/phút. Máy không tự gỡ được.

Soát code ra **hai nguyên nhân độc lập**, phải vá riêng.

---

## 2. Nguyên nhân A — `lastTimeSD` đi vào đuôi làm nguội của file mẫu

### Cơ chế

`sdRead()` đọc CSV nhận **mọi dòng có Time2 khác rỗng** (`Program.h:511-570`).
Nó ghi nhận `csvDropIdx` khi gặp event `DROP` (`Program.h:537`) nhưng **không
`break`** — đọc tiếp tới hết file. Nên `sdTempTi` = **giây cuối FILE**, không
phải giây cuối MẺ.

`calibProgram()` dùng `if(timeRoast<=sdTempTi) lastTimeSD = timeRoast;`
(`Program.h:813`). Khi file có đuôi làm nguội, `lastTimeSD` **không đóng băng ở
giây xả** mà đi thẳng vào vùng làm nguội:

| Giây | `sdGas[]` | `sdAirflow[]` | `sdBT[]` | Máy làm gì |
|---|---|---|---|---|
| T_drop | gas DEV thấp | gió DEV | 2170 | bình thường |
| T_drop + 1 | **0** | thường **max** | đang tụt | **gas về 0, gió mở hết** |

Bộ bù còn cộng cùng chiều: BT thật cao hơn mục tiêu-làm-nguội →
`gasPercent -= numIncGas` → kẹp 0.

Kết quả: gas 0 + gió lớn khi mẻ còn ~1 °C nữa là tới nhiệt xả. BT không bao giờ
chạm `DROP_PRO_R`, auto-drop không kích, mà `STP_DEV` **không có điều kiện
thoát** (`Program.h:1869-1874`). Máy nằm rang tới khi thợ để ý.

### Nguồn file nào dính

| Nguồn | `sdTempTi` | Rủi ro |
|---|---|---|
| Máy tự ghi (SAVE) | = giây xả — logging dừng tại DROP (`timeAbsoluteEn=0`, `Program.h:2075`) | **an toàn** |
| Xuất từ Artisan | > giây xả — Artisan đếm Time2 tiếp suốt pha làm nguội | **dính** |

### Cách kiểm tra một file trong 30 giây

So `DROP:MM:SS` ở header với cột Time2 của **dòng cuối cùng**.
Time2 cuối > DROP ⇒ có đuôi ⇒ file này sẽ gây lỗi.

### Vá

Thêm 1 biến toàn cục, sửa 5 chỗ.

```c
// Define.h — cạnh sdTempTi
uint16_t sdProfileEndTi = 0;   // giây XẢ của mẫu; chặn lastTimeSD đi vào đuôi làm nguội
```

**a) Parser CSV** — ngay sau khi tính `rtDROP` (`Program.h:581-582`):

```c
sdProfileEndTi = (rtDROP > 0 && rtDROP < PROFILE_MAX_SECONDS) ? rtDROP : sdTempTi;
```

Dùng `rtDROP` chứ **không** dùng `csvDropIdx`: `rtDROP` đã hợp nhất hai nguồn
(event `DROP` trên dòng, và `DROP:` ở header) nên vẫn chạy được với file thợ
quên bấm event.

**b) Parser TXT** — sau `sscanf` dòng `P`, **trước** khi chia M/S
(`Program.h:706-714`), lúc đó `DROP_PRO_S_R` còn là tổng giây:

```c
sdProfileEndTi = (DROP_PRO_S_R > 0 && DROP_PRO_S_R < PROFILE_MAX_SECONDS)
               ? DROP_PRO_S_R : sdTempTi;
```

**c) Nhánh SD nạp lỗi** (`Program.h:745-754`) — thêm `sdProfileEndTi = 0;` cùng
chỗ reset các `*_PRO_R`.

**d) `calibProgram()`** (`Program.h:813`):

```c
if(timeRoast <= sdProfileEndTi) lastTimeSD = timeRoast;
```

**e) `rorCtrl_populateSdRorBT()`** (`RoR_Control.h:52`): đổi bound `t < sdTempTi`
→ `t < sdProfileEndTi`. Không bắt buộc về mặt đúng/sai (vùng đó không còn được
đọc) nhưng làm vòng lặp ngắn lại và giữ mảng sạch.

### Tác dụng phụ phải biết

`rorBT_pro` (`Program.h:134-138`) đọc `sdBT[lastTimeSD]` → sau khi kẹp, nó
**đóng băng ở RoR cuối mẫu**. Hiện `rorBT_pro` chỉ để hiển thị/so sánh, chưa lái
gì, nên chấp nhận được. Mục 4 bên dưới có dùng lại nó — phải nhớ nó là hằng số
sau khi kẹp.

### Việc kèm ngoài firmware

Cắt các dòng sau `DROP` trong file `.csv` nhập từ Artisan đang nằm trên thẻ.
Firmware guard là chốt cuối, nhưng file sạch vẫn tốt hơn (nạp nhanh hơn, đường
cong đúng khi app vẽ lại).

### Ngân sách

RAM +2 byte. Flash không đáng kể. **Rủi ro: THẤP** — thuần phòng thủ, không thêm
đường lái lửa nào.

---

## 3. Nguyên nhân B — bộ bù BT bị khoá cứng ở 0.6 °C cuối

Cái này xảy ra **kể cả khi file mẫu sạch** (không có đuôi).

### Cơ chế

Khi `lastTimeSD` đóng băng đúng ở giây xả, mục tiêu `sdBT[lastTimeSD]` **chính là
`DROP_PRO_R`**. Từ đó sai lệch `DROP_PRO_R − BT` **chỉ có thể co lại** khi RoR
còn dương.

Bộ bù đòi hai điều kiện đồng thời (`Program.h:852-871`):

1. `|BT − sdBT|` > deadband 6 (0.6 °C)
2. giữ được điều kiện 1 **liên tục 10 giây** để `timeCalibGas` đếm tới 10

Nhánh `else` reset `timeCalibGas = 0` ngay khi lệch chui lại vào deadband
(`Program.h:898-902`).

→ Bộ bù chỉ tính được bước nếu **lúc đóng băng, BT còn cách nhiệt xả hơn
`0.6 °C + 10×RoR`**. Ở RoR 2 °C/phút (0.033 °C/s) là **0.93 °C**.

Dựng lại tình huống thật (mẫu 0.75 đv/s, thật 0.33 đv/s, đóng băng tại T_end):

| Thời điểm | Mục tiêu | BT thật | Lệch | Bộ bù |
|---|---|---|---|---|
| T_end − 13 | 2160 | 2160 | 0 | im |
| T_end | **2170 (đóng băng)** | 2164.3 | 5.7 | im — cần > 6 |
| T_end + 8 | 2170 | 2167 | 3.0 | im — lệch đang co |
| T_end + 17 | 2170 | 2170 | 0 | AUTO-DROP |

**Bộ bù im suốt. Gas không được đụng tới.** Máy vẫn xả được, trễ ~17 giây.

Nếu RoR tụt sâu hơn (dưới ~1.2 °C/phút) thì cửa sổ mới đóng được, và bù ra
`numIncGas = 5%` → kẹp về `FcsCalib_R` ($M31). Với $M31 = 1 thì được +1.5 °C/ph
— nâng RoR từ 0.5 lên 2.0, vẫn lê.

### ⚠ Đề xuất cũ đã bị bác

Lượt phân tích trước có đề xuất "nới trần $M31 ở đoạn cuối". **Sai hướng** —
trần chỉ kẹp bước bù *sau khi nó được tính*, mà ở đây bước bù không bao giờ được
tính. Nới trần không thay đổi gì. Bỏ đề xuất đó.

Hai đường còn lại:

| | Cách | Đánh giá |
|---|---|---|
| B-1 | Rút cửa sổ 10 s xuống ngắn hơn khi gần nhiệt xả | ❌ **Không làm.** Con số 10 s đã chốt theo kinh nghiệm (khớp trễ nhiệt bếp→hạt 15–30 s, chống hunting). Đụng vào là mở lại một quyết định đã đóng, và ảnh hưởng cả mẻ chứ không riêng đoạn cuối. |
| B-2 | Thêm **chốt cứu đoạn cuối** có bộ đếm RIÊNG, không dính cửa sổ 10 s | ✅ Đề xuất |

---

## 4. Đề xuất B-2 — chốt cứu đoạn cuối

### Phạm vi cố ý hẹp

Chỉ chạy trong cửa sổ mà mục 3 đã **chứng minh** là bộ bù chết:

```
progStatus == STT_PROGRAM_AUTO
&& progStep == STP_DEV
&& BT >= DROP_PRO_R - END_GUARD_BAND        // mặc định 20 = 2.0 °C
&& BT <  DROP_PRO_R
&& rorBT < END_ROR_FLOOR                    // đơn vị rorBT: 1 °C/ph = 100
```

Cổng theo **khoảng cách tới nhiệt xả**, không theo `progStep == STP_DEV` đơn
thuần — vì `STP_DEV` phụ thuộc $M21 (`fcsPhase`) được cài đúng, còn khoảng cách
tới `DROP_PRO_R` thì không phụ thuộc việc bắt mốc.

### Hành vi

```
dwell: RoR dưới sàn liên tục END_ROR_DWELL giây (mặc định 15) mới hành động
       — RoR có Kalman + cửa sổ 3 s, dwell là bộ lọc xác nhận, không phải trễ thừa

bump:  gasPercent += END_GAS_BUMP mỗi END_ROR_DWELL giây (mặc định 3%)
       CỘNG DỒN qua biến riêng endRescueOffset, KHÔNG ghi đè numIncGas

trần:  endRescueOffset <= END_RESCUE_MAX (mặc định 12%)

thoát: RoR vượt lại sàn  → giữ offset, ngừng cộng (không xả offset đột ngột)
       BT >= DROP_PRO_R  → auto-drop lo phần còn lại
       progStep đổi / START tắt → endRescueOffset = 0

timeout: END_RESCUE_TMO giây (mặc định 120) mà RoR vẫn dưới sàn
         → NGỪNG cộng, kêu chuông, setMachineStatus(STT_WARN_...)
         Hết gas / tắc béc / hạt đã chín — cộng thêm chỉ làm cháy vỏ.
```

### Ba quyết định thiết kế — ĐÃ CHỐT 10/09/2026

**Q1 — Sàn RoR: ✅ SỐ TUYỆT ĐỐI**

`END_ROR_FLOOR` là hằng số, ví dụ 150 = 1.5 °C/ph.

Lý do chốt: tính năng này lái lửa ở nhiệt cao nhất mẻ, bản đầu phải **dễ đoán và
dễ soi bằng debug serial** — nhìn một số là biết ngay nó có kích hay không.
Phương án tương đối (`rorBT < rorBT_pro/2`) tự co giãn theo hồ sơ nhưng khó dò
khi sai, và phụ thuộc chất lượng file mẫu.

Hệ quả phải chấp nhận: đổi kiểu rang (DEV 4 phút nền 4.5 °C/ph ↔ DEV 1:30 nền
12 °C/ph) thì phải chỉnh lại số. Ghi rõ trong `docs/config/config-*.md` của từng
máy. Nâng lên tương đối ở bản sau, khi đã có số thật từ máy.

**Q2 — Tham số: ✅ `Config.h`, KHÔNG lên $M**

Hằng số biên dịch, mỗi máy một bản build như hiện nay (xem `docs/config/config-*.md`).

Lý do chốt: $M **đã dùng hết $M1..$M60** — `rwMemHMI()` đọc đúng 60 thanh ghi
(`Modbus_Master.h:125`), buffer ModbusMaster là 64 → chỉ còn **4 ô** ($M61–$M64),
mà chốt này ăn 3–4 ô là hết sạch. Chứng minh trên một máy trước; thấy đúng thì
mới nâng lên $M, lúc đó biết chắc cần mấy ô.

Tránh được luôn: sửa `protocol/pc_link.json` + chạy `gen_pc_link.py`, nâng
`Numaddress`, nâng `PCL_CFG_MAXIDX`, nâng `iMemHMI[61]`, và thêm ô nhập trên màn
HMI Delta.

**Q3 — Đụng độ với bộ bù BT: ✅ BỘ BÙ THẮNG, chốt cứu im**

Chốt cứu **không bao giờ** chống lại lệnh giảm gas.

```c
bool btWantsCut = (Temperature_BT > sdBT[lastTimeSD] + clRange);
if (!btWantsCut && rorBT < END_ROR_FLOOR) {
    endRescueDwell++;
}
```

Lý do chốt: BT cao hơn mẫu nghĩa là **không thiếu nhiệt**. Lê lúc đó là chuyện
khác — gió quá lớn, mẻ quá tải — và không được chữa bằng gas. Bơm lửa vào mẻ
đang nóng hơn mẫu, ở đúng nhiệt cao nhất, là công thức cháy vỏ.

### Ngân sách

RAM ~+8 byte (offset, dwell timer, timeout timer, cờ). **Rủi ro: CAO** — đây là
đường lái lửa tự động mới, chạy đúng lúc mẻ ở nhiệt cao nhất.

**Bắt buộc thử trên `tools/roaster_sim.py` / `virtual_roaster.py` trước khi
flash máy thật.** Không flash thẳng.

---

## 5. Nợ kỹ thuật phải trả trước — `RoR_Control.h` là code CHẾT, ăn 5 KB RAM

### Soát lại 10/09/2026 — nặng hơn tưởng

Ban đầu tôi ghi mục này là "lỗi đơn vị RoR". Soát tiếp thì phát hiện **cả module
`RoR_Control.h` không chạy**:

| Hàm | Được gọi ở đâu | Thực chất |
|---|---|---|
| `rorCtrl_update()` | **KHÔNG Ở ĐÂU** | code chết |
| `rorCtrl_populateSdRorBT()` | `Program.h:780` | điền `sdRorBT[]`… mà `sdRorBT[]` **chỉ được đọc bởi `rorCtrl_update()`** |
| `rorCtrl_reset()` | `Program.h:1609` | reset state chỉ dùng bởi `rorCtrl_update()` |

→ `sdRorBT[]` là `int16_t[2520]` = **5040 byte RAM phục vụ số 0**. Mỗi lần nạp
profile còn chạy thêm một vòng lặp 2520 bước để điền vào cái không ai đọc.

Điều này cũng có nghĩa lỗi đơn vị bên dưới **chưa từng gây hại trên máy thật** —
nhưng nó sẽ nổ ngay lúc ai đó gọi `rorCtrl_update()` lên.

### Lỗi đơn vị (để lại làm hồ sơ, đừng lặp lại)

`RoR_Control.h:100-101` và `plan-auto-profile-replay.md:211` cùng viết:

```c
int16_t rorOver = rorBT - sdRorBT[lastTimeSD];
if (sensitiveHeat && rorOver >= 20) { ... }
```

Hai vế **lệch thang 10 lần**:

| Biến | Tính ở | Thang |
|---|---|---|
| `rorBT` | `Program.h:111-122` — `(ΔBT/3s)*20` rồi `*10` | **0.01 °C/ph** (1 °C/ph = 100) |
| `sdRorBT[]` | `RoR_Control.h:58-59` — `Δ(10s)*6` | **0.1 °C/ph** (1 °C/ph = 10) |
| `rorBT_pro` | `Program.h:135-137` — cùng cách `rorBT` | 0.01 °C/ph |

Trừ thẳng là ra rác. Và `rorOver >= 20` với thang `rorBT` là **0.2 °C/ph**, không
phải 2.0 như plan viết.

### ✅ ĐÃ CHỐT 10/09/2026 — BỎ HẲN `sdRorBT[]`, dùng `rorBT_pro`

`rorBT_pro` (`Program.h:135-137`) tính **cùng công thức, cùng cửa sổ 3 s, cùng
thang** với `rorBT` — không cần mảng nào cả.

Việc phải làm:

1. Xoá khai báo `sdRorBT[]` (`Define.h:1065`).
2. Xoá `rorCtrl_populateSdRorBT()` (`RoR_Control.h:50-61`) và lời gọi
   (`Program.h:780`).
3. Xoá chỗ ghi `sdRorBT[sdTempTi]` ở cả hai parser (`Program.h:565`,
   `Program.h:677`) — **giữ nguyên việc parse cột trong file** để không phá tương
   thích CSV, chỉ bỏ chỗ chứa.
4. `rorCtrl_update()` + `rorCtrl_reset()` + 4 biến static: **xoá luôn hay giữ?**
   Xem quyết định bên dưới.
5. Sửa `plan-auto-profile-replay.md:211` và mục "RoR Guard" của nó sang
   `rorBT_pro` cho khỏi lan lỗi sang phần khác.

**Thu hồi 5040 byte** → RAM tĩnh từ 84.5 % xuống **~74.3 %**. Đây là khoản lợi
lớn nhất của cả kế hoạch, và nó **không có rủi ro hành vi** vì không có gì đang
đọc mảng đó.

### ⚠ Còn một câu chưa chốt — số phận `rorCtrl_update()`

Hàm này là một bộ điều khiển RoR hoàn chỉnh (correction theo RoR + BT + early
warning từ `rorET`, dead time, tích lũy offset, kẹp theo pha) — **viết xong nhưng
chưa bao giờ được đấu vào**.

| | Cách | Đánh giá |
|---|---|---|
| a | Xoá sạch `RoR_Control.h` | Sạch nhất. Nhưng vứt một bộ điều khiển đã viết xong, sau muốn làm sàn RoR toàn pha DEV thì viết lại từ đầu. |
| b | Giữ file, chỉ xoá `sdRorBT[]` và sửa `rorTarget` sang `rorBT_pro` | Giữ được công sức cũ, tốn ~0 RAM (4 biến static). Nhưng để code chết trong repo dễ làm người sau tưởng nó đang chạy. |
| c | Giữ, bọc trong `#if 0` + ghi chú rõ "CHƯA ĐẤU" | Trung dung. |

Đề xuất **(b)** kèm một dòng comment đầu file ghi rõ *"module này CHƯA được gọi
ở đâu — xem kế hoạch 2026-09-10"*, vì mục 9 đã ghi sàn RoR toàn pha DEV là việc
sẽ làm sau, và đây chính là bộ khung cho nó.

Việc này phải xong **trước đợt 3**, vì chốt cứu đọc `rorBT`.

---

## 6. Nguyên nhân C (phụ) — `sdTempTi` ngoài dải

`Program.h:520-521`:

```c
sdTempTi = (uint16_t)(mm*60 + ss);
if(sdTempTi >= PROFILE_MAX_SECONDS) continue;   // continue SAU khi đã gán
```

Dòng vượt dải bị bỏ qua nhưng `sdTempTi` **giữ lại giá trị rác**. Nếu đó là dòng
cuối, `sdTempTi` > 2520 → `lastTimeSD` có thể vượt biên → `sdBT[lastTimeSD]`
**đọc ra ngoài mảng**.

Cần mẻ chạy quá 42 phút mới chạm tới, nhưng đuôi làm nguội làm nó gần hơn nhiều.
Vá mục 2 đã che phần lớn (kẹp theo `rtDROP`), vẫn nên vá gốc:

```c
uint16_t tiTmp = (uint16_t)(mm*60 + ss);
if(tiTmp >= PROFILE_MAX_SECONDS) continue;
sdTempTi = tiTmp;
```

Parser TXT (`Program.h:662-663`) đã kiểm trước khi gán — **không dính**.

RAM/Flash: 0. **Rủi ro: THẤP.**

---

## 7. Thứ tự triển khai

### Đợt 1 — phòng thủ (không thêm đường lái lửa)

- [ ] Mục 6: sửa thứ tự gán `sdTempTi`
- [ ] Mục 2: thêm `sdProfileEndTi`, kẹp `lastTimeSD`, sửa bound `rorCtrl_populateSdRorBT()`
- [ ] Build, `/memory-check`
- [ ] Kiểm bằng file mẫu **có đuôi làm nguội** cố ý → xác nhận `lastTimeSD` khựng đúng giây xả
- [ ] Kiểm hồi quy bằng file **máy tự ghi** → hành vi không đổi
- [ ] Cắt đuôi các file `.csv` Artisan đang nằm trên thẻ

Đợt này **có thể flash sớm** — nó chỉ *chặn* hành vi sai, không sinh hành vi mới.

### Đợt 2 — dọn `RoR_Control.h`, thu hồi 5 KB RAM

- [ ] Xoá `sdRorBT[]` + `rorCtrl_populateSdRorBT()` + 2 chỗ ghi trong parser
- [ ] Chốt số phận `rorCtrl_update()` (a/b/c ở mục 5) — đề xuất (b)
- [ ] Sửa `plan-auto-profile-replay.md:211` cho khỏi lan lỗi sang phần khác
- [ ] Build, xác nhận RAM tĩnh xuống ~74 %
- [ ] Chạy một mẻ AUTO trên sim → hành vi **không đổi** (mảng vốn không ai đọc)

Phải xong **trước** đợt 3, vì chốt cứu đọc `rorBT`.

### Đợt 3 — chốt cứu đoạn cuối (B-2)

- [x] ~~Chốt Q1/Q2/Q3 mục 4~~ — xong 10/09/2026
- [ ] Code theo 3 chốt: sàn tuyệt đối · `Config.h` · bộ bù BT thắng
- [ ] Chạy trên `roaster_sim.py`: dựng đúng ca 216 °C / RoR 2 / xả 217
- [ ] Chạy ca ngược: RoR bình thường → xác nhận chốt **không** kích
- [ ] Chạy ca hết gas → xác nhận timeout kêu và ngừng cộng
- [ ] Chỉ flash máy thật sau khi 3 ca sim đều đúng

---

## 8. Ngân sách tài nguyên

Đo trên bản build hiện tại (`.pio/build/genericSTM32F103RC/firmware.elf`,
10/09/2026 11:02):

Số **đo thật** bằng `pio run` ngày 10/09/2026 (số 41 544 ghi ở bản kế hoạch đầu
lấy từ file `.elf` cũ trên đĩa — sai, đã bỏ):

| | RAM tĩnh | % của 49 152 |
|---|---|---|
| Trước đợt 1 | 40 006 | 81.4 % |
| **Sau đợt 1 — ĐÃ BUILD OK** | **40 008** | **81.4 %** |
| Sau đợt 2 (−`sdRorBT[]`) | ~34 968 | **~71.1 %** |
| Sau đợt 3 (+chốt cứu) | ~34 976 | ~71.2 % |

Ngưỡng nguy hiểm là **88 %** (43 254 byte). Hiện còn **3 246 byte** đệm; sau đợt 2
còn **~8 286 byte**.

Flash sau đợt 1: 102 064 / 262 144 = **38.9 %**, không phải lo.

Ô $M còn trống: **4** ($M61–$M64), và chốt Q2 giữ nguyên 4 ô đó.

> ⚠ `CLAUDE.md` ghi RAM 20 KB — **sai**. Board `genericSTM32F103RC` là 48 KB
> (`maximum_ram_size = 49152` trong board json). Con số 20 KB đang được dùng để
> đánh giá mọi tính năng mới nên phải sửa. Việc riêng, không thuộc đợt nào.

---

## 9. Việc KHÔNG làm trong kế hoạch này

- **Không** đổi cửa sổ xác nhận 10 s của bộ bù gas (đã chốt theo kinh nghiệm).
- **Không** đổi cấu trúc cộng-mỗi-giây của `calibProgram()` (cố ý, đã xác nhận).
- **Không** thêm sàn RoR cho **toàn** pha DEV — phạm vi rộng, rủi ro cao, để sau
  khi chốt cứu đoạn cuối chạy ổn trên máy thật.
- **Không** tự xả mẻ khi timeout. Tự xả một mẻ chưa tới nhiệt là hỏng mẻ — chỉ
  kêu chuông + báo mã, để thợ quyết. Cùng nguyên tắc với trần pha phát triển
  (`Program.h:1869-1874`).
