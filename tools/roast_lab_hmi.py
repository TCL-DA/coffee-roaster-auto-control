"""
OTL Roast Lab HMI — vỏ desktop (pywebview) cho giao diện HMI cảm ứng.

Bọc file 'OTL Roast Lab.html' (vanilla HTML/CSS/JS, không framework) thành một
cửa sổ app native trên Windows (dùng WebView2 hệ thống). Phần lõi giao diện nằm
trọn trong file HTML — script này chỉ mở cửa sổ và nạp nó.

Chạy thử:  python tools/roast_lab_hmi.py
Build exe: python -m PyInstaller tools/RoastLabHMI.spec
Phụ thuộc: pip install pywebview   (Windows cần WebView2 runtime — Win10/11 có sẵn)
"""

import os
import sys

import webview

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import otl_link                                  # noqa: E402  (cầu Modbus tới máy rang)

APP_TITLE = "OTL Roast Lab — HMI"
APP_BG = "#0b0e13"          # nền khớp theme tối của HTML, tránh chớp trắng lúc mở
HTML_NAME = "OTL Roast Lab.html"


def html_path():
    """Đường dẫn file HTML: khi đóng exe lấy từ bundle (_MEIPASS), khi dev lấy ở gốc repo."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return os.path.join(base, HTML_NAME)
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(here, "..", HTML_NAME))


class Api:
    """Cầu nối JS → Python: cửa sổ + dữ liệu live từ máy rang (otl_link).

    ⚠ MỌI thuộc tính phải bắt đầu bằng '_'. pywebview DUYỆT ĐỆ QUY thuộc tính
    công khai của đối tượng này để phơi sang JS; gặp đối tượng cửa sổ .NET nó bò
    vào window.native.AccessibilityObject.Bounds.Empty.Empty… tới khi tràn stack:
        [pywebview] maximum recursion depth exceeded
    JS gọi link_snapshot() mỗi giây → mỗi giây một trận đệ quy → app TREO
    (not responding). Tên bắt đầu bằng '_' được pywebview bỏ qua.
    """

    def __init__(self):
        self._window = None
        self._link = otl_link.RoasterLink()

    # ── chỉ những method dưới đây mới phơi sang JS ──────────────────────────
    def toggle_fullscreen(self):
        if self._window:
            self._window.toggle_fullscreen()

    def link_snapshot(self):
        """Gói dữ liệu mới nhất + trạng thái kết nối. JS gọi mỗi giây."""
        return self._link.snapshot()

    def link_config(self):
        return self._link.cfg

    def link_set_config(self, cfg):
        self._link.reconfigure(cfg or {})
        return self._link.cfg

    def link_ports(self):
        return otl_link.list_serial_ports()

    def link_write(self, name, value):
        """Ghi setpoint / nút ảo. Máy chỉ nhận khi PC control đang BẬT."""
        return self._link.write(name, value)

    def link_new_batch(self):
        """Về mẻ trống — xoá đồng hồ/mốc bên Python."""
        return self._link.new_batch()

    def link_begin_batch(self):
        """Thợ bấm Bắt đầu rang — mở đồng hồ mẻ + chấm mốc từ giây này."""
        return self._link.begin_batch()


def main():
    api = Api()
    # Tự mở FULLSCREEN đúng độ phân giải màn hình hiện tại — hoàn toàn tự động.
    # Phần HTML tự co khung 2560×1440 vừa khít mọi phân giải (fit()).
    window = webview.create_window(
        APP_TITLE,
        url=html_path(),
        fullscreen=True,
        width=1680,          # dự phòng nếu môi trường bỏ qua fullscreen
        height=1000,
        background_color=APP_BG,
        js_api=api,
    )
    api._window = window
    api._link.start()         # luồng nền tự dò cổng, tự kết nối lại — không chặn UI
    # QUAN TRỌNG: pywebview mặc định private_mode=True (ẩn danh) → localStorage bị
    # xoá mỗi lần đóng. App lưu PIN/tài khoản/config/nhật ký trong localStorage nên
    # phải TẮT ẩn danh + trỏ thư mục dữ liệu bền trong %LOCALAPPDATA%.
    storage = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                           "OTL Roast Lab HMI")
    webview.start(private_mode=False, storage_path=storage)


if __name__ == "__main__":
    main()
