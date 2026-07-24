"""
Nhật ký thao tác chống-sửa (hash-chain) — GĐ2 §16.3.

Mỗi dòng nhật ký ôm hash của dòng trước:
    hash_n = SHA256(hash_{n-1} + canon(bản_ghi_n))
Xoá/sửa/chèn một dòng giữa chừng là gãy chuỗi từ đó về sau — verify() chỉ đúng
điểm gãy. Không chống được kẻ ghi đè TOÀN BỘ file (cần HSM/append-only ngoài
tầm này), nhưng đủ để phát hiện chỉnh sửa lịch sử — mục tiêu GĐ2.

File: %LOCALAPPDATA%\\OTL Roast Lab HMI\\audit.log — mỗi dòng 1 JSON, append-only.
"""

import hashlib
import json
import os
import threading
import time

GENESIS = "0" * 64


def _canon(rec: dict) -> bytes:
    return json.dumps(rec, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


class AuditLog:
    def __init__(self, base_dir, log=None):
        self.base = base_dir
        self._path = os.path.join(base_dir, "audit.log")
        self._log = log or (lambda *a: None)
        self._lock = threading.Lock()
        os.makedirs(base_dir, exist_ok=True)
        self._last = self._tail_hash()

    def _tail_hash(self) -> str:
        """Hash của dòng cuối (để nối tiếp). File chưa có → GENESIS."""
        try:
            last = None
            with open(self._path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        last = line
            if last:
                return json.loads(last).get("h", GENESIS)
        except Exception:
            pass
        return GENESIS

    def append(self, user, action, field="", old="", new=""):
        """Thêm 1 dòng, ôm hash dòng trước. Trả bản ghi vừa ghi."""
        with self._lock:
            rec = {"ts": int(time.time() * 1000), "user": str(user or "?"),
                   "action": str(action), "field": str(field),
                   "old": "" if old is None else str(old),
                   "new": "" if new is None else str(new),
                   "prev": self._last}
            rec["h"] = hashlib.sha256(
                self._last.encode() + _canon({k: rec[k] for k in rec if k != "h"})
            ).hexdigest()
            try:
                with open(self._path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                self._last = rec["h"]
            except Exception:
                self._log("[AUDIT] ghi nhật ký thất bại", exc_info=False)
            return rec

    def tail(self, n=200):
        """n dòng gần nhất (mới ở đầu) cho UI."""
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                lines = [l for l in f if l.strip()]
            out = []
            for l in lines[-int(n):]:
                try:
                    out.append(json.loads(l))
                except Exception:
                    pass
            out.reverse()
            return out
        except Exception:
            return []

    def verify(self) -> dict:
        """Kiểm toàn chuỗi. Trả {ok, total, broken_at} — broken_at=None nếu nguyên vẹn."""
        prev = GENESIS
        i = 0
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    i += 1
                    rec = json.loads(line)
                    h = rec.get("h")
                    body = {k: rec[k] for k in rec if k != "h"}
                    calc = hashlib.sha256(prev.encode() + _canon(body)).hexdigest()
                    if rec.get("prev") != prev or calc != h:
                        return {"ok": False, "total": i, "broken_at": i}
                    prev = h
        except FileNotFoundError:
            return {"ok": True, "total": 0, "broken_at": None}
        except Exception as e:
            return {"ok": False, "total": i, "broken_at": i, "err": str(e)}
        return {"ok": True, "total": i, "broken_at": None}
