# Thợ rang dùng thử Roast Lab trên tablet — làm tiếp phần Codex (14/09/2026 chiều)

## Bối cảnh

13:51 chủ máy giao Codex: đọc lịch sử Claude, đóng vai thợ rang (skill `rang-ca-phe`), dùng app từ A–Z, chấm dễ
xài / tùy biến chuyên sâu / tinh tế / tốc độ thao tác, **check lỗi**, rồi **lập kế hoạch chi tiết nâng cấp**; thử
trên tablet Windows bằng chạm–vuốt lẫn chuột–phím, **đặc biệt màn Rang sau khi bấm Bắt đầu**. Chủ máy dặn thêm:
**không chiếm chuột**, thử bằng cách khác.

Codex đã chạy hồi quy nền (32 bài UI + 2 bài phụ: ĐẠT), bắt đầu thử chạm ở 1366×768, mở hai câu hỏi (vùng chạm,
nút "Tạm dừng") rồi **dừng lúc 14:02 vì hết hạn mức**. Claude làm tiếp theo đúng cách đó.

- **Không chiếm chuột:** Chromium chạy nền (Playwright), **cảm ứng thật** qua CDP `Input.dispatchTouchEvent` —
  không phải sự kiện pointer tổng hợp.
- **Hai cỡ tablet:** 1280×720 @150% (tablet 1920×1080 đặt tỉ lệ 150%) và 1366×768 @100%; đối chứng 1920×1080.
- **Máy ảo:** stub + `feed()` của `tools/test_ui_review_0914.py`. Không nối máy thật, không đụng dữ liệu xưởng.
- **Chỉ đọc + đo, CHƯA sửa app.** Bản đo = bản EXE đợt 14 (md5 HTML `6daf7758…`).

## Kết luận chính

Luồng rang lõi đúng và đã an toàn hơn nhiều so với đầu ngày. Nhưng **trên màn cảm ứng có một lỗi P0 làm cơ cấu thật
chạy ngoài ý muốn**, cùng gốc với một lỗi P1 ở nút gas/gió/trống. Cả hai **chỉ lộ khi dùng ngón tay**; chuột chạy
đúng, nên 32 bộ kiểm hiện có đều xanh.

Giao diện đang được thiết kế cho màn lớn: sân khấu 2560 px thu còn 0,5 lần trên tablet → nhiều chữ 8–9 px và vùng
chạm dưới 44 px.

| Tiêu chí chủ máy hỏi | Chấm | Vì sao |
|---|---|---|
| Dễ xài, thân thiện | 7/10 | Luồng Chọn hồ sơ → Bắt đầu → chỉnh → xả → tổng kết rõ; màn 1920 dễ đọc. Tablet chữ phụ quá nhỏ. |
| Tùy biến chuyên sâu | 8,5/10 | RoR kiểu Artisan 4 tầng, trục đồ thị, thiết bị máy có, 50 tham số $M, mục tiêu DE/FCs/% phát triển theo hồ sơ, mẻ nền, cá nhân hóa giao diện, API/MCP, file cài đặt CSV. |
| Tinh tế | 7/10 | Giữ-để-xác-nhận, nút nói "● Cửa xả đang mở", gợi ý "lần trước 28%", tổng kết so mục tiêu. Trừ điểm: "Tạm dừng" không dừng gì, tổng kết thiếu DROP, thanh đầu chồng chữ. |
| Tốc độ thao tác | 8/10 | Chạm ± phản hồi tức thì; giữ 1,5 giây nhảy 14 bậc mà máy chỉ nhận 2 lệnh. Chưa có phím tắt, không lăn chuột để chỉnh. |
| Chạm–vuốt trên tablet | 5/10 | Lỗi P0/P1 khi trượt ngón; 20 vùng chạm < 44 px; 57 nhãn < 13 px. |

## Điểm đang làm tốt (có đo)

