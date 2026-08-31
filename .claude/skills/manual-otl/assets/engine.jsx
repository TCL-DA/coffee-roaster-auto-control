// engine.jsx — bộ dàn trang manual OTL (A4, style theo User-manual-Auto v1.0.4)
// Toạ độ: gốc trái-trên mỗi trang, y tính XUỐNG dưới (hàm X()/Y() quy đổi).

var W = 595.28, H = 841.89, GAP = 40;
var ML = 80, MR = 80, CW = W - ML - MR;      // cột chữ 435.28pt
var TOP = 96, BOT = 780;                      // vùng chữ
var FOOT_Y = 800, HEAD_Y = 44;

var F_REG = "ArialMT", F_BOLD = "Arial-BoldMT", F_ITAL = "Arial-ItalicMT",
    F_BI = "Arial-BoldItalicMT";

var doc, page = 0, y = TOP, chapterHeader = "";
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
    var lg = new File(OLDDIR + "logo-otl.png");
    if (lg.exists) {
        var pi = doc.placedItems.add(); pi.file = lg;
        var b = pi.geometricBounds, w0 = b[2] - b[0], h0 = b[1] - b[3], s = 58 / w0;
        pi.width = w0 * s; pi.height = h0 * s;
        pi.position = [X(W - MR - 58), Y(92)];
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
    var lg = new File(OLDDIR + "logo-otl.png");
    if (lg.exists) {
        var pi = doc.placedItems.add();
        pi.file = lg;
        var b = pi.geometricBounds, w0 = b[2] - b[0], h0 = b[1] - b[3];
        var s = 34 / w0;
        pi.width = w0 * s; pi.height = h0 * s;
        pi.position = [X(ML), Y(HEAD_Y - 12)];
    }
    if (chapterHeader !== "") {
        mkText(ML + 60, HEAD_Y - 4, CW - 60, chapterHeader, F_REG, 10, 13, C_BLUE, Justification.RIGHT);
    }
    var f1 = doc.textFrames.add();
    f1.contents = "Copyright (c) O Tesla Industry CO., Ltd";
    f1.textRange.characterAttributes.textFont = app.textFonts.getByName(F_REG);
    f1.textRange.characterAttributes.size = 9;
    f1.textRange.characterAttributes.fillColor = C_BLUE;
    f1.position = [X(ML), Y(FOOT_Y)];

    mkText(ML + 200, FOOT_Y - 3, CW - 200, "PH-" + (page + 1), F_REG, 9, 12, C_BLUE, Justification.RIGHT);
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

// ── khối chữ đo được chiều cao ─────────────────────────────────────────────
// tạo area text rộng w, cao tạm 2000, set chữ, đo số dòng -> chiều cao thật
function mkText(x, yTop, w, str, font, size, lead, color, just) {
    var r = doc.pathItems.rectangle(Y(yTop), X(x), w, 2000);
    r.filled = false; r.stroked = false;
    var tf = doc.textFrames.areaText(r);
    tf.contents = str;
    var ca = tf.textRange.characterAttributes;
    ca.textFont = app.textFonts.getByName(font);
    ca.size = size;
    ca.autoLeading = false;
    ca.leading = lead;
    ca.fillColor = color;
    try { tf.textRange.paragraphAttributes.justification = just; } catch (e) {}
    return tf;
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
    need(46);
    var d = 21;
    var e = doc.pathItems.ellipse(Y(y - 3), X(ML), d, d);
    e.filled = true; e.stroked = false; e.fillColor = C_BADGE;
    badgeNum("" + num, ML + d / 2, y - 3 + d / 2, 11);
    var tf = mkText(ML + 30, y, CW - 30, str, F_BOLD, 12.5, 17, C_BLACK, Justification.LEFT);
    y += Math.max(textH(tf, 17), d) + 12;
}
function H3(str) {
    need(34);
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
function SAFETY(kind, title, body) {
    var col = C_BLUE, txtOnBar = C_WHITE;
    if (kind === "nguyhiem") col = C_RED;
    else if (kind === "canhbao") { col = C_ORANGE; }
    else if (kind === "thantrong") { col = C_YELLOW; txtOnBar = C_BLACK; }

    // đo trước
    var probe = mkText(ML + 12, y + 28, CW - 24, body, F_REG, 10, 15, C_TEXT, Justification.LEFT);
    var bh = textH(probe, 15);
    var boxH = 26 + bh + 10;
    if (y + boxH > BOT) { probe.remove(); addPage(); probe = mkText(ML + 12, y + 28, CW - 24, body, F_REG, 10, 15, C_TEXT, Justification.LEFT); bh = textH(probe, 15); boxH = 26 + bh + 10; }

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
    tt.position = [X(ML + 30), Y(y + 5.5)];
    tt.zOrder(ZOrderMethod.BRINGTOFRONT);

    var ic = new File(OLDDIR + "icon-canhbao.png");
    if (ic.exists) {
        var pi = doc.placedItems.add(); pi.file = ic;
        var b = pi.geometricBounds, w0 = b[2] - b[0], h0 = b[1] - b[3], s = 15 / w0;
        pi.width = w0 * s; pi.height = h0 * s;
        pi.position = [X(ML + 9), Y(y + 3.5)];
        if (kind !== "thantrong") { /* icon đen mặc định */ }
    }
    probe.position = [X(ML + 12), Y(y + 28)];
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
    var legH = 0;
    if (legend && legend.length) legH = legend.length * 14 + 6;
    if (y + h + 30 + legH > BOT) addPage();
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
function TABLE(cols, rows, widths) {
    var pad = 6, lead = 14, size = 9.5;
    // đo chiều cao từng hàng
    function rowH(cells, font) {
        var mx = 0;
        for (var i = 0; i < cells.length; i++) {
            var t = mkText(0, -3000, widths[i] - 2 * pad, cells[i], font, size, lead, C_TEXT, Justification.LEFT);
            var h = textH(t, lead); t.remove();
            if (h > mx) mx = h;
        }
        return mx + 2 * pad;
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
        y += rh;
    }
    y += 16;
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
