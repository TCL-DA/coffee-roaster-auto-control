"""Kiểm thử serial_terminal_auth — tạo token KHÔNG BAO GIỜ được làm sập app.

Lỗi thật 15/09/2026: gửi exe sang máy Win 11, icacls chạy quá 5 giây →
TimeoutExpired lọt ra ngoài → app sập ngay lúc mở.
"""

import os
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

import serial_terminal_auth as auth


def _ok(returncode=0):
    return subprocess.CompletedProcess(["icacls"], returncode, b"", b"")


class TokenTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "OTL" / "api-token"
        self.env = mock.patch.dict(os.environ, {"OTL_SERIAL_API_TOKEN_FILE": str(self.path),
                                                "USERNAME": "Dell"})
        self.env.start()
        os.environ.pop("OTL_SERIAL_API_TOKEN", None)
        auth._cached_token = None

    def tearDown(self):
        auth._cached_token = None
        self.env.stop()
        self.tmp.cleanup()

    def _dong_bo(self):
        """Chạy khoá quyền ngay trên luồng test để kiểm tra kết quả."""
        return mock.patch.object(auth, "_lock_down_windows", side_effect=auth._lock_down_windows_now)

    @unittest.skipUnless(os.name == "nt", "icacls chỉ có trên Windows")
    def test_icacls_het_gio_van_tao_duoc_token(self):
        het_gio = subprocess.TimeoutExpired(["icacls"], auth.ICACLS_TIMEOUT_S)
        with self._dong_bo(), mock.patch.object(auth.subprocess, "run", side_effect=het_gio):
            token = auth.load_or_create_token()
        self.assertGreaterEqual(len(token), 24)
        self.assertEqual(self.path.read_text(encoding="ascii").strip(), token)

    @unittest.skipUnless(os.name == "nt", "icacls chỉ có trên Windows")
    def test_khong_co_icacls_khong_lam_sap(self):
        with mock.patch.object(auth.subprocess, "run", side_effect=FileNotFoundError("icacls")):
            auth._lock_down_windows_now(self.path)

    @unittest.skipUnless(os.name == "nt", "icacls chỉ có trên Windows")
    def test_cap_quyen_hong_thi_khong_cat_ke_thua(self):
        with mock.patch.object(auth.subprocess, "run", return_value=_ok(1332)) as run:
            auth._lock_down_windows_now(self.path)
        self.assertEqual(run.call_count, 1)
        self.assertIn("/grant:r", run.call_args_list[0].args[0])

    @unittest.skipUnless(os.name == "nt", "icacls chỉ có trên Windows")
    def test_cap_quyen_xong_moi_cat_ke_thua_va_khong_bat_console(self):
        with mock.patch.object(auth.subprocess, "run", return_value=_ok()) as run:
            auth._lock_down_windows_now(self.path)
        lenh = [c.args[0] for c in run.call_args_list]
        self.assertEqual(len(lenh), 2)
        self.assertIn("/grant:r", lenh[0])
        self.assertIn("Dell:(R,W)", lenh[0])
        self.assertIn("/inheritance:r", lenh[1])
        for c in run.call_args_list:
            self.assertEqual(c.kwargs["creationflags"], subprocess.CREATE_NO_WINDOW)

    def test_icacls_cham_khong_chan_khoi_dong(self):
        tha = threading.Event()
        def cham(*_a, **_k):
            tha.wait(5)
            return _ok()
        with mock.patch.object(auth.subprocess, "run", side_effect=cham):
            bat_dau = time.monotonic()
            token = auth.load_or_create_token()
            troi = time.monotonic() - bat_dau
            tha.set()
        self.assertGreaterEqual(len(token), 24)
        self.assertLess(troi, 1.0)

    def test_tep_token_bi_khoa_quyen_van_mo_app(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text("x" * 40 + "\n", encoding="ascii")
        with mock.patch.object(Path, "read_text", side_effect=PermissionError("khoá")):
            token = auth.load_or_create_token()
        self.assertGreaterEqual(len(token), 24)

    def test_tep_token_hong_van_mo_app(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text("ngan\n", encoding="ascii")
        self.assertGreaterEqual(len(auth.load_or_create_token()), 24)

    def test_doc_lai_token_da_luu(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text("a" * 43 + "\n", encoding="ascii")
        self.assertEqual(auth.load_or_create_token(), "a" * 43)

    def test_token_moi_truong_ngan_van_bao_loi_cau_hinh(self):
        with mock.patch.dict(os.environ, {"OTL_SERIAL_API_TOKEN": "ngan"}):
            with self.assertRaises(RuntimeError):
                auth.load_or_create_token()


if __name__ == "__main__":
    unittest.main()
