"""
Test lõi Modbus relay (tools/modbus_relay.py).

Phần tích hợp chạy qua SerialManager THẬT của OTL Serial Terminal — chỉ thay
serial.Serial bằng một cổng giả có gắn module Waveshare giả. Module giả chỉ
trả lời khi cổng đặt ĐÚNG baud + parity của nó (sai thì trả nhiễu), đổi địa
chỉ/UART SAU khi đã trả lời, và có thể hiểu mã parity theo bảng 2 của tài liệu.

Chạy: cd tools && python -m unittest test_modbus_relay
"""

import os
import sys
import threading
import time
import unittest

import serial

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import modbus_relay as mr  # noqa: E402
import otl_serial_terminal as app_module  # noqa: E402

PARITY_LETTER = {"None": serial.PARITY_NONE, "Even": serial.PARITY_EVEN, "Odd": serial.PARITY_ODD}
KHONG_FLOW = dict(rtscts=False, xonxoff=False, dsrdtr=False)


class ModuleGia:
    """Module relay Waveshare V3 giả — đủ các lệnh tool dùng tới."""

    def __init__(self, addr=1, baud=9600, parity="None", ma_parity=None, echo=False):
        self.addr, self.baud, self.parity = addr, baud, parity
        self.ma_parity = ma_parity or {0: "None", 1: "Even", 2: "Odd"}   # mã → parity thật
        self.coils = [False] * 8
        self.flash = []
        self.echo = echo            # bộ chuyển USB-485 dội lại lệnh gửi

    def _loi(self, addr, fc, code):
        return mr.with_crc(bytes((addr, fc | 0x80, code))), None

    def xu_ly(self, data):
        if len(data) < 4 or mr.crc16(data[:-2]) != data[-2:]:
            return b"", None
        addr, fc = data[0], data[1]
        if addr not in (0, self.addr):
            return b"", None
        a = int.from_bytes(data[2:4], "big")
        b = int.from_bytes(data[4:6], "big")
        if fc == 0x01:
            mask = sum(1 << i for i, on in enumerate(self.coils) if on)
            return mr.with_crc(bytes((addr, 0x01, 1, mask))), None
        if fc == 0x03:
            if a == mr.REG_ADDRESS:
                val = self.addr
            elif a == mr.REG_UART:
                code = next(c for c, p in self.ma_parity.items() if p == self.parity)
                val = (code << 8) | mr.BAUD_CODES[self.baud]
            elif a == mr.REG_VERSION:
                val = 300
            else:
                return self._loi(addr, fc, 0x02)
            return mr.with_crc(bytes((addr, 0x03, 2)) + val.to_bytes(2, "big")), None
        if fc == 0x05:
            if a < 8:
                self.coils[a] = {mr.ON: True, mr.OFF: False}.get(b, not self.coils[a])
            elif a == mr.COIL_ALL:
                self.coils = [{mr.ON: True, mr.OFF: False}.get(b, not c) for c in self.coils]
            elif a >> 8 in (0x02, 0x04):
                self.flash.append((a, b))
            else:
                return self._loi(addr, fc, 0x02)
            return bytes(data), None
        if fc == 0x06:
            if a == mr.REG_ADDRESS:
                return bytes(data), ("addr", b)
            if a == mr.REG_UART:
                return bytes(data), ("uart", b)
            return self._loi(addr, fc, 0x02)
        if fc == 0x0F:
            mask = data[7]
            self.coils = [bool(mask >> i & 1) for i in range(8)]
            return mr.with_crc(bytes(data[:6])), None
        return self._loi(addr, fc, 0x01)

    def ap_dung(self, pending):
        kind, value = pending
        if kind == "addr":
            self.addr = value
        else:
            self.baud = mr.CODE_BAUDS[value & 0xFF]
            self.parity = self.ma_parity[value >> 8]


