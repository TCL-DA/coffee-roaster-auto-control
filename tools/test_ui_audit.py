# -*- coding: utf-8 -*-
"""Soát giao diện app OTL Roast Lab — ĐO thật, không nhìn bằng mắt.

Chạy:  python tools/test_ui_audit.py              (đủ bộ, cần playwright)
       python tools/test_ui_audit.py --keys-only  (chỉ kiểm từ điển, không cần trình duyệt)

Bốn phép kiểm, mỗi phép ứng với một lỗi ĐÃ TỪNG xảy ra thật:

1. Từ điển i18n  — data-i18n trỏ vào khoá không tồn tại thì applyLang() bỏ qua
   IM LẶNG, chữ vẫn là tiếng Việt mà không ai biết (đã dính ketnoi.mach, maycfg.lead).
2. Sót tiếng Việt — bật tiếng Anh rồi quét dấu tiếng Việt còn trên màn hình
   (đã từng sót 47 chuỗi; khách nước ngoài nhìn thấy hết).
3. Tràn / đè    — ô lưới và flex-item mặc định min-width:auto nên KHÔNG co được:
   hộp nhập tràn khỏi cột che mất đơn vị (trang Cài đặt máy), tên hồ sơ dài không
   dấu cách thổi bung cột (trang Hồ sơ).
4. Nút quá nhỏ  — máy rang bấm bằng găng tay, dưới 44px là khó trúng.
"""
import sys, io, re, pathlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parent.parent
APP = ROOT / "OTL Roast Lab.html"
TAP = 44  # ngưỡng bấm bằng găng tay (px, ở cỡ màn thiết kế)


def kiem_tu_dien(src):
    """Không cần trình duyệt: đối chiếu khoá dùng <-> khoá có."""
    i = src.index("const I18N={vi:{")
    j = src.index(" en:{", i)
    k = src.index("};", j)
    vi = set(re.findall(r"'([A-Za-z0-9._]+)':", src[i:j]))
    en = set(re.findall(r"'([A-Za-z0-9._]+)':", src[j:k]))
    used = set(re.findall(r'data-i18n="([^"]+)"', src))
    treo, thieu = sorted(used - vi), sorted(vi - en)
    dvi = dict(re.findall(r"'([A-Za-z0-9._]+)':'([^']*)'", src[i:j]))
    den = dict(re.findall(r"'([A-Za-z0-9._]+)':'([^']*)'", src[j:k]))
    lech = sorted(x for x in vi & en
                  if ("{n}" in dvi.get(x, "")) != ("{n}" in den.get(x, "")))
    print("  khoá vi=%d en=%d · data-i18n dùng=%d" % (len(vi), len(en), len(used)))
    for ten, ds in (("data-i18n trỏ vào khoá KHÔNG CÓ", treo),
                    ("khoá THIẾU bản tiếng Anh", thieu),
                    ("chỗ giữ {n} lệch giữa 2 bản", lech)):
        print("  %s: %s" % (ten, ", ".join(ds) if ds else "không có"))
    return not (treo or thieu or lech)


PROBE = r"""
() => {
  const out={overflow:[],overlap:[],small:[]};
  const vis=el=>{const s=getComputedStyle(el);
    if(s.display==='none'||s.visibility==='hidden'||+s.opacity===0)return false;
    const r=el.getBoundingClientRect();return r.width>0&&r.height>0;};
  const path=el=>{let p=[],n=el,i=0;while(n&&n.nodeType===1&&i++<3){let s=n.tagName.toLowerCase();
    if(n.id)s+='#'+n.id;else if(n.className&&typeof n.className==='string')
      s+='.'+n.className.trim().split(/\s+/)[0];p.unshift(s);n=n.parentElement;}return p.join('>');};
  const txt=el=>(el.textContent||'').trim().replace(/\s+/g,' ').slice(0,44);
  const all=[...document.querySelectorAll('body *')].filter(vis);
  for(const el of all){
    const s=getComputedStyle(el);
    if(s.position!=='static'&&s.position!=='relative')continue;
    if(el.closest('svg'))continue;   // <use> báo kích thước symbol, không phải kích thước vẽ
    const p=el.parentElement;if(!p||p===document.body)continue;
    const ps=getComputedStyle(p);
    if(ps.overflowX==='auto'||ps.overflowX==='scroll')continue;
    const r=el.getBoundingClientRect(),pr=p.getBoundingClientRect();
    const d=Math.round(r.right-pr.right);
    if(d>2&&pr.width>0)out.overflow.push({sel:path(el),over:d,txt:txt(el)});
  }
  for(const c of all.filter(e=>['grid','flex'].includes(getComputedStyle(e).display))){
    const st=k=>getComputedStyle(k).position;
    const kids=[...c.children].filter(vis).filter(k=>st(k)==='static'||st(k)==='relative');
    for(let i=0;i<kids.length;i++)for(let j=i+1;j<kids.length;j++){
      const a=kids[i].getBoundingClientRect(),b=kids[j].getBoundingClientRect();
      const ox=Math.min(a.right,b.right)-Math.max(a.left,b.left);
      const oy=Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top);
      if(ox>3&&oy>3)out.overlap.push({cont:path(c),a:txt(kids[i]),b:txt(kids[j]),
                                      dx:Math.round(ox),dy:Math.round(oy)});
    }
  }
  for(const el of document.querySelectorAll('button,input,select,[role=button]')){
    if(!vis(el))continue;const r=el.getBoundingClientRect();
    if(r.height<__TAP__||r.width<__TAP__)
      out.small.push({sel:path(el),w:Math.round(r.width),h:Math.round(r.height),txt:txt(el)});
  }
  return out;
}
"""

