# -*- coding: utf-8 -*-
"""Kiểm LUẬT LÁI T2 ở tầng app — không cần máy rang, không cần app đang chạy.

Đây là tầng giữ luật (§4 kế hoạch): MCP server chỉ là bộ chuyển ngữ, nên luật
phải được kiểm ở đây. Dùng Api rỗng (bỏ qua __init__ vốn mở DB/auth/serial) và
một cầu Modbus GIẢ, để soi đúng phần quyết định cho hay không cho.

Chạy: python tools/test_lease_t2.py
"""
import io
import os
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import roast_lab_hmi as H                              # noqa: E402

FAIL = []


def ok(ten, dieu_kien, chi_tiet=""):
    print(("  ĐẠT  " if dieu_kien else "  SAI  ") + ten
          + ("  → " + str(chi_tiet)[:90] if chi_tiet else ""))
    if not dieu_kien:
        FAIL.append(ten)


class LinkGia:
    """Cầu Modbus giả — đủ để Api hỏi trạng thái và xếp lệnh."""

    def __init__(self, pc_control=True, state="connected", gas=30):
        self.pc_control = pc_control
        self.state = state
        self.gas = gas
        self.lenh = []
        self.nhip = []                # các lần Api nhấp nhịp xuống tầng link
        self.mo_lai = []              # các lần Api gọi agent_open, kèm số giây
        self.ag = {"dang_lai": False, "con_lai_s": 0, "im_lang_s": None,
                   "nhip_toi_da_s": 20, "ngung_nhip": False, "ly_do": ""}

    def snapshot(self):
        return {"state": self.state, "err": "", "data": {
            "gas": self.gas, "air": 20, "drum": 60, "sv": 210.0, "vac": -120,
            "flags": {"pc_control": self.pc_control, "flame": True}}}

    def agent_state(self):
        return dict(self.ag)

    def agent_open(self, giay, stale=20.0):
        self.mo_lai.append(int(giay))
        self.ag.update(dang_lai=True, con_lai_s=int(giay), im_lang_s=0.0,
                       nhip_toi_da_s=stale)
        return self.agent_state()

    def agent_beat(self):
        self.ag["im_lang_s"] = 0.0
        self.nhip.append(time.time())     # đếm số nhịp thật sự xuống tầng link

    def agent_close(self, why=""):
        self.ag.update(dang_lai=False, ly_do=why)
        return self.agent_state()

    def write(self, name, value=1):
        self.lenh.append((name, value))
        if name == "gas":
            self.gas = value
        return {"ok": True, "name": name, "value": value, "reg": 0, "kind": "level"}


def api_gia(link):
    a = H.Api.__new__(H.Api)          # bỏ qua __init__: không mở DB/auth/serial
    a._link = link
    a._lease = None
    a._audit = None
    return a


AI = {"kind": "may", "scopes": ["read", "control"], "name": "ai-thu", "id": "k1"}
AI2 = {"kind": "may", "scopes": ["read", "control"], "name": "ai-khac", "id": "k2"}
THO = {"kind": "nguoi", "scopes": ["read", "config", "control"], "name": "web"}


