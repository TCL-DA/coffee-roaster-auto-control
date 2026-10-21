# Kế hoạch: API v1 · MCP server · Extension cho app OTL Roast Lab

**Mục tiêu cuối:** cho AI đọc, phân tích và (có điều kiện) điều khiển app Roast Lab.
**Ngày lập:** 2026-09-06 · Nối tiếp mục 7 và 10 của [plan-roadmap-quocte-ai.md](plan-roadmap-quocte-ai.md).

---

## 0. Điều phải nói trước

App này không điều khiển một trang web. Nó điều khiển **một cái bếp gas đang cháy**, có
xi-lanh khí nén đóng mở cửa nạp và cửa xả, và một trống quay chứa 15–30 kg hạt ở 200 °C.

Khác biệt giữa "thợ lái app" và "AI lái app" không nằm ở chỗ ai bấm nút, mà ở chỗ:
**thợ đứng cạnh máy, AI thì không**. Thợ thấy khói, nghe tiếng nổ hạt, ngửi mùi khét, và
tay chạm được nút dừng. AI mất mạng thì im lặng, và máy không biết là nó đã im.

Vì vậy toàn bộ kế hoạch này xoay quanh một câu hỏi duy nhất:
**khi phía điều khiển biến mất, máy tự về trạng thái an toàn hay đứng nguyên đó mà cháy?**

---

## 1. Chốt chặn số 1 — watchdog ~~đang TẮT~~ ĐÃ BẬT THEO TẦNG (2026-09-06)

```c
// include/Config.h — nay là 1: siết 3 giây, nhưng CHỈ với tác nhân tự động
#define PCL_APP_WATCHDOG_EN               1
```

> **Cập nhật 2026-09-07.** Bật cờ này chưa đủ: app vẫn nhấp heartbeat vô điều kiện
> mỗi chu kỳ poll, nên firmware chỉ biết *app* còn sống chứ không biết *AI* đã treo.
> Đã vá ở `otl_link._hb_cho_phep()` — có lượt lái đang mở mà tác nhân im quá 20 giây
> (hoặc hết hạn lượt) thì app **ngừng nhấp**, firmware nhả quyền trong 3 giây.
> Dây chuyền nối liền từ AI xuống tới van gas, không đứt khúc nào.

Firmware **có sẵn** watchdog: app phải nhấp `PCL_W_HB` mỗi giây, im quá `PCL_APP_TMO_S = 3`
giây thì firmware tự nhả quyền PC control về HMI và kêu còi. Nhưng nó đang bị tắt theo lệnh
chủ máy trước đây (xem `project_pc_link`) — lý do chính đáng ở thời điểm đó: thợ lái app,
đứng ngay cạnh máy, watchdog nhả quyền giữa mẻ gây khó chịu hơn là giúp.

**Với AI thì lý do đó không còn đúng.** Đây là việc bắt buộc phải làm trước mọi thứ khác:

- `PCL_APP_WATCHDOG_EN = 1` khi có bất kỳ tác nhân tự động nào ghi vào máy.
- Cân nhắc để watchdog **theo tầng quyền**, không phải bật/tắt toàn cục: thợ lái tay thì
  nới (hoặc tắt), AI lái thì siết 3 giây. Firmware phân biệt được vì tầng quyền do
  chính firmware cấp (xem §4).

Chốt chặn thứ hai — **mồi hụt** (`PCL_FLAME_TMO_S`, bật gas mà không có `gasSignal` thì đóng
gas) — hiện **đang bật**, giữ nguyên.

Chốt chặn thứ ba đã làm xong hôm nay: firmware tự kiểm dải 52 tham số `$M` và khoá ghi khi
máy bận (xem `project_pclink_cfg_hardening`). Nguyên tắc đó phải áp cho cả khối lệnh, không
riêng khối cấu hình.

---

## 2. Hiện trạng — đã có nhiều hơn ta tưởng

Không phải xây API mới. Đã có sẵn:

