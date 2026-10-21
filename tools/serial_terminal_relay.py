"""
Panel "Modbus Relay" của OTL Serial Terminal.

Dò tìm, đọc/ghi cấu hình và bật/tắt thử module relay 8 kênh Waveshare Modbus
RTU Relay (B). Bản thiết kế gốc (Claude Design, project "OTL Serial Terminal")
mirror ở html/design/otl-serial-terminal/ — đổi giao diện thì sửa bản thiết kế
trước rồi mới sửa ở đây.

Luồng chạy:
  nút bấm (luồng Tk) → chụp thông số widget thành `snap` → giao MỘT tác vụ cho
  luồng phụ → luồng phụ nói chuyện với cổng qua modbus_relay → mọi cập nhật
  giao diện gửi ngược về luồng Tk bằng app.ui_call(). Luồng phụ KHÔNG đọc hay
  ghi widget / biến Tk nào.
"""

import math
import threading
import time
import tkinter as tk

import customtkinter as ctk
import serial
import serial.tools.list_ports

import modbus_relay as mr

PANEL_WIDTH = 452
TAB_SCAN, TAB_CONFIG, TAB_TEST = "Tìm thiết bị", "Cấu hình", "Test relay"
SCOPE_PORT, SCOPE_ALL = "Cổng đang chọn", "Mọi cổng COM"
MODE_QUICK, MODE_IDS = "Nhanh (broadcast)", "Hỏi từng ID"
FLASH_MODES = ("Bật rồi tự tắt", "Tắt rồi tự bật")
SCAN_BAUD_DEFAULT = (9600, 38400, 115200, 19200, 57600)
PRESETS = (
    ("Máy rang OTL · ID 7 · 38400", 7, 38400, "None"),
    ("Mặc định hãng · ID 1 · 9600", 1, 9600, "None"),
)
PARITY_BY_LETTER = {serial.PARITY_NONE: "None", serial.PARITY_EVEN: "Even", serial.PARITY_ODD: "Odd"}
PARITY_BY_NAME = {name: letter for letter, name in PARITY_BY_LETTER.items()}
NO_FLOW = {"xonxoff": False, "rtscts": False, "dsrdtr": False}
POLL_MS = 1000
POLL_FAIL_LIMIT = 3
CONFIRM_MS = 4000
BUSY_TEXT = "Panel Modbus Relay đang chạy tác vụ khác — chờ xong hoặc bấm Dừng"


