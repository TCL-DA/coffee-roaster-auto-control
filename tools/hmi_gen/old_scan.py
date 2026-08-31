# -*- coding: utf-8 -*-
import zlib, re, collections, sys
TBL=bytes(b^0x64 for b in range(256))
F=r'F:\HMI\3XILANH_NOLOADCELL\HMI_3XILANH_NOLOADCELL_23_02_2020\Thanh\10_2025\17_CMS_2026\CMS_06_012026 - Copy.dpa'
raw=open(F,'rb').read(); off=raw.find(b'\x1f\x8b\x08',40000)
ini=zlib.decompressobj(31).decompress(raw[off:]).translate(TBL)
secs=[(m.start(), m.group(1).decode('latin1')) for m in re.finditer(rb'\[([A-Za-z_0-9]{2,20})\]', ini)]
bnd=[(secs[i][0], secs[i+1][0] if i+1<len(secs) else len(ini), secs[i][1]) for i in range(len(secs))]
si=[i for i,b in enumerate(bnd) if b[2]=='Screen' and re.search(rb'\r\nID=2\r\n', ini[b[0]:b[1]])][0]
def g(b,k,d=''):
    m=re.search((r'\r\n'+re.escape(k)+r'=([^\r\n]*)\r\n').encode(), b)
    return m.group(1).decode('latin1') if m else d
def gs(b,k):
    m=re.search((r'\r\n'+re.escape(k)+r'=(\d+)\r\n').encode()+rb'((?:(?!\r\n)[\s\S])*)\r\n', b)
    return m.group(2).decode('utf-16le','ignore').replace('\x00','') if m else ''
items=[]; i=si+1
while i<len(bnd) and bnd[i][2] in ('Element','State','AuxKeyElement'):
    if bnd[i][2]=='Element':
        el=ini[bnd[i][0]:bnd[i][1]]
        st=ini[bnd[i+1][0]:bnd[i+1][1]] if i+1<len(bnd) and bnd[i+1][2]=='State' else b''
        items.append((el,st))
    i+=1
NAMES={('10','6'):'Chu',('5','1'):'So',('1','5'):'NutDaTrangThai',('10','2'):'HinhChuNhat',
 ('6','1'):'NhapSo',('6','2'):'NhapChu',('10','3'):'HinhTron',('10','1'):'DuongThang',
 ('1','10'):'NutChuyenMan',('2','1'):'DenBao',('1','1'):'NutBat',('1','2'):'NutTat',
 ('9','1'):'DoThi',('10','7'):'ThuocDo',('5','2'):'HienChu',('1','16'):'OTich'}
print("MAN HINH ID=2 'PROGRAM MANUAL' —", len(items), "doi tuong\n")
c=collections.Counter()
for el,st in items: c[(g(el,'Type'),g(el,'SubType'))]+=1
for k,n in c.most_common():
    print("  %-16s x%-4d (Type=%s Sub=%s)" % (NAMES.get(k,'?'), n, k[0], k[1]))
print("\n--- doi tuong CO dia chi (30 dau) ---")
n=0
for el,st in items:
    rv,wv=g(el,'ReadVar','None'), g(el,'WriteVar','None')
    if rv=='None' and wv=='None': continue
    lbl=gs(st,'wTextLen1') or gs(st,'wTextLen0') or gs(el,'wDescTextLen0')
    print("  %-14s (%4s,%4s) %4sx%-4s R=%-20s W=%-20s %s" % (
        NAMES.get((g(el,'Type'),g(el,'SubType')),'?'), g(el,'X'),g(el,'Y'),
        g(el,'Width'),g(el,'Height'), rv[:20], wv[:20], lbl[:22]))
    n+=1
    if n>=30: break
print("\ntong doi tuong co dia chi:", sum(1 for el,st in items if g(el,'ReadVar','None')!='None' or g(el,'WriteVar','None')!='None'))
