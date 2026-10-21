# -*- coding: utf-8 -*-
"""Vẽ hình minh hoạ CƠ CHẾ cho case CS-01 (không phải số đo): vùng mù deadband sát nhiệt xả,
mẻ cũ đứng ở 216,5 °C, chốt cứu v3.10.0 bơm gas theo ETA và đưa mẻ về DROP.
Chạy: python docs/case-study/ve_minh_hoa_cs01.py  → docs/case-study/CS-01_minh-hoa.svg"""
import math
import os

W, H = 960, 520
L, R, T, PH = 70, 40, 96, 290
GAS_Y, GAS_H = T + PH + 34, 60
DROP, BAND = 217.0, 0.6
Y0, Y1 = 213.5, 217.6           # khung nhiệt độ phóng to quanh nhiệt xả
T_MAX = 150                     # giây hiển thị (đoạn cuối mẻ)
MAU = {'bt': '#1565C0', 'cu': '#9CA3AF', 'mau': '#57534E', 'xa': '#C62828', 'gas': '#EA580C',
       'mu': '#FEF3C7', 'chu': '#292524', 'phu': '#78716C', 'luoi': '#E7E5E4', 'vien': '#D6D3D1', 'cuu': '#16A34A'}

pw = W - L - R
X = lambda t: L + t / T_MAX * pw                                          # noqa: E731
Y = lambda v: T + PH - (v - Y0) / (Y1 - Y0) * PH                          # noqa: E731
G = lambda g: GAS_Y + GAS_H - g / 25.0 * GAS_H                            # noqa: E731


def bt_cu(t):          # mẻ cũ: RoR tụt dần, tiệm cận 216,5 — không bao giờ chạm 217,0
    return 216.5 - 2.0 * math.exp(-t / 38.0)


T_BOM = 44             # ETA > 30 s → chốt cứu bơm gas
TRE = 30               # trễ nhiệt bếp → hạt


def bt_moi(t):         # sau khi bơm + trễ nhiệt, BT lấy lại đà và chạm nhiệt xả
    if t <= T_BOM + TRE:
        return bt_cu(t)
    base = bt_cu(T_BOM + TRE)
    return min(DROP + 0.05, base + 0.0215 * (t - T_BOM - TRE) ** 1.08)


T_DROP = next(t / 2 for t in range(0, 2 * T_MAX) if bt_moi(t / 2) >= DROP)


def pl(f, t0, t1, mau, day, dash=''):
    pts = ' '.join('%.1f,%.1f' % (X(t / 2), Y(f(t / 2))) for t in range(int(2 * t0), int(2 * t1) + 1))
    return '<polyline fill="none" stroke="%s" stroke-width="%s"%s points="%s"/>' % (
        mau, day, (' stroke-dasharray="%s"' % dash) if dash else '', pts)


o = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
     'font-family="Segoe UI, Roboto, Helvetica, Arial, sans-serif">' % (W, H, W, H),
     '<rect x="0.5" y="0.5" width="%d" height="%d" rx="10" fill="#fff" stroke="%s"/>' % (W - 1, H - 1, MAU['vien']),
     '<text x="%d" y="32" font-size="18" font-weight="700" fill="%s">CS-01 · Vì sao mẻ AUTO đứng sát nhiệt xả, và chốt cứu gỡ thế nào</text>' % (L, MAU['chu']),
     '<text x="%d" y="54" font-size="12" fill="%s">Minh hoạ cơ chế — phóng to 150 giây cuối mẻ quanh nhiệt xả 217,0 °C. Không phải số đo của một mẻ cụ thể.</text>' % (L, MAU['phu'])]
# vùng mù
o.append('<rect x="%d" y="%.1f" width="%d" height="%.1f" fill="%s"/>' % (L, Y(DROP), pw, Y(DROP - BAND) - Y(DROP), MAU['mu']))
o.append('<text x="%d" y="%.1f" font-size="12" font-weight="700" fill="#92400E">VÙNG MÙ ±0,6 °C</text>' % (L + 10, Y(DROP - BAND / 2) - 2))
o.append('<text x="%d" y="%.1f" font-size="11" fill="#92400E">bộ bù gas cũ đòi lệch &gt; 0,6 °C liên tục 10 s mới bù → ở đây không bao giờ kích</text>'
         % (L + 10, Y(DROP - BAND / 2) + 13))
# lưới
v = Y0
while v <= Y1 + 1e-6:
    o.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="%s"/>' % (L, Y(v), L + pw, Y(v), MAU['luoi']))
    o.append('<text x="%d" y="%.1f" font-size="11" text-anchor="end" fill="%s">%.1f</text>' % (L - 8, Y(v) + 4, MAU['phu'], v))
    v += 0.5
