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
    6 FCs−90 s → FCs (theo BT + RoR đo, gan_fcs): cấm tăng trừ khi RoR đo < 4,8 · sau FCs: RoR đích PHẲNG 5,5, giảm tự do, tăng ≤ +0,5 %/10 s
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
DICH.update(json.loads(os.environ.get("HONG_DICH", "{}")))      # đề khác (vd Robusta phin) ghi đè bằng JSON
LICH_DAU = [(0, 80), (14, 70), (16, 55), (18, 40), (19, 30), (20, 20), (87, 30), (89, 40), (92, 50), (96, 60), (100, 70), (105, 77)]
U_DUNG = 77
PHAT_DU = float(os.environ.get("HONG_PHAT_DU", "0.05"))
GIO_NEN, GIO_FCS, T_GIO, BT_GIO, BU_GIO = 85, 90, float(os.environ.get("HONG_T_GIO", "600")), float(os.environ.get("HONG_BT_GIO", "190")), -3
# Mẻ 10 (17/10 chiều, sửa từ log mẻ 9) — mặc định TẮT, bật bằng env, mẻ 9 chạy y như cũ:
#   HONG_LICH_SAY  = [[t, %], ...]  sấy theo lịch cố định đã đo (mẻ 9: MPC DE cắt 70→64 vì bản sao báo DE sớm, thật trễ +16 s)
#   HONG_DE_MPC    = {"t": lệch_s}   chỉ xét MPC DE ở các giây này, cộng lệch bản sao đã đo (mẻ 9: 4:45 báo 6:32 thật 6:46 ⇒ +14)
#   HONG_NEO_DE=1  RoR đích DE→FCs neo vào RoR ĐO lúc DE, giảm cong r0 − (r0 − r1)·s^p, p chọn để RoR TB đủ cho FCs đúng giờ
#   HONG_TANG_MAX  tổng tăng Nhiệt từ DE tới FCs tối đa (%) — mẻ 9 tăng 64 → 79 rồi phải hạ ⇒ "đồi" RoR, FCs +25 s
LICH_SAY = json.loads(os.environ.get("HONG_LICH_SAY", "null"))
DE_MPC = {int(k): float(v) for k, v in json.loads(os.environ.get("HONG_DE_MPC", "{}")).items()}
NEO_DE = os.environ.get("HONG_NEO_DE") == "1"
TANG_MAX = float(os.environ.get("HONG_TANG_MAX", "99"))
# HONG_SAY_BAM=<log 1 Hz mẻ mẫu> (anh Thành 17/10 chiều): KHÔNG lịch Nhiệt cố định đầu mẻ, KHÔNG chờ lồng nguội. Sấy CHARGE → DE
# bám đường BT đích = BT mẻ mẫu (mẻ 9) co giãn thời gian cho DE mẫu (HONG_DE_MAU) trùng DE đích. MPC mỗi 10 s trên bản sao,
# ĉ học từ k ĐO (RoR/(buồng − BT)); tâm ứng viên N = (BT + R/k − 160)/2,1 với R = RoR đường đích + bù lệch BT trong 90 s.
# Trước TP + 20 s (hạt vừa vào, RoR âm, k vô nghĩa) bám đường BUỒNG của mẻ mẫu (bản sao buồng ← SV đáng tin).
# HONG_SAY_DICH=<csv t_rang,bt,buong> (mẻ 2 Yirgacheffe, anh duyệt 18/10): cùng cơ chế SAY_BAM nhưng file là ĐƯỜNG ĐÍCH đã dựng
# sẵn theo giờ rang của chính mẻ đó (DE nằm sẵn trong file) ⇒ KHÔNG co giãn thời gian, bỏ qua HONG_DE_MAU. Đặt cả hai ⇒ SAY_DICH thắng.
SAY_DICH = os.environ.get("HONG_SAY_DICH")
SAY_BAM = SAY_DICH or os.environ.get("HONG_SAY_BAM")
if SAY_BAM:
    import csv as _csv
    _r = [x for x in _csv.DictReader(open(SAY_BAM, encoding="utf-8")) if x["bt"] not in ("", "nan")]
    _co = 1.0 if SAY_DICH else float(os.environ.get("HONG_DE_MAU", "406")) / 390.0
    REF_T = np.array([float(x["t_rang"]) for x in _r]) / _co
    REF_BT = np.array([float(x["bt"]) for x in _r])
    REF_B = np.array([float(x["buong"]) for x in _r])
