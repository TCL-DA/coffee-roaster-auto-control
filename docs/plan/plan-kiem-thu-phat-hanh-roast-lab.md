# Quy trình kiểm thử phát hành OTL Roast Lab

Ngày 29/09/2026. **Đã lập quy trình; chưa thực thi chiến dịch kiểm thử.**

## 1. Kiến trúc và phạm vi

App hiện dùng `OTL Roast Lab.html` (HTML/JS), `tools/roast_lab_hmi.py` (Python + pywebview), `tools/RoastLabHMI.spec` (PyInstaller). Windows dùng WebView2. Có web server/API, SQLite, PIN/tài khoản, license và giao tiếp máy rang. Không áp dụng bộ Electron/Tauri cho kiến trúc này.

Dữ liệu dev ở `tools/appdata`; bản đóng gói lưu dữ liệu cạnh EXE. Phải bảo vệ settings, hồ sơ, DB, tài khoản và license khi thử cập nhật. Chưa xác nhận gói desktop Mac; web client trên Mac không chứng minh desktop Mac hoạt động.

Căn cứ: [hướng dẫn QA](../../.claude/skills/rang-ca-phe/references/kiem-thu-phat-hanh-app.md), [đặc tả UI](../ui/2026-09-07-design-spec.md), code và test hiện hành. Áp dụng quy tắc trạng thái/accessibility từ `F:/Project/open-design/craft/`, không chạy engine thiết kế. Khi sửa HTML/test_ui phải theo [UI-LOCK](../ui/UI-LOCK.md). Báo cáo bằng chữ; không tự tạo bộ ảnh/video bàn giao.

## 2. Chuẩn bị

1. Người phụ trách phát hành ghi phiên bản, commit, thay đổi chưa commit, hash gói, firmware/protocol và nền tảng cam kết hỗ trợ.
2. QA dùng checkout, tài khoản/VM và dữ liệu thử riêng; ngắt máy rang thật khi chạy phần mềm. Đọc script trước khi chạy để biết nơi ghi dữ liệu, mở server, tạo ảnh hoặc gửi lệnh.
3. Dev sửa lỗi, QA chạy lại ca lỗi và nhóm chịu ảnh hưởng. Không đổi assertion chỉ để lấy màu xanh.
4. Phần cứng/gas/cơ cấu do người vận hành thử trong phạm vi được cho phép. Simulator không chứng minh an toàn máy thật.

Không chạy mù quáng `pytest tools/` hoặc toàn bộ `test_*.py`: dự án có nhiều kiểu test, một số cần app thật. Không dùng bộ requirements của Serial Terminal làm dependency đầy đủ cho Roast Lab.

## 3. Ma trận môi trường

| Môi trường | Nội dung | Trạng thái ban đầu |
|---|---|---|
| Windows x64 thấp nhất được hỗ trợ và bản hiện hành | Desktop/WebView2, API/web, portable, dữ liệu | Chưa thử |
| Windows cảm ứng | Giữ/nhả, hai ngón, mất focus, đeo găng | Chưa thử |
| macOS Apple Silicon | Web client; desktop cần gói Mac riêng | Chưa thử |
| Windows ARM64/Mac Intel | Bổ sung nếu cam kết hỗ trợ | Chưa xác nhận hỗ trợ |

Ghi rõ phiên bản OS, Python, pywebview, WebView2 và trình duyệt. Dùng máy thật cho USB/Serial/Bluetooth và Sleep/wake. Chromium trên Windows không thay thế Safari/macOS hoặc WebView2 native.

## 4. Tầng A — Logic và dữ liệu giả

Các lệnh sau đã đối chiếu tên script, chưa chạy trong lần lập quy trình. Chạy từ gốc repository trong môi trường thử có dependency phù hợp:

```powershell
python -X utf8 tools/test_roast_derive.py
python -X utf8 tools/test_otl_link.py
python -X utf8 tools/test_settings_file.py
python -X utf8 tools/test_inventory_rebase.py
python -X utf8 tools/test_lease_t2.py
```

Kiểm RoR/mốc, Modbus qua FakeSerial, cấu hình, kho SQLite tạm và quyền điều khiển qua bridge giả. `test_otl_link.py` có đường dẫn import Windows tuyệt đối: kiểm tra đúng checkout trước khi chạy máy khác. Import app có thể tạo log dev, vẫn cần cô lập.

Đạt: đúng kết quả/đơn vị, không trừ kho hai lần, mẻ gián đoạn không thành hoàn tất, thiếu quyền không lọt lệnh. Lỗi môi trường ghi BLOCKED.

## 5. Tầng B — Giao diện HTML bằng Playwright

Chuẩn bị Playwright trong virtual environment thử; cài Chromium nếu thiếu rồi chạy tuần tự:

```powershell
python -m playwright install chromium
python -X utf8 tools/test_ui_hold_confirm.py
python -X utf8 tools/test_ui_touch_hold.py
python -X utf8 tools/test_ui_step_accel.py
python -X utf8 tools/test_ui_autodrop.py
python -X utf8 tools/test_ui_performance.py
```

