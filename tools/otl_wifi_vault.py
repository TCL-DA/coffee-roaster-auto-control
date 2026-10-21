"""Wifi cho OTL WiFi Link: quét wifi quanh module, nhớ mật khẩu wifi trên máy tính, đọc wifi máy tính đã lưu.

Mật khẩu KHÔNG lưu chữ thường:
  · Windows — DPAPI (CryptProtectData, gắn tài khoản Windows đang đăng nhập) → %APPDATA%\\OTL WiFi Link\\wifi.json
  · macOS   — Keychain (lệnh `security`, dịch vụ "OTL WiFi Link"); wifi.json chỉ giữ TÊN wifi
  · hệ khác — không nhớ mật khẩu (chỉ nhớ tên)
Chỉ dùng thư viện chuẩn (bản macOS chạy bằng python3 có sẵn).
"""
import base64
import json
import os
import re
import subprocess
import sys
import tempfile
import time

SERVICE = "OTL WiFi Link"
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _cfg_dir():
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.path.expanduser("~/.config")
    d = os.path.join(base, SERVICE)
    os.makedirs(d, exist_ok=True)
    return d


def _store_path():
    return os.path.join(_cfg_dir(), "wifi.json")


def _load():
    try:
        with open(_store_path(), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(data):
    tmp = _store_path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, _store_path())


# ── Windows DPAPI ────────────────────────────────────────────────────────────
def _dpapi(data, protect):
    import ctypes
    from ctypes import wintypes

    class Blob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    buf = ctypes.create_string_buffer(data, len(data))
    src = Blob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    dst = Blob()
    crypt = ctypes.windll.crypt32
    ok = (crypt.CryptProtectData(ctypes.byref(src), SERVICE, None, None, None, 0, ctypes.byref(dst)) if protect
          else crypt.CryptUnprotectData(ctypes.byref(src), None, None, None, None, 0, ctypes.byref(dst)))
    if not ok:
        raise OSError("DPAPI")
    try:
        return ctypes.string_at(dst.pbData, dst.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(dst.pbData)


# ── macOS Keychain ───────────────────────────────────────────────────────────
def _keychain_set(ssid, key):
    subprocess.run(["security", "add-generic-password", "-U", "-s", SERVICE, "-a", ssid, "-w", key],
                   capture_output=True, timeout=10, check=True)


def _keychain_get(ssid):
    r = subprocess.run(["security", "find-generic-password", "-s", SERVICE, "-a", ssid, "-w"],
                       capture_output=True, text=True, timeout=10)
    return r.stdout.rstrip("\n") if r.returncode == 0 else None


def _keychain_del(ssid):
    subprocess.run(["security", "delete-generic-password", "-s", SERVICE, "-a", ssid], capture_output=True, timeout=10)


# ── Kho nhớ dùng chung ───────────────────────────────────────────────────────
def remember(ssid, key):
    data = _load()
    if os.name == "nt":
        data[ssid] = base64.b64encode(_dpapi(key.encode("utf-8"), True)).decode()
    elif sys.platform == "darwin":
        _keychain_set(ssid, key)
        data[ssid] = "keychain"
    else:
        data[ssid] = ""                 # hệ khác: chỉ nhớ tên
    _save(data)


def recall(ssid):
    v = _load().get(ssid)
    if v is None:
        return None
    try:
        if os.name == "nt" and v:
            return _dpapi(base64.b64decode(v), False).decode("utf-8")
        if sys.platform == "darwin" and v == "keychain":
            return _keychain_get(ssid)
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    return None


def forget(ssid):
    data = _load()
    if data.pop(ssid, None) is not None:
        if sys.platform == "darwin":
            _keychain_del(ssid)
        _save(data)


def saved_names():
    return sorted(_load())


# ── Wifi máy tính đã lưu (gợi ý mật khẩu khi nối module vào wifi quán) ───────
def _run(args, timeout=10):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout, creationflags=_NO_WINDOW,
                              encoding="utf-8", errors="replace").stdout
    except (OSError, subprocess.SubprocessError):
        return ""


# ── Wifi CỦA MÁY TÍNH: quét xung quanh, nối sang wifi module, quay lại ───────
# Module vừa reset / mới mua phát wifi gốc của hãng (tên bắt đầu "USR-", mở); module chuẩn OTL phát "OTL Roaster".
MODULE_AP = re.compile(r"^(USR-|OTL Roaster$)", re.I)


