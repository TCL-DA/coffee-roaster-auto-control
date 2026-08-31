# -*- coding: utf-8 -*-
"""Man THU CONG nang cap - giao dien CONG NGHIEP man 10 inch.

Giu nguyen bo cuc va moi dia chi cua man cu (ID=2).
Nang cap: nen sang tuong phan cao, the trang bo goc, nut to bam duoc bang gang,
so lon ro thu bac, bo hinh tron trang tri va vien thua.
"""
import sys
sys.path.insert(0, '.')
from hmilib import *
from layout4 import harvest, BASE_F
from render_screen import g as gk

# ---------- tong mau cong nghiep: nen sang, tuong phan cao ----------
PAGE    = C('EDEFF2')
CARD    = C('FFFFFF')
LINE    = C('D8DCE2')
INK     = C('16181D')
DIM     = C('6B7280')
BLUE    = C('1187E9')      # xanh thuong hieu san co cua O Tesla
ORANGE  = C('E5670B')
GREEN   = C('1E9E52')
RED     = C('D9342B')

E = []
def add(p): E.append(p)

OLD, _, _ = harvest(BASE_F, 2)

def find(pred):
    for el, sts in OLD:
        if pred(el, sts):
            return bytes(el), [bytes(s) for s in sts]
    return None, None

def by_write(reg, width=None):
    tgt = '{Link2}1@W%d' % reg
    return find(lambda el, st: gk(el, 'WriteVar', '') == tgt
                and (width is None or gk(el, 'Width') == str(width)))

def place(el, x, y, w, h, name=None):
    for k, v in (('X', x), ('Y', y), ('Width', w), ('Height', h)):
        el = setk(el, k, v)
    if name:
        el = setstr(el, 'wDescTextLen0', name)
        el = setstr(el, 'wDescTextLen1', name)
    return el

def panel(x, y, w, h, fill=CARD, r=14, name='panel'):
    add(card(x, y, w, h, fill=fill, radius=r, name=name))

def lbl(x, y, w, h, en, vi, size=13, color=DIM, bold=1, name='l'):
    add(text(x, y, w, h, en, vi, size=size, color=color, bold=bold,
             fill=CARD, name=name))

def val(x, y, w, h, reg, size=40, color=INK, gain='1.0', intn=3, dot=0,
        lead=0, name='v'):
    el, st = num(x, y, w, h, reg, size=size, color=color, gain=gain,
                 intn=intn, dot=dot, fill=CARD, name=name)
    if lead:
        el = setk(el, 'LeadingZero', 1)
    add((el, st))

# ===================== 1) DAI MOC TREN =====================
MOCK = [('CHARGE', 'NẠP LIỆU', 40070, 40071, 40072),
        ('TP',     'TP',                40073, 40074, 40075),
        ('DE',     'DE',                40076, 40077, 40078),
        ('FCs',    'FCs',               40079, 40080, 40081),
        ('DEV',    'DEV',               40082, None,  None),
        ('DROP',   'XẢ LIỆU',  40083, None,  None)]
for i, (en, vi, rt, rm, rs) in enumerate(MOCK):
    x = 12 + i * 168
    panel(x, 8, 160, 68, name='mk%d' % i)
    lbl(x + 12, 14, 136, 18, en, vi, size=12, name='mkl%d' % i)
    val(x + 12, 32, 96, 32, rt, size=24, gain='0.1', dot=1, name='mkt%d' % i)
    if rm:
        val(x + 108, 38, 22, 22, rm, size=15, color=DIM, intn=2, name='mkm%d' % i)
        add(text(x + 130, 38, 8, 22, ':', ':', size=15, color=DIM, fill=CARD,
                 name='mkc%d' % i))
        val(x + 138, 38, 22, 22, rs, size=15, color=DIM, intn=2, lead=1,
            name='mks%d' % i)

# ===================== 2) DO THI =====================
panel(12, 84, 700, 424, name='graph_bg')
lbl(28, 94, 300, 22, 'ROASTING CURVE', 'ĐƯỜNG RANG', size=13,
    name='gl')
gel, gsts = find(lambda el, st: gk(el, 'Type') == '9')
if gel is not None:
    gel = place(gel, 24, 120, 676, 376, name='trend')
    gel = setk(gel, 'BorderColor', LINE)
    gst = setk(gsts[0], 'BgColor', CARD)
    gst = setk(gst, 'FgColor', CARD)
    gst = setk(gst, 'GridColor', LINE)
    add((gel, gst))

# ===================== 3) COT THONG SO PHAI =====================
CX, CW = 720, 292

# -- nhiet do hat: so to nhat man hinh --
panel(CX, 84, CW, 118, name='bt_bg')
lbl(CX + 16, 94, 200, 20, 'BEAN TEMP', 'NHIỆT ĐỘ HẠT',
    size=13, name='btl')
val(CX + 16, 116, 168, 74, 40061, size=64, gain='0.1', dot=1, name='btv')
add(text(CX + 188, 150, 28, 30, '°C', '°C', size=18, color=DIM,
         fill=CARD, name='btu'))
val(CX + 222, 120, 58, 30, 40063, size=22, color=BLUE, gain='0.1', dot=1,
    name='btr')