Ngưỡng giữ lấy từ yêu cầu đã duyệt và code hiện hành; không lấy tiêu đề/comment “1 giây” làm chuẩn. Chạy tuần tự để hạn chế sai timing do nghẽn CPU. Các bài có mock lệnh/bridge hoặc bỏ login chỉ chứng minh UI đang thử.

Theo thay đổi, đọc rồi bổ sung `test_ui_workflow.py`, `test_ui_deadstate.py`, `test_ui_profile_target.py`, `test_ui_ror.py`, `test_ui_portpick.py`, `test_ui_colors_fonts.py`, `test_ui_dialog_layout.py`. Kiểm tra nơi xuất artefact trước khi chạy.

Kiểm thủ công 5 trạng thái: đang tải/rỗng/lỗi/có dữ liệu/cực trị; lỗi giữ phần nhập và có cách khôi phục. Thử Tab/focus, nhãn, tương phản, dark/light, giảm chuyển động, DPI 100/150/200%, 1366×768 và 1920×1080. Đây là tập thử khởi đầu, không phải tuyên bố phạm vi hỗ trợ.

## 6. Tầng C — Backend, web và quyền

Mở app trong checkout riêng, không nối serial thật:

```powershell
python -X utf8 tools/roast_lab_hmi.py
```

Từ cửa sổ khác, xác nhận endpoint thuộc app thử rồi chạy:

```powershell
python -X utf8 tools/test_api_scope.py
python -X utf8 tools/test_api_login.py
```

Scope test tạo/xóa API key thử. Login test cần `OTL_TEST_USER` và `OTL_TEST_PIN` của tài khoản thử, không ghi secret vào repo/log. Thiếu server/biến môi trường có thể báo bỏ qua với exit 0: SKIP/BLOCKED, không PASS.

Đọc rồi bổ sung `test_web_pin.py`, `test_web_sync.py`, `test_web_pwa.py`, `test_apikey.py`, `test_telemetry_control_mcp.py`, `test_config_api_mcp.py` theo phạm vi. Không chạy đồng thời các bài dùng cùng dữ liệu/server/cổng.

Đạt: chỉ xem không ghi được; khóa sai/hết hạn/thu hồi bị từ chối; mất quyền chặn tại backend; log không lộ PIN; web/desktop đồng bộ. Login bị bypass ở tầng B không chứng minh tầng C.

## 7. Tầng D — Gói EXE và desktop native

Build trong bản sao checkout, kiểm nơi xuất để tránh ghi đè EXE đang dùng:

```powershell
python -m PyInstaller tools/RoastLabHMI.spec
```

Test EXE hiện cố định `tools/dist/OTL Roast Lab HMI.exe`, cổng 8555, đọc settings cạnh EXE, mở rồi dọn process. Xác nhận output build, đặt đúng gói vào đường dẫn test trong môi trường riêng và bảo đảm cổng chưa bị app khác chiếm.

```powershell
python -X utf8 tools/test_exe_end_to_end.py
Get-FileHash -Algorithm SHA256 -LiteralPath 'tools/dist/OTL Roast Lab HMI.exe'
```

Giới hạn: thiếu EXE có thể báo bỏ qua với exit 0; test dùng Chromium vào web do EXE phục vụ và mock một số lệnh. Nó không kiểm trọn WebView2 native hoặc chứng minh HTML khớp toàn bộ. Kiểm có mặt vài hàm không thay manifest/build và hash gói trước/sau chiến dịch.

Thử cửa sổ desktop thật: login tài khoản thử, dialog mở/lưu file, lưu settings, đóng/mở app, resize, nhiều màn hình, Sleep/wake và cổng thiết bị. Làm thủ công trước; cân nhắc FlaUI cho control phù hợp khi cần tự động hóa.

## 8. Tầng E — Phân phối, nâng cấp, bảo mật

- Máy Windows sạch có/không có WebView2: kiểm runtime và hướng dẫn cài thực tế.
- Portable ở đường dẫn có dấu/khoảng trắng; thiếu quyền/hết dung lượng phải báo rõ và giữ dữ liệu.
- Backup khi app đóng hoặc dùng backup SQLite nhất quán; không chỉ chép DB đang ghi và bỏ WAL. Nâng cấp từ bản còn hỗ trợ, đối chiếu mẻ/hồ sơ/kho/quyền/license.
- Migration từ vị trí cũ trong tài khoản thử phải giữ nguồn và không nhân đôi khi mở lần hai.
- License hợp lệ/sai chữ ký/hết hạn/chuyển máy theo chính sách thực tế. Updater/thanh toán chưa có thì ghi N/A có lý do hoặc khoảng trống của kênh phân phối.
- Quét dependency/secret/mã Python-JS; rà API, bind server, origin/CORS, PIN và LAN theo mô hình đe dọa. Không gửi dữ liệu khách ra dịch vụ ngoài.
- Windows: xác minh chữ ký/timestamp theo kênh phát hành; WACK khi phù hợp loại gói. Desktop Mac cần gói riêng và kiểm signing/notarization/Gatekeeper. Chưa có gói Mac thì chưa thể kết luận đạt.
- Smoke test gói cuối sau ký; loại test hook/mock. Thử phục hồi cập nhật tương thích migration, không hạ phiên bản mù quáng.

