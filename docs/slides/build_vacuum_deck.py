# -*- coding: utf-8 -*-
"""
Bộ slide giới thiệu VACUUM CONTROL (điều khiển áp hút) — OTL-06ALS.
Tone xanh dương / đen, chuyển cảnh Morph, đồ thị vẽ bằng vector thật.

Chạy:  python build_vacuum_deck.py
Ra:    OTL-Vacuum-Control-Gioi-thieu.pptx
"""
import math
import os

from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

from otl_deck import Deck

# ─────────────────────────────────────────────────────────────────────────────
# BẢNG MÀU — xanh dương trên nền đen
# ─────────────────────────────────────────────────────────────────────────────
PALETTE = {
    "bg":      "060A12",   # đen ngả xanh
    "bg2":     "0C1424",
    "card":    "101A2C",
    "cardlo":  "0B1322",
    "stroke":  "1F2E48",
    "accent":  "2E86FF",   # xanh dương chính
    "accent2": "22D3EE",   # xanh ngọc
    "ice":     "7DD3FC",   # xanh băng
    "gold":    "F5B841",
    "ink":     "FFFFFF",
    "mute":    "94A6C0",
    "dim":     "5B6C88",
    "grid":    "18253C",
}

D = Deck(PALETTE, total=12)
M, CW, W, H = D.M, D.CW, D.W, D.H


def IN(v):
    return int(Inches(v))


# ─────────────────────────────────────────────────────────────────────────────
# 01 · BÌA
# ─────────────────────────────────────────────────────────────────────────────
s = D.slide("Mở đầu: điều khiển theo áp hút thay vì theo phần trăm gió.")
D.orb(s, IN(7.2), IN(-1.9), IN(9.8), "accent", 46)
D.orb(s, IN(-2.6), IN(4.0), IN(6.8), "accent2", 20, "ORB2")
D.text(s, M, IN(1.5), CW, IN(0.4),
       [("TÍNH NĂNG  ·  FIRMWARE OTL-06ALS", 12, "bold", "accent2", 2.4)], name="KICKER")
D.rule(s, M, IN(2.06), IN(1.5), "accent", Pt(5), "RULE")
D.text(s, M, IN(2.4), IN(11.2), IN(2.9),
       [("VACUUM", 96, "display", "ink", -3),
        ("CONTROL", 96, "display", "accent", -3)], line=0.9, name="HEADING")
D.text(s, M, IN(5.05), IN(9.6), IN(0.7),
       [("Giữ áp hút — không giữ phần trăm gió", 26, "light", "mute")])
D.rule(s, M, IN(5.75), IN(11.6), "stroke", Pt(1))
D.text(s, M, IN(6.02), IN(11.6), IN(0.4),
       [("O TESLA  ·  Điều khiển & Tự động hoá máy rang cà phê", 13, "body", "dim", 1)])

# ─────────────────────────────────────────────────────────────────────────────
# 02 · VẤN ĐỀ
# ─────────────────────────────────────────────────────────────────────────────
s = D.slide("Cùng một % gió nhưng lực hút thực tế đổi theo ngày.")
D.orb(s, IN(9.8), IN(-2.5), IN(7.2), "accent", 30)
D.orb(s, IN(-3.0), IN(5.2), IN(5.2), "accent2", 14, "ORB2")
D.kicker(s, "Vấn đề")
D.heading(s, "Cùng 40% gió — hôm nay khác hôm qua")
cards = [
    ("Vỏ lụa bám lọc", "Rang được vài mẻ là lưới lọc dày lên. Quạt vẫn quay đúng 40% "
                       "nhưng gió qua trống đã yếu đi rõ."),
    ("Bụi bám đường ống", "Xiclon và đường ống bám bụi dần theo tuần. Cùng một mức đặt, "
                          "lực hút cứ trôi đi mà không ai để ý."),
    ("Cửa gió và thời tiết", "Cửa gió chỉnh tay, áp suất ngoài trời, ống khói nóng nguội — "
                             "mỗi thứ đẩy lưu lượng đi một ít."),
]
cw3 = (CW - IN(0.5)) / 3
for i, (t, d) in enumerate(cards):
    x = int(M + i * (cw3 + IN(0.25)))
    D.card(s, x, IN(2.75), int(cw3), IN(2.95))
    D.rule(s, x + IN(0.4), IN(3.15), IN(0.55), "accent2", Pt(4))
    D.text(s, x + IN(0.4), IN(3.5), int(cw3 - IN(0.8)), IN(0.5),
           [(t, 22, "display", "ink", -0.5)])
    D.text(s, x + IN(0.4), IN(4.12), int(cw3 - IN(0.8)), IN(1.4),
           [(d, 13.5, "body", "mute")], line=1.35)
