# -*- coding: utf-8 -*-
"""Bộ kiểm gợi ý "MỨC LẦN TRƯỚC" của gas · gió · trống.

Ba thứ phải canh, theo đúng thứ tự nguy hiểm giảm dần:

 1. KHÔNG ĐƯỢC TỐN CHIỀU CAO. Bản đầu làm một dải riêng bắc ngang trên ba ô điều
    khiển — nó chiếm một hàng của lưới, đẩy ba ô tụt 66px, thò khỏi khung và chui
    xuống dưới thanh nút đáy, cắt mất con số phần trăm. Chủ máy chụp ảnh gửi về
    mới lộ. Nay gợi ý nằm trong dòng chú thích sẵn có của từng ô.
 2. KHÔNG TỰ ÁP xuống máy. Mở app mà gas tự nhảy về mức hôm qua trên một trống
    rỗng đang có lửa là cách nhanh nhất để cháy trống.
 3. Gas phải hỏi lại trước khi mở; gió và trống thì không — bắt xác nhận thứ vô
    hại chỉ dạy thợ bấm "Đồng ý" theo phản xạ.

    python tools/test_ui_outlast.py
"""
import io
import os
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

GOC = Path(__file__).resolve().parent.parent
HTML = GOC / "OTL Roast Lab.html"
_loi = []


def kiem(ten, dk, gc=""):
    print(("  OK   " if dk else "  HỎNG ") + ten + (" → " + str(gc) if gc != "" else ""))
    if not dk:
        _loi.append(ten)


def doc_ma():
    s = io.open(HTML, encoding="utf-8").read()
    print("— đọc mã —")
    kiem("có ô lưu riêng trong localStorage", "LS_OUT_LAST='otl_out_last'" in s)
    kiem("machCmd gọi nhoMucCuoi sau khi lệnh xuống máy",
         re.search(r"uxCommandUpdate\(name,'queued',command\);[\s\S]{0,200}?nhoMucCuoi\(name,v\)", s) is not None)
    kiem("chỉ nhớ gas · gió · trống", "['gas','air','drum'].includes(name)" in s)
    kiem("KHÔNG còn dải riêng chiếm chiều cao", "outLast" not in s and ".outlast{" not in s)
    kiem("gợi ý dùng đúng dòng chú thích sẵn có",
         "OLAST_SLOT={gas:'hintBurner',air:'hintAir',drum:'hintDrum'}" in s)
    than = re.search(r"async function apMucCuoiMot\(k\)[\s\S]{0,900}?\n}", s)
    than = than.group(0) if than else ""
    kiem("chỉ GAS mới hỏi xác nhận",
         "if(k==='gas'){" in than and "askConfirm(" in than and than.count("askConfirm(") == 1)
    kiem("hộp xác nhận nói rõ lệnh xuống MÁY THẬT", "MÁY THẬT" in than)
    kiem("không có đường nào TỰ áp lúc mở app",
         len(re.findall(r"apMucCuoiMot\(", s)) <= 3, "%d chỗ gọi" % len(re.findall(r"apMucCuoiMot\(", s)))


def chay_that():
    print("— chạy thật trong trình duyệt —")
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1920, "height": 1080})
        loi_js = []
        pg.on("pageerror", lambda e: loi_js.append(str(e)[:120]))
        pg.goto(HTML.as_uri())
        pg.wait_for_timeout(800)
        pg.evaluate("session={name:'M',role:'master',perms:{}};"
                    "document.getElementById('login').classList.remove('on');updateBadge();")
        pg.evaluate("gotoTab('rang')")
        pg.wait_for_timeout(400)

        def do():
            return pg.evaluate("""() => {
                const r = s => { const e = document.querySelector(s); if (!e) return null;
                  const b = e.getBoundingClientRect(); return [Math.round(b.top), Math.round(b.bottom)]; };
                return {o: r('#pane-rang .outrow.burner'), khung: r('.rangbody>.outcard'),
                        day: r('#pane-rang .toolbar'),
                        hint: ['hintBurner','hintAir','hintDrum'].map(i => {
                          const e = document.getElementById(i);
                          return e ? [e.classList.contains('olast'), e.textContent.trim().slice(0,34)] : null; })};
            }""")

        # chưa nhớ gì → không mời gì cả
        a = do()
        kiem("chưa có mức đã nhớ thì không mời áp",
             not any(h and h[0] for h in a["hint"]), a["hint"])

        # có mức đã nhớ + máy đang nối + chưa rang → mời ở cả ba ô
        pg.evaluate("""() => { DS.state='connected'; R.burner=71; R.air=14; R.drum=4;
            localStorage.setItem('otl_out_last', JSON.stringify({gas:40,air:20,drum:60,ts:Date.now()}));
            renderMucCuoi(); }""")
        pg.wait_for_timeout(300)
        b1 = do()
        kiem("cả ba ô đều mời áp lại", all(h and h[0] for h in b1["hint"]),
             [h[1] for h in b1["hint"]])
        kiem("gợi ý KHÔNG đẩy ba ô thò khỏi khung",
             b1["o"] == b1["khung"], "ô %s · khung %s" % (b1["o"], b1["khung"]))
        kiem("ba ô KHÔNG chui xuống dưới thanh nút đáy",
             b1["o"][1] <= b1["day"][0], "ô đáy %s · thanh nút %s" % (b1["o"][1], b1["day"][0]))

        # đang rang thì im, đừng mời đổi mức giữa mẻ
        pg.evaluate("R.phase='RUNNING';renderMucCuoi()")
        pg.wait_for_timeout(200)
        kiem("đang rang thì không mời", not any(h and h[0] for h in do()["hint"]))
        pg.evaluate("R.phase='IDLE';renderMucCuoi()")

        # mất kết nối cũng im
        pg.evaluate("DS.state='error';renderMucCuoi()")
        pg.wait_for_timeout(200)
        kiem("mất kết nối thì không mời", not any(h and h[0] for h in do()["hint"]))
        pg.evaluate("DS.state='connected';renderMucCuoi()")

        # mức máy đã trùng mức đã nhớ → thôi mời, và trả lại chữ cũ
        pg.evaluate("R.air=20;renderMucCuoi()")
        pg.wait_for_timeout(200)
        h = do()["hint"]
        kiem("mức đã trùng thì thôi mời", not h[1][0], h[1])
        # chú thích cũ là "công thức N% · giữ để chạy nhanh" khi đã nạp công thức,
        # còn chưa nạp thì chỉ có vế mẹo — miễn là KHÔNG còn lời mời áp lại.
        kiem("trả lại đúng chú thích cũ",
             h[1][1] and "chạm để áp" not in h[1][1] and "tap to apply" not in h[1][1], h[1][1])

        b.close()
    kiem("không có lỗi JS", not loi_js, "; ".join(loi_js)[:120])


def main():
    doc_ma()
    chay_that()
    print()
    if _loi:
        print("HỎNG %d mục:\n  - %s" % (len(_loi), "\n  - ".join(_loi)))
        return 1
    print("TẤT CẢ ĐẠT")
    return 0


if __name__ == "__main__":
    sys.exit(main())
