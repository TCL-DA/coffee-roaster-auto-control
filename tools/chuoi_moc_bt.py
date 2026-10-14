# -*- coding: utf-8 -*-
"""Đưa BT qua CHUỖI MỐC, KHÔNG VỌT LỐ — máy điện VX4 (agent OTL Hồng, bài toán chủ máy 14/10/2026: 170>190>210>230>200>180>150).

    OTL_PORT=COM13 python chuoi_moc_bt.py <thư mục> 170 190 210 230 200 180 150
Cần cờ 'Điều khiển từ PC'. Một tiến trình giữ cổng (không chạy cùng lai_may / Artisan).

Mô hình (đo 14/10, máy đã ngấm, gió 85 %): SV = 130 + 2,2·Nhiệt%; buồng ≈ SV sau 10–15 s; BT cân bằng ≈ 114 + 0,39·buồng.
  ⇒ Nhiệt%_cân_bằng(T) = ((T − 114)/0,39 − 130)/2,2. Dưới ~165 °C máy không đứng được ở 0 % (SV tối thiểu 130) ⇒ bật/tắt Lệnh nhiệt.
Thuật toán mỗi mốc:
  CHẠY  lên: 100 % · xuống: TẮT Lệnh nhiệt (nguội nhanh nhất). Ngắt SỚM khi BT + độ dốc·(40 s lên / 25 s xuống) chạm mốc ∓ 3 °C.
  GIỮ   đặt mức cân bằng (lên: làm tròn XUỐNG, xuống: làm tròn LÊN) — tiến về mốc từ phía an toàn; mỗi 20 s: dưới mốc và không đang
        lên thì +1 %; sắp vượt (BT + dốc·30 s > mốc + 1) thì −2 %. Mốc thấp (cân bằng < 0 %): bật / tắt Lệnh nhiệt quanh mốc.
  ĐẠT   |BT − mốc| ≤ 1,5 °C liên tục 60 s ⇒ mốc kế. Vọt lố = vượt mốc > 1,5 °C theo chiều đang đi (ghi lại để học).
An toàn: ET > 255 ⇒ tắt Lệnh nhiệt; mất số liệu > 5 s ⇒ dừng; hết mốc ⇒ giữ mốc cuối, trả quyền."""
import csv
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import otl_link as L  # noqa: E402

