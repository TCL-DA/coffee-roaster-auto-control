# -*- coding: utf-8 -*-
"""Xem LIVE agent OTL Hồng: sơ đồ việc đang làm + số máy (chỉ ĐỌC file, không đụng máy rang / panel).

    python tools/hong_live/server.py [--port 6099]  ->  mở http://127.0.0.1:6099/

Nguồn:
  - nhật ký agent: ~/.claude/projects/<dự án>/<phiên>/subagents/agent-*.jsonl có meta agentType = otl-hong (file mới nhất)
  - mẻ: thư mục mới nhất trong F:/Artisan/Profile/OTL-Hong có trang_thai.txt (trang_thai.txt + log.csv)
Claude Code KHÔNG lưu chữ suy nghĩ (khối thinking rỗng) ⇒ trang hiện việc Hồng làm, câu Hồng viết và số máy Hồng đang dùng.
"""
import csv
import glob
import json
import os
import re
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

NOI = os.path.dirname(os.path.abspath(__file__))
DU_AN = os.path.expanduser(r"~/.claude/projects/f--Project-100-OTL-06ALS---CMS---Cacao")
ME_GOC = r"F:/Artisan/Profile/OTL-Hong"
DUOI_JSONL = 4_000_000    # đọc ~4 MB cuối nhật ký (mỗi dòng có thể rất dài: kết quả lệnh, bản sao yêu cầu)
SO_SU_KIEN = 140
SO_DIEM_LOG = 1200        # 20 phút log 1 Hz cho biểu đồ

NHOM = [  # (khoá, tên, regex trên lệnh / mô tả) — thứ tự = ưu tiên
    ("hmi", "Thao tác HMI", r"co_cau|bat_dau|dat_ten|lam_nong|HONG_DUOC_THAO_TAC|HONG_DUOC_LAI|write_register|\$0 ?=|\$7 ?="),
    ("artisan", "Artisan", r"(?i)artisan(?!/profile)|\.alog"),
    ("mpc", "Dự báo · MPC", r"ban_sao|mpc|hong_de3|giai_de|du_bao|dự báo|monte"),
    ("phantich", "Phân tích", r"phan_tich|ve_k|gian_do|\.png|cham|k_david|matplotlib"),
    ("doc", "Đọc máy", r"hmi_dien\.py doc|doc_man|log\.csv|trang_thai|quan_sat|Modbus|\$60|đọc"),
    ("nho", "Ghi nhớ · Git", r"(?i)memory|otl-hong\.md|git |nhat_ky|nhật ký|\.md"),
]
NHOM_KHAC = ("tra", "Tra cứu · Code")
LOI = re.compile(r"TỪ CHỐI|Traceback|Exit code [1-9]|⛔|Error|lỗi", re.I)


def _file_hong():
    tot, t_tot = None, 0
    for meta in glob.glob(os.path.join(DU_AN, "*", "subagents", "agent-*.meta.json")):
        try:
            if json.load(open(meta, encoding="utf-8")).get("agentType") != "otl-hong":
                continue
        except (OSError, ValueError):
            continue
        j = meta[:-len(".meta.json")] + ".jsonl"
        if os.path.exists(j) and os.path.getmtime(j) > t_tot:
            tot, t_tot = j, os.path.getmtime(j)
    return tot


def _doc_duoi(p, n):
    with open(p, "rb") as f:
        f.seek(0, 2)
        f.seek(max(0, f.tell() - n))
        b = f.read()
    dong = b.decode("utf-8", "ignore").splitlines()
    return dong[1:] if len(b) >= n else dong


def _nhan(inp, ten):
    if not isinstance(inp, dict):
        return ten
    for k in ("description", "summary"):
        if inp.get(k):
            return str(inp[k])
    for k in ("command", "file_path", "pattern", "path"):
        if inp.get(k):
            s = str(inp[k]).replace("\\", "/")
            return (ten + ": " + (os.path.basename(s) if k == "file_path" else s.splitlines()[0]))[:110]
    return ten


def _nhom(chu):
    chu = chu.replace("\\", "/")
    for k, ten, rx in NHOM:
        if re.search(rx, chu):
            return k
    return NHOM_KHAC[0]


