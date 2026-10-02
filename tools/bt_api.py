# -*- coding: utf-8 -*-
"""CLI lái BT Serial Tester đang chạy trên MÁY NÀY — để test HMI khỏi đốt lửa.

Cùng lý do tồn tại như `otl_api.py`: luật quyền của Claude Code khớp theo TIỀN
TỐ, nên cho phép `curl` là cho phép curl đi khắp Internet. File này chốt cứng
127.0.0.1 nên cấp quyền cho riêng nó là cấp đúng phần cần.

    python tools/bt_api.py trangthai          # cổng, baud, BT thiết bị
    python tools/bt_api.py dat 185.0          # đặt BT về đúng 185,0 °C
    python tools/bt_api.py doi -2.5           # dời BT đi −2,5 °C
    python tools/bt_api.py replay start|stop|reset

Điều kiện: BT Serial Tester phải ĐANG MỞ và đã Open cổng COM. Token đọc tự
động từ kho dùng chung với OTL Serial Terminal; đè bằng `OTL_SERIAL_API_TOKEN`.

VÒNG TEST HMI: đặt BT bằng đây → firmware đọc qua RS485 → ghi `$M` lên HMI →
đọc lại bằng Modbus TCP 502 của panel, hoặc chụp màn bằng VNC. Máy vẫn nguội.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)
from serial_terminal_auth import load_or_create_token

# CHỐT CỨNG: chỉ gọi được máy nội bộ. Nhận host từ dòng lệnh là biến file này
# thành một cái curl đội lốt, mất sạch ý nghĩa của việc thu hẹp quyền.
HOST = "127.0.0.1"
PORT = os.environ.get("OTL_BT_API_PORT") or "8777"
BASE = f"http://{HOST}:{PORT}"


def goi(duong, than=None, timeout=10):
    du_lieu = json.dumps(than).encode("utf-8") if than is not None else None
    yeu_cau = urllib.request.Request(
        BASE + duong, data=du_lieu,
        headers={"Authorization": "Bearer " + load_or_create_token(),
                 **({"Content-Type": "application/json"} if du_lieu else {})},
        method="POST" if du_lieu is not None else "GET")
    try:
        with urllib.request.urlopen(yeu_cau, timeout=timeout) as tra_loi:
            return json.load(tra_loi)
    except urllib.error.HTTPError as exc:
        try:
            chi_tiet = json.load(exc)
        except Exception:
            chi_tiet = {"error": str(exc.code), "message": exc.reason}
        print(f"Lỗi {exc.code} [{chi_tiet.get('error')}]: {chi_tiet.get('message')}",
              file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as exc:
        print(f"Không nối được BT Serial Tester tại {BASE}: {exc}\n"
              "→ Mở app BT Serial Tester lên trước (và Open cổng COM).", file=sys.stderr)
        sys.exit(2)


def main():
    bo = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    lenh = bo.add_subparsers(dest="lenh", required=True)
    lenh.add_parser("trangthai", help="cổng, baud, BT thiết bị, đang replay không")
    p = lenh.add_parser("dat", help="đặt BT về một giá trị tuyệt đối (°C)")
    p.add_argument("bt", type=float)
    p = lenh.add_parser("doi", help="dời BT đi một lượng (°C, âm/dương)")
    p.add_argument("deg", type=float)
    p = lenh.add_parser("replay", help="điều khiển phát lại hồ sơ")
    p.add_argument("action", choices=["start", "stop", "reset"])
    p = lenh.add_parser("cong", help="mở/đóng cổng COM")
    p.add_argument("action", choices=["open", "close"])

    tham_so = bo.parse_args()
    if tham_so.lenh == "trangthai":
        ket_qua = goi("/api/v1/status")
    elif tham_so.lenh == "dat":
        ket_qua = goi("/api/v1/set", {"bt": tham_so.bt})
    elif tham_so.lenh == "doi":
        ket_qua = goi("/api/v1/nudge", {"deg": tham_so.deg})
    elif tham_so.lenh == "cong":
        ket_qua = goi("/api/v1/port", {"action": tham_so.action})
    else:
        ket_qua = goi("/api/v1/replay", {"action": tham_so.action})
    print(json.dumps(ket_qua, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