# Mẻ 2 Yirgacheffe (Hồng + Claude 18/10) — mặc định TẮT, mẻ cũ chạy y như cũ. Áp lên MỌI đường sấy (lịch / SAY_BAM / MPC DE),
# chỉ khi BT < DE. Gốc: mẻ 11 SAY_BAM bám buồng mẻ mẫu cắt 46 → 32 → 23 → 18 → 13 % trong 40 s (1:08 → 1:48) lúc RoR 24 → 31
# ⇒ buồng 252 → 185, RoR 30,9 → 16,5 trong 50 s (crash đầu mẻ do lái). Luật 7d: không cắt sâu rồi bù (buồng xuống nhanh, lên chậm).
#   HONG_SAY_MIN   sàn Nhiệt sấy (%), vd 25
#   HONG_ROR_TRAN  trần RoR sấy (°C/ph), vd 22: RoR đo > trần ⇒ KHÔNG tăng; nếu RoR còn đang lên (so 10 s trước) ⇒ hạ HONG_SAY_HA
#                  một bước; RoR > trần nhưng đã quay đầu ⇒ giữ (trễ buồng → RoR 15–20 s, hạ tiếp là cắt đôi)
#   HONG_SAY_HA    hạ tối đa mỗi 10 s trong sấy (%), mặc định 3 — chỉ có hiệu lực khi bật một trong hai biến trên
SAY_MIN = float(os.environ["HONG_SAY_MIN"]) if os.environ.get("HONG_SAY_MIN") else None
ROR_TRAN = float(os.environ["HONG_ROR_TRAN"]) if os.environ.get("HONG_ROR_TRAN") else None
SAY_HA = float(os.environ.get("HONG_SAY_HA", "3"))
SAY_HA_TU = float(os.environ.get("HONG_SAY_HA_TU", "30"))   # hạ êm tính từ giây này sau CHARGE (trước đó: hạ từ 80 % chờ charge về mức sấy)


# ⛔ Luật cứng anh Thành 17/10: KHÔNG BAO GIỜ CHARGE khi BT < 150 °C.
# Hai mốc khác nhau, không được lẫn:
#   BT_START  = BT lúc bấm START chương trình (lồng đã làm nguội, CHƯA có hạt) — kế hoạch 85–90 °C
#   BT_CHARGE = BT lúc firmware đổ hạt (tự CHARGE ở nhiệt charge $M23, thường 170) — bắt buộc ≥ 150 °C
BT_CHARGE_MIN = 150.0
BT_CHARGE_KE_HOACH = 170.0
BT_START_DAI = tuple(float(x) for x in os.environ.get("HONG_BT_START", "85,90").split(","))


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


