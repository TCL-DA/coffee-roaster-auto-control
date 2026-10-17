"""OTL Hồng — vòng chạy mẻ 9: ghép bộ lái LaiMe9 (tools/hong_lai_me9.py) vào máy (panel Modbus TCP) hoặc vào PHÁT LẠI log.

Chỉ MPC, không PID. ⛔ Luật cứng: không CHARGE khi BT < 150 °C (anh Thành 17/10). Tách hai mốc BT_START (lồng, chưa hạt) và BT_CHARGE.
Vòng 1 Hz: đọc máy → an toàn → (chờ CHARGE) → LaiMe9.lenh → ghi Nhiệt / gió khi đổi → DROP ở BT 218 → mỗi 15 s dòng PHÂN TÍCH
có nhãn lỗi RoR (hong_ror_loi, cùng ngưỡng báo cáo 17/10).

Máy thật (CHỈ khi anh cho):  HONG_DUOC_LAI=1 HONG_DUOC_THAO_TAC=1 python tools/hong_chay_me9.py may <thư mục mẻ> --slot 9
    Artisan ON + START trước (artisan_ui.bat_ghi), kiem_truoc_start, chọn slot RANG LƯU, $0 = 1, rồi vòng lái.
Chạy khô (không mở Modbus): python tools/hong_chay_me9.py kho <mẻ 4|5> [--charge_bt 140] [--m23 1400]
"""
import csv
import json
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hong_lai_me9 as L9  # noqa: E402
import hong_ror_loi as H  # noqa: E402

BT_MAX, ET_MAX = 245.0, 255.0
T_MAX = 1080            # 18:00 chưa DROP ⇒ xả
CHO_CHARGE_MAX = 1200   # 20 phút sau START chưa CHARGE ⇒ dừng


def s16(v):
    return v - 65536 if v >= 32768 else v


# ───────────────────────── hai kiểu "máy" cùng giao diện ─────────────────────────
class MayThat:
    """Panel thật. Chỉ tạo khi HONG_DUOC_LAI=1."""
    gia_lap = False

    def __init__(self):
        if os.environ.get("HONG_DUOC_LAI") != "1":
            raise SystemExit("cần HONG_DUOC_LAI=1 (anh Thành cho quyền lái)")
        from hong_qua_panel import Panel
        self.pn = Panel()

    def doc(self):
        r = self.pn.doc(0, 100)
        return dict(bt=s16(r[60]) / 10, et=s16(r[61]) / 10, bu=s16(r[96]) / 10, lenh=r[1], ma=r[40], pc=r[13], man=r[21],
                    fw_t=r[67] * 60 + r[68], start=r[0], m23=self.pn.doc(2023, 1)[0])

    def dat(self, nhiet=None, gio=None):
        if nhiet is not None:
            self.pn.dat_nhiet(nhiet)
            return self.pn.doc(2036, 1)[0]
        if gio is not None:
            self.pn.dat_gio(gio)
            return self.pn.doc(2035, 1)[0]

    def xa(self):
        self.pn.ghi(7, [1])
        v = self.pn.doc(7, 1)[0]
        self.artisan("DROP")
        return v

    def artisan(self, nut):
        """Bấm nút chính Artisan bằng UIA (không chiếm màn hình) — dùng lại hàm của bộ lái mẻ 5–8."""
        import types
        import hong_lai_me_mpc
        hong_lai_me_mpc.LaiMe.bam_artisan(types.SimpleNamespace(ghi=print), nut)

    def an_toan(self):
        self.pn.pc_control(False)
        self.pn.lenh_nhiet(False)
        self.pn.dat_nhiet(0)
        self.pn.dat_gio(100)
        return self.pn.doc(1, 1)[0]

    def ngu(self, s):
        time.sleep(s)


