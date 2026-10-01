# -*- coding: utf-8 -*-
"""Cắt một video thành các tấm ghép khung hình để AI đọc bằng Read.

    python xem_video.py "<file.mp4>" --giay 10

⛔ Tấm ghép LUÔN ≤ 2000 px mỗi chiều (mặc định chặn ở 1500 cho chắc). Lỡ đọc một ảnh
quá khổ là cả phiên sau đó không gửi thêm được ảnh nào, phải mở phiên mới.
"""
import argparse
import json
import os
import subprocess
import sys

TOI_DA = 1500          # px, mỗi chiều của tấm ghép


def chay(*lenh):
    r = subprocess.run(lenh, capture_output=True, text=True)
    if r.returncode:
        sys.exit('LỖI: ' + ' '.join(lenh[:2]) + '\n' + r.stderr[-500:])
    return r.stdout


def main():
    p = argparse.ArgumentParser()
    p.add_argument('video')
    p.add_argument('--giay', type=int, default=10, help='giây giữa hai khung (mặc định 10)')
    p.add_argument('--ra', default='', help='thư mục kết quả')
    a = p.parse_args()

    if not os.path.exists(a.video):
        sys.exit('không thấy file: ' + a.video)
    ra = a.ra or os.path.join(os.path.dirname(os.path.abspath(a.video)), 'xem_video_out')
    kh = os.path.join(ra, 'khung')
    os.makedirs(kh, exist_ok=True)

    # 1. video dài bao nhiêu, cỡ bao nhiêu, CÓ TIẾNG KHÔNG
    tt = json.loads(chay('ffprobe', '-v', 'error', '-show_format', '-show_streams',
                         '-of', 'json', a.video))
    vid = next(s for s in tt['streams'] if s['codec_type'] == 'video')
    co_tieng = any(s['codec_type'] == 'audio' for s in tt['streams'])
    dai = float(tt['format']['duration'])
    W0, H0 = int(vid['width']), int(vid['height'])
    print('dài %d:%02d | %dx%d | %s' % (dai // 60, dai % 60, W0, H0,
          'CÓ tiếng' if co_tieng else '⛔ KHÔNG có tiếng — không bóc lời được'))

    # 2. cắt khung hình
    for f in os.listdir(kh):
        os.remove(os.path.join(kh, f))
    chay('ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', a.video,
         '-vf', 'fps=1/%d' % a.giay, '-q:v', '3', os.path.join(kh, 'k%04d.jpg'))
    khung = sorted(os.listdir(kh))
    print('cắt được %d khung, mỗi %d giây' % (len(khung), a.giay))

    # 3. ghép lưới, luôn ≤ TOI_DA mỗi chiều
    from PIL import Image, ImageDraw
    TW = 240
    TH = int(round(TW * H0 / W0))
    cols = max(1, TOI_DA // TW)
    rows = max(1, TOI_DA // (TH + 14))
    per = cols * rows
    print('lưới %dx%d = %d khung/tấm, tấm cỡ %dx%d' % (
        cols, rows, per, cols * TW, rows * (TH + 14)))
    assert cols * TW <= 2000 and rows * (TH + 14) <= 2000, 'tấm ghép quá khổ'

    tam = []
    for gi in range(0, len(khung), per):
        g = khung[gi:gi + per]
        m = Image.new('RGB', (cols * TW, rows * (TH + 14)), 'black')
        d = ImageDraw.Draw(m)
        for i, f in enumerate(g):
            n = int(f[1:5])
            t = (n - 1) * a.giay
            im = Image.open(os.path.join(kh, f)).resize((TW, TH), Image.LANCZOS)
            x, y = (i % cols) * TW, (i // cols) * (TH + 14)
            m.paste(im, (x, y + 14))
            d.text((x + 3, 1), '%02d:%02d' % (t // 60, t % 60), fill='yellow')
        ten = os.path.join(ra, 't%02d.png' % (gi // per))
        m.save(ten)
        t0, t1 = gi * a.giay, (gi + len(g) - 1) * a.giay
        tam.append(ten)
        print('  %s  %02d:%02d - %02d:%02d' % (ten, t0 // 60, t0 % 60, t1 // 60, t1 % 60))

    print('\nXong %d tấm. Đọc từng tấm bằng Read.' % len(tam))
    if not co_tieng:
        print('Nhắc lại: video KHÔNG có tiếng, mô tả phải ghi rõ "NO SOUND".')


if __name__ == '__main__':
    main()
