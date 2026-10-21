# -*- coding: utf-8 -*-
"""Vẽ giản đồ rang SVG cho mọi profile Artisan (.alog) trong profiles/artisan + trang xem theo thư mục.

GitHub hiển thị SVG ngay trong trang, nên mở repo là xem được đường rang, không cần cài Artisan.
SVG tự viết (không matplotlib): lấy mẫu 2 s, ~20 KB / tệp.

Chạy lại mỗi khi thêm profile:
    python tools/ve_gian_do_alog.py
Sinh ra:
    profiles/artisan/_do-thi/<đường dẫn profile>.svg   — một giản đồ cho mỗi .alog
    profiles/artisan/<thư mục>/XEM-GIAN-DO.md            — trang xem cả thư mục (ảnh + số liệu mốc)
"""
import ast
import os
import sys
from html import escape

GOC = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'profiles', 'artisan'))
DO_THI = os.path.join(GOC, '_do-thi')
TRANG = 'XEM-GIAN-DO.md'

W = 960                            # rộng khung SVG
L, R = 64, 70                      # lề trái / phải vùng vẽ
T = 128                            # đỉnh vùng vẽ — phía trên: tiêu đề + dải nhãn mốc 2 hàng
PH = 300                           # cao vùng vẽ
GAS_H = 34                         # cao dải gas dưới đồ thị (chỉ khi profile có kênh gas)
BUOC_GIAY = 2                      # lấy mẫu
ROR_SPAN = 30                      # giây cửa sổ hồi quy RoR (giống Artisan Delta Span 30 s)

MAU = {'bt': '#1565C0', 'et': '#C62828', 'ror': '#7C3AED', 'gas': '#EA580C',
       'luoi': '#E7E5E4', 'chu': '#292524', 'phu': '#78716C', 'nen': '#FFFFFF', 'vien': '#D6D3D1'}
MOC = [(0, 'CHARGE'), (1, 'DRY'), (2, 'FCs'), (6, 'DROP')]   # chỉ số trong timeindex của Artisan


def doc(duong_dan):
    try:
        return ast.literal_eval(open(duong_dan, encoding='utf-8', errors='replace').read())
    except Exception:  # noqa: BLE001 — tệp hỏng: bỏ qua, trang xem sẽ ghi "không đọc được"
        return None


