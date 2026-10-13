// engine.jsx — bộ dàn trang manual OTL (A4, style theo User-manual-Auto v1.0.4)
// Toạ độ: gốc trái-trên mỗi trang, y tính XUỐNG dưới (hàm X()/Y() quy đổi).

var W = 595.28, H = 841.89, GAP = 40;
var ML = 80, MR = 80, CW = W - ML - MR;      // cột chữ 435.28pt
var TOP = 96, BOT = 780;                      // vùng chữ
var FOOT_Y = 800, HEAD_Y = 44;

var F_REG = "ArialMT", F_BOLD = "Arial-BoldMT", F_ITAL = "Arial-ItalicMT",
    F_BI = "Arial-BoldItalicMT";

var doc, page = 0, y = TOP, chapterHeader = "";
// ── thuong hieu: dat lai trong content TRUOC khi goi COVER() ───────────────
var PGPREFIX = "PH-";                      // tien to so trang o chan trang
var LOGO = "logo-otl.png";                 // tim trong IMGDIR truoc, roi OLDDIR
var LOGO_W_COVER = 58, LOGO_W_HEAD = 34;   // be ngang logo (pt) tren bia / dau trang
var FOOTLINE = "Copyright (c) O Tesla Industry CO., Ltd";
var IMGDIR = "F:/Project/112_Quanly/122_Manual_AI/preheat-vi/images/";
var OLDDIR = IMGDIR + "_tu-manual-cu/";
var missing = [];
var coverImage = "may-rang-bia.png";   // đổi trước khi gọi COVER() để thay ảnh máy
var tocList = [], tocPage = -1;

function rgb(r, g, b) { var c = new RGBColor(); c.red = r; c.green = g; c.blue = b; return c; }
var C_BLUE = rgb(46, 116, 181), C_TEXT = rgb(35, 35, 35), C_BLACK = rgb(0, 0, 0),
    C_GREY = rgb(120, 120, 120), C_LGREY = rgb(232, 232, 232), C_BADGE = rgb(74, 135, 199),
    C_WHITE = rgb(255, 255, 255), C_RED = rgb(192, 0, 0), C_ORANGE = rgb(226, 108, 10),
    C_YELLOW = rgb(255, 192, 0), C_LBLUE = rgb(234, 242, 250), C_RULE = rgb(200, 200, 200);

var COLS = 5;   // xếp trang theo lưới, tránh vượt giới hạn canvas 16384pt của Illustrator
function X(x) { return (page % COLS) * (W + GAP) + x; }
function Y(v) { return -(Math.floor(page / COLS) * (H + GAP) + v); }

function newDoc() {
    newDocBare();
    decorate();
}
function newDocBare() {
    doc = app.documents.add(DocumentColorSpace.RGB, W, H);
    doc.artboards[0].artboardRect = [X(0), Y(0), X(W), Y(H)];
    page = 0; y = TOP;
}

// ── TRANG BÌA ──────────────────────────────────────────────────────────────
function COVER(kicker, title, subtitle, machine, footline) {
    newDocBare();
    var lg = new File(IMGDIR + LOGO);
    if (!lg.exists) lg = new File(OLDDIR + LOGO);
    if (lg.exists) {
        var pi = doc.placedItems.add(); pi.file = lg;
        var b = pi.geometricBounds, w0 = b[2] - b[0], h0 = b[1] - b[3], s = LOGO_W_COVER / w0;
        pi.width = w0 * s; pi.height = h0 * s;
        pi.position = [X(W - MR - LOGO_W_COVER), Y(92)];
    }
    mkText(ML, 96, 300, kicker, F_REG, 12.5, 17, C_TEXT, Justification.LEFT);
    mkText(ML, 122, 340, title, F_BOLD, 25, 31, C_BLACK, Justification.LEFT);
    var bar = doc.pathItems.rectangle(Y(168), X(ML), 62, 3);
    bar.filled = true; bar.fillColor = C_BLUE; bar.stroked = false;
    mkText(ML, 186, 380, subtitle, F_BOLD, 15, 21, C_BLUE, Justification.LEFT);
    mkText(ML, 232, 380, machine, F_REG, 11.5, 17, C_GREY, Justification.LEFT);

    var mf = new File(OLDDIR + coverImage);
    if (mf.exists) {
        var p2 = doc.placedItems.add(); p2.file = mf;
        var b2 = p2.geometricBounds, w2 = b2[2] - b2[0], h2 = b2[1] - b2[3];
        var s2 = 420 / h2; if (w2 * s2 > 330) s2 = 330 / w2;
        p2.width = w2 * s2; p2.height = h2 * s2;
        p2.position = [X((W - w2 * s2) / 2 + 30), Y(300)];
    }
    var ln = doc.pathItems.rectangle(Y(772), X(ML), CW, 0.8);
    ln.filled = true; ln.fillColor = C_RULE; ln.stroked = false;
    mkText(ML, 782, CW, footline, F_REG, 9.5, 13, C_BLUE, Justification.LEFT);
}
function addPage() {
    page++;
    doc.artboards.add([X(0), Y(0), X(W), Y(H)]);
    y = TOP;
    decorate();
}
function need(h) { if (y + h > BOT) addPage(); }

