"""OTL WiFi Link — tìm IP và cài nhanh module wifi nối máy rang với Artisan (bản giao khách).

Chạy:  Windows: OTL WiFi Link.exe (Start) hoặc  python tools/otl_wifi_link.py
        macOS:   bấm đúp "OTL WiFi Link.command" hoặc  python3 otl_wifi_link.py   (chỉ thư viện chuẩn, Python ≥ 3.8)
        → mở Chrome (không có Chrome thì trình duyệt mặc định) trang otl_wifi_link.html.
        --demo: số liệu giả (chụp ảnh hướng dẫn, không đụng module thật) · --no-browser --port N: dùng cho bài kiểm.
        --sign <mã thử>: (máy O Tesla, cần _otl_secret.key) in mã mở chế độ kỹ thuật viên cho khách.
macOS: "OTL WiFi Link.command" + thư mục app/ (otl_wifi_link.py/.html/.css/.js, otl_wifi_motion.js, otl_wifi_guide.js,
        otl_aset.py, otl_artisan_template.aset, otl_wifi_vault.py, ed25519_tiny.py).
Trình duyệt không gửi được UDP nên dò tìm + lệnh AT chạy ở đây; trang HTML chỉ là giao diện.
Máy chủ chỉ nghe 127.0.0.1; lệnh ghi phải có header X-OTL (trang web lạ không gọi được).

Giao thức (đo trên module 7.04T.18 ngày 19/10/2026):
  · Dò:     gửi 'www.usr.cn' UDP cổng 48899 (broadcast) → '<ip>,<mac>,<mid>'
  · AT:     gửi '+ok' rồi 'AT+XXX\\r' cùng cổng       → '+ok=...\\r\\n\\r\\n' hoặc '+ERR=n'
  · Modbus: TCP server 8899, module tự đổi Modbus TCP ↔ RTU cho board (ID 1, ô 0 = BT, ô 1 = ET, ×10).
"""
import base64
import ipaddress
import json
import os
import platform
import re
import secrets
import socket
import struct
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # python3 -I bỏ thư mục script ⇒ thêm lại TRƯỚC khi nạp module riêng
import otl_aset  # noqa: E402
import otl_wifi_vault  # noqa: E402
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

DISCOVER_PORT = 48899
DISCOVER_MSG = b"www.usr.cn"
AT_QUIT = b"AT+Q\r"                  # thoát chế độ lệnh — phiên AT bỏ dở làm module KHÔNG trả lời dò (đo 19/10/2026)
AP_DEFAULT_IP = "10.10.100.254"      # IP module khi tự phát wifi
MODBUS_PORT = 8899
IDLE_EXIT_SEC = 90                   # trang đóng (không còn ping) quá lâu thì tự thoát
WIN_CHROME = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
              os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")]
TXN_ID = 0x4F54                      # mã giao dịch Modbus TCP riêng — lọc trả lời giữa luồng của máy khác
SWEEP_TIMEOUT = 0.4                  # giây chờ mỗi IP khi quét dự phòng cổng 8899
MODULE_OUI = "D4:AD:20"              # 3 byte đầu MAC module wifi đang dùng
STATIC = {"/app.css": ("otl_wifi_link.css", "text/css; charset=utf-8"),
          "/i18n.js": ("otl_wifi_i18n.js", "text/javascript; charset=utf-8"),
          "/app.js": ("otl_wifi_link.js", "text/javascript; charset=utf-8"),
          "/motion.js": ("otl_wifi_motion.js", "text/javascript; charset=utf-8"),
          "/guide.js": ("otl_wifi_guide.js", "text/javascript; charset=utf-8"),
          "/guide.pdf": ("Huong-dan_User-guide.pdf", "application/pdf"),
          "/guide-fr.pdf": ("Guide-utilisateur.pdf", "application/pdf")}
VERSION = "1.4"
BAUDS = (57600, 9600, 38400, 19200, 115200)   # thứ tự tự dò: tốc độ máy OTL hay dùng trước
TECH_BAUDS = (4800, 9600, 19200, 38400, 57600, 115200)
PROBE_IDS = (1, 2, 3, 4, 5)          # ID Modbus thử khi đọc (cài trên HMI máy, thường là 1)
PROBE_TIMEOUT = 0.8                  # giây chờ mỗi ID
PUBLIC_KEY_HEX = "22adb18a126b1dfea89ac2894db13bc30d4405c3da145d6b9ba6c4d2d018dfc1"   # = license_otl.py, chỉ KIỂM
TECH_PREFIX = b"OTL-WIFI-TECH:"
TECH_CHALLENGE_SEC = 1800            # mã thử sống 30 phút
AT_TRIES = 4                         # số lần hỏi lại khi module không đáp gói mở phiên lệnh


INFO_CMDS = ["AT+VER", "AT+WMODE", "AT+NETP", "AT+WANN", "AT+LANN", "AT+UART",
             "AT+WSSSID", "AT+WSKEY", "AT+WAP", "AT+WAKEY", "AT+TMODE", "AT+WSLK"]
SET_WAIT = 2.5                       # lệnh ghi (có '=') ghi bộ nhớ, trả chậm — chờ ít thì câu trả lời rơi sang lệnh sau
AT_REPLY = re.compile(r"\+(?:ok|ERR)[^\r\n]*")

# Chuẩn OTL của module (đo trên module đang chạy với Artisan 19/10/2026). Module mới mua để chế độ truyền thẳng
# (Through) ⇒ Artisan TCP không đọc được dù đúng tốc độ; AT+TMODE=Modbus bật chuyển Modbus TCP ↔ RTU.
STD_NETP = "TCP,Server,8899,10.10.100.100"
STD_UART_FMT = ["8", "1", "None", "NFC"]
STD_AP_SSID = "OTL Roaster"
MODES = ("AP", "STA")             # module không có AP+STA (AT+WMODE=APSTA → +ERR=-4, đo 19/10/2026)
BAD_CHARS = re.compile(r"[,\r\n]")   # dấu phẩy / xuống dòng làm vỡ cú pháp lệnh AT

_last_ping = time.time()


class UiError(Exception):
    """Lỗi có mã — trang HTML tự dịch câu báo theo ngôn ngữ đang chọn (VI / EN)."""

    def __init__(self, code: str, **params):
        super().__init__(code)
        self.code, self.params = code, params


def _base_dir():
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


