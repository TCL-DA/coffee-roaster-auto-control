# -*- coding: utf-8 -*-
"""Điều khiển Artisan 4.x bằng UI Automation (không chuột / phím thật) — agent OTL Hồng (14/10/2026).

Chủ máy: "khi nào bắt đầu làm bài thì bật biểu đồ Artisan lên, làm xong thì tắt Artisan và lưu lại biểu đồ để nộp bài".
Artisan phải cài sẵn: Modbus TCP 127.0.0.1:5020 (cầu tools/cau_artisan.py) + autosave (autosaveflag=1, autosavepath).
    bat_ghi()  -> mở Artisan nếu chưa chạy, bấm ON rồi START
    tat_luu()  -> bấm OFF (autosave ghi .alog), trả đường dẫn file mới trong thư mục autosave
"""
import glob
import os
import subprocess
import sys
import time

EXE = r"C:\Program Files\Artisan\artisan.exe"
THU_MUC_LUU = r"F:\Artisan\Profile\OTL-Hong"


def _cua_so(cho=20):
    import uiautomation as A
    w = A.WindowControl(searchDepth=2, SubName="Artisan")
    t = time.time()
    while not w.Exists(1) and time.time() - t < cho:
        time.sleep(1)
    return w if w.Exists(0.5) else None


def _tra_man_hinh(w, fg_cu):
    """⛔ Luật chủ máy 15/10: không chiếm màn hình anh. Artisan tự nhảy lên khi ON/OFF ⇒ đẩy Artisan xuống ĐÁY z-order (không
    kích hoạt; PrintWindow vẫn chụp được khi bị che) và trả lại cửa sổ anh đang dùng."""
    import ctypes
    u32 = ctypes.windll.user32
    u32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p] + [ctypes.c_int] * 4 + [ctypes.c_uint]
    u32.SetForegroundWindow.argtypes = [ctypes.c_void_p]
    hw = w.NativeWindowHandle
    if fg_cu and fg_cu != hw:
        u32.SetWindowPos(hw, ctypes.c_void_p(1), 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)  # HWND_BOTTOM, NOSIZE|NOMOVE|NOACTIVATE
        u32.SetForegroundWindow(fg_cu)


NUT_CHINH = ("ON", "OFF", "START")


def co_thanh_nut(w):
    """Thanh nút chính (ON/OFF/START + đồng hồ) đang hiện? Chỉ đọc UIA."""
    return any(w.ButtonControl(Name=n, searchDepth=12).Exists(0.3) for n in NUT_CHINH)


def _phim_c(w):
    """Gửi phím 'c' RIÊNG vào cửa sổ Artisan bằng PostMessage (không SendInput, không đổi cửa sổ trước, không đụng bàn phím anh).
    Phím 'c' của Artisan = Hiện / ẩn thanh nút chính (Controls) — đo thật 15/10 16:55: ẩn rồi hiện lại đúng."""
    import ctypes
    u32 = ctypes.windll.user32
    hw = w.NativeWindowHandle
    u32.PostMessageW(hw, 0x100, 0x43, 0x002E0001)      # WM_KEYDOWN 'C'
    u32.PostMessageW(hw, 0x102, ord("c"), 0x002E0001)  # WM_CHAR 'c'
    u32.PostMessageW(hw, 0x101, 0x43, 0xC02E0001)      # WM_KEYUP
    time.sleep(1.2)


def hien_thanh_nut(w=None):
    """Bảo đảm thanh nút chính hiện. 15/10 15:20: thanh nút bị ẩn (gốc nghi: Artisan tự nhảy lên khi ON/OFF, phím 'c' anh đang gõ
    lọt vào Artisan) ⇒ Hồng kẹt, mất giản đồ. Ẩn ⇒ gửi 'c' một lần; vẫn không thấy ⇒ gửi lại 'c' (trả trạng thái cũ) và báo lỗi."""
    w = w or _cua_so(3)
    if w is None:
        raise RuntimeError("Artisan không chạy")
    if co_thanh_nut(w):
        return True
    _phim_c(w)
    if co_thanh_nut(w):
        return True
    _phim_c(w)
    raise RuntimeError("Artisan: không hiện được thanh nút chính (phím 'c' không tác dụng)")


