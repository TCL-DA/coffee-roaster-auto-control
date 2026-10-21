"""Self-test otl_link bằng serial giả mô phỏng đúng PC_Link.h (không cần máy)."""
import os, sys, time
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"f:\Project\100_OTL_06ALS - CMS - Cacao\tools")
import otl_link as L


class FakeSerial:
    """Slave Modbus RTU tối giản: 0x03 + 0x10 trên bản đồ PC_Link."""
    def __init__(self, regs, slave=1):
        self.regs = dict(regs); self.slave = slave; self.out = b""; self.log = []
    def reset_input_buffer(self): pass
    def close(self): pass
    def write(self, frame):
        sid, fn = frame[0], frame[1]
        if sid != self.slave: self.out = b""; return
        if fn == 0x03:
            addr = (frame[2] << 8) | frame[3]; n = (frame[4] << 8) | frame[5]
            if any((addr + i) not in self.regs for i in range(n)):
                body = bytes((sid, 0x83, 0x02)); self.out = body + L.crc16(body); return
            body = bytearray((sid, 0x03, 2 * n))
            for i in range(n):
                v = self.regs[addr + i] & 0xFFFF
                body += bytes((v >> 8, v & 0xFF))
            self.out = bytes(body) + L.crc16(bytes(body))
        elif fn == 0x10:
            addr = (frame[2] << 8) | frame[3]; n = (frame[4] << 8) | frame[5]
            for i in range(n):
                self.regs[addr + i] = (frame[7 + 2*i] << 8) | frame[8 + 2*i]
            self.log.append((addr, [self.regs[addr + i] for i in range(n)]))
            body = frame[:6]; self.out = body + L.crc16(body)
    def read(self, n):
        out, self.out = self.out[:n], self.out[n:]
        return out


def make_regs():
    r = {}
    # flags 0x43 = AUTO|GAS|PCCTRL (không có CHARGE) — xem FLAG_BITS
    vals = [2153, 2310, 1234, -560, 1100, 35, 18, 60, 2200, -120, 7, 642, 0x07, 0x43, 1]
    for i, v in enumerate(vals):
        r[L.R_BASE + i] = v & 0xFFFF
    for i in range(len(vals), L.R_COUNT):
        r[L.R_BASE + i] = 0        # ô mới (prof_*/scale/…) — bản đồ nới thì test tự nới
    for i in range(L.W_COUNT):
        r[L.W_BASE + i] = 0
    return r


