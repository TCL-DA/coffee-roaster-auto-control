# -*- coding: utf-8 -*-
"""Kiểm MCP server tầng đọc — nói chuyện qua stdio đúng như Claude sẽ gọi.

Cần app đang chạy (:8555). Không chạy thì báo bỏ qua.
Chạy: python tools/test_mcp_roaster.py

Tự tạo khoá 'read' rồi TỰ XOÁ.
"""
import io
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from otl_apikey import ApiKeyStore                    # noqa: E402

SERVER = os.path.join(HERE, "mcp_roaster", "server.py")
DATA = os.path.join(HERE, "appdata")
FAIL = []


def ok(ten, dieu_kien, chi_tiet=""):
    print(("  ĐẠT  " if dieu_kien else "  SAI  ") + ten
          + ("  → " + str(chi_tiet)[:80] if chi_tiet else ""))
    if not dieu_kien:
        FAIL.append(ten)


class Mcp:
    """Bọc tiến trình MCP: gửi JSON-RPC một dòng, đọc một dòng."""

    def __init__(self, key):
        env = dict(os.environ, OTL_API_KEY=key or "",
                   OTL_API_BASE="http://127.0.0.1:8555",
                   PYTHONIOENCODING="utf-8")
        self.p = subprocess.Popen(
            [sys.executable, SERVER], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env=env, text=True, encoding="utf-8", bufsize=1)
        self._id = 0

    def goi(self, method, params=None):
        self._id += 1
        self.p.stdin.write(json.dumps(
            {"jsonrpc": "2.0", "id": self._id, "method": method,
             "params": params or {}}, ensure_ascii=False) + "\n")
        self.p.stdin.flush()
        line = self.p.stdout.readline()
        return json.loads(line) if line.strip() else {}

    def cong_cu(self, ten, args=None):
        r = self.goi("tools/call", {"name": ten, "arguments": args or {}})
        res = r.get("result") or {}
        return (res.get("content") or [{}])[0].get("text", ""), bool(res.get("isError"))

    def dong(self):
        try:
            self.p.stdin.close()
            self.p.wait(timeout=5)
        except Exception:
            self.p.kill()


def app_song():
    try:
        urllib.request.urlopen("http://127.0.0.1:8555/api/state", timeout=4).read()
        return True
    except urllib.error.HTTPError:
        return True
    except Exception:
        return False


def main():
    if not app_song():
        print("App chưa chạy trên :8555 — BỎ QUA (không tính là hỏng).")
        return 0

    st = ApiKeyStore(DATA)
    for k in st.list():
        if k["name"].startswith("test-mcp-"):
            st.delete(k["id"])
    key = st.add("test-mcp-doc", ["read"])["key"]
    kid = [k["id"] for k in st.list() if k["name"] == "test-mcp-doc"][0]
    time.sleep(2.5)                                    # chờ app nạp lại khoá

    m = Mcp(key)
    try:
        print("1) Bắt tay MCP")
        r = m.goi("initialize")
        ok("initialize trả kết quả", "result" in r)
        ok("đúng tên server", (r.get("result") or {}).get("serverInfo", {}).get("name")
           == "otl-roaster-read")

        print("\n2) Danh sách công cụ")
        tools = (m.goi("tools/list").get("result") or {}).get("tools") or []
        ten = [t["name"] for t in tools]
        ok("có công cụ", len(tools) >= 8, len(tools))
        ok("mọi công cụ đều là ĐỌC (không có ghi/lái)",
           not [t for t in ten if any(x in t for x in ("write", "set", "ghi", "lai", "control"))],
           ten)
        ok("có roaster_trang_thai", "roaster_trang_thai" in ten)
        ok("mọi công cụ có mô tả", all(t.get("description") for t in tools))

        print("\n3) Gọi công cụ thật")
        txt, loi = m.cong_cu("roaster_kiem_tra")
        ok("roaster_kiem_tra chạy", not loi, txt[:70])
        ok("báo nối được app", '"noi_duoc": true' in txt.replace(" ", " "), txt[:70])

        txt, loi = m.cong_cu("roaster_ho_so")
        ok("roaster_ho_so chạy", not loi)
        ok("đọc được hồ sơ", "profiles" in txt, txt[:60])

        txt, loi = m.cong_cu("roaster_trang_thai")
        ok("roaster_trang_thai chạy", not loi, txt[:60])

        print("\n4) Báo lỗi phải ĐỌC ĐƯỢC, không phải mã số")
        txt, loi = m.cong_cu("roaster_duong_cong_me")          # thiếu tham số
        ok("thiếu tham số → báo lỗi", loi)
        ok("nói rõ thiếu gì", "ma_me" in txt, txt[:60])

        txt, loi = m.cong_cu("khong_co_cong_cu_nay")
        ok("công cụ lạ → báo lỗi", loi, txt[:60])
    finally:
        m.dong()

    print("\n5) Khoá SAI thì phải nói rõ lý do")
    m2 = Mcp("otl_" + "0" * 64)
    try:
        txt, loi = m2.cong_cu("roaster_ho_so")
        ok("khoá sai → báo lỗi", loi)
        ok("nói rõ là do khoá", "OTL_API_KEY" in txt or "khoá" in txt, txt[:90])
    finally:
        m2.dong()

    print("\n6) KHÔNG có đường nào lái máy")
    src = io.open(SERVER, encoding="utf-8").read()
    ok("không dùng POST", "POST" not in src and "method=" not in src.replace("method\", ", ""))
    ok("không có /api/v1/write trong danh sách cho phép", "/api/v1/write" not in src)

    st.delete(kid)
    print("(đã xoá khoá thử)")
    print("\nTẤT CẢ ĐẠT" if not FAIL else "\nCÓ %d PHÉP SAI: %s" % (len(FAIL), ", ".join(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
