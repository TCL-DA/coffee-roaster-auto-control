# -*- coding: utf-8 -*-
"""CLI gọi API của app Roast Lab đang chạy trên MÁY NÀY.

Vì sao có file này thay vì gọi curl thẳng: luật quyền của Claude Code khớp theo
TIỀN TỐ, nên cho phép `curl` là cho phép curl đi bất kỳ đâu trên Internet. File
này chỉ nói chuyện được với 127.0.0.1 (chốt cứng bên dưới), nên cấp quyền cho
riêng nó là cấp đúng phần cần, không hơn.

    python tools/otl_api.py dangnhap Master <PIN>  # đăng nhập bằng tài khoản app
    python tools/otl_api.py trangthai            # máy đang thế nào
    python tools/otl_api.py doc snapshot         # đọc một tuyến bất kỳ
    python tools/otl_api.py lenh afterburner 1   # bắn một lệnh (cần lease)
    python tools/otl_api.py lease mo|nhip|dong

HAI CÁCH VÀO, dùng cách nào cũng được:
  · ĐĂNG NHẬP tài khoản app (dễ nhất): `dangnhap <tên> <PIN>` — đúng tài khoản
    vẫn dùng ở màn khoá của app. Token 8 giờ, cất ở tools/dist/apitoken.json.
    Master được cả ba phạm vi; thợ chỉ đọc (+ ghi cấu hình nếu có quyền
    calib gas / model nhiệt).
  · KHOÁ API: tạo trong app (Cài đặt → Khoá API & MCP) — hợp cho thứ chạy nền
    dài ngày, vì khoá không hết hạn và cấp được phạm vi hẹp.

Thứ tự lấy: cờ --key → biến OTL_API_KEY → token đăng nhập còn hạn →
tools/dist/apikey.txt.

CẢNH BÁO: `lenh` chạm vào MÁY THẬT — xi-lanh, quạt, và bếp gas. App có lease,
trần lệnh và chặn bước nhảy, nhưng không cái nào thay được người đứng cạnh máy.
"""
import argparse
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request

# CHỐT CỨNG: chỉ gọi được máy nội bộ. Không nhận host từ dòng lệnh — nhận là
# file này thành một cái curl đội lốt, mất sạch ý nghĩa của việc thu hẹp quyền.
HOST = "127.0.0.1"
CONG = {"app": 8555, "serial": 8765}
ROOT = pathlib.Path(__file__).resolve().parent


def _tep_token():
    """Chỗ cất token đăng nhập. Cạnh apikey.txt — tức trong tools/dist/, thư mục
    đã bị .gitignore chặn, nên không có đường vô tình đẩy lên repo PUBLIC."""
    return (ROOT / "dist" if (ROOT / "dist").is_dir() else ROOT) / "apitoken.json"


def doc_token():
    """Token đăng nhập còn hạn, hoặc "" nếu chưa có / đã hết hạn."""
    try:
        d = json.loads(_tep_token().read_text(encoding="utf-8"))
        if float(d.get("het_luc", 0)) > time.time():
            return str(d.get("token") or "")
    except Exception:
        pass
    return ""


def luu_token(tok, ten, phams, ttl):
    """Ghi qua tệp tạm rồi os.replace. Ghi ĐÈ THẲNG là dính WinError 5: lần trước
    đã đặt thuộc tính ẩn cho tệp, mà Windows từ chối mở tệp ẩn bằng chế độ 'w'."""
    t = _tep_token()
    tmp = t.with_suffix(".tmp")
    tmp.write_text(json.dumps({"token": tok, "ten": ten, "scopes": phams,
                               "het_luc": time.time() + float(ttl or 0)},
                              ensure_ascii=False), encoding="utf-8")
    os.replace(str(tmp), str(t))
    if os.name == "nt":        # ẩn bớt khỏi Explorer — gọn mắt, không phải bảo mật
        try:
            import ctypes
            ctypes.windll.kernel32.SetFileAttributesW(str(t), 2)
        except Exception:
            pass


def lay_khoa(cli=None):
    if cli:
        return cli
    if os.environ.get("OTL_API_KEY"):
        return os.environ["OTL_API_KEY"]
    tok = doc_token()
    if tok:
        return tok
    for p in (ROOT / "dist" / "apikey.txt", ROOT / "apikey.txt"):
        if p.exists():
            k = p.read_text(encoding="utf-8").strip()
            if k:
                return k
    return ""


def goi(tuyen, khoa, du_lieu=None, cong="app", timeout=8):
    url = f"http://{HOST}:{CONG[cong]}/api/v1/{tuyen.lstrip('/')}"
    data = json.dumps(du_lieu).encode() if du_lieu is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    if khoa:
        req.add_header("Authorization", "Bearer " + khoa)
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace") or "{}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return json.loads(raw)
        except Exception:
            return {"ok": False, "err": f"HTTP {e.code}", "msg": raw[:300]}
    except Exception as e:
        return {"ok": False, "err": "khong_goi_duoc",
                "msg": f"{e} — app đã chạy chưa? cổng {CONG[cong]}"}


