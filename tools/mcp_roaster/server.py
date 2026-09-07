# -*- coding: utf-8 -*-
"""MCP server cho máy rang OTL — TẦNG ĐỌC (T0).

Giai đoạn C của docs/plan/plan-mcp-api-extension.md.

Cho AI ĐỌC máy rang: trạng thái, hồ sơ, lịch sử mẻ, đường cong, tham số $M —
để phân tích mẻ, so hồ sơ, tìm mẻ lệch. KHÔNG có công cụ nào lái máy.

Đây không phải hạn chế tạm thời rồi sau nới ra cho tiện: file này **không có**
đường mã nào gửi lệnh xuống máy. Muốn cho AI lái máy thì phải qua tầng T2 với đủ
5 điều kiện trong kế hoạch (thợ bật tay tại chỗ, lease có hạn, heartbeat, giới hạn
tốc độ đổi, nút dừng cứng) — không phải bằng cách thêm một dòng vào đây.

Chạy:
    set OTL_API_KEY=otl_...        (khoá phạm vi 'read', tạo trong app)
    set OTL_API_BASE=http://127.0.0.1:8555
    python tools/mcp_roaster/server.py

Thuần stdlib, không cần cài gì — máy xưởng thường không có pip.
"""
import io
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

VERSION = "0.1.0"

# Windows: stdio mặc định cp1252 → tên hồ sơ tiếng Việt làm hỏng giao thức
try:
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace")
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", newline="\n")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

BASE = (os.environ.get("OTL_API_BASE") or "http://127.0.0.1:8555").rstrip("/")
KEY = os.environ.get("OTL_API_KEY") or ""

# CHỈ những đường này được gọi. Chốt chặn thứ hai bên cạnh phạm vi quyền của khoá:
# kể cả ai đó đưa nhầm khoá 'control' vào biến môi trường, server này vẫn không có
# cách nào bắn lệnh xuống máy.
CHO_PHEP = (
    "/api/v1/snapshot", "/api/v1/profiles", "/api/v1/batches",
    "/api/v1/batch_curve", "/api/v1/batch_stats", "/api/v1/batches_curves",
    "/api/v1/mc_read", "/api/v1/state", "/api/v1/audit", "/api/v1/oplog",
)


class LoiGoi(Exception):
    pass


def _goi(duong, tham_so=None):
    """GET một đường trong danh sách cho phép. Trả dict."""
    goc = duong.split("?")[0]
    if goc not in CHO_PHEP:
        raise LoiGoi("đường '%s' không nằm trong danh sách cho phép của server đọc" % goc)
    url = BASE + duong
    if tham_so:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(tham_so)
    req = urllib.request.Request(url)
    if KEY:
        req.add_header("Authorization", "Bearer " + KEY)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise LoiGoi("app từ chối: thiếu hoặc sai OTL_API_KEY. "
                         "Tạo khoá phạm vi 'read' trong app (Cài đặt → Tài khoản).")
        if e.code == 403:
            raise LoiGoi("khoá API không có phạm vi 'read'.")
        if e.code == 429:
            raise LoiGoi("gọi quá nhiều, đang bị hãm — chờ một phút.")
        raise LoiGoi("app trả HTTP %s" % e.code)
    except urllib.error.URLError as e:
        raise LoiGoi("không nối được app ở %s (%s). App OTL Roast Lab có đang chạy không?"
                     % (BASE, e.reason))


# ── Công cụ ───────────────────────────────────────────────────────────────────
def t_trang_thai(_):
    """Ảnh chụp máy lúc này."""
    return _goi("/api/v1/snapshot")


def t_ho_so(_):
    return _goi("/api/v1/profiles")


def t_danh_sach_me(a):
    d = _goi("/api/v1/batches")
    ds = d.get("batches") or []
    n = int(a.get("so_luong") or 20)
    return {"tong": len(ds), "batches": ds[:n]}


def t_duong_cong(a):
    bid = a.get("ma_me")
    if bid in (None, ""):
        raise LoiGoi("thiếu 'ma_me'")
    return _goi("/api/v1/batch_curve", {"id": bid})


def t_thong_ke_me(a):
    bid = a.get("ma_me")
    if bid in (None, ""):
        raise LoiGoi("thiếu 'ma_me'")
    return _goi("/api/v1/batch_stats", {"id": bid})


def t_cau_hinh_may(_):
    """52 tham số $M đọc từ máy. Mỗi tham số một lượt hỏi-đáp nên hơi chậm."""
    return _goi("/api/v1/mc_read")


def t_so_me(a):
    """So nhiều mẻ với nhau — đây mới là chỗ AI có ích thật: chỉ ra mẻ nào lệch."""
    ids = a.get("ma_me") or []
    if isinstance(ids, str):
        ids = [x.strip() for x in ids.split(",") if x.strip()]
    if len(ids) < 2:
        raise LoiGoi("cần ít nhất 2 'ma_me' để so")
    return _goi("/api/v1/batches_curves", {"ids": ",".join(str(i) for i in ids)})