# ── UDP: dò tìm + lệnh AT ────────────────────────────────────────────────────
def _xfer(sock, ip, msg, wait):
    """Gửi 1 gói, gom trả lời tới khi đủ khung AT hoặc hết giờ."""
    sock.sendto(msg, (ip, DISCOVER_PORT))
    buf, end = b"", time.time() + wait
    while time.time() < end:
        try:
            data, _ = sock.recvfrom(1024)
        except socket.timeout:
            continue
        buf += data
        if buf.endswith(b"\r\n\r\n") or (msg == DISCOVER_MSG and buf):
            break
    return buf


def _local_ips():
    """IP của máy tính trên các mạng đang nối. macOS: tên máy thường chỉ phân giải ra 127.0.0.1 ⇒ thêm mẹo
    'connect' UDP (không gửi gói nào) để hệ điều hành chỉ ra IP của card mạng đi tới địa chỉ đó."""
    ips = set()
    try:
        ips.update(info[4][0] for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET))
    except OSError:
        pass
    for probe in ("8.8.8.8", AP_DEFAULT_IP):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect((probe, 80))
            ips.add(s.getsockname()[0])
        except OSError:
            pass
        finally:
            s.close()
    return sorted(ip for ip in ips if not ip.startswith(("127.", "169.254.", "0.")))


def _local_broadcasts():
    return sorted({"255.255.255.255", AP_DEFAULT_IP} |
                  {str(ipaddress.ip_network(ip + "/24", strict=False).broadcast_address) for ip in _local_ips()})


def _local_prefixes():
    return sorted({ip.rsplit(".", 1)[0] for ip in _local_ips()})


def _port_open(ip, port=MODBUS_PORT):
    try:
        with socket.create_connection((ip, port), timeout=SWEEP_TIMEOUT):
            return True
    except OSError:
        return False


def _is_usr_web(ip):
    """Trang cài đặt module USR đòi đăng nhập với realm 'USR_module' — dấu nhận chắc chắn, không cần mật khẩu."""
    try:
        urllib.request.urlopen(f"http://{ip}/", timeout=1.5)
    except urllib.error.HTTPError as e:
        return e.code == 401 and "USR" in (e.headers.get("WWW-Authenticate") or "")
    except OSError:
        return False
    return False


ARP_LINE = re.compile(r"\(?(\d+\.\d+\.\d+\.\d+)\)?\s+(?:at\s+)?([0-9a-fA-F]{1,2}(?:[:-][0-9a-fA-F]{1,2}){5})")


def parse_arp(text):
    """Windows: '  192.168.1.180   d4-ad-20-d9-72-f1   dynamic'
    macOS:   '? (192.168.1.180) at d4:ad:20:d9:72:f1 on en0 ifscope [ethernet]' (macOS bỏ số 0 đầu: '0:1a:…')."""
    return {ip: ":".join(x.zfill(2) for x in re.split(r"[:-]", mac)).upper() for ip, mac in ARP_LINE.findall(text)}


