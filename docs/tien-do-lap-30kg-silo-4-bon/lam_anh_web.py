# -*- coding: utf-8 -*-
"""Nén ảnh hiện trường cho trang tiến độ (GitHub Pages, nhánh gh-pages).

Cách dùng:
    python lam_anh_web.py <thư mục ảnh gốc> <thư mục gốc nhánh gh-pages>

Thư mục ảnh gốc chứa các thư mục con theo ngày, tên kết thúc bằng DDMM
("ngay 0911", "1311"...). Ảnh gốc nằm ở kho ảnh, KHÔNG đưa vào repo.

Nhiều thư mục cùng một ngày ("1611" và "Sáng 1611") được gộp chung, ảnh
trùng nội dung (md5) chỉ lấy một lần. Trong một ngày ảnh xếp theo mốc giờ
gửi Zalo (13 chữ số đầu tên file = mili giây Unix).

Kết quả ghi vào <gh-pages>/anh/:
    anh/<DDMM>/NN.jpg    cạnh dài 1600 px, dùng khi mở to
    anh/<DDMM>/tNN.jpg   cạnh dài 480 px, dùng trong lưới
    anh/anh.js           window.ANH = {"DDMM": [[w, h], [w, h, 1], ...]}
                         phần tử thứ 3 = 1 nghĩa là khung hình trích từ video

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
    '3a8ca5a49b56cc81ac2a69fa9d836e66',  # ảnh camera an ninh của khách (09/11)
    '84e4798c437103424f4ef868f3211cd7',  # chữ tên quán trên trần
    '13736679949092f336b8421ceb01822a',  # chữ tên quán trên tường cong
    'e20a12f410ba1ba038e8c54d4154b21e',  # mặt đường qua kính
    # 3 ảnh trong lòng bồn chụp 19/11 (sau bàn giao), để trong thư mục 1811 nhưng không phải 18/11
    '14d1ecd3a3aea99d57e8a6162ca1a2d5',
    '02107eda75ceef9c136faa821b9309c3',
    '57be1c7e35b07fbabde2cf09c10cf76d',
}

# ảnh nằm trong thư mục ngày khác với ngày chụp: mã cuối tên file -> DDMM
CHUYEN_NGAY = {
    '093538c924282f53796a2848221aabad': '1711',  # gửi 22:21 17/11, để trong "Sáng 1611"
}

# cắt bớt ảnh (trái, trên, phải, dưới — tỉ lệ 0..1) để bỏ phần lộ thông tin
CAT = {
    '093538c924282f53796a2848221aabad': (0, 0, 1, 0.84),  # đáy ảnh thấy mặt đường
}

# khung hình trích từ video: (DDMM, 13 số đầu tên file video, [vị trí 0..1 trong video])
KHUNG_VIDEO = [
    ('1611', '1794822738550', [0.3]),              # ống khói ngoài trời
    ('1711', '1794928270903', [0.1, 0.4, 0.7]),    # máy rang, tủ điện, đầu dò nhiệt
    ('1711', '1794928354495', [0.1, 0.95]),        # trống rang, cyclone
    ('1711', '1794928399920', [0.1, 0.4]),         # máy 30 kg
    ('1711', '1794928677466', [0.1, 0.7]),         # máy nén khí, ống khí nén
    ('1711', '1794928677469', [0.1, 0.95]),        # dàn bồn silo
    ('1811', '1795021309642', [0.4, 0.95]),        # đường ống trên trần vào phòng silo
    ('1811', '1795021356725', [0.7]),              # màn hình rang
    ('1811', '1795021356726', [0.7]),              # xả mẻ rang
    ('1811', '1795021377667', [0.95]),             # khay làm nguội
    ('1811', '1795021377678', [0.95]),             # hạt vào bồn
]


def ma_ngay(ten):
    m = re.search(r'(\d{4})\s*$', ten)
    return m.group(1) if m else None


def moc_gio(ten):
    """13 chữ số đầu tên file Zalo = mili giây gửi; file khác xếp cuối theo tên."""
    m = re.match(r'(\d{13})_', ten)
    return (int(m.group(1)) if m else 10 ** 14, ten)


def luu(im, duong_dan, canh, chat):
    ban = im.copy()
    ban.thumbnail((canh, canh), Image.LANCZOS)
    ban.save(duong_dan, 'JPEG', quality=chat, optimize=True, progressive=True)
    return ban.size


def cat(im, ma):
    if ma not in CAT:
        return im
    t, tr, p, d = CAT[ma]
    w, h = im.size
    return im.crop((round(t * w), round(tr * h), round(p * w), round(d * h)))


def gom_nguon(nguon):
    """Trả về {DDMM: [(khoá xếp, đường dẫn, mã 32 ký tự | None, vị trí video | None)]}."""
    ngay_list, video = {}, {}
    for thu_muc in os.listdir(nguon):
        ngay, duong = ma_ngay(thu_muc), os.path.join(nguon, thu_muc)
        if not ngay or not os.path.isdir(duong):
            continue
        for ten in os.listdir(duong):
            tep = os.path.join(duong, ten)
            if ten.lower().endswith('.mp4'):
                video.setdefault(ten[:13], tep)
                continue
            if not ten.lower().endswith(DUOI_ANH):
                continue
            ma = os.path.splitext(ten)[0][-32:]
            if ma in BO_QUA:
                continue
            ngay_dung = CHUYEN_NGAY.get(ma, ngay)
            ngay_list.setdefault(ngay_dung, []).append((moc_gio(ten), tep, ma, None))
    for ngay, ma_video, vi_tri in KHUNG_VIDEO:
        tep = video.get(ma_video)
        if not tep:
            sys.exit('Không thấy video ' + ma_video)
        for k, r in enumerate(vi_tri):
            khoa = (int(ma_video), '~%02d' % k)
            ngay_list.setdefault(ngay, []).append((khoa, tep, None, r))
    return ngay_list


def doc_khung(tep, vi_tri):
    import cv2  # chỉ cần khi có KHUNG_VIDEO
    cap = cv2.VideoCapture(tep)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.set(cv2.CAP_PROP_POS_FRAMES, min(n - 1, int(n * vi_tri)))
    ok, khung = cap.read()
    cap.release()
    if not ok:
        sys.exit('Không đọc được khung hình %s @ %.2f' % (tep, vi_tri))
    return Image.fromarray(cv2.cvtColor(khung, cv2.COLOR_BGR2RGB))


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    nguon, dich = sys.argv[1], os.path.join(sys.argv[2], 'anh')
    if os.path.isdir(dich):
        shutil.rmtree(dich)
    os.makedirs(dich)
    ket_qua, da_thay = {}, set()
    gom = gom_nguon(nguon)
    for ngay in sorted(gom, key=lambda n: n[2:] + n[:2]):
        os.makedirs(os.path.join(dich, ngay), exist_ok=True)
        danh_sach = []
        for _, tep, ma, vi_tri in sorted(gom[ngay], key=lambda x: x[0]):
            if vi_tri is None:
                with open(tep, 'rb') as f:
                    bam = hashlib.md5(f.read()).hexdigest()
                if bam in da_thay:  # ảnh trùng
                    continue
                da_thay.add(bam)
                im = cat(ImageOps.exif_transpose(Image.open(tep)).convert('RGB'), ma)
            else:
                im = doc_khung(tep, vi_tri)
            so = '%02d' % (len(danh_sach) + 1)
            w, h = luu(im, os.path.join(dich, ngay, so + '.jpg'), FULL_PX, 78)
            luu(im, os.path.join(dich, ngay, 't' + so + '.jpg'), THUMB_PX, 70)
            danh_sach.append([w, h] if vi_tri is None else [w, h, 1])
        ket_qua[ngay] = danh_sach
        print(ngay, len(danh_sach), 'anh')
    with open(os.path.join(dich, 'anh.js'), 'w', encoding='utf-8') as f:
        f.write('window.ANH=' + json.dumps(ket_qua, separators=(',', ':')) + ';\n')
    tong = sum(os.path.getsize(os.path.join(r, t)) for r, _, ts in os.walk(dich) for t in ts)
    print('tong', sum(len(v) for v in ket_qua.values()), 'anh,', round(tong / 1e6, 1), 'MB')


if __name__ == '__main__':
    main()
