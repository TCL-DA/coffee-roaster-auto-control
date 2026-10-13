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
import csv
import http.server
import json
import logging
import logging.handlers
import math
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
import inventory_db                              # noqa: E402  (GĐ4: kho nhân/đơn hàng/cupping/chi phí)
import auth_otl                                  # noqa: E402  (GĐ2: kiểm PIN phía Python + pepper)
import otl_apikey                                # noqa: E402  (GĐ B: khoá API có phạm vi cho script/AI)
import audit_otl                                 # noqa: E402  (GĐ2: nhật ký hash-chain)
import license_otl                               # noqa: E402  (GĐ2: license Ed25519 khoá theo máy)
import roast_assistant                           # noqa: E402  (trợ lý, công cụ và quyền thực thi)

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

# ── THƯ MỤC DỮ LIỆU PORTABLE — NẰM CẠNH EXE ─────────────────────────────────
# Lệnh chủ máy 2026-07-25: "exe nằm ở đâu thì mọi dữ liệu nằm ở đó luôn." Một thư
# mục cạnh exe chứa HẾT: settings (app_config.json/settings.ini/state.json),
# batches.db, auth.json, audit.log, .pepper, logs/, backup/, EBWebView/, VÀ kho hồ
# sơ rang (ho-so.csv) + .alog Artisan + pdf/. Copy nguyên folder là chạy máy khác.
# Dev (chạy .py) → tools/appdata/ cho gọn, khỏi rác repo.
def app_data_dir():
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)          # cạnh exe đóng gói
    else:
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "appdata")
    os.makedirs(base, exist_ok=True)
    return base


