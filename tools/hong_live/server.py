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
    ("ghi", "Ghi giản đồ",r"(?i)artisan(?!/profile)|\.alog"),
    ("dubao", "Dự báo", r"ban_sao|mpc|hong_de3|giai_de|du_bao|dự báo|monte"),
    ("phantich", "Phân tích", r"phan_tich|ve_k|gian_do|\.png|cham|k_david|matplotlib"),
    ("doc", "Đọc máy", r"hmi_dien\.py doc|doc_man|log\.csv|trang_thai|quan_sat|Modbus|\$60|đọc"),
    ("nho", "Ghi nhớ · Git", r"(?i)memory|otl-hong\.md|git |nhat_ky|nhật ký|\.md"),
]
NHOM_KHAC = ("tra", "Tra cứu · Code")
LOI = re.compile(r"TỪ CHỐI|Traceback|Exit code [1-9]|⛔|Error|lỗi", re.I)

# ---- GIẤU DỮ LIỆU NỘI BỘ (anh Thành 17/10/2026) ----
# Mọi chữ gửi ra trình duyệt đi qua đây. Không gửi lệnh, đường dẫn, tên tệp, kết quả lệnh, thanh ghi, IP, cổng COM,
# tên khách, tên phần mềm / nguồn tham khảo, thuật toán điều khiển. Việc Hồng làm chỉ hiện tên NHÓM việc.
NHAN_NHOM = {"hmi": "Thao tác trên màn hình máy", "ghi": "Ghi giản đồ mẻ", "dubao": "Tính dự báo nhiệt",
             "phantich": "Phân tích số liệu", "doc": "Đọc số máy", "nho": "Ghi nhớ bài học", "tra": "Tra cứu, chuẩn bị"}
_GIAU = [
    (r"`[^`]*`", ""),
    (r"https?://\S+|\S+@\S+\.\w+", ""),
    (r"(?i)\b[a-z]:[\\/]\S*", ""),                                      # đường dẫn Windows
    (r"(?:[\w.-]+/){2,}[\w.-]*|\w+(?:\\[\w.-]+)+", ""),                # đường dẫn a/b/c, a\b (°C/ph giữ nguyên)
    (r"(?i)[\w.-]*\.(?:py|md|json|jsonl|csv|txt|alog|html?|js|ps1|h|cpp|ini|png|jpe?g|pdf|xlsx?|dpa|exe)\b", ""),
    (r"\b\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?\b", ""),                      # IP
    (r"(?i)\bCOM\d+\b", "cổng"),
    (r"\$[A-Z]?\d+(?:\s*=\s*\d+)?|\b[WD]?4\d{4}\b|\bidx\s*\d+", ""),   # thanh ghi, chỉ số
    (r"\(?\b\d{2,4},\d{2,4},\d{2,4},\d{2,4}\)?(?:\[\d+x\d+\])?", ""),   # toạ độ màn hình
    (r"\+?84\d{8,10}\b|\b0\d{9,10}\b", ""),                             # số điện thoại
    (r"\b(anh|chị|chú|cô|bác)\s+[A-ZĐ][a-zà-ỹ]+(?:\s+[A-ZĐ][a-zà-ỹ]+)*", r"\1"),   # tên người / khách
    (r"(?i)\bartisan\b", "bộ ghi giản đồ"),
    (r"(?i)\s*\(?\b(?:david|rao|hoos|münchow|munchow|probat|mill city|hollifield|norman|giesen|loring|cropster)\b\)?", ""),
    (r"\bMPC\b", "bộ dự báo"), (r"\bPID\b", "bộ điều khiển"), (r"\bFF\b|feed-forward", "lịch nhiệt"),
    (r"\bSV\s*\d+(?:\.\d+)?", ""), (r"\bVX4\b", ""), (r"(?i)\b(?:modbus|uia|firmware|slot\s*\d+)\b", ""),
    (r"\b(?:HONG|KG|HONG_\w+)\s*=?\s*[\d.+-]*", ""), (r"d̂\s*-?[\d.,]+|d̂0?", ""),
]
_GIAU = [(re.compile(a), b) for a, b in _GIAU]
_BO_DONG = re.compile(r"^\s*(?:\||```|\$ |>|#|python|git |cd |-{3,})")