// ── nền mỗi trang: logo + header + footer ──────────────────────────────────
function decorate() {
    var lg = new File(IMGDIR + LOGO);
    if (!lg.exists) lg = new File(OLDDIR + LOGO);
    if (lg.exists) {
        var pi = doc.placedItems.add();
        pi.file = lg;
        var b = pi.geometricBounds, w0 = b[2] - b[0], h0 = b[1] - b[3];
        var s = LOGO_W_HEAD / w0;
        pi.width = w0 * s; pi.height = h0 * s;
        pi.position = [X(ML), Y(HEAD_Y - 12)];
    }
    if (chapterHeader !== "") {
        mkText(ML + 60, HEAD_Y - 4, CW - 60, chapterHeader, F_REG, 10, 13, C_BLUE, Justification.RIGHT);
    }
    var f1 = doc.textFrames.add();
    f1.contents = FOOTLINE;
    f1.textRange.characterAttributes.textFont = app.textFonts.getByName(F_REG);
    f1.textRange.characterAttributes.size = 9;
    f1.textRange.characterAttributes.fillColor = C_BLUE;
    f1.position = [X(ML), Y(FOOT_Y)];

    // số trang cũng là point text cùng cỡ, canh phải theo bề ngang đo được:
    // cùng đường chân chữ với dòng bản quyền (area text cũ lệch lên ~4 pt)
    var f2 = doc.textFrames.add();
    f2.contents = PGPREFIX + (page + 1);
    f2.textRange.characterAttributes.textFont = app.textFonts.getByName(F_REG);
    f2.textRange.characterAttributes.size = 9;
    f2.textRange.characterAttributes.fillColor = C_BLUE;
    var b2 = f2.geometricBounds;
    f2.position = [X(ML + CW) - (b2[2] - b2[0]), Y(FOOT_Y)];
}


// ── TRANG THÔNG TIN CÔNG TY ────────────────────────────────────────────────
function COMPANY(name, tagline, rows, noticeTitle, noticeBody) {
    y += 26;   // logo đã có sẵn ở header, không lặp lại
    var t1 = mkText(ML, y, CW, name, F_BOLD, 17, 22, C_BLACK, Justification.LEFT);
    y += textH(t1, 22) + 4;
    var t2 = mkText(ML, y, CW, tagline, F_REG, 11, 16, C_GREY, Justification.LEFT);
    y += textH(t2, 16) + 18;
    var ln = doc.pathItems.rectangle(Y(y), X(ML), CW, 0.8);
    ln.filled = true; ln.fillColor = C_RULE; ln.stroked = false;
    y += 18;

    for (var i = 0; i < rows.length; i++) {
        var lab = mkText(ML, y, 120, rows[i][0], F_BOLD, 10.5, 15, C_TEXT, Justification.LEFT);
        var val = mkText(ML + 124, y, CW - 124, rows[i][1], F_REG, 10.5, 15, C_TEXT, Justification.LEFT);
        y += Math.max(textH(lab, 15), textH(val, 15)) + 8;
    }
    y += 12;
    if (noticeTitle) SAFETY("luuy", noticeTitle, noticeBody);
}

// ── MỤC LỤC: giữ chỗ trước, vẽ sau khi biết số trang ───────────────────────
function TOCRESERVE() { addPage(); tocPage = page; }

function TOCDRAW(title, prefix) {
    if (tocPage < 0) return;
    var savePage = page, saveY = y;
    page = tocPage; y = TOP;
    var h = mkText(ML, y, CW, title, F_BOLD, 19, 24, C_BLACK, Justification.CENTER);
    y += textH(h, 24) + 26;
    for (var i = 0; i < tocList.length; i++) {
        var name = tocList[i][0], pg = tocList[i][1];
        var pt = doc.textFrames.add();          // point text để đo bề ngang
        pt.contents = name;
        pt.textRange.characterAttributes.textFont = app.textFonts.getByName(F_REG);
        pt.textRange.characterAttributes.size = 11;
        pt.textRange.characterAttributes.fillColor = C_TEXT;
        pt.position = [X(ML), Y(y)];
        var wb = pt.geometricBounds, wname = wb[2] - wb[0];
        mkText(ML + CW - 60, y, 60, prefix + (pg + 1), F_REG, 11, 15, C_TEXT, Justification.RIGHT);
        var x1 = ML + wname + 8, x2 = ML + CW - 66;
        if (x2 > x1) {
            var dots = doc.pathItems.rectangle(Y(y + 9.5), X(x1), x2 - x1, 0.7);
            dots.filled = true; dots.fillColor = rgb(180, 180, 180); dots.stroked = false;
        }
        y += 22;
    }
    page = savePage; y = saveY;
}

