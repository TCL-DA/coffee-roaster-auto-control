# -*- coding: utf-8 -*-
"""BẢN SAO SỐ (digital twin) máy rang ĐIỆN VX4 — mô hình rời rạc 1 giây, học từ log 1 giây (agent OTL Hồng, 14/10/2026).

CHỈ chạy trên file: không mở cổng COM, không đụng Artisan / panel.

    python ban_sao_so_may_dien.py hoc  <log1.csv> [log2.csv …] [--hoc-den HH:MM:SS] [--kiem-tu HH:MM:SS]
    python ban_sao_so_may_dien.py kiem <log1.csv> [log2.csv …] --kiem-tu HH:MM:SS [--den HH:MM:SS]

Cột log đọc được: gio, bt, et, [buong], gas|nhiet (= Nhiệt %), [flags_hex] (bit 0x02 = Lệnh nhiệt). Không có flags ⇒ coi Lệnh bật.
Tham số học xong ghi vào `ban_sao_so_may_dien.json` cạnh file này; class BanSaoSo tự đọc.

Mô hình (gió 85 %, trống 85 %, lồng TRỐNG — đổi gió / trống / có hạt thì phải học lại):
    SV   = 130 + 2,2·Nhiệt%  khi Lệnh nhiệt bật, = 0 khi tắt.
    Mở   = rampa sau khi bật Lệnh: kep((giây_bật − d0)/r, 0, 1)    (firmware cần ~3 s mới báo "có nhiệt")
    VX4  : u = Mở · kep(kp·(SV − buồng) + I, 0, 1);  I += ki·(SV − buồng), kẹp 0…1, về 0 khi Lệnh tắt
    H    (điện trở, trạng thái ẩn)  += aH·u − bH·(H − buồng)            ⇒ tắt nguồn buồng vẫn lên thêm ~10 s
    buồng += cB·(H − buồng) − dB·(buồng − 30) + eB·(W1 − buồng)
    ET   += kE·(aE·buồng + bE·W1 + cE − ET)                               (khí qua lồng: buồng + thành lồng)
    BT   += kT·(aT·ET + bT·W1 + cT − BT)                                  (đầu dò hạt trong lồng trống)
    W1   (vỏ lồng, ẩn) += g1·(buồng − W1) + g12·(W2 − W1) − l1·(W1 − 30)
    W2   (thân máy, ẩn, chậm hàng chục phút) += g21·(W1 − W2) − l2·(W2 − 30)
Bộ quan sát (dùng khi bám log): mỗi giây gán buồng/ET/BT = số đo; H, W1, W2 chỉnh theo sai số dự báo 1 bước (L*)."""
import csv
import json
import math
import os
import sys

import numpy as np

NOI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ban_sao_so_may_dien.json")
T_MOI_TRUONG = 30.0
KHOANG_DUT = 5          # mất số liệu > 5 s ⇒ cắt đoạn
GIU_CHAM_QUA_DUT = 600  # trạng thái chậm (W1, W2) mang qua chỗ đứt ≤ 10 phút
TEN = ["kp", "ki", "d0", "r", "aH", "bH", "cB", "dB", "eB", "kE", "aE", "bE", "cE", "kT", "aT", "bT", "cT",
       "g1", "g12", "l1", "g21", "l2", "LhB", "LbE", "LwT", "LwE", "Lw2"]
