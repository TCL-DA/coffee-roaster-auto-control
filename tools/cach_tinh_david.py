# -*- coding: utf-8 -*-
"""CÁCH TÍNH DAVID — hằng số truyền nhiệt k = RoR / (ET − BT) dọc mẻ, đọc thẳng từ giản đồ Artisan (.alog) (15/10/2026).
⛔ Chủ máy 15/10: Hồng LUÔN tính k David để THAM KHẢO (chấm, phiên, lái, phân tích mẻ khách) — không dùng để điều khiển.

Nguồn và luật suy luận: skill rang-ca-phe → references/chan-doan-profile.md mục "Cách tính David".
  - Mẻ mẫu chuẩn: k gần PHẲNG suốt mẻ. Lô nhân khác ⇒ k khác nhưng vẫn là hằng số; k không thể tăng trong lúc rang.
  - k VỌT cuối mẻ ⇒ hạt nhận nhiệt mà ET − BT không giải thích (thành trống dẫn nhiệt). Vọt đúng lúc lửa THẤP nhất
    ⇒ gas thực > lệnh ở mức thấp ⇒ nghi điểm 0 van gas lệch (loại trừ: van giảm áp, đầu dò ET, gió yếu — xem skill).
  - Chỉ so giữa các mẻ CÙNG máy, cùng gió / trống, cùng cỡ mẻ. Lồng TRỐNG (bài nhiệt không hạt): k chỉ là đặc trưng truyền
    nhiệt đầu dò BT — so giữa các lượt cùng gió / trống, không suy ra chuyện hạt.

    python tools/cach_tinh_david.py <mẫu.alog> [<nghi_lỗi.alog> ...] [--phut 3,6,9,11] [--cua 30]

Tốc độ: cả mẻ tính MỘT lần bằng numpy (tổng tích luỹ ⇒ hồi quy mọi điểm O(N)); ~0,01 s cho mẻ 20 phút.
Mốc thời gian tính từ CHARGE (nếu có), không thì từ START. RoR = hồi quy BT trên cửa sổ `cua` giây ĐỐI XỨNG (phân tích sau
mẻ, không trễ). Bỏ điểm ET − BT < 8 °C (chia số nhỏ ⇒ k vô nghĩa).
"""
import ast
import os
import sys

import numpy as np

ET_BT_MIN = 8.0          # °C — dưới mức này k không đáng tin
VOT = 1.5                # k cuối / k nền ≥ 1,5 ⇒ báo K VỌT CUỐI


def doc_alog(duong):
    """Mảng numpy (t giây từ CHARGE hoặc START, BT, ET, Burner % hoặc NaN) + giây DROP (hoặc None)."""
    with open(duong, encoding="utf-8") as f:
        d = ast.literal_eval(f.read())
    tx = np.asarray(d.get("timex", []), dtype=float)
    n = len(tx)
    et = np.asarray([v if v is not None else np.nan for v in d.get("temp1", [])[:n]], dtype=float)
    bt = np.asarray([v if v is not None else np.nan for v in d.get("temp2", [])[:n]], dtype=float)
    g = np.full(n, np.nan)
    for k, ten in (("extratemp2", "extraname2"), ("extratemp1", "extraname1")):
        for j, nm in enumerate(d.get(ten, [])):
            if "burner" in str(nm).lower() and j < len(d.get(k, [])):
                s = np.asarray([v if v is not None else np.nan for v in d[k][j][:n]], dtype=float)
                g[:len(s)] = np.where(s >= 0, s, np.nan)
    ti = d.get("timeindex") or [-1, 0, 0, 0, 0, 0, 0, 0]
    i_charge = ti[0] if ti[0] is not None and ti[0] >= 0 else 0
    i_drop = ti[6] if len(ti) > 6 and ti[6] else None
    t0 = tx[i_charge] if n else 0.0
    ok = (bt > 0) & (et > 0) & np.isfinite(bt) & np.isfinite(et)
    t_drop = float(tx[i_drop] - t0) if i_drop and i_drop < n else None
    co_charge = ti[0] is not None and ti[0] >= 0         # Artisan: −1 = không có CHARGE (bài lồng trống)
    return tx[ok] - t0, bt[ok], et[ok], g[ok], t_drop, co_charge


def k_day(t, bt, et, cua=30.0):
    """RoR (°C/phút) và k cho MỌI mẫu một lần: hồi quy BT theo t trên cửa sổ đối xứng ±cua/2, bằng tổng tích luỹ."""
    t, bt, et = np.asarray(t, float), np.asarray(bt, float), np.asarray(et, float)
    lo = np.searchsorted(t, t - cua / 2, "left")
    hi = np.searchsorted(t, t + cua / 2, "right")
    c = lambda x: np.concatenate(([0.0], np.cumsum(x)))  # noqa: E731
    St, Sb, Stt, Stb = c(t), c(bt), c(t * t), c(t * bt)
    n = (hi - lo).astype(float)
    st, sb = St[hi] - St[lo], Sb[hi] - Sb[lo]
    stt, stb = Stt[hi] - Stt[lo], Stb[hi] - Stb[lo]
    mau = n * stt - st * st
    with np.errstate(divide="ignore", invalid="ignore"):
        ror = np.where((n >= 5) & (mau > 0), (n * stb - st * sb) / mau * 60.0, np.nan)
        hieu = et - bt
        k = np.where(hieu >= ET_BT_MIN, ror / hieu, np.nan)
    return ror, k


