"""Khớp lại mô hình nhiệt board ảo (08/10/2026 tối — chủ máy: "ET giả trân", "tăng nhiệt trước charge quá chậm, ngoài đời RoR
lúc nào cũng hơn 15 °C/phút và giảm dần khi gần charge").
Bản cũ (fit_plant.py) chỉ có BT của mẻ SD 1904/1 (KHÔNG có ET) -> ET suy ra sai, hệ số W lồng rỗng chạm biên 0,2 -> hâm cực chậm.
Phương trình = ĐÚNG plant_step() trong sim_core.cpp (hệ số cắm thẳng vào):
  airf = 0.25 + 0.75·gió/100;  et += gas·A − (et−amb)·(B|BE)·airf − (et−bean)·C·[có hạt] − (et−vách)·D;  vách += (et−vách)·E
  có hạt: bean += (et−bean)·K1 + (vách−bean)·K2;  probe += (bean−probe)/TAU
  lồng rỗng: probe += (W·et + (1−W)·vách − probe)/TAU_E
Dữ liệu + ràng buộc:
  1. F:/Artisan/Profile/1904/1.CSV (máy 30 kg, % gas + gió thật): BT 118 s lồng rỗng + 918 s có hạt
  2. F:/Artisan/Linh-tinh/30kg_auto_ThaiLan/21-07-09_1726.alog (30 kg, ET thật): khoảng ET − BT theo BT sau TP
  3. hâm từ nguội, gas mồi 32 % (preGas 40 × trần 80 %), gió 43 %: 150 -> 185 °C với RoR ≥ 15 °C/phút; ET − BT ≤ 25 ở 180;
     lên 180 °C trong 10…20 phút
    python fit_plant2.py ra.json"""
import ast
import json
import sys

import numpy as np
from scipy.optimize import least_squares

SRC = r"F:/Artisan/Profile/1904/1.CSV"
THAI = r"F:/Artisan/Linh-tinh/30kg_auto_ThaiLan/21-07-09_1726.alog"
AMB = 30.0
NAMES = ["QMAX", "B", "BE", "C", "D", "E", "K1", "K2", "TAU", "W", "TAU_E", "PMIN", "NEXP", "et_p0", "wall_p0"]
X0 = [2.0, 0.0024, 0.004, 0.0138, 0.0124, 0.0061, 0.0009, 0.0034, 33.8, 0.95, 10.0, 0.2, 1.6, 200.0, 160.0]
LO = [0.3, 0.0005, 0.0005, 0.0005, 0.0001, 0.0002, 0.00001, 0.0001, 5.0, 0.85, 5.0, 0.05, 1.0, 120.0, 100.0]  # W ≥ 0,85, TAU_E 5..20 s   # W ≥ 0,6: đầu dò lồng rỗng nằm trong luồng khí
HI = [6.0, 0.050, 0.080, 0.080, 0.050, 0.0200, 0.0060, 0.0200, 80.0, 1.0, 20.0, 0.45, 3.0, 320.0, 300.0]


def load_sd():
    txt = open(SRC, "rb").read().decode("latin1").replace("\r", "")
    rows = [l.split("\t") for l in txt.split("\n")[2:] if l[:1].isdigit()]
    pre = [r for r in rows if not r[1]]
    roast = [r for r in rows if r[1]]
    f = lambda rs, i: np.array([float(r[i]) for r in rs])  # noqa: E731
    return (f(pre, 3), f(pre, 5), f(pre, 6)), (f(roast, 3), f(roast, 5), f(roast, 6))   # premix: % gas log = % công suất bếp (HMI ép $M28 ≤ 50 %: lệnh 100 % = đầu ra 50 % = lửa max)


def gap_thai():
    """Khoảng ET − BT theo BT (sau TP, trước xả) của mẻ 30 kg thật có ET."""
    p = ast.literal_eval(open(THAI, encoding="utf-8", errors="replace").read())
    tx, bt, et, ti = p["timex"], p["temp2"], p["temp1"], p["timeindex"]
    i0, i1 = ti[0], ti[6]
    tp = i0 + int(np.argmin(bt[i0:i0 + 200]))
    b = np.array(bt[tp:i1])
    g = np.array(et[tp:i1]) - b
    o = np.argsort(b)
    return b[o], g[o]


