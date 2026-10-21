"""Kiểm luồng ĐIỀU KHIỂN của Serial Terminal bằng serial giả, không đụng COM thật.

Bộ test cũ (``test_serial_terminal_api.py``) chỉ phủ đường ĐỌC. File này phủ nốt
các tiêu chí nghiệm thu trong docs/plan/2026-09-10-serial-terminal-automation.md:
quét cổng, cấu hình, mở/đóng, TX, ranh giới bộ đệm, xác thực và hàng đợi lệnh.

Điểm quan trọng: test chạy CHÍNH ``App._execute_api_command`` của ứng dụng — chỗ
duy nhất quyết định ngữ nghĩa mở/gửi/đóng — chỉ thay Tk bằng widget giả và thay
``serial.Serial`` bằng cổng giả. Không chép lại logic của app vào test, vì bản
chép sẽ vẫn xanh khi app thật hỏng.
"""

import json
import os
import subprocess
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request

THU_MUC_TOOLS = os.path.dirname(os.path.abspath(__file__))
if THU_MUC_TOOLS not in sys.path:
    sys.path.insert(0, THU_MUC_TOOLS)

TOKEN_TEST = "kiem-thu-serial-terminal-token-du-dai"
os.environ["OTL_SERIAL_API_TOKEN"] = TOKEN_TEST

import serial                                        # noqa: E402
import serial.tools.list_ports                       # noqa: E402

import otl_serial_terminal as app_module             # noqa: E402
from serial_terminal_bridge import SerialDataBridge  # noqa: E402


# ───────────────────────────── cổng serial giả ─────────────────────────────

class CongGia:
    """Bề mặt pySerial mà SerialManager thật sự dùng tới."""

    da_tao = []
    tre_mo = 0.0        # giả lập driver mở cổng chậm

    def __init__(self, port, baudrate, bytesize, parity, stopbits,
                 timeout=None, write_timeout=None, **flow):
        if CongGia.tre_mo:
            time.sleep(CongGia.tre_mo)
        self.port, self.baudrate, self.bytesize = port, baudrate, bytesize
        self.parity, self.stopbits = parity, stopbits
        self.xonxoff = flow.get("xonxoff", False)
        self.rtscts = flow.get("rtscts", False)
        self.dsrdtr = flow.get("dsrdtr", False)
        self.timeout, self.write_timeout = timeout, write_timeout
        self.dtr = self.rts = False
        self.cd = self.ri = self.dsr = self.cts = False
        self.is_open = True
        self.da_ghi = bytearray()
        self.so_lan_ghi = 0
        self.ghi_thieu = None      # None = ghi đủ; số = chỉ ghi được ngần ấy byte
        self.loi_ghi = None        # exception ném ra khi ghi
        self._rx = bytearray()
        self._khoa = threading.Lock()
        CongGia.da_tao.append(self)

    def nap_rx(self, data):
        with self._khoa:
            self._rx += data

    def read(self, size=1):
        with self._khoa:
            if self._rx:
                khoi = bytes(self._rx[:size])
                del self._rx[:size]
                return khoi
        time.sleep(0.01)           # thay cho timeout đọc thật, tránh quay CPU
        return b""

    def write(self, data):
        self.so_lan_ghi += 1
        if self.loi_ghi is not None:
            raise self.loi_ghi
        n = len(data) if self.ghi_thieu is None else self.ghi_thieu
        self.da_ghi += bytes(data[:n])
        return n

    def close(self):
        self.is_open = False


class CongHeDieuHanh:
    """Bản ghi cổng giả cho serial.tools.list_ports.comports()."""

    def __init__(self, device, description):
        self.device, self.description, self.name = device, description, device
        self.hwid = "USB VID:PID=1234:5678"
        self.vid, self.pid = 0x1234, 0x5678
        self.serial_number = "SN-" + device
        self.location = self.manufacturer = self.product = self.interface = None


CONG_GIA = [CongHeDieuHanh("COM90", "Cong gia A"), CongHeDieuHanh("COM91", "Cong gia B")]


