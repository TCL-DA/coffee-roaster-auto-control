# -*- coding: utf-8 -*-
"""VÒNG NGOÀI giữ BT cho máy điện VX4 — chạy CẠNH tools/lai_may.py, không chiếm cổng (đọc log.csv, ghi lenh.txt).

Rút từ 14/10/2026: hệ có HAI tầng — tầng nhanh (Nhiệt% -> SV -> buồng -> ET, ~15 s) và tầng chậm (thân lồng ngấm nhiệt, hàng
chục phút, làm BT trôi dù Nhiệt% đứng yên). PI dự báo theo RoR (tầng nhanh) bù quá tay -> dao động ±15 °C. Cách đúng: CHỈ tích phân,
đi chậm: mỗi CHU_KY giây, Nhiệt% += KI × (đích − BT trung bình 15 s), kẹp ±BUOC. Độ nhạy đo được ~0,7 °C BT / 1 %.

    python vong_ngoai_bt.py <thư mục lai_may> <đích BT> [KI=0.4] [chu_ky=30] [buoc=3]
In mỗi chu kỳ: BT, ET, ET−BT, RoR ET, Nhiệt%, lệnh mới."""
import csv
import os
import sys
import time

TM, DICH = sys.argv[1], float(sys.argv[2])
KI = float(sys.argv[3]) if len(sys.argv) > 3 else 0.4
CHU_KY = float(sys.argv[4]) if len(sys.argv) > 4 else 30
BUOC = float(sys.argv[5]) if len(sys.argv) > 5 else 3
sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
LOG, LENH = os.path.join(TM, "log.csv"), os.path.join(TM, "lenh.txt")


def cuoi(n=15):
    with open(LOG, encoding="utf-8") as f:
        r = [x for x in csv.DictReader(f) if x.get("gio") != "gio"]
    return r[-n:]


while True:
    r = cuoi()
    if len(r) < 5:
        time.sleep(2)
        continue
    bt = sum(float(x["bt"]) for x in r) / len(r)
    et = float(r[-1]["et"])
    gas = float(r[-1]["gas"] or 0)
    if "0002" not in "%04X" % (int(r[-1]["flags_hex"], 16) & 0x0002):
        print(time.strftime("%H:%M:%S"), "Lenh nhiet TAT — vong ngoai cho")
        time.sleep(CHU_KY)
        continue
    moi = round(max(0, min(100, gas + max(-BUOC, min(BUOC, KI * (DICH - bt))))))
    buong = r[-1].get("buong") or "?"
    print(time.strftime("%H:%M:%S"), "BT %.1f (tb15s) ET %.1f BUONG %s ET-BT %.1f buong-ET %s RoR_ET %s nhiet %d (SV %d) -> %d"
          % (bt, et, buong, et - bt, ("%.1f" % (float(buong) - et)) if buong != "?" else "?", r[-1].get("ror_et"), gas,
             130 + 2.2 * gas, moi))
    if moi != gas:
        with open(LENH, "a", encoding="utf-8") as f:
            f.write("gas %d\n" % moi)
    time.sleep(CHU_KY)
