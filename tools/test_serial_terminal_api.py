"""Kiểm cầu API/MCP của Serial Terminal mà không mở cổng COM thật."""

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

from serial_terminal_bridge import SerialDataBridge


TEST_TOKEN = "test-token-for-serial-api-1234567890"


class FakeWidget:
    def __init__(self, value=None):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value

    def configure(self, **_kwargs):
        pass


class FakeSerialManager:
    def __init__(self):
        self.opened = False
        self.written = []
        self.partial = False
        self.settings = None
        self.dtr = self.rts = False

    def is_open(self):
        return self.opened

    def open(self, port, baud, bytesize, parity, stopbits, flow):
        self.opened = True
        self.port = port
        self.settings = (baud, bytesize, parity, stopbits, dict(flow))

    def configure(self, settings):
        self.settings = dict(settings)

    def write(self, data):
        count = len(data) - 1 if self.partial else len(data)
        self.written.append(bytes(data[:count]))
        return count

    def close(self):
        self.opened = False

    def set_dtr(self, value):
        self.dtr = value

    def set_rts(self, value):
        self.rts = value

    def modem_lines(self):
        return (True, False, True, False) if self.opened else None


class SerialTerminalApiTest(unittest.TestCase):
    def setUp(self):
        self.bridge = SerialDataBridge(port=0, max_events=3)
        self.bridge.start()
        self.base = "http://127.0.0.1:%d" % self.bridge.port

    def tearDown(self):
        self.bridge.stop()

    def get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=3) as response:
            return json.load(response)

    def test_status_va_du_lieu_nguyen_ban(self):
        self.bridge.set_connection(True, "COM3", {"baud": 9600})
        self.bridge.record("rx", b"OK\r\n")
        status = self.get("/api/v1/status")
        self.assertTrue(status["connected"])
        self.assertEqual(status["port"], "COM3")
        data = self.get("/api/v1/events?after=0&direction=rx")
        self.assertEqual(data["events"][0]["text"], "OK\r\n")
        self.assertEqual(data["events"][0]["hex"], "4F 4B 0D 0A")
        self.assertEqual(data["events"][0]["base64"], "T0sNCg==")

    def test_bo_dem_vong_va_con_tro(self):
        for value in (b"1", b"2", b"3", b"4"):
            self.bridge.record("rx", value)
        data = self.get("/api/v1/events?after=2&limit=1")
        self.assertEqual([e["seq"] for e in data["events"]], [3])
        self.assertEqual(data["next_after"], 3)
        self.assertEqual(data["latest_seq"], 4)

    def test_mcp_doc_api_that(self):
        self.bridge.record("tx", b"PING")
        server = os.path.join(os.path.dirname(__file__), "mcp_serial_terminal", "server.py")
        env = dict(os.environ, OTL_SERIAL_API_BASE=self.base, PYTHONIOENCODING="utf-8")
        request = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                   "params": {"name": "serial_read", "arguments": {"after": 0}}}
        run = subprocess.run([sys.executable, server], input=json.dumps(request) + "\n",
                             capture_output=True, text=True, encoding="utf-8",
                             env=env, timeout=5)
        self.assertEqual(run.returncode, 0, run.stderr)
        result = json.loads(run.stdout)["result"]
        body = json.loads(result["content"][0]["text"])
        self.assertEqual(body["events"][0]["direction"], "tx")


