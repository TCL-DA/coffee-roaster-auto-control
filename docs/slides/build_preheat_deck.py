# -*- coding: utf-8 -*-
"""
Dựng bộ slide giới thiệu tính năng PREHEAT (làm nóng máy rang tự động) — OTL-06ALS.
Tone đỏ/đen, chuyển cảnh Morph (kiểu Keynote Magic Move / iPhone motion).

Chạy:  python build_preheat_deck.py
Ra:    OTL-Preheat-Gioi-thieu.pptx  (cùng thư mục)
"""

import os

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml.ns import nsdecls, qn
from pptx.util import Emu, Inches, Pt

# ─────────────────────────────────────────────────────────────────────────────
# HỆ MÀU + CHỮ  (design token — đổi ở đây là đổi cả bộ)
# ─────────────────────────────────────────────────────────────────────────────
# 4 TÔNG DUY NHẤT: xanh dương · trắng · đỏ · đen (nền ngả xanh thép, sáng hơn đen tuyệt đối)
BG      = "141C28"   # nền đen xanh
CARD    = "1F2A3A"   # nền thẻ
STROKE  = "3C5170"   # viền mảnh
RED     = "E23A2E"   # đỏ OTL
RED_BR  = "FF4A3D"   # đỏ sáng
BLUE    = "3E8FF0"   # xanh dương chủ đạo
BLUE_LT = "8CC2FF"   # xanh nhạt
EMBER   = BLUE       # giữ tên cũ, gộp về xanh dương
GOLD    = BLUE
INK     = "FFFFFF"
MUTE    = "EAF1FA"   # chữ nội dung — trắng ngả xanh
DIM     = "8CC2FF"   # nhãn phụ / chân trang — xanh nhạt

F_DISPLAY = "Segoe UI Black"
F_BOLD    = "Segoe UI Semibold"
F_BODY    = "Segoe UI"
F_LIGHT   = "Segoe UI Light"
F_NUM     = "Bahnschrift SemiBold Condensed"

W, H   = Inches(13.333), Inches(7.5)
MARGIN = Inches(0.85)
CW     = W - 2 * MARGIN          # bề rộng vùng nội dung

prs = Presentation()
prs.slide_width, prs.slide_height = W, H
BLANK = prs.slide_layouts[6]


# ─────────────────────────────────────────────────────────────────────────────
# TIỆN ÍCH XML
# ─────────────────────────────────────────────────────────────────────────────
def _no_line(shape):
    shape.line.fill.background()


def solid(shape, hexcolor, alpha=None):
    """Tô đặc, có thể kèm độ trong suốt (alpha 0..100 = % đục)."""
    shape.fill.solid()
    shape.fill.fore_color.rgb = RGBColor.from_string(hexcolor)
    if alpha is not None:
        srgb = shape.fill.fore_color._xFill.find(qn("a:srgbClr"))
        a = srgb.makeelement(qn("a:alpha"), {"val": str(int(alpha * 1000))})
        srgb.append(a)


def _set_fill_xml(shape, xml):
    """Thay khối tô của shape bằng XML tự viết.
    BẮT BUỘC chèn NGAY SAU prstGeom — sai thứ tự là PowerPoint bỏ qua, shape ra trắng."""
    from lxml import etree
    spPr = shape._element.spPr
    for tag in ("a:solidFill", "a:noFill", "a:gradFill",
                "a:blipFill", "a:pattFill", "a:grpFill"):
        old = spPr.find(qn(tag))
        if old is not None:
            spPr.remove(old)
    node = etree.fromstring(xml)
    geom = spPr.find(qn("a:prstGeom"))
    if geom is None:
        geom = spPr.find(qn("a:custGeom"))
    if geom is not None:
        geom.addnext(node)
    else:
        spPr.insert(0, node)


def radial_glow(shape, hexcolor, center_alpha=45):
    """Quầng sáng toả tròn — thay cho 'soft glow' của Canva."""
    xml = (
        '<a:gradFill %s rotWithShape="1">'
        '  <a:gsLst>'
        '    <a:gs pos="0"><a:srgbClr val="%s"><a:alpha val="%d"/></a:srgbClr></a:gs>'
        '    <a:gs pos="55000"><a:srgbClr val="%s"><a:alpha val="%d"/></a:srgbClr></a:gs>'
        '    <a:gs pos="100000"><a:srgbClr val="%s"><a:alpha val="0"/></a:srgbClr></a:gs>'
        '  </a:gsLst>'
        '  <a:path path="circle"><a:fillToRect l="50000" t="50000" r="50000" b="50000"/></a:path>'
        "</a:gradFill>" % (nsdecls("a"), hexcolor, center_alpha * 1000,
                           hexcolor, int(center_alpha * 1000 * 0.35), hexcolor)
    )
    _set_fill_xml(shape, xml)


