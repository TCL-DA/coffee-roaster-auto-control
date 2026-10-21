# BÁO CÁO MCP SERVER VÀ API — OTL ROAST LAB

**Ngày báo cáo:** 09/09/2026  
**Đối tượng đọc:** Ban lãnh đạo, quản lý sản xuất và phụ trách kỹ thuật  
**Phạm vi:** App OTL Roast Lab, API nội bộ, MCP Server và kết nối máy rang OTL-06ALS

## 1. Tóm tắt điều hành

OTL Roast Lab hiện đã có một lớp API và MCP Server cho phép trợ lý AI đọc dữ liệu rang, phân tích lịch sử, đọc và thay đổi cấu hình máy, đồng thời điều khiển phần lớn cơ cấu của máy rang khi được người vận hành cấp quyền.

Hệ thống không cho AI kết nối Modbus trực tiếp. Mọi yêu cầu phải đi qua bốn lớp:

1. Trợ lý AI gọi công cụ MCP.
2. MCP Server chuyển yêu cầu sang API của Roast Lab.
3. App kiểm tra khóa, phạm vi quyền, lượt lái và giới hạn lệnh.
4. Firmware STM32 kiểm tra lần cuối trước khi tác động lên máy.

Thiết kế này tạo nền tảng để Roast Lab phát triển thành hệ thống quản lý và tối ưu rang có AI, thay vì chỉ là một màn hình điều khiển. Tuy nhiên, quyền điều khiển máy thật vẫn đang ở giai đoạn kỹ thuật: đã qua kiểm thử giả lập và build firmware, nhưng chưa nghiệm thu đầy đủ trên máy rang thực tế.

## 2. Giá trị đối với doanh nghiệp

### Giá trị đã có

- Theo dõi trạng thái máy và mẻ rang bằng phần mềm hoặc trợ lý AI.
- Tra cứu nhanh hồ sơ, lịch sử và đường cong mẻ rang.
- So sánh nhiều mẻ để tìm sai lệch về nhiệt độ, thời gian và các giai đoạn rang.
- Đọc và hiệu chỉnh cấu hình máy từ một giao diện tích hợp có phân quyền.
- Chuẩn bị nền tảng để AI hỗ trợ vận hành, đào tạo thợ và điều tra nguyên nhân mẻ lỗi.
- Lưu dấu vết thao tác để biết tác nhân nào đã gửi lệnh gì và vào thời điểm nào.
- Mở đường cho các chức năng tiếp theo: quản lý hồ sơ rang, nhân xanh, thành phẩm, khách hàng và mô phỏng hồ sơ.

### Giá trị kỳ vọng khi hoàn thiện

- Chuẩn hóa chất lượng giữa nhiều thợ và nhiều ca sản xuất.
- Rút ngắn thời gian tìm hồ sơ phù hợp cho từng loại hạt và từng khách hàng.
- Giảm mẻ thử nhờ mô phỏng và so sánh với dữ liệu lịch sử.
- Truy xuất từ khách hàng, đơn hàng và thành phẩm về đúng mẻ rang và lô nhân xanh.
- Hỗ trợ ra quyết định nhưng vẫn giữ quyền phê duyệt cuối cùng cho người vận hành.

## 3. Năng lực MCP hiện tại

### 3.1. Đọc và phân tích

MCP hiện có thể:

- Kiểm tra app và API có đang hoạt động hay không.
- Đọc BT, ET, RoR, gas, gió, trống, SV, áp hút và bước rang.
- Đọc trạng thái lửa, PC Control và các cờ vận hành.
- Đọc trạng thái bật/tắt của PID gió theo áp hút (thêm 09/09/2026 — trước đó chỉ ra lệnh được, không đọc lại được).
- Đọc danh sách hồ sơ rang.
- Tìm lịch sử mẻ theo từ khóa và khoảng ngày.
- Phân trang lịch sử và đếm đúng tổng số mẻ theo bộ lọc.
- Đọc toàn bộ đường cong của một mẻ.
- Đọc thống kê TP, DE, FCs, Drop và thời gian từng pha.
- So sánh nhiều mẻ để phát hiện mẻ lệch khỏi nhóm.
- Đọc toàn bộ khối cấu hình máy từ M1 đến M60, trừ các địa chỉ lịch sử không được định nghĩa.
- Đọc các skill nghiệp vụ dùng chung với trợ lý tích hợp trong Roast Lab.