1. **Bắt đầu không tự tin quá sớm:** chạm BẮT ĐẦU chỉ gửi `charge=1`, pha vẫn `IDLE`; máy báo CHARGE mới chuyển
   `RUNNING`.
2. **± gas nhanh và không dội lệnh:** 3 chạm = 3 lệnh 36/37/38. Giữ 1,5 giây: 38 → 52 nhưng chỉ ghi 2 lệnh (39, 52).
3. **Xả → tổng kết đúng một lần:** `db_batch_finish` gọi 1 lần, không lỗi JS suốt mẻ.
4. **Chuột:** rê khỏi nút đang giữ là huỷ ngay, cả nút ± lẫn nút giữ-để-xác-nhận.
5. **Tổng kết có giá trị cho thợ:** tổng thời gian, nhiệt xả, % phát triển, từng mốc so mục tiêu (±), kg, ghi chú,
   "Rang lại hồ sơ này".

## Phát hiện

### TB-01 · P0 — Giữ "Kết thúc mẻ" / "Xả liệu" bằng ngón rồi trượt ra khỏi nút: lệnh VẪN phát xuống máy

**Bằng chứng** (1280×720, chạm 100 ms rồi trượt 150 px ra khỏi nút, ngón vẫn đè 1,5 giây):

| Nút | Ngón trượt ra | Chuột rê ra | Ngón giữ đúng chỗ (đối chứng) |
|---|---|---|---|
| Kết thúc mẻ `#btnDrop` | **gửi `drop=1`**, `_dropPending` bật | không gửi | gửi `drop=1` |
| Xả liệu `#btnEscape` | **gửi `escape=1`** | không gửi | gửi `escape=1` |

**Nguyên nhân:**
- `holdBind()` huỷ khi nhận `pointerleave`.
- Với cảm ứng, Chromium tự giữ con trỏ trên phần tử vừa chạm (*implicit pointer capture*). Vì vậy `pointerleave`
  chỉ tới **sau khi nhấc ngón**. Chuỗi đo được: `pointerdown → gotpointercapture → touchmove… → pointerup →
  lostpointercapture → pointerleave`.
- Đồng hồ `HOLD_MS` chạy hết trước khi `pointerleave` tới, nên lệnh phát.
- Chú thích trong mã ghi "kéo ngón ra khỏi nút… đều huỷ và KHÔNG gửi gì" — điều này **chỉ đúng với chuột**.

**Tác động:**
- Thợ đeo găng tì tay lên thanh đáy, ngón chạm trúng "Kết thúc mẻ" rồi trượt đi vì đang nhìn hạt → cửa xả mở
  giữa mẻ.
- Tương tự với "Xả liệu": xi-lanh thoát liệu chạy.

**Vì sao bộ kiểm không bắt:** `test_ui_hold_confirm` / `test_ui_touch_hold` kéo ra ngoài bằng chuột hoặc sự kiện
pointer tổng hợp — không có implicit capture.

**Chấp nhận sửa:**
- Chạm-giữ rồi ngón ra khỏi khung nút (dung sai ~12 px) là huỷ ngay, không gửi gì, nhãn trở về.
- Bộ kiểm dùng touch CDP như trên cho `drop`, `escape` và `quit`.

Hướng sửa: `releasePointerCapture(e.pointerId)` ngay trong `pointerdown` để `pointerleave` bắn đúng lúc, **và**
so toạ độ trong `pointermove` làm lưới thứ hai.

### TB-02 · P1 — Giữ ± gas/gió/trống rồi trượt ngón ra: vẫn tự lặp và GHI xuống máy

**Bằng chứng:**
- Giữ Gas − 0,7 giây (50 → 48), trượt 140 px ra ngoài, ngón vẫn đè.
- 1 giây sau gas còn **21%**; đã ghi 3 lệnh gas **49 / 36 / 21**.
- Cùng thao tác bằng chuột: dừng ở 48.

**Nguyên nhân:** như TB-01 (nút ± ở `.outrow .pm` dừng bằng `pointerleave`).

