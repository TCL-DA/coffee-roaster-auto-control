"""
Virtual Roaster — Máy rang ảo để test firmware OTL-06ALS không cần tủ điện.

Hai chế độ trong cùng một app:
  1. DEMO (mặc định)  — chạy độc lập, không cần phần cứng. Kéo slider Gas/Air,
     model nhiệt sinh BT/ET/RoR, GUI vẽ giống màn hình HMI. Dùng để kiểm tra
     bản thân model + làm quen layout.
  2. BRIDGE (Modbus) — nếu cài pymodbus + có 2 cổng USB-RS485 nối STM32 thật,
     app đóng vai các node Modbus: đọc gas%/air% firmware ghi ra HMI bus,
     trả BT/ET trên sensor bus. Vòng kín với binary thật (HIL).

Nguồn dữ liệu giao tiếp: tools/sim/register_map.json + ref-sim-interface.md
Tham số nhiệt: analysis-roaster-thermal.md (gas 35% cân bằng, ~1.5 °C/min/%).

Chạy:  python tools/sim/virtual_roaster.py
Phụ thuộc bắt buộc: chỉ stdlib (tkinter). Modbus bridge cần: pip install pymodbus pyserial
"""

import json
import os
import time
import threading
import tkinter as tk
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
REG_MAP_PATH = os.path.join(HERE, "register_map.json")

# ─────────────────────────────────────────────────────────────────────────────
# Cấu hình cổng (chỉ dùng ở chế độ BRIDGE). Để None thì chạy DEMO.
# ─────────────────────────────────────────────────────────────────────────────
HMI_PORT    = None      # vd "COM5"  — bus HMI 115200, app làm slave id 1
SENSOR_PORT = None      # vd "COM6"  — bus cảm biến 38400, app làm slave id 1/2/4/5/7

# ─────────────────────────────────────────────────────────────────────────────
# Tham số model nhiệt — trích từ analysis-roaster-thermal.md
# ─────────────────────────────────────────────────────────────────────────────
GAS_EQUILIB   = 35.0    # % gas tại điểm cân bằng nhiệt (RoR≈0) ở vùng 210-220°C
GAS_SENS      = 1.5     # °C/min thay đổi RoR cho mỗi 1% gas (vùng BT 180-240)
HEATLOSS_K    = 0.020   # hệ số mất nhiệt theo (BT - ambient); kéo RoR<0 khi BT cao
AMBIENT       = 28.0    # nhiệt môi trường (°C)
GAS_LAG_S     = 5.0     # hằng số thời gian lag gas -> RoR (giây)
AIR_COOL_K    = 0.15    # air% làm RoR_ET (và nhẹ RoR_BT) giảm
ET_OFFSET     = 18.0    # ET cao hơn BT khoảng này khi cân bằng
DT            = 1.0     # bước mô phỏng (giây) — khớp chu kỳ firmware


class ThermalModel:
    """Model nhiệt bậc nhất: gas/air -> RoR -> tích phân ra BT/ET.

    Đơn giản hoá có chủ đích — đủ để firmware phản ứng giống thật, không phải
    mô phỏng CFD. Chỉnh hằng số ở phần cấu hình trên nếu cần khớp máy cụ thể.
    """

    def __init__(self, bt0=AMBIENT, et0=AMBIENT):
        self.bt = bt0          # °C thực (không ×10)
        self.et = et0
        self.ror_bt = 0.0      # °C/min
        self.ror_et = 0.0
        self._gas_eff = 0.0    # gas đã qua lag
        self.charged = False   # đã CHARGE chưa (ảnh hưởng khối lượng nhiệt)

    def step(self, gas_pct, air_pct, dt=DT):
        # Lag gas: gas hiệu dụng tiến dần về lệnh đặt
        alpha = dt / (GAS_LAG_S + dt)
        self._gas_eff += alpha * (gas_pct - self._gas_eff)

        # RoR_BT mục tiêu = lực gas trên cân bằng - mất nhiệt theo nhiệt độ - mát do gió
        gas_drive = (self._gas_eff - GAS_EQUILIB) * GAS_SENS
        heat_loss = HEATLOSS_K * max(self.bt - AMBIENT, 0.0)
        air_cool  = AIR_COOL_K * air_pct * 0.1
        self.ror_bt = gas_drive - heat_loss - air_cool

        # ET phản ứng nhanh hơn, nhạy gió hơn
        self.ror_et = (gas_drive * 1.2) - heat_loss - (AIR_COOL_K * air_pct)

        # Tích phân RoR (°C/min) -> nhiệt (°C) theo dt giây
        self.bt += self.ror_bt * dt / 60.0
        self.et += self.ror_et * dt / 60.0

        # ET bám trên BT một khoảng + ảnh hưởng riêng
        target_et = self.bt + ET_OFFSET
        self.et += 0.1 * (target_et - self.et)

        self.bt = max(self.bt, AMBIENT)
        self.et = max(self.et, AMBIENT)
        return self.bt, self.et