D.text(s, M, IN(6.0), CW, IN(0.5),
       [("Phần trăm gió chỉ là lệnh gửi cho biến tần. Thứ quyết định mẻ rang là "
         "LỰC HÚT THẬT trong trống — đo bằng Pa.", 15, "body", "ice")], line=1.35)
D.footer(s, 2)

# ─────────────────────────────────────────────────────────────────────────────
# 03 · TUYÊN NGÔN
# ─────────────────────────────────────────────────────────────────────────────
s = D.slide("Tuyên ngôn: đặt theo Pa, máy tự tìm % gió.")
D.orb(s, IN(3.2), IN(0.7), IN(7.8), "accent", 44)
D.kicker(s, "Giải pháp", IN(0.9))
D.text(s, M, IN(2.3), IN(11.6), IN(2.2),
       [("Anh đặt Pa.", 60, "display", "ink", -2),
        ("Máy tự tìm % gió.", 60, "display", "accent2", -2)], line=1.1, name="HEADING")
D.text(s, M, IN(4.85), IN(10.6), IN(1.2),
       [("Cảm biến áp suất đọc lực hút thật trong trống mỗi vòng lặp. Firmware so với "
         "mức anh đặt rồi tự nhích biến tần gió lên xuống cho tới khi khớp — lọc có bẩn, "
         "ống có bám bụi thì nó tự bù.", 17, "body", "mute")], line=1.4)
D.footer(s, 3)

# ─────────────────────────────────────────────────────────────────────────────
# 04 · VÒNG LẶP ĐIỀU KHIỂN  (đồ thị vector)
# ─────────────────────────────────────────────────────────────────────────────
s = D.slide("Vòng lặp: lệch quá ±3 Pa thì nhích 1%, trong vùng chết thì đứng yên.")
D.orb(s, IN(10.6), IN(4.6), IN(6.0), "accent", 20)
D.kicker(s, "Vòng lặp")
D.heading(s, "Lệch quá 3 Pa mới nhích — mỗi lần 1%")

# khung đồ thị
gx0, gx1 = IN(0.85), IN(7.55)
gy_sp = IN(3.75)
PA = IN(0.032)                       # 1 Pa = 0,032 inch
band = int(3 * PA)
D.card(s, gx0, IN(2.85), gx1 - gx0, IN(2.85), "cardlo", "stroke")
# vùng chết ±3 Pa
bandbox = s.shapes.add_shape(1, gx0 + IN(0.1), gy_sp - band, gx1 - gx0 - IN(0.2), 2 * band)
D.solid(bandbox, "accent2", 14)
D._no_line(bandbox)
# đường mức đặt
D.polyline(s, [(gx0 + IN(0.1), gy_sp), (gx1 - IN(0.1), gy_sp)], "accent2", Pt(1.75), "dash")
# đường áp hút đo được — bậc thang hội tụ
pts = []
n = 34
for i in range(n):
    err = 46 * math.exp(-0.155 * i) + (2.2 * math.sin(i * 0.9) if i > 14 else 0)
    x = gx0 + IN(0.18) + int((gx1 - gx0 - IN(0.36)) * i / (n - 1))
    y = int(gy_sp + err * PA)
    if pts:
        pts.append((x, pts[-1][1]))
    pts.append((x, y))
