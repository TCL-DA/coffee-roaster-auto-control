# -*- coding: utf-8 -*-
"""OTL Hồng đọc + lái máy rang QUA PANEL HMI (Modbus TCP) — song song với Artisan (14/10/2026).

Luật chủ máy: Artisan kết nối máy rang TRƯỚC (giữ cổng COM của board); agent kết nối SAU bằng đường RIÊNG, không qua Artisan,
đọc TOÀN BỘ dữ liệu, phân tích mỗi 3 giây. Đường riêng = panel Delta (bản HMI có bảng Modbus TCP mở — bản bàn thử ..-LO99-DIEN):
panel giữ bản sao mọi số board gửi lên (W400nn ≡ $(nn−1)) và board đọc ô điều khiển của panel như người bấm.

Bản đồ (firmware include/Define.h):
  đọc  $1 Lệnh nhiệt (W40002) · $13 cờ PC control (W40014) · $21 màn đang hiện · $40 mã trạng thái (W40041) · $60 BT ×10
       $61 ET ×10 · $64 gió % ×10 · $65 trống % ×10 · $66 Nhiệt % thật ×10 · $96 nhiệt BUỒNG VX4 ×10 (W40097)
  ghi  $M34 trống đặt · $M35 gió đặt · $M36 Nhiệt đặt (TCP 2000 + n) · $1 bật/tắt Lệnh nhiệt
⛔ Board nghe HMI chỉ khi cờ PC control TẮT ($13 = 0) — đang bật thì nó nghe PC (Artisan / PC_Link).

    python hong_qua_panel.py doc                   # đọc 1 lần, in đủ
    python hong_qua_panel.py theo_doi <phút> <csv> # đọc mỗi 1 s, PHÂN TÍCH mỗi 3 s
    python hong_qua_panel.py cham <file.alog> [--lo 1.5]          # chấm đề chuỗi mốc từ giản đồ Artisan đã lưu
    python hong_qua_panel.py thu [seed] [thư mục]                 # DRY-RUN 1 lượt đề trên bản sao số (cùng logic với máy thật)
    python hong_qua_panel.py mc <số lượt> [--lo 1.5] [--luong 12] # Monte Carlo bản sao số
    python hong_qua_panel.py kiem_artisan                         # CHỈ ĐỌC: cấu hình COM13, ON, LCD (UIA, không bấm)
    python hong_qua_panel.py an_toan [--gio 100] [--csv <file> --den 60]  # TẮT nhiệt + làm mát 1 phát; --csv: theo dõi tới nguội
    HONG_DUOC_LAI=1 python hong_qua_panel.py phien <số lượt> <hết lúc HH:MM> <thư mục> [--ngam 15 --n_ngam 55] [--dau 200]
        # CẢ BUỔI 1 tiến trình: [ngấm] → N × (về đầu MPC → lượt đề → chấm .alog) → an_toan + làm mát. Đọc tong_ket.jsonl
    HONG_DUOC_LAI=1 python hong_qua_panel.py giai_de <hết lúc HH:MM> <thư mục log>   # MÁY THẬT — chỉ khi anh Thành duyệt

Bộ giải đề chuỗi mốc (15/10/2026) — xem `.claude/skills/rang-ca-phe/references/dieu-khien-nhiet.md` mục 7.
"""
import ast
import csv
import os
import re
import socket
import struct
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ban_sao_so_may_dien as bss  # noqa: E402
import cach_tinh_david as david  # noqa: E402  — chủ máy 15/10: LUÔN tính k David để tham khảo

IP = os.environ.get("OTL_PANEL_IP", "169.254.116.153")
GIO_MIN_PCT = 34                      # gió tối thiểu máy điện = 50 Hz (chủ máy 14/10)
MAN_RANG, MAN_KHOA = 2, 15


def _pin_panel():
    """PIN đăng nhập panel: biến OTL_PANEL_PIN, không thì file riêng ~/.otl/panel_pin.txt (ngoài repo — không lên GitHub)."""
    pin = os.environ.get("OTL_PANEL_PIN")
    if not pin:
        try:
            with open(os.path.join(os.path.expanduser("~"), ".otl", "panel_pin.txt"), encoding="utf-8") as f:
                pin = f.read().strip()
        except OSError:
            sys.exit("Thiếu PIN panel: đặt OTL_PANEL_PIN hoặc tạo ~/.otl/panel_pin.txt")
    return pin


class Panel:
    def __init__(self, ip=IP):
        self.ip, self.s, self.tid = ip, None, 0

    def _ket_noi(self):
        if self.s is None:
            self.s = socket.create_connection((self.ip, 502), 3)
            self.s.settimeout(3)

    def _hoi(self, pdu):
        for lan in (1, 2):
            try:
                self._ket_noi()
                self.tid = (self.tid + 1) & 0xFFFF
                self.s.sendall(struct.pack(">HHHB", self.tid, 0, len(pdu) + 1, 1) + pdu)
                h = b""
                while len(h) < 7:
                    x = self.s.recv(7 - len(h))
                    if not x:
                        raise OSError("panel đóng kết nối")
                    h += x
                n = struct.unpack(">H", h[4:6])[0] - 1
                b = b""
                while len(b) < n:
                    x = self.s.recv(n - len(b))
                    if not x:
                        raise OSError("panel đóng kết nối")
                    b += x
                if b[0] & 0x80:
                    raise ValueError("panel từ chối (ngoại lệ %d) — bảng Modbus TCP của HMI chưa mở ô này" % b[1])
                return b
            except OSError:
                self.s = None
                if lan == 2:
                    raise
                time.sleep(0.3)

    def doc(self, dau, so):
        b = self._hoi(struct.pack(">BHH", 3, dau, so))
        return list(struct.unpack(">%dH" % so, b[2:2 + 2 * so]))

    def ghi(self, dau, vals):
        self._hoi(struct.pack(">BHHB", 16, dau, len(vals), 2 * len(vals)) + struct.pack(">%dH" % len(vals), *vals))

    # ── đọc / ghi theo tên ───────────────────────────────────────────────────────────────
    def doc_tat_ca(self):
        r = self.doc(0, 100)                       # $0..$99 một giao dịch
        m = self.doc(2034, 3)                      # $M34..$M36
        s16 = lambda v: v - 65536 if v >= 32768 else v  # noqa: E731
        return {"lenh_nhiet": r[1], "pc_control": r[13], "man": r[21], "ma": r[40], "bt": s16(r[60]) / 10,
                "et": s16(r[61]) / 10, "gio": r[64] / 10, "trong": r[65] / 10, "nhiet": r[66] / 10,
                "buong": s16(r[96]) / 10 if len(r) > 96 else None, "dat_trong": m[0], "dat_gio": m[1], "dat_nhiet": m[2]}

    def dat_nhiet(self, pct):
        self.ghi(2036, [int(max(0, min(100, round(pct))))])

    def dat_gio(self, pct):
        self.ghi(2035, [int(max(GIO_MIN_PCT, min(100, round(pct))))])

    def dat_trong(self, pct):
        self.ghi(2034, [int(max(0, min(100, round(pct))))])

    def lenh_nhiet(self, bat):
        self.ghi(1, [1 if bat else 0])

    def pc_control(self, bat):
        self.ghi(13, [1 if bat else 0])

    def dang_nhap(self, pin=None):
        """Panel vừa khởi động lại thì ở MÀN KHOÁ ($21 = 15). Ghi PIN vào $955 rồi về màn rang ($49 = 2). Trả màn đang hiện.
        Chủ máy 14/10: "sao không đăng nhập vô đi kìa" — agent phải TỰ đăng nhập sau mỗi lần nạp / khởi động panel."""
        if self.doc(21, 1)[0] == MAN_KHOA:
            self.ghi(955, [int(pin or _pin_panel())])
            time.sleep(2.5)
        self.ghi(49, [MAN_RANG])
        time.sleep(2.5)
        return self.doc(21, 1)[0]


def doc_hoi_quy(lich_su, giay=20):
    """Độ dốc hồi quy (°C/phút) của cột trong lich_su [(t, v)] trên `giay` giây gần nhất."""
    if not lich_su:
        return 0.0
    now = lich_su[-1][0]
    cs = [(t, v) for t, v in lich_su if now - t <= giay]
    if len(cs) < 5:
        return 0.0
    tt = sum(t for t, _ in cs) / len(cs)
    vv = sum(v for _, v in cs) / len(cs)
    m = sum((t - tt) ** 2 for t, _ in cs)
    return sum((t - tt) * (v - vv) for t, v in cs) / m * 60 if m else 0.0


def theo_doi(phut, duong_csv):
    """Đọc mỗi 1 s, PHÂN TÍCH mỗi 3 s: RoR BT/ET/buồng (hồi quy 20 s), chênh buồng−ET, ET−BT, SV, BT dự báo +30 s, mã."""
    p = Panel()
    f = open(duong_csv, "a", newline="", encoding="utf-8")
    w = csv.writer(f)
    w.writerow(["gio", "bt", "et", "buong", "nhiet", "gio_pct", "trong", "lenh_nhiet", "pc", "ma"])
    ls = {"bt": [], "et": [], "buong": []}
    t0, t_pt = time.time(), 0.0
    while time.time() - t0 < phut * 60:
        now = time.time()
        d = p.doc_tat_ca()
        w.writerow([time.strftime("%H:%M:%S"), d["bt"], d["et"], d["buong"], d["nhiet"], d["gio"], d["trong"], d["lenh_nhiet"],
                    d["pc_control"], d["ma"]])
        f.flush()
        for k in ls:
            if d[k] is not None:
                ls[k].append((now, d[k]))
                ls[k] = [x for x in ls[k] if now - x[0] <= 60]
        if now - t_pt >= 3:
            t_pt = now
            r_bt, r_et, r_bu = (doc_hoi_quy(ls[k]) for k in ("bt", "et", "buong"))
            sv = 160 + 2.1 * d["nhiet"] if d["lenh_nhiet"] else 0   # thang firmware từ 16/10 (Config.h VX4_SV_*)
            print("%s BT %.1f (RoR %+.1f) · ET %.1f (%+.1f) · BUONG %s (%+.1f) · SV %d · buong-ET %s · ET-BT %.1f · "
                  "BT+30s %.1f · nhiet %d%% gio %d%% trong %d%% · lenh %d pc %d ma %d"
                  % (time.strftime("%H:%M:%S"), d["bt"], r_bt, d["et"], r_et, d["buong"], r_bu, sv,
                     ("%.1f" % (d["buong"] - d["et"])) if d["buong"] is not None else "?", d["et"] - d["bt"],
                     d["bt"] + r_bt / 2, d["nhiet"], d["gio"], d["trong"], d["lenh_nhiet"], d["pc_control"], d["ma"]),
                  flush=True)
        time.sleep(max(0.0, 1.0 - (time.time() - now)))
    f.close()


# ══════════════════════════════════════════════════════════════════════════════════════════════
# ĐỀ CHUỖI MỐC BT (chủ máy 14/10/2026) — chấm, bộ giải, an toàn, Artisan, máy thật / bản sao số
# ══════════════════════════════════════════════════════════════════════════════════════════════
MOC_DE = (170, 190, 210, 230, 200, 180, 150)
LO_MAX = 1.5          # ⛔ luật cứng: lên mà BT > mốc + LO_MAX, hoặc xuống mà BT < mốc − LO_MAX ⇒ mốc TRƯỢT (có thể chốt 0)
DAI_DE, GIU_DE, HAN_DE = 1.5, 30.0, 600.0
ET_MAX, BT_TREN_MOC, MAT_SO_GIAY, TRAN_GIAY = 255.0, 15.0, 5.0, 720.0
BT_TUYET_DOI = 245.0                              # chủ máy 15/10: BT > 245 °C ⇒ tự dừng
# cảnh báo cảm biến / nhiệt độ, lỗi truyền thông Modbus (trừ 288 CRC lẻ), lỗi nghiêm trọng (include/MachineStatus.h)
MA_DUNG = (range(261, 281), range(281, 288), range(289, 298), range(401, 431))


def cham_bt(t, bt, moc=MOC_DE, lo_max=LO_MAX, dai=DAI_DE, giu=GIU_DE, han=HAN_DE):
    """Chấm đề theo luật: mốc i bắt đầu khi mốc i−1 xong (mốc 1 bắt đầu ở mẫu đầu). Xong = |BT − mốc| ≤ dai LIÊN TỤC ≥ giu giây.
    Lố tính từ lúc bắt đầu tới lúc xong, theo CHIỀU ĐANG ĐI (chiều so với mốc trước / BT đầu). Lố > lo_max ⇒ mốc TRƯỢT.
    Đạt = đủ mốc, không mốc nào trượt, xong mốc cuối ≤ han giây tính từ mẫu đầu (Artisan START)."""
    kq, i, t_vao, t_dau, lo = [], 0, None, t[0], -1e9
    truoc = bt[0]
    for tk, b in zip(t, bt):
        if i >= len(moc):
            break
        mc = moc[i]
        hg = 1.0 if mc > truoc else -1.0
        lo = max(lo, hg * (b - mc))
        if abs(b - mc) <= dai + 1e-9:
            t_vao = tk if t_vao is None else t_vao
            if tk - t_vao >= giu - 1e-9:
                kq.append({"moc": mc, "huong": "lên" if hg > 0 else "xuống", "bat_dau": round(t_dau - t[0], 1),
                           "xong": round(tk - t[0], 1), "giay": round(tk - t_dau, 1), "lo": round(max(lo, 0.0), 2),
                           "truot": lo > lo_max + 1e-9})
                truoc, t_dau, t_vao, lo, i = mc, tk, None, -1e9, i + 1
        else:
            t_vao = None
    if i < len(moc):                                 # mốc đang dở khi hết dữ liệu
        kq.append({"moc": moc[i], "huong": "lên" if moc[i] > truoc else "xuống", "bat_dau": round(t_dau - t[0], 1),
                   "xong": None, "giay": None, "lo": round(max(lo, 0.0), 2), "truot": lo > lo_max + 1e-9})
    du = len(kq) == len(moc) and kq[-1]["xong"] is not None
    tong = kq[-1]["xong"] if du else None
    lo_len = max([k["lo"] for k in kq if k["huong"] == "lên"] or [0.0])
    lo_xuong = max([k["lo"] for k in kq if k["huong"] == "xuống"] or [0.0])
    so_xong = sum(1 for k in kq if k["xong"] is not None and not k["truot"])
    return {"dat": bool(du and not any(k["truot"] for k in kq) and tong <= han), "so_moc_dat": so_xong,
            "tong_giay": tong, "lo_len": lo_len, "lo_xuong": lo_xuong, "moc": kq, "lo_max": lo_max}


def doc_alog(duong):
    """Giản đồ Artisan (.alog = dict Python): (t giây từ START, BT = temp2, ET = temp1). Bỏ mẫu lỗi (−1 / None)."""
    with open(duong, encoding="utf-8") as f:
        d = ast.literal_eval(f.read())
    ts, bts, ets = [], [], []
    for t, b, e in zip(d.get("timex", []), d.get("temp2", []), d.get("temp1", [])):
        if b is None or b <= 0:
            continue
        ts.append(float(t))
        bts.append(float(b))
        ets.append(float(e) if e is not None else float("nan"))
    return ts, bts, ets, d


