"""
Roaster Monitor — Watch CSV từ Artisan, hiển thị BT/ET/RoR real-time
Artisan lưu CSV vào data/roast_logs\ — tool này đọc file mới nhất và cập nhật mỗi giây
"""

import tkinter as tk
from tkinter import filedialog
import csv
import os
import glob
import sys
import threading
import time
from collections import deque

import customtkinter as ctk


def _repo_root() -> str:
    # Bản exe OTL Toolbox nằm ở tools/dist/OTLToolbox/ → gốc repo lùi 3 cấp
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(sys.executable))))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


WATCH_DIR = os.path.join(_repo_root(), 'data', 'roast_logs')

# ── RoR calculator ────────────────────────────────────────────────────────────

class RoRCalc:
    def __init__(self, window: int = 30):
        self.window = window
        self.buf: deque[tuple[float, float]] = deque()

    def reset(self):
        self.buf.clear()

    def add(self, ts: float, val: float) -> float | None:
        self.buf.append((ts, val))
        while self.buf and ts - self.buf[0][0] > self.window + 5:
            self.buf.popleft()
        older = [(t, v) for t, v in self.buf if t <= ts - self.window]
        if not older:
            return None
        t0, v0 = older[-1]
        dt = ts - t0
        if dt < 5:
            return None
        return round((val - v0) / dt * 60, 1)


# ── CSV reader ────────────────────────────────────────────────────────────────

def parse_artisan_csv(filepath: str) -> list[dict]:
    """
    Đọc CSV Artisan format:
    Row 1: metadata (Date, CHARGE, TP, FCs...)
    Row 2: header (Time1, Time2, ET, BT, Event, Air(%), Burner(%), Drum(%),...)
    Row 3+: data
    """
    rows = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.reader(f, delimiter='\t')
            lines = list(reader)

        if len(lines) < 3:
            return rows

        # Row 2 là header
        header = [h.strip() for h in lines[1]]

        # Tìm index các cột cần
        def idx(name):
            for i, h in enumerate(header):
                if name.lower() in h.lower():
                    return i
            return -1

        i_time1  = idx('Time1')
        i_time2  = idx('Time2')
        i_et     = idx('ET')
        i_bt     = idx('BT')
        i_air    = idx('Air')
        i_burner = idx('Burner')
        i_drum   = idx('Drum')

        for line in lines[2:]:
            if not line or not line[0].strip():
                continue
            try:
                def get(i):
                    if i < 0 or i >= len(line):
                        return ''
                    return line[i].strip()

                time1 = get(i_time1)
                time2 = get(i_time2)
                et_s  = get(i_et)
                bt_s  = get(i_bt)
                air_s = get(i_air)
                gas_s = get(i_burner)
                drm_s = get(i_drum)

                if not et_s or not bt_s:
                    continue

                et  = float(et_s)
                bt  = float(bt_s)
                air = float(air_s) if air_s else 0.0
                gas = float(gas_s) if gas_s else 0.0
                drm = float(drm_s) if drm_s else 0.0

                # parse roast time từ Time2 (mm:ss), fallback Time1
                t_str = time2 if time2 else time1
                roast_sec = _time_to_sec(t_str)

                rows.append({
                    'time1':     time1,
                    'time2':     time2,
                    'roast_sec': roast_sec,
                    'ET':  et,
                    'BT':  bt,
                    'Air': air,
                    'Gas': gas,
                    'Drum': drm,
                })
            except (ValueError, IndexError):
                continue

    except Exception:
        pass

    return rows


def _time_to_sec(t: str) -> float:
    """mm:ss hoặc hh:mm:ss → seconds"""
    try:
        parts = t.strip().split(':')
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except Exception:
        pass
    return 0.0


def get_latest_csv(folder: str) -> str | None:
    """Tìm file CSV mới nhất trong folder"""
    files = glob.glob(os.path.join(folder, '*.csv'))
    if not files:
        return None
    return max(files, key=os.path.getmtime)


# ── Main App ──────────────────────────────────────────────────────────────────

