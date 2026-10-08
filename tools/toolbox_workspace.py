"""
Màn LÀM VIỆC của OTL Toolbox — một màn đủ thao tác của BT Tester, Scale Simulator,
Serial Terminal và Roaster Monitor.

Màn này KHÔNG giữ logic riêng: mỗi nút gọi thẳng hàm của "bộ máy" (App gốc của từng
công cụ, dựng sẵn và nằm ở tab Cài đặt). Cổng COM, baud, Kalman, Modbus relay… chỉnh ở
tab Cài đặt; màn này đọc trạng thái của bộ máy theo nhịp REFRESH_MS và log RX/TX của
BT + Terminal được rẽ nhánh sang ô log chung.
"""
import sys
import time
import tkinter as tk
from collections import deque

import customtkinter as ctk

FONT = "Segoe UI"
MONO = "Consolas"
INK = "#1E293B"
MUTED = "#64748B"
CARD = "#FFFFFF"
FIELD = "#F1F5F9"
LINE = "#E2E8F0"
BRAND = "#C62828"
BRAND_HOVER = "#A31F1F"
RUN = "#15803D"
UP_BG, UP_HOVER, UP_TEXT = "#E7F6EC", "#D3EEDC", "#166534"
DOWN_BG, DOWN_HOVER, DOWN_TEXT = "#FDECEC", "#FADADA", "#991B1B"
SRC_COLOR = {"BT": "#1D4ED8", "Terminal": "#7E22CE", "Cân": "#B45309"}
# Kiểu nút chọn iOS: rãnh xám, ô đang chọn trắng — chữ đậm đọc được ở cả hai trạng thái
SEGMENT_STYLE = dict(fg_color=LINE, selected_color=CARD, selected_hover_color=CARD,
                     unselected_color=LINE, unselected_hover_color="#CBD5E1", text_color=INK,
                     text_color_disabled=MUTED)

REFRESH_MS = 250
LOG_KEEP = 3000            # số dòng log chung giữ lại để lọc lại được
PARTIAL_FLUSH_S = 0.4      # dòng RX không có '\n' — chờ chừng này rồi ghi luôn
EOL = {"(không)": "", "\\n": "\n", "\\r\\n": "\r\n"}
BT_HOTKEYS = "1259qwer"
TEXT_INPUTS = {"Entry", "Text", "TEntry", "Spinbox"}


def _module_of(engine):
    return sys.modules[type(engine).__module__]


def _text(widget, default="—") -> str:
    try:
        return widget.cget("text") or default
    except (AttributeError, tk.TclError):
        return default


