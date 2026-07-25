"""
gen_pc_link.py — sinh bản đồ register PC_Link cho CẢ BA phía từ một nguồn duy nhất.

    protocol/pc_link.json  ──┬─→ include/PC_Link_Map.h        (firmware C++)
                             ├─→ tools/pc_link_map.py         (tool Python)
                             └─→ khối đánh dấu trong 'OTL Roast Lab.html' (JS)

VÌ SAO: trước đây địa chỉ/hệ số nằm rải ở 3 nơi, sửa 1 chỗ quên 2 chỗ kia là app
đọc sai số mà không ai báo lỗi. Giờ sửa JSON → sinh lại → cả 3 phía luôn khớp.

    python protocol/gen_pc_link.py            # sinh lại
    python protocol/gen_pc_link.py --check    # chỉ kiểm tra, lệch thì exit 1

--check còn đối chiếu giá trị progStep trong JSON với #define STP_* của Define.h,
bắt được ca sửa quy trình firmware mà quên cập nhật giao thức.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = os.path.join(ROOT, "protocol", "pc_link.json")
OUT_H = os.path.join(ROOT, "include", "PC_Link_Map.h")
OUT_PY = os.path.join(ROOT, "tools", "pc_link_map.py")
OUT_HTML = os.path.join(ROOT, "OTL Roast Lab.html")
DEFINE_H = os.path.join(ROOT, "include", "Define.h")

MARK_A = "/* <<< PC_LINK MAP — SINH TỰ ĐỘNG, ĐỪNG SỬA TAY (protocol/gen_pc_link.py) */"
MARK_B = "/* PC_LINK MAP >>> */"

BANNER = "SINH TỰ ĐỘNG từ protocol/pc_link.json — ĐỪNG SỬA TAY."
REGEN = "Sửa JSON rồi chạy: python protocol/gen_pc_link.py"


def load() -> dict:
    with io.open(SPEC, encoding="utf-8") as f:
        return json.load(f)


def cname(f: dict) -> str:
    return f["c"]


# ── C++ ─────────────────────────────────────────────────────────────────────
def gen_h(s: dict) -> str:
    rd, wr = s["read"], s["write"]
    L = ["// " + "=" * 74,
         f"// PC_Link_Map.h — {BANNER}",
         f"// {REGEN}",
         "// Bản đồ register dùng chung giữa firmware và app OTL Roast Lab.",
         "// " + "=" * 74,
         "#ifndef PC_LINK_MAP_H",
         "#define PC_LINK_MAP_H",
         "",
         f"#define PCL_VERSION    {s['version']}",
         "",
         f"// ── Khối ĐỌC (máy → app) — {rd['base']}..{rd['base'] + len(rd['fields']) - 1} ──",
         f"// {rd['comment']}",
         f"#define PCL_R_BASE     {rd['base']}"]
    w = max(len(cname(f)) for f in rd["fields"]) + 8
    for i, f in enumerate(rd["fields"]):
        nm = f"PCL_R_{cname(f)}".ljust(w)
        unit = f" [{f['unit']}]" if f.get("unit") else ""
        sc = f" ×{f['scale']}" if f.get("scale", 1) != 1 else ""
        sg = " (có dấu)" if f.get("signed") else ""
        L.append(f"#define {nm} (PCL_R_BASE + {i:<2})  // {f['desc']}{unit}{sc}{sg}")
    L += [f"#define PCL_R_COUNT    {len(rd['fields'])}", ""]

    for name, bm in s["bitmaps"].items():
        L.append(f"// Bit của {name}")
        pw = max(len(b.get("c", b["key"]).upper()) for b in bm["bits"]) + len(bm["c_prefix"]) + 2
        for b in bm["bits"]:
            nm = f"{bm['c_prefix']}_{b.get('c', b['key']).upper()}".ljust(pw)
            L.append(f"#define {nm} 0x{1 << b['bit']:02X}   // {b['desc']}")
        L.append("")

    L += [f"// ── Khối GHI (app → máy) — {wr['base']}..{wr['base'] + len(wr['fields']) - 1} ──",
          f"// {wr['comment']}",
          f"#define PCL_W_BASE     {wr['base']}"]
    w = max(len(cname(f)) for f in wr["fields"]) + 8
    for i, f in enumerate(wr["fields"]):
        nm = f"PCL_W_{cname(f)}".ljust(w)
        sc = f" ×{f['scale']}" if f.get("scale", 1) != 1 else ""
        L.append(f"#define {nm} (PCL_W_BASE + {i:<2})  // {f['desc']}{sc}  [{f['min']}..{f['max']}]")
    L += [f"#define PCL_W_COUNT    {len(wr['fields'])}", ""]

    L += ["// Giới hạn kẹp phía firmware — tầng 2 của clamp 2 tầng (app kẹp tầng 1)",
          "static const int16_t PCL_W_MIN[PCL_W_COUNT] = {"
          + ", ".join(str(f["min"]) for f in wr["fields"]) + "};",
          "static const int16_t PCL_W_MAX[PCL_W_COUNT] = {"
          + ", ".join(str(f["max"]) for f in wr["fields"]) + "};",
          ""]

    cfg = s.get("config")
    if cfg:
        n = len(cfg["regs"])
        L += [f"// ── Khối CẤU HÌNH $M (handshake app↔máy) — {cfg['base']}..{cfg['base'] + n - 1} ──",
              f"// {cfg['comment']}",
              f"#define PCL_CFG_BASE   {cfg['base']}"]
        cw = max(len(r["c"]) for r in cfg["regs"]) + 9
        for i, r in enumerate(cfg["regs"]):
            nm = f"PCL_CFG_{r['c']}".ljust(cw)
            L.append(f"#define {nm} (PCL_CFG_BASE + {i})  // {r['desc']}")
        L += [f"#define PCL_CFG_COUNT  {n}",
              f"#define PCL_CFG_MAXIDX {cfg['count']}   // số $M lớn nhất (idx hợp lệ 1..MAXIDX)",
              f"#define PCL_CFG_IDLE   {cfg['cmd_idle']}",
              f"#define PCL_CFG_READ   {cfg['cmd_read']}",
              f"#define PCL_CFG_WRITE  {cfg['cmd_write']}",
              f"#define PCL_CFG_ST_OK  {cfg['status_ok']}",
              f"#define PCL_CFG_ST_ERR {cfg['status_err']}", ""]

    fs = s["failsafe"]
    L += ["// ── Chốt an toàn khi APP là bộ điều khiển ──────────────────────────────",
          f"#define PCL_APP_TMO_S    {fs['app_timeout_s']}   "
          "// app không nhấp heartbeat quá ngần này giây → nhả quyền về HMI + còi",
          f"#define PCL_FLAME_TMO_S  {fs['flame_timeout_s']}  "
          "// bật gas mà không có lửa quá ngần này giây → firmware TỰ ĐÓNG GAS",
          ""]

    L += ["// ── Khối tương thích (Modbus_Slave.h) — app đọc/ghi khi máy chưa có PC_Link ──",
          "// Không định nghĩa lại địa chỉ; chỉ ĐỐI CHIẾU để spec không lệch khỏi firmware.",
          "#ifdef BT_show_artisan"]
    for f in s["read_artisan"]["fields"] + s["write_artisan"]["fields"]:
        L.append(f'static_assert({f["c_check"]} == {f["reg"]}, '
                 f'"pc_link.json lech {f["c_check"]} — chay: python protocol/gen_pc_link.py");')
    L += ["#endif", "", "#endif  // PC_LINK_MAP_H", ""]
    return "\n".join(L)


# ── Python ──────────────────────────────────────────────────────────────────
def gen_py(s: dict) -> str:
    rd, wr = s["read"], s["write"]
    L = ['"""',
         f"pc_link_map.py — {BANNER}",
         f"{REGEN}",
         "",
         "Bản đồ register + giải mã gói dữ liệu máy rang, dùng chung với firmware.",
         '"""',
         "",
         f"VERSION = {s['version']}",
         f"BAUD_DEFAULT = {s['link']['baud_default']}",
         f"SLAVE_DEFAULT = {s['link']['slave_default']}",
         "",
         f"R_BASE, R_COUNT = {rd['base']}, {len(rd['fields'])}",
         f"W_BASE, W_COUNT = {wr['base']}, {len(wr['fields'])}",
         "",
         "# tên → chỉ số trong khối GHI (offset từ W_BASE)",
         "W_INDEX = {"]
    for i, f in enumerate(wr["fields"]):
        L.append(f'    "{f["key"]}": {i},')
    L += ["}", "",
          "# giới hạn kẹp phía PC (firmware kẹp lần nữa — clamp 2 tầng)",
          "W_RANGE = {"]
    for f in wr["fields"]:
        L.append(f'    "{f["key"]}": ({f["min"]}, {f["max"]}),   # {f["desc"]}')
    L += ["}", "",
          "# hệ số ghi: giá trị kỹ thuật × scale = số gửi xuống máy",
          "W_SCALE = {" + ", ".join(f'"{f["key"]}": {f.get("scale", 1)}' for f in wr["fields"]) + "}",
          ""]

    for name, bm in s["bitmaps"].items():
        L.append(f"{name.upper()}_BITS = {{")
        for b in bm["bits"]:
            L.append(f'    "{b["key"]}": 0x{1 << b["bit"]:02X},   # {b["desc"]}')
        L += ["}", ""]

    L += ["# progStep của firmware (Define.h)",
          "STP = {"]
    for k, v in s["steps"].items():
        if k.startswith("_"):
            continue
        L.append(f'    "{k}": {v},')
    L += ["}", "",
          "# MỐC ĐÃ ĐẠT ⟺ progStep >= giá trị này. LỆCH MỘT BƯỚC so với STP:",
          "# progStep = 'đang CHỜ mốc đó', không phải 'đã qua'. Chấm mốc dùng bảng NÀY.",
          "MILE_STEP = {"]
    for k, v in s["mile_step"].items():
        if k.startswith("_"):
            continue
        L.append(f'    "{k}": {v},')
    L += ["}", ""]

    ar = s["read_artisan"]
    L += ["# ── Khối tương thích (reg 0..19) — máy chưa nạp PC_Link vẫn đọc được ──",
          f"A_BASE, A_COUNT = {ar['base']}, {ar['count']}",
          "A_FIELDS = {   # key → (offset, scale, signed)"]
    for f in ar["fields"]:
        L.append(f'    "{f["key"]}": ({f["reg"]}, {f.get("scale", 1)}, '
                 f'{bool(f.get("signed"))}),   # {f["desc"]}')
    L += ["}", "",
          "",
          "def decode_artisan(regs):",
          '    """Khối tương thích thô → dict. Thiếu RoR/thời gian/mốc — xem roast_derive.py."""',
          "    if len(regs) < A_COUNT:",
          '        raise ValueError(f"cần {A_COUNT} register, nhận {len(regs)}")',
          "    out = {}",
          "    for key, (off, scale, sgn) in A_FIELDS.items():",
          "        v = regs[off]",
          "        if sgn:",
          "            v = to_signed(v)",
          "        out[key] = v / float(scale) if scale != 1 else v",
          "    return out",
          "",
          ""]

    aw = s["write_artisan"]
    L += ["# ── Ô LỆNH khối tương thích — điều khiển máy chưa nạp PC_Link ──",
          "# KHÔNG có xung: mọi ô đều là MỨC. latch = ghi 1 rồi thôi, firmware tự đóng.",
          "AW_INDEX = {   # key → (địa chỉ register, 'level' | 'toggle' | 'latch')"]
    for f in aw["fields"]:
        L.append(f'    "{f["key"]}": ({f["reg"]}, "{f["kind"]}"),   # {f["desc"]}')
    L += ["}", ""]

    dv = s["derive"]
    L += ["# Tham số để tái tạo đúng phép tính firmware (xem roast_derive.py)",
          "DERIVE = {"]
    for k, v in dv.items():
        if not k.startswith("_"):
            L.append(f"    \"{k}\": {v!r},")
    L += ["}", ""]

    cfg = s.get("config")
    if cfg:
        L += ["# Handshake cấu hình $M — đọc/ghi 1 tham số (idx = số $M 1..MAXIDX)",
              f"CFG_BASE = {cfg['base']}",
              "CFG_REG = {"]
        for i, r in enumerate(cfg["regs"]):
            L.append(f'    "{r["key"]}": {cfg["base"] + i},   # {r["desc"]}')
        L += ["}",
              f"CFG_MAXIDX = {cfg['count']}",
              f"CFG_CMD = {{'idle': {cfg['cmd_idle']}, 'read': {cfg['cmd_read']}, 'write': {cfg['cmd_write']}}}",
              f"CFG_STATUS = {{'busy': {cfg['status_busy']}, 'ok': {cfg['status_ok']}, 'err': {cfg['status_err']}}}",
              ""]

    fs = s["failsafe"]
    L += ["# Chốt an toàn khi app là bộ điều khiển",
          "FAILSAFE = {"]
    for k, v in fs.items():
        if not k.startswith("_"):
            L.append(f"    \"{k}\": {v!r},")
    L += ["}", "",
          "",
          "def to_signed(v):",
          '    """Register 16-bit về số có dấu."""',
          "    return v - 0x10000 if v >= 0x8000 else v",
          "",
          "",
          "def decode(regs):",
          '    """Khối ĐỌC thô (15 register) → dict đơn vị kỹ thuật."""',
          "    if len(regs) < R_COUNT:",
          '        raise ValueError(f"cần {R_COUNT} register, nhận {len(regs)}")',
          "    return {"]
    for i, f in enumerate(rd["fields"]):
        if f.get("bits"):
            L.append(f'        "{f["key"]}": {{k: bool(regs[{i}] & m) '
                     f"for k, m in {f['bits'].upper()}_BITS.items()}},")
        else:
            expr = f"regs[{i}]"
            if f.get("signed"):
                expr = f"to_signed({expr})"
            if f.get("scale", 1) != 1:
                expr = f"{expr} / {float(f['scale'])}"
            L.append(f'        "{f["key"]}": {expr},   # {f["desc"]}')
    L += ["    }", ""]
    return "\n".join(L)