**Tác động:** gas/gió tụt hoặc leo tiếp tới khi nhấc tay. Thợ không thấy vì mắt không nhìn nút.

**Chấp nhận sửa:**
- Ngón ra khỏi nút là dừng lặp và chốt giá trị tại lúc ra.
- Áp cho **mọi** nút giữ-lặp: ± màn Rang, ± hộp Sửa hồ sơ, ± Cài đặt.
- Bộ kiểm touch CDP cho từng loại.

### TB-03 · P1 — "Tạm dừng" khi đang nối máy không dừng gì, nhưng nhìn như đã dừng

**Bằng chứng:**
- Đang rang 3:00, chạm Tạm dừng → nút đổi màu nhấn, nhãn vẫn "Tạm dừng".
- Máy chạy tiếp 20 giây: đồng hồ app 3:00 → 3:20, đường cong vẫn vẽ, gas giữ nguyên.
- Không lệnh nào gửi xuống máy. Nhật ký thao tác vẫn ghi "MẺ · tạm dừng".

**Nguyên nhân:** `R.paused` chỉ được đọc trong `roastTick()`, mà hàm này đã `return` ngay khi `dsLive()`.

**Tác động:**
- Thợ tưởng mẻ/lửa đã dừng → rời máy hoặc chờ.
- Nhật ký ghi một việc không xảy ra.
- Nút chiếm một ô lớn ở thanh đáy, ngay cạnh "Làm nguội".

**Chấp nhận sửa:** chủ máy chọn một trong ba:
- (a) nối máy thì **ẩn/khoá nút** kèm dòng giải thích — đề xuất;
- (b) biến thành lệnh "giữ nhiệt" thật — cần firmware;
- (c) chỉ giữ ở chế độ mô phỏng.

Dù chọn gì, nhật ký không được ghi "tạm dừng" khi máy không dừng.

### TB-04 · P2 — Mẻ chốt theo cờ CỬA XẢ không ghi mốc DROP

**Bằng chứng** (chuỗi sát firmware thật — `progStep` không bao giờ bằng 10):

| Kịch bản | Pha | `R.mileT.DROP` | `mile.DROP` gửi SQLite | Ô DROP tổng kết |
|---|---|---|---|---|
| C. Máy báo cờ drop lúc step 9, sau đó step 11 | DONE | trống | **thiếu** | "—" |
| D. App ra lệnh xả, máy báo cờ drop, rồi step 11 | DONE | trống | **thiếu** | "—" |
| B. HMI xả, step nhảy thẳng 11, không cờ | DONE | 562 s · 204° | có | 09:22 |

**Nguyên nhân:** hai đường chốt theo cờ — `autoDrop()` nhánh "máy báo cửa xả đã mở sẵn" và `dropPendingCheck()`
— gọi thẳng `finishRoast()`. Chỉ nhánh "máy rời dải progStep" mới tự điền `mileT.DROP`.

**Tác động:**
- Tổng kết thiếu mốc xả.
- Kho mẻ thiếu DROP trong `mile` → so mẻ nền, "Lấy mốc theo mẻ nền", API/MCP đọc curve đều hụt.
- `drop_sec` vẫn lưu đúng nên tổng thời gian không sai.

**Chấp nhận sửa:** mẻ không gián đoạn thì `finishRoast()` tự điền `mileT.DROP = dropSec`, `mileD.DROP = dropT` nếu
còn trống. Bộ kiểm cho cả C, D, B.

### TB-05 · P2 — Tablet: chữ và vùng chạm quá nhỏ

Sân khấu cố định 2560 px thu còn 0,5 (1280×720) / 0,53 (1366×768) lần.

**Vùng chạm < 44 px — 20 chỗ trên màn Rang đang chạy:**
- 6 tab trên cùng cao 40 px;
- 5 nút chú giải đồ thị cao 17 px;
- "Thao tác" 54×22 px;
- hàng "🌡 Nạp hạt tại … chạm để đổi" và "⚙ Công thức nạp" cao 22 px;
- 6 nút thiết bị phụ cao 40 px;
- nút mức nhanh gió/trống (60%, 55%) cao 39 px;
- gợi ý **"lần trước 28% · chạm để áp" chỉ 105×11 px** dù là nút bấm được.

