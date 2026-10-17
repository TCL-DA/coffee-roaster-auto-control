"""Nhận diện lỗi đường RoR BT của một mẻ có hạt (OTL Hồng, 17/10/2026).

Dùng chung cho phân tích sau mẻ và cho dòng PHÂN TÍCH 15 s khi đang rang (cùng ngưỡng).
Căn cứ: skill rang-ca-phe — chan-doan-profile.md (bảng Hiện tượng / Cơ chế, mục RoR), cac-cach-rang.md mục 3.1,
chien-luoc-rang.md "Theo pha", khoa-hoc-rang.md "BT, ET, RoR", dieu-khien-nhiet.md (trễ VX4, không giật SV).

RoR: hồi quy tuyến tính BT trong cửa sổ 30 s đặt giữa (t − 15 … t + 15), đơn vị °C/phút.
Khi đang rang chỉ có số tới "bây giờ", nên RoR mới nhất là của thời điểm bây giờ − 15 s (trễ 15 s, có ghi trong dòng).
"""
import numpy as np

CUA_SO = 30.0           # s, cửa sổ hồi quy RoR
BUOC_LUON = 3.0         # °C/ph, biên độ một lần đảo chiều tính là "lượn sóng"
TANG_LAI = 2.0          # °C/ph, RoR tăng lại trước FCs
TANG_LAI_GIU = 20.0     # s, phải giữ ít nhất
STALL_RoR = 4.0         # °C/ph, stall giữa DE và FCs
STALL_GIU = 30.0        # s
PHANG_TB_MAX = 7.5      # °C/ph: RoR DE→FCs trung bình cao hơn thì phẳng không đáng lo
DOC_PHANG = -0.3        # °C/ph mỗi phút: RoR DE→FCs giảm chậm hơn mức này = phẳng
CRASH_RoI = 3.0         # °C/ph rơi trong 60 s sau FCs so RoR lúc FCs − 30 s
FLICK_NHO = 1.5         # °C/ph nhô lên trong 90 s cuối
SCORCH_TP = 82.0        # °C, TP cao = lồng / charge nóng
SCORCH_DINH = 25.0      # °C/ph, đỉnh RoR sau TP
DIEU_KHIEN_TRE = 90.0   # s, tìm lệnh Nhiệt / gió đổi trước lỗi (VX4 + lồng: 20–60 s, cộng biên)


def ror30(t, bt):
    t = np.asarray(t, float)
    bt = np.asarray(bt, float)
    out = np.full(len(t), np.nan)
    h = CUA_SO / 2
    j0 = 0
    j1 = 0
    for i in range(len(t)):
        while t[j0] < t[i] - h:
            j0 += 1
        while j1 < len(t) and t[j1] <= t[i] + h:
            j1 += 1
        if j1 - j0 >= 10 and t[j1 - 1] - t[j0] >= CUA_SO * 0.8:
            x = t[j0:j1] - t[i]
            out[i] = np.polyfit(x, bt[j0:j1], 1)[0] * 60
    return out


def _muc(v, nhe, vua):
    return "nhe" if v < nhe else ("vua" if v < vua else "nang")


def _lenh_truoc(lenh, tu, den=None):
    """Lệnh Nhiệt / gió đổi trong [tu − DIEU_KHIEN_TRE, den] — chuỗi mô tả."""
    den = tu if den is None else den
    x = [l for l in lenh if tu - DIEU_KHIEN_TRE <= l[0] <= den]
    if not x:
        return "không có lệnh Nhiệt/gió đổi trong 90 s trước"
    return "; ".join("%s %d→%d %% lúc %ds" % (k, a, b, t) for t, k, a, b in x[:8])


def lenh_tu_log(t, nhiet, gio):
    out = []
    for i in range(1, len(t)):
        if nhiet[i] != nhiet[i - 1] and abs(nhiet[i] - nhiet[i - 1]) >= 3:
            out.append((float(t[i]), "Nhiệt", nhiet[i - 1], nhiet[i]))
        if gio[i] != gio[i - 1]:
            out.append((float(t[i]), "gió", gio[i - 1], gio[i]))
    return out


