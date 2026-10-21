"""Kiểm quyền, lưu PIN có số 0 đầu và lỗi ghi; không dùng dữ liệu thật."""
import configparser
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
import roast_lab_hmi as H


class WebPinTest(unittest.TestCase):
    def test_pin(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'settings.ini'
            path.write_text('[WebServer]\npin_dieu_khien=123456\ncong=8555\n[Other]\nvalue=keep\n',encoding='utf-8')
            api=H.Api.__new__(H.Api)
            api._ini_path=lambda:str(path)
            api._is_master=Mock(return_value=False)
            api.web_cfg={'pin':'123456'}
            api.web_tokens={'old':123}
            self.assertFalse(api.web_pin_get()['ok'])
            self.assertFalse(api.web_pin_set('001234')['ok'])
            api._is_master.return_value=True
            for value in ['123','1234567890123','abcdef',123456,'１２３４５６','123456','000000']:
                self.assertFalse(api.web_pin_set(value)['ok'])
            with patch.object(H.os,'replace',side_effect=OSError()):
                self.assertFalse(api.web_pin_set('001234')['ok'])
            self.assertEqual(api.web_cfg['pin'],'123456')
            self.assertTrue(api.web_tokens)
            self.assertTrue(api.web_pin_set('001234')['ok'])
            self.assertEqual(api.web_pin_get()['pin'],'001234')
            self.assertFalse(api.web_tokens)
            c=configparser.ConfigParser();c.read(path,encoding='utf-8')
            self.assertEqual(c['WebServer']['pin_dieu_khien'],'001234')
            self.assertEqual(c['Other']['value'],'keep')
            self.assertEqual(c['WebServer']['cong'],'8555')


if __name__=='__main__':unittest.main()