def in_json(o):
    print(json.dumps(o, ensure_ascii=False, indent=1))


def trangthai(khoa):
    s = goi("snapshot", khoa)
    d = (s or {}).get("data") or {}
    f = d.get("flags") or {}
    if not d:
        in_json(s)
        return 1
    print(f"kết nối : {s.get('state')} · {s.get('mode')} · {s.get('port')} "
          f"· trễ {s.get('age_ms')}ms")
    print(f"nhiệt   : BT {d.get('bt')}  ET {d.get('et')}  SV {d.get('sv')}")
    print(f"đầu ra  : gas {d.get('gas')}  gió {d.get('air')}  trống {d.get('drum')}")
    print(f"mẻ      : bước {d.get('step')}  t={d.get('t_roast')}s")
    bat = [k for k, v in f.items() if v is True]
    print("cờ BẬT  : " + (", ".join(bat) if bat else "(không có)"))
    L = goi("lease", khoa)
    print(f"lượt lái: {'CÓ người/AI đang lái' if L.get('dang_lai') else 'đang rảnh'}")
    return 0


def main():
    p = argparse.ArgumentParser(description="Gọi API app Roast Lab trên máy này")
    p.add_argument("viec", choices=["dangnhap", "dangxuat", "trangthai", "doc",
                                    "lenh", "lease", "luat"])
    p.add_argument("a", nargs="?", default="")
    p.add_argument("b", nargs="?", default="")
    p.add_argument("--key", default="")
    p.add_argument("--cong", default="app", choices=list(CONG))
    p.add_argument("--khong-mo-app", action="store_true", dest="khong_mo_app",
                   help="đăng nhập nhưng ĐỪNG mở khoá màn hình app (cho script nền)")
    p.add_argument("--khoa-app", action="store_true", dest="khoa_app",
                   help="đăng xuất thì khoá luôn màn hình app")
    n = p.parse_args()
    if n.viec == "dangnhap":
        ten = n.a or os.environ.get("OTL_API_USER") or "Master"
        mk = n.b or os.environ.get("OTL_API_PIN") or ""
        if not mk:
            print("dùng: dangnhap <tên tài khoản> <PIN>   ví dụ: dangnhap Master 0000")
            return 2
        r = goi("login", "", {"name": ten, "pin": mk,
                              "mo_khoa_app": not n.khong_mo_app}, cong=n.cong)
        if not r.get("ok"):
            in_json(r)
            return 1
        luu_token(r["token"], r.get("name"), r.get("scopes"), r.get("het_han_s"))
        gio = int(float(r.get("het_han_s") or 0) // 3600)
        print("Đã đăng nhập: %s (%s) · phạm vi %s · còn %d giờ"
              % (r.get("name"), r.get("role"), ", ".join(r.get("scopes") or []), gio))
        if r.get("mo_khoa_app"):
            print("Màn hình app cũng đã MỞ KHOÁ theo tài khoản này.")
        elif not n.khong_mo_app:
            print("(Màn hình app không nhận lệnh mở khoá — app có đang mở không?)")
        print("Token cất ở %s — các lệnh sau tự dùng, khỏi truyền gì thêm."
              % _tep_token())
        return 0

    khoa = lay_khoa(n.key)
    if n.viec == "dangxuat":
        r = goi("logout", khoa, {"khoa_app": n.khoa_app}, cong=n.cong) \
            if khoa else {"ok": False}
        try:
            _tep_token().unlink()
        except OSError:
            pass
        print("Đã trả phiên." if r.get("ok") else "Không có phiên nào đang mở.")
        return 0
    if not khoa and n.viec != "luat":
        print("Chưa đăng nhập. Cách nhanh nhất:\n"
              "  python tools/otl_api.py dangnhap Master <PIN>\n"
              "Hoặc dùng khoá API (Cài đặt → Khoá API & MCP) rồi\n"
              "  set OTL_API_KEY=otl_...   hoặc lưu vào tools/dist/apikey.txt")
        return 2

    if n.viec == "trangthai":
        return trangthai(khoa)
    if n.viec == "luat":
        in_json(goi("lease", khoa)); return 0
    if n.viec == "doc":
        in_json(goi(n.a or "snapshot", khoa)); return 0
    if n.viec == "lease":
        m = {"mo": "lease_open", "nhip": "lease_beat", "dong": "lease_close"}
        if n.a not in m:
            print("dùng: lease mo|nhip|dong"); return 2
        body = {"agent": "claude-code", "reason": n.b or "thao tác thủ công"} \
            if n.a == "mo" else {}
        in_json(goi(m[n.a], khoa, body)); return 0
    if n.viec == "lenh":
        if not n.a:
            print("dùng: lenh <tên> <giá trị>   ví dụ: lenh afterburner 1"); return 2
        try:
            gt = float(n.b) if "." in str(n.b) else int(n.b or 1)
        except ValueError:
            gt = n.b
        r = goi("write", khoa, {"name": n.a, "value": gt})
        in_json(r)
        return 0 if r.get("ok") else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
