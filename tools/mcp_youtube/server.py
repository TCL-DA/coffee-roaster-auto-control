# -*- coding: utf-8 -*-
"""MCP server đọc kênh YouTube của O Tesla — CHỈ ĐỌC.

Chạy:
    python tools/mcp_youtube/server.py

Khoá để NGOÀI repo (mặc định F:\\Project\\114_Youtube):
    client_secret.json   tải từ Google Cloud Console
    token.json           sinh ra khi chạy 114_Youtube\\cap_quyen.py

Biến môi trường:
    OTL_YT_DIR    thư mục chứa hai file trên

⛔ Server này KHÔNG đăng, KHÔNG sửa, KHÔNG xoá gì trên kênh. Bộ quyền xin trong
cap_quyen.py chỉ có youtube.readonly + yt-analytics.readonly, nên kể cả có lỗi
lập trình thì Google cũng từ chối mọi lệnh ghi. Muốn đăng video thì phải sửa
QUYEN trong cap_quyen.py, xoá token.json, cấp quyền lại — và biết trước rằng
app chưa qua kiểm duyệt Google thì video đăng lên bị khoá private.
"""
import io
import json
import os
import sys

VERSION = "1.0.0"

THUMUC = os.environ.get("OTL_YT_DIR", r"F:\Project\114_Youtube")
BI_MAT = os.path.join(THUMUC, "client_secret.json")
TOKEN = os.path.join(THUMUC, "token.json")

QUYEN = ["https://www.googleapis.com/auth/youtube.readonly",
         "https://www.googleapis.com/auth/yt-analytics.readonly"]

_dv = {}     # dịch vụ đã dựng, dùng lại cho các lần gọi sau


class LoiGoi(Exception):
    """Lỗi đã lường trước — báo gọn, không phải sự cố server."""


def _creds():
    if not os.path.exists(TOKEN):
        raise LoiGoi("chưa cấp quyền. Chạy một lần:\n"
                     "  cd \"%s\"\n  python cap_quyen.py" % THUMUC)
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
    except ImportError:
        raise LoiGoi("thiếu thư viện. Chạy: pip install google-auth-oauthlib "
                     "google-api-python-client")
    c = Credentials.from_authorized_user_file(TOKEN, QUYEN)
    if not c.valid:
        if c.expired and c.refresh_token:
            try:
                c.refresh(Request())
                io.open(TOKEN, "w", encoding="utf-8").write(c.to_json())
            except Exception as e:      # noqa: BLE001
                raise LoiGoi("token hết hạn và làm mới không được (%s). App để ở "
                             "chế độ Testing thì Google chỉ cho token sống 7 "
                             "ngày — chạy lại cap_quyen.py, hoặc vào OAuth "
                             "consent screen bấm Publish app để khỏi phải lặp "
                             "lại hàng tuần." % e)
        else:
            raise LoiGoi("token không dùng được, chạy lại cap_quyen.py")
    return c


def _yt(ten="youtube", ver="v3"):
    if ten not in _dv:
        from googleapiclient.discovery import build
        _dv[ten] = build(ten, ver, credentials=_creds(), cache_discovery=False)
    return _dv[ten]


def _ma_kenh():
    r = _yt().channels().list(part="id", mine=True).execute()
    if not r.get("items"):
        raise LoiGoi("tài khoản đã cấp quyền không sở hữu kênh nào")
    return r["items"][0]["id"]


# ── công cụ ────────────────────────────────────────────────────────────────
def youtube_kiem_tra(a):
    ket = {"phien_ban": VERSION, "thu_muc_khoa": THUMUC,
           "co_client_secret": os.path.exists(BI_MAT),
           "co_token": os.path.exists(TOKEN)}
    if not ket["co_token"]:
        ket["viec_can_lam"] = ("chạy `python cap_quyen.py` trong %s, bấm đồng ý "
                               "trên trình duyệt" % THUMUC)
        return ket
    r = _yt().channels().list(part="snippet,statistics", mine=True).execute()
    k = r["items"][0]
    ket["ket_noi"] = "OK"
    ket["kenh"] = {"ten": k["snippet"]["title"], "ma": k["id"]}
    ket["kenh"].update(k.get("statistics", {}))
    return ket