def tim_loi(t, bt, moc, lenh=(), lo=None, hi=None, bay_gio=None):
    """t (s từ charge), bt, moc {'TP','DE','FCs','DROP'} (giây, có thể thiếu), lenh [(t, tên, cũ, mới)].
    bay_gio: đang rang — chỉ dùng số tới bay_gio. Trả (danh sách lỗi, mảng RoR)."""
    t = np.asarray(t, float)
    bt = np.asarray(bt, float)
    if bay_gio is not None:
        k = t <= bay_gio
        t, bt = t[k], bt[k]
    R = ror30(t, bt)
    ok = np.isfinite(R)
    loi = []
    tp = moc.get("TP")
    de = moc.get("DE")
    fcs = moc.get("FCs")
    drop = moc.get("DROP")
    het = (drop - 15) if drop is not None else (t[-1] - 15)
    if tp is None:
        return loi, R
    # 1. Dấu hiệu scorching / tipping: TP cao + đỉnh RoR cao sau TP
    i_tp = int(np.argmin(abs(t - tp)))
    w = ok & (t >= tp + 30) & (t <= tp + 150)
    if w.any():
        dinh = float(np.nanmax(R[w]))
        if bt[i_tp] >= SCORCH_TP and dinh >= SCORCH_DINH:
            loi.append({"loai": "nguy cơ scorching/tipping (chỉ dấu hiệu)", "tu_s": int(tp), "den_s": int(tp + 150),
                        "muc": "nhe" if bt[i_tp] < 85 else "vua",
                        "so_do": "TP %.1f °C (≥ %.0f) · đỉnh RoR sau TP %.1f °C/ph" % (bt[i_tp], SCORCH_TP, dinh),
                        "lenh": _lenh_truoc(lenh, 0, tp + 150), "ma": "scorch"})
    # 2. RoR âm sau TP
    w = ok & (t >= tp + 30) & (t <= het)
    if w.any() and float(np.nanmin(R[w])) < 0:
        i = np.where(w & (R < 0))[0]
        loi.append({"loai": "RoR âm", "tu_s": int(t[i[0]]), "den_s": int(t[i[-1]]), "muc": "nang",
                    "so_do": "RoR thấp nhất %.1f °C/ph" % float(np.nanmin(R[w])), "lenh": _lenh_truoc(lenh, t[i[0]]), "ma": "am"})
    # 3. Lượn sóng do lái + RoR tăng lại (sau đỉnh RoR, trước FCs)
    den_truoc = (fcs if fcs is not None else het)
    w = ok & (t >= tp + 60) & (t < den_truoc)
    if w.sum() > 20:
        idx = np.where(w)[0]
        i_dinh = idx[int(np.argmax(R[idx]))]
        dao = []
        ref_i, chieu = idx[0], 0
        for i in idx:
            if chieu >= 0 and R[i] < R[ref_i] - BUOC_LUON:
                if chieu > 0:
                    dao.append(ref_i)
                chieu, ref_i = -1, i
            elif chieu <= 0 and R[i] > R[ref_i] + BUOC_LUON:
                if chieu < 0:
                    dao.append(ref_i)
                chieu, ref_i = 1, i
            elif (chieu > 0 and R[i] > R[ref_i]) or (chieu < 0 and R[i] < R[ref_i]):
                ref_i = i
        if len(dao) >= 1:
            bien = max(abs(R[dao[k + 1]] - R[dao[k]]) for k in range(len(dao) - 1)) if len(dao) > 1 else BUOC_LUON
            chu_ky = float(np.mean(np.diff(t[dao])) * 2) if len(dao) > 1 else float("nan")
            loi.append({"loai": "lượn sóng do lái", "tu_s": int(t[dao[0]]), "den_s": int(t[dao[-1]]),
                        "muc": "nhe" if len(dao) <= 1 else ("vua" if len(dao) <= 3 else "nang"),
                        "so_do": "%d lần RoR đảo chiều ≥ %.0f °C/ph · biên độ lớn nhất %.1f · chu kỳ ~%s s · điểm đảo %s" % (
                            len(dao), BUOC_LUON, bien, "—" if chu_ky != chu_ky else "%.0f" % chu_ky,
                            ", ".join("%ds/%.1f" % (t[d], R[d]) for d in dao[:6])),
                        "lenh": _lenh_truoc(lenh, t[dao[0]], t[dao[-1]]), "ma": "luon"})
        # RoR tăng lại sau đỉnh: từ đáy tạm tăng ≥ TANG_LAI và giữ ≥ TANG_LAI_GIU
        sau = idx[idx > i_dinh + 30]
        if len(sau) > 10:
            day = np.minimum.accumulate(R[sau])
            nho = R[sau] - day
            m = nho >= TANG_LAI
            if m.any():
                j = np.where(m)[0]
                if t[sau[j[-1]]] - t[sau[j[0]]] >= TANG_LAI_GIU or len(j) >= TANG_LAI_GIU:
                    v = float(nho.max())
                    loi.append({"loai": "RoR tăng lại (trước FCs)", "tu_s": int(t[sau[j[0]]]), "den_s": int(t[sau[j[-1]]]),
                                "muc": _muc(v, 4, 7),
                                "so_do": "RoR từ đáy %.1f lên %.1f (+%.1f °C/ph)" % (
                                    float(day[int(np.argmax(nho))]), float(R[sau][int(np.argmax(nho))]), v),
                                "lenh": _lenh_truoc(lenh, t[sau[j[0]]]), "ma": "tang"})
    # 4. Stall / nguy cơ baked giữa DE và FCs
    if de is not None:
        w = ok & (t >= de) & (t < (fcs if fcs is not None else het))
        if w.any():
            m = w & (R < STALL_RoR)
            if m.sum() >= STALL_GIU:
                i = np.where(m)[0]
                mn = float(np.nanmin(R[w]))
                loi.append({"loai": "stall (nguy cơ baked)", "tu_s": int(t[i[0]]), "den_s": int(t[i[-1]]),
                            "muc": "nang" if mn < 2 else ("vua" if m.sum() >= 60 else "nhe"),
                            "so_do": "%d s RoR < %.0f · thấp nhất %.1f °C/ph" % (int(m.sum()), STALL_RoR, mn),
                            "lenh": _lenh_truoc(lenh, t[i[0]]), "ma": "stall"})
        # 4b. RoR phẳng / không giảm suốt DE → FCs (≥ 180 s): nguy cơ baked/flat (cac-cach-rang 3.1, chan-doan "Baked/flat")
        den_p = fcs if fcs is not None else (t[-1] - 15)
        w = ok & (t >= de) & (t < den_p)
        if w.sum() >= 180:
            doc_ = float(np.polyfit(t[w] / 60.0, R[w], 1)[0])        # °C/ph mỗi phút
            tb = float(np.mean(R[w]))
            if doc_ >= DOC_PHANG and tb <= PHANG_TB_MAX:
                loi.append({"loai": "RoR phẳng (nguy cơ baked/flat)", "tu_s": int(de), "den_s": int(den_p),
                            "muc": "nang" if tb < 5 else ("vua" if doc_ >= 0 else "nhe"),
                            "so_do": "độ dốc RoR %+.2f °C/ph mỗi phút trong %d s · RoR TB %.1f · %.1f→%.1f" % (
                                doc_, int(w.sum()), tb, float(R[w][0]), float(R[w][-1])),
                            "lenh": _lenh_truoc(lenh, de, den_p), "ma": "phang"})
    # 5. Crash sau FCs
    if fcs is not None:
        i0 = int(np.argmin(abs(t - (fcs - 30))))
        w = ok & (t >= fcs) & (t <= min(fcs + 60, het))
        if np.isfinite(R[i0]) and w.any():
            roi = float(R[i0] - np.nanmin(R[w]))
            if roi >= CRASH_RoI:
                i = np.where(w)[0][int(np.argmin(R[w]))]
                loi.append({"loai": "crash", "tu_s": int(fcs), "den_s": int(t[i]), "muc": _muc(roi, 4, 6),
                            "so_do": "RoR FCs−30 s %.1f → thấp nhất %.1f (rơi %.1f °C/ph)" % (R[i0], R[i], roi),
                            "lenh": _lenh_truoc(lenh, fcs - 60, t[i]), "ma": "crash"})
    # 6. Flick 90 s cuối trước DROP
    # đang rang chưa DROP: xét 90 s gần nhất, chỉ sau FCs + 60 s
    tc = drop if drop is not None else (t[-1] if fcs is not None and t[-1] > fcs + 60 else None)
    if tc is not None:
        w = ok & (t >= tc - 105) & (t <= tc - 15)
        if w.sum() > 10:
            x = R[w]
            nho = x - np.minimum.accumulate(x)
            v = float(nho.max())
            if v > FLICK_NHO:
                j = int(np.argmax(nho))
                i = np.where(w)[0]
                loi.append({"loai": "flick", "tu_s": int(t[i[0]]), "den_s": int(t[i[j]]), "muc": _muc(v, 2.5, 4),
                            "so_do": "RoR từ đáy %.1f lên %.1f (+%.1f °C/ph) trong 90 s cuối" % (
                                float(np.minimum.accumulate(x)[j]), float(x[j]), v),
                            "lenh": _lenh_truoc(lenh, t[i[0]], t[i[j]]), "ma": "flick"})
    # 7. Dev ngoài dải đích
    if fcs is not None and lo is not None:
        w = ok & (t >= fcs) & (t <= het)
        if w.sum() >= 60:                      # cần ≥ 60 s dev, tránh báo nặng khi mới vào FCs
            x = R[w]
            tren, duoi = float(np.mean(x > hi)), float(np.mean(x < lo))
            if tren + duoi > 0.2:
                loi.append({"loai": "RoR dev ngoài dải đích", "tu_s": int(fcs), "den_s": int(het),
                            "muc": "nhe" if tren + duoi < 0.35 else ("vua" if tren + duoi < 0.5 else "nang"),
                            "so_do": "%.0f %% trên %g · %.0f %% dưới %g · TB %.2f" % (100 * tren, hi, 100 * duoi, lo, float(x.mean())),
                            "lenh": _lenh_truoc(lenh, fcs, het), "ma": "dai"})
    return loi, R


VIEC_LAI = {
    "scorch": "đầu mẻ: hạ Nhiệt sớm theo BT lúc START, không phát lại lịch mồi",
    "am": "nâng Nhiệt một bước, không cắt thêm",
    "luon": "giữ Nhiệt, bước ≤ 4 %/12 s, tăng phạt Δu",
    "tang": "hạ Nhiệt sớm 60–120 s trước FCs, không đuổi BT",
    "stall": "nâng Nhiệt một bước (+5 %) ngay, chờ 30 s",
    "crash": "không cắt thêm; nâng nhẹ nếu RoR < dải dưới",
    "flick": "không tăng muộn; hạ 3–5 % nếu RoR > dải trên",
    "dai": "kéo RoR về giữa dải bằng bước nhỏ",
    "phang": "dồn năng lượng trước DE để RoR giảm đều; không giữ RoR ~6 quá sớm",
}
