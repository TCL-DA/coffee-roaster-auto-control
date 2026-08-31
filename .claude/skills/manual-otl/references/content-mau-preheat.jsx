// content.jsx — chương "Làm nóng máy tự động (Warm-up)" — tiếng Việt
// Ảnh màn hình thật: main.bmp, config page.bmp, preheat.bmp, config.bmp

// ═══════════════════ TRANG BÌA ═══════════════════
coverImage = "may-rang-auto-bia.png";   // ảnh máy Auto
COVER("OTL Roaster",
      "Hướng dẫn sử dụng",
      "Chức năng Làm nóng máy tự động\n(Preheat / Warm-up)",
      "Máy rang cà phê OTL Auto \u2013 bảng điều khiển HMI",
      "Phiên bản 1.0 \u2013 08/2026          Copyright (c) O Tesla Industry CO., Ltd");

// ═══════════════════ TRANG THÔNG TIN CÔNG TY ═══════════════════
chapterHeader = "Thông tin nhà sản xuất";
addPage();
COMPANY("CÔNG TY TNHH CÔNG NGHIỆP O TESLA",
        "O Tesla Industry Co., Ltd – Nhà sản xuất máy rang cà phê công nghiệp OTL",
[["Văn phòng", "44 Đường N5, KP. Tân Phước, P. Tân Đông Hiệp, TP. HCM"],
 ["Nhà máy", "398/33 ĐT743B, KP Đông Thành, P. Tân Đông Hiệp, TP. HCM"],
 ["Điện thoại", "0936 198 938"],
 ["Email", "otesla.vn@gmail.com"],
 ["Mã số thuế", "0314844413"],
 ["Tài liệu", "Hướng dẫn sử dụng – Chức năng Làm nóng máy tự động (Preheat / Warm-up)"],
 ["Phiên bản", "1.0 – 08/2026"],
 ["Áp dụng cho", "Máy rang cà phê OTL Auto có chức năng làm nóng tự động"]],
"LƯU Ý QUAN TRỌNG",
"Tài liệu này giúp người vận hành sử dụng máy đúng trình tự và an toàn. Người vận hành phải đủ sức khoẻ, tuân thủ mọi quy định phòng cháy chữa cháy tại địa phương và làm đúng hướng dẫn trong tài liệu.\n• Phải đọc kỹ toàn bộ tài liệu trước khi sử dụng máy.\n• Giữ tài liệu ở gần máy để tra cứu được ngay trong mọi tình huống.\n• Nội dung có thể thay đổi theo phiên bản phần mềm điều khiển. Liên hệ O Tesla để nhận bản mới nhất.");

// ═══════════════════ MỤC LỤC (giữ chỗ, vẽ ở cuối) ═══════════════════
chapterHeader = "Mục lục";
TOCRESERVE();


// ═══════════════════ MỞ CHƯƠNG ═══════════════════
chapterHeader = "Làm nóng máy tự động";
addPage();

H1("Làm nóng máy tự động (Warm-up)");

P("Trước mỗi ngày rang, thân trống và toàn bộ khối gang của máy phải được đưa lên đúng nhiệt độ làm việc. Nếu vào mẻ khi máy chưa đủ nóng, mẻ đầu tiên luôn bị hụt nhiệt: hạt vào trống bị \u201Csốc\u201D nhiệt kém, thời gian tới mốc nứt kéo dài, mẻ đầu không bao giờ giống các mẻ sau.");

P("Ở các dòng máy trước, người vận hành phải tự bật lửa rồi canh đồng hồ 15 \u2013 30 phút, tự tay chỉnh gas cho nhiệt lên vừa phải. Cách làm này phụ thuộc hoàn toàn vào tay nghề và trí nhớ của từng người.");

P("Máy rang OTL Auto có chức năng làm nóng tự động. Người vận hành chỉ cần nhập nhiệt độ mong muốn và thời gian làm nóng trong cửa sổ Preheat, rồi bấm START. Máy sẽ tự thổi sạch buồng đốt, tự mồi lửa, tự điều chỉnh mức gas để đưa nhiệt độ hạt (BT) lên đúng mức đặt, sau đó tự giữ nhiệt độ đó ổn định trong khoảng \u00b12 \u00b0C cho tới khi hết thời gian đã cài.");

