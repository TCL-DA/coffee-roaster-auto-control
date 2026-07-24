"""
OTL Roast Lab HMI — vỏ desktop (pywebview) cho giao diện HMI cảm ứng.

Bọc file 'OTL Roast Lab.html' (vanilla HTML/CSS/JS, không framework) thành một
cửa sổ app native trên Windows (dùng WebView2 hệ thống). Phần lõi giao diện nằm
trọn trong file HTML — script này chỉ mở cửa sổ và nạp nó.

Chạy thử:  python tools/roast_lab_hmi.py
Build exe: python -m PyInstaller tools/RoastLabHMI.spec
Phụ thuộc: pip install pywebview   (Windows cần WebView2 runtime — Win10/11 có sẵn)
"""

import configparser
import http.server
import json
import logging
import logging.handlers
import os
import secrets
import shutil
import sys
import threading
import time

import webview

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import otl_link                                  # noqa: E402  (cầu Modbus tới máy rang)
import roast_db                                  # noqa: E402  (kho mẻ SQLite — không mất mẻ)
import auth_otl                                  # noqa: E402  (GĐ2: kiểm PIN phía Python + pepper)
import audit_otl                                 # noqa: E402  (GĐ2: nhật ký hash-chain)
import license_otl                               # noqa: E402  (GĐ2: license Ed25519 khoá theo máy)

# Console của exe (PyInstaller) mặc định codec cp1252 → print tiếng Việt là
# UnicodeEncodeError chết app ngay lúc mở. Ép UTF-8, lỗi thì thay ? — không chết.
for _s in (sys.stdout, sys.stderr):
    try:
        if _s:
            _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

APP_TITLE = "OTL Roast Lab — HMI"
APP_BG = "#0b0e13"          # nền khớp theme tối của HTML, tránh chớp trắng lúc mở
HTML_NAME = "OTL Roast Lab.html"

# ── LOG VẬN HÀNH (operation log) ────────────────────────────────────────────
# MỘT file chung cho cả Python lẫn JS (JS đẩy qua api.op_log): mẻ rang, lệnh
# máy + độ trễ ACK Modbus, đổi trạng thái kết nối, lỗi JS/Python kèm traceback.
# Xoay vòng 2MB × 3 file. Xem trong app: Cài đặt → Log kỹ thuật.
LOG_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                       "OTL Roast Lab HMI", "logs")
LOG_FILE = os.path.join(LOG_DIR, "app.log")
log = logging.getLogger("otl")


def setup_logging():
    os.makedirs(LOG_DIR, exist_ok=True)
    h = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    h.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)-5s %(message)s", datefmt="%d/%m %H:%M:%S"))
    log.addHandler(h)
    log.setLevel(logging.INFO)

    # Crash Python (kể cả trong thread link/web) → ghi traceback vào log rồi
    # mới chết — hết cảnh exe tắt câm không dấu vết như vụ cp1252 sáng 23/07.
    def _hook(t, v, tb):
        log.error("[CRASH] app chết vì exception", exc_info=(t, v, tb))
        sys.__excepthook__(t, v, tb)
    sys.excepthook = _hook
    threading.excepthook = lambda a: log.error(
        "[CRASH] thread %s chết", a.thread.name if a.thread else "?",
        exc_info=(a.exc_type, a.exc_value, a.exc_traceback))