VN_CHARS = ("ăâđêôơưĂÂĐÊÔƠƯáàảãạắằẳẵặấầẩẫậéèẻẽẹếềểễệíìỉĩị"
            "óòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ")

VN_PROBE = r"""
(VN) => {
  const hits=[],seen=new Set();
  const vis=el=>{const s=getComputedStyle(el);
    if(s.display==='none'||s.visibility==='hidden'||+s.opacity===0)return false;
    const r=el.getBoundingClientRect();return r.width>0&&r.height>0;};
  const w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);let n;
  while(n=w.nextNode()){
    const t=(n.nodeValue||'').trim();if(!t)continue;
    if(![...t].some(c=>VN.includes(c)))continue;
    const el=n.parentElement;if(!el||!vis(el))continue;
    const k=t.slice(0,60);if(seen.has(k))continue;seen.add(k);
    hits.push(t.slice(0,64));
  }
  return hits;
}
"""

TABS_VI = ["Tổng quan", "Rang", "Hồ sơ", "Lịch sử", "Kho & Kinh doanh", "Cài đặt"]
TABS_EN = ["Overview", "Roast", "Profiles", "History", "Inventory & Business", "Settings"]


def dang_nhap(pg):
    """Trình duyệt trắng = lần chạy đầu -> app bắt đặt PIN, gõ 2 lần."""
    for _ in range(2):
        for d in "1111":
            pg.click("#loginPad button:has-text('%s')" % d)
            pg.wait_for_timeout(80)
        pg.wait_for_timeout(600)
    pg.wait_for_timeout(1600)


def kiem_giao_dien(vw, vh):
    from playwright.sync_api import sync_playwright
    loi = []
    probe = PROBE.replace("__TAP__", str(TAP))
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": vw, "height": vh})
        js_err = []
        pg.on("pageerror", lambda e: js_err.append(str(e)))
        pg.goto(APP.as_uri())
        pg.wait_for_timeout(2200)
        dang_nhap(pg)

        for lang, tabs in (("vi", TABS_VI), ("en", TABS_EN)):
            if pg.evaluate("() => LANG") != lang:
                pg.evaluate("() => toggleLang()")
                pg.wait_for_timeout(1200)
            for t in tabs:
                try:
                    pg.click('#tabnav button:has-text("%s")' % t, timeout=4000)
                except Exception:
                    loi.append("không mở được tab %s (%s)" % (t, lang))
                    continue
                pg.wait_for_timeout(1200)
                if lang == "en":
                    for s in pg.evaluate(VN_PROBE, VN_CHARS):
                        loi.append("[%s] còn tiếng Việt: «%s»" % (t, s))
                r = pg.evaluate(probe)
                for it in r["overlap"]:
                    loi.append("[%s] ĐÈ %dx%dpx «%s»<->«%s»"
                               % (t, it["dx"], it["dy"], it["a"][:20], it["b"][:20]))
                for it in r["overflow"]:
                    loi.append("[%s] TRÀN +%dpx «%s» %s"
                               % (t, it["over"], it["txt"][:26], it["sel"][-38:]))
                if lang == "vi" and r["small"]:
                    print("  (nhắc) %s: %d nút dưới %dpx — bấm bằng găng tay sẽ khó"
                          % (t, len(r["small"]), TAP))
        if js_err:
            loi += ["LỖI JS: %s" % e[:90] for e in js_err[:5]]
        b.close()
    return loi


def main():
    src = APP.read_text(encoding="utf-8")
    print("1) Từ điển i18n")
    ok = kiem_tu_dien(src)
    if "--keys-only" in sys.argv:
        print("\nĐẠT" if ok else "\nCÓ LỖI")
        return 0 if ok else 1
    print("\n2) Bố cục + sót tiếng Việt (1920x1080)")
    loi = kiem_giao_dien(1920, 1080)
    for l in loi:
        print("   " + l)
    ok = ok and not loi
    print("\nTẤT CẢ ĐẠT" if ok else "\nCÓ %d VẤN ĐỀ" % len(loi))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
