"""
Tool KÝ LICENSE — chạy ở máy NGƯỜI BÁN (OTL). KHÔNG ship theo app khách.

Quy trình:
  1. Sinh cặp khoá 1 lần:
        python tools/license_admin.py init
     → in PUBLIC_KEY_HEX (dán vào tools/license_otl.py) + lưu khoá bí mật
       tools/_otl_secret.key (GIỮ KÍN, đừng commit — đã có trong .gitignore ý tưởng).

  2. Khách gửi machine_id (app hiện ở Cài đặt → Bản quyền, hoặc chạy
        python tools/license_admin.py machine-id  trên máy khách).

  3. Ký license cho khách:
        python tools/license_admin.py sign --may <machine_id> --ten "Xưởng ABC" [--het-han 2027-12-31]
     → xuất otl.lic, gửi khách đặt vào %LOCALAPPDATA%\\OTL Roast Lab HMI\\
"""

import argparse
import json
import os
import sys

# Console Windows mặc định cp1252 -> print tiếng Việt sẽ nổ UnicodeEncodeError.
# Ép UTF-8 cho stdout/stderr để lệnh init/sign in tên xưởng có dấu an toàn.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ed25519_tiny                                            # noqa: E402
import license_otl                                            # noqa: E402

SECRET_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_otl_secret.key")


def cmd_init(_args):
    if os.path.exists(SECRET_PATH):
        print("Đã có _otl_secret.key — xoá tay nếu muốn tạo khoá mới (sẽ vô hiệu mọi license cũ!)")
        return 1
    import secrets
    sk = secrets.token_bytes(32)
    with open(SECRET_PATH, "wb") as f:
        f.write(sk)
    pub = ed25519_tiny.publickey(sk).hex()
    print("Đã tạo khoá bí mật:", SECRET_PATH, "(GIỮ KÍN)")
    print("\nDán dòng này vào tools/license_otl.py:")
    print(f'  PUBLIC_KEY_HEX = "{pub}"')
    return 0


def cmd_machine_id(_args):
    print(license_otl.machine_id())
    return 0


def cmd_sign(args):
    if not os.path.exists(SECRET_PATH):
        print("Chưa có khoá — chạy: python tools/license_admin.py init")
        return 1
    with open(SECRET_PATH, "rb") as f:
        sk = f.read()
    lic = {"may": args.may, "ten": args.ten, "goi": args.goi}
    if args.het_han:
        lic["het_han"] = args.het_han
    signed = license_otl.make_license(lic, sk)
    out = args.out or "otl.lic"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(signed, f, ensure_ascii=False, indent=1)
    # tự kiểm lại bằng khoá công khai suy từ bí mật — chắc chắn khách verify được
    pub = ed25519_tiny.publickey(sk).hex()
    chk = license_otl.verify_file(out, pub)
    print("Đã ký:", out)
    print("Máy:", args.may, "| Tên:", args.ten,
          "| Hết hạn:", args.het_han or "vĩnh viễn")
    print("Tự kiểm chữ ký:", "OK" if chk.get("ok") or chk.get("ly_do", "").startswith("license của máy khác")
          else "LỖI " + chk.get("ly_do", ""))
    return 0


def main():
    ap = argparse.ArgumentParser(description="Ký license OTL Roast Lab (máy người bán)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    sub.add_parser("machine-id")
    s = sub.add_parser("sign")
    s.add_argument("--may", required=True, help="machine_id của khách")
    s.add_argument("--ten", required=True, help="tên xưởng/khách in trong license")
    s.add_argument("--goi", default="full", help="gói: full/lite (app tự diễn giải)")
    s.add_argument("--het-han", default="", help="YYYY-MM-DD, để trống = vĩnh viễn")
    s.add_argument("--out", default="", help="đường dẫn file .lic xuất ra")
    args = ap.parse_args()
    return {"init": cmd_init, "machine-id": cmd_machine_id, "sign": cmd_sign}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