def html_path():
    """Đường dẫn file HTML: khi đóng exe lấy từ bundle (_MEIPASS), khi dev lấy ở gốc repo."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return os.path.join(base, HTML_NAME)
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(here, "..", HTML_NAME))


# ── BUS SỰ KIỆN — trái tim đồng bộ app ↔ web ────────────────────────────────
# Một dòng sự kiện chung: snapshot máy ({'t':'snap'}) + thao tác UI ({'t':'ui'}).
# App nhận qua evaluate_js, web nhận qua SSE /api/stream — cả hai màn cùng ăn
# một nguồn nên lệch nhau chỉ vài ms trên LAN.
class _Bus:
    def __init__(self):
        self._cond = threading.Condition()
        self._q: list[tuple[int, dict]] = []
        self._gen = 0

    def publish(self, evt: dict):
        with self._cond:
            self._gen += 1
            self._q.append((self._gen, evt))
            if len(self._q) > 200:                  # giữ đuôi gần nhất là đủ
                del self._q[:len(self._q) - 200]
            self._cond.notify_all()

    def wait(self, after: int, timeout: float = 15.0):
        """Trả (gen, [sự kiện mới hơn after]) — rỗng nếu hết timeout."""
        with self._cond:
            self._cond.wait_for(lambda: self._gen > after, timeout)
            return self._gen, [e for g, e in self._q if g > after]


BUS = _Bus()


class Api:
    """Cầu nối JS → Python: cửa sổ + dữ liệu live từ máy rang (otl_link).

    ⚠ MỌI thuộc tính phải bắt đầu bằng '_'. pywebview DUYỆT ĐỆ QUY thuộc tính
    công khai của đối tượng này để phơi sang JS; gặp đối tượng cửa sổ .NET nó bò
    vào window.native.AccessibilityObject.Bounds.Empty.Empty… tới khi tràn stack:
        [pywebview] maximum recursion depth exceeded
    JS gọi link_snapshot() mỗi giây → mỗi giây một trận đệ quy → app TREO
    (not responding). Tên bắt đầu bằng '_' được pywebview bỏ qua.
    """

    def __init__(self):
        self._window = None
        self._link = otl_link.RoasterLink()
        self._lk_state = None    # trạng thái link lần trước — đổi mới ghi log, khỏi spam
        self._websrv = None      # server web LAN đang chạy (nút gạt bật/tắt trong menu)
        self.web_cfg = {"bat": True, "cong": 8555, "pin": "1108"}  # [WebServer] trong settings.ini
        self.web_tokens = {}     # token → thời điểm cấp (điện thoại đã nhập đúng PIN web)
        # Kho mẻ SQLite (không mất mẻ) — DB hỏng cũng KHÔNG được chặn app mở
        self._db = None          # RoastDb — None nếu mở thất bại (app vẫn chạy)
        self._db_bid = None      # id mẻ đang RUNNING trong DB
        self._db_t0 = 0.0        # lúc mở mẻ — chặn begin_batch gọi đúp (app + web)
        try:
            self._db = roast_db.RoastDb(os.path.dirname(self._state_path()), log=log.info)
            self._db.backup_daily()
        except Exception:
            log.error("[DB] không mở được kho mẻ — app chạy tiếp KHÔNG ghi mẻ",
                      exc_info=True)
        # GĐ2 — auth phía Python + nhật ký hash-chain. Lỗi cũng không chặn app.
        base = os.path.dirname(self._state_path())
        try:
            self._auth = auth_otl.Auth(base, log=log.info)
        except Exception:
            self._auth = None
            log.error("[AUTH] không khởi tạo được — quay về auth localStorage", exc_info=True)
        try:
            self._audit = audit_otl.AuditLog(base, log=log.info)
        except Exception:
            self._audit = None
        self._session = None      # user đã đăng nhập ở tiến trình Python (nguồn quyền thật)

    # ── chỉ những method dưới đây mới phơi sang JS ──────────────────────────
    def toggle_fullscreen(self):
        if self._window:
            self._window.toggle_fullscreen()

    def app_exit(self):
        """Nút Thoát trong menu người dùng — kiosk cảm ứng không có Alt+F4."""
        log.info("[APP] thoát theo lệnh người dùng")
        if self._window:
            self._window.destroy()
        return True

    def link_snapshot(self):
        """Gói dữ liệu mới nhất + trạng thái kết nối. JS gọi mỗi giây."""
        s = self._link.snapshot()
        st = s.get("state")
        if st != self._lk_state:              # chỉ ghi lúc CHUYỂN trạng thái
            log.log(logging.WARNING if st in ("error", "stalled") else logging.INFO,
                    "[LINK] %s → %s%s%s", self._lk_state or "khởi động", st,
                    " cổng " + s["port"] if s.get("port") else "",
                    " (" + s["err"] + ")" if s.get("err") else "")
            self._lk_state = st
        return s

    # ── "Linh hồn" app (localStorage: tài khoản/theme/lịch sử/cấu hình) ─────
    # App đẩy xuống file state.json; web mở lên MƯỢN nguyên hồn — cùng tài
    # khoản, cùng theme, không còn cảnh trình duyệt đòi "tạo master" riêng.
    def _state_path(self):
        base = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                            "OTL Roast Lab HMI")
        os.makedirs(base, exist_ok=True)
        return os.path.join(base, "state.json")

    def state_save(self, data):
        if not isinstance(data, dict):
            return {"ok": False}
        try:
            path = self._state_path(); tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            os.replace(tmp, path)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "err": str(e)}

    def state_load(self):
        try:
            with open(self._state_path(), encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def ui_event(self, evt):
        """Thao tác UI (chuyển tab, theme, nạp hồ sơ…) từ MỘT màn → phát cho MỌI màn."""
        if not isinstance(evt, dict):
            return {"ok": False}
        BUS.publish({"t": "ui", "cid": str(evt.get("cid", ""))[:24],
                     "fn": str(evt.get("fn", ""))[:32], "args": evt.get("args") or []})
        return {"ok": True}

    def op_log(self, level, tag, msg):
        """JS đẩy sự kiện vận hành vào file log chung (Cài đặt → Log kỹ thuật)."""
        lv = {"WARN": logging.WARNING, "ERROR": logging.ERROR}.get(
            str(level).upper(), logging.INFO)
        log.log(lv, "[%s] %s", tag, msg)
        return True

    def op_tail(self, n=400):
        """Đuôi file log cho viewer trong app (dòng mới nhất ở cuối)."""
        try:
            with open(LOG_FILE, encoding="utf-8", errors="replace") as f:
                return f.readlines()[-int(n):]
        except Exception:
            return []

    def link_config(self):
        return self._link.cfg

    def link_set_config(self, cfg):
        self._link.reconfigure(cfg or {})
        self.ini_write()          # đổi cổng/baud → cập nhật settings.ini
        return self._link.cfg

    def link_ports(self):
        return otl_link.list_serial_ports()

    def link_write(self, name, value):
        """Ghi setpoint / nút ảo. Máy chỉ nhận khi PC control đang BẬT."""
        return self._link.write(name, value)

    def link_new_batch(self):
        """Về mẻ trống — xoá đồng hồ/mốc bên Python. Mẻ DB chưa chốt (bấm Mẻ mới
        giữa chừng) thì đóng INTERRUPTED, không để RUNNING mồ côi."""
        if self._db and self._db_bid is not None:
            try:
                self._db.close_running()
            except Exception:
                log.error("[DB] đóng mẻ dở thất bại", exc_info=True)
            self._db_bid = None
        return self._link.new_batch()

    def link_begin_batch(self, meta=None):
        """Thợ bấm Bắt đầu rang — mở đồng hồ mẻ + chấm mốc từ giây này.

        Mở luôn mẻ mới trong kho SQLite (meta = hồ sơ từ JS). App và web clone
        CÙNG gọi hàm này khi máy vào mẻ (mỗi màn tự phát hiện qua snapshot) →
        trong 20s chỉ nhận lần đầu, các lần sau dùng lại mẻ đang mở."""
        r = self._link.begin_batch()
        if self._db:
            try:
                if self._db_bid is not None and (time.time() - self._db_t0) < 20:
                    pass                          # gọi đúp (màn thứ hai) — dùng mẻ đang mở
                else:
                    self._db_bid = self._db.begin(meta)
                    self._db_t0 = time.time()
                    log.info("[DB] mở mẻ #%s — hồ sơ %s", self._db_bid,
                             (meta or {}).get("name") or "?")
            except Exception:
                log.error("[DB] mở mẻ thất bại — rang vẫn chạy tiếp", exc_info=True)
        return r

    # ── Kho mẻ SQLite (không mất mẻ) — JS gọi qua cầu, web qua /api/* ───────
    def db_batch_finish(self, summary=None):
        """JS chốt mẻ (finishRoast): mã mẻ + tổng kết + mốc. Xong thì backup ngày
        (chạy 16h/ngày nên lúc app mở có thể chưa sang ngày mới)."""
        if not (self._db and self._db_bid is not None):
            return {"ok": False, "err": "không có mẻ đang mở"}
        try:
            r = self._db.finish(self._db_bid, summary)
            log.info("[DB] chốt mẻ #%s %s", self._db_bid,
                     (summary or {}).get("code") or "")
            self._db_bid = None
            self._db.backup_daily()
            return r
        except Exception as e:
            log.error("[DB] chốt mẻ thất bại", exc_info=True)
            return {"ok": False, "err": str(e)}

    def db_batch_list(self, n=50):
        """Danh sách mẻ mới nhất cho tab Lịch sử (app + web đọc chung)."""
        if not self._db:
            return None
        try:
            return self._db.latest(n)
        except Exception:
            log.error("[DB] đọc lịch sử thất bại", exc_info=True)
            return None

    def db_batch_curve(self, bid):
        """Curve 1 mẻ (mảng cột như p.curve) — xem lại / xuất."""
        if not self._db:
            return None
        try:
            return self._db.curve(bid)
        except Exception:
            return None

    def db_batch_stats(self, bid):
        """Thống kê pha 1 mẻ (DTR, dev%, AUC, RoR đỉnh) — GĐ3."""
        if not self._db:
            return None
        try:
            return self._db.stats(bid)
        except Exception:
            log.error("[DB] tính stats thất bại", exc_info=True)
            return None

    def db_batches_curves(self, ids):
        """Curve NHIỀU mẻ để so chồng (GĐ3). Nhận list id, trả {id: curve}."""
        if not self._db:
            return {}
        out = {}
        for bid in (ids or [])[:6]:            # so tối đa 6 mẻ — quá thì rối hình
            try:
                out[str(int(bid))] = self._db.curve(int(bid))
            except Exception:
                pass
        return out

    def db_export_csv(self, bid=None):
        """Xuất CSV vào thư mục hồ sơ (chưa chọn thì cạnh DB): bid=None → bảng
        tổng lich-su-me.csv, bid=N → curve mẻ đó."""
        if not self._db:
            return {"ok": False, "err": "kho mẻ chưa mở"}
        out_dir = self.prof_dir() or os.path.dirname(self._state_path())
        try:
            return self._db.export_csv(out_dir, bid)
        except Exception as e:
            log.error("[DB] xuất CSV thất bại", exc_info=True)
            return {"ok": False, "err": str(e)}

    # ── AUTH (GĐ2 §16.1/16.3) — kiểm PIN phía Python, không tin trình duyệt ──
    def auth_state(self):
        """UI vẽ màn đăng nhập: đã setup master chưa + danh sách user (không hash)."""
        return self._auth.state() if self._auth else {"setup": False, "users": [], "nopy": True}

    def auth_setup_master(self, pin):
        if not self._auth:
            return {"ok": False, "err": "auth Python chưa sẵn sàng"}
        r = self._auth.setup_master(str(pin))
        if r.get("ok"):
            self._session = r["user"]
            self.audit_add("Master", "Tạo", "Tài khoản master", "", "Master")
        return r

    def auth_login(self, name, pin):
        if not self._auth:
            return {"ok": False, "err": "auth Python chưa sẵn sàng"}
        r = self._auth.login(str(name), str(pin))
        if r.get("ok"):
            self._session = r["user"]
            self.audit_add(name, "Đăng nhập", "Phiên", "", name)
        return r

    def auth_verify(self, name, pin):
        """Kiểm PIN cho WEB (điện thoại) — lockout vẫn tính ở Python, nhưng KHÔNG
        chiếm phiên kiosk của app. Web giữ hồ sơ user trong phiên trình duyệt."""
        if not self._auth:
            return {"ok": False, "err": "auth Python chưa sẵn sàng"}
        r = self._auth.login(str(name), str(pin))
        if r.get("ok"):
            self.audit_add(name, "Đăng nhập (web)", "Phiên", "", str(name))
        return r

    def auth_logout(self):
        if self._session:
            self.audit_add(self._session["name"], "Đăng xuất", "Phiên", "", self._session["name"])
        self._session = None
        return {"ok": True}

    def auth_add_operator(self, name, pin, perms=None):
        if not self._is_master():
            return {"ok": False, "err": "chỉ master"}
        r = self._auth.add_operator(name, str(pin), perms or {})
        if r.get("ok"):
            self.audit_add(self._session["name"], "Tạo", "Tài khoản thợ", "", str(name))
        return r

    def auth_set_operator(self, name, perms=None, enabled=None):
        if not self._is_master():
            return {"ok": False, "err": "chỉ master"}
        r = self._auth.set_operator(name, perms, enabled)
        if r.get("ok"):
            self.audit_add(self._session["name"], "Sửa quyền", str(name), "",
                           json.dumps(perms, ensure_ascii=False) if perms is not None
                           else ("bật" if enabled else "khoá"))
        return r

    def auth_del_operator(self, name):
        if not self._is_master():
            return {"ok": False, "err": "chỉ master"}
        r = self._auth.del_operator(name)
        if r.get("ok"):
            self.audit_add(self._session["name"], "Xoá", "Tài khoản thợ", str(name), "")
        return r

    def auth_change_pin(self, name, old_pin, new_pin):
        if not self._auth:
            return {"ok": False, "err": "auth Python chưa sẵn sàng"}
        # thợ chỉ đổi PIN của chính mình; master đổi được của bất kỳ ai (bỏ qua old)
        if self._is_master() and self._session["name"] != name:
            u = self._auth._find(name)
            if u:
                with self._auth._lock:
                    import secrets as _sec
                    u["salt"] = _sec.token_hex(16)
                    u["hash"] = self._auth._hash(str(new_pin), u["salt"])
                    u.pop("legacy", None)
                    self._auth._save()
                self.audit_add(self._session["name"], "Đặt lại PIN", str(name), "", "")
                return {"ok": True}
        r = self._auth.change_pin(str(name), str(old_pin), str(new_pin))
        if r.get("ok"):
            self.audit_add(name, "Đổi PIN", "Tài khoản", "", str(name))
        return r

    def auth_migrate(self, js_users):
        """Di cư tài khoản từ localStorage bản cũ (chỉ khi Python chưa có user)."""
        if not self._auth:
            return {"ok": False, "err": "auth Python chưa sẵn sàng"}
        return self._auth.migrate_from_js(js_users or {})

    def _is_master(self):
        return bool(self._auth and self._session and self._session.get("role") == "master")

    # ── AUDIT hash-chain (GĐ2 §16.3) ───────────────────────────────────────
    def audit_add(self, user, action, field="", old="", new=""):
        if self._audit:
            self._audit.append(user, action, field, old, new)
        return {"ok": True}

    def audit_tail(self, n=200):
        return self._audit.tail(n) if self._audit else []

    def audit_verify(self):
        """Kiểm tính toàn vẹn nhật ký — UI hiện 'nguyên vẹn' / 'đã bị sửa ở dòng N'."""
        return self._audit.verify() if self._audit else {"ok": True, "total": 0, "broken_at": None}

    # ── LICENSE (GĐ2 §16.4) — khoá theo máy, mặc định KHÔNG cưỡng chế ───────
    def license_status(self):
        """Trạng thái license + machine_id (UI hiện ở Cài đặt → Bản quyền)."""
        base = os.path.dirname(self._state_path())
        info = license_otl.verify_file(license_otl.lic_path(base))
        info["may"] = license_otl.machine_id()          # để khách copy gửi người bán
        info["cuong_che"] = bool(self.web_cfg.get("license_enforce"))
        return info

    def _db_point(self, snap):
        """Luồng _snap_bridge gọi mỗi snapshot: đang có mẻ mở + máy nối thật thì
        ghi điểm curve. UI treo cỡ nào điểm vẫn vào DB — đây là chốt 'không mất mẻ'."""
        if not (self._db and self._db_bid is not None):
            return
        if snap.get("state") != "connected" or not snap.get("data"):
            return
        try:
            self._db.point(self._db_bid, snap["data"])
        except Exception:
            log.error("[DB] ghi điểm curve thất bại", exc_info=True)

    def web_toggle(self):
        """Nút gạt web LAN trong menu người dùng — bật/tắt ngay lúc chạy, lưu INI."""
        if self._websrv is not None:                      # đang chạy → TẮT
            srv, self._websrv = self._websrv, None
            def _stop(s):
                try:
                    s.shutdown(); s.server_close()
                except Exception:
                    pass
            threading.Thread(target=_stop, args=(srv,), daemon=True).start()
            self.web_cfg["bat"] = False
            self.ini_write()
            log.info("[WEB] TẮT web LAN theo lệnh người dùng")
            return {"on": False}
        self.web_cfg["bat"] = True                        # đang tắt → BẬT
        self.ini_write()
        start_webserver(self)
        ok = self._websrv is not None
        log.info("[WEB] BẬT web LAN theo lệnh người dùng%s",
                 "" if ok else " — MỞ CỔNG THẤT BẠI")
        return {"on": ok, "err": "" if ok else "không mở được cổng — xem Log kỹ thuật"}

    def web_info(self):
        """IP LAN + cổng web server — app hiện trên thanh trên, chạm để copy."""
        if not self.web_cfg.get("bat", True):
            return {"on": False}
        import socket
        ip = "127.0.0.1"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))          # không gửi gói nào — chỉ để OS chọn IP LAN
            ip = s.getsockname()[0]
            s.close()
        except Exception:
            pass
        return {"on": True, "ip": ip, "port": int(self.web_cfg.get("cong", 8555))}

    # ── Hồ sơ rang lưu ra THƯ MỤC trên máy tính (profiles.json) ────────────
    # localStorage vẫn là cache chạy hằng ngày; thư mục là bản BỀN + di chuyển
    # được (copy qua máy khác, backup). Đường dẫn nhớ trong _cfg_path().

    def _cfg_path(self):
        base = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                            "OTL Roast Lab HMI")
        os.makedirs(base, exist_ok=True)
        return os.path.join(base, "app_config.json")

    def _cfg(self):
        try:
            with open(self._cfg_path(), "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _cfg_save(self, cfg):
        with open(self._cfg_path(), "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=1)

    # ── settings.ini — file config DẠNG CHỮ, mở Notepad sửa được ─────────────
    # Kiểu GameUserSettings.ini: [Section] key=value. INI là NGUỒN SỰ THẬT lúc
    # mở app (sửa tay xong mở app là ăn); app đổi cài đặt thì ghi ngược lại INI.

    def _ini_path(self):
        return os.path.join(os.path.dirname(self._cfg_path()), "settings.ini")

    def ini_write(self):
        """Ghi cài đặt hiện tại ra settings.ini (gọi sau mỗi lần đổi cài đặt)."""
        c = configparser.ConfigParser()
        c["KetNoi"] = {
            "cong": str(self._link.cfg.get("port") or ""),
            "baud": str(self._link.cfg.get("baud") or 9600),
            "dia_chi_may": str(self._link.cfg.get("slave") or 1),
            "bat": "1" if self._link.cfg.get("enabled", True) else "0",
        }
        c["HoSo"] = {"thu_muc": self._cfg().get("prof_dir", "")}
        c["WebServer"] = {
            "bat": "1" if self.web_cfg.get("bat", True) else "0",
            "cong": str(self.web_cfg.get("cong", 8555)),
            "pin_dieu_khien": str(self.web_cfg.get("pin", "1108")),
        }
        # [BanQuyen] cuong_che: 0 (mặc định) = xưởng mình tự dùng, KHÔNG tự chặn.
        # Bản build BÁN cho khách mới đặt 1 để bắt buộc có license đúng máy.
        c["BanQuyen"] = {
            "cuong_che": "1" if self.web_cfg.get("license_enforce") else "0",
        }
        try:
            with open(self._ini_path(), "w", encoding="utf-8") as f:
                f.write("; OTL Roast Lab — file cấu hình. Sửa xong lưu lại rồi mở app.\n")
                c.write(f)
        except Exception:
            pass

    def ini_load(self):
        """Đọc settings.ini lúc mở app — người dùng sửa tay thì INI thắng."""
        p = self._ini_path()
        if not os.path.exists(p):
            self.ini_write()          # lần đầu: tạo sẵn file cho người dùng thấy
            return
        c = configparser.ConfigParser()
        try:
            c.read(p, encoding="utf-8")
        except Exception:
            return
        if c.has_section("KetNoi"):
            k = c["KetNoi"]
            upd = {}
            if k.get("cong"):            upd["port"] = k.get("cong")
            if k.get("baud"):            upd["baud"] = int(k.get("baud") or 9600)
            if k.get("dia_chi_may"):     upd["slave"] = int(k.get("dia_chi_may") or 1)
            upd["enabled"] = k.get("bat", "1") != "0"
            try:
                self._link.reconfigure(upd)
            except Exception:
                pass
        if c.has_section("HoSo"):
            d = c["HoSo"].get("thu_muc", "")
            if d:
                cfg = self._cfg(); cfg["prof_dir"] = d; self._cfg_save(cfg)
        if c.has_section("WebServer"):
            w = c["WebServer"]
            self.web_cfg = {
                "bat":  w.get("bat", "1") != "0",
                "cong": int(w.get("cong", "8555") or 8555),
                "pin":  w.get("pin_dieu_khien", "1108") or "1108",
            }
        if c.has_section("BanQuyen"):
            self.web_cfg["license_enforce"] = c["BanQuyen"].get("cuong_che", "0") != "0"

    def prof_dir(self):
        """Thư mục lưu hồ sơ hiện tại ('' = chưa chọn)."""
        return self._cfg().get("prof_dir", "")

    def prof_dir_pick(self):
        """Mở hộp chọn thư mục Windows → lưu lựa chọn, trả về đường dẫn."""
        if not self._window:
            return ""
        r = self._window.create_file_dialog(webview.FOLDER_DIALOG)
        if not r:
            return self.prof_dir()
        d = r[0] if isinstance(r, (list, tuple)) else r
        cfg = self._cfg(); cfg["prof_dir"] = d; self._cfg_save(cfg)
        self.ini_write()          # đổi thư mục hồ sơ → cập nhật settings.ini
        return d

    def prof_load(self):
        """Đọc profiles.json từ thư mục đã chọn. None = chưa chọn/chưa có file."""
        d = self.prof_dir()
        if not d:
            return None
        try:
            with open(os.path.join(d, "profiles.json"), "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else None
        except Exception:
            return None

    def prof_write_files(self, files):
        """Ghi 1 loạt file text vào thư mục hồ sơ (CSV máy rang / Artisan / index).

        `files` = {tên_file: nội_dung}. Chỉ nhận TÊN file trơn (chặn ../),
        ghi tạm rồi thay để không bao giờ có file cụt.
        """
        d = self.prof_dir()
        if not d:
            return {"ok": False, "err": "chưa chọn thư mục"}
        n = 0
        try:
            for name, content in (files or {}).items():
                name = os.path.basename(str(name))          # chặn path traversal
                if not name:
                    continue
                path = os.path.join(d, name)
                tmp = path + ".tmp"
                with open(tmp, "w", encoding="utf-8", newline="") as f:
                    f.write(content)
                os.replace(tmp, path)
                n += 1
            return {"ok": True, "count": n, "dir": d}
        except Exception as e:
            return {"ok": False, "err": str(e)}

    def prof_export_pdf(self, profiles):
        """Xuất mỗi hồ sơ 1 file PDF vào <thư mục>/pdf/ — phiếu hồ sơ + đồ thị curve.

        Dùng matplotlib (đã có sẵn cho tool mô phỏng). Hồ sơ chưa có curve
        (chưa rang mẻ nào) vẫn ra phiếu thông số, phần đồ thị để trống.
        """
        d = self.prof_dir()
        if not d:
            return {"ok": False, "err": "chưa chọn thư mục"}
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except Exception as e:
            return {"ok": False, "err": "thiếu matplotlib: " + str(e)}
        pdf_dir = os.path.join(d, "pdf")
        os.makedirs(pdf_dir, exist_ok=True)
        n = 0
        try:
            for i, p in enumerate(profiles or []):
                name = str(p.get("name", f"ho-so-{i+1}"))
                safe = "".join(c if c not in '\\/:*?"<>|' else "-" for c in name).strip() or f"ho-so-{i+1}"
                cv = p.get("curve") or {}
                t = cv.get("t") or []

                fig = plt.figure(figsize=(11.7, 8.3))          # A4 ngang
                fig.suptitle(f"{i+1}. {name}", fontsize=18, fontweight="bold")
                meta = (f"Mức rang: {p.get('roast','—')}   ·   Nhiệt charge: {p.get('chargeT','—')}°C   ·   "
                        f"Nhiệt xả: {p.get('temp','—')}°C   ·   Thời gian: {p.get('time','—')}\n"
                        f"Ngày rang: {p.get('date','—')}   ·   Thợ rang: {p.get('roaster','—')}   ·   "
                        f"Ghi chú: {p.get('notes','')}")
                fig.text(0.5, 0.90, meta, ha="center", fontsize=11)

                ax = fig.add_axes([0.07, 0.09, 0.86, 0.72])
                if t:
                    mn = [x / 60.0 for x in t]
                    ax.plot(mn, cv.get("bt") or [], color="#1f77b4", lw=2, label="BT")
                    if cv.get("et"): ax.plot(mn, cv["et"], color="#d62728", lw=1.5, label="ET")
                    ax.set_xlabel("Thời gian (phút)"); ax.set_ylabel("Nhiệt độ (°C)")
                    if cv.get("gas"):
                        ax2 = ax.twinx()
                        ax2.plot(mn, cv["gas"], color="#ff7f0e", lw=1.2, ls="--", label="Gas %")
                        ax2.set_ylabel("Gas (%)"); ax2.set_ylim(0, 105)
                    mile = cv.get("mile") or {}
                    for k in ("TP", "DE", "FCs", "DROP"):
                        s = mile.get(k)
                        if s is not None:
                            ax.axvline(s / 60.0, color="#888", lw=.8, ls=":")
                            ax.text(s / 60.0, ax.get_ylim()[1], k, ha="center", va="bottom", fontsize=9, color="#555")
                    ax.legend(loc="lower right"); ax.grid(alpha=.25)
                else:
                    ax.axis("off")
                    ax.text(.5, .5, "Chưa có dữ liệu mẻ rang (curve)", ha="center", va="center",
                            fontsize=14, color="#999")
                fig.savefig(os.path.join(pdf_dir, f"{i+1} - {safe}.pdf"))
                plt.close(fig)
                n += 1
            return {"ok": True, "count": n, "dir": pdf_dir}
        except Exception as e:
            return {"ok": False, "err": str(e)}

    def prof_save(self, profiles):
        """Ghi danh sách hồ sơ ra <thư mục>/profiles.json (ghi tạm rồi thay — chống hỏng file)."""
        d = self.prof_dir()
        if not d:
            return {"ok": False, "err": "chưa chọn thư mục"}
        try:
            path = os.path.join(d, "profiles.json")
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(profiles, f, ensure_ascii=False, indent=1)
            os.replace(tmp, path)
            return {"ok": True, "path": path}
        except Exception as e:
            return {"ok": False, "err": str(e)}


# ════════════════════════════════════════════════════════════════════════════
# WEB SERVER LAN — điện thoại/tablet cùng WiFi xưởng vào http://<ip-máy-tính>:8555
# Serve ĐÚNG file HTML của app (shim trong HTML tự chuyển pywebview.api → fetch).
# Xem: tự do. ĐIỀU KHIỂN: phải nhập PIN web ([WebServer] pin_dieu_khien trong
# settings.ini) → cấp token 12 giờ. Stdlib thuần, không thêm thư viện.
# ════════════════════════════════════════════════════════════════════════════
WEB_TOKEN_TTL = 12 * 3600


def start_webserver(api):
    if not api.web_cfg.get("bat", True):
        return

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):        # im lặng — khỏi spam console
            pass

        def _json(self, obj, code=200):
            body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _tok_ok(self, tok):
            t = api.web_tokens.get(tok or "")
            return t is not None and (time.time() - t) < WEB_TOKEN_TTL

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                try:
                    with open(html_path(), "rb") as f:
                        body = f.read()
                    # ĐÓNG DẤU web clone — shim trong HTML chỉ bật khi có dấu này
                    body = body.replace(
                        b"<head>",
                        b"<head><script>window._OTL_WEBCLONE=1</script>", 1)
                except Exception as e:
                    self._json({"err": str(e)}, 500); return
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif self.path == "/api/snapshot":
                self._json(api.link_snapshot())
            elif self.path == "/api/config":
                self._json({"port": api._link.cfg.get("port"), "baud": api._link.cfg.get("baud")})
            elif self.path == "/api/oplog":
                self._json({"lines": api.op_tail(400)})
            elif self.path == "/api/ports":
                # danh sách cổng COM CỦA MÁY TÍNH chạy app — web chọn từ xa được
                self._json({"ports": otl_link.list_serial_ports()})
            elif self.path == "/api/state":
                # web mượn "linh hồn" app (tài khoản/theme/…) — LAN nội bộ,
                # PIN trong đó là hash PBKDF2 chứ không phải số trần
                self._json({"state": api.state_load()})
            elif self.path == "/api/profiles":
                # web đọc CHUNG profiles.json với app — Legion/điện thoại thấy đúng
                # hồ sơ thật, không xài bản localStorage riêng của trình duyệt
                self._json({"profiles": api.prof_load()})
            elif self.path == "/api/batches":
                # lịch sử mẻ từ kho SQLite — web xem chung với app (xem tự do)
                self._json({"batches": api.db_batch_list(50)})
            elif self.path == "/api/auth_state":
                # màn đăng nhập web: danh sách user (KHÔNG kèm hash) — xem tự do
                self._json(api.auth_state())
            elif self.path == "/api/audit":
                # nhật ký hash-chain + huy hiệu toàn vẹn (xem tự do)
                self._json({"tail": api.audit_tail(300), "verify": api.audit_verify()})
            elif self.path.startswith("/api/batch_curve?"):
                from urllib.parse import parse_qs, urlparse
                q = parse_qs(urlparse(self.path).query)
                try:
                    bid = int(q.get("id", ["0"])[0])
                except ValueError:
                    bid = 0
                self._json({"curve": api.db_batch_curve(bid)})
            elif self.path.startswith("/api/batch_stats?"):
                from urllib.parse import parse_qs, urlparse
                q = parse_qs(urlparse(self.path).query)
                try:
                    bid = int(q.get("id", ["0"])[0])
                except ValueError:
                    bid = 0
                self._json({"stats": api.db_batch_stats(bid)})
            elif self.path.startswith("/api/batches_curves?"):
                from urllib.parse import parse_qs, urlparse
                q = parse_qs(urlparse(self.path).query)
                ids = [x for x in q.get("ids", [""])[0].split(",") if x]
                self._json({"curves": api.db_batches_curves(ids)})
            elif self.path == "/api/stream":
                # SSE: đẩy snapshot máy + thao tác UI xuống trình duyệt — web nhận
                # cùng nhịp với app, lệch nhau chỉ vài ms
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                after = BUS._gen                    # chỉ nhận từ BÂY GIỜ trở đi
                try:
                    while True:
                        gen, evts = BUS.wait(after, 15.0)
                        if gen == after:            # im ắng → ping giữ kết nối
                            self.wfile.write(b": ping\n\n"); self.wfile.flush()
                            continue
                        after = gen
                        for e in evts:
                            self.wfile.write(
                                ("data: " + json.dumps(e, ensure_ascii=False) + "\n\n")
                                .encode("utf-8"))
                        self.wfile.flush()
                except Exception:
                    return                          # trình duyệt đóng tab — thường thôi
            else:
                self._json({"err": "not found"}, 404)

        def do_POST(self):
            try:
                n = int(self.headers.get("Content-Length") or 0)
                req = json.loads(self.rfile.read(n) or b"{}")
            except Exception:
                self._json({"ok": False, "err": "bad json"}, 400); return

            if self.path == "/api/auth_login":
                # đăng nhập từ web — lockout tính ở Python, KHÔNG chiếm phiên kiosk;
                # đứng TRƯỚC cổng token vì đây chính là bước để có quyền
                self._json(api.auth_verify(req.get("name"), req.get("pin")))
                return
            if self.path == "/api/auth_setup_master":
                self._json(api.auth_setup_master(req.get("pin")))
                return

            if self.path == "/api/pbkdf2":
                # Băm PIN giùm web LAN (trình duyệt cấm crypto.subtle ngoài HTTPS).
                # Chỉ băm — không lộ hash lưu trữ; đứng TRƯỚC cổng token vì đây là
                # bước để đăng nhập.
                import hashlib
                try:
                    h = hashlib.pbkdf2_hmac(
                        "sha256", str(req.get("pin", "")).encode(),
                        bytes.fromhex(str(req.get("salt", ""))), 150000).hex()
                    self._json({"hash": h})
                except Exception as e:
                    self._json({"hash": "", "err": str(e)}, 400)
                return

            if self.path == "/api/weblogin":
                if str(req.get("pin", "")) == str(api.web_cfg.get("pin", "1108")):
                    tok = secrets.token_hex(16)
                    api.web_tokens[tok] = time.time()
                    self._json({"ok": True, "token": tok})
                else:
                    time.sleep(1)                      # hãm dò PIN
                    self._json({"ok": False, "err": "sai PIN"})
                return

            # các lệnh dưới đây ĐỘNG VÀO MÁY → bắt buộc token hợp lệ
            if not self._tok_ok(req.get("token")):
                self._json({"ok": False, "err": "pin"}); return
            if self.path == "/api/oplog":
                self._json({"ok": api.op_log(req.get("level"), req.get("tag") or "WEB",
                                             req.get("msg") or "")})
            elif self.path == "/api/profiles":
                self._json(api.prof_save(req.get("profiles") or []))
            elif self.path == "/api/uievent":
                self._json(api.ui_event(req))
            elif self.path == "/api/set_config":
                # web đổi cổng/baud/slave từ xa (token) — áp thẳng vào cầu Modbus
                self._json({"cfg": api.link_set_config(req.get("cfg") or {})})
            elif self.path == "/api/write":
                self._json(api.link_write(req.get("name"), req.get("value")))
            elif self.path == "/api/new_batch":
                self._json(api.link_new_batch())
            elif self.path == "/api/begin_batch":
                self._json(api.link_begin_batch(req.get("meta")))
            else:
                self._json({"err": "not found"}, 404)

    port = int(api.web_cfg.get("cong", 8555))
    try:
        srv = http.server.ThreadingHTTPServer(("0.0.0.0", port), Handler)
    except OSError as e:
        print(f"[web] không mở được cổng {port}: {e}")
        log.warning("[WEB] không mở được cổng %s: %s", port, e)
        return
    api._websrv = srv            # giữ tham chiếu cho nút gạt bật/tắt
    threading.Thread(target=srv.serve_forever, name="otl-web", daemon=True).start()
    print(f"[web] điện thoại cùng WiFi vào: http://<ip-máy-này>:{port}")
    log.info("[WEB] server LAN chạy — cổng %s", port)


def main():
    setup_logging()
    log.info("[APP] khởi động — %s", "exe" if getattr(sys, "frozen", False) else "dev")
    api = Api()
    # Tự mở FULLSCREEN đúng độ phân giải màn hình hiện tại — hoàn toàn tự động.
    # Phần HTML tự co khung 2560×1440 vừa khít mọi phân giải (fit()).
    # CHỐNG CACHE: WebView2 nhận cờ Chromium qua biến môi trường — tắt hẳn
    # http/disk cache (?v= trên file:// KHÔNG dùng được: ERR_FILE_NOT_FOUND).
    os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = \
        "--disable-http-cache --disk-cache-size=1"
    window = webview.create_window(
        APP_TITLE,
        url=html_path(),
        fullscreen=True,
        width=1680,          # dự phòng nếu môi trường bỏ qua fullscreen
        height=1000,
        background_color=APP_BG,
        js_api=api,
    )
    api._window = window
    api.ini_load()            # settings.ini (sửa tay được) thắng cấu hình đã lưu
    api.ini_write()           # bảo đảm INI có đủ section mới ([WebServer]…) cho người dùng thấy
    api._link.start()         # luồng nền tự dò cổng, tự kết nối lại — không chặn UI
    start_webserver(api)      # điện thoại cùng WiFi vào xem/điều khiển (PIN web)

    # ── Kênh đồng bộ app ↔ web ──────────────────────────────────────────────
    # 1) cầu: snapshot máy mới → đăng lên BUS (chung với sự kiện UI)
    def _snap_bridge():
        gen = 0
        while True:
            gen, snap = api._link.wait_snapshot(gen)
            if snap:
                api._db_point(snap)               # điểm curve vào SQLite (không mất mẻ)
                BUS.publish({"t": "snap", "data": api.link_snapshot()})
    threading.Thread(target=_snap_bridge, name="otl-snapbridge", daemon=True).start()

    # 2) đẩy BUS vào cửa sổ app (web tự nhận qua SSE /api/stream)
    _push_started = []
    def _app_push():
        after = 0
        while True:
            after, evts = BUS.wait(after)
            for e in evts:
                try:
                    window.evaluate_js(
                        "window._rxPush&&_rxPush(" + json.dumps(e, ensure_ascii=False) + ")")
                except Exception:
                    pass                      # cửa sổ đang đóng — bỏ qua
    def _start_push():
        if not _push_started:
            _push_started.append(1)
            threading.Thread(target=_app_push, name="otl-apppush", daemon=True).start()
    window.events.loaded += _start_push
    # QUAN TRỌNG: pywebview mặc định private_mode=True (ẩn danh) → localStorage bị
    # xoá mỗi lần đóng. App lưu PIN/tài khoản/config/nhật ký trong localStorage nên
    # phải TẮT ẩn danh + trỏ thư mục dữ liệu bền trong %LOCALAPPDATA%.
    storage = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                           "OTL Roast Lab HMI")
    # WebView2 (private_mode=False) hay giữ CACHE trang cũ → sửa HTML xong mở app
    # vẫn thấy giao diện cũ. Dọn cache render mỗi lần mở; GIỮ Local Storage
    # (PIN/tài khoản/config nằm ở "Local Storage"/"IndexedDB", không đụng).
    for sub in ("Cache", "Code Cache", "GPUCache", "Service Worker"):
        shutil.rmtree(os.path.join(storage, "EBWebView", "Default", sub),
                      ignore_errors=True)
    webview.start(private_mode=False, storage_path=storage)


if __name__ == "__main__":
    main()
