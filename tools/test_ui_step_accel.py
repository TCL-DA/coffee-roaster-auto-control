# -*- coding: utf-8 -*-
"""Kiểm nút ± : bậc nhỏ khi chạm, lớn dần khi giữ, máy chỉ nhận 1 lệnh/giây.

Chủ máy chốt 08/09/2026: chạm ±1; giữ thì bậc lớn dần 1 → 5 → 10; đang giữ thì số
trên màn chạy liền tay nhưng chỉ đẩy xuống máy mỗi giây một lần, cộng một lần chốt
khi nhả tay.
"""
from pathlib import Path
import sys
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')
APP = Path(__file__).resolve().parent.parent / 'OTL Roast Lab.html'

SPY = """() => {
  window.__cmds = [];
  window.machCmd = async (name, value) => { window.__cmds.push([name, value]); return true; };
  window.dsTick = () => {};
  window.pywebview = window.pywebview || { api: {} };
  window.dsBridge = () => true;
  // ⛔ ĐỎ OAN NGẪU NHIÊN (tìm ra 19/09/2026). `dsStart()` chạy `setInterval(dsTick,1000)`
  // nên nhịp đó giữ THAM CHIẾU GỐC: gán `window.dsTick` ở trên chỉ đổi tên toàn cục,
  // nhịp cũ vẫn gọi `pywebview.api.link_snapshot()` — stub không có hàm này nên ném lỗi
  // → `DS.state='error'` → `_chuaNoiMay()` chặn `start()` IM LẶNG. Nhịp rơi trúng lúc
  // đang giữ thì bài kiểm đỏ, rơi lệch thì xanh. Bịt bằng cách cho nhịp gốc chạy vô hại.
  window.pywebview.api.link_snapshot = async () => ({ state: 'connected', data: null });
  window.dsApply = () => {};
  window.dsLive = () => false;      // lấy giá trị từ R[k], khỏi phụ thuộc số trên màn
  window.toast = () => {};
  window.opLog = () => {};
  R.mode = 'MANUAL'; R.burner = 40;
  document.getElementById('ovBurner').textContent = '40';
}"""


def hold(page, sel, ms):
    box = page.locator(sel).bounding_box()
    page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
    page.mouse.down()
    page.wait_for_timeout(ms)
    page.mouse.up()
    page.wait_for_timeout(150)


