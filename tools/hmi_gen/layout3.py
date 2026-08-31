# -*- coding: utf-8 -*-
"""Man hinh RANG kieu iOS - ban 3 (cuoi): can doi chieu cao + thanh dieu huong."""
import sys
sys.path.insert(0, '.')
from hmilib import *

CAP_MAGIC, CAP_VER    = 40126, 40127
CAP_AIRFLOW, CAP_GAS  = 40128, 40129
CAP_DRUM, CAP_VACUUM  = 40130, 40131
CAP_AIRINV, CAP_SCALE = 40132, 40133
CAP_IORLY, CAP_BT     = 40134, 40135
CAP_ET, CAP_PREMIX    = 40136, 40137
CAP_VACDRUM, CAP_VRHMI, CAP_BATCH = 40138, 40139, 40140

E = []
def add(p): E.append(p)

def tile(x, y, w, h, en, vi, reg, *, size=36, gain='1.0', intn=3, dot=0,
         color=WHITE, vis=None, tag='t', lead=0):
    add(card(x, y, w, h, vis=vis, name=tag+'_bg'))
    add(text(x+22, y+16, w-44, 22, en, vi, size=13, color=GREY, bold=1,
             vis=vis, name=tag+'_lb'))
    el, st = num(x+22, y+50, w-44, h-70, reg, size=size, color=color,
                 intn=intn, dot=dot, gain=gain, vis=vis, name=tag+'_v')
    if lead: el = setk(el, 'LeadingZero', 1)
    add((el, st))

def navbtn(x, y, w, h, en, vi, sid, sname, tag='nav'):
    add(card(x, y, w, h, fill=CARD_HI, radius=14, name=tag+'_bg'))
    el, st = mk('GOTO', x+2, y+2, w-4, h-4, name=tag+'_btn')
    el = setk(el, 'GoToScreenID', sid)
    el = setk(el, 'GoToScreenName', sname)
    el = setk(el, 'CloseScreen', 0)
    st = setstr(st, 'wTextLen0', en); st = setstr(st, 'wTextLen1', vi)
    for k, v in (('FontSize0',14), ('FontSize1',14), ('FontName0','Arial'),
                 ('FontName1','Arial'), ('FontColor',WHITE), ('FontBold',1),
                 ('FgColor',CARD_HI), ('BgColor',CARD_HI), ('FgFillColor',CARD_HI),
                 ('FgFillStopColor0',CARD_HI), ('FgFillStopColor1',CARD_HI),
                 ('FgFillType',1), ('FillStyle',1), ('BorderStyle',0)):
        st = setk(st, k, v)
    add((el, st))

# ---------- thanh tren (0..56) ----------
add(text(24, 12, 190, 32, 'O TESLA', 'O TESLA', size=19, bold=1, color=BLUE,
         fill=BG, name='brand'))
add(text(168, 15, 300, 28, 'ROASTING', 'RANG C\u00c0 PH\u00ca', size=15,
         color=GREY, fill=BG, name='subtitle'))
add(card(690, 22, 16, 16, fill=ORANGE, radius=8, vis=40060, name='firedot'))
add(text(714, 15, 90, 28, 'FLAME', 'L\u1eecA', size=14, color=GREY, fill=BG, name='firelb'))
add(text(812, 15, 80, 28, 'BATCH', 'M\u1eba', size=13, color=GREY, fill=BG, name='batchlb'))
add(num(876, 12, 76, 32, CAP_BATCH, size=19, intn=3, fill=BG, name='batchv'))
add(text(956, 15, 44, 28, 'kg', 'kg', size=15, color=GREY, fill=BG, name='batchu'))

# ---------- hang chinh (68..238) ----------
tile(24, 68, 480, 170, 'BEAN TEMP  \u00b7  \u00b0C', 'NHI\u1ec6T H\u1ea0T  \u00b7  \u00b0C',
     40061, size=76, gain='0.1', dot=1, tag='bt')
tile(520, 68, 232, 170, 'ENV TEMP  \u00b7  \u00b0C', 'NHI\u1ec6T GI\u00d3  \u00b7  \u00b0C',
     40062, size=46, gain='0.1', dot=1, color=ORANGE, tag='et')
tile(768, 68, 232, 170, 'RATE  \u00b7  \u00b0/min', 'T\u1ed0C \u0110\u1ed8 T\u0102NG \u00b7 \u00b0/ph',
     40063, size=46, gain='0.1', dot=1, color=BLUE, tag='ror')

# ---------- hang 2 (250..380) ----------
tile(24,  250, 232, 130, 'GAS  \u00b7  %',      'GAS  \u00b7  %',       40067, vis=CAP_GAS, tag='gas')
tile(272, 250, 232, 130, 'AIRFLOW  \u00b7  %',  'GI\u00d3  \u00b7  %',   40065, vis=CAP_AIRFLOW, tag='air')
tile(520, 250, 232, 130, 'DRUM  \u00b7  %',     'L\u1ed2NG RANG \u00b7 %',40066, vis=CAP_DRUM, tag='drum')
tile(768, 250, 232, 130, 'VACUUM  \u00b7  Pa',  '\u00c1P H\u00daT \u00b7 Pa',40086, color=GREEN, vis=CAP_VACUUM, tag='vac')

# ---------- hang 3 (392..522) ----------
add(card(24, 392, 480, 130, name='tm_bg'))
add(text(46, 408, 300, 22, 'ELAPSED  \u00b7  min : s',
         'TH\u1edcI GIAN  \u00b7  ph\u00fat : gi\u00e2y', size=13, color=GREY, bold=1, name='tm_lb'))
add(num(46, 442, 96, 62, 40068, size=48, intn=2, name='tm_min'))
add(text(148, 446, 22, 56, ':', ':', size=42, color=GREY, name='tm_sep'))
elm, stm = num(174, 442, 96, 62, 40069, size=48, intn=2, name='tm_sec')
add((setk(elm, 'LeadingZero', 1), stm))
tile(520, 392, 232, 130, 'WEIGHT  \u00b7  kg', 'C\u00c2N  \u00b7  kg', 40084,
     size=38, gain='0.1', dot=1, vis=CAP_SCALE, tag='wei')
tile(768, 392, 232, 130, 'CHARGE  \u00b7  \u00b0C', 'NHI\u1ec6T N\u1ea0P \u00b7 \u00b0C', 40082,
     size=38, gain='0.1', dot=1, tag='chg')

# ---------- thanh dieu huong (534..580) ----------
navbtn(24,  534, 232, 46, 'MANUAL', 'TH\u1ee6 C\u00d4NG',   2,  'PROGRAM MANUAL', 'n1')
navbtn(272, 534, 232, 46, 'AUTO',   'T\u1ef0 \u0110\u1ed8NG', 3,  'PROGRAM AUTO',   'n2')
navbtn(520, 534, 232, 46, 'SETTINGS','C\u00c0I \u0110\u1eb6T',  5,  'CONFIGURATION',  'n3')
navbtn(768, 534, 232, 46, 'HISTORY','L\u1ecaCH S\u1eec',    10, 'History',        'n4')

print('element sinh ra:', len(E))
