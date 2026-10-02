# -*- coding: utf-8 -*-
"""Kiểm bt_control_server + MCP otl-bt-sim mà KHÔNG cần cắm phần cứng.

Cách làm: dựng một `App` giả bắt chước đúng phần Tkinter mà server đụng tới —
`after(0, fn)` đẩy việc sang một luồng đóng vai main thread, cộng với các
thuộc tính `sm / dev_bt / playing / bt_offset / opt_port / opt_baud` và ba
phương thức `bump_bt / start_replay / stop_replay`.

    python tools/test_bt_control.py
"""
import json
import os
import queue
import subprocess
import sys
import threading
import urllib.error
import urllib.request

TOOLS = os.path.dirname(os.path.abspath(__file__))
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)
# Đặt token TRƯỚC khi import: serial_terminal_auth cache token ngay lần gọi đầu.
os.environ["OTL_SERIAL_API_TOKEN"] = "t" * 32
import bt_control_server                                   # noqa: E402
from serial_terminal_auth import load_or_create_token      # noqa: E402

CONG = int(os.environ.get("OTL_BT_TEST_PORT") or 8799)
GOC = f"http://127.0.0.1:{CONG}"
_so_loi = 0


def kiem(ten, dieu_kien, chi_tiet=""):
    global _so_loi
    print(("  OK   " if dieu_kien else "  FAIL ") + ten
          + ("  " + str(chi_tiet)[:160] if chi_tiet else ""))
    _so_loi += 0 if dieu_kien else 1


class _Opt:
    def __init__(self, v):
        self.v = v

    def get(self):
        return self.v


class _SM:
    def __init__(self):
        self.mo = True

    def is_open(self):
        return self.mo


class AppGia:
    """Chỉ có đúng những gì `DieuKhienBT` chạm vào — không hơn."""

    def __init__(self):
        self.sm, self.dev_bt, self.playing, self.bt_offset = _SM(), 180.0, False, 0.0
        self.opt_port, self.opt_baud = _Opt("COM3"), _Opt("9600")
        self.viec = queue.Queue()
        self.da_gui = []
        self.mo_cong_loi = None     # đặt chuỗi để giả lập cổng bận

    def after(self, _ms, ham):
        self.viec.put(ham)

    def vong_ui(self):
        while True:
            ham = self.viec.get()
            if ham is None:
                return
            ham()

    def bump_bt(self, deg):
        self.da_gui.append(deg)
        self.dev_bt = round(self.dev_bt + deg, 1)

    def open_port(self, im_lang=False):
        """Bắt chước bản thật: trả câu lỗi khi `im_lang`, None khi mở được."""
        if self.mo_cong_loi:
            return self.mo_cong_loi
        self.sm.mo = True

    def close_port(self):
        self.sm.mo = False

    def start_replay(self):
        self.playing = True

    def stop_replay(self):
        self.playing = False

    def reset_replay(self):
        self.playing = False
        self.bt_offset = 0.0


def goi(duong, than=None, token=None):
    du_lieu = json.dumps(than).encode() if than is not None else None
    tieu_de = {"Authorization": "Bearer " + (token or load_or_create_token())}
    if du_lieu:
        tieu_de["Content-Type"] = "application/json"
    yeu_cau = urllib.request.Request(GOC + duong, data=du_lieu, headers=tieu_de,
                                     method="POST" if du_lieu else "GET")
    try:
        with urllib.request.urlopen(yeu_cau, timeout=5) as tl:
            return tl.status, json.load(tl)
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.load(exc)
        except ValueError:
            return exc.code, {}


def thu_http(app):
    print("— HTTP: đọc trạng thái —")
    ma, than = goi("/api/v1/status")
    kiem("status 200", ma == 200, than)
    kiem("báo đúng COM3 @9600, BT 180",
         than.get("cong") == "COM3" and than.get("baud") == "9600"
         and than.get("bt_thiet_bi") == 180.0)

    print("— HTTP: đặt và dời —")
    ma, than = goi("/api/v1/set", {"bt": 185.5})
    kiem("set 185.5 → lệch +5.5", ma == 200 and than.get("lech") == 5.5, than)
    kiem("app nhận đúng lượng dời", app.da_gui == [5.5], app.da_gui)
    ma, than = goi("/api/v1/nudge", {"deg": -2.5})
    kiem("nudge −2.5 → BT 183.0", ma == 200 and app.dev_bt == 183.0, than)

    print("— HTTP: chặn đầu vào sai —")
    for ten, duong, gui, ma_cho in (
            ("ngoài dải", "/api/v1/set", {"bt": 999}, "ngoai_dai"),
            ("bước quá lớn", "/api/v1/nudge", {"deg": 90}, "buoc_qua_lon"),
            ("thiếu tham số", "/api/v1/set", {}, "thieu_tham_so"),
            ("sai kiểu", "/api/v1/set", {"bt": "nóng"}, "sai_kieu"),
            ("action lạ", "/api/v1/replay", {"action": "bay"}, "hanh_dong_la")):
        ma, than = goi(duong, gui)
        kiem(ten + " bị chặn", ma == 400 and than.get("error") == ma_cho, than)
    ma, than = goi("/api/v1/khong-co-tuyen-nay")
    kiem("tuyến lạ → 404", ma == 404, than)

    print("— HTTP: token —")
    ma, than = goi("/api/v1/status", token="token-sai")
    kiem("token sai → 401", ma == 401 and than.get("error") == "sai_token", than)

    print("— HTTP: replay —")
    ma, _ = goi("/api/v1/replay", {"action": "start"})
    kiem("start → đang replay", ma == 200 and app.playing is True)
    ma, _ = goi("/api/v1/replay", {"action": "stop"})
    kiem("stop → dừng", ma == 200 and app.playing is False)

    print("— HTTP: cổng COM đóng —")
    app.sm.mo = False
    ma, than = goi("/api/v1/set", {"bt": 190})
    kiem("chưa mở cổng → 409", ma == 409 and than.get("error") == "chua_mo_cong", than)
    app.sm.mo = True

    print("— HTTP: mở/đóng cổng COM —")
    app.sm.mo = False
    ma, than = goi("/api/v1/port", {"action": "open"})
    kiem("open → cổng mở", ma == 200 and app.sm.is_open() is True, than)
    ma, than = goi("/api/v1/port", {"action": "open"})
    kiem("open lần hai → báo đã mở sẵn", ma == 200 and than.get("ghi_chu") == "đã mở sẵn", than)
    ma, than = goi("/api/v1/port", {"action": "close"})
    kiem("close → cổng đóng", ma == 200 and app.sm.is_open() is False, than)
    ma, than = goi("/api/v1/port", {"action": "close"})
    kiem("close lần hai → báo đã đóng sẵn", ma == 200 and than.get("ghi_chu") == "đã đóng sẵn", than)
    ma, than = goi("/api/v1/port", {"action": "toang"})
    kiem("action lạ bị chặn", ma == 400 and than.get("error") == "hanh_dong_la", than)
    app.mo_cong_loi = "could not open port COM3: Access is denied."
    ma, than = goi("/api/v1/port", {"action": "open"})
    kiem("cổng bận → 409 mo_cong_that_bai",
         ma == 409 and than.get("error") == "mo_cong_that_bai", than)
    app.mo_cong_loi = None
    goi("/api/v1/port", {"action": "open"})

    print("— HTTP: chưa đọc được BT —")
    cu, app.dev_bt = app.dev_bt, None
    ma, than = goi("/api/v1/set", {"bt": 190})
    kiem("chưa biết BT → 409", ma == 409 and than.get("error") == "chua_biet_bt", than)
    app.dev_bt = cu


