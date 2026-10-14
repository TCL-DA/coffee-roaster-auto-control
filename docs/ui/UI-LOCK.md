# Khoá sửa giao diện — `OTL Roast Lab.html` và `tools/test_ui_*`

Đọc file này TRƯỚC khi sửa. Quy tắc đầy đủ ở `AGENTS.md`, mục
"Bản thiết kế Claude Design và cách Claude + Codex làm chung trên app".

## Trạng thái

**RẢNH — CLAUDE ĐÃ NHẢ — 13/10/2026** (gói R0 "một bản cho mọi máy"): nút thiết bị màn Rang + thẻ áp hút ẩn / hiện theo cấu
hình máy `$M62` firmware (snapshot `mc_opt`, `setMcOpt`), ô tích "Thiết bị máy có" khoá khi máy đã cấu hình (trừ Làm nguội).
Sửa JS `applyDevVisibility` / `vacOn` / `dsApply` / ô tích `#devEnRow` + CSS `.permchk.locked` + `tools/roast_lab_hmi.py`
`_mc_opt` (đọc $M62 ở luồng nền 60 s / lần). Kiểm: `test_ui_mc_opt` 8/8 (mới), `test_ui_live`, `test_ui_compat_roast`,
`test_ui_caidat_tuluu`, `test_ui_overview_history` ĐẠT. CHƯA build EXE, CHƯA commit.

**RẢNH — CLAUDE ĐÃ NHẢ — 11/10/2026**. Chỉ gỡ vạch màu mép trái `.nsfav` (6 px accent) và `.profcard` (7 px gas / 4 px)
— chủ máy cấm tuyệt đối vạch / dải màu ở mép nút hay thẻ. Sao lưu: `docs/ui/backup/OTL Roast Lab.pre-bo-vach-mep-20261011.html`.
Kiểm: `test_ui_overview_history`, `test_ui_workflow` ĐẠT. ĐÃ BUILD EXE (md5 HTML nhúng `2078f9f1…` khớp đĩa; bản trước:
`tools/dist/_cu/OTL Roast Lab HMI.before-ao-v7-20261011.exe`). CHƯA commit.

**RẢNH — Codex đã nhả — 29/09/2026**. Đợt tối ưu canvas live và lưu phong cách tài khoản hoàn tất; bộ kiểm và EXE end-to-end đã đạt. HTML sao lưu: `docs/ui/backup/OTL Roast Lab.pre-performance2-20260929-090308.html`. EXE cũ sao lưu: `tools/dist/OTL Roast Lab HMI.before-performance2-20260929.exe`.