def k_song(ror_bt, et, bt):
    """k tức thời cho vòng lái (RoR đã có sẵn từ hồi quy đuôi). None khi ET − BT < ET_BT_MIN."""
    hieu = et - bt
    return ror_bt / hieu if hieu >= ET_BT_MIN else None


def phan_tich(duong, phut=(3, 6, 9, 11), cua=30.0):
    t, bt, et, g, t_drop, co_charge = doc_alog(duong)
    if len(t) < 10:
        return {"file": duong, "loi": "giản đồ có %d mẫu" % len(t)}
    ror, k = k_day(t, bt, et, cua)
    t_het = t_drop if t_drop else float(t[-1])
    moc = np.array([p * 60 for p in phut if p * 60 < t_het - cua / 2] + [t_het - cua / 2])
    idx = np.clip(np.searchsorted(t, moc), 0, len(t) - 1)
    diem = [(float(t[i]), float(k[i]), float(ror[i]), float(et[i]), float(bt[i]), float(g[i])) for i in idx]
    # k nền = trung vị 2/3 đầu (từ phút 2, bỏ đoạn TP), k cuối = lớn nhất 1/3 cuối — chỉ điểm hợp lệ
    hop = np.isfinite(k) & (t >= 120) & (t <= t_het - cua / 2)
    nen = cuoi = None
    if hop.sum() >= 60:
        ih = np.flatnonzero(hop)
        cat = ih[int(len(ih) * 2 / 3)]
        nen = float(np.median(k[ih[ih < cat]]))
        sau = ih[ih >= cat]
        j = sau[np.argmax(k[sau])]
        cuoi = (float(t[j]), float(k[j]), float(g[j]))
    return {"file": duong, "diem": diem, "nen": nen, "cuoi": cuoi, "t_het": t_het, "co_hat": co_charge}


def tom_tat(kq):
    """Một dòng cho bảng tổng kết / báo cáo."""
    if kq.get("loi") or kq.get("nen") is None:
        return "k David: —"
    t, k, g = kq["cuoi"]
    vot = kq["co_hat"] and kq["nen"] and k / kq["nen"] >= VOT
    return "k David nền %.3f · cuối %.3f lúc %s · ×%.2f%s" % (kq["nen"], k, _mmss(t), k / kq["nen"] if kq["nen"] else 0,
                                                              " ⛔ VỌT" if vot else ("" if kq["co_hat"] else " (lồng trống)"))


def _mmss(t):
    return "%d:%02d" % divmod(int(round(t)), 60)


def _so(v, f="%.3f"):
    return f % v if v is not None and np.isfinite(v) else "—"


def in_kq(kq, k_mau=None):
    if kq.get("loi"):
        return "DAVID %s: %s" % (os.path.basename(kq["file"]), kq["loi"])
    dong = ["DAVID %s" % os.path.basename(kq["file"])]
    for t, k, r, e, b, g in kq["diem"]:
        dong.append("  %5s  ET %5.1f BT %5.1f ΔT %5.1f RoR %5s  k %5s%s" % (
            _mmss(t), e, b, e - b, _so(r, "%.1f"), _so(k), "  lửa %g%%" % g if np.isfinite(g) else ""))
    if kq["nen"] is not None:
        t, k, g = kq["cuoi"]
        ti_le = k / kq["nen"] if kq["nen"] > 0 else float("inf")
        dong.append("  ⇒ k nền %.3f · k cuối lớn nhất %.3f lúc %s%s · ×%.2f%s" % (
            kq["nen"], k, _mmss(t), " (lửa %g%%)" % g if np.isfinite(g) else "", ti_le,
            ("  (không CHARGE = bài lồng trống: k chỉ tham khảo, không áp luật vọt)" if not kq["co_hat"]
             else "  ⛔ K VỌT CUỐI — xem luật suy luận" if ti_le >= VOT else "  k phẳng")))
        if k_mau:
            dong.append("  so mẻ mẫu: k nền ×%.2f · k cuối ×%.2f" % (kq["nen"] / k_mau, k / k_mau))
    else:
        dong.append("  ⇒ quá ít điểm hợp lệ để tính k nền (ET − BT < %.0f °C hoặc mẻ ngắn)" % ET_BT_MIN)
    return "\n".join(dong)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    pos, opt, i = [], {}, 1
    while i < len(sys.argv):
        if sys.argv[i].startswith("--"):
            opt[sys.argv[i][2:]] = sys.argv[i + 1]
            i += 2
        else:
            pos.append(sys.argv[i])
            i += 1
    if not pos:
        sys.exit(__doc__)
    phut = tuple(float(x) for x in opt.get("phut", "3,6,9,11").split(","))
    cua = float(opt.get("cua", 30))
    k_mau = None
    for n, f in enumerate(pos):
        kq = phan_tich(f, phut, cua)
        print(in_kq(kq, k_mau if n else None))
        if n == 0 and not kq.get("loi"):
            k_mau = kq["nen"]