def _chu(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(str(x.get("text", "")) if isinstance(x, dict) else str(x) for x in content)
    return ""


def doc_hong():
    p = _file_hong()
    if not p:
        return {"file": None, "su_kien": [], "trang_thai": "không thấy nhật ký Hồng"}
    ev, theo_id = [], {}
    for d in _doc_duoi(p, DUOI_JSONL):
        try:
            d = json.loads(d)
        except ValueError:
            continue
        loai, ts = d.get("type"), d.get("timestamp")
        c = (d.get("message") or {}).get("content")
        if loai == "user":
            if isinstance(c, str) or (isinstance(c, list) and any(x.get("type") == "text" for x in c if isinstance(x, dict))):
                s = _chu(c).strip().replace("The coordinator sent a message while you were working:", "").strip()
                if s and not s.startswith("<") and not s.startswith("Base directory for this skill"):
                    ev.append({"ts": ts, "loai": "lenh", "nhom": "lenh", "nhan": s[:160], "chi_tiet": s[:1500], "tt": "xong"})
                continue
            for x in c or []:
                if isinstance(x, dict) and x.get("type") == "tool_result" and x.get("tool_use_id") in theo_id:
                    e = theo_id[x["tool_use_id"]]
                    kq = _chu(x.get("content"))
                    e["tt"] = "loi" if (x.get("is_error") or LOI.search(kq[:400])) else "xong"
                    e["kq"] = kq[:600]
                    e["ts_xong"] = ts
        elif loai == "assistant":
            for x in c or []:
                if not isinstance(x, dict):
                    continue
                if x.get("type") == "text" and x.get("text", "").strip():
                    s = x["text"].strip()
                    ev.append({"ts": ts, "loai": "nghi", "nhom": "nghi", "nhan": s.splitlines()[0][:160], "chi_tiet": s[:1500], "tt": "can_nhac"})
                elif x.get("type") == "tool_use":
                    inp = x.get("input") or {}
                    nhan = _nhan(inp, x.get("name", "?"))
                    tho = json.dumps(inp, ensure_ascii=False)
                    goc = " ".join(str(inp.get(k, "")) for k in ("command", "file_path", "pattern", "path")) \
                        if isinstance(inp, dict) else ""   # phân nhóm theo lệnh / file, không theo nội dung sửa
                    e = {"ts": ts, "loai": "lam", "nhom": _nhom(nhan + " " + goc[:800]), "nhan": nhan,
                         "chi_tiet": tho[:1200], "tt": "dang_lam", "cong_cu": x.get("name")}
                    theo_id[x.get("id")] = e
                    ev.append(e)
    tuoi = time.time() - os.path.getmtime(p)
    dang = [e for e in ev if e["tt"] == "dang_lam"]
    if dang and tuoi < 900:
        tt = "Đang làm: " + dang[-1]["nhan"]
    elif tuoi < 30:
        tt = "Đang nghĩ / viết"
    else:
        tt = "Rảnh (lần cuối %s trước)" % (("%d s" % tuoi) if tuoi < 120 else ("%d phút" % (tuoi // 60)))
    for e in ev:  # việc cũ chưa có kết quả mà nhật ký đã im lâu ⇒ coi như dừng
        if e["tt"] == "dang_lam" and tuoi >= 900:
            e["tt"] = "xong"
    return {"file": os.path.basename(p), "tuoi_s": round(tuoi), "trang_thai": tt, "su_kien": ev[-SO_SU_KIEN:]}


def _so(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v and abs(v) != float("inf") else None   # NaN / inf làm hỏng JSON của trình duyệt


def doc_me():
    tt = sorted(glob.glob(os.path.join(ME_GOC, "*", "trang_thai.txt")), key=os.path.getmtime)
    if not tt:
        return {}
    thu_muc = os.path.dirname(tt[-1])
    try:
        dong = open(tt[-1], encoding="utf-8", errors="ignore").read().splitlines()
    except OSError:
        dong = []
    log, cuoi = [], {}
    lp = os.path.join(thu_muc, "log.csv")
    if os.path.exists(lp):
        hang = _doc_duoi(lp, 400_000)
        try:
            dau = open(lp, encoding="utf-8", errors="ignore").readline().strip().split(",")
            for r in csv.DictReader(hang[-SO_DIEM_LOG:], fieldnames=dau):
                if r.get(dau[0]) == dau[0]:
                    continue
                log.append([r.get("gio"), _so(r.get("bt")), _so(r.get("et")), _so(r.get("buong")),
                            _so(r.get("ror_bt")), _so(r.get("k_david")), _so(r.get("nhiet")), _so(r.get("t_rang"))])
            if log:
                cuoi = {"gio": log[-1][0], "bt": log[-1][1], "et": log[-1][2], "buong": log[-1][3], "ror": log[-1][4],
                        "k": log[-1][5], "nhiet": log[-1][6], "t": log[-1][7]}
        except (OSError, csv.Error):
            pass
    return {"thu_muc": os.path.basename(thu_muc), "dong": dong[-40:], "log": log, "cuoi": cuoi,
            "tuoi_log_s": round(time.time() - os.path.getmtime(lp)) if os.path.exists(lp) else None}


class XuLy(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _gui(self, ma, kieu, b):
        self.send_response(ma)
        self.send_header("Content-Type", kieu)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path.startswith("/api/state"):
            try:
                b = json.dumps({"hong": doc_hong(), "me": doc_me(), "gio": time.strftime("%H:%M:%S")}, ensure_ascii=False)
                self._gui(200, "application/json; charset=utf-8", b.encode("utf-8"))
            except Exception as e:  # trang vẫn sống, báo lỗi lên màn
                self._gui(500, "application/json; charset=utf-8", json.dumps({"loi": repr(e)}).encode())
            return
        if self.path in ("/", "/index.html"):
            self._gui(200, "text/html; charset=utf-8", open(os.path.join(NOI, "index.html"), "rb").read())
            return
        self._gui(404, "text/plain", b"404")


def main():
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 6099
    # --lan: cho cả xưởng xem (mạng nội bộ). Trang CHỈ ĐỌC — không có đường ghi nào xuống máy rang / panel.
    host = "0.0.0.0" if "--lan" in sys.argv else "127.0.0.1"
    print("Hồng live: http://%s:%d/" % (host, port), flush=True)
    ThreadingHTTPServer((host, port), XuLy).serve_forever()


if __name__ == "__main__":
    main()
