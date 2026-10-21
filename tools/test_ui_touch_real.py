"""Bộ kiểm đợt 15 (14/09/2026) — CẢM ỨNG THẬT + chuột/phím + tablet.
Kế hoạch + bằng chứng: docs/ui/2026-09-14-tho-rang-tablet-tiep-codex.md.

Ngón tay = CDP `Input.dispatchTouchEvent`: có "implicit pointer capture" y như màn cảm ứng thật. KHÔNG
dùng pg.mouse hay PointerEvent tổng hợp — chính vì vậy mà 32 bộ kiểm cũ xanh trong khi giữ "Kết thúc mẻ"
rồi trượt ngón vẫn mở cửa xả.
  1) Kết thúc mẻ / Xả liệu: ngón trượt ra khỏi nút → 0 lệnh; giữ đúng chỗ → có lệnh (đối chứng)
  2) ± gas: ngón giữ rồi trượt ra → dừng, không ghi thêm; giữ đúng chỗ vẫn tự lặp (đối chứng)
  3) ± hộp Sửa hồ sơ: ngón giữ rồi trượt ra → số đứng yên
  4) Tạm dừng: nối máy → không "đã dừng" giả, không ghi nhật ký, có toast + dòng phụ; mô phỏng vẫn dừng
  5) Mốc DROP: máy tự mở cửa xả / app ra lệnh xả / HMI xả → đều có DROP trong tổng kết + mile gửi kho
  6) Lăn chuột + ↑/↓ trên ô gas: số đúng, máy nhận ≤ 1 lệnh/giây
  7) Esc lúc đang rang / tổng kết không thu toàn màn; lúc chờ thì có
  8) Phím M lúc đang rang = nút Ghi mốc
  9) Tablet 1280×720@1,5: chữ < 12px thật; thanh đầu không chồng; vùng chạm chú giải ≥ 44px thật;
     toast tổng kết không đè tab
Chạy trên bản sao lưu để chứng minh bộ kiểm bắt được lỗi: python tools/test_ui_touch_real.py <đường dẫn html>
"""
import sys, re, pathlib
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

TOOLS = pathlib.Path(__file__).resolve().parent
HTML = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else TOOLS.parent / "OTL Roast Lab.html"
SRC = (TOOLS / "test_ui_review_0914.py").read_text(encoding="utf-8")
STUB = re.search(r'STUB = r"""(.*?)"""', SRC, re.S).group(1)
HELPERS = re.search(r'HELPERS = r"""(.*?)"""', SRC, re.S).group(1)
EXTRA = """window.__fs=0; window.__fsSt=[]; window.pywebview.api.toggle_fullscreen=()=>{window.__fs++;
  window.__fsSt.push(((typeof R==='object'&&R)?R.phase:'?')+' @ '+String(new Error().stack).split(String.fromCharCode(10)).slice(2,4).join(' | '));};"""
RAMP = """([a,b])=>{for(let t=a;t<=b;t+=2){const bt=t<80?180-t*1.1:92+(t-80)*.27;
  window.feed({step:t<80?6:t<300?7:t<480?8:9,t_roast:t,bt,et:bt+28,gas:40});}}"""

fails = []


def chk(name, cond, got=""):
    print(("  OK   " if cond else "  FAIL ") + name + (f"  → {got}" if got != "" else ""))
    if not cond:
        fails.append(name)


def mo(p, w=1280, h=720, dsf=1.5, touch=True, stub=True):
    br = p.chromium.launch()
    ctx = br.new_context(viewport={"width": w, "height": h}, device_scale_factor=dsf, has_touch=touch)
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
    if stub:
        pg.add_init_script(STUB)
    pg.goto(HTML.as_uri())
    pg.wait_for_function("typeof finishRoast==='function'")
    pg.evaluate("session={name:'Thợ',role:'master',perms:{}};document.getElementById('login').classList.remove('on');"
                "try{updateBadge()}catch(e){};try{SND.on=false}catch(e){}")
    if stub:
        pg.evaluate(EXTRA)
        pg.evaluate(f"({HELPERS})()")
    return br, ctx, pg, errs


