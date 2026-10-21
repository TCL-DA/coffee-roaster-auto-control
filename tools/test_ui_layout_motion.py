# -*- coding: utf-8 -*-
"""Kiểm bố cục và chuyển động: lối tắt hồ sơ, tab trượt, hình nền và mẻ đang rang."""
from pathlib import Path
import sys
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')
APP = Path(__file__).resolve().parent.parent / 'OTL Roast Lab.html'

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1366, 'height': 768})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto(APP.as_uri())
    page.evaluate("document.getElementById('login').classList.remove('on');gotoTab('tongquan')")
    page.wait_for_timeout(350)
    assert page.locator('.ov-profile').count() == 3
    page.evaluate("""() => {
        const profiles=loadProfiles();profiles[2].fav=true;
        profiles[2].name='<img src=x onerror=alert(1)>'+'x'.repeat(150);
        localStorage.setItem(LS_PROF,JSON.stringify(profiles));renderOverviewQuick();
    }""")
    assert page.locator('.ov-profile').first.locator('strong').inner_text().startswith('★ <img')
    assert page.locator('#ovQuickGrid img').count() == 0
    assert page.evaluate("document.getElementById('ovQuickGrid').scrollWidth<=document.getElementById('ovQuickGrid').clientWidth")
    page.locator('.ov-profile').first.click()
    assert page.evaluate('R.profNo') == 3
    assert page.evaluate('R.phase') == 'IDLE'
    print('ĐẠT: hồ sơ yêu thích lên trước, tên dài không tràn, không chèn HTML, bấm chọn đúng hồ sơ')

    page.evaluate("R.phase='RUNNING';gotoTab('tongquan')")
    before = page.evaluate('R.profName')
    page.locator('.ov-profile').nth(1).click()
    assert page.evaluate('R.profName') == before
    assert page.evaluate('R.phase') == 'RUNNING'
    assert page.locator('#pane-rang').get_attribute('class').endswith('on')
    print('ĐẠT: lối tắt không thay hồ sơ khi mẻ đang chạy')

    page.evaluate("R.phase='NOSEL'")
    for width, height in [(1920, 1080), (1366, 768), (1280, 800)]:
        page.set_viewport_size({'width': width, 'height': height})
        for lang in ('vi', 'en'):
            page.evaluate('(l)=>{LANG=l;applyLang();}', lang)
            for tab in ('tongquan', 'rang', 'hoso', 'lichsu', 'caidat'):
                page.evaluate('(t)=>gotoTab(t)', tab)
                result = page.evaluate("""() => {
                    const nav=document.getElementById('tabnav'),b=nav.querySelector('.tab.on');
                    return Math.abs(parseFloat(nav.style.getPropertyValue('--nav-x'))-b.offsetLeft)<1
                      && Math.abs(parseFloat(nav.style.getPropertyValue('--nav-width'))-b.offsetWidth)<1;
                }""")
                assert result, (width, lang, tab)
    print('ĐẠT: nền tab chọn khớp đúng nút khi đổi ngôn ngữ và kích thước')

    page.evaluate("personalSet('motion','full');gotoTab('rang')")
    page.wait_for_timeout(30)
    assert page.evaluate("getComputedStyle(document.getElementById('pane-rang')).transform") == 'none'
    page.evaluate("personalOpen();personalTab('wall');personalSet('wall','forest')")
    assert page.evaluate("getComputedStyle(document.getElementById('stage'),'::before').animationName") == 'layout-wall'
    page.emulate_media(reduced_motion='reduce')
    assert page.evaluate("getComputedStyle(document.getElementById('stage'),'::before').animationName") == 'none'
    assert page.evaluate("getComputedStyle(document.getElementById('tabnav'),'::before').transitionDuration") == '0s'
    print('ĐẠT: màn rang không trượt nút; chuyển nền và giảm chuyển động hoạt động')
    assert not errors, errors
    browser.close()
print('TẤT CẢ ĐẠT')
