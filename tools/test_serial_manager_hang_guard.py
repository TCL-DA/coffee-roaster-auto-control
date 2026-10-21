"""Kiểm SerialManager.open()/write() không treo vô hạn khi driver không phản hồi.

Không đụng COM thật — cổng giả tự treo trong __init__/write() cho tới khi test
tự mở khoá bằng threading.Event, để đo đúng lúc open()/write() phải trả lỗi
(bounded) thay vì chờ tới khi driver xong (unbounded). Chạy trực tiếp
SerialManager, không qua App/HTTP, vì đây là hành vi tầng thấp nhất.
"""

import threading
import time
import unittest

import serial

import otl_serial_terminal as app_module


class CongTreoMo:
    """Cổng giả treo NGAY TRONG constructor — mô phỏng driver mở cổng ảo (vd.
    Bluetooth SPP) không bắt tay xong, hoặc không bao giờ xong."""

    cho_mo = None   # threading.Event dùng chung; None = mở ngay, không treo
    da_tao = []

    def __init__(self, port, baudrate, bytesize, parity, stopbits,
                 timeout=None, write_timeout=None, **flow):
        if CongTreoMo.cho_mo is not None:
            CongTreoMo.cho_mo.wait()
        self.port = port
        self.is_open = True
        self.so_lan_dong = 0
        CongTreoMo.da_tao.append(self)

    def close(self):
        self.is_open = False
        self.so_lan_dong += 1

    def read(self, size=1):
        time.sleep(0.01)
        return b""

    def write(self, data):
        return len(data)


class CongTreoGhi:
    """Mở ngay, nhưng write() treo tới khi test mở khoá — mô phỏng driver/
    thiết bị không rút được byte ra khỏi bộ đệm ghi."""

    cho_ghi = None
    da_tao = []

    def __init__(self, port, baudrate, bytesize, parity, stopbits,
                 timeout=None, write_timeout=None, **flow):
        self.port = port
        self.is_open = True
        self.so_lan_ghi = 0
        CongTreoGhi.da_tao.append(self)

    def close(self):
        self.is_open = False

    def read(self, size=1):
        time.sleep(0.01)
        return b""

    def write(self, data):
        self.so_lan_ghi += 1
        if CongTreoGhi.cho_ghi is not None:
            CongTreoGhi.cho_ghi.wait()
        return len(data)


FLOW = {"xonxoff": False, "rtscts": False, "dsrdtr": False}


class MoCongTreoBiChanTran(unittest.TestCase):
    def setUp(self):
        self._serial_that = serial.Serial
        serial.Serial = CongTreoMo
        CongTreoMo.cho_mo = threading.Event()
        CongTreoMo.da_tao.clear()
        self.sm = app_module.SerialManager()

    def tearDown(self):
        CongTreoMo.cho_mo.set()   # nhả driver treo để reaper thread thoát sạch
        time.sleep(0.05)
        serial.Serial = self._serial_that

    def test_mo_cong_treo_vo_han_van_tra_loi_dung_han(self):
        bat_dau = time.monotonic()
        with self.assertRaises(serial.SerialException):
            self.sm.open("COM50", 9600, serial.EIGHTBITS, serial.PARITY_NONE,
                         serial.STOPBITS_ONE, FLOW, open_timeout=0.15)
        troi_qua = time.monotonic() - bat_dau
        self.assertLess(troi_qua, 1.0, "phải trả lỗi trong vòng open_timeout, không chờ driver")
        self.assertFalse(self.sm.is_open())

    def test_khong_cho_mo_cong_thu_hai_khi_cong_treo_cu_chua_xong(self):
        with self.assertRaises(serial.SerialException):
            self.sm.open("COM50", 9600, serial.EIGHTBITS, serial.PARITY_NONE,
                         serial.STOPBITS_ONE, FLOW, open_timeout=0.1)
        with self.assertRaises(serial.SerialException) as ctx:
            self.sm.open("COM51", 9600, serial.EIGHTBITS, serial.PARITY_NONE,
                         serial.STOPBITS_ONE, FLOW, open_timeout=0.1)
        self.assertIn("chưa xong", str(ctx.exception))

    def test_driver_mo_xong_muon_bi_tu_dong_dong_lai(self):
        with self.assertRaises(serial.SerialException):
            self.sm.open("COM50", 9600, serial.EIGHTBITS, serial.PARITY_NONE,
                         serial.STOPBITS_ONE, FLOW, open_timeout=0.1)
        CongTreoMo.cho_mo.set()      # driver "xong muộn"
        han = time.monotonic() + 2
        while time.monotonic() < han and not CongTreoMo.da_tao:
            time.sleep(0.02)
        self.assertEqual(len(CongTreoMo.da_tao), 1)
        han = time.monotonic() + 2
        while time.monotonic() < han and CongTreoMo.da_tao[0].so_lan_dong == 0:
            time.sleep(0.02)
        self.assertEqual(CongTreoMo.da_tao[0].so_lan_dong, 1,
                         "cổng mở muộn phải bị đóng hộ, không được chiếm mãi")

    def test_mo_lai_binh_thuong_sau_khi_co_treo_cu_da_don_xong(self):
        with self.assertRaises(serial.SerialException):
            self.sm.open("COM50", 9600, serial.EIGHTBITS, serial.PARITY_NONE,
                         serial.STOPBITS_ONE, FLOW, open_timeout=0.1)
        CongTreoMo.cho_mo.set()
        han = time.monotonic() + 2
        while time.monotonic() < han and self.sm._opening:
            time.sleep(0.02)
        self.assertFalse(self.sm._opening, "cờ phải tự nhả sau khi luồng treo cũ xong")
        self.sm.open("COM52", 9600, serial.EIGHTBITS, serial.PARITY_NONE,
                     serial.STOPBITS_ONE, FLOW, open_timeout=1.0)
        self.assertTrue(self.sm.is_open())
        self.sm.close()


