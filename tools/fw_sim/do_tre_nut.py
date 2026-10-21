# -*- coding: utf-8 -*-
"""Đo độ trễ NÚT LỆNH HMI -> RELAY trên board ảo (firmware thật chạy trên PC + HMIApp), để so trước / sau khi sửa.

Chủ máy 10/10/2026: "bật tắt burner, charge, drop, escape… bấm vô có 1 sự delay nhẹ rồi relay mới bật — fix cho nhạy nhất có
thể, và không lỗi". Bài này ghi word nút lên HMIApp (như ngón tay bấm) rồi hỏi board ảo liên tục tới khi chân relay đổi.

    python tools/fw_sim/do_tre_nut.py <build HMIApp> [<board ảo .exe>] [<số lần mỗi nút>]

  · build   : thư mục bản biên dịch của bộ mô phỏng (vd F:/Project/112_Quanly/mcp-dpa/emu/builds/T-R0-1010-LO50)
  · exe     : mặc định tools/fw_sim/out/otl_fw_sim.exe; đưa otl_fw_sim_truoc.exe để đo bản TRƯỚC khi sửa
Lưu ý: board ảo mô phỏng một giao dịch HMI = 2 ms, thiết bị RS485 = 4 ms — vòng quét ảo NHANH hơn board thật (~140 ms),
nên số tuyệt đối trên máy thật lớn hơn; cái so được là TỈ LỆ trước / sau trong cùng một môi trường."""
import json
import os
import random
import statistics
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = sys.argv[1]
EXE = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else os.path.join(HERE, 'out', 'otl_fw_sim.exe')
LAN = int(sys.argv[3]) if len(sys.argv) > 3 else 12
os.environ['OTL_FW_EXE'] = EXE                      # phải đặt TRƯỚC khi nạp run_system (đọc lúc import)
sys.path.insert(0, 'F:/Project/112_Quanly/mcp-dpa')
import t_emu as E  # noqa: E402

#        tên        word nút   khoá relay trong status của board ảo
NUT = (('cooling', 'W40005', 'cool'),
       ('charge', 'W40007', 'charge'),
       ('escape', 'W40009', 'escape'),
       ('afterburner', 'W40012', 'ab'))
HET_GIO = 3.0


class Ong:
    """Một kết nối GIỮ MỞ tới pipe điều khiển của board ảo. Máy chủ pipe (sim_core.cpp ctl_thread) phục vụ từng kết nối một và
    tạo lại pipe sau mỗi lần ngắt — mở / đóng liên tục (như t_emu.fw_cmd) sẽ rơi vào khe chưa có pipe và báo 'board ảo chưa
    chạy'. Giữ mở thì mỗi lượt hỏi chỉ là một cặp ghi / đọc (< 1 ms)."""
    def __init__(self):
        import ctypes
        from ctypes import wintypes as wt
        self.ct, self.wt = ctypes, wt
        self.k32 = ctypes.WinDLL('kernel32', use_last_error=True)
        self.k32.CreateFileW.restype = wt.HANDLE
        self.h = None

    def mo(self, cho_s=60):
        t0 = time.time()
        while time.time() - t0 < cho_s:
            h = self.k32.CreateFileW(r'\\.\pipe\otl_fw_sim', 0xC0000000, 0, None, 3, 0, None)
            if h and h != self.wt.HANDLE(-1).value:
                mode = self.wt.DWORD(2)
                self.k32.SetNamedPipeHandleState(h, self.ct.byref(mode), None, None)
                self.h = h
                return self
            time.sleep(0.2)
        raise RuntimeError('không mở được pipe board ảo sau %d s' % cho_s)

    def hoi(self, lenh='status'):
        n = self.wt.DWORD()
        b = lenh.encode()
        buf = self.ct.create_string_buffer(4096)
        if not self.k32.WriteFile(self.h, b, len(b), self.ct.byref(n), None) or \
                not self.k32.ReadFile(self.h, buf, 4096, self.ct.byref(n), None):
            self.dong()
            self.mo(10)
            return self.hoi(lenh)
        return json.loads(buf.raw[:n.value].decode('utf-8', 'replace'))

    def dong(self):
        if self.h:
            self.k32.CloseHandle(self.h)
            self.h = None


ONG = Ong()


def rl(khoa):
    return ONG.hoi()['rl'][khoa]


def do(word, khoa, gia_tri):
    """Ghi nút = gia_tri, trả ms tới khi relay = gia_tri (None nếu quá HET_GIO)."""
    E.emu_write(word, [gia_tri])
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < HET_GIO:
        if rl(khoa) == gia_tri:
            return (time.perf_counter() - t0) * 1000.0
    return None


def cho(ham, giay):
    t0 = time.time()
    while time.time() - t0 < giay:
        if ham():
            return round(time.time() - t0, 1)
        time.sleep(0.1)
    return None