class MayPhatLai:
    """Chạy khô: đọc log 1 Hz của một mẻ cũ thay panel (KHÔNG mở Modbus). Lệnh chỉ ghi lại, không đổi số đo.
    charge_bt: ép BT lúc CHARGE (thử luật 150) · m23: ép ngưỡng auto-charge."""
    gia_lap = True

    def __init__(self, me, charge_bt=None, m23=1700):
        tm = {4: "me_ho_so_4_1610", 5: "me_ho_so_5_1610"}[me]
        r = [x for x in csv.DictReader(open("F:/Artisan/Profile/OTL-Hong/%s/log.csv" % tm, encoding="utf-8")) if x["bt"] not in ("", "nan")]
        self.rows, self.i, self.m23 = r, 0, m23
        self.charge_bt = charge_bt
        if charge_bt is not None:                   # giả lập CHARGE ở BT thấp: hạ 60 dòng trước charge cho đỉnh = charge_bt
            i_ch = next(i for i, x in enumerate(r) if x["t_rang"] != "")
            dau = max(0, i_ch - 60)
            dinh = max(float(x["bt"]) for x in r[dau:i_ch + 1])
            for x in r[dau:i_ch + 3]:
                x["bt"] = str(float(x["bt"]) - (dinh - charge_bt))
        self.lenh_ghi = []
        self.t0 = None

    def doc(self):
        x = self.rows[min(self.i, len(self.rows) - 1)]
        self.i += 1
        fw = (int(float(x["fw_phut"] or 0)) * 60 + int(float(x["fw_giay"] or 0))) if x.get("fw_phut") else 0
        bt = float(x["bt"])
        return dict(bt=bt, et=float(x["et"]), bu=float(x["buong"]), lenh=int(float(x["lenh"])), ma=int(float(x["ma"])), pc=0,
                    man=2, fw_t=fw, start=1, m23=self.m23, het=self.i >= len(self.rows))

    def dat(self, nhiet=None, gio=None):
        self.lenh_ghi.append((self.i, nhiet, gio))
        return nhiet if nhiet is not None else gio

    def xa(self):
        self.lenh_ghi.append((self.i, "XA", None))
        return 1

    def artisan(self, nut):
        self.lenh_ghi.append((self.i, "ARTISAN_" + nut, None))

    def an_toan(self):
        self.lenh_ghi.append((self.i, "AN_TOAN", None))
        return 0

    def ngu(self, s):
        pass