def duong_quay_lai(w=None):
    """⛔ Luật 15/10: TRƯỚC mỗi OFF phải chắc bấm lại được ON → START. Trả (True, lý do) nếu đủ đường quay lại."""
    w = w or _cua_so(3)
    try:
        hien_thanh_nut(w)
    except RuntimeError as e:
        return False, str(e)
    if not w.ButtonControl(Name="OFF", searchDepth=12).Exists(0.5) and not w.ButtonControl(Name="ON", searchDepth=12).Exists(0.5):
        return False, "không thấy nút ON/OFF"
    return True, "thanh nút hiện, ON/OFF/START bấm được bằng UIA"


def _bam(w, ten):
    import ctypes
    ctypes.windll.user32.GetForegroundWindow.restype = ctypes.c_void_p
    fg_cu = ctypes.windll.user32.GetForegroundWindow()
    b = w.ButtonControl(Name=ten, searchDepth=12)
    if not b.Exists(5):
        raise RuntimeError("Artisan: không thấy nút %s" % ten)
    b.GetInvokePattern().Invoke()
    for _ in range(15):                                 # trả màn NGAY và nhiều lần (0,1 s): phím anh gõ không lọt vào Artisan
        _tra_man_hinh(w, fg_cu)
        time.sleep(0.1)


def bat_ghi():
    w = _cua_so(2)
    if w is None:
        subprocess.Popen([EXE])
        w = _cua_so(40)
        if w is None:
            raise RuntimeError("Artisan không mở được")
        time.sleep(5)
    # 14/10: bài nộp phải là biểu đồ MỚI — đang ghi / đang ON thì OFF trước (autosave cất bản cũ), rồi mới ON (Artisan reset)
    ok, ly = duong_quay_lai(w)
    if not ok:
        raise RuntimeError("Artisan: KHÔNG có đường quay lại (%s) — không OFF, báo anh trước khi vào mẻ" % ly)
    st = w.ButtonControl(Name="START", searchDepth=12)
    if w.ButtonControl(Name="OFF", searchDepth=12).Exists(1):
        if st.Exists(0.5) and st.IsEnabled:
            # 15/10 14:30: đang ON mà CHƯA ghi ⇒ START thẳng (START xoá giản đồ cũ) — OFF lúc này hay kẹt, không thấy nút ON
            _bam(w, "START")
            return True
        _bam(w, "OFF")
        t = time.time()
        while not w.ButtonControl(Name="ON", searchDepth=12).Exists(0.5) and time.time() - t < 20:
            time.sleep(0.5)
    _bam(w, "ON")
    time.sleep(3)
    _bam(w, "START")
    return True


def tat_luu(cho=20):
    # 14/10: Artisan có thể GHI ĐÈ cùng tên (tiền tố ~batchcounter ~droptime = 0) -> so cả thời điểm sửa, không chỉ file mới
    truoc = {p: os.path.getmtime(p) for p in glob.glob(os.path.join(THU_MUC_LUU, "*.alog"))}
    w = _cua_so(5)
    if w is None:
        raise RuntimeError("Artisan không chạy")
    ok, ly = duong_quay_lai(w)
    if not ok:
        raise RuntimeError("Artisan: KHÔNG có đường quay lại (%s) — không OFF" % ly)
    _bam(w, "OFF")
    t = time.time()
    while time.time() - t < cho:
        moi = [p for p in glob.glob(os.path.join(THU_MUC_LUU, "*.alog")) if truoc.get(p) != os.path.getmtime(p)]
        if moi:
            return max(moi, key=os.path.getmtime)
        time.sleep(1)
    return None


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    lenh = sys.argv[1:] or ["tat"]
    if lenh == ["kiem"]:
        w = _cua_so(3)
        print("thanh nút:", co_thanh_nut(w), "· đường quay lại:", duong_quay_lai(w))
    elif lenh == ["bat"]:
        print(bat_ghi())
    else:
        print(tat_luu())