def t_kiem_tra(_):
    """Kiểm nhanh: có nối được app không, khoá có dùng được không."""
    kq = {"dia_chi": BASE, "co_khoa": bool(KEY)}
    try:
        s = _goi("/api/v1/snapshot")
        kq["noi_duoc"] = True
        kq["trang_thai_may"] = s.get("state")
        if s.get("err"):
            kq["ghi_chu"] = ("App chạy nhưng CHƯA nối được máy rang: %s" % s["err"])
    except LoiGoi as e:
        kq["noi_duoc"] = False
        kq["loi"] = str(e)
    return kq


TOOLS = [
    {"name": "roaster_kiem_tra",
     "description": "Kiểm nhanh có nối được app máy rang không và khoá API có dùng được không. "
                    "Gọi cái này trước khi báo lỗi cho người dùng.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "roaster_trang_thai",
     "description": "Trạng thái máy rang lúc này: nhiệt hạt (BT), nhiệt khí (ET), RoR, "
                    "mức gas/gió/trống, bước quy trình, thời gian mẻ.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "roaster_ho_so",
     "description": "Danh sách hồ sơ rang đã lưu (tên, mức rang, nhiệt nạp, nhiệt xả, thời gian).",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "roaster_danh_sach_me",
     "description": "Các mẻ đã rang gần đây.",
     "inputSchema": {"type": "object", "properties": {
         "so_luong": {"type": "integer", "description": "lấy bao nhiêu mẻ (mặc định 20)"}}}},
    {"name": "roaster_duong_cong_me",
     "description": "Đường cong nhiệt độ của MỘT mẻ — dùng để phân tích mẻ đó rang thế nào.",
     "inputSchema": {"type": "object", "required": ["ma_me"], "properties": {
         "ma_me": {"description": "mã mẻ lấy từ roaster_danh_sach_me"}}}},
    {"name": "roaster_thong_ke_me",
     "description": "Số liệu tổng hợp của một mẻ: các mốc TP/DE/FCs/Drop, thời gian từng pha.",
     "inputSchema": {"type": "object", "required": ["ma_me"], "properties": {
         "ma_me": {"description": "mã mẻ"}}}},
    {"name": "roaster_so_me",
     "description": "So đường cong của nhiều mẻ với nhau — tìm mẻ lệch khỏi nhóm, "
                    "đối chiếu mẻ mới với mẻ nền.",
     "inputSchema": {"type": "object", "required": ["ma_me"], "properties": {
         "ma_me": {"type": "array", "items": {"type": "string"},
                   "description": "danh sách mã mẻ, ít nhất 2"}}}},
    {"name": "roaster_cau_hinh_may",
     "description": "Đọc 52 tham số vận hành $M từ máy (timer xi-lanh, gas, mốc pha rang, "
                    "cân, hút, làm nóng). CHỈ ĐỌC — server này không ghi được.",
     "inputSchema": {"type": "object", "properties": {}}},
]

HAM = {
    "roaster_kiem_tra": t_kiem_tra,
    "roaster_trang_thai": t_trang_thai,
    "roaster_ho_so": t_ho_so,
    "roaster_danh_sach_me": t_danh_sach_me,
    "roaster_duong_cong_me": t_duong_cong,
    "roaster_thong_ke_me": t_thong_ke_me,
    "roaster_so_me": t_so_me,
    "roaster_cau_hinh_may": t_cau_hinh_may,
}


def _send(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def call(ten, args):
    f = HAM.get(ten)
    if not f:
        raise LoiGoi("không có công cụ tên '%s'" % ten)
    return f(args or {})


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue

        mid, method = req.get("id"), req.get("method")

        if method == "initialize":
            _send({"jsonrpc": "2.0", "id": mid, "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "otl-roaster-read", "version": VERSION},
            }})
        elif method in ("notifications/initialized", "initialized"):
            pass
        elif method == "tools/list":
            _send({"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS}})
        elif method == "tools/call":
            p = req.get("params", {})
            try:
                out = call(p.get("name"), p.get("arguments") or {})
                body = json.dumps(out, ensure_ascii=False, indent=1)
                if len(body) > 190000:
                    body = body[:190000] + "\n…(cắt bớt — thu hẹp bằng 'so_luong')"
                _send({"jsonrpc": "2.0", "id": mid,
                       "result": {"content": [{"type": "text", "text": body}]}})
            except LoiGoi as e:
                # Lỗi đã lường trước → báo gọn, nói RÕ LÝ DO để AI xử đúng
                _send({"jsonrpc": "2.0", "id": mid, "result": {
                    "content": [{"type": "text", "text": "Lỗi: %s" % e}],
                    "isError": True}})
            except Exception as e:            # noqa: BLE001 — không được để server chết
                _send({"jsonrpc": "2.0", "id": mid, "result": {
                    "content": [{"type": "text", "text": "Lỗi bất ngờ: %r" % e}],
                    "isError": True}})
        elif mid is not None:
            _send({"jsonrpc": "2.0", "id": mid,
                   "error": {"code": -32601, "message": "method không hỗ trợ: %s" % method}})


if __name__ == "__main__":
    main()
