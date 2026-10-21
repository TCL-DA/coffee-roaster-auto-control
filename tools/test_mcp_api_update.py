# -*- coding: utf-8 -*-
"""Kiểm đợt đồng bộ MCP/API 08/09/2026 — lọc dưới kho, số tổng thật, OpenAPI đúng.

Chỉ dùng kho SQLite TẠM và cầu web giả trên cổng 0. Không mở serial, không chạm
app thật ở cổng 8555, không tạo khoá API nào.

Ba thứ đợt này phải chứng minh:
  1. Bộ lọc lịch sử chạy DƯỚI KHO rồi mới phân trang — không cắt trên trang.
  2. `tong` là tổng thật của bộ lọc, KHÔNG phải số dòng của trang đang xem;
     và "đếm được mà rỗng" khác hẳn "chưa đếm được".
  3. OpenAPI mô tả đúng những đường MCP thật sự gọi, tên tham số khớp handler.
"""
import ast
import json
import os
import subprocess
import sys
import tempfile
import unittest
import urllib.parse
import urllib.request
from unittest.mock import Mock

import roast_lab_hmi as H
from roast_db import RoastDb

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MCP_SERVER = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "mcp_roaster", "server.py")


def _nap_openapi():
    """Sinh OpenAPI trong bộ nhớ từ pc_link.json — KHÔNG đọc artefact đã commit,
    vì phải kiểm cái generator sinh ra chứ không phải bản cũ còn nằm trên đĩa."""
    thu_muc = os.path.join(GOC, "protocol")
    if thu_muc not in sys.path:
        sys.path.append(thu_muc)
    from gen_openapi import gen_openapi
    with open(os.path.join(thu_muc, "pc_link.json"), encoding="utf-8") as f:
        return json.loads(gen_openapi(json.load(f)))


def _danh_sach_duong_mcp():
    """Đọc CHO_PHEP / CHO_PHEP_GHI bằng ast thay vì import server.py.

    Nạp server.py sẽ bọc lại sys.stdin/stdout/stderr của CHÍNH tiến trình kiểm
    thử; bộ bọc đó khi bị thu hồi còn đóng luôn stdout thật, và runner mất chỗ
    in kết quả. Đọc tĩnh thì không đụng gì."""
    with open(MCP_SERVER, encoding="utf-8") as f:
        cay = ast.parse(f.read())
    ra = {}
    for node in cay.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            ten = node.targets[0].id
            if ten in ("CHO_PHEP", "CHO_PHEP_GHI"):
                ra[ten] = list(ast.literal_eval(node.value))
    return ra["CHO_PHEP"], ra["CHO_PHEP_GHI"]


class CauGia(unittest.TestCase):
    """Cầu web thật của app, gắn vào kho SQLite tạm."""

    SO_ME = 125

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = RoastDb(self.tmp.name)
        for i in range(self.SO_ME):
            bid = self.db.begin({"name": "Cà phê ĐẬM" if i % 2 else "Nhạt",
                                 "roaster": "Trường"})
            self.db.finish(bid, {"code": "#B-%04d" % i, "drop_sec": 600})
            self.db._con.execute("UPDATE batches SET started_at=? WHERE id=?",
                                 ("2026-09-06 10:00:00" if i < 100 else "2026-09-07 10:00:00", bid))
        self.db._con.commit()

        self.api = H.Api.__new__(H.Api)
        self.api._db = self.db
        self.api.web_cfg = {"bat": True, "cong": 0}
        self.api.web_tokens = {}
        self.api.lease_touch = Mock()
        self.api._apikeys = Mock()
        self.api._apikeys.verify.side_effect = lambda key: (
            {"id": key, "name": key, "scopes": ["read"]} if key == "read" else None)
        H.start_webserver(self.api)
        self.base = "http://127.0.0.1:%d" % self.api._websrv.server_port

    def tearDown(self):
        self.api._websrv.shutdown()
        self.api._websrv.server_close()
        self.db.close()
        try:
            self.tmp.cleanup()
        except OSError:
            pass        # Windows còn giữ handle SQLite — không phải lỗi của phép thử

    # ── tiện ích ────────────────────────────────────────────────────────────
    def get(self, duong, tham_so=None, key="read"):
        url = self.base + duong
        if tham_so:
            url += "?" + urllib.parse.urlencode(tham_so)
        req = urllib.request.Request(url, headers={"Authorization": "Bearer " + key})
        with urllib.request.urlopen(req, timeout=5) as res:
            return json.load(res)

    def mcp(self, calls, method="tools/call", key="read"):
        """Chạy MCP server thật trong tiến trình riêng, trỏ vào cầu giả."""
        env = dict(os.environ, OTL_API_BASE=self.base, OTL_API_KEY=key,
                   OTL_MCP_CONTROL="0", OTL_MCP_CONFIG="0", PYTHONIOENCODING="utf-8")
        if method == "tools/list":
            messages = [{"jsonrpc": "2.0", "id": 0, "method": "tools/list"}]
        else:
            messages = [{"jsonrpc": "2.0", "id": i, "method": "tools/call",
                         "params": {"name": ten, "arguments": args}}
                        for i, (ten, args) in enumerate(calls)]
        run = subprocess.run([sys.executable, MCP_SERVER],
                             input="\n".join(map(json.dumps, messages)) + "\n",
                             capture_output=True, text=True, encoding="utf-8",
                             env=env, timeout=30)
        # Server KHÔNG được chết vì đầu vào xấu — chết là mất luôn phiên của AI.
        self.assertEqual(run.returncode, 0, run.stderr)
        return [json.loads(dong)["result"] for dong in run.stdout.splitlines()]

    @staticmethod
    def than(kq):
        return json.loads(kq["content"][0]["text"])