| Thứ | Ở đâu | Trạng thái |
|---|---|---|
| ~40 endpoint HTTP | `tools/roast_lab_hmi.py`, `start_webserver()` | chạy thật, cổng 8555 |
| Token phiên 12 giờ | `api.web_tokens`, `_tok_ok()` | có, nhưng yếu (xem §3) |
| Đẩy sự kiện realtime | `/api/stream` (SSE) + `BUS` | chạy thật |
| 22 lệnh ghi có dải | `protocol/pc_link.json` → `otl_link.write()` | có min/max, có kiểu level/latch |
| Bản đồ thanh ghi 1 nguồn | `protocol/pc_link.json` + `gen_pc_link.py` | sinh cho firmware/Python/JS, có `--check` |
| Lớp cầu Modbus | `tools/otl_link.py` (`RoasterLink`) | tự dò cổng, tự nối lại |
| Nhật ký vận hành | `op_log` / `op_tail` | có |

`gen_pc_link.py` là tài sản lớn nhất ở đây: bản đồ lệnh đã là **một nguồn sự thật duy nhất**
sinh ra cho 3 phía. MCP và OpenAPI phải sinh từ chính file đó, tuyệt đối không chép tay.

---

## 3. Lỗ bảo mật phải vá trước khi mở rộng

Mở API cho AI = nhân bội bề mặt tấn công. Ba thứ sau đang là lỗ thật, đã kiểm chứng bằng code:

1. **`GET` không cần xác thực gì cả.** `/api/snapshot`, `/api/profiles`, `/api/batches`,
   `/api/inv_lots`, `/api/inv_orders`, `/api/inv_cost` đều trả tự do. Server bind
   `0.0.0.0:8555`. Ai vào được WiFi xưởng là đọc được trạng thái máy **và toàn bộ dữ liệu
   kinh doanh**: lô nhân, đơn hàng, giá vốn, lãi gộp.
2. **PIN web mặc định ghi cứng `1108`** (`web_cfg.get("pin", "1108")`) — trùng luôn PIN
   master dùng để test.
3. **Token đi trong thân JSON, không HTTPS, không giới hạn tần suất.** Trên LAN là chữ thường.

Ba thứ này phải xong trước GĐ B. Không thương lượng.

---

## 4. Kiến trúc — 4 lớp, mỗi lớp một trách nhiệm

```
┌──────────────────────────────────────────────────────────┐
│  AI (Claude / trợ lý khác)                               │
└───────────────┬──────────────────────────────────────────┘
                │ MCP (stdio hoặc HTTP)
┌───────────────▼──────────────────────────────────────────┐
│  LỚP 3 — MCP server        tools/mcp_roaster/            │
│  Công cụ chia 3 tầng · mọi từ chối phải nói RÕ LÝ DO     │
└───────────────┬──────────────────────────────────────────┘
                │ HTTP, Bearer token có phạm vi
┌───────────────▼──────────────────────────────────────────┐
│  LỚP 2 — API v1            /api/v1/…                     │
│  Xác thực · phạm vi quyền · lease · giới hạn tần suất    │
│  · nhật ký bất biến. ĐÂY là nơi giữ luật, không phải MCP │
└───────────────┬──────────────────────────────────────────┘
                │ gọi thẳng lớp Api sẵn có
┌───────────────▼──────────────────────────────────────────┐
│  LỚP 1 — Api + RoasterLink (đã có)                       │
│  Quy đổi đơn vị · dải · Modbus · SQLite                  │
└───────────────┬──────────────────────────────────────────┘
                │ Modbus RTU (PC_Link)
┌───────────────▼──────────────────────────────────────────┐
│  LỚP 0 — FIRMWARE STM32 — quyền phủ quyết cuối cùng      │
│  watchdog · mồi hụt · kiểm dải · khoá khi máy bận        │
│  KHÔNG TIN bất cứ thứ gì ở trên                          │
└──────────────────────────────────────────────────────────┘
```

