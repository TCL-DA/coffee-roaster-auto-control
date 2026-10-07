"""Dựng board ảo: biên dịch firmware THẬT (src/main.cpp + include/) chạy trên PC.

    python tools/fw_sim/build.py           -> tools/fw_sim/out/otl_fw_sim.exe

Trình biên dịch: `zig c++` (gói pip ziglang, clang 21) — đích x86_64-windows-gnu.
Thư viện phần cứng thay bằng stub/ (Arduino, ModbusMaster, ModbusRTU, SD, DAC, timer).
SimpleKalmanFilter dùng nguyên mã thư viện thật trong .pio/libdeps.
"""
import glob
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
# OTL_FW_SRC: thư mục có src/ + include/ KHÁC repo (vd bản sao đã vá để thử, không đụng mã thật)
SRC = os.path.abspath(os.environ.get("OTL_FW_SRC") or REPO)
OUT = os.path.join(HERE, "out")
EXE_NAME = os.environ.get("OTL_FW_OUT") or "otl_fw_sim.exe"
LIBDEPS = os.path.join(REPO, ".pio", "libdeps", "genericSTM32F103RC")


def kalman_src():
    hits = glob.glob(os.path.join(LIBDEPS, "SimpleKalmanFilter", "**", "SimpleKalmanFilter.cpp"), recursive=True)
    if not hits:
        sys.exit("thiếu SimpleKalmanFilter trong .pio/libdeps — chạy 'pio pkg install' trước")
    return hits[0]


def build(extra=()):
    os.makedirs(OUT, exist_ok=True)
    ksrc = kalman_src()
    exe = os.path.join(OUT, EXE_NAME)
    cmd = [sys.executable, "-m", "ziglang", "c++", "-target", "x86_64-windows-gnu",
           "-std=gnu++17", "-O1", "-g", "-fno-sanitize=all",
           "-DSTM32F1", "-DARDUINO=10813", "-DARDUINO_ARCH_STM32", "-DOTL_FW_SIM=1",
           "-I", os.path.join(HERE, "stub"),
           "-I", os.path.join(SRC, "include"),
           "-I", os.path.dirname(ksrc),
           "-Wno-everything",
           os.path.join(SRC, "src", "main.cpp"),
           os.path.join(HERE, "sim_core.cpp"),
           ksrc,
           "-lws2_32", "-lwinmm", "-ldbghelp",
           "-o", exe] + list(extra)
    t0 = time.time()
    r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        errs = [ln for ln in (r.stderr or "").splitlines() if "error" in ln]
        print("\n".join(errs[:60]) or r.stderr[-4000:])
        print("== LỖI BIÊN DỊCH: %d dòng error" % len(errs))
        sys.exit(1)
    print("== đã dựng %s (%.0f KB) sau %.1fs" % (exe, os.path.getsize(exe) / 1024, time.time() - t0))
    return exe


if __name__ == "__main__":
    build(sys.argv[1:])
