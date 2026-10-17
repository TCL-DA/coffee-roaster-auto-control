# -*- coding: utf-8 -*-
"""Bật Hồng Live nếu chưa chạy — chạy ngầm, tách khỏi phiên agent, KHÔNG mở cửa sổ (không chiếm màn hình anh Thành).

    python tools/hong_live/bat.py      ->  in "đang chạy" hoặc "đã bật", kèm địa chỉ xưởng mở
"""
import os
import socket
import subprocess
import sys
import time

CONG = 6099
SERVER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.py")


def dang_chay() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", CONG), timeout=1):
            return True
    except OSError:
        return False


def ip_lan() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))  # UDP không gửi gói, chỉ để hỏi card mạng ra ngoài
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def bat() -> bool:
    py = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.exists(py):
        py = sys.executable
    co = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    subprocess.Popen([py, SERVER, "--lan"], creationflags=co, close_fds=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(20):
        time.sleep(0.25)
        if dang_chay():
            return True
    return False


def main() -> int:
    dia_chi = "http://%s:%d/" % (ip_lan(), CONG)
    if dang_chay():
        print("Hồng Live đang chạy:", dia_chi)
        return 0
    if bat():
        print("Hồng Live đã bật:", dia_chi)
        return 0
    print("Hồng Live KHÔNG bật được — chạy tay: python tools/hong_live/server.py --lan")
    return 1


if __name__ == "__main__":
    sys.exit(main())
