"""OTL Hồng — bộ lái mẻ 9 "lái thưa / buồng phẳng" (17/10/2026, Hồng + Claude). CHỈ MPC trên bản sao số, KHÔNG PID.

Căn cứ (skill rang-ca-phe): RoR giảm đều (cac-cach-rang 3.1, K8) · tránh chuỗi giảm–tăng do tín hiệu trễ (chien-luoc-rang
"Theo pha", K10) · VX4 dồn trước, quyết định giảm trước FCs 60–120 s (K14) · đừng giật SV VX4 (dieu-khien-nhiet, K13) ·
preheat ổn định / mẻ sau nhanh hơn (K16, K6). Số đo: bao_cao_1710 (mẻ 4 Nhiệt đứng ⇒ mượt nhất và đúng mốc).

Bản sao số (Claude 17/10, `bao_cao_1710/ban_sao.py`, kiểm DE→DROP mẻ 6/8 FCs lệch 1 / 17 s):
    buồng' = +1,6·(1 − e^(−g/35)) nếu g = SV − buồng ≥ 0, ngược lại −1,7·(1 − e^(g/18))      SV = 160 + 2,1·Nhiệt
    RoR    = k(BT)·(buồng − BT)·ĉ          k(BT) bảng học từ mẻ 4–8 (≈ 0,053–0,067 từ BT 160) · ĉ học chậm, kẹp 0,7–1,4
Lịch 7 bước:
    1 START ở BT 85–90 (kiểm trước khi bấm, không phải việc của lớp này)
    2 0–1:45 lịch mẻ 4: 80 % → 20 % (14–20 s) → giữ → dốc lên, ĐỨNG 77 %
    3 1:45–DE: Nhiệt đứng; mỗi 60 s MPC chọn ±0/1/2 % để DE dự báo = 6:30
    4 DE–FCs: mỗi 10 s MPC chọn Δ ∈ {−1, −0,5, 0, +0,5, +1} % bám RoR đích giảm thẳng về 6,0 lúc 11:00 (buồng phẳng)
    5 gió 85 → 90 lúc 10:00 (hoặc BT 190): bù trước −3 % một lần
    6 FCs−90 s → FCs: cấm tăng trừ khi RoR đo < 4,8 · sau FCs: RoR đích PHẲNG 5,5, giảm tự do, tăng ≤ +0,5 %/10 s
    7 an toàn: BT > 245 / ET > 255 ⇒ Lệnh 0 + xả; DROP ở BT 218; 18:00 chưa DROP ⇒ xả
Chạy máy (CHỈ khi anh cho):  HONG_DUOC_LAI=1 python tools/hong_lai_me9.py <thư mục mẻ>
Thử trên bản sao:            python tools/hong_lai_me9.py thu
"""
import json
import math
import os
import sys

import numpy as np

NOI = os.path.dirname(os.path.abspath(__file__))
MO_HINH = json.load(open(os.path.join(NOI, "ban_sao_me_k.json"), encoding="utf-8"))
DICH = dict(de=390, fcs=660, drop_t=922, bt_de=155.0, bt_fcs=194.0, bt_drop=218.0, ror_fcs=6.0, ror_dev=5.5)
LICH_DAU = [(0, 80), (14, 70), (16, 55), (18, 40), (19, 30), (20, 20), (87, 30), (89, 40), (92, 50), (96, 60), (100, 70), (105, 77)]
U_DUNG = 77
PHAT_DU = float(os.environ.get("HONG_PHAT_DU", "0.05"))
GIO_NEN, GIO_FCS, T_GIO, BT_GIO, BU_GIO = 85, 90, 600, 190.0, -3


# ⛔ Luật cứng anh Thành 17/10: KHÔNG BAO GIỜ CHARGE khi BT < 150 °C.
# Hai mốc khác nhau, không được lẫn:
#   BT_START  = BT lúc bấm START chương trình (lồng đã làm nguội, CHƯA có hạt) — kế hoạch 85–90 °C
#   BT_CHARGE = BT lúc firmware đổ hạt (tự CHARGE ở nhiệt charge $M23, thường 170) — bắt buộc ≥ 150 °C
BT_CHARGE_MIN = 150.0
BT_CHARGE_KE_HOACH = 170.0
BT_START_DAI = (85.0, 90.0)


