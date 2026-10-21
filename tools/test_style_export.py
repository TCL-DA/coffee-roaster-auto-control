"""Kiểm xuất phong cách bằng hộp lưu giả, không mở dữ liệu hay cửa sổ máy thật."""
import json
import tempfile
import unittest
from pathlib import Path
from roast_lab_hmi import Api


class StyleExportTest(unittest.TestCase):
    def test_save_and_cancel(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'phong-cach.json'
            class Window:
                def create_file_dialog(self, *args, **kwargs):
                    return [str(path)]
            api = Api.__new__(Api)
            api._window = Window()
            bundle = {'format': 'otl-style', 'version': 1, 'style': {'name': 'Rừng sâu'}}
            self.assertTrue(api.style_export(bundle)['ok'])
            self.assertEqual(json.loads(path.read_text(encoding='utf-8')), bundle)
            self.assertFalse(api.style_export({'format': 'machine-config'})['ok'])
            api._window.create_file_dialog = lambda *args, **kwargs: None
            self.assertTrue(api.style_export(bundle)['cancelled'])
            self.assertEqual(json.loads(path.read_text(encoding='utf-8')), bundle)


if __name__ == '__main__':
    unittest.main()
