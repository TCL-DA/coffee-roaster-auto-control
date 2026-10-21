"""Cầu HTTP tự động hóa cho OTL Serial Terminal.

Luồng HTTP không truy cập Tk. Lệnh điều khiển được xếp hàng và ứng dụng xử lý
trên luồng Tk qua ``process_commands``.
"""

import base64
import binascii
import hmac
import json
import logging
import math
import re
import socket
import threading
import time
import uuid
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from logging.handlers import RotatingFileHandler
from urllib.parse import parse_qs, urlparse

from serial_terminal_auth import load_or_create_token, token_file_path

MAX_BODY_BYTES = 64 * 1024
MAX_TX_BYTES = 4096
MAX_EVENT_BYTES = 4096
MAX_WAIT_SECONDS = 25.0
MAX_COMMAND_SECONDS = 10.0

_HOST_RE = re.compile(r"^(127\.0\.0\.1|localhost)(:\d{1,5})?$")


def _setup_audit_logger():
    """Nhật ký kiểm toán: ai gọi lệnh điều khiển gì, lúc nào, kết quả ra sao.

    Trước đây log_message() của BaseHTTPRequestHandler bị tắt hoàn toàn (đúng,
    vì log truy cập mặc định quá ồn và không hữu ích) nhưng kéo theo hệ quả
    phụ: KHÔNG CÓ dấu vết nào để điều tra lại nếu có sự cố (gửi nhầm byte vào
    máy thật qua automation). Ghi riêng một log có chủ đích, không log token
    hay nội dung byte gửi/nhận — chỉ tên lệnh, kết quả, và ai gọi (địa chỉ).
    """
    logger = logging.getLogger("otl_serial_api")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    try:
        path = token_file_path().parent / "audit.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(path, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
    except OSError:
        logger.addHandler(logging.NullHandler())
    return logger


_audit = _setup_audit_logger()


class CommandError(Exception):
    def __init__(self, code, message, http_status=400):
        super().__init__(message)
        self.code = code
        self.http_status = int(http_status)


def _finite(value, name):
    if isinstance(value, bool):
        raise ValueError(f"{name} phải là số")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} phải là số hữu hạn")
    return number


def normalize_settings(value, base=None, require_all=False):
    if value is None:
        value = {}
    if not isinstance(value, dict):
        raise ValueError("settings phải là object")
    allowed = {"baudrate", "bytesize", "parity", "stopbits", "xonxoff", "rtscts", "dsrdtr"}
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ValueError("Trường settings không hỗ trợ: " + ", ".join(unknown))
    result = dict(base or {})
    result.update(value)
    if require_all and not allowed.issubset(result):
        raise ValueError("Thiếu trường settings: " + ", ".join(sorted(allowed - set(result))))
    if "baudrate" in result:
        baud = result["baudrate"]
        if isinstance(baud, bool) or not isinstance(baud, int) or not 50 <= baud <= 4_000_000:
            raise ValueError("baudrate phải là số nguyên từ 50 đến 4000000")
    if "bytesize" in result:
        size = result["bytesize"]
        if isinstance(size, bool) or not isinstance(size, int) or size not in (5, 6, 7, 8):
            raise ValueError("bytesize phải là 5, 6, 7 hoặc 8")
    if "parity" in result:
        parity = result["parity"]
        if not isinstance(parity, str) or parity.lower() not in ("none", "even", "odd", "mark", "space"):
            raise ValueError("parity phải là none, even, odd, mark hoặc space")
        result["parity"] = parity.lower()
    if "stopbits" in result:
        stop = _finite(result["stopbits"], "stopbits")
        if stop not in (1.0, 1.5, 2.0):
            raise ValueError("stopbits phải là 1, 1.5 hoặc 2")
        result["stopbits"] = int(stop) if stop in (1.0, 2.0) else 1.5
    for key in ("xonxoff", "rtscts", "dsrdtr"):
        if key in result and not isinstance(result[key], bool):
            raise ValueError(f"{key} phải là boolean")
    if sum(bool(result.get(key)) for key in ("xonxoff", "rtscts", "dsrdtr")) > 1:
        raise ValueError("Chỉ được bật một chế độ flow control")
    return result


