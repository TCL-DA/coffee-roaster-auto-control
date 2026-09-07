# -*- coding: utf-8 -*-
"""Quản lý khoá API bằng DÒNG LỆNH (chưa có màn hình trong app).

    python tools/otl_apikey_cli.py list
    python tools/otl_apikey_cli.py add "MCP đọc" read
    python tools/otl_apikey_cli.py add "trợ lý chỉnh máy" read config
    python tools/otl_apikey_cli.py off <id>      # tạm khoá
    python tools/otl_apikey_cli.py on  <id>
    python tools/otl_apikey_cli.py del <id>

Chạy TRÊN MÁY đang cài app — ai chạy được lệnh này thì đã ngồi trước máy rồi, nên
không đặt thêm cổng xác thực ở đây. Khoá gốc in ra ĐÚNG MỘT LẦN.

Cấp phạm vi 'control' là cấp quyền mở van gas và bắn xi-lanh. Đừng cấp cho thứ chỉ
cần đọc — công cụ này hỏi lại một lần trước khi cấp.
"""
import io
import os
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from otl_apikey import SCOPES, ApiKeyStore              # noqa: E402


def _kho():
    # cùng thư mục dữ liệu portable mà app dùng
    for d in (os.path.join(HERE, "appdata"), HERE):
        if os.path.isdir(d):
            return ApiKeyStore(d)
    return ApiKeyStore(HERE)


def _gio(ts):
    return time.strftime("%d/%m/%Y %H:%M", time.localtime(ts)) if ts else "chưa dùng"


def cmd_list(_):
    ks = _kho().list()
    if not ks:
        print("Chưa có khoá nào.")
        return 0
    print("%-14s %-24s %-22s %-17s %s" % ("ID", "TÊN", "PHẠM VI", "DÙNG LẦN CUỐI", "TRẠNG THÁI"))
    for k in ks:
        print("%-14s %-24s %-22s %-17s %s" % (
            k["id"], k["name"][:23], ",".join(k["scopes"]),
            _gio(k["last_used"]), "bật" if k["enabled"] else "ĐANG KHOÁ"))
    return 0


def cmd_add(a):
    if len(a) < 2:
        print("Thiếu tham số. Ví dụ: add \"MCP đọc\" read")
        return 2
    ten, sc = a[0], a[1:]
    la = [s for s in sc if s not in SCOPES]
    if la:
        print("Phạm vi không có: %s. Chỉ có: %s" % (", ".join(la), ", ".join(SCOPES)))
        return 2
    if "control" in sc:
        print("\n  ⚠  Phạm vi 'control' LÁI ĐƯỢC MÁY: mở gas, nạp hạt, xả mẻ.")
        print("     Chỉ cấp khi thực sự cần. Thứ chỉ đọc thì dùng 'read'.")
        if input("     Vẫn cấp? (go 'CO' de dong y): ").strip() != "CO":
            print("     Đã huỷ.")
            return 1
    r = _kho().add(ten, sc)
    if not r.get("ok"):
        print("Lỗi: %s" % r.get("err"))
        return 1
    print("\n  Đã tạo khoá  id=%s  phạm vi=%s" % (r["id"], ",".join(r["scopes"])))
    print("  " + "-" * 74)
    print("  %s" % r["key"])
    print("  " + "-" * 74)
    print("  ⚠  %s\n" % r["canh_bao"])
    print("  Dùng cho MCP server:")
    print("     set OTL_API_KEY=%s" % r["key"])
    print("     set OTL_API_BASE=http://127.0.0.1:8555\n")
    return 0


def cmd_del(a):
    if not a:
        print("Thiếu id.")
        return 2
    r = _kho().delete(a[0])
    print("Đã xoá." if r.get("ok") else "Lỗi: %s" % r.get("err"))
    return 0 if r.get("ok") else 1


def _bat_tat(a, on):
    if not a:
        print("Thiếu id.")
        return 2
    r = _kho().set_enabled(a[0], on)
    print(("Đã bật." if on else "Đã khoá.") if r.get("ok") else "Lỗi: %s" % r.get("err"))
    return 0 if r.get("ok") else 1


def main(argv):
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    lenh, con = argv[0], argv[1:]
    bang = {"list": cmd_list, "add": cmd_add, "del": cmd_del,
            "off": lambda a: _bat_tat(a, False), "on": lambda a: _bat_tat(a, True)}
    f = bang.get(lenh)
    if not f:
        print("Không có lệnh '%s'. Xem: --help" % lenh)
        return 2
    return f(con)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
