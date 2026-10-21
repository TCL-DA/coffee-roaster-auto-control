# -*- coding: utf-8 -*-
"""Đề 3 (chủ máy 15/10/2026 ~14:20): 5 bài nhiệt nối tiếp trên máy điện VX4, burner (Nhiệt $M36) + gió ($M35), trống giữ nguyên.
Mỗi bài một giản đồ Artisan (chạy ngầm), chấm trên .alog theo F:/Artisan/Profile/OTL-Hong/de3_10bai/DE-BAI.md.

  HONG_DUOC_LAI=1 python tools/de3_nam_bai.py chay <hết HH:MM> [--tu 1]
  python tools/de3_nam_bai.py cham <bài> <file.alog>

Bài giữ / bậc (1, 2, 5): bộ giải MPC `GiaiDe` (đã đạt 7/7 mốc không lố sáng 15/10) qua `chay_de`, giữ Lệnh + mức khi xong.
Bài dốc (3, 4): bộ bám đường dốc PI trên Nhiệt, tiền định từ mức giữ vừa đo ở bài trước (≈ 1,1 %/°C, giáo trình mục 7).
Gió cố định 85 % (đúng nền mô hình bản sao số) — đổi gió làm sai mô hình MPC nhiều hơn là giúp.
"""
import csv
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hong_qua_panel as h  # noqa: E402

THU_MUC = r"F:\Artisan\Profile\OTL-Hong\de3_10bai"
GIO = 85
# (tên, loại, tham số chấm)
BAI = {
    1: dict(ten="Giu diem 200", loai="giu", dich=200.0, dai=1.5, can=60.0, han=180.0, vao_han=None),
    2: dict(ten="Bac len 205", loai="giu", dich=205.0, dai=1.5, can=30.0, han=90.0, vao_han=60.0),
    3: dict(ten="Doc len 205-215 +5", loai="doc", r0=205.0, doc=5.0, dai=1.5, han=120.0),
    4: dict(ten="Doc xuong 215-195 -8", loai="doc", r0=215.0, doc=-8.0, dai=2.0, han=150.0),
    5: dict(ten="Giu chat 195 +-1", loai="giu", dich=195.0, dai=1.0, can=60.0, han=120.0, vao_han=None),
}


# ── chấm ──────────────────────────────────────────────────────────────────────────────────────
def _doc(duong, han):
    ts, bts, _, _ = h.doc_alog(duong)
    t = np.asarray(ts, float) - ts[0]
    bt = np.asarray(bts, float)
    m = t <= han + 0.5
    return t[m], bt[m]


def cham(so, duong):
    b = BAI[so]
    t, bt = _doc(duong, b["han"])
    if len(t) < 2:
        return {"bai": so, "diem": 0.0, "ghi_chu": "giản đồ trống", "alog": duong}
    if b["loai"] == "doc":
        ref = b["r0"] + b["doc"] * t / 60.0
        lech = bt - ref
        ty = float(np.mean(np.abs(lech) <= b["dai"] + 1e-9))
        return {"bai": so, "diem": round(min(10.0, 10.0 * ty / 0.9), 1), "ty_le": round(ty * 100, 1),
                "lech_max": round(float(np.abs(lech).max()), 2), "giu_max": None, "lo_max": round(float(lech.max()), 2),
                "tut_max": round(float(-lech.min()), 2), "dai_giay": round(float(t[-1]), 0), "alog": duong}
    trong = np.abs(bt - b["dich"]) <= b["dai"] + 1e-9
    vao = np.flatnonzero(trong)
    giu_max, j = 0.0, None
    for k in range(len(t)):
        if trong[k] and j is None:
            j = k
        if j is not None and (not trong[k] or k == len(t) - 1):
            e = k if trong[k] else k - 1
            giu_max, j = max(giu_max, float(t[e] - t[j])), None
    t_vao = float(t[vao[0]]) if len(vao) else None
    ra = 0.0
    if len(vao):
        sau = bt[vao[0]:]
        ra = float(max(0.0, (np.abs(sau - b["dich"]) - b["dai"]).max()))
    diem = 10.0 * min(1.0, giu_max / b["can"])
    if b["vao_han"] is not None and (t_vao is None or t_vao > b["vao_han"]):
        diem -= 2.0
    diem -= math.floor(ra / 0.5 + 1e-9) * 1.0
    return {"bai": so, "diem": round(max(0.0, diem), 1), "giu_max": round(giu_max, 1), "t_vao": t_vao,
            "ra_ngoai_max": round(ra, 2), "dai_giay": round(float(t[-1]), 0), "alog": duong}


def dong_kq(kq):
    b = BAI[kq["bai"]]
    if b["loai"] == "doc":
        ct = "trong dải %.1f %% mẫu · lệch max %.2f (lố %.2f / tụt %.2f)" % (kq["ty_le"], kq["lech_max"], kq["lo_max"],
                                                                            kq["tut_max"])
    else:
        ct = "giữ dài nhất %.0f s (cần %.0f) · vào dải %s · ra ngoài dải max %.2f °C" % (
            kq["giu_max"], b["can"], "%.0f s" % kq["t_vao"] if kq.get("t_vao") is not None else "—", kq["ra_ngoai_max"])
    return "| %d | %s | `%s` | **%.1f** | %s | %.0f s |" % (kq["bai"], b["ten"], os.path.basename(kq["alog"] or "-"),
                                                          kq["diem"], ct, kq.get("dai_giay", 0))