def linear_fill(shape, c1, c2, angle=5400000):
    xml = (
        '<a:gradFill %s rotWithShape="1"><a:gsLst>'
        '<a:gs pos="0"><a:srgbClr val="%s"/></a:gs>'
        '<a:gs pos="100000"><a:srgbClr val="%s"/></a:gs>'
        '</a:gsLst><a:lin ang="%d" scaled="0"/></a:gradFill>'
        % (nsdecls("a"), c1, c2, angle)
    )
    _set_fill_xml(shape, xml)


def morph(slide, dur=900):
    """Chuyển cảnh Morph — vật thể cùng TÊN ở 2 slide sẽ tự bay/giãn sang nhau."""
    from lxml import etree
    xml = (
        '<mc:AlternateContent xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" '
        '   xmlns:p14="http://schemas.microsoft.com/office/powerpoint/2010/main" '
        '   xmlns:p159="http://schemas.microsoft.com/office/powerpoint/2015/09/main" '
        '   xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
        '  <mc:Choice Requires="p159">'
        '    <p:transition spd="slow" p14:dur="%d">'
        '      <p159:morph option="byObject"/>'
        "    </p:transition>"
        "  </mc:Choice>"
        "  <mc:Fallback>"
        '    <p:transition spd="slow"><p:fade/></p:transition>'
        "  </mc:Fallback>"
        "</mc:AlternateContent>" % dur
    )
    slide._element.append(etree.fromstring(xml))


# ─────────────────────────────────────────────────────────────────────────────
# TIỆN ÍCH DỰNG KHỐI
# ─────────────────────────────────────────────────────────────────────────────
def new_slide(notes=""):
    s = prs.slides.add_slide(BLANK)
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, W, H)
    linear_fill(bg, "1C2636", BG, 2700000)
    _no_line(bg)
    if notes:
        s.notes_slide.notes_text_frame.text = notes
    morph(s)
    return s


def ember(slide, left, top, size, color=RED, alpha=42, name="EMBER"):
    """Quầng lửa — vật thể xuyên suốt, Morph sẽ bay nó từ slide này sang slide kia.
    Hệ số 0.38: giữ nền thật mờ, tránh kiểu đồ hoạ hiệu ứng bóng bẩy."""
    alpha = alpha * 0.38
    e = slide.shapes.add_shape(MSO_SHAPE.OVAL, left, top, size, size)
    _no_line(e)
    radial_glow(e, color, alpha)
    e.name = name
    return e


def text(slide, left, top, width, height, runs, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, line=None, space_after=0, name=None):
    """runs = [(nội dung, cỡ chữ, font, màu, giãn chữ pt)] — mỗi phần tử 1 đoạn."""
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = True
    # TẮT autofit: để bật, PowerPoint tự co giãn hộp lúc mở file và chữ nhảy khỏi vị trí đã đặt.
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    for i, item in enumerate(runs):
        content, size, font, color = item[0], item[1], item[2], item[3]
        spc = item[4] if len(item) > 4 else 0
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        if line:
            p.line_spacing = line
        if space_after:
            p.space_after = Pt(space_after)
        r = p.add_run()
        r.text = content
        r.font.size = Pt(size)
        r.font.name = font
        r.font.color.rgb = RGBColor.from_string(color)
        if spc:
            r.font._rPr.set("spc", str(int(spc * 100)))
    if name:
        tb.name = name
    return tb


def rule(slide, left, top, width, color=RED, thick=Pt(4), name=None):
    # Pt() đã trả về Length tính bằng EMU — KHÔNG nhân 12700 lần nữa (nhân là phình khổng lồ).
    r = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, Emu(int(thick)))
    solid(r, color)
    _no_line(r)
    if name:
        r.name = name
    return r


def card(slide, left, top, width, height, fill=CARD, stroke=STROKE, name=None):
    # GÓC VUÔNG là cố ý: bo tròn làm trang trình chiếu giống mẫu dựng sẵn.
    c = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    solid(c, fill)
    c.line.color.rgb = RGBColor.from_string(stroke)
    c.line.width = Pt(1.25)
    if name:
        c.name = name
    return c