def dang_rang(pg, t_end=300):
    pg.evaluate("()=>{gotoTab('rang');loadProfile(0);window.feed({step:0,t_roast:0,bt:180,et:205});startRoast();}")
    pg.wait_for_timeout(150)
    pg.evaluate("()=>window.feed({step:6,t_roast:1,bt:180,et:205},{charge:true})")
    pg.evaluate(RAMP, [2, t_end])
    pg.wait_for_timeout(250)


def tam(pg, sel):
    bb = pg.locator(sel).first.bounding_box()
    return bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2


def ngon(cdp, kieu, x, y, i=7):
    cdp.send("Input.dispatchTouchEvent", {"type": kieu, "touchPoints": [] if kieu == "touchEnd" else [{"x": x, "y": y, "id": i}]})


def ngon_truot_ra(pg, cdp, sel, giu_truoc=100, giu_sau=1500, dy=150):
    x, y = tam(pg, sel)
    ngon(cdp, "touchStart", x, y); pg.wait_for_timeout(giu_truoc)
    for d in (40, 100, dy):
        ngon(cdp, "touchMove", x, y - d); pg.wait_for_timeout(40)
    pg.wait_for_timeout(giu_sau)
    ngon(cdp, "touchEnd", 0, 0); pg.wait_for_timeout(300)


