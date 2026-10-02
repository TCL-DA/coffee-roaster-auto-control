"""
BT Serial Tester — giao diện slate gọn, biểu đồ làm chủ.

Công cụ test/điều khiển thiết bị BT qua Serial. Bố cục đọc theo thứ tự
kết nối → chỉ số → đường cong → hành động: header gọn một hàng, card cấu hình
cổng có luôn Open/Close cạnh đèn trạng thái, vùng biểu đồ nhận hết chiều cao dư,
log có chiều cao hữu hạn và thu gọn được. Bảng màu slate trung tính cho cả
Light/Dark, chữ phụ nâng tương phản để đọc rõ.

Logic serial tách trong lớp SerialManager (đọc trên thread riêng, đẩy về UI qua
queue — tkinter không an toàn đa luồng). Luồng replay CŨNG chỉ nói chuyện với UI
qua queue `_ui_q`: không gọi widget/`after`/messagebox từ thread, và dừng bằng
`threading.Event` để đang `sleep` vẫn bị đánh thức ngay.

Con trỏ replay chạy mượt ở nhịp mục tiêu 60 Hz bằng cách nội suy theo
`time.monotonic` (SmoothCursor) và blit nền đã cache của matplotlib — tần suất
gửi lệnh ra thiết bị KHÔNG đổi, vẫn đúng một bước mỗi giây hồ sơ / tốc độ.

Bộ lệnh thiết bị (mỗi ký tự đổi BT 0.1°C, thiết bị echo "BT:xxx.xx"):
    '1' +0.1   '2' +0.2   '5' +0.5   '9' +1.0
    'q' -0.1   'w' -0.2   'e' -0.5   'r' -1.0

Cài lib + build: xem comment cuối file.
"""

import os
import sys
import re
import io
import json
import queue
import threading
import time
import tkinter as tk
from tkinter import messagebox, filedialog

import serial
import serial.tools.list_ports

import customtkinter as ctk
from PIL import Image, ImageTk

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

try:                       # module phụ nằm cạnh file này (logic thuần, test được)
    from bt_display_loop import (FRAME_MS, PerfStats, SmoothCursor,
                                 bounded_drain, trim_text_lines)
except ImportError:        # khi được gọi kiểu `python -m tools.bt_serial_tester_glass`
    from tools.bt_display_loop import (FRAME_MS, PerfStats, SmoothCursor,
                                       bounded_drain, trim_text_lines)


