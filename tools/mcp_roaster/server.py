# -*- coding: utf-8 -*-
"""MCP server cho máy rang OTL — tầng ĐỌC (T0) + tầng LÁI (T2, phải tự bật).

Giai đoạn C và G của docs/plan/plan-mcp-api-extension.md.

MẶC ĐỊNH: chỉ ĐỌC — trạng thái, hồ sơ, lịch sử mẻ, đường cong, tham số $M, để
phân tích mẻ và tìm mẻ lệch. Không có công cụ nào lái máy xuất hiện.

BẬT TẦNG LÁI: đặt OTL_MCP_CONTROL=1 khi khởi động server. Đó là hành động phải
làm TẠI CHỖ trên máy tính đứng cạnh máy rang, không bật được từ xa và không tự
bật giữa phiên. Kể cả bật rồi, mỗi lệnh vẫn phải qua đủ chuỗi sau:

    khoá API phạm vi control  →  thợ bật PC control TRÊN HMI bằng tay
      →  lượt lái 15 phút/lượt, trần 60 phút cả phiên  →  hãm bước + hãm tần suất
      →  firmware kiểm dải, watchdog 3 giây, chốt mồi hụt đóng gas

Luật nằm ở app (tools/roast_lab_hmi.py) và firmware, KHÔNG nằm ở file này —
file này chỉ là bộ chuyển ngữ. Ai viết MCP server khác hay gọi thẳng bằng curl
thì vẫn dính đúng bấy nhiêu luật. Luật đặt ở tầng AI là luật tự nguyện.

DÂY CHUYỀN NHỊP SỐNG (chỗ dễ hiểu sai nhất): server này CỐ Ý không có luồng nền
nhấp nhịp giữ quyền. Nhịp chỉ sinh ra khi AI thật sự LÁI — lệnh ghi, hoặc gọi
roaster_lai_nhip cho tường minh. Từ 2026-09-09 việc ĐỌC trạng thái KHÔNG còn
tính là nhịp: một vòng lặp poll còn chạy chỉ chứng minh tiến trình còn sống,
không chứng minh tác nhân còn tỉnh — mà chốt im-lặng sinh ra đúng để bắt ca AI
treo giữa mẻ. AI treo, hết quota hay đứt mạng là app ngừng nhấp heartbeat xuống
máy, và trong 3 giây firmware trả quyền về HMI kèm còi. Thêm một luồng nhấp nền
vào đây là phá đúng cái van an toàn đó — đừng làm.

VÀO BẰNG GÌ — hai đường, chọn một:
    · TÀI KHOẢN APP (dễ nhất): set OTL_API_USER=Master + OTL_API_PIN=<PIN>, hoặc
      gọi công cụ roaster_dang_nhap giữa phiên. Đúng tài khoản ở màn khoá của app.
      Master có đủ ba phạm vi; thợ chỉ đọc (+ cấu hình nếu được giao quyền).
      Token sống 8 giờ, hết hạn thì server tự đăng nhập lại.
    · KHOÁ API: hợp cho thứ chạy nền dài ngày (khoá không hết hạn, phạm vi hẹp).
Đăng nhập bằng mật khẩu KHÔNG lỏng hơn khoá: app xếp token đăng nhập vào đúng
nhóm "tác nhân tự động", nên vẫn phải xin lượt lái, vẫn dính hãm bước và hãm
tần suất y như khoá API.

Chạy:
    set OTL_API_KEY=otl_...        (khoá tạo trong app; đọc cần phạm vi read,
                                    lái cần thêm phạm vi control)
    set OTL_API_BASE=http://127.0.0.1:8555
    set OTL_MCP_CONTROL=1          (tuỳ chọn — mở tầng lái)
    python tools/mcp_roaster/server.py

Thuần stdlib, không cần cài gì — máy xưởng thường không có pip.
"""
import io
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

VERSION = "0.4.0"

# Windows: stdio mặc định cp1252 → tên hồ sơ tiếng Việt làm hỏng giao thức
try:
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace")
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", newline="\n")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

BASE = (os.environ.get("OTL_API_BASE") or "http://127.0.0.1:8555").rstrip("/")

# urlopen trơn dò proxy trong registry Windows ở MỖI lần gọi: đo 13/10/2026 là
# 12,9 ms/lượt so với 9,4 ms khi bỏ dò. App nằm cùng máy thì proxy vô nghĩa (còn
# hại: proxy công ty chặn 127.0.0.1 là mất app). Địa chỉ ngoài máy thì giữ dò proxy.
_HOST = urllib.parse.urlsplit(BASE).hostname or ""
_MO = (urllib.request.build_opener(urllib.request.ProxyHandler({}))
       if _HOST in ("127.0.0.1", "localhost", "::1") else urllib.request.build_opener())


def _khoa():
    """Khoá API: biến môi trường trước, rồi tới file cạnh app.

    Có đường đọc FILE để khỏi phải nhét khoá vào .mcp.json — file cấu hình đó
    không bị .gitignore chặn, nên một khoá phạm vi 'control' nằm trần trong đó
    là một ngày nào đó lên repo PUBLIC. apikey.txt thì nằm cạnh dữ liệu app,
    không nằm trong repo."""
    k = os.environ.get("OTL_API_KEY") or ""
    if k:
        return k
    import pathlib
    goc = pathlib.Path(__file__).resolve().parent.parent
    for p in (goc / "dist" / "apikey.txt", goc / "apikey.txt"):
        try:
            if p.exists():
                v = p.read_text(encoding="utf-8").strip()
                if v:
                    return v
        except OSError:
            pass
    return ""


