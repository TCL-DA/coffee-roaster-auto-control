"""Kiểm bố cục toàn app và các lỗi quan sát từ ảnh người dùng, không nối máy thật."""
from pathlib import Path
import sys
from playwright.sync_api import sync_playwright
from test_ui_audit import PROBE, dang_nhap


def main():
    with sync_playwright() as p:
        browser=p.chromium.launch()
        page=browser.new_page(viewport={'width':1366,'height':768})
        errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto((Path(__file__).resolve().parent.parent/'OTL Roast Lab.html').as_uri())
        dang_nhap(page)
        failures=[]
        for w,h in [(1920,1080),(1366,768),(1280,800)]:
            page.set_viewport_size({'width':w,'height':h})
            for theme in ['light','dark']:
                page.evaluate('(t)=>setTheme(t)',theme)
                for tab in ['tongquan','rang','hoso','lichsu','kho','caidat']:
                    page.evaluate('(t)=>gotoTab(t)',tab)
                    subs=['ketnoi','calib','model','maycfg','oplog','nhatky','taikhoan'] if tab=='caidat' else [None]
                    for sub in subs:
                        if sub:page.evaluate('(s)=>gotoSub(s)',sub)
                        page.wait_for_timeout(100)
                        # Đây là bài kiểm BỐ CỤC, phải đo lúc đứng yên. Từ 11/09/2026
                        # pane có hoạt ảnh vào (trượt 14px, 0,38s) nên chờ 100ms là đo
                        # đúng giữa lúc đang chạy và báo "tràn 3-6px" oan. Tua mọi hoạt
                        # ảnh HỮU HẠN về cuối — nhanh hơn ngồi chờ, và đo đúng thứ cần
                        # đo. Bỏ qua hoạt ảnh vô hạn (nhịp thở nút lửa) vì chúng không
                        # bao giờ kết thúc.
                        page.evaluate("""() => document.getAnimations()
                          .filter(a => { try { return a.effect &&
                              a.effect.getComputedTiming().iterations !== Infinity; }
                            catch(e){ return false; } })
                          .forEach(a => { try { a.finish(); } catch(e){} })""")
                        result=page.evaluate(PROBE.replace('__TAP__','44'))
                        for kind in ['overflow','overlap']:
                            if result[kind]:failures.append((w,theme,tab,sub,kind,result[kind]))
        page.evaluate("gotoTab('rang');setView('detail',true);setRoastPhase('NOSEL');uiPlaceRoastPanels()")
        assert page.evaluate("document.querySelector('.roast-nosel').parentElement.classList.contains('chartwrap')")
        assert page.evaluate("getComputedStyle(document.querySelector('.chartwrap')).opacity")=='1'
        assert page.evaluate("getComputedStyle(document.querySelector('.roast-nosel')).backdropFilter")=='none'
        assert page.evaluate("getComputedStyle(document.querySelector('.chartleg')).display")=='none'
        page.evaluate("setView('simple',true);uiPlaceRoastPanels()")
        assert page.locator('.roast-nosel').is_visible()
        page.evaluate("""()=>{
          setView('detail',true);DS.state='error';DS.snap=null;renderLinkChip();
        }""")
        # ltBT/ltET đã BỎ khỏi thanh đầu (đợt PD 08/09) — thiết kế không đặt nhiệt ở đó.
        for id in ['liveBT','liveET','ovBurner','ovAir','ovDrum']:
            assert page.locator('#'+id).inner_text()=='—',id
        assert 'ok' not in page.locator('#cnStMach').get_attribute('class').split()
        assert not errors,errors
        assert not failures,failures
        browser.close()
    print('ĐẠT: 6 tab và 7 trang cài đặt, 3 kích thước, sáng/tối; vùng chờ đúng chỗ và không hiện số cũ khi mất kết nối.')


if __name__=='__main__':
    main()