D.polyline(s, pts, "accent", Pt(2.75))
D.dot(s, pts[0][0], pts[0][1], IN(0.1), "accent")
D.dot(s, pts[-1][0], pts[-1][1], IN(0.1), "ice")
D.text(s, gx0 + IN(0.25), IN(2.98), IN(3.0), IN(0.3),
       [("ÁP HÚT ĐO ĐƯỢC", 10.5, "bold", "accent", 1.6)])
D.text(s, gx1 - IN(2.3), gy_sp - IN(0.42), IN(2.1), IN(0.3),
       [("MỨC ĐẶT ±3 Pa", 10.5, "bold", "accent2", 1.6)], align=PP_ALIGN.RIGHT)
D.text(s, gx0, IN(5.82), gx1 - gx0, IN(0.3),
       [("thời gian →", 11, "body", "dim")], align=PP_ALIGN.CENTER)

lx, lw = IN(8.15), int(CW + M - IN(8.15))
D.card(s, lx, IN(2.85), lw, IN(2.85))
rules_ = [
    ("Thấp hơn mức đặt", "tăng gió 1%", "accent"),
    ("Cao hơn mức đặt", "giảm gió 1%", "accent"),
    ("Trong vùng ±3 Pa", "đứng yên, không rung", "accent2"),
]
for j, (a, b, col) in enumerate(rules_):
    y = IN(3.2) + int(IN(0.88) * j)
    D.rule(s, lx + IN(0.45), y, IN(0.3), col, Pt(3))
    D.text(s, lx + IN(0.45), y + IN(0.16), lw - IN(0.9), IN(0.3),
           [(a, 15, "bold", "ink")])
    D.text(s, lx + IN(0.45), y + IN(0.46), lw - IN(0.9), IN(0.3),
           [(b, 13, "body", col)])
D.text(s, M, IN(6.3), CW, IN(0.4),
       [("Vùng chết ±3 Pa là thứ giữ cho biến tần không rung liên tục quanh mức đặt.",
         13, "body", "dim")])
D.footer(s, 4)

# ─────────────────────────────────────────────────────────────────────────────
# 05 · NHỊP BƯỚC ĐỘNG
# ─────────────────────────────────────────────────────────────────────────────
s = D.slide("Lệch nhiều đi nhanh, gần tới thì đi chậm cho khỏi vọt.")
D.orb(s, IN(-2.8), IN(-1.6), IN(6.6), "accent", 26)
D.kicker(s, "Nhịp bước")
D.heading(s, "Xa thì bước nhanh, gần thì bước chậm")
D.text(s, M, IN(2.35), IN(6.0), IN(1.0),
       [("Nhịp nhích gió không cố định. Lệch càng lớn thì khoảng nghỉ giữa hai bước "
         "càng ngắn, nên máy đuổi kịp nhanh; càng gần mức đặt thì bước càng thưa, "
         "tránh vọt qua rồi phải kéo lại.", 15, "body", "mute")], line=1.4)
tiles = [("1,5 giây", "khi lệch ≥ 30 Pa", "accent"),
         ("3,0 giây", "khi vừa ra khỏi vùng chết", "accent2")]
for j, (a, b, col) in enumerate(tiles):
    y = IN(4.05) + int(IN(1.05) * j)
    D.card(s, M, y, IN(5.9), IN(0.88))
    D.text(s, M + IN(0.4), y + IN(0.2), IN(2.2), IN(0.5),
           [(a, 26, "display", col, -1)])
    D.text(s, M + IN(2.9), y + IN(0.3), IN(2.8), IN(0.35),
           [(b, 13.5, "body", "mute")])

