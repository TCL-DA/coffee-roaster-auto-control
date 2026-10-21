# -*- coding: utf-8 -*-
"""Kiểm đường CÀI LÊN IPHONE: web server LAN phải phục vụ manifest + icon, và trang
web phải có đủ thẻ Safari cần để "Thêm vào Màn hình chính" ra biểu tượng riêng, mở
toàn màn. Chạy CHÍNH EXE trong dist — giống test_exe_end_to_end — vì lỗi hay gặp là
QUÊN BỎcC ICON VÀO SPEC: chạy bằng python thì xanh, đóng exe xong là 404.

BẪY: `proc.terminate()` chỉ giết tiến trình cha, pywebview đẻ thêm con — phải
`taskkill /IM` theo tên, không thì cửa sổ nằm lại và khoá EXE cho lần build sau (WinError 5).
"""
from pathlib import Path
import json
import socket
import subprocess
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding='utf-8')
EXE = Path(__file__).resolve().parent / 'dist' / 'OTL Roast Lab HMI.exe'
PORT = 8555
THE_CAN = ('rel="manifest"', 'apple-touch-icon', 'apple-mobile-web-app-capable',
           'apple-mobile-web-app-status-bar-style', 'apple-mobile-web-app-title')


def lay(duong):
    with urllib.request.urlopen(f'http://127.0.0.1:{PORT}{duong}', timeout=8) as r:
        return r.status, r.headers.get('Content-Type', ''), r.read()


def main():
    loi = []
    if not EXE.exists():
        print('BỎP QUA: chưa có', EXE.name, '— build trước đã')
        return 0
    proc = subprocess.Popen([str(EXE)])
    try:
        for _ in range(90):
            try:
                socket.create_connection(('127.0.0.1', PORT), 1).close()
                break
            except OSError:
                time.sleep(1)
        else:
            print('KHÔNG ĐẠT: web server LAN không lên ở cổng', PORT)
            return 1
        time.sleep(1)

        st, ct, body = lay('/manifest.webmanifest')
        if st != 200 or 'manifest' not in ct:
            loi.append(f'manifest trả {st} / {ct}')
        else:
            m = json.loads(body)
            if m.get('display') != 'standalone':
                loi.append(f"manifest display = {m.get('display')} (phải standalone, không thì Safari mở kèm thanh địa chỉ)")
            if not m.get('icons'):
                loi.append('manifest không có icon')
        if not loi:
            print('ĐẠT: /manifest.webmanifest đúng kiểu, display=standalone')

        for ic in ('/pwa-180.png', '/pwa-192.png', '/pwa-512.png'):
            st, ct, body = lay(ic)
        if st != 200 or not body.startswith(bytes([0x89])+ b'PNG'):
                loi.append(f'{ic}: trả {st}, {len(body)} byte — nhớ thêm vào datas của RoastLabHMI.spec')
        if not any('pwa-' in e for e in loi):
            print('ĐẠT: ba icon PWA nằm trong gói exe và tải được')

        st, ct, body = lay('/')
        dau = body[:6000].decode('utf-8', 'ignore')
        thieu = [t for t in THE_CAN if t not in dau]
        if thieu:
            loi.append('trang web thiếu thẻ: ' + ', '.join(thieu))
        else:
            print('ĐẠT: trang web có đủ thẻ cho màn hình chính iPhone')
    finally:
        subprocess.run(['taskkill', '/IM', EXE.name, '/F'], capture_output=True)

    if loi:
        print()
        print('KHÔNG ĐẠT:')
        for e in loi:
            print(' -', e)
        return 1
    print()
    print('TẤT CẢ ĐẠT — cài lên iPhone bằng "Thêm vào Màn hình chính" chạy được.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