IMGC("main.bmp", 400, "Hình 1 \u2013 Màn hình chính của máy rang OTL Auto.",
[[0.004, 0.850, 0.090, 0.147, "1"],
 [0.812, 0.238, 0.180, 0.175, "2"],
 [0.812, 0.660, 0.180, 0.105, "3"],
 [0.812, 0.765, 0.180, 0.100, "4"]],
["1  Nút Setup \u2013 mở trang chức năng phụ, từ đó vào cửa sổ Preheat.",
 "2  Nhiệt độ hạt (BT) và nhiệt độ khí thải (ET) \u2013 hai giá trị theo dõi khi làm nóng.",
 "3  Mức gas của đầu đốt (Burner).",
 "4  Mức gió của quạt hút (Airflow)."]);

H3("Nội dung chương này");
BUL([
"Cảnh báo an toàn bắt buộc đọc trước khi vận hành.",
"Nguyên lý làm việc và 6 giai đoạn của chu trình làm nóng.",
"Các điều kiện phải kiểm tra trước khi bắt đầu.",
"Hướng dẫn vận hành từng bước trên màn hình.",
"Chức năng tự học PID trong lần chạy đầu tiên.",
"Bảng nhận biết và xử lý sự cố.",
"Phụ lục tham số kỹ thuật."
]);

// ═══════════════════ AN TOÀN ═══════════════════
chapterHeader = "Làm nóng máy tự động \u2013 An toàn";
addPage();
H1("1  An toàn");

P("Chức năng làm nóng tự động điều khiển trực tiếp van gas và ngọn lửa của đầu đốt. Người vận hành phải đọc và hiểu toàn bộ các cảnh báo dưới đây trước khi sử dụng.");

SAFETY("nguyhiem", "NGUY HIỂM \u2013 Nguy cơ cháy nổ khí gas",
"Khí gas rò rỉ tích tụ trong buồng đốt có thể gây nổ, dẫn đến tử vong hoặc thương tích nặng.\n\u2022 Trước khi bấm START, phải kiểm tra toàn bộ đường ống và van gas, bảo đảm không có mùi gas trong khu vực.\n\u2022 Không được vô hiệu hoá, tháo bỏ hoặc che chắn cảm biến lửa. Máy dựa vào cảm biến này để xác nhận đã có lửa.\n\u2022 Nếu máy báo mồi lửa thất bại, phải KHOÁ VAN GAS TAY và tìm nguyên nhân trước khi thử lại. Tuyệt đối không bấm mồi lại liên tục.");

SAFETY("canhbao", "CẢNH BÁO \u2013 Bề mặt nóng",
"Trong và sau khi làm nóng, thân trống, cửa lấy mẫu, ống khói và cụm đầu đốt có nhiệt độ trên 200 \u00b0C. Chạm vào sẽ gây bỏng nặng.\n\u2022 Luôn dùng găng tay chịu nhiệt khi thao tác gần các bộ phận này.\n\u2022 Không đặt vật dễ cháy (bao bì, giẻ lau, can nhựa) trong bán kính 1 m quanh máy.");

SAFETY("canhbao", "CẢNH BÁO \u2013 Máy tự khởi động thiết bị",
"Khi chức năng làm nóng đang chạy, máy tự động mở van gas, tự chỉnh mức gas và tự chỉnh quạt hút mà không cần thao tác của người vận hành.\n\u2022 Không được đưa tay vào trống, phễu nạp hoặc khoang làm nguội khi chu trình làm nóng đang chạy.\n\u2022 Muốn dừng ngay lập tức: tắt chức năng làm nóng trên cửa sổ Preheat, hoặc nhấn nút DỪNG KHẨN CẤP.");

SAFETY("thantrong", "THẬN TRỌNG \u2013 Phải có quạt hút chạy",
"Quạt hút phải hoạt động trong suốt quá trình làm nóng để thải khí cháy. Nếu quạt hút hỏng hoặc ống khói bị nghẹt, khí cháy sẽ tràn vào xưởng.");

SAFETY("luuy", "LƯU Ý \u2013 Không nạp cà phê trong lúc làm nóng",
"Trống phải rỗng trong toàn bộ quá trình làm nóng. Cà phê nằm trong trống suốt giai đoạn này sẽ bị cháy sém bề mặt và mẻ rang coi như hỏng.");

// ═══════════════════ NGUYÊN LÝ ═══════════════════
chapterHeader = "Làm nóng máy tự động \u2013 Nguyên lý";
addPage();
H1("2  Nguyên lý làm việc");