# ───────────────────────── vòng chạy ─────────────────────────
class ChayMe9:
    def __init__(self, may, tm):
        self.may, self.tm = may, tm
        os.makedirs(tm, exist_ok=True)
        self.f_log = open(os.path.join(tm, "lai9_log.csv"), "w", encoding="utf-8", newline="")
        self.w = csv.writer(self.f_log)
        self.w.writerow(["t_rang", "bt", "et", "buong", "ror30_lui", "nhiet_lenh", "nhiet_ghi", "gio", "buoc", "ghi_chu"])
        self.lai = L9.LaiMe9()
        self.bt_hist = []
        self.su_kien = []
        self.bt_drop = L9.DICH["bt_drop"]

    def ghi(self, s, t=None):
        dong = "%s %s" % ("t=%s" % t if self.may.gia_lap else time.strftime("%H:%M:%S"), s)
        self.su_kien.append(dong)
        with open(os.path.join(self.tm, "trang_thai.txt"), "a", encoding="utf-8") as f:
            f.write(dong + "\n")
        if not self.may.gia_lap:
            print(dong, flush=True)

    def buoc_cua(self, t, bt):
        if t < 105:
            return "2_lich_me4"
        if bt < L9.DICH["bt_de"]:
            return "3_dung_den_DE"
        if bt < L9.DICH["bt_fcs"]:
            return "4_buong_phang" if t < L9.DICH["fcs"] - 90 else "6a_FCs-90_cam_tang"
        return "6b_dev_phang_5.5"

    def an_toan(self, ly_do, t=None):
        lenh = self.may.an_toan()
        self.ghi("⛔ AN TOÀN: %s ⇒ Lệnh nhiệt %s, gió 100 — lệnh kế: hong_qua_panel.py an_toan --csv làm mát" % (ly_do, lenh), t)

    def chay(self):
        d = self.may.doc()
        # 1. trước START: BT_START + ngưỡng auto-charge (luật 150)
        nguong = d["m23"] / 10
        self.ghi("BT_START %.1f °C (lồng, CHƯA có hạt) · ngưỡng auto-charge $M23 %.1f °C" % (d["bt"], nguong))
        if nguong < L9.BT_CHARGE_MIN:
            self.ghi("⛔ $M23 %.1f < %.0f — DỪNG, không chạy, báo anh (luật không CHARGE khi BT < 150)" % (nguong, L9.BT_CHARGE_MIN))
            return "dung_m23"
        if abs(nguong - L9.BT_CHARGE_KE_HOACH) > 0.5:
            self.ghi("⚠ $M23 %.1f khác kế hoạch %.0f — DỪNG, báo anh" % (nguong, L9.BT_CHARGE_KE_HOACH))
            return "dung_m23_khac"
        # 2. chờ CHARGE (firmware tự charge ở $M23); theo dõi BT 30 s gần nhất để bắt rơi
        cho, truoc = 0, []
        while True:
            d = self.may.doc()
            truoc = (truoc + [d["bt"]])[-30:]
            if d["bt"] > BT_MAX or d["et"] > ET_MAX:
                self.an_toan("BT %.1f / ET %.1f trước charge" % (d["bt"], d["et"]))
                return "an_toan"
            if d["fw_t"] == 0:
                self._da_thay_fw0 = True
            if (d["fw_t"] > 0 and getattr(self, "_da_thay_fw0", False)) or (len(truoc) >= 10 and max(truoc) - d["bt"] >= 25 and max(truoc) > 120):
                bt_charge = max(truoc[-10:])
                if not L9.kiem_charge(bt_charge, ghi=self.ghi):
                    self.an_toan("CHARGE ở BT %.1f < %.0f (vi phạm luật — hạt đã vào lồng lạnh)" % (bt_charge, L9.BT_CHARGE_MIN))
                    return "cam_charge"
                break
            if d["m23"] / 10 < L9.BT_CHARGE_MIN:
                self.an_toan("ngưỡng $M23 bị đổi xuống %.1f lúc chờ charge" % (d["m23"] / 10))
                return "dung_m23"
            cho += 1
            if cho > CHO_CHARGE_MAX or d.get("het"):
                self.ghi("⛔ 20 phút chưa CHARGE — dừng bộ lái")
                return "khong_charge"
            self.may.ngu(1)
        self.may.artisan("CHARGE")
        self.ghi("MỐC CHARGE · BT_CHARGE %.1f °C (≥ %.0f) — bộ lái mẻ 9 bắt đầu" % (bt_charge, L9.BT_CHARGE_MIN), 0)
        # 3. vòng lái 1 Hz
        t, u_ghi, gio_ghi, t_pt, buoc_cu = 0, None, None, 0, None
        moc = {}
        while True:
            d = self.may.doc()
            bt, et, bu = d["bt"], d["et"], d["bu"]
            self.bt_hist.append(bt)
            if bt > BT_MAX or et > ET_MAX:
                self.an_toan("BT %.1f / ET %.1f vượt %.0f/%.0f" % (bt, et, BT_MAX, ET_MAX), t)
                self.may.xa()
                return "an_toan"
            ror = 60 * np.polyfit(np.arange(30), self.bt_hist[-30:], 1)[0] if len(self.bt_hist) >= 30 else float("nan")
            if "TP" not in moc and t > 20 and len(self.bt_hist) > 5 and bt > min(self.bt_hist) + 0.5:
                moc["TP"] = int(np.argmin(self.bt_hist))
            for ten, nguong in (("DE", 155.0), ("FCs", 194.0)):
                if ten not in moc and "TP" in moc and bt >= nguong:
                    moc[ten] = t
                    self.ghi("MỐC %s %d:%02d · BT %.1f" % (ten, t // 60, t % 60, bt), t)
            u, gio, chu = self.lai.lenh(t, bt, bu, ror)
            buoc = self.buoc_cua(t, bt)
            if buoc != buoc_cu:
                self.ghi("BƯỚC %s bắt đầu lúc %d:%02d (BT %.1f)" % (buoc, t // 60, t % 60, bt), t)
                buoc_cu = buoc
            u_int = int(round(u))
            if u_int != u_ghi:
                self.may.dat(nhiet=u_int)
                u_ghi = u_int
            if gio != gio_ghi:
                self.may.dat(gio=gio)
                gio_ghi = gio
            if chu:
                self.ghi("LÁI %d:%02d · %s · Nhiệt %.1f → ghi %d %%" % (t // 60, t % 60, chu, u, u_int), t)
            self.w.writerow([t, bt, et, bu, round(ror, 2) if ror == ror else "", round(u, 2), u_int, gio, buoc, chu])
            if t - t_pt >= 15 and len(self.bt_hist) > 40:
                t_pt = t
                tt = np.arange(len(self.bt_hist), dtype=float)
                loi, _ = H.tim_loi(tt, np.array(self.bt_hist), moc, (), 5, 6, bay_gio=t)
                dang = [l for l in loi if l["den_s"] >= t - 60]
                nhan = " | ".join("%s [%s] %s ⇒ %s" % (l["loai"], l["muc"], l["so_do"], H.VIEC_LAI[l["ma"]]) for l in dang) or "không lỗi"
                self.ghi("PHÂN TÍCH 15s %d:%02d · BT %.1f ET %.1f buồng %.1f · RoR %s · Nhiệt %d %% gió %d %% · bước %s · RoR: %s" % (
                    t // 60, t % 60, bt, et, bu, ("%.1f" % ror) if ror == ror else "—", u_int, gio, buoc, nhan), t)
            if bt >= self.bt_drop:
                v = self.may.xa()
                self.ghi("Hồng DROP: $7=1 (đọc lại %s) ở BT %.1f · %d:%02d" % (v, bt, t // 60, t % 60), t)
                return "drop"
            if t >= T_MAX or d.get("het"):
                v = self.may.xa()
                self.ghi("⛔ %s chưa tới BT %.0f — xả ở BT %.1f" % ("hết log" if d.get("het") else "18:00", L9.DICH["bt_drop"], bt), t)
                return "xa_het_gio"
            t += 1
            self.may.ngu(1)


def chay_may(tm, slot):
    import artisan_ui
    import hmi_dien
    may = MayThat()
    # chọn hồ sơ trước — nạp hồ sơ trống làm firmware ghi đè $M23 = 180 ⇒ đặt lại 170 rồi MỚI kiểm (luật CHARGE ≥ 150, = kế hoạch)
    hmi_dien.chon_ho_so(slot)
    hmi_dien.che_do(False)                      # False = RANG LƯU (SAVE); True = AUTO
    hmi_dien.nhiet_charge(L9.BT_CHARGE_KE_HOACH)
    ok, ly = L9.kiem_truoc_start(may.pn, ghi=print)
    if not ok:
        raise SystemExit("Không START: " + ly)
    print("Artisan:", artisan_ui.bat_ghi())       # Artisan kết nối máy TRƯỚC (luật 14/10)
    may.pn.dat_gio(L9.GIO_NEN)
    may.pn.dat_nhiet(80)
    may.pn.lenh_nhiet(1)
    try:
        hmi_dien.bat_dau()
    except Exception as e:                      # START không thành ⇒ TẮT nhiệt ngay (bài học 17/10: bật 80 % rồi chết)
        may.an_toan()
        raise SystemExit("START lỗi, đã tắt nhiệt: %s" % e)
    return ChayMe9(may, tm).chay()


def chay_kho(me, charge_bt=None, m23=1700, drop=None):
    tm = os.path.join(os.environ.get("TEMP", "."), "kho_me9_%d_%s_%s" % (me, charge_bt, m23))
    if os.path.exists(os.path.join(tm, "trang_thai.txt")):
        os.remove(os.path.join(tm, "trang_thai.txt"))
    may = MayPhatLai(me, charge_bt, m23)
    c = ChayMe9(may, tm)
    if drop is not None:
        c.bt_drop = drop                            # chạy khô: log mẻ 4/5 không tới 218 ⇒ hạ ngưỡng để thử đường DROP
    kq = c.chay()
    # kiểm tốc độ lệnh Nhiệt
    log = list(csv.DictReader(open(os.path.join(tm, "lai9_log.csv"), encoding="utf-8")))
    vi_pham = []
    if log:
        t = np.array([int(x["t_rang"]) for x in log])
        u = np.array([float(x["nhiet_lenh"]) for x in log])
        b = [x["buoc"] for x in log]
        for i in range(10, len(t)):
            du = u[i] - u[i - 10]
            if b[i] in ("4_buong_phang", "6a_FCs-90_cam_tang") and abs(du) > 1.0 + 1e-9 and not (585 <= t[i] <= 615):
                vi_pham.append((int(t[i]), b[i], round(du, 2)))
            if b[i] == "6b_dev_phang_5.5" and du > 0.5 + 1e-9:
                vi_pham.append((int(t[i]), b[i], round(du, 2)))
    buoc = [s for s in c.su_kien if "PHÂN TÍCH" not in s and ("BƯỚC" in s or "MỐC" in s or "DROP" in s or "⛔" in s or "CHARGE" in s or "gió" in s)]
    return dict(ket_qua=kq, su_kien=buoc, vi_pham_toc_do=vi_pham, so_dong_phan_tich=sum("PHÂN TÍCH" in s for s in c.su_kien),
                so_lenh_nhiet_ghi=sum(1 for x in may.lenh_ghi if isinstance(x[1], (int, float))), thu_muc=tm)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    a = sys.argv[1:]
    opt = {a[i][2:]: a[i + 1] for i in range(len(a)) if a[i].startswith("--")}
    if a and a[0] == "kho":
        r = chay_kho(int(a[1]), float(opt["charge_bt"]) if "charge_bt" in opt else None, int(opt.get("m23", 1700)),
                     float(opt["drop"]) if "drop" in opt else None)
        print(json.dumps(r, ensure_ascii=False, indent=1))
    elif a and a[0] == "may":
        if os.environ.get("HONG_DUOC_THAO_TAC") != "1":
            raise SystemExit("cần HONG_DUOC_THAO_TAC=1 (chọn slot / START trên HMI)")
        print(chay_may(a[1], int(opt.get("slot", 9))))
    else:
        print(__doc__)
