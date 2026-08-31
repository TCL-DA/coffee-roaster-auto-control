# -*- coding: utf-8 -*-
"""Man THU CONG nang cap - BAN DU CHUC NANG.

Muc tieu: phu HET 47 dia chi cua man cu ID=2, khong rot mot nut nao.
Giao dien cong nghiep man 10 inch: nen sang tuong phan cao, nut to bam bang gang.
"""
import sys
sys.path.insert(0, '.')
from hmilib import *
from layout4 import harvest, BASE_F
from render_screen import g as gk

PAGE   = C('EDEFF2')
CARD   = C('FFFFFF')
LINE   = C('D8DCE2')
INK    = C('16181D')
DIM    = C('6B7280')
BLUE   = C('1187E9')
ORANGE = C('E5670B')
GREEN  = C('1E9E52')
RED    = C('D9342B')
WHITE  = C('FFFFFF')

E = []
def add(p): E.append(p)

OLD, _, _ = harvest(BASE_F, 2)
USED = set()

def clone(read=None, write=None, sub=None, nth=0):
    """Lay doi tuong that tu man cu - giu DU moi khoi State + dia chi."""
    hits = []
    for n, (el, sts) in enumerate(OLD):
        if read is not None and gk(el, 'ReadVar', '') != read:
            continue
        if write is not None and gk(el, 'WriteVar', '') != write:
            continue
        if sub is not None and gk(el, 'SubType', '') != str(sub):
            continue
        hits.append((n, bytes(el), [bytes(s) for s in sts]))
    if len(hits) <= nth:
        return None, None
    n, el, sts = hits[nth]
    USED.add(n)
    return el, sts

def put(el, sts, x, y, w, h, *, name='obj', fill=CARD, on_fill=BLUE,
        font=15, bold=1, en=None, vi=None, plain=False):
    for k, v in (('X', x), ('Y', y), ('Width', w), ('Height', h)):
        el = setk(el, k, v)
    el = setstr(el, 'wDescTextLen0', name)
    el = setstr(el, 'wDescTextLen1', name)
    el = setk(el, 'BorderColor', LINE)
    out = []
    for k, s in enumerate(sts):
        f = on_fill if k else fill
        s = setk(s, 'FontColor', WHITE if k else INK)
        for kk in ('FgColor', 'BgColor', 'FgFillColor', 'FgFillEndColor',
                   'FgFillStopColor0', 'FgFillStopColor1'):
            s = setk(s, kk, f)
        s = setk(s, 'FgFillType', 1)
        s = setk(s, 'FillStyle', 1)
        s = setk(s, 'FontBold', bold)
        for fk in ('FontSize0', 'FontSize1'):
            s = setk(s, fk, font)
        for fk in ('FontName0', 'FontName1'):
            s = setk(s, fk, 'Arial')
        if en is not None:
            s = setstr(s, 'wTextLen0', en)
        if vi is not None:
            s = setstr(s, 'wTextLen1', vi)
        out.append(s)
    add((el, b''.join(out)))

def panel(x, y, w, h, *, fill=CARD, r=14, name='p'):
    add(card(x, y, w, h, fill=fill, radius=r, name=name))

def lbl(x, y, w, h, en, vi, *, size=12, color=DIM, bold=1, name='l'):
    add(text(x, y, w, h, en, vi, size=size, color=color, bold=bold,
             fill=CARD, name=name))

def val(x, y, w, h, reg, *, size=34, color=INK, gain='1.0', intn=3, dot=0,
        lead=0, name='v'):
    el, st = num(x, y, w, h, reg, size=size, color=color, gain=gain,
                 intn=intn, dot=dot, fill=CARD, name=name)
    if lead:
        el = setk(el, 'LeadingZero', 1)
    add((el, st))

L = '{Link2}1@'

# ================= HEADER  y 0..54 =================
panel(12, 4, 1000, 50, name='hd')
# chu trang thai (char display $M970) - giu nguyen cua man cu
el, sts = clone(read='$M970')
if el:
    put(el, sts, 24, 10, 200, 38, name='mode_txt', font=17)
