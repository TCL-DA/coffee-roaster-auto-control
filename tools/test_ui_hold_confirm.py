# -*- coding: utf-8 -*-
"""Kiểm cơ chế GIỮ 1 GIÂY cho lệnh hệ trọng (đợt PD, theo bản thiết kế Claude Design).

Luật phải giữ được: lệnh CHỈ đi khi giữ đủ HOLD_MS (chủ máy chốt 0,5 giây 08/09/2026). Nhả sớm, kéo ngón ra khỏi nút,
hay tắt chuyển động đều không được làm lệnh thoát ra sớm.
"""
from pathlib import Path
import sys
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')
APP = Path(__file__).resolve().parent.parent / 'OTL Roast Lab.html'

# Bẫy lệnh ở tầng THẤP NHẤT mà app tự viết: machCmd. Mọi đường gửi lệnh máy đều
# chui qua đây, nên đếm ở đây là đếm đúng cái đi ra dây.
SPY = """() => {
  window.__cmds = [];
  window.machCmd = async (name, value) => { window.__cmds.push([name, value]); return true; };
  // Ép dsBridge() = true thì vòng lấy dữ liệu 1 giây/lần sẽ tin là có cầu thật rồi
  // vấp. Chặn hẳn vòng đó: bộ kiểm này chỉ xét cử chỉ giữ nút, không xét dữ liệu.
  window.dsTick = () => {};
  window.pywebview = window.pywebview || { api: {} };
  window.dsBridge = () => true;
  // Giả lập cầu nối thì phải giả lập ĐỦ: từ 11/09/2026 các nút lệnh máy tự khoá
  // khi CÓ cầu mà CHƯA nối được máy (thợ khỏi giữ đủ 0,5 giây rồi mới bị từ
  // chối). Chỉ bật dsBridge mà bỏ quên DS.state là dựng đúng cái trạng thái bị
  // khoá đó, rồi bài kiểm tưởng cử chỉ giữ hỏng. Nói rõ là đã nối.
  try { if (typeof DS !== 'undefined' && DS) DS.state = 'connected'; } catch (e) {}
  window.toast = () => {};
  window.opLog = () => {};
}"""


def press(page, sel, ms, release='mouse'):
    """Đè nút trong ms mili giây rồi nhả theo kiểu chỉ định."""
    loc = page.locator(sel)
    box = loc.bounding_box()
    # Menu tài khoản dài hơn cửa sổ nên nút Thoát rơi khỏi tầm chuột — kéo vào đã.
    if box is None or box['y'] + box['height'] > page.viewport_size['height']:
        loc.scroll_into_view_if_needed()
        page.wait_for_timeout(120)
        box = loc.bounding_box()
    assert box is not None, f'{sel}: không lấy được vị trí nút'
    cx, cy = box['x'] + box['width'] / 2, box['y'] + box['height'] / 2
    page.mouse.move(cx, cy)
    page.mouse.down()
    page.wait_for_timeout(ms)
    if release == 'leave':                       # kéo ngón ra khỏi nút rồi mới nhả
        page.mouse.move(cx, box['y'] - 40)
        page.wait_for_timeout(60)
    page.mouse.up()
    page.wait_for_timeout(120)


