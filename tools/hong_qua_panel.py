# -*- coding: utf-8 -*-
"""OTL Hồng đọc + lái máy rang QUA PANEL HMI (Modbus TCP) — song song với Artisan (14/10/2026).

Luật chủ máy: Artisan kết nối máy rang TRƯỚC (giữ cổng COM của board); agent kết nối SAU bằng đường RIÊNG, không qua Artisan,
đọc TOÀN BỘ dữ liệu, phân tích mỗi 3 giây. Đường riêng = panel Delta (bản HMI có bảng Modbus TCP mở — bản bàn thử ..-LO99-DIEN):
panel giữ bản sao mọi số board gửi lên (W400nn ≡ $(nn−1)) và board đọc ô điều khiển của panel như người bấm.

Bản đồ (firmware include/Define.h):
  đọc  $1 Lệnh nhiệt (W40002) · $13 cờ PC control (W40014) · $40 mã trạng thái (W40041) · $60 BT ×10 · $61 ET ×10
       $64 gió % ×10 · $65 trống % ×10 · $66 Nhiệt % thật ×10 (board ghi airflowPercent*10 …) · $96 nhiệt BUỒNG VX4 ×10 (W40097)
  ghi  $M34 trống đặt · $M35 gió đặt · $M36 Nhiệt đặt (TCP 2000 + n) · $1 bật/tắt Lệnh nhiệt
⛔ Board nghe HMI chỉ khi cờ PC control TẮT ($13 = 0) — đang bật thì nó nghe PC (Artisan / PC_Link).

    python hong_qua_panel.py doc                 # đọc 1 lần, in đủ
    python hong_qua_panel.py theo_doi <phút> <csv> # đọc mỗi 1 s, PHÂN TÍCH mỗi 3 s
"""
import csv
import os
import socket
import struct
import sys
import time

IP = os.environ.get("OTL_PANEL_IP", "169.254.116.153")
GIO_MIN_PCT = 34                      # gió tối thiểu máy điện = 50 Hz (chủ máy 14/10)


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
        return {"lenh_nhiet": r[1], "pc_control": r[13], "ma": r[40], "bt": s16(r[60]) / 10, "et": s16(r[61]) / 10,
                "gio": r[64] / 10, "trong": r[65] / 10, "nhiet": r[66] / 10, "buong": s16(r[96]) / 10 if len(r) > 96 else None,
                "dat_trong": m[0], "dat_gio": m[1], "dat_nhiet": m[2]}

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
        if self.doc(21, 1)[0] == 15:
            self.ghi(955, [int(pin or os.environ.get("OTL_PANEL_PIN", "2026"))])
            time.sleep(2.5)
        self.ghi(49, [2])
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
            sv = 130 + 2.2 * d["nhiet"] if d["lenh_nhiet"] else 0
            print("%s BT %.1f (RoR %+.1f) · ET %.1f (%+.1f) · BUONG %s (%+.1f) · SV %d · buong-ET %s · ET-BT %.1f · "
                  "BT+30s %.1f · nhiet %d%% gio %d%% trong %d%% · lenh %d pc %d ma %d"
                  % (time.strftime("%H:%M:%S"), d["bt"], r_bt, d["et"], r_et, d["buong"], r_bu, sv,
                     ("%.1f" % (d["buong"] - d["et"])) if d["buong"] is not None else "?", d["et"] - d["bt"],
                     d["bt"] + r_bt / 2, d["nhiet"], d["gio"], d["trong"], d["lenh_nhiet"], d["pc_control"], d["ma"]),
                  flush=True)
        time.sleep(max(0.0, 1.0 - (time.time() - now)))
    f.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if sys.argv[1] == "doc":
        print(Panel().doc_tat_ca())
    else:
        theo_doi(float(sys.argv[2]), sys.argv[3])
