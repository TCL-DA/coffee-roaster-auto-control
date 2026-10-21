# -*- coding: utf-8 -*-
"""Vẽ giản đồ THẬT của hồ sơ mẫu case CS-01 (CS-01_ho-so-mau.csv — định dạng hồ sơ thẻ SD của máy OTL).
Dùng chung bộ vẽ với kho profile (tools/ve_gian_do_alog.py).
Chạy: python docs/case-study/ve_ho_so_cs01.py  → docs/case-study/CS-01_ho-so-mau.svg"""
import os
import sys

DAY = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(DAY, '..', '..', 'tools'))
import ve_gian_do_alog as vg  # noqa: E402

NGUON = os.path.join(DAY, 'CS-01_ho-so-mau.csv')
MOC_IDX = {'CHARGE': 0, 'DRY End': 1, 'FCs': 2, 'DROP': 6}


def giay(s):
    m, x = s.split(':')
    return int(m) * 60 + int(x)


dong = [l.rstrip('\n').split('\t') for l in open(NGUON, encoding='utf-8', errors='replace')]
hang = [r for r in dong[2:] if len(r) > 6 and r[1]]
tx = [float(giay(r[1])) for r in hang]
d = {'timex': tx, 'temp1': [float(r[2]) for r in hang], 'temp2': [float(r[3]) for r in hang],
     'extraname1': ['Gas(%)'], 'extratemp1': [[float(r[6]) for r in hang]],
     'timeindex': [-1, 0, 0, 0, 0, 0, 0, 0], 'computed': {}}
for i, r in enumerate(hang):
    ev = r[4].strip()
    if ev in MOC_IDX:
        d['timeindex'][MOC_IDX[ev]] = i
    if ev == 'TP':
        d['computed'].update(TP_time=tx[i], TP_BT=float(r[3]))

svg, tom = vg.ve(d, 'CS-01 · Hồ sơ mẫu của mẻ AUTO bị đứng sát nhiệt xả',
                 'Hồ sơ thẻ SD (.csv), bản sửa 10/09/2026  ·  FCs 199,0 → DROP 217,0 °C, DEV 4:00  ·  gas 0 % từ 12:09')
open(os.path.join(DAY, 'CS-01_ho-so-mau.svg'), 'w', encoding='utf-8').write(svg)
print('ok', tom)
