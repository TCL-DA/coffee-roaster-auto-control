# -*- coding: utf-8 -*-
"""Máy chủ điều khiển BT Serial Tester — cho MCP và API lái app từ ngoài.

VÌ SAO phải nằm TRONG app chứ không mở cổng COM riêng: COM3 là tài nguyên
ĐỘC QUYỀN. App đang mở COM3 thì tiến trình thứ hai `serial.Serial('COM3')`
sẽ lỗi `PermissionError`. Nên muốn vừa dùng GUI vừa cho máy lái, chỉ còn một
đường: app giữ cổng, và mở một cửa nhỏ cho bên ngoài gọi vào.

Ràng buộc kỹ thuật: Tkinter KHÔNG an toàn đa luồng. HTTP chạy ở luồng nền,
nên mọi việc đụng tới app đều phải đẩy về luồng chính bằng `app.after(0, …)`
rồi chờ kết quả — đó là việc của `_tren_luong_ui()` bên dưới.

Chỉ nghe trên 127.0.0.1. Cổng mặc định 8777, đổi bằng `OTL_BT_API_PORT`.
Mọi request phải mang `Authorization: Bearer <token>`; token dùng chung với
OTL Serial Terminal (cùng máy, cùng người dùng, cùng phạm vi 127.0.0.1).

    GET  /api/v1/status            → cổng, baud, BT thiết bị, đang replay không
    POST /api/v1/port    {action}  → open | close cổng COM
    POST /api/v1/set     {bt}      → đặt BT về đúng một giá trị tuyệt đối (°C)
    POST /api/v1/nudge   {deg}     → dời BT đi một lượng (°C, âm/dương)
    POST /api/v1/replay  {action}  → start | stop | reset
"""
import json
import os
import queue
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from serial_terminal_auth import load_or_create_token

HOST = "127.0.0.1"          # CHỐT CỨNG: không nhận host từ ngoài vào.
DEFAULT_PORT = 8777
UI_TIMEOUT_S = 5.0
MAX_BODY = 4096

# Trần an toàn. BT Tester chỉ giả lập đầu đo, nhưng firmware thật đang nghe đầu
# kia: một bước nhảy vô lý làm RoR vọt và có thể kích logic cắt gas. Giới hạn
# theo dải nhiệt rang thật của máy, không theo dải số của kiểu dữ liệu.
BT_MIN, BT_MAX = 0.0, 300.0
NUDGE_MAX = 50.0


class _Loi(Exception):
    """Lỗi có mã máy đọc được — HTTP trả đúng mã này cho tác nhân tự động."""

    def __init__(self, ma, cau, http=400):
        super().__init__(cau)
        self.ma, self.cau, self.http = ma, cau, http


