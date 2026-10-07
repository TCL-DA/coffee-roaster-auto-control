"""Khớp mô hình nhiệt của board ảo theo MẺ THẬT (F:/Artisan/Profile/1904/1.CSV, máy 30 kg).

Mô hình 4 trạng thái: et (khí nóng), wall (vách trống), bean (khối hạt), probe (đầu dò BT).
Đầu vào: gas %, gió % từng giây của mẻ thật. Hai đoạn dữ liệu:
  - 118 s lồng RỖNG trước khi nạp (gas 35 %): đầu dò đo hỗn hợp khí + vách;
  - 918 s có hạt, từ CHARGE tới DROP: đầu dò đo khối hạt (có trễ).
Ràng buộc vật lý: ET không vượt 300 °C trong mẻ; lồng rỗng gas 35 % cân bằng quanh 300 °C
(firmware cắt gas ở ET > 350, báo lệch đầu dò ở ET > 300 khi BT < 150).
"""
import json
import sys

import numpy as np
from scipy.optimize import least_squares

SRC = r"F:/Artisan/Profile/1904/1.CSV"
AMB = 30.0


def load():
    txt = open(SRC, "rb").read().decode("latin1").replace("\r", "")
    rows = [l.split("\t") for l in txt.split("\n")[2:] if l[:1].isdigit()]
    pre = [r for r in rows if not r[1]]
    roast = [r for r in rows if r[1]]
    f = lambda rs, i: np.array([float(r[i]) for r in rs])  # noqa: E731
    return (f(pre, 3), f(pre, 5), f(pre, 6)), (f(roast, 3), f(roast, 5), f(roast, 6))


NAMES = ["A", "B", "C", "D", "E", "F", "K1", "K2", "tau", "w", "tau_e", "et_p0", "wall_p0"]
X0 = [0.050, 0.012, 0.012, 0.010, 0.003, 0.002, 0.0008, 0.0025, 30.0, 0.6, 20.0, 190.0, 150.0]
LO = [0.005, 0.002, 0.000, 0.001, 0.0005, 0.000, 0.0001, 0.0000, 8.0, 0.2, 5.0, 120.0, 100.0]
HI = [0.300, 0.080, 0.080, 0.060, 0.0200, 0.020, 0.0060, 0.0060, 60.0, 1.0, 60.0, 300.0, 280.0]


def step(p, st, a, g, loaded):
    A, B, C, D, E, F, K1, K2, tau, w, tau_e = p[:11]
    et, wall, bean, probe = st
    airf = 0.25 + 0.75 * a / 100.0
    if loaded:
        det = g * A - B * airf * (et - AMB) - C * (et - bean) - D * (et - wall)
        dwall = E * (et - wall) - F * (wall - bean)
        bean += K1 * (et - bean) + K2 * (wall - bean)
        probe += (bean - probe) / tau
    else:
        det = g * A - B * airf * (et - AMB) - D * (et - wall)
        dwall = E * (et - wall)
        probe += ((w * et + (1 - w) * wall) - probe) / tau_e
    return et + det, wall + dwall, bean, probe


def run(p, pre, roast):
    (pbt, pair, pgas), (bt, air, gas) = pre, roast
    st = (p[11], p[12], AMB, pbt[0])
    y1 = []
    for a, g in zip(pair, pgas):
        st = step(p, st, a, g, False)
        y1.append(st[3])
    st = (st[0], st[1], AMB, bt[0])
    y2, ets, walls = [], [], []
    for a, g in zip(air, gas):
        st = step(p, st, a, g, True)
        y2.append(st[3])
        ets.append(st[0])
        walls.append(st[1])
    return np.array(y1), np.array(y2), np.array(ets), np.array(walls)


def et_eq_empty(p, g, a=43.0):
    return AMB + g * p[0] / (p[1] * (0.25 + 0.75 * a / 100.0))


def main():
    pre, roast = load()

    def resid(p):
        y1, y2, ets, _ = run(p, pre, roast)
        r2 = y2 - roast[0]
        r2[:90] *= 0.5
        return np.concatenate([(y1 - pre[0]) * 1.5, r2, np.clip(ets - 290.0, 0, None) * 0.3,
                               [(et_eq_empty(p, 35.0) - 300.0) * 0.2]])

    best = least_squares(resid, X0, bounds=(LO, HI), loss="soft_l1", f_scale=2.0, max_nfev=800)
    p = best.x
    y1, y2, ets, walls = run(p, pre, roast)
    bt = roast[0]
    err = y2 - bt
    print("he so:", json.dumps({n: round(float(v), 5) for n, v in zip(NAMES, p)}))
    print("lồng rỗng: sai so RMS %.2f | cuoi that %.1f mo hinh %.1f" % (
        float(np.sqrt(np.mean((y1 - pre[0]) ** 2))), pre[0][-1], y1[-1]))
    print("co hat: RMS %.2f | max %.2f (t=%d) | sau TP max %.2f | ET %.0f..%.0f | vach %.0f..%.0f" % (
        float(np.sqrt(np.mean(err ** 2))), float(np.max(np.abs(err))), int(np.argmax(np.abs(err))),
        float(np.max(np.abs(err[90:]))), ets.min(), ets.max(), walls.min(), walls.max()))
    for t in (0, 30, 60, 83, 120, 180, 300, 454, 600, 711, 800, 917):
        print("  t=%3d  that %.1f | mo hinh %.1f | ET %.0f | vach %.0f | gas %.0f" % (
            t, bt[t], y2[t], ets[t], walls[t], roast[2][t]))
    for g in (35, 50, 69):
        print("  long rong gas %d %%: ET can bang %.0f C" % (g, et_eq_empty(p, g)))
    json.dump({n: float(v) for n, v in zip(NAMES, p)}, open(sys.argv[1], "w"))


if __name__ == "__main__":
    main()
