# Kiểm thử Roast Lab trước khi phát hành thương mại

Áp dụng cho dự án: [Quy trình kiểm thử OTL Roast Lab](../../../../docs/plan/plan-kiem-thu-phat-hanh-roast-lab.md), gồm kiến trúc pywebview/PyInstaller, lệnh test có sẵn, ca trọng yếu và mẫu báo cáo.

Tổng hợp từ nghiên cứu ngày 28/09/2026. Dùng khi lập kế hoạch kiểm thử hoặc đánh giá bản phát hành Windows/macOS. Đây là hướng dẫn QA; không tự cấp quyền xuất bản, mua dịch vụ, gửi báo cáo ra ngoài hay điều khiển máy thật.

## Xác định đối tượng kiểm thử

- Đọc cấu hình build và mã hiện hành để xác định app là web/PWA, Electron, Tauri, .NET, Qt hay native macOS. Không suy ra framework từ tên Roast Lab hoặc mặc định app đã có bộ cài desktop.
- Ghi commit/build, phiên bản firmware/protocol tương thích, hệ điều hành/kiến trúc được hỗ trợ, cấu hình tối thiểu và kênh phân phối website/Store.
- Phân biệt đặc tả mong muốn với hành vi đang triển khai. Các reference OTL có thể cũ; đối chiếu code trước khi đặt kỳ vọng. Không tự sửa state machine cho khớp tài liệu.
- Khi đụng UI, tuân thủ Open Design, đặc tả và UI-LOCK của dự án. Báo cáo bằng chữ; không tạo ảnh/video bàn giao nếu chưa được yêu cầu.

## Chọn công cụ theo framework

| Đối tượng | Công cụ nên cân nhắc | Giới hạn cần giữ |
|---|---|---|
| Web/PWA | Playwright cho luồng trình duyệt | Vẫn thử cài PWA, quyền thiết bị và hành vi trên hệ điều hành thực |
| Electron | Playwright Electron | Hỗ trợ được ghi là experimental; kiểm tra tương thích phiên bản |
| Tauri | WebdriverIO + Tauri service | Tài liệu hiện hỗ trợ macOS qua server nhúng; tauri-driver trực tiếp chỉ Windows/Linux. Loại công cụ điều khiển dành cho test khỏi bản bán |
| Windows .NET/WPF/WinForms | FlaUI UIA2/UIA3 | Chọn backend phù hợp control; không giả định mọi control đều truy cập được |
| macOS native | XCTest + XCUIAutomation | Chạy kiểm thử trên macOS |
| Qt/C++ | Squish | Công cụ thương mại; đánh giá nhu cầu và giấy phép trước khi chọn |

Chọn một bộ GUI phù hợp, kết hợp test logic và tích hợp theo ngôn ngữ dự án. Ưu tiên assertion về dữ liệu/trạng thái, không chỉ click thành công. Tái sử dụng test có sẵn khi phù hợp; không chạy mọi test firmware cho thay đổi tài liệu.

## Các nhóm kiểm thử

### Chức năng, dữ liệu và thương mại

- Luồng cốt lõi: tạo hồ sơ → lưu → đóng → mở lại; import/export; ghi và đọc lại lịch sử mẻ. Kiểm tra kết quả số và đơn vị.
- Dữ liệu cũ qua nâng cấp, tệp lỗi/rỗng/lớn, tên tiếng Việt, dấu thập phân và múi giờ. Lỗi đọc/ghi phải có thông báo và giữ được dữ liệu gốc.
- Nếu có tài khoản/bản quyền: đăng nhập, token hết hạn, kích hoạt, hết hạn trial, gia hạn, offline và lỗi dịch vụ. Dùng môi trường thanh toán thử khi cần.

### Bản cài và cập nhật

- Thử đúng gói dự kiến giao khách trên máy sạch, tài khoản thường và môi trường không có công cụ phát triển.
- Cài mới, mở lần đầu, nâng cấp từ phiên bản còn hỗ trợ, gỡ/cài lại; giữ dữ liệu và giấy phép theo chính sách sản phẩm.
- Thử thiếu dung lượng, quyền ghi bị từ chối, tải gói hỏng và gián đoạn cập nhật. Updater phải từ chối gói không hợp lệ; kiểm tra cơ chế phục hồi tương thích với migration dữ liệu, không hạ phiên bản mù quáng.
- Thử gói tải xuống thực tế trên máy khác máy build; ghi bằng chứng gắn với phiên bản/hash gói cuối.

### Tương thích, hiệu năng và khả năng tiếp cận

- Lập ma trận hệ điều hành/CPU theo phạm vi cam kết; ưu tiên bản thấp nhất được hỗ trợ và bản hiện hành. Dùng máy thật cho USB/Serial/Bluetooth, GPU và Sleep/wake.
- Thử nhiều màn hình/DPI, bàn phím tiếng Việt, Tab/focus, screen reader và quyền truy cập bị từ chối.
- Đo thời gian mở app, CPU/RAM lúc nhàn rỗi và khi xử lý dữ liệu lớn; chạy đủ lâu để tìm tăng RAM liên tục, treo và mất mẫu telemetry. Đặt ngưỡng theo nhu cầu sản phẩm và máy tối thiểu, không bịa một ngưỡng chung.
- Windows: WPR/WPA để phân tích hiệu năng; Application Verifier khi có mã unmanaged. Accessibility Insights for Windows và Accessibility Inspector trên Mac hỗ trợ kiểm tra accessibility.

