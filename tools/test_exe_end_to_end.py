# -*- coding: utf-8 -*-
"""Kiểm EXE THẬT — không phải file HTML trên đĩa.

Mọi bài test_ui_* đều nạp thẳng `OTL Roast Lab.html` bằng file://, nên chúng không
chứng minh được cái EXE sắp giao có đúng nội dung đó không, và cũng không đi qua cầu
Python thật. Bài này chạy chính EXE trong dist, rồi lái bản web mà EXE tự phục vụ:

    EXE (PyInstaller)  →  máy chủ web trong roast_lab_hmi.py  →  HTML nhúng trong EXE

Vẫn còn một chỗ KHÔNG kiểm được ở đây: cửa sổ WebView2 của bản desktop. Trình duyệt
của bài này là Chromium của Playwright. Hai thứ cùng nhân Chromium (WebView2 152 vs
Playwright 149 khi viết bài này) nên rủi ro khác biệt là thấp, nhưng không phải không.
"""
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parent.parent
EXE = ROOT / 'tools' / 'dist' / 'OTL Roast Lab HMI.exe'
PORT = 8555


def cong_mo(port, giay):
    """Đợi EXE mở cổng web. Trả True nếu mở kịp."""
    het = time.time() + giay
    while time.time() < het:
        with socket.socket() as s:
            s.settimeout(0.5)
            if s.connect_ex(('127.0.0.1', port)) == 0:
                return True
        time.sleep(0.5)
    return False


