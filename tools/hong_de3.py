# -*- coding: utf-8 -*-
"""Đề 3 (anh Thành 15/10/2026 ~14:20): 5 bài nối tiếp, lái Nhiệt ($M36) + gió ($M35 50–100), trống giữ 100.
Đề + cách chấm: F:\\Artisan\\Profile\\OTL-Hong\\de3_10bai\\DE-BAI.md

    HONG_DUOC_LAI=1 python tools/hong_de3.py chay <thư mục> [--tu 1]   # chạy bài tu..5 nối tiếp, mỗi bài 1 giản đồ
    python tools/hong_de3.py cham <bài 1..5> <file.alog>                # chấm 1 bài từ .alog

Bộ lái = MPC bám ĐƯỜNG THAM CHIẾU (hằng hoặc dốc) trên bản sao số (`ban_sao_so_may_dien`), dùng lại bộ quan sát + chọn mô hình
+ offset tự học của `GiaiDe` (hong_qua_panel). Kế hoạch 2 đoạn (v1 trong τ giây rồi v2), chi phí = Σ (BT dự báo − đường)²
+ phạt ra khỏi dải; nhìn trước qua chỗ chuyển bài (đường bài sau). Gió: chỉ trợ khi Nhiệt đã kịch (kịch 100 mà còn thấp ⇒ gió
giảm; Lệnh tắt mà còn cao ⇒ gió 100). Lớp an toàn độc lập: BT > 245 / ET > 255 / mất số / mã lỗi / cờ PC ⇒ TẮT Lệnh.
"""
import json
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import artisan_ui  # noqa: E402
import ban_sao_so_may_dien as bss  # noqa: E402
import cach_tinh_david as david  # noqa: E402
import hong_qua_panel as hq  # noqa: E402

GAP = 9.0                                   # giây chuyển bài (OFF → ON → START) ước lượng


def _ref_bai(b):
    k = b["kieu"]
    if k == "giu":
        return lambda t: b["dich"]
    return lambda t: b["dau"] + b["ror"] * max(0.0, t) / 60.0


BAI0 = {"so": 0, "ten": "Chuẩn bị 215 (không chấm)", "kieu": "giu", "dich": 215.0, "dai": 1.5, "han": 240, "giu": 4, "vao": 240}
BAI = [
    {"so": 1, "ten": "Giữ điểm", "kieu": "giu", "dich": 200.0, "dai": 1.5, "han": 180, "giu": 60, "vao": 180},
    {"so": 2, "ten": "Bậc lên", "kieu": "giu", "dich": 205.0, "dai": 1.5, "han": 90, "giu": 30, "vao": 60},
    {"so": 3, "ten": "Dốc lên", "kieu": "doc", "dau": 205.0, "ror": 5.0, "dai": 1.5, "han": 120},
    {"so": 4, "ten": "Dốc xuống", "kieu": "doc", "dau": 215.0, "ror": -8.0, "dai": 2.0, "han": 150},
    {"so": 5, "ten": "Giữ chặt", "kieu": "giu", "dich": 195.0, "dai": 1.0, "han": 120, "giu": 60, "vao": 120},
]
for _b in BAI:
    _b["ref"] = _ref_bai(_b)


# ── chấm từ .alog theo DE-BAI.md ─────────────────────────────────────────────────────────────
def cham(b, duong):
    ts, bts, _, _ = hq.doc_alog(duong)
    t = np.array(ts)
    bt = np.array(bts)
    m = (t >= 0) & (t <= b["han"] + 0.5)
    t, bt = t[m], bt[m]
    ref = np.array([b["ref"](x) for x in t])
    e = bt - ref
    trong = np.abs(e) <= b["dai"] + 1e-9
    kq = {"bai": b["so"], "alog": duong, "so_mau": int(len(t)), "dai_giay": float(t[-1] - t[0]) if len(t) else 0}
    if b["kieu"] == "doc":
        ti_le = float(trong.mean()) if len(t) else 0.0
        kq.update(ti_le=round(ti_le, 3), diem=round(min(10.0, 10 * ti_le / 0.9), 1),
                  lech_max=round(float(np.max(np.abs(e))) if len(t) else 0, 2))
        return kq
    giu_max, bd = 0.0, None
    for i in range(len(t)):
        if trong[i]:
            bd = t[i] if bd is None else bd
            giu_max = max(giu_max, t[i] - bd)
        else:
            bd = None
    vao = float(t[np.argmax(trong)]) if trong.any() else None
    lo = tut = 0.0
    if vao is not None:
        sau = t >= vao
        lo = float(max(0.0, np.max(e[sau]) - b["dai"]))
        tut = float(max(0.0, np.max(-e[sau]) - b["dai"]))
    diem = 10 * min(1.0, giu_max / b["giu"])
    if vao is None or vao > b["vao"]:
        diem -= 2
    tru = math.ceil(max(lo, tut) / 0.5 - 1e-9) if max(lo, tut) > 0 else 0
    diem = max(0.0, diem - tru)
    kq.update(vao=vao, giu_max=round(giu_max, 1), lo=round(lo, 2), tut=round(tut, 2), tru_lo=tru, diem=round(diem, 1))
    return kq