for t in range(0, T_MAX + 1, 30):
    o.append('<text x="%.1f" y="%d" font-size="11" text-anchor="middle" fill="%s">+%d s</text>' % (X(t), GAS_Y + GAS_H + 18, MAU['phu'], t))
o.append('<text x="%d" y="%d" font-size="11" text-anchor="end" fill="%s">°C (BT)</text>' % (L - 8, T - 8, MAU['phu']))
o.append('<rect x="%d" y="%d" width="%d" height="%d" fill="none" stroke="%s"/>' % (L, T, pw, PH, MAU['vien']))
# nhiệt xả
o.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="%s" stroke-width="1.6" stroke-dasharray="7 5"/>' % (L, Y(DROP), L + pw, Y(DROP), MAU['xa']))
o.append('<text x="%d" y="%.1f" font-size="12" font-weight="700" text-anchor="end" fill="%s">Nhiệt xả 217,0 °C</text>' % (L + pw - 6, Y(DROP) - 6, MAU['xa']))
# đường
o.append(pl(bt_cu, 0, T_MAX, MAU['cu'], 3, '8 5'))
o.append(pl(bt_moi, 0, T_DROP, MAU['bt'], 3.2))
o.append('<text x="%.1f" y="%.1f" font-size="12" fill="%s">Trước v3.10.0: kẹt 216,5 °C, không bao giờ DROP</text>' % (X(92), Y(bt_cu(150)) + 32, '#6B7280'))
# mốc bơm + DROP
for t, ten, mau in ((T_BOM, 'ETA > 30 s → bơm +10 % gas (mã 420)', MAU['cuu']), (T_BOM + TRE, 'trễ nhiệt bếp→hạt ~30 s', MAU['phu'])):
    o.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="%s" stroke-dasharray="4 4"/>' % (X(t), T, X(t), GAS_Y + GAS_H, mau))
o.append('<text x="%.1f" y="%d" font-size="12" font-weight="700" fill="%s">%s</text>' % (X(T_BOM) + 6, T + 18, MAU['cuu'], 'ETA > 30 s → bơm gas (mã 420)'))
o.append('<text x="%.1f" y="%d" font-size="11" fill="%s">%s</text>' % (X(T_BOM + TRE) + 6, T + 36, MAU['phu'], 'trễ nhiệt bếp → hạt ~30 s'))
o.append('<circle cx="%.1f" cy="%.1f" r="6" fill="%s" stroke="#fff" stroke-width="2"/>' % (X(T_DROP), Y(DROP), MAU['bt']))
o.append('<text x="%.1f" y="%.1f" font-size="12" font-weight="700" fill="%s">Từ v3.10.0: tự DROP ở +%d s</text>' % (X(T_DROP) + 12, Y(DROP) + 20, MAU['bt'], T_DROP))
# dải gas
o.append('<text x="%d" y="%d" font-size="12" font-weight="700" fill="%s">Gas %%</text>' % (L, GAS_Y - 8, MAU['gas']))
o.append('<rect x="%d" y="%d" width="%d" height="%d" fill="#FFF7ED" stroke="%s"/>' % (L, GAS_Y, pw, GAS_H, MAU['vien']))
gas_cu = lambda t: max(0.0, 5 - t / 12)                                     # noqa: E731 — hồ sơ vuốt gas về 0
gas_moi = lambda t: gas_cu(t) if t < T_BOM else max(gas_cu(t), 10)        # noqa: E731 — max(), không cộng dồn
for f, mau, dd, dash in ((gas_cu, MAU['cu'], 2.4, '8 5'), (gas_moi, MAU['gas'], 2.4, '')):
    pts = ' '.join('%.1f,%.1f' % (X(t / 2), G(f(t / 2))) for t in range(0, 2 * int(T_DROP) + 1))
    if f is gas_cu:
        pts = ' '.join('%.1f,%.1f' % (X(t / 2), G(f(t / 2))) for t in range(0, 2 * T_MAX + 1))
    o.append('<polyline fill="none" stroke="%s" stroke-width="%s"%s points="%s"/>' % (mau, dd, (' stroke-dasharray="%s"' % dash) if dash else '', pts))
o.append('<text x="%.1f" y="%.1f" font-size="11" fill="%s">hồ sơ vuốt gas về 0 %% → bộ bù cũ đứng im</text>' % (X(64), G(0) - 4, '#6B7280'))
o.append('<text x="%.1f" y="%.1f" font-size="11" fill="%s">chốt cứu nâng lên 10 %%</text>' % (X(T_BOM) + 6, G(10) - 4, MAU['gas']))
o.append('</svg>')
ra = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'CS-01_minh-hoa.svg')
open(ra, 'w', encoding='utf-8').write('\n'.join(o))
print('ok', ra, 'DROP tai +%ds' % T_DROP)