# ───────────────────────────── widget Tk giả ─────────────────────────────

class Bien:
    def __init__(self, value=None):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value

    def configure(self, **_kwargs):
        pass


class WidgetGia:
    def configure(self, **_kwargs):
        pass


class AppGia:
    """Vỏ tối thiểu để chạy các phương thức THẬT của App ngoài vòng đời Tk."""

    _execute_api_command = app_module.App._execute_api_command
    # App khai báo đây là staticmethod; gán trần sẽ biến nó thành method và nuốt self.
    _check_command_deadline = staticmethod(app_module.App._check_command_deadline)
    _selected_api_settings = app_module.App._selected_api_settings
    _apply_api_selection = app_module.App._apply_api_selection
    _sync_api_selected = app_module.App._sync_api_selected
    refresh_ports = app_module.App.refresh_ports
    selected_port = app_module.App.selected_port
    close_port = app_module.App.close_port

    def __init__(self, bridge):
        self.api = bridge
        self.sm = app_module.SerialManager(on_rx=lambda chunk: bridge.record("rx", chunk))
        self.opt_port = Bien("COM90")
        self.opt_baud = Bien("9600")
        self.opt_data = Bien("8")
        self.opt_parity = Bien("None")
        self.opt_stop = Bien("1")
        self.opt_handshake = Bien("None")
        self.dtr_var, self.rts_var = Bien(False), Bien(False)
        self.echo_on = Bien(False)
        self.btn_open, self.pill_dot, self.pill_txt = WidgetGia(), WidgetGia(), WidgetGia()
        self.lbl_status, self.info_box = WidgetGia(), WidgetGia()
        self.modem_lbls = {}
        self.port_map = {}
        self.nhat_ky = []
        self.refresh_ports()

    # Các mảnh thuần giao diện — không ảnh hưởng ngữ nghĩa cổng.
    def _show_port_info(self):
        pass

    def _set_pill(self, _connected):
        pass

    def _set_status(self, _text):
        pass

    def _append_log(self, text, tag):
        self.nhat_ky.append((tag, text))


# ───────────────────────────── nền test ─────────────────────────────

class NenDieuKhien(unittest.TestCase):
    def setUp(self):
        CongGia.da_tao.clear()
        CongGia.tre_mo = 0.0
        self._serial_that = serial.Serial
        self._comports_that = serial.tools.list_ports.comports
        serial.Serial = CongGia
        serial.tools.list_ports.comports = lambda: list(CONG_GIA)

        self.bridge = SerialDataBridge(port=0, token=TOKEN_TEST,
                                       port_provider=app_module.SerialManager.port_metadata)
        self.bridge.start()
        self.base = "http://127.0.0.1:%d" % self.bridge.port
        self.app = AppGia(self.bridge)

        self.tre_xu_ly = 0.0
        self._chay = True
        self._bom = threading.Thread(target=self._vong_tk, name="tk-gia", daemon=True)
        self._bom.start()

    def tearDown(self):
        self._chay = False
        self._bom.join(timeout=5)
        self.app.sm.close()
        self.bridge.stop()
        serial.Serial = self._serial_that
        serial.tools.list_ports.comports = self._comports_that

    def _vong_tk(self):
        """Thay cho vòng lặp Tk: rút lệnh khỏi hàng đợi và thực thi."""
        def handler(name, payload, deadline):
            if self.tre_xu_ly:
                time.sleep(self.tre_xu_ly)
            return self.app._execute_api_command(name, payload, deadline)

        while self._chay:
            if not self.bridge.process_commands(handler):
                time.sleep(0.005)

    # ── tiện ích HTTP ──
    def _goi(self, method, path, body=None, token=TOKEN_TEST, headers=None):
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(self.base + path, data=data, method=method)
        if data is not None:
            request.add_header("Content-Type", "application/json")
        if token:
            request.add_header("Authorization", "Bearer " + token)
        for key, value in (headers or {}).items():
            request.add_header(key, value)
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8")
            return exc.code, json.loads(raw) if raw else {}

    def post(self, path, body=None, **kwargs):
        return self._goi("POST", path, body if body is not None else {}, **kwargs)

    def get(self, path, **kwargs):
        return self._goi("GET", path, None, **kwargs)

    def mo_cong(self, port="COM90", **settings):
        cau_hinh = {"baudrate": 9600, "bytesize": 8, "parity": "none", "stopbits": 1,
                    "xonxoff": False, "rtscts": False, "dsrdtr": False}
        cau_hinh.update(settings)
        return self.post("/api/v1/connect", {"port": port, "settings": cau_hinh,
                                             "timeout_seconds": 5.0})


