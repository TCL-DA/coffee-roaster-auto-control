"""
Auth OTL Roast Lab — kiểm PIN phía PYTHON, không phải trong trình duyệt (GĐ2 §16.1/16.3).

Vì sao dời khỏi JS:
  - Trước GĐ2, PIN băm PBKDF2 rồi so TRONG localStorage → ai mở DevTools/sửa file
    JSON là qua mặt. Dời phép so xuống Python + trộn PEPPER bọc DPAPI (khoá theo
    user Windows, KHÔNG nằm trong file nào đọc thẳng được) → xoá %LOCALAPPDATA%
    cũng không giả được hash, copy users.json sang máy khác cũng vô dụng.
  - Lockout đếm ở Python: đóng app / xoá localStorage KHÔNG reset bộ đếm sai
    (trước đây reset được → dò PIN thoải mái).

Lưu ở %LOCALAPPDATA%\\OTL Roast Lab HMI:
  auth.json   — {users:[{name,role,salt,hash,perms,enabled}], locks:{name:{fails,until}}}
  .pepper     — DPAPI blob (chỉ user Windows này giải được); Linux/dev → pepper thường

hash = PBKDF2-HMAC-SHA256(pin, salt+PEPPER, 200k). PEPPER trộn vào salt nên
thiếu pepper (bê file sang máy khác) là hash không bao giờ khớp.
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
import threading
import time

PBKDF2_ITERS = 200_000
LOCK_THRESHOLD = 7                    # sai 7 lần mới bắt đầu khoá
LOCK_MINUTES = (1, 3, 5)             # lần khoá 1/2/3+; từ lần 3 giữ 5 phút


def _dpapi_protect(data: bytes) -> bytes:
    """Bọc DPAPI (Windows). Ngoài Windows → trả nguyên (dev/Linux)."""
    try:
        import ctypes
        from ctypes import wintypes

        class BLOB(ctypes.Structure):
            _fields_ = [("cbData", wintypes.DWORD),
                        ("pbData", ctypes.POINTER(ctypes.c_char))]

        buf = ctypes.create_string_buffer(data, len(data))
        blob_in = BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
        blob_out = BLOB()
        if not ctypes.windll.crypt32.CryptProtectData(
                ctypes.byref(blob_in), None, None, None, None, 0,
                ctypes.byref(blob_out)):
            raise OSError("CryptProtectData thất bại")
        out = ctypes.string_at(blob_out.pbData, blob_out.cbData)
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)
        return out
    except Exception:
        return data


def _dpapi_unprotect(data: bytes) -> bytes:
    try:
        import ctypes
        from ctypes import wintypes

        class BLOB(ctypes.Structure):
            _fields_ = [("cbData", wintypes.DWORD),
                        ("pbData", ctypes.POINTER(ctypes.c_char))]

        buf = ctypes.create_string_buffer(data, len(data))
        blob_in = BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
        blob_out = BLOB()
        if not ctypes.windll.crypt32.CryptUnprotectData(
                ctypes.byref(blob_in), None, None, None, None, 0,
                ctypes.byref(blob_out)):
            raise OSError("CryptUnprotectData thất bại")
        out = ctypes.string_at(blob_out.pbData, blob_out.cbData)
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)
        return out
    except Exception:
        return data


class Auth:
    def __init__(self, base_dir, log=None):
        self.base = base_dir
        self._path = os.path.join(base_dir, "auth.json")
        self._pepper_path = os.path.join(base_dir, ".pepper")
        self._log = log or (lambda *a: None)
        self._lock = threading.Lock()
        os.makedirs(base_dir, exist_ok=True)
        self._pepper = self._load_pepper()
        self._data = self._load()

    # ── pepper (DPAPI) ──────────────────────────────────────────────────────
    def _load_pepper(self) -> bytes:
        try:
            with open(self._pepper_path, "rb") as f:
                return _dpapi_unprotect(f.read())
        except FileNotFoundError:
            pep = secrets.token_bytes(32)
            try:
                with open(self._pepper_path, "wb") as f:
                    f.write(_dpapi_protect(pep))
                if os.name == "nt":            # ẩn file cho gọn
                    import ctypes
                    ctypes.windll.kernel32.SetFileAttributesW(self._pepper_path, 2)
            except Exception:
                self._log("[AUTH] không ghi được .pepper — pepper phiên tạm")
            return pep
        except Exception:
            self._log("[AUTH] .pepper hỏng — tạo pepper phiên tạm")
            return secrets.token_bytes(32)

    # ── lưu / đọc ───────────────────────────────────────────────────────────
    def _load(self) -> dict:
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                d = json.load(f)
            d.setdefault("users", [])
            d.setdefault("locks", {})
            return d
        except Exception:
            return {"users": [], "locks": {}}

    def _save(self):
        tmp = self._path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self._path)

    # ── băm ─────────────────────────────────────────────────────────────────
    def _hash(self, pin: str, salt_hex: str) -> str:
        salt = bytes.fromhex(salt_hex) + self._pepper
        return hashlib.pbkdf2_hmac("sha256", str(pin).encode(), salt,
                                   PBKDF2_ITERS).hex()

    def _find(self, name):
        for u in self._data["users"]:
            if u["name"] == name:
                return u
        return None

    # ── API ─────────────────────────────────────────────────────────────────
    def state(self) -> dict:
        """Cho UI vẽ màn đăng nhập: danh sách user (KHÔNG kèm hash) + đã setup chưa."""
        with self._lock:
            users = [{"name": u["name"], "role": u["role"],
                      "enabled": u.get("enabled", True),
                      "perms": u.get("perms", {})}
                     for u in self._data["users"]]
            return {"setup": len(users) > 0, "users": users}

    def setup_master(self, pin: str) -> dict:
        """Lần đầu chạy: tạo tài khoản master. Đã có user thì từ chối."""
        with self._lock:
            if self._data["users"]:
                return {"ok": False, "err": "đã có tài khoản"}
            salt = secrets.token_hex(16)
            self._data["users"].append({
                "name": "Master", "role": "master", "salt": salt,
                "hash": self._hash(pin, salt), "perms": {}, "enabled": True})
            self._save()
            return {"ok": True, "user": {"name": "Master", "role": "master", "perms": {}}}

    def _lock_left(self, name) -> int:
        st = self._data["locks"].get(name)
        if not st:
            return 0
        return max(0, int(st.get("until", 0) - time.time()))

    def login(self, name: str, pin: str) -> dict:
        """Kiểm PIN. Trả ok + hồ sơ user, hoặc lý do (khoá còn n giây / sai còn n lần)."""
        with self._lock:
            u = self._find(name)
            if not u:
                return {"ok": False, "err": "khong_co_tk"}
            if not u.get("enabled", True):
                return {"ok": False, "err": "tk_khoa"}
            left = self._lock_left(name)
            if left > 0:
                return {"ok": False, "err": "locked", "left": left}
            # tài khoản di cư từ JS: verify bằng đường legacy (không pepper), đúng
            # thì NÂNG CẤP sang hash có pepper ngay để lần sau đi đường chuẩn
            ok = False
            if u.get("legacy"):
                if hmac.compare_digest(self._hash_legacy(pin, u["salt"]), u["hash"]):
                    ok = True
                    u["salt"] = secrets.token_hex(16)
                    u["hash"] = self._hash(pin, u["salt"])
                    u.pop("legacy", None)
                    self._log("[AUTH] nâng cấp hash có pepper cho '%s'", name)
            elif hmac.compare_digest(self._hash(pin, u["salt"]), u["hash"]):
                ok = True
            if ok:
                self._data["locks"].pop(name, None)     # đăng nhập được → xoá bộ đếm
                self._save()
                return {"ok": True, "user": {"name": u["name"], "role": u["role"],
                                             "perms": u.get("perms", {})}}
            # sai PIN → tăng bộ đếm, tính khoá
            st = self._data["locks"].get(name, {"fails": 0, "until": 0})
            st["fails"] += 1
            if st["fails"] >= LOCK_THRESHOLD:
                lvl = st["fails"] - LOCK_THRESHOLD          # 0,1,2,...
                mins = LOCK_MINUTES[min(lvl, len(LOCK_MINUTES) - 1)]
                st["until"] = time.time() + mins * 60
            self._data["locks"][name] = st
            self._save()
            if self._lock_left(name) > 0:
                return {"ok": False, "err": "locked", "left": self._lock_left(name)}
            return {"ok": False, "err": "sai_pin", "left_tries": LOCK_THRESHOLD - st["fails"]}

    # ── quản lý tài khoản thợ (chỉ master, UI tự gác quyền) ─────────────────
    def add_operator(self, name: str, pin: str, perms=None) -> dict:
        with self._lock:
            name = str(name).strip()[:24]
            if not name:
                return {"ok": False, "err": "thiếu tên"}
            if self._find(name):
                return {"ok": False, "err": "trùng tên"}
            salt = secrets.token_hex(16)
            self._data["users"].append({
                "name": name, "role": "slave", "salt": salt,
                "hash": self._hash(pin, salt), "perms": perms or {}, "enabled": True})
            self._save()
            return {"ok": True}

    def set_operator(self, name: str, perms=None, enabled=None) -> dict:
        with self._lock:
            u = self._find(name)
            if not u or u["role"] == "master":
                return {"ok": False, "err": "không sửa được"}
            if perms is not None:
                u["perms"] = perms
            if enabled is not None:
                u["enabled"] = bool(enabled)
            self._save()
            return {"ok": True}

    def del_operator(self, name: str) -> dict:
        with self._lock:
            u = self._find(name)
            if not u or u["role"] == "master":
                return {"ok": False, "err": "không xoá được"}
            self._data["users"] = [x for x in self._data["users"] if x["name"] != name]
            self._data["locks"].pop(name, None)
            self._save()
            return {"ok": True}

    def change_pin(self, name: str, old_pin: str, new_pin: str) -> dict:
        with self._lock:
            u = self._find(name)
            if not u:
                return {"ok": False, "err": "khong_co_tk"}
            if not hmac.compare_digest(self._hash(old_pin, u["salt"]), u["hash"]):
                return {"ok": False, "err": "sai_pin_cu"}
            u["salt"] = secrets.token_hex(16)
            u["hash"] = self._hash(new_pin, u["salt"])
            self._save()
            return {"ok": True}

    # ── di cư từ localStorage (bản cũ băm trong JS, KHÔNG có pepper) ────────
    def migrate_from_js(self, js_users: dict) -> dict:
        """Nhận {list:[{name,role,salt,pin,perms,enabled}]} từ localStorage cũ.

        KHÔNG biết PIN gốc nên không băm lại kèm pepper được → giữ hash JS cũ,
        đánh dấu legacy=True. Lần đăng nhập ĐÚNG đầu tiên (verify bằng đường
        legacy) sẽ băm lại có pepper và xoá cờ. Chỉ chạy khi CHƯA có auth.json."""
        with self._lock:
            if self._data["users"]:
                return {"ok": False, "err": "đã có tài khoản Python"}
            n = 0
            for u in (js_users or {}).get("list", []):
                if not u.get("name") or not u.get("salt") or not u.get("pin"):
                    continue
                self._data["users"].append({
                    "name": u["name"], "role": u.get("role", "slave"),
                    "salt": u["salt"], "hash": u["pin"],   # hash JS cũ (không pepper)
                    "perms": u.get("perms", {}), "enabled": u.get("enabled", True),
                    "legacy": True})
                n += 1
            if n:
                self._save()
            return {"ok": n > 0, "count": n}

    def _hash_legacy(self, pin: str, salt_hex: str) -> str:
        """Băm KIỂU JS cũ: PBKDF2 150k, KHÔNG pepper — chỉ để verify bản di cư."""
        return hashlib.pbkdf2_hmac("sha256", str(pin).encode(),
                                   bytes.fromhex(salt_hex), 150_000).hex()
