# -*- coding: utf-8 -*-
"""Bài thử CẤU HÌNH MÁY lúc chạy ($M62, include/MachineOpt.h) trên TRỌN HỆ mô phỏng:
HMIApp (panel ảo) + board ảo chạy firmware thật (tools/fw_sim/out/otl_fw_sim.exe).

    python tools/fw_sim/test_mc_opt.py [thư mục bản HMI biên dịch]

Một lần khởi động, đổi $M62 qua Modbus TCP của HMIApp (như Master lưu trên màn Cấu hình máy):
  C1 chưa cấu hình  → bật gas / Start bị trả về 0, mã 422, relay gas KHÔNG đóng
  C2 30 kg trơn     → không hỏi biến tần gió (ID 5) và relay ngoài (ID 7); bật gas được
  C3 30 kg đủ bộ    → có hỏi ID 5 và ID 7
  C4 vô lý          → mã 423, giữ cấu hình cũ (vẫn hỏi ID 5)
  C5 đổi khi có lửa → chưa áp, tắt lửa xong mới áp
In 'DAT …' / 'LOI …' từng mục, cuối 'KET LUAN: DAT|LOI'; mã thoát 1 nếu có LOI.
"""
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
EMU = r"F:\Project\112_Quanly\mcp-dpa\emu"
sys.path.insert(0, EMU)
from otl_emu import LinkClient, TcpMaster  # noqa: E402
from run_system import System  # noqa: E402


def fw_cmd(cmd):
    """Lệnh chữ tới board ảo qua pipe \\\\.\\pipe\\otl_fw_sim (cùng giao thức emu_board của MCP dpa)."""
    import ctypes
    from ctypes import wintypes as wt
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateFileW.restype = wt.HANDLE
    # Board ảo mở lại cổng pipe sau mỗi lượt nối — gọi dồn dập thì có lúc chưa kịp mở: thử lại tới 2 s.
    for _ in range(40):
        h = k32.CreateFileW(r"\\.\pipe\otl_fw_sim", 0xC0000000, 0, None, 3, 0, None)
        if h and h != wt.HANDLE(-1).value:
            break
        time.sleep(0.05)
    else:
        raise RuntimeError("board ảo không trả lời pipe")
    mode = wt.DWORD(2)
    k32.SetNamedPipeHandleState(h, ctypes.byref(mode), None, None)
    n = wt.DWORD()
    b = cmd.encode()
    k32.WriteFile(h, b, len(b), ctypes.byref(n), None)
    buf = ctypes.create_string_buffer(4096)
    k32.ReadFile(h, buf, 4096, ctypes.byref(n), None)
    k32.CloseHandle(h)
    return json.loads(buf.raw[:n.value].decode("utf-8", "replace"))

BUILD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(EMU, "builds", "T-R0-1012-LO80")
HERE = os.path.dirname(os.path.abspath(__file__))
RA = os.path.join(HERE, "log", "test_mc_opt")

W_START, W_GAS, W_STT = 40001, 40002, 40041   # pipe otl_hmi_link đánh số = 40001 + địa chỉ board (sim_core.cpp link_frame)
OPT_CONFIGURED, SIZE_30 = 0x8000, 3 << 6
OPT_VACUUM, OPT_LOADER, OPT_SCALE, OPT_RELAY = 0x0004, 0x0008, 0x0010, 0x0020
OPT_AB, OPT_DES, OPT_SPLIT, OPT_VR_DRUM = 0x0200, 0x0400, 0x0800, 0x0002
TRON = OPT_CONFIGURED | SIZE_30
DU = TRON | OPT_VACUUM | OPT_LOADER | OPT_SCALE | OPT_RELAY | OPT_AB | OPT_DES | OPT_SPLIT
VO_LY = TRON | OPT_VR_DRUM                 # VR trống mà không có VR gas + gió

KQ = []


def kiem(ten, dat, chi_tiet=""):
    KQ.append(dat)
    print(("DAT " if dat else "LOI ") + ten + ("" if dat else "  | " + str(chi_tiet)), flush=True)


def st():
    return fw_cmd("status")


def hoi(slave):
    return st()["hoi_rs485"][str(slave)]


def cho_ma(link, ma, giay):
    """Có thấy mã trạng thái `ma` ở W40041 trong `giay` giây không."""
    t = time.time()
    while time.time() - t < giay:
        if link.read_words(W_STT)[0] == ma:
            return True
        time.sleep(0.1)
    return False


def dat_m62(v):
    tm = TcpMaster()
    tm.write_M(62, v & 0xFFFF)
    tm.close()


