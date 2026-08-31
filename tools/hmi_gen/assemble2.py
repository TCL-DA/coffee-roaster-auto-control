# -*- coding: utf-8 -*-
"""Ghep CA HAI man moi vao 1 file: 20-ROAST (thiet ke moi) + 21-THU CONG nang cap."""
import sys, os, re, zlib, runpy
sys.path.insert(0,'.')
from hmilib import *

OUT = r'C:\Users\truon\Desktop\GATE_DIASCREEN\HMI_OTL_NANGCAP.dpa'
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

def screen_block(sid, en, vi, bg='EDEFF2'):
    s=bytes(scr_tpl)
    s=setk(s,'ID',sid)
    s=setstr(s,'wTextLen',en)
    s=setstr(s,'wScreenDESCTextLen000',en)
    s=setstr(s,'wScreenDESCTextLen001',vi)
    s=setk(s,'BgColor',C(bg))
    for k,v in (('IsSubScreen',0),('IsTemplateScreen',0),('IsKeypadScreen',0),('Hidden',0),
                ('IsUseFrame',0),('IsUseTitleBar',0),('BaseScreenID',0),
                ('OpenMacroLen',0),('CloseMacroLen',0),('CycleMacroLen',0)):
        s=setk(s,k,v)
    return s

body=b''
for mod, sid, en, vi, bg in (('layout3.py',20,'ROAST','RANG','000000'),
                             ('layout6.py',21,'MANUAL+','THU CONG+','EDEFF2')):
    E = runpy.run_path(mod)['E']
    body += screen_block(sid,en,vi,bg) + aux_tpl + b''.join(el+st for el,st in E)
    print('  man %d (%s): %d khoi' % (sid, vi, len(E)))

out_ini = ini[:ins] + body + ini[ins:]
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT,'wb').write(encode(head,out_ini))
print('da ghi %s (%d byte)' % (os.path.basename(OUT), os.path.getsize(OUT)))

sys.path.insert(0, r'f:\Project\112_Quanly\mcp-dpa')
import dpa_parser as p
d0,d1=p.load(BASE),p.load(OUT)
print('man hinh %d -> %d | element %d -> %d | macro %d -> %d'
      % (len(p.screens(d0)),len(p.screens(d1)),len(p.elements(d0)),
         len(p.elements(d1)),len(p.macros(d0)),len(p.macros(d1))))
for s in p.screens(d1):
    if s.get('id') in ('20','21'): print('   moi:', s.get('id'), s.get('name'), s.get('size'))