def mmss(s):
    s = max(0, int(round(s)))
    return '%d:%02d' % (s // 60, s % 60)


def rong_chu(s, co=12):
    """Ước lượng bề rộng chữ (px) để căn nhãn không đè nhau."""
    return len(s) * co * 0.56


def ror_hoi_quy(ts, vs, span=ROR_SPAN):
    """RoR °C/phút = độ dốc hồi quy tuyến tính trên cửa sổ span giây (mượt như Artisan)."""
    ra, j = [], 0
    for i, t in enumerate(ts):
        while ts[j] < t - span:
            j += 1
        n = i - j + 1
        if n < 5:
            ra.append(None)
            continue
        xs, ys = ts[j:i + 1], vs[j:i + 1]
        mx, my = sum(xs) / n, sum(ys) / n
        sxx = sum((x - mx) ** 2 for x in xs)
        ra.append(None if sxx == 0 else 60.0 * sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx)
    return ra


def chuoi_gas(d):
    for k in ('extraname1', 'extraname2'):
        for i, ten in enumerate(d.get(k, []) or []):
            if 'gas' in str(ten).lower():
                src = d.get('extratemp1' if k == 'extraname1' else 'extratemp2', [])
                if i < len(src):
                    return src[i]
    return None


def ve(d, tieu_de, phu_de):
    tx = d.get('timex') or []
    bt, et = d.get('temp2') or [], d.get('temp1') or []
    n = min(len(tx), len(bt), len(et))
    if n < 10:
        return None, None
    ti = list(d.get('timeindex') or [-1, 0, 0, 0, 0, 0, 0, 0]) + [0] * 8
    co_charge = ti[0] is not None and ti[0] >= 0
    i0 = ti[0] if co_charge else 0
    co_drop = bool(ti[6]) and ti[6] > i0
    nhip = max(1e-3, (tx[n - 1] - tx[0]) / max(1, n - 1))
    i_het = min(n - 1, (ti[6] if co_drop else n - 1) + int(60 / nhip))        # 1 phút sau DROP
    t0 = tx[i0]
    gas = chuoi_gas(d)

    idx, moc_t = [], -1e9                                                     # lấy mẫu 2 s
    for i in range(max(0, i0 - int(30 / nhip)), i_het + 1):
        if tx[i] - moc_t >= BUOC_GIAY:
            idx.append(i)
            moc_t = tx[i]
    ts = [tx[i] - t0 for i in idx]
    b = [bt[i] if bt[i] not in (None, -1) else None for i in idx]
    e = [et[i] if et[i] not in (None, -1) else None for i in idx]
    tmin, tmax = min(ts), max(ts)
    if tmax - tmin < 30:
        return None, None

    # RoR chỉ trong khoảng có nghĩa: từ TP (hoặc 45 s sau nạp) tới DROP — như Artisan
    cp = d.get('computed', {}) or {}
    t_tp = cp.get('TP_time') or 45
    t_drop = (tx[ti[6]] - t0) if co_drop else tmax
    hop = [(t, v) for t, v in zip(ts, b) if v is not None and v > 0]
    ror_all = ror_hoi_quy([t for t, _ in hop], [v for _, v in hop]) if len(hop) > 5 else []
    ror = [(t, r) for (t, _), r in zip(hop, ror_all) if r is not None and t_tp + 10 <= t <= t_drop]
    rmax = max([r for _, r in ror] + [10])
    ror_tran = min(50, max(20, int(rmax / 10 + 1) * 10))

    vmax = max([v for v in b + e if v is not None and v < 600] + [100])
    ymax = min(400, max(250, int(vmax / 50 + 1) * 50))
    pw = W - L - R
    day = T + PH
    y_gas = day + 10
    y_truc = (y_gas + GAS_H if gas else day) + 18
    H = y_truc + 16
    X = lambda t: L + (t - tmin) / (tmax - tmin) * pw                         # noqa: E731
    Y = lambda v: day - max(0, min(ymax, v)) / ymax * PH                       # noqa: E731
    Y2 = lambda r: day - max(0, min(ror_tran, r)) / ror_tran * PH              # noqa: E731

    o = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
         'font-family="Segoe UI, Roboto, Helvetica, Arial, sans-serif">' % (W, H, W, H)]
    o.append('<rect x="0.5" y="0.5" width="%d" height="%d" rx="10" fill="%s" stroke="%s"/>'
             % (W - 1, H - 1, MAU['nen'], MAU['vien']))
    o.append('<text x="%d" y="30" font-size="17" font-weight="700" fill="%s">%s</text>' % (L, MAU['chu'], escape(tieu_de)))
    o.append('<text x="%d" y="50" font-size="12" fill="%s">%s</text>' % (L, MAU['phu'], escape(phu_de)))

    # chú giải — căn phải, đo bề rộng chữ để không đè nhau
    muc = [('BT hạt', MAU['bt'], 3), ('ET khí', MAU['et'], 2), ('RoR °C/phút', MAU['ror'], 1.6)]
    if gas:
        muc.append(('Gas %', MAU['gas'], 2))
    gx = W - R - sum(26 + rong_chu(m[0]) + 14 for m in muc)
    for ten, mau, dd in muc:
        o.append('<line x1="%.0f" y1="26" x2="%.0f" y2="26" stroke="%s" stroke-width="%s" stroke-linecap="round"/>'
                 % (gx, gx + 18, mau, dd))
        o.append('<text x="%.0f" y="30" font-size="12" fill="%s">%s</text>' % (gx + 24, MAU['chu'], ten))
        gx += 26 + rong_chu(ten) + 14

    # lưới + trục
    for v in range(0, ymax + 1, 50):
        o.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="%s"/>' % (L, Y(v), L + pw, Y(v), MAU['luoi']))
        o.append('<text x="%d" y="%.1f" font-size="11" text-anchor="end" fill="%s">%d</text>' % (L - 8, Y(v) + 4, MAU['phu'], v))
    for r in range(0, ror_tran + 1, 10):
        o.append('<text x="%d" y="%.1f" font-size="11" fill="%s">%d</text>' % (L + pw + 8, Y2(r) + 4, MAU['ror'], r))
    o.append('<text x="%d" y="%d" font-size="11" text-anchor="end" fill="%s">°C</text>' % (L - 8, T - 6, MAU['phu']))
    o.append('<text x="%d" y="%d" font-size="11" fill="%s">°C/ph</text>' % (L + pw + 6, T - 6, MAU['ror']))
    buoc = 60 if tmax - tmin <= 1200 else 120
    t = (int(tmin // buoc) + (1 if tmin > 0 else 0)) * buoc
    while t <= tmax:
        o.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="%s"/>' % (X(t), T, X(t), day, MAU['luoi']))
        if X(t) < L + pw - 40:                                               # chừa chỗ chữ "phút"
            o.append('<text x="%.1f" y="%d" font-size="11" text-anchor="middle" fill="%s">%d</text>'
                     % (X(t), y_truc, MAU['phu'], t // 60))
        t += buoc
    o.append('<text x="%d" y="%d" font-size="11" text-anchor="end" fill="%s">phút</text>' % (L + pw, y_truc, MAU['phu']))
    o.append('<rect x="%d" y="%d" width="%d" height="%d" fill="none" stroke="%s"/>' % (L, T, pw, PH, MAU['vien']))

    def duong(xs, ys, mau, dd, toi=None):
        pts, doan = [], []
        for x, y in zip(xs, ys):
            if y is None:
                if len(pts) > 1:
                    doan.append(pts)
                pts = []
                continue
            pts.append('%.1f,%.1f' % (x, y))
        if len(pts) > 1:
            doan.append(pts)
        for pp in doan:
            o.append('<polyline fill="none" stroke="%s" stroke-width="%s" stroke-linejoin="round"%s points="%s"/>'
                     % (mau, dd, (' stroke-opacity="%s"' % toi) if toi else '', ' '.join(pp)))

    if gas:
        o.append('<rect x="%d" y="%d" width="%d" height="%d" fill="#FFF7ED" stroke="%s"/>' % (L, y_gas, pw, GAS_H, MAU['vien']))
        o.append('<text x="%d" y="%.0f" font-size="10" text-anchor="end" fill="%s">gas</text>'
                 % (L - 8, y_gas + GAS_H / 2 + 4, MAU['gas']))
        gv = [gas[i] if i < len(gas) and gas[i] not in (None, -1) else None for i in idx]
        duong([X(t) for t in ts], [None if v is None else y_gas + GAS_H - max(0, min(100, v)) / 100 * GAS_H for v in gv],
              MAU['gas'], 1.6)
    duong([X(t) for t in ts], [None if v is None else Y(v) for v in e], MAU['et'], 2)
    duong([X(t) for t, _ in ror], [Y2(r) for _, r in ror], MAU['ror'], 1.6, 0.9)
    duong([X(t) for t in ts], [None if v is None else Y(v) for v in b], MAU['bt'], 3)

    # mốc — nhãn nằm trong dải RIÊNG phía trên vùng vẽ (2 hàng xen kẽ), không đè đường cong
    moc = []
    if co_charge:
        moc.append(('CHARGE', 0, bt[i0]))
    if cp.get('TP_time'):
        moc.append(('TP', cp['TP_time'], cp.get('TP_BT', 0)))
    for k, ten in MOC[1:]:
        if ti[k] and 0 < ti[k] < n:
            moc.append((ten, tx[ti[k]] - t0, bt[ti[k]]))
    phai_hang = [-1e9, -1e9]
    for ten, t, v in moc:
        if t < tmin or t > tmax:
            continue
        x = X(t)
        chu2 = '%s · %.1f°C' % (mmss(t), v)
        w = max(rong_chu(ten, 12), rong_chu(chu2, 11)) + 8
        ax = 'start' if x + w < W - 8 else 'end'
        trai, phai = (x, x + w) if ax == 'start' else (x - w, x)
        hang = 0 if trai > phai_hang[0] else 1
        phai_hang[hang] = phai
        ty = 74 + hang * 28
        dx = 5 if ax == 'start' else -5
        o.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="%s" stroke-dasharray="4 4"/>' % (x, ty + 12, x, day, MAU['phu']))
        o.append('<circle cx="%.1f" cy="%.1f" r="4.5" fill="%s" stroke="#fff" stroke-width="1.5"/>' % (x, Y(v), MAU['bt']))
        o.append('<text x="%.1f" y="%d" font-size="12" font-weight="700" text-anchor="%s" fill="%s">%s</text>'
                 % (x + dx, ty - 4, ax, MAU['chu'], ten))
        o.append('<text x="%.1f" y="%d" font-size="11" text-anchor="%s" fill="%s">%s</text>'
                 % (x + dx, ty + 10, ax, MAU['phu'], chu2))
    o.append('</svg>')

    tom = {'moc': {ten: (mmss(t), '%.1f' % v) for ten, t, v in moc}}
    if co_drop:
        tong = tx[ti[6]] - t0
        tom['tong'] = mmss(tong)
        if ti[2] and ti[2] > i0:
            tom['dtr'] = '%.1f %%' % (100.0 * (tx[ti[6]] - tx[ti[2]]) / tong)
    return '\n'.join(o), tom


def phu_de_cua(d):
    w = d.get('weight') or [0, 0, 'g']
    bits = []
    if d.get('roastisodate'):
        bits.append('%s %s' % (d['roastisodate'], (d.get('roasttime') or '')[:5]))
    if d.get('beans'):
        bits.append(str(d['beans']).replace('\n', ' ')[:60])
    if w and w[0]:
        dv = w[2] if len(w) > 2 else ''
        bits.append('%g %s' % (w[0], dv) + ((' → %g %s' % (w[1], dv)) if len(w) > 1 and w[1] else ''))
    if d.get('machinesetup'):
        bits.append(str(d['machinesetup']))
    return '  ·  '.join(bits)


def main():
    nhom = {}
    for goc, ds, fs in os.walk(GOC):
        ds[:] = sorted(x for x in ds if x != '_do-thi')
        for f in sorted(fs):
            if f.lower().endswith('.alog'):
                rel = os.path.relpath(os.path.join(goc, f), GOC).replace(os.sep, '/')
                nhom.setdefault(rel.split('/')[0] if '/' in rel else '.', []).append(rel)
    dem = 0
    for thu_muc, ds in sorted(nhom.items()):
        dong = ['# Giản đồ rang — `%s`\n' % thu_muc,
                '%d profile. Bấm tên để mở tệp `.alog` (tải về, mở bằng Artisan: `File → Open`). '
                'Giản đồ sinh tự động bằng [`tools/ve_gian_do_alog.py`](../../../tools/ve_gian_do_alog.py) — '
                '[về bảng tổng](../README.md).\n' % len(ds)]
        for rel in ds:
            d = doc(os.path.join(GOC, rel))
            ten = os.path.splitext(os.path.basename(rel))[0]
            link_alog = '/'.join(rel.split('/')[1:]).replace(' ', '%20')
            if not d:
                dong.append('### %s\n\n_Không đọc được tệp._\n' % ten)
                continue
            tieu_de = d.get('title') if d.get('title') not in (None, '', 'Roaster Scope') else ten
            svg, tom = ve(d, str(tieu_de)[:70], phu_de_cua(d))
            if not svg:
                dong.append('### [%s](%s)\n\n_Bản ghi quá ngắn, không vẽ._\n' % (ten, link_alog))
                continue
            ra = os.path.join(DO_THI, rel[:-5] + '.svg')
            os.makedirs(os.path.dirname(ra), exist_ok=True)
            open(ra, 'w', encoding='utf-8').write(svg)
            dem += 1
            anh = ('../_do-thi/' + rel[:-5] + '.svg').replace(' ', '%20')
            so = ' · '.join('**%s** %s · %s°C' % (k, v[0], v[1]) for k, v in tom['moc'].items() if k != 'CHARGE')
            if 'tong' in tom:
                so += '  —  tổng **%s**' % tom['tong'] + (' · DTR **%s**' % tom['dtr'] if 'dtr' in tom else '')
            dong.append('### [%s](%s)\n\n![%s](%s)\n\n%s\n' % (ten, link_alog, escape(ten), anh, so))
        if thu_muc != '.':
            open(os.path.join(GOC, thu_muc, TRANG), 'w', encoding='utf-8').write('\n'.join(dong) + '\n')
    print('ve', dem, 'gian do,', len([k for k in nhom if k != '.']), 'trang xem')


if __name__ == '__main__':
    sys.exit(main())
