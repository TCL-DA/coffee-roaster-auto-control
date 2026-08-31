# -*- coding: utf-8 -*-
"""Ve lai man hinh RANG tu CHINH file .dpa vua sinh, de soi truoc khi mo DIAScreen."""
import zlib, re, sys
from PIL import Image, ImageDraw, ImageFont
TBL=bytes(b^0x64 for b in range(256))
OUT=r'C:\Users\truon\Desktop\GATE_DIASCREEN\HMI_OTL_RANG_iOS.dpa'
raw=open(OUT,'rb').read(); off=raw.find(b'\x1f\x8b\x08',40000)
ini=zlib.decompressobj(31).decompress(raw[off:]).translate(TBL)
secs=[(m.start(), m.group(1).decode('latin1')) for m in re.finditer(rb'\[([A-Za-z_0-9]{2,20})\]', ini)]
bnd=[(secs[i][0], secs[i+1][0] if i+1<len(secs) else len(ini), secs[i][1]) for i in range(len(secs))]
# tim man hinh ID=20
si=[i for i,b in enumerate(bnd) if b[2]=='Screen' and re.search(rb'\r\nID=20\r\n', ini[b[0]:b[1]])][0]
items=[]; i=si+1
while i<len(bnd) and bnd[i][2] in ('Element','State','AuxKeyElement'):
    if bnd[i][2]=='Element':
        el=ini[bnd[i][0]:bnd[i][1]]
        st=ini[bnd[i+1][0]:bnd[i+1][1]] if i+1<len(bnd) and bnd[i+1][2]=='State' else b''
        items.append((el,st))
    i+=1
def g(b,k,d=None):
    m=re.search((r'\r\n'+re.escape(k)+r'=([^\r\n]*)\r\n').encode(), b)
    return m.group(1).decode('latin1') if m else d
def gs(b,k):
    m=re.search((r'\r\n'+re.escape(k)+r'=(\d+)\r\n').encode()+rb'((?:(?!\r\n)[\s\S])*)\r\n', b)
    if not m: return ''
    return m.group(2).decode('utf-16le','ignore').replace('\x00','')
def rgb(v):
    v=int(v); return (v&255,(v>>8)&255,(v>>16)&255)   # COLORREF -> RGB
img=Image.new('RGB',(1024,600),(0,0,0)); dr=ImageDraw.Draw(img)
def font(sz,bold=0):
    p=r'C:\Windows\Fonts\%s.ttf'%('arialbd' if bold else 'arial')
    return ImageFont.truetype(p, max(8,int(sz*1.05)))
DEMO={'40061':'198.4','40062':'231.0','40063':'8.2','40067':'45','40065':'60',
      '40066':'38','40086':'-80','40068':'12','40069':'45','40084':'61.7',
      '40060':'1','40140':'30','40082':'182.0'}
for el,st in items:
    t,sub=g(el,'Type'),g(el,'SubType')
    x,y,w,h=[int(g(el,k,'0')) for k in ('X','Y','Width','Height')]
    if t=='10' and sub=='2':
        c=rgb(g(st,'FgFillColor','0')); r=int(g(el,'RoundRadius','0'))
        dr.rounded_rectangle([x,y,x+w,y+h], radius=r, fill=c)
    elif t=='10' and sub=='6':
        s=gs(st,'wTextLen1') or gs(st,'wTextLen0')
        c=rgb(g(st,'FontColor','16777215')); sz=int(g(st,'FontSize0','14'))
        dr.text((x,y), s, font=font(sz,int(g(st,'FontBold','0'))), fill=c)
    elif t=='1' and sub=='10':
        s=gs(st,'wTextLen1') or gs(st,'wTextLen0')
        c=rgb(g(st,'FontColor','16777215')); sz=int(g(st,'FontSize0','14'))
        bb=dr.textbbox((0,0),s,font=font(sz,1))
        dr.text((x+(w-bb[2])//2, y+(h-bb[3])//2-2), s, font=font(sz,1), fill=c)
    elif t=='5' and sub=='1':
        rv=g(el,'ReadVar','') or ''
        reg=(re.search(r'W(\d+)',rv).group(1) if re.search(r'W(\d+)',rv) else '')
        s=DEMO.get(reg,'---')
        c=rgb(g(st,'FontColor','16777215')); sz=int(g(st,'FontSize0','20'))
        dr.text((x,y), s, font=font(sz), fill=c)
img.save('preview_rang.png')
print('da ve', len(items), 'element -> preview_rang.png')