**TRỐNG — CLAUDE ĐÃ NHẢ** (19/09/2026). Đợt 16, chủ máy: "sửa tiếp đi… build trên cả app PC lẫn iOS".
**KHÔNG đụng `OTL Roast Lab.html`** (md5 vẫn `19eadc94…`). Đã làm:
1. **Tìm ra gốc lỗi ĐỎ NGẪU NHIÊN đeo bám từ 11/09** ở `test_ui_hold_confirm` (#btnEscape/#btnDrop, "giữ đủ mốc mà
   lệnh không đi") — là **lỗi bộ kiểm, không phải lỗi app**: `dsStart()` chạy `setInterval(dsTick,1000)` giữ tham
   chiếu GỐC nên stub `window.dsTick=()=>{}` không tắt được nhịp; nhịp gốc gọi `pywebview.api.link_snapshot()` (stub
   không có) → `DS.state='error'` → `_chuaNoiMay()` chặn `start()` im lặng. Vá stub ở 3 bộ kiểm dính cùng gốc
   (`hold_confirm`, `step_accel`, `touch_hold`). Kiểm lại: 4/4 xanh, và 4/4 xanh cả khi ép CPU chậm 8× (trước đó
   ép 8× là đỏ).
2. **Đường cài lên iPhone**: web server LAN thêm `/manifest.webmanifest` + 3 icon `pwa-*.png`, và bơm thẻ
   `apple-touch-icon` / `apple-mobile-web-app-*` vào **bản web** (file HTML gốc không đổi). Bộ kiểm mới
   `tools/test_web_pwa.py` chạy chính EXE. ĐÃ BUILD EXE, bản trước giữ ở
   `tools/dist/OTL Roast Lab HMI.before-pwa-20260919.exe`. **CHƯA commit.**

Trước đó — **TRỐNG — CLAUDE ĐÃ NHẢ, CODEX TIẾP TỤC ĐƯỢC** (14/09/2026 tối). Xong đợt 15 (chủ máy: "sửa đi, và build… sửa
cho xong luôn đi"): làm hết kế hoạch `docs/ui/2026-09-14-tho-rang-tablet-tiep-codex.md` — Đợt A an toàn cảm
ứng, Đợt B mật độ tablet, Đợt C chuột/phím. **33/33 bộ kiểm UI ĐẠT** (có bộ mới `tools/test_ui_touch_real.py`
dùng cảm ứng CDP thật; chạy trên bản cũ thì ĐỎ đúng các lỗi). **ĐÃ BUILD EXE tên chuẩn** (md5 HTML nhúng
`19eadc94…` khớp bản trên đĩa; bản trước giữ ở `tools/dist/OTL Roast Lab HMI.before-tablet-dot-a-20260914.exe`).
**CHƯA commit, CHƯA thử tablet thật.** Sao lưu HTML: `docs/ui/backup/OTL Roast Lab.pre-tablet-dot-a-0914.html`
(md5 `6daf7758…`). Codex nhận file thì ghi đè dòng này.

Trước đó — TRỐNG — CLAUDE ĐÃ NHẢ, CODEX TIẾP TỤC (chủ máy 14/09/2026 chiều muộn: "build xong thì để codex
tiếp tục công việc"). Xong đợt 14: **32/32 bộ kiểm UI ĐẠT + `test_settings_file.py` ĐẠT, ĐÃ BUILD
EXE tên chuẩn** (md5 HTML nhúng `6daf7758…` khớp bản trên đĩa; bản trước giữ ở
`tools/dist/OTL Roast Lab HMI.before-caidat-tuluu-20260914.exe`). **CHƯA commit, CHƯA chạy máy thật.**
Codex nhận file thì ghi đè dòng này. Báo cáo đợt 14: `docs/ui/2026-09-14-caidat-tuluu-va-lag.md`.

**14/09 ~14:30 — Claude làm tiếp phần review tablet của Codex** (Codex hết hạn mức lúc 14:02). CHỈ ĐỌC + ĐO bằng
Chromium nền + cảm ứng thật (CDP), **KHÔNG sửa file nào trong khoá** — khoá vẫn TRỐNG. Báo cáo + kế hoạch:
`docs/ui/2026-09-14-tho-rang-tablet-tiep-codex.md`. ⛔ **P0 CHƯA SỬA:** giữ "Kết thúc mẻ"/"Xả liệu" bằng NGÓN rồi
trượt ra khỏi nút vẫn phát `drop=1`/`escape=1` (chuột thì huỷ đúng); cùng gốc, ± gas trượt ra vẫn ghi xuống máy.
Chờ chủ máy duyệt Đợt A.
(Đợt 14: trục khung "Đường rang dự kiến" theo Cài đặt; Cài đặt tự lưu + Hoàn tác + xuất/nhập CSV;
bỏ `backdrop-filter` ở lớp phủ/hộp đăng nhập vì làm lag con trỏ.) Sao lưu
`docs/ui/backup/OTL Roast Lab.pre-caidat-tuluu-0914.html` (bung từ EXE, md5 `4b866211…`).

Trước đó — TẠM DỪNG từ 14/09/2026 chiều — xong đợt 13, **31/31 bộ kiểm ĐẠT, ĐÃ BUILD
EXE tên chuẩn** (md5 HTML nhúng `4b866211…` khớp bản trên đĩa; bản trước giữ ở
`tools/dist/OTL Roast Lab HMI.before-hoso-dev-20260914.exe`). **CHƯA commit, CHƯA chạy máy thật.**
Codex cần file trước khi Claude quay lại thì cứ lấy — ghi đè dòng này là được.
(Đợt 13: **hộp "Sửa hồ sơ"** — đóng băng vùng
"Đường rang dự kiến", chỉ ô nhập cuộn; gọn phần thông tin dưới đồ thị; pha phát triển chỉnh theo
cả % lẫn thời gian). Chủ máy giao. Sao lưu `docs/ui/backup/OTL Roast Lab.pre-hoso-dev-0914.html`.

Trước đó — TẠM DỪNG từ 14/09/2026 12:00. Xong đợt 11 + 12, **31/31 bộ kiểm ĐẠT, ĐÃ
BUILD EXE tên chuẩn** (md5 HTML nhúng `558b2ab9…` khớp bản trên đĩa; bản cũ giữ ở
`tools/dist/OTL Roast Lab HMI.before-review-ux-20260914.exe`). **CHƯA chạy máy rang thật, CHƯA
commit.** Codex cần file trước khi Claude quay lại thì cứ lấy — ghi đè dòng này là được.

Đợt 12 (14/09 trưa): **thợ rang dùng thử + đối chiếu bản thiết kế Claude Design**, chủ máy giao. Phạm vi: nút "Kết thúc mẻ" khi cửa xả đang mở, trạng thái
tự xả trên chip DROP, chip DEV, chú giải đồ thị, dải pha lúc chờ, panel làm nóng, bảng Lịch sử,
thẻ hồ sơ, vị trí toast. Sao lưu: `docs/ui/backup/OTL Roast Lab.pre-ux-thorang-0914.html`.

Đợt 11 cùng ngày (xong, chờ build): **vá 11 phát hiện review của Codex**
`docs/ui/2026-09-14-otl-roast-lab-review.md`). Phạm vi: `finishRoast`/`roastTick`/`cmdDrop`/
`autoDrop`/`checkMileSets`/`applyMachine` (xác nhận xả + mất kết nối giữa mẻ), `loadProfile`/
`chkChargeReady` (chờ tự nạp), `openBatch`/`uxRoastAgain`/`uxDone*`, ngữ nghĩa hộp thoại +
nhãn ô hồ sơ, màu `.bp-bt`; phía Python `roast_db.finish`, `db_batch_set_weight`,
`inventory_db` (điều chỉnh kho/đơn theo kg). Sao lưu:
`docs/ui/backup/OTL Roast Lab.pre-codex-review-0914.html`.

Trạng thái trước đó — **CLAUDE ĐANG GIỮ — TẠM DỪNG** từ 13/09/2026 (đợt 10: **đường rang dự kiến**).
Chỉ đụng hộp "Sửa hồ sơ" + `buildTarget()`/`curveAt()`/`loadProfile()`/`finishRoast()`
— không chạm màn Rang, không chạm tầng chuyển động của đợt 9.
Vá **ba lỗi im lặng** Codex soát ra tối 12/09: (1) nạp hồ sơ không đẩy `deT`/`fcsT`
sang `R.mileSet` nên preview và máy chấm mốc theo hai ngưỡng khác nhau; (2)
`finishRoast()` ghi đè `p.temp`/`p.time` làm **mục tiêu trôi qua từng mẻ**; (3) RoR
xem trước dùng cửa sổ ±15s riêng, lệch với RoR màn rang. Nâng cấp: ô **giờ mốc**
`deTime`/`fcsTime`, **mẻ nền thật** vẽ mờ dưới đường kế hoạch, **RoR tại từng mốc**,
thang RoR tính từ đáy TP (±65 → ±25), và **bộ soi kế hoạch** `peAudit()` 9 nhóm luật.
**Soi lại theo bản thiết kế Claude Design** (mirror trên đĩa — `DesignSync` đòi
`/design-login` nên phiên nền không kéo bản mới được): lấy khuôn **dải 3 pha** và
**chú giải đường** của màn Rang áp sang; mẻ nền đổi thành **xám đứt** để không có hai
đường cam cạnh nhau; thẻ mốc thêm đơn vị `°/′`.
**Đợt trải nghiệm (chủ máy chốt 13/09): chỉnh được bằng NGÓN TAY.** Nút ± hai bên
**cả 10 ô số**, dùng lại `.fpm` 72×72 của Cài đặt + đúng luật tăng tốc của nút ± màn
Rang (chạm 1 bậc · giữ thì tự lặp bậc lớn dần · ngón đầu làm chủ). Ô tuỳ chọn đang
trống thì chạm ± lần đầu **lấy chính số app đang ước** làm điểm xuất phát. Tiêu đề và
hàng "Huỷ / Lưu" ra NGOÀI vùng cuộn (chỉ `.pe2col` cuộn) — khỏi vuốt hai lần cho mỗi
con số. ⚠ Đã thử `position:sticky` cho hàng nút rồi GỠ: nội dung trôi *dưới* hàng nút
và `test_ui_overlap` bắt đúng chỗ đó.
Kèm 2 bẫy của BỘ KIỂM (không phải lỗi app): bộ kiểm không đóng màn đăng nhập thì mọi
cú chạm rơi vào phím PIN trong khi đọc DOM vẫn xanh; và `test_ui_overlap` chưa biết
bỏ phần tử **bị khung cuộn cắt** — đã thêm `catBoiCha()`.
**Đợt "xuất sắc":** **kéo mốc DE · FCs · DROP ngay trên hình** (DROP cố ý chỉ kéo dọc
— nó dính mép phải; bán kính bắt 34px; hiện ô số cạnh ngón), nút **⤓ Lấy mốc theo mẻ
nền** (chép giờ/nhiệt xả + mốc DE/FCs từ `mile` trong kho + charge/gas/kg, hỏi lại
trước khi ghi đè), và **chạm thẻ cảnh báo là nhảy tới đúng ô** đang sai.
Bộ kiểm mới `tools/test_ui_profile_target.py` — **80/80 ĐẠT**; cả 29 bộ `test_ui_*`
chạy lại đều ĐẠT, chỉ còn `test_ui_overview_history` đỏ y như trên bản cũ. **ĐÃ BUILD VÀ THAY BẢN CHÍNH** `tools/dist/OTL Roast Lab HMI.exe` (md5 `73344ade…`,
HTML nhúng khớp bản trên đĩa; bản cũ giữ ở `.before-duongrang-20260913.exe`).
Smoke-test 9 giây không thoát; lối tắt Start trỏ đúng bản mới và Windows trả về
"Unpin from Start" — **đang ghim thật**. **CHƯA chạy với máy rang thật.**
⚠ `test_ui_hold_confirm` chập chờn **sẵn từ trước** (bản cũ 2/5, bản mới 1/5, dựng lại
trình tự thì hai bản hỏng y hệt) — đừng đổ cho đợt này. Chi tiết:
`docs/ui/2026-09-13-duong-rang-du-kien-nang-cap.md`.

**Đợt 9 — chuyển động mượt** (11/09/2026 tối).
Dựng tầng chuyển động mới bằng `@starting-style` + `transition-behavior:allow-discrete`
nên **không sửa một dòng JS đóng/mở nào** — hơn 20 hàm rải khắp file giữ nguyên.
Gốc của cảm giác giật KHÔNG phải đường cong mà là `.pane`/`.overlay` bật tắt bằng
`display`, thứ không nội suy được, nên **chưa từng có lượt RA**.
⛔ **ĐÃ THỬ VÀ GỠ: View Transitions cho đổi tab.** Chạy rất mượt nhưng đẩy việc đổi
DOM sang khung hình sau → `gotoTab()` hoá **bất đồng bộ**, mọi chỗ gọi rồi đọc DOM
ngay sẽ đọc trạng thái CŨ. Đừng thử lại. View Transitions chỉ còn dùng cho thu phóng
chi tiết mẻ (chỗ đó vốn async).
Bộ kiểm mới `tools/test_ui_smooth.py`. **27/27 bộ kiểm ĐẠT.**

**Đợt 8 — thống nhất thanh đầu (hướng A, chủ máy chốt 11/09).** Xoá **24 luật**
`html:has(#pane-rang.on)` nuôi "thanh đầu thứ hai". Phát hiện NGOÀI kế hoạch: một
trong số đó đổi cả bộ chữ toàn sân khấu — **màn Rang chạy IBM Plex, 5 tab kia chạy
Segoe UI**. Nay sáu tab một dáng, đo bằng nhau tuyệt đối.

**Đợt 7 — trạng thái chết** (chi tiết ở nhật ký).
Soát bằng ẢNH CHỤP 6 tab + dò đo, tìm ở lớp mà 26 bộ kiểm cũ không với tới:
**app tưởng mình đang nói điều gì đó với thợ, mà thật ra không.** Sửa 5, nặng
nhất là **luật làm dịu nút "Kết thúc mẻ" là MÃ CHẾT** — máy đứng yên mà nút nguy
hiểm nhất thanh đáy vẫn đỏ rực; và **nhãn "Cần xác nhận" không nói phải GIỮ** nên
thợ chạm hoài không có gì xảy ra. Bộ kiểm mới `tools/test_ui_deadstate.py`,
**đã chứng minh không vô dụng: gỡ 4 bản vá ra là bắt đủ 8/8 lỗi.**
Ba bộ kiểm liên quan chạy lại đều ĐẠT. **Đã build EXE tên chuẩn, md5 HTML nhúng
khớp bản trên đĩa, đã tạo lối tắt Start. CHƯA chạy với máy rang thật.**
⚠ Thanh đầu vẫn CHƯA VÁ — giữ nguyên chủ ý cũ.

Trạng thái trước đó — **CLAUDE ĐANG GIỮ — TẠM DỪNG** từ 08/09/2026 chiều (đợt 3: cử chỉ kéo + web).
Thêm **cử chỉ kéo viên thuốc kiểu iOS cho CẢ 6 cụm nút chọn**, vá lỗi hiển thị
"chưa có dữ liệu" (dấu `—` ở ô BT vẽ thành KHỐI ĐẶC 63×97 px), và chứng minh bản
web đồng bộ 100% với app. **22/22 bộ kiểm ĐẠT.**
⚠ **Thanh đầu CHƯA VÁ — cố ý.** Chủ máy dặn "từ từ hãy vá". Chẩn đoán + 3 hướng ở
`docs/ui/2026-09-08-ke-hoach-thong-nhat-thanh-dau.md`. Kết luận ngược trực giác:
**màn Rang mới ĐÚNG thiết kế, 5 tab kia mới lệch.**

Trạng thái trước đó — **CLAUDE ĐANG GIỮ — TẠM DỪNG** từ 08/09/2026 chiều (đợt 2: hiệu ứng lúc rang +
màu/chữ/font/popup). Sửa thêm 5 mục, thêm 2 bộ kiểm, **20/20 ĐẠT**. Nặng nhất:
thợ **không bao giờ nghe được "Crack đầu"** ở MỌI mẻ (FCs và DEV cùng progStep 9
nên câu sau cắt câu trước), và **nút vẽ chữ Việt bằng Arial** (24 phần tử).
CHƯA chạy máy thật, CHƯA commit.

Trạng thái trước đó — **CLAUDE ĐANG GIỮ — TẠM DỪNG** từ 08/09/2026 chiều (sau đợt rà soát hiển thị/
chuyển động/đồng bộ tab). Đã sửa 6 mục hiển thị + UX, 17/17 bộ kiểm ĐẠT, thêm bộ
kiểm mới `tools/test_ui_motion_sync.py`. Báo cáo:
`docs/ui/2026-09-08-ui-chuyendong-dongbo-audit.md`. **CHƯA build EXE, CHƯA chạy
máy thật.** ⚠ **RF-07 trong bản của Codex thì Claude CỐ Ý KHÔNG SỬA** — đã có
người nhận trong kế hoạch bàn giao của Codex; hai bên cùng sửa là hỏng.

Trạng thái trước đó — **CLAUDE ĐANG GIỮ — TẠM DỪNG** từ 08/09/2026 09:56. Đợt PD đã xong và đã build EXE
tên chuẩn; đang chờ chủ máy chạy thử trên máy thật và chốt **PD-4** (bậc nhảy nút `±`:
thiết kế ghi ±10 mỗi chạm, app đang ±1). Việc tiếp theo trong kế hoạch là P1 rồi P3.
Nếu Codex cần file trước khi Claude quay lại thì cứ lấy — ghi đè dòng này là được,
phần PD đã hoàn tất và có bộ kiểm giữ.

Khoá trước đó do **Codex** giữ cho việc tích hợp trợ lý chat. Chủ máy cắt ngang và
giao việc này cho Claude ("bắt tay vào làm đi", 08/09) — áp quy tắc ưu tiên người dùng
trong AGENTS.md. Kiểm tra trước khi nhận: `OTL Roast Lab.html` sửa lần cuối 07/09
20:28 và **chưa có dòng nào của trợ lý** trong đó (`grep assistant` = 0), tức Codex
chưa động vào file, module trợ lý vẫn nằm riêng ở `tools/roast_assistant_ui.js`. Mọi
sửa đổi dùng Edit theo chuỗi khớp chính xác, không ghi đè cả file, nên phần việc của
Codex trong các file khác không bị ảnh hưởng. Sao lưu:
`docs/ui/backup/OTL Roast Lab.pre-PD-0908-hold.html`.

Hoàn tất 07/09/2026 20:17 — Claude, đợt ba: dọn nốt bản rà soát Open Design.
Gom màu BT/ET về MỘT nguồn (trước đây thanh trên cùng và khung Rang đảo ngược ý nghĩa
màu của nhau); thêm dấu hiệu cuộn cho khối Thiết bị phụ; và vá một LỖI CÓ SẴN nặng:
applyMachine() gọi thẳng d.bt.toFixed() nên MỘT gói dữ liệu thiếu trường là chết cả
vòng cập nhật, màn Rang đứng hình giữa lúc máy chạy. Làm rõ 2 bộ kiểm 'hỏng sẵn' là do
ghim cứng thư mục dữ liệu (bản EXE để dữ liệu cạnh exe) — đã thêm tools/otl_testdata.py.
**28/28 bộ kiểm ĐẠT.** Đã build đúng tên chuẩn tools/dist/OTL Roast Lab HMI.exe, md5
HTML nhúng khớp, app đã mở lại. CHƯA chạy với máy rang thật.

## Nhật ký

| Thời điểm | Ai | Phạm vi | Kết quả |
|---|---|---|---|
| 14/09/2026 tối (15) | Claude | **An toàn cảm ứng + tablet + chuột/phím** (tiếp review tablet của Codex) | Chủ máy duyệt "sửa cho xong luôn". ⛔ **TB-01/02:** cảm ứng có *implicit pointer capture* nên `pointerleave` chỉ tới sau khi nhấc ngón → giữ "Kết thúc mẻ"/"Xả liệu" rồi trượt đi VẪN gửi lệnh, ± gas trượt đi vẫn ghi xuống máy. Vá bằng `holdGuard()` (nhả capture + so toạ độ pointermove, dung sai 12px) cho holdBind, ± Rang, ± Sửa hồ sơ. **TB-03:** Tạm dừng khi nối máy không làm gì → nay không đổi trạng thái/không ghi nhật ký, toast + dòng phụ "máy đang lái mẻ". **TB-04:** `finishRoast()` chấm DROP khi mẻ chốt theo cờ cửa xả. **TB-05–07:** `fit()` gắn `data-density="tablet"` + `--read-floor`/`--hit-min`; sàn chữ `max(cỡ thiết kế, 12px thật)` chỉ kiểu Chi tiết; vùng chạm `::after` trong suốt; thanh đầu cắt "…"; toast DONE nửa trái; tổng kết tablet 5 ô mốc một hàng + bỏ đường cong mini. **TB-08:** lăn chuột/↑↓ ô gas-gió-trống (≤1 lệnh/giây), Esc lúc RUNNING/DONE không thu toàn màn, phím M = Ghi mốc. BẪY: `test_ui_overlap` bỏ qua phần tử bị khung cuộn cắt — nút "Mẻ mới" khuất vẫn xanh, soi ảnh mới thấy. Bộ kiểm mới `test_ui_touch_real.py`. 33/33 ĐẠT, EXE md5 `19eadc94`. |
| 14/09/2026 chiều muộn (14) | Claude | **Cài đặt tự lưu + file CSV · trục khung dự kiến theo Cài đặt · con trỏ lag** | Chủ máy giao. (1) `peDrawPreview` dùng đúng luật trục màn Rang (`ch_auto/ch_tmin/ch_tmax/ch_rmin/ch_rmax`). (2) **Lag:** JS nhàn rỗi; đo khoảng cách rAF + trễ pointermove trên Chromium vẽ phần mềm → màn đăng nhập 100/100 khung >34ms do `backdrop-filter` (lớp phủ 12px + hộp đăng nhập 26px đè đường cong vẽ dần 17s). Bỏ blur ở `.overlay`/`.loginbox`/`#personalDialog::backdrop` → 0/436. Python thôi xoá `GPUCache`. (3) **Tự lưu** 0,6s, bỏ Hủy/Áp dụng/Lưu → Hoàn tác + Nhập/Xuất file; đang rang/làm nóng chặn đổi cổng/baud; cổng/baud chỉ đẩy cầu nối khi đổi đúng 2 ô. (4) **CSV** `nhom,khoa,gia_tri,mo_ta` UTF-8 BOM, nhập nhận `;` + thập phân phẩy + ANSI (NFC), kẹp dải, KHÔNG nhập COM/baud, $M chỉ điền form. API `settings_export`/`settings_import`. Bộ kiểm mới `test_ui_caidat_tuluu.py`, `test_settings_file.py`. 32/32 UI ĐẠT, build EXE md5 `6daf7758`. |
| 14/09/2026 chiều (13) | Claude | **Hộp "Sửa hồ sơ": đóng băng xem trước · gọn thông tin · phát triển theo %/thời gian** | Chủ máy giao. (1) **Đóng băng:** `.pe2col` thành cột flex KHÔNG cuộn, chỉ `.pe-fields` cuộn (không sticky). (2) **Gọn:** đầu khung 1 hàng (tên · gợi ý · chú giải), đồ thị 300px, thẻ mốc 3 dòng, thẻ soi 1 hàng vuốt ngang → khung ~800→~430px, ô nhập ~230→~400px (đo ở 1920×1080). (3) **Ô PHÁT TRIỂN** thay thẻ DEV (chấm DEV giữa FCs→DROP bỏ khỏi hình — nó không phải sự kiện): hai hàng ± thời lượng + %, cả hai GIỮ tổng thời gian; chỉnh giờ → `fcsTime`=tổng−thời lượng, chỉnh % → `devTarget` và BỎ `fcsTime` (nhãn neo "theo giờ nổ"/"theo %"). Markup cố định để nút đang giữ không bị dựng lại. **Bộ kiểm bắt 2 lỗi thật do đóng băng:** khung cao/thấp theo số thẻ soi → lưới ô nhập bị đẩy → nút ± trôi khỏi ngón (khoá chiều cao khung); ở cửa sổ 1024 nút "+" lòi 9px (container query xếp chồng hai hàng). Bộ kiểm `test_ui_profile_target` thêm mục 18, sửa `tap()` luôn cuộn tới nút (nút có thể nằm trong cửa sổ mà bị khung cuộn con che). **Trọn bộ 31/31 ĐẠT.** |
| 14/09/2026 trưa (12) | Claude | **Thợ rang dùng thử + đối chiếu Claude Design** | Đóng vai thợ đi trọn mẻ trên máy ảo, chụp từng bước, so 4 màn thiết kế. ⛔ **Lỗi nguy hiểm:** tự xả vừa chạy, thợ giữ "Kết thúc mẻ" → app ghi drop=0 ĐÓNG cửa xả giữa lúc trút hạt (HOLD_JOBS.drop không chặn theo pha, cmdDrop là toggle) → nay nút ghi "● Cửa xả đang mở" + phải xác nhận. Sửa thêm: chip DROP "tự xả" + báo trước 3°C; DEV = thời lượng phát triển (chip + tổng kết); chú giải Tăng nhiệt/Gas; dải pha "dự kiến" + % theo thời gian mẻ tới giờ; panel làm nóng "còn khoảng N phút", ẩn ô thời gian + nút trùng; Lịch sử thead thiếu `.hsel` → lệch cả hàng; toast che nút tổng kết; nút xoá hồ sơ; số BT viên trạng thái nền tối cố định. Báo cáo `docs/ui/2026-09-14-tho-rang-dung-thu.md` (có 4 việc chờ chủ máy quyết). |
| 14/09/2026 sáng (11) | Claude | **Vá 11 phát hiện review Codex** | Soát lại từng bằng chứng trên code, khớp cả 11. Lệnh xả `queued` → chờ máy báo cờ drop (10s, hẹn giờ riêng); mất kết nối giữa mẻ không tự đếm/chốt, đóng tay = INTERRUPTED; chặn **mẻ ma** pclink (`_machHoldoff`); chờ tự nạp gắn hồ sơ; tự xả thử lại có trần; kho/đơn theo kg thật (`rebase_batch` + `order_credits`); chống phản hồi cũ đè hộp chi tiết mẻ; ngữ nghĩa hộp thoại + tên ô. Bộ kiểm mới `test_ui_review_0914.py`, `test_inventory_rebase.py`. Bẫy: `page.evaluate()` trả promise đang chờ hộp hỏi → headless "Target crashed" (bản sao lưu cũng sập). Phản hồi `docs/ui/2026-09-14-phan-hoi-review-codex.md`. |
| 11/09/2026 tối (10) | Claude | **HỒNG — bong bóng trợ lý AI · hộp Sửa hồ sơ dựng lại · hiệu ứng đợt 2** | (1) **Trợ lý "Hồng".** Tên lấy từ *than hồng* — chính là tên màu chủ đạo của bản thiết kế, và là tên người Việt thật. Logo là ANH EM với dấu OTL trên thanh đầu: cùng ô bo góc đỏ `#D93A32`, ruột đổi thành ngọn lửa + đốm than. **KHÔNG dựng lại khung chat** — `#ra-panel` là của Codex ở `tools/roast_assistant_ui.js` (Python nạp vào lúc chạy, xem `roast_lab_hmi.py:1739,2152`); bong bóng chỉ là NÚT MỞ, gọi `window.otlAssistantOpen()`. Hạng AssistiveTouch: kéo khắp màn, thả thì hít về mép gần nhất, nhớ chỗ trong localStorage, tự kẹp vào trong màn khi cửa sổ nhỏ lại, mờ .62 lúc rảnh cho khỏi tranh mắt với mẻ đang rang. **Giữ để NÓI** (`SpeechRecognition`, vi-VN) — chữ rơi vào `#ra-input` chứ KHÔNG tự gửi, vì nhận dạng tiếng Việt trong xưởng ồn sai là chuyện thường và đây là trợ lý của một cái máy đang cháy. Khung chat nở ra từ đúng vị trí bong bóng (gốc phóng tính bằng JS theo toạ độ thật). **BẪY ĐÃ DÍNH:** đặt bong bóng trong `#stage` thì `position:fixed` bị `transform` của sân khấu NHỐT LẠI và nút teo theo tỉ lệ — đo được 47px thay vì 62px, mắt thường rất khó thấy. Phải đưa ra làm con trực tiếp của `body`. Bộ kiểm mới `tools/test_ui_buddy.py`, đã chứng minh không vô dụng (đặt lại vào `#stage` là B1 đỏ ngay). (2) **Hộp Sửa hồ sơ dựng lại theo ý chủ máy:** đường cong lên trên chiếm trọn bề ngang, thông số xuống dưới xếp hai cột, nhãn nằm trên ô. Đường cong hết nhoè — canvas khai cứng `880×600` rồi bị CSS ép về `100%×300px`, **sai tỉ lệ VÀ không theo tỉ lệ điểm ảnh màn hình**; đó mới là gốc của cảm giác "thô", không phải thiếu trang trí. Nay đo đúng ô, nhân `dpr` vào ma trận vẽ (`setTransform`) và giữ toạ độ theo pixel CSS nên không phải sửa một dòng vẽ nào. Ba chỗ mở hộp đều phải `requestAnimationFrame(peDrawPreview)` vì `refreshPE()` chạy TRƯỚC khi hộp hiện, lúc đó bề rộng bằng 0. Khối bố cục mới phải gắn tiền tố `#profedit` vì có ba luật `.pe2col`/`.pefield` nằm SAU trong file vẫn ép hai cột. (3) **Hiệu ứng đợt 2:** menu Cài đặt nhanh nở ra từ nút tài khoản + dòng hiện xếp tầng; viên thuốc tab thêm 3 nếp iOS (bóp theo trục, chữ tụt lại, lún khi nhấn); chuyển tab có HƯỚNG (trượt từ phải khi đi tới, từ trái khi lùi) — hoà tan trơn không có hướng chính là chỗ làm nó trông thô; 7 trang con Cài đặt có lượt vào; danh sách trong hộp thoại hiện xếp tầng. (4) **Lỗi thật đã vá:** băng `#faultBanner` ghim cứng `top:118px` nên đè lên chip lọc hồ sơ, ô "Tên" của hộp Sửa hồ sơ và tiêu đề trang Cài đặt — nó `pointer-events:none` nên vẫn bấm xuyên qua được nhưng KHÔNG ĐỌC ĐƯỢC, tức cảnh báo che mất thông tin, hỏng đúng việc nó sinh ra để làm; dời xuống đáy. (5) **Sửa lại bản vá khoá-khi-mất-kết-nối của đợt trước:** bản đầu đặt `btn.disabled` trong vòng vẽ mỗi nhịp — vòng đó tắc là nút KẸT KHOÁ vĩnh viễn và thợ mất quyền điều khiển máy; nay chỉ làm mờ, còn chặn thật chuyển sang `job.blocked` hỏi ngay lúc bấm, không để lại trạng thái dính. |
| 11/09/2026 tối (9) | Claude | **Tầng chuyển động mượt** | Chủ máy xin "đổi tab, mở hộp thoại, báo lỗi, hồ sơ có curve, thu phóng — tất cả siêu mượt". **Chẩn đoán khác với yêu cầu:** gốc của cảm giác giật KHÔNG nằm ở đường cong mà ở chỗ `.pane` và `.overlay` bật tắt bằng `display`, thứ **không nội suy được**, nên chưa từng có **lượt RA** — màn cũ biến mất tức thì rồi màn mới mới trượt vào; thêm đường cong đẹp cỡ nào cũng vô ích. Dựng bằng `@starting-style` + `transition-behavior:allow-discrete`, nhờ đó **không phải sửa một dòng JS nào** trong hơn 20 hàm đóng/mở rải khắp file. Thêm: bộ đường cong `--ease-out`/`--ease-in`/`--spring` (lò xo thật viết bằng `linear()`, cubic-bezier không tả được vượt đà); đường cong hồ sơ **tự vẽ ra** nhờ `pathLength="1"` chuẩn hoá mọi đường về cùng chiều dài; thu phóng chi tiết mẻ **nở ra từ chính dòng vừa bấm** (matched-geometry qua View Transitions). ⛔ **ĐÃ THỬ VÀ GỠ — đừng thử lại:** gói `gotoTab` trong `startViewTransition`. Mượt thật, nhưng nó gọi hàm đổi DOM ở KHUNG HÌNH SAU nên `gotoTab()` hoá **bất đồng bộ** — mọi chỗ gọi rồi đọc DOM ngay đọc phải trạng thái cũ (`test_ui_consistency` đỏ ngay); và đổi tab nhanh tay làm promise từ chối `"Transition was skipped"` nổi thành lỗi JS, đỏ thêm 3 bộ nữa. Đổi hợp đồng một hàm điều hướng trong app điều khiển máy để lấy hiệu ứng là đổi sai giá. **Ba lỗi tự gây, đều do bộ kiểm bắt:** (a) chốt "đang rang thì đừng đóng băng" viết `window.R` — mà `R` khai bằng `const` nên **không nằm trên window**, chốt chưa bao giờ chạy; (b) `.pane` chạy `transform:scale()` → tạo containing block mới cho mọi con `position:fixed`, đủ để lệch hộp thoại, nay chỉ hoà tan bằng opacity; (c) ép `flex-wrap:nowrap` ở MỌI bề rộng làm cửa sổ 1024 nhồi đến mức chip kết nối tràn 52px, nay chặn dưới 1180px. Bộ kiểm mới `tools/test_ui_smooth.py` (6 mục, có 2 chốt an toàn). **27/27 ĐẠT.** |
| 11/09/2026 chiều (8) | Claude | **Thống nhất thanh đầu — hướng A** | Chủ máy chốt hướng A sau khi tự chụp hai thanh đầu cạnh nhau. Xoá **24 luật** `html:has(#pane-rang.on)` vốn nuôi một "thanh đầu thứ hai" chỉ dựng khi màn Rang mở; đưa thông số của màn Rang (đã đúng thiết kế) lên thành thanh dùng chung. **Phát hiện ngoài kế hoạch, nặng hơn cả mục tiêu ban đầu:** một trong 24 luật đó đổi `--f-ui`/`--f-num`/`--f-mono` cho **cả sân khấu**, nghĩa là **màn Rang chạy IBM Plex còn 5 tab kia chạy Segoe UI** — đổi tab là đổi cả bộ chữ toàn màn, không riêng thanh đầu; kế hoạch cũ chỉ đo thanh đầu nên không thấy. Chỉ xoá luật thì Rang tụt ngược về Segoe, nên phải nâng IBM Plex lên dùng chung. **Hai bẫy nằm dưới:** (1) nền viên thuốc trượt là `--panel`, trùng đúng màu thanh đầu — gỡ khung bọc ra là nó **tàng hình**, mất luôn dấu báo tab đang mở; đổi sang `--card`. (2) `@media(max-width:1700px)` đo **cửa sổ** chứ không đo sân khấu (rộng cứng 2560px rồi mới thu nhỏ) nên cửa sổ 1366 vẫn ăn và đẩy cụm tab xuống hàng; trước đây chỉ Rang thoát nhờ 4 luật `!important`. Đo lại: cao thanh, cỡ chữ tab, cỡ đồng hồ, bộ chữ và mốc bắt đầu nội dung **bằng nhau tuyệt đối ở cả 6 tab** — hết cú nhảy 8px. `test_ui_nav_drag` mục D8 đang giữ luật đời cũ ("màn Rang không được hiện viên thuốc") nên đã sửa bài kiểm theo luật mới, không sửa app theo bài kiểm. Sao lưu `docs/ui/backup/OTL Roast Lab.pre-header-unify.html`. |
| 11/09/2026 chiều (7) | Claude | **Trạng thái chết — luật không ăn, nút câm, nhãn sai việc** | Soát bằng ảnh chụp thật 6 tab thay vì đọc code. **Sửa 5.** (1) **Nặng nhất — `.tbtn.warn.idle` là MÃ CHẾT.** Mã có ghi rõ chủ ý "chưa vào mẻ thì Kết thúc mẻ đừng hút mắt", JS bật/tắt lớp `idle` đúng theo `R.phase`, nhưng luật chỉ có 3 LỚP (0,3,0) nên thua cả `#btnDrop` lẫn `#stage #pane-rang #btnDrop` (3 ID). Kết quả: máy đứng yên mà **nút nguy hiểm nhất thanh đáy lại là thứ bắt mắt nhất** — đúng ngược điều thiết kế muốn. Nhắc lại luật ở đúng độ đặc hiệu ba-ID + lớp. (2) **Nhãn cụm nút hệ trọng không dạy cách bấm.** Một đợt trước ghi đè nhãn thành "Cần xác nhận"; hai nút này CHỈ ăn khi GIỮ đủ `HOLD_MS`, nên trên màn cảm ứng thợ sẽ chạm, chạm nữa, không gì xảy ra, và **không ai bảo phải giữ**. Đổi thành "Giữ 0,5 giây để xác nhận", số giây lấy thẳng từ `HOLD_MS` qua `_holdSec()` nên không thể lệch; đồng bộ luôn `tb.holdhint` ở cả hai từ điển (đang là mã chết vì bị ghi đè lúc chạy). (3) **Kho rỗng mà ba nút vẫn bấm được** — Xuất CSV / Xóa bộ lọc / Bỏ chọn mẻ. Trước/Sau thì khoá đúng từ lâu → là bỏ sót. Khoá theo đúng thứ mỗi nút cần, và kho rỗng mà ĐANG lọc thì "Xóa bộ lọc" vẫn phải mở để thợ thoát ra. (4) **Hai hệ đánh số đá nhau ở Tổng quan** — `uxTick()` đánh số theo thang 4 bước của dải `#uxGuide` rồi dùng lại NGUYÊN câu đó làm phụ đề thẻ "Chuẩn bị mẻ rang" vốn có thang 3 bước riêng; thẻ hiện "1 · Chọn hồ sơ" ngay trên danh sách mà bước 1 là "Làm nóng máy". Bỏ tiền tố "N ·" khi dùng lại. (5) **Ô cấu hình máy kẹp dải âm thầm rồi tự ghi xuống máy sau 1 giây** — thợ gõ 300 tưởng máy nhận 300, thực tế `$M` nhận 100; nay nói ra dải hợp lệ và số đã bị sửa. **Bộ ĐO lại tự sai lần thứ 8:** thước đầu tiên so hai nút bằng TỶ LỆ TƯƠNG PHẢN, mà xám `--mute` và cam-đỏ gần như cùng độ sáng (1,3) nên **bản vá ĐÚNG vẫn bị báo hỏng** — phải so thẳng với token. Bộ kiểm mới `tools/test_ui_deadstate.py` nhận `OTL_APP_HTML` để chạy trên bản sao đã gỡ vá; **gỡ 4 bản vá ra là bắt đủ 8/8**. `test_ui_hold_confirm`, `test_ui_overview_history`, `test_ui_motion_sync`, `test_exe_end_to_end` đều ĐẠT. Build EXE tên chuẩn (sao lưu bản cũ `*.before-deadstate-*`), **bung HTML khỏi EXE so md5 = khớp**, đủ 5/5 dấu hiệu bản vá. Lối tắt Start đã tạo. CHƯA chạy máy thật, CHƯA commit. |
| 08/09/2026 chiều (6) | Claude | **Cử chỉ kéo kiểu iOS · lỗi ô "chưa có số" · đồng bộ web** | (1) **Hiệu ứng chủ máy đặt** — segmented control kiểu iOS: giữ ô đang chọn rồi kéo, viên thuốc bám ngón tay, qua ô nào ô đó sáng trước, thả mới chuyển. Làm cho **CẢ 6 cụm** (thanh tab chính · Cài đặt · 2 tab con Hồ sơ · Kho · chip lọc hồ sơ · chip lọc log) bằng MỘT cơ chế khai báo, tự nhận trục ngang/dọc. Năm cụm kia lúc thường KHÔNG có viên thuốc nên nó chỉ hiện trong lúc kéo — dáng vẻ khi không ai đụng vào giữ nguyên. **Hai bẫy đã trả giá:** `touch-action:auto` khiến trình duyệt giữ luôn cử chỉ để cuộn và **không gửi pointermove nào cả** (cụm trong vùng cuộn được chỉ nhận đúng pointerdown rồi im); và `#subnav` xếp **DỌC** nên logic chỉ-tính-ngang ra dx=0, kéo bao nhiêu cũng không chạy. Bộ kiểm mới `test_ui_nav_drag.py` bắn **chạm thật qua CDP**, 9 kịch bản gồm ngón thứ hai chen vào và mất tiêu điểm giữa chừng; đã chứng minh không vô dụng (gỡ tính năng ra là hỏng 4 mục). (2) **Lỗi hiển thị nặng:** dấu `—` báo chưa-có-số bị vẽ ở cỡ **112px màu cam BT** → ra **khối đặc 63×97 px**, thợ nhìn tưởng thanh mức hỏng. Sửa tại hàm `txt()` nên ăn cho cả **74 chỗ**. Bẫy đi kèm: lần đầu dùng `--faint` làm màu chữ chỉ được 1,7–2,2:1 — đúng loại lỗi vừa đi sửa chỗ khác — phải đổi sang `--mute`. (3) **Web:** thêm `gotoHs`/`khoView`/`setProfFilter` vào gương soi (đều là hàm giao diện, KHÔNG có lệnh máy). Bộ kiểm mới `test_web_sync.py` chạy **máy chủ thật trên thư mục dữ liệu tạm**, chứng minh web phục vụ **byte-identical** với file trên đĩa và cử chỉ kéo chạy thật trên web. **Bốn lần nữa bộ ĐO tự sai** (so CRLF với LF nên lệch đúng số dòng; Playwright TỰ HUỶ hộp prompt hỏi PIN web; chưa qua cổng PIN web nên mọi API 401 và tưởng web hỏng; sau đăng nhập web mở hộp chọn cổng COM phủ kín màn). **22/22 ĐẠT.** |
| 08/09/2026 chiều (5) | Claude | **Hiệu ứng lúc rang · màu · chữ · font · popup** | Hai bộ kiểm mới: `test_ui_roast_effects.py` (chạy TRỌN một mẻ, thay hàm phát tiếng + `speechSynthesis` bằng bản ghi sổ) và `test_ui_colors_fonts.py` (6 tab × 2 nền × {chờ, đang rang} + **7 màu chủ đạo** × 2 nền + **13 hộp thoại** × 2 nền — vùng đợt trước không với tới vì hộp đều đang đóng). **Sửa 5:** (R-01, P1) `mileWatch` gọi `say()` từng mốc mà `say()` huỷ câu đang nói → **"Crack đầu" bị "Phát triển" cắt trong cùng mili-giây**; xảy ra ở MỌI mẻ vì `MILE_STEP` xếp FCs và DEV **cùng progStep 9** — mốc mã nguồn tự ghi là *quan trọng nhất* không bao giờ phát ra tiếng, đúng tính năng sinh ra để thợ khỏi nhìn màn. Nay gom một câu + chỉ phát bộ tiếng mốc nặng nhất (`MILE_RANK`). (R-02) **24 phần tử vẽ chữ Việt bằng Arial** — `button`/`input` không kế thừa font; bịt một luật `font-family:inherit` (0-0-1 nên không đè luật cũ), 24→0. Bẫy này đã dính từ 30/07. (R-03) chữ "đang cháy" chỉ **1,85:1** trên nền nâu ép cứng — biến mất ĐÚNG LÚC lửa cháy. (R-04) `personalContrast()` hiệu chuẩn mực accent **chỉ với `--card`**, mặt nền tối hơn thì tụt; nay lấy mặt nền tệ nhất trong 4 mặt — cả 7 màu chủ đạo ≥4,65. (R-05) thông báo che **2 nút ±** 2,2 giây lúc đang rang. **Ba lần nữa bộ ĐO tự sai** (quét cả trang sau popup → 221 mục ma; ghim màu dự phòng trắng; đo cả nội dung `<details>` đang đóng nên nhận màu CŨ) — cộng đợt 1 là **bảy**. `test_ui_motion_sync` nay tách ghi nhận khỏi lỗi để không đỏ vĩnh viễn. **20/20 ĐẠT.** |
| 08/09/2026 chiều (4) | Claude | **Rà soát hiển thị · chuyển động · đồng bộ tab** | Tiếp bản của Codex (bản đó đi luồng nghiệp vụ, bản này đi phần nhìn). Viết bộ kiểm mới `test_ui_motion_sync.py` — 7 kịch bản, tự khai kịch bản nào chạy được để không âm thầm bỏ qua. **Sửa 6:** (D-01) trục thời gian đồ thị in đè thành `−0:3000:00` ở MỌI mẻ chưa nạp, cả hai nền — canvas nên không bộ kiểm nào đọc được; (D-02/D-03) gas/gió/trống và RoR lấy **màu đường vẽ làm màu chữ** — đo được 1,91–2,72:1 trên nền sáng, tách `--oci` khỏi `--oc`, thanh mức giữ nguyên màu thiết kế; (D-04) `Cần xác nhận` và `Không lửa` dưới ngưỡng đọc; (D-05) `uxPreheat()` ghi bằng `textContent` **xoá mất chấm trạng thái** ngay nhịp đầu → luật CSS chấm vàng/xanh thành **mã chết**, chỉ bản chạy thật dính; (D-06) 3 nút khoá câm nay nói lý do. **CỐ Ý KHÔNG SỬA:** transition `width` và hoạt ảnh `box-shadow` — đo thật **0 tác vụ >50 ms**, đổi sang `transform` sẽ méo bo góc, không đáng. **Bốn lần bộ ĐO tự sai đã bắt kịp** (ghép nền sai → 22 lỗi ma; Chromium mới gắn `cssRules` rỗng → nhảy qua cả 1624 luật; `focus()` script không bật `:focus-visible`; thiếu cầu pywebview → báo oan app). Đồng bộ tab **ĐẠT hết**. 17/17 bộ kiểm ĐẠT. |
| 07/09/2026 | Codex | Rà soát toàn app và build | Kiểm 6 tab, 7 trang cài đặt, 10 hộp thoại, các luồng dữ liệu/điều khiển giả. Sửa chú giải NOSEL, hai nhãn tiếng Anh, vùng bấm nhỏ. Các bộ kiểm đạt; build bản `tools/dist/OTL Roast Lab HMI - UI 20260907.exe` vì EXE gốc đang chạy và bị khóa. Chi tiết ở `2026-09-07-full-ui-check.md`. |
| 07/09/2026 | Codex | Kiểm tra tiếp màn Rang | Áp font IBM Plex đã nhúng, giới hạn ô nhập trực tiếp để không tràn. Kiểm nhập gas/gió/trống gửi đúng giá trị, Escape không gửi lệnh; kiểm menu, chuyển view, mất kết nối và ba kích thước màn hình đạt, không lỗi JS. |
| 07/09/2026 | Codex | Màn Rang theo ảnh mẫu của chủ máy | Thu gọn nav, sửa tỷ lệ hai cột, mốc và tiêu đề đồ thị, thẻ BT/ET/thời gian, ba ô điều khiển và thanh đáy. Thao tác bổ sung giữ trong menu; nạp tay hiện ở thanh đáy trước mẻ. Giữ xác nhận xả/kết thúc. Kiểm thử match_reference, roast_columns, live, compat_roast và toolbar đạt. |
| 07/09/2026 13:36 | Claude | Áp bảng màu bản thiết kế | Xong — thêm màu chủ đạo `ember` ("Than hồng"). Sao lưu: `docs/ui/backup/OTL Roast Lab.pre-design-0907-1336.html` |
| 07/09/2026 14:2x | Claude | Áp bản thiết kế cho giống hệt — đợt 1 | Xong: nhúng chữ IBM Plex offline, da thẻ hồ sơ, thuật ngữ "Nhiệt nạp", vá ô ngày Lịch sử bị bóp nát. Sao lưu `docs/ui/backup/*pre-font*`. CÒN: bố cục màn Tổng quan / Rang / Lịch sử + thanh trên cùng |
| 07/09/2026 14:5x | Claude | Dựng lại màn Rang theo bản thiết kế | Xong 5 mục: vá ghi đè theo tài khoản, cột phải 4 thẻ + mốc hồ sơ, dải giai đoạn giờ-trước-%, 3 ô điều khiển có chấm màu + thanh mức, thanh dưới bỏ icon. CÒN: màn Tổng quan, Lịch sử |
| 07/09/2026 19:17 | Claude | Dựng nốt Tổng quan + Lịch sử + hộp Giới thiệu | Tổng quan: bỏ 4 thẻ cũ, thêm khối "Chuẩn bị mẻ rang" 3 bước bám máy trạng thái sẵn có, ngày trong lời chào, 3 lối đi nhanh, bảng 3 mẻ gần nhất. Lịch sử: bảng vào thẻ bo góc, tiêu đề dính đỉnh, phân trang xuống đáy thẻ. Mới: hộp Giới thiệu. Làm rõ ô ngày `dd-----yyyy` là do Chromium của bộ kiểm thiếu ICU chứ KHÔNG phải lỗi app. CÒN NỢ: cột Khối lượng — bảng `batches` chưa có trường này. |
| 07/09/2026 19:37 | Claude | Đợt hai theo bản thiết kế: Hồ sơ + khối lượng + số đếm | Màn Hồ sơ: lưới 3 cột, thẻ gọn, sao/sửa/xoá xuống hàng thao tác đáy thẻ, tiêu đề "Hồ sơ rang" đổi theo tab con. Kho: thêm cột `charge_kg` (tự nâng cấp kho cũ) + `RoastDb.count()`; API `db_batch_set_weight`, `db_batch_count`. Lịch sử có cột Khối lượng, panel sau mẻ có ô nhập kg (thợ nhập, không suy từ cân phễu). Đã build EXE tên có ngày vì EXE gốc bị app đang chạy khoá. |
| 08/09/2026 chiều (3) | Claude | **⛔ Vá lỗi CHẠY LOẠN + tự kiểm sâu** | Chủ máy hỏi "ai kiểm?" nên đi bịt nốt hai chỗ trống. (1) **Bộ kiểm chạm ngón tay thật** `tools/test_ui_touch_hold.py` — bắn `Input.dispatchTouchEvent` qua CDP, có `pointerType='touch'`, có `pointercancel`, có ngón thứ hai. Nó **bắt được một lỗi thật**: hai lần `pointerdown` liên tiếp không có `stop()` ở giữa (ngón thứ hai chạm vào, mép găng quẹt trúng) làm bộ đếm cũ bị bỏ rơi và **chạy mãi — không còn ai chạm màn mà gas vẫn tự leo lên 100**. Nút hệ trọng dính cùng kiểu nhưng nặng hơn: mất `pointerup` là **lệnh tự phát sau 1 giây**, tức cửa xả tự mở. Vá bằng: khoá theo `pointerId` (ngón đầu làm chủ), gọi `stop()` phòng hờ ở đầu mỗi lần nhấn, và lưới an toàn bắt `pointerup`/`pointercancel` ở tầng `document` cộng `window.blur`. Đã chứng minh bộ kiểm không vô dụng: gỡ bản vá ra là nó hỏng ngay. (2) **Bộ kiểm EXE thật** `tools/test_exe_end_to_end.py` — chạy chính EXE trong `dist`, lái bản web mà EXE tự phục vụ, xác nhận EXE ôm đúng HTML mới và cử chỉ giữ chạy đúng qua cầu Python thật. (3) Đối chiếu nhân trình duyệt: WebView2 trên máy **152**, Chromium của bộ kiểm **149** — cùng nhân, bản máy mới hơn. |
| 08/09/2026 chiều (2) | Claude | **PD-4b — trải nghiệm cụm nút ±** | Bốn việc, ba trong đó lấy thẳng từ bản thiết kế. (1) Gợi ý **"giữ để chạy nhanh"** ở góc phải hàng tiêu đề — thiết kế ghi `hồ sơ 45% · giữ để chạy nhanh`, app có tính năng chạy nhanh dần mà không nói ra thì thợ không biết dùng; đo ở 1920/1366/1280 đều không tràn. (2) Đang giữ ở bậc lớn thì ô đó báo **×5 / ×10** kèm một tiếng tách lúc sang bậc — xưởng ồn, thợ nhìn hạt chứ không nhìn màn. (3) **Vạch mốc trên thanh mức** chỉ chỗ MÁY đang thật sự chạy, vì nay số trên màn đi trước máy tới 1 giây; khớp rồi thì tự ẩn. (4) Chạm trần 0/100 không xếp lại cùng một số để khỏi bắn lệnh trùng mỗi giây. **Vá 2 lỗi lộ ra khi chụp hình:** bảng trợ giúp bật sau 700 ms che mất nhãn ×5 và thanh đếm giữ (nay khoá trong lúc đang giữ, rê chuột vẫn xem được — đúng bẫy S8 đã ghi ở mục soát); và vạch mốc bị luật `.obar i` tô cùng màu cam với thanh nền nên chìm nghỉm (nay `:not(.ack)`, đo lại tương phản ở cả nền sáng lẫn tối). |
| 08/09/2026 chiều | Claude | **PD-4 — nút ± bậc lớn dần, máy nhận 1 lệnh/giây** | Chủ máy chốt. Chạm = **±1** (trước là ±5: `data-d` chỉ là chiều, độ lớn ở `OUT_STEP`). Đè giữ = tự lặp 200 ms, bậc lớn dần ±1 → ±5 sau 1,2 s → ±10 sau 3 s. Quan trọng nhất: **đang giữ thì chỉ đẩy xuống máy mỗi giây một lần** + chốt ngay khi nhả tay, thay vì bắn một lệnh Modbus mỗi nấc. Đo được: giữ 2,6 s đi 39 nấc mà chỉ tốn 3 lệnh. Bộ kiểm mới `tools/test_ui_step_accel.py`. |
| 08/09/2026 | Claude | **Đợt PD — giữ 1 giây để xác nhận** | Theo nguồn Claude Design (đọc cả khối `x-dc`, không chỉ phần hình). **Xả liệu** và **Kết thúc mẻ** trước đây `onclick` → `machCmd` NGAY: một cú quệt tay vào màn cảm ứng là mở cửa xả giữa mẻ. Nay phải giữ đủ 1 giây, có thanh chạy `scaleX` trong lòng nút, nhả sớm/kéo ngón ra là huỷ và KHÔNG gửi gì. **Thoát app** đổi từ bấm-hai-lần sang cùng cử chỉ, giữ nguyên chốt chặn khi đang rang và chặn ngay lúc bắt đầu giữ. Bỏ **BT/ET chết trên thanh đầu** (markup + JS + 9 luật CSS) vì thiết kế không đặt nhiệt ở đó. Sửa chú thích SAI trong mã ("app hỏi lại bằng hộp thoại" — không hề có hộp thoại nào). Bộ kiểm mới `tools/test_ui_hold_confirm.py`. Sao lưu `docs/ui/backup/OTL Roast Lab.pre-PD-0908-hold.html`. |
| 07/09/2026 20:17 | Claude | Đợt ba: màu BT/ET, dấu cuộn Thiết bị phụ, vá applyMachine | Gom `--c-bt`/`--c-et` về một nguồn + thêm `--bt-ink`/`--et-ink` (đo tương phản 5,07–7,91:1), bỏ bản sao ở accent otl và #pane-rang, sửa nhiệt xả tô nhầm màu ET. Vệt mờ báo còn nội dung ở khối Thiết bị phụ + nhãn "0/6 đang bật". VÁ LỖI CÓ SẴN: applyMachine thiếu trường là ném lỗi, chết luôn gas/gió/trống và nút nạp-xả. Sửa giả định thư mục dữ liệu trong test_api_scope + test_mcp_roaster. 28/28 đạt. Build EXE tên chuẩn. |