def ghi_kq(dong):
    p = os.path.join(THU_MUC, "ket_qua.md")
    moi = not os.path.exists(p)
    with open(p, "a", encoding="utf-8") as f:
        if moi:
            f.write("# Kết quả đề 3 — OTL Hồng (chấm trên .alog theo DE-BAI.md)\n\n")
        f.write(dong + "\n")


# ── bài giữ: GiaiDe có thời hạn ───────────────────────────────────────────────────────────────
class GiaiDeHan(h.GiaiDe):
    """GiaiDe kết thúc SẠCH (giữ Lệnh + mức) khi xong mốc HOẶC hết thời hạn bài — để bài sau nối tiếp không mất nhiệt."""

    def __init__(self, han, **kw):
        super().__init__(**kw)
        self.han, self.t_hien = han, 0.0

    @property
    def het(self):
        return self.i >= len(self.moc) or self.t_hien >= self.han

    def cap_nhat(self, t, bt, et, buong):
        self.t_hien = t
        return super().cap_nhat(t, bt, et, buong)


def bai_giu(so, panel, art, in_ra, het):
    b = BAI[so]
    kw = dict(moc=(b["dich"],), giu=int(b["can"]) + 3, dai_dem=b["dai"] - 0.3)
    if b["dai"] <= 1.0:
        kw.update(dai_ke=0.6, bien_lo=0.3, bien_lo_giu=0.6, bien_lo_rong=0.6)
    giai = GiaiDeHan(b["han"] - 2.0, **kw)
    art.bat_on()
    kq = h.chay_de(panel, art, h.DongHoThat(), giai, log_csv=os.path.join(THU_MUC, "bai%d.csv" % so),
                   in_ra=lambda s: in_ra("[B%d] %s" % (so, s)), het_luc=het, tat_cuoi=False)
    return kq, giai.u


# ── bài dốc: PI bám đường dốc trên Nhiệt ──────────────────────────────────────────────────────
def bai_doc(so, panel, art, in_ra, het, u_giu, t_giu, kff=1.2, kp=5.0, ki=0.15, tp=12.0):
    """Đường dốc r(t) = r0 + doc·t/60 từ START. Nhiệt = tiền định (mức giữ đo được + 1,1 %/°C·(r − T giữ) + kff·doc)
    + kp·sai số dự báo trước tp giây + tích phân. Lệnh luôn bật; gió cố định."""
    b = BAI[so]
    art.bat_on()
    ok, ly = art.kiem()
    in_ra("[B%d] ARTISAN KIEM: %s" % (so, ly))
    if not ok:
        return {"dung": "artisan", "alog": None}, u_giu
    art.reset_start()
    t0 = time.time()
    time.sleep(3)
    for _ in range(3):
        ok, ct = art.dang_ghi()
        if ok:
            break
        time.sleep(2)
    in_ra("[B%d] ARTISAN DANG GHI: %s" % (so, ct))
    if not ok:
        panel.lenh_nhiet(False)
        return {"dung": "artisan_khong_ghi", "alog": art.tat_luu()}, 0
    f = open(os.path.join(THU_MUC, "bai%d.csv" % so), "a", newline="", encoding="utf-8")
    w = csv.writer(f)
    w.writerow(["gio", "t", "ref", "bt", "et", "buong", "nhiet", "lenh", "gio_pct", "ror", "e", "I"])
    ls, I, u_cu, t_ok, ly_do = [], 0.0, None, time.time(), "xong"
    try:
        while True:
            now = time.time()
            t = now - t0
            if t >= b["han"] + 1.0:
                break
            try:
                d = panel.doc_tat_ca()
                t_ok = now
            except (OSError, ValueError) as e:
                if now - t_ok > h.MAT_SO_GIAY:
                    ly_do = "MAT SO %s" % e
                    break
                time.sleep(1)
                continue
            if d["bt"] > h.BT_TUYET_DOI or d["et"] > h.ET_MAX:
                ly_do = "AN TOAN BT %.1f ET %.1f" % (d["bt"], d["et"])
                break
            loi = h.tu_kiem(d, None)
            if loi or now > het:
                ly_do = "TU KIEM: " + "; ".join(loi) if loi else "HET GIO"
                break
            if not art.con_nhan_so(d["bt"]):
                ly_do = "Artisan mất số > 10 s"
                break
            ls.append((t, d["bt"]))
            ls = ls[-40:]
            ror = h.doc_hoi_quy(ls, 20) if t > 6 else b["doc"]
            ref_p = b["r0"] + b["doc"] * (t + tp) / 60.0
            e = ref_p - (d["bt"] + ror * tp / 60.0)
            u_ff = u_giu + 1.1 * (ref_p - t_giu) + kff * b["doc"]
            u_raw = u_ff + kp * e + I
            u = int(round(max(0.0, min(100.0, u_raw))))
            if 0 < u < 100 or (u == 0 and e > 0) or (u == 100 and e < 0):   # chống bão hoà tích phân
                I += ki * e
            if u != u_cu:
                panel.dat_nhiet(u)
                if not d["lenh_nhiet"]:
                    panel.lenh_nhiet(True)
                if u_cu is None or abs(u - u_cu) >= 5:
                    in_ra("[B%d] %5.0f BT %.1f ref %.1f RoR %+.1f e %+.2f -> Nhiet %d" % (so, t, d["bt"], ref_p, ror, e, u))
                u_cu = u
            w.writerow([time.strftime("%H:%M:%S"), round(t, 1), round(ref_p, 2), d["bt"], d["et"], d["buong"], u,
                        d["lenh_nhiet"], d["gio"], round(ror, 2), round(e, 2), round(I, 2)])
            f.flush()
            time.sleep(max(0.0, 1.0 - (time.time() - now)))
    finally:
        f.close()
        if ly_do != "xong":
            panel.lenh_nhiet(False)
    in_ra("[B%d] KET THUC: %s · Nhiet %s" % (so, ly_do, u_cu))
    alog = art.tat_luu()
    in_ra("[B%d] ARTISAN OFF · %s" % (so, alog))
    return {"dung": ly_do, "alog": alog}, (u_cu if ly_do == "xong" else 0)


