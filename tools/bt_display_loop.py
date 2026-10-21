# -*- coding: utf-8 -*-
"""
Tiện ích hiển thị cho BT Serial Tester — phần LOGIC THUẦN, không Tk, không serial.

Tách riêng để:
  • kiểm thử được không cần mở cửa sổ hay cổng COM (`tools/test_bt_display.py`);
  • đo thời gian callback/vẽ bằng số thật thay vì suy ra từ chu kỳ hẹn giờ.

Ba khối:
  • SmoothCursor  — nội suy vị trí con trỏ theo `time.monotonic`, để con trỏ chạy
    mượt ở nhịp vẽ cao MÀ KHÔNG tăng tần suất gửi lệnh ra thiết bị.
  • PerfStats     — đếm nhịp callback và thời gian vẽ (trung bình, p95, lớn nhất).
  • bounded_drain — lấy có giới hạn từ queue để RX dồn không treo giao diện.
"""

import time
from collections import deque

# Nhịp vẽ MỤC TIÊU 60 Hz ≈ 16,7 ms. Tk `after` chỉ nhận số nguyên ms nên chọn 16
# (nhắm hơi cao hơn mục tiêu); nhịp THỰC luôn phụ thuộc Tk và phải ĐO, xem
# PerfStats — gọi `after(16, …)` không phải bằng chứng đạt 60 Hz.
TARGET_FPS = 60.0
FRAME_MS = 16

# Chặn hai đầu khoảng thời gian nội suy: quá ngắn thì nhảy giật, quá dài thì con
# trỏ bò sau khi luồng replay đã im (ví dụ người dùng bấm Stop giữa đoạn).
SEG_MIN_S, SEG_MAX_S = 0.02, 10.0


class SmoothCursor:
    """Con trỏ chạy mượt giữa hai mốc dữ liệu.

    Luồng replay chỉ báo vị trí mới mỗi bước hồ sơ (1 giây hồ sơ / tốc độ). Lớp
    này nhớ mốc trước, mốc sau và thời điểm bắt đầu, rồi trả vị trí nội suy tại
    thời điểm bất kỳ. Không hề gọi Tk/matplotlib nên test được thuần Python.
    """

    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self._from = 0.0
        self._to = 0.0
        self._t0 = clock()
        self._dur = 0.0
        self._last = 0.0

    def jump(self, x, now=None):
        """Nhảy thẳng tới vị trí (Reset, đổi hồ sơ) — không nội suy."""
        now = self._clock() if now is None else now
        x = float(x)
        self._from = self._to = self._last = x
        self._t0, self._dur = now, 0.0

    def target(self, x, dur, now=None):
        """Đặt mốc mới; con trỏ đi từ vị trí ĐANG hiện tới `x` trong `dur` giây."""
        now = self._clock() if now is None else now
        cur = self.value(now)[0]
        self._from = cur
        self._to = float(x)
        self._t0 = now
        self._dur = max(SEG_MIN_S, min(SEG_MAX_S, float(dur)))
        self._last = cur

    def value(self, now=None):
        """Trả (vị trí, còn đang chạy). Hết đoạn thì chốt đúng mốc đích."""
        now = self._clock() if now is None else now
        if self._dur <= 0.0 or now >= self._t0 + self._dur:
            self._last = self._to
            return self._to, False
        if now <= self._t0:
            self._last = self._from
            return self._from, True
        t = (now - self._t0) / self._dur
        self._last = self._from + (self._to - self._from) * t
        return self._last, True

    def current(self):
        """Vị trí đã tính lần gần nhất — dùng khi vẽ lại nền, khỏi nhích con trỏ."""
        return self._last

    def moving(self, now=None):
        return self.value(now)[1]