# ───────────────────────────── mở · gửi · đóng ─────────────────────────────

class MoGuiDong(NenDieuKhien):
    def test_quet_cong_khong_mo_cong(self):
        status, body = self.get("/api/v1/ports")
        self.assertEqual(status, 200)
        self.assertEqual([row["device"] for row in body["ports"]], ["COM90", "COM91"])
        self.assertEqual(body["ports"][0]["serial_number"], "SN-COM90")
        self.assertEqual(CongGia.da_tao, [], "quét cổng không được mở cổng")

    def test_vong_doi_mo_gui_dong(self):
        status, body = self.mo_cong()
        self.assertEqual(status, 200, body)
        self.assertTrue(body["connected"])
        self.assertEqual(body["port"], "COM90")
        cong = CongGia.da_tao[-1]

        # RX từ thiết bị phải chảy vào bộ đệm API.
        cong.nap_rx(b"preCool_R=1\r\n")
        status, data = self.get("/api/v1/events?after=0&direction=rx&wait=5")
        self.assertEqual(status, 200)
        self.assertIn("preCool_R=1", "".join(e["text"] for e in data["events"]))

        # TX đi ra đúng cổng và được ghi lại.
        status, body = self.post("/api/v1/send",
                                 {"encoding": "text", "data": "AT", "eol": "crlf"})
        self.assertEqual(status, 200, body)
        self.assertEqual(body, {"requested_bytes": 4, "written_bytes": 4, "complete": True})
        self.assertEqual(bytes(cong.da_ghi), b"AT\r\n")
        _, data = self.get("/api/v1/events?after=0&direction=tx")
        self.assertEqual(data["events"][-1]["hex"], "41 54 0D 0A")

        status, body = self.post("/api/v1/disconnect")
        self.assertEqual(status, 200, body)
        self.assertFalse(body["connected"])
        self.assertFalse(cong.is_open)
        _, st = self.get("/api/v1/status")
        self.assertFalse(st["connected"])
        self.assertIsNone(st["port"])

    def test_tx_nhi_phan_giu_nguyen_byte(self):
        self.mo_cong()
        cong = CongGia.da_tao[-1]
        self.post("/api/v1/send", {"encoding": "hex", "data": "00 01 FF 7F 0A"})
        self.assertEqual(bytes(cong.da_ghi), b"\x00\x01\xff\x7f\x0a")
        cong.da_ghi.clear()
        self.post("/api/v1/send", {"encoding": "base64", "data": "AAH/"})
        self.assertEqual(bytes(cong.da_ghi), b"\x00\x01\xff")

    def test_ghi_thieu_khong_bao_thanh_cong(self):
        self.mo_cong()
        cong = CongGia.da_tao[-1]
        cong.ghi_thieu = 2
        status, body = self.post("/api/v1/send", {"encoding": "text", "data": "ABCDE"})
        self.assertEqual(status, 409, body)
        self.assertEqual(body["error"], "partial_write")
        self.assertIn("2/5", body["message"])
        # Chỉ phần đã ghi được vào nhật ký TX, không ghi khống đủ 5 byte.
        _, data = self.get("/api/v1/events?after=0&direction=tx")
        thuc_te = b"".join(bytes.fromhex(e["hex"].replace(" ", "")) for e in data["events"])
        self.assertEqual(thuc_te, b"AB")

    def test_loi_ghi_khong_tu_gui_lai(self):
        self.mo_cong()
        cong = CongGia.da_tao[-1]
        cong.loi_ghi = serial.SerialTimeoutException("het gio ghi")
        status, body = self.post("/api/v1/send",
                                 {"encoding": "text", "data": "X", "timeout_seconds": 5.0})
        self.assertEqual(status, 409, body)
        self.assertEqual(body["error"], "write_failed")
        self.assertEqual(cong.so_lan_ghi, 1, "timeout ghi không được tự gửi lại")

    def test_gui_khi_chua_mo_bi_tu_choi(self):
        status, body = self.post("/api/v1/send", {"encoding": "text", "data": "X"})
        self.assertEqual(status, 409, body)
        self.assertEqual(body["error"], "not_connected")


