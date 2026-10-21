#!/usr/bin/env python3
"""MCP stdio điều khiển một phiên OTL Serial Terminal đang chạy."""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)
from serial_terminal_auth import load_or_create_token

DEFAULT_PORT = os.environ.get("OTL_SERIAL_API_PORT", "8765")
BASE = (os.environ.get("OTL_SERIAL_API_BASE") or f"http://127.0.0.1:{DEFAULT_PORT}").rstrip("/")
if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SETTINGS_SCHEMA = {"type": "object", "properties": {
    "baudrate": {"type": "integer", "minimum": 50, "maximum": 4000000},
    "bytesize": {"type": "integer", "enum": [5, 6, 7, 8]},
    "parity": {"type": "string", "enum": ["none", "even", "odd", "mark", "space"]},
    "stopbits": {"type": "number", "enum": [1, 1.5, 2]},
    "xonxoff": {"type": "boolean"}, "rtscts": {"type": "boolean"}, "dsrdtr": {"type": "boolean"},
}, "additionalProperties": False}

TOOLS = [
    {"name": "serial_status", "description": "Xem kết nối, cấu hình được chọn/đang dùng và cursor của phiên.",
     "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "serial_list_ports", "description": "Liệt kê cổng cùng toàn bộ metadata pyserial, không mở cổng.",
     "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "serial_configure", "description": "Chọn cổng/cấu hình; áp dụng trực tiếp nếu cổng đang mở.",
     "inputSchema": {"type": "object", "properties": {"port": {"type": "string"}, "settings": SETTINGS_SCHEMA,
        "timeout_seconds": {"type": "number", "minimum": 0.05, "maximum": 10}}, "additionalProperties": False}},
    {"name": "serial_connect", "description": "Mở cổng bằng cấu hình đã chọn hoặc các giá trị ghi đè.",
     "inputSchema": {"type": "object", "properties": {"port": {"type": "string"}, "settings": SETTINGS_SCHEMA,
        "timeout_seconds": {"type": "number", "minimum": 0.05, "maximum": 10}}, "additionalProperties": False}},
    {"name": "serial_disconnect", "description": "Đóng cổng serial hiện tại.",
     "inputSchema": {"type": "object", "properties": {"timeout_seconds": {"type": "number", "minimum": 0.05, "maximum": 10}},
        "additionalProperties": False}},
    {"name": "serial_send", "description": "Gửi text UTF-8, hex hoặc base64 với EOL tùy chọn; tối đa 4096 byte.",
     "inputSchema": {"type": "object", "required": ["data"], "properties": {
        "encoding": {"type": "string", "enum": ["text", "hex", "base64"], "default": "text"}, "data": {"type": "string"},
        "eol": {"type": "string", "enum": ["none", "lf", "cr", "crlf"], "default": "none"},
        "timeout_seconds": {"type": "number", "minimum": 0.05, "maximum": 10}}, "additionalProperties": False}},
    {"name": "serial_read", "description": "Đọc các khối RX/TX sau seq; kết quả báo cursor_lost/cursor_ahead.",
     "inputSchema": {"type": "object", "properties": {"after": {"type": "integer", "minimum": 0},
        "limit": {"type": "integer", "minimum": 1, "maximum": 1000}, "direction": {"type": "string", "enum": ["rx", "tx"]}},
        "additionalProperties": False}},
    {"name": "serial_wait", "description": "Chờ hữu hạn tối đa 25 giây để nhận khối RX/TX mới.",
     "inputSchema": {"type": "object", "properties": {"after": {"type": "integer", "minimum": 0},
        "timeout_seconds": {"type": "number", "minimum": 0, "maximum": 25},
        "direction": {"type": "string", "enum": ["rx", "tx"]}}, "additionalProperties": False}},
    {"name": "serial_modem_status", "description": "Đọc CD, RI, DSR, CTS, DTR và RTS.",
     "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "serial_set_lines", "description": "Đặt DTR và/hoặc RTS trên cổng đang mở.",
     "inputSchema": {"type": "object", "properties": {"dtr": {"type": "boolean"}, "rts": {"type": "boolean"},
        "timeout_seconds": {"type": "number", "minimum": 0.05, "maximum": 10}}, "additionalProperties": False}},
    {"name": "serial_operation_status", "description": "Kiểm tra lệnh chạy quá timeout mà không gửi lại dữ liệu.",
     "inputSchema": {"type": "object", "required": ["operation_id"], "properties": {
        "operation_id": {"type": "string", "minLength": 1}}, "additionalProperties": False}},
]