def giau(s, toi_da=240):
    """Chữ an toàn cho web: bỏ dòng mã/bảng, lọc chuỗi nội bộ, cắt ngắn."""
    s = re.sub(r"\[SYSTEM NOTIFICATION.*", "", str(s or ""), flags=re.S)
    dong = [d for d in s.splitlines() if d.strip() and not _BO_DONG.match(d)]
    s = " ".join(dong)
    for rx, thay in _GIAU:
        s = rx.sub(thay, s)
    s = re.sub(r"\*\*|__", "", s)
    s = re.sub(r"\s+([,.;:)])", r"\1",re.sub(r"\(\s*\)|\[\s*\]", "", s))
    s = re.sub(r"(?:\s*·\s*){2,}", " · ", re.sub(r"\s{2,}", " ", s)).strip(" ·,;:")
    return s if len(s) <= toi_da else s[:toi_da - 1].rstrip() + "…"


def ten_me(thu_muc):
    m = re.match(r"me_ho_so_(\d+)_(\d\d)(\d\d)", thu_muc or "")
    if m:
        return "Mẻ %s · %s/%s" % (m.group(1), m.group(2), m.group(3))
    m = re.search(r"_(\d\d)(\d\d)", thu_muc or "")
    return "Mẻ thử" + (" · %s/%s" % (m.group(1), m.group(2)) if m else "")


_MOC = re.compile(r"^(\d\d:\d\d:\d\d) MỐC (CHARGE|TP|DE|FCs|DROP)\b\s*([\d:]*)[^·]*·\s*BT(?: charge)?\s*([\d.]+)")
_LENH = re.compile(r"^(\d\d:\d\d:\d\d) LỆNH Hồng: (.*?)(?: · lúc ([\d:]+))?(?: · BT|$)")


def nhat_ky_me(dong):
    """Nhật ký mẻ cho web: chỉ mốc + các lần Hồng chỉnh nhiệt / gió (bỏ dòng thuật toán, tệp, nút bấm)."""
    ra = []
    for d in dong:
        m = _MOC.match(d)
        if m:
            ra.append("%s · Mốc %s%s · BT %s °C" % (m.group(1), m.group(2), (" " + m.group(3)) if m.group(3) else "", m.group(4)))
            continue
        m = _LENH.match(d)
        if m:
            viec = m.group(2).replace("Lệnh 1→0", "tắt nhiệt").replace("Lệnh 0→1", "bật nhiệt")
            ra.append("%s · Hồng chỉnh %s%s" % (m.group(1), giau(viec, 80), (" · giờ rang " + m.group(3)) if m.group(3) else ""))
            continue
        if "ĐÃ BẮT ĐẦU MẺ" in d:
            ra.append(d[:8] + " · Bắt đầu mẻ")
    return ra


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
                if s and not s.startswith(("<", "[SYSTEM", "Base directory for this skill")) and "task-notification" not in s:
                    # lời giao việc chứa đủ thứ nội bộ ⇒ web chỉ biết là có việc mới, không hiện nội dung
                    ev.append({"ts": ts, "loai": "lenh", "nhom": "lenh", "nhan": "Nhận việc mới", "tt": "xong"})
                continue
            for x in c or []:
                if isinstance(x, dict) and x.get("type") == "tool_result" and x.get("tool_use_id") in theo_id:
                    e = theo_id[x["tool_use_id"]]
                    kq = _chu(x.get("content"))
                    e["tt"] = "loi" if (x.get("is_error") or LOI.search(kq[:400])) else "xong"
                    e["ts_xong"] = ts
        elif loai == "assistant":
            for x in c or []:
                if not isinstance(x, dict):
                    continue
                if x.get("type") == "text" and x.get("text", "").strip():
                    s = giau(x["text"])
                    if s:
                        ev.append({"ts": ts, "loai": "nghi", "nhom": "nghi", "nhan": s, "tt": "can_nhac"})
                elif x.get("type") == "tool_use":
                    inp = x.get("input") or {}
                    nhan = _nhan(inp, x.get("name", "?"))
                    goc = " ".join(str(inp.get(k, "")) for k in ("command", "file_path", "pattern", "path")) \
                        if isinstance(inp, dict) else ""   # phân nhóm theo lệnh / file, không theo nội dung sửa
                    nhom = _nhom(nhan + " " + goc[:800])
                    e = {"ts": ts, "loai": "lam", "nhom": nhom, "nhan": NHAN_NHOM.get(nhom, "Làm việc"), "tt": "dang_lam"}
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
    for e in ev:
        e.pop("ts_xong", None)
    return {"tuoi_s": round(tuoi), "trang_thai": tt, "su_kien": ev[-SO_SU_KIEN:]}