// ── xuống dòng thông minh (chủ máy yêu cầu 07/10/2026) ─────────────────────
// Dựng chữ xong thì ĐỌC LẠI từng dòng Illustrator đã ngắt; gặp chỗ ngắt xấu thì thay dấu cách
// đứng trước chữ cuối của dòng trên bằng xuống dòng mềm (ký tự 3), để chữ đó xuống dòng cùng
// chữ đi kèm. Lặp tối đa 6 lần cho tới khi hết chỗ xấu. Bốn loại chỗ xấu:
//   1. chữ mồ côi: dòng cuối đoạn chỉ có một chữ ngắn ("3.", "hành.")
//   2. số tách khỏi đơn vị: "90" | "°C", "4–6" | "mẻ", "8" | "tháng"
//   3. tiền tố tách khỏi số: "Hình" | "4.1", "mục" | "2.1", "chương" | "3", "Phụ lục" | "A"
//   4. dòng mới bắt đầu bằng dấu gạch "–"
// KHÔNG dùng U+00A0 hay thuộc tính noBreak: đo 07/10/2026, Illustrator vẫn ngắt ở U+00A0,
// còn noBreak thì giữ được nhưng để chữ TRÀN RA NGOÀI LỀ PHẢI thay vì đẩy xuống dòng.
// Chỉ áp cho khung rộng > 150 pt (đoạn văn, chú thích, hộp cảnh báo); ô bảng hẹp để nguyên.
var SMARTBREAK = true;
var XUONG_DONG_MEM = String.fromCharCode(3);
var GACH_NOI = String.fromCharCode(0x2013);
var DONVI = {"mm": 1, "cm": 1, "m": 1, "kg": 1, "g": 1, "%": 1, "phút": 1, "giây": 1, "giờ": 1,
             "ngày": 1, "tuần": 1, "tháng": 1, "năm": 1, "mẻ": 1, "bar": 1, "kW": 1, "W": 1,
             "V": 1, "Hz": 1, "lít": 1, "MB": 1, "lần": 1, "độ": 1,
             // bản tiếng Anh
             "min": 1, "h": 1, "s": 1, "hours": 1, "days": 1, "weeks": 1, "months": 1, "years": 1,
             "batches": 1, "Pa": 1, "kPa": 1, "mbar": 1, "rpm": 1, "degrees": 1};
DONVI[String.fromCharCode(0xB0) + "C"] = 1;
var TIENTO = {"Hình": 1, "hình": 1, "Mục": 1, "mục": 1, "Chương": 1, "chương": 1, "lục": 1,
              "Bước": 1, "bước": 1, "số": 1, "Số": 1, "Tuần": 1, "tuần": 1,
              "Figure": 1, "figure": 1, "Figures": 1, "figures": 1, "Section": 1, "section": 1,
              "Chapter": 1, "chapter": 1, "Appendix": 1, "Step": 1, "step": 1, "steps": 1, "Week": 1};

function catHaiDau(s) { return s.replace(/^\s+|\s+$/g, ""); }
function tuDau(s) { var m = catHaiDau(s).match(/^\S+/); return m ? m[0] : ""; }
function tuCuoi(s) { var m = catHaiDau(s).match(/\S+$/); return m ? m[0] : ""; }
function boDauCau(s) { return s.replace(/^[(*]+|[.,;:)*]+$/g, ""); }

function laNgatXau(dongA, dongB, bLaCuoiDoan) {
    var cuoiA = boDauCau(tuCuoi(dongA)), dauB = tuDau(dongB), sachB = catHaiDau(dongB);
    if (cuoiA === "" || dauB === "") return false;
    if (bLaCuoiDoan && sachB.indexOf(" ") < 0 && sachB.length <= 10) return true;      // 1
    if (/\d$/.test(cuoiA) && DONVI[boDauCau(dauB)]) return true;                      // 2
    if (TIENTO[cuoiA] && /^[\dA-D]/.test(dauB)) return true;                          // 3
    if (dauB === GACH_NOI || dauB === "-") return true;                               // 4
    return false;
}

function sapDong(tf, w) {
    if (!SMARTBREAK || w <= 150) return;
    for (var lan = 0; lan < 6; lan++) {
        var L = tf.lines, n = L.length, sua = false;
        if (n < 2) return;
        var story = tf.contents;
        for (var i = 0; i < n - 1 && !sua; i++) {
            var a = L[i].contents, b = L[i + 1].contents;
            var bDau = L[i + 1].characterOffset - 1, bHet = bDau + b.length;
            var kyTuSau = story.charAt(bHet);
            var bLaCuoiDoan = bHet >= story.length || kyTuSau === "\r" || kyTuSau === "\n";
            if (!laNgatXau(a, b, bLaCuoiDoan)) continue;
            var aGon = a.replace(/\s+$/, ""), k = aGon.lastIndexOf(" ");
            if (k <= 0) continue;                     // dòng trên chỉ có một chữ: để nguyên
            try {
                tf.characters[L[i].characterOffset - 1 + k].contents = XUONG_DONG_MEM;
                sua = true;
            } catch (e) {}
        }
        if (!sua) return;
    }
}

// ── chữ đậm trong đoạn: viết **chữ cần nhấn** trong content ───────────────
// Trả về [chuỗi đã bỏ dấu **, danh sách [vị trí đầu, vị trí cuối)].
function boDam(str) {
    var out = "", vung = [], i = 0, mo = -1;
    while (i < str.length) {
        if (str.charAt(i) === "*" && str.charAt(i + 1) === "*") {
            if (mo < 0) mo = out.length; else { vung.push([mo, out.length]); mo = -1; }
            i += 2;
        } else { out += str.charAt(i); i++; }
    }
    return [out, vung];
}
function fontDam(font) {
    if (font === F_ITAL) return F_BI;
    if (font === F_REG) return F_BOLD;
    return font;
}

