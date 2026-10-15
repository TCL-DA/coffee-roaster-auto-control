# -*- coding: utf-8 -*-
"""Phân tích MẺ RANG THẬT từ log 1 Hz của panel (hong_quan_sat.py) — chỉ đọc file (15/10/2026).
    python tools/hong_phan_tich_me.py <log.csv> [--fc HH:MM:SS] [--de 155]
Mốc: CHARGE (BT rơi ≥ 25 °C/30 s) · TP (BT thấp nhất sau CHARGE) · DE (BT ≥ --de) · FC (giờ anh bấm, --fc) · DROP (sau CHARGE
≥ 6 phút BT rơi ≥ 15 °C/30 s). In pha, RoR, crash/flick, DTR, k David (RoR / (ET − BT)), bảng thao tác."""
import csv
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hong_qua_panel as hq  # noqa: E402


def doc(duong):
    with open(duong, encoding="utf-8") as f:
        rows = list(csv.reader(f))[1:]
    a = lambda k: np.array([float(r[k]) for r in rows])  # noqa: E731
    return {"gio": [r[0] for r in rows], "t": a(1), "bt": a(2), "et": a(3), "buong": a(4), "n": a(5), "l": a(7),
            "g": a(8), "tr": a(10)}


def ror(t, y, i, cua=30):
    m = (t <= t[i]) & (t > t[i] - cua)
    return 60 * np.polyfit(t[m], y[m], 1)[0] if m.sum() >= 8 else float("nan")


def hms(s):
    return "%d:%02d" % divmod(int(round(s)), 60)


def main():
    pos, opt = hq._tach_opt(sys.argv[1:])
    d = doc(pos[0])
    t, bt, et = d["t"], d["bt"], d["et"]
    n = len(t)
    ich = next((i for i in range(n) if bt[i] < bt[max(0, i - 30):i + 1].max() - 25), None)
    if ich is None:
        print("Chưa thấy CHARGE trong log")
        return
    ich = max(range(max(0, ich - 30), ich + 1), key=lambda i: bt[i])          # CHARGE = đỉnh ngay trước cú rơi
    itp = ich + int(np.argmin(bt[ich:min(n, ich + 240)]))
    de = float(opt.get("de", 155))
    ide = next((i for i in range(itp, n) if bt[i] >= de), None)
    idr = next((i for i in range(ich + 360, n) if bt[i] < bt[max(ich, i - 30):i + 1].max() - 15), None)
    if idr is not None:
        idr = max(range(max(ich, idr - 30), idr + 1), key=lambda i: bt[i])
    ifc = None
    if "fc" in opt:
        ifc = next((i for i in range(n) if d["gio"][i] >= opt["fc"]), None)
    tc = t[ich]
    het = idr if idr is not None else n - 1
    print("## Mốc (giờ máy · thời gian từ CHARGE · BT)")
    for ten, i in (("CHARGE", ich), ("TP", itp), ("DE %.0f" % de, ide), ("FC", ifc), ("DROP", idr)):
        if i is not None:
            print("- %s: %s · %s · BT %.1f · ET %.1f" % (ten, d["gio"][i], hms(t[i] - tc), bt[i], et[i]))
    tong = t[het] - tc
    print("\n## Pha (tổng %s)" % hms(tong))
    pha = [("Sấy", ich, ide), ("Maillard", ide, ifc if ifc else het), ("Phát triển", ifc, idr)]
    for ten, a, b in pha:
        if a is None or b is None:
            continue
        r = [ror(t, bt, k) for k in (min(a + 30, b), (a + b) // 2, b)]
        print("- %s: %s (%.0f %%) · RoR đầu/giữa/cuối %+.1f / %+.1f / %+.1f °C/ph" % (
            ten, hms(t[b] - t[a]), 100 * (t[b] - t[a]) / tong, *r))
    if ifc is not None and idr is not None:
        print("- DTR %.1f %%" % (100 * (t[idr] - t[ifc]) / tong))
    rr = np.array([ror(t, bt, k) for k in range(itp + 30, het)])
    if len(rr) > 60:
        dr = np.diff(rr[::15])
        lui = [k for k in range(1, len(dr)) if dr[k - 1] < -1.5 and dr[k] > 1.5]
        print("- RoR sau TP: max %+.1f · đổi chiều tăng lại (flick) %d lần · RoR rơi > 3 °C/ph trong 30 s (crash) %d lần" % (
            np.nanmax(rr), len(lui), int(np.sum(np.diff(rr[::30]) < -3))))
    print("\n## k David = RoR / (ET − BT) (tham khảo, không lái)")
    k0 = None
    for ph in (3, 6, 9, 11):
        i = ich + ph * 60
        if i < het:
            dlt = et[i] - bt[i]
            k = ror(t, bt, i) / dlt if dlt >= 8 else None
            k0 = k0 or k
            print("- phút %d: RoR %+.1f · ET−BT %.1f · k %s%s" % (ph, ror(t, bt, i), dlt, "%.3f" % k if k else "—",
                                                            " (×%.2f nền)" % (k / k0) if k and k0 else ""))
    print("\n## Thao tác (Nhiệt/Lệnh/gió/trống) từ CHARGE")
    print("| giờ | t | đổi | BT | RoR |\n|---|---|---|---|---|")
    for i in range(ich + 1, het + 1):
        a = (d["n"][i - 1], d["l"][i - 1], d["g"][i - 1], d["tr"][i - 1])
        b = (d["n"][i], d["l"][i], d["g"][i], d["tr"][i])
        if a != b:
            print("| %s | %s | %d/%d/%d/%d → %d/%d/%d/%d | %.1f | %+.1f |" % (d["gio"][i], hms(t[i] - tc), *a, *b, bt[i],
                                                                         ror(t, bt, i)))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
