"""OTL Hồng LÁI một mẻ có hạt bằng MPC trên mô hình học từ mẻ mồi (16/10/2026, mẻ 5).

Mô hình (học từ log.csv mẻ mồi, 1 Hz):
    buồng' = α_up·(SV − buồng) (kẹp ≤ ρ) nếu SV > buồng, ngược lại α_dn·(SV − buồng)        SV = 160 + 2,1·Nhiệt%
    RoR_BT  = a·(buồng − BT) + b·BT + c + d̂                                                   (°C/phút; d̂ = nhiễu ước lượng)
d̂ cập nhật trong bộ quan sát (lọc mũ sai lệch RoR đo − RoR mô hình) — không phải khâu I của bộ lái.
MPC: mỗi 5 s, thử mọi Nhiệt % hằng trên chân trời 120 s, chọn J = Σ(BT − BT_ref)² + λ(Δu)² (+ RoR sau FCs về đích);
áp bước đầu, làm lại. 0–85 s sau charge: phát lại thao tác mẻ mồi (feed-forward, mô hình không đúng lúc hạt vừa vào).
Gió / trống: theo lịch mẻ mồi (feed-forward) — chưa có dữ liệu nhận dạng ảnh hưởng gió khi có hạt.
DROP: BT ≥ ngưỡng ⇒ $7 = 1, đọc lại, bấm DROP Artisan (UIA). An toàn: BT > 245 / ET > 255 ⇒ Lệnh nhiệt 0 + xả.
Chạy: HONG_DUOC_LAI=1 python tools/hong_lai_me_mpc.py <thư mục mẻ> <log mẻ mồi> [--drop 217 --fcs 660 --ror_dev 6]
"""
import csv
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hong_qua_panel import Panel  # noqa: E402

import numpy as np  # noqa: E402

SV = lambda u: 160 + 2.1 * u  # noqa: E731
U_MAX = 90


def s16(v):
    return v - 65536 if v >= 32768 else v


def doc_moi(duong):
    r = list(csv.DictReader(open(duong, encoding="utf-8")))
    out = []
    for x in r:
        try:
            t = float(x["t_rang"])
        except (ValueError, TypeError):
            continue
        out.append((t, float(x["bt"]), float(x["et"]), float(x["buong"]), float(x["ror_bt"] or "nan"),
                    float(x["dat_nhiet"]), float(x["dat_gio"]), float(x["dat_trong"])))
    a = np.array(out)
    # bỏ phần sau DROP (t_rang đứng yên)
    k = int(np.argmax(a[:, 0])) + 1
    return a[:k]


def hoc(a):
    t, bt, bu, ror, u = a[:, 0], a[:, 1], a[:, 3], a[:, 4], a[:, 5]
    m = (t >= 100) & np.isfinite(ror)
    X = np.c_[bu[m] - bt[m], np.ones(m.sum())]
    coef, *_ = np.linalg.lstsq(X, ror[m], rcond=None)
    coef = [coef[0], 0.0, coef[1]]
    X = np.c_[X[:, 0], np.zeros(m.sum()), X[:, 1]]
    res = ror[m] - X @ coef
    # buồng
    sv = SV(u[:-1])
    db = np.diff(bu)
    gap = sv - bu[:-1]
    up = (gap > 3) & (t[:-1] >= 60)
    dn = (gap < -3) & (t[:-1] >= 60)
    a_up = float(np.sum(db[up] * gap[up]) / np.sum(gap[up] ** 2)) if up.sum() > 5 else 0.01
    a_dn = float(np.sum(db[dn] * gap[dn]) / np.sum(gap[dn] ** 2)) if dn.sum() > 3 else 0.08
    rho = float(np.percentile(db[up], 98)) if up.sum() > 5 else 1.2
    return {"a": float(coef[0]), "b": float(coef[1]), "c": float(coef[2]), "rmse_ror": float(np.sqrt(np.mean(res ** 2))),
            "a_up": a_up, "a_dn": max(a_dn, 0.03), "rho": max(rho, 0.3)}


def mo_phong(p, bt, bu, u, d, H):
    """Trả BT[1..H], RoR[1..H] với Nhiệt u hằng."""
    sv = SV(u)
    bts, rors = np.empty(H), np.empty(H)
    for i in range(H):
        g = sv - bu
        bu += min(p["a_up"] * g, p["rho"]) if g > 0 else p["a_dn"] * g
        r = p["a"] * (bu - bt) + p["b"] * bt + p["c"] + d * math.exp(-i / 90.0)
        bt += r / 60.0
        bts[i], rors[i] = bt, r
    return bts, rors