**Nguyên tắc xuyên suốt:** luật an toàn nằm ở **lớp 0 và lớp 2**, không nằm ở lớp 3.
MCP server chỉ là bộ chuyển ngữ. Ai đó viết một MCP server khác, hay gọi thẳng HTTP bằng
`curl`, thì vẫn phải đi qua đúng bấy nhiêu luật. Luật đặt ở lớp AI là luật tự nguyện — vô nghĩa.

---

## 5. Mô hình quyền — 3 tầng

| Tầng | Làm được gì | Điều kiện |
|---|---|---|
| **T0 · ĐỌC** | trạng thái máy, hồ sơ, lịch sử mẻ, đường cong, kho | API key có phạm vi `read`. Mặc định cho AI. |
| **T1 · ĐẶT** | 52 tham số `$M`, cấu hình, hồ sơ, kho/đơn | Máy **rảnh** (firmware đã tự khoá). Ghi nhật ký. Hoàn tác được. |
| **T2 · LÁI** | gas · gió · trống · nạp · xả · mồi lửa · auto | Toàn bộ 5 điều kiện ở dưới. |

**Năm điều kiện của T2 — thiếu một là từ chối:**

1. **Thợ bật bằng tay** một công tắc "cho phép AI lái" **ngay trên app**, không bật được từ xa.
2. **Lease có hạn** — cấp tối đa 15 phút, hết thì tự rụng, muốn tiếp phải thợ bật lại.
3. **Heartbeat 3 giây** — AI im là firmware nhả quyền về HMI (§1). Đây là cái van thật.
4. **Giới hạn tốc độ đổi** — gas không được nhảy quá X%/lần và Y lần/phút. Firmware siết,
   không phải API siết. Đã có sẵn cơ chế slew rate gas trong `AnalogConfig.h`.
5. **Nút dừng cứng** — một nút to đỏ trên app, và nút dừng vật lý trên tủ, cắt quyền tức thì.

### Cửa vào thứ hai — đăng nhập tài khoản app (12/09/2026, ĐÃ LÀM)

`POST /api/v1/login {name, pin}` đổi **tài khoản + PIN của app** lấy token 8 giờ,
thay cho việc bắt buộc phải tạo khoá API. Phạm vi suy ra từ vai trò: Master đủ ba
tầng; thợ chỉ `read`, thêm `config` nếu được giao quyền calib gas / model nhiệt;
**thợ không bao giờ có `control` qua đường này**.

Token đăng nhập bị xếp vào nhóm **tác nhân tự động** chứ không phải "người" như
token PIN web, nên **năm điều kiện T2 ở trên vẫn áp nguyên**. Chủ ý: mật khẩu đi
qua mạng là thứ dùng lại được, không chứng minh có người đứng cạnh máy — tiện hơn
khoá API thì được, lỏng hơn thì không.

Chi tiết dùng ở CLI và MCP: `tools/mcp_roaster/README.md`. Bộ kiểm:
`tools/test_api_login.py`.

**Shadow mode** (theo đúng roadmap cũ) là bước bắt buộc giữa T1 và T2: AI tính ra lệnh, app
**hiện đề xuất cho thợ duyệt** chứ chưa ghi xuống máy. Chạy shadow đủ số mẻ, đối chiếu lệnh AI
với lệnh thợ thật, rồi mới mở T2.

---

## 6. Lớp 2 — API v1

- `/api/v1/…` mới, **giữ nguyên** đường cũ cho app hiện tại. Không phá bản đang chạy.
- Xác thực bằng **API key có phạm vi** (`read` · `config` · `control`), gửi ở header
  `Authorization: Bearer`. Key sinh trong app, hiện đúng một lần, lưu dạng băm.
- **Đóng cổng GET.** Ai muốn đọc thì phải có key `read`.
- Giới hạn tần suất theo key. Ghi nhật ký mọi lệnh ghi: ai (người hay AI), lệnh gì, lúc nào,
  máy trả lời gì. Nhật ký **chỉ thêm, không sửa** — đây là thứ để tra khi có mẻ hỏng.