Nút ± gas 46 px là đạt.

**Chữ < 13 px — 57 nhãn**, ví dụ:
- dải mốc TP/DE/FCs 8,5 px;
- "dự kiến", "54%" trong dải pha 8 px;
- "Rang vừa" 8 px;
- chú giải 9 px;
- "Nhiệt hạt · BT", "°C/phút" 10 px;
- "xả 210°C" 8,5 px.

Đối chứng 1920×1080: chỉ 6 vùng nhỏ (chú giải 25 px, Thao tác 32 px).

### TB-06 · P2 — Thanh đầu ở 1280×720 lúc đang rang: đồng hồ đè chữ trạng thái máy

Viên "Máy rang · trực tiếp" (`#linkLbl`) và đồng hồ (`#clock`) chồng nhau 33×16 px, đọc thành "trực 14:08". Lúc
đó thanh đầu có thêm băng lệnh "Nạp hạt = 1 · Trạng thái máy đã khớp" chiếm chỗ. 1920×1080 không chồng.

### TB-07 · P3 — Toast ở pha DONE đè logo và tab "Tổng quan"

Luật `#stage:has(#pane-rang.on[data-phase="DONE"]) #toast{top:26px;left:26px}` (vá đợt 12 cho khỏi che nút tổng
kết) nay đặt "Đã lưu curve vào hồ sơ …" lên đúng thanh tab trong ~2 giây.

### TB-08 · P3 — Chuột + bàn phím chưa được coi là cách điều khiển

- Không có phím tắt nào ngoài Esc/F11 (bật tắt toàn màn). **Esc khi không có hộp nào mở là thoát toàn màn** —
  thợ quen bấm Esc để "đóng" tổng kết sẽ bị thu cửa sổ.
- Thứ tự Tab phụ thuộc tiêu điểm trước đó. Một lượt đo, Tab đầu tiên rơi vào **"Kết thúc mẻ"** (nút nguy hiểm
  nhất); lượt khác vào ô gas. Tab thứ ba có lúc rơi về `body`.
- Không lăn chuột trên ô gas/gió/trống để chỉnh; không có ↑/↓ khi ô đang có tiêu điểm.
- Viền tiêu điểm có (2 px) — đạt.

## Kế hoạch nâng cấp chi tiết

Thứ tự theo rủi ro. Mỗi đợt: nhận khoá UI-LOCK, sao lưu, bộ kiểm mới, chạy lại 32 bộ `test_ui_*`, build EXE,
so md5.

### Đợt A — An toàn cảm ứng (làm ngay, trước khi đưa tablet vào xưởng)

| Việc | Nội dung | Nghiệm thu |
|---|---|---|
| A1 | TB-01: nút giữ-xác-nhận huỷ khi ngón ra khỏi nút (`releasePointerCapture` + so toạ độ `pointermove`) | Touch CDP trượt ra: 0 lệnh `drop`/`escape`/thoát app; giữ đúng chỗ vẫn phát |
| A2 | TB-02: cùng cơ chế cho mọi nút giữ-lặp (Rang, Sửa hồ sơ, Cài đặt) | Trượt ra: số dừng tại lúc ra, 0 lệnh ghi thêm |
| A3 | Bộ kiểm `tools/test_ui_touch_real.py` dùng touch CDP (không pointer tổng hợp) cho A1, A2, cả hai ngón | Gỡ bản vá ra phải đỏ (chứng minh không vô dụng) |
| A4 | TB-03 theo lựa chọn của chủ máy (đề xuất: nối máy thì khoá nút + dòng "Máy đang lái mẻ — dừng trên HMI") | Không còn trạng thái "đã tạm dừng" giả; nhật ký không ghi sai |
| A5 | TB-04: `finishRoast()` điền mốc DROP khi còn trống | Kịch bản B/C/D đều có DROP trong tổng kết + `mile` |

