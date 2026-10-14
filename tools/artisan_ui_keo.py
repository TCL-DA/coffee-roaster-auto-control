# -*- coding: utf-8 -*-
"""Kéo thanh trượt Artisan (Burner / Air / Drum) tới GIÁ TRỊ CHÍNH XÁC — agent đi QUA Artisan (luật: Artisan kết nối trước).

Đo 14/10/2026: đặt giá trị bằng UI Automation (RangeValue.SetValue) chỉ đổi số trên màn, Artisan KHÔNG gửi lệnh xuống board
(Artisan gửi khi THẢ chuột khỏi thanh trượt). Nút 'Burner ±5' thì gửi được nhưng thô (5 % ≈ 4 °C BT).
Cách này: PostMessage nhấn – kéo – thả vào ĐÚNG hwnd Qt của cửa sổ Artisan (không chuột thật, không rơi sang app khác).
    python artisan_ui_keo.py Burner 12
"""
import ctypes
import ctypes.wintypes as wt
import sys
import time

import uiautomation as A

u32 = ctypes.windll.user32
WM_MOUSEMOVE, WM_LBUTTONDOWN, WM_LBUTTONUP, MK_LBUTTON = 0x0200, 0x0201, 0x0202, 0x0001


def _cua_so():
    w = A.WindowControl(searchDepth=2, SubName="Artisan")
    if not w.Exists(3):
        raise RuntimeError("Artisan chưa mở")
    return w


def _thanh(w, ten):
    s = [c for c, _ in A.WalkControl(w, maxDepth=12) if c.ControlTypeName == "SliderControl" and c.Name == ten]
    if not s:
        raise RuntimeError("không thấy thanh trượt %s" % ten)
    return s[0]


def _lp(hwnd, x, y):
    pt = wt.POINT(int(x), int(y))
    u32.ScreenToClient(hwnd, ctypes.byref(pt))
    return (pt.y << 16) | (pt.x & 0xFFFF)


def keo(ten, gia_tri, w=None):
    """Kéo thanh trượt dọc `ten` tới gia_tri (0..100). Trả giá trị thanh trượt sau khi thả."""
    w = w or _cua_so()
    s = _thanh(w, ten)
    rv = s.GetRangeValuePattern()
    r = s.BoundingRectangle
    lo, hi = rv.Minimum, rv.Maximum
    hwnd = w.NativeWindowHandle
    # thanh dọc: giá trị lớn ở TRÊN. Bỏ biên tay nắm ~8 px mỗi đầu.
    bien = 8
    def y_cua(v):
        return r.bottom - bien - (v - lo) / (hi - lo) * (r.height() - 2 * bien)
    x = (r.left + r.right) // 2
    y0, y1 = y_cua(rv.Value), y_cua(float(gia_tri))
    u32.PostMessageW(hwnd, WM_MOUSEMOVE, 0, _lp(hwnd, x, y0))
    time.sleep(0.05)
    u32.PostMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, _lp(hwnd, x, y0))
    time.sleep(0.08)
    buoc = 6
    for i in range(1, buoc + 1):
        u32.PostMessageW(hwnd, WM_MOUSEMOVE, MK_LBUTTON, _lp(hwnd, x, y0 + (y1 - y0) * i / buoc))
        time.sleep(0.03)
    u32.PostMessageW(hwnd, WM_LBUTTONUP, 0, _lp(hwnd, x, y1))
    time.sleep(0.3)
    # tinh chỉnh: lệch do làm tròn pixel -> đặt đúng bằng UIA rồi kéo 0 px (nhấn-thả tại chỗ) để Artisan gửi lại
    if round(rv.Value) != round(float(gia_tri)):
        rv.SetValue(float(gia_tri))
        y = y_cua(float(gia_tri))
        u32.PostMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, _lp(hwnd, x, y))
        time.sleep(0.08)
        u32.PostMessageW(hwnd, WM_LBUTTONUP, 0, _lp(hwnd, x, y))
        time.sleep(0.3)
    return rv.Value


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(keo(sys.argv[1], float(sys.argv[2])))