def corner_marks(slide, left, top, right, bottom, arm=Inches(0.3), color=STROKE):
    """Dấu góc chữ L — quy ước khung bản vẽ kỹ thuật, thay cho viền bo tròn."""
    t = Pt(1.25)
    for x, dx in ((left, 1), (right, -1)):
        for y, dy in ((top, 1), (bottom, -1)):
            hx = x if dx > 0 else x - arm
            rule(slide, hx, y if dy > 0 else y - Emu(int(t)), arm, color, t)
            vy = y if dy > 0 else y - arm
            v = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                       x if dx > 0 else x - Emu(int(t)), vy,
                                       Emu(int(t)), arm)
            solid(v, color)
            _no_line(v)


def kicker(slide, txt, top=Inches(0.72), color=RED):
    """Nhãn nhỏ in hoa, giãn chữ — dấu hiệu nhận diện của bộ slide."""
    return text(slide, MARGIN, top, CW, Inches(0.3),
                [(txt.upper(), 15, F_BOLD, color, 2.4)], name="KICKER")


def heading(slide, txt, size=46, top=Inches(1.06), color=INK, width=None):
    return text(slide, MARGIN, top, width or CW, Inches(1.5),
                [(txt, size, F_DISPLAY, color)], line=0.94, name="HEADING")


def page_no(slide, n, total):
    text(slide, MARGIN, H - Inches(0.72), CW, Inches(0.3),
         [("O TESLA  ·  OTL-06ALS", 13, F_BODY, DIM, 1.2)])
    text(slide, MARGIN, H - Inches(0.72), CW, Inches(0.3),
         [("%02d / %02d" % (n, total), 13, F_NUM, DIM, 1.2)], align=PP_ALIGN.RIGHT)


TOTAL = 11

# ─────────────────────────────────────────────────────────────────────────────
# 01 · BÌA
# ─────────────────────────────────────────────────────────────────────────────
s = new_slide("Between-batch preheat — máy tự chốt nhiệt nạp trước mỗi mẻ.")
ember(s, Inches(7.4), Inches(-1.6), Inches(9.4), RED, 50)
ember(s, Inches(-2.2), Inches(4.2), Inches(6.4), BLUE, 30, "EMBER2")
corner_marks(s, Inches(0.5), Inches(0.5), W - Inches(0.5), H - Inches(0.5))
rule(s, MARGIN, Inches(2.06), Inches(1.5), RED, Pt(5), "RULE")
text(s, MARGIN, Inches(1.5), CW, Inches(0.4),
     [("TÍNH NĂNG MỚI  ·  FIRMWARE OTL-06ALS", 16, F_BOLD, RED, 2.4)], name="KICKER")
text(s, MARGIN, Inches(2.5), Inches(9.6), Inches(2.4),
     [("PREHEAT", 138, F_DISPLAY, INK, -3)], line=0.86, name="HEADING")
text(s, MARGIN, Inches(4.6), Inches(11.6), Inches(0.7),
     [("Between-batch preheat — tự chốt nhiệt nạp trước mỗi mẻ", 32, F_BODY, MUTE)], line=1.15)
rule(s, MARGIN, Inches(5.55), Inches(11.6), STROKE, Pt(1))
text(s, MARGIN, Inches(5.85), Inches(11.6), Inches(0.4),
     [("O TESLA  ·  Điều khiển & Tự động hoá máy rang cà phê", 17, F_BODY, DIM, 1)])

