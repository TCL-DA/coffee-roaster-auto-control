"""Mẻ 7: mỗi 15 s đọc log.csv / phan_tich_3s.csv / mpc.csv / moc.json (chỉ đọc file, không chạm panel) ⇒ 1 dòng trang_thai.txt."""
import csv, json, os, sys, time
import numpy as np
tm = sys.argv[1]; LO, HI = 5.0, 6.0
def rows(f):
    try: return list(csv.DictReader(open(os.path.join(tm, f), encoding="utf-8")))
    except Exception: return []
def mm(s):
    try: s = float(s); return "%s%d:%02d" % ("-" if s < 0 else "", abs(s) // 60, abs(s) % 60)
    except Exception: return "—"
def lech(s):
    try: return "%+ds" % float(s)
    except Exception: return "—"
def ghi(s):
    with open(os.path.join(tm, "trang_thai.txt"), "a", encoding="utf-8") as f: f.write(time.strftime("%H:%M:%S ") + s + "\n")
xong = False
while not xong:
    time.sleep(15)
    lg = rows("log.csv"); pt = rows("phan_tich_3s.csv"); mp = rows("mpc.csv")
    if not lg or not lg[-1]["t_rang"]: continue
    try: moc = json.load(open(os.path.join(tm, "moc.json"), encoding="utf-8"))["moc_giay"]
    except Exception: moc = {}
    x = lg[-1]; t = float(x["t_rang"]); bt, et, bu = float(x["bt"]), float(x["et"]), float(x["buong"])
    u = float(x["dat_nhiet"]); sv = 160 + 2.1 * u
    p = pt[-1] if pt else {}
    k = (float(x["ror_bt"]) / (et - bt)) if et - bt >= 8 and x["ror_bt"] not in ("", "nan") else float("nan")
    s = ("PHÂN TÍCH 15s %s · BT %.1f ET %.1f buồng %.1f · ET−BT %.1f · RoR %s · ΔET %s · K %s · Nhiệt %d %% (SV %d) · gió %s %% · trống %s Hz"
         % (mm(t), bt, et, bu, et - bt, x["ror_bt"][:5], p.get("det", "—"), ("%.3f" % k) if k == k else "—", u, sv, x["dat_gio"], x["trong_hz"]))
    s += " · AUC %s · DRY %s%% RAMP %s%% DTR %s%%" % (p.get("auc", "—"), p.get("dry_pct", "—"), p.get("ramp_pct", "—"), p.get("dtr_pct", "—") or "—")
    s += " · »DE %s (%s) »FCs %s (%s) »DROP %s (%s)" % (mm(p.get("du_bao_de")), lech(p.get("lech_de")), mm(p.get("du_bao_fcs")),
                                                       lech(p.get("lech_fcs")), mm(p.get("du_bao_drop")), lech(p.get("lech_drop")))
    if "FCs" in moc:
        a = np.array([(float(r["t_rang"]), float(r["ror_bt"])) for r in lg if r["t_rang"] and r["ror_bt"] not in ("", "nan")
                      and float(r["t_rang"]) >= moc["FCs"]])
        if len(a):
            r = a[:, 1]; s += " · DEV RoR TB %.2f · %d %% trong %g–%g (min %.1f max %.1f)" % (r.mean(), 100 * np.mean((r >= LO) & (r <= HI)), LO, HI, r.min(), r.max())
    if mp:
        m = mp[-1]; uc, um = float(m["u_cu"]), float(m["u_moi"])
        vi = "BT %s so đường mồi %s" % (m["bt"], m["bt_ref"])
        s += " · Hồng: Nhiệt %d→%d %% (%s, dự báo 60 s %s / 120 s %s, d̂ %s)" % (uc, um, vi, m["bt_du_bao_60"], m["bt_du_bao_120"], m["d_hat"])
        if t < 600 and float(m["bt"]) < 190: s += " · sắp: gió 85→90 lúc 10:00 / BT 190"
    elif t < 85: s += " · Hồng: phát lại FF 0–85 s mẻ mồi, MPC vào lúc 1:25"
    ghi(s)
    if "DROP" in moc: xong = True