class Workspace(ctk.CTkFrame):
    def __init__(self, master, engines: dict, open_settings):
        super().__init__(master, fg_color="transparent")
        self.bt = engines.get("bt")
        self.scale = engines.get("scale")
        self.term = engines.get("terminal")
        self.mon = engines.get("monitor")
        self.open_settings = open_settings
        self._log_rows = deque(maxlen=LOG_KEEP)
        self._pending = {}             # nguồn → (chuỗi dở dang, thời điểm nhận)
        self.f = {n: ctk.CTkFont(FONT, s, w) for n, s, w in (
            ("h", 15, "bold"), ("b", 13, "normal"), ("bb", 13, "bold"), ("s", 12, "normal"),
            ("btn", 14, "bold"))}
        self._build()
        self._hook_logs()
        self._bind_bt_hotkeys()
        self.after(REFRESH_MS, self._refresh)

    # ═════ khối dùng chung ═════
    def _card(self, parent, title=None, note=None):
        card = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=14)
        if title:
            head = ctk.CTkFrame(card, fg_color="transparent")
            head.pack(fill="x", padx=18, pady=(12, 4))
            ctk.CTkLabel(head, text=title, text_color=INK, font=self.f["h"]).pack(side="left")
            if note:
                self._small(head, note).pack(side="right")
        return card

    def _btn(self, parent, text, cmd, kind="soft", width=0, height=40):
        colors = {"soft": (FIELD, LINE, INK), "primary": (BRAND, BRAND_HOVER, "#FFFFFF"),
                  "up": (UP_BG, UP_HOVER, UP_TEXT), "down": (DOWN_BG, DOWN_HOVER, DOWN_TEXT)}[kind]
        return ctk.CTkButton(parent, text=text, command=cmd, width=width, height=height,
                             corner_radius=10, fg_color=colors[0], hover_color=colors[1],
                             text_color=colors[2],
                             font=self.f["btn"] if kind != "soft" else self.f["b"])

    def _small(self, parent, text, color=MUTED):
        return ctk.CTkLabel(parent, text=text, text_color=color, font=self.f["s"])

    # ═════ dựng màn ═════
    def _build(self):
        self._build_device_strip()
        mid = ctk.CTkFrame(self, fg_color="transparent")
        mid.pack(fill="both", expand=True, padx=16, pady=(0, 10))
        for c in range(3):
            mid.grid_columnconfigure(c, weight=1, uniform="col")
        mid.grid_rowconfigure(0, weight=1)
        self._build_bt_card(mid).grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self._build_scale_card(mid).grid(row=0, column=1, sticky="nsew", padx=6)
        self._build_monitor_card(mid).grid(row=0, column=2, sticky="nsew", padx=(6, 0))
        self._build_log_card().pack(fill="both", expand=True, padx=16, pady=(0, 12))

    def _build_device_strip(self):
        strip = ctk.CTkFrame(self, fg_color="transparent")
        strip.pack(fill="x", padx=16, pady=(12, 10))
        self.chips = {}
        for i, (key, name) in enumerate((("bt", "BT Tester"), ("scale", "Cân giả lập"),
                                         ("terminal", "Serial Terminal"))):
            strip.grid_columnconfigure(i, weight=1, uniform="chip")
            card = ctk.CTkFrame(strip, fg_color=CARD, corner_radius=14)
            card.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 6, 0 if i == 2 else 6))
            info = ctk.CTkFrame(card, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True, padx=16, pady=6)
            ctk.CTkLabel(info, text=name, text_color=INK, font=self.f["bb"]).pack(anchor="w")
            state = ctk.CTkLabel(info, text="", text_color=MUTED, font=self.f["s"], anchor="w")
            state.pack(anchor="w", fill="x")
            btn = self._btn(card, "Nối", lambda k=key: self._toggle_device(k), "primary", 112, 44)
            btn.pack(side="right", padx=(6, 14), pady=8)
            self._btn(card, "Đổi cổng", lambda k=key: self.open_settings(k), "soft", 96, 44
                      ).pack(side="right", pady=8)
            self.chips[key] = (state, btn)

    def _build_bt_card(self, parent):
        card = self._card(parent, "BT giả lập", "phím tắt 1 2 5 9 tăng · q w e r giảm")
        mod = _module_of(self.bt) if self.bt else None
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=18)
        self._small(top, "BT thiết bị báo về").pack(anchor="w")
        self.bt_value = ctk.CTkLabel(top, text="—", text_color=INK, anchor="w",
                                     font=ctk.CTkFont(MONO, 38, "bold"))
        self.bt_value.pack(anchor="w")
        pad = ctk.CTkFrame(card, fg_color="transparent")
        pad.pack(fill="x", padx=18, pady=(4, 0))
        cmds = ((mod.UP_CMDS, "up"), (mod.DOWN_CMDS, "down")) if mod else ()
        for r, (row, kind) in enumerate(cmds):
            for c, (label, code) in enumerate(row):
                pad.grid_columnconfigure(c, weight=1, uniform="k")
                self._btn(pad, f"{label}  ({code})", lambda x=code: self.bt.send_text(x), kind,
                          height=40).grid(row=r, column=c, sticky="ew", padx=3, pady=3)
        tk.Frame(card, height=1, bg=LINE).pack(fill="x", padx=18, pady=(8, 0))
        self._build_replay(card, mod)
        return card

    def _build_replay(self, card, mod):
        box = ctk.CTkFrame(card, fg_color="transparent")
        box.pack(fill="both", expand=True, padx=18, pady=(10, 14))
        head = ctk.CTkFrame(box, fg_color="transparent")
        head.pack(fill="x")
        ctk.CTkLabel(head, text="Phát lại hồ sơ", text_color=INK, font=self.f["bb"]).pack(side="left")
        self.rp_file = self._small(head, "chưa chọn hồ sơ")
        self.rp_file.pack(side="left", padx=10)
        acts = ctk.CTkFrame(box, fg_color="transparent")
        acts.pack(fill="x", pady=(8, 0))
        self._btn(acts, "Chọn hồ sơ", lambda: self.bt.choose_csv(), height=44).pack(side="left")
        self.rp_play = self._btn(acts, "▶  Phát", self._toggle_replay, "primary", 112, 44)
        self.rp_play.pack(side="left", padx=6)
        self._btn(acts, "Về đầu", lambda: self.bt.reset_replay(), height=44, width=84).pack(side="left")
        speeds = list(getattr(mod, "SPEED_PRESETS", ["x1"]))
        self.rp_speed = ctk.CTkOptionMenu(acts, values=speeds, width=92, height=44,
                                          fg_color=FIELD, button_color=FIELD, button_hover_color=LINE,
                                          text_color=INK, font=self.f["b"], command=self._set_speed)
        self.rp_speed.pack(side="right")
        self._small(acts, "Tốc độ").pack(side="right", padx=6)
        stats = ctk.CTkFrame(box, fg_color=FIELD, corner_radius=10)
        stats.pack(fill="x", pady=(10, 0))
        self.rp_stats = {}
        for c, name in enumerate(("Pha", "BT mục tiêu", "RoR", "Bù tay")):
            stats.grid_columnconfigure(c, weight=1, uniform="s")
            self._small(stats, name).grid(row=0, column=c, sticky="w", padx=12, pady=(8, 0))
            lbl = ctk.CTkLabel(stats, text="—", text_color=INK, font=ctk.CTkFont(MONO, 16, "bold"))
            lbl.grid(row=1, column=c, sticky="w", padx=12, pady=(0, 8))
            self.rp_stats[name] = lbl

    def _build_scale_card(self, parent):
        card = self._card(parent, "Cân giả lập")
        mod = _module_of(self.scale) if self.scale else None
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=18)
        self._small(top, "Trọng lượng đang gửi").pack(anchor="w")
        row = ctk.CTkFrame(top, fg_color="transparent")
        row.pack(anchor="w")
        self.sc_value = ctk.CTkLabel(row, text="—", text_color=INK, font=ctk.CTkFont(MONO, 38, "bold"))
        self.sc_value.pack(side="left")
        ctk.CTkLabel(row, text=" kg", text_color=MUTED, font=ctk.CTkFont(FONT, 20, "bold")).pack(
            side="left", pady=(14, 0))
        pad = ctk.CTkFrame(card, fg_color="transparent")
        pad.pack(fill="x", padx=18, pady=(4, 0))
        for c, step in enumerate(getattr(mod, "STEPS", [0.01, 0.1, 1.0, 10.0])):
            pad.grid_columnconfigure(c, weight=1, uniform="k")
            self._btn(pad, f"+{step:.2f}", lambda s=step: self.scale.adjust(s), "up", height=40
                      ).grid(row=0, column=c, sticky="ew", padx=3, pady=3)
            self._btn(pad, f"−{step:.2f}", lambda s=step: self.scale.adjust(-s), "down", height=40
                      ).grid(row=1, column=c, sticky="ew", padx=3, pady=3)
        setrow = ctk.CTkFrame(card, fg_color="transparent")
        setrow.pack(fill="x", padx=18, pady=(8, 10))
        self.sc_set = ctk.CTkEntry(setrow, width=110, height=44, fg_color=FIELD, border_width=0,
                                   placeholder_text="kg", font=self.f["b"])
        self.sc_set.pack(side="left")
        self._btn(setrow, "Đặt", self._scale_set, height=44, width=72).pack(side="left", padx=6)
        self._btn(setrow, "Về 0", lambda: self.scale.set_to(0), height=44, width=72).pack(side="left")
        self.sc_ror = self._small(setrow, "RoR —")
        self.sc_ror.pack(side="right")
        tk.Frame(card, height=1, bg=LINE).pack(fill="x", padx=18)
        self._build_suction(card)
        return card

    def _build_suction(self, card):
        box = ctk.CTkFrame(card, fg_color="transparent")
        box.pack(fill="both", expand=True, padx=18, pady=(10, 14))
        ctk.CTkLabel(box, text="Mô phỏng hút", text_color=INK, font=self.f["bb"]).pack(anchor="w")
        row = ctk.CTkFrame(box, fg_color="transparent")
        row.pack(fill="x", pady=(8, 0))
        self.suck = {}
        for name, default, unit in (("kg", "30", "kg trong"), ("min", "3", "phút"), ("sec", "0", "giây")):
            ent = ctk.CTkEntry(row, width=64, height=44, fg_color=FIELD, border_width=0,
                               justify="center", font=self.f["b"])
            ent.insert(0, default)
            ent.pack(side="left")
            self._small(row, unit).pack(side="left", padx=(4, 10))
            self.suck[name] = ent
        acts = ctk.CTkFrame(box, fg_color="transparent")
        acts.pack(fill="x", pady=(8, 0))
        self._btn(acts, "Bắt đầu hút", self._start_suck, "up", 130, 44).pack(side="left")
        self._btn(acts, "Dừng hút", lambda: self.scale.stop_suck(), "down", 110, 44).pack(
            side="left", padx=6)
        self.sc_suck = ctk.CTkLabel(box, text="", text_color=MUTED, font=self.f["s"], anchor="w",
                                    justify="left", wraplength=480)
        self.sc_suck.pack(fill="x", pady=(8, 0))

    def _build_monitor_card(self, parent):
        card = self._card(parent, "Số liệu mẻ rang (Artisan CSV)")
        mon = self.mon
        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill="x", padx=18)
        self.mon_btn = self._btn(head, "Bắt đầu theo dõi", lambda: mon._toggle(), "primary", 150, 44)
        self.mon_btn.pack(side="left")
        ctk.CTkLabel(head, textvariable=mon.file_var, text_color=MUTED, font=self.f["s"]).pack(
            side="left", padx=10)
        grid = ctk.CTkFrame(card, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=12, pady=(8, 14))
        mod = _module_of(mon)
        for c in range(2):
            grid.grid_columnconfigure(c, weight=1, uniform="m")
        for i, (name, unit, color) in enumerate(mod.METRICS):
            # Một hàng: tên + đơn vị bên trái, số bên phải — 10 chỉ số vừa 5 hàng thấp
            tile = ctk.CTkFrame(grid, fg_color=FIELD, corner_radius=10, height=48)
            tile.grid(row=i // 2, column=i % 2, sticky="nsew", padx=4, pady=4)
            grid.grid_rowconfigure(i // 2, weight=1)
            self._small(tile, f"{name}\n{unit}").pack(side="left", padx=12)
            ctk.CTkLabel(tile, textvariable=mon.vars[name], text_color=color,
                         font=ctk.CTkFont(MONO, 22, "bold")).pack(side="right", padx=12)
        return card

    def _build_log_card(self):
        card = ctk.CTkFrame(self, fg_color=CARD, corner_radius=14)
        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill="x", padx=18, pady=(12, 6))
        ctk.CTkLabel(head, text="Log chung", text_color=INK, font=self.f["h"]).pack(side="left")
        self.log_filter = ctk.CTkSegmentedButton(head, values=["Tất cả", "BT", "Terminal"],
                                                 command=lambda _v: self._rerender_log(),
                                                 font=self.f["b"], height=34, **SEGMENT_STYLE)
        self.log_filter.set("Tất cả")
        self.log_filter.pack(side="left", padx=14)
        self._btn(head, "Xóa", self._clear_log, height=34, width=64).pack(side="right")
        # 72 px là TỐI THIỂU — ô log giãn theo chỗ trống, màn 125% vẫn không phải cuộn
        self.log = ctk.CTkTextbox(card, height=72, fg_color=FIELD, corner_radius=10,
                                  font=ctk.CTkFont(MONO, 12), text_color=INK, wrap="none")
        self.log.pack(fill="both", expand=True, padx=18)
        for src, color in SRC_COLOR.items():
            self.log.tag_config(src, foreground=color)
        self.log.configure(state="disabled")
        send = ctk.CTkFrame(card, fg_color="transparent")
        send.pack(fill="x", padx=18, pady=(8, 14))
        self._small(send, "Gửi tới").pack(side="left")
        self.send_target = ctk.CTkSegmentedButton(send, values=["BT", "Terminal"], height=40,
                                                  font=self.f["b"], **SEGMENT_STYLE)
        self.send_target.set("Terminal")
        self.send_target.pack(side="left", padx=8)
        self.send_entry = ctk.CTkEntry(send, height=40, fg_color=FIELD, border_width=0,
                                       placeholder_text="Chuỗi gửi… (Enter để gửi)", font=self.f["b"])
        self.send_entry.pack(side="left", fill="x", expand=True)
        self.send_entry.bind("<Return>", lambda _e: self._send())
        self.send_eol = ctk.CTkOptionMenu(send, values=list(EOL), width=100, height=40, fg_color=FIELD,
                                          button_color=FIELD, button_hover_color=LINE, text_color=INK,
                                          font=self.f["b"])
        self.send_eol.set("\\r\\n")
        self.send_eol.pack(side="left", padx=8)
        self._btn(send, "Gửi", self._send, "primary", 96, 40).pack(side="left")
        return card

    # ═════ thao tác ═════
    def _toggle_device(self, key):
        engine = {"bt": self.bt, "scale": self.scale, "terminal": self.term}[key]
        (engine.toggle if key == "scale" else engine.toggle_open)()
        self._log_line("Cân" if key == "scale" else ("BT" if key == "bt" else "Terminal"),
                       "— bấm Nối/Ngắt từ màn Làm việc")

    def _toggle_replay(self):
        (self.bt.stop_replay if self.bt.playing else self.bt.start_replay)()

    def _set_speed(self, value):
        v = self.bt._parse_speed(value)
        if v is not None:
            self.bt._set_speed(v)

    def _scale_set(self):
        try:
            self.scale.set_to(float(self.sc_set.get().replace(",", ".")))
        except ValueError:
            self.sc_suck.configure(text="Giá trị cân không hợp lệ", text_color=DOWN_TEXT)

    def _start_suck(self):
        targets = {"kg": self.scale.ent_suck_kg, "min": self.scale.ent_suck_min,
                   "sec": self.scale.ent_suck_sec}
        for name, ent in targets.items():
            ent.delete(0, "end")
            ent.insert(0, self.suck[name].get())
        self.scale.start_suck()

    def _send(self):
        text = self.send_entry.get()
        if not text:
            return
        data = text + EOL[self.send_eol.get()]
        if self.send_target.get() == "BT":
            self.bt.send_text(data)
        else:
            self.term._write(data.encode("latin-1", "replace"), text)

    # ═════ log chung ═════
    def _hook_logs(self):
        """Rẽ nhánh log RX/TX của BT và Terminal sang log chung (log gốc vẫn ghi như cũ)."""
        if self.bt is not None:
            bt_append = self.bt._append_log
            self.bt._append_log = lambda text: (bt_append(text), self._feed("BT", text))
        if self.term is not None:
            term_append = self.term._append_log
            self.term._append_log = lambda text, tag: (term_append(text, tag), self._feed("Terminal", text))

    def _feed(self, src, text):
        buf, _ = self._pending.get(src, ("", 0.0))
        buf += text.replace("\r", "")
        *lines, rest = buf.split("\n")
        for line in lines:
            self._log_line(src, line)
        self._pending[src] = (rest, time.monotonic())

    def _flush_partial(self):
        now = time.monotonic()
        for src, (rest, at) in list(self._pending.items()):
            if rest and now - at > PARTIAL_FLUSH_S:
                self._log_line(src, rest)
                self._pending[src] = ("", now)

    def _log_line(self, src, line):
        row = (time.strftime("%H:%M:%S"), src, line)
        self._log_rows.append(row)
        if self.log_filter.get() in ("Tất cả", src):
            self._insert_rows([row])

    def _insert_rows(self, rows):
        self.log.configure(state="normal")
        for ts, src, line in rows:
            self.log.insert("end", f"{ts}  {src:<8} ", (src,))
            self.log.insert("end", f"{line}\n")
        if len(rows) > 1 or int(self.log.index("end-1c").split(".")[0]) > LOG_KEEP:
            self.log.delete("1.0", f"end-{LOG_KEEP}l")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _rerender_log(self):
        want = self.log_filter.get()
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self._insert_rows([r for r in self._log_rows if want in ("Tất cả", r[1])])

    def _clear_log(self):
        self._log_rows.clear()
        self._rerender_log()

    # ═════ phím tắt BT trên màn này ═════
    def _bind_bt_hotkeys(self):
        top = self.winfo_toplevel()
        for key in BT_HOTKEYS:
            top.bind(f"<KeyPress-{key}>", self._on_hotkey, add="+")

    def _on_hotkey(self, event):
        if not self.winfo_ismapped() or self.bt is None:
            return None
        try:
            if event.widget.winfo_class() in TEXT_INPUTS:
                return None
        except (AttributeError, tk.TclError):
            pass
        if event.char and event.char in BT_HOTKEYS:
            self.bt.send_text(event.char)
        return None

    # ═════ đồng bộ trạng thái từ bộ máy ═════
    def _refresh(self):
        try:
            self._flush_partial()
            if self.winfo_ismapped():
                self._refresh_chips()
                self._refresh_bt()
                self._refresh_scale()
                self.mon_btn.configure(text="Dừng theo dõi" if self.mon.running else "Bắt đầu theo dõi",
                                       fg_color="#475569" if self.mon.running else BRAND)
        finally:
            self.after(REFRESH_MS, self._refresh)

    def _chip(self, key, on, port, on_text, off_text, btn_on, btn_off):
        state, btn = self.chips[key]
        port = port or "chưa chọn cổng"
        if on:
            state.configure(text=f"● {port} · {on_text}", text_color=RUN)
            btn.configure(text=btn_on, fg_color="#475569", hover_color="#334155")
        else:
            state.configure(text=f"○ {port} · {off_text}", text_color=MUTED)
            btn.configure(text=btn_off, fg_color=BRAND, hover_color=BRAND_HOVER)

    def _refresh_chips(self):
        self._chip("bt", self.bt.sm.is_open(), self.bt.selected_port(), "đã nối", "chưa nối",
                   "Ngắt", "Nối")
        self._chip("scale", self.scale.sending, self.scale.selected_port(),
                   f"đang gửi · {self.scale.tx_count} khung", "đang dừng", "Dừng gửi", "Bắt đầu gửi")
        self._chip("terminal", self.term.sm.is_open(), self.term.selected_port(), "đã nối",
                   "chưa nối", "Ngắt", "Nối")

    def _refresh_bt(self):
        bt = self.bt
        self.bt_value.configure(text=f"{bt.dev_bt:.2f} °C" if bt.dev_bt is not None else "— °C")
        name = _text(bt.lbl_file, "")
        self.rp_file.configure(text=name if bt.profile else "chưa chọn hồ sơ")
        self.rp_play.configure(text="■  Dừng" if bt.playing else "▶  Phát",
                               fg_color="#475569" if bt.playing else BRAND)
        for key, widget in (("Pha", bt.lbl_phase), ("BT mục tiêu", bt.lbl_bt), ("RoR", bt.lbl_ror),
                            ("Bù tay", bt.lbl_offset)):
            self.rp_stats[key].configure(text=_text(widget))
        speed = bt.opt_speed.get()
        if self.rp_speed.get() != speed:
            self.rp_speed.set(speed)

    def _refresh_scale(self):
        sc = self.scale
        self.sc_value.configure(text=f"{sc.weight:.2f}")
        self.sc_ror.configure(text=f"RoR {sc.rorKG / 100:+.2f} kg/phút")
        self.sc_suck.configure(text=_text(sc.lbl_suck, ""), text_color=MUTED)
