"""
OTL Serial Terminal — Liquid Glass (iOS 26 / macOS Tahoe style).

Terminal serial đa năng kiểu Hercules SETUP utility, nhưng giao diện Liquid Glass:
nền gradient có chiều sâu (vẽ bằng Pillow trên Canvas), các khu chức năng là "card
kính" nổi trên nền, bo góc lớn nhất quán, logo OTL ở góc trên.

So với Hercules:
  • Cấu hình cổng: Baud, Data, Parity, Stop, Handshake (chạy thật qua pyserial).
  • Cổng COM HIỆN ĐẦY ĐỦ THÔNG TIN: device, mô tả, nhà sản xuất, sản phẩm,
    VID:PID, serial number, vị trí (USB hub/port) — card "Thông tin cổng" riêng.
  • Cửa sổ Received/Sent gộp chung, tô màu RX/TX, bật/tắt HEX, timestamp.
  • 3 dòng Send độc lập, mỗi dòng có HEX + EOL + nút Send (giống Hercules).
  • Đèn modem lines: CD/RI/DSR/CTS (đọc) và DTR/RTS (bấm để bật/tắt).

Logic serial tách trong SerialManager (đọc trên thread riêng, đẩy về UI qua queue
— tkinter không an toàn đa luồng).

Cài lib + build: xem comment cuối file.
"""

import os
import sys
import queue
import threading
import time
import tkinter as tk
from tkinter import messagebox

import serial
import serial.tools.list_ports

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont, ImageTk