# đồ thị ánh xạ sai lệch → nhịp
cx0, cx1 = IN(7.5), IN(12.48)
cy0, cy1 = IN(3.0), IN(5.9)
D.card(s, cx0, IN(2.75), cx1 - cx0, IN(3.4), "cardlo", "stroke")
px0, px1 = cx0 + IN(0.85), cx1 - IN(0.45)
py0, py1 = cy0 + IN(0.35), cy1 - IN(0.35)
for k in range(4):                                  # lưới ngang
    gy = py0 + int((py1 - py0) * k / 3)
    D.polyline(s, [(px0, gy), (px1, gy)], "grid", Pt(0.75))
D.polyline(s, [(px0, py0), (px0 + int((px1 - px0) * 30 / 45.0), py1),
               (px1, py1)], "accent", Pt(3))
D.dot(s, px0, py0, IN(0.09), "accent2")
D.dot(s, px0 + int((px1 - px0) * 30 / 45.0), py1, IN(0.09), "accent2")
D.text(s, cx0 + IN(0.3), IN(2.98), IN(3.0), IN(0.3),
       [("KHOẢNG NGHỈ GIỮA 2 BƯỚC", 10, "bold", "ice", 1.4)])
D.text(s, cx0 + IN(0.25), py0 - IN(0.12), IN(0.6), IN(0.25),
       [("3,0s", 10, "num", "dim")])
D.text(s, cx0 + IN(0.25), py1 - IN(0.12), IN(0.6), IN(0.25),
       [("1,5s", 10, "num", "dim")])
for frac, lab in ((0.0, "3 Pa"), (30 / 45.0, "30 Pa"), (1.0, "45 Pa")):
    D.text(s, px0 + int((px1 - px0) * frac) - IN(0.4), py1 + IN(0.16), IN(0.8), IN(0.25),
           [(lab, 10, "num", "dim")], align=PP_ALIGN.CENTER)
D.footer(s, 5)

# ─────────────────────────────────────────────────────────────────────────────
# 06 · BẢNG FF
# ─────────────────────────────────────────────────────────────────────────────
s = D.slide("Bảng ghi nhớ: mức đặt Pa nào thì ứng với bao nhiêu % gió.")
D.orb(s, IN(10.2), IN(-2.2), IN(6.4), "accent", 26)
D.kicker(s, "Bảng ghi nhớ")
D.heading(s, "Máy nhớ sẵn: Pa nào thì mấy phần trăm")
# đồ thị Air% ↔ Pa
gx0, gx1 = IN(0.85), IN(7.2)
gy0, gy1 = IN(2.95), IN(5.95)
D.card(s, gx0, gy0, gx1 - gx0, gy1 - gy0, "cardlo", "stroke")
px0, px1 = gx0 + IN(0.85), gx1 - IN(0.45)
py0, py1 = gy0 + IN(0.4), gy1 - IN(0.78)
for k in range(5):
    gy = py0 + int((py1 - py0) * k / 4)
    D.polyline(s, [(px0, gy), (px1, gy)], "grid", Pt(0.75))
curve = []
for i in range(0, 101, 4):
    pa = 160.0 * (i / 100.0) ** 1.35
    x = px0 + int((px1 - px0) * i / 100.0)
    y = py1 - int((py1 - py0) * pa / 160.0)
    curve.append((x, y))
D.polyline(s, curve, "accent", Pt(3))
for i in range(0, 101, 20):
    pa = 160.0 * (i / 100.0) ** 1.35
    D.dot(s, px0 + int((px1 - px0) * i / 100.0),
          py1 - int((py1 - py0) * pa / 160.0), IN(0.11), "ice")
D.text(s, gx0 + IN(0.3), gy0 + IN(0.13), IN(3.0), IN(0.3),
       [("ÁP HÚT (Pa)", 10, "bold", "ice", 1.4)])