def youtube_kenh(a):
    r = _yt().channels().list(part="snippet,statistics,contentDetails",
                              mine=True).execute()
    k = r["items"][0]
    s, t = k["snippet"], k.get("statistics", {})
    return {"ma": k["id"], "ten": s["title"], "mo_ta": s.get("description", ""),
            "lap_ngay": s.get("publishedAt"),
            "nguoi_dang_ky": t.get("subscriberCount"),
            "an_so_nguoi_dang_ky": t.get("hiddenSubscriberCount"),
            "so_video": t.get("videoCount"), "luot_xem": t.get("viewCount")}


def youtube_video(a):
    """Liệt kê video của kênh, mới nhất trước."""
    n = min(int(a.get("so_luong", 25)), 200)
    yt = _yt()
    up = yt.channels().list(part="contentDetails", mine=True).execute()
    pl = up["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    ids, trang = [], None
    while len(ids) < n:
        r = yt.playlistItems().list(part="contentDetails", playlistId=pl,
                                    maxResults=min(50, n - len(ids)),
                                    pageToken=trang).execute()
        ids += [x["contentDetails"]["videoId"] for x in r.get("items", [])]
        trang = r.get("nextPageToken")
        if not trang:
            break

    ra = []
    for i in range(0, len(ids), 50):
        r = yt.videos().list(part="snippet,statistics,contentDetails",
                             id=",".join(ids[i:i + 50])).execute()
        for v in r.get("items", []):
            s, t = v["snippet"], v.get("statistics", {})
            ra.append({"ma": v["id"], "tieu_de": s["title"],
                       "dang_ngay": s.get("publishedAt"),
                       "thoi_luong": v.get("contentDetails", {}).get("duration"),
                       "luot_xem": t.get("viewCount"),
                       "thich": t.get("likeCount"),
                       "binh_luan": t.get("commentCount"),
                       "link": "https://youtu.be/" + v["id"]})
    return {"so_video": len(ra), "video": ra}


def youtube_so_lieu(a):
    """Số liệu người xem theo khoảng ngày. Mặc định 28 ngày gần nhất."""
    import datetime as dt
    den = a.get("den") or dt.date.today().isoformat()
    tu = a.get("tu") or (dt.date.fromisoformat(den) - dt.timedelta(days=27)).isoformat()
    chi_so = a.get("chi_so") or ("views,estimatedMinutesWatched,"
                                 "averageViewDuration,averageViewPercentage,"
                                 "subscribersGained")
    tham = {"ids": "channel==" + _ma_kenh(), "startDate": tu, "endDate": den,
            "metrics": chi_so}
    if a.get("theo_video"):
        tham.update({"dimensions": "video", "sort": "-views",
                     "maxResults": int(a.get("so_luong", 20))})
    elif a.get("theo_ngay"):
        tham["dimensions"] = "day"

    r = _yt("youtubeAnalytics", "v2").reports().query(**tham).execute()
    cot = [c["name"] for c in r.get("columnHeaders", [])]
    hang = [dict(zip(cot, d)) for d in r.get("rows", [])]

    # thêm tiêu đề cho dễ đọc khi tách theo video
    if a.get("theo_video") and hang:
        ids = [h["video"] for h in hang if h.get("video")]
        ten = {}
        for i in range(0, len(ids), 50):
            rv = _yt().videos().list(part="snippet",
                                     id=",".join(ids[i:i + 50])).execute()
            ten.update({v["id"]: v["snippet"]["title"] for v in rv.get("items", [])})
        for h in hang:
            h["tieu_de"] = ten.get(h.get("video"), "(không đọc được)")

    return {"tu_ngay": tu, "den_ngay": den, "cot": cot,
            "so_hang": len(hang), "so_lieu": hang}


def youtube_binh_luan(a):
    ma = a.get("video")
    if not ma:
        raise LoiGoi("thiếu mã video (lấy từ youtube_video)")
    n = min(int(a.get("so_luong", 30)), 100)
    r = _yt().commentThreads().list(part="snippet", videoId=ma, maxResults=n,
                                    order=a.get("sap_xep", "relevance"),
                                    textFormat="plainText").execute()
    ra = []
    for t in r.get("items", []):
        c = t["snippet"]["topLevelComment"]["snippet"]
        ra.append({"nguoi": c.get("authorDisplayName"),
                   "noi_dung": c.get("textDisplay"),
                   "thich": c.get("likeCount"),
                   "luc": c.get("publishedAt"),
                   "so_tra_loi": t["snippet"].get("totalReplyCount")})
    return {"video": ma, "so_binh_luan": len(ra), "binh_luan": ra,
            "ghi_chu": "chỉ đọc — server này không trả lời bình luận được"}


HAM = {"youtube_kiem_tra": youtube_kiem_tra,
       "youtube_kenh": youtube_kenh,
       "youtube_video": youtube_video,
       "youtube_so_lieu": youtube_so_lieu,
       "youtube_binh_luan": youtube_binh_luan}

TOOLS = [
    {"name": "youtube_kiem_tra",
     "description": "Kiểm nhanh đã nối được kênh YouTube chưa và đang nối vào kênh nào. "
                    "Gọi cái này TRƯỚC khi báo lỗi cho người dùng — nó nói rõ thiếu "
                    "khoá, hết hạn token, hay tài khoản không có kênh.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "youtube_kenh",
     "description": "Thông tin tổng quan của kênh: tên, mô tả, ngày lập, số người đăng ký, "
                    "tổng số video, tổng lượt xem.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "youtube_video",
     "description": "Liệt kê video của kênh, mới nhất trước, kèm lượt xem, lượt thích, "
                    "số bình luận, thời lượng và link. Dùng để tìm mã video cho các "
                    "công cụ khác.",
     "inputSchema": {"type": "object", "properties": {
         "so_luong": {"type": "integer", "description": "số video lấy về, mặc định 25, "
                      "tối đa 200"}}}},
    {"name": "youtube_so_lieu",
     "description": "Số liệu người xem theo khoảng ngày: lượt xem, số phút đã xem, thời "
                    "lượng xem trung bình, phần trăm xem hết, số người đăng ký tăng thêm. "
                    "Mặc định 28 ngày gần nhất, gộp cả kênh. Đặt theo_video=true để xem "
                    "video nào ăn khách, theo_ngay=true để xem diễn biến từng ngày.",
     "inputSchema": {"type": "object", "properties": {
         "tu": {"type": "string", "description": "ngày bắt đầu, dạng YYYY-MM-DD"},
         "den": {"type": "string", "description": "ngày kết thúc, dạng YYYY-MM-DD"},
         "theo_video": {"type": "boolean", "description": "tách theo từng video, sắp "
                        "theo lượt xem giảm dần, có kèm tiêu đề"},
         "theo_ngay": {"type": "boolean", "description": "tách theo từng ngày"},
         "so_luong": {"type": "integer", "description": "số dòng khi tách theo video"},
         "chi_so": {"type": "string", "description": "danh sách chỉ số của YouTube "
                    "Analytics, cách nhau bằng dấu phẩy. Bỏ trống thì dùng bộ hay dùng"}}}},
    {"name": "youtube_binh_luan",
     "description": "Đọc bình luận của một video. CHỈ ĐỌC — không trả lời được.",
     "inputSchema": {"type": "object", "properties": {
         "video": {"type": "string", "description": "mã video, lấy từ youtube_video"},
         "so_luong": {"type": "integer", "description": "mặc định 30, tối đa 100"},
         "sap_xep": {"type": "string", "description": "relevance (mặc định) hoặc time"}},
         "required": ["video"]}},
]


# ── giao thức ──────────────────────────────────────────────────────────────
def _send(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


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
                "serverInfo": {"name": "otl-youtube", "version": VERSION}}})
        elif method in ("notifications/initialized", "initialized"):
            pass
        elif method == "tools/list":
            _send({"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS}})
        elif method == "tools/call":
            p = req.get("params", {})
            try:
                f = HAM.get(p.get("name"))
                if not f:
                    raise LoiGoi("không có công cụ tên '%s'" % p.get("name"))
                out = f(p.get("arguments") or {})
                body = json.dumps(out, ensure_ascii=False, indent=1)
                if len(body) > 190000:
                    body = body[:190000] + "\n…(cắt bớt — thu hẹp bằng 'so_luong')"
                _send({"jsonrpc": "2.0", "id": mid,
                       "result": {"content": [{"type": "text", "text": body}]}})
            except LoiGoi as e:
                _send({"jsonrpc": "2.0", "id": mid, "result": {
                    "content": [{"type": "text", "text": "Lỗi: %s" % e}],
                    "isError": True}})
            except Exception as e:      # noqa: BLE001 — không để server chết
                _send({"jsonrpc": "2.0", "id": mid, "result": {
                    "content": [{"type": "text", "text": "Lỗi bất ngờ: %r" % e}],
                    "isError": True}})
        elif mid is not None:
            _send({"jsonrpc": "2.0", "id": mid,
                   "error": {"code": -32601,
                             "message": "method không hỗ trợ: %s" % method}})


if __name__ == "__main__":
    main()
