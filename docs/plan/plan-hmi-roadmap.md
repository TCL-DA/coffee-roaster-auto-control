# Lộ trình OTL Roast Lab HMI — LÀM GÌ, THỨ TỰ NÀO

> **File mở hằng ngày khi code.** Đây là bản đồ ưu tiên; **chi tiết thiết kế** từng
> mục ở `docs/ref/ref-roast-lab-hmi-architecture.md` (các "§X" bên dưới trỏ tới file
> đó). Quy trình rang gốc (firmware) ở `docs/ref/ref-roast-process-firmware.md`.
>
> Cập nhật: 2026-07-14.

---

## 0. Bối cảnh vận hành — LA BÀN cho mọi quyết định

> **Đây KHÔNG phải app demo.** Nó nối **máy rang cà phê thật**, chạy **~16h/ngày,
> mỗi ngày**, là **công cụ sản xuất** của thợ rang chuyên nghiệp. Mọi đánh đổi thiết
> kế phải bám thực tế này, không bám giả định "sim rồi nối máy sau".

**Thực tế xưởng (con số để thiết kế):**
- **~40–60 mẻ/ngày** (mẻ ~15–18′ gồm rang + xoay vòng) → **12.000–18.000 mẻ/năm**.
  Mỗi mẻ là **bản ghi kinh doanh** (QC, truy vết lô, công thức = IP).
- Môi trường: **nóng (cạnh burner gas), bụi trấu, khói, ẩm, nhiễu điện RS485** (gần
  biến tần). **Mất điện chớp nhoáng là cơm bữa** (máy rang là tải lớn).
- Người dùng: **thợ chuyên nghiệp lặp cùng thao tác ~60 lần/ngày**, có thể **nhiều
  ca**, đeo găng, tay bẩn, mỏi mắt cuối ca.

**Thứ tự ưu tiên ĐÚNG cho sản xuất 16h/ngày** (đảo lại so với bản cũ để-bảo-mật-trước):

1. **An toàn** — số hiển thị đáng tin (sensor sanity), clamp 2 tầng, firmware là chốt.
2. **Dữ liệu thời gian thực bền** — BT/ET/RoR ổn định, **auto-reconnect** (mất cáp/
   nhiễu là sự kiện thường ngày, KHÔNG bắt restart).
3. **Không mất mẻ nào** — ghi power-safe (WAL), **auto-backup hằng ngày**.
4. **Uptime 16h** — không rò bộ nhớ, watchdog + hồi phục **tính bằng giây**.
5. **Nhịp sản xuất** — workflow **tàn nhẫn ít chạm**, back-to-back preheat idle-warm.
6. **Ergonomics cả ngày** — đọc-từ-xa, tương phản cao chống lóa (theme `workshop`).
7. **RỒI MỚI** — bảo mật/license/đa theme/đa ngôn ngữ/stats (quan trọng để **bán
   cho người khác**, không phải để **chạy máy hằng ngày**).

> Hệ quả: "nối máy thật" **KHÔNG phải GĐ3** — nó là **GĐ1**. Sim chỉ là tiện ích lúc
> dev. Đầu tư lớn vào DPAPI/anti-piracy là mối quan tâm của OTL-người-bán, đừng để
> nó chặn đường ship cái **chạy được máy hằng ngày**.

---

## 1. Lộ trình các giai đoạn (SẢN XUẤT-FIRST)

