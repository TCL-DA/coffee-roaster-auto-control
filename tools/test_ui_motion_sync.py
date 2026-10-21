# -*- coding: utf-8 -*-
"""Soát CHUYỂN ĐỘNG, HIỂN THỊ và ĐỒNG BỘ GIỮA CÁC TAB — đo bằng máy.

Bộ kiểm cũ đã phủ tràn/đè/vùng bấm/i18n. Bộ này đi vào bốn chỗ CHƯA ai đo:

M · Chuyển động  — transition đặt trên thuộc tính gây DỰNG LẠI BỐ CỤC
                   (width/height/top/left/margin/padding) thì mỗi khung hình
                   trình duyệt phải tính lại cả trang. Trên màn Rang các thanh
                   này chạy MỖI GIÂY suốt mẻ, cùng lúc với vẽ đồ thị.
H · Hiển thị     — chữ bị cắt mà không có dấu "…" hay title; ô số hiện
                   NaN/undefined/Infinity; tương phản chữ/nền dưới ngưỡng đọc
                   được ở cả nền sáng lẫn tối.
S · Đồng bộ tab  — CÙNG một con số của máy hiện ở nhiều tab phải khớp nhau, và
                   phải tự đổi khi máy đổi, KHÔNG chờ người dùng rời tab rồi
                   quay lại.
X · UX           — nút bị khoá mà không nói lý do; ô đang chờ dữ liệu không có
                   vùng báo trạng thái cho trình đọc màn hình.

Chạy: python tools/test_ui_motion_sync.py [--report]
      --report chỉ IN bảng phát hiện, không bắt lỗi (dùng lúc rà soát).
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from test_ui_audit import dang_nhap  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parent.parent
APP = ROOT / "OTL Roast Lab.html"

# Thuộc tính mà trình duyệt KHÔNG chạy được trên luồng ghép hình: đổi một cái là
# phải đo lại bố cục cả cây. Dùng transform/opacity thay được thì nên thay.
RELAYOUT_PROPS = {
    "width", "height", "top", "left", "right", "bottom", "margin", "margin-top",
    "margin-left", "margin-right", "margin-bottom", "padding", "padding-top",
    "padding-left", "padding-right", "padding-bottom", "font-size", "line-height",
    "flex", "flex-basis", "gap", "inset",
}

# ── M1: quét CSSOM tìm transition trên thuộc tính gây dựng lại bố cục ──────────
JS_RELAYOUT = r"""
(PROPS) => {
  const out=[];
  for(const sheet of document.styleSheets){
    let rules; try{rules=sheet.cssRules;}catch(e){continue;}
    /* BẪY: Chromium từ khi có CSS lồng nhau gắn cho MỌI luật thường một
       `cssRules` RỖNG. Viết `if(r.cssRules){đệ quy;continue;}` là nhảy qua sạch
       cả 1600 luật mà vẫn báo "không thấy gì" — im lặng, không hề lỗi. Nên phải
       xử lý `r.style` TRƯỚC, rồi mới đệ quy khi thật sự có luật con. */
    const walk=list=>{ for(const r of list){
      if(r.cssRules&&r.cssRules.length)walk(r.cssRules);
      if(!r.style)continue;
      let src=((r.style.getPropertyValue('transition-property')||'')+' '+
               (r.style.getPropertyValue('transition')||'')).toLowerCase();
      /* Shorthand có var() bên trong trở thành "giá trị chờ thay" — CSSOM trả
         RỖNG cho cả transition lẫn transition-property. Bỏ qua chỗ này là sót
         đúng những luật hay dùng token nhất. Nên đọc thẳng chữ của luật. */
      if(!src.trim()){
        const m=(r.cssText||'').match(/transition\s*:\s*([^;}]+)/i);
        if(!m)continue; src=m[1].toLowerCase();
      }
      if(!src.trim())continue;
      // tách từng đoạn "prop thời-gian easing" rồi lấy từ đầu tiên
      const props=src.split(',').map(s=>s.trim().split(/\s+/)[0]).filter(Boolean);
      const hit=props.filter(p=>PROPS.includes(p));
      if(hit.length)out.push({sel:r.selectorText||'?',props:hit.join(',')});
    }};
    walk(rules);
  }
  return out;
}
"""

# ── M2: đếm animation VÔ HẠN đang thật sự chạy trên phần tử đang hiện ─────────
JS_INFINITE = r"""
() => {
  const vis=el=>{const s=getComputedStyle(el);
    if(s.display==='none'||s.visibility==='hidden'||+s.opacity===0)return false;
    const r=el.getBoundingClientRect();return r.width>0&&r.height>0;};
  const out=[];
  for(const el of document.querySelectorAll('body *')){
    if(!vis(el))continue;
    const s=getComputedStyle(el);
    if(s.animationName==='none')continue;
    if(!s.animationIterationCount.split(',').includes('infinite'))continue;
    // thuộc tính nào bị hoạt hoá? đọc keyframe để biết có phải box-shadow/filter không
    out.push({name:s.animationName,
              sel:(el.id?'#'+el.id:el.tagName.toLowerCase()+'.'+(el.className||'').toString().trim().split(/\s+/)[0]),
              dur:s.animationDuration});
  }
  return out;
}
"""

# keyframe nào đụng thuộc tính TÔ LẠI NẶNG (box-shadow/filter/backdrop-filter)
JS_HEAVY_KF = r"""
() => {
  const heavy=['box-shadow','filter','backdrop-filter'];
  const out=[];
  for(const sheet of document.styleSheets){
    let rules; try{rules=sheet.cssRules;}catch(e){continue;}
    for(const r of rules){
      if(r.type!==CSSRule.KEYFRAMES_RULE)continue;
      const props=new Set();
      for(const kf of r.cssRules) for(const p of kf.style) props.add(p);
      const hit=heavy.filter(p=>props.has(p));
      if(hit.length)out.push({name:r.name,props:hit.join(',')});
    }
  }
  return out;
}
"""

# ── H1: chữ bị cắt mà không báo hiệu; H2: ô số hỏng ───────────────────────────
JS_DISPLAY = r"""
() => {
  const bad={clip:[],nan:[]};
  const vis=el=>{const s=getComputedStyle(el);
    if(s.display==='none'||s.visibility==='hidden'||+s.opacity===0)return false;
    const r=el.getBoundingClientRect();return r.width>0&&r.height>0;};
  const name=el=>el.id?'#'+el.id:(el.tagName.toLowerCase()+'.'+((el.className||'').toString().trim().split(/\s+/)[0]||''));
  for(const el of document.querySelectorAll('body *')){
    if(!vis(el))continue;
    if(el.children.length)continue;            // chỉ nút lá mang chữ
    const t=(el.textContent||'').trim();
    if(!t)continue;
    if(/\b(NaN|undefined|Infinity|\[object Object\])\b/.test(t))
      bad.nan.push({sel:name(el),txt:t.slice(0,60)});
    const s=getComputedStyle(el);
    const cut=el.scrollWidth-el.clientWidth;
    if(cut>1 && s.overflowX!=='auto' && s.overflowX!=='scroll'){
      const soft=s.textOverflow==='ellipsis'||el.title||el.getAttribute('aria-label');
      if(!soft)bad.clip.push({sel:name(el),cut,txt:t.slice(0,48)});
    }
  }
  return bad;
}
"""

# ── H3: tương phản chữ/nền theo WCAG, nền lấy từ tổ tiên có màu đục ───────────
JS_CONTRAST = r"""
(MIN) => {
  const lin=c=>{c/=255;return c<=0.04045?c/12.92:Math.pow((c+0.055)/1.055,2.4);};
  const lum=([r,g,b])=>0.2126*lin(r)+0.7152*lin(g)+0.0722*lin(b);
  const parse=s=>{const m=s&&s.match(/rgba?\(([^)]+)\)/);if(!m)return null;
    const p=m[1].split(/[,\s/]+/).filter(Boolean).map(Number);
    return {rgb:p.slice(0,3),a:p.length>3?p[3]:1};};
  const over=(fg,bg)=>fg.rgb.map((c,i)=>c*fg.a+bg[i]*(1-fg.a));
  /* Nền THẬT dưới một chữ = chồng các lớp nền từ DƯỚI LÊN.
     Sai lầm dễ mắc: gặp lớp mờ đầu tiên đã đem chồng lên trắng luôn, thế là
     nút mờ trên nền tối bị tính thành nút trắng — cả màn nền tối báo hỏng oan.
     Nên phải GOM các lớp từ chữ đi ra tới lớp ĐỤC đầu tiên, rồi mới chồng ngược. */
  const bgOf=el=>{
    const layers=[];let n=el;
    while(n&&n.nodeType===1){
      const c=parse(getComputedStyle(n).backgroundColor);
      if(c&&c.a>0){layers.push(c);if(c.a>=0.999)break;}
      n=n.parentElement;}
    let base=layers.length&&layers[layers.length-1].a>=0.999
             ?layers.pop().rgb:[255,255,255];
    for(let i=layers.length-1;i>=0;i--)base=over(layers[i],base);
    return base;};
  const vis=el=>{const s=getComputedStyle(el);
    if(s.display==='none'||s.visibility==='hidden'||+s.opacity===0)return false;
    const r=el.getBoundingClientRect();return r.width>0&&r.height>0;};
  const name=el=>el.id?'#'+el.id:(el.tagName.toLowerCase()+'.'+((el.className||'').toString().trim().split(/\s+/)[0]||''));
  const out=[],seen=new Set();
  for(const el of document.querySelectorAll('body *')){
    if(!vis(el)||el.children.length)continue;
    const t=(el.textContent||'').trim();if(!t)continue;
    const s=getComputedStyle(el);
    const fg=parse(s.color);if(!fg)continue;
    const px=parseFloat(s.fontSize), bold=parseInt(s.fontWeight)>=700;
    const big=px>=24||(px>=18.66&&bold);      // ngưỡng chữ lớn của WCAG
    const need=big?3.0:MIN;
    const b=bgOf(el),f=over(fg,b);
    const L1=lum(f),L2=lum(b);
    const ratio=(Math.max(L1,L2)+0.05)/(Math.min(L1,L2)+0.05);
    if(ratio<need){
      const k=name(el)+'|'+t.slice(0,20);if(seen.has(k))continue;seen.add(k);
      out.push({sel:name(el),ratio:+ratio.toFixed(2),need,px:+px.toFixed(0),txt:t.slice(0,40)});
    }
  }
  return out;
}
"""

# ── X1: nút bị khoá mà không nói vì sao ───────────────────────────────────────
JS_DISABLED = r"""
() => {
  const out=[];
  for(const b of document.querySelectorAll('button[disabled],button[aria-disabled="true"]')){
    const r=b.getBoundingClientRect();if(r.width<1||r.height<1)continue;
    const why=b.title||b.getAttribute('aria-label')||b.getAttribute('data-why')||
              b.getAttribute('aria-describedby');
    if(!why)out.push({sel:b.id?'#'+b.id:b.className,txt:(b.textContent||'').trim().slice(0,40)});
  }
  return out;
}
"""

SNAP_A = {
    "bt": 182.4, "et": 205.1, "ror_bt": 8.4, "ror_et": 6.0, "ror_pro": 8.0,
    "gas": 42, "air": 61, "drum": 55, "sv": 200.0, "vac": -110,
    "step": 6, "t_roast": 240,
    "phase": {"dry": True, "mai": False, "dev": False},
    "flags": {"auto": True, "gas": True, "charge": False, "drop": False,
              "escape": False, "cool": False, "pc_control": True},
    "hb": 4242,
}


# CẦU pywebview GIẢ — BẮT BUỘC phải có.
# Không cài cầu thì app coi đây là trình duyệt thuần và chạy nhánh MÔ PHỎNG; lúc đó
# "mất kết nối mà vẫn hiện số" là hành vi ĐÚNG của app, còn bộ kiểm thì báo lỗi oan.
# Bản EXE luôn có cầu, nên muốn đo đúng thì phải dựng lại đúng bối cảnh đó.
BRIDGE = """
window.__snap=null; window.__st='connected';
window.pywebview={api:{
  link_snapshot: async()=>({state:window.__st,mode:'pclink',err:'',port:'COM-TEST',
                            age_ms:10,data:window.__snap}),
  link_config: async()=>({port:'COM-TEST',baud:9600}),
  toggle_fullscreen: async()=>null,
}};
"""


def snap(page, **over):
    d = dict(SNAP_A)
    d.update(over)
    page.evaluate(
        "(d)=>{window.__snap=d;window.__st='connected';"
        "DS.state='connected';DS.mode='pclink';DS.snap=d;applyMachine(d);}", d
    )
    page.wait_for_timeout(120)


def main():
    report_only = "--report" in sys.argv
    found = []          # (mã, mức, mô tả)
    ran = []            # phép kiểm đã THẬT SỰ chạy được kịch bản của nó

    # GHI NHẬN ≠ LỖI. M1/M2/M3/M5 là mấy chỗ đã CÂN NHẮC rồi cố ý không đổi
    # (đo được 0 tác vụ khoá luồng; đổi sang transform sẽ méo bo góc). Vẫn in ra
    # để không ai quên, nhưng KHÔNG bắt bộ kiểm đỏ — một bộ kiểm lúc nào cũng đỏ
    # thì chẳng ai còn đọc nó nữa.
    GHI_NHAN = {"M1", "M2", "M3", "M5"}
    notes = []

    def hit(code, level, msg):
        (notes if code in GHI_NHAN else found).append((code, level, msg))

    def did(code, note):
        """Ghi nhận phép kiểm đã dựng được kịch bản. Phép nào không xuất hiện ở
        đây là đã ÂM THẦM BỎ QUA — nguy hiểm hơn cả một phép báo lỗi."""
        ran.append((code, note))

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 768})
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.add_init_script(BRIDGE)
        page.goto(APP.as_uri())
        dang_nhap(page)
        page.wait_for_timeout(400)

        # ══ M · CHUYỂN ĐỘNG ═════════════════════════════════════════════════
        relay = page.evaluate(JS_RELAYOUT, sorted(RELAYOUT_PROPS))
        for r in relay:
            hit("M1", "P2", "transition trên thuộc tính dựng lại bố cục: %s { %s }"
                % (r["sel"][:70], r["props"]))

        heavy = {k["name"]: k["props"] for k in page.evaluate(JS_HEAVY_KF)}

        # đưa màn Rang vào trạng thái "nhiều thứ nhấp nháy nhất" rồi đếm
        page.evaluate("gotoTab('rang')")
        snap(page)
        page.evaluate("""()=>{
          document.querySelectorAll('.tbtn').forEach(b=>b.classList.add('ready'));
          const d=document.getElementById('btnDrop');if(d)d.classList.add('warn','hot');
          const i=document.getElementById('btnIgnite');if(i)i.classList.add('slow');
        }""")
        page.wait_for_timeout(200)
        inf = page.evaluate(JS_INFINITE)
        heavy_running = [a for a in inf if a["name"] in heavy]
        if len(inf) > 3:
            hit("M2", "P2", "màn Rang chạy %d hoạt ảnh vô hạn cùng lúc (%s)"
                % (len(inf), ", ".join(sorted({a["name"] for a in inf}))))
        for a in heavy_running:
            hit("M3", "P2", "hoạt ảnh vô hạn %s trên %s hoạt hoá %s — tô lại nặng mỗi khung hình"
                % (a["name"], a["sel"], heavy[a["name"]]))

        # M4 — bật "giảm chuyển động" thì phải TẮT SẠCH
        page.evaluate("document.documentElement.dataset.motion='reduced'")
        page.wait_for_timeout(150)
        left = page.evaluate(JS_INFINITE)
        if left:
            hit("M4", "P1", "bật Giảm chuyển động mà còn %d hoạt ảnh chạy: %s"
                % (len(left), ", ".join(sorted({a["name"] for a in left}))))
        page.evaluate("document.documentElement.dataset.motion='full'")

        # M5 — chuyển tab có mượt không: đo thời gian một lần đổi tab
        page.evaluate("gotoTab('tongquan')")
        page.wait_for_timeout(200)
        for tab in ["rang", "hoso", "lichsu", "kho", "caidat", "tongquan"]:
            ms = page.evaluate(
                "(t)=>{const a=performance.now();gotoTab(t);"
                "document.body.getBoundingClientRect();return performance.now()-a;}", tab)
            if ms > 60:
                hit("M5", "P2", "đổi sang tab %s khoá luồng %d ms (>60 ms là thấy khựng)"
                    % (tab, round(ms)))

        # ══ H · HIỂN THỊ ════════════════════════════════════════════════════
        for theme in ["light", "dark"]:
            page.evaluate("(t)=>setTheme(t)", theme)
            for tab in ["tongquan", "rang", "hoso", "lichsu", "kho", "caidat"]:
                page.evaluate("(t)=>gotoTab(t)", tab)
                if tab == "rang":
                    snap(page)
                page.wait_for_timeout(150)
                d = page.evaluate(JS_DISPLAY)
                for x in d["nan"]:
                    hit("H1", "P1", "[%s/%s] ô số hỏng %s → %r"
                        % (theme, tab, x["sel"], x["txt"]))
                for x in d["clip"]:
                    hit("H2", "P3", "[%s/%s] chữ bị cắt %d px không có dấu …: %s %r"
                        % (theme, tab, x["cut"], x["sel"], x["txt"]))
                for c in page.evaluate(JS_CONTRAST, 4.5):
                    hit("H3", "P2",
                        "[%s/%s] tương phản %.2f < %.1f (cỡ %dpx) %s %r"
                        % (theme, tab, c["ratio"], c["need"], c["px"], c["sel"], c["txt"]))
                for b in page.evaluate(JS_DISABLED):
                    hit("X1", "P3", "[%s/%s] nút khoá không nói lý do: %s %r"
                        % (theme, tab, b["sel"], b["txt"]))
        page.evaluate("setTheme('light')")

        # ══ S · ĐỒNG BỘ GIỮA CÁC TAB ════════════════════════════════════════
        # S1 — ĐỨNG YÊN ở Tổng quan trong lúc máy đổi nhiệt: khối chuẩn bị mẻ
        #      phải tự đổi, không đợi người dùng rời tab rồi quay lại.
        # Phải ở trạng thái TRƯỚC KHI NẠP mới đo được: để step trong dải CHARGE..DROP
        # là app vào mẻ, khối này hiện "Đang rang" và đứng yên — đúng, không phải lỗi.
        page.evaluate("""()=>{R.phase='IDLE';R._machRun=false;
          if(typeof loadProfile==='function')loadProfile(0);}""")
        page.evaluate("gotoTab('tongquan')")
        snap(page, bt=120.0, step=3, t_roast=0)
        page.wait_for_timeout(1400)
        before = page.evaluate(
            "()=>document.getElementById('ovPrep')?.textContent.replace(/\\s+/g,' ').trim()||''")
        snap(page, bt=205.0, step=3, t_roast=0)
        page.wait_for_timeout(1400)          # qua ít nhất một nhịp uxTick 1 s
        after = page.evaluate(
            "()=>document.getElementById('ovPrep')?.textContent.replace(/\\s+/g,' ').trim()||''")
        did("S1", "truoc=%r | sau=%r" % (before[-60:], after[-60:]))
        if before and before == after:
            hit("S1", "P1",
                "đứng ở Tổng quan, BT đổi 120→205°C mà khối Chuẩn bị mẻ KHÔNG đổi chữ "
                "(chỉ vẽ lại lúc vào tab): %r" % before[:90])

        # S2 — cùng một con số phải khớp ở mọi nơi nó xuất hiện
        snap(page, bt=188.8, gas=37)
        page.wait_for_timeout(300)
        vals = page.evaluate("""()=>{
          const g=id=>{const e=document.getElementById(id);return e?e.textContent.trim():null;};
          return {ovBurner:g('ovBurner'),ovAir:g('ovAir'),ovDrum:g('ovDrum'),
                  chip:document.getElementById('cnStMach')?.className||''};
        }""")
        did("S2", "ovBurner=%r" % vals["ovBurner"])
        if vals["ovBurner"] not in (None, "37"):
            hit("S2", "P2", "gas máy = 37 nhưng ô ovBurner hiện %r" % vals["ovBurner"])

        # S3 — sửa hồ sơ ở tab Hồ sơ rồi sang Rang: tên/nhiệt phải theo bản mới.
        # PHẢI ra khỏi mẻ trước: đang rang thì loadProfile() từ chối đổi hồ sơ —
        # đó là chốt an toàn ĐÚNG, không phải lỗi đồng bộ.
        page.evaluate("()=>{R.phase='IDLE';R._machRun=false;}")
        snap(page, step=3, t_roast=0)
        page.evaluate("gotoTab('hoso')")
        page.wait_for_timeout(200)
        renamed = page.evaluate("""()=>{
          const ps=loadProfiles(); if(!ps.length)return null;
          const old=ps[0].name; ps[0].name='ĐỔI TÊN KIỂM TRA'; saveProfiles(ps);
          if(typeof renderProfiles==='function')renderProfiles();
          return old;
        }""")
        if renamed:
            page.evaluate("(i)=>{if(typeof loadProfile==='function')loadProfile(0);}", 0)
            page.evaluate("gotoTab('rang')")
            page.wait_for_timeout(700)
            shown = page.evaluate(
                "()=>document.getElementById('matchProfile')?.textContent.trim()||''")
            did("S3", "tên cũ=%r · màn Rang hiện=%r" % (renamed, shown))
            if shown and "ĐỔI TÊN KIỂM TRA" not in shown and shown != "Chưa chọn hồ sơ":
                hit("S3", "P2",
                    "đổi tên hồ sơ ở tab Hồ sơ, màn Rang vẫn hiện tên cũ %r" % shown)

        # S4 — mất kết nối: MỌI tab phải cùng bỏ số cũ, không tab nào giữ số ma
        page.evaluate("()=>{window.__st='error';window.__snap=null;"
                      "DS.state='error';DS.snap=null;renderLinkChip();updateRoastLive();}")
        page.wait_for_timeout(1400)
        stale = page.evaluate("""()=>{
          const bad=[];
          for(const id of ['ovBurner','ovAir','ovDrum','liveBT','liveET']){
            const e=document.getElementById(id);
            if(e&&e.textContent.trim()!=='—')bad.push(id+'='+e.textContent.trim());
          }
          return bad;
        }""")
        did("S4", "còn số cũ: %s" % (stale or "không"))
        if stale:
            hit("S4", "P1", "mất kết nối mà vẫn còn số cũ trên màn: %s" % ", ".join(stale))

        # S5 — cuộn giữa bảng Lịch sử, đi tab khác rồi quay lại: mất chỗ đang đọc
        page.evaluate("()=>{window.__st='connected';DS.state='connected';DS.snap=null;}")
        page.evaluate("gotoTab('lichsu')")
        page.wait_for_timeout(500)
        moved = page.evaluate("""()=>{
          const sc=[...document.querySelectorAll('#pane-lichsu *')]
            .find(e=>e.scrollHeight-e.clientHeight>80);
          if(!sc)return null;
          sc.scrollTop=Math.min(200,sc.scrollHeight-sc.clientHeight);
          return {sel:sc.id||sc.className,top:sc.scrollTop};}""")
        if moved and moved["top"] > 0:
            page.evaluate("gotoTab('kho')")
            page.wait_for_timeout(250)
            page.evaluate("gotoTab('lichsu')")
            page.wait_for_timeout(400)
            back = page.evaluate("""()=>{
              const sc=[...document.querySelectorAll('#pane-lichsu *')]
                .find(e=>e.scrollHeight-e.clientHeight>80);
              return sc?sc.scrollTop:null;}""")
            did("S5", "cuộn %d → quay lại %s" % (moved["top"], back))
            if back == 0:
                hit("S5", "P3", "cuộn tới %d px trong Lịch sử, đi tab khác rồi quay lại "
                    "là nhảy về đầu bảng — mất chỗ đang đọc" % moved["top"])

        # X2 — đi bằng bàn phím: phần tử đang chọn phải THẤY được viền
        page.evaluate("gotoTab('tongquan')")
        page.wait_for_timeout(200)
        # :focus-visible KHÔNG bật khi gọi el.focus() bằng script — phải bấm Tab
        # thật, nếu không là báo oan cả loạt nút vốn có viền đàng hoàng.
        page.evaluate("()=>document.body.focus()")
        noring = []
        for _ in range(14):
            page.keyboard.press("Tab")
            r = page.evaluate("""()=>{
              const b=document.activeElement;
              if(!b||b===document.body||!b.getBoundingClientRect().width)return null;
              const s=getComputedStyle(b);
              const ring=(s.outlineStyle!=='none'&&parseFloat(s.outlineWidth)>0)||
                         (s.boxShadow!=='none'&&/\\d/.test(s.boxShadow));
              return ring?null:(b.id||(b.textContent||'').trim().slice(0,24)||b.tagName);}""")
            if r and r not in noring:
                noring.append(r)
        did("X2", "%d nút không có viền chọn" % len(noring))
        if noring:
            hit("X2", "P2", "đi bằng bàn phím không thấy phần tử đang chọn ở %d nút: %s"
                % (len(noring), ", ".join(noring[:6])))

        # M6 — KHỰNG KHI ĐANG RANG: đẩy 6 gói dữ liệu như máy thật rồi đo tác vụ dài
        page.evaluate("gotoTab('rang')")
        snap(page)
        page.evaluate("""()=>{window.__long=[];
          try{new PerformanceObserver(l=>{for(const e of l.getEntries())
            window.__long.push(Math.round(e.duration));}).observe({entryTypes:['longtask']});}
          catch(e){window.__long=null;}}""")
        for i in range(6):
            snap(page, bt=180 + i * 2.5, t_roast=240 + i, gas=40 + i)
            page.wait_for_timeout(400)
        longs = page.evaluate("()=>window.__long")
        did("M6", "tác vụ dài: %s" % (longs if longs else "không có"))
        if longs:
            hit("M6", "P2", "trong 3 s rang có %d tác vụ khoá luồng >50 ms (%s ms) — "
                "màn giật lúc thợ đang chỉnh gas" % (len(longs), ", ".join(map(str, longs[:6]))))

        # H4 — chỉ báo có CHẤM MÀU phải sống sót qua các nhịp vẽ lại. Ghi bằng
        # textContent là xoá chấm, mọi luật CSS bám vào `.d` thành vô hiệu mà
        # không ai thấy: không lỗi, không cảnh báo, chỉ mất chỉ báo.
        page.evaluate("gotoTab('tongquan')")
        page.wait_for_timeout(1500)
        dots = page.evaluate("""()=>{
          const bad=[];
          for(const id of ['phStatus','cnStMach']){
            const e=document.getElementById(id);
            if(e&&!e.querySelector('.d'))bad.push(id);}
          return bad;}""")
        did("H4", "chỉ báo mất chấm: %s" % (dots or "không"))
        for x in dots:
            hit("H4", "P3", "chỉ báo #%s mất chấm màu sau khi vẽ lại — "
                "luật CSS theo trạng thái không còn chỗ bám" % x)

        # X3 — trạng thái RỖNG: bảng không có dữ liệu phải nói ra, không để trắng trơn
        empt = page.evaluate("""()=>{
          const bad=[];
          for(const id of ['pane-lichsu','pane-kho']){
            const pane=document.getElementById(id);
            for(const tb of pane.querySelectorAll('tbody')){
              const r=tb.getBoundingClientRect();
              if(!tb.children.length&&r.width>0)bad.push(id+' '+(tb.closest('table')?.id||''));
            }}
          return bad;}""")
        for e in empt:
            hit("X3", "P3", "bảng rỗng không có dòng báo 'chưa có dữ liệu': %s" % e)

        if errs:
            hit("JS", "P1", "lỗi JavaScript khi chạy: %s" % "; ".join(errs[:4]))
        browser.close()

    # ── in kết quả ──────────────────────────────────────────────────────────
    order = {"P1": 0, "P2": 1, "P3": 2}
    found.sort(key=lambda x: (order.get(x[1], 9), x[0]))
    print("Kịch bản dựng được (%d):" % len(ran))
    for code, note in ran:
        print("  %-3s %s" % (code, note))
    if notes:
        print("")
        print("Ghi nhan - da can nhac, CO Y khong doi (%d):" % len(notes))
        for code, _lv, msg in sorted(notes):
            print("  %-3s %s" % (code, msg))
    print("")
    if not found:
        print("ĐẠT: không thấy lỗi chuyển động / hiển thị / đồng bộ tab.")
        return 0
    print("Phát hiện %d mục:\n" % len(found))
    last = None
    for code, lvl, msg in found:
        if code != last:
            print("")
            last = code
        print("  %-3s %s  %s" % (code, lvl, msg))
    print("\nTổng: %d (P1=%d P2=%d P3=%d)" % (
        len(found), *[sum(1 for f in found if f[1] == k) for k in ("P1", "P2", "P3")]))
    return 0 if report_only else 1


if __name__ == "__main__":
    sys.exit(main())