def resource_path(name):
    """Đường dẫn tài nguyên, chạy được cả khi đóng gói PyInstaller (--onefile)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def set_timer_resolution(on):
    """Windows: xin độ phân giải hẹn giờ ~1 ms cho nhịp vẽ đều tay.

    Mặc định Tk chỉ thức theo mốc ~15,6 ms, nên `after(16)` hay rơi sang mốc sau
    và chuyển động 60 Hz bị giật nhịp (đo được: nhịp nhảy 16/31 ms). Không có
    winmm (hệ khác) thì bỏ qua — app vẫn chạy, chỉ là nhịp thô hơn. Phải nhả lại
    bằng `set_timer_resolution(False)` khi thoát."""
    try:
        import ctypes
        winmm = ctypes.WinDLL("winmm")
        (winmm.timeBeginPeriod if on else winmm.timeEndPeriod)(1)
        return True
    except (OSError, AttributeError, ImportError, ValueError):
        return False


# ════════════════════════════════════════════════════════════════════════════
#  BẢNG MÀU & HÌNH HỌC (slate trung tính). Màu dạng (light, dark) để CTk tự đổi.
# ════════════════════════════════════════════════════════════════════════════
GLASS_CARD = ("#FFFFFF", "#1E293B")        # card chính (slate-800 ở Dark)
GLASS_INNER = ("#F8FAFC", "#172136")       # card lồng bên trong
CARD_BORDER = ("#E2E8F0", "#334155")       # viền mảnh tách card khỏi nền
TEXT_STRONG = ("#0F172A", "#F1F5F9")
# Chữ phụ: nâng tương phản hẳn so với xám nhạt cũ (slate-600 / slate-300)
TEXT_SUB = ("#475569", "#A9B7C8")
LOG_BG = ("#F1F5F9", "#0F172A")
FIELD_BG = ("#EDF1F7", "#334155")
FIELD_HOVER = ("#DCE4EF", "#475569")
PILL_BG = ("#EDF1F7", "#334155")
BLUE, BLUE_HOVER = "#2563EB", "#1D4ED8"
GREEN, GREEN_HOVER = "#16A34A", "#15803D"
RED, RED_HOVER = "#DC2626", "#B91C1C"
GREY_DOT = ("#94A3B8", "#64748B")          # đèn trạng thái lúc chưa kết nối

# Nền (top, bottom) cho từng mode — slate nhạt / slate rất tối
GRAD_LIGHT = ((241, 245, 249), (226, 232, 240))
GRAD_DARK = ((15, 23, 42), (2, 6, 23))

# Bán kính bo góc nhất quán toàn app (gọn hơn bản cũ cho đỡ tốn chiều cao)
R_CARD, R_BTN, R_FIELD, R_LOG, R_PILL = 14, 10, 8, 10, 14

# Khoảng cách thể hiện nhóm: card cách nhau PAD_Y, mép cửa sổ PAD_X
PAD_X, PAD_Y = 14, 6

# Log: chiều cao hữu hạn + chặn lịch sử + chặn khối lượng xử lý mỗi nhịp
LOG_HEIGHT = 108            # px — log KHÔNG giành chiều cao của biểu đồ
LOG_MAX_LINES = 1200        # quá thì cắt bớt phần đầu
LOG_MAX_CHARS = 140000      # chặn cả theo ký tự (chế độ HEX không có dòng mới)
LOG_MAX_CHUNK = 48          # số gói RX xử lý mỗi nhịp
LOG_TIME_BUDGET = 0.010     # giây — hết thì để nhịp sau làm tiếp
POLL_MS = 40                # nhịp lấy dữ liệu từ queue (RX + tin từ luồng replay)

FONT_FAMILY = "Segoe UI"        # SF Pro nếu máy có; fallback đẹp trên Windows
MONO_FAMILY = "Consolas"

# Tham số serial
BAUD_OPTIONS = ["1200", "2400", "4800", "9600", "19200", "38400", "57600", "115200"]
DATABITS = {"5": serial.FIVEBITS, "6": serial.SIXBITS, "7": serial.SEVENBITS, "8": serial.EIGHTBITS}
PARITY = {"None": serial.PARITY_NONE, "Even": serial.PARITY_EVEN, "Odd": serial.PARITY_ODD}
STOPBITS = {"1": serial.STOPBITS_ONE, "1.5": serial.STOPBITS_ONE_POINT_FIVE, "2": serial.STOPBITS_TWO}

UP_CMDS = [("+0.1", "1"), ("+0.2", "2"), ("+0.5", "5"), ("+1.0", "9")]
DOWN_CMDS = [("−0.1", "q"), ("−0.2", "w"), ("−0.5", "e"), ("−1.0", "r")]
HOTKEYS = ["1", "2", "5", "9", "q", "w", "e", "r"]

UP_STEPS = [("9", 10), ("5", 5), ("2", 2), ("1", 1)]
DOWN_STEPS = [("r", 10), ("e", 5), ("w", 2), ("q", 1)]

WARMUP_DROP, WARMUP_ROR = 30.0, 50.0
# Tốc độ replay: chọn nhanh trong danh sách HOẶC gõ thẳng số bất kỳ (x0.81, x1.02…)
SPEED_PRESETS = ["x0.25", "x0.5", "x0.75", "x0.9", "x1", "x1.1",
                 "x1.25", "x1.5", "x2", "x5", "x10"]
SPEED_MIN, SPEED_MAX = 0.05, 20.0
SPEED_NUDGE = 0.01          # bước của nút −/+ và con lăn chuột
SPEED_TYPING_MS = 400       # gõ xong ngừng bấy nhiêu ms thì mới áp dụng
ROR_WIN = 15
# Trần cột RoR bên phải đồ thị. Số → khoá cứng trần đó; None → tự co theo dữ liệu.
ROR_MAX_DEFAULT = 35.0
ROR_MAX_MIN, ROR_MAX_MAX = 5.0, 500.0
ROR_MAX_NUDGE = 5.0
ROR_AUTO_TEXT = "Tự động"
ROR_PRESETS = [ROR_AUTO_TEXT, "20", "35", "50", "80", "160"]
# Cài đặt lưu CẠNH exe (bản đóng gói) hoặc cạnh script (chạy dev) — app xách tay.
SETTINGS_FILE = "bt_tester_settings.json"
# Giới hạn bước gửi mỗi nhịp (0.1°C). Chặn việc dồn cả chuỗi lệnh lớn trong 1 lần
# write làm nghẽn thiết bị/Modbus (vd lúc Start phải kéo BT một đoạn dài).
MAX_STEP_TENTHS = 30

EVENT_LABELS = {"CHARGE": "CHARGE", "TP": "TP", "DRY END": "DE", "FCS": "FCs", "DROP": "DROP"}
PHASES = [("Dry", "CHARGE", "DE", "#15803D"),
          ("Maillard", "DE", "FCs", "#C2410C"),
          ("Dev", "FCs", "DROP", "#BE123C")]
PHASE_ALPHA = 0.07          # dải pha chỉ gợi vùng, không được tranh với đường BT
CHART_THEME = {
    "Light": {"fig": "#FFFFFF", "grid": "#E2E8F0", "text": "#0F172A", "bt": "#2563EB",
              "ror": "#7C3AED", "warm": "#94A3B8", "marker": "#16A34A", "box": "#F1F5F9"},
    "Dark": {"fig": "#1E293B", "grid": "#334155", "text": "#F1F5F9", "bt": "#60A5FA",
             "ror": "#A78BFA", "warm": "#64748B", "marker": "#4ADE80", "box": "#0F172A"},
}


def mmss(sec):
    return f"{sec // 60:02d}:{sec % 60:02d}"


def fmt_speed(v):
    """0.85 → 'x0.85'; 1.0 → 'x1' (bỏ số 0 thừa cho gọn ô)."""
    return "x" + f"{v:.2f}".rstrip("0").rstrip(".")


def fmt_num(v):
    """35.0 → '35'; 37.5 → '37.5'."""
    return f"{v:.1f}".rstrip("0").rstrip(".")


def settings_path():
    """Cạnh exe khi đã đóng gói, cạnh file .py khi chạy dev."""
    base = os.path.dirname(sys.executable if getattr(sys, "frozen", False)
                           else os.path.abspath(__file__))
    return os.path.join(base, SETTINGS_FILE)


def load_settings():
    """Đọc cài đặt đã lưu. Hỏng/thiếu file → dùng mặc định, KHÔNG chặn app."""
    try:
        with io.open(settings_path(), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def save_settings(d):
    try:
        with io.open(settings_path(), "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        return True
    except OSError:
        return False


def make_gradient(w, h, mode):
    """Tạo ảnh gradient dọc mềm (Pillow) để làm nền có chiều sâu."""
    w, h = max(2, w), max(2, h)
    top, bottom = (GRAD_DARK if mode == "Dark" else GRAD_LIGHT)
    strip = Image.new("RGB", (1, h))
    px = strip.load()
    for y in range(h):
        t = y / (h - 1)
        px[0, y] = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
    return ImageTk.PhotoImage(strip.resize((w, h)))


def compose_commands(delta_tenths):
    """Ghép chuỗi lệnh dời BT đúng delta (0.1°C). VD -2.6°C → 'rreq'."""
    cmds, d = [], int(delta_tenths)
    for ch, val in UP_STEPS:
        while d >= val:
            cmds.append(ch); d -= val
    for ch, val in DOWN_STEPS:
        while d <= -val:
            cmds.append(ch); d += val
    return "".join(cmds)


class SimpleKalman:
    """Bản sao SimpleKalmanFilter (Arduino) để khớp tính rorBT của firmware."""

    def __init__(self, e_mea, e_est, q):
        self.err_measure, self.err_estimate, self.q = e_mea, e_est, q
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
    kal = SimpleKalman(1, 1, 0.01)
    out = []
    for i in range(len(bt_list)):
        j = max(0, i - win)
        dt = i - j
        out.append(kal.update((bt_list[i] - bt_list[j]) / dt * 60 if dt else 0.0))
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
            rows.append((c[1].strip(), float(c[3]), c[4].strip()))
        except ValueError:
            continue
    charge_idx = next((i for i, (_, _, ev) in enumerate(rows) if ev.upper() == "CHARGE"), None)
    if charge_idx is None:
        raise ValueError("Không tìm thấy sự kiện CHARGE trong file")
    prof = rows[charge_idx:]
    bt_list = [bt for _, bt, _ in prof]
    events = [(EVENT_LABELS[ev.upper()], i, t2 or mmss(i))
              for i, (t2, _, ev) in enumerate(prof) if ev.upper() in EVENT_LABELS]
    return bt_list, events, bt_list[0]


# ════════════════════════════════════════════════════════════════════════════
#  LỚP LOGIC SERIAL — tách hẳn UI. Đọc trên thread riêng, đẩy qua queue.
# ════════════════════════════════════════════════════════════════════════════
class SerialManager:
    def __init__(self):
        self.ser = None
        self.rx_queue = queue.Queue()      # ('data', bytes) | ('error', str)
        self._running = False
        self._thread = None

    @staticmethod
    def list_ports():
        out = []
        for p in serial.tools.list_ports.comports():
            desc = p.description or ""
            tail = f"({p.device})"
            if desc.endswith(tail):
                desc = desc[: -len(tail)].strip()
            if len(desc) > 26:      # tên dài đẩy cả hàng cấu hình tràn khỏi card
                desc = desc[:25].rstrip() + "…"
            out.append((p.device, f"{p.device} — {desc}" if desc and desc != "n/a" else p.device))
        return out

    def open(self, port, baud, bytesize, parity, stopbits):
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
        self.geometry("1040x820")
        # Nhỏ nhất phải vừa màn 1366×768 (trừ taskbar) — bố cục gọn nên đủ chỗ.
        self.minsize(1000, 600)
        try:                       # icon cửa sổ (taskbar/title bar)
            self.iconbitmap(resource_path("bt_icon.ico"))
        except tk.TclError:
            pass

        # Phân cấp chữ: tiêu đề → mục → nhãn. Nhãn để 12 (bản cũ 11 quá nhỏ).
        self.f_title = ctk.CTkFont(FONT_FAMILY, 19, "bold")
        self.f_section = ctk.CTkFont(FONT_FAMILY, 14, "bold")
        self.f_label = ctk.CTkFont(FONT_FAMILY, 12)
        self.f_label_b = ctk.CTkFont(FONT_FAMILY, 12, "bold")
        self.f_body = ctk.CTkFont(FONT_FAMILY, 13)
        self.f_btn = ctk.CTkFont(FONT_FAMILY, 13, "bold")
        self.f_value = ctk.CTkFont(MONO_FAMILY, 17, "bold")
        self.f_mono = ctk.CTkFont(MONO_FAMILY, 12)

        self.sm = SerialManager()
        self.port_map = {}
        self.rx_buf = ""
        self.dev_bt = None
        self.show_hex = tk.BooleanVar(value=False)
        self.echo_on = tk.BooleanVar(value=True)
        self.log_open = tk.BooleanVar(value=True)   # log thu gọn được

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
        self.bt_offset = 0.0        # bù BT do can thiệp tay khi replay (°C)

        # Cầu nối luồng replay → UI. Luồng KHÔNG gọi widget/after/messagebox:
        # chỉ đẩy tin vào queue này, UI lấy mẫu ở `_poll_queues` trên main thread.
        self._ui_q = queue.Queue()
        self._stop_evt = threading.Event()   # đánh thức luồng đang đợi khi Stop
        self._play_gen = 0                   # thế hệ phiên replay: bỏ tin của phiên cũ

        # Vòng hiển thị: con trỏ nội suy theo monotonic + nền biểu đồ đã cache
        self.cursor = SmoothCursor()
        self.perf = PerfStats()
        self._bg_cache = None       # ảnh nền tĩnh để blit con trỏ
        self._bg_size = None        # cỡ khung lúc chụp nền — lệch là cache vô dụng
        self._frame_job = None      # id after() của vòng vẽ (None = đang nghỉ)
        self._resize_job = None
        self._canvas_wh = (0, 0)
        self._in_mpl_draw = False   # chống đệ quy khi xử lý draw_event
        self._last_blit_x = None    # vị trí con trỏ đã blit lần gần nhất
        self._hi_res_timer = set_timer_resolution(True)
        self._log_lines = 0         # số dòng đang có trong ô log
        self._log_chars = 0         # số ký tự đang có trong ô log
        # Cài đặt người dùng — nạp từ file cạnh exe, sửa tới đâu ghi lại tới đó
        self.cfg = load_settings()
        self.speed = 1.0            # tốc độ replay đang áp dụng (giá trị tự do)
        v = self._parse_speed(self.cfg.get("speed"))
        if v is not None:
            self.speed = v
        self._speed_job = None      # id after() của bộ chống rung khi gõ tốc độ
        # Trần cột RoR: số → khoá cứng; None → tự co theo dữ liệu
        self.ror_max = ROR_MAX_DEFAULT
        if "ror_max" in self.cfg:
            r = self.cfg["ror_max"]
            self.ror_max = None if r is None else max(ROR_MAX_MIN, min(ROR_MAX_MAX, float(r)))
        self._rormax_job = None

        self._bgimg = None

        self._build_ui()
        self.refresh_ports()
        self._bind_hotkeys()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(POLL_MS, self._poll_queues)

    # ───────────────────────── Khối UI dùng lại ─────────────────────────────
    def _card(self, parent, inner=False, **kw):
        return ctk.CTkFrame(parent, fg_color=GLASS_INNER if inner else GLASS_CARD,
                            corner_radius=R_CARD, border_width=1, border_color=CARD_BORDER, **kw)

    def _field(self, parent, label_text):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        # height ép tay: CTkLabel mặc định cao 28 px, ba nhãn kiểu này là mất
        # hơn 40 px chiều cao mà biểu đồ đang cần
        ctk.CTkLabel(f, text=label_text.upper(), font=self.f_label, height=15,
                     text_color=TEXT_SUB).pack(anchor="w", padx=2, pady=(0, 1))
        return f

    def _menu(self, parent, values, default, width=92):
        opt = ctk.CTkOptionMenu(parent, values=values, width=width, height=32, corner_radius=R_FIELD,
                                font=self.f_body, fg_color=FIELD_BG, button_color=FIELD_BG,
                                text_color=TEXT_STRONG, button_hover_color=FIELD_HOVER,
                                dropdown_font=self.f_body, dropdown_fg_color=GLASS_CARD,
                                dropdown_text_color=TEXT_STRONG)
        opt.set(default)
        return opt

    def _combo(self, parent, values, default, width=92, command=None):
        """Như _menu nhưng GÕ ĐƯỢC — dùng cho tốc độ replay (giá trị tự do)."""
        cb = ctk.CTkComboBox(parent, values=values, width=width, height=32,
                             corner_radius=R_FIELD, font=self.f_body,
                             fg_color=FIELD_BG, border_width=1, border_color=FIELD_BG,
                             button_color=FIELD_BG, button_hover_color=FIELD_HOVER,
                             text_color=TEXT_STRONG, dropdown_font=self.f_body,
                             dropdown_fg_color=GLASS_CARD, dropdown_text_color=TEXT_STRONG,
                             command=command)
        cb.set(default)
        return cb

    # ───────────────────────────── Dựng UI ──────────────────────────────────
    def _build_ui(self):
        # Nền gradient: Canvas phủ toàn cửa sổ bằng place (nằm DƯỚI các card). Card
        # là con TRỰC TIẾP của root và grid lên trên — khoảng hở giữa card lộ
        # gradient của canvas. Cách này ổn định, KHÔNG bị Tk restack/unmap như khi
        # dùng Label-chứa-ảnh làm cha (đổi tab/maximize từng làm mất card).
        self.bg = tk.Canvas(self, highlightthickness=0, bd=0)
        self.bg.place(x=0, y=0, relwidth=1, relheight=1)
        self.grid_columnconfigure(0, weight=1)
        # Chiều cao dư dồn cho VÙNG LÀM VIỆC (tab + biểu đồ), không cho log.
        self.grid_rowconfigure(2, weight=1)

        # Header một hàng: tên app + mô tả ngắn + đổi Light/Dark
        head = self._card(self)
        head.grid(row=0, column=0, sticky="ew", padx=PAD_X, pady=(10, PAD_Y))
        head.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(head, text="BT Serial Tester", font=self.f_title,
                     text_color=TEXT_STRONG).grid(row=0, column=0, sticky="w",
                                                  padx=(16, 12), pady=8)
        ctk.CTkLabel(head, text="Giả lập BT cho máy rang — gửi lệnh tay hoặc phát lại hồ sơ",
                     font=self.f_label, text_color=TEXT_SUB).grid(row=0, column=1,
                                                                  sticky="w", pady=8)
        self.seg_theme = ctk.CTkSegmentedButton(head, values=["Light", "Dark"], font=self.f_label,
                                                 corner_radius=R_BTN, height=30,
                                                 selected_color=BLUE,
                                                 selected_hover_color=BLUE_HOVER,
                                                 command=self._on_theme)
        self.seg_theme.set("Light")
        self.seg_theme.grid(row=0, column=2, sticky="e", padx=12, pady=8)

        self._build_config_card()

        self.tabs = ctk.CTkTabview(self, fg_color=GLASS_CARD, corner_radius=R_CARD,
                                   border_width=1, border_color=CARD_BORDER,
                                   segmented_button_selected_color=BLUE,
                                   segmented_button_selected_hover_color=BLUE_HOVER)
        self.tabs.grid(row=2, column=0, sticky="nsew", padx=PAD_X, pady=PAD_Y)
        self.tabs.add("Điều khiển tay")
        self.tabs.add("Replay profile")
        self._build_manual_tab(self.tabs.tab("Điều khiển tay"))
        self._build_replay_tab(self.tabs.tab("Replay profile"))

        self._build_log_card()

        # Tạo gradient nền (kích thước màn hình) sau khi đã có đủ card để lift
        self._refresh_gradient()

    def _build_config_card(self):
        """Một hàng duy nhất: cấu hình cổng → Open/Close → đèn trạng thái → BT đọc về.

        Nút Open/Close đứng NGAY cạnh cấu hình và đèn trạng thái để thao tác và
        kết quả nằm cùng chỗ mắt nhìn (bản cũ đặt hai thứ này xa nhau)."""
        card = self._card(self)
        card.grid(row=1, column=0, sticky="ew", padx=PAD_X, pady=PAD_Y)
        card.grid_columnconfigure(0, weight=1)

        com = self._field(card, "Cổng COM")
        com.grid(row=0, column=0, sticky="ew", padx=(14, 6), pady=(7, 8))
        row = ctk.CTkFrame(com, fg_color="transparent")
        row.pack(fill="x")
        self.opt_port = self._menu(row, ["(quét...)"], "(quét...)", width=170)
        self.opt_port.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(row, text="⟳", width=32, height=32, corner_radius=R_FIELD, font=self.f_btn,
                      fg_color=FIELD_BG, text_color=TEXT_STRONG, hover_color=FIELD_HOVER,
                      command=self.refresh_ports).pack(side="left", padx=(6, 0))

        for c, (label, values, default, w) in enumerate([
                ("Baud", BAUD_OPTIONS, "9600", 84), ("Data", list(DATABITS), "8", 62),
                ("Parity", list(PARITY), "None", 80), ("Stop", list(STOPBITS), "1", 66)], start=1):
            f = self._field(card, label)
            f.grid(row=0, column=c, sticky="w", padx=6, pady=(7, 8))
            m = self._menu(f, values, default, width=w)
            m.pack()
            setattr(self, f"opt_{label.lower()}", m)

        act = self._field(card, "Kết nối")
        act.grid(row=0, column=5, sticky="w", padx=(14, 6), pady=(7, 8))
        self.btn_open = ctk.CTkButton(act, text="Open", font=self.f_btn, width=92, height=32,
                                      corner_radius=R_BTN, fg_color=BLUE, hover_color=BLUE_HOVER,
                                      command=self.toggle_open)
        self.btn_open.pack()

        st = self._field(card, "Trạng thái")
        st.grid(row=0, column=6, sticky="w", padx=6, pady=(7, 8))
        pill = ctk.CTkFrame(st, fg_color=PILL_BG, corner_radius=R_PILL, height=32)
        pill.pack(fill="x")
        self.pill_dot = ctk.CTkLabel(pill, text="●", font=self.f_body, text_color=GREY_DOT)
        self.pill_dot.pack(side="left", padx=(10, 4), pady=5)
        self.pill_txt = ctk.CTkLabel(pill, text="Chưa kết nối", font=self.f_body,
                                     text_color=TEXT_STRONG)
        self.pill_txt.pack(side="left", padx=(0, 12))

        dev = self._field(card, "BT thiết bị")
        dev.grid(row=0, column=7, sticky="w", padx=(6, 14), pady=(7, 8))
        self.lbl_dev_bt = ctk.CTkLabel(dev, text="—  °C", font=self.f_value,
                                       text_color=BLUE, height=32, anchor="w")
        self.lbl_dev_bt.pack(anchor="w", fill="x")

    def _build_manual_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)

        bt = self._card(tab, inner=True)
        bt.grid(row=0, column=0, sticky="ew", padx=6, pady=(8, 6))
        for c in range(4):
            bt.grid_columnconfigure(c, weight=1)
        ctk.CTkLabel(bt, text="Lệnh BT", font=self.f_section, text_color=TEXT_STRONG).grid(
            row=0, column=0, columnspan=4, sticky="w", padx=14, pady=(10, 6))
        for i, (label, ch) in enumerate(UP_CMDS):
            ctk.CTkButton(bt, text=f"{label}   ({ch})", font=self.f_btn, height=42,
                          corner_radius=R_BTN,
                          fg_color=GREEN, hover_color=GREEN_HOVER, text_color="white",
                          command=lambda c=ch: self.send_text(c)).grid(
                              row=1, column=i, padx=6, pady=3, sticky="ew")
        for i, (label, ch) in enumerate(DOWN_CMDS):
            ctk.CTkButton(bt, text=f"{label}   ({ch})", font=self.f_btn, height=42,
                          corner_radius=R_BTN,
                          fg_color=RED, hover_color=RED_HOVER, text_color="white",
                          command=lambda c=ch: self.send_text(c)).grid(
                              row=2, column=i, padx=6, pady=3, sticky="ew")
        ctk.CTkLabel(bt, text="Phím tắt: 1 2 5 9 tăng — q w e r giảm (trừ lúc đang gõ ô gửi)",
                     font=self.f_label, text_color=TEXT_SUB).grid(
                         row=3, column=0, columnspan=4, sticky="w", padx=14, pady=(4, 10))

        snd = self._card(tab, inner=True)
        snd.grid(row=1, column=0, sticky="ew", padx=6, pady=(6, 8))
        snd.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(snd, text="Gửi tự do", font=self.f_section, text_color=TEXT_STRONG).grid(
            row=0, column=0, columnspan=4, sticky="w", padx=14, pady=(10, 6))
        self.ent_send = ctk.CTkEntry(snd, font=self.f_body, height=38, corner_radius=R_FIELD,
                                     fg_color=FIELD_BG, border_width=0, placeholder_text="Nhập chuỗi gửi…")
        self.ent_send.grid(row=1, column=0, sticky="ew", padx=(14, 8), pady=(0, 14))
        self.ent_send.bind("<Return>", lambda e: self.send_entry())
        ctk.CTkSwitch(snd, text="HEX", font=self.f_body, variable=self.show_hex,
                      progress_color=BLUE).grid(row=1, column=1, padx=8, pady=(0, 14))
        self.opt_eol = self._menu(snd, ["(không)", "\\n", "\\r\\n"], "(không)", width=90)
        self.opt_eol.grid(row=1, column=2, padx=8, pady=(0, 16))
        ctk.CTkButton(snd, text="Send", font=self.f_btn, width=90, height=38, corner_radius=R_BTN,
                      fg_color=BLUE, hover_color=BLUE_HOVER, command=self.send_entry).grid(
                          row=1, column=3, padx=(8, 16), pady=(0, 16))

    def _build_replay_tab(self, tab):
        """Bốn hàng: hồ sơ + thiết lập → chỉ số → biểu đồ (ăn chiều cao dư) → hành động.

        Thiết lập biểu đồ (tốc độ, trần RoR) tách khỏi điều khiển chính
        (Start/Stop/Reset) để hàng nút không bị tràn ở cửa sổ hẹp."""
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)      # chỉ biểu đồ được giãn

        # ── Hàng 0: hồ sơ + thiết lập biểu đồ ───────────────────────────────
        top = ctk.CTkFrame(tab, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=6, pady=(8, 2))
        ctk.CTkButton(top, text="Chọn file CSV…", font=self.f_body, height=32, width=124,
                      corner_radius=R_BTN, fg_color=FIELD_BG, text_color=TEXT_STRONG,
                      hover_color=FIELD_HOVER, command=self.choose_csv).pack(side="left")
        self.lbl_file = ctk.CTkLabel(top, text="(chưa chọn)", font=self.f_body, text_color=TEXT_SUB)
        self.lbl_file.pack(side="left", padx=10)

        # Trần cột RoR (trục phải của đồ thị) — gõ số tuỳ ý hoặc chọn "Tự động".
        # Sát mép phải cho thẳng hàng với trục nó điều khiển. Sửa xong ghi vào
        # file cài đặt ngay, lần sau mở app không phải chỉnh lại.
        ctk.CTkButton(top, text="+", font=self.f_btn, width=32, height=32, corner_radius=R_BTN,
                      fg_color=FIELD_BG, text_color=TEXT_STRONG, hover_color=FIELD_HOVER,
                      command=lambda: self.nudge_ror_max(ROR_MAX_NUDGE)).pack(side="right")
        self.opt_rormax = self._combo(top, ROR_PRESETS,
                                      ROR_AUTO_TEXT if self.ror_max is None else fmt_num(self.ror_max),
                                      width=98, command=self.commit_ror_max)
        self.opt_rormax.pack(side="right", padx=4)
        self.opt_rormax.bind("<Return>", lambda e: self.commit_ror_max())
        self.opt_rormax.bind("<KP_Enter>", lambda e: self.commit_ror_max())
        self.opt_rormax.bind("<FocusOut>", lambda e: self.commit_ror_max())
        self.opt_rormax.bind("<KeyRelease>", self._rormax_typed)
        self.opt_rormax.bind("<MouseWheel>", self._rormax_wheel)
        ctk.CTkButton(top, text="−", font=self.f_btn, width=32, height=32, corner_radius=R_BTN,
                      fg_color=FIELD_BG, text_color=TEXT_STRONG, hover_color=FIELD_HOVER,
                      command=lambda: self.nudge_ror_max(-ROR_MAX_NUDGE)).pack(side="right")
        ctk.CTkLabel(top, text="Trần RoR", font=self.f_label,
                     text_color=TEXT_SUB).pack(side="right", padx=(16, 6))

        # Tốc độ replay: chọn nhanh trong danh sách, hoặc gõ thẳng số tuỳ ý
        # (x0.81, x1.02…), hoặc bấm −/+ (lăn chuột trên ô cũng được) từng 0.01.
        self.lbl_speed = ctk.CTkLabel(top, text=f"1 giây hồ sơ = {1.0 / self.speed:.2f}s thật",
                                      font=self.f_label, text_color=TEXT_SUB)
        self.lbl_speed.pack(side="right", padx=(8, 0))
        ctk.CTkButton(top, text="+", font=self.f_btn, width=32, height=32, corner_radius=R_BTN,
                      fg_color=FIELD_BG, text_color=TEXT_STRONG, hover_color=FIELD_HOVER,
                      command=lambda: self.nudge_speed(SPEED_NUDGE)).pack(side="right", padx=(6, 0))
        self.opt_speed = self._combo(top, SPEED_PRESETS, fmt_speed(self.speed), width=92,
                                     command=self.commit_speed)
        self.opt_speed.pack(side="right", padx=4)
        self.opt_speed.bind("<Return>", lambda e: self.commit_speed())
        self.opt_speed.bind("<KP_Enter>", lambda e: self.commit_speed())
        self.opt_speed.bind("<FocusOut>", lambda e: self.commit_speed())
        self.opt_speed.bind("<KeyRelease>", self._speed_typed)
        self.opt_speed.bind("<MouseWheel>", self._speed_wheel)
        ctk.CTkButton(top, text="−", font=self.f_btn, width=32, height=32, corner_radius=R_BTN,
                      fg_color=FIELD_BG, text_color=TEXT_STRONG, hover_color=FIELD_HOVER,
                      command=lambda: self.nudge_speed(-SPEED_NUDGE)).pack(side="right")
        ctk.CTkLabel(top, text="Tốc độ", font=self.f_label,
                     text_color=TEXT_SUB).pack(side="right", padx=(18, 6))

        # ── Hàng 2: biểu đồ, phần chiếm chỗ chính của màn hình ───────────────
        col = CHART_THEME[ctk.get_appearance_mode()]
        self.fig = Figure(figsize=(7.6, 3.3), dpi=100, facecolor=col["fig"])
        # Bố cục tự tính lại ở MỌI lần vẽ (kể cả sau resize) — gọi tight_layout()
        # một lần thì tỉ lệ chừa chỗ tính theo cỡ cũ, thu nhỏ là mất nhãn trục X.
        # rect chừa dải trên cho nhãn pha.
        self.fig.set_layout_engine("tight", rect=(0, 0, 1, 0.945), pad=0.5)
        self.ax = self.fig.add_subplot(111)
        self.ax2 = self.ax.twinx()
        self.canvas = FigureCanvasTkAgg(self.fig, master=tab)
        cw = self.canvas.get_tk_widget()
        cw.grid(row=2, column=0, sticky="nsew", padx=6, pady=4)
        cw.configure(highlightthickness=0)
        # Mỗi lần matplotlib vẽ lại (đổi hồ sơ, đổi theme, đổi trần RoR, resize)
        # thì cache nền phải làm mới — nếu không con trỏ blit sẽ để lại vết cũ.
        self.canvas.mpl_connect("draw_event", self._on_mpl_draw)
        # add="+" là BẮT BUỘC: FigureCanvasTkAgg đã bind <Configure> để đổi cỡ
        # figure; bind đè lên sẽ làm figure không co giãn (mất nhãn trục, vùng
        # bên phải trắng bệch vì chưa ai vẽ vào đó).
        cw.bind("<Configure>", self._on_canvas_resize, add="+")
        self._draw_empty_chart()

        self._build_replay_kpi(tab)
        self._build_replay_actions(tab)

    def _build_replay_kpi(self, tab):
        """Hàng 1 — chỉ số: đọc xong mới tới đường cong. Đơn vị ghi ngay trên nhãn."""
        kpi = ctk.CTkFrame(tab, fg_color="transparent")
        kpi.grid(row=1, column=0, sticky="ew", padx=6, pady=(2, 2))
        self.lbl_phase = self._stat_block(kpi, "PHA", "—", TEXT_STRONG)
        self.lbl_bt = self._stat_block(kpi, "BT MỤC TIÊU (°C)", "—", GREEN)
        self.lbl_ror = self._stat_block(kpi, "rorBT (°C/phút)", "—", "#C2410C")
        self.lbl_offset = self._stat_block(kpi, "BÙ TAY (°C)", "+0.0", TEXT_SUB)
        self.lbl_events = ctk.CTkLabel(kpi, text="", font=self.f_mono,
                                       text_color=TEXT_STRONG, justify="right")
        self.lbl_events.pack(side="right", padx=(10, 6))

    def _build_replay_actions(self, tab):
        """Hàng 3 — hành động: chạy/dừng và can thiệp BT, tách khỏi thiết lập biểu đồ."""
        ctl = ctk.CTkFrame(tab, fg_color="transparent")
        ctl.grid(row=3, column=0, sticky="ew", padx=6, pady=(4, 8))
        self.btn_play = ctk.CTkButton(ctl, text="▶  Start", font=self.f_btn, width=100, height=36,
                                      corner_radius=R_BTN, fg_color=GREEN, hover_color=GREEN_HOVER,
                                      text_color="white", command=self.start_replay)
        self.btn_play.pack(side="left", padx=(0, 6))
        # Stop luôn cạnh Start, không bị nhóm thiết lập đẩy ra khỏi khung nữa
        ctk.CTkButton(ctl, text="■  Stop", font=self.f_btn, width=88, height=36, corner_radius=R_BTN,
                      fg_color=RED, hover_color=RED_HOVER, text_color="white",
                      command=self.stop_replay).pack(side="left", padx=6)
        ctk.CTkButton(ctl, text="⟲  Reset", font=self.f_btn, width=88, height=36, corner_radius=R_BTN,
                      fg_color=FIELD_BG, text_color=TEXT_STRONG, hover_color=FIELD_HOVER,
                      command=self.reset_replay).pack(side="left", padx=6)

        # Can thiệp BT — bước độ nguyên ±1/±2/±5/±10
        ctk.CTkLabel(ctl, text="Can thiệp BT (°C)", font=self.f_label,
                     text_color=TEXT_SUB).pack(side="left", padx=(20, 8))
        for d in (-10, -5, -2, -1):
            ctk.CTkButton(ctl, text=str(d), width=44, height=32, corner_radius=R_BTN,
                          font=self.f_btn, fg_color=RED, hover_color=RED_HOVER, text_color="white",
                          command=lambda v=d: self.bump_bt(v)).pack(side="left", padx=2)
        for d in (1, 2, 5, 10):
            ctk.CTkButton(ctl, text=f"+{d}", width=44, height=32, corner_radius=R_BTN,
                          font=self.f_btn, fg_color=GREEN, hover_color=GREEN_HOVER, text_color="white",
                          command=lambda v=d: self.bump_bt(v)).pack(side="left", padx=2)

    def _stat_block(self, parent, title, value, color):
        """Ô chỉ số: nhãn nhỏ trên, số lớn dưới, nền card lồng để tách nhóm rõ."""
        f = ctk.CTkFrame(parent, fg_color=GLASS_INNER, corner_radius=R_BTN,
                         border_width=1, border_color=CARD_BORDER)
        f.pack(side="left", padx=(0, 8))
        ctk.CTkLabel(f, text=title, font=self.f_label, height=15, text_color=TEXT_SUB).pack(
            anchor="w", padx=11, pady=(3, 0))
        lbl = ctk.CTkLabel(f, text=value, font=self.f_value, height=24, text_color=color)
        lbl.pack(anchor="w", padx=11, pady=(0, 3))
        return lbl

    def _build_log_card(self):
        """Log chiều cao hữu hạn + thu gọn được: RX dồn bao nhiêu cũng không ăn
        chỗ của biểu đồ. Trạng thái cổng nằm cùng hàng tiêu đề để đỡ một dòng."""
        card = self._card(self)
        card.grid(row=3, column=0, sticky="ew", padx=PAD_X, pady=(PAD_Y, 10))
        card.grid_columnconfigure(0, weight=1)
        self.log_card = card

        head = ctk.CTkFrame(card, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 2))
        head.grid_columnconfigure(1, weight=1)
        self.btn_log = ctk.CTkButton(head, text="▾  Dữ liệu nhận", font=self.f_section,
                                     width=172, height=28, corner_radius=R_FIELD, anchor="w",
                                     fg_color="transparent", text_color=TEXT_STRONG,
                                     hover_color=FIELD_HOVER, command=self.toggle_log)
        self.btn_log.grid(row=0, column=0, sticky="w")
        self.lbl_status = ctk.CTkLabel(head, text="Đang đóng", font=self.f_label,
                                       text_color=TEXT_SUB)
        self.lbl_status.grid(row=0, column=1, sticky="w", padx=8)
        ctk.CTkSwitch(head, text="Hiện HEX", font=self.f_body, variable=self.show_hex,
                      progress_color=BLUE).grid(row=0, column=2, padx=8)
        ctk.CTkSwitch(head, text="Echo lệnh gửi", font=self.f_body, variable=self.echo_on,
                      progress_color=BLUE).grid(row=0, column=3, padx=8)
        ctk.CTkButton(head, text="Xóa", font=self.f_body, width=62, height=28,
                      corner_radius=R_FIELD, fg_color=FIELD_BG, text_color=TEXT_STRONG,
                      hover_color=FIELD_HOVER,
                      command=self.clear_log).grid(row=0, column=4, padx=(8, 0))

        self.log = ctk.CTkTextbox(card, font=self.f_mono, fg_color=LOG_BG, corner_radius=R_LOG,
                                  text_color=TEXT_STRONG, wrap="none", height=LOG_HEIGHT)
        self.log.configure(state="disabled")
        # Màn thấp (1366×768) mở lần đầu thì gập log lại cho biểu đồ rộng rãi
        self.log_open.set(bool(self.cfg.get("log_open", self.winfo_screenheight() > 800)))
        self._sync_log_toggle()

    def _sync_log_toggle(self):
        """Gập/mở ô log. Gập rồi vẫn nhận dữ liệu, chỉ là không hiện."""
        if self.log_open.get():
            self.log.grid(row=1, column=0, sticky="ew", padx=12, pady=(2, 10))
            self.btn_log.configure(text="▾  Dữ liệu nhận")
        else:
            self.log.grid_remove()
            self.btn_log.configure(text="▸  Dữ liệu nhận")

    def toggle_log(self):
        self.log_open.set(not self.log_open.get())
        self._sync_log_toggle()
        self._save_cfg()

    # ───────────────────────────── Nền gradient ─────────────────────────────
    def _refresh_gradient(self):
        # Vẽ gradient lên canvas nền (kích thước màn hình → phủ mọi cỡ cửa sổ).
        # Canvas nằm dưới các card nên redraw không ảnh hưởng z-order của card.
        w, h = self.winfo_screenwidth(), self.winfo_screenheight()
        self._bgimg = make_gradient(w, h, ctk.get_appearance_mode())
        self.bg.delete("grad")
        self.bg.create_image(0, 0, anchor="nw", image=self._bgimg, tags="grad")
        self.bg.tag_lower("grad")

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
        self.close_port() if self.sm.is_open() else self.open_port()

    def open_port(self, im_lang=False):
        """Mở cổng COM. `im_lang=True` thì TRẢ VỀ câu lỗi thay vì bật hộp thoại.

        Máy chủ điều khiển (API/MCP) phải gọi với `im_lang=True`: messagebox là
        modal, bật lên từ lệnh gọi máy là treo cứng luồng Tk và không ai ở đó
        mà bấm OK. Trả None nghĩa là mở được.
        """
        port = self.selected_port()
        if not port:
            if im_lang:
                return "Chưa chọn cổng COM hợp lệ"
            messagebox.showerror("Lỗi", "Chưa chọn cổng COM hợp lệ")
            return
        try:
            self.sm.open(port, int(self.opt_baud.get()), DATABITS[self.opt_data.get()],
                         PARITY[self.opt_parity.get()], STOPBITS[self.opt_stop.get()])
        except (serial.SerialException, ValueError) as e:
            self._set_status("Mở cổng thất bại")
            if im_lang:
                return str(e)
            messagebox.showerror("Không mở được cổng", str(e))
            return
        self.rx_buf = ""
        self.btn_open.configure(text="Close", fg_color="transparent", border_width=1,
                                border_color=CARD_BORDER, text_color=TEXT_STRONG, hover_color=FIELD_BG)
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
            self.pill_txt.configure(text="Đã kết nối")
        else:
            self.pill_dot.configure(text_color=GREY_DOT)
            self.pill_txt.configure(text="Chưa kết nối")
            self.dev_bt = None
            self.lbl_dev_bt.configure(text="—  °C")

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
        self.bind("<F9>", self._show_perf)      # móc đo hiệu năng, xem _show_perf

    def _on_hotkey(self, event):
        if self.focus_get() is self.ent_send:
            return
        if event.char in HOTKEYS:
            self.send_text(event.char)

    # ──────────────── Nhận RX + tin của luồng replay (queue → UI) ───────────
    def _poll_queues(self):
        """Một nhịp lo cả RX và tin luồng replay, CÓ GIỚI HẠN công việc.

        Mỗi nhịp lấy tối đa LOG_MAX_CHUNK gói (hoặc LOG_TIME_BUDGET giây) rồi ghi
        log MỘT lần; phần còn tồn để nhịp sau làm tiếp và nhịp đó được gọi sớm
        hơn. Nhờ vậy RX dồn một cục không treo giao diện."""
        items, more = bounded_drain(self.sm.rx_queue, LOG_MAX_CHUNK, LOG_TIME_BUDGET)
        buf = []
        for kind, payload in items:
            if kind == "error":
                self.close_port()
                self._set_status(payload)
                continue
            buf.append(self._handle_rx(payload))
        if buf:
            self._append_log("".join(buf))
        self._drain_ui_queue()
        self.after(5 if more else POLL_MS, self._poll_queues)

    def _handle_rx(self, chunk):
        """Tách dòng, cập nhật BT thiết bị; TRẢ chuỗi để bên ngoài ghi log gộp."""
        text = chunk.decode("ascii", "replace")
        self.rx_buf += text
        while "\n" in self.rx_buf:
            line, self.rx_buf = self.rx_buf.split("\n", 1)
            m = re.search(r"BT:\s*(-?\d+(?:\.\d+)?)", line)
            if m:
                self.dev_bt = float(m.group(1))
                self.lbl_dev_bt.configure(text=f"{self.dev_bt:.2f}  °C")
        if len(self.rx_buf) > 4096:      # dòng không bao giờ xuống hàng → cắt bớt
            self.rx_buf = self.rx_buf[-512:]
        return (" ".join(f"{b:02X}" for b in chunk) + " ") if self.show_hex.get() else text

    def _drain_ui_queue(self):
        """Tin từ luồng replay: LẤY MẪU, chỉ tin mới nhất được vẽ.

        Tin của phiên replay cũ (khác `_play_gen`) bị bỏ — Stop rồi Start lại
        không còn bị con trỏ nhảy theo dữ liệu tồn của luồng trước."""
        items, _ = bounded_drain(self._ui_q, 256, 0.004)
        last = None
        for msg in items:
            if msg[1] != self._play_gen:
                continue
            if msg[0] == "ui":
                last = msg
            elif msg[0] == "finish":
                self._finish()
            elif msg[0] == "error":
                self._set_status(msg[2])
                self.stop_replay()
                self.close_port()
        if last is not None:
            self._apply_replay_ui(*last[2:])

    def _append_log(self, text):
        """Ghi log một lần mỗi nhịp và chặn lịch sử theo dòng lẫn ký tự."""
        if not text:
            return
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self._log_lines += text.count("\n")
        self._log_chars += len(text)
        if self._log_lines > LOG_MAX_LINES:
            cut = self._log_lines - LOG_MAX_LINES
            self.log.delete("1.0", f"{cut + 1}.0")
            self._log_lines -= cut
            self._log_chars = len(self.log.get("1.0", "end-1c"))
        elif self._log_chars > LOG_MAX_CHARS:
            drop = self._log_chars - LOG_MAX_CHARS
            self.log.delete("1.0", f"1.0+{drop}c")
            self._log_chars -= drop
        if self.log_open.get():          # gập lại thì khỏi tốn công cuộn
            self.log.see("end")
        self.log.configure(state="disabled")

    def clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self._log_lines = self._log_chars = 0

    # ───────────────────────── Replay: chọn & vẽ ────────────────────────────
    def choose_csv(self):
        path = filedialog.askopenfilename(title="Chọn file CSV Roaster Scope",
                                          filetypes=[("CSV", "*.csv"), ("Tất cả", "*.*")])
        if not path:
            return
        try:
            bt_list, events, charge_bt = parse_profile(path)
        except (ValueError, OSError) as e:
            messagebox.showerror("Lỗi đọc file", str(e))
            return
        self.load_profile_data(bt_list, events, charge_bt, os.path.basename(path))

    def load_profile_data(self, bt_list, events, charge_bt, name):
        """Nạp hồ sơ đã đọc xong rồi vẽ lại.

        Tách khỏi `choose_csv` để đo hiệu năng được bằng dữ liệu giả — không cần
        hộp thoại chọn file, cũng không cần mở cổng COM."""
        self.stop_replay()
        self.profile, self.events, self.charge_bt = bt_list, events, float(charge_bt)
        self.replay_idx = 0
        self.lbl_file.configure(text=name, text_color=TEXT_STRONG)
        self.cursor.jump(0)
        self._draw_profile()

    def _draw_profile(self):
        """Vẽ lại TOÀN BỘ biểu đồ — chỉ khi dữ liệu/khung/theme đổi.

        Con trỏ replay KHÔNG nằm trong lần vẽ này: nó là artist `animated`, được
        blit riêng lên nền đã cache (xem `_blit_cursor`)."""
        col = CHART_THEME[ctk.get_appearance_mode()]
        self._bg_cache = None          # nền cũ hết giá trị ngay khi vẽ lại
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
            self.ax.axvspan(i0, i1, color=color, alpha=PHASE_ALPHA, zorder=0)
            dur = i1 - i0
            pct = dur / total * 100 if total else 0
            self.ax.text((i0 + i1) / 2, 1.015, f"{name} · {mmss(dur)} · {pct:.1f}%",
                         transform=self.ax.get_xaxis_transform(), ha="center", va="bottom",
                         fontsize=8, color="white", clip_on=False,
                         bbox=dict(boxstyle="round,pad=0.3", fc=color, ec="none"))
            parts.append(f"{name} {mmss(dur)} {pct:.0f}%")
        self.lbl_events.configure(text="   ".join(parts))

        ror = compute_ror(self.profile)
        self.ax2.plot(range(n), ror, color=col["ror"], lw=1.2, ls="--")
        # ax2.clear() kéo nhãn trục phụ về bên trái (đè lên nhãn BT) — đặt lại
        self.ax2.yaxis.set_label_position("right")
        self.ax2.yaxis.set_ticks_position("right")
        self.ax2.set_ylabel("RoR (°C/phút)", color=col["ror"], fontsize=9)
        self.ax2.tick_params(colors=col["ror"], labelsize=8)
        self.ax2.set_ylim(0, self.ror_max if self.ror_max is not None
                         else max(30, max(ror) * 1.2 if ror else 30))

        warm_secs = int(WARMUP_DROP / (WARMUP_ROR / 60.0))
        wx = list(range(-warm_secs, 1))
        wy = [self.charge_bt - WARMUP_DROP + (WARMUP_ROR / 60.0) * (s + warm_secs) for s in wx]
        self.ax.plot(wx, wy, color=col["warm"], lw=1.0, ls="--")
        self.ax.plot(range(n), self.profile, color=col["bt"], lw=2.0, zorder=3)

        # Nhãn mốc so le trên/dưới cho khỏi đè nhau khi hai mốc sát nhau
        for k, (label, idx, t2) in enumerate(self.events):
            ec = next((c for nm, a, bb, c in PHASES if a == label), col["ror"])
            dy = 15 if k % 2 == 0 else -32
            self.ax.annotate(f"{label}\n{t2}\n{self.profile[idx]:.0f}°C",
                             (idx, self.profile[idx]), textcoords="offset points",
                             xytext=(0, dy), fontsize=7, color=col["text"], ha="center", zorder=5,
                             bbox=dict(boxstyle="round,pad=0.3", fc=col["box"], ec=ec, lw=1.2))

        self._style_axes(n, col)
        self.marker = self.ax.axvline(self.cursor.current(), color=col["marker"], lw=1.6,
                                      zorder=6, animated=True)
        self.perf.full_draws += 1
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
        # Chừa chỗ cho nhãn mốc so le trên/dưới, tránh chữ dính mép
        lo, hi = self.ax.get_ylim()
        pad = (hi - lo) * 0.09 or 1.0
        self.ax.set_ylim(lo - pad, hi + pad)

    # ────────── Vòng hiển thị: blit nền cache + nội suy theo monotonic ───────
    def _draw_empty_chart(self):
        """Trạng thái rỗng: vẫn có khung và lời nhắc, không để ô trắng vô nghĩa."""
        col = CHART_THEME[ctk.get_appearance_mode()]
        self._bg_cache = None
        self.marker = None
        self.fig.set_facecolor(col["fig"])
        self.ax.clear()
        self.ax2.clear()
        self.ax.set_facecolor(col["fig"])
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.ax2.set_yticks([])
        self.ax.grid(False)
        for sp in list(self.ax.spines.values()) + list(self.ax2.spines.values()):
            sp.set_color(col["grid"])
        self.ax.text(0.5, 0.5, "Chọn file CSV hồ sơ rang để xem đường BT và RoR",
                     transform=self.ax.transAxes, ha="center", va="center",
                     fontsize=10, color=col["text"], alpha=0.75)
        self.perf.full_draws += 1
        self.canvas.draw_idle()

    def _on_mpl_draw(self, _event=None):
        """Sau MỌI lần matplotlib vẽ xong: chụp lại nền rồi đặt con trỏ lên trên.

        Đây là chỗ duy nhất sinh cache, nên mọi nguyên nhân vẽ lại (resize, đổi
        theme, đổi trần RoR, đổi hồ sơ) đều tự làm mới cache — không còn bóng
        con trỏ cũ, và vị trí replay vẫn đúng."""
        if self._in_mpl_draw:
            return
        self._in_mpl_draw = True
        try:
            self._bg_cache = self.canvas.copy_from_bbox(self.fig.bbox)
            self._bg_size = self.canvas.get_width_height()
            self._blit_cursor(self.cursor.current())
        except (RuntimeError, ValueError, AttributeError):
            self._bg_cache = None      # renderer chưa sẵn sàng → nhịp sau thử lại
        finally:
            self._in_mpl_draw = False

    def _on_canvas_resize(self, event):
        """Resize: bỏ cache ngay (kích thước khác thì restore_region sai), rồi hẹn
        vẽ lại MỘT lần sau khi người dùng thả chuột."""
        if (event.width, event.height) == self._canvas_wh:
            return
        self._canvas_wh = (event.width, event.height)
        self._bg_cache = None
        if self._resize_job is not None:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(140, self._apply_resize)

    def _apply_resize(self):
        self._resize_job = None
        if self.profile:
            self._draw_profile()
        else:
            self._draw_empty_chart()

    def _blit_cursor(self, x):
        """Vẽ lại CHỈ con trỏ trên nền đã cache — rẻ hơn draw_idle() nhiều lần."""
        if self.marker is None:
            return False
        if self._bg_cache is None:
            self.perf.skipped += 1
            return False
        # Nền chụp ở cỡ khác (vừa resize/đổi theme) mà đem blit thì chỉ tô được
        # một góc, phần còn lại trắng bệch. Bỏ nhịp này, chờ lần vẽ đầy đủ kế tiếp.
        if self._bg_size != self.canvas.get_width_height():
            self._bg_cache = None
            self.perf.skipped += 1
            return False
        t0 = time.perf_counter()
        try:
            self.canvas.restore_region(self._bg_cache)
            self.marker.set_xdata([x, x])
            self.ax.draw_artist(self.marker)
            # Chỉ đẩy vùng trục lên Tk (con trỏ bị clip trong trục): nhỏ hơn cả
            # figure nên rẻ hơn, đo được bằng tools/test_bt_display.py --bench
            self.canvas.blit(self.ax.bbox)
        except (RuntimeError, ValueError, AttributeError):
            self._bg_cache = None      # cache lệch cỡ → vẽ full một lần rồi cache lại
            self.perf.skipped += 1
            self.canvas.draw_idle()
            return False
        self.perf.add_draw(time.perf_counter() - t0)
        self._last_blit_x = x
        return True

    def _schedule_frame(self, delay_ms=FRAME_MS):
        """Hẹn nhịp vẽ kế tiếp. `delay_ms` đã TRỪ thời gian vừa làm việc, nếu
        không nhịp thực sẽ bị trôi: Tk trên Windows chỉ thức theo mốc ~15,6 ms
        nên 16 ms cộng thêm 2 ms vẽ là nhảy sang mốc sau (≈31 ms/khung)."""
        if self._frame_job is None:
            self._frame_job = self.after(max(1, int(delay_ms)), self._on_frame)

    def _on_frame(self):
        """Nhịp vẽ: nội suy vị trí con trỏ theo `time.monotonic` rồi blit.

        Vòng này chỉ sống khi con trỏ còn phải di chuyển hoặc replay còn chạy —
        lúc nghỉ KHÔNG đốt CPU cho 60 khung/giây vô ích."""
        self._frame_job = None
        now = time.monotonic()
        t_start = time.perf_counter()
        self.perf.tick(now)
        x, moving = self.cursor.value(now)
        # Con trỏ đứng yên (tốc độ chậm, pha CĂN BT) thì khỏi blit lại cho tốn công
        if moving or self._last_blit_x is None or abs(x - self._last_blit_x) > 1e-6:
            self._blit_cursor(x)
        if moving or self.playing:
            used_ms = (time.perf_counter() - t_start) * 1000.0
            self._schedule_frame(FRAME_MS - used_ms)
        else:
            self.perf.gap()            # nghỉ → đừng tính khoảng trống thành nhịp

    def perf_snapshot(self):
        """Móc đo: số khung, nhịp callback và thời gian blit thực tế (ms).

        Dùng được mà không cần mở COM — xem `tools/test_bt_display.py --bench`."""
        return self.perf.snapshot()

    def _show_perf(self, _event=None):
        """F9 — in số đo hiệu năng ra log và thanh trạng thái."""
        line = self.perf.summary()
        self._append_log("» perf " + line + "\n")
        self._set_status(line)

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
        # Luồng của phiên trước phải chết hẳn, và tin còn tồn của nó bị vô hiệu,
        # nếu không con trỏ sẽ giật theo dữ liệu cũ ngay sau khi Start lại.
        self._join_play_thread()
        self._play_gen += 1
        self._stop_evt.clear()
        self.playing = True
        self.phase = "align"        # căn BT về điểm bắt đầu warmup trước
        self.warm_target = self.charge_bt - WARMUP_DROP
        self.replay_idx = 0
        self.bt_offset = 0.0
        self.lbl_offset.configure(text="+0.0")
        self.ror_kalman.reset()
        self.ror_count = 0
        self.ror_samp1 = None
        self.rorBT = 0
        self.btn_play.configure(state="disabled")
        self.cursor.jump(-int(WARMUP_DROP / (WARMUP_ROR / 60.0)))
        self.play_thread = threading.Thread(target=self._play_loop,
                                            args=(self._play_gen,), daemon=True)
        self.play_thread.start()
        self._schedule_frame()

    def _join_play_thread(self):
        """Chờ luồng replay cũ thoát (không bao giờ tự join chính nó)."""
        t, self.play_thread = self.play_thread, None
        if t is not None and t is not threading.current_thread():
            t.join(timeout=1.5)

    def stop_replay(self):
        self.playing = False
        self._stop_evt.set()       # đánh thức luồng đang đợi, khỏi chờ hết nhịp
        self._join_play_thread()
        self._play_gen += 1        # tin của phiên vừa dừng coi như không còn
        self.phase = "idle"
        self.btn_play.configure(state="normal")
        self.lbl_phase.configure(text="Dừng")

    def reset_replay(self):
        self.stop_replay()
        self.replay_idx = 0
        self.rorBT = 0
        self.bt_offset = 0.0
        self.lbl_offset.configure(text="+0.0")
        self.lbl_bt.configure(text="—")
        self.lbl_ror.configure(text="—")
        self.lbl_phase.configure(text="—")
        if self.profile:
            self.cursor.jump(0)
            self._blit_cursor(0)

    # ──────────────── Cài đặt lưu lại + trần cột RoR của đồ thị ─────────────
    def _save_cfg(self):
        """Ghi cài đặt ra file cạnh exe. Ghi hỏng (thư mục chỉ đọc) thì bỏ qua,
        app vẫn chạy — chỉ mất phần nhớ giữa hai lần mở."""
        self.cfg.update({"ror_max": self.ror_max, "speed": self.speed})
        self.cfg["log_open"] = bool(self.log_open.get())
        save_settings(self.cfg)

    @staticmethod
    def _parse_ror_max(text):
        """'35' / '35 °C/phút' → 35.0; 'Tự động' / rỗng → 'auto'; đọc không ra → None."""
        s = str(text).strip().lower().replace(",", ".")
        if s in ("", "-", "auto", "tự động", "tu dong", "tự co", "tudong"):
            return "auto"
        m = re.search(r"[0-9]*\.?[0-9]+", s)
        if not m:
            return None
        v = float(m.group())
        if v <= 0:
            return None
        return max(ROR_MAX_MIN, min(ROR_MAX_MAX, v))

    def _set_ror_max(self, v, rewrite=True):
        self.ror_max = None if v == "auto" else float(v)
        if rewrite:
            self.opt_rormax.set(ROR_AUTO_TEXT if self.ror_max is None else fmt_num(self.ror_max))
        self._save_cfg()
        if self.profile:
            self._draw_profile()

    def commit_ror_max(self, _value=None):
        if self._rormax_job is not None:
            self.after_cancel(self._rormax_job)
            self._rormax_job = None
        v = self._parse_ror_max(self.opt_rormax.get())
        if v is None:
            v = "auto" if self.ror_max is None else self.ror_max
        self._set_ror_max(v)

    def _rormax_typed(self, event=None):
        if event is not None and event.keysym in ("Return", "KP_Enter", "Tab"):
            return
        if self._rormax_job is not None:
            self.after_cancel(self._rormax_job)
        self._rormax_job = self.after(SPEED_TYPING_MS, self._rormax_typed_apply)

    def _rormax_typed_apply(self):
        self._rormax_job = None
        v = self._parse_ror_max(self.opt_rormax.get())
        if v is not None:
            self._set_ror_max(v, rewrite=False)

    def nudge_ror_max(self, delta):
        """Đang để Tự động mà bấm −/+ thì bắt đầu từ trần mặc định."""
        base = self._parse_ror_max(self.opt_rormax.get())
        if base is None or base == "auto":
            base = ROR_MAX_DEFAULT
        self._set_ror_max(max(ROR_MAX_MIN, min(ROR_MAX_MAX, round(base + delta, 1))))

    def _rormax_wheel(self, event):
        self.nudge_ror_max(ROR_MAX_NUDGE if event.delta > 0 else -ROR_MAX_NUDGE)
        return "break"

    # ─────────────────────── Tốc độ replay (giá trị tự do) ──────────────────
    @staticmethod
    def _parse_speed(text):
        """'x0.85' / '0,85' / '85%' → 0.85. Không đọc được → None."""
        s = str(text).strip().lower().replace(",", ".").lstrip("x×").strip()
        pct = s.endswith("%")
        if pct:
            s = s[:-1].strip()
        try:
            v = float(s)
        except ValueError:
            return None
        if pct:
            v /= 100.0
        if v <= 0:
            return None
        return max(SPEED_MIN, min(SPEED_MAX, v))

    def _set_speed(self, v, rewrite=True):
        """Áp dụng tốc độ mới. rewrite=False khi đang gõ dở, để không nhảy con trỏ."""
        self.speed = v
        if rewrite:
            self.opt_speed.set(fmt_speed(v))
        self.lbl_speed.configure(text=f"1 giây hồ sơ = {1.0 / v:.2f}s thật")
        self._save_cfg()

    def commit_speed(self, _value=None):
        """Chốt giá trị trong ô: gõ sai thì trả về tốc độ đang chạy."""
        if self._speed_job is not None:
            self.after_cancel(self._speed_job)
            self._speed_job = None
        v = self._parse_speed(self.opt_speed.get())
        self._set_speed(self.speed if v is None else v)

    def _speed_typed(self, event=None):
        """Gõ tới đâu áp tới đó, nhưng chờ ngừng gõ để khỏi ăn số dang dở."""
        if event is not None and event.keysym in ("Return", "KP_Enter", "Tab"):
            return
        if self._speed_job is not None:
            self.after_cancel(self._speed_job)
        self._speed_job = self.after(SPEED_TYPING_MS, self._speed_typed_apply)

    def _speed_typed_apply(self):
        self._speed_job = None
        v = self._parse_speed(self.opt_speed.get())
        if v is not None:
            self._set_speed(v, rewrite=False)

    def nudge_speed(self, delta):
        base = self._parse_speed(self.opt_speed.get())
        if base is None:
            base = self.speed
        self._set_speed(max(SPEED_MIN, min(SPEED_MAX, round(base + delta, 2))))

    def _speed_wheel(self, event):
        self.nudge_speed(SPEED_NUDGE if event.delta > 0 else -SPEED_NUDGE)
        return "break"

    # ───────────────── Luồng replay (KHÔNG được gọi Tk ở đây) ───────────────
    def _tx(self, data, gen):
        """Gửi từ luồng replay. Lỗi thì báo về UI qua queue, TUYỆT ĐỐI không mở
        messagebox hay sờ widget (gọi Tk ngoài main thread là treo app).
        Trả False nghĩa là luồng phải thoát."""
        try:
            self.sm.write(data)
        except (serial.SerialException, OSError, AttributeError, TypeError) as e:
            self._ui_q.put(("error", gen, f"Lỗi gửi: {e}"))
            return False
        return True

    def _post(self, gen, target, x_pos, phase_txt, step_s):
        """Đẩy một tin trạng thái về UI. `step_s` cho con trỏ biết phải trượt
        tới mốc mới trong bao lâu — nhờ đó vẽ mượt mà KHÔNG tăng nhịp gửi lệnh."""
        self._ui_q.put(("ui", gen, target, x_pos, phase_txt, self.rorBT, step_s))

    def _play_loop(self, gen):
        """Phát lại hồ sơ: mỗi nhịp gửi đúng một bước lệnh như cũ.

        Mọi lần nghỉ đều qua `_stop_evt.wait()` nên bấm Stop là tỉnh ngay, không
        phải chờ hết 1 giây hồ sơ."""
        warm_secs = int(WARMUP_DROP / (WARMUP_ROR / 60.0))
        while not self._stop_evt.is_set():
            speed = self.speed          # đã chốt sẵn ở luồng UI, đọc là dùng
            if self.dev_bt is None:
                if not self._tx(b"1", gen):
                    return
                if self._stop_evt.wait(0.3):
                    return
                continue

            # Pha CĂN BT: kéo BT thiết bị về điểm bắt đầu warmup theo từng bước nhỏ
            # (≤ MAX_STEP_TENTHS mỗi nhịp) để KHÔNG gửi cả chuỗi lệnh lớn một lần —
            # đây là nguyên nhân thiết bị/Modbus lỗi 1 nhịp ngay lúc Start.
            if self.phase == "align":
                target = self.charge_bt - WARMUP_DROP
                delta = round((target - self.dev_bt) * 10)
                step = max(-MAX_STEP_TENTHS, min(MAX_STEP_TENTHS, delta))
                if step:
                    if not self._tx(compose_commands(step).encode("ascii"), gen):
                        return
                    self.dev_bt = round(self.dev_bt + step / 10.0, 1)
                self._post(gen, self.dev_bt, -warm_secs, "CĂN BT", 0.08)
                if abs(delta) <= MAX_STEP_TENTHS:
                    self.phase = "warmup"
                    self.warm_target = self.charge_bt - WARMUP_DROP
                if self._stop_evt.wait(0.08):
                    return
                continue

            if self.phase == "warmup":
                target = self.warm_target
                x_pos = -int((self.charge_bt - self.warm_target) / (WARMUP_ROR / 60.0))
                phase_txt = "HÂM"
            else:
                if self.replay_idx >= len(self.profile):
                    self._ui_q.put(("finish", gen))
                    return
                target = self.profile[self.replay_idx]
                x_pos = self.replay_idx
                phase_txt = "REPLAY"

            target += self.bt_offset        # can thiệp tay (offset bền)
            # Giới hạn bước mỗi nhịp để tránh dồn chuỗi lệnh lớn (vd offset bump to)
            delta_tenths = max(-MAX_STEP_TENTHS, min(MAX_STEP_TENTHS, round((target - self.dev_bt) * 10)))
            if delta_tenths:
                if not self._tx(compose_commands(delta_tenths).encode("ascii"), gen):
                    return
                self.dev_bt = round(self.dev_bt + delta_tenths / 10.0, 1)

            self._update_ror(target)
            # Mốc kế tiếp là x_pos + 1 và nó tới sau đúng một nhịp → con trỏ trượt
            # liên tục trong khoảng đó thay vì nhảy từng bậc.
            self._post(gen, target, x_pos + 1, phase_txt, 1.0 / speed)

            if self.phase == "warmup":
                self.warm_target += WARMUP_ROR / 60.0
                if self.warm_target >= self.charge_bt:
                    self.warm_target = self.charge_bt
                    self.phase = "replay"
                    self.replay_idx = 0
            else:
                self.replay_idx += 1
            if self._stop_evt.wait(1.0 / speed):
                return

    def bump_bt(self, deg):
        """Can thiệp BT bằng bước độ nguyên. Đang replay → cộng offset bền;
        đang rảnh → gửi lệnh dời BT thiết bị ngay."""
        if not self.sm.is_open():
            messagebox.showwarning("Chưa mở cổng", "Hãy Open cổng COM trước")
            return
        if self.playing:
            self.bt_offset += deg
            self.lbl_offset.configure(text=f"{self.bt_offset:+.1f}")
        else:
            self._write(compose_commands(deg * 10).encode("ascii"), "")
            if self.dev_bt is not None:
                self.dev_bt = round(self.dev_bt + deg, 1)

    def _update_ror(self, target):
        units = round(target * 10)
        if self.ror_samp1 is None:
            self.ror_samp1 = units
        self.ror_count += 1
        if self.ror_count >= 3:
            raw = (units - self.ror_samp1) * 20
            self.rorBT = max(-200, min(200, int(self.ror_kalman.update(raw))))
            self.ror_samp1 = units
            self.ror_count = 0

    def _apply_replay_ui(self, target, x_pos, phase_txt, ror, step_s):
        """Chạy trên main thread, nhận tin đã lấy mẫu từ `_ui_q`.

        Chỉ đặt mốc cho con trỏ rồi bật vòng vẽ; việc di chuyển do `_on_frame`
        nội suy nên tin đến 1 lần/giây vẫn cho chuyển động liên tục."""
        self.lbl_phase.configure(text=phase_txt)
        self.lbl_bt.configure(text=f"{target:.1f}")
        self.lbl_ror.configure(text=f"{ror / 10:+.1f}")
        self.cursor.target(x_pos, step_s)
        self._schedule_frame()

    def _finish(self):
        self.playing = False
        self._stop_evt.set()
        self._join_play_thread()
        self._play_gen += 1
        self.phase = "idle"
        self.btn_play.configure(state="normal")
        self.lbl_phase.configure(text="Xong ✓")

    # ───────────────────────────── Theme & thoát ────────────────────────────
    def _on_theme(self, mode):
        ctk.set_appearance_mode(mode)
        self._refresh_gradient()
        # Đổi theme phải vẽ lại cả lúc chưa có hồ sơ, và cache nền sẽ tự làm mới
        # trong draw_event — nếu không con trỏ còn giữ màu của theme cũ.
        if self.profile:
            self._draw_profile()
        else:
            self._draw_empty_chart()

    def _on_close(self):
        self.playing = False
        self._stop_evt.set()
        self._join_play_thread()
        for job in (self._speed_job, self._rormax_job,    # hẹn giờ còn treo → huỷ
                    self._frame_job, self._resize_job):
            if job is not None:
                self.after_cancel(job)
        if self._hi_res_timer:
            set_timer_resolution(False)
        self.sm.close()
        self.destroy()


def main():
    app = App()
    # Cửa cho MCP/API lái app từ ngoài. Phải bật SAU khi App dựng xong widget
    # (server đọc opt_port/opt_baud), và trước mainloop. Hỏng thì bỏ qua —
    # BT Tester vẫn phải chạy được khi không có server điều khiển.
    try:
        import bt_control_server
    except ImportError:
        from tools import bt_control_server
    _server, cong = bt_control_server.khoi_dong(app)
    if cong:
        app._bt_api_port = cong
    app.mainloop()


if __name__ == "__main__":
    main()


# ════════════════════════════════════════════════════════════════════════════
#  CÀI ĐẶT & ĐÓNG GÓI
# ════════════════════════════════════════════════════════════════════════════
#  Cài thư viện:
#      pip install customtkinter pyserial matplotlib pillow
#
#  File này import `bt_display_loop.py` nằm CÙNG thư mục tools/ (vòng vẽ + móc đo).
#  PyInstaller tự theo import đó vì thư mục của script được đưa vào đường tìm kiếm;
#  nếu bản build báo thiếu module thì thêm `--paths tools` (hoặc `pathex` trong
#  tools/BTSerialTester.spec). Đo hiệu năng không cần COM:
#      python tools/test_bt_display.py            (kiểm thử logic, không mở cửa sổ)
#      python tools/test_bt_display.py --bench    (mở app, hồ sơ giả, in số đo)
#  Trong app đang chạy: bấm F9 để in số đo vào log.
#
#  Build exe onefile. Gradient nền vẽ bằng code (Pillow). customtkinter BẮT BUỘC
#  --collect-all để kèm asset theme .json. Icon: --icon cho exe + --add-data để
#  iconbitmap cửa sổ tìm được file lúc onefile:
#      python -m PyInstaller --onefile --windowed --name BTSerialTester ^
#          --collect-all customtkinter ^
#          --icon tools/bt_icon.ico ^
#          --add-data "tools/bt_icon.ico;." ^
#          tools/bt_serial_tester_glass.py
#
#  (Git Bash: thay ^ bằng \ để nối dòng, hoặc viết trên 1 dòng.)
#
#  TODO (nếu thiết bị khác bộ lệnh): chuỗi mỗi nút BT gửi đi hiện wired theo
#  firmware giả lập ('1'=+0.1 … 'r'=-1.0). Sửa UP_CMDS/DOWN_CMDS/UP_STEPS/
#  DOWN_STEPS ở đầu file nếu cần.