def _so(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v and abs(v) != float("inf") else None   # NaN / inf làm hỏng JSON của trình duyệt


def _csv(p, so_dong=None):
    """Đọc CSV có tiêu đề -> list dict (so_dong: chỉ lấy N dòng cuối)."""
    if not os.path.exists(p):
        return []
    try:
        hang = open(p, encoding="utf-8", errors="ignore").read().splitlines()
    except OSError:
        return []
    if len(hang) < 2:
        return []
    dau = hang[0].split(",")
    than = hang[1:] if so_dong is None else hang[-so_dong:]
    return [r for r in csv.DictReader(than, fieldnames=dau) if r.get(dau[0]) != dau[0]]


# cột log gửi cho giản đồ: t, bt, et, buồng, RoR BT, (ô 5 bỏ trống — hệ số nội bộ không gửi), nhiệt thực, gió thực, trống Hz, nhiệt đặt
COT_LOG = ("t_rang", "bt", "et", "buong", "ror_bt", "_khong_gui", "nhiet", "gio_pv", "trong_hz", "dat_nhiet")
# cột phân tích gửi cho ô số (chỉ những cột trang dùng)
COT_PT = ("det", "auc", "dtr_pct", "dev_s", "dry_pct", "ramp_pct", "dry_s", "ramp_s",
          "du_bao_fcs", "lech_fcs", "du_bao_drop", "lech_drop")


def doc_me():
    tt = sorted(glob.glob(os.path.join(ME_GOC, "*", "trang_thai.txt")), key=os.path.getmtime)
    if not tt:
        return {}
    thu_muc = os.path.dirname(tt[-1])
    try:
        dong = open(tt[-1], encoding="utf-8", errors="ignore").read().splitlines()
    except OSError:
        dong = []
    lp = os.path.join(thu_muc, "log.csv")
    hang = _csv(lp)
    trong_me = [r for r in hang if (r.get("t_rang") or "").strip()]
    nguon = trong_me if trong_me else hang[-SO_DIEM_LOG:]          # chưa charge: lấy đoạn chờ gần nhất
    log = [[_so(r.get(c)) for c in COT_LOG] for r in nguon]
    if not trong_me:
        for i, r in enumerate(log):
            r[0] = i - len(log)                                        # giây âm = trước charge
    cuoi = {}
    if hang:
        r = hang[-1]
        cuoi = {"gio": r.get("gio"), "t": _so(r.get("t_rang")), "bt": _so(r.get("bt")), "et": _so(r.get("et")),
                "buong": _so(r.get("buong")), "ror": _so(r.get("ror_bt")),
                "nhiet": _so(r.get("nhiet")), "dat_nhiet": _so(r.get("dat_nhiet")), "gio_pv": _so(r.get("gio_pv")),
                "trong_hz": _so(r.get("trong_hz")), "lenh": _so(r.get("lenh"))}
    try:
        moc = json.load(open(os.path.join(thu_muc, "moc.json"), encoding="utf-8"))
    except (OSError, ValueError):
        moc = {}
    pt = _csv(os.path.join(thu_muc, "phan_tich_3s.csv"), 1)
    mpc = _csv(os.path.join(thu_muc, "mpc.csv"))
    duong_dich = [[_so(r.get("t_rang")), _so(r.get("bt_ref"))] for r in mpc[::3]]
    mc = mpc[-1] if mpc else {}
    moc = {k: moc[k] for k in ("moc_giay", "moc_bt", "dich") if k in moc}   # bỏ ngưỡng nội bộ, giờ máy
    return {"ten": ten_me(os.path.basename(thu_muc)), "dong": nhat_ky_me(dong)[-60:], "log": log, "cuoi": cuoi, "moc": moc,
            "pt": {k: _so(v) for k, v in (pt[-1].items() if pt else []) if k in COT_PT},
            "duong_dich": duong_dich,
            "du_bao": {"t": _so(mc.get("t_rang")), "bt60": _so(mc.get("bt_du_bao_60")),
                       "bt120": _so(mc.get("bt_du_bao_120")), "ref": _so(mc.get("bt_ref"))} if mc else {},
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
            except Exception:  # trang vẫn sống; không gửi chi tiết lỗi (lộ đường dẫn)
                self._gui(500, "application/json; charset=utf-8", json.dumps({"loi": "doc_so"}).encode())
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
