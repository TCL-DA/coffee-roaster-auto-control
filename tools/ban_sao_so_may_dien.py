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
Bộ quan sát (dùng khi bám log): mỗi giây gán buồng/ET/BT = số đo; H, W1, W2 chỉnh theo sai số dự báo 1 bước (L*).

15/10/2026 — bổ sung cho bộ giải đề (`hong_qua_panel.py`):
    trang_thai_tu_do()  ước trạng thái ẩn từ MỘT mẫu đo (bộ giải vừa nối panel, chưa có lịch sử)
    buoc_quan_sat()     bộ quan sát 1 bước, chạy cho 1 hoặc K mô hình cùng lúc (xep_tham_so)
    doi_do_nhay()       đổi độ nhạy cân bằng °C/% (0,76 bảng giữ thật … 0,94 khớp log)
    lech_tham_so()      bộ tham số lệch ngẫu nhiên cho Monte Carlo (động học ±12 %, VX4 ±25 %, offset ±2,5…3 °C)
    MayMoPhong          máy ảo có nhiễu, trễ đọc / trễ lệnh, RoR firmware giả (trễ 35 s, có lúc đảo dấu)
    kiem_dac_diem()     soát mô hình với đặc điểm đo thật (VX4 bám SV 10–15 s, mức giữ 200/210, lên chậm khi lồng nguội)"""
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
    """Phương trình mô hình — MỘT chỗ duy nhất; chạy được cho số đơn (bộ quan sát) và mảng (dự báo theo lô).
    Tham số có thể là số hoặc mảng (K, 1) — bộ giải dùng K mô hình cùng lúc (MPC nhiều mô hình)."""
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


def hoc(d, diem, p0=None, in_tien_trinh=True, tam_dai=()):
    """Bình phương tối thiểu trên sai số dự báo nhiều tầm (BT 5/15/30/60 s, ET 15/30, buồng 5/15).
    tam_dai = ((giây, trọng số), …) thêm tầm dài (vd 120/240 s) — ép độ nhạy cân bằng °C/% khớp máy thật (15/10)."""
    from scipy.optimize import least_squares
    lo = np.array([KHOI[k][1] for k in TEN])
    hi = np.array([KHOI[k][2] for k in TEN])
    v0 = np.array([(p0 or {}).get(k, KHOI[k][0]) for k in TEN])
    v0 = np.clip(v0, lo + 1e-9, hi - 1e-9)
    co_buong = np.isfinite(d["buong"])

    def r(v):
        p = _p(v)
        X = quan_sat(p, d)
        tam = max([60] + [h for h, _ in tam_dai])
        Y = du_bao(p, d, X, diem, tam)
        res = []
        for h, w in ((5, 0.5), (15, 1.0), (30, 1.0), (60, 1.0)) + tuple(tam_dai):
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


# ---------------------------------------------------------------- khởi tạo trạng thái từ MỘT lần đo
def trang_thai_tu_do(p, bt, et, buong, nhiet, lenh):
    """Ước trạng thái ẩn từ một mẫu đo khi máy gần đứng (dùng lúc bộ giải vừa nối, chưa có lịch sử).
    W1 suy từ phương trình ET (hệ số bE ≈ 1 ⇒ ít nhạy nhiễu); H, I suy từ cân bằng buồng; W2 ≈ W1."""
    b = et if buong is None or buong != buong else buong
    w1 = (et - p["aE"] * b - p["cE"]) / max(p["bE"], 1e-3)
    h = b + (p["dB"] * (b - T_MOI_TRUONG) - p["eB"] * (w1 - b)) / p["cB"]
    sv = (130.0 + 2.2 * nhiet) if lenh else 0.0
    u = _kep_so(p["bH"] * (h - b) / p["aH"], 0.0, 1.0)
    i = _kep_so(u - p["kp"] * (sv - b), 0.0, 1.0) if lenh else 0.0
    return np.array([h, b, et, bt, w1, w1, i, 600.0 if lenh else 0.0])


def buoc_quan_sat(p, x, u, bt, et, buong):
    """Một bước bộ quan sát (giống quan_sat): dự báo 1 s với lệnh u = (nhiệt %, lệnh) rồi gán số đo, chỉnh trạng thái ẩn.
    Chạy được cho x (8,) hoặc (K, 8) với p là tham số mảng (K, 1)."""
    y = buoc(p, x, u[0], u[1]) if x.ndim == 1 else _buoc_k(p, x, u)
    eT, eE = bt - y[..., T], et - y[..., E]
    if buong is not None and buong == buong:
        y[..., H] += _sq(p["LhB"]) * (buong - y[..., B])
        y[..., B] = buong
    else:
        y[..., B] += _sq(p["LbE"]) * eE
    y[..., E], y[..., T] = et, bt
    y[..., W1] += _sq(p["LwT"]) * eT + _sq(p["LwE"]) * eE
    y[..., W2] += _sq(p["Lw2"]) * eT
    return y


def _sq(v):
    return np.squeeze(v, -1) if isinstance(v, np.ndarray) else v


def _buoc_k(p, x, u):
    """x (K, 8), p mảng (K, 1): đưa về (K, 1, 8) để dùng chung buoc() theo lô."""
    return buoc(p, x[:, None, :], np.full((x.shape[0], 1), u[0]), np.full((x.shape[0], 1), u[1]))[:, 0, :]


def xep_tham_so(ds):
    """Gộp K bộ tham số thành dict mảng (K, 1) để mô phỏng K mô hình một lượt."""
    return {k: np.array([q[k] for q in ds], float)[:, None] for k in ds[0]}


# ---------------------------------------------------------------- MONTE CARLO: máy ảo lệch tham số + nhiễu + trễ
# Mức lệch chọn theo độ phân tán THẬT 14/10: cùng BT 200 °C nhưng mức giữ 37–45 % giữa các phiên (≈ ±3 °C BT tương đương
# ⇒ lệch offset cT ±2,5 / cE ±3); động học ±12 % (VX4 bám SV 10–15 s ⇒ aH, cB, r lệch ±25 %).
DONG_HOC = ("kp", "ki", "bH", "dB", "eB", "kE", "kT", "g1", "g12", "l1", "g21", "l2")
VX4_NHANH = ("aH", "cB", "r", "d0")


def doi_do_nhay(p, he_so):
    """Đổi độ nhạy cân bằng °C BT / % Nhiệt bằng tỉ lệ buồng→ET (aE), giữ tổng aE + bE.
    aE × 0,75 ⇒ 0,76 °C/% (bảng giữ thật 14/10: 200 → 37–41 %, 210 → 51–54 %); × 1,0 ⇒ 0,94 (khớp log tốt nhất); × 1,1 ⇒ 1,01."""
    q = dict(p)
    s = p["aE"] + p["bE"]
    q["aE"] = p["aE"] * he_so
    q["bE"] = s - q["aE"]
    return q


def lech_tham_so(p, rng, muc=0.12, muc_vx4=0.25, lech_cT=2.5, lech_cE=3.0, nhay=(0.75, 1.1)):
    q = doi_do_nhay(p, rng.uniform(*nhay))
    for k in DONG_HOC:
        q[k] = q[k] * rng.uniform(1 - muc, 1 + muc)
    for k in VX4_NHANH:
        q[k] = q[k] * rng.uniform(1 - muc_vx4, 1 + muc_vx4)
    s = q["aT"] + q["bT"]                               # giữ tổng hệ số (đúng ở cân bằng) — đổi tỉ lệ khí / thành lồng
    q["aT"] = q["aT"] * rng.uniform(1 - muc / 2, 1 + muc / 2)
    q["bT"] = s - q["aT"]
    q["cT"] = p["cT"] + rng.uniform(-lech_cT, lech_cT)
    q["cE"] = p["cE"] + rng.uniform(-lech_cE, lech_cE)
    return q


class MayMoPhong(BanSaoSo):
    """Máy ảo cho Monte Carlo: tham số lệch, nhiễu quá trình + nhiễu đo, trễ đọc (bản sao trên panel) và trễ lệnh
    (panel → board → VX4), RoR firmware giả lập (trễ 30–40 s, có lúc NGƯỢC DẤU — bộ giải KHÔNG được dùng)."""

    def __init__(self, x0, p, rng, tre_do=1, tre_lenh=1, nhieu_do=0.1, nhieu_qt=(0.3, 0.3, 0.05)):
        super().__init__(x0[T], x0[E], p=p)
        self.x = np.array(x0, float)
        self.rng, self.tre_do, self.tre_lenh = rng, int(tre_do), int(tre_lenh)
        self.nhieu_do, self.nhieu_qt = nhieu_do, nhieu_qt
        self.hang_lenh = [(0.0, 0.0)] * (self.tre_lenh + 1)
        self.hang_do = []
        self.ls_bt = []
        self.dao_dau = 0
        self.ror_fw = 0.0

    def dat(self, nhiet, lenh):
        """Lệnh mới — tới board sau `tre_lenh` giây."""
        self.hang_lenh[-1] = (float(_kep_so(nhiet, 0, 100)), 1.0 if lenh else 0.0)

    def tick(self):
        """Một giây máy thật. Trả số đo trên panel (đã trễ): (bt, et, buong)."""
        u = self.hang_lenh[0]
        self.hang_lenh = self.hang_lenh[1:] + [self.hang_lenh[-1]]
        self.x = buoc(self.p, self.x, *u)
        a, b, c = self.nhieu_qt
        self.x[E] += self.rng.normal(0, a)
        self.x[B] += self.rng.normal(0, b)
        self.x[T] += self.rng.normal(0, c)
        do = np.round(self.x[[T, E, B]] + self.rng.normal(0, self.nhieu_do, 3), 1)
        self.hang_do.append(do)
        self.ls_bt.append(self.x[T])
        self._ror_firmware()
        return tuple(self.hang_do[max(0, len(self.hang_do) - 1 - self.tre_do)])

    def bt_that(self):
        return float(self.x[T])

    def _ror_firmware(self):
        """Giống `ror_bt` firmware đo 14/10: độ dốc của đoạn 30 s kết thúc 35 s trước; thỉnh thoảng đảo dấu 5–10 s."""
        ls = self.ls_bt
        if len(ls) < 70:
            self.ror_fw = 0.0
            return
        doc = (ls[-36] - ls[-66]) * 2.0
        if self.dao_dau <= 0 and self.rng.random() < 0.01:
            self.dao_dau = int(self.rng.integers(5, 11))
        if self.dao_dau > 0:
            self.dao_dau -= 1
            doc = -doc
        self.ror_fw = round(doc, 1)


def kiem_dac_diem(p, x0):
    """Soát mô hình với đặc điểm ĐÃ ĐO của VX4: trả dict số để ghi vào giáo trình."""
    kq = {}
    # 1) VX4 bám SV: giữ 40 % tới đứng, nâng 50 % — đo giây tới khi buồng đạt 90 % bước SV
    x = np.array(x0, float)
    for _ in range(400):
        x = buoc(p, x, 40.0, 1.0)
    b0 = x[B]
    sv1 = 130 + 2.2 * 50
    for s in range(1, 120):
        x = buoc(p, x, 50.0, 1.0)
        if x[B] >= b0 + 0.9 * (sv1 - b0):
            kq["vx4_90pt_s"] = s
            break
    # 2) độ nhạy BT ở 200–210 °C: mức giữ sau 3 phút đứng (như cách đọc bảng cân bằng thật)
    def bt_sau(n, giay=180):
        y = np.array(x0, float)
        for _ in range(giay):
            y = buoc(p, y, n, 1.0)
        return y[T]
    gia = {n: bt_sau(n) for n in range(30, 61, 2)}
    tim = lambda T0: min(gia, key=lambda n: abs(gia[n] - T0))  # noqa: E731
    kq["giu_200_pct"], kq["giu_210_pct"] = tim(200), tim(210)
    kq["do_nhay_C_per_pct"] = round((gia[50] - gia[40]) / 10, 2)
    # 3) lên chậm khi thân lồng nguội: RoR 100 % trong 60 s, lồng ngấm vs nguội hơn 40 °C
    def ror_100(dw):
        y = np.array(x0, float)
        y[W1] -= dw
        y[W2] -= dw
        a = y[T]
        for _ in range(60):
            y = buoc(p, y, 100.0, 1.0)
        return y[T] - a
    kq["tang_60s_100pct_ngam"], kq["tang_60s_100pct_long_nguoi20"] = round(ror_100(0), 1), round(ror_100(20), 1)
    return kq


def trang_thai_ngam(duong=NOI):
    """Trạng thái máy ĐÃ NGẤM (đo lúc bắt đầu đề 14/10 20:18:57, BT 192,9) — điểm xuất phát Monte Carlo."""
    with open(duong, encoding="utf-8") as f:
        return np.array(json.load(f)["trang_thai_ngam"], float)


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
