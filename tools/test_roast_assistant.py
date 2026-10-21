"""Kiểm quyền và thao tác lặp bằng máy/mô hình giả; không gọi dịch vụ AI thật."""
import copy
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

import roast_assistant as A


class FakeApi:
    def __init__(self):
        self._control_lock = threading.RLock()
        self._lease = None
        self.master = True
        self.commands = []
        self.profiles = [{"name": "Colombia", "chargeT": 180, "temp": 206, "time": "11:00", "notes": "giữ lại"}]
        self.snap = {"state": "connected", "age_ms": 10, "data": {"flags": {"pc_control": True}, "gas": 30}}
        self.audit_add = Mock(return_value={"ok": True})
        self.ui_event = Mock()
        self.inv_lot_adjust = Mock(return_value={"ok": True})
        self.inv_order_add = Mock(return_value={"ok": True, "id": 1})
        self.lease_touch = Mock()

    def _is_master(self): return self.master
    def link_snapshot(self): return copy.deepcopy(self.snap)
    def prof_load(self): return copy.deepcopy(self.profiles)
    def prof_save(self, profiles): self.profiles = copy.deepcopy(profiles); return {"ok": True}
    def lease_state(self): return {"dang_lai": bool(self._lease), "khoa_id": (self._lease or {}).get("id")}
    def lease_open(self, ctx, minutes):
        if self._lease and self._lease["id"] != ctx["id"]: return {"ok": False, "msg": "Có người khác cầm lái."}
        self._lease = ctx.copy(); return {"ok": True}
    def lease_close(self, ctx, reason): self._lease = None; return {"ok": True}
    def link_write(self, name, value, ctx=None):
        self.commands.append((name, value)); return {"ok": True}
    def db_batch_list(self, n, query): return []
    def db_batch_stats(self, bid): return {"id": bid, "drop_sec": 660}
    def inv_lots(self): return []
    def inv_orders(self, n): return []
    def inv_cost_config(self): return {}


class FakeProvider:
    def __init__(self, calls): self.calls, self.n = calls, 0
    def complete(self, config, history, definitions):
        self.n += 1
        calls = self.calls if self.n == 1 else []
        return {"raw": [], "text": "" if calls else "Đã đọc kết quả.", "calls": copy.deepcopy(calls)}


def call(name, args, cid="call-1"):
    return {"name": name, "args": args, "id": cid}


class AssistantTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.api = FakeApi()
        self.agent = A.Assistant(self.api, self.tmp.name)
        self.agent.config = {"provider": "openai", "model": "test", "key": "test-secret"}

    def tearDown(self):
        self.agent.pause_all("Kết thúc kiểm thử.")
        self.tmp.cleanup()

    def action(self, action, payload=None, actor="desktop", trusted=True):
        return self.agent.dispatch(action, payload or {}, actor, trusted)

    def run_calls(self, calls, actor="desktop"):
        self.agent.provider = FakeProvider(calls)
        out = self.action("chat", {"text": "Kiểm thử", "request_id": "req-" + str(time.monotonic_ns())}, actor)
        self.assertTrue(out["ok"], out)
        deadline = time.monotonic() + 3
        while self.agent.state(actor)["busy"] and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertFalse(self.agent.state(actor)["busy"])
        return self.agent.state(actor)

    def test_a_requires_approval_and_replay_does_not_write(self):
        a = {"id": 1, "kg": -2, "note": "Kiểm kê"}
        st = self.run_calls([call("adjust_stock", a)])
        self.api.inv_lot_adjust.assert_not_called()
        pid = st["pending"]["id"]
        self.assertTrue(self.action("approve", {"id": pid})["ok"])
        self.assertFalse(self.action("approve", {"id": pid})["ok"])
        self.api.inv_lot_adjust.assert_called_once_with(1, -2, "Kiểm kê")

    def test_b_auto_data_but_not_machine(self):
        self.action("mode", {"mode": "B"})
        st = self.run_calls([call("adjust_stock", {"id": 1, "kg": 2, "note": "Nhập"})])
        self.assertIsNone(st["pending"])
        self.api.inv_lot_adjust.assert_called_once()
        st = self.run_calls([call("machine_command", {"name": "gas", "value": 35})])
        self.assertIsNotNone(st["pending"])
        self.assertEqual(self.api.commands, [])

    def test_c_limits_critical_and_valid_command(self):
        self.action("mode", {"mode": "C"})
        self.run_calls([call("machine_command", {"name": "gas", "value": 60})])
        self.assertEqual(self.api.commands, [])
        self.run_calls([call("machine_command", {"name": "gas", "value": 35})])
        self.assertEqual(self.api.commands, [("gas", 35)])
        st = self.run_calls([call("machine_command", {"name": "charge", "value": 1})])
        self.assertIsNotNone(st["pending"])
        self.assertEqual(len(self.api.commands), 1)

    def test_unknown_schema_nonfinite_and_safety_register(self):
        self.action("mode", {"mode": "C"})
        for args in ({"name": "hb", "value": 1}, {"name": "gas", "value": True},
                     {"name": "gas", "value": float("nan")}, {"name": "gas", "value": 101},
                     {"name": "gas", "value": 1, "approved": True}, {"name": "gas", "value": .01}):
            self.run_calls([call("machine_command", args)])
        self.assertEqual(self.api.commands, [])

    def test_stale_disconnected_and_revoked_master(self):
        self.action("mode", {"mode": "C"})
        self.api.snap["age_ms"] = 3000
        self.run_calls([call("machine_command", {"name": "gas", "value": 35})])
        self.api.snap["age_ms"] = 10
        self.api.master = False
        self.run_calls([call("machine_command", {"name": "gas", "value": 35})])
        self.assertEqual(self.api.commands, [])

    def test_web_separate_session_no_elevation(self):
        self.action("mode", {"mode": "C"})
        self.assertFalse(self.action("mode", {"mode": "D"}, "web:test", False)["ok"])
        self.run_calls([call("machine_command", {"name": "gas", "value": 35})], "web:test")
        self.assertEqual(self.api.commands, [])
        self.assertEqual(self.agent.state("web:test")["mode"], "A")
        self.assertFalse(self.action("configure", {"provider": "openai", "key": "bad", "model": "test"}, "web:test", False)["ok"])
        self.action("pause", actor="web:test", trusted=False)
        self.assertTrue(self.action("resume", actor="web:test", trusted=False)["ok"])

    def test_pending_expiry_and_cancellation(self):
        st = self.run_calls([call("machine_command", {"name": "charge", "value": 1})])
        self.agent.sessions["desktop"]["pending"]["expires"] = 0
        self.assertFalse(self.action("approve", {"id": st["pending"]["id"]})["ok"])
        self.assertEqual(self.api.commands, [])

    def test_pause_during_model_request_discards_response(self):
        entered, release = threading.Event(), threading.Event()
        def blocked(*args):
            entered.set(); release.wait(2)
            return {"raw": [], "text": "", "calls": [call("machine_command", {"name": "gas", "value": 35})]}
        self.agent.provider.complete = blocked
        self.action("mode", {"mode": "C"})
        self.action("chat", {"text": "đổi gas", "request_id": "pause-test"})
        self.assertTrue(entered.wait(1))
        self.agent.pause_all("Thợ thao tác.")
        release.set(); time.sleep(.05)
        self.assertEqual(self.api.commands, [])
        self.assertTrue(self.agent.state("desktop")["paused"])

    def test_request_id_prevents_double_provider_call(self):
        self.agent.provider = FakeProvider([])
        for _ in range(2):
            self.action("chat", {"text": "xin chào", "request_id": "same-request"})
        time.sleep(.05)
        self.assertEqual(self.agent.provider.n, 1)

    def test_profile_preserves_unedited_fields_and_order_maps_columns(self):
        self.action("mode", {"mode": "B"})
        self.run_calls([call("save_profile", {"name": "Colombia", "chargeT": 181, "temp": 207, "time": "11:20"})])
        self.assertEqual(self.api.profiles[0]["notes"], "giữ lại")
        self.run_calls([call("create_order", {"customer": "An", "profile": "Colombia", "qty_kg": 3, "notes": "Giao sáng"})])
        self.api.inv_order_add.assert_called_with({"customer": "An", "product": "Colombia", "qty_kg": 3, "note": "Giao sáng"})

    def test_dpapi_round_trip_and_no_key_in_state(self):
        result = self.action("configure", {"provider": "openai", "model": "test", "key": "a-real-looking-test-secret"})
        self.assertTrue(result["ok"], result)
        raw = (Path(self.tmp.name) / "assistant.json").read_text()
        self.assertNotIn("a-real-looking-test-secret", raw)
        other = A.Assistant(self.api, self.tmp.name)
        self.assertEqual(other.config["key"], "a-real-looking-test-secret")
        self.assertNotIn("a-real-looking-test-secret", json.dumps(other.state("desktop")))

    def test_encryption_failure_does_not_write_plaintext(self):
        with patch("auth_otl._dpapi_protect", side_effect=lambda data: data):
            result = self.action("configure", {"provider": "openai", "model": "test", "key": "test-secret"})
        self.assertFalse(result["ok"])
        self.assertFalse((Path(self.tmp.name) / "assistant.json").exists())

    def test_skill_allowlist(self):
        self.assertTrue(any(skill["name"] == "artisan-issues" for skill in A.skills()))
        self.assertIn("Đọc", A.read_skill("analyze-roast"))
        self.assertIn("search_roast_knowledge", A.read_skill("mill-city-roasters"))
        self.assertIn("search_artisan_issues", A.read_skill("artisan-issues"))
        result = A.search_artisan_issues("Fuji", limit=3, year="2022")
        self.assertTrue(result["available"])
        self.assertTrue(any(item["number"] == 1054 for item in result["matches"]))
        through_tool = self.agent._execute("desktop", "search_artisan_issues", {"query": "Fuji", "year": "2022"})
        self.assertTrue(through_tool["available"])
        for name in ("../auth_otl.py", "", "../../secret"):
            with self.assertRaises(ValueError): A.read_skill(name)

    def test_artisan_comment_only_match_returns_comment_evidence(self):
        data = Path(self.tmp.name) / "knowledge" / "artisan-issues"
        data.mkdir(parents=True)
        issue = {"number": 7, "title": "Serial report", "state": "closed",
                 "created_at": "2022-01-02T00:00:00Z", "updated_at": "2022-01-03T00:00:00Z",
                 "labels": ["bug"], "body": "The application starts.", "comments_count": 1,
                 "html_url": "https://github.com/artisan-roaster-scope/artisan/issues/7"}
        comment = {"issue_number": 7, "id": 99, "author": "tester",
                   "created_at": "2022-01-03T00:00:00Z", "body": "unique-comment-token reproduces the fault.",
                   "html_url": "https://github.com/artisan-roaster-scope/artisan/issues/7#issuecomment-99"}
        (data / "issues.jsonl").write_text(json.dumps(issue) + "\n", encoding="utf-8")
        (data / "comments.jsonl").write_text(json.dumps(comment) + "\n", encoding="utf-8")
        result = A.search_artisan_issues("unique-comment-token", directory=self.tmp.name)
        self.assertEqual(result["matches"][0]["match_source"], "comment")
        self.assertIn("unique-comment-token", result["matches"][0]["match_excerpt"])
        self.assertEqual(result["matches"][0]["matched_comments"][0]["author"], "tester")

    def test_roast_knowledge_search_is_bounded_and_cited(self):
        path = Path(self.tmp.name) / "corpus.sqlite3"
        with closing(sqlite3.connect(path)) as db:
            db.executescript("""
                CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE passages (id INTEGER PRIMARY KEY, video_id TEXT, title TEXT,
                    start_ms INTEGER, end_ms INTEGER, language TEXT, caption_type TEXT, text TEXT);
                CREATE VIRTUAL TABLE passages_fts USING fts5(
                    title, text, content='passages', content_rowid='id');
                INSERT INTO metadata VALUES ('channel_videos','1'),('indexed_videos','1'),
                    ('missing_videos','0'),('passages','1'),('built_at','2026-09-27T00:00:00+00:00');
                INSERT INTO passages VALUES
                    (1,'abcdefghijk','Airflow basics',65000,70000,'en-orig','automatic',
                     'Increase airflow after first crack when the coffee needs it.');
                INSERT INTO passages_fts(rowid,title,text) VALUES
                    (1,'Airflow basics','Increase airflow after first crack when the coffee needs it.');
            """)
        with patch.dict(os.environ, {"OTL_ROAST_KNOWLEDGE_DB": str(path)}):
            result = A.search_roast_knowledge("airflow first crack", limit=2)
            through_tool = self.agent._execute("desktop", "search_roast_knowledge", {"query": "airflow"})
        self.assertTrue(result["available"])
        self.assertTrue(through_tool["available"])
        self.assertEqual(self.api.commands, [])
        self.assertEqual(result["coverage"]["indexed_videos"], 1)
        self.assertEqual(result["matches"][0]["timestamp"], "1:05")
        self.assertIn("&t=65s", result["matches"][0]["url"])
        self.assertEqual(result["matches"][0]["caption_type"], "automatic")
        with self.assertRaises(ValueError):
            A.search_roast_knowledge("x" * 201)

    def start_plan(self):
        self.action("mode", {"mode": "D"})
        with patch.object(self.agent, "_launch_plan"):
            self.agent._start_plan("desktop", {"summary": "Kiểm kế hoạch", "steps": [
                {"after_s": 0, "name": "gas", "value": 30}, {"after_s": 10, "name": "air", "value": 40}]})
        return self.agent.sessions["desktop"]

    def test_plan_once_pause_resume_no_catchup(self):
        s = self.start_plan()
        with self.agent.lock:
            self.assertTrue(self.agent._plan_tick("desktop"))
            self.assertTrue(self.agent._plan_tick("desktop"))
        self.assertEqual(self.api.commands, [("gas", 30)])
        self.action("pause")
        self.assertFalse(self.agent._plan_tick("desktop"))
        self.assertIsNone(self.api._lease)
        with patch.object(self.agent, "_launch_plan"):
            self.assertTrue(self.action("resume")["ok"])
        s["plan"]["start"] = time.monotonic() - 10
        self.assertFalse(self.agent._plan_tick("desktop"))
        self.assertEqual(self.api.commands, [("gas", 30), ("air", 40)])
        self.assertEqual(s["plan"]["status"], "done")

    def test_plan_late_stale_and_lease_loss_rejected(self):
        s = self.start_plan()
        s["plan"]["start"] -= 5
        with self.assertRaises(ValueError): self.agent._plan_tick("desktop")
        self.assertEqual(self.api.commands, [])
        s["plan"]["start"] = time.monotonic()
        self.api._lease = None
        with self.assertRaises(ValueError): self.agent._plan_tick("desktop")
        self.assertEqual(self.api.commands, [])

    def test_shared_human_write_hook_cancels_before_write(self):
        import roast_lab_hmi as H
        host = H.Api.__new__(H.Api)
        host._control_lock = self.api._control_lock
        host._assistant = self.agent
        host._link_write_guarded = Mock(side_effect=lambda *a: {"paused_before_write": self.agent.state("desktop")["paused"]})
        self.action("mode", {"mode": "C"})
        result = host.link_write("gas", 25)
        self.assertTrue(result["paused_before_write"])

    def test_anthropic_results_grouped_for_multiple_tools(self):
        self.agent.config["provider"] = "anthropic"
        s = self.agent._session("desktop")
        s["history"] = [{"role": "assistant", "content": []}]
        self.agent._result(s, "one", {"ok": True})
        self.agent._result(s, "two", {"ok": False})
        self.assertEqual(len(s["history"]), 2)
        self.assertEqual(len(s["history"][-1]["content"]), 2)


if __name__ == "__main__":
    unittest.main()