class RelayPanel:
    def __init__(self, app, card, tok):
        self.app, self.card, self.t = app, card, tok
        self.client = app.mb
        self.client.on_frame = self._on_frame
        self.cur_baud, self.cur_parity = 9600, "None"
        self.relay = mr.WaveshareRelay(self.client, lambda: self.cur_baud)
        self.quiet = False              # True = không in từng khung (quét, đọc định kỳ)
        self.device = None              # module đã xác nhận: address/baud/parity/version/port
        self._job = None
        self._job_is_poll = False
        self._pending = None            # lệnh bấm trúng lúc đang đọc định kỳ → chạy ngay sau
        self._cancel = threading.Event()
        self._poll_fail = 0
        self._confirm_after = None
        self._seq_running = False
        self._build()
        app.after(POLL_MS, self._poll_tick)

    # ═════════════════════════════ khối UI dùng lại ═════════════════════════════
    def _label(self, parent, text, sub=False, font=None, **kw):
        return ctk.CTkLabel(parent, text=text, font=font or self.app.f_body,
                            text_color=self.t.TEXT_SUB if sub else self.t.TEXT_STRONG, **kw)

    def _btn(self, parent, text, command, primary=False, height=None, font=None, **kw):
        t = self.t
        if primary:
            style = dict(fg_color=t.BLUE, hover_color=t.BLUE_HOVER, text_color="white",
                         corner_radius=t.R_BTN, font=font or self.app.f_btn)
        else:
            style = dict(fg_color=t.FIELD_BG, hover_color=t.FIELD_HOVER, text_color=t.TEXT_STRONG,
                         corner_radius=t.R_FIELD, font=font or self.f_small)
        return ctk.CTkButton(parent, text=text, command=command, height=height or 28, **style, **kw)

    def _entry(self, parent, width, value):
        t = self.t
        ent = ctk.CTkEntry(parent, width=width, height=30, corner_radius=t.R_FIELD, border_width=0,
                           fg_color=t.FIELD_BG, text_color=t.TEXT_STRONG, font=self.app.f_mono,
                           justify="center")
        ent.insert(0, str(value))
        return ent

    def _seg(self, parent, values, command=None, height=30):
        t = self.t
        return ctk.CTkSegmentedButton(parent, values=values, command=command, height=height,
                                      font=self.app.f_body, corner_radius=10, border_width=3,
                                      fg_color=t.SEG_TRACK, selected_color=t.GLASS_CARD,
                                      selected_hover_color=t.GLASS_CARD, unselected_color=t.SEG_TRACK,
                                      unselected_hover_color=t.FIELD_HOVER, text_color=t.TEXT_STRONG,
                                      dynamic_resizing=False)

    def _group(self, parent):
        t = self.t
        return ctk.CTkFrame(parent, fg_color=t.GLASS_INNER, corner_radius=14,
                            border_width=1, border_color=t.CARD_BORDER)

    def _check(self, parent, text, var):
        t = self.t
        # width mặc định của CTkCheckBox là 100 px → 4 ô baud một hàng tràn khỏi panel
        return ctk.CTkCheckBox(parent, text=text, variable=var, font=self.app.f_body, width=40,
                               text_color=t.TEXT_STRONG, checkbox_width=18, checkbox_height=18,
                               corner_radius=5, border_width=2, border_color=t.TEXT_SUB,
                               fg_color=t.BLUE, hover_color=t.BLUE_HOVER)

    @staticmethod
    def _set_entry(entry, value):
        state = entry.cget("state")
        entry.configure(state="normal")
        entry.delete(0, "end")
        entry.insert(0, str(value))
        entry.configure(state=state)

    def _status(self, text):
        self.app._set_status(text)

    # ═════════════════════════════════ dựng UI ═════════════════════════════════
    def _build(self):
        t, app, card = self.t, self.app, self.card
        self.f_small = ctk.CTkFont(t.FONT_FAMILY, 12)
        self.f_bold = ctk.CTkFont(t.FONT_FAMILY, 13, "bold")
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(3, weight=1)

        head = ctk.CTkFrame(card, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 0))
        head.grid_columnconfigure(0, weight=1)
        self._label(head, "Modbus Relay", font=app.f_section).grid(row=0, column=0, sticky="w")
        self._label(head, "Waveshare 8 kênh · RTU · giao thức V3", sub=True, font=self.f_small,
                    height=16).grid(row=1, column=0, sticky="w")
        self.chip = ctk.CTkFrame(head, fg_color=t.FIELD_BG, corner_radius=12)
        self.chip.grid(row=0, column=1, rowspan=2, sticky="ne")
        self.chip_dot = ctk.CTkLabel(self.chip, text="●", font=self.f_small, text_color=t.GREY_DOT, height=26)
        self.chip_dot.pack(side="left", padx=(10, 4))
        self.chip_txt = self._label(self.chip, "Chưa xác định thiết bị", font=self.f_small, height=26)
        self.chip_txt.pack(side="left", padx=(0, 10))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.grid(row=1, column=0, sticky="ew", padx=16, pady=(10, 0))
        self._label(row, "ID đích", sub=True).pack(side="left")
        self.ent_id = self._entry(row, 62, 1)
        self.ent_id.pack(side="left", padx=(8, 18))
        self._label(row, "Chờ trả lời", sub=True).pack(side="left")
        self.ent_timeout = self._entry(row, 58, 200)
        self.ent_timeout.pack(side="left", padx=(8, 6))
        self._label(row, "ms", sub=True).pack(side="left")

        self.seg_tab = self._seg(card, [TAB_SCAN, TAB_CONFIG, TAB_TEST], self._show_tab, height=34)
        self.seg_tab.grid(row=2, column=0, sticky="ew", padx=16, pady=(10, 4))

        self.tabs = {}
        for name, builder in ((TAB_SCAN, self._build_scan), (TAB_CONFIG, self._build_config),
                              (TAB_TEST, self._build_test)):
            body = ctk.CTkScrollableFrame(card, fg_color="transparent", corner_radius=0,
                                          scrollbar_button_color=t.FIELD_BG,
                                          scrollbar_button_hover_color=t.FIELD_HOVER)
            body.grid_columnconfigure(0, weight=1)
            builder(body)
            self.tabs[name] = body
        self.seg_tab.set(TAB_SCAN)
        self._show_tab(TAB_SCAN)

    def _show_tab(self, name):
        for tab, body in self.tabs.items():
            if tab == name:
                body.grid(row=3, column=0, sticky="nsew", padx=(10, 4), pady=(4, 12))
            else:
                body.grid_forget()

    # ── Tab 1: Tìm thiết bị ──
    def _build_scan(self, s):
        t, app = self.t, self.app
        g = self._group(s)
        g.grid(row=0, column=0, sticky="ew", padx=6, pady=(2, 8))
        g.grid_columnconfigure(1, weight=1)

        def label(r, text, top=False):
            self._label(g, text, sub=True, width=66, anchor="w").grid(
                row=r, column=0, sticky="nw" if top else "w", padx=(12, 6), pady=(10 if r == 0 else 4, 4))

        label(0, "Phạm vi")
        self.seg_scope = self._seg(g, [SCOPE_PORT, SCOPE_ALL])
        self.seg_scope.set(SCOPE_PORT)
        self.seg_scope.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=(10, 4))

        label(1, "Cách dò")
        self.seg_mode = self._seg(g, [MODE_QUICK, MODE_IDS], lambda _v: self._sync_mode())
        self.seg_mode.set(MODE_QUICK)
        self.seg_mode.grid(row=1, column=1, sticky="ew", padx=(0, 12), pady=4)

        label(2, "Dải ID")
        rng = ctk.CTkFrame(g, fg_color="transparent")
        rng.grid(row=2, column=1, sticky="w", pady=4)
        self.ent_from = self._entry(rng, 58, 1)
        self.ent_from.pack(side="left")
        self._label(rng, "đến", sub=True).pack(side="left", padx=8)
        self.ent_to = self._entry(rng, 58, 247)
        self.ent_to.pack(side="left")

        label(3, "Baud", top=True)
        bf = ctk.CTkFrame(g, fg_color="transparent")
        bf.grid(row=3, column=1, sticky="ew", padx=(0, 8), pady=4)
        self.baud_vars = {}
        for i, baud in enumerate(mr.BAUD_SCAN_ORDER):
            var = tk.BooleanVar(value=baud in SCAN_BAUD_DEFAULT)
            self._check(bf, str(baud), var).grid(row=i // 4, column=i % 4, sticky="w", padx=(0, 4), pady=3)
            self.baud_vars[baud] = var

        label(4, "Parity")
        pf = ctk.CTkFrame(g, fg_color="transparent")
        pf.grid(row=4, column=1, sticky="w", pady=4)
        self.parity_vars = {}
        for i, name in enumerate(mr.PARITY_NAMES):
            var = tk.BooleanVar(value=True)
            self._check(pf, name, var).grid(row=0, column=i, sticky="w", padx=(0, 14))
            self.parity_vars[name] = var

        self._label(g, "Chỉ gửi lệnh ĐỌC (FC03 thanh ghi 0x4000) — không đổi trạng thái relay. "
                       "Dò nhanh cần bus chỉ có một module.", sub=True, font=self.f_small,
                    wraplength=360, justify="left").grid(row=5, column=0, columnspan=2, sticky="w",
                                                         padx=12, pady=(4, 10))

        btns = ctk.CTkFrame(s, fg_color="transparent")
        btns.grid(row=1, column=0, sticky="ew", padx=6)
        btns.grid_columnconfigure(0, weight=1)
        self.btn_scan = self._btn(btns, "Quét tìm thiết bị", self.start_scan, primary=True, height=40)
        self.btn_scan.grid(row=0, column=0, sticky="ew")
        self._btn(btns, "Dừng", self.stop, height=40, width=80, font=app.f_body).grid(
            row=0, column=1, padx=(8, 0))

        self.bar = ctk.CTkProgressBar(s, height=6, corner_radius=3, fg_color=t.FIELD_HOVER,
                                      progress_color=t.BLUE)
        self.bar.set(0)
        self.bar.grid(row=2, column=0, sticky="ew", padx=6, pady=(12, 4))
        pr = ctk.CTkFrame(s, fg_color="transparent")
        pr.grid(row=3, column=0, sticky="ew", padx=6)
        pr.grid_columnconfigure(0, weight=1)
        self.lbl_prog = self._label(pr, "Sẵn sàng", sub=True, font=self.f_small, anchor="w", height=18)
        self.lbl_prog.grid(row=0, column=0, sticky="w")
        self.lbl_count = self._label(pr, "", sub=True, font=app.f_mono_sm, height=18)
        self.lbl_count.grid(row=0, column=1, sticky="e")

        self._label(s, "KẾT QUẢ", sub=True, font=app.f_label, height=18).grid(
            row=4, column=0, sticky="w", padx=8, pady=(12, 4))
        self.results = ctk.CTkFrame(s, fg_color="transparent")
        self.results.grid(row=5, column=0, sticky="ew", padx=6)
        self.results.grid_columnconfigure(0, weight=1)
        self._show_results([])
        self._sync_mode()

    def _sync_mode(self):
        state = "normal" if self.seg_mode.get() == MODE_IDS else "disabled"
        color = self.t.TEXT_STRONG if state == "normal" else self.t.TEXT_SUB
        for ent in (self.ent_from, self.ent_to):
            ent.configure(state=state, text_color=color)

    # ── Tab 2: Cấu hình ──
    def _build_config(self, s):
        t, app = self.t, self.app
        g = self._group(s)
        g.grid(row=0, column=0, sticky="ew", padx=6, pady=(2, 8))
        g.grid_columnconfigure(1, weight=1)
        self._label(g, "Cấu hình đang chạy", font=self.f_bold).grid(row=0, column=0, sticky="w",
                                                                   padx=12, pady=(10, 6))
        self._btn(g, "Đọc lại", self.read_config, width=70).grid(row=0, column=1, sticky="e",
                                                                 padx=12, pady=(10, 6))
        self.cfg_vals = {}
        keys = ("Địa chỉ", "Tốc độ", "Parity", "Thanh ghi 0x2000", "Phiên bản", "Cổng giao tiếp")
        for r, key in enumerate(keys, start=1):
            last = r == len(keys)
            self._label(g, key, sub=True, anchor="w", height=22).grid(
                row=r, column=0, sticky="nw", padx=12, pady=(0, 10 if last else 0))
            val = self._label(g, "—", font=app.f_mono, anchor="w", justify="left", wraplength=230, height=22)
            val.grid(row=r, column=1, sticky="w", padx=(0, 12), pady=(0, 10 if last else 0))
            self.cfg_vals[key] = val

        g2 = self._group(s)
        g2.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 8))
        g2.grid_columnconfigure(0, weight=1)
        self._label(g2, "Ghi cấu hình mới", font=self.f_bold).grid(row=0, column=0, sticky="w",
                                                                  padx=12, pady=(10, 6))
        pre = ctk.CTkFrame(g2, fg_color="transparent")
        pre.grid(row=1, column=0, sticky="w", padx=12)
        self._label(pre, "Mẫu", sub=True).grid(row=0, column=0, rowspan=2, sticky="nw", padx=(0, 8), pady=2)
        for i, (text, addr, baud, parity) in enumerate(PRESETS):
            self._btn(pre, text, lambda a=addr, b=baud, p=parity: self._apply_preset(a, b, p)).grid(
                row=i, column=1, sticky="w", pady=2)

        fields = ctk.CTkFrame(g2, fg_color="transparent")
        fields.grid(row=2, column=0, sticky="w", padx=12, pady=(8, 4))
        for c, name in enumerate(("Địa chỉ mới", "Baud", "Parity")):
            self._label(fields, name.upper(), sub=True, font=app.f_label, height=16).grid(
                row=0, column=c, sticky="w", padx=(0, 10))
        self.ent_new_addr = self._entry(fields, 70, 7)
        self.ent_new_addr.grid(row=1, column=0, sticky="w", padx=(0, 10))
        self.opt_new_baud = app._menu(fields, [str(b) for b in mr.BAUD_CODES], "38400", width=104)
        self.opt_new_baud.grid(row=1, column=1, sticky="w", padx=(0, 10))
        self.opt_new_parity = app._menu(fields, list(mr.PARITY_NAMES), "None", width=90)
        self.opt_new_parity.grid(row=1, column=2, sticky="w")

        self.var_broadcast = tk.BooleanVar(value=False)
        ctk.CTkSwitch(g2, text="Gửi broadcast (ID 0) — khi quên địa chỉ", font=app.f_body,
                      variable=self.var_broadcast, progress_color=t.BLUE,
                      command=self._sync_broadcast).grid(row=3, column=0, sticky="w", padx=12, pady=(8, 4))
        self.warn = ctk.CTkFrame(g2, fg_color=t.WARN_BG, corner_radius=10)
        ctk.CTkLabel(self.warn, text="Broadcast đổi địa chỉ của MỌI module trên bus. Tháo module khỏi "
                                     "bus máy, chỉ để lại một mình nó.", font=self.f_small,
                     text_color=t.WARN_TEXT, wraplength=350, justify="left").pack(padx=10, pady=7, anchor="w")
        self.warn.grid(row=4, column=0, sticky="ew", padx=12, pady=4)
        self.warn.grid_remove()

        self.btn_write = self._btn(g2, "Ghi vào thiết bị", self.write_config_click, primary=True, height=40)
        self.btn_write.grid(row=5, column=0, sticky="ew", padx=12, pady=(8, 6))
        self._label(g2, "Bấm hai lần để ghi. Đổi tốc độ xong, tool tự chuyển cổng sang tốc độ mới và "
                        "đọc lại để xác nhận — tự sửa nếu module hiểu mã parity ngược tài liệu.",
                    sub=True, font=self.f_small, wraplength=360, justify="left").grid(
            row=6, column=0, sticky="w", padx=12, pady=(0, 10))

    def _sync_broadcast(self):
        if self.var_broadcast.get():
            self.warn.grid()
        else:
            self.warn.grid_remove()

    def _apply_preset(self, addr, baud, parity):
        self._set_entry(self.ent_new_addr, addr)
        self.opt_new_baud.set(str(baud))
        self.opt_new_parity.set(parity)

    # ── Tab 3: Test relay ──
    def _build_test(self, s):
        t, app = self.t, self.app
        top = ctk.CTkFrame(s, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=6, pady=(2, 0))
        top.grid_columnconfigure(1, weight=1)
        self.var_poll = tk.BooleanVar(value=False)
        ctk.CTkSwitch(top, text="Tự đọc trạng thái mỗi 1 s", font=app.f_body, variable=self.var_poll,
                      progress_color=t.BLUE, command=self._on_poll_toggle).grid(row=0, column=0, sticky="w")
        self._btn(top, "Đọc ngay", self.read_now, width=76).grid(row=0, column=2, sticky="e")

        tiles = ctk.CTkFrame(s, fg_color="transparent")
        tiles.grid(row=1, column=0, sticky="ew", padx=6, pady=(8, 4))
        tiles.grid_columnconfigure((0, 1), weight=1, uniform="tile")
        self.tiles = []
        for ch in range(mr.CHANNELS):
            tile = self._group(tiles)
            tile.grid(row=ch // 2, column=ch % 2, sticky="ew",
                      padx=(0, 4) if ch % 2 == 0 else (4, 0), pady=4)
            tile.grid_columnconfigure((0, 1, 2), weight=1, uniform="btn")
            self._label(tile, f"CH{ch + 1}", font=self.f_bold, height=22).grid(
                row=0, column=0, sticky="w", padx=(10, 0), pady=(8, 4))
            state = ctk.CTkLabel(tile, text="● —", font=self.f_small, text_color=t.TEXT_SUB, height=22)
            state.grid(row=0, column=1, columnspan=2, sticky="e", padx=(0, 10), pady=(8, 4))
            for i, (text, value) in enumerate((("Bật", mr.ON), ("Tắt", mr.OFF), ("Đảo", mr.TOGGLE))):
                self._btn(tile, text, lambda c=ch, v=value: self.channel(c, v), width=40).grid(
                    row=1, column=i, sticky="ew", padx=(10 if i == 0 else 3, 10 if i == 2 else 3),
                    pady=(0, 10))
            self.tiles.append((tile, state))

        g = self._group(s)
        g.grid(row=2, column=0, sticky="ew", padx=6, pady=(4, 8))
        g.grid_columnconfigure(1, weight=1)
        self._label(g, "Cả 8 kênh", font=self.f_bold, width=84, anchor="w").grid(
            row=0, column=0, sticky="w", padx=(12, 6), pady=(10, 4))
        allrow = ctk.CTkFrame(g, fg_color="transparent")
        allrow.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=(10, 4))
        allrow.grid_columnconfigure((0, 1, 2), weight=1, uniform="all")
        for i, (text, value) in enumerate((("Bật hết", mr.ON), ("Tắt hết", mr.OFF), ("Đảo hết", mr.TOGGLE))):
            self._btn(allrow, text, lambda v=value: self.all_channels(v), width=60).grid(
                row=0, column=i, sticky="ew", padx=(0 if i == 0 else 3, 0 if i == 2 else 3))

        self._label(g, "Nhấp nháy", font=self.f_bold, anchor="w").grid(
            row=1, column=0, columnspan=2, sticky="w", padx=12, pady=(8, 2))
        fl = ctk.CTkFrame(g, fg_color="transparent")
        fl.grid(row=2, column=0, columnspan=2, sticky="ew", padx=12)
        fl.grid_columnconfigure(1, weight=1)
        self.opt_flash_ch = app._menu(fl, [f"CH{i + 1}" for i in range(mr.CHANNELS)], "CH1", width=72)
        self.opt_flash_ch.grid(row=0, column=0, padx=(0, 6))
        self.opt_flash_mode = app._menu(fl, list(FLASH_MODES), FLASH_MODES[0], width=130)
        self.opt_flash_mode.grid(row=0, column=1, sticky="ew", padx=(0, 6))
        self.ent_flash_ms = self._entry(fl, 60, 700)
        self.ent_flash_ms.grid(row=0, column=2)
        self._label(fl, "ms", sub=True).grid(row=0, column=3, padx=(4, 6))
        self._btn(fl, "Gửi", self.flash, primary=True, width=52, height=30,
                  font=app.f_body).grid(row=0, column=4)

        self._label(g, "Chạy thử", font=self.f_bold, width=84, anchor="w").grid(
            row=3, column=0, sticky="w", padx=(12, 6), pady=(10, 12))
        self.btn_seq = self._btn(g, "Lần lượt CH1 → CH8, rồi tắt dần", self.sequence)
        self.btn_seq.grid(row=3, column=1, sticky="ew", padx=(0, 12), pady=(10, 12))

    # ═══════════════════════════ luồng phụ & đồng bộ ═══════════════════════════
    def busy(self):
        return self._job is not None and self._job.is_alive()

    def stop(self):
        self._cancel.set()
        self._pending = None

    def on_port_closed(self):
        """App gọi TRƯỚC khi đóng cổng: dừng tác vụ đang dùng cổng."""
        self.stop()
        self._set_chip("idle", "Cổng đang đóng")
        self._set_coils([None] * mr.CHANNELS)

    def log(self, text, tag="sys"):
        """Luồng phụ gọi — in một dòng vào terminal."""
        self.app.ui_call(self._log_line, text, tag)

    def _new_line(self):
        # Dữ liệu thô của terminal có thể chưa xuống dòng → ngắt trước để dòng panel khỏi dính vào.
        if not self.app._need_ts:
            self.app._append_log("\n", "sys")

    def _log_line(self, text, tag):
        self._new_line()
        self.app._append_log(text + "\n", tag)

    def _on_frame(self, kind, data, note):
        """ModbusRtuClient gọi (luồng phụ) mỗi khi gửi/nhận một khung."""
        if self.quiet:
            return
        mark = {"tx": "»", "rx": "«"}.get(kind, "·")
        tag = kind if kind in ("tx", "rx") else "sys"
        if kind == "junk":
            note = f"{note} ({len(data)} byte)"
        self.app.ui_call(self._log_frame, f"{mark} {mr.hexs(data)}", tag, note)

    def _log_frame(self, text, tag, note):
        self._new_line()
        self.app._append_log(text.ljust(30) + "  ", tag)
        self.app._append_log(f"{note}\n", "sys")

    def _snapshot(self, need_target=True, silent=False):
        """Chụp mọi thông số luồng phụ cần — CHỈ gọi trên luồng Tk."""
        app = self.app
        try:
            target = int(self.ent_id.get().strip())
        except ValueError:
            target = 0
        if need_target and not 1 <= target <= 255:
            if not silent:
                self._status("Nhập ID đích 1–255, hoặc bấm Quét tìm thiết bị")
            return None
        try:
            timeout_ms = max(20, min(5000, int(self.ent_timeout.get().strip())))
        except ValueError:
            timeout_ms = 200
            self._set_entry(self.ent_timeout, timeout_ms)
        parity = app.opt_parity.get()
        return {"target": target if 0 <= target <= 255 else 0, "timeout_ms": timeout_ms,
                "port": app.selected_port(), "baud": int(app.opt_baud.get()),
                "parity": parity if parity in mr.PARITY_NAMES else "None",
                "dtr": bool(app.dtr_var.get()), "rts": bool(app.rts_var.get()),
                "open": app.sm.snapshot()}

    def _run(self, fn, snap, quiet=False, poll=False, label=None):
        if self.busy():
            if self._job_is_poll and not poll:
                self._pending = (fn, snap, quiet, label)
                return True
            if not poll:
                self._status(BUSY_TEXT)
            return False
        self._cancel = threading.Event()
        self.relay.cancel = self._cancel
        self.relay.timeout_ms = snap["timeout_ms"]
        self._job_is_poll = poll
        if label:
            self._status(label)

        def worker():
            self.quiet = quiet
            self.client.begin()
            try:
                fn(snap)
            except mr.ModbusCancelled:
                if not poll:
                    self.log("Đã dừng — relay giữ nguyên trạng thái hiện tại")
            except mr.ModbusError as exc:
                if not poll:
                    self.log(f"✗ {exc}", "err")
            except (serial.SerialException, OSError, ValueError) as exc:
                if not poll:
                    self.log(f"✗ Lỗi cổng: {exc}", "err")
            except Exception as exc:        # luồng phụ chết im lặng thì panel kẹt "bận" mãi
                self.log(f"✗ Lỗi không lường trước: {exc!r}", "err")
            finally:
                self.client.end()
                self.quiet = False
                self.app.ui_call(self._job_done, poll)

        self._job = threading.Thread(target=worker, name="modbus-relay", daemon=True)
        self._job.start()
        return True

    def _job_done(self, poll):
        if self._job is not None:
            self._job.join(timeout=0.5)
        self._job_is_poll = False
        if not poll:
            self.app._refresh_connection_ui()
            self._set_scanning(False)
            self._set_seq(False)
        if self._pending:
            fn, snap, quiet, label = self._pending
            self._pending = None
            self._run(fn, snap, quiet=quiet, label=label)

    def _configure(self, baud, parity):
        """Luồng phụ: đổi cổng đang mở sang baud/parity, 8 bit, 1 stop, không flow."""
        try:
            self.app.sm.configure({"baudrate": baud, "bytesize": 8, "parity": parity.lower(),
                                   "stopbits": 1, **NO_FLOW})
        except (serial.SerialException, ValueError, OSError):
            return False
        self.cur_baud, self.cur_parity = baud, parity
        time.sleep(0.02)
        return True

    def _ensure_port(self, snap, port=None, baud=None, parity=None):
        """Luồng phụ: bảo đảm cổng đang mở đúng cổng + cấu hình. Trả tên cổng."""
        if self._cancel.is_set():
            raise mr.ModbusCancelled()
        sm = self.app.sm
        cur = sm.snapshot()
        if port is None:
            port = cur["port"] if cur else snap["port"]
        if not port:
            raise mr.ModbusError("Chưa chọn cổng COM")
        if baud is None:
            if cur and cur["port"] == port:
                baud, parity = cur["baudrate"], PARITY_BY_LETTER.get(cur["parity"], "None")
            else:
                baud, parity = snap["baud"], snap["parity"]
        if cur and cur["port"] != port:
            sm.close()
            cur = None
        if cur is None:
            sm.open(port, baud, serial.EIGHTBITS, PARITY_BY_NAME[parity], serial.STOPBITS_ONE, dict(NO_FLOW))
            sm.set_dtr(snap["dtr"])
            sm.set_rts(snap["rts"])
            self.log(f"Đã mở {port} @ {baud} 8{parity[0]}1")
        if not self._configure(baud, parity):
            raise mr.ModbusError(f"Driver {port} không nhận {baud} baud")
        return port

    # ═══════════════════════════════ tìm thiết bị ═══════════════════════════════
    def start_scan(self):
        snap = self._snapshot(need_target=False)
        if snap is None:
            return
        bauds = [b for b in mr.BAUD_SCAN_ORDER if self.baud_vars[b].get()]
        parities = [p for p in mr.PARITY_NAMES if self.parity_vars[p].get()]
        if not bauds or not parities:
            self._status("Chọn ít nhất một tốc độ và một parity để quét")
            return
        ids = None
        if self.seg_mode.get() == MODE_IDS:
            try:
                a, b = int(self.ent_from.get()), int(self.ent_to.get())
            except ValueError:
                self._status("Dải ID phải là số 1–255")
                return
            a, b = max(1, min(a, b)), min(255, max(a, b))
            ids = list(range(a, b + 1))
        all_ports = self.seg_scope.get() == SCOPE_ALL
        if not all_ports and not (snap["open"] or snap["port"]):
            self._status("Chưa chọn cổng COM")
            return
        opts = {"bauds": bauds, "parities": parities, "ids": ids, "all_ports": all_ports}
        self._show_results([])
        if self._run(lambda s: self._scan_job(s, opts), snap, quiet=True, label="Đang quét tìm thiết bị…"):
            self._set_scanning(True)

    def _scan_job(self, snap, opts):
        sm = self.app.sm
        orig = sm.snapshot()
        if opts["all_ports"]:
            ports = []
            for info in serial.tools.list_ports.comports():
                if "bluetooth" in (info.description or "").lower():
                    self.log(f"Bỏ qua {info.device} (cổng Bluetooth, mở rất lâu)")
                    continue
                ports.append(info.device)
        else:
            ports = [orig["port"] if orig else snap["port"]]
        combos = [(b, p) for b in opts["bauds"] for p in opts["parities"]]
        ids = opts["ids"]
        per_port = len(combos) * (len(ids) if ids else 1)
        total = max(1, per_port * len(ports))
        step_s = self.relay.timeout_ms / 1000 + 0.03
        what = f"ID {ids[0]}–{ids[-1]}" if ids else "broadcast"
        self.log(f"── Quét tìm thiết bị · {len(ports)} cổng · {len(opts['bauds'])} tốc độ × "
                 f"{len(opts['parities'])} parity · {what} ──")

        results, base = [], 0
        for port in ports:
            try:
                self._ensure_port(snap, port=port, baud=combos[0][0], parity=combos[0][1])
            except mr.ModbusCancelled:
                raise
            except (serial.SerialException, OSError, mr.ModbusError) as exc:
                self.log(f"{port}: không mở được — {exc}", "err")
                base += per_port
                continue

            def progress(done, _total, text, base=base, port=port):
                n = base + done
                self.app.ui_call(self._set_progress, n / total, f"{port} · {text}", n, total,
                                 (total - n) * step_s)

            found = mr.scan_combos(self.relay, self._configure, combos, ids, on_progress=progress,
                                   on_log=lambda m, port=port: self.log(f"{port} · {m}"))
            for item in found:
                item["port"] = port
            results.extend(found)
            base += per_port
            self.app.ui_call(self._show_results, list(results))
            if any(item["kind"] == "waveshare" for item in found):
                break
        self.app.ui_call(self._set_progress, 1.0, "Xong", total, total, 0)

        module = next((item for item in results if item["kind"] == "waveshare"), None)
        if module is None:
            extra = f" Có {len(results)} thiết bị Modbus khác trả lời." if results else ""
            self.log("✗ Không thấy module relay. Kiểm tra dây A–A / B–B và nguồn module, rồi bật thêm "
                     "tốc độ/parity hoặc dò từng ID." + extra, "err")
            self._restore(snap, orig)
            return
        self._ensure_port(snap, port=module["port"], baud=module["baud"], parity=module["parity"])
        self.log(f"✓ Thấy module relay · {module['port']} · ID {module['address']} · {module['baud']} "
                 f"8{module['parity'][0]}1 · {module['version'] or 'chưa đọc được phiên bản'}", "ok")
        self.app.ui_call(self._adopt, module)
        self.quiet = False
        self.app.ui_call(self._set_coils, self.relay.read_coils(module["address"]), module["address"])

    def _restore(self, snap, orig):
        """Quét hụt: trả cổng về đúng như trước khi quét."""
        if orig is None:
            self.app.sm.close()
            return
        self._ensure_port(snap, port=orig["port"], baud=orig["baudrate"],
                          parity=PARITY_BY_LETTER.get(orig["parity"], "None"))

    def use_result(self, item):
        snap = self._snapshot(need_target=False)
        if snap is None:
            return

        def job(s):
            self._ensure_port(s, port=item["port"], baud=item["baud"], parity=item["parity"])
            self.app.ui_call(self._adopt, item)
            self.app.ui_call(self._set_coils, self.relay.read_coils(item["address"]), item["address"])

        self._run(job, snap)

    def _adopt(self, module):
        """Luồng Tk: nhận module vừa tìm được làm thiết bị đang làm việc."""
        self.device = dict(module)
        self._set_entry(self.ent_id, module["address"])
        self._set_entry(self.ent_new_addr, module["address"])
        self.opt_new_baud.set(str(module["baud"]))
        self.opt_new_parity.set(module["parity"])
        self._chip_for(module["address"])

    def _set_scanning(self, on):
        if on:
            self.bar.set(0)
            self.lbl_prog.configure(text="Đang quét…")
            self.lbl_count.configure(text="")
            self.btn_scan.configure(text="Đang quét…", state="disabled")
        else:
            self.btn_scan.configure(text="Quét tìm thiết bị", state="normal")

    def _set_progress(self, frac, text, n, total, eta_s):
        self.bar.set(max(0.0, min(1.0, frac)))
        self.lbl_prog.configure(text=text)
        eta = f" · còn ~{math.ceil(eta_s)} s" if eta_s >= 1 else ""
        self.lbl_count.configure(text=f"{n} / {total}{eta}")

    def _show_results(self, items):
        t = self.t
        for child in self.results.winfo_children():
            child.destroy()
        if not items:
            self._label(self.results, "Chưa có — bấm Quét tìm thiết bị", sub=True,
                        font=self.f_small, height=20).grid(row=0, column=0, sticky="w", padx=2)
            return
        for r, item in enumerate(items):
            row = self._group(self.results)
            row.grid(row=r, column=0, sticky="ew", pady=(0, 6))
            row.grid_columnconfigure(1, weight=1)
            ok = item["kind"] == "waveshare"
            ctk.CTkLabel(row, text="●", font=self.f_small, text_color=t.GREEN if ok else t.ORANGE,
                         width=14).grid(row=0, column=0, rowspan=2, padx=(12, 6))
            title = f"Module relay · ID {item['address']}" if ok else \
                f"Thiết bị Modbus khác · ID {item['address']}"
            self._label(row, title, font=self.f_bold, height=20).grid(row=0, column=1, sticky="w", pady=(8, 0))
            parts = [item.get("port", "?"), f"{item['baud']} 8{item['parity'][0]}1"]
            if item.get("version"):
                parts.append(item["version"])
            if item.get("detail"):
                parts.append(item["detail"])
            self._label(row, " · ".join(parts), sub=True, font=self.app.f_mono_sm, height=18,
                        wraplength=280, justify="left").grid(row=1, column=1, sticky="w", pady=(0, 8))
            if ok:
                self._btn(row, "Dùng", lambda i=item: self.use_result(i), primary=True, width=58,
                          font=self.app.f_body).grid(row=0, column=2, rowspan=2, padx=12)

    # ═════════════════════════════════ cấu hình ═════════════════════════════════
    def read_config(self):
        snap = self._snapshot(need_target=False)
        if snap is not None:
            self._run(self._read_config_job, snap, label="Đang đọc cấu hình…")

    def _read_config_job(self, snap):
        port = self._ensure_port(snap)
        addr = snap["target"]
        if not 1 <= addr <= 255:
            addr = self.relay.read_address(0)
            self.log(f"Broadcast trả địa chỉ = {addr}")
        cfg = self._read_config_checked(port, addr)
        self.app.ui_call(self._show_config, cfg)

    def _read_config_checked(self, port, addr):
        """Luồng phụ: đọc cấu hình; nếu parity giải mã lệch parity cổng đang chạy
        thì module đang hiểu mã Even/Odd ngược tài liệu → đổi bảng mã rồi giải lại."""
        cfg = self.relay.read_config(addr)
        if {cfg["parity"], self.cur_parity} == {"Even", "Odd"}:
            codes = self.relay.parity_codes
            codes["Even"], codes["Odd"] = codes["Odd"], codes["Even"]
            cfg["baud"], cfg["parity"] = mr.decode_uart(cfg["uart_raw"], codes)
            self.log("Module hiểu mã parity NGƯỢC tài liệu — đã đổi bảng mã cho đúng")
        cfg.update(port=port, port_baud=self.cur_baud, port_parity=self.cur_parity)
        return cfg

    def _show_config(self, cfg):
        v, raw, addr = self.cfg_vals, cfg["uart_raw"], cfg["address"]
        v["Địa chỉ"].configure(text=f"{addr}  (0x{addr:02X})")
        v["Tốc độ"].configure(text=f"{cfg['baud']} baud" if cfg["baud"] else f"mã lạ 0x{raw & 0xFF:02X}")
        v["Parity"].configure(text=cfg["parity"] or f"mã lạ 0x{raw >> 8:02X}")
        v["Thanh ghi 0x2000"].configure(text=f"0x{raw:04X}")
        v["Phiên bản"].configure(text=cfg["version"])
        v["Cổng giao tiếp"].configure(text=f"{cfg['port']} · {cfg['port_baud']} 8{cfg['port_parity'][0]}1")
        self.device = {"address": addr, "baud": cfg["port_baud"], "parity": cfg["port_parity"],
                       "version": cfg["version"], "port": cfg["port"]}
        self._set_entry(self.ent_id, addr)
        self._chip_for(addr)

    def write_config_click(self):
        try:
            new_addr = int(self.ent_new_addr.get().strip())
        except ValueError:
            new_addr = 0
        if not 1 <= new_addr <= 255:
            self._status("Địa chỉ mới phải trong 1–255")
            return
        broadcast = self.var_broadcast.get()
        snap = self._snapshot(need_target=not broadcast)
        if snap is None:
            return
        if self._confirm_after is None:
            t = self.t
            self.btn_write.configure(text="Bấm lần nữa để ghi", fg_color=t.ORANGE, hover_color=t.ORANGE)
            self._confirm_after = self.app.after(CONFIRM_MS, self._reset_confirm)
            return
        self._reset_confirm()
        target = {"address": new_addr, "baud": int(self.opt_new_baud.get()),
                  "parity": self.opt_new_parity.get()}
        self._run(lambda s: self._write_job(s, target, broadcast), snap, label="Đang ghi cấu hình…")

    def _reset_confirm(self):
        if self._confirm_after is not None:
            try:
                self.app.after_cancel(self._confirm_after)
            except (tk.TclError, ValueError):
                pass
            self._confirm_after = None
        self.btn_write.configure(text="Ghi vào thiết bị", fg_color=self.t.BLUE, hover_color=self.t.BLUE_HOVER)

    def _write_job(self, snap, target, broadcast):
        port = self._ensure_port(snap)
        current = {"address": snap["target"], "baud": self.cur_baud, "parity": self.cur_parity}
        if not broadcast and current == target:
            self.log("Cấu hình mới trùng cấu hình đang chạy — không ghi gì")
            return
        sender = "broadcast" if broadcast else f"ID {current['address']}"
        self.log(f"── Ghi cấu hình · {port} · {sender} → ID {target['address']} · "
                 f"{target['baud']} 8{target['parity'][0]}1 ──")
        result = mr.write_config(self.relay, self._configure, current, target,
                                 broadcast=broadcast, on_log=self.log)
        self.log(f"✓ Đã ghi và xác nhận · ID {result['address']} · {result['baud']} "
                 f"8{result['parity'][0]}1", "ok")
        self.app.ui_call(self._show_config, self._read_config_checked(port, result["address"]))

    # ═════════════════════════════════ test relay ═════════════════════════════════
    def channel(self, ch, value):
        self._relay_action(lambda addr: self.relay.write_channel(addr, ch, value))

    def all_channels(self, value):
        self._relay_action(lambda addr: self.relay.write_all(addr, value))

    def read_now(self):
        self._relay_action(None)

    def flash(self):
        ch = int(self.opt_flash_ch.get()[2:]) - 1
        on_first = self.opt_flash_mode.get() == FLASH_MODES[0]
        try:
            ms = int(self.ent_flash_ms.get().strip())
        except ValueError:
            self._status("Thời gian nhấp nháy phải là số mili-giây")
            return
        tenths = max(1, min(mr.FLASH_MAX_TENTHS, round(ms / 100)))
        self._relay_action(lambda addr: self.relay.flash(addr, ch, on_first, tenths))

    def _relay_action(self, action):
        snap = self._snapshot()
        if snap is None:
            return

        def job(s):
            self._ensure_port(s)
            addr = s["target"]
            if action is not None:
                action(addr)
            self.app.ui_call(self._set_coils, self.relay.read_coils(addr), addr)

        self._run(job, snap)

    def sequence(self):
        if self._seq_running:
            self.stop()
            return
        snap = self._snapshot()
        if snap is None:
            return

        def job(s):
            self._ensure_port(s)
            addr = s["target"]
            for value in (mr.ON, mr.OFF):
                for ch in range(mr.CHANNELS):
                    self.relay.write_channel(addr, ch, value)
                    self.app.ui_call(self._set_coils, self.relay.read_coils(addr), addr)
                    if self._cancel.wait(0.3):
                        raise mr.ModbusCancelled()

        if self._run(job, snap, label="Đang chạy thử 8 kênh…"):
            self._set_seq(True)

    def _set_seq(self, on):
        self._seq_running = on
        self.btn_seq.configure(text="Dừng chạy thử" if on else "Lần lượt CH1 → CH8, rồi tắt dần")

    def _on_poll_toggle(self):
        if self.var_poll.get() and not self.app.sm.is_open():
            self._status("Tự đọc chạy khi cổng đang mở — bấm Open hoặc Quét tìm thiết bị")

    def _poll_tick(self):
        try:
            if self.var_poll.get() and not self.busy():
                snap = self._snapshot(silent=True)
                if snap is not None and snap["open"]:
                    self._run(self._poll_job, snap, quiet=True, poll=True)
        finally:
            self.app.after(POLL_MS, self._poll_tick)

    def _poll_job(self, snap):
        self.cur_baud = snap["open"]["baudrate"]
        addr = snap["target"]
        try:
            coils = self.relay.read_coils(addr)
        except mr.ModbusError:
            self._poll_fail += 1
            if self._poll_fail >= POLL_FAIL_LIMIT:
                self._poll_fail = 0
                self.app.ui_call(self._poll_lost, addr)
            return
        self._poll_fail = 0
        self.app.ui_call(self._set_coils, coils, addr)

    def _poll_lost(self, addr):
        self.var_poll.set(False)
        self._set_chip("warn", f"Mất trả lời · ID {addr}")
        self._log_line(f"✗ Tự đọc trạng thái: ID {addr} không trả lời {POLL_FAIL_LIMIT} lần liền "
                       "— đã tắt tự đọc", "err")

    # ═════════════════════════════ hiển thị trạng thái ═════════════════════════════
    def _set_coils(self, coils, addr=None):
        t = self.t
        for (tile, state), on in zip(self.tiles, coils):
            if on is None:
                tile.configure(fg_color=t.GLASS_INNER, border_color=t.CARD_BORDER)
                state.configure(text="● —", text_color=t.TEXT_SUB)
            elif on:
                tile.configure(fg_color=t.ON_BG, border_color=t.GREEN)
                state.configure(text="● BẬT", text_color=t.OK_TEXT)
            else:
                tile.configure(fg_color=t.GLASS_INNER, border_color=t.CARD_BORDER)
                state.configure(text="● TẮT", text_color=t.TEXT_SUB)
        if addr is not None:
            self._chip_for(addr)

    def _chip_for(self, addr):
        text = f"ID {addr} · {self.cur_baud} 8{self.cur_parity[0]}1"
        if self.device and self.device.get("address") == addr and self.device.get("version"):
            text += f" · {self.device['version']}"
        self._set_chip("ok", text)

    def _set_chip(self, state, text):
        t = self.t
        bg, dot = {"ok": (t.ON_BG, t.GREEN), "idle": (t.FIELD_BG, t.GREY_DOT),
                   "warn": (t.WARN_BG, t.ORANGE)}[state]
        self.chip.configure(fg_color=bg)
        self.chip_dot.configure(text_color=dot)
        self.chip_txt.configure(text=text)