### 3.2. Thay đổi cấu hình

Khi MCP được khởi động với tầng cấu hình và API key có quyền `config`, hệ thống có thể đọc hoặc ghi tham số máy. App và firmware cùng kiểm tra dải của từng tham số.

Khối cấu hình hiện đã mở tới M60. Các tham số mới gồm:

| Tham số | Nội dung | Dải cấu hình |
|---|---|---:|
| M54 | Thời hạn PID preheat đạt nhiệt mục tiêu | 60–900 giây |
| M55 | Thời gian ổn định trước khi đánh giá giữ nhiệt | 10–120 giây |
| M56 | Dải nhiệt mục tiêu preheat | 1,0–3,0 °C |
| M57 | Ngưỡng cảnh báo tỷ lệ development | 10,0–30,0% |
| M58 | Thời gian tối thiểu trước khi auto-drop | 120–600 giây |
| M59 | Thời gian mở Escape bổ sung | 0–30 giây |
| M60 | Timeout cửa Drop bị kẹt khi chạy loop | 5–60 giây |

M23 cũng đã được sửa đúng quy ước nhiệt độ nhân 10: giá trị `1800` tương ứng `180,0 °C`.

M17 và M18 là hai vị trí trống từ thiết kế cũ, chưa có chức năng vận hành và firmware tiếp tục từ chối ghi vào hai địa chỉ này.

### 3.3. Điều khiển máy rang

Khi bật riêng tầng điều khiển, dùng khóa có quyền `control`, bật PC Control tại máy và có lượt lái hợp lệ, MCP có thể gửi các lệnh:

- Đặt mức gas, gió và tốc độ trống.
- Đặt SV nhiệt và áp hút.
- Bật hoặc tắt PID điều khiển gió theo áp hút.
- Mồi lửa hoặc tắt bếp.
- Charge, Drop và Escape.
- Bật hoặc tắt làm nguội.
- Điều khiển quạt trống và cánh khuấy.
- Điều khiển afterburner, loader và destoner.
- Chọn hồ sơ, chế độ rang và bật hoặc tắt Auto.
- Bật Auto Loader và đặt khối lượng cân đích.
- Xem, xin và trả lượt điều khiển.

Phản hồi `queued` chỉ có nghĩa lệnh đã được xếp để gửi, không phải bằng chứng van, động cơ hoặc xi-lanh đã chuyển động. Muốn xác nhận hoàn tất phải đọc lại trạng thái máy hoặc bổ sung cảm biến phản hồi tương ứng.

## 4. Cơ chế an toàn và phân quyền

> Mục này đã được rà lại từng câu đối chiếu mã nguồn ngày 09/09/2026. Bản trước
> mô tả chuỗi an toàn kín hơn thực tế ở bốn điểm; những điểm đó nay đã được vá
> trong mã và mô tả lại cho đúng ở đây. Nhật ký vá ở mục 11.

### 4.1. Mặc định an toàn

- MCP mặc định chỉ tải các công cụ đọc.
- Tầng sửa cấu hình phải bật bằng `OTL_MCP_CONFIG=1`.
- Tầng điều khiển phải bật bằng `OTL_MCP_CONTROL=1`.
- API key được chia phạm vi `read`, `config` và `control`.
- Quyền cấu hình không tự động cấp quyền điều khiển máy. Hơn thế, nhóm tham số
  $M lái trực tiếp lửa, nhiệt hoặc cơ cấu — trần gas tuyệt đối, gas mồi, nhiệt
  bật gas, nhiệt nạp, mốc DE/FCs, thời gian xi-lanh, tham số preheat — nay đòi
  **cả hai** phạm vi `config` và `control`. Lý do: khối cấu hình chạy độc lập
  nút PC control, nên nếu chỉ cần `config` thì một tác nhân đổi được trần gas
  lúc máy nguội, không ai đứng cạnh, rồi mẻ sau thợ rang tay theo tham số đã bị
  đổi. Nhóm còn lại (ID slave, thang đo cảm biến, ngưỡng cân, kho) vẫn chỉ cần
  `config`.

### 4.2. Hai loại người gọi — luật khác nhau

Cần phân biệt rõ, vì hai đường này chịu luật rất khác nhau:

- **NGƯỜI** (thợ dùng app tại máy, hoặc điện thoại đã nhập PIN web): có đủ mọi
  phạm vi, **không** phải xin lượt lái, **không** bị hãm bước nhảy. Đây là chủ
  ý — thợ đứng cạnh máy, thấy khói và nghe tiếng nổ hạt. Hệ quả cần nói thẳng:
  ai lấy được PIN web hoặc token web thì có quyền **cao hơn** một khoá API
  `control`. PIN web vì vậy phải được coi như chìa khoá tủ máy.
- **MÁY** (script, MCP, trợ lý AI dùng khoá API): chịu toàn bộ luật ở 4.3.

### 4.3. Lượt lái có thời hạn — dành cho tác nhân tự động

- Người vận hành phải bật PC control tại tủ máy bằng tay. Không có đường bật từ xa.
- Tác nhân AI phải xin một lượt lái trước khi gửi lệnh điều khiển.
- Một thời điểm chỉ có một tác nhân giữ lượt.
- **Một lượt tối đa 15 phút**, và **tổng cả phiên PC control tối đa 60 phút**.
  Trần phiên là điểm mấu chốt: không có nó thì trần 15 phút vô nghĩa, vì khoá
  đang cầm lái xin lại được ngay lập tức và lái vô tận mà không ai phải có mặt.
  Hết trần phiên thì thợ phải tắt rồi bật lại PC control mới lái tiếp được —
  tức là bắt buộc có một hành động của con người tại tủ.
- **Nhịp tim chỉ tính hành động lái**: lệnh ghi, hoặc lời gọi `lease_beat` cho
  tường minh. Việc **đọc** trạng thái không còn tính là nhịp. Trước đây mọi
  request đều tính, nên một vòng lặp đọc telemetry còn chạy là đủ giữ quyền lái
  dù phần suy nghĩ của AI đã treo hay hết quota — nhịp khi đó đo "tiến trình còn
  chạy" chứ không đo "tác nhân còn tỉnh", đúng cái mà chốt im lặng sinh ra để bắt.
- Tác nhân im quá 20 giây thì app ngừng nhấp heartbeat; firmware nhả quyền PC
  control về HMI sau 3 giây và hú còi.
- Người vận hành có thể tắt PC control hoặc đóng lượt để thu hồi quyền bất cứ lúc nào.

### 4.4. Chốt firmware

- Firmware giữ quyền phủ quyết cuối cùng.
- **Kiểm dải hai kiểu, cố ý khác nhau:** lệnh điều khiển (gas, gió, trống, SV,
  áp hút) bị **kẹp im lặng** về biên; tham số cấu hình $M thì bị **từ chối** kèm
  mã lỗi. Kẹp im lặng nghĩa là app xin 150% gas sẽ nhận `queued` và máy chạy
  100% — muốn biết máy thật sự nhận bao nhiêu thì phải đọc lại khối trạng thái.
- Khoá ghi cấu hình khi máy đang bận: có lửa, đang làm nóng, đang chạy AUTO,
  hoặc đang trong vòng mẻ từ bước mồi lửa trở đi.
- Watchdog tác nhân tự động: siết 3 giây khi phần mềm khai `agent = 1`. **Cần
  nói rõ giới hạn:** watchdog này chỉ siết khi bên gọi *tự khai* mình là tác
  nhân tự động. Cờ có cài then (khai 1 rồi thì không hạ về 0 giữa phiên để né
  watchdog), nhưng không có gì chống trường hợp một client chưa bao giờ khai.
  Đây là chốt tự nguyện ở tầng phần mềm, không phải chốt cứng của firmware —
  cần biết đúng bản chất khi đánh giá rủi ro.
- Chốt mồi hụt đóng gas: bật gas quá 75 giây mà không có tín hiệu lửa thì
  firmware tự đóng gas và hú còi. Chốt này chạy độc lập, không phụ thuộc cờ nào.
- Giới hạn bước thay đổi và tần suất lệnh tại tầng app. **Đúng bản chất:** đây
  là chốt chống *một cú nhảy* (mỗi lệnh đổi tối đa 25 điểm gas), không phải chốt
  chống *leo thang nhanh* — với trần 60 lệnh/phút thì gas vẫn đi từ 0 lên 100
  trong bốn lệnh. Chốt tốc độ thật nằm ở slew rate của firmware: 100% trong 3
  giây khi tăng, 100% trong 5 giây khi giảm.