class LaiMe:
    def __init__(self, tm, moi, drop=217.0, fcs=660.0, ror_dev=6.0):
        self.tm, self.drop_bt, self.fcs_t, self.ror_dev = tm, drop, fcs, ror_dev
        self.a = doc_moi(moi)
        self.p = hoc(self.a)
        self.pn = Panel()
        self.d = 0.0
        self.lich = []
        self.u = None
        self.t_fcs_that = None
        self.f_mpc = open(os.path.join(tm, "mpc.csv"), "a", encoding="utf-8", newline="")
        self.w_mpc = csv.writer(self.f_mpc)
        self.w_mpc.writerow(["gio", "t_rang", "bt", "buong", "ror_do", "ror_mh", "d_hat", "bt_ref", "u_cu", "u_moi",
                             "gio_dat", "bt_du_bao_60", "bt_du_bao_120", "J"])
        self.ghi("Hồng LÁI (MPC) sẵn sàng · mô hình học từ mẻ mồi: RoR = %.4f·(buồng−BT) %+.4f·BT %+.2f (rmse %.2f °C/ph) · "
                 "buồng α↑ %.4f/s ρ %.2f °C/s α↓ %.3f/s" % (self.p["a"], self.p["b"], self.p["c"], self.p["rmse_ror"],
                                                          self.p["a_up"], self.p["rho"], self.p["a_dn"]))

    # ── tiện ích ─────────────────────────────────────────────────────────────
    def ghi(self, s):
        dong = "%s %s" % (time.strftime("%H:%M:%S"), s)
        print(dong, flush=True)
        with open(os.path.join(self.tm, "trang_thai.txt"), "a", encoding="utf-8") as f:
            f.write(dong + "\n")

    def doc(self):
        r = self.pn.doc(0, 100)
        return r, s16(r[60]) / 10, s16(r[61]) / 10, s16(r[96]) / 10

    def ror(self, giay=20):
        now = self.lich[-1][0]
        x = [(t, b) for t, b in self.lich if now - t <= giay]
        if len(x) < 8:
            return float("nan")
        t, b = np.array(x).T
        return float(np.polyfit(t - t[-1], b, 1)[0] * 60)

    def bt_ref(self, t):
        a = self.a
        if t <= self.fcs_t:
            return float(np.interp(t, a[:, 0], a[:, 1]))
        b0 = float(np.interp(self.fcs_t, a[:, 0], a[:, 1]))
        return b0 + self.ror_dev * (t - self.fcs_t) / 60.0

    def ff(self, t, cot):
        a = self.a
        i = int(np.searchsorted(a[:, 0], t, side="right")) - 1
        return float(a[max(i, 0), cot])

    def dat(self, u=None, gio=None, trong=None):
        if u is not None:
            u = int(max(0, min(U_MAX, round(u))))
            self.pn.dat_nhiet(u)
            v = self.pn.doc(2036, 1)[0]
            if v != u:
                self.ghi("⛔ ghi Nhiệt %d, đọc lại %d" % (u, v))
            self.u = u
        if gio is not None:
            self.pn.dat_gio(gio)
        if trong is not None:
            self.pn.dat_trong(trong)

    def an_toan(self, ly_do):
        self.ghi("⛔ AN TOÀN: %s ⇒ Lệnh nhiệt 0" % ly_do)
        for _ in range(3):
            try:
                self.pn.lenh_nhiet(0)
                if self.pn.doc(1, 1)[0] == 0:
                    break
            except Exception:
                time.sleep(0.3)

    # ── MPC ──────────────────────────────────────────────────────────────────
    def mpc(self, t, bt, bu, ror_do):
        p, H = self.p, 120
        ror_mh = p["a"] * (bu - bt) + p["b"] * bt + p["c"]
        if math.isfinite(ror_do):
            self.d += 0.15 * ((ror_do - ror_mh) - self.d)        # bộ quan sát nhiễu
        sau_fcs = bt >= 194.0 or t > self.fcs_t
        u0 = self.u if self.u is not None else 80
        best = None
        uff = self.ff(t, 5)
        for u in range(int(max(0, uff - 20)), int(min(U_MAX, uff + 10)) + 1):
            bts, rors = mo_phong(p, bt, bu, u, self.d, H)
            tt = t + np.arange(1, H + 1)
            ref = np.array([self.bt_ref(x) for x in tt])
            w = np.where(np.arange(1, H + 1) >= 15, 1.0, 0.0)
            J = float(np.sum(w * (bts - ref) ** 2)) / H
            if sau_fcs or t > self.fcs_t - 60:
                m = (tt >= max(self.fcs_t, t))
                if m.any():
                    J += 0.6 * float(np.mean((rors[m] - self.ror_dev) ** 2))
            J += 0.004 * (u - u0) ** 2 + 0.01 * (u - uff) ** 2
            if best is None or J < best[0]:
                best = (J, u, bts[59], bts[-1])
        J, u, b60, b120 = best
        gio = self.ff(t, 6)
        self.w_mpc.writerow([time.strftime("%H:%M:%S"), round(t), bt, bu, round(ror_do, 2), round(ror_mh, 2),
                             round(self.d, 2), round(self.bt_ref(t), 1), u0, u, gio, round(b60, 1), round(b120, 1),
                             round(J, 3)])
        self.f_mpc.flush()
        if u != u0:
            self.ghi("MPC %d:%02d · BT %.1f (đích %.1f) · RoR %.1f · d̂ %+.1f ⇒ Nhiệt %d→%d %% · dự báo BT 60 s %.1f · 120 s %.1f" % (
                t // 60, t % 60, bt, self.bt_ref(t), ror_do, self.d, u0, u, b60, b120))
        self.dat(u=u, gio=gio)

    # ── vòng chính ──────────────────────────────────────────────────────────
    def chay(self):
        t_charge = float(os.environ.get("HONG_T_CHARGE", "nan"))
        t_charge = None if math.isnan(t_charge) else t_charge
        t_mpc = 0
        moc_ff = [(0, 80), (14, 70), (16, 55), (18, 40), (19, 30), (20, 20)]   # mẻ mồi 0:00–0:20
        ff_i = 0
        dropped = False
        t_bat = time.time()
        while True:
            try:
                r, bt, et, bu = self.doc()
            except Exception as e:
                self.ghi("⚠ đọc panel lỗi: %s" % e)
                time.sleep(0.5)
                continue
            now = time.time()
            self.lich.append((now, bt))
            self.lich = self.lich[-120:]
            if bt > 245 or et > 255:
                self.an_toan("BT %.1f / ET %.1f vượt 245/255" % (bt, et))
                self.xa(bt)
                return
            if t_charge is None:
                ds = [b for tt, b in self.lich if now - tt <= 30]
                if r[81] > 0 or (max(ds) - bt >= 25 and max(ds) > 120):
                    t_charge = now - (r[67] * 60 + r[68])
                    self.ghi("Hồng LÁI: CHARGE thấy lúc BT %.1f · bắt đầu phát lại feed-forward 0–85 s rồi MPC" % bt)
                    self.bam_artisan("CHARGE")
                elif now - t_bat > 900:
                    self.ghi("⛔ 15 phút chưa CHARGE — bộ lái thoát (firmware giữ chương trình)")
                    return
                time.sleep(0.5)
                continue
            t = r[67] * 60 + r[68] if (r[67] or r[68]) else now - t_charge
            if t < 85:
                while ff_i < len(moc_ff) and t >= moc_ff[ff_i][0]:
                    self.dat(u=moc_ff[ff_i][1])
                    self.ghi("FF %d s · Nhiệt %d %% (phát lại mẻ mồi)" % (t, moc_ff[ff_i][1]))
                    ff_i += 1
                g = self.ff(t, 6)
                if g != getattr(self, "_g", None):
                    self.dat(gio=g)
                    self._g = g
            elif now - t_mpc >= 5:
                t_mpc = now
                try:
                    self.mpc(t, bt, bu, self.ror())
                except Exception as e:
                    self.ghi("⚠ MPC lỗi: %s (giữ Nhiệt %s)" % (e, self.u))
            if self.t_fcs_that is None and bt >= 194.0:
                self.t_fcs_that = t
            # DROP
            ror_s = self.ror(10) / 60 if len(self.lich) > 10 else 0.1
            if not dropped and bt >= self.drop_bt - max(0.0, ror_s) * 0.3:
                self.xa(bt, t)
                dropped = True
                return
            if t > 1080:
                self.ghi("⛔ 18:00 chưa tới BT %.1f — xả an toàn ở BT %.1f" % (self.drop_bt, bt))
                self.xa(bt, t)
                return
            time.sleep(0.25 if bt > self.drop_bt - 3 else 0.5)

    def xa(self, bt, t=0):
        self.pn.ghi(7, [1])
        v = self.pn.doc(7, 1)[0]
        r = self.pn.doc(0, 100)
        self.ghi("Hồng DROP: $7=1 (đọc lại %d) ở BT %.1f · %d:%02d · mã %d" % (v, bt, t // 60, t % 60, r[40]))
        self.bam_artisan("DROP")

    def bam_artisan(self, nut):
        try:
            import artisan_ui
            w = artisan_ui._cua_so(3)
            artisan_ui._bam(w, nut)
            self.ghi("Artisan: bấm %s (UIA Invoke)" % nut)
        except Exception as e:
            self.ghi("⚠ Artisan %s lỗi: %s" % (nut, e))


def main():
    if os.environ.get("HONG_DUOC_LAI") != "1":
        sys.exit("cần HONG_DUOC_LAI=1")
    sys.stdout.reconfigure(encoding="utf-8")
    a = sys.argv[1:]
    kw = {}
    for k in ("--drop", "--fcs", "--ror_dev"):
        if k in a:
            i = a.index(k)
            kw[k[2:]] = float(a[i + 1])
            del a[i:i + 2]
    if a[0] == "hoc":
        print(json.dumps(hoc(doc_moi(a[1])), indent=1))
        return
    LaiMe(a[0], a[1], **kw).chay()


if __name__ == "__main__":
    main()