for i in range(0, 101, 25):
    D.text(s, px0 + int((px1 - px0) * i / 100.0) - IN(0.35), py1 + IN(0.16),
           IN(0.7), IN(0.25), [("%d%%" % i, 10, "num", "dim")], align=PP_ALIGN.CENTER)
D.text(s, gx0, gy1 - IN(0.32), gx1 - gx0, IN(0.25),
       [("phần trăm gió →", 10.5, "body", "dim")], align=PP_ALIGN.CENTER)

lx, lw = IN(7.85), int(CW + M - IN(7.85))
D.card(s, lx, gy0, lw, gy1 - gy0)
items = [
    ("Đổi mức đặt là nhảy thẳng", "Lấy ngay % gió đã học cho mức Pa đó."),
    ("60 ô nhớ", "Hai mức cách nhau dưới 3 Pa gộp chung một ô."),
    ("Lưu trong thẻ nhớ", "Ghi ra /pid_ff.txt, mất điện vẫn còn."),
]
for j, (t, d) in enumerate(items):
    y = gy0 + IN(0.42) + int(IN(0.92) * j)
    D.rule(s, lx + IN(0.42), y, IN(0.3), "accent", Pt(3))
    D.text(s, lx + IN(0.42), y + IN(0.16), lw - IN(0.84), IN(0.32),
           [(t, 15.5, "bold", "ink")])
    D.text(s, lx + IN(0.42), y + IN(0.48), lw - IN(0.84), IN(0.5),
           [(d, 12.5, "body", "mute")], line=1.3)
D.footer(s, 6)

# ─────────────────────────────────────────────────────────────────────────────
# 07 · FACTORY AUTO-TUNE
# ─────────────────────────────────────────────────────────────────────────────
s = D.slide("Chạy một lần lúc lắp máy: quét toàn dải để dựng bảng.")
D.orb(s, IN(-2.4), IN(4.4), IN(6.4), "accent2", 18)
D.kicker(s, "Cân chỉnh đầu vào")
D.heading(s, "Bấm một lần — năm phút có cả bảng")
# bậc thang quét
bx0, bx1 = IN(0.85), IN(12.48)
by1 = IN(5.55)
bh = IN(2.05)
nb = 26
bw = int((bx1 - bx0 - IN(0.2)) / nb)
for i in range(nb):
    frac = (i / (nb - 1.0)) ** 1.35
    h = int(bh * (0.06 + 0.94 * frac))
    x = bx0 + i * bw
    r = s.shapes.add_shape(1, x, by1 - h, bw - IN(0.05), h)
    D.solid(r, "accent" if i % 2 == 0 else "accent2", 30 + int(55 * frac))
    D._no_line(r)
D.polyline(s, [(bx0, by1), (bx1, by1)], "stroke", Pt(1.5))
D.text(s, bx0, IN(5.68), bx1 - bx0, IN(0.3),
       [("0%  →  100% gió,  mỗi bước 2%", 11.5, "num", "dim", 1.2)], align=PP_ALIGN.CENTER)
steps = [("15 giây", "chờ máy ổn định rồi mới quét"),
         ("3 giây", "giữ mỗi mức gió, đo Pa ở 2 giây cuối"),
         ("51 điểm", "ghi thẳng vào bảng ghi nhớ"),
         ("~5 phút", "xong là tự lưu thẻ và tự tắt")]
sw = (CW - IN(0.45)) / 4
for i, (a, b) in enumerate(steps):
    x = int(M + i * (sw + IN(0.15)))
    D.text(s, x, IN(2.42), int(sw), IN(0.45),
           [(a, 25, "display", "ice", -0.8)])
    D.text(s, x, IN(2.86), int(sw), IN(0.4),
           [(b, 12.5, "body", "mute")], line=1.3)
D.footer(s, 7)

