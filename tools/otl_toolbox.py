"""
OTL Toolbox — gom 5 công cụ kỹ thuật vào MỘT cửa sổ, cột trái chọn công cụ.

Cách chạy:
    python tools/otl_toolbox.py               → cửa sổ Toolbox
    python tools/otl_toolbox.py --open bt     → cửa sổ Toolbox, mở sẵn tab BT
    python tools/otl_toolbox.py --tool bt     → chạy riêng một công cụ (cửa sổ riêng như cũ)
    python tools/otl_toolbox.py --chart x.json → đồ thị của bộ chuyển profile

Mã 5 công cụ giữ nguyên: lớp App của chúng viết cho cửa sổ riêng (ctk.CTk / tk.Tk).
Lúc nạp module, Toolbox tạm thay ctk.CTk / tk.Tk bằng một khung (frame) biết "giả"
các lệnh cửa sổ (title, geometry, protocol…), nên App nằm gọn trong tab bên phải.
Công cụ đã mở vẫn chạy nền khi chuyển tab — cổng COM, máy chủ API không bị ngắt.
"""
import importlib
import os
import runpy
import shutil
import subprocess
import sys
import tkinter as tk
import traceback
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from pathlib import Path

import customtkinter as ctk
from PIL import Image

FROZEN = getattr(sys, "frozen", False)
TOOLS_DIR = Path(__file__).resolve().parent
# Bộ chuyển profile (OTLRoastLab) nằm ở project 101, không chép mã sang đây
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
    subtitle: str
    module: str
    icon: str
    entry: str      # tên lớp dựng giao diện trong module
    kind: str       # "ctk": lớp con ctk.CTk · "tk": lớp con tk.Tk · "root": nhận root làm tham số
    fill: bool      # True: giãn kín tab · False: cỡ cố định, đặt giữa phía trên


TOOLS = (
    Tool("bt", "BT Serial Tester", "Giả lập cảm biến BT/ET qua cổng COM",
         "bt_serial_tester_glass", "bt_icon.ico", "App", "ctk", True),
    Tool("terminal", "Serial Terminal", "RS232/RS485, relay Modbus, API cho AI",
         "otl_serial_terminal", "otl_icon.ico", "App", "ctk", True),
    Tool("scale", "Scale Simulator", "Giả lập cân loader, lọc Kalman",
         "scale_simulator", "scale_icon.ico", "App", "ctk", True),
    Tool("convert", "Chuyển profile", "OTLRoastLab — .txt / .csv / .alog",
         "main", "assets/icon.ico", "App", "tk", False),
    Tool("monitor", "Roaster Monitor", "Theo dõi file log mẻ rang",
         "roaster_monitor", "otl_icon.ico", "RoasterMonitor", "root", False),
)
TOOL_BY_KEY = {t.key: t for t in TOOLS}

FONT = "Segoe UI"
INK = "#1E293B"          # chữ chính — tương phản > 12:1 trên nền trắng
MUTED = "#475569"        # chữ phụ — tương phản > 7:1
LINE = "#E2E8F0"
SURFACE = "#FFFFFF"
BG = "#F1F5F9"
BRAND = "#C62828"        # đỏ OTL
SELECTED_BG = "#FDECEC"
RUN = "#15803D"          # xanh "đang chạy" — luôn kèm chữ, không chỉ màu
SIDEBAR_W = 236


def resource_path(rel: str) -> Path:
    path = Path(getattr(sys, "_MEIPASS", TOOLS_DIR)) / rel
    if not path.exists() and not FROZEN:
        path = PROFILE_CONVERT_SRC.parent / rel   # icon của bộ chuyển profile (project 101)
    return path


def prepare_paths() -> None:
    """Chạy từ mã nguồn: cho Python thấy module công cụ ở tools/ và project 101."""
    if FROZEN:
        os.environ["OTL_TOOLBOX_EXE"] = sys.executable  # bộ chuyển profile mở đồ thị bằng exe này
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


class _WindowShim:
    """Giả các lệnh cửa sổ để App viết cho cửa sổ riêng nằm gọn trong một khung."""
    _tab_title = ""
    close_handler = None

    def bind(self, sequence=None, func=None, add=None):
        """Phím tắt App gắn cho "cửa sổ" → gắn lên cửa sổ Toolbox, chỉ ăn khi tab đang hiện
        và không đang gõ trong ô nhập (gõ số trong Terminal không được bắn lệnh BT)."""
        if func is None or not _is_key_sequence(sequence):
            return super().bind(sequence, func, add)

        def guarded(event, _func=func):
            if not self.winfo_ismapped():
                return None
            try:
                if event.widget.winfo_class() in _TEXT_INPUTS:
                    return None
            except (AttributeError, tk.TclError):
                pass
            return _func(event)
        return self.winfo_toplevel().bind(sequence, guarded, add="+")

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

    def _ignore_wm(self, *args, **kwargs):
        return None
    minsize = maxsize = resizable = iconbitmap = wm_iconbitmap = iconphoto = _ignore_wm
    attributes = wm_attributes = state = overrideredirect = _ignore_wm
    deiconify = withdraw = iconify = mainloop = quit = _ignore_wm