P("Chu trình làm nóng gồm 6 giai đoạn nối tiếp nhau. Máy tự chuyển giai đoạn theo nhiệt độ đo được và theo tín hiệu cảm biến lửa; người vận hành không phải can thiệp.");

STATEFLOW([
["Chờ", "Máy nhận quyền điều khiển gas và gió, khoá van gas về 0 %.", "vài giây"],
["Hạ nhiệt", "Chỉ chạy khi máy còn nóng hơn nhiệt độ đặt. Gió mở 60 %, gas tắt, chờ nhiệt tụt xuống.", "thay đổi"],
["Thổi sạch buồng đốt", "Gió 60 % thổi hết khí gas dư trong buồng đốt trước khi có tia lửa.", "8 giây"],
["Mồi lửa", "Mở van gas, gas 30 % và gió 30 %, chờ cảm biến báo có lửa. Thử tối đa 3 lần.", "3 \u00d7 60 giây"],
["Lên nhiệt", "Bộ điều khiển PID tự tăng giảm gas để kéo nhiệt độ hạt lên mức đặt, không vọt lố.", "10 \u2013 20 phút"],
["Giữ nhiệt", "Nhiệt độ đã đạt. Máy giữ quanh mức đặt trong khoảng \u00b12 \u00b0C cho tới hết giờ.", "tới hết giờ"]
]);

P("Hai lớp bảo vệ luôn hoạt động song song trong mọi giai đoạn:");
BUL([
"Nếu nhiệt độ hạt vượt quá mức đặt 15 \u00b0C: máy cắt gas về 0 % và mở gió tối đa cho tới khi nhiệt hạ xuống. Chu trình làm nóng vẫn tiếp tục.",
"Nếu chênh lệch giữa nhiệt độ khí thải (ET) và nhiệt độ hạt (BT) vượt quá 160 \u00b0C: máy hiểu là một trong hai cảm biến có sự cố, lập tức huỷ chu trình, đóng van gas và báo lỗi."
]);

// ═══════════════════ TRƯỚC KHI BẮT ĐẦU ═══════════════════
chapterHeader = "Làm nóng máy tự động \u2013 Chuẩn bị";
addPage();
H1("3  Kiểm tra trước khi bắt đầu");

P("Thực hiện đủ các mục dưới đây trước mỗi lần làm nóng. Bỏ qua một mục có thể làm hỏng chu trình hoặc gây mất an toàn.");

TABLE(["", "Hạng mục kiểm tra", "Yêu cầu"],
[
["\u25A1", "Trống rang", "Rỗng hoàn toàn, không còn hạt của mẻ trước."],
["\u25A1", "Cửa xả và cửa nạp", "Đóng kín. Xy-lanh ở vị trí đóng."],
["\u25A1", "Van gas tay", "Mở hoàn toàn. Áp gas trong dải cho phép của đầu đốt."],
["\u25A1", "Mùi gas", "Không có mùi gas trong khu vực máy."],
["\u25A1", "Quạt hút và ống khói", "Quạt chạy êm, ống khói thông, cyclone đã được vệ sinh."],
["\u25A1", "Cảm biến BT và ET", "Cả hai đều hiện số hợp lý trên màn hình, chênh nhau không quá 160 \u00b0C."],
["\u25A1", "Nút dừng khẩn cấp", "Đã nhả, mạch an toàn đã được reset (đèn xanh sáng)."],
["\u25A1", "Khu vực quanh máy", "Không có vật dễ cháy trong bán kính 1 m."]
], [24, 176, 235.28]);

SAFETY("thantrong", "THẬN TRỌNG \u2013 Cảm biến lệch nhau",
"Nếu ngay từ lúc máy nguội mà BT và ET đã chênh nhau nhiều, gần như chắc chắn một trong hai đầu dò hoặc dây tín hiệu có vấn đề. Không được chạy làm nóng cho tới khi sửa xong.");

// ═══════════════════ CÁC BƯỚC VẬN HÀNH ═══════════════════
chapterHeader = "Làm nóng máy tự động \u2013 Vận hành";
addPage();
H1("4  Hướng dẫn vận hành từng bước");

