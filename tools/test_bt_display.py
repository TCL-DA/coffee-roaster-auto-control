# -*- coding: utf-8 -*-
"""
Kiểm thử vòng hiển thị của BT Serial Tester.

Hai chế độ:
  • `python tools/test_bt_display.py`          — kiểm thử LOGIC THUẦN: con trỏ nội
    suy, bộ đếm hiệu năng, lấy queue có giới hạn, vài hàm thuần của app. Không mở
    cửa sổ, không mở cổng COM, không gửi gì ra thiết bị.
  • `python tools/test_bt_display.py --bench [--secs 6] [--speed 1]` — ĐO THẬT:
    mở app với hồ sơ GIẢ, bơm tin trạng thái đúng nhịp replay rồi in thời gian
    callback và thời gian blit. Vẫn KHÔNG mở COM.
"""

import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bt_display_loop import (FRAME_MS, PerfStats, SmoothCursor, bounded_drain,
                             trim_text_lines)


def fake_profile(n=540):
    """Hồ sơ rang giả: nạp 90°C, tụt tới TP rồi lên dần — đủ hình để vẽ và đo."""
    bt = []
    for i in range(n):
        if i <= 70:
            bt.append(90.0 - 0.5 * i)
        else:
            bt.append(55.0 + (205.0 - 55.0) * ((i - 70) / float(n - 71)) ** 0.85)
    mm = lambda s: "%02d:%02d" % (s // 60, s % 60)
    events = [("CHARGE", 0, mm(0)), ("TP", 70, mm(70)),
              ("DE", int(n * 0.45), mm(int(n * 0.45))),
              ("FCs", int(n * 0.82), mm(int(n * 0.82))),
              ("DROP", n - 1, mm(n - 1))]
    return bt, events, bt[0]


def fake_csv(path, n=240):
    """Ghi file CSV kiểu Roaster Scope (phân cách Tab) để thử parse_profile."""
    tab = "\t"
    rows = ["Time1" + tab + "Time2" + tab + "ET" + tab + "BT" + tab + "Event"]
    for i in range(n):
        ev = {0: "CHARGE", 60: "TP", 120: "DRY END", 190: "FCS", n - 1: "DROP"}.get(i, "")
        rows.append(tab.join(["00:00", "%02d:%02d" % (i // 60, i % 60),
                              "200.0", "%.1f" % (90.0 + i * 0.4), ev]))
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(rows))
    return path


class TestSmoothCursor(unittest.TestCase):
    def test_noi_suy_tuyen_tinh(self):
        c = SmoothCursor()
        c.jump(0, now=100.0)
        c.target(10, 1.0, now=100.0)
        self.assertAlmostEqual(c.value(100.0)[0], 0.0)
        self.assertAlmostEqual(c.value(100.25)[0], 2.5)
        self.assertAlmostEqual(c.value(100.5)[0], 5.0)
        self.assertTrue(c.value(100.5)[1])

    def test_het_doan_thi_chot_dung_moc(self):
        c = SmoothCursor()
        c.jump(0, now=0.0)
        c.target(5, 0.5, now=0.0)
        self.assertEqual(c.value(0.5), (5.0, False))
        self.assertEqual(c.value(9.0), (5.0, False))
        self.assertEqual(c.current(), 5.0)

    def test_doi_moc_giua_duong_thi_di_tu_vi_tri_dang_co(self):
        c = SmoothCursor()
        c.jump(0, now=0.0)
        c.target(10, 1.0, now=0.0)
        c.target(20, 1.0, now=0.5)          # đang ở 5.0
        self.assertAlmostEqual(c.value(0.5)[0], 5.0)
        self.assertAlmostEqual(c.value(1.0)[0], 12.5)

    def test_jump_khong_noi_suy(self):
        c = SmoothCursor()
        c.target(100, 1.0, now=0.0)
        c.jump(0, now=0.1)
        self.assertEqual(c.value(0.2), (0.0, False))

    def test_dung_yen_khi_hai_moc_bang_nhau(self):
        c = SmoothCursor()
        c.jump(-36, now=0.0)
        c.target(-36, 0.08, now=0.0)
        self.assertAlmostEqual(c.value(0.04)[0], -36.0)


class TestPerfStats(unittest.TestCase):
    def test_nhip_callback_va_thoi_gian_ve(self):
        p = PerfStats()
        for i in range(11):
            p.tick(i * 0.016)
        for _ in range(5):
            p.add_draw(0.0012)
        s = p.snapshot()
        self.assertEqual(s["frames"], 11)
        self.assertEqual(s["cb_n"], 10)
        self.assertAlmostEqual(s["cb_ms_avg"], 16.0, places=3)
        self.assertAlmostEqual(s["fps_avg"], 62.5, places=2)
        self.assertAlmostEqual(s["draw_ms_avg"], 1.2, places=3)
        self.assertIn("frames=11", p.summary())

    def test_gap_khong_tinh_khoang_nghi_thanh_nhip(self):
        p = PerfStats()
        p.tick(0.0)
        p.tick(0.016)
        p.gap()
        p.tick(5.0)                          # nghỉ 5 giây, không được tính
        self.assertEqual(p.snapshot()["cb_n"], 1)

    def test_reset_xoa_sach(self):
        p = PerfStats()
        p.tick(0.0); p.tick(0.02); p.add_draw(0.001)
        p.reset()
        s = p.snapshot()
        self.assertEqual((s["frames"], s["draws"], s["cb_n"]), (0, 0, 0))


class TestBoundedDrain(unittest.TestCase):
    def setUp(self):
        import queue
        self.q = queue.Queue()

    def test_chan_so_phan_tu_moi_nhip(self):
        for i in range(100):
            self.q.put(i)
        got, more = bounded_drain(self.q, max_items=10, budget_s=1.0)
        self.assertEqual(got, list(range(10)))
        self.assertTrue(more)

    def test_het_queue_thi_bao_khong_con_ton(self):
        self.q.put("a")
        got, more = bounded_drain(self.q, max_items=10, budget_s=1.0)
        self.assertEqual(got, ["a"])
        self.assertFalse(more)

    def test_chan_theo_thoi_gian(self):
        for i in range(50):
            self.q.put(i)
        ticks = iter([0.0] + [1.0] * 50)      # lần đo thứ hai đã quá hạn
        got, more = bounded_drain(self.q, max_items=50, budget_s=0.5,
                                  clock=lambda: next(ticks))
        self.assertEqual(len(got), 1)
        self.assertTrue(more)


class TestTrimTextLines(unittest.TestCase):
    def test_cat_bot_dau(self):
        text = "".join("dong %d\n" % i for i in range(10))
        self.assertEqual(trim_text_lines(text, 3).count("\n"), 3)
        self.assertTrue(trim_text_lines(text, 3).startswith("dong 7"))
        self.assertEqual(trim_text_lines(text, 99), text)
        self.assertEqual(trim_text_lines(text, 0), "")


class TestFrameTarget(unittest.TestCase):
    def test_nhip_ve_nham_60hz(self):
        # 16 ms là MỤC TIÊU; nhịp thực phải đo bằng --bench, không suy từ hằng số
        self.assertLessEqual(FRAME_MS, 17)
        self.assertGreaterEqual(FRAME_MS, 10)


def _import_app():
    """Import module app. Thiếu thư viện GUI thì bỏ qua nhóm test này."""
    try:
        import bt_serial_tester_glass as g
        return g
    except ImportError as e:                  # pragma: no cover
        raise unittest.SkipTest("thiếu thư viện: %s" % e)


class TestGlassPureLogic(unittest.TestCase):
    """Các hàm thuần của app — gọi được mà không dựng cửa sổ, không mở COM."""

    @classmethod
    def setUpClass(cls):
        cls.g = _import_app()

    def test_compose_commands(self):
        self.assertEqual(self.g.compose_commands(-26), "rreq")
        self.assertEqual(self.g.compose_commands(13), "921")      # 10 + 2 + 1
        self.assertEqual(self.g.compose_commands(18), "9521")     # 10 + 5 + 2 + 1
        self.assertEqual(self.g.compose_commands(0), "")

    def test_parse_speed_giu_nguyen_ngu_nghia(self):
        p = self.g.App._parse_speed
        self.assertAlmostEqual(p("x0.85"), 0.85)
        self.assertAlmostEqual(p("0,85"), 0.85)
        self.assertAlmostEqual(p("85%"), 0.85)
        self.assertIsNone(p("abc"))
        self.assertAlmostEqual(p("999"), self.g.SPEED_MAX)

    def test_parse_ror_max_giu_nguyen_ngu_nghia(self):
        p = self.g.App._parse_ror_max
        self.assertEqual(p("Tự động"), "auto")
        self.assertEqual(p(""), "auto")
        self.assertAlmostEqual(p("35"), 35.0)
        self.assertAlmostEqual(p("9999"), self.g.ROR_MAX_MAX)
        self.assertIsNone(p("abc"))

    def test_fmt(self):
        self.assertEqual(self.g.fmt_speed(1.0), "x1")
        self.assertEqual(self.g.fmt_speed(0.85), "x0.85")
        self.assertEqual(self.g.fmt_num(35.0), "35")
        self.assertEqual(self.g.fmt_num(37.5), "37.5")

    def test_parse_profile_doc_duoc_csv(self):
        path = os.path.join(tempfile.gettempdir(), "bt_tester_fake_profile.csv")
        fake_csv(path)
        bt, events, charge = self.g.parse_profile(path)
        labels = [e[0] for e in events]
        self.assertEqual(labels, ["CHARGE", "TP", "DE", "FCs", "DROP"])
        self.assertAlmostEqual(charge, bt[0])
        self.assertEqual(len(bt), 240)
        os.remove(path)

    def test_ror_theo_kalman_khong_doi(self):
        ror = self.g.compute_ror([100.0 + i for i in range(60)])
        self.assertEqual(len(ror), 60)
        self.assertGreater(ror[-1], 0.0)      # BT tăng đều thì RoR phải dương


def bench(secs=6.0, speed=1.0):
    """Đo nhịp callback và thời gian blit với HỒ SƠ GIẢ — không mở cổng COM.

    Bơm tin vào `_ui_q` đúng như luồng replay (1 bước mỗi 1/speed giây) rồi để
    `mainloop()` THẬT chạy vòng vẽ — đo bằng vòng lặp tay sẽ ra nhịp của vòng lặp
    đó, không phải nhịp app. In số đo của PerfStats; đây là bằng chứng duy nhất
    được dùng khi nói về 60 Hz."""
    g = _import_app()
    app = g.App()
    app.geometry("1366x768")
    bt, events, charge = fake_profile()
    app.load_profile_data(bt, events, charge, "bench-fake.csv")
    step = 1.0 / float(speed)
    step_ms = max(1, int(round(step * 1000)))
    state = {"idx": 0, "job": None}

    def feed():
        """Thay luồng replay: mỗi bước một tin, KHÔNG nhanh hơn nhịp gửi lệnh."""
        i = state["idx"]
        app._ui_q.put(("ui", app._play_gen, bt[i % len(bt)], i + 1, "BENCH", 120, step))
        state["idx"] = i + 1
        state["job"] = app.after(step_ms, feed)

    app.after(400, app.perf.reset)            # bỏ giai đoạn vẽ/cache ban đầu
    app.after(450, feed)
    app.after(int(450 + secs * 1000.0), app.quit)
    app.mainloop()
    if state["job"] is not None:
        try:
            app.after_cancel(state["job"])
        except Exception:
            pass
    idx = state["idx"]
    snap = app.perf_snapshot()
    print("BT Serial Tester — do vong hien thi (ho so gia, khong mo COM)")
    print("  secs=%.1f speed=x%s buoc=%d FRAME_MS=%d" % (secs, speed, idx, FRAME_MS))
    print("  " + app.perf.summary())
    print("  cb_ms min/avg/p95/max = %.2f / %.2f / %.2f / %.2f"
          % (snap["cb_ms_min"], snap["cb_ms_avg"], snap["cb_ms_p95"], snap["cb_ms_max"]))
    print("  draw_ms avg/p95/max   = %.3f / %.3f / %.3f"
          % (snap["draw_ms_avg"], snap["draw_ms_p95"], snap["draw_ms_max"]))
    print("  ghi chu: cb_ms la khoang giua hai callback Tk; fps_avg = 1/cb_ms_avg.")
    app._on_close()
    return snap


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--bench" in args:
        def _arg(name, default):
            return float(args[args.index(name) + 1]) if name in args else default
        bench(secs=_arg("--secs", 6.0), speed=_arg("--speed", 1.0))
    else:
        unittest.main(argv=[sys.argv[0]], verbosity=2)