def _token_da_luu():
    """Token đăng nhập do tools/otl_api.py cất — dùng chung cho tiện, khỏi bắt
    thợ đăng nhập hai lần cho hai công cụ."""
    import pathlib
    goc = pathlib.Path(__file__).resolve().parent.parent
    for p in (goc / "dist" / "apitoken.json", goc / "apitoken.json"):
        try:
            if p.exists():
                import time as _t
                d = json.loads(p.read_text(encoding="utf-8"))
                if float(d.get("het_luc", 0)) > _t.time():
                    return str(d.get("token") or "")
        except (OSError, ValueError):
            pass
    return ""


KEY = _khoa() or _token_da_luu()
TEN_TK = (os.environ.get("OTL_API_USER") or "").strip()
MK_TK = (os.environ.get("OTL_API_PIN") or "").strip()


def _dang_nhap(ten=None, mk=None, mo_khoa_app=True):
    """Đổi tài khoản app (tên + PIN) lấy token phiên, gán vào KEY cho mọi lệnh sau.

    PIN chỉ đi trong bộ nhớ và trên vòng lặp localhost tới app — KHÔNG ghi ra
    đĩa ở đây. Muốn nhớ giữa các lần chạy thì dùng
    `python tools/otl_api.py dangnhap`, chỗ đó cất token (không cất PIN)."""
    global KEY
    ten = (ten or TEN_TK or "Master").strip()
    mk = str(mk if mk not in (None, "") else MK_TK)
    if not mk:
        raise LoiGoi("chưa có mật khẩu. Đặt OTL_API_USER/OTL_API_PIN khi chạy "
                     "server, hoặc gọi roaster_dang_nhap(ten, mk).")
    data = json.dumps({"name": ten, "pin": mk,
                       "mo_khoa_app": bool(mo_khoa_app)}).encode("utf-8")
    req = urllib.request.Request(BASE + "/api/v1/login", data=data, method="POST")
    req.add_header("Content-Type", "application/json; charset=utf-8")
    try:
        with _MO.open(req, timeout=15) as r:
            kq = json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        try:
            kq = json.loads(e.read().decode("utf-8") or "{}")
        except Exception:
            kq = {}
        loi = kq.get("err") or ("HTTP %s" % e.code)
        if loi == "sai_pin":
            raise LoiGoi("sai mật khẩu — còn %s lần trước khi bị khoá tạm"
                         % kq.get("left_tries", "?"))
        if loi == "locked":
            raise LoiGoi("tài khoản đang bị khoá tạm, chờ %s giây" % kq.get("left", "?"))
        if loi == "khong_co_tk":
            raise LoiGoi("app không có tài khoản tên '%s'" % ten)
        raise LoiGoi("đăng nhập hỏng: %s" % loi)
    except urllib.error.URLError as e:
        raise LoiGoi("không nối được app ở %s (%s). App OTL Roast Lab có đang chạy không?"
                     % (BASE, e.reason))
    if not kq.get("ok"):
        raise LoiGoi("đăng nhập hỏng: %s" % (kq.get("err") or "?"))
    KEY = kq["token"]
    return {"ok": True, "ten": kq.get("name"), "vai_tro": kq.get("role"),
            "pham_vi": kq.get("scopes"),
            "het_han_gio": int((kq.get("het_han_s") or 0) // 3600),
            "da_mo_khoa_man_hinh_app": bool(kq.get("mo_khoa_app"))}


def _thu_dang_nhap_lai():
    """App trả 401 (token hết hạn / app vừa khởi động lại) → thử đăng nhập lại
    MỘT lần nếu có sẵn tài khoản. Không có thì trả False để báo lỗi như cũ."""
    if not MK_TK:
        return False
    try:
        _dang_nhap()
        return True
    except LoiGoi:
        return False
# Tầng lái chỉ nạp khi người vận hành TỰ BẬT lúc khởi động server (§5 ĐK1).
# Không có đường nào bật nó giữa phiên — kể cả AI có đọc được file này.
CO_LAI = (os.environ.get("OTL_MCP_CONTROL") or "").strip() in ("1", "true", "True")
CO_CAU_HINH = (os.environ.get("OTL_MCP_CONFIG") or "").strip().lower() in ("1", "true")


def _so_tham_so_M():
    """Số $M lớn nhất, lấy từ NGUỒN PC_Link sinh sẵn — không ghi cứng.

    Số này phải đi theo firmware; hiện khối đã mở tới $M60. Ghi cứng một con số
    ở mô tả làm AI bỏ sót tham số mới mà không có lỗi rõ ràng.

    Hai đường lấy số, đều không cần cài gói nào: bản đồ Python sinh sẵn ở
    tools/pc_link_map.py, hoặc chính protocol/pc_link.json. Chép server này đi
    nơi khác mà thiếu cả hai thì trả None — mô tả nói chung chung chứ KHÔNG bịa
    một con số, vì con số sai còn tệ hơn không có số.
    """
    goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if goc not in sys.path:
        sys.path.append(goc)           # nối vào CUỐI: không che module chuẩn
    try:
        import pc_link_map
        return int(pc_link_map.CFG_MAXIDX)
    except Exception:
        pass
    try:
        duong = os.path.join(os.path.dirname(goc), "protocol", "pc_link.json")
        with io.open(duong, encoding="utf-8") as f:
            return int(json.load(f)["config"]["count"])
    except Exception:
        return None


SO_M = _so_tham_so_M()
_MO_TA_M = ("%d tham số" % SO_M) if SO_M else "khối tham số"
try:
    import pc_link_map as _PCL_MAP
except Exception:
    _PCL_MAP = None

# CHỈ những đường này được gọi. Chốt chặn thứ hai bên cạnh phạm vi quyền của khoá:
# kể cả ai đó đưa nhầm khoá 'control' vào biến môi trường, server này vẫn không có
# cách nào bắn lệnh xuống máy.
CHO_PHEP = (
    "/api/v1/snapshot", "/api/v1/profiles", "/api/v1/batches",
    "/api/v1/batches_count",
    "/api/v1/batch_curve", "/api/v1/batch_stats", "/api/v1/batches_curves",
    "/api/v1/mc_read", "/api/v1/state", "/api/v1/audit", "/api/v1/oplog",
    "/api/v1/lease",
    "/api/v1/assistant_skills", "/api/v1/assistant_skill", "/api/v1/assistant_capabilities",
)
# Đường GHI — chỉ dùng được khi CO_LAI bật. Danh sách đóng: không có đường nào
# khác gửi được lệnh xuống máy từ file này.
CHO_PHEP_GHI = (
    "/api/v1/write", "/api/v1/lease_open", "/api/v1/lease_beat",
    "/api/v1/lease_close",
)
# Hai ô thuộc dây chuyền an toàn — app cũng chặn, đây là lớp thứ hai cho chắc.
CAM_GHI = ("hb", "agent")


class LoiGoi(Exception):
    pass


def _goi(duong, tham_so=None, lan2=False):
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
        # Đọc toàn bộ $M gồm nhiều handshake nối tiếp, mỗi lượt tối đa 2,5 giây.
        with _MO.open(req, timeout=150 if goc == "/api/v1/mc_read" else 15) as r:
            return json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        if e.code == 401:
            if not lan2 and _thu_dang_nhap_lai():
                return _goi(duong, tham_so, lan2=True)
            raise LoiGoi("app từ chối: chưa đăng nhập. Đặt OTL_API_USER/OTL_API_PIN, "
                         "gọi roaster_dang_nhap, hoặc tạo khoá API phạm vi 'read' "
                         "trong app (Cài đặt → Tài khoản).")
        if e.code == 403:
            raise LoiGoi("khoá API không có phạm vi 'read'.")
        if e.code == 429:
            raise LoiGoi("gọi quá nhiều, đang bị hãm — chờ một phút.")
        raise LoiGoi("app trả HTTP %s" % e.code)
    except urllib.error.URLError as e:
        raise LoiGoi("không nối được app ở %s (%s). App OTL Roast Lab có đang chạy không?"
                     % (BASE, e.reason))


def _gui(duong, than=None, lan2=False):
    """POST một đường GHI. Chỉ chạy khi tầng lái đang bật."""
    cau_hinh = duong == "/api/v1/mc_write"
    if cau_hinh and not CO_CAU_HINH:
        raise LoiGoi("tầng cấu hình đang tắt; cần OTL_MCP_CONFIG=1")
    if not cau_hinh and not CO_LAI:
        raise LoiGoi("tầng lái đang TẮT. Người vận hành phải khởi động server "
                     "với OTL_MCP_CONTROL=1 ngay tại máy tính cạnh máy rang.")
    if duong not in CHO_PHEP_GHI and not cau_hinh:
        raise LoiGoi("đường %s không nằm trong danh sách ghi cho phép" % duong)
    data = json.dumps(than or {}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(BASE + duong, data=data, method="POST")
    req.add_header("Content-Type", "application/json; charset=utf-8")
    if KEY:
        req.add_header("Authorization", "Bearer " + KEY)
    try:
        with _MO.open(req, timeout=15) as r:
            kq = json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        if e.code == 401:
            if not lan2 and _thu_dang_nhap_lai():
                return _gui(duong, than, lan2=True)
            raise LoiGoi("app từ chối: chưa đăng nhập (OTL_API_USER/OTL_API_PIN, "
                         "roaster_dang_nhap, hoặc khoá API).")
        if e.code == 403:
            if cau_hinh:
                raise LoiGoi("tài khoản/khoá thiếu phạm vi 'config'")
            raise LoiGoi("tài khoản/khoá này không có phạm vi 'control' — thợ vận "
                         "hành chỉ đọc; lái máy phải là tài khoản Master hoặc khoá "
                         "cấp riêng, hoặc để thợ lái tay.")
        if e.code == 429:
            raise LoiGoi("gọi quá nhiều, đang bị hãm — chờ một phút.")
        raise LoiGoi("app trả HTTP %s" % e.code)
    except urllib.error.URLError as e:
        raise LoiGoi("không nối được app ở %s (%s)." % (BASE, e.reason))
    # App từ chối có lý do đọc được → đưa nguyên văn cho AI, đừng nuốt
    if isinstance(kq, dict) and kq.get("ok") is False:
        raise LoiGoi(kq.get("msg") or kq.get("err") or "máy từ chối")
    return kq


# ── Công cụ ───────────────────────────────────────────────────────────────────
def t_trang_thai(_):
    """Ảnh chụp máy lúc này."""
    return _goi("/api/v1/snapshot")


def t_ho_so(_):
    return _goi("/api/v1/profiles")


def t_ky_nang(_):
    return _goi("/api/v1/assistant_skills")


def t_doc_ky_nang(a):
    name = a.get("name")
    if not isinstance(name, str) or not name or len(name) > 64:
        raise LoiGoi("cần tên skill hợp lệ từ roaster_list_skills")
    return _goi("/api/v1/assistant_skill", {"name": name})


def t_kha_nang(_):
    return _goi("/api/v1/assistant_capabilities")


_NGAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _so_nguyen(v, mac_dinh, thap, cao, ten):
    """Số nguyên trong dải, hoặc LoiGoi nói rõ sai chỗ nào.

    bool bị loại tay: trong Python `True` là số nguyên hợp lệ, mà AI gửi
    `so_luong: true` thì ý nó chắc chắn không phải "lấy 1 mẻ"."""
    if v in (None, ""):
        return mac_dinh
    if isinstance(v, bool) or isinstance(v, float) or isinstance(v, (list, dict)):
        raise LoiGoi("%s phải là số nguyên" % ten)
    try:
        n = int(str(v).strip())
    except (TypeError, ValueError):
        raise LoiGoi("%s phải là số nguyên" % ten)
    if not thap <= n <= cao:
        raise LoiGoi("%s phải trong khoảng %d..%d" % (ten, thap, cao))
    return n


def _loc_me(a):
    """Bộ lọc lịch sử mẻ → tham số truy vấn của app. Dùng CHUNG cho danh sách và
    số tổng: hai bên lệch bộ lọc là ra "trang 1/0"."""
    q = {}
    tu_khoa = a.get("tu_khoa")
    if tu_khoa not in (None, ""):
        if not isinstance(tu_khoa, str):
            raise LoiGoi("tu_khoa phải là chuỗi")
        # Kho lọc bằng chữ không dấu nên tiếng Việt có dấu vẫn tìm được.
        q["q"] = tu_khoa.strip()[:200]
    for ten, khoa in (("tu_ngay", "from"), ("den_ngay", "to")):
        v = a.get(ten)
        if v in (None, ""):
            continue
        if not isinstance(v, str) or not _NGAY.match(v.strip()):
            raise LoiGoi("%s phải dạng YYYY-MM-DD" % ten)
        q[khoa] = v.strip()
    if q.get("from") and q.get("to") and q["from"] > q["to"]:
        raise LoiGoi("tu_ngay phải trước den_ngay")
    return q


def t_dem_me(a):
    """Đếm mẻ khớp bộ lọc. Rẻ hơn nhiều so với kéo cả trang về chỉ để đếm."""
    loc = _loc_me(a)
    d = _goi("/api/v1/batches_count", loc)
    tong = d.get("count")
    if tong is None:
        raise LoiGoi("app chưa đếm được: kho mẻ chưa mở hoặc đọc kho thất bại")
    return {"tong": int(tong), "loc": loc}


def t_danh_sach_me(a):
    """Các mẻ đã rang, có lọc và phân trang.

    Bộ lọc chạy DƯỚI KHO SQLite rồi mới cắt trang — trước đây server này kéo về
    một trang rồi mới cắt trong bộ nhớ, nên tìm "Cà phê đậm" trong kho 900 mẻ chỉ
    soi được 50 mẻ mới nhất và báo "không có". Và `tong` từng là số dòng của
    trang, tức đứng yên ở 50 dù kho có bao nhiêu mẻ."""
    loc = _loc_me(a)
    n = _so_nguyen(a.get("so_luong"), 20, 1, 500, "so_luong")
    bo_qua = _so_nguyen(a.get("bo_qua"), 0, 0, 1000000, "bo_qua")
    tong, ghi_chu = None, ""
    # Đếm và lấy trang chạy SONG SONG: hai lượt hỏi app độc lập, chạy nối tiếp
    # là cộng dồn thời gian (app là ThreadingHTTPServer nên chịu được cả hai).
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(2) as ex:
        f_dem = ex.submit(t_dem_me, a)
        f_ds = ex.submit(_goi, "/api/v1/batches", dict(loc, n=n, offset=bo_qua))
        try:
            tong = f_dem.result()["tong"]
        except LoiGoi as e:
            # Đếm hỏng KHÔNG được kéo cả danh sách hỏng theo, nhưng cũng không được
            # lấy len(ds) thay vào: đó đúng là con số sai mà đợt này đi sửa.
            ghi_chu = "chưa đếm được tổng: %s" % e
        d = f_ds.result()
    ds = d.get("batches")
    if ds is None:
        raise LoiGoi("app không đọc được kho mẻ (kho chưa mở, hoặc bộ lọc sai kiểu)")
    # `tong` đứng TRƯỚC `batches`: câu trả lời dài quá bị cắt đuôi, mà cắt mất con
    # số tổng thì AI lại đi đếm số dòng đang thấy — đúng cái lỗi vừa sửa.
    kq = {"tong": tong}
    if ghi_chu:
        kq["ghi_chu_tong"] = ghi_chu
    kq.update({"so_dong": len(ds), "bo_qua": bo_qua, "loc": loc, "batches": ds})
    return kq


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
    """Cả khối $M đọc từ máy. Mỗi tham số một lượt hỏi-đáp nên hơi chậm."""
    return _goi("/api/v1/mc_read")


def t_so_me(a):
    """So nhiều mẻ với nhau — đây mới là chỗ AI có ích thật: chỉ ra mẻ nào lệch."""
    ids = a.get("ma_me") or []
    if isinstance(ids, str):
        ids = [x.strip() for x in ids.split(",") if x.strip()]
    if len(ids) < 2:
        raise LoiGoi("cần ít nhất 2 'ma_me' để so")
    return _goi("/api/v1/batches_curves", {"ids": ",".join(str(i) for i in ids)})


def t_dang_nhap(a):
    """Đăng nhập bằng tài khoản app giữa phiên."""
    a = a or {}
    mo = a.get("mo_khoa_app")
    return _dang_nhap(a.get("ten"), a.get("mk"), True if mo is None else bool(mo))


def t_kiem_tra(_):
    """Kiểm nhanh: có nối được app không, khoá có dùng được không."""
    kq = {"dia_chi": BASE, "co_khoa": bool(KEY), "tang_lai_bat": CO_LAI,
          "cach_vao": ("khoá API" if KEY.startswith("otl_")
                       else ("đăng nhập tài khoản" if KEY else "CHƯA có gì")),
          "tai_khoan": TEN_TK or ("Master" if MK_TK else "")}
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


# ── Công cụ TẦNG LÁI (T2) — chỉ nạp khi CO_LAI ────────────────────────────
def t_lai_trang_thai(_):
    """Đang có ai cầm lái không, còn bao nhiêu phút, luật đang áp là gì."""
    d = _goi("/api/v1/lease")
    d["tang_lai_bat"] = CO_LAI
    return d


def t_lai_xin_quyen(a):
    """Xin lượt lái. Thất bại thường vì thợ chưa bật PC control trên HMI."""
    return _gui("/api/v1/lease_open", {"phut": a.get("so_phut")})


def t_lai_tra_quyen(a):
    return _gui("/api/v1/lease_close", {"ly_do": a.get("ly_do") or "xong việc"})


def t_lai_nhip(_):
    """Báo còn tỉnh để giữ lượt lái trong lúc đang cân nhắc.

    Từ 2026-09-09 việc ĐỌC trạng thái không còn tính là nhịp tim: một vòng lặp
    poll còn chạy không chứng minh được tác nhân còn tỉnh, mà chốt im-lặng sinh
    ra đúng để bắt ca tác nhân treo giữa mẻ. Nghĩ lâu thì gọi hàm này."""
    return _gui("/api/v1/lease_beat", {})


def _muc(a, ten="muc"):
    v = a.get(ten)
    if v in (None, ""):
        raise LoiGoi("thiếu %s" % ten)
    try:
        return float(v)
    except (TypeError, ValueError):
        raise LoiGoi("%s phải là số" % ten)


def _lenh(ten, gia_tri):
    if ten in CAM_GHI:
        raise LoiGoi("%s thuộc dây chuyền an toàn — không ghi được" % ten)
    return _gui("/api/v1/write", {"name": ten, "value": gia_tri})


def t_lai_gas(a):
    return _lenh("gas", _muc(a))


def t_lai_gio(a):
    return _lenh("air", _muc(a))


def t_lai_trong(a):
    return _lenh("drum", _muc(a))


def t_lai_lua(a):
    """Bật/tắt bếp. Bật mà 75 giây không lên lửa thì FIRMWARE tự đóng gas."""
    bat = a.get("bat")
    if type(bat) is bool:
        return _lenh("ignite", 1 if bat else 0)
    if type(bat) is int and bat in (0, 1):
        return _lenh("ignite", bat)
    raise LoiGoi("bat phải là boolean hoặc số nguyên 0/1")


def t_lai_hut(a):
    """Áp hút đặt (Pa, 90..250) và/hoặc bật PID gió theo áp hút."""
    kq = {}
    if a.get("ap") not in (None, ""):
        kq["ap"] = _lenh("vac", _muc(a, "ap"))
    if a.get("bat_pid") is not None:
        kq["pid"] = _lenh("vacen", 1 if a["bat_pid"] in (True, 1, "1", "true", "True") else 0)
    if not kq:
        raise LoiGoi("cần ít nhất một trong hai: ap hoặc bat_pid")
    return kq


def t_lai_lenh(a):
    """Đường chung cho các lệnh còn lại. App mới là bên phán xét tên lệnh hợp
    lệ hay không — ở đây KHÔNG chép lại bản đồ lệnh, chép là có ngày lệch."""
    ten = (a.get("ten") or "").strip()
    if not ten:
        raise LoiGoi("thiếu ten")
    if a.get("gia_tri") is None:
        raise LoiGoi("thiếu gia_tri")
    return _lenh(ten, a["gia_tri"])


TOOLS_LAI = [
    {"name": "roaster_lai_trang_thai",
     "description": "Xem lượt lái: có tác nhân nào đang cầm lái không, còn bao nhiêu "
                    "giây, và LUẬT đang áp (trần phút, bước nhảy tối đa, số lệnh mỗi "
                    "phút). Gọi cái này trước khi định lái.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "roaster_lai_xin_quyen",
     "description": "XIN QUYỀN LÁI MÁY RANG THẬT (bếp gas đang cháy). Chỉ được khi thợ "
                    "đã bật nút PC control trên HMI bằng tay tại tủ máy. Tối đa 15 phút "
                    "một lượt, và TỔNG 60 phút cho cả phiên PC control — hết trần phiên "
                    "thì thợ phải tắt rồi bật lại PC control, không xin thêm được. Im "
                    "lặng quá 20 giây cũng rụng và máy hú còi trả quyền về HMI (chỉ lệnh "
                    "ghi hoặc roaster_lai_nhip mới tính là còn tỉnh).",
     "inputSchema": {"type": "object", "properties": {
         "so_phut": {"type": "number", "description": "xin bao nhiêu phút (tối đa 15)"}}}},
    {"name": "roaster_lai_tra_quyen",
     "description": "Trả quyền lái về cho thợ. Gọi ngay khi xong việc, đừng giữ.",
     "inputSchema": {"type": "object", "properties": {
         "ly_do": {"type": "string"}}}},
    {"name": "roaster_lai_nhip",
     "description": "Báo còn tỉnh để GIỮ lượt lái khi đang cân nhắc mà chưa ra lệnh. "
                    "ĐỌC trạng thái KHÔNG còn tính là nhịp tim — im quá 20 giây là máy "
                    "hú còi và trả quyền về HMI. Nghĩ lâu thì gọi hàm này, đừng dựa vào "
                    "vòng lặp đọc telemetry.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "roaster_lai_gas",
     "description": "Đặt mức GAS (0-100%). Mỗi lệnh chỉ đổi tối đa 25 điểm — muốn đổi "
                    "nhiều thì chia nhiều bước và chờ nhiệt phản hồi giữa các bước.",
     "inputSchema": {"type": "object", "required": ["muc"], "properties": {
         "muc": {"type": "number", "description": "0-100"}}}},
    {"name": "roaster_lai_gio",
     "description": "Đặt mức GIÓ / quạt hút (0-100%).",
     "inputSchema": {"type": "object", "required": ["muc"], "properties": {
         "muc": {"type": "number", "description": "0-100"}}}},
    {"name": "roaster_lai_trong",
     "description": "Đặt tốc độ TRỐNG quay (0-100%).",
     "inputSchema": {"type": "object", "required": ["muc"], "properties": {
         "muc": {"type": "number", "description": "0-100"}}}},
    {"name": "roaster_lai_lua",
     "description": "MỒI LỬA hoặc TẮT BẾP. Bật gas mà 75 giây không lên lửa thì firmware "
                    "tự đóng gas, hú còi, báo mã 414 và nếu đang có mẻ thì huỷ mẻ (START = 0). "
                    "Kiểm cờ flame trong roaster_trang_thai để biết có lửa thật (chân CH1 "
                    "của board) hay mới chỉ bấm bật — relay gas bật KHÔNG có nghĩa là có lửa. "
                    "Bếp premix khi rang: board không chờ lửa ở bước mồi, chốt 75 s là thứ duy "
                    "nhất canh mồi hụt.",
     "inputSchema": {"type": "object", "required": ["bat"], "properties": {
         "bat": {"type": "boolean", "description": "true = mồi lửa, false = tắt bếp"}}}},
    {"name": "roaster_lai_hut",
     "description": "Đặt áp hút chân không (Pa, 90-250) và/hoặc bật PID gió theo áp hút.",
     "inputSchema": {"type": "object", "properties": {
         "ap": {"type": "number", "description": "áp hút đặt, Pa"},
         "bat_pid": {"type": "boolean", "description": "bật/tắt PID gió theo áp hút"}}}},
    {"name": "roaster_lai_lenh",
     "description": "Lệnh khác ngoài gas/gió/trống/lửa: charge (NẠP HẠT), drop (XẢ MẺ), "
                    "cool, escape, auto, afterburner, loader, destoner, mixer, drumfan, "
                    "sv, scale_tg... CẨN TRỌNG: charge và drop mở xi-lanh khí nén cửa nạp "
                    "và cửa xả của trống đang 200°C — chỉ dùng khi biết chắc đang làm gì. "
                    "App là bên phán xét tên lệnh và dải giá trị.",
     "inputSchema": {"type": "object", "required": ["ten", "gia_tri"], "properties": {
         "ten": {"type": "string", "description": "tên lệnh, ví dụ charge / drop / auto"},
         "gia_tri": {"description": "giá trị (thường 0 hoặc 1, hoặc % với mức)"}}}},
]

HAM_LAI = {
    "roaster_lai_trang_thai": t_lai_trang_thai,
    "roaster_lai_xin_quyen": t_lai_xin_quyen,
    "roaster_lai_tra_quyen": t_lai_tra_quyen,
    "roaster_lai_nhip": t_lai_nhip,
    "roaster_lai_gas": t_lai_gas,
    "roaster_lai_gio": t_lai_gio,
    "roaster_lai_trong": t_lai_trong,
    "roaster_lai_lua": t_lai_lua,
    "roaster_lai_hut": t_lai_hut,
    "roaster_lai_lenh": t_lai_lenh,
}


TOOLS = [
    {"name": "roaster_dang_nhap",
     "description": "Đăng nhập vào app máy rang bằng TÀI KHOẢN của app (tên + PIN, "
                    "đúng cái gõ ở màn khoá). Chỉ cần khi server chạy mà chưa có "
                    "OTL_API_USER/OTL_API_PIN hay khoá API — roaster_kiem_tra sẽ nói "
                    "rõ đang vào bằng gì. Master được cả ba phạm vi (đọc, cấu hình, "
                    "lái); thợ vận hành chỉ đọc. Token sống 8 giờ. ĐỪNG đoán PIN: sai "
                    "vài lần là app khoá tài khoản tạm.",
     "inputSchema": {"type": "object", "properties": {
         "ten": {"type": "string", "description": "tên tài khoản, ví dụ Master"},
         "mk": {"type": "string", "description": "mã PIN của tài khoản đó"},
         "mo_khoa_app": {"type": "boolean", "description": "mở khoá luôn MÀN HÌNH app "
                         "đang mở ở máy tính cạnh máy rang (mặc định có). Đặt false "
                         "nếu chạy nền, không muốn màn hình ngoài xưởng tự mở khoá."}},
         "required": ["ten", "mk"]}},
    {"name": "roaster_kiem_tra",
     "description": "Kiểm nhanh có nối được app máy rang không và khoá API có dùng được không. "
                    "Gọi cái này trước khi báo lỗi cho người dùng.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "roaster_trang_thai",
     "description": "Trạng thái máy: data.bt/et (°C), ror_bt/ror_et (°C/phút), "
                    "gas/air/drum (%), drum_hz (Hz), vac (Pa), step, t_roast (giây), "
                    "flags.charge/drop/flame, prof_sel/prof_pct/prof_ok. Kiểm state, "
                    "age_ms và mode trước khi dùng số liệu. Lệnh trả status=queued chỉ "
                    "mới xếp hàng, cần đọc lại trạng thái; cờ charge/drop là trạng thái nút, "
                    "không phải cảm biến xác nhận hạt đã nạp/xả xong.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "roaster_ho_so",
     "description": "Danh sách hồ sơ rang đã lưu (tên, mức rang, nhiệt nạp, nhiệt xả, thời gian).",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "roaster_danh_sach_me",
     "description": "Các mẻ đã rang, có lọc theo từ khoá/khoảng ngày và phân trang. "
                    "Bộ lọc chạy dưới kho chứ không cắt trên trang, nên tìm được cả mẻ "
                    "cũ. Trả tong = TỔNG số mẻ khớp bộ lọc (không phải số dòng trang này); "
                    "tong = null nghĩa là chưa đếm được, xem ghi_chu_tong.",
     "inputSchema": {"type": "object", "properties": {
         "so_luong": {"type": "integer", "description": "lấy bao nhiêu mẻ mỗi trang (1..500, mặc định 20)"},
         "bo_qua": {"type": "integer", "description": "bỏ qua bao nhiêu mẻ đầu — trang kế = bo_qua + so_luong"},
         "tu_khoa": {"type": "string", "description": "tìm trong mã mẻ, tên hồ sơ, tên thợ; bỏ dấu vẫn khớp"},
         "tu_ngay": {"type": "string", "description": "từ ngày, dạng YYYY-MM-DD"},
         "den_ngay": {"type": "string", "description": "đến ngày, dạng YYYY-MM-DD"}}}},
    {"name": "roaster_dem_me",
     "description": "Đếm số mẻ khớp bộ lọc, không kéo dữ liệu mẻ về. Dùng khi chỉ cần "
                    "con số (\"xưởng rang bao nhiêu mẻ tuần này\") hoặc để biết còn "
                    "bao nhiêu trang trước khi lật.",
     "inputSchema": {"type": "object", "properties": {
         "tu_khoa": {"type": "string", "description": "tìm trong mã mẻ, tên hồ sơ, tên thợ"},
         "tu_ngay": {"type": "string", "description": "từ ngày, dạng YYYY-MM-DD"},
         "den_ngay": {"type": "string", "description": "đến ngày, dạng YYYY-MM-DD"}}}},
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
     "description": "Đọc %s vận hành $M từ máy (timer xi-lanh, gas, mốc pha rang, "
                    "cân, hút, làm nóng, M53 tự động mở cửa xả và M54..M60 là các "
                    "chốt timing/an toàn). CHỈ ĐỌC — "
                    "server này không ghi được." % _MO_TA_M,
     "inputSchema": {"type": "object", "properties": {}}},
]

if CO_LAI:                      # tầng lái chỉ XUẤT HIỆN khi người vận hành bật
    TOOLS = TOOLS + TOOLS_LAI

TOOLS += [
    {"name": "roaster_list_skills", "description": "Liệt kê skill nghiệp vụ dùng chung với chatbot trong Roast Lab.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "roaster_read_skill", "description": "Đọc chỉ dẫn skill đã chọn; không thực thi mã hoặc cấp quyền.",
     "inputSchema": {"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}}}},
    {"name": "roaster_assistant_capabilities", "description": "Đọc các chế độ quyền và khả năng của trợ lý tích hợp; không thay đổi phiên.",
     "inputSchema": {"type": "object", "properties": {}}},
]

HAM = {
    "roaster_dang_nhap": t_dang_nhap,
    "roaster_kiem_tra": t_kiem_tra,
    "roaster_trang_thai": t_trang_thai,
    "roaster_ho_so": t_ho_so,
    "roaster_danh_sach_me": t_danh_sach_me,
    "roaster_dem_me": t_dem_me,
    "roaster_duong_cong_me": t_duong_cong,
    "roaster_thong_ke_me": t_thong_ke_me,
    "roaster_so_me": t_so_me,
    "roaster_cau_hinh_may": t_cau_hinh_may,
    "roaster_list_skills": t_ky_nang,
    "roaster_read_skill": t_doc_ky_nang,
    "roaster_assistant_capabilities": t_kha_nang,
}
if CO_LAI:
    HAM.update(HAM_LAI)


def t_dat_tham_so(a):
    """Ghi theo đơn vị thanh ghi; firmware kiểm dải riêng từng $M."""
    idx, value = a.get("idx"), a.get("value")
    if type(idx) is not int or type(value) is not int:
        raise LoiGoi("idx và value phải là số nguyên")
    if SO_M and not 1 <= idx <= SO_M:
        raise LoiGoi("idx $M phải trong khoảng 1..%d" % SO_M)
    if not 0 <= value <= 65535:
        raise LoiGoi("value phải trong khoảng 0..65535 (số nguyên thô HMI)")
    if _PCL_MAP is not None:
        lo, hi = _PCL_MAP.CFG_RANGE[idx]
        if lo > hi or not lo <= value <= hi:
            raise LoiGoi("M%d cần số nguyên thô trong khoảng %d..%d" % (idx, lo, hi))
    return _gui("/api/v1/mc_write", {"items": [["M%d" % idx, idx, value]]})


if CO_CAU_HINH:
    _lc_idx = {"type": "integer",
               "description": ("số $M, 1..%d" % SO_M) if SO_M else "số $M"}
    if SO_M:
        _lc_idx.update({"minimum": 1, "maximum": SO_M})
    TOOLS.append({"name": "roaster_set_machine_param",
                  "description": "Ghi một tham số $M khi máy rảnh (%s). M23 là nhiệt "
                                 "nạp thô ×10 (1800 = 180,0°C; tối đa 3000). M54..M60 "
                                 "điều chỉnh timing/chốt an toàn; M59=0 là hợp lệ. Cần "
                                 "khoá config. App và firmware đều kiểm đúng dải; firmware "
                                 "chỉ báo OK sau khi HMI xác nhận ghi." % _MO_TA_M,
                  "inputSchema": {"type": "object", "required": ["idx", "value"],
                                  "properties": {"idx": _lc_idx,
                                                 "value": {"type": "integer", "minimum": 0, "maximum": 65535}}}})
    HAM["roaster_set_machine_param"] = t_dat_tham_so


def _send(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def call(ten, args):
    f = HAM.get(ten)
    if not f:
        raise LoiGoi("không có công cụ tên '%s'" % ten)
    return f(args or {})


def _vao_luc_khoi_dong():
    """Có sẵn tài khoản trong biến môi trường thì đăng nhập ngay, để lần gọi đầu
    tiên không phải nuốt một lượt 401. Hỏng thì IM LẶNG chạy tiếp — báo lỗi lúc
    này chỉ làm bẩn stdio của giao thức MCP; roaster_kiem_tra nói rõ hơn nhiều."""
    # Tài khoản đặt tường minh trong biến môi trường THẮNG tệp apikey.txt còn sót
    # lại cạnh app: người chạy server vừa nói rõ muốn vào bằng tài khoản nào.
    # Chỉ OTL_API_KEY (cũng tường minh) mới được ưu tiên hơn.
    if os.environ.get("OTL_API_KEY") or not MK_TK:
        return
    try:
        _dang_nhap()
    except Exception:
        pass


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
                "serverInfo": {
                    "name": "otl-roaster-lai" if CO_LAI else "otl-roaster-read",
                    "version": VERSION},
            }})
        elif method in ("notifications/initialized", "initialized"):
            pass
        elif method == "tools/list":
            _send({"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS}})
        elif method == "tools/call":
            p = req.get("params", {})
            try:
                out = call(p.get("name"), p.get("arguments") or {})
                # JSON gọn: indent=1 xuống dòng từng số trong mảng đường cong, phình
                # gấp mấy lần → tốn token, và dễ chạm ngưỡng cắt 190 k hơn.
                body = json.dumps(out, ensure_ascii=False, separators=(",", ":"))
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


_vao_luc_khoi_dong()


if __name__ == "__main__":
    main()