# ───────────────────────────── macro send/expect/wait ──────────────────────

class MacroLenh(NenDieuKhien):
    def test_plan_khong_dung_toi_cong(self):
        status, body = self.post("/api/v1/macro/plan", {"steps": [
            {"type": "send", "data": "PING\n"},
            {"type": "expect", "data": "PONG", "timeout_ms": 500},
        ]})
        self.assertEqual(status, 200, body)
        self.assertEqual(body["step_count"], 2)
        self.assertEqual(body["steps"][0]["hex"], "50 49 4E 47 0A")
        self.assertEqual(CongGia.da_tao, [], "plan không được đụng tới cổng")

    def test_run_ghep_duoc_rx_ve_lam_hai_khoi(self):
        status, body = self.mo_cong()
        self.assertEqual(status, 200, body)
        cong = CongGia.da_tao[-1]

        def gia_lam_thiet_bi_tra_loi():
            han = time.monotonic() + 2
            while time.monotonic() < han and cong.so_lan_ghi == 0:
                time.sleep(0.01)
            cong.nap_rx(b"PO")     # cố ý chia làm hai khối để bắt lỗi ghép byte
            time.sleep(0.05)
            cong.nap_rx(b"NG\n")

        threading.Thread(target=gia_lam_thiet_bi_tra_loi, daemon=True).start()
        status, body = self.post("/api/v1/macro/run", {"steps": [
            {"type": "send", "data": "PING\n"},
            {"type": "expect", "data": "PONG", "timeout_ms": 2000},
        ]})
        self.assertEqual(status, 200, body)
        self.assertTrue(body["completed"], body)
        self.assertEqual(bytes(cong.da_ghi), b"PING\n")
        self.assertEqual(len(body["steps"]), 2)
        self.assertTrue(body["steps"][1]["ok"])

    def test_run_dung_ngay_khi_buoc_dau_that_bai(self):
        # Chưa mở cổng nên bước send đầu tiên fail — bước wait phía sau KHÔNG
        # được chạy, tránh macro cứ lao tiếp dù bước trước đã sai.
        status, body = self.post("/api/v1/macro/run", {"steps": [
            {"type": "send", "data": "PING\n"},
            {"type": "wait", "ms": 10},
        ]})
        self.assertEqual(status, 200, body)
        self.assertFalse(body["completed"])
        self.assertEqual(len(body["steps"]), 1)
        self.assertFalse(body["steps"][0]["ok"])

    def test_expect_khong_khop_bao_that_bai_dung_han(self):
        status, body = self.mo_cong()
        self.assertEqual(status, 200, body)
        bat_dau = time.monotonic()
        status, body = self.post("/api/v1/macro/run", {"steps": [
            {"type": "expect", "data": "PONG", "timeout_ms": 200},
        ]})
        troi_qua = time.monotonic() - bat_dau
        self.assertEqual(status, 200, body)
        self.assertFalse(body["steps"][0]["ok"])
        self.assertLess(troi_qua, 2.0)

    def test_qua_20_buoc_bi_tu_choi(self):
        steps = [{"type": "wait", "ms": 1}] * 21
        status, body = self.post("/api/v1/macro/plan", {"steps": steps})
        self.assertEqual(status, 400, body)
        self.assertEqual(body["error"], "invalid_request")