def cham_alog(duong, lo_max=LO_MAX, moc=MOC_DE):
    """Hồng TỰ CHẤM từ file giản đồ Artisan đã lưu — không chấm từ log của bộ giải."""
    ts, bts, _, d = doc_alog(duong)
    if len(ts) < 2:
        return {"dat": False, "so_moc_dat": 0, "tong_giay": None, "loi": "giản đồ không có số liệu (%d mẫu)" % len(ts),
                "file": duong}
    kq = cham_bt(ts, bts, moc=moc, lo_max=lo_max)
    kq.update(file=duong, bat_dau=d.get("roastisodate", "") + " " + d.get("roasttime", ""), so_mau=len(ts),
              dai_giay=round(ts[-1] - ts[0], 1))
    return kq


def in_cham(kq):
    if kq.get("loi"):
        return "CHẤM %s: %s" % (os.path.basename(kq.get("file", "")), kq["loi"])
    dong = ["CHẤM %s · %s · lố cho phép %.1f °C" % (os.path.basename(kq.get("file", "bản sao số")), kq.get("bat_dau", ""),
                                                      kq["lo_max"])]
    for k in kq["moc"]:
        dong.append("  mốc %3d (%s) %s · %s · lố %.2f °C%s" % (
            k["moc"], k["huong"], "bắt đầu %5.0f s" % k["bat_dau"],
            ("xong %5.0f s (%3.0f s)" % (k["xong"], k["giay"])) if k["xong"] is not None else "CHƯA XONG",
            k["lo"], "  ⛔ TRƯỢT (vọt lố)" if k["truot"] else ""))
    tg = kq["tong_giay"]
    dong.append("  ⇒ %s · %d/%d mốc · tổng %s · lố lớn nhất lên %.2f / xuống %.2f °C" % (
        "ĐẠT" if kq["dat"] else "KHÔNG ĐẠT", kq["so_moc_dat"], len(MOC_DE),
        ("%d:%02d" % (tg // 60, tg % 60)) if tg is not None else "—", kq["lo_len"], kq["lo_xuong"]))
    return "\n".join(dong)


# ── BỘ GIẢI: MPC nhiều mô hình trên bản sao số ─────────────────────────────────────────────────
# Mỗi giây: bộ quan sát (K mô hình) nhận BT/ET/buồng → thử ~1 800 kế hoạch lệnh (giữ / đổi ở thời điểm τ / chạy hết cỡ rồi hãm /
# xung ngắn) trên CẢ K mô hình 150 s tới → chọn kế hoạch xong mốc sớm nhất mà KHÔNG mô hình nào vọt qua mốc quá BIEN_LO.
# Không dùng ror_bt firmware (trễ 30–40 s, có lúc ngược dấu — giáo trình mục 3).
TAU = (0, 1, 2, 3, 4, 6, 8, 10, 13, 16, 20, 25, 30, 40, 60)
TAU_HAM = (2, 4, 6, 8, 10, 13, 16, 20, 25, 30, 40, 50, 60)      # chạy hết cỡ rồi hãm sau τ giây
XUNG = (2, 3, 4, 5, 6, 8)
XUNG_NGHI = (6, 10, 14, 18, 24)                      # nghỉ giữa hai xung (s) — tắt ít nhất 6 s
NHIET_LUOI = tuple(range(0, 101))                             # 1 % ≈ 0,8–0,9 °C BT cân bằng — lưới 2 % làm giữ 190 đảo 32↔34 %


class GiaiDe:
    NHAY = (0.75, 0.85, 1.0, 1.05, 1.1)          # độ nhạy aE ⇒ 0,76 … 1,01 °C BT / % Nhiệt

    def __init__(self, moc=MOC_DE, p_ds=None, bien_lo=0.5, bien_lo_rong=1.0, cua_rong=40, dai_ke=0.9, dai_dem=1.3, giu=31,
                 tam=150, dung_nhiet=6, bat_it_nhat=2, tat_it_nhat=6, chu_ky=1, tre=2, phat_doi=0.5, kiem_rong=False,
                 tam_chon=15, nho_chon=0.03, bien_lo_giu=0.9, ki_lech=0.04):
        if p_ds is None:
            p0 = bss.doc_tham_so()
            p_ds = [bss.doi_do_nhay(p0, h) for h in self.NHAY]
        self.p_ds, self.P, self.K = p_ds, bss.xep_tham_so(p_ds), len(p_ds)
        self.kiem_rong, self.tam_chon, self.nho_chon = kiem_rong, int(tam_chon), nho_chon
        self.chon = min(range(self.K), key=lambda k: abs(self.NHAY[k] - 1.0)) if len(p_ds) == len(self.NHAY) else 0
        self.sai = np.zeros(self.K)
        self.ls_x = []
        self.cT0 = self.P["cT"].copy()                     # offset-free: cT += dT (nhiễu cân bằng ước theo sai số 15 s)
        self.dT = np.zeros_like(self.cT0)
        self.ki_lech, self.lech_max = ki_lech, 5.0
        self.moc = list(moc)
        self.bien_lo, self.bien_lo_rong, self.cua_rong, self.bien_lo_giu = bien_lo, bien_lo_rong, cua_rong, bien_lo_giu
        self.dai_ke, self.dai_dem, self.giu, self.tam = dai_ke, dai_dem, giu, tam
        self.mac_dinh, self.thap = (dai_ke, bien_lo, dai_dem, giu), False
        self.tre, self.phat_doi = int(tre), phat_doi          # trễ chết đọc panel + lệnh panel→board→VX4 (giây)
        self.lsu = []
        self.dung_nhiet, self.bat_it_nhat, self.tat_it_nhat, self.chu_ky = dung_nhiet, bat_it_nhat, tat_it_nhat, chu_ky
        self.x = None
        self.u = (0.0, 0.0)
        self.t_doi_nhiet = self.t_doi_lenh = -1e9
        self.i, self.dem, self.truoc = 0, 0, None
        self.xong = []
        self.ke_hoach = ""

    @property
    def het(self):
        return self.i >= len(self.moc)

    def bat_dau(self, t, bt, et, buong, u_hien_tai):
        self.u = (float(u_hien_tai[0]), 1.0) if u_hien_tai[1] else (0.0, 0.0)
        self.x = np.stack([bss.trang_thai_tu_do(p, bt, et, buong, *self.u) for p in self.p_ds])
        self.truoc = bt
        self.lsu = [self.u] * (self.tre + 1)

    def cap_nhat(self, t, bt, et, buong):
        # số đo lúc này là kết quả của lệnh đã ra `tre` giây trước
        self.x = bss.buoc_quan_sat(self.P, self.x, self.lsu[-1 - self.tre], bt, et, buong)
        self._chon_mo_hinh(bt)
        if self.het:
            return None
        mc = self.moc[self.i]
        self.dem = self.dem + 1 if abs(bt - mc) <= self.dai_dem else 0
        if self.dem >= self.giu:
            self.xong.append((mc, t))
            self.truoc, self.i, self.dem = mc, self.i + 1, 0
            return mc
        return None

    def huong(self):
        return 1.0 if self.moc[self.i] > self.truoc else -1.0

    def _xet_moc_thap(self):
        """Mốc THẤP = Lệnh bật ở 0 % (SV 130 °C) mà BT cân bằng vẫn > mốc + 1 °C ⇒ chỉ giữ được bằng xung ngắn tính trước.
        Chế độ này nới dải kế hoạch ±1,3 / lề lố 0,8 / đếm ±1,4 trong 31 s (luật đề ±1,5 / 30 s / lố 1,5) vì gợn xung 2–3 °C."""
        if getattr(self, "_moc_xet", None) == self.i:
            return
        self._moc_xet = self.i
        P = {k: v[[self.chon]] for k, v in self.P.items()}
        x = self.x[[self.chon]]
        for _ in range(150):
            x = bss._buoc_k(P, x, (0.0, 1.0))
        mc = self.moc[self.i]
        self.thap = bool(x[0, bss.T] > mc + 1.0)
        if self.thap:
            self.dai_ke, self.bien_lo, self.dai_dem, self.giu = 1.3, 0.8, 1.4, 31
        else:
            self.dai_ke, self.bien_lo, self.dai_dem, self.giu = self.mac_dinh

    def dang_giu(self):
        """Đã vào dải ±dai_dem và đang đếm giây giữ, Lệnh đang bật (mốc thấp dưới SV tối thiểu thì không khoá)."""
        return self.dem >= 3 and self.u[1] == 1.0 and not self.thap      # mốc thấp giữ bằng xung ⇒ không khoá Lệnh

    def _chon_mo_hinh(self, bt):
        """Mô hình THÍCH NGHI: mỗi giây chạy lại vòng hở `tam_chon` giây từ trạng thái quan sát cũ với ĐÚNG lệnh đã ra,
        so với BT đo ⇒ sai số trượt (EWMA) từng mô hình ⇒ lập kế hoạch bằng mô hình khớp máy nhất (có trễ chuyển 10 %)."""
        self.ls_x.append(self.x.copy())
        n = self.tam_chon
        if len(self.ls_x) <= n or len(self.lsu) < n + self.tre + 1:
            return
        x = self.ls_x[-1 - n]
        us = self.lsu[len(self.lsu) - n - self.tre:len(self.lsu) - self.tre]
        for u in us:
            x = bss._buoc_k(self.P, x, u)
        e = bt - x[:, bss.T]
        e2 = e ** 2
        self.sai = (1 - self.nho_chon) * self.sai + self.nho_chon * e2
        # lệch cân bằng (thân lồng ngấm khác, đầu dò, gió…): tích phân chậm vào offset cT của từng mô hình — CHỈ khi đang
        # giữ gần mốc (bài học PI 14/10: tích phân lúc đang chuyển mốc ⇒ dồn sai; lượt 1 ngày 15/10 dT trôi −10 °C, bão hoà)
        if not self.het and self.dang_giu():
            self.dT = np.clip(self.dT + self.ki_lech * e[:, None], -self.lech_max, self.lech_max)
            self.P["cT"] = self.cT0 + self.dT
        k = int(np.argmin(self.sai))
        if self.sai[k] < 0.9 * self.sai[self.chon]:
            self.chon = k
        del self.ls_x[:-(n + 2)]

    # kế hoạch = mảng lệnh (N, tam, 2); số lần đổi lệnh trong kế hoạch dùng để phạt "đảo lệnh liên tục"
    def _ke_hoach(self, t):
        cur, hg, H = self.u, self.huong(), self.tam
        chay = (100.0, 1.0) if hg > 0 else (0.0, 0.0)
        dich = [(float(n), 1.0) for n in NHIET_LUOI] + [(0.0, 0.0)]

        def som_nhat(a, b, t_dn, t_dl, t_luc):
            """Giây sớm nhất (tính từ t_luc) được đổi từ lệnh a sang b."""
            s = 0.0
            if a[1] != b[1]:
                s = max(s, t_dl + (self.bat_it_nhat if a[1] else self.tat_it_nhat) - t_luc)
            if a[0] != b[0] and a[1] and b[1]:
                s = max(s, t_dn + self.dung_nhiet - t_luc)
            return s

        ds, nhan, doi, dl = [], [], [], []

        def them(doan, ten, so_doi):
            u = np.empty((H, 2))
            dl.append(sum(1 for a, b in zip(doan, doan[1:]) if a[0][1] != b[0][1]) + (doan[0][0][1] != cur[1]))
            k = 0
            for v, n in doan:
                n = H - k if n is None else min(n, H - k)
                u[k:k + n] = v
                k += n
            u[k:] = doan[-1][0]
            ds.append(u)
            nhan.append(ten)
            doi.append(so_doi)

        them([(cur, None)], "giữ", 0)
        if self.dang_giu():                                # ĐANG GIỮ trong dải: chỉ tinh chỉnh Nhiệt ±4 %, cấm đảo Lệnh / chạy hết cỡ
            for v in dich:
                if v != cur and v[1] and cur[1] and abs(v[0] - cur[0]) <= 4:
                    s0 = som_nhat(cur, v, self.t_doi_nhiet, self.t_doi_lenh, t)
                    for tau in TAU:
                        if tau >= s0:
                            them([(cur, tau), (v, None)], "%s→%s@%d" % (_u(cur), _u(v), tau), 1)
            return np.stack(ds), nhan, np.array(doi, float), np.array(dl, float)
        for v in dich:
            if v == cur:
                continue
            s0 = som_nhat(cur, v, self.t_doi_nhiet, self.t_doi_lenh, t)
            for tau in TAU:
                if tau >= s0:
                    them([(cur, tau), (v, None)], "%s→%s@%d" % (_u(cur), _u(v), tau), 1 + (cur[1] != v[1]))
        if cur != chay and som_nhat(cur, chay, self.t_doi_nhiet, self.t_doi_lenh, t) <= 0:
            tdn = t if cur[0] != chay[0] else self.t_doi_nhiet
            tdl = t if cur[1] != chay[1] else self.t_doi_lenh
            for v in dich:
                if v == chay or (v[1] and int(v[0]) % 2):
                    continue
                s0 = som_nhat(chay, v, tdn, tdl, t)
                for tau in TAU_HAM:
                    if tau >= s0:
                        them([(chay, tau), (v, None)], "%s→%s@%d" % (_u(chay), _u(v), tau), 2 + (chay[1] != v[1]))
        on0, off = (0.0, 1.0), (0.0, 0.0)
        if cur[1] == 0.0:                                  # xung ngắn có tính trước (mốc thấp: SV tối thiểu 130 °C khi bật)
            s0 = som_nhat(cur, on0, self.t_doi_nhiet, self.t_doi_lenh, t)
            for tau in TAU:
                if tau >= s0:
                    for w in XUNG:
                        them([(cur, tau), (on0, w), (off, None)], "xung %ds@%d" % (w, tau), 3)
                        if self.thap and w <= 6:            # HAI xung: gò rộng đủ 30 s trong dải
                            for g in XUNG_NGHI:
                                for w2 in (2, 3, 4):
                                    them([(cur, tau), (on0, w), (off, g), (on0, w2), (off, None)],
                                         "2 xung %d+%ds@%d nghỉ %d" % (w, w2, tau, g), 5)
        elif self.thap and cur == on0:                     # đang trong xung: tắt sau τ, nghỉ g, xung w2
            s0 = som_nhat(cur, off, self.t_doi_nhiet, self.t_doi_lenh, t)
            for tau in (0, 1, 2, 3, 4, 6):
                if tau >= s0:
                    for g in XUNG_NGHI:
                        for w2 in (2, 3, 4):
                            them([(cur, tau), (off, g), (on0, w2), (off, None)], "tắt@%d nghỉ %d xung %d" % (tau, g, w2), 4)
        return np.stack(ds), nhan, np.array(doi, float), np.array(dl, float)

    def quyet_dinh(self, t):
        if self.het or (int(round(t)) % self.chu_ky):
            self.lsu.append(self.u)
            return self.u
        self._xet_moc_thap()
        U, nhan, doi, doi_lenh = self._ke_hoach(t)
        # mô hình lập kế hoạch: mô hình đang khớp máy nhất (k = 0); kiem_rong ⇒ thêm các mô hình khác để kiểm vọt lố
        thu_tu = [self.chon] + ([k for k in range(self.K) if k != self.chon] if self.kiem_rong else [])
        P = {k: v[thu_tu] for k, v in self.P.items()}
        N, H, K = U.shape[0], self.tam, len(thu_tu)
        x = self.x[thu_tu]
        for u in self.lsu[len(self.lsu) - self.tre:]:                # lệnh đã ra nhưng máy chưa "thấy"
            x = bss._buoc_k(P, x, u)
        X = np.repeat(x[:, None, :], N, 1)                          # (K, N, 8)
        BT = np.empty((K, N, H + 1))
        BT[:, :, 0] = x[:, None, bss.T]
        for s in range(H):
            X = bss.buoc(P, X, U[None, :, s, 0], U[None, :, s, 1])
            BT[:, :, s + 1] = X[..., bss.T]
        mc, hg = self.moc[self.i], self.huong()
        # thời gian + vọt lố: theo mô hình chọn (k = 0); k > 0 (nếu kiem_rong) chỉ kiểm vọt lố, lề rộng hơn — vẫn < LO_MAX
        b0 = BT[0]
        trong = np.abs(b0 - mc) <= self.dai_ke
        dem = np.full(N, float(self.dem if abs(b0[0, 0] - mc) <= self.dai_ke else 0))
        fin = np.full(N, 10 ** 6)
        toi = np.full(N, 10 ** 6)
        for s in range(1, H + 1):
            dem = np.where(trong[:, s], dem + 1, 0)
            fin[(dem >= self.giu) & (fin == 10 ** 6)] = s
            toi[trong[:, s] & (toi == 10 ** 6)] = s
        idx = np.arange(H + 1)[None, None, :]
        cua = idx <= np.minimum(fin, H)[None, :, None]
        lo = np.max(np.where(cua, hg * (BT - mc), -99.0), axis=2)   # (K, N)
        vi_pham = np.maximum(lo[0] - (self.bien_lo_giu if self.dang_giu() else self.bien_lo), 0)
        if K > 1:
            # mô hình lệch độ nhạy: chỉ kiểm cửa sổ TIẾP CẬN ngắn (vọt lố do hãm muộn); trôi dài hạn để phản hồi sửa
            cua_r = idx <= np.minimum(np.minimum(fin, H), self.cua_rong)[None, :, None]
            lo_r = np.max(np.where(cua_r, hg * (BT[1:] - mc), -99.0), axis=2).max(0)
            vi_pham = vi_pham + np.maximum(lo_r - self.bien_lo_rong, 0)
        gia = np.where(fin < 10 ** 6, fin,
                       np.where(toi < 10 ** 6, H + toi + 0.5 * np.abs(b0[:, -1] - mc),
                                2 * H + 10 * np.abs(b0[:, -1] - mc)))
        gia = gia + self.phat_doi * doi + 3.0 * np.maximum(lo[0], 0) + 10000 * (vi_pham > 0) + 100 * vi_pham
        if not self.thap and abs(b0[0, 0] - mc) < 6.0:
            # gần mốc ở chế độ thường: ĐỔI LỆNH (tắt / bật lại) bị phạt 30 s — lượt 2 ngày 15/10 bộ giải TẮT ngay tại 190 °C
            # vì Nhiệt % còn trong thời gian chờ ⇒ BT rơi khỏi dải, mất 128 s
            gia = gia + 30.0 * doi_lenh
        j = int(np.argmin(gia))
        chay = (100.0, 1.0) if hg > 0 else (0.0, 0.0)
        if not (fin < 10 ** 6).any() and abs(b0[0, 0] - mc) > 8.0:
            # chưa kế hoạch nào xong trong tầm nhìn mà còn xa mốc: CHẠY hết cỡ (lên 100 % · xuống TẮT Lệnh) — hãm để MPC lo
            k = [i for i, n in enumerate(nhan) if n.startswith("%s→" % _u(chay)) or (n == "giữ" and self.u == chay)]
            if not k and self.u != chay:
                k = [i for i, n in enumerate(nhan) if n.startswith("%s→%s@0" % (_u(self.u), _u(chay)))]
            if k:
                j = k[0]
        self.ke_hoach = "%s%s (xong ~%s s, lố %.2f · mô hình %.2f lệch %+.1f)" % (
            "[thấp] " if self.thap else "", nhan[j], fin[j] if fin[j] < 10 ** 6 else "?", lo[0, j], self.NHAY[self.chon] if self.K == len(self.NHAY) else 0,
            float(self.dT[self.chon, 0]))
        u = (float(U[j, 0, 0]), float(U[j, 0, 1]))
        if u != self.u:
            if u[1] != self.u[1]:
                self.t_doi_lenh = t
            if u[0] != self.u[0]:
                self.t_doi_nhiet = t
            self.u = u
        self.lsu.append(self.u)
        del self.lsu[:-(self.tre + self.tam_chon + 4)]
        return self.u


def _u(u):
    return "TẮT" if not u[1] else "%d%%" % u[0]


# ── Artisan: thật (UIA + registry, CHỈ ĐỌC khi kiểm) và ảo (ghi giản đồ từ bản sao số) ──────────────
class ArtisanThat:
    """Artisan giữ COM13. Hồng chỉ: đọc cấu hình (registry), đọc trạng thái nút / LCD (UIA), bấm OFF→ON→START và OFF để lưu
    (tools/artisan_ui.py). ⛔ Không mở COM, không dựng cầu."""
    COM, BAUD, SLAVE = "COM13", 57600, 1

    def kiem_cau_hinh(self):
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\artisan-scope\Artisan\Modbus") as k:
                v = {n: winreg.QueryValueEx(k, n)[0] for n in ("comport", "baudrate", "input1slave", "type")
                     if _co_khoa(winreg, k, n)}
        except OSError as e:
            return False, "không đọc được cấu hình Modbus Artisan (%s)" % e
        loi = []
        if str(v.get("comport", "")).upper() != self.COM:
            loi.append("cổng %s (cần %s)" % (v.get("comport"), self.COM))
        if int(v.get("baudrate", 0)) != self.BAUD:
            loi.append("baud %s (cần %d)" % (v.get("baudrate"), self.BAUD))
        if int(v.get("input1slave", -1)) != self.SLAVE:
            loi.append("slave %s (cần %d)" % (v.get("input1slave"), self.SLAVE))
        if "type" in v and int(v["type"]) != 0:
            loi.append("kiểu Modbus %s (cần 0 = Serial RTU, không phải TCP / cầu)" % v["type"])
        return (not loi), ("COM13 57600 slave 1" if not loi else "; ".join(loi))

    def __init__(self):
        self.lcd = None
        self.t_co_so = time.time()

    def _w(self):
        """Cửa sổ Artisan, ĐỂ YÊN chỗ cũ. ⛔ Luật chủ máy 15/10 chiều: KHÔNG chiếm màn hình anh — không restore / maximize /
        activate / SetFocus. Thu nhỏ thì Qt không vẽ ⇒ `dang_ghi` báo lý do, không tự khôi phục."""
        import artisan_ui
        return artisan_ui._cua_so(2)

    def thu_nho(self):
        """True nếu cửa sổ Artisan đang thu nhỏ (chỉ ĐỌC trạng thái, không đổi)."""
        import uiautomation as A
        w = self._w()
        try:
            return w is not None and w.GetWindowPattern().WindowVisualState == A.WindowVisualState.Minimized
        except Exception:                                   # noqa: BLE001 — không có WindowPattern thì coi như không thu nhỏ
            return False

    def hien_nut(self):
        """Artisan ẩn thanh nút chính (View → Controls tắt) ⇒ UIA không thấy ON/OFF/START. ⛔ 15/10 chiều: KHÔNG mở menu
        (menu bật lên giữa màn hình anh) — chỉ báo lỗi để anh bật lại."""
        w = self._w()
        if w is None or w.ButtonControl(Name="OFF", searchDepth=14).Exists(0.5)                 or w.ButtonControl(Name="ON", searchDepth=14).Exists(0.5):
            return
        raise RuntimeError("Artisan đang ẩn thanh nút (View → Controls) — không mở menu vì luật không chiếm màn hình")

    def dang_on(self):
        self.hien_nut()
        w = self._w()
        return w is not None and w.ButtonControl(Name="OFF", searchDepth=14).Exists(1)

    def doc_lcd(self):
        """(ET, BT) trên 2 ô LCD chính của Artisan (lớp MyQLCDNumber, UIA chỉ đọc, ~0,05 s). Lỗi ⇒ ()."""
        import uiautomation as A
        try:
            if self.lcd is None:
                w = self._w()
                # chỉ LCD trong khung ClickableLCDFrame (ET, BT, ΔET, ΔBT, extra…) — bỏ LCD đồng hồ trên thanh Controls
                self.lcd = [c for c, _ in A.WalkControl(w, maxDepth=8) if c.ClassName == "MyQLCDNumber"
                            and "ClickableLCDFrame" in (c.AutomationId or "")][:2]
            return tuple(float(c.Name.replace(",", ".")) for c in self.lcd)
        except Exception:                                   # noqa: BLE001 — UIA lỗi = coi như mất số
            self.lcd = None
            return ()

    def con_nhan_so(self, bt_panel=None):
        """Artisan còn nhận số: đọc được LCD BT, lệch BT panel ≤ 3 °C. Mất số chỉ tính là MẤT khi kéo dài > 10 s."""
        a = self.doc_lcd()
        ok = len(a) == 2 and 20 <= a[1] <= 300 and (bt_panel is None or abs(a[1] - bt_panel) <= 3.0)
        if ok:
            self.t_co_so = time.time()
        return ok or time.time() - self.t_co_so <= 10.0

    # ── Artisan ĐANG GHI (luật cứng 15/10: "Không giản đồ Artisan = bài không tính") ──
    def _anh(self, rect):
        """Ảnh vùng `rect` (toạ độ màn hình) lấy từ NỘI DUNG cửa sổ Artisan bằng PrintWindow(PW_RENDERFULLCONTENT) — đúng cả khi
        cửa sổ bị app khác che (15/10 lượt 2: VS Code che ⇒ chụp màn hình ra ảnh đứng yên ⇒ báo nhầm "đồng hồ đứng")."""
        import ctypes
        from ctypes import wintypes as wt
        from PIL import Image
        u32, g32 = ctypes.windll.user32, ctypes.windll.gdi32
        H_ = ctypes.c_void_p                                 # handle 64 bit — khai báo kiểu, không thì tràn int
        u32.GetWindowDC.restype, u32.GetWindowDC.argtypes = H_, [H_]
        u32.ReleaseDC.argtypes = [H_, H_]
        u32.PrintWindow.argtypes = [H_, H_, ctypes.c_uint]
        u32.GetWindowRect.argtypes = [H_, ctypes.c_void_p]
        g32.CreateCompatibleDC.restype, g32.CreateCompatibleDC.argtypes = H_, [H_]
        g32.CreateCompatibleBitmap.restype, g32.CreateCompatibleBitmap.argtypes = H_, [H_, ctypes.c_int, ctypes.c_int]
        g32.SelectObject.restype, g32.SelectObject.argtypes = H_, [H_, H_]
        g32.GetDIBits.argtypes = [H_, H_, ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint]
        g32.DeleteObject.argtypes = [H_]
        g32.DeleteDC.argtypes = [H_]
        w = self._w()
        hwnd = w.NativeWindowHandle
        r = wt.RECT()
        u32.GetWindowRect(hwnd, ctypes.byref(r))
        W, H = r.right - r.left, r.bottom - r.top
        hdc = u32.GetWindowDC(hwnd)
        mdc = g32.CreateCompatibleDC(hdc)
        bmp = g32.CreateCompatibleBitmap(hdc, W, H)
        g32.SelectObject(mdc, bmp)
        u32.PrintWindow(hwnd, mdc, 2)
        bi = (ctypes.c_uint32 * 10)(40, W, (-H) & 0xFFFFFFFF, 1 | (32 << 16), 0, 0, 0, 0, 0, 0)
        buf = ctypes.create_string_buffer(W * H * 4)
        g32.GetDIBits(mdc, bmp, 0, H, buf, ctypes.byref(bi), 0)
        g32.DeleteObject(bmp)
        g32.DeleteDC(mdc)
        u32.ReleaseDC(hwnd, hdc)
        im = Image.frombuffer("RGBA", (W, H), buf, "raw", "BGRA", 0, 1).convert("RGB")
        im = im.crop((rect.left - r.left, rect.top - r.top, rect.right - r.left, rect.bottom - r.top))
        return np.array(im, dtype=int)

    def _dong_ho(self):
        """Ô đồng hồ = MyQLCDNumber ngoài khung LCD nhiệt, trên thanh Controls (UIA đọc ra '0' ⇒ so ẢNH vùng đồng hồ)."""
        import uiautomation as A
        w = self._w()
        for c, _ in A.WalkControl(w, maxDepth=8):
            if c.ClassName == "MyQLCDNumber" and "ClickableLCDFrame" not in (c.AutomationId or "") \
                    and c.BoundingRectangle.top < 200 and c.BoundingRectangle.width() > 80:
                return c.BoundingRectangle
        return None

    def _duong_cong(self):
        """Số điểm ảnh đường ET (đỏ) và BT (xanh đậm) trên đồ thị Artisan."""
        import uiautomation as A
        cv = self._w().Control(searchDepth=5, ClassName="MplCanvas")
        a = self._anh(cv.BoundingRectangle)
        r, g, b = a[..., 0], a[..., 1], a[..., 2]
        et = int(((r > 200) & (g < 70) & (b < 70)).sum())
        bt = int(((r < 50) & (g < 50) & (b > 80) & (b < 180)).sum())
        return et, bt

    def dang_ghi(self, cho=3.0):
        """Đủ 3 điều kiện: START đã vô hiệu (đang ghi) · đồng hồ chạy (ảnh đổi sau `cho` s) · có đường ET/BT. Trả (ok, chi tiết)."""
        w = self._w()
        if w is None:
            return False, "không thấy cửa sổ Artisan"
        if self.thu_nho():
            return False, "cửa sổ Artisan đang THU NHỎ — PrintWindow không vẽ được; không tự khôi phục (luật không chiếm màn hình)"
        st = w.ButtonControl(Name="START", searchDepth=14)
        off = w.ButtonControl(Name="OFF", searchDepth=14)
        nut = off.Exists(1) and off.IsEnabled and (not st.Exists(0.5) or not st.IsEnabled)
        rc = self._dong_ho()
        if rc is None:
            return False, "không thấy ô đồng hồ Artisan"
        a1 = self._anh(rc)
        time.sleep(cho)
        a2 = self._anh(rc)
        chay = bool(np.abs(a1 - a2).sum() > 0)
        et, bt = self._duong_cong()
        lcd = self.doc_lcd()
        # máy nguội: ET ≈ BT ⇒ đường ET vẽ ĐÈ lên BT (15/10 13:27 BT 43 kẹt 5 điểm ảnh) ⇒ đủ = ET có đường + LCD có số, ET−BT < 5
        trung = len(lcd) == 2 and 20 <= lcd[1] <= 300 and abs(lcd[0] - lcd[1]) < 5.0
        cong = et > 5 and (bt > 5 or trung)
        self.anh_dong_ho, self.t_anh = a2, time.time()
        ok = nut and chay and cong
        return ok, "START %s · đồng hồ %s · đường ET %d BT %d điểm ảnh" % (
            "đã vô hiệu (đang ghi)" if nut else "CÒN BẤM ĐƯỢC (chưa ghi)", "chạy" if chay else "ĐỨNG", et, bt)

    def con_ghi(self):
        """Gọi mỗi ~30 s trong lượt: ảnh đồng hồ phải khác lần trước."""
        rc = self._dong_ho()
        if rc is None:
            return False
        a = self._anh(rc)
        cu = getattr(self, "anh_dong_ho", None)
        self.anh_dong_ho = a
        return cu is None or bool(np.abs(a - cu).sum() > 0)

    def bam_start(self):
        """Thử lại START bằng UIA: theo tên, rồi theo AutomationId + vị trí trên thanh Controls."""
        import uiautomation as A
        w = self._w()
        b = w.ButtonControl(Name="START", searchDepth=14)
        if b.Exists(2) and b.IsEnabled:
            import artisan_ui
            artisan_ui._bam(w, "START")
            return True
        for c, _ in A.WalkControl(w, maxDepth=14):
            if c.ControlTypeName == "ButtonControl" and c.ClassName == "QPushButton" and "START" in (c.Name or "").upper()                     and c.IsEnabled:
                c.GetInvokePattern().Invoke()
                return True
        return False

    def bat_on(self, cho=6.0):
        """Artisan chưa mở ⇒ mở (Popen exe); đang OFF ⇒ bấm ON bằng UIA (chủ máy cho phép 15/10). Không START.
        15/10 13:15: sau `tat_luu` Artisan nằm OFF ⇒ `kiem()` lượt sau báo "chưa ON" — gọi hàm này trước `kiem()`."""
        import artisan_ui
        w = artisan_ui._cua_so(2)
        if w is None:
            si = subprocess.STARTUPINFO()                   # mở KHÔNG kích hoạt (SW_SHOWNOACTIVATE) — không giành bàn phím của anh
            si.dwFlags, si.wShowWindow = subprocess.STARTF_USESHOWWINDOW, 4
            subprocess.Popen([artisan_ui.EXE], startupinfo=si)
            w = artisan_ui._cua_so(60)
            if w is None:
                return False
            time.sleep(8)
            artisan_ui.dong_hop_tai_tro()                   # hộp "Artisan is free to use!" chặn nút chính (15/10 17:10)
        self.hien_nut()
        if self.dang_on():
            return True
        artisan_ui._bam(self._w(), "ON")
        time.sleep(cho)
        self.lcd, self.t_co_so = None, time.time()
        return self.dang_on()

    def kiem(self, bt_panel=None):
        ok, ly = self.kiem_cau_hinh()
        if not ok:
            return False, "Artisan sai cấu hình: " + ly
        if not self.dang_on():
            return False, "Artisan chưa ON"
        a = self.doc_lcd()                                  # 15/10 13:20: phải ĐỌC ĐƯỢC số thật, không dùng ân hạn 10 s
        if len(a) != 2 or not 20 <= a[1] <= 300 or (bt_panel is not None and abs(a[1] - bt_panel) > 3.0):
            return False, "Artisan không nhận số (LCD %s — Modbus COM13 chưa nối? lệch BT panel > 3 °C?)" % (str(a) if a else "không đọc được",)
        return True, "Artisan " + ly + ", ON, LCD có số"

    def reset_start(self):
        import artisan_ui
        self.hien_nut()
        kq = artisan_ui.bat_ghi()          # OFF (autosave cất bản cũ) → ON (giản đồ mới) → START
        self.lcd, self.t_co_so = None, time.time()
        return kq

    def tat_luu(self):
        import artisan_ui
        self.hien_nut()
        return artisan_ui.tat_luu()


def _co_khoa(winreg, k, n):
    try:
        winreg.QueryValueEx(k, n)
        return True
    except OSError:
        return False


class ArtisanAo:
    """Artisan ảo cho dry-run: đọc board (BT thật của máy ảo) mỗi giây, ghi giản đồ .alog cùng định dạng để chấm như thật."""

    def __init__(self, may, thu_muc=None, nhieu=0.1, rng=None):
        self.may, self.thu_muc, self.nhieu = may, thu_muc, nhieu
        self.rng = rng or np.random.default_rng()
        self.on, self.ghi_so, self.t = True, False, 0.0
        self.timex, self.temp1, self.temp2 = [], [], []

    def kiem(self, bt_panel=None):
        return (True, "Artisan ảo COM13 57600 slave 1, ON") if self.on else (False, "Artisan ảo chưa ON")

    def con_nhan_so(self, bt_panel=None):
        return self.on

    def dang_ghi(self, cho=3.0):
        return self.ghi_so, "Artisan ảo đang ghi" if self.ghi_so else "Artisan ảo chưa ghi"

    def con_ghi(self):
        return self.ghi_so

    def bam_start(self):
        self.ghi_so = True
        return True

    def reset_start(self):
        self.timex, self.temp1, self.temp2, self.t, self.ghi_so = [], [], [], 0.0, True
        return True

    def mau(self):
        """Gọi mỗi giây máy ảo (đồng hồ ảo)."""
        if not self.ghi_so:
            return
        x = self.may.x
        self.timex.append(round(self.t + 0.6, 3))
        self.temp2.append(round(float(x[bss.T]) + self.rng.normal(0, self.nhieu), 1))
        self.temp1.append(round(float(x[bss.E]) + self.rng.normal(0, self.nhieu), 1))
        self.t += 1.0

    def tat_luu(self):
        self.ghi_so = False
        d = {"timex": self.timex, "temp1": self.temp1, "temp2": self.temp2, "mode": "C", "timeindex": [-1, 0, 0, 0, 0, 0, 0, 0],
             "title": "OTL-Hong dry-run", "roastisodate": time.strftime("%Y-%m-%d"), "roasttime": time.strftime("%H:%M:%S")}
        if self.thu_muc is None:
            self.alog = d
            return None
        os.makedirs(self.thu_muc, exist_ok=True)
        duong = os.path.join(self.thu_muc, "OTL-Hong_dry-run_%s.alog" % time.strftime("%Y-%m-%d_%H%M%S"))
        with open(duong, "w", encoding="utf-8") as f:
            f.write(repr(d))
        return duong


# ── Máy: panel thật và panel ảo (bản sao số) — CÙNG giao diện ─────────────────────────────────────
class PanelAo:
    """Giống Panel (doc_tat_ca / dat_nhiet / lenh_nhiet) nhưng chạy trên bản sao số MayMoPhong. Board chỉ nghe HMI khi $13 = 0."""

    def __init__(self, may, nhiet0=40.0, lenh0=1, rng=None):
        self.may, self.rng = may, rng or np.random.default_rng()
        self.dat_n, self.lenh = float(nhiet0), int(lenh0)
        self.do = tuple(may.x[[bss.T, bss.E, bss.B]])
        self.may.dat(self.dat_n, self.lenh)
        self.so_ghi = 0

    def tick(self):
        self.do = self.may.tick()

    def doc_tat_ca(self):
        bt, et, bu = self.do
        return {"lenh_nhiet": self.lenh, "pc_control": 0, "man": MAN_RANG, "ma": 163, "bt": bt, "et": et, "gio": 85.0,
                "trong": 85.0, "nhiet": self.dat_n if self.lenh else 0.0, "buong": bu, "dat_trong": 85, "dat_gio": 85,
                "dat_nhiet": int(round(self.dat_n)), "ror_fw": self.may.ror_fw}

    def dat_nhiet(self, pct):
        self.dat_n = float(int(max(0, min(100, round(pct)))))
        self.may.dat(self.dat_n, self.lenh)
        self.so_ghi += 1

    def lenh_nhiet(self, bat):
        self.lenh = 1 if bat else 0
        self.may.dat(self.dat_n, self.lenh)
        self.so_ghi += 1

    def dang_nhap(self, pin=None):
        return MAN_RANG


class DongHoThat:
    def now(self):
        return time.time()

    def sleep(self, s):
        time.sleep(max(0.0, s))


class DongHoAo:
    """Đồng hồ ảo: mỗi giây ngủ = 1 giây máy ảo + 1 mẫu Artisan ảo."""

    def __init__(self, panel, artisan):
        self.panel, self.artisan, self.t = panel, artisan, 0.0

    def now(self):
        return self.t

    def sleep(self, s):
        for _ in range(int(round(s))):
            self.panel.tick()
            self.artisan.mau()
            self.t += 1.0


# ── tự kiểm sau mỗi thao tác + vòng lái ─────────────────────────────────────────────────────────
def tu_kiem(d, artisan, cho_nhiet=None, cho_lenh=None):
    """Kiểm như người đứng máy nhìn: màn rang ($21), mã ($40), Lệnh nhiệt ($1), Nhiệt đặt ($M36), cờ PC ($13), Artisan.
    Trả list lỗi (rỗng = ổn)."""
    loi = []
    if d.get("man") != MAN_RANG:
        loi.append("màn $21 = %s (không phải màn rang / chưa đăng nhập)" % d.get("man"))
    if d.get("pc_control"):
        loi.append("cờ PC control $13 BẬT — board không nghe panel")
    if any(d.get("ma") in r for r in MA_DUNG):
        loi.append("mã $40 = %s (cảnh báo / lỗi nghiêm trọng)" % d.get("ma"))
    if cho_lenh is not None and int(d.get("lenh_nhiet", -1)) != int(cho_lenh):
        loi.append("Lệnh nhiệt $1 = %s, đã ghi %d" % (d.get("lenh_nhiet"), cho_lenh))
    if cho_nhiet is not None and int(d.get("dat_nhiet", -1)) != int(round(cho_nhiet)):
        loi.append("Nhiệt đặt $M36 = %s, đã ghi %d" % (d.get("dat_nhiet"), round(cho_nhiet)))
    if artisan is not None and not artisan.con_nhan_so(d.get("bt")):
        loi.append("Artisan không còn nhận số")
    return loi


def chay_de(panel, artisan, dong_ho, giai, log_csv=None, in_ra=print, het_luc=None, cho_noi=3, tat_cuoi=True):
    """MỘT lượt đề, cùng logic cho máy thật và bản sao số. Thứ tự (luật chủ máy 14–15/10):
    Artisan kiểm (COM13 57600 slave 1, ON, nhận số) → Artisan RESET + START → Hồng nối panel, tự kiểm → lái tới hết mốc
    → TẮT Lệnh nhiệt → Artisan OFF (lưu giản đồ) → Hồng tự chấm từ .alog. Không dừng / khởi động lại giữa chừng.
    `tat_cuoi=False` (bước VỀ ĐẦU): xong sạch thì GIỮ Lệnh + mức giữ cho lượt sau; dừng vì bất kỳ lý do nào khác vẫn TẮT."""
    ok, ly = artisan.kiem()
    in_ra("ARTISAN KIEM: %s" % ly)
    if not ok:
        return {"dung": "artisan", "ly_do": ly}
    artisan.reset_start()
    t0 = dong_ho.now()
    in_ra("ARTISAN RESET + START")
    dong_ho.sleep(cho_noi)                               # Artisan có mẫu đầu rồi Hồng mới nối panel
    # ⛔ luật cứng 15/10: "Không giản đồ Artisan = bài không tính" — chưa ĐANG GHI thì KHÔNG lái
    ok, ct = artisan.dang_ghi()
    if not ok:
        in_ra("ARTISAN CHUA GHI (%s) — thu START lai bang UIA" % ct)
        artisan.bam_start()
        dong_ho.sleep(2)
        ok, ct = artisan.dang_ghi()
    in_ra("ARTISAN DANG GHI: %s" % ct)
    if not ok:
        panel.lenh_nhiet(False)
        in_ra("DUNG: Artisan khong ghi — khong lai mu; TAT Lenh nhiet")
        return {"dung": "artisan_khong_ghi", "ly_do": ct}
    d = panel.doc_tat_ca()
    loi = tu_kiem(d, artisan)
    if loi:
        in_ra("DUNG TRUOC KHI LAI: " + "; ".join(loi))
        return {"dung": "tu_kiem", "ly_do": loi, "alog": artisan.tat_luu()}
    giai.bat_dau(dong_ho.now() - t0, d["bt"], d["et"], d["buong"], (d["dat_nhiet"], d["lenh_nhiet"]))
    in_ra("NHAN QUYEN · BT %.1f ET %.1f buong %s · Nhiet %d%% Lenh %d" % (d["bt"], d["et"], d["buong"], d["dat_nhiet"],
                                                                      d["lenh_nhiet"]))
    f = open(log_csv, "a", newline="", encoding="utf-8") if log_csv else None
    w = csv.writer(f) if f else None
    if w:
        w.writerow(["gio", "t", "moc", "bt", "et", "buong", "nhiet", "lenh_nhiet", "flags_hex", "ma", "ror_fw_bo_qua",
                    "ke_hoach", "ghi_chu", "k_david"])
    ly_do, t_doc_ok, cho, xong_sach = "xong", dong_ho.now(), None, False
    ls_k = []                                            # (t, BT) 30 s cho k David sống — tham khảo, không lái
    try:
        while not giai.het:
            now = dong_ho.now()
            t = now - t0
            try:
                d = panel.doc_tat_ca()
                t_doc_ok = now
            except (OSError, ValueError) as e:
                if now - t_doc_ok > MAT_SO_GIAY:
                    ly_do = "MAT SO LIEU > %.0f s (%s)" % (MAT_SO_GIAY, e)
                    break
                dong_ho.sleep(1)
                continue
            # ── lớp an toàn: độc lập với bộ giải, không bộ giải nào ghi đè ──
            mc = giai.moc[giai.i]
            moc_tren = max(mc, giai.truoc if giai.truoc is not None else mc)
            if d["et"] > ET_MAX:
                ly_do = "AN TOAN ET %.1f > %.0f" % (d["et"], ET_MAX)
                break
            if d["bt"] > min(moc_tren + BT_TREN_MOC, BT_TUYET_DOI):
                ly_do = "AN TOAN BT %.1f > %.0f" % (d["bt"], min(moc_tren + BT_TREN_MOC, BT_TUYET_DOI))
                break
            if t > TRAN_GIAY or (het_luc is not None and time.time() > het_luc):
                ly_do = "HET GIO"
                break
            loi = tu_kiem(d, None, *(cho or (None, None)))
            if loi:
                if any("PC control" in x or "mã" in x or "màn" in x for x in loi):
                    ly_do = "TU KIEM: " + "; ".join(loi)
                    break
                in_ra("%5.0f CANH BAO %s — ghi lại" % (t, "; ".join(loi)))
                panel.dat_nhiet(giai.u[0])
                panel.lenh_nhiet(bool(giai.u[1]))
            cho = None
            ls_k.append((t, d["bt"]))
            ls_k = ls_k[-40:]
            k_dv = david.k_song(doc_hoi_quy(ls_k, 30), d["et"], d["bt"])
            xong = giai.cap_nhat(t, d["bt"], d["et"], d["buong"])
            if xong is not None:
                in_ra("%5.0f DAT MOC %d (noi bo ±%.1f %d s)" % (t, xong, giai.dai_dem, giai.giu))
                if giai.het:
                    break
            u_cu = giai.u
            u = giai.quyet_dinh(t)
            ghi = ""
            if u != u_cu:
                if u[1] and (u[0] != u_cu[0] or not u_cu[1]):   # bật lại Lệnh: ghi Nhiệt TRƯỚC (panel còn giữ mức cũ)
                    panel.dat_nhiet(u[0])
                if u[1] != u_cu[1]:
                    panel.lenh_nhiet(bool(u[1]))
                ghi = "nhiet -> %s" % _u(u)
                cho = (u[0] if u[1] else None, u[1])
                in_ra("%5.0f BT %.1f moc %d · %s · %s · k %s" % (t, d["bt"], mc, ghi, giai.ke_hoach,
                                                              "%.3f" % k_dv if k_dv is not None else "—"))
            if w:
                gio = time.strftime("%H:%M:%S", time.localtime(now)) if now > 1e9 else bss._hms(now)
                w.writerow([gio, round(t, 1), mc, d["bt"], d["et"], d["buong"], u[0], int(u[1]), "%04X" % (2 * int(u[1])),
                            d["ma"], d.get("ror_fw", ""), giai.ke_hoach, ghi,
                            round(k_dv, 4) if k_dv is not None else ""])
                f.flush()
            if artisan is not None and not artisan.con_nhan_so(d["bt"]):
                ly_do = "Artisan mất số > 10 s"
                break
            if artisan is not None and int(t) % 30 == 15 and not artisan.con_ghi():
                ly_do = "Artisan NGỪNG GHI (đồng hồ đứng)"
                break
            dong_ho.sleep(max(0.0, 1.0 - (dong_ho.now() - now)))
        xong_sach = ly_do == "xong" and giai.het
    finally:
        tat = tat_cuoi or not xong_sach
        if tat:
            panel.lenh_nhiet(False)                     # xong / dừng: TẮT Lệnh nhiệt (lồng trống, gió 85 % tự nguội)
        if f:
            f.close()
    dong_ho.sleep(1)
    d = panel.doc_tat_ca()
    loi = tu_kiem(d, artisan, cho_lenh=0 if tat else None)
    in_ra("%s · %s · tu kiem: %s" % (ly_do, "TAT Lenh nhiet" if tat else "GIU Nhiet %d%% Lenh %d" % (giai.u[0], giai.u[1]),
                                     "; ".join(loi) if loi else "màn rang, $13=0, $1=%d, mã %s, Artisan có số"
                                     % (d["lenh_nhiet"], d["ma"])))
    alog = artisan.tat_luu()
    in_ra("ARTISAN OFF · gian do: %s" % alog)
    if alog:
        ts, bts, _, _ = doc_alog(alog)
        in_ra("KIEM ALOG: %d mau · %.0f s · BT %.1f..%.1f" % (len(ts), (ts[-1] - ts[0]) if ts else 0,
                                                            min(bts) if bts else 0, max(bts) if bts else 0))
    return {"dung": ly_do, "alog": alog, "xong_noi_bo": giai.xong, "so_ghi": getattr(panel, "so_ghi", None),
            "sach": xong_sach}


# ── dry-run + Monte Carlo ─────────────────────────────────────────────────────────────────────
def dung_may_ao(seed, lech=True):
    """Một máy ảo đã NGẤM: trạng thái 14/10 20:18:57 lệch W ±5 °C, giữ Nhiệt 36–44 % thêm 3–7 phút (như bước làm nóng ngấm)."""
    rng = np.random.default_rng(seed)
    p0 = bss.doc_tham_so()
    p = bss.lech_tham_so(p0, rng) if lech else dict(p0)
    x = bss.trang_thai_ngam().copy()
    dw = rng.normal(0, 5)
    x[bss.W1] += dw
    x[bss.W2] += dw
    n0 = float(rng.integers(36, 45)) if lech else 40.0
    may = bss.MayMoPhong(x, p, rng, tre_do=int(rng.integers(0, 3)) if lech else 1,
                         tre_lenh=int(rng.integers(0, 3)) if lech else 1)
    may.dat(n0, 1)
    for _ in range(int(rng.integers(180, 421)) if lech else 300):
        may.tick()
    return may, n0, rng


def mot_luot(seed, lo_max=LO_MAX, thu_muc=None, in_ra=None, lech=True):
    may, n0, rng = dung_may_ao(seed, lech)
    panel = PanelAo(may, n0, 1, rng)
    art = ArtisanAo(may, thu_muc, rng=rng)
    dh = DongHoAo(panel, art)
    if thu_muc:
        os.makedirs(thu_muc, exist_ok=True)
    log_csv = os.path.join(thu_muc, "log_dry_run.csv") if thu_muc else None
    kq = chay_de(panel, art, dh, GiaiDe(), log_csv=log_csv, in_ra=in_ra or (lambda s: None),
                 cho_noi=int(rng.integers(3, 9)))
    if kq.get("alog"):
        ch = cham_alog(kq["alog"], lo_max=lo_max)
    else:
        a = art.alog
        ch = cham_bt(a["timex"], a["temp2"], lo_max=lo_max)
        ch["lo0"] = cham_bt(a["timex"], a["temp2"], lo_max=0.0)["dat"]
    ch.update(seed=seed, dung=kq["dung"], so_ghi=kq.get("so_ghi"), bt0=float(may.ls_bt[0]) if may.ls_bt else None)
    return ch


def _mot_luot_mc(a):
    return mot_luot(*a)


def monte_carlo(so_luot=200, lo_max=LO_MAX, luong=None, seed0=1000):
    from multiprocessing import Pool
    luong = luong or max(1, (os.cpu_count() or 2) - 1)
    t0 = time.time()
    with Pool(luong) as pool:
        kq = pool.map(_mot_luot_mc, [(seed0 + i, lo_max) for i in range(so_luot)])
    tg = np.array([k["tong_giay"] for k in kq if k["tong_giay"] is not None], float)
    dat = sum(k["dat"] for k in kq)
    co_lo = sum(1 for k in kq if any(m["truot"] for m in k["moc"]))
    tom = {"so_luot": so_luot, "dat_10_10": dat, "ti_le": dat / so_luot, "luot_vot_lo": co_lo,
           "lo_len_max": max(k["lo_len"] for k in kq), "lo_xuong_max": max(k["lo_xuong"] for k in kq),
           "lo_len_p95": float(np.percentile([k["lo_len"] for k in kq], 95)),
           "lo_xuong_p95": float(np.percentile([k["lo_xuong"] for k in kq], 95)),
           "dat_neu_lo_0": sum(1 for k in kq if k.get("lo0")),
           "tong_p50": float(np.percentile(tg, 50)) if len(tg) else None,
           "tong_p95": float(np.percentile(tg, 95)) if len(tg) else None, "tong_max": float(tg.max()) if len(tg) else None,
           "khong_xong": so_luot - len(tg), "qua_10_phut": int((tg > HAN_DE).sum()),
           "dung_khac": sorted({k["dung"] for k in kq if k["dung"] != "xong"}), "giay_tinh": round(time.time() - t0)}
    hong = [(k["seed"], k["so_moc_dat"], k["tong_giay"], k["lo_len"], k["lo_xuong"], k["dung"]) for k in kq if not k["dat"]]
    return tom, hong, kq


# ── máy thật ───────────────────────────────────────────────────────────────────────────────────
def ngam(phut, nhiet, duong_csv, gio=85, trong=85, bt_max=245.0, mat_so=10.0):
    """LÀM NÓNG NGẤM (không tính vào bài): đặt THẲNG mức cân bằng (giáo trình mục 3 — đừng lái liên tục), gió / trống cố định,
    rồi chỉ đọc + giữ an toàn mỗi 1 s. Hết giờ: GIỮ NGUYÊN Lệnh nhiệt + mức đặt để bộ giải đề nhận máy đang đứng.
    Tự dừng (TẮT Lệnh nhiệt): BT > bt_max, ET > ET_MAX, mất số > mat_so giây, mã lỗi, cờ PC control bật."""
    p = Panel()
    if p.doc(21, 1)[0] != MAN_RANG:
        print("màn", p.dang_nhap(), flush=True)
    d = p.doc_tat_ca()
    if d["pc_control"]:
        sys.exit("cờ PC control BẬT — board không nghe panel; dừng")
    p.dat_gio(gio)
    p.dat_trong(trong)
    p.dat_nhiet(nhiet)
    p.lenh_nhiet(True)
    time.sleep(1.5)
    d = p.doc_tat_ca()
    print("NGAM BAT · dat gio %s trong %s nhiet %s lenh %s · ma %s man %s pc %s" % (
        d["dat_gio"], d["dat_trong"], d["dat_nhiet"], d["lenh_nhiet"], d["ma"], d["man"], d["pc_control"]), flush=True)
    f = open(duong_csv, "a", newline="", encoding="utf-8")
    w = csv.writer(f)
    w.writerow(["gio", "bt", "et", "buong", "nhiet", "gio_pct", "trong", "lenh_nhiet", "pc", "ma"])
    t0 = t_ok = time.time()
    ly_do = "HET GIO NGAM"
    while time.time() - t0 < phut * 60:
        now = time.time()
        try:
            d = p.doc_tat_ca()
            t_ok = now
        except (OSError, ValueError) as e:
            if now - t_ok > mat_so:
                ly_do = "MAT SO PANEL %s" % e
                break
            time.sleep(1)
            continue
        w.writerow([time.strftime("%H:%M:%S"), d["bt"], d["et"], d["buong"], d["nhiet"], d["gio"], d["trong"], d["lenh_nhiet"],
                    d["pc_control"], d["ma"]])
        f.flush()
        if d["bt"] > bt_max or d["et"] > ET_MAX:
            ly_do = "AN TOAN BT %.1f ET %.1f" % (d["bt"], d["et"])
            break
        if d["pc_control"] or any(d["ma"] in r for r in MA_DUNG):
            ly_do = "TU KIEM pc %s ma %s" % (d["pc_control"], d["ma"])
            break
        if int(now - t0) % 60 == 0:
            print("%s NGAM %4.1f ph · BT %.1f ET %.1f buong %s · nhiet %s lenh %s gio %s trong %s ma %s" % (
                time.strftime("%H:%M:%S"), (now - t0) / 60, d["bt"], d["et"], d["buong"], d["nhiet"], d["lenh_nhiet"],
                d["gio"], d["trong"], d["ma"]), flush=True)
        time.sleep(max(0.0, 1.0 - (time.time() - now)))
    f.close()
    if ly_do != "HET GIO NGAM":
        try:
            p.lenh_nhiet(False)
        finally:
            print("%s %s — TAT Lenh nhiet" % (time.strftime("%H:%M:%S"), ly_do), flush=True)
        return False
    print("%s %s — giữ nguyên Nhiệt %s%% Lệnh bật cho bộ giải" % (time.strftime("%H:%M:%S"), ly_do, nhiet), flush=True)
    return True


def ve_dau(muc, duong_csv, phut_max=15.0, giay_on=90, nhiet0=None, giu_muc=None):
    """Đưa máy về ĐIỀU KIỆN ĐẦU giống nhau trước mỗi lượt (không bấm Artisan): vòng NGOÀI chậm đã kiểm trên máy thật
    (giáo trình mục 1b): mỗi 30 s Nhiệt += 0,4·(muc − BT) (kẹp ±3 %/lần); ổn định = |BT − muc| ≤ 1,5 và |dốc 60 s| < 1 °C/ph
    liên tục `giay_on` s. Tự dừng (TẮT Lệnh) như lượt đề. Trả mức Nhiệt đang giữ, None nếu phải dừng."""
    p = Panel()
    d = p.doc_tat_ca()
    loi = tu_kiem(d, None)
    if loi:
        print("VE DAU DUNG: " + "; ".join(loi), flush=True)
        return None
    n = float(nhiet0 if nhiet0 is not None else (d["dat_nhiet"] if d["lenh_nhiet"] else 40))
    p.dat_nhiet(n)
    p.lenh_nhiet(True)
    f = open(duong_csv, "a", newline="", encoding="utf-8")
    w = csv.writer(f)
    t0 = t_ok = t_chinh = time.time()
    ls, t_on = [], None
    try:
        while True:
            now = time.time()
            try:
                d = p.doc_tat_ca()
                t_ok = now
            except (OSError, ValueError):
                if now - t_ok > MAT_SO_GIAY:
                    print("VE DAU: mat so panel — TAT Lenh", flush=True)
                    p.lenh_nhiet(False)
                    return None
                time.sleep(1)
                continue
            if d["bt"] > BT_TUYET_DOI or d["et"] > ET_MAX or now - t0 > phut_max * 60 or tu_kiem(d, None):
                print("VE DAU DUNG: BT %.1f ET %.1f %s — TAT Lenh" % (d["bt"], d["et"], tu_kiem(d, None)), flush=True)
                p.lenh_nhiet(False)
                return None
            ls.append((now, d["bt"]))
            ls = [x for x in ls if now - x[0] <= 60]
            doc = doc_hoi_quy(ls, 60)
            if abs(d["bt"] - muc) <= 1.5 and abs(doc) < 1.0:
                t_on = t_on or now
                if now - t_on >= giay_on:
                    break
            else:
                t_on = None
            if giu_muc is not None and d["bt"] < muc - 10 and d["bt"] + doc / 2 < muc - 4:
                # còn xa dưới mức: CHẠY 100 %, hãm theo BT dự báo 30 s về THẲNG mức giữ đã đo (15/10: vòng chậm mất 10 phút)
                if round(n) != 100:
                    n = 100.0
                    p.dat_nhiet(100)
                    p.lenh_nhiet(True)
                    print("%s VE DAU CHAY 100%% · BT %.1f" % (time.strftime("%H:%M:%S"), d["bt"]), flush=True)
                t_chinh = now
            elif giu_muc is not None and round(n) == 100:
                n = float(giu_muc)
                p.dat_nhiet(round(n))
                t_chinh = now
                print("%s VE DAU HAM -> %d%% · BT %.1f doc %+.1f" % (time.strftime("%H:%M:%S"), round(n), d["bt"], doc), flush=True)
            elif now - t_chinh >= 30:
                t_chinh = now
                # tiến về mức theo BT DỰ BÁO 30 s (BT + dốc/2) để không vọt — dốc hồi quy 60 s, không dùng RoR firmware
                n = max(0.0, min(100.0, n + max(-3.0, min(3.0, 0.4 * (muc - (d["bt"] + doc / 2))))))
                p.dat_nhiet(round(n))
                print("%s VE DAU BT %.1f doc %+.1f/ph -> Nhiet %d%%" % (time.strftime("%H:%M:%S"), d["bt"], doc, round(n)),
                      flush=True)
            w.writerow([time.strftime("%H:%M:%S"), d["bt"], d["et"], d["buong"], round(n), d["lenh_nhiet"], d["ma"], doc])
            f.flush()
            time.sleep(max(0.0, 1.0 - (time.time() - now)))
    finally:
        f.close()
    print("%s VE DAU XONG · BT %.1f · giữ Nhiệt %d%%" % (time.strftime("%H:%M:%S"), d["bt"], round(n)), flush=True)
    return round(n)


def giai_de_that(het_luc_hhmm, thu_muc):
    """MÁY THẬT. Chỉ chạy khi anh Thành đã DUYỆT kế hoạch và cho quyền nhiệt (biến HONG_DUOC_LAI=1 + giờ hết quyền)."""
    if os.environ.get("HONG_DUOC_LAI") != "1":
        sys.exit("Chưa có quyền lái (HONG_DUOC_LAI=1) — anh Thành duyệt kế hoạch trước.")
    h, m = (int(v) for v in het_luc_hhmm.split(":"))
    lt = time.localtime()
    het = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, h, m, 0, 0, 0, -1))
    if het <= time.time():
        sys.exit("Giờ hết quyền đã qua.")
    os.makedirs(thu_muc, exist_ok=True)
    nhat_ky = open(os.path.join(thu_muc, "giai_de.txt"), "a", encoding="utf-8")

    def in_ra(s):
        dong = time.strftime("%H:%M:%S ") + s
        print(dong, flush=True)
        nhat_ky.write(dong + "\n")
        nhat_ky.flush()

    art = ArtisanThat()
    panel = Panel()
    kq = chay_de(panel, art, DongHoThat(), GiaiDe(), log_csv=os.path.join(thu_muc, "log.csv"), in_ra=in_ra, het_luc=het)
    if kq.get("alog"):
        in_ra(in_cham(cham_alog(kq["alog"])))
    nhat_ky.close()
    return kq


def _gio_het(hhmm):
    h, m = (int(v) for v in hhmm.split(":"))
    lt = time.localtime()
    het = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, h, m, 0, 0, 0, -1))
    if het <= time.time():
        sys.exit("Giờ hết quyền đã qua.")
    return het


