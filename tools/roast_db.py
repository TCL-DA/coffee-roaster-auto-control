"""
Kho mẻ rang SQLite — KHÔNG MẤT MẺ (GĐ1, §16.2 ref-roast-lab-hmi-architecture).

Mỗi mẻ là bản ghi kinh doanh: mất điện chớp nhoáng là cơm bữa ở xưởng nên file
phải power-safe. Ba lớp bảo vệ:
  1. WAL + synchronous=NORMAL — rớt điện giữa chừng DB không hỏng, mất tối đa
     giao dịch cuối chưa checkpoint (≤1 giây dữ liệu).
  2. quick_check lúc mở — file hỏng thật (SD/ổ cứng lỗi) thì ĐỔI TÊN giữ lại
     (batches.hong-*.db) rồi tạo DB mới, không bao giờ ghi đè lên bằng chứng.
  3. Backup ngày (sqlite3 backup API) vào backup/, giữ 14 bản gần nhất.

Mẻ đang RUNNING mà app chết (kill/chớp điện) → lần mở sau tự chốt thành
INTERRUPTED, giờ xả + nhiệt xả lấy từ ĐIỂM CUỐI đã ghi — curve còn nguyên tới
giây cuối, đúng nghĩa "không mất mẻ".

Ai ghi gì:
  - Python (roast_lab_hmi._snap_bridge) tự ghi ĐIỂM curve mỗi giây từ snapshot
    máy — UI có treo thì điểm vẫn vào DB.
  - JS chỉ báo đầu mẻ (meta hồ sơ) + cuối mẻ (mã mẻ, tổng kết) qua Api.

Thuần stdlib (sqlite3), dùng chung một kết nối + khoá cho mọi luồng.
"""

import json
import os
import sqlite3
import threading
import time

DB_NAME = "batches.db"
BACKUP_DIR = "backup"
BACKUP_KEEP = 14          # giữ 14 bản backup ngày gần nhất

_SCHEMA = """
CREATE TABLE IF NOT EXISTS batches(
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  code       TEXT    DEFAULT '',          -- mã mẻ (#B-0420) — JS đặt lúc chốt
  prof_no    INTEGER DEFAULT 0,           -- số hồ sơ (1-based, 0 = không rõ)
  prof_name  TEXT    DEFAULT '',
  color      TEXT    DEFAULT '',
  roaster    TEXT    DEFAULT '',          -- tên thợ đang đăng nhập
  started_at TEXT    NOT NULL,            -- 'YYYY-MM-DD HH:MM:SS' giờ máy tính
  ended_at   TEXT,
  drop_sec   INTEGER,                     -- giây xả (đồng hồ mẻ)
  drop_temp  REAL,                        -- BT lúc xả
  dev_pct    INTEGER,                     -- % phát triển
  mile       TEXT    DEFAULT '{}',        -- JSON {"TP":{"t":94,"bt":91.2},...}
  live       INTEGER DEFAULT 0,           -- 1 = có điểm từ máy thật, 0 = mô phỏng
  status     TEXT    DEFAULT 'RUNNING'    -- RUNNING | DONE | INTERRUPTED
);
CREATE TABLE IF NOT EXISTS points(
  batch_id INTEGER NOT NULL,
  t        INTEGER NOT NULL,              -- giây thứ t của mẻ (1 điểm/giây)
  bt REAL, et REAL, ror REAL, gas REAL, air REAL, drum REAL,
  PRIMARY KEY(batch_id, t)
) WITHOUT ROWID;
"""


def _now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