# ─────────────────────────────────────────────────────────────────────────────
# 02 · HIỆN TRẠNG
# ─────────────────────────────────────────────────────────────────────────────
s = new_slide("Ba hạn chế khi sấy máy và phục hồi nhiệt giữa mẻ bằng tay.")
ember(s, Inches(9.9), Inches(-2.4), Inches(7.0), RED, 34)
kicker(s, "Hiện trạng")
rule(s, MARGIN, Inches(1.04), Inches(1.5), RED, Pt(5), "RULE")
heading(s, "Sấy máy và hồi nhiệt bằng tay", 46)
pains = [
    ("20–30′", "sấy máy đầu ca", "Thợ trực bảng điều khiển tới khi trống đạt nhiệt nạp."),
    ("7 kiểu", "đồng nhất giữa mẻ", "Bảy thợ cho ra bảy đường sấy khác nhau."),
    ("+15°C", "vọt lố ghi nhận", "Hạ 215 → 150°C: mẻ đầu lệch điểm TP."),
]
cw3 = (CW - Inches(0.5)) / 3
for i, (big, small, desc) in enumerate(pains):
    x = MARGIN + i * (cw3 + Inches(0.25))
    card(s, x, Inches(2.72), cw3, Inches(3.4))
    rule(s, x + Inches(0.4), Inches(3.12), Inches(0.6), RED, Pt(5))
    text(s, x + Inches(0.4), Inches(3.42), cw3 - Inches(0.8), Inches(1.0),
         [(big, 58, F_DISPLAY, RED_BR, -1)], line=0.95)
    text(s, x + Inches(0.4), Inches(4.4), cw3 - Inches(0.8), Inches(0.4),
         [(small.upper(), 15, F_BOLD, BLUE, 1.6)])
    text(s, x + Inches(0.4), Inches(4.95), cw3 - Inches(0.8), Inches(1.1),
         [(desc, 19, F_BODY, MUTE)], line=1.3)
page_no(s, 2, TOTAL)

# ─────────────────────────────────────────────────────────────────────────────
# 03 · GIẢI PHÁP
# ─────────────────────────────────────────────────────────────────────────────
s = new_slide("Between-batch preheat chuẩn hoá bước gia nhiệt giữa hai mẻ.")
ember(s, Inches(3.4), Inches(0.9), Inches(7.4), RED, 44)
kicker(s, "Between-batch preheat", Inches(0.9))
rule(s, MARGIN, Inches(1.22), Inches(1.5), RED, Pt(5), "RULE")
text(s, MARGIN, Inches(2.3), Inches(11.6), Inches(2.2),
     [("Một lệnh khởi động.", 58, F_DISPLAY, INK, -2),
      ("Toàn bộ chu trình tự động.", 58, F_DISPLAY, RED_BR, -2)],
     line=1.1, name="HEADING")
text(s, MARGIN, Inches(4.85), Inches(11.2), Inches(1.4),
     [("Bộ điều khiển đọc BT, ET và RoR mỗi giây, điều tiết gas và damper "
       "qua 8 trạng thái, giữ trống tại nhiệt nạp chờ charge.",
       24, F_BODY, MUTE)], line=1.4)
page_no(s, 3, TOTAL)

# ─────────────────────────────────────────────────────────────────────────────
# 04 · CHỈ TIÊU
# ─────────────────────────────────────────────────────────────────────────────
s = new_slide("Bốn chỉ tiêu kỹ thuật của bộ điều khiển gia nhiệt.")
ember(s, Inches(10.2), Inches(4.6), Inches(6.2), BLUE, 26)
kicker(s, "Chỉ tiêu kỹ thuật")
rule(s, MARGIN, Inches(1.04), Inches(1.5), RED, Pt(5), "RULE")
heading(s, "Bốn chỉ tiêu chính", 46)
stats = [
    ("≤ 3", "°C", "Vọt lố nhiệt nạp"),
    ("8", "trạng thái", "Nguội → giữ nhiệt"),
    ("12", "vùng", "Bảng bù trước 25°C"),
    ("5", "giây", "Chu kỳ ghi log CSV"),
]
cw4 = (CW - Inches(0.6)) / 4
for i, (num, unit, title) in enumerate(stats):
    x = MARGIN + i * (cw4 + Inches(0.2))
    card(s, x, Inches(2.68), cw4, Inches(3.2))
    text(s, x + Inches(0.35), Inches(2.98), cw4 - Inches(0.7), Inches(1.3),
         [(num, 78, F_DISPLAY, INK, -2)], line=0.92)
    text(s, x + Inches(0.35), Inches(4.3), cw4 - Inches(0.7), Inches(0.35),
         [(unit.upper(), 16, F_BOLD, RED_BR, 1.8)])
    rule(s, x + Inches(0.35), Inches(4.88), Inches(0.6), BLUE, Pt(3))
    text(s, x + Inches(0.35), Inches(5.12), cw4 - Inches(0.7), Inches(0.7),
         [(title, 21, F_BOLD, INK)], line=1.2)
page_no(s, 4, TOTAL)

