"""
OTL Roast Lab — app rang & phân tích roast log real-time cho máy OTL-06ALS.
(Có thêm chế độ máy rang ảo để test firmware ở nhà khi không có tủ điện.)

Gộp 3 thứ vào 1 tool test code, KHÔNG cần board/tủ điện:
  1. Nạp 1 profile rang (CSV Roaster Scope, cùng format SD của firmware).
  2. "Firmware ảo" chạy đúng nguyên lý calibProgram() (Program.h) bằng Python:
     - FF: air/gas/drum/vacuum lấy thẳng từ profile theo từng giây.
     - Sau TP, nếu BT lệch quá deadband thì tự bù gas (bậc tính mỗi 10s,
       kẹp theo pha Tp/De/Fcs) — CỘNG lên FF mỗi giây để duy trì lực bù.
  3. Model nhiệt gas→RoR→BT/ET đóng vòng kín: gas do calib ra → nhiệt phản ứng
     → BT mới → calib lại. Xem calib có kéo BT bám profile không.

Có thêm: expose Modbus slave (map include/Modbus_Slave.h) trên 1 cổng COM để
Artisan PC / HMI thật nối vào đọc BT/ET/gas/air/drum/vacuum như máy thật.

Module BT vật lý (48_RS485_RTU_BT_SIMU, cắm qua Silicon Labs CP210x): app tự dò
cổng CP210x và tự nối lúc mở. Khi mô phỏng chạy, BT model được lái thẳng ra module
bằng bộ lệnh '1/2/5/9' (+0.1/0.2/0.5/1.0) và 'q/w/e/r' (giảm) — firmware thật đọc
BT đó qua RS485, không cần cặp nhiệt.

Tham số nhiệt gốc: analysis-roaster-thermal.md (gas 35% cân bằng, ~1.5°C/min/%).
Giao tiếp Modbus: ref-sim-interface.md.

Chạy:  python tools/otl_roast_lab.py
Phụ thuộc: pip install customtkinter matplotlib pyserial
           (Modbus slave cần thêm: pip install pymodbus)
Build exe: python -m PyInstaller tools/OTLRoastLab.spec
"""

import os
import threading
import time
import tkinter as tk
from dataclasses import dataclass, field
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw, ImageFilter
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import serial.tools.list_ports

HERE = os.path.dirname(os.path.abspath(__file__))
ICON = os.path.join(HERE, "otl_icon.ico")

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# ─────────────────────────────────────────────────────────────────────────────
# HiDPI / 2K — render sắc nét ở phân giải cao, phóng toàn UI theo 1 hệ số duy nhất
# ─────────────────────────────────────────────────────────────────────────────
UI_SCALE = 1.0   # gán trong App.__init__ theo bề ngang màn hình


def _s(v):
    """Nhân kích thước pixel theo hệ số phóng UI (dùng cho widget vẽ bằng PIL)."""
    return max(1, int(round(v * UI_SCALE)))


def _pick_ui_scale(screen_w):
    """Chọn hệ số phóng theo phân giải ngang: FHD≈1.0, 2K≈1.3, 4K≈1.6."""
    if screen_w >= 3200:
        return 1.6
    if screen_w >= 2560:
        return 1.3
    if screen_w >= 1920:
        return 1.1
    return 1.0


def _enable_hidpi():
    """Bật DPI-aware (render native, hết mờ) + tắt auto-DPI của ctk để tự phóng."""
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)   # per-monitor v2
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass
    try:
        ctk.deactivate_automatic_dpi_awareness()   # chỉ dùng UI_SCALE của ta
    except Exception:
        pass


_enable_hidpi()


# ─────────────────────────────────────────────────────────────────────────────
# Cấu hình — chỉnh được từ tab Config
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class CalibConfig:
    """Tham số calibProgram() — khớp Program.h + $M HMI (iMemHMI)."""
    cl_range_bt: int = 10   # deadband trước FCS (0.1°C) — clRangeBt, ±1.0°C
    cl_range_fcs: int = 6   # deadband từ FCS trở đi (0.1°C) — siết ±0.6°C
    step_pct: int = 5       # bước gas mỗi bậc (%) — numIncGas = calibGas*step
    eval_sec: int = 10      # chu kỳ tính lại bậc bù (giây) — timeCalibGas>=10
    tp_calib: int = 20      # cap bù gas giai đoạn Tp (BT<DE) — TpCalib_R (%)
    de_calib: int = 15      # cap bù gas giai đoạn De (DE<=BT<FCS) — DeCalib_R (%)
    fcs_calib: int = 10     # cap bù gas giai đoạn Fcs (BT>=FCS) — FcsCalib_R (%)


@dataclass
class ThermalConfig:
    """Model nhiệt — trích analysis-roaster-thermal.md."""
    gas_equilib: float = 35.0   # % gas cân bằng (RoR≈0) vùng 210-220°C
    gas_sens: float = 1.5       # °C/min RoR cho mỗi 1% gas
    heatloss_k: float = 0.020   # mất nhiệt theo (BT-ambient)
    ambient: float = 28.0       # nhiệt môi trường
    gas_lag_s: float = 5.0      # lag gas→RoR (giây)
    air_cool_k: float = 0.15    # air% làm giảm RoR
    et_offset: float = 18.0     # ET cao hơn BT khi cân bằng


# Preset model theo máy — máy NHỎ phản ứng nhanh (sens cao, equilib + lag thấp),
# máy LỚN quán tính lớn (sens thấp, equilib + lag cao). Chỉnh tinh trong Config.
THERMAL_PRESETS = {
    "Cacao 30kg (M06)": dict(gas_equilib=22, gas_sens=1.0, heatloss_k=0.028,
                                  gas_lag_s=6, air_cool_k=0.15),
    "Máy 30kg":  dict(gas_equilib=35, gas_sens=1.0, heatloss_k=0.020, gas_lag_s=6,
                      air_cool_k=0.15),
    "Máy 12kg":  dict(gas_equilib=28, gas_sens=1.3, heatloss_k=0.024, gas_lag_s=5,
                      air_cool_k=0.16),
    "Máy 6kg":   dict(gas_equilib=22, gas_sens=1.6, heatloss_k=0.028, gas_lag_s=4,
                      air_cool_k=0.18),
    "Máy 3kg":   dict(gas_equilib=18, gas_sens=2.0, heatloss_k=0.032, gas_lag_s=3,
                      air_cool_k=0.20),
}


# ─────────────────────────────────────────────────────────────────────────────
# Profile — nạp CSV cùng format SD firmware
#   Cột: Time1  Time2  ET  BT  Event  Air(%)  Burner(%)  Drum(%)  VacFlag  VacSP
#   Index theo Time2 (mm:ss) kể từ CHARGE. BT lưu ×10 giống Temperature_BT.
# ─────────────────────────────────────────────────────────────────────────────
EVENT_LABELS = {"CHARGE": "CHARGE", "TP": "TP", "DRY END": "DE",
                "DRYEND": "DE", "FCS": "FCS", "DROP": "DROP"}


@dataclass
class Profile:
    bt: list = field(default_factory=list)     # ×10 (0.1°C)
    et: list = field(default_factory=list)     # ×10
    air: list = field(default_factory=list)    # %
    gas: list = field(default_factory=list)    # %
    drum: list = field(default_factory=list)   # %
    vacflag: list = field(default_factory=list)
    vacsp: list = field(default_factory=list)  # Pa
    events: dict = field(default_factory=dict) # nhãn -> index giây
    name: str = ""

    @property
    def n(self):
        return len(self.bt)

    def de_bt(self):
        """DE_PRO_R (0.1°C). Mốc thiếu → 0, GIỐNG firmware (rtDRYe>0 mới lấy).
        Hệ quả (đúng máy thật): FCs trống → BT>=0 luôn → deadband siết + cap Fcs cả mẻ."""
        i = self.events.get("DE")
        return self.bt[i] if i is not None and 0 < i < self.n else 0

    def fcs_bt(self):
        i = self.events.get("FCS")
        return self.bt[i] if i is not None and 0 < i < self.n else 0


def _int(s, default=0):
    """atoi kiểu firmware: '100.0' → 100, '' → default."""
    try:
        return int(float(s.strip()))
    except (ValueError, AttributeError):
        return default


def _int_x10(s, default=0):
    """'134.3' → 1343 (0.1°C như Temperature_BT)."""
    try:
        return int(float(s.strip()) * 10 + 0.5)
    except (ValueError, AttributeError):
        return default


def _mmss(s):
    """'02:12' → 132 giây; rỗng → None."""
    try:
        mm, ss = (int(x) for x in s.strip().split(":"))
        return mm * 60 + ss
    except (ValueError, AttributeError):
        return None


def parse_profile(path):
    """Đọc CSV Roaster Scope → Profile (mảng theo giây từ CHARGE)."""
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()

    # Mốc pha nằm ở dòng header ("CHARGE:00:00  TP:02:12  DRYe:18:35  FCs:  DROP:30:03")
    # là roast time (Time2) — parse trực tiếp, ưu tiên hơn cột Event.
    events = {}
    hdr = next((l for l in lines if "CHARGE:" in l), "")
    for tok in hdr.split("\t"):
        if ":" not in tok:
            continue
        key, _, rest = tok.partition(":")
        label = {"CHARGE": "CHARGE", "TP": "TP", "DRYE": "DE",
                 "FCS": "FCS", "DROP": "DROP"}.get(key.strip().upper())
        if label:
            idx = _mmss(rest)
            # Mốc 00:00 (trừ CHARGE) = chưa đánh dấu — GIỐNG firmware (rtTP/rtDRYe/rtFCs > 0)
            if idx is not None and (idx > 0 or label == "CHARGE"):
                events[label] = idx

    # Tìm dòng header dữ liệu (bắt đầu "Time1")
    start = next((i + 1 for i, l in enumerate(lines) if l.startswith("Time1")), 0)

    rows = []  # (idx, et, bt×10, event, air, gas, drum, vacflag, vacsp)
    for l in lines[start:]:
        c = l.split("\t")
        if len(c) < 5 or not c[0].strip() or not c[0].strip()[0].isdigit():
            continue
        idx = _mmss(c[1])
        if idx is None:         # hàng trước CHARGE (Time2 rỗng) → bỏ
            continue
        et = _int(c[2]) if len(c) > 2 else 0
        bt = int(_int_x10(c[3]) if len(c) > 3 else 0)
        ev = c[4].strip() if len(c) > 4 else ""
        air = _int(c[5]) if len(c) > 5 else 0
        gas = _int(c[6]) if len(c) > 6 else 0
        drum = _int(c[7]) if len(c) > 7 else 0
        vacflag = _int(c[8]) if len(c) > 8 else 0
        vacsp = _int(c[9]) if len(c) > 9 else 0
        rows.append((idx, et, bt, ev, air, gas, drum, vacflag, vacsp))

    if not rows:
        raise ValueError("Không đọc được data row nào (kiểm tra format CSV).")

    n = rows[-1][0] + 1
    p = Profile(name=os.path.basename(path), events=events)
    p.bt = [0] * n; p.et = [0] * n; p.air = [0] * n; p.gas = [0] * n
    p.drum = [0] * n; p.vacflag = [0] * n; p.vacsp = [0] * n
    for idx, et, bt, ev, air, gas, drum, vf, vsp in rows:
        if idx >= n:
            continue
        p.et[idx] = et; p.bt[idx] = bt; p.air[idx] = air; p.gas[idx] = gas
        p.drum[idx] = drum; p.vacflag[idx] = vf; p.vacsp[idx] = vsp
        label = EVENT_LABELS.get(ev.upper().strip())
        if label and label not in p.events:   # cột Event bổ sung nếu header thiếu
            p.events[label] = idx

    # Điền các ô trống giữa các mẫu (giữ giá trị trước) để FF liên tục
    for arr in (p.bt, p.et, p.air, p.gas, p.drum, p.vacflag, p.vacsp):
        last = 0
        for i in range(n):
            if arr[i] == 0 and i > 0:
                arr[i] = last
            last = arr[i]

    # RoR profile (°C/phút, cửa sổ 15s) — vẽ tham chiếu như Artisan/Cropster
    win = 15
    p.ror = [0.0] * n
    for i in range(n):
        j = max(0, i - win)
        if i > j:
            p.ror[i] = (p.bt[i] - p.bt[j]) / 10.0 / (i - j) * 60.0
    return p