# ─────────────────────────────────────────────────────────────────────────────
# 08 · TỰ HỌC LÚC CHẠY
# ─────────────────────────────────────────────────────────────────────────────
s = D.slide("Ngoài lần quét đầu, máy vẫn học thêm mỗi khi chạy ổn định.")
D.orb(s, IN(9.6), IN(4.2), IN(6.4), "accent", 22)
D.kicker(s, "Tự học")
D.heading(s, "Chạy ngày nào, bảng chuẩn thêm ngày đó")
flow = [("Ổn định 10 giây", "Áp hút nằm trong vùng chết liên tục 10 giây"),
        ("Ghi vào bảng", "Lưu cặp mức đặt và % gió đang dùng"),
        ("Lệch ≥ 3% mới sửa", "Nhiễu vặt không làm hỏng số đã học"),
        ("60 giây lưu thẻ", "Ghi SD ngoài vòng lặp, không làm nghẽn máy")]
fw = (CW - IN(0.45)) / 4
for i, (t, d) in enumerate(flow):
    x = int(M + i * (fw + IN(0.15)))
    D.card(s, x, IN(2.8), int(fw), IN(2.15))
    D.rule(s, x, IN(2.8), int(fw), "accent" if i < 2 else "accent2", Pt(3))
    D.text(s, x + IN(0.28), IN(3.1), int(fw - IN(0.56)), IN(0.3),
           [("%02d" % (i + 1), 12, "num", "dim", 1.2)])
    D.text(s, x + IN(0.28), IN(3.45), int(fw - IN(0.56)), IN(0.6),
           [(t, 17, "display", "ink", -0.3)], line=1.05)
    D.text(s, x + IN(0.28), IN(4.12), int(fw - IN(0.56)), IN(0.7),
           [(d, 12.5, "body", "mute")], line=1.3)
    if i < 3:
        D.text(s, x + int(fw), IN(3.75), IN(0.15), IN(0.3),
               [("›", 20, "body", "dim")], align=PP_ALIGN.CENTER)
D.text(s, M, IN(5.35), CW, IN(0.8),
       [("Việc ghi thẻ nhớ nằm ngoài vòng điều khiển — máy không bao giờ khựng lại "
         "chỉ vì đang lưu dữ liệu.", 15, "body", "ice")], line=1.35)
D.footer(s, 8)

# ─────────────────────────────────────────────────────────────────────────────
# 09 · NHẢY THẲNG
# ─────────────────────────────────────────────────────────────────────────────
s = D.slide("Đổi mức đặt lớn thì nhảy thẳng, đổi nhỏ thì bò từ từ.")
D.orb(s, IN(3.0), IN(-2.4), IN(7.0), "accent", 26)
D.kicker(s, "Đổi mức đặt")
D.heading(s, "Đổi nhiều thì nhảy, đổi ít thì bò")
half = (CW - IN(0.3)) / 2
blocks = [
    (M, "> 30 Pa", "NHẢY THẲNG", "accent",
     ["Lấy % gió đã học cho mức mới", "Trừ hao một khoảng đệm cho khỏi vọt",
      "Đệm tự tính từ độ nhạy của máy: 8–25%", "Mỗi lần nhảy không quá 20%"]),
    (int(M + half + IN(0.3)), "≤ 30 Pa", "BÒ TỪ TỪ", "accent2",
     ["Không nhảy, giữ nguyên % gió đang chạy", "Để vòng lặp 1% tự bù dần",
      "Tránh giật gió giữa mẻ đang rang", "Êm hơn cho cả hạt lẫn quạt"]),
]
for x, tag, title, col, items in blocks:
    D.card(s, x, IN(2.7), int(half), IN(3.4))
    D.text(s, x + IN(0.45), IN(3.0), int(half - IN(0.9)), IN(0.7),
           [(tag, 40, "display", col, -1.5)])
    D.text(s, x + IN(0.45), IN(3.72), int(half - IN(0.9)), IN(0.35),
           [(title, 12.5, "bold", "ink", 1.6)])
    D.rule(s, x + IN(0.45), IN(4.15), IN(0.5), col, Pt(3))
    for j, it in enumerate(items):
        y = IN(4.38) + int(IN(0.36) * j)
        D.text(s, x + IN(0.45), y, IN(0.16), IN(0.3), [("—", 12, "body", col)])
        D.text(s, x + IN(0.78), y, int(half - IN(1.25)), IN(0.3),
               [(it, 13.5, "body", "mute")])
