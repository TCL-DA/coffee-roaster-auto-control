"""
Test end-to-end nửa HTML: giả lập cầu pywebview + một mẻ rang thật của máy,
kiểm tra app chuyển sang dữ liệu live, chốt mốc theo progStep, vẽ curve, chốt mẻ.
"""
import sys, json, pathlib
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

HTML = pathlib.Path(r"f:\Project\100_OTL_06ALS - CMS - Cacao\OTL Roast Lab.html")
SHOT = pathlib.Path(__file__).parent

# Kịch bản 1 mẻ: (giây, step, BT, ET, ror) — mốc theo progStep: TP6 DE7 FCs8 DEV9 DROP10
SCRIPT_JS = """
window.__t = 0;
window.__frames = FRAMES;
window.pywebview = { api: {
  link_snapshot: async () => {
    const f = window.__frames[Math.min(window.__t, window.__frames.length-1)];
    return {state:'connected', err:'', port:'COM-TEST', age_ms:10, data:{
      bt:f.bt, et:f.et, ror_bt:f.ror, ror_et:f.ror+2, ror_pro:f.ror,
      gas:f.gas, air:60, drum:55, sv:200.0, vac:-120,
      step:f.step, t_roast:f.t, phase:{dry:f.step>=6,mai:f.step>=8,dev:f.step>=9},
      flags:{auto:f.step>=5&&f.step<10,gas:true,charge:false,drop:false,escape:false,cool:false,pc_control:true},
      hb: 1000+window.__t}};
  },
  link_config: async () => ({port:'COM-TEST',baud:9600}),
  toggle_fullscreen: async () => null,
}};
"""


def frames():
    out = []
    for t in range(0, 601, 5):
        # progStep = 'đang CHỜ mốc', nên mốc ĐẠT khi step nhảy sang bước kế:
        #   TP đạt ⟺ step>=7 · DE đạt ⟺ step>=8 · FCs/DEV đạt ⟺ step>=9 · DROP ⟺ 10
        if   t < 5:   step = 4
        elif t < 90:  step = 5      # CHARGE
        elif t < 300: step = 6      # đang chờ TP
        elif t < 470: step = 7      # TP đạt, đang chờ DE
        elif t < 540: step = 8      # DE đạt, đang chờ FCs
        elif t < 595: step = 9      # FCs đạt → vào DEV
        else:         step = 10     # DROP → máy dừng
        bt = 200 - 110 * min(1, t / 90.0) if t < 90 else 90 + 120 * ((t - 90) / 510.0) ** 0.82
        out.append({"t": max(0, t - 5), "step": step, "bt": round(bt, 1),
                    "et": round(bt + 16, 1), "ror": round(14 - 10 * t / 600, 2),
                    "gas": 35 if t < 300 else 25})
    return out


def main():
    fr = frames()
    fails = []

    def chk(name, cond, got=""):
        print(("  OK   " if cond else "  FAIL ") + name + (f"  → {got}" if got else ""))
        if not cond:
            fails.append(name)

    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1600, "height": 900})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append("console." + m.type + ": " + m.text)
              if m.type == "error" else None)
        pg.add_init_script(SCRIPT_JS.replace("FRAMES", json.dumps(fr)))
        pg.goto(HTML.as_uri())
        pg.wait_for_timeout(600)

        # đăng nhập master (PIN 1108) để vào app
        pg.evaluate("session={name:'Test',role:'master',perms:{}};"
                    "document.getElementById('login').classList.remove('on');"
                    "updateBadge();")
        pg.evaluate("gotoTab('rang')")
        pg.wait_for_timeout(300)

        print("1) chip kết nối")
        pg.evaluate("dsTick()")
        pg.wait_for_timeout(300)
        chk("state = connected", pg.evaluate("DS.state") == "connected", pg.evaluate("DS.state"))
        chk("chip đổi màu/nhãn", pg.evaluate("document.getElementById('linkLbl').textContent")
            == "Máy rang · trực tiếp", pg.evaluate("document.getElementById('linkLbl').textContent"))
        chk("BT topbar theo máy", pg.evaluate("document.getElementById('ltBT').textContent") != "198.4°",
            pg.evaluate("document.getElementById('ltBT').textContent"))

        print("2) máy CHARGE → app tự vào RUNNING")
        pg.evaluate("window.__t=20; dsTick()")     # t=100s, step 6
        pg.wait_for_timeout(200)
        chk("phase RUNNING", pg.evaluate("R.phase") == "RUNNING", pg.evaluate("R.phase"))
        chk("đồng hồ lấy theo máy", pg.evaluate("R.elapsed") == fr[20]["t"], pg.evaluate("R.elapsed"))
        chk("CHUA chot TP (step 6 = dang CHO TP)", pg.evaluate("R.mileT.TP") is None,
            pg.evaluate("R.mileT"))

        print("3) chạy hết mẻ (mốc theo progStep)")
        for i in range(21, 119):
            pg.evaluate(f"window.__t={i}; dsTick()")
        pg.wait_for_timeout(300)
        mt = pg.evaluate("R.mileT")
        chk("có đủ TP/DE/FCs/DEV", all(k in mt for k in ("TP", "DE", "FCs", "DEV")), mt)
        # FCs và DEV cùng một giây: firmware chạm FCs là chuyển thẳng sang STP_DEV
        chk("thứ tự mốc tăng dần", mt["TP"] < mt["DE"] < mt["FCs"] <= mt["DEV"], mt)
        chk("TP chốt đúng lúc step sang 7", 290 <= mt["TP"] <= 300, mt["TP"])
        chk("DE chốt đúng lúc step sang 8", 460 <= mt["DE"] <= 470, mt["DE"])
        chk("chuỗi curve có dữ liệu", pg.evaluate("SERIES.t.length") > 90,
            pg.evaluate("SERIES.t.length"))
        chk("số live = số máy", pg.evaluate("document.getElementById('liveBT').textContent")
            == str(fr[118]["bt"]), pg.evaluate("document.getElementById('liveBT').textContent"))
        chk("ABT để trống (máy không có)", pg.evaluate("document.getElementById('liveABT').textContent") == "—")
        chk("chip mốc hiện giờ thật",
            pg.evaluate("document.querySelectorAll('.milestrip .mchip')[0].querySelector('.tm').textContent") != "—",
            pg.evaluate("document.querySelectorAll('.milestrip .mchip')[0].querySelector('.tm').textContent"))
        pg.screenshot(path=str(SHOT / "live_running.png"))

        print("4) máy DROP → app chốt mẻ + ghi lịch sử")
        n0 = pg.evaluate("loadHist().length")
        pg.evaluate(f"window.__t={len(fr)-1}; dsTick()")
        pg.wait_for_timeout(300)
        chk("phase DONE", pg.evaluate("R.phase") == "DONE", pg.evaluate("R.phase"))
        chk("mẻ đã vào lịch sử", pg.evaluate("loadHist().length") == n0 + 1)
        rec = pg.evaluate("loadHist()[0]")
        chk("nhiệt xả = BT thật cuối", abs(rec["temp"] - fr[-1]["bt"]) <= 1, rec)
        chk("thời gian xả khớp máy", rec["time"] == pg.evaluate("fmtMMSS(R.elapsed)"), rec["time"])
        pg.screenshot(path=str(SHOT / "live_done.png"))

        print("5) không có lỗi JS")
        chk("0 pageerror", not errs, errs[:3])
        b.close()

    print("\n" + ("TẤT CẢ ĐẠT" if not fails else f"{len(fails)} MỤC HỎNG: {fails}"))
    return 1 if fails else 0


sys.exit(main())
