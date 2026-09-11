"""Kiểm menu nhanh trong màn hình và ngăn thoát nhầm lúc rang; không nối máy thật."""
from pathlib import Path
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto((Path(__file__).resolve().parent.parent / 'OTL Roast Lab.html').as_uri())
    page.evaluate("session={name:'Master',role:'master',perms:{}};document.getElementById('login').classList.remove('on');updateBadge();gotoTab('rang')")
    for width, height in [(1920,1080),(1366,768),(1280,800),(1024,768)]:
        page.set_viewport_size({'width':width,'height':height})
        page.wait_for_timeout(150)
        page.evaluate("renderWebRow({on:true,ip:'192.168.100.144',port:8555});document.getElementById('usermenu').classList.add('on');odPositionMenu()")
        box = page.locator('#usermenu').bounding_box()
        assert box['x'] >= 0 and box['y'] >= 0, box
        assert box['x'] + box['width'] <= width + 1, box
        assert box['y'] + box['height'] <= height + 1, box
        assert page.locator('#usermenu').evaluate('(e)=>e.scrollWidth<=e.clientWidth'), width
        assert page.locator('#ipChipV').inner_text() == '192.168.100.144:8555'
        assert page.locator('#odWebSwitch').get_attribute('aria-checked') == 'true'
        page.keyboard.press('Escape')
        # Từ 11/09/2026 menu có LƯỢT RA (.15s, `allow-discrete`) nên nó còn nằm
        # trong DOM một nhịp sau khi bấm Escape — hỏi ngay là thấy "vẫn hiện" và
        # đỏ oan. Chờ hết lượt ra rồi mới hỏi; điều cần khẳng định là menu ĐÓNG
        # HẲN, không phải là nó biến mất trong cùng mili-giây.
        page.wait_for_timeout(400)
        assert not page.locator('#usermenu').is_visible()
    page.evaluate("window.__exits=0;window.pywebview={api:{app_exit:()=>window.__exits++}};R.phase='RUNNING';appExit();appExit()")
    assert page.evaluate('window.__exits') == 0
    # Từ 08/09 xác nhận nằm ở CỬ CHỈ GIỮ 1 GIÂY, không còn bấm-hai-lần: appExit()
    # gọi thẳng là đã qua cửa xác nhận rồi, nên một lần gọi là thoát một lần.
    # Phần giữ nút được kiểm riêng ở test_ui_hold_confirm.py.
    page.evaluate("R.phase='IDLE';appExit()")
    assert page.evaluate('window.__exits') == 1
    assert not errors, errors
    browser.close()
print('PASS: menu trong khung 4 kich thuoc, IP day du, Escape, chan thoat khi rang.')
