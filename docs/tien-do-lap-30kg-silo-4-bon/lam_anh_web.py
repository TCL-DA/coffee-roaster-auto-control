# -*- coding: utf-8 -*-
"""Nén ảnh hiện trường cho trang tiến độ (GitHub Pages, nhánh gh-pages).

Cách dùng:
    python lam_anh_web.py <thư mục ảnh gốc> <thư mục gốc nhánh gh-pages>

Thư mục ảnh gốc chứa các thư mục con theo ngày, tên kết thúc bằng DDMM
("ngay 0911", "1311"...). Ảnh gốc nằm ở kho ảnh, KHÔNG đưa vào repo.

Kết quả ghi vào <gh-pages>/anh/:
    anh/<DDMM>/NN.jpg    cạnh dài 1600 px, dùng khi mở to
    anh/<DDMM>/tNN.jpg   cạnh dài 480 px, dùng trong lưới
    anh/anh.js           window.ANH = {"DDMM": [[w, h], ...]}

Ảnh được dựng lại từ điểm ảnh nên mọi EXIF (máy chụp, GPS) đều mất.
Repo PUBLIC: ảnh lộ biển hiệu, tên quán, đường phố, đồng phục nhân viên
của khách thì thêm mã cuối tên file vào BO_QUA rồi chạy lại.
"""
import hashlib
import json
import os
import re
import shutil
import sys

from PIL import Image, ImageOps

FULL_PX = 1600
THUMB_PX = 480
DUOI_ANH = ('.jpg', '.jpeg', '.png')

# 32 ký tự cuối tên file Zalo của các ảnh không đưa lên web
BO_QUA = {
    '56748f8eb817864ad93b01194952a26c',  # biển hiệu bên kia đường
    '6f6656cf61e4367f3886f06b01dc8b3d',  # mặt đường trước công trình
    'b4641aa5f303127b3291ffe9d7510757',  # chữ tên quán trên kính
    'af50f690b2f81d23eedd374adbb74b35',  # ly có tên quán
    'ed626ab62e32d6c07d46e8dc18cf45c5',  # tường trưng bày trong quán
    'b7ef39c343a56acea8e572aa6487e95f',  # đồng phục nhân viên khách
    '8212798016ef9cc238c083720a78e6da',
    'a913e2fdf4815ecaeb62218bd2ca71f3',
}


def ma_ngay(ten):
    m = re.search(r'(\d{4})\s*$', ten)
    return m.group(1) if m else None


def luu(im, duong_dan, canh, chat):
    ban = im.copy()
    ban.thumbnail((canh, canh), Image.LANCZOS)
    ban.save(duong_dan, 'JPEG', quality=chat, optimize=True, progressive=True)
    return ban.size


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    nguon, dich = sys.argv[1], os.path.join(sys.argv[2], 'anh')
    if os.path.isdir(dich):
        shutil.rmtree(dich)
    os.makedirs(dich)
    ket_qua, da_thay = {}, set()
    for thu_muc in sorted(os.listdir(nguon), key=lambda t: (lambda n: n[2:] + n[:2])(ma_ngay(t) or '')):
        ngay = ma_ngay(thu_muc)
        duong = os.path.join(nguon, thu_muc)
        if not ngay or not os.path.isdir(duong):
            continue
        os.makedirs(os.path.join(dich, ngay), exist_ok=True)
        danh_sach = []
        for ten in sorted(os.listdir(duong)):
            if not ten.lower().endswith(DUOI_ANH):
                continue
            if os.path.splitext(ten)[0][-32:] in BO_QUA:
                continue
            tep = os.path.join(duong, ten)
            with open(tep, 'rb') as f:
                bam = hashlib.md5(f.read()).hexdigest()
            if bam in da_thay:  # ảnh trùng
                continue
            da_thay.add(bam)
            im = ImageOps.exif_transpose(Image.open(tep)).convert('RGB')
            so = '%02d' % (len(danh_sach) + 1)
            w, h = luu(im, os.path.join(dich, ngay, so + '.jpg'), FULL_PX, 78)
            luu(im, os.path.join(dich, ngay, 't' + so + '.jpg'), THUMB_PX, 70)
            danh_sach.append([w, h])
        ket_qua[ngay] = danh_sach
        print(ngay, len(danh_sach), 'anh')
    with open(os.path.join(dich, 'anh.js'), 'w', encoding='utf-8') as f:
        f.write('window.ANH=' + json.dumps(ket_qua, separators=(',', ':')) + ';\n')
    tong = sum(os.path.getsize(os.path.join(r, t)) for r, _, ts in os.walk(dich) for t in ts)
    print('tong', sum(len(v) for v in ket_qua.values()), 'anh,', round(tong / 1e6, 1), 'MB')


if __name__ == '__main__':
    main()
