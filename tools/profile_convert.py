"""
Chuyển profile — giao diện mới (cùng kiểu thẻ sáng với BT Tester / Scale) cho bộ
chuyển file rang của project 101 (OTLRoastLab). Phần xử lý dùng NGUYÊN converter.py
của 101: đọc .txt/.csv/.alog, bù dòng thiếu, ghi CSV Artisan + .alog, soát mốc rang.

App 101 chạy riêng (F:/Project/101_profile_convert) vẫn giữ nguyên, không phụ thuộc file này.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
import uuid
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

FROZEN = getattr(sys, "frozen", False)
PROFILE_CONVERT_SRC = Path(r"F:\Project\101_profile_convert\src")
if not FROZEN and str(PROFILE_CONVERT_SRC) not in sys.path:
    sys.path.insert(0, str(PROFILE_CONVERT_SRC))

from converter import (convert, extract_milestones_alog, extract_milestones_csv,  # noqa: E402
                       extract_milestones_txt, fill_gaps, parse_alog, parse_csv_rows,
                       parse_txt, validate_rows_integrity, write_alog, write_csv,
                       write_fixed_txt)

FONT = "Segoe UI"
MONO = "Consolas"
INK = "#1E293B"
MUTED = "#64748B"
CARD = "#FFFFFF"
BG = "#EEF2F7"
FIELD = "#F1F5F9"
LINE = "#E2E8F0"
BRAND = "#C62828"
BRAND_HOVER = "#A31F1F"
OK = "#15803D"
BAD = "#B91C1C"
SOURCE_EXT = (".txt", ".csv", ".alog")


def _parse_any(path: str):
    """Đọc rows + milestones theo đuôi file (.txt / .alog / .csv)."""
    ext = Path(path).suffix.lower()
    try:
        if ext == ".alog":
            return parse_alog(path)
        if ext == ".csv":
            return parse_csv_rows(path), {}
        return parse_txt(path)
    except Exception:
        return [], {}


def _ms_any(path: str) -> dict:
    """Tóm tắt mốc rang theo đuôi file."""
    ext = Path(path).suffix.lower()
    try:
        if ext == ".alog":
            return extract_milestones_alog(path)
        if ext == ".csv":
            return extract_milestones_csv(path)
        return extract_milestones_txt(path)
    except Exception:
        return {}


def _natkey(name: str):
    return [int(s) if s.isdigit() else s.lower() for s in re.split(r"(\d+)", name)]


def _mmss(s) -> str:
    return f"{int(s) // 60:02d}:{int(s) % 60:02d}" if s else "—"


def chart_command(json_path: str) -> list:
    """Lệnh mở đồ thị: dùng chính OTL Toolbox (exe hoặc otl_toolbox.py) — không cần Python cài sẵn."""
    if FROZEN:
        return [sys.executable, "--chart", json_path]
    here = Path(__file__).resolve().parent
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    interp = pythonw if pythonw.exists() else Path(sys.executable)
    return [str(interp), str(here / "otl_toolbox.py"), "--chart", json_path]


# (nhãn, khoá milestone, cách hiển thị)
COMPARE_ROWS = [
    ("BT lúc nạp",     "charge_bt", lambda v: f"{v:.1f} °C"),
    ("Kết thúc sấy",   "dry_s",     _mmss),
    ("Nổ lần 1",       "fcs_s",     _mmss),
    ("Thời điểm xả",   "drop_s",    _mmss),
    ("BT lúc xả",      "drop_bt",   lambda v: f"{v:.1f} °C"),
    ("ET lúc xả",      "drop_et",   lambda v: f"{v:.1f} °C"),
    ("Thời gian phát triển", "dev_s", _mmss),
    ("% phát triển",   "dev_pct",   lambda v: f"{v:.1f} %"),
]


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("Light")
        self.title("Chuyển profile")
        self.geometry("1280x860")
        self.minsize(1080, 700)
        self.configure(fg_color=BG)
        self._input_path = ""
        self._rows, self._milestones = [], {}
        self._build()

    # ═════ dựng giao diện ═════
    def _card(self, parent):
        return ctk.CTkFrame(parent, fg_color=CARD, corner_radius=14)

    def _title(self, parent, text):
        ctk.CTkLabel(parent, text=text, text_color=INK,
                     font=ctk.CTkFont(FONT, 15, "bold")).pack(anchor="w", padx=20, pady=(12, 8))

    def _build(self):
        if isinstance(self, tk.Tk):     # chạy riêng mới cần tiêu đề; trong Toolbox khung trượt đã có
            head = self._card(self)
            head.pack(fill="x", padx=16, pady=(16, 0))
            ctk.CTkLabel(head, text="Chuyển profile", text_color=INK,
                         font=ctk.CTkFont(FONT, 22, "bold")).pack(side="left", padx=20, pady=14)
            ctk.CTkLabel(head, text="File rang máy OTL (.txt) → CSV Artisan + .alog · soát mốc rang · xem đồ thị",
                         text_color=MUTED, font=ctk.CTkFont(FONT, 13)).pack(side="left")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=(10, 12))
        body.grid_columnconfigure(0, weight=2, uniform="c")
        body.grid_columnconfigure(1, weight=3, uniform="c")
        body.grid_rowconfigure(1, weight=1)

        src = self._card(body)
        src.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))
        self._build_source(src)
        self.cmp_card = self._card(body)
        self.cmp_card.grid(row=0, column=1, sticky="nsew", pady=(0, 10))
        self._show_compare_empty()
        self.ov_card = self._card(body)
        self.ov_card.grid(row=1, column=0, columnspan=2, sticky="nsew")
        self._build_overview()

    def _build_source(self, card):
        self._title(card, "Tệp nguồn")
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=20)
        self._button(row, "Chọn file", self._browse_file).pack(side="left", padx=(0, 8))
        self._button(row, "Quét cả thư mục", self._browse_folder).pack(side="left")

        self.file_var = tk.StringVar(value="Chưa chọn file (.txt / .csv / .alog)")
        chip = ctk.CTkFrame(card, fg_color=FIELD, corner_radius=8)
        chip.pack(fill="x", padx=20, pady=(10, 0))
        self.file_lbl = ctk.CTkLabel(chip, textvariable=self.file_var, text_color=MUTED, anchor="w",
                                     font=ctk.CTkFont(MONO, 12))
        self.file_lbl.pack(side="left", fill="x", expand=True, padx=12, pady=8)
        ctk.CTkButton(chip, text="Bỏ chọn", width=72, height=32, fg_color="transparent",
                      hover_color=LINE, text_color=MUTED, font=ctk.CTkFont(FONT, 12),
                      command=self._clear_file).pack(side="right", padx=6)

        self._build_datetime(card)
        self._build_options(card)

        act = ctk.CTkFrame(card, fg_color="transparent")
        act.pack(fill="x", padx=20, pady=(10, 0))
        self.convert_btn = ctk.CTkButton(act, text="Chuyển đổi", height=44, width=150,
                                         corner_radius=10, fg_color=BRAND, hover_color=BRAND_HOVER,
                                         font=ctk.CTkFont(FONT, 14, "bold"), state="disabled",
                                         command=self._on_convert)
        self.convert_btn.pack(side="left", padx=(0, 8))
        self.chart_btn = self._button(act, "Xem đồ thị", self._open_chart)
        self.chart_btn.configure(state="disabled")
        self.chart_btn.pack(side="left")

        self.progress = ctk.CTkProgressBar(card, height=6, progress_color=BRAND, fg_color=LINE)
        self.progress.set(0)
        self.progress.pack(fill="x", padx=20, pady=(10, 4))
        self.status_var = tk.StringVar(value="Chọn file .txt để bắt đầu…")
        self.status_lbl = ctk.CTkLabel(card, textvariable=self.status_var, text_color=MUTED,
                                       anchor="w", justify="left", wraplength=440,
                                       font=ctk.CTkFont(FONT, 12))
        self.status_lbl.pack(fill="x", padx=20, pady=(0, 12))

    def _button(self, parent, text, command):
        return ctk.CTkButton(parent, text=text, height=44, corner_radius=10, fg_color=FIELD,
                             hover_color=LINE, text_color=INK, font=ctk.CTkFont(FONT, 13),
                             command=command)

    def _build_datetime(self, card):
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(10, 0))
        ctk.CTkLabel(row, text="Ngày giờ rang", text_color=MUTED,
                     font=ctk.CTkFont(FONT, 12)).pack(side="left", padx=(0, 10))
        now = datetime.now()
        self.dt_vars = []
        for value, width, sep in ((f"{now.day:02d}", 44, "/"), (f"{now.month:02d}", 44, "/"),
                                  (f"{now.year}", 64, "   "), (f"{now.hour:02d}", 44, ":"),
                                  (f"{now.minute:02d}", 44, "")):
            var = tk.StringVar(value=value)
            ctk.CTkEntry(row, textvariable=var, width=width, height=36, justify="center",
                         fg_color=FIELD, border_width=0, font=ctk.CTkFont(FONT, 13)).pack(side="left")
            if sep:
                ctk.CTkLabel(row, text=sep, text_color=MUTED).pack(side="left", padx=2)
            self.dt_vars.append(var)

    def _build_options(self, card):
        box = ctk.CTkFrame(card, fg_color="transparent")
        box.pack(fill="x", padx=20, pady=(10, 0))
        self.fill_var = tk.BooleanVar(value=True)
        self.alog_var = tk.BooleanVar(value=True)
        self.gas_on = tk.BooleanVar(value=False)
        self.gas_val = tk.StringVar(value="100")
        font = ctk.CTkFont(FONT, 13)
        ctk.CTkCheckBox(box, text="Tự bù dòng thiếu (nội suy nhiệt, giữ gió/gas/trống)",
                        variable=self.fill_var, font=font, text_color=INK,
                        fg_color=BRAND, hover_color=BRAND_HOVER).pack(anchor="w", pady=2)
        ctk.CTkCheckBox(box, text="Xuất thêm profile Artisan (.alog)", variable=self.alog_var,
                        font=font, text_color=INK, fg_color=BRAND,
                        hover_color=BRAND_HOVER).pack(anchor="w", pady=2)
        gas = ctk.CTkFrame(box, fg_color="transparent")
        gas.pack(anchor="w", pady=2)
        ctk.CTkCheckBox(gas, text="CSV kèm công suất gas (MaxGas)", variable=self.gas_on,
                        font=font, text_color=INK, fg_color=BRAND, hover_color=BRAND_HOVER,
                        command=self._toggle_gas).pack(side="left")
        self.gas_entry = ctk.CTkEntry(gas, textvariable=self.gas_val, width=56, height=32,
                                      justify="center", fg_color=FIELD, border_width=0,
                                      state="disabled", font=font)
        self.gas_entry.pack(side="left", padx=(8, 4))
        ctk.CTkLabel(gas, text="%", text_color=MUTED, font=font).pack(side="left")

    # ═════ bảng so sánh mốc ═════
    def _clear_children(self, widget):
        for child in widget.winfo_children():
            child.destroy()

    def _show_compare_empty(self):
        self._clear_children(self.cmp_card)
        self._title(self.cmp_card, "Mốc rang")
        ctk.CTkLabel(self.cmp_card, text="Chọn một file để xem mốc rang và kiểm tra dữ liệu.",
                     text_color=MUTED, font=ctk.CTkFont(FONT, 13)).pack(anchor="w", padx=20)

    def _show_compare(self, src_path: str, csv_path, issues: list):
        old = _ms_any(src_path)
        if not old:
            self._show_compare_empty()
            return
        new = extract_milestones_csv(csv_path) if csv_path else {}
        card = self.cmp_card
        self._clear_children(card)
        self._title(card, "Mốc rang — file gốc và sau chuyển đổi")
        table = ctk.CTkFrame(card, fg_color="transparent")
        table.pack(fill="x", padx=20)
        for c, (text, w) in enumerate((("Tiêu chí", 3), ("File gốc", 2), ("Sau chuyển", 2))):
            table.grid_columnconfigure(c, weight=w, uniform="t")
            ctk.CTkLabel(table, text=text, text_color=MUTED, anchor="w",
                         font=ctk.CTkFont(FONT, 12, "bold")).grid(row=0, column=c, sticky="ew", pady=(0, 4))
        matched = diff = 0
        for r, (label, key, fmt) in enumerate(COMPARE_ROWS, start=1):
            v_old = fmt(old.get(key, 0))
            v_new = fmt(new[key]) if new else "—"
            if new:
                same = v_old == v_new
                matched, diff = matched + same, diff + (not same)
                v_new = f"{v_new}  {'✓' if same else '≠'}"
                color = OK if same else BAD
            else:
                color = MUTED
            bg = FIELD if r % 2 else CARD
            for c, (text, fg, bold) in enumerate(((label, INK, False), (v_old, INK, False),
                                                  (v_new, color, True))):
                ctk.CTkLabel(table, text=text, text_color=fg, fg_color=bg, anchor="w", height=30,
                             font=ctk.CTkFont(FONT, 13, "bold" if bold else "normal")
                             ).grid(row=r, column=c, sticky="ew")
        summary = (f"Khớp {matched}/{matched + diff} mốc" + (f" · lệch {diff}" if diff else "")
                   if new else "Chưa chuyển đổi — cột 'Sau chuyển' sẽ điền sau khi lưu CSV.")
        ctk.CTkLabel(card, text=summary, text_color=OK if new and not diff else MUTED, anchor="w",
                     font=ctk.CTkFont(FONT, 13, "bold")).pack(fill="x", padx=20, pady=(10, 0))
        self._show_issues(card, issues)

    def _show_issues(self, card, issues: list):
        if not issues:
            text, color = "✓ Dữ liệu toàn vẹn — không thiếu dòng, không nhảy giá trị.", OK
        else:
            more = f"\n… và {len(issues) - 8} lỗi khác" if len(issues) > 8 else ""
            text = f"⚠ {len(issues)} điểm cần xem:\n" + "\n".join(f"• {i}" for i in issues[:8]) + more
            color = BAD
        ctk.CTkLabel(card, text=text, text_color=color, anchor="w", justify="left", wraplength=640,
                     font=ctk.CTkFont(FONT, 12)).pack(fill="x", padx=20, pady=(8, 16))

    # ═════ tổng quan thư mục ═════
    def _build_overview(self):
        card = self.ov_card
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(16, 8))
        self.ov_title = ctk.CTkLabel(top, text="Tổng quan thư mục", text_color=INK,
                                     font=ctk.CTkFont(FONT, 15, "bold"))
        self.ov_title.pack(side="left")
        self.batch_btn = ctk.CTkButton(top, text="Chuyển tất cả .txt → converted/", height=40,
                                       corner_radius=10, fg_color=BRAND, hover_color=BRAND_HOVER,
                                       font=ctk.CTkFont(FONT, 13, "bold"), state="disabled",
                                       command=self._batch_convert)
        self.batch_btn.pack(side="right")
        self.batch_var = tk.StringVar(value="Bấm 'Quét cả thư mục' để liệt kê mọi file rang · bấm đúp một dòng để xem đồ thị")
        ctk.CTkLabel(top, textvariable=self.batch_var, text_color=MUTED,
                     font=ctk.CTkFont(FONT, 12)).pack(side="right", padx=12)

        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("OTL.Treeview", rowheight=30, font=(FONT, 11), background=CARD,
                        fieldbackground=CARD, foreground=INK, borderwidth=0)
        style.configure("OTL.Treeview.Heading", font=(FONT, 11, "bold"), background=FIELD,
                        foreground=MUTED, relief="flat")
        style.map("OTL.Treeview", background=[("selected", "#FDECEC")],
                  foreground=[("selected", INK)])
        cols = ("file", "type", "charge", "dry", "fcs", "drop", "dev", "dropbt", "dropet")
        heads = ("File", "Loại", "BT nạp", "Hết sấy", "Nổ 1", "Xả", "% PT", "BT xả", "ET xả")
        frame = tk.Frame(card, bg=CARD)
        frame.pack(fill="both", expand=True, padx=20, pady=(0, 12))
        # height=3 là chiều cao TỐI THIỂU — bảng giãn theo chỗ trống, không đẩy màn phải cuộn
        self.tree = ttk.Treeview(frame, columns=cols, show="headings", style="OTL.Treeview", height=3)
        for c, h in zip(cols, heads):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=240 if c == "file" else 90, anchor="w" if c == "file" else "center")
        vsb = ctk.CTkScrollbar(frame, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", self._on_tree_open)
        self._ov_paths, self._ov_folder, self._ov_files = {}, "", []

    def _fill_overview(self, folder: str, files: list):
        self._ov_folder, self._ov_files = folder, files
        self.tree.delete(*self.tree.get_children())
        self._ov_paths.clear()
        for p in files:
            ext = p.suffix.lower()
            m = _ms_any(str(p))
            if ext == ".csv" and m and m.get("drop_s", 0) == 0 and m.get("charge_bt", 0) == 0:
                m = {}  # CSV không hợp lệ → coi như không đọc được
            kind = {".csv": "CSV", ".alog": "ALOG"}.get(ext, "TXT")
            vals = (p.name, kind, f"{m['charge_bt']:.1f}°", _mmss(m["dry_s"]), _mmss(m["fcs_s"]),
                    _mmss(m["drop_s"]), f"{m['dev_pct']:.1f}%", f"{m['drop_bt']:.1f}°",
                    f"{m['drop_et']:.1f}°") if m else (p.name, kind) + ("—",) * 7
            self._ov_paths[self.tree.insert("", "end", values=vals)] = p
        n_txt = sum(1 for p in files if p.suffix.lower() == ".txt")
        self.ov_title.configure(text=f"Tổng quan thư mục — {Path(folder).name} ({len(files)} file)")
        self.batch_btn.configure(text=f"Chuyển {n_txt} file .txt → converted/",
                                 state="normal" if n_txt else "disabled")
        self.batch_var.set("Bấm đúp một dòng để xem đồ thị")

    def _on_tree_open(self, _event):
        sel = self.tree.selection()
        p = self._ov_paths.get(sel[0]) if sel else None
        if p:
            rows, _ = _parse_any(str(p))
            if rows:
                self._launch_chart(rows, _ms_any(str(p)), p.stem)

    # ═════ thao tác ═════
    def toolbox_status(self):
        """Dòng trạng thái trên tab OTL Toolbox: (None = không có cổng COM, chữ)."""
        return None, Path(self._input_path).name if self._input_path else "chưa chọn file"

    def _set_status(self, text: str, color: str = MUTED):
        self.status_var.set(text)
        self.status_lbl.configure(text_color=color)

    def _toggle_gas(self):
        self.gas_entry.configure(state="normal" if self.gas_on.get() else "disabled")

    def _max_gas(self):
        if not self.gas_on.get():
            return None
        try:
            return max(0, min(100, int(self.gas_val.get())))
        except ValueError:
            return 100

    def _roast_dt(self) -> str:
        dd, mm, yy, hh, mn = (v.get().strip() for v in self.dt_vars)
        return f"{dd.zfill(2)}.{mm.zfill(2)}.{yy} {hh.zfill(2)}:{mn.zfill(2)}:00"

    def _browse_file(self):
        path = filedialog.askopenfilename(
            title="Chọn file rang",
            filetypes=[("File rang", "*.txt *.alog *.csv"), ("Tất cả", "*.*")])
        if path:
            self._load_path(path)

    def _load_path(self, path: str):
        self._input_path = path
        self.file_var.set(Path(path).name)
        self.file_lbl.configure(text_color=INK)
        self._rows, self._milestones = _parse_any(path)[0], _ms_any(path)
        issues = validate_rows_integrity(self._rows)
        if issues:
            self._set_status(f"Đã đọc {len(self._rows)} dòng — có {len(issues)} điểm cần xem.", BAD)
        else:
            self._set_status(f"Đã đọc {len(self._rows)} dòng — dữ liệu ổn, sẵn sàng chuyển đổi.", OK)
        self.convert_btn.configure(state="normal")
        self.chart_btn.configure(state="normal" if self._rows else "disabled")
        self._show_compare(path, None, issues)

    def _clear_file(self):
        self._input_path = ""
        self._rows, self._milestones = [], {}
        self.file_var.set("Chưa chọn file (.txt / .csv / .alog)")
        self.file_lbl.configure(text_color=MUTED)
        self.convert_btn.configure(state="disabled")
        self.chart_btn.configure(state="disabled")
        self._set_status("Chọn file .txt để bắt đầu…")
        self._show_compare_empty()

    def _browse_folder(self):
        folder = filedialog.askdirectory(title="Chọn thư mục file rang")
        if not folder:
            return
        files = sorted((p for p in Path(folder).iterdir()
                        if p.is_file() and p.suffix.lower() in SOURCE_EXT),
                       key=lambda p: _natkey(p.name))
        self._fill_overview(folder, files)

    def _on_convert(self):
        if not self._input_path:
            return
        self.convert_btn.configure(state="disabled")
        self.progress.set(0)
        self._set_status("Đang chuyển đổi…", BRAND)
        tmp = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
        tmp.close()
        args = (self._input_path, tmp.name, self._roast_dt(), self.fill_var.get(), self._max_gas())
        threading.Thread(target=self._run_convert, args=args, daemon=True).start()

    def _run_convert(self, inp, tmp, roast_dt, fill, max_gas):
        try:
            n = convert(inp, tmp, progress_cb=lambda p: self.after(0, self.progress.set, p / 100),
                        roast_dt=roast_dt, fill_missing=fill, max_gas=max_gas)
            self.after(0, lambda: self._on_done(n, tmp, roast_dt))
        except Exception as exc:
            self.after(0, lambda e=str(exc): self._on_error(e, tmp))

    def _on_done(self, n: int, tmp: str, roast_dt: str):
        self.progress.set(1)
        save_path = filedialog.asksaveasfilename(
            title="Lưu file CSV", initialfile=Path(self._input_path).stem + ".csv",
            defaultextension=".csv", filetypes=[("CSV Artisan", "*.csv"), ("Tất cả", "*.*")])
        self.progress.set(0)
        if save_path:
            shutil.copy(tmp, save_path)
            issues = self._write_extras(save_path, roast_dt)
            self._set_status(f"Xong {n} dòng → {Path(save_path).name}", OK)
            self._milestones = _ms_any(self._input_path)
            self._show_compare(self._input_path, save_path, issues)
        else:
            self._set_status("Đã huỷ lưu.")
        Path(tmp).unlink(missing_ok=True)
        self.convert_btn.configure(state="normal")

    def _write_extras(self, save_path: str, roast_dt: str) -> list:
        """Ghi .alog (nếu bật) và file .txt đã bù dòng vào TXT_converted/; trả danh sách cảnh báo."""
        rows, milestones = _parse_any(self._input_path)
        filled = []
        if Path(self._input_path).suffix.lower() == ".txt":
            if self.fill_var.get():
                rows, filled = fill_gaps(rows)
            if self.alog_var.get():
                write_alog(rows, milestones, str(Path(save_path).with_suffix(".alog")), roast_dt=roast_dt)
        self._rows = rows
        issues = validate_rows_integrity(rows)
        if filled:
            fixed = Path(self._input_path).parent / "TXT_converted" / Path(self._input_path).name
            write_fixed_txt(rows, milestones, str(fixed))
            issues = [f"Đã bù {len(filled)} dòng thiếu → TXT_converted/{fixed.name}"] + issues
        return issues

    def _on_error(self, msg: str, tmp: str):
        self.progress.set(0)
        Path(tmp).unlink(missing_ok=True)
        self._set_status(f"Lỗi: {msg}", BAD)
        self.convert_btn.configure(state="normal")

    def _batch_convert(self):
        txts = [p for p in self._ov_files if p.suffix.lower() == ".txt"]
        if not txts:
            return
        self.batch_btn.configure(state="disabled")
        opts = (self.fill_var.get(), self._max_gas(), self.alog_var.get())
        threading.Thread(target=self._batch_work, args=(txts,) + opts, daemon=True).start()

    def _batch_work(self, txts, fill, max_gas, export_alog):
        out_dir = Path(self._ov_folder) / "converted"
        txt_dir = Path(self._ov_folder) / "TXT_converted"
        ok, n_fixed, errs = 0, 0, []
        for i, p in enumerate(txts):
            self.after(0, self.batch_var.set, f"Đang chuyển {i + 1}/{len(txts)}…")
            try:
                rows, ms = parse_txt(str(p))
                filled = []
                if fill:
                    rows, filled = fill_gaps(rows)
                roast_dt = datetime.fromtimestamp(p.stat().st_mtime).strftime("%d.%m.%Y %H:%M:00")
                write_csv(rows, ms, str(out_dir / f"{p.stem}.csv"), roast_dt=roast_dt, max_gas=max_gas)
                if export_alog:
                    write_alog(rows, ms, str(out_dir / f"{p.stem}.alog"), roast_dt=roast_dt)
                if filled:
                    write_fixed_txt(rows, ms, str(txt_dir / p.name))
                    n_fixed += 1
                ok += 1
            except Exception as exc:
                errs.append(f"{p.name}: {exc}")
        msg = f"Xong {ok}/{len(txts)} file → {out_dir}"
        if fill:
            msg += f"\nĐã bù dòng {n_fixed} file → {txt_dir}"
        if errs:
            msg += f"\n\nLỗi ({len(errs)}):\n" + "\n".join(errs[:10])
        self.after(0, lambda: self._batch_done(ok, len(txts), msg))

    def _batch_done(self, ok: int, total: int, msg: str):
        self.batch_var.set(f"✓ {ok}/{total} → converted/")
        self.batch_btn.configure(state="normal")
        messagebox.showinfo("Chuyển hàng loạt", msg)

    def _open_chart(self):
        if self._rows:
            self._launch_chart(self._rows, self._milestones, Path(self._input_path).stem)

    def _launch_chart(self, rows, milestones, name):
        tmp_json = Path(tempfile.gettempdir()) / f"otl_chart_{uuid.uuid4().hex[:8]}.json"
        tmp_json.write_text(json.dumps({"rows": rows, "milestones": milestones, "name": name}),
                            encoding="utf-8")
        try:
            subprocess.Popen(chart_command(str(tmp_json)))
        except OSError as exc:
            self._set_status(f"Không mở được đồ thị: {exc}", BAD)


if __name__ == "__main__":
    App().mainloop()
