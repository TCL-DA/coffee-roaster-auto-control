# -*- coding: utf-8 -*-
"""Soát MÀU · MÀU CHỮ · FONT trên toàn app — kể cả popup và lúc ĐANG RANG.

Vì sao cần riêng bộ này: bộ đo trước chỉ quét 6 tab ở trạng thái ĐỨNG YÊN, tức
**14 hộp thoại đều đang đóng** nên không phần tử nào bên trong được đo, và màn
Rang lúc đó chưa vào mẻ nên các trạng thái nóng (nút xả đỏ, dải giai đoạn đang
sáng, thông báo lệnh) cũng chưa hiện. Đó là hai vùng lớn chưa ai soi.

F1  Font: ô nhập và nút KHÔNG kế thừa font trang — thiếu `font-family` là dấu
    tiếng Việt vẽ bằng font dự phòng của trình duyệt, nhìn lệch hẳn phần còn lại.
F2  Chữ quá nhỏ so với màn cảm ứng đứng xa (ngưỡng đọc trong xưởng).
C1  Tương phản chữ/nền theo WCAG ở: 6 tab × 2 nền × {chờ, đang rang}
    + 13 hộp thoại × 2 nền.
C2  Màu chữ ghim cứng mã hex thay vì dùng token — nguồn gốc của mọi lần
    "màu đường vẽ đem làm màu chữ" tái phát.

Chạy: python tools/test_ui_colors_fonts.py [--report]
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from test_ui_audit import dang_nhap  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parent.parent
APP = ROOT / "OTL Roast Lab.html"

BRIDGE = """
window.__snap=null; window.__st='connected';
window.pywebview={api:{
  link_snapshot: async()=>({state:window.__st,mode:'pclink',err:'',port:'COM-TEST',
                            age_ms:10,data:window.__snap}),
  link_config: async()=>({port:'COM-TEST',baud:9600}),
  toggle_fullscreen: async()=>null }};
