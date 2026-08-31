"""
BT Serial Tester — terminal serial + replay profile cho máy rang OTL-06ALS.

Lái nhiệt BT của thiết bị (firmware giả lập) qua serial, không cần cặp nhiệt thật.
Bộ lệnh thiết bị (mỗi ký tự đổi BT, thiết bị echo lại "BT:xxx.xx"):
    '1' +0.1   '2' +0.2   '5' +0.5   '9' +1.0   (tăng)
    'q' -0.1   'w' -0.2   'e' -0.5   'r' -1.0   (giảm)

Hai chế độ (Notebook):
  • Điều khiển tay : các nút tăng/giảm BT + gửi tự do.
  • Replay profile : chọn file CSV Roaster Scope → vẽ đường BT, đánh dấu
    CHARGE/DE/FCs/DROP. Bấm Start: BT khởi đầu = charge-30°C, tăng dần tới
    charge với RoR 50°C/phút, sau đó mô phỏng đúng đường BT của file. Hiển thị
    rorBT (lọc Kalman, khớp firmware). Có chọn tốc độ x1..x10, Stop, Reset.

Chọn COM, baudrate (mặc định 9600), khung dữ liệu (mặc định 8N1).

Build exe:
    python -m PyInstaller --onefile --windowed --name BTSerialTester tools/bt_serial_tester.py
"""

import os
import re
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog

import serial
import serial.tools.list_ports

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


# Tùy chọn cho các combobox cấu hình cổng
BAUD_OPTIONS = ["1200", "2400", "4800", "9600", "19200", "38400", "57600", "115200"]
DATABITS = {"5": serial.FIVEBITS, "6": serial.SIXBITS, "7": serial.SEVENBITS, "8": serial.EIGHTBITS}
PARITY = {"None (N)": serial.PARITY_NONE, "Even (E)": serial.PARITY_EVEN,
          "Odd (O)": serial.PARITY_ODD, "Mark (M)": serial.PARITY_MARK,
          "Space (S)": serial.PARITY_SPACE}
STOPBITS = {"1": serial.STOPBITS_ONE, "1.5": serial.STOPBITS_ONE_POINT_FIVE, "2": serial.STOPBITS_TWO}

# Nút lệnh BT tay: (nhãn, ký tự gửi)
UP_CMDS = [("+0.1 (1)", "1"), ("+0.2 (2)", "2"), ("+0.5 (5)", "5"), ("+1.0 (9)", "9")]
DOWN_CMDS = [("-0.1 (q)", "q"), ("-0.2 (w)", "w"), ("-0.5 (e)", "e"), ("-1.0 (r)", "r")]

# Bước lệnh để ghép delta (đơn vị 0.1°C). Tăng dần độ lớn để ghép tham lam.
UP_STEPS = [("9", 10), ("5", 5), ("2", 2), ("1", 1)]
DOWN_STEPS = [("r", 10), ("e", 5), ("w", 2), ("q", 1)]

WARMUP_DROP = 30.0          # BT khởi đầu thấp hơn charge 30°C
WARMUP_ROR = 50.0           # tốc độ tăng pha hâm: °C/phút
SPEED_OPTIONS = ["x1", "x2", "x5", "x10"]

# Tên sự kiện cần đánh dấu (chuẩn hóa từ cột Event)
EVENT_LABELS = {"CHARGE": "CHARGE", "TP": "TP", "DRY END": "DE", "FCS": "FCs", "DROP": "DROP"}

# Bảng màu nền tối (tham khảo Roast Lab)
THEME = {
    "fig": "#0f1b2d", "ax": "#0f1b2d", "grid": "#27374d", "text": "#cdd9e8",
    "bt": "#3b82f6", "ror": "#b388ff", "warm": "#8a97a8", "marker": "#22e6c3",
}
# Pha rang: (nhãn, sự kiện đầu, sự kiện cuối, màu)
PHASES = [("Dry", "CHARGE", "DE", "#2ecc71"),
          ("Maillard", "DE", "FCs", "#f39c12"),
          ("Dev", "FCs", "DROP", "#e91e8c")]
ROR_WIN = 15        # cửa sổ tính RoR cho đường vẽ (giây)


def mmss(sec):
    return f"{sec // 60:02d}:{sec % 60:02d}"