# ───────────────────────── một chủ sở hữu cổng ─────────────────────────

class MotChuSoHuu(NenDieuKhien):
    def test_khong_mo_hai_ket_noi_cung_luc(self):
        self.assertEqual(self.mo_cong()[0], 200)
        status, body = self.mo_cong()
        self.assertEqual(status, 409, body)
        self.assertEqual(body["error"], "already_connected")
        self.assertEqual(len(CongGia.da_tao), 1, "không được mở cổng lần hai")

    def test_doi_cong_khi_dang_ket_noi_bi_chan(self):
        self.mo_cong(port="COM90")
        status, body = self.post("/api/v1/configure",
                                 {"port": "COM91", "settings": {"baudrate": 19200}})
        self.assertEqual(status, 409, body)
        self.assertEqual(body["error"], "port_change_while_connected")
        _, st = self.get("/api/v1/status")
        self.assertEqual(st["port"], "COM90", "trạng thái không được báo sai tên cổng")
        self.assertEqual(CongGia.da_tao[-1].baudrate, 9600)

    def test_configure_khi_dang_mo_ap_thang_len_cong(self):
        self.mo_cong()
        status, body = self.post("/api/v1/configure", {"settings": {"baudrate": 57600}})
        self.assertEqual(status, 200, body)
        self.assertTrue(body["applied"])
        self.assertEqual(CongGia.da_tao[-1].baudrate, 57600)
        _, st = self.get("/api/v1/status")
        self.assertEqual(st["current"]["settings"]["baudrate"], 57600)

    def test_configure_khi_dong_chi_ghi_lua_chon(self):
        status, body = self.post("/api/v1/configure",
                                 {"port": "COM91", "settings": {"baudrate": 115200}})
        self.assertEqual(status, 200, body)
        self.assertFalse(body["applied"])
        self.assertEqual(CongGia.da_tao, [], "chưa mở cổng thì không được đụng thiết bị")
        _, st = self.get("/api/v1/status")
        self.assertEqual(st["selected"]["port"], "COM91")

    def test_cong_khong_ton_tai_bao_404(self):
        status, body = self.post("/api/v1/connect", {"port": "COM_KHONG_CO"})
        self.assertEqual(status, 404, body)
        self.assertEqual(body["error"], "port_not_found")


# ───────────────── tham số sai chặn trước khi đổi thiết bị ─────────────────

class ThamSoSai(NenDieuKhien):
    def test_baudrate_sai_bi_chan_truoc_khi_mo(self):
        for baud in (3, 0, "9600", True, 9_000_000):
            with self.subTest(baud=baud):
                status, body = self.post("/api/v1/connect",
                                         {"port": "COM90", "settings": {"baudrate": baud}})
                self.assertEqual(status, 400, body)
                self.assertEqual(body["error"], "invalid_request")
        self.assertEqual(CongGia.da_tao, [], "tham số sai không được chạm tới cổng")

    def test_truong_la_va_flow_xung_dot_bi_tu_choi(self):
        status, body = self.post("/api/v1/connect",
                                 {"port": "COM90", "settings": {"baudrate": 9600, "khac": 1}})
        self.assertEqual(status, 400, body)
        self.assertIn("khac", body["message"])
        status, body = self.post(
            "/api/v1/connect",
            {"port": "COM90", "settings": {"baudrate": 9600, "rtscts": True, "xonxoff": True}})
        self.assertEqual(status, 400, body)
        self.assertEqual(CongGia.da_tao, [])

    def test_tx_qua_lon_va_rong_bi_tu_choi(self):
        self.mo_cong()
        cong = CongGia.da_tao[-1]
        for payload in ({"encoding": "text", "data": ""},
                        {"encoding": "text", "data": "A" * 4097},
                        {"encoding": "hex", "data": "ABC"},
                        {"encoding": "base64", "data": "khong-phai-base64!"}):
            with self.subTest(encoding=payload.get("encoding")):
                status, body = self.post("/api/v1/send", payload)
                self.assertEqual(status, 400, body)
        self.assertEqual(cong.so_lan_ghi, 0, "dữ liệu sai không được chạm tới cổng")