def chuc_nang():
    """Thử hồi quy ngắn sau khi đo: (a) nút gas bật / tắt relay gas; (b) Xả tay: relay bật / tắt; (c) TRONG MẺ (Start, nhiệt
    nạp = 0 để vào thẳng bước chờ nạp): bấm Nạp -> relay bật, rồi BOARD tự đóng sau thời gian mở cửa nạp ($M1) — board ghi 0
    lên HMI rồi đọc lại, tức đường 'board ghi, đọc lại' và bộ đếm giờ của chuỗi rang phải còn nguyên. (Ngoài mẻ thì cửa nạp
    không tự đóng — chargeTimerEn chỉ bật trong STP_CHARGE.)"""
    kq = {}
    E.emu_write('W40002', [1])
    kq['gas_bat_s'] = cho(lambda: rl('gas') == 1, 3)
    E.emu_write('W40002', [0])
    kq['gas_tat_s'] = cho(lambda: rl('gas') == 0, 3)
    E.emu_write('W40008', [1])
    kq['xa_bat_s'] = cho(lambda: rl('drop') == 1, 3)
    E.emu_write('W40008', [0])
    kq['xa_tat_s'] = cho(lambda: rl('drop') == 0, 3)
    for w in ('W40005', 'W40009', 'W40012'):               # dọn: làm nguội / xả khay / đốt khói có thể đã tự bật sau khi xả
        E.emu_write(w, [0])
    time.sleep(2)
    m1 = E.emu_read('$M1', 1)['values'][0]
    kq['M1_s'] = m1
    E.emu_write('$M23', [0])                               # nhiệt nạp 0 = không chờ nhiệt, Start đi thẳng tới chờ bấm Nạp
    time.sleep(2)
    E.emu_write('W40001', [1])                             # Start mẻ
    time.sleep(8)
    E.emu_write('W40007', [1])                             # bấm Nạp
    kq['nap_bat_s'] = cho(lambda: rl('charge') == 1, 3)
    kq['nap_tu_dong_sau_s'] = cho(lambda: rl('charge') == 0 and E.emu_read('W40007', 1)['values'][0] == 0, m1 + 10)
    E.emu_write('W40001', [0])                             # dừng mẻ
    time.sleep(3)
    E.emu_write('W40002', [0])
    kq['gas_tat_sau_dung'] = cho(lambda: rl('gas') == 0, 5) is not None
    kq['dat'] = all(kq[k] is not None for k in ('gas_bat_s', 'gas_tat_s', 'xa_bat_s', 'xa_tat_s', 'nap_bat_s', 'nap_tu_dong_sau_s')) \
        and kq['nap_tu_dong_sau_s'] >= m1 - 3 and kq['gas_tat_sau_dung']
    return kq


def main():
    print('board ảo: %s' % os.path.basename(EXE), flush=True)
    E.emu_start(build=BUILD, firmware=True, state='_do_tre_nut', fresh_state=True, m_profile=True)
    try:
        ONG.mo(90)                                  # chờ board ảo khởi động xong
        t0 = time.time()
        while time.time() - t0 < 90 and not ONG.hoi().get('hmi_ok'):      # … và bắt tay được HMI
            time.sleep(1.0)
        time.sleep(12)                              # qua đoạn quét hồ sơ / ghi khởi động
        # ước lượng chu kỳ vòng quét: không đo trực tiếp được, chỉ in t_ms để biết board còn chạy
        kq, hong = {}, 0
        for ten, word, khoa in NUT:
            E.emu_write(word, [0])
        time.sleep(1.0)
        for ten, word, khoa in NUT:
            bat, tat = [], []
            for _ in range(LAN):
                time.sleep(random.uniform(0.25, 0.55))          # pha ngẫu nhiên so với vòng quét
                a = do(word, khoa, 1)
                time.sleep(random.uniform(0.25, 0.55))
                b = do(word, khoa, 0)
                if a is None or b is None:
                    hong += 1
                    continue
                bat.append(a)
                tat.append(b)
            kq[ten] = {'bat': bat, 'tat': tat}
            tat_ca = bat + tat
            if tat_ca:
                print('%-12s BẬT tb %5.0f ms · TẮT tb %5.0f ms · lớn nhất %5.0f ms  (%d lần)'
                      % (ten, statistics.mean(bat), statistics.mean(tat), max(tat_ca), len(bat)), flush=True)
        moi = [v for d in kq.values() for v in d['bat'] + d['tat']]
        moi.sort()
        tom = {'exe': os.path.basename(EXE), 'so_lan': len(moi), 'hong': hong,
               'tb_ms': round(statistics.mean(moi), 1), 'trung_vi_ms': round(statistics.median(moi), 1),
               'p95_ms': round(moi[int(len(moi) * 0.95) - 1], 1), 'max_ms': round(moi[-1], 1)}
        print('TOM TAT %s' % json.dumps(tom, ensure_ascii=False), flush=True)
        tom['chuc_nang'] = chuc_nang()
        print('CHUC NANG %s' % json.dumps(tom['chuc_nang'], ensure_ascii=False), flush=True)
        ra = os.path.join(HERE, 'log', 'do_tre_nut_%s.json' % os.path.splitext(os.path.basename(EXE))[0])
        json.dump({'tom_tat': tom, 'chi_tiet': kq}, open(ra, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    finally:
        ONG.dong()
        try:
            E.emu_stop()
        except Exception:  # noqa: BLE001
            pass


if __name__ == '__main__':
    main()