# (giá trị đầu, cận dưới, cận trên) — cận giữ mô hình có nghĩa vật lý
KHOI = {"kp": (0.05, 0.005, 1.0), "ki": (0.002, 0.0, 0.05), "d0": (0.5, -2.0, 6.0), "r": (3.0, 0.5, 40.0),
        "aH": (8.0, 0.5, 60.0), "bH": (0.15, 0.01, 1.0), "cB": (0.3, 0.02, 1.0), "dB": (0.006, 0.0, 0.05),
        "eB": (0.005, 0.0, 0.05), "kE": (0.2, 0.02, 1.0), "aE": (0.3, 0.0, 1.0), "bE": (0.7, 0.0, 1.2),
        "cE": (0.0, -80.0, 80.0), "kT": (0.1, 0.01, 1.0), "aT": (0.6, 0.0, 1.2), "bT": (0.4, 0.0, 1.2),
        "cT": (0.0, -80.0, 80.0), "g1": (0.005, 0.0, 0.1), "g12": (0.002, 0.0, 0.05), "l1": (0.001, 0.0, 0.02),
        "g21": (0.0005, 0.0, 0.02), "l2": (0.0002, 0.0, 0.005), "LhB": (0.5, 0.0, 3.0), "LbE": (0.3, 0.0, 2.0),
        "LwT": (0.5, 0.0, 3.0), "LwE": (0.1, 0.0, 2.0), "Lw2": (0.02, 0.0, 1.0)}
# cột trạng thái
H, B, E, T, W1, W2, I, G = range(8)


def _kep(x, lo, hi):
    return np.minimum(np.maximum(x, lo), hi)


