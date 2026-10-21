"""Quản lý token cục bộ dùng chung giữa Serial Terminal và MCP."""

import os
import secrets
import subprocess
import threading
from pathlib import Path

ICACLS_TIMEOUT_S = 15


def _icacls(*args):
    """Chạy icacls không bật cửa sổ console; trả True nếu lệnh thành công."""
    result = subprocess.run(
        ["icacls", *args], capture_output=True, timeout=ICACLS_TIMEOUT_S, check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return result.returncode == 0


def _lock_down_windows_now(path):
    """Khoá file token chỉ cho tài khoản Windows hiện tại đọc được (best-effort).

    os.open(..., 0o600) chỉ có tác dụng thật trên POSIX — trên Windows, mode
    bit kiểu này KHÔNG map sang ACL của NTFS, tức bình luận "chỉ chủ sở hữu
    đọc được" trước đây không đúng thực tế trên nền tảng app này chạy. Không
    có lib chuẩn nào trong stdlib chỉnh ACL Windows nên gọi icacls.

    Cấp quyền cho người dùng TRƯỚC, chỉ khi thành công mới cắt quyền kế thừa.
    Gộp chung một lệnh `/inheritance:r /grant:r` mà tên tài khoản không map
    được SID thì có nguy cơ khoá luôn chính chủ, lần mở sau đọc token lỗi.

    Mọi lỗi (không có icacls, hết giờ, lệnh hỏng) đều nuốt. Máy Win 11 thật
    từng chạy icacls quá 5 giây: TimeoutExpired KHÔNG phải OSError nên lọt ra
    ngoài và làm sập app ngay lúc mở (15/09/2026).
    """
    if os.name != "nt":
        return
    user = os.environ.get("USERNAME")
    if not user:
        return
    try:
        if _icacls(str(path), "/grant:r", f"{user}:(R,W)"):
            _icacls(str(path), "/inheritance:r")
    except (OSError, subprocess.SubprocessError):
        pass


def _lock_down_windows(path):
    """Khoá quyền ở luồng nền — icacls chậm không được chặn app khởi động."""
    threading.Thread(target=_lock_down_windows_now, args=(path,),
                     name="token-acl", daemon=True).start()


def token_file_path():
    configured = os.environ.get("OTL_SERIAL_API_TOKEN_FILE")
    if configured:
        return Path(configured).expanduser()
    if os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
        return root / "OTL" / "SerialTerminal" / "api-token"
    root = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state")
    return root / "otl" / "serial-terminal" / "api-token"


_cached_token = None


def _create_token_file(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    token = secrets.token_urlsafe(32)
    try:
        descriptor = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return path.read_text(encoding="ascii").strip()
    with os.fdopen(descriptor, "w", encoding="ascii", newline="\n") as stream:
        stream.write(token + "\n")
    _lock_down_windows(path)
    return token


def load_or_create_token():
    """Đọc token từ môi trường/tệp hoặc tạo token riêng cho người dùng hiện tại.

    Được cache trong tiến trình: MCP gọi hàm này ở MỖI lần gọi công cụ (mỗi
    request tới app), nên đọc lại đĩa mỗi lần là phí một syscall vô ích cho mọi
    lệnh tự động hoá. Token không đổi trong vòng đời một tiến trình MCP/app nên
    cache là an toàn; nếu tệp token bị xoá/đổi khi tiến trình đang chạy thì
    phải khởi động lại tiến trình đó để đọc token mới — đúng như mô tả "đọc
    khoá cục bộ" hiện có, không đổi ngữ nghĩa.

    Tệp token hỏng hoặc không đọc/ghi được (bị khoá quyền, ổ chỉ đọc...) thì
    KHÔNG được làm sập app: dùng token tạm trong tiến trình. App và API vẫn
    chạy, chỉ MCP ở tiến trình khác bị 401 cho tới khi sửa được tệp.
    """
    global _cached_token
    if _cached_token is not None:
        return _cached_token
    configured = os.environ.get("OTL_SERIAL_API_TOKEN")
    if configured:
        token = configured.strip()
        if len(token) < 24:
            raise RuntimeError("OTL_SERIAL_API_TOKEN phải có ít nhất 24 ký tự")
        _cached_token = token
        return token
    path = token_file_path()
    try:
        try:
            token = path.read_text(encoding="ascii").strip()
        except FileNotFoundError:
            token = _create_token_file(path)
    except (OSError, UnicodeError):
        token = ""
    if len(token) < 24:
        token = secrets.token_urlsafe(32)
    _cached_token = token
    return token
