"""
Tầng nghiệp vụ xưởng rang — GĐ4 (§3 plan-hmi-roadmap: quản lý xưởng, hướng Cropster).

Đây là "model dữ liệu kinh doanh" mà §3 gọi là điều kiện tiên quyết: lô nhân,
sổ biến động, đơn hàng, cupping, cấu hình chi phí. TÁI DÙNG kết nối SQLite của
RoastDb (cùng file batches.db) nên:
  - được BACKUP ngày + quick_check + tự hồi phục y như bảng mẻ (không phải viết lại),
  - quan hệ thẳng với bảng `batches` qua batch_id (§3 "quan hệ với batches"),
  - một khoá ghi chung → không tranh chấp với luồng ghi điểm curve mỗi giây.

Triết lý bám §3.1 (tránh 4 bẫy làm chết hệ thống kho ở xưởng nhỏ):
  1. TRỪ KHO BẰNG CÂN THẬT (kg đã cân), không bằng số danh định → sổ không lệch dần.
  2. "LÔ ĐANG MỞ" theo phễu: gán lô 1 lần, mọi mẻ tự ghi lô đó (0 thao tác/mẻ).
  3. NÓI BẰNG MẺ, không bằng kg: tồn ÷ kg/mẻ = "còn ~N mẻ" (thợ nghĩ bằng mẻ).
  4. SỔ BIẾN ĐỘNG (ledger): số dư = tổng ledger; kiểm kho chỉnh lệch không phá lịch sử.

Thuần stdlib. Mọi hàm KHÔNG nổ exception ra ngoài lớp Api — trả dict {"ok":...}.
"""

import json
import time