MACRO_STEP_SCHEMA = {"type": "object", "required": ["type"], "properties": {
    "type": {"type": "string", "enum": ["send", "expect", "wait"]},
    "encoding": {"type": "string", "enum": ["text", "hex", "base64"], "default": "text"},
    "data": {"type": "string"},
    "eol": {"type": "string", "enum": ["none", "lf", "cr", "crlf"], "default": "none"},
    "op": {"type": "string", "enum": ["contains", "equals"], "default": "contains"},
    "timeout_ms": {"type": "integer", "minimum": 1, "maximum": 25000},
    "ms": {"type": "integer", "minimum": 1, "maximum": 5000},
}, "additionalProperties": False}

TOOLS += [
    {"name": "serial_macro_plan",
     "description": "Duyệt & xem trước chuỗi bước send/expect/wait — KHÔNG chạm cổng serial thật.",
     "inputSchema": {"type": "object", "required": ["steps"], "properties": {
        "steps": {"type": "array", "minItems": 1, "maxItems": 20, "items": MACRO_STEP_SCHEMA}},
        "additionalProperties": False}},
    {"name": "serial_macro_run",
     "description": ("Chạy thật chuỗi bước send/expect/wait trên cổng đang mở. Dừng ngay ở bước đầu "
                     "tiên thất bại. Nên gọi serial_macro_plan trước để xem trước những gì sẽ gửi."),
     "inputSchema": {"type": "object", "required": ["steps"], "properties": {
        "steps": {"type": "array", "minItems": 1, "maxItems": 20, "items": MACRO_STEP_SCHEMA},
        "send_timeout_seconds": {"type": "number", "minimum": 0.05, "maximum": 10}},
        "additionalProperties": False}},
]


def api_request(path, params=None, body=None, timeout=30):
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {"Authorization": "Bearer " + load_or_create_token()}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers,
                                     method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        # Giữ CẢ mã lỗi lẫn câu mô tả: tác nhân tự động cần mã để rẽ nhánh
        # (not_connected, already_connected, partial_write...), người đọc cần câu.
        try:
            detail = json.load(exc)
            code = detail.get("error")
            message = detail.get("message") or code
        except Exception:
            code, message = None, str(exc)
        nhan = f"{exc.code} {code}" if code else str(exc.code)
        raise RuntimeError(f"Serial API HTTP {nhan}: {message}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Không nối được OTL Serial Terminal tại {BASE}: {exc}") from exc


def call_tool(name, args):
    args = dict(args or {})
    if name == "serial_status":
        return api_request("/api/v1/status")
    if name == "serial_list_ports":
        return api_request("/api/v1/ports")
    endpoints = {"serial_configure": "configure", "serial_connect": "connect",
                 "serial_send": "send", "serial_set_lines": "lines", "serial_disconnect": "disconnect"}
    if name in endpoints:
        return api_request("/api/v1/" + endpoints[name], body=args, timeout=15)
    if name in ("serial_read", "serial_wait"):
        params = {"after": args.get("after", 0), "limit": args.get("limit", 200)}
        if args.get("direction"):
            params["direction"] = args["direction"]
        wait = args.get("timeout_seconds", 10) if name == "serial_wait" else 0
        if wait:
            params["wait"] = wait
        return api_request("/api/v1/events", params=params, timeout=float(wait) + 5)
    if name == "serial_modem_status":
        return api_request("/api/v1/modem", timeout=8)
    if name == "serial_operation_status":
        op_id = urllib.parse.quote(str(args.get("operation_id", "")), safe="")
        return api_request("/api/v1/operations/" + op_id)
    if name == "serial_macro_plan":
        return api_request("/api/v1/macro/plan", body={"steps": args.get("steps") or []})
    if name == "serial_macro_run":
        body = {"steps": args.get("steps") or []}
        if args.get("send_timeout_seconds") is not None:
            body["send_timeout_seconds"] = args["send_timeout_seconds"]
        return api_request("/api/v1/macro/run", body=body, timeout=125)
    raise ValueError("Không có công cụ: " + name)


def send(message):
    sys.stdout.write(json.dumps(message, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main():
    for line in sys.stdin:
        try:
            request = json.loads(line)
            method, req_id = request.get("method"), request.get("id")
            if method == "initialize":
                result = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}},
                          "serverInfo": {"name": "otl-serial-terminal", "version": "2.0.0"}}
            elif method == "notifications/initialized":
                continue
            elif method == "tools/list":
                result = {"tools": TOOLS}
            elif method == "tools/call":
                params = request.get("params") or {}
                try:
                    value = call_tool(params.get("name", ""), params.get("arguments") or {})
                    result = {"content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False)}]}
                except Exception as exc:
                    result = {"content": [{"type": "text", "text": "Lỗi: " + str(exc)}], "isError": True}
            elif method == "ping":
                result = {}
            else:
                send({"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": "Method not found"}})
                continue
            if req_id is not None:
                send({"jsonrpc": "2.0", "id": req_id, "result": result})
        except Exception as exc:
            send({"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": str(exc)}})


if __name__ == "__main__":
    main()
