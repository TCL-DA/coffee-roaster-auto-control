# -*- coding: utf-8 -*-
"""Phân tích log QUAN SÁT anh Thành tự lái về BT 200 (15/10/2026) — chỉ đọc file, không chạm máy.
    python tools/hong_phan_tich_quan_sat.py <log.csv> [--dich 200 --dai 1.5]
In: bảng thao tác (gộp các lần kéo liền nhau ≤ 4 s), đáp ứng BT/ET/buồng, điểm hãm, so MPC (BamDuong) trên cùng trạng thái,
sai số bản sao số vòng hở với đúng lệnh của anh + bộ tham số khớp nhất (độ nhạy × offset cT)."""
import csv
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ban_sao_so_may_dien as bss  # noqa: E402
import hong_de3 as h3  # noqa: E402
import hong_qua_panel as hq  # noqa: E402


def doc(duong):
    with open(duong, encoding="utf-8") as f:
        r = list(csv.DictReader(f))
    g = lambda k: np.array([float(x[k]) for x in r])  # noqa: E731
    with open(duong, encoding="utf-8") as f:
        gio = [x[0] for x in list(csv.reader(f))[1:]]    # header có 2 cột "gio" (giờ + gió thật) ⇒ lấy giờ theo vị trí
    return {"gio": gio, "t": g("t"), "bt": g("bt"), "et": g("et"), "buong": g("buong"),
            "n": g("dat_nhiet"), "l": g("lenh"), "gio_dat": g("dat_gio"), "trong": g("dat_trong")}


def ror(t, y, i, cua=20):
    m = (t <= t[i]) & (t > t[i] - cua)
    return 60 * np.polyfit(t[m], y[m], 1)[0] if m.sum() >= 5 else float("nan")


def thao_tac(d):
    u = np.stack([d["n"], d["l"], d["gio_dat"], d["trong"]], 1)
    doi = [i for i in range(1, len(u)) if (u[i] != u[i - 1]).any()]
    nhom = []
    for i in doi:
        if nhom and d["t"][i] - d["t"][nhom[-1][-1]] <= 4:
            nhom[-1].append(i)
        else:
            nhom.append([i])
    return [(g[0] - 1, g[-1]) for g in nhom]


def main():
    pos, opt = hq._tach_opt(sys.argv[1:])
    d = doc(pos[0])
    dich, dai = float(opt.get("dich", 200)), float(opt.get("dai", 1.5))
    t, bt, et, bu = d["t"], d["bt"], d["et"], d["buong"]
    tt = thao_tac(d)
    i_cham = next((i for i in range(len(bt)) if bt[i] >= dich), None)
    print("## Thao tác của anh")
    print("| # | giờ | t | đổi (Nhiệt/Lệnh/gió/trống) | BT | ET | buồng | RoR BT 20 s | cách đích | giây tới khi chạm %.0f |" % dich)
    print("|---|---|---|---|---|---|---|---|---|---|")
    for k, (a, b) in enumerate(tt, 1):
        tr = "%d/%d/%d/%d → %d/%d/%d/%d" % (d["n"][a], d["l"][a], d["gio_dat"][a], d["trong"][a],
                                            d["n"][b], d["l"][b], d["gio_dat"][b], d["trong"][b])
        con = "%+.0f" % (t[i_cham] - t[b]) if i_cham is not None else "—"
        print("| %d | %s | %.0f | %s | %.1f | %.1f | %.1f | %+.1f | %+.1f | %s |" % (
            k, d["gio"][b], t[b], tr, bt[b], et[b], bu[b], ror(t, bt, b), bt[b] - dich, con))
    if not tt:
        print("(không có thao tác)")
        return
    i0 = tt[0][1]
    trong = np.abs(bt - dich) <= dai
    i_vao = next((i for i in range(i0, len(bt)) if trong[i]), None)
    i_len = next((i for i in range(i0, len(bt)) if bt[i] > bt[i0] + 0.5), None)
    print("\n## Đáp ứng")
    print("- trễ BT (từ thao tác 1 tới BT +0,5): %s s · ET: %s s · buồng: %s s" % tuple(
        ("%.0f" % (t[j] - t[i0]) if j is not None else "—") for j in (
            i_len, next((i for i in range(i0, len(et)) if et[i] > et[i0] + 0.5), None),
            next((i for i in range(i0, len(bu)) if bu[i] > bu[i0] + 0.5), None))))
    if i_vao is not None:
        sau = slice(i_vao, None)
        jm = i_vao + int(np.argmax(bt[sau]))
        print("- vào dải %.0f ± %.1f lúc %s (t %.0f, %.0f s sau thao tác 1) · BT max sau đó %.1f lúc %s (vọt %+.1f so %.0f, %+.1f so mép dải)" % (
            dich, dai, d["gio"][i_vao], t[i_vao], t[i_vao] - t[i0], bt[jm], d["gio"][jm], bt[jm] - dich, dich, bt[jm] - dich - dai))
        run, bd, best = 0, None, (0, None)
        for i in range(i_vao, len(bt)):
            if trong[i]:
                bd = t[i] if bd is None else bd
                if t[i] - bd > best[0]:
                    best = (t[i] - bd, bd)
            else:
                bd = None
        print("- giữ liên tục dài nhất %.0f s (từ t %.0f) · BT min sau vào dải %.1f · BT cuối %.1f" % (
            best[0], best[1] or 0, bt[sau].min(), bt[-1]))
    giam = [(a, b) for a, b in tt if d["n"][b] < d["n"][a] or d["l"][b] < d["l"][a]]
    if giam:
        a, b = giam[0]
        print("- HÃM lần đầu lúc %s: Nhiệt %d → %d · BT %.1f · RoR %+.1f °C/ph · cách đích %.1f °C · %s s trước khi chạm %.0f" % (
            d["gio"][b], d["n"][a], d["n"][b], bt[b], ror(t, bt, b), dich - bt[b],
            "%.0f" % (t[i_cham] - t[b]) if i_cham is not None else "—", dich))
    mpc(d, i0, dich, dai)
    ban_sao(d, i0)


