// content-mau-toi-thieu.jsx — BỘ KHUNG ĐỂ BẮT ĐẦU MỘT TÀI LIỆU MỚI
//
// Chạy được ngay, không cần thêm ảnh nào:
//     python <skill>\assets\make.py content-mau-toi-thieu.jsx
// hoặc qua MCP:
//     manual_dung(content="_mau/content-mau-toi-thieu.jsx")
//
// Cách dùng: chép file này sang thư mục tài liệu mới, đổi tên, rồi thay nội dung.
// Hai file mẫu ĐẦY ĐỦ (một chương thật đã giao khách) là content-mau-preheat.jsx
// và content-mau-preheat-EN.jsx cạnh đây — xem khi cần ví dụ dày hơn.
//
// ⛔ Ba chỗ hay quên nhất, đều nằm ở đầu file:
//    1. PGPREFIX — không đặt lại thì chân trang in "PH-" của bộ preheat
//    2. IMGDIR   — trỏ vào thư mục ảnh của TÀI LIỆU NÀY
//    3. coverImage — đặt TRƯỚC COVER(), đặt sau là không ăn


// ═══════════════════ 0. KHAI BÁO ĐẦU FILE ═══════════════════
IMGDIR = "F:/Project/112_Quanly/122_Manual_AI/_mau/images/";
PGPREFIX = "MAU-";        // tiền tố số trang ở chân trang

// Bản mang thương hiệu đối tác thì mở 4 dòng dưới. KHÔNG viết tên đối tác vào
// skill — thông tin từng đối tác để ngoài repo, xem mục "Bản OEM" trong SKILL.md.
// coverImage = "<anh-may-da-go-dau-nhan>.png";
// LOGO = "<logo-doi-tac>.png";
// LOGO_W_COVER = 105; LOGO_W_HEAD = 78;   // đo lại khe hở với tiêu đề, dưới 25 pt là chật
// FOOTLINE = "Copyright (c) <phap nhan doi tac>";


// ═══════════════════ 1. BÌA ═══════════════════
coverImage = "may-rang-bia.png";   // may-rang-auto-bia.png = máy Auto
COVER("Máy rang OTL",                                   // dòng nhỏ trên tiêu đề
      "Tên tài liệu",                                   // tiêu đề lớn
      "Dòng phụ 1\nDòng phụ 2",                         // \n xuống dòng
      "Máy áp dụng \u2013 ghi rõ cỡ máy và đời máy",
      "Phiên bản 1.0 \u2013 09/2026          Copyright (c) O Tesla Industry CO., Ltd");


// ═══════════════════ 2. TRANG THÔNG TIN CÔNG TY ═══════════════════
chapterHeader = "Thông tin nhà sản xuất";   // GÁN TRƯỚC addPage()
addPage();
COMPANY("CÔNG TY TNHH CÔNG NGHIỆP O TESLA",
        "Nhà sản xuất máy rang cà phê công nghiệp OTL",
[["Văn phòng", "44 Đường N5, KP. Tân Phước, P. Tân Đông Hiệp, TP. Hồ Chí Minh"],
 ["Nhà máy", "398/33 ĐT743B, KP. Đông Thành, P. Tân Đông Hiệp, TP. Hồ Chí Minh"],
 ["Điện thoại", "0936 198 938 (+84 936 198 938)"],
 ["WhatsApp", "+84 936 198 938"],
 ["Email", "otlpro.com@gmail.com"],
 ["Mã số thuế", "0314844413"],
 ["Tài liệu", "Tên tài liệu"],
 ["Phiên bản", "1.0 \u2013 09/2026"],
 ["Áp dụng cho", "Máy nào dùng được tài liệu này"]],
"LƯU Ý QUAN TRỌNG",
"Đoạn mở đầu nói tài liệu dùng để làm gì và ai được phép làm.\n\u2022 Mỗi gạch đầu dòng một ý.\n\u2022 Dùng \\u2022 cho dấu chấm đầu dòng bên trong hộp.");


