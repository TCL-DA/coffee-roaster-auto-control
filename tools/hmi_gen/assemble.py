# -*- coding: utf-8 -*-
"""Ghep man hinh moi vao file .dpa + kiem chung."""
import sys, os, re, zlib, runpy
sys.path.insert(0, '.')
from hmilib import *
import pickle

g = runpy.run_path('layout3.py'); E = g['E']
NEW_ID = 20
OUT = r'C:\Users\truon\Desktop\GATE_DIASCREEN\HMI_OTL_RANG_iOS.dpa'

raw = open(BASE,'rb').read(); head, ini = decode(raw)
secs=[(m.start(), m.group(1).decode('latin1')) for m in re.finditer(rb'\[([A-Za-z_0-9]{2,20})\]', ini)]
bnd=[(secs[i][0], secs[i+1][0] if i+1<len(secs) else len(ini), secs[i][1]) for i in range(len(secs))]
scr_idx=[i for i,b in enumerate(bnd) if b[2]=='Screen']
aux_idx=[i for i,b in enumerate(bnd) if b[2]=='AuxKeyElement']
scr_tpl=ini[bnd[scr_idx[0]][0]:bnd[scr_idx[0]][1]]
aux_tpl=ini[bnd[aux_idx[0]][0]:bnd[aux_idx[0]][1]]
i=scr_idx[-1]+1
while i<len(bnd) and bnd[i][2] in ('Element','State','AuxKeyElement'): i+=1
ins=bnd[i][0] if i<len(bnd) else len(ini)

scr=bytes(scr_tpl)
scr=setk(scr,'ID',NEW_ID)
scr=setstr(scr,'wTextLen','ROAST')
scr=setstr(scr,'wScreenDESCTextLen000','ROAST')
scr=setstr(scr,'wScreenDESCTextLen001','RANG')
scr=setk(scr,'BgColor',BG)
for k,v in (('IsSubScreen',0),('IsTemplateScreen',0),('IsKeypadScreen',0),('Hidden',0),
            ('IsUseFrame',0),('IsUseTitleBar',0),('BaseScreenID',0),
            ('OpenMacroLen',0),('CloseMacroLen',0),('CycleMacroLen',0)):
    scr=setk(scr,k,v)

body = scr + aux_tpl + b''.join(el+st for el,st in E)
out_ini = ini[:ins] + body + ini[ins:]
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT,'wb').write(encode(head,out_ini))
print('da ghi %s (%d byte), payload +%d B' % (os.path.basename(OUT), os.path.getsize(OUT), len(out_ini)-len(ini)))

sys.path.insert(0, r'f:\Project\112_Quanly\mcp-dpa')
import dpa_parser as p
d0,d1 = p.load(BASE), p.load(OUT)
print('man hinh %d -> %d | element %d -> %d | macro %d -> %d'
      % (len(p.screens(d0)),len(p.screens(d1)),
         len(p.elements(d0)),len(p.elements(d1)),
         len(p.macros(d0)),len(p.macros(d1))))
mine=[e for e in p.elements(d1) if str(e.get('screen_id'))=='20']
print('element tren man RANG:', len(mine))
# kiem chuoi tieng Viet con dau
import collections
raw2=open(OUT,'rb').read(); off=raw2.find(b'\x1f\x8b\x08',40000)
ini2=zlib.decompressobj(31).decompress(raw2[off:]).translate(TBL)
for probe in ('NHI\u1ec6T H\u1ea0T','T\u1ed0C \u0110\u1ed8 T\u0102NG','L\u1ed2NG RANG','\u00c1P H\u00daT','TH\u1edcI GIAN'):
    ok = probe.encode('utf-16le') in ini2
    print('  chuoi %-16s : %s' % (probe, 'CO' if ok else 'THIEU'))
vv=collections.Counter(v.decode('latin1') for v in re.findall(rb'\r\nVisibleVar=([^\r\n]+)\r\n', ini2))
print('VisibleVar gan bien:', {k:n for k,n in vv.items() if k!='None'})
