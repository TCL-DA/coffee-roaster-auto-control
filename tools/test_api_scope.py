# -*- coding: utf-8 -*-
"""Kiểm PHẠM VI QUYỀN của khoá API qua HTTP thật.

Cần app đang chạy (python tools/roast_lab_hmi.py). Không chạy thì báo bỏ qua chứ
không coi là hỏng.  Chạy: python tools/test_api_scope.py

Tự tạo 3 khoá thử rồi TỰ XOÁ — không để lại khoá 'control' nằm trên máy.
"""
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request as U

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from otl_apikey import ApiKeyStore                      # noqa: E402
from otl_testdata import tim_thu_muc                    # noqa: E402

BASE = "http://127.0.0.1:8555"
DATA = os.path.join(HERE, "appdata")
FAIL = []


def call(path, key=None, body=None):
    r = U.Request(BASE + path,
                  data=json.dumps(body).encode() if body else None,
                  headers={"Content-Type": "application/json"} if body else {})
    if key:
        r.add_header("Authorization", "Bearer " + key)
    try:
        with U.urlopen(r, timeout=8) as x:
            return x.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


def kiem(nhan, got, mong):
    dat = got == mong
    print(("  ĐẠT  " if dat else "  SAI  ") + "%-46s HTTP %s (mong %s)" % (nhan, got, mong))
    if not dat:
        FAIL.append(nhan)


def main():
    if call("/api/state") == 0:
        print("App chưa chạy trên :8555 — BỎ QUA (không tính là hỏng).")
        return 0

    # Thư mục dữ liệu KHÔNG được ghim cứng: chạy dev thì app đọc tools/appdata,
    # còn bản EXE đóng gói đọc thư mục cạnh exe. Ghim cứng appdata làm khoá tạo
    # ra nằm chỗ máy chủ không đọc → mọi khoá hợp lệ bị 401 và bộ kiểm báo sai
    # hàng loạt trong khi phần quyền của app vẫn đúng.
    thu_muc, st = tim_thu_muc(BASE)
    if not st:
        print("Không tìm được thư mục dữ liệu của app đang chạy — BỎ QUA.")
        return 0
    print("Thư mục dữ liệu app đang dùng: %s" % thu_muc)
    print()
    for k in st.list():                      # dọn khoá thử sót từ lần trước
        if k["name"].startswith("test-scope-"):
            st.delete(k["id"])
    doc = st.add("test-scope-doc", ["read"])["key"]
    lai = st.add("test-scope-lai", ["read", "control"])["key"]
    cfg = st.add("test-scope-cfg", ["config"])["key"]
    ids = [k["id"] for k in st.list() if k["name"].startswith("test-scope-")]
    time.sleep(2.5)                          # chờ app nạp lại (hãm 2 giây)

    try:
        print("1) Khoá CHỈ ĐỌC")
        kiem("GET  snapshot", call("/api/snapshot", doc), 200)
        kiem("GET  v1/snapshot (bí danh)", call("/api/v1/snapshot", doc), 200)
        kiem("POST write — phải CẤM", call("/api/write", doc, {"name": "gas", "value": 0}), 403)
        kiem("POST mc_write — phải CẤM", call("/api/mc_write", doc, {"items": []}), 403)

        print("\n2) Khoá ĐỌC + LÁI MÁY")
        kiem("GET  snapshot", call("/api/snapshot", lai), 200)
        kiem("POST write — cho", call("/api/write", lai, {"name": "gas", "value": 0}), 200)
        kiem("POST mc_write — CẤM (thiếu config)", call("/api/mc_write", lai, {"items": []}), 403)

        print("\n3) Khoá CHỈ CẤU HÌNH")
        kiem("GET  snapshot — CẤM (thiếu read)", call("/api/snapshot", cfg), 403)
        kiem("POST mc_write — cho", call("/api/mc_write", cfg, {"items": []}), 200)
        kiem("POST write — CẤM", call("/api/write", cfg, {"name": "gas", "value": 0}), 403)

        print("\n4) Không khoá / khoá bịa")
        kiem("GET  không khoá", call("/api/snapshot"), 401)
        kiem("GET  khoá bịa", call("/api/snapshot", "otl_" + "0" * 64), 401)

        print("\n5) Khoá bị tắt thì hết dùng")
        st.set_enabled(ids[0], False)
        time.sleep(2.5)
        kiem("GET  khoá đã tắt", call("/api/snapshot", doc), 401)
    finally:
        for i in ids:                        # KHÔNG để khoá 'control' nằm lại trên máy
            st.delete(i)
        print("\n(đã xoá %d khoá thử)" % len(ids))

    print("\nTẤT CẢ ĐẠT" if not FAIL else "\nCÓ %d PHÉP SAI: %s" % (len(FAIL), ", ".join(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