def step(p, st, a, g, loaded):
    QMAX, B, BE, C, D, E, K1, K2, TAU, W, TAU_E, PMIN, NEXP = p[:13]
    et, wall, bean, probe = st
    airf = 0.25 + 0.75 * a / 100.0
    q = QMAX * (PMIN + (1 - PMIN) * (max(0.0, g) / 100.0) ** NEXP) if g >= 0 else 0.0   # premix; g < 0 = relay gas TẮT
    if loaded:
        det = q - (et - AMB) * B * airf - (et - bean) * C - (et - wall) * D
        wall2 = wall + (et - wall) * E
        bean2 = bean + (et - bean) * K1 + (wall - bean) * K2
        probe2 = probe + (bean - probe) / TAU
    else:
        det = q - (et - AMB) * BE * airf - (et - wall) * D
        wall2 = wall + (et - wall) * E
        bean2 = AMB
        probe2 = probe + ((W * et + (1 - W) * wall) - probe) / TAU_E
    et2 = max(AMB, et + det)
    return et2, wall2, bean2, probe2


def run_sd(p, pre, roast):
    (pbt, pair, pgas), (bt, air, gas) = pre, roast
    st = (p[13], p[14], AMB, pbt[0])
    y1 = []
    for a, g in zip(pair, pgas):
        st = step(p, st, a, g, False)
        y1.append(st[3])
    st = (st[0], st[1], AMB, bt[0])
    y2, ets = [], []
    for a, g in zip(air, gas):
        st = step(p, st, a, g, True)
        y2.append(st[3])
        ets.append(st[0])
    return np.array(y1), np.array(y2), np.array(ets)


def han_nguoi(p, gas=52.0, air=20.0, giay=1500):
    """Firmware Preheat (Preheat.h): gas 65 % khi còn xa đích (× trần 80 % = 52 % thực), gió ≤ 20 % (PH_HEAT_AIR_FAR_MAX)."""
    return _han(p, gas, air, giay)


def _han(p, gas, air, giay):
    """Hâm từ nguội lồng rỗng: (BT, ET) từng giây."""
    st = (AMB, AMB, AMB, AMB)
    bt, et = [], []
    for _ in range(giay):
        st = step(p, st, air, gas, False)
        bt.append(st[3])
        et.append(st[0])
    return np.array(bt), np.array(et)


def truoc_nap(p, nap=195.0, lui=20.0, gas_moi=40.0, air=43.0):
    """Trình tự ĐO trên máy ảo 08/10 23:27 (firmware thật, bếp premix): Preheat lệnh 40 % gió 20 % 15 phút -> START: tắt gas chờ
    BT ≤ nap − $M9 -> relay gas bật, quạt xả + mồi 40 s (KHÔNG có nhiệt, gió 43 % vẫn thổi) -> có lửa, gas mồi $M8 = lệnh 40 %
    cố định tới BT ≥ nap − $M10. Chủ máy: thực tế tầm 1 – 1,5 phút. Trả BT từng giây từ lúc CÓ LỬA."""
    st = (AMB, AMB, AMB, AMB)
    for _ in range(900):
        st = step(p, st, 20.0, 40.0, False)
    for _ in range(1800):
        st = step(p, st, air, -1.0, False)
        if st[3] <= nap - lui:
            break
    for _ in range(40):
        st = step(p, st, air, -1.0, False)
    bt = []
    for _ in range(600):
        st = step(p, st, air, gas_moi, False)
        bt.append(st[3])
        if st[3] >= nap - 3:
            break
    return np.array(bt)


def tran_lua_nho(p, gas=20.0, air=43.0):
    """Lồng rỗng gas 25 % đặt (20 % DAC) chạy lâu: BT cân bằng (máy 6 kg premix thật: ~160 °C)."""
    st = (AMB, AMB, AMB, AMB)
    for _ in range(5400):
        st = step(p, st, air, gas, False)
    return st[3]


def ror_doan(bt, lo, hi):
    idx = np.where((bt >= lo) & (bt < hi))[0]
    if len(idx) < 2:
        return 0.0
    return (bt[idx[-1]] - bt[idx[0]]) / max(1, idx[-1] - idx[0]) * 60


