"""Kiểm thanh ghi → API → MCP và chiều lệnh về hàng đợi Modbus, không mở serial."""
import json
import os
import subprocess
import sys
import time
import unittest
from unittest.mock import Mock

import roast_lab_hmi as H
import pc_link_map as P
from test_config_api_mcp import ConfigTest


class TelemetryControlTest(unittest.TestCase):
    request = ConfigTest.request
    tearDown = ConfigTest.tearDown

    def setUp(self):
        ConfigTest.setUp(self)
        self.api._lease = None
        self.api._lk_state = "connected"
        self.api.op_log = Mock()
        self.api.lease_touch = H.Api.lease_touch.__get__(self.api)
        self.api._apikeys.verify.side_effect = lambda key: (
            {"id": key, "name": key, "scopes": ["read", "control"]}
            if key == "driver" else {"id": key, "name": key, "scopes": ["read"]})
        link = H.otl_link.RoasterLink({"port": "FAKE", "baud": 9600, "slave": 1})
        link._mode = H.otl_link.MODE_PCLINK
        link._state = "connected"
        link._snap_ts = time.time()
        # Giá trị thô độc lập với bộ giải mã để bắt sai vị trí/hệ số/dấu.
        link._snap = P.decode([1850, 2200, 1234, 65536 - 250, 800,
                               30, 40, 50, 2000, 65536 - 120, 6, 120,
                               1, 0xCC, 15, 3500, 100, 1, 3, 1250, 100, 150,
                               1])   # vac_en — ô ĐỌC thêm 2026-09-09
        self.api._link = link
        self.api.prof_load = Mock(return_value=[{"id": "profile-1", "name": "Hồ sơ thử"}])
        self.api.db_batch_stats = Mock(return_value={"mile": {"CHARGE": 0, "DROP": 600}})

    def mcp(self, calls, enabled=True):
        env = dict(os.environ, OTL_API_BASE=self.base, OTL_API_KEY="driver",
                   OTL_MCP_CONTROL="1" if enabled else "0", OTL_MCP_CONFIG="0",
                   PYTHONIOENCODING="utf-8")
        messages = [{"jsonrpc": "2.0", "id": i, "method": "tools/call",
                     "params": {"name": name, "arguments": args}} for i, (name, args) in enumerate(calls)]
        run = subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "mcp_roaster", "server.py")],
                             input="\n".join(map(json.dumps, messages)) + "\n",
                             capture_output=True, text=True, encoding="utf-8", env=env, timeout=15)
        self.assertEqual(run.returncode, 0, run.stderr)
        return [json.loads(line)["result"] for line in run.stdout.splitlines()]

    def test_telemetry_and_profiles(self):
        result = self.mcp([("roaster_trang_thai", {}), ("roaster_ho_so", {})])
        snapshot = json.loads(result[0]["content"][0]["text"])
        self.assertEqual(snapshot, self.request("/api/v1/snapshot", "read") | {"age_ms": snapshot["age_ms"]})
        expected = {"bt": 185.0, "et": 220.0, "ror_bt": 12.34, "ror_et": -2.5,
                    "gas": 30, "air": 40, "drum": 50, "drum_hz": 35.0,
                    "vac": -120, "prof_sel": 3, "prof_ok": 1, "prof_pct": 100}
        for key, value in expected.items():
            self.assertEqual(snapshot["data"][key], value, key)
        for key in ("charge", "drop", "pc_control", "flame"):
            self.assertTrue(snapshot["data"]["flags"][key])
        self.assertEqual(json.loads(result[1]["content"][0]["text"])["profiles"][0]["id"], "profile-1")

    def test_commands_reach_correct_registers(self):
        calls = [("roaster_lai_xin_quyen", {"so_phut": 1}),
                 ("roaster_lai_gas", {"muc": 40}), ("roaster_lai_gio", {"muc": 50}),
                 ("roaster_lai_trong", {"muc": 60}), ("roaster_lai_lua", {"bat": True})]
        for name, value in (("charge", 1), ("drop", 1), ("sv", 210), ("sv", 215),
                            ("profile", 3), ("mode", 2), ("auto", 1), ("scale_tg", 15.5)):
            calls.append(("roaster_lai_lenh", {"ten": name, "gia_tri": value}))
        results = self.mcp(calls)
        for result in results:
            self.assertFalse(result.get("isError"), result)
        queued = self.api._link._pending
        for reg, value in ((140, 40), (141, 50), (142, 60), (145, 1), (146, 1),
                           (147, 1), (143, 2100), (143, 2150), (157, 3), (158, 2),
                           (150, 1), (159, 155)):
            self.assertIn((reg, [value]), queued)
        self.assertNotIn((146, [0]), queued)
        self.assertNotIn((147, [0]), queued)
        self.assertEqual(self.api._lease["cuoi"]["sv"], 215)
        ack = json.loads(results[1]["content"][0]["text"])
        self.assertEqual(ack["status"], "queued")
        self.assertEqual(ack["engineering_value"], 40)

    def test_invalid_values_and_missing_lease(self):
        result = self.mcp([("roaster_lai_gas", {"muc": 40})])[0]
        self.assertTrue(result["isError"])
        self.assertFalse(self.api._link._pending)
        self.request("/api/v1/lease_open", "driver", {"phut": 1})
        before = list(self.api._link._pending)
        for name, value in (("gas", -1), ("air", 101), ("drum", float("nan")),
                            ("sv", float("inf")), ("charge", 2), ("unknown", 1),
                            ("hb", 1), ("agent", 0)):
            result = self.request("/api/v1/write", "driver", {"name": name, "value": value})
            self.assertFalse(result["ok"], (name, value, result))
        self.assertEqual(self.api._link._pending, before)


if __name__ == "__main__":
    unittest.main()