def compute_ror(bt_list, win=ROR_WIN):
    """RoR (°C/phút) làm mượt bằng Kalman, để vẽ đường tham khảo."""
    kal = SimpleKalman(1, 1, 0.01)
    out = []
    for i in range(len(bt_list)):
        j = max(0, i - win)
        dt = i - j
        raw = (bt_list[i] - bt_list[j]) / dt * 60 if dt else 0.0
        out.append(kal.update(raw))
    return out


class SimpleKalman:
    """Bản sao SimpleKalmanFilter (thư viện Arduino) để khớp tính rorBT firmware."""

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


def compose_commands(delta_tenths):
    """Ghép chuỗi lệnh ('1'/'2'/'5'/'9'/'q'/'w'/'e'/'r') để dời BT đúng delta (0.1°C)."""
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


def parse_profile(path):
    """Đọc CSV Roaster Scope. Trả về (bt_list, events, charge_bt) tính từ CHARGE.

    bt_list : danh sách BT (°C) mỗi giây kể từ CHARGE.
    events  : list (nhãn, index_giây, "mm:ss") cho CHARGE/DE/FCs/DROP.
    """
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()

    start = 0
    for i, l in enumerate(lines):
        if l.startswith("Time1"):
            start = i + 1
            break

    rows = []          # (time2, bt, event_raw)
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

    charge_idx = next((i for i, (_, _, ev) in enumerate(rows)
                       if ev.upper() == "CHARGE"), None)
    if charge_idx is None:
        raise ValueError("Không tìm thấy sự kiện CHARGE trong file")

    prof = rows[charge_idx:]
    bt_list = [bt for _, bt, _ in prof]
    events = []
    for i, (t2, _, ev) in enumerate(prof):
        label = EVENT_LABELS.get(ev.upper())
        if label:
            events.append((label, i, t2 or f"{i // 60:02d}:{i % 60:02d}"))
    return bt_list, events, bt_list[0]


