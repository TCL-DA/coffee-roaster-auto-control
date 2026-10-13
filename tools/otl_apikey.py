# -*- coding: utf-8 -*-
"""Khoá API có PHẠM VI QUYỀN cho app OTL Roast Lab.

Vì sao cần, khi đã có PIN web:
  PIN web là cửa cho NGƯỜI — thợ cầm điện thoại, nhập một lần, được làm mọi thứ.
  Khoá API là cửa cho MÁY — script, MCP server, trợ lý AI. Chúng chạy không ai
  ngồi cạnh, nên phải cấp quyền HẸP: đọc thì chỉ được đọc, không kèm quyền mở gas.

Ba phạm vi, đúng 3 tầng trong docs/plan/plan-mcp-api-extension.md:
  read     — đọc trạng thái máy, hồ sơ, lịch sử mẻ, kho
  config   — ghi tham số $M, cấu hình, hồ sơ, kho (firmware vẫn khoá khi máy bận)
  control  — LÁI MÁY: gas, nạp, xả, mồi lửa. Nguy hiểm nhất, cấp riêng.

Lưu trữ: apikeys.json cạnh exe (portable). CHỈ lưu BĂM của khoá, không lưu khoá
trần — lộ file cũng không dùng lại được. Khoá gốc hiện đúng MỘT LẦN lúc tạo.
"""
import hashlib
import hmac
import json
import os
import secrets
import threading
import time

SCOPES = ("read", "config", "control")
KEY_PREFIX = "otl_"
_FILE = "apikeys.json"
# Khoảng cách tối thiểu giữa 2 lần GHI ĐĨA mốc "dùng lần cuối". Mốc này chỉ để
# thợ nhìn khoá nào còn sống, không phải dữ liệu an toàn — không đáng một lần
# ghi đĩa mỗi request.
_LAST_USED_MIN_S = 300


def _hash(key: str) -> str:
    """SHA-256 là đủ: khoá là 32 byte ngẫu nhiên, không phải mật khẩu người nghĩ ra,
    nên không cần KDF chậm chống dò từ điển."""
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


class ApiKeyStore:
    def __init__(self, base_dir, log=None):
        self._path = os.path.join(base_dir, _FILE)
        self._lock = threading.Lock()
        self._log = log or (lambda *a, **k: None)
        self._data = {"keys": []}
        self._mtime = 0.0        # mtime lần nạp gần nhất
        self._last_try = 0.0     # lần thử nạp lại gần nhất (có hãm)
        self._load()

    # ── đĩa ────────────────────────────────────────────────────────────────
    def _load(self):
        try:
            self._mtime = os.path.getmtime(self._path)
            with open(self._path, encoding="utf-8") as f:
                d = json.load(f)
            if isinstance(d, dict) and isinstance(d.get("keys"), list):
                self._data = d
        except FileNotFoundError:
            pass
        except Exception:
            self._log("[APIKEY] apikeys.json hỏng — bắt đầu lại bằng danh sách rỗng")

    def _reload_if_changed(self):
        """Nạp lại khi file đổi. Cần vì tiến trình khác có thể tạo khoá (thợ tạo
        trong app trong lúc script đang chạy) — không có cái này thì phải khởi động
        lại app mới dùng được khoá mới, rất dễ tưởng là khoá hỏng.
        HÃM 2 giây: kẻ bắn khoá bịa liên tục không ép được đọc đĩa liên tục."""
        now = time.time()
        if now - self._last_try < 2.0:
            return
        self._last_try = now
        try:
            if os.path.getmtime(self._path) != self._mtime:
                self._load()
        except OSError:
            pass

    def _save(self):
        tmp = self._path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self._path)
        try:
            self._mtime = os.path.getmtime(self._path)   # bản của CHÍNH mình, khỏi nạp lại
        except OSError:
            pass
        try:                                   # ẩn bớt khỏi Explorer, không phải bảo mật
            if os.name == "nt":
                import ctypes
                ctypes.windll.kernel32.SetFileAttributesW(self._path, 2)
        except Exception:
            pass

    # ── quản lý ────────────────────────────────────────────────────────────
    def list(self):
        """Danh sách khoá — KHÔNG bao giờ trả băm ra ngoài."""
        with self._lock:
            return [{"id": k["id"], "name": k.get("name", ""),
                     "scopes": k.get("scopes", []),
                     "created": k.get("created", 0),
                     "last_used": k.get("last_used", 0),
                     "enabled": k.get("enabled", True)}
                    for k in self._data["keys"]]

    def add(self, name, scopes):
        """Tạo khoá mới. Trả về khoá GỐC — gọi xong là mất, không lấy lại được."""
        sc = [s for s in (scopes or []) if s in SCOPES]
        if not sc:
            return {"ok": False, "err": "phải chọn ít nhất một phạm vi: %s" % ", ".join(SCOPES)}
        raw = KEY_PREFIX + secrets.token_hex(32)
        rec = {"id": secrets.token_hex(6), "name": str(name or "")[:60],
               "scopes": sc, "hash": _hash(raw), "created": time.time(),
               "last_used": 0, "enabled": True}
        with self._lock:
            self._data["keys"].append(rec)
            self._save()
        self._log("[APIKEY] tạo khoá '%s' phạm vi %s", rec["name"], ",".join(sc))
        return {"ok": True, "key": raw, "id": rec["id"], "scopes": sc,
                "canh_bao": "Khoá này chỉ hiện MỘT LẦN. Chép ngay, mất là phải tạo khoá khác."}

    def delete(self, key_id):
        with self._lock:
            n = len(self._data["keys"])
            self._data["keys"] = [k for k in self._data["keys"] if k["id"] != key_id]
            if len(self._data["keys"]) == n:
                return {"ok": False, "err": "không có khoá id này"}
            self._save()
        self._log("[APIKEY] xoá khoá %s", key_id)
        return {"ok": True}

    def set_enabled(self, key_id, on):
        with self._lock:
            for k in self._data["keys"]:
                if k["id"] == key_id:
                    k["enabled"] = bool(on)
                    self._save()
                    return {"ok": True}
        return {"ok": False, "err": "không có khoá id này"}

    # ── kiểm khi có yêu cầu ────────────────────────────────────────────────
    def verify(self, raw):
        """Trả về bản ghi khoá (dict) nếu hợp lệ, None nếu không.
        So bằng compare_digest để không rò thông tin qua thời gian so sánh."""
        if not raw or not raw.startswith(KEY_PREFIX):
            return None
        h = _hash(raw)
        self._reload_if_changed()
        with self._lock:
            for k in self._data["keys"]:
                if not k.get("enabled", True):
                    continue
                if hmac.compare_digest(k.get("hash", ""), h):
                    # last_used cập nhật trong BỘ NHỚ mọi lần, nhưng chỉ GHI ĐĨA
                    # hoạ hoằn. Trước 2026-09-09 mỗi request hợp lệ là một lần
                    # ghi lại toàn bộ apikeys.json + os.replace: agent poll 1 Hz
                    # thành 86.400 lần ghi/ngày ngay trên máy đang bơm Modbus,
                    # và trong cửa sổ hãm 2 giây của _reload_if_changed thì bản
                    # ghi đè này có thể nuốt mất khoá vừa tạo ở tiến trình khác.
                    now = time.time()
                    cu = k.get("last_used") or 0
                    k["last_used"] = now
                    if now - cu >= _LAST_USED_MIN_S:
                        try:
                            self._save()
                        except Exception:
                            pass
                    return {"id": k["id"], "name": k.get("name", ""),
                            "scopes": list(k.get("scopes", []))}
        return None
