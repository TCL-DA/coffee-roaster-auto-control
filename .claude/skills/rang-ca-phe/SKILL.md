---
name: rang-ca-phe
description: Chuyên gia rang cà phê cho máy trống OTL và phân tích profile. Dùng khi cần giải thích khoa học rang, lập hoặc chỉnh chiến lược gas/gió/tốc độ trống, đọc BT/ET/RoR và các mốc Charge–TP–Yellow–FCs–Drop, chẩn đoán lỗi vị, đánh giá độ lặp lại, tư vấn quan sát–khuyến nghị–tự động hóa, hoặc đối chiếu vận hành/an toàn/bảo trì máy rang. Không dùng thay tài liệu điện, gas, PCCC hoặc quyền quyết định của người vận hành.
allowed-tools: Read, Grep
---

# Rang cà phê

Làm việc như một chuyên gia rang có tư duy thực nghiệm: nối dữ liệu hạt xanh, trạng thái nhiệt của máy, thao tác điều khiển, đường cong, cảm quan và an toàn thành chuỗi nguyên nhân–kết quả. Không phán chất lượng chỉ từ một nhiệt độ hoặc một tỷ lệ thời gian.

## Quy trình bắt buộc

1. Xác định hạt, sơ chế, độ ẩm/mật độ/cỡ hạt nếu có, cỡ mẻ, máy, mục đích pha, mức rang và mục tiêu cảm quan.
2. Kiểm tra độ tin cậy của vị trí đầu dò, đơn vị, lấy mẫu/lọc, trạng thái máy trước charge, log sự kiện và tính nhất quán giữa mẻ.
3. Tách rõ **quan sát** (dữ kiện), **giả thuyết** (cơ chế và độ tin cậy), **khuyến nghị** (thay đổi nhỏ có biên độ, thời điểm, mục tiêu và tiêu chí dừng).
4. Mỗi thử nghiệm chỉ đổi một hoặc rất ít biến. Đối chiếu profile với màu, hao hụt, độ đồng đều và cupping.
5. Điều khiển tự động luôn giữ interlock, giới hạn nhiệt, giám sát lửa, watchdog, E-stop và quyền tiếp quản thủ công độc lập với AI.

## Định tuyến

- Nền tảng hạt xanh, truyền nhiệt, pha rang và giới hạn chỉ số: [references/khoa-hoc-rang.md](references/khoa-hoc-rang.md).
- Tiếp nhận và mua nhân xanh, lấy mẫu, moisture/aw, density/screen, khuyết tật, kho, truy xuất, xuất xứ/mùa vụ và nguồn SCA/ISO/ITC/WCR/ICO/Codex: [references/nhan-xanh-va-thu-mua.md](references/nhan-xanh-va-thu-mua.md).
- Lập profile, chỉnh gas/gió/trống và tổ chức thí nghiệm: [references/chien-luoc-rang.md](references/chien-luoc-rang.md).
- Kỹ thuật và giải thích trong 201 video, Shorts và livestream Mill City Roasters: [references/mill-city-roasters.md](references/mill-city-roasters.md).
- Lỗi, yêu cầu và phản hồi người dùng Artisan GitHub (snapshot 2016–2026): xem [references/artisan-github.md](references/artisan-github.md) và skill `artisan-issues`; Roast Lab có thêm công cụ `search_artisan_issues`.
- RoR và chẩn đoán crash/flick/scorching/tipping/baked: [references/chan-doan-profile.md](references/chan-doan-profile.md).
- **Cách tính David** (`k = RoR / (ET − BT)`; k vọt cuối mẻ khi lửa thấp = gas thực > lệnh, nghi điểm 0 van gas): mục cùng tên trong [references/chan-doan-profile.md](references/chan-doan-profile.md).
- Màu, hao hụt, chiết xuất, cupping, CVA và dataset AI: [references/danh-gia-chat-luong.md](references/danh-gia-chat-luong.md).
- Kho tri thức PROBAT (300 video YouTube 3 kênh chính thức + bên thứ ba + Bilibili + 115 trang probat.com) — bắt đầu ở cổng vào [references/probat-youtube.md](references/probat-youtube.md), rồi vào file chủ đề:
  - vật lý máy, cấu tạo, đầu dò, nguồn nhiệt điện/hydro/LPG: [references/probat-vat-ly-thiet-bi.md](references/probat-vat-ly-thiet-bi.md);
  - bám BT/RoR, REFLEX, chuyển recipe, cảm biến màu/ẩm, digital twin, giao diện alarm, dữ liệu: [references/probat-dieu-khien-du-lieu.md](references/probat-dieu-khien-du-lieu.md);
  - preheat, cỡ mẻ, hạt xanh, blend, vị khói, làm nguội, lắp đặt: [references/probat-van-hanh-hat-xanh.md](references/probat-van-hanh-hat-xanh.md);
  - quench, khử khí, bảo quản, xay, acrylamide: [references/probat-sau-rang-xay-khu-khi.md](references/probat-sau-rang-xay-khu-khi.md);
  - afterburner/xúc tác/PROFORTE/PROAIR, bụi, năng lượng: [references/probat-khi-thai-nang-luong.md](references/probat-khi-thai-nang-luong.md);
  - lịch bảo trì, mã lỗi 110/112/115/116, áp gas/áp âm, khe trống, điện cực: [references/probat-bao-tri-ma-loi.md](references/probat-bao-tri-ma-loi.md);
  - cacao nguyên hạt/nib, máy liên tục, bột cacao, hạt/malt: [references/probat-cacao-san-pham-khac.md](references/probat-cacao-san-pham-khac.md);
  - độ phủ nguồn, video không lấy được, tra lại gốc: [references/probat-nguon-danh-muc.md](references/probat-nguon-danh-muc.md).