# ─────────────────────────────────────────────────────────────────────────────
# Model nhiệt — bậc nhất gas/air → RoR → tích phân BT/ET (như virtual_roaster)
# ─────────────────────────────────────────────────────────────────────────────
class ThermalModel:
    def __init__(self, cfg: ThermalConfig, bt0=None, et0=None):
        self.cfg = cfg
        self.bt = bt0 if bt0 is not None else cfg.ambient   # °C thực
        self.et = et0 if et0 is not None else cfg.ambient
        self.ror_bt = 0.0
        self.ror_et = 0.0
        self._gas_eff = 0.0

    def step(self, gas_pct, air_pct, dt=1.0):
        c = self.cfg
        alpha = dt / (c.gas_lag_s + dt)
        self._gas_eff += alpha * (gas_pct - self._gas_eff)

        gas_drive = (self._gas_eff - c.gas_equilib) * c.gas_sens
        heat_loss = c.heatloss_k * max(self.bt - c.ambient, 0.0)
        air_cool = c.air_cool_k * air_pct * 0.1
        self.ror_bt = gas_drive - heat_loss - air_cool
        self.ror_et = gas_drive * 1.2 - heat_loss - c.air_cool_k * air_pct

        self.bt += self.ror_bt * dt / 60.0
        self.et += self.ror_et * dt / 60.0
        self.et += 0.1 * (self.bt + c.et_offset - self.et)
        self.bt = max(self.bt, c.ambient)
        self.et = max(self.et, c.ambient)
        return self.bt, self.et


# ─────────────────────────────────────────────────────────────────────────────
# Firmware ảo — calibProgram() bằng Python (bám sát Program.h:782)
# ─────────────────────────────────────────────────────────────────────────────
class VirtualFirmware:
    def __init__(self, cfg: CalibConfig):
        self.cfg = cfg
        self.reset()

    def reset(self):
        self.time_calib_gas = 0
        self.num_inc_gas = 0
        self.calib_gas = 0
        self.gas = 0        # gas% lệnh ra (FF ± bù)
        self.air = 0
        self.drum = 0
        self.vac_flag = 0
        self.vac_sp = 0

    def step(self, prof: Profile, roast_t, bt_x10, past_tp):
        """1 giây calibProgram. bt_x10 = BT thực đo (0.1°C). Trả gas/air/drum."""
        idx = min(roast_t, prof.n - 1)
        c = self.cfg

        # FF — air/drum/vacuum/gas nền từ profile
        self.air = prof.air[idx]
        self.drum = prof.drum[idx]
        self.vac_flag = prof.vacflag[idx]
        self.vac_sp = prof.vacsp[idx]
        gas = prof.gas[idx]

        sd_bt = prof.bt[idx]
        de = prof.de_bt()
        fcs = prof.fcs_bt()

        # Hiệu chỉnh gas — chỉ sau TP (progStep > STP_TP)
        if past_tp:
            cl = c.cl_range_fcs if bt_x10 >= fcs else c.cl_range_bt
            if bt_x10 > sd_bt + cl or bt_x10 < sd_bt - cl:
                self.time_calib_gas += 1
                if self.time_calib_gas >= c.eval_sec:
                    self.calib_gas = abs(bt_x10 - sd_bt) // 5
                    if self.calib_gas <= 0:
                        self.calib_gas = 1
                    self.num_inc_gas = self.calib_gas * c.step_pct
                    # Kẹp theo pha — thứ tự khớp 3 if TUẦN TỰ của firmware
                    # (câu BT>=FCS đứng cuối nên đè; FCS=0 → cap Fcs cả mẻ)
                    if bt_x10 >= fcs:
                        cap = c.fcs_calib
                    elif bt_x10 >= de:
                        cap = c.de_calib
                    else:
                        cap = c.tp_calib
                    if self.num_inc_gas >= cap:
                        self.num_inc_gas = cap
                    self.time_calib_gas = 0
                # CỘNG bù lên FF mỗi giây (cố ý — duy trì lực bù)
                if bt_x10 < sd_bt - cl:
                    gas += self.num_inc_gas
                if bt_x10 > sd_bt + cl:
                    gas -= self.num_inc_gas
                gas = max(0, min(100, gas))
            else:
                self.time_calib_gas = 0
                self.num_inc_gas = 0
                self.calib_gas = 0

        self.gas = gas
        return gas, self.air, self.drum


# ─────────────────────────────────────────────────────────────────────────────
# Engine — buộc model + firmware ảo thành vòng kín
# ─────────────────────────────────────────────────────────────────────────────
class SimEngine:
    def __init__(self, calib: CalibConfig, thermal: ThermalConfig):
        self.calib_cfg = calib
        self.thermal_cfg = thermal
        self.fw = VirtualFirmware(calib)
        self.model = ThermalModel(thermal)
        self.profile = None
        self.roast_t = 0
        self.running = False
        self.gas_ff = 0
        self.lock = threading.Lock()
        self.hist = []   # (t, bt°C, profile_bt°C, gas, air, ror)
        # PC control — Artisan làm master ghi gas/air/drum + nút qua Modbus
        # (giống PC_CONTROL_BTN_R=1 trong handle_Modbus_Slave)
        self.pc_control = False
        self.pc_gas = 0
        self.pc_air = 0
        self.pc_drum = 0
        # MANUAL — người vận hành xoay đồng hồ tại chỗ (bỏ FF/calib)
        self.manual = False
        self.man_gas = 0
        self.man_air = 0
        self.man_drum = 0

    def load(self, profile):
        with self.lock:
            self.profile = profile
            self.reset()

    def reset(self):
        self.fw.reset()
        self.model = ThermalModel(self.thermal_cfg)
        self.roast_t = 0
        self.running = False
        self.hist = []

    def charge(self):
        with self.lock:
            if not self.profile and not self.pc_control and not self.manual:
                return
            pc, man = self.pc_control, self.manual
            self.reset()
            self.pc_control, self.manual = pc, man   # reset() không xoá chế độ
            if self.profile:
                # Seed BT/ET = mốc CHARGE của profile
                self.model.bt = self.profile.bt[0] / 10.0
                self.model.et = self.profile.et[0] if self.profile.et[0] else self.model.bt + self.thermal_cfg.et_offset
            self.running = True

    def tick(self):
        with self.lock:
            # Chỉ mô phỏng khi đã Charge — không thì model nguội dần + hist phình rác
            if not self.running:
                return
            # PC CONTROL (Artisan) / MANUAL (xoay đồng hồ) — cùng cơ chế: bỏ FF/calib,
            # model chạy theo lệnh đặt tay. PC control giống PC_CONTROL_BTN_R=1.
            if self.pc_control or self.manual:
                src = (self.pc_gas, self.pc_air, self.pc_drum) if self.pc_control \
                    else (self.man_gas, self.man_air, self.man_drum)
                gas = max(0, min(100, int(src[0])))
                air = max(0, min(100, int(src[1])))
                self.fw.gas, self.fw.air = gas, air
                self.fw.drum = max(0, min(100, int(src[2])))
                self.gas_ff = gas
                self.model.step(gas, air)
                target = (self.profile.bt[min(self.roast_t, self.profile.n - 1)] / 10.0
                          if self.profile else self.model.bt)
                self.hist.append((self.roast_t, self.model.bt, target, gas, air,
                                  self.model.ror_bt, self.model.et, self.fw.drum))
                self.roast_t += 1
                return
            if not self.profile:
                return
            p = self.profile
            bt_x10 = int(self.model.bt * 10 + 0.5)
            tp_idx = p.events.get("TP", 0)
            past_tp = self.roast_t > tp_idx
            self.gas_ff = p.gas[min(self.roast_t, p.n - 1)]
            gas, air, _drum = self.fw.step(p, self.roast_t, bt_x10, past_tp)
            self.model.step(gas, air)
            idx = min(self.roast_t, p.n - 1)
            self.hist.append((self.roast_t, self.model.bt, p.bt[idx] / 10.0, gas,
                              air, self.model.ror_bt, self.model.et, self.fw.drum))
            self.roast_t += 1
            # Hết profile → tự DROP (dừng, giữ nguyên đồ thị + số liệu)
            if self.roast_t >= p.n:
                self.running = False

    def phase(self):
        if self.pc_control:
            return "PC CONTROL" if self.running else "PC (chờ Charge)"
        if not self.profile:
            return "—"
        if not self.running:
            return "DROP ✓" if self.roast_t >= self.profile.n else "—"
        bt = int(self.model.bt * 10 + 0.5)
        p = self.profile
        if self.roast_t <= p.events.get("TP", 0):
            return "DRY (chưa qua TP)"
        # Cùng thứ tự nhánh với cap gas (FCS xét trước — mốc trống=0 → vùng Fcs cả mẻ)
        if bt >= p.fcs_bt():
            return "DEV (vùng Fcs)"
        if bt >= p.de_bt():
            return "MAILLARD"
        return "DRY"


# ─────────────────────────────────────────────────────────────────────────────
# Module BT vật lý (48_RS485_RTU_BT_SIMU) — cắm qua Silicon Labs CP210x.
# Bộ lệnh 1 ký tự đổi BT (đơn vị 0.1°C), module echo "BT:xx" mỗi lệnh.
# App lái BT module bám theo BT model: ghép chuỗi lệnh tham lam mỗi giây sim.
# ─────────────────────────────────────────────────────────────────────────────
UP_STEPS = [("9", 10), ("5", 5), ("2", 2), ("1", 1)]      # +1.0 / +0.5 / +0.2 / +0.1
DOWN_STEPS = [("r", 10), ("e", 5), ("w", 2), ("q", 1)]    # giảm tương ứng


def compose_commands(delta_tenths, max_cmds=100):
    """Ghép chuỗi lệnh để dời BT module đúng delta (0.1°C). Cắt trần max_cmds."""
    cmds = []
    d = int(delta_tenths)
    for ch, val in UP_STEPS:
        while d >= val and len(cmds) < max_cmds:
            cmds.append(ch); d -= val
    for ch, val in DOWN_STEPS:
        while d <= -val and len(cmds) < max_cmds:
            cmds.append(ch); d += val
    return "".join(cmds), int(delta_tenths) - d   # (chuỗi, delta thực gửi)


def find_cp210x_port():
    """Tìm cổng Silicon Labs CP210x (module BT luôn hiện tên này)."""
    for p in serial.tools.list_ports.comports():
        desc = (p.description or "").upper()
        if "CP210" in desc or "SILICON LABS" in desc:
            return p.device
    return None


class BTModuleLink:
    """Nối serial tới module BT, lái BT module bám target từ model."""

    def __init__(self):
        self.ser = None
        self.mod_bt = None      # BT module theo dõi nội bộ (°C) — echo chỉ để hiển thị
        self.echo_bt = None     # BT module đọc từ echo (°C, độ phân giải 1°C)
        self._rx_run = False
        self._buf = ""
        self.lock = threading.Lock()

    @property
    def connected(self):
        return self.ser is not None

    def connect(self, port, baud=9600):
        self.ser = serial.Serial(port=port, baudrate=baud, timeout=0.2)
        self._rx_run = True
        threading.Thread(target=self._rx_loop, daemon=True).start()
        # Dò BT hiện tại của module: +0.1 rồi -0.1 (vô hại), chờ echo
        self.ser.write(b"1")
        time.sleep(0.4)
        self.ser.write(b"q")
        for _ in range(10):
            if self.echo_bt is not None:
                break
            time.sleep(0.1)
        with self.lock:
            self.mod_bt = self.echo_bt   # có thể None nếu module im lặng

    def disconnect(self):
        self._rx_run = False
        if self.ser:
            try:
                self.ser.close()
            except serial.SerialException:
                pass
            self.ser = None
        self.mod_bt = self.echo_bt = None

    def _rx_loop(self):
        import re
        while self._rx_run and self.ser:
            try:
                chunk = self.ser.read(128)
            except (serial.SerialException, TypeError):
                return
            if not chunk:
                continue
            self._buf += chunk.decode("ascii", "replace")
            while "\n" in self._buf:
                line, self._buf = self._buf.split("\n", 1)
                m = re.search(r"BT:\s*(-?\d+(?:\.\d+)?)", line)
                if m:
                    self.echo_bt = float(m.group(1))

    def track(self, target_c):
        """Lái BT module về target (°C). Gọi mỗi tick sim khi đang chạy."""
        if not self.ser:
            return
        with self.lock:
            if self.mod_bt is None:
                self.mod_bt = self.echo_bt
                if self.mod_bt is None:
                    return
            delta = round((target_c - self.mod_bt) * 10)
            if not delta:
                return
            cmds, sent = compose_commands(delta)
            if cmds:
                try:
                    self.ser.write(cmds.encode("ascii"))
                except serial.SerialException:
                    self.disconnect()
                    return
                self.mod_bt = round(self.mod_bt + sent / 10.0, 1)


