# -*- coding: utf-8 -*-
"""Kiểm hồi quy cá nhân hóa bằng Chromium, không kết nối máy rang thật.

Chạy: python tools/test_ui_personalization.py
Kiểm lưu/tải lại, ảnh hỏng, bộ nhớ đầy, tương phản, bàn phím, báo lỗi và bố cục.
"""
import base64
import pathlib
import sys

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
APP = pathlib.Path(__file__).resolve().parent.parent / "OTL Roast Lab.html"
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/l9sAAAAASUVORK5CYII="
)


def boot(page):
    page.goto(APP.as_uri())
    page.wait_for_function("typeof PERSONAL !== 'undefined'")
    page.evaluate("document.getElementById('login').classList.remove('on')")


def main():
    errors = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        boot(page)
        page.click("#personalBtn")
        assert page.locator("#personalDialog").is_visible()

        page.click('[data-ps-theme="system"]')
        page.emulate_media(color_scheme="dark")
        page.wait_for_function("document.documentElement.dataset.theme==='dark'")
        assert page.evaluate("document.documentElement.dataset.theme") == "dark"
        page.emulate_media(color_scheme="light")
        page.wait_for_function("document.documentElement.dataset.theme==='light'")
        assert page.evaluate("document.documentElement.dataset.theme") == "light"
        assert page.evaluate("localStorage.getItem('otl_theme')") == "system"
        print("ĐẠT: theme theo hệ thống cập nhật trực tiếp")

        for theme in ("light", "dark"):
            for color in ("#ffff00", "#ffffff", "#000000", "#808080", "#00ff00", "#ff00ff"):
                result = page.evaluate("""([theme,color])=>{
                    setTheme(theme);personalHex(color);
                    const s=getComputedStyle(document.documentElement);
                    const lum=k=>personalLum(personalRGB(s.getPropertyValue(k).trim()));
                    const ratio=(a,b)=>(Math.max(a,b)+.05)/(Math.min(a,b)+.05);
                    return [ratio(lum('--accent'),lum('--accent-ink')),
                            ratio(lum('--card'),lum('--accent-txt'))];
                }""", [theme, color])
                assert min(result) >= 4.5, (theme, color, result)
        boot(page)
        assert page.evaluate("localStorage.getItem('otl_accent_hex')") == "#ff00ff"
        assert page.evaluate("document.documentElement.dataset.accent") == "custom"
        print("ĐẠT: màu cực trị vẫn đọc được; màu riêng giữ sau khi tải lại")

        page.click("#personalBtn")
        page.click('[data-ps-tab="wall"]')
        page.locator("#psFile").set_input_files({"name": "sample.png", "mimeType": "image/png", "buffer": PNG})
        page.wait_for_function("PERSONAL.wall==='custom'")
        wallpaper = page.evaluate("localStorage.getItem('otl_wallpaper')")
        assert wallpaper.startswith("data:image/jpeg;base64,")
        page.locator("#psFile").set_input_files({"name": "broken.png", "mimeType": "image/png", "buffer": b"invalid"})
        page.wait_for_function("document.getElementById('psStatus').dataset.error==='true'")
        assert page.evaluate("localStorage.getItem('otl_wallpaper')") == wallpaper
        page.locator("#psFile").set_input_files({"name": "unsafe.svg", "mimeType": "image/svg+xml", "buffer": b"<svg/>"})
        assert page.locator("#psStatus").get_attribute("data-error") == "true"
        assert page.evaluate("localStorage.getItem('otl_wallpaper')") == wallpaper
        boot(page)
        assert page.evaluate("PERSONAL.wall") == "custom"
        print("ĐẠT: nhập ảnh, tải lại, từ chối ảnh hỏng/SVG và giữ ảnh cũ")

        page.click("#personalBtn")
        page.evaluate("""() => {
            window.__storageSet=Storage.prototype.setItem;
            Storage.prototype.setItem=function(){throw new DOMException('Full','QuotaExceededError');};
            personalSet('opacity',70);
        }""")
        assert page.locator("#psStatus").get_attribute("data-error") == "true"
        page.evaluate("() => {Storage.prototype.setItem=window.__storageSet;}")
        print("ĐẠT: bộ nhớ đầy báo lỗi, giao diện vẫn hoạt động")

        page.evaluate("""() => {
            window.__full=0;
            window.pywebview={api:{toggle_fullscreen:()=>{window.__full++;}}};
        }""")
        page.keyboard.press("Escape")
        assert not page.locator("#personalDialog").is_visible()
        assert page.evaluate("window.__full") == 0
        page.evaluate("() => {window.__answer='pending';askConfirm('Delete?','Test').then(v=>window.__answer=v);}")
        page.keyboard.press("Escape")
        assert page.evaluate("window.__answer") is None
        assert page.evaluate("window.__full") == 0
        page.evaluate("""() => {
            window.__first='pending';window.__second='pending';
            askConfirm('First','').then(v=>window.__first=v);
            askConfirm('Second','').then(v=>window.__second=v);
        }""")
        assert page.evaluate("window.__first") is None
        page.wait_for_timeout(60)
        for _ in range(4):
            page.keyboard.press("Tab")
            assert page.evaluate("document.activeElement.id") in ("askNo", "askYes")
        page.keyboard.press("Escape")
        assert page.evaluate("window.__second") is None
        print("ĐẠT: Escape không đổi toàn màn hình; xác nhận không treo và giữ focus")

        page.evaluate("""() => {
            window.__writes=[];
            pywebview.api.link_snapshot=async()=>({state:'connected',mode:'pclink',data:DS.snap});
            pywebview.api.link_write=async(n,v)=>{window.__writes.push([n,v]);return {ok:true};};
            DS.state='connected';DS.mode='pclink';
            DS.snap={bt:100,flags:{pc_control:true,flame:true,gas:true}};
            R.phase='IDLE';R._machRun=false;R._autoCharge=false;R.chargeT=200;
            startRoast();
        }""")
        page.wait_for_function("document.getElementById('askbox').classList.contains('on')")
        page.keyboard.press("Escape")
        assert page.evaluate("R._autoCharge") is False
        assert page.evaluate("window.__writes") == []
        page.evaluate("() => {startRoast();}")
        page.click("#askNo")
        # Từ 14/09 (review RF-03) chờ tự nạp là LỜI HẸN gắn hồ sơ {no,name,t}, không còn true trần
        assert page.evaluate("!!R._autoCharge && R._autoCharge.t===200") is True
        assert page.evaluate("window.__writes") == []
        page.evaluate("""() => {
            delete pywebview.api.link_snapshot;
            R._autoCharge=false;R.phase='NOSEL';DS.state='nobridge';DS.snap=null;
        }""")
        print("ĐẠT: Escape không tự bật chờ nạp; chỉ bấm nút Chờ mới bật")

        page.click("#personalBtn")
        page.evaluate("DS.state='stalled';faultCheck(null)")
        assert not page.locator("#personalDialog").is_visible()
        assert "show" in page.locator("#faultBanner").get_attribute("class")
        page.evaluate("DS.state='nobridge';faultCheck(null)")
        print("ĐẠT: cảnh báo máy tự đóng cá nhân hóa để hiện ngay")

        page.evaluate("""() => {
            window.__attempts=0;_stLast='';
            pywebview.api.state_save=async()=>({ok:++window.__attempts>1});
        }""")
        page.evaluate("stateSync()")
        page.evaluate("stateSync()")
        assert page.evaluate("window.__attempts") == 2
        page.evaluate("stateSync()")
        assert page.evaluate("window.__attempts") == 2
        print("ĐẠT: lưu trạng thái thất bại được thử lại")

        page.click("#personalBtn")
        page.click('[data-ps-tab="sound"]')
        page.evaluate("personalVolume(30);personalSet('tone','glass')")
        page.click('[data-ps-sound="on"]')
        assert page.locator("#psVolume").is_disabled()
        assert page.locator("#psListen").is_disabled()
        boot(page)
        assert page.evaluate("SND.on") is False
        assert page.evaluate("SND.vol") == .3
        assert page.evaluate("PERSONAL.tone") == "glass"
        print("ĐẠT: âm thanh, âm lượng và chất âm giữ sau khi mở lại")

        page.evaluate("personalSet('motion','reduced');gotoTab('hoso')")
        assert page.evaluate("getComputedStyle(document.getElementById('pane-hoso')).animationName") == "none"
        page.evaluate("personalSet('motion','full')")
        page.emulate_media(reduced_motion="reduce")
        assert page.evaluate("getComputedStyle(document.getElementById('pane-hoso')).animationName") == "none"
        print("ĐẠT: giảm chuyển động ở cả app và hệ điều hành")

        for width, height in ((1920, 1080), (1366, 768), (1024, 768), (390, 844)):
            page.set_viewport_size({"width": width, "height": height})
            page.evaluate("LANG='en';applyLang();personalOpen()")
            for tab in ("look", "wall", "sound"):
                page.click(f'[data-ps-tab="{tab}"]')
                overflow = page.evaluate("""() => [...document.querySelectorAll('#personalDialog *')]
                    .filter(e=>e.getBoundingClientRect().width>0 && !e.closest('svg'))
                    .filter(e=>e.scrollWidth>e.clientWidth+2 && getComputedStyle(e).overflowX==='visible')
                    .map(e=>e.className||e.id)""")
                assert not overflow, (width, tab, overflow)
                close = page.locator("#psClose").bounding_box()
                assert close and close['x'] >= 0 and close['y'] >= 0
                assert close['x'] + close['width'] <= width and close['y'] + close['height'] <= height
            page.keyboard.press("Escape")
        print("ĐẠT: bảng tùy chỉnh không tràn ở 1920 / 1366 / 1024 / 390 px")

        page.evaluate("""() => {
          localStorage.setItem('otl_snd_cfg',JSON.stringify({vol:-50,on:'false',ctx:'broken'}));
          localStorage.setItem('otl_personal_v1',JSON.stringify({opacity:'bad',blur:999,wall:'bad'}));
          localStorage.setItem('otl_theme','broken');localStorage.setItem('otl_lang','broken');
        }""")
        boot(page)
        assert page.evaluate("SND.vol") == 0
        assert page.evaluate("SND.ctx===null")
        assert page.evaluate("PERSONAL.opacity") == 45
        assert page.evaluate("PERSONAL.blur") == 24
        assert page.evaluate("document.documentElement.dataset.theme") == "dark"
        assert page.evaluate("LANG") == "vi"
        assert not errors, errors
        print("ĐẠT: sở thích hỏng được chuẩn hóa; không có lỗi JavaScript")
        browser.close()
    print("TẤT CẢ ĐẠT")


if __name__ == '__main__':
    main()
