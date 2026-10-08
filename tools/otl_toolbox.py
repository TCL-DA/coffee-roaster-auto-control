"""
OTL Toolbox — một app gom 5 công cụ kỹ thuật.

    Làm việc : MỘT màn đủ thao tác BT / Cân / Terminal / số liệu rang + log chung (toolbox_workspace.py)
    Cài đặt  : giao diện gốc từng công cụ — chọn cổng COM, baud, Kalman, Modbus relay…
    Chuyển profile : khung trượt từ phải

Cách chạy:
    python tools/otl_toolbox.py                → mở app ở màn Làm việc
    python tools/otl_toolbox.py --open scale   → mở app ở Cài đặt · Cân (bt/scale/terminal/monitor)
    python tools/otl_toolbox.py --open convert → mở app, bật sẵn khung Chuyển profile
    python tools/otl_toolbox.py --tool bt      → chạy riêng một công cụ (cửa sổ riêng như cũ)
    python tools/otl_toolbox.py --chart x.json → đồ thị của bộ chuyển profile

Khởi động là dựng cả 5 công cụ làm "bộ máy" (App gốc). Màn Làm việc chỉ gọi hàm của
bộ máy, không giữ logic riêng. Mã công cụ viết cho cửa sổ riêng (lớp con ctk.CTk): lúc
nạp module, Toolbox tạm thay ctk.CTk bằng một khung biết "giả" các lệnh cửa sổ
(title, geometry, protocol…) nên App nằm gọn trong trang mà không phải sửa mã công cụ.
"""
import importlib
import os
import runpy
import shutil
import subprocess
import sys
import tkinter as tk
import traceback
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import customtkinter as ctk
from PIL import Image

FROZEN = getattr(sys, "frozen", False)
TOOLS_DIR = Path(__file__).resolve().parent
# Phần xử lý của bộ chuyển profile nằm ở project 101, không chép mã sang đây
PROFILE_CONVERT_SRC = Path(r"F:\Project\101_profile_convert\src")

# Bản đóng gói onedir nằm ở tools/dist/OTLToolbox/
EXE_DIR = Path(sys.executable).parent if FROZEN else TOOLS_DIR / "dist"
DIST_DIR = EXE_DIR.parent if FROZEN else TOOLS_DIR / "dist"
ROAST_LAB_HMI_EXE = DIST_DIR / "OTL Roast Lab HMI.exe"

# File cài đặt các công cụ cũ lưu cạnh exe — chép sang chỗ mới lần đầu chạy
LEGACY_SETTINGS = ("bt_tester_settings.json",)


@dataclass(frozen=True)
class Tool:
    key: str
    title: str
    module: str
    icon: str


# Bộ máy (App gốc) — dựng lúc khởi động. Bốn cái đầu có trang ở tab Cài đặt,
# "convert" nằm trong khung trượt Chuyển profile.
SETTINGS_TOOLS = (
    Tool("bt", "BT Tester", "bt_serial_tester_glass", "bt_icon.ico"),
    Tool("scale", "Cân giả lập", "scale_simulator", "scale_icon.ico"),
    Tool("terminal", "Serial Terminal · Modbus relay", "otl_serial_terminal", "otl_icon.ico"),
    Tool("monitor", "Roaster Monitor", "roaster_monitor", "otl_icon.ico"),
)
ENGINE_TOOLS = SETTINGS_TOOLS + (
    Tool("convert", "Chuyển profile", "profile_convert", "assets/icon.ico"),
)
TOOL_BY_KEY = {t.key: t for t in ENGINE_TOOLS}

PAGE_WORK = "Làm việc"
PAGE_SETTINGS = "Cài đặt"

FONT = "Segoe UI"
INK = "#1E293B"          # chữ chính — tương phản > 12:1 trên nền trắng
MUTED = "#64748B"        # chữ phụ — tương phản > 4.5:1
LINE = "#E2E8F0"
FIELD = "#F1F5F9"
SURFACE = "#FFFFFF"
BG = "#EEF2F7"
BRAND = "#C62828"        # đỏ OTL
BRAND_HOVER = "#A31F1F"
SELECTED_BG = "#FDECEC"
DRAWER_FRAC = {"convert": 0.72}   # bề rộng khung trượt theo bề rộng cửa sổ; còn lại 0.9
DRAWER_STEPS = 10
DRAWER_FRAME_MS = 20     # 10 nhịp × 20 ms ≈ 200 ms


