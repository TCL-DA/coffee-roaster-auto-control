# -*- coding: utf-8 -*-
"""MCP server kênh YouTube của O Tesla — đọc kênh, sửa video, lấy lời thoại.

Chạy:
    python tools/mcp_youtube/server.py

Khoá để NGOÀI repo (mặc định F:\\Project\\114_Youtube):
    client_secret.json   tải từ Google Cloud Console
    token.json           sinh ra khi chạy 114_Youtube\\cap_quyen.py
    api_key.txt          (tuỳ chọn) khoá API cho youtube_tim_cong_khai

Biến môi trường:
    OTL_YT_DIR        thư mục chứa mấy file trên
    OTL_YT_API_KEY    thay cho api_key.txt

Bản 2.0 gộp việc của 5 dự án nguồn vào chung một server — xem NGUON.md để biết
lấy gì ở đâu và giấy phép kèm theo:
    google-api-python-client   Apache-2.0   nền gọi API (đọc kênh, sửa video)
    youtube-transcript-api     MIT          youtube_loi_thoai (khỏi cần OAuth)
    ytstudio-cli               MIT          youtube_thay_hang_loat, _phu_de,
                                            _danh_sach_phat
    youtube-studio-mcp         MIT          youtube_anh_bia, _tra_loi_binh_luan
    python-youtube (pyyoutube) MIT          youtube_tim_cong_khai

⛔ Server này KHÔNG xoá video — cố ý không mở.
Từ 01/10/2026 ĐĂNG được video mới (youtube_dang_video), theo yêu cầu của chủ máy.
Mặc định đăng RIÊNG TƯ; muốn công khai phải nói rõ che_do='public'.
Những việc GHI làm được, đều hiện ngay trên kênh công khai nên phải đưa người
dùng duyệt trước khi gọi:
    youtube_sua_video          đổi tiêu đề / mô tả / tag / chế độ riêng tư 1 video
    youtube_thay_hang_loat     thay chữ trên NHIỀU video (mặc định chỉ xem trước)
    youtube_anh_bia            đặt ảnh bìa mới
    youtube_tra_loi_binh_luan  đăng bình luận dưới tên kênh (cần thêm quyền)
    youtube_dang_video         ĐĂNG VIDEO MỚI (cần quyền youtube.upload)

Quyền: gắn phụ đề rời và trả lời bình luận cần youtube.force-ssl. Scope đã có
trong QUYEN và cap_quyen.py, nhưng token cấp TRƯỚC 01/10/2026 thì chưa mang nó —
youtube_dang_video soát trước khi tải nên báo ngay, không để tải xong mới 403.
Thiếu thì: xoá token.json, chạy lại python cap_quyen.py.
Biết trước: app để chế độ Testing thì token chỉ sống 7 ngày.
"""
import io
import json
import os
import sys
import time

# Windows mặc định để stdout ở bảng mã cp1252, mà giao thức MCP lẫn chữ tiếng
# Việt đều là UTF-8. Không ép lại thì ngay bước tools/list đã ném
# UnicodeEncodeError ở chữ có dấu và server chết lúc bắt tay.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", newline=chr(10))
if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")

VERSION = "2.0.0"

THUMUC = os.environ.get("OTL_YT_DIR", r"F:\Project\114_Youtube")
BI_MAT = os.path.join(THUMUC, "client_secret.json")
TOKEN = os.path.join(THUMUC, "token.json")

QUYEN = ["https://www.googleapis.com/auth/youtube.readonly",
         "https://www.googleapis.com/auth/yt-analytics.readonly",
         "https://www.googleapis.com/auth/youtube",
         "https://www.googleapis.com/auth/youtube.upload",
         "https://www.googleapis.com/auth/youtube.force-ssl"]

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


def youtube_sua_video(a):
    """Sửa tiêu đề / mô tả / tag / chế độ riêng tư của MỘT video đã có."""
    ma = a.get("video")
    if not ma:
        raise LoiGoi("thiếu mã video (lấy từ youtube_video)")
    xin = dict((k, a[k]) for k in ("tieu_de", "mo_ta", "tag", "rieng_tu")
               if a.get(k) is not None)
    if not xin:
        raise LoiGoi("không có gì để sửa. Đưa ít nhất một trong: tieu_de, "
                     "mo_ta, tag, rieng_tu")

    if "tieu_de" in xin:
        if not xin["tieu_de"].strip():
            raise LoiGoi("tiêu đề để trống thì YouTube từ chối")
        if len(xin["tieu_de"]) > 100:
            raise LoiGoi("tiêu đề tối đa 100 ký tự, đang %d" % len(xin["tieu_de"]))
    if "mo_ta" in xin and len(xin["mo_ta"]) > 5000:
        raise LoiGoi("mô tả tối đa 5000 ký tự, đang %d" % len(xin["mo_ta"]))
    # YouTube từ chối dấu < và > trong tiêu đề lẫn mô tả, trả lỗi 400 khó đoán
    # ("invalid video description"). Bắt ở đây để báo đúng chỗ sai.
    for k, ten in (("tieu_de", "tiêu đề"), ("mo_ta", "mô tả")):
        if k in xin and ("<" in xin[k] or ">" in xin[k]):
            raise LoiGoi("%s có dấu < hoặc > — YouTube không nhận. Thay bằng "
                         "mũi tên → hoặc gạch ngang." % ten)
    if "tag" in xin:
        if not isinstance(xin["tag"], list):
            raise LoiGoi("tag phải là danh sách chuỗi")
        if sum(len(t) + 1 for t in xin["tag"]) > 500:
            raise LoiGoi("tổng các tag tối đa 500 ký tự")
    if "rieng_tu" in xin and xin["rieng_tu"] not in ("public", "unlisted", "private"):
        raise LoiGoi("rieng_tu chỉ nhận public, unlisted hoặc private")

    yt = _yt()
    r = yt.videos().list(part="snippet,status", id=ma).execute()
    if not r.get("items"):
        raise LoiGoi("không thấy video %s — kiểm lại mã, hoặc video không thuộc "
                     "kênh đã cấp quyền" % ma)
    v = r["items"][0]
    s, t = v["snippet"], v["status"]
    truoc = {"tieu_de": s.get("title"), "mo_ta": s.get("description", ""),
             "tag": s.get("tags", []), "rieng_tu": t.get("privacyStatus")}

    # videos().update GHI ĐÈ nguyên khối chứ không vá từng trường: phải gửi lại
    # đủ những gì đang có, kể cả categoryId, nếu không YouTube xoá mất phần
    # mình không gửi.
    if any(k in xin for k in ("tieu_de", "mo_ta", "tag")):
        moi = {"title": xin.get("tieu_de", truoc["tieu_de"]),
               "description": xin.get("mo_ta", truoc["mo_ta"]),
               "categoryId": s.get("categoryId")}
        tag = xin.get("tag", truoc["tag"])
        if tag:
            moi["tags"] = tag
        for k in ("defaultLanguage", "defaultAudioLanguage"):
            if s.get(k):
                moi[k] = s[k]
        s = yt.videos().update(part="snippet",
                               body={"id": ma, "snippet": moi}).execute()["snippet"]
    if "rieng_tu" in xin:
        moi = {"privacyStatus": xin["rieng_tu"]}
        for k in ("embeddable", "license", "publicStatsViewable",
                  "selfDeclaredMadeForKids"):
            if t.get(k) is not None:
                moi[k] = t[k]
        t = yt.videos().update(part="status",
                               body={"id": ma, "status": moi}).execute()["status"]

    # ⛔ KHÔNG đọc lại bằng videos().list() để báo kết quả: vài giây đầu sau khi
    # ghi, YouTube vẫn trả BẢN CŨ (bộ nhớ đệm) — nhìn vào tưởng ghi hỏng trong
    # khi thực ra đã ghi xong. Bản videos().update() trả về chính là bản vừa ghi.
    return {"video": ma, "link": "https://youtu.be/" + ma, "truoc": truoc,
            "sau": {"tieu_de": s.get("title"), "mo_ta": s.get("description", ""),
                    "tag": s.get("tags", []), "rieng_tu": t.get("privacyStatus")},
            "ghi_chu": "đã ghi lên kênh thật, người xem thấy ngay. Đọc lại bằng "
                       "youtube_video ngay sau đó có thể vẫn ra tên cũ vài giây."}