"""

DIALOGS = ["profedit", "napedit", "scalebox", "roastmgr", "batchDetail", "batchCompare",
           "portpick", "askbox", "keyboard", "numpad", "picker", "aboutbox", "khoForm"]

# Font app CHỦ ĐỘNG chọn. Bản thiết kế Claude Design dùng 'IBM Plex Sans' cho chữ
# và 'IBM Plex Mono' cho số; app nhúng sẵn hai bộ này nên mọi chữ phải rơi vào đây.
OK_FONTS = ["ibm plex sans", "ibm plex mono", "segoe ui", "system-ui", "-apple-system"]

# ── C1 · tương phản. Phép ghép nền đã sửa: gom lớp tới lớp ĐỤC rồi chồng ngược ──
JS_CONTRAST = r"""
(A) => {
  const MIN=A.min, ROOT=A.root?document.querySelector(A.root):document.body;
  if(!ROOT)return [];
  const lin=c=>{c/=255;return c<=0.04045?c/12.92:Math.pow((c+0.055)/1.055,2.4);};
  const lum=([r,g,b])=>0.2126*lin(r)+0.7152*lin(g)+0.0722*lin(b);
  const parse=s=>{const m=s&&s.match(/rgba?\(([^)]+)\)/);if(!m)return null;
    const p=m[1].split(/[,\s/]+/).filter(Boolean).map(Number);
    return {rgb:p.slice(0,3),a:p.length>3?p[3]:1};};
  const over=(fg,bg)=>fg.rgb.map((c,i)=>c*fg.a+bg[i]*(1-fg.a));
  /* Nền GRADIENT hoặc ẢNH thì KHÔNG tính được bằng một màu — bộ đo cũ từng báo
     1,18:1 cho chữ trắng trên nền nâu mà thật ra là 6:1. Gặp gradient thì trả
     null và BỎ QUA phần tử đó, thà không đo còn hơn đo sai rồi đi "sửa" oan. */
  const bgOf=el=>{
    const layers=[];let n=el;
    while(n&&n.nodeType===1){
      const st=getComputedStyle(n);
      if(st.backgroundImage&&st.backgroundImage!=='none')return null;
      const c=parse(st.backgroundColor);
      if(c&&c.a>0){layers.push(c);if(c.a>=0.999)break;}
      n=n.parentElement;}
    /* Không gặp lớp đục nào thì lấy nền THẬT của trang, ĐỪNG ghim trắng: ở nền
       tối, chữ trắng trên nền trắng giả ra 1,18:1 và bị báo lỗi oan. */
    const nen=()=>{ for(const n of [document.body,document.documentElement]){
        const c=parse(getComputedStyle(n).backgroundColor);
        if(c&&c.a>=0.999)return c.rgb; } return [255,255,255]; };
    let base=layers.length&&layers[layers.length-1].a>=0.999?layers.pop().rgb:nen();
    for(let i=layers.length-1;i>=0;i--)base=over(layers[i],base);
    return base;};
  /* Nội dung trong <details> ĐANG ĐÓNG: người dùng không thấy, nhưng trình duyệt
     vẫn trả kích thước và trả MÀU CŨ (chưa tính lại theo nền hiện tại). Đo vào đó
     là ra chữ nền tối nằm trên nền trắng — báo lỗi oan. Bỏ qua hẳn. */
  const trongMenuDong=el=>{
    for(let n=el;n;n=n.parentElement){
      const p=n.parentElement;
      if(p&&p.tagName==='DETAILS'&&!p.open&&n.tagName!=='SUMMARY')return true;
    } return false;};
  const vis=el=>{if(trongMenuDong(el))return false;
    const s=getComputedStyle(el);
    if(s.display==='none'||s.visibility==='hidden'||+s.opacity===0)return false;
    const r=el.getBoundingClientRect();return r.width>0&&r.height>0;};
  const name=el=>el.id?'#'+el.id:(el.tagName.toLowerCase()+'.'+((el.className||'').toString().trim().split(/\s+/)[0]||''));
  const out=[],seen=new Set();
  for(const el of ROOT.querySelectorAll('*')){
    if(!vis(el)||el.children.length)continue;
    const t=(el.textContent||'').trim();if(!t)continue;
    const s=getComputedStyle(el);
    const fg=parse(s.color);if(!fg)continue;
    const px=parseFloat(s.fontSize), bold=parseInt(s.fontWeight)>=700;
    const big=px>=24||(px>=18.66&&bold);
    const need=big?3.0:MIN;
    const b=bgOf(el);if(!b)continue;
    const f=over(fg,b);
    const L1=lum(f),L2=lum(b);
    const ratio=(Math.max(L1,L2)+0.05)/(Math.min(L1,L2)+0.05);
    if(ratio<need){
      const k=name(el)+'|'+t.slice(0,20);if(seen.has(k))continue;seen.add(k);
      out.push({sel:name(el),ratio:+ratio.toFixed(2),need,px:+px.toFixed(0),txt:t.slice(0,36),
                fg:f.map(Math.round).join(','),bg:b.map(Math.round).join(',')});
    }
  }
  return out;
}
"""

# ── F1/F2 · font và cỡ chữ ──────────────────────────────────────────────────
JS_FONT = r"""
(P) => {
  const ROOT=P.root?document.querySelector(P.root):document.body;
  if(!ROOT)return {lac:[],nho:[]};
  /* Nội dung trong <details> ĐANG ĐÓNG: người dùng không thấy, nhưng trình duyệt
     vẫn trả kích thước và trả MÀU CŨ (chưa tính lại theo nền hiện tại). Đo vào đó
     là ra chữ nền tối nằm trên nền trắng — báo lỗi oan. Bỏ qua hẳn. */
  const trongMenuDong=el=>{
    for(let n=el;n;n=n.parentElement){
      const p=n.parentElement;
      if(p&&p.tagName==='DETAILS'&&!p.open&&n.tagName!=='SUMMARY')return true;
    } return false;};
  const vis=el=>{if(trongMenuDong(el))return false;
    const s=getComputedStyle(el);
    if(s.display==='none'||s.visibility==='hidden'||+s.opacity===0)return false;
    const r=el.getBoundingClientRect();return r.width>0&&r.height>0;};
  const name=el=>el.id?'#'+el.id:(el.tagName.toLowerCase()+'.'+((el.className||'').toString().trim().split(/\s+/)[0]||''));
  const lac=[],nho=[],seen=new Set();
  for(const el of ROOT.querySelectorAll('*')){
    if(!vis(el))continue;
    const t=(el.textContent||'').trim();
    if(!t&&!['INPUT','TEXTAREA','SELECT'].includes(el.tagName))continue;
    const s=getComputedStyle(el);
    const dau=(s.fontFamily||'').toLowerCase().split(',')[0].replace(/["']/g,'').trim();
    if(!P.ok.some(f=>dau.includes(f))){
      const k='F|'+name(el)+'|'+dau;
      if(!seen.has(k)){seen.add(k);lac.push({sel:name(el),font:dau,tag:el.tagName,txt:t.slice(0,28)});}
    }
    if(el.children.length===0&&t){
      const px=parseFloat(s.fontSize);
      if(px<P.min){const k='N|'+name(el);if(!seen.has(k)){seen.add(k);
        nho.push({sel:name(el),px:+px.toFixed(1),txt:t.slice(0,28)});}}
    }
  }
  return {lac,nho};
}
"""

SNAP_RUN = {
    "bt": 196.4, "et": 214.0, "ror_bt": 6.2, "ror_et": 4.0, "ror_pro": 6.0,
    "gas": 34, "air": 58, "drum": 55, "sv": 205.0, "vac": -110,
    "step": 9, "t_roast": 540,
    "phase": {"dry": True, "mai": True, "dev": True},
    "flags": {"auto": True, "gas": True, "flame": True, "charge": False, "drop": False,
              "escape": False, "cool": False, "pc_control": True},
    "hb": 9001,
}


def main():
    report_only = "--report" in sys.argv
    found, ran = [], []

    def hit(c, lv, m):
        found.append((c, lv, m))

    def did(c, n):
        ran.append((c, n))

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 768})
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.add_init_script(BRIDGE)
        page.goto(APP.as_uri())
        dang_nhap(page)
        page.wait_for_timeout(500)
        # Dựng sẵn nội dung cho các hộp, nếu không hộp mở ra rỗng và đo được rất ít.
        page.evaluate("""()=>{newProfile();closeProfEdit();
          if(typeof loadProfile==='function')loadProfile(0);}""")

        def quet(canh, minc=4.5, minpx=13, root=None):
            n = 0
            for c in page.evaluate(JS_CONTRAST, {"min": minc, "root": root}):
                n += 1
                hit("C1", "P2", "[%s] tương phản %.2f < %.1f (%dpx) %s %r  chữ(%s) nền(%s)"
                    % (canh, c["ratio"], c["need"], c["px"], c["sel"], c["txt"],
                       c["fg"], c["bg"]))
            f = page.evaluate(JS_FONT, {"ok": OK_FONTS, "min": minpx, "root": root})
            for x in f["lac"]:
                hit("F1", "P2", "[%s] %s dùng font NGOÀI bộ đã chọn: %r %s %r"
                    % (canh, x["tag"], x["font"], x["sel"], x["txt"]))
            for x in f["nho"]:
                hit("F2", "P3", "[%s] chữ %.1fpx quá nhỏ cho màn cảm ứng: %s %r"
                    % (canh, x["px"], x["sel"], x["txt"]))
            return n, len(f["lac"]), len(f["nho"])

        # ══ 6 TAB × 2 NỀN × {chờ, đang rang} ═══════════════════════════════
        tong = [0, 0, 0]
        for theme in ["light", "dark"]:
            page.evaluate("(t)=>setTheme(t)", theme)
            for tab in ["tongquan", "rang", "hoso", "lichsu", "kho", "caidat"]:
                page.evaluate("(t)=>gotoTab(t)", tab)
                page.wait_for_timeout(160)
                r = quet("%s/%s" % (theme, tab))
                tong = [a + b for a, b in zip(tong, r)]
        did("tab", "6 tab × 2 nền: %d tương phản · %d font lạc · %d chữ nhỏ" % tuple(tong))

        # ══ ĐANG RANG — trạng thái nóng mà bộ đo cũ không với tới ══════════
        for theme in ["light", "dark"]:
            page.evaluate("(t)=>setTheme(t)", theme)
            page.evaluate("""(d)=>{gotoTab('rang');
              window.__snap=d;DS.state='connected';DS.mode='pclink';DS.snap=d;
              applyMachine(d);
              // ép các trạng thái NÓNG cùng hiện: nút xả giục, thông báo lệnh
              const bd=document.getElementById('btnDrop');
              if(bd)bd.classList.add('warn','hot');
              if(typeof uxCommandStart==='function')uxCommandStart('gas',34);
            }""", SNAP_RUN)
            page.wait_for_timeout(400)
            r = quet("%s/ĐANG RANG" % theme)
            did("rang-%s" % theme, "%d tương phản · %d font lạc · %d chữ nhỏ" % r)

        # ══ 7 MÀU CHỦ ĐẠO × 2 NỀN — thợ đổi được màu, đổi xong phải vẫn đọc được
        # Chỗ nào ghim cứng một mã hex thay vì dùng token mực sẽ lòi ra ở đây.
        accents = ["otl", "emerald", "azure", "teal", "violet", "amber", "ember"]
        for theme in ["light", "dark"]:
            page.evaluate("(t)=>setTheme(t)", theme)
            for ac in accents:
                page.evaluate("(a)=>setAccent(a)", ac)
                page.evaluate("()=>gotoTab('rang')")
                page.wait_for_timeout(200)
                quet("%s/màu %s" % (theme, ac))
        page.evaluate("()=>setAccent('ember')")
        did("màu chủ đạo", "%d màu × 2 nền đã đo trên màn Rang" % len(accents))

        # ══ 13 HỘP THOẠI × 2 NỀN — vùng CHƯA AI ĐO ═════════════════════════
        for theme in ["light", "dark"]:
            page.evaluate("(t)=>setTheme(t)", theme)
            for dlg in DIALOGS:
                ok = page.evaluate("""(id)=>{
                  document.querySelectorAll('.overlay').forEach(e=>e.classList.remove('on'));
                  const e=document.getElementById(id); if(!e)return false;
                  e.classList.add('on');
                  const r=e.firstElementChild&&e.firstElementChild.getBoundingClientRect();
                  return !!(r&&r.width>0&&r.height>0);}""", dlg)
                if not ok:
                    hit("D0", "P3", "[%s] hộp %s mở ra RỖNG — không đo được" % (theme, dlg))
                    continue
                page.wait_for_timeout(140)
                quet("%s/hộp %s" % (theme, dlg), root="#" + dlg)
            page.evaluate("()=>document.querySelectorAll('.overlay').forEach(e=>e.classList.remove('on'))")
        did("hộp", "%d hộp × 2 nền đã mở và đo" % len(DIALOGS))

        if errs:
            hit("JS", "P1", "lỗi JavaScript: %s" % "; ".join(dict.fromkeys(errs))[:240])
        did("JS", "lỗi JS: %s" % (len(errs) or "không"))
        browser.close()

    print("Kịch bản dựng được (%d):" % len(ran))
    for c, n in ran:
        print("  %-10s %s" % (c, n))
    print("")
    if not found:
        print("ĐẠT: màu, màu chữ và font sạch ở mọi tab, mọi hộp thoại, cả lúc đang rang.")
        return 0
    rank = {"P1": 0, "P2": 1, "P3": 2}
    found.sort(key=lambda x: (rank.get(x[1], 9), x[0]))
    print("Phát hiện %d mục:\n" % len(found))
    last = None
    for c, lv, m in found:
        if c != last:
            print("")
            last = c
        print("  %-3s %s  %s" % (c, lv, m))
    print("\nTổng: %d (P1=%d P2=%d P3=%d)" % (
        len(found), *[sum(1 for f in found if f[1] == k) for k in ("P1", "P2", "P3")]))
    return 0 if report_only else 1


if __name__ == "__main__":
    sys.exit(main())