# ───────────────────────────── xác thực ─────────────────────────────

class XacThuc(NenDieuKhien):
    def test_thieu_hoac_sai_token(self):
        for token in (None, "token-sai-hoan-toan-nhung-du-dai"):
            with self.subTest(token=token):
                status, body = self.post("/api/v1/disconnect", token=token)
                self.assertEqual(status, 401, body)
                self.assertEqual(body["error"], "unauthorized")

    def test_tu_choi_request_tu_trinh_duyet(self):
        status, body = self.post("/api/v1/disconnect",
                                 headers={"Origin": "http://ac.example"})
        self.assertEqual(status, 403, body)
        self.assertEqual(body["error"], "origin_forbidden")

    def test_tu_choi_host_khong_phai_loopback(self):
        status, body = self.get("/api/v1/status", headers={"Host": "roaster.local"})
        self.assertEqual(status, 403, body)
        self.assertEqual(body["error"], "invalid_host")

    def test_tu_choi_host_gia_dang_so_cong_la(self):
        # Trước đây "127.0.0.1:1;evil" lọt qua vì code cũ cắt bằng
        # rsplit(":", 1) nên phần trước dấu ':' cuối vẫn khớp "127.0.0.1".
        for host_gia in ("127.0.0.1:1;evil", "evil.example", "[::1]", "127.0.0.1evil"):
            with self.subTest(host=host_gia):
                status, body = self.get("/api/v1/status", headers={"Host": host_gia})
                self.assertEqual(status, 403, body)
                self.assertEqual(body["error"], "invalid_host")

    def test_duong_doc_khong_doi_token(self):
        status, _ = self.get("/api/v1/status", token=None)
        self.assertEqual(status, 200)


# ───────────────────────── trần số kết nối đồng thời ────────────────────────
# /api/v1/events?wait= là endpoint đọc CÔNG KHAI (cố ý không cần token) — tự
# thực nghiệm mở được 365+ kết nối "treo" chỉ trong 1.6s mà không cần biết
# token gì cả. Hạ trần xuống 4 để test nhanh, không cần mở hàng trăm kết nối
# thật mới thấy được cơ chế chặn.

class GioiHanKetNoi(unittest.TestCase):
    def setUp(self):
        import serial_terminal_bridge as bridge_mod
        self._bridge_mod = bridge_mod
        self._tran_goc = bridge_mod.MAX_CONCURRENT_CONNECTIONS
        bridge_mod.MAX_CONCURRENT_CONNECTIONS = 4
        self.bridge = SerialDataBridge(port=0, token=TOKEN_TEST, port_provider=lambda: [])
        self.bridge.start()
        self.base = "http://127.0.0.1:%d" % self.bridge.port

    def tearDown(self):
        self.bridge.stop()
        self._bridge_mod.MAX_CONCURRENT_CONNECTIONS = self._tran_goc

    def test_vuot_tran_bi_tu_choi_503_khong_treo_khong_sap(self):
        import http.client
        host, port = self.base.split("//")[1].split(":")
        ket_noi = []
        for _ in range(4):
            c = http.client.HTTPConnection(host, int(port), timeout=10)
            c.request("GET", "/api/v1/events?after=999999&wait=3")
            ket_noi.append(c)
        time.sleep(0.2)   # để 4 kết nối trên thật sự chiếm slot trước khi bắn thêm

        them = http.client.HTTPConnection(host, int(port), timeout=5)
        them.request("GET", "/api/v1/status")
        resp = them.getresponse()
        body = json.loads(resp.read())
        self.assertEqual(resp.status, 503, body)
        self.assertEqual(body["error"], "too_many_connections")
        them.close()

        for c in ket_noi:
            c.close()
        # Đóng socket phía client KHÔNG giải phóng slot ngay — luồng server vẫn
        # đang chặn trong _condition.wait() nội bộ (không phải I/O socket) nên
        # không thấy client đã ngắt, chỉ nhả slot sau khi hết đúng wait=3 đã
        # khai. Đây là giới hạn thật (đã bị chặn trên bởi wait<=25s), không
        # phải lỗi rò rỉ — chờ đủ hơn wait= rồi mới kỳ vọng slot đã trống lại.
        time.sleep(3.5)

        status, _ = self._goi_don("GET", "/api/v1/status")
        self.assertEqual(status, 200)

    def _goi_don(self, method, path):
        import urllib.request
        req = urllib.request.Request(self.base + path, method=method)
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.load(r)