def resource_path(rel: str) -> Path:
    path = Path(getattr(sys, "_MEIPASS", TOOLS_DIR)) / rel
    if not path.exists() and not FROZEN:
        path = PROFILE_CONVERT_SRC.parent / rel   # icon của bộ chuyển profile (project 101)
    return path


def prepare_paths() -> None:
    """Chạy từ mã nguồn: cho Python thấy module công cụ ở tools/ và project 101."""
    if FROZEN:
        return
    for path in (TOOLS_DIR, PROFILE_CONVERT_SRC):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))


def migrate_legacy_settings() -> None:
    """Giữ cài đặt cũ: chép file cài đặt từ tools/dist sang cạnh exe mới (nếu chưa có)."""
    if not FROZEN:
        return
    for name in LEGACY_SETTINGS:
        old, new = DIST_DIR / name, EXE_DIR / name
        if old.exists() and not new.exists():
            try:
                shutil.copy2(old, new)
            except OSError:
                pass  # không chép được thì công cụ dùng cài đặt mặc định, vẫn chạy


def run_module_as_main(module: str, argv: list) -> None:
    sys.argv = argv
    runpy.run_module(module, run_name="__main__", alter_sys=True)


# ════════════════════════════════════════════════════════════════════════════
#  NHÚNG App (viết cho cửa sổ riêng) vào một tab
# ════════════════════════════════════════════════════════════════════════════
_host_parent = None   # khung tab đang chờ nhận App — đặt ngay trước khi tạo App

_NON_KEY_EVENTS = {"Button", "ButtonPress", "ButtonRelease", "Motion", "Enter", "Leave",
                   "Configure", "MouseWheel", "Map", "Unmap", "Destroy", "FocusIn", "FocusOut",
                   "Visibility", "Expose", "Activate", "Deactivate"}
_TEXT_INPUTS = {"Entry", "Text", "TEntry", "Spinbox", "TSpinbox", "TCombobox"}


def _is_key_sequence(sequence) -> bool:
    if not sequence or not sequence.startswith("<") or sequence.startswith("<<"):
        return False
    parts = sequence.strip("<>").split("-")
    return not any(p in _NON_KEY_EVENTS or (p[:1] == "B" and p[1:].isdigit()) for p in parts)


class EmbeddedCTk(ctk.CTkFrame):
    """Khung đóng vai cửa sổ ctk.CTk: các lệnh cửa sổ thành không làm gì / chuyển lên Toolbox."""
    _tab_title = ""
    close_handler = None

    def __init__(self, *args, **kwargs):
        bg = kwargs.pop("fg_color", ctk.ThemeManager.theme["CTk"]["fg_color"])
        super().__init__(_host_parent, corner_radius=0, fg_color=bg)

    def title(self, text=None):
        if text is None:
            return self._tab_title
        self._tab_title = text
        return None
    wm_title = title

    def geometry(self, spec=None):
        return self.winfo_toplevel().geometry() if spec is None else None
    wm_geometry = geometry

    def protocol(self, name=None, func=None):
        if name == "WM_DELETE_WINDOW" and func is not None:
            self.close_handler = func
    wm_protocol = protocol

    def bind(self, sequence=None, command=None, add=True):
        """Phím tắt App gắn cho "cửa sổ" → gắn lên cửa sổ Toolbox, chỉ ăn khi tab đang hiện
        và không đang gõ trong ô nhập (gõ số trong Terminal không được bắn lệnh BT)."""
        if command is None or not _is_key_sequence(sequence):
            return super().bind(sequence, command, add)

        def guarded(event, _func=command):
            if not self.winfo_ismapped():
                return None
            try:
                if event.widget.winfo_class() in _TEXT_INPUTS:
                    return None
            except (AttributeError, tk.TclError):
                pass
            return _func(event)
        return self.winfo_toplevel().bind(sequence, guarded, add="+")

    def _ignore_wm(self, *args, **kwargs):
        return None
    minsize = maxsize = resizable = iconbitmap = wm_iconbitmap = iconphoto = _ignore_wm
    attributes = wm_attributes = state = overrideredirect = _ignore_wm
    deiconify = withdraw = iconify = mainloop = quit = _ignore_wm


@contextmanager
def _ctk_window_replaced():
    original = ctk.CTk
    ctk.CTk = EmbeddedCTk
    try:
        yield
    finally:
        ctk.CTk = original


