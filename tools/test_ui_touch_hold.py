# -*- coding: utf-8 -*-
"""Kiểm cử chỉ ĐÈ GIỮ bằng NGÓN TAY THẬT, không phải chuột giả lập.

Máy rang là màn cảm ứng, thợ đeo găng. Chuột giả lập không có những thứ ngón tay
có: pointerType='touch', pointercancel khi trình duyệt giành cử chỉ cuộn, và ngón
thứ hai chạm vào giữa chừng. Bài này bắn sự kiện chạm thật qua CDP.
"""
from pathlib import Path
import sys
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')
APP = Path(__file__).resolve().parent.parent / 'OTL Roast Lab.html'

SPY = """() => {
  window.__cmds = [];
  window.__ptypes = [];
  window.machCmd = async (n, v) => { window.__cmds.push([n, v]); return true; };
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
  // Giả lập cầu nối thì phải giả lập ĐỦ. Từ 11/09/2026 lệnh máy bị chặn NGAY lúc
  // đặt ngón xuống nếu CÓ cầu mà CHƯA nối được máy — để thợ khỏi giữ đủ 0,5 giây
  // rồi mới bị từ chối. Bật dsBridge mà bỏ quên DS.state là dựng đúng trạng thái
  // bị chặn đó, rồi bài kiểm tưởng cử chỉ giữ hỏng.
  try { if (typeof DS !== 'undefined' && DS) DS.state = 'connected'; } catch (e) {}
  window.dsLive = () => false;
  window.toast = () => {};
  window.opLog = () => {};
  R.mode = 'MANUAL'; R.phase = 'RUNNING'; R.burner = 40;
  document.getElementById('ovBurner').textContent = '40';
  // ghi lại LOẠI con trỏ để chắc chắn đây đúng là chạm, không phải chuột
  document.addEventListener('pointerdown', e => window.__ptypes.push(e.pointerType), true);
}"""


class Finger:
    """Một ngón tay thật trên màn, bắn qua CDP Input.dispatchTouchEvent."""

    def __init__(self, page):
        self.cdp = page.context.new_cdp_session(page)
        self.page = page

    def _send(self, kind, points):
        self.cdp.send('Input.dispatchTouchEvent', {'type': kind, 'touchPoints': points})

    def down(self, x, y, ident=0):
        self._send('touchStart', [{'x': x, 'y': y, 'id': ident}])

    def move(self, x, y, ident=0):
        self._send('touchMove', [{'x': x, 'y': y, 'id': ident}])

    def up(self):
        self._send('touchEnd', [])

    def cancel(self):
        """Trình duyệt giành cử chỉ (bắt đầu cuộn) — ngón vẫn trên màn nhưng app mất quyền."""
        self._send('touchCancel', [])

    def hold(self, sel, ms):
        b = self.page.locator(sel).bounding_box()
        x, y = b['x'] + b['width'] / 2, b['y'] + b['height'] / 2
        self.down(x, y)
        self.page.wait_for_timeout(ms)
        self.up()
        self.page.wait_for_timeout(150)
        return x, y