# ─────────────────────────────────────────────────────────────────────────────
# Modbus slave — expose register map Artisan (include/Modbus_Slave.h)
# ─────────────────────────────────────────────────────────────────────────────
# Chỉ số holding register Artisan (include/Modbus_Slave.h)
R_BT, R_ET, R_AIR, R_GAS, R_DRUM = 0, 1, 2, 3, 4
R_UNDER, R_START, R_SV_SHOW, R_VACC = 9, 17, 19, 21
# Register Artisan GHI (PC control): setpoint + nút HMI ảo
R_AIR_W, R_GAS_W, R_DRUM_W = 10, 11, 20
R_CHARGE_BTN, R_DROP_BTN = 14, 15
MAX_REG = 27


class ModbusSlave:
    def __init__(self, engine):
        self.engine = engine
        self._ctx = None
        self._server = None
        self._loop = None
        self._thread = None
        self._last_btn = None
        self.running = False

    def start(self, port, baud, unit_id):
        try:
            import asyncio
            from pymodbus.datastore import (ModbusSlaveContext, ModbusServerContext,
                                            ModbusSequentialDataBlock)
            from pymodbus.server import ModbusSerialServer
            from pymodbus.transaction import ModbusRtuFramer
        except Exception as e:
            raise RuntimeError(f"pymodbus chưa cài / lỗi: {e}")

        block = ModbusSequentialDataBlock(0, [0] * (MAX_REG + 1))
        self._ctx = ModbusServerContext(
            slaves={unit_id: ModbusSlaveContext(hr=block, zero_mode=True)}, single=False)
        self._block = block

        # ModbusSerialServer.__init__ đòi event loop ĐANG chạy → dựng trong loop riêng.
        # Giữ loop + server để stop() shutdown async, nhả cổng COM (bản cũ StartSerialServer chặn, không handle).
        async def _run():
            self._server = ModbusSerialServer(context=self._ctx, framer=ModbusRtuFramer,
                                              port=port, baudrate=baud, stopbits=1,
                                              bytesize=8, parity="N")
            await self._server.serve_forever()

        def serve():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            try:
                self._loop.run_until_complete(_run())
            except asyncio.CancelledError:
                pass
            except Exception as e:
                print(f"[MODBUS] dừng: {e}")
            finally:
                self._loop.close()

        self.running = True
        self._thread = threading.Thread(target=serve, daemon=True)
        self._thread.start()
        threading.Thread(target=self._sync_loop, daemon=True).start()

    def _sync_once(self):
        """1 chu kỳ đồng bộ register ↔ engine (tách riêng để test headless)."""
        eng = self.engine
        m, fw = eng.model, eng.fw
        # Ghi trạng thái máy lên Artisan (Artisan chỉ đọc) — như handle_Modbus_Slave
        vals = {
            R_BT: int(m.bt * 10), R_ET: int(m.et * 10),
            R_AIR: int(fw.air), R_GAS: int(fw.gas), R_DRUM: int(fw.drum),
            R_VACC: int(fw.vac_sp), R_SV_SHOW: 0,
            R_START: 1 if eng.running else 0,
            R_UNDER: 0,
        }
        if eng.pc_control:
            del vals[R_START]   # PC control: Artisan sở hữu nút, không đè
        for addr, v in vals.items():
            self._block.setValues(addr, [v & 0xFFFF])

        if not eng.pc_control:
            self._last_btn = None
            return
        # PC CONTROL: đọc setpoint Artisan ghi → engine
        eng.pc_air = self._block.getValues(R_AIR_W, 1)[0]
        eng.pc_gas = self._block.getValues(R_GAS_W, 1)[0]
        eng.pc_drum = self._block.getValues(R_DRUM_W, 1)[0]
        # Nút CHARGE/DROP: firmware kích khi GIÁ TRỊ ĐỔI (SYNC_BTN) — bắt cạnh đổi
        cur = (self._block.getValues(R_CHARGE_BTN, 1)[0],
               self._block.getValues(R_DROP_BTN, 1)[0])
        if self._last_btn is not None:
            if cur[0] != self._last_btn[0]:
                self.engine.charge()
            if cur[1] != self._last_btn[1]:
                self.engine.running = False
        self._last_btn = cur

    def _sync_loop(self):
        self._last_btn = None
        while self.running:
            try:
                self._sync_once()
            except Exception:
                pass
            time.sleep(0.3)

    def stop(self):
        self.running = False
        srv, loop = self._server, self._loop
        if srv and loop:
            # shutdown là coroutine → chạy trên chính loop của server (thread-safe)
            try:
                import asyncio
                fut = asyncio.run_coroutine_threadsafe(srv.shutdown(), loop)
                fut.result(timeout=2)
            except Exception:
                pass
        self._server = self._loop = None


# ─────────────────────────────────────────────────────────────────────────────
# Tổng kết mẻ — đo chất lượng bám profile sau khi DROP (kiểu RoastGuard/QC)
# ─────────────────────────────────────────────────────────────────────────────
def roast_summary(hist, prof, band_c=1.0):
    """Thống kê độ bám BT vs profile SAU TP. None nếu chưa đủ dữ liệu."""
    if not prof or len(hist) < 10:
        return None
    tp = prof.events.get("TP", 0)
    devs = [(t, abs(bt - pbt)) for (t, bt, pbt, *_ ) in hist if t > tp]
    if len(devs) < 5:
        return None
    allv = [d for _, d in devs]
    drop = prof.events.get("DROP", hist[-1][0])

    def phase_avg(a, b):
        i0, i1 = prof.events.get(a), prof.events.get(b)
        if i0 is None or i1 is None or i1 <= i0:
            return None
        vs = [d for t, d in devs if i0 <= t < i1]
        return sum(vs) / len(vs) if vs else None

    phases = []
    for name, a, b in [("Dry", "TP", "DE"), ("Maillard", "DE", "FCS"),
                       ("Dev", "FCS", "DROP")]:
        avg = phase_avg(a, b)
        if avg is not None:
            phases.append((name, avg))
    return {
        "dur": drop,
        "max": max(allv),
        "avg": sum(allv) / len(allv),
        "pct_out": 100.0 * sum(1 for d in allv if d > band_c) / len(allv),
        "band": band_c,
        "phases": phases,
    }


def hist_to_csv(hist, prof):
    """Kết xuất lịch sử mẻ ảo → CSV Roaster Scope (cùng format SD firmware, nạp lại được).
    Cột: Time1 Time2 ET BT Event Air Burner Drum VacFlag VacSP."""
    import datetime
    if not hist:
        return None
    n = len(hist)
    drop = hist[-1][0]
    ev = dict(prof.events) if prof else {}
    ev.setdefault("CHARGE", 0)
    ev["DROP"] = drop
    if "TP" not in ev:  # dò turning point = BT thấp nhất (khi manual/pc không có profile)
        ti = min(range(n), key=lambda i: hist[i][1])
        ev["TP"] = hist[ti][0]

    def mmss(s):
        return f"{s // 60:02d}:{s % 60:02d}"

    def hv(key):
        return mmss(ev[key]) if key in ev else ""

    now = datetime.datetime.now()
    hdr = [f"Date:{now.strftime('%d.%m.%Y %H:%M:%S')}", "Unit:C",
           f"CHARGE:{hv('CHARGE')}", f"TP:{hv('TP')}", f"DRYe:{hv('DE')}",
           f"FCs:{hv('FCS')}", "FCe:", "SCs:", "SCe:", f"DROP:{hv('DROP')}",
           "COOL:", f"Time:{now.strftime('%H:%M')}"]
    lines = ["\t".join(hdr),
             "Time1\tTime2\tET\tBT\tEvent\tAir(%)\tBurner(%)\tDrum(%)\tVacFlag\tVacSP(Pa)"]
    label_at = {}   # index giây → nhãn Event (parse_profile đọc được)
    for lab, key in [("CHARGE", "CHARGE"), ("TP", "TP"), ("DRY END", "DE"),
                     ("FCs", "FCS"), ("DROP", "DROP")]:
        if key in ev:
            label_at[ev[key]] = lab
    for row in hist:
        t, bt, _pbt, gas, air, _ror = row[:6]
        et = row[6] if len(row) > 6 else bt + 18
        drum = row[7] if len(row) > 7 else 0
        lines.append("\t".join([mmss(t), mmss(t), f"{et:.1f}", f"{bt:.1f}",
                                label_at.get(t, ""), f"{int(air)}", f"{int(gas)}",
                                f"{int(drum)}", "0", "0"]))
    return "\r\n".join(lines) + "\r\n"


# ─────────────────────────────────────────────────────────────────────────────
# GUI — Executive graphite: nền than phân tầng, nhấn kim loại ấm (champagne),
# hairline mảnh, bóng khuếch tán nhẹ, số tabular. Sang = ít chi tiết, nhiều khoảng thở.
# ─────────────────────────────────────────────────────────────────────────────
# Graphite 3 lớp tối tạo chiều sâu
NEU_BG   = "#0f1216"    # nền CỬA SỔ — sâu nhất
CARD_BG  = "#191d23"    # mặt panel/card
SCREEN   = "#0b0d10"    # "màn hình" biểu đồ / ô lõm — sâu hơn panel (khung tranh nổi)
NEU_DARK = "#070809"    # bóng tối neu (rất nhẹ)
NEU_LITE = "#1c2128"    # highlight neu
BORDER   = "#2b313a"    # hairline 1px sáng mờ
HAIR2    = "#20252c"    # hairline mờ hơn (phân tách nội bộ)
TXT      = "#eef1f5"    # chữ chính
TXT_DIM  = "#8b93a0"    # nhãn phụ
TXT_MUTE = "#586069"    # rất mờ (mốc chưa đạt, đơn vị)
FONT     = "Segoe UI"           # nhãn (Barlow-like)
MONO     = "Consolas"           # SỐ LIỆU tabular — digit không nhảy khi đổi
DISP     = "Bahnschrift SemiCondensed"  # nhãn hoa công nghiệp (không dùng cho số chính)
# Nhấn KIM LOẠI ẤM champagne — 1 màu chủ đạo, dùng tiết chế. Data muted, sang.
AMBER  = "#d8bd86"   # BT + branding + primary — champagne (thay vàng chói)
CYAN   = "#8fb6c8"   # ET — steel xanh trầm
INDIGO = "#a29ac9"   # RoR — lavender trầm
ORANGE = "#cf9f61"   # Gas — copper ấm
BLUE   = "#7aa2c9"   # Airflow — steel-blue
TEAL   = "#63b1a4"   # Drum — teal trầm
RED    = "#b0483f"   # CHỈ alarm / Stop — oxblood đỏ trầm sang
GREEN  = "#6fae7d"   # CHỈ đã kết nối / đang chạy — sage


def _rgb(c):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def _track(s, sp=" "):
    """Giãn cách chữ (letter-spacing) bằng thin-space — nhãn hoa kiểu thiết bị đo."""
    return sp.join(s)


SSAA = 3   # bội số supersampling: vẽ ở SSAA× rồi thu LANCZOS → viền mượt, hết răng cưa