# den bao che do THU CONG / TU DONG (40015)
el, sts = clone(write=L + 'W40015')
if el:
    put(el, sts, 236, 12, 120, 34, name='mode_ind', font=14,
        en='MANUAL', vi='THỦ CÔNG')
# nhiet do nap lieu (setpoint $M23) + nut BAT DAU
lbl(392, 14, 150, 16, 'CHARGE TEMP', 'NHIỆT NẠP (°C)', size=11,
    name='chg_l')
el, sts = clone(write='$M23')
if el:
    put(el, sts, 392, 30, 110, 20, name='chg_sp', font=15, bold=0)
el, sts = clone(write=L + 'W40001')
if el:
    put(el, sts, 858, 10, 146, 38, name='start', font=17,
        en='START', vi='BẮT ĐẦU', on_fill=GREEN)

# ================= DAI MOC  y 60..126 =================
MOCK = [('CHARGE', 'NẠP LIỆU', 40070, 40071, 40072, None),
        ('TP', 'TP', 40073, 40074, 40075, None),
        ('DE', 'DE', 40076, 40077, 40078, '$M20'),
        ('FCs', 'FCs', 40079, 40080, 40081, '$M21'),
        ('DEV', 'DEV', 40082, None, None, None),
        ('DROP', 'XẢ LIỆU', 40083, None, None, None)]
for i, (en, vi, rt, rm, rs, sp) in enumerate(MOCK):
    x = 12 + i * 168
    panel(x, 60, 160, 66, name='mk%d' % i)
    lbl(x + 10, 64, 100, 16, en, vi, size=11, name='mkl%d' % i)
    val(x + 10, 80, 92, 30, rt, size=23, gain='0.1', dot=1, name='mkt%d' % i)
    if rm:
        val(x + 104, 86, 20, 20, rm, size=13, color=DIM, intn=2, name='mkm%d' % i)
        add(text(x + 124, 86, 7, 20, ':', ':', size=13, color=DIM, fill=CARD,
                 name='mkc%d' % i))
        val(x + 131, 86, 20, 20, rs, size=13, color=DIM, intn=2, lead=1,
            name='mks%d' % i)
    if sp:
        el, sts = clone(write=sp)
        if el:
            put(el, sts, x + 104, 64, 48, 18, name='mksp%d' % i, font=11, bold=0)

# ================= DO THI  y 132..436 =================
panel(12, 132, 548, 304, name='gbg')
lbl(26, 138, 260, 18, 'ROASTING CURVE', 'ĐƯỜNG RANG', size=12,
    name='gl')
gel, gsts = None, None
for n, (el, sts) in enumerate(OLD):
    if gk(el, 'Type') == '9':
        gel, gsts = bytes(el), [bytes(s) for s in sts]
        USED.add(n)
        break
if gel:
    for k, v in (('X', 24), ('Y', 160), ('Width', 524), ('Height', 264)):
        gel = setk(gel, k, v)
    gel = setk(gel, 'BorderColor', LINE)
    gs = setk(gsts[0], 'BgColor', CARD)
    gs = setk(gs, 'FgColor', CARD)
    gs = setk(gs, 'GridColor', LINE)
    add((gel, gs))

# ================= COT DIEU KHIEN PHU  x 568..760 =================
panel(568, 132, 192, 304, name='ctl')
lbl(582, 138, 170, 18, 'AUX CONTROL', 'ĐIỀU KHIỂN PHỤ',
    size=12, name='ctll')
PAIRS = [(L + 'B1',  'CHART',  'ĐỒ THỊ'),
         (L + 'B4',  'AUX 2',  'PHỤ 2'),
         (L + 'B17', 'AUX 3',  'PHỤ 3')]