def is_module_ap(ssid):
    return bool(MODULE_AP.match(ssid or ""))


# macOS 14.4+ / 15: Terminal chưa có quyền Vị trí thì mọi tên wifi bị thay bằng "<redacted>" — coi như KHÔNG biết tên
# (không được đem "<redacted>" đi làm tên wifi quán cho module).
_HIDDEN = re.compile(r"^<.*redacted.*>$", re.I)
MODULE_NET = "10.10.100."           # mạng của wifi riêng module (module là 10.10.100.254)


def _clean_ssid(name):
    name = (name or "").strip()
    return None if not name or _HIDDEN.match(name) else name


def _mac_dev():
    m = re.search(r"Hardware Port: (?:Wi-Fi|AirPort)\s*\nDevice: (\S+)", _run(["networksetup", "-listallhardwareports"]))
    return m.group(1) if m else "en0"


def _mac_ip():
    return _run(["ipconfig", "getifaddr", _mac_dev()]).strip()


def pc_current():
    """Tên wifi máy tính đang nối (None nếu không nối hoặc macOS giấu tên)."""
    if os.name == "nt":
        out = _run(["netsh", "wlan", "show", "interfaces"])
        m = re.search(r"^\s+SSID\s+:\s(.+)$", out, re.M)       # 'BSSID' không khớp vì phải bắt đầu bằng 'SSID'
        return _clean_ssid(m.group(1)) if m else None
    if sys.platform == "darwin":
        dev = _mac_dev()
        m = re.search(r"Current Wi-Fi Network:\s*(.+)", _run(["networksetup", "-getairportnetwork", dev]))
        name = _clean_ssid(m.group(1)) if m else None
        if not name:                                           # macOS 15: networksetup không còn báo tên — hỏi ipconfig
            m = re.search(r"^\s*SSID\s*:\s*(.+)$", _run(["ipconfig", "getsummary", dev]), re.M)
            name = _clean_ssid(m.group(1)) if m else None
        return name
    return None


def pc_on(ssid):
    """Máy tính đang ở wifi `ssid`? Biết tên thì so tên. macOS giấu tên ⇒ đoán theo IP: wifi module cấp 10.10.100.x,
    wifi quán thì không — đủ để biết đã sang được wifi module / đã về lại wifi quán."""
    cur = pc_current()
    if cur is not None:
        return cur == ssid
    if sys.platform != "darwin":
        return False
    ip = _mac_ip()
    if not ip or ip.startswith("169.254."):
        return False
    return ip.startswith(MODULE_NET) if is_module_ap(ssid) else not ip.startswith(MODULE_NET)


def _win_rescan():
    """Bắt Windows quét wifi ngay (netsh chỉ trả danh sách cũ trong bộ nhớ). Lỗi thì bỏ qua — vẫn còn danh sách cũ."""
    try:
        import ctypes
        from ctypes import wintypes

        class GUID(ctypes.Structure):
            _fields_ = [("a", wintypes.DWORD), ("b", wintypes.WORD), ("c", wintypes.WORD), ("d", ctypes.c_ubyte * 8)]

        class IfInfo(ctypes.Structure):
            _fields_ = [("guid", GUID), ("desc", ctypes.c_wchar * 256), ("state", ctypes.c_uint)]

        class IfList(ctypes.Structure):
            _fields_ = [("n", wintypes.DWORD), ("i", wintypes.DWORD), ("items", IfInfo * 1)]

        wlan = ctypes.windll.wlanapi
        h, ver = wintypes.HANDLE(), wintypes.DWORD()
        if wlan.WlanOpenHandle(2, None, ctypes.byref(ver), ctypes.byref(h)):
            return False
        try:
            lst = ctypes.POINTER(IfList)()
            if wlan.WlanEnumInterfaces(h, None, ctypes.byref(lst)):
                return False
            try:
                n = lst.contents.n
                items = ctypes.cast(ctypes.byref(lst.contents.items), ctypes.POINTER(IfInfo * n)).contents
                for it in items:
                    wlan.WlanScan(h, ctypes.byref(it.guid), None, None, None)
            finally:
                wlan.WlanFreeMemory(lst)
        finally:
            wlan.WlanCloseHandle(h, None)
        return True
    except (OSError, AttributeError, ValueError):
        return False