def build_tool(tool: Tool, parent) -> tk.Misc:
    """Nạp module công cụ (lớp App kế thừa khung nhúng) rồi dựng App trong `parent`."""
    global _host_parent
    with _ctk_window_replaced():
        module = importlib.import_module(tool.module)
    _host_parent = parent
    try:
        return module.App()
    finally:
        _host_parent = None


# ════════════════════════════════════════════════════════════════════════════
#  CỬA SỔ TOOLBOX
# ════════════════════════════════════════════════════════════════════════════
class Toolbox(ctk.CTk):
    def __init__(self, start: str = "work"):
        super().__init__()
        ctk.set_appearance_mode("Light")
        ctk.set_default_color_theme("blue")
        self.title("OTL Toolbox")
        self.geometry("1440x900")
        self.minsize(1100, 640)   # ctk nhân theo DPI: 125% → 1375×800, vừa màn laptop 1536×864
        self.configure(fg_color=BG)
        try:
            self.iconbitmap(str(resource_path("otl_icon.ico")))
        except tk.TclError:
            pass
        self.engines, self.errors = {}, {}
        self.workspace = self.settings = None
        self.page = "work"
        self._drawer_key = None
        self._start = start
        self._build_shell()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Escape>", lambda _e: self._close_drawer())
        self.after(0, lambda: self.state("zoomed"))
        self.after(80, self._boot)

    # ----- khung -----
    def _icon(self, name: str, size: int):
        try:
            return ctk.CTkImage(light_image=Image.open(resource_path(name)), size=(size, size))
        except OSError:
            return None

    def _outline(self, parent, text, cmd, width=140):
        return ctk.CTkButton(parent, text=text, height=40, width=width, corner_radius=8,
                             fg_color="transparent", border_width=1, border_color="#CBD5E1",
                             text_color=INK, hover_color=LINE, font=ctk.CTkFont(FONT, 13),
                             command=cmd)

    def _build_shell(self):
        bar = ctk.CTkFrame(self, height=64, corner_radius=0, fg_color=SURFACE)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        tk.Frame(self, height=1, bg=LINE).pack(fill="x")
        self.body = ctk.CTkFrame(self, corner_radius=0, fg_color=BG)
        self.body.pack(fill="both", expand=True)

        logo = self._icon("otl_symbol.png", 30)
        if logo:
            ctk.CTkLabel(bar, image=logo, text="").pack(side="left", padx=(18, 8))
        ctk.CTkLabel(bar, text="OTL Toolbox", text_color=INK,
                     font=ctk.CTkFont(FONT, 18, "bold")).pack(side="left", padx=(0, 24))
        self.page_switch = ctk.CTkSegmentedButton(
            bar, values=[PAGE_WORK, PAGE_SETTINGS], height=40, font=ctk.CTkFont(FONT, 14, "bold"),
            selected_color=BRAND, selected_hover_color=BRAND_HOVER, command=self._on_page_switch)
        self.page_switch.set(PAGE_WORK)
        self.page_switch.pack(side="left")
        self._outline(bar, "Thư mục dist", self._open_dist, 120).pack(side="right", padx=(0, 16))
        self._outline(bar, "Roast Lab HMI  ↗", self._open_roast_lab).pack(side="right", padx=(0, 8))
        ctk.CTkButton(bar, text="Chuyển profile  ›", height=40, width=150, corner_radius=8,
                      fg_color=INK, hover_color="#334155", font=ctk.CTkFont(FONT, 13, "bold"),
                      command=lambda: self.open_drawer("convert")).pack(side="right", padx=(0, 8))

        self.work_page = ctk.CTkFrame(self.body, fg_color="transparent")
        self.settings_page = ctk.CTkFrame(self.body, fg_color="transparent")
        self._build_drawer()
        self.splash = ctk.CTkLabel(self.body, text="Đang khởi động công cụ…", text_color=MUTED,
                                   font=ctk.CTkFont(FONT, 16))
        self.splash.pack(expand=True)

    def _build_drawer(self):
        """Khung trượt từ phải — chứa giao diện đầy đủ của MỘT bộ máy mỗi lần mở."""
        self.drawer = ctk.CTkFrame(self.body, fg_color=SURFACE, corner_radius=0,
                                   border_width=1, border_color=LINE)
        head = ctk.CTkFrame(self.drawer, fg_color="transparent")
        head.pack(fill="x", padx=16, pady=(10, 0))
        self.drawer_title = ctk.CTkLabel(head, text="", text_color=INK,
                                         font=ctk.CTkFont(FONT, 15, "bold"))
        self.drawer_title.pack(side="left")
        ctk.CTkButton(head, text="Đóng  ✕", width=96, height=40, corner_radius=8, fg_color=FIELD,
                      hover_color=LINE, text_color=INK, font=ctk.CTkFont(FONT, 13),
                      command=self._close_drawer).pack(side="right")
        ctk.CTkLabel(head, text="Esc để đóng", text_color=MUTED,
                     font=ctk.CTkFont(FONT, 12)).pack(side="right", padx=10)
        self.drawer_host = ctk.CTkFrame(self.drawer, fg_color="transparent")
        self.drawer_host.pack(fill="both", expand=True)
        self._drawer_open = False

    # ----- khởi động: dựng bộ máy từng cái, rồi màn Làm việc -----
    def _boot(self, idx: int = 0):
        if idx < len(ENGINE_TOOLS):
            tool = ENGINE_TOOLS[idx]
            self.splash.configure(text=f"Đang khởi động {tool.title}…  ({idx + 1}/{len(ENGINE_TOOLS)})")
            self.update_idletasks()
            try:
                frame = build_tool(tool, self.drawer_host)
                frame.pack_forget()
                self.engines[tool.key] = frame
                if tool.key == "bt":
                    start_bt_control_server(frame)
            except Exception:  # công cụ lỗi không được kéo sập cả Toolbox
                self.errors[tool.key] = traceback.format_exc()
            self.after(10, lambda: self._boot(idx + 1))
            return
        self.splash.destroy()
        self._build_pages()
        self.show_settings() if self._start == "settings" else self.show_work()
        if self._start in TOOL_BY_KEY:
            self.open_drawer(self._start)

    def _build_pages(self):
        needed = ("bt", "scale", "terminal", "monitor")
        missing = [k for k in needed if k not in self.engines]
        if missing:
            detail = "\n\n".join(f"--- {k}:\n{self.errors.get(k, '')}" for k in missing)
            for page in (self.work_page, self.settings_page):
                self._error_panel(page, "Thiếu công cụ: " + ", ".join(missing),
                                  detail).pack(fill="both", expand=True, padx=32, pady=28)
            return
        from toolbox_settings import SettingsPage
        from toolbox_workspace import Workspace
        self.workspace = Workspace(self.work_page, self.engines, lambda _key=None: self.show_settings())
        self.workspace.pack(fill="both", expand=True)
        self.settings = SettingsPage(self.settings_page, self.engines, self.open_drawer)
        self.settings.pack(fill="both", expand=True)

    # ----- chuyển trang -----
    def _on_page_switch(self, value):
        self.show_work() if value == PAGE_WORK else self.show_settings()

    def show_work(self):
        self.page = "work"
        self.page_switch.set(PAGE_WORK)
        self.settings_page.pack_forget()
        self.work_page.pack(fill="both", expand=True)
        self.title("OTL Toolbox — Làm việc")
        self._raise_drawer()

    def show_settings(self):
        self.page = "settings"
        self.page_switch.set(PAGE_SETTINGS)
        self.work_page.pack_forget()
        self.settings_page.pack(fill="both", expand=True)
        self.title("OTL Toolbox — Cài đặt")
        self._raise_drawer()

    # ----- khung trượt: giao diện đầy đủ của một bộ máy -----
    def _drawer_frac(self) -> float:
        """Bề rộng khung trượt so với cửa sổ (ctk không cho đặt width ở place → dùng relwidth)."""
        return DRAWER_FRAC.get(self._drawer_key, 0.9)

    def open_drawer(self, key: str):
        tool = TOOL_BY_KEY.get(key)
        if tool is None:
            return
        for child in self.drawer_host.winfo_children():
            child.pack_forget()
        if key in self.engines:
            self.engines[key].pack(fill="both", expand=True)
        else:
            self._error_panel(self.drawer_host, f"Không mở được {tool.title}",
                              self.errors.get(key, "")).pack(fill="both", expand=True, padx=32, pady=28)
        self.drawer_title.configure(text=tool.title if key == "convert" else f"{tool.title} — giao diện đầy đủ")
        was_open, self._drawer_key = self._drawer_open, key
        self._drawer_open = True
        if was_open:
            self.drawer.place_configure(relwidth=self._drawer_frac())
        else:
            self._slide(0)

    def _close_drawer(self):
        if self._drawer_open:
            self._drawer_open = False
            self._slide(0, closing=True)

    def _slide(self, step: int, closing: bool = False):
        """Trượt khung ra/vào trong DRAWER_STEPS nhịp (~200 ms), chậm dần ở cuối."""
        rel = self._drawer_frac()
        w = self.body.winfo_width() * rel
        k = (step + 1) / DRAWER_STEPS
        shown = 1 - (1 - k) ** 3
        frac = 1 - shown if closing else shown
        self.drawer.place(relx=1.0, rely=0, x=int(w * (1 - frac)), anchor="ne", relwidth=rel, relheight=1)
        self.drawer.lift()
        if step + 1 < DRAWER_STEPS:
            self.after(DRAWER_FRAME_MS, lambda: self._slide(step + 1, closing))
        elif closing:
            self.drawer.place_forget()

    def _raise_drawer(self):
        if self._drawer_open:
            self.drawer.lift()

    # ----- phụ -----
    def _error_panel(self, parent, title: str, detail: str):
        panel = ctk.CTkFrame(parent, fg_color="transparent")
        ctk.CTkLabel(panel, text=title, text_color=BRAND,
                     font=ctk.CTkFont(FONT, 20, "bold")).pack(anchor="w")
        ctk.CTkLabel(panel, text="Các phần khác vẫn dùng bình thường. Chi tiết lỗi:",
                     text_color=MUTED, font=ctk.CTkFont(FONT, 13)).pack(anchor="w", pady=(6, 8))
        box = ctk.CTkTextbox(panel, height=360, font=ctk.CTkFont("Consolas", 12))
        box.insert("1.0", detail)
        box.configure(state="disabled")
        box.pack(fill="both", expand=True)
        return panel

    def _open_dist(self):
        try:
            os.startfile(str(DIST_DIR))
        except OSError:
            pass

    def _open_roast_lab(self):
        from tkinter import messagebox
        if not ROAST_LAB_HMI_EXE.exists():
            messagebox.showerror("OTL Toolbox", f"Không thấy file:\n{ROAST_LAB_HMI_EXE}")
            return
        try:
            subprocess.Popen([str(ROAST_LAB_HMI_EXE)], cwd=str(ROAST_LAB_HMI_EXE.parent))
        except OSError as exc:
            messagebox.showerror("OTL Toolbox", f"Không mở được Roast Lab HMI:\n{exc}")

    def _on_close(self):
        """Gọi thủ tục đóng của từng bộ máy (đóng cổng COM, lưu cài đặt) rồi mới tắt."""
        for key, frame in list(self.engines.items()):
            handler = getattr(frame, "close_handler", None)
            if handler is None:
                continue
            try:
                handler()
            except Exception:
                traceback.print_exc()   # công cụ lỗi khi đóng → vẫn đóng tiếp, không kẹt app
                del self.engines[key]
                continue
            if frame.winfo_exists():   # công cụ từ chối đóng (người dùng bấm Huỷ)
                self.open_drawer(key)
                return
            del self.engines[key]
        self.destroy()


def start_bt_control_server(bt_app) -> None:
    """Bật máy chủ điều khiển BT Tester (MCP otl-bt-sim) như main() của app lẻ. Hỏng thì bỏ qua."""
    try:
        import bt_control_server
        _server, port = bt_control_server.khoi_dong(bt_app)
        if port:
            bt_app._bt_api_port = port
    except Exception:
        traceback.print_exc()


def main() -> None:
    prepare_paths()
    migrate_legacy_settings()
    args = sys.argv[1:]
    if len(args) >= 2 and args[0] == "--tool" and args[1] in TOOL_BY_KEY:
        run_module_as_main(TOOL_BY_KEY[args[1]].module, [sys.argv[0]])
        return
    if len(args) >= 2 and args[0] == "--chart":
        run_module_as_main("chart", ["chart", args[1]])
        return
    start = args[1] if len(args) >= 2 and args[0] == "--open" else "work"
    Toolbox(start).mainloop()
    # Luồng đọc cổng COM của công cụ có thể không phải daemon — thoát hẳn tiến trình
    os._exit(0)


if __name__ == "__main__":
    main()
