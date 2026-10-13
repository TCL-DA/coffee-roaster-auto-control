# MCP server máy rang OTL — tầng ĐỌC + CẤU HÌNH + LÁI

## Đăng nhập bằng TÀI KHOẢN APP (12/09/2026)

Trước đây muốn dùng API hay MCP thì bắt buộc phải vào app tạo khoá, chép chuỗi
`otl_...` ra rồi nhét vào biến môi trường — mỗi máy mới là một vòng như vậy. Nay
có thêm cửa thứ hai: **đăng nhập bằng đúng tài khoản + PIN vẫn gõ ở màn khoá của
app**.

```
POST /api/v1/login   {"name": "Master", "pin": "****"}
   → {"ok": true, "token": "...", "role": "master",
      "scopes": ["read","config","control"], "het_han_s": 28800}
POST /api/v1/logout  (kèm token)  → trả phiên ngay
```

Token sống **8 giờ** (ngắn hơn token PIN web 12 giờ: đây là cửa cho máy, không ai
ngồi cạnh để thấy phiên còn mở). Gửi kèm y như khoá API:
`Authorization: Bearer <token>`.

**Phạm vi theo vai trò** — không phải ai đăng nhập cũng lái được máy:

| Tài khoản | read | config | control |
|---|---|---|---|
| Master | ✔ | ✔ | ✔ |
| Thợ có quyền calib gas / model nhiệt | ✔ | ✔ | ✘ |
| Thợ thường | ✔ | ✘ | ✘ |

**Đăng nhập bằng mật khẩu KHÔNG lỏng hơn khoá API.** App xếp token đăng nhập vào
đúng nhóm *tác nhân tự động*: vẫn phải xin lượt lái (15 phút/lượt, trần 60 phút
cả phiên), vẫn dính hãm bước và hãm tần suất, vẫn cần thợ bật PC control bằng tay
trên HMI. Lý do: lệnh tới qua mạng bằng một mật khẩu dùng lại được thì không có
gì chứng minh có người đứng cạnh máy rang.

Lockout dùng chung với màn khoá của app (sai 7 lần bắt đầu khoá theo tên), cộng
thêm hãm 20 lần/phút theo IP — vì kẻ dò xoay vòng nhiều tên là né được khoá tên.

### Mở khoá luôn MÀN HÌNH app (12/09/2026)

Đăng nhập API là phiên của *script*, còn màn khoá trong cửa sổ app là phiên của
*người* — hai thứ rời nhau, nên lúc đầu đăng nhập bằng API xong nhìn lên màn hình
vẫn thấy màn khoá. Nay `/api/v1/login` **mở khoá luôn màn hình app đang mở** (mặc
định bật; trả về `mo_khoa_app: true/false`). Tắt bằng `{"mo_khoa_app": false}` —
script chạy nền nên gửi cờ này, đừng để màn hình ngoài xưởng tự mở khoá.

Chiều ngược lại: `/api/v1/logout` với `{"khoa_app": true}` khoá màn hình lại.
Mặc định KHÔNG khoá — thợ có thể đang đứng dùng đúng màn hình đó.

Python chỉ gọi xuống UI **sau khi** đã kiểm PIN (băm + pepper + lockout), và màn
hình hiện toast "Mở khoá từ xa qua API: <tên>" + ghi nhật ký, để người đứng ở máy
không bao giờ thấy màn hình tự mở mà không biết vì sao. Cửa sổ app không mở thì
`mo_khoa_app` trả `false`, phần token vẫn cấp bình thường.

CLI: `dangnhap ... --khong-mo-app` và `dangxuat --khoa-app`.
MCP: `roaster_dang_nhap(ten, mk, mo_khoa_app)`.

### Dùng ở CLI

```
python tools/otl_api.py dangnhap Master <PIN>   # token cất ở tools/dist/apitoken.json
python tools/otl_api.py trangthai               # các lệnh sau tự dùng token
python tools/otl_api.py dangxuat
```

### Dùng ở MCP server

Ba đường, server tự chọn theo thứ tự `OTL_API_KEY` → tài khoản trong biến môi
trường → `apikey.txt` → token đã lưu ở `tools/dist/apitoken.json`:

```
set OTL_API_USER=Master
set OTL_API_PIN=****
```