// ── khối chữ đo được chiều cao ─────────────────────────────────────────────
// tạo area text rộng w, cao tạm 2000, set chữ, đo số dòng -> chiều cao thật
function mkText(x, yTop, w, str, font, size, lead, color, just) {
    var r = doc.pathItems.rectangle(Y(yTop), X(x), w, 2000);
    r.filled = false; r.stroked = false;
    var tf = doc.textFrames.areaText(r);
    var tach = boDam(str);
    tf.contents = tach[0];
    var ca = tf.textRange.characterAttributes;
    ca.textFont = app.textFonts.getByName(font);
    ca.size = size;
    ca.autoLeading = false;
    ca.leading = lead;
    ca.fillColor = color;
    try { tf.textRange.paragraphAttributes.justification = just; } catch (e) {}
    // tắt gạch nối tự động: bản tiếng Anh bị Illustrator chẻ từ ("sched-ule") và làm sapDong ngắt hai lần
    try { tf.textRange.paragraphAttributes.hyphenation = false; } catch (e) {}
    if (tach[1].length) {
        var fd = app.textFonts.getByName(fontDam(font));
        for (var v = 0; v < tach[1].length; v++)
            datKhoang(tf, tach[1][v][0], tach[1][v][1], function (rg) { rg.characterAttributes.textFont = fd; });
    }
    sapDong(tf, w);          // sau khi đã đặt font/cỡ/đậm: ngắt dòng mới đúng như khi in
    return tf;
}
// áp một thao tác lên đoạn ký tự [dau, cuoi) của khung chữ; thử gán cả đoạn trước, lỗi thì làm từng ký tự
function datKhoang(tf, dau, cuoi, lam) {
    try {
        var r = tf.characters[dau];
        r.length = cuoi - dau;
        lam(r);
    } catch (e) {
        for (var c = dau; c < cuoi; c++) try { lam(tf.characters[c]); } catch (e2) {}
    }
}

// ── tiêu đề nhỏ có nhãn màu phía trước (ví dụ nhãn "V1" / "V2") ────────────
// H3TAG("V2", "Thùng trấu có chốt gài đỏ")  — nhãn xanh đậm, chữ trắng
function H3TAG(tag, str, mau) {
    need(150);
    var c = mau || C_BLUE;
    var t = doc.textFrames.add();
    t.contents = tag;
    t.textRange.characterAttributes.textFont = app.textFonts.getByName(F_BOLD);
    t.textRange.characterAttributes.size = 9.5;
    t.textRange.characterAttributes.fillColor = C_WHITE;
    var b = t.geometricBounds, tw = b[2] - b[0];
    var pw = tw + 12, ph = 16;
    var pill = doc.pathItems.roundedRectangle(Y(y), X(ML), pw, ph, 4, 4);
    pill.filled = true; pill.fillColor = c; pill.stroked = false;
    t.position = [X(ML + 6), Y(y + 2.5)];
    t.zOrder(ZOrderMethod.BRINGTOFRONT);
    var tf = mkText(ML + pw + 8, y, CW - pw - 8, str, F_BOLD, 11.5, 17, C_BLACK, Justification.LEFT);
    y += Math.max(textH(tf, 17), ph) + 7;
}

// ── hai ảnh cạnh nhau, mỗi ảnh chiếm nửa cột chữ, chú thích dưới từng ảnh ──
function IMG2(fa, fb, hMax, capA, capB) {
    var half = (CW - 16) / 2, names = [fa, fb], caps = [capA, capB], items = [], rowH = hMax;
    // hai ảnh CÙNG chiều cao (mép trên và mép dưới thẳng hàng): lấy chiều cao nhỏ nhất
    // mà cả hai ảnh vẫn lọt nửa cột, rồi co cả hai về đúng chiều cao đó
    for (var i = 0; i < 2; i++) {
        var f = new File(IMGDIR + names[i]);
        if (!f.exists) f = new File(OLDDIR + names[i]);
        if (!f.exists) { missing.push(names[i]); items.push(null); continue; }
        var pi = doc.placedItems.add(); pi.file = f;
        var b = pi.geometricBounds, w0 = b[2] - b[0], h0 = b[1] - b[3];
        items.push([pi, w0, h0]);
        rowH = Math.min(rowH, half * h0 / w0);
    }
    for (var q = 0; q < 2; q++) {
        if (!items[q]) continue;
        var sq = rowH / items[q][2];
        items[q][0].width = items[q][1] * sq; items[q][0].height = rowH;
        items[q] = items[q][0];
    }
    var capH = 0;
    for (var k = 0; k < 2; k++) {
        var t = mkText(0, -3000, half, caps[k], F_ITAL, 9.5, 14, C_GREY, Justification.CENTER);
        capH = Math.max(capH, textH(t, 14)); t.remove();
    }
    need(rowH + capH + 16);
    for (var j = 0; j < 2; j++) {
        var x0 = ML + j * (half + 16);
        if (items[j]) {
            var bb = items[j].geometricBounds, w = bb[2] - bb[0], h = bb[1] - bb[3];
            items[j].position = [X(x0 + (half - w) / 2), Y(y + (rowH - h))];
        }
        mkText(x0, y + rowH + 6, half, caps[j], F_ITAL, 9.5, 14, C_GREY, Justification.CENTER);
    }
    y += rowH + 6 + capH + 12;
}
function textH(tf, lead) { return tf.lines.length * lead; }
function moveTo(tf, x, yTop) {
    tf.position = [X(x), Y(yTop)];
}
// đặt khối chữ theo dòng chảy, tự sang trang nếu tràn
function flow(x, w, str, font, size, lead, color, just, gapAfter) {
    var tf = mkText(x, y, w, str, font, size, lead, color, just);
    var h = textH(tf, lead);
    if (y + h > BOT) {
        var oldPage = page;
        addPage();
        tf.translate((page - oldPage) * (W + GAP), (y - (y)) );
        tf.position = [X(x), Y(y)];
    }
    y += h + gapAfter;
    return tf;
}

