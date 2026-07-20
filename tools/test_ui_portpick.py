"""Hộp thoại chọn cổng COM: nhớ cổng cũ, tự nối, mất cổng thì hỏi lại."""
import sys, pathlib
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

HTML = pathlib.Path(r"f:\Project\100_OTL_06ALS - CMS - Cacao\OTL Roast Lab.html")
SHOT = pathlib.Path(__file__).parent

PORTS = """[
 {"port":"COM9","desc":"Prolific PL2303GT USB Serial COM Port","maker":"Prolific",
  "product":"","serial":"A1B2C3","vid":"067B","pid":"23A3","location":"1-3","hwid":"USB VID:PID=067B:23A3",
  "bluetooth":false,"likely":true},
 {"port":"COM3","desc":"Silicon Labs CP210x USB to UART Bridge","maker":"Silicon Labs",
  "product":"","serial":"0001","vid":"10C4","pid":"EA60","location":"1-4","hwid":"USB VID:PID=10C4:EA60",
  "bluetooth":false,"likely":true},
 {"port":"COM14","desc":"Standard Serial over Bluetooth link","maker":"Microsoft",
  "product":"","serial":"","vid":"","pid":"","location":"","hwid":"BTHENUM",
  "bluetooth":true,"likely":false}
]"""

# CFG_PORT / CONNECT_ON được thay theo từng kịch bản
STUB = """
window.__cfg = {port: CFG_PORT, baud:9600, slave:1, enabled:true};
window.__connectOn = CONNECT_ON;      // cổng nào thì nối được
window.__setCalls = [];
window.pywebview = { api: {
  link_ports: async () => PORTS,
  link_config: async () => window.__cfg,
  link_set_config: async (c) => { window.__setCalls.push(c.port);
                                  window.__cfg = Object.assign({}, window.__cfg, c);
                                  return window.__cfg; },
  link_snapshot: async () => {
    const ok = window.__cfg.port === window.__connectOn;
    return {state: ok?'connected':'error', err: ok?'':'máy không trả lời',
            mode: ok?'tuongthich':null, port: window.__cfg.port, baud:9600, age_ms:10,
            data: ok?{bt:180,et:38,ror_bt:0,ror_et:0,ror_pro:0,gas:0,air:0,drum:82,sv:0,vac:-80,
                      step:4,t_roast:0,phase:{dry:false,mai:false,dev:false},
                      flags:{auto:false,gas:false,charge:false,drop:false,escape:false,cool:false,
                             pc_control:false,flame:null,pc_lost:false,flame_fail:false},
                      hb:0,derived:[]}:null};
  },
  link_write: async () => ({ok:true}),
  toggle_fullscreen: async () => null,
}};
"""

fails = []


def chk(name, cond, got=""):
    print(("  OK   " if cond else "  FAIL ") + name + (f"  → {got}" if got else ""))
    if not cond:
        fails.append(name)


def run(pg, cfg_port, connect_on):
    pg.add_init_script(STUB.replace("PORTS", PORTS)
                       .replace("CFG_PORT", cfg_port)
                       .replace("CONNECT_ON", connect_on))
    pg.goto(HTML.as_uri())
    pg.wait_for_timeout(400)
    pg.evaluate("session={name:'M',role:'master',perms:{}}; finishLogin();")


with sync_playwright() as p:
    b = p.chromium.launch()

    print("1) Cổng nhớ lần trước còn đó và nối được → KHÔNG làm phiền thợ")
    pg = b.new_page(viewport={"width": 1600, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    run(pg, "'COM9'", "'COM9'")
    pg.wait_for_timeout(1600)
    chk("hộp thoại không hiện", not pg.evaluate("PP.open"), pg.evaluate("PP.open"))
    chk("đã nối", pg.evaluate("DS.state") == "connected", pg.evaluate("DS.state"))
    chk("không gọi đổi cấu hình", pg.evaluate("window.__setCalls") == [],
        pg.evaluate("window.__setCalls"))
    pg.close()

    print("2) Cổng nhớ lần trước KHÔNG còn (rút cáp / đổi cổng USB) → hiện hộp thoại")
    pg = b.new_page(viewport={"width": 1600, "height": 900})
    pg.on("pageerror", lambda e: errs.append(str(e)))
    run(pg, "'COM77'", "'COM9'")
    pg.wait_for_timeout(1200)
    chk("hộp thoại hiện lên", pg.evaluate("PP.open"))
    chk("nói rõ mất cổng nào", "COM77" in pg.evaluate(
        "document.getElementById('ppStat').textContent"),
        pg.evaluate("document.getElementById('ppStat').textContent"))
    chk("liệt kê đủ 3 cổng", pg.evaluate("document.querySelectorAll('.pprow').length") == 3,
        pg.evaluate("document.querySelectorAll('.pprow').length"))

    print("3) Thông tin chi tiết từng cổng")
    row = pg.locator(".pprow").first
    txt = row.inner_text()
    chk("có tên cổng", "COM9" in txt, txt.replace("\n", " | "))
    chk("có mô tả + hãng", "Prolific" in txt)
    chk("có VID:PID", "067B:23A3" in txt)
    chk("có số sê-ri", "A1B2C3" in txt)
    chk("đánh dấu cáp USB-serial", "USB-SERIAL" in txt.upper())
    chk("bluetooth bị đẩy xuống cuối", "COM14" in pg.locator(".pprow").last.inner_text())
    pg.screenshot(path=str(SHOT / "portpick.png"))

    print("4) Chọn cổng đúng → nối được, lưu lại, tự đóng")
    pg.locator(".pprow", has_text="COM9").first.click()
    pg.wait_for_timeout(1800)
    chk("đã lưu cổng chọn", pg.evaluate("window.__setCalls") == ["COM9"],
        pg.evaluate("window.__setCalls"))
    chk("báo nối được", "nối được" in pg.evaluate(
        "document.getElementById('ppStat').textContent"),
        pg.evaluate("document.getElementById('ppStat').textContent"))
    chk("hộp thoại tự đóng", not pg.evaluate("PP.open"))
    pg.close()

    print("5) Chọn nhầm cổng → báo lỗi, hộp thoại ở lại cho chọn tiếp")
    pg = b.new_page(viewport={"width": 1600, "height": 900})
    pg.on("pageerror", lambda e: errs.append(str(e)))
    run(pg, "'COM77'", "'COM9'")
    pg.wait_for_timeout(1200)
    pg.locator(".pprow", has_text="COM3").first.click()
    pg.wait_for_timeout(7000)
    st = pg.evaluate("document.getElementById('ppStat').textContent")
    chk("báo không nối được", "không nối được" in st, st)
    chk("hộp thoại vẫn mở", pg.evaluate("PP.open"))
    pg.close()

    chk("0 lỗi JS", not errs, errs[:2])
    b.close()

print("\n" + ("TẤT CẢ ĐẠT" if not fails else f"{len(fails)} MỤC HỎNG: {fails}"))
sys.exit(1 if fails else 0)
