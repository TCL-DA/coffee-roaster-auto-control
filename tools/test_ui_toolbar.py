"""Chưa chọn hồ sơ (NOSEL) thì thanh công cụ vẫn phải bấm được và gửi đúng lệnh."""
import sys, json, pathlib
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

HTML = pathlib.Path(__file__).resolve().parent.parent / "OTL Roast Lab.html"
SHOT = HTML.parent / "_codex_temp" / "ui-tests"
SHOT.mkdir(parents=True, exist_ok=True)

STUB = """
window.__sent = [];
window.pywebview = { api: {
  link_snapshot: async () => ({state:'connected', err:'', port:'COM9', mode:'tuongthich', age_ms:10,
    data:{bt:180.0, et:38.3, ror_bt:0, ror_et:0, ror_pro:0, gas:0, air:0, drum:82, sv:0, vac:-80,
      step:4, t_roast:0, phase:{dry:false,mai:false,dev:false},
      flags:{auto:false,gas:false,charge:false,drop:false,escape:false,cool:false,
             pc_control:false,flame:null,pc_lost:false,flame_fail:false},
      hb:0, derived:['ror_bt','step','t_roast']}}),
  link_write: async (name, value) => { window.__sent.push([name, value]);
                                       return {ok:true, name, value, reg:0, kind:'pulse'}; },
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
    pg.wait_for_timeout(500)
    pg.evaluate("session={name:'M',role:'master',perms:{}};"
                "document.getElementById('login').classList.remove('on');updateBadge();gotoTab('rang')")
    pg.evaluate("dsTick()")
    pg.wait_for_timeout(600)

    print("1) đang ở trạng thái chưa chọn hồ sơ")
    chk("phase = NOSEL", pg.evaluate("R.phase") == "NOSEL", pg.evaluate("R.phase"))
    chk("overlay đang hiện", pg.evaluate(
        "getComputedStyle(document.querySelector('.roast-nosel')).display") == "flex")

    print("2) nút thanh công cụ KHÔNG bị overlay che")
    # Dùng ID ổn định: nút đánh lửa đã chuyển lên hàng gas, nhãn xả đã đổi.
    for label, control in [("Đánh lửa", "btnIgnite"), ("Nạp hạt", "btnCharge"),
                           ("Xả liệu", "btnEscape"), ("Kết thúc mẻ", "btnDrop")]:
        el = pg.locator("#" + control)
        box = el.bounding_box()
        top = pg.evaluate("([x,y])=>{const e=document.elementFromPoint(x,y);"
                          "return e? (e.closest('button')? 'button':e.className||e.tagName):'null'}",
                          [box["x"] + box["width"] / 2, box["y"] + box["height"] / 2])
        chk(f"'{label}' nhận được cú chạm", top == "button", top)

    print("3) bấm thật → có gửi lệnh xuống máy")
    # Xả liệu nay là lệnh HỆ TRỌNG: chạm KHÔNG gửi, phải giữ đủ 1 giây (đợt PD).
    esc = pg.locator("#btnEscape").bounding_box()
    ecx, ecy = esc["x"] + esc["width"] / 2, esc["y"] + esc["height"] / 2
    pg.mouse.move(ecx, ecy)
    pg.mouse.down(); pg.wait_for_timeout(300); pg.mouse.up()
    pg.wait_for_timeout(200)
    chk("chạm nhanh KHÔNG xả liệu", len(pg.evaluate("window.__sent")) == 0,
        pg.evaluate("window.__sent"))
    pg.mouse.move(ecx, ecy)
    pg.mouse.down(); pg.wait_for_timeout(1250); pg.mouse.up()
    pg.wait_for_timeout(300)
    pg.locator("#btnIgnite").click()
    pg.wait_for_timeout(300)
    sent = pg.evaluate("window.__sent")
    chk("gửi escape + ignite", [s[0] for s in sent] == ["escape", "ignite"], sent)
    # 12/09/2026: lệnh gửi được KHÔNG còn toast nữa — băng trạng thái trên thanh
    # đầu đã nói việc đó và nói kỹ hơn (có cả chặng máy xác nhận), toast chỉ là
    # cái loa thứ hai nói cùng một câu mà lại nổi che thân màn Rang. Ý của phép
    # kiểm giữ nguyên: THỢ PHẢI ĐƯỢC BÁO là lệnh đã đi.
    chk("có báo cho thợ biết (băng trạng thái trên thanh đầu)",
        bool(pg.evaluate("document.getElementById('uxCommand').textContent.trim()")),
        pg.evaluate("document.getElementById('uxCommand').textContent"))

    print("4) số live hiện số MÁY dù chưa rang")
    chk("BT to = 180.0", pg.evaluate("document.getElementById('liveBT').textContent") == "180.0",
        pg.evaluate("document.getElementById('liveBT').textContent"))
    chk("ET = 38.3", pg.evaluate("document.getElementById('liveET').textContent") == "38.3",
        pg.evaluate("document.getElementById('liveET').textContent"))
    chk("Vacuum = -80", pg.evaluate("document.getElementById('liveVac').textContent") == "-80",
        pg.evaluate("document.getElementById('liveVac').textContent"))

    print("5) Nap hat CHI gui lenh, KHONG tu dung me")
    pg.locator("#btnCharge").click()
    pg.wait_for_timeout(500)
    chk("co gui lenh charge", "charge" in [s[0] for s in pg.evaluate("window.__sent")],
        pg.evaluate("window.__sent"))
    chk("van o NOSEL, khong tu vao me", pg.evaluate("R.phase") == "NOSEL",
        pg.evaluate("R.phase"))

    chk("0 lỗi JS", not errs, errs[:2])
    pg.screenshot(path=str(SHOT / "nosel_toolbar.png"))
    b.close()

print("\n" + ("TẤT CẢ ĐẠT" if not fails else f"{len(fails)} MỤC HỎNG: {fails}"))
sys.exit(1 if fails else 0)