# ─────────────────────────────────────────────────────────────────────────────
# 05 · TRÌNH TỰ
# ─────────────────────────────────────────────────────────────────────────────
s = new_slide("Sáu trạng thái chính; COOLING và COAST xử lý trống còn dư nhiệt.")
ember(s, Inches(-2.4), Inches(-1.4), Inches(6.4), BLUE, 26)
kicker(s, "Nguyên lý vận hành")
rule(s, MARGIN, Inches(1.04), Inches(1.5), RED, Pt(5), "RULE")
heading(s, "Trình tự sáu bước tự động", 46)
steps = [
    ("IDLE", "Phân loại", "Nguội · nóng · cần hạ"),
    ("PURGE", "Thông gió", "Xả khí buồng đốt"),
    ("IGNITE", "Đánh lửa", "Xác nhận có lửa"),
    ("HEATING", "Gia nhiệt", "Gas theo sai lệch và RoR"),
    ("HOLDING", "Giữ nhiệt", "Ghìm tại nhiệt nạp"),
    ("PRECISION", "Tinh chỉnh", "Điều khiển PI, ±2°C"),
]
bw = (CW - Inches(0.75)) / 6
for i, (code, name_, desc) in enumerate(steps):
    x = MARGIN + i * (bw + Inches(0.15))
    accent = RED_BR if i in (2, 5) else STROKE
    card(s, x, Inches(2.68), bw, Inches(2.85), CARD, accent)
    rule(s, x, Inches(2.68), bw, RED if i in (2, 5) else BLUE, Pt(4))
    text(s, x + Inches(0.22), Inches(2.94), bw - Inches(0.44), Inches(0.3),
         [("%02d" % (i + 1), 16, F_NUM, DIM, 1.2)])
    text(s, x + Inches(0.22), Inches(3.36), bw - Inches(0.44), Inches(0.5),
         [(code, 18, F_DISPLAY, INK, -0.3)], line=1.0)
    text(s, x + Inches(0.22), Inches(3.9), bw - Inches(0.44), Inches(0.35),
         [(name_, 17, F_BOLD, RED_BR)])
    text(s, x + Inches(0.22), Inches(4.4), bw - Inches(0.44), Inches(1.0),
         [(desc, 15, F_BODY, MUTE)], line=1.28)
    if i < 5:
        text(s, x + bw, Inches(3.5), Inches(0.15), Inches(0.35),
             [("›", 26, F_BODY, DIM)], align=PP_ALIGN.CENTER)
text(s, MARGIN, Inches(5.85), CW, Inches(0.8),
     [("COOLING và COAST xử lý trống còn dư nhiệt khi đổi từ mẻ rang đậm sang mẻ nhạt.",
       19, F_BODY, MUTE)], line=1.35)
page_no(s, 5, TOTAL)

# ─────────────────────────────────────────────────────────────────────────────
# 06 · HAI PHA
# ─────────────────────────────────────────────────────────────────────────────
s = new_slide("Chia 60/40: pha ramp ưu tiên tốc độ, pha precision ưu tiên độ chính xác.")
ember(s, Inches(5.6), Inches(-2.2), Inches(6.6), RED, 30)
kicker(s, "Chiến lược điều khiển")
rule(s, MARGIN, Inches(1.04), Inches(1.5), RED, Pt(5), "RULE")
heading(s, "Hai pha điều khiển", 46)
half = (CW - Inches(0.3)) / 2
blocks = [
    (MARGIN, "60%", "RAMP  ·  3 PHÚT ĐẦU", BLUE,
     ["Ưu tiên tốc độ gia nhiệt", "Damper thấp khi còn xa nhiệt nạp",
      "Chấp nhận sai lệch ≤ 5°C"]),
    (MARGIN + half + Inches(0.3), "40%", "PRECISION  ·  2 PHÚT CUỐI", RED_BR,
     ["Dao động trong dải ±2°C", "Điều khiển PI khử sai lệch tĩnh",
      "Chốt nhiệt nạp ±1°C"]),
]
for x, pct, title, col, items in blocks:
    card(s, x, Inches(2.62), half, Inches(3.6))
    text(s, x + Inches(0.5), Inches(2.86), half - Inches(1.0), Inches(0.9),
         [(pct, 64, F_DISPLAY, col, -1.5)], line=0.95)
    text(s, x + Inches(0.5), Inches(3.88), half - Inches(1.0), Inches(0.4),
         [(title, 17, F_BOLD, INK, 1.4)])
    rule(s, x + Inches(0.5), Inches(4.42), Inches(0.6), col, Pt(4))
    for j, it in enumerate(items):
        y = Inches(4.72) + Inches(0.48) * j
        text(s, x + Inches(0.5), y, Inches(0.22), Inches(0.34),
             [("—", 17, F_BODY, col)])
        text(s, x + Inches(0.92), y, half - Inches(1.42), Inches(0.34),
             [(it, 19, F_BODY, MUTE)])