class EmbeddedCTk(_WindowShim, ctk.CTkFrame):
    def __init__(self, *args, **kwargs):
        bg = kwargs.pop("fg_color", ctk.ThemeManager.theme["CTk"]["fg_color"])
        ctk.CTkFrame.__init__(self, _host_parent, corner_radius=0, fg_color=bg)


class EmbeddedTk(_WindowShim, tk.Frame):
    def __init__(self, *args, **kwargs):
        tk.Frame.__init__(self, _host_parent)


@contextmanager
def _patched(owner, name: str, value):
    original = getattr(owner, name)
    setattr(owner, name, value)
    try:
        yield
    finally:
        setattr(owner, name, original)


def load_tool_module(tool: Tool):
    """Nạp module công cụ, lớp cửa sổ gốc của nó được kế thừa từ khung nhúng."""
    if tool.kind == "ctk":
        ctx = _patched(ctk, "CTk", EmbeddedCTk)
    elif tool.kind == "tk":
        ctx = _patched(tk, "Tk", EmbeddedTk)
    else:
        ctx = nullcontext()
    with ctx:
        return importlib.import_module(tool.module)


def build_tool(tool: Tool, parent) -> tk.Misc:
    global _host_parent
    module = load_tool_module(tool)
    _host_parent = parent
    try:
        if tool.kind == "root":
            frame = EmbeddedTk()
            frame.tool_obj = getattr(module, tool.entry)(frame)  # giữ tham chiếu
        else:
            frame = getattr(module, tool.entry)()
    finally:
        _host_parent = None
    return frame


