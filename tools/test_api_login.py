# -*- coding: utf-8 -*-
"""Bộ kiểm cửa ĐĂNG NHẬP API bằng tài khoản app (/api/v1/login).

Cần app OTL Roast Lab ĐANG CHẠY trên máy này, và mật khẩu đưa qua biến môi
trường — KHÔNG ghi PIN thật vào repo (repo này công khai):

    set OTL_TEST_USER=Master
    set OTL_TEST_PIN=****
    python tools/test_api_login.py

Thiếu một trong hai thứ đó thì BỎ QUA chứ không báo đỏ: máy nào không có app
chạy vẫn chạy được cả bộ kiểm còn lại.
"""
import json
import os
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8555/api/v1/"
TEN = os.environ.get("OTL_TEST_USER") or "Master"
MK = os.environ.get("OTL_TEST_PIN") or ""
_loi = []


def goi(duong, than=None, tok=""):
    """Trả (mã HTTP, dict). Lỗi HTTP cũng trả thân — chỗ này cần đọc err."""
    data = json.dumps(than).encode() if than is not None else None
    req = urllib.request.Request(BASE + duong, data=data,
                                 method="POST" if data is not None else "GET")
    if tok:
        req.add_header("Authorization", "Bearer " + tok)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8") or "{}")
        except ValueError:
            return e.code, {}


def kiem(ten, dieu_kien, ghi_chu=""):
    print(("  OK   " if dieu_kien else "  HỎNG ") + ten + (" → " + ghi_chu if ghi_chu else ""))
    if not dieu_kien:
        _loi.append(ten)


def main():
    if not MK:
        print("Chưa đặt OTL_TEST_PIN — BỎ QUA.")
        return 0
    try:
        urllib.request.urlopen(BASE + "snapshot", timeout=5)
    except urllib.error.HTTPError:
        pass                      # 401 là đúng: app có chạy, chỉ chưa có quyền
    except OSError:
        print("App không chạy ở 127.0.0.1:8555 — BỎ QUA.")
        return 0

    print("— cửa đăng nhập —")
    ma, r = goi("snapshot")
    kiem("chưa đăng nhập thì không đọc được", ma == 401 and r.get("err") == "pin")

    ma, r = goi("login", {"name": TEN, "pin": str(MK) + "9"})
    kiem("sai PIN bị từ chối", ma == 401 and r.get("err") in ("sai_pin", "locked"),
         str(r.get("err")))

    ma, r = goi("login", {"name": "khong-co-tai-khoan-nay", "pin": MK})
    kiem("tên lạ bị từ chối", ma == 401 and r.get("err") == "khong_co_tk")

    ma, r = goi("login", {"name": TEN, "pin": MK})
    kiem("đúng PIN thì cấp token", ma == 200 and bool(r.get("token")), str(r.get("err") or ""))
    tok = r.get("token") or ""
    pham = r.get("scopes") or []
    kiem("có phạm vi đọc", "read" in pham, ", ".join(pham))
    if r.get("role") == "master":
        kiem("master đủ ba phạm vi", len(pham) == 3, ", ".join(pham))
    else:
        kiem("thợ KHÔNG được phạm vi lái", "control" not in pham, ", ".join(pham))

    print("— token dùng được —")
    ma, r = goi("snapshot", tok=tok)
    kiem("đọc được trạng thái máy", ma == 200 and "state" in r)

    if "control" not in pham:
        ma, r = goi("write", {"name": "afterburner", "value": 0}, tok=tok)
        kiem("thiếu phạm vi lái thì bị chặn", ma == 403 and r.get("err") == "pham_vi")

    print("— trả phiên —")
    ma, r = goi("logout", {}, tok=tok)
    kiem("logout nhận", ma == 200 and r.get("ok") is True)
    ma, r = goi("snapshot", tok=tok)
    kiem("token cũ hết dùng được", ma == 401)

    print()
    if _loi:
        print("HỎNG %d mục: %s" % (len(_loi), "; ".join(_loi)))
        return 1
    print("TẤT CẢ ĐẠT")
    return 0


if __name__ == "__main__":
    sys.exit(main())