def _decode_bytes(encoding, data):
    if encoding not in ("text", "hex", "base64") or not isinstance(data, str):
        raise ValueError("encoding phải là text/hex/base64 và data phải là chuỗi")
    try:
        if encoding == "text":
            return data.encode("utf-8")
        if encoding == "hex":
            compact = "".join(data.split())
            if len(compact) % 2:
                raise ValueError("Chuỗi hex phải có đủ cặp ký tự")
            return bytes.fromhex(compact)
        return base64.b64decode(data.encode("ascii"), validate=True)
    except (UnicodeEncodeError, ValueError, binascii.Error) as exc:
        raise ValueError(f"Dữ liệu {encoding} không hợp lệ: {exc}") from exc


def decode_send(payload):
    if not isinstance(payload, dict):
        raise ValueError("Nội dung gửi phải là object")
    unknown = sorted(set(payload) - {"encoding", "data", "eol"})
    if unknown:
        raise ValueError("Trường gửi không hỗ trợ: " + ", ".join(unknown))
    encoding = payload.get("encoding", "text")
    eol = payload.get("eol", "none")
    if eol not in ("none", "lf", "cr", "crlf"):
        raise ValueError("eol phải là none, lf, cr hoặc crlf")
    raw = _decode_bytes(encoding, payload.get("data"))
    raw += {"none": b"", "lf": b"\n", "cr": b"\r", "crlf": b"\r\n"}[eol]
    if not raw or len(raw) > MAX_TX_BYTES:
        raise ValueError(f"Dữ liệu gửi phải từ 1 đến {MAX_TX_BYTES} byte")
    return raw


# ─────────────────────────── macro send/expect/wait ────────────────────────
# DSL rút gọn tham khảo serial-mcp-server (Adancurusul) nhưng bỏ phần lưu file/
# assembly — chỉ giữ 3 loại bước, chạy trực tiếp từ payload HTTP một lần.
MAX_MACRO_STEPS = 20
MAX_MACRO_SECONDS = 120.0
MAX_WAIT_STEP_MS = 5000
MAX_EXPECT_ACCUMULATE = 65536


def normalize_macro_steps(steps):
    """Kiểm & chuẩn hoá toàn bộ macro TRƯỚC khi chạm cổng — dùng chung cho cả
    macro/plan (chỉ xem trước) lẫn macro/run (chạy thật)."""
    if not isinstance(steps, list) or not steps:
        raise ValueError("steps phải là mảng khác rỗng")
    if len(steps) > MAX_MACRO_STEPS:
        raise ValueError(f"Macro tối đa {MAX_MACRO_STEPS} bước")
    normalized = []
    total_budget = 0.0
    for index, raw_step in enumerate(steps):
        if not isinstance(raw_step, dict):
            raise ValueError(f"Bước {index} phải là object")
        kind = raw_step.get("type")
        unknown = sorted(set(raw_step) - {"type", "data", "encoding", "eol", "op", "timeout_ms", "ms"})
        if unknown:
            raise ValueError(f"Bước {index} có trường không hỗ trợ: " + ", ".join(unknown))
        if kind == "send":
            raw = decode_send({"encoding": raw_step.get("encoding", "text"),
                               "data": raw_step.get("data"), "eol": raw_step.get("eol", "none")})
            normalized.append({"type": "send", "raw": raw})
        elif kind == "expect":
            op = raw_step.get("op", "contains")
            if op not in ("contains", "equals"):
                raise ValueError(f"Bước {index}: op phải là contains hoặc equals")
            expected = _decode_bytes(raw_step.get("encoding", "text"), raw_step.get("data"))
            if not expected or len(expected) > MAX_TX_BYTES:
                raise ValueError(f"Bước {index}: dữ liệu mong đợi phải từ 1 đến {MAX_TX_BYTES} byte")
            timeout_ms = raw_step.get("timeout_ms", 1000)
            if (isinstance(timeout_ms, bool) or not isinstance(timeout_ms, (int, float))
                    or not 1 <= timeout_ms <= MAX_WAIT_SECONDS * 1000):
                raise ValueError(f"Bước {index}: timeout_ms phải từ 1 đến {int(MAX_WAIT_SECONDS * 1000)}")
            normalized.append({"type": "expect", "op": op, "expected": expected, "timeout_ms": timeout_ms})
            total_budget += timeout_ms / 1000
        elif kind == "wait":
            ms = raw_step.get("ms")
            if isinstance(ms, bool) or not isinstance(ms, (int, float)) or not 1 <= ms <= MAX_WAIT_STEP_MS:
                raise ValueError(f"Bước {index}: ms phải từ 1 đến {MAX_WAIT_STEP_MS}")
            normalized.append({"type": "wait", "ms": ms})
            total_budget += ms / 1000
        else:
            raise ValueError(f"Bước {index}: type phải là send, expect hoặc wait")
    if total_budget > MAX_MACRO_SECONDS:
        raise ValueError(f"Tổng thời gian khai báo của macro vượt {MAX_MACRO_SECONDS:g}s")
    return normalized