def gan_fcs(bt, ror):
    """Còn ≤ 90 s tới FCs, tính theo BT + RoR ĐO (không theo giờ đích). Mẻ 11 (17/10): luật cũ "t ≥ FCs đích − 90" cấm tăng từ
    7:00 trong khi BT còn 179 / RoR 7,5 (thật còn ~2 phút) ⇒ không bù được RoR thấp, FCs trễ 43 s."""
    if bt >= DICH["bt_fcs"] - 2:
        return True
    return math.isfinite(ror) and ror > 0 and (DICH["bt_fcs"] - bt) / ror * 60 <= 90


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
        # ĉ ban đầu = k ĐO / k bảng của chính lô (mẻ 2: HONG_C0 = 1,4 khớp từ mẻ 1 BT < 140, ban_sao_500g.py). Mặc định 1,0 như cũ.
        # Gốc (chạy khô mẻ 2 18/10): ĉ 1,0 ⇒ bản sao trong bộ lái báo RoR thấp ⇒ nâng 22 → 28 % lúc 1:15 ⇒ đỉnh 25,5 lúc 1:54.
        self.c = float(os.environ.get("HONG_C0", "1.0"))
        self.t_cuoi = -999
        self.da_bu_gio = False
        self.gio = GIO_NEN
        self.neo = None          # (t0, r0, r1, p) khi NEO_DE
        self.u_de = None
        self.da_gan_fcs = False  # chốt: đã vào cửa FCs−90 s thì giữ cấm tăng tới FCs (RoR dao động không mở lại)
        self.u_say = {}          # t → Nhiệt đã ra trong sấy (giới hạn hạ / 10 s)
        self.ror_say = {}        # t → RoR (đo, hoặc RoR buồng trước TP+20) trong sấy — xem còn lên hay đã quay đầu
        self.tp_say = None

    def gioi_han_say(self, t, bt, b, ror_do, u, chu):
        """Sàn + trần RoR + hạ êm cho đoạn sấy (HONG_SAY_MIN / HONG_ROR_TRAN). Tắt cả hai ⇒ trả nguyên (u, chu).
        Trước TP + 20 s RoR đo âm / vô nghĩa ⇒ dùng RoR BUỒNG ĐANG ĐẨY = k_cua(BT)·ĉ·(buồng − BT) (luật 7f). Mẻ 11: 0:32–1:02
        buồng 234–244, BT ~95 ⇒ RoR buồng ≈ 25–26 > 22 trong khi bộ lái còn tăng 37 → 46 % — đó là nhiệt sinh đỉnh 30,9 lúc 1:38."""
        if SAY_MIN is None and ROR_TRAN is None:
            return u, chu
        self.bt_min_say = min(getattr(self, "bt_min_say", 999.0), bt)
        if getattr(self, "tp_say", None) is None and t > 25 and bt > self.bt_min_say + 1.0:
            self.tp_say = t
        tin_ror = self.tp_say is not None and t >= self.tp_say + 20 and math.isfinite(ror_do)
        r_bu = k_cua(bt) * self.c * (b - bt)
        r = ror_do if tin_ror else (r_bu if t >= SAY_HA_TU else float("nan"))
        nguon = "RoR" if tin_ror else "RoR buồng"
        if math.isfinite(r):
            self.ror_say[t] = r
        truoc = [v for k, v in self.u_say.items() if t - 10 <= k < t]
        u_cu = self.u_say[max(self.u_say)] if self.u_say else u
        moi, ly = u, []
        if ROR_TRAN is not None and math.isfinite(r) and r > ROR_TRAN:
            r10 = self.ror_say.get(t - 10)
            dang_len = r10 is not None and r > r10 + 0.2
            if dang_len and (t - getattr(self, "t_ha_tran", -99)) >= 10:
                moi, self.t_ha_tran = min(moi, u_cu - SAY_HA), t
                ly.append("%s %.1f > trần %.0f, còn lên ⇒ hạ %.0f %%" % (nguon, r, ROR_TRAN, SAY_HA))
            elif moi > u_cu:
                moi = u_cu
                ly.append("%s %.1f > trần %.0f ⇒ không tăng" % (nguon, r, ROR_TRAN))
        if t >= SAY_HA_TU and truoc and moi < max(truoc) - SAY_HA:
            moi = max(truoc) - SAY_HA
            ly.append("hạ êm ≤ %.0f %%/10 s" % SAY_HA)
        if SAY_MIN is not None and moi < SAY_MIN:
            moi = SAY_MIN
            ly.append("sàn sấy %.0f %%" % SAY_MIN)
        self.u_say[t] = moi
        self.u = moi
        if ly and abs(moi - u) > 1e-9 and (chu or abs(moi - u_cu) > 1e-9):     # giữ nguyên mức cũ thì không ghi lại mỗi giây
            chu = ((chu + " · ") if chu else "SẤY ") + "giới hạn: " + ", ".join(ly) + " ⇒ Nhiệt %.0f %%" % moi
        return moi, chu

    def dat_neo(self, t, bt, ror_do):
        """Neo RoR đích lúc vào DE: r0 = RoR đo, r1 = ror_fcs, p sao cho TB[r] = RoR cần (194 − BT)/(FCs − t)."""
        con = max(60, DICH["fcs"] - t)
        tb = (DICH["bt_fcs"] - bt) / con * 60
        r0 = ror_do if math.isfinite(ror_do) else tb
        r1 = DICH["ror_fcs"]
        if r0 > tb > r1:
            p = (r0 - r1) / (r0 - tb) - 1          # TB của r0 − (r0 − r1)·s^p trên [0,1] = r0 − (r0 − r1)/(p + 1)
        elif tb >= r0:
            p = 4.0                                # thiếu RoR: đường cong nhất (RoR đích lúc DE gần RoR đo, không ép tăng)
        else:
            p = 1.0                                # dư RoR: giảm thẳng, FCs sớm một chút
        p = float(min(4.0, max(1.0, p)))
        self.neo = (t, r0, min(r1, r0), p, con)
        return tb

    def say_bam(self, t, bt, b, ror_do):
        """Sấy: bám đường đích (BT sau TP, buồng trước TP). Trả (Nhiệt, gió, ghi chú)."""
        self.bt_min = min(getattr(self, "bt_min", 999.0), bt)
        if getattr(self, "t_tp", None) is None and t > 25 and bt > self.bt_min + 1.0:
            self.t_tp = t
        k_do = ror_do / (b - bt) if (math.isfinite(ror_do) and b - bt > 20 and ror_do > 0) else float("nan")
        if getattr(self, "t_tp", None) is not None and t >= self.t_tp + 20 and math.isfinite(k_do):
            self.c = min(1.6, max(0.5, self.c + 0.05 * (k_do / k_cua(bt) - self.c)))     # bộ quan sát: ĉ ← k đo / k bảng
        if t - self.t_cuoi < 10:
            return self.u, self.gio, ""
        self.t_cuoi = t
        H_ = 90
        tt = t + np.arange(1, H_ + 1)
        bam_bt = getattr(self, "t_tp", None) is not None and t >= self.t_tp + 20
        if bam_bt:
            ref = np.interp(tt, REF_T, REF_BT)
            r_ref = float(np.interp(t + 30, REF_T, REF_BT) - np.interp(t, REF_T, REF_BT)) * 2
            r_can = r_ref + (float(np.interp(t, REF_T, REF_BT)) - bt) * 60 / 90
            k = k_do if math.isfinite(k_do) else k_cua(bt) * self.c
            n_tam = (bt + max(0.0, r_can) / k - 160) / 2.1
        else:
            ref = np.interp(tt, REF_T, REF_B)
            n_tam = (float(np.interp(t + 20, REF_T, REF_B)) - 160) / 2.1
        ung = sorted(set(int(round(min(90, max(0, x)))) for x in
                         [n_tam + d for d in (-6, -4, -2, 0, 2, 4, 6)] + [self.u + d for d in (-2, -1, 0, 1, 2)]))
        best = None
        for n in ung:
            bts, _ = mo_phong(bt, b, n, H_, self.c) if bam_bt else (None, None)
            if bam_bt:
                J = float(np.mean((bts[29:] - ref[29:]) ** 2)) + 0.02 * (n - self.u) ** 2
            else:
                bb, out = b, []
                for i in range(H_):
                    bb += buoc_buong(bb, 160 + 2.1 * n)
                    out.append(bb)
                J = float(np.mean((np.array(out[9:]) - ref[9:]) ** 2)) + 0.5 * (n - self.u) ** 2
            if best is None or J < best[0]:
                best = (J, n)
        du = best[1] - self.u
        self.u = float(best[1])
        if not du:
            return self.u, self.gio, ""
        if bam_bt:
            return self.u, self.gio, "SẤY bám BT: BT %.1f / đích %.1f · R cần %.1f · k đo %s · N tâm %.0f · ĉ %.2f ⇒ Nhiệt %+.0f %%" % (
                bt, float(np.interp(t, REF_T, REF_BT)), r_can, ("%.3f" % k_do) if math.isfinite(k_do) else "—", n_tam, self.c, du)
        return self.u, self.gio, "SẤY bám buồng (trước TP+20): buồng %.0f / đích %.0f ⇒ Nhiệt %+.0f %%" % (
            b, float(np.interp(t, REF_T, REF_B)), du)

    def ror_dich(self, t, bt):
        if NEO_DE and self.neo is not None and bt < DICH["bt_fcs"]:
            # tính lại MỖI bước từ quãng còn lại (tự sửa giờ FCs như bản cũ), nhưng đường giảm CONG mũ p (p neo lúc DE sao cho
            # RoR đích lúc DE = RoR đo): điểm đầu đường cong có TB = tb và kết thúc r1 là ((p + 1)·tb − r1)/p (p = 1 ⇒ bản cũ)
            p = self.neo[3]
            con = max(30, DICH["fcs"] - t)
            tb = (DICH["bt_fcs"] - bt) / con * 60
            return max(3.5, ((p + 1) * tb - DICH["ror_fcs"]) / p)
        if bt < DICH["bt_fcs"] and t < DICH["fcs"]:
            con = max(30, DICH["fcs"] - t)
            tb = (DICH["bt_fcs"] - bt) / con * 60
            return max(3.5, 2 * tb - DICH["ror_fcs"])          # RoR giảm thẳng, trung bình đủ để 194 đúng 11:00
        if "ror_drop" in DICH:
            # Mẻ 2 (18/10): dev RoR GIẢM THẲNG ror_fcs → ror_drop, trung bình đủ để BT tới bt_drop sau (drop_t − fcs) giây tính từ
            # nổ ĐO (t_fcs), không từ giờ đích ⇒ nổ trễ / sớm thì dev vẫn dài như kế hoạch. Dự báo chưa qua nổ ⇒ coi nổ ở giờ đó.
            t_f = self.t_fcs if getattr(self, "t_fcs", None) is not None else max(t, DICH["fcs"])
            con = max(20.0, t_f + DICH["drop_t"] - DICH["fcs"] - t)
            tb = max(0.0, DICH["bt_drop"] - bt) / con * 60
            return min(DICH["ror_fcs"], max(DICH["ror_drop"], 2 * tb - DICH["ror_drop"]))
        return DICH["ror_dev"]                                  # sau FCs: RoR đích PHẲNG 5,5 (giữa dải 5–6)

    def lenh(self, t, bt, b, ror_do):
        if bt >= DICH["bt_fcs"] and getattr(self, "t_fcs", None) is None:
            self.t_fcs = t                                      # giờ nổ ĐO (ngưỡng bt_fcs) — gốc đường dev khi DICH có ror_drop
        u, gio, chu = self._lenh(t, bt, b, ror_do)
        if bt < DICH["bt_de"]:
            u, chu = self.gioi_han_say(t, bt, b, ror_do, u, chu)
        return u, gio, chu

    def _lenh(self, t, bt, b, ror_do):
        ghi = ""
        # 5. gió theo lịch + bù trước
        if not self.da_bu_gio and (t >= T_GIO or bt >= BT_GIO):
            self.gio, self.da_bu_gio = GIO_FCS, True
            self.u = max(0.0, self.u + BU_GIO)
            ghi = "gió 85→90, bù trước %d %% (k +6–8 %%)" % BU_GIO
            return self.u, self.gio, ghi
        # 2. đầu mẻ theo lịch mẻ 4
        if SAY_BAM and bt < DICH["bt_de"]:
            return self.say_bam(t, bt, b, ror_do)
        if LICH_SAY is not None and 105 <= t and bt < DICH["bt_de"]:
            moi = self.u
            for tt, uu in LICH_SAY:
                if t >= tt:
                    moi = float(uu)
            if self.c is not None and math.isfinite(ror_do) and b - bt > 20 and bt >= 115:
                self.c = min(1.4, max(0.7, self.c + 0.02 * (ror_do / (k_cua(bt) * (b - bt)) - self.c)))
            if t in DE_MPC:
                best = None
                for du in (-1, 0, 1, 2):
                    bts, _ = mo_phong(bt, b, moi + du, 600, self.c)
                    i = int(np.argmax(bts >= DICH["bt_de"])) if (bts >= DICH["bt_de"]).any() else 900
                    de_bao = t + i + 1 + DE_MPC[t]
                    J = (de_bao - DICH["de"]) ** 2 + 30 * du ** 2
                    if best is None or J < best[0]:
                        best = (J, du, de_bao)
                self.lich_bu = getattr(self, "lich_bu", 0) + best[1]
                self.u = moi + self.lich_bu
                return self.u, self.gio, "MPC DE (lệch bản sao +%d s): Nhiệt %+d %% ⇒ DE dự báo %d:%02d" % (
                    DE_MPC[t], best[1], best[2] // 60, best[2] % 60)
            self.u = moi + getattr(self, "lich_bu", 0)
            return self.u, self.gio, ""
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
        if NEO_DE and self.neo is None:
            tb = self.dat_neo(t, bt, ror_do)
            self.u_de = self.u
            self.t_cuoi = t
            return self.u, self.gio, "NEO DE: RoR đo %.1f → %.1f lúc FCs đích · cần TB %.2f · p %.2f" % (
                self.neo[1], self.neo[2], tb, self.neo[3])
        if t - self.t_cuoi < 10:
            return self.u, self.gio, ""
        self.t_cuoi = t
        best = None
        sau_fcs = bt >= DICH["bt_fcs"]
        # chốt cửa FCs−90 s: RoR 30 s dao động quanh ngưỡng 90 s thì luật không tự mở lại (mở lại ⇒ tăng ⇒ RoR tăng lại trước FCs)
        self.da_gan_fcs = self.da_gan_fcs or gan_fcs(bt, ror_do)
        for du in (-1.0, -0.5, 0.0, 0.5, 1.0):
            # 6. sau FCs: được giảm theo nhu cầu, TĂNG tối đa +0,5 %/10 s (k gần hằng mà BT +24 °C trong dev ⇒ buồng phải
            #    nhích theo BT thì RoR mới phẳng). FCs−90 s → FCs: cấm tăng trừ khi RoR đo < 4,8 (chặn RoR tăng lại trước FCs).
            if sau_fcs and du > 0.5:
                continue
            if (not sau_fcs) and du > 0 and self.u_de is not None and self.u + du > self.u_de + TANG_MAX:
                continue
            if (not sau_fcs) and du > 0 and self.da_gan_fcs and not (math.isfinite(ror_do) and ror_do < 4.8):
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
