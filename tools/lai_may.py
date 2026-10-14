# -*- coding: utf-8 -*-
"""LÁI MÁY RANG qua PC_Link (cổng: biến OTL_PORT, mặc định COM13) — công cụ của agent OTL Hồng (.claude/agents/otl-hong.md) — không chạm màn, không chụp ảnh (14/10/2026).
Cần cờ 'Điều khiển từ PC' trên HMI (pc_control). Chủ máy cho toàn quyền nhiệt / gió / trống tới HET.

    python lai_may.py <đích BT> <hết lúc HH:MM> <thư mục>
Thư mục: log.csv (mỗi giây, đủ trường), trang_thai.json (đọc nhanh), lenh.txt (lệnh tay, mỗi dòng 1 lệnh):
    gas|air|drum <0-100> · charge|drop|cool|escape <0|1> · dich <°C> · giu on|off
Giữ BT: PI có dự báo RoR, I luôn tích phân (kẹp 0..100, chống tràn khi bão hoà). An toàn: ET>ET_MAX / BT>đích+15 -> nhiệt 0;
mất số liệu >5 s -> dừng; hết giờ -> nhiệt 0 rồi trả quyền (firmware tự trả khi im nhịp)."""
import csv
import datetime as dt
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import otl_link as L  # noqa: E402

DICH = float(sys.argv[1])
HET = dt.datetime.combine(dt.date.today(), dt.datetime.strptime(sys.argv[2], "%H:%M").time())
TM = sys.argv[3]
os.makedirs(TM, exist_ok=True)
ET_MAX, CU_MAX = 255.0, 5.0
GIO_MIN = float(os.environ.get("GIO_MIN", 34))   # gió tối thiểu máy điện VX4 = 50 Hz (chủ máy 14/10); dải 45–60 Hz ⇒ 50 Hz = 33,3 % ⇒ 34 %
KP, TAU, KI, CHU_KY = 0.8, 0.8, 0.15, 12.0
BUOC_MAX = 4               # mỗi lần chỉnh đổi tối đa ±4 % — VX4 có PID riêng, giật SV liên tục làm điện trở nung / ngắt dồn dập
sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

cfg = L.load_config()
cfg.update(port=os.environ.get("OTL_PORT", "COM13"), doc_buong=True)
l = L.RoasterLink(cfg)
l.start()
t0 = time.time()
while l.snapshot().get("state") != "connected" and time.time() - t0 < 20:
    time.sleep(0.3)

COT = ["gio", "bt", "et", "buong", "ror_bt_tu_tinh", "ror_bt", "ror_et", "gas", "air", "drum", "drum_hz", "sv", "vac", "step",
       "t_roast", "flags_hex", "pc", "lenh_gas", "I", "dich", "giu", "ghi_chu"]
fcsv = open(os.path.join(TM, "log.csv"), "a", newline="", encoding="utf-8")
w = csv.writer(fcsv)
w.writerow(COT)
p_lenh = os.path.join(TM, "lenh.txt")
open(p_lenh, "a").close()
da_doc_lenh = os.path.getsize(p_lenh)

lich_su, I, gui, t_ctl, giu, lai = [], None, None, 0.0, True, False
canh_bao_tat = False
t_on_dinh = None          # BT trong ±2 °C và |RoR| < 1,5 liên tục 3 phút -> SẴN SÀNG NẠP


def gui_lenh(ten, v):
    r = l.write(ten, v)
    print(time.strftime("%H:%M:%S"), "GUI", ten, v, "->", r.get("status") or r.get("err"))
    return r


def xac_nhan(ten, v, giay=3.0, co=False):
    """Đọc lại từ board: giá trị (gas/air/drum) hoặc cờ (charge/drop/cool/escape) phải khớp."""
    t = time.time()
    while time.time() - t < giay:
        d = l.snapshot().get("data") or {}
        if ten in ("gas", "air", "drum") and not co:
            if int(d.get(ten, -1)) == int(v):
                return True
        elif bool((d.get("flags") or {}).get(ten)) == bool(int(v)):
            return True
        time.sleep(0.2)
    return False