def dong_ket_qua(b, kq):
    f = os.path.basename(kq["alog"])
    if b["kieu"] == "doc":
        return "| %d %s | %s | **%.1f** | — | lệch lớn nhất %.2f °C | %.0f %% mẫu trong ±%.1f (%d mẫu, %.0f s) |" % (
            b["so"], b["ten"], f, kq["diem"], kq["lech_max"], 100 * kq["ti_le"], b["dai"], kq["so_mau"], kq["dai_giay"])
    return "| %d %s | %s | **%.1f** | %.1f s | lố %.2f / tụt %.2f (trừ %d) | vào dải %s s (hạn %d) · %d mẫu |" % (
        b["so"], b["ten"], f, kq["diem"], kq["giu_max"], kq["lo"], kq["tut"], kq["tru_lo"],
        "%.0f" % kq["vao"] if kq["vao"] is not None else "—", b["vao"], kq["so_mau"])


# ── bộ lái: MPC bám đường ────────────────────────────────────────────────────────────────────
class BamDuong(hq.GiaiDe):
    LUOI = [(float(n), 1.0) for n in range(0, 101, 2)] + [(0.0, 0.0)]
    TAU = (8, 16, 30)

    def __init__(self, tam=90, **kw):
        super().__init__(moc=(200.0,), tam=tam, **kw)
        self._gan = False
        self.bias, self.ki_bam = 0.0, float(os.environ.get("HONG_KI_BAM", "0.03"))
        self.ref_tuong_lai = lambda s: 200.0          # s = giây tính từ BÂY GIỜ
        self.dai = 1.5
        U = []
        for v in self.LUOI:
            u = np.empty((tam, 2))
            u[:] = v
            U.append(u)
        for v1 in self.LUOI:
            for tau in self.TAU:
                for v2 in self.LUOI:
                    if v2 == v1:
                        continue
                    u = np.empty((tam, 2))
                    u[:tau] = v1
                    u[tau:] = v2
                    U.append(u)
        for v in self.LUOI[:-1]:                       # kế hoạch DỐC Nhiệt: v + r·s (bám đường dốc cần lệnh dốc)
            for r in (-0.4, -0.25, -0.15, -0.08, 0.08, 0.15, 0.25, 0.4):
                u = np.empty((tam, 2))
                u[:, 0] = np.clip(v[0] + r * np.arange(tam), 0, 100)
                u[:, 1] = 1.0
                U.append(u)
        self.U = np.stack(U)

    def dang_giu(self):
        return self._gan

    def cap_nhat(self, t, bt, et, buong):
        e0 = bt - self.ref_tuong_lai(0)
        self._gan = abs(e0) <= 1.5
        if abs(e0) < 4:                                # tích phân sai số bám (sim: mô hình đúng vẫn lệch +3 ở dốc lên)
            self.bias = float(np.clip(self.bias + self.ki_bam * e0, -6, 6))
        self.x = bss.buoc_quan_sat(self.P, self.x, self.lsu[-1 - self.tre], bt, et, buong)
        self._chon_mo_hinh(bt)

    def quyet_dinh(self, t):
        if int(round(t)) % 2:
            self.lsu.append(self.u)
            return self.u
        P = {k: v[[self.chon]] for k, v in self.P.items()}
        x = self.x[[self.chon]]
        for u in self.lsu[len(self.lsu) - self.tre:]:
            x = bss._buoc_k(P, x, u)
        U, H = self.U, self.tam
        N = U.shape[0]
        X = np.repeat(x[:, None, :], N, 1)
        BT = np.empty((N, H))
        for s in range(H):
            X = bss.buoc(P, X, U[None, :, s, 0], U[None, :, s, 1])
            BT[:, s] = X[0, :, bss.T]
        ref = np.array([self.ref_tuong_lai(s + 1 + self.tre) for s in range(H)]) - self.bias
        e = BT - ref[None, :]
        w = np.ones(H)
        w[:8] = 0.3                                    # vài giây đầu gần như không đổi được (trễ VX4)
        ra = np.maximum(np.abs(e) - (self.dai - 0.5), 0)
        gia = (w * e ** 2).sum(1) / H + 40 * (w * ra ** 2).sum(1) / H
        # đổi lệnh: phạt nhẹ, cấm đổi Nhiệt < 4 s, đổi Lệnh < 6 s
        dau = U[:, 0, :]
        doi_n = dau[:, 0] != self.u[0]
        doi_l = dau[:, 1] != self.u[1]
        gia = gia + 0.02 * doi_n + 0.2 * doi_l
        if t - self.t_doi_nhiet < 4:
            gia = gia + 1e6 * (doi_n & (dau[:, 1] == 1) & (self.u[1] == 1))
        if t - self.t_doi_lenh < 6:
            gia = gia + 1e6 * doi_l
        j = int(np.argmin(gia))
        u = (float(U[j, 0, 0]), float(U[j, 0, 1]))
        self.ke_hoach = "u %s · e0 %+.2f · bias %+.2f · lệch %+.1f · mô hình %.2f" % (hq._u(u), float(e[j, 10]), self.bias, float(self.dT[self.chon, 0]),
                                                                        self.NHAY[self.chon])
        if u != self.u:
            if u[1] != self.u[1]:
                self.t_doi_lenh = t
            if u[0] != self.u[0]:
                self.t_doi_nhiet = t
            self.u = u
        self.lsu.append(self.u)
        del self.lsu[:-(self.tre + self.tam_chon + 4)]
        return self.u