# ── JS (khối nhúng trong file HTML một-file) ────────────────────────────────
def gen_js(s: dict) -> str:
    steps = {k: v for k, v in s["steps"].items() if not k.startswith("_")}
    flags = [b["key"] for b in s["bitmaps"]["flags"]["bits"]]
    phase = [b["key"] for b in s["bitmaps"]["phase"]["bits"]]
    dv = {k: v for k, v in s["derive"].items() if not k.startswith("_")}
    fs = {k: v for k, v in s["failsafe"].items() if not k.startswith("_")}
    cfg = s.get("config")
    cfg_js = ""
    if cfg:
        cfg_obj = {
            "base": cfg["base"],
            "reg": {r["key"]: cfg["base"] + i for i, r in enumerate(cfg["regs"])},
            "maxIdx": cfg["count"],
            "cmd": {"idle": cfg["cmd_idle"], "read": cfg["cmd_read"], "write": cfg["cmd_write"]},
            "status": {"busy": cfg["status_busy"], "ok": cfg["status_ok"], "err": cfg["status_err"]},
        }
        cfg_js = "const PCL_CFG=" + json.dumps(cfg_obj, ensure_ascii=False) + ";"
    lines = [
        MARK_A,
        f"const PCL_VERSION={s['version']};",
        "/* progStep của firmware */",
        "const STP=" + json.dumps(steps, ensure_ascii=False) + ";",
        "/* Mốc ĐÃ ĐẠT ⟺ progStep >= giá trị này — lệch 1 bước so với STP,",
        "   vì progStep nghĩa là 'đang CHỜ mốc đó'. Chấm mốc phải dùng bảng này. */",
        "const MILE_STEP=" + json.dumps(
            {k: v for k, v in s["mile_step"].items() if not k.startswith("_")},
            ensure_ascii=False) + ";",
        "const PCL_FLAGS=" + json.dumps(flags) + ";",
        "const PCL_PHASES=" + json.dumps(phase) + ";",
        "/* Ngưỡng/hệ số app dùng khi TỰ TÍNH (máy chưa có PC_Link, hoặc app tự lái) */",
        "const PCL_DERIVE=" + json.dumps(dv, ensure_ascii=False) + ";",
        "const PCL_FAILSAFE=" + json.dumps(fs, ensure_ascii=False) + ";",
    ]
    if cfg_js:
        lines.append("/* Handshake cấu hình $M — đọc/ghi 1 tham số qua PC_Link (Bước E) */")
        lines.append(cfg_js)
    lines.append(MARK_B)
    return "\n".join(lines)