def _kep_so(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


def _cong_thuc(p, h, b, et, bt, w1, w2, i, g, nhiet, lenh, kep):
    """Phương trình mô hình — MỘT chỗ duy nhất; chạy được cho số đơn (bộ quan sát) và mảng (dự báo theo lô)."""
    sv = (130.0 + 2.2 * nhiet) * lenh
    g = (g + 1.0) * lenh
    mo = kep((g - p["d0"]) / p["r"], 0.0, 1.0)
    e = sv - b
    i = kep(i + p["ki"] * e, 0.0, 1.0) * lenh
    u = mo * kep(p["kp"] * e + i, 0.0, 1.0)
    return (h + p["aH"] * u - p["bH"] * (h - b),
            b + p["cB"] * (h - b) - p["dB"] * (b - T_MOI_TRUONG) + p["eB"] * (w1 - b),
            et + p["kE"] * (p["aE"] * b + p["bE"] * w1 + p["cE"] - et),
            bt + p["kT"] * (p["aT"] * et + p["bT"] * w1 + p["cT"] - bt),
            w1 + p["g1"] * (b - w1) + p["g12"] * (w2 - w1) - p["l1"] * (w1 - T_MOI_TRUONG),
            w2 + p["g21"] * (w1 - w2) - p["l2"] * (w2 - T_MOI_TRUONG),
            i, g)


def buoc(p, x, nhiet, lenh):
    """Một giây mô hình. x: mảng (…, 8). nhiet, lenh: số hoặc mảng cùng cỡ lô. Trả x mới (không sửa x cũ)."""
    if x.ndim == 1:
        return np.array(_cong_thuc(p, *map(float, x), float(nhiet), float(lenh), _kep_so))
    y = _cong_thuc(p, *(x[..., k] for k in range(8)), np.asarray(nhiet, float), np.asarray(lenh, float), _kep)
    return np.stack(y, axis=-1)


# ---------------------------------------------------------------- dữ liệu
def _giay(s):
    h, m, x = (int(v) for v in s.split(":"))
    return h * 3600 + m * 60 + x


def _so(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return math.nan


def nap_log(duong_dan):
    """Gộp nhiều log 1 giây ⇒ dict mảng (t, bt, et, buong, nhiet, lenh, doan). Trùng giây: giữ dòng của file sau.
    Lỗ 2…5 s: nội suy BT/ET/buồng, giữ lệnh cũ. Lỗ > 5 s: sang đoạn mới (doan += 1)."""
    dong = {}
    for f in duong_dan:
        with open(f, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                try:
                    t = _giay(r["gio"])
                    bt, et = float(r["bt"]), float(r["et"])
                except (KeyError, ValueError, AttributeError):
                    continue
                n = _so(r.get("gas", r.get("nhiet")))
                fl = r.get("flags_hex")
                lenh = ((int(fl, 16) >> 1) & 1) if fl else 1
                dong[t] = (t, bt, et, _so(r.get("buong")), 0.0 if math.isnan(n) else n, lenh)
    ts = sorted(dong)
    out = {k: [] for k in ("t", "bt", "et", "buong", "nhiet", "lenh", "doan", "noi_suy")}
    doan = 0
    for j, t in enumerate(ts):
        if j and t - ts[j - 1] > KHOANG_DUT:
            doan += 1
        elif j and t - ts[j - 1] > 1:  # lấp lỗ ngắn
            a, b = dong[ts[j - 1]], dong[t]
            for tt in range(ts[j - 1] + 1, t):
                w = (tt - a[0]) / (b[0] - a[0])
                v = [a[k] + w * (b[k] - a[k]) for k in (1, 2, 3)]
                for k, val in zip(("t", "bt", "et", "buong", "nhiet", "lenh", "doan", "noi_suy"),
                                  (tt, *v, a[4], a[5], doan, 1)):
                    out[k].append(val)
        for k, val in zip(("t", "bt", "et", "buong", "nhiet", "lenh", "doan", "noi_suy"), (*dong[t], doan, 0)):
            out[k].append(val)
    return {k: np.array(v, dtype=float) for k, v in out.items()}


def tom_tat_doan(d):
    """Liệt kê các đoạn liền: (giờ đầu, giờ cuối, số giây, có buồng?)."""
    kq = []
    for s in np.unique(d["doan"]):
        m = d["doan"] == s
        t = d["t"][m]
        kq.append((_hms(t[0]), _hms(t[-1]), int(m.sum()), bool(np.isfinite(d["buong"][m]).mean() > 0.9)))
    return kq


def _hms(t):
    t = int(t)
    return "%02d:%02d:%02d" % (t // 3600, t % 3600 // 60, t % 60)


# ---------------------------------------------------------------- bộ quan sát + dự báo
def quan_sat(p, d):
    """Chạy mô hình bám log. Trả mảng trạng thái SAU khi gán số đo tại mỗi giây (dùng làm điểm xuất phát dự báo)."""
    n = len(d["t"])
    X = np.zeros((n, 8))
    x = None
    t_truoc = None
    tt, bb, ee, TT, nn, ll, dd = (d[k].tolist() for k in ("t", "buong", "et", "bt", "nhiet", "lenh", "doan"))
    for k in range(n):
        bm, em, tm = bb[k], ee[k], TT[k]
        co_b = bm == bm  # không phải NaN
        if x is None or dd[k] != dd[k - 1]:
            b0 = bm if co_b else (130 + 2.2 * nn[k] if ll[k] else em)
            cham = (x[W1], x[W2]) if (x is not None and tt[k] - t_truoc <= GIU_CHAM_QUA_DUT) else (tm, tm)
            x = [b0, b0, em, tm, cham[0], cham[1], 0.0, 0.0]
        else:
            x = list(_cong_thuc(p, *x, nn[k - 1], ll[k - 1], _kep_so))
            eT, eE = tm - x[T], em - x[E]
            if co_b:
                x[H] += p["LhB"] * (bm - x[B])
                x[B] = bm
            else:
                x[B] += p["LbE"] * eE
            x[E], x[T] = em, tm
            x[W1] += p["LwT"] * eT + p["LwE"] * eE
            x[W2] += p["Lw2"] * eT
        X[k] = x
        t_truoc = tt[k]
    return X


def du_bao(p, d, X, diem, tam=60):
    """Dự báo vòng hở từ các điểm `diem` (chỉ số), biết trước Nhiệt % / Lệnh tương lai. Trả mảng (len(diem), tam+1, 8)."""
    x = X[diem].copy()
    kq = [x]
    for j in range(tam):
        x = buoc(p, x, d["nhiet"][diem + j], d["lenh"][diem + j])
        kq.append(x)
    return np.stack(kq, axis=1)


def diem_hop_le(d, tu, den, tam=60, buoc_nhay=1, can_buong=True):
    """Chỉ số k (bắt đầu ≥ tu, kết thúc k+tam < den) mà k..k+tam cùng đoạn (không lỗ) và (nếu cần) có buồng."""
    t = d["t"]
    n = len(t)
    k = np.arange(n - tam)
    ok = (t[k] >= tu) & (t[k + tam] < den) & (d["doan"][k] == d["doan"][k + tam])
    if can_buong:
        ok &= np.isfinite(d["buong"][k])
    return k[ok][::buoc_nhay]


def sai_so(p, d, diem, tam_list=(15, 30, 60)):
    X = quan_sat(p, d)
    Y = du_bao(p, d, X, diem, max(tam_list))
    kq = {}
    for h in tam_list:
        e = Y[:, h, T] - d["bt"][diem + h]
        kq[h] = (float(np.mean(np.abs(e))), float(np.max(np.abs(e))), float(np.mean(e)))
    return kq


# ---------------------------------------------------------------- học tham số
def _p(v):
    return dict(zip(TEN, v))


def hoc(d, diem, p0=None, in_tien_trinh=True):
    """Bình phương tối thiểu trên sai số dự báo nhiều tầm (BT 5/15/30/60 s, ET 15/30, buồng 5/15)."""
    from scipy.optimize import least_squares
    lo = np.array([KHOI[k][1] for k in TEN])
    hi = np.array([KHOI[k][2] for k in TEN])
    v0 = np.array([(p0 or {}).get(k, KHOI[k][0]) for k in TEN])
    v0 = np.clip(v0, lo + 1e-9, hi - 1e-9)
    co_buong = np.isfinite(d["buong"])

    def r(v):
        p = _p(v)
        X = quan_sat(p, d)
        Y = du_bao(p, d, X, diem, 60)
        res = []
        for h, w in ((5, 0.5), (15, 1.0), (30, 1.0), (60, 1.0)):
            res.append(w * (Y[:, h, T] - d["bt"][diem + h]))
        for h, w in ((15, 0.4), (30, 0.4)):
            res.append(w * (Y[:, h, E] - d["et"][diem + h]))
        for h, w in ((5, 0.2), (15, 0.2)):
            m = co_buong[diem + h]
            res.append(w * np.where(m, Y[:, h, B] - np.nan_to_num(d["buong"][diem + h]), 0.0))
        out = np.concatenate(res)
        return np.nan_to_num(out, nan=1e3, posinf=1e3, neginf=-1e3)

    kq = least_squares(r, v0, bounds=(lo, hi), x_scale="jac", max_nfev=400, verbose=2 if in_tien_trinh else 0)
    return _p(kq.x), float(np.sqrt(np.mean(kq.fun ** 2)))


def luu(p, them=None):
    with open(NOI, "w", encoding="utf-8") as f:
        json.dump({"tham_so": p, **(them or {})}, f, ensure_ascii=False, indent=1)


def doc_tham_so(duong=NOI):
    with open(duong, encoding="utf-8") as f:
        return json.load(f)["tham_so"]


# ---------------------------------------------------------------- class mô phỏng
class BanSaoSo:
    """Máy ảo 1 giây. step(nhiet_pct, lenh_nhiet) -> (bt, et, buong).
    Khởi tạo theo số đo hiện tại; nếu biết máy đã ngấm thì truyền w1/w2 (mặc định = BT: máy ngấm đều)."""

    def __init__(self, bt, et, buong=None, w1=None, w2=None, p=None, nhieu=0.0, seed=None):
        self.p = dict(p or doc_tham_so())
        b = et if buong is None else buong
        self.x = np.array([b, b, et, bt, bt if w1 is None else w1, bt if w2 is None else w2, 0.0, 0.0])
        self.nhieu = nhieu
        self.rng = np.random.default_rng(seed)

    @classmethod
    def tu_log(cls, d, p=None, k=-1, **kw):
        """Dựng máy ảo từ trạng thái quan sát được tại chỉ số k của log (đủ cả trạng thái ẩn)."""
        p = dict(p or doc_tham_so())
        X = quan_sat(p, d)
        m = cls(d["bt"][k], d["et"][k], p=p, **kw)
        m.x = X[k].copy()
        return m

    def step(self, nhiet_pct, lenh_nhiet):
        self.x = buoc(self.p, self.x, float(_kep(nhiet_pct, 0, 100)), 1.0 if lenh_nhiet else 0.0)
        do = self.x[[T, E, B]].copy()
        if self.nhieu:
            do += self.rng.normal(0, self.nhieu, 3)
        return tuple(round(float(v), 1) for v in do)

    def an(self):
        """Trạng thái ẩn để soi: điện trở H, vỏ lồng W1, thân máy W2, tích phân VX4."""
        return {"H": self.x[H], "W1": self.x[W1], "W2": self.x[W2], "I_vx4": self.x[I]}


def hoc_lai(duong_log, hoc_den=None, p0=None):
    """Học lại từ log mới (gộp với log cũ nếu truyền cả). Trả (tham số, sai số dự báo trên chính dữ liệu học)."""
    d = nap_log(duong_log)
    den = _giay(hoc_den) if hoc_den else d["t"][-1] + 1
    diem = diem_hop_le(d, d["t"][0], den, buoc_nhay=3)
    p, rms = hoc(d, diem, p0=p0 or (doc_tham_so() if os.path.exists(NOI) else None))
    return p, rms


# ---------------------------------------------------------------- dòng lệnh
def _tach(argv):
    log, opt = [], {}
    i = 0
    while i < len(argv):
        if argv[i].startswith("--"):
            opt[argv[i][2:]] = argv[i + 1]
            i += 2
        else:
            log.append(argv[i])
            i += 1
    return log, opt


def main():
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    if len(sys.argv) < 3 or sys.argv[1] not in ("hoc", "kiem"):
        print(__doc__)
        return
    log, opt = _tach(sys.argv[2:])
    d = nap_log(log)
    for a, b, n, cb in tom_tat_doan(d):
        print("đoạn %s–%s  %5d s  %s" % (a, b, n, "CÓ buồng" if cb else "không buồng"))
    if sys.argv[1] == "hoc":
        den = _giay(opt["hoc-den"]) if "hoc-den" in opt else d["t"][-1] + 1
        tu = _giay(opt["hoc-tu"]) if "hoc-tu" in opt else d["t"][0]
        diem = diem_hop_le(d, tu, den, buoc_nhay=3)
        p0 = doc_tham_so() if os.path.exists(NOI) else None
        p, rms = hoc(d, diem, p0=p0)
        them = {"hoc_tu": _hms(tu), "hoc_den": _hms(den), "rms_hoc": rms, "log": [os.path.basename(os.path.dirname(x))
                                                                                  or x for x in log]}
        if "kiem-tu" in opt:
            dk = diem_hop_le(d, _giay(opt["kiem-tu"]), _giay(opt.get("den", "23:59:59")))
            them["kiem"] = {str(k): v for k, v in sai_so(p, d, dk).items()}
        luu(p, them)
        print(json.dumps(them, ensure_ascii=False))
    else:
        p = doc_tham_so()
        dk = diem_hop_le(d, _giay(opt["kiem-tu"]), _giay(opt.get("den", "23:59:59")))
        for h, (mae, mx, tb) in sai_so(p, d, dk).items():
            print("BT +%2d s: MAE %.2f °C · max %.2f · lệch TB %+.2f  (%d điểm)" % (h, mae, mx, tb, len(dk)))


if __name__ == "__main__":
    main()