# ─────────────────────────────────────────────────────────────────────────────
# Trạng thái chia sẻ giữa GUI / model / Modbus bridge
# ─────────────────────────────────────────────────────────────────────────────
class RoasterState:
    def __init__(self):
        self.model = ThermalModel()
        self.gas = 0.0          # % — DEMO: từ slider; BRIDGE: đọc reg 67
        self.air = 0.0          # %
        self.drum = 60.0        # %
        self.running = False    # đã START chưa
        self.roast_t = 0        # giây kể từ CHARGE
        self.mode = "DEMO"      # DEMO | BRIDGE
        self.lock = threading.Lock()
        self.ror_hist = deque(maxlen=600)   # (t, bt, et) để vẽ

    def tick(self):
        with self.lock:
            bt, et = self.model.step(self.gas, self.air)
            if self.running:
                self.roast_t += 1
            self.ror_hist.append((self.roast_t, bt, et))
            return bt, et


STATE = RoasterState()


# ─────────────────────────────────────────────────────────────────────────────
# Modbus bridge (tuỳ chọn) — chỉ kích hoạt khi có cổng + pymodbus
# ─────────────────────────────────────────────────────────────────────────────
class ModbusBridge:
    """Đóng vai node Modbus. Đọc gas%/air% firmware ghi (HMI bus reg 67/65),
    trả BT/ET (×10) trên sensor bus cho node id 1/2.

    Lưu ý: tempRegister là địa chỉ cấu hình runtime -> dùng datablock trả BT*10
    cho MỌI lệnh đọc-1-reg tới unit 1, ET*10 tới unit 2.
    """

    def __init__(self, state, hmi_port, sensor_port):
        self.state = state
        self.hmi_port = hmi_port
        self.sensor_port = sensor_port
        self._threads = []

    def start(self):
        try:
            from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
            from pymodbus.datastore import ModbusSparseDataBlock
            from pymodbus.server import StartSerialServer
            from pymodbus.transaction import ModbusRtuFramer
        except Exception as e:
            print(f"[BRIDGE] pymodbus chưa sẵn sàng: {e}. Chạy DEMO.")
            return False

        state = self.state

        class TempBlock(ModbusSparseDataBlock):
            """Trả nhiệt độ ×10 cho mọi lệnh đọc, bất kể địa chỉ."""
            def __init__(self, which):
                super().__init__({0: 0})
                self.which = which  # 'BT' | 'ET'

            def getValues(self, address, count=1):
                with state.lock:
                    v = state.model.bt if self.which == "BT" else state.model.et
                return [int(v * 10)] * count

            def validate(self, address, count=1):
                return True

        # Sensor bus: unit 1=BT, 2=ET, 4=drum, 5=air, 7=relay
        sensor_slaves = {
            1: ModbusSlaveContext(hr=TempBlock("BT")),
            2: ModbusSlaveContext(hr=TempBlock("ET")),
            4: ModbusSlaveContext(hr=ModbusSparseDataBlock({8451: 0, 8193: 0})),
            5: ModbusSlaveContext(hr=ModbusSparseDataBlock({8451: 0, 2048: 0, 8716: 0})),
            7: ModbusSlaveContext(co=ModbusSparseDataBlock({i: 0 for i in range(8)})),
        }
        sensor_ctx = ModbusServerContext(slaves=sensor_slaves, single=False)

        # HMI bus: unit 1 — block đủ rộng cho iMemHMI + dAddress
        hmi_block = ModbusSparseDataBlock({i: 0 for i in range(0, 600)})
        hmi_ctx = ModbusServerContext(
            slaves={1: ModbusSlaveContext(hr=hmi_block, co=hmi_block)}, single=False
        )
        self._hmi_block = hmi_block

        def serve(ctx, port, baud, name):
            print(f"[BRIDGE] {name} slave trên {port} @ {baud}")
            StartSerialServer(context=ctx, port=port, baudrate=baud,
                              framer=ModbusRtuFramer, stopbits=1, bytesize=8, parity="N")

        for ctx, port, baud, name in [
            (sensor_ctx, self.sensor_port, 38400, "sensor"),
            (hmi_ctx, self.hmi_port, 115200, "hmi"),
        ]:
            t = threading.Thread(target=serve, args=(ctx, port, baud, name), daemon=True)
            t.start()
            self._threads.append(t)

        # Thread đồng bộ: đọc gas%/air% firmware ghi -> state
        threading.Thread(target=self._sync_loop, daemon=True).start()
        return True

    def _sync_loop(self):
        # HMI 1-based 67/65 -> index 66/64 (xem mục 7 ref-sim-interface.md)
        while True:
            try:
                gas = self._hmi_block.getValues(66, 1)[0] / 10.0
                air = self._hmi_block.getValues(64, 1)[0] / 10.0
                with self.state.lock:
                    self.state.gas = gas
                    self.state.air = air
            except Exception:
                pass
            time.sleep(0.2)