H2(1, "Cấp nguồn và mở mạch an toàn");
STEPIMG(1, "Bật công tắc nguồn chính sang vị trí ON.", "cong-tac-nguon.png", "", 66);
STEPIMG(2, "Xoay nút dừng khẩn cấp theo chiều kim đồng hồ để nhả nút.", "nut-dung-khan.png", "", 58);
STEPIMG(3, "Bấm nút Reset Circuit để cấp điện cho mạch điều khiển. Đèn xanh trên nút sẽ sáng.", "nut-reset-circuit.png", "", 46);

H2(2, "Mở cửa sổ Preheat");
STEPIMG(4, "Trên màn hình chính, bấm nút Setup ở góc dưới bên trái.", "nut-setup.png", "", 40);
STEPIMG(5, "Trong trang chức năng phụ, bấm nút Preheat.", "nut-preheat-menu.png", "", 110);

IMGC("config page.bmp", 330, "Hình 2 \u2013 Trang chức năng phụ. Nút Preheat nằm ở hàng trên.",
[[0.494, 0.238, 0.250, 0.140, "1"]],
[]);

// ═══════════════════ CỬA SỔ PREHEAT ═══════════════════

H2(3, "Đặt nhiệt độ và thời gian");

IMGC("preheat.bmp", 300, "Hình 3 \u2013 Cửa sổ Preheat.",
[[0.015, 0.020, 0.330, 0.190, "1"],
 [0.660, 0.020, 0.325, 0.190, "2"],
 [0.025, 0.280, 0.465, 0.235, "3"],
 [0.505, 0.280, 0.470, 0.235, "4"],
 [0.025, 0.525, 0.950, 0.170, "5"],
 [0.025, 0.735, 0.950, 0.225, "6"]],
["1  Bean temp \u2013 nhiệt độ hạt hiện tại của máy.",
 "2  Target \u2013 nhiệt độ đích máy đang hướng tới.",
 "3  Set temp \u2013 ô đặt nhiệt độ làm nóng, chỉnh bằng phím \u2013 và +.",
 "4  Set time \u2013 ô đặt thời gian làm nóng tính bằng phút.",
 "5  Process \u2013 thanh tiến trình của chu trình làm nóng.",
 "6  START \u2013 nút bắt đầu và kết thúc chu trình làm nóng."]);

STEP(6, "Đặt Set temp bằng phím \u2013 và + tới nhiệt độ hạt mong muốn. Giá trị thường dùng: 180 \u2013 200 \u00b0C cho cà phê nhân, 150 \u2013 170 \u00b0C cho ca cao.");
STEP(7, "Đặt Set time tới tổng thời gian làm nóng tính bằng phút. Giá trị thường dùng: 20 \u2013 30 phút. Hết khoảng thời gian này máy tự tắt lửa và kết thúc chu trình.");

PI("Ghi chú: thời gian làm nóng được tính từ lúc mồi lửa thành công, không tính khoảng thổi sạch buồng đốt.");

H2(4, "Bắt đầu làm nóng");
STEPIMG(8, "Bấm nút START. Máy bắt đầu chu trình: thổi sạch buồng đốt rồi mồi lửa.", "nut-start-preheat.png", "", 220);
STEP(9, "Đứng quan sát cho tới khi máy mồi lửa thành công và nhiệt độ hạt bắt đầu tăng. Từ lúc này máy chạy hoàn toàn tự động, người vận hành có thể làm việc khác trong xưởng nhưng không được rời khỏi khu vực máy.");

SAFETY("canhbao", "CẢNH BÁO \u2013 Không rời máy khi đang mồi lửa",
"Phải đứng quan sát máy trong suốt giai đoạn thổi sạch buồng đốt và mồi lửa. Chỉ được rời vị trí sau khi nhiệt độ hạt đã tăng đều, xác nhận lửa cháy ổn định.");

// ═══════════════════ TRONG QUÁ TRÌNH ═══════════════════
chapterHeader = "Làm nóng máy tự động \u2013 Theo dõi";
addPage();
H1("5  Theo dõi trong lúc máy làm nóng");

P("Bảng dưới đây cho biết máy đang làm gì ở từng giai đoạn, màn hình hiển thị ra sao và người vận hành cần chú ý điều gì.");

