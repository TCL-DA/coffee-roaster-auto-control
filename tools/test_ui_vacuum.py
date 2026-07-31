"""Vacuum Control — điều khiển gió theo áp hút.

Bật lên thì hàng "gió" chỉnh ÁP HÚT ĐẶT (Pa) và gửi ô 'vac'; tắt thì chỉnh % gió và
gửi ô 'air' như cũ. Hai đường không được lẫn nhau — gửi cả hai là hai bộ điều khiển
giành cùng một cái quạt.
"""
import sys, pathlib
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

HTML = pathlib.Path(__file__).resolve().parent.parent / "OTL Roast Lab.html"

STUB = """
window.__sent = []; window.__mcw = [];
window.pywebview = { api: {
  link_write: async (n, v) => { window.__sent.push([n, v]); return {ok:true}; },
  mc_write:   async (items) => { window.__mcw.push(items); return {ok:true, count:items.length}; },
  link_snapshot: async () => ({state:'connected', mode:'pclink', data:{}}),
}};
"""

SETUP = """() => {
  CFG.dv_vacuum = '1'; CFG_EDIT.dv_vacuum = '1';
  CFG.vc_min='90'; CFG.vc_max='250'; CFG.vc_step='5'; CFG.vc_sp='120';
  DS.state='connected'; DS.mode='pclink';
  DS.snap={bt:180, et:200, gas:40, air:62, drum:55, vac:118, ror_bt:5, ror_et:4,
           step:6, t_roast:100, flags:{pc_control:true, flame:true}};
  R.mode='MANUAL'; R.vacMode=false; R.vacSp=null;
  applyVacVisibility();
  window.__sent=[]; window.__mcw=[];
}"""

fails = []
with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page()
    pg.add_init_script(STUB)
    pg.goto(HTML.as_uri())
    pg.wait_for_function("typeof vacModeToggle === 'function'")
    pg.evaluate(SETUP)

    def check(label, cond, extra=""):
        print(f"   {'OK  ' if cond else 'FAIL'} {label}{(' — ' + extra) if extra else ''}")
        if not cond: fails.append(label)

    print("1) Chưa bật — hàng gió gửi 'air' theo %")
    pg.evaluate("() => { window.__sent=[]; stepOut(document.querySelector('.outrow.air .pm[data-d=\\'1\\']')); }")
    pg.wait_for_timeout(200)
    sent = pg.evaluate("() => window.__sent")
    check("gửi ô 'air'", sent and sent[0][0] == 'air', str(sent))
    check("không gửi ô 'vac'", all(s[0] != 'vac' for s in sent), str(sent))

    print("2) Nút %/Pa hiện khi máy khai báo CÓ bộ hút")
    vis = pg.evaluate("() => getComputedStyle(document.getElementById('vcBtn')).display")
    check("nút hiện", vis != 'none', f"display={vis}")

    print("3) Bật chế độ áp hút — phải gửi ô 'vacen' = 1 rồi gửi setpoint mặc định")
    pg.evaluate("async () => { window.__sent=[]; window.__mcw=[]; await vacModeToggle(); }")
    pg.wait_for_timeout(300)
    sent = pg.evaluate("() => window.__sent")
    check("gửi vacen = 1", ('vacen', 1) in [tuple(s) for s in sent], str(sent))
    check("KHÔNG đi đường $M nữa", pg.evaluate("() => window.__mcw") == [], "phải dùng PC_Link")
    check("gửi vac = 120", ('vac', 120) in [tuple(s) for s in sent], str(sent))
    check("nhãn đơn vị thành Pa",
          pg.evaluate("() => document.getElementById('airUnit').textContent") == 'Pa')

    print("4) Bấm + ở hàng gió — đổi Pa theo bậc, gửi 'vac', KHÔNG gửi 'air'")
    pg.evaluate("() => { window.__sent=[]; stepOut(document.querySelector('.outrow.air .pm[data-d=\\'1\\']')); }")
    pg.wait_for_timeout(200)
    sent = pg.evaluate("() => window.__sent")
    check("gửi vac = 125", [tuple(s) for s in sent] == [('vac', 125)], str(sent))
    check("cột số hiện 125",
          pg.evaluate("() => document.getElementById('ovAir').textContent") == '125')

    print("5) Kẹp theo dải đã khai báo (max 250) — bấm + 40 lần không được vượt")
    pg.evaluate("() => { for (let i=0;i<40;i++) stepOut(document.querySelector('.outrow.air .pm[data-d=\\'1\\']')); }")
    pg.wait_for_timeout(300)
    sp = pg.evaluate("() => R.vacSp")
    check("kẹp ở 250", sp == 250, f"vacSp={sp}")

    print("6) Chế độ TỰ ĐỘNG không được phát lại % gió của mẻ nền")
    conflict = pg.evaluate("""() => {
      window.__sent=[];
      R.mode='AUTO'; R.phase='RUNNING';
      AUTO.plan=[{gas:40,air:70,drum:55,bt:180}];
      autoTick({t_roast:0, bt:180, gas:40, air:62, drum:55,
                flags:{pc_control:true, flame:true}});
      return window.__sent.filter(s => s[0]==='air');
    }""")
    check("không gửi 'air' khi đang theo áp hút", conflict == [], str(conflict))
    pg.evaluate("() => { R.mode='MANUAL'; }")

    print("7) Tắt chế độ — gửi 'vacen' = 0, đơn vị về %")
    pg.evaluate("async () => { window.__sent=[]; await vacModeToggle(); }")
    pg.wait_for_timeout(300)
    sent = pg.evaluate("() => window.__sent")
    check("gửi vacen = 0", ('vacen', 0) in [tuple(s) for s in sent], str(sent))
    check("đơn vị về %",
          pg.evaluate("() => document.getElementById('airUnit').textContent") == '%')

    print("8) Bỏ khai báo bộ hút — chế độ phải tự tắt và nút ẩn đi")
    st = pg.evaluate("""() => {
      R.vacMode = true;
      CFG.dv_vacuum='0'; CFG_EDIT.dv_vacuum='0';
      applyVacVisibility();
      return {mode:R.vacMode, vis:getComputedStyle(document.getElementById('vcBtn')).display};
    }""")
    check("chế độ tự tắt", st["mode"] is False, str(st))
    check("nút ẩn", st["vis"] == 'none', str(st))

    br.close()

print()
if fails:
    print("THẤT BẠI:"); [print(" -", f) for f in fails]; sys.exit(1)
print("TẤT CẢ PASS")