- Handshake cấu hình chỉ báo thành công sau khi HMI xác nhận ghi; không còn báo
  thành công giả khi Modbus HMI thất bại.

### 4.5. Mô hình đe doạ — ai tác động được vào máy

Không có mục này thì mọi bảng phân quyền ở trên đều thiếu ngữ cảnh.

| Kẻ tác động | Vào bằng đường nào | Chịu luật nào |
|---|---|---|
| Thợ tại máy | App desktop | Không luật nào — chủ ý |
| Người trong LAN xưởng có PIN web | HTTP cổng 8555 | Không luật lái nào — quyền ngang thợ |
| Tác nhân AI / script | Khoá API | Toàn bộ luật mục 4.3 |
| Người trong LAN xưởng **không** có PIN | HTTP | Chặn ở cổng token; PIN 6 số, sai 5 lần khoá 5 phút theo IP |
| Người cắm được vào bus RS485 hoặc cổng USB | Modbus trực tiếp | **Chỉ còn kẹp dải và chốt mồi hụt của firmware.** Không lease, không audit, không phạm vi quyền |

Hai điều phải ghi nhận thẳng:

1. **Toàn bộ đường mạng chạy HTTP trần.** Khoá API, PIN web và token đi qua WiFi
   xưởng dạng rõ. Trong một mạng xưởng dùng chung, đây là mặt phẳng tấn công
   thật. Biện pháp hiện tại là mạng nội bộ tách riêng, chưa phải TLS.
2. **Đường Modbus trực tiếp không chịu tầng phân quyền nào.** Ai cắm được vào
   bus là ghi thẳng được khối lệnh. Đây là lý do các chốt của firmware (kẹp dải,
   mồi hụt đóng gas, khoá cấu hình khi máy bận) phải tồn tại độc lập với app.

## 5. Kiến trúc triển khai

```text
Trợ lý AI
    │ MCP
    ▼
MCP Server
    │ HTTP + API key
    ▼
API v1 trong Roast Lab
    │ kiểm quyền, lease, giới hạn và audit
    ▼
RoasterLink / PC-Link
    │ Modbus RTU
    ▼
Firmware STM32
    │ kiểm tra an toàn cuối cùng
    ▼
Gas · gió · trống · xi-lanh · thiết bị phụ
```

MCP Server chỉ là lớp chuyển ngữ. Luật an toàn quan trọng nằm trong app/API và firmware, vì một chương trình khác gọi thẳng API vẫn phải chịu cùng các giới hạn.

Cần đọc sơ đồ này cùng mục 4.5: nó mô tả đường đi **qua app**. Ai cắm được thẳng vào bus RS485 hoặc cổng USB thì vào ở nấc dưới cùng, bỏ qua toàn bộ phần phân quyền — đó là lý do các chốt của firmware phải tồn tại độc lập với app.

## 6. Kết quả kiểm chứng

Chạy lại toàn bộ sau đợt vá 09/09/2026. Ghi kèm lệnh để ai cũng tái lập được.

| Hạng mục | Lệnh | Kết quả |
|---|---|---|
| Đồng bộ bản đồ PC-Link | `python protocol/gen_pc_link.py --check` | Cả 3 phía khớp |
| Luật lái T2 | `python tools/test_lease_t2.py` | Tất cả đạt (14 nhóm) |
| Cầu Modbus + lùi khối đọc | `python tools/test_otl_link.py` | Tất cả đạt |
| Cấu hình $M qua API/MCP | `python tools/test_config_api_mcp.py` | 6/6 đạt |
| Telemetry + điều khiển MCP | `python tools/test_telemetry_control_mcp.py` | 9/9 đạt |
| Đồng bộ MCP/API | `python tools/test_mcp_api_update.py` | 13/13 đạt |
| Firmware | `pio run -e genericSTM32F103RC` | SUCCESS |

- RAM sử dụng: 40.028/49.152 byte, tương đương **81,4%**. Ngưỡng cảnh báo của dự
  án là 88% RAM tĩnh, nên còn khoảng 3.300 byte dư địa cho các giai đoạn sau.
- Flash sử dụng: 102.244/262.144 byte, tương đương **39,0%**.
- Hai bộ `test_api_scope.py` và `test_mcp_roaster.py` cần app đang chạy thật nên
  tự bỏ qua trong lần chạy này — chưa tính là đạt, cũng chưa tính là hỏng.

### Cảnh báo build còn lại