hoặc gọi công cụ `roaster_dang_nhap(ten, mk)` giữa phiên. `roaster_kiem_tra` nói
rõ đang vào bằng đường nào (`cach_vao`). Token hết hạn giữa chừng thì server tự
đăng nhập lại một lần rồi gọi tiếp, miễn là còn `OTL_API_PIN`.

⚠ **Đừng đặt PIN vào `.mcp.json`** — file đó không bị `.gitignore` chặn, còn repo
này công khai. Cách sạch: chạy `otl_api.py dangnhap` một lần, MCP server dùng
chung token đã lưu (`tools/dist/` đã bị gitignore).

Bộ kiểm: `python tools/test_api_login.py` (cần app đang chạy và
`OTL_TEST_USER`/`OTL_TEST_PIN`; thiếu thì tự bỏ qua).

## Vá 5 lỗi tầng lái, soát trên MÁY THẬT (12/09/2026)

Bắt được bằng cách lái máy thật qua API/MCP rồi ép nặng, không phải bằng đọc mã.

| # | Lỗi | Gốc | Cách vá |
|---|---|---|---|
| 1 | Bắn ~12 lệnh trong 1 giây là **đứt liên lạc Modbus** | bo STM32 vừa làm slave cho PC vừa làm master hỏi 6 node trên RS485 38400; lệnh ghi cách nhau 10ms là nó lỡ khung | `otl_link._run`: mỗi chu kỳ poll phát tối đa **3 lệnh, cách nhau 50ms**, phần dư nằm lại hàng đợi đúng thứ tự (không gộp — nhịp `charge 1→0` không được nuốt) |
| 2 | Một khung hụt = **mất lái vĩnh viễn** | `_set_state("error")` chạy ngay lần hụt đầu, tầng trên thấy "không connected" là đóng lượt lái, dù 2s sau đã nối lại | báo lỗi từ lần hụt **thứ 2**; và lượt lái có **ân hạn 3 giây** (đúng bằng watchdog PC control của firmware) — nối lại kịp thì lái tiếp, trả mã riêng `link_gian_doan` |
| 3 | Trần bước nhảy chặn **cả chiều giảm** | `abs(moi - cu) > buoc` | chỉ hãm chiều TĂNG; hạ gas/gió/trống bao nhiêu cũng được |
| 4 | Hết quota 60 lệnh/phút thì **rút gas cũng bị chặn** | chốt tần suất áp cho mọi lệnh | lệnh **kéo mức xuống miễn quota** |
| 5 | Cặp nhiệt hở đọc **3277,2 °C** lọt ra app | `SensorGuard` giữ "giá trị tốt gần nhất", nhưng hỏng từ lúc khởi động thì chưa có giá trị tốt nào → trả nguyên số rác | trả **None** = "không có số", kèm cờ `sens_warn`; `roast_derive.feed` bỏ qua nhịp None |

Lỗi 3 và 4 cùng một bài học: **chốt an toàn chỉ được chặn chiều làm máy nóng thêm.**
Chặn luôn chiều rút là tự nhốt mình ngoài cửa đúng lúc cần rút nhất.

Sau khi vá, bắn 70 lệnh liên tiếp qua MCP: link vẫn `connected`, trễ 4ms.

## Đối chiếu đọc và điều khiển (07/09/2026)

`roaster_trang_thai` gọi GET `/api/v1/snapshot`. Trong `data` có:
`bt`, `et` (°C); `ror_bt`, `ror_et` (°C/phút); `gas`, `air`, `drum` (%);
`drum_hz` (Hz); `vac` (Pa); `step`, `t_roast`; `flags.charge/drop/flame`;
`prof_sel`, `prof_pct`, `prof_ok`. Kiểm `state`, `age_ms`, `mode` để biết dữ liệu
còn mới và đang dùng PC_Link hay khối tương thích. Khối tương thích suy diễn
RoR/mốc tại app và không cung cấp đầy đủ phản hồi hồ sơ SD như PC_Link.

