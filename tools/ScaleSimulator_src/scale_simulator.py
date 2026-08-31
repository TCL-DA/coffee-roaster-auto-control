"""
Scale Simulator — Liquid Glass (iOS 26 / macOS Tahoe style).

Mô phỏng cân Bluetooth/Serial cho máy rang OTL-06ALS. Gửi liên tục frame:
    GS,    61.45,kg<CR><LF>          (tùy chọn thêm trạng thái: ST,GS,…)

Giao diện theo tinh thần Liquid Glass: nền tint phẳng dịu, mỗi khu là "card kính"
nổi trên nền (bo góc lớn nhất quán, khoảng trắng rộng). Toàn bộ nằm trong vùng
cuộn được nên vừa mọi cỡ màn hình/DPI. Số trọng lượng là điểm nhấn lớn nhất.

Lưu ý hiệu năng: simulator gửi theo chu kỳ (200ms) → KHÔNG redraw card mỗi nhịp
(rất tốn CPU). Card vẽ MỘT lần; mỗi nhịp chỉ reconfigure đúng các label số
(trọng lượng, rorKG, bộ đếm đã gửi, frame).

Logic serial/RoR/hút giữ nguyên như bản gốc để khớp firmware.

Cài lib + build: xem comment cuối file.
"""

import os
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox

import serial
import serial.tools.list_ports

import customtkinter as ctk


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
# Nút +/- dạng kính có tông: nền nhạt, chữ đậm cùng tông
GREEN_TINT = ("#E7F8EC", "#1E3A28")
GREEN_TINT_HOVER = ("#D6F2DE", "#264A33")
RED_TINT = ("#FDEAE8", "#3A1E1C")
RED_TINT_HOVER = ("#FBDAD6", "#4A2622")

# Nền tint phẳng (light, dark) — xanh→tím rất nhạt / xám than. Card kính nổi trên.
BG_TINT = ("#E9EEFB", "#16181E")

# Bán kính bo góc nhất quán toàn app
R_CARD, R_BTN, R_FIELD, R_LOG, R_PILL = 18, 12, 9, 14, 16

FONT_FAMILY = "Segoe UI"        # SF Pro nếu máy có; fallback đẹp trên Windows
THIN_FAMILY = "Segoe UI Light"  # cho số trọng lượng to mảnh kiểu Apple
MONO_FAMILY = "Consolas"

SEND_INTERVAL_MS_DEFAULT = 200
BAUD_OPTIONS = ["1200", "2400", "4800", "9600", "19200", "38400", "57600", "115200"]
STATUS_OPTIONS = ["(không)", "ST", "US", "OL", "UL", "TL"]
STEPS = [0.01, 0.10, 1.00, 10.00]