D.footer(s, 9)

# ─────────────────────────────────────────────────────────────────────────────
# 10 · VÀO HỒ SƠ RANG
# ─────────────────────────────────────────────────────────────────────────────
s = D.slide("Áp hút được ghi theo từng giây vào hồ sơ và phát lại khi rang AUTO.")
D.orb(s, IN(10.4), IN(-2.0), IN(6.2), "accent2", 22)
D.kicker(s, "Vào mẻ rang")
D.heading(s, "Áp hút cũng là một phần của hồ sơ")
# dải thời gian
tx0, tx1 = IN(0.85), IN(12.48)
ty = IN(3.25)
D.polyline(s, [(tx0, ty), (tx1, ty)], "stroke", Pt(1.5))
marks = [(0.0, "NẠP", "accent"), (0.22, "TP", "accent2"), (0.48, "CHUYỂN VÀNG", "accent2"),
         (0.74, "NỔ HẠT", "accent"), (1.0, "XẢ", "accent")]
for f, lab, col in marks:
    x = tx0 + int((tx1 - tx0) * f)
    D.dot(s, x, ty, IN(0.14), col)
    D.text(s, x - IN(0.9), ty - IN(0.48), IN(1.8), IN(0.3),
           [(lab, 11, "bold", col, 1.4)], align=PP_ALIGN.CENTER)
# đường áp hút theo mẻ — trục dọc: Pa (hút mạnh dần về cuối mẻ)
vy0, vy1 = IN(3.66), IN(4.80)
for k in range(3):
    gy = vy0 + int((vy1 - vy0) * k / 2)
    D.polyline(s, [(tx0, gy), (tx1, gy)], "grid", Pt(0.75))
series = [(i / 60.0, 55 + 48 * (i / 60.0) + 9 * math.sin(i / 60.0 * 6.0))
          for i in range(61)]
lo = min(p for _, p in series)
hi = max(p for _, p in series)
vpts = [(tx0 + int((tx1 - tx0) * f),
         vy1 - int((vy1 - vy0) * (pa - lo) / (hi - lo)))
        for f, pa in series]
D.polyline(s, vpts, "accent", Pt(3.5))
D.dot(s, vpts[0][0], vpts[0][1], IN(0.11), "ice")
D.dot(s, vpts[-1][0], vpts[-1][1], IN(0.11), "ice")
D.text(s, tx0, IN(5.05), IN(5.0), IN(0.3),
       [("MỨC ÁP HÚT GHI THEO TỪNG GIÂY", 10.5, "bold", "accent", 1.6)])
notes = [("Ghi lúc rang tay", "Mỗi giây một giá trị, nằm chung hồ sơ với nhiệt và gas."),
         ("Phát lại lúc rang AUTO", "Máy bám đúng đường áp hút của mẻ nền đã chọn."),
         ("Xả xong trả về như cũ", "Kết mẻ hoặc bấm huỷ là trạng thái hút quay lại mức trước đó.")]
nw = (CW - IN(0.5)) / 3
for i, (t, d) in enumerate(notes):
    x = int(M + i * (nw + IN(0.25)))
    D.rule(s, x, IN(5.5), IN(0.4), "accent2", Pt(3))
    D.text(s, x, IN(5.67), int(nw), IN(0.3), [(t, 15, "bold", "ink")])
    D.text(s, x, IN(5.99), int(nw), IN(0.6), [(d, 12.5, "body", "mute")], line=1.3)