def main():
    pre, roast = load_sd()
    gb, gg = gap_thai()

    def resid(p):
        y1, y2, ets = run_sd(p, pre, roast)
        r_pre = (y1 - pre[0]) * 0.0                 # đoạn này BT tụt rồi vọt (cửa mở / mẻ trước) — bỏ, kéo W về biên 0,2
        r_bt = y2 - roast[0]
        r_bt[:90] *= 0.5
        tp = int(np.argmin(roast[0][:200]))
        b = y2[tp:]
        gap_ref = np.interp(b, gb, gg)
        r_gap = ((ets[tp:] - b) - gap_ref) * 0.35
        # Preheat firmware thật (đo 08/10 23:15): premix gas 20 % DAC, gió 20 %, 15 phút -> phải lên ≥ 205 °C (đích 210)
        hb, he = _han(p, 40.0, 20.0, 900)                       # lệnh 40 % (đầu ra van 20 % đo được)
        r_han = [max(0.0, 205.0 - hb[-1]) * 1.0, max(0.0, (he[-1] - hb[-1]) - 25.0) * 0.5]
        tn = truoc_nap(p)
        r_tn = [max(0.0, len(tn) - 90) * 2.0 + max(0.0, 55 - len(tn)) * 2.0,   # có lửa tới nạp: 60 – 90 s (chủ máy: 1 – 1,5 phút)
                max(0.0, ror_doan(tn, 186, 192) - ror_doan(tn, 165, 180) + 1.0) * 2.0]   # chậm dần khi gần nạp
        r_nho = [0.0]   # 'trần ~160 °C ở gas 25 %' là số máy 6 kg Philippines, KHÔNG phải OTL-30A — chủ máy: trước nạp RoR > 15
        r_et = np.clip(ets - 300.0, 0, None) * 0.3
        return np.concatenate([r_pre, r_bt, r_gap, np.array(r_han), np.array(r_tn), np.array(r_nho), r_et])

    best = least_squares(resid, X0, bounds=(LO, HI), loss="soft_l1", f_scale=2.0, max_nfev=3000)
    p = best.x
    y1, y2, ets = run_sd(p, pre, roast)
    bt = roast[0]
    err = y2 - bt
    tp = int(np.argmin(bt[:200]))
    print("he so:", json.dumps({n: round(float(v), 6) for n, v in zip(NAMES, p)}))
    print("long rong (1904/1): RMS %.2f" % float(np.sqrt(np.mean((y1 - pre[0]) ** 2))))
    print("co hat: RMS %.2f | sau TP max %.2f" % (float(np.sqrt(np.mean(err ** 2))), float(np.max(np.abs(err[tp:])))))
    for t in (0, 60, 90, 180, 300, 454, 600, 711, 800, 917):
        ref = float(np.interp(y2[t], gb, gg)) if t >= tp else float("nan")
        print("  t=%3d  BT that %.1f | mo hinh %.1f | ET %.0f (ET-BT %.0f, mau 30kg %.0f) | gas %.0f" % (
            t, bt[t], y2[t], ets[t], ets[t] - y2[t], ref, roast[2][t]))
    hb, he = _han(p, 40.0, 20.0, 900)
    print("  Preheat firmware (premix 20%% DAC, gio 20%%, 15 phut): BT cuoi %.0f, ET %.0f" % (hb[-1], he[-1]))
    for x in (100, 150, 165, 180, 185):
        i = np.where(hb >= x)[0]
        if len(i):
            j = i[0]
            ror = (hb[min(j + 30, len(hb) - 1)] - hb[max(0, j - 30)]) / 60 * 60
            print("  Preheat 20%% DAC: BT %d o phut %.1f, RoR %.1f C/phut, ET %.0f" % (x, j / 60, ror, he[j]))
    tn = truoc_nap(p)
    print("  START sau Preheat: tu luc CO LUA (gas moi lenh 40%%) toi nap %d s, BT %.0f -> %.0f | RoR 165-180 %.1f, 186-192 %.1f C/phut" % (
        len(tn), tn[0], tn[-1], ror_doan(tn, 165, 180), ror_doan(tn, 186, 192)))
    print("  long rong gas 25%% dat (20%% DAC) chay lau: BT can bang %.0f C (may 6 kg premix that ~160)" % tran_lua_nho(p))
    for g in (0, 20, 40, 60, 100):
        print("  cong suat premix o lenh %d%%: %.0f%% cong suat toi da" % (g, 100 * (p[11] + (1 - p[11]) * (g / 100.0) ** p[12])))
    json.dump({n: float(v) for n, v in zip(NAMES, p)}, open(sys.argv[1], "w"))


if __name__ == "__main__":
    main()