def pc_visible(rescan=True):
    """Wifi máy tính thấy quanh nó: [{ssid, signal}] (sóng mạnh trước)."""
    nets = {}
    if os.name == "nt":
        if rescan and _win_rescan():
            time.sleep(3.5)
        cur = None
        for line in _run(["netsh", "wlan", "show", "networks", "mode=bssid"]).splitlines():
            m = re.match(r"^SSID \d+\s*:\s?(.*)$", line)
            if m:
                cur = m.group(1).strip()
                if cur:
                    nets.setdefault(cur, 0)
                continue
            s = re.search(r":\s*(\d{1,3})\s*%", line)
            if cur and s:
                nets[cur] = max(nets[cur], int(s.group(1)))
    elif sys.platform == "darwin":
        nets = parse_mac_airport(_run(["system_profiler", "-json", "SPAirPortDataType"], timeout=25))
    return sorted(({"ssid": k, "signal": v} for k, v in nets.items() if _clean_ssid(k)), key=lambda n: -n["signal"])


def _rssi_pct(sn):
    """'-52 dBm / -92 dBm' → % sóng (cùng thang Windows: -100 dBm = 0 %, -50 dBm = 100 %)."""
    m = re.match(r"\s*(-?\d+)\s*dBm", str(sn or ""))
    return max(0, min(100, 2 * (int(m.group(1)) + 100))) if m else 0


def parse_mac_airport(text):
    """`system_profiler -json SPAirPortDataType` → {ssid: % sóng}. Dùng bản JSON vì bản chữ dịch theo ngôn ngữ máy
    ("Other Local Wi-Fi Networks" thành "Autres réseaux Wi-Fi locaux" trên Mac tiếng Pháp). Tên bị giấu thì bỏ."""
    try:
        data = json.loads(text or "{}")
    except ValueError:
        return {}
    nets = {}
    for block in data.get("SPAirPortDataType") or []:
        for itf in block.get("spairport_airport_interfaces") or []:
            seen = list(itf.get("spairport_airport_other_local_wireless_networks") or [])
            cur = itf.get("spairport_current_network_information")
            if isinstance(cur, dict):
                seen.append(cur)
            for n in seen:
                name = _clean_ssid(n.get("_name") if isinstance(n, dict) else None)
                if name:
                    nets[name] = max(nets.get(name, 0), _rssi_pct(n.get("spairport_signal_noise")))
    return nets