| GĐ | Nội dung | Điều kiện xong |
|---|---|---|
| **1 — Chạy sản xuất thật** (dùng được hằng ngày) | `DataSource` thật + poll một-chủ-serial + **auto-reconnect** + **sensor sanity** + clamp 2 tầng + heartbeat + version handshake (§16.7, §16.9); **SQLite power-safe (WAL) + auto-backup ngày + không mất mẻ** (§16.2); **watchdog + soft-reload uptime** (§16.6); background profile + bảng DONE (§18.3, §18.5); workflow ít chạm; theme `workshop` + `vi` | **Rang thật 16h/ngày nhiều ngày: không sập, không mất mẻ, rút cáp/chớp điện tự hồi phục**; kill HMI giữa mẻ → firmware giữ an toàn |
| **2 — Bán cho người khác** (commercial hardening) | Auth về Python + DPAPI + per-call + installer elevated + lockout bền + audit hash-chain (§16.1, §16.3); migration từ localStorage; license Ed25519 + machine_id + ký số Authenticode (§16.4, §16.5); unit test (§16.8) | Xóa `%LOCALAPPDATA%` **không** chiếm được master; copy exe sang máy lạ → chế độ xem; cài trên Win sạch không cảnh báo SmartScreen |
| **3 — Mở rộng & trải nghiệm** | Stats/AUC (§18.7), so nhiều mẻ (§18.2), phase editor (§8.4), thư viện Preheat UI (§7.1), capability matrix UI (§9.2), thêm theme/ngôn ngữ (§4.2/4.3), alarm catalog đầy đủ + push (§19), **kho nhân LITE** (§3.1), cloud opt-in | Kích hoạt **theo tín hiệu thật** (khách yêu cầu / đơn xuất khẩu), không làm sẵn |
| **4 — Quản lý xưởng** (business layer, hướng Cropster) | Kho nhân · cupping · kế hoạch SX · chi phí/hao hụt/lợi nhuận — xem **§3** | **Quyết định chiến lược**: đổi loại sản phẩm; chỉ làm khi GĐ1 vững + nhắm phân khúc specialty |

> Lưu ý: các nhãn "GĐ 3" rải rác trong §13/§16.7 của doc kiến trúc (viết theo lộ
> trình cũ) nay hiểu là **GĐ1** — nối máy thật đã lên đầu. SQLite ở GĐ1 (để ghi mẻ
> power-safe), còn **hardening auth** ở GĐ2 (tiệm tự dùng không cần chống chính mình).

### 1.1 Những gì CỐ TÌNH không làm (tránh over-engineering)
- **Không** server/cloud bắt buộc — xưởng rang thường không có internet ổn định;
  cloud sync để mở sau như tính năng cộng thêm.
- **Không** đổi UI sang framework/bundler — 1 file HTML là lợi thế bảo trì. (Ngoại
  lệ được phép: `assemble.py` **nối văn bản** src→1 file lúc build — không
  transpile/minify/import nên KHÔNG phải bundler; ship vẫn đúng 1 file.)
- **Không** mã hóa toàn bộ database — DPAPI bọc pepper/key là đủ với mô hình đe
  dọa (người chạm được máy ở xưởng), mã hóa full DB gây rủi ro mất dữ liệu khách.
- **Không** DRM nặng/anti-debug — tốn công, phá trải nghiệm, không chặn được
  đối thủ quyết tâm; license ký số + khóa máy là mức đầu tư đúng.

---

## 2. Cut-line MVP GĐ1 — in / out (SẢN XUẤT-FIRST, một người ~2–3 tháng)

> **Mục tiêu GĐ1**: một cái **chạy được máy thật hằng ngày ở chính xưởng mình** —
> an toàn, dữ liệu tin cậy, không mất mẻ, không sập 16h. KHÔNG phải "đủ để bán".
> Bán cho người khác là GĐ2. Mọi mục ⭐ trong doc kiến trúc mặc định OUT trừ khi có
> tên trong bảng TRONG.

**TRONG MVP GĐ1** (chạy sản xuất thật):

| Nhóm | Làm | Chi tiết ở |
|---|---|---|
| **An toàn + dữ liệu thật** | `DataSource` thật + poll một-chủ-serial + auto-reconnect + sensor sanity + clamp 2 tầng + heartbeat + version handshake | §16.7, §16.9 |
| **Không mất mẻ** | SQLite **power-safe (WAL) + integrity_check + auto-backup ngày**; ghi mẻ + curve; export CSV | §16.2, §18.1 |
| **Uptime 16h** | watchdog + autostart + **soft-reload chống rò bộ nhớ** + checkpoint hồi phục | §16.6, §6 |
| **Rang lõi** | Thư viện Mục tiêu rang + nền mờ (background profile) + bảng DONE Thực tế/Mục tiêu | §8.3, §18.3, §18.5 |
| **Nhịp + đọc-từ-xa** | Workflow ít chạm; **back-to-back preheat idle-warm**; số live to; banner lỗi cơ bản + FAULT | §12, §7, §6, §19 |
| **Giao diện** | **1 theme `workshop`** làm cực tốt + **`vi`** | §4.2, §4.3 |

