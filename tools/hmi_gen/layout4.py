# -*- coding: utf-8 -*-
"""Nang cap man THU CONG: giu nguyen bo cuc + moi dia chi, chi thay lop ao.
Nhan ban toan bo man ID=2 -> man ID=21, roi son lai theo tong den cao cap."""
import sys, re, zlib
sys.path.insert(0,'.')
from hmilib import *
from render_screen import load, sections, g as gk, gs

BASE_F = BASE

# ---- tong mau ----
INK       = C('FFFFFF')   # chu chinh
INK_DIM   = C('9A9AA0')   # chu phu
CARD_BG   = C('1C1C1E')
CARD_BG2  = C('26262A')
PANEL     = C('000000')
ACC_BLUE  = C('0A84FF')
ACC_ORANGE= C('FF9F0A')
ACC_GREEN = C('30D158')
ACC_RED   = C('FF453A')
BTN_BG    = C('2C2C2E')

# mau chu theo thanh ghi (giu dung y nghia mau cua man cu)
REG_COLOR = {
    '40061': INK,        '40063': ACC_BLUE,    # BT + RoR BT
    '40062': ACC_ORANGE, '40064': ACC_ORANGE,  # ET + RoR ET
    '40065': ACC_GREEN,  '40066': ACC_GREEN,   # gio / trong
    '40067': ACC_RED,                          # gas
    '40086': ACC_GREEN,
}

def harvest(path, sid):
    """Lay (element, [state...]) cua 1 man hinh - GIU DU moi khoi State."""
    ini = load(path); bnd = sections(ini)
    hit = [i for i,b in enumerate(bnd) if b[2]=='Screen'
           and re.search((r'\r\nID=%s\r\n'%sid).encode(), ini[b[0]:b[1]])][0]
    i = hit+1; out=[]
    while i < len(bnd) and bnd[i][2] in ('Element','State','AuxKeyElement'):
        if bnd[i][2]=='Element':
            el = ini[bnd[i][0]:bnd[i][1]]; sts=[]; j=i+1
            while j < len(bnd) and bnd[j][2]=='State':
                sts.append(ini[bnd[j][0]:bnd[j][1]]); j+=1
            out.append((el, sts)); i=j
        else: i+=1
    return out, ini[bnd[hit][0]:bnd[hit][1]], ini

def restyle(el, sts):
    """Son lai 1 doi tuong theo tong den, giu nguyen dia chi/vi tri/chuc nang."""
    t, sub = gk(el,'Type'), gk(el,'SubType')
    reg_m = re.search(r'W(\d+)', gk(el,'ReadVar','') or '')
    reg = reg_m.group(1) if reg_m else None
    new_sts = []
    for st in sts:
        st = bytes(st)
        if t=='10' and sub=='6':                    # CHU
            st = setk(st,'FontColor', INK_DIM)
            for k in ('FgColor','BgColor','FgFillColor','FgFillStopColor0','FgFillStopColor1'):
                st = setk(st,k,CARD_BG)
            st = setk(st,'FgFillType',1); st = setk(st,'BorderStyle',0)
        elif t=='5':                                 # SO
            st = setk(st,'FontColor', REG_COLOR.get(reg, INK))
            for k in ('FgColor','BgColor','FgFillColor','FgFillStopColor0','FgFillStopColor1'):
                st = setk(st,k,CARD_BG)
            st = setk(st,'FgFillType',1); st = setk(st,'BorderStyle',0)
        elif t=='10' and sub=='2':                   # HINH CHU NHAT -> the
            for k in ('FgColor','BgColor','FgFillColor','FgFillEndColor',
                      'FgFillStopColor0','FgFillStopColor1'):
                st = setk(st,k,CARD_BG2)
            st = setk(st,'FgFillType',1); st = setk(st,'FontColor',INK_DIM)
        elif t=='10' and sub=='3':                   # HINH TRON -> cham trang thai
            for k in ('FgColor','BgColor','FgFillColor','FgFillStopColor0','FgFillStopColor1'):
                st = setk(st,k,ACC_ORANGE)
            st = setk(st,'FgFillType',1)
        elif t in ('1','2','6'):                     # NUT / DEN / O NHAP
            val = gk(st,'Value','0')
            on  = (val not in ('0','')) 
            bgc = ACC_BLUE if (t=='1' and sub=='5' and on) else BTN_BG
            for k in ('FgColor','BgColor','FgFillColor','FgFillEndColor',
                      'FgFillStopColor0','FgFillStopColor1'):
                st = setk(st,k,bgc)
            st = setk(st,'FgFillType',1)
            st = setk(st,'FontColor', INK)
            st = setk(st,'FontBold',1)
        new_sts.append(st)
    el = bytes(el)
    if t=='10' and sub=='2':
        el = setk(el,'RoundRadius',16)
        for k in ('RoundRadiusLTVar','RoundRadiusRTVar','RoundRadiusLBVar','RoundRadiusRBVar'):
            el = setk(el,k,16)
        el = setk(el,'EnableCustomRadius',1); el = setk(el,'ShowBorder',0)
        el = setk(el,'BorderColor',CARD_BG2)
    if t in ('1','2','6'):
        el = setk(el,'BorderColor',BTN_BG)
    return el, new_sts

# ---------------- dung man moi ----------------
items, scr_old, ini = harvest(BASE_F, 2)
print('nhan ban tu man ID=2:', len(items), 'doi tuong,',
      sum(len(s) for _,s in items), 'khoi State')

E = []
# 1) cac the nen dat TRUOC (nam duoi cung)
ZONES = [
    (10,   6, 1004,  56),   # dai moc tren
    (10,  70,  822, 432),   # vung do thi
    (840,  70, 174, 432),   # cot thong so phai
    (10, 512, 1004,  80),   # hang nut duoi
]
for i,(x,y,w,h) in enumerate(ZONES):
    E.append(card(x, y, w, h, fill=CARD_BG, radius=18, name='zone%d'%i))

# 2) toan bo doi tuong cu, da son lai
for el, sts in items:
    el2, sts2 = restyle(el, sts)
    E.append((el2, b''.join(sts2)))

print('tong khoi ghi ra:', len(E))