TABLE(["Giai đoạn", "Máy đang làm", "Trên màn hình", "Người vận hành"],
[
["Hạ nhiệt", "Gas 0 %, gió 60 %, chờ nhiệt tụt về mức đặt.", "Bean temp giảm dần, Burner bằng 0.", "Chờ. Không tắt quạt hút."],
["Thổi sạch", "Gió 60 % trong 8 giây, van gas vẫn đóng.", "Airflow tăng, Burner bằng 0.", "Đứng quan sát."],
["Mồi lửa", "Van gas mở, gas 30 %, gió 30 %, chờ tín hiệu lửa.", "Burner hiện 30 %, Bean temp bắt đầu nhích lên.", "Quan sát. Có mùi gas thì tắt ngay."],
["Tự học PID", "Chỉ ở lần đầu của mỗi mức nhiệt. Máy cho nhiệt dao động quanh một mức thấp hơn để đo đặc tính lò.", "Thanh Process tăng dần theo số chu kỳ đo.", "Chờ, không chỉnh tay."],
["Lên nhiệt", "Bộ PID tự tăng giảm gas theo tiến độ.", "Bean temp tăng đều, Burner thay đổi liên tục.", "Có thể làm việc khác gần máy."],
["Giữ nhiệt", "Giữ nhiệt độ quanh mức đặt \u00b12 \u00b0C.", "Bean temp bám sát Target, Burner nhỏ và ổn định.", "Chuẩn bị cà phê cho mẻ đầu."]
], [70, 150, 118, 97.28]);

PI("Trong lúc làm nóng, mức gas và mức gió trên màn hình chính do máy tự đặt. Xoay biến trở hoặc chỉnh tay lúc này sẽ không có tác dụng cho tới khi chu trình kết thúc.");

// ═══════════════════ TỰ HỌC PID ═══════════════════
chapterHeader = "Làm nóng máy tự động \u2013 Tự học PID";
addPage();
H1("6  Chức năng tự học trong lần chạy đầu");

P("Mỗi lò rang có đặc tính nhiệt riêng: khối lượng gang, công suất đầu đốt, chiều dài ống khói, chất lượng gas. Vì vậy máy không dùng một bộ tham số cố định mà tự đo đặc tính của chính lò mình rồi tính ra bộ tham số điều khiển phù hợp.");

H3("Khi nào máy tự học");
BUL([
"Lần đầu tiên chạy làm nóng ở một mức nhiệt độ mới.",
"Sau khi kết quả giữ nhiệt của lần trước bị đánh giá là chưa đạt (lệch quá \u00b12 \u00b0C).",
"Máy phải đang đủ nguội. Nếu máy còn nóng sẵn, máy bỏ qua bước tự học và dùng bộ tham số dự phòng."
]);

H3("Máy làm gì khi tự học");
P("Máy cho mức gas đóng \u2013 mở luân phiên quanh một mức nhiệt thấp hơn nhiệt độ đặt để nhiệt độ hạt dao động lên xuống. Từ biên độ và chu kỳ của dao động đó, máy tính ra ba hệ số điều khiển và ghi vào thẻ nhớ. Quá trình này mất khoảng 5 \u2013 10 phút và chỉ chạy một lần cho mỗi mức nhiệt.");

PI("Ghi chú: nếu quá trình tự học kéo dài quá 10 phút mà chưa xong, máy tự bỏ qua và chuyển sang lên nhiệt bằng bộ tham số dự phòng. Đây không phải lỗi.");

H3("Sau khi tự học xong");
BUL([
"Máy nhớ được tối đa 8 mức nhiệt độ khác nhau. Hai mức chênh nhau không quá 15 \u00b0C được coi là cùng một mức.",
"Từ lần thứ hai trở đi, máy dùng lại bộ tham số đã lưu và đi thẳng vào giai đoạn lên nhiệt.",
"Cuối mỗi lần làm nóng, máy tự chấm điểm độ ổn định. Nếu chưa đạt, máy tự xoá bộ tham số của mức đó và sẽ tự học lại ở lần sau. Người vận hành không phải thao tác gì."
]);

// ═══════════════════ KẾT THÚC ═══════════════════
chapterHeader = "Làm nóng máy tự động \u2013 Kết thúc";
addPage();
H1("7  Kết thúc chu trình và vào mẻ rang");

H3("Máy tự kết thúc");
P("Khi chạy hết thời gian đã cài trong ô Set time, máy tự động tắt lửa, đóng van gas, trả quyền điều khiển gas và gió lại cho người vận hành, đồng thời tự tắt chức năng làm nóng. Trống vẫn quay và quạt hút vẫn chạy.");

H3("Dừng sớm bằng tay");
STEP(1, "Mở lại cửa sổ Preheat và tắt chức năng làm nóng. Máy đóng van gas ngay lập tức và huỷ chu trình.");
STEP(2, "Chờ nhiệt độ ổn định trở lại trước khi bắt đầu thao tác khác.");