def main():
    if not EXE.exists():
        print('BỎ QUA: chưa có EXE ở', EXE)
        return
    fails = []
    pin = ''
    ini = EXE.parent / 'settings.ini'
    if ini.exists():
        for d in ini.read_text(encoding='utf-8', errors='ignore').splitlines():
            if d.strip().startswith('pin_dieu_khien'):
                pin = d.split('=', 1)[1].strip()

    proc = subprocess.Popen([str(EXE)], cwd=str(EXE.parent))
    try:
        if not cong_mo(PORT, 60):
            print('KHÔNG ĐẠT: EXE chạy nhưng không mở được cổng web', PORT)
            sys.exit(1)
        print(f'ĐẠT: EXE khởi động và mở cổng web {PORT}')

        with sync_playwright() as p:
            browser = p.chromium.launch()
            ctx = browser.new_context(viewport={'width': 1366, 'height': 768}, has_touch=True)
            page = ctx.new_page()
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.goto(f'http://127.0.0.1:{PORT}/', wait_until='domcontentloaded')
            page.wait_for_timeout(1500)

            # 1) HTML do EXE phục vụ phải là bản MỚI — có đủ mã của đợt này
            co = page.evaluate("""() => ({
                giu: typeof holdBind === 'function',
                bac: typeof outAccelStep === 'function',
                day: typeof outFlush === 'function',
                vach: !!document.getElementById('ackBurner'),
                btcu: !!document.getElementById('ltBT')
            })""")
            thieu = [k for k, v in co.items() if k != 'btcu' and not v]
            if thieu:
                fails.append(f'EXE đang ôm HTML CŨ — thiếu {thieu}')
            elif co['btcu']:
                fails.append('EXE đang ôm HTML CŨ — BT/ET trên thanh đầu lẽ ra đã bỏ')
            else:
                print('ĐẠT: HTML trong EXE đúng là bản mới (có giữ 1 giây, bậc nhảy, vạch mốc)')

            # 2) Bậc nhảy và ngưỡng đúng như đã chốt với chủ máy
            so = page.evaluate("({step:OUT_STEP, accel:OUT_ACCEL, day:OUT_PUSH_MS, lap:OUT_REPEAT_MS})")
            if so['step'] != 1 or so['day'] != 1000:
                fails.append(f'thông số nút ± trong EXE sai: {so}')
            else:
                print(f'ĐẠT: trong EXE — chạm ±{so["step"]}, đẩy máy mỗi {so["day"]}ms, '
                      f'lặp {so["lap"]}ms, bậc {so["accel"]}')

            # 3) Cử chỉ giữ 1 giây chạy thật trên bản do EXE phục vụ
            page.evaluate("""() => {
                document.getElementById('login').classList.remove('on');
                gotoTab('rang'); R.phase='RUNNING'; R.mode='MANUAL';
                window.__cmds=[]; window.dsTick=()=>{};
                window.machCmd = async (n,v) => { window.__cmds.push([n,v]); return true; };
                window.dsBridge = () => true; window.toast=()=>{}; window.opLog=()=>{};
                // Từ 11/09/2026 nút lệnh máy tự khoá khi CÓ cầu nối mà CHƯA nối được
                // máy — để thợ khỏi giữ đủ 0,5 giây rồi mới bị từ chối. Bài này chỉ
                // đo CỬ CHỈ GIỮ nên phải dựng trạng thái "đã nối".
                // HAI BẪY đã trả giá ở đây, đừng đạp lại:
                //  1. Gán `window.dsBridge` KHÔNG với tới mã app — `dsBridge` khai
                //     bằng const nên nằm trong phạm vi từ vựng, không phải thuộc
                //     tính của window. App vẫn đọc bản gốc.
                //  2. Gán thẳng `DS.state='connected'` chỉ sống được ~1,5s: trong
                //     EXE có vòng dữ liệu THẬT chạy mỗi giây và ghi đè nó về
                //     undefined, nút khoá lại, bài kiểm đỏ oan.
                // Nên khoá cứng bằng getter — vòng dữ liệu ghi vào thì rơi vào hư vô.
                try { Object.defineProperty(DS, 'state',
                      { get: () => 'connected', set: () => {}, configurable: true }); } catch(e) {}
            }""")
            page.wait_for_timeout(300)
            cdp = ctx.new_cdp_session(page)
            b = page.locator('#btnEscape').bounding_box()
            x, y = b['x'] + b['width'] / 2, b['y'] + b['height'] / 2
            for giu_ms, mong in ((400, 0), (1250, 1)):
                page.evaluate('window.__cmds=[]')
                cdp.send('Input.dispatchTouchEvent',
                         {'type': 'touchStart', 'touchPoints': [{'x': x, 'y': y, 'id': 0}]})
                page.wait_for_timeout(giu_ms)
                cdp.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})
                page.wait_for_timeout(250)
                n = len(page.evaluate('window.__cmds'))
                if n != mong:
                    fails.append(f'trong EXE: giữ {giu_ms}ms phải cho {mong} lệnh, thực tế {n}')
            if not fails:
                print('ĐẠT: trong EXE — chạm nhanh không xả, giữ đủ 1 giây mới xả')

            if errors:
                fails.append(f'Lỗi JS trên bản EXE phục vụ: {errors[:3]}')
            browser.close()
    finally:
        # terminate() chỉ giết tiến trình cha; pywebview đẻ thêm tiến trình con nên
        # phải quét theo TÊN, nếu không cửa sổ app còn nằm lại trên màn chủ máy và
        # khoá luôn file EXE cho lần build sau (WinError 5).
        try:
            proc.terminate()
            proc.wait(timeout=8)
        except Exception:
            pass
        subprocess.run(['taskkill', '/IM', EXE.name, '/F'], capture_output=True)
        time.sleep(1.5)
        con = subprocess.run(['tasklist'], capture_output=True, text=True,
                             errors='ignore').stdout
        if EXE.name.lower() in con.lower():
            print('CẢNH BÁO: vẫn còn tiến trình EXE sót lại, đóng tay giùm')

    if fails:
        print('\nKHÔNG ĐẠT:')
        for f in fails:
            print(' -', f)
        sys.exit(1)
    print('\nTẤT CẢ ĐẠT — EXE thật chạy đúng, ôm đúng HTML mới.')


if __name__ == '__main__':
    main()