class CongRelayGia:
    """Bề mặt pySerial SerialManager dùng + dây nối tới ModuleGia."""

    module = None

    def __init__(self, port, baudrate, bytesize, parity, stopbits,
                 timeout=None, write_timeout=None, **flow):
        self.port, self.baudrate, self.bytesize = port, baudrate, bytesize
        self.parity, self.stopbits = parity, stopbits
        self.xonxoff = flow.get("xonxoff", False)
        self.rtscts = flow.get("rtscts", False)
        self.dsrdtr = flow.get("dsrdtr", False)
        self.timeout, self.write_timeout = timeout, write_timeout
        self.dtr = self.rts = False
        self.cd = self.ri = self.dsr = self.cts = False
        self.is_open = True
        self._rx = bytearray()
        self._khoa = threading.Lock()

    @property
    def in_waiting(self):
        with self._khoa:
            return len(self._rx)

    def read(self, size=1):
        with self._khoa:
            if self._rx:
                khoi = bytes(self._rx[:size])
                del self._rx[:size]
                return khoi
        time.sleep(0.005)
        return b""

    def write(self, data):
        data = bytes(data)
        m = CongRelayGia.module
        with self._khoa:
            if m is not None and m.echo:
                self._rx += data
        if m is not None and self.baudrate == m.baud and self.parity == PARITY_LETTER[m.parity]:
            resp, pending = m.xu_ly(data)
            with self._khoa:
                self._rx += resp
            if pending:
                m.ap_dung(pending)
        elif m is not None:
            with self._khoa:
                self._rx += b"\xF0\x0F\xE1"      # sai tốc độ/parity → byte nhiễu
        return len(data)

    def close(self):
        self.is_open = False


def moi_to_hop():
    return [(b, p) for b in mr.BAUD_SCAN_ORDER for p in mr.PARITY_NAMES]


# ───────────────────────────── khung & tách khung ─────────────────────────────

class KhungTheoTaiLieu(unittest.TestCase):
    def test_khung_khop_tai_lieu_hang(self):
        h = bytes.fromhex
        self.assertEqual(mr.req_write_coil(1, 0, mr.ON), h("01 05 00 00 FF 00 8C 3A"))
        self.assertEqual(mr.req_write_coil(1, 3, mr.OFF), h("01 05 00 03 00 00 3D CA"))
        self.assertEqual(mr.req_write_coil(1, 2, mr.TOGGLE), h("01 05 00 02 55 00 53 5A"))
        self.assertEqual(mr.req_write_coil(1, mr.COIL_ALL, mr.TOGGLE), h("01 05 00 FF 55 00 C2 AA"))
        self.assertEqual(mr.req_read_coils(1), h("01 01 00 00 00 08 3D CC"))
        self.assertEqual(mr.req_write_coils(1, [True] * 8), h("01 0F 00 00 00 08 01 FF BE D5"))
        self.assertEqual(mr.req_write_coils(1, [True, True] + [False] * 6),
                         h("01 0F 00 00 00 08 01 03 BE 94"))
        self.assertEqual(mr.req_write_coil(1, mr.FLASH_ON_BASE + 1, 8), h("01 05 02 01 00 08 9C 74"))
        self.assertEqual(mr.req_write_register(1, mr.REG_UART, 5), h("01 06 20 00 00 05 42 09"))
        self.assertEqual(mr.req_write_register(0, mr.REG_ADDRESS, 3), h("00 06 40 00 00 03 DD DA"))
        self.assertEqual(mr.req_read_register(0, mr.REG_ADDRESS), h("00 03 40 00 00 01 90 1B"))
        self.assertEqual(mr.req_read_register(1, mr.REG_VERSION), h("01 03 80 00 00 01 AD CA"))

    def test_giai_ma_uart_va_phien_ban(self):
        self.assertEqual(mr.decode_uart(0x0003), (38400, "None"))
        self.assertEqual(mr.decode_uart(0x0105), (115200, "Even"))
        self.assertEqual(mr.version_text(0x012C), "V3.00")

    def test_tach_khung_bo_rac_va_byte_dem_sai(self):
        req = mr.req_read_register(7, mr.REG_VERSION)
        reply = bytes.fromhex("07 03 02 01 2C 30 09")
        # rác + một "khung" giả cùng địa chỉ/FC nhưng byte đếm sai
        buf = bytearray(b"\x00\xFF" + bytes.fromhex("07 03 80") + reply)
        frame, drop = mr.find_reply(buf, req)
        self.assertEqual(frame, reply)
        self.assertEqual(drop, 5)          # 00 FF + "07 03 80" đứng trước khung thật

    def test_tach_khung_cho_them_khi_chua_du(self):
        req = mr.req_read_coils(7)
        frame, drop = mr.find_reply(bytearray(bytes.fromhex("07 01 01")), req)
        self.assertIsNone(frame)
        self.assertEqual(drop, 0)

    def test_tach_khung_loi_ngoai_le(self):
        req = mr.req_read_register(7, 0x1234)
        reply = mr.with_crc(bytes((7, 0x83, 0x02)))
        frame, _ = mr.find_reply(bytearray(reply), req)
        self.assertEqual(frame, reply)