SAFETY("luuy", "LƯU Ý \u2013 Vào mẻ ngay sau khi làm nóng",
"Nên vào mẻ đầu tiên trong vòng 5 phút sau khi kết thúc làm nóng. Để lâu hơn, khối gang nguội dần và mẻ đầu vẫn bị hụt nhiệt như khi không làm nóng.");

H3("Chuyển sang rang");
BUL([
"Kiểm tra Bean temp trên màn hình chính đúng bằng nhiệt độ nạp mong muốn.",
"Nạp cà phê vào phễu và tiến hành theo chương Vận hành máy rang.",
"Nếu chuyển sang chế độ rang tự động, kiểm tra hồ sơ rang đã được chọn đúng."
]);

// ═══════════════════ SỰ CỐ ═══════════════════
chapterHeader = "Làm nóng máy tự động \u2013 Sự cố";
addPage();
H1("8  Sự cố và cách xử lý");

TABLE(["Hiện tượng", "Nguyên nhân có thể", "Cách xử lý"],
[
["Máy báo mồi lửa thất bại sau 3 lần thử.",
 "Hết gas hoặc van gas tay còn khoá. Kim đánh lửa bẩn, mòn, sai khe hở. Cảm biến lửa bẩn hoặc đứt dây. Gió mồi quá mạnh thổi tắt lửa.",
 "Khoá van gas tay. Kiểm tra áp gas, vệ sinh kim đánh lửa và cảm biến lửa, chỉnh lại khe hở theo tài liệu đầu đốt. Sau đó mới thử lại."],
["Máy báo lỗi lệch nhiệt độ và tự đóng gas.",
 "Chênh lệch giữa nhiệt độ khí thải và nhiệt độ hạt vượt quá 160 \u00b0C. Thường do một đầu dò tuột khỏi vị trí, đứt dây hoặc hỏng bộ chuyển đổi tín hiệu.",
 "Kiểm tra cả hai đầu dò và dây tín hiệu. So sánh hai giá trị lúc máy nguội: chênh nhau nhiều là có hỏng hóc."],
["Nhiệt độ vọt cao hơn mức đặt rồi máy cắt gas, mở gió tối đa.",
 "Đây là lớp bảo vệ chống vọt lố, không phải hỏng hóc. Thường gặp khi máy còn nhiệt dư từ mẻ trước hoặc bộ tham số chưa được học lại.",
 "Để máy tự xử lý. Nếu lặp lại nhiều lần, chạy làm nóng khi máy đã nguội hẳn để máy tự học lại."],
["Nhiệt độ lên rất chậm hoặc không tới được mức đặt.",
 "Áp gas thấp, đầu đốt bẩn, quạt hút mở quá lớn kéo hết nhiệt ra ngoài, hoặc cửa nạp và cửa xả không kín.",
 "Kiểm tra áp gas và vệ sinh đầu đốt. Kiểm tra độ kín các cửa. Kiểm tra ống khói và cyclone có bị nghẹt không."],
["Nhiệt độ dao động lên xuống quanh mức đặt quá nhiều.",
 "Bộ tham số của mức nhiệt này chưa phù hợp.",
 "Máy tự nhận biết và sẽ tự học lại ở lần làm nóng kế tiếp. Nếu vẫn còn, gọi kỹ thuật của O Tesla."],
["Thời gian tự học kéo dài rồi máy bỏ qua.",
 "Máy còn nóng nên nhiệt độ không tụt xuống đủ để đo dao động.",
 "Không phải lỗi. Muốn máy học đúng, chạy làm nóng khi máy đã nguội hẳn từ đầu ca."],
["Bấm START nhưng máy không phản ứng.",
 "Mạch an toàn chưa được reset, nút dừng khẩn còn nhấn, hoặc máy đang trong một chu trình khác.",
 "Reset mạch an toàn, kiểm tra nút dừng khẩn, bảo đảm máy không đang chạy mẻ rang."],
["Mồi lửa lâu hơn bình thường ở máy dùng bếp premix.",
 "Bếp premix mồi chậm, khoảng 40 giây mới bắt lửa.",
 "Bình thường. Kiểm tra công tắc Premix burner trong trang Config đã bật đúng loại đầu đốt của máy."]
], [110, 165, 160.28]);

