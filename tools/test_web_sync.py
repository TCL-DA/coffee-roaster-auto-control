# -*- coding: utf-8 -*-
"""Kiểm BẢN WEB có đúng bằng bản app không — chạy server thật rồi mở bằng trình duyệt.

Vì sao cần: web và app dùng CHUNG một file `OTL Roast Lab.html`, server chỉ đóng
thêm dấu `window._OTL_WEBCLONE=1`. Nghe thì "đương nhiên đồng bộ", nhưng đó là
suy luận chứ không phải bằng chứng — server có thể đọc bản đã nạp sẵn từ lúc khởi
động, hoặc trình duyệt giữ bản cũ trong bộ nhớ đệm. Bộ này ĐO.

W1  trang web phục vụ đúng NỘI DUNG của file trên đĩa (so từng byte phần thân)
W2  có dấu web clone, và shim web đã bật
W3  các bản vá mới nhất CÓ MẶT trên web (cử chỉ kéo, luật font, dấu chưa-có-số)
W4  cử chỉ kéo viên thuốc CHẠY THẬT trên web, không chỉ có mã
W5  không lỗi JavaScript khi mở

BẪY: web giữ kết nối SSE nên `networkidle` KHÔNG BAO GIỜ tới — phải chờ `load`.

Chạy: python tools/test_web_sync.py
"""
import pathlib
import re
import shutil
import socket
import subprocess
import tempfile
import sys
import time
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from playwright.sync_api import sync_playwright  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
APP = HERE.parent / "OTL Roast Lab.html"


def cong_trong():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    n = s.getsockname()[1]
    s.close()
    return n