# ───────────────────── bộ đệm, con trỏ, chờ RX ─────────────────────

class BoDemVaConTro(unittest.TestCase):
    def setUp(self):
        self.bridge = SerialDataBridge(port=0, max_events=3, token=TOKEN_TEST)
        self.bridge.start()
        self.base = "http://127.0.0.1:%d" % self.bridge.port

    def tearDown(self):
        self.bridge.stop()

    def get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=10) as response:
            return json.load(response)

    def test_tran_bo_dem_bao_mat_du_lieu(self):
        for value in (b"1", b"2", b"3", b"4", b"5"):
            self.bridge.record("rx", value)
        data = self.get("/api/v1/events?after=0")
        self.assertTrue(data["cursor_lost"], "phải báo dữ liệu đã bị đẩy khỏi bộ đệm")
        self.assertEqual(data["oldest_seq"], 3)

    def test_con_tro_vuot_truoc_bao_ro(self):
        self.bridge.record("rx", b"1")
        data = self.get("/api/v1/events?after=99")
        self.assertTrue(data["cursor_ahead"])
        self.assertEqual(data["next_after"], 1)

    def test_khoi_qua_lon_bi_cat_nho(self):
        self.bridge.record("rx", b"A" * 9000)
        data = self.get("/api/v1/events?after=0&limit=10")
        self.assertTrue(all(e["size"] <= 4096 for e in data["events"]))

    def test_session_id_on_dinh_trong_mot_phien(self):
        dau = self.get("/api/v1/events?after=0")["session_id"]
        self.bridge.record("rx", b"x")
        self.assertEqual(self.get("/api/v1/events?after=0")["session_id"], dau)

    def test_cho_rx_khong_bi_danh_thuc_boi_tx(self):
        def ghi_tx():
            time.sleep(0.15)
            self.bridge.record("tx", b"PING")

        threading.Thread(target=ghi_tx, daemon=True).start()
        bat_dau = time.monotonic()
        data = self.get("/api/v1/events?after=0&direction=rx&wait=0.6")
        troi_qua = time.monotonic() - bat_dau
        self.assertEqual(data["events"], [], "lọc rx không được trả về khối tx")
        self.assertGreater(troi_qua, 0.5, "phải chờ hết hạn, không thoát sớm vì có tx")


# ───────────────────────────── hàng đợi lệnh ─────────────────────────────

class HangDoiLenh(NenDieuKhien):
    def setUp(self):
        super().setUp()
        self._chay = False            # dừng bơm Tk để mô phỏng app đang bận
        self._bom.join(timeout=5)

    def test_lenh_het_han_khi_con_cho_thi_bi_huy(self):
        status, body = self.post("/api/v1/disconnect", {"timeout_seconds": 0.2})
        self.assertEqual(status, 504, body)
        self.assertEqual(body["error"], "command_timeout")
        self.assertEqual(CongGia.da_tao, [], "lệnh bị hủy không được chạm thiết bị")