Các cảnh báo hiện còn là cảnh báo cũ của dự án:

- `ADDREG` được định nghĩa lại bởi thư viện Modbus.
- Kiểu `boolean` cũ của Arduino đã bị đánh dấu deprecated.
- Một số cảnh báo narrowing trong mã kế thừa.

Chưa ghi nhận linker error hoặc vượt bộ nhớ Flash/RAM trong lần build này.

## 7. Giới hạn và phần chưa hoàn tất

### Chưa nghiệm thu trên phần cứng

- Chưa flash và nghiệm thu M54–M60 trên máy thật.
- Chưa thử toàn bộ lệnh điều khiển với gas và cơ cấu thật.
- Toàn bộ đợt vá 09/09 (mục 11) mới build xong, **chưa nạp lên máy**.

### Còn thiếu về chức năng

- Chưa có kênh PC-Link riêng cho xi-lanh `DISCHARGE`.
- Charge, Drop, Escape và một số thiết bị phụ vẫn dùng công cụ MCP tổng quát.
- Chưa từ chối đầy đủ lệnh theo biến thể phần cứng; máy không có cảm biến vacuum
  hoặc module relay phải trả `không hỗ trợ`, không nên chỉ trả `queued`.
- Chưa có interlock riêng theo trạng thái cho mọi lệnh Charge, Drop và Escape do
  tác nhân PC gửi.
- Giao diện HTML: bản đồ sinh tự động đã mở tới M60, nhưng **màn hình cấu hình
  chưa có hàng cho M54–M60** — phần này chờ đợt sửa giao diện.

### Còn tồn về an toàn — đã biết, chưa vá

Bốn mục dưới đây là nợ kỹ thuật đã xác định, xếp theo mức nghiêm trọng:

1. **Không có TLS.** Khoá API, PIN web và token đi trần trên WiFi xưởng. Đây là
   rủi ro lớn nhất còn lại. Cách xử lý phải chọn: TLS nội bộ, hoặc tách mạng
   xưởng ra VLAN riêng, hoặc buộc MCP chỉ chạy trên chính máy tính cạnh máy rang.
2. **Khoá API không có hạn dùng, không xoay vòng, không ràng theo IP.** Lộ khoá
   là lộ vĩnh viễn cho tới khi có người nhớ vào xoá tay.
3. **Dòng SSE `/api/stream` chỉ kiểm token lúc mở kết nối.** Token hết hạn hoặc
   bị thu hồi không cắt được dòng đang mở.
4. **Kẹp im lặng ở đường của thợ.** Thợ đặt giá trị ngoài dải thì app kẹp về
   biên rồi vẫn báo thành công, trong khi đường tác nhân thì từ chối kèm lý do.
   Hai chuẩn khác nhau trong cùng một hệ; nên thống nhất về hướng báo lỗi.

### Về quy trình

- Đặc tả và code hiện nằm trong worktree có nhiều thay đổi chưa commit; chưa
  phải bản release chính thức.
- Phản hồi `queued` cần tiếp tục được phân biệt rõ với xác nhận cơ cấu thực tế.

## 8. Lộ trình đề xuất

### Giai đoạn 1 — hoàn thiện nền điều khiển

1. Thêm kênh `DISCHARGE` vào PC-Link, API và MCP.
2. Tạo tool riêng cho Charge, Drop, Escape, cooling và từng thiết bị phụ.
3. Bổ sung bảng capability theo biến thể máy.
4. Thêm interlock trạng thái riêng cho lệnh từ tác nhân tự động.
5. Cập nhật giao diện M54–M60 sau khi khóa UI được trả.
6. Kiểm thử Hardware-in-the-loop khi máy nguội và không có cà phê.

### Giai đoạn 2 — quản lý dữ liệu rang bằng MCP

1. Tạo, sửa, nhân bản và version hóa hồ sơ rang.
2. Tạo hồ sơ từ một mẻ rang thực tế tốt.
3. Quản lý lô nhân xanh và truy xuất tồn kho.
4. Quản lý thành phẩm, QC và cupping.
5. Tạo hồ sơ khách hàng độc lập, liên kết đơn hàng và gu rang.
6. Tách scope dữ liệu thương mại khỏi scope đọc trạng thái máy.

### Giai đoạn 3 — mô phỏng và trợ lý vận hành