def main():
    loi = []

    def bat(ma, dk, mo_ta):
        if not dk:
            loi.append("%s — %s" % (ma, mo_ta))

    port = cong_trong()
    # Dựng đúng máy chủ web của app, nhưng KHÔNG mở cửa sổ pywebview.
    # Dùng CHÍNH start_webserver() của app — không dựng máy chủ giả, vì máy chủ
    # giả thì kiểm được cái mình tự viết chứ không kiểm được cái khách đang chạy.
    # Chạy trên THƯ MỤC DỮ LIỆU TẠM: máy chủ thành "máy mới tinh", không tài khoản
    # nào — nên bộ kiểm tự tạo được master và đi hết luồng. Quan trọng hơn: KHÔNG
    # đụng vào auth.json / state.json thật của chủ máy.
    tmp = tempfile.mkdtemp(prefix="otl-websync-")
    ma = (
        "import sys,time;"
        "sys.path.insert(0,r'%s');"
        "import roast_lab_hmi as M;"
        "M.app_data_dir=lambda: r'%s';"
        "api=M.Api();"
        "api.web_cfg=dict(getattr(api,'web_cfg',{}) or {});"
        "api.web_cfg['cong']=%d;"
        "api.web_cfg['pin']='112233';"
        "M.start_webserver(api);"
        "time.sleep(180)"
    ) % (HERE, tmp, port)
    PIN_WEB = "112233"
    srv = subprocess.Popen([sys.executable, "-c", ma],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    goc = "http://127.0.0.1:%d" % port
    body = None
    for _ in range(50):
        try:
            body = urllib.request.urlopen(goc + "/", timeout=1).read().decode("utf-8", "replace")
            break
        except Exception:
            time.sleep(0.3)
    if body is None:
        srv.kill()
        out, err = srv.communicate(timeout=5)
        print("KHÔNG dựng được máy chủ web — bỏ qua bộ kiểm này, KHÔNG coi là ĐẠT.")
        print((err or b"").decode("utf-8", "replace")[-600:])
        return 2

    # ĐỌC NHỊ PHÂN rồi mới giải mã: read_text() tự đổi CRLF thành LF, còn qua
    # HTTP thì giữ nguyên — so thẳng là lệch đúng bằng SỐ DÒNG và tưởng web sai bản.
    # Lấy token web ĐÚNG ĐƯỜNG khách đi (POST /api/weblogin), rồi nhét sẵn vào
    # sessionStorage trước khi trang khởi động — vì hộp hỏi PIN của web là
    # prompt(), mà prompt() chỉ bật khi có thao tác cần quyền, không bật lúc mở.
    import json as _json
    tok = ""
    try:
        rq = urllib.request.Request(
            goc + "/api/weblogin", method="POST",
            data=_json.dumps({"pin": PIN_WEB}).encode(),
            headers={"Content-Type": "application/json"})
        tok = (_json.loads(urllib.request.urlopen(rq, timeout=5).read()) or {}).get("token", "")
    except Exception as e:
        loi.append("W0 — không lấy được token web: %s" % e)
    bat("W0", bool(tok), "đăng nhập PIN web không trả về token")

    dia = APP.read_bytes().decode("utf-8")
    body = body.replace(chr(13) + chr(10), chr(10))
    dia = dia.replace(chr(13) + chr(10), chr(10))

    # ── W1 · nội dung web = nội dung file trên đĩa (trừ 2 chỗ server chèn) ──
    sach = body.replace('<head><script>window._OTL_WEBCLONE=1</script>', '<head>', 1)
    sach = sach.replace('<script src="/assistant.js"></script></body>', '</body>', 1)
    bat("W1", sach == dia,
        "web phục vụ nội dung KHÁC file trên đĩa (%d vs %d ký tự)" % (len(sach), len(dia)))

    # ── W2 · có dấu web clone ─────────────────────────────────────────────
    bat("W2", "window._OTL_WEBCLONE=1" in body, "web thiếu dấu _OTL_WEBCLONE")

    # ── W3 · các bản vá mới nhất có mặt trên web ──────────────────────────
    moc = {
        "cử chỉ kéo viên thuốc": "SEG_GROUPS",
        "nhận trục ngang/dọc": "function segDoc",
        "luật font cho nút/ô nhập": "button,input,select,textarea,optgroup{font-family:inherit}",
        "dấu chưa-có-số": ".num.nodata",
        "gộp lời báo mốc": "MILE_RANK",
        "gương soi thêm 3 hàm": "'setProfFilter'",
    }
    for ten, dau in moc.items():
        bat("W3", dau in body, "web THIẾU bản vá %r (không thấy %r)" % (ten, dau))

    # ── W4/W5 · mở bằng trình duyệt và kéo thử ────────────────────────────
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1920, "height": 1080}, has_touch=True)
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        # BẪY: Playwright mặc định TỰ HUỶ hộp prompt. Web hỏi PIN điều khiển bằng
        # prompt(), nên không bắt hộp này là mọi lệnh API đều 401 và bộ kiểm tưởng
        # bản web hỏng — trong khi app xử lý hoàn toàn đúng.
        pg.on("dialog", lambda d: d.accept(PIN_WEB)
              if d.type == "prompt" else d.accept())
        if tok:
            pg.add_init_script(
                "try{sessionStorage.setItem('otl_webtok',%r)}catch(e){}" % tok)
        pg.goto(goc + "/", wait_until="load")   # SSE giữ kết nối → networkidle không tới
        pg.wait_for_timeout(1500)
        # Web BẮT ĐĂNG NHẬP y như app — không đăng nhập thì lớp phủ PIN che hết
        # thanh tab, mọi cú chạm rơi vào lớp phủ và bộ kiểm tưởng cử chỉ hỏng.
        from test_ui_audit import dang_nhap
        dang_nhap(pg)
        # Băm PIN 150k vòng nên web chậm hơn app rõ rệt — CHỜ THEO ĐIỀU KIỆN,
        # đừng chờ cứng một con số rồi kết luận là hỏng.
        vao_duoc = True
        try:
            pg.wait_for_function(
                "()=>getComputedStyle(document.getElementById('login')).display==='none'",
                timeout=15000)
        except Exception:
            vao_duoc = False
        bat("W4", vao_duoc, "đăng nhập xong mà lớp phủ PIN vẫn che màn hình sau 15 s")
        pg.wait_for_timeout(600)
        bat("W2", pg.evaluate("()=>!!window._OTL_WEBCLONE"), "shim web không bật trên trang")

        # Trên web, đăng nhập xong app mở HỘP CHỌN CỔNG COM — nó phủ kín màn nên
        # mọi cú chạm rơi vào lớp phủ chứ không tới thanh tab. Đóng đúng như thợ
        # bấm Huỷ, rồi mới thử cử chỉ.
        pg.evaluate("()=>document.querySelectorAll('.overlay.on')"
                    ".forEach(e=>{if(e.id!=='login')e.classList.remove('on');})")
        pg.wait_for_timeout(400)
        bat("W4", pg.evaluate(
            "()=>!document.querySelector('.overlay.on')"), "còn lớp phủ che thanh tab")

        co_cuchi = pg.evaluate("()=>typeof SEG_GROUPS!=='undefined'&&SEG_GROUPS.length>0")
        bat("W4", co_cuchi, "trên web không thấy cử chỉ kéo được nạp")
        if co_cuchi:
            pg.evaluate("()=>gotoTab('tongquan')")
            pg.wait_for_timeout(400)
            vt = pg.evaluate("""()=>{
                const q=t=>document.querySelector('#tabnav .tab[data-tab="'+t+'"]');
                const a=q('tongquan'),c=q('lichsu'); if(!a||!c)return null;
                const r1=a.getBoundingClientRect(),r2=c.getBoundingClientRect();
                return {ax:r1.x+r1.width/2,ay:r1.y+r1.height/2,
                        bx:r2.x+r2.width/2,by:r2.y+r2.height/2};}""")
            if not vt:
                loi.append("W4 — không tìm được ô tab trên web")
            else:
                cdp = pg.context.new_cdp_session(pg)
                cdp.send("Input.dispatchTouchEvent", {"type": "touchStart",
                         "touchPoints": [{"x": vt["ax"], "y": vt["ay"], "id": 1}]})
                pg.wait_for_timeout(60)
                for i in range(1, 9):
                    cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [
                        {"x": vt["ax"] + (vt["bx"] - vt["ax"]) * i / 8, "y": vt["ay"], "id": 1}]})
                    pg.wait_for_timeout(25)
                cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
                pg.wait_for_timeout(600)
                dang = pg.evaluate(
                    "()=>document.querySelector('.pane.on')?.id.replace('pane-','')||null")
                bat("W4", dang == "lichsu",
                    "kéo trên WEB không chuyển được tab (đang ở %r)" % dang)
        loc = [e for e in errs if "SSE" not in e and "EventSource" not in e]
        bat("W5", not loc, "lỗi JavaScript trên web: %s" % "; ".join(dict.fromkeys(loc))[:220])
        b.close()

    srv.terminate()
    try:
        srv.wait(timeout=5)
    except Exception:
        srv.kill()
    shutil.rmtree(tmp, ignore_errors=True)

    if loi:
        print("HỎNG %d mục:" % len(loi))
        for x in loi:
            print("  " + x)
        return 1
    print("ĐẠT: bản web phục vụ ĐÚNG nội dung file trên đĩa, có đủ bản vá mới, "
          "và cử chỉ kéo chạy thật trên web.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