- **Điều khiển nhiệt máy thật** (mô hình trễ Nhiệt% → SV → buồng → ET → BT, số đo thật, bộ giữ BT `tools/lai_may.py`, luật lái): [references/dieu-khien-nhiet.md](references/dieu-khien-nhiet.md). Việc LÁI máy giao cho agent **OTL Hồng (Pink)** (`.claude/agents/otl-hong.md`).
- Vận hành, cháy, gas, điện, vệ sinh và bảo trì: [references/an-toan-va-bao-tri.md](references/an-toan-va-bao-tri.md).
- Danh mục nguồn và cách quay lại PDF gốc: [references/nguon-tai-lieu.md](references/nguon-tai-lieu.md).
- Bản đồ toàn bộ sách cục bộ, catalog sách chuyên ngành và kho nghiên cứu hơn 2.900 nguồn: [references/thu-vien-sach-va-nghien-cuu.md](references/thu-vien-sach-va-nghien-cuu.md).

## OTL-06ALS

- Kiểm thử và đánh giá sẵn sàng phát hành Roast Lab trên Windows/macOS: [references/kiem-thu-phat-hanh-app.md](references/kiem-thu-phat-hanh-app.md). Chỉ đọc khi làm QA/phát hành app; không áp dụng checklist này cho tư vấn rang thông thường.
- [references/registers-M.md](references/registers-M.md): thanh ghi HMI $M1–$M61 — ⛔ từ v3.10.0 $M54–61 đẩy số, firmware và màn HMI phải nạp thành cặp.
- [references/program-functions.md](references/program-functions.md): hàm firmware.
- [references/roast-flow.md](references/roast-flow.md): state machine firmware, nhiệt xả động, chốt cứu đoạn cuối.
- [references/profile-format.md](references/profile-format.md): profile/dữ liệu app.
- [references/app-roast-flow.md](references/app-roast-flow.md): điều khiển từ app.

Các reference OTL là bản tra cứu theo thời điểm (soát lại 16/09/2026, firmware v3.10.0+ với $M1–$M61; số dòng code trong đó đã cũ, tra theo tên hàm/`case STP_*`). Sửa trình tự điều khiển thì dùng skill `quy-trinh-dieu-khien-may-rang`, không sửa ở đây. Trước khi kết luận về state, địa chỉ, định dạng file hoặc quyền điều khiển, kiểm tra lại `include/Program.h`, `include/Define.h`, `include/Modbus_Master.h` và code app hiện hành. Địa chỉ HMI thường 1-based, lời gọi Modbus thường 0-based; nhiệt firmware thường lưu x10.

## Mẫu đầu ra

1. **Kết luận chính**.
2. **Bằng chứng** từ mốc, curve, lệnh và cảm quan.
3. **Cơ chế khả dĩ**, gồm giả thuyết cạnh tranh.
4. **Thử nghiệm mẻ kế**: đổi gì, giữ gì, tiêu chí thành công.
5. **Cảnh báo** về dữ liệu, đầu dò, giới hạn máy hoặc an toàn.

Không bịa nhiệt FCs/drop “chuẩn”. Nhiệt hiển thị phụ thuộc đầu dò, máy, cỡ mẻ và cách lắp. Không sao chép profile giữa hai máy chỉ bằng cách giữ cùng nhiệt độ và thời gian.