# ════════════════════════════════════════════════════════════════════════════
#  CỬA SỔ TOOLBOX
# ════════════════════════════════════════════════════════════════════════════
class Toolbox(ctk.CTk):
    def __init__(self, start_key=None):
        super().__init__()
        ctk.set_appearance_mode("Light")
        ctk.set_default_color_theme("blue")
        self.title("OTL Toolbox")
        self.geometry("1440x920")
        self.minsize(1200, 680)
        try:
            self.iconbitmap(str(resource_path("otl_icon.ico")))
        except tk.TclError:
            pass
        self.frames = {}
        self.nav = {}
        self.current = None
        self._build()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        for i, tool in enumerate(TOOLS, start=1):
            self.bind(f"<Control-Key-{i}>", lambda _e, k=tool.key: self.select(k))
        self.after(0, lambda: self.state("zoomed"))
        if start_key in TOOL_BY_KEY:
            self.after(50, lambda: self.select(start_key))

    # ----- dựng khung -----
    def _icon(self, name: str, size: int):
        try:
            return ctk.CTkImage(light_image=Image.open(resource_path(name)), size=(size, size))
        except OSError:
            return None

    def _build(self):
        side = ctk.CTkFrame(self, width=SIDEBAR_W, corner_radius=0, fg_color=SURFACE)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        tk.Frame(self, width=1, bg=LINE).pack(side="left", fill="y")
        self.content = ctk.CTkFrame(self, corner_radius=0, fg_color=BG)
        self.content.pack(side="left", fill="both", expand=True)

        head = ctk.CTkFrame(side, fg_color="transparent")
        head.pack(fill="x", padx=16, pady=(18, 14))
        logo = self._icon("otl_symbol.png", 32)
        if logo:
            ctk.CTkLabel(head, image=logo, text="").pack(side="left", padx=(0, 10))
        ctk.CTkLabel(head, text="OTL Toolbox", text_color=INK,
                     font=ctk.CTkFont(FONT, 18, "bold")).pack(side="left")

        for i, tool in enumerate(TOOLS, start=1):
            self.nav[tool.key] = self._nav_item(side, i, tool)

        foot = ctk.CTkFrame(side, fg_color="transparent")
        foot.pack(side="bottom", fill="x", padx=12, pady=14)
        ctk.CTkLabel(foot, text="Ctrl+1 … Ctrl+5: chuyển công cụ", text_color=MUTED,
                     font=ctk.CTkFont(FONT, 11)).pack(anchor="w", padx=4, pady=(8, 0))
        self._outline_button(foot, "Thư mục dist", self._open_dist).pack(fill="x", pady=(6, 0))
        self._outline_button(foot, "Mở Roast Lab HMI  ↗", self._open_roast_lab).pack(fill="x")
        tk.Frame(side, height=1, bg=LINE).pack(side="bottom", fill="x", padx=12)

        self._show_panel(self._welcome_panel())

    def _outline_button(self, parent, text: str, command):
        return ctk.CTkButton(parent, text=text, height=44, corner_radius=8, fg_color="transparent",
                             border_width=1, border_color="#CBD5E1", text_color=INK,
                             hover_color=LINE, font=ctk.CTkFont(FONT, 13), command=command)

    def _nav_item(self, parent, idx: int, tool: Tool):
        row = ctk.CTkFrame(parent, fg_color="transparent", corner_radius=8)
        row.pack(fill="x", padx=10, pady=2)
        bar = tk.Frame(row, width=4, bg=SURFACE)
        bar.pack(side="left", fill="y", pady=6)
        btn = ctk.CTkButton(row, text=f"  {tool.title}", image=self._icon(tool.icon, 26),
                            anchor="w", height=52, corner_radius=8, fg_color="transparent",
                            hover_color=LINE, text_color=INK, font=ctk.CTkFont(FONT, 14),
                            command=lambda k=tool.key: self.select(k))
        btn.pack(side="left", fill="x", expand=True, padx=(4, 0))
        status = ctk.CTkLabel(row, text="", width=0, text_color=RUN,
                              font=ctk.CTkFont(FONT, 11, "bold"))
        status.pack(side="right", padx=(0, 6))
        return row, bar, btn, status

    def _welcome_panel(self):
        panel = ctk.CTkFrame(self.content, fg_color="transparent")
        ctk.CTkLabel(panel, text="Chọn công cụ ở cột bên trái", text_color=INK,
                     font=ctk.CTkFont(FONT, 22, "bold")).pack(anchor="w")
        lines = [f"{t.title} — {t.subtitle}" for t in TOOLS] + [
            "",
            "Công cụ đã mở vẫn chạy nền khi chuyển sang công cụ khác (cổng COM giữ kết nối).",
            "Đóng OTL Toolbox là đóng tất cả công cụ.",
        ]
        ctk.CTkLabel(panel, text="\n".join(lines), justify="left", text_color=MUTED,
                     font=ctk.CTkFont(FONT, 14)).pack(anchor="w", pady=(10, 0))
        return panel

    # ----- chuyển công cụ -----
    def _show_panel(self, widget, fill: bool = False):
        for child in self.content.winfo_children():
            child.pack_forget()
        if fill:
            widget.pack(fill="both", expand=True)
        else:
            widget.pack(anchor="n", padx=32, pady=28)

    def select(self, key: str):
        tool = TOOL_BY_KEY[key]
        self.current = key
        self._refresh_nav()
        if key in self.frames:
            self._show_panel(self.frames[key], tool.fill)
            self.title(f"OTL Toolbox — {tool.title}")
            return
        loading = ctk.CTkLabel(self.content, text=f"Đang mở {tool.title}…", text_color=MUTED,
                               font=ctk.CTkFont(FONT, 16))
        self._show_panel(loading)
        self.after(30, lambda: self._load(tool, loading))

    def _load(self, tool: Tool, loading):
        try:
            frame = build_tool(tool, self.content)
        except Exception:  # công cụ lỗi không được kéo sập cả Toolbox
            loading.destroy()
            self._show_panel(self._error_panel(tool, traceback.format_exc()))
            return
        loading.destroy()
        self.frames[tool.key] = frame
        self._refresh_nav()
        if self.current == tool.key:
            self.select(tool.key)
        else:
            frame.pack_forget()

    def _error_panel(self, tool: Tool, detail: str):
        panel = ctk.CTkFrame(self.content, fg_color="transparent")
        ctk.CTkLabel(panel, text=f"Không mở được {tool.title}", text_color=BRAND,
                     font=ctk.CTkFont(FONT, 20, "bold")).pack(anchor="w")
        ctk.CTkLabel(panel, text="Các công cụ khác vẫn dùng bình thường. Chi tiết lỗi:",
                     text_color=MUTED, font=ctk.CTkFont(FONT, 13)).pack(anchor="w", pady=(6, 8))
        box = ctk.CTkTextbox(panel, width=900, height=360, font=ctk.CTkFont("Consolas", 12))
        box.insert("1.0", detail)
        box.configure(state="disabled")
        box.pack(anchor="w")
        return panel

    def _refresh_nav(self):
        for key, (row, bar, btn, status) in self.nav.items():
            active = key == self.current
            row.configure(fg_color=SELECTED_BG if active else "transparent")
            bar.configure(bg=BRAND if active else SURFACE)
            btn.configure(font=ctk.CTkFont(FONT, 14, "bold" if active else "normal"),
                          hover_color=SELECTED_BG if active else LINE)
            status.configure(text="chạy" if key in self.frames else "")

    # ----- nút phụ -----
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

    # ----- đóng -----
    def _on_close(self):
        """Gọi thủ tục đóng của từng công cụ (đóng cổng COM, lưu cài đặt) rồi mới tắt."""
        for key, frame in list(self.frames.items()):
            handler = getattr(frame, "close_handler", None)
            if handler is None:
                continue
            try:
                handler()
            except Exception:
                traceback.print_exc()
            if frame.winfo_exists():   # công cụ từ chối đóng (người dùng bấm Huỷ)
                self.select(key)
                return
            del self.frames[key]
        self.destroy()


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
    start_key = args[1] if len(args) >= 2 and args[0] == "--open" else None
    Toolbox(start_key).mainloop()
    # Luồng đọc cổng COM của công cụ có thể không phải daemon — thoát hẳn tiến trình
    os._exit(0)


if __name__ == "__main__":
    main()