# Số dư một lô = tổng cột kg trong lot_movements (nhập dương, trừ âm). Không giữ
# cột "số dư" nào để tránh lệch giữa cache và sự thật (bẫy §3.1 mục 4).
_SCHEMA = """
CREATE TABLE IF NOT EXISTS lots(
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  code        TEXT    DEFAULT '',        -- mã lô ngắn hiện trên thẻ ("DL-07")
  name        TEXT    NOT NULL,          -- tên/nguồn gốc ("Đắk Lắk Robusta")
  farm        TEXT    DEFAULT '',        -- nông trại (tuỳ chọn)
  variety     TEXT    DEFAULT '',        -- giống (tuỳ chọn)
  process     TEXT    DEFAULT '',        -- sơ chế: washed/natural/honey (tuỳ chọn)
  bag_kg      REAL    DEFAULT 0,         -- khối lượng 1 bao (nhập theo bao §3.1#5)
  cost_per_kg REAL    DEFAULT 0,         -- giá vốn/kg gồm vận chuyển (tuỳ chọn)
  moisture    REAL    DEFAULT 0,         -- độ ẩm % (tuỳ chọn)
  note        TEXT    DEFAULT '',
  received_at TEXT    NOT NULL,          -- ngày nhập 'YYYY-MM-DD' (tính tuổi lô §3.1#6)
  active      INTEGER DEFAULT 1,         -- 0 = đã ẩn (hết/ngừng dùng)
  created_at  TEXT    NOT NULL
);
CREATE TABLE IF NOT EXISTS lot_movements(
  id       INTEGER PRIMARY KEY AUTOINCREMENT,
  lot_id   INTEGER NOT NULL,
  ts       TEXT    NOT NULL,             -- 'YYYY-MM-DD HH:MM:SS'
  kind     TEXT    NOT NULL,             -- nhap | me | kiemke | huy
  kg       REAL    NOT NULL,             -- +nhập/-trừ (kiemke có thể +/-)
  batch_id INTEGER,                      -- kind='me' → mẻ nào trừ (nối batches)
  note     TEXT    DEFAULT '',
  user     TEXT    DEFAULT ''
);
CREATE INDEX IF NOT EXISTS ix_mov_lot ON lot_movements(lot_id);
CREATE INDEX IF NOT EXISTS ix_mov_batch ON lot_movements(batch_id);
-- Phễu: mỗi phễu giữ "lô đang mở". Gán 1 lần khi đổ bao (§3.1#2).
CREATE TABLE IF NOT EXISTS hoppers(
  id         INTEGER PRIMARY KEY,        -- số phễu (1 là mặc định máy 1 phễu)
  lot_id     INTEGER,                    -- lô đang mở (NULL = chưa gán)
  opened_at  TEXT    DEFAULT '',
  opened_by  TEXT    DEFAULT ''
);
-- Đơn hàng / kế hoạch sản xuất (§3 #44). qty theo KG; roasted_kg cộng dồn.
CREATE TABLE IF NOT EXISTS orders(
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  code        TEXT    DEFAULT '',
  customer    TEXT    DEFAULT '',
  product     TEXT    DEFAULT '',        -- hồ sơ/blend cần rang
  prof_no     INTEGER DEFAULT 0,         -- gợi ý hồ sơ (1-based, 0 = tự do)
  qty_kg      REAL    DEFAULT 0,         -- cần giao (kg thành phẩm)
  roasted_kg  REAL    DEFAULT 0,         -- đã rang xong (kg thành phẩm)
  due_date    TEXT    DEFAULT '',        -- hạn giao 'YYYY-MM-DD'
  status      TEXT    DEFAULT 'open',    -- open | done | cancel
  note        TEXT    DEFAULT '',
  created_at  TEXT    NOT NULL
);
-- Cupping / chấm điểm (§3.2). Gắn LINH HOẠT: lot | batch | profile (§3.2#3).
CREATE TABLE IF NOT EXISTS cuppings(
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  target     TEXT    NOT NULL,           -- 'lot' | 'batch' | 'profile'
  target_id  INTEGER NOT NULL,           -- id lô / id mẻ / số hồ sơ
  tier       INTEGER DEFAULT 1,          -- 1 = QC nhanh (sao), 2 = SCA /100
  stars      REAL    DEFAULT 0,          -- 0..5 (tầng 1)
  score      REAL    DEFAULT 0,          -- 0..100 (tầng 2, SCA)
  defects    TEXT    DEFAULT '',         -- lỗi (mô tả ngắn)
  flavors    TEXT    DEFAULT '[]',       -- JSON tag hương vị (§3.2#4)
  notes      TEXT    DEFAULT '',
  cupper     TEXT    DEFAULT '',
  blind_code TEXT    DEFAULT '',         -- mã mẫu ẩn (phiên mù, tầng 2)
  cupped_at  TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_cup_target ON cuppings(target, target_id);
-- Cấu hình chi phí (§3 #45) — key-value, 1 dòng mỗi khoá.
CREATE TABLE IF NOT EXISTS biz_config(
  k TEXT PRIMARY KEY,
  v TEXT
);
"""

# Khoá chi phí mặc định (đơn vị: VND). Xưởng chỉnh trong UI; 0 = chưa cấu hình.
_COST_DEFAULTS = {
    "tien_te": "VND",
    "gas_vnd_gio": "0",         # tiền gas mỗi giờ đốt (ước lượng theo thời gian mẻ)
    "cong_vnd_me": "0",         # tiền nhân công mỗi mẻ
    "dien_vnd_me": "0",         # điện + khấu hao mỗi mẻ (gộp overhead)
    "gia_ban_vnd_kg": "0",      # giá bán thành phẩm/kg (tính lợi nhuận)
    "me_kg_dinh_muc": "6",      # kg 1 mẻ danh định (quy 'còn N mẻ' + trừ kho khi chưa cân)
    "hao_hut_dinh_muc_pct": "15",  # hao hụt ước lượng để cộng tiến độ đơn hàng
}


def _now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _today():
    return time.strftime("%Y-%m-%d")