def main():
    fails = []
    plus = '.outrow .pm[data-out="burner"][data-d="1"]'
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1366, 'height': 768})
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(APP.as_uri())
        page.evaluate("document.getElementById('login').classList.remove('on');gotoTab('rang')")
        page.evaluate("R.phase='RUNNING'")
        page.wait_for_timeout(250)

        # 1) Chạm một cái = ±1, gửi ngay
        page.evaluate(SPY)
        hold(page, plus, 60)
        cmds = page.evaluate('window.__cmds')
        val = page.evaluate("R.burner")
        if val != 41:
            fails.append(f'chạm một cái phải +1 (40→41), thực tế {val}')
        if cmds != [['gas', 41]]:
            fails.append(f'chạm một cái phải gửi đúng 1 lệnh gas=41, thực tế {cmds}')
        else:
            print('ĐẠT: chạm một cái = +1 và gửi ngay')

        # 2) Giữ ~1 giây: bậc còn nhỏ (1), và máy nhận RẤT ÍT lệnh so với số nấc
        page.evaluate(SPY)
        hold(page, plus, 1000)
        cmds = page.evaluate('window.__cmds')
        val = page.evaluate("R.burner")
        nac = val - 40
        if not (3 <= nac <= 8):
            fails.append(f'giữ 1s ở bậc nhỏ phải nhích khoảng 3–8, thực tế {nac}')
        if len(cmds) > 3:
            fails.append(f'giữ 1s mà gửi {len(cmds)} lệnh — phải gom lại, không bắn từng nấc')
        if cmds and cmds[-1][1] != val:
            fails.append(f'lệnh cuối ({cmds[-1]}) không khớp số trên màn ({val})')
        if not fails:
            print(f'ĐẠT: giữ 1s nhích {nac} nấc nhưng chỉ {len(cmds)} lệnh xuống máy, '
                  f'lệnh cuối khớp số hiển thị')

        # 3) Giữ lâu: bậc phải LỚN DẦN — giữ 2,6s phải đi xa hơn 2,6 lần giữ 1s
        page.evaluate(SPY)
        hold(page, plus, 2600)
        xa = page.evaluate("R.burner") - 40
        cmds3 = page.evaluate('window.__cmds')
        if xa <= nac * 2.6:
            fails.append(f'giữ lâu mà bậc không lớn dần: 1s đi {nac}, 2,6s mới đi {xa}')
        else:
            print(f'ĐẠT: bậc lớn dần — giữ 1s đi {nac}, giữ 2,6s đi {xa}')

        # 4) Nhịp đẩy xuống máy ~1 lệnh/giây, không phải mỗi nấc một lệnh
        if len(cmds3) > 5:
            fails.append(f'giữ 2,6s mà gửi {len(cmds3)} lệnh — vượt nhịp 1 lệnh/giây')
        elif cmds3[-1][1] != page.evaluate("R.burner"):
            fails.append('nhả tay mà không chốt giá trị cuối xuống máy')
        else:
            print(f'ĐẠT: giữ 2,6s chỉ {len(cmds3)} lệnh, nhả tay chốt đúng giá trị cuối')

        # 5) Kéo ngón ra khỏi nút giữa chừng vẫn phải chốt, không bỏ lửng
        page.evaluate(SPY)
        box = page.locator(plus).bounding_box()
        page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
        page.mouse.down()
        page.wait_for_timeout(1400)
        page.mouse.move(box['x'] + box['width'] / 2, box['y'] - 60)   # rời khỏi nút
        page.wait_for_timeout(200)
        page.mouse.up()
        page.wait_for_timeout(150)
        cmds5 = page.evaluate('window.__cmds')
        if not cmds5 or cmds5[-1][1] != page.evaluate("R.burner"):
            fails.append(f'kéo ngón ra mà không chốt giá trị cuối ({cmds5})')
        else:
            print('ĐẠT: kéo ngón ra khỏi nút vẫn chốt đúng giá trị cuối')

        # 6) Không vượt trần 100 dù giữ rất lâu
        page.evaluate(SPY)
        page.evaluate("R.burner=95;document.getElementById('ovBurner').textContent='95'")
        hold(page, plus, 2500)
        if page.evaluate("R.burner") != 100:
            fails.append(f'phải kẹp ở 100, thực tế {page.evaluate("R.burner")}')
        elif any(c[1] > 100 for c in page.evaluate('window.__cmds')):
            fails.append('gửi xuống máy giá trị vượt 100')
        else:
            print('ĐẠT: kẹp trần 100, không gửi giá trị vượt dải')

        # 7) Gợi ý "giữ để chạy nhanh" phải có, và không được tràn ô
        page.evaluate("NAP_CUR={name:'x',burner:45,air:55};uxOutHints()")
        page.wait_for_timeout(150)
        r = page.evaluate("""()=>{const e=document.getElementById('hintBurner'),hd=e.closest('.ohead');
              return {txt:e.textContent, cut:e.scrollWidth>e.clientWidth+1,
                      headOver:hd.scrollWidth>hd.clientWidth+1};}""")
        if 'giữ để chạy nhanh' not in r['txt']:
            fails.append(f'thiếu gợi ý "giữ để chạy nhanh" (đang là {r["txt"]!r})')
        elif r['cut'] or r['headOver']:
            fails.append(f'gợi ý bị cắt / tràn hàng tiêu đề: {r["txt"]!r}')
        else:
            print('ĐẠT: có gợi ý "giữ để chạy nhanh" theo thiết kế, không tràn ô')

        # 8) Đang giữ ở bậc lớn thì báo ×5, nhả tay thì trả về như cũ
        page.evaluate(SPY)
        page.evaluate("NAP_CUR={name:'x',burner:45,air:55};uxOutHints()")
        box = page.locator(plus).bounding_box()
        page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
        page.mouse.down()
        page.wait_for_timeout(1700)
        giua = page.evaluate("""()=>{const e=document.getElementById('hintBurner');
              return {txt:e.textContent, accel:e.classList.contains('accel')};}""")
        page.mouse.up()
        page.wait_for_timeout(250)
        sau = page.evaluate("document.getElementById('hintBurner').textContent")
        if giua['txt'] != '×5' or not giua['accel']:
            fails.append(f'giữ qua 1,2s phải báo ×5, thực tế {giua}')
        elif 'giữ để chạy nhanh' not in sau:
            fails.append(f'nhả tay mà ô gợi ý không trở lại như cũ ({sau!r})')
        else:
            print('ĐẠT: báo ×5 khi sang bậc, nhả tay trả ô gợi ý về như cũ')

        # 9) Vạch mốc: máy chưa theo kịp thì hiện, khớp rồi thì ẩn
        page.evaluate("""()=>{MACH_OUT.burner=30;
              document.getElementById('ovBurner').textContent='70';uxOutHints();}""")
        lag = page.evaluate("""()=>{const b=document.getElementById('obarBurner');
              return {lag:b.classList.contains('lag'), left:b.querySelector('.ack').style.left};}""")
        page.evaluate("""()=>{MACH_OUT.burner=70;uxOutHints();}""")
        het = page.evaluate("document.getElementById('obarBurner').classList.contains('lag')")
        if not lag['lag'] or lag['left'] != '30%':
            fails.append(f'máy lệch số trên màn mà vạch mốc không hiện đúng ({lag})')
        elif het:
            fails.append('máy đã theo kịp mà vạch mốc vẫn còn')
        else:
            print('ĐẠT: vạch mốc hiện khi máy chưa theo kịp, tự ẩn khi đã khớp')

        if errors:
            fails.append(f'Lỗi JS: {errors[:3]}')
        browser.close()

    if fails:
        print('\nKHÔNG ĐẠT:')
        for f in fails:
            print(' -', f)
        sys.exit(1)
    print('\nTẤT CẢ ĐẠT — nút ± đúng ý chủ máy.')


if __name__ == '__main__':
    main()