class DieuKhienBT:
    """Lớp mỏng bọc quanh `App` — chỗ DUY NHẤT server đụng vào app."""

    def __init__(self, app):
        self.app = app

    def _tren_luong_ui(self, viec):
        """Chạy `viec()` trên luồng Tk rồi trả kết quả về luồng gọi.

        Dùng Queue thay cho biến + Event: Queue đã khoá sẵn, và nó phân biệt
        được 'chưa chạy xong' với 'chạy xong, trả None'.
        """
        hop = queue.Queue(maxsize=1)

        def chay():
            try:
                hop.put(("ok", viec()))
            except Exception as exc:                 # noqa: BLE001 — gói lại để trả về HTTP
                hop.put(("loi", exc))

        self.app.after(0, chay)
        try:
            trang_thai, gia_tri = hop.get(timeout=UI_TIMEOUT_S)
        except queue.Empty:
            raise _Loi("ui_ban", "App không trả lời trong 5 giây", 504) from None
        if trang_thai == "loi":
            raise gia_tri
        return gia_tri

    # ---- đọc ----------------------------------------------------------------

    def trang_thai(self):
        return self._tren_luong_ui(self._trang_thai)

    def _trang_thai(self):
        app = self.app
        return {
            "cong_mo": bool(app.sm.is_open()),
            "cong": app.opt_port.get() if hasattr(app, "opt_port") else None,
            "baud": app.opt_baud.get() if hasattr(app, "opt_baud") else None,
            "bt_thiet_bi": app.dev_bt,
            "dang_replay": bool(app.playing),
            "bu_bt": round(float(app.bt_offset), 1),
        }

    # ---- ghi ----------------------------------------------------------------

    def _doi_hoi_cong_mo(self):
        if not self.app.sm.is_open():
            raise _Loi("chua_mo_cong", "Chưa mở cổng COM trong BT Serial Tester", 409)

    def dat(self, bt):
        """Đặt BT về giá trị tuyệt đối. Quy ra lượng dời rồi gọi `bump_bt`."""
        if not BT_MIN <= bt <= BT_MAX:
            raise _Loi("ngoai_dai", f"bt phải trong {BT_MIN}–{BT_MAX} °C")

        def viec():
            self._doi_hoi_cong_mo()
            hien = self.app.dev_bt
            if hien is None:
                raise _Loi("chua_biet_bt", "Chưa đọc được BT thiết bị — mở cổng "
                                           "và chờ một dòng 'BT:xx.xx' rồi gọi lại", 409)
            lech = round(bt - float(hien), 1)
            if abs(lech) > NUDGE_MAX:
                raise _Loi("buoc_qua_lon", f"Lệch {lech:+.1f} °C vượt trần {NUDGE_MAX} °C "
                                           "một lần; chia nhỏ ra")
            if lech:
                self.app.bump_bt(lech)
            return {"da_dat": bt, "truoc_do": float(hien), "lech": lech}

        return self._tren_luong_ui(viec)

    def doi(self, deg):
        if abs(deg) > NUDGE_MAX:
            raise _Loi("buoc_qua_lon", f"deg vượt trần {NUDGE_MAX} °C một lần")

        def viec():
            self._doi_hoi_cong_mo()
            truoc = self.app.dev_bt
            self.app.bump_bt(deg)
            return {"lech": deg, "truoc_do": truoc, "bt_thiet_bi": self.app.dev_bt}

        return self._tren_luong_ui(viec)

    def cong(self, hanh_dong):
        """Mở/đóng cổng COM — để chạy test HMI không cần người bấm `Open`."""
        if hanh_dong not in ("open", "close"):
            raise _Loi("hanh_dong_la", "action phải là open hoặc close")

        def viec():
            dang_mo = bool(self.app.sm.is_open())
            if hanh_dong == "open":
                if dang_mo:
                    return {"hanh_dong": "open", "cong_mo": True, "ghi_chu": "đã mở sẵn"}
                # ⛔ `im_lang=True`: messagebox là modal, bật từ lệnh gọi máy là
                # treo cứng luồng Tk vì không ai ở đó mà bấm OK.
                loi = self.app.open_port(im_lang=True)
                if loi:
                    raise _Loi("mo_cong_that_bai", loi, 409)
            else:
                if not dang_mo:
                    return {"hanh_dong": "close", "cong_mo": False, "ghi_chu": "đã đóng sẵn"}
                self.app.close_port()
            return {"hanh_dong": hanh_dong, "cong_mo": bool(self.app.sm.is_open())}

        return self._tren_luong_ui(viec)

    def replay(self, hanh_dong):
        ten_ham = {"start": "start_replay", "stop": "stop_replay", "reset": "reset_replay"}
        if hanh_dong not in ten_ham:
            raise _Loi("hanh_dong_la", "action phải là start, stop hoặc reset")

        def viec():
            if hanh_dong == "start":
                self._doi_hoi_cong_mo()
            getattr(self.app, ten_ham[hanh_dong])()
            return {"hanh_dong": hanh_dong, "dang_replay": bool(self.app.playing)}

        return self._tren_luong_ui(viec)


