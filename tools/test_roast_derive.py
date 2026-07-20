"""Kiểm tra roast_derive: RoR và mốc rang có khớp luật firmware không."""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from roast_derive import RoastDeriver, Kalman      # noqa: E402
from pc_link_map import STP                        # noqa: E402

fails = []


def chk(name, cond, got=""):
    print(("  OK   " if cond else "  FAIL ") + name + (f"  → {got}" if got else ""))
    if not cond:
        fails.append(name)


def bt_at(t):
    """Đường BT giống mẻ thật: 200°C lúc nạp → đáy ~90°C ở 90 s → lên 210°C ở 600 s."""
    if t < 90:
        return 200 - 110 * (t / 90.0)
    return 90 + 120 * ((t - 90) / 510.0) ** 0.82


print("1) RoR — dốc đều thì phải ra đúng °C/phút")
d = RoastDeriver()
d.charge(100.0)
for t in range(1, 121):
    d.feed(100.0 + t * 0.2, 120.0 + t * 0.2)      # 0.2 °C/giây = 12 °C/phút
chk("RoR bám 12 °C/phút", abs(d.ror_bt - 12.0) < 0.6, round(d.ror_bt, 2))

print("2) RoR — kẹp trần ±95 °C/phút")
d2 = RoastDeriver()
d2.charge(20.0)
for t in range(1, 61):
    d2.feed(20.0 + t * 5.0, 20.0)                  # 300 °C/phút, vượt trần
chk("không vượt 95", d2.ror_bt <= 95.0 + 1e-6, round(d2.ror_bt, 2))

print("3) Mốc rang trên đường cong giống mẻ thật")
d3 = RoastDeriver(de_temp=150.0, fcs_temp=196.0)
d3.charge(bt_at(0))
for t in range(1, 601):
    d3.feed(bt_at(t), bt_at(t) + 16)
m = d3.mile
chk("bắt được TP", "TP" in m, m)
chk("TP đúng chỗ đáy (~90 s)", 85 <= m.get("TP", 0) <= 100, m.get("TP"))
chk("TP ghi nhiệt đáy ~90°C", abs(d3.mile_bt.get("TP", 0) - 90) < 2, round(d3.mile_bt.get("TP", 0), 1))
chk("DE khi BT chạm 150", "DE" in m and abs(bt_at(m["DE"]) - 150) < 2, m.get("DE"))
chk("FCs khi BT chạm 196", "FCs" in m and abs(bt_at(m["FCs"]) - 196) < 2, m.get("FCs"))
chk("thứ tự TP < DE < FCs", m["TP"] < m["DE"] < m["FCs"], m)
chk("step kết thúc ở DEV", d3.step == STP["DEV"], d3.step)
chk("đồng hồ mẻ = số giây đã nạp", d3.t_roast == 600, d3.t_roast)

print("4) Chưa nạp hạt thì đồng hồ không chạy")
d4 = RoastDeriver()
for t in range(30):
    d4.feed(200 - t, 210 - t)
chk("t_roast = 0", d4.t_roast == 0, d4.t_roast)
chk("chưa qua mốc nào", not d4.mile, d4.mile)

print("5) Gói dữ liệu cùng hình dạng với khối PC_Link")
raw = {"bt": 200.0, "et": 216.0, "gas": 35, "air": 60, "drum": 55, "sv": 210.0,
       "vac": -120, "auto": 1, "charge": 0, "drop": 0, "escape": 0, "cool": 0}
snap = d3.snapshot(raw)
need = {"bt", "et", "ror_bt", "ror_et", "ror_pro", "gas", "air", "drum", "sv",
        "vac", "step", "t_roast", "phase", "flags", "hb"}
chk("đủ khoá giao diện cần", need <= set(snap), sorted(need - set(snap)))
chk("có nói rõ số nào do app tính", "ror_bt" in snap["derived"] and "step" in snap["derived"],
    snap["derived"])
chk("flame = None (khối cũ không đọc được)", snap["flags"]["flame"] is None)

print("6) Kalman khớp công thức SimpleKalmanFilter")
k = Kalman(1.0, 1.0, 0.005)
out = [round(k.update(10.0), 4) for _ in range(3)]
chk("hội tụ dần về giá trị đo", out[0] < out[1] < out[2] < 10.0, out)

print("\n" + ("TẤT CẢ ĐẠT" if not fails else f"{len(fails)} MỤC HỎNG: {fails}"))
sys.exit(1 if fails else 0)