# ── chạy nối tiếp ────────────────────────────────────────────────────────────────────────────
def _chuyen_artisan(lan_dau):
    """OFF (lưu bài trước) → ON → START. Trả thời điểm START (time.time())."""
    w = artisan_ui._cua_so(3)
    st = w.ButtonControl(Name="START", searchDepth=12)
    if not lan_dau or not (w.ButtonControl(Name="OFF", searchDepth=12).Exists(0.5) and st.Exists(0.5) and st.IsEnabled):
        if w.ButtonControl(Name="OFF", searchDepth=12).Exists(0.5):
            artisan_ui._bam(w, "OFF")
        # 15/10 14:38: Artisan 4.0.2 sau OFF (đang ghi) có lúc vẫn ON, START sáng lại — không hiện nút ON
        t = time.time()
        while time.time() - t < 20:
            if w.ButtonControl(Name="ON", searchDepth=12).Exists(0.3):
                artisan_ui._bam(w, "ON")
                break
            if st.Exists(0.3) and st.IsEnabled:
                break
            time.sleep(0.3)
        t = time.time()
        while not (st.Exists(0.3) and st.IsEnabled) and time.time() - t < 10:
            time.sleep(0.3)
        time.sleep(0.5)
    st.GetInvokePattern().Invoke()
    t0 = time.time()
    artisan_ui._tra_man_hinh(w, None)
    return t0


def _alog_moi(truoc, cho=25):
    t = time.time()
    while time.time() - t < cho:
        moi = [p for p in os.listdir(artisan_ui.THU_MUC_LUU) if p.endswith(".alog")]
        moi = [os.path.join(artisan_ui.THU_MUC_LUU, p) for p in moi]
        moi = [p for p in moi if truoc.get(p) != os.path.getmtime(p)]
        if moi:
            return max(moi, key=os.path.getmtime)
        time.sleep(0.5)
    return None


def _anh_alog():
    d = artisan_ui.THU_MUC_LUU
    return {os.path.join(d, p): os.path.getmtime(os.path.join(d, p)) for p in os.listdir(d) if p.endswith(".alog")}


