"""
License OTL Roast Lab — Ed25519 + khoá theo máy (GĐ2 §16.4).

Mô hình:
  - Người bán (OTL) giữ khoá BÍ MẬT (tools/license_admin.py, KHÔNG ship theo app).
  - App nhúng khoá CÔNG KHAI (PUBLIC_KEY_HEX dưới đây) — chỉ VERIFY, không ký được.
  - File license `otl.lic` (JSON + chữ ký) đặt trong %LOCALAPPDATA%\\OTL Roast Lab HMI.
  - License trói vào `machine_id` — copy exe + license sang máy lạ → sai máy →
    app chạy CHẾ ĐỘ XEM (xem dữ liệu, không điều khiển máy).

Bật/tắt cưỡng chế: settings.ini [BanQuyen] bat=1. MẶC ĐỊNH TẮT — GĐ1 (xưởng
mình tự dùng) không được để chuyện bán hàng chặn máy chạy. Khi bắt đầu bán mới
bật lên trong bản build cho khách.

machine_id = SHA256(MachineGuid)[:16] — MachineGuid nằm trong registry
HKLM\\SOFTWARE\\Microsoft\\Cryptography, ổn định qua reboot/đổi tên máy,
không lộ GUID gốc của khách trong file license.
"""

import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ed25519_tiny                                            # noqa: E402

# Khoá công khai của OTL (hex 64 ký tự). RỖNG = chưa phát hành khoá → verify
# luôn False (chỉ có ý nghĩa khi bật cưỡng chế). Sinh khoá: license_admin.py init
PUBLIC_KEY_HEX = "22adb18a126b1dfea89ac2894db13bc30d4405c3da145d6b9ba6c4d2d018dfc1"

LIC_NAME = "otl.lic"


def machine_id() -> str:
    """Mã máy 16 hex — SHA256(MachineGuid) cắt ngắn. Lỗi registry → 'unknown'."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SOFTWARE\Microsoft\Cryptography",
                            0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as k:
            guid, _ = winreg.QueryValueEx(k, "MachineGuid")
        return hashlib.sha256(guid.encode()).hexdigest()[:16]
    except Exception:
        return "unknown"


def _canon(lic: dict) -> bytes:
    """Dạng chuẩn hoá để ký/kiểm — MỌI bên phải dùng đúng một dạng này."""
    return json.dumps(lic, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def lic_path(base_dir: str) -> str:
    return os.path.join(base_dir, LIC_NAME)


def verify_file(path: str, pub_hex: str = None) -> dict:
    """Kiểm license: trả {'ok':bool,'ly_do':str,...thông tin license}.

    KHÔNG nổ exception — license hỏng/thiếu chỉ là một trạng thái bình thường.
    """
    pub_hex = PUBLIC_KEY_HEX if pub_hex is None else pub_hex
    if not pub_hex:
        return {"ok": False, "ly_do": "app chưa nhúng khoá công khai"}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        lic, sig = data["lic"], bytes.fromhex(data["kyso"])
    except FileNotFoundError:
        return {"ok": False, "ly_do": "chưa có file license"}
    except Exception as e:
        return {"ok": False, "ly_do": "file license hỏng: " + str(e)}

    if not ed25519_tiny.verify(sig, _canon(lic), bytes.fromhex(pub_hex)):
        return {"ok": False, "ly_do": "chữ ký không hợp lệ"}
    if lic.get("may") != machine_id():
        return {"ok": False, "ly_do": "license của máy khác",
                "may_lic": lic.get("may"), "may_nay": machine_id()}
    hh = lic.get("het_han")
    if hh:
        import datetime
        try:
            if datetime.date.today().isoformat() > hh:
                return {"ok": False, "ly_do": "license hết hạn " + hh, **lic}
        except Exception:
            return {"ok": False, "ly_do": "ngày hết hạn không hợp lệ"}
    return {"ok": True, "ly_do": "", **lic}


def make_license(lic: dict, secret: bytes) -> dict:
    """Ký license (chạy ở máy NGƯỜI BÁN — license_admin.py gọi)."""
    pub = ed25519_tiny.publickey(secret)
    sig = ed25519_tiny.sign(_canon(lic), secret, pub)
    return {"lic": lic, "kyso": sig.hex()}