def main():
    fails = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1366, 'height': 768})
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(APP.as_uri())
        page.evaluate("document.getElementById('login').classList.remove('on');gotoTab('rang')")
        page.evaluate("R.phase='RUNNING';R.mode='MANUAL'")
        page.wait_for_timeout(250)

        # 0) THANH CHẠY và LỆNH phải cùng một con số. Đây là chỗ dễ lệch nhất:
        #    đổi HOLD_MS mà quên đổi thời lượng .holdfill là thanh mới chạy nửa
        #    đường lệnh đã đi (hoặc chạy xong rồi mà còn phải giữ thêm) — thợ mất
        #    tin vào nút. Bộ kiểm bằng thời gian không bắt được, phải so thẳng.
        moc = page.evaluate('()=>HOLD_MS')
        page.evaluate("()=>document.getElementById('btnDrop').classList.add('holding')")
        page.wait_for_timeout(60)
        thanh = page.evaluate("""()=>{
            const e=document.querySelector('#btnDrop>.holdfill');
            const d=getComputedStyle(e).transitionDuration.split(',')[0].trim();
            return d.endsWith('ms')?parseFloat(d):parseFloat(d)*1000;}""")
        page.evaluate("()=>document.getElementById('btnDrop').classList.remove('holding')")
        if abs(thanh - moc) > 1:
            fails.append(f'thanh chạy {thanh:.0f}ms KHÁC mốc lệnh {moc}ms — nút nói dối')

        for sel, name in [('#btnEscape', 'escape'), ('#btnDrop', 'drop')]:
            # 1) nhả TRƯỚC mốc → KHÔNG được gửi gì
            page.evaluate(SPY)
            press(page, sel, 220)
            got = page.evaluate('window.__cmds')
            if got:
                fails.append(f'{sel}: nhả sau 0,22s mà vẫn gửi lệnh {got}')

            # 2) giữ ĐỦ mốc → gửi ĐÚNG MỘT lần
            page.evaluate(SPY)
            press(page, sel, 800)
            got = page.evaluate('window.__cmds')
            if len(got) != 1 or got[0][0] != name:
                fails.append(f'{sel}: giữ đủ mốc phải gửi đúng 1 lệnh {name}, thực tế {got}')

            # 3) giữ đủ lâu nhưng KÉO NGÓN RA khỏi nút → huỷ
            page.evaluate(SPY)
            press(page, sel, 260, release='leave')
            page.wait_for_timeout(900)
            got = page.evaluate('window.__cmds')
            if got:
                fails.append(f'{sel}: kéo ngón ra khỏi nút mà vẫn gửi {got}')

            # 4) chạm nhanh liên tiếp 5 cái → không lệnh nào lọt
            page.evaluate(SPY)
            for _ in range(5):
                press(page, sel, 90)
            got = page.evaluate('window.__cmds')
            if got:
                fails.append(f'{sel}: 5 cú chạm nhanh mà lọt lệnh {got}')

        print('ĐẠT: nhả sớm không gửi, giữ đủ gửi đúng một lần, kéo ra huỷ, chạm nhanh không lọt'
              if not fails else 'CÓ LỖI ở nhóm cơ bản')

        # 5) TẮT CHUYỂN ĐỘNG vẫn phải giữ đủ mốc — chốt an toàn, không phải trang trí
        page.evaluate("document.documentElement.setAttribute('data-motion','reduced')")
        page.evaluate(SPY)
        press(page, '#btnDrop', 220)
        if page.evaluate('window.__cmds'):
            fails.append('Giảm chuyển động: nhả sau 0,22s mà vẫn gửi lệnh')
        page.evaluate(SPY)
        press(page, '#btnDrop', 800)
        if len(page.evaluate('window.__cmds')) != 1:
            fails.append('Giảm chuyển động: giữ đủ mốc mà lệnh không đi')
        page.evaluate("document.documentElement.setAttribute('data-motion','full')")
        if not fails:
            print('ĐẠT: tắt chuyển động vẫn phải giữ đủ mốc, và giữ đủ thì lệnh vẫn đi')

        # 6) Thoát app bị chặn khi đang rang, kể cả khi giữ đủ lâu
        page.evaluate("""() => {
          window.__exit = 0;
          R.phase = 'RUNNING';        // các bước trên có thể đã đổi pha — nói rõ ý định
          window.dsTick = () => {};
          window.pywebview = window.pywebview || { api: {} };
          window.pywebview.api.app_exit = () => { window.__exit++; };
          document.getElementById('umExit').style.display = '';
          document.getElementById('usermenu').classList.add('on');
        }""")
        page.wait_for_timeout(120)
        press(page, '#umExit', 850)
        if page.evaluate('window.__exit') != 0:
            fails.append('Thoát app: đang rang mà vẫn thoát được')
        page.evaluate("R.phase='IDLE'")
        press(page, '#umExit', 850)
        if page.evaluate('window.__exit') != 1:
            fails.append('Thoát app: hết rang rồi mà giữ đủ mốc vẫn không thoát')
        if not fails:
            print('ĐẠT: thoát app chặn khi đang rang, cho phép khi máy rảnh')

        # 7) Nhãn quay về trạng thái gốc, không kẹt ở "Đang giữ…"
        page.evaluate(SPY)
        press(page, '#btnEscape', 300)
        page.wait_for_timeout(200)
        lbl = page.locator('#btnEscape [data-i18n="tb.eject"]').inner_text().strip()
        if lbl != 'Xả liệu':
            fails.append(f'Nhãn kẹt sau khi huỷ: "{lbl}" (phải về "Xả liệu")')
        else:
            print('ĐẠT: nhãn nút trở lại bình thường sau khi huỷ')

        if errors:
            fails.append(f'Lỗi JS: {errors[:3]}')
        browser.close()

    if fails:
        print('\nKHÔNG ĐẠT:')
        for f in fails:
            print(' -', f)
        sys.exit(1)
    print('\nTẤT CẢ ĐẠT — cử chỉ giữ-để-xác-nhận hoạt động đúng luật.')


if __name__ == '__main__':
    main()
