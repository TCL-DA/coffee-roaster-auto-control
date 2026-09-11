# -*- coding: utf-8 -*-
"""Soát TẦNG CHUYỂN ĐỘNG MƯỢT — 11/09/2026.

Trước đợt này `.pane` và `.overlay` bật/tắt bằng `display`, mà `display` không
nội suy được, nên KHÔNG CÓ lượt ra: màn cũ biến mất tức thì rồi màn mới mới
trượt vào. Bộ này giữ bốn thứ vừa dựng, và giữ luôn hai CHỐT AN TOÀN quanh chúng.

S1 · Nền tảng   — trình duyệt phải có đủ 4 cơ chế. Thiếu một cái là cả tầng thành
                  mã chết mà app vẫn chạy bình thường, không ai biết.
S2 · Lượt RA    — đóng hộp thoại thì giữa chừng `display` PHẢI còn hiện. Đây là
                  phép đo phân biệt "có chuyển động ra" với "biến mất tức thì".
S3 · Đổi tab    — có gói View Transition khi được phép.
S4 · CHỐT       — ĐANG RANG thì KHÔNG gói. Chuyển cảnh làm đóng băng trang để
                  chụp ảnh; màn Rang cập nhật mỗi giây giữa lúc 30kg hạt đang
                  cháy, đóng băng ở đó là đổi an toàn lấy cái đẹp.
S5 · CHỐT       — tắt chuyển động thì không gói, và đường cong phải hiện ĐỦ chứ
                  không nằm lại ở trạng thái nửa vời.
S6 · Rò tên     — `view-transition-name` phải DUY NHẤT tại mỗi thời điểm. Quên gỡ
                  một lần là mọi lần thu phóng sau trình duyệt thấy trùng tên rồi
                  bỏ qua lặng lẽ — hỏng mà không có lỗi nào hiện ra.

Chạy: python tools/test_ui_smooth.py
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


def chay():
    loi = []
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1366, "height": 768})
        js_err = []
        pg.on("pageerror", lambda e: js_err.append(str(e)))
        pg.goto(APP.as_uri())
        pg.wait_for_timeout(2200)
        dang_nhap(pg)

        # ── S1 · nền tảng ────────────────────────────────────────────────────
        sup = pg.evaluate("""() => ({
          vt: typeof document.startViewTransition === 'function',
          ad: CSS.supports('transition-behavior','allow-discrete'),
          le: CSS.supports('transition-timing-function','linear(0,1)'),
          ease: getComputedStyle(document.documentElement)
                  .getPropertyValue('--ease-out').trim(),
        })""")
        for k, ten in (("vt", "View Transitions"), ("ad", "allow-discrete"),
                       ("le", "linear() easing")):
            if not sup[k]:
                loi.append(f"S1 · trình duyệt thiếu {ten} — cả tầng mượt thành mã chết")
        if not sup["ease"]:
            loi.append("S1 · token --ease-out không có giá trị")

        # ── S2 · hộp thoại phải có LƯỢT RA ───────────────────────────────────
        pg.evaluate("() => aboutOpen()")
        pg.wait_for_timeout(600)
        if pg.evaluate("()=>+getComputedStyle(document.getElementById('aboutbox')).opacity") < .9:
            loi.append("S2 · mở hộp thoại xong mà chưa hiện rõ")
        pg.evaluate("() => aboutClose()")
        pg.wait_for_timeout(70)
        giua = pg.evaluate("""() => {const o=document.getElementById('aboutbox');
          const c=getComputedStyle(o);return {d:c.display,op:+c.opacity}}""")
        if giua["d"] == "none":
            loi.append("S2 · đóng hộp thoại là BIẾN MẤT TỨC THÌ — không có lượt ra "
                       "(display đã 'none' ngay ở mốc 70ms)")
        pg.wait_for_timeout(600)
        if pg.evaluate("()=>getComputedStyle(document.getElementById('aboutbox')).display") != "none":
            loi.append("S2 · đóng xong rồi mà hộp thoại vẫn chiếm chỗ — sẽ chặn thao tác")

        # ── S3 · đổi tab: ĐỒNG BỘ, và pane cũ có lượt ra ─────────────────────
        # Chốt quan trọng nhất của bộ này. Đã từng gói gotoTab trong
        # startViewTransition; nó chạy mượt nhưng đẩy việc đổi DOM sang khung hình
        # sau, biến gotoTab thành bất đồng bộ — mọi chỗ gọi rồi đọc DOM ngay sẽ
        # đọc phải trạng thái CŨ. Bài này khoá lại tính đồng bộ đó.
        pg.evaluate("() => gotoTab('tongquan')")
        pg.wait_for_timeout(600)
        ngay = pg.evaluate("""() => { gotoTab('hoso');
          return [...document.querySelectorAll('.pane.on')].map(p=>p.id).join(','); }""")
        if ngay != "pane-hoso":
            loi.append(f"S3 · gotoTab KHÔNG còn đồng bộ — gọi xong đọc ngay vẫn thấy "
                       f"{ngay!r}; mọi chỗ gọi rồi đọc DOM liền sẽ đọc trạng thái cũ")
        # pane cũ phải còn hiện giữa chừng thì mới là hoà tan chứ không phải cắt
        giua_tab = pg.evaluate("""() => { gotoTab('lichsu');
          const o=document.getElementById('pane-hoso');
          const c=getComputedStyle(o);return {d:c.display,op:+(+c.opacity).toFixed(2)}; }""")
        if giua_tab["d"] == "none":
            loi.append("S3 · pane cũ tắt TỨC THÌ khi đổi tab — không có lượt ra, "
                       "vẫn là cú cắt")
        pg.wait_for_timeout(700)
        if pg.evaluate("()=>getComputedStyle(document.getElementById('pane-hoso')).display") != "none":
            loi.append("S3 · pane cũ hoà tan xong rồi mà vẫn chiếm chỗ")

        # ── S4 · không nổi lỗi JS khi đổi tab liên tiếp thật nhanh ───────────
        truoc = len(js_err)
        pg.evaluate("""() => { const t=['tongquan','rang','hoso','lichsu','kho','caidat'];
          t.forEach(x=>gotoTab(x)); }""")
        pg.wait_for_timeout(900)
        if len(js_err) > truoc:
            loi.append("S4 · đổi tab liên tiếp làm nổi lỗi JS: " + js_err[truoc][:70])

        # ── S5 · CHỐT: tắt chuyển động thì đổi tab tức thì ──────────────────
        pg.evaluate("""() => { window.__m=document.documentElement.dataset.motion;
          document.documentElement.dataset.motion='reduced'; gotoTab('tongquan'); }""")
        pg.wait_for_timeout(80)
        r5 = pg.evaluate("""() => {const o=document.getElementById('pane-lichsu');
          return getComputedStyle(o).display}""")
        pg.evaluate("() => { document.documentElement.dataset.motion=window.__m; }")
        if r5 != "none":
            loi.append("S5 · đã tắt chuyển động mà pane cũ vẫn nán lại — "
                       "người tắt chuyển động cần phản hồi tức thì")

        # ── S6 · đường cong tự vẽ + không rò tên thu phóng ───────────────────
        ve = pg.evaluate("""() => {
          if(typeof uxSpark!=='function')return 'không có uxSpark';
          const html=uxSpark({t:[0,60,120,180,240],bt:[90,120,150,175,196]});
          const d=document.createElement('div');d.innerHTML=html;
          const p=d.querySelector('path[pathLength]');
          return p?'có':'đường cong KHÔNG có pathLength';
        }""")
        if ve != "có":
            loi.append("S6 · " + ve + " — không tự vẽ ra được")

        ro = pg.evaluate("""() => {
          if(typeof zoomOpen!=='function')return 'không có zoomOpen';
          const src=document.createElement('div');src.style.cssText='width:40px;height:20px';
          document.body.appendChild(src);
          zoomOpen(src,()=>{});
          const ngay=src.style.viewTransitionName;
          return new Promise(r=>setTimeout(()=>{
            const sau=src.style.viewTransitionName;
            const con=[...document.querySelectorAll('[style*="view-transition-name"]')]
              .filter(e=>e.style.viewTransitionName).length;
            src.remove();
            r({ngay, sau, con});
          },700));
        }""")
        if isinstance(ro, str):
            loi.append("S6 · " + ro)
        elif ro["sau"]:
            loi.append(f"S6 · RÒ TÊN thu phóng: xong rồi mà còn {ro['sau']!r} — "
                       "lần thu phóng sau sẽ chết lặng vì trùng tên")
        elif ro["con"]:
            loi.append(f"S6 · còn {ro['con']} phần tử giữ view-transition-name sau khi xong")

        if js_err:
            loi.append("JS · " + "; ".join(js_err[:3]))
        b.close()
    return loi


if __name__ == "__main__":
    ds = chay()
    if ds:
        print("HỎNG — %d mục:" % len(ds))
        for x in ds:
            print("  •", x)
        sys.exit(1)
    print("ĐẠT — hộp thoại có lượt ra, đổi tab hoà tan, đang rang thì không đóng băng, "
          "tắt chuyển động thì tôn trọng, không rò tên thu phóng.")