def kiem_truoc_start(pn, ghi=print):
    """Đọc máy trước $0 = 1. Trả (được_chạy, lý_do). pn: hong_qua_panel.Panel."""
    def s16(v):
        return v - 65536 if v >= 32768 else v
    r = pn.doc(0, 100)
    bt_start = s16(r[60]) / 10
    nguong = pn.doc(2023, 1)[0] / 10                     # $M23 nhiệt charge ×10 — firmware tự CHARGE khi BT vào ngưỡng này
    if nguong < BT_CHARGE_MIN:
        ghi("⛔ Ngưỡng auto-charge $M23 = %.1f °C < %.0f — DỪNG, không START, báo anh" % (nguong, BT_CHARGE_MIN))
        return False, "ngưỡng charge %.1f < %.0f" % (nguong, BT_CHARGE_MIN)
    if abs(nguong - BT_CHARGE_KE_HOACH) > 0.5:
        ghi("⚠ Ngưỡng auto-charge $M23 = %.1f °C (kế hoạch %.0f) — báo anh trước khi START" % (nguong, BT_CHARGE_KE_HOACH))
        return False, "ngưỡng charge %.1f khác kế hoạch %.0f" % (nguong, BT_CHARGE_KE_HOACH)
    if not (BT_START_DAI[0] <= bt_start <= BT_START_DAI[1]):
        ghi("⚠ BT_START %.1f °C ngoài dải %.0f–%.0f (lồng chưa đúng trạng thái) — chưa START" % ((bt_start,) + BT_START_DAI))
        return False, "BT_START %.1f ngoài dải" % bt_start
    ghi("Kiểm trước START: BT_START %.1f °C (chưa có hạt) · ngưỡng auto-charge $M23 %.1f °C (≥ %.0f) — OK" % (bt_start, nguong, BT_CHARGE_MIN))
    return True, "ok"


def kiem_charge(bt_charge, ghi=print):
    """Gọi khi phát hiện CHARGE (hoặc ngay trước khi cho phép đổ hạt). BT < 150 ⇒ cấm cho vào hạt, nung tiếp, ghi cảnh báo."""
    if bt_charge < BT_CHARGE_MIN:
        ghi("⛔ CẤM CHARGE: BT_CHARGE %.1f °C < %.0f — KHÔNG cho vào hạt, nung tiếp tới ngưỡng máy (%.0f)" % (bt_charge, BT_CHARGE_MIN, BT_CHARGE_KE_HOACH))
        return False
    ghi("CHARGE: BT_CHARGE %.1f °C (≥ %.0f) — hợp lệ" % (bt_charge, BT_CHARGE_MIN))
    return True


def k_cua(bt, M=MO_HINH):
    if bt < 115:
        return 0.18
    return float(np.interp(bt, M["k_bt"], M["k_v"]))


def buoc_buong(b, sv):
    g = sv - b
    if g >= 0:
        return 1.6 * (1 - math.exp(-g / 35))
    return -1.7 * (1 - math.exp(g / 18))


def mo_phong(bt, b, n, giay, c=1.0, n_sau=None, t_doi=None):
    """Bản sao: giữ Nhiệt n (đổi sang n_sau ở giây t_doi nếu có). Trả mảng BT, RoR mỗi giây."""
    bts, rors = np.empty(giay), np.empty(giay)
    for i in range(giay):
        nn = n_sau if (t_doi is not None and i >= t_doi) else n
        r = k_cua(bt) * c * (b - bt)
        bt += r / 60
        b += buoc_buong(b, 160 + 2.1 * nn)
        bts[i], rors[i] = bt, r
    return bts, rors