**GĐ2 — bán cho người khác** (không cần cho xưởng mình): auth về Python + DPAPI +
per-call + installer elevated + lockout bền + audit hash-chain (§16.1/§16.3);
license Ed25519 + ký số (§16.4/16.5); migration localStorage; unit test (§16.8).

**GĐ3 — mở rộng theo tín hiệu thật:**

| Tính năng | Chỉ làm khi | Chi tiết ở |
|---|---|---|
| Stats/AUC · so nhiều mẻ | Khách/mình cần phân tích sâu | §18.7, §18.2 |
| Phase editor · Preheat UI ≤6 · capability matrix UI | Đã chạy ổn, muốn tinh chỉnh sâu | §8.4, §7.1, §9.2 |
| Alarm catalog ~380 mã + push Telegram/Zalo | Cần giám sát từ xa (GĐ1 chỉ cần banner + FAULT) | §19 |
| Thêm theme · zh/th/fr/it/pt | Khách cần / có đơn xuất khẩu (dịch = cam kết bảo trì) | §4.2, §4.3 |
| **Kho nhân LITE** (lô đang mở + trừ tự động bằng cân + còn-lại-theo-mẻ) | Có cân/loader; mồi dẫn sang chi phí/hao hụt | §3.1 |

**Nguyên tắc backlog**: kiến trúc **chừa sẵn chỗ** (slot i18n, lớp vẽ chung, khuôn
overlay, `DataSource`) để bật sau **không phải viết lại** — nhưng **không ship code
chết**. GĐ1 xong = **rang thật cả tuần không sự cố** trước khi nghĩ tới GĐ2/3.

---

## 3. GĐ4 — Quản lý xưởng (business layer, hướng Cropster)

> ⚠️ **Quyết định chiến lược, không phải tính năng thường.** 4 mục dưới **đổi loại
> sản phẩm**: từ "HMI lái máy" → "phần mềm quản lý xưởng rang" — cạnh tranh **trực
> diện với lõi giá trị của Cropster**. Cam kết lớn (mỗi mục ~cỡ một module), cần
> **model dữ liệu kinh doanh** riêng + có thể cần đồng bộ nhiều máy. Chỉ làm sau khi
> GĐ1 (máy chạy tin cậy) đã vững. Có thể là **sản phẩm/gói bán riêng**.