// chữ trắng căn đúng tâm hình tròn (cx, cy tính theo hệ toạ độ trang)
function badgeNum(str, cx, cy, size) {
    var t = doc.textFrames.add();
    t.contents = str;
    t.textRange.characterAttributes.textFont = app.textFonts.getByName(F_BOLD);
    t.textRange.characterAttributes.size = size;
    t.textRange.characterAttributes.fillColor = C_WHITE;
    var b = t.geometricBounds;                 // [left, top, right, bottom]
    var w = b[2] - b[0], h = b[1] - b[3];
    t.position = [X(cx) - w / 2, Y(cy) + h / 2];
    return t;
}

// ── các loại khối ──────────────────────────────────────────────────────────
function H1(str) {
    need(60);
    tocList.push([str, page]);
    var tf = mkText(ML, y, CW, str, F_BOLD, 19, 24, C_BLACK, Justification.CENTER);
    y += textH(tf, 24) + 22;
}
function H2(num, str) {
    need(200);   // tieu de + ~5 dong: muc ngan khong bi xe doi qua 2 trang
    var d = 21;
    var e = doc.pathItems.ellipse(Y(y - 3), X(ML), d, d);
    e.filled = true; e.stroked = false; e.fillColor = C_BADGE;
    badgeNum("" + num, ML + d / 2, y - 3 + d / 2, 11);
    var tf = mkText(ML + 30, y, CW - 30, str, F_BOLD, 12.5, 17, C_BLACK, Justification.LEFT);
    y += Math.max(textH(tf, 17), d) + 12;
}
function H3(str) {
    need(150);   // nhu H2
    flow(ML, CW, str, F_BOLD, 11.5, 17, C_BLACK, Justification.LEFT, 7);
}
function P(str) { flow(ML, CW, str, F_REG, 11, 18, C_TEXT, Justification.FULLJUSTIFYLASTLINELEFT, 7); }
function PI(str) { flow(ML, CW, str, F_ITAL, 10, 16, C_GREY, Justification.LEFT, 8); }
function BUL(arr) {
    for (var i = 0; i < arr.length; i++)
        flow(ML + 20, CW - 20, "\u2022 " + arr[i], F_REG, 11, 18, C_TEXT, Justification.LEFT, 4);
    y += 6;
}
function STEP(n, str) {
    need(30);
    var num = mkText(ML, y, 24, n + ".", F_BOLD, 11, 18, C_BLACK, Justification.LEFT);
    var tf = mkText(ML + 24, y, CW - 24, str, F_REG, 11, 18, C_TEXT, Justification.LEFT);
    var h = textH(tf, 18);
    if (y + h > BOT) {
        var o = page; addPage();
        num.position = [X(ML), Y(y)];
        tf.position = [X(ML + 24), Y(y)];
    }
    y += h + 7;
}
function RULE() {
    need(20);
    var l = doc.pathItems.rectangle(Y(y + 6), X(ML), CW, 0.8);
    l.filled = true; l.stroked = false; l.fillColor = C_RULE;
    y += 20;
}
function GAPV(h) { y += h; }