def describe_macro_steps(steps):
    """Bản JSON xem trước — KHÔNG chạm cổng, dùng cho /api/v1/macro/plan."""
    described = []
    for step in steps:
        if step["type"] == "send":
            described.append({"type": "send", "bytes": len(step["raw"]),
                              "hex": step["raw"].hex(" ").upper(),
                              "text_preview": step["raw"].decode("utf-8", "replace")})
        elif step["type"] == "expect":
            described.append({"type": "expect", "op": step["op"], "timeout_ms": step["timeout_ms"],
                              "bytes": len(step["expected"]), "hex": step["expected"].hex(" ").upper(),
                              "text_preview": step["expected"].decode("utf-8", "replace")})
        else:
            described.append({"type": "wait", "ms": step["ms"]})
    return described


MAX_CONCURRENT_CONNECTIONS = 64


class _ApiServer(ThreadingHTTPServer):
    """Giới hạn số kết nối xử lý đồng thời.

    ThreadingHTTPServer gốc tạo MỘT luồng OS cho MỖI kết nối, không có trần.
    /api/v1/events?wait=... là endpoint đọc CÔNG KHAI (cố ý không cần token) —
    tự thực nghiệm mở được 365+ kết nối "treo" (wait=20s) chỉ trong 1.6 giây mà
    không cần biết token gì cả. Không trần thì bất kỳ tiến trình nào trên máy
    (kể cả không ác ý, chỉ là script tự động hoá bị lỗi vòng lặp) cứ mở mãi
    loại kết nối này sẽ sớm muộn ăn hết luồng/RAM, treo hoặc sập luôn cả tiến
    trình — kể cả phần GUI người thợ đang thao tác tay, vì chung một tiến
    trình. Vượt trần thì từ chối ngay ở tầng accept bằng 503, không xếp hàng.
    """
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._slots = threading.Semaphore(MAX_CONCURRENT_CONNECTIONS)

    def process_request(self, request, client_address):
        if not self._slots.acquire(blocking=False):
            _audit.warning("tu choi ket noi qua tai tu %s", client_address)
            body = b'{"error":"too_many_connections","message":"Server dang qua tai, thu lai sau"}'
            try:
                # Gạn bớt dữ liệu request đang chờ đọc trước khi đóng — Windows
                # gửi RST thay vì FIN êm nếu socket còn dữ liệu CHƯA ĐỌC lúc
                # close(), làm phía client (kể cả MCP thật) nhận lỗi socket
                # thô thay vì đọc được mã 503 sạch sẽ.
                request.settimeout(0.2)
                try:
                    request.recv(4096)
                except OSError:
                    pass
                request.sendall(
                    b"HTTP/1.1 503 Service Unavailable\r\n"
                    b"Content-Type: application/json; charset=utf-8\r\n"
                    b"Content-Length: " + str(len(body)).encode("ascii") + b"\r\n"
                    b"Connection: close\r\n\r\n" + body)
                try:
                    request.shutdown(socket.SHUT_WR)
                except OSError:
                    pass
            except OSError:
                pass
            finally:
                try:
                    request.close()
                except OSError:
                    pass
            return
        super().process_request(request, client_address)

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._slots.release()