def chay(thu_muc, tu=1):
    if os.environ.get("HONG_DUOC_LAI") != "1":
        sys.exit("Chưa có quyền lái (HONG_DUOC_LAI=1).")
    os.makedirs(thu_muc, exist_ok=True)
    nk = open(os.path.join(thu_muc, "chay.txt"), "a", encoding="utf-8")

    def in_ra(s):
        dong = time.strftime("%H:%M:%S ") + s
        print(dong, flush=True)
        nk.write(dong + "\n")
        nk.flush()

    p, art = hq.Panel(), hq.ArtisanThat()
    ok, ly = art.kiem() if art.dang_on() else (art.bat_on() and art.kiem())
    in_ra("ARTISAN: %s" % (ly,))
    if not ok:
        return
    d = p.doc_tat_ca()
    loi = hq.tu_kiem(d, None)
    if loi:
        in_ra("DUNG: " + "; ".join(loi))
        return
    if int(d["dat_trong"]) != 100:
        p.dat_trong(100)
    gio_nen = 100
    if int(d["dat_gio"]) != gio_nen:
        p.dat_gio(gio_nen)
    gio = gio_nen
    giai = BamDuong()
    T0 = time.time()
    giai.bat_dau(0.0, d["bt"], d["et"], d["buong"], (d["dat_nhiet"], d["lenh_nhiet"]))
    in_ra("NHAN QUYEN · BT %.1f ET %.1f buong %s · Nhiet %d%% Lenh %d gio %d" % (
        d["bt"], d["et"], d["buong"], d["dat_nhiet"], d["lenh_nhiet"], d["dat_gio"]))
    f = open(os.path.join(thu_muc, "log.csv"), "a", encoding="utf-8")
    f.write("gio,t,bai,tb,ref,bt,et,buong,nhiet,lenh,gio_dat,ke_hoach\n")
    lich = [b for b in BAI if b["so"] >= tu]
    if os.environ.get("HONG_CHUAN_BI_215") == "1":     # 14:45: chạy lại bài 4 cần BT 215 lúc START — bước chuẩn bị có giản đồ riêng
        BAI0["ref"] = _ref_bai(BAI0)
        lich = [BAI0] + lich
    ket, ly_do, t_ok = [], "xong", time.time()
    gio_bai1 = None
    try:
        for ib, b in enumerate(lich):
            truoc = _anh_alog()
            t_start = _chuyen_artisan(ib == 0)
            gio_bai1 = gio_bai1 or time.strftime("%H:%M:%S", time.localtime(t_start))
            time.sleep(2)
            ok, ct = art.dang_ghi(cho=2.0)
            in_ra("BAI %d %s · START %s · Artisan dang ghi: %s" % (b["so"], b["ten"], time.strftime("%H:%M:%S",
                                                                                          time.localtime(t_start)), ct))
            # 14:44: bài 4 START vừa xong, đường BT mới 5 điểm ảnh ⇒ dang_ghi False dù START đã vô hiệu + đồng hồ chạy
            ok = ok or ("vô hiệu" in ct and "đồng hồ chạy" in ct)
            if not ok and not art.bam_start():
                ly_do = "Artisan không ghi"
                break
            sau = lich[ib + 1] if ib + 1 < len(lich) else None
            giu_dem, t_bd = 0.0, None
            while True:
                now = time.time()
                tb = now - t_start
                if tb > b["han"]:
                    break
                try:
                    d = p.doc_tat_ca()
                    t_ok = now
                except (OSError, ValueError):
                    if now - t_ok > hq.MAT_SO_GIAY:
                        ly_do = "mất số panel"
                        raise StopIteration
                    time.sleep(0.5)
                    continue
                if d["bt"] > hq.BT_TUYET_DOI or d["et"] > hq.ET_MAX:
                    ly_do = "AN TOAN BT %.1f ET %.1f" % (d["bt"], d["et"])
                    raise StopIteration
                loi = hq.tu_kiem(d, None)
                if loi:
                    ly_do = "TU KIEM: " + "; ".join(loi)
                    raise StopIteration
                ref0 = b["ref"](tb)
                # kết thúc sớm bài giữ khi đã giữ đủ (+8 s lề), theo số panel (dải hẹp hơn 0,3)
                if b["kieu"] == "giu":
                    if abs(d["bt"] - ref0) <= b["dai"] - 0.3:
                        t_bd = t_bd or now
                        giu_dem = now - t_bd
                    else:
                        t_bd, giu_dem = None, 0.0
                    if giu_dem >= b["giu"] + 8:
                        break
                    con = (b["giu"] + 8 - giu_dem) if t_bd else (b["han"] - tb)
                    het_du = min(b["han"] - tb, con)
                else:
                    het_du = b["han"] - tb

                def ref_tl(s, b=b, tb=tb, het_du=het_du, sau=sau):
                    if s <= het_du or sau is None or sau["kieu"] == "giu":   # bài sau là bài giữ: KHÔNG nhìn trước (sim: vọt sớm 4 °C)
                        return b["ref"](tb + s)
                    return sau["ref"](s - het_du - GAP)

                giai.ref_tuong_lai, giai.dai = ref_tl, b["dai"]
                t = now - T0
                giai.cap_nhat(t, d["bt"], d["et"], d["buong"])
                u_cu = giai.u
                u = giai.quyet_dinh(t)
                if u != u_cu:
                    if u[1]:
                        p.dat_nhiet(u[0])
                    if u[1] != u_cu[1]:
                        p.lenh_nhiet(bool(u[1]))
                # gió trợ khi Nhiệt đã kịch
                e = d["bt"] - ref0
                g_moi = gio
                if u == (100.0, 1.0) and e < -1.0:
                    g_moi = 60
                elif e > -0.3:
                    g_moi = gio_nen
                if g_moi != gio:
                    p.dat_gio(g_moi)
                    gio = g_moi
                    in_ra("  gio -> %d (BT %.1f ref %.1f)" % (gio, d["bt"], ref0))
                f.write("%s,%.1f,%d,%.1f,%.2f,%.1f,%.1f,%s,%.0f,%d,%d,%s\n" % (
                    time.strftime("%H:%M:%S"), t, b["so"], tb, ref0, d["bt"], d["et"], d["buong"], u[0], u[1], gio,
                    giai.ke_hoach))
                f.flush()
                if int(tb) % 15 == 0 and tb - int(tb) < 1.0:
                    in_ra("  b%d %4.0f s BT %.1f ref %.1f · %s" % (b["so"], tb, d["bt"], ref0, giai.ke_hoach))
                time.sleep(max(0.0, 1.0 - (time.time() - now)))
            # chuyển bài: Artisan OFF (lưu) nằm trong _chuyen_artisan của bài sau; bài cuối OFF ở đây
            if sau is None:
                w = artisan_ui._cua_so(3)
                artisan_ui._bam(w, "OFF")
            ket.append((b, truoc, time.time()))
            in_ra("BAI %d het · %.0f s" % (b["so"], time.time() - t_start))
            if sau is not None:
                # tìm .alog của bài vừa xong SAU khi bài sau đã START (không chặn lái)
                pass
    except StopIteration:
        pass
    except Exception as ex:                             # noqa: BLE001 — lỗi code: TẮT nhiệt trước, báo sau
        ly_do = "LOI CODE: %r" % ex
    finally:
        p.lenh_nhiet(False)                             # hết đề / dừng / lỗi: luôn TẮT Lệnh nhiệt
        f.close()
    in_ra("KET THUC: %s · bai 1 START %s · het %s" % (ly_do, gio_bai1, time.strftime("%H:%M:%S")))
    if ly_do != "xong":
        try:
            artisan_ui._bam(artisan_ui._cua_so(3), "OFF")
        except Exception as ex:  # noqa: BLE001
            in_ra("Artisan OFF lỗi: %s" % ex)
    nk.close()
    return ly_do


def cham_thu_muc(thu_muc_alog_list):
    out = []
    for so, duong in thu_muc_alog_list:
        b = BAI[so - 1]
        kq = cham(b, duong)
        out.append((b, kq))
    return out


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    lenh, (pos, opt) = sys.argv[1], hq._tach_opt(sys.argv[2:])
    if lenh == "chay":
        chay(pos[0], tu=int(opt.get("tu", 1)))
    elif lenh == "cham":
        b = BAI[int(pos[0]) - 1]
        kq = cham(b, pos[1])
        print(json.dumps(kq, ensure_ascii=False))
        print(dong_ket_qua(b, kq))
        print(david.tom_tat(david.phan_tich(pos[1])))
    elif lenh == "thoi_gian":
        g = BamDuong()
        d = {"bt": 200, "et": 215, "buong": 300}
        g.bat_dau(0, 200, 215, 300, (45, 1))
        t = time.time()
        for i in range(4):
            g.cap_nhat(i * 2, 200, 215, 300)
            g.quyet_dinh(i * 2)
        print("quyet_dinh %.3f s/lần · %d kế hoạch · %s" % ((time.time() - t) / 4, g.U.shape[0], g.ke_hoach))