def _xml(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _win_profile(ssid, key):
    sec = (f"<authEncryption><authentication>WPA2PSK</authentication><encryption>AES</encryption><useOneX>false</useOneX></authEncryption>"
           f"<sharedKey><keyType>passPhrase</keyType><protected>false</protected><keyMaterial>{_xml(key)}</keyMaterial></sharedKey>") if key else \
          "<authEncryption><authentication>open</authentication><encryption>none</encryption><useOneX>false</useOneX></authEncryption>"
    return ('<?xml version="1.0"?><WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">'
            f"<name>{_xml(ssid)}</name><SSIDConfig><SSID><name>{_xml(ssid)}</name></SSID></SSIDConfig>"
            # 'auto': module khởi động lại (~10 s mất wifi) thì Windows tự nối lại, công cụ không mất module giữa chừng
            f"<connectionType>ESS</connectionType><connectionMode>auto</connectionMode><MSM><security>{sec}</security></MSM></WLANProfile>")


def pc_connect(ssid, key=None, timeout=60):
    """Nối máy tính vào wifi `ssid`. Trả True nếu công cụ TẠO hồ sơ mới (để xoá khi quay lại). Lỗi ⇒ OSError.

    Lặp tới khi nối được: module vừa khởi động lại (đổi tên wifi) thì vài giây đầu wifi CHƯA phát, Windows chỉ biết danh
    sách quét cũ nên `netsh wlan connect` hỏng ngay và không tự thử lại (đo 19/10/2026: "OTL Roaster" sau AT+Z) ⇒ quét lại,
    thấy wifi trong danh sách mới rồi mới nối, hỏng thì quét + nối lại."""
    created = False
    if os.name == "nt" and ssid not in pc_known():
        with tempfile.TemporaryDirectory() as d:
            fn = os.path.join(d, "otl.xml")
            with open(fn, "w", encoding="utf-8") as f:
                f.write(_win_profile(ssid, key))
            _run(["netsh", "wlan", "add", "profile", f"filename={fn}", "user=current"])
        created = True
    if os.name != "nt" and sys.platform != "darwin":
        raise OSError("unsupported")
    end = time.time() + timeout
    while time.time() < end:
        if pc_on(ssid):
            return created
        if os.name == "nt":
            if not any(n["ssid"] == ssid for n in pc_visible(rescan=True)):
                continue                        # wifi chưa phát — quét lại vòng sau
            _run(["netsh", "wlan", "connect", f"name={ssid}", f"ssid={ssid}"])
        else:
            # networksetup chỉ in chữ khi hỏng ("Could not find network …" — wifi chưa phát lại) ⇒ chờ rồi thử lại
            out = _run(["networksetup", "-setairportnetwork", _mac_dev(), ssid] + ([key] if key else []), timeout=40)
            if out.strip():
                time.sleep(3)
        t2 = min(end, time.time() + 12)
        while time.time() < t2:
            if pc_on(ssid):
                return created
            time.sleep(1)
    raise OSError(f"join {ssid}")


def pc_auth(ssid):
    """'open' / 'secured' theo hồ sơ wifi máy tính đã lưu (Windows); không có hồ sơ hoặc không phải Windows ⇒ None."""
    if os.name != "nt":
        return None
    with tempfile.TemporaryDirectory() as d:
        _run(["netsh", "wlan", "export", "profile", f"name={ssid}", f"folder={d}"])
        for fn in os.listdir(d):
            m = re.search(r"<authentication>([^<]*)</authentication>", open(os.path.join(d, fn), encoding="utf-8", errors="replace").read())
            if m:
                return "open" if m.group(1).lower() == "open" else "secured"
    return None


def pc_forget(ssid):
    """Xoá hồ sơ wifi công cụ đã tạo (không để máy tính tự nhảy vào wifi module về sau — wifi đó không có internet)."""
    if os.name == "nt":
        _run(["netsh", "wlan", "delete", "profile", f"name={ssid}"])
    elif sys.platform == "darwin":
        _run(["networksetup", "-removepreferredwirelessnetwork", _mac_dev(), ssid])


def pc_known():
    """Tên wifi máy tính đã lưu. Windows: export XML (không phụ thuộc ngôn ngữ Windows). macOS: networksetup."""
    if os.name == "nt":
        with tempfile.TemporaryDirectory() as d:
            _run(["netsh", "wlan", "export", "profile", f"folder={d}"])
            names = []
            for fn in os.listdir(d):
                m = re.search(r"<name>([^<]*)</name>", open(os.path.join(d, fn), encoding="utf-8", errors="replace").read())
                if m:
                    names.append(m.group(1))
            return sorted(set(names))
    if sys.platform == "darwin":
        out = _run(["networksetup", "-listpreferredwirelessnetworks", _mac_dev()])
        return sorted({n for n in (_clean_ssid(ln) for ln in out.splitlines()[1:]) if n})
    return []


def pc_key(ssid):
    """Mật khẩu wifi máy tính đã lưu (Windows; cần quyền đọc khoá — không có thì trả None). macOS: không đọc (Keychain hỏi)."""
    if os.name != "nt":
        return None
    with tempfile.TemporaryDirectory() as d:
        _run(["netsh", "wlan", "export", "profile", f"name={ssid}", "key=clear", f"folder={d}"])
        for fn in os.listdir(d):
            m = re.search(r"<keyMaterial>([^<]*)</keyMaterial>", open(os.path.join(d, fn), encoding="utf-8", errors="replace").read())
            if m:
                return m.group(1)
    return None


# ── Quét wifi quanh module (AT+WSCAN) ────────────────────────────────────────
_SCAN_ROW = re.compile(r"^(\d{1,3})%,(.*),([0-9a-fA-F:]{17}),(\d+),([^,]*),([^,;]*);?$")


def parse_wscan(text):
    """'RSSI,SSID,BSSID,Channel,Encryption,Authentication' mỗi dòng; firmware có dòng rác 'Siganl(%)…' — bỏ.
    Trùng tên (nhiều trạm phát) giữ sóng mạnh nhất."""
    best = {}
    for line in text.replace("\r", "").split("\n"):
        m = _SCAN_ROW.match(line.strip())
        if not m:
            continue
        sig, ssid, _bssid, ch, enc, auth = m.groups()
        if not ssid.strip():
            continue
        cur = best.get(ssid)
        if cur is None or int(sig) > cur["signal"]:
            best[ssid] = {"ssid": ssid, "signal": min(int(sig), 100), "ch": int(ch),
                          "secure": auth.upper() not in ("OPEN", "") or enc.upper() not in ("NONE", "")}
    return sorted(best.values(), key=lambda n: -n["signal"])