`flags.flame` là lửa THẬT (chân CH1 của board, `PCLF_FLAME`), khác relay gas đang bật.
Đo bàn thử 12/10/2026 (panel + board thật): gas mở 75 s không lửa → board đóng gas,
báo mã 414, đang có mẻ thì tắt START (huỷ mẻ, không treo). Sau mẻ huỷ / dừng, chọn lại
đúng ô hồ sơ cũ thì board không tải lại — căn cứ "đã nạp hồ sơ" là W40119 = 1, không phải
mã trạng thái 102.

`roaster_ho_so` đọc hồ sơ lưu tại app qua `/api/v1/profiles`; đây không phải
nội dung toàn bộ file hồ sơ trên thẻ SD của firmware.

Chiều ghi dùng POST `/api/v1/write`: `name=gas/air/drum` nhận %, `sv` nhận °C,
`scale_tg` nhận kg. MCP có `roaster_lai_gas/gio/trong/lua`; các lệnh
`charge`, `drop`, `profile`, `mode`, `auto` đi qua `roaster_lai_lenh`.
Cần `OTL_MCP_CONTROL=1`, khoá `control`, PC control trên HMI và lease hợp lệ.

Phản hồi `status=queued` chỉ xác nhận lệnh vào hàng đợi Modbus; `value` là giá trị
thanh ghi, `engineering_value` là đơn vị kỹ thuật. Đọc lại snapshot để đối chiếu.
Cờ Charge/Drop phản ánh nút điều khiển, không chứng minh hạt đã di chuyển xong;
mức burner/gió/trống cũng không phải phép đo công suất nhiệt hay lưu lượng khí.

Kiểm thử xuyên HTTP và MCP: `python tools/test_telemetry_control_mcp.py`.
Dùng thanh ghi giả và hàng đợi Modbus thật của lớp link; không mở cổng serial.

## Bổ sung tầng cấu hình (07/09/2026)

Đặt `OTL_MCP_CONFIG=1` và dùng khoá có phạm vi `config` để nạp công cụ
`roaster_set_machine_param`. Cờ này độc lập với `OTL_MCP_CONTROL`; mặc định tắt.
Đối số: `idx` là số $M, `value` là số nguyên thô HMI (không tự đổi đơn vị).
Firmware kiểm dải riêng từng tham số và từ chối khi máy bận.

HTTP tương ứng: `POST /api/v1/mc_write`, thân JSON
`{"items": [["M1", 1, 10]]}`. Đây là ví dụ định dạng, không phải giá trị khuyến nghị.
API chặn danh sách sai trước khi ghi, ghi nhật ký kết quả và dừng khi gặp lỗi.
Nếu ghi được một phần, `ok=false`, `count` cho biết số đã ghi,
`errors` giữ lý do và `not_attempted` liệt kê phần chưa thử; không tự hoàn tác.
Đường cũ vẫn nhận `cfg` theo cùng định dạng danh sách.

`GET /api/v1/mc_read` trả `cfg` với tên `M1` đến `M<số $M lớn nhất>`, giá trị thô HMI.
Kiểm thử không cần máy thật: `python tools/test_config_api_mcp.py`.

## Đồng bộ số tham số $M và bộ lọc lịch sử (08/09/2026)

**Số $M không còn ghi cứng.** Trước đây mô tả công cụ ghi thẳng "52 tham số", trong
khi firmware đã mở tới `$M53`; AI đọc mô tả sẽ tin là không có `$M53` và không bao
giờ hỏi tới nó. Nay `server.py` lấy số từ nguồn sinh sẵn — `tools/pc_link_map.py`
(`CFG_MAXIDX`), dự phòng `protocol/pc_link.json`. Sửa JSON rồi chạy
`python protocol/gen_pc_link.py` là mô tả công cụ, dải `idx` trong schema và
OpenAPI cùng đi theo. Không lấy được cả hai nguồn thì mô tả nói chung chung chứ
**không bịa** một con số.

`$M53` là **tự động mở cửa xả**: `1` = chạy trọn chuỗi xả tự động, `0` = chỉ làm
nguội, thợ xả tay. Firmware chỉ nghe thanh ghi này khi HMI thật sự có ô gạt đó.
Ghi vẫn đi đúng đường cũ: khoá `config`, `OTL_MCP_CONFIG=1`, firmware kiểm dải và
khoá khi máy bận — đợt này **không nới** quyền nào.