def migrate_to_portable():
    """Di trú MỘT LẦN từ %LOCALAPPDATA%\\OTL Roast Lab HMI (+ prof_dir CŨ) sang thư
    mục cạnh exe. Chỉ chạy khi thư mục mới CHƯA có app_config.json. KHÔNG xoá nguồn
    cũ (an toàn, còn bản gốc). Phải gọi TRƯỚC khi mở batches.db/logging."""
    new = app_data_dir()
    old = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                       "OTL Roast Lab HMI")
    if os.path.abspath(new) == os.path.abspath(old):
        return
    if os.path.exists(os.path.join(new, "app_config.json")):
        return                                          # đã di trú rồi
    if not os.path.isdir(old):
        return
    old_cfg = {}
    try:
        with open(os.path.join(old, "app_config.json"), encoding="utf-8") as f:
            old_cfg = json.load(f)
    except Exception:
        pass
    # 1) file settings/dữ liệu trong dir cũ → dir mới (không đè nếu đã có)
    for fn in ("state.json", "settings.ini", "batches.db", "auth.json",
               "audit.log", ".pepper", "otl.lic"):
        src, dst = os.path.join(old, fn), os.path.join(new, fn)
        if os.path.exists(src) and not os.path.exists(dst):
            try:
                shutil.copy2(src, dst)
            except Exception:
                pass
    for sub in ("backup", "logs"):
        s, dstd = os.path.join(old, sub), os.path.join(new, sub)
        if os.path.isdir(s) and not os.path.exists(dstd):
            try:
                shutil.copytree(s, dstd)
            except Exception:
                pass
    # 2) hồ sơ CSV/alog/pdf từ prof_dir CŨ (nếu có & khác dir mới)
    old_pdir = (old_cfg.get("prof_dir") or "").strip()
    if old_pdir and os.path.isdir(old_pdir) and os.path.abspath(old_pdir) != os.path.abspath(new):
        for fn in os.listdir(old_pdir):
            src, dst = os.path.join(old_pdir, fn), os.path.join(new, fn)
            try:
                if os.path.isdir(src):
                    if not os.path.exists(dst):
                        shutil.copytree(src, dst)
                elif not os.path.exists(dst):
                    shutil.copy2(src, dst)
            except Exception:
                pass
    # 3) settings.ini mới: xoá thu_muc cũ để prof_dir MẶC ĐỊNH = cạnh exe
    ini_new = os.path.join(new, "settings.ini")
    if os.path.exists(ini_new):
        try:
            c = configparser.ConfigParser()
            c.read(ini_new, encoding="utf-8")
            if c.has_section("HoSo"):
                c["HoSo"]["thu_muc"] = ""
                with open(ini_new, "w", encoding="utf-8") as f:
                    c.write(f)
        except Exception:
            pass
    # 4) app_config.json mới: bỏ prof_dir (mặc định = cạnh exe) — chốt "đã di trú"
    old_cfg.pop("prof_dir", None)
    try:
        with open(os.path.join(new, "app_config.json"), "w", encoding="utf-8") as f:
            json.dump(old_cfg, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


# ── LOG VẬN HÀNH (operation log) ────────────────────────────────────────────
# MỘT file chung cho cả Python lẫn JS (JS đẩy qua api.op_log): mẻ rang, lệnh
# máy + độ trễ ACK Modbus, đổi trạng thái kết nối, lỗi JS/Python kèm traceback.
# Xoay vòng 2MB × 3 file. Xem trong app: Cài đặt → Log kỹ thuật.
LOG_DIR = os.path.join(app_data_dir(), "logs")
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


def asset_path(name):
    """File kèm theo app (icon PWA…): đóng exe thì nằm trong bundle, chạy dev thì nằm cạnh file này."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return os.path.join(base, name)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), name)


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
        # PIN web KHÔNG có giá trị mặc định: rỗng = chưa đặt = KHOÁ hẳn đường web.
        # Trước 2026-09-06 mặc định "1108" — trùng luôn PIN master dùng để test,
        # nên mọi máy giao khách đều mở sẵn cùng một PIN ai cũng đoán được.
        self.web_cfg = {"bat": True, "cong": 8555, "pin": ""}   # [WebServer] trong settings.ini
        self.web_tokens = {}     # token → thời điểm cấp (điện thoại đã nhập đúng PIN web)
        # Token cấp cho MÁY (script/MCP/AI) khi ĐĂNG NHẬP bằng tài khoản app
        # (Master/thợ + PIN) thay vì phải tạo khoá API. token → hồ sơ phiên.
        self.api_sessions = {}
        # Kho mẻ SQLite (không mất mẻ) — DB hỏng cũng KHÔNG được chặn app mở
        self._db = None          # RoastDb — None nếu mở thất bại (app vẫn chạy)
        self._inv = None         # GĐ4 InventoryDb (kho/đơn/cupping) — chung DB với _db
        self._db_bid = None      # id mẻ đang RUNNING trong DB
        self._db_t0 = 0.0        # lúc mở mẻ — chặn begin_batch gọi đúp (app + web)
        self._db_meta = {}       # meta hồ sơ mẻ đang mở (prof_no… — để trừ kho/đơn khi chốt)
        self._lease_gian = None  # lúc bắt đầu đứt liên lạc trong khi có tác nhân lái
        # Khoá API cho MÁY (script/MCP/AI) — khác PIN web vốn dành cho NGƯỜI.
        # Xem docs/plan/plan-mcp-api-extension.md §5 (ba tầng quyền).
        self._apikeys = otl_apikey.ApiKeyStore(app_data_dir(), log=log.info)
        try:
            self._db = roast_db.RoastDb(os.path.dirname(self._state_path()), log=log.info)
            self._db.backup_daily()
            # GĐ4 dùng CHUNG kết nối/khoá/backup với kho mẻ — lỗi cũng không chặn app
            self._inv = inventory_db.InventoryDb(self._db, log=log.info)
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
        self._lease = None        # lượt lái T2 đang mở của tác nhân tự động (None = không có)
        # Mốc mở lượt lái ĐẦU TIÊN của phiên PC control hiện tại. Gia hạn không
        # xoá mốc này — nếu không, "trần 15 phút" chỉ là trần cho MỘT lượt, còn
        # tác nhân cứ xin lại là lái vô tận mà không ai phải đụng vào máy.
        self._lease_phien_t0 = None
        self._control_lock = threading.RLock()
        self._assistant = None

    def _assistant_instance(self):
        with self._control_lock:
            if self._assistant is None:
                self._assistant = roast_assistant.Assistant(self, app_data_dir())
            return self._assistant

    def assistant_action(self, action, payload=None):
        """Cầu desktop; quyền lấy từ phiên Python, không lấy vai trò do JS gửi."""
        if not self._is_master():
            return {"ok": False, "err": "Đăng nhập Master để dùng trợ lý trên máy chủ."}
        return self._assistant_instance().dispatch(action, payload or {}, "desktop", trusted=True)

    # ── chỉ những method dưới đây mới phơi sang JS ──────────────────────────
    def toggle_fullscreen(self):
        if self._window:
            self._window.toggle_fullscreen()

    def app_exit(self):
        """Nút Thoát trong menu người dùng — kiosk cảm ứng không có Alt+F4."""
        if self._assistant:
            self._assistant.pause_all("Ứng dụng đang đóng.")
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
        return os.path.join(app_data_dir(), "state.json")   # portable — cạnh exe

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

    def link_write(self, name, value, ctx=None):
        """Tuần tự hóa lệnh máy; thao tác người vận hành tạm dừng agent trước khi ghi."""
        lock = getattr(self, "_control_lock", None)
        if lock is None:
            # Một số bộ kiểm tạo Api bằng __new__, không mở phần cứng.
            lock = self._control_lock = threading.RLock()
        with lock:
            assistant = getattr(self, "_assistant", None)
            if assistant and (not ctx or ctx.get("kind") != "may"):
                assistant.pause_all("Bạn vừa điều khiển máy; AI tạm dừng. Bấm Tiếp tục khi muốn giao lại.")
            return self._link_write_guarded(name, value, ctx)

    def _link_write_guarded(self, name, value, ctx=None):
        """Ghi setpoint / nút ảo. Máy chỉ nhận khi PC control đang BẬT.

        ctx=None hoặc ctx[kind]==nguoi → THỢ lái (app hoặc web đã nhập PIN):
        giữ nguyên hành vi cũ, không thêm luật nào.
        ctx[kind]==may → TÁC NHÂN TỰ ĐỘNG: phải có lượt lái T2 đang mở."""
        if ctx and ctx.get("kind") == "may":
            # API dùng đơn vị kỹ thuật; không kẹp âm thầm lệnh của tác nhân.
            if not isinstance(name, str) or name not in otl_link.W_INDEX:
                return {"ok": False, "err": "lenh", "msg": "tên lệnh không hợp lệ"}
            scale = otl_link.W_SCALE[name]
            lo, hi = otl_link.W_RANGE[name]
            if (type(value) not in (int, float) or not math.isfinite(value)
                    or not lo <= value * scale <= hi):
                return {"ok": False, "err": "gia_tri",
                        "msg": "%s cần số hữu hạn trong khoảng %g..%g" % (name, lo / scale, hi / scale)}
            tu_choi = self._lease_guard(ctx, name, value)
            if tu_choi:
                return tu_choi
        r = self._link.write(name, value)
        if ctx and ctx.get("kind") == "may" and r.get("ok"):
            self._lease_ghi_so(ctx, name, r)
        return r

    # ── LƯỢT LÁI T2 — tác nhân tự động (AI/script) cầm lái ──────────────────
    #
    # Luật nằm ở ĐÂY, không nằm trong MCP server. Ai viết MCP server khác, hay
    # gọi thẳng bằng curl, thì vẫn phải đi qua đúng bấy nhiêu luật. Luật đặt ở
    # tầng AI là luật tự nguyện — vô nghĩa (§4 kế hoạch).

    # Mặc định ở TẦNG LỚP, không chỉ trong __init__: bộ kiểm dựng Api bằng
    # __new__ để khỏi mở DB/auth/serial, nên thiếu cái này là gãy ngay.
    _lease_phien_t0 = None
    _lease_gian = None            # đồng hồ ân hạn khi đứt liên lạc (xem _lease_guard)
    api_sessions = {}             # phiên đăng nhập API — __init__ thay bằng dict riêng

    def lease_state(self):
        """Trạng thái lượt lái. Cũng là chỗ dọn lượt lái đã rụng ở tầng dưới."""
        ag = self._link.agent_state()
        # Thợ tắt PC control = kết thúc phiên → xoá đồng hồ tổng, lần sau tính lại
        # từ đầu. Đây chính là hành động của CON NGƯỜI mà trần tổng đòi hỏi.
        # Phải thấy cờ pc_control ĐÚNG BẰNG False mới xoá: mất kết nối thoáng qua
        # trả về None/thiếu dữ liệu, mà coi đó là "thợ đã tắt" thì chỉ cần rớt
        # cáp một nhịp là tác nhân được tặng thêm một phiên 60 phút.
        _fl = ((self._link.snapshot().get("data") or {}).get("flags") or {})
        if _fl.get("pc_control") is False:
            self._lease_phien_t0 = None
        L = self._lease
        if L and not ag.get("dang_lai"):
            # tầng link đã tự cắt (hết hạn / im lặng / máy đã về HMI)
            self._lease = None
            log.warning("[LAI] lượt lái của %s đã rụng — %s", L.get("ten"),
                        ag.get("ly_do") or "máy về HMI")
            self.op_log("warn", "LAI", "lượt lái %s rụng: %s"
                        % (L.get("ten"), ag.get("ly_do") or "máy về HMI"))
            L = None
        if not L:
            return {"dang_lai": False, "luat": self._lease_luat()}
        return {"dang_lai": True, "ten": L["ten"], "khoa_id": L["id"],
                "mo_luc": L["t0"], "con_lai_s": ag.get("con_lai_s"),
                "im_lang_s": ag.get("im_lang_s"), "so_lenh": L["n"],
                "luat": self._lease_luat()}

    def _lease_luat(self):
        """Nói RÕ luật cho tác nhân biết đường mà lái, khỏi phải đoán."""
        con = None
        if self._lease_phien_t0 is not None:
            con = max(0, int(LEASE_PHIEN_MAX_S - (time.time() - self._lease_phien_t0)))
        return {"tran_phut": LEASE_MAX_S // 60, "im_lang_toi_da_s": LEASE_STALE_S,
                "lenh_moi_phut": LEASE_RATE_N, "buoc_nhay_toi_da": dict(LEASE_STEP),
                "cam_ghi": list(LEASE_CAM),
                "tran_phien_phut": LEASE_PHIEN_MAX_S // 60,
                "phien_con_lai_s": con,
                "nhip_tinh_tu": "lệnh GHI hoặc lease_beat — ĐỌC trạng thái KHÔNG "
                                "còn tính là nhịp tim (vá 2026-09-09). Đang nghĩ "
                                "lâu thì gọi lease_beat, đừng dựa vào vòng lặp đọc."}

    def _may_san_sang(self):
        """Máy có đang ở thế nhận lệnh từ PC không? Trả (ok, lý do đọc được)."""
        snap = self._link.snapshot()
        if snap.get("state") != "connected":
            return False, ("app chưa nối được máy rang (%s)"
                           % (snap.get("err") or snap.get("state") or "không rõ"))
        d = snap.get("data") or {}
        if not (d.get("flags") or {}).get("pc_control"):
            return False, ("nút PC control trên HMI đang TẮT — thợ phải tự bật "
                           "bằng tay ngay tại tủ máy, không bật được từ xa")
        return True, ""

    def lease_open(self, ctx=None, phut=None):
        """Xin lượt lái. ĐK1 của §5: thợ phải bật PC control BẰNG TAY trên HMI —
        nút đó nằm trên tủ, không có đường bật từ xa, nên chính nó là công tắc
        cho phép tác nhân tự động lái."""
        if not ctx or ctx.get("kind") != "may":
            return {"ok": False, "err": "khong_can",
                    "msg": "lượt lái chỉ dành cho tác nhân tự động; thợ lái app "
                           "thì ghi thẳng, không cần xin"}
        cu = self.lease_state()
        if cu.get("dang_lai") and cu.get("khoa_id") != ctx.get("id"):
            return {"ok": False, "err": "ban",
                    "msg": "đang có tác nhân khác cầm lái: %s" % cu.get("ten")}
        ok, vi_sao = self._may_san_sang()
        if not ok:
            return {"ok": False, "err": "may_chua_san_sang", "msg": vi_sao}
        # TRẦN TỔNG CỦA PHIÊN. Trần 15 phút cũ chỉ chặn MỘT lượt: khoá đang giữ
        # lái gọi lại lease_open là được cấp 15 phút mới ngay, nên tổng thời gian
        # tác nhân tự động cầm máy là vô hạn mà không ai phải có mặt. Nay hết
        # trần phiên thì phải có NGƯỜI tắt/bật lại PC control tại tủ.
        now = time.time()
        if self._lease_phien_t0 is None:
            self._lease_phien_t0 = now
        elif now - self._lease_phien_t0 > LEASE_PHIEN_MAX_S:
            da = int((now - self._lease_phien_t0) // 60)
            return {"ok": False, "err": "het_phien",
                    "msg": "tác nhân tự động đã cầm lái %d phút trong phiên này "
                           "(trần %d phút). Thợ phải tắt rồi bật lại PC control "
                           "trên HMI thì mới xin lái tiếp được."
                           % (da, LEASE_PHIEN_MAX_S // 60)}
        try:
            giay = int(float(phut) * 60) if phut else LEASE_MAX_S
        except (TypeError, ValueError):
            giay = LEASE_MAX_S
        giay = max(60, min(LEASE_MAX_S, giay))
        self._link.agent_open(giay, LEASE_STALE_S)
        self._lease = {"id": ctx.get("id"), "ten": ctx.get("name") or "?",
                       "t0": time.time(), "n": 0, "moc": time.time(),
                       "dem": 0, "cuoi": {}}
        log.warning("[LAI] %s mở lượt lái %d giây — TÁC NHÂN TỰ ĐỘNG CẦM LÁI",
                    ctx.get("name"), giay)
        self.op_log("warn", "LAI", "tác nhân tự động %s bắt đầu lái (%d phút)"
                    % (ctx.get("name"), giay // 60))
        self.audit_add("api:" + str(ctx.get("name")), "lease_open", "", "", str(giay))
        return {"ok": True, **self.lease_state()}

    def lease_touch(self, key_id):
        """Khoá này vừa gọi một đường API bất kỳ = tác nhân còn sống. Gọi từ
        _ctx() nên MỌI request đều tính, khỏi bắt AI nhấp nhịp riêng."""
        if self._lease and self._lease.get("id") == key_id:
            self._link.agent_beat()

    def lease_close(self, ctx=None, ly_do=""):
        """Trả quyền. Thợ (token web) cắt được lượt lái của bất kỳ tác nhân nào."""
        L = self._lease
        if not L:
            return {"ok": True, "msg": "không có lượt lái nào đang mở"}
        if ctx and ctx.get("kind") == "may" and ctx.get("id") != L.get("id"):
            return {"ok": False, "err": "khong_phai_cua_ban",
                    "msg": "lượt lái này của %s" % L.get("ten")}
        self._link.agent_close(ly_do or "trả quyền")
        self._lease = None
        ai = (ctx or {}).get("name") or "hệ thống"
        log.warning("[LAI] %s đóng lượt lái của %s — %s", ai, L.get("ten"),
                    ly_do or "trả quyền")
        self.op_log("info", "LAI", "kết thúc lượt lái %s (%s)"
                    % (L.get("ten"), ly_do or "trả quyền"))
        self.audit_add("api:" + str(ai), "lease_close", "", str(L.get("ten")), ly_do)
        return {"ok": True, "msg": "đã trả quyền về thợ"}

    def _lease_guard(self, ctx, name, value):
        """Tác nhân tự động ghi 1 lệnh — soát đủ điều kiện. Trả None nếu cho đi,
        hoặc dict lỗi CÓ LÝ DO ĐỌC ĐƯỢC (AI đọc mã số thì nó đoán, đọc được lý
        do thì nó xử đúng — xem _cfg_reason trong otl_link.py)."""
        if name in LEASE_CAM:
            return {"ok": False, "err": "cam",
                    "msg": "%s thuộc dây chuyền an toàn — app giữ, tác nhân tự "
                           "động không được ghi" % name}
        st = self.lease_state()
        if not st.get("dang_lai"):
            return {"ok": False, "err": "chua_xin_quyen",
                    "msg": "chưa có lượt lái. Gọi lease_open trước; và thợ phải "
                           "bật PC control trên HMI bằng tay."}
        if st.get("khoa_id") != ctx.get("id"):
            return {"ok": False, "err": "ban",
                    "msg": "tác nhân khác đang cầm lái: %s" % st.get("ten")}
        ok, vi_sao = self._may_san_sang()
        if not ok:
            # ÂN HẠN 3 GIÂY cho đứt liên lạc thoáng qua. Con số 3 không tuỳ tiện:
            # đúng bằng watchdog PC control trong firmware. Nối lại kịp trong đó
            # thì firmware cũng chưa hề nhả quyền, nên giữ lượt lái là đúng sự
            # thật chứ không phải nới lỏng. Quá 3 giây thì firmware đã tự trả
            # quyền về HMI kèm còi — lúc đó đóng hẳn, tác nhân phải xin lại.
            # Thợ TẮT PC control là ý chí con người → đóng ngay, không ân hạn.
            hong_link = "PC control" not in vi_sao
            now = time.time()
            if hong_link:
                if self._lease_gian is None:
                    self._lease_gian = now
                if now - self._lease_gian <= LEASE_AN_HAN_S:
                    return {"ok": False, "err": "link_gian_doan",
                            "msg": "đứt liên lạc với máy %0.1fs — VẪN GIỮ lượt lái, "
                                   "thử lại lệnh này sau một nhịp. Quá %gs mới mất "
                                   "quyền." % (now - self._lease_gian, LEASE_AN_HAN_S)}
            self._lease_gian = None
            self.lease_close(None, vi_sao)
            return {"ok": False, "err": "may_chua_san_sang", "msg": vi_sao}
        self._lease_gian = None            # nối lại rồi → xoá đồng hồ ân hạn

        L = self._lease
        now = time.time()
        if now - L["moc"] >= 60:           # cửa sổ trượt 1 phút
            L["moc"], L["dem"] = now, 0

        buoc = LEASE_STEP.get(name)
        giam = False                       # lệnh này có kéo mức XUỐNG không?
        if buoc is not None:
            try:
                moi = float(value)
            except (TypeError, ValueError):
                return {"ok": False, "err": "gia_tri", "msg": "giá trị không phải số"}
            cu = L["cuoi"].get(name)
            if cu is None:                 # chưa ra lệnh lần nào → lấy mức máy đang chạy
                cu = (self._link.snapshot().get("data") or {}).get(name)
            giam = cu is not None and moi <= float(cu)

        # Chốt tần suất KHÔNG áp cho lệnh kéo mức xuống. Bắt được 12/09/2026:
        # bắn dồn tới hạn quota rồi thì đến gas = 0 cũng bị từ chối — tác nhân
        # tự nhốt mình ngoài cửa đúng lúc cần rút gas nhất. Chốt này sinh ra để
        # chặn tác nhân quậy, không phải để chặn tác nhân dọn dẹp.
        if not giam and L["dem"] >= LEASE_RATE_N:
            return {"ok": False, "err": "qua_nhanh",
                    "msg": "quá %d lệnh trong 1 phút — chờ chút rồi ghi tiếp "
                           "(lệnh GIẢM mức thì không bị chặn)" % LEASE_RATE_N}

        if buoc is not None:
            # CHỈ hãm chiều TĂNG. Trước 12/09/2026 hãm cả hai chiều, nên hạ gas
            # 80 → 0 hay rút gió gấp đều bị từ chối, bắt tác nhân chia 3 lệnh —
            # đúng lúc cần rút nhanh nhất. Chốt này sinh ra để chặn "AI đòi gas 0
            # lên 100 lúc FCs", tức chặn NHIỆT VÀO tăng vọt; chiều giảm là chiều
            # an toàn, chặn nó là quay súng vào chính mình.
            if cu is not None and (moi - float(cu)) > buoc:
                return {"ok": False, "err": "buoc_qua_lon",
                        "msg": "%s đang %g, đòi tăng lên %g — mỗi lệnh chỉ TĂNG "
                               "tối đa %g. Chia nhỏ ra nhiều bước (giảm thì không "
                               "giới hạn)." % (name, float(cu), moi, buoc)}
        return None

    def _lease_ghi_so(self, ctx, name, r):
        """Lệnh đã xuống máy — đếm, nhớ mức, ghi nhật ký (tra khi mẻ hỏng)."""
        L = self._lease
        if not L:
            return
        L["n"] += 1
        L["dem"] += 1
        # Link trả giá trị thanh ghi, còn giới hạn bước dùng °C/kg/%/Pa.
        L["cuoi"][name] = r.get("value") / otl_link.W_SCALE.get(name, 1)
        self.op_log("info", "LAI", "%s = %s (tác nhân %s)"
                    % (name, r.get("value"), ctx.get("name")))
        self.audit_add("api:" + str(ctx.get("name")), "lai_may", name, "",
                       str(r.get("value")))

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
                    self._db_meta = meta or {}       # giữ hồ sơ để trừ kho/đơn lúc chốt
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
        bid = self._db_bid
        try:
            r = self._db.finish(bid, summary)
            log.info("[DB] chốt mẻ #%s %s", bid, (summary or {}).get("code") or "")
            self._inv_on_finish(bid, summary or {})    # GĐ4: trừ kho + tiến độ đơn
            self._db_bid = None
            self._db_meta = {}
            self._db.backup_daily()
            return r
        except Exception as e:
            log.error("[DB] chốt mẻ thất bại", exc_info=True)
            return {"ok": False, "err": str(e)}

    def _inv_on_finish(self, bid, summary):
        """GĐ4 — mẻ chốt xong thì (1) TRỪ KHO lô đang mở, (2) cộng tiến độ ĐƠN.

        Lượng trừ = charge_kg cân thật (JS gửi trong summary nếu có) → không có thì
        định mức mẻ cấu hình (§3.1#1 fallback). Không có lô đang mở / DB lỗi thì
        LẶNG bỏ qua — chuyện kho KHÔNG được cản việc chốt mẻ (§0 an toàn-first)."""
        if not self._inv:
            return
        try:
            cfg = self._inv.cost_config()
            charge = summary.get("charge_kg")
            kg_in = float(charge) if charge not in (None, "") else self._machine_batch_kg()
            if self._inv.hopper_lot(1):              # chỉ trừ khi đã gán lô đang mở
                self._inv.consume_batch(bid, kg_in, user=self._session_name())
            # tiến độ đơn: sản lượng ước lượng = kg vào × (1 − hao hụt định mức).
            # Mẻ GIÁN ĐOẠN (mất kết nối, máy chưa xác nhận xả) không biết ra được bao
            # nhiêu thành phẩm → không cộng đơn; hạt thì đã vào trống nên kho vẫn trừ.
            pno = int(self._db_meta.get("no") or 0)
            if pno > 0 and not summary.get("interrupted"):
                self._inv.order_progress(pno, self._kg_out_uoc(kg_in, cfg), batch_id=bid)
        except Exception:
            log.error("[KHO] móc trừ kho/đơn lúc chốt mẻ lỗi (mẻ vẫn chốt)", exc_info=True)

    @staticmethod
    def _kg_out_uoc(kg_in, cfg):
        """Thành phẩm ước lượng = kg vào × (1 − hao hụt định mức)."""
        shrink = float(cfg.get("hao_hut_dinh_muc_pct") or 15.0)
        return round(kg_in * (1.0 - shrink / 100.0), 2)

    def _inv_rebase(self, bid, kg):
        """Thợ sửa kg sau mẻ → chỉnh kho + đơn theo số thật (review 14/09 RF-05).
        Xoá số (kg=None) = quay về định mức, đúng con số lúc chốt mẻ đã dùng.
        Lỗi kho không được làm hỏng việc ghi kg — chỉ ghi log."""
        if not self._inv:
            return
        try:
            kg_in = float(kg) if kg is not None else self._machine_batch_kg()
            self._inv.rebase_batch(bid, kg_in, self._kg_out_uoc(kg_in, self._inv.cost_config()),
                                   user=self._session_name())
        except Exception:
            log.error("[KHO] chỉnh kho/đơn theo kg mẻ #%s lỗi (kg vẫn ghi)", bid, exc_info=True)

    def _session_name(self):
        return (self._session or {}).get("name", "") if self._session else ""

    # ── GĐ4: KHO NHÂN · ĐƠN HÀNG · CHI PHÍ · CUPPING (§3) ───────────────────
    # Đọc: xem tự do (web GET). Ghi: app trực tiếp / web cần token. Lỗi kho KHÔNG
    # bao giờ nổ ra ngoài — luôn trả dict {"ok":...}/None để UI xử nhẹ nhàng.
    def _machine_batch_kg(self):
        """Định mức kg 1 mẻ (quy số dư lô ra 'còn N mẻ')."""
        if not self._inv:
            return 6.0
        try:
            return float(self._inv.cost_config().get("me_kg_dinh_muc") or 6.0) or 6.0
        except Exception:
            return 6.0

    def inv_lots(self):
        return self._inv.lots_overview(self._machine_batch_kg()) if self._inv else None

    def inv_lot_add(self, d):
        if not self._inv:
            return {"ok": False, "err": "kho chưa mở"}
        d = dict(d or {}); d["user"] = self._session_name()
        r = self._inv.lot_add(d)
        if r.get("ok"):
            self.audit_add(self._session_name(), "Nhập lô", "Kho nhân", "",
                           f"{d.get('name')} {r.get('kg')}kg")
        return r

    def inv_lot_edit(self, lot_id, d):
        return self._inv.lot_edit(lot_id, d) if self._inv else {"ok": False, "err": "kho chưa mở"}

    def inv_lot_adjust(self, lot_id, kg, note=""):
        if not self._inv:
            return {"ok": False, "err": "kho chưa mở"}
        r = self._inv.lot_adjust(lot_id, kg, note, user=self._session_name())
        if r.get("ok"):
            self.audit_add(self._session_name(), "Kiểm kho", f"Lô #{lot_id}", "", f"{kg}kg — {note}")
        return r

    def inv_lot_movements(self, lot_id, n=200):
        return self._inv.lot_movements(lot_id, n) if self._inv else None

    def inv_hopper_lot(self, hopper=1):
        return self._inv.hopper_lot(hopper) if self._inv else None

    def inv_hopper_set(self, lot_id, hopper=1):
        if not self._inv:
            return {"ok": False, "err": "kho chưa mở"}
        r = self._inv.hopper_set(lot_id, hopper, user=self._session_name())
        if r.get("ok"):
            self.audit_add(self._session_name(), "Đổi lô đang mở", f"Phễu {hopper}", "", str(lot_id))
        return r

    def inv_orders(self, status=None, n=100):
        return self._inv.orders_list(status, n) if self._inv else None

    def inv_order_add(self, d):
        return self._inv.order_add(d) if self._inv else {"ok": False, "err": "kho chưa mở"}

    def inv_order_set(self, order_id, d):
        return self._inv.order_set(order_id, d) if self._inv else {"ok": False, "err": "kho chưa mở"}

    def inv_cost_config(self):
        return self._inv.cost_config() if self._inv else None

    def inv_cost_config_set(self, cfg):
        if not self._inv:
            return {"ok": False, "err": "kho chưa mở"}
        r = self._inv.cost_config_set(cfg)
        if r.get("ok"):
            self.audit_add(self._session_name(), "Sửa cấu hình chi phí", "Kinh doanh", "",
                           json.dumps(cfg, ensure_ascii=False)[:120])
        return r

    def inv_batch_econ(self, batch_id, drop_sec=None, kg_out=None):
        return self._inv.batch_economics(batch_id, drop_sec, kg_out) if self._inv else None

    def inv_cup_add(self, d):
        return self._inv.cup_add(d) if self._inv else {"ok": False, "err": "kho chưa mở"}

    def inv_cup_list(self, target=None, target_id=None, n=100):
        return self._inv.cup_list(target, target_id, n) if self._inv else None

    def inv_report(self, days=7):
        """GĐ5 — báo cáo điều hành xưởng N ngày (sản lượng/tồn/lô sắp hết/đơn/lãi)."""
        return self._inv.workshop_report(days) if self._inv else None

    # ── CÀI ĐẶT MÁY (tham số firmware $M1..$M<CFG_MAXIDX>) ───────────────────
    # Lưu/mở FILE cấu hình chạy độc lập (backup/khôi phục/chuyển máy). Đọc/ghi
    # THẲNG xuống máy cần firmware mở khối cấu hình trong PC_Link (nay chỉ chở
    # dữ liệu live) — chưa có thì báo rõ để UI biết, giống cách xử firmware cũ.
    def _mc_path(self):
        d = self.prof_dir() or os.path.dirname(self._state_path())
        return os.path.join(d, "cai-dat-may.json")

    def machine_cfg_save(self, cfg):
        if not isinstance(cfg, dict):
            return {"ok": False, "err": "dữ liệu cấu hình sai"}
        try:
            path = self._mc_path(); tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=1)
            os.replace(tmp, path)
            log.info("[MÁY] lưu cấu hình máy → %s (%d tham số)", path, len(cfg))
            return {"ok": True, "path": path}
        except Exception as e:
            return {"ok": False, "err": str(e)}

    def machine_cfg_load(self):
        try:
            with open(self._mc_path(), encoding="utf-8") as f:
                return {"ok": True, "cfg": json.load(f)}
        except FileNotFoundError:
            return {"ok": False, "err": "chưa có file cai-dat-may.json"}
        except Exception as e:
            return {"ok": False, "err": str(e)}

    def mc_read(self, items=None):
        """Đọc tham số $M TỪ MÁY qua handshake PC_Link.
        items = [[key, idx], ...] (idx = số $M). Trả {ok, cfg:{key:val}, failed:[key]}.
        App mở tab Cài đặt máy gọi 1 lần cho CẢ KHỐI $M (1..CFG_MAXIDX, mỗi cái 1
        vòng hỏi-đáp). Số lượng lấy từ bản đồ PC_Link sinh sẵn, không ghi cứng —
        firmware mở thêm $M là chỗ này tự theo."""
        if items is None:
            items = [["M%d" % idx, idx] for idx in range(1, otl_link.CFG_MAXIDX + 1)]
        if not isinstance(items, list):
            return {"ok": False, "err": "thiếu danh sách tham số"}
        cfg, failed = {}, []
        for it in items:
            try:
                key, idx = it[0], int(it[1])
            except Exception:
                continue
            r = self._link.cfg_op(1, idx)          # 1 = đọc
            if r.get("ok"):
                cfg[key] = r.get("val")
            else:
                failed.append(key)
                if r.get("err", "").startswith("máy chưa nạp"):
                    return {"ok": False, "err": r["err"]}   # dừng sớm nếu máy không có PC_Link
        return {"ok": bool(cfg), "cfg": cfg, "failed": failed,
                "err": "" if cfg else "không đọc được tham số nào"}

    # $M lái TRỰC TIẾP lửa, nhiệt hoặc cơ cấu. Khối cấu hình chạy ĐỘC LẬP PC
    # control (PC_Link.h), nên trước 2026-09-09 một khoá chỉ có phạm vi `config`
    # đổi được trần gas tuyệt đối ($M28), gas mồi ($M8) hay nhiệt nạp ($M23) mà
    # không cần thợ bật PC control, không cần lượt lái, không ai đứng cạnh máy —
    # rồi mẻ sau thợ rang tay theo tham số đã bị đổi. Đó là leo quyền thật sự:
    # ảnh hưởng vật lý mà không đi qua cổng nào của tầng điều khiển.
    # Nay nhóm này đòi thêm phạm vi `control`. Nhóm còn lại (ID slave, thang đo
    # cảm biến, ngưỡng cân, kho…) vẫn chỉ cần `config` như cũ.
    M_CAN_CONTROL = {
        1, 2, 3,        # xi-lanh nạp / xả / thoát
        4, 5, 31,       # trần bậc tăng gas AUTO (trước DE, DE→FCs, sau FCs)
        7,              # nhiệt vận hành afterburner (đầu đốt thứ hai)
        8,              # gas mồi lúc charge
        9,              # nhiệt bật gas chính
        10, 23,         # nhiệt nạp mẻ + dung sai
        20, 21,         # mốc DE / FCs — đổi là đổi cả đường gas AUTO
        24,             # SV BT ghi xuống bộ điều khiển nhiệt
        28,             # TRẦN GAS TUYỆT ĐỐI — hệ số nhân của DAC gas
        29,             # loại đầu đốt (đổi cả tham số preheat)
        34, 35,         # tốc độ trống / gió chế độ tay
        36,             # đặt gas thủ công
        37,             # tự cắt lửa khi kết thúc
        51, 52,         # preheat: thời gian + nhiệt đích
        54, 55, 56,     # preheat PID: thời hạn, ổn định, dải mục tiêu
        58, 59, 60,     # auto-drop tối thiểu, Escape bổ sung, timeout cửa Drop
    }

    def mc_write(self, items, ctx=None):
        """Ghi tham số $M XUỐNG MÁY qua handshake PC_Link.
        items = [[key, idx, val], ...]. Ghi bị CHẶN phía firmware khi đang rang.
        Trả {ok, count, failed:[key]}. Dùng cho 'Ghi tất cả' và auto-ghi từng ô."""
        # Kiểm toàn bộ yêu cầu trước khi ghi để không áp dụng nửa danh sách lỗi.
        if not isinstance(items, list) or not 1 <= len(items) <= otl_link.CFG_MAXIDX:
            return {"ok": False, "err": "cần danh sách từ 1 đến %d tham số" % otl_link.CFG_MAXIDX}
        seen = set()
        for it in items:
            if (not isinstance(it, (list, tuple)) or len(it) != 3
                    or not isinstance(it[0], str) or not it[0]
                    or type(it[1]) is not int or not 1 <= it[1] <= otl_link.CFG_MAXIDX
                    or type(it[2]) is not int or not 0 <= it[2] <= 65535
                    or it[1] in seen):
                return {"ok": False, "err": "tham số không hợp lệ: cần [tên, số $M, số nguyên 0..65535], không lặp $M"}
            lo, hi = otl_link.CFG_RANGE[it[1]]
            if lo > hi or not lo <= it[2] <= hi:
                return {"ok": False, "err": "M%d cần số nguyên thô trong khoảng %d..%d" % (it[1], lo, hi)}
            seen.add(it[1])
        if ctx is not None and ctx.get("kind") == "may":
            nguy = sorted({it[1] for it in items if it[1] in self.M_CAN_CONTROL})
            if nguy and "control" not in (ctx.get("scopes") or []):
                return {"ok": False, "err": "pham_vi",
                        "msg": "M%s lái trực tiếp lửa/nhiệt/cơ cấu nên cần thêm "
                               "phạm vi 'control', không chỉ 'config'."
                               % ", M".join(str(x) for x in nguy)}
        count, failed, errors = 0, [], {}
        for key, idx, val in items:
            r = self._link.cfg_op(2, idx, val)
            if ctx is not None:
                self.audit_add("api:" + str(ctx.get("name", "")), "mc_write",
                               "M%d" % idx, "", json.dumps({"value": val, "result": r}, ensure_ascii=False))
            if r.get("ok"):
                count += 1
            else:
                failed.append(key)
                errors[key] = r.get("err") or "firmware từ chối"
                # Dừng khi máy từ chối; không tiếp tục các lệnh còn lại.
                break
        return {"ok": count == len(items), "count": count, "failed": failed,
                "errors": errors, "not_attempted": [it[0] for it in items[count + len(failed):]],
                "err": next(iter(errors.values()), "")}

    def db_batch_list(self, n=50, query="", date_from="", date_to="", offset=0):
        """Danh sách mẻ mới nhất cho tab Lịch sử (app + web đọc chung)."""
        if not self._db:
            return None
        try:
            return self._db.latest(n, query, date_from, date_to, offset)
        except Exception:
            log.error("[DB] đọc lịch sử thất bại", exc_info=True)
            return None

    def db_batch_count(self, query="", date_from="", date_to=""):
        """Tổng số mẻ khớp bộ lọc — giao diện cần để ghi \"N mẻ đã lưu\"."""
        if not self._db:
            return None
        try:
            return self._db.count(query, date_from, date_to)
        except Exception:
            log.error("[DB] đếm mẻ thất bại", exc_info=True)
            return None

    def db_batch_set_weight(self, bid, kg):
        """Ghi khối lượng nạp (kg) do thợ nhập cho một mẻ. kg rỗng = xoá.
        Ghi xong thì chỉnh luôn kho + tiến độ đơn cho khớp số thật — trước đây chỉ
        sửa cột batches.charge_kg nên lịch sử ghi 3 kg mà kho vẫn trừ 6 kg."""
        if not self._db:
            return False
        try:
            kg_so = None if kg in ("", None) else float(kg)
            ok = self._db.set_weight(bid, kg_so)
        except ValueError:
            return False
        except Exception:
            log.error("[DB] ghi khối lượng thất bại", exc_info=True)
            return False
        if ok:
            self._inv_rebase(bid, kg_so)
        return ok

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
    # ── Khoá API (GĐ B) ────────────────────────────────────────────────────
    def apikey_list(self):
        return {"ok": True, "keys": self._apikeys.list(), "scopes": list(otl_apikey.SCOPES)}

    def apikey_add(self, name, scopes):
        """Chỉ MASTER được tạo khoá: khoá 'control' lái được gas/nạp/xả."""
        if not self._is_master():
            return {"ok": False, "err": "chỉ tài khoản master được tạo khoá API"}
        return self._apikeys.add(name, scopes)

    def apikey_del(self, key_id):
        if not self._is_master():
            return {"ok": False, "err": "chỉ tài khoản master được xoá khoá API"}
        return self._apikeys.delete(key_id)

    def apikey_toggle(self, key_id, on):
        if not self._is_master():
            return {"ok": False, "err": "chỉ tài khoản master được khoá/mở khoá API"}
        return self._apikeys.set_enabled(key_id, on)

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

    # ── mở khoá MÀN HÌNH APP từ xa (API/MCP) ────────────────────────────────
    # Hai phiên khác nhau: token API là cửa cho script, còn màn khoá trong cửa sổ
    # app là phiên của NGƯỜI. Trước 12/09/2026 hai thứ đó không nối nhau, nên
    # đăng nhập bằng API xong nhìn lên màn hình vẫn thấy màn khoá — đúng về mặt
    # kỹ thuật nhưng vô lý với người đứng ở máy. Nay đăng nhập API mở khoá luôn
    # màn hình, vì PIN dùng để mở màn hình CHÍNH LÀ PIN vừa nhập.
    def ui_mo_khoa(self, user):
        w = getattr(self, "_window", None)
        if not w:
            return False
        try:
            r = w.evaluate_js("window.otlRemoteLogin&&otlRemoteLogin(%s)"
                              % json.dumps(user, ensure_ascii=False))
            return bool(r)
        except Exception:
            log.warning("[API] không đẩy được lệnh mở khoá xuống cửa sổ app",
                        exc_info=True)
            return False

    def ui_khoa(self):
        """Khoá màn hình app lại — dùng khi trả phiên từ xa."""
        w = getattr(self, "_window", None)
        if not w:
            return False
        try:
            return bool(w.evaluate_js("window.otlRemoteLogout&&otlRemoteLogout()"))
        except Exception:
            return False

    def auth_logout(self):
        if getattr(self, "_assistant", None):
            self._assistant.pause_all("Đã đăng xuất người vận hành.")
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

    def web_pin_get(self):
        """Chỉ cầu desktop của Master được đọc PIN; không mở đường HTTP."""
        if not self._is_master():
            return {"ok": False, "err": "Chỉ Master được xem hoặc sửa PIN web."}
        return {"ok": True, "pin": str(self.web_cfg.get("pin") or "")}

    def web_pin_set(self, pin):
        """Lưu nguyên chuỗi để giữ số 0 đầu; chỉ đổi PIN chạy sau khi ghi bền."""
        if not self._is_master():
            return {"ok": False, "err": "Chỉ Master được xem hoặc sửa PIN web."}
        if not isinstance(pin, str) or not 6 <= len(pin) <= 12 or not pin.isascii() or not pin.isdigit():
            return {"ok": False, "err": "PIN web cần từ 6 đến 12 chữ số."}
        if pin in {"123456", "000000"}:
            return {"ok": False, "err": "PIN này quá dễ đoán. Hãy chọn PIN khác để giữ nguyên sau khi khởi động lại."}
        path = self._ini_path()
        tmp = path + ".web-pin.tmp"
        try:
            c = configparser.ConfigParser()
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    c.read_file(f)
            if not c.has_section("WebServer"):
                c.add_section("WebServer")
            c.set("WebServer", "pin_dieu_khien", pin)
            with open(tmp, "w", encoding="utf-8") as f:
                c.write(f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
        except Exception:
            return {"ok": False, "err": "Không lưu được settings.ini. PIN cũ vẫn giữ nguyên."}
        self.web_cfg["pin"] = pin
        # Đổi PIN có hiệu lực ngay cả với tablet đã đăng nhập bằng PIN cũ.
        self.web_tokens.clear()
        return {"ok": True}

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
        return os.path.join(app_data_dir(), "app_config.json")   # portable — cạnh exe

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
                "pin":  (w.get("pin_dieu_khien", "") or "").strip(),
            }
        if c.has_section("BanQuyen"):
            self.web_cfg["license_enforce"] = c["BanQuyen"].get("cuong_che", "0") != "0"
        # PIN web: chưa đặt HOẶC đang dùng một PIN yếu ai cũng biết → sinh NGẪU
        # NHIÊN 6 số, ghi vào settings.ini để thợ đọc. Không bao giờ quay lại hằng số.
        #
        # Vì sao phải đổi cả PIN đã có: "1108" là mặc định ghi cứng trong mã nguồn
        # tới 2026-09-06, nên MỌI máy đã giao đều đang mở cùng một PIN — mà PIN web
        # là cửa dẫn thẳng tới POST /api/write, tức lái được gas/nạp/xả. Thợ đổi
        # sang PIN khác trong settings.ini lúc nào cũng được, chỉ cần đừng dùng lại
        # mấy số trong danh sách này.
        if self.web_cfg.get("bat", True):
            weak = {"", "1108", "0000", "1111", "1234", "123456", "000000"}
            if str(self.web_cfg.get("pin") or "") in weak:
                cu = self.web_cfg.get("pin") or "(chưa đặt)"
                self.web_cfg["pin"] = "".join(secrets.choice("0123456789") for _ in range(6))
                log.warning("[WEB] PIN điều khiển từ xa cũ (%s) quá yếu — ĐÃ ĐỔI. "
                            "PIN mới nằm trong settings.ini, mục [WebServer].", cu)

    def prof_dir(self):
        """Thư mục lưu hồ sơ. MẶC ĐỊNH = thư mục dữ liệu cạnh exe (portable) — khỏi
        cần bấm 📁. Nút 📁 (prof_dir_pick) vẫn override sang thư mục khác nếu muốn."""
        return (self._cfg().get("prof_dir") or "").strip() or app_data_dir()

    def style_export(self, package):
        """Xuất phong cách qua hộp lưu Windows; không đụng cấu hình máy."""
        if not self._window:
            return {"ok": False, "err": "không có cửa sổ ứng dụng"}
        if not isinstance(package, dict) or package.get("format") != "otl-style" or package.get("version") != 1:
            return {"ok": False, "err": "gói phong cách không hợp lệ"}
        body = json.dumps(package, ensure_ascii=False, indent=2)
        if len(body.encode("utf-8")) > 1100000:
            return {"ok": False, "err": "gói phong cách quá lớn"}
        try:
            selected = self._window.create_file_dialog(
                webview.SAVE_DIALOG, save_filename="OTL-style.json",
                file_types=("JSON (*.json)",))
            if not selected:
                return {"ok": False, "cancelled": True}
            path = selected[0] if isinstance(selected, (list, tuple)) else selected
            with open(path, "w", encoding="utf-8") as stream:
                stream.write(body)
            return {"ok": True}
        except Exception:
            log.error("[UI] Style export failed", exc_info=True)
            return {"ok": False, "err": "không ghi được tệp phong cách"}

    # ── File cài đặt app (CSV chữ) — chủ máy 14/09: xuất/nhập được, Excel/Notepad sửa được ──
    # JS dựng/đọc nội dung (nó biết khoá nào hợp lệ, dải nào đúng); Python chỉ lo HỘP
    # CHỌN FILE của Windows + đọc/ghi đĩa. utf-8-sig để Excel mở không vỡ dấu tiếng Việt.
    _SETTINGS_MAX = 1_000_000

    def settings_export(self, text, filename="OTL-cai-dat.csv"):
        """Hỏi chỗ lưu rồi ghi file cài đặt. Trả {ok, path} / {ok:False, cancelled|err}."""
        if not self._window:
            return {"ok": False, "err": "không có cửa sổ ứng dụng"}
        if not isinstance(text, str) or len(text.encode("utf-8")) > self._SETTINGS_MAX:
            return {"ok": False, "err": "nội dung cài đặt không hợp lệ"}
        name = "".join("-" if ch in '\\/:*?"<>|' else ch for ch in str(filename or ""))[:80] \
            or "OTL-cai-dat.csv"
        try:
            selected = self._window.create_file_dialog(
                webview.SAVE_DIALOG, save_filename=name,
                file_types=("CSV (*.csv)", "Văn bản (*.txt)"))
            if not selected:
                return {"ok": False, "cancelled": True}
            path = selected[0] if isinstance(selected, (list, tuple)) else selected
            with open(path, "w", encoding="utf-8-sig", newline="") as stream:
                stream.write(text)
            log.info("[CÀI ĐẶT] xuất file cài đặt → %s", path)
            return {"ok": True, "path": path}
        except Exception:
            log.error("[UI] Settings export failed", exc_info=True)
            return {"ok": False, "err": "không ghi được file cài đặt"}

    def settings_import(self):
        """Hỏi file rồi TRẢ NỘI DUNG cho JS kiểm — Python không tự áp dụng gì."""
        if not self._window:
            return {"ok": False, "err": "không có cửa sổ ứng dụng"}
        try:
            selected = self._window.create_file_dialog(
                webview.OPEN_DIALOG, allow_multiple=False,
                file_types=("File cài đặt (*.csv;*.txt)", "Mọi tệp (*.*)"))
            if not selected:
                return {"ok": False, "cancelled": True}
            path = selected[0] if isinstance(selected, (list, tuple)) else selected
            if os.path.getsize(path) > self._SETTINGS_MAX:
                return {"ok": False, "err": "file quá lớn — không phải file cài đặt"}
            with open(path, "rb") as stream:
                raw = stream.read()
            try:
                text = raw.decode("utf-8-sig")
            except UnicodeDecodeError:          # Excel lưu "CSV" kiểu ANSI tiếng Việt
                text = raw.decode("cp1258", errors="replace")
            log.info("[CÀI ĐẶT] đọc file cài đặt ← %s", path)
            return {"ok": True, "text": text, "name": os.path.basename(path)}
        except Exception:
            log.error("[UI] Settings import failed", exc_info=True)
            return {"ok": False, "err": "không đọc được file cài đặt"}

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

    # ── Kho hồ sơ = ho-so.csv (đọc bằng mắt/Excel/Artisan) ────────────────────
    # NGUỒN SỰ THẬT của DANH SÁCH hồ sơ (chốt chủ máy 2026-07-25, bỏ profiles.json).
    # Curve mẻ đã rang KHÔNG nhồi vào đây — nằm ở kho mẻ SQLite + file .csv/.alog
    # Artisan từng mẻ (prof_write_files). Cột trống = thẻ mỏng (app tự ước).
    # bgBatch = id MẺ NỀN trong kho mẻ (batches.db) — chế độ rang TỰ ĐỘNG phát lại
    # đúng đường gas/gió/trống của mẻ đó. Trống = hồ sơ chỉ rang THƯỜNG (thợ chỉnh tay).
    _PROF_COLS = ["no", "name", "roast", "chargeT", "deT", "fcsT", "devTarget",
                  "preGas", "temp", "time", "kg", "bean", "bgBatch", "fav",
                  "color", "date", "roaster", "notes"]
    _PROF_INT = ("chargeT", "deT", "fcsT", "devTarget", "preGas", "temp",
                 "bgBatch", "fav")

    def _prof_csv_path(self):
        return os.path.join(self.prof_dir(), "ho-so.csv")

    def _prof_from_csv(self):
        """ho-so.csv → list hồ sơ (số đã parse, ô trống bỏ qua). None nếu lỗi."""
        out = []
        try:
            with open(self._prof_csv_path(), "r", encoding="utf-8-sig", newline="") as f:
                for r in csv.DictReader(f):
                    p = {}
                    for k in self._PROF_COLS:
                        if k == "no":
                            continue
                        v = (r.get(k) or "").strip()
                        if v == "":
                            continue
                        if k in self._PROF_INT:
                            try:
                                p[k] = int(float(v))
                            except Exception:
                                pass
                        elif k == "kg":
                            try:
                                p[k] = float(v)
                            except Exception:
                                pass
                        else:
                            p[k] = v
                    if p.get("name"):
                        out.append(p)
            return out
        except Exception:
            return None

    def _prof_to_csv(self, profiles):
        """Ghi list hồ sơ ra ho-so.csv (ghi tạm rồi thay — không bao giờ file cụt)."""
        path = self._prof_csv_path()
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=self._PROF_COLS)
            w.writeheader()
            for i, p in enumerate(profiles or []):
                row = {k: "" for k in self._PROF_COLS}
                for k in self._PROF_COLS:
                    v = p.get(k)
                    if v is not None and v != "":
                        row[k] = v
                row["no"] = i + 1
                w.writerow(row)
        os.replace(tmp, path)

    def prof_load(self):
        """Đọc kho hồ sơ. Ưu tiên ho-so.csv (nguồn sự thật). Chưa có CSV mà còn
        profiles.json cũ → DI TRÚ một lần (ghi CSV, đổi tên json→.bak). None =
        chưa chọn thư mục / chưa có hồ sơ nào."""
        d = self.prof_dir()
        if not d:
            return None
        if os.path.exists(self._prof_csv_path()):
            return self._prof_from_csv()
        jpath = os.path.join(d, "profiles.json")
        if os.path.exists(jpath):
            try:
                with open(jpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    self._prof_to_csv(data)                 # di trú → ho-so.csv
                    try:
                        os.replace(jpath, jpath + ".bak")   # giữ bản phòng hờ
                    except Exception:
                        pass
                    return self._prof_from_csv()
            except Exception:
                return None
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
        """Ghi danh sách hồ sơ ra <thư mục>/ho-so.csv (ghi tạm rồi thay — chống hỏng file)."""
        d = self.prof_dir()
        if not d:
            return {"ok": False, "err": "chưa chọn thư mục"}
        try:
            self._prof_to_csv(profiles)
            return {"ok": True, "path": self._prof_csv_path()}
        except Exception as e:
            return {"ok": False, "err": str(e)}

    # ── CÔNG THỨC NẠP = cong-thuc-nap.csv ────────────────────────────────────
    # Bộ mức máy đặt SẴN cho lúc vào mẻ: gas / gió / trống + nhiệt charge.
    # Thợ chọn 1 công thức trước khi nạp → app ghi thẳng 3 mức xuống máy và đặt
    # nhiệt nạp. Tách khỏi ho-so.csv vì 1 công thức dùng cho nhiều hồ sơ (cùng
    # một cách vào mẻ, khác loại cà). Cùng kiểu CSV đọc-bằng-mắt như hồ sơ.
    _NAP_COLS = ["no", "name", "burner", "air", "drum", "chargeT", "fav",
                 "roaster", "date", "notes"]
    _NAP_INT = ("burner", "air", "drum", "chargeT", "fav")

    def _nap_csv_path(self):
        return os.path.join(self.prof_dir(), "cong-thuc-nap.csv")

    def nap_load(self):
        """Đọc kho công thức nạp. Chưa có file → [] (app tự mời tạo)."""
        d = self.prof_dir()
        if not d or not os.path.exists(self._nap_csv_path()):
            return []
        out = []
        try:
            with open(self._nap_csv_path(), "r", encoding="utf-8-sig", newline="") as f:
                for r in csv.DictReader(f):
                    n = {}
                    for k in self._NAP_COLS:
                        if k == "no":
                            continue
                        v = (r.get(k) or "").strip()
                        if v == "":
                            continue
                        if k in self._NAP_INT:
                            try:
                                n[k] = int(float(v))
                            except Exception:
                                pass
                        else:
                            n[k] = v
                    if n.get("name"):
                        out.append(n)
            return out
        except Exception:
            log.error("[HỒ SƠ] đọc cong-thuc-nap.csv lỗi", exc_info=True)
            return []

    def nap_save(self, naps):
        """Ghi kho công thức nạp (ghi tạm rồi thay — không bao giờ file cụt)."""
        d = self.prof_dir()
        if not d:
            return {"ok": False, "err": "chưa chọn thư mục"}
        try:
            path = self._nap_csv_path()
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8-sig", newline="") as f:
                w = csv.DictWriter(f, fieldnames=self._NAP_COLS)
                w.writeheader()
                for i, n in enumerate(naps or []):
                    row = {k: "" for k in self._NAP_COLS}
                    for k in self._NAP_COLS:
                        v = n.get(k)
                        if v is not None and v != "":
                            row[k] = v
                    row["no"] = i + 1
                    w.writerow(row)
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
# Phiên ĐĂNG NHẬP API (tài khoản app + PIN, dùng cho CLI/MCP). Ngắn hơn token web
# 12 giờ vì đây là cửa cho MÁY: không ai ngồi cạnh để thấy phiên còn mở.
API_SESS_TTL = 8 * 3600


def _scopes_cho(role, perms):
    """Tài khoản app → phạm vi khoá API. Master đủ ba tầng; thợ KHÔNG bao giờ có
    'control' qua đường này — lái máy từ xa vẫn phải là khoá cấp riêng hoặc Master.
    'config' chỉ mở cho thợ đã được giao quyền chỉnh calib/model nhiệt."""
    if role == "master":
        return list(otl_apikey.SCOPES)
    p = perms or {}
    sc = ["read"]
    if p.get("calib_gas") or p.get("model_nhiet"):
        sc.append("config")
    return sc


def _prune_sessions(api):
    now = time.time()
    for t, v in list(api.api_sessions.items()):
        if now - v.get("t", 0) >= API_SESS_TTL:
            api.api_sessions.pop(t, None)
# Đếm số lần sai PIN web theo IP: {ip: (số_lần, khoá_tới_lúc)}. Phải có khoá
# luồng vì ThreadingHTTPServer xử nhiều yêu cầu cùng lúc.
_LOGIN_FAIL = {}
_LOGIN_LOCK = threading.Lock()
# Bộ hãm CHUNG theo IP cho các đường ĐỨNG TRƯỚC cổng token: {(tên, ip): [mốc giây]}
_RATE = {}


def _rate_ok(bucket, ip, limit, window=60.0):
    """True nếu IP còn quota. Dùng cho đường chưa đăng nhập mà TỐN CPU hoặc dò được.
    Ví dụ /api/pbkdf2: 150k vòng băm ≈ 108 ms CPU mỗi lần gọi, không hãm thì vài chục
    kết nối là ghim CPU của chính máy đang bơm Modbus giữa mẻ rang."""
    now = time.time()
    with _LOGIN_LOCK:
        k = (bucket, ip)
        q = [t for t in _RATE.get(k, ()) if now - t < window]
        if len(q) >= limit:
            _RATE[k] = q
            return False
        q.append(now)
        _RATE[k] = q
        if len(_RATE) > 500:                     # dọn rác, khỏi phình vô hạn
            for kk in [x for x, v in _RATE.items() if not v or now - v[-1] > window * 4]:
                _RATE.pop(kk, None)
        return True


def _prune_tokens(api):
    """Token hết hạn nằm lại trong dict mãi mãi — dọn mỗi lần cấp token mới."""
    now = time.time()
    for t in [t for t, ts in api.web_tokens.items() if now - ts >= WEB_TOKEN_TTL]:
        api.web_tokens.pop(t, None)


# Khoá "linh hồn" web được phép mượn KHI CHƯA ĐĂNG NHẬP — chỉ trang trí, không
# có dữ liệu người dùng, không có tài khoản, không có bí quyết nghề.
# Đường GHI nào cần phạm vi nào. Không có trong bảng = "config" (mặc định chặt).
# LÁI MÁY tách riêng vì đây là thứ mở được van gas và bắn xi-lanh.
SCOPE_POST = {
    "/api/write":        "control",   # gas · gió · trống · nạp · xả · mồi lửa
    "/api/new_batch":    "control",
    "/api/begin_batch":  "control",
    "/api/lease_open":   "control",   # xin lượt lái cho tác nhân tự động (T2)
    "/api/lease_beat":   "control",
    "/api/lease_close":  "control",
    "/api/uievent":      "read",      # chỉ soi gương thao tác UI, không đụng máy
    "/api/oplog":        "read",      # ghi nhật ký vận hành
}
SCOPE_GET = "read"

# Đường nào tính là NHỊP TIM của tác nhân tự động. Chỉ hành động LÁI mới tính:
# đọc trạng thái không chứng minh được tác nhân còn tỉnh, chỉ chứng minh tiến
# trình còn chạy. Tác nhân nghĩ lâu thì gọi /api/lease_beat cho tường minh.
NHIP_POST = {"/api/write", "/api/lease_open", "/api/lease_beat",
             "/api/new_batch", "/api/begin_batch"}

# ── LUẬT LÁI T2 (§5 docs/plan/plan-mcp-api-extension.md) ────────────────────
# Chỉ áp cho TÁC NHÂN TỰ ĐỘNG (khoá API). Thợ lái app bằng tay KHÔNG dính luật
# nào ở đây — thợ đứng cạnh máy, thấy khói nghe tiếng nổ hạt; AI thì không.
LEASE_MAX_S = 900        # trần 15 phút một lượt. Hết là rụng, muốn nữa phải xin lại.
# Trần TỔNG cho cả phiên PC control. Không có nó thì trần 15 phút ở trên vô
# nghĩa: khoá đang giữ lái xin lại được ngay, lái vô tận không cần ai có mặt.
# Hết trần này thì phải có NGƯỜI tắt/bật lại PC control ở tủ mới lái tiếp.
LEASE_PHIEN_MAX_S = 3600
LEASE_STALE_S = 20       # tác nhân im quá ngần này giây = coi như đã mất
# Ân hạn khi ĐỨT LIÊN LẠC với máy: giữ lượt lái ngần này giây rồi mới đóng. Bằng
# đúng watchdog PC control của firmware — trong cửa sổ đó firmware cũng chưa nhả
# quyền, nên giữ lượt lái là đúng sự thật. Xem _lease_guard.
LEASE_AN_HAN_S = 3.0
LEASE_RATE_N = 60        # trần số lệnh ghi mỗi phút của một lượt lái
# Trần BƯỚC NHẢY mỗi lệnh — chốt chặn "AI đòi gas 0 lên 100 lúc FCs". Firmware
# còn một lớp slew rate riêng (AnalogConfig.h); đây là lớp thứ hai, không thay.
LEASE_STEP = {"gas": 25, "air": 40, "drum": 40, "sv": 30, "vac": 60}
# Hai ô này thuộc DÂY CHUYỀN AN TOÀN, tác nhân tự động không được đụng: hb là
# nhịp tim do app giữ (xem otl_link._hb_cho_phep), agent là cờ khai chính nó.
LEASE_CAM = ("hb", "agent")

SOUL_PUBLIC = {"otl_theme", "otl_accent", "otl_hue", "otl_lang",
               "otl_accent_hex", "otl_wallpaper"}


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

        def _blob(self, body, ctype, cache="no-store"):
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", cache)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _tok_ok(self, tok):
            t = api.web_tokens.get(tok or "")
            return t is not None and (time.time() - t) < WEB_TOKEN_TTL

        def _tok_any(self, body_tok=None):
            """Lấy token từ MỌI đường: header Authorization/X-OTL-Token, ?token= trên
            URL (EventSource không đặt được header), hoặc thân JSON (đường cũ)."""
            h = self.headers.get("Authorization", "")
            if h.lower().startswith("bearer "):
                return h[7:].strip()
            h = self.headers.get("X-OTL-Token", "")
            if h:
                return h.strip()
            if "?" in self.path:
                from urllib.parse import parse_qs, urlparse
                q = parse_qs(urlparse(self.path).query).get("token")
                if q:
                    return q[0]
            return body_tok

        def _v1(self):
            """/api/v1/xxx là BÍ DANH của /api/xxx — cửa vào có đánh số bản cho
            client ngoài (MCP, script). Đổi thẳng đường dẫn rồi dùng chung handler,
            khỏi nhân đôi mã: hai bản sao là hai chỗ để quên vá lỗ bảo mật."""
            if self.path.startswith("/api/v1/"):
                self.path = "/api/" + self.path[len("/api/v1/"):]

        def _ctx(self, body_tok=None):
            """Ai đang gọi? Trả {kind, scopes, name} hoặc None.
            · token web  = NGƯỜI đã nhập PIN → đủ mọi phạm vi (thợ đứng ngay đó)
            · khoá API   = MÁY (script/MCP/AI) → CHỈ những phạm vi được cấp"""
            raw = self._tok_any(body_tok)
            if self._tok_ok(raw):
                return {"kind": "nguoi", "scopes": list(otl_apikey.SCOPES), "name": "web"}
            # Phiên đăng nhập bằng TÀI KHOẢN APP (/api/v1/login). Cố ý mang kind
            # "may" chứ không phải "nguoi": lệnh tới qua mạng bằng một mật khẩu
            # dùng lại được, không ai chứng minh có người đứng cạnh máy — nên vẫn
            # phải đi trọn dây an toàn của tác nhân tự động (lượt lái, hãm bước,
            # hãm tần suất). Mật khẩu tiện hơn khoá API, KHÔNG lỏng hơn.
            se = api.api_sessions.get(raw or "")
            if se:
                if time.time() - se.get("t", 0) < API_SESS_TTL:
                    return {"kind": "may", "scopes": list(se.get("scopes", [])),
                            "name": "login:" + se.get("name", "?"),
                            "id": se.get("id", "")}
                api.api_sessions.pop(raw, None)
            k = api._apikeys.verify(raw or "")
            if k:
                # KHÔNG nhấp nhịp ở đây. Trước 2026-09-09 mọi request đều tính là
                # "tác nhân còn sống", kể cả GET đọc telemetry — nên một vòng lặp
                # poll còn chạy là đủ giữ lượt lái, dù phần suy nghĩ của AI đã
                # treo hoặc hết quota. Nhịp đo "tiến trình còn chạy" chứ không đo
                # "tác nhân còn tỉnh", đúng cái mà chốt 20 giây sinh ra để bắt.
                # Nay chỉ HÀNH ĐỘNG LÁI mới là nhịp — xem NHIP_POST bên dưới.
                return {"kind": "may", "scopes": k["scopes"], "name": k["name"],
                        "id": k["id"]}
            return None

        def _need(self, scope, body_tok=None):
            """Kiểm quyền. Trả ctx nếu được đi tiếp, None nếu đã trả lỗi cho client."""
            c = self._ctx(body_tok)
            if c is None:
                self._json({"ok": False, "err": "pin",
                            "msg": "chưa đăng nhập — cần PIN web, tài khoản app "
                                   "(/api/v1/login) hoặc khoá API hợp lệ"}, 401)
                return None
            if scope not in c["scopes"]:
                self._json({"ok": False, "err": "pham_vi",
                            "msg": "tài khoản/khoá này không có phạm vi '%s'" % scope,
                            "co": c["scopes"]}, 403)
                log.info("[API] từ chối '%s' — khoá '%s' thiếu phạm vi %s",
                         self.path, c["name"], scope)
                return None
            return c

        def _get_guard(self):
            """Cổng cho MỌI GET /api/*. Trước 2026-09-06 đọc tự do: ai vào được WiFi
            xưởng là lấy sạch hồ sơ rang, giá vốn, đơn hàng, danh sách thợ và trạng
            thái máy — rồi dò PIN web để chiếm quyền ghi. Nay phải có token web.
            Trả True nếu ĐƯỢC đi tiếp."""
            return self._need(SCOPE_GET) is not None

        def do_GET(self):
            self._v1()
            if self.path == "/assistant.js":
                path = os.path.join(os.path.dirname(__file__), "roast_assistant_ui.js")
                with open(path, "rb") as f:
                    body = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/javascript; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif self.path == "/manifest.webmanifest":
                # Trang trí thuần — không dữ liệu người dùng nên không đòi token, giống /api/state.
                body = json.dumps({
                    "name": "OTL Roast Lab", "short_name": "Roast Lab",
                    "start_url": "/", "scope": "/", "display": "standalone",
                    "orientation": "landscape", "background_color": "#0b0e13",
                    "theme_color": "#0b0e13", "lang": "vi",
                    "icons": [{"src": "/pwa-192.png", "sizes": "192x192", "type": "image/png"},
                              {"src": "/pwa-512.png", "sizes": "512x512", "type": "image/png"},
                              {"src": "/pwa-512.png", "sizes": "512x512", "type": "image/png",
                               "purpose": "maskable"}],
                }, ensure_ascii=False).encode("utf-8")
                self._blob(body, "application/manifest+json; charset=utf-8")
            elif self.path in ("/pwa-180.png", "/pwa-192.png", "/pwa-512.png"):
                try:
                    with open(asset_path(self.path.lstrip("/")), "rb") as f:
                        body = f.read()
                except Exception as e:
                    self._json({"err": str(e)}, 404); return
                self._blob(body, "image/png", "public, max-age=86400")
            elif self.path in ("/", "/index.html"):
                try:
                    with open(html_path(), "rb") as f:
                        body = f.read()
                    # ĐÓNG DẤU web clone — shim trong HTML chỉ bật khi có dấu này
                    # Thêm ở bản WEB thôi — file HTML gốc không đổi. iPhone/iPad mở
                    # http://<ip-máy>:8555 rồi "Thêm vào Màn hình chính" sẽ có biểu tượng
                    # riêng, mở TOÀN MÀN (không thanh Safari) — nhìn như app cài thật.
                    body = body.replace(
                        b"<head>",
                        b"<head><script>window._OTL_WEBCLONE=1</script>"
                        b'<link rel="manifest" href="/manifest.webmanifest">'
                        b'<link rel="apple-touch-icon" href="/pwa-180.png">'
                        b'<meta name="apple-mobile-web-app-capable" content="yes">'
                        b'<meta name="mobile-web-app-capable" content="yes">'
                        b'<meta name="apple-mobile-web-app-title" content="Roast Lab">'
                        b'<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">'
                        b'<meta name="theme-color" content="#0b0e13">', 1)
                    body = body.replace(b"</body>", b'<script src="/assistant.js"></script></body>', 1)
                except Exception as e:
                    self._json({"err": str(e)}, 500); return
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif self.path.startswith("/api/"):
                # ── CỔNG: mọi API đọc đều cần token, trừ vài đường bootstrap ──
                # /api/state được xử riêng bên dưới (trả phần TRANG TRÍ không cần
                # token) vì trang web phải mượn theme/ngôn ngữ TRƯỚC khi đăng nhập.
                if self.path != "/api/state" and not self._get_guard():
                    return
                self._do_get_api()

        def _do_get_api(self):
            if False:
                pass
            elif self.path == "/api/assistant_skills":
                self._json({"skills": roast_assistant.skills()})
            elif self.path.startswith("/api/assistant_skill?"):
                from urllib.parse import parse_qs, urlparse
                try:
                    name = parse_qs(urlparse(self.path).query).get("name", [""])[0]
                    self._json({"name": name, "instructions": roast_assistant.read_skill(name)})
                except ValueError as e:
                    self._json({"ok": False, "err": str(e)}, 404)
            elif self.path == "/api/assistant_capabilities":
                self._json({"modes": roast_assistant.MODES, "tools": roast_assistant.TOOLS,
                            "grant_location": "desktop_master", "lan_chat": "read_only",
                            "plan_max_seconds": 840, "pause_on_manual": True})
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
                # Trang web phải mượn theme/ngôn ngữ TRƯỚC khi đăng nhập, nên đường
                # này mở — nhưng CHỈ trả phần TRANG TRÍ. Phần còn lại (tài khoản
                # otl_users2, hồ sơ, lịch sử, nhật ký, khoá đăng nhập) đòi token.
                # Trước 2026-09-06 trả trọn gói không cần gì: máy nào chưa di cư
                # tài khoản sang Python là phát luôn cả salt + băm PIN ra LAN, mà
                # PIN chỉ có 4 chữ số nên dò ngoại tuyến vài giây là ra.
                st = api.state_load() or {}
                if not self._tok_ok(self._tok_any()):
                    st = {k: v for k, v in st.items() if k in SOUL_PUBLIC}
                self._json({"state": st})
            elif self.path == "/api/profiles":
                # web đọc CHUNG profiles.json với app — Legion/điện thoại thấy đúng
                # hồ sơ thật, không xài bản localStorage riêng của trình duyệt
                self._json({"profiles": api.prof_load()})
            elif self.path == "/api/naps":
                self._json({"naps": api.nap_load()})       # công thức nạp
            elif self.path.split("?", 1)[0] == "/api/batches":
                # lịch sử mẻ từ kho SQLite — web xem chung với app (xem tự do)
                from urllib.parse import parse_qs, urlsplit
                q = parse_qs(urlsplit(self.path).query)
                self._json({"batches": api.db_batch_list(
                    q.get("n", [50])[0], q.get("q", [""])[0],
                    q.get("from", [""])[0], q.get("to", [""])[0],
                    q.get("offset", [0])[0])})
            elif self.path.split("?", 1)[0] == "/api/batches_count":
                # TỔNG số mẻ khớp bộ lọc — CÙNG bộ lọc với /api/batches, chỉ khác
                # là không phân trang. Trước đây chỉ app desktop gọi được qua cầu
                # pywebview, nên bản web và client ngoài (MCP, script) phải lấy số
                # dòng của MỘT TRANG làm tổng: kho 900 mẻ mà màn hình ghi "50 mẻ
                # đã lưu" và không bao giờ nhúc nhích.
                # count = null nghĩa là CHƯA ĐẾM ĐƯỢC (kho chưa mở hoặc lỗi đọc);
                # count = 0 nghĩa là đếm được và bộ lọc không khớp mẻ nào. Hai
                # chuyện khác hẳn nhau nên không gộp về 0.
                from urllib.parse import parse_qs, urlsplit
                q = parse_qs(urlsplit(self.path).query)
                self._json({"count": api.db_batch_count(
                    q.get("q", [""])[0], q.get("from", [""])[0],
                    q.get("to", [""])[0])})
            elif self.path == "/api/auth_state":
                # màn đăng nhập web: danh sách user (KHÔNG kèm hash) — xem tự do
                self._json(api.auth_state())
            elif self.path == "/api/audit":
                # nhật ký hash-chain + huy hiệu toàn vẹn (xem tự do)
                self._json({"tail": api.audit_tail(300), "verify": api.audit_verify()})
            elif self.path == "/api/inv_lots":
                # GĐ4: kho nhân (xem tự do) — số dư, còn N mẻ, tuổi lô
                self._json({"lots": api.inv_lots()})
            elif self.path == "/api/inv_orders":
                self._json({"orders": api.inv_orders()})
            elif self.path == "/api/inv_cost":
                self._json({"cfg": api.inv_cost_config()})
            elif self.path.startswith("/api/inv_report"):
                from urllib.parse import parse_qs, urlparse
                q = parse_qs(urlparse(self.path).query)
                try:
                    dd = int(q.get("days", ["7"])[0])
                except ValueError:
                    dd = 7
                self._json({"report": api.inv_report(dd)})
            elif self.path == "/api/lease":
                self._json(api.lease_state())
            elif self.path == "/api/machine_cfg":
                self._json(api.machine_cfg_load())
            elif self.path == "/api/mc_read":
                self._json(api.mc_read())
            elif self.path.startswith("/api/inv_movements?"):
                from urllib.parse import parse_qs, urlparse
                q = parse_qs(urlparse(self.path).query)
                try:
                    lot = int(q.get("lot", ["0"])[0])
                except ValueError:
                    lot = 0
                self._json({"movements": api.inv_lot_movements(lot)})
            elif self.path.startswith("/api/inv_econ?"):
                from urllib.parse import parse_qs, urlparse
                q = parse_qs(urlparse(self.path).query)
                try:
                    bid = int(q.get("id", ["0"])[0])
                except ValueError:
                    bid = 0
                ds = q.get("drop_sec", [None])[0]
                ko = q.get("kg_out", [None])[0]
                self._json({"econ": api.inv_batch_econ(bid, ds, ko)})
            elif self.path.startswith("/api/inv_cup?"):
                from urllib.parse import parse_qs, urlparse
                q = parse_qs(urlparse(self.path).query)
                tgt = q.get("target", [None])[0]
                tid = q.get("target_id", [None])[0]
                self._json({"cuppings": api.inv_cup_list(tgt, tid)})
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
            self._v1()
            try:
                n = int(self.headers.get("Content-Length") or 0)
                if self.path == "/api/assistant" and not 0 <= n <= 24000:
                    self._json({"ok": False, "err": "Yêu cầu trợ lý quá lớn."}, 413); return
                req = json.loads(self.rfile.read(n) or b"{}")
                if not isinstance(req, dict):
                    self._json({"ok": False, "err": "Cần đối tượng JSON."}, 400); return
            except Exception:
                self._json({"ok": False, "err": "bad json"}, 400); return

            _ip = self.client_address[0]
            if self.path == "/api/assistant":
                ctx = self._need("read", req.get("token"))
                if ctx is None:
                    return
                if ctx.get("kind") != "nguoi":
                    self._json({"ok": False, "err": "Chat chỉ dành cho người đã đăng nhập PIN web."}, 403); return
                if req.get("action") not in ("state", "chat", "pause", "resume", "clear"):
                    self._json({"ok": False, "err": "Cấu hình và duyệt lệnh tại app máy chủ bằng Master."}, 403); return
                if req.get("action") == "chat" and not _rate_ok("assistant-chat", _ip, 10):
                    self._json({"ok": False, "err": "Tối đa 10 câu hỏi/phút."}, 429); return
                import hashlib
                actor = "web:" + hashlib.sha256(self._tok_any(req.get("token")).encode()).hexdigest()[:24]
                self._json(api._assistant_instance().dispatch(req.get("action"), req.get("payload", {}), actor))
                return
            if self.path == "/api/auth_login":
                # đăng nhập từ web — lockout tính ở Python, KHÔNG chiếm phiên kiosk;
                # đứng TRƯỚC cổng token vì đây chính là bước để có quyền.
                # Khoá bên Python tính THEO TÊN tài khoản, nên vẫn phải hãm theo IP:
                # kẻ dò có thể xoay vòng nhiều tên để né khoá của từng tên.
                if not _rate_ok("login", _ip, 20):
                    self._json({"ok": False, "err": "khoa",
                                "msg": "thử quá nhiều — chờ một phút"}, 429)
                    return
                self._json(api.auth_verify(req.get("name"), req.get("pin")))
                return
            if self.path == "/api/login":
                # ĐĂNG NHẬP CHO MÁY bằng tài khoản app (Master/thợ + PIN) — để
                # script/MCP khỏi phải tạo khoá API. Đứng TRƯỚC cổng token vì đây
                # chính là bước để có quyền. Lockout theo TÊN nằm ở auth_otl; hãm
                # theo IP ở đây vì kẻ dò xoay vòng tên là né được lockout tên.
                if not _rate_ok("apilogin", _ip, 20):
                    self._json({"ok": False, "err": "khoa",
                                "msg": "thử quá nhiều — chờ một phút"}, 429)
                    return
                if not api._auth:
                    self._json({"ok": False, "err": "auth Python chưa sẵn sàng"}, 503)
                    return
                r = api._auth.login(str(req.get("name") or ""), str(req.get("pin") or ""))
                if not r.get("ok"):
                    log.info("[API] %s đăng nhập hỏng cho '%s' (%s)", _ip,
                             req.get("name"), r.get("err"))
                    self._json(r, 401)
                    return
                u = r["user"]
                sc = _scopes_cho(u.get("role"), u.get("perms"))
                _prune_sessions(api)
                tok = secrets.token_hex(24)
                api.api_sessions[tok] = {"t": time.time(), "name": u["name"],
                                         "role": u.get("role", "slave"), "scopes": sc,
                                         "id": "login-" + secrets.token_hex(3)}
                log.info("[API] %s đăng nhập '%s' (%s) — phạm vi %s", _ip, u["name"],
                         u.get("role"), ",".join(sc))
                # Mở khoá luôn màn hình app đang mở. Mặc định BẬT: PIN vừa nhập
                # chính là PIN mở màn hình đó, nên giữ màn khoá lại không chặn
                # thêm được ai, chỉ làm người đứng ở máy khó hiểu. Muốn tắt thì
                # gửi {"mo_khoa_app": false} — script chạy nền nên gửi cờ này.
                mo = req.get("mo_khoa_app")
                da_mo = False
                if mo is None or mo:
                    da_mo = api.ui_mo_khoa({"name": u["name"], "role": u.get("role"),
                                            "perms": u.get("perms") or {}})
                    if da_mo:
                        log.warning("[API] MỞ KHOÁ MÀN HÌNH APP từ xa cho '%s' (%s)",
                                    u["name"], _ip)
                        api.op_log("warn", "API", "mở khoá màn hình từ xa: %s" % u["name"])
                self._json({"ok": True, "token": tok, "name": u["name"],
                            "role": u.get("role"), "scopes": sc,
                            "het_han_s": API_SESS_TTL, "mo_khoa_app": da_mo})
                return
            if self.path == "/api/logout":
                # Trả lại phiên. Không cần quyền gì: chỉ xoá đúng token đang cầm.
                tok = self._tok_any(req.get("token"))
                co = api.api_sessions.pop(tok or "", None) is not None
                # Khoá luôn màn hình app — KHÔNG mặc định: thợ có thể đang đứng
                # dùng màn hình đó, khoá ngang là cướp việc của người thật.
                da_khoa = bool(co and req.get("khoa_app") and api.ui_khoa())
                self._json({"ok": co, "khoa_app": da_khoa})
                return
            if self.path == "/api/auth_setup_master":
                if not _rate_ok("setup", _ip, 5):
                    self._json({"ok": False, "err": "khoa"}, 429)
                    return
                self._json(api.auth_setup_master(req.get("pin")))
                return

            if self.path == "/api/pbkdf2":
                # Băm PIN giùm web LAN (trình duyệt cấm crypto.subtle ngoài HTTPS).
                # Chỉ băm — không lộ hash lưu trữ; đứng TRƯỚC cổng token vì đây là
                # bước để đăng nhập.
                if not _rate_ok("pbkdf2", _ip, 10):
                    self._json({"hash": "", "err": "khoa",
                                "msg": "băm quá nhiều lần — chờ một phút"}, 429)
                    return
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
                # Hãm cũ (time.sleep 1s) gần như vô dụng: ThreadingHTTPServer nên kẻ
                # dò chạy 50 luồng song song là quét hết PIN 4 số trong vài phút.
                # Nay KHOÁ THEO IP: sai 5 lần thì cấm 5 phút, đếm chung mọi luồng.
                ip = self.client_address[0]
                with _LOGIN_LOCK:
                    n, until = _LOGIN_FAIL.get(ip, (0, 0.0))
                    if time.time() < until:
                        con = int(until - time.time())
                        self._json({"ok": False, "err": "khoa",
                                    "msg": "sai PIN nhiều lần — chờ %d giây" % con}, 429)
                        return
                pin = str(api.web_cfg.get("pin") or "")
                if pin and secrets.compare_digest(str(req.get("pin", "")), pin):
                    _prune_tokens(api)
                    tok = secrets.token_hex(16)
                    api.web_tokens[tok] = time.time()
                    with _LOGIN_LOCK:
                        _LOGIN_FAIL.pop(ip, None)
                    log.info("[WEB] %s đăng nhập PIN web thành công", ip)
                    self._json({"ok": True, "token": tok})
                else:
                    with _LOGIN_LOCK:
                        n = _LOGIN_FAIL.get(ip, (0, 0.0))[0] + 1
                        until = time.time() + 300 if n >= 5 else 0.0
                        _LOGIN_FAIL[ip] = (n, until)
                    log.info("[WEB] %s sai PIN web (lần %d)", ip, n)
                    time.sleep(1)
                    self._json({"ok": False, "err": "sai PIN"})
                return

            # Các lệnh dưới đây GHI — cần đúng phạm vi. Token web (người) có đủ;
            # khoá API chỉ được làm phần đã cấp. Mặc định "config" cho đường lạ.
            _scope = SCOPE_POST.get(self.path, "config")
            _ctx = self._need(_scope, req.get("token"))
            if _ctx is None:
                return
            if _ctx.get("kind") == "may" and self.path in NHIP_POST:
                api.lease_touch(_ctx.get("id"))     # nhịp tim = hành động lái
            if self.path == "/api/oplog":
                self._json({"ok": api.op_log(req.get("level"), req.get("tag") or "WEB",
                                             req.get("msg") or "")})
            elif self.path == "/api/profiles":
                self._json(api.prof_save(req.get("profiles") or []))
            elif self.path == "/api/naps":
                self._json(api.nap_save(req.get("naps") or []))    # công thức nạp
            elif self.path == "/api/uievent":
                self._json(api.ui_event(req))
            elif self.path == "/api/set_config":
                # web đổi cổng/baud/slave từ xa (token) — áp thẳng vào cầu Modbus
                self._json({"cfg": api.link_set_config(req.get("cfg") or {})})
            elif self.path == "/api/write":
                # ctx đi kèm: NGƯỜI (token web) ghi thẳng như cũ, MÁY (khoá API)
                # phải có lượt lái T2 đang mở — luật ở Api._lease_guard.
                self._json(api.link_write(req.get("name"), req.get("value"), _ctx))
            elif self.path == "/api/lease_open":
                self._json(api.lease_open(_ctx, req.get("phut")))
            elif self.path == "/api/lease_beat":
                api.lease_touch(_ctx.get("id"))
                self._json(api.lease_state())
            elif self.path == "/api/lease_close":
                self._json(api.lease_close(_ctx, req.get("ly_do") or ""))
            elif self.path == "/api/new_batch":
                self._json(api.link_new_batch())
            elif self.path == "/api/begin_batch":
                self._json(api.link_begin_batch(req.get("meta")))
            # ── GĐ4: ghi kho/đơn/chi phí/cupping (cần token) ────────────────
            elif self.path == "/api/inv_lot_add":
                self._json(api.inv_lot_add(req.get("lot") or {}))
            elif self.path == "/api/inv_lot_edit":
                self._json(api.inv_lot_edit(req.get("id"), req.get("lot") or {}))
            elif self.path == "/api/inv_lot_adjust":
                self._json(api.inv_lot_adjust(req.get("id"), req.get("kg"), req.get("note") or ""))
            elif self.path == "/api/inv_hopper_set":
                self._json(api.inv_hopper_set(req.get("lot_id"), req.get("hopper") or 1))
            elif self.path == "/api/inv_order_add":
                self._json(api.inv_order_add(req.get("order") or {}))
            elif self.path == "/api/inv_order_set":
                self._json(api.inv_order_set(req.get("id"), req.get("order") or {}))
            elif self.path == "/api/inv_cost_set":
                self._json(api.inv_cost_config_set(req.get("cfg") or {}))
            elif self.path == "/api/inv_cup_add":
                self._json(api.inv_cup_add(req.get("cup") or {}))
            elif self.path == "/api/machine_cfg_save":
                self._json(api.machine_cfg_save(req.get("cfg") or {}))
            elif self.path == "/api/mc_write":
                self._json(api.mc_write(req.get("items", req.get("cfg")), _ctx))
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
    migrate_to_portable()   # di trú 1 lần data cũ (%LOCALAPPDATA% + prof_dir) sang cạnh exe — TRƯỚC logging/DB
    setup_logging()
    log.info("[APP] khởi động — %s — data: %s",
             "exe" if getattr(sys, "frozen", False) else "dev", app_data_dir())
    api = Api()
    # Tự mở FULLSCREEN đúng độ phân giải màn hình hiện tại — hoàn toàn tự động.
    # Phần HTML tự co khung 2560×1440 vừa khít mọi phân giải (fit()).
    # CHỐNG CACHE: WebView2 nhận cờ Chromium qua biến môi trường — tắt hẳn
    # http/disk cache (?v= trên file:// KHÔNG dùng được: ERR_FILE_NOT_FOUND).
    # --lang=vi-VN: ô <input type="date"> của Chromium lấy ĐỊNH DẠNG NGÀY CỦA
    # WINDOWS, không phải của trang. Máy xưởng đang đặt sShortDate = "dd-MMM-yy"
    # nên hai ô lọc ngày ở màn Lịch sử hiện gợi ý "dd-----yyyy" — thợ đọc không
    # ra phải điền kiểu gì. Ghi chú cũ trong OTL Roast Lab.html bảo đây chỉ là
    # chuyện của Chromium headless lúc chạy test: SAI, tái lập được trong Edge
    # thật (cùng nhân WebView2) và có ảnh chụp app thật ngày 12/09/2026.
    # PHẢI là vi-VN. Đã thử en-GB: Chromium vẫn rơi về định dạng Windows và vẫn
    # ra "dd-----yyyy" — chỉ locale KHÁC hệ mới ép được nó dùng định dạng riêng.
    # vi-VN cho gợi ý "nn/mm/yyyy" (ngày/tháng/năm), đúng thứ tự ta quen.
    # Nhãn cạnh ô vì vậy viết bằng CHỮ ("ngày/tháng/năm") chứ không viết mã chữ
    # cái, để máy khách đặt Windows kiểu nào nhãn cũng không nói sai.
    # Không đụng gì tới nút VI/EN của app: app tự dịch bằng localStorage otl_lang,
    # không đọc navigator.language chỗ nào (đã grep).
    os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = \
        "--disable-http-cache --disk-cache-size=1 --lang=vi-VN"
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
        try:
            with open(os.path.join(os.path.dirname(__file__), "roast_assistant_ui.js"), encoding="utf-8") as f:
                window.evaluate_js(f.read())
        except Exception:
            log.exception("[ASSISTANT] Could not load assistant panel")
        if not _push_started:
            _push_started.append(1)
            threading.Thread(target=_app_push, name="otl-apppush", daemon=True).start()
    window.events.loaded += _start_push
    # QUAN TRỌNG: pywebview mặc định private_mode=True (ẩn danh) → localStorage bị
    # xoá mỗi lần đóng. App lưu PIN/tài khoản/config/nhật ký trong localStorage nên
    # phải TẮT ẩn danh + trỏ thư mục dữ liệu bền (portable — cạnh exe).
    storage = app_data_dir()
    # WebView2 (private_mode=False) hay giữ CACHE trang cũ → sửa HTML xong mở app
    # vẫn thấy giao diện cũ. Dọn cache render mỗi lần mở; GIỮ Local Storage
    # (PIN/tài khoản/config nằm ở "Local Storage"/"IndexedDB", không đụng).
    # GPUCache KHÔNG xoá nữa (14/09/2026): đó là bộ đệm SHADER của card đồ hoạ, không chứa
    # trang cũ nào. Xoá nó thì mỗi lần mở app GPU phải biên dịch lại shader từ đầu — góp phần
    # làm vài giây đầu khung hình giật (chủ máy báo "mở app lên là con trỏ chuột lag").
    for sub in ("Cache", "Code Cache", "Service Worker"):
        shutil.rmtree(os.path.join(storage, "EBWebView", "Default", sub),
                      ignore_errors=True)
    webview.start(private_mode=False, storage_path=storage)


if __name__ == "__main__":
    main()