class PerfStats:
    """Đếm nhịp callback và thời gian vẽ của vòng hiển thị.

    Giữ cửa sổ trượt để báo số trung bình/p95 trên đoạn gần nhất, kèm số tổng
    cộng dồn. Đây là móc đo cho người review: có số thật mới được nói về 60 Hz.
    """

    def __init__(self, window=240):
        self.window = int(window)
        self._iv = deque(maxlen=self.window)     # khoảng giữa hai callback (s)
        self._draw = deque(maxlen=self.window)   # thời gian một lần vẽ (s)
        self._prev_tick = None
        self.frames = 0
        self.draws = 0
        self.skipped = 0                         # lần bỏ blit vì thiếu nền cache
        self.full_draws = 0                      # lần phải vẽ lại toàn hình
        self.started = time.monotonic()

    def reset(self):
        self._iv.clear()
        self._draw.clear()
        self._prev_tick = None
        self.frames = self.draws = self.skipped = self.full_draws = 0
        self.started = time.monotonic()

    def tick(self, now):
        """Gọi ở đầu mỗi callback của vòng vẽ."""
        self.frames += 1
        if self._prev_tick is not None:
            self._iv.append(now - self._prev_tick)
        self._prev_tick = now

    def gap(self):
        """Ngắt mạch đo khoảng thời gian (vòng vẽ vừa nghỉ) để khỏi ghi nhịp ảo."""
        self._prev_tick = None

    def add_draw(self, sec):
        self.draws += 1
        self._draw.append(float(sec))

    @staticmethod
    def _stat(vals):
        if not vals:
            return {"n": 0, "avg": 0.0, "p95": 0.0, "max": 0.0, "min": 0.0}
        s = sorted(vals)
        k = min(len(s) - 1, int(round(0.95 * (len(s) - 1))))
        return {"n": len(s), "avg": sum(s) / len(s), "p95": s[k],
                "max": s[-1], "min": s[0]}

    def snapshot(self):
        """Số đo dạng dict, đơn vị ms — root dùng để báo cáo nghiệm thu."""
        iv = self._stat(self._iv)
        dr = self._stat(self._draw)
        fps = (1.0 / iv["avg"]) if iv["avg"] > 0 else 0.0
        return {
            "frames": self.frames, "draws": self.draws,
            "skipped": self.skipped, "full_draws": self.full_draws,
            "cb_n": iv["n"],
            "cb_ms_avg": iv["avg"] * 1000.0, "cb_ms_p95": iv["p95"] * 1000.0,
            "cb_ms_max": iv["max"] * 1000.0, "cb_ms_min": iv["min"] * 1000.0,
            "fps_avg": fps,
            "draw_n": dr["n"],
            "draw_ms_avg": dr["avg"] * 1000.0, "draw_ms_p95": dr["p95"] * 1000.0,
            "draw_ms_max": dr["max"] * 1000.0,
        }

    def summary(self):
        """Một dòng gọn để in vào log/stdout."""
        s = self.snapshot()
        return ("frames={frames} fps~{fps_avg:.1f} "
                "cb avg/p95/max {cb_ms_avg:.1f}/{cb_ms_p95:.1f}/{cb_ms_max:.1f}ms "
                "draw avg/p95/max {draw_ms_avg:.2f}/{draw_ms_p95:.2f}/{draw_ms_max:.2f}ms "
                "full={full_draws} skip={skipped}").format(**s)


def bounded_drain(q, max_items=64, budget_s=0.012, clock=time.perf_counter):
    """Lấy tối đa `max_items` phần tử hoặc tới khi hết `budget_s` giây.

    Trả (danh sách lấy được, còn tồn hay không). Nhờ vậy RX dồn một cục không
    khiến vòng lặp giao diện đứng: phần còn lại để nhịp sau xử lý tiếp.
    """
    out = []
    t0 = clock()
    while len(out) < max_items:
        try:
            out.append(q.get_nowait())
        except Exception:          # queue.Empty — tránh phải import queue ở đây
            return out, False
        if clock() - t0 >= budget_s:
            break
    return out, not q.empty()


def trim_text_lines(text, max_lines):
    """Cắt bớt đầu chuỗi log để giữ không quá `max_lines` dòng."""
    if max_lines <= 0:
        return ""
    lines = text.splitlines(True)
    if len(lines) <= max_lines:
        return text
    return "".join(lines[-max_lines:])
