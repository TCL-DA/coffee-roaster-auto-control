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


def _bam(w, ten):
    b = w.ButtonControl(Name=ten, searchDepth=12)
    if not b.Exists(5):
        raise RuntimeError("Artisan: không thấy nút %s" % ten)
    b.GetInvokePattern().Invoke()


def bat_ghi():
    w = _cua_so(2)
    if w is None:
        subprocess.Popen([EXE])
        w = _cua_so(40)
        if w is None:
            raise RuntimeError("Artisan không mở được")
        time.sleep(5)
    # 14/10: bài nộp phải là biểu đồ MỚI — đang ghi / đang ON thì OFF trước (autosave cất bản cũ), rồi mới ON (Artisan reset)
    off = w.ButtonControl(Name="OFF", searchDepth=12)
    if off.Exists(1):
        off.GetInvokePattern().Invoke()
        time.sleep(4)
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
    print(bat_ghi() if sys.argv[1:] == ["bat"] else tat_luu())