class RoastDb:
    """Một kết nối SQLite dùng chung mọi luồng (khoá riêng), WAL, tự hồi phục."""

    def __init__(self, base_dir, log=None):
        self.base = base_dir
        self.path = os.path.join(base_dir, DB_NAME)
        self._log = log or (lambda *a: None)      # log(fmt, *args) kiểu logging
        self._lock = threading.Lock()
        self._con = None
        os.makedirs(base_dir, exist_ok=True)
        self._open()

    # ── mở / kiểm tra / hồi phục ────────────────────────────────────────────
    def _connect(self):
        con = sqlite3.connect(self.path, check_same_thread=False, timeout=5)
        try:
            con.row_factory = sqlite3.Row
            con.execute("PRAGMA journal_mode=WAL")
            con.execute("PRAGMA synchronous=NORMAL")
        except Exception:
            con.close()      # Windows: không đóng là file bị khoá, hết đổi tên được
            raise
        return con

    def _open(self):
        try:
            con = self._connect()
            ok = con.execute("PRAGMA quick_check").fetchone()[0]
            if ok != "ok":
                raise sqlite3.DatabaseError("quick_check: " + str(ok))
        except sqlite3.DatabaseError as e:
            # File hỏng thật — giữ lại làm bằng chứng, tạo DB mới rỗng
            self._log("[DB] batches.db HỎNG (%s) — đổi tên giữ lại, tạo mới", e)
            try:
                con.close()
            except Exception:
                pass
            stamp = time.strftime("%Y%m%d-%H%M%S")
            for suf in ("", "-wal", "-shm"):
                p = self.path + suf
                if os.path.exists(p):
                    os.replace(p, os.path.join(
                        self.base, f"batches.hong-{stamp}.db{suf}"))
            con = self._connect()
        con.executescript(_SCHEMA)
        con.commit()
        self._con = con
        self._recover()

    def _recover(self):
        """Mẻ còn RUNNING từ phiên trước = app chết giữa mẻ → chốt INTERRUPTED
        bằng điểm cuối đã ghi. Curve giữ nguyên tới giây cuối cùng."""
        with self._lock:
            self._close_running_locked(reason="dở dang từ phiên trước")
            # điểm mồ côi (mẻ đã xoá mà điểm lọt khe race) — dọn một lần lúc mở
            self._con.execute(
                "DELETE FROM points WHERE batch_id NOT IN (SELECT id FROM batches)")
            self._con.commit()

    # ── vòng đời mẻ ─────────────────────────────────────────────────────────
    def begin(self, meta=None):
        """Mở mẻ mới, trả id. Mẻ RUNNING cũ (nếu còn) chốt INTERRUPTED trước."""
        meta = meta if isinstance(meta, dict) else {}
        with self._lock:
            self._close_running_locked()
            cur = self._con.execute(
                "INSERT INTO batches(prof_no, prof_name, color, roaster, started_at)"
                " VALUES(?,?,?,?,?)",
                (int(meta.get("no") or 0), str(meta.get("name") or "")[:80],
                 str(meta.get("color") or "")[:16],
                 str(meta.get("roaster") or "")[:40], _now()))
            self._con.commit()
            return cur.lastrowid

    def point(self, bid, d):
        """Ghi 1 điểm curve (poll 8Hz gọi thoải mái — PK (batch_id,t) tự khử trùng)."""
        t = d.get("t_roast")
        if bid is None or t is None:
            return
        with self._lock:
            c = self._con.execute(
                "INSERT OR IGNORE INTO points(batch_id,t,bt,et,ror,gas,air,drum)"
                " VALUES(?,?,?,?,?,?,?,?)",
                (bid, int(t), d.get("bt"), d.get("et"), d.get("ror_bt"),
                 d.get("gas"), d.get("air"), d.get("drum")))
            if c.rowcount:                       # điểm mới thật sự
                self._con.execute(
                    "UPDATE batches SET live=1 WHERE id=? AND live=0", (bid,))
                self._con.commit()

    def finish(self, bid, summary=None):
        """Chốt mẻ DONE với tổng kết từ JS (mã mẻ, giây xả, mốc…)."""
        s = summary if isinstance(summary, dict) else {}
        mile = s.get("mile")
        with self._lock:
            self._con.execute(
                "UPDATE batches SET status='DONE', ended_at=?, code=?, "
                "drop_sec=?, drop_temp=?, dev_pct=?, mile=? WHERE id=?",
                (_now(), str(s.get("code") or "")[:16],
                 s.get("drop_sec"), s.get("drop_temp"), s.get("dev_pct"),
                 json.dumps(mile, ensure_ascii=False) if mile else "{}", bid))
            self._con.commit()
        return {"ok": True, "id": bid}

    def close_running(self):
        """Thợ bấm 'Mẻ mới' khi mẻ chưa chốt / app thoát — không để RUNNING mồ côi."""
        with self._lock:
            self._close_running_locked()
            self._con.commit()

    def _close_running_locked(self, reason="đóng mẻ dở"):
        """Mẻ RUNNING có điểm → INTERRUPTED (giữ curve tới giây cuối).
        Mẻ RUNNING RỖNG (bấm Bắt đầu rồi không rang) → XOÁ — không phải bản ghi
        kinh doanh, để lại chỉ rác lịch sử."""
        rows = self._con.execute(
            "SELECT id FROM batches WHERE status='RUNNING'").fetchall()
        for r in rows:
            last = self._con.execute(
                "SELECT t, bt FROM points WHERE batch_id=? ORDER BY t DESC LIMIT 1",
                (r["id"],)).fetchone()
            if last is None:
                self._con.execute("DELETE FROM batches WHERE id=?", (r["id"],))
                self._log("[DB] mẻ #%s rỗng (0 điểm) → xoá", r["id"])
                continue
            self._con.execute(
                "UPDATE batches SET status='INTERRUPTED', ended_at=?, "
                "drop_sec=COALESCE(drop_sec,?), drop_temp=COALESCE(drop_temp,?) "
                "WHERE id=?", (_now(), last["t"], last["bt"], r["id"]))
            self._log("[DB] mẻ #%s %s → INTERRUPTED (giữ curve tới giây %s)",
                      r["id"], reason, last["t"])

    # ── đọc cho UI ──────────────────────────────────────────────────────────
    def latest(self, n=50):
        with self._lock:
            rows = self._con.execute(
                "SELECT id, code, prof_no, prof_name, color, roaster, started_at,"
                " ended_at, drop_sec, drop_temp, dev_pct, mile, live, status"
                " FROM batches ORDER BY id DESC LIMIT ?", (int(n),)).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            try:
                d["mile"] = json.loads(d.get("mile") or "{}")
            except Exception:
                d["mile"] = {}
            out.append(d)
        return out

    def curve(self, bid):
        """Curve 1 mẻ dạng mảng cột (như p.curve của JS) — vẽ/xuất CSV đều dùng."""
        with self._lock:
            rows = self._con.execute(
                "SELECT t, bt, et, ror, gas, air, drum FROM points"
                " WHERE batch_id=? ORDER BY t", (int(bid),)).fetchall()
        cv = {k: [] for k in ("t", "bt", "et", "ror", "gas", "air", "drum")}
        for r in rows:
            for k in cv:
                cv[k].append(r[k])
        return cv

    # ── phân tích mẻ (GĐ3 §18.7): DTR, dev%, AUC, RoR đỉnh ─────────────────
    def stats(self, bid):
        """Thống kê pha từ curve + mốc đã lưu. Mẻ mô phỏng (0 điểm) → None.

        DTR (Development Time Ratio) = thời gian sau FCs / tổng — chỉ số then chốt
        quyết định vị của mẻ. AUC = tích phân (BT − ngưỡng) theo thời gian, đo
        'tổng nhiệt nạp' — dùng so mẻ nhạt/đậm khách quan hơn chỉ nhìn nhiệt xả."""
        with self._lock:
            row = self._con.execute(
                "SELECT mile, drop_sec, drop_temp FROM batches WHERE id=?",
                (int(bid),)).fetchone()
        if not row:
            return None
        cv = self.curve(bid)
        t, bt = cv["t"], cv["bt"]
        if len(t) < 3:
            return None
        try:
            mile = json.loads(row["mile"] or "{}")
        except Exception:
            mile = {}

        def _ms(key):
            m = mile.get(key)
            if isinstance(m, dict):
                return m.get("t")
            return m

        drop_sec = row["drop_sec"] if row["drop_sec"] is not None else t[-1]
        fcs = _ms("FCs")
        tp = _ms("TP")
        de = _ms("DE")
        out = {"total_sec": drop_sec, "drop_temp": row["drop_temp"],
               "tp_sec": tp, "de_sec": de, "fcs_sec": fcs}
        # DTR
        if fcs is not None and drop_sec and drop_sec > 0:
            out["dtr_pct"] = round((drop_sec - fcs) / drop_sec * 100, 1)
        else:
            out["dtr_pct"] = None
        # RoR đỉnh + trung bình pha phát triển (bỏ None do sensor guard chèn)
        rors = [r for r in cv["ror"] if r is not None]
        out["ror_max"] = round(max(rors), 1) if rors else None
        # AUC trên ngưỡng 100°C (tích phân hình thang, đơn vị °C·phút)
        auc = 0.0
        for i in range(1, len(t)):
            dt = (t[i] - t[i - 1]) / 60.0
            b0 = (bt[i - 1] or 0) - 100.0
            b1 = (bt[i] or 0) - 100.0
            auc += max(0.0, (b0 + b1) / 2.0) * dt
        out["auc"] = round(auc, 1)
        # nhiệt đáy TP (điểm quay đầu) nếu mốc có kèm bt
        tpm = mile.get("TP")
        out["tp_temp"] = tpm.get("bt") if isinstance(tpm, dict) else None
        return out

    # ── xuất CSV ────────────────────────────────────────────────────────────
    def export_csv(self, out_dir, bid=None):
        """bid=None → bảng tổng lich-su-me.csv; bid=N → curve 1 mẻ me-N.csv.
        Ghi tạm rồi thay — không bao giờ có file cụt."""
        os.makedirs(out_dir, exist_ok=True)

        def _q(s):
            s = str("" if s is None else s)
            return '"' + s.replace('"', '""') + '"' if any(
                c in s for c in ',"\n') else s

        if bid is None:
            path = os.path.join(out_dir, "lich-su-me.csv")
            out = ("﻿id,ma_me,ho_so,tho_rang,bat_dau,ket_thuc,"
                   "giay_xa,nhiet_xa,phat_trien_pct,may_that,trang_thai\r\n")
            for b in reversed(self.latest(10000)):     # cũ → mới, mở Excel dễ đọc
                out += ",".join([str(b["id"]), _q(b["code"]), _q(b["prof_name"]),
                                 _q(b["roaster"]), _q(b["started_at"]),
                                 _q(b["ended_at"]),
                                 "" if b["drop_sec"] is None else str(b["drop_sec"]),
                                 "" if b["drop_temp"] is None else f"{b['drop_temp']:.1f}",
                                 "" if b["dev_pct"] is None else str(b["dev_pct"]),
                                 "CO" if b["live"] else "KHONG",
                                 b["status"]]) + "\r\n"
        else:
            with self._lock:
                row = self._con.execute(
                    "SELECT code, prof_name FROM batches WHERE id=?",
                    (int(bid),)).fetchone()
            if not row:
                return {"ok": False, "err": f"không có mẻ #{bid}"}
            cv = self.curve(bid)
            if not cv["t"]:
                return {"ok": False, "err": "mẻ này không có curve (mô phỏng?)"}
            code = (row["code"] or f"me-{bid}").lstrip("#").replace("/", "-")
            path = os.path.join(out_dir, f"{code}.csv")
            out = "﻿giay,bt,et,ror,gas,air,drum\r\n"
            for i, t in enumerate(cv["t"]):
                out += ",".join(
                    "" if v is None else (f"{v:.1f}" if isinstance(v, float) else str(v))
                    for v in (t, cv["bt"][i], cv["et"][i], cv["ror"][i],
                              cv["gas"][i], cv["air"][i], cv["drum"][i])) + "\r\n"
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="") as f:
            f.write(out)
        os.replace(tmp, path)
        return {"ok": True, "path": path}

    # ── backup ngày ─────────────────────────────────────────────────────────
    def backup_daily(self):
        """Mỗi ngày 1 bản backup/batches-YYYYMMDD.db (sqlite backup API — an toàn
        khi đang ghi). Đã có bản hôm nay thì thôi. Giữ BACKUP_KEEP bản gần nhất."""
        bdir = os.path.join(self.base, BACKUP_DIR)
        os.makedirs(bdir, exist_ok=True)
        dst = os.path.join(bdir, "batches-" + time.strftime("%Y%m%d") + ".db")
        if os.path.exists(dst):
            return {"ok": True, "path": dst, "skipped": True}
        try:
            with self._lock:
                out = sqlite3.connect(dst)
                self._con.backup(out)
                out.close()
            olds = sorted(f for f in os.listdir(bdir)
                          if f.startswith("batches-") and f.endswith(".db"))
            for f in olds[:-BACKUP_KEEP]:
                os.remove(os.path.join(bdir, f))
            self._log("[DB] backup ngày → %s", dst)
            return {"ok": True, "path": dst}
        except Exception as e:
            self._log("[DB] backup THẤT BẠI: %s", e)
            return {"ok": False, "err": str(e)}

    def close(self):
        with self._lock:
            try:
                self._con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                self._con.close()
            except Exception:
                pass