- **Sinh đặc tả OpenAPI từ `protocol/pc_link.json`** bằng `gen_pc_link.py`. Thêm một emitter
  nữa cạnh 3 emitter đang có. Lệch bản đồ là `--check` bắt được ngay.

---

## 7. Lớp 3 — MCP server

`tools/mcp_roaster/` — Python, đi qua HTTP API v1, **không nói chuyện Modbus trực tiếp**.

**Resources (đọc):**
- `roaster://state` — trạng thái máy lúc này
- `roaster://profiles` — hồ sơ rang
- `roaster://batches/{id}` — một mẻ + đường cong
- `roaster://config` — 52 tham số `$M`

**Tools, đặt tên theo tầng để không bấm nhầm:**
- `read_*` (T0): `read_state`, `read_batch`, `list_profiles`, `compare_batches`
- `set_*` (T1): `set_machine_param`, `save_profile` — trả lỗi rõ lý do khi máy bận
- `control_*` (T2): `control_gas`, `control_charge`, `control_drop`… — mặc định **không nạp**;
  chỉ xuất hiện khi lease T2 đang mở

**Bắt buộc:** mọi tool trả về thất bại phải kèm **lý do đọc được**, không phải mã số. Hôm nay
đã làm mẫu ở `_cfg_reason()` trong `otl_link.py` — "máy đang bận (đang rang · mồi lửa · làm
nóng · còn lửa)" chứ không phải `status=3`. AI đọc được lý do thì mới xử lý đúng; đọc được mã
số thì nó đoán.

---

## 8. Lớp 3b — Extension cho app

- **Manifest JSON**: tên, phiên bản, quyền xin, điểm gắn.
- **Chạy trong `iframe` sandbox**, nói chuyện với app qua `postMessage` — không cho đụng thẳng
  DOM app. App 545 KB một file, extension đụng thẳng vào là vỡ.
- **Điểm gắn:** tab mới · panel bên màn Rang · phản ứng sự kiện mẻ (bắt đầu/TP/FCs/xả).
- **Quyền xin theo đúng 3 tầng ở §5**, thợ duyệt một lần, xem lại được trong Cài đặt.
- Extension **không có đường tắt** xuống T2. Muốn lái máy vẫn phải qua lease.

---

## 9. Thứ tự làm

Cập nhật Codex 07/09/2026: bổ sung phần tham số máy của GĐ D. Sửa GET `mc_read`
thiếu đối số và POST `mc_write` lệch trường `items` trong OpenAPI; giữ nhận `cfg`
cho client cũ. MCP có `roaster_set_machine_param` sau cờ `OTL_MCP_CONFIG=1`,
cần khoá `config`. API kiểm danh sách trước khi ghi, ghi nhật ký kết quả từng
tham số, dừng ở lỗi đầu tiên và báo phần chưa ghi. Kiểm HTTP + MCP bằng cầu giả
trong `tools/test_config_api_mcp.py`; chưa xác nhận trên máy thật.
GĐ D còn phần công cụ lưu hồ sơ; GĐ F và extension vẫn chưa hoàn tất.

| GĐ | Nội dung | Ra được gì | Phụ thuộc |
|---|---|---|---|
| **A** | Nền an toàn: bật watchdog theo tầng · vá 3 lỗ §3 · nhật ký bất biến | Máy an toàn hơn ngay cả khi chưa có AI | — |
| **B** | API v1 read + API key + OpenAPI sinh từ json | AI **đọc** được máy | A |
| **C** | MCP server tầng T0 | AI phân tích mẻ, so hồ sơ, tìm mẻ hỏng — **giá trị thật đầu tiên** | B |
| **D** | API v1 write T1 + MCP `set_*` | AI chỉnh tham số lúc máy rảnh | C |
| **E** | Extension + manifest + sandbox | Người khác viết thêm được | B |
| **F** | Shadow mode — AI đề xuất, thợ duyệt | Đo được AI lái tốt hay không, **không rủi ro** | D |
| **G** | T2 lease + 5 điều kiện | AI lái thật | F chạy đủ số mẻ |