class LenhChayLau(NenDieuKhien):
    def test_lenh_vuot_han_tra_ma_thao_tac_de_theo_doi(self):
        # Trễ nằm trong lúc driver mở cổng: lệnh ĐÃ bắt đầu rồi mới vượt hạn.
        CongGia.tre_mo = 0.6
        status, body = self.post("/api/v1/connect",
                                 {"port": "COM90", "timeout_seconds": 0.2})
        self.assertEqual(status, 202, body)
        op_id = body["operation"]["id"]
        self.assertIn(body["operation"]["state"], ("pending", "running"))

        theo_doi = None
        ket_thuc = time.monotonic() + 10
        while time.monotonic() < ket_thuc:
            status, theo_doi = self.get("/api/v1/operations/" + op_id)
            self.assertEqual(status, 200, theo_doi)
            if theo_doi["state"] not in ("pending", "running"):
                break
            time.sleep(0.05)
        self.assertEqual(theo_doi["state"], "completed", theo_doi)
        self.assertEqual(len(CongGia.da_tao), 1, "không được thực thi lệnh hai lần")

    def test_thao_tac_khong_ton_tai_bao_404(self):
        status, body = self.get("/api/v1/operations/khong-co-that")
        self.assertEqual(status, 404, body)


# ───────────────────────────── MCP thật ─────────────────────────────

class McpThucTe(NenDieuKhien):
    def _mcp(self, requests):
        server = os.path.join(THU_MUC_TOOLS, "mcp_serial_terminal", "server.py")
        env = dict(os.environ, OTL_SERIAL_API_BASE=self.base,
                   OTL_SERIAL_API_TOKEN=TOKEN_TEST, PYTHONIOENCODING="utf-8")
        stdin = "".join(json.dumps(row) + "\n" for row in requests)
        run = subprocess.run([sys.executable, server], input=stdin, capture_output=True,
                             text=True, encoding="utf-8", env=env, timeout=60)
        self.assertEqual(run.returncode, 0, run.stderr)
        return [json.loads(line) for line in run.stdout.splitlines() if line.strip()]

    def test_danh_sach_du_13_cong_cu(self):
        (phan_hoi,) = self._mcp([{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}])
        ten = sorted(tool["name"] for tool in phan_hoi["result"]["tools"])
        self.assertEqual(ten, sorted([
            "serial_status", "serial_list_ports", "serial_configure", "serial_connect",
            "serial_disconnect", "serial_send", "serial_read", "serial_wait",
            "serial_modem_status", "serial_set_lines", "serial_operation_status",
            "serial_macro_plan", "serial_macro_run"]))

    def test_mcp_mo_gui_doc_dong_qua_api_that(self):
        goi = [
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
             "params": {"name": "serial_connect",
                        "arguments": {"port": "COM90",
                                      "settings": {"baudrate": 9600}}}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
             "params": {"name": "serial_send",
                        "arguments": {"encoding": "text", "data": "MCP", "eol": "lf"}}},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
             "params": {"name": "serial_disconnect", "arguments": {}}},
        ]
        phan_hoi = {row["id"]: row for row in self._mcp(goi)}
        for ma in (1, 2, 3):
            self.assertNotIn("error", phan_hoi[ma], phan_hoi[ma])
            self.assertFalse(phan_hoi[ma]["result"].get("isError"), phan_hoi[ma])
        gui = json.loads(phan_hoi[2]["result"]["content"][0]["text"])
        self.assertEqual(gui["written_bytes"], 4)
        self.assertEqual(bytes(CongGia.da_tao[-1].da_ghi), b"MCP\n")
        self.assertFalse(CongGia.da_tao[-1].is_open)

    def test_mcp_bao_loi_co_noi_dung_khi_app_tu_choi(self):
        (phan_hoi,) = self._mcp([{"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                  "params": {"name": "serial_send",
                                             "arguments": {"encoding": "text", "data": "X"}}}])
        ket_qua = phan_hoi["result"]
        self.assertTrue(ket_qua.get("isError"), ket_qua)
        noi_dung = ket_qua["content"][0]["text"]
        self.assertIn("not_connected", noi_dung, "MCP phải giữ mã lỗi máy đọc được")
        self.assertIn("Cổng serial chưa mở", noi_dung)


if __name__ == "__main__":
    unittest.main(verbosity=2)