### Kết nối máy rang

- Bắt đầu bằng simulator/replay và fault injection: mất kết nối, timeout, phản hồi trễ/trùng, dữ liệu sai/đứt gói, rút/cắm cổng, app crash và Sleep/wake.
- Kiểm tra x10 nhiệt, phần trăm 0–100, Pa, địa chỉ 1-based/0-based theo protocol thực tế. Không nhầm trạng thái cũ với telemetry mới.
- Sau reconnect, kiểm tra quyền điều khiển và đồng bộ trạng thái; không phát lại lệnh cơ cấu/gas cũ ngoài ý muốn. Thử thao tác lặp để phát hiện lệnh bị thực thi hai lần.
- Xác định bên giữ state machine từ code/firmware đang chạy. Kiểm tra watchdog, chốt gas và quyền tiếp quản theo yêu cầu đã xác nhận; không lấy các mốc thời gian trong reference cũ làm chân lý.
- Test trên máy thật có nhiệt/gas/cơ cấu cần phạm vi vận hành được người dùng cho phép và điều kiện kiểm soát phù hợp. Kết quả simulator không chứng minh an toàn phần cứng; ghi rõ phần chưa thử.

## Bảo mật và yêu cầu nền tảng

- Quét mã, dependency và secret bằng công cụ phù hợp như CodeQL/dependency review/secret scanning; kiểm tra quyền sử dụng và ngôn ngữ được hỗ trợ. Đánh giá quyền truy cập, IPC/API, thông tin nhạy cảm trong log và xác thực gói cập nhật.
- Electron cần kiểm tra riêng theo hướng dẫn security chính thức; không coi test giao diện là kiểm thử bảo mật.
- Windows: ký và xác minh chữ ký bằng SignTool; Windows App Certification Kit khi phù hợp loại gói/kênh phân phối. Chữ ký không bảo đảm không có cảnh báo hay không có lỗi.
- macOS phát hành trực tiếp: Developer ID signing, notarization và kiểm tra Gatekeeper với bản tải xuống; theo quy trình Apple hiện hành. Notarization không thay thế test chức năng.
- CI chạy test phù hợp trên Windows/macOS và lưu kết quả theo build. Chạy lại smoke test trên gói cuối sau đóng gói/ký; không chỉ kiểm tra bản dev có mock hoặc công cụ test nhúng.

## Beta và tiêu chí phát hành

Cho người dùng đại diện thử công việc thực tế; TestFlight là một lựa chọn cho Mac khi phù hợp kênh phân phối. Thu thập lỗi kèm phiên bản, môi trường, bước tái hiện và log đã loại thông tin nhạy cảm.

Đề xuất chặn phát hành khi còn lỗi mất dữ liệu, không cài/mở được, sai quyền/lệnh điều khiển, lỗ hổng nghiêm trọng chưa xử lý hoặc luồng chính không hoàn thành. Các trường hợp chưa test phải ghi là chưa test, không tính pass.

Báo cáo QA gồm: build và phạm vi, môi trường đã thử, pass/fail/chưa thử, lỗi kèm bằng chứng và tác động, kết luận sẵn sàng/chưa sẵn sàng, phương án phục hồi cập nhật. Dùng mẫu này cho QA thay mẫu cupping/thử mẻ của skill. Kết luận sẵn sàng không tự thực hiện phát hành.

## Nguồn chính thức

Khả năng công cụ và yêu cầu Store có thể thay đổi; kiểm tra lại khi triển khai.

- [Playwright Electron](https://playwright.dev/docs/api/class-electron)
- [Tauri WebDriver](https://v2.tauri.app/develop/tests/webdriver/)
- [FlaUI](https://github.com/FlaUI/FlaUI)
- [Apple XCUIAutomation](https://developer.apple.com/documentation/XCUIAutomation)
- [Squish](https://doc.qt.io/squish/)
- [WPR/WPA](https://learn.microsoft.com/en-us/troubleshoot/windows-server/support-tools/support-tools-xperf-wpa-wpr)
- [Application Verifier](https://learn.microsoft.com/en-us/windows-hardware/drivers/devtest/application-verifier)
- [GitHub security](https://docs.github.com/en/code-security/reference)
- [Electron security](https://www.electronjs.org/docs/latest/tutorial/security)
- [Accessibility Insights](https://accessibilityinsights.io/docs/windows/getstarted/automatedchecks/)
- [Accessibility Inspector](https://developer.apple.com/documentation/accessibility/accessibility-inspector)
- [SignTool](https://learn.microsoft.com/en-us/windows/win32/seccrypto/signtool)
- [Windows App Certification Kit](https://learn.microsoft.com/en-us/windows/uwp/debug-test-perf/windows-app-certification-kit)
- [Apple notarization](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution)
- [Đóng gói ứng dụng Mac](https://developer.apple.com/documentation/xcode/packaging-mac-software-for-distribution)
- [TestFlight](https://developer.apple.com/testflight/)