# ───────────────────────────── tích hợp qua SerialManager ─────────────────────────────

class NenRelay(unittest.TestCase):
    module_kwargs = {}

    def setUp(self):
        self._serial_that = serial.Serial
        serial.Serial = CongRelayGia
        self.module = ModuleGia(**self.module_kwargs)
        CongRelayGia.module = self.module
        self.baud = 9600
        self.sm = app_module.SerialManager(on_rx=lambda chunk: self.client.feed(chunk))
        self.client = mr.ModbusRtuClient(write=self.sm.write, gap_s=0.002)
        self.relay = mr.WaveshareRelay(self.client, lambda: self.baud, timeout_ms=60)
        self.sm.open("COM77", 9600, 8, serial.PARITY_NONE, serial.STOPBITS_ONE, KHONG_FLOW)
        self.client.begin()

    def tearDown(self):
        self.client.end()
        self.sm.close()
        serial.Serial = self._serial_that
        CongRelayGia.module = None

    def configure(self, baud, parity):
        self.sm.configure({"baudrate": baud, "bytesize": 8, "parity": parity.lower(),
                           "stopbits": 1, **KHONG_FLOW})
        self.baud = baud
        return True


class LenhRelay(NenRelay):
    module_kwargs = {"addr": 7}

    def test_bat_tat_dao_va_doc_trang_thai(self):
        self.relay.write_channel(7, 0, mr.ON)
        self.relay.write_channel(7, 2, mr.TOGGLE)
        self.assertEqual(self.relay.read_coils(7), [True, False, True] + [False] * 5)
        self.relay.write_all(7, mr.TOGGLE)
        self.assertEqual(self.relay.read_coils(7), [False, True, False] + [True] * 5)
        self.relay.write_all(7, mr.OFF)
        self.assertEqual(self.relay.read_coils(7), [False] * 8)
        self.relay.write_mask(7, [True, False] * 4)
        self.assertEqual(self.module.coils, [True, False] * 4)

    def test_khung_sach_khong_bi_bao_rac(self):
        # Lỗi thật 15/09: find_reply trả vị trí CUỐI khung, transact hiểu là số byte
        # rác → mỗi trả lời bị in thêm một dòng "rác" và xoá lố sang khung sau.
        frames = []
        self.client.on_frame = lambda kind, data, note: frames.append(kind)
        self.relay.write_channel(7, 0, mr.ON)
        self.assertEqual(self.relay.read_coils(7)[0], True)
        self.assertEqual(frames, ["tx", "rx", "tx", "rx"])

    def test_nhap_nhay_gui_dung_thanh_ghi(self):
        self.relay.flash(7, 1, True, 7)
        self.relay.flash(7, 0, False, 5)
        self.assertEqual(self.module.flash, [(0x0201, 7), (0x0400, 5)])

    def test_doc_cau_hinh(self):
        self.module.baud = 9600
        cfg = self.relay.read_config(7)
        self.assertEqual((cfg["address"], cfg["baud"], cfg["parity"], cfg["version"]),
                         (7, 9600, "None", "V3.00"))

    def test_loi_ngoai_le_va_sai_id(self):
        with self.assertRaises(mr.ModbusExceptionReply) as ctx:
            self.relay.read_register(7, 0x1234)
        self.assertEqual(ctx.exception.exc_code, 0x02)
        with self.assertRaises(mr.ModbusTimeout):
            self.relay.read_coils(9)

    def test_ngoai_phien_byte_tra_ve_terminal(self):
        self.client.end()
        self.assertFalse(self.client.feed(b"OTL ready\n"))
        self.client.begin()
        self.assertTrue(self.client.feed(b"x"))


