"""Review Codex 14/09/2026 — phần kho & bản ghi mẻ (không cần trình duyệt).

RF-05  Thợ sửa kg SAU mẻ → kho và tiến độ đơn phải theo số thật, idempotent,
       không trừ/cộng hai lần; mẻ chưa từng trừ kho/cộng đơn thì không tự gắn bừa.
RF-08  Ghi chú dài quá giới hạn → TỪ CHỐI, không cắt lặng rồi vẫn trả ok.
RF-01  Mẻ đóng lúc mất kết nối → bản ghi INTERRUPTED chứ không DONE.

Chạy trên kho SQLite tạm — không đụng dữ liệu thật.
"""
import sys, pathlib, tempfile
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from roast_db import RoastDb          # noqa: E402
from inventory_db import InventoryDb  # noqa: E402

fails = []


def chk(name, cond, got=""):
    print(("  OK   " if cond else "  FAIL ") + name + (f"  → {got}" if got != "" else ""))
    if not cond:
        fails.append(name)


with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    db = RoastDb(tmp)
    inv = InventoryDb(db)

    def don(oid):
        r = inv._con.execute("SELECT roasted_kg, status FROM orders WHERE id=?", (oid,)).fetchone()
        return round(r["roasted_kg"], 2), r["status"]

    def so_dong(bid):
        return inv._con.execute("SELECT COUNT(*) FROM lot_movements WHERE batch_id=?", (bid,)).fetchone()[0]

    lot = inv.lot_add({"name": "Lô thử", "kg": 100})["id"]
    inv.hopper_set(lot)
    oid = inv.order_add({"code": "DH1", "prof_no": 2, "qty_kg": 10})["id"]

    print("RF-05) Chốt mẻ theo định mức rồi thợ sửa kg thật")
    b1 = db.begin({"no": 2, "name": "B"})
    db.finish(b1, {"code": "M1"})
    inv.consume_batch(b1, 6.0)                       # chốt mẻ: chưa có kg → định mức 6
    inv.order_progress(2, 5.1, batch_id=b1)          # 6 × (1 − 15%)
    chk("kho trừ 6 kg theo định mức", inv.lot_balance(lot) == 94.0, inv.lot_balance(lot))
    chk("đơn cộng 5,1 kg", don(oid) == (5.1, "open"), don(oid))
    inv.order_progress(2, 5.1, batch_id=b1)
    chk("chốt mẻ gọi đúp (app + web) KHÔNG cộng đơn lần hai", don(oid) == (5.1, "open"), don(oid))

    inv.rebase_batch(b1, 3.0, 2.55)
    chk("sửa kg = 3 → kho hoàn lại 3 kg (97)", inv.lot_balance(lot) == 97.0, inv.lot_balance(lot))
    chk("sửa kg = 3 → đơn về 2,55", don(oid) == (2.55, "open"), don(oid))
    chk("giá thành mẻ đọc đúng kg mới", inv.batch_economics(b1)["kg_in"] == 3.0, inv.batch_economics(b1)["kg_in"])
    n = so_dong(b1)
    inv.rebase_batch(b1, 3.0, 2.55)
    chk("gọi lại cùng số → không ghi thêm dòng nào (idempotent)", so_dong(b1) == n and inv.lot_balance(lot) == 97.0,
        (so_dong(b1), inv.lot_balance(lot)))
    chk("…và đơn không đổi", don(oid) == (2.55, "open"), don(oid))

    inv.rebase_batch(b1, 12.0, 10.2)
    chk("sửa lên 12 kg → kho 88", inv.lot_balance(lot) == 88.0, inv.lot_balance(lot))
    chk("…đơn đủ 10,2 ≥ 10 → tự chuyển done", don(oid) == (10.2, "done"), don(oid))
    inv.rebase_batch(b1, 6.0, 5.1)
    chk("hạ về 6 kg → đơn MỞ LẠI", don(oid) == (5.1, "open"), don(oid))
    chk("…kho về 94", inv.lot_balance(lot) == 94.0, inv.lot_balance(lot))

    inv.order_set(oid, {"status": "cancel"})
    inv.rebase_batch(b1, 12.0, 10.2)
    chk("đơn đã HUỶ thì giữ nguyên trạng thái huỷ", don(oid)[1] == "cancel", don(oid))

    b2 = db.begin({"no": 5, "name": "Tự do"})
    db.finish(b2, {"code": "M2"})
    bal = inv.lot_balance(lot)
    r2 = inv.rebase_batch(b2, 5.0, 4.25)
    chk("mẻ chưa từng trừ kho/cộng đơn → không tự gắn lô/đơn",
        r2.get("ok") and r2["stock"] is None and r2["order"] is None and inv.lot_balance(lot) == bal, r2)

    print("RF-08) Ghi chú quá giới hạn phải bị từ chối")
    r = inv.cup_add({"target": "batch", "target_id": b1, "notes": "x" * 401})
    chk("401 ký tự → ok:false + lý do", r.get("ok") is False and "400" in (r.get("err") or ""), r)
    r = inv.cup_add({"target": "batch", "target_id": b1, "notes": "x" * 400})
    chk("400 ký tự → lưu được", r.get("ok") is True, r)
    luu = inv._con.execute("SELECT notes FROM cuppings WHERE id=?", (r["id"],)).fetchone()["notes"]
    chk("…và lưu đủ 400 ký tự", len(luu) == 400, len(luu))

    print("RF-01) Mẻ đóng lúc mất kết nối → INTERRUPTED")
    b3 = db.begin({"no": 1, "name": "A"})
    db.point(b3, {"t_roast": 1, "bt": 180.0, "et": 200.0})
    db.finish(b3, {"code": "M3", "interrupted": True})
    st = db._con.execute("SELECT status FROM batches WHERE id=?", (b3,)).fetchone()[0]
    chk("status = INTERRUPTED", st == "INTERRUPTED", st)
    b4 = db.begin({"no": 1, "name": "A"})
    db.finish(b4, {"code": "M4"})
    st = db._con.execute("SELECT status FROM batches WHERE id=?", (b4,)).fetchone()[0]
    chk("chốt thường vẫn DONE", st == "DONE", st)
    db._con.close()

print("\n" + ("TẤT CẢ ĐẠT" if not fails else f"{len(fails)} MỤC HỎNG: {fails}"))
sys.exit(1 if fails else 0)
