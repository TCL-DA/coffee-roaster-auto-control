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
        self.web_cfg = {"bat": True, "cong": 8555, "pin": "1108"}  # [WebServer] trong settings.ini
        self.web_tokens = {}     # token → thời điểm cấp (điện thoại đã nhập đúng PIN web)

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
        """Về mẻ trống — xoá đồng hồ/mốc bên Python."""
        return self._link.new_batch()

    def link_begin_batch(self):
        """Thợ bấm Bắt đầu rang — mở đồng hồ mẻ + chấm mốc từ giây này."""
        return self._link.begin_batch()

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
            else:
                self._json({"err": "not found"}, 404)

        def do_POST(self):
            try:
                n = int(self.headers.get("Content-Length") or 0)
                req = json.loads(self.rfile.read(n) or b"{}")
            except Exception:
                self._json({"ok": False, "err": "bad json"}, 400); return

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
            elif self.path == "/api/write":
                self._json(api.link_write(req.get("name"), req.get("value")))
            elif self.path == "/api/new_batch":
                self._json(api.link_new_batch())
            elif self.path == "/api/begin_batch":
                self._json(api.link_begin_batch())
            else:
                self._json({"err": "not found"}, 404)

    port = int(api.web_cfg.get("cong", 8555))
    try:
        srv = http.server.ThreadingHTTPServer(("0.0.0.0", port), Handler)
    except OSError as e:
        print(f"[web] không mở được cổng {port}: {e}")
        log.warning("[WEB] không mở được cổng %s: %s", port, e)
        return
    threading.Thread(target=srv.serve_forever, name="otl-web", daemon=True).start()
    print(f"[web] điện thoại cùng WiFi vào: http://<ip-máy-này>:{port}")
    log.info("[WEB] server LAN chạy — cổng %s", port)


def main():
    setup_logging()
    log.info("[APP] khởi động — %s", "exe" if getattr(sys, "frozen", False) else "dev")
    api = Api()
    # Tự mở FULLSCREEN đúng độ phân giải màn hình hiện tại — hoàn toàn tự động.
    # Phần HTML tự co khung 2560×1440 vừa khít mọi phân giải (fit()).
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