# ─────────────────────────────────────────────────────────────────────────────
# GUI — mô phỏng layout HMI-OTL-ROASTER (1024×600)
# ─────────────────────────────────────────────────────────────────────────────
class RoasterGUI:
    def __init__(self, root, state):
        self.state = state
        self.root = root
        root.title("Virtual Roaster — OTL-06ALS")
        root.configure(bg="#202024")

        # Đồ thị
        self.canvas = tk.Canvas(root, width=720, height=460, bg="#cfcfcf",
                                highlightthickness=0)
        self.canvas.grid(row=0, column=0, rowspan=10, padx=8, pady=8)

        # Cột phải — các ô số giống HMI
        right = tk.Frame(root, bg="#202024")
        right.grid(row=0, column=1, sticky="n", pady=8, padx=4)
        self.mode_lbl = self._big(right, "DEMO", "#e0e0e0")
        self.bt_lbl   = self._row(right, "Bean temp (BT)", "#3a6cff")
        self.rorbt_lbl= self._row(right, "RoR BT", "#3a6cff")
        self.et_lbl   = self._row(right, "Exhaust (ET)", "#ff3a3a")
        self.roret_lbl= self._row(right, "RoR ET", "#ff3a3a")
        self.time_lbl = self._row(right, "Roast time", "#e0e0e0")
        self.gas_lbl  = self._row(right, "Burner gas %", "#ff5fae")
        self.air_lbl  = self._row(right, "Airflow %", "#35d07f")

        # Điều khiển DEMO (slider) + nút HMI
        ctrl = tk.Frame(root, bg="#202024")
        ctrl.grid(row=10, column=0, columnspan=2, sticky="we", padx=8, pady=4)
        self.gas_slider = self._slider(ctrl, "Gas %", 0, self._set_gas)
        self.air_slider = self._slider(ctrl, "Air %", 1, self._set_air)

        btns = tk.Frame(root, bg="#202024")
        btns.grid(row=11, column=0, columnspan=2, pady=6)
        for i, (txt, fn) in enumerate([
            ("Ignition", self._ignition), ("Charge", self._charge),
            ("Drop", self._drop), ("Reset", self._reset),
        ]):
            tk.Button(btns, text=txt, width=10, command=fn,
                      bg="#3a3a40", fg="white").grid(row=0, column=i, padx=4)

    def _big(self, parent, text, color):
        l = tk.Label(parent, text=text, font=("Consolas", 18, "bold"),
                     fg=color, bg="#202024")
        l.pack(anchor="e")
        return l

    def _row(self, parent, name, color):
        f = tk.Frame(parent, bg="#202024")
        f.pack(anchor="e", pady=1)
        tk.Label(f, text=name, font=("Segoe UI", 9), fg="#9a9aa0",
                 bg="#202024").pack(side="left", padx=4)
        val = tk.Label(f, text="--", font=("Consolas", 16, "bold"),
                       fg=color, bg="#202024", width=8, anchor="e")
        val.pack(side="left")
        return val

    def _slider(self, parent, name, col, cb):
        f = tk.Frame(parent, bg="#202024")
        f.grid(row=0, column=col, padx=12)
        tk.Label(f, text=name, fg="#cfcfcf", bg="#202024").pack()
        s = tk.Scale(f, from_=0, to=100, orient="horizontal", length=260,
                     command=cb, bg="#202024", fg="white", troughcolor="#3a3a40",
                     highlightthickness=0)
        s.pack()
        return s

    # ── lệnh nút ───────────────────────────────────────────────────────────
    def _set_gas(self, v):
        if self.state.mode == "DEMO":
            with self.state.lock:
                self.state.gas = float(v)

    def _set_air(self, v):
        if self.state.mode == "DEMO":
            with self.state.lock:
                self.state.air = float(v)

    def _ignition(self):
        with self.state.lock:
            self.state.running = True

    def _charge(self):
        with self.state.lock:
            self.state.model.charged = True
            self.state.roast_t = 0
            self.state.running = True

    def _drop(self):
        with self.state.lock:
            self.state.running = False

    def _reset(self):
        with self.state.lock:
            self.state.model = ThermalModel()
            self.state.roast_t = 0
            self.state.running = False
            self.state.ror_hist.clear()

    # ── vẽ ─────────────────────────────────────────────────────────────────
    def refresh(self):
        st = self.state
        with st.lock:
            m = st.model
            bt, et, rbt, ret = m.bt, m.et, m.ror_bt, m.ror_et
            gas, air, t = st.gas, st.air, st.roast_t
            hist = list(st.ror_hist)

        self.mode_lbl.config(text=st.mode)
        self.bt_lbl.config(text=f"{bt:6.1f}")
        self.et_lbl.config(text=f"{et:6.1f}")
        self.rorbt_lbl.config(text=f"{rbt:5.1f}")
        self.roret_lbl.config(text=f"{ret:5.1f}")
        self.time_lbl.config(text=f"{t//60:02d}:{t%60:02d}")
        self.gas_lbl.config(text=f"{gas:5.1f}")
        self.air_lbl.config(text=f"{air:5.1f}")
        self._draw_curve(hist)
        self.root.after(500, self.refresh)

    def _draw_curve(self, hist):
        c = self.canvas
        c.delete("all")
        W, H = 720, 460
        tmax = max(60, hist[-1][0] if hist else 60)
        ymax = 300.0
        for gy in range(0, 301, 50):       # lưới ngang
            y = H - gy / ymax * H
            c.create_line(0, y, W, y, fill="#bbb")
            c.create_text(18, y, text=str(gy), fill="#666", font=("Segoe UI", 7))
        def pts(idx):
            return [(x / tmax * W, H - max(min(v, ymax), 0) / ymax * H)
                    for x, *vals in hist for v in [vals[idx]]]
        for idx, col in [(0, "#3a6cff"), (1, "#ff3a3a")]:  # BT xanh, ET đỏ
            p = pts(idx)
            if len(p) > 1:
                c.create_line([co for xy in p for co in xy], fill=col, width=2)


# ─────────────────────────────────────────────────────────────────────────────
def model_loop(state):
    """Tick model mỗi DT giây, độc lập với GUI."""
    while True:
        state.tick()
        time.sleep(DT)


def main():
    # Thử bật bridge nếu có cổng; không thì DEMO
    if HMI_PORT and SENSOR_PORT:
        bridge = ModbusBridge(STATE, HMI_PORT, SENSOR_PORT)
        if bridge.start():
            STATE.mode = "BRIDGE"

    threading.Thread(target=model_loop, args=(STATE,), daemon=True).start()

    root = tk.Tk()
    gui = RoasterGUI(root, STATE)
    gui.refresh()
    root.mainloop()


if __name__ == "__main__":
    main()