**Lọc lịch sử mẻ chạy dưới kho, không cắt trên trang.** `roaster_danh_sach_me` nay
nhận `tu_khoa`, `tu_ngay`, `den_ngay` (`YYYY-MM-DD`), `so_luong`, `bo_qua` và đẩy
hết xuống `GET /api/v1/batches`. Trước đây nó kéo về một trang rồi mới cắt trong bộ
nhớ, nên tìm trong kho 900 mẻ chỉ soi được 50 mẻ mới nhất rồi báo "không có".

**`tong` là tổng thật, không phải số dòng của trang.** Thêm `GET /api/v1/batches_count`
(cùng bộ lọc `q`/`from`/`to`, không phân trang) và công cụ `roaster_dem_me`. Phân
biệt rõ: `count = 0` là đếm được mà không mẻ nào khớp; `count = null` là **chưa đếm
được** (kho chưa mở hoặc lỗi đọc). Khi đếm hỏng, `roaster_danh_sach_me` trả
`tong = null` kèm `ghi_chu_tong` chứ không lấy `len(batches)` thay vào — đó đúng là
con số sai mà đợt này đi sửa.

Lời gọi cũ chỉ có `so_luong` vẫn chạy nguyên như trước.

Kiểm thử: `python tools/test_mcp_api_update.py` (kho SQLite tạm + cầu giả, không
chạm máy thật).

Cho AI đọc máy rang để **phân tích**: trạng thái, hồ sơ, lịch sử mẻ, đường cong, tham số `$M`.
Và — khi người vận hành tự bật — cho AI **lái máy**: gas, gió, trống, mồi lửa, nạp, xả.

**Mặc định tầng lái TẮT.** Không bật thì không một công cụ lái nào xuất hiện trong danh sách,
gọi thẳng tên cũng chỉ nhận *"không có công cụ tên đó"*.

## Cần gì

1. App **OTL Roast Lab đang chạy** (nó là chỗ giữ cầu Modbus tới máy).
2. Một **khoá API**:

```bash
python tools/otl_apikey_cli.py add "MCP doc may rang" read            # chỉ đọc
python tools/otl_apikey_cli.py add "MCP lai may" read control         # đọc + lái
```

Khoá hiện **đúng một lần** — chép ngay.

## Đăng ký với Claude Code

Thêm vào `~/.claude.json`, mục `mcpServers`:

```json
"otl-roaster": {
  "command": "python",
  "args": ["F:\\Project\\100_OTL_06ALS - CMS - Cacao\\tools\\mcp_roaster\\server.py"],
  "env": {
    "OTL_API_KEY": "otl_…",
    "OTL_API_BASE": "http://127.0.0.1:8555"
  }
}
```

Muốn mở tầng lái thì thêm `"OTL_MCP_CONTROL": "1"` vào `env`.

> Ghi thẳng vào JSON, **đừng** dùng `claude mcp add` trong Git Bash — nó biến `/c` thành `C:/`
> làm hỏng config (đã dính một lần với MCP Excel).

Máy khác trong xưởng thì đổi `OTL_API_BASE` thành `http://<ip-máy-chạy-app>:8555`.

## Công cụ tầng ĐỌC

| Công cụ | Làm gì |
|---|---|
| `roaster_kiem_tra` | có nối được app không, khoá dùng được không — gọi trước khi báo lỗi |
| `roaster_trang_thai` | nhiệt BT/ET, RoR, gas/gió/trống, bước quy trình |
| `roaster_ho_so` | danh sách hồ sơ rang |
| `roaster_danh_sach_me` | các mẻ đã rang — lọc `tu_khoa`/`tu_ngay`/`den_ngay`, phân trang `so_luong`+`bo_qua`, kèm `tong` thật |
| `roaster_dem_me` | **đếm** mẻ khớp bộ lọc, không kéo dữ liệu mẻ về |
| `roaster_duong_cong_me` | đường cong một mẻ |
| `roaster_thong_ke_me` | mốc TP/DE/FCs/Drop, thời gian từng pha |
| `roaster_so_me` | **so nhiều mẻ** — tìm mẻ lệch khỏi nhóm |
| `roaster_cau_hinh_may` | đọc cả khối `$M` (chậm: mỗi tham số một lượt hỏi-đáp) |

## Công cụ tầng LÁI (chỉ khi `OTL_MCP_CONTROL=1`)