// ═══════════════════ 3. MỤC LỤC ═══════════════════
chapterHeader = "Mục lục";
TOCRESERVE();               // giữ chỗ ở đây, vẽ thật bằng TOCDRAW ở cuối file


// ═══════════════════ 4. NỘI DUNG ═══════════════════
chapterHeader = "Chương 1 \u2013 tên chương";
addPage();

H1("1  Tiêu đề chương");

P("Đoạn văn thường, tự canh đều hai bên và tự sang trang. KHÔNG tự tính toạ độ y \u2013 engine đo chiều cao chữ và ngắt trang giúp.");

H2("1", "Tiêu đề mục có huy hiệu tròn xanh");

BUL([
"Gạch đầu dòng thứ nhất.",
"Gạch đầu dòng thứ hai."
]);

STEP(1, "Bước đánh số. Dùng cho quy trình thao tác, mỗi bước một việc làm được.");
STEP(2, "Bước tiếp theo. Câu ngắn, chủ ngữ rõ, tên nút giữ nguyên tiếng Anh như trên HMI.");

H3("Tiêu đề nhỏ");

PI("Đoạn chữ nghiêng xám, dùng cho ghi chú phụ.");

// Bốn loại hộp cảnh báo, theo mức nguy hiểm giảm dần:
SAFETY("nguyhiem",  "NGUY HIỂM \u2013 chết người hoặc thương tật vĩnh viễn", "Nội dung.");
SAFETY("canhbao",   "CẢNH BÁO \u2013 có thể gây thương tích", "Nội dung.");
SAFETY("thantrong", "THẬN TRỌNG \u2013 có thể hỏng máy", "Nội dung.");
SAFETY("luuy",      "LƯU Ý \u2013 thông tin cần biết", "Nội dung.");

RULE();     // đường kẻ ngang
GAPV(10);   // chừa khoảng trắng 10 pt

// Bảng: tổng chiều rộng các cột PHẢI bằng 435.28
TABLE(["Cột 1", "Cột 2", "Cột 3"],
[
["ô 1.1", "ô 1.2", "ô 1.3"],
["ô 2.1", "ô 2.2", "ô 2.3"]
], [150, 140, 145.28]);

// Sơ đồ các bước nối bằng mũi tên: [tên, mô tả, thời gian]
STATEFLOW([
["Bước một", "Mô tả ngắn việc xảy ra ở bước này.", "1 phút"],
["Bước hai", "Mô tả bước kế tiếp.", "2 phút"]
]);

// Ảnh — bỏ chú thích ở đây vì mẫu này không kèm ảnh.
// Thiếu file thì engine vẽ ô nét đứt thay chỗ và báo "thieu anh", vẫn dựng được.
//
// IMG("ten-anh.png", 300, "Hình 1 \u2013 chú thích.");
//
// Ảnh có khung đỏ đánh số: marks = [[x, y, rộng, cao, "số"], ...] theo TỈ LỆ 0–1
// của ảnh, không phải pixel. Vẽ xong phải soi lại, các khung rất hay chồng nhau.
//
// IMGC("ten-anh.png", 330, "Hình 2 \u2013 chú thích.",
// [[0.10, 0.07, 0.45, 0.45, "1"],
//  [0.63, 0.26, 0.26, 0.44, "2"]],
// ["1  Giải thích khung 1.",
//  "2  Giải thích khung 2."]);


// ═══════════════════ 5. VẼ MỤC LỤC + XUẤT FILE ═══════════════════
TOCDRAW("Mục lục", "MAU-");   // tiền tố phải KHỚP với PGPREFIX ở đầu file

var base = "F:/Project/112_Quanly/122_Manual_AI/_mau/";
doc.saveAs(new File(base + "Mau-Toi-Thieu.ai"), new IllustratorSaveOptions());

var po = new PDFSaveOptions();
po.preserveEditability = false;
doc.saveAs(new File(base + "Mau-Toi-Thieu.pdf"), po);

var msg = "OK pages=" + doc.artboards.length;
if (missing.length > 0) msg += " | thieu anh: " + missing.join(", ");
msg;