### Đợt B — Mật độ tablet

Ràng buộc: `#stage` cố định 2560 px → không dùng media query. Dùng một lớp mật độ, ví dụ
`html[data-density="tablet"]`: tự bật khi tỉ lệ sân khấu < 0,6, chọn tay được trong Cá nhân hóa.

| Việc | Nội dung | Nghiệm thu |
|---|---|---|
| B1 | Sàn cỡ chữ thật 12 px cho nhãn phụ (dải mốc, dải pha, chú giải, đơn vị) — tăng token, không đổi bố cục khung | 1280×720@1,5: ≤ 5 nhãn < 12 px trên màn Rang |
| B2 | Vùng chạm ≥ 44 px thật: tab, chú giải (bấm cả dòng), hàng Nạp hạt/Công thức, gợi ý "lần trước", thiết bị phụ, mức nhanh | 0 phần tử bấm được < 44 px trong vùng điều khiển |
| B3 | Thanh đầu: nhãn kết nối rút gọn ("Trực tiếp"), băng lệnh co/ẩn khi hẹp, đồng hồ không bao giờ đè (TB-06) | Đo giao nhau = 0 ở 1280×720, 1366×768, 1920×1080 |
| B4 | Toast pha DONE đặt trong khung tổng kết, không lên thanh tab (TB-07) | Toast không giao tab/nút nào |
| B5 | Thêm 1280×720@1,5 vào `test_ui_overlap.py` | ĐẠT cả 3 cỡ |

### Đợt C — Chuột và bàn phím cho máy trạm

| Việc | Nội dung | Nghiệm thu |
|---|---|---|
| C1 | Lăn chuột trên ô gas/gió/trống = ±1 (hãm nhịp ghi như nút ±); ↑/↓ khi ô có tiêu điểm | Lăn 10 nấc → máy nhận ≤ 1 lệnh/giây, giá trị cuối đúng |
| C2 | Esc không thoát toàn màn khi đang rang/DONE; thoát toàn màn chỉ còn F11 | Esc lúc tổng kết không đổi kích thước cửa sổ |
| C3 | Thứ tự Tab màn Rang cố định: gas → gió → trống → Ghi mốc → Làm nguội → (cuối) Xả liệu / Kết thúc mẻ | Tab đầu tiên không bao giờ vào nút nguy hiểm |
| C4 | (Chờ chủ máy) Phím tắt: `M` ghi mốc, `?` bảng phím; KHÔNG có phím tắt một chạm cho xả/kết thúc — chỉ giữ phím | Không phím nào phát lệnh cơ cấu nếu không giữ đủ `HOLD_MS` |

### Đợt D — Tinh tế

| Việc | Nội dung |
|---|---|
| D1 | Thử cảm giác chuột/chạm trên **app thật WebView2** trên tablet xưởng (lần này chủ máy chưa cho chiếm chuột) |
| D2 | Gợi ý "lần trước 28% · chạm để áp" thành nút rõ ràng (chip), vì đây là tính năng hay mà gần như vô hình |
| D3 | 4 quyết định còn treo từ đợt 12: tự xả mặc định bật/tắt; ước % phát triển ~9–10% khi hồ sơ trống; dòng "Tăng nhiệt +54 °C/phút" lúc làm nóng; vị trí bong bóng Hồng |

## Đã sửa — đợt 15 (14/09/2026 tối, chủ máy: "sửa đi, và build… sửa cho xong luôn")

Tạm dừng dùng phương án (a).

