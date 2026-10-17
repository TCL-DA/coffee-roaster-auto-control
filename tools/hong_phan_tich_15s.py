"""OTL Hồng — PHÂN TÍCH 15 s khi đang rang (chỉ đọc file, không chạm panel, không làm chậm bộ lái MPC / lệnh DROP).

Mỗi 15 s đọc log.csv / phan_tich_3s.csv / mpc.csv / moc.json của thư mục mẻ ⇒ 1 dòng "PHÂN TÍCH 15s" vào trang_thai.txt:
số đo, chỉ số Artisan, dự báo mốc, RoR dev so dải, việc Hồng đang lái — và từ 17/10 thêm NHÃN LỖI RoR
(cùng ngưỡng với phân tích sau mẻ, `hong_ror_loi.py`; căn cứ skill rang-ca-phe › chan-doan-profile.md).

Chạy khi rang:   python tools/hong_phan_tich_15s.py <thư mục mẻ> [--lo 5 --hi 6]
Phát lại mẻ cũ:  python tools/hong_phan_tich_15s.py <thư mục mẻ> --phat_lai 1 [--lo 5 --hi 6]   (in ra, KHÔNG ghi trang_thai)
"""
import csv
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hong_ror_loi as H  # noqa: E402

CHU_KY = 15.0
GIU_NHAN = 45.0          # s — nhãn còn "đang" nếu lỗi kết thúc trong 45 s gần nhất


def rows(tm, f):
    try:
        return list(csv.DictReader(open(os.path.join(tm, f), encoding="utf-8")))
    except (OSError, csv.Error):
        return []


