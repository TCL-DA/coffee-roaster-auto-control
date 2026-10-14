# -*- coding: utf-8 -*-
"""QUAN SÁT chủ máy rang — CHỈ ĐỌC, không gửi lệnh nào (công cụ học của agent OTL Hồng, 14/10/2026).

    OTL_PORT=COM13 python quan_sat_rang.py <thư mục ra> [phút tối đa]
Ra: log.csv (mỗi giây, đủ trường PC_Link) + thao_tac.csv (mỗi lần người đổi gas/gió/trống/nút: lúc đó BT/ET/RoR/bước mẻ)
+ moc.csv (Charge, TP, DE, FCs, DEV, Drop… khi bước mẻ đổi). In dòng tóm tắt khi có mốc / thao tác.
Không dùng chung cổng với tools/lai_may.py — chỉ chạy một trong hai."""
import csv
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import otl_link as L  # noqa: E402

TM = sys.argv[1]
PHUT = float(sys.argv[2]) if len(sys.argv) > 2 else 120
os.makedirs(TM, exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
TEN_BUOC = {v: k for k, v in L.pc_link_map.STP.items()}
NUT = ("gas", "charge", "drop", "escape", "cool", "auto", "pc_control")

cfg = L.load_config()
cfg.update(port=os.environ.get("OTL_PORT", "COM13"))
l = L.RoasterLink(cfg)
l.start()
t0 = time.time()
while l.snapshot().get("state") != "connected" and time.time() - t0 < 20:
    time.sleep(0.3)

COT = ["gio", "bt", "et", "ror_bt", "ror_et", "gas", "air", "drum", "drum_hz", "sv", "step", "t_roast", "flags_hex"]
f_log = open(os.path.join(TM, "log.csv"), "a", newline="", encoding="utf-8")
f_tt = open(os.path.join(TM, "thao_tac.csv"), "a", newline="", encoding="utf-8")
f_moc = open(os.path.join(TM, "moc.csv"), "a", newline="", encoding="utf-8")
w_log, w_tt, w_moc = csv.writer(f_log), csv.writer(f_tt), csv.writer(f_moc)
w_log.writerow(COT)
w_tt.writerow(["gio", "t_roast", "buoc", "thao_tac", "tu", "thanh", "bt", "et", "ror_bt"])
w_moc.writerow(["gio", "t_roast", "moc", "bt", "et", "ror_bt", "gas", "air", "drum"])
truoc = None
try:
    while time.time() - t0 < PHUT * 60:
        s = l.snapshot()
        d = s.get("data") or {}
        if s.get("state") != "connected" or not d:
            time.sleep(1)
            continue
        fl = d.get("flags") or {}
        g = time.strftime("%H:%M:%S")
        hex_ = "%04X" % sum(m for k, m in L.pc_link_map.FLAGS_BITS.items() if fl.get(k))
        w_log.writerow([g] + [d.get(k) for k in COT[1:-1]] + [hex_])
        if truoc:
            for k in ("gas", "air", "drum"):
                if d.get(k) != truoc["d"].get(k):
                    w_tt.writerow([g, d.get("t_roast"), d.get("step"), k, truoc["d"].get(k), d.get(k), d.get("bt"), d.get("et"),
                                   d.get("ror_bt")])
                    print(g, "THAO TAC", k, truoc["d"].get(k), "->", d.get(k), "| BT", d.get("bt"), "RoR", d.get("ror_bt"))
            for k in NUT:
                if bool(fl.get(k)) != bool(truoc["fl"].get(k)):
                    w_tt.writerow([g, d.get("t_roast"), d.get("step"), "nut_" + k, int(bool(truoc["fl"].get(k))),
                                   int(bool(fl.get(k))), d.get("bt"), d.get("et"), d.get("ror_bt")])
                    print(g, "NUT", k, "BAT" if fl.get(k) else "TAT", "| BT", d.get("bt"))
            if d.get("step") != truoc["d"].get("step"):
                moc = TEN_BUOC.get(d.get("step"), "buoc_%s" % d.get("step"))
                w_moc.writerow([g, d.get("t_roast"), moc, d.get("bt"), d.get("et"), d.get("ror_bt"), d.get("gas"), d.get("air"),
                                d.get("drum")])
                print(g, "MOC", moc, "| t", d.get("t_roast"), "BT", d.get("bt"), "ET", d.get("et"))
        truoc = {"d": dict(d), "fl": dict(fl)}
        for fh in (f_log, f_tt, f_moc):
            fh.flush()
        time.sleep(1)
finally:
    l.stop()
    for fh in (f_log, f_tt, f_moc):
        fh.close()
    print(time.strftime("%H:%M:%S"), "DUNG QUAN SAT")
