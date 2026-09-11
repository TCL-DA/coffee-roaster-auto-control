# -*- coding: utf-8 -*-
"""Kiểm cử chỉ KÉO VIÊN THUỐC trên thanh tab — segmented control kiểu iOS.

Giữ ô đang chọn rồi kéo ngang: viên thuốc bám ngón tay, qua tab nào tab đó sáng
lên trước, thả ra mới thật sự chuyển tab.

Bắn CHẠM THẬT qua CDP (`Input.dispatchTouchEvent`) chứ không giả bằng chuột —
máy rang bấm bằng ngón tay có găng, và bộ kiểm chuột đã từng bỏ lọt một lỗi thật
(hai ngón chạm cùng lúc làm cử chỉ kẹt, xem UI-LOCK 08/09).

D1  kéo qua tab khác rồi thả  → CHUYỂN sang tab đó
D2  kéo rồi kéo về chỗ cũ     → KHÔNG đổi tab
D3  chạm mà không kéo         → không kích hoạt cử chỉ, bấm thường vẫn chạy
D4  NGÓN THỨ HAI chen vào     → không cướp được cử chỉ của ngón đầu
D5  mất pointerup (nhấc tay ngoài vùng / app mất tiêu điểm) → cử chỉ PHẢI tự dọn,
    không để thanh tab kẹt ở trạng thái đang kéo
D6  kéo quá hai đầu           → viên thuốc bị chặn trong thanh, không văng ra ngoài
D7  ô KHÔNG được chọn         → kéo không ăn (chỉ ô đang chọn mới kéo được)
D8  màn Rang                  → vẫn kéo được, và viên thuốc chỉ hiện lúc kéo
D9  4 cụm còn lại (Cài đặt · Hồ sơ · Kho · chip lọc) → kéo được, viên thuốc
    hiện lúc kéo rồi ẩn lại khi thả

Chạy: python tools/test_ui_nav_drag.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from test_ui_audit import dang_nhap  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

APP = pathlib.Path(__file__).resolve().parent.parent / "OTL Roast Lab.html"


class Ngon:
    """Một ngón tay thật, bắn qua CDP."""

    def __init__(self, cdp, ident=1):
        self.cdp, self.id, self.pts = cdp, ident, []

    def _send(self, kind, pts):
        self.cdp.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": pts})

    def cham(self, x, y):
        self.pts = [{"x": x, "y": y, "id": self.id}]
        self._send("touchStart", self.pts)

    def keo(self, x, y):
        self.pts = [{"x": x, "y": y, "id": self.id}]
        self._send("touchMove", self.pts)

    def nha(self):
        self._send("touchEnd", [])


def tam(page, tab):
    return page.evaluate("""(t)=>{
        const e=document.querySelector('#tabnav .tab[data-tab="'+t+'"]');
        if(!e)return null; const r=e.getBoundingClientRect();
        return {x:r.x+r.width/2, y:r.y+r.height/2};}""", tab)


def tab_dang_chon(page):
    return page.evaluate(
        "()=>document.querySelector('#tabnav .tab.on')?.dataset.tab||null")


def pane_dang_mo(page):
    return page.evaluate(
        "()=>document.querySelector('.pane.on')?.id.replace('pane-','')||null")


def main():
    loi = []

    def bat(ma, dieu_kien, mo_ta):
        if not dieu_kien:
            loi.append("%s — %s" % (ma, mo_ta))

    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1920, "height": 1080},
                        has_touch=True, is_mobile=False)
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(APP.as_uri())
        dang_nhap(pg)
        pg.wait_for_timeout(600)
        cdp = pg.context.new_cdp_session(pg)
        f1, f2 = Ngon(cdp, 1), Ngon(cdp, 2)

        def ve_tab(t):
            pg.evaluate("(t)=>gotoTab(t)", t)
            pg.wait_for_timeout(350)

        # ── D1 · kéo sang tab khác rồi thả → phải chuyển ───────────────────
        ve_tab("tongquan")
        a, c = tam(pg, "tongquan"), tam(pg, "lichsu")
        f1.cham(a["x"], a["y"])
        pg.wait_for_timeout(60)
        for i in range(1, 9):
            f1.keo(a["x"] + (c["x"] - a["x"]) * i / 8, a["y"])
            pg.wait_for_timeout(25)
        giua_keo = pg.evaluate("()=>document.getElementById('tabnav').classList.contains('segdragging')")
        f1.nha()
        pg.wait_for_timeout(500)
        bat("D1", giua_keo, "kéo mà thanh tab không vào trạng thái đang kéo")
        bat("D1", pane_dang_mo(pg) == "lichsu",
            "kéo sang Lịch sử rồi thả mà màn hiện tại là %r" % pane_dang_mo(pg))

        # ── D2 · kéo đi rồi kéo về chỗ cũ → KHÔNG đổi tab ──────────────────
        ve_tab("tongquan")
        a, c = tam(pg, "tongquan"), tam(pg, "hoso")
        f1.cham(a["x"], a["y"])
        pg.wait_for_timeout(60)
        f1.keo((a["x"] + c["x"]) / 2, a["y"])
        pg.wait_for_timeout(60)
        f1.keo(a["x"], a["y"])
        pg.wait_for_timeout(60)
        f1.nha()
        pg.wait_for_timeout(450)
        bat("D2", pane_dang_mo(pg) == "tongquan",
            "kéo đi rồi kéo về chỗ cũ mà vẫn đổi sang %r" % pane_dang_mo(pg))

        # ── D3 · chạm không kéo → không kích hoạt cử chỉ ───────────────────
        ve_tab("tongquan")
        a = tam(pg, "tongquan")
        f1.cham(a["x"], a["y"])
        pg.wait_for_timeout(120)
        keo_nham = pg.evaluate("()=>document.getElementById('tabnav').classList.contains('segdragging')")
        f1.nha()
        pg.wait_for_timeout(300)
        bat("D3", not keo_nham, "chỉ chạm mà đã vào trạng thái đang kéo")
        bat("D3", pane_dang_mo(pg) == "tongquan", "chỉ chạm mà đổi tab")

        # ── D4 · ngón thứ hai chen vào không được cướp cử chỉ ──────────────
        ve_tab("tongquan")
        a, c = tam(pg, "tongquan"), tam(pg, "lichsu")
        f1.cham(a["x"], a["y"])
        pg.wait_for_timeout(50)
        f1.keo((a["x"] + c["x"]) / 2, a["y"])
        pg.wait_for_timeout(50)
        cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [
            {"x": a["x"], "y": a["y"], "id": 1},
            {"x": c["x"], "y": c["y"], "id": 2}]})
        pg.wait_for_timeout(50)
        cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [
            {"x": (a["x"] + c["x"]) / 2, "y": a["y"], "id": 1},
            {"x": c["x"] + 200, "y": c["y"], "id": 2}]})
        pg.wait_for_timeout(60)
        cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        pg.wait_for_timeout(450)
        bat("D4", pg.evaluate("()=>!document.getElementById('tabnav').classList.contains('segdragging')"),
            "ngón thứ hai xen vào rồi mà thanh tab vẫn kẹt ở trạng thái đang kéo")

        # ── D5 · mất pointerup → phải tự dọn, không kẹt ────────────────────
        ve_tab("tongquan")
        a, c = tam(pg, "tongquan"), tam(pg, "hoso")
        f1.cham(a["x"], a["y"])
        pg.wait_for_timeout(50)
        f1.keo((a["x"] + c["x"]) / 2, a["y"])
        pg.wait_for_timeout(50)
        pg.evaluate("()=>dispatchEvent(new Event('blur'))")   # app mất tiêu điểm
        pg.wait_for_timeout(300)
        bat("D5", pg.evaluate("()=>!document.getElementById('tabnav').classList.contains('segdragging')"),
            "mất tiêu điểm giữa lúc kéo mà thanh tab vẫn kẹt")
        bat("D5", pg.evaluate("()=>SEGDRAG.id===null"), "cử chỉ không được dọn sạch")
        f1.nha()
        pg.wait_for_timeout(200)

        # ── D6 · kéo quá hai đầu → viên thuốc bị chặn trong thanh ──────────
        ve_tab("tongquan")
        a = tam(pg, "tongquan")
        f1.cham(a["x"], a["y"])
        pg.wait_for_timeout(50)
        f1.keo(a["x"] + 4000, a["y"])
        pg.wait_for_timeout(90)
        trong = pg.evaluate("""()=>{
            const n=document.getElementById('tabnav');
            const x=parseFloat(getComputedStyle(n).getPropertyValue('--nav-x'))||0;
            const w=parseFloat(getComputedStyle(n).getPropertyValue('--nav-width'))||0;
            const t=[...n.querySelectorAll('.tab')];
            const hi=t[t.length-1].offsetLeft+t[t.length-1].offsetWidth;
            return {x,w,hi,lot:x>=t[0].offsetLeft-1 && x+w<=hi+1};}""")
        f1.nha()
        pg.wait_for_timeout(400)
        bat("D6", trong["lot"], "kéo quá đầu thanh mà viên thuốc văng ra ngoài: %s" % trong)

        # ── D7 · ô không được chọn thì không kéo được ──────────────────────
        ve_tab("tongquan")
        c = tam(pg, "kho")
        f1.cham(c["x"], c["y"])
        pg.wait_for_timeout(50)
        f1.keo(c["x"] - 300, c["y"])
        pg.wait_for_timeout(80)
        bat("D7", pg.evaluate("()=>!document.getElementById('tabnav').classList.contains('segdragging')"),
            "kéo từ ô KHÔNG được chọn mà vẫn chạy cử chỉ")
        f1.nha()
        pg.wait_for_timeout(300)

        # ── D8 · màn Rang: kéo được, viên thuốc chỉ hiện lúc kéo ───────────
        ve_tab("rang")
        an_luc_thuong = pg.evaluate(
            "()=>getComputedStyle(document.getElementById('tabnav'),'::before').display")
        a, c = tam(pg, "rang"), tam(pg, "hoso")
        f1.cham(a["x"], a["y"])
        pg.wait_for_timeout(50)
        f1.keo((a["x"] + c["x"]) / 2, a["y"])
        pg.wait_for_timeout(80)
        hien_luc_keo = pg.evaluate(
            "()=>getComputedStyle(document.getElementById('tabnav'),'::before').display")
        for i in range(1, 5):
            f1.keo(a["x"] + (c["x"] - a["x"]) * i / 4, a["y"])
            pg.wait_for_timeout(30)
        f1.nha()
        pg.wait_for_timeout(500)
        # ĐỔI LUẬT 11/09/2026 — thống nhất thanh đầu (hướng A). Trước đây màn Rang
        # tắt viên thuốc và dùng nền ô thay thế, nên bài này bắt nó phải 'none' lúc
        # thường. Nay cả 6 tab dùng CHUNG một thanh đầu và viên thuốc là dấu báo tab
        # đang mở cho mọi tab, nên yêu cầu ngược lại: LUÔN hiện. Giữ nguyên phần
        # kiểm kéo — đó mới là thứ bài này sinh ra để giữ.
        bat("D8", an_luc_thuong != "none",
            "thanh đầu đã thống nhất thì viên thuốc phải hiện ở MỌI tab, kể cả Rang "
            "(đang là %r) — không có nó thì không biết tab nào đang mở" % an_luc_thuong)
        bat("D8", hien_luc_keo != "none",
            "màn Rang đang kéo mà không thấy viên thuốc — không biết mình kéo cái gì")
        bat("D8", pane_dang_mo(pg) == "hoso",
            "kéo trên màn Rang không chuyển được tab (đang ở %r)" % pane_dang_mo(pg))

        # ── D9 · CẢ 5 CỤM CÒN LẠI cũng phải kéo được ───────────────────────
        cum = [
            ("Cài đặt",    "caidat", "#subnav",     "button[data-sub]",     "sub"),
            ("Hồ sơ",      "hoso",   "#hsnav",      "button[data-hs]",      "hs"),
            ("Kho",        "kho",    ".khosub",     "button[data-khosub]",  "khosub"),
            ("Lọc hồ sơ",  "hoso",   "#profFilter", "button[data-f]",       "f"),
        ]
        for ten, tab, box, item, attr in cum:
            ve_tab(tab)
            # Bước "Hồ sơ" ở trên đã kéo sang tab con Công thức nạp, mà chip lọc
            # chỉ sống trong tab con Hồ sơ rang — không đưa về là kịch bản rỗng.
            if box == "#profFilter":
                pg.evaluate("()=>gotoHs('rang')")
                pg.wait_for_timeout(350)
            vt = pg.evaluate("""(a)=>{
                const b=document.querySelector(a.box); if(!b)return null;
                const its=[...b.querySelectorAll(a.item)].filter(e=>e.offsetWidth>0);
                if(its.length<2)return null;
                const on=its.find(e=>e.classList.contains('on'))||its[0];
                const kh=its.find(e=>e!==on);
                const r1=on.getBoundingClientRect(), r2=kh.getBoundingClientRect();
                return {a:{x:r1.x+r1.width/2,y:r1.y+r1.height/2},
                        b:{x:r2.x+r2.width/2,y:r2.y+r2.height/2},
                        tu:on.dataset[a.attr], toi:kh.dataset[a.attr]};}""",
                {"box": box, "item": item, "attr": attr})
            if not vt:
                loi.append("D9 — cụm %s không dựng được kịch bản (thiếu nút?)" % ten)
                continue
            f1.cham(vt["a"]["x"], vt["a"]["y"])
            pg.wait_for_timeout(60)
            # Kéo theo ĐÚNG HƯỚNG tới ô đích — cụm Cài đặt xếp DỌC, kéo ngang
            # thì quãng đường bằng 0 và cử chỉ không bao giờ khởi động.
            for i in range(1, 7):
                f1.keo(vt["a"]["x"] + (vt["b"]["x"] - vt["a"]["x"]) * i / 6,
                       vt["a"]["y"] + (vt["b"]["y"] - vt["a"]["y"]) * i / 6)
                pg.wait_for_timeout(28)
            dang_keo = pg.evaluate("(s)=>{const e=document.querySelector(s);"
                                   "return !!e&&e.classList.contains('segdragging');}", box)
            thay_pill = pg.evaluate("""(s)=>{const e=document.querySelector(s);
                const p=e&&e.querySelector(':scope>.segpill');
                return !!p&&getComputedStyle(p).opacity!=='0';}""", box)
            f1.nha()
            pg.wait_for_timeout(450)
            chon = pg.evaluate("""(a)=>{const b=document.querySelector(a.box);
                const on=b&&b.querySelector(a.item+'.on');
                return on?on.dataset[a.attr]:null;}""",
                {"box": box, "item": item, "attr": attr})
            bat("D9", dang_keo, "cụm %s kéo mà không vào trạng thái đang kéo" % ten)
            bat("D9", thay_pill, "cụm %s đang kéo mà không thấy viên thuốc" % ten)
            bat("D9", chon == vt["toi"],
                "cụm %s kéo sang %r rồi thả mà đang chọn %r" % (ten, vt["toi"], chon))
            # thả ra thì viên thuốc phải ẩn lại, cụm trông như cũ
            an_lai = pg.evaluate("""(s)=>{const e=document.querySelector(s);
                const p=e&&e.querySelector(':scope>.segpill');
                return !p||getComputedStyle(p).opacity==='0';}""", box)
            bat("D9", an_lai, "cụm %s thả tay rồi mà viên thuốc còn hiện" % ten)

        ve_tab("tongquan")
        # tab đang chọn và màn đang mở phải luôn khớp nhau
        bat("SYNC", tab_dang_chon(pg) == pane_dang_mo(pg),
            "ô sáng (%r) và màn đang mở (%r) lệch nhau"
            % (tab_dang_chon(pg), pane_dang_mo(pg)))
        if errs:
            loi.append("JS — lỗi khi chạy: %s" % "; ".join(dict.fromkeys(errs))[:200])
        b.close()

    if loi:
        print("HỎNG %d mục:" % len(loi))
        for x in loi:
            print("  " + x)
        return 1
    print("ĐẠT: kéo viên thuốc trên thanh tab chạy đúng — chuyển tab, huỷ khi kéo về, "
          "chặn trong thanh, ngón thứ hai không cướp được, mất tiêu điểm vẫn tự dọn.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