def main():
    fails = []
    def chk(name, cond, got=""):
        print(("  OK   " if cond else "  FAIL ") + name + (f"  → {got}" if got else ""))
        if not cond: fails.append(name)

    # 1) CRC theo ví dụ chuẩn Modbus: 01 03 00 00 00 0A → CRC C5 CD
    print("1) CRC16")
    got = L.crc16(bytes.fromhex("0103000000 0A".replace(" ", "")))
    chk("khung chuẩn 01 03 00 00 00 0A", got == bytes((0xC5, 0xCD)), got.hex())

    print("2) decode")
    link = L.RoasterLink({"port": "FAKE", "baud": 9600, "slave": 1, "enabled": True})
    link._ser = FakeSerial(make_regs())
    d = link._decode(link.read_regs(L.R_BASE, L.R_COUNT))
    chk("BT ×10", d["bt"] == 215.3, d["bt"])
    chk("ET ×10", d["et"] == 231.0, d["et"])
    chk("RoR ×100", d["ror_bt"] == 12.34, d["ror_bt"])
    chk("RoR âm", d["ror_et"] == -5.6, d["ror_et"])
    chk("vac âm (Pa)", d["vac"] == -120, d["vac"])
    chk("SV ×10", d["sv"] == 220.0, d["sv"])
    chk("phase 3 bit", d["phase"] == {"dry": True, "mai": True, "dev": True}, d["phase"])
    chk("flags auto+gas+pc", d["flags"]["auto"] and d["flags"]["gas"] and d["flags"]["pc_control"]
        and not d["flags"]["charge"], d["flags"])

    print("3) khung ngoại lệ (reg không tồn tại)")
    try:
        link.read_regs(500, 2); chk("bắt được lỗi code 2", False)
    except L.ModbusError as e:
        chk("bắt được lỗi code 2", "code 2" in str(e), str(e))

    print("4) ghi + kẹp giá trị")
    chk("kẹp gas >100", link.write("gas", 250)["value"] == 100)
    chk("kẹp vac <90", link.write("vac", 10)["value"] == 90)
    chk("lệnh lạ bị chặn", link.write("nuke", 1)["ok"] is False)
    for addr, vals in link._pending:
        link.write_regs(addr, vals)
    chk("ghi tới đúng reg gas (W_BASE)",
        link._ser.log[0] == (L.W_BASE + L.W_INDEX["gas"], [100]), link._ser.log)

    print("5) vòng poll + heartbeat")
    link2 = L.RoasterLink({"port": "FAKE", "baud": 9600, "slave": 1, "enabled": True, "poll_hz": 20})
    fake = FakeSerial(make_regs())
    link2._open = lambda: (setattr(link2, "_ser", fake) or True)
    link2.start(); time.sleep(0.3)
    s = link2.snapshot()
    chk("state connected", s["state"] == "connected", s["state"])
    chk("có data", s["data"]["bt"] == 215.3)
    fake.regs[L.R_BASE + 14] = 1          # hb đứng yên
    time.sleep(3.4)
    chk("phát hiện hb đứng yên", link2.snapshot()["state"] == "stalled", link2.snapshot()["state"])
    link2.stop()

    print("6) đơn vị kỹ thuật theo bản đồ chung")
    chk("SV nhận °C, tự ×10", link.write("sv", 215.3)["value"] == 2153, link.write("sv", 215.3))
    chk("gas không nhân hệ số", link.write("gas", 42)["value"] == 42)

    print("7) chế độ tương thích: đọc + gửi lệnh đúng ô của khối cũ")
    art = {i: 0 for i in range(0, 27)}
    art[0], art[1], art[3], art[4], art[9], art[19] = 2153, 2310, 35, 82, 0xFF88, 2200
    lk = L.RoasterLink({"port": "FAKE", "baud": 9600, "slave": 1, "enabled": True})
    lk._ser = FakeSerial(art)
    chk("dò ra chế độ tương thích", lk._probe() == L.MODE_COMPAT, lk._probe())
    lk._mode = L.MODE_COMPAT
    s2 = lk._poll_compat()
    chk("BT/ET đúng", (s2["bt"], s2["et"]) == (215.3, 231.0), (s2["bt"], s2["et"]))
    chk("áp hút âm", s2["vac"] == -120, s2["vac"])
    chk("có nói rõ số nào app tính", "ror_bt" in s2["derived"])

    lk._ser.log.clear()
    r = lk.write("charge")
    chk("charge → reg 14, kiểu latch", (r["reg"], r["kind"]) == (14, "latch"), r)
    for addr, vals in lk._pending:
        lk.write_regs(addr, vals)
    # KHÔNG được ghi 0 theo sau: firmware tự đóng xi lanh, ghi 0 sớm là huỷ timer
    chk("chỉ ghi 1, KHÔNG ghi 0 theo sau", lk._ser.log == [(14, [1])], lk._ser.log)
    lk._pending.clear(); lk._ser.log.clear()
    r = lk.write("gas", 40)
    chk("gas → reg 11, giữ mức", (r["reg"], r["kind"], r["value"]) == (11, "level", 40), r)
    chk("một lệnh = đúng một lần ghi", len(lk._pending) == 1, lk._pending)
    lk._pending.clear()
    chk("đánh lửa tắt được (ghi 0)", lk.write("ignite", 0)["value"] == 0, lk._pending)

    print("8) bản đồ 3 phía còn đồng bộ")
    import subprocess
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    r = subprocess.run([sys.executable, os.path.join(root, "protocol", "gen_pc_link.py"), "--check"],
                       capture_output=True, text=True, encoding="utf-8", cwd=root)
    chk("firmware + tool + giao diện khớp pc_link.json", r.returncode == 0,
        (r.stdout or "").strip().replace("\n", " | "))

    print("9) nhịp tim có điều kiện — tác nhân tự động im thì NGỪNG nhấp")
    # Đây là cái van thật của cả tầng lái T2: firmware chỉ biết "app còn sống".
    # Nếu app cứ nhấp vô điều kiện thì AI treo mà gas vẫn cháy ở mức lệnh cuối.
    HB = L.W_BASE + L.W_INDEX["hb"]
    lk3 = L.RoasterLink({"port": "FAKE", "baud": 9600, "slave": 1, "enabled": True,
                         "poll_hz": 20})
    fk = FakeSerial(make_regs())
    lk3._open = lambda: (setattr(lk3, "_ser", fk) or True)

    def dem_hb():
        return len([x for x in fk.log if x[0] == HB])

    lk3.start(); time.sleep(0.4)
    n0 = dem_hb(); time.sleep(0.3); n1 = dem_hb()
    chk("thợ lái tay: vẫn nhấp nhịp như cũ", n1 > n0, f"{n0}→{n1}")

    lk3.agent_open(60, stale=1.0)          # tác nhân tự động vào cầm lái
    time.sleep(0.15)                       # chờ vòng poll rút lệnh khỏi hàng đợi
    chk("khai agent=1 xuống máy", any(a == L.W_BASE + L.W_INDEX["agent"] and v == [1]
                                      for a, v in fk.log), fk.log[-3:])
    n2 = dem_hb(); time.sleep(0.3); lk3.agent_beat(); time.sleep(0.3); n3 = dem_hb()
    chk("tác nhân còn tươi: vẫn nhấp", n3 > n2, f"{n2}→{n3}")

    time.sleep(1.3)                        # im quá stale=1.0s
    n4 = dem_hb(); time.sleep(0.4); n5 = dem_hb()
    chk("tác nhân im → NGỪNG nhấp (firmware sẽ trả quyền)", n5 == n4, f"{n4}→{n5}")
    chk("nói rõ vì sao ngừng", "im quá" in lk3.agent_state()["ly_do"],
        lk3.agent_state()["ly_do"])

    lk3.agent_beat()                       # tác nhân sống lại
    time.sleep(0.3)
    chk("tác nhân lên tiếng lại → nhấp tiếp", dem_hb() > n5, dem_hb())

    # Firmware nhả quyền (pc_control tắt) → dọn lượt lái, app về nếp cũ
    lk3.agent_open(60, stale=0.3)
    time.sleep(0.6)                        # để nó rơi vào trạng thái ngừng nhấp
    fk.regs[L.R_BASE + 13] = 0x03          # bỏ bit PCCTRL — máy đã về HMI
    time.sleep(0.5)
    chk("máy về HMI → xoá lượt lái", lk3.agent_state()["dang_lai"] is False,
        lk3.agent_state())
    n6 = dem_hb(); time.sleep(0.3)
    chk("và nhấp lại bình thường cho lần sau", dem_hb() > n6, dem_hb())

    # Hết hạn lượt lái cũng ngừng nhấp, dù tác nhân vẫn nói
    fk.regs[L.R_BASE + 13] = 0x43
    time.sleep(0.3)
    lk3.agent_open(1, stale=30)            # hạn 1 giây, nhịp thoải mái
    time.sleep(1.4)
    lk3.agent_beat()                       # vẫn còn sống, nhưng HẾT HẠN
    n7 = dem_hb(); time.sleep(0.4)
    chk("hết hạn lượt lái → ngừng nhấp dù tác nhân còn nói", dem_hb() == n7,
        lk3.agent_state()["ly_do"])
    lk3.agent_close("xong")
    lk3.stop()

    # N) Lùi số ô đọc khi gặp firmware cũ — LÙI TỪNG NẤC, không rơi thẳng về gốc.
    #    Rơi thẳng là app mất cân/profile/RoR hồ sơ trên máy VỐN CÓ những ô đó.
    print("")
    print("N) Firmware cu it o hon -> lui tung nac")

    class LinkCut(L.RoasterLink):
        """Máy giả chỉ có `co` ô đọc: xin nhiều hơn là ném ModbusError."""
        def __init__(self, co):
            self.co = co
            self.doc = []
            self._r_count = L.R_COUNT

        def read_regs(self, addr, count):
            self.doc.append(count)
            if count > self.co:
                raise L.ModbusError("exception 02 - dia chi khong co")
            return [0] * count

    def doc_lui(lk):
        for _ in range(5):                   # mỗi vòng lùi đúng 1 nấc
            try:
                return L.RoasterLink._read_pclink(lk)
            except L.ModbusError:
                continue
        return None

    lk4 = LinkCut(22)                        # firmware 22 ô đang chạy ngoài xưởng
    s4 = doc_lui(lk4)
    chk("22 o: lui dung 1 nac roi doc duoc", lk4.doc == [L.R_COUNT, 22], lk4.doc)
    chk("o may chua co tra None, khong phai 0",
        s4 is not None and s4.get("vac_en") is None and s4.get("scale_tg") is not None,
        (s4 or {}).get("vac_en"))

    lk5 = LinkCut(16)                        # máy đời đầu, chỉ có khối gốc
    s5 = doc_lui(lk5)
    chk("16 o: lui qua 22 roi moi toi 16", lk5.doc == [L.R_COUNT, 22, 16], lk5.doc)
    chk("khoi goc: can van bao None", s5 is not None and s5.get("scale") is None,
        (s5 or {}).get("scale"))

    print("\n" + ("TẤT CẢ ĐẠT" if not fails else f"{len(fails)} MỤC HỎNG: {fails}"))
    return 1 if fails else 0


sys.exit(main())