class BTSerialTester:
    def __init__(self, root):
        self.root = root
        root.title("BT Serial Tester — OTL-06ALS")

        self.ser = None
        self.rx_thread = None
        self.rx_running = False
        self.rx_buf = ""
        self.dev_bt = None          # BT thiết bị đọc từ echo (°C), None = chưa biết

        # Trạng thái replay
        self.profile = None         # list BT (°C) từ CHARGE
        self.events = []
        self.charge_bt = 0.0
        self.csv_path = None
        self.play_thread = None
        self.playing = False
        self.phase = "idle"         # idle | warmup | replay
        self.warm_target = 0.0      # BT mục tiêu pha hâm
        self.replay_idx = 0
        # rorBT khớp firmware: raw=(ΔBT_0.1)*20, Kalman(1,1,0.01), clamp ±200, cửa sổ 3s
        self.ror_kalman = SimpleKalman(1, 1, 0.01)
        self.ror_count = 0
        self.ror_samp1 = None       # BT (đơn vị 0.1°C) của 3 giây trước
        self.rorBT = 0              # đơn vị 0.1°C/phút

        self._build_ui()
        self.refresh_ports()

    # ---------- UI ----------
    def _build_ui(self):
        pad = {"padx": 6, "pady": 4}

        # Cấu hình cổng (dùng chung)
        cfg = ttk.LabelFrame(self.root, text="Cấu hình cổng")
        cfg.grid(row=0, column=0, sticky="ew", padx=8, pady=6)

        ttk.Label(cfg, text="COM:").grid(row=0, column=0, **pad)
        self.cb_port = ttk.Combobox(cfg, width=28, state="readonly")
        self.cb_port.grid(row=0, column=1, columnspan=3, sticky="w", **pad)
        ttk.Button(cfg, text="↻", width=3, command=self.refresh_ports).grid(row=0, column=4, **pad)

        ttk.Label(cfg, text="Baud:").grid(row=1, column=0, **pad)
        self.cb_baud = ttk.Combobox(cfg, width=8, state="readonly", values=BAUD_OPTIONS)
        self.cb_baud.set("9600")
        self.cb_baud.grid(row=1, column=1, sticky="w", **pad)
        ttk.Label(cfg, text="Data:").grid(row=1, column=2, **pad)
        self.cb_data = ttk.Combobox(cfg, width=4, state="readonly", values=list(DATABITS))
        self.cb_data.set("8")
        self.cb_data.grid(row=1, column=3, sticky="w", **pad)

        ttk.Label(cfg, text="Parity:").grid(row=2, column=0, **pad)
        self.cb_parity = ttk.Combobox(cfg, width=10, state="readonly", values=list(PARITY))
        self.cb_parity.set("None (N)")
        self.cb_parity.grid(row=2, column=1, sticky="w", **pad)
        ttk.Label(cfg, text="Stop:").grid(row=2, column=2, **pad)
        self.cb_stop = ttk.Combobox(cfg, width=4, state="readonly", values=list(STOPBITS))
        self.cb_stop.set("1")
        self.cb_stop.grid(row=2, column=3, sticky="w", **pad)

        self.btn_open = tk.Button(cfg, text="Open", width=10, bg="#0a7d32", fg="white",
                                  font=("Segoe UI", 10, "bold"), command=self.toggle_open)
        self.btn_open.grid(row=1, column=4, rowspan=2, padx=6, pady=4)

        self.lbl_dev_bt = ttk.Label(cfg, text="BT thiết bị: --", foreground="#1763b6",
                                    font=("Consolas", 10, "bold"))
        self.lbl_dev_bt.grid(row=0, column=5, rowspan=3, padx=12)

        # Notebook: Điều khiển tay / Replay profile
        nb = ttk.Notebook(self.root)
        nb.grid(row=1, column=0, sticky="nsew", padx=8, pady=6)
        self._build_manual_tab(nb)
        self._build_replay_tab(nb)

        # Khung nhận (dùng chung)
        rx = ttk.LabelFrame(self.root, text="Dữ liệu nhận")
        rx.grid(row=2, column=0, sticky="ew", padx=8, pady=6)
        self.txt_rx = scrolledtext.ScrolledText(rx, width=70, height=8,
                                                 font=("Consolas", 9), state="disabled")
        self.txt_rx.grid(row=0, column=0, columnspan=4, padx=6, pady=6)
        self.var_rxhex = tk.BooleanVar(value=False)
        ttk.Checkbutton(rx, text="Hiện HEX", variable=self.var_rxhex).grid(row=1, column=0, padx=6, sticky="w")
        self.var_echo = tk.BooleanVar(value=True)
        ttk.Checkbutton(rx, text="Echo lệnh gửi", variable=self.var_echo).grid(row=1, column=1, sticky="w")
        ttk.Button(rx, text="Xóa", width=8, command=self.clear_rx).grid(row=1, column=3, padx=6, sticky="e")

        self.lbl_status = ttk.Label(self.root, text="Đang đóng", foreground="gray")
        self.lbl_status.grid(row=3, column=0, sticky="w", padx=12, pady=(0, 8))

    def _build_manual_tab(self, nb):
        tab = ttk.Frame(nb)
        nb.add(tab, text="Điều khiển tay")

        bt = ttk.LabelFrame(tab, text="Lệnh BT")
        bt.grid(row=0, column=0, sticky="ew", padx=8, pady=6)
        for i, (label, ch) in enumerate(UP_CMDS):
            tk.Button(bt, text=label, width=9, height=2, bg="#0a7d32", fg="white",
                      font=("Segoe UI", 9, "bold"),
                      command=lambda c=ch: self.send_text(c)).grid(row=0, column=i, padx=4, pady=4)
        for i, (label, ch) in enumerate(DOWN_CMDS):
            tk.Button(bt, text=label, width=9, height=2, bg="#c0392b", fg="white",
                      font=("Segoe UI", 9, "bold"),
                      command=lambda c=ch: self.send_text(c)).grid(row=1, column=i, padx=4, pady=4)

        snd = ttk.LabelFrame(tab, text="Gửi tự do")
        snd.grid(row=1, column=0, sticky="ew", padx=8, pady=6)
        self.ent_send = ttk.Entry(snd, width=34)
        self.ent_send.grid(row=0, column=0, padx=6, pady=6)
        self.ent_send.bind("<Return>", lambda e: self.send_entry())
        self.var_hex = tk.BooleanVar(value=False)
        ttk.Checkbutton(snd, text="HEX", variable=self.var_hex).grid(row=0, column=1, padx=4)
        self.var_eol = tk.StringVar(value="(không)")
        ttk.Combobox(snd, width=8, state="readonly", textvariable=self.var_eol,
                     values=["(không)", "CR", "LF", "CRLF"]).grid(row=0, column=2, padx=4)
        ttk.Button(snd, text="Send", width=8, command=self.send_entry).grid(row=0, column=3, padx=6)

    def _build_replay_tab(self, nb):
        tab = ttk.Frame(nb)
        nb.add(tab, text="Replay profile")

        # Hàng chọn file + thông tin sự kiện
        top = ttk.Frame(tab)
        top.grid(row=0, column=0, sticky="ew", padx=8, pady=4)
        ttk.Button(top, text="Chọn file CSV…", command=self.choose_csv).grid(row=0, column=0, padx=4)
        self.lbl_file = ttk.Label(top, text="(chưa chọn)", foreground="gray")
        self.lbl_file.grid(row=0, column=1, padx=8, sticky="w")
        self.lbl_events = ttk.Label(top, text="", font=("Consolas", 9))
        self.lbl_events.grid(row=1, column=0, columnspan=2, padx=4, pady=2, sticky="w")

        # Đồ thị BT — nền tối kiểu Roast Lab
        self.fig = Figure(figsize=(7.6, 3.7), dpi=100, facecolor=THEME["fig"])
        self.ax = self.fig.add_subplot(111)
        self.ax2 = self.ax.twinx()      # trục phải cho RoR
        self.canvas = FigureCanvasTkAgg(self.fig, master=tab)
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew", padx=8, pady=4)
        self.canvas.get_tk_widget().config(bg=THEME["fig"], highlightthickness=0)
        self.marker = None

        # Điều khiển replay
        ctl = ttk.Frame(tab)
        ctl.grid(row=2, column=0, sticky="ew", padx=8, pady=6)
        self.btn_play = tk.Button(ctl, text="▶ Start", width=10, height=2, bg="#0a7d32", fg="white",
                                  font=("Segoe UI", 10, "bold"), command=self.start_replay)
        self.btn_play.grid(row=0, column=0, padx=4)
        tk.Button(ctl, text="■ Stop", width=8, height=2, bg="#c0392b", fg="white",
                  font=("Segoe UI", 10, "bold"), command=self.stop_replay).grid(row=0, column=1, padx=4)
        tk.Button(ctl, text="⟲ Reset", width=8, height=2,
                  command=self.reset_replay).grid(row=0, column=2, padx=4)

        ttk.Label(ctl, text="Tốc độ:").grid(row=0, column=3, padx=(16, 2))
        self.cb_speed = ttk.Combobox(ctl, width=5, state="readonly", values=SPEED_OPTIONS)
        self.cb_speed.set("x1")
        self.cb_speed.grid(row=0, column=4, padx=2)

        info = ttk.Frame(tab)
        info.grid(row=3, column=0, sticky="ew", padx=8, pady=4)
        ttk.Label(info, text="Pha:").grid(row=0, column=0, sticky="e")
        self.lbl_phase = ttk.Label(info, text="—", font=("Segoe UI", 11, "bold"), foreground="#555")
        self.lbl_phase.grid(row=0, column=1, padx=(4, 18), sticky="w")
        ttk.Label(info, text="BT mục tiêu:").grid(row=0, column=2, sticky="e")
        self.lbl_bt = ttk.Label(info, text="--", font=("Consolas", 16, "bold"), foreground="#0a7d32")
        self.lbl_bt.grid(row=0, column=3, padx=(4, 18), sticky="w")
        ttk.Label(info, text="rorBT (Kalman):").grid(row=0, column=4, sticky="e")
        self.lbl_ror = ttk.Label(info, text="--", font=("Consolas", 16, "bold"), foreground="#b35a00")
        self.lbl_ror.grid(row=0, column=5, padx=4, sticky="w")

    # ---------- Cổng COM ----------
    def refresh_ports(self):
        labels = []
        for p in serial.tools.list_ports.comports():
            desc = p.description or ""
            tail = f"({p.device})"
            if desc.endswith(tail):
                desc = desc[: -len(tail)].strip()
            labels.append(f"{p.device} — {desc}" if desc and desc != "n/a" else p.device)
        self.cb_port["values"] = labels
        if labels and not self.cb_port.get():
            self.cb_port.set(labels[0])

    def selected_port(self):
        sel = self.cb_port.get()
        return sel.split(" ")[0] if sel else ""

    def toggle_open(self):
        if self.ser:
            self.close_port()
        else:
            self.open_port()

    def open_port(self):
        port = self.selected_port()
        if not port:
            messagebox.showerror("Lỗi", "Chưa chọn cổng COM")
            return
        try:
            self.ser = serial.Serial(
                port=port,
                baudrate=int(self.cb_baud.get()),
                bytesize=DATABITS[self.cb_data.get()],
                parity=PARITY[self.cb_parity.get()],
                stopbits=STOPBITS[self.cb_stop.get()],
                timeout=0.2,
            )
        except (serial.SerialException, ValueError) as e:
            self.ser = None
            messagebox.showerror("Không mở được cổng", str(e))
            return

        self.rx_running = True
        self.rx_buf = ""
        self.rx_thread = threading.Thread(target=self._rx_loop, daemon=True)
        self.rx_thread.start()
        self.btn_open.config(text="Close", bg="#c0392b")
        self._lock_config(True)
        fmt = f"{self.cb_data.get()}{self.cb_parity.get()[-2]}{self.cb_stop.get()}"
        self.lbl_status.config(text=f"Đã mở {port} @ {self.cb_baud.get()} {fmt}", foreground="#0a7d32")

    def close_port(self):
        self.stop_replay()
        self.rx_running = False
        if self.rx_thread:
            self.rx_thread.join(timeout=1)
            self.rx_thread = None
        if self.ser:
            self.ser.close()
            self.ser = None
        self.btn_open.config(text="Open", bg="#0a7d32")
        self._lock_config(False)
        self.lbl_status.config(text="Đang đóng", foreground="gray")

    def _lock_config(self, locked):
        state = "disabled" if locked else "readonly"
        for cb in (self.cb_port, self.cb_baud, self.cb_data, self.cb_parity, self.cb_stop):
            cb.config(state=state)

    # ---------- Gửi ----------
    def send_entry(self):
        text = self.ent_send.get()
        if not text:
            return
        if self.var_hex.get():
            try:
                data = bytes.fromhex(text.replace(",", " "))
            except ValueError:
                messagebox.showerror("Lỗi", "Chuỗi HEX không hợp lệ (vd: 31 39 72)")
                return
            self._write(data, text)
        else:
            eol = {"(không)": "", "CR": "\r", "LF": "\n", "CRLF": "\r\n"}[self.var_eol.get()]
            self.send_text(text + eol)

    def send_text(self, text):
        self._write(text.encode("ascii", "ignore"), text)

    def _write(self, data, shown):
        if not self.ser:
            messagebox.showwarning("Chưa mở cổng", "Hãy bấm Open trước khi gửi")
            return
        try:
            self.ser.write(data)
        except serial.SerialException as e:
            messagebox.showerror("Lỗi gửi", str(e))
            self.close_port()
            return
        if self.var_echo.get() and shown:
            self._append(f"» {shown}\n", "#1763b6")

    # ---------- Nhận + đồng bộ BT từ echo ----------
    def _rx_loop(self):
        while self.rx_running and self.ser:
            try:
                chunk = self.ser.read(256)
            except serial.SerialException:
                self.root.after(0, self.close_port)
                return
            if not chunk:
                continue
            text = chunk.decode("ascii", "replace")
            self.rx_buf += text
            # Tách dòng để bắt "BT:xxx.xx" dù dữ liệu đến từng phần
            while "\n" in self.rx_buf:
                line, self.rx_buf = self.rx_buf.split("\n", 1)
                m = re.search(r"BT:\s*(-?\d+(?:\.\d+)?)", line)
                if m:
                    self.dev_bt = float(m.group(1))
                    self.root.after(0, lambda v=self.dev_bt:
                                    self.lbl_dev_bt.config(text=f"BT thiết bị: {v:.2f}"))
            shown = (" ".join(f"{b:02X}" for b in chunk) + " ") if self.var_rxhex.get() else text
            self.root.after(0, lambda t=shown: self._append(t, "#222222"))

    def _append(self, text, color):
        self.txt_rx.config(state="normal")
        tag = f"c{color}"
        self.txt_rx.tag_config(tag, foreground=color)
        self.txt_rx.insert("end", text, tag)
        self.txt_rx.see("end")
        self.txt_rx.config(state="disabled")

    def clear_rx(self):
        self.txt_rx.config(state="normal")
        self.txt_rx.delete("1.0", "end")
        self.txt_rx.config(state="disabled")

    # ---------- Replay: chọn & vẽ ----------
    def choose_csv(self):
        path = filedialog.askopenfilename(
            title="Chọn file CSV Roaster Scope",
            filetypes=[("CSV", "*.csv"), ("Tất cả", "*.*")])
        if not path:
            return
        try:
            self.profile, self.events, self.charge_bt = parse_profile(path)
        except (ValueError, OSError) as e:
            messagebox.showerror("Lỗi đọc file", str(e))
            return
        self.csv_path = path
        self.replay_idx = 0
        self.lbl_file.config(text=os.path.basename(path), foreground="black")
        self._draw_profile()

    def _draw_profile(self):
        self.ax.clear()
        self.ax2.clear()
        n = len(self.profile)
        ev = {label: (idx, t2) for label, idx, t2 in self.events}
        total = ev["DROP"][0] if "DROP" in ev else n - 1

        # Dải pha Dry/Maillard/Dev: nền mờ + thanh nhãn trên đỉnh
        parts = []
        for name, a, b, color in PHASES:
            if a not in ev or b not in ev:
                continue
            i0, i1 = ev[a][0], ev[b][0]
            self.ax.axvspan(i0, i1, color=color, alpha=0.10, zorder=0)
            dur = i1 - i0
            pct = dur / total * 100 if total else 0
            self.ax.text((i0 + i1) / 2, 1.04, f"{name} · {mmss(dur)} · {pct:.1f}%",
                         transform=self.ax.get_xaxis_transform(), ha="center", va="bottom",
                         fontsize=8, color="white", clip_on=False,
                         bbox=dict(boxstyle="round,pad=0.3", fc=color, ec="none"))
            parts.append(f"{name} {mmss(dur)} {pct:.0f}%")
        self.lbl_events.config(text="   ".join(parts))

        # Đường RoR (trục phải) — tham khảo, làm mượt Kalman
        ror = compute_ror(self.profile)
        self.ax2.plot(range(n), ror, color=THEME["ror"], lw=1.2, ls="--", label="RoR")
        self.ax2.set_ylabel("RoR (°C/phút)", color=THEME["ror"], fontsize=9)
        self.ax2.tick_params(colors=THEME["ror"], labelsize=8)
        self.ax2.set_ylim(0, max(30, max(ror) * 1.2 if ror else 30))

        # Đoạn hâm warmup (charge-30 -> charge) nét đứt trước mốc 0
        warm_secs = int(WARMUP_DROP / (WARMUP_ROR / 60.0))
        wx = list(range(-warm_secs, 1))
        wy = [self.charge_bt - WARMUP_DROP + (WARMUP_ROR / 60.0) * (s + warm_secs) for s in wx]
        self.ax.plot(wx, wy, color=THEME["warm"], lw=1.0, ls="--", label="Warmup 50°C/ph")

        # Đường BT
        self.ax.plot(range(n), self.profile, color=THEME["bt"], lw=2.0, label="BT", zorder=3)

        # Hộp milestone tại mỗi sự kiện
        for label, idx, t2 in self.events:
            color = next((c for nm, a, b, c in PHASES if a == label), "#5b7aa5")
            self.ax.annotate(f"{label}\n{t2}\n{self.profile[idx]:.0f}°C",
                             (idx, self.profile[idx]), textcoords="offset points",
                             xytext=(0, 14), fontsize=7, color="white", ha="center", zorder=5,
                             bbox=dict(boxstyle="round,pad=0.3", fc="#1b2a40", ec=color, lw=1.2))

        self._style_axes(n)
        self.marker = self.ax.axvline(0, color=THEME["marker"], lw=1.5, zorder=6)
        self.fig.tight_layout()
        self.canvas.draw_idle()

    def _style_axes(self, n):
        self.ax.set_facecolor(THEME["ax"])
        self.ax.set_xlabel("Thời gian rang (mm:ss)", color=THEME["text"], fontsize=9)
        self.ax.set_ylabel("BT (°C)", color=THEME["bt"], fontsize=9)
        self.ax.tick_params(colors=THEME["text"], labelsize=8)
        self.ax.grid(True, color=THEME["grid"], alpha=0.6, lw=0.6)
        for sp in self.ax.spines.values():
            sp.set_color(THEME["grid"])
        for sp in self.ax2.spines.values():
            sp.set_color(THEME["grid"])
        step = 60 if n <= 1200 else 120
        ticks = list(range(0, n, step))
        self.ax.set_xticks(ticks)
        self.ax.set_xticklabels([mmss(t) for t in ticks])
        self.ax.set_xlim(-int(WARMUP_DROP / (WARMUP_ROR / 60.0)) - 5, n + 5)

    # ---------- Replay: chạy ----------
    def start_replay(self):
        if self.playing:
            return
        if not self.ser:
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
        self.btn_play.config(state="disabled")
        self.play_thread = threading.Thread(target=self._play_loop, daemon=True)
        self.play_thread.start()

    def stop_replay(self):
        self.playing = False
        if self.play_thread and self.play_thread is not threading.current_thread():
            self.play_thread.join(timeout=1)
        self.play_thread = None
        self.phase = "idle"
        self.btn_play.config(state="normal")
        self.lbl_phase.config(text="Dừng", foreground="#555")

    def reset_replay(self):
        self.stop_replay()
        self.replay_idx = 0
        self.rorBT = 0
        self.lbl_bt.config(text="--")
        self.lbl_ror.config(text="--")
        self.lbl_phase.config(text="—")
        if self.profile:
            self._move_marker(0)

    def _play_loop(self):
        while self.playing:
            try:
                speed = float(self.cb_speed.get().lstrip("x"))
            except ValueError:
                speed = 1.0

            # Cần biết BT thiết bị (đọc từ echo). Nếu chưa có, gửi 1 lệnh dò.
            if self.dev_bt is None:
                self._write(b"1", "")
                time.sleep(0.3)
                continue

            # Tính BT mục tiêu của giây hiện tại
            if self.phase == "warmup":
                target = self.warm_target
                x_pos = -int((self.charge_bt - self.warm_target) / (WARMUP_ROR / 60.0))
                phase_txt = "HÂM (warmup)"
            else:
                if self.replay_idx >= len(self.profile):
                    self.root.after(0, self._finish)
                    return
                target = self.profile[self.replay_idx]
                x_pos = self.replay_idx
                phase_txt = "REPLAY"

            # Gửi lệnh dời BT thiết bị tới target
            delta_tenths = round((target - self.dev_bt) * 10)
            cmds = compose_commands(delta_tenths)
            if cmds:
                self._write(cmds.encode("ascii"), "")
                # Cập nhật model BT ngay (echo sẽ xác nhận lại sau)
                self.dev_bt = round(self.dev_bt + delta_tenths / 10.0, 1)

            self._update_ror(target)
            self.root.after(0, lambda t=target, x=x_pos, p=phase_txt:
                            self._update_replay_ui(t, x, p))

            # Sang giây kế tiếp của profile
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
        # rorBT khớp firmware: mỗi 3 giây raw=(ΔBT_0.1)*20, Kalman, clamp ±200 (0.1°C/phút).
        units = round(target * 10)            # BT đơn vị 0.1°C như Temperature_BT
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
        self.lbl_phase.config(text=phase_txt, foreground="#0a7d32")
        self.lbl_bt.config(text=f"{target:.1f}°C")
        self.lbl_ror.config(text=f"{self.rorBT / 10:+.1f}°C/ph")
        self._move_marker(x_pos)

    def _move_marker(self, x_pos):
        if self.marker is not None:
            self.marker.set_xdata([x_pos, x_pos])
            self.canvas.draw_idle()

    def _finish(self):
        self.playing = False
        self.play_thread = None
        self.phase = "idle"
        self.btn_play.config(state="normal")
        self.lbl_phase.config(text="Xong ✓", foreground="#0a7d32")


def main():
    root = tk.Tk()
    app = BTSerialTester(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.close_port(), root.destroy()))
    root.mainloop()


if __name__ == "__main__":
    main()
