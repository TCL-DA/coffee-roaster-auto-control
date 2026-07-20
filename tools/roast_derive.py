"""
roast_derive.py — tự tính RoR / thời gian rang / mốc rang từ BT-ET thô.

DÙNG KHI NÀO:
  • Máy chưa nạp PC_Link (chỉ có khối tương thích reg 0–19) — mọi máy đã bán.
  • App tự lái mẻ: app là bên quyết định bước, không đọc progStep của firmware.

NGUYÊN TẮC: bám ĐÚNG công thức firmware để số trên app khớp số trên HMI.
  RoR   — Program.h:110   mỗi 3 giây: (BT − BT₋₃ₛ) × 20 → lọc Kalman → kẹp ±95
  TP    — Program.h:1608  sau 20 s và BT < 150: BT chạm đáy rồi tăng lại
  DE    — Program.h:1630  BT ≥ yellowPhase_R_CV
  FCs   — Program.h:1645  BT ≥ fcsPhase_R_CV
  t_roast — đếm từ CHARGE (firmware bật timeRoastEn lúc CHARGE)

Hai ngưỡng DE/FCs nằm trên HMI và khối tương thích KHÔNG đẩy ra → truyền vào qua
`de_temp` / `fcs_temp` (mặc định lấy từ bản đồ dùng chung).

Đầu ra có CÙNG hình dạng với pc_link_map.decode() → giao diện không cần biết dữ
liệu đến từ đâu. Khoá `derived` liệt kê số nào là do app tính, để UI nói thật.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pc_link_map import DERIVE, STP     # noqa: E402


class Kalman:
    """Bản Python của SimpleKalmanFilter (thư viện firmware dùng) — cùng công thức."""

    def __init__(self, e_mea: float, e_est: float, q: float):
        self.err_measure = e_mea
        self.err_estimate = e_est
        self.q = q
        self.last_estimate = 0.0

    def update(self, mea: float) -> float:
        gain = self.err_estimate / (self.err_estimate + self.err_measure)
        cur = self.last_estimate + gain * (mea - self.last_estimate)
        self.err_estimate = (1.0 - gain) * self.err_estimate + \
            abs(self.last_estimate - cur) * self.q
        self.last_estimate = cur
        return cur


class RoastDeriver:
    """Nạp mẫu (BT/ET) mỗi giây, trả về các số firmware vốn tự tính.

    Vòng đời: reset() → feed() mỗi giây → charge()/drop() khi có sự kiện.
    """

    def __init__(self, de_temp: float | None = None, fcs_temp: float | None = None):
        self.de_temp = DERIVE["de_temp_default"] if de_temp is None else de_temp
        self.fcs_temp = DERIVE["fcs_temp_default"] if fcs_temp is None else fcs_temp
        self.reset()

    # ── vòng đời mẻ ─────────────────────────────────────────────────────────
    def reset(self):
        self._kal_bt = Kalman(*DERIVE["kalman_bt"])
        self._kal_et = Kalman(*DERIVE["kalman_et"])
        self._bt_hist: list[float] = []     # BT mỗi giây, để lấy mẫu cách đây 3 s
        self._et_hist: list[float] = []
        self.ror_bt = 0.0
        self.ror_et = 0.0
        self.t_roast = 0                    # giây từ CHARGE
        self.charged = False
        self.dropped = False
        self.step = STP["CHARGE"] - 1       # chưa nạp
        self.mile: dict[str, int] = {}      # mốc → giây
        self.mile_bt: dict[str, float] = {}  # mốc → nhiệt lúc đó
        self._bt_tp_pre = 9999.0            # theo dõi đáy BT (giống BT_TP_Pre)
        self._n = 0                         # số mẫu đã nạp (kể cả trước CHARGE)

    def charge(self, bt: float):
        """Hạt vào trống — đồng hồ mẻ bắt đầu từ đây."""
        if self.charged:
            return
        self.charged = True
        self.t_roast = 0
        self.step = STP["TP"]               # firmware sang STP_TP ngay sau CHARGE
        self._bt_tp_pre = bt
        self.mile["CHARGE"] = 0
        self.mile_bt["CHARGE"] = bt

    def drop(self, bt: float):
        if self.dropped:
            return
        self.dropped = True
        self.step = STP["DROP"]
        self.mile.setdefault("DROP", self.t_roast)
        self.mile_bt.setdefault("DROP", bt)

    # ── nạp 1 mẫu/giây ──────────────────────────────────────────────────────
    def feed(self, bt: float, et: float):
        self._n += 1
        self._bt_hist.append(bt)
        self._et_hist.append(et)
        w = DERIVE["ror_window_s"]
        keep = w + 2
        if len(self._bt_hist) > keep:
            del self._bt_hist[:-keep]
            del self._et_hist[:-keep]

        # ── RoR: đúng nhịp 3 giây của firmware ─────────────────────────────
        if self._n % w == 0 and len(self._bt_hist) > w:
            g = DERIVE["ror_gain"]
            self.ror_bt = self._clamp(
                self._kal_bt.update((bt - self._bt_hist[-1 - w]) * g),
                DERIVE["ror_bt_clamp"])
            self.ror_et = self._clamp(
                self._kal_et.update((et - self._et_hist[-1 - w]) * g),
                DERIVE["ror_et_clamp"])

        if not self.charged or self.dropped:
            return
        self.t_roast += 1
        self._advance(bt)

    @staticmethod
    def _clamp(v: float, lim: float) -> float:
        return max(-lim, min(lim, v))

    def _advance(self, bt: float):
        """Chuyển bước đúng luật firmware — mỗi mốc chốt đúng một lần."""
        if self.step == STP["TP"]:
            # sau ulimitTPTime và BT còn dưới ulimitTPTemp: bám đáy, quay đầu là TP
            if self.t_roast > DERIVE["tp_min_time_s"] and bt < DERIVE["tp_max_temp"]:
                if bt <= self._bt_tp_pre:
                    self._bt_tp_pre = bt
                else:
                    self._mark("TP", self._bt_tp_pre)
                    self.step = STP["DE"]
        elif self.step == STP["DE"]:
            if bt >= self.de_temp:
                self._mark("DE", bt)
                self.step = STP["FCs"]
        elif self.step == STP["FCs"]:
            if bt >= self.fcs_temp:
                self._mark("FCs", bt)
                self.step = STP["DEV"]
                self._mark("DEV", bt)     # firmware sang DEV ngay khi chạm FCs

    def _mark(self, name: str, bt: float):
        self.mile.setdefault(name, self.t_roast)
        self.mile_bt.setdefault(name, bt)

    # ── gói dữ liệu — CÙNG hình dạng với pc_link_map.decode() ───────────────
    def snapshot(self, raw: dict, hb: int = 0) -> dict:
        """raw = dict từ decode_artisan(). Trả về gói giao diện dùng được ngay."""
        step = self.step
        return {
            "bt": raw["bt"],
            "et": raw["et"],
            "ror_bt": round(self.ror_bt, 2),
            "ror_et": round(self.ror_et, 2),
            "ror_pro": 0.0,               # cần hồ sơ mẫu — app tự tính ở lớp trên
            "gas": raw["gas"],
            "air": raw["air"],
            "drum": raw["drum"],
            "sv": raw["sv"],
            "vac": raw["vac"],
            "step": step,
            "t_roast": self.t_roast,
            "phase": {"dry": step >= STP["TP"],
                      "mai": step >= STP["FCs"],
                      "dev": step >= STP["DEV"]},
            "flags": {
                "auto": bool(raw.get("auto")),
                "gas": raw["gas"] > 0,
                "charge": bool(raw.get("charge")),
                "drop": bool(raw.get("drop")),
                "escape": bool(raw.get("escape")),
                "cool": bool(raw.get("cool")),
                "pc_control": False,      # khối cũ không nói được — app tự biết
                "flame": None,            # KHÔNG đọc được ở khối cũ (gasSignal)
                "pc_lost": False,
                "flame_fail": False,
            },
            "hb": hb,
            # mốc CHÍNH bộ suy diễn chốt (giây + nhiệt lúc đó) — giao diện dùng
            # thẳng, khỏi suy lại từ step (suy lại là dính lệch một bước)
            "mile": dict(self.mile),
            "mile_bt": {k: round(v, 1) for k, v in self.mile_bt.items()},
            # nói thật: các số dưới đây do APP tính, không phải máy gửi
            "derived": ["ror_bt", "ror_et", "step", "t_roast", "phase", "mile"],
        }