page_no(s, 6, TOTAL)

# ─────────────────────────────────────────────────────────────────────────────
# 07 · TRỄ NHIỆT
# ─────────────────────────────────────────────────────────────────────────────
s = new_slide("Chuỗi trễ nhiệt: từ lệnh gas tới khi đầu dò BT thấy nhiệt mất ~30 giây.")
ember(s, Inches(9.6), Inches(4.4), Inches(6.6), BLUE, 26)
kicker(s, "Đặc tính đối tượng")
rule(s, MARGIN, Inches(1.04), Inches(1.5), RED, Pt(5), "RULE")
heading(s, "Trễ trong chuỗi truyền nhiệt", 46)
chain = [
    ("GAS %", "tín hiệu đặt", "tức thì", INK),
    ("ĐẦU ĐỐT", "ngọn lửa ổn định", "2–3 giây", BLUE),
    ("BUỒNG ĐỐT", "khí nóng · đầu dò ET", "5–10 giây", BLUE_LT),
    ("TRỐNG RANG", "vỏ trống · đầu dò BT", "15–20 giây", RED_BR),
]
bw = (CW - Inches(1.65)) / 4
for i, (nm, sub, lag, col) in enumerate(chain):
    x = MARGIN + i * (bw + Inches(0.55))
    card(s, x, Inches(2.78), bw, Inches(2.4))
    rule(s, x, Inches(2.78), bw, col, Pt(4))
    text(s, x + Inches(0.28), Inches(3.08), bw - Inches(0.56), Inches(0.5),
         [(nm, 19, F_DISPLAY, INK, -0.3)])
    text(s, x + Inches(0.28), Inches(3.66), bw - Inches(0.56), Inches(0.8),
         [(sub, 16, F_BODY, MUTE)], line=1.3)
    text(s, x + Inches(0.28), Inches(4.6), bw - Inches(0.56), Inches(0.35),
         [(lag.upper(), 15, F_BOLD, col, 1.2)])
    if i < 3:
        text(s, x + bw, Inches(3.48), Inches(0.55), Inches(0.45),
             [("→", 28, F_BODY, DIM)], align=PP_ALIGN.CENTER)
text(s, MARGIN, Inches(5.6), CW, Inches(0.9),
     [("Chuỗi trễ này chi phối cả mẻ rang. Bộ điều khiển chờ 15 giây sau mỗi bước gas "
       "rồi mới tác động tiếp.", 19, F_BODY, MUTE)], line=1.4)
page_no(s, 7, TOTAL)

# ─────────────────────────────────────────────────────────────────────────────
# 08 · TỰ HIỆU CHỈNH
# ─────────────────────────────────────────────────────────────────────────────
s = new_slide("Bảng bù trước 12 vùng và 3 tham số máy tự nhận dạng.")
ember(s, Inches(-2.6), Inches(3.4), Inches(6.8), RED, 28)
kicker(s, "Tự hiệu chỉnh")
rule(s, MARGIN, Inches(1.04), Inches(1.5), RED, Pt(5), "RULE")
heading(s, "Bù trước và thích nghi", 46)
text(s, MARGIN, Inches(2.42), Inches(7.4), Inches(0.7),
     [("Mỗi lượt sấy, bộ điều khiển lưu mức gas giữ nhiệt của từng vùng.",
       19, F_BODY, MUTE)], line=1.35)
zones = [("0–25", 0), ("25–50", 0), ("50–75", 1), ("75–100", 1), ("100–125", 2),
         ("125–150", 2), ("150–175", 3), ("175–200", 3), ("200–225", 4),
         ("225–250", 4), ("250–275", 3), ("275–300", 2)]
zw = (Inches(7.4) - Inches(0.55)) / 6
for i, (lab, lv) in enumerate(zones):
    col_i, row_i = i % 6, i // 6
    x = MARGIN + col_i * (zw + Inches(0.11))
    y = Inches(3.35) + row_i * Inches(0.95)
    shade = ["1E2A3A", "4A2320", "6E2A22", "A63026", "E23A2E"][lv]
    card(s, x, y, zw, Inches(0.85), shade, STROKE)
    text(s, x, y + Inches(0.14), zw, Inches(0.34),
         [(lab, 16, F_NUM, INK if lv >= 3 else MUTE)], align=PP_ALIGN.CENTER)
    text(s, x, y + Inches(0.5), zw, Inches(0.26),
         [("°C", 12, F_BODY, INK if lv >= 3 else DIM, 1)], align=PP_ALIGN.CENTER)
