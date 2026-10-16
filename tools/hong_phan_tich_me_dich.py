# -*- coding: utf-8 -*-
"""Phân tích mẻ anh Thành lái theo ĐÍCH mốc (agent OTL Hồng, 15/10/2026). CHỈ ĐỌC file, không đụng máy.

    python tools/hong_phan_tich_me_dich.py <thư mục quan sát> [--alog <file.alog>] [--de 240 --fcs 540 --drop 780 --dev 240]

Đọc log.csv + moc.json của `hong_quan_sat_me.py` ⇒ in bảng đích ↔ thực, bảng thao tác (mọi lần đổi Nhiệt / gió / trống sau
CHARGE), RoR + mức Nhiệt từng giai đoạn, k David (`k = RoR / (ET − BT)`, chỉ tham khảo), và vẽ gian_do_k.png có vạch đích.
Có .alog ⇒ thêm k David chính thức từ giản đồ Artisan (`cach_tinh_david.phan_tich`)."""
import csv
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cach_tinh_david as cd  # noqa: E402
import hong_qua_panel as hq  # noqa: E402


def mmss(s):
    if s is None:
        return "—"
    s = int(round(s))
    return "%s%d:%02d" % ("-" if s < 0 else "", abs(s) // 60, abs(s) % 60)


def lech(s, d):
    return "—" if s is None else "%+d s" % int(round(s - d))


def nap(tm):
    rows = list(csv.DictReader(open(os.path.join(tm, "log.csv"), encoding="utf-8")))
    rows = [r for r in rows if r["t_rang"] not in ("", None)]
    f = lambda k: np.array([float(r[k]) if r[k] not in ("", "nan") else np.nan for r in rows])  # noqa: E731
    d = {k: f(k) for k in ("t_rang", "bt", "et", "buong", "dat_nhiet", "nhiet", "lenh", "dat_gio", "gio_pv", "dat_trong")}
    d["gio"] = [r["gio"] for r in rows]
    moc = json.load(open(os.path.join(tm, "moc.json"), encoding="utf-8"))
    return d, moc


def ror_doi_xung(t, bt, cua=30.0):
    ror, _ = cd.k_day(t, bt, bt, cua)  # k_day trả (ror, k); chỉ cần ror
    return ror


def thao_tac(d):
    out = []
    key = list(zip(d["nhiet"], d["dat_gio"], d["dat_trong"], d["lenh"]))
    for i in range(1, len(key)):
        if key[i] != key[i - 1]:
            out.append((d["t_rang"][i], d["gio"][i], key[i - 1], key[i], d["bt"][i]))
    return out


def giai_doan(d, moc, ror):
    t = d["t_rang"]
    mc = moc["moc_giay"]
    bien = [("sấy (TP→DE; RoR trước TP âm nên bỏ)", mc.get("TP", 0), mc.get("DE")), ("Maillard (DE→FCs)", mc.get("DE"), mc.get("FCs")),
            ("phát triển (FCs→DROP−20 s; RoR đối xứng 30 s)", mc.get("FCs"), (mc["DROP"] - 20) if mc.get("DROP") else None)]
    out = []
    for ten, a, b in bien:
        if a is None or b is None:
            continue
        m = (t >= a) & (t <= b)
        if m.sum() < 5:
            continue
        out.append((ten, b - a, float(np.nanmean(d["nhiet"][m])), float(np.nanmin(d["nhiet"][m])),
                    float(np.nanmax(d["nhiet"][m])), float(np.nanmean(ror[m])), float(np.nanmean(d["dat_gio"][m]))))
    return out


def ve(tm, d, moc, ror, k, dich, tieu_de):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    t = d["t_rang"] / 60
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(13, 8.5), sharex=True, gridspec_kw={"height_ratios": [3, 1.6]})
    a1.plot(t, d["bt"], color="#1f5fbf", lw=2, label="BT")
    a1.plot(t, d["et"], color="#c62828", lw=1.6, label="ET")
    a1.set_ylabel("°C")
    b1 = a1.twinx()
    b1.plot(t, ror, color="#2e7d32", lw=1.3, label="RoR BT (°C/ph)")
    b1.step(t, d["nhiet"], color="#ef6c00", lw=1.2, where="post", label="Nhiệt %")
    b1.step(t, d["dat_gio"], color="#6a1b9a", lw=1.0, ls=":", where="post", label="gió %")
    b1.set_ylim(-5, 105)
    b1.set_ylabel("RoR °C/ph · Nhiệt % · gió %")
    mc = moc["moc_giay"]
    for ten, dd in (("DE", dich["de"]), ("FCs", dich["fcs"]), ("DROP", dich["drop"])):
        a1.axvline(dd / 60, color="#555", ls="--", lw=1.2)
        a1.text(dd / 60, a1.get_ylim()[1], " đích %s %s" % (ten, mmss(dd)), va="top", fontsize=9, color="#333")
        if mc.get(ten) is not None:
            a1.axvline(mc[ten] / 60, color="#000", lw=1.6)
            a1.text(mc[ten] / 60, a1.get_ylim()[0], " %s %s (%s)" % (ten, mmss(mc[ten]), lech(mc[ten], dd)),
                    va="bottom", fontsize=9, rotation=90)
    h1, l1 = a1.get_legend_handles_labels()
    h2, l2 = b1.get_legend_handles_labels()
    a1.legend(h1 + h2, l1 + l2, loc="center right", fontsize=8)
    a1.set_title(tieu_de + " — đích DE %s · FCs %s · DROP %s · dev ~%s" % tuple(mmss(dich[x]) for x in ("de", "fcs", "drop", "dev")))
    a2.plot(t, k, color="#37474f", lw=1.5, label="k David = RoR / (ET − BT)  (tham khảo)")
    for dd in (dich["de"], dich["fcs"], dich["drop"]):
        a2.axvline(dd / 60, color="#555", ls="--", lw=1.0)
    a2.set_ylabel("k (1/ph)")
    a2.set_xlabel("thời gian từ CHARGE (phút)")
    a2.legend(fontsize=8)
    a2.grid(alpha=0.3)
    a1.grid(alpha=0.3)
    duong = os.path.join(tm, "gian_do_k.png")
    fig.tight_layout()
    fig.savefig(duong, dpi=110)
    return duong


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    pos, opt = hq._tach_opt(sys.argv[1:])
    tm = pos[0]
    dich = {k: float(opt.get(k, v)) for k, v in (("de", 240), ("fcs", 540), ("drop", 780), ("dev", 240))}
    d, moc = nap(tm)
    mc = moc["moc_giay"]
    ror = ror_doi_xung(d["t_rang"], d["bt"])
    hieu = d["et"] - d["bt"]
    k = np.where(hieu >= cd.ET_BT_MIN, ror / np.where(hieu == 0, np.nan, hieu), np.nan)
    t_tp, t_drop = mc.get("TP", 60), mc.get("DROP", d["t_rang"][-1])
    k = np.where((d["t_rang"] >= t_tp + 15) & (d["t_rang"] <= t_drop - 20), k, np.nan)  # trước TP / sau DROP: k vô nghĩa
    dev = mc["DROP"] - mc["FCs"] if mc.get("DROP") is not None and mc.get("FCs") is not None else None
    print("## Đích ↔ thực (nguồn: firmware $69–$77 / log panel 1 Hz)")
    print("| Mốc | Đích | Thực | Lệch | BT |")
    print("|---|---|---|---|---|")
    for ten, dd in (("TP", None), ("DE", dich["de"]), ("FCs", dich["fcs"]), ("DROP", dich["drop"])):
        s = mc.get(ten)
        print("| %s | %s | %s | %s | %s |" % (ten, mmss(dd) if dd else "—", mmss(s), lech(s, dd) if dd else "—",
                                         "%.1f" % moc["moc_bt"][ten] if ten in moc["moc_bt"] else "—"))
    print("| dev (FCs→DROP) | 4:00 | %s | %s | — |" % (mmss(dev), lech(dev, dich["dev"])))
    if dev is not None:
        print("| DTR | %.1f %% (4:00 / 13:00) | %.1f %% | — | — |" % (100 * dich["dev"] / dich["drop"], 100 * dev / mc["DROP"]))
    print("\n## Giai đoạn (Nhiệt TB / min–max · RoR TB · gió TB)")
    for ten, dai, tb, lo, hi, r, g in giai_doan(d, moc, ror):
        print("- %s: %s · Nhiệt %.0f %% (%.0f–%.0f) · RoR %.1f °C/ph · gió %.0f %%" % (ten, mmss(dai), tb, lo, hi, r, g))
    print("\n## Thao tác (Nhiệt thực / gió đặt / trống đặt / Lệnh)")
    for tr, gio, a, b, bt in thao_tac(d):
        if tr >= 0:
            print("- %s (%s) · BT %.1f · RoR %+.1f · %s → %s" % (mmss(tr), gio, bt, float(np.interp(tr, d["t_rang"], ror)),
                                                           "/".join("%g" % x for x in a), "/".join("%g" % x for x in b)))
    print("\n## k David (log panel, RoR đối xứng 30 s; tham khảo)")
    for ph in (2, 4, 6, 8, 9, 10, 12):
        m = np.abs(d["t_rang"] - ph * 60) <= 15
        if m.any():
            print("- phút %d: k %.3f · RoR %.1f · ET−BT %.1f" % (ph, np.nanmean(k[m]), np.nanmean(ror[m]), np.nanmean(hieu[m])))
    if "alog" in opt:
        print("\n## k David chính thức (.alog)")
        print(cd.in_kq(cd.phan_tich(opt["alog"])))
    print("\nảnh:", ve(tm, d, moc, ror, k, dich, opt.get("tieu_de", os.path.basename(os.path.normpath(tm)))))


if __name__ == "__main__":
    main()
