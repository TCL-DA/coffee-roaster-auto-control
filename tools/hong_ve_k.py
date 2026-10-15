# -*- coding: utf-8 -*-
"""Vẽ giản đồ mẻ + hệ số k David (k = RoR BT / (ET − BT)) từ log 1 Hz panel (hong_quan_sat.py) — chỉ đọc file.
    python tools/hong_ve_k.py <log.csv> <ra.png> [--tu HH:MM:SS] [--den HH:MM:SS] [--nguong 15]
Mốc lấy từ mã trạng thái $40 firmware trong log (86 CHARGE mở · 81 TP · 82 vàng/DE · 83 FCs · 88/144 DROP); thiếu thì dò theo BT."""
import csv
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hong_qua_panel as hq  # noqa: E402

MA_MOC = {86: "CHARGE", 81: "TP", 82: "DE (vàng)", 83: "FCs", 88: "DROP", 144: "DROP"}


def doc(duong):
    with open(duong, encoding="utf-8") as f:
        r = list(csv.reader(f))[1:]
    a = lambda k: np.array([float(x[k]) for x in r])  # noqa: E731
    return [x[0] for x in r], a(1), a(2), a(3), a(4), a(6), a(9), a(12).astype(int)


def doc_hoi_quy(t, y, cua):
    out = np.full(len(t), np.nan)
    for i in range(len(t)):
        m = (t > t[i] - cua) & (t <= t[i])
        if m.sum() >= cua * 0.6:
            out[i] = 60 * np.polyfit(t[m], y[m], 1)[0]
    return out


def main():
    pos, opt = hq._tach_opt(sys.argv[1:])
    gio, t, bt, et, bu, nh, gi, ma = doc(pos[0])
    nguong = float(opt.get("nguong", 15))
    moc = {}
    for i in range(1, len(ma)):
        if ma[i] != ma[i - 1] and ma[i] in MA_MOC and MA_MOC[ma[i]] not in moc:
            moc[MA_MOC[ma[i]]] = i
    i0 = moc.get("CHARGE", 0)
    if "tu" in opt:
        i0 = next(i for i in range(len(gio)) if gio[i] >= opt["tu"])
    i1 = moc.get("DROP", len(t) - 1)
    if "den" in opt:
        i1 = next((i for i in range(len(gio)) if gio[i] >= opt["den"]), len(t) - 1)
    i1 = min(len(t) - 1, i1 + 30)
    s = slice(i0, i1 + 1)
    tt = (t[s] - t[i0]) / 60
    ror = doc_hoi_quy(t, bt, 30)[s]
    dlt = (et - bt)[s]
    k = np.where(dlt >= nguong, ror / np.maximum(dlt, 1e-6), np.nan)
    tp = moc.get("TP", i0) - i0
    k[: max(tp, 0) + 30] = np.nan                     # trước TP + 30 s: RoR âm / nhiễu nạp hạt — bỏ
    k[max(0, len(k) - 31):] = np.nan                   # sau DROP: hạt đã ra — bỏ
    ks = np.convolve(np.nan_to_num(k), np.ones(15) / 15, "same")
    ks[np.isnan(k)] = np.nan
    ks[-7:] = np.nan                                   # mép cửa sổ trượt
    fig, (ax, axd) = plt.subplots(2, 1, figsize=(13, 8.5), sharex=True, gridspec_kw={"height_ratios": [3.2, 1]})
    ax.plot(tt, et[s], color="#d62728", lw=1.6, label="ET")
    ax.plot(tt, bt[s], color="#1f77b4", lw=2.0, label="BT")
    if np.isfinite(bu[s]).any():
        ax.plot(tt, bu[s], color="#ff7f0e", lw=1.0, alpha=0.6, label="Buồng VX4")
    ax.set_ylabel("Nhiệt độ (°C)")
    ax.grid(alpha=0.3)
    ax2 = ax.twinx()
    ax2.plot(tt, ror, color="#2ca02c", lw=1.3, label="RoR BT (°C/ph, hồi quy 30 s)")
    ax2.set_ylabel("RoR BT (°C/ph)  ·  k × 100", color="#2ca02c")
    ax2.plot(tt, ks * 100, color="#9467bd", lw=2.2, label="k David × 100 (mượt 15 s)")
    ax2.set_ylim(-5, max(30, np.nanmax(np.r_[ror[tp + 30:], ks[np.isfinite(ks)] * 100]) * 1.15 if len(ror) > tp + 30 else 30))
    x_cu, tang = -9.0, 0
    for ten, i in moc.items():
        if i0 <= i <= i1:
            x = (t[i] - t[i0]) / 60
            tang = tang + 1 if x - x_cu < 1.2 else 0          # mốc sát nhau: hạ nhãn xuống một tầng
            x_cu = x
            ax.axvline(x, color="k", ls="--", lw=0.8, alpha=0.6)
            y0, y1 = ax.get_ylim()
            ax.text(x, y1 - tang * 0.07 * (y1 - y0), " %s\n %d:%02d · %.1f" % ((ten,) + divmod(int(t[i] - t[i0]), 60) + (bt[i],)),
                    va="top", fontsize=8.5)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="lower right", fontsize=8.5)
    axd.step(tt, nh[s], where="post", color="#d62728", label="Nhiệt % (anh đặt / máy)")
    axd.step(tt, gi[s], where="post", color="#17becf", label="Gió %")
    axd.set_ylim(0, 105)
    axd.set_ylabel("%")
    axd.set_xlabel("Thời gian từ CHARGE (phút)")
    axd.grid(alpha=0.3)
    axd.legend(loc="upper left", fontsize=8.5)
    ax.set_title(opt.get("ten", "Mẻ hồ sơ 1 · 500 g") + " · 15/10/2026 · charge 170 °C · máy điện VX4 — BT/ET, RoR và hệ số k David = RoR / (ET − BT)\n"
                 "k chỉ tính khi ET − BT ≥ %.0f °C và sau TP + 30 s · tham khảo, không dùng để lái" % nguong, fontsize=10.5)
    fig.tight_layout()
    fig.savefig(pos[1], dpi=110)
    v = lambda a, b: np.nanmean(k[a:b]) if np.isfinite(k[a:b]).any() else float("nan")  # noqa: E731
    n = len(k)
    print("k nền (TP+30 s → DE): %.4f" % v(tp + 30, moc.get("DE (vàng)", i0 + n // 2) - i0))
    if "FCs" in moc:
        print("k DE → FCs: %.4f · k FCs → DROP: %.4f" % (v(moc["DE (vàng)"] - i0, moc["FCs"] - i0), v(moc["FCs"] - i0, i1 - i0 - 30)))
    print("k 60 s cuối trước DROP: %.4f" % v(max(0, i1 - i0 - 90), i1 - i0 - 30))
    print("mốc:", {kk: "%s (%d:%02d)" % ((gio[i],) + divmod(int(t[i] - t[i0]), 60)) for kk, i in moc.items()})


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