text(s, MARGIN, Inches(5.42), Inches(7.4), Inches(0.4),
     [("12 VÙNG × 25°C  ·  LƯU THƯỜNG TRÚ", 14.5, F_BOLD, DIM, 1.6)])

lx = MARGIN + Inches(7.85)
lw = CW - Inches(7.85)
card(s, lx, Inches(2.62), lw, Inches(3.65))
text(s, lx + Inches(0.45), Inches(2.9), lw - Inches(0.9), Inches(0.4),
     [("THAM SỐ TỰ NHẬN DẠNG", 14.5, F_BOLD, BLUE, 1.2)])
adapt = [
    ("Quán tính nhiệt", "Nhiệt còn tăng sau khoá gas"),
    ("Tổn thất nhiệt", "Tốc độ nguội của trống"),
    ("Khuếch đại gas", "Độ tăng nhiệt trên mỗi 1% gas"),
]
for j, (t, d) in enumerate(adapt):
    y = Inches(3.45) + Inches(0.95) * j
    rule(s, lx + Inches(0.45), y + Inches(0.02), Inches(0.34), RED, Pt(4))
    text(s, lx + Inches(0.45), y + Inches(0.18), lw - Inches(0.8), Inches(0.35),
         [(t, 20, F_BOLD, INK)])
    text(s, lx + Inches(0.45), y + Inches(0.56), lw - Inches(0.8), Inches(0.3),
         [(d, 15, F_BODY, MUTE)])
page_no(s, 8, TOTAL)

# ─────────────────────────────────────────────────────────────────────────────
# 09 · AN TOÀN
# ─────────────────────────────────────────────────────────────────────────────
s = new_slide("Năm cờ lỗi tự giám sát và hai khoá cứng đóng gas.")
ember(s, Inches(9.4), Inches(-2.0), Inches(6.4), RED, 32)
kicker(s, "An toàn vận hành")
rule(s, MARGIN, Inches(1.04), Inches(1.5), RED, Pt(5), "RULE")
heading(s, "Giám sát và bảo vệ", 46)
faults = [
    ("Mất tín hiệu đầu dò", "BT hoặc ET sụt đột ngột"),
    ("RoR bất thường", "Vượt dải cho phép"),
    ("Mất lửa", "Cấp gas mà nhiệt không lên"),
    ("Mất truyền thông HMI", "Màn hình không đáp ứng"),
    ("Lỗi thẻ nhớ", "Mất log, máy vẫn chạy"),
]
fw = (CW - Inches(0.4)) / 5
for i, (t, d) in enumerate(faults):
    x = MARGIN + i * (fw + Inches(0.1))
    card(s, x, Inches(2.62), fw, Inches(2.2))
    rule(s, x, Inches(2.62), fw, BLUE, Pt(4))
    text(s, x + Inches(0.24), Inches(2.92), fw - Inches(0.48), Inches(0.9),
         [(t, 18, F_BOLD, INK)], line=1.15)
    text(s, x + Inches(0.24), Inches(3.88), fw - Inches(0.48), Inches(0.8),
         [(d, 15.5, F_BODY, MUTE)], line=1.28)
hard = [
    ("ET − BT VƯỢT 160°C", "Huỷ gia nhiệt, khoá gas và báo lỗi."),
    ("ĐÁNH LỬA QUÁ GIỜ", "Không xác nhận được lửa thì khoá gas."),
]
for i, (t, d) in enumerate(hard):
    ww = (CW - Inches(0.3)) / 2
    x = MARGIN + i * (ww + Inches(0.3))
    card(s, x, Inches(5.05), ww, Inches(1.35), "2E1210", RED)
    text(s, x + Inches(0.4), Inches(5.28), ww - Inches(0.8), Inches(0.35),
         [("KHOÁ CỨNG  ·  " + t, 15, F_BOLD, RED_BR, 1.2)])
    text(s, x + Inches(0.4), Inches(5.72), ww - Inches(0.8), Inches(0.45),
         [(d, 18, F_BODY, MUTE)])
page_no(s, 9, TOTAL)