class SerialAutomationControlTest(unittest.TestCase):
    def setUp(self):
        from otl_serial_terminal import App

        self.App = App
        self.bridge = SerialDataBridge(port=0, token=TEST_TOKEN, port_provider=lambda: [{
            "device": "FAKE0", "name": "FAKE0", "description": "Fake USB", "hwid": "FAKE",
            "vid": 0x1234, "pid": 0x5678, "serial_number": "TEST", "location": "1-1",
            "manufacturer": "OTL", "product": "Test", "interface": None,
        }])
        self.manager = FakeSerialManager()
        app = object.__new__(App)
        app.api, app.sm = self.bridge, self.manager
        app.port_map = {"FAKE0 — Fake USB": "FAKE0"}
        app.opt_port = FakeWidget("FAKE0 — Fake USB")
        app.opt_baud = FakeWidget("9600")
        app.opt_data = FakeWidget("8")
        app.opt_parity = FakeWidget("None")
        app.opt_stop = FakeWidget("1")
        app.opt_handshake = FakeWidget("None")
        app.dtr_var = FakeWidget(False)
        app.rts_var = FakeWidget(False)
        app.echo_on = FakeWidget(False)
        app.btn_open = FakeWidget()
        app.modem_lbls = {}
        app.refresh_ports = lambda: None
        app._show_port_info = lambda: None
        app._set_pill = lambda _value: None
        app._set_status = lambda _value: None
        app._append_log = lambda *_args: None
        self.app = app
        self.bridge.set_selected("FAKE0", app._selected_api_settings())
        self.bridge.start()
        self.base = "http://127.0.0.1:%d" % self.bridge.port
        self.running = True

        def pump():
            while self.running:
                self.bridge.process_commands(self.app._execute_api_command)
                time.sleep(0.002)

        self.pump = threading.Thread(target=pump, daemon=True)
        self.pump.start()

    def tearDown(self):
        self.running = False
        self.pump.join(timeout=1)
        self.bridge.stop()

    def request(self, path, body=None, token=TEST_TOKEN, origin=None):
        data = None if body is None else json.dumps(body).encode("utf-8")
        headers = {"Authorization": "Bearer " + token}
        if data is not None:
            headers["Content-Type"] = "application/json"
        if origin:
            headers["Origin"] = origin
        req = urllib.request.Request(self.base + path, data=data, headers=headers,
                                     method="POST" if data is not None else "GET")
        with urllib.request.urlopen(req, timeout=4) as response:
            return response.status, json.load(response)

    def test_http_configure_connect_tx_rx_modem_disconnect(self):
        _, configured = self.request("/api/v1/configure", {"port": "FAKE0", "settings": {
            "baudrate": 19200, "bytesize": 7, "parity": "even", "stopbits": 2}})
        self.assertFalse(configured["applied"])
        _, connected = self.request("/api/v1/connect", {})
        self.assertTrue(connected["connected"])
        _, sent = self.request("/api/v1/send", {"encoding": "text", "data": "Cà", "eol": "crlf"})
        self.assertEqual(sent["written_bytes"], len("Cà".encode("utf-8")) + 2)
        self.bridge.record("rx", b"OK\r\n")
        _, events = self.request("/api/v1/events?after=0")
        self.assertEqual([row["direction"] for row in events["events"]], ["tx", "rx"])
        _, modem = self.request("/api/v1/modem")
        self.assertTrue(modem["cd"])
        _, closed = self.request("/api/v1/disconnect", {})
        self.assertFalse(closed["connected"])

    def test_port_switch_refused_while_connected(self):
        self.request("/api/v1/connect", {})
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.request("/api/v1/configure", {"port": "FAKE1", "settings": {"baudrate": 115200}})
        self.assertEqual(caught.exception.code, 409)
        self.assertEqual(self.bridge.status()["port"], "FAKE0")

    def test_partial_write_is_reported_and_only_written_bytes_recorded(self):
        self.request("/api/v1/connect", {})
        self.manager.partial = True
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.request("/api/v1/send", {"encoding": "hex", "data": "01 02 03"})
        self.assertEqual(caught.exception.code, 409)
        self.assertEqual(self.bridge.events()["events"][0]["hex"], "01 02")

    def test_auth_and_origin_protect_control(self):
        with self.assertRaises(urllib.error.HTTPError) as unauthorized:
            self.request("/api/v1/connect", {}, token="wrong-token-but-long-enough-000")
        self.assertEqual(unauthorized.exception.code, 401)
        with self.assertRaises(urllib.error.HTTPError) as forbidden:
            self.request("/api/v1/connect", {}, origin="https://example.test")
        self.assertEqual(forbidden.exception.code, 403)

    def test_mcp_subprocess_controls_same_fake_owner(self):
        self.request("/api/v1/connect", {})
        server = os.path.join(THU_MUC_TOOLS, "mcp_serial_terminal", "server.py")
        env = dict(os.environ, OTL_SERIAL_API_BASE=self.base,
                   OTL_SERIAL_API_TOKEN=TEST_TOKEN, PYTHONIOENCODING="utf-8")
        message = {"jsonrpc": "2.0", "id": 7, "method": "tools/call", "params": {
            "name": "serial_send", "arguments": {"encoding": "base64", "data": "UElORw=="}}}
        run = subprocess.run([sys.executable, server], input=json.dumps(message) + "\n",
                             capture_output=True, text=True, encoding="utf-8", env=env, timeout=8)
        self.assertEqual(run.returncode, 0, run.stderr)
        result = json.loads(run.stdout)["result"]
        self.assertNotIn("isError", result)
        self.assertEqual(self.manager.written[-1], b"PING")

    def test_pending_command_timeout_is_cancelled(self):
        self.running = False
        self.pump.join(timeout=1)
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.request("/api/v1/connect", {"timeout_seconds": 0.05})
        self.assertEqual(caught.exception.code, 504)
        calls = []
        self.bridge.process_commands(lambda *args: calls.append(args))
        self.assertEqual(calls, [])
        self.assertFalse(self.manager.opened)


if __name__ == "__main__":
    unittest.main()
