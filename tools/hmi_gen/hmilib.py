# -*- coding: utf-8 -*-
"""Sinh man hinh RANG kieu iOS cho HMI Delta DOP-110CS (1024x600).
Khong sua man hinh cu - them mot man moi ID=20."""
import zlib, struct, re, os, pickle, sys

TBL = bytes(b ^ 0x64 for b in range(256))
BASE = r'F:\HMI\3XILANH_NOLOADCELL\HMI_3XILANH_NOLOADCELL_23_02_2020\Thanh\10_2025\17_CMS_2026\CMS_06_012026 - Copy.dpa'
OUT  = r'C:\Users\truon\Desktop\GATE_DIASCREEN\HMI_OTL_RANG_iOS.dpa'

# ---------- vo file ----------
def decode(raw):
    off = raw.find(b'\x1f\x8b\x08', 40000)
    return raw[:off], zlib.decompressobj(31).decompress(raw[off:]).translate(TBL)

def encode(head, ini):
    x = ini.translate(TBL)
    co = zlib.compressobj(6, zlib.DEFLATED, -15)
    return (head + b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x0b'
            + co.compress(x) + co.flush()
            + struct.pack('<II', zlib.crc32(x) & 0xffffffff, len(x) & 0xffffffff))

# ---------- mau: COLORREF kieu Win32 = R | G<<8 | B<<16 ----------
def C(h):
    h = h.lstrip('#'); r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
    return r | (g << 8) | (b << 16)

BG      = C('000000')   # nen den
CARD    = C('1C1C1E')   # the
CARD_HI = C('2C2C2E')   # the noi
WHITE   = C('FFFFFF')
GREY    = C('8E8E93')   # chu phu
BLUE    = C('0A84FF')
GREEN   = C('30D158')
ORANGE  = C('FF9F0A')
RED     = C('FF453A')

# ---------- vá field ----------
def setk(blk, key, val):
    """Dat key=val trong khoi INI (them vao cuoi neu chua co)."""
    pat = (r'\r\n' + re.escape(key) + r'=[^\r\n]*\r\n').encode()
    rep = ('\r\n%s=%s\r\n' % (key, val)).encode()
    new, n = re.subn(pat, rep, blk, count=1)
    if n == 0:
        new = blk.rstrip(b'\r\n') + b'\r\n' + ('%s=%s' % (key, val)).encode() + b'\r\n'
    return new

def setstr(blk, lenkey, s):
    """Dat chuoi UTF-16LE + o do dai di kem (wTextLen0 / wDescTextLen0 ...)."""
    b = s.encode('utf-16le') + b'\x00\x00'
    pat = (r'\r\n' + re.escape(lenkey) + r'=\d+\r\n').encode() + rb'(?:(?!\r\n)[\s\S])*\r\n'
    rep = ('\r\n%s=%d\r\n' % (lenkey, len(b))).encode() + b + b'\r\n'
    new, n = re.subn(pat, rep, blk, count=1)
    if n == 0:
        raise SystemExit('khong thay o do dai ' + lenkey)
    return new

T = pickle.load(open('tmpl.pkl','rb'))

def mk(kind, x, y, w, h, *, name='obj', vis=None):
    el, st = T[kind]
    el = bytes(el); st = bytes(st)
    for k, v in (('X',x), ('Y',y), ('Width',w), ('Height',h)):
        el = setk(el, k, v)
    el = setstr(el, 'wDescTextLen0', name)
    el = setstr(el, 'wDescTextLen1', name)
    if vis is not None:
        el = setk(el, 'VisibleLink', 1)
        el = setk(el, 'VisibleVar', '{Link2}1@W%d' % vis)
        el = setk(el, 'VisibleCondition', 1)
    return el, st

def card(x, y, w, h, fill=CARD, radius=22, vis=None, name='card'):
    el, st = mk('RECT', x, y, w, h, name=name, vis=vis)
    el = setk(el, 'RoundRadius', radius)
    for k in ('RoundRadiusLTVar','RoundRadiusRTVar','RoundRadiusLBVar','RoundRadiusRBVar'):
        el = setk(el, k, radius)
    el = setk(el, 'EnableCustomRadius', 1); el = setk(el, 'ShowBorder', 0)
    el = setk(el, 'BorderColor', fill)
    st = setk(st, 'FgFillType', 1)
    for k in ('FgColor','BgColor','FgFillColor','FgFillEndColor',
              'FgFillStopColor0','FgFillStopColor1'):
        st = setk(st, k, fill)
    st = setk(st, 'FillStyle', 1); st = setk(st, 'BorderStyle', 0)
    return el, st

def text(x, y, w, h, s, sv=None, *, size=16, color=WHITE, bold=0, align=33,
         fill=CARD, vis=None, name='text'):
    el, st = mk('TEXT', x, y, w, h, name=name, vis=vis)
    st = setstr(st, 'wTextLen0', s)
    st = setstr(st, 'wTextLen1', sv if sv is not None else s)
    for k, v in (('FontSize0',size), ('FontSize1',size),
                 ('FontName0','Arial'), ('FontName1','Arial'),
                 ('FontColor',color), ('FontBold',bold), ('FontAlign',align)):
        st = setk(st, k, v)
    st = setk(st, 'FgFillType', 1)
    for k in ('FgColor','BgColor','FgFillColor','FgFillStopColor0','FgFillStopColor1'):
        st = setk(st, k, fill)
    st = setk(st, 'FillStyle', 1); st = setk(st, 'BorderStyle', 0)
    el = setk(el, 'BorderColor', fill); el = setk(el, 'ShowBorder', 0)
    return el, st

def num(x, y, w, h, reg, *, size=44, color=WHITE, intn=3, dot=0, gain='1.0',
        fill=CARD, align=34, vis=None, name='num'):
    el, st = mk('NUMERIC', x, y, w, h, name=name, vis=vis)
    el = setk(el, 'ReadVar', '{Link2}1@W%d' % reg)
    el = setk(el, 'ReadMemType', 3); el = setk(el, 'ReadLink', 1)
    el = setk(el, 'IntNum', intn); el = setk(el, 'DotNum', dot)
    el = setk(el, 'GainValue', gain); el = setk(el, 'LeadingZero', 0)
    for k, v in (('FontSize0',size), ('FontSize1',size),
                 ('FontName0','Arial'), ('FontName1','Arial'),
                 ('FontColor',color), ('FontBold',0), ('FontAlign',align)):
        st = setk(st, k, v)
    st = setk(st, 'FgFillType', 1)
    for k in ('FgColor','BgColor','FgFillColor','FgFillStopColor0','FgFillStopColor1'):
        st = setk(st, k, fill)
    st = setk(st, 'FillStyle', 1); st = setk(st, 'BorderStyle', 0)
    return el, st
