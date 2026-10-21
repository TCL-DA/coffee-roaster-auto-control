"""Kiểm bố cục hai cột và khả năng chạm thiết bị phụ sau khi cuộn."""
from pathlib import Path
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser=p.chromium.launch()
    page=browser.new_page()
    page.goto((Path(__file__).resolve().parent.parent/'OTL Roast Lab.html').as_uri())
    page.evaluate("session={name:'Master',role:'master',perms:{}};document.getElementById('login').classList.remove('on');gotoTab('rang');setView('detail',true);setDevPin(1)")
    for w,h in [(1920,1080),(1440,900),(1366,768),(1280,800)]:
        page.set_viewport_size({'width':w,'height':h})
        page.wait_for_timeout(150)
        chart=page.locator('.chartcol').bounding_box()
        outputs=page.locator('.rangbody>.outcard').bounding_box()
        right=page.locator('.rightcol').bounding_box()
        aux=page.locator('.od-aux').bounding_box()
        assert abs(chart['x']-outputs['x'])<2
        assert outputs['x']+outputs['width']<=right['x']
        assert aux['height']>=90,(w,h,aux)
        for control in ['btnDrumFan','btnDestoner','devPin']:
            el=page.locator('#'+control)
            el.scroll_into_view_if_needed()
            assert el.evaluate('(e)=>{const r=e.getBoundingClientRect();return e.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2))}'),(w,control)
        page.evaluate('setDevPin(0)')
        assert page.locator('#devExpand').is_visible()
        page.locator('#devExpand').click()
        assert page.locator('#devstrip').is_visible()
    browser.close()
print('PASS: columns, output alignment, auxiliary scrolling and collapse at 4 sizes.')
