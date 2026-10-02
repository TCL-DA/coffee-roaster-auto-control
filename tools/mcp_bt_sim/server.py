#!/usr/bin/env python3
"""MCP stdio lái BT Serial Tester đang chạy — giả lập đầu đo BT để test HMI.

Nói chuyện với máy chủ điều khiển nhúng trong app (`tools/bt_control_server.py`),
không tự mở cổng COM: COM là tài nguyên độc quyền, app đang giữ.
"""

import json
import os
import sys
import urllib.error
import urllib.request

TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)
from serial_terminal_auth import load_or_create_token

DEFAULT_PORT = os.environ.get("OTL_BT_API_PORT", "8777")
BASE = (os.environ.get("OTL_BT_API_BASE") or f"http://127.0.0.1:{DEFAULT_PORT}").rstrip("/")
if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

TOOLS = [
    {"name": "bt_trang_thai",
     "description": "Xem BT Serial Tester: cổng COM, baud, BT thiết bị hiện tại, "
                    "có đang phát lại hồ sơ không. Gọi cái này TRƯỚC khi đặt BT.",
     "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "bt_cong",
     "description": "Mở hoặc đóng cổng COM của BT Serial Tester. Gọi `open` trước khi "
                    "đặt BT nếu `bt_trang_thai` báo `cong_mo: false`. Mở sẵn rồi thì "
                    "không sao, trả về ghi chú 'đã mở sẵn'.",
     "inputSchema": {"type": "object", "required": ["action"], "properties": {
         "action": {"type": "string", "enum": ["open", "close"]}},
         "additionalProperties": False}},
    {"name": "bt_dat",
     "description": "Đặt BT giả lập về một giá trị TUYỆT ĐỐI (°C). Dùng để đẩy máy "
                    "qua các mốc rang (Charge/DE/FCs) mà test HMI khỏi đốt lửa. "
                    "Lệch quá 50 °C một lần sẽ bị từ chối — chia nhỏ ra.",
     "inputSchema": {"type": "object", "required": ["bt"], "properties": {
         "bt": {"type": "number", "minimum": 0, "maximum": 300,
                "description": "Nhiệt độ BT muốn đặt, °C"}},
         "additionalProperties": False}},
    {"name": "bt_doi",
     "description": "Dời BT đi một lượng tương đối (°C, âm hoặc dương), tối đa 50 °C "
                    "mỗi lần. Đang phát lại hồ sơ thì cộng vào offset thay vì gửi thẳng.",
     "inputSchema": {"type": "object", "required": ["deg"], "properties": {
         "deg": {"type": "number", "minimum": -50, "maximum": 50}},
         "additionalProperties": False}},
    {"name": "bt_replay",
     "description": "Điều khiển phát lại hồ sơ rang trong BT Serial Tester.",
     "inputSchema": {"type": "object", "required": ["action"], "properties": {
         "action": {"type": "string", "enum": ["start", "stop", "reset"]}},
         "additionalProperties": False}},
]


def goi_api(duong, than=None, timeout=15):
    du_lieu = json.dumps(than).encode("utf-8") if than is not None else None
    tieu_de = {"Authorization": "Bearer " + load_or_create_token()}
    if du_lieu is not None:
        tieu_de["Content-Type"] = "application/json"
    yeu_cau = urllib.request.Request(BASE + duong, data=du_lieu, headers=tieu_de,
                                     method="POST" if du_lieu is not None else "GET")
    try:
        with urllib.request.urlopen(yeu_cau, timeout=timeout) as tra_loi:
            return json.load(tra_loi)
    except urllib.error.HTTPError as exc:
        # Giữ CẢ mã lẫn câu: tác nhân tự động cần mã để rẽ nhánh
        # (chua_mo_cong, chua_biet_bt, buoc_qua_lon), người đọc cần câu.
        try:
            chi_tiet = json.load(exc)
            ma, cau = chi_tiet.get("error"), chi_tiet.get("message") or chi_tiet.get("error")
        except Exception:
            ma, cau = None, str(exc)
        nhan = f"{exc.code} {ma}" if ma else str(exc.code)
        raise RuntimeError(f"BT API HTTP {nhan}: {cau}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Không nối được BT Serial Tester tại {BASE}: {exc}. "
            "Mở app BT Serial Tester lên và Open cổng COM trước.") from exc


def call_tool(name, args):
    args = dict(args or {})
    if name == "bt_trang_thai":
        return goi_api("/api/v1/status")
    if name == "bt_cong":
        return goi_api("/api/v1/port", {"action": args.get("action")})
    if name == "bt_dat":
        return goi_api("/api/v1/set", {"bt": args.get("bt")})
    if name == "bt_doi":
        return goi_api("/api/v1/nudge", {"deg": args.get("deg")})
    if name == "bt_replay":
        return goi_api("/api/v1/replay", {"action": args.get("action")})
    raise ValueError("Không có công cụ: " + name)


def send(message):
    sys.stdout.write(json.dumps(message, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main():
    for dong in sys.stdin:
        dong = dong.strip()
        if not dong:
            continue
        try:
            tin = json.loads(dong)
        except ValueError:
            continue
        ma, phuong_thuc = tin.get("id"), tin.get("method")
        try:
            if phuong_thuc == "initialize":
                ket_qua = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}},
                           "serverInfo": {"name": "otl-bt-sim", "version": "1.0.0"}}
            elif phuong_thuc == "notifications/initialized":
                continue
            elif phuong_thuc == "tools/list":
                ket_qua = {"tools": TOOLS}
            elif phuong_thuc == "ping":
                ket_qua = {}
            elif phuong_thuc == "tools/call":
                tham_so = tin.get("params") or {}
                try:
                    gia_tri = call_tool(tham_so.get("name", ""), tham_so.get("arguments") or {})
                    ket_qua = {"content": [{"type": "text",
                                            "text": json.dumps(gia_tri, ensure_ascii=False, indent=2)}]}
                except Exception as exc:             # noqa: BLE001 — lỗi phải về client, không sập MCP
                    ket_qua = {"content": [{"type": "text", "text": "Lỗi: " + str(exc)}],
                               "isError": True}
            else:
                send({"jsonrpc": "2.0", "id": ma,
                      "error": {"code": -32601, "message": "Method not found"}})
                continue
            if ma is not None:
                send({"jsonrpc": "2.0", "id": ma, "result": ket_qua})
        except Exception as exc:                     # noqa: BLE001
            send({"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": str(exc)}})


if __name__ == "__main__":
    main()