# ─────────────────────────────────────────────────────────────────────────────
# 10 · ĐÁNH GIÁ
# ─────────────────────────────────────────────────────────────────────────────
s = new_slide("Đối chiếu vận hành thủ công và between-batch preheat tự động.")
ember(s, Inches(10.4), Inches(4.2), Inches(6.0), BLUE, 24)
kicker(s, "Đánh giá")
rule(s, MARGIN, Inches(1.04), Inches(1.5), RED, Pt(5), "RULE")
heading(s, "So sánh chỉ tiêu vận hành", 46)
rows = [
    ("", "THỦ CÔNG", "PREHEAT TỰ ĐỘNG"),
    ("Người trực khi sấy", "Suốt 20–30 phút", "Không cần"),
    ("Vọt lố nhiệt nạp", "+1 … +3°C", "≤ 3°C"),
    ("Rang liên mẻ", "Canh lại từ đầu", "Tự bù theo nhiệt dư"),
    ("Dữ liệu truy vết", "Không có", "CSV 5 giây/dòng"),
]
tw = [Inches(4.0), Inches(3.85), Inches(3.78)]
ty = Inches(2.75)
rh = Inches(0.78)
for r, row in enumerate(rows):
    x = MARGIN
    for c_i, cell in enumerate(row):
        y = ty + rh * r
        if r == 0:
            if cell:
                card(s, x, y, tw[c_i], rh, CARD if c_i == 1 else "2E1210",
                     STROKE if c_i == 1 else RED)
            text(s, x + Inches(0.3), y + Inches(0.26), tw[c_i] - Inches(0.6), Inches(0.34),
                 [(cell, 16, F_BOLD, MUTE if c_i == 1 else RED_BR, 1.6)])
        else:
            if c_i == 0:
                text(s, x + Inches(0.05), y + Inches(0.22), tw[c_i] - Inches(0.3), Inches(0.4),
                     [(cell, 20, F_BODY, MUTE)])
            else:
                col = MUTE if c_i == 1 else INK
                fnt = F_BODY if c_i == 1 else F_BOLD
                text(s, x + Inches(0.3), y + Inches(0.2), tw[c_i] - Inches(0.6), Inches(0.42),
                     [(cell, 20, fnt, col)])
            rule(s, x, y + rh - Inches(0.01), tw[c_i], STROKE, Pt(1))
        x += tw[c_i] + Inches(0.15)
page_no(s, 10, TOTAL)

# ─────────────────────────────────────────────────────────────────────────────
# 11 · KẾT
# ─────────────────────────────────────────────────────────────────────────────
s = new_slide("Chốt lại và trạng thái phát hành.")
ember(s, Inches(2.9), Inches(0.4), Inches(8.4), RED, 48)
ember(s, Inches(10.6), Inches(5.0), Inches(5.0), BLUE, 26, "EMBER2")
corner_marks(s, Inches(0.5), Inches(0.5), W - Inches(0.5), H - Inches(0.5))
rule(s, MARGIN, Inches(2.06), Inches(1.5), RED, Pt(5), "RULE")
text(s, MARGIN, Inches(1.5), CW, Inches(0.4),
     [("PREHEAT  ·  OTL-06ALS", 16, F_BOLD, RED, 2.4)], name="KICKER")
text(s, MARGIN, Inches(2.5), Inches(11.6), Inches(2.6),
     [("Gia nhiệt tự động.", 58, F_DISPLAY, INK, -2),
      ("Đúng nhiệt nạp mỗi mẻ.", 58, F_DISPLAY, RED_BR, -2)],
     line=1.1, name="HEADING")
rule(s, MARGIN, Inches(5.3), Inches(11.6), STROKE, Pt(1))
foot = [("Trạng thái", "Đang chạy thử có giám sát"),
        ("Áp dụng cho", "Đầu đốt thường và premix"),
        ("Liên hệ", "otlpro.com@gmail.com")]
for i, (k, v) in enumerate(foot):
    x = MARGIN + i * Inches(3.95)
    text(s, x, Inches(5.58), Inches(3.8), Inches(0.32),
         [(k.upper(), 14, F_BOLD, DIM, 1.6)])
    text(s, x, Inches(6.02), Inches(3.8), Inches(0.45),
         [(v, 19, F_BOLD, INK)])

# ─────────────────────────────────────────────────────────────────────────────
out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "OTL-Preheat-Gioi-thieu.pptx")
prs.save(out)
print("Da luu:", out)
print("So slide:", len(prs.slides.__iter__.__self__._sldIdLst))