def thu_mcp(app):
    print("— MCP: nói chuyện thật qua stdio —")
    moi_truong = {**os.environ, "OTL_BT_API_PORT": str(CONG), "PYTHONIOENCODING": "utf-8"}
    tien_trinh = subprocess.Popen(
        [sys.executable, os.path.join(TOOLS, "mcp_bt_sim", "server.py")],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, env=moi_truong,
        text=True, encoding="utf-8", bufsize=1)

    def rpc(ma, phuong_thuc, tham=None):
        tien_trinh.stdin.write(json.dumps(
            {"jsonrpc": "2.0", "id": ma, "method": phuong_thuc, "params": tham or {}}) + "\n")
        tien_trinh.stdin.flush()
        return json.loads(tien_trinh.stdout.readline())

    try:
        tra = rpc(1, "initialize")
        kiem("initialize", tra["result"]["serverInfo"]["name"] == "otl-bt-sim")
        tra = rpc(2, "tools/list")
        ten = [t["name"] for t in tra["result"]["tools"]]
        kiem("đủ 5 công cụ",
             ten == ["bt_trang_thai", "bt_cong", "bt_dat", "bt_doi", "bt_replay"], ten)
        kiem("ping", rpc(3, "ping").get("result") == {})

        tra = rpc(4, "tools/call", {"name": "bt_trang_thai", "arguments": {}})
        than = json.loads(tra["result"]["content"][0]["text"])
        kiem("bt_trang_thai đọc được BT", than["bt_thiet_bi"] == app.dev_bt, than)

        truoc = app.dev_bt
        tra = rpc(5, "tools/call", {"name": "bt_dat", "arguments": {"bt": 196.0}})
        than = json.loads(tra["result"]["content"][0]["text"])
        kiem("bt_dat 196", than["lech"] == round(196.0 - truoc, 1) and app.dev_bt == 196.0, than)

        rpc(6, "tools/call", {"name": "bt_doi", "arguments": {"deg": -1.5}})
        kiem("bt_doi −1.5 → 194.5", app.dev_bt == 194.5)

        rpc(7, "tools/call", {"name": "bt_replay", "arguments": {"action": "start"}})
        kiem("bt_replay start", app.playing is True)

        rpc(10, "tools/call", {"name": "bt_cong", "arguments": {"action": "close"}})
        kiem("bt_cong close", app.sm.is_open() is False)
        rpc(11, "tools/call", {"name": "bt_cong", "arguments": {"action": "open"}})
        kiem("bt_cong open", app.sm.is_open() is True)

        tra = rpc(8, "tools/call", {"name": "bt_dat", "arguments": {"bt": 999}})
        kiem("lỗi trả về isError + giữ mã",
             tra["result"].get("isError") is True
             and "ngoai_dai" in tra["result"]["content"][0]["text"],
             tra["result"]["content"][0]["text"])

        tra = rpc(9, "tools/call", {"name": "khong_co", "arguments": {}})
        kiem("công cụ lạ → isError", tra["result"].get("isError") is True)
    finally:
        tien_trinh.stdin.close()
        tien_trinh.wait(timeout=10)


def main():
    app = AppGia()
    threading.Thread(target=app.vong_ui, name="ui-gia", daemon=True).start()
    may_chu, cong = bt_control_server.khoi_dong(app, port=CONG)
    if not cong:
        print(f"Không mở được cổng {CONG} — đặt OTL_BT_TEST_PORT sang cổng khác")
        return 2
    try:
        thu_http(app)
        thu_mcp(app)
    finally:
        may_chu.shutdown()
    print(("\n%d PHÉP THỬ HỎNG" % _so_loi) if _so_loi else "\nTẤT CẢ QUA")
    return 1 if _so_loi else 0


if __name__ == "__main__":
    sys.exit(main())