TM = sys.argv[1]
MOC = [float(x) for x in sys.argv[2:]]
os.makedirs(TM, exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
A0, K = 114.0, 0.39
LAG_LEN, LAG_XUONG, ET_MAX = 30.0, 20.0, 255.0
CHU_KY_GIU, KI_GIU, DAT_GIAY = 8.0, 0.15, 30.0


# Bảng CÂN BẰNG học từ mốc đã đạt 14/10 (gió 85 %, máy đã ngấm): °C -> Nhiệt %. Nội suy / ngoại suy tuyến tính.
# Công thức buồng (A0, K) lệch 5–6 % ở 190 °C -> giữ mốc bò 7 phút; bảng đo thật thay thế.
BANG = [(170, 5.0), (190, 35.0), (200, 41.0), (210, 51.0), (230, 72.0)]   # cập nhật 20:16: 210 giữ 51 %, 230 giữ 72 %


def can_bang(t):
    b = BANG
    if t <= b[0][0]:
        return b[0][1] + (t - b[0][0]) * (b[1][1] - b[0][1]) / (b[1][0] - b[0][0])
    for (t1, g1), (t2, g2) in zip(b, b[1:]):
        if t <= t2:
            return g1 + (t - t1) * (g2 - g1) / (t2 - t1)
    (t1, g1), (t2, g2) = b[-2], b[-1]
    return g2 + (t - t2) * (g2 - g1) / (t2 - t1)


cfg = L.load_config()
cfg.update(port=os.environ.get("OTL_PORT", "COM13"), doc_buong=True)
l = L.RoasterLink(cfg)
l.start()
# Artisan xem đồ thị CÙNG LÚC qua cầu Modbus TCP 127.0.0.1:5020 (chủ máy 14/10: "vừa điều khiển bằng agent mà vừa xem được artisan")
from cau_artisan import CauArtisan  # noqa: E402
CauArtisan(lambda: (l.snapshot().get("data") or {}).get("artisan_regs")).start()
t0 = time.time()
while l.snapshot().get("state") != "connected" and time.time() - t0 < 20:
    time.sleep(0.3)

f = open(os.path.join(TM, "log.csv"), "a", newline="", encoding="utf-8")
w = csv.writer(f)
w.writerow(["gio", "moc", "pha", "bt", "et", "buong", "doc_cpm", "gas", "lenh_nhiet", "flags_hex", "ghi_chu"])
ls, gas, nhiet_on = [], None, None
t_xung = 0.0


def snap():
    s = l.snapshot()
    return s, (s.get("data") or {})


def dat_gas(v):
    global gas
    v = int(max(0, min(100, round(v))))
    if v != gas:
        l.write("gas", v)
        gas = v


def dat_nhiet(on):
    global nhiet_on
    if on != nhiet_on:
        l.write("ignite", 1 if on else 0)
        nhiet_on = on
        print(time.strftime("%H:%M:%S"), "LENH NHIET", "BAT" if on else "TAT")


def doc():
    """Độ dốc hồi quy BT 20 s (°C/giây)."""
    now = time.time()
    cs = [(t, b) for t, b in ls if now - t <= 20]
    if len(cs) < 8:
        return 0.0
    tt = sum(t for t, _ in cs) / len(cs)
    bb = sum(b for _, b in cs) / len(cs)
    m = sum((t - tt) ** 2 for t, _ in cs)
    return sum((t - tt) * (b - bb) for t, b in cs) / m if m else 0.0


try:
    s, d = snap()
    if not (d.get("flags") or {}).get("pc_control"):
        sys.exit("Chua bat 'Dieu khien tu PC' tren HMI")
    l.agent_open(3600, stale=15)
    if os.environ.get("ARTISAN") == "1":                 # chủ máy: bắt đầu bài thì bật đồ thị Artisan, xong thì tắt + lưu để nộp
        import artisan_ui
        time.sleep(3)                                     # cầu TCP có số trước khi Artisan ON
        artisan_ui.bat_ghi()
        print(time.strftime("%H:%M:%S"), "ARTISAN ON + START")
    gas, nhiet_on = int(d.get("gas", 0)), bool((d.get("flags") or {}).get("gas"))
    for i, moc in enumerate(MOC):
        pha, t_dat, t_giu, vot, ghi_moc, I_giu = "CHAY", None, 0.0, 0.0, time.time(), 0.0
        di_len = moc > d.get("bt", 0)
        cb = can_bang(moc)
        print(time.strftime("%H:%M:%S"), "=== MOC %d/%d: %.0f °C (%s) — can bang %.1f %%" % (i + 1, len(MOC), moc,
                                                                                         "LEN" if di_len else "XUONG", cb))
        while True:
            l.agent_beat()
            s, d = snap()
            if s.get("state") != "connected" or s.get("age_ms", 1e9) > 5000:
                print(time.strftime("%H:%M:%S"), "MAT SO LIEU — dung")
                raise SystemExit(2)
            if not (d.get("flags") or {}).get("pc_control"):
                print(time.strftime("%H:%M:%S"), "PC control TAT — tra quyen")
                raise SystemExit(0)
            now = time.time()
            bt, et = float(d.get("bt", 0)), float(d.get("et", 0))
            ls.append((now, bt))
            while ls and now - ls[0][0] > 40:
                ls.pop(0)
            g = doc()
            ghi = ""
            if et > ET_MAX:
                dat_nhiet(False)
                ghi = "AN TOAN ET"
            elif pha == "CHAY":
                if di_len:
                    dat_nhiet(True)
                    dat_gas(100)
                    if bt + g * LAG_LEN >= moc - 1.5:
                        pha = "GIU"
                else:
                    dat_nhiet(False)
                    if bt + g * LAG_XUONG <= moc + 1.5:
                        pha = "GIU"
                if pha == "GIU":
                    if cb >= 0:
                        # tiến về mốc từ PHÍA AN TOÀN: lên đặt thấp hơn bảng 4 %, xuống cao hơn 4 % (210: bảng 54 % -> lố 3 °C, 14/10)
                        I_giu = -4.0 if di_len else 4.0
                        dat_gas(cb + I_giu)
                        dat_nhiet(True)
                    print(time.strftime("%H:%M:%S"), "-> GIU  bt=%.1f doc=%+.1f°C/ph gas=%s" % (bt, g * 60, gas))
            else:
                if cb < 0:                                       # mốc thấp: XUNG Lệnh nhiệt ngắn, gas 0
                    # 14/10 20:35: bật/tắt theo dự báo 20 s -> mỗi lần bật SV 0->130, VX4 nung hết cỡ -> BT bật +5 °C, dao động
                    # 153↔160 không vào được ±1,5. Nay: chỉ bật khi BT dự báo 5 s < mốc + 0,5, mỗi xung tối đa 3 s.
                    dat_gas(0)
                    if nhiet_on and now - t_xung >= 3.0:
                        dat_nhiet(False)
                    elif not nhiet_on and bt + g * 5 < moc + 0.5:
                        dat_nhiet(True)
                        t_xung = now
                elif now - t_giu >= CHU_KY_GIU:
                    t_giu = now
                    lech = moc - bt
                    if (bt - moc > 0.8) if di_len else (moc - bt > 0.8):     # chớm lố theo chiều đang đi -> lùi ngay
                        I_giu -= 1.5 if di_len else -1.5
                    elif abs(g * 60) < 6:                                     # chỉ tích khi BT đã gần đứng
                        I_giu += KI_GIU * lech
                    I_giu = max(-30.0, min(30.0, I_giu))
                    dat_gas(cb + I_giu)
            # vọt lố = vượt mốc theo chiều đang đi
            vot = max(vot, (bt - moc) if di_len else (moc - bt))
            if abs(bt - moc) <= 1.5:
                t_dat = t_dat or now
                if now - t_dat >= DAT_GIAY:
                    print(time.strftime("%H:%M:%S"), "DAT MOC %.0f sau %.0f s — vot lo toi da %.1f °C — gas giu %s"
                          % (moc, now - ghi_moc, max(0.0, vot), gas))
                    break
            else:
                t_dat = None
            fl = d.get("flags") or {}
            w.writerow([time.strftime("%H:%M:%S"), moc, pha, bt, et, d.get("chamber"), round(g * 60, 2), d.get("gas"),
                        int(bool(fl.get("gas"))), "%04X" % sum(m for k, m in L.pc_link_map.FLAGS_BITS.items() if fl.get(k)),
                        ghi])
            f.flush()
            time.sleep(1)
    print(time.strftime("%H:%M:%S"), "XONG CHUOI MOC")
    if os.environ.get("ARTISAN") == "1":
        import artisan_ui
        print(time.strftime("%H:%M:%S"), "ARTISAN DA LUU:", artisan_ui.tat_luu())
finally:
    l.agent_close("xong chuoi moc")
    time.sleep(1.5)
    l.stop()
    f.close()
    print(time.strftime("%H:%M:%S"), "DUNG")