// ── hộp an toàn kiểu ISO 3864 ──────────────────────────────────────────────
// kind: "nguyhiem" | "canhbao" | "thantrong" | "luuy"
// "luuy" (NOTICE) KHÔNG có tam giác cảnh báo: theo ISO 3864-2 / ANSI Z535.6, ký hiệu tam giác
// chỉ dùng cho nguy cơ gây thương tích; LƯU Ý là hỏng máy hoặc thông tin.
// icons (tuỳ chọn): mảng tên file biển ISO 7010 trong IMGDIR (vd ["iso-w017.png"]) — đặt dọc
// bên trái thân hộp, chữ lùi vào nhường chỗ.
var ICON_W = 34;
function SAFETY(kind, title, body, icons) {
    var col = C_BLUE, txtOnBar = C_WHITE;
    if (kind === "nguyhiem") col = C_RED;
    else if (kind === "canhbao") { col = C_ORANGE; }
    else if (kind === "thantrong") { col = C_YELLOW; txtOnBar = C_BLACK; }
    icons = icons || [];
    var tx = icons.length ? ML + 12 + ICON_W + 12 : ML + 12;
    var tw = ML + CW - 12 - tx;
    var iconsH = icons.length ? icons.length * (ICON_W * 0.88 + 6) : 0;

    // đo trước
    var probe = mkText(tx, y + 28, tw, body, F_REG, 10, 15, C_TEXT, Justification.LEFT);
    var bh = Math.max(textH(probe, 15), iconsH);
    var boxH = 26 + bh + 10;
    if (y + boxH > BOT) { probe.remove(); addPage(); probe = mkText(tx, y + 28, tw, body, F_REG, 10, 15, C_TEXT, Justification.LEFT); bh = Math.max(textH(probe, 15), iconsH); boxH = 26 + bh + 10; }

    var bg = doc.pathItems.rectangle(Y(y), X(ML), CW, boxH);
    bg.filled = true; bg.fillColor = rgb(250, 250, 250);
    bg.stroked = true; bg.strokeColor = col; bg.strokeWidth = 1;
    var bar = doc.pathItems.rectangle(Y(y), X(ML), CW, 22);
    bar.filled = true; bar.fillColor = col; bar.stroked = false;

    var tt = doc.textFrames.add();
    tt.contents = title;
    tt.textRange.characterAttributes.textFont = app.textFonts.getByName(F_BOLD);
    tt.textRange.characterAttributes.size = 11;
    tt.textRange.characterAttributes.fillColor = txtOnBar;
    tt.position = [X(ML + (kind === "luuy" ? 10 : 30)), Y(y + 5.5)];
    tt.zOrder(ZOrderMethod.BRINGTOFRONT);

    var ic = new File(OLDDIR + "icon-canhbao.png");
    if (kind !== "luuy" && ic.exists) {
        var pi = doc.placedItems.add(); pi.file = ic;
        var b = pi.geometricBounds, w0 = b[2] - b[0], h0 = b[1] - b[3], s = 15 / w0;
        pi.width = w0 * s; pi.height = h0 * s;
        pi.position = [X(ML + 9), Y(y + 3.5)];
    }
    for (var k = 0; k < icons.length; k++) {
        var fi = new File(IMGDIR + icons[k]);
        if (!fi.exists) { missing.push(icons[k]); continue; }
        var pk = doc.placedItems.add(); pk.file = fi;
        var bk = pk.geometricBounds, wk = bk[2] - bk[0], hk = bk[1] - bk[3], sk = ICON_W / wk;
        pk.width = wk * sk; pk.height = hk * sk;
        pk.position = [X(ML + 12), Y(y + 30 + k * (ICON_W * 0.88 + 6))];
    }
    probe.position = [X(tx), Y(y + 28)];
    probe.zOrder(ZOrderMethod.BRINGTOFRONT);
    y += boxH + 12;
}

// ── ảnh: có file thật thì đặt, không thì vẽ ô trống ────────────────────────
function IMG(fname, maxW, caption) {
    var f = new File(IMGDIR + fname);
    if (!f.exists) f = new File(OLDDIR + fname);
    var capH = caption ? 26 : 8;
    if (f.exists) {
        var pi = doc.placedItems.add(); pi.file = f;
        var b = pi.geometricBounds, w0 = b[2] - b[0], h0 = b[1] - b[3];
        var s = maxW / w0; if (h0 * s > 330) s = 330 / h0;
        var w = w0 * s, h = h0 * s;
        if (y + h + capH > BOT) { addPage(); }
        pi.width = w; pi.height = h;
        pi.position = [X(ML + (CW - w) / 2), Y(y)];
        y += h + 6;
    } else {
        missing.push(fname);
        var h2 = Math.round(maxW * 0.42);
        if (y + h2 + capH > BOT) addPage();
        var r = doc.pathItems.rectangle(Y(y), X(ML + (CW - maxW) / 2), maxW, h2);
        r.filled = true; r.fillColor = rgb(245, 246, 248);
        r.stroked = true; r.strokeColor = rgb(170, 180, 195); r.strokeWidth = 0.8;
        r.strokeDashes = [4, 3];
        var note = mkText(ML + (CW - maxW) / 2 + 10, y + h2 / 2 - 16, maxW - 20,
            "\u1EA2NH S\u1EBC CH\u00c8N\n" + fname, F_BOLD, 9.5, 14, rgb(130, 145, 165), Justification.CENTER);
        y += h2 + 6;
    }
    if (caption) {
        flow(ML, CW, caption, F_ITAL, 9.5, 14, C_GREY, Justification.CENTER, 10);
    } else y += 8;
}


// ── ảnh có khung chú thích đánh số (kiểu manual kỹ thuật Đức) ──────────────
// marks: [[xf, yf, wf, hf, "nhãn"], ...] toạ độ theo TỈ LỆ ảnh (0..1)
function IMGC(fname, maxW, caption, marks, legend) {
    var f = new File(IMGDIR + fname);
    if (!f.exists) f = new File(OLDDIR + fname);
    if (!f.exists) { missing.push(fname); IMG(fname, maxW, caption); return; }

    var pi = doc.placedItems.add(); pi.file = f;
    var b = pi.geometricBounds, w0 = b[2] - b[0], h0 = b[1] - b[3];
    var s = maxW / w0; if (h0 * s > 340) s = 340 / h0;
    var w = w0 * s, h = h0 * s;
    // đo THẬT chiều cao chú thích + từng dòng giải thích (bản tiếng Anh hay dài 2 dòng):
    // ước theo số mục thì dòng cuối rơi sang trang sau, tách khỏi hình
    var legH = 0, capH = 8;
    for (var g = 0; legend && g < legend.length; g++) {
        var tg = mkText(0, -3000, CW - 24, legend[g], F_REG, 10, 14, C_TEXT, Justification.LEFT);
        legH += textH(tg, 14) + 2; tg.remove();
    }
    if (legend && legend.length) legH += 10;
    if (caption) {
        var tc = mkText(0, -3000, CW, caption, F_ITAL, 9.5, 14, C_GREY, Justification.CENTER);
        capH = textH(tc, 14) + 8; tc.remove();
    }
    if (y + h + 6 + capH + legH > BOT) addPage();
    pi.width = w; pi.height = h;
    var x0 = ML + (CW - w) / 2;
    pi.position = [X(x0), Y(y)];

    for (var i = 0; marks && i < marks.length; i++) {
        var m = marks[i];
        var rx = x0 + m[0] * w, ry = y + m[1] * h, rw = m[2] * w, rh = m[3] * h;
        var r = doc.pathItems.roundedRectangle(Y(ry), X(rx), rw, rh, 3, 3);
        r.filled = false; r.stroked = true; r.strokeColor = C_RED; r.strokeWidth = 1.2;
        var d = 15;
        var e = doc.pathItems.ellipse(Y(ry - d / 2), X(rx - d / 2), d, d);
        e.filled = true; e.fillColor = C_RED; e.stroked = true;
        e.strokeColor = C_WHITE; e.strokeWidth = 1;
        badgeNum(m[4], rx, ry, 8.5);
    }
    y += h + 6;
    if (caption) flow(ML, CW, caption, F_ITAL, 9.5, 14, C_GREY, Justification.CENTER, 8);
    for (var k = 0; legend && k < legend.length; k++)
        flow(ML + 24, CW - 24, legend[k], F_REG, 10, 14, C_TEXT, Justification.LEFT, 2);
    if (legend && legend.length) y += 10;
}

