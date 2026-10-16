# -*- coding: utf-8 -*-
"""CHỈ ĐỌC: quan sát MẺ RANG anh Thành tự lái, so với đích mốc (agent OTL Hồng, 15/10/2026). Không ghi thanh ghi nào,
trừ an toàn tuyệt đối BT > 245 / ET > 255 ⇒ gọi `hong_qua_panel.an_toan` (luật cứng, luôn được).

    python tools/hong_quan_sat_me.py <thư mục> [--de 240 --fcs 540 --drop 780 --dev 240 --phut 100]

Ra trong <thư mục>: log.csv (1 Hz) · trang_thai.txt (mốc CHARGE / TP / DE / FCs / DROP so đích, mỗi thao tác của anh,
mỗi 60 s một dòng DỰ BÁO chỉ để tham khảo) · moc.json (mốc cuối cùng, dùng cho bảng sau mẻ).
Mốc lấy từ firmware ($69–$77 TP/DE/FCs, $81 BT charge, $939 đã xả, $67/$68 giờ rang); thiếu thì tự nhận từ BT.
Dừng: DROP + 3 phút · quá --phut · file <thư mục>/dung xuất hiện."""
import json
import os
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hong_qua_panel as hq  # noqa: E402

DUOI_ROR = 30          # giây hồi quy RoR (như cột k_david của log lượt)
DIEN_DU_BAO = 60       # giây giữa hai dòng dự báo


def s16(v):
    return v - 65536 if v >= 32768 else v


