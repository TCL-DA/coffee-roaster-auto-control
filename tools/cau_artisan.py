# -*- coding: utf-8 -*-
"""CẦU MODBUS TCP cho Artisan — agent (OTL Hồng) giữ cổng COM của board, Artisan đọc số qua TCP (14/10/2026).

Một cổng COM chỉ một phần mềm mở được. Agent đọc khối Artisan 0..19 của board mỗi chu kỳ (otl_link cfg doc_buong) rồi phát lại
NGUYÊN VĂN qua Modbus TCP (FC3 / FC4). Artisan cài: Modbus type TCP, host 127.0.0.1, port CONG (5020). CHỈ ĐỌC — lệnh ghi từ
Artisan bị từ chối (ngoại lệ 1) để chỉ một bên lái máy.

    from cau_artisan import CauArtisan
    cau = CauArtisan(lambda: (link.snapshot().get("data") or {}).get("artisan_regs")); cau.start()
"""
import socket
import struct
import threading

CONG = 5020


class CauArtisan(threading.Thread):
    def __init__(self, lay_regs, cong=CONG, host="127.0.0.1"):
        super().__init__(daemon=True)
        self.lay_regs, self.cong, self.host = lay_regs, cong, host
        self.so_yeu_cau = 0

    def run(self):
        sv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sv.bind((self.host, self.cong))
        sv.listen(4)
        while True:
            c, _ = sv.accept()
            threading.Thread(target=self._phuc_vu, args=(c,), daemon=True).start()

    def _phuc_vu(self, c):
        try:
            while True:
                h = self._doc_du(c, 7)
                if not h:
                    return
                tid, pid, ln, uid = struct.unpack(">HHHB", h)
                pdu = self._doc_du(c, ln - 1)
                if not pdu:
                    return
                fc = pdu[0]
                if fc in (3, 4) and len(pdu) >= 5:
                    dau, so = struct.unpack(">HH", pdu[1:5])
                    regs = list(self.lay_regs() or [])
                    if not regs or dau + so > max(len(regs), 20) or so > 125:
                        tra = bytes([fc | 0x80, 2])
                    else:
                        regs = (regs + [0] * 20)[:max(len(regs), 20)]
                        val = [int(v) & 0xFFFF for v in regs[dau:dau + so]]
                        tra = bytes([fc, 2 * so]) + struct.pack(">%dH" % so, *val)
                    self.so_yeu_cau += 1
                else:
                    tra = bytes([fc | 0x80, 1])            # chỉ đọc: không cho Artisan ghi
                c.sendall(struct.pack(">HHHB", tid, pid, len(tra) + 1, uid) + tra)
        except OSError:
            return
        finally:
            c.close()

    @staticmethod
    def _doc_du(c, n):
        b = b""
        while len(b) < n:
            x = c.recv(n - len(b))
            if not x:
                return None
            b += x
        return b