def _so(than, ten, mac_dinh=None):
    gia_tri = than.get(ten, mac_dinh)
    if gia_tri is None:
        raise _Loi("thieu_tham_so", f"thiếu tham số '{ten}'")
    try:
        return float(gia_tri)
    except (TypeError, ValueError):
        raise _Loi("sai_kieu", f"'{ten}' phải là số") from None


def _tao_handler(dieu_khien, token):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        server_version = "OTL-BT-Sim/1.0"

        def log_message(self, *_):
            """Câm. Server chạy trong app GUI, không có console để in ra."""

        # -- hạ tầng --------------------------------------------------------

        def _tra(self, ma_http, than):
            noi_dung = json.dumps(than, ensure_ascii=False).encode("utf-8")
            self.send_response(ma_http)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(noi_dung)))
            self.end_headers()
            self.wfile.write(noi_dung)

        def _kiem_token(self):
            dua_ra = self.headers.get("Authorization", "")
            if not dua_ra.startswith("Bearer ") or dua_ra[7:].strip() != token:
                self._tra(401, {"error": "sai_token", "message": "Thiếu hoặc sai Bearer token"})
                return False
            return True

        def _doc_than(self):
            try:
                dai = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                raise _Loi("than_hong", "Content-Length không hợp lệ") from None
            if dai > MAX_BODY:
                raise _Loi("than_qua_lon", f"Thân request vượt {MAX_BODY} byte", 413)
            if dai <= 0:
                return {}
            try:
                return json.loads(self.rfile.read(dai).decode("utf-8"))
            except (ValueError, UnicodeError):
                raise _Loi("than_hong", "Thân request không phải JSON hợp lệ") from None

        # -- tuyến ----------------------------------------------------------

        def do_GET(self):
            if not self._kiem_token():
                return
            if self.path.split("?")[0] != "/api/v1/status":
                self._tra(404, {"error": "khong_co_tuyen", "message": self.path})
                return
            self._chay(lambda: dieu_khien.trang_thai())

        def do_POST(self):
            if not self._kiem_token():
                return
            duong = self.path.split("?")[0]
            try:
                than = self._doc_than()
            except _Loi as exc:
                self._tra(exc.http, {"error": exc.ma, "message": exc.cau})
                return
            if duong == "/api/v1/set":
                self._chay(lambda: dieu_khien.dat(_so(than, "bt")))
            elif duong == "/api/v1/nudge":
                self._chay(lambda: dieu_khien.doi(_so(than, "deg")))
            elif duong == "/api/v1/replay":
                self._chay(lambda: dieu_khien.replay(than.get("action")))
            elif duong == "/api/v1/port":
                self._chay(lambda: dieu_khien.cong(than.get("action")))
            else:
                self._tra(404, {"error": "khong_co_tuyen", "message": duong})

        def _chay(self, viec):
            try:
                self._tra(200, viec())
            except _Loi as exc:
                self._tra(exc.http, {"error": exc.ma, "message": exc.cau})
            except Exception as exc:                 # noqa: BLE001 — không để sập luồng HTTP
                self._tra(500, {"error": "loi_trong", "message": str(exc)})

    return Handler


def khoi_dong(app, port=None):
    """Bật server ở luồng nền. Trả (server, cổng) hoặc (None, None) nếu hỏng.

    KHÔNG bao giờ được làm sập app: BT Tester là công cụ chính, server điều
    khiển chỉ là tiện ích. Cổng bận (đã mở một bản app khác) thì chịu, bỏ qua.
    """
    if port is None:
        try:
            port = int(os.environ.get("OTL_BT_API_PORT") or DEFAULT_PORT)
        except ValueError:
            port = DEFAULT_PORT
    try:
        token = load_or_create_token()
        server = ThreadingHTTPServer((HOST, port), _tao_handler(DieuKhienBT(app), token))
    except OSError:
        return None, None
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, name="bt-control-api", daemon=True).start()
    return server, port