| Công cụ | Làm gì |
|---|---|
| `roaster_lai_trang_thai` | ai đang cầm lái, còn mấy giây, luật đang áp |
| `roaster_lai_xin_quyen` | xin lượt lái (tối đa 15 phút) |
| `roaster_lai_tra_quyen` | trả quyền về thợ |
| `roaster_lai_gas` | mức gas 0–100% |
| `roaster_lai_gio` | mức gió 0–100% |
| `roaster_lai_trong` | tốc độ trống 0–100% |
| `roaster_lai_lua` | mồi lửa / tắt bếp |
| `roaster_lai_hut` | áp hút đặt (Pa) và PID gió theo áp hút |
| `roaster_lai_lenh` | lệnh còn lại: `charge`, `drop`, `cool`, `escape`, `auto`, `afterburner`… |

## Chuỗi an toàn — 6 mắt xích

Bật `OTL_MCP_CONTROL=1` mới chỉ là mắt xích đầu. Một lệnh gas muốn tới được van gas phải qua:

1. **Khoá API có phạm vi `control`** — khoá `read` bị chặn ngay ở app.
2. **Thợ bật PC control trên HMI bằng tay** — nút nằm trên tủ máy, không có đường bật từ xa.
   Đây chính là "công tắc cho phép AI lái" trong kế hoạch.
3. **Lượt lái (lease)** — xin trước, tối đa 15 phút, hết là tự rụng. Một lúc chỉ một tác nhân.
4. **Hãm bước nhảy và tần suất** — gas đổi tối đa 25 điểm mỗi lệnh, 60 lệnh mỗi phút.
5. **Nhịp sống thật** — AI im quá 20 giây thì app **ngừng nhấp heartbeat**, và trong 3 giây
   firmware trả quyền về HMI kèm còi.
6. **Firmware phủ quyết** — kiểm dải, watchdog, và chốt mồi hụt 75 giây tự đóng gas.

Luật 1–5 nằm ở **app** (`tools/roast_lab_hmi.py`), luật 6 ở **firmware**. Không luật nào nằm
trong file này: ai viết MCP server khác, hay gọi thẳng bằng `curl`, vẫn dính đúng bấy nhiêu.

> **Đừng thêm luồng nền nhấp nhịp vào `server.py`.** Nhịp chỉ được sinh ra khi AI thật sự gọi
> một công cụ — đó là cách duy nhất máy biết AI còn sống. Một luồng nhấp nền chạy đều đặn sẽ
> giả vờ AI còn sống trong khi nó đã treo, và phá đúng cái van an toàn số 5.

## Cắt quyền ngay lập tức

- Thợ **tắt nút PC control trên HMI** → máy về tay thợ ngay, lượt lái tự huỷ.
- Hoặc gọi `roaster_lai_tra_quyen`.
- Hoặc từ web/app: `POST /api/v1/lease_close` bằng token của thợ — thợ cắt được lượt lái của
  bất kỳ tác nhân nào.

## Khi hỏng

Mọi lỗi đều nói **lý do đọc được**, không phải mã số:

- *"không nối được app… App OTL Roast Lab có đang chạy không?"* → mở app.
- *"thiếu hoặc sai OTL_API_KEY"* → khoá sai, hoặc app chưa nạp khoá mới (chờ ~2 giây).
- *"khoá API không có phạm vi 'read'"* → tạo lại khoá với `read`.
- *"tầng lái đang TẮT"* → khởi động lại server với `OTL_MCP_CONTROL=1`.
- *"nút PC control trên HMI đang TẮT"* → ra tủ máy bật, không bật từ xa được.
- *"gas đang 30, đòi 80 — mỗi lệnh chỉ đổi tối đa 25"* → chia nhỏ, chờ nhiệt phản hồi.
- `roaster_trang_thai` trả `state: error, err: could not open port COM…` → app chạy nhưng
  **chưa nối được máy rang**. Đó là chuyện của cáp/cổng COM, không phải lỗi MCP.

## Kiểm

```bash
python tools/test_mcp_roaster.py     # cần app đang chạy; tự tạo và tự xoá khoá thử
python tools/test_otl_link.py        # mục 9: nhịp tim có điều kiện (không cần máy)
```
