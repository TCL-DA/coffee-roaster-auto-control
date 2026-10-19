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
ROR_BAO, ROR_CAT = 25.0, 30.0   # mẻ 2: RoR (sau TP + 20 s) > 25 ghi báo, > 30 ghi "quá ngưỡng cắt" (trần sấy HONG_ROR_TRAN là cơ chế hạ)
# HONG_DROP_NO="11,205,209" ⇒ bật đổi DROP theo nổ người báo (no_that.txt). Không đặt ⇒ DROP = DICH["bt_drop"] cố định.
DROP_NO = tuple(float(x) for x in os.environ["HONG_DROP_NO"].split(",")) if os.environ.get("HONG_DROP_NO") else None
CHARGE_ROI_MIN = 40.0   # dự phòng nhận CHARGE khi không đọc được fw_t: BT rơi ≥ 40 °C trong 20 s (nguội ≤ 25/30 s, hạt vào 66/20 s)


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

    def doi_drop_theo_no(self, t, bt):
        """MỘT cơ chế DROP (mẻ 2, 18/10): bt_drop = DICH["bt_drop"] (207 = nổ đo 196 + 11). Chỉ khi bật HONG_DROP_NO="cộng,min,max":
        người đứng máy nghe nổ ⇒ Hồng ghi file <thư mục mẻ>/no_that.txt (số = BT nổ; để trống = BT lúc file xuất hiện) ⇒
        bt_drop = BT nổ + cộng, kẹp [min, max]. Đọc 1 lần. Không có file ⇒ giữ 207. Đổi cả DICH để đường RoR dev bám đích mới."""
        if DROP_NO is None or getattr(self, "da_doc_no", False):
            return
        f = os.path.join(self.tm, "no_that.txt")
        if not os.path.exists(f):
            return
        self.da_doc_no = True
        try:
            s = open(f, encoding="utf-8").read().strip().replace(",", ".")
            bt_no = float(s) if s else bt
        except ValueError:
            self.ghi("⚠ no_that.txt không đọc được số — giữ DROP %.1f" % self.bt_drop, t)
            return
        cong, lo, hi = DROP_NO
        moi = min(hi, max(lo, bt_no + cong))
        self.ghi("NỔ NGƯỜI BÁO %d:%02d · BT nổ %.1f (BT bây giờ %.1f) ⇒ DROP %.1f (= nổ + %g, kẹp %g–%g; trước %.1f)" % (
            t // 60, t % 60, bt_no, bt, moi, cong, lo, hi, self.bt_drop), t)
        self.bt_drop = moi
        L9.DICH["bt_drop"] = moi

    def buoc_cua(self, t, bt, ror=float("nan")):
        if t < 105:
            return "2_lich_me4"
        if bt < L9.DICH["bt_de"]:
            return "3_dung_den_DE"
        if bt < L9.DICH["bt_fcs"]:
            return "6a_FCs-90_cam_tang" if (self.lai.da_gan_fcs or L9.gan_fcs(bt, ror)) else "4_buong_phang"
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
            # CHARGE = đồng hồ rang firmware chạy (fw_t 0 → > 0). Mẻ 11 (17/10): luật cũ "BT rơi ≥ 25 / 30 s" bắt nhầm lúc
            # firmware COOL_DOWN tắt nhiệt từ BT 224 (lồng trống). Đo mẻ 11: nguội rơi ≤ 25 / 30 s, hạt 500 g vào rơi 66,6 / 20 s.
            # Dự phòng (đồng hồ kẹt / không đọc được): BT rơi ≥ CHARGE_ROI_MIN °C trong 20 s — nhanh gấp ~2 lần nguội nhanh nhất.
            fw_chay = d["fw_t"] > 0 and getattr(self, "_da_thay_fw0", False)
            # Hồng 18/10: dự phòng chỉ tin khi Lệnh nhiệt = 1 — firmware COOL_DOWN luôn TẮT Lệnh (mẻ 11: Lệnh 0, mã 164),
            # còn lúc nung tới $M23 rồi tự CHARGE thì Lệnh 1 (mẻ 11: mã 163 → 86). Lồng nóng nguội nhanh hơn dự kiến vẫn không nhận nhầm.
            roi_hat = (len(truoc) >= 20 and max(truoc[-20:]) - d["bt"] >= CHARGE_ROI_MIN and max(truoc[-20:]) > 120
                       and d.get("lenh") == 1)
            if fw_chay or roi_hat:
                # đồng hồ chạy ⇒ hạt vừa vào 0–2 s trước (5 s là đủ; 20 s có thể lẫn BT cao lúc COOL_DOWN vừa xong);
                # nhận bằng BT rơi ⇒ hạt vào ~10–12 s trước ⇒ cửa 20 s
                bt_charge = max(truoc[-5:]) if fw_chay else max(truoc[-20:])
                # nhận bằng BT rơi ⇒ giờ rang bắt đầu từ đỉnh BT (hạt vào), không từ lúc phát hiện (~10–12 s sau)
                if not fw_chay:
                    w = truoc[-20:]
                    self.bt_hist = list(w[int(np.argmax(w)):])     # đỉnh → mẫu hiện tại = giây 0 … tre
                    self.t_dau = len(self.bt_hist)                 # vòng lái đọc mẫu KẾ TIẾP
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
        t, u_ghi, gio_ghi, t_pt, buoc_cu = getattr(self, "t_dau", 0), None, None, 0, None
        if t:
            self.ghi("CHARGE nhận bằng BT rơi (đồng hồ firmware không chạy) ⇒ giờ rang bắt đầu từ đỉnh BT, trễ %d s" % t, t)
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
            for ten, nguong in (("DE", L9.DICH["bt_de"]), ("FCs", L9.DICH["bt_fcs"])):     # mẻ 2: nổ đo 196 qua HONG_DICH
                if ten not in moc and "TP" in moc and bt >= nguong:
                    moc[ten] = t
                    self.ghi("MỐC %s %d:%02d · BT %.1f" % (ten, t // 60, t % 60, bt), t)
            u, gio, chu = self.lai.lenh(t, bt, bu, ror)
            buoc = self.buoc_cua(t, bt, ror)
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
            self.doi_drop_theo_no(t, bt)
            if "TP" in moc and t >= moc["TP"] + 20 and ror == ror and ror > ROR_BAO and t - getattr(self, "t_bao_ror", -99) >= 30:
                self.t_bao_ror = t
                self.ghi("⚠ RoR %.1f > %s °C/ph (%s) · Nhiệt %d %% — trần sấy %s đang giữ; > %s kéo dài ⇒ an_toan" % (
                    ror, ROR_BAO, "QUÁ NGƯỠNG CẮT" if ror > ROR_CAT else "báo", u_int, L9.ROR_TRAN, ROR_CAT), t)
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


def va_drop_alog(alog, t_drop, bt_drop=None):
    """Artisan thiếu mốc DROP (mẻ 11, 17/10: UIA báo đã bấm DROP nhưng timeindex[6] = 0 — gốc chưa rõ) ⇒ ghi bản
    `<tên>_drop_sua.alog` với DROP = CHARGE + t_drop giây (giờ rang firmware). Không sửa đè file gốc.
    Hồng 18/10 — kiểm trước khi ghi (Artisan có thể giữ CHARGE NHẦM nếu bị bấm 2 lần, như mẻ 11 lúc 16:51:23 / 16:52:53):
      · CHARGE Artisan phải là hạt vào thật: BT rơi ≥ 40 °C trong 60 s sau CHARGE (lồng trống nguội ≤ 25 / 30 s);
      · bt_drop (nếu đưa): BT ở mẫu DROP phải lệch ≤ 2 °C so BT DROP ghi trong trang_thai / log bộ lái.
    Trả (đường dẫn bản sửa | None, ghi chú)."""
    import ast
    d = ast.literal_eval(open(alog, encoding="utf-8").read())
    ti, tx, bt = d["timeindex"], d["timex"], d["temp2"]
    if ti[6] > 0:
        return None, "Artisan đã có DROP — không sửa"
    if ti[0] < 0 or not tx:
        return None, "Artisan chưa có CHARGE — không sửa"
    sau = [bt[i] for i in range(ti[0], len(tx)) if tx[i] - tx[ti[0]] <= 60 and bt[i] > 0]
    if not sau or bt[ti[0]] - min(sau) < 40:
        return None, "CHARGE Artisan (mẫu %d, BT %.1f) không có BT rơi ≥ 40 °C / 60 s ⇒ nghi CHARGE NHẦM — không sửa, sửa tay" % (
            ti[0], bt[ti[0]])
    dich = tx[ti[0]] + float(t_drop)
    i = min(range(len(tx)), key=lambda k: abs(tx[k] - dich))
    if bt_drop is not None and abs(bt[i] - float(bt_drop)) > 2:
        return None, "mẫu %d BT %.1f lệch BT DROP %.1f > 2 °C — không sửa" % (i, bt[i], float(bt_drop))
    ti[6] = i
    ra = os.path.splitext(alog)[0] + "_drop_sua.alog"
    with open(ra, "w", encoding="utf-8") as f:
        f.write(repr(d))
    return ra, "DROP mẫu %d · %.1f s sau CHARGE · BT %.1f" % (i, tx[i] - tx[ti[0]], bt[i])


def chay_may(tm, slot):
    import artisan_ui
    import hmi_dien
    may = MayThat()
    # chọn hồ sơ trước — nạp hồ sơ trống làm firmware ghi đè $M23 = 180 ⇒ đặt lại 170 rồi MỚI kiểm (luật CHARGE ≥ 150, = kế hoạch)
    try:
        hmi_dien.chon_ho_so(slot)
        hmi_dien.che_do(False)                      # False = RANG LƯU (SAVE); True = AUTO
        hmi_dien.nhiet_charge(L9.BT_CHARGE_KE_HOACH)
    except Exception:
        hmi_dien.chuyen_man(2)                      # lỗi giữa chừng vẫn trả HMI về màn 2
        raise
    # luật anh Thành 17/10: thao tác HMI xong ⇒ về NGAY màn 2 VẬN HÀNH (anh xem giản đồ trên HMI suốt mẻ)
    v2 = hmi_dien.chuyen_man(2)
    print("HMI về màn 2:", v2, "· $21 =", may.pn.doc(21, 1)[0])
    if may.pn.doc(21, 1)[0] != 2:
        raise SystemExit("Không đưa được HMI về màn 2 — không START")
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
    c = ChayMe9(may, tm)
    if os.environ.get("HONG_T_LENH"):               # luật 17/10: ghi GIÂY LỆNH→START (đích ≤ 60 s)
        n = time.time() - float(os.environ["HONG_T_LENH"])
        c.ghi("START (slot %d, RANG LƯU, $M23 %.0f) · GIÂY LỆNH→START = %.0f s%s" % (
            slot, L9.BT_CHARGE_KE_HOACH, n, "" if n <= 60 else " — QUÁ 60 s, ghi lý do"))
    return c.chay()


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
    elif a and a[0] == "va_drop":                   # python tools/hong_chay_me9.py va_drop <file.alog> <giây DROP từ CHARGE> [--bt <BT DROP>]
        print(*va_drop_alog(a[1], float(a[2]), float(opt["bt"]) if "bt" in opt else None), sep=" · ")
    elif a and a[0] == "may":
        if os.environ.get("HONG_DUOC_THAO_TAC") != "1":
            raise SystemExit("cần HONG_DUOC_THAO_TAC=1 (chọn slot / START trên HMI)")
        print(chay_may(a[1], int(opt.get("slot", 9))))
    else:
        print(__doc__)
