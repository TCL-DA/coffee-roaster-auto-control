"""Chế độ tương thích: nút thanh công cụ là LỆNH MÁY, mẻ chỉ mở khi bấm Bắt đầu rang.

Dựng đúng tình huống máy thật: bật PC control thì reg 14 thành ô LỆNH nên không
còn phản chiếu nút HMI — progStep đứng yên ở 4, app không được dựa vào nó.
"""
import sys, pathlib
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

HTML = pathlib.Path(__file__).resolve().parent.parent / "OTL Roast Lab.html"

STUB = """
window.__sent = [];
window.__begun = 0;          // mô phỏng roast_derive: link_begin_batch mở đồng hồ
window.__dropped = 0;
window.pywebview = { api: {
  link_snapshot: async () => {
    const c = window.__begun;
    const t = c ? Math.floor(((window.__dropped||Date.now()) - c)/1000) : 0;
    return {state:'connected', err:'', port:'COM9', mode:'tuongthich', age_ms:10,
      data:{bt:180.0, et:37.9, ror_bt:0, ror_et:0, ror_pro:0, gas:0, air:0, drum:82, sv:0, vac:0,
        step:4, t_roast:t, phase:{dry:false,mai:false,dev:false},
        mile: c?{CHARGE:0}:{}, mile_bt: c?{CHARGE:180.0}:{},
        flags:{auto:false,gas:false,charge:false,drop:false,escape:false,cool:false,
               pc_control:false,flame:null,pc_lost:false,flame_fail:false},
        hb:0, derived:['ror_bt','step','t_roast','mile']}};
  },
  link_write: async (name, value) => { window.__sent.push(name); return {ok:true, name, value}; },
  link_begin_batch: async () => { window.__begun = Date.now(); window.__dropped = 0;
                                  return {ok:true}; },
  link_new_batch: async () => { window.__begun = 0; window.__dropped = 0; return {ok:true}; },
  link_ports: async () => [],
  link_config: async () => ({port:'COM9'}),
  toggle_fullscreen: async () => null,
}};
"""

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
    pg.add_init_script(STUB)
    pg.goto(HTML.as_uri())
    pg.wait_for_timeout(400)
    pg.evaluate("session={name:'M',role:'master',perms:{}};"
                "document.getElementById('login').classList.remove('on');updateBadge();gotoTab('rang')")
    pg.evaluate("dsTick()")
    pg.wait_for_timeout(500)
    n0 = pg.evaluate("loadHist().length")

    print("1) Chưa bấm Bắt đầu rang — nút thanh công cụ KHÔNG được dựng mẻ")
    for label in ("Đánh lửa", "Nạp hạt", "Xả liệu"):
        pg.locator(f"#pane-rang .toolbar button:has-text('{label}')").first.click()
        pg.wait_for_timeout(250)
    pg.wait_for_timeout(2000)
    chk("có gửi đủ 3 lệnh", pg.evaluate("window.__sent") == ["ignite", "charge", "escape"],
        pg.evaluate("window.__sent"))
    chk("vẫn ở NOSEL, không tự vào mẻ", pg.evaluate("R.phase") == "NOSEL",
        pg.evaluate("R.phase"))
    chk("đồng hồ vẫn 00:00", pg.evaluate("R.elapsed") == 0, pg.evaluate("R.elapsed"))
    chk("KHÔNG hiện banner Mẻ hoàn tất", pg.evaluate(
        "getComputedStyle(document.querySelector('.roast-done')).display") == "none")
    chk("không ghi mẻ nào vào lịch sử", pg.evaluate("loadHist().length") == n0,
        pg.evaluate("loadHist().length"))
    chk("chưa chốt mốc nào", pg.evaluate("Object.keys(R.mileT).length") == 0,
        pg.evaluate("R.mileT"))

    print("2) Bấm Bắt đầu rang → mẻ mới mở, đồng hồ chạy")
    pg.evaluate("loadProfile(0); startRoast();")
    pg.wait_for_timeout(4200)          # poll 1 Hz — cần vài nhịp mới thấy đồng hồ nhích
    chk("phase RUNNING", pg.evaluate("R.phase") == "RUNNING", pg.evaluate("R.phase"))
    chk("đồng hồ chạy", pg.evaluate("R.elapsed") >= 2, pg.evaluate("R.elapsed"))
    chk("ở lại trong mẻ dù step vẫn 4", pg.evaluate("R.phase") == "RUNNING")

    print("3) Đang rang mới chốt được mẻ bằng Xả mẻ")
    pg.locator("#pane-rang .toolbar button:has-text('Xả mẻ')").first.click()
    pg.wait_for_timeout(1200)
    chk("có gửi lệnh drop", "drop" in pg.evaluate("window.__sent"), pg.evaluate("window.__sent"))
    chk("phase DONE", pg.evaluate("R.phase") == "DONE", pg.evaluate("R.phase"))
    chk("mẻ vào lịch sử", pg.evaluate("loadHist().length") == n0 + 1,
        pg.evaluate("loadHist().length"))

    print("4) Chạm chip kết nối → mở bảng chọn cổng dù đang nối tốt")
    pg.evaluate("newRoast()")
    pg.locator("#linkChip").click()
    pg.wait_for_timeout(900)
    chk("bảng chọn cổng mở", pg.evaluate("PP.open"))

    chk("0 lỗi JS", not errs, errs[:2])
    b.close()

print("\n" + ("TẤT CẢ ĐẠT" if not fails else f"{len(fails)} MỤC HỎNG: {fails}"))
sys.exit(1 if fails else 0)