def _f(x, d=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return d


def _i(x, d=0):
    try:
        return int(x)
    except (TypeError, ValueError):
        return d


class InventoryDb:
    """Kho + kinh doanh trên CHUNG kết nối SQLite với RoastDb (khoá dùng chung)."""

    def __init__(self, roast_db, log=None):
        # Dùng thẳng con + lock của RoastDb: một file, một khoá ghi, một backup.
        self._con = roast_db._con
        self._lock = roast_db._lock
        self._log = log or (lambda *a: None)
        with self._lock:
            self._con.executescript(_SCHEMA)
            # phễu 1 luôn tồn tại (máy mặc định 1 phễu)
            self._con.execute("INSERT OR IGNORE INTO hoppers(id) VALUES(1)")
            for k, v in _COST_DEFAULTS.items():
                self._con.execute("INSERT OR IGNORE INTO biz_config(k,v) VALUES(?,?)", (k, v))
            self._con.commit()

    # ══ LÔ NHÂN ════════════════════════════════════════════════════════════
    def lot_add(self, d):
        """Nhập lô mới. Nhập theo BAO (bag_kg×bags) HOẶC kg trực tiếp (§3.1#5).
        Bắt buộc chỉ `name` + khối lượng > 0; còn lại tuỳ chọn."""
        d = d if isinstance(d, dict) else {}
        name = str(d.get("name") or "").strip()[:80]
        if not name:
            return {"ok": False, "err": "thiếu tên lô"}
        bag_kg = _f(d.get("bag_kg"))
        bags = _f(d.get("bags"))
        kg = _f(d.get("kg"))
        if kg <= 0:
            kg = bag_kg * bags
        if kg <= 0:
            return {"ok": False, "err": "khối lượng phải > 0 (nhập số bao×kg/bao hoặc kg)"}
        recv = str(d.get("received_at") or _today())[:10]
        try:
            with self._lock:
                cur = self._con.execute(
                    "INSERT INTO lots(code,name,farm,variety,process,bag_kg,"
                    "cost_per_kg,moisture,note,received_at,active,created_at)"
                    " VALUES(?,?,?,?,?,?,?,?,?,?,1,?)",
                    (str(d.get("code") or "")[:24], name,
                     str(d.get("farm") or "")[:60], str(d.get("variety") or "")[:40],
                     str(d.get("process") or "")[:24], bag_kg,
                     _f(d.get("cost_per_kg")), _f(d.get("moisture")),
                     str(d.get("note") or "")[:200], recv, _now()))
                lot_id = cur.lastrowid
                # biến động NHẬP đầu tiên
                self._con.execute(
                    "INSERT INTO lot_movements(lot_id,ts,kind,kg,note,user)"
                    " VALUES(?,?, 'nhap', ?, ?, ?)",
                    (lot_id, _now(), kg, "nhập lô" + (f" ({int(bags)} bao)" if bags else ""),
                     str(d.get("user") or "")[:40]))
                self._con.commit()
            self._log("[KHO] nhập lô #%s %s: %.1fkg", lot_id, name, kg)
            return {"ok": True, "id": lot_id, "kg": kg}
        except Exception as e:
            self._log("[KHO] nhập lô lỗi: %s", e)
            return {"ok": False, "err": str(e)}

    def lot_edit(self, lot_id, d):
        """Sửa thông tin mô tả lô (KHÔNG đụng khối lượng — dùng ledger cho lượng)."""
        d = d if isinstance(d, dict) else {}
        cols = ("code", "name", "farm", "variety", "process", "bag_kg",
                "cost_per_kg", "moisture", "note", "received_at", "active")
        sets, vals = [], []
        for c in cols:
            if c in d:
                sets.append(f"{c}=?")
                v = d[c]
                if c in ("bag_kg", "cost_per_kg", "moisture"):
                    v = _f(v)
                elif c == "active":
                    v = 1 if v else 0
                else:
                    v = str(v)[:200]
                vals.append(v)
        if not sets:
            return {"ok": False, "err": "không có gì để sửa"}
        vals.append(_i(lot_id))
        try:
            with self._lock:
                self._con.execute(f"UPDATE lots SET {','.join(sets)} WHERE id=?", vals)
                self._con.commit()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "err": str(e)}

    def lot_balance(self, lot_id):
        """Số dư một lô (kg) = tổng ledger."""
        with self._lock:
            row = self._con.execute(
                "SELECT COALESCE(SUM(kg),0) FROM lot_movements WHERE lot_id=?",
                (_i(lot_id),)).fetchone()
        return round(row[0], 3)

    def lot_adjust(self, lot_id, kg, note="", user=""):
        """Kiểm kho — chỉnh lệch (rơi vãi, bay ẩm). Ghi ledger 'kiemke', KHÔNG sửa
        lịch sử (§3.1#4). kg = số kg CỘNG THÊM (âm = giảm)."""
        kg = _f(kg)
        if kg == 0:
            return {"ok": False, "err": "lượng chỉnh = 0"}
        try:
            with self._lock:
                self._con.execute(
                    "INSERT INTO lot_movements(lot_id,ts,kind,kg,note,user)"
                    " VALUES(?,?, 'kiemke', ?, ?, ?)",
                    (_i(lot_id), _now(), kg, str(note or "kiểm kho")[:200], str(user)[:40]))
                self._con.commit()
            self._log("[KHO] kiểm kho lô #%s: %+.2fkg (%s)", lot_id, kg, note)
            return {"ok": True, "so_du": self.lot_balance(lot_id)}
        except Exception as e:
            return {"ok": False, "err": str(e)}

    def lots_overview(self, batch_kg=6.0):
        """Danh sách lô còn dùng + số dư + TUỔI + "còn ~N mẻ" (§3.1#3, #6).

        batch_kg = kg trung bình 1 mẻ (từ MACHINE_BATCH_KG) để quy số dư ra mẻ.
        Sắp FIFO: lô nhập lâu nhất trước (§3.1#6 khuyến khích dùng lô cũ)."""
        batch_kg = _f(batch_kg, 6.0) or 6.0
        with self._lock:
            rows = self._con.execute(
                "SELECT l.*, "
                " (SELECT COALESCE(SUM(kg),0) FROM lot_movements m WHERE m.lot_id=l.id) bal "
                "FROM lots l WHERE l.active=1 ORDER BY l.received_at ASC, l.id ASC"
            ).fetchall()
        open_lot = self.hopper_lot(1)
        today = time.strftime("%Y-%m-%d")
        out = []
        for r in rows:
            d = dict(r)
            bal = round(d.pop("bal"), 2)
            d["so_du_kg"] = bal
            d["con_me"] = round(bal / batch_kg, 1) if batch_kg else None
            d["tuoi_ngay"] = _days_between(d.get("received_at"), today)
            d["dang_mo"] = (open_lot == d["id"])       # lô đang gán phễu 1
            d["canh_bao_cu"] = (d["tuoi_ngay"] or 0) > 365   # nhân >12 tháng (§3.1#6)
            out.append(d)
        return out

    def lot_movements(self, lot_id, n=200):
        """Sổ biến động một lô (mới → cũ) để soi/kiểm kho."""
        with self._lock:
            rows = self._con.execute(
                "SELECT id,ts,kind,kg,batch_id,note,user FROM lot_movements"
                " WHERE lot_id=? ORDER BY id DESC LIMIT ?", (_i(lot_id), _i(n, 200))
            ).fetchall()
        return [dict(r) for r in rows]

    # ══ PHỄU — "lô đang mở" (§3.1#2) ═══════════════════════════════════════
    def hopper_lot(self, hopper=1):
        with self._lock:
            row = self._con.execute(
                "SELECT lot_id FROM hoppers WHERE id=?", (_i(hopper, 1),)).fetchone()
        return row["lot_id"] if row else None

    def hopper_set(self, lot_id, hopper=1, user=""):
        """Gán lô đang mở cho phễu (đổ bao mới). lot_id=None → tháo lô."""
        lot_id = _i(lot_id) if lot_id not in (None, "", 0, "0") else None
        try:
            with self._lock:
                self._con.execute(
                    "INSERT INTO hoppers(id,lot_id,opened_at,opened_by) VALUES(?,?,?,?) "
                    "ON CONFLICT(id) DO UPDATE SET lot_id=excluded.lot_id,"
                    " opened_at=excluded.opened_at, opened_by=excluded.opened_by",
                    (_i(hopper, 1), lot_id, _now(), str(user)[:40]))
                self._con.commit()
            self._log("[KHO] phễu %s → lô #%s", hopper, lot_id)
            return {"ok": True, "lot_id": lot_id}
        except Exception as e:
            return {"ok": False, "err": str(e)}

    # ══ TRỪ KHO THEO MẺ — bằng CÂN THẬT (§3.1#1) ═══════════════════════════
    def consume_batch(self, batch_id, kg, lot_id=None, hopper=1, user=""):
        """Trừ kho cho một mẻ. kg = KG ĐÃ CÂN thật (netW từ đầu cân máy) — không
        có cân thì lớp Api truyền MACHINE_BATCH_KG danh định. Lô = lô đang mở của
        phễu nếu không chỉ định. Idempotent theo batch_id (gọi đúp app+web →
        không trừ 2 lần)."""
        kg = _f(kg)
        if kg <= 0:
            return {"ok": False, "err": "kg đã cân phải > 0"}
        if lot_id in (None, "", 0, "0"):
            lot_id = self.hopper_lot(hopper)
        if not lot_id:
            return {"ok": False, "err": "phễu chưa gán lô đang mở"}
        bid = _i(batch_id)
        try:
            with self._lock:
                if bid:
                    ex = self._con.execute(
                        "SELECT 1 FROM lot_movements WHERE batch_id=? AND kind='me' LIMIT 1",
                        (bid,)).fetchone()
                    if ex:
                        bal = self._con.execute(
                            "SELECT COALESCE(SUM(kg),0) FROM lot_movements WHERE lot_id=?",
                            (_i(lot_id),)).fetchone()[0]
                        return {"ok": True, "skipped": True, "so_du": round(bal, 3)}
                self._con.execute(
                    "INSERT INTO lot_movements(lot_id,ts,kind,kg,batch_id,note,user)"
                    " VALUES(?,?, 'me', ?, ?, ?, ?)",
                    (_i(lot_id), _now(), -abs(kg), bid or None,
                     "trừ theo mẻ (cân thật)", str(user)[:40]))
                self._con.commit()
            self._log("[KHO] mẻ #%s trừ lô #%s: %.2fkg", batch_id, lot_id, kg)
            return {"ok": True, "lot_id": lot_id, "so_du": self.lot_balance(lot_id)}
        except Exception as e:
            self._log("[KHO] trừ theo mẻ lỗi: %s", e)
            return {"ok": False, "err": str(e)}

    # ══ ĐƠN HÀNG / KẾ HOẠCH SX (§3 #44) ════════════════════════════════════
    def order_add(self, d):
        d = d if isinstance(d, dict) else {}
        try:
            with self._lock:
                cur = self._con.execute(
                    "INSERT INTO orders(code,customer,product,prof_no,qty_kg,"
                    "due_date,status,note,created_at) VALUES(?,?,?,?,?,?, 'open', ?,?)",
                    (str(d.get("code") or "")[:24], str(d.get("customer") or "")[:80],
                     str(d.get("product") or "")[:80], _i(d.get("prof_no")),
                     _f(d.get("qty_kg")), str(d.get("due_date") or "")[:10],
                     str(d.get("note") or "")[:200], _now()))
                self._con.commit()
            return {"ok": True, "id": cur.lastrowid}
        except Exception as e:
            return {"ok": False, "err": str(e)}

    def order_set(self, order_id, d):
        d = d if isinstance(d, dict) else {}
        cols = ("code", "customer", "product", "prof_no", "qty_kg", "roasted_kg",
                "due_date", "status", "note")
        sets, vals = [], []
        for c in cols:
            if c in d:
                if c == "status" and str(d[c]) not in ("open", "done", "cancel"):
                    continue                       # chặn trạng thái rác
                sets.append(f"{c}=?")
                v = _f(d[c]) if c in ("qty_kg", "roasted_kg") else (
                    _i(d[c]) if c == "prof_no" else str(d[c])[:200])
                vals.append(v)
        if not sets:
            return {"ok": False, "err": "không có gì để sửa"}
        vals.append(_i(order_id))
        try:
            with self._lock:
                self._con.execute(f"UPDATE orders SET {','.join(sets)} WHERE id=?", vals)
                self._con.commit()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "err": str(e)}

    def order_progress(self, prof_no, kg_out):
        """Rang xong 1 mẻ hồ sơ prof_no → cộng vào đơn OPEN gần hạn nhất cùng hồ sơ.
        Tự chuyển 'done' khi đủ. Không có đơn khớp → bỏ qua (rang tự do)."""
        kg_out = _f(kg_out)
        pno = _i(prof_no)
        if kg_out <= 0 or pno <= 0:
            return {"ok": False, "err": "thiếu hồ sơ/kg"}
        try:
            with self._lock:
                row = self._con.execute(
                    "SELECT id,qty_kg,roasted_kg FROM orders WHERE status='open' AND "
                    "prof_no=? ORDER BY (due_date=''), due_date ASC, id ASC LIMIT 1",
                    (pno,)).fetchone()
                if not row:
                    return {"ok": True, "matched": False}
                new_out = _f(row["roasted_kg"]) + kg_out
                done = new_out >= _f(row["qty_kg"]) > 0
                self._con.execute(
                    "UPDATE orders SET roasted_kg=?, status=? WHERE id=?",
                    (round(new_out, 2), "done" if done else "open", row["id"]))
                self._con.commit()
            return {"ok": True, "matched": True, "order_id": row["id"], "done": done}
        except Exception as e:
            return {"ok": False, "err": str(e)}

    def orders_list(self, status=None, n=100):
        q = ("SELECT * FROM orders" + (" WHERE status=?" if status else "") +
             " ORDER BY (due_date=''), due_date ASC, id DESC LIMIT ?")
        args = ((status, _i(n, 100)) if status else (_i(n, 100),))
        with self._lock:
            rows = self._con.execute(q, args).fetchall()
        return [dict(r) for r in rows]

    # ══ CHI PHÍ · HAO HỤT · LỢI NHUẬN (§3 #45) ═════════════════════════════
    def cost_config(self):
        with self._lock:
            rows = self._con.execute("SELECT k,v FROM biz_config").fetchall()
        return {r["k"]: r["v"] for r in rows}

    def cost_config_set(self, cfg):
        cfg = cfg if isinstance(cfg, dict) else {}
        try:
            with self._lock:
                for k, v in cfg.items():
                    self._con.execute(
                        "INSERT INTO biz_config(k,v) VALUES(?,?) "
                        "ON CONFLICT(k) DO UPDATE SET v=excluded.v", (str(k), str(v)))
                self._con.commit()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "err": str(e)}

    def batch_economics(self, batch_id, drop_sec=None, kg_out=None):
        """Kinh tế 1 mẻ: hao hụt (shrinkage) + giá thành + lợi nhuận.

        kg_vào  = kg đã trừ kho cho mẻ (ledger 'me'); không có → None.
        kg_ra   = kg_out truyền vào (cân sau rang) — chưa cân thì suy từ hao hụt
                  không tính được, trả shrink=None.
        Giá thành = nhân (kg_vào×cost_per_kg lô) + gas (giờ×đơn giá) + công + điện.
        Lợi nhuận = kg_ra×giá bán − giá thành (chỉ khi đủ dữ liệu)."""
        bid = _i(batch_id)
        cfg = self.cost_config()
        with self._lock:
            mv = self._con.execute(
                "SELECT lot_id, -SUM(kg) kin FROM lot_movements "
                "WHERE batch_id=? AND kind='me' GROUP BY lot_id", (bid,)).fetchone()
        kg_in = round(mv["kin"], 3) if mv and mv["kin"] else None
        lot_id = mv["lot_id"] if mv else None
        cost_green = None
        if kg_in and lot_id:
            with self._lock:
                lr = self._con.execute(
                    "SELECT cost_per_kg FROM lots WHERE id=?", (lot_id,)).fetchone()
            if lr and _f(lr["cost_per_kg"]) > 0:
                cost_green = kg_in * _f(lr["cost_per_kg"])
        # gas theo thời gian mẻ (đơn giá VND/giờ)
        gas_gio = _f(cfg.get("gas_vnd_gio"))
        cost_gas = (gas_gio * (_f(drop_sec) / 3600.0)) if (gas_gio > 0 and drop_sec) else 0.0
        cost_cong = _f(cfg.get("cong_vnd_me"))
        cost_dien = _f(cfg.get("dien_vnd_me"))
        gia_thanh = None
        if cost_green is not None:
            gia_thanh = round(cost_green + cost_gas + cost_cong + cost_dien, 0)
        # hao hụt
        kg_out = _f(kg_out) if kg_out not in (None, "") else None
        shrink = None
        if kg_in and kg_out and kg_out > 0:
            shrink = round((kg_in - kg_out) / kg_in * 100, 1)
        # lợi nhuận
        gia_ban = _f(cfg.get("gia_ban_vnd_kg"))
        loi_nhuan = None
        if gia_thanh is not None and kg_out and gia_ban > 0:
            loi_nhuan = round(kg_out * gia_ban - gia_thanh, 0)
        return {"kg_in": kg_in, "kg_out": kg_out, "lot_id": lot_id,
                "shrink_pct": shrink, "cost_green": None if cost_green is None else round(cost_green, 0),
                "cost_gas": round(cost_gas, 0), "cost_cong": cost_cong, "cost_dien": cost_dien,
                "gia_thanh": gia_thanh, "loi_nhuan": loi_nhuan, "tien_te": cfg.get("tien_te", "VND")}

    # ══ CUPPING (§3.2) — nối RANG↔CUP là giá trị lõi ══════════════════════
    def cup_add(self, d):
        d = d if isinstance(d, dict) else {}
        target = str(d.get("target") or "batch")
        if target not in ("lot", "batch", "profile"):
            return {"ok": False, "err": "target phải là lot/batch/profile"}
        flavors = d.get("flavors")
        try:
            with self._lock:
                cur = self._con.execute(
                    "INSERT INTO cuppings(target,target_id,tier,stars,score,defects,"
                    "flavors,notes,cupper,blind_code,cupped_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (target, _i(d.get("target_id")), _i(d.get("tier"), 1) or 1,
                     _f(d.get("stars")), _f(d.get("score")),
                     str(d.get("defects") or "")[:120],
                     json.dumps(flavors, ensure_ascii=False) if isinstance(flavors, list) else "[]",
                     str(d.get("notes") or "")[:400], str(d.get("cupper") or "")[:40],
                     str(d.get("blind_code") or "")[:24], _now()))
                self._con.commit()
            return {"ok": True, "id": cur.lastrowid}
        except Exception as e:
            return {"ok": False, "err": str(e)}

    # ══ GĐ5 — BÁO CÁO ĐIỀU HÀNH XƯỞNG ═════════════════════════════════════
    # Biến dữ liệu GĐ4 thành QUYẾT ĐỊNH (offline, không hạ tầng ngoài). Tổng hợp
    # trên chính bảng batches (rang) + ledger (kho) + orders + biz_config.
    def workshop_report(self, days=7):
        """Ảnh chụp xưởng N ngày gần nhất: sản lượng · tồn kho (quy MẺ) · lô sắp
        hết · đơn tới hạn · lãi gộp ƯỚC TÍNH. Số nào thiếu dữ liệu → None/ước tính,
        KHÔNG bịa."""
        import datetime
        days = _i(days, 7) or 7
        since = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
        cfg = self.cost_config()
        me_kg = _f(cfg.get("me_kg_dinh_muc"), 6.0) or 6.0
        shrink = _f(cfg.get("hao_hut_dinh_muc_pct"), 15.0)
        gia_ban = _f(cfg.get("gia_ban_vnd_kg"))
        gas_gio = _f(cfg.get("gas_vnd_gio"))
        cong = _f(cfg.get("cong_vnd_me"))
        dien = _f(cfg.get("dien_vnd_me"))
        with self._lock:
            # sản lượng: mẻ DONE có điểm thật trong kỳ + tổng giây rang
            b = self._con.execute(
                "SELECT COUNT(*) n, COALESCE(SUM(drop_sec),0) sec FROM batches "
                "WHERE status='DONE' AND live=1 AND date(ended_at)>=?", (since,)).fetchone()
            # kho tiêu thụ trong kỳ (ledger 'me') + giá vốn nhân đã dùng
            g = self._con.execute(
                "SELECT COALESCE(-SUM(m.kg),0) kg, "
                " COALESCE(SUM(-m.kg*COALESCE(l.cost_per_kg,0)),0) cost "
                "FROM lot_movements m LEFT JOIN lots l ON l.id=m.lot_id "
                "WHERE m.kind='me' AND date(m.ts)>=?", (since,)).fetchone()
            # tồn kho tổng (mọi lô còn dùng)
            ton = self._con.execute(
                "SELECT COALESCE(SUM(kg),0) FROM lot_movements WHERE lot_id IN "
                "(SELECT id FROM lots WHERE active=1)").fetchone()[0]
            # đơn còn mở + đơn tới hạn trong kỳ (hoặc quá hạn)
            due = self._con.execute(
                "SELECT COUNT(*) FROM orders WHERE status='open' AND due_date!='' "
                "AND due_date<=?", ((datetime.date.today()+datetime.timedelta(days=days)).isoformat(),)
            ).fetchone()[0]
            open_orders = self._con.execute(
                "SELECT COUNT(*) FROM orders WHERE status='open'").fetchone()[0]
        batches_done = b["n"]
        green_kg = round(g["kg"], 2)
        green_cost = g["cost"]
        # sản lượng thành phẩm ước tính (chưa cân ra) + lãi gộp ước tính
        kg_out_est = round(green_kg * (1 - shrink / 100.0), 2)
        profit_est = None
        if gia_ban > 0 and green_cost > 0:
            gas_cost = gas_gio * (b["sec"] / 3600.0)
            total_cost = green_cost + gas_cost + (cong + dien) * batches_done
            profit_est = round(kg_out_est * gia_ban - total_cost, 0)
        lots = self.lots_overview(me_kg)
        low = [{"name": l["name"], "code": l["code"], "con_me": l["con_me"],
                "so_du_kg": l["so_du_kg"]}
               for l in lots if l["con_me"] is not None and l["con_me"] <= 2]
        return {
            "days": days,
            "batches_done": batches_done,
            "green_kg": green_kg,
            "kg_out_est": kg_out_est,
            "ton_kho_kg": round(ton, 1),
            "ton_kho_me": round(ton / me_kg, 1) if me_kg else None,
            "active_lots": len(lots),
            "lots_low": low,
            "orders_open": open_orders,
            "orders_due": due,
            "profit_est": profit_est,
            "tien_te": cfg.get("tien_te", "VND"),
        }

    def cup_list(self, target=None, target_id=None, n=100):
        q = "SELECT * FROM cuppings"
        args, where = [], []
        if target:
            where.append("target=?"); args.append(str(target))
        if target_id is not None:
            where.append("target_id=?"); args.append(_i(target_id))
        if where:
            q += " WHERE " + " AND ".join(where)
        q += " ORDER BY id DESC LIMIT ?"; args.append(_i(n, 100))
        with self._lock:
            rows = self._con.execute(q, args).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            try:
                d["flavors"] = json.loads(d.get("flavors") or "[]")
            except Exception:
                d["flavors"] = []
            out.append(d)
        return out


def _days_between(a, b):
    """Số ngày giữa 2 chuỗi 'YYYY-MM-DD' (b−a). Lỗi → None."""
    import datetime
    try:
        da = datetime.date.fromisoformat(str(a)[:10])
        db = datetime.date.fromisoformat(str(b)[:10])
        return (db - da).days
    except Exception:
        return None