def chay(het_hhmm, tu=1):
    if os.environ.get("HONG_DUOC_LAI") != "1":
        sys.exit("Chưa có quyền lái (HONG_DUOC_LAI=1).")
    het = h._gio_het(het_hhmm)
    os.makedirs(THU_MUC, exist_ok=True)
    nk = open(os.path.join(THU_MUC, "nhat_ky.txt"), "a", encoding="utf-8")

    def in_ra(s):
        dong = time.strftime("%H:%M:%S ") + s
        print(dong, flush=True)
        nk.write(dong + "\n")
        nk.flush()

    panel, art = h.Panel(), h.ArtisanThat()
    if panel.doc(21, 1)[0] != h.MAN_RANG:
        in_ra("dang nhap -> man %s" % panel.dang_nhap())
    panel.dat_gio(GIO)
    in_ra("GIO %d%% · trong giu nguyen %s" % (GIO, panel.doc_tat_ca()["dat_trong"]))
    if tu == 1:
        # chuẩn bị (giản đồ riêng, không chấm): MPC về 200, giữ 10 s, GIỮ Lệnh + mức
        art.bat_on()
        kv = h.chay_de(panel, art, h.DongHoThat(), h.GiaiDe(moc=(200.0,), giu=10, dai_dem=1.2), het_luc=het,
                       tat_cuoi=False, log_csv=os.path.join(THU_MUC, "chuan_bi.csv"),
                       in_ra=lambda s: in_ra("[chuan bi] " + s))
        in_ra("CHUAN BI: %s · %s" % (kv.get("dung"), kv.get("alog")))
        if not kv.get("sach"):
            h.an_toan(gio=100)
            return
    t_bai1, u, t_giu = None, None, None
    for so in range(tu, 6):
        if time.time() > het:
            in_ra("HET GIO LAI truoc bai %d" % so)
            break
        if t_bai1 is None:
            t_bai1 = time.strftime("%H:%M:%S")
            ghi_kq("\nSTART bài %d: %s\n\n| # | Bài | Giản đồ | Điểm | Chi tiết | Dài |\n|---|---|---|---|---|---|" % (so, t_bai1))
        b = BAI[so]
        if b["loai"] == "giu":
            kq, uu = bai_giu(so, panel, art, in_ra, het)
            u, t_giu = uu[0], b["dich"]
        else:
            if u is None:
                d = panel.doc_tat_ca()
                u, t_giu = d["dat_nhiet"], d["bt"]
            kq, u = bai_doc(so, panel, art, in_ra, het, u, t_giu)
            t_giu = b["r0"] + b["doc"] * b["han"] / 60.0
        if kq.get("alog"):
            ck = cham(so, kq["alog"])
            ghi_kq(dong_kq(ck))
            in_ra("CHAM BAI %d: %.1f diem · %s" % (so, ck["diem"], ck))
        else:
            ghi_kq("| %d | %s | — | 0 | không có giản đồ (%s) | — |" % (so, b["ten"], kq.get("dung")))
        if kq.get("dung") not in ("xong",) and not kq.get("sach", kq.get("dung") == "xong"):
            in_ra("DUNG sau bai %d: %s" % (so, kq.get("dung")))
            break
    ghi_kq("\nHết bài cuối: %s\n" % time.strftime("%H:%M:%S"))
    h.an_toan(gio=100)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    lenh, (pos, opt) = sys.argv[1], h._tach_opt(sys.argv[2:])
    if lenh == "chay":
        chay(pos[0], tu=int(opt.get("tu", 1)))
    elif lenh == "cham":
        print(dong_kq(cham(int(pos[0]), pos[1])))
