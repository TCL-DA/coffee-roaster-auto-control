# -*- coding: utf-8 -*-
"""Ve lai BAT KY man hinh nao tu file .dpa (mo phong, khong can DIAScreen)."""
import zlib, re, sys
from PIL import Image, ImageDraw, ImageFont
TBL=bytes(b^0x64 for b in range(256))

def load(path):
    raw=open(path,'rb').read(); off=raw.find(b'\x1f\x8b\x08',40000)
    return zlib.decompressobj(31).decompress(raw[off:]).translate(TBL)

def sections(ini):
    s=[(m.start(), m.group(1).decode('latin1')) for m in re.finditer(rb'\[([A-Za-z_0-9]{2,20})\]', ini)]
    return [(s[i][0], s[i+1][0] if i+1<len(s) else len(ini), s[i][1]) for i in range(len(s))]

def g(b,k,d=''):
    m=re.search((r'\r\n'+re.escape(k)+r'=([^\r\n]*)\r\n').encode(), b)
    return m.group(1).decode('latin1') if m else d
def gs(b,k):
    m=re.search((r'\r\n'+re.escape(k)+r'=(\d+)\r\n').encode()+rb'((?:(?!\r\n)[\s\S])*)\r\n', b)
    return m.group(2).decode('utf-16le','ignore').replace('\x00','') if m else ''
def rgb(v):
    try: v=int(v)
    except: return (128,128,128)
    return (v&255,(v>>8)&255,(v>>16)&255)
def font(sz,bold=0):
    return ImageFont.truetype(r'C:\Windows\Fonts\%s.ttf'%('arialbd' if bold else 'arial'), max(8,int(sz*1.05)))

def elements_of(ini, sid):
    bnd=sections(ini)
    hit=[i for i,b in enumerate(bnd) if b[2]=='Screen'
         and re.search((r'\r\nID=%s\r\n'%sid).encode(), ini[b[0]:b[1]])]
    if not hit: raise SystemExit('khong thay man hinh ID=%s'%sid)
    i=hit[0]+1; out=[]
    while i<len(bnd) and bnd[i][2] in ('Element','State','AuxKeyElement'):
        if bnd[i][2]=='Element':
            el=ini[bnd[i][0]:bnd[i][1]]
            st=ini[bnd[i+1][0]:bnd[i+1][1]] if i+1<len(bnd) and bnd[i+1][2]=='State' else b''
            out.append((el,st))
        i+=1
    return out, ini[bnd[hit[0]][0]:bnd[hit[0]][1]]

DEMO={'40061':'198.4','40062':'231.0','40063':'8.2','40064':'4.1','40065':'60','40066':'38',
 '40067':'45','40068':'12','40069':'45','40084':'61.7','40060':'1','40140':'30','40082':'182.0',
 '40083':'204.5','40070':'182.0','40071':'0','40072':'12','40074':'1','40075':'30','40077':'6',
 '40078':'12','40079':'196.0','40080':'9','40081':'20','40073':'155.0','40076':'176.0'}

def draw(path, sid, out_png, caps=None):
    caps = caps or {}
    ini=load(path); items, scr = elements_of(ini, sid)
    W=int(g(scr,'PanelSizeX','1024')); H=int(g(scr,'PanelSizeY','600'))
    bg=rgb(g(scr,'BgColor','13158600'))
    img=Image.new('RGB',(W,H),bg); dr=ImageDraw.Draw(img)
    drawn=0
    for el,st in items:
        vv=g(el,'VisibleVar','None')
        m=re.search(r'W(\d+)', vv or '')
        if m and caps.get(m.group(1),1)==0: continue
        t,sub=g(el,'Type'),g(el,'SubType')
        try: x,y,w,h=[int(g(el,k,'0')) for k in ('X','Y','Width','Height')]
        except: continue
        fg=rgb(g(st,'FgFillColor', g(st,'FgColor','11842740')))
        fc=rgb(g(st,'FontColor','0'))
        sz=int(g(st,'FontSize0','14') or 14); bold=int(g(st,'FontBold','0') or 0)
        rad=int(g(el,'RoundRadius','0') or 0)
        label=gs(st,'wTextLen1') or gs(st,'wTextLen0')
        drawn+=1
        if t=='10' and sub in ('2','6'):          # chu nhat / chu
            if sub=='2':
                dr.rounded_rectangle([x,y,x+w,y+h], radius=min(rad,min(w,h)//2), fill=fg)
            if label: dr.text((x+3,y+2), label, font=font(sz,bold), fill=fc)
        elif t=='10' and sub=='3':                 # hinh tron
            dr.ellipse([x,y,x+w,y+h], fill=fg)
        elif t=='10' and sub=='1':                 # duong thang
            dr.line([x,y,x+w,y+h], fill=fg, width=2)
        elif t=='9':                               # do thi
            dr.rectangle([x,y,x+w,y+h], fill=(250,250,250), outline=(120,120,120))
            dr.text((x+8,y+6),'[ ĐỒ THỊ RANG ]',font=font(13),fill=(90,90,90))
        elif t=='5':                               # so / chu hien thi
            reg=(re.search(r'W(\d+)', g(el,'ReadVar','')) or [None])
            k=re.search(r'W(\d+)', g(el,'ReadVar','') or '')
            s=DEMO.get(k.group(1),'123.4') if k else '---'
            dr.text((x+2,y), s, font=font(sz), fill=fc)
        elif t in ('1','6','2'):                   # nut / o nhap / den bao
            dr.rounded_rectangle([x,y,x+w,y+h], radius=min(rad or 4,min(w,h)//2),
                                 fill=fg, outline=(90,90,90))
            if label:
                bb=dr.textbbox((0,0),label,font=font(sz,bold))
                dr.text((x+max(2,(w-bb[2])//2), y+max(1,(h-bb[3])//2)-1), label,
                        font=font(sz,bold), fill=fc)
        else:
            dr.rectangle([x,y,x+w,y+h], outline=(150,150,150))
    img.save(out_png)
    print('man %s: ve %d/%d doi tuong -> %s' % (sid, drawn, len(items), out_png))

if __name__=='__main__':
    draw(sys.argv[1], sys.argv[2], sys.argv[3])