class BoChuyenDoiLai(NenRelay):
    module_kwargs = {"addr": 7, "echo": True}

    def test_tieng_doi_khong_bien_thanh_ok_gia(self):
        self.assertEqual(self.relay.read_coils(7), [False] * 8)
        self.assertTrue(self.client.echo_seen)
        self.relay.write_channel(7, 0, mr.ON)          # module thật trả lời → vẫn OK
        self.assertTrue(self.module.coils[0])
        with self.assertRaises(mr.ModbusTimeout):      # ID vắng mặt: chỉ có tiếng dội
            self.relay.write_channel(9, 0, mr.ON)


class DoTimThietBi(NenRelay):
    module_kwargs = {"addr": 7, "baud": 38400, "parity": "Even"}

    def test_do_nhanh_broadcast_thay_38400_even(self):
        logs = []
        found = mr.scan_combos(self.relay, self.configure, moi_to_hop(), on_log=logs.append)
        self.assertEqual(len(found), 1)
        item = found[0]
        self.assertEqual((item["kind"], item["address"], item["baud"], item["parity"]),
                         ("waveshare", 7, 38400, "Even"))
        self.assertEqual(item["version"], "V3.00")
        self.assertEqual(item["uart_raw"], 0x0103)

    def test_hoi_tung_id(self):
        found = mr.scan_combos(self.relay, self.configure, [(38400, "Even")], ids=range(1, 10))
        self.assertEqual([(f["kind"], f["address"]) for f in found], [("waveshare", 7)])

    def test_dung_giua_chung(self):
        self.relay.cancel = threading.Event()
        self.relay.cancel.set()
        with self.assertRaises(mr.ModbusCancelled):
            mr.scan_combos(self.relay, self.configure, moi_to_hop())


class GhiCauHinh(NenRelay):
    module_kwargs = {"addr": 1, "baud": 9600, "parity": "None"}

    def test_doi_dia_chi_va_toc_do_roi_xac_nhan(self):
        result = mr.write_config(self.relay, self.configure,
                                 {"address": 1, "baud": 9600, "parity": "None"},
                                 {"address": 7, "baud": 38400, "parity": "None"})
        self.assertEqual((self.module.addr, self.module.baud, self.module.parity), (7, 38400, "None"))
        self.assertEqual(result, {"address": 7, "baud": 38400, "parity": "None", "parity_swapped": False})
        self.assertEqual(self.relay.read_address(7), 7)

    def test_broadcast_doi_dia_chi(self):
        mr.write_config(self.relay, self.configure,
                        {"address": 99, "baud": 9600, "parity": "None"},
                        {"address": 5, "baud": 9600, "parity": "None"}, broadcast=True)
        self.assertEqual(self.module.addr, 5)


class ParityNguocTaiLieu(NenRelay):
    module_kwargs = {"addr": 7, "baud": 9600, "parity": "None",
                     "ma_parity": {0: "None", 1: "Odd", 2: "Even"}}

    def test_tu_phat_hien_va_ghi_lai_cho_dung(self):
        logs = []
        result = mr.write_config(self.relay, self.configure,
                                 {"address": 7, "baud": 9600, "parity": "None"},
                                 {"address": 7, "baud": 9600, "parity": "Even"}, on_log=logs.append)
        self.assertEqual(self.module.parity, "Even")
        self.assertTrue(result["parity_swapped"])
        self.assertEqual(self.relay.parity_codes["Even"], 2)
        self.assertTrue(any("NGƯỢC" in line for line in logs))


if __name__ == "__main__":
    unittest.main()
