# -*- coding: utf-8 -*-
"""Kiểm app ẩn / hiện thiết bị theo CẤU HÌNH MÁY $M62 của firmware (gói R0, 13/10/2026 — include/MachineOpt.h).
Luật:
  · mc_opt = null hoặc bit 15 = 0 (máy cũ / chưa cấu hình / chưa đọc được) -> giữ cách cũ theo ô tích của app
  · máy đã cấu hình -> nút Loader / Cân / Destoner / Afterburner / Mixer / Drum-fan + thẻ áp hút theo đúng bit; ô tích khoá
    python tools/test_ui_mc_opt.py"""
from pathlib import Path
import sys
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')
APP = Path(__file__).resolve().parent.parent / 'OTL Roast Lab.html'
DU = 0x8000 | (3 << 6) | 0x0004 | 0x0008 | 0x0010 | 0x0020 | 0x0200 | 0x0400 | 0x0800   # 30 kg đủ bộ = 36604
TRON = 0x8000 | (3 << 6)                                                                  # 30 kg không thiết bị phụ
NUT = ('btnLoader', 'btnScale', 'btnDestoner', 'btnAB', 'btnMixer', 'btnDrumFan')
KQ = []


def kiem(ten, dat, ct=''):
    KQ.append(dat)
    print(('DAT ' if dat else 'LOI ') + ten + ('' if dat else '  | %s' % (ct,)), flush=True)


def hien(page):
    return page.evaluate("""(ids) => Object.fromEntries(ids.map(id => {const e = document.getElementById(id);
        return [id, !!e && getComputedStyle(e).display !== 'none'];}))""", list(NUT) + ['vacCard'])


def main():
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={'width': 1280, 'height': 800})
        page.goto(APP.as_uri())
        page.wait_for_timeout(1500)
        page.evaluate("() => { window.toast = () => {}; }")
        # máy cũ: null -> theo ô tích (mặc định app: có mọi thiết bị, không có áp hút)
        page.evaluate("() => setMcOpt(null)")
        h = hien(page)
        kiem('mc_opt null: các nút thiết bị theo ô tích (hiện)', all(h[k] for k in NUT), h)
        kiem('mc_opt null: thẻ áp hút theo ô tích (dv_vacuum mặc định 0 -> ẩn)', not h['vacCard'], h)
        page.evaluate("(v) => setMcOpt(v)", 0x00FF)                   # bit 15 = 0: chưa cấu hình -> vẫn theo ô tích
        kiem('chưa cấu hình (bit 15 = 0): vẫn theo ô tích', hien(page) == h, hien(page))
        page.evaluate("(v) => setMcOpt(v)", DU)
        h = hien(page)
        kiem('đủ bộ: mọi nút + thẻ áp hút hiện', all(h.values()), h)
        page.evaluate("(v) => setMcOpt(v)", TRON)
        h = hien(page)
        kiem('trơn: ẩn Loader, Cân, Destoner, Afterburner, Mixer, Drum-fan, áp hút', not any(h.values()), h)
        page.evaluate("(v) => setMcOpt(v)", TRON | 0x0008)
        h = hien(page)
        kiem('chỉ loader (không cân): Loader hiện, Cân ẩn', h['btnLoader'] and not h['btnScale'], h)
        khoa = page.evaluate("""() => Object.fromEntries([...document.querySelectorAll('#devEnRow .permchk')]
            .map(c => [c.dataset.devEn, c.classList.contains('locked')]))""")
        # làm nguội có ở mọi máy (không có bit trong $M62) -> ô của nó vẫn mở
        kiem('ô tích thiết bị theo $M62 khoá, Làm nguội vẫn mở',
             all(v for k, v in khoa.items() if k != 'cooling') and not khoa.get('cooling', False), khoa)
        page.evaluate("() => setMcOpt(null)")
        khoa = page.evaluate("""() => [...document.querySelectorAll('#devEnRow .permchk')].map(c => c.classList.contains('locked'))""")
        kiem('mất nối (null): ô tích mở lại', not any(khoa), khoa)
        b.close()
    print('KET LUAN:', 'DAT' if all(KQ) else 'LOI', '(%d/%d)' % (sum(KQ), len(KQ)))
    sys.exit(0 if all(KQ) else 1)


if __name__ == '__main__':
    main()