class SerialDataBridge:
    def __init__(self, host="127.0.0.1", port=8765, max_events=2000,
                 token=None, port_provider=None):
        if host != "127.0.0.1":
            raise ValueError("host phải là 127.0.0.1")
        if isinstance(max_events, bool) or not isinstance(max_events, int) or not 1 <= max_events <= 10000:
            raise ValueError("max_events phải từ 1 đến 10000")
        self.host, self.port = host, int(port)
        self._events = deque(maxlen=max_events)
        self._condition = threading.Condition()
        self._next_seq = 1
        self._session_id = uuid.uuid4().hex
        self._status = {"connected": False, "port": None, "selected": None, "current": None}
        self._started_at = time.time()
        self._server = self._thread = None
        self._token = token or load_or_create_token()
        self._port_provider = port_provider or (lambda: [])
        self._commands = deque()
        self._operations = {}
        self._operation_order = deque(maxlen=100)

    @property
    def token(self):
        """Chỉ dùng nội bộ/kiểm thử; API không công bố token."""
        return self._token

    def record(self, direction, data):
        if direction not in ("rx", "tx"):
            raise ValueError("direction phải là rx hoặc tx")
        raw = bytes(data)
        for offset in range(0, len(raw), MAX_EVENT_BYTES):
            chunk = raw[offset:offset + MAX_EVENT_BYTES]
            if not chunk:
                continue
            with self._condition:
                self._events.append({
                    "seq": self._next_seq, "timestamp": time.time(), "direction": direction,
                    "size": len(chunk), "text": chunk.decode("utf-8", "replace"),
                    "hex": chunk.hex(" ").upper(),
                    "base64": base64.b64encode(chunk).decode("ascii"),
                })
                self._next_seq += 1
                self._condition.notify_all()

    def set_selected(self, port, settings):
        with self._condition:
            self._status["selected"] = {"port": port, "settings": dict(settings)}
            self._condition.notify_all()

    def set_connection(self, connected, port=None, settings=None):
        with self._condition:
            self._status.update({
                "connected": bool(connected), "port": port if connected else None,
                "current": {"port": port, "settings": dict(settings or {})} if connected else None,
            })
            self._condition.notify_all()

    def status(self):
        with self._condition:
            result = json.loads(json.dumps(self._status))
            result.update({
                "api": "OTL Serial Terminal", "api_version": "2.0",
                "session_id": self._session_id,
                "uptime_seconds": round(time.time() - self._started_at, 3),
                "event_count": len(self._events),
                "oldest_seq": self._events[0]["seq"] if self._events else None,
                "latest_seq": self._events[-1]["seq"] if self._events else 0,
                "pending_commands": sum(op["state"] in ("pending", "running")
                                        for op in self._operations.values()),
            })
            return result

    def ports(self):
        rows = list(self._port_provider())
        return {"ports": rows, "count": len(rows)}

    def events(self, after=0, limit=200, direction=None, wait_seconds=0):
        if isinstance(after, bool) or not isinstance(after, int) or after < 0:
            raise ValueError("after phải là số nguyên không âm")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
            raise ValueError("limit phải là số nguyên từ 1 đến 1000")
        wait_seconds = _finite(wait_seconds, "wait")
        if not 0 <= wait_seconds <= MAX_WAIT_SECONDS:
            raise ValueError(f"wait phải từ 0 đến {MAX_WAIT_SECONDS:g} giây")
        if direction is not None and direction not in ("rx", "tx"):
            raise ValueError("direction phải là rx hoặc tx")
        deadline = time.monotonic() + wait_seconds
        with self._condition:
            def matching():
                return any(row["seq"] > after and (direction is None or row["direction"] == direction)
                           for row in self._events)
            while wait_seconds and not matching():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                self._condition.wait(remaining)
            oldest = self._events[0]["seq"] if self._events else None
            latest = self._events[-1]["seq"] if self._events else 0
            rows = [row for row in self._events
                    if row["seq"] > after and (direction is None or row["direction"] == direction)][:limit]
            lost = oldest is not None and after < oldest - 1
            ahead = after > latest
            next_after = rows[-1]["seq"] if rows else latest if (lost or ahead) else after
            return {"session_id": self._session_id, "events": rows, "count": len(rows),
                    "next_after": next_after, "oldest_seq": oldest, "latest_seq": latest,
                    "cursor_lost": lost, "cursor_ahead": ahead}

    def _wait_for_match(self, after_seq, op, expected, timeout_seconds):
        """Gom byte RX kể từ after_seq cho tới khi khớp mẫu hoặc hết hạn.

        Chỉ đọc self._events (đã an toàn đa luồng qua _condition) — KHÔNG đụng
        SerialManager/Tk, nên chạy trên luồng HTTP gọi macro mà không giữ cổng.
        Gộp nhiều khối RX lại trước khi so khớp vì "PONG" có thể về làm hai lần
        đọc tách rời ("PO" rồi "NG") — so khớp từng khối riêng sẽ bỏ lỡ.
        """
        deadline = time.monotonic() + timeout_seconds
        accumulated = bytearray()
        cursor = after_seq
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False, bytes(accumulated), cursor
            result = self.events(after=cursor, direction="rx", wait_seconds=remaining)
            for row in result["events"]:
                accumulated += base64.b64decode(row["base64"])
            if len(accumulated) > MAX_EXPECT_ACCUMULATE:
                del accumulated[:-MAX_EXPECT_ACCUMULATE]
            cursor = result["next_after"]
            matched = (expected in accumulated) if op == "contains" else (bytes(accumulated) == expected)
            if matched:
                return True, bytes(accumulated), cursor

    def run_macro(self, steps, send_timeout_seconds=3.0):
        """Chạy tuần tự send/expect/wait đã được normalize_macro_steps() duyệt.

        CHỈ bước 'send' đi qua submit_command() — dùng lại đúng logic /send đã
        có (qua hàng đợi lệnh, thực thi trên luồng Tk, có write-guard chống
        treo). 'expect'/'wait' không đụng SerialManager nên không cần luồng Tk;
        macro vì vậy không giữ Tk suốt thời gian chờ, chỉ giữ trong từng lần
        gửi ngắn. Dừng NGAY ở bước đầu tiên thất bại — không gửi tiếp lệnh nếu
        bước trước đã sai, tránh bắn lệnh vào thiết bị không phản hồi đúng ý.
        """
        deadline = time.monotonic() + MAX_MACRO_SECONDS
        report = []
        cursor = self.status()["latest_seq"]
        for index, step in enumerate(steps):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                report.append({"index": index, "type": step["type"], "ok": False, "error": "macro_timeout"})
                break
            if step["type"] == "send":
                op = self.submit_command("send", {"data": step["raw"]}, min(send_timeout_seconds, remaining))
                ok = op["state"] == "completed"
                row = {"index": index, "type": "send", "ok": ok, "bytes": len(step["raw"]), "operation": op}
                report.append(row)
                if not ok:
                    break
            elif step["type"] == "wait":
                time.sleep(max(0.0, min(step["ms"] / 1000, remaining)))
                report.append({"index": index, "type": "wait", "ok": True, "ms": step["ms"]})
            else:
                budget = max(0.0, min(step["timeout_ms"] / 1000, remaining))
                matched, seen, cursor = self._wait_for_match(cursor, step["op"], step["expected"], budget)
                report.append({"index": index, "type": "expect", "ok": matched, "op": step["op"],
                               "seen_base64": base64.b64encode(seen).decode("ascii")})
                if not matched:
                    break
        return {"steps": report, "completed": len(report) == len(steps) and all(row["ok"] for row in report)}

    def submit_command(self, name, payload, timeout_seconds=3.0):
        timeout_seconds = _finite(timeout_seconds, "timeout")
        if not 0.05 <= timeout_seconds <= MAX_COMMAND_SECONDS:
            raise ValueError(f"timeout phải từ 0.05 đến {MAX_COMMAND_SECONDS:g} giây")
        now, op_id = time.monotonic(), uuid.uuid4().hex
        operation = {"id": op_id, "name": name, "payload": payload, "state": "pending",
                     "created_at": time.time(), "deadline": now + timeout_seconds,
                     "result": None, "error": None, "http_status": 200}
        with self._condition:
            self._commands = deque(item for item in self._commands
                                   if self._operations.get(item, {}).get("state") == "pending")
            active = sum(op["state"] in ("pending", "running") for op in self._operations.values())
            if active >= 32:
                raise CommandError("command_queue_full", "Hàng đợi điều khiển đang đầy", 503)
            self._operations[op_id] = operation
            self._operation_order.append(op_id)
            self._commands.append(op_id)
            self._prune_locked()
            self._condition.notify_all()
            while operation["state"] in ("pending", "running"):
                remaining = operation["deadline"] - time.monotonic()
                if remaining <= 0:
                    if operation["state"] == "pending":
                        operation.update(state="cancelled",
                                         error={"code": "command_timeout", "message": "Lệnh hết hạn trước khi thực thi"},
                                         http_status=504)
                    break
                self._condition.wait(remaining)
            result = self._public_operation(operation)
        # Ghi audit NGOÀI khoá — không giữ _condition trong lúc ghi file.
        # Không log payload (có thể chứa byte tuỳ ý gửi ra thiết bị), chỉ tên
        # lệnh + kết quả, đủ để dựng lại "ai làm gì lúc nào" khi điều tra sau.
        _audit.info("lenh=%s trang_thai=%s ma_loi=%s", name, result["state"],
                   (result.get("error") or {}).get("code"))
        return result

    def process_commands(self, handler, max_commands=8):
        """Chỉ gọi từ luồng Tk để thực thi lệnh HTTP đang chờ."""
        processed = 0
        while processed < max_commands:
            with self._condition:
                if not self._commands:
                    break
                operation = self._operations.get(self._commands.popleft())
                if not operation or operation["state"] != "pending":
                    continue
                if time.monotonic() >= operation["deadline"]:
                    operation.update(state="cancelled",
                                     error={"code": "command_timeout", "message": "Lệnh hết hạn trước khi thực thi"},
                                     http_status=504)
                    self._condition.notify_all()
                    continue
                operation["state"] = "running"
            try:
                result = handler(operation["name"], operation["payload"], operation["deadline"])
            except CommandError as exc:
                with self._condition:
                    operation.update(state="failed", error={"code": exc.code, "message": str(exc)},
                                     http_status=exc.http_status)
                    self._condition.notify_all()
            except Exception as exc:
                with self._condition:
                    operation.update(state="failed", error={"code": "command_failed", "message": str(exc)},
                                     http_status=500)
                    self._condition.notify_all()
            else:
                with self._condition:
                    operation.update(state="completed", result=result)
                    self._condition.notify_all()
            processed += 1
        return processed

    def operation(self, op_id):
        with self._condition:
            if op_id not in self._operations:
                raise KeyError(op_id)
            return self._public_operation(self._operations[op_id])

    @staticmethod
    def _public_operation(operation):
        return {key: operation[key] for key in
                ("id", "name", "state", "created_at", "result", "error", "http_status")}

    def _prune_locked(self):
        keep = set(self._operation_order)
        for op_id in list(self._operations):
            if op_id not in keep and self._operations[op_id]["state"] not in ("pending", "running"):
                del self._operations[op_id]

    def _authorized(self, header):
        return bool(header and header.startswith("Bearer ") and
                    hmac.compare_digest(header[7:], self._token))

    def start(self):
        bridge = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, _format, *_args):
                return

            def _json(self, value, status=200):
                body = json.dumps(value, ensure_ascii=False).encode("utf-8")
                try:
                    self.send_response(status)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("X-Content-Type-Options", "nosniff")
                    self.end_headers()
                    self.wfile.write(body)
                except OSError:
                    # Client đã đóng kết nối trước khi kịp nhận phản hồi — vd.
                    # bỏ cuộc một GET /events?wait= dài rồi ngắt sớm. Không
                    # phải lỗi cần xử lý, chỉ là client không còn ở đó nữa.
                    pass

            def _error(self, status, code, message):
                self._drain_body()
                self._json({"error": code, "message": message}, status)

            def _drain_body(self):
                """Nuốt nốt body chưa đọc trước khi trả lỗi.

                Từ chối sớm (sai token, sai Origin/Host) mà không đọc body sẽ
                khiến client đang gửi dở nhận connection reset thay vì mã lỗi —
                tác nhân tự động đọc ra thành 'server chết' chứ không phải 401.
                """
                if getattr(self, "_body_done", False):
                    return
                self._body_done = True
                try:
                    remaining = int(self.headers.get("Content-Length") or 0)
                except (TypeError, ValueError):
                    return
                if not 0 < remaining <= MAX_BODY_BYTES:
                    if remaining:
                        self.close_connection = True
                    return
                self.connection.settimeout(2.0)
                try:
                    while remaining > 0:
                        chunk = self.rfile.read(min(remaining, 8192))
                        if not chunk:
                            break
                        remaining -= len(chunk)
                except OSError:
                    self.close_connection = True

            def _validate_host(self):
                raw = (self.headers.get("Host") or "").strip().lower()
                # So khớp NGUYÊN header bằng regex thay vì tự cắt chuỗi bằng
                # rsplit(":", 1) — cách cũ để lọt "127.0.0.1:1;evil" vì phần
                # trước dấu ':' cuối vẫn đúng "127.0.0.1", dù cả header không
                # phải một Host hợp lệ.
                if not _HOST_RE.match(raw):
                    _audit.warning("tu choi host=%r tu %s", raw, self.client_address[0])
                    raise CommandError("invalid_host", "Host phải là loopback", 403)

            def _control(self):
                self._validate_host()
                if self.headers.get("Origin"):
                    _audit.warning("tu choi origin=%r tu %s %s", self.headers.get("Origin"),
                                   self.client_address[0], self.path)
                    raise CommandError("origin_forbidden", "Control API không nhận request từ trình duyệt", 403)
                if not bridge._authorized(self.headers.get("Authorization")):
                    _audit.warning("tu choi token sai tu %s %s", self.client_address[0], self.path)
                    raise CommandError("unauthorized", "Thiếu hoặc sai Bearer token", 401)

            def _body(self):
                if self.headers.get("Content-Length") is None:
                    raise ValueError("Thiếu Content-Length")
                length = int(self.headers["Content-Length"])
                if not 0 <= length <= MAX_BODY_BYTES:
                    raise ValueError(f"Body vượt giới hạn {MAX_BODY_BYTES} byte")
                self.connection.settimeout(2.0)
                self._body_done = True
                raw = self.rfile.read(length)
                value = json.loads(raw.decode("utf-8")) if raw else {}
                if not isinstance(value, dict):
                    raise ValueError("JSON body phải là object")
                return value

            @staticmethod
            def _one(query, key, default):
                values = query.get(key)
                if values is None:
                    return default
                if len(values) != 1:
                    raise ValueError(f"{key} chỉ được xuất hiện một lần")
                return values[0]

            def _respond(self, operation):
                if operation["state"] == "completed":
                    self._json(operation["result"])
                elif operation["state"] in ("pending", "running"):
                    self._json({"operation": operation}, 202)
                else:
                    error = operation["error"]
                    self._error(operation["http_status"], error["code"], error["message"])

            def do_GET(self):
                parsed = urlparse(self.path)
                try:
                    self._validate_host()
                    if parsed.path in ("/", "/api/v1/status"):
                        return self._json(bridge.status())
                    if parsed.path == "/api/v1/ports":
                        return self._json(bridge.ports())
                    if parsed.path == "/api/v1/events":
                        query = parse_qs(parsed.query, keep_blank_values=True)
                        return self._json(bridge.events(
                            int(self._one(query, "after", "0")), int(self._one(query, "limit", "200")),
                            self._one(query, "direction", None),
                            _finite(self._one(query, "wait", "0"), "wait")))
                    if parsed.path == "/api/v1/modem":
                        self._control()
                        return self._respond(bridge.submit_command("modem", {}, 3.0))
                    prefix = "/api/v1/operations/"
                    if parsed.path.startswith(prefix):
                        self._control()
                        return self._json(bridge.operation(parsed.path[len(prefix):]))
                    self._error(404, "not_found", "Không có endpoint này")
                except KeyError:
                    self._error(404, "operation_not_found", "Không có thao tác này")
                except CommandError as exc:
                    self._error(exc.http_status, exc.code, str(exc))
                except (TypeError, ValueError, json.JSONDecodeError) as exc:
                    self._error(400, "invalid_request", str(exc))

            def do_POST(self):
                parsed = urlparse(self.path)
                try:
                    self._control()
                    body = self._body()
                    timeout = body.pop("timeout_seconds", 3.0)
                    if parsed.path == "/api/v1/configure":
                        unknown = sorted(set(body) - {"port", "settings"})
                        if unknown:
                            raise ValueError("Trường configure không hỗ trợ: " + ", ".join(unknown))
                        port = body.get("port")
                        if port is not None and (not isinstance(port, str) or not port.strip() or len(port) > 255):
                            raise ValueError("port không hợp lệ")
                        payload = {"port": port, "settings": normalize_settings(body.get("settings"))}
                        return self._respond(bridge.submit_command("configure", payload, timeout))
                    if parsed.path == "/api/v1/connect":
                        unknown = sorted(set(body) - {"port", "settings"})
                        if unknown:
                            raise ValueError("Trường connect không hỗ trợ: " + ", ".join(unknown))
                        port = body.get("port")
                        if port is not None and (not isinstance(port, str) or not port.strip() or len(port) > 255):
                            raise ValueError("port không hợp lệ")
                        payload = {"port": port, "settings": normalize_settings(body.get("settings"))}
                        return self._respond(bridge.submit_command("connect", payload, timeout))
                    if parsed.path == "/api/v1/disconnect":
                        if body:
                            raise ValueError("disconnect không nhận tham số")
                        return self._respond(bridge.submit_command("disconnect", {}, timeout))
                    if parsed.path == "/api/v1/send":
                        return self._respond(bridge.submit_command("send", {"data": decode_send(body)}, timeout))
                    if parsed.path == "/api/v1/lines":
                        unknown = sorted(set(body) - {"dtr", "rts"})
                        if unknown or not body or any(not isinstance(v, bool) for v in body.values()):
                            raise ValueError("lines chỉ nhận dtr và/hoặc rts dạng boolean")
                        return self._respond(bridge.submit_command("lines", body, timeout))
                    if parsed.path == "/api/v1/macro/plan":
                        unknown = sorted(set(body) - {"steps"})
                        if unknown:
                            raise ValueError("Trường macro/plan không hỗ trợ: " + ", ".join(unknown))
                        normalized = normalize_macro_steps(body.get("steps"))
                        return self._json({"step_count": len(normalized),
                                           "steps": describe_macro_steps(normalized)})
                    if parsed.path == "/api/v1/macro/run":
                        unknown = sorted(set(body) - {"steps", "send_timeout_seconds"})
                        if unknown:
                            raise ValueError("Trường macro/run không hỗ trợ: " + ", ".join(unknown))
                        normalized = normalize_macro_steps(body.get("steps"))
                        send_timeout = _finite(body.get("send_timeout_seconds", 3.0), "send_timeout_seconds")
                        if not 0.05 <= send_timeout <= MAX_COMMAND_SECONDS:
                            raise ValueError(f"send_timeout_seconds phải từ 0.05 đến {MAX_COMMAND_SECONDS:g}")
                        return self._json(bridge.run_macro(normalized, send_timeout))
                    self._error(404, "not_found", "Không có endpoint này")
                except CommandError as exc:
                    self._error(exc.http_status, exc.code, str(exc))
                except (TypeError, ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
                    self._error(400, "invalid_request", str(exc))
                except OSError as exc:
                    self._error(408, "request_timeout", str(exc))

        self._server = _ApiServer((self.host, self.port), Handler)
        self.port = self._server.server_port
        self._thread = threading.Thread(target=self._server.serve_forever,
                                        name="serial-api", daemon=True)
        self._thread.start()

    def stop(self):
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=2)
        self._thread = None