for i, (coil, en, vi) in enumerate(PAIRS):
    y = 162 + i * 74
    lbl(582, y, 170, 16, en, vi, size=11, name='pl%d' % i)
    eon, son = clone(write=coil, sub=1)
    eof, sof = clone(write=coil, sub=2)
    if eon:
        put(eon, son, 582, y + 18, 82, 44, name='on%d' % i, font=14,
            en='ON', vi='BẬT', on_fill=GREEN)
    if eof:
        put(eof, sof, 670, y + 18, 82, 44, name='off%d' % i, font=14,
            en='OFF', vi='TẮT', on_fill=RED)
    elam, slam = clone(read=coil, sub=1)
    if elam:
        put(elam, slam, 736, y, 16, 16, name='lamp%d' % i, font=8,
            fill=LINE, on_fill=GREEN)

# ================= COT THONG SO  x 768..1012 =================
CX, CW = 768, 244
panel(CX, 132, CW, 104, name='bt')
lbl(CX + 14, 138, 180, 18, 'BEAN TEMP', 'NHIỆT ĐỘ HẠT',
    size=12, name='btl')
val(CX + 14, 158, 130, 66, 40061, size=54, gain='0.1', dot=1, name='btv')
add(text(CX + 148, 190, 24, 26, '°C', '°C', size=15, color=DIM,
         fill=CARD, name='btu'))
val(CX + 178, 162, 60, 26, 40063, size=17, color=BLUE, gain='0.1', dot=1,
    name='btr')
add(text(CX + 178, 190, 60, 16, 'RoR', 'RoR', size=11, color=DIM, fill=CARD,
         name='btrl'))

panel(CX, 242, CW, 76, name='et')
lbl(CX + 14, 246, 190, 16, 'EXHAUST TEMP', 'NHIỆT KHÍ THẢI',
    size=12, name='etl')
val(CX + 14, 264, 116, 46, 40062, size=34, color=ORANGE, gain='0.1', dot=1,
    name='etv')
add(text(CX + 134, 280, 22, 24, '°C', '°C', size=14, color=DIM,
         fill=CARD, name='etu'))
val(CX + 178, 266, 60, 24, 40064, size=16, color=ORANGE, gain='0.1', dot=1,
    name='etr')
add(text(CX + 178, 292, 60, 16, 'RoR', 'RoR', size=11, color=DIM, fill=CARD,
         name='etrl'))

# toc do trong (40085) + chenh lech ap suat (40086)
panel(CX, 324, 118, 54, name='rpm')
lbl(CX + 10, 328, 100, 15, 'DRUM rpm', 'TỐC ĐỘ TRỐNG',
    size=10, name='rpml')
val(CX + 10, 344, 100, 30, 40085, size=22, gain='0.1', dot=1, name='rpmv')
panel(CX + 126, 324, 118, 54, name='dp')
lbl(CX + 136, 328, 100, 15, 'PRESSURE Pa', 'CHÊNH ÁP (Pa)',
    size=10, name='dpl')
val(CX + 136, 344, 100, 30, 40086, size=22, color=GREEN, name='dpv')

# trong / gio / dau dot
panel(CX, 384, CW, 52, name='trio')
for i, (en, vi, reg, col) in enumerate(
        [('DRUM %', 'TRỐNG %', 40066, GREEN),
         ('AIR %', 'GIÓ %', 40065, GREEN),
         ('GAS %', 'ĐẦU ĐỐT %', 40067, RED)]):
    tx = CX + 10 + i * 78
    add(text(tx, 388, 74, 14, en, vi, size=10, color=DIM, fill=CARD,
             name='tl%d' % i))
    val(tx, 402, 74, 30, reg, size=22, color=col, name='tv%d' % i)

# ================= HANG NUT  y 444..520 =================
BTN = [('SETTINGS', 'CÀI ĐẶT', '$10'),
       ('IGNITE', 'BẬT LỬA', L + 'W40002'),
       ('FEED', 'NẠP LIỆU', L + 'W40007'),
       ('TRAY', 'MỞ CỬA KHAY', L + 'W40009'),
       ('DRUM DOOR', 'MỞ CỬA TRỐNG', L + 'W40008'),
       ('MIX+COOL', 'ĐẢO & LÀM MÁT', L + 'W40005'),
       ('PROFILE', 'HỒ SƠ', None)]
