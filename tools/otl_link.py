"""
otl_link.py — cầu Modbus RTU giữa app OTL Roast Lab (PC) và máy rang.

Đọc khối register do PC_Link.h cấp (xem include/PC_Link.h và
docs/ref/ref-pc-link-protocol.md):
    ĐỌC  reg 100..114 (15 reg) — BT/ET/RoR/gas/air/drum/SV/vac/step/time/phase/flags/hb
    GHI  reg 120..130 (11 reg) — setpoint + nút ảo, CHỈ có tác dụng khi máy bật
                                 "PC control" trên HMI (cờ PCLF_PCCTRL).

VÌ SAO TỰ VIẾT MODBUS THAY VÌ pymodbus:
    Chỉ cần đúng 2 hàm (0x03 đọc, 0x10 ghi) trên 1 cổng COM. Tự viết ~80 dòng,
    không phụ thuộc phiên bản (API pymodbus đổi liên tục giữa 3.x), đóng exe nhẹ.

MỘT CHỦ CỔNG SERIAL: chỉ luồng poll trong file này được chạm `self._ser`.
Lệnh ghi từ UI xếp hàng vào `_pending`, luồng poll gửi giữa 2 nhịp đọc.

Chạy thử độc lập (không cần app):
    python tools/otl_link.py --port COM9            # xem số live 1 Hz
    python tools/otl_link.py --port COM9 --scan     # dò baud
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time

import serial
from serial.tools import list_ports

# ── Bản đồ register: DÙNG CHUNG với firmware ────────────────────────────────
# pc_link_map.py sinh từ protocol/pc_link.json — cùng nguồn với include/PC_Link_Map.h.
# Thêm/sửa register: sửa JSON rồi chạy `python protocol/gen_pc_link.py`.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pc_link_map                                             # noqa: E402
from pc_link_map import (                                      # noqa: E402
    R_BASE, R_COUNT, W_BASE, W_COUNT, W_INDEX, W_RANGE, W_SCALE, decode,
    A_BASE, A_COUNT, decode_artisan, AW_INDEX, STP,
    CFG_BASE, CFG_MAXIDX, CFG_CMD, CFG_STATUS,
)
from roast_derive import RoastDeriver                           # noqa: E402

# Hai chế độ đọc, app tự dò lúc kết nối:
#   pclink   — máy đã nạp PC_Link: số nào cũng do firmware tính, chuẩn nhất.
#   tuongthich — máy chỉ có khối Artisan 0–19: app TỰ TÍNH RoR/thời gian/mốc
#                (roast_derive.py). Chạy được trên mọi máy đã bán.
MODE_PCLINK = "pclink"
MODE_COMPAT = "tuongthich"

DEFAULT_CFG = {
    # RỖNG là cố ý: máy mới chưa từng chọn cổng → app phải HỎI thợ, không được
    # đoán bừa một cổng. Để sẵn "COM9" thì mỗi máy khách cắm cổng khác là app im
    # lặng nối hụt mà không ai biết vì sao.
    "port": "",
    "baud": pc_link_map.BAUD_DEFAULT,    # đổi nếu HMI set modbusBaud_R
    "slave": pc_link_map.SLAVE_DEFAULT,  # đổi nếu HMI set modbusID_R
    "poll_hz": 8,   # 125ms/vòng — máy chạy 57600 baud, khung đọc ~20ms, dư sức
    "enabled": True,
}


def config_path() -> str:
    base = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                        "OTL Roast Lab HMI")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "link.json")


def load_config() -> dict:
    cfg = dict(DEFAULT_CFG)
    try:
        with open(config_path(), "r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    return cfg


def save_config(cfg: dict) -> dict:
    merged = dict(DEFAULT_CFG)
    merged.update(cfg or {})
    with open(config_path(), "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2)
    return merged


"""Chip USB-serial hay gặp ở tủ điện máy rang — dùng để gợi ý cổng nào đáng thử."""
KNOWN_USB_SERIAL = ("ft232", "ftdi", "pl2303", "prolific", "ch340", "ch341",
                    "cp210", "silicon labs", "usb-serial", "usb serial")


def list_serial_ports() -> list:
    """Danh sách cổng COM kèm THÔNG TIN CHI TIẾT để thợ nhận ra đúng cáp máy rang.

    Bluetooth ảo bị đánh dấu để đẩy xuống cuối — máy rang không bao giờ nằm ở đó.
    """
    out = []
    for p in list_ports.comports():
        desc = p.description or ""
        low = (desc + " " + (p.hwid or "")).lower()
        bluetooth = "bluetooth" in low
        out.append({
            "port": p.device,
            "desc": desc,
            "maker": p.manufacturer or "",
            "product": p.product or "",
            "serial": p.serial_number or "",
            "vid": f"{p.vid:04X}" if p.vid else "",
            "pid": f"{p.pid:04X}" if p.pid else "",
            "location": p.location or "",
            "hwid": p.hwid or "",
            "bluetooth": bluetooth,
            # gợi ý: cáp USB-serial thật, không phải cổng ảo
            "likely": (not bluetooth) and any(k in low for k in KNOWN_USB_SERIAL),
        })
    out.sort(key=lambda d: (d["bluetooth"], not d["likely"], d["port"]))
    return out


# ── Modbus RTU trần ─────────────────────────────────────────────────────────
def crc16(buf: bytes) -> bytes:
    crc = 0xFFFF
    for ch in buf:
        crc ^= ch
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return bytes((crc & 0xFF, crc >> 8))


def _u16(hi: int, lo: int) -> int:
    return (hi << 8) | lo


MB_EXC = {
    1: "hàm không hỗ trợ", 2: "địa chỉ register không tồn tại",
    3: "giá trị không hợp lệ", 4: "lỗi thiết bị",
}


class SensorGuard:
    """Sensor sanity (§16.9) cho MỘT kênh nhiệt (BT hoặc ET) — chặn số rác
    TRƯỚC khi vào app/DB/luật tự động (ngưỡng DROP tự xả ăn theo BT!).

    3 luật, đúng vật lý cặp nhiệt trên máy rang:
      range  — ngoài −20..400°C chắc chắn là rác (hở cặp nhiệt đọc max, chập đọc
               0/âm sâu): GIỮ giá trị tốt gần nhất, cắm cờ.
      spike  — nhảy >25°C giữa 2 lần poll (~125ms): nhiễu RS485 cạnh biến tần.
               Giữ giá trị tốt; mức mới mà ĐỨNG VỮNG quá 3s thì chấp nhận
               (sự kiện thật — nhiễu không bao giờ đứng yên 3 giây).
      frozen — đứng hình y nguyên >120s TRONG LÚC RANG: nghi sensor/module chết
               đơ. Chỉ cắm cờ, không đổi số (số "đứng" vẫn là số đo cuối).
    """

    RANGE_LO, RANGE_HI = -20.0, 400.0
    SPIKE_C = 25.0          # °C giữa 2 lần poll — vật lý trống rang không cho phép
    SPIKE_HOLD_S = 3.0      # mức mới đứng vững quá ngưỡng này = thật, hết nghi nhiễu
    FROZEN_S = 120.0        # đang rang mà BT bất động 2 phút = có chuyện

    def __init__(self):
        self.reset()

    def reset(self):
        """Gọi khi mở lại cổng — quá khứ trước lúc đứt cáp không còn ý nghĩa."""
        self.good = None          # giá trị tốt gần nhất
        self._spike_t0 = None     # lúc bắt đầu chuỗi giá trị nhảy vọt
        self._ref = None          # giá trị so đứng hình
        self._ref_ts = 0.0        # lần cuối giá trị ĐỔI

    def feed(self, v, now, roasting):
        """Trả (giá_trị_nên_dùng, cảnh_báo 'range'/'spike'/'frozen'/None)."""
        if v is None:
            return v, None
        if not (self.RANGE_LO <= v <= self.RANGE_HI):
            self._spike_t0 = None
            return (self.good if self.good is not None else v), "range"
        if self.good is not None and abs(v - self.good) > self.SPIKE_C:
            if self._spike_t0 is None:
                self._spike_t0 = now
            if now - self._spike_t0 < self.SPIKE_HOLD_S:
                return self.good, "spike"
            # đứng vững quá 3s → sự kiện thật, nhận mức mới (rơi xuống dưới)
        self._spike_t0 = None
        if self._ref is None or v != self._ref:
            self._ref, self._ref_ts = v, now
        warn = ("frozen" if roasting and (now - self._ref_ts) > self.FROZEN_S
                else None)
        self.good = v
        return v, warn


class ModbusError(Exception):
    pass


class RoasterLink:
    """Luồng nền: poll khối ĐỌC, gửi lệnh GHI xếp hàng, tự kết nối lại."""

    def __init__(self, cfg: dict | None = None):
        self.cfg = cfg or load_config()
        self._ser: serial.Serial | None = None
        self._lock = threading.Lock()
        self._pending: list[tuple[int, list[int]]] = []
        self._stop = threading.Event()
        self._kick = threading.Event()      # write() đánh thức vòng poll — lệnh phát ngay, khỏi đợi hết chu kỳ
        self._thread: threading.Thread | None = None
        self._snap: dict | None = None      # gói dữ liệu mới nhất đã quy đổi
        self._snap_ts = 0.0
        self._snap_cond = threading.Condition()   # báo "có snapshot mới" cho kênh push
        self._snap_gen = 0                        # số thứ tự snapshot — client so để biết mới/cũ
        self._state = "off"                 # off|connecting|connected|stalled|error
        self._err = ""
        self._hb = -1
        self._hb_ts = 0.0
        self._app_hb = 0                    # heartbeat CỦA APP gửi xuống máy (watchdog PC_Link)
        self._app_hb_ts = 0.0
        self._mode = None                   # dò lúc kết nối: MODE_PCLINK / MODE_COMPAT
        self._r_count = R_COUNT             # firmware CŨ có ít ô đọc hơn → tự lùi (xem _read_pclink)
        self._deriver = RoastDeriver()      # chỉ dùng ở chế độ tương thích
        self._last_charge = 0               # cạnh lên nút charge/drop của HMI
        self._sg_bt = SensorGuard()         # sensor sanity §16.9 — lọc BT/ET rác
        self._sg_et = SensorGuard()         #   ngay tại nguồn: app/DB/web đều hưởng
        # ── Handshake cấu hình $M (đọc/ghi 1 tham số) — chỉ chế độ PC_Link ──
        self._cfg_gate = threading.Lock()   # 1 handshake tại 1 thời điểm
        self._cfg_req: tuple | None = None  # (cmd, idx, val) chờ luồng _run xử
        self._cfg_res: dict | None = None   # kết quả handshake gần nhất
        self._cfg_done = threading.Event()

    # ── vòng đời ────────────────────────────────────────────────────────────
    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="otl-link", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
        self._close()

    def reconfigure(self, cfg: dict):
        """Đổi cổng/baud lúc chạy: lưu file, đá kết nối cũ, luồng tự mở lại."""
        self.cfg = save_config(cfg)
        with self._lock:
            self._pending.clear()
        self._close()

    # ── giao diện cho UI ────────────────────────────────────────────────────
    def wait_snapshot(self, after_gen: int, timeout: float = 15.0):
        """Chặn tới khi có snapshot MỚI hơn after_gen (cho kênh push app/web).

        Trả (gen, snapshot()) — snapshot None nếu hết timeout mà chưa có gì mới."""
        with self._snap_cond:
            ok = self._snap_cond.wait_for(lambda: self._snap_gen > after_gen, timeout)
            gen = self._snap_gen
        return gen, (self.snapshot() if ok else None)

    def snapshot(self) -> dict:
        with self._lock:
            snap, ts, state, err = self._snap, self._snap_ts, self._state, self._err
        age = int((time.time() - ts) * 1000) if ts else None
        return {
            "state": state,
            "err": err,
            "mode": self._mode,
            "port": self.cfg.get("port"),
            "baud": self.cfg.get("baud"),
            "age_ms": age,
            "data": snap,
        }

    def write(self, name: str, value=1) -> dict:
        """Xếp hàng 1 lệnh xuống máy — đơn vị KỸ THUẬT (sv nhận °C, tự nhân hệ số).

        Địa chỉ tuỳ chế độ đã dò: khối PC_Link (120+) hay ô lệnh của khối tương
        thích (10–22).

        KHÔNG phát xung. Xi lanh nạp/xả chạy theo MỨC và firmware TỰ đóng sau
        chargeDuration_R giây; ghi 0 sớm là huỷ luôn timer tự đóng, xi lanh chỉ hé
        rồi sập (IOConfig.h:53, Program.h:2078-2090).

        Máy CHỈ nhận khi nút "PC control" trên HMI đang BẬT.
        """
        if name not in W_INDEX:
            return {"ok": False, "err": f"lệnh lạ: {name}"}
        lo, hi = W_RANGE[name]
        try:
            v = int(round(float(value) * W_SCALE[name]))
        except (TypeError, ValueError):
            return {"ok": False, "err": "giá trị không hợp lệ"}
        v = max(lo, min(hi, v))

        if self._mode == MODE_COMPAT:
            if name not in AW_INDEX:
                return {"ok": False, "err": f"khối tương thích không có lệnh: {name}"}
            addr, kind = AW_INDEX[name]
        else:
            addr = W_BASE + W_INDEX[name]
            kind = AW_INDEX[name][1] if name in AW_INDEX else "level"

        # APP LÀ BÊN RA LỆNH → chính lệnh này định mốc mẻ, không chờ máy báo lại.
        # Bật PC control thì reg 14/15 thành ô LỆNH, không còn phản chiếu nút HMI,
        # nên bộ suy diễn không có cách nào tự biết mẻ đã bắt đầu/kết thúc.
        if name in ("charge", "drop") and v:
            bt = (self._snap or {}).get("bt", 0.0)
            (self._deriver.charge if name == "charge" else self._deriver.drop)(bt)

        with self._lock:
            self._pending.append((addr, [v]))
        self._kick.set()                    # dậy ngay — trước đây lệnh nằm đợi tới 0.5s
        return {"ok": True, "name": name, "value": v, "reg": addr, "kind": kind,
                "mode": self._mode}

    def cfg_op(self, cmd: int, idx: int, val: int = 0, timeout: float = 2.5) -> dict:
        """Handshake cấu hình $M: cmd 1=đọc / 2=ghi tham số $M số `idx` (1..MAXIDX).
        CHẶN tới khi luồng _run xử xong (nó sở hữu cổng serial). Chỉ chạy được ở
        chế độ PC_Link. Trả {ok, val, status} hoặc {ok:False, err}."""
        if self._mode != MODE_PCLINK:
            return {"ok": False, "err": "máy chưa nạp PC_Link (khối tương thích không có khối config)"}
        if not (1 <= int(idx) <= CFG_MAXIDX):
            return {"ok": False, "err": f"idx $M ngoài khoảng 1..{CFG_MAXIDX}"}
        with self._cfg_gate:                       # 1 handshake tại 1 thời điểm
            self._cfg_done.clear()
            self._cfg_res = None
            self._cfg_req = (int(cmd), int(idx), int(val) & 0xFFFF)
            self._kick.set()                       # đánh thức _run xử ngay
            if not self._cfg_done.wait(timeout):
                self._cfg_req = None
                return {"ok": False, "err": "máy không phản hồi handshake $M (timeout)"}
            return self._cfg_res or {"ok": False, "err": "không có kết quả"}

    def _do_cfg(self, cmd: int, idx: int, val: int):
        """Thực thi 1 handshake trong luồng _run (đang giữ cổng serial).
        Ghi [cmd,idx,val,status=0] xuống khối CFG rồi poll tới khi firmware set
        CMD về 0 (báo xong), đọc STATUS/VAL. Không ngủ quá vài trăm ms."""
        try:
            self.write_regs(CFG_BASE, [cmd & 0xFFFF, idx & 0xFFFF, val & 0xFFFF, 0])
            deadline = time.time() + 1.5
            while time.time() < deadline:
                time.sleep(0.03)                   # cho firmware 1-2 vòng loop (~141ms)
                regs = self.read_regs(CFG_BASE, 4)  # [cmd, idx, val, status]
                if regs[0] == CFG_CMD["idle"]:      # firmware đã xử xong
                    ok = regs[3] == CFG_STATUS["ok"]
                    self._cfg_res = {"ok": ok, "val": regs[2], "status": regs[3],
                                     "err": "" if ok else "máy từ chối (idx sai / đang rang)"}
                    return
            self._cfg_res = {"ok": False, "err": "firmware không set CMD về 0 (treo handshake)"}
        except Exception as e:
            self._cfg_res = {"ok": False, "err": str(e)}

    def new_batch(self):
        """Mẻ mới — xoá đồng hồ và mốc của bộ suy diễn."""
        self._deriver.reset()
        self._last_charge = 0
        return {"ok": True}

    def begin_batch(self):
        """Thợ bấm Bắt đầu rang: mở đồng hồ + chấm mốc từ giây này.

        Tách khỏi write('charge') vì hai việc khác nhau — 'charge' là LỆNH mở cửa
        nạp xuống máy, còn đây là mốc thời gian của mẻ trên app.
        """
        self._deriver.reset()
        self._last_charge = 0
        self._deriver.charge((self._snap or {}).get("bt", 0.0))
        return {"ok": True, "t_roast": self._deriver.t_roast}

    # ── lõi ─────────────────────────────────────────────────────────────────
    def _close(self):
        if self._ser:
            try:
                self._ser.close()
            except Exception:
                pass
        self._ser = None

    def _open(self) -> bool:
        self._close()
        try:
            self._ser = serial.Serial(
                port=self.cfg["port"], baudrate=int(self.cfg["baud"]),
                bytesize=8, parity="N", stopbits=1, timeout=0.6, write_timeout=0.6,
            )
            time.sleep(0.15)                 # PL2303/FT232 cần chút thời gian ổn định
            self._ser.reset_input_buffer()
            self._sg_bt.reset()              # quá khứ trước lúc đứt cáp hết ý nghĩa —
            self._sg_et.reset()              #   không được so spike với số cũ cả phút trước
            return True
        except Exception as e:
            self._set_state("error", str(e))
            self._close()
            return False

    def _set_state(self, state: str, err: str = ""):
        with self._lock:
            self._state = state
            self._err = err

    def _txn(self, req: bytes, expect_len: int) -> bytes:
        """Gửi 1 khung, chờ trả lời. Đọc header trước để bắt được khung ngoại lệ
        (chỉ 5 byte) thay vì chết vì 'thiếu byte'."""
        ser = self._ser
        ser.reset_input_buffer()
        ser.write(req + crc16(req))
        head = ser.read(2)
        if len(head) < 2:
            raise ModbusError("máy không trả lời")
        if head[0] != int(self.cfg["slave"]):
            raise ModbusError(f"sai slave id (nhận {head[0]})")
        if head[1] & 0x80:                       # khung ngoại lệ: +code +crc(2)
            tail = ser.read(3)
            code = tail[0] if tail else 0
            raise ModbusError(f"máy từ chối, code {code} "
                              f"({MB_EXC.get(code, 'không rõ')})")
        rsp = head + ser.read(expect_len - 2)
        if len(rsp) < expect_len:
            raise ModbusError(f"thiếu byte ({len(rsp)}/{expect_len})")
        if crc16(rsp[:-2]) != rsp[-2:]:
            raise ModbusError("CRC sai")
        return rsp

    def read_regs(self, addr: int, count: int) -> list[int]:
        sid = int(self.cfg["slave"])
        req = bytes((sid, 0x03, addr >> 8, addr & 0xFF, count >> 8, count & 0xFF))
        rsp = self._txn(req, 5 + 2 * count)     # id+func+len + data + crc(2)
        n = rsp[2]
        if n != 2 * count:
            raise ModbusError("độ dài trả về sai")
        body = rsp[3:3 + n]
        return [_u16(body[i], body[i + 1]) for i in range(0, n, 2)]

    def write_regs(self, addr: int, values: list[int]) -> None:
        sid = int(self.cfg["slave"])
        n = len(values)
        payload = bytearray((sid, 0x10, addr >> 8, addr & 0xFF, n >> 8, n & 0xFF, 2 * n))
        for v in values:
            v &= 0xFFFF
            payload += bytes((v >> 8, v & 0xFF))
        self._txn(bytes(payload), 8)            # id+func+addr(2)+qty(2)+crc(2)

    def _decode(self, r: list[int]) -> dict:
        """Quy đổi do bản đồ dùng chung lo (pc_link_map.decode)."""
        return decode(r)

    def _sanity(self, snap: dict, roasting: bool) -> dict:
        """Sensor sanity §16.9: BT/ET đi qua SensorGuard, cắm snap['sens_warn']
        = {'bt':'spike',...} hoặc None. Ngưỡng DROP tự xả ăn theo BT nên số rác
        1 khung cũng đủ xả nhầm nguyên mẻ — phải chặn ở đây, tầng thấp nhất."""
        now = time.time()
        warns = {}
        for key, sg in (("bt", self._sg_bt), ("et", self._sg_et)):
            v, w = sg.feed(snap.get(key), now, roasting)
            snap[key] = v
            if w:
                warns[key] = w
        snap["sens_warn"] = warns or None
        return snap

    def _read_pclink(self) -> dict:
        """Đọc khối PC_Link, TỰ LÙI số ô khi máy chạy firmware cũ (ít register hơn).

        Firmware cũ chỉ có 16 ô (100-115); bản mới thêm prof_pct/prof_ok/prof_sel/
        scale. Đọc quá số ô máy có → exception Modbus mỗi vòng, app tưởng đứt cáp.
        Gặp lỗi 1 lần thì rút về 16 ô; các trường thiếu trả None để app biết
        'máy chưa có tính năng này' (khác hẳn số 0)."""
        try:
            regs = self.read_regs(R_BASE, self._r_count)
        except ModbusError:
            if self._r_count <= 16:
                raise
            self._r_count = 16              # firmware cũ — dùng khối gốc
            regs = self.read_regs(R_BASE, 16)
        if len(regs) < R_COUNT:
            snap = decode(regs + [0] * (R_COUNT - len(regs)))
            for k in ("prof_pct", "prof_ok", "prof_sel", "scale", "ror_kg", "scale_tg"):
                if k in snap:
                    snap[k] = None          # máy chưa có ô này
        else:
            snap = decode(regs)
        return snap

    # ── Dò khả năng máy: có PC_Link hay chỉ có khối tương thích ─────────────
    def _probe(self) -> str:
        self._r_count = R_COUNT             # máy mới cắm vào — thử full trước, lùi sau
        try:
            self.read_regs(R_BASE, 1)
            return MODE_PCLINK
        except ModbusError:
            self.read_regs(A_BASE, 1)      # còn lỗi nữa thì để _run bắt
            return MODE_COMPAT

    def _poll_compat(self) -> dict:
        """Đọc khối tương thích rồi TỰ TÍNH phần firmware vốn lo.

        Mốc CHARGE/DROP: ưu tiên nút thật của HMI (reg 14/15 — chỉ phản chiếu khi
        PC control TẮT); nếu không thấy thì dựa vào cạnh lên của cờ AUTO (reg 17,
        luôn phản chiếu). App tự lái thì gọi thẳng deriver.charge()/drop().
        """
        raw = decode_artisan(self.read_regs(A_BASE, A_COUNT))
        d = self._deriver
        # lọc rác TRƯỚC khi deriver ăn — RoR/mốc không được tính trên số nhiễu
        raw = self._sanity(raw, d.charged and not d.dropped)
        d.feed(raw["bt"], raw["et"])

        started = bool(raw.get("charge")) or bool(raw.get("auto"))
        if started and not d.charged:
            d.charge(raw["bt"])
        elif d.charged and not d.dropped and (raw.get("drop") or
                                              (self._last_charge and not started)):
            d.drop(raw["bt"])
        self._last_charge = 1 if started else 0
        snap = d.snapshot(raw)
        snap["sens_warn"] = raw.get("sens_warn")   # d.snapshot chỉ lấy ô nó biết
        return snap

    def _run(self):
        period = 1.0 / max(0.5, float(self.cfg.get("poll_hz", 8)))
        fails = 0
        while not self._stop.is_set():
            if not self.cfg.get("enabled", True) or not self.cfg.get("port"):
                # chưa chọn cổng → nằm im, KHÔNG dò bừa; giao diện sẽ hỏi thợ
                self._set_state("off", "" if self.cfg.get("port") else "chưa chọn cổng")
                self._close()
                self._stop.wait(1.0)
                continue
            if self._ser is None:
                self._set_state("connecting")
                if not self._open():
                    self._stop.wait(2.0)     # cổng chưa cắm → thử lại, KHÔNG bắt restart app
                    continue
            try:
                # lệnh ghi đi trước để nút bấm phản hồi nhanh
                with self._lock:
                    todo, self._pending = self._pending, []
                for addr, vals in todo:
                    self.write_regs(addr, vals)
                    time.sleep(0.01)

                if self._mode is None:
                    self._mode = self._probe()

                # Handshake cấu hình $M (nếu có yêu cầu) — luồng này sở hữu cổng serial
                if self._cfg_req is not None and self._mode == MODE_PCLINK:
                    c, i, v = self._cfg_req
                    self._cfg_req = None
                    self._do_cfg(c, i, v)
                    self._cfg_done.set()
                elif self._cfg_req is not None:
                    self._cfg_req = None
                    self._cfg_res = {"ok": False, "err": "máy chưa nạp PC_Link"}
                    self._cfg_done.set()

                # Heartbeat app → máy (chỉ khối PC_Link có ô này): nhấp MỖI CHU KỲ
                # poll để watchdog firmware biết app còn sống — thưa hơn là dễ rớt
                # oan khi trúng vài khung nhiễu liên tiếp (mỗi timeout 0.6s).
                if self._mode == MODE_PCLINK:
                    self._app_hb = (self._app_hb + 1) & 0x7FFF
                    self.write_regs(W_BASE + W_INDEX["hb"], [self._app_hb])

                if self._mode == MODE_PCLINK:
                    snap = self._read_pclink()
                    # "đang rang" theo progStep (t_roast có thể KHÔNG reset sau DROP
                    # — dựa vào nó là máy nằm im qua đêm cũng bị báo frozen oan)
                    roasting = STP["CHARGE"] <= (snap.get("step") or 0) < STP["DROP"]
                    snap = self._sanity(snap, roasting)
                else:
                    snap = self._poll_compat()   # sanity đã chạy bên trong (trước deriver)

                now = time.time()
                # heartbeat đứng yên = firmware treo / cáp còn nhưng máy không chạy.
                # Khối tương thích không có heartbeat → bỏ qua phép kiểm này.
                if self._mode == MODE_PCLINK:
                    if snap["hb"] != self._hb:
                        self._hb, self._hb_ts = snap["hb"], now
                    stalled = self._hb_ts and (now - self._hb_ts) > 3.0
                else:
                    stalled = False
                with self._lock:
                    self._snap, self._snap_ts = snap, now
                    self._state = "stalled" if stalled else "connected"
                    self._err = "heartbeat đứng yên" if stalled else ""
                with self._snap_cond:              # đánh thức kênh push (app + web SSE)
                    self._snap_gen += 1
                    self._snap_cond.notify_all()
                fails = 0
            except Exception as e:
                fails += 1
                self._set_state("error", str(e))
                if fails >= 3:               # rớt cáp/nhiễu → đóng, vòng sau mở lại
                    self._close()
                    self._mode = None        # máy có thể đã được nạp firmware mới
                    fails = 0
            # Ngủ hết chu kỳ HOẶC dậy sớm khi write() gõ chuông (lệnh mới cần phát ngay)
            if self._kick.wait(period):
                self._kick.clear()


# ── CLI kiểm tra tay ────────────────────────────────────────────────────────
def _cli():
    try:                                    # console Windows mặc định cp1252
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Kiểm tra cầu Modbus tới máy rang")
    ap.add_argument("--port", default=load_config()["port"])
    ap.add_argument("--baud", type=int, default=load_config()["baud"])
    ap.add_argument("--slave", type=int, default=load_config()["slave"])
    ap.add_argument("--scan", action="store_true", help="dò baud thông dụng")
    ap.add_argument("--ports", action="store_true", help="liệt kê cổng COM")
    ap.add_argument("--n", type=int, default=10, help="số nhịp in ra")
    a = ap.parse_args()

    if a.ports:
        for p in list_serial_ports():
            print(f"  {p['port']:<8} {p['desc']}")
        return

    bauds = [9600, 19200, 38400, 57600, 115200] if a.scan else [a.baud]
    link = None
    for b in bauds:
        link = RoasterLink({"port": a.port, "baud": b, "slave": a.slave, "enabled": True})
        if not link._open():
            print(f"[{b}] không mở được cổng: {link._err}")
            continue
        try:
            regs = link.read_regs(R_BASE, R_COUNT)
            print(f"[{b}] OK — reg thô: {regs}")
            break
        except Exception as e:
            print(f"[{b}] không đọc được: {e}")
            link._close()
            link = None
    if link is None or link._ser is None:
        print("→ Không bắt được máy. Kiểm tra cổng/baud/ID hoặc firmware đã nạp PC_Link chưa.")
        return

    print("\nĐọc live (Ctrl+C để dừng):")
    try:
        for _ in range(a.n):
            d = link._decode(link.read_regs(R_BASE, R_COUNT))
            f = "".join(k[0].upper() for k, v in d["flags"].items() if v) or "-"
            print(f"  BT {d['bt']:6.1f}  ET {d['et']:6.1f}  RoR {d['ror_bt']:+6.2f}"
                  f"  gas {d['gas']:3d}  air {d['air']:3d}  drum {d['drum']:3d}"
                  f"  SV {d['sv']:5.1f}  vac {d['vac']:5d}  step {d['step']:2d}"
                  f"  t {d['t_roast']:4d}s  hb {d['hb']:5d}  [{f}]")
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        link._close()


if __name__ == "__main__":
    _cli()