def phien(so_luot, het_luc_hhmm, thu_muc, ngam_phut=0.0, n_ngam=55, dau=200, giu_dau=30, nguoi=True):
    """CẢ BUỔI trong MỘT tiến trình (chủ máy 15/10: "nâng tốc độ lên gấp 5"): [ngấm] → N × (VỀ ĐẦU bằng MPC 1 mốc → LƯỢT ĐỀ
    → CHẤM .alog + k David) → AN TOÀN + làm mát. Về đầu: giữ 30 s, dải đếm ±1,5 (bản sao số 24/24 seed, trung vị ~70 s,
    lâu nhất 284 s; giữ 60 s / ±1,3 kẹt 1/24 seed ở 197–198 °C đảo 100↔47 %). Mỗi bước có giản đồ Artisan riêng (chay_de tự RESET/START/OFF). Code đóng băng sẵn
    (một tiến trình). Dừng sạch ⇒ lượt sau; dừng vì an toàn / hết giờ / Artisan ⇒ thôi, `an_toan`. Kết quả: tong_ket.jsonl."""
    import json
    if os.environ.get("HONG_DUOC_LAI") != "1":
        sys.exit("Chưa có quyền lái (HONG_DUOC_LAI=1).")
    het = _gio_het(het_luc_hhmm)
    os.makedirs(thu_muc, exist_ok=True)
    nhat_ky = open(os.path.join(thu_muc, "phien.txt"), "a", encoding="utf-8")

    def in_ra(s):
        dong = time.strftime("%H:%M:%S ") + s
        print(dong, flush=True)
        nhat_ky.write(dong + "\n")
        nhat_ky.flush()

    bang = []
    try:
        art, panel = ArtisanThat(), Panel()
        ok, ly = art.kiem()
        in_ra("PHIEN %d luot · het %s · Artisan: %s" % (so_luot, het_luc_hhmm, ly))
        if not ok:
            return bang
        if panel.doc(21, 1)[0] != MAN_RANG:
            in_ra("dang nhap -> man %s" % panel.dang_nhap())
        if ngam_phut > 0:
            art.reset_start()
            time.sleep(8)
            ok, ct = art.dang_ghi()
            in_ra("NGAM %.0f ph Nhiet %d%% · Artisan dang ghi: %s" % (ngam_phut, n_ngam, ct))
            if not ok:
                return bang
            ok = ngam(ngam_phut, n_ngam, os.path.join(thu_muc, "ngam.csv"))
            in_ra("NGAM xong (%s) · gian do %s" % (ok, art.tat_luu()))
            if not ok:
                return bang
        for i in range(1, so_luot + 1):
            if time.time() > het - (TRAN_GIAY + 4 * 60):
                in_ra("KHONG DU GIO cho luot %d — thoi" % i)
                break
            t1 = time.time()
            kv = chay_de(panel, art, DongHoThat(), GiaiDe(moc=(dau,), giu=giu_dau, dai_dem=1.5), het_luc=het, tat_cuoi=False,
                         log_csv=os.path.join(thu_muc, "luot%d_ve_dau.csv" % i), in_ra=lambda s: in_ra("[ve dau] " + s))
            t_ve = time.time() - t1
            in_ra("LUOT %d · VE DAU %s sau %.0f s · %s" % (i, "xong" if kv["sach"] else "DUNG", t_ve, kv["dung"]))
            if not kv["sach"]:
                break
            kq = chay_de(panel, art, DongHoThat(), GiaiDe(), het_luc=het,
                         log_csv=os.path.join(thu_muc, "luot%d.csv" % i), in_ra=lambda s: in_ra("[luot %d] %s" % (i, s)))
            ch = cham_alog(kq["alog"]) if kq.get("alog") else {"dat": False, "so_moc_dat": 0, "loi": "không có giản đồ"}
            in_ra(in_cham(ch) if kq.get("alog") else "CHAM: không có giản đồ — lượt không tính")
            k_dv = david.tom_tat(david.phan_tich(kq["alog"])) if kq.get("alog") else "k David: —"
            in_ra(k_dv)
            dong = {"luot": i, "alog": kq.get("alog"), "ve_dau_alog": kv.get("alog"), "ve_dau_giay": round(t_ve),
                    "dung": kq["dung"], "dat": ch.get("dat"), "so_moc_dat": ch.get("so_moc_dat"),
                    "tong_giay": ch.get("tong_giay"), "lo_len": ch.get("lo_len"), "lo_xuong": ch.get("lo_xuong"),
                    "moc": [(k["moc"], k["giay"], k["lo"], k["truot"]) for k in ch.get("moc", [])], "david": k_dv}
            bang.append(dong)
            with open(os.path.join(thu_muc, "tong_ket.jsonl"), "a", encoding="utf-8") as f:
                f.write(json.dumps(dong, ensure_ascii=False) + "\n")
            if kq["dung"] not in ("xong", "HET GIO") or time.time() > het:
                in_ra("DUNG PHIEN: %s" % kq["dung"])
                break
    finally:
        in_ra("KET THUC PHIEN · %s" % " | ".join("L%d %s %s/7 %s lo %.1f/%.1f" % (
            b["luot"], "DAT" if b["dat"] else "-", b["so_moc_dat"],
            "%d:%02d" % divmod(int(b["tong_giay"]), 60) if b["tong_giay"] else "--:--",
            b["lo_len"] or 0, b["lo_xuong"] or 0) for b in bang))
        nhat_ky.close()
        an_toan(gio=100, duong_csv=os.path.join(thu_muc, "lam_mat.csv") if nguoi else None)
    return bang


