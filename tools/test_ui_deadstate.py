# -*- coding: utf-8 -*-
"""Soát TRẠNG THÁI CHẾT — luật CSS không ăn, nút không làm gì, chữ nói sai việc.

26 bộ kiểm trước đã phủ màu/tương phản/chuyển động/vùng bấm/cử chỉ chạm. Bộ này
đi vào bốn chỗ CHƯA ai đo, đều thuộc một họ: **app TƯỞNG mình đang nói điều gì
đó với thợ, mà thật ra không**.

D · Mã chết      — luật CSS có mặt, lớp có được gắn đúng theo trạng thái, nhưng
                   một luật khác đặc hiệu hơn đè mất nên KHÔNG BAO GIỜ hiện ra.
                   Ở đây: `.tbtn.warn.idle` (3 lớp) thua `#btnDrop` và
                   `#stage #pane-rang #btnDrop` (ID), làm nút "Kết thúc mẻ" đỏ
                   rực cả lúc máy đứng yên — nút nguy hiểm nhất lại bắt mắt nhất.
N · Nút câm      — mở kho rỗng mà Xuất CSV / Xóa bộ lọc / Bỏ chọn mẻ vẫn bấm
                   được. Trước/Sau thì khoá đúng, chứng tỏ là bỏ sót chứ không
                   phải chủ ý.
H · Nhãn sai việc— cụm nút hệ trọng chỉ ăn khi GIỮ, mà nhãn ghi "Cần xác nhận"
                   nên thợ chạm hoài không có gì xảy ra. Nhãn phải dạy cách bấm,
                   và số giây phải lấy từ HOLD_MS để không lệch.
S · Số bước đá nhau — thẻ "Chuẩn bị mẻ rang" (thang 3 bước) dùng lại nguyên câu
                   của dải #uxGuide (thang 4 bước), nên hiện "1 · Chọn hồ sơ"
                   ngay trên danh sách mà bước 1 là "Làm nóng máy".

Chạy: python tools/test_ui_deadstate.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from test_ui_audit import dang_nhap  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parent.parent
# OTL_APP_HTML cho phép trỏ sang BẢN SAO đã gỡ bản vá, để chứng minh bộ kiểm này
# không vô dụng (gỡ vá ra là phải hỏng). Không đặt thì chạy trên file thật.
import os  # noqa: E402
APP = pathlib.Path(os.environ.get("OTL_APP_HTML") or (ROOT / "OTL Roast Lab.html"))


def _rgb(s):
    """Nhận cả 'rgb(r,g,b)' lẫn '#RRGGBB' — token CSS trả về hex, getComputedStyle
    trả về rgb(), so hai thứ đó với nhau nên phải quy về một dạng."""
    s = s.strip()
    if s.startswith("#"):
        h = s[1:]
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    return tuple(int(float(x)) for x in s.replace("rgb(", "").replace("rgba(", "")
                 .rstrip(")").split(",")[:3])


def _lum(c):
    def f(v):
        v /= 255
        return v / 12.92 if v <= .03928 else ((v + .055) / 1.055) ** 2.4
    r, g, b = (f(x) for x in c)
    return .2126 * r + .7152 * g + .0722 * b


def tuong_phan(a, b):
    la, lb = _lum(_rgb(a)), _lum(_rgb(b))
    hi, lo = max(la, lb), min(la, lb)
    return (hi + .05) / (lo + .05)


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

        # ── D · "Kết thúc mẻ" phải DỊU khi chưa vào mẻ ───────────────────────
        pg.evaluate("() => gotoTab('rang')")
        pg.wait_for_timeout(800)
        d = pg.evaluate("""() => {
          const bd=document.getElementById('btnDrop');
          const esc=document.getElementById('btnEscape');
          const cs=getComputedStyle(bd), ce=getComputedStyle(esc);
          return {idle:bd.classList.contains('idle'), phase:(window.R||{}).phase,
                  drop:cs.color, dropBd:cs.borderTopColor, esc:ce.color,
                  mute:getComputedStyle(document.documentElement)
                        .getPropertyValue('--mute').trim()};
        }""")
        if not d["idle"]:
            loi.append(f"D1 · chưa vào mẻ (phase={d['phase']}) mà btnDrop KHÔNG có lớp .idle")
        else:
            # BẪY ĐÃ TRẢ GIÁ: lần đầu đo bằng TỶ LỆ TƯƠNG PHẢN giữa hai nút. Sai —
            # tương phản chỉ đo ĐỘ SÁNG, mà xám --mute rgb(132,132,143) và cam-đỏ
            # rgb(239,117,107) gần như cùng độ sáng, ra 1,3 dù mắt thấy khác hẳn.
            # Bản vá ĐÚNG vẫn bị báo hỏng. Phải so thẳng với token --mute.
            if _rgb(d["drop"]) != _rgb(d["mute"]):
                loi.append(
                    f"D2 · .idle không ăn: 'Kết thúc mẻ' ra {d['drop']} chứ không "
                    f"phải --mute ({d['mute']}) — luật CSS bị luật ID đè")
            if _rgb(d["drop"]) == _rgb(d["esc"]):
                loi.append("D3 · 'Kết thúc mẻ' lúc rảnh vẫn cùng màu 'Xả liệu'")

        # ── H · nhãn cụm nút hệ trọng phải dạy cách bấm ──────────────────────
        h = pg.evaluate("""() => ({
          txt:(document.getElementById('tbDangerLbl').textContent||'').trim(),
          ms:(typeof HOLD_MS!=='undefined')?HOLD_MS:null})""")
        if not h["txt"]:
            loi.append("H1 · nhãn cụm nút hệ trọng rỗng")
        else:
            if "giữ" not in h["txt"].lower() and "hold" not in h["txt"].lower():
                loi.append(f"H2 · nhãn “{h['txt']}” không nói phải GIỮ — thợ sẽ chạm hoài")
            giay = str(round(h["ms"] / 1000, 1)).rstrip("0").rstrip(".")
            if giay.replace(".", ",") not in h["txt"] and giay not in h["txt"]:
                loi.append(f"H3 · nhãn “{h['txt']}” không khớp HOLD_MS={h['ms']}ms")

        # ── N · kho rỗng thì ba nút kia phải khoá và nói lý do ───────────────
        pg.evaluate("() => gotoTab('lichsu')")
        pg.wait_for_timeout(900)
        for eid, ten in (("histCsvBtn", "Xuất CSV"),
                         ("uxHistReset", "Xóa bộ lọc"),
                         ("uxHistClear", "Bỏ chọn mẻ")):
            n = pg.evaluate("(id)=>{const e=document.getElementById(id);"
                            "return e?{dis:e.disabled===true,ti:e.title||''}:null}", eid)
            if n is None:
                loi.append(f"N0 · không thấy nút #{eid}")
            elif not n["dis"]:
                loi.append(f"N1 · kho rỗng mà “{ten}” vẫn bấm được — bấm chẳng làm gì")
            elif not n["ti"]:
                loi.append(f"N2 · “{ten}” khoá mà câm, không nói lý do")

        # gõ vào ô tìm kiếm → "Xóa bộ lọc" PHẢI mở lại (kho vẫn rỗng)
        pg.fill("#uxHistSearch", "zzz-khong-co-that")
        pg.wait_for_timeout(1400)
        r = pg.evaluate("() => document.getElementById('uxHistReset').disabled===true")
        if r:
            loi.append("N3 · đang lọc mà “Xóa bộ lọc” vẫn khoá — thợ kẹt trong bộ lọc rỗng")
        pg.fill("#uxHistSearch", "")
        pg.wait_for_timeout(1200)

        # ── S · thẻ Chuẩn bị mẻ rang không được đánh số đá nhau ──────────────
        pg.evaluate("() => gotoTab('tongquan')")
        pg.wait_for_timeout(900)
        s = pg.evaluate("""() => ({
          sub:(document.getElementById('ovPrepSub').textContent||'').trim(),
          steps:[...document.querySelectorAll('.ovstep')].map(x=>({
            n:x.querySelector('.ovstep-n').textContent.trim(),
            t:x.querySelector('.ovstep-t').textContent.trim()}))})""")
        import re
        m = re.match(r"^\s*(\d+)\s*·", s["sub"])
        if m:
            loi.append(f"S1 · phụ đề còn tiền tố số “{m.group(1)} ·” trong khi thẻ "
                       f"tự đánh số riêng ({', '.join(x['n']+'='+x['t'] for x in s['steps'])})"
                       f" — hai hệ số đá nhau")

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
    print("ĐẠT — trạng thái chết đã hết: nút hệ trọng dịu đúng lúc, nhãn dạy cách "
          "bấm, nút kho rỗng khoá có lý do, số bước không đá nhau.")