def html_with(block: str) -> str:
    with io.open(OUT_HTML, encoding="utf-8") as f:
        src = f.read()
    i, j = src.find(MARK_A), src.find(MARK_B)
    if i < 0 or j < 0:
        raise SystemExit(f"Không thấy mốc PC_LINK MAP trong {os.path.basename(OUT_HTML)}. "
                         "Thêm 2 dòng mốc rồi chạy lại.")
    return src[:i] + block + src[j + len(MARK_B):]


def main():
    ap = argparse.ArgumentParser(description="Sinh bản đồ PC_Link cho firmware + tool + giao diện")
    ap.add_argument("--check", action="store_true", help="chỉ kiểm tra đồng bộ, không ghi")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    s = load()
    targets = [(OUT_H, gen_h(s)), (OUT_PY, gen_py(s)), (OUT_HTML, html_with(gen_js(s)))]

    # đối chiếu progStep với Define.h — bắt ca đổi quy trình firmware mà quên giao thức
    problems = []
    if os.path.exists(DEFINE_H):
        with io.open(DEFINE_H, encoding="utf-8", errors="replace") as f:
            dh = f.read()
        for key, macro in s["step_define"].items():
            m = re.search(rf"^\s*#define\s+{macro}\s+(\d+)", dh, re.M)
            if not m:
                problems.append(f"Define.h thiếu {macro} (ứng với step {key})")
            elif int(m.group(1)) != s["steps"][key]:
                problems.append(f"{macro}={m.group(1)} nhưng pc_link.json ghi {key}={s['steps'][key]}")

    stale = []
    for path, content in targets:
        old = io.open(path, encoding="utf-8").read() if os.path.exists(path) else None
        if old != content:
            stale.append(path)

    if a.check:
        for p in problems:
            print("  LỆCH  " + p)
        for p in stale:
            print("  CŨ    " + os.path.relpath(p, ROOT))
        if problems or stale:
            print("\nKhông đồng bộ → chạy: python protocol/gen_pc_link.py")
            return 1
        print("Cả 3 phía khớp bản đồ PC_Link.")
        return 0

    for p in problems:
        print("  CẢNH BÁO  " + p)
    for path, content in targets:
        with io.open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        print(("  cập nhật  " if path in stale else "  giữ nguyên ")
              + os.path.relpath(path, ROOT))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