class GhiTreoBiChanTran(unittest.TestCase):
    def setUp(self):
        self._serial_that = serial.Serial
        serial.Serial = CongTreoGhi
        CongTreoGhi.cho_ghi = threading.Event()
        CongTreoGhi.da_tao.clear()
        self.sm = app_module.SerialManager()
        self.sm.open("COM60", 9600, serial.EIGHTBITS, serial.PARITY_NONE,
                    serial.STOPBITS_ONE, FLOW, open_timeout=1.0)

    def tearDown(self):
        CongTreoGhi.cho_ghi.set()
        time.sleep(0.05)
        self.sm.close()
        serial.Serial = self._serial_that

    def test_ghi_treo_van_tra_loi_dung_han(self):
        bat_dau = time.monotonic()
        with self.assertRaises(serial.SerialException):
            self.sm.write(b"ping", write_guard_seconds=0.15)
        troi_qua = time.monotonic() - bat_dau
        self.assertLess(troi_qua, 1.0, "phải trả lỗi trong vòng write_guard_seconds")

    def test_khong_cho_ghi_lenh_moi_khi_lenh_cu_con_treo(self):
        with self.assertRaises(serial.SerialException):
            self.sm.write(b"ping", write_guard_seconds=0.1)
        with self.assertRaises(serial.SerialException) as ctx:
            self.sm.write(b"pong", write_guard_seconds=0.1)
        self.assertIn("chưa xong", str(ctx.exception))
        # Chỉ có ĐÚNG MỘT lệnh ghi thật sự chạm cổng — lệnh thứ hai bị chặn ở
        # cờ _writing, không rơi luôn hai chuỗi byte vào cùng một cổng.
        self.assertEqual(CongTreoGhi.da_tao[-1].so_lan_ghi, 1)

    def test_ghi_lai_binh_thuong_sau_khi_lenh_treo_cu_da_xong(self):
        with self.assertRaises(serial.SerialException):
            self.sm.write(b"ping", write_guard_seconds=0.1)
        CongTreoGhi.cho_ghi.set()
        han = time.monotonic() + 2
        while time.monotonic() < han and self.sm._writing:
            time.sleep(0.02)
        self.assertFalse(self.sm._writing, "cờ phải tự nhả sau khi lệnh ghi treo cũ xong")
        written = self.sm.write(b"pong", write_guard_seconds=1.0)
        self.assertEqual(written, 4)


if __name__ == "__main__":
    unittest.main()