def _arp_macs():
    args = ["arp", "-a"] if os.name == "nt" else ["arp", "-an"]   # -n: macOS khỏi tra tên (chậm)
    try:
        out = subprocess.run(args, capture_output=True, text=True, timeout=5,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
    except (OSError, subprocess.SubprocessError):
        return {}
    return parse_arp(out)


def sweep_tcp():
    """Dò dự phòng: wifi chặn UDP giữa thiết bị (đo 19/10/2026: ping + TCP qua, UDP 48899 mất)
    ⇒ quét /24 tìm cổng 8899 mở rồi xác nhận trang cài đặt USR. Module tìm kiểu này KHÔNG nhận lệnh AT."""
    hosts = [f"{p}.{i}" for p in _local_prefixes() for i in range(1, 255)]
    with ThreadPoolExecutor(max_workers=96) as ex:
        opened = [ip for ip, ok in zip(hosts, ex.map(_port_open, hosts)) if ok]
        usr = [ip for ip, ok in zip(opened, ex.map(_is_usr_web, opened)) if ok]
    macs = _arp_macs()
    return [{"ip": ip, "mac": macs.get(ip, ""), "via": "tcp"} for ip in usr]


_udp_sent = {"any": True}             # lần dò gần nhất có gửi được gói UDP nào không


def scan(wait=1.5):
    found = scan_udp(wait)
    if found:
        return found
    found = sweep_tcp()
    # macOS 15+: chưa cho Terminal quyền Mạng cục bộ ⇒ MỌI gói tới mạng LAN bị chặn ('No route to host') —
    # nếu không báo thì khách chỉ thấy "không có module" mà không biết vì sao.
    if not found and sys.platform == "darwin" and not _udp_sent["any"]:
        raise UiError("mac_lan")            # trang dịch: Cài đặt hệ thống → Quyền riêng tư → Mạng cục bộ → bật Terminal
    return found


def scan_udp(wait=1.5):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(0.2)
    found = {}
    try:
        sock.bind(("", 0))
        # KHÔNG phát rộng AT+Q: nhiều gói AT+Q dồn rồi mới dò thì module im (đo 19/10/2026). Module kẹt phiên lệnh
        # vẫn được quét TCP tìm ra; at_session gửi AT+Q THẲNG tới IP để gỡ kẹt.
        known = [ip for ip, mac in _arp_macs().items() if mac.startswith(MODULE_OUI)]
        _udp_sent["any"] = False
        for dst in _local_broadcasts() + known:     # gói phát rộng hay rơi trên wifi ⇒ thêm gói thẳng tới IP đã biết
            try:
                sock.sendto(DISCOVER_MSG, (dst, DISCOVER_PORT))
                _udp_sent["any"] = True
            except OSError:
                pass                    # mạng không tới được — bỏ qua địa chỉ đó
        end = time.time() + wait
        while time.time() < end:
            try:
                data, addr = sock.recvfrom(512)
            except socket.timeout:
                continue
            parts = data.decode("ascii", "replace").split(",")
            if len(parts) >= 2 and parts[0] == addr[0]:
                mac = parts[1].upper()
                found[mac] = {"ip": addr[0], "mac": ":".join(mac[i:i + 2] for i in range(0, len(mac), 2)), "via": "udp"}
    finally:
        sock.close()
    return sorted(found.values(), key=lambda m: m["ip"])


def _drain(sock, quiet=0.15):
    """Đọc bỏ mọi gói còn đợi tới khi im `quiet` giây."""
    old = sock.gettimeout()
    sock.settimeout(quiet)
    try:
        while True:
            sock.recvfrom(1024)
    except (socket.timeout, OSError):
        pass
    finally:
        sock.settimeout(old)


def at_session(ip, cmds, wait=1.0, raw=False):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(0.2)
    try:
        for _ in range(AT_TRIES):           # wifi rơi gói / module bận ⇒ thử lại (đo 19/10/2026: lúc có lúc không)
            sock.sendto(AT_QUIT, (ip, DISCOVER_PORT))   # gỡ kẹt phiên lệnh cũ (của mình hay công cụ khác)
            _drain(sock, 0.3)
            if _xfer(sock, ip, DISCOVER_MSG, 2.0):      # module đáp dò sau ~0,6 s
                break
        else:
            raise UiError("no_reply", ip=ip)
        _drain(sock, 0.6)                   # trả lời dò trùng / đến muộn không được lọt vào lệnh đầu
        sock.sendto(b"+ok", (ip, DISCOVER_PORT))
        _drain(sock, 0.3)
        out = []
        for cmd in cmds:
            _drain(sock, 0.1)
            data = _xfer(sock, ip, (cmd + "\r").encode("ascii"), SET_WAIT if "=" in cmd else wait)
            text = data.decode("utf-8", "replace")
            if raw:
                out.append((cmd, text))
                continue
            found = AT_REPLY.findall(text)
            out.append((cmd, found[-1] if found else ""))
        return out
    finally:
        try:
            sock.sendto(AT_QUIT, (ip, DISCOVER_PORT))   # LUÔN thoát chế độ lệnh, không để module kẹt
        except OSError:
            pass
        sock.close()


def _val(reply):
    return reply[4:] if reply.startswith("+ok=") else None


def module_info(ip):
    r = {c: _val(v) for c, v in at_session(ip, INFO_CMDS)}

    def field(cmd, i):
        v = r.get(cmd)
        parts = v.split(",") if v else []
        return parts[i] if i < len(parts) else None

    return {
        "ver": r.get("AT+VER"),
        "mode": r.get("AT+WMODE"),
        "netp": r.get("AT+NETP"),
        "wan_mode": field("AT+WANN", 0), "wan_ip": field("AT+WANN", 1),
        "wan_mask": field("AT+WANN", 2), "wan_gw": field("AT+WANN", 3),
        "lan_ip": field("AT+LANN", 0),
        "uart": r.get("AT+UART"),
        "sta_ssid": r.get("AT+WSSSID"),
        "sta_auth": field("AT+WSKEY", 0),          # KHÔNG trả mật khẩu wifi về trang
        "ap_ssid": field("AT+WAP", 1),
        "ap_auth": field("AT+WAKEY", 0),
        "tmode": r.get("AT+TMODE"),
        "link": r.get("AT+WSLK"),
    }


def std_issues(info):
    """Mục lệch chuẩn OTL: tmode · netp · uart_fmt · ap_name (tên wifi gốc của hãng, chỉ khi module đang phát wifi)."""
    out = []
    if (info.get("tmode") or "").lower() != "modbus":
        out.append("tmode")
    netp = (info.get("netp") or "").split(",")
    if len(netp) < 3 or netp[0].upper() != "TCP" or netp[1].lower() != "server" or netp[2] != str(MODBUS_PORT):
        out.append("netp")
    if (info.get("uart") or "").split(",")[1:5] != STD_UART_FMT:
        out.append("uart_fmt")
    if (info.get("mode") or "").upper() in ("AP", "APSTA") and (info.get("ap_ssid") or "").upper().startswith("USR"):
        out.append("ap_name")
    return out


def module_info_std(ip):
    info = module_info(ip)
    info["std"] = std_issues(info)
    return info


# ── Modbus TCP qua module (module tự đổi sang RTU cho board) ─────────────────
# Tốc độ + ID Modbus của máy rang cài trên HMI máy, mỗi máy có thể khác nhau.
# Module phải cùng tốc độ thì máy mới trả lời.
def _modbus_req(sock, uid, addr, count, timeout):
    """Một lệnh đọc FC 3 trên kết nối sẵn có → list giá trị · None nếu hết giờ · UiError nếu máy báo lỗi."""
    sock.sendall(struct.pack(">HHHBBHH", TXN_ID, 0, 6, uid, 3, addr, count))
    ok = struct.pack(">HHHBBB", TXN_ID, 0, 3 + 2 * count, uid, 3, 2 * count)
    exc = struct.pack(">HHHBB", TXN_ID, 0, 3, uid, 0x83)
    buf, end = b"", time.time() + timeout
    while time.time() < end:
        sock.settimeout(max(0.05, end - time.time()))
        try:
            data = sock.recv(512)
        except socket.timeout:
            break
        if not data:
            break
        buf += data
        i = buf.find(ok)
        if i >= 0 and len(buf) >= i + len(ok) + 2 * count:
            return list(struct.unpack(f">{count}h", buf[i + len(ok):i + len(ok) + 2 * count]))
        j = buf.find(exc)
        if j >= 0 and len(buf) > j + len(exc):
            raise UiError("modbus_exc", code=buf[j + len(exc)])
    return None


def probe(ip, port=MODBUS_PORT, ids=PROBE_IDS, timeout=PROBE_TIMEOUT):
    """Đọc BT / ET (ô 0, 1) lần lượt từng ID → {id, bt, et} của ID đầu tiên trả lời · None nếu không ID nào."""
    with socket.create_connection((ip, port), timeout=3) as s:
        for uid in ids:
            try:
                v = _modbus_req(s, uid, 0, 2, timeout)
            except UiError:
                continue                # máy trả lời nhưng báo lỗi ô — tốc độ đúng, thử ID khác
            if v:
                return {"id": uid, "bt": v[0] / 10, "et": v[1] / 10}
    return None


def modbus_bt_et(ip, port=MODBUS_PORT):
    r = probe(ip, port)
    if not r:
        raise UiError("modbus_timeout", ip=ip, port=port)
    return r


def modbus_read(ip, port, uid, addr, count):
    with socket.create_connection((ip, port), timeout=3) as s:
        v = _modbus_req(s, uid, addr, count, 1.5)
    if v is None:
        raise UiError("modbus_timeout", ip=ip, port=port)
    return v


# ── Tự động: dò tốc độ + ID, chỉnh module cho khớp máy rang ──────────────────
_auto = {"running": False, "log": [], "result": None, "t0": 0.0}
_auto_lock = threading.Lock()


def _log(ev, **params):
    _auto["log"].append({"code": ev, "params": params, "t": round(time.time() - _auto["t0"], 1)})


def _uart_baud(info):
    try:
        return int((info.get("uart") or "").split(",")[0])
    except ValueError:
        return None


def _netp_port(info):
    parts = (info.get("netp") or "").split(",")
    return int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else MODBUS_PORT


def set_uart(ip, baud):
    """Đổi tốc độ cổng nối máy rang (8N1) rồi khởi động lại module — tốc độ mới chỉ có hiệu lực sau khởi động lại."""
    (_, reply), = at_session(ip, [f"AT+UART={int(baud)},8,1,None,NFC"])
    if not reply.startswith("+ok"):
        raise UiError("at_refused", cmd="AT+UART", reply=reply[:40])
    at_session(ip, ["AT+Z"], wait=0.3)


def wait_module(mac, old_ip, port, timeout=60):
    """Chờ module khởi động lại, tìm lại theo MAC (IP có thể đổi). Wifi chặn UDP ⇒ nhận IP cũ khi cổng mở lại."""
    time.sleep(6)
    end = time.time() + timeout
    while time.time() < end:
        ap = _auto.get("ap")
        if ap and not otl_wifi_vault.pc_on(ap):
            try:
                otl_wifi_vault.pc_connect(ap, otl_wifi_vault.recall(ap), timeout=30)
                _wait_ap_ip()
            except OSError:
                pass                    # wifi module chưa phát lại — vòng sau thử tiếp
        for m in scan_udp(1.0):
            if m["mac"] == mac:
                time.sleep(1.5)         # cổng nối máy rang lên sau wifi một chút
                return m["ip"]
        if _port_open(old_ip, port):
            time.sleep(1.5)
            return old_ip
    return None


def _done(ok, **res):
    _auto["result"] = {"ok": ok, **res}
    return _auto["result"]


def auto_fix(ip, mac, nested=False):
    if not nested:
        _auto.update(running=True, log=[], result=None, t0=time.time(), ap=None, need=None)
    try:
        info = module_info(ip)
        cur = _uart_baud(info)
        issues = std_issues(info)
        fix = [i for i in issues if i != "ap_name"]
        if fix:                             # module mới / bị cài sai ⇒ đưa về chuẩn OTL rồi mới dò
            _log("std", items=",".join(fix))
            _write(ip, _std_cmds(fix, cur or BAUDS[0]))
            at_session(ip, ["AT+Z"], wait=0.3)
            ip = wait_module(mac, ip, MODBUS_PORT)
            if not ip:
                _log("lost")
                return _done(False, reason="lost")
            cur = cur or BAUDS[0]
        port = MODBUS_PORT if fix else _netp_port(info)
        _log("check", baud=cur)
        r = probe(ip, port)
        if r:
            _log("found", baud=cur, id=r["id"])
            return _finish(ip, port, cur, bool(fix), issues, r)
        _log("no_reply", baud=cur)
        for b in [x for x in BAUDS if x != cur]:
            _log("try", baud=b)
            set_uart(ip, b)
            ip = wait_module(mac, ip, port)
            if not ip:
                _log("lost")
                return _done(False, reason="lost")
            r = probe(ip, port)
            if r:
                _log("found", baud=b, id=r["id"])
                return _finish(ip, port, b, True, issues, r)
            _log("no_reply", baud=b)
        if cur:                         # không tốc độ nào khớp ⇒ trả module về như cũ
            _log("restore", baud=cur)
            set_uart(ip, cur)
            ip = wait_module(mac, ip, port) or ip
        return _done(False, reason="not_found", ip=ip)
    except UiError as e:
        _log("error", err=e.code)
        return _done(False, reason=e.code)
    except OSError as e:
        _log("error", err="net", msg=str(e)[:120])
        return _done(False, reason="net")
    except Exception as e:              # lỗi lập trình: báo ra nhật ký, không chết im
        _log("error", err="bug", msg=f"{type(e).__name__}: {e}"[:160])
        return _done(False, reason="bug")
    finally:
        if not nested:
            _auto["running"] = False


def _write(ip, cmds):
    for cmd, reply in at_session(ip, cmds):
        if not reply.startswith("+ok"):
            raise UiError("at_refused", cmd=cmd.split("=")[0], reply=reply[:40])


def _std_cmds(items, baud):
    cmds = []
    if "tmode" in items:
        cmds.append("AT+TMODE=Modbus")
    if "netp" in items:
        cmds.append("AT+NETP=" + STD_NETP)
    if "uart_fmt" in items:
        cmds.append(f"AT+UART={int(baud)}," + ",".join(STD_UART_FMT))
    return cmds


def _finish(ip, port, baud, changed, issues, r):
    renamed = False
    if "ap_name" in issues:             # sau cùng: máy tính đang bắt wifi gốc sẽ rớt, phải bắt lại "OTL Roaster"
        _log("ap_name", ssid=STD_AP_SSID)
        _write(ip, [f"AT+WAP=11BGN,{STD_AP_SSID},Auto"])
        at_session(ip, ["AT+Z"], wait=0.3)
        renamed = True
    return _done(True, ip=ip, port=port, baud=baud, changed=changed, renamed=renamed, ssid=STD_AP_SSID, **r)


# ── Cài trọn gói module mới / vừa reset: máy tính tự nối wifi module → chuẩn OTL + dò tốc độ → nối module vào wifi quán ─
_setup = {"orig": None, "made": [], "key_evt": threading.Event(), "key": None}


def _ap_label(ssid):
    """Wifi gốc của hãng mang tên hãng ⇒ trang chỉ hiện 4 ký tự cuối (không lộ tên hãng)."""
    return ("…" + ssid[-4:]) if ssid.upper().startswith("USR") else ssid


def _wait_ap_ip(timeout=20):
    end = time.time() + timeout
    while time.time() < end:
        if any(ip.startswith("10.10.100.") for ip in _local_ips()):
            return True
        time.sleep(1)
    return False


def pcwifi_state():
    mods = [{"ssid": n["ssid"], "label": _ap_label(n["ssid"]), "signal": n["signal"],
             "factory": n["ssid"].upper().startswith("USR")}
            for n in otl_wifi_vault.pc_visible() if otl_wifi_vault.is_module_ap(n["ssid"])]
    return {"current": otl_wifi_vault.pc_current(), "modules": mods}


def _join(ssid):
    _log("pc_join", ssid=_ap_label(ssid), factory=ssid.upper().startswith("USR"))
    if not otl_wifi_vault.pc_on(ssid):
        if otl_wifi_vault.pc_connect(ssid, otl_wifi_vault.recall(ssid)):
            _setup["made"].append(ssid)
    _auto["ap"] = ssid
    if not _wait_ap_ip():
        raise UiError("pc_join", ssid=_ap_label(ssid))


def _find_ap_module(timeout=45):
    end = time.time() + timeout
    while time.time() < end:
        ap = _auto.get("ap")
        if ap and not otl_wifi_vault.pc_on(ap):     # wifi module không có internet ⇒ Windows hay tự nhảy về wifi quán
            try:
                otl_wifi_vault.pc_connect(ap, otl_wifi_vault.recall(ap), timeout=30)
                _wait_ap_ip()
            except OSError:
                pass
        for m in scan_udp(1.2):
            if m["ip"] == AP_DEFAULT_IP:
                return m
        time.sleep(1)
    return None


def _pc_back():
    orig = _setup["orig"]
    _auto["ap"] = None
    if orig and not otl_wifi_vault.pc_on(orig):
        _log("pc_back", ssid=orig)
        try:
            otl_wifi_vault.pc_connect(orig, None, timeout=30)
        except OSError:
            pass
    for s in _setup["made"]:            # không để máy tự nhảy vào wifi module về sau (wifi đó không có internet)
        otl_wifi_vault.pc_forget(s)
    _setup["made"] = []


def setup_run(ap_ssid):
    _auto.update(running=True, log=[], result=None, t0=time.time(), ap=None, need=None)
    _setup.update(orig=None, made=[], key=None)
    _setup["key_evt"].clear()
    try:
        cur = otl_wifi_vault.pc_current()
        if cur and not otl_wifi_vault.is_module_ap(cur):
            _setup["orig"] = cur
        _join(ap_ssid)
        _log("find")
        m = _find_ap_module()
        if not m:
            _log("lost")
            _pc_back()
            return _done(False, reason="lost")
        r = auto_fix(m["ip"], m["mac"], nested=True)
        if not r.get("ok"):
            _pc_back()
            return r
        r = {k: v for k, v in r.items() if k != "ok"}   # _done(True, **r) mà r còn khoá "ok" ⇒ TypeError (lỗi chạy thật 19/10/2026)
        if r.get("renamed"):                    # wifi riêng vừa đổi tên ⇒ chờ module khởi động xong rồi máy tính nối "OTL Roaster"
            time.sleep(8)
            _join(STD_AP_SSID)
            m = _find_ap_module() or m
        orig = _setup["orig"]
        if not orig:                            # máy tính không có wifi quán ⇒ module chạy wifi riêng, xong
            return _done(True, **{**r, "ip": m["ip"], "mode": "AP", "ssid": STD_AP_SSID})
        key = otl_wifi_vault.recall(orig) or otl_wifi_vault.pc_key(orig)
        if key is None and otl_wifi_vault.pc_auth(orig) != "open":
            _auto["need"] = {"ssid": orig}      # không đọc được mật khẩu wifi quán ⇒ chờ người dùng gõ (hoặc bỏ qua)
            _log("need_key", ssid=orig)
            _setup["key_evt"].wait(timeout=600)
            _auto["need"] = None
            key = _setup["key"]
            if not key:                         # bỏ qua: giữ wifi riêng của module
                _pc_back()
                return _done(True, **{**r, "ip": m["ip"], "mode": "AP", "ssid": STD_AP_SSID})
        _log("sta", ssid=orig)
        _write(m["ip"], [f"AT+WSSSID={orig}", f"AT+WSKEY=WPA2PSK,AES,{key}" if key else "AT+WSKEY=OPEN,NONE",
                         "AT+WANN=DHCP", "AT+WMODE=STA"])
        if key:
            otl_wifi_vault.remember(orig, key)
        at_session(m["ip"], ["AT+Z"], wait=0.3)
        _pc_back()
        _log("find_shop", ssid=orig)
        ip = wait_module(m["mac"], "0.0.0.0", MODBUS_PORT, timeout=90)
        if not ip:
            _log("lost")
            return _done(False, reason="sta_lost", ssid=orig)
        pr = probe(ip, MODBUS_PORT)
        _log("found" if pr else "no_reply", baud=r.get("baud"), id=(pr or r).get("id"))
        return _done(True, **{**r, **(pr or {}), "ip": ip, "mode": "STA", "ssid": orig})
    except UiError as e:
        _log("error", err=e.code)
        _pc_back()
        return _done(False, reason=e.code)
    except OSError as e:
        _log("error", err="net", msg=str(e)[:120])
        _pc_back()
        return _done(False, reason="net")
    except Exception as e:              # lỗi lập trình: vẫn báo ra nhật ký + đưa máy tính về, không chết im
        _log("error", err="bug", msg=f"{type(e).__name__}: {e}"[:160])
        _pc_back()
        return _done(False, reason="bug")
    finally:
        _auto["running"] = False


def setup_start(req):
    ssid = _check_text(req.get("ssid"), "sta_ssid", 1, 32)
    if not otl_wifi_vault.is_module_ap(ssid):
        raise UiError("bad_input", msg="ssid")
    with _auto_lock:
        if _auto["running"]:
            raise UiError("busy")
        _auto["running"] = True
    threading.Thread(target=globals()["setup_run"], args=(ssid,), daemon=True).start()
    return {"started": True}


def setup_key(req):
    key = str(req.get("key") or "")
    if key:
        _check_text(key, "sta_key", 8, 63)
    _setup["key"] = key or None
    _setup["key_evt"].set()
    return {"ok": True}


def auto_start(req):
    ip = _check_ip(req.get("ip", ""), "module_ip")
    mac = str(req.get("mac", ""))[:17]
    with _auto_lock:
        if _auto["running"]:
            raise UiError("busy")
        _auto["running"] = True
    threading.Thread(target=globals()["auto_fix"], args=(ip, mac), daemon=True).start()
    return {"started": True}


def auto_state():
    return {k: _auto.get(k) for k in ("running", "log", "result", "need")}


# ── Wifi cho module: quét quanh module, gợi ý mật khẩu đã nhớ / máy tính đã lưu ─
def wifi_scan(ip):
    _check_ip(ip, "module_ip")
    (_, text), = at_session(ip, ["AT+WSCAN"], wait=8.0, raw=True)
    nets = otl_wifi_vault.parse_wscan(text)
    saved, pc = set(otl_wifi_vault.saved_names()), set(otl_wifi_vault.pc_known())
    for n in nets:
        n["saved"], n["pc"] = n["ssid"] in saved, n["ssid"] in pc
    return {"networks": nets}


def wifi_key(ssid):
    ssid = _check_text(ssid, "sta_ssid", 1, 32)
    key = otl_wifi_vault.recall(ssid)
    if key:
        return {"key": key, "source": "tool"}
    key = otl_wifi_vault.pc_key(ssid)
    return {"key": key, "source": "pc"} if key else {"key": None, "source": None}


def wifi_remember(req):
    ssid = _check_text(req.get("ssid"), "sta_ssid", 1, 32)
    key = str(req.get("key", ""))
    if key:
        _check_text(key, "sta_key", 8, 63)
    otl_wifi_vault.remember(ssid, key)
    return {"saved": True}


def wifi_forget(req):
    otl_wifi_vault.forget(_check_text(req.get("ssid"), "sta_ssid", 1, 32))
    return {"saved": False}


# ── Chẩn đoán: khách chép gửi O Tesla (không có mật khẩu) ────────────────────
def diagnostics(ip=None):
    lines = [f"OTL WiFi Link {VERSION} | {platform.system()} {platform.release()} | Python {platform.python_version()}",
             "PC IP: " + (", ".join(_local_ips()) or "-")]
    mods = scan_udp(1.5)
    lines.append("Modules (UDP): " + (", ".join(f"{m['ip']} {m['mac']}" for m in mods) or "none"))
    if ip:
        _check_ip(ip, "ip")
        try:
            info = module_info(ip)
            lines += [f"  {k}: {v}" for k, v in info.items()]
            r = probe(ip, _netp_port(info))
            lines.append(f"Test read: {r}" if r else "Test read: roaster not answering")
        except (UiError, OSError) as e:
            lines.append(f"Module {ip}: error {getattr(e, 'code', e)}")
    if _auto["log"]:
        lines.append("Auto log: " + json.dumps(_auto["log"][-30:], ensure_ascii=False))
        lines.append("Auto result: " + json.dumps(_auto["result"], ensure_ascii=False))
    return {"text": "\n".join(lines)}


# ── Chế độ kỹ thuật viên: mở bằng mã O Tesla ký (ed25519, khoá công khai như license) ─
_tech = {"challenge": None, "until": 0.0, "unlocked": False}


def tech_challenge():
    if not _tech["challenge"] or time.time() > _tech["until"]:
        _tech.update(challenge=secrets.token_hex(4).upper(), until=time.time() + TECH_CHALLENGE_SEC)
    return {"challenge": _tech["challenge"], "unlocked": _tech["unlocked"]}


def _code_bytes(code):
    s = re.sub(r"[^A-Z2-7]", "", str(code).upper())
    try:
        return base64.b32decode(s + "=" * (-len(s) % 8))
    except (ValueError, base64.binascii.Error):
        return b""


def tech_unlock(req):
    import ed25519_tiny                 # nạp muộn: chỉ cần khi mở chế độ kỹ thuật
    sig, ch = _code_bytes(req.get("code", "")), _tech["challenge"]
    if not ch or time.time() > _tech["until"] or len(sig) != 64 or \
            not ed25519_tiny.verify(sig, TECH_PREFIX + ch.encode(), bytes.fromhex(PUBLIC_KEY_HEX)):
        raise UiError("tech_bad")
    _tech["unlocked"] = True
    return {"unlocked": True}


def sign_code(challenge):
    """Chạy ở máy O Tesla (có tools/_otl_secret.key): python otl_wifi_link.py --sign <mã thử>."""
    import ed25519_tiny
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_otl_secret.key"), "rb") as f:
        sk = f.read()
    sig = ed25519_tiny.sign(TECH_PREFIX + challenge.strip().upper().encode(), sk, ed25519_tiny.publickey(sk))
    s = base64.b32encode(sig).decode().rstrip("=")
    return "-".join(s[i:i + 4] for i in range(0, len(s), 4))


def _need_tech():
    if not _tech["unlocked"]:
        raise UiError("tech_locked")


def tech_at(req):
    _need_tech()
    ip, cmd = _check_ip(req.get("ip", ""), "module_ip"), str(req.get("cmd", "")).strip()
    if not re.fullmatch(r"AT\+[A-Z0-9]+(=[^\r\n]{0,120})?", cmd):
        raise UiError("bad_cmd")
    (_, reply), = at_session(ip, [cmd])
    return {"cmd": cmd, "reply": reply}


def tech_read(req):
    _need_tech()
    ip = _check_ip(req.get("ip", ""), "module_ip")
    port, uid, addr, count = (int(req.get(k, d)) for k, d in (("port", MODBUS_PORT), ("id", 1), ("addr", 0), ("count", 2)))
    if not (1 <= uid <= 247 and 0 <= addr <= 65535 and 1 <= count <= 20):
        raise UiError("bad_input", msg="id 1-247, addr 0-65535, count 1-20")
    return {"values": modbus_read(ip, port, uid, addr, count)}


def tech_uart(req):
    _need_tech()
    ip, baud = _check_ip(req.get("ip", ""), "module_ip"), int(req.get("baud", 0))
    if baud not in TECH_BAUDS:
        raise UiError("bad_input", msg="baud")
    set_uart(ip, baud)
    new_ip = wait_module(str(req.get("mac", ""))[:17], ip, int(req.get("port", MODBUS_PORT)))
    return {"ip": new_ip, "baud": baud}


# ── Kiểm số liệu nhập + dựng lệnh ghi ────────────────────────────────────────
def _check_ip(v, field):
    try:
        ipaddress.IPv4Address(v)
    except ValueError:
        raise UiError("bad_ip", field=field, value=str(v)[:40])
    return v


def _check_text(v, field, lo, hi):
    if not isinstance(v, str) or not (lo <= len(v) <= hi) or BAD_CHARS.search(v):
        raise UiError("bad_text", field=field, lo=lo, hi=hi)
    return v


def build_apply_cmds(req):
    cmds = []
    wan = req.get("wan")
    if wan:
        if wan.get("dhcp"):
            cmds.append("AT+WANN=DHCP")
        else:
            ip = _check_ip(wan.get("ip", ""), "ip")
            mask = _check_ip(wan.get("mask", ""), "mask")
            gw = _check_ip(wan.get("gw", ""), "gw")
            cmds.append(f"AT+WANN=static,{ip},{mask},{gw}")
    sta = req.get("sta")
    if sta:
        cmds.append("AT+WSSSID=" + _check_text(sta.get("ssid"), "sta_ssid", 1, 32))
        key = sta.get("key", "")
        cmds.append("AT+WSKEY=OPEN,NONE" if key == "" else
                    "AT+WSKEY=WPA2PSK,AES," + _check_text(key, "sta_key", 8, 63))
    ap = req.get("ap")
    if ap:
        key = ap.get("key", "")
        cmds.append("AT+WAKEY=OPEN,NONE" if key == "" else
                    "AT+WAKEY=WPA2PSK,AES," + _check_text(key, "ap_key", 8, 63))
    mode = req.get("mode")
    if mode:
        if mode not in MODES:
            raise UiError("bad_mode")
        cmds.append("AT+WMODE=" + mode)
    if not cmds:
        raise UiError("nothing")
    return cmds


def apply_settings(req):
    ip = _check_ip(req.get("ip", ""), "module_ip")
    cmds = build_apply_cmds(req)
    # Trả về trang chỉ TÊN lệnh (phần trước '='): không gửi ngược mật khẩu wifi.
    results = [(c.split("=")[0], r) for c, r in at_session(ip, cmds)]
    if any(not r.startswith("+ok") for _, r in results):
        return {"results": results, "restarted": False}   # có lệnh hỏng ⇒ KHÔNG khởi động lại, giữ cấu hình đang chạy
    at_session(ip, ["AT+Z"], wait=0.3)  # khởi động lại để áp cấu hình mới (~10 s)
    return {"results": results, "restarted": True}


# ── Máy chủ web nội bộ ───────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _host_ok(self):
        return self.headers.get("Host", "").split(":")[0] in ("127.0.0.1", "localhost")

    def _run(self, fn):
        try:
            self._send(200, {"ok": True, "data": fn()})
        except UiError as e:
            self._send(200, {"ok": False, "code": e.code, "params": e.params})
        except OSError as e:            # mạng không tới được, bị từ chối kết nối…
            self._send(200, {"ok": False, "code": "net", "params": {"msg": str(e)[:160]}})
        except (ValueError, TypeError, AttributeError) as e:   # số liệu gửi lên sai kiểu (vd cổng không phải số)
            self._send(200, {"ok": False, "code": "bad_input", "params": {"msg": str(e)[:160]}})

    def do_GET(self):
        global _last_ping
        if not self._host_ok():
            return self._send(403, {"ok": False, "error": "host"})
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        _last_ping = time.time()
        if u.path in ("/", "/index.html"):
            with open(os.path.join(_base_dir(), "otl_wifi_link.html"), "rb") as f:
                return self._send(200, f.read(), "text/html; charset=utf-8")
        if u.path == "/api/ping":
            return self._send(200, {"ok": True})
        if u.path == "/api/scan":
            return self._run(scan)
        if u.path == "/api/info":
            return self._run(lambda: globals()["module_info_std"](_check_ip(q.get("ip", ""), "ip")))
        if u.path == "/api/test":
            return self._run(lambda: modbus_bt_et(_check_ip(q.get("ip", ""), "ip"),
                                                  int(q.get("port", MODBUS_PORT))))
        if u.path == "/api/auto":
            return self._run(auto_state)
        if u.path == "/api/diag":
            return self._run(lambda: diagnostics(q.get("ip") or None))
        if u.path == "/api/tech/challenge":
            return self._run(tech_challenge)
        if u.path == "/api/pcwifi":
            return self._run(lambda: globals()["pcwifi_state"]())
        if u.path == "/api/wifi/scan":
            return self._run(lambda: globals()["wifi_scan"](q.get("ip", "")))
        if u.path == "/api/aset":            # tệp cài đặt Artisan cho module đang chọn — bấm là tải về
            try:
                ip = _check_ip(q.get("ip", ""), "ip")
                opts = {k: q[k] for k in list(otl_aset.CHOICES) + ["prefix"] if k in q}   # tuỳ chọn cá nhân hoá (lọc trong otl_aset)
                data = otl_aset.make_aset(ip, int(q.get("port", MODBUS_PORT)), int(q.get("id", 1)), _base_dir(), opts).encode("utf-8")
            except (UiError, ValueError, OSError) as e:
                return self._send(400, {"ok": False, "error": str(e)})
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", f'attachment; filename="OTL-Artisan-{ip}.aset"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if u.path == "/api/wifi/key":
            return self._run(lambda: wifi_key(q.get("ssid", "")))
        if u.path in STATIC:
            fn, ctype = STATIC[u.path]
            for d in (_base_dir(), os.path.dirname(_base_dir()), os.path.dirname(os.path.dirname(_base_dir()))):   # macOS: PDF nằm ngoài thư mục app
                try:
                    with open(os.path.join(d, fn), "rb") as f:
                        return self._send(200, f.read(), ctype)
                except OSError:
                    continue
            return self._send(404, {"ok": False, "error": "không có"})
        self._send(404, {"ok": False, "error": "không có"})

    def do_POST(self):
        if not self._host_ok() or self.headers.get("X-OTL") != "1":
            return self._send(403, {"ok": False, "error": "chặn"})
        u = urlparse(self.path)
        if u.path == "/api/quit":
            self._send(200, {"ok": True})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        routes = {"/api/apply": apply_settings, "/api/auto": auto_start, "/api/tech/unlock": tech_unlock,
                  "/api/wifi/remember": wifi_remember, "/api/wifi/forget": wifi_forget,
                  "/api/setup": setup_start, "/api/setup/key": setup_key,
                  "/api/tech/at": tech_at, "/api/tech/read": tech_read, "/api/tech/uart": tech_uart}
        if u.path not in routes:
            return self._send(404, {"ok": False, "error": "không có"})
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        except (ValueError, json.JSONDecodeError):
            return self._send(400, {"ok": False, "error": "JSON hỏng"})
        fn = globals()[routes[u.path].__name__]  # tra lúc gọi: chế độ demo thay hàm
        return self._run(lambda: fn(body))


def _open_page(url):
    """Ưu tiên Chrome (quy ước của chủ máy); không có thì trình duyệt mặc định (Edge / Safari)."""
    try:
        if sys.platform == "darwin":
            if subprocess.run(["open", "-a", "Google Chrome", url], capture_output=True).returncode == 0:
                return
        else:
            chrome = next((p for p in WIN_CHROME if os.path.exists(p)), None)
            if chrome:
                subprocess.Popen([chrome, url])
                return
    except OSError:
        pass
    webbrowser.open(url)


def _idle_watch(server):
    while True:
        time.sleep(5)
        if time.time() - _last_ping > IDLE_EXIT_SEC and not _auto["running"]:   # đang dò dở thì không tắt
            server.shutdown()
            return


# ── Chế độ demo: số liệu giả để chụp ảnh hướng dẫn khách ─────────────────────
DEMO_MOD = {"ip": "192.168.1.50", "mac": "02:00:00:00:00:50", "via": "udp"}
DEMO_INFO = {"ver": "1.0", "mode": "STA", "netp": "TCP,Server,8899,10.10.100.100", "wan_mode": "DHCP",
             "wan_ip": "192.168.1.50", "wan_mask": "255.255.255.0", "wan_gw": "192.168.1.1", "lan_ip": "10.10.100.254",
             "uart": "9600,8,1,None,NFC", "sta_ssid": "Coffee-Shop", "sta_auth": "WPA2PSK",
             "ap_ssid": "OTL Roaster", "ap_auth": "OPEN", "tmode": "Modbus", "link": "Coffee-Shop"}


def _demo_auto(ip, mac):
    _auto.update(running=True, log=[], result=None, t0=time.time())
    for code, params, wait in (("check", {"baud": 9600}, 1), ("no_reply", {"baud": 9600}, 0.5),
                               ("try", {"baud": 57600}, 3), ("found", {"baud": 57600, "id": 1}, 0)):
        _log(code, **params)
        time.sleep(wait)
    DEMO_INFO["uart"] = "57600,8,1,None,NFC"
    _done(True, ip=ip, port=MODBUS_PORT, baud=57600, changed=True, id=1, bt=187.4, et=214.9)
    _auto["running"] = False


def _demo_setup(ssid):
    _auto.update(running=True, log=[], result=None, t0=time.time(), ap=None, need=None)
    for code, params, wait in (("pc_join", {"ssid": "…72F0", "factory": True}, 1.5), ("find", {}, 1), ("std", {"items": "tmode,netp"}, 2),
                               ("check", {"baud": 115200}, 1), ("no_reply", {"baud": 115200}, .4), ("try", {"baud": 57600}, 2.5),
                               ("found", {"baud": 57600, "id": 1}, .6), ("ap_name", {"ssid": "OTL Roaster"}, 1.5),
                               ("pc_join", {"ssid": "OTL Roaster", "factory": False}, 1.5), ("sta", {"ssid": "Coffee-Shop"}, 2),
                               ("pc_back", {"ssid": "Coffee-Shop"}, 1.5), ("find_shop", {"ssid": "Coffee-Shop"}, 2.5),
                               ("found", {"baud": 57600, "id": 1}, 0)):
        _log(code, **params)
        time.sleep(wait)
    DEMO_INFO["uart"] = "57600,8,1,None,NFC"
    _done(True, ip="192.168.1.50", port=MODBUS_PORT, baud=57600, id=1, bt=187.4, et=214.9, mode="STA", ssid="Coffee-Shop", changed=True)
    _auto["running"] = False


def _use_demo():
    global scan, module_info, modbus_bt_et, apply_settings, auto_fix, diagnostics, scan_udp, wifi_scan, setup_run, pcwifi_state
    scan_udp = lambda wait=1.5: [dict(DEMO_MOD)]
    module_info = lambda ip: dict(DEMO_INFO)
    def modbus_bt_et(ip, port=MODBUS_PORT):     # demo: 9600 lệch máy rang, tự dò sang 57600 mới trả lời
        if not DEMO_INFO["uart"].startswith("57600"):
            raise UiError("modbus_timeout", ip=ip, port=port)
        return {"id": 1, "bt": 187.4, "et": 214.9}
    apply_settings = lambda req: {"results": [[c, "+ok"] for c in ("AT+WANN",)], "restarted": True}
    auto_fix = _demo_auto
    setup_run = _demo_setup
    _demo_seen = {"n": 0}

    def pcwifi_state():                 # lần dò đầu: chưa có module trên mạng, thấy wifi gốc của module
        return {"current": "Coffee-Shop", "modules": [{"ssid": "USR-XXXX_72F0", "label": "…72F0", "signal": 96, "factory": True}]}

    def scan(wait=1.5):
        _demo_seen["n"] += 1
        time.sleep(1.2)
        return [] if _demo_seen["n"] == 1 and "--demo-new" in sys.argv else [dict(DEMO_MOD)]
    wifi_scan = lambda ip: {"networks": [
        {"ssid": "Coffee-Shop", "signal": 92, "ch": 6, "secure": True, "saved": True, "pc": True},
        {"ssid": "Coffee-Shop-5G", "signal": 71, "ch": 11, "secure": True, "saved": False, "pc": True},
        {"ssid": "Guest", "signal": 54, "ch": 1, "secure": False, "saved": False, "pc": False},
        {"ssid": "Neighbor", "signal": 23, "ch": 3, "secure": True, "saved": False, "pc": False}]}
    diagnostics = lambda ip=None: {"text": "OTL WiFi Link (demo)\nModules (UDP): 192.168.1.50 02:00:00:00:00:50"}


def main():
    if "--sign" in sys.argv:
        print(sign_code(sys.argv[sys.argv.index("--sign") + 1]))
        return
    if "--demo" in sys.argv:
        _use_demo()
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 0
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print("OTL WiFi Link:", url, flush=True)
    threading.Thread(target=_idle_watch, args=(server,), daemon=True).start()
    if "--no-browser" not in sys.argv:          # --no-browser: dùng cho bài kiểm, không bật cửa sổ
        _open_page(url)
    server.serve_forever()


if __name__ == "__main__":
    main()