| Mục | Đã sửa |
|---|---|
| TB-01 | `holdGuard()`: trong `pointerdown` nhả *implicit capture* + lưới thứ hai so toạ độ `pointermove` (ra khỏi khung nút quá 12 px thật = huỷ). Áp cho `holdBind` (Xả liệu, Kết thúc mẻ, Thoát app). |
| TB-02 | Cùng `holdGuard()` cho ± màn Rang (ngón ra là dừng lặp, chốt giá trị lúc ra) và ± hộp Sửa hồ sơ. |
| TB-03 | Nối máy: `togglePause()` không đổi trạng thái, không ghi nhật ký, toast giải thích; nút mờ + dòng phụ "máy đang lái mẻ". Mô phỏng vẫn dừng như cũ. Trợ giúp nút ghi rõ. |
| TB-04 | `finishRoast()` chấm DROP = giây xả + nhiệt xả nếu còn trống (mẻ không gián đoạn) → tổng kết và `mile` gửi kho đủ DROP ở cả 3 kiểu xả. |
| TB-05 | `fit()` gắn `html[data-density="tablet"]` khi tỉ lệ sân khấu < 0,62, kèm `--read-floor` (12 px thật) và `--hit-min` (44 px thật). Khối CSS cuối: sàn chữ `max(cỡ thiết kế, sàn)` cho 9 nhóm, chỉ kiểu Chi tiết (1920 và kiểu Đơn giản không đổi); vùng chạm `::after` trong suốt cho tab, chú giải, "Thao tác", hàng Nạp hạt, gợi ý "lần trước", thiết bị phụ, ô số, nút tổng kết — không đổi bố cục. Còn lại < 11,5 px: 3 biểu tượng thanh đầu (🔓, chữ cái avatar, ▾). |
| TB-06 | Viên trạng thái máy + băng lệnh co được và cắt "…", đồng hồ không co; tablet ẩn nhãn vai trò dưới tên. |
| TB-07 | Toast pha DONE nằm nửa trái, trên dải pha. |
| TB-08 | Lăn chuột / ↑↓ trên ô gas-gió-trống (≤ 1 lệnh/giây, ngừng tay 0,35 s là chốt); Esc lúc đang rang / tổng kết không thu toàn màn (F11 vẫn được); phím **M** = Ghi mốc. Không có phím tắt nào cho nạp/xả/kết thúc mẻ. |

Không làm:
- **C3** — đo lại thì Tab đầu tiên theo điểm bắt đầu tiêu điểm của trình duyệt (chỗ vừa chạm), không phải thứ tự DOM sai.
- **D1** — cần tablet thật.
- **D3** — 4 quyết định vận hành cũ vẫn chờ chủ máy.

**Kiểm và build:**
- Bộ kiểm mới `tools/test_ui_touch_real.py`: 9 mục, cảm ứng CDP thật. Chạy trên bản sao lưu trước sửa thì ĐỎ đúng
  các lỗi TB-01/02.
- Toàn bộ **33/33** `tools/test_ui_*.py` ĐẠT.
- Soi ảnh tablet phát hiện thêm: chữ to đẩy "Về Tổng quan · Mẻ mới" khuất khỏi bảng tổng kết. `test_ui_overlap` bỏ
  qua phần tử trong khung cuộn nên không bắt → đã giữ 5 ô mốc một hàng + bỏ đường cong mini trên tablet, và thêm
  phép kiểm vào bộ mới.
- Build `tools/dist/OTL Roast Lab HMI.exe` — md5 HTML nhúng `19eadc94…` khớp bản trên đĩa. Chưa commit.

## Còn chờ chủ máy

1. Thử trên tablet thật (D1): trượt ngón khỏi nút giữ, cỡ chữ màn Rang.
2. Bốn quyết định cũ (D3).

## Tái lập

Script ở scratchpad phiên Claude 14/09 — viết lại theo mô tả:
- Playwright `new_context(has_touch=True, device_scale_factor=1.5, viewport 1280×720)`;
- nạp stub + `feed()` từ `tools/test_ui_review_0914.py`;
- ngón thật bằng `cdp.send("Input.dispatchTouchEvent", …)` (`touchStart` / `touchMove` / `touchEnd`);
- đếm `window.__sent`.
