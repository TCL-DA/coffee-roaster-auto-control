# GĐ R — Rang lõi khớp firmware (app ↔ skill rang)

> Track riêng, **KHÔNG** thuộc UX (GĐ5–8) hay kinh doanh (GĐ4). Đây là phần chiều
> sâu rang-lõi bị hoãn của GĐ1/GĐ3 (§8.3 thư viện mục tiêu, §8.4 phase editor,
> §9.2 capability matrix). **Làm TRƯỚC GĐ5** — vì đường mục tiêu thật là NỀN bắt
> buộc cho giọng nói/đếm ngược mốc của GĐ5–6.
>
> Nguồn đối chiếu: skill `.claude/skills/rang-ca-phe/` (bảng `$M`, luồng 11 bước,
> hàm Program.h). Tạo: 2026-07-25.

---

## Trạng thái (cập nhật 2026-07-25 — phiên "làm cho xong")

| Bước | Trạng thái | Ghi chú |
|------|-----------|---------|
| **B** Đường mục tiêu thật | ✅ XONG (app) | `buildTarget()` suy đường BT + 5 mốc từ setpoint hồ sơ; thay `curveAt/MILES/ROAST_SECS` cứng; `MILES`/`ROAST_SECS`/`TGT` giờ theo hồ sơ. Chọn hồ sơ khác → nền mờ + mốc + số khác nhau. **Chưa test trên exe/máy thật.** |
| **A** Hồ sơ dày | ✅ XONG (app) | Thêm trường tuỳ chọn `deT/fcsT/devTarget/preGas/kg/bean` vào form + `refreshPE` + helper `peOpt/peOptIn`; trống = app tự ước. Trường mới tự chảy vào `profiles.json` qua `prof_save` (chưa đổi CSV — xem A'). |
| **D** Audit $M | ✅ XONG | Sửa 4 nhãn lệch so với `registers-M.md` + code thật: `loop`=số mẻ (không phải ms/Sample), `autoOff`=0/1 (không phải °C), `preCool`=°C ×10 (không phải 0/1), `autoLoader`=bỏ "/đốt". |
| **F** Màn chờ | ✅ XONG (app) | Bảng thông số mẻ `#riPlan` (~ = ước), nút "✎ Sửa thông số mẻ" + clone-khi-đã-rang (`editCurrentProfile`), reload sau lưu. |
| **G** Model máy (app) | ✅ XONG (app) | `MACHINE_MODELS` 3/6/12/30kg → `applyModel()` điền timer + kg mặc định vào form Cài đặt máy; `currentModelKg()` cấp kg auto cho hồ sơ trống. **Áp THẬT xuống máy = phần E.** |
| **A'** Kho CSV | ✅ CODE XONG | `prof_load/prof_save` (Python) đọc/ghi `ho-so.csv` (16 cột) + di trú `profiles.json`→`.bak` một lần. Round-trip test PASS. Bỏ `profiles.csv` trùng phía JS. **CẦN test với exe** (kiểm di trú thật + web sync). |
| **E** Handshake $M | ✅ CODE XONG | Khối `config` (reg 170-173) trong `pc_link.json` → gen 3 phía khớp (`--check` OK). `PC_Link.h::pcLinkConfigTask()` đọc/ghi `iMemHMI[idx]` (idx=$M 1..52, `iMemHMI[60]` an toàn), chặn ghi khi rang. Python `mc_read/mc_write` + `otl_link.cfg_op()` handshake. JS đọc auto khi mở tab + ghi auto từng ô có guard. **CẦN flash STM32 + test** (không có pio ở đây). |
| **C** App lái | ✅ CODE XONG | Bộ `AUTOPILOT` (nút "🤖 App LÁI" cạnh Chế độ): mỗi ~10s so BT thật với `TGT.btAt` → nhích gas (bậc 2%, deadband 3°C, kẹp maxGas), AB theo nhiệt; chỉ chạy khi nối máy + PC control + CÓ LỬA; mất PC control/xong mẻ → tự nhả. Choreography xi-lanh vẫn firmware backstop. **CẦN test bench máy thật** (tune gas). |

> Đã sửa `OTL Roast Lab.html` + `tools/{roast_lab_hmi,otl_link,pc_link_map}.py` + `protocol/{pc_link.json,gen_pc_link.py}` + `include/{PC_Link.h,PC_Link_Map.h}`. Kiểm: JS parse sạch, py_compile OK, gen --check khớp, CSV round-trip PASS. **Review code**: sửa 2 lỗi — (B) ép DE<FCs<xả cho đường mục tiêu đơn điệu; (C) không nâng gas khi chưa có lửa. **Review design**: giảm gap màn chờ IDLE + cho cuộn để bảng thông số không kẹp. **Chưa build exe/flash firmware, chưa commit.**

---

## La bàn

Firmware lái mẻ bằng **setpoint nhiệt** (`chargeTemp → yellowPhase(DE) → fcsPhase(FCs)
→ DROP_PRO`) + **kế hoạch gas** (`preGas`, bậc `TpCalib/DeCalib/FcsCalib`, bảng FF
`sdGas[]`). App hiện **chưa mang được** các setpoint đó trong hồ sơ, nên:
- Hồ sơ app không mô tả nổi mẻ nó định rang (chỉ có charge/drop/tổng-giờ).
- Đường "mục tiêu" trên màn là **curve DEMO cứng**, không theo hồ sơ đang chọn.
- Không tự soạn/ghi được profile AUTO xuống máy.

Mục tiêu track: **hồ sơ app = công thức thật lái được mẻ**, và mọi thứ "mục tiêu"
(nền mờ, đếm ngược, giọng nói) bám hồ sơ đó chứ không bám hằng số.

---

## ⛔ Ràng buộc CỨNG — KHÔNG dùng thẻ SD của máy trên app (lệnh chủ máy 2026-07-25)

**App OTL Roast Lab TUYỆT ĐỐI không đọc / ghi / chọn thẻ SD của máy rang.**
- **Bỏ/ẩn** tính năng "▶ RANG AUTO từ thẻ SD máy" (chọn slot 1-30) — cả nhánh phụ
  thuộc SD (`prof_pct/prof_ok/prof_sel`, `link_write('profile'…)`) ở luồng rang.
- **Không** soạn/ghi profile xuống thẻ SD. Hồ sơ sống trong app dưới dạng **file CSV**
  (định dạng chuẩn, đọc được bằng mắt/Excel/Artisan), KHÔNG đẩy lên thẻ, KHÔNG khoá
  trong blob json riêng. CSV = nguồn sự thật của hồ sơ.
- Rang AUTO (nếu làm) phải do **APP LÁI TRỰC TIẾP** — stream setpoint qua khối GHI
  PC_Link, KHÔNG qua file SD. Xem Bước C (đã đổi hướng).
- Ảnh hưởng: **Bước C đổi hẳn hướng**; khoảng trống #3 trong bảng dưới không còn là
  việc phải làm (SD-Auto bị loại), giữ lại chỉ để ghi nhận đã gỡ.

---

## Khoảng trống đã xác nhận (bằng chứng trong code)

| # | Vấn đề | Chỗ trong code |
|---|--------|----------------|
| 1 | Hồ sơ chỉ `chargeT / temp(drop) / time / roast / notes` — thiếu DE°C, FCs°C, DEV%, kế hoạch gas | `OTL Roast Lab.html` `newProfile()` (~2923) |
| 2 | Đường mục tiêu + mốc là **hằng số demo** (`ROAST_SECS=642`, `MILES` cứng, `curveAt()` bịa) | `curveAt()` (~3788), `MILES` (~3780) |
| 3 | ~~SD-Auto chỉ chọn slot có sẵn~~ → **ĐÃ LOẠI** theo ràng buộc không-SD (gỡ nút RANG AUTO từ SD) | luồng SD-Auto qua PC_Link (xem `project_sd_auto_pclink`) |
| 4 | Trang "Cài đặt máy" 52 `$M` cần soi lại nhãn/đơn vị + **chưa đồng bộ 2 chiều với máy** (2 nút mc_read/mc_write còn là stub) | machine-config (`project_machine_config`); `roast_lab_hmi.py:442-448` |

Mốc **thật** lúc rang đã đúng — bắt từ `progStep` qua DataSource (`~3454-3459`),
lưu SQLite. Track này KHÔNG đụng phần đó.

---

## Bước B — Đường mục tiêu THẬT (ưu tiên 1, nền cho GĐ5–6)

**Việc:** thay `curveAt()/MILES/ROAST_SECS` cứng bằng hàm suy từ setpoint hồ sơ đang
chọn. Tối thiểu cần: `chargeT` (đầu), `DE°C`, `FCs°C`, `dropT`, `time` (tổng) → nội
suy đường BT mục tiêu + đặt mốc TP/DE/FCs/DEV/DROP theo giây dự kiến.

**Chi tiết:**
- Mốc thời gian dự kiến suy từ nhiệt: dùng RoR mẫu theo mức rang (nhạt/vừa/đậm) để
  ước giây đạt DE/FCs, hoặc cho người dùng nhập thẳng "phút DE / phút FCs" nếu biết.
- Hồ sơ **chưa đủ setpoint** (thẻ mỏng cũ) → fallback về ước lượng từ `chargeT/dropT/
  time` (tốt hơn hằng số demo), KHÔNG vẽ đường bịa khi thiếu dữ liệu (giữ nguyên tắc
  `R.bgCurve` chỉ vẽ khi có curve thật, ~4058).
- Đầu ra dùng chung cho: nền mờ chart, chip milestrip, **đếm ngược mốc kế** (GĐ6),
  **giọng nói** (GĐ5).

**Xong khi:** chọn 2 hồ sơ khác nhau → nền mờ + mốc + đếm ngược **khác nhau đúng
theo setpoint**, không còn 01:34/06:12/09:40 cố định.

**Rủi ro:** đừng để đường mục tiêu trông như "curve thật đã rang" — phải rõ đây là
*dự kiến*. Giữ style nét đứt/mờ.

---

## Bước A — Hồ sơ dày thêm (đi kèm B)

**Việc:** thêm trường **tuỳ chọn** vào object hồ sơ + form `refreshPE()`:
- `deT` (DE °C, ~`yellowPhase`), `fcsT` (FCs °C, ~`fcsPhase`)
- `devTarget` (% phát triển mục tiêu)
- Kế hoạch gas gọn: `preGas` (%), có thể thêm bậc/pha sau
- `kg` (mẻ nạp, **trống → auto theo model máy** — xem Bước G), `bean` (loại cà, **để
  trống được**, thợ chọn sau trong trang Hồ sơ)
- **Gas/gió/trống ghi vào CSV lúc rang:** thợ chỉnh `outEdit` khi rang → lưu lại đường
  gas/gió/trống thực vào hồ sơ CSV (mẻ sau lặp được). Hiện chỉnh được nhưng KHÔNG lưu.

**Nguyên tắc:**
- **CSV LÀ ĐỊNH DẠNG LƯU CHÍNH** (chốt chủ máy 2026-07-25): **bỏ `profiles.json`**, app
  đọc/ghi thẳng **thư mục CSV**. Hồ sơ = file CSV đọc được bằng mắt/Excel/Artisan.
  Trường mới thành cột CSV (header rõ tên: `deT,fcsT,devTarget,preGas`), cột trống =
  thẻ mỏng cũ.
- **Di trú một lần (không mất hồ sơ):** lần chạy đầu thấy `profiles.json` mà chưa có
  kho CSV → tự chuyển toàn bộ sang CSV rồi thôi đọc json (giữ `profiles.json.bak` phòng hờ).
- **Nơi sửa (Python):** thay `prof_load`/`prof_save` (`roast_lab_hmi.py:775/873`, đang
  đọc/ghi `profiles.json`) sang đọc/ghi CSV; **tận dụng `prof_write_files`
  (`:787`)** đã biết ghi file text/CSV vào thư mục. Web đọc chung (`:950`) phải đổi theo.
- **Granularity (đề xuất):** 1 file `ho-so.csv` cho DANH SÁCH hồ sơ (mỗi dòng 1 hồ sơ,
  metadata charge/DE/FCs/drop/gas…); curve mẻ đã rang giữ ở kho mẻ (SQLite) như cũ,
  không nhồi vào CSV hồ sơ. → chốt lại lúc code.
- Mặc định vẫn là **thẻ mỏng** — cột mới để trống thì hồ sơ hành xử y như cũ.
- Cập nhật `profCsvIndex()` + `profAlog()` + PDF để mang trường mới (alog map
  `deT→timeindex[1]`, `fcsT→timeindex[2]` khi đã quy ra giây ở bước B).
- Đơn vị: °C nguyên (khớp `$M`); firmware ×10 khi so sánh (skill registers-M.md).

**Xong khi:** app đọc/ghi hồ sơ thẳng CSV (không còn `profiles.json`); hồ sơ cũ đã di
trú đủ; cột mới có/không đều không vỡ.

---

## Bước D — Audit trang "Cài đặt máy" ($M) theo skill (rẻ, làm sớm)

**Việc:** soi nhãn/đơn vị 52 tham số `$M` trên trang cài đặt máy so với
`references/registers-M.md`. Sửa các chú thích lệch:
- `loop` = **số mẻ rang lặp** (không phải "Sample").
- `FcsCalib` = **$M31** (comment cũ ghi nhầm $M5).
- `autoLoader` = **cờ auto-loader nạp** (không phải "auto burner").
- Timer cơ cấu = **giây**; nhiều setpoint nhiệt firmware **×10** khi so sánh.

**Xong khi:** nhãn trên UI khớp bảng skill; không còn 3 chú thích sai.

---

## Bước E — Đồng bộ trang "Cài đặt máy" với máy thật (firmware, phải flash)

**Việc:** nối 2 nút "Đọc từ máy" / "Ghi xuống máy" (UI đã có) qua **cửa sổ handshake
~5 register** — KHÔNG stream 52 register mỗi vòng (tránh lag + tiết kiệm RAM).

**Cửa sổ handshake (thêm khối `config` vào `pc_link.json` → gen):**

| Ô | Nghĩa |
|---|---|
| `cfg_cmd`    | 0=rảnh · 1=đọc 1 tham số · 2=ghi 1 tham số |
| `cfg_idx`    | chỉ số tham số 0…51 |
| `cfg_val`    | giá trị (app ghi khi lệnh ghi / firmware điền khi lệnh đọc) |
| `cfg_status` | 0=đang xử · 1=OK · 2=lỗi/khoá |

**Hành vi UI (đã chốt 2026-07-25):**
- **Đọc = TỰ ĐỘNG** khi mở tab Cài đặt máy (một loạt 52 vòng hỏi-đáp ≈ 1-2s, chỉ chạy
  lúc mở tab, không per-loop). Giữ nút "Làm mới" để đọc lại thủ công.
- **Ghi = auto TỪNG Ô + guard:** sửa ô nào → viền vàng → debounce ~1s → tự ghi RIÊNG ô
  đó (1 vòng handshake) → toast "đã ghi $Mxx". **Chặn khi `_machRun`** (đang rang) →
  báo "đang rang, không ghi", giữ vàng để ghi sau. Giữ nút "Ghi tất cả" dự phòng.

**Firmware (PC_Link.h):** khi `cfg_cmd==0` → `return` ngay (per-loop ≈ 0). Lệnh đọc:
chép `*_R[idx]` vào `cfg_val`. Lệnh ghi: kẹp + set `*_R/_R_CP` + `nodeHMI.writeSingleRegister(addr+2000, v)`
— y hệt pattern setpoint gas/gió đang chạy thật.

**Phụ thuộc:** bảng ánh xạ `idx → (biến *_R, địa chỉ HMI +2000, scale)` do **Bước D** dựng.
Ghi sai địa chỉ = ghi nhầm tham số vận hành → phải audit trước.

**Xong khi:** mở tab hiện đúng số máy; sửa 1 ô lúc máy rảnh → máy đổi thật; đang rang → chặn.

---

## Bước C — RANG AUTO do APP LÁI (KHÔNG qua SD) — đã đổi hướng 2026-07-25

**Đổi hướng:** theo ràng buộc **không dùng SD**, BỎ ý "soạn profile ghi xuống thẻ SD".
Thay bằng: app **tự lái mẻ AUTO** — stream setpoint theo đường mục tiêu (Bước B) xuống
máy qua **khối GHI PC_Link** (gas/gió/SV + nút charge/drop/ignite), đúng kiến trúc
**APP LÁI MÁY** (`project_app_lai_may`): app tự mồi lửa → tự nạp theo nhiệt → tự chỉnh
gas bám curve → tự xả; firmware = tay chân + watchdog 3s (nhả về HMI nếu mất app) +
chốt đóng gas khi mồi hụt 75s.

**✅ QUYẾT ĐỊNH KIẾN TRÚC (chủ máy chốt 2026-07-25): (A) — APP LÁI TOÀN BỘ.**
App giữ **trọn state machine rang** (đúng vai `Program.h` trước đây) và tự ra lệnh từng
cơ cấu theo thứ tự/nhiệt/timer. Firmware = **tay chân thuần**: nhận lệnh mức, đóng xi
lanh theo timer phần cứng (relay), giữ 2 chốt an toàn (watchdog mất-app + mồi-hụt).
Bộ tuần tự AUTO cũ trong `Program.h` (chạy từ SD) **không dùng nữa** ở chế độ app-lái.

**Hệ quả:** mọi dòng 🔧 trong bảng đối chiếu (preCool trước drop, destonerPre trước
escape, AB theo nhiệt, auto-loader ở TP) **chuyển thành việc của app**, không còn nhờ
firmware. App phải **biết toàn bộ timer** → **C phụ thuộc E + G** (đọc `$M`/model để lấy
`chargeDuration/dropDuration/escapeDuration/preCool/destonerPre/destonerSet/afterburner*`).

**Việc — state machine rang trong app (theo hướng A):**
1. **Chờ nạp:** vòng bật/tắt đầu đốt giữ BT bám nhiệt charge (thấp→bật, cao→tắt) — hiện
   app chỉ mồi 1 lần, cần vòng giữ.
2. **Charge:** app fire charge đúng nhiệt; xi lanh đóng theo `chargeDuration_R` (relay
   firmware là backstop, app vẫn tự đếm để biết mốc).
3. **Rang:** mỗi giây so BT với đường mục tiêu (Bước B) → tính gas → ghi `gas/air/sv`
   qua PC_Link. Chấm TP/DE/FCs/DEV. **Auto-loader:** app tự bật loader ở TP nếu option bật.
   **AB:** app bật/tắt afterburner theo `afterburnerSet_R` (nhiệt).
4. **Drop:**
   - *theo nhiệt mục tiêu:* app chạy **preCool trước** (bật mixer+cooling), chờ tới
     `DROP_PRO − preCool` rồi mới fire drop.
   - *thợ bấm tay:* **drop + mixcool CÙNG LÚC** (`cmdDrop` hiện chỉ gửi 'drop' → bổ sung).
   - drop đóng theo `dropDuration_R`.
5. **Sau drop:** AB tiếp theo `afterburnerNext_R` (0 = tắt ngay). mixcool gần xong → app
   fire **destoner trước escape** một khoảng `destonerPre_R`; escape đóng theo
   `escapeDuration_R`; destoner đóng theo `destonerSet_R`.
- KHÔNG đụng thẻ SD, KHÔNG `link_write('profile'…)`.

**⚠️ An toàn (bắt buộc vì app giữ cả chuỗi):** app treo giữa chuỗi drop/escape là nguy
hiểm → `failsafe` firmware (`pc_link.json`: watchdog 3s nhả về HMI, mồi-hụt 75s đóng gas)
phải BẬT đúng. App nên viết state machine idempotent (mất nhịp 1-2s không kẹt cơ cấu).

**Phụ thuộc:** **B** (đường mục tiêu = bản nhạc) + **E** (đọc timer `$M` thật) + **G**
(model → timer mặc định) đều phải xong trước C.

**Xong khi:** tạo hồ sơ trong app → BẬT chế độ APP-AUTO → máy chạy trọn mẻ theo app,
mất app thì firmware nhả về HMI an toàn — KHÔNG file SD nào tham gia.

---

## Bước F — Màn "chờ bắt đầu": sửa thông số tại chỗ + đổi hồ sơ + clone-khi-có-CSV

**Bối cảnh:** màn IDLE hiện chỉ có nút "BẮT ĐẦU" ([OTL Roast Lab.html:1587-1593]). Đề xuất
chủ máy: trước khi bấm rang, hiện **bảng thông số mẻ** (charge/drop/DE/FCs/gas/kg/loại
cà…) **sửa được ngay tại đó** + **đổi sang hồ sơ khác** + logic clone.

**Việc:**
- Overlay IDLE thêm bảng thông số của hồ sơ đang chọn — sửa tại chỗ, đổi hồ sơ tại chỗ.
- **Clone-khi-có-CSV:** hồ sơ CHƯA có file CSV (chưa rang mẻ nào) → sửa thẳng. Hồ sơ ĐÃ
  có CSV (đã rang) → cho sửa nhưng **tự tạo hồ sơ MỚI giữ kết cấu CSV cũ**, chỉ đổi phần
  thợ chỉnh (không đè bản gốc đã rang).
- Hai bước hiện đang rời (Bắt đầu rang ở Tổng quan → tab Rang → BẮT ĐẦU) — gộp mạch cho
  liền tay (Play → tự sang giao diện rang).

**Xong khi:** ở màn chờ sửa được thông số + đổi hồ sơ; sửa hồ sơ đã-rang không đè bản gốc.

---

## Bước G — Khái niệm "Model máy" + bảng timer mặc định tự áp

**Bối cảnh:** đề xuất chủ máy: **timer cơ cấu phải tự đổi theo model máy** (máy 5kg escape
~55s, 12kg ~65s…). Hiện các timer là `$M` cố định (`chargeDuration_R`/`escapeDuration_R`/
`destonerSet_R`…), KHÔNG có khái niệm model, không auto theo kg.

**Việc:**
- Thêm **"Model máy"** (5/6/12/30kg…) — gắn trang Cài đặt máy (Bước E) hoặc cấu hình riêng.
- Bảng **timer mặc định theo model** → chọn model là app gợi ý/áp bộ timer chuẩn
  (escape/destoner/charge/drop) xuống `$M` qua Bước E. Thợ vẫn override được.
- Trường `kg` hồ sơ (Bước A) **trống → lấy kg mặc định của model** (máy 5kg → 5kg).

**Xong khi:** đổi model → bộ timer + kg mặc định đổi theo; hồ sơ để trống kg vẫn ra đúng.

---

## Đối chiếu quy trình rang: đề xuất chủ máy vs app hiện tại (2026-07-25)

Kiểm code thật (HTML + `Define.h`/`Program.h`). Ký hiệu: ✅ khớp · ⚠️ một phần · ❌ chưa
có · 🔧 firmware (đã có nhưng chỉ chạy AUTO/SD, chưa dùng khi app lái).

| Đề xuất | App hiện tại | |
|---|---|---|
| Đăng nhập · chọn hồ sơ | có | ✅ |
| Nhập kg, trống→auto theo model | không có trường kg/model (chỉ `scale_tg` nhập tay) | ❌ →G,A |
| Mức rang, default medium | thuộc tính hồ sơ; default = mục đầu list, không "medium" | ⚠️ |
| Chọn loại cà (trống được, chọn sau) | không có trường | ❌ →A |
| Nhập nhiệt charge/drop | `chargeT`/`temp` trong form hồ sơ | ✅ |
| Play → tự sang giao diện rang | 2 bước rời | ⚠️ →F |
| Loader (cân→kg / không cân→timer) | có nút+auto-loader+`scale_tg`; app chưa dẫn bước | ⚠️ |
| Màn chờ: sửa thông số + đổi hồ sơ + clone-CSV | chỉ nút BẮT ĐẦU | ❌ →F |
| Tự bật/tắt đầu đốt giữ BT ở charge; charge auto-close | app mồi 1 lần (không vòng giữ); auto-close = firmware | ⚠️ →C |
| Charge xong chỉnh gas/gió/trống → LƯU CSV | chỉnh được, không lưu | ❌ →A |
| DE, FCs | chấm mốc được; ngưỡng chưa thành trường hồ sơ | ⚠️ →A |
| Drop theo nhiệt HOẶC bấm tay | có cả 2 | ✅ |
| Drop-nhiệt → mixcool trước (`preCool_R`) | firmware có (`Program.h:1779`), chỉ AUTO | 🔧 →C |
| Drop-tay → drop+mixcool cùng lúc | `cmdDrop` chỉ gửi 'drop' | ❌ →C |
| Drop auto-close `dropDuration_R` | firmware | ✅ |
| AB theo `afterburnerSet_R`/`Next_R` | firmware behavior; app có nút tay | 🔧 |
| destonerPre/escape/destoner timers | firmware có (`:2191/2352`), là `$M` cố định | 🔧/❌ →G |
| Timer tự đổi theo model | KHÔNG có | ❌ →G |
| Auto-loader tự bật ở TP | firmware có (`:1682/1751`); app toggle cờ | 🔧 |

**Kết luận:** đề xuất là SPEC ĐÍCH tốt; app nay làm ~½. Phần thiếu chia 3 nhóm →
**A/A'** (trường hồ sơ + lưu CSV), **F** (màn chờ), **G** (model+timer), và **C** (chuỗi
cơ cấu — chờ chốt hướng (A) hay (B)).