def mmss(s):
    s = int(round(s))
    return "%s%d:%02d" % ("-" if s < 0 else "", abs(s) // 60, abs(s) % 60)


def lech(s, dich):
    d = int(round(s - dich))
    return "%s%ds" % ("+" if d >= 0 else "", d)


DONG_3S = 3.0          # anh Thành 16/10: phân tích LIÊN TỤC mỗi 3 s ⇒ phan_tich_3s.csv
COT_3S = ("gio,t_rang,bt,et,dbt,det,k_david,dry_s,dry_pct,ramp_s,ramp_pct,dev_s,dtr_pct,auc,du_bao_de,du_bao_fcs,"
          "du_bao_drop,lech_de,lech_fcs,lech_drop,nhiet,gio_dat,trong_dat")


def chi_so(t, bt, et, moc, moc_bt, now, dich, bt_fcs=194.0, bt_de=155.0, span=20.0):
    """Các số Artisan hiện (đối chiếu ca kiểm mẻ 4 lúc 8:54: BT 176,8 · ET 204,5 · ΔBT 9,2 (Artisan 9,1) · ΔET 6,7 (6,6) ·
    AUC 465,7 (464) · »FCs 10:47 (10:47) · DRY 5:29 / 72,8 % (73,0)). Nguồn công thức: .alog Artisan 1745 trường `computed`
    (AUCbegin 'TP', AUCbase = BT lúc TP, phases [70, 155, 194, 232]) + số anh đánh dấu trên màn Artisan 16/10.
      ΔBT/ΔET = hồi quy `span` s cuối (°C/ph) · AUC = ∫(BT − BT_TP)⁺ dt từ TP (°C·ph)
      DRY = DE − TP (đang sấy: now − TP), DRY% = DE / now · RAMP = »FCs − DE (sau FCs: FCs − DE), RAMP% = 100 − DRY% (trước FCs)
      »DE / »FCs = now + (ngưỡng − BT) / ΔBT · DEV = now − FCs, DTR = DEV / now · »DROP = FCs + dev đích (trước FCs: »FCs + dev đích)."""
    m = (t > now - span) & (t <= now)
    if m.sum() < 5:
        return None
    dbt = float(np.polyfit(t[m], bt[m], 1)[0] * 60)
    det = float(np.polyfit(t[m], et[m], 1)[0] * 60)
    b, e = float(bt[m][-1]), float(et[m][-1])
    k = dbt / (e - b) if e - b >= 8 else float("nan")
    tp, de, fcs = moc.get("TP"), moc.get("DE"), moc.get("FCs")
    auc = float("nan")
    if tp is not None:
        s = (t >= tp) & (t <= now)
        auc = float(np.trapezoid(np.clip(bt[s] - moc_bt.get("TP", bt[s][0]), 0, None), t[s]) / 60) if s.sum() > 1 else 0.0
    du = lambda nguong: now + (nguong - b) / dbt * 60 if dbt > 0.5 and b < nguong else float("nan")  # noqa: E731
    p_de = de if de is not None else du(bt_de)
    p_fcs = fcs if fcs is not None else du(bt_fcs)
    p_drop = (fcs if fcs is not None else p_fcs) + dich["dev"]
    dry_s = (de - tp) if (de is not None and tp is not None) else ((now - tp) if tp is not None else float("nan"))
    dry_pct = 100 * (de if de is not None else now) / now
    ramp_s = (fcs - de) if (fcs is not None and de is not None) else ((p_fcs - de) if de is not None else float("nan"))
    ramp_pct = (100 * (fcs - de) / now) if (fcs is not None and de is not None) else (100 - dry_pct if de is not None else 0.0)
    dev_s = now - fcs if fcs is not None else float("nan")
    dtr = 100 * dev_s / now if fcs is not None else float("nan")
    return dict(dbt=dbt, det=det, bt=b, et=e, k=k, dry_s=dry_s, dry_pct=dry_pct, ramp_s=ramp_s, ramp_pct=ramp_pct, dev_s=dev_s,
                dtr=dtr, auc=auc, p_de=p_de, p_fcs=p_fcs, p_drop=p_drop, l_de=p_de - dich["de"], l_fcs=p_fcs - dich["fcs"],
                l_drop=p_drop - dich["drop"])


def dong_3s(gio, now, c, nhiet, gio_dat, trong_dat):
    f = lambda v, fm="%.1f": "" if v != v else fm % v  # noqa: E731
    return ",".join([gio, "%.0f" % now, f(c["bt"]), f(c["et"]), f(c["dbt"]), f(c["det"]), f(c["k"], "%.4f"),
                     f(c["dry_s"], "%.0f"), f(c["dry_pct"]), f(c["ramp_s"], "%.0f"), f(c["ramp_pct"]), f(c["dev_s"], "%.0f"),
                     f(c["dtr"]), f(c["auc"], "%.0f"), f(c["p_de"], "%.0f"), f(c["p_fcs"], "%.0f"), f(c["p_drop"], "%.0f"),
                     f(c["l_de"], "%+.0f"), f(c["l_fcs"], "%+.0f"), f(c["l_drop"], "%+.0f"), "%g" % nhiet, "%g" % gio_dat,
                     "%g" % trong_dat])


def lai_3s(tm, dich):
    """Dựng phan_tich_3s.csv từ log.csv + moc.json có sẵn (mẻ đã xong) — cùng công thức với vòng sống."""
    import csv
    R = [r for r in csv.DictReader(open(os.path.join(tm, "log.csv"), encoding="utf-8")) if r["t_rang"]]
    mj = json.load(open(os.path.join(tm, "moc.json"), encoding="utf-8"))
    t = np.array([float(r["t_rang"]) for r in R])
    bt = np.array([float(r["bt"]) for r in R])
    et = np.array([float(r["et"]) for r in R])
    het = mj["moc_giay"].get("DROP", t[-1])
    with open(os.path.join(tm, "phan_tich_3s.csv"), "w", encoding="utf-8") as f:
        f.write(COT_3S + "\n")
        for now in np.arange(DONG_3S * 3, het + 0.1, DONG_3S):
            moc = {k: v for k, v in mj["moc_giay"].items() if v is not None and v <= now}
            c = chi_so(t, bt, et, moc, mj["moc_bt"], now, dich, mj.get("nguong_fcs", 194), mj.get("nguong_de", 155))
            if c:
                i = int(np.argmin(np.abs(t - now)))
                f.write(dong_3s(R[i]["gio"], now, c, float(R[i]["nhiet"]), float(R[i]["dat_gio"]),
                                float(R[i]["dat_trong"])) + "\n")
    return os.path.join(tm, "phan_tich_3s.csv")


class QuanSat:
    def __init__(self, tm, dich, phut):
        self.tm, self.dich, self.phut = tm, dich, phut
        os.makedirs(tm, exist_ok=True)
        self.p = hq.Panel()
        self.f_tt = open(os.path.join(tm, "trang_thai.txt"), "a", encoding="utf-8")
        duong = os.path.join(tm, "log.csv")
        moi = not os.path.exists(duong)
        self.f = open(duong, "a", encoding="utf-8")
        if moi:
            self.f.write("gio,t_rang,bt,et,buong,ror_bt,k_david,dat_nhiet,nhiet,lenh,dat_gio,gio_pv,dat_trong,trong_hz,"
                         "ma,man,start,fw_phut,fw_giay\n")
        self.lich = []                     # (giờ máy tính, bt, et)
        self.moc = {}                      # tên -> giây rang
        self.moc_bt = {}
        self.t_charge = None
        self.cu = None
        self.t_du_bao = 0.0
        self.m3, self.t3, self.f3, self.nhan_dinh_cu = [], 0.0, None, None
        m = self.p.doc(2020, 2)            # $M20 ngưỡng DE, $M21 ngưỡng FCs (°C, firmware)
        self.nguong_de, self.nguong_fcs = float(m[0] or 155), float(m[1] or 194)

    def ghi(self, dong):
        line = "%s %s" % (time.strftime("%H:%M:%S"), dong)
        self.f_tt.write(line + "\n")
        self.f_tt.flush()
        print(line, flush=True)

    def ror(self, now):
        ds = [(t, b) for t, b, _ in self.lich if now - t <= DUOI_ROR]
        if len(ds) < 10:
            return float("nan")
        t, b = np.array(ds).T
        return float(np.polyfit(t - t[-1], b, 1)[0] * 60.0)

    def ror_xu_huong(self, now):
        """Độ dốc của RoR (°C/ph mỗi phút) trên 120 s gần nhất — để dự báo RoR giảm dần."""
        ds = [(t, b) for t, b, _ in self.lich if now - t <= 120]
        if len(ds) < 60:
            return 0.0
        t, b = np.array(ds).T
        a = np.polyfit((t - t[-1]) / 60.0, b, 2)        # BT = a0 x² + a1 x + a2 ⇒ RoR' = 2 a0 (°C/ph²)
        return float(2 * a[0])

    def t_rang(self, now, fw):
        if self.t_charge is None:
            return None
        if fw[0] or fw[1]:
            return fw[0] * 60 + fw[1]
        return now - self.t_charge

    def doc(self):
        r = self.p.doc(0, 100)
        m = self.p.doc(2034, 3)
        x = self.p.doc(930, 10)
        return r, m, x

    def an_toan_neu_can(self, bt, et):
        if bt > hq.BT_TUYET_DOI or et > hq.ET_MAX:
            self.ghi("⛔ AN TOÀN TUYỆT ĐỐI: BT %.1f / ET %.1f vượt 245 / 255 ⇒ Hồng chạy an_toan (tắt nhiệt + làm mát)" % (bt, et))
            subprocess.Popen([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "hong_qua_panel.py"),
                              "an_toan", "--csv", os.path.join(self.tm, "an_toan.csv")])
            return True
        return False

    def thao_tac(self, now, r, m, bt, tr):
        dk = (m[2], r[1], m[1], m[0])      # đặt Nhiệt, Lệnh, đặt gió, đặt trống
        if self.cu is not None and dk != self.cu:
            ten = ("Nhiệt", "Lệnh", "gió", "trống")
            doi = " · ".join("%s %s→%s%s" % (ten[i], self.cu[i], dk[i], "" if i == 1 else " %")
                             for i in range(4) if dk[i] != self.cu[i])
            self.ghi("THAO TÁC (anh hoặc bộ lái Hồng): %s · lúc %s · BT %.1f · RoR %+.1f °C/ph" % (
                doi, mmss(tr) if tr is not None else "trước charge", bt, self.ror(now)))
        self.cu = dk

    def nhan_moc(self, now, r, x, bt, tr):
        fw_moc = {"TP": (r[69], r[70], r[71]), "DE": (r[72], r[73], r[74]), "FCs": (r[75], r[76], r[77])}
        # CHARGE: firmware ghi BT charge ($81) hoặc BT rơi ≥ 25 °C trong 30 s
        if self.t_charge is None:
            ds = [b for t, b, _ in self.lich if now - t <= 30]
            rot = (max(ds) - bt) if ds else 0.0
            if r[81] > 0 or (rot >= 25 and max(ds) > 120):
                self.t_charge = now - (r[67] * 60 + r[68] if (r[67] or r[68]) else 0)
                self.moc["CHARGE"] = 0.0
                self.moc_bt["CHARGE"] = r[81] / 10 if r[81] else max(ds)
                self.ghi("MỐC CHARGE · BT charge %.1f · buồng %.1f · Nhiệt %d %% · gió %d %% (giờ rang bắt đầu %s)" % (
                    self.moc_bt["CHARGE"], s16(r[96]) / 10, r[66] // 10, r[64] // 10, time.strftime("%H:%M:%S")))
                self.kiem_artisan()
            return
        for ten, (b10, ph, gi) in fw_moc.items():
            if ten not in self.moc and b10:
                s = ph * 60 + gi
                self.moc[ten], self.moc_bt[ten] = s, b10 / 10
                if ten == "TP":
                    self.ghi("MỐC TP %s · BT %.1f" % (mmss(s), b10 / 10))
                elif ten == "DE":
                    self.ghi("MỐC DE %s · BT %.1f · đích 4:00 ⇒ lệch %s" % (mmss(s), b10 / 10, lech(s, self.dich["de"])))
                else:
                    self.ghi("MỐC FCs %s · BT %.1f · đích 9:00 ⇒ lệch %s" % (mmss(s), b10 / 10, lech(s, self.dich["fcs"])))
        if "DROP" not in self.moc:
            ds = [b for t, b, _ in self.lich if now - t <= 30]
            rot = (max(ds) - bt) if ds else 0.0
            if x[9] == 1 or r[82] > 0 or (tr is not None and tr > 360 and rot >= 15):
                s = tr if tr is not None else now - self.t_charge
                self.moc["DROP"] = s
                self.moc_bt["DROP"] = r[82] / 10 if r[82] else max(ds)
                dong = "MỐC DROP %s · BT %.1f · đích 13:00 ⇒ lệch %s" % (mmss(s), self.moc_bt["DROP"], lech(s, self.dich["drop"]))
                if "FCs" in self.moc:
                    dev = s - self.moc["FCs"]
                    dong += " · dev %s (đích ~4:00 ⇒ %s) · DTR %.1f %%" % (mmss(dev), lech(dev, self.dich["dev"]), 100 * dev / s)
                self.ghi(dong)
                self.t_drop = now
        self.luu_moc()

    def du_bao(self, now, bt, tr):
        if tr is None or "TP" not in self.moc or "DROP" in self.moc or now - self.t_du_bao < DIEN_DU_BAO:
            return
        self.t_du_bao = now
        ror = self.ror(now)
        if not ror == ror or ror <= 0.5:
            self.ghi("DỰ BÁO %s · BT %.1f · RoR %+.1f — RoR quá thấp, không dự báo" % (mmss(tr), bt, ror))
            return
        dr = self.ror_xu_huong(now)
        phan = []
        for ten, nguong, dich in (("DE", self.nguong_de, self.dich["de"]), ("FCs", self.nguong_fcs, self.dich["fcs"])):
            if ten in self.moc or bt >= nguong:
                continue
            t1 = tr + (nguong - bt) / ror * 60
            s = "%s (BT %.0f) ~%s (%s)" % (ten, nguong, mmss(t1), lech(t1, dich))
            if dr < 0:                                  # RoR giảm dần theo xu hướng 2 phút
                tt, b, rr = 0.0, bt, ror
                while b < nguong and tt < 1800 and rr > 0.3:
                    b += rr / 60
                    rr += dr / 60
                    tt += 1
                if b >= nguong:
                    s += " · nếu RoR giảm như 2 phút qua: ~%s (%s)" % (mmss(tr + tt), lech(tr + tt, dich))
            phan.append(s)
        if phan:
            self.ghi("DỰ BÁO (tham khảo) %s · BT %.1f · RoR %+.1f (đổi %+.1f/ph) ⇒ %s" % (mmss(tr), bt, ror, dr, " | ".join(phan)))

    def vong_3s(self, now, tr, bt, et, r, m):
        """Mỗi 3 s: số Artisan + k David + dự báo DE/FCs/DROP so đích ⇒ phan_tich_3s.csv. trang_thai.txt chỉ khi nhận định đổi
        (dự báo FCs / DROP lệch đích đổi ≥ 20 s so với lần báo trước) — không spam."""
        if tr is None or "DROP" in self.moc:
            return
        self.m3.append((tr, bt, et))
        if now - self.t3 < DONG_3S:
            return
        self.t3 = now
        a = np.array(self.m3)
        moc = {k: v for k, v in self.moc.items() if v is not None}
        c = chi_so(a[:, 0], a[:, 1], a[:, 2], moc, self.moc_bt, tr, self.dich, self.nguong_fcs, self.nguong_de)
        if not c:
            return
        if self.f3 is None:
            duong = os.path.join(self.tm, "phan_tich_3s.csv")
            moi = not os.path.exists(duong)
            self.f3 = open(duong, "a", encoding="utf-8")
            if moi:
                self.f3.write(COT_3S + "\n")
        self.f3.write(dong_3s(time.strftime("%H:%M:%S"), tr, c, r[66] / 10, m[1], m[0]) + "\n")
        self.f3.flush()
        if "TP" not in self.moc or tr < self.moc["TP"] + 60 or c["l_drop"] != c["l_drop"]:
            return                                      # 60 s đầu sau TP RoR còn đang lên ⇒ dự báo nhảy, không báo
        pha = ("DE" in self.moc, "FCs" in self.moc)
        cu = self.nhan_dinh_cu
        if cu is None or cu[0] != pha or abs(c["l_drop"] - cu[1]) >= 30:   # trễ 30 s: không báo lại khi chỉ dao động
            self.nhan_dinh_cu = (pha, c["l_drop"])
            dong = "NHẬN ĐỊNH %s · BT %.1f · ΔBT %+.1f · k %.3f · AUC %.0f · " % (mmss(tr), c["bt"], c["dbt"], c["k"], c["auc"])
            if "DE" not in self.moc:
                dong += "»DE %s (%s) · " % (mmss(c["p_de"]), lech(c["p_de"], self.dich["de"]))
            if "FCs" not in self.moc:
                dong += "»FCs %s (%s) · " % (mmss(c["p_fcs"]), lech(c["p_fcs"], self.dich["fcs"]))
            else:
                dong += "DEV %s · DTR %.1f %% · " % (mmss(c["dev_s"]), c["dtr"])
            dong += "»DROP %s (%s, = FCs + dev đích 4:00)" % (mmss(c["p_drop"]), lech(c["p_drop"], self.dich["drop"]))
            self.ghi(dong)

    def kiem_artisan(self):
        """Chỉ đọc UIA: START vô hiệu = Artisan đang ghi giản đồ. Không bấm gì (anh đang dùng Artisan)."""
        try:
            import artisan_ui
            w = artisan_ui._cua_so(2)
            if w is None:
                self.ghi("Artisan: KHÔNG thấy cửa sổ — mẻ chỉ có log panel 1 Hz")
                return
            st = w.ButtonControl(Name="START", searchDepth=12)
            if not artisan_ui.co_thanh_nut(w):
                self.ghi("Artisan: thanh nút đang ẩn — không biết đang ghi hay không (em không bấm)")
            elif st.Exists(0.5) and st.IsEnabled:
                self.ghi("Artisan: ĐANG ON nhưng CHƯA START giản đồ — anh bấm START trên Artisan nếu muốn có .alog (em không bấm khi anh đang dùng)")
            else:
                self.ghi("Artisan: đang ghi giản đồ (START vô hiệu)")
        except Exception as e:  # noqa: BLE001 — chỉ báo, không dừng quan sát
            self.ghi("Artisan: không kiểm được (%s)" % e)

    def luu_moc(self):
        with open(os.path.join(self.tm, "moc.json"), "w", encoding="utf-8") as f:
            json.dump({"moc_giay": self.moc, "moc_bt": self.moc_bt, "dich": self.dich,
                       "t_charge_epoch": self.t_charge, "nguong_de": self.nguong_de, "nguong_fcs": self.nguong_fcs},
                      f, ensure_ascii=False, indent=1)

    def chay(self):
        t0 = t_ok = time.time()
        self.t_drop = None
        self.ghi("Hồng QUAN SÁT mẻ (chỉ đọc) · log 1 Hz %s · ngưỡng firmware DE %.0f / FCs %.0f °C" % (
            os.path.join(self.tm, "log.csv"), self.nguong_de, self.nguong_fcs))
        while True:
            now = time.time()
            try:
                r, m, x = self.doc()
                t_ok = now
            except (OSError, ValueError) as e:
                if now - t_ok > 10:
                    self.ghi("MẤT SỐ PANEL > 10 s (%s)" % e)
                    t_ok = now
                time.sleep(1)
                continue
            bt, et, bu = s16(r[60]) / 10, s16(r[61]) / 10, s16(r[96]) / 10
            self.lich.append((now, bt, et))
            self.lich = [z for z in self.lich if now - z[0] <= 130]
            if self.an_toan_neu_can(bt, et):
                break
            tr = self.t_rang(now, (r[67], r[68]))
            self.thao_tac(now, r, m, bt, tr)
            self.nhan_moc(now, r, x, bt, tr)
            tr = self.t_rang(now, (r[67], r[68]))
            self.vong_3s(now, tr, bt, et, r, m)
            ro = self.ror(now)
            k = ro / (et - bt) if (ro == ro and et - bt >= 8) else float("nan")
            self.f.write("%s,%s,%.1f,%.1f,%.1f,%.2f,%.4f,%d,%.1f,%d,%d,%.1f,%d,%.1f,%d,%d,%d,%d,%d\n" % (
                time.strftime("%H:%M:%S"), "" if tr is None else "%.0f" % tr, bt, et, bu, ro, k, m[2], r[66] / 10, r[1],
                m[1], r[64] / 10, m[0], r[84] / 100, r[40], r[21], r[0], r[67], r[68]))
            self.f.flush()
            if self.t_drop and now - self.t_drop >= 180:
                self.ghi("KẾT THÚC quan sát: DROP + 3 phút")
                break
            if now - t0 > self.phut * 60 or os.path.exists(os.path.join(self.tm, "dung")):
                self.ghi("KẾT THÚC quan sát: hết giờ / được báo dừng")
                break
            time.sleep(max(0.0, 1.0 - (time.time() - now)))
        self.luu_moc()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    pos, opt = hq._tach_opt(sys.argv[1:])
    dich = {k: float(opt.get(k, v)) for k, v in (("de", 240), ("fcs", 540), ("drop", 780), ("dev", 240))}
    if opt.get("lai_3s") == "1":
        print(lai_3s(pos[0], dich))
    else:
        QuanSat(pos[0], dich, float(opt.get("phut", 100))).chay()