FONT = 'Segoe UI'
MONO = 'Consolas'
INK = '#1E293B'
MUTED = '#64748B'
CARD = '#FFFFFF'
BG = '#EEF2F7'
FIELD = '#F1F5F9'
BRAND = '#C62828'
ROR_HIGH = '#DC2626'      # RoR BT > 15 °C/min
ROR_NEG = '#2563EB'       # RoR BT < 0
ROR_HIGH_LIMIT = 15

# (tên, đơn vị, màu số)
METRICS = [
    ('BT',      '°C',      '#15803D'),
    ('ET',      '°C',      '#B91C1C'),
    ('ET-BT',   '°C',      '#B45309'),
    ('RoR BT',  '°C/min',  '#C2410C'),
    ('RoR ET',  '°C/min',  '#A16207'),
    ('dRoR/dt', '°C/min²', '#7E22CE'),
    ('Gas',     '%',       '#1D4ED8'),
    ('Air',     '%',       '#0369A1'),
    ('Drum',    '%',       '#4338CA'),
    ('Roast t', 'mm:ss',   INK),
]


class App(ctk.CTk):

    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode('Light')
        self.title('Roaster Monitor')
        self.geometry('1180x760')
        self.minsize(980, 640)
        self.configure(fg_color=BG)

        self.watch_dir      = WATCH_DIR
        self.running        = False
        self.current_file   = ''
        self.last_row_count = 0
        self.ror_bt         = RoRCalc(30)
        self.ror_et         = RoRCalc(30)
        self.prev_ror_bt: float | None = None
        self.monitor_start  = time.time()

        self._build_ui()
        self.protocol('WM_DELETE_WINDOW', self._on_close)
        self._log(f'Watching: {self.watch_dir}')
        self._log('Lưu CSV từ Artisan vào thư mục đó, công cụ tự đọc file mới nhất.')

    # ── UI ────────────────────────────────────────────────────────────────────

    def _card(self, parent, **kw):
        return ctk.CTkFrame(parent, fg_color=CARD, corner_radius=14, **kw)

    def _build_ui(self):
        head = self._card(self)
        head.pack(fill='x', padx=16, pady=(16, 10))
        ctk.CTkLabel(head, text='Roaster Monitor', text_color=INK,
                     font=ctk.CTkFont(FONT, 22, 'bold')).pack(side='left', padx=20, pady=14)
        ctk.CTkLabel(head, text='Theo dõi file CSV Artisan đang ghi — cập nhật mỗi giây',
                     text_color=MUTED, font=ctk.CTkFont(FONT, 13)).pack(side='left')

        bar = self._card(self)
        bar.pack(fill='x', padx=16, pady=(0, 10))
        left = ctk.CTkFrame(bar, fg_color='transparent')
        left.pack(side='left', fill='x', expand=True, padx=20, pady=12)
        ctk.CTkLabel(left, text='THƯ MỤC THEO DÕI', text_color=MUTED,
                     font=ctk.CTkFont(FONT, 11)).pack(anchor='w')
        self.dir_var = tk.StringVar(value=self.watch_dir)
        ctk.CTkLabel(left, textvariable=self.dir_var, text_color=INK, anchor='w',
                     font=ctk.CTkFont(MONO, 13)).pack(anchor='w', fill='x')
        self.file_var = tk.StringVar(value='Chưa có file')
        ctk.CTkLabel(left, textvariable=self.file_var, text_color=MUTED, anchor='w',
                     font=ctk.CTkFont(MONO, 12)).pack(anchor='w', fill='x')

        self.btn = ctk.CTkButton(bar, text='Bắt đầu theo dõi', width=168, height=44,
                                 corner_radius=10, fg_color=BRAND, hover_color='#A31F1F',
                                 font=ctk.CTkFont(FONT, 14, 'bold'), command=self._toggle)
        self.btn.pack(side='right', padx=(8, 20))
        for text, cmd in (('Reset RoR', self._reset_ror), ('Đổi thư mục', self._pick_dir)):
            ctk.CTkButton(bar, text=text, width=120, height=44, corner_radius=10,
                          fg_color=FIELD, hover_color='#E2E8F0', text_color=INK,
                          font=ctk.CTkFont(FONT, 13), command=cmd).pack(side='right', padx=4)

        body = ctk.CTkFrame(self, fg_color='transparent')
        body.pack(fill='both', expand=True, padx=16, pady=(0, 10))
        body.grid_columnconfigure(0, weight=3, uniform='col')
        body.grid_columnconfigure(1, weight=2, uniform='col')
        body.grid_rowconfigure(0, weight=1)

        data = self._card(body)
        data.grid(row=0, column=0, sticky='nsew', padx=(0, 10))
        ctk.CTkLabel(data, text='Số liệu trực tiếp', text_color=INK,
                     font=ctk.CTkFont(FONT, 15, 'bold')).pack(anchor='w', padx=20, pady=(16, 8))
        grid = ctk.CTkFrame(data, fg_color='transparent')
        grid.pack(fill='both', expand=True, padx=14, pady=(0, 14))
        for c in range(2):
            grid.grid_columnconfigure(c, weight=1, uniform='m')

        self.vars: dict[str, tk.StringVar] = {}
        self.lcds: dict[str, ctk.CTkLabel] = {}
        self.base_color: dict[str, str] = {}
        for i, (name, unit, color) in enumerate(METRICS):
            tile = ctk.CTkFrame(grid, fg_color=FIELD, corner_radius=10)
            tile.grid(row=i // 2, column=i % 2, sticky='nsew', padx=6, pady=6)
            grid.grid_rowconfigure(i // 2, weight=1)
            ctk.CTkLabel(tile, text=f'{name}  ({unit})', text_color=MUTED,
                         font=ctk.CTkFont(FONT, 12)).pack(anchor='w', padx=14, pady=(8, 0))
            var = tk.StringVar(value='---')
            lbl = ctk.CTkLabel(tile, textvariable=var, text_color=color, anchor='w',
                               font=ctk.CTkFont(MONO, 30, 'bold'))
            lbl.pack(anchor='w', padx=14, pady=(0, 8))
            self.vars[name] = var
            self.lcds[name] = lbl
            self.base_color[name] = color

        log = self._card(body)
        log.grid(row=0, column=1, sticky='nsew')
        ctk.CTkLabel(log, text='Nhật ký', text_color=INK,
                     font=ctk.CTkFont(FONT, 15, 'bold')).pack(anchor='w', padx=20, pady=(16, 8))
        self.log_text = ctk.CTkTextbox(log, fg_color=FIELD, text_color=INK, corner_radius=10,
                                       font=ctk.CTkFont(MONO, 12))
        self.log_text.pack(fill='both', expand=True, padx=14, pady=(0, 14))

        self.status_var = tk.StringVar(value='Đang dừng')
        ctk.CTkLabel(self, textvariable=self.status_var, text_color=MUTED, anchor='w',
                     font=ctk.CTkFont(FONT, 12)).pack(fill='x', padx=24, pady=(0, 10))

    # ── Control ───────────────────────────────────────────────────────────────

    def toolbox_status(self):
        """Trạng thái hiện trên tab OTL Toolbox: (đang chạy?, chữ)."""
        return (True, 'đang theo dõi') if self.running else (False, 'dừng')

    def _pick_dir(self):
        folder = filedialog.askdirectory(title='Chọn thư mục Artisan lưu CSV',
                                         initialdir=self.watch_dir)
        if not folder:
            return
        self.watch_dir = os.path.normpath(folder)
        self.dir_var.set(self.watch_dir)
        self.current_file = ''
        self._log(f'Watching: {self.watch_dir}')

    def _toggle(self):
        if self.running:
            self.running = False
            self.btn.configure(text='Bắt đầu theo dõi', fg_color=BRAND)
            self.status_var.set('Đang dừng')
        else:
            self.running        = True
            self.current_file   = ''
            self.last_row_count = 0
            self.monitor_start  = time.time()
            self.btn.configure(text='Dừng', fg_color='#475569')
            self.status_var.set('Đang theo dõi…')
            t = threading.Thread(target=self._watch_loop, daemon=True)
            t.start()

    def _reset_ror(self):
        self.ror_bt.reset()
        self.ror_et.reset()
        self.prev_ror_bt = None
        self._log('RoR reset')

    def _on_close(self):
        self.running = False
        self.destroy()

    # ── Watch loop ────────────────────────────────────────────────────────────

    def _watch_loop(self):
        while self.running:
            try:
                latest = get_latest_csv(self.watch_dir)
                if latest is None:
                    self.after(0, self.status_var.set,
                               'Chưa thấy file CSV — lưu file từ Artisan vào thư mục theo dõi')
                    time.sleep(2)
                    continue

                # file mới → reset
                if latest != self.current_file:
                    self.current_file   = latest
                    self.last_row_count = 0
                    self.ror_bt.reset()
                    self.ror_et.reset()
                    self.prev_ror_bt = None
                    fname = os.path.basename(latest)
                    self.after(0, self.file_var.set, fname)
                    self.after(0, self._log, f'New file: {fname}')

                rows = parse_artisan_csv(self.current_file)
                if len(rows) > self.last_row_count and rows:
                    self.last_row_count = len(rows)
                    last = rows[-1]
                    self.after(0, self._update_ui, last, rows)

            except Exception as e:
                self.after(0, self.status_var.set, f'Lỗi: {e}')

            time.sleep(1)

    # ── Update UI ─────────────────────────────────────────────────────────────

    def _update_ui(self, row: dict, all_rows: list[dict]):
        bt   = row['BT']
        et   = row['ET']
        gas  = row['Gas']
        air  = row['Air']
        drum = row['Drum']
        rsec = row['roast_sec']
        gap  = round(et - bt, 1)

        # dùng roast_sec làm timestamp cho RoR
        ror_bt = self.ror_bt.add(rsec, bt)
        ror_et = self.ror_et.add(rsec, et)

        dror: float | None = None
        if ror_bt is not None and self.prev_ror_bt is not None:
            dror = round(ror_bt - self.prev_ror_bt, 1)
        if ror_bt is not None:
            self.prev_ror_bt = ror_bt

        # roast time display
        m = int(rsec) // 60
        s = int(rsec) % 60
        t_str = f'{m:02d}:{s:02d}' if rsec > 0 else row['time1']

        self.vars['BT'].set(f'{bt:.1f}')
        self.vars['ET'].set(f'{et:.1f}')
        self.vars['ET-BT'].set(f'{gap:+.1f}')
        self.vars['RoR BT'].set(f'{ror_bt:.1f}' if ror_bt is not None else '---')
        self.vars['RoR ET'].set(f'{ror_et:.1f}' if ror_et is not None else '---')
        self.vars['dRoR/dt'].set(f'{dror:+.1f}' if dror is not None else '---')
        self.vars['Gas'].set(f'{gas:.0f}')
        self.vars['Air'].set(f'{air:.0f}')
        self.vars['Drum'].set(f'{drum:.0f}')
        self.vars['Roast t'].set(t_str)

        # màu RoR BT: cao / âm / bình thường
        if ror_bt is not None:
            if ror_bt > ROR_HIGH_LIMIT:
                color = ROR_HIGH
            elif ror_bt < 0:
                color = ROR_NEG
            else:
                color = self.base_color['RoR BT']
            self.lcds['RoR BT'].configure(text_color=color)

        self.status_var.set(
            f'Live  BT:{bt:.1f}°C  ET:{et:.1f}°C  '
            f'RoR:{ror_bt:.1f}°C/min  {len(all_rows)} rows'
            if ror_bt is not None else
            f'Live  BT:{bt:.1f}°C  ET:{et:.1f}°C  {len(all_rows)} rows'
        )

        # log mỗi 30 giây roast time
        if rsec > 0 and int(rsec) % 30 == 0:
            ror_str = f'{ror_bt:.1f}' if ror_bt is not None else '---'
            self._log(f'{t_str} BT:{bt:.1f} ET:{et:.1f} Gap:{gap:+.1f} RoR:{ror_str} Gas:{gas:.0f}% Air:{air:.0f}%')

    def _log(self, msg: str):
        ts = time.strftime('%H:%M:%S')
        self.log_text.insert('end', f'[{ts}] {msg}\n')
        self.log_text.see('end')


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    App().mainloop()
