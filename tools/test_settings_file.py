"""Kiểm xuất/nhập file cài đặt app bằng hộp chọn file giả, không mở cửa sổ máy thật."""
import tempfile
import unittest
from pathlib import Path
from roast_lab_hmi import Api


class Window:
    def __init__(self, result):
        self.result, self.calls = result, []

    def create_file_dialog(self, *args, **kwargs):
        self.calls.append(kwargs)
        return self.result


class SettingsFileTest(unittest.TestCase):
    TEXT = "nhom,khoa,gia_tri,mo_ta\r\napp,mn_preset,Cacao 30kg (anh Hiếu),Preset máy\r\n"

    def test_export_writes_utf8_bom_and_cleans_name(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'cai-dat.csv'
            api = Api.__new__(Api)
            api._window = Window([str(path)])
            result = api.settings_export(self.TEXT, 'OTL:cai/dat?.csv')
            self.assertTrue(result['ok'])
            self.assertEqual(api._window.calls[0]['save_filename'], 'OTL-cai-dat-.csv')
            raw = path.read_bytes()
            self.assertTrue(raw.startswith(b'\xef\xbb\xbf'))       # Excel mở không vỡ dấu
            self.assertEqual(raw[3:].decode('utf-8'), self.TEXT)

    def test_export_rejects_bad_content_and_cancel(self):
        api = Api.__new__(Api)
        api._window = Window(None)
        self.assertFalse(api.settings_export({'khong': 'phai chu'})['ok'])
        self.assertFalse(api.settings_export('x' * 1_000_001)['ok'])
        self.assertTrue(api.settings_export(self.TEXT)['cancelled'])
        api._window = None
        self.assertFalse(api.settings_export(self.TEXT)['ok'])

    def test_import_returns_text_without_applying(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'cai-dat.csv'
            path.write_bytes(b'\xef\xbb\xbf' + self.TEXT.encode('utf-8'))
            api = Api.__new__(Api)
            api._window = Window((str(path),))
            result = api.settings_import()
            self.assertEqual(result, {'ok': True, 'text': self.TEXT, 'name': 'cai-dat.csv'})

    def test_import_ansi_fallback_size_limit_and_cancel(self):
        with tempfile.TemporaryDirectory() as directory:
            ansi = Path(directory) / 'ansi.csv'
            # cp1258 (Excel "CSV" kiểu ANSI) lưu chữ có dấu thanh = chữ gốc + dấu thanh RỜI
            dong = 'app,ui_view,Đơn giản\r\n'
            ansi.write_bytes(dong.encode('cp1258'))
            api = Api.__new__(Api)
            api._window = Window([str(ansi)])
            self.assertEqual(api.settings_import()['text'], dong)
            big = Path(directory) / 'big.csv'
            big.write_bytes(b'x' * 1_000_001)
            api._window = Window([str(big)])
            self.assertFalse(api.settings_import()['ok'])
            api._window = Window(None)
            self.assertTrue(api.settings_import()['cancelled'])


if __name__ == '__main__':
    unittest.main()