D.footer(s, 10)

# ─────────────────────────────────────────────────────────────────────────────
# 11 · CON SỐ
# ─────────────────────────────────────────────────────────────────────────────
s = D.slide("Năm con số tóm gọn.")
D.orb(s, IN(-2.6), IN(3.6), IN(6.6), "accent", 24)
D.kicker(s, "Tóm tắt")
D.heading(s, "Những con số cần nhớ")
stats = [("± 3", "Pa", "Vùng chết", "Trong khoảng này thì đứng yên"),
         ("1", "%", "Mỗi bước gió", "Nhích nhỏ nên không giật mẻ"),
         ("60", "ô nhớ", "Bảng ghi nhớ", "Lưu trong /pid_ff.txt"),
         ("51", "điểm", "Lần quét đầu", "0→100% gió, bước 2%"),
         ("~5", "phút", "Cân chỉnh", "Chỉ chạy một lần lúc lắp máy")]
cw5 = (CW - IN(0.6)) / 5
for i, (num, unit, title, sub) in enumerate(stats):
    x = int(M + i * (cw5 + IN(0.15)))
    D.card(s, x, IN(2.7), int(cw5), IN(3.2))
    D.text(s, x + IN(0.32), IN(3.05), int(cw5 - IN(0.64)), IN(1.0),
           [(num, 54, "display", "ink", -2)], line=0.95)
    D.text(s, x + IN(0.32), IN(3.98), int(cw5 - IN(0.64)), IN(0.35),
           [(unit.upper(), 12, "bold", "accent2", 1.8)])
    D.rule(s, x + IN(0.32), IN(4.5), IN(0.5), "stroke", Pt(2))
    D.text(s, x + IN(0.32), IN(4.72), int(cw5 - IN(0.64)), IN(0.4),
           [(title, 15, "bold", "ink")])
    D.text(s, x + IN(0.32), IN(5.08), int(cw5 - IN(0.64)), IN(0.7),
           [(sub, 12, "body", "dim")], line=1.3)
D.footer(s, 11)

# ─────────────────────────────────────────────────────────────────────────────
# 12 · KẾT
# ─────────────────────────────────────────────────────────────────────────────
s = D.slide("Chốt lại.")
D.orb(s, IN(2.8), IN(0.3), IN(8.6), "accent", 48)
D.orb(s, IN(10.4), IN(4.8), IN(5.2), "accent2", 18, "ORB2")
D.text(s, M, IN(1.5), CW, IN(0.4),
       [("VACUUM CONTROL  ·  OTL-06ALS", 12, "bold", "accent2", 2.4)], name="KICKER")
D.rule(s, M, IN(2.06), IN(1.5), "accent", Pt(5), "RULE")
D.text(s, M, IN(2.5), IN(11.6), IN(2.4),
       [("Lọc có bẩn, ống có bụi.", 56, "display", "ink", -2),
        ("Lực hút vẫn y như hôm qua.", 56, "display", "accent2", -2)],
       line=1.1, name="HEADING")
D.rule(s, M, IN(5.3), IN(11.6), "stroke", Pt(1))
foot = [("Đo bằng", "Cảm biến áp suất chênh, đơn vị Pa"),
        ("Cần có", "Biến tần gió điều khiển được"),
        ("Liên hệ", "O Tesla  ·  otlpro.com@gmail.com")]
for i, (k, v) in enumerate(foot):
    x = int(M + i * IN(3.95))
    D.text(s, x, IN(5.6), IN(3.7), IN(0.3), [(k.upper(), 10.5, "bold", "dim", 1.6)])
    D.text(s, x, IN(5.95), IN(3.7), IN(0.4), [(v, 15, "bold", "ink")])

out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "OTL-Vacuum-Control-Gioi-thieu.pptx")
D.save(out)
print("Da luu:", out)