def mpc(d, i0, dich, dai):
    """Phát lại bộ quan sát trên log; mỗi 2 s hỏi BamDuong 'em sẽ chọn gì' (rồi ép lệnh về đúng lệnh anh)."""
    t, bt, et, bu = d["t"], d["bt"], d["et"], d["buong"]
    g = h3.BamDuong()
    g.ki_bam = 0.0
    g.ref_tuong_lai, g.dai = (lambda s: dich), dai
    g.bat_dau(t[i0], bt[i0], et[i0], bu[i0], (d["n"][i0], d["l"][i0]))
    print("\n## MPC (BamDuong) trên cùng trạng thái — mỗi 10 s")
    print("| giờ | BT | RoR | anh | MPC chọn | kế hoạch MPC |")
    print("|---|---|---|---|---|---|")
    ham_mpc = None
    for i in range(i0, len(t)):
        g.cap_nhat(t[i], bt[i], et[i], bu[i])
        g.t_doi_nhiet = g.t_doi_lenh = -1e9
        u_anh = (float(d["n"][i]), float(d["l"][i]))
        g.u = u_anh
        u = g.quyet_dinh(float(int(t[i]) // 2 * 2))
        if ham_mpc is None and bt[i] < dich and (u[0] < 100 or not u[1]) and i > i0 + 5:
            ham_mpc = i
        if int(t[i] - t[i0]) % 10 == 0:
            print("| %s | %.1f | %+.1f | %s | %s | %s |" % (d["gio"][i], bt[i], ror(t, bt, i), hq._u(u_anh), hq._u(u), g.ke_hoach))
        g.u = u_anh
        g.lsu[-1] = u_anh
    if ham_mpc is not None:
        print("- MPC HÃM lần đầu (chọn < 100 %%) lúc %s: BT %.1f · RoR %+.1f · cách đích %.1f" % (
            d["gio"][ham_mpc], bt[ham_mpc], ror(t, bt, ham_mpc), dich - bt[ham_mpc]))


def ban_sao(d, i0):
    """Vòng hở: bản sao số chạy với ĐÚNG lệnh anh từ trạng thái lúc thao tác 1 — sai số, và (độ nhạy, offset cT) khớp nhất."""
    t, bt, et, bu = d["t"], d["bt"], d["et"], d["buong"]
    p0 = bss.doc_tham_so()
    kq = []
    for nh in (0.75, 0.85, 1.0, 1.1, 1.25):
        for dc in np.arange(-8, 8.1, 1.0):
            p = bss.doi_do_nhay(p0, nh)
            p = dict(p, cT=p["cT"] + dc)
            x = bss.trang_thai_tu_do(p, bt[i0], et[i0], bu[i0], d["n"][i0], d["l"][i0])
            pr = []
            for i in range(i0, len(t)):
                pr.append(x[bss.T])
                x = bss.buoc(p, x, d["n"][i], d["l"][i])
            e = np.array(pr) - bt[i0:]
            kq.append((float(np.sqrt(np.mean(e ** 2))), nh, dc, float(np.max(pr)), e))
    kq.sort(key=lambda r: r[0])
    goc = [r for r in kq if r[1] == 1.0 and r[2] == 0][0]
    print("\n## Bản sao số vòng hở với lệnh của anh")
    print("- tham số hiện tại: RMSE %.2f °C · BT max dự báo %.1f (thật %.1f) · sai số ở 60/120/240 s: %s" % (
        goc[0], goc[3], bt[i0:].max(), " / ".join("%+.1f" % goc[4][k] for k in (60, 120, 240) if k < len(goc[4]))))
    b = kq[0]
    print("- khớp nhất: độ nhạy ×%.2f, offset cT %+.0f °C · RMSE %.2f · BT max dự báo %.1f" % (b[1], b[2], b[0], b[3]))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
