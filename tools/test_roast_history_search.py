"""Kiểm tìm kiếm/phân trang trên kho SQLite tạm, không đọc kho mẻ thật."""
import tempfile
import unittest
from roast_db import RoastDb


class HistorySearchTest(unittest.TestCase):
    def test_search_before_pagination(self):
        with tempfile.TemporaryDirectory() as directory:
            db = RoastDb(directory)
            try:
                for i in range(125):
                    bid = db.begin({'name': 'Cà phê ĐẬM' if i % 2 else 'Nhạt', 'roaster': 'Trường'})
                    db.finish(bid, {'code': f'#B-{i:04d}', 'drop_sec': 600})
                    db._con.execute('UPDATE batches SET started_at=? WHERE id=?',
                                    ('2026-09-06 10:00:00' if i < 100 else '2026-09-07 10:00:00', bid))
                db._con.commit()
                page1 = db.latest(50, 'ca phe dam', '2026-09-06', '2026-09-06')
                self.assertEqual(len(page1), 50)
                self.assertTrue(all(r['prof_name'] == 'Cà phê ĐẬM' for r in page1))
                self.assertEqual(db.latest(50, 'ca phe dam', '2026-09-06', '2026-09-06', 50), [])
                self.assertEqual(len(db.latest(50, 'truong', '2026-09-07', '2026-09-07')), 25)
                self.assertEqual(db.latest(50, "' OR 1=1 --"), [])
                self.assertEqual(len(db.latest(50, '#B-0001')), 1)
                ids1 = {r['id'] for r in db.latest(50)}
                ids2 = {r['id'] for r in db.latest(50, offset=50)}
                self.assertFalse(ids1 & ids2)
                self.assertEqual(len(db.latest(50, offset=100)), 25)
            finally:
                db.close()


if __name__ == '__main__':
    unittest.main()
