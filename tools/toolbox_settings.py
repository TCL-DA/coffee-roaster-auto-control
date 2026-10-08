"""
Trang CÀI ĐẶT của OTL Toolbox — một trang, 4 thẻ thông số, không tab con, không cuộn.

Mỗi ô ở đây là "gương" của ô trong bộ máy (App gốc): chọn ở đây thì đặt thẳng vào
ô gốc và gọi đúng lệnh của ô gốc, nên logic lưu/áp dụng vẫn là của công cụ. Ô nào bị
đổi từ nơi khác (MCP/API) thì trang này tự đồng bộ theo nhịp SYNC_MS.
Giao diện đầy đủ của từng công cụ (Modbus relay, đồ thị replay, Kalman…) mở trong
khung trượt bằng nút "Giao diện đầy đủ".
"""
import tkinter as tk

import customtkinter as ctk

FONT = "Segoe UI"
MONO = "Consolas"
INK = "#1E293B"
MUTED = "#64748B"
CARD = "#FFFFFF"
FIELD = "#F1F5F9"
LINE = "#E2E8F0"
BRAND = "#C62828"
LOCK = "#B45309"
SYNC_MS = 700


class SettingsPage(ctk.CTkFrame):
    def __init__(self, master, engines: dict, open_full):
        super().__init__(master, fg_color="transparent")
        self.engines = engines
        self.open_full = open_full
        self.mirrors = []          # (ô gương, ô gốc, hàm lấy giá trị gốc)
        self.locks = []            # (danh sách ô khoá khi nối, nhãn báo, hàm "đang nối?")
        self.f_h = ctk.CTkFont(FONT, 15, "bold")
        self.f_b = ctk.CTkFont(FONT, 13)
        self.f_s = ctk.CTkFont(FONT, 12)
        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=16, pady=16)
        for c in range(2):
            grid.grid_columnconfigure(c, weight=1, uniform="c")
        for r in range(2):
            grid.grid_rowconfigure(r, weight=1, uniform="r")
        self._bt_card(grid).grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))
        self._scale_card(grid).grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=(0, 8))
        self._terminal_card(grid).grid(row=1, column=0, sticky="nsew", padx=(0, 8), pady=(8, 0))
        self._monitor_card(grid).grid(row=1, column=1, sticky="nsew", padx=(8, 0), pady=(8, 0))
        self.after(SYNC_MS, self._sync)

    # ═════ khối dùng chung ═════
    def _card(self, parent, title, key, full_text="Giao diện đầy đủ  ›"):
        card = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=14)
        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill="x", padx=20, pady=(16, 6))
        ctk.CTkLabel(head, text=title, text_color=INK, font=self.f_h).pack(side="left")
        ctk.CTkButton(head, text=full_text, height=40, corner_radius=8, fg_color=FIELD,
                      hover_color=LINE, text_color=INK, font=self.f_b,
                      command=lambda: self.open_full(key)).pack(side="right")
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=(4, 16))
        return card, body

    def _field(self, parent, label, row, col, colspan=1):
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.grid(row=row, column=col, columnspan=colspan, sticky="ew", padx=(0, 12), pady=(0, 12))
        ctk.CTkLabel(box, text=label, text_color=MUTED, font=self.f_s).pack(anchor="w")
        return box

    def _mirror_menu(self, parent, src, width, rescan=None):
        """Ô chọn gương của CTkOptionMenu/ComboBox gốc. `rescan` = hàm quét lại cổng COM."""
        def on_pick(value):
            src.set(value)
            cmd = getattr(src, "_command", None)
            if callable(cmd):
                cmd(value)
        menu = ctk.CTkOptionMenu(parent, values=list(src.cget("values")), width=width, height=40,
                                 fg_color=FIELD, button_color=FIELD, button_hover_color=LINE,
                                 text_color=INK, font=self.f_b, dropdown_font=self.f_b,
                                 command=on_pick)
        menu.set(src.get())
        if rescan is not None:
            orig_open = menu._open_dropdown_menu

            def open_with_rescan():
                rescan()
                menu.configure(values=list(src.cget("values")))
                menu.set(src.get())
                orig_open()
            menu._open_dropdown_menu = open_with_rescan
        menu.pack(anchor="w", fill="x")
        self.mirrors.append((menu, src, src.get))
        return menu

    def _mirror_entry(self, parent, src, width):
        """Ô nhập gương: gõ xong (Enter / rời ô) mới chép vào ô gốc."""
        var = tk.StringVar(value=src.get())
        ent = ctk.CTkEntry(parent, textvariable=var, width=width, height=40, fg_color=FIELD,
                           border_width=0, font=self.f_b, justify="center")

        def commit(_e=None):
            src.delete(0, "end")
            src.insert(0, var.get())
        ent.bind("<Return>", commit)
        ent.bind("<FocusOut>", commit)
        ent.pack(anchor="w")
        self.mirrors.append((ent, src, src.get))
        return ent

    def _switch(self, parent, text, variable):
        sw = ctk.CTkSwitch(parent, text=text, variable=variable, font=self.f_b, text_color=INK,
                           progress_color=BRAND)
        sw.pack(anchor="w", pady=4)
        return sw

    def _lock_note(self, parent, row, is_open, widgets):
        note = ctk.CTkLabel(parent, text="", text_color=LOCK, font=self.f_s, anchor="w")
        note.grid(row=row, column=0, columnspan=6, sticky="w")
        self.locks.append((widgets, note, is_open))

    def _serial_fields(self, body, eng, names, rescan):
        """Cổng + các ô thông số nối tiếp (Baud/Data/Parity/Stop/Handshake) của một bộ máy."""
        port_box = self._field(body, "Cổng COM", 0, 0, colspan=len(names))
        widgets = [self._mirror_menu(port_box, eng.opt_port, 420, rescan=rescan)]
        for c, name in enumerate(names):
            box = self._field(body, name, 1, c)
            widgets.append(self._mirror_menu(box, getattr(eng, f"opt_{name.lower()}"), 110))
        return widgets

    # ═════ 4 thẻ ═════
    def _bt_card(self, parent):
        card, body = self._card(parent, "BT Tester", "bt")
        bt = self.engines["bt"]
        widgets = self._serial_fields(body, bt, ["Baud", "Data", "Parity", "Stop"], bt.refresh_ports)
        self._lock_note(body, 2, bt.sm.is_open, widgets)
        ctk.CTkLabel(body, text="Phát lại hồ sơ, đồ thị replay, trần RoR → Giao diện đầy đủ",
                     text_color=MUTED, font=self.f_s).grid(row=3, column=0, columnspan=6, sticky="w",
                                                           pady=(8, 0))
        return card

    def _scale_card(self, parent):
        card, body = self._card(parent, "Cân giả lập", "scale")
        sc = self.engines["scale"]
        port_box = self._field(body, "Cổng COM", 0, 0, colspan=3)
        widgets = [self._mirror_menu(port_box, sc.opt_port, 420, rescan=sc.refresh_ports)]
        widgets.append(self._mirror_menu(self._field(body, "Baud", 1, 0), sc.opt_baud, 110))
        self._mirror_entry(self._field(body, "Chu kỳ gửi (ms)", 1, 1), sc.ent_interval, 110)
        self._mirror_menu(self._field(body, "Trạng thái", 1, 2), sc.opt_status, 110)
        self._lock_note(body, 2, lambda: sc.sending, widgets)
        opts = ctk.CTkFrame(body, fg_color="transparent")
        opts.grid(row=3, column=0, columnspan=3, sticky="w", pady=(6, 0))
        self._switch(opts, "Gửi 2 số lẻ (61.45)", sc.var_2dec)
        ror = ctk.CTkFrame(opts, fg_color="transparent")
        ror.pack(anchor="w")
        sw = ctk.CTkSwitch(ror, text="RoR tự động", variable=sc.var_ror, font=self.f_b,
                           text_color=INK, progress_color=BRAND, command=sc._reset_ror)
        sw.pack(side="left")
        ctk.CTkLabel(ror, text="tốc độ (kg/phút)", text_color=MUTED, font=self.f_s).pack(
            side="left", padx=(12, 6))
        box = ctk.CTkFrame(ror, fg_color="transparent")
        box.pack(side="left")
        self._mirror_entry(box, sc.ent_ror, 80)
        return card

    def _terminal_card(self, parent):
        card, body = self._card(parent, "Serial Terminal", "terminal", "Modbus relay · đầy đủ  ›")
        term = self.engines["terminal"]
        widgets = self._serial_fields(body, term, ["Baud", "Data", "Parity", "Stop", "Handshake"],
                                      term.refresh_ports)
        self._lock_note(body, 2, term.sm.is_open, widgets)
        api = getattr(term, "api", None)
        addr = f"{getattr(api, 'host', '127.0.0.1')}:{getattr(api, 'port', '8765')}" if api else "—"
        ctk.CTkLabel(body, text=f"API cho AI/MCP: {addr}  ·  dò ID, cấu hình, test relay → Modbus relay",
                     text_color=MUTED, font=self.f_s).grid(row=3, column=0, columnspan=6, sticky="w",
                                                           pady=(8, 0))
        return card

    def _monitor_card(self, parent):
        card, body = self._card(parent, "Roaster Monitor", "monitor")
        mon = self.engines["monitor"]
        ctk.CTkLabel(body, text="Thư mục Artisan lưu CSV", text_color=MUTED, font=self.f_s).pack(anchor="w")
        row = ctk.CTkFrame(body, fg_color=FIELD, corner_radius=10)
        row.pack(fill="x", pady=(2, 0))
        ctk.CTkLabel(row, textvariable=mon.dir_var, text_color=INK, anchor="w",
                     font=ctk.CTkFont(MONO, 12)).pack(side="left", fill="x", expand=True, padx=12, pady=10)
        ctk.CTkButton(row, text="Đổi thư mục", width=120, height=40, corner_radius=8, fg_color=CARD,
                      hover_color=LINE, text_color=INK, font=self.f_b,
                      command=mon._pick_dir).pack(side="right", padx=6, pady=6)
        ctk.CTkLabel(body, text="Công cụ đọc file CSV mới nhất trong thư mục mỗi giây; "
                                "RoR tính trên cửa sổ 30 giây.",
                     text_color=MUTED, font=self.f_s, wraplength=600, justify="left").pack(anchor="w",
                                                                                         pady=(10, 0))
        return card

    # ═════ đồng bộ ═════
    def _sync(self):
        try:
            for widget, src, getter in self.mirrors:
                value = getter()
                if widget.focus_get() is not None and str(widget.focus_get()).startswith(str(widget)):
                    continue        # đang gõ trong ô này thì không chép đè
                if isinstance(widget, ctk.CTkOptionMenu):
                    if widget.get() != value:
                        widget.set(value)
                elif widget.get() != value:
                    widget.delete(0, "end")
                    widget.insert(0, value)
            for widgets, note, is_open in self.locks:
                busy = bool(is_open())
                for w in widgets:
                    w.configure(state="disabled" if busy else "normal")
                note.configure(text="Đang nối — ngắt kết nối ở màn Làm việc để đổi cổng / tốc độ"
                               if busy else "")
        finally:
            self.after(SYNC_MS, self._sync)