def resource_path(rel):
    """Đường dẫn tài nguyên, chạy được cả khi đóng gói PyInstaller (--onefile)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


class SimpleKalman:
    """Bản sao thuật toán SimpleKalmanFilter (thư viện Arduino) để khớp firmware."""

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


def trunc_int(x):
    """Cắt về int như gán float -> int16_t trong C (về phía 0)."""
    return int(x)


# ════════════════════════════════════════════════════════════════════════════
#  ỨNG DỤNG (UI)
# ════════════════════════════════════════════════════════════════════════════
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("Light")
        ctk.set_default_color_theme("blue")
        self.title("Scale Simulator")
        self.geometry("1040x800")        # vừa gọn màn 1600×900, thấy đủ tính năng
        self.minsize(900, 640)
        try:
            self.iconbitmap(resource_path("scale_icon.ico"))
        except tk.TclError:
            pass

        # ----- Fonts -----
        self.f_title = ctk.CTkFont(FONT_FAMILY, 22, "bold")
        self.f_section = ctk.CTkFont(FONT_FAMILY, 15, "bold")
        self.f_label = ctk.CTkFont(FONT_FAMILY, 11)
        self.f_body = ctk.CTkFont(FONT_FAMILY, 13)
        self.f_btn = ctk.CTkFont(FONT_FAMILY, 14, "bold")
        self.f_hero = ctk.CTkFont(THIN_FAMILY, 72)
        self.f_unit = ctk.CTkFont(FONT_FAMILY, 22, "bold")
        self.f_pill = ctk.CTkFont(MONO_FAMILY, 17, "bold")
        self.f_mono = ctk.CTkFont(MONO_FAMILY, 13)

        # ----- Trạng thái serial / mô phỏng (giữ nguyên logic gốc) -----
        self.ser = None
        self.sending = False
        self.tx_thread = None
        self.weight = 120.00        # kg (mặc định)
        self.tx_count = 0
        # RoR khớp firmware: Kalman(1,1,0.02), cửa sổ 3s, clamp ±200, ×10
        self.ror_kalman = SimpleKalman(1, 1, 0.02)
        self.kg_samp_1 = None       # netW100 mẫu trước (×100)
        self.ror_next_t = None      # mốc 3s kế tiếp
        self.rorKG = 0              # giá trị firmware (đơn vị ×100: 1kg/phút=100)
        # Mô phỏng hút: rút X kg trong Y phút
        self.suck_active = False
        self.suck_remaining = 0.0
        self.suck_rate = 0.0
        self.suck_target = 0.0

        self.port_map = {}

        self._build_ui()
        self.refresh_ports()
        self.update_display()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ───────────────────────── Khối UI dùng lại ─────────────────────────────
    def _card(self, parent, inner=False, **kw):
        return ctk.CTkFrame(parent, fg_color=GLASS_INNER if inner else GLASS_CARD,
                            corner_radius=R_CARD, border_width=1, border_color=CARD_BORDER, **kw)

    def _field(self, parent, label_text):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        ctk.CTkLabel(f, text=label_text.upper(), font=self.f_label,
                     text_color=TEXT_SUB).pack(anchor="w", padx=2, pady=(0, 2))
        return f

    def _menu(self, parent, values, default, width=110, command=None):
        opt = ctk.CTkOptionMenu(parent, values=values, width=width, height=32, corner_radius=R_FIELD,
                                font=self.f_body, fg_color=FIELD_BG, button_color=FIELD_BG,
                                text_color=TEXT_STRONG, button_hover_color=FIELD_HOVER,
                                dropdown_font=self.f_body, dropdown_fg_color=GLASS_CARD,
                                dropdown_text_color=TEXT_STRONG, command=command)
        opt.set(default)
        return opt

    def _entry(self, parent, default, width=90):
        e = ctk.CTkEntry(parent, font=self.f_body, height=32, width=width, corner_radius=R_FIELD,
                         fg_color=FIELD_BG, border_width=0)
        e.insert(0, default)
        return e

    def _spinner(self, parent, default, step, fmt, width=64):
        # Ô nhập kèm nút − / + bước 1 đơn vị: − (tông đỏ) | ô | + (tông xanh)
        fr = ctk.CTkFrame(parent, fg_color="transparent")
        ctk.CTkButton(fr, text="−", width=28, height=32, corner_radius=R_BTN, font=self.f_btn,
                      fg_color=RED_TINT, hover_color=RED_TINT_HOVER, text_color=RED_HOVER,
                      command=lambda: self._spin(ent, -step, fmt)).pack(side="left", padx=(0, 4))
        ent = ctk.CTkEntry(fr, font=self.f_body, height=32, width=width, corner_radius=R_FIELD,
                           fg_color=FIELD_BG, border_width=0, justify="center")
        ent.insert(0, default)
        ent.pack(side="left")
        ctk.CTkButton(fr, text="+", width=28, height=32, corner_radius=R_BTN, font=self.f_btn,
                      fg_color=GREEN_TINT, hover_color=GREEN_TINT_HOVER, text_color=GREEN_HOVER,
                      command=lambda: self._spin(ent, step, fmt)).pack(side="left", padx=(4, 0))
        return fr, ent

    def _spin(self, entry, delta, fmt):
        # Đọc giá trị hiện tại, cộng/trừ bước, kẹp không âm rồi ghi lại theo định dạng
        try:
            v = float(entry.get() or 0)
        except ValueError:
            v = 0.0
        v = max(0.0, v + delta)
        entry.delete(0, "end")
        entry.insert(0, fmt.format(v))

    # ───────────────────────────── Dựng UI ──────────────────────────────────
    def _build_ui(self):
        # Bố cục 2 cột để thấy đủ tính năng không cần cuộn (vừa 1600×900). Vẫn bọc
        # trong vùng cuộn để an toàn khi cửa sổ bị thu nhỏ. fg_color của host/cột là
        # tint nền: khoảng hở giữa các card lộ tint này (card kính nổi lên trên).
        self.host = ctk.CTkScrollableFrame(self, fg_color=BG_TINT, corner_radius=0)
        self.host.pack(fill="both", expand=True)
        self.host.grid_columnconfigure(0, weight=1, uniform="col")
        self.host.grid_columnconfigure(1, weight=1, uniform="col")

        # Header card: tiêu đề + đổi mode (full width)
        head = self._card(self.host)
        head.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(20, 8))
        head.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(head, text="Scale Simulator", font=self.f_title,
                     text_color=TEXT_STRONG).grid(row=0, column=0, sticky="w", padx=20, pady=14)
        self.seg_theme = ctk.CTkSegmentedButton(head, values=["Light", "Dark"], font=self.f_label,
                                                 corner_radius=R_BTN, selected_color=BLUE,
                                                 selected_hover_color=BLUE_HOVER, command=self._on_theme)
        self.seg_theme.set("Light")
        self.seg_theme.grid(row=0, column=1, sticky="e", padx=16, pady=14)

        # Cột trái: Trọng lượng + nút gửi. Cột phải: Cấu hình + RoR + Hút.
        left = ctk.CTkFrame(self.host, fg_color=BG_TINT)
        left.grid(row=1, column=0, sticky="new", padx=(20, 10))
        left.grid_columnconfigure(0, weight=1)
        right = ctk.CTkFrame(self.host, fg_color=BG_TINT)
        right.grid(row=1, column=1, sticky="new", padx=(10, 20))
        right.grid_columnconfigure(0, weight=1)

        self._build_weight_card(left).grid(row=0, column=0, sticky="ew", pady=(8, 8))
        self._build_send_card(left).grid(row=1, column=0, sticky="ew", pady=(0, 20))
        self._build_config_card(right).grid(row=0, column=0, sticky="ew", pady=(8, 8))
        self._build_ror_card(right).grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self._build_suck_card(right).grid(row=2, column=0, sticky="ew", pady=(0, 20))

    def _build_config_card(self, parent):
        card = self._card(parent)
        card.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkLabel(card, text="Cấu hình cổng", font=self.f_section,
                     text_color=TEXT_STRONG).grid(row=0, column=0, columnspan=3, sticky="w",
                                                   padx=20, pady=(16, 6))

        com = self._field(card, "Cổng COM")
        com.grid(row=1, column=0, columnspan=3, sticky="ew", padx=20, pady=(0, 10))
        row = ctk.CTkFrame(com, fg_color="transparent")
        row.pack(fill="x")
        self.opt_port = self._menu(row, ["(quét...)"], "(quét...)", width=300)
        self.opt_port.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(row, text="⟳", width=34, height=32, corner_radius=R_FIELD, font=self.f_btn,
                      fg_color=FIELD_BG, text_color=TEXT_STRONG, hover_color=FIELD_HOVER,
                      command=self.refresh_ports).pack(side="left", padx=(8, 0))

        baud = self._field(card, "Baud")
        baud.grid(row=2, column=0, sticky="w", padx=(20, 8), pady=(0, 10))
        self.opt_baud = self._menu(baud, BAUD_OPTIONS, "2400", width=110)
        self.opt_baud.pack(anchor="w")

        ck = self._field(card, "Chu kỳ (ms)")
        ck.grid(row=2, column=1, sticky="w", padx=8, pady=(0, 10))
        self.ent_interval = self._entry(ck, str(SEND_INTERVAL_MS_DEFAULT), width=90)
        self.ent_interval.pack(anchor="w")

        st = self._field(card, "Trạng thái")
        st.grid(row=2, column=2, sticky="w", padx=8, pady=(0, 10))
        self.opt_status = self._menu(st, STATUS_OPTIONS, "(không)", width=110)
        self.opt_status.pack(anchor="w")

        self.var_2dec = tk.BooleanVar(value=True)
        ctk.CTkSwitch(card, text="2 số lẻ (61.45)", font=self.f_body, variable=self.var_2dec,
                      progress_color=BLUE, command=self.update_display).grid(
                          row=3, column=0, columnspan=3, sticky="w", padx=20, pady=(0, 16))
        return card

    def _build_weight_card(self, parent):
        card = self._card(parent)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(card, text="TRỌNG LƯỢNG", font=self.f_label,
                     text_color=TEXT_SUB).grid(row=0, column=0, pady=(16, 0))

        hero = ctk.CTkFrame(card, fg_color="transparent")
        hero.grid(row=1, column=0, pady=(0, 6))
        self.lbl_weight = ctk.CTkLabel(hero, text="0.00", font=self.f_hero, text_color=TEXT_STRONG)
        self.lbl_weight.pack(side="left")
        ctk.CTkLabel(hero, text="kg", font=self.f_unit, text_color=GREEN).pack(
            side="left", anchor="s", padx=(8, 0), pady=(0, 16))

        # Lưới +/- : hàng tăng (tông xanh), hàng giảm (tông đỏ)
        grid = ctk.CTkFrame(card, fg_color="transparent")
        grid.grid(row=2, column=0, pady=4)
        for i, s in enumerate(STEPS):
            grid.grid_columnconfigure(i, weight=1)
            ctk.CTkButton(grid, text=f"+{s:.2f}", width=104, height=42, corner_radius=R_BTN,
                          font=self.f_btn, fg_color=GREEN_TINT, hover_color=GREEN_TINT_HOVER,
                          text_color=GREEN_HOVER, command=lambda v=s: self.adjust(v)).grid(
                              row=0, column=i, padx=5, pady=4)
            ctk.CTkButton(grid, text=f"−{s:.2f}", width=104, height=42, corner_radius=R_BTN,
                          font=self.f_btn, fg_color=RED_TINT, hover_color=RED_TINT_HOVER,
                          text_color=RED_HOVER, command=lambda v=s: self.adjust(-v)).grid(
                              row=1, column=i, padx=5, pady=4)

        # Đặt nhanh / Zero
        quick = ctk.CTkFrame(card, fg_color="transparent")
        quick.grid(row=3, column=0, pady=(8, 18))
        ctk.CTkLabel(quick, text="Đặt", font=self.f_label, text_color=TEXT_SUB).pack(side="left", padx=(0, 6))
        self.ent_set = self._entry(quick, "120.00", width=100)
        self.ent_set.pack(side="left", padx=(0, 8))
        self.ent_set.bind("<Return>", lambda e: self.set_weight())
        ctk.CTkButton(quick, text="Set", width=72, height=34, corner_radius=R_BTN, font=self.f_btn,
                      fg_color=BLUE, hover_color=BLUE_HOVER, command=self.set_weight).pack(side="left", padx=4)
        ctk.CTkButton(quick, text="Zero", width=72, height=34, corner_radius=R_BTN, font=self.f_btn,
                      fg_color="transparent", border_width=1, border_color=CARD_BORDER,
                      text_color=TEXT_STRONG, hover_color=FIELD_BG,
                      command=lambda: self.set_to(0.0)).pack(side="left", padx=4)
        return card

    def _build_ror_card(self, parent):
        card = self._card(parent)
        card.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(card, text="RoR — tự động (kg/phút)", font=self.f_section,
                     text_color=TEXT_STRONG).grid(row=0, column=0, columnspan=3, sticky="w",
                                                   padx=20, pady=(16, 6))

        self.var_ror = tk.BooleanVar(value=False)
        ctk.CTkSwitch(card, text="Bật tự động", font=self.f_body, variable=self.var_ror,
                      progress_color=GREEN, command=self._reset_ror).grid(
                          row=1, column=0, sticky="w", padx=20, pady=6)
        ctk.CTkLabel(card, text="Tốc độ", font=self.f_label, text_color=TEXT_SUB).grid(
            row=1, column=1, sticky="e", padx=4)
        self.ent_ror = self._entry(card, "1.0", width=80)
        self.ent_ror.grid(row=1, column=2, sticky="w", padx=(0, 20))

        ctk.CTkLabel(card, text="Tốc độ dương = hút/cân giảm · rorKG (firmware): tăng → +, giảm → −",
                     font=self.f_label, text_color=TEXT_SUB).grid(
                         row=2, column=0, columnspan=3, sticky="w", padx=20, pady=(0, 8))

        # Metric pill: rorKG (Kalman khớp firmware)
        pill = ctk.CTkFrame(card, fg_color=PILL_BG, corner_radius=R_PILL)
        pill.grid(row=3, column=0, columnspan=3, sticky="ew", padx=20, pady=(0, 6))
        pill.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(pill, text="rorKG (KALMAN, KHỚP FIRMWARE)", font=self.f_label,
                     text_color=TEXT_SUB).grid(row=0, column=0, sticky="w", padx=16, pady=(10, 0))
        self.lbl_ror = ctk.CTkLabel(pill, text="+0   (+0.00 kg/phút)", font=self.f_pill,
                                    text_color=ORANGE)
        self.lbl_ror.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 10))

        ctk.CTkLabel(card, text="cửa sổ 3s · Kalman 1,1,0.02 · clamp ±200 · ×10",
                     font=self.f_label, text_color=TEXT_SUB).grid(
                         row=4, column=0, columnspan=3, sticky="w", padx=20, pady=(0, 16))
        return card

    def _build_suck_card(self, parent):
        card = self._card(parent)
        card.grid_columnconfigure(5, weight=1)

        ctk.CTkLabel(card, text="Mô phỏng hút", font=self.f_section,
                     text_color=TEXT_STRONG).grid(row=0, column=0, columnspan=6, sticky="w",
                                                   padx=20, pady=(16, 6))

        # Hàng 1: lượng cần hút (kg). Hàng 2: thời gian (phút/giây) — tách 2 hàng để
        # cụm nút − / + không làm tràn ô "giây" ra ngoài mép card.
        ctk.CTkLabel(card, text="Hút (kg)", font=self.f_label, text_color=TEXT_SUB).grid(
            row=1, column=0, sticky="w", padx=(20, 4), pady=4)
        fr_kg, self.ent_suck_kg = self._spinner(card, "30.00", 1.0, "{:.2f}", width=64)
        fr_kg.grid(row=1, column=1, sticky="w", pady=4)

        time_row = ctk.CTkFrame(card, fg_color="transparent")
        time_row.grid(row=2, column=0, columnspan=6, sticky="w", padx=(20, 0), pady=4)
        ctk.CTkLabel(time_row, text="Trong", font=self.f_label, text_color=TEXT_SUB).pack(
            side="left", padx=(0, 6))
        fr_min, self.ent_suck_min = self._spinner(time_row, "3", 1, "{:.0f}", width=40)
        fr_min.pack(side="left")
        ctk.CTkLabel(time_row, text="phút", font=self.f_label, text_color=TEXT_SUB).pack(
            side="left", padx=(4, 14))
        fr_sec, self.ent_suck_sec = self._spinner(time_row, "25", 1, "{:.0f}", width=40)
        fr_sec.pack(side="left")
        ctk.CTkLabel(time_row, text="giây", font=self.f_label, text_color=TEXT_SUB).pack(
            side="left", padx=(4, 0))

        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.grid(row=3, column=0, columnspan=6, sticky="w", padx=16, pady=(8, 6))
        ctk.CTkButton(btns, text="Bắt đầu hút", width=130, height=36, corner_radius=R_BTN,
                      font=self.f_btn, fg_color=GREEN, hover_color=GREEN_HOVER, text_color="white",
                      command=self.start_suck).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="Dừng hút", width=110, height=36, corner_radius=R_BTN,
                      font=self.f_btn, fg_color=RED_TINT, hover_color=RED_TINT_HOVER,
                      text_color=RED_HOVER, command=self.stop_suck).pack(side="left", padx=4)

        self.lbl_suck = ctk.CTkLabel(card, text="", font=self.f_body, text_color=ORANGE)
        self.lbl_suck.grid(row=4, column=0, columnspan=6, sticky="w", padx=20, pady=(0, 16))
        return card

    def _build_send_card(self, parent):
        card = self._card(parent)
        card.grid_columnconfigure(1, weight=1)

        self.btn_start = ctk.CTkButton(card, text="▶  START", width=150, height=56, corner_radius=R_BTN,
                                       font=self.f_title, fg_color=GREEN, hover_color=GREEN_HOVER,
                                       text_color="white", command=self.toggle)
        self.btn_start.grid(row=0, column=0, padx=20, pady=16)

        status = ctk.CTkFrame(card, fg_color="transparent")
        status.grid(row=0, column=1, sticky="w", padx=4, pady=16)
        spill = ctk.CTkFrame(status, fg_color=PILL_BG, corner_radius=R_PILL)
        spill.pack(anchor="w")
        self.pill_dot = ctk.CTkLabel(spill, text="●", font=self.f_body, text_color="#8E8E93")
        self.pill_dot.pack(side="left", padx=(12, 4), pady=6)
        self.pill_txt = ctk.CTkLabel(spill, text="Đang dừng", font=self.f_body, text_color=TEXT_STRONG)
        self.pill_txt.pack(side="left", padx=(0, 14))
        self.lbl_count = ctk.CTkLabel(status, text="đã gửi 0", font=self.f_label, text_color=TEXT_SUB)
        self.lbl_count.pack(anchor="w", padx=4, pady=(4, 0))

        # Frame đang gửi — log kỹ thuật, nền đặc, mono
        framebox = ctk.CTkFrame(card, fg_color=LOG_BG, corner_radius=R_LOG)
        framebox.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 18))
        framebox.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(framebox, text="FRAME ĐANG GỬI", font=self.f_label,
                     text_color=TEXT_SUB).grid(row=0, column=0, sticky="w", padx=14, pady=(10, 0))
        self.lbl_frame = ctk.CTkLabel(framebox, text="", font=self.f_mono, text_color=BLUE)
        self.lbl_frame.grid(row=1, column=0, sticky="w", padx=14, pady=(0, 10))
        return card

    # ───────────────────────────── Theme ────────────────────────────────────
    def _on_theme(self, mode):
        # Màu dạng (light, dark) nên CTk tự đổi toàn bộ — không cần vẽ lại gì.
        ctk.set_appearance_mode(mode)

    # ───────────────────────────── Cổng COM ─────────────────────────────────
    def refresh_ports(self):
        out = {}
        for p in serial.tools.list_ports.comports():
            desc = p.description or ""
            tail = f"({p.device})"
            if desc.endswith(tail):
                desc = desc[: -len(tail)].strip()
            label = f"{p.device} — {desc}" if desc and desc != "n/a" else p.device
            out[label] = p.device
        self.port_map = out
        labels = list(out) or ["(không có cổng)"]
        self.opt_port.configure(values=labels)
        if self.opt_port.get() not in labels:
            self.opt_port.set(labels[0])

    def selected_port(self):
        return self.port_map.get(self.opt_port.get(), "")

    # ───────────────────────────── Trọng lượng ──────────────────────────────
    def adjust(self, delta):
        self.set_to(self.weight + delta)

    def set_weight(self):
        try:
            self.set_to(float(self.ent_set.get()))
        except ValueError:
            messagebox.showerror("Lỗi", "Giá trị không hợp lệ")

    def set_to(self, value):
        self.weight = round(value, 2)
        self.update_display()

    # ───────────────────────────── Mô phỏng hút ─────────────────────────────
    def start_suck(self):
        try:
            kg = float(self.ent_suck_kg.get())
            mm = float(self.ent_suck_min.get() or 0)
            ss = float(self.ent_suck_sec.get() or 0)
        except ValueError:
            messagebox.showerror("Lỗi", "Số kg / phút / giây không hợp lệ")
            return
        minutes = mm + ss / 60.0
        if kg <= 0 or minutes <= 0:
            messagebox.showerror("Lỗi", "kg và thời gian phải lớn hơn 0")
            return
        self.suck_rate = kg / minutes
        self.suck_remaining = kg
        self.suck_target = round(max(0.0, self.weight - kg), 2)
        self.suck_active = True
        if not self.sending:                 # tự bật gửi nếu chưa chạy
            self.start()
        self.lbl_suck.configure(
            text=f"Hút {kg:.2f} kg trong {int(mm)}ph {int(ss)}s "
                 f"({self.suck_rate:.2f} kg/phút) → mục tiêu {self.suck_target:.2f} kg")

    def stop_suck(self):
        self.suck_active = False
        self.lbl_suck.configure(text="Đã dừng hút")

    def _suck_done(self):
        self.lbl_suck.configure(text=f"Hút xong ✓  (mục tiêu {self.suck_target:.2f} kg)")

    def _reset_ror(self):
        # Xóa trạng thái Kalman/mẫu khi bật/tắt auto để RoR tính lại từ đầu
        self.ror_kalman.reset()
        self.kg_samp_1 = None
        self.ror_next_t = None
        self.rorKG = 0

    # ───────────────────────────── Frame ────────────────────────────────────
    def build_frame(self):
        dec = 2 if self.var_2dec.get() else 1
        # weight căn phải 8 ký tự kể cả dấu chấm (theo protocol cân)
        num = f"{self.weight:.{dec}f}".rjust(8)
        status = self.opt_status.get()
        prefix = "" if status == "(không)" else f"{status},"
        return f"{prefix}GS,{num},kg\r\n"

    def update_display(self):
        self.lbl_weight.configure(text=f"{self.weight:.2f}")
        frame = self.build_frame().replace("\r", "<CR>").replace("\n", "<LF>")
        self.lbl_frame.configure(text=f"[{frame}]")

    # ───────────────────────────── Gửi ──────────────────────────────────────
    def toggle(self):
        self.stop() if self.sending else self.start()

    def start(self):
        port = self.selected_port()
        if not port:
            messagebox.showerror("Lỗi", "Chưa chọn cổng COM")
            return
        try:
            self.ser = serial.Serial(port, int(self.opt_baud.get()), timeout=1)
        except serial.SerialException as e:
            messagebox.showerror("Không mở được cổng", str(e))
            return

        self.sending = True
        self.tx_count = 0
        self._reset_ror()
        self.btn_start.configure(text="■  STOP", fg_color=RED, hover_color=RED_HOVER)
        self.pill_dot.configure(text_color=GREEN)
        self.tx_thread = threading.Thread(target=self._tx_loop, daemon=True)
        self.tx_thread.start()

    def stop(self):
        self.sending = False
        if self.tx_thread and self.tx_thread is not threading.current_thread():
            self.tx_thread.join(timeout=1)
        self.tx_thread = None
        if self.ser:
            self.ser.close()
            self.ser = None
        self.btn_start.configure(text="▶  START", fg_color=GREEN, hover_color=GREEN_HOVER)
        self.pill_dot.configure(text_color="#8E8E93")
        self.pill_txt.configure(text="Đang dừng")

    def _tx_loop(self):
        while self.sending and self.ser:
            try:
                interval = max(20, int(self.ent_interval.get()))
            except ValueError:
                interval = SEND_INTERVAL_MS_DEFAULT

            # Cập nhật cân: ưu tiên chế độ hút có mục tiêu, rồi mới tới Auto RoR.
            # Giữ self.weight ở độ chính xác đầy đủ, chỉ làm tròn khi hiển thị/gửi
            # để không dồn sai số làm tròn (trước đây gây lệch ~1kg).
            if self.suck_active:
                dec = self.suck_rate * (interval / 1000.0) / 60.0
                new_w = self.weight - dec
                if new_w <= self.suck_target:   # dừng đúng tại cân mục tiêu
                    new_w = self.suck_target
                    self.suck_active = False
                    self.after(0, self._suck_done)
                self.weight = new_w
                self.suck_remaining = self.weight - self.suck_target
            elif self.var_ror.get():
                try:
                    rate = float(self.ent_ror.get())
                except ValueError:
                    rate = 0.0
                # Tốc độ dương = hút → cân GIẢM (firmware: cân giảm → rorKG âm)
                self.weight = max(0.0, self.weight - rate * (interval / 1000.0) / 60.0)

            self._measure_ror()

            try:
                frame = self.build_frame()
                self.ser.write(frame.encode("ascii"))
                self.tx_count += 1
                self.after(0, self._update_status)
            except serial.SerialException as e:
                self.after(0, lambda: messagebox.showerror("Lỗi gửi", str(e)))
                self.after(0, self.stop)
                return
            time.sleep(interval / 1000.0)

    def _measure_ror(self):
        # Tính rorKG y hệt firmware (Program.h): cửa sổ 3s, Kalman, clamp ±200, ×10.
        # net100 = trọng lượng ×100 (như netW100). Khớp dấu firmware (hiện tại − trước):
        # cân TĂNG/nạp → dương, cân GIẢM/hút → âm.
        now = time.time()
        if self.ror_next_t is None:
            self.kg_samp_1 = round(self.weight * 100)
            self.ror_next_t = now + 3.0
            return
        if now < self.ror_next_t:
            return

        net100 = round(self.weight * 100)
        raw_rorKG = (net100 - self.kg_samp_1) * 2
        est = self.ror_kalman.update(raw_rorKG)
        r = trunc_int(est)
        r = max(-200, min(200, r))
        self.rorKG = r * 10
        self.kg_samp_1 = net100
        self.ror_next_t += 3.0

    def _update_status(self):
        # Chỉ reconfigure label — KHÔNG đụng card/gradient (tránh redraw 200ms).
        self.pill_txt.configure(text=f"ĐANG GỬI  {self.selected_port()} @ {self.opt_baud.get()}")
        self.lbl_count.configure(text=f"đã gửi {self.tx_count}")
        self.lbl_ror.configure(text=f"{self.rorKG:+d}   ({self.rorKG/100:+.2f} kg/phút)")
        if self.suck_active:
            self.lbl_suck.configure(
                text=f"Đang hút… còn {self.suck_remaining:.2f} kg "
                     f"→ mục tiêu {self.suck_target:.2f} kg  ({self.suck_rate:.2f} kg/phút)")
        self.update_display()

    def _on_close(self):
        self.stop()
        self.destroy()


def main():
    App().mainloop()


if __name__ == "__main__":
    main()


# ════════════════════════════════════════════════════════════════════════════
#  CÀI ĐẶT & ĐÓNG GÓI
# ════════════════════════════════════════════════════════════════════════════
#  Cài thư viện:
#      pip install customtkinter pyserial
#
#  Icon Liquid Glass đỏ–đen do tools/make_icon.py sinh ra (scale_icon.ico/.png).
#  Build exe onefile. customtkinter BẮT BUỘC --collect-all để kèm asset theme .json;
#  --icon đặt icon file exe, --add-data kèm .ico để iconbitmap chạy được lúc runtime
#  (đường dẫn icon nên là TUYỆT ĐỐI vì có dùng --specpath tools):
#      python -m PyInstaller --onefile --windowed --name ScaleSimulator ^
#          --icon  <ABS>/tools/scale_icon.ico ^
#          --add-data "<ABS>/tools/scale_icon.ico;." ^
#          --collect-all customtkinter ^
#          tools/scale_simulator.py
#
#  (Git Bash: thay ^ bằng \ để nối dòng, hoặc viết trên 1 dòng.)