def main():
    fails = []
    plus = '.outrow .pm[data-out="burner"][data-d="1"]'
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={'width': 1366, 'height': 768}, has_touch=True)
        page = ctx.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(APP.as_uri())
        page.evaluate("document.getElementById('login').classList.remove('on');gotoTab('rang')")
        page.wait_for_timeout(300)
        f = Finger(page)

        # 0) Xác nhận đây thật sự là CHẠM chứ không phải chuột
        page.evaluate(SPY)
        f.hold(plus, 80)
        ptypes = page.evaluate('window.__ptypes')
        if 'touch' not in ptypes:
            fails.append(f'không phải sự kiện chạm thật: {ptypes}')
        else:
            print(f'ĐẠT: đang bắn sự kiện chạm thật (pointerType={ptypes[0]})')

        # 1) Chạm nhanh bằng ngón = +1
        page.evaluate(SPY)
        f.hold(plus, 80)
        if page.evaluate('R.burner') != 41 or page.evaluate('window.__cmds') != [['gas', 41]]:
            fails.append(f'chạm ngón phải +1 và gửi 1 lệnh, thực tế {page.evaluate("R.burner")} '
                         f'{page.evaluate("window.__cmds")}')
        else:
            print('ĐẠT: chạm bằng ngón = +1, gửi đúng một lệnh')

        # 2) Giữ bằng ngón: bậc lớn dần, máy vẫn chỉ nhận ~1 lệnh/giây
        page.evaluate(SPY)
        f.hold(plus, 2600)
        di = page.evaluate('R.burner') - 40
        cmds = page.evaluate('window.__cmds')
        if di < 20:
            fails.append(f'giữ ngón 2,6s mà chỉ đi {di} nấc — bậc không lớn dần')
        elif len(cmds) > 5:
            fails.append(f'giữ ngón 2,6s mà gửi {len(cmds)} lệnh — vượt nhịp 1 lệnh/giây')
        elif cmds[-1][1] != page.evaluate('R.burner'):
            fails.append('nhả ngón mà không chốt giá trị cuối')
        else:
            print(f'ĐẠT: giữ ngón 2,6s đi {di} nấc, chỉ {len(cmds)} lệnh, chốt đúng khi nhả')

        # 3) TRÌNH DUYỆT GIÀNH CỬ CHỈ giữa chừng (pointercancel) — phải dừng sạch,
        #    không được để nút chạy tiếp khi ngón đã không còn điều khiển nữa
        page.evaluate(SPY)
        b = page.locator(plus).bounding_box()
        f.down(b['x'] + b['width'] / 2, b['y'] + b['height'] / 2)
        page.wait_for_timeout(1500)
        giua = page.evaluate('R.burner')
        f.cancel()
        page.wait_for_timeout(700)
        sau = page.evaluate('R.burner')
        if sau != giua:
            fails.append(f'bị pointercancel mà nút vẫn chạy tiếp: {giua} → {sau}')
        elif page.evaluate('window.__cmds')[-1][1] != sau:
            fails.append('bị pointercancel mà không chốt giá trị cuối xuống máy')
        else:
            print('ĐẠT: trình duyệt giành cử chỉ thì dừng sạch và vẫn chốt giá trị cuối')

        # 4) NGÓN THỨ HAI chạm vào giữa lúc đang giữ — không được nhân đôi tốc độ
        page.evaluate(SPY)
        b = page.locator(plus).bounding_box()
        x, y = b['x'] + b['width'] / 2, b['y'] + b['height'] / 2
        f._send('touchStart', [{'x': x, 'y': y, 'id': 0}])
        page.wait_for_timeout(700)
        mot = page.evaluate('R.burner')
        f._send('touchStart', [{'x': x, 'y': y, 'id': 0}, {'x': x - 4, 'y': y - 4, 'id': 1}])
        page.wait_for_timeout(700)
        hai = page.evaluate('R.burner')
        f.up()
        page.wait_for_timeout(200)
        # tốc độ nửa sau không được vọt hơn ~2,2 lần nửa đầu (bậc có lớn dần thật,
        # nhưng ngón thứ hai KHÔNG được cộng thêm một chuỗi lặp nữa)
        if (hai - mot) > (mot - 40) * 2.2 + 6:
            fails.append(f'ngón thứ hai làm nhân tốc độ: nửa đầu +{mot-40}, nửa sau +{hai-mot}')
        else:
            print(f'ĐẠT: ngón thứ hai không nhân tốc độ (nửa đầu +{mot-40}, nửa sau +{hai-mot})')

        # 5) Nút HỆ TRỌNG bằng ngón: chạm nhanh không xả, giữ đủ mới xả
        page.evaluate(SPY)
        f.hold('#btnEscape', 400)
        if page.evaluate('window.__cmds'):
            fails.append(f'chạm ngón nhanh mà vẫn xả liệu: {page.evaluate("window.__cmds")}')
        else:
            page.evaluate(SPY)
            f.hold('#btnEscape', 800)
            if page.evaluate('window.__cmds') != [['escape', 1]]:
                fails.append(f'giữ ngón đủ mốc mà không xả: {page.evaluate("window.__cmds")}')
            else:
                print('ĐẠT: nút Xả liệu — chạm ngón không đi, giữ đủ mốc mới đi')

        # 6) Nút hệ trọng bị pointercancel giữa chừng → tuyệt đối không được phát lệnh
        page.evaluate(SPY)
        b = page.locator('#btnEscape').bounding_box()
        f.down(b['x'] + b['width'] / 2, b['y'] + b['height'] / 2)
        page.wait_for_timeout(260)          # PHẢI dưới HOLD_MS (0,5 s) — quá mốc
        f.cancel()                          # là lệnh đã đi rồi, kiểm nhầm chuyện khác
        page.wait_for_timeout(900)
        if page.evaluate('window.__cmds'):
            fails.append(f'nút hệ trọng bị cancel mà vẫn phát lệnh: {page.evaluate("window.__cmds")}')
        else:
            print('ĐẠT: nút hệ trọng bị giành cử chỉ giữa chừng thì huỷ hẳn, không phát lệnh')

        # 7) CHỐNG CHẠY LOẠN (lỗi thật bắt được 08/09/2026): sau khi buông tay hết,
        #    số PHẢI đứng yên. Trước bản vá, hai ngón chạm rồi nhả để lại một bộ đếm
        #    mồ côi chạy mãi — không còn ai chạm màn mà gas vẫn tự leo lên 100.
        page.evaluate(SPY)
        b = page.locator(plus).bounding_box()
        x, y = b['x'] + b['width'] / 2, b['y'] + b['height'] / 2
        for _ in range(3):                       # quấy nhiều ngón, nhả kiểu xấu nhất
            f._send('touchStart', [{'x': x, 'y': y, 'id': 0}])
            page.wait_for_timeout(250)
            f._send('touchStart', [{'x': x, 'y': y, 'id': 0}, {'x': x - 5, 'y': y - 5, 'id': 1}])
            page.wait_for_timeout(250)
            f.up()
            page.wait_for_timeout(100)
        yen1 = page.evaluate('R.burner')
        page.wait_for_timeout(1500)              # buông tay hoàn toàn 1,5 giây
        yen2 = page.evaluate('R.burner')
        n_after = len(page.evaluate('window.__cmds'))
        page.wait_for_timeout(1200)
        if yen2 != yen1:
            fails.append(f'CHẠY LOẠN: buông tay rồi mà số vẫn tự đổi {yen1} → {yen2}')
        elif len(page.evaluate('window.__cmds')) != n_after:
            fails.append('CHẠY LOẠN: buông tay rồi mà vẫn còn lệnh tự gửi xuống máy')
        else:
            print(f'ĐẠT: buông tay là đứng yên ở {yen2}, không còn bộ đếm mồ côi')

        if errors:
            fails.append(f'Lỗi JS: {errors[:3]}')
        browser.close()

    if fails:
        print('\nKHÔNG ĐẠT:')
        for x in fails:
            print(' -', x)
        sys.exit(1)
    print('\nTẤT CẢ ĐẠT — cử chỉ đúng khi chạm bằng ngón tay thật.')


if __name__ == '__main__':
    main()