def cho_firmware(giay=90):
    """Board đã vào vòng chính: lượt hỏi đồng hồ BT tăng đều."""
    t = time.time()
    while time.time() - t < giay:
        try:
            a = hoi(1); time.sleep(2); b = hoi(1)
            if b - a >= 3:
                return True
        except Exception:
            time.sleep(1)
    return False


def main():
    os.makedirs(RA, exist_ok=True)
    prof = json.load(open(os.path.join(EMU, "m_profile_30kg.json"), encoding="utf-8"))
    prof["62"] = 0                                   # C1: panel mới, chưa cấu hình
    p_json = os.path.join(RA, "m_profile_c1.json")
    json.dump(prof, open(p_json, "w", encoding="utf-8"))

    s = System(BUILD, RA)
    s.start(fresh_state=True, m_profile=p_json)
    link = LinkClient()
    link.open()
    try:
        kiem("board vào vòng chính", cho_firmware())

        # ── C1 chưa cấu hình ────────────────────────────────────────────────
        link.write_words(W_GAS, [1])
        thay = cho_ma(link, 422, 5)
        kiem("C1 chưa cấu hình: báo 422", thay)
        time.sleep(1.5)
        kiem("C1 nút gas bị trả về 0", link.read_words(W_GAS)[0] == 0, link.read_words(W_GAS))
        kiem("C1 relay gas KHÔNG đóng", st()["rl"]["gas"] == 0, st()["rl"])
        link.write_words(W_START, [1])
        time.sleep(2.5)
        kiem("C1 Start bị trả về 0", link.read_words(W_START)[0] == 0, link.read_words(W_START))
        kiem("C1 không hỏi ID 5 / ID 7", hoi(5) == 0 and hoi(7) == 0, st()["hoi_rs485"])

        # ── C2 30 kg trơn ───────────────────────────────────────────────────
        dat_m62(TRON)
        time.sleep(3)
        h5, h7 = hoi(5), hoi(7)
        link.write_words(W_GAS, [1])
        time.sleep(3)
        kiem("C2 bật gas được (nút giữ 1)", link.read_words(W_GAS)[0] == 1, link.read_words(W_GAS))
        kiem("C2 relay gas đóng", st()["rl"]["gas"] == 1, st()["rl"])
        link.write_words(W_GAS, [0])
        time.sleep(8)                                 # tắt lửa, máy đứng yên trở lại
        kiem("C2 không hỏi ID 5 / ID 7", hoi(5) == h5 and hoi(7) == h7, (h5, h7, st()["hoi_rs485"]))

        # ── C3 30 kg đủ bộ ──────────────────────────────────────────────────
        dat_m62(DU)
        time.sleep(4)
        h5, h7 = hoi(5), hoi(7)
        time.sleep(4)
        kiem("C3 có hỏi ID 5 (biến tần gió / áp hút)", hoi(5) > h5, (h5, hoi(5)))
        kiem("C3 có hỏi ID 7 (relay ngoài)", hoi(7) > h7, (h7, hoi(7)))

        # ── C4 vô lý ────────────────────────────────────────────────────────
        dat_m62(VO_LY)
        kiem("C4 cấu hình vô lý: báo 423", cho_ma(link, 423, 5))
        h5 = hoi(5)
        time.sleep(3)
        kiem("C4 giữ cấu hình cũ (vẫn hỏi ID 5)", hoi(5) > h5, (h5, hoi(5)))

        # ── C5 đổi khi có lửa ───────────────────────────────────────────────
        dat_m62(TRON)                                 # về trơn (đứng yên ⇒ áp ngay)
        time.sleep(3)
        link.write_words(W_GAS, [1])
        t = time.time()
        while time.time() - t < 70 and not st()["flame"]:      # bếp premix ảo mồi ~40 s mới có lửa
            time.sleep(0.5)
        kiem("C5 có lửa trước khi đổi", st()["flame"] == 1, st())
        dat_m62(DU)
        time.sleep(1)
        h5 = hoi(5)
        time.sleep(4)
        kiem("C5 đang có lửa: CHƯA áp (không hỏi ID 5)", hoi(5) == h5, (h5, hoi(5)))
        link.write_words(W_GAS, [0])
        t = time.time()
        while time.time() - t < 30 and st()["flame"]:
            time.sleep(0.5)
        time.sleep(3)
        h5 = hoi(5)
        time.sleep(4)
        kiem("C5 tắt lửa xong: đã áp (có hỏi ID 5)", hoi(5) > h5, (h5, hoi(5)))
    finally:
        link.close()
        s.shot("cuoi.png")
        s.stop()

    print("KET LUAN:", "DAT" if all(KQ) else "LOI", "(%d/%d mục)" % (sum(KQ), len(KQ)))
    sys.exit(0 if all(KQ) else 1)


if __name__ == "__main__":
    main()
