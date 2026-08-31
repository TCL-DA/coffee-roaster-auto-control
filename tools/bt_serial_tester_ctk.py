"""
BT Serial Tester (Apple style) — công cụ test/điều khiển thiết bị BT qua Serial.

Giao diện viết lại bằng customtkinter theo phong cách macOS/iOS: card bo góc,
switch kiểu iOS, nút primary xanh, light/dark mode. Logic serial giữ nguyên,
tách riêng trong lớp SerialManager (đọc trên thread riêng, đẩy dữ liệu về UI
qua queue — tkinter không an toàn đa luồng).

Bộ lệnh thiết bị (mỗi ký tự đổi BT 0.1°C, thiết bị echo "BT:xxx.xx"):
    '1' +0.1   '2' +0.2   '5' +0.5   '9' +1.0
    'q' -0.1   'w' -0.2   'e' -0.5   'r' -1.0

Cài lib + build: xem comment cuối file.
"""

import os
import re
import queue
import threading
import time
import tkinter as tk
from tkinter import messagebox, filedialog

import serial
import serial.tools.list_ports

import customtkinter as ctk

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


# ════════════════════════════════════════════════════════════════════════════
#  HẰNG SỐ & BẢNG MÀU (kiểu Apple). Màu dạng (light, dark) để CTk tự đổi theme.
# ════════════════════════════════════════════════════════════════════════════
BG_WINDOW = ("#F5F5F7", "#1C1C1E")
CARD = ("#FFFFFF", "#2C2C2E")
TEXT_STRONG = ("#1D1D1F", "#F5F5F7")
TEXT_SUB = ("#86868B", "#98989D")
LOG_BG = ("#FAFAFA", "#1C1C1E")
BLUE = "#007AFF"
BLUE_HOVER = "#0051D5"
GREEN = "#34C759"
GREEN_HOVER = "#2EB14F"
RED = "#FF3B30"
RED_HOVER = "#E0322A"
PILL_OFF = ("#E5E5EA", "#3A3A3C")
GREY_BORDER = ("#C7C7CC", "#48484A")

FONT_FAMILY = "Segoe UI"        # fallback đẹp trên Windows (SF Pro nếu máy có)
MONO_FAMILY = "Consolas"

# Bộ lệnh BT
BAUD_OPTIONS = ["1200", "2400", "4800", "9600", "19200", "38400", "57600", "115200"]
DATABITS = {"5": serial.FIVEBITS, "6": serial.SIXBITS, "7": serial.SEVENBITS, "8": serial.EIGHTBITS}
PARITY = {"None": serial.PARITY_NONE, "Even": serial.PARITY_EVEN, "Odd": serial.PARITY_ODD}
STOPBITS = {"1": serial.STOPBITS_ONE, "1.5": serial.STOPBITS_ONE_POINT_FIVE, "2": serial.STOPBITS_TWO}

UP_CMDS = [("+0.1", "1"), ("+0.2", "2"), ("+0.5", "5"), ("+1.0", "9")]
DOWN_CMDS = [("−0.1", "q"), ("−0.2", "w"), ("−0.5", "e"), ("−1.0", "r")]
HOTKEYS = ["1", "2", "5", "9", "q", "w", "e", "r"]

# Ghép delta (đơn vị 0.1°C) thành chuỗi lệnh
UP_STEPS = [("9", 10), ("5", 5), ("2", 2), ("1", 1)]
DOWN_STEPS = [("r", 10), ("e", 5), ("w", 2), ("q", 1)]

WARMUP_DROP = 30.0
WARMUP_ROR = 50.0
SPEED_OPTIONS = ["x1", "x2", "x5", "x10"]
ROR_WIN = 15

EVENT_LABELS = {"CHARGE": "CHARGE", "TP": "TP", "DRY END": "DE", "FCS": "FCs", "DROP": "DROP"}
PHASES = [("Dry", "CHARGE", "DE", "#34C759"),
          ("Maillard", "DE", "FCs", "#FF9500"),
          ("Dev", "FCs", "DROP", "#FF2D55")]

# Màu biểu đồ matplotlib theo từng mode (phải khớp nền CTk)
CHART_THEME = {
    "Light": {"fig": "#FFFFFF", "grid": "#E0E0E5", "text": "#1D1D1F",
              "bt": "#007AFF", "ror": "#AF52DE", "warm": "#C7C7CC",
              "marker": "#34C759", "box": "#F2F2F7"},
    "Dark": {"fig": "#2C2C2E", "grid": "#3A3A3C", "text": "#F5F5F7",
             "bt": "#0A84FF", "ror": "#BF5AF2", "warm": "#636366",
             "marker": "#32D74B", "box": "#1C1C1E"},
}


def mmss(sec):
    return f"{sec // 60:02d}:{sec % 60:02d}"