def doc_lenh():
    global da_doc_lenh, DICH, giu, I, KP, KI, TAU
    n = os.path.getsize(p_lenh)
    if n <= da_doc_lenh:
        return
    with open(p_lenh, encoding="utf-8") as f:
        f.seek(da_doc_lenh)
        moi = f.read()
    da_doc_lenh = n
    for dong in moi.splitlines():
        p = dong.split()
        if len(p) != 2:
            continue
        k, v = p[0].lower(), p[1].lower()
        if k == "dich":
            DICH = float(v)
            print(time.strftime("%H:%M:%S"), "DICH MOI", DICH)
        elif k in ("kp", "ki", "tau"):
            if k == "kp":
                KP = float(v)
            elif k == "ki":
                KI = float(v)
            else:
                TAU = float(v)
            print(time.strftime("%H:%M:%S"), "THAM SO", k, v)
        elif k == "ignite":
            # Bật / tắt 'Lệnh nhiệt' (START_GAS). Firmware tự TẮT khi mất nhịp PC (pc_lost) — bật lại có chủ đích ở đây.
            gui_lenh("ignite", float(v))
            print(time.strftime("%H:%M:%S"), "XAC NHAN ignite", v, "DAT" if xac_nhan("gas", v, co=True) else "KHONG DAT")
        elif k == "giu":
            giu = v == "on"
            print(time.strftime("%H:%M:%S"), "GIU BT", giu)
        elif k == "air" and float(v) < GIO_MIN:
            print(time.strftime("%H:%M:%S"), "TU CHOI air", v, "< gio toi thieu", GIO_MIN)
        elif k in ("gas", "air", "drum", "charge", "drop", "cool", "escape"):
            if k == "gas":
                giu = False                       # chỉnh nhiệt tay -> tạm thôi giữ BT
            gui_lenh(k, float(v))
            print(time.strftime("%H:%M:%S"), "XAC NHAN", k, v, "DAT" if xac_nhan(k, v) else "KHONG DAT")


def dat_gas(v, ly_do):
    global gui
    v = int(max(0, min(100, round(v))))
    if v != gui:
        gui_lenh("gas", v)
        gui = v
        print(time.strftime("%H:%M:%S"), "nhiet ->", v, ly_do)