---

## Thứ tự & phụ thuộc

```
Thuần app:      B (đường mục tiêu) ─→ A (hồ sơ dày + CSV kho chính) ─→ F (màn chờ, clone-CSV)
                      └── nuôi GĐ5 (giọng) + GĐ6 (đếm ngược) + "bản nhạc" cho C

Cần firmware:   D (audit → bảng ánh xạ $M) ─→ E (đồng bộ Cài đặt máy, handshake)
                                                   └─→ G (model máy + timer mặc định)
                C (RANG app LÁI TOÀN BỘ, KHÔNG SD) ── sau B + E + G + chốt an toàn
```

1. **B trước** — mở đường cho GĐ5–6, không phụ thuộc firmware.
2. **A** ngay sau B (hồ sơ CSV mang đúng setpoint + kg/loại cà/lưu gas lúc rang).
3. **F** sau A (màn chờ sửa thông số + đổi hồ sơ + clone-khi-có-CSV).
4. **D** chen vào bất cứ lúc nào (độc lập, rẻ) — ra bảng ánh xạ cho E.
5. **E** sau D (đồng bộ Cài đặt máy — đọc auto khi mở tab, ghi auto từng ô + guard).
6. **G** sau E (model máy + bảng timer mặc định áp xuống `$M` qua E).
7. **C** cuối — **app LÁI TOÀN BỘ (hướng A đã chốt)**, KHÔNG SD; cần **B + E + G** xong
   (app phải biết mọi timer `$M`) + chốt an toàn firmware.

---

## Liên quan
- Skill: `.claude/skills/rang-ca-phe/` (registers-M, roast-flow, program-functions,
  profile-format).
- `docs/plan/plan-hmi-roadmap.md` (GĐ1–4), `docs/plan/plan-nangcap-gd5-gd8.md` (UX).
- Memory: `[[project_skill_rang_ca_phe]]`, `[[project_sd_auto_pclink]]`,
  `[[project_machine_config]]`, `[[project_gas_calib_auto]]`, `[[project_app_lai_may]]`.