def compose_commands(delta_tenths):
    """Ghép chuỗi lệnh để dời BT thiết bị đúng delta (0.1°C). VD -2.6°C → 'rreq'."""
    cmds = []
    d = int(delta_tenths)
    for ch, val in UP_STEPS:
        while d >= val:
            cmds.append(ch)
            d -= val
    for ch, val in DOWN_STEPS:
        while d <= -val:
            cmds.append(ch)
            d += val
    return "".join(cmds)


class SimpleKalman:
    """Bản sao SimpleKalmanFilter (Arduino) để khớp tính rorBT của firmware."""

    def __init__(self, e_mea, e_est, q):
        self.err_measure = e_mea
        self.err_estimate = e_est
        self.q = q
        self.last_estimate = 0.0

    def update(self, mea):
        gain = self.err_estimate / (self.err_estimate + self.err_measure)
        cur = self.last_estimate + gain * (mea - self.last_estimate)
        self.err_estimate = (1.0 - gain) * self.err_estimate + abs(self.last_estimate - cur) * self.q
        self.last_estimate = cur
        return cur

    def reset(self):
        self.last_estimate = 0.0


def compute_ror(bt_list, win=ROR_WIN):
    """RoR (°C/phút) làm mượt Kalman để vẽ đường tham khảo."""
    kal = SimpleKalman(1, 1, 0.01)
    out = []
    for i in range(len(bt_list)):
        j = max(0, i - win)
        dt = i - j
        raw = (bt_list[i] - bt_list[j]) / dt * 60 if dt else 0.0
        out.append(kal.update(raw))
    return out


def parse_profile(path):
    """Đọc CSV Roaster Scope → (bt_list, events, charge_bt) tính từ CHARGE."""
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    start = 0
    for i, l in enumerate(lines):
        if l.startswith("Time1"):
            start = i + 1
            break
    rows = []
    for l in lines[start:]:
        if not l.strip():
            continue
        c = l.split("\t")
        if len(c) < 5:
            continue
        try:
            bt = float(c[3])
        except ValueError:
            continue
        rows.append((c[1].strip(), bt, c[4].strip()))
    charge_idx = next((i for i, (_, _, ev) in enumerate(rows) if ev.upper() == "CHARGE"), None)
    if charge_idx is None:
        raise ValueError("Không tìm thấy sự kiện CHARGE trong file")
    prof = rows[charge_idx:]
    bt_list = [bt for _, bt, _ in prof]
    events = []
    for i, (t2, _, ev) in enumerate(prof):
        label = EVENT_LABELS.get(ev.upper())
        if label:
            events.append((label, i, t2 or mmss(i)))
    return bt_list, events, bt_list[0]


# ════════════════════════════════════════════════════════════════════════════
#  LỚP LOGIC SERIAL — tách hẳn khỏi UI. Đọc trên thread riêng, đẩy qua queue.
# ════════════════════════════════════════════════════════════════════════════
class SerialManager:
    def __init__(self):
        self.ser = None
        self.rx_queue = queue.Queue()      # ('data', bytes) | ('error', str)
        self._running = False
        self._thread = None

    @staticmethod
    def list_ports():
        """Trả về list (device, label) — label kèm tên thiết bị."""
        out = []
        for p in serial.tools.list_ports.comports():
            desc = p.description or ""
            tail = f"({p.device})"
            if desc.endswith(tail):
                desc = desc[: -len(tail)].strip()
            label = f"{p.device} — {desc}" if desc and desc != "n/a" else p.device
            out.append((p.device, label))
        return out

    def open(self, port, baud, bytesize, parity, stopbits):
        """Mở cổng. Ném serial.SerialException/ValueError nếu lỗi."""
        self.ser = serial.Serial(port=port, baudrate=baud, bytesize=bytesize,
                                 parity=parity, stopbits=stopbits, timeout=0.2)
        self._running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def _read_loop(self):
        while self._running and self.ser:
            try:
                chunk = self.ser.read(256)
            except serial.SerialException:
                self.rx_queue.put(("error", "Mất kết nối cổng"))
                return
            if chunk:
                self.rx_queue.put(("data", chunk))

    def write(self, data):
        """Ghi bytes. Ném serial.SerialException nếu lỗi."""
        if self.ser:
            self.ser.write(data)

    def close(self):
        self._running = False
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=1)
        self._thread = None
        if self.ser:
            try:
                self.ser.close()
            except serial.SerialException:
                pass
            self.ser = None

    def is_open(self):
        return self.ser is not None


