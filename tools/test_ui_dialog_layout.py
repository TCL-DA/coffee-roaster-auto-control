"""Kiểm hộp thoại và vị trí điều khiển khi đổi kích thước, không kết nối máy thật."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from test_ui_audit import PROBE, dang_nhap


def main():
    with sync_playwright() as p:
        browser=p.chromium.launch()
        page=browser.new_page(viewport={'width':1366,'height':768})
        page.goto((Path(__file__).resolve().parent.parent/'OTL Roast Lab.html').as_uri())
        dang_nhap(page)
        page.evaluate('newProfile();closeProfEdit()')
        for width,height in [(1920,1080),(1366,768),(1280,800),(1024,768)]:
            page.set_viewport_size({'width':width,'height':height})
            page.evaluate('refit()')
            page.wait_for_timeout(120)
            for dialog in ['profedit','napedit','scalebox','roastmgr','batchDetail','batchCompare','portpick','askbox','keyboard','numpad']:
                page.evaluate("""id=>{
                  document.querySelectorAll('.overlay').forEach(e=>e.classList.remove('on'));
                  document.getElementById(id).classList.add('on');
                }""",dialog)
                result=page.evaluate(PROBE.replace('__TAP__','44'))
                assert not result['overflow'],(width,dialog,result['overflow'])
                assert not result['overlap'],(width,dialog,result['overlap'])
                assert page.evaluate("""id=>{
                  const e=document.getElementById(id).firstElementChild,r=e.getBoundingClientRect();
                  return r.left>=-1&&r.right<=innerWidth+1&&r.top>=-1&&r.bottom<=innerHeight+1;
                }""",dialog),(width,dialog)
        page.evaluate("document.querySelectorAll('.overlay').forEach(e=>e.classList.remove('on'));gotoTab('rang');setRoastPhase('RUNNING')")
        before=page.locator('.outrow.drum').bounding_box()
        page.evaluate("uxCommandStart('gas',30)")
        after=page.locator('.outrow.drum').bounding_box()
        assert abs(before['y']-after['y'])<1
        assert abs(before['height']-after['height'])<1
        browser.close()
    print('ĐẠT: 10 hộp thoại ở 4 kích thước; thông báo lệnh không dịch chuyển cụm điều khiển.')


if __name__=='__main__':
    main()