// ── ảnh nhỏ nằm cùng dòng chữ (kiểu manual cũ) ────────────────────────────
function STEPIMG(n, before, fname, after, iconW) {
    var f = new File(IMGDIR + fname); if (!f.exists) f = new File(OLDDIR + fname);
    need(46);
    var yy = y;
    var num = mkText(ML, yy, 24, n + ".", F_BOLD, 11, 18, C_BLACK, Justification.LEFT);
    var t1 = mkText(ML + 24, yy, CW - 24, before, F_REG, 11, 18, C_TEXT, Justification.LEFT);
    var h1 = textH(t1, 18);
    var lastLineW = 0;
    // đặt icon sau khối chữ, xuống dòng mới cho gọn
    y += h1 + 4;
    if (f.exists) {
        var pi = doc.placedItems.add(); pi.file = f;
        var b = pi.geometricBounds, w0 = b[2] - b[0], h0 = b[1] - b[3], s = iconW / w0;
        pi.width = w0 * s; pi.height = h0 * s;
        if (y + h0 * s > BOT) addPage();
        pi.position = [X(ML + 24), Y(y)];
        y += h0 * s + 6;
    } else {
        missing.push(fname);
        var r = doc.pathItems.rectangle(Y(y), X(ML + 24), iconW, iconW * 0.75);
        r.filled = true; r.fillColor = rgb(245, 246, 248);
        r.stroked = true; r.strokeColor = rgb(170, 180, 195); r.strokeWidth = 0.8; r.strokeDashes = [4, 3];
        mkText(ML + 26, y + iconW * 0.30, iconW - 4, fname, F_BOLD, 7, 9, rgb(130, 145, 165), Justification.CENTER);
        y += iconW * 0.75 + 6;
    }
    if (after && after !== "") {
        flow(ML + 24, CW - 24, after, F_REG, 11, 18, C_TEXT, Justification.LEFT, 7);
    }
}

// ── bảng ───────────────────────────────────────────────────────────────────
// opts (tuỳ chọn): { grid: true } kẻ khung đủ ô (phiếu in ra để ký tay),
//                  { minRow: 30 } chiều cao tối thiểu mỗi hàng (pt)
//                  { size: 9, lead: 13 } chữ nhỏ hơn cho bảng dài cần gọn một trang (bản tiếng Anh dài hơn)
function TABLE(cols, rows, widths, opts) {
    opts = opts || {};
    var pad = 6, lead = opts.lead || 14, size = opts.size || 9.5;
    // đo chiều cao từng hàng
    function rowH(cells, font) {
        var mx = 0;
        for (var i = 0; i < cells.length; i++) {
            var t = mkText(0, -3000, widths[i] - 2 * pad, cells[i], font, size, lead, C_TEXT, Justification.LEFT);
            var h = textH(t, lead); t.remove();
            if (h > mx) mx = h;
        }
        return Math.max(mx + 2 * pad, font === F_REG && opts.minRow ? opts.minRow : 0);
    }
    function keDoc(yTop, h) {          // vạch dọc + hai mép ngoài cho một hàng
        if (!opts.grid) return;
        var xv = ML;
        for (var c = 0; c <= widths.length; c++) {
            var v = doc.pathItems.rectangle(Y(yTop), X(xv - 0.25), 0.5, h);
            v.filled = true; v.fillColor = C_RULE; v.stroked = false;
            if (c < widths.length) xv += widths[c];
        }
    }
    var hH = rowH(cols, F_BOLD);
    need(hH + 40);
    // header
    var x0 = ML;
    var hbg = doc.pathItems.rectangle(Y(y), X(ML), CW, hH);
    hbg.filled = true; hbg.fillColor = C_BLUE; hbg.stroked = false;
    for (var c = 0; c < cols.length; c++) {
        mkText(x0 + pad, y + pad - 2, widths[c] - 2 * pad, cols[c], F_BOLD, size, lead, C_WHITE, Justification.LEFT);
        x0 += widths[c];
    }
    keDoc(y, hH);
    y += hH;
    for (var r2 = 0; r2 < rows.length; r2++) {
        var rh = rowH(rows[r2], F_REG);
        if (y + rh > BOT) {
            addPage();
            var x1 = ML;
            var hbg2 = doc.pathItems.rectangle(Y(y), X(ML), CW, hH);
            hbg2.filled = true; hbg2.fillColor = C_BLUE; hbg2.stroked = false;
            for (var c2 = 0; c2 < cols.length; c2++) {
                mkText(x1 + pad, y + pad - 2, widths[c2] - 2 * pad, cols[c2], F_BOLD, size, lead, C_WHITE, Justification.LEFT);
                x1 += widths[c2];
            }
            keDoc(y, hH);
            y += hH;
        }
        if (r2 % 2 === 1) {
            var zbg = doc.pathItems.rectangle(Y(y), X(ML), CW, rh);
            zbg.filled = true; zbg.fillColor = rgb(244, 247, 251); zbg.stroked = false;
        }
        var xx = ML;
        for (var c3 = 0; c3 < rows[r2].length; c3++) {
            mkText(xx + pad, y + pad - 2, widths[c3] - 2 * pad, rows[r2][c3], F_REG, size, lead, C_TEXT, Justification.LEFT);
            xx += widths[c3];
        }
        var ln = doc.pathItems.rectangle(Y(y + rh), X(ML), CW, 0.5);
        ln.filled = true; ln.fillColor = C_RULE; ln.stroked = false;
        keDoc(y, rh);
        y += rh;
    }
    y += 16;
}