def an_toan(gio=100, den=60.0, duong_csv=None, toi_da_phut=60):
    """Lệnh AN TOÀN một phát (chủ máy 15/10: "lệnh an toàn làm trước, phân tích sau"): cờ PC control TẮT (board nghe panel)
    → TẮT Lệnh nhiệt + Nhiệt đặt 0 % → gió lên `gio` % · trống GIỮ NGUYÊN để quay làm mát. Đọc lại, in 1 dòng kiểm.
    Có `duong_csv` thì theo dõi mỗi 5 s tới khi BT, ET và buồng đều < `den` °C (không tự tắt gió / trống)."""
    p = Panel()
    p.pc_control(False)
    p.lenh_nhiet(False)
    p.dat_nhiet(0)
    p.dat_gio(gio)
    time.sleep(1.5)
    d = p.doc_tat_ca()
    print("AN TOAN: Lenh %s · Nhiet dat %s · gio dat %s · trong dat %s · PC %s · man %s · ma %s · BT %.1f ET %.1f buong %s"
          % (d["lenh_nhiet"], d["dat_nhiet"], d["dat_gio"], d["dat_trong"], d["pc_control"], d["man"], d["ma"],
             d["bt"], d["et"], d["buong"]), flush=True)
    if d["lenh_nhiet"] or d["dat_nhiet"]:
        sys.exit("CANH BAO: Lệnh nhiệt / Nhiệt đặt chưa về 0 — kiểm panel ngay")
    if not duong_csv:
        return d
    het = time.time() + toi_da_phut * 60
    with open(duong_csv, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        while time.time() < het:
            d = p.doc_tat_ca()
            w.writerow([time.strftime("%H:%M:%S"), d["bt"], d["et"], d["buong"], d["lenh_nhiet"], d["gio"], d["trong"]])
            f.flush()
            nong = [v for v in (d["bt"], d["et"], d["buong"]) if v is not None and v >= den]
            if not nong:
                print("NGUOI: BT %.1f ET %.1f buong %s < %.0f °C" % (d["bt"], d["et"], d["buong"], den), flush=True)
                return d
            time.sleep(5)
    print("HET GIO THEO DOI: BT %.1f ET %.1f buong %s" % (d["bt"], d["et"], d["buong"]), flush=True)
    return d


# ══════════════════════════════════════════════════════════════════════════════════════════════
# BÀI GIÓ (chủ máy 15/10 11:37, sửa 11:51: 65 → 75 %): Nhiệt KHOÁ 75 %, CHỈ lái gió 50–100 %, trống giữ nguyên; BT về 200 và GIỮ.
# Mỗi lượt 5 phút tính từ START Artisan, tối đa 3 lượt. ĐẠT = BT trong 200 ± 1,5 liên tục tới hết 5 phút, ≥ 60 s cuối, không lố > 1,5.
# ══════════════════════════════════════════════════════════════════════════════════════════════
GIO_BAI = (50, 100)
NHIET_BAI, DICH_BAI, DAI_BAI, GIU_CUOI_BAI, LUOT_BAI_GIAY = 75, 200.0, 1.5, 60.0, 300.0  # 11:51 chủ máy sửa đề 65 → 75 %


def cham_gio_bt(t, bt, dich=DICH_BAI, dai=DAI_BAI, giu_cuoi=GIU_CUOI_BAI, dai_bai=LUOT_BAI_GIAY):
    """Chấm bài gió từ (t, BT) của giản đồ, chỉ xét t ≤ 5 phút từ START. Lố theo CHIỀU ĐANG ĐI: từ dưới lên ⇒ lố lên = max(BT) − đích
    cả lượt; lố xuống = max(đích − BT) SAU lần đầu BT CHẠM đích. ĐẠT cần cả hai ≤ dai (luật chặt)."""
    t = np.asarray(t, float) - t[0]
    bt = np.asarray(bt, float)
    m = t <= dai_bai + 0.5
    t, bt = t[m], bt[m]
    trong = np.abs(bt - dich) <= dai + 1e-9
    vao = np.flatnonzero(trong)
    t_vao_dau = float(t[vao[0]]) if len(vao) else None
    t_vao_cuoi = None
    if trong[-1]:
        j = len(trong) - 1
        while j > 0 and trong[j - 1]:
            j -= 1
        t_vao_cuoi = float(t[j])
    hg = 1.0 if bt[0] < dich else -1.0
    lo_di = float(max(0.0, (hg * (bt - dich)).max()))
    cham = np.flatnonzero(hg * (bt - dich) >= 0)                  # lần đầu CHẠM đích (theo chiều đang đi)
    lo_nguoc = float(max(0.0, (-hg * (bt[cham[0]:] - dich)).max())) if len(cham) else 0.0
    giu = float(t[-1] - t_vao_cuoi) if t_vao_cuoi is not None else 0.0
    cuoi = t >= t[-1] - 60
    du_gio = t[-1] >= dai_bai - 2
    dat = bool(du_gio and giu >= giu_cuoi - 1e-9 and lo_di <= dai + 1e-9 and lo_nguoc <= dai + 1e-9)
    return {"dat": dat, "dai_giay": round(float(t[-1]), 1), "bt_dau": round(float(bt[0]), 1),
            "t_vao_dau": t_vao_dau, "t_vao_cuoi": t_vao_cuoi, "giu_cuoi": round(giu, 1),
            "lo_len": round(lo_di if hg > 0 else lo_nguoc, 2), "lo_xuong": round(lo_nguoc if hg > 0 else lo_di, 2),
            "sai_tb_60": round(float(np.abs(bt[cuoi] - dich).mean()), 2), "bt_cuoi": round(float(bt[-1]), 1),
            "bt_max": round(float(bt.max()), 1), "bt_min_sau_vao": round(float(bt[vao[0]:].min()), 1) if len(vao) else None}


def cham_gio_alog(duong, dich=DICH_BAI):
    ts, bts, _, d = doc_alog(duong)
    if len(ts) < 2:
        return {"dat": False, "loi": "giản đồ không có số liệu (%d mẫu)" % len(ts), "file": duong}
    kq = cham_gio_bt(ts, bts, dich=dich)
    kq.update(file=duong, so_mau=len(ts), bat_dau=d.get("roastisodate", "") + " " + d.get("roasttime", ""))
    return kq


def in_cham_gio(kq):
    if kq.get("loi"):
        return "CHAM %s: %s" % (os.path.basename(kq.get("file", "")), kq["loi"])
    f = lambda v: "%.0f s" % v if v is not None else "—"  # noqa: E731
    return ("CHAM %s · %s · %s · %d mau %.0f s · BT dau %.1f · vao ±1,5 lan dau %s · doan cuoi tu %s (giu %.0f s) · "
            "lo len %.2f / xuong %.2f · sai TB 60 s cuoi %.2f · BT cuoi %.1f max %.1f") % (
        os.path.basename(kq["file"]), kq.get("bat_dau", ""), "DAT" if kq["dat"] else "CHUA DAT", kq["so_mau"], kq["dai_giay"],
        kq["bt_dau"], f(kq["t_vao_dau"]), f(kq["t_vao_cuoi"]), kq["giu_cuoi"], kq["lo_len"], kq["lo_xuong"], kq["sai_tb_60"],
        kq["bt_cuoi"], kq["bt_max"])


MOC_THANG = (195.0, 200.0, 205.0)   # chủ máy 15/10 ~13:55: 195 → 200 → 205, mỗi mốc ± 1,5 liên tục ≥ 30 s, cả 3 trong 5 phút


def cham_bac_thang(duong, moc=MOC_THANG, dai=1.5, giu=30.0, han=LUOT_BAI_GIAY):
    """Chấm đề bậc thang từ .alog: cham_bt (mốc sau bắt đầu khi mốc trước xong) + mọi khoảng vào/ra dải của từng mốc."""
    ts, bts, _, _ = doc_alog(duong)
    t = np.asarray(ts, float) - ts[0]
    bt = np.asarray(bts, float)
    m = t <= han + 0.5
    t, bt = t[m], bt[m]
    r = cham_bt(t, bt, moc=moc, lo_max=1e9, dai=dai, giu=giu, han=han)
    khoang = {}
    for mc in moc:
        trong, ds, j = np.abs(bt - mc) <= dai + 1e-9, [], None
        for k in range(len(t)):
            if trong[k] and j is None:
                j = k
            if j is not None and (not trong[k] or k == len(t) - 1):
                e = k if trong[k] else k - 1
                ds.append((round(float(t[j]), 1), round(float(t[e]), 1), round(float(t[e] - t[j]), 1)))
                j = None
        khoang[mc] = ds
    dong = "BAC THANG %s · %d/3 · %s" % (os.path.basename(duong), r["so_moc_dat"], " · ".join(
        "%g: %s" % (mc, ", ".join("%.0f-%.0f s (%.0f s)" % x for x in khoang[mc]) or "khong vao") for mc in moc))
    return {"dat": r["dat"], "so_moc_dat": r["so_moc_dat"], "khoang": {str(k): v for k, v in khoang.items()},
            "bt_dau": round(float(bt[0]), 1), "bt_cuoi": round(float(bt[-1]), 1), "bt_max": round(float(bt.max()), 1),
            "dong": dong}


class GiuBTGio:
    """Nhiệt KHOÁ; chỉ lái gió trong GIO_BAI. Mô hình RoR (đo trong ngấm 15/10: gió 100 → 50 ở BT 166 làm RoR tụt ~5 °C/ph, trễ
    ~10 s; thân lồng còn ngấm ⇒ BT trôi lên kể cả ở gió 50): RoR = r50 + kg·(g_eff − 50), g_eff = gió thật qua trễ bậc 1 `tg` s,
    r50 = độ trôi ở gió 50 (bộ quan sát sống ⇒ tác dụng tích phân). Mỗi `chu_ky` s: BT dự báo trước `tre` s, RoR mong muốn
    = (đích(t) − BT dự báo)/tc ⇒ gió = 50 + (RoR mong muốn − r50)/kg, kẹp [50, 100], bước ≤ buoc.
    Gió 50 vẫn trôi lên (r50 > 0, không giữ đứng được) ⇒ bám đường dốc r50 kết thúc ở 200 + kep lúc 300 s (`dich_t`) — qua dải
    ±1,5 trong ≥ 60 s cuối chỉ được khi r50 ≲ 2,6 °C/ph (giới hạn vật lý: gió không hãm thêm dưới 50 %)."""

    def __init__(self, dich, kg, tg, tre, tc, buoc=10, a_b=0.05, g0=50, chu_ky=2, kep=1.1, t_cat=None, bt_cat=None):
        self.dich, self.kg, self.tg, self.tre, self.tc = dich, kg, tg, tre, tc
        # 15/10 13:38 chiến lược CẮT GIÓ: gió cao đẩy BT tới bt_cat lúc t_cat rồi HẠ 50 — sau khi hạ gió ET đứng ~30 s
        # (do75.csv 11:56) ⇒ BT đi chậm ~1,5 °C/ph đúng lúc vào dải ⇒ ăn thêm thời gian trong ± 1,5 (độ trôi gió 50 quanh 200 ~3–4).
        self.t_cat, self.bt_cat, self.da_cat, self.sau_cat_50 = t_cat, bt_cat, None, False
        self.buoc, self.a_b, self.g, self.chu_ky, self.kep = buoc, a_b, int(g0), chu_ky, kep
        self.g_eff, self.t_cu, self.r50, self.t_chinh, self.ke = float(g0), None, None, -1e9, ""

    def quan_sat(self, t, bt, ror, g_that):
        dt = 1.0 if self.t_cu is None else max(0.2, t - self.t_cu)
        self.t_cu = t
        self.g_eff += (g_that - self.g_eff) * min(1.0, dt / self.tg)
        r_hat = ror - self.kg * (self.g_eff - 50.0)
        self.r50 = r_hat if self.r50 is None else self.r50 + self.a_b * (r_hat - self.r50)

    def dich_t(self, t):
        """(đích, độ dốc °C/ph) lúc t. r50 ≤ 0,3 ⇒ giữ đứng 200. r50 > 0,3 (gió 50 vẫn trôi lên, không giữ đứng được) ⇒ đường
        dốc r50 kết thúc ở 200 + kep lúc hết lượt: BT đi qua dải với tốc độ tự nhiên, gió chỉ để TĂNG TỐC khi tụt sau đường."""
        r = self.r50 if self.r50 is not None else 0.0
        if r <= 0.3:
            return self.dich, 0.0
        t_giua = LUOT_BAI_GIAY - self.kep / r * 60.0
        v = self.dich + r * (t - t_giua) / 60.0
        return (self.dich + self.kep, 0.0) if v >= self.dich + self.kep else (v, r)

    def _cat_gio(self, t, bt_p):
        """Chế độ cắt gió. Trả gió, hoặc None nếu đã qua pha trước-cắt và hết 40 s giữ 50 (về luật đường dốc cũ)."""
        if self.t_cat < 0:                                  # t_cat < 0 ⇒ gió cố định 50 cả lượt (bậc thang lên thuận chiều trôi)
            self.ke = "gio co dinh 50 BTp %.1f" % bt_p
            return GIO_BAI[0]
        if self.da_cat is None:
            if t >= self.t_cat or bt_p >= self.bt_cat:
                self.da_cat = t
                self.ke = "CAT GIO luc %.0f s BTp %.1f" % (t, bt_p)
                return GIO_BAI[0]
            ror_d = (self.bt_cat - bt_p) / max(10.0, self.t_cat - t - self.tre) * 60.0
            g = 50.0 + (ror_d - self.r50) / self.kg
            g = max(self.g - self.buoc, min(self.g + self.buoc, g))
            self.ke = "truoc cat: RoRd %+.1f r50 %+.2f BTp %.1f" % (ror_d, self.r50, bt_p)
            return int(round(max(GIO_BAI[0], min(GIO_BAI[1], g))))
        if self.sau_cat_50 or t - self.da_cat < 40 or bt_p >= self.dich - 1.1:
            self.ke = "sau cat: giu 50 BTp %.1f" % bt_p
            return GIO_BAI[0]
        g = 50.0 + 15.0 * (self.dich - 1.1 - bt_p)              # tụt sau dải ⇒ đẩy gió vừa đủ
        self.ke = "sau cat: day BTp %.1f" % bt_p
        return int(round(max(GIO_BAI[0], min(GIO_BAI[1], g))))

    def quyet_dinh(self, t, bt, ror):
        if t - self.t_chinh < self.chu_ky or self.r50 is None:
            return self.g
        self.t_chinh = t
        bt_p = bt + ror / 60.0 * self.tre
        if self.t_cat is not None:
            self.g = self._cat_gio(t, bt_p)
            return self.g
        dt_, r_ref = self.dich_t(t + self.tre)
        ror_d = r_ref + (dt_ - bt_p) / self.tc * 60.0
        g = 50.0 + (ror_d - self.r50) / self.kg
        g = max(self.g - self.buoc, min(self.g + self.buoc, g))
        self.g = int(round(max(GIO_BAI[0], min(GIO_BAI[1], g))))
        self.ke = "dich %.1f BTp %.1f RoRd %+.1f r50 %+.2f geff %.0f" % (dt_, bt_p, ror_d, self.r50, self.g_eff)
        return self.g


def phan_tich_gio(duong_csv, cua=20):
    """Độ nhạy gió → BT từ csv của `ngam` (gio, bt, et, buong, nhiet, gio_pct, …): RoR hồi quy `cua` s TRƯỚC mỗi bước gió và
    sau bước (bỏ 10 s trễ đầu). Trả list (giờ, gió trước → sau, BT, RoR trước, RoR sau, ΔRoR / 10 % gió)."""
    rows = [r for r in csv.reader(open(duong_csv, encoding="utf-8")) if r and r[0][:1].isdigit()]
    t = np.array([sum(int(x) * k for x, k in zip(r[0].split(":"), (3600, 60, 1))) for r in rows], float)
    bt = np.array([float(r[1]) for r in rows])
    g = np.array([float(r[5]) for r in rows])
    kq = []
    for i in range(1, len(g)):
        if g[i] == g[i - 1]:
            continue
        tr = (t >= t[i] - cua) & (t < t[i])
        j = np.flatnonzero(g[i:] != g[i])
        het = t[i + j[0]] if len(j) else t[-1]
        sa = (t >= t[i] + 10) & (t <= min(t[i] + 10 + cua, het))
        if tr.sum() < 5 or sa.sum() < 5:
            continue
        r0 = np.polyfit(t[tr], bt[tr], 1)[0] * 60
        r1 = np.polyfit(t[sa], bt[sa], 1)[0] * 60
        kq.append((rows[i][0], g[i - 1], g[i], bt[i], r0, r1, (r1 - r0) / (g[i] - g[i - 1]) * 10))
    return kq


def do_gio(duong_csv, nhiet, buoc, trong=None):
    """ĐO chiều + độ nhạy gió → BT ở Nhiệt cố định (chuẩn bị, không chấm). Giản đồ riêng: Artisan OFF bản đang ghi → ON → START,
    kiểm ĐANG GHI → chuỗi bước gió `buoc` [(gió %, giây)] bằng `ngam` (lớp an toàn BT > 245 / ET > 255 / mất số / mã / cờ PC)
    → TẮT Lệnh + gió 100 → OFF lưu giản đồ → in ΔRoR mỗi bước."""
    art, p = ArtisanThat(), Panel()
    print("ARTISAN ON:", art.bat_on(), flush=True)
    ok, ly = art.kiem()
    print("ARTISAN KIEM:", ly, flush=True)
    if not ok:
        sys.exit(2)
    print("ARTISAN OFF (ban dang ghi):", art.tat_luu(), flush=True)
    if trong is None:                                   # đề: trống GIỮ NGUYÊN mức anh đang đặt (15/10 13:26 anh đổi 85 → 100)
        trong = p.doc_tat_ca()["dat_trong"]
    art.reset_start()
    time.sleep(3)
    for _ in range(3):                                  # vừa START có thể chưa đủ điểm vẽ ⇒ thử lại tối đa 3 lần
        ok, ct = art.dang_ghi()
        print("ARTISAN DANG GHI:", ct, flush=True)
        if ok:
            break
        time.sleep(3)
    if not ok:
        p.lenh_nhiet(False)
        sys.exit("Artisan không ghi — không lái mù; đã TẮT Lệnh nhiệt")
    ok = True
    try:
        for gio, giay in buoc:
            ok = ngam(giay / 60.0, nhiet, duong_csv, gio=gio, trong=trong)
            if not ok:
                break
    finally:
        p.lenh_nhiet(False)
        p.dat_gio(100)
        time.sleep(1.5)
        d = p.doc_tat_ca()
        print("DO GIO XONG (%s) · Lenh %s · gio dat %s · BT %.1f ET %.1f buong %s" % (
            ok, d["lenh_nhiet"], d["dat_gio"], d["bt"], d["et"], d["buong"]), flush=True)
        print("ARTISAN OFF:", art.tat_luu(), flush=True)
    for gio_, g0, g1, b, r0, r1, k in phan_tich_gio(duong_csv):
        print("BUOC %s gio %.0f -> %.0f · BT %.1f · RoR %+.1f -> %+.1f °C/ph · %+.2f °C/ph moi +10 %% gio" % (
            gio_, g0, g1, b, r0, r1, k), flush=True)
    return ok


def _doc_an_toan(p, t_ok, in_ra):
    try:
        return p.doc_tat_ca(), time.time()
    except (OSError, ValueError) as e:
        if time.time() - t_ok > MAT_SO_GIAY:
            raise RuntimeError("MAT SO PANEL > %.0f s (%s)" % (MAT_SO_GIAY, e))
        return None, t_ok


def chuan_bi_gio(p, dau, g0, csv_w, in_ra, het, lead=12.0, ha=12.0, phut_max=8.0, buong_min=0.0):
    """CHUẨN BỊ (không chấm, giản đồ riêng): NGUỘI (Lệnh TẮT, gió 100) tới BT ≤ dau − ha → NUNG (Nhiệt NHIET_BAI, Lệnh bật, gió g0)
    tới BT + RoR·lead ≥ dau (lead = thời gian OFF → ON → START của Artisan). Điểm xuất phát mỗi lượt giống nhau: BT ≈ dau ĐANG
    LÊN, Nhiệt NHIET_BAI (VX4 đã giữ buồng ≥ 60 s), gió g0, trống giữ nguyên. Trả RoR lúc kích START, None nếu phải dừng."""
    t0 = t_ok = time.time()
    pha, ls = None, []
    while True:
        d, t_ok = _doc_an_toan(p, t_ok, in_ra)
        now = time.time()
        if d is None:
            time.sleep(1)
            continue
        loi = tu_kiem(d, None)
        if d["bt"] > BT_TUYET_DOI or d["et"] > ET_MAX or loi or now > het or now - t0 > phut_max * 60:
            in_ra("CHUAN BI DUNG: BT %.1f ET %.1f %s" % (d["bt"], d["et"], "; ".join(loi) or "het gio / qua lau"))
            return None
        ls.append((now, d["bt"]))
        ls = ls[-30:]
        ror = doc_hoi_quy(ls, 20)
        moi = "nguoi" if (pha in (None, "nguoi") and d["bt"] > dau - ha) else "nung"
        if moi != pha:
            pha = moi
            if pha == "nguoi":
                p.lenh_nhiet(False)
                p.dat_gio(100)
            else:
                p.dat_nhiet(NHIET_BAI)
                p.dat_gio(g0)
                p.lenh_nhiet(True)
            time.sleep(1.0)
            d = p.doc_tat_ca()
            in_ra("CHUAN BI %s · BT %.1f · Lenh %d Nhiet dat %d gio dat %d trong dat %d" % (
                pha.upper(), d["bt"], d["lenh_nhiet"], d["dat_nhiet"], d["dat_gio"], d["dat_trong"]))
        csv_w.writerow([time.strftime("%H:%M:%S"), round(now - t0, 1), "chuan_bi_" + pha, d["bt"], d["et"], d["buong"],
                        d["dat_nhiet"], d["lenh_nhiet"], d["dat_gio"], d["gio"], d["trong"], d["ma"], round(ror, 2), "", ""])
        buong_ok = d["buong"] is not None and d["buong"] >= buong_min
        if pha == "nung" and not buong_ok and d["bt"] > dau + 2.0:
            # 15/10 M23: BT tới đích trước khi buồng chạm SV ⇒ START sẽ dính cú vọt nung lại — dừng, không đốt lượt
            in_ra("CHUAN BI DUNG: BT %.1f > dau + 2 ma buong %.1f < %.0f (chua cham SV)" % (d["bt"], d["buong"], buong_min))
            return None
        if pha == "nung" and now - t0 > 5 and buong_ok and d["bt"] + ror / 60.0 * lead >= dau:
            in_ra("CHUAN BI XONG · BT %.1f RoR %+.1f °C/ph · kich START" % (d["bt"], ror))
            return ror
        time.sleep(max(0.0, 1.0 - (time.time() - now)))


def giu_bt_gio(luot, het_luc_hhmm, thu_muc, dau=175.0, g0=50, kg=0.08, tg=12.0, tre=10.0, tc=45.0, buoc=10, a_b=0.05,
               kep=1.1, nguoi=False, t_cat=None, bt_cat=None, ha=12.0, buong_min=0.0, phut_cb=8.0, sau_cat_50=False):
    """MỘT lượt bài gió trên MÁY THẬT: Artisan kiểm → giản đồ CHUẨN BỊ → giản đồ LƯỢT (đúng 5 phút từ START, Nhiệt khoá NHIET_BAI,
    chỉ gió 50–100 %) → TẮT nhiệt + an_toan → chấm .alog + k David → tong_ket.jsonl. Tham số mô hình qua dòng lệnh (ghi vào log)."""
    import json
    if os.environ.get("HONG_DUOC_LAI") != "1":
        sys.exit("Chưa có quyền lái (HONG_DUOC_LAI=1).")
    het = _gio_het(het_luc_hhmm)
    os.makedirs(thu_muc, exist_ok=True)
    nk = open(os.path.join(thu_muc, "bai_gio.txt"), "a", encoding="utf-8")

    def in_ra(s):
        dong = time.strftime("%H:%M:%S ") + "[L%d] " % luot + s
        print(dong, flush=True)
        nk.write(dong + "\n")
        nk.flush()

    ts_ = dict(nhiet=NHIET_BAI, dau=dau, g0=g0, kg=kg, tg=tg, tre=tre, tc=tc, buoc=buoc, a_b=a_b, kep=kep, t_cat=t_cat,
               bt_cat=bt_cat, ha=ha, buong_min=buong_min, phut_cb=phut_cb, sau_cat_50=sau_cat_50)
    in_ra("THAM SO %s" % ts_)
    art, p = ArtisanThat(), Panel()
    ly_do, alog_cb, alog, ror0, gio_dung, pha = "xong", None, None, None, [], "kiem"
    fcsv = open(os.path.join(thu_muc, "luot%d.csv" % luot), "a", newline="", encoding="utf-8")
    w = csv.writer(fcsv)
    w.writerow(["gio", "t", "pha", "bt", "et", "buong", "nhiet_dat", "lenh", "gio_dat", "gio_that", "trong", "ma", "ror",
                "ke_hoach", "k_david"])
    try:
        in_ra("ARTISAN ON: %s" % art.bat_on())
        ok, ly = art.kiem()
        in_ra("ARTISAN KIEM: %s" % ly)
        if not ok:
            raise RuntimeError("artisan")
        if p.doc(21, 1)[0] != MAN_RANG:
            in_ra("dang nhap -> man %s" % p.dang_nhap())
        trong0 = p.doc_tat_ca()["dat_trong"]
        # ── giản đồ CHUẨN BỊ ──
        art.reset_start()
        pha = "chuan_bi"
        time.sleep(3)
        for _ in range(3):
            ok, ct = art.dang_ghi()
            in_ra("ARTISAN (chuan bi) DANG GHI: %s" % ct)
            if ok:
                break
            time.sleep(3)
        if not ok:
            raise RuntimeError("artisan_khong_ghi_chuan_bi")
        ror0 = chuan_bi_gio(p, dau, g0, w, in_ra, het, ha=ha, phut_max=phut_cb, buong_min=buong_min)
        if ror0 is None:
            raise RuntimeError("chuan_bi_dung")
        alog_cb, pha = art.tat_luu(), "giua"
        # ── giản đồ LƯỢT: OFF → ON → START một lần ──
        art.reset_start()
        t0, pha = time.time(), "luot"
        d = p.doc_tat_ca()
        in_ra("START · BT %.1f ET %.1f buong %s · Nhiet dat %d Lenh %d · gio dat %d · trong dat %d · (chuan bi %s)" % (
            d["bt"], d["et"], d["buong"], d["dat_nhiet"], d["lenh_nhiet"], d["dat_gio"], d["dat_trong"], alog_cb))
        ok, ct = art.dang_ghi()
        if not ok:
            art.bam_start()
            time.sleep(2)
            ok, ct = art.dang_ghi()
        in_ra("ARTISAN (luot) DANG GHI: %s" % ct)
        if not ok:
            raise RuntimeError("artisan_khong_ghi")
        bo = GiuBTGio(DICH_BAI, kg, tg, tre, tc, buoc=buoc, a_b=a_b, g0=g0, kep=kep, t_cat=t_cat, bt_cat=bt_cat)
        bo.sau_cat_50 = sau_cat_50          # bậc thang 195/200/205: sau khi cắt gió GIỮ 50 tới hết (trôi tự nhiên qua 200, 205)
        ls, t_ok, g_cu = [], time.time(), g0
        while True:
            now = time.time()
            t = now - t0
            if t >= LUOT_BAI_GIAY + 1.0:
                break
            d, t_ok = _doc_an_toan(p, t_ok, in_ra)
            if d is None:
                time.sleep(1)
                continue
            if d["et"] > ET_MAX or d["bt"] > min(DICH_BAI + BT_TREN_MOC, BT_TUYET_DOI):
                ly_do = "AN TOAN BT %.1f ET %.1f" % (d["bt"], d["et"])
                break
            loi = tu_kiem(d, None, cho_nhiet=NHIET_BAI, cho_lenh=1)
            if d["dat_trong"] != trong0:
                loi.append("trống đặt %s ≠ %s" % (d["dat_trong"], trong0))
            if loi:
                ly_do = "TU KIEM: " + "; ".join(loi)
                break
            if now > het:
                ly_do = "HET GIO LAI"
                break
            ls.append((t, d["bt"]))
            ls = ls[-40:]
            ror = doc_hoi_quy(ls, 20)
            k_dv = david.k_song(doc_hoi_quy(ls, 30), d["et"], d["bt"])
            bo.quan_sat(t, d["bt"], ror, d["gio"])
            g = bo.quyet_dinh(t, d["bt"], ror)
            if g != g_cu or d["dat_gio"] != g:
                p.dat_gio(g)
                if g != g_cu:
                    in_ra("%5.0f BT %.1f RoR %+.1f · gio %d -> %d · %s" % (t, d["bt"], ror, g_cu, g, bo.ke))
                g_cu = g
            gio_dung.append(g)
            w.writerow([time.strftime("%H:%M:%S"), round(t, 1), "luot", d["bt"], d["et"], d["buong"], d["dat_nhiet"],
                        d["lenh_nhiet"], g, d["gio"], d["trong"], d["ma"], round(ror, 2), bo.ke,
                        round(k_dv, 4) if k_dv is not None else ""])
            fcsv.flush()
            if not art.con_nhan_so(d["bt"]):
                ly_do = "Artisan mất số > 10 s"
                break
            if int(t) % 30 == 15 and not art.con_ghi():
                ly_do = "Artisan NGỪNG GHI (đồng hồ đứng)"
                break
            time.sleep(max(0.0, 1.0 - (time.time() - now)))
    except RuntimeError as e:
        ly_do = str(e)
    finally:
        p.lenh_nhiet(False)
        in_ra("KET THUC LUOT: %s · TAT Lenh nhiet" % ly_do)
        fcsv.close()
        try:
            if pha == "luot":
                alog = art.tat_luu()
            elif pha == "chuan_bi":
                alog_cb = art.tat_luu()
        finally:
            an_toan(gio=100, duong_csv=os.path.join(thu_muc, "lam_mat.csv") if nguoi else None)
    in_ra("ARTISAN OFF · gian do: %s" % alog)
    dong = {"luot": luot, "tham_so": ts_, "dung": ly_do, "alog": alog, "chuan_bi_alog": alog_cb, "ror_kich_start": ror0,
            "gio_min": min(gio_dung) if gio_dung else None, "gio_max": max(gio_dung) if gio_dung else None}
    if alog:
        ch = cham_gio_alog(alog)
        in_ra(in_cham_gio(ch))
        k_dv = david.tom_tat(david.phan_tich(alog))
        in_ra(k_dv)
        bt3 = cham_bac_thang(alog)
        in_ra(bt3["dong"])
        dong.update(cham=ch, david=k_dv, bac_thang=bt3)
    with open(os.path.join(thu_muc, "tong_ket.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(dong, ensure_ascii=False) + "\n")
    nk.close()
    return dong


def _tach_opt(argv):
    pos, opt, i = [], {}, 0
    while i < len(argv):
        if argv[i].startswith("--"):
            opt[argv[i][2:]] = argv[i + 1]
            i += 2
        else:
            pos.append(argv[i])
            i += 1
    return pos, opt


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    lenh, (pos, opt) = sys.argv[1], _tach_opt(sys.argv[2:])
    if lenh == "doc":
        print(Panel().doc_tat_ca())
    elif lenh == "theo_doi":
        theo_doi(float(pos[0]), pos[1])
    elif lenh == "cham":
        for f in pos:
            print(in_cham(cham_alog(f, lo_max=float(opt.get("lo", LO_MAX)))))
            print(david.in_kq(david.phan_tich(f)))
    elif lenh == "thu":
        seed = int(pos[0]) if pos else 0
        tm = pos[1] if len(pos) > 1 else None
        kq = mot_luot(seed, float(opt.get("lo", LO_MAX)), tm, in_ra=print, lech=opt.get("lech", "1") == "1")
        print(in_cham(kq))
    elif lenh == "mc":
        tom, hong, _ = monte_carlo(int(pos[0]) if pos else 200, float(opt.get("lo", LO_MAX)),
                                   int(opt["luong"]) if "luong" in opt else None, int(opt.get("seed", 1000)))
        print(tom)
        for h in hong:
            print("  hỏng seed %d: %d/7 mốc · tổng %s · lố lên %.2f xuống %.2f · %s" % h)
    elif lenh == "ngam":
        if os.environ.get("HONG_DUOC_LAI") != "1":
            sys.exit("Chưa có quyền lái (HONG_DUOC_LAI=1).")
        ngam(float(pos[0]), float(pos[1]), pos[2])
    elif lenh == "ve_dau_ghi":
        # ⛔ luật 15/10: bộ lái đổi nhiệt thì Artisan phải ĐANG GHI — bước về điều kiện đầu cũng có giản đồ riêng
        if os.environ.get("HONG_DUOC_LAI") != "1":
            sys.exit("Chưa có quyền lái (HONG_DUOC_LAI=1).")
        a = ArtisanThat()
        ok, ly = a.kiem()
        print("ARTISAN KIEM:", ly, flush=True)
        if not ok:
            sys.exit(2)
        a.reset_start()
        time.sleep(8)
        ok, ct = a.dang_ghi()
        print("ARTISAN DANG GHI:", ct, flush=True)
        if not ok:
            Panel().lenh_nhiet(False)
            sys.exit("Artisan không ghi — không lái mù; đã TẮT Lệnh nhiệt")
        kq = ve_dau(float(pos[0]), pos[1], nhiet0=float(opt["n0"]) if "n0" in opt else None,
                    giu_muc=float(opt["giu"]) if "giu" in opt else None)
        print("ARTISAN OFF:", a.tat_luu(), flush=True)
        sys.exit(0 if kq is not None else 2)
    elif lenh == "ve_dau":
        if os.environ.get("HONG_DUOC_LAI") != "1":
            sys.exit("Chưa có quyền lái (HONG_DUOC_LAI=1).")
        sys.exit(0 if ve_dau(float(pos[0]), pos[1], nhiet0=float(opt["n0"]) if "n0" in opt else None) is not None else 2)
    elif lenh == "phien":
        phien(int(pos[0]), pos[1], pos[2], ngam_phut=float(opt.get("ngam", 0)), n_ngam=int(opt.get("n_ngam", 55)),
              dau=float(opt.get("dau", 200)), giu_dau=int(opt.get("giu_dau", 30)), nguoi=opt.get("nguoi", "1") == "1")
    elif lenh == "an_toan":
        # luôn được chạy, không cần HONG_DUOC_LAI: chỉ TẮT nhiệt + làm mát
        an_toan(gio=float(opt.get("gio", 100)), den=float(opt.get("den", 60)), duong_csv=opt.get("csv"))
    elif lenh == "kiem_artisan":
        print(ArtisanThat().kiem())
    elif lenh == "giai_de":
        giai_de_that(pos[0], pos[1])
    elif lenh == "giu_bt_gio":
        # bài gió 15/10: giu_bt_gio <lượt> <hết HH:MM> <thư mục> [--dau 175 --g0 50 --kg 0.08 --tg 12 --tre 10 --tc 45
        #   --buoc 10 --a_b 0.05 --kep 1.1 --nguoi 0]
        giu_bt_gio(int(pos[0]), pos[1], pos[2], dau=float(opt.get("dau", 175)), g0=int(opt.get("g0", 50)),
                   kg=float(opt.get("kg", 0.08)), tg=float(opt.get("tg", 12)), tre=float(opt.get("tre", 10)),
                   tc=float(opt.get("tc", 45)), buoc=int(opt.get("buoc", 10)), a_b=float(opt.get("a_b", 0.05)),
                   kep=float(opt.get("kep", 1.1)), nguoi=opt.get("nguoi", "0") == "1",
                   t_cat=float(opt["t_cat"]) if "t_cat" in opt else None,
                   bt_cat=float(opt["bt_cat"]) if "bt_cat" in opt else None, ha=float(opt.get("ha", 12)),
                   buong_min=float(opt.get("buong_min", 0)), phut_cb=float(opt.get("phut_cb", 8)),
                   sau_cat_50=opt.get("sau_cat_50", "0") == "1")
    elif lenh == "do_gio":
        # do_gio <csv> [--nhiet 75 --buoc 100:90,50:90,100:60] — đo chiều + độ nhạy gió → BT (giản đồ riêng)
        if os.environ.get("HONG_DUOC_LAI") != "1":
            sys.exit("Chưa có quyền lái (HONG_DUOC_LAI=1).")
        bb = [tuple(int(v) for v in x.split(":")) for x in opt.get("buoc", "100:90,50:90,100:60").split(",")]
        if any(not (GIO_BAI[0] <= g <= GIO_BAI[1]) or s > 300 for g, s in bb):
            sys.exit("bước gió phải trong 50–100 %, mỗi bước ≤ 300 s")
        do_gio(pos[0], float(opt.get("nhiet", NHIET_BAI)), bb)
    elif lenh == "phan_tich_gio":
        for r in phan_tich_gio(pos[0]):
            print("BUOC %s gio %.0f -> %.0f · BT %.1f · RoR %+.1f -> %+.1f · %+.2f °C/ph moi +10 %% gio" % r)
    elif lenh == "cham_thang":
        for f in pos:
            print(cham_bac_thang(f)["dong"])
    elif lenh == "cham_gio":
        for f in pos:
            print(in_cham_gio(cham_gio_alog(f, dich=float(opt.get("dich", DICH_BAI)))))
            print(david.in_kq(david.phan_tich(f)))
    else:
        print(__doc__)
