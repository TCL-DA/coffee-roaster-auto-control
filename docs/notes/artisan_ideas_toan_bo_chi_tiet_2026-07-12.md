# Toàn bộ ý tưởng trong GitHub Discussions — Artisan / Ideas

> **Nguồn chính:** [artisan-roaster-scope/artisan — Discussions — Ideas](https://github.com/artisan-roaster-scope/artisan/discussions/categories/ideas)  
> **Thời điểm kiểm tra:** 12/07/2026  
> **Phạm vi:** 27 cuộc thảo luận, gồm 22 chủ đề đang mở và 5 chủ đề đã đóng  
> **Ngôn ngữ tài liệu:** Tiếng Việt

## Lưu ý về cách biên soạn

Tài liệu này **trích lọc và diễn giải chi tiết toàn bộ nội dung có ý nghĩa** trong từng cuộc thảo luận: bài đăng mở đầu, ví dụ, yêu cầu kỹ thuật, phản hồi của cộng đồng, giải thích của maintainer, cách làm thay thế, kết quả thử nghiệm và trạng thái cuối cùng. Nội dung không được sao chép nguyên văn hàng loạt; thay vào đó, nó được dịch và thuật lại sát nghĩa để dễ đọc, dễ tìm kiếm và dùng làm tài liệu phát triển sản phẩm.

Một số luồng GitHub có các nhánh trả lời bị giao diện khách chưa đăng nhập thu gọn bằng dòng “Show previous replies”. Với các luồng đó, tài liệu ghi đầy đủ phần nội dung công khai đọc được, các kết luận xuất hiện sau nhánh bị thu gọn, đồng thời đánh dấu rõ giới hạn thay vì tự suy đoán phần văn bản không truy cập được.

---

# Mục lục nhanh

1. [#1467 — Getting Started W Artisan and Kaleido](#1-1467--getting-started-w-artisan-and-kaleido)
2. [#2132 — Linking the settings file path to the alog](#2-2132--linking-the-settings-file-path-to-the-alog)
3. [#2112 — Roast designer controls](#3-2112--roast-designer-controls)
4. [#2100 — Artisan for Ikawa Home](#4-2100--artisan-for-ikawa-home)
5. [#2084 — Increase/Decrease Burner Power by % relative to current value](#5-2084--increasedecrease-burner-power-by--relative-to-current-value)
6. [#2012 — More space between Windows 11 taskbar and buttons](#6-2012--more-space-between-windows-11-taskbar-and-buttons)
7. [#1969 — How long is the X-axis?](#7-1969--how-long-is-the-x-axis)
8. [#1979 — Informational tips for Tooltip display mode](#8-1979--informational-tips-for-tooltip-display-mode)
9. [#1915 — Organizing the button layout in the event table](#9-1915--organizing-the-button-layout-in-the-event-table)
10. [#1934 — Readings imported (from??)](#10-1934--readings-imported-from)
11. [#1884 — Switching between Artisan PID and Roaster PID](#11-1884--switching-between-artisan-pid-and-roaster-pid)
12. [#1821 — Six sliders instead of four](#12-1821--six-sliders-instead-of-four)
13. [#1782 — Bluetooth LE profile template](#13-1782--bluetooth-le-profile-template)
14. [#936 — Charting Phidgets HUM1001 stack humidity](#14-936--charting-phidgets-hum1001-stack-humidity)
15. [#1551 — Headless style operation](#15-1551--headless-style-operation)
16. [#1474 — Posting status: Open/Closed and utility of conversation](#16-1474--posting-status-openclosed-and-utility-of-conversation)
17. [#1443 — Better decaf roasts with advanced alarms](#17-1443--better-decaf-roasts-with-advanced-alarms)
18. [#1035 — Add support for PICO TC08](#18-1035--add-support-for-pico-tc08)
19. [#1102 — Display DTR comparison](#19-1102--display-dtr-comparison)
20. [#1083 — Artisan Command for setting symbolic ET/BT](#20-1083--artisan-command-for-setting-symbolic-etbt)
21. [#1038 — Dark Mode for Artisan](#21-1038--dark-mode-for-artisan)
22. [#955 — Support for Yoctopuce Yocto-Watt](#22-955--support-for-yoctopuce-yocto-watt)
23. [#1025 — Positionable Statistics Summary](#23-1025--positionable-statistics-summary)
24. [#985 — Modify events by BT, not time](#24-985--modify-events-by-bt-not-time)
25. [#997 — Controlling WebSocket devices](#25-997--controlling-websocket-devices)
26. [#856 — Playback Events On/Off shortcut](#26-856--playback-events-onoff-shortcut)
27. [#788 — “Show full” in Comparator](#27-788--show-full-in-comparator)
28. [Tổng hợp các nhóm ý tưởng lớn](#tổng-hợp-các-nhóm-ý-tưởng-lớn)

---

# Bảng tổng quan

| STT | Discussion | Chủ đề rút gọn | Trạng thái khi kiểm tra | Kết quả chính |
|---:|---:|---|---|---|
| 1 | #1467 | Cơ sở dữ liệu profile/bean/machine | Mở | Hữu ích nhưng nhóm Artisan không có nguồn lực xây dựng; cộng đồng chỉ ra Roastetta |
| 2 | #2132 | Liên kết file setting với `.alog` | Đóng | Maintainer giải thích setting là trạng thái ứng dụng, không phải một file cố định |
| 3 | #2112 | Thiết kế và tự động chạy profile | Mở | Artisan đã làm được bằng playback, Alarm, PID và Artisan Command; cấu hình của người dùng được sửa thành công |
| 4 | #2100 | IKAWA Home | Mở | Đọc dữ liệu được; gửi profile chưa được hỗ trợ; cần đóng góp mã nguồn |
| 5 | #2084 | Điều chỉnh burner theo phần trăm tương đối | Mở | Chưa có lệnh tích hợp; có thể dùng script ngoài qua Call Program |
| 6 | #2012 | Khoảng cách nút với taskbar Windows 11 | Mở | Đã thêm bằng commit `0e6b474` |
| 7 | #1969 | Trục X kéo dài nhiều giờ/ngày | Mở | Khoảng lấy mẫu dài hơn và trục thời gian lớn hơn được chuẩn bị cho bản kế tiếp |
| 8 | #1979 | Tooltip hướng dẫn Characteristics | Đóng | Đề xuất bắt nguồn từ việc tính năng nhấp chuột phải khó được khám phá |
| 9 | #1915 | Tổ chức bố cục Event Buttons | Mở | Có quy tắc tương thích mới; continuous build sửa bố cục và người dùng xác nhận hoàn hảo |
| 10 | #1934 | Hiện tên file CSV đã import | Đóng | Tên đường dẫn có trong Messages; maintainer đồng ý thêm tên CSV trong bản kế tiếp |
| 11 | #1884 | Chuyển PID Artisan/PID máy bằng nút | Mở | Chưa có Artisan Command; người dùng muốn tránh phải đổi SlaveID thủ công |
| 12 | #1821 | Tăng từ 4 lên 6 slider/event type | Đóng | Maintainer từ chối; Artisan sẽ giữ tối đa 4 named event types |
| 13 | #1782 | Mẫu BLE chung | Đóng | Có thể làm qua PR/đề xuất kỹ thuật; chưa có triển khai trong luồng |
| 14 | #936 | Đồ thị độ ẩm khí thải | Mở | Dữ liệu thú vị nhưng cảm biến, độ trễ, nhiệt độ và bụi làm giảm tính hành động thực tế |
| 15 | #1551 | Chạy headless/backend | Mở | Artisan là ứng dụng nguyên khối; khó tách backend/frontend |
| 16 | #1474 | Đóng chủ đề có làm mất thảo luận? | Mở | Đặt câu hỏi về quy trình diễn đàn, không có phản hồi |
| 17 | #1443 | Rang decaf tự động bằng Alarm | Mở | Chia sẻ quy trình, video và file cấu hình; không có phản hồi |
| 18 | #1035 | Pico TC-08 | Mở | Người dùng tự phát triển mã macOS và công bố repository; chưa thấy xác nhận merge chính thức |
| 19 | #1102 | So sánh DTR của background | Mở | Chỉ có yêu cầu, chưa có phản hồi |
| 20 | #1083 | Đổi Symbolic ET/BT theo mẻ | Mở | Không cần tính năng mới; giải quyết bằng công thức có điều kiện và `WEIGHTin` |
| 21 | #1038 | Dark Mode | Mở | Bị phụ thuộc hỗ trợ dark mode của Qt; chưa có kết quả trong luồng |
| 22 | #955 | Yocto-Watt | Mở | Nhóm mở cửa nhận PR; người đề xuất muốn thuê lập trình viên |
| 23 | #1025 | Kéo thả Statistics Summary | Mở | Có cách giảm che khuất bằng Auto Axis và giới hạn ký tự; kéo thả được ghi vào danh sách |
| 24 | #985 | Sửa Event theo BT | Mở | Bị từ chối do một nhiệt độ có thể xuất hiện nhiều lần; dùng cursor/time làm cách thay thế |
| 25 | #997 | Gửi lệnh qua WebSocket | Mở | Artisan đã có WebSocket Command gửi JSON; cấu hình hiện tại giải quyết được nhu cầu PID setpoint |
| 26 | #856 | Nút bật/tắt Playback | Mở | Đã có phím `j` và Artisan Command `playbackmode`; có thể tạo nút cảm ứng |
| 27 | #788 | Hiển thị BBP đầy đủ trong Comparator | Mở | Đã triển khai, sau đó sửa thêm lỗi trục thời gian; người dùng xác nhận hoàn hảo |

---

# Chi tiết từng cuộc thảo luận

## 1. #1467 — Getting Started W Artisan and Kaleido

- **Nguồn:** https://github.com/artisan-roaster-scope/artisan/discussions/1467
- **Người mở:** `asarule`
- **Ngày mở:** 26/02/2024
- **Trạng thái:** Mở
- **Quy mô luồng:** Bài mở đầu và 2 bình luận

### Yêu cầu ban đầu

Người dùng đặt câu hỏi liệu cộng đồng Artisan có một nguồn tham khảo tập trung cho các tổ hợp **profile rang – loại hạt – máy rang** hay không, lý tưởng nhất là một cơ sở dữ liệu trực tuyến có khả năng tìm kiếm. Họ lấy hệ sinh thái Aillio Bullet làm ví dụ: Roast.World cho phép người dùng chia sẻ và tìm các mẻ rang trên cùng một nền tảng máy, nhờ đó người mới có một điểm khởi đầu rõ ràng.

Người đề xuất hiểu rằng Artisan phức tạp hơn vì hỗ trợ rất nhiều máy rang, đầu dò, kiểu truyền nhiệt, khối lượng mẻ và phương thức điều khiển. Tuy vậy, chính sự đa dạng đó lại khiến người mới khó tìm một profile đủ gần với máy và nguyên liệu của mình. Họ cho rằng một thư viện cộng đồng sẽ giảm chi phí “học phí” do những mẻ thất bại, đặc biệt đối với người mới dùng Artisan và Kaleido.

### Phản hồi trong luồng

`CarefreeBuzzBuzz`, với vai trò cộng tác viên, cho biết ý tưởng tương tự đã từng được thử trước đây. Vấn đề không nằm ở việc ý tưởng thiếu giá trị, mà ở chỗ nhóm Artisan hiện không có nguồn lực để xây dựng, chuẩn hóa, kiểm duyệt và duy trì một kho dữ liệu như vậy.

Một phản hồi xuất hiện về sau, từ `prmango43`, hướng người dùng tới **Roastetta** — một dịch vụ bên ngoài có thể lưu và chia sẻ dữ liệu rang, bao gồm cả các máy Kaleido và những nền tảng khác. Điều này không đồng nghĩa Roastetta là cơ sở dữ liệu chính thức của Artisan, nhưng là lựa chọn gần nhất với nhu cầu được nêu.

### Kết luận và ý nghĩa

Đề xuất vẫn mở, nhưng không có cam kết triển khai từ nhóm Artisan. Khó khăn thực tế của một thư viện profile không chỉ là lưu file; hệ thống còn phải mô tả và lọc theo máy, kích thước mẻ, vị trí đầu dò, loại hạt, độ ẩm, mật độ, quy trình sơ chế, mục tiêu màu rang, điều kiện môi trường và phiên bản cấu hình. Nếu không chuẩn hóa metadata, người dùng rất dễ áp dụng nhầm profile.

**Ý tưởng sản phẩm rút ra:** một app máy rang có thể tạo lợi thế lớn nếu tự động thu thập metadata của máy, hạt và mẻ rang, rồi cho phép tìm “mẻ tương tự” thay vì chỉ chia sẻ một đường cong thời gian–nhiệt độ trần.

---

## 2. #2132 — Linking the settings file path to the alog

- **Nguồn:** https://github.com/artisan-roaster-scope/artisan/discussions/2132
- **Người mở:** `prmango43`
- **Ngày mở:** 23/02/2026
- **Trạng thái:** **Đã đóng**
- **Quy mô luồng:** 1 bình luận chính và 11 nhánh trả lời; 6 trả lời cũ bị giao diện khách thu gọn

### Bối cảnh và yêu cầu

Người dùng gặp một mẻ rang có các Event bất thường trên Kaleido M2S. Khi được yêu cầu gửi cả file cấu hình `.aset` và file log `.alog` tương ứng để chẩn đoán, họ nhận ra mình không chắc file setting nào đã được dùng cho mẻ rang đó. Vì vậy, họ đề nghị khi ghi `.alog`, Artisan nên thêm đường dẫn tới file `.aset` liên quan.

Mục tiêu của người đề xuất khá hẹp: không yêu cầu lưu lịch sử mọi thay đổi cấu hình, chỉ muốn một dòng đường dẫn giúp ghép cặp log với file setting mà họ cho rằng đang được dùng.

### Giải thích nền tảng của maintainer

`MAKOMO` giải thích rằng giả định “mỗi mẻ rang tương ứng với một file setting” không đúng với kiến trúc của Artisan:

1. Setting của Artisan là **trạng thái đang sống của ứng dụng**, được hệ điều hành lưu lại giữa các lần chạy.
2. Người dùng có thể thay đổi trạng thái đó trực tiếp trong giao diện mà không hề xuất ra file `.aset`.
3. Trạng thái còn có thể thay đổi ngay trong lúc đang rang.
4. File `.aset` chỉ xuất hiện khi người dùng chủ động **Export Settings** tại một thời điểm cụ thể.
5. Vì vậy, “file setting được load gần nhất” không đảm bảo đại diện cho cấu hình thật sự tại thời điểm mẻ rang diễn ra.

Maintainer phân biệt rõ:

- **App settings:** trạng thái ứng dụng như cấu hình thiết bị, giao diện, vị trí cửa sổ và nhiều tham số đang hoạt động; hệ điều hành quản lý việc lưu trạng thái này.
- **App data:** dữ liệu mẻ rang được lưu trong `.alog`, tương tự tài liệu mà một trình soạn thảo văn bản lưu ra file.

Artisan đã ghi tên file setting được load gần nhất vào `.alog` chủ yếu cho mục đích debug, nhưng dữ liệu đó không phải bằng chứng hoàn chỉnh rằng toàn bộ trạng thái lúc rang giống hệt file ấy.

### Các phương án được cộng đồng bàn tới

`mrpenner` đề xuất hai hướng:

- Artisan tự lưu một `.aset` cho từng mẻ rang.
- Hoặc tự tạo bản sao setting có timestamp mỗi khi cấu hình thay đổi, sau đó đối chiếu thời gian mẻ rang với lịch sử setting.

Người này cũng tự nhận rằng lưu một file cho mỗi mẻ có thể quá nặng và không cần thiết với đa số người dùng. Lưu mỗi lần thay đổi thì chính xác hơn, nhưng tạo ra bài toán quản lý phiên bản, dung lượng và xác định thời điểm hiệu lực.

Người mở chủ đề nhấn mạnh họ chỉ cần đường dẫn đơn giản vì yêu cầu phát sinh từ quá trình support. Sau khi thấy các phương án đều phức tạp hoặc không đúng ý ban đầu, họ chấp nhận chủ đề đã bị đóng và dừng theo đuổi.

### Kết luận

Đề xuất bị đóng không phải vì nhu cầu truy vết cấu hình vô lý, mà vì **mô hình dữ liệu được đề xuất không phản ánh đúng nguồn sự thật**. Một đường dẫn file không thể đại diện cho trạng thái cấu hình đã bị sửa sau khi load.

**Ý tưởng sản phẩm rút ra:** để hỗ trợ hậu mãi tốt, app máy rang nên lưu một **configuration snapshot bất biến** ngay trong log mỗi mẻ, hoặc lưu hash/version ID của snapshot. Snapshot nên bao gồm toàn bộ thông số điều khiển có ảnh hưởng tới mẻ rang, thay vì chỉ lưu tên file cấu hình cuối cùng.

---

## 3. #2112 — Roast designer controls

- **Nguồn:** https://github.com/artisan-roaster-scope/artisan/discussions/2112
- **Người mở:** `LukeRoaster`
- **Thời gian thảo luận chính:** 02–24/02/2026
- **Trạng thái:** Mở
- **Kết quả:** Người dùng cấu hình thành công và dự định áp dụng cho máy 30 kg

### Mong muốn ban đầu

Người dùng vận hành các máy Giesen đời cũ và muốn có một công cụ “thiết kế profile” trực quan, nơi họ có thể khai báo các thay đổi điều khiển theo **BT** thay vì phải thao tác thủ công. Kịch bản mẫu của họ gồm:

- Nạp hạt với các mức fan, drum và burner ban đầu.
- Giữ burner 0% trong khoảng 30 giây đầu.
- Sau đó đưa burner lên 100%.
- Khi BT đạt khoảng 130°C, giảm burner xuống 90%.
- Ở 140°C, tiếp tục giảm còn 80%.
- Gần First Crack, khoảng 182°C, bắt đầu giảm nhiệt từng bước.
- Tiếp tục hạ công suất cho tới 0%.
- Drop khi BT đạt khoảng 199°C.

Điểm cốt lõi là người dùng muốn chuyển tư duy rang thành một chuỗi điều kiện có thể thiết kế, lưu, thử và phát lại.

### Phản hồi của maintainer: Artisan đã có các khối cần thiết

`MAKOMO` giải thích Artisan vốn được xây dựng để tự động hóa. Có nhiều lớp công cụ:

1. **Playback Background Events:** phát lại các Event của profile nền theo thời gian hoặc theo nhiệt độ.
2. **Alarm system:** tạo luật dựa trên time, BT, ET, TP, FC và các điều kiện khác; mỗi luật có thể kích hoạt hành động nội bộ hoặc gửi lệnh tới máy.
3. **Custom Event Buttons / Artisan Commands:** đóng gói lệnh điều khiển thành nút hoặc hành động tái sử dụng.
4. **Artisan PID:** điều khiển bám theo đường mục tiêu; có thể kết hợp với các bước thay đổi theo nhiệt độ.
5. **Simulator:** thử toàn bộ luật mà không làm hỏng hạt thật.

Maintainer còn dựng một bảng Alarm mẫu cho kịch bản giảm burner, cho thấy yêu cầu không nhất thiết cần một module hoàn toàn mới.

### Sự cố khi người dùng tự cấu hình

Sau khi thử nghiệm, người dùng báo hệ thống hoạt động không ổn định:

- Drum setting đầu mẻ không đổi như mong muốn.
- Burner bật 100% ở 1:15 thì hoạt động.
- Một số mức nhiệt như 145°C, 170°C và 180°C kích hoạt được, nhưng các mức khác bị bỏ qua.
- Máy Giesen của họ chỉ hiển thị BT số nguyên, nên họ nghĩ điều kiện bằng đúng một số nguyên phải đủ an toàn.
- Họ thử nhiều tổ hợp `If Alarm` và `But Not` nhưng chưa hiểu rõ quan hệ giữa các luật.

### Phân tích chi tiết của MAKOMO

Maintainer chỉ ra từng lỗi logic:

#### 1. Ba Alarm đầu không thể chạy

Người dùng để `SOURCE` trống, nghĩa là vô hiệu điều kiện nhiệt độ. Đồng thời time là `00:00`, mà trong hệ thống Alarm lại được hiểu là điều kiện thời gian bị tắt. Khi cả hai nguồn kích hoạt đều bị tắt, luật không bao giờ chạy. Cách sửa là dùng thời gian như `00:01` để các lệnh thiết lập đầu mẻ thực sự có điều kiện kích hoạt.

#### 2. Luật bật burner lúc 1:15 là hợp lệ

Luật số 4 mã hóa đúng yêu cầu và vì vậy nó là phần hiếm hoi luôn chạy ổn định.

#### 3. Luật bắt TP/RoR không cần thiết và dễ sai

Người dùng tạo một luật trung gian dựa trên RoR để chờ Turning Point. Maintainer lưu ý RoR thường bị trễ do bộ lọc nhiễu. Thay vì tạo luật vòng vo, các luật sau có thể đặt trực tiếp `From = TP`, nhờ đó chúng chỉ được phép hoạt động sau Turning Point.

#### 4. Ý nghĩa của `If Alarm` và `But Not`

- `If Alarm = N`: khóa luật hiện tại cho tới khi luật N đã được thực thi.
- `But Not = N`: khóa luật hiện tại nếu luật N đã được thực thi.

Người dùng đã dùng `But Not` theo cách khiến các bước sau vô tình tự chặn nhau. Trong kịch bản giảm burner tuần tự, maintainer khuyên đặt `But Not = 0`; phần lớn trường hợp cũng không cần xâu chuỗi bằng `If Alarm` nếu mỗi luật đã có ngưỡng BT riêng và chỉ được chạy sau TP.

#### 5. Không nên dùng điều kiện `BT = 120°C`

Ngay cả khi máy chỉ hiển thị số nguyên, chu kỳ lấy mẫu có thể chuyển từ 119°C sang 121°C mà không bao giờ tạo mẫu đúng 120°C. Vì vậy, luật `=` sẽ bị bỏ qua. Nên dùng `BT > 120°C`. Mỗi Alarm chỉ chạy một lần nên điều kiện `>` không khiến lệnh lặp vô hạn.

Cấu hình khuyến nghị cho các bước 6–14 là:

- Source: BT.
- Condition: `>`.
- From: TP.
- But Not: 0.
- Không dùng quan hệ phụ không cần thiết giữa các bước.

### Kết quả cuối cùng

Người dùng xác nhận cấu hình mới đã hoạt động. Họ hiểu được cách giải thích và dự định sao chép logic sang máy rang 30 kg. Maintainer chúc họ thành công.

### Giá trị kỹ thuật rút ra

Đây là một trong những luồng giàu giá trị nhất của mục Ideas. Nó cho thấy một hệ thống tự động hóa mạnh vẫn có thể tạo cảm giác “thiếu tính năng” nếu giao diện rule engine khó hiểu. Các điểm cần cải thiện cho app máy rang:

- Trình thiết kế profile dạng timeline/temperature map thay vì bảng Alarm thuần túy.
- Cảnh báo ngay khi một rule không có trigger hợp lệ.
- Cảnh báo khi dùng `=` với dữ liệu cảm biến liên tục.
- Hiển thị quan hệ khóa/phụ thuộc giữa các rule bằng sơ đồ.
- Chế độ simulation và event trace giải thích vì sao một rule đã hoặc chưa chạy.
- Template “sau TP”, “trước FC”, “mỗi rule chạy một lần” để người dùng không phải hiểu toàn bộ thuật ngữ nội bộ.

---

## 4. #2100 — Artisan for Ikawa Home

- **Nguồn:** https://github.com/artisan-roaster-scope/artisan/discussions/2100
- **Người mở:** `cafelatrobot`
- **Ngày mở:** 20/01/2026
- **Trạng thái:** Mở

### Nội dung đề xuất

Người dùng cho biết dòng IKAWA Home đang bị ngừng phát triển/ngừng cung cấp và hỏi cần làm gì để Artisan hỗ trợ thiết bị này lâu dài. Họ nhận xét IKAWA Home tương tự IKAWA Pro, sẵn sàng liên hệ phía IKAWA để xin thông tin kỹ thuật, thậm chí đề xuất gây quỹ cộng đồng cho công việc phát triển.

### Phản hồi

`MAKOMO` nói Artisan **có thể kết nối IKAWA Home ngay ở trạng thái hiện tại**, nhưng chưa thể gửi profile từ Artisan sang máy. Ông đồng thời cảnh báo về rủi ro mua vào một hệ sinh thái đóng: khi hãng ngừng sản phẩm hoặc dịch vụ, người dùng có thể mất khả năng kiểm soát thiết bị dù phần cứng vẫn còn tốt.

Người mở hỏi tiếp: nếu Andrew/IKAWA công khai mã nguồn ứng dụng IKAWA Home, việc sửa Artisan để gửi profile có trở nên dễ dàng không. Maintainer trả lời thẳng rằng hiện ông không biết mức độ công việc và không có nguồn lực để làm; dự án luôn chào đón Pull Request có giá trị từ cộng đồng.

### Kết luận

- Đọc/kết nối: được cho là đã hoạt động sẵn.
- Gửi profile: chưa được hỗ trợ.
- Không có cam kết phát triển chính thức.
- Hướng khả thi là tài liệu giao thức hoặc mã nguồn mở từ IKAWA, sau đó cộng đồng viết PR.

**Ý tưởng sản phẩm rút ra:** nhà sản xuất máy rang nên công khai hoặc ít nhất tài liệu hóa giao thức điều khiển, cho phép xuất/nhập profile cục bộ và tránh phụ thuộc hoàn toàn vào cloud/app độc quyền.

---

## 5. #2084 — Increase/Decrease Burner Power by % relative to current value

- **Nguồn:** https://github.com/artisan-roaster-scope/artisan/discussions/2084
- **Người mở:** `feichong83`
- **Ngày mở:** 01/01/2026
- **Trạng thái:** Mở

### Yêu cầu

Artisan hiện cho phép nút Event tăng/giảm burner bằng **giá trị tuyệt đối**. Ví dụ burner đang 40, bấm `-10` sẽ xuống 30. Người đề xuất cho rằng trong tư duy vận hành, roaster thường nghĩ theo tỷ lệ: “giảm 50% so với công suất hiện tại”, đặc biệt khi kiểm soát giai đoạn development.

Họ muốn tạo các nút như `-10%`, `-25%`, `-50%`. Với burner hiện tại bằng 40:

- `-50%` → 20.
- `-25%` → 30.
- `-10%` → 36.

Điểm khác biệt là phép tính luôn dựa trên giá trị hiện hành, không phải trừ một lượng cố định.

### Phản hồi

Một bình luận của `beanoccio` là lời chúc năm mới/phỏng theo thơ Rilke và không xử lý nội dung kỹ thuật. Nó cho thấy luồng có một phản hồi lệch chủ đề nhưng không làm thay đổi yêu cầu.

`Terracotta-6` đề xuất giải pháp ngoài: viết script Python, gọi bằng hành động **Call Program**, để script đọc giá trị hiện tại, tính phần trăm và gửi lại một giá trị tuyệt đối phù hợp. Tức là có thể mô phỏng chức năng mà không cần thay lõi Artisan, nhưng cần hạ tầng giao tiếp giữa Artisan, script và controller.

### Trạng thái

Không có phản hồi maintainer hay xác nhận tính năng đã được tích hợp. Ý tưởng vẫn là một feature request hợp lệ.

**Ý tưởng sản phẩm rút ra:** các nút điều khiển nên hỗ trợ ba chế độ rõ ràng: `Set absolute`, `Add/subtract delta`, và `Multiply by percentage`. Giao diện phải hiển thị giá trị dự kiến trước khi áp dụng để tránh nhầm giữa “giảm 50 điểm” và “giảm 50%”.

---

## 6. #2012 — More space between Windows 11 taskbar and buttons

- **Nguồn:** https://github.com/artisan-roaster-scope/artisan/discussions/2012
- **Người mở:** `beanoccio`
- **Ngày mở:** 14/10/2025
- **Trạng thái:** Mở
- **Dạng yêu cầu:** Chủ yếu trình bày bằng ảnh chụp màn hình

### Vấn đề

Người dùng muốn có thêm khoảng trống giữa hàng nút phía dưới của Artisan và taskbar Windows 11. Dù bài viết gần như không có mô tả chữ, ảnh minh họa cho thấy các nút quá sát vùng hệ điều hành, tạo cảm giác chật và có thể bất tiện khi dùng chuột hoặc màn hình cảm ứng.

### Phản hồi và kết quả

Ngày 15/10/2025, `MAKOMO` trả lời ngắn gọn rằng thay đổi đã được thêm trong commit `0e6b474`. Người mở cảm ơn ngay sau đó. Đến 19/10/2025, họ thử bản cập nhật và xác nhận khoảng cách mới “hoàn hảo”.

### Ý nghĩa

Đây là một yêu cầu UI nhỏ nhưng được giải quyết rất nhanh. Nó nhấn mạnh rằng giao diện công nghiệp phải tính đến safe area của Windows, taskbar tự ẩn/không tự ẩn, DPI scaling và thao tác cảm ứng; vài pixel có thể ảnh hưởng đáng kể đến trải nghiệm vận hành lâu dài.

---

## 7. #1969 — How long is the X-axis?

- **Nguồn:** https://github.com/artisan-roaster-scope/artisan/discussions/1969
- **Người mở:** `davidm870`
- **Ngày mở:** 30/08/2025
- **Trạng thái:** Mở

### Bối cảnh đặc biệt

Người mở đến từ Tostadores de Ometepe tại Nicaragua. Họ kể về hành trình dùng Artisan không chỉ cho máy rang mà cả các quá trình nhiệt dài:

- Công ty đưa vào vận hành máy rang Quest M3 thứ ba, được sửa bằng RC micro servo để Artisan điều khiển.
- Họ từng dùng Artisan từ năm 2020 để theo dõi một lò biochar kiểu top-lit updraft.
- Lò được làm từ thùng thép 220 lít, gắn hai thermocouple: một ở nắp và một ở lớp vỏ gốm.
- Phiên theo dõi kéo dài khoảng bốn giờ; phiên bản Artisan cũ không thật sự thoải mái với một phiên dài như vậy.

Từ đó, họ nêu một ứng dụng còn dài hơn: **precision fermentation** cà phê trong các thùng nhựa 220 lít kín, dùng chủng men và vi khuẩn chọn lọc. Quá trình có thể kéo dài nhiều giờ hoặc nhiều ngày và cần ghi nhiệt độ, pH liên tục. Họ hỏi Artisan hiện có thể kéo trục X tới mức nào và liệu nên hỗ trợ thời gian tính bằng ngày.

### Thảo luận về thiết bị ghi dữ liệu

`Terracotta-6` đưa ra một danh sách dài các data logger IoT dùng trong thực phẩm/lên men, trong đó có các nhóm thiết bị như Jingchuang GSP-8A, Toprie TR-750, TempSir-GT+, Xiangkong và Saiou Huachuang. Các gợi ý xoay quanh:

- Phạm vi nhiệt độ và số kênh.
- Hỗ trợ đầu dò ngoài.
- Wi‑Fi/4G/Ethernet/USB.
- Cloud dashboard, cảnh báo và xuất dữ liệu.
- Độ chính xác, ổn định trong môi trường ẩm.

Danh sách này mang tính tham khảo phần cứng hơn là giải pháp trực tiếp cho Artisan.

### Câu hỏi về chu kỳ lấy mẫu

`MAKOMO` hỏi người dùng cần khoảng lấy mẫu tối thiểu/tối đa nào. Người mở trả lời rằng nhiệt độ và pH trong lên men thay đổi chậm nên 10 phút hoặc một giờ có thể đủ để thấy xu hướng. Tuy nhiên, họ vẫn muốn lấy mẫu tương đối thường xuyên để phát hiện thay đổi đột ngột; về sau có thể bỏ bớt các mẫu không có giá trị.

### Phản hồi phát triển

Maintainer cho biết hỗ trợ khoảng lấy mẫu dài hơn và trục X lớn hơn đã được thực hiện cho phiên bản Artisan kế tiếp. Nhóm cũng đang cải thiện cách nhập/hiển thị thời gian cho các quy trình nhiều giờ.

### Ý nghĩa

Ý tưởng biến Artisan từ “roast logger” thành một nền tảng ghi dữ liệu quá trình chung. Khi mở rộng tới giờ/ngày, phần mềm cần:

- Đơn vị trục tự chuyển giây → phút → giờ → ngày.
- Downsampling/aggregation để không vẽ hàng triệu điểm.
- Chống mất dữ liệu, autosave và phục hồi phiên.
- Nhiều tốc độ lấy mẫu tùy giai đoạn.
- Event và annotation cho thay đổi pH, bổ sung men, đảo thùng, mở van.
- Cơ chế cảnh báo dài hạn và chạy ổn định không cần người giám sát.

---

## 8. #1979 — Informational tips for Tooltip display mode

- **Nguồn:** https://github.com/artisan-roaster-scope/artisan/discussions/1979
- **Trạng thái:** **Đã đóng**
- **Nội dung trực tiếp:** Bài đăng chỉ dẫn chiếu tới Discussion #1978, không có bình luận độc lập
- **Luồng liên quan:** https://github.com/artisan-roaster-scope/artisan/discussions/1978

### Nguồn gốc của ý tưởng

Trong #1978, một người dùng thấy hàng thông tin bên dưới trục X đột nhiên hiển thị Energy và CO₂ thay vì ngày rang, khối lượng mẻ và hao hụt khối lượng. Họ đã kiểm tra `Characteristics` nhưng không biết rằng vùng này có menu ngữ cảnh khi nhấp chuột phải.

Cộng đồng hướng dẫn:

- Di chuột tới vùng đang gây khó hiểu.
- Nhấp chuột phải để chọn những trường cần hiển thị.
- Tooltip xuất hiện khi hover lên `Characteristics` cũng có thể giải thích cách dùng.

Người dùng xác nhận vấn đề được giải quyết, nhưng nói họ đã đọc phần Statistics nhiều lần mà không thấy hướng dẫn nhấp chuột phải. Một người dùng lâu năm khác cũng bất ngờ vì chưa biết chức năng này, dù đã theo Artisan nhiều năm.

### Ý tưởng được đưa sang #1979

Từ vấn đề discoverability trên, #1979 đề xuất đưa thêm thông tin hướng dẫn vào **Tooltip display mode trong khu vực Characteristics**, để người dùng biết:

- Vùng dữ liệu có thể tương tác.
- Nhấp chuột phải mở lựa chọn trường hiển thị.
- Nội dung bên dưới trục X không bị lỗi; nó chỉ đang dùng một cấu hình hiển thị khác.

### Kết luận

Chủ đề đã đóng và không có trao đổi tiếp. Tuy vậy, bài học UX rất rõ: chức năng chỉ tồn tại trong menu nhấp chuột phải là chức năng khó khám phá, nhất là trên màn hình cảm ứng nơi khái niệm right-click không tự nhiên.

**Ý tưởng sản phẩm rút ra:** thêm biểu tượng cài đặt nhỏ, menu ba chấm hoặc tooltip có câu hành động cụ thể như “Nhấp chuột phải để chọn dữ liệu hiển thị”; không nên phụ thuộc hoàn toàn vào thao tác ẩn.

---

## 9. #1915 — Organizing the button layout in the event table

- **Nguồn:** https://github.com/artisan-roaster-scope/artisan/discussions/1915
- **Người mở:** `beanoccio`
- **Ngày mở:** 10/07/2025
- **Trạng thái:** Mở
- **Quy mô:** 1 bình luận chính và 7 nhánh trả lời; 2 trả lời cũ bị giao diện khách thu gọn

### Vấn đề

Một thay đổi dự kiến cho Artisan 3.2.1 ảnh hưởng cách Event Buttons được xếp thành hàng. Người dùng nói phải thử đi thử lại gần một giờ để tái tạo bố cục đã chăm chút từ nhiều tháng hoặc nhiều năm trước. Họ cho rằng cơ chế dựa trên việc đếm nút visible/hidden quá khó kiểm soát.

Họ đề nghị bổ sung hai loại hàng/phần tử bố cục:

- **New button row / line break:** bắt đầu hàng nút mới một cách tường minh.
- **Spacing:** tạo khoảng cách ngang giữa hai nút.

Nhờ đó người dùng không phải chèn và đếm nhiều nút ẩn chỉ để điều khiển layout.

### Giải thích của `roasterdave`

Maintainer suy đoán người dùng có các nút ẩn nằm đầu bảng, trước nút nhìn thấy đầu tiên. Để giữ bố cục cũ sau thay đổi:

- Đếm số nút ẩn ở đầu bảng.
- Thêm đúng số nút ẩn rỗng vào cuối hàng nút nhìn thấy đầu tiên.
- Chỉ hàng đầu tiên cần chỉnh.
- Nếu nút đầu tiên vốn đã visible, thay đổi mới không ảnh hưởng layout.

Mục đích thiết kế mới là cho phép đặt các **hidden action buttons** ở đầu bảng. Những nút này có thể chứa action được Alarm hoặc nút khác tham chiếu. Khi chúng nằm đầu bảng, số dòng/index của chúng ổn định dù người dùng sắp xếp lại các nút visible phía sau.

### Các chi tiết tiếp theo

Người dùng phát hiện có thể dùng ký tự `#` cho comment và tự nhận đã không nghĩ tới điều đó dù Artisan viết bằng Python. Luồng còn trao đổi về việc các nút ẩn có Type/Action và các nút ẩn rỗng được tính khác nhau:

- Hidden button có hành động ở đầu bảng được xem như action storage và không nên phá hàng visible.
- Hidden button rỗng có thể được dùng như spacer và vẫn được tính trong bố cục.
- Vì vậy, các spacer cần được chuyển tới vị trí đúng thay vì để lẫn với action button ở đầu bảng.

Nhóm phát triển cung cấp continuous build. Người dùng thử bản 3.2.1 build `8fd6bb0` và xác nhận việc chỉnh sửa rất nhanh, bố cục đạt mức “pixel-perfect”.

### Kết luận

Yêu cầu về phần tử line-break/spacing riêng không được xác nhận là đã trở thành tính năng độc lập, nhưng vấn đề tương thích layout cụ thể đã được sửa thành công.

**Ý tưởng sản phẩm rút ra:** nên tách “nút thực hiện hành động” khỏi “phần tử bố cục”. Một editor kéo-thả có grid, row, spacer và preview sẽ an toàn hơn việc dùng nút ẩn như CSS thủ công. ID của action cũng nên là ID ổn định, không phải số hàng dễ thay đổi.

---

## 10. #1934 — Readings imported (from??)

- **Nguồn:** https://github.com/artisan-roaster-scope/artisan/discussions/1934
- **Người mở:** `prmango43`
- **Ngày mở:** 22/07/2025
- **Trạng thái:** **Đã đóng**

### Yêu cầu

Người dùng xuất dữ liệu ra CSV, chỉnh/cắt các dòng dữ liệu, rồi import ngược vào Artisan để kiểm tra. Sau nhiều lần thử, họ khó nhớ file CSV nào là bản mới nhất đã nạp. Trên biểu đồ chỉ hiện thông báo chung “Readings imported”, nên mỗi khi rời máy rồi quay lại, họ phải xem ghi chú hoặc mở editor để truy lại nguồn.

Đề xuất là hiển thị **tên file và phần mở rộng** của file đã import, thay vì chỉ có nhãn chung.

### Phản hồi

`poundy` cho rằng quy trình export–edit–reimport không phải use case thông thường và khó kỳ vọng nhóm dành thời gian cho yêu cầu này; nếu người dùng thật sự cần, dự án mã nguồn mở có thể nhận Pull Request.

`MAKOMO` chỉ ra rằng menu **Help → Messages** đã ghi log đường dẫn các file được load, ví dụ đường dẫn profile `.alog` chính và background profile. Đây là cách hiện tại để truy nguồn file.

`roasterdave` làm rõ điểm khác biệt: người mở đang hỏi tên file **CSV import**, không phải `.alog`. Ông nhận xét việc thêm tên CSV vào message là thay đổi khá đơn giản và hợp lý để đưa vào bản phát hành tiếp theo.

### Kết luận

Chủ đề được đóng, nhưng phản hồi cuối cho thấy cải tiến nhỏ nhiều khả năng được chấp nhận ở cấp message log. Không có xác nhận trong luồng rằng tên file sẽ được in trực tiếp lên graph.

**Ý tưởng sản phẩm rút ra:** mọi thao tác import nên tạo provenance rõ ràng: tên file, đường dẫn, timestamp, hash, ai thực hiện và trạng thái dữ liệu đã bị sửa hay chưa.

---

## 11. #1884 — Switching between Artisan PID and Roaster PID

- **Nguồn:** https://github.com/artisan-roaster-scope/artisan/discussions/1884
- **Người mở:** `beanoccio`
- **Ngày mở:** 09/06/2025
- **Trạng thái:** Mở

### Yêu cầu

Người dùng muốn chuyển giữa:

- PID nội bộ của controller/máy rang.
- PID của Artisan.

Hiện họ chủ yếu dùng PID của máy, đôi lúc chuyển sang Artisan PID. Mỗi lần chuyển, họ phải vào cấu hình thiết bị và đặt `SlaveID` thành `0`. Họ muốn có một **Artisan Command** để gán thao tác này cho một nút.

### Trao đổi

`Terracotta-6` nhận xét tùy chọn hiện nằm trong `Config → Device Assignment → PID Firmware`, và nghi ngờ việc thêm nút chuyển trực tiếp sẽ không đơn giản. Lý do ngầm hiểu là đây không chỉ là một giá trị UI; nó có thể ảnh hưởng giao thức, mapping thiết bị và tương thích controller.

Người mở đồng ý rằng thay đổi có vẻ nhỏ nhưng có thể gây nhiều vấn đề tương thích. Tuy vậy, từ góc độ workflow, một command sẽ giúp tránh vào sâu trong Device Configuration và thay SlaveID thủ công mỗi lần.

### Trạng thái

Không có phản hồi maintainer hoặc xác nhận triển khai. Ý tưởng vẫn mở.

**Ý tưởng sản phẩm rút ra:** nếu cho phép đổi “nguồn PID” khi vận hành, hệ thống phải có state machine an toàn: bumpless transfer, xác nhận setpoint hiện tại, khóa chuyển khi output không hợp lệ, và hiển thị rất rõ PID nào đang nắm quyền điều khiển.

---

## 12. #1821 — Six sliders instead of four

- **Nguồn:** https://github.com/artisan-roaster-scope/artisan/discussions/1821
- **Người mở:** `beanoccio`
- **Ngày mở:** 08/04/2025
- **Trạng thái:** **Đã đóng**

### Nhu cầu

Người dùng ghi lại bốn nhóm Event bằng bốn slider hiện có:

1. In Air — độ mở damper khí tươi vào.
2. Drum speed.
3. Exhaust air damper — độ mở damper khí thải.
4. Exhaust air fan speed.

Như vậy không còn slider cho thông số quan trọng nhất là **heating power**. Người dùng thừa nhận họ dùng tới ba slider chỉ cho airflow, nhưng cho rằng điều đó cần thiết để nghiên cứu và lập tài liệu quá trình rang. Họ hỏi việc tăng thêm hai Event/slider có tốn nhiều công không.

### Phản hồi quyết định

`MAKOMO` trả lời rằng đây là thay đổi lớn và Artisan **sẽ không hỗ trợ quá bốn named event types**. Vì dự án mã nguồn mở, người dùng có thể tạo fork riêng nếu thật sự cần sáu loại.

### Kết luận

Đề xuất bị từ chối dứt khoát và đóng. Giới hạn bốn Event type là một quyết định kiến trúc/UI, không chỉ là thiếu hai widget.

**Ý tưởng sản phẩm rút ra:** một phần mềm máy rang hiện đại nên dùng hệ thống channel động, nơi mỗi actuator/sensor có ID, đơn vị, min/max, kiểu hiển thị và quyền điều khiển riêng; không nên đóng cứng đúng bốn loại Event nếu máy có nhiều damper, fan, drum, burner hoặc afterburner.

---

## 13. #1782 — Bluetooth LE profile template

- **Nguồn:** https://github.com/artisan-roaster-scope/artisan/discussions/1782
- **Trạng thái:** **Đã đóng**

### Yêu cầu

Người dùng muốn Artisan có một mẫu profile chung cho **Bluetooth Low Energy**, tương tự các template đang có cho USB serial hoặc Bluetooth Classic. Mục tiêu là giúp những board như ESP32, CH592 và các vi điều khiển BLE khác giao tiếp với Artisan theo một cấu trúc chuẩn, thay vì mỗi dự án tự phát minh protocol.

### Phản hồi

`MAKOMO` nói điều này có thể thực hiện vì Artisan là mã nguồn mở. Tuy nhiên, để tiến triển, cộng đồng cần gửi:

- Pull Request có mã nguồn.
- Hoặc ít nhất một đề xuất kỹ thuật đủ cụ thể: service UUID, characteristic UUID, định dạng packet, subscribe/notify, write command, reconnect và mapping channel.

Người mở nói họ sẽ học Python để thử đóng góp.

### Kết luận

Chủ đề được đóng mà chưa có template BLE chung được xác nhận trong luồng.

**Ý tưởng sản phẩm rút ra:** BLE cần một protocol versioned rõ ràng, hỗ trợ discovery, metadata đơn vị, notify theo chu kỳ, command acknowledgement và cơ chế mất kết nối an toàn; chỉ tạo “kết nối BLE” mà không chuẩn hóa schema vẫn dẫn tới tích hợp riêng lẻ.

---

## 14. #936 — Charting Phidgets HUM1001 stack humidity

- **Nguồn:** https://github.com/artisan-roaster-scope/artisan/discussions/936
- **Người mở:** `collinarneson`
- **Trạng thái:** Mở
- **Phạm vi thảo luận:** Kéo dài từ năm 2022 tới đầu năm 2025

### Đề xuất ban đầu

Người dùng muốn lấy dữ liệu từ cảm biến độ ẩm Phidgets HUM1001 và vẽ thành một đường trên roast chart để theo dõi **độ ẩm khí thải/stack humidity trong quá trình rang**. Artisan khi đó đã có thể đọc HUM1001 cho độ ẩm môi trường, nhưng chưa dùng nó như một Extra Device có stream liên tục trên biểu đồ mẻ rang.

Giả thuyết của người đề xuất là hơi nước thoát ra từ hạt, đặc biệt quanh First Crack, có thể tạo tín hiệu đủ rõ để:

- Nhìn thấy tốc độ giải phóng ẩm.
- Xác định hoặc hỗ trợ xác định thời điểm First Crack.
- So sánh hạt, quá trình sơ chế và profile.
- Tạo thêm dữ liệu khách quan ngoài BT/ET/RoR.

Người dùng vận hành máy điện, nên họ cho rằng ảnh hưởng hơi nước từ đốt gas không đáng kể. Họ dẫn một quan sát cho thấy RH có thể tăng khoảng 5% trong chừng 30 giây quanh First Crack, trên nền tăng/giảm chậm hơn khoảng 1% mỗi phút.

### Phản hồi thận trọng của `MAKOMO`

Maintainer nói nhóm đã từng thử các đầu dò nhanh và đắt tiền nhưng kết quả không thuyết phục. Các vấn đề chính:

- Cảm biến độ ẩm phổ thông thường quá chậm.
- Nhiệt độ khí thải có thể vượt phạm vi làm việc.
- Độ phân giải và độ nhạy chưa đủ để đánh dấu chính xác một Event.
- Với máy gas, quá trình cháy tự tạo hơi nước, làm tín hiệu không chỉ đến từ hạt.
- HUM1001 được Artisan dùng như cảm biến môi trường; đưa nó vào stack không có nghĩa nó phù hợp với điều kiện đó.

Khi người dùng vẫn muốn thử, maintainer nhấn mạnh dự án mở và họ có thể tự sửa mã nguồn.

### Kinh nghiệm thực nghiệm của `roasterdave`

Đây là phần kỹ thuật quan trọng nhất của luồng. `roasterdave` cho biết đã thử:

- Cảm biến công nghiệp Novus, giao tiếp MODBUS/4–20 mA/0–10 V.
- Một số đầu dò MODBUS giá thấp.
- Tìm hiểu cảm biến chất lượng phòng thí nghiệm cho môi trường trong drum, nhưng giá quá cao và chính nhà sản xuất không khuyến khích dùng trong điều kiện rang.
- Cuối cùng tập trung vào exhaust thay vì đặt cảm biến trực tiếp trong drum.

Ông phân tích nhiều lớp rủi ro:

#### 1. Chip cảm biến có nhiều cấp chất lượng

Các module “đều đo RH” nhưng khác rất lớn về:

- Nhiệt độ tối đa.
- Sai số RH ở nhiệt độ cao.
- Response time.
- Khả năng phục hồi sau ngưng tụ/quá nhiệt.
- Độ trôi lâu dài.

Thông số response time trong phòng thử không đảm bảo giống response time khi đặt sau đường ống, filter và luồng khí thực tế.

#### 2. Độ trễ làm mất giá trị điều khiển

Nếu spike chỉ xuất hiện vài chục giây sau sự kiện thật, dữ liệu có thể thú vị khi xem lại nhưng không đủ tin cậy để điều khiển theo thời gian thực. Việc thay đổi gas có thể tạo bước tín hiệu dùng để ước lượng trễ cảm biến, nhưng chính thao tác đó lại làm nhiễu quá trình.

#### 3. Bụi, chaff và dầu sẽ làm bẩn cảm biến

Khí thải rang có particulate và chaff. Cảm biến cần filter phù hợp, dễ thay; nếu không, số đọc sẽ xuống cấp liên tục và tuổi thọ ngắn.

#### 4. Có thể thấy vùng FC nhưng khó đánh dấu chính xác FCs

Kết quả thử cho thấy giải phóng ẩm quanh First Crack là rõ ràng, nhưng:

- Điểm bắt đầu tín hiệu không tương quan chặt với tiếng nổ đầu tiên.
- Không tương quan ổn định với phương pháp ETRoR.
- Hình dạng và thời điểm đường độ ẩm thay đổi nhiều giữa các loại green coffee.
- Sau mẻ rang, dữ liệu trông thú vị; trong lúc rang, nó chưa đủ “actionable”.

Nói cách khác, hệ thống nhận ra “đang ở vùng First Crack”, nhưng không xác định tin cậy chính xác khoảnh khắc FCs.

### Nhánh thảo luận về drying phase năm 2025

`ShakesTC`, người dùng SmartRoast 800, hỏi liệu độ ẩm có giúp xác định **kết thúc drying phase** khách quan hơn màu hạt, nhiệt độ và kinh nghiệm hay không. Họ lo việc chọn sai Yellow/Dry End làm sai phần trăm các phase và ảnh hưởng quyết định drop.

`collinarneson` trả lời rằng họ hoài nghi khả năng đó. Spike quanh 1C có thể rõ nếu đầu dò đủ tốt, nhưng cuối drying phase không có biến động nổi bật tương tự. Mục tiêu thực tế vẫn là tái tạo dry/ramp/dev ratio tạo vị ngon, và việc đó hoàn toàn có thể làm với dữ liệu nhiệt độ chất lượng tốt.

`ShakesTC` sau đó vẫn thử thủ công: mỗi phút mở cửa sổ Roast Properties, bấm Update và ghi một mẫu. Kết quả đúng với kỳ vọng nhưng không đủ mạnh:

- RH cao hơn đầu mẻ.
- Giảm dần tới cuối drying.
- Tăng nhẹ ở First Crack.
- Biến đổi không kịch tính như họ hy vọng, nên khó dùng làm marker chính xác.

Họ kết luận thử nghiệm vui và có giá trị học hỏi, nhưng không chứng minh được một ứng dụng điều khiển mạnh.

### Kết luận

Luồng không xác nhận HUM1001 được thêm thành kênh stack humidity. Giá trị lớn nhất là khung đánh giá cảm biến:

- Đừng chỉ hỏi “đọc được RH không”; phải hỏi độ trễ, nhiệt độ, fouling, filter, calibration và tính hành động của tín hiệu.
- Một đường dữ liệu có thể hữu ích cho nghiên cứu nhưng không đủ an toàn để làm trigger tự động.
- Cần phân biệt ambient humidity, exhaust humidity và humidity gần bean mass.

**Ý tưởng sản phẩm rút ra:** app có thể hỗ trợ kênh humidity mở, nhưng nên gắn nhãn “experimental”, lưu metadata cảm biến, cho phép time-offset calibration và không mặc định dùng nó để tự đánh dấu FC/Yellow nếu chưa có độ tin cậy thống kê.

---

## 15. #1551 — Headless style operation

- **Nguồn:** https://github.com/artisan-roaster-scope/artisan/discussions/1551
- **Người mở:** `projection-org`
- **Ngày mở:** 20/05/2024
- **Trạng thái:** Mở

### Nội dung nhìn thấy

Bài mở đầu hiện chỉ còn câu yêu cầu xóa vì người viết dùng nhầm tài khoản. Hai bình luận sau của chính tác giả cũng lặp lại yêu cầu xóa. Vì vậy, phần mô tả đầy đủ ban đầu của nhu cầu headless không còn xuất hiện trong nội dung công khai đọc được.

### Phản hồi kỹ thuật còn lại

`MAKOMO` vẫn để lại câu trả lời có giá trị:

- Artisan là ứng dụng **monolithic**, và rất có thể sẽ không được tách thành backend và frontend độc lập.
- Tuy nhiên, Artisan kết nối với các “backend” phần cứng/giao thức như MODBUS, Siemens S7 hoặc WebSocket server để đọc dữ liệu và gửi lệnh.
- Theo góc nhìn đó, Artisan chính là frontend của PLC/controller.
- Một Arduino hoặc Raspberry Pi đơn giản có thể điều khiển actuator, đọc sensor và giao tiếp với Artisan.

### Ý nghĩa

Một chế độ headless đúng nghĩa có thể bao gồm daemon thu thập dữ liệu, REST/WebSocket API, logic automation chạy không cần UI và nhiều client hiển thị. Maintainer cho biết kiến trúc hiện tại không hướng tới việc tách như vậy.

**Ý tưởng sản phẩm rút ra:** với một hệ điều khiển máy rang mới, nên tách rõ:

- Controller thời gian thực trên PLC/MCU.
- Service thu thập/logging.
- API.
- HMI tại máy.
- Client từ xa.

Việc tách này giúp app đóng/mất kết nối mà máy vẫn an toàn, đồng thời hỗ trợ dashboard web và remote service.

---

## 16. #1474 — Posting status: Open/Closed and utility of conversation

- **Nguồn:** https://github.com/artisan-roaster-scope/artisan/discussions/1474
- **Người mở:** `asarule`
- **Ngày mở:** 26/02/2024
- **Trạng thái:** Mở
- **Phản hồi:** Không có

### Bối cảnh

Người dùng có máy Kaleido M10 và thấy First Crack hiển thị ở BT khoảng 178°C thay vì khoảng 198°C như họ kỳ vọng từ Kaffelogic Nano 7. Trong một bài trước, họ đã đề xuất một lựa chọn thay thế cho `Config → Device → Symb ET/BT` để làm BT, SV và background profile phản ánh mức nhiệt mà họ cho là đúng hơn.

Bài đó bị đánh dấu đóng. Người dùng hiểu rằng, từ góc độ feature development, nhóm có thể đã quyết định không theo đuổi ý tưởng. Tuy nhiên, mục tiêu của họ còn là xin ý kiến cộng đồng về cách xử lý chênh lệch nhiệt độ. Họ lo nhãn **Closed** làm những người khác nghĩ cuộc trò chuyện đã kết thúc và không tiếp tục góp ý.

### Câu hỏi quản trị cộng đồng

Họ hỏi có phương pháp, địa điểm hoặc cách đặt câu hỏi nào tốt hơn để:

- Một feature request có thể bị từ chối/đóng.
- Nhưng phần trao đổi về quy trình rang và giải pháp workaround vẫn tiếp tục.

### Kết luận

Không ai phản hồi. Vì vậy, chủ đề không đưa ra quy tắc chính thức cho Open/Closed.

**Ý tưởng sản phẩm/cộng đồng rút ra:** hệ thống support nên tách trạng thái “feature decision” khỏi trạng thái “community discussion”. Có thể dùng nhãn `not planned`, `answered`, `workaround available`, `discussion welcome` thay vì chỉ Open/Closed.

---

## 17. #1443 — Better decaf roasts with advanced alarms

- **Nguồn:** https://github.com/artisan-roaster-scope/artisan/discussions/1443
- **Trạng thái:** Mở
- **Phản hồi:** Không có

### Nội dung chia sẻ

Người mở không yêu cầu một tính năng mới theo nghĩa truyền thống. Họ chia sẻ cách cải thiện decaf bằng một chiến lược **mélange of roasts**: cùng một loại cà phê decaf được rang ở các mức khác nhau rồi phối lại, thay vì cố ép toàn bộ đặc tính mong muốn vào một profile duy nhất.

Họ đã thực hiện thủ công trong nhiều năm, sau đó dùng hệ thống Alarm của Artisan để tự động hóa hoàn toàn trên Hottop B-2K+.

Bài đăng cung cấp:

- Hai video YouTube trình bày phương pháp/quy trình.
- Một website giải thích thêm.
- Các file có thể tải để tái tạo cấu hình.

### Ý nghĩa

Luồng cho thấy Alarm không chỉ dùng cho cảnh báo; nó có thể trở thành engine điều khiển một quy trình rang phức tạp và lặp lại được. Nó cũng gợi ý rằng “profile tốt” không nhất thiết là một đường cong duy nhất; blending nhiều roast level có thể là một chiều thiết kế sản phẩm.

**Ý tưởng sản phẩm rút ra:** phần mềm có thể hỗ trợ “roast set” gồm nhiều mẻ thành phần, tính tỷ lệ phối, theo dõi batch genealogy và dự đoán màu/khối lượng sau phối.

---

## 18. #1035 — Add support for PICO TC08

- **Nguồn:** https://github.com/artisan-roaster-scope/artisan/discussions/1035
- **Người mở:** `waanito`
- **Trạng thái:** Mở
- **Phạm vi:** Nhiều bình luận và nhánh kỹ thuật; một số nhánh bị giao diện khách thu gọn

### Mục tiêu

Người dùng muốn Artisan hỗ trợ **Pico Technology TC-08**, một bộ ghi nhiệt độ USB nhiều kênh thermocouple. Họ có nền tảng lập trình/reverse engineering và cũng quan tâm tới Omega MWTC.

### Hướng dẫn đóng góp ban đầu

Trong trao đổi, cộng đồng khuyến nghị:

1. Trước hết viết một script nhỏ có thể đọc dữ liệu thiết bị và in ra console.
2. Nếu có thể, dùng mô hình hiện đại như `asyncio streams` để tránh chặn vòng lặp ứng dụng.
3. Khi driver độc lập hoạt động ổn định, mới tích hợp vào Artisan.
4. Với file đơn giản có thể đính kèm vào Discussion; với thay đổi dài hạn nên tạo repository/fork và gửi Pull Request.

`poundy` giải thích quy trình chia sẻ file trên GitHub: file nhỏ có thể đổi đuôi `.txt`, file phức tạp có thể zip; nhưng cuối cùng người đóng góp nên thiết lập GitHub đúng cách để PR vào codebase.

### Quá trình phát triển của người dùng

Người mở dành nhiều thời gian làm cho Pico SDK chạy trên macOS:

- Ví dụ single mode gần như chạy ngay, chỉ cần bỏ một reference không tồn tại.
- Streaming mode khó hơn vì phải hiểu Python wrapper và cách truyền mảng.
- Họ mở rộng bản Python dựa trên ví dụ C/C++.
- Sau khi chạy được trên macOS, họ sẵn sàng thử Linux và Windows.

Họ công bố repository:

`https://github.com/waanito/artisan-scope-tc08-macos`

Ban đầu có ba file, sau đó xóa và đẩy lên các bản cập nhật tốt hơn. Đến 10/03/2023, họ nói repository đã có file dùng Pico TC-08 với Artisan trên macOS và dự định làm bản Windows/Linux trong vài tuần tiếp theo.

### Nhận xét về Omega MWTC

Người dùng đánh giá Omega MWTC là ứng viên kém hơn cho Artisan vì:

- Chỉ hỗ trợ synchronized polling.
- Chu kỳ danh nghĩa 2 giây bị lệch nhẹ so với đúng 2 giây.
- Điều này làm đồng bộ thời gian và tích hợp streaming khó hơn.

Dù vậy, vì họ đang dùng MWTC với máy rang drum RK, họ có thể vẫn tiếp tục thử.

### Trạng thái

Luồng cho thấy một prototype/adapter macOS thực tế đã được tạo, nhưng không có xác nhận rõ trong Discussion rằng mã đã được merge vào bản Artisan chính thức. Do đó cần phân biệt “mã cộng đồng hoạt động” với “thiết bị được hỗ trợ chính thức”.

### Bài học kỹ thuật

- Viết driver độc lập trước khi chạm code chính.
- Streaming tốt hơn polling nếu thiết bị hỗ trợ.
- Phải xử lý SDK native, wrapper Python, mảng, architecture và đóng gói thư viện trên từng OS.
- Tích hợp thiết bị không chỉ là đọc số; còn cần timestamp, channel mapping, reconnect, lỗi đầu dò và phân phối binary.

---

## 19. #1102 — Display DTR comparison

- **Nguồn:** https://github.com/artisan-roaster-scope/artisan/discussions/1102
- **Người mở:** `jsphvrghs`
- **Ngày mở:** 16/02/2023
- **Trạng thái:** Mở
- **Phản hồi:** Không có

### Yêu cầu

Khi load một profile làm background/base để so sánh, người dùng muốn Artisan hiển thị cả **đồ thị DTR** của profile nền, không chỉ DTR của mẻ hiện tại. Ảnh minh họa đi kèm cho thấy mục tiêu là nhìn trực tiếp sự khác nhau về Development Time Ratio giữa hai mẻ.

### Ý nghĩa

DTR thường được tính từ FCs tới Drop chia cho tổng thời gian rang. Khi so sánh profile, chỉ nhìn một con số cuối cùng không cho thấy sự tiến triển theo thời gian hoặc cách hai profile lệch nhau quanh FC.

Không có phản hồi, workaround hay cam kết triển khai trong luồng.

**Ý tưởng sản phẩm rút ra:** Comparator nên cho phép chọn bất kỳ derived metric nào của foreground/background, hiển thị delta và cảnh báo rằng DTR chỉ có ý nghĩa khi Event FC được đánh dấu nhất quán.

---

## 20. #1083 — Artisan Command for setting symbolic ET/BT

- **Nguồn:** https://github.com/artisan-roaster-scope/artisan/discussions/1083
- **Người mở:** `hermetheuscoffee`
- **Ngày mở:** 27/01/2023
- **Trạng thái:** Mở
- **Kết quả:** Giải quyết hoàn toàn bằng tính năng đã có

### Vấn đề thực tế

Người dùng thử một máy rang fluid-bed 7 lb mới. Với mẻ bình thường, First Crack ổn định ở khoảng 400°F. Nhưng với sample batch chỉ 200 g, cả First Crack và Second Crack hiển thị thấp hơn khoảng 17°F, tức khoảng 383°F.

Nguyên nhân họ quan sát được:

- Khi mẻ quá nhỏ, hạt không chạm/bao phủ đầu dò BT.
- Đầu dò thực chất đọc gần với ET.
- Khi khối lượng đủ để che đầu dò, khoảng 400 g, số đọc lại phản ánh BT khá đúng.
- Từ 400 g tới 4.000 g, hành vi gần như cùng một nhóm.

Họ đã có nút Artisan để load bộ PID hoàn toàn khác cho mẻ 200 g và muốn cùng nút đó đổi công thức Symbolic ET/BT, áp correction cho mẻ nhỏ.

### Gợi ý của maintainer

`MAKOMO` không thích ý tưởng thay công thức symbolic động bằng action vì dễ tạo trạng thái khó theo dõi. Thay vào đó, ông đề xuất làm **một công thức thông minh**, sử dụng biến mới `WEIGHTin`, chứa khối lượng nạp quy đổi về gram từ Roast Properties.

Người dùng nói quan hệ không tuyến tính theo weight; nó là một ngưỡng “hạt có chạm probe hay không”. Vì vậy họ cần IF/ELSE, ví dụ về ý tưởng:

```text
IF weight < 400: dùng công thức hiệu chỉnh
ELSE: dùng BT bình thường
```

Maintainer hướng họ tới phần “Conditional” trong tài liệu Symbolic Formulas.

### Công thức cuối cùng

Sau khi thử, người dùng xác nhận hoạt động rất tốt với:

```python
(Y2 * 1.11 if WEIGHTin < 300 else Y2)
```

Ý nghĩa:

- Nếu mẻ dưới 300 g, nhân kênh Y2 với 1,11 để bù sai lệch.
- Nếu từ 300 g trở lên, dùng Y2 nguyên bản.
- Người dùng có thể nhập khối lượng bằng gram, pound hoặc đơn vị khác; Artisan quy đổi về gram cho `WEIGHTin`.

### Kết luận

Yêu cầu ban đầu là một Command mới, nhưng giải pháp tốt hơn là công thức symbolic có điều kiện. Đây là ví dụ tiêu biểu cho việc một hệ thống biểu thức đủ mạnh có thể loại bỏ nhiều nút và trạng thái cấu hình đặc biệt.

### Cảnh báo kỹ thuật

Công thức hiệu chỉnh dựa trên quan sát của một máy/đầu dò cụ thể. Không nên sao chép hệ số 1,11 hoặc ngưỡng 300 g sang máy khác mà chưa hiệu chuẩn. Tốt hơn là lưu công thức theo machine configuration và kiểm chứng bằng marker vật lý/cupping.

---

## 21. #1038 — Dark Mode for Artisan

- **Nguồn:** https://github.com/artisan-roaster-scope/artisan/discussions/1038
- **Trạng thái:** Mở

### Đề xuất

Người dùng muốn Dark Mode để dễ chịu hơn khi rang, cupping hoặc chỉnh profile vào buổi tối. Họ sẵn sàng hỗ trợ triển khai.

### Phản hồi

`MAKOMO` lưu ý dark mode trên Windows phụ thuộc lớn vào Qt. Tại thời điểm thảo luận, hỗ trợ phù hợp dường như chưa xuất hiện trước Qt 6.5. Ông dẫn tới issue Qt liên quan và yêu cầu thêm thông tin nếu người đề xuất biết cách khả thi.

### Trạng thái

Không có kết quả triển khai được ghi trong luồng. Đây không chỉ là đổi nền chart sang đen; một Dark Mode hoàn chỉnh phải xử lý:

- Widget hệ thống và custom widget.
- Dialog, tooltip, menu, table, focus state.
- Màu curve và độ tương phản.
- Trạng thái alarm/error.
- Icon có nền trong suốt.
- Windows/macOS/Linux và các Qt style khác nhau.

**Ý tưởng sản phẩm rút ra:** theme công nghiệp nên dùng design token và kiểm thử độ tương phản, không hard-code màu rải rác. Cần cho phép chart theme tách với application theme nếu người vận hành chỉ muốn nền biểu đồ tối.

---

## 22. #955 — Support for Yoctopuce Yocto-Watt

- **Nguồn:** https://github.com/artisan-roaster-scope/artisan/discussions/955
- **Người mở:** `Hambren`
- **Ngày mở:** 14/09/2022
- **Trạng thái:** Mở

### Giá trị được đề xuất

Người dùng máy rang điện muốn Artisan hỗ trợ **Yoctopuce Yocto-Watt** để đo:

- Điện áp.
- Dòng điện.
- Công suất/năng lượng.
- Năng lượng phản kháng hoặc đại lượng tích lũy liên quan trong khoảng từ Charge tới Drop.

Họ muốn so sánh mức tiêu thụ theo:

- Độ ẩm hạt.
- Phân bố kích thước.
- Profile.
- Các điều kiện mẻ khác.

Mục tiêu không chỉ là tính chi phí điện mà còn nghiên cứu năng lượng như một biến quá trình, tiến tới khả năng tái tạo “mẻ hoàn hảo”.

### Phản hồi

`MAKOMO` nói dự án sẵn sàng nhận đóng góp mã qua Pull Request.

Người mở thừa nhận không biết lập trình. Họ đã đăng việc lên Upwork nhưng nhận ra người thực hiện cần hiểu kiến trúc Artisan chứ không chỉ API Yoctopuce. Họ sẵn sàng trả chi phí hợp lý và xin hướng dẫn cách tìm một lập trình viên quen Artisan.

### Trạng thái

Không có người nhận việc hoặc xác nhận tích hợp trong luồng.

### Ý nghĩa

Năng lượng là một chiều dữ liệu mạnh, đặc biệt với máy điện. Một tích hợp tốt nên lưu:

- Công suất tức thời kW.
- Năng lượng tích lũy kWh từ Charge tới Drop.
- Năng lượng/kg green và energy/kg roasted.
- Peak demand.
- Quan hệ giữa heater command và power thực.
- Điện áp sụt, power factor và lỗi nguồn.

Cần kiểm tra thuật ngữ KVAR/kVARh cho đúng đại lượng mà thiết bị thật sự đo; tránh dùng lẫn công suất phản kháng và năng lượng tác dụng.

---

## 23. #1025 — Positionable Statistics Summary

- **Nguồn:** https://github.com/artisan-roaster-scope/artisan/discussions/1025
- **Người mở:** `JSTCOFFEE`
- **Ngày mở:** 01/12/2022
- **Trạng thái:** Mở

### Vấn đề UI

Statistics Summary xuất hiện ở góc trên bên phải và thường che curve hoặc các giá trị nhiệt độ/thời gian. Cách workaround duy nhất mà người dùng tìm thấy là chỉnh axis để tránh hộp, làm một phần lớn màn hình không được dùng hiệu quả.

Họ muốn hộp Summary có thể kéo/đặt vị trí tương tự legend.

### Cách xử lý hiện có

`roasterdave` đề xuất:

1. Vào `Config → Axes`, bật **Auto** cho Time Axis. Trục sẽ tự điều chỉnh để vừa graph khi bật/tắt Statistics Summary.
2. Vào `Config → Statistics`, giảm **Max characters per line** để hộp hẹp hơn.

Ông đồng ý ý tưởng kéo thả là hợp lý và sẽ đưa vào danh sách, nhưng có thể mất lâu mới được xem xét.

### Trạng thái

Không có xác nhận rằng hộp đã trở thành draggable trong luồng.

**Ý tưởng sản phẩm rút ra:** mọi overlay trên đồ thị nên có anchor, drag, snap, opacity, collapse và lựa chọn “avoid data labels”. Layout nên được lưu theo kích thước màn hình/DPI.

---

## 24. #985 — Modify events by BT, not time

- **Nguồn:** https://github.com/artisan-roaster-scope/artisan/discussions/985
- **Người mở:** `fatrabbit-la`
- **Ngày mở:** 16/10/2022
- **Trạng thái:** Mở, nhưng feature request bị maintainer từ chối trong luồng

### Yêu cầu

Khi thêm/sửa Event sau mẻ rang, người dùng nghĩ theo BT. Ví dụ họ muốn đặt Event ở 300°F, nhưng editor yêu cầu thời gian. Họ phải đoán thời điểm curve đạt 300°F rồi chỉnh nhiều lần tới khi marker nằm đúng vị trí.

Họ muốn chỉnh Event trực tiếp bằng BT.

### Workaround được cộng đồng đưa ra

`poundy` nói có thể:

- Di chuột tới điểm mong muốn trên graph.
- Dùng cursor display để đọc time và temperature.
- Nhấp chuột phải để thêm Event ngay tại đó.

Về mặt dữ liệu, time là trục khóa. Nếu nhập temperature, phần mềm phải tìm/interpolate các điểm lân cận để suy ra time tương ứng.

`roasterdave` bổ sung rằng người dùng có thể muốn liên hệ Event với bất kỳ curve nào, không chỉ BT. Cursor widget và crosshair cho phép đọc time tại điểm mong muốn. Cursor được cải thiện trong v2.6.0 và có tài liệu/video hướng dẫn.

Người mở nói cách này tốt hơn nhiều so với cách họ đang làm, dù nhập BT ngay trong tab Events vẫn hiệu quả hơn.

### Nhánh về nút Cluster

Người dùng hỏi thêm `Cluster` làm gì. `roasterdave` giải thích:

- Khi dùng event quantifiers để chuyển reading từ thiết bị kết nối thành một trong bốn special events, một số thiết bị tạo nhiều entry trùng/lặp.
- Nút Cluster trong `Roast → Properties → Events` gom các entry dư sau mẻ.
- Checkbox Cluster trong `Config → Events → Quantifiers` có thể thực hiện việc này ngay trong khi rang.

### Lý do từ chối

`MAKOMO` từ chối feature request vì một nhiệt độ có thể xuất hiện **nhiều lần** trong cùng profile. Ví dụ BT có thể giảm sau Charge, đi qua cùng nhiệt độ trước và sau TP; curve nhiễu hoặc giảm lại cũng có thể tạo nhiều nghiệm. Nếu chỉ nhập 300°F, phần mềm không biết Event thuộc thời điểm nào.

### Ý nghĩa

Một thiết kế tốt hơn có thể cho phép nhập BT kèm ràng buộc:

- Trước/sau TP.
- Lần xuất hiện thứ nhất/thứ hai.
- Gần time hiện tại nhất.
- Trên đoạn BT đang tăng.

Như vậy giải quyết ambiguity thay vì loại bỏ hoàn toàn nhu cầu.

---

## 25. #997 — Controlling WebSocket devices

- **Nguồn:** https://github.com/artisan-roaster-scope/artisan/discussions/997
- **Người mở:** `ademuri`
- **Ngày mở:** 27/10/2022
- **Trạng thái:** Mở
- **Kết quả:** Nhu cầu được giải quyết bằng cấu hình hiện có

### Bối cảnh

Người dùng phát triển controller máy rang dùng ESP32 kết nối Wi‑Fi. Board đã hỗ trợ giao diện WebSocket của Artisan. Họ muốn thêm khả năng “set temperature” và hỏi liệu code có cơ hội được merge hay có rủi ro kiến trúc nào.

### Trao đổi

`poundy` hỏi liệu họ đã cân nhắc **Modbus TCP**, một lớp điều khiển công nghiệp chuẩn hơn WebSocket hay chưa. Người mở nói trước đó không biết Modbus TCP tồn tại và sẽ nghiên cứu.

`MAKOMO` hỏi “set temperature” cụ thể là gì, đồng thời nhắc Artisan đã có **WebSocket command actions** cho phép gửi JSON bất kỳ tới thiết bị, tương tự Modbus Commands. Vì vậy nhu cầu có thể giải quyết bằng configuration thay vì sửa code.

Người mở giải thích controller có PID, và “set temperature” nghĩa là thay **PID setpoint**. Sau khi hiểu WebSocket Commands, họ xác nhận cấu hình hiện có hoạt động tốt.

Một bình luận khác nhấn mạnh WebSocket chỉ là transport; schema/protocol bên trong vẫn do thiết bị và Artisan thống nhất.

### Kết luận

Không cần feature mới. Artisan đã có primitive đủ linh hoạt để gửi setpoint dạng JSON.

### Bài học kỹ thuật

- Transport không phải protocol nghiệp vụ.
- Cần định nghĩa command schema, version, acknowledgement và error response.
- Modbus TCP dễ tích hợp với công nghiệp nhưng WebSocket thuận tiện cho JSON và web stack.
- Đối với PID setpoint, nên có giới hạn, đơn vị, quyền ghi và xác nhận giá trị thật từ controller.

---

## 26. #856 — Playback Events On/Off shortcut

- **Nguồn:** https://github.com/artisan-roaster-scope/artisan/discussions/856
- **Người mở:** `arnovandyk`
- **Trạng thái:** Mở
- **Kết quả:** Đã có nhiều cách thực hiện trong Artisan 2.6.0

### Nhu cầu

Người dùng muốn bật/tắt **Playback Events** ngay trên màn hình chính, thay vì đi qua menu `Roast → Background → Playback`. Họ dùng màn hình cảm ứng chất lượng không cao nên phím tắt bàn phím không phải giải pháp lý tưởng; cần một nút lớn có thể chạm.

### Các giải pháp được chỉ ra

`MAKOMO` cho biết trong Artisan 2.6.0:

- Phím `j` có thể toggle playback.
- Có Artisan Command `playbackmode` để gọi từ custom Event Button.
- Có thể cấu hình nút bật/tắt Playback, kể cả chế độ phát lại theo bean temperature.

Khi người dùng hỏi cách tạo custom button và tìm tài liệu ở đâu, maintainer yêu cầu nâng lên phiên bản 2.6.0, đồng thời chỉ tới:

- Artisan Blog.
- Nút Help trong các Events dialog.
- Một ảnh cấu hình mẫu toggle Playback OFF/ON.

Người dùng cảm ơn sau khi nhận được hướng dẫn.

### Ý nghĩa

Yêu cầu không cần thêm control cố định vào màn hình vì hệ thống custom button đã giải quyết. Tuy vậy, việc người dùng không biết tính năng tồn tại cho thấy vấn đề discoverability.

**Ý tưởng sản phẩm rút ra:** nên có thư viện command có tìm kiếm, mô tả, preview trạng thái và mẫu nút “Toggle Playback”, thay vì buộc người dùng biết tên command nội bộ.

---

## 27. #788 — “Show full” in Comparator

- **Nguồn:** https://github.com/artisan-roaster-scope/artisan/discussions/788
- **Người mở:** `sc818`
- **Ngày mở:** 19/01/2022
- **Trạng thái:** Mở
- **Kết quả:** Đã triển khai và sửa lỗi tiếp theo

### Yêu cầu

Người dùng luôn bật ghi dữ liệu trước Charge để theo dõi **BBP**. Khi dùng Comparator, phần dữ liệu trước Charge không được hiển thị đầy đủ. Họ muốn một tùy chọn “Show full” để xem BBP của các profile khi so sánh.

### Triển khai đầu tiên

`MAKOMO` đánh giá đây là đề xuất tốt và thêm flag **BBP** vào Comparator:

- Khi bật, toàn bộ đoạn ghi trước Charge được hiển thị.
- Dữ liệu sau Drop không được kéo theo vì ít giá trị trong mục đích này và có thể làm rối graph.
- Nếu Time Axis đặt Auto, trục tự mở rộng sang trái để chứa đoạn trước Charge.

Người dùng phản hồi rất tích cực, gọi đây là điều họ mong đợi từ lâu.

### Lỗi phụ về trục thời gian

Sau khi tải continuous build 2.4.7, họ xác nhận Comparator với BBP hoạt động tốt nhưng phát hiện:

- Khi time-axis step đặt 1 phút, trục chỉ lùi tối thiểu tới khoảng -2 phút.
- Vì vậy một số BBP dài hơn vẫn chưa hiện đầy đủ.

Maintainer yêu cầu gửi hai file `.alog` dạng zip để điều tra. Người dùng tải file lên. Ngày 01/02/2022, `MAKOMO` xác nhận đã sửa lỗi và đưa continuous build mới lên. Ngày 03/02, người dùng thử lại và nói kết quả hoàn hảo.

### Kết luận

Đây là ví dụ hoàn chỉnh của vòng đời feature:

1. Người dùng mô tả use case rõ ràng.
2. Maintainer triển khai nhanh.
3. Người dùng beta-test trên dữ liệu thật.
4. Phát hiện edge case.
5. Gửi file tái hiện.
6. Maintainer sửa.
7. Người dùng xác nhận.

**Ý tưởng sản phẩm rút ra:** nút so sánh nên cho phép chọn phạm vi `Pre-charge`, `Roast`, `Post-drop` độc lập; bug report nên có nút đính kèm log/config tự động để giảm trao đổi thủ công.

---

# Tổng hợp các nhóm ý tưởng lớn

## 1. Thiết kế profile và tự động hóa

Các chủ đề #2112, #1083, #985, #856, #1884 và #1443 cho thấy người dùng muốn mô tả chiến lược rang ở mức gần với tư duy thực tế:

- “Sau TP, khi BT vượt 130°C thì giảm gas.”
- “Nếu mẻ dưới 300 g thì dùng công thức hiệu chỉnh khác.”
- “Bật/tắt phát lại bằng một nút.”
- “Đổi nguồn PID mà không vào sâu trong cài đặt.”
- “Tự động chạy một quy trình decaf phức tạp.”

Artisan đã có nhiều primitive mạnh, nhưng chúng nằm rải rác trong Alarm, Event Buttons, Symbolic Formulas, PID, background playback và Device Assignment. Khoảng trống lớn nhất không hẳn là năng lực điều khiển, mà là **mô hình hóa và giải thích**.

Một hệ thống mới nên có visual profile designer với:

- Trigger theo time, BT, ET, phase và event.
- Action cho burner/fan/drum/damper/PID.
- Điều kiện trước/sau TP/FC.
- Simulation.
- Trace “rule nào chạy, rule nào bị chặn và vì sao”.
- Validation trước khi rang.

## 2. Tính truy vết và dữ liệu mẻ rang

#2132 và #1934 nhấn mạnh provenance:

- Log phải cho biết dữ liệu đến từ đâu.
- Cấu hình nào thật sự có hiệu lực.
- File nào đã được import.
- Cấu hình đã đổi trong lúc rang hay chưa.

Chỉ lưu đường dẫn file không đủ. Thiết kế tốt hơn là snapshot cấu hình, hash, version, timestamp và audit trail.

## 3. Mở rộng giao thức và thiết bị

#2100, #1782, #1035, #955 và #997 bao phủ IKAWA, BLE, Pico TC-08, Yocto-Watt và WebSocket. Mẫu chung:

- Cộng đồng có phần cứng thực và động lực.
- Nhóm lõi thiếu nguồn lực cho mọi thiết bị.
- Một plugin/driver SDK ổn định sẽ giảm gánh nặng merge vào core.
- Tài liệu giao thức mở quan trọng hơn một app đóng.

Kiến trúc nên có plugin manifest, channel metadata, capability discovery, test harness và driver chạy ngoài tiến trình.

## 4. Giao diện vận hành và khả năng khám phá

#2012, #1979, #1915, #1025, #1038 và #856 đều là bài học UX:

- Khoảng cách vài pixel có thể quan trọng trên HMI.
- Right-click là chức năng ẩn, đặc biệt trên touchscreen.
- Dùng hidden button để dàn layout là quá kỹ thuật.
- Overlay che curve phải kéo/thu gọn được.
- Dark Mode phải là hệ thống theme hoàn chỉnh.
- Command mạnh nhưng người dùng không biết tên sẽ gần như không tồn tại.

## 5. Phân tích nâng cao và quy trình ngoài rang

#936, #1102, #1969, #788 và #955 mở rộng phạm vi dữ liệu:

- Humidity khí thải.
- DTR background comparison.
- BBP trước Charge.
- Năng lượng điện.
- Lên men kéo dài nhiều ngày.

Điều này gợi ý graph engine nên hỗ trợ channel động, time span rất dài, derived metrics, downsampling và vùng phase tùy chỉnh.

## 6. Giới hạn kiến trúc được maintainer nêu rõ

Một số yêu cầu bị giới hạn hoặc từ chối vì quyết định nền tảng:

- Artisan khó trở thành backend/headless vì kiến trúc monolithic (#1551).
- Tối đa bốn named event types (#1821).
- Không thể coi `.aset` là nguồn sự thật duy nhất (#2132).
- Sửa Event chỉ bằng temperature mơ hồ khi cùng nhiệt độ xuất hiện nhiều lần (#985).
- Gửi profile tới hệ thống đóng phụ thuộc giao thức/mã nguồn của hãng (#2100).

Những phản hồi này đặc biệt hữu ích khi thiết kế phần mềm mới: chúng chỉ ra các quyết định nên tránh đóng cứng từ đầu.

---

# Danh sách ý tưởng có giá trị cao nhất để áp dụng cho app/HMI máy rang

1. **Configuration snapshot theo từng mẻ:** lưu toàn bộ trạng thái thật, không chỉ tên file.
2. **Visual roast automation designer:** xây profile bằng BT/time/phase và action kéo-thả.
3. **Rule validator:** phát hiện trigger bị vô hiệu, điều kiện `=` dễ bị bỏ qua và dependency sai.
4. **Simulation + execution trace:** chạy thử không hạt và giải thích từng rule.
5. **Channel động:** không giới hạn bốn slider; thêm actuator/sensor theo cấu hình máy.
6. **Ba loại nút điều chỉnh:** absolute, delta và percentage-relative.
7. **Bumpless PID handover:** chuyển PLC PID/app PID an toàn và có trạng thái rõ.
8. **Event provenance:** tên file import, hash, thời gian và người thao tác.
9. **Driver/plugin SDK:** BLE, Modbus TCP, WebSocket, USB logger và energy meter.
10. **Open local protocol:** thiết bị vẫn dùng được khi cloud hoặc app hãng dừng.
11. **Touch-first UI:** không phụ thuộc right-click; nút có safe area và kích thước công nghiệp.
12. **Layout editor:** row, spacer, grid và action ID ổn định.
13. **Overlay có thể kéo/thu gọn:** Statistics, legend, event list không che dữ liệu.
14. **Dark Mode theo design token:** kiểm soát tương phản và màu alarm.
15. **Comparator nâng cao:** foreground/background cho DTR, energy, BBP và derived metrics.
16. **Long-duration logging:** từ mẻ rang vài phút tới lên men nhiều ngày.
17. **Energy per kg:** công suất thật, kWh/mẻ, kWh/kg và hiệu suất.
18. **Experimental sensor framework:** humidity và sensor mới có calibration, delay và confidence.
19. **Profile library có metadata chuẩn:** máy, batch, bean, moisture, density, process, probe và target color.
20. **Support bundle một nút:** log, configuration snapshot, firmware/app version và diagnostics đóng gói tự động.

---

# Kết luận chung

27 cuộc thảo luận không chỉ là 27 yêu cầu rời rạc. Chúng mô tả ba nhu cầu cốt lõi của người dùng phần mềm rang:

1. **Muốn điều khiển theo ngôn ngữ rang**, không phải theo cấu trúc kỹ thuật của phần mềm.
2. **Muốn dữ liệu có thể truy vết và so sánh**, kể cả cấu hình, nguồn file, năng lượng và các giai đoạn trước/sau mẻ.
3. **Muốn hệ sinh thái mở**, nơi thiết bị, controller, cảm biến và giao diện không bị khóa vào một nhà cung cấp.

Artisan có nền tảng rất mạnh và nhiều yêu cầu đã giải quyết được bằng công cụ có sẵn. Tuy nhiên, chính các luồng này cho thấy sức mạnh đó thường bị che bởi cấu hình phức tạp, thao tác ẩn và giới hạn kiến trúc lâu năm. Đây là cơ hội rõ ràng cho một app/HMI máy rang thế hệ mới: giữ chiều sâu kỹ thuật của Artisan nhưng trình bày bằng workflow trực quan, validation chủ động và dữ liệu tự truy vết.