def make_neu(w, h, radius=20, base=NEU_BG, pressed=False, glow=None,
             off=6, blur=9):
    """Ảnh thẻ neumorphic w×h: mặt phẳng cùng màu nền + bóng kép mềm.
    Vẽ ở SSAA× rồi thu nhỏ để viền squircle sắc, khử răng cưa (chất lượng 2K).
    pressed=True → bóng lõm (nhấn). glow → viền accent mảnh (evolved)."""
    w, h = max(int(w), 12), max(int(h), 12)
    k = SSAA
    W, H, R = w * k, h * k, radius * k
    bl = blur * k
    pad = off * k + bl + 2 * k
    # kẹp để không đảo ngược khi khung quá nhỏ (Configure kích thước 1px lúc đầu)
    rect = [pad, pad, max(pad + 1, W - pad), max(pad + 1, H - pad)]
    o = (-off if pressed else off) * k
    res = Image.new("RGBA", (W, H), _rgb(base) + (255,))

    def shadow(color, dx, dy):
        s = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(s).rounded_rectangle(
            [rect[0] + dx, rect[1] + dy, rect[2] + dx, rect[3] + dy],
            radius=R, fill=_rgb(color) + (255,))
        return s.filter(ImageFilter.GaussianBlur(bl))

    res = Image.alpha_composite(res, shadow(NEU_DARK, o, o))       # dưới-phải
    res = Image.alpha_composite(res, shadow(NEU_LITE, -o, -o))     # trên-trái
    face = ImageDraw.Draw(res)
    face.rounded_rectangle(rect, radius=R, fill=_rgb(base) + (255,))
    if glow:
        face.rounded_rectangle(rect, radius=R, outline=_rgb(glow) + (150,),
                               width=2 * k)
    res = res.convert("RGB").resize((w, h), Image.LANCZOS)
    return ImageTk.PhotoImage(res)


class NeuCard(tk.Frame):
    """Thẻ nổi neumorphic co giãn. Đặt nội dung vào `.body` (khớp màu mặt thẻ)."""

    def __init__(self, master, radius=20, inset=20, glow=None, **kw):
        super().__init__(master, bg=NEU_BG, bd=0, highlightthickness=0, **kw)
        self._radius, self._inset, self._glow = radius, inset, glow
        self._img = None
        self._job = None
        self._bg = tk.Label(self, bd=0, highlightthickness=0, bg=NEU_BG)
        self._bg.place(x=0, y=0, relwidth=1, relheight=1)
        # body = tk.Frame thuần để place() nhận width/height (CTkFrame chặn)
        self.body = tk.Frame(self, bg=NEU_BG, bd=0, highlightthickness=0)
        self.bind("<Configure>", self._on_resize)

    def _on_resize(self, e):
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(50, lambda w=e.width, h=e.height: self._render(w, h))

    def _render(self, w, h):
        self._img = make_neu(w, h, self._radius, glow=self._glow)
        self._bg.configure(image=self._img)
        i = self._inset
        self.body.place(x=i, y=i, width=w - 2 * i, height=h - 2 * i)


class NeuButton(tk.Frame):
    """Nút neumorphic kích thước cố định: nhấn → lõm (micro-interaction)."""

    def __init__(self, master, text, command, accent=TXT, w=112, h=44, radius=15):
        w, h, radius = _s(w), _s(h), _s(radius)
        super().__init__(master, bg=NEU_BG, width=w, height=h, bd=0,
                         highlightthickness=0)
        self.pack_propagate(False); self.grid_propagate(False)
        self._cmd = command
        self._up = make_neu(w, h, radius, off=_s(5), blur=_s(7))
        self._dn = make_neu(w, h, radius, pressed=True, off=_s(5), blur=_s(7))
        self._bg = tk.Label(self, image=self._up, bd=0, bg=NEU_BG)
        self._bg.place(x=0, y=0, relwidth=1, relheight=1)
        self._txt = tk.Label(self, text=text, bg=NEU_BG, fg=accent,
                             font=(FONT, _s(12), "bold"))
        self._txt.place(relx=0.5, rely=0.5, anchor="center")
        for wdg in (self, self._bg, self._txt):
            wdg.configure(cursor="hand2")
            wdg.bind("<Button-1>", self._press)
            wdg.bind("<ButtonRelease-1>", self._release)

    def set_text(self, text, accent=None):
        self._txt.configure(text=text)
        if accent:
            self._txt.configure(fg=accent)

    def _press(self, _e):
        self._bg.configure(image=self._dn)
        self._txt.place_configure(rely=0.54)

    def _release(self, _e):
        self._bg.configure(image=self._up)
        self._txt.place_configure(rely=0.5)
        if self._cmd:
            self._cmd()

    def set_text(self, text, accent=None):
        self._txt.configure(text=text)


def make_glow(w, h, accent, radius=14, base=NEU_BG, filled=True, pressed=False):
    """Nút phẳng squircle + quầng sáng màu bên dưới + highlight trên (kiểu HMI OTL).
    filled=True → mặt đổ màu accent (hành động chính); False → mặt tối viền accent."""
    w, h = max(int(w), 12), max(int(h), 12)
    k = SSAA                                  # vẽ ở SSAA× rồi thu → viền + glow mượt
    W, H, R = w * k, h * k, radius * k
    pad = _s(12) * k
    rect = [pad, pad, max(pad + 1, W - pad), max(pad + 1, H - pad)]
    ar = _rgb(accent)
    res = Image.new("RGBA", (W, H), _rgb(base) + (255,))
    # quầng sáng: rounded rect màu accent lệch xuống, blur mạnh, alpha thấp
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    off = (_s(3) if not pressed else _s(1)) * k
    gd.rounded_rectangle([rect[0], rect[1] + off, rect[2], rect[3] + off + _s(3) * k],
                         radius=R, fill=ar + (150 if not pressed else 90,))
    res = Image.alpha_composite(res, glow.filter(ImageFilter.GaussianBlur(_s(7) * k)))
    # mặt nút
    face = ImageDraw.Draw(res)
    if filled:
        fc = tuple(int(c * (0.82 if pressed else 1.0)) for c in ar)
        face.rounded_rectangle(rect, radius=R, fill=fc + (255,))
        # highlight mảnh trên đỉnh (inset top light)
        face.line([rect[0] + R, rect[1] + k, rect[2] - R, rect[1] + k],
                  fill=(255, 255, 255, 90), width=k)
    else:
        face.rounded_rectangle(rect, radius=R, fill=_rgb(CARD_BG) + (255,),
                               outline=ar + (255,), width=_s(2) * k)
    res = res.convert("RGB").resize((w, h), Image.LANCZOS)
    return ImageTk.PhotoImage(res)


class GlowButton(tk.Frame):
    """Nút hành động phát sáng (Industrial Flat + glow). API như NeuButton."""

    def __init__(self, master, text, command, accent, w=150, h=52, radius=14,
                 filled=True):
        w, h, radius = _s(w), _s(h), _s(radius)
        super().__init__(master, bg=NEU_BG, width=w, height=h, bd=0,
                         highlightthickness=0)
        self.pack_propagate(False); self.grid_propagate(False)
        self._cmd = command
        self._filled = filled
        self._enabled = True
        self._up = make_glow(w, h, accent, radius, filled=filled)
        self._dn = make_glow(w, h, accent, radius, filled=filled, pressed=True)
        self._off = make_glow(w, h, "#39414e", radius, filled=filled)   # disabled mờ
        self._bg = tk.Label(self, image=self._up, bd=0, bg=NEU_BG)
        self._bg.place(x=0, y=0, relwidth=1, relheight=1)
        self._fg_on = "#0d1015" if filled else accent
        self._face_on = accent if filled else CARD_BG   # nền chữ khớp mặt nút
        self._txt = tk.Label(self, text=text, bg=self._face_on, fg=self._fg_on,
                             font=(FONT, _s(13), "bold"))
        self._txt.place(relx=0.5, rely=0.5, anchor="center")
        for wdg in (self, self._bg, self._txt):
            wdg.configure(cursor="hand2")
            wdg.bind("<Button-1>", self._press)
            wdg.bind("<ButtonRelease-1>", self._release)

    def set_text(self, text, accent=None):
        self._txt.configure(text=text)

    def set_enabled(self, on):
        """Bật/tắt nút: tắt → mặt mờ, chữ chìm, không nhận bấm (vd STOP khi chưa chạy)."""
        if on == self._enabled:
            return
        self._enabled = on
        if on:
            self._bg.configure(image=self._up)
            self._txt.configure(fg=self._fg_on, bg=self._face_on)
        else:
            self._bg.configure(image=self._off)
            face = "#39414e" if self._filled else CARD_BG
            self._txt.configure(fg=TXT_MUTE, bg=face)
        cur = "hand2" if on else "arrow"
        for wdg in (self, self._bg, self._txt):
            wdg.configure(cursor=cur)

    def _press(self, _e):
        if not self._enabled:
            return
        self._bg.configure(image=self._dn)
        self._txt.place_configure(rely=0.54)

    def _release(self, _e):
        if not self._enabled:
            return
        self._bg.configure(image=self._up)
        self._txt.place_configure(rely=0.5)
        if self._cmd:
            self._cmd()