try:
    while True:
        s = l.snapshot()
        d = s.get("data") or {}
        fl = d.get("flags") or {}
        now = time.time()
        ghi = ""
        if s.get("state") != "connected" or s.get("age_ms", 1e9) > CU_MAX * 1000:
            print(time.strftime("%H:%M:%S"), "MAT SO LIEU", s.get("state"), s.get("err"))
            if now - t0 > 30:
                break
            time.sleep(1)
            continue
        pc = bool(fl.get("pc_control"))
        if not pc:
            if lai:
                print(time.strftime("%H:%M:%S"), "PC control TAT — tra quyen, DUNG")
                break
            time.sleep(1)
            continue
        if not lai:
            l.agent_open((HET - dt.datetime.now()).total_seconds(), stale=15)
            lai, I, gui = True, float(os.environ.get("I0", d.get("gas", 50))), int(d.get("gas", 50))
            print(time.strftime("%H:%M:%S"), "NHAN QUYEN LAI (PC_Link) — I", I)
        l.agent_beat()
        bt, et = d.get("bt", 0.0), d.get("et", 0.0)
        lich_su.append((now, bt))
        while lich_su and now - lich_su[0][0] > 30:
            lich_su.pop(0)
        # RoR = độ dốc HỒI QUY TUYẾN TÍNH của BT trong 20 s gần nhất (°C/phút).
        # 14/10 19:27: ror_bt của firmware TRỄ 30–40 s và có lúc NGƯỢC DẤU (BT +35 °C/phút mà báo −15) -> bộ lái tăng nhiệt
        # đúng lúc đang vọt -> BT 197 -> 215 °C, cắt an toàn. Hiệu 2 điểm (bản đầu) thì nhiễu. Hồi quy: đúng dấu, ít trễ, ít nhiễu.
        cua_so = [(t, b) for t, b in lich_su if now - t <= 20]
        if len(cua_so) >= 8:
            tb_t = sum(t for t, _ in cua_so) / len(cua_so)
            tb_b = sum(b for _, b in cua_so) / len(cua_so)
            mau = sum((t - tb_t) ** 2 for t, _ in cua_so)
            ror = (sum((t - tb_t) * (b - tb_b) for t, b in cua_so) / mau * 60) if mau > 0 else 0.0
        else:
            ror = 0.0
        if dt.datetime.now() >= HET:
            dat_gas(0, "HET GIO")
            print(time.strftime("%H:%M:%S"), "HET 60 PHUT")
            break
        doc_lenh()
        if abs(bt - DICH) <= 2 and abs(ror) < 1.5:
            if t_on_dinh is None:
                t_on_dinh = now
            elif now - t_on_dinh >= 180:
                print(time.strftime("%H:%M:%S"), "SAN SANG NAP — BT %.1f on dinh 3 phut quanh %.0f" % (bt, DICH))
                t_on_dinh = now + 1e9             # báo một lần cho tới khi lệch lại
        else:
            t_on_dinh = None
        # 14/10 19:11: firmware tự TẮT 'Lệnh nhiệt' khi mất nhịp PC (pc_lost) — máy nguội 187 -> 108 °C mà không ai biết.
        if giu and not fl.get("gas"):
            if not canh_bao_tat:
                print(time.strftime("%H:%M:%S"), "CANH BAO: Lenh nhiet dang TAT (co gas = 0)%s — gui 'ignite 1' neu muon nung"
                      % (" — firmware bao pc_lost" if fl.get("pc_lost") else ""))
            canh_bao_tat = True
        else:
            canh_bao_tat = False
        if et > ET_MAX or bt > DICH + 15:
            ghi = "AN TOAN et=%.1f bt=%.1f" % (et, bt)
            dat_gas(0, ghi)
        elif giu and now - t_ctl >= CHU_KY:
            t_ctl = now
            du_bao = bt + ror * TAU
            u = KP * (DICH - du_bao) + I
            # 19:11 14/10: tích theo sai số HIỆN TẠI khi còn xa đích -> I cộng dồn lên đúng lúc dự báo sắp vọt (I 60 -> 70,
            # đẩy nhiệt ngược chiều). Nay: chỉ tích khi |đích − BT| < 10 °C, theo sai số DỰ BÁO; không tích khi bão hoà.
            if abs(DICH - bt) < 10 and 0 < u < 100:
                I = max(0.0, min(100.0, I + KI * (DICH - du_bao)))
            moi = KP * (DICH - du_bao) + I
            if gui is not None:
                moi = max(gui - BUOC_MAX, min(gui + BUOC_MAX, moi))
            dat_gas(moi, "bt=%.1f ror=%+.1f du_bao=%.1f I=%.1f" % (bt, ror, du_bao, I))
        hang = [time.strftime("%H:%M:%S"), bt, et, d.get("chamber"), round(ror, 2), d.get("ror_bt"), d.get("ror_et"), d.get("gas"),
                d.get("air"), d.get("drum"), d.get("drum_hz"), d.get("sv"), d.get("vac"), d.get("step"), d.get("t_roast"),
                "%04X" % sum(m for k, m in L.pc_link_map.FLAGS_BITS.items() if fl.get(k)), int(pc), gui,
                None if I is None else round(I, 2), DICH, int(giu), ghi]
        w.writerow(hang)
        fcsv.flush()
        with open(os.path.join(TM, "trang_thai.json"), "w", encoding="utf-8") as fj:
            json.dump(dict(zip(COT, hang), co=[k for k, v in fl.items() if v]), fj, ensure_ascii=False)
        time.sleep(1)
finally:
    if lai:
        l.agent_close("ket thuc lai_may")
    time.sleep(1.5)
    l.stop()
    fcsv.close()
    print(time.strftime("%H:%M:%S"), "DUNG")