def main():
    print("1) Thợ lái tay — KHÔNG dính luật nào")
    lk = LinkGia()
    a = api_gia(lk)
    ok("ctx=None ghi thẳng", a.link_write("gas", 55).get("ok") is True)
    ok("token web ghi thẳng", a.link_write("gas", 60, THO).get("ok") is True)
    ok("không cần lượt lái", a.lease_state()["dang_lai"] is False)

    print("\n2) Tác nhân tự động CHƯA xin quyền")
    lk = LinkGia(); a = api_gia(lk)
    r = a.link_write("gas", 50, AI)
    ok("bị từ chối", r.get("ok") is False, r.get("err"))
    ok("nói rõ phải xin lượt lái", "lượt lái" in r.get("msg", ""), r.get("msg"))
    ok("KHÔNG có lệnh nào xuống máy", lk.lenh == [], lk.lenh)

    print("\n3) PC control trên HMI đang TẮT → không xin được quyền")
    lk = LinkGia(pc_control=False); a = api_gia(lk)
    r = a.lease_open(AI, 5)
    ok("bị từ chối", r.get("ok") is False, r.get("err"))
    ok("nói rõ do PC control", "PC control" in r.get("msg", ""), r.get("msg"))

    print("\n4) Chưa nối được máy → không xin được quyền")
    lk = LinkGia(state="error"); a = api_gia(lk)
    r = a.lease_open(AI, 5)
    ok("bị từ chối", r.get("ok") is False, r.get("err"))

    print("\n5) Xin quyền hợp lệ rồi lái")
    lk = LinkGia(gas=30); a = api_gia(lk)
    r = a.lease_open(AI, 5)
    ok("mở được lượt lái", r.get("ok") is True, r.get("con_lai_s"))
    # (việc khai agent=1 xuống firmware do tầng link làm — xem test_otl_link mục 9)
    ok("bảo tầng link mở đúng số giây", lk.mo_lai == [300], lk.mo_lai)
    ok("trần 15 phút dù xin nhiều hơn", a.lease_open(AI, 999)["con_lai_s"] <= 900)
    ok("nói rõ luật cho AI biết", r["luat"]["buoc_nhay_toi_da"]["gas"] == 25, r["luat"])

    r = a.link_write("gas", 50, AI)         # 30 → 50, trong tầm 25
    ok("gas 30→50 được", r.get("ok") is True, r)
    ok("lệnh xuống máy thật", ("gas", 50) in lk.lenh)

    print("\n6) Bước nhảy quá lớn bị chặn")
    r = a.link_write("gas", 100, AI)        # 50 → 100, quá 25
    ok("gas 50→100 bị chặn", r.get("ok") is False, r.get("err"))
    ok("nói rõ nên chia nhỏ", "Chia nhỏ" in r.get("msg", ""), r.get("msg"))
    ok("bước nhỏ thì cho đi", a.link_write("gas", 70, AI).get("ok") is True)

    print("\n7) Dây chuyền an toàn — AI không tự khai mình còn sống")
    for ten in ("hb", "agent"):
        r = a.link_write(ten, 1, AI)
        ok("chặn ghi %s" % ten, r.get("ok") is False, r.get("msg"))

    print("\n8) Một lúc chỉ MỘT tác nhân cầm lái")
    r = a.lease_open(AI2, 5)
    ok("tác nhân thứ hai bị chặn", r.get("ok") is False, r.get("msg"))
    r = a.link_write("gas", 60, AI2)
    ok("tác nhân thứ hai không ghi được", r.get("ok") is False, r.get("err"))
    r = a.lease_close(AI2)
    ok("và không đóng được lượt của người khác", r.get("ok") is False, r.get("err"))

    print("\n9) Hãm tần suất")
    lk = LinkGia(); a = api_gia(lk); a.lease_open(AI, 5)
    a._lease["dem"] = H.LEASE_RATE_N        # đã đủ trần trong phút này
    r = a.link_write("air", 25, AI)
    ok("quá %d lệnh/phút → chặn" % H.LEASE_RATE_N, r.get("ok") is False, r.get("err"))
    a._lease["moc"] = time.time() - 61       # sang phút mới
    ok("qua phút mới thì ghi lại được", a.link_write("air", 25, AI).get("ok") is True)

    print("\n10) Thợ cắt quyền bất cứ lúc nào")
    lk = LinkGia(); a = api_gia(lk); a.lease_open(AI, 5)
    ok("thợ đóng được lượt lái của AI", a.lease_close(THO, "thợ cắt")["ok"] is True)
    ok("máy hết bị lái", a.lease_state()["dang_lai"] is False)
    r = a.link_write("gas", 40, AI)
    ok("AI mất quyền ghi ngay", r.get("ok") is False, r.get("err"))

    print("\n11) Thợ tắt PC control giữa chừng → lượt lái tự huỷ")
    lk = LinkGia(); a = api_gia(lk); a.lease_open(AI, 5)
    lk.pc_control = False
    r = a.link_write("gas", 40, AI)
    ok("lệnh bị chặn", r.get("ok") is False, r.get("err"))
    ok("và lượt lái bị huỷ luôn", a.lease_state()["dang_lai"] is False)

    print("\n12) Tầng dưới cắt (im lặng/hết hạn) → app dọn theo")
    lk = LinkGia(); a = api_gia(lk); a.lease_open(AI, 5)
    lk.ag.update(dang_lai=False, ly_do="tác nhân tự động im quá 20 giây")
    ok("app thấy lượt lái đã rụng", a.lease_state()["dang_lai"] is False)
    ok("ghi tiếp thì bị chặn", a.link_write("gas", 40, AI).get("ok") is False)

    print("")
    print("13) Tran TONG cua phien PC control — gia han khong vo han")
    lk = LinkGia(); a = api_gia(lk)
    ok("lượt đầu mở được", a.lease_open(AI, 15).get("ok") is True)
    # Gia hạn ngay lập tức vẫn phải được — mới lái vài phút.
    ok("gia hạn sớm thì cho", a.lease_open(AI, 15).get("ok") is True)
    # Đẩy lùi mốc phiên ra quá trần: coi như đã lái hết giờ.
    a._lease_phien_t0 = time.time() - H.LEASE_PHIEN_MAX_S - 1
    r = a.lease_open(AI, 15)
    ok("hết trần phiên thì từ chối", r.get("ok") is False, r.get("err"))
    ok("bảo thợ tắt bật lại PC control", "PC control" in r.get("msg", ""), r.get("msg"))
    # Mất kết nối thoáng qua KHÔNG được tính là "thợ đã tắt PC control" — nếu
    # tính thì chỉ cần rớt cáp một nhịp là tác nhân có thêm một phiên 60 phút.
    lk.state = "mat_ket_noi"
    a.lease_state()
    lk.state = "connected"
    ok("rớt cáp KHÔNG làm mới phiên", a.lease_open(AI, 15).get("err") == "het_phien")
    # Thợ tắt PC control = phiên mới. lease_state() là chỗ nhận ra điều đó.
    lk.pc_control = False
    a.lease_state()
    lk.pc_control = True
    ok("thợ tắt/bật PC control → lái lại được", a.lease_open(AI, 15).get("ok") is True)

    print("")
    print("14) Nhip tim CHI tinh hanh dong lai, khong tinh doc telemetry")
    ok("đường đọc không nằm trong bảng nhịp",
       "/api/snapshot" not in H.NHIP_POST and "/api/state" not in H.NHIP_POST)
    ok("đường ghi lệnh máy thì có", "/api/write" in H.NHIP_POST)
    ok("và nhịp tường minh cũng có", "/api/lease_beat" in H.NHIP_POST)
    lk = LinkGia(); a = api_gia(lk); a.lease_open(AI, 5)
    n = len(lk.nhip) if hasattr(lk, "nhip") else None
    a.lease_touch("k1")
    ok("lease_touch đúng khoá thì nhấp xuống tầng link",
       n is None or len(lk.nhip) == n + 1)
    a.lease_touch("khoa-la")
    ok("khoá khác thì KHÔNG nhấp hộ",
       n is None or len(lk.nhip) == n + 1)

    print("\n" + ("TẤT CẢ ĐẠT" if not FAIL
                  else "CÓ %d PHÉP SAI: %s" % (len(FAIL), ", ".join(FAIL))))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