| # | Tính năng | Nội dung cốt lõi | Ghi chú |
|---|---|---|---|
| 42 | **Quản lý kho cà phê nhân (FULL)** | Phần nặng: **blend nhiều lô/mẻ**, đa kho/đa vị trí, giá vốn gồm vận chuyển, gắn vào chi phí (#45). Phần LITE tách lên **GĐ3** (xem §3.1) | Chi tiết + 6 cải thiện ở **§3.1** |
| 43 | **Cupping / chấm điểm cảm quan** | Tầng 1 (Nếm QC nhanh) trên panel + Tầng 2 (SCA đầy đủ) là **companion app**; **nối rang↔cup**. Chi tiết + 6 cải thiện ở **§3.2** | Mục "lệch máy" nhất — dẫn bằng link rang↔cup |
| 44 | **Kế hoạch sản xuất** | Lịch mẻ theo đơn hàng; **số mẻ cần rang/ngày**; gán hồ sơ + lô nhân cho từng mẻ; theo dõi tiến độ (đã rang / còn lại) | Dùng `loop_R` + lịch sử mẻ đã có |
| 45 | **Chi phí · hao hụt · lợi nhuận/mẻ** | **Shrinkage** = (KL vào − KL ra)/vào (dùng cân §scale + BT_DROP); **giá thành** = nhân + gas + nhân công; **lợi nhuận** theo giá bán | Cần dữ liệu kho (#42) + cân thật |

**Điều kiện tiên quyết chung** (khác hẳn GĐ1–3):
- **Model dữ liệu kinh doanh** mới: `lots` (lô nhân), `cuppings`, `orders`,
  `costs` — bảng SQLite riêng, quan hệ với `batches` (§18.1).
- **Nhập liệu nhiều** (kho/đơn/giá) — bàn phím ảo hiện tại đủ nhưng cực; cân nhắc
  nhập từ PC/web phụ trợ, không gõ hết trên panel cảm ứng nóng-bụi.
- **Đồng bộ** (nếu nhiều máy/nhiều người): đây là chỗ **cloud opt-in** trở nên có
  giá trị thật — ngược với triết lý offline của GĐ1. Cần cân nhắc kỹ.

> **Khuyến nghị**: GĐ4 nên là **quyết định riêng sau khi bán được GĐ1–2**. Nếu
> khách chủ lực là xưởng nhỏ VN "chỉ cần máy chạy tốt", GĐ4 là thừa; nếu nhắm xưởng
> specialty muốn thay Cropster, GĐ4 là **cả một sản phẩm thứ hai** — định giá &
> nguồn lực tương xứng.

### 3.1 Chi tiết #42 — Quản lý kho cà phê nhân

**Bẫy của spec một dòng** ("nhập lô → trừ theo mẻ → cảnh báo → truy vết"):
- **Trừ kho bằng số danh định = lệch dần**: mẻ "6kg" thực nạp 5.8–6.2kg; sau
  ~60 mẻ/ngày sổ lệch cả chục kg/tuần → mất niềm tin → bỏ dùng (lý do #1 hệ thống
  kho chết ở xưởng nhỏ).
- **Chọn lô mỗi mẻ = +1 chạm × 60 lần/ngày** → vi phạm "tàn nhẫn ít chạm" (§0) →
  thợ chọn bừa/bỏ qua → dữ liệu truy vết rác.
- **Cảnh báo "còn 45kg"**: thợ nghĩ bằng **mẻ**, không bằng kg.
- **Chỉ lưu số dư, không lưu biến động** → không kiểm kho được.

**6 cải thiện (xếp theo giá trị):**

| # | Cải thiện | Cốt lõi |
|---|---|---|
| 1 | **Trừ kho bằng CÂN THẬT, tự động** | Máy đã có đầu cân BT (`netW`, ×100). Auto-loader cân mỗi lần nạp → trừ đúng kg đã cân, **0 thao tác**. Không cân → fallback `MACHINE_BATCH_KG` + sửa tay. **Lợi thế Cropster không có**: cân nằm trong máy |
| 2 | **"Lô đang mở" thay vì chọn lô mỗi mẻ** | Gán lô cho phễu **một lần** khi đổ bao; mọi mẻ sau tự ghi lô đó tới khi đổi lô. 60 mẻ = 1 thao tác |
| 3 | **Nói bằng MẺ, không bằng kg** | "Lô  #7: **còn ~7 mẻ**" (tồn ÷ batch kg). Cảnh báo "còn 2 mẻ" lúc **đầu ca**, không giữa mẻ |
| 4 | **Sổ biến động (ledger)** | Bảng `lot_movements`: nhập / trừ-theo-mẻ / **điều chỉnh kiểm kho** (lý do + audit). Số dư = tổng ledger. Kiểm kho chỉnh lệch (rơi vãi, bay ẩm) không phá lịch sử |
| 5 | **Nhập theo BAO** | "20 bao × 60kg" (đơn vị kho VN) → app quy ra kg. Bắt buộc chỉ **Tên + khối lượng**; nông trại/giống/giá/độ ẩm tùy chọn. Nhập ~1 lần/tuần → panel đủ |
| 6 | **FIFO + tuổi lô** | Thẻ lô hiện tuổi (ngày nhập→nay), gợi ý dùng lô cũ trước; cảnh báo nhân >12 tháng |

**Truy vết 2 chiều** (giá trị bán hàng cho khách sỉ): khách khiếu nại mẻ #B-0212 →
ra lô → ra **mọi mẻ cùng lô** (một chạm).

**Tách LITE (→ GĐ3) vs FULL (→ GĐ4):**
- **Kho LITE** = cải thiện #1 + #2 + #3 + ledger tối thiểu (#4). **Rất nhỏ** vì
  cân + loader đã có sẵn trong firmware → **đưa lên GĐ3**, làm mồi dẫn sang #45
  (hao hụt/giá thành).
- **Kho FULL** = blend nhiều lô, đa kho, giá vốn phức tạp → giữ ở **GĐ4** (#42).

### 3.2 Chi tiết #43 — Cupping / chấm điểm cảm quan

**Vì sao spec một dòng sai chỗ** (mục "lệch máy" nhất trong GĐ4):
- **Cupping KHÔNG ở máy, không lúc rang**: cà phê nghỉ/thải khí **12–24h+** rồi mới
  cup, ở **bàn cupping** phòng khác. Panel nóng-bụi-chói cạnh lò là **sai thiết bị**.
- **Cupping thường MÙ + NHIỀU người** chấm độc lập rồi hiệu chỉnh — không phải
  "1 điểm/1 mẻ bởi 1 người ở máy".
- **Chấm cái gì**: thường là **lô** (mua nhân) / **phiên bản hồ sơ** (dev) / **QC
  spot-check mẻ** — không cứng "theo mẻ".
- **Điểm ≠ một số**: là mô tả hương vị + lỗi; **mô tả quan trọng hơn số** cho marketing.
- **Đa số xưởng VN không cup kiểu SCA** đủ 10 thuộc tính → ép form đầy đủ = không ai dùng.

**6 cải thiện:**

| # | Cải thiện | Cốt lõi |
|---|---|---|
| 1 | **Nhập ở thiết bị khác, panel chỉ HIỆN** | Form chấm trên **điện thoại/tablet/web companion**; panel máy hiển thị điểm + note. Ca rõ nhất cho thấy business-layer cần input ngoài panel |
| 2 | **Hai tầng** | **Tầng 1 (mặc định)**: sao ⭐ + check lỗi + 1 note — nhanh, spot-check hằng ngày. **Tầng 2 (tùy chọn)**: SCA 10 thuộc tính /100 cho đánh giá nhân/dev. Không ép tầng 2 |
| 3 | **Gắn LINH HOẠT** | Chấm vào **lô** (#42) / **phiên bản hồ sơ** (§8.3) / **mẻ** (§18) — không cứng theo mẻ |
| 4 | **Từ vựng MÔ TẢ hương vị** | Bộ tag (flavor wheel gọn: trái cây/chocolate/hạt/hoa/caramel) + note tự do → dùng cho bao bì/marketing |
| 5 | **⭐ Nối RANG↔CUP (killer)** | Gắn điểm/note với **curve + phase stats** (DTR, dev%, RoR) → học "hồ sơ nào cho vị nào". **Lợi thế DUY NHẤT của OTL**: sở hữu sẵn curve (Cropster phải nhập từ ngoài) |
| 6 | **Phiên mù + đa người** (tầng 2) | Mã mẫu ẩn, nhiều người chấm, tổng hợp + độ lệch. Chỉ cho ai cup thật |

**Quy tắc nghỉ**: nhắc "mẻ #B-0212 sẵn sàng cup sau 12–24h" (tính từ giờ DROP) —
**không cho cup mẻ còn tươi** (kết quả sai).

**Để sau (đừng làm)**: CSDL cupping cộng đồng / chứng chỉ Q-grader / hiệu chỉnh
scorer chuẩn SCA — đó là hệ sinh thái Cropster, không phải việc của HMI máy.

**Chiến lược**: cupping là mục **yếu nhất để nhét vào HMI**. Nếu làm, **đừng đua form
SCA với Cropster** — dẫn bằng **#5 (nối rang↔cup)**, chỗ duy nhất OTL mạnh hơn. Khuyến
nghị: **GĐ4 chỉ làm Tầng 1 (nếm QC nhanh) + link rang↔cup**; cupping SCA đầy đủ là
**companion app riêng**, không phải tính năng panel.

---

## Liên quan
- `docs/ref/ref-roast-lab-hmi-architecture.md` — chi tiết thiết kế (các "§X" ở trên).
- `docs/ref/ref-roast-process-firmware.md` — quy trình rang gốc (firmware) HMI phản chiếu.