def mm(s):
    try:
        s = float(s)
        return "%s%d:%02d" % ("-" if s < 0 else "", abs(s) // 60, abs(s) % 60)
    except (TypeError, ValueError):
        return "—"


def lech(s):
    try:
        return "%+ds" % float(s)
    except (TypeError, ValueError):
        return "—"


def chuoi_log(lg):
    x = [r for r in lg if r.get("t_rang") not in ("", None) and r.get("bt") not in ("", "nan", None)]
    t = np.array([float(r["t_rang"]) for r in x])
    bt = np.array([float(r["bt"]) for r in x])
    nh = np.array([float(r["dat_nhiet"]) for r in x])
    gi = np.array([float(r["dat_gio"]) for r in x])
    return t, bt, nh, gi


def nhan_ror(t, bt, nh, gi, moc, lo, hi, bay_gio, da_bao, dich=None):
    """Nhãn lỗi RoR tại bay_gio. Trả (chuỗi nhãn, danh sách mã lỗi mới)."""
    m = {k: v for k, v in moc.items() if v is not None and v <= bay_gio}
    lenh = H.lenh_tu_log(t, nh, gi)
    loi, _ = H.tim_loi(t, bt, m, lenh, lo, hi, bay_gio=bay_gio, dich=dich)
    dang = [l for l in loi if l["den_s"] >= bay_gio - 15 - GIU_NHAN]
    moi = [l for l in loi if (l["ma"], l["tu_s"] // 60) not in da_bao]
    for l in moi:
        da_bao.add((l["ma"], l["tu_s"] // 60))
    if not dang:
        return "RoR: không lỗi (trễ 15 s)", moi
    s = "RoR LỖI: " + " | ".join("%s [%s] %s ⇒ %s" % (l["loai"], l["muc"], l["so_do"], H.VIEC_LAI[l["ma"]]) for l in dang)
    return s, moi


def dong(tm, lg, pt, mp, moc, lo, hi, da_bao):
    x = lg[-1]
    t = float(x["t_rang"])
    bt, et, bu = float(x["bt"]), float(x["et"]), float(x["buong"])
    u = float(x["dat_nhiet"])
    p = pt[-1] if pt else {}
    rb = x.get("ror_bt", "")
    k = (float(rb) / (et - bt)) if et - bt >= 8 and rb not in ("", "nan") else float("nan")
    s = ("PHÂN TÍCH 15s %s · BT %.1f ET %.1f buồng %.1f · ET−BT %.1f · RoR %s · ΔET %s · K %s · Nhiệt %d %% (SV %d) · gió %s %% · trống %s Hz"
         % (mm(t), bt, et, bu, et - bt, rb[:5], p.get("det", "—"), ("%.3f" % k) if k == k else "—", u, 160 + 2.1 * u,
            x["dat_gio"], x.get("trong_hz", "—")))
    s += " · AUC %s · DRY %s%% RAMP %s%% DTR %s%%" % (p.get("auc", "—"), p.get("dry_pct", "—"), p.get("ramp_pct", "—"), p.get("dtr_pct") or "—")
    s += " · »DE %s (%s) »FCs %s (%s) »DROP %s (%s)" % (mm(p.get("du_bao_de")), lech(p.get("lech_de")), mm(p.get("du_bao_fcs")),
                                                       lech(p.get("lech_fcs")), mm(p.get("du_bao_drop")), lech(p.get("lech_drop")))
    ta, bta, nh, gi = chuoi_log(lg)
    if "FCs" in moc and moc["FCs"] <= t and lo is not None:
        R = H.ror30(ta, bta)
        w = (ta >= moc["FCs"]) & np.isfinite(R)
        if w.any():
            r = R[w]
            s += " · DEV RoR TB %.2f · %d %% trong %g–%g" % (r.mean(), 100 * np.mean((r >= lo) & (r <= hi)), lo, hi)
    if len(ta) > 40 and "TP" in moc:
        nhan, _ = nhan_ror(ta, bta, nh, gi, moc, lo, hi, t, da_bao, doc_dich(tm))
        s += " · " + nhan
    if mp:
        m = mp[-1]
        s += " · Hồng: Nhiệt %s→%s %% (BT %s so đường mồi %s, dự báo 60 s %s / 120 s %s, d̂ %s)" % (
            m["u_cu"], m["u_moi"], m["bt"], m["bt_ref"], m["bt_du_bao_60"], m["bt_du_bao_120"], m["d_hat"])
    return s


def doc_moc(tm):
    try:
        return json.load(open(os.path.join(tm, "moc.json"), encoding="utf-8"))["moc_giay"]
    except (OSError, ValueError, KeyError):
        return {}


def doc_dich(tm):
    """Đích DE / FCs / dev (giây) từ moc.json › dich (bộ quan sát ghi); thiếu thì dùng kế hoạch mẻ 9."""
    try:
        d = json.load(open(os.path.join(tm, "moc.json"), encoding="utf-8"))["dich"]
        return {"de": float(d["de"]), "fcs": float(d["fcs"]), "dev": float(d["dev"])}
    except (OSError, ValueError, KeyError, TypeError):
        return dict(H.DICH_ME9)


def chay_song(tm, lo, hi):
    da_bao = set()
    while True:
        time.sleep(CHU_KY)
        lg = rows(tm, "log.csv")
        if not lg or not lg[-1]["t_rang"]:
            continue
        moc = doc_moc(tm)
        try:
            s = dong(tm, lg, rows(tm, "phan_tich_3s.csv"), rows(tm, "mpc.csv"), moc, lo, hi, da_bao)
        except Exception as e:  # phân tích lỗi không được làm dừng dòng 15 s
            s = "PHÂN TÍCH 15s lỗi: %s" % e
        with open(os.path.join(tm, "trang_thai.txt"), "a", encoding="utf-8") as f:
            f.write(time.strftime("%H:%M:%S ") + s + "\n")
        if "DROP" in moc:
            return


def phat_lai(tm, lo, hi, dich=None):
    """Phát lại mẻ cũ mỗi 15 s giờ rang: chỉ dùng số tới thời điểm đó. Trả danh sách (giây phát hiện, lỗi)."""
    lg = rows(tm, "log.csv")
    moc = doc_moc(tm)
    ta, bta, nh, gi = chuoi_log(lg)
    da_bao, phat_hien = set(), []
    for now in np.arange(60, moc["DROP"] + 1, CHU_KY):
        m = {k: v for k, v in moc.items() if v <= now}
        k = ta <= now
        _, moi = nhan_ror(ta[k], bta[k], nh[k], gi[k], m, lo, hi, now, da_bao, dich or H.DICH_ME9)
        for l in moi:
            phat_hien.append((int(now), l))
    return phat_hien


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    a = sys.argv[1:]
    opt = {a[i][2:]: a[i + 1] for i in range(len(a)) if a[i].startswith("--")}
    tm = a[0]
    lo = float(opt["lo"]) if "lo" in opt else None
    hi = float(opt["hi"]) if "hi" in opt else None
    if opt.get("phat_lai") == "1":
        for now, l in phat_lai(tm, lo, hi):
            print("%s  phát hiện %s [%s] (lỗi từ %ds) %s ⇒ %s" % (mm(now), l["loai"], l["muc"], l["tu_s"], l["so_do"], H.VIEC_LAI[l["ma"]]))
    else:
        chay_song(tm, lo, hi)
