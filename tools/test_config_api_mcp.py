"""Kiểm API cấu hình qua HTTP và MCP bằng cầu giả, không chạm máy thật."""
import json
import os
import subprocess
import sys
import unittest
import urllib.request
import urllib.error
from unittest.mock import Mock

import roast_lab_hmi as H


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.api = H.Api.__new__(H.Api)
        self.api._link = Mock()
        self.api._link.cfg_op.return_value = {"ok": True, "val": 12}
        self.api.audit_add = Mock()
        self.api.lease_touch = Mock()
        self.api.web_cfg = {"bat": True, "cong": 0}
        self.api.web_tokens = {}
        self.api._apikeys = Mock()
        # "control_config" = khoá có ĐỦ hai phạm vi, để soi nhóm $M lái lửa.
        self.api._apikeys.verify.side_effect = lambda key: (
            {"id": key, "name": key,
             "scopes": ["config", "control"] if key == "control_config" else [key]}
            if key in ("read", "config", "control_config") else None)
        H.start_webserver(self.api)
        self.base = "http://127.0.0.1:%d" % self.api._websrv.server_port

    def tearDown(self):
        self.api._websrv.shutdown()
        self.api._websrv.server_close()

    def request(self, path, key, data=None):
        req = urllib.request.Request(self.base + path,
                                     data=None if data is None else json.dumps(data).encode(),
                                     headers={"Authorization": "Bearer " + key,
                                              "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as res:
            return json.load(res)

    def test_read_and_permissions(self):
        result = self.request("/api/v1/mc_read", "read")
        self.assertEqual(len(result["cfg"]), H.otl_link.CFG_MAXIDX)
        for key in ("read", "invalid"):
            with self.assertRaises(urllib.error.HTTPError) as caught:
                self.request("/api/v1/mc_write", key, {"items": [["M1", 1, 10]]})
            self.assertEqual(caught.exception.code, 403 if key == "read" else 401)
        self.assertFalse(any(c.args[0] == 2 for c in self.api._link.cfg_op.call_args_list))

    def test_write_validation_and_partial_failure(self):
        for items in ([], [["M1", 1, -1]], [["M1", 1, 65536]],
                      [["M1", 1, 1.5]], [["M1", 1, True]],
                      [["M1", 1, 1], ["M1", 1, 2]], [["M1", 1, 1], ["bad", 999, 2]]):
            self.assertFalse(self.request("/api/v1/mc_write", "config", {"items": items})["ok"])
        self.api._link.cfg_op.assert_not_called()
        self.api._link.cfg_op.side_effect = [{"ok": True}, {"ok": False, "err": "máy đang bận"}]
        result = self.request("/api/v1/mc_write", "config",
                              {"items": [["M38", 38, 10], ["M39", 39, 20], ["M40", 40, 30]]})
        self.assertFalse(result["ok"])
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["err"], "máy đang bận")
        self.assertEqual(result["not_attempted"], ["M40"])
        self.assertEqual(self.api.audit_add.call_count, 2)

    def test_doc_khong_con_tinh_la_nhip_tim(self):
        """Trước 2026-09-09 mọi request của khoá đang lái đều nhấp nhịp, kể cả
        GET đọc telemetry — nên một vòng lặp poll còn chạy là đủ giữ quyền lái dù
        AI đã treo. Nhịp phải sinh từ HÀNH ĐỘNG LÁI, không từ việc đọc."""
        self.request("/api/v1/mc_read", "read")
        self.api.lease_touch.assert_not_called()
        self.request("/api/v1/mc_write", "config", {"items": [["M38", 38, 10]]})
        self.api.lease_touch.assert_not_called()   # ghi cấu hình cũng không phải lái
        self.api._lease = None                     # lease_state() thật cần ô này
        self.request("/api/v1/lease_beat", "control_config", {})
        self.assertTrue(self.api.lease_touch.called)

    def test_m_lai_lua_can_them_pham_vi_control(self):
        """Khối cấu hình chạy ĐỘC LẬP PC control, nên nếu chỉ cần phạm vi
        'config' là một tác nhân đổi được trần gas ($M28) lúc không ai đứng cạnh
        máy, rồi mẻ sau thợ rang tay theo tham số đã bị đổi. Nhóm $M lái lửa,
        nhiệt và cơ cấu phải đòi thêm 'control'."""
        for idx in (1, 8, 23, 28, 52):
            r = self.request("/api/v1/mc_write", "config", {"items": [["M%d" % idx, idx, 10]]})
            self.assertFalse(r["ok"], idx)
            self.assertEqual(r["err"], "pham_vi", idx)
        self.api._link.cfg_op.assert_not_called()      # chưa ô nào xuống máy
        # Khoá có đủ control thì đi được; $M vô hại thì 'config' vẫn đủ như cũ.
        self.api._link.cfg_op.side_effect = None
        self.api._link.cfg_op.return_value = {"ok": True}
        self.assertTrue(self.request("/api/v1/mc_write", "control_config",
                                     {"items": [["M28", 28, 60]]})["ok"])
        self.assertTrue(self.request("/api/v1/mc_write", "config",
                                     {"items": [["M38", 38, 10]]})["ok"])
        self.assertEqual([c.args for c in self.api._link.cfg_op.call_args_list],
                         [(2, 28, 60), (2, 38, 10)])

    def mcp_cau_hinh(self, calls):
        """Chạy MCP server thật với tầng cấu hình bật, trỏ vào cầu giả."""
        env = dict(os.environ, OTL_API_BASE=self.base, OTL_API_KEY="config",
                   OTL_MCP_CONFIG="1", OTL_MCP_CONTROL="0", PYTHONIOENCODING="utf-8")
        messages = [{"jsonrpc": "2.0", "id": i, "method": "tools/call",
                     "params": {"name": name, "arguments": args}}
                    for i, (name, args) in enumerate(calls)]
        run = subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "mcp_roaster", "server.py")],
                             input="\n".join(map(json.dumps, messages)) + "\n",
                             capture_output=True, text=True, encoding="utf-8", env=env, timeout=15)
        self.assertEqual(run.returncode, 0, run.stderr)
        return [json.loads(line)["result"] for line in run.stdout.splitlines()]

    def test_m53_doc_ghi_qua_http_va_mcp(self):
        """$M53 = tự động mở cửa xả (1 chạy trọn chuỗi xả · 0 chỉ làm nguội).

        Khối cấu hình mở tới đâu thì đọc/ghi phải với tới đó. Mô tả dừng ở $M52
        trong khi firmware đã mở $M53 nghĩa là AI không bao giờ hỏi tới tham số
        mới — không báo lỗi gì cả, chỉ lặng lẽ thiếu."""
        maxidx = H.otl_link.CFG_MAXIDX
        self.assertGreaterEqual(maxidx, 53)
        cfg = self.request("/api/v1/mc_read", "read")["cfg"]
        self.assertEqual(len(cfg), maxidx)
        self.assertIn("M53", cfg)
        # Khoá chỉ-đọc KHÔNG ghi được $M53
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.request("/api/v1/mc_write", "read", {"items": [["M53", 53, 1]]})
        self.assertEqual(caught.exception.code, 403)
        # Khoá config ghi được; ngoài dải bị API chặn TRƯỚC khi chạm máy
        self.assertTrue(self.request("/api/v1/mc_write", "config",
                                     {"items": [["M53", 53, 1]]})["ok"])
        self.assertFalse(self.request("/api/v1/mc_write", "config",
                                      {"items": [["M?", maxidx + 1, 1]]})["ok"])
        ghi = [c.args for c in self.api._link.cfg_op.call_args_list if c.args[0] == 2]
        self.assertEqual(ghi, [(2, 53, 1)])
        # MCP giả: ghi $M53 đi đúng thanh ghi, ngoài dải chặn ngay tại MCP
        dat, ngoai_dai = self.mcp_cau_hinh([
            ("roaster_set_machine_param", {"idx": 53, "value": 0}),
            ("roaster_set_machine_param", {"idx": maxidx + 1, "value": 1})])
        self.assertFalse(dat.get("isError"), dat)
        self.assertTrue(ngoai_dai.get("isError"), ngoai_dai)
        ghi = [c.args for c in self.api._link.cfg_op.call_args_list if c.args[0] == 2]
        self.assertEqual(ghi, [(2, 53, 1), (2, 53, 0)])

    def test_mcp_config_gate_and_http(self):
        for enabled in (False, True):
            messages = [
                {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                 "params": {"name": "roaster_set_machine_param", "arguments": {"idx": 38, "value": 10}}}]
            env = dict(os.environ, OTL_API_BASE=self.base, OTL_API_KEY="config",
                       OTL_MCP_CONFIG="1" if enabled else "0", OTL_MCP_CONTROL="0",
                       PYTHONIOENCODING="utf-8")
            run = subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "mcp_roaster", "server.py")],
                                 input="\n".join(map(json.dumps, messages)) + "\n",
                                 capture_output=True, text=True, encoding="utf-8", env=env, timeout=10)
            self.assertEqual(run.returncode, 0, run.stderr)
            listed, called = [json.loads(line)["result"] for line in run.stdout.splitlines()]
            names = [tool["name"] for tool in listed["tools"]]
            self.assertEqual("roaster_set_machine_param" in names, enabled)
            self.assertFalse(any(name.startswith("roaster_lai_") for name in names))
            self.assertEqual(bool(called.get("isError")), not enabled)
        self.api._link.cfg_op.assert_called_once_with(2, 38, 10)


if __name__ == "__main__":
    unittest.main()
