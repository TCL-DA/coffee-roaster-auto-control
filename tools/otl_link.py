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
    A_BASE, A_COUNT, decode_artisan, AW_INDEX,
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
    "poll_hz": 2,
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
        self._thread: threading.Thread | None = None
        self._snap: dict | None = None      # gói dữ liệu mới nhất đã quy đổi
        self._snap_ts = 0.0
        self._state = "off"                 # off|connecting|connected|stalled|error
        self._err = ""
        self._hb = -1
        self._hb_ts = 0.0
        self._app_hb = 0                    # heartbeat CỦA APP gửi xuống máy (watchdog PC_Link)
        self._app_hb_ts = 0.0
        self._mode = None                   # dò lúc kết nối: MODE_PCLINK / MODE_COMPAT
        self._deriver = RoastDeriver()      # chỉ dùng ở chế độ tương thích
        self._last_charge = 0               # cạnh lên nút charge/drop của HMI

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
        return {"ok": True, "name": name, "value": v, "reg": addr, "kind": kind,
                "mode": self._mode}

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

    # ── Dò khả năng máy: có PC_Link hay chỉ có khối tương thích ─────────────
    def _probe(self) -> str:
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
        d.feed(raw["bt"], raw["et"])

        started = bool(raw.get("charge")) or bool(raw.get("auto"))
        if started and not d.charged:
            d.charge(raw["bt"])
        elif d.charged and not d.dropped and (raw.get("drop") or
                                              (self._last_charge and not started)):
            d.drop(raw["bt"])
        self._last_charge = 1 if started else 0
        return d.snapshot(raw)

    def _run(self):
        period = 1.0 / max(0.5, float(self.cfg.get("poll_hz", 2)))
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

                # Heartbeat app → máy (chỉ khối PC_Link có ô này): nhấp MỖI CHU KỲ
                # poll để watchdog firmware biết app còn sống — thưa hơn là dễ rớt
                # oan khi trúng vài khung nhiễu liên tiếp (mỗi timeout 0.6s).
                if self._mode == MODE_PCLINK:
                    self._app_hb = (self._app_hb + 1) & 0x7FFF
                    self.write_regs(W_BASE + W_INDEX["hb"], [self._app_hb])

                if self._mode == MODE_PCLINK:
                    snap = self._decode(self.read_regs(R_BASE, R_COUNT))
                else:
                    snap = self._poll_compat()

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
                fails = 0
            except Exception as e:
                fails += 1
                self._set_state("error", str(e))
                if fails >= 3:               # rớt cáp/nhiễu → đóng, vòng sau mở lại
                    self._close()
                    self._mode = None        # máy có thể đã được nạp firmware mới
                    fails = 0
            self._stop.wait(period)


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