THIEU_SSL = ("token hiện tại chưa đủ quyền cho việc này. Mở %s\\cap_quyen.py, thêm "
             "\"https://www.googleapis.com/auth/youtube.force-ssl\" vào QUYEN, xoá "
             "%s rồi chạy lại cap_quyen.py để cấp quyền mới." % (THUMUC, TOKEN))


def _ma_video(x):
    """Nhận cả mã trần lẫn link, trả về mã 11 ký tự.

    Người dùng hay dán nguyên link từ trình duyệt; bắt ở đây đỡ phải dặn.
    """
    if not x:
        raise LoiGoi("thiếu mã video (lấy từ youtube_video, hoặc dán luôn link)")
    x = x.strip()
    for dau in ("v=", "youtu.be/", "/shorts/", "/live/", "/embed/"):
        if dau in x:
            x = x.split(dau, 1)[1]
    x = x.split("&", 1)[0].split("?", 1)[0].split("/", 1)[0]
    if len(x) != 11:
        raise LoiGoi("'%s' không giống mã video YouTube (phải đúng 11 ký tự)" % x)
    return x


def _gio(giay):
    """185.0 → '3:05'  ·  3723.0 → '1:02:03' — đúng dạng mốc chương YouTube."""
    g = int(giay)
    if g >= 3600:
        return "%d:%02d:%02d" % (g // 3600, g % 3600 // 60, g % 60)
    return "%d:%02d" % (g // 60, g % 60)


def _dich_loi_google(e):
    """Đổi HttpError của Google sang lời báo hiểu được, hoặc None nếu không phải.

    Hai lỗi hay gặp nhất mà thông báo gốc của Google nói rất khó hiểu: hết hạn
    mức ngày (quotaExceeded) và token thiếu quyền (insufficientPermissions).
    """
    try:
        from googleapiclient.errors import HttpError
    except ImportError:
        return None
    if not isinstance(e, HttpError):
        return None
    ma = getattr(getattr(e, "resp", None), "status", 0)
    ly_do = ""
    try:
        ly_do = (e.error_details or [{}])[0].get("reason", "") or ""
    except Exception:      # noqa: BLE001 — cấu trúc lỗi của Google hay đổi
        pass
    if ly_do == "quotaExceeded":
        return LoiGoi("hết hạn mức YouTube API của hôm nay (10.000 đơn vị, Google "
                      "đặt lại lúc 14:00 giờ Việt Nam). Mỗi lần GHI tốn 50 đơn vị, "
                      "mỗi lần đọc tốn 1 — nên tránh chạy youtube_thay_hang_loat "
                      "nhiều lượt trong ngày.")
    if ma == 403 and ly_do in ("insufficientPermissions", "forbidden",
                               "insufficientFilePermissions"):
        return LoiGoi(THIEU_SSL)
    return None


# ── gộp từ youtube-transcript-api (MIT) ────────────────────────────────────
def youtube_loi_thoai(a):
    """Lấy lời thoại video KHÔNG cần OAuth — chạy được cả khi token hỏng.

    Dùng để viết mô tả và mốc chương mà không phải cắt khung hình xem từng đoạn.
    Chạy được trên MỌI video công khai, không riêng kênh mình.
    """
    ma = _ma_video(a.get("video"))
    try:
        from youtube_transcript_api import (YouTubeTranscriptApi, TranscriptsDisabled,
                                            NoTranscriptFound, VideoUnavailable)
    except ImportError:
        raise LoiGoi("thiếu thư viện. Chạy: pip install youtube-transcript-api")

    api = YouTubeTranscriptApi()
    if a.get("chi_liet_ke"):
        try:
            ds = api.list(ma)
        except Exception as e:      # noqa: BLE001
            raise LoiGoi("không đọc được danh sách phụ đề: %s" % e)
        return {"video": ma, "phu_de_co_san": [
            {"ma_ngon_ngu": t.language_code, "ten": t.language,
             "may_tu_nghe": t.is_generated} for t in ds]}

    nn = a.get("ngon_ngu") or ["vi", "en"]
    if isinstance(nn, str):
        nn = [x.strip() for x in nn.split(",") if x.strip()]
    try:
        ban = api.fetch(ma, languages=nn)
    except TranscriptsDisabled:
        raise LoiGoi("video này tắt phụ đề nên không lấy lời thoại được")
    except NoTranscriptFound:
        raise LoiGoi("không có phụ đề tiếng %s. Gọi lại với chi_liet_ke=true để "
                     "xem video có sẵn tiếng gì." % "/".join(nn))
    except VideoUnavailable:
        raise LoiGoi("không mở được video %s (riêng tư, bị xoá, hoặc chặn vùng)" % ma)
    except Exception as e:      # noqa: BLE001
        raise LoiGoi("lấy lời thoại hỏng: %s" % e)

    # Gộp các mẩu phụ đề thành khối vài chục giây. Phụ đề thô mỗi mẩu ~2 giây,
    # video 30 phút ra cả nghìn dòng — nhồi hết vào ngữ cảnh rất tốn mà không
    # đọc ra ý gì hơn. Gộp lại vừa gọn vừa đủ mốc thời gian để đặt chương.
    gop = max(0, int(a.get("gop_giay", 30)))
    khoi, moc, chu = [], None, []
    for m in ban.snippets:
        if moc is None or (gop and m.start - moc >= gop):
            if chu:
                khoi.append({"luc": _gio(moc), "giay": int(moc), "chu": " ".join(chu)})
            moc, chu = m.start, []
        chu.append(m.text.replace("\n", " ").strip())
    if chu:
        khoi.append({"luc": _gio(moc), "giay": int(moc), "chu": " ".join(chu)})

    return {"video": ma, "link": "https://youtu.be/" + ma,
            "ngon_ngu": getattr(ban, "language_code", nn[0]),
            "may_tu_nghe": getattr(ban, "is_generated", None),
            "gop_moi_khoi_giay": gop, "so_khoi": len(khoi),
            "tong_chu": sum(len(k["chu"]) for k in khoi), "loi_thoai": khoi,
            "ghi_chu": "mốc 'luc' dán thẳng vào mô tả là thành chương YouTube"}


# ── gộp từ ytstudio-cli (MIT) ──────────────────────────────────────────────
def youtube_thay_hang_loat(a):
    """Tìm & thay chữ trong tiêu đề hoặc mô tả của HÀNG LOẠT video.

    Mặc định chỉ XEM TRƯỚC, không ghi. Phải truyền thuc_thi=true mới ghi thật.
    """
    import re
    tim, thay = a.get("tim"), a.get("thay")
    if not tim:
        raise LoiGoi("thiếu 'tim' — chữ cần tìm")
    if thay is None:
        raise LoiGoi("thiếu 'thay' — chữ thay vào (để chuỗi rỗng là xoá đi)")
    truong = a.get("truong", "mo_ta")
    if truong not in ("tieu_de", "mo_ta"):
        raise LoiGoi("truong chỉ nhận 'tieu_de' hoặc 'mo_ta'")
    khoa = "title" if truong == "tieu_de" else "description"
    n = min(int(a.get("so_luong", 20)), 100)
    thuc_thi = bool(a.get("thuc_thi"))

    yt = _yt()
    # Duyệt playlist "uploads" chứ KHÔNG dùng search().list(forMine=True) như bản
    # gốc ytstudio-cli: search tốn 100 đơn vị hạn mức mỗi lần gọi, còn
    # playlistItems chỉ tốn 1. Kênh vài trăm video là khác nhau cả ngàn đơn vị.
    up = yt.channels().list(part="contentDetails", mine=True).execute()
    pl = up["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    ids, trang = [], None
    while True:
        r = yt.playlistItems().list(part="contentDetails", playlistId=pl,
                                    maxResults=50, pageToken=trang).execute()
        ids += [x["contentDetails"]["videoId"] for x in r.get("items", [])]
        trang = r.get("nextPageToken")
        if not trang:
            break

    doi = []
    for i in range(0, len(ids), 50):
        r = yt.videos().list(part="snippet", id=",".join(ids[i:i + 50])).execute()
        for v in r.get("items", []):
            cu = v["snippet"].get(khoa, "") or ""
            moi = re.sub(tim, thay, cu) if a.get("bieu_thuc") else cu.replace(tim, thay)
            if moi != cu:
                doi.append({"video": v["id"], "tieu_de_video": v["snippet"]["title"],
                            "truoc": cu, "sau": moi})

    tong = len(doi)
    doi = doi[:n]
    if not doi:
        return {"da_quet": len(ids), "so_trung": 0,
                "ket_luan": "không video nào chứa '%s' trong %s" % (tim, truong)}

    if not thuc_thi:
        for d in doi:      # xem trước thì cắt bớt cho dễ đọc
            for k in ("truoc", "sau"):
                if len(d[k]) > 400:
                    d[k] = d[k][:400] + "…"
        return {"da_quet": len(ids), "so_trung": tong, "se_sua": len(doi),
                "thay_doi": doi,
                "ghi_chu": "MỚI CHỈ XEM TRƯỚC, chưa ghi gì lên kênh. Đưa người dùng "
                           "duyệt rồi gọi lại với thuc_thi=true. Quá 100 chỗ thì "
                           "làm nhiều đợt."}

    # Ghi thật. Tốn 50 đơn vị hạn mức mỗi video nên chặn trần ở so_luong.
    xong, hong = [], []
    for d in doi:
        try:
            r = yt.videos().list(part="snippet", id=d["video"]).execute()
            if not r.get("items"):
                hong.append({"video": d["video"], "vi_sao": "không thấy video"})
                continue
            s = r["items"][0]["snippet"]
            # videos().update ghi đè nguyên khối snippet: phải gửi lại đủ những
            # trường đang có, nếu không YouTube xoá mất phần mình không gửi.
            moi = {"title": s.get("title"), "description": s.get("description", ""),
                   "categoryId": s.get("categoryId")}
            if s.get("tags"):
                moi["tags"] = s["tags"]
            for k in ("defaultLanguage", "defaultAudioLanguage"):
                if s.get(k):
                    moi[k] = s[k]
            moi[khoa] = d["sau"]
            yt.videos().update(part="snippet",
                               body={"id": d["video"], "snippet": moi}).execute()
            xong.append(d["video"])
        except Exception as e:      # noqa: BLE001
            ro = _dich_loi_google(e)
            if ro:      # hết hạn mức thì dừng luôn, chạy tiếp cũng hỏng
                return {"da_sua": xong, "so_da_sua": len(xong),
                        "dung_giua_chung": str(ro),
                        "con_lai": [d["video"] for d in doi if d["video"] not in xong]}
            hong.append({"video": d["video"], "vi_sao": repr(e)})
    return {"so_trung": tong, "da_sua": xong, "so_da_sua": len(xong), "hong": hong,
            "ghi_chu": "đã ghi lên kênh thật, người xem thấy ngay"}


def youtube_danh_sach_phat(a):
    """Liệt kê playlist của kênh, hoặc video bên trong một playlist."""
    yt = _yt()
    ma = a.get("danh_sach")
    if not ma:
        r = yt.playlists().list(part="snippet,contentDetails", mine=True,
                                maxResults=min(int(a.get("so_luong", 50)), 50)).execute()
        return {"so_danh_sach": len(r.get("items", [])), "danh_sach": [
            {"ma": p["id"], "ten": p["snippet"]["title"],
             "mo_ta": p["snippet"].get("description", ""),
             "so_video": p.get("contentDetails", {}).get("itemCount"),
             "link": "https://www.youtube.com/playlist?list=" + p["id"]}
            for p in r.get("items", [])]}

    n = min(int(a.get("so_luong", 50)), 200)
    ra, trang = [], None
    while len(ra) < n:
        r = yt.playlistItems().list(part="snippet,contentDetails", playlistId=ma,
                                    maxResults=min(50, n - len(ra)),
                                    pageToken=trang).execute()
        for x in r.get("items", []):
            ra.append({"ma": x["contentDetails"]["videoId"],
                       "tieu_de": x["snippet"]["title"],
                       "thu_tu": x["snippet"].get("position"),
                       "link": "https://youtu.be/" + x["contentDetails"]["videoId"]})
        trang = r.get("nextPageToken")
        if not trang:
            break
    return {"danh_sach": ma, "so_video": len(ra), "video": ra}


def youtube_phu_de(a):
    """Phụ đề CHÍNH THỨC của kênh mình, qua API (cần quyền force-ssl).

    Khác youtube_loi_thoai ở chỗ: cái này đọc đúng bản phụ đề đã tải lên kênh,
    kể cả bản chưa công khai; cái kia lấy bản YouTube phát ra ngoài, khỏi cần quyền.
    """
    import re
    ma = _ma_video(a.get("video"))
    yt = _yt()
    try:
        r = yt.captions().list(part="snippet", videoId=ma).execute()
    except Exception as e:      # noqa: BLE001
        ro = _dich_loi_google(e)
        if ro:
            raise ro
        raise LoiGoi("không đọc được danh sách phụ đề: %s" % e)

    rank = [{"ma": x["id"], "ngon_ngu": x["snippet"].get("language", ""),
             "ten": x["snippet"].get("name", ""),
             "kieu": x["snippet"].get("trackKind", "standard"),
             "ban_nhap": x["snippet"].get("isDraft", False),
             "sua_lan_cuoi": x["snippet"].get("lastUpdated", "")}
            for x in r.get("items", [])]
    if not rank:
        return {"video": ma, "so_ban": 0,
                "ghi_chu": "video này chưa có bản phụ đề nào trên kênh. Muốn lấy lời "
                           "thoại thì dùng youtube_loi_thoai."}
    if a.get("chi_liet_ke"):
        return {"video": ma, "so_ban": len(rank), "phu_de": rank}

    nn = a.get("ngon_ngu")
    chon = [t for t in rank if t["ngon_ngu"] == nn] if nn else list(rank)
    if not chon:
        raise LoiGoi("không có bản phụ đề tiếng '%s'. Có: %s"
                     % (nn, ", ".join(t["ngon_ngu"] for t in rank)))
    # Ưu tiên bản người làm (standard) hơn bản máy nghe (ASR): bản máy nghe hay
    # bị YouTube khoá không cho tải, mà chữ cũng sai nhiều hơn.
    nguoi = [t for t in chon if t["kieu"] == "standard"]
    t = (nguoi or chon)[0]

    try:
        data = yt.captions().download(id=t["ma"], tfmt="srt").execute()
    except Exception as e:      # noqa: BLE001
        ro = _dich_loi_google(e)
        if ro:
            raise ro
        raise LoiGoi("bản phụ đề '%s' (%s) có nhưng YouTube không cho tải. Bản máy tự "
                     "nghe hay bị khoá như vậy — dùng youtube_loi_thoai thay thế."
                     % (t["ngon_ngu"], t["kieu"]))

    srt = data.decode("utf-8") if isinstance(data, bytes) else data
    # Bóc SRT thành chữ trơn: bỏ dòng số thứ tự và dòng mốc giờ, nhưng giữ nguyên
    # dòng chữ kể cả khi nó cũng toàn số (đếm ngược, năm sản xuất...).
    cues = []
    for block in re.split(r"\n\s*\n", srt.replace("\r\n", "\n").replace("\r", "\n").strip()):
        chu = []
        for i, dong in enumerate(block.splitlines()):
            dong = dong.strip()
            if not dong or "-->" in dong or (i == 0 and re.match(r"^\d+$", dong)):
                continue
            sach = re.sub(r"<[^>]+>", "", dong).strip()
            if sach:
                chu.append(sach)
        cue = " ".join(chu)
        if cue and not (a.get("bo_lap") and cues and cues[-1] == cue):
            cues.append(cue)
    return {"video": ma, "ban_dung": t, "so_dong": len(cues),
            "loi_thoai": "\n".join(cues)}


# ── gộp từ youtube-studio-mcp (MIT) ────────────────────────────────────────
def youtube_phu_de_them(a):
    """Gắn một file phụ đề .srt/.vtt vào video ĐÃ đăng.

    Trước 01/10/2026 chỉ youtube_dang_video gắn được phụ đề, mà gắn đúng một lần
    ngay lúc đăng — hỏng là coi như mất, phải đăng lại cả file. Tách riêng ra đây
    để gắn lại được bất cứ lúc nào, kể cả cho video đăng từ lâu.

    Cần quyền youtube.force-ssl.
    """
    ma = _ma_video(a.get("video"))
    duong = a.get("tep")
    if not duong:
        raise LoiGoi("thiếu 'tep' — đường dẫn file phụ đề .srt hoặc .vtt")
    if not os.path.exists(duong):
        raise LoiGoi("không thấy file phụ đề: %s" % duong)
    if os.path.splitext(duong)[1].lower() not in (".srt", ".vtt", ".sbv"):
        raise LoiGoi("phụ đề phải là .srt, .vtt hoặc .sbv")
    if not any("force-ssl" in q for q in _quyen_token()):
        raise LoiGoi("token thiếu quyền youtube.force-ssl nên không gắn được phụ đề. "
                     "Thêm scope đó vào QUYEN trong cap_quyen.py, xoá token.json, "
                     "chạy lại: python cap_quyen.py")

    nn = a.get("ngon_ngu") or "vi"
    from googleapiclient.http import MediaFileUpload
    try:
        r = _yt().captions().insert(
            part="snippet",
            body={"snippet": {"videoId": ma, "language": nn,
                              "name": a.get("ten") or nn.upper(),
                              "isDraft": False}},
            media_body=MediaFileUpload(duong, resumable=False)).execute()
    except Exception as e:      # noqa: BLE001
        ro = _dich_loi_google(e)
        if ro:
            raise ro
        raise LoiGoi("gắn phụ đề không được: %s" % e)
    return {"video": ma, "link": "https://youtu.be/" + ma, "phu_de": r.get("id"),
            "ngon_ngu": nn, "tep": duong,
            "ghi_chu": "Đã gắn. Người xem bật/tắt được, và YouTube dịch tự động "
                       "sang tiếng khác từ bản này."}


def youtube_anh_bia(a):
    """Đặt ảnh bìa (thumbnail) mới cho video, lấy từ file ảnh trên máy."""
    ma = _ma_video(a.get("video"))
    duong = a.get("anh")
    if not duong:
        raise LoiGoi("thiếu 'anh' — đường dẫn file ảnh trên máy")
    if not os.path.exists(duong):
        raise LoiGoi("không thấy file ảnh: %s" % duong)
    co = os.path.getsize(duong)
    if co > 2 * 1024 * 1024:
        raise LoiGoi("ảnh nặng %.1f MB, YouTube chỉ nhận tối đa 2 MB" % (co / 1048576.0))
    duoi = os.path.splitext(duong)[1].lower()
    if duoi not in (".jpg", ".jpeg", ".png", ".gif", ".bmp"):
        raise LoiGoi("YouTube chỉ nhận .jpg .png .gif .bmp — file đang là %s" % duoi)

    from googleapiclient.http import MediaFileUpload
    try:
        r = _yt().thumbnails().set(
            videoId=ma, media_body=MediaFileUpload(duong, resumable=False)).execute()
    except Exception as e:      # noqa: BLE001
        ro = _dich_loi_google(e)
        if ro:
            raise ro
        # Đứt mạng ≠ chưa xác minh. Bản cũ đổ hết cho "chưa xác minh" nên
        # 01/10/2026 báo sai khi SSL đứt lúc đường lên đang kẹt vì tải video.
        t = str(e)
        if any(k in t for k in ("EOF occurred", "timed out", "Connection",
                                "SSLError", "BrokenPipe")):
            raise LoiGoi("đặt ảnh bìa đứt giữa chừng (%s). Đây là lỗi MẠNG, "
                         "không phải chưa xác minh — hay gặp khi đang tải "
                         "video khác chiếm hết đường lên. Chờ tải xong rồi "
                         "gọi lại." % t)
        raise LoiGoi("đặt ảnh bìa không được: %s. Nếu là lỗi 403 thì kênh "
                     "phải được XÁC MINH (youtube.com/verify) mới đặt được "
                     "ảnh bìa riêng." % t)
    return {"video": ma, "link": "https://youtu.be/" + ma, "anh_da_dat": duong,
            "co_file_byte": co, "ban_youtube_luu": (r.get("items") or [{}])[0],
            "ghi_chu": "đã ghi lên kênh thật. Ảnh mới có thể mất vài phút mới hiện đủ "
                       "mọi nơi vì YouTube còn phải tạo các bản thu nhỏ."}


def youtube_tra_loi_binh_luan(a):
    """Trả lời một bình luận, hoặc đăng bình luận mới lên video của kênh.

    Cần quyền force-ssl. Viết dưới danh nghĩa kênh công ty nên PHẢI đưa người
    dùng duyệt chữ trước khi gọi.
    """
    chu = (a.get("noi_dung") or "").strip()
    if not chu:
        raise LoiGoi("thiếu 'noi_dung' — chữ cần đăng")
    if len(chu) > 10000:
        raise LoiGoi("bình luận tối đa 10.000 ký tự, đang %d" % len(chu))
    yt = _yt()
    tra_loi = a.get("tra_loi_binh_luan")
    try:
        if tra_loi:
            r = yt.comments().insert(part="snippet", body={"snippet": {
                "parentId": tra_loi, "textOriginal": chu}}).execute()
            return {"kieu": "trả lời", "ma_binh_luan": r["id"], "tra_loi_cho": tra_loi,
                    "noi_dung": r["snippet"].get("textOriginal"),
                    "ghi_chu": "đã đăng công khai dưới tên kênh"}
        ma = _ma_video(a.get("video"))
        r = yt.commentThreads().insert(part="snippet", body={"snippet": {
            "videoId": ma,
            "topLevelComment": {"snippet": {"textOriginal": chu}}}}).execute()
        return {"kieu": "bình luận mới", "video": ma, "ma_binh_luan": r["id"],
                "noi_dung": chu, "ghi_chu": "đã đăng công khai dưới tên kênh"}
    except LoiGoi:
        raise
    except Exception as e:      # noqa: BLE001
        ro = _dich_loi_google(e)
        if ro:
            raise ro
        raise LoiGoi("đăng không được: %s" % e)


# ── gộp từ python-youtube / pyyoutube (MIT) ────────────────────────────────
def youtube_tim_cong_khai(a):
    """Tìm video công khai của NGƯỜI KHÁC — chỉ cần khoá API, không cần OAuth.

    Dùng để xem đối thủ đặt tiêu đề thế nào, hoặc tra video kỹ thuật tham khảo.
    """
    tu_khoa = a.get("tu_khoa")
    if not tu_khoa:
        raise LoiGoi("thiếu 'tu_khoa'")
    khoa = os.environ.get("OTL_YT_API_KEY")
    if not khoa:
        f = os.path.join(THUMUC, "api_key.txt")
        if os.path.exists(f):
            khoa = io.open(f, encoding="utf-8").read().strip()
    if not khoa:
        raise LoiGoi("chưa có khoá API. Vào Google Cloud Console → APIs & Services → "
                     "Credentials → Create credentials → API key, rồi lưu vào "
                     "%s\\api_key.txt (hoặc đặt biến môi trường OTL_YT_API_KEY). Khoá "
                     "này chỉ đọc dữ liệu công khai, không đụng được kênh mình."
                     % THUMUC)
    try:
        from pyyoutube import Api
    except ImportError:
        raise LoiGoi("thiếu thư viện. Chạy: pip install python-youtube")

    n = min(int(a.get("so_luong", 15)), 50)
    them = {"order": a["sap_xep"]} if a.get("sap_xep") else {}
    try:
        r = Api(api_key=khoa).search_by_keywords(
            q=tu_khoa, search_type=["video"], count=n, limit=min(n, 50),
            return_json=True, **them)
    except Exception as e:      # noqa: BLE001
        raise LoiGoi("tìm không được: %s" % e)

    ra = []
    for x in (r.get("items") or []):
        s = x.get("snippet") or {}
        mv = (x.get("id") or {}).get("videoId")
        ra.append({"ma": mv, "tieu_de": s.get("title"), "kenh": s.get("channelTitle"),
                   "dang_ngay": s.get("publishedAt"),
                   "mo_ta": (s.get("description") or "")[:200],
                   "link": ("https://youtu.be/" + mv) if mv else None})
    return {"tu_khoa": tu_khoa, "so_ket_qua": len(ra), "ket_qua": ra,
            "ghi_chu": "dữ liệu công khai của người khác, tìm bằng khoá API riêng — "
                       "KHÔNG tốn hạn mức của phần quản lý kênh mình"}


# Đuôi YouTube nhận; danh sách này hẹp hơn thực tế nhưng đủ dùng và chặn được
# việc lỡ trỏ vào file không phải video.
DUOI_VIDEO = (".mp4", ".mov", ".avi", ".wmv", ".flv", ".webm", ".mpeg", ".mpg",
              ".m4v", ".mkv", ".3gp")

CHE_DO_HOP_LE = ("private", "unlisted", "public")


def _quyen_token():
    """Scope THẬT đang có trong token.json. Biết trước thì báo thiếu quyền ngay,
    khỏi tải xong 3 GB mới ăn 403 như lần đăng 01/10/2026."""
    try:
        return json.load(io.open(TOKEN, encoding="utf-8")).get("scopes") or []
    except Exception:      # noqa: BLE001
        return []


def _trang_thai_dai():
    """Kênh có được đăng video dài quá 15 phút không — HỎI YouTube, không đoán.

    channels.list(part="status").longUploadsStatus trả một trong:
        allowed     đã xác minh, đăng dài bao nhiêu cũng được
        eligible    đủ điều kiện nhưng CHƯA xác minh ở youtube.com/verify
        disallowed  không được phép (kênh bị gậy bản quyền...)
    Hỏi không được thì trả None để bên gọi cảnh báo nhẹ, đừng chặn oan.
    """
    try:
        r = _yt().channels().list(part="status", mine=True).execute()
        return r["items"][0]["status"].get("longUploadsStatus")
    except Exception:      # noqa: BLE001
        return None


def _do_dai_video(duong):
    """Giây của file, lấy bằng ffprobe. Không có ffprobe thì trả None."""
    import subprocess
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", duong],
            capture_output=True, text=True, timeout=60)
        return float(r.stdout.strip())
    except Exception:      # noqa: BLE001 — thiếu ffprobe thì bỏ qua, không chặn
        return None


def youtube_dang_video(a):
    """Đăng một video MỚI lên kênh.

    Mặc định để chế độ RIÊNG TƯ (private). Đăng công khai ngay là việc không rút
    lại được — người xem, đăng ký và cả Google Search có thể bắt được bản chưa
    duyệt chỉ trong vài giây. Nên cứ đăng riêng tư, xem lại trên Studio, rồi mới
    tự tay chuyển sang công khai.
    """
    duong = a.get("tep")
    if not duong:
        raise LoiGoi("thiếu 'tep' — đường dẫn file video trên máy")
    if not os.path.exists(duong):
        raise LoiGoi("không thấy file video: %s" % duong)
    duoi = os.path.splitext(duong)[1].lower()
    if duoi not in DUOI_VIDEO:
        raise LoiGoi("đuôi %s không phải định dạng video YouTube nhận" % duoi)

    tieu_de = (a.get("tieu_de") or "").strip()
    if not tieu_de:
        raise LoiGoi("thiếu 'tieu_de'")
    if len(tieu_de) > 100:
        raise LoiGoi("tiêu đề %d ký tự, YouTube chỉ cho tối đa 100" % len(tieu_de))

    mo_ta = a.get("mo_ta") or ""
    if len(mo_ta) > 5000:
        raise LoiGoi("mô tả %d ký tự, YouTube chỉ cho tối đa 5000" % len(mo_ta))

    che_do = (a.get("che_do") or "private").lower()
    if che_do not in CHE_DO_HOP_LE:
        raise LoiGoi("'che_do' phải là private / unlisted / public — đang là '%s'" % che_do)

    tag = a.get("tag") or []
    if isinstance(tag, str):
        tag = [t.strip() for t in tag.split(",") if t.strip()]

    co = os.path.getsize(duong)
    canh_bao = []

    # Video dài quá 15 phút thì kênh phải xác minh. Hỏi thẳng YouTube chứ đừng
    # đoán theo độ dài file — bản cũ kêu "CHƯA XÁC MINH" cả khi đã xác minh rồi.
    giay = _do_dai_video(duong)
    if giay and giay > 15 * 60:
        tt = _trang_thai_dai()
        phut = "%d phút %02d giây" % (int(giay) // 60, int(giay) % 60)
        if tt == "eligible":
            raise LoiGoi(
                "Video dài %s mà kênh CHƯA xác minh — YouTube sẽ nuốt hết %.2f GB "
                "rồi mới báo lỗi. Vào youtube.com/verify xác minh bằng số điện "
                "thoại (vài phút), xong chạy lại lệnh này."
                % (phut, co / 1e9))
        if tt == "disallowed":
            raise LoiGoi("Video dài %s nhưng kênh KHÔNG được phép đăng video dài "
                         "(longUploadsStatus=disallowed). Kiểm cảnh cáo bản quyền "
                         "trong YouTube Studio." % phut)
        if tt is None:
            canh_bao.append("Video dài %s; hỏi trạng thái xác minh của kênh không "
                            "được nên vẫn đăng. Chưa xác minh thì YouTube báo lỗi "
                            "sau khi xử lý." % phut)

    # Phụ đề rời cần force-ssl. Soát TRƯỚC khi tải, đừng để tải xong mới 403.
    bo_phu_de = False
    if a.get("phu_de") and not any("force-ssl" in q for q in _quyen_token()):
        bo_phu_de = True
        canh_bao.append(
            "Token thiếu quyền youtube.force-ssl nên BỎ QUA bước gắn phụ đề rời "
            "(video vẫn đăng, chữ đã nung sẵn trong hình). Muốn gắn được: thêm "
            "scope đó vào QUYEN trong cap_quyen.py, xoá token.json, chạy lại "
            "python cap_quyen.py, rồi dùng youtube_phu_de cho video này.")

    if che_do == "public":
        canh_bao.append("Đăng CÔNG KHAI ngay — ai cũng xem được lập tức, không rút lại được.")

    from googleapiclient.http import MediaFileUpload
    than = {
        "snippet": {"title": tieu_de, "description": mo_ta, "tags": tag,
                    "categoryId": str(a.get("danh_muc") or 28)},   # 28 = Science & Technology
        "status": {"privacyStatus": che_do, "selfDeclaredMadeForKids": False},
    }
    if a.get("ngon_ngu"):
        than["snippet"]["defaultLanguage"] = a["ngon_ngu"]
        than["snippet"]["defaultAudioLanguage"] = a["ngon_ngu"]

    # resumable=True để file lớn đứt mạng giữa chừng còn gửi tiếp được.
    tai = MediaFileUpload(duong, chunksize=8 * 1024 * 1024, resumable=True)
    try:
        yc = _yt().videos().insert(part="snippet,status", body=than, media_body=tai)
        tra, dem, t0 = None, 0, time.time()
        while tra is None:
            tt, tra = yc.next_chunk()
            # stdout là đường JSON-RPC của MCP — in vào đó là gãy giao thức.
            if tt is not None:
                dem += 1
                if dem % 4 == 0:        # ~mỗi 32 MB, đủ theo dõi mà không ngập log
                    da = tt.resumable_progress
                    toc = da / max(time.time() - t0, 1e-6)
                    sys.stderr.write(
                        "   tai len %5.1f%%  %.2f MB/s  con khoang %.0f phut\n"
                        % (da * 100.0 / co, toc / 1e6, (co - da) / max(toc, 1) / 60))
                    sys.stderr.flush()
    except Exception as e:      # noqa: BLE001
        ro = _dich_loi_google(e)
        if ro:
            raise ro
        raise LoiGoi("đăng video không được: %s" % e)

    ma = tra["id"]
    kq = {"video": ma, "link": "https://youtu.be/" + ma,
          "studio": "https://studio.youtube.com/video/%s/edit" % ma,
          "tieu_de": tieu_de, "che_do": che_do, "co_file_byte": co,
          "tep_nguon": duong}
    if giay:
        kq["dai_giay"] = round(giay, 1)

    # Phụ đề rời: có thì gắn luôn, để YouTube bật/tắt và tự dịch được.
    if a.get("phu_de") and not bo_phu_de:
        pd = a["phu_de"]
        if not os.path.exists(pd):
            canh_bao.append("Không thấy file phụ đề %s — video đã đăng, phụ đề CHƯA gắn." % pd)
        else:
            try:
                r2 = _yt().captions().insert(
                    part="snippet",
                    body={"snippet": {"videoId": ma, "language": a.get("ngon_ngu") or "en",
                                      "name": "English", "isDraft": False}},
                    media_body=MediaFileUpload(pd, resumable=False)).execute()
                kq["phu_de_da_gan"] = {"tep": pd, "ma": r2.get("id")}
            except Exception as e:      # noqa: BLE001
                canh_bao.append("Video đã đăng nhưng gắn phụ đề hỏng: %s" % e)

    kq["ghi_chu"] = ("ĐÃ ĐĂNG LÊN KÊNH THẬT. YouTube còn phải xử lý vài phút mới "
                     "xem được ở độ phân giải cao. Mốc chương chỉ hiện khi phần mô tả "
                     "có mốc đầu là 00:00, đủ từ 3 mốc, mỗi đoạn từ 10 giây.")
    if canh_bao:
        kq["canh_bao"] = canh_bao
    return kq


HAM = {"youtube_kiem_tra": youtube_kiem_tra,
       "youtube_dang_video": youtube_dang_video,
       "youtube_kenh": youtube_kenh,
       "youtube_video": youtube_video,
       "youtube_so_lieu": youtube_so_lieu,
       "youtube_binh_luan": youtube_binh_luan,
       "youtube_sua_video": youtube_sua_video,
       "youtube_loi_thoai": youtube_loi_thoai,
       "youtube_phu_de": youtube_phu_de,
       "youtube_danh_sach_phat": youtube_danh_sach_phat,
       "youtube_thay_hang_loat": youtube_thay_hang_loat,
       "youtube_phu_de_them": youtube_phu_de_them,
       "youtube_anh_bia": youtube_anh_bia,
       "youtube_tra_loi_binh_luan": youtube_tra_loi_binh_luan,
       "youtube_tim_cong_khai": youtube_tim_cong_khai}

TOOLS = [
    {"name": "youtube_kiem_tra",
     "description": "Kiểm nhanh đã nối được kênh YouTube chưa và đang nối vào kênh nào. "
                    "Gọi cái này TRƯỚC khi báo lỗi cho người dùng — nó nói rõ thiếu "
                    "khoá, hết hạn token, hay tài khoản không có kênh.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "youtube_dang_video",
     "description": "ĐĂNG MỘT VIDEO MỚI lên kênh từ file trên máy. Mặc định để chế độ "
                    "RIÊNG TƯ — đăng công khai là việc KHÔNG RÚT LẠI ĐƯỢC, nên phải hỏi "
                    "người dùng rồi mới đặt che_do='public'. Gắn được luôn file phụ đề "
                    ".srt. Cần quyền youtube.upload: thiếu thì xoá token.json, chạy "
                    "114_Youtube/cap_quyen.py cấp lại. Kênh chưa xác minh chỉ đăng được "
                    "video tối đa 15 phút.",
     "inputSchema": {"type": "object", "properties": {
         "tep": {"type": "string", "description": "đường dẫn file video trên máy"},
         "tieu_de": {"type": "string", "description": "tiêu đề, tối đa 100 ký tự"},
         "mo_ta": {"type": "string", "description": "mô tả, tối đa 5000 ký tự. Muốn có "
                   "mốc chương thì mốc đầu phải là 00:00, đủ từ 3 mốc, mỗi đoạn từ 10 giây"},
         "tag": {"type": "array", "items": {"type": "string"}, "description": "danh sách tag"},
         "che_do": {"type": "string", "description": "private (mặc định) / unlisted / public"},
         "danh_muc": {"type": "integer", "description": "mã danh mục, mặc định 28 = Khoa học & Kỹ thuật"},
         "ngon_ngu": {"type": "string", "description": "mã ngôn ngữ, ví dụ en hoặc vi"},
         "phu_de": {"type": "string", "description": "đường dẫn file .srt gắn kèm (tuỳ chọn)"}},
         "required": ["tep", "tieu_de"]}},
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
    {"name": "youtube_sua_video",
     "description": "GHI LÊN KÊNH THẬT: đổi tiêu đề, mô tả, tag hoặc chế độ riêng tư "
                    "của một video đã đăng. Sửa xong người xem thấy ngay, nên PHẢI "
                    "đưa người dùng đọc và duyệt chữ mới trước khi gọi. Trường nào "
                    "không truyền thì giữ nguyên. Trả về cả bản trước và bản sau để "
                    "đối chiếu. Không đăng, không xoá video được.",
     "inputSchema": {"type": "object", "properties": {
         "video": {"type": "string", "description": "mã video, lấy từ youtube_video"},
         "tieu_de": {"type": "string", "description": "tiêu đề mới, tối đa 100 ký tự"},
         "mo_ta": {"type": "string", "description": "mô tả mới, tối đa 5000 ký tự. "
                   "GHI ĐÈ cả phần mô tả cũ chứ không nối thêm — muốn giữ phần cũ "
                   "thì đọc bằng youtube_video rồi gửi lại cả bài"},
         "tag": {"type": "array", "items": {"type": "string"},
                 "description": "bộ tag mới, thay cho bộ tag cũ. Tổng tối đa 500 ký tự"},
         "rieng_tu": {"type": "string", "description": "public, unlisted hoặc private"}},
         "required": ["video"]}},
    {"name": "youtube_loi_thoai",
     "description": "Lấy LỜI THOẠI của video kèm mốc thời gian — cách rẻ nhất để biết "
                    "video quay gì mà không phải cắt khung hình ra xem. KHÔNG cần cấp "
                    "quyền OAuth, nên chạy được cả khi token hỏng, và chạy được trên "
                    "video của bất kỳ ai chứ không riêng kênh mình. Mốc 'luc' trả về "
                    "dán thẳng vào mô tả là thành chương YouTube.",
     "inputSchema": {"type": "object", "properties": {
         "video": {"type": "string", "description": "mã video hoặc dán nguyên link"},
         "ngon_ngu": {"type": "array", "items": {"type": "string"},
                      "description": "thứ tự ưu tiên ngôn ngữ, mặc định [\"vi\",\"en\"]"},
         "gop_giay": {"type": "integer", "description": "gộp lời thoại thành khối bao "
                      "nhiêu giây, mặc định 30. Để 0 là giữ nguyên từng mẩu (rất dài)"},
         "chi_liet_ke": {"type": "boolean", "description": "chỉ xem video có phụ đề "
                         "tiếng gì, chưa lấy nội dung"}},
         "required": ["video"]}},
    {"name": "youtube_phu_de",
     "description": "Đọc bản phụ đề CHÍNH THỨC đã tải lên kênh (kể cả bản nháp chưa "
                    "công khai). Cần quyền youtube.force-ssl — chưa cấp thì công cụ "
                    "nói rõ cách thêm. Chỉ muốn biết video nói gì thì dùng "
                    "youtube_loi_thoai, nhẹ hơn và không cần quyền.",
     "inputSchema": {"type": "object", "properties": {
         "video": {"type": "string", "description": "mã video hoặc link"},
         "ngon_ngu": {"type": "string", "description": "mã ngôn ngữ, ví dụ vi hoặc en"},
         "chi_liet_ke": {"type": "boolean", "description": "chỉ liệt kê các bản có sẵn"},
         "bo_lap": {"type": "boolean", "description": "bỏ các dòng lặp liền nhau — "
                    "hợp với bản máy tự nghe, đừng bật cho bản người làm"}},
         "required": ["video"]}},
    {"name": "youtube_danh_sach_phat",
     "description": "Liệt kê các playlist của kênh. Truyền 'danh_sach' để xem video "
                    "bên trong một playlist cụ thể.",
     "inputSchema": {"type": "object", "properties": {
         "danh_sach": {"type": "string", "description": "mã playlist. Bỏ trống thì "
                       "liệt kê tất cả playlist của kênh"},
         "so_luong": {"type": "integer", "description": "mặc định 50"}}}},
    {"name": "youtube_thay_hang_loat",
     "description": "Tìm & thay một đoạn chữ trong tiêu đề hoặc mô tả của NHIỀU video "
                    "cùng lúc — ví dụ đổi số điện thoại hay địa chỉ web cũ trên cả "
                    "kênh. MẶC ĐỊNH CHỈ XEM TRƯỚC, không ghi gì: gọi lần đầu để lấy "
                    "danh sách sẽ đổi, đưa người dùng duyệt, rồi mới gọi lại với "
                    "thuc_thi=true. Mỗi video ghi tốn 50 đơn vị hạn mức ngày (tổng "
                    "10.000), nên đừng chạy tràn lan.",
     "inputSchema": {"type": "object", "properties": {
         "tim": {"type": "string", "description": "chữ cần tìm"},
         "thay": {"type": "string", "description": "chữ thay vào. Để chuỗi rỗng là xoá"},
         "truong": {"type": "string", "description": "mo_ta (mặc định) hoặc tieu_de"},
         "bieu_thuc": {"type": "boolean", "description": "coi 'tim' là biểu thức chính "
                       "quy Python thay vì chữ thường"},
         "so_luong": {"type": "integer", "description": "trần số video sửa một lượt, "
                      "mặc định 20, tối đa 100"},
         "thuc_thi": {"type": "boolean", "description": "true mới GHI THẬT lên kênh. "
                      "Bỏ trống hoặc false là chỉ xem trước"}},
         "required": ["tim", "thay"]}},
    {"name": "youtube_phu_de_them",
     "description": "GHI LÊN KÊNH THẬT: gắn file phụ đề .srt/.vtt vào một video đã "
                    "đăng, để người xem bật/tắt được và YouTube dịch tự động sang "
                    "tiếng khác. Dùng cả cho video đăng từ lâu. Cần quyền "
                    "youtube.force-ssl — thiếu thì công cụ báo ngay, không gọi API.",
     "inputSchema": {"type": "object", "properties": {
         "video": {"type": "string", "description": "mã video hoặc link"},
         "tep": {"type": "string", "description": "đường dẫn file .srt/.vtt trên máy"},
         "ngon_ngu": {"type": "string", "description": "mã ngôn ngữ của phụ đề, "
                      "vd vi hoặc en. Mặc định vi"},
         "ten": {"type": "string", "description": "tên hiện trong trình chọn phụ đề"}},
         "required": ["video", "tep"]}},
    {"name": "youtube_anh_bia",
     "description": "GHI LÊN KÊNH THẬT: đặt ảnh bìa (thumbnail) mới cho một video, lấy "
                    "từ file ảnh trên máy. Tối đa 2 MB, định dạng jpg/png/gif/bmp. Kênh "
                    "phải được xác minh thì YouTube mới cho đặt ảnh bìa riêng. Đưa "
                    "người dùng xem ảnh và duyệt trước khi gọi.",
     "inputSchema": {"type": "object", "properties": {
         "video": {"type": "string", "description": "mã video hoặc link"},
         "anh": {"type": "string", "description": "đường dẫn đầy đủ tới file ảnh"}},
         "required": ["video", "anh"]}},
    {"name": "youtube_tra_loi_binh_luan",
     "description": "GHI LÊN KÊNH THẬT: trả lời một bình luận, hoặc đăng bình luận mới "
                    "lên video của kênh. Chữ đăng ra mang danh nghĩa kênh công ty nên "
                    "PHẢI đưa người dùng duyệt trước. Cần quyền youtube.force-ssl — "
                    "chưa cấp thì công cụ nói rõ cách thêm.",
     "inputSchema": {"type": "object", "properties": {
         "noi_dung": {"type": "string", "description": "chữ cần đăng, tối đa 10.000 ký tự"},
         "tra_loi_binh_luan": {"type": "string", "description": "mã bình luận cần trả "
                               "lời. Bỏ trống thì đăng bình luận mới lên video"},
         "video": {"type": "string", "description": "mã video — chỉ cần khi đăng bình "
                   "luận mới"}},
         "required": ["noi_dung"]}},
    {"name": "youtube_tim_cong_khai",
     "description": "Tìm video công khai của NGƯỜI KHÁC trên YouTube — xem đối thủ đặt "
                    "tiêu đề thế nào, hay tra video kỹ thuật tham khảo. Dùng khoá API "
                    "riêng (api_key.txt), không cần OAuth và không đụng gì tới kênh "
                    "mình. Không liệt kê được video của kênh mình — việc đó dùng "
                    "youtube_video.",
     "inputSchema": {"type": "object", "properties": {
         "tu_khoa": {"type": "string", "description": "chữ cần tìm"},
         "so_luong": {"type": "integer", "description": "mặc định 15, tối đa 50"},
         "sap_xep": {"type": "string", "description": "relevance (mặc định), date, "
                     "viewCount, rating"}},
         "required": ["tu_khoa"]}},
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
                # Lỗi của Google nói rất khó hiểu (nhất là hết hạn mức ngày và
                # token thiếu quyền). Dịch được thì báo bằng lời người đọc hiểu.
                ro = _dich_loi_google(e)
                _send({"jsonrpc": "2.0", "id": mid, "result": {
                    "content": [{"type": "text",
                                 "text": ("Lỗi: %s" % ro) if ro
                                 else ("Lỗi bất ngờ: %r" % e)}],
                    "isError": True}})
        elif mid is not None:
            _send({"jsonrpc": "2.0", "id": mid,
                   "error": {"code": -32601,
                             "message": "method không hỗ trợ: %s" % method}})


if __name__ == "__main__":
    main()