// ── hàng biển cảnh báo có chú thích bên dưới (giải thích ký hiệu ở chương 1) ──
// ICONROW([["iso-w012.png", "Điện giật"], ...])
function ICONROW(list) {
    var n = list.length, cell = CW / n, iw = 46, capH = 0;
    for (var m = 0; m < n; m++) {
        var t = mkText(0, -3000, cell - 8, list[m][1], F_REG, 9.5, 13, C_TEXT, Justification.CENTER);
        capH = Math.max(capH, textH(t, 13)); t.remove();
    }
    need(iw + capH + 20);
    for (var i = 0; i < n; i++) {
        var x0 = ML + i * cell;
        var f = new File(IMGDIR + list[i][0]);
        if (f.exists) {
            var pi = doc.placedItems.add(); pi.file = f;
            var b = pi.geometricBounds, w0 = b[2] - b[0], h0 = b[1] - b[3], s = iw / w0;
            pi.width = w0 * s; pi.height = h0 * s;
            pi.position = [X(x0 + (cell - iw) / 2), Y(y)];
        } else missing.push(list[i][0]);
        mkText(x0 + 4, y + iw * 0.88 + 6, cell - 8, list[i][1], F_REG, 9.5, 13, C_TEXT, Justification.CENTER);
    }
    y += iw * 0.88 + 6 + capH + 14;
}

// ── sơ đồ trạng thái (vector, không cần ảnh) ───────────────────────────────
function STATEFLOW(items) {
    var bw = CW, gapv = 14;
    // đo trước chiều cao từng hộp
    var hs = [], total = 0;
    for (var m = 0; m < items.length; m++) {
        var pr = mkText(0, -4000, bw - 210, items[m][1], F_REG, 9.5, 12, C_GREY, Justification.LEFT);
        var hh = Math.max(38, 22 + textH(pr, 12)); pr.remove();
        hs.push(hh); total += hh + gapv;
    }
    if (y + total > BOT) addPage();
    for (var i = 0; i < items.length; i++) {
        var it = items[i], bh = hs[i];
        var box = doc.pathItems.roundedRectangle(Y(y), X(ML + 26), bw - 52, bh, 6, 6);
        box.filled = true; box.fillColor = (i === 0 || i === items.length - 1) ? rgb(238, 243, 249) : C_WHITE;
        box.stroked = true; box.strokeColor = C_BADGE; box.strokeWidth = 1;

        var n = doc.pathItems.ellipse(Y(y + 9), X(ML + 34), 22, 22);
        n.filled = true; n.fillColor = C_BADGE; n.stroked = false;
        badgeNum("" + (i + 1), ML + 45, y + 20, 11);

        mkText(ML + 66, y + 6, 200, it[0], F_BOLD, 10.5, 13, C_BLACK, Justification.LEFT);
        mkText(ML + 66, y + 20, bw - 210, it[1], F_REG, 9.5, 12, C_GREY, Justification.LEFT);
        mkText(ML + bw - 140, y + 12, 88, it[2], F_BOLD, 9.5, 12, C_BLUE, Justification.RIGHT);

        if (i < items.length - 1) {
            var ar = doc.pathItems.rectangle(Y(y + bh), X(ML + 26 + (bw - 52) / 2 - 0.75), 1.5, gapv);
            ar.filled = true; ar.fillColor = C_BADGE; ar.stroked = false;
            var tip = doc.pathItems.add();
            tip.setEntirePath([[X(ML + 26 + (bw - 52) / 2 - 4), Y(y + bh + gapv - 5)],
                               [X(ML + 26 + (bw - 52) / 2 + 4), Y(y + bh + gapv - 5)],
                               [X(ML + 26 + (bw - 52) / 2), Y(y + bh + gapv)]]);
            tip.closed = true; tip.filled = true; tip.fillColor = C_BADGE; tip.stroked = false;
        }
        y += bh + gapv;
    }
    y += 6;
}