def resource_path(name):
    """Đường dẫn tài nguyên, chạy được cả khi đóng gói PyInstaller (--onefile)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


# ════════════════════════════════════════════════════════════════════════════
#  BẢNG MÀU & HÌNH HỌC (Liquid Glass). Màu dạng (light, dark) để CTk tự đổi.
# ════════════════════════════════════════════════════════════════════════════
GLASS_CARD = ("#FFFFFF", "#2C2C2E")        # lớp kính chính
GLASS_INNER = ("#F6F6FB", "#242426")       # card lồng bên trong
CARD_BORDER = ("#E6E6EC", "#3A3A3C")       # viền mảnh tách card khỏi nền
TEXT_STRONG = ("#1D1D1F", "#F5F5F7")
TEXT_SUB = ("#86868B", "#98989D")
LOG_BG = ("#F4F4F8", "#1C1C1E")
FIELD_BG = ("#EFEFF4", "#3A3A3C")
FIELD_HOVER = ("#E2E2EA", "#48484A")
PILL_BG = ("#EFEFF4", "#3A3A3C")
BLUE, BLUE_HOVER = "#007AFF", "#0051D5"
GREEN, GREEN_HOVER = "#34C759", "#2EB14F"
RED, RED_HOVER = "#FF3B30", "#E0322A"
ORANGE = "#FF9500"
GREY_DOT = "#8E8E93"

# Gradient nền (top, bottom) — xanh→tím rất nhạt / xám than
GRAD_LIGHT = ((233, 238, 251), (244, 239, 250))
GRAD_DARK = ((26, 28, 34), (14, 15, 19))

# Màu log RX/TX cho 2 mode
RX_COLOR = {"Light": "#0A7D2C", "Dark": "#32D74B"}
TX_COLOR = {"Light": "#0051D5", "Dark": "#0A84FF"}
SYS_COLOR = {"Light": "#86868B", "Dark": "#98989D"}

R_CARD, R_BTN, R_FIELD, R_LOG, R_PILL = 18, 12, 9, 14, 16

# Vùng data luôn chiếm tỉ lệ này theo chiều cao cửa sổ (mọi độ phân giải)
DATA_RATIO = 0.70
DATA_RATIO_MINSIZE = 320       # minsize khởi tạo, sẽ được _on_resize cập nhật theo 70%
FONT_FAMILY = "Segoe UI"
MONO_FAMILY = "Consolas"

BAUD_OPTIONS = ["300", "1200", "2400", "4800", "9600", "14400", "19200",
                "38400", "57600", "115200", "230400"]
DATABITS = {"5": serial.FIVEBITS, "6": serial.SIXBITS, "7": serial.SEVENBITS, "8": serial.EIGHTBITS}
PARITY = {"None": serial.PARITY_NONE, "Even": serial.PARITY_EVEN, "Odd": serial.PARITY_ODD,
          "Mark": serial.PARITY_MARK, "Space": serial.PARITY_SPACE}
STOPBITS = {"1": serial.STOPBITS_ONE, "1.5": serial.STOPBITS_ONE_POINT_FIVE, "2": serial.STOPBITS_TWO}
# Handshake → kwargs flow control của pyserial
HANDSHAKE = {
    "None": dict(rtscts=False, xonxoff=False, dsrdtr=False),
    "RTS/CTS": dict(rtscts=True, xonxoff=False, dsrdtr=False),
    "XON/XOFF": dict(rtscts=False, xonxoff=True, dsrdtr=False),
    "DSR/DTR": dict(rtscts=False, xonxoff=False, dsrdtr=True),
}
EOL_MAP = {"(không)": b"", "\\n": b"\n", "\\r": b"\r", "\\r\\n": b"\r\n"}


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


def load_logo(size=44):
    """Nạp biểu tượng OTL đã crop vuông (otl_symbol.png) — chỉ phần đỏ + đầu dò,
    bỏ chữ để nhỏ vẫn nét. Thiếu file thì rơi về logo vẽ tay (draw_logo)."""
    path = resource_path("otl_symbol.png")
    if not os.path.exists(path):
        return draw_logo(size)
    img = Image.open(path).convert("RGBA").resize((size, size), Image.LANCZOS)
    return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))


def draw_logo(size=40):
    """Vẽ logo OTL dự phòng: huy hiệu bo góc gradient xanh, chữ 'OTL' trắng đậm."""
    scale = 4
    s = size * scale
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Nền gradient chéo xanh dương → xanh lam
    top, bot = (10, 132, 255), (0, 81, 213)
    for y in range(s):
        t = y / (s - 1)
        c = tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3))
        d.line([(0, y), (s, y)], fill=c)
    # Mặt nạ bo góc
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, s - 1, s - 1], radius=int(s * 0.26), fill=255)
    img.putalpha(mask)
    # Chữ OTL
    txt = "OTL"
    font = None
    for name in ("segoeuib.ttf", "arialbd.ttf", "Helvetica.ttf"):
        try:
            font = ImageFont.truetype(name, int(s * 0.38))
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()
    bbox = d.textbbox((0, 0), txt, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((s - tw) / 2 - bbox[0], (s - th) / 2 - bbox[1]), txt, font=font, fill="white")
    img = img.resize((size, size), Image.LANCZOS)
    return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))


def port_record(device):
    """Trả về ListPortInfo của 1 cổng theo device, hoặc None."""
    for p in serial.tools.list_ports.comports():
        if p.device == device:
            return p
    return None


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
        """[(device, label đầy đủ)] — label gồm mô tả để chọn dễ."""
        out = []
        for p in serial.tools.list_ports.comports():
            desc = (p.description or "").strip()
            tail = f"({p.device})"
            if desc.endswith(tail):
                desc = desc[: -len(tail)].strip()
            label = f"{p.device} — {desc}" if desc and desc.lower() != "n/a" else p.device
            out.append((p.device, label))
        return out

    def open(self, port, baud, bytesize, parity, stopbits, flow):
        self.ser = serial.Serial(port=port, baudrate=baud, bytesize=bytesize,
                                 parity=parity, stopbits=stopbits, timeout=0.2, **flow)
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

    def modem_lines(self):
        """(cd, ri, dsr, cts) đọc từ cổng, hoặc None nếu chưa mở."""
        if not self.ser:
            return None
        try:
            return (self.ser.cd, self.ser.ri, self.ser.dsr, self.ser.cts)
        except (serial.SerialException, OSError):
            return None

    def set_dtr(self, val):
        if self.ser:
            self.ser.dtr = val

    def set_rts(self, val):
        if self.ser:
            self.ser.rts = val

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
        self.title("OTL Serial Terminal")
        self.geometry("1100x1000")
        self.minsize(960, 620)
        try:                       # icon cửa sổ (taskbar/title bar)
            self.iconbitmap(resource_path("otl_icon.ico"))
        except tk.TclError:
            pass

        self.f_title = ctk.CTkFont(FONT_FAMILY, 22, "bold")
        self.f_section = ctk.CTkFont(FONT_FAMILY, 15, "bold")
        self.f_label = ctk.CTkFont(FONT_FAMILY, 11)
        self.f_body = ctk.CTkFont(FONT_FAMILY, 13)
        self.f_btn = ctk.CTkFont(FONT_FAMILY, 14, "bold")
        self.f_mono = ctk.CTkFont(MONO_FAMILY, 12)
        self.f_mono_sm = ctk.CTkFont(MONO_FAMILY, 11)

        self.sm = SerialManager()
        self.port_map = {}
        self.show_hex = tk.BooleanVar(value=False)
        self.echo_on = tk.BooleanVar(value=True)
        self.show_ts = tk.BooleanVar(value=False)
        self.autoscroll = tk.BooleanVar(value=True)
        self.dtr_var = tk.BooleanVar(value=False)
        self.rts_var = tk.BooleanVar(value=False)
        self.info_shown = tk.BooleanVar(value=False)   # panel Thông tin/Modem mặc định thu gọn
        self.send_rows = []        # (entry, hex_var, eol_menu)
        self._need_ts = True       # sắp tới là đầu dòng → cần chèn timestamp
        self._bgimg = None
        self.logo_img = load_logo(44)
        self.modem_lbls = {}

        self._build_ui()
        self.refresh_ports()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(50, self._poll_rx)
        self.after(200, self._poll_modem)

    # ───────────────────────── Khối UI dùng lại ─────────────────────────────
    def _card(self, parent, inner=False, **kw):
        return ctk.CTkFrame(parent, fg_color=GLASS_INNER if inner else GLASS_CARD,
                            corner_radius=R_CARD, border_width=1, border_color=CARD_BORDER, **kw)

    def _field(self, parent, label_text):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        ctk.CTkLabel(f, text=label_text.upper(), font=self.f_label,
                     text_color=TEXT_SUB).pack(anchor="w", padx=2, pady=(0, 2))
        return f

    def _menu(self, parent, values, default, width=92):
        opt = ctk.CTkOptionMenu(parent, values=values, width=width, height=32, corner_radius=R_FIELD,
                                font=self.f_body, fg_color=FIELD_BG, button_color=FIELD_BG,
                                text_color=TEXT_STRONG, button_hover_color=FIELD_HOVER,
                                dropdown_font=self.f_body, dropdown_fg_color=GLASS_CARD,
                                dropdown_text_color=TEXT_STRONG)
        opt.set(default)
        return opt

    # ───────────────────────────── Dựng UI ──────────────────────────────────
    def _build_ui(self):
        # Nền gradient: Canvas phủ toàn cửa sổ (nằm DƯỚI card). Card là con trực
        # tiếp của root, grid lên trên — khoảng hở giữa card lộ gradient.
        self.bg = tk.Canvas(self, highlightthickness=0, bd=0)
        self.bg.place(x=0, y=0, relwidth=1, relheight=1)
        self.grid_columnconfigure(0, weight=1)
        # Hàng 2 = vùng data; weight cho nở, minsize ép = 70% chiều cao (xem _on_resize)
        self.grid_rowconfigure(2, weight=1, minsize=DATA_RATIO_MINSIZE)

        self._build_toolbar()
        self._build_mid_row()
        self._build_log_card()
        self._build_send_card()
        self._refresh_gradient()
        # Sau khi layout xong: tính chiều cao tối thiểu để data luôn giữ được 70%
        self.after(80, self._setup_data_ratio)

    def _build_toolbar(self):
        # Gộp logo + tiêu đề + toàn bộ cấu hình cổng vào MỘT thanh gọn (tiết kiệm
        # chiều cao để nhường cho vùng data).
        card = self._card(self)
        card.grid(row=0, column=0, sticky="ew", padx=24, pady=(16, 5))
        card.grid_columnconfigure(0, weight=1)
        self.toolbar_card = card

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=16, pady=(10, 2))
        top.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(top, text="", image=self.logo_img).grid(row=0, column=0, padx=(0, 10))
        ctk.CTkLabel(top, text="OTL Serial Terminal", font=self.f_title,
                     text_color=TEXT_STRONG).grid(row=0, column=1, sticky="w")
        ctk.CTkSwitch(top, text="Thông tin cổng & Modem", font=self.f_body, variable=self.info_shown,
                      progress_color=BLUE, command=self._toggle_info).grid(row=0, column=2, sticky="e", padx=(0, 14))
        self.seg_theme = ctk.CTkSegmentedButton(top, values=["Light", "Dark"], font=self.f_label,
                                                 corner_radius=R_BTN, selected_color=BLUE,
                                                 selected_hover_color=BLUE_HOVER, command=self._on_theme)
        self.seg_theme.set("Light")
        self.seg_theme.grid(row=0, column=3, sticky="e")

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.grid(row=1, column=0, sticky="ew", padx=16, pady=(2, 12))
        row.grid_columnconfigure(0, weight=1)

        com = self._field(row, "Cổng COM")
        com.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        inner = ctk.CTkFrame(com, fg_color="transparent")
        inner.pack(fill="x")
        self.opt_port = self._menu(inner, ["(quét...)"], "(quét...)", width=230)
        self.opt_port.configure(command=lambda _=None: self._show_port_info())
        self.opt_port.pack(side="left", fill="x", expand=True)
        # Mỗi lần bấm mở dropdown COM → tự quét lại cổng (bọc hàm mở của CTkOptionMenu)
        _orig_open = self.opt_port._open_dropdown_menu
        def _open_with_rescan():
            self.refresh_ports()
            _orig_open()
        self.opt_port._open_dropdown_menu = _open_with_rescan
        ctk.CTkButton(inner, text="⟳", width=34, height=32, corner_radius=R_FIELD, font=self.f_btn,
                      fg_color=FIELD_BG, text_color=TEXT_STRONG, hover_color=FIELD_HOVER,
                      command=self.refresh_ports).pack(side="left", padx=(8, 0))

        for c, (label, values, default) in enumerate([
                ("Baud", BAUD_OPTIONS, "9600"), ("Data", list(DATABITS), "8"),
                ("Parity", list(PARITY), "None"), ("Stop", list(STOPBITS), "1"),
                ("Handshake", list(HANDSHAKE), "None")], start=1):
            f = self._field(row, label)
            f.grid(row=0, column=c, sticky="w", padx=6)
            m = self._menu(f, values, default, width=100 if label == "Handshake" else 78)
            m.pack()
            setattr(self, f"opt_{label.lower()}", m)

        self.btn_open = ctk.CTkButton(row, text="Open", font=self.f_btn, width=96, height=46,
                                      corner_radius=R_BTN, fg_color=BLUE, hover_color=BLUE_HOVER,
                                      command=self.toggle_open)
        self.btn_open.grid(row=0, column=6, sticky="s", padx=(10, 6), pady=(0, 1))

        pill = ctk.CTkFrame(row, fg_color=PILL_BG, corner_radius=R_PILL)
        pill.grid(row=0, column=7, sticky="s", padx=(2, 0), pady=(0, 5))
        self.pill_dot = ctk.CTkLabel(pill, text="●", font=self.f_body, text_color=GREY_DOT)
        self.pill_dot.pack(side="left", padx=(10, 4), pady=6)
        self.pill_txt = ctk.CTkLabel(pill, text="Chưa kết nối", font=self.f_body, text_color=TEXT_STRONG)
        self.pill_txt.pack(side="left", padx=(0, 12))

    def _setup_data_ratio(self):
        """Gắn ràng buộc động: data = 70% chiều cao, nhưng không bao giờ đè lên Send."""
        self.bind("<Configure>", self._on_resize)
        self._on_resize(None)

    def _on_resize(self, event):
        if event is not None and event.widget is not self:
            return
        h = self.winfo_height()
        # chrome = các khối ngoài data đang hiển thị (đo chiều cao yêu cầu thực tế)
        chrome = self.toolbar_card.winfo_reqheight() + self.send_card.winfo_reqheight() + 64
        if self.info_shown.get():
            chrome += self.mid_wrap.winfo_reqheight() + 8
        # ép data = 70%, nhưng nếu cửa sổ thấp thì chỉ lấy phần còn dư (Send không bị cắt)
        data_min = min(int(h * DATA_RATIO), h - chrome)
        self.grid_rowconfigure(2, minsize=max(140, data_min))

    def _toggle_info(self):
        if self.info_shown.get():
            self.mid_wrap.grid()
        else:
            self.mid_wrap.grid_remove()
        self._on_resize(None)

    def _build_mid_row(self):
        wrap = ctk.CTkFrame(self, fg_color="transparent")
        wrap.grid(row=1, column=0, sticky="ew", padx=24, pady=(4, 4))
        wrap.grid_columnconfigure(0, weight=3)
        wrap.grid_columnconfigure(1, weight=2)
        self.mid_wrap = wrap
        wrap.grid_remove()              # mặc định thu gọn để data đạt 70%

        # ── Card thông tin cổng (đầy đủ) ──
        info = self._card(wrap)
        info.grid(row=0, column=0, sticky="nsew", padx=(0, 9))
        info.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(info, text="Thông tin cổng", font=self.f_section,
                     text_color=TEXT_STRONG).grid(row=0, column=0, sticky="w", padx=20, pady=(10, 2))
        self.info_box = ctk.CTkTextbox(info, font=self.f_mono_sm, fg_color=LOG_BG, corner_radius=R_LOG,
                                       text_color=TEXT_STRONG, wrap="word", height=56)
        self.info_box.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 12))
        self.info_box.configure(state="disabled")

        # ── Card modem lines ──
        modem = self._card(wrap)
        modem.grid(row=0, column=1, sticky="nsew", padx=(9, 0))
        modem.grid_columnconfigure((0, 1, 2, 3), weight=1)
        ctk.CTkLabel(modem, text="Modem lines", font=self.f_section,
                     text_color=TEXT_STRONG).grid(row=0, column=0, columnspan=4, sticky="w",
                                                   padx=20, pady=(10, 2))
        # Đèn đọc (input): CD RI DSR CTS
        for i, name in enumerate(("CD", "RI", "DSR", "CTS")):
            cell = ctk.CTkFrame(modem, fg_color="transparent")
            cell.grid(row=1, column=i, pady=(0, 4))
            dot = ctk.CTkLabel(cell, text="●", font=self.f_section, text_color=GREY_DOT)
            dot.pack()
            ctk.CTkLabel(cell, text=name, font=self.f_label, text_color=TEXT_SUB).pack()
            self.modem_lbls[name] = dot
        # Toggle ghi (output): DTR RTS
        ctk.CTkSwitch(modem, text="DTR", font=self.f_body, variable=self.dtr_var,
                      progress_color=BLUE, command=lambda: self.sm.set_dtr(self.dtr_var.get())).grid(
                          row=2, column=0, columnspan=2, padx=20, pady=(0, 12), sticky="w")
        ctk.CTkSwitch(modem, text="RTS", font=self.f_body, variable=self.rts_var,
                      progress_color=BLUE, command=lambda: self.sm.set_rts(self.rts_var.get())).grid(
                          row=2, column=2, columnspan=2, padx=8, pady=(0, 12), sticky="w")

    def _build_log_card(self):
        card = self._card(self)
        card.grid(row=2, column=0, sticky="nsew", padx=24, pady=(5, 5))
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)

        head = ctk.CTkFrame(card, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 4))
        head.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(head, text="Received / Sent data", font=self.f_section,
                     text_color=TEXT_STRONG).grid(row=0, column=0, sticky="w")
        ctk.CTkSwitch(head, text="HEX", font=self.f_body, variable=self.show_hex,
                      progress_color=BLUE).grid(row=0, column=1, padx=10)
        ctk.CTkSwitch(head, text="Timestamp", font=self.f_body, variable=self.show_ts,
                      progress_color=BLUE, command=self._toggle_ts).grid(row=0, column=2, padx=10)
        ctk.CTkSwitch(head, text="Echo TX", font=self.f_body, variable=self.echo_on,
                      progress_color=BLUE).grid(row=0, column=3, padx=10)
        ctk.CTkSwitch(head, text="Tự cuộn", font=self.f_body, variable=self.autoscroll,
                      progress_color=BLUE).grid(row=0, column=4, padx=10)
        self.btn_copy = ctk.CTkButton(head, text="Copy", font=self.f_body, width=64, height=30,
                                      corner_radius=R_FIELD, fg_color=FIELD_BG, text_color=TEXT_STRONG,
                                      hover_color=FIELD_HOVER, command=self.copy_log)
        self.btn_copy.grid(row=0, column=5, padx=(10, 0))
        ctk.CTkButton(head, text="Xóa", font=self.f_body, width=64, height=30, corner_radius=R_FIELD,
                      fg_color=FIELD_BG, text_color=TEXT_STRONG, hover_color=FIELD_HOVER,
                      command=self.clear_log).grid(row=0, column=6, padx=(10, 0))

        self.log = ctk.CTkTextbox(card, font=self.f_mono, fg_color=LOG_BG, corner_radius=R_LOG,
                                  text_color=TEXT_STRONG, wrap="none", height=140,
                                  activate_scrollbars=True)
        self.log.grid(row=1, column=0, sticky="nsew", padx=16, pady=(4, 16))
        self._apply_log_tags()
        self.log.configure(state="disabled")

    def _build_send_card(self):
        card = self._card(self)
        card.grid(row=3, column=0, sticky="ew", padx=24, pady=(5, 18))
        card.grid_columnconfigure(0, weight=1)
        self.send_card = card
        for r in range(3):
            ent = ctk.CTkEntry(card, font=self.f_body, height=30, corner_radius=R_FIELD,
                               fg_color=FIELD_BG, border_width=0,
                               placeholder_text=f"Chuỗi gửi #{r + 1}…")
            ent.grid(row=r, column=0, sticky="ew", padx=(20, 8), pady=(8 if r == 0 else 3, 3))
            hv = tk.BooleanVar(value=False)
            ctk.CTkSwitch(card, text="HEX", font=self.f_body, variable=hv,
                          progress_color=BLUE, width=60).grid(row=r, column=1, padx=8, pady=3)
            eol = self._menu(card, list(EOL_MAP), "(không)", width=90)
            eol.grid(row=r, column=2, padx=8, pady=3)
            ctk.CTkButton(card, text="Send", font=self.f_btn, width=90, height=30,
                          corner_radius=R_BTN, fg_color=BLUE, hover_color=BLUE_HOVER,
                          command=lambda i=r: self.send_row(i)).grid(
                              row=r, column=3, padx=(8, 20), pady=3)
            ent.bind("<Return>", lambda e, i=r: self.send_row(i))
            self.send_rows.append((ent, hv, eol))

        self.lbl_status = ctk.CTkLabel(card, text="Đang đóng", font=self.f_label, text_color=TEXT_SUB)
        self.lbl_status.grid(row=3, column=0, sticky="w", padx=22, pady=(2, 8))

    def _apply_log_tags(self):
        mode = ctk.get_appearance_mode()
        tb = self.log._textbox          # CTkTextbox bọc tk.Text bên trong
        tb.tag_config("rx", foreground=RX_COLOR[mode])
        tb.tag_config("tx", foreground=TX_COLOR[mode])
        tb.tag_config("sys", foreground=SYS_COLOR[mode])
        # Timestamp luôn được ghi; tag "ts" elide để ẩn/hiện theo nút Timestamp
        tb.tag_config("ts", foreground=SYS_COLOR[mode], elide=not self.show_ts.get())

    def _toggle_ts(self):
        self.log._textbox.tag_config("ts", elide=not self.show_ts.get())

    # ───────────────────────────── Nền gradient ─────────────────────────────
    def _refresh_gradient(self):
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
        self._show_port_info()

    def selected_port(self):
        return self.port_map.get(self.opt_port.get())

    def _show_port_info(self):
        """Đổ đầy đủ thông tin cổng đang chọn vào card 'Thông tin cổng'."""
        dev = self.selected_port()
        self.info_box.configure(state="normal")
        self.info_box.delete("1.0", "end")
        p = port_record(dev) if dev else None
        if p is None:
            self.info_box.insert("end", "Không có cổng để hiển thị.\nBấm ⟳ để quét lại.")
        else:
            def vp(v):
                return f"{v:04X}" if isinstance(v, int) else "—"
            rows = [
                ("Device", p.device),
                ("Tên", p.name or "—"),
                ("Mô tả", p.description or "—"),
                ("Nhà SX", p.manufacturer or "—"),
                ("Sản phẩm", p.product or "—"),
                ("VID:PID", f"{vp(p.vid)}:{vp(p.pid)}" if p.vid else "—"),
                ("Serial", p.serial_number or "—"),
                ("Vị trí", p.location or "—"),
                ("Interface", p.interface or "—"),
                ("HWID", p.hwid or "—"),
            ]
            for k, v in rows:
                self.info_box.insert("end", f"{k:<10}: {v}\n")
        self.info_box.configure(state="disabled")

    def toggle_open(self):
        self.close_port() if self.sm.is_open() else self.open_port()

    def open_port(self):
        port = self.selected_port()
        if not port:
            messagebox.showerror("Lỗi", "Chưa chọn cổng COM hợp lệ")
            return
        try:
            self.sm.open(port, int(self.opt_baud.get()), DATABITS[self.opt_data.get()],
                         PARITY[self.opt_parity.get()], STOPBITS[self.opt_stop.get()],
                         HANDSHAKE[self.opt_handshake.get()])
        except (serial.SerialException, ValueError, OSError) as e:
            messagebox.showerror("Không mở được cổng", str(e))
            self._set_status("Mở cổng thất bại")
            return
        # Đồng bộ DTR/RTS theo trạng thái switch hiện tại
        self.sm.set_dtr(self.dtr_var.get())
        self.sm.set_rts(self.rts_var.get())
        self.btn_open.configure(text="Close", fg_color="transparent", border_width=1,
                                border_color=CARD_BORDER, text_color=TEXT_STRONG, hover_color=FIELD_BG)
        self._set_pill(True)
        fmt = f"{self.opt_data.get()}{self.opt_parity.get()[0]}{self.opt_stop.get()}"
        self._set_status(f"Đã mở {port} @ {self.opt_baud.get()} {fmt} · {self.opt_handshake.get()}")

    def close_port(self):
        self.sm.close()
        self.btn_open.configure(text="Open", fg_color=BLUE, border_width=0,
                                text_color="white", hover_color=BLUE_HOVER)
        self._set_pill(False)
        self._set_status("Đang đóng")
        for dot in self.modem_lbls.values():
            dot.configure(text_color=GREY_DOT)

    def _set_pill(self, connected):
        if connected:
            self.pill_dot.configure(text_color=GREEN)
            self.pill_txt.configure(text="Connected")
        else:
            self.pill_dot.configure(text_color=GREY_DOT)
            self.pill_txt.configure(text="Chưa kết nối")

    def _set_status(self, text):
        self.lbl_status.configure(text=text)

    # ───────────────────────────── Gửi ──────────────────────────────────────
    def send_row(self, idx):
        ent, hv, eol = self.send_rows[idx]
        text = ent.get()
        if not text:
            return
        if hv.get():
            try:
                data = bytes.fromhex(text.replace(",", " "))
            except ValueError:
                messagebox.showerror("Lỗi", "Chuỗi HEX không hợp lệ (vd: 31 39 72)")
                return
            shown = " ".join(f"{b:02X}" for b in data)
        else:
            data = text.encode("ascii", "ignore") + EOL_MAP[eol.get()]
            shown = text
        self._write(data, shown)

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
            self._append_log(f"» {shown}\n", "tx")

    # ───────────────────────── Nhận (queue → UI) ────────────────────────────
    def _poll_rx(self):
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

    def _poll_modem(self):
        lines = self.sm.modem_lines()
        if lines is not None:
            for name, val in zip(("CD", "RI", "DSR", "CTS"), lines):
                self.modem_lbls[name].configure(text_color=GREEN if val else GREY_DOT)
        self.after(200, self._poll_modem)

    def _handle_rx(self, chunk):
        if self.show_hex.get():
            shown = " ".join(f"{b:02X}" for b in chunk) + " "
        else:
            shown = chunk.decode("ascii", "replace")
        self._append_log(shown, "rx")

    def _append_log(self, text, tag):
        # Chèn timestamp (tag "ts") ở ĐẦU MỖI DÒNG, luôn ghi; nút Timestamp chỉ
        # ẩn/hiện qua elide. Tách theo '\n' để timestamp đúng từng dòng dù data
        # về theo từng cụm bất kỳ.
        self.log.configure(state="normal")
        segs = text.split("\n")
        for i, seg in enumerate(segs):
            if seg:
                if self._need_ts:
                    self.log.insert("end", time.strftime("[%H:%M:%S] "), ("ts",))
                    self._need_ts = False
                self.log.insert("end", seg, (tag,))
            if i < len(segs) - 1:
                self.log.insert("end", "\n", (tag,))
                self._need_ts = True
        if self.autoscroll.get():
            self.log.see("end")
        self.log.configure(state="disabled")

    def clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self._need_ts = True

    def copy_log(self):
        """Chép toàn bộ nội dung ô data vào clipboard — đúng những gì đang hiện
        (bỏ timestamp nếu nút Timestamp đang tắt)."""
        tb = self.log._textbox
        if self.show_ts.get():
            content = tb.get("1.0", "end-1c")
        else:
            # Bỏ các đoạn mang tag "ts" (timestamp đang ẩn)
            ranges = tb.tag_ranges("ts")
            parts, pos = [], "1.0"
            for i in range(0, len(ranges), 2):
                parts.append(tb.get(pos, ranges[i]))
                pos = ranges[i + 1]
            parts.append(tb.get(pos, "end-1c"))
            content = "".join(parts)
        self.clipboard_clear()
        self.clipboard_append(content)
        self.btn_copy.configure(text="Đã chép ✓")
        self.after(1200, lambda: self.btn_copy.configure(text="Copy"))

    # ───────────────────────────── Theme & thoát ────────────────────────────
    def _on_theme(self, mode):
        ctk.set_appearance_mode(mode)
        self._refresh_gradient()
        self._apply_log_tags()

    def _on_close(self):
        self.sm.close()
        self.destroy()


def main():
    App().mainloop()


if __name__ == "__main__":
    main()


# ════════════════════════════════════════════════════════════════════════════
#  CÀI ĐẶT & ĐÓNG GÓI
# ════════════════════════════════════════════════════════════════════════════
#  Cài thư viện:
#      pip install customtkinter pyserial pillow
#
#  Chạy thử:
#      python tools/otl_serial_terminal.py
#
#  Build exe onefile. customtkinter BẮT BUỘC --collect-all để kèm asset theme
#  .json. Logo nạp từ otl_symbol.png + icon otl_icon.ico nên cần --add-data
#  (thiếu file thì tự rơi về logo vẽ tay):
#      python -m PyInstaller --onefile --windowed --name OTLSerialTerminal ^
#          --collect-all customtkinter ^
#          --icon tools/otl_icon.ico ^
#          --add-data "tools/otl_symbol.png;." ^
#          --add-data "tools/otl_icon.ico;." ^
#          tools/otl_serial_terminal.py
#
#  (Git Bash: thay ^ bằng \ để nối dòng, hoặc viết trên 1 dòng.)