// ═══════════════════ PHỤ LỤC ═══════════════════
chapterHeader = "Làm nóng máy tự động \u2013 Phụ lục";
addPage();
H1("Phụ lục A  Tham số kỹ thuật");

P("Các giá trị dưới đây được cài đặt sẵn trong phần mềm điều khiển. Chỉ kỹ thuật viên được O Tesla uỷ quyền mới được thay đổi.");

TABLE(["Tham số", "Giá trị", "Ý nghĩa"],
[
["Thời gian thổi sạch buồng đốt", "8 giây", "Thổi hết khí gas dư trước khi có tia lửa."],
["Mức gió khi thổi sạch và hạ nhiệt", "60 %", "Mức quạt hút trong giai đoạn chuẩn bị."],
["Mức gas khi mồi lửa", "30 %", "Mức gas dùng để mồi."],
["Mức gió khi mồi lửa", "30 %", "Giữ lửa mồi không bị thổi tắt."],
["Thời gian chờ tín hiệu lửa", "60 giây", "Đầu đốt premix: 65 giây."],
["Số lần thử mồi lại", "3 lần", "Hết 3 lần thì báo lỗi và đóng gas."],
["Dải coi như đã đạt nhiệt", "\u00b13 \u00b0C", "Vào dải này máy chuyển sang giữ nhiệt."],
["Mục tiêu ổn định khi giữ nhiệt", "\u00b12 \u00b0C", "Vượt dải này thì máy sẽ tự học lại."],
["Ngưỡng cắt gas chống vọt lố", "mức đặt + 15 \u00b0C", "Cắt gas, mở gió tối đa."],
["Ngưỡng huỷ do lệch cảm biến", "160 \u00b0C", "Chênh lệch giữa ET và BT."],
["Số mức nhiệt nhớ được", "8 mức", "Hai mức chênh dưới 15 \u00b0C coi là một."],
["Thời gian tối đa cho tự học", "10 phút", "Quá giờ thì dùng tham số dự phòng."]
], [175, 100, 160.28]);

// ═══════════════════ PHỤ LỤC B ═══════════════════
chapterHeader = "Làm nóng máy tự động \u2013 Phụ lục";
addPage();
H1("Phụ lục B  Chọn loại đầu đốt");

P("Máy dùng bộ tham số mồi lửa khác nhau cho hai loại đầu đốt. Chọn sai loại sẽ làm máy báo mồi lửa thất bại dù đầu đốt vẫn tốt.");

IMGC("config.bmp", 330, "Hình 4 \u2013 Trang Config. Công tắc Premix burner nằm ở hàng dưới bên trái.",
[[0.340, 0.735, 0.155, 0.215, "1"]],
["1  Premix burner \u2013 bật khi máy dùng đầu đốt premix (khí và gió trộn sẵn), tắt khi dùng đầu đốt thường."]);

TABLE(["Loại đầu đốt", "Công tắc Premix burner", "Thời gian chờ lửa"],
[
["Đầu đốt thường (khuếch tán)", "TẮT", "60 giây"],
["Đầu đốt premix (trộn sẵn)", "BẬT", "65 giây"]
], [175, 130, 130.28]);

SAFETY("thantrong", "THẬN TRỌNG \u2013 Chỉ đổi khi thay đầu đốt",
"Công tắc này phải khớp với đầu đốt thực tế đang lắp trên máy. Người vận hành không được tự đổi; chỉ kỹ thuật viên đổi khi thay đầu đốt.");

RULE();
PI("Tài liệu này áp dụng cho máy rang cà phê OTL Auto có chức năng làm nóng tự động. Mọi thắc mắc kỹ thuật xin liên hệ O Tesla Industry Co., Ltd.");

TOCDRAW("Mục lục", "PH-");
// ═══════════════════ XUẤT FILE ═══════════════════
var base = "F:/Project/112_Quanly/122_Manual_AI/preheat-vi/build/";
var ai = new File(base + "Huong-dan-Lam-nong-may-VI.ai");
var saveOpt = new IllustratorSaveOptions();
doc.saveAs(ai, saveOpt);

var pdf = new File(base + "Huong-dan-Lam-nong-may-VI.pdf");
var po = new PDFSaveOptions();
po.preserveEditability = false;
doc.saveAs(pdf, po);

var msg = "OK pages=" + doc.artboards.length;
if (missing.length > 0) msg += " | thieu anh: " + missing.join(", ");
msg;