class LaiMe9:
    """Không chạm panel: lenh(t, bt, buong, ror_do, gio_hien) -> (Nhiệt %, gió %, ghi_chú). Dùng chung cho máy thật và bản sao."""

    def __init__(self):
        self.u = 80.0
        self.c = 1.0
        self.t_cuoi = -999
        self.da_bu_gio = False
        self.gio = GIO_NEN

    def ror_dich(self, t, bt):
        if bt < DICH["bt_fcs"] and t < DICH["fcs"]:
            con = max(30, DICH["fcs"] - t)
            tb = (DICH["bt_fcs"] - bt) / con * 60
            return max(3.5, 2 * tb - DICH["ror_fcs"])          # RoR giảm thẳng, trung bình đủ để 194 đúng 11:00
        return DICH["ror_dev"]                                  # sau FCs: RoR đích PHẲNG 5,5 (giữa dải 5–6)

    def lenh(self, t, bt, b, ror_do):
        ghi = ""
        # 5. gió theo lịch + bù trước
        if not self.da_bu_gio and (t >= T_GIO or bt >= BT_GIO):
            self.gio, self.da_bu_gio = GIO_FCS, True
            self.u = max(0.0, self.u + BU_GIO)
            ghi = "gió 85→90, bù trước %d %% (k +6–8 %%)" % BU_GIO
            return self.u, self.gio, ghi
        # 2. đầu mẻ theo lịch mẻ 4
        if t < 105:
            for tt, uu in LICH_DAU:
                if t >= tt:
                    self.u = float(uu)
            return self.u, self.gio, ""
        # học ĉ chậm (bộ quan sát): RoR đo / RoR mô hình
        if math.isfinite(ror_do) and b - bt > 20 and bt >= 115:
            self.c += 0.02 * (ror_do / (k_cua(bt) * (b - bt)) - self.c)
            self.c = min(1.4, max(0.7, self.c))
        # 3. 1:45–DE: đứng, xét mỗi 60 s, ±2 %
        if bt < DICH["bt_de"]:
            if t - self.t_cuoi < 60:
                return self.u, self.gio, ""
            self.t_cuoi = t
            best = None
            for du in (-2, -1, 0, 1, 2):
                bts, _ = mo_phong(bt, b, self.u + du, 600, self.c)
                i = int(np.argmax(bts >= DICH["bt_de"])) if (bts >= DICH["bt_de"]).any() else 900
                J = ((t + i + 1) - DICH["de"]) ** 2 + 30 * du ** 2
                if best is None or J < best[0]:
                    best = (J, du, t + i + 1)
            self.u += best[1]
            return self.u, self.gio, "MPC DE: Nhiệt %+d %% ⇒ DE dự báo %d:%02d" % (best[1], best[2] // 60, best[2] % 60)
        # 4 + 6. DE → DROP: mỗi 10 s, |Δ| ≤ 1 %
        if t - self.t_cuoi < 10:
            return self.u, self.gio, ""
        self.t_cuoi = t
        best = None
        sau_fcs = bt >= DICH["bt_fcs"]
        for du in (-1.0, -0.5, 0.0, 0.5, 1.0):
            # 6. sau FCs: được giảm theo nhu cầu, TĂNG tối đa +0,5 %/10 s (k gần hằng mà BT +24 °C trong dev ⇒ buồng phải
            #    nhích theo BT thì RoR mới phẳng). FCs−90 s → FCs: cấm tăng trừ khi RoR đo < 4,8 (chặn RoR tăng lại trước FCs).
            if sau_fcs and du > 0.5:
                continue
            if (not sau_fcs) and du > 0 and t >= DICH["fcs"] - 90 and not (math.isfinite(ror_do) and ror_do < 4.8):
                continue
            # giữ du trong 120 s (trễ buồng→RoR 15–20 s ⇒ bỏ 20 s đầu); BT đích tịnh tiến theo RoR đích
            bts, rors = mo_phong(bt, b, self.u + du, 120, self.c)
            ref = np.array([self.ror_dich(t + i, bts[i]) for i in range(120)])
            J = float(np.mean((rors[20:] - ref[20:]) ** 2)) + PHAT_DU * du ** 2
            if best is None or J < best[0]:
                best = (J, du)
        self.u = float(np.clip(self.u + best[1], 0, 90))
        return self.u, self.gio, ("MPC RoR: Nhiệt %+.1f %% · RoR đích %.1f · ĉ %.2f" % (best[1], self.ror_dich(t, bt), self.c)) if best[1] else ""


# ───────────────────────── thử trên bản sao (không đụng máy) ─────────────────────────
def thu_ban_sao(me, he_k=1.0):
    """Chạy cả mẻ trên bản sao từ 90 s với trạng thái thật của mẻ `me` (4/5 = START nguội), máy 'thật' lệch k × he_k."""
    sys.path.insert(0, r"F:/Artisan/Profile/OTL-Hong/bao_cao_1710")
    import ban_sao as B
    L, moc = B.doc(me)
    by = {x["t"]: x for x in L}
    s = by[min(by, key=lambda k: abs(k - 90))]
    bt, b = s["bt"], s["b"]
    lai = LaiMe9()
    for tt in range(0, 90):
        lai.lenh(tt, bt, b, float("nan"))
    hist, out = [], []
    for t in range(90, 1080):
        hist.append(bt)
        ror_do = 60 * np.polyfit(np.arange(30), hist[-30:], 1)[0] if len(hist) >= 30 else float("nan")
        u, g, _ = lai.lenh(t, bt, b, ror_do)
        out.append((t, bt, b, u, g))
        if bt >= DICH["bt_drop"]:
            break
        r = k_cua(bt) * he_k * (b - bt)
        bt += r / 60
        b += buoc_buong(b, 160 + 2.1 * u)
    return np.array(out)


def danh_gia(o):
    sys.path.insert(0, NOI)
    import hong_ror_loi as H
    t, bt, u = o[:, 0], o[:, 1], o[:, 3]
    R = H.ror30(t, bt)
    tim = lambda v: int(t[np.argmax(bt >= v)]) if (bt >= v).any() else None
    de, fcs = tim(155), tim(194)
    drop = int(t[-1]) if bt[-1] >= 218 else None
    w = np.isfinite(R) & (t >= 120) & (t <= t[-1] - 15)
    x = R[w]
    dao, cuc, h = 0, x[0], 0
    for v in x:
        if h >= 0 and v < cuc - 1:
            dao += h > 0; h, cuc = -1, v
        elif h <= 0 and v > cuc + 1:
            dao += h < 0; h, cuc = 1, v
        if h > 0: cuc = max(cuc, v)
        if h < 0: cuc = min(cuc, v)
    dv = np.isfinite(R) & (t >= (fcs or 9e9)) & (t <= t[-1] - 15)
    truoc = R[np.isfinite(R) & (t >= 150) & (t < (fcs or t[-1]))]
    tang = float(np.max(truoc - np.minimum.accumulate(truoc))) if len(truoc) else 0.0
    return dict(DE=de, FCs=fcs, DROP=drop, lech_DE=None if de is None else de - 390, lech_FCs=None if fcs is None else fcs - 660,
                lech_DROP=None if drop is None else drop - 922, dev_s=None if (drop is None or fcs is None) else drop - fcs,
                dev_ror_tb=round(float(R[dv].mean()), 2) if dv.any() else None,
                pct_5_6=round(100 * float(np.mean((R[dv] >= 5) & (R[dv] <= 6))), 0) if dv.any() else None,
                dao_ror_ge1=dao, sd_dRoR=round(float(np.std(np.diff(x)) * 60), 2), ror_tang_lai_max=round(tang, 2),
                so_doi_nhiet=int(np.sum(np.abs(np.diff(u)) > 0.01)), buoc_max=round(float(np.max(np.abs(np.diff(u[15:])))), 1))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if sys.argv[1:] == ["thu"]:
        kq = {}
        for me in (4, 5):
            for hk in (0.9, 1.0, 1.1):
                o = thu_ban_sao(me, hk)
                d = danh_gia(o)
                kq["me%d_k%.1f" % (me, hk)] = dict(danh_gia=d, chuoi=[[int(a), round(float(c_), 1), round(float(e), 1)] for a, c_, _, e, _ in o[::5]])
                print("mẻ %d k×%.1f" % (me, hk), d)
        json.dump(kq, open(r"F:/Artisan/Profile/OTL-Hong/bao_cao_1710/me9_thu_ban_sao.json", "w", encoding="utf-8"), ensure_ascii=False)
    else:
        sys.exit("Chạy máy thật chưa nối: cần anh Thành cho phép rồi mới ghép LaiMe9 vào vòng panel (hong_lai_me_mpc.LaiMe.chay).")
