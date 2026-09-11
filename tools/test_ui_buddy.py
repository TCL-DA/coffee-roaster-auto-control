# -*- coding: utf-8 -*-
"""Soát HỒNG — bong bóng trợ lý AI (hạng AssistiveTouch). 11/09/2026.

Bong bóng là NÚT MỞ cho khung chat `#ra-panel` do `tools/roast_assistant_ui.js`
dựng (phần của Codex). Bài này chỉ soát bong bóng, không soát khung chat.

B1 · Ngoài sân khấu — BẪY ĐÃ DÍNH: đặt bong bóng trong `#stage` thì `position:fixed`
     bị `transform` của sân khấu NHỐT LẠI và nó teo theo tỉ lệ thu nhỏ (đo được
     47px thay vì 62px) — mắt thường rất khó thấy, phải đo mới ra. Cha phải là BODY.
B2 · Có mặt ở CẢ 6 TAB, đúng cỡ. Chủ máy đặt hàng "tab nào cũng thấy nó".
B3 · Kéo thả rồi HÍT về mép gần nhất, và nhớ chỗ đã đặt.
B4 · Cửa sổ nhỏ lại thì bong bóng phải tự kẹp vào trong màn — không thì nó nằm
     ngoài vùng nhìn và thợ mất luôn trợ lý, không có đường gọi lại.
B5 · Vùng chạm đủ lớn cho ngón tay có găng (≥44px).
B6 · Tắt chuyển động thì vòng sóng "đang nghe" phải đứng yên.

Chạy: python tools/test_ui_buddy.py
"""
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from test_ui_audit import dang_nhap  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parent.parent
APP = pathlib.Path(os.environ.get("OTL_APP_HTML") or (ROOT / "OTL Roast Lab.html"))
TABS = ["tongquan", "rang", "hoso", "lichsu", "kho", "caidat"]


def chay():
    loi = []
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1920, "height": 1080})
        js = []
        pg.on("pageerror", lambda e: js.append(str(e)))
        pg.goto(APP.as_uri())
        pg.wait_for_timeout(2200)
        dang_nhap(pg)

        if not pg.evaluate("() => !!document.getElementById('otlBuddy')"):
            return ["B0 · không thấy bong bóng #otlBuddy"]

        # ── B1 · phải nằm NGOÀI sân khấu co giãn ─────────────────────────────
        cha = pg.evaluate("""() => {
          let e=document.getElementById('otlBuddy'),n=[];
          while(e&&e.parentElement){n.push(e.parentElement.id||e.parentElement.tagName);
            e=e.parentElement;}
          return n; }""")
        if "stage" in cha or "viewport" in cha:
            loi.append(f"B1 · bong bóng nằm TRONG sân khấu ({'>'.join(cha[:3])}) — "
                       "position:fixed bị transform nhốt lại, nút sẽ teo theo tỉ lệ")

        # ── B2 · đủ 6 tab, đúng cỡ, đủ vùng chạm ─────────────────────────────
        for t in TABS:
            pg.evaluate(f"() => gotoTab('{t}')")
            pg.wait_for_timeout(320)
            r = pg.evaluate("""() => {const e=document.getElementById('otlBuddy');
              const b=e.getBoundingClientRect(),c=getComputedStyle(e);
              return {w:Math.round(b.width),h:Math.round(b.height),
                      hien:c.display!=='none'&&c.visibility!=='hidden'&&+c.opacity>.05}}""")
            if not r["hien"]:
                loi.append(f"B2 · tab {t}: bong bóng không hiện")
            elif r["w"] < 44 or r["h"] < 44:
                loi.append(f"B5 · tab {t}: vùng chạm {r['w']}×{r['h']}px — "
                           "dưới 44px, bấm bằng găng tay sẽ trượt")

        # ── B3 · kéo rồi thả phải HÍT về mép ────────────────────────────────
        bb = pg.locator("#otlBuddy").bounding_box()
        pg.mouse.move(bb["x"] + 30, bb["y"] + 30)
        pg.mouse.down()
        pg.mouse.move(940, 430, steps=8)
        pg.wait_for_timeout(60)
        pg.mouse.up()
        pg.wait_for_timeout(700)
        r = pg.evaluate("""() => {const b=document.getElementById('otlBuddy')
          .getBoundingClientRect();
          return {x:Math.round(b.left),right:Math.round(innerWidth-b.right)}}""")
        if min(r["x"], r["right"]) > 40:
            loi.append(f"B3 · thả tay mà KHÔNG hít về mép (cách trái {r['x']}px, "
                       f"phải {r['right']}px) — đứng giữa màn là che mất số liệu")
        if not pg.evaluate("() => !!localStorage.getItem('otl_buddy_pos')"):
            loi.append("B3 · không nhớ chỗ đã đặt — mở lại app là về chỗ cũ")

        # ── B4 · thu nhỏ cửa sổ thì phải tự kẹp vào trong màn ────────────────
        pg.evaluate("""() => {const b=document.getElementById('otlBuddy');
          b.style.left='1700px';b.style.top='980px';}""")
        pg.set_viewport_size({"width": 1000, "height": 700})
        pg.wait_for_timeout(500)
        r = pg.evaluate("""() => {const b=document.getElementById('otlBuddy')
          .getBoundingClientRect();
          return {ngoai: b.right>innerWidth+1||b.bottom>innerHeight+1||b.left<-1||b.top<-1,
                  x:Math.round(b.left),y:Math.round(b.top)}}""")
        if r["ngoai"]:
            loi.append(f"B4 · thu nhỏ cửa sổ là bong bóng ra ngoài màn ({r['x']},{r['y']}) "
                       "— thợ mất luôn trợ lý, không có đường gọi lại")
        pg.set_viewport_size({"width": 1920, "height": 1080})
        pg.wait_for_timeout(400)

        # ── B6 · tắt chuyển động thì vòng sóng đứng yên ─────────────────────
        r = pg.evaluate("""() => {
          const h=document.documentElement, cu=h.dataset.motion;
          h.dataset.motion='reduced';
          const b=document.getElementById('otlBuddy'); b.classList.add('listening');
          const a=getComputedStyle(b.querySelector('.bd-ring')).animationName;
          b.classList.remove('listening'); h.dataset.motion=cu; return a; }""")
        if r and r != "none":
            loi.append(f"B6 · đã tắt chuyển động mà vòng sóng vẫn chạy ({r})")

        if js:
            loi.append("JS · " + "; ".join(js[:3]))
        b.close()
    return loi


if __name__ == "__main__":
    ds = chay()
    if ds:
        print("HỎNG — %d mục:" % len(ds))
        for x in ds:
            print("  •", x)
        sys.exit(1)
    print("ĐẠT — Hồng có mặt ở cả 6 tab, nằm ngoài sân khấu nên không teo, "
          "kéo thả hít mép và nhớ chỗ, thu nhỏ cửa sổ vẫn ở trong màn.")