# ════════════════════════════════════════════════════════════════════════════
#  ỨNG DỤNG (UI)
# ════════════════════════════════════════════════════════════════════════════
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("Light")
        ctk.set_default_color_theme("blue")

        self.title("BT Serial Tester")
        self.geometry("1000x780")
        self.minsize(900, 720)
        self.configure(fg_color=BG_WINDOW)

        # Fonts
        self.f_title = ctk.CTkFont(FONT_FAMILY, 20, "bold")
        self.f_section = ctk.CTkFont(FONT_FAMILY, 14, "bold")
        self.f_label = ctk.CTkFont(FONT_FAMILY, 11)
        self.f_body = ctk.CTkFont(FONT_FAMILY, 13)
        self.f_btn = ctk.CTkFont(FONT_FAMILY, 14, "bold")
        self.f_value = ctk.CTkFont(MONO_FAMILY, 22, "bold")
        self.f_mono = ctk.CTkFont(MONO_FAMILY, 12)

        # Logic serial + trạng thái
        self.sm = SerialManager()
        self.port_map = {}          # label -> device
        self.rx_buf = ""
        self.dev_bt = None          # BT thiết bị (°C) đọc từ echo
        self.show_hex = tk.BooleanVar(value=False)
        self.echo_on = tk.BooleanVar(value=True)

        # Replay
        self.profile = None
        self.events = []
        self.charge_bt = 0.0
        self.play_thread = None
        self.playing = False
        self.phase = "idle"
        self.warm_target = 0.0
        self.replay_idx = 0
        self.ror_kalman = SimpleKalman(1, 1, 0.01)
        self.ror_count = 0
        self.ror_samp1 = None
        self.rorBT = 0
        self.marker = None

        self._build_ui()
        self.refresh_ports()
        self._bind_hotkeys()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(50, self._poll_rx)

    # ───────────────────────── Khối UI dùng lại ─────────────────────────────
    def _card(self, parent, **kw):
        return ctk.CTkFrame(parent, fg_color=CARD, corner_radius=12, **kw)

    def _field(self, parent, label_text):
        """Field kiểu Apple: label nhỏ xám phía trên, widget đặt bên dưới."""
        f = ctk.CTkFrame(parent, fg_color="transparent")
        ctk.CTkLabel(f, text=label_text.upper(), font=self.f_label,
                     text_color=TEXT_SUB).pack(anchor="w", padx=2, pady=(0, 2))
        return f

    # ───────────────────────────── Dựng UI ──────────────────────────────────
    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)   # vùng tab co giãn

        # Header
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 6))
        head.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(head, text="BT Serial Tester", font=self.f_title,
                     text_color=TEXT_STRONG).grid(row=0, column=0, sticky="w")
        self.seg_theme = ctk.CTkSegmentedButton(head, values=["Light", "Dark"],
                                                 command=self._on_theme, font=self.f_label)
        self.seg_theme.set("Light")
        self.seg_theme.grid(row=0, column=1, sticky="e")

        self._build_config_card()

        # Tabs
        self.tabs = ctk.CTkTabview(self, fg_color=CARD, corner_radius=12,
                                   segmented_button_selected_color=BLUE,
                                   segmented_button_selected_hover_color=BLUE_HOVER)
        self.tabs.grid(row=2, column=0, sticky="nsew", padx=24, pady=10)
        self.tabs.add("Điều khiển tay")
        self.tabs.add("Replay profile")
        self._build_manual_tab(self.tabs.tab("Điều khiển tay"))
        self._build_replay_tab(self.tabs.tab("Replay profile"))

        self._build_log_card()

        # Thanh status dưới cùng
        self.lbl_status = ctk.CTkLabel(self, text="Đang đóng", font=self.f_label,
                                       text_color=TEXT_SUB)
        self.lbl_status.grid(row=4, column=0, sticky="w", padx=28, pady=(0, 14))

    def _build_config_card(self):
        card = self._card(self)
        card.grid(row=1, column=0, sticky="ew", padx=24, pady=10)
        for c in range(6):
            card.grid_columnconfigure(c, weight=0)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(card, text="Cấu hình cổng", font=self.f_section,
                     text_color=TEXT_STRONG).grid(row=0, column=0, columnspan=6,
                                                   sticky="w", padx=18, pady=(14, 4))

        # Hàng 1: COM (giãn) + refresh
        com = self._field(card, "Cổng COM")
        com.grid(row=1, column=0, columnspan=2, sticky="ew", padx=(18, 8), pady=(0, 14))
        row = ctk.CTkFrame(com, fg_color="transparent")
        row.pack(fill="x")
        self.opt_port = ctk.CTkOptionMenu(row, values=["(quét...)"], font=self.f_body,
                                          fg_color=PILL_OFF, button_color=PILL_OFF,
                                          text_color=TEXT_STRONG, button_hover_color=GREY_BORDER,
                                          dropdown_font=self.f_body)
        self.opt_port.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(row, text="⟳", width=36, font=self.f_btn, fg_color=PILL_OFF,
                      text_color=TEXT_STRONG, hover_color=GREY_BORDER,
                      command=self.refresh_ports).pack(side="left", padx=(8, 0))

        # Hàng 1: Baud / Data / Parity / Stop
        self.opt_baud = self._add_option(card, "Baud", BAUD_OPTIONS, "9600", 1, 2)
        self.opt_data = self._add_option(card, "Data", list(DATABITS), "8", 1, 3)
        self.opt_parity = self._add_option(card, "Parity", list(PARITY), "None", 1, 4)
        self.opt_stop = self._add_option(card, "Stop", list(STOPBITS), "1", 1, 5)

        # Hàng 2: nút Open + status pill
        self.btn_open = ctk.CTkButton(card, text="Open", font=self.f_btn, width=120, height=38,
                                      corner_radius=10, fg_color=BLUE, hover_color=BLUE_HOVER,
                                      command=self.toggle_open)
        self.btn_open.grid(row=2, column=0, sticky="w", padx=18, pady=(0, 16))

        pill = ctk.CTkFrame(card, fg_color=PILL_OFF, corner_radius=14)
        pill.grid(row=2, column=1, columnspan=2, sticky="w", padx=4, pady=(0, 16))
        self.pill_dot = ctk.CTkLabel(pill, text="●", font=self.f_body, text_color="#8E8E93")
        self.pill_dot.pack(side="left", padx=(12, 4), pady=6)
        self.pill_txt = ctk.CTkLabel(pill, text="Chưa kết nối", font=self.f_body,
                                     text_color=TEXT_STRONG)
        self.pill_txt.pack(side="left", padx=(0, 14))

        self.lbl_dev_bt = ctk.CTkLabel(card, text="BT thiết bị  —", font=self.f_mono,
                                       text_color=BLUE)
        self.lbl_dev_bt.grid(row=2, column=3, columnspan=3, sticky="w", padx=8, pady=(0, 16))

    def _add_option(self, card, label, values, default, r, c):
        f = self._field(card, label)
        f.grid(row=r, column=c, sticky="w", padx=8, pady=(0, 14))
        opt = ctk.CTkOptionMenu(f, values=values, width=92, font=self.f_body,
                                fg_color=PILL_OFF, button_color=PILL_OFF,
                                text_color=TEXT_STRONG, button_hover_color=GREY_BORDER,
                                dropdown_font=self.f_body)
        opt.set(default)
        opt.pack()
        return opt

    def _build_manual_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)

        # Card Lệnh BT
        bt = self._card(tab)
        bt.grid(row=0, column=0, sticky="ew", padx=8, pady=(10, 8))
        for c in range(4):
            bt.grid_columnconfigure(c, weight=1)
        ctk.CTkLabel(bt, text="Lệnh BT", font=self.f_section,
                     text_color=TEXT_STRONG).grid(row=0, column=0, columnspan=4,
                                                  sticky="w", padx=16, pady=(14, 8))
        for i, (label, ch) in enumerate(UP_CMDS):
            ctk.CTkButton(bt, text=f"{label}\n{ch}", font=self.f_btn, height=52, corner_radius=10,
                          fg_color=GREEN, hover_color=GREEN_HOVER, text_color="white",
                          command=lambda c=ch: self.send_text(c)).grid(
                              row=1, column=i, padx=8, pady=4, sticky="ew")
        for i, (label, ch) in enumerate(DOWN_CMDS):
            ctk.CTkButton(bt, text=f"{label}\n{ch}", font=self.f_btn, height=52, corner_radius=10,
                          fg_color=RED, hover_color=RED_HOVER, text_color="white",
                          command=lambda c=ch: self.send_text(c)).grid(
                              row=2, column=i, padx=8, pady=(4, 16), sticky="ew")

        # Card Gửi tự do
        snd = self._card(tab)
        snd.grid(row=1, column=0, sticky="ew", padx=8, pady=8)
        snd.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(snd, text="Gửi tự do", font=self.f_section,
                     text_color=TEXT_STRONG).grid(row=0, column=0, columnspan=4,
                                                  sticky="w", padx=16, pady=(14, 8))
        self.ent_send = ctk.CTkEntry(snd, font=self.f_body, height=36, corner_radius=10,
                                     placeholder_text="Nhập chuỗi gửi…")
        self.ent_send.grid(row=1, column=0, sticky="ew", padx=(16, 8), pady=(0, 16))
        self.ent_send.bind("<Return>", lambda e: self.send_entry())
        self.sw_hex = ctk.CTkSwitch(snd, text="HEX", font=self.f_body, variable=self.show_hex,
                                    progress_color=BLUE)
        self.sw_hex.grid(row=1, column=1, padx=8, pady=(0, 16))
        self.opt_eol = ctk.CTkOptionMenu(snd, values=["(không)", "\\n", "\\r\\n"], width=90,
                                         font=self.f_body, fg_color=PILL_OFF, button_color=PILL_OFF,
                                         text_color=TEXT_STRONG, button_hover_color=GREY_BORDER)
        self.opt_eol.set("(không)")
        self.opt_eol.grid(row=1, column=2, padx=8, pady=(0, 16))
        ctk.CTkButton(snd, text="Send", font=self.f_btn, width=90, height=36, corner_radius=10,
                      fg_color=BLUE, hover_color=BLUE_HOVER,
                      command=self.send_entry).grid(row=1, column=3, padx=(8, 16), pady=(0, 16))

    def _build_replay_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(tab, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=8, pady=(10, 4))
        ctk.CTkButton(top, text="Chọn file CSV…", font=self.f_body, height=34, corner_radius=10,
                      fg_color=PILL_OFF, text_color=TEXT_STRONG, hover_color=GREY_BORDER,
                      command=self.choose_csv).pack(side="left")
        self.lbl_file = ctk.CTkLabel(top, text="(chưa chọn)", font=self.f_body, text_color=TEXT_SUB)
        self.lbl_file.pack(side="left", padx=12)
        self.lbl_events = ctk.CTkLabel(top, text="", font=self.f_mono, text_color=TEXT_STRONG)
        self.lbl_events.pack(side="left", padx=12)

        # Biểu đồ
        mode = ctk.get_appearance_mode()
        col = CHART_THEME[mode]
        self.fig = Figure(figsize=(7.6, 3.4), dpi=100, facecolor=col["fig"])
        self.ax = self.fig.add_subplot(111)
        self.ax2 = self.ax.twinx()
        self.canvas = FigureCanvasTkAgg(self.fig, master=tab)
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew", padx=8, pady=6)
        self.canvas.get_tk_widget().configure(highlightthickness=0)

        # Điều khiển replay
        ctl = ctk.CTkFrame(tab, fg_color="transparent")
        ctl.grid(row=2, column=0, sticky="ew", padx=8, pady=(2, 4))
        self.btn_play = ctk.CTkButton(ctl, text="▶  Start", font=self.f_btn, width=110, height=40,
                                      corner_radius=10, fg_color=GREEN, hover_color=GREEN_HOVER,
                                      text_color="white", command=self.start_replay)
        self.btn_play.pack(side="left", padx=(0, 8))
        ctk.CTkButton(ctl, text="■  Stop", font=self.f_btn, width=90, height=40, corner_radius=10,
                      fg_color=RED, hover_color=RED_HOVER, text_color="white",
                      command=self.stop_replay).pack(side="left", padx=8)
        ctk.CTkButton(ctl, text="⟲  Reset", font=self.f_btn, width=90, height=40, corner_radius=10,
                      fg_color=PILL_OFF, text_color=TEXT_STRONG, hover_color=GREY_BORDER,
                      command=self.reset_replay).pack(side="left", padx=8)
        ctk.CTkLabel(ctl, text="Tốc độ", font=self.f_label, text_color=TEXT_SUB).pack(side="left", padx=(16, 4))
        self.opt_speed = ctk.CTkOptionMenu(ctl, values=SPEED_OPTIONS, width=70, font=self.f_body,
                                           fg_color=PILL_OFF, button_color=PILL_OFF,
                                           text_color=TEXT_STRONG, button_hover_color=GREY_BORDER)
        self.opt_speed.set("x1")
        self.opt_speed.pack(side="left")

        info = ctk.CTkFrame(tab, fg_color="transparent")
        info.grid(row=3, column=0, sticky="ew", padx=8, pady=(2, 10))
        self.lbl_phase = self._stat_block(info, "PHA", "—", TEXT_STRONG)
        self.lbl_bt = self._stat_block(info, "BT MỤC TIÊU", "—", GREEN)
        self.lbl_ror = self._stat_block(info, "rorBT (KALMAN)", "—", "#FF9500")

    def _stat_block(self, parent, title, value, color):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(side="left", padx=(0, 26))
        ctk.CTkLabel(f, text=title, font=self.f_label, text_color=TEXT_SUB).pack(anchor="w")
        lbl = ctk.CTkLabel(f, text=value, font=self.f_value, text_color=color)
        lbl.pack(anchor="w")
        return lbl

    def _build_log_card(self):
        card = self._card(self)
        card.grid(row=3, column=0, sticky="nsew", padx=24, pady=10)
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(3, weight=1)

        head = ctk.CTkFrame(card, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 4))
        head.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(head, text="Dữ liệu nhận", font=self.f_section,
                     text_color=TEXT_STRONG).grid(row=0, column=0, sticky="w")
        ctk.CTkSwitch(head, text="Hiện HEX", font=self.f_body, variable=self.show_hex,
                      progress_color=BLUE).grid(row=0, column=1, padx=10)
        ctk.CTkSwitch(head, text="Echo lệnh gửi", font=self.f_body, variable=self.echo_on,
                      progress_color=BLUE).grid(row=0, column=2, padx=10)
        ctk.CTkButton(head, text="Xóa", font=self.f_body, width=64, height=30, corner_radius=8,
                      fg_color=PILL_OFF, text_color=TEXT_STRONG, hover_color=GREY_BORDER,
                      command=self.clear_log).grid(row=0, column=3, padx=(10, 0))

        self.log = ctk.CTkTextbox(card, font=self.f_mono, fg_color=LOG_BG, corner_radius=10,
                                  text_color=TEXT_STRONG, wrap="none")
        self.log.grid(row=1, column=0, sticky="nsew", padx=16, pady=(4, 16))
        self.log.configure(state="disabled")

    # ───────────────────────────── Cổng COM ─────────────────────────────────
    def refresh_ports(self):
        ports = SerialManager.list_ports()
        self.port_map = {label: dev for dev, label in ports}
        labels = list(self.port_map) or ["(không có cổng)"]
        self.opt_port.configure(values=labels)
        if self.opt_port.get() not in labels:
            self.opt_port.set(labels[0])

    def selected_port(self):
        return self.port_map.get(self.opt_port.get())

    def toggle_open(self):
        if self.sm.is_open():
            self.close_port()
        else:
            self.open_port()

    def open_port(self):
        port = self.selected_port()
        if not port:
            messagebox.showerror("Lỗi", "Chưa chọn cổng COM hợp lệ")
            return
        try:
            self.sm.open(port, int(self.opt_baud.get()), DATABITS[self.opt_data.get()],
                         PARITY[self.opt_parity.get()], STOPBITS[self.opt_stop.get()])
        except (serial.SerialException, ValueError) as e:
            messagebox.showerror("Không mở được cổng", str(e))
            self._set_status("Mở cổng thất bại")
            return
        self.rx_buf = ""
        self.btn_open.configure(text="Close", fg_color="transparent", border_width=1,
                                border_color=GREY_BORDER, text_color=TEXT_STRONG, hover_color=PILL_OFF)
        self._set_pill(True)
        fmt = f"{self.opt_data.get()}{self.opt_parity.get()[0]}{self.opt_stop.get()}"
        self._set_status(f"Đã mở {port} @ {self.opt_baud.get()} {fmt}")

    def close_port(self):
        self.stop_replay()
        self.sm.close()
        self.btn_open.configure(text="Open", fg_color=BLUE, border_width=0,
                                text_color="white", hover_color=BLUE_HOVER)
        self._set_pill(False)
        self._set_status("Đang đóng")

    def _set_pill(self, connected):
        if connected:
            self.pill_dot.configure(text_color=GREEN)
            self.pill_txt.configure(text="Connected")
        else:
            self.pill_dot.configure(text_color="#8E8E93")
            self.pill_txt.configure(text="Chưa kết nối")
            self.dev_bt = None
            self.lbl_dev_bt.configure(text="BT thiết bị  —")

    def _set_status(self, text):
        self.lbl_status.configure(text=text)

    # ───────────────────────────── Gửi ──────────────────────────────────────
    def send_entry(self):
        text = self.ent_send.get()
        if not text:
            return
        if self.show_hex.get():
            try:
                data = bytes.fromhex(text.replace(",", " "))
            except ValueError:
                messagebox.showerror("Lỗi", "Chuỗi HEX không hợp lệ (vd: 31 39 72)")
                return
            self._write(data, text)
        else:
            eol = {"(không)": "", "\\n": "\n", "\\r\\n": "\r\n"}[self.opt_eol.get()]
            self.send_text(text + eol)

    def send_text(self, text):
        self._write(text.encode("ascii", "ignore"), text)

    def _write(self, data, shown):
        if not self.sm.is_open():
            messagebox.showwarning("Chưa mở cổng", "Hãy bấm Open trước khi gửi")
            return
        try:
            self.sm.write(data)
        except serial.SerialException as e:
            messagebox.showerror("Lỗi gửi", str(e))
            self.close_port()
            return
        if self.echo_on.get() and shown:
            self._append_log(f"» {shown}\n")

    def _bind_hotkeys(self):
        for key in HOTKEYS:
            self.bind(f"<KeyPress-{key}>", self._on_hotkey)

    def _on_hotkey(self, event):
        # Bỏ qua khi đang gõ trong ô nhập tự do
        if self.focus_get() is self.ent_send:
            return
        if event.char in HOTKEYS:
            self.send_text(event.char)

    # ───────────────────────── Nhận (queue → UI) ────────────────────────────
    def _poll_rx(self):
        """Chạy trên main thread mỗi 50ms: rút queue, parse echo BT, ghi log."""
        try:
            while True:
                kind, payload = self.sm.rx_queue.get_nowait()
                if kind == "error":
                    self.close_port()
                    self._set_status(payload)
                    continue
                self._handle_rx(payload)
        except queue.Empty:
            pass
        self.after(50, self._poll_rx)

    def _handle_rx(self, chunk):
        text = chunk.decode("ascii", "replace")
        self.rx_buf += text
        while "\n" in self.rx_buf:
            line, self.rx_buf = self.rx_buf.split("\n", 1)
            m = re.search(r"BT:\s*(-?\d+(?:\.\d+)?)", line)
            if m:
                self.dev_bt = float(m.group(1))
                self.lbl_dev_bt.configure(text=f"BT thiết bị  {self.dev_bt:.2f}°C")
        shown = (" ".join(f"{b:02X}" for b in chunk) + " ") if self.show_hex.get() else text
        self._append_log(shown)

    def _append_log(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    # ───────────────────────── Replay: chọn & vẽ ────────────────────────────
    def choose_csv(self):
        path = filedialog.askopenfilename(title="Chọn file CSV Roaster Scope",
                                          filetypes=[("CSV", "*.csv"), ("Tất cả", "*.*")])
        if not path:
            return
        try:
            self.profile, self.events, self.charge_bt = parse_profile(path)
        except (ValueError, OSError) as e:
            messagebox.showerror("Lỗi đọc file", str(e))
            return
        self.replay_idx = 0
        self.lbl_file.configure(text=os.path.basename(path), text_color=TEXT_STRONG)
        self._draw_profile()

    def _draw_profile(self):
        col = CHART_THEME[ctk.get_appearance_mode()]
        self.fig.set_facecolor(col["fig"])
        self.ax.clear()
        self.ax2.clear()
        self.ax.set_facecolor(col["fig"])
        n = len(self.profile)
        ev = {label: (idx, t2) for label, idx, t2 in self.events}
        total = ev["DROP"][0] if "DROP" in ev else n - 1

        parts = []
        for name, a, b, color in PHASES:
            if a not in ev or b not in ev:
                continue
            i0, i1 = ev[a][0], ev[b][0]
            self.ax.axvspan(i0, i1, color=color, alpha=0.12, zorder=0)
            dur = i1 - i0
            pct = dur / total * 100 if total else 0
            self.ax.text((i0 + i1) / 2, 1.04, f"{name} · {mmss(dur)} · {pct:.1f}%",
                         transform=self.ax.get_xaxis_transform(), ha="center", va="bottom",
                         fontsize=8, color="white", clip_on=False,
                         bbox=dict(boxstyle="round,pad=0.3", fc=color, ec="none"))
            parts.append(f"{name} {mmss(dur)} {pct:.0f}%")
        self.lbl_events.configure(text="   ".join(parts))

        ror = compute_ror(self.profile)
        self.ax2.plot(range(n), ror, color=col["ror"], lw=1.2, ls="--")
        self.ax2.set_ylabel("RoR (°C/phút)", color=col["ror"], fontsize=9)
        self.ax2.tick_params(colors=col["ror"], labelsize=8)
        self.ax2.set_ylim(0, max(30, max(ror) * 1.2 if ror else 30))

        warm_secs = int(WARMUP_DROP / (WARMUP_ROR / 60.0))
        wx = list(range(-warm_secs, 1))
        wy = [self.charge_bt - WARMUP_DROP + (WARMUP_ROR / 60.0) * (s + warm_secs) for s in wx]
        self.ax.plot(wx, wy, color=col["warm"], lw=1.0, ls="--")
        self.ax.plot(range(n), self.profile, color=col["bt"], lw=2.0, zorder=3)

        for label, idx, t2 in self.events:
            ec = next((c for nm, a, bb, c in PHASES if a == label), col["ror"])
            self.ax.annotate(f"{label}\n{t2}\n{self.profile[idx]:.0f}°C",
                             (idx, self.profile[idx]), textcoords="offset points",
                             xytext=(0, 14), fontsize=7, color=col["text"], ha="center", zorder=5,
                             bbox=dict(boxstyle="round,pad=0.3", fc=col["box"], ec=ec, lw=1.2))

        self._style_axes(n, col)
        self.marker = self.ax.axvline(0, color=col["marker"], lw=1.5, zorder=6)
        self.fig.tight_layout()
        self.canvas.draw_idle()

    def _style_axes(self, n, col):
        self.ax.set_xlabel("Thời gian rang (mm:ss)", color=col["text"], fontsize=9)
        self.ax.set_ylabel("BT (°C)", color=col["bt"], fontsize=9)
        self.ax.tick_params(colors=col["text"], labelsize=8)
        self.ax.grid(True, color=col["grid"], alpha=0.7, lw=0.6)
        for sp in list(self.ax.spines.values()) + list(self.ax2.spines.values()):
            sp.set_color(col["grid"])
        step = 60 if n <= 1200 else 120
        ticks = list(range(0, n, step))
        self.ax.set_xticks(ticks)
        self.ax.set_xticklabels([mmss(t) for t in ticks])
        self.ax.set_xlim(-int(WARMUP_DROP / (WARMUP_ROR / 60.0)) - 5, n + 5)

    # ───────────────────────────── Replay: chạy ─────────────────────────────
    def start_replay(self):
        if self.playing:
            return
        if not self.sm.is_open():
            messagebox.showwarning("Chưa mở cổng", "Hãy Open cổng COM trước")
            return
        if not self.profile:
            messagebox.showwarning("Chưa có profile", "Hãy chọn file CSV trước")
            return
        self.playing = True
        self.phase = "warmup"
        self.warm_target = self.charge_bt - WARMUP_DROP
        self.replay_idx = 0
        self.ror_kalman.reset()
        self.ror_count = 0
        self.ror_samp1 = None
        self.rorBT = 0
        self.btn_play.configure(state="disabled")
        self.play_thread = threading.Thread(target=self._play_loop, daemon=True)
        self.play_thread.start()

    def stop_replay(self):
        self.playing = False
        if self.play_thread and self.play_thread is not threading.current_thread():
            self.play_thread.join(timeout=1)
        self.play_thread = None
        self.phase = "idle"
        self.btn_play.configure(state="normal")
        self.lbl_phase.configure(text="Dừng")

    def reset_replay(self):
        self.stop_replay()
        self.replay_idx = 0
        self.rorBT = 0
        self.lbl_bt.configure(text="—")
        self.lbl_ror.configure(text="—")
        self.lbl_phase.configure(text="—")
        if self.profile:
            self._move_marker(0)

    def _play_loop(self):
        while self.playing:
            try:
                speed = float(self.opt_speed.get().lstrip("x"))
            except ValueError:
                speed = 1.0
            if self.dev_bt is None:        # chưa biết BT thiết bị → gửi 1 lệnh dò
                self._write(b"1", "")
                time.sleep(0.3)
                continue

            if self.phase == "warmup":
                target = self.warm_target
                x_pos = -int((self.charge_bt - self.warm_target) / (WARMUP_ROR / 60.0))
                phase_txt = "HÂM"
            else:
                if self.replay_idx >= len(self.profile):
                    self.after(0, self._finish)
                    return
                target = self.profile[self.replay_idx]
                x_pos = self.replay_idx
                phase_txt = "REPLAY"

            delta_tenths = round((target - self.dev_bt) * 10)
            cmds = compose_commands(delta_tenths)
            if cmds:
                self._write(cmds.encode("ascii"), "")
                self.dev_bt = round(self.dev_bt + delta_tenths / 10.0, 1)

            self._update_ror(target)
            self.after(0, lambda t=target, x=x_pos, p=phase_txt: self._update_replay_ui(t, x, p))

            if self.phase == "warmup":
                self.warm_target += WARMUP_ROR / 60.0
                if self.warm_target >= self.charge_bt:
                    self.warm_target = self.charge_bt
                    self.phase = "replay"
                    self.replay_idx = 0
            else:
                self.replay_idx += 1
            time.sleep(1.0 / speed)

    def _update_ror(self, target):
        # rorBT khớp firmware: mỗi 3 giây raw=(ΔBT_0.1)*20, Kalman, clamp ±200 (0.1°C/phút)
        units = round(target * 10)
        if self.ror_samp1 is None:
            self.ror_samp1 = units
        self.ror_count += 1
        if self.ror_count >= 3:
            raw = (units - self.ror_samp1) * 20
            r = self.ror_kalman.update(raw)
            self.rorBT = max(-200, min(200, int(r)))
            self.ror_samp1 = units
            self.ror_count = 0

    def _update_replay_ui(self, target, x_pos, phase_txt):
        self.lbl_phase.configure(text=phase_txt)
        self.lbl_bt.configure(text=f"{target:.1f}°")
        self.lbl_ror.configure(text=f"{self.rorBT / 10:+.1f}")
        self._move_marker(x_pos)

    def _move_marker(self, x_pos):
        if self.marker is not None:
            self.marker.set_xdata([x_pos, x_pos])
            self.canvas.draw_idle()

    def _finish(self):
        self.playing = False
        self.play_thread = None
        self.phase = "idle"
        self.btn_play.configure(state="normal")
        self.lbl_phase.configure(text="Xong ✓")

    # ───────────────────────────── Theme ────────────────────────────────────
    def _on_theme(self, mode):
        ctk.set_appearance_mode(mode)
        if self.profile:
            self._draw_profile()

    # ───────────────────────────── Thoát ────────────────────────────────────
    def _on_close(self):
        self.playing = False
        self.sm.close()
        self.destroy()


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()


# ════════════════════════════════════════════════════════════════════════════
#  CÀI ĐẶT & ĐÓNG GÓI
# ════════════════════════════════════════════════════════════════════════════
#  Cài thư viện:
#      pip install customtkinter pyserial matplotlib
#
#  Build exe onefile (BẮT BUỘC --collect-all customtkinter nếu không exe lỗi
#  thiếu asset theme .json của customtkinter):
#      python -m PyInstaller --onefile --windowed --name BTSerialTester ^
#          --collect-all customtkinter ^
#          tools/bt_serial_tester_ctk.py
#
#  (Trên Git Bash dùng \ thay cho ^ để nối dòng, hoặc viết 1 dòng.)
#
#  GHI CHÚ: chuỗi lệnh mỗi nút BT gửi đi ĐÃ wired đúng theo firmware giả lập
#  ('1'=+0.1 … 'r'=-1.0). Nếu thiết bị của bạn dùng bộ lệnh khác, sửa UP_CMDS /
#  DOWN_CMDS / UP_STEPS / DOWN_STEPS ở đầu file.
