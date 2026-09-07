# -*- coding: utf-8 -*-
"""Kiểm kho khoá API — chạy: python tools/test_apikey.py"""
import io
import os
import shutil
import sys
import tempfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from otl_apikey import ApiKeyStore, _hash          # noqa: E402

FAIL = []


def ok(ten, dieu_kien, chi_tiet=""):
    print(("  ĐẠT  " if dieu_kien else "  SAI  ") + ten + ("  → " + str(chi_tiet) if chi_tiet else ""))
    if not dieu_kien:
        FAIL.append(ten)


def main():
    d = tempfile.mkdtemp(prefix="otl_apikey_")
    try:
        s = ApiKeyStore(d)
        print("1) Tạo khoá")
        r = s.add("MCP đọc", ["read"])
        ok("tạo được", r.get("ok"))
        key = r.get("key", "")
        ok("khoá có tiền tố otl_", key.startswith("otl_"), key[:12] + "…")
        ok("khoá đủ dài (>=64 hex)", len(key) >= 68, len(key))
        ok("có cảnh báo chỉ hiện 1 lần", "MỘT LẦN" in r.get("canh_bao", ""))

        print("\n2) Phạm vi quyền")
        ok("từ chối khi không có phạm vi", not s.add("rỗng", []).get("ok"))
        ok("bỏ phạm vi lạ", s.add("lạ", ["read", "xoá_sạch"])["scopes"] == ["read"])

        print("\n3) Xác thực")
        v = s.verify(key)
        ok("khoá đúng thì nhận", v is not None)
        ok("trả đúng phạm vi", v and v["scopes"] == ["read"], v and v["scopes"])
        ok("khoá sai thì từ chối", s.verify("otl_" + "0" * 64) is None)
        ok("chuỗi rỗng từ chối", s.verify("") is None)
        ok("thiếu tiền tố từ chối", s.verify("abc123") is None)

        print("\n4) KHÔNG lưu khoá trần trên đĩa")
        raw = io.open(os.path.join(d, "apikeys.json"), encoding="utf-8").read()
        ok("file không chứa khoá gốc", key not in raw)
        ok("file có chứa băm", _hash(key) in raw)

        print("\n5) Khoá / xoá")
        kid = r["id"]
        s.set_enabled(kid, False)
        ok("tắt rồi thì từ chối", s.verify(key) is None)
        s.set_enabled(kid, True)
        ok("bật lại thì nhận", s.verify(key) is not None)
        ok("xoá được", s.delete(kid).get("ok"))
        ok("xoá rồi thì từ chối", s.verify(key) is None)
        ok("xoá id không có → báo lỗi", not s.delete("khong_co").get("ok"))

        print("\n6) Còn nguyên sau khi mở lại (nạp từ đĩa)")
        r2 = s.add("điều khiển", ["read", "control"])
        s2 = ApiKeyStore(d)
        v2 = s2.verify(r2["key"])
        ok("khoá dùng được ở phiên mới", v2 is not None)
        ok("giữ đúng 2 phạm vi", v2 and sorted(v2["scopes"]) == ["control", "read"], v2 and v2["scopes"])
        ok("list không lộ băm", all("hash" not in k for k in s2.list()))
    finally:
        shutil.rmtree(d, ignore_errors=True)

    print("\nTẤT CẢ ĐẠT" if not FAIL else "\nCÓ %d PHÉP SAI: %s" % (len(FAIL), ", ".join(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