**Trạng thái 2026-09-07:** A · B · C xong. **G làm trước F** theo lệnh chủ máy — lease T2 và
5 điều kiện đã chạy (xem bảng dưới), MCP có tầng lái sau cờ `OTL_MCP_CONTROL`. Shadow mode (F)
vẫn nên chạy trước khi giao AI lái mẻ thật, chỉ là nó không còn chặn đường nữa.

| ĐK §5 | Hiện thực |
|---|---|
| 1 · thợ bật tay tại chỗ | nút **PC control trên HMI** (trên tủ máy, không bật được từ xa) + cờ `OTL_MCP_CONTROL` lúc khởi động MCP |
| 2 · lease có hạn | `POST /api/v1/lease_open`, trần `LEASE_MAX_S` = 15 phút, một tác nhân một lúc |
| 3 · heartbeat 3 giây | `otl_link._hb_cho_phep()` — nhịp chỉ sinh từ request THẬT của AI (`Api.lease_touch` gọi trong `_ctx`), không có luồng nhấp nền |
| 4 · giới hạn tốc độ đổi | `LEASE_STEP` (gas 25 điểm/lệnh) + `LEASE_RATE_N` (60 lệnh/phút) + slew rate firmware |
| 5 · nút dừng cứng | tắt PC control trên HMI (tự huỷ lease) · `lease_close` bằng token thợ · nút dừng vật lý trên tủ |

Còn thiếu: **nút cắt to đỏ ngay trên màn app** — chưa làm vì `OTL Roast Lab.html` đang do
Codex giữ. Thợ vẫn cắt được bằng nút PC control trên HMI, là đường chắc chắn hơn.

GĐ **C là mốc đáng làm nhất** và nó **không đụng gì tới điều khiển**: AI đọc lịch sử mẻ,
chỉ ra mẻ nào lệch đường cong, giải thích vì sao, so hai lô nhân. Toàn bộ giá trị đó có được
mà không cần chạm vào cái van gas nào. Nếu chỉ làm được tới C thì vẫn đã lời.

---

## 10. Rủi ro

| Rủi ro | Chốt chặn |
|---|---|
| AI treo / hết quota giữa mẻ | Watchdog 3s (§1) — firmware nhả quyền, còi kêu |
| AI ra lệnh vô lý (gas 100% lúc FCs) | Firmware kiểm dải + slew rate; giới hạn tốc độ đổi |
| Prompt injection qua tên hồ sơ / ghi chú của thợ | Dữ liệu người dùng là **dữ liệu**, không phải lệnh. MCP không bao giờ thực thi thứ đọc lên từ DB |
| Lộ dữ liệu kinh doanh | Đóng cổng GET (§3), key có phạm vi |
| Extension của bên thứ ba làm bậy | Sandbox iframe + quyền theo tầng + không có đường tắt T2 |
| Hai tác nhân cùng lái (thợ + AI) | Lease độc quyền — có AI thì app hiện rõ "AI ĐANG LÁI", thợ chạm là cắt |
| Bản đồ lệnh lệch giữa 4 phía | `gen_pc_link.py --check` chạy trong CI |

---

## 11. Việc làm ngay được (không cần chờ chốt gì)

1. Bật lại watchdog và **thử trên máy thật** xem nhả quyền có mượt không — việc firmware, làm được ngay.
2. Vá 3 lỗ §3 — việc Python thuần, không đụng máy.
3. Thêm emitter OpenAPI vào `gen_pc_link.py` — nối tiếp việc hôm nay đã làm.

---

## Liên quan

- [plan-roadmap-quocte-ai.md](plan-roadmap-quocte-ai.md) — mục 7 (AI/PC command contract) và 10 (protocol)
- [plan-hmi-roadmap.md](plan-hmi-roadmap.md) — lộ trình app
- `protocol/pc_link.json` · `protocol/gen_pc_link.py` — nguồn sự thật của bản đồ lệnh
- `include/PC_Link.h` — chốt an toàn phía firmware