add(text(CX + 222, 152, 58, 20, 'RoR', 'RoR', size=12, color=DIM, fill=CARD,
         name='btrl'))

# -- nhiet khi thai --
panel(CX, 210, CW, 96, name='et_bg')
lbl(CX + 16, 218, 220, 20, 'EXHAUST TEMP',
    'NHIỆT KHÍ THẢI', size=13, name='etl')
val(CX + 16, 240, 150, 52, 40062, size=40, color=ORANGE, gain='0.1', dot=1,
    name='etv')
add(text(CX + 168, 256, 34, 28, '°C', '°C', size=16, color=DIM,
         fill=CARD, name='etu'))
val(CX + 206, 242, 74, 28, 40064, size=20, color=ORANGE, gain='0.1', dot=1,
    name='etr')
add(text(CX + 206, 272, 74, 18, 'RoR', 'RoR', size=12, color=DIM, fill=CARD,
         name='etrl'))

# -- thoi gian rang --
panel(CX, 314, CW, 88, name='tm_bg')
lbl(CX + 16, 322, 220, 20, 'ROAST TIME', 'THỜI GIAN RANG', size=13,
    name='tml')
val(CX + 16, 344, 84, 48, 40068, size=42, intn=2, name='tmm')
add(text(CX + 102, 348, 16, 44, ':', ':', size=36, color=DIM, fill=CARD,
         name='tmc'))
val(CX + 120, 344, 84, 48, 40069, size=42, intn=2, lead=1, name='tms')

# -- trong / gio / dau dot --
panel(CX, 410, CW, 98, name='trio_bg')
TRIO = [('DRUM · %', 'TRỐNG · %', 40066, GREEN),
        ('AIR · %',  'GIÓ · %',   40065, GREEN),
        ('GAS · %',  'ĐẦU ĐỐT · %', 40067, RED)]
for i, (en, vi, reg, col) in enumerate(TRIO):
    tx = CX + 12 + i * 94
    add(text(tx, 418, 88, 18, en, vi, size=12, color=DIM, fill=CARD,
             name='tr%d' % i))
    val(tx, 442, 88, 50, reg, size=32, color=col, name='trv%d' % i)

# ===================== 4) HANG NUT DUOI =====================
# 136x76 - du to de bam bang gang tay tren man 10 inch
BTN = [('SETTINGS', 'CÀI ĐẶT',            None,  5, 'CONFIGURATION'),
       ('IGNITE',   'BẬT LỬA',                 40002, None, None),
       ('FEED',     'NẠP LIỆU',                40007, None, None),
       ('TRAY',     'MỞ CỬA KHAY',             40009, None, None),
       ('DRUM DOOR', 'MỞ CỬA TRỐNG',      40008, None, None),
       ('MIX+COOL', 'ĐẢO & LÀM MÁT', 40005, None, None),
       ('PROFILE',  'HỒ SƠ',                   None,  6, 'MULTI PROFILE')]

for i, (en, vi, wreg, sid, sname) in enumerate(BTN):
    x = 12 + i * 144
    if wreg:
        el, sts = by_write(wreg, 50)
        if el is None:
            el, sts = by_write(wreg)
        if el is None:
            continue
        el = place(el, x, 516, 136, 76, name='btn%d' % i)
        el = setk(el, 'BorderColor', LINE)
        out = []
        for k, s in enumerate(sts):
            fillc = BLUE if k else CARD
            s = setk(s, 'FontColor', C('FFFFFF') if k else INK)
            for kk in ('FgColor', 'BgColor', 'FgFillColor', 'FgFillEndColor',
                       'FgFillStopColor0', 'FgFillStopColor1'):
                s = setk(s, kk, fillc)
            s = setk(s, 'FgFillType', 1)
            s = setk(s, 'FontBold', 1)
            s = setk(s, 'FontSize0', 15)
            s = setk(s, 'FontSize1', 15)
            s = setk(s, 'FontName0', 'Arial')
            s = setk(s, 'FontName1', 'Arial')
            s = setstr(s, 'wTextLen0', en)
            s = setstr(s, 'wTextLen1', vi)
            out.append(s)
        add((el, b''.join(out)))
    else:
        add(card(x, 516, 136, 76, fill=CARD, radius=14, name='nb%d' % i))
        el, st = mk('GOTO', x + 3, 519, 130, 70, name='nav%d' % i)
        el = setk(el, 'GoToScreenID', sid)
        el = setk(el, 'GoToScreenName', sname)
        el = setk(el, 'CloseScreen', 0)
        el = setk(el, 'BorderColor', LINE)
        st = setstr(st, 'wTextLen0', en)
        st = setstr(st, 'wTextLen1', vi)
        for k, v in (('FontSize0', 15), ('FontSize1', 15),
                     ('FontName0', 'Arial'), ('FontName1', 'Arial'),
                     ('FontColor', INK), ('FontBold', 1),
                     ('FgColor', CARD), ('BgColor', CARD),
                     ('FgFillColor', CARD), ('FgFillStopColor0', CARD),
                     ('FgFillStopColor1', CARD), ('FgFillType', 1),
                     ('FillStyle', 1), ('BorderStyle', 0)):
            st = setk(st, k, v)
        add((el, st))

print('element sinh ra:', len(E))