## 9. Tầng F — Kết nối, tải dài và phần cứng

Simulator trước: mất gói, phản hồi trễ/trùng/sai, stale, đổi cổng, mất server, crash, mất mạng và reconnect. Ca chưa có fault injection phải ghi cần bổ sung; FakeSerial không tự bao phủ mọi lỗi.

Sau đó bàn phần cứng và mẻ thật có người vận hành trong phạm vi được cho phép. Ghi model, firmware/map, bên giữ state machine, watchdog/chốt gas thực tế; đối chiếu code và protocol, không lấy ngưỡng từ reference cũ.

Tải dài tương đương ca vận hành dự kiến, số mẻ/dung lượng theo khách hàng. Chốt baseline/ngưỡng trước khi chạy; ghi RAM/CPU, độ trễ thao tác, số mẫu nhận/lưu và lệnh gửi. WPR/WPA hỗ trợ phân tích Windows. Test hồi quy DOM không thay thử tải dài.

## 10. Ca trọng yếu

| ID | Tình huống | Tiêu chí đạt | Tầng |
|---|---|---|---|
| R01 | Giữ/nhả sớm, hai ngón, mất focus | Không phát lệnh ngoài ý muốn; không tăng gas sau kết thúc cử chỉ | B/D/F |
| R02 | Tự xả khi cửa đã mở | Không đảo thành đóng cửa, không lặp do phản hồi trễ | B/F |
| R03 | Mất telemetry khi rang | Báo stale/mất kết nối; không coi số cũ là mới | C/F |
| R04 | Reconnect sau crash/Sleep | Đồng bộ quyền/trạng thái; không replay lệnh cũ | C/D/F |
| R05 | Tài khoản xem/khóa thiếu quyền | Backend từ chối ghi | C |
| R06 | Đóng mẻ khi mất kết nối | Gián đoạn khác hoàn tất theo đặc tả | A/C |
| R07 | Sửa khối lượng nhiều lần | Kho/đơn không trừ lặp | A/C |
| R08 | CSV lỗi, đường dẫn có dấu, dữ liệu cũ | Giữ dữ liệu gốc, báo lỗi rõ, đọc lại dữ liệu hợp lệ | A/D/E |
| R09 | Biên/thiếu trường/sai đơn vị | Đúng x10 nhiệt, %, Pa và địa chỉ protocol; thiếu không thành 0 hợp lệ | A/B/C |
| R10 | App mất liên lạc máy | Firmware/HMI đúng yêu cầu an toàn đã xác nhận | F |
| R11 | Nâng cấp/gián đoạn lúc ghi | Phục hồi nhất quán, đường quay lại đã thử | E |
| R12 | Nhiều mẻ/dữ liệu lớn | Không tăng tài nguyên vô hạn, mất mẫu, lặp lệnh | C/D/F |

## 11. Lịch và điều kiện phát hành

Mỗi thay đổi: A/B liên quan; thay API thêm C, thay native/đóng gói thêm D/E. Ứng viên phát hành: A→B→C→D→E; F theo chức năng điều khiển và thay đổi, giữ bằng chứng phần cứng còn áp dụng; beta với người dùng đại diện trên gói định danh.

Chặn phát hành nếu sai lệnh/quyền, mất dữ liệu, không cài/mở trên nền tảng cam kết, luồng chính thất bại hoặc lỗ hổng nghiêm trọng chưa xử lý. Ca trọng yếu chưa thử là NOT RUN/BLOCKED, không PASS vì exit 0/mock xanh. Chỉ kết luận cho nền tảng đã thử; có phương án phục hồi update và kênh nhận lỗi. Quy trình không tự xuất bản/flash máy.

## 12. Mẫu báo cáo

```text
Build/commit/thay đổi chưa commit:
Gói + SHA-256:
OS/CPU/runtime/trình duyệt:
Firmware/protocol/model:
Fixture/cách cô lập/baseline:
ID/test/lệnh:
Kỳ vọng và thực tế:
Exit code/có SKIP không:
PASS / FAIL / BLOCKED / NOT RUN / N/A (lý do):
Bằng chứng/log đã loại secret:
Lỗi/tác động/người xử lý/test hồi quy:
Kết luận theo từng nền tảng:
```

Báo cáo phát triển: `docs/analysis/analysis-qa-roast-lab-<build>.md`. Log/fixture ở môi trường thử; không commit dữ liệu khách/secret. Chưa tạo báo cáo PASS khi chưa chạy.

Khoảng trống hiện chưa có bằng chứng: native Mac, toàn bộ WebView2 bridge, fault injection đầy đủ, tải dài, gói ký và migration các bản cũ. Đây là phần cần thử, không phải kết luận app đang lỗi. Nguồn công cụ/phân phối nằm trong reference QA; kiểm lại tài liệu hãng khi triển khai.