1. Mô phỏng hồ sơ hoàn toàn ngoại tuyến, không gửi lệnh xuống máy.
2. So sánh mô phỏng với các mẻ thật tương tự.
3. Phát hiện RoR crash/flick, development bất thường và bước gas/gió không phù hợp.
4. Chạy Shadow Mode: AI đề xuất, thợ duyệt, chưa tự điều khiển.
5. Chỉ xem xét tự động hóa sâu sau khi có đủ dữ liệu đối chứng và tiêu chí nghiệm thu.

## 9. Đề nghị quyết định của lãnh đạo

Đề nghị phê duyệt hướng phát triển MCP/API theo ba nguyên tắc:

1. AI được mở rộng khả năng quản lý dữ liệu và hỗ trợ quyết định trước khi mở rộng quyền lái máy thật.
2. Mọi quyền điều khiển máy phải tiếp tục qua PC Control tại chỗ, lease có thời hạn, audit và firmware phủ quyết.
3. Chưa phát hành cho khách hàng hoặc vận hành không giám sát cho đến khi hoàn tất kiểm thử phần cứng, capability theo biến thể máy và interlock cho các lệnh cơ cấu.

## 10. Kết luận

MCP Server và API của OTL Roast Lab đã vượt qua mức thử nghiệm đọc dữ liệu: hệ thống hiện có thể phân tích mẻ, quản lý cấu hình M1–M60 và gửi phần lớn lệnh điều khiển máy trong một chuỗi phân quyền nhiều lớp.

Đây là nền tảng có giá trị để xây dựng Roast Lab thành sản phẩm rang có trợ lý AI và truy xuất dữ liệu toàn diện. Trạng thái hiện tại phù hợp cho tiếp tục phát triển và kiểm thử có giám sát; chưa phù hợp để công bố là hệ thống AI tự vận hành máy rang ngoài thực tế.

---

## 11. Nhật ký vá ngày 09/09/2026

Đợt rà soát đối chiếu mã nguồn tìm ra bảy điểm; đã vá cả bảy, build và chạy lại
bộ kiểm ở mục 6.

| # | Vấn đề | Đã làm |
|---|---|---|
| 1 | Trần 15 phút không phải trần thật — khoá đang lái xin lại được ngay, lái vô tận không cần ai có mặt | Thêm **trần tổng 60 phút cho cả phiên PC control**; hết trần thì thợ phải tắt/bật lại PC control tại tủ |
| 2 | Nhịp tim tính cả GET đọc telemetry — vòng lặp poll còn chạy là đủ giữ quyền lái dù AI đã treo | Nhịp **chỉ tính hành động lái** (lệnh ghi hoặc `lease_beat`); thêm công cụ MCP `roaster_lai_nhip` để tác nhân đang cân nhắc giữ quyền một cách tường minh |
| 3 | Khoá chỉ có phạm vi `config` đổi được trần gas, gas mồi, nhiệt nạp — mà khối cấu hình chạy độc lập nút PC control | Nhóm $M lái lửa/nhiệt/cơ cấu nay **đòi thêm phạm vi `control`** |
| 4 | Ô lệnh PID gió không được phản chiếu: máy đang bật PID mà app ghi 0 để tắt thì không có gì xảy ra, giao diện vẫn báo đã tắt | Vá hai mảng gương thiếu 2 ô, và **thêm ô ĐỌC `vac_en`** để app có đường đọc lại trạng thái thật |
| 5 | Mỗi request API hợp lệ là một lần ghi lại `apikeys.json` — poll 1 Hz thành 86.400 lần ghi đĩa/ngày ngay trên máy đang bơm Modbus | Mốc "dùng lần cuối" cập nhật trong bộ nhớ, **ghi đĩa tối đa 5 phút một lần** |
| 6 | Khối đọc nới lên 23 ô sẽ làm app gặp firmware cũ rơi thẳng về khối gốc 16 ô, mất cân và profile mà máy vốn có | **Lùi từng nấc** 23 → 22 → 16; danh sách trường "máy chưa có" nay sinh tự động từ bản đồ, không chép tay |
| 7 | Mục 4 của báo cáo mô tả chuỗi an toàn kín hơn thực tế | Viết lại mục 4 theo đúng mã nguồn, thêm **mục 4.5 mô hình đe doạ** |

Bốn mục còn tồn về an toàn nằm ở mục 7 — chưa vá, đã ghi rõ mức nghiêm trọng.

