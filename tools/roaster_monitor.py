"""
Roaster Monitor — Watch CSV từ Artisan, hiển thị BT/ET/RoR real-time
Artisan lưu CSV vào data/roast_logs\ — tool này đọc file mới nhất và cập nhật mỗi giây
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import csv
import os
import glob
import threading
import time
from collections import deque

WATCH_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'roast_logs')

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

class RoasterMonitor:

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title('Roaster Monitor')
        self.root.resizable(False, False)

        self.running       = False
        self.current_file  = ''
        self.last_row_count = 0
        self.ror_bt        = RoRCalc(30)
        self.ror_et        = RoRCalc(30)
        self.prev_ror_bt: float | None = None
        self.monitor_start = time.time()

        self._build_ui()
        self._log(f'Watching: {WATCH_DIR}')
        self._log('Lưu CSV từ Artisan vào folder đó, tool tự đọc.')

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        PAD = dict(padx=8, pady=4)

        # Folder info
        top = ttk.LabelFrame(self.root, text='Watch Folder')
        top.grid(row=0, column=0, columnspan=2, sticky='ew', **PAD)
        ttk.Label(top, text=WATCH_DIR, font=('Consolas', 9)).grid(row=0, column=0, sticky='w', **PAD)

        # Control
        ctrl = ttk.Frame(self.root)
        ctrl.grid(row=1, column=0, columnspan=2, sticky='ew', **PAD)
        self.btn = ttk.Button(ctrl, text='Start Monitor', command=self._toggle)
        self.btn.pack(side='left', **PAD)
        ttk.Button(ctrl, text='Reset RoR', command=self._reset_ror).pack(side='left', **PAD)
        self.file_var = tk.StringVar(value='No file')
        ttk.Label(ctrl, textvariable=self.file_var, font=('Consolas', 8),
                  foreground='gray').pack(side='left', **PAD)

        # Data LCDs
        data = ttk.LabelFrame(self.root, text='Live Data')
        data.grid(row=2, column=0, sticky='nsew', **PAD)

        self.vars: dict[str, tk.StringVar] = {}
        self.lcds: dict[str, tk.Label]     = {}

        rows_cfg = [
            ('BT',       '°C',      '#00cc44'),
            ('ET',       '°C',      '#00aa33'),
            ('ET-BT',    '°C',      '#ffcc00'),
            ('RoR BT',   '°C/min',  '#ff9900'),
            ('RoR ET',   '°C/min',  '#ffbb44'),
            ('dRoR/dt',  '°C/min²', '#cc66ff'),
            ('Gas',      '%',       '#3399ff'),
            ('Air',      '%',       '#55bbff'),
            ('Drum',     '%',       '#aaaaff'),
            ('Roast t',  'mm:ss',   '#ffffff'),
        ]
        for r, (name, unit, color) in enumerate(rows_cfg):
            ttk.Label(data, text=name, font=('Arial', 10, 'bold')).grid(
                row=r, column=0, sticky='w', **PAD)
            var = tk.StringVar(value='---')
            lbl = tk.Label(data, textvariable=var, font=('Consolas', 22, 'bold'),
                           fg=color, bg='#1a1a1a', width=9, anchor='e')
            lbl.grid(row=r, column=1, **PAD)
            if unit:
                ttk.Label(data, text=unit, font=('Arial', 9)).grid(
                    row=r, column=2, sticky='w')
            self.vars[name] = var
            self.lcds[name] = lbl

        # Log
        log = ttk.LabelFrame(self.root, text='Log')
        log.grid(row=2, column=1, sticky='nsew', **PAD)
        self.log_text = scrolledtext.ScrolledText(
            log, width=52, height=20,
            font=('Consolas', 9), bg='#1a1a1a', fg='#cccccc')
        self.log_text.pack(fill='both', expand=True, padx=4, pady=4)

        # Status
        self.status_var = tk.StringVar(value='Stopped')
        ttk.Label(self.root, textvariable=self.status_var,
                  relief='sunken', anchor='w').grid(
            row=3, column=0, columnspan=2, sticky='ew', padx=8, pady=2)

    # ── Control ───────────────────────────────────────────────────────────────

    def _toggle(self):
        if self.running:
            self.running = False
            self.btn.config(text='Start Monitor')
            self.status_var.set('Stopped')
        else:
            self.running        = True
            self.current_file   = ''
            self.last_row_count = 0
            self.monitor_start  = time.time()
            self.btn.config(text='Stop')
            self.status_var.set('Monitoring...')
            t = threading.Thread(target=self._watch_loop, daemon=True)
            t.start()

    def _reset_ror(self):
        self.ror_bt.reset()
        self.ror_et.reset()
        self.prev_ror_bt = None
        self._log('RoR reset')

    # ── Watch loop ────────────────────────────────────────────────────────────

    def _watch_loop(self):
        while self.running:
            try:
                latest = get_latest_csv(WATCH_DIR)
                if latest is None:
                    self.root.after(0, self.status_var.set,
                                    'No CSV found — lưu file từ Artisan vào folder')
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
                    self.root.after(0, self.file_var.set, fname)
                    self.root.after(0, self._log, f'New file: {fname}')

                rows = parse_artisan_csv(self.current_file)
                if len(rows) > self.last_row_count and rows:
                    self.last_row_count = len(rows)
                    last = rows[-1]
                    self.root.after(0, self._update_ui, last, rows)

            except Exception as e:
                self.root.after(0, self.status_var.set, f'Error: {e}')

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

        # color RoR BT
        if ror_bt is not None:
            if ror_bt > 15:
                self.lcds['RoR BT'].config(fg='#ff4444')
            elif ror_bt < 0:
                self.lcds['RoR BT'].config(fg='#3399ff')
            else:
                self.lcds['RoR BT'].config(fg='#ff9900')

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
    root = tk.Tk()
    RoasterMonitor(root)
    root.mainloop()