for i, (en, vi, wv) in enumerate(BTN):
    x = 12 + i * 144
    if wv:
        el, sts = clone(write=wv, sub=5)
        if el is None:
            el, sts = clone(write=wv)
        if el:
            # nen the + icon o tren + nhan chu rieng o duoi (icon nam trong
            # dinh nghia part, khong go duoc -> khong de chu de len icon)
            panel(x, 444, 136, 76, name='bbg%d' % i)
            put(el, sts, x + 2, 446, 132, 52, name='b%d' % i, font=9,
                en='', vi='')
            add(text(x + 12, 500, 112, 20, en, vi, size=13, color=INK,
                     bold=1, fill=CARD, name='blb%d' % i))
            continue
    panel(x, 444, 136, 76, name='nb%d' % i)
    add(text(x + 12, 500, 112, 20, en, vi, size=13, color=INK, bold=1,
             fill=CARD, name='nlb%d' % i))
    el, st = mk('GOTO', x + 2, 446, 132, 52, name='nav%d' % i)
    el = setk(el, 'GoToScreenID', 6)
    el = setk(el, 'GoToScreenName', 'MULTI PROFILE')
    el = setk(el, 'CloseScreen', 0)
    el = setk(el, 'BorderColor', LINE)
    st = setstr(st, 'wTextLen0', '')
    st = setstr(st, 'wTextLen1', '')
    for k, v in (('FontSize0', 9), ('FontSize1', 9), ('FontName0', 'Arial'),
                 ('FontName1', 'Arial'), ('FontColor', INK), ('FontBold', 1),
                 ('FgColor', CARD), ('BgColor', CARD), ('FgFillColor', CARD),
                 ('FgFillStopColor0', CARD), ('FgFillStopColor1', CARD),
                 ('FgFillType', 1), ('FillStyle', 1), ('BorderStyle', 0)):
        st = setk(st, k, v)
    add((el, st))

# ================= DAI DUOI  y 528..584 =================
# thoi gian rang | hen tat | chuong trinh | con lai
panel(12, 528, 242, 56, name='s1')
lbl(24, 531, 220, 15, 'ROAST TIME', 'THỜI GIAN RANG', size=11, name='s1l')
val(24, 546, 74, 34, 40068, size=28, intn=2, name='tmm')
add(text(100, 548, 12, 30, ':', ':', size=24, color=DIM, fill=CARD, name='tmc'))
val(114, 546, 74, 34, 40069, size=28, intn=2, lead=1, name='tms')

panel(264, 528, 242, 56, name='s2')
lbl(276, 531, 220, 15, 'AUTO-OFF', 'HẸN TẮT', size=11, name='s2l')
el, sts = clone(write='$M22')
if el:
    put(el, sts, 276, 546, 218, 32, name='offtimer', font=16, bold=0)

panel(516, 528, 242, 56, name='s3')
lbl(528, 531, 220, 15, 'PROGRAM No.', 'CHƯƠNG TRÌNH', size=11,
    name='s3l')
val(528, 546, 218, 32, 40016, size=26, name='prog')

panel(768, 528, 244, 56, name='s4')
lbl(780, 531, 220, 15, 'OPTIONS', 'TÙY CHỌN', size=11, name='s4l')
for i, rv in enumerate(('$0.0', '$1.0')):
    el, sts = clone(read=rv)
    if el:
        put(el, sts, 780 + i * 66, 548, 60, 30, name='opt%d' % i, font=12)
# 2 o tich con lai
for i, coil in enumerate((L + 'B17', L + 'B18')):
    el, sts = clone(write=coil, sub=16)
    if el is None:
        el, sts = clone(read=coil, sub=16)
    if el:
        put(el, sts, 916 + i * 46, 548, 40, 30, name='cb%d' % i, font=11)

print('element sinh ra:', len(E), '| tai su dung tu man cu:', len(USED))