with sync_playwright() as p:
    print("1) Nút GIỮ-để-xác-nhận bằng ngón thật")
    for sel, lenh in (("#btnDrop", "drop"), ("#btnEscape", "escape")):
        br, ctx, pg, errs = mo(p); dang_rang(pg); cdp = ctx.new_cdp_session(pg)
        n0 = len(pg.evaluate("window.__sent"))
        ngon_truot_ra(pg, cdp, sel)
        s = [c for c in pg.evaluate("window.__sent")[n0:] if c[0] == lenh]
        chk(f"{sel}: chạm rồi trượt ngón ra, đè thêm 1,5s → KHÔNG gửi {lenh}", s == [], s)
        chk(f"{sel}: nhãn trở về, không kẹt 'Đang giữ'", "holding" not in (pg.locator(sel).get_attribute("class") or ""))
        x, y = tam(pg, sel)
        ngon(cdp, "touchStart", x, y); pg.wait_for_timeout(1400); ngon(cdp, "touchEnd", 0, 0); pg.wait_for_timeout(300)
        s = [c for c in pg.evaluate("window.__sent")[n0:] if c[0] == lenh]
        chk(f"{sel}: đối chứng — giữ đúng chỗ vẫn gửi {lenh}", len(s) == 1, s)
        br.close()

    print("2) ± gas bằng ngón thật")
    br, ctx, pg, errs = mo(p); dang_rang(pg); cdp = ctx.new_cdp_session(pg)
    sel = '.pm[data-out="burner"][data-d="-1"]'
    x, y = tam(pg, sel)
    ngon(cdp, "touchStart", x, y); pg.wait_for_timeout(700)
    for d in (40, 100, 150):
        ngon(cdp, "touchMove", x, y + d); pg.wait_for_timeout(40)
    v_ra = pg.locator("#ovBurner").text_content(); n_ra = len(pg.evaluate("window.__sent"))
    pg.wait_for_timeout(1000)
    v_sau = pg.locator("#ovBurner").text_content(); gui_sau = pg.evaluate("window.__sent")[n_ra:]
    ngon(cdp, "touchEnd", 0, 0); pg.wait_for_timeout(400)
    chk("giữ Gas − rồi trượt ra: số đứng yên suốt 1s ngón vẫn đè", v_sau == v_ra, (v_ra, v_sau))
    chk("… và không ghi thêm lệnh gas nào", [c for c in gui_sau if c[0] == "gas"] == [], gui_sau)
    v0 = int(pg.locator("#ovBurner").text_content())
    x, y = tam(pg, '.pm[data-out="burner"][data-d="1"]')
    ngon(cdp, "touchStart", x, y); pg.wait_for_timeout(1500); ngon(cdp, "touchEnd", 0, 0); pg.wait_for_timeout(500)
    v1 = int(pg.locator("#ovBurner").text_content())
    chk("đối chứng — giữ Gas + đúng chỗ 1,5s vẫn tự lặp tăng tốc", v1 - v0 >= 8, (v0, v1))
    chk("không lỗi JS (±)", not errs, errs[:2])
    br.close()

    print("3) ± hộp Sửa hồ sơ bằng ngón thật")
    br, ctx, pg, errs = mo(p)
    pg.evaluate("()=>{gotoTab('hoso');editProfile(0);}"); pg.wait_for_timeout(500)
    b = pg.locator('#profedit .pestep[data-pestep="temp"] .fpm[data-d="1"]').first
    if b.count() == 0:
        b = pg.locator("#profedit .pestep .fpm[data-d='1']").first
    b.scroll_into_view_if_needed(); pg.wait_for_timeout(200)
    key = b.evaluate("e=>e.closest('.pestep').dataset.pestep")
    cdp = ctx.new_cdp_session(pg)
    bb = b.bounding_box(); x, y = bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2
    ngon(cdp, "touchStart", x, y); pg.wait_for_timeout(700)
    for d in (40, 100, 150):
        ngon(cdp, "touchMove", x - d, y); pg.wait_for_timeout(40)
    v_ra = pg.evaluate(f"String(peTmp[{key!r}])"); pg.wait_for_timeout(1000)
    v_sau = pg.evaluate(f"String(peTmp[{key!r}])")
    ngon(cdp, "touchEnd", 0, 0)
    chk(f"ô '{key}': giữ + rồi trượt ra → số đứng yên", v_ra == v_sau, (v_ra, v_sau))
    br.close()

    print("4) Tạm dừng")
    br, ctx, pg, errs = mo(p, touch=False, dsf=1.0, w=1920, h=1080); dang_rang(pg)
    pg.evaluate("()=>{window.__ol=[];const o=opLog;opLog=function(a,b){window.__ol.push(a+' '+b);return o.apply(this,arguments);};}")
    pg.locator("#pauseBtn").click(); pg.wait_for_timeout(200)
    pg.evaluate(RAMP, [302, 330]); pg.wait_for_timeout(200)
    r = pg.evaluate("""()=>({paused:R.paused, cls:document.getElementById('pane-rang').classList.contains('paused'),
      lock:document.getElementById('pauseBtn').classList.contains('machlock'), sub:document.getElementById('pauseSub').textContent,
      toast:document.getElementById('toast').textContent, ol:window.__ol.filter(x=>/tạm dừng/.test(x)), el:R.elapsed})""")
    chk("nối máy: bấm Tạm dừng KHÔNG thành 'đã tạm dừng'", r["paused"] is False and r["cls"] is False, r)
    chk("nối máy: không ghi nhật ký 'tạm dừng'", r["ol"] == [], r["ol"])
    chk("nối máy: nút mờ + dòng phụ 'máy đang lái mẻ'", r["lock"] is True and "máy đang lái" in r["sub"], r["sub"])
    chk("nối máy: toast nói vì sao", "không tạm dừng được máy" in r["toast"], r["toast"])
    br.close()
    br, ctx, pg, errs = mo(p, touch=False, dsf=1.0, w=1920, h=1080, stub=False)
    pg.evaluate("()=>{gotoTab('rang');loadProfile(0);startRoast();}"); pg.wait_for_timeout(300)
    ph = pg.evaluate("R.phase")
    if ph == "RUNNING":
        pg.evaluate("togglePause()")
        chk("mô phỏng (không cầu nối): Tạm dừng vẫn dừng đồng hồ", pg.evaluate("R.paused") is True)
    else:
        chk("mô phỏng: vào được mẻ để thử Tạm dừng", False, ph)
    br.close()

    print("5) Mốc DROP khi mẻ chốt theo cờ cửa xả")
    for kieu in ("máy tự mở cửa xả", "app ra lệnh xả", "HMI xả (step nhảy 11)"):
        br, ctx, pg, errs = mo(p, touch=False, dsf=1.0, w=1920, h=1080); dang_rang(pg, 560)
        if kieu == "app ra lệnh xả":
            pg.evaluate("()=>{cmdDrop();}"); pg.wait_for_timeout(300)
        if kieu.startswith("HMI"):
            pg.evaluate("()=>window.feed({step:11,t_roast:562,bt:204,et:228},{cool:true})")
        else:
            pg.evaluate("()=>window.feed({step:9,t_roast:562,bt:204,et:230},{drop:true})"); pg.wait_for_timeout(400)
            pg.evaluate("()=>window.feed({step:11,t_roast:564,bt:200,et:228},{drop:true,cool:true})")
        pg.wait_for_timeout(1200)
        r = pg.evaluate("""()=>({ph:R.phase, drop:R.mileT.DROP??null, mile:((window.__finish[0]||{}).mile||{}).DROP||null,
          o:(document.getElementById('done_DROP')||{}).textContent||''})""")
        chk(f"{kieu}: DONE + mốc DROP có trong tổng kết và mile gửi kho",
            r["ph"] == "DONE" and r["drop"] is not None and r["mile"] is not None and r["o"] not in ("", "—"), r)
        br.close()

    print("6) Lăn chuột + ↑/↓ trên ô gas")
    br, ctx, pg, errs = mo(p, touch=False, dsf=1.0, w=1920, h=1080); dang_rang(pg)
    v0 = int(pg.locator("#ovBurner").text_content()); n0 = len(pg.evaluate("window.__sent"))
    x, y = tam(pg, "#ovBurner"); pg.mouse.move(x, y)
    pg.evaluate("()=>{window.__gasT=[];const o=window.pywebview.api.link_write;window.pywebview.api.link_write=async(n,v)=>{if(n==='gas')window.__gasT.push(performance.now());return o(n,v);};}")
    for _ in range(10):
        pg.mouse.wheel(0, -100); pg.wait_for_timeout(40)
    v_ngay = int(pg.locator("#ovBurner").text_content())
    pg.wait_for_timeout(900)
    gas = [c for c in pg.evaluate("window.__sent")[n0:] if c[0] == "gas"]
    t = pg.evaluate("window.__gasT")
    khoang = [round(b - a) for a, b in zip(t, t[1:])]
    chk("lăn lên 10 nấc → gas +10 ngay trên màn", v_ngay - v0 == 10, (v0, v_ngay))
    chk("10 nấc gom lại: ít lệnh hơn hẳn số nấc, lệnh cuối = giá trị cuối", 1 <= len(gas) <= 4 and gas[-1][1] == v_ngay, gas)
    # Lệnh chốt cuối (ngừng tay 0,35s) được phép sát lệnh trước; các lệnh giữa chừng phải cách ≥ ~1 giây.
    chk("lệnh giữa chừng cách nhau ≥ 1 giây (hãm nhịp như nút ±)", all(k >= 950 for k in khoang[:-1]), khoang)
    pg.locator('.pm[data-out="burner"][data-d="1"]').focus()
    for _ in range(3):
        pg.keyboard.press("ArrowDown"); pg.wait_for_timeout(30)
    pg.wait_for_timeout(500)
    chk("↓ 3 lần khi tiêu điểm ở ô gas → −3", int(pg.locator("#ovBurner").text_content()) == v_ngay - 3, pg.locator("#ovBurner").text_content())

    print("7–8) Esc và phím M")
    pg.evaluate("()=>{window.__mk=0;const o=mileSetEdit;mileSetEdit=function(){window.__mk++;return o.apply(this,arguments);};}")
    pg.evaluate("document.activeElement&&document.activeElement.blur()")
    pg.keyboard.press("m"); pg.wait_for_timeout(200)
    chk("phím M lúc đang rang = bấm Ghi mốc", pg.evaluate("window.__mk") == 1, pg.evaluate("window.__mk"))
    pg.evaluate("()=>{document.querySelectorAll('.overlay.on').forEach(o=>o.classList.remove('on'));}")
    pg.evaluate("window.__fs=0;window.__fsSt=[]")
    pg.keyboard.press("Escape"); pg.wait_for_timeout(100)
    chk("Esc lúc đang rang KHÔNG thu toàn màn", pg.evaluate("window.__fs") == 0,
        (pg.evaluate("R.phase"), pg.evaluate("window.__fsSt")))
    br.close()
    br, ctx, pg, errs = mo(p, touch=False, dsf=1.0, w=1920, h=1080)
    pg.evaluate("gotoTab('rang')"); pg.wait_for_timeout(100)
    pg.evaluate("window.__fs=0;window.__fsSt=[]")
    pg.keyboard.press("Escape"); pg.wait_for_timeout(100)
    chk("Esc lúc chưa rang vẫn bật/tắt toàn màn như cũ", pg.evaluate("window.__fs") == 1,
        (pg.evaluate("R.phase"), pg.evaluate("window.__fsSt")))
    br.close()

    print("9) Tablet 1280×720 @150%")
    br, ctx, pg, errs = mo(p); dang_rang(pg)
    r = pg.evaluate(r"""() => { const st=document.getElementById('stage'); const k=st.getBoundingClientRect().width/st.offsetWidth;
      const w=document.createTreeWalker(document.getElementById('pane-rang'),NodeFilter.SHOW_TEXT); const nho=new Set(); let n;
      while(n=w.nextNode()){ const s=n.textContent.trim(); if(!s)continue; const e=n.parentElement;
        if(!e.checkVisibility({checkOpacity:true,checkVisibilityCSS:true}))continue; const r=e.getBoundingClientRect();
        if(!r.width||r.bottom<0||r.top>innerHeight)continue;
        if(parseFloat(getComputedStyle(e).fontSize)*k<11.5)nho.add(s.slice(0,20)); }
      const a=document.getElementById('linkLbl').getBoundingClientRect(), c=document.getElementById('clock').getBoundingClientRect();
      const chong=Math.min(a.right,c.right)-Math.max(a.left,c.left)>1&&Math.min(a.bottom,c.bottom)-Math.max(a.top,c.top)>1;
      const leg=[...document.querySelectorAll('#pane-rang .chartleg .lg')].filter(e=>e.checkVisibility());
      const lech=leg.map(e=>{const r=e.getBoundingClientRect(); const x=r.left+r.width/2, y=r.top-((44-r.height)/2)+3;
        const t=document.elementFromPoint(x,y); return t&&e.contains(t)||t===e;});
      return {nho:[...nho], chong, legend_trung_mep:lech}; }""")
    chk("màn Rang đang rang: không còn chữ < 11,5px thật", len(r["nho"]) == 0, r["nho"][:12])
    chk("thanh đầu: chữ trạng thái máy không chồng đồng hồ", r["chong"] is False)
    chk("chú giải đồ thị: chạm cách mép trên (44px thật) vẫn trúng", len(r["legend_trung_mep"]) > 0 and all(r["legend_trung_mep"]), r["legend_trung_mep"])
    pg.evaluate(RAMP, [302, 560]); pg.evaluate("()=>window.feed({step:11,t_roast:562,bt:204,et:228},{cool:true})")
    pg.wait_for_timeout(1000)
    pg.evaluate("()=>toast('Đã lưu curve vào hồ sơ \"Brazil Cerrado\"',true)"); pg.wait_for_timeout(300)
    r = pg.evaluate("""()=>{const t=document.getElementById('toast').getBoundingClientRect();
      return [...document.querySelectorAll('#tabnav .tab,#topbar .brand')].filter(e=>{const r=e.getBoundingClientRect();
        return Math.min(r.right,t.right)-Math.max(r.left,t.left)>1&&Math.min(r.bottom,t.bottom)-Math.max(r.top,t.top)>1;}).map(e=>e.textContent.trim())}""")
    chk("tổng kết: toast không đè tab / logo", r == [], r)
    r = pg.evaluate("""()=>{const box=document.querySelector('.roast-done').getBoundingClientRect();
      return {nut:[...document.querySelectorAll('.rd-actions button')].every(e=>{const r=e.getBoundingClientRect();
                return r.height>0&&r.top>=box.top-1&&r.bottom<=box.bottom+1;}),
              hang:new Set([...document.querySelectorAll('.rd-m')].map(e=>Math.round(e.getBoundingClientRect().top))).size}}""")
    chk("tổng kết tablet: 5 ô mốc một hàng, 'Về Tổng quan · Mẻ mới' nằm trong khung (không bị đẩy khuất)",
        r["nut"] is True and r["hang"] == 1, r)
    chk("không lỗi JS (tablet)", not errs, errs[:2])
    br.close()

print("\nKẾT QUẢ:", "ĐẠT hết" if not fails else f"{len(fails)} mục TRƯỢT: {fails}")
sys.exit(1 if fails else 0)