class Gauge(tk.Canvas):
    """Đồng hồ vòng cung 270° cho cơ cấu (Gas/Air/Drum) — cảm giác núm xoay máy thật.
    Học từ OTL Roaster HMI standalone (25 svg + 9 circle dial)."""

    def __init__(self, master, label, color, size=98, unit="%", vmax=100,
                 command=None):
        size = _s(size)
        super().__init__(master, width=size, height=size, bg=CARD_BG,
                         highlightthickness=0, bd=0)
        self.size, self.color, self.label = size, color, label
        self.unit, self.vmax, self._val = unit, vmax, None
        self.command = command
        self.interactive = False
        self._last_y = 0
        self.bind("<Button-1>", self._grab)
        self.bind("<B1-Motion>", self._drag)
        self.set(0)

    def set_interactive(self, on):
        self.interactive = on
        self.configure(cursor="sb_v_double_arrow" if on else "")
        self._val = None; self.set(self._shown if hasattr(self, "_shown") else 0)

    def _grab(self, e):
        self._last_y = e.y

    def _drag(self, e):
        if not self.interactive:
            return
        v = max(0, min(self.vmax, (self._shown or 0) + (self._last_y - e.y) * 0.8))
        self._last_y = e.y
        self.set(v)
        if self.command:
            self.command(int(round(v)))

    def set(self, val):
        val = max(0, min(self.vmax, val))
        self._shown = val
        if val == self._val:
            return
        self._val = val
        # mọi kích thước suy từ s (đã phóng) → tự co giãn theo màn
        s = self.size
        self.delete("all")
        # cung vẽ bằng PIL SSAA (AA mượt) — số/nhãn để canvas (font đã AA)
        self._arc = self._render_arc(val)
        self.create_image(0, 0, anchor="nw", image=self._arc)
        self.create_text(s / 2, s / 2 - s * 0.06, text=f"{int(round(val))}",
                         fill=TXT, font=(DISP, max(11, int(s * 0.27)), "bold"))
        lbl = ("⇅ " + self.label) if self.interactive else self.label
        self.create_text(s / 2, s / 2 + s * 0.17, text=lbl,
                         fill=self.color if self.interactive else TXT_DIM,
                         font=(FONT, max(7, int(s * 0.10)), "bold"))

    def _render_arc(self, val):
        """Ảnh PIL của rãnh + cung giá trị (270°, hở dưới), khử răng cưa SSAA."""
        s, k = self.size, SSAA
        S = s * k
        pad = int(s * 0.12) * k
        aw = max(4, int(s * 0.09)) * k
        box = [pad, pad, S - pad, S - pad]
        im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        track = (0x5a, 0x66, 0x75) if self.interactive else (0x45, 0x4c, 0x57)
        # 3 o'clock=0°, quay CLOCKWISE; cung từ 135° (dưới-trái) quét 270°
        d.arc(box, 135, 135 + 270, fill=track + (255,), width=aw)
        p = val / self.vmax
        if p > 0:
            d.arc(box, 135, 135 + 270 * p, fill=_rgb(self.color) + (255,), width=aw)
        return ImageTk.PhotoImage(im.resize((s, s), Image.LANCZOS))


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        # Phóng toàn UI theo phân giải màn (2K/4K nét & đủ lớn). CTk lo font/widget,
        # widget PIL (nút/gauge) đọc UI_SCALE. Geometry logic giữ nguyên, CTk scale.
        global UI_SCALE
        UI_SCALE = _pick_ui_scale(self.winfo_screenwidth())
        ctk.set_widget_scaling(UI_SCALE)
        ctk.set_window_scaling(UI_SCALE)
        self.title("OTL Roast Lab")
        self.geometry("1280x938")
        self.minsize(1120, 880)
        self.configure(fg_color=NEU_BG)
        self.attributes("-alpha", 0.0)   # mờ hẳn để fade-in mượt lúc mở
        try:
            self.iconbitmap(ICON)
        except Exception:
            pass

        self.engine = SimEngine(CalibConfig(), ThermalConfig())
        self.modbus = ModbusSlave(self.engine)
        self.btlink = BTModuleLink()
        self.speed = tk.StringVar(value="x2")
        self.compares = []   # profile so sánh vẽ chồng (tối đa 3)

        self._build_header()
        self._build_body()
        self._build_footer()

        # Giá trị hiển thị được "kéo mượt" về giá trị máy (animator 60fps)
        self._d_bt = self.engine.model.bt
        self._d_et = self.engine.model.et
        self._d_ror = 0.0

        threading.Thread(target=self._sim_loop, daemon=True).start()
        self.after(300, self._auto_connect_module)   # tự nối module CP210x lúc mở
        self._refresh_ui()
        self._animate()                              # 60fps: ease số + gauge
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(30, lambda: self._fade(0.0, 1.0, 240))   # fade-in sau khi vẽ xong

    @staticmethod
    def _flat_card(parent, **kw):
        """Thẻ PHẲNG squircle viền 1px (dùng cho SỐ LIỆU — điểm 10: thông tin phẳng)."""
        return ctk.CTkFrame(parent, fg_color=CARD_BG, border_width=1,
                            border_color=BORDER, corner_radius=16, **kw)

    def _dot(self, parent, text):
        """Đèn trạng thái ● + nhãn. Trả về (label_đèn) để đổi màu."""
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(side="left", padx=(0, 18))
        d = ctk.CTkLabel(f, text="●", font=(FONT, 14), text_color="#5a606b")
        d.pack(side="left", padx=(0, 5))
        ctk.CTkLabel(f, text=text, font=(FONT, 12), text_color=TXT_DIM).pack(side="left")
        return d

    # ── Header: thanh trạng thái tổng thể + kết nối + nút cấu hình ────────────
    def _build_header(self):
        bar = ctk.CTkFrame(self, fg_color=NEU_BG, height=54)
        bar.pack(fill="x", padx=28, pady=(18, 0))
        bar.pack_propagate(False)

        ctk.CTkLabel(bar, text="OTL", text_color=AMBER,
                     font=(FONT, 21, "bold")).pack(side="left")
        ctk.CTkLabel(bar, text="Roast Lab", text_color=TXT,
                     font=(FONT, 21, "bold")).pack(side="left", padx=(9, 20))

        # Chip trạng thái tinh tế (chấm màu + chữ) — gắn cạnh logo
        chip = ctk.CTkFrame(bar, fg_color=CARD_BG, corner_radius=14,
                            border_width=1, border_color=BORDER)
        chip.pack(side="left", pady=11)
        self.state_dot = ctk.CTkLabel(chip, text="●", text_color=TXT_MUTE,
                                      font=(FONT, 11))
        self.state_dot.pack(side="left", padx=(13, 7), pady=5)
        self.lbl_state = ctk.CTkLabel(chip, text=_track("CHƯA NẠP PROFILE"),
                                      text_color=TXT_DIM, font=(FONT, 11, "bold"))
        self.lbl_state.pack(side="left", padx=(0, 15))

        # Nút cấu hình — ghost viền mảnh, góc phải
        GlowButton(bar, "⚙  Cấu hình", self._open_config, TXT_DIM, w=126, h=38,
                   filled=False).pack(side="right")

        # Đèn kết nối gọn (chi tiết mở trong Cấu hình)
        conn = ctk.CTkFrame(bar, fg_color="transparent")
        conn.pack(side="right", padx=22)
        self.dot_artisan = self._dot(conn, "Artisan")
        self.dot_module = self._dot(conn, "ET module")
        self.lbl_mod_bt = ctk.CTkLabel(conn, text="", font=(MONO, 13, "bold"),
                                       text_color=GREEN)
        self.lbl_mod_bt.pack(side="left")

        # Thanh cảnh báo — luôn hiện, mặc định "không có cảnh báo"
        self.lbl_alarm = ctk.CTkLabel(self, text="✓  Không có cảnh báo",
                                      text_color=GREEN, font=(FONT, 12, "bold"),
                                      fg_color=CARD_BG, corner_radius=10, height=28,
                                      anchor="w")
        self.lbl_alarm.pack(fill="x", padx=28, pady=(10, 0))

        # Widget kết nối tạo trong dialog Cấu hình — giữ chỗ tên cổng CP210x
        self._auto_port = find_cp210x_port()

    # ── Body: đồ thị + panel số liệu phân cấp ────────────────────────────────
    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color=NEU_BG)
        body.pack(fill="both", expand=True, padx=24, pady=(12, 0))

        # Card đồ thị (phẳng, viền mảnh — điểm 10)
        chart = self._flat_card(body)
        chart.pack(side="left", fill="both", expand=True, padx=(0, 16))
        self.fig = Figure(figsize=(7, 5), dpi=int(100 * UI_SCALE), facecolor=CARD_BG)
        gs = self.fig.add_gridspec(2, 1, height_ratios=[4, 1], hspace=0.16)
        self.ax = self.fig.add_subplot(gs[0])
        self.ax2 = self.ax.twinx()
        self.ax_g = self.fig.add_subplot(gs[1], sharex=self.ax)
        self.canvas = FigureCanvasTkAgg(self.fig, master=chart)
        self.canvas.get_tk_widget().configure(bg=CARD_BG, highlightthickness=0)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
        self._style_axes()

        right = ctk.CTkFrame(body, fg_color=NEU_BG, width=336)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)
        self._build_metrics(right)

    @staticmethod
    def _caplabel(parent, text, **pk):
        """Nhãn hoa giãn cách (letter-spacing) — kiểu thiết bị đo chính xác."""
        w = ctk.CTkLabel(parent, text=_track(text, " "), text_color=TXT_DIM,
                         font=(FONT, 10, "bold"))
        w.pack(**pk)
        return w

    def _metric_row(self, parent, name, label, color, big=False):
        """1 dòng số liệu: nhãn trái + số phải (mono tabular)."""
        row = ctk.CTkFrame(parent, fg_color=CARD_BG)
        row.pack(fill="x", pady=3 if big else 2)
        ctk.CTkLabel(row, text=label, text_color=TXT_DIM, anchor="w",
                     font=(FONT, 12 if big else 11)).pack(side="left")
        v = ctk.CTkLabel(row, text="—", text_color=color, anchor="e",
                         font=(MONO, 20 if big else 14, "bold"))
        v.pack(side="right")
        self.metrics[name] = v

    def _build_metrics(self, parent):
        """Khối đo executive: BT hero → ET/Time → Output → State → Mốc rang."""
        self.metrics = {}
        self.miles = {}

        # ── BT HERO — số tabular champagne, đơn vị mờ, RoR + mũi tên xu hướng ──
        hero = self._flat_card(parent)
        hero.pack(fill="x", pady=(0, 9))
        pad = ctk.CTkFrame(hero, fg_color=CARD_BG); pad.pack(fill="x", padx=22, pady=(13, 12))
        self._caplabel(pad, "BEAN TEMP", anchor="w")
        vr = ctk.CTkFrame(pad, fg_color=CARD_BG); vr.pack(anchor="w", fill="x", pady=(3, 0))
        self.metrics["BT"] = ctk.CTkLabel(vr, text="—", text_color=AMBER,
                                          font=(MONO, 52, "bold"))
        self.metrics["BT"].pack(side="left")
        ctk.CTkLabel(vr, text="°C", text_color=TXT_MUTE,
                     font=(FONT, 15)).pack(side="left", padx=(9, 0), pady=(20, 0))
        rr = ctk.CTkFrame(pad, fg_color=CARD_BG); rr.pack(anchor="w", fill="x", pady=(8, 0))
        self._caplabel(rr, "RoR", side="left")
        self.metrics["RoR arrow"] = ctk.CTkLabel(rr, text="", text_color=INDIGO,
                                                 font=(FONT, 14, "bold"))
        self.metrics["RoR arrow"].pack(side="left", padx=(12, 3))
        self.metrics["RoR BT"] = ctk.CTkLabel(rr, text="—", text_color=INDIGO,
                                              font=(MONO, 19, "bold"))
        self.metrics["RoR BT"].pack(side="left")
        ctk.CTkLabel(rr, text="°C/ph", text_color=TXT_MUTE,
                     font=(FONT, 11)).pack(side="left", padx=(6, 0), pady=(4, 0))

        # ── ET + THỜI GIAN — 2 cột, hairline dọc phân tách ──
        et = self._flat_card(parent); et.pack(fill="x", pady=(0, 9))
        cols = ctk.CTkFrame(et, fg_color=CARD_BG); cols.pack(fill="x", padx=22, pady=13)
        cols.columnconfigure(0, weight=1); cols.columnconfigure(2, weight=1)
        for ci, (name, label, color) in [(0, ("ET", "EXHAUST · ET", CYAN)),
                                         (2, ("Thời gian", "THỜI GIAN", TXT))]:
            col = ctk.CTkFrame(cols, fg_color=CARD_BG)
            col.grid(row=0, column=ci, sticky="w")
            self._caplabel(col, label, anchor="w")
            self.metrics[name] = ctk.CTkLabel(col, text="—", text_color=color,
                                              font=(MONO, 30, "bold"))
            self.metrics[name].pack(anchor="w")
        ctk.CTkFrame(cols, fg_color=HAIR2, width=1, height=1).grid(
            row=0, column=1, sticky="ns")

        # ── OUTPUT — 3 ring mảnh (đã SSAA), nhấn champagne cho AUTO/MANUAL ──
        out = self._flat_card(parent); out.pack(fill="x", pady=(0, 9))
        head = ctk.CTkFrame(out, fg_color=CARD_BG)
        head.pack(fill="x", padx=22, pady=(13, 0))
        self._caplabel(head, "OUTPUT", side="left")
        self.mode = ctk.CTkSegmentedButton(
            head, values=["AUTO", "MANUAL"], command=self._set_mode,
            fg_color=NEU_DARK, selected_color=AMBER, selected_hover_color=AMBER,
            text_color=TXT_DIM, unselected_color=NEU_DARK,
            font=(FONT, 11, "bold"), height=26)
        self.mode.set("AUTO")
        self.mode.pack(side="right")
        op = ctk.CTkFrame(out, fg_color=CARD_BG); op.pack(padx=10, pady=(10, 4))
        self.gauges = {}
        setters = {"Gas (calib)": "man_gas", "Air": "man_air", "Drum": "man_drum"}
        for name, label, color in [("Gas (calib)", "GAS", ORANGE),
                                   ("Air", "AIR", BLUE), ("Drum", "DRUM", TEAL)]:
            attr = setters[name]
            g = Gauge(op, label, color, size=90,
                      command=lambda v, a=attr: setattr(self.engine, a, v))
            g.pack(side="left", padx=3)
            self.gauges[name] = g
        det = ctk.CTkFrame(out, fg_color=CARD_BG); det.pack(fill="x", padx=22, pady=(2, 14))
        ctk.CTkFrame(det, height=1, fg_color=HAIR2).pack(fill="x", pady=(0, 8))
        self._metric_row(det, "Gas (FF)", "Gas phản hồi (FF)", TXT_DIM)
        self._metric_row(det, "Vacuum SP", "Áp suất hút đặt", TXT_DIM)

        # ── MỐC RANG — CHARGE·TP·DRY END·FCs·DROP + thanh tỉ lệ 3 pha ──
        self._build_milestones(parent)

    def _build_milestones(self, parent):
        card = self._flat_card(parent); card.pack(fill="x", pady=(0, 0))
        mp = ctk.CTkFrame(card, fg_color=CARD_BG); mp.pack(fill="x", padx=22, pady=(14, 15))
        top = ctk.CTkFrame(mp, fg_color=CARD_BG); top.pack(fill="x")
        self._caplabel(top, "MỐC RANG", side="left")
        self.metrics["Pha"] = ctk.CTkLabel(top, text="—", text_color=AMBER,
                                            font=(FONT, 11, "bold"))
        self.metrics["Pha"].pack(side="right")
        ctk.CTkFrame(mp, fg_color=HAIR2, height=1).pack(fill="x", pady=(8, 6))
        for key, label in [("CHARGE", "CHARGE"), ("TP", "TP"), ("DE", "DRY END"),
                           ("FCS", "FCs"), ("DROP", "DROP")]:
            row = ctk.CTkFrame(mp, fg_color=CARD_BG); row.pack(fill="x", pady=1)
            lb = ctk.CTkLabel(row, text=label, text_color=TXT_MUTE, anchor="w",
                              width=70, font=(FONT, 11, "bold"))
            lb.pack(side="left")
            v = ctk.CTkLabel(row, text="—", text_color=TXT_MUTE, anchor="e",
                             font=(MONO, 12))
            v.pack(side="right")
            self.miles[key] = (lb, v)
        # thanh tỉ lệ 3 pha (Drying / Maillard / Development)
        self.phasebar = tk.Canvas(mp, height=_s(6), bg=CARD_BG, highlightthickness=0, bd=0)
        self.phasebar.pack(fill="x", pady=(10, 2))
        self.phaselbl = ctk.CTkLabel(mp, text="", text_color=TXT_MUTE, anchor="w",
                                     font=(FONT, 9))
        self.phaselbl.pack(fill="x")

    def _open_config(self):
        """Dialog Cấu hình neumorphic (calib + model nhiệt)."""
        if getattr(self, "_cfg_win", None) and self._cfg_win.winfo_exists():
            self._cfg_win.lift(); return
        win = ctk.CTkToplevel(self)
        self._cfg_win = win
        win.title("Cấu hình")
        win.geometry("440x680")
        win.configure(fg_color=NEU_BG)
        win.transient(self)
        card = NeuCard(win, radius=20, inset=18)
        card.pack(fill="both", expand=True, padx=14, pady=14)
        sc = ctk.CTkScrollableFrame(card.body, fg_color=NEU_BG)
        sc.pack(fill="both", expand=True)
        self.cfg_entries = {}

        def section(title):
            ctk.CTkLabel(sc, text=title, font=(FONT, 13, "bold"), text_color=TXT,
                         anchor="w").pack(fill="x", pady=(10, 2))

        def row(key, label, value):
            f = ctk.CTkFrame(sc, fg_color=NEU_BG)
            f.pack(fill="x", pady=2)
            ctk.CTkLabel(f, text=label, anchor="w", width=180,
                         text_color=TXT_DIM, font=(FONT, 11)).pack(side="left")
            e = ctk.CTkEntry(f, width=76, fg_color=NEU_DARK, border_width=0)
            e.insert(0, str(value)); e.pack(side="right")
            self.cfg_entries[key] = e

        # ── Kết nối (gom khỏi màn chính — điểm 8) ────────────────────────────
        section("Kết nối — Modbus slave (Artisan)")
        rm = ctk.CTkFrame(sc, fg_color=NEU_BG); rm.pack(fill="x", pady=2)
        self.cb_port = ctk.CTkComboBox(rm, width=118, values=self._ports(),
                                       fg_color=NEU_DARK, button_color=NEU_DARK,
                                       border_width=0)
        self.cb_port.pack(side="left")
        NeuButton(rm, "↻", self._refresh_ports, w=32, h=28, radius=8,
                  accent=TXT).pack(side="left", padx=4)
        self.ent_id = ctk.CTkEntry(rm, width=36, fg_color=NEU_DARK, border_width=0)
        self.ent_id.insert(0, "1"); self.ent_id.pack(side="left")
        self.cb_baud = ctk.CTkComboBox(rm, width=76, values=["9600", "19200",
                                       "38400", "115200"], fg_color=NEU_DARK,
                                       button_color=NEU_DARK, border_width=0)
        self.cb_baud.set("9600"); self.cb_baud.pack(side="left", padx=4)
        rsw = ctk.CTkFrame(sc, fg_color=NEU_BG); rsw.pack(fill="x", pady=4)
        self.sw_modbus = ctk.CTkSwitch(rsw, text="Bật slave", progress_color=GREEN,
                                       command=self._toggle_modbus)
        self.sw_modbus.pack(side="left")
        if self.modbus.running:
            self.sw_modbus.select()
        self.sw_pc = ctk.CTkSwitch(rsw, text="PC control", progress_color=ORANGE,
                                   command=self._toggle_pc)
        self.sw_pc.pack(side="left", padx=14)
        if self.engine.pc_control:
            self.sw_pc.select()

        section("Kết nối — Module ET (CP210x)")
        rmo = ctk.CTkFrame(sc, fg_color=NEU_BG); rmo.pack(fill="x", pady=2)
        self.cb_mod_port = ctk.CTkComboBox(rmo, width=120, values=self._ports(),
                                           fg_color=NEU_DARK, button_color=NEU_DARK,
                                           border_width=0)
        if self._auto_port:
            self.cb_mod_port.set(self._auto_port)
        self.cb_mod_port.pack(side="left")
        self.sw_module = ctk.CTkSwitch(rmo, text="Nối", progress_color=GREEN,
                                       command=self._toggle_module)
        self.sw_module.pack(side="left", padx=10)
        if self.btlink.connected:
            self.sw_module.select()

        c, t = self.engine.calib_cfg, self.engine.thermal_cfg
        section("Calib gas (Program.h)")
        row("cl_range_bt", "Deadband trước FCS (0.1°C)", c.cl_range_bt)
        row("cl_range_fcs", "Deadband từ FCS (0.1°C)", c.cl_range_fcs)
        row("step_pct", "Bước gas mỗi bậc (%)", c.step_pct)
        row("eval_sec", "Chu kỳ tính bậc (giây)", c.eval_sec)
        row("tp_calib", "Cap bù pha Tp (%)", c.tp_calib)
        row("de_calib", "Cap bù pha De (%)", c.de_calib)
        row("fcs_calib", "Cap bù pha Fcs (%)", c.fcs_calib)
        section("Model nhiệt")
        # Preset theo máy — chọn là điền sẵn 5 số, khỏi gõ tay
        pf = ctk.CTkFrame(sc, fg_color=NEU_BG); pf.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(pf, text="Preset máy", anchor="w", width=180,
                     text_color=INDIGO, font=(FONT, 11, "bold")).pack(side="left")
        ctk.CTkOptionMenu(pf, values=list(THERMAL_PRESETS.keys()),
                          command=self._apply_preset, width=190, fg_color=NEU_DARK,
                          button_color=NEU_DARK, font=(FONT, 11)).pack(side="right")
        row("gas_equilib", "Gas cân bằng (%)", t.gas_equilib)
        row("gas_sens", "Độ nhạy gas (°C/min/%)", t.gas_sens)
        row("heatloss_k", "Hệ số mất nhiệt", t.heatloss_k)
        row("gas_lag_s", "Lag gas (giây)", t.gas_lag_s)
        row("air_cool_k", "Hệ số mát do gió", t.air_cool_k)
        row("ambient", "Nhiệt môi trường (°C)", t.ambient)
        NeuButton(sc, "Áp dụng", self._apply_config, w=140, h=40,
                  accent=GREEN).pack(pady=14)

    def _apply_preset(self, name):
        """Điền 5 ô model nhiệt theo preset máy đã chọn (chưa áp — bấm Áp dụng)."""
        p = THERMAL_PRESETS.get(name)
        if not p:
            return
        for key, val in p.items():
            e = self.cfg_entries.get(key)
            if e is not None and e.winfo_exists():
                e.delete(0, "end"); e.insert(0, str(val))

    # ── Footer: nút điều khiển to, tách xa (chống nhấn nhầm) ──────────────────
    def _build_footer(self):
        bar = ctk.CTkFrame(self, fg_color=NEU_BG, height=80)
        bar.pack(fill="x", padx=24, pady=(12, 20))
        bar.pack_propagate(False)

        # Trái: nạp profile + xuất CSV + tên (nút phụ = viền, không đầy)
        left = ctk.CTkFrame(bar, fg_color="transparent")
        left.pack(side="left", fill="y")
        GlowButton(left, "📂  Nạp profile", self._load, BLUE, w=150, h=52,
                   filled=False).pack(side="left")
        GlowButton(left, "⭳  Xuất CSV", self._export, TXT_DIM, w=128, h=52,
                   filled=False).pack(side="left", padx=10)
        self.btn_compare = GlowButton(left, "⇄  So sánh", self._compare, CYAN,
                                      w=128, h=52, filled=False)
        self.btn_compare.pack(side="left")
        self.lbl_file = ctk.CTkLabel(left, text="Profile: chưa chọn",
                                     text_color=TXT_DIM, font=(FONT, 13))
        self.lbl_file.pack(side="left", padx=14)

        # Phải: nhóm VẬN HÀNH — STOP tách hẳn sau hairline dọc (chống nhấn nhầm)
        right = ctk.CTkFrame(bar, fg_color="transparent")
        right.pack(side="right", fill="y")
        spd = self._flat_card(right); spd.pack(side="left", padx=(0, 14), pady=14)
        spd.configure(width=82, height=52)
        ctk.CTkOptionMenu(spd, variable=self.speed, width=64,
                          values=["x1", "x2", "x5", "x10", "x20"],
                          fg_color=NEU_DARK, button_color=NEU_DARK,
                          font=(FONT, 13)).pack(expand=True, padx=8)
        self.btn_charge = GlowButton(right, "▶  CHARGE", self._charge, GREEN,
                                     w=152, h=52, filled=True)
        self.btn_charge.pack(side="left", padx=(0, 12))
        self.btn_reset = GlowButton(right, "⟲  Reset", self._reset, TXT_DIM,
                                    w=112, h=52, filled=False)
        self.btn_reset.pack(side="left")
        # hairline dọc + khoảng thở rộng tách nhóm dừng khẩn
        ctk.CTkFrame(right, fg_color="transparent", width=24).pack(side="left")
        ctk.CTkFrame(right, fg_color=BORDER, width=1).pack(side="left", fill="y", pady=8)
        ctk.CTkFrame(right, fg_color="transparent", width=24).pack(side="left")
        self.btn_stop = GlowButton(right, "■  STOP", self._stop, RED, w=150, h=52,
                                   filled=True)
        self.btn_stop.pack(side="left")
        self.btn_stop.set_enabled(False)   # chưa chạy → STOP mờ

    # ── Cổng COM ─────────────────────────────────────────────────────────────
    def _ports(self):
        return [p.device for p in serial.tools.list_ports.comports()] or ["(không có)"]

    def _refresh_ports(self):
        for cb in ("cb_port", "cb_mod_port"):
            w = getattr(self, cb, None)
            if w is not None and w.winfo_exists():
                w.configure(values=self._ports())

    def _toggle_pc(self):
        self.engine.pc_control = bool(self.sw_pc.get())
        if self.engine.pc_control and not self.modbus.running:
            messagebox.showwarning("PC control",
                                   "Bật Modbus slave trước để Artisan ghi lệnh vào")

    def _set_mode(self, mode):
        """AUTO = profile+calib điều khiển; MANUAL = xoay đồng hồ điều khiển tay."""
        manual = (mode == "MANUAL")
        eng = self.engine
        if manual:
            # nhận giá trị hiện tại làm điểm khởi đầu (không nhảy)
            eng.man_gas, eng.man_air, eng.man_drum = eng.fw.gas, eng.fw.air, eng.fw.drum
        eng.manual = manual
        for g in self.gauges.values():
            g.set_interactive(manual)

    def _auto_connect_module(self):
        """Tự nối module BT nếu thấy cổng CP210x lúc mở app (im lặng nếu bận)."""
        port = find_cp210x_port()
        if not port or self.btlink.connected:
            return
        try:
            self.btlink.connect(port)   # đèn ET module trên header sẽ xanh
        except serial.SerialException:
            pass   # cổng bận (app khác giữ) — bật tay trong Cấu hình sau

    def _toggle_module(self):
        if self.sw_module.get():
            port = self.cb_mod_port.get()
            if not port or port.startswith("("):
                messagebox.showwarning("Module BT", "Chưa chọn cổng COM")
                self.sw_module.deselect(); return
            try:
                self.btlink.connect(port)
            except serial.SerialException as e:
                messagebox.showerror("Module BT",
                                     f"Không mở được {port}:\n{e}\n\n"
                                     "Cổng đang bị app khác giữ? (BT Serial Tester, Serial Monitor…)")
                self.sw_module.deselect()
        else:
            self.btlink.disconnect()

    def _toggle_modbus(self):
        if self.sw_modbus.get():
            port = self.cb_port.get()
            if not port or port.startswith("("):
                messagebox.showwarning("Modbus", "Chưa chọn cổng COM")
                self.sw_modbus.deselect(); return
            try:
                self.modbus.start(port, int(self.cb_baud.get()), int(self.ent_id.get()))
            except (RuntimeError, ValueError) as e:
                messagebox.showerror("Modbus", str(e))
                self.sw_modbus.deselect()
        else:
            self.modbus.stop()

    # ── Lệnh ─────────────────────────────────────────────────────────────────
    def _load(self):
        path = filedialog.askopenfilename(
            title="Chọn profile CSV", filetypes=[("CSV", "*.csv"), ("Tất cả", "*.*")])
        if not path:
            return
        try:
            prof = parse_profile(path)
        except (ValueError, OSError) as e:
            messagebox.showerror("Lỗi đọc profile", str(e))
            return
        self.engine.load(prof)
        ev = "  ".join(f"{k}@{v//60:02d}:{v%60:02d}" for k, v in prof.events.items())
        self.lbl_file.configure(text=f"{prof.name}  ({prof.n}s)  {ev}", text_color=TXT)

    def _charge(self):
        if not self.engine.profile and not self.engine.manual and not self.engine.pc_control:
            messagebox.showwarning("Charge", "Hãy nạp profile, hoặc bật MANUAL/PC control")
            return
        self.engine.charge()

    # Màu đường so sánh (khác AMBER của BT sim/ghost chính)
    COMPARE_COLORS = ["#7f8cff", "#e0904e", "#4ec9a8"]

    def _compare(self):
        """Toggle: chưa có → nạp 1-3 CSV vẽ chồng; đang có → xoá."""
        if self.compares:
            self.compares = []
            self.btn_compare.set_text("⇄  So sánh", accent=CYAN)
            return
        paths = filedialog.askopenfilenames(
            title="Chọn 1-3 mẻ để so sánh (CSV)",
            filetypes=[("CSV", "*.csv"), ("Tất cả", "*.*")])
        if not paths:
            return
        loaded = []
        for p in paths[:3]:
            try:
                loaded.append(parse_profile(p))
            except (ValueError, OSError):
                pass
        if not loaded:
            messagebox.showerror("So sánh", "Không đọc được file nào")
            return
        self.compares = loaded
        self.btn_compare.set_text(f"✕  Xoá ({len(loaded)})", accent=RED)

    def _export(self):
        with self.engine.lock:
            hist = list(self.engine.hist)
            prof = self.engine.profile
        if len(hist) < 2:
            messagebox.showwarning("Xuất CSV", "Chưa có dữ liệu mẻ — hãy Charge và chạy đã")
            return
        csv = hist_to_csv(hist, prof)
        path = filedialog.asksaveasfilename(
            title="Lưu mẻ ảo (Roaster Scope CSV)", defaultextension=".csv",
            initialfile="roast_sim.csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(csv)
        except OSError as e:
            messagebox.showerror("Xuất CSV", str(e)); return
        messagebox.showinfo("Xuất CSV", f"Đã lưu {len(hist)}s mẻ ảo:\n{path}")

    def _confirm(self, title, msg, on_yes, yes_text="Xác nhận", danger=False):
        """Modal xác nhận bán trong suốt (glass nhẹ) — chống thao tác nhầm quan trọng."""
        win = ctk.CTkToplevel(self)
        win.overrideredirect(True)
        win.configure(fg_color=NEU_BG)
        try:
            win.attributes("-alpha", 0.97)   # hint glass (điểm brief: glass cho popup)
        except tk.TclError:
            pass
        w, h = 410, 196
        self.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - w) // 2
        y = self.winfo_rooty() + (self.winfo_height() - h) // 3
        win.geometry(f"{w}x{h}+{x}+{y}")
        win.transient(self)
        win.grab_set()
        card = NeuCard(win, radius=22, inset=24)
        card.pack(fill="both", expand=True, padx=6, pady=6)
        b = card.body
        ctk.CTkLabel(b, text=title, text_color=RED if danger else AMBER,
                     font=(FONT, 17, "bold")).pack(anchor="w")
        ctk.CTkLabel(b, text=msg, text_color=TXT, font=(FONT, 12), justify="left",
                     wraplength=330).pack(anchor="w", pady=(6, 0))

        def close():
            win.grab_release(); win.destroy()

        def yes():
            close(); on_yes()

        rowf = ctk.CTkFrame(b, fg_color=NEU_BG); rowf.pack(side="bottom", fill="x")
        NeuButton(rowf, yes_text, yes, w=150, h=44,
                  accent=RED if danger else GREEN).pack(side="right")
        NeuButton(rowf, "Huỷ", close, w=96, h=44,
                  accent=TXT_DIM).pack(side="right", padx=10)

    def _stop(self):
        if self.engine.running:
            self._confirm("DỪNG / DROP MẺ?",
                          "Máy đang chạy. Dừng và drop mẻ ngay bây giờ?",
                          self._do_stop, yes_text="■  DỪNG", danger=True)
        else:
            self._do_stop()

    def _do_stop(self):
        self.engine.running = False

    def _reset(self):
        if self.engine.running:
            self._confirm("RESET KHI ĐANG RANG?",
                          "Đang rang. Reset sẽ xoá đồ thị và đưa mẻ về đầu.",
                          self._do_reset, yes_text="⟲  Reset", danger=True)
        else:
            self._do_reset()

    def _do_reset(self):
        with self.engine.lock:
            self.engine.reset()

    def _apply_config(self):
        try:
            c, t = self.engine.calib_cfg, self.engine.thermal_cfg
            for key, e in self.cfg_entries.items():
                val = float(e.get()) if key in ("gas_equilib", "gas_sens", "heatloss_k",
                                                 "gas_lag_s", "air_cool_k", "ambient") else int(e.get())
                if hasattr(c, key):
                    setattr(c, key, val)
                elif hasattr(t, key):
                    setattr(t, key, val)
        except ValueError:
            messagebox.showerror("Config", "Giá trị không hợp lệ")

    # ── Vòng mô phỏng ────────────────────────────────────────────────────────
    def _sim_loop(self):
        while True:
            self.engine.tick()
            # Lái module BT vật lý bám BT model (chỉ khi đang rang)
            if self.btlink.connected and self.engine.running:
                self.btlink.track(self.engine.model.bt)
            try:
                spd = float(self.speed.get().lstrip("x"))
            except ValueError:
                spd = 1.0
            time.sleep(max(0.02, 1.0 / spd))

    def _refresh_ui(self):
        try:
            self._refresh_ui_body()
        except tk.TclError:
            return   # cửa sổ đã đóng — dừng chuỗi after()

    # ── Animator 60fps: kéo số + gauge trôi mượt về giá trị máy ───────────────
    @staticmethod
    def _ease(cur, tgt, a=0.22, snap=0.05):
        """Kéo cur về tgt; snap thẳng khi đã sát để ngừng vẽ lại vô ích lúc đứng yên."""
        return tgt if abs(tgt - cur) < snap else cur + (tgt - cur) * a

    def _animate(self):
        try:
            eng = self.engine
            m = eng.model
            self._d_bt = self._ease(self._d_bt, m.bt)
            self._d_et = self._ease(self._d_et, m.et)
            self._d_ror = self._ease(self._d_ror, m.ror_bt)
            self.metrics["BT"].configure(text=f"{self._d_bt:.1f}")
            self.metrics["ET"].configure(text=f"{self._d_et:.1f}")
            self.metrics["RoR BT"].configure(text=f"{self._d_ror:+.1f}")
            arr = "▲" if self._d_ror > 0.3 else ("▼" if self._d_ror < -0.3 else "▬")
            self.metrics["RoR arrow"].configure(text=arr)
            # 3 đồng hồ cơ cấu — ở MANUAL do người dùng xoay, không đè
            if not eng.manual:
                for name, tgt in (("Gas (calib)", eng.fw.gas),
                                  ("Air", eng.fw.air), ("Drum", eng.fw.drum)):
                    g = self.gauges[name]
                    g.set(self._ease(g._shown or 0, tgt, snap=0.2))
        except tk.TclError:
            return
        self.after(16, self._animate)        # ~60Hz

    # ── Fade alpha (ease-out cubic) dùng cho mở/đóng ──────────────────────────
    def _fade(self, start, end, dur_ms, done=None):
        steps = max(1, dur_ms // 16)

        def step(i):
            k = i / steps
            e = 1 - (1 - k) ** 3             # ease-out
            try:
                self.attributes("-alpha", start + (end - start) * e)
            except tk.TclError:
                return
            if i < steps:
                self.after(16, lambda: step(i + 1))
            elif done:
                done()

        step(0)

    def _on_close(self):
        """Fade-out mượt rồi dọn tài nguyên và đóng."""
        self._fade(1.0, 0.0, 160,
                   done=lambda: (self.modbus.stop(),
                                 self.btlink.disconnect(), self.destroy()))

    def _machine_state(self):
        """Trạng thái tổng thể của máy — 1 phát nhìn biết đang làm gì (điểm 5)."""
        eng = self.engine
        if eng.pc_control:
            return ("PC CONTROL", ORANGE) if eng.running else ("PC · CHỜ CHARGE", ORANGE)
        if eng.manual:
            return ("MANUAL · ĐANG CHẠY", ORANGE) if eng.running else ("MANUAL · CHỜ CHARGE", ORANGE)
        if not eng.profile:
            return "CHƯA NẠP PROFILE", TXT_DIM
        if eng.running:
            ph = eng.phase()
            if "DRY" in ph and "TP" in ph:
                return "TURNING POINT", CYAN
            if ph.startswith("DEV"):
                return "DEVELOPMENT", ORANGE
            if ph == "MAILLARD":
                return "MAILLARD", ORANGE
            return "ROASTING", GREEN
        if eng.roast_t >= eng.profile.n:
            return "DROP ✓", CYAN
        return "READY", GREEN

    def _refresh_ui_body(self):
        eng = self.engine
        fw = eng.fw
        t = eng.roast_t
        # BT/ET/RoR + gauge do animator 60fps kéo mượt (xem _animate)
        ff = f"{eng.gas_ff} %" + (f"  ({fw.gas-eng.gas_ff:+d} bù)" if fw.num_inc_gas else "")
        self.metrics["Gas (FF)"].configure(text=ff)
        self.metrics["Vacuum SP"].configure(text=f"{fw.vac_sp} Pa")
        self.metrics["Thời gian"].configure(text=f"{t//60:02d}:{t%60:02d}")
        self.metrics["Pha"].configure(text=eng.phase())

        # Trạng thái máy tổng thể (chip header: chấm màu + chữ giãn cách)
        st, col = self._machine_state()
        self.lbl_state.configure(text=_track(st), text_color=col)
        self.state_dot.configure(text_color=col)

        # Bật/tắt nút theo trạng thái: đang chạy → chỉ STOP; dừng → CHARGE/Reset
        run = eng.running
        self.btn_stop.set_enabled(run)
        self.btn_charge.set_enabled(not run)
        self.btn_reset.set_enabled(not run)

        # Đèn kết nối + BT module
        self.dot_artisan.configure(text_color=GREEN if self.modbus.running else "#5a606b")
        if self.btlink.connected:
            self.dot_module.configure(text_color=GREEN)
            v = self.btlink.echo_bt if self.btlink.echo_bt is not None else self.btlink.mod_bt
            self.lbl_mod_bt.configure(text="" if v is None else f"{v:.0f}°C")
        else:
            self.dot_module.configure(text_color="#5a606b")
            self.lbl_mod_bt.configure(text="")

        # Mốc rang + thanh 3 pha
        self._update_miles()
        # Thanh cảnh báo (điểm 9)
        self._update_alarm()
        self._draw()
        self.after(300, self._refresh_ui)

    def _update_miles(self):
        """Điền thời gian + BT cho mỗi mốc; mốc chưa đạt/không có → mờ. Vẽ thanh 3 pha."""
        eng = self.engine
        prof = eng.profile
        if not prof:
            for lb, v in self.miles.values():
                lb.configure(text_color=TXT_MUTE)
                v.configure(text="—", text_color=TXT_MUTE)
            self.phasebar.delete("all")
            self.phaselbl.configure(text="")
            return
        ev = prof.events
        for key, (lb, v) in self.miles.items():
            i = ev.get(key)
            if i is None or (i == 0 and key != "CHARGE"):
                v.configure(text="—", text_color=TXT_MUTE)
                lb.configure(text_color=TXT_MUTE)
                continue
            bi = min(i, prof.n - 1)             # DROP có thể = prof.n → kẹp lại
            txt = f"{self._fmt_mmss(i)}   {prof.bt[bi] / 10:.0f}°"
            reached = eng.roast_t >= i
            v.configure(text=txt, text_color=TXT if reached else TXT_MUTE)
            lb.configure(text_color=TXT_DIM if reached else TXT_MUTE)
        self._draw_phasebar(ev)

    # Pha cho thanh tỉ lệ (nhãn, mốc đầu, mốc cuối, màu trầm)
    _PHASE_SEG = [("Dry", "CHARGE", "DE", "#5f8f78"),
                  ("Maillard", "DE", "FCS", ORANGE),
                  ("Dev", "FCS", "DROP", "#9c7048")]

    def _draw_phasebar(self, ev):
        c = self.phasebar
        c.delete("all")
        c.update_idletasks()
        W = c.winfo_width() or _s(290)
        H = int(c["height"])
        segs = []
        for name, a, b, col in self._PHASE_SEG:
            i0, i1 = ev.get(a), ev.get(b)
            if i0 is None or i1 is None or i1 <= i0:
                continue
            segs.append((name, i1 - i0, col))
        total = sum(d for _, d, _ in segs)
        if not total:
            self.phaselbl.configure(text="")
            return
        gap = _s(2)
        x = 0
        parts = []
        for name, dur, col in segs:
            w = (W - gap * (len(segs) - 1)) * dur / total
            c.create_rectangle(x, 0, x + w, H, fill=col, width=0)
            x += w + gap
            parts.append(f"{name} {dur/total*100:.0f}%")
        self.phaselbl.configure(text="   ·   ".join(parts))

    def _update_alarm(self):
        """Cảnh báo rõ ràng: nói lỗi gì + cách xử lý. Mặc định: không có."""
        eng = self.engine
        if eng.pc_control and not self.modbus.running:
            self.lbl_alarm.configure(
                text="⚠  PC CONTROL bật nhưng chưa bật Modbus slave  ·  vào Cấu hình bật slave",
                text_color=RED, fg_color="#3a2020")
        elif eng.running and abs(eng.model.et - eng.model.bt) > 90:
            self.lbl_alarm.configure(
                text=f"⚠  ET − BT = {eng.model.et-eng.model.bt:.0f}°C vượt ngưỡng  ·  kiểm tra model nhiệt / cảm biến",
                text_color=ORANGE, fg_color="#3a3120")
        else:
            self.lbl_alarm.configure(text="✓  Không có cảnh báo",
                                     text_color=GREEN, fg_color=CARD_BG)

    @staticmethod
    def _fmt_mmss(x, _pos=None):
        x = max(0, int(x))
        return f"{x//60:02d}:{x%60:02d}"

    def _style_axes(self):
        from matplotlib.ticker import FuncFormatter
        self.fig.patch.set_facecolor(CARD_BG)
        for a in (self.ax, self.ax_g):
            a.set_facecolor(SCREEN)              # khung tranh sâu hơn panel → nổi lên
            a.grid(True, color="#1b2027", lw=0.5)   # grid siêu mảnh
        self.ax.set_ylabel("°C", color=TXT_DIM, fontsize=8.5)
        self.ax2.set_ylabel("RoR °C/ph", color=TXT_MUTE, fontsize=8)   # trục phụ mờ
        self.ax2.yaxis.set_label_position("right")
        self.ax_g.set_ylabel("%", color=TXT_MUTE, fontsize=8)
        self.ax_g.set_xlabel("Thời gian rang", color=TXT_DIM, fontsize=8.5)
        self.ax_g.xaxis.set_major_formatter(FuncFormatter(self._fmt_mmss))
        self.ax.tick_params(labelbottom=False)   # trục thời gian chỉ hiện ở tầng dưới
        self.ax.tick_params(colors=TXT_DIM, labelsize=8)
        # trục phụ (RoR + %) làm MỜ để BT/ET nổi
        for a in (self.ax2, self.ax_g):
            a.tick_params(colors=TXT_MUTE, labelsize=7.5)
        for a in (self.ax, self.ax2, self.ax_g):
            for sp in a.spines.values():
                sp.set_color(HAIR2)
        # Dải MẶC ĐỊNH khi chưa có dữ liệu (điểm 7: tránh trục 0.0–1.0 như lỗi)
        self.ax.set_ylim(0, 300)
        self.ax2.set_ylim(-10, 30)
        self.ax_g.set_ylim(0, 105)
        self.ax.set_xlim(0, 60)

    # Pha (nhãn, mốc đầu, mốc cuối, màu) — Dev dùng nâu (đỏ chỉ cho alarm — điểm 2)
    PHASES = [("Dry", "CHARGE", "DE", "#5f8f78"),
              ("Maillard", "DE", "FCS", ORANGE),
              ("Dev", "FCS", "DROP", "#9c7048")]

    def _draw(self):
        with self.engine.lock:
            hist = list(self.engine.hist)
            prof = self.engine.profile
        self.ax.clear(); self.ax2.clear(); self.ax_g.clear()
        self._style_axes()

        if prof:
            xs = range(prof.n)
            # Đường tham chiếu "ghost" trên nền tối: BT + RoR profile
            self.ax.plot(xs, [b / 10.0 for b in prof.bt], color="#484e57",
                         lw=1.3, ls="--", label="BT profile")
            self.ax2.plot(xs, prof.ror, color="#3a3f47", lw=0.9, ls="--")
            # Gas/Air FF nền mờ ở tầng dưới
            self.ax_g.plot(xs, prof.gas, color="#7a6540", lw=1.0, ls="--")
            self.ax_g.plot(xs, prof.air, color="#3f6b52", lw=1.0, ls="--")

            # Dải pha + thời lượng (chỉ khi có đủ 2 mốc, mốc >0)
            ev = prof.events
            total = ev.get("DROP", prof.n - 1) or (prof.n - 1)
            for name, a, b, color in self.PHASES:
                i0, i1 = ev.get(a), ev.get(b)
                if i0 is None or i1 is None or i1 <= i0:
                    continue
                self.ax.axvspan(i0, i1, color=color, alpha=0.06, zorder=0)
                dur = i1 - i0
                self.ax.text((i0 + i1) / 2, 0.99, f"{name} · {self._fmt_mmss(dur)}"
                             f" · {dur/total*100:.0f}%",
                             transform=self.ax.get_xaxis_transform(),
                             ha="center", va="top", fontsize=7, color="white",
                             bbox=dict(boxstyle="round,pad=0.25", fc=color, ec="none"))

            # Hộp sự kiện [mm:ss] @ °C ngay trên đường BT (kiểu Cropster)
            for label, i in ev.items():
                if not (0 <= i < prof.n) or (i == 0 and label != "CHARGE"):
                    continue
                self.ax.axvline(i, color=HAIR2, lw=0.7, zorder=1)
                self.ax.annotate(f"{label}\n[{self._fmt_mmss(i)}] {prof.bt[i]/10:.0f}°",
                                 (i, prof.bt[i] / 10.0), textcoords="offset points",
                                 xytext=(0, 11), fontsize=6.5, color=TXT,
                                 ha="center", zorder=6,
                                 bbox=dict(boxstyle="round,pad=0.3",
                                           fc="#20242b", ec="#333a44", lw=0.6,
                                           alpha=0.96))

        # Mẻ so sánh vẽ chồng (Roast Compare) — BT + RoR mỗi mẻ 1 màu
        for k, cp in enumerate(self.compares):
            col = self.COMPARE_COLORS[k % len(self.COMPARE_COLORS)]
            xs = range(cp.n)
            self.ax.plot(xs, [b / 10.0 for b in cp.bt], color=col, lw=1.4,
                         alpha=0.9, label=f"↺ {cp.name}")
            self.ax2.plot(xs, cp.ror, color=col, lw=0.9, alpha=0.5, ls=":")

        if hist:
            t = [h[0] for h in hist]
            self.ax.plot(t, [h[1] for h in hist], color=AMBER, lw=1.9, label="BT")
            self.ax2.plot(t, [h[5] for h in hist], color=INDIGO, lw=1.1, label="RoR")
            self.ax_g.plot(t, [h[3] for h in hist], color=ORANGE, lw=1.4,
                           drawstyle="steps-post", label="Gas")
            self.ax_g.plot(t, [h[4] for h in hist], color=BLUE, lw=1.1,
                           drawstyle="steps-post", label="Air")
            for a in (self.ax, self.ax_g):
                a.axvline(t[-1], color=AMBER, lw=0.8, alpha=0.5)

        self.ax_g.set_ylim(0, 105)
        self.ax2.set_ylim(-10, 30)   # kẹp hiển thị RoR như Artisan (đáy TP rất sâu)
        nmax = max([p.n for p in ([prof] if prof else []) + self.compares] or [0])
        if nmax:
            self.ax.set_xlim(-10, nmax + 10)
            bt_top = max([max(p.bt) for p in ([prof] if prof else []) + self.compares])
            self.ax.set_ylim(0, max(300, bt_top / 10 + 20))
        if prof or hist or self.compares:
            h1, l1 = self.ax.get_legend_handles_labels()
            h2, l2 = self.ax2.get_legend_handles_labels()
            leg = self.ax.legend(h1 + h2, l1 + l2, loc="lower right", fontsize=7,
                                 facecolor=SCREEN, edgecolor="#3a3d44",
                                 labelcolor=TXT)   # lower right: né hộp CHARGE
            leg.get_frame().set_alpha(0.9)
            if hist:
                lg = self.ax_g.legend(loc="upper right", fontsize=6.5, ncol=2,
                                      facecolor=SCREEN, edgecolor="#3a3d44",
                                      labelcolor=TXT)
                lg.get_frame().set_alpha(0.9)

        # Bảng tổng kết sau DROP (chỉ khi đã dừng + có profile) — QC kiểu RoastGuard
        if not self.engine.running and not self.engine.pc_control:
            s = roast_summary(hist, prof)
            if s:
                lines = [f"Thời lượng mẻ   {self._fmt_mmss(s['dur'])}",
                         f"Bám sau TP   TB {s['avg']:.1f}°  ·  đỉnh {s['max']:.1f}°"]
                if s["phases"]:
                    lines.append("   " + "   ".join(f"{n} {a:.1f}°"
                                                     for n, a in s["phases"]))
                lines.append(f"Ngoài ±{s['band']:.0f}°   {s['pct_out']:.0f}% thời gian")
                self.ax.text(0.985, 0.97, "TỔNG KẾT MẺ\n" + "\n".join(lines),
                             transform=self.ax.transAxes, ha="right", va="top",
                             fontsize=8, color=TXT, family="monospace",
                             bbox=dict(boxstyle="round,pad=0.5", fc="#1d1f24",
                                       ec=BLUE, lw=1.2, alpha=0.96), zorder=10)
        # Trạng thái trống — gợi ý nhẹ giữa "màn hình" thay vì trục rỗng trông lỗi
        if not (prof or hist or self.compares):
            self.ax.text(0.5, 0.5, "Nạp profile để bắt đầu",
                         transform=self.ax.transAxes, ha="center", va="center",
                         fontsize=13, color="#4a5260")

        self.fig.subplots_adjust(left=0.075, right=0.925, top=0.965, bottom=0.085)
        self.canvas.draw_idle()


def main():
    app = App()   # đóng cửa sổ → _on_close (fade-out + dọn tài nguyên)
    app.mainloop()


if __name__ == "__main__":
    main()