class LocVaDemTest(CauGia):
    def test_http_loc_truoc_phan_trang(self):
        """Lọc chạy dưới kho: trang 1 và trang 2 không trùng, tổng đếm cùng bộ lọc."""
        loc = {"q": "ca phe dam", "from": "2026-09-06", "to": "2026-09-06"}
        trang1 = self.get("/api/v1/batches", dict(loc, n=20, offset=0))["batches"]
        trang2 = self.get("/api/v1/batches", dict(loc, n=20, offset=20))["batches"]
        self.assertEqual(len(trang1), 20)
        self.assertEqual(len(trang2), 20)
        self.assertFalse({r["id"] for r in trang1} & {r["id"] for r in trang2})
        self.assertTrue(all(r["prof_name"] == "Cà phê ĐẬM" for r in trang1 + trang2))

        tong = self.get("/api/v1/batches_count", loc)["count"]
        self.assertEqual(tong, 50)                 # 100 mẻ ngày 06, một nửa "ĐẬM"
        self.assertNotEqual(tong, len(trang1))     # ⚠ đúng cái lỗi đợt này đi sửa
        self.assertEqual(self.get("/api/v1/batches_count")["count"], self.SO_ME)

    def test_dem_rong_hop_le_khac_loi_dem(self):
        """`0` là đếm được mà không khớp; `null` là CHƯA ĐẾM ĐƯỢC. Gộp hai cái
        này lại là màn hình ghi "0 mẻ đã lưu" trong lúc kho có 900 mẻ."""
        rong = self.get("/api/v1/batches_count", {"q": "không-có-mẻ-nào-tên-thế-này"})
        self.assertEqual(rong["count"], 0)
        self.assertEqual(self.get("/api/v1/batches",
                                  {"q": "không-có-mẻ-nào-tên-thế-này"})["batches"], [])
        self.api._db = None                        # giả cảnh kho chưa mở
        self.assertIsNone(self.get("/api/v1/batches_count")["count"])
        self.assertIsNone(self.get("/api/v1/batches")["batches"])

    def test_mcp_day_bo_loc_xuong_api(self):
        loc = {"tu_khoa": "Cà phê đậm", "tu_ngay": "2026-09-06", "den_ngay": "2026-09-06"}
        trang1, trang2, dem = self.mcp([
            ("roaster_danh_sach_me", dict(loc, so_luong=20)),
            ("roaster_danh_sach_me", dict(loc, so_luong=20, bo_qua=20)),
            ("roaster_dem_me", loc)])
        t1, t2 = self.than(trang1), self.than(trang2)
        self.assertEqual(t1["so_dong"], 20)
        self.assertEqual(t1["tong"], 50)           # tổng THẬT, không phải 20
        self.assertEqual(t2["tong"], 50)
        self.assertEqual(t2["bo_qua"], 20)
        self.assertFalse({r["id"] for r in t1["batches"]} & {r["id"] for r in t2["batches"]})
        self.assertTrue(all(r["prof_name"] == "Cà phê ĐẬM" for r in t1["batches"]))
        self.assertEqual(self.than(dem)["tong"], 50)

    def test_mcp_giu_loi_goi_cu_chi_co_so_luong(self):
        """Lời gọi cũ `{so_luong: N}` phải chạy y như trước, chỉ khác là `tong`
        nay đúng thật."""
        cu, mac_dinh = self.mcp([("roaster_danh_sach_me", {"so_luong": 3}),
                                 ("roaster_danh_sach_me", {})])
        self.assertEqual(len(self.than(cu)["batches"]), 3)
        self.assertEqual(self.than(cu)["tong"], self.SO_ME)
        self.assertEqual(len(self.than(mac_dinh)["batches"]), 20)

    def test_mcp_bao_loi_thay_vi_doan_khi_khong_dem_duoc(self):
        """Đếm hỏng thì `tong = null` kèm ghi chú — KHÔNG lấy len(batches) thay."""
        self.api.db_batch_count = Mock(return_value=None)
        ds, dem = self.mcp([("roaster_danh_sach_me", {"so_luong": 5}),
                            ("roaster_dem_me", {})])
        than = self.than(ds)
        self.assertFalse(ds.get("isError"))        # danh sách vẫn dùng được
        self.assertEqual(len(than["batches"]), 5)
        self.assertIsNone(than["tong"])
        self.assertIn("ghi_chu_tong", than)
        self.assertTrue(dem.get("isError"))        # còn đếm riêng thì báo lỗi thẳng

        self.api._db = None
        (ds,) = self.mcp([("roaster_danh_sach_me", {})])
        self.assertTrue(ds.get("isError"))

    def test_mcp_bien_dau_vao_khong_lam_chet_server(self):
        xau = [("roaster_danh_sach_me", {"so_luong": -1}),
               ("roaster_danh_sach_me", {"so_luong": 0}),
               ("roaster_danh_sach_me", {"so_luong": 501}),
               ("roaster_danh_sach_me", {"so_luong": "hai chục"}),
               ("roaster_danh_sach_me", {"so_luong": 1.5}),
               ("roaster_danh_sach_me", {"so_luong": True}),
               ("roaster_danh_sach_me", {"bo_qua": -5}),
               ("roaster_danh_sach_me", {"tu_khoa": ["đậm"]}),
               ("roaster_danh_sach_me", {"tu_ngay": "07/09/2026"}),
               ("roaster_danh_sach_me", {"tu_ngay": "2026-09-07", "den_ngay": "2026-09-06"}),
               ("roaster_dem_me", {"den_ngay": "hôm qua"}),
               ("roaster_khong_co_that", {})]
        ket_qua = self.mcp(xau + [("roaster_danh_sach_me", {"so_luong": 2})])
        for kq, (ten, args) in zip(ket_qua, xau):
            self.assertTrue(kq.get("isError"), (ten, args, kq))
            self.assertTrue(kq["content"][0]["text"].startswith("Lỗi:"), kq)
        # Sau tất cả, server vẫn phục vụ bình thường
        self.assertEqual(len(self.than(ket_qua[-1])["batches"]), 2)

    def test_mcp_tu_khoa_tieng_viet_co_dau(self):
        co_dau, khong_dau = self.mcp([("roaster_dem_me", {"tu_khoa": "Cà phê ĐẬM"}),
                                      ("roaster_dem_me", {"tu_khoa": "ca phe dam"})])
        self.assertEqual(self.than(co_dau)["tong"], self.SO_ME // 2)
        self.assertEqual(self.than(khong_dau)["tong"], self.than(co_dau)["tong"])

    def test_mcp_khong_lo_cong_cu_lai_hay_cau_hinh(self):
        """Mặc định KHÔNG có đường ghi nào — công cụ mới không được kéo theo quyền."""
        (liet_ke,) = self.mcp([], method="tools/list")
        ten = [t["name"] for t in liet_ke["tools"]]
        self.assertIn("roaster_dem_me", ten)
        self.assertFalse([t for t in ten if t.startswith("roaster_lai_")])
        self.assertNotIn("roaster_set_machine_param", ten)
        thuoc_tinh = next(t for t in liet_ke["tools"]
                          if t["name"] == "roaster_danh_sach_me")["inputSchema"]["properties"]
        for k in ("so_luong", "bo_qua", "tu_khoa", "tu_ngay", "den_ngay"):
            self.assertIn(k, thuoc_tinh)


class OpenApiTest(unittest.TestCase):
    """OpenAPI phải phủ đúng những đường MCP gọi, và không quảng cáo đường chưa có."""

    @classmethod
    def setUpClass(cls):
        cls.oas = _nap_openapi()
        cls.duong = cls.oas["paths"]
        cls.cho_phep, cls.cho_phep_ghi = _danh_sach_duong_mcp()
        thu_muc = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(thu_muc, "roast_lab_hmi.py"), encoding="utf-8") as f:
            cls.nguon_app = f.read()

    def test_phu_het_duong_mcp_goi(self):
        for duong in self.cho_phep:
            self.assertIn(duong, self.duong, "OpenAPI thiếu " + duong)
            self.assertIn("get", self.duong[duong], duong)
        for duong in self.cho_phep_ghi:
            self.assertIn(duong, self.duong, "OpenAPI thiếu " + duong)
            self.assertIn("post", self.duong[duong], duong)

    def test_khong_quang_cao_duong_chua_trien_khai(self):
        """Mọi đường trong tài liệu phải có mặt trong handler của app."""
        for duong in self.duong:
            hau_to = duong[len("/api/v1/"):]
            self.assertIn('"/api/%s' % hau_to, self.nguon_app,
                          "OpenAPI ghi %s mà app không phục vụ" % duong)

    def test_ten_tham_so_khop_handler(self):
        def ten_tham_so(duong, cach="get"):
            return {p["name"] for p in self.duong[duong][cach].get("parameters", [])}

        self.assertEqual(ten_tham_so("/api/v1/batches"),
                         {"n", "offset", "q", "from", "to"})
        self.assertEqual(ten_tham_so("/api/v1/batches_count"), {"q", "from", "to"})
        self.assertEqual(ten_tham_so("/api/v1/batch_curve"), {"id"})
        self.assertEqual(ten_tham_so("/api/v1/batch_stats"), {"id"})
        self.assertEqual(ten_tham_so("/api/v1/batches_curves"), {"ids"})
        self.assertEqual(ten_tham_so("/api/v1/assistant_skill"), {"name"})
        # Thân POST phải đúng khoá handler đọc
        than = self.duong["/api/v1/write"]["post"]["requestBody"]["content"]["application/json"]["schema"]
        self.assertEqual(set(than["required"]), {"name", "value"})
        for cam in ("hb", "agent"):
            self.assertNotIn(cam, than["properties"]["name"]["enum"])
        self.assertIn("phut", self.duong["/api/v1/lease_open"]["post"]
                      ["requestBody"]["content"]["application/json"]["schema"]["properties"])
        self.assertIn("ly_do", self.duong["/api/v1/lease_close"]["post"]
                      ["requestBody"]["content"]["application/json"]["schema"]["properties"])

    def test_pham_vi_va_so_tham_so_M_theo_nguon(self):
        with open(os.path.join(GOC, "protocol", "pc_link.json"), encoding="utf-8") as f:
            n_M = int(json.load(f)["config"]["count"])
        self.assertGreaterEqual(n_M, 53)
        mc_read = self.duong["/api/v1/mc_read"]["get"]
        self.assertIn("M1..M%d" % n_M, mc_read["description"])
        self.assertIn("%d tham số" % n_M, mc_read["summary"])
        # Bản cũ ghi cứng "Đọc 52 tham số" trong summary trong khi mô tả đã là
        # M1..M53 — tài liệu tự mâu thuẫn ngay trong một endpoint.
        van_ban = json.dumps(self.oas, ensure_ascii=False)
        for cung_nhac in ("M52", "52 tham số"):
            self.assertNotIn(cung_nhac, van_ban, "còn ghi cứng: " + cung_nhac)
        items = (self.duong["/api/v1/mc_write"]["post"]["requestBody"]
                 ["content"]["application/json"]["schema"]["properties"]["items"])
        self.assertEqual(items["maxItems"], n_M)
        # Phạm vi quyền ghi trong tài liệu phải khớp bảng SCOPE_POST của app
        for duong, scope in (("/api/v1/write", "control"), ("/api/v1/lease_open", "control"),
                             ("/api/v1/lease_beat", "control"), ("/api/v1/lease_close", "control"),
                             ("/api/v1/mc_write", "config")):
            self.assertIn(scope, self.duong[duong]["post"]["responses"]["403"]["description"])
        self.assertEqual(H.SCOPE_POST.get("/api/write"), "control")
        self.assertEqual(H.SCOPE_POST.get("/api/lease_beat"), "control")

    def test_noi_ro_queued_khong_phai_da_thuc_hien(self):
        mo_ta = self.duong["/api/v1/write"]["post"]["description"]
        self.assertIn("queued", mo_ta)
        self.assertIn("chưa xác nhận", mo_ta)


if __name__ == "__main__":
    unittest.main()
