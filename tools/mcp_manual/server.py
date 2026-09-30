# -*- coding: utf-8 -*-
"""MCP server dựng tài liệu manual OTL bằng Illustrator.

Thay cho chuỗi thao tác tay: nối engine + content → PowerShell COM → render PNG →
đếm chữ từng trang. Gọi một công cụ là xong, và kết quả trả về đã kèm phần rà lỗi.

Chạy:
    python tools/mcp_manual/server.py

Biến môi trường (đều có mặc định, thường không cần đặt):
    OTL_MANUAL_ENGINE   engine.jsx của skill manual-otl
    OTL_MANUAL_GOC      thư mục gốc cho đường dẫn tương đối (mặc định 122_Manual_AI)

KHÔNG tự viết nội dung tài liệu ở đây. Nội dung nằm trong các file content*.jsx;
server này chỉ dựng và soi. Quy ước trình bày, API engine và các bẫy đã trả giá
nằm trong skill `manual-otl` — đọc skill đó trước khi soạn nội dung.

⚠ Máy chỉ bắt được trang THƯA CHỮ. Chồng chữ, tràn khung, logo chạm tiêu đề thì
không thấy — dựng xong vẫn phải xem ảnh bằng mắt rồi mới giao.
"""
import io
import json
import os
import re
import subprocess
import sys

VERSION = "1.0.0"

MAC_DINH_ENGINE = (r"F:\Project\100_OTL_06ALS - CMS - Cacao"
                   r"\.claude\skills\manual-otl\assets\engine.jsx")
MAC_DINH_GOC = r"F:\Project\112_Quanly\122_Manual_AI"

ENGINE = os.environ.get("OTL_MANUAL_ENGINE", MAC_DINH_ENGINE)
GOC = os.environ.get("OTL_MANUAL_GOC", MAC_DINH_GOC)

IT_CHU = 420          # dưới ngưỡng này, không ảnh → nghi trang thừa
CAO_TOI_THIEU = 430   # khối chữ cuối kết thúc cao hơn → nửa dưới trang trống


class LoiGoi(Exception):
    """Lỗi đã lường trước — báo gọn cho người gọi, không phải sự cố server."""


# ── tiện ích ───────────────────────────────────────────────────────────────
def _duong_dan(p):
    """Cho phép truyền đường dẫn tương đối so với OTL_MANUAL_GOC."""
    if not p:
        raise LoiGoi("thiếu đường dẫn file nội dung")
    p = os.path.expandvars(p)
    if not os.path.isabs(p):
        p = os.path.join(GOC, p)
    p = os.path.abspath(p)
    if not os.path.exists(p):
        raise LoiGoi("không thấy file: %s" % p)
    return p


def _soat_dau_cach(noi_dung):
    """Bắt sớm lỗi thiếu dấu cách trước \\u2013 — dính chữ, hay lọt ra tận bìa."""
    return [x.strip() for x in
            re.findall(r'.{0,24}(?<=[^\s"])\\u2013.{0,20}', noi_dung)]


def _noi_file(content):
    thu_muc = os.path.dirname(content)
    ten = os.path.basename(content)
    ra = os.path.join(thu_muc, ten if ten.startswith("manual") else "manual-" + ten)
    if not os.path.exists(ENGINE):
        raise LoiGoi("không thấy engine.jsx: %s" % ENGINE)
    e = io.open(ENGINE, encoding="utf-8").read()
    c = io.open(content, encoding="utf-8").read()
    io.open(ra, "w", encoding="utf-8", newline="").write(e + c)
    return ra, _soat_dau_cach(c)


def _chay_illustrator(jsx):
    ps = ("$ai = New-Object -ComObject Illustrator.Application; "
          "while ($ai.Documents.Count -gt 0) { $ai.ActiveDocument.Close(2) }; "
          '$ai.DoJavaScriptFile("%s")' % jsx.replace("/", "\\"))
    try:
        r = subprocess.run(["powershell", "-NonInteractive", "-Command", ps],
                           capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        raise LoiGoi("Illustrator không trả lời sau 10 phút — mở Illustrator xem "
                     "có hộp thoại nào đang chặn không")
    out = (r.stdout or "").strip()
    if "OK pages=" not in out:
        raise LoiGoi("Illustrator không dựng được:\n%s\n%s"
                     % (out, (r.stderr or "").strip()[:800]))
    return out


def _tim_pdf(jsx):
    s = io.open(jsx, encoding="utf-8").read()
    base = re.findall(r'var base = "([^"]+)"', s)
    ten = re.findall(r'new File\(base \+ "([^"]+\.pdf)"\)', s)
    return (base[-1] + ten[-1]) if (base and ten) else None


def _ra_soat(pdf, ve_anh, dpi):
    try:
        import fitz
    except ImportError:
        return {"ghi_chu": "chưa cài pymupdf nên không rà được (pip install pymupdf)"}
    d = fitz.open(pdf)
    thu_muc = os.path.dirname(pdf)
    trang, canh_bao = [], []
    for i in range(d.page_count):
        p = d[i]
        t = p.get_text().strip()
        anh = len(p.get_images())
        khoi = [b for b in p.get_text("blocks") if b[4].strip()]
        day = max((b[3] for b in khoi), default=0)
        trang.append({"trang": i + 1, "so_ky_tu": len(t), "so_anh": anh})
        if i > 0 and anh == 0 and len(t) < IT_CHU:
            canh_bao.append("tr%02d chỉ %d ký tự, không ảnh" % (i + 1, len(t)))
        elif i > 0 and anh == 0 and day < CAO_TOI_THIEU:
            canh_bao.append("tr%02d trống nửa dưới" % (i + 1))
        if ve_anh:
            p.get_pixmap(dpi=dpi).save(os.path.join(thu_muc, "p_%02d.png" % (i + 1)))
    kq = {"so_trang": d.page_count, "trang": trang, "canh_bao": canh_bao}
    if ve_anh:
        kq["anh"] = os.path.join(thu_muc, "p_NN.png")
        kq["nhac"] = ("Đã render ảnh. PHẢI xem bằng mắt rồi mới giao — máy không "
                      "bắt được chồng chữ, tràn khung hay logo chạm tiêu đề.")
    return kq


# ── công cụ ────────────────────────────────────────────────────────────────
def manual_dung(a):
    content = _duong_dan(a.get("content"))
    ve_anh = a.get("render_anh", True)
    dpi = int(a.get("dpi", 80))
    jsx, dinh_chu = _noi_file(content)
    ket = {"content": content, "ket_qua_illustrator": _chay_illustrator(jsx)}
    if dinh_chu:
        ket["loi_dinh_chu"] = {
            "so_cho": len(dinh_chu), "vi_du": dinh_chu[:5],
            "cach_sua": "thiếu dấu cách trước \\u2013 — sửa trong file content "
                        "bằng script Python (đừng dùng công cụ sửa tay, nó cắt "
                        "khoảng trắng cuối chuỗi) rồi dựng lại"}
    pdf = _tim_pdf(jsx)
    if pdf and os.path.exists(pdf):
        ket["pdf"] = pdf
        ket["ra_soat"] = _ra_soat(pdf, ve_anh, dpi)
    else:
        ket["ghi_chu"] = ("không đọc được đường dẫn PDF từ content — file content "
                          "phải tự gọi doc.saveAs(...) ở cuối như các bản mẫu")
    return ket


def manual_ra_soat(a):
    pdf = _duong_dan(a.get("pdf"))
    return {"pdf": pdf, "ra_soat": _ra_soat(pdf, a.get("render_anh", True),
                                            int(a.get("dpi", 80)))}


def manual_kiem_chuoi_cam(a):
    """Kiểm bản OEM: PDF còn sót dấu vết thương hiệu gốc nào không.

    Đọc chữ trong chính file PDF chứ không đọc mã nguồn — ảnh bìa cũ vẫn có thể
    mang dấu nhận dập trên tôn máy mà đọc mã nguồn không thấy.
    """
    import fitz
    pdf = _duong_dan(a.get("pdf"))
    cam = a.get("chuoi_cam") or ["O Tesla", "OTL", "otlpro", "0314844413",
                                 "936 198 938", "Ho Chi Minh", "Vietnam"]
    d = fitz.open(pdf)
    sot = {}
    for i in range(d.page_count):
        t = d[i].get_text()
        for c in cam:
            if c in t:
                sot.setdefault(c, []).append(i + 1)
    return {"pdf": pdf, "so_trang": d.page_count,
            "chuoi_da_kiem": cam,
            "con_sot": sot or None,
            "ket_luan": "SẠCH — không còn dấu vết" if not sot
                        else "CÒN SÓT %d chuỗi, xem con_sot" % len(sot)}


def manual_kiem_tra(a):
    co_fitz = True
    try:
        import fitz  # noqa: F401
    except ImportError:
        co_fitz = False
    return {"phien_ban": VERSION,
            "engine": ENGINE, "engine_co_ton_tai": os.path.exists(ENGINE),
            "thu_muc_goc": GOC, "goc_co_ton_tai": os.path.isdir(GOC),
            "pymupdf": co_fitz,
            "nhac": "Quy ước trình bày và API engine nằm trong skill manual-otl."}


HAM = {"manual_dung": manual_dung,
       "manual_ra_soat": manual_ra_soat,
       "manual_kiem_chuoi_cam": manual_kiem_chuoi_cam,
       "manual_kiem_tra": manual_kiem_tra}

TOOLS = [
    {"name": "manual_dung",
     "description": "Dựng một tài liệu manual OTL từ file nội dung .jsx: nối engine, "
                    "chạy Illustrator, xuất .ai + .pdf, render PNG từng trang và rà "
                    "máy tìm trang thưa chữ. Thay cho 4 lệnh tay. Trả về số trang, "
                    "đường dẫn PDF và danh sách cảnh báo. LƯU Ý: rà máy chỉ bắt trang "
                    "thưa chữ — chồng chữ, tràn khung, logo chạm tiêu đề thì phải xem "
                    "ảnh bằng mắt mới thấy.",
     "inputSchema": {"type": "object", "properties": {
         "content": {"type": "string", "description": "file nội dung, ví dụ "
                     "airlock-repair-en/content.jsx — tương đối so với thư mục "
                     "122_Manual_AI, hoặc đường dẫn tuyệt đối"},
         "render_anh": {"type": "boolean", "description": "có render PNG để soi không "
                        "(mặc định có)"},
         "dpi": {"type": "integer", "description": "độ phân giải ảnh, mặc định 80; "
                 "đặt 110 khi cần soi kỹ chữ nhỏ"}},
         "required": ["content"]}},
    {"name": "manual_ra_soat",
     "description": "Rà lại một file PDF đã dựng sẵn mà không dựng lại: đếm chữ từng "
                    "trang, tìm trang thưa, render PNG. Dùng khi muốn soi lại bản cũ.",
     "inputSchema": {"type": "object", "properties": {
         "pdf": {"type": "string", "description": "đường dẫn file PDF"},
         "render_anh": {"type": "boolean"},
         "dpi": {"type": "integer"}},
         "required": ["pdf"]}},
    {"name": "manual_kiem_chuoi_cam",
     "description": "Kiểm bản OEM mang thương hiệu đối tác: bóc chữ trong PDF xem còn "
                    "sót dấu vết thương hiệu gốc không, chỉ rõ sót ở trang nào. Phải "
                    "chạy TRƯỚC khi gửi bản OEM cho đối tác — đọc mã nguồn là chưa đủ.",
     "inputSchema": {"type": "object", "properties": {
         "pdf": {"type": "string", "description": "đường dẫn file PDF bản OEM"},
         "chuoi_cam": {"type": "array", "items": {"type": "string"},
                       "description": "danh sách chuỗi cấm; bỏ trống thì dùng bộ mặc định"}},
         "required": ["pdf"]}},
    {"name": "manual_kiem_tra",
     "description": "Kiểm nhanh server dựng được hay không: có engine.jsx chưa, thư mục "
                    "gốc đúng chưa, đã cài pymupdf chưa. Gọi cái này trước khi báo lỗi.",
     "inputSchema": {"type": "object", "properties": {}}},
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
                "serverInfo": {"name": "otl-manual", "version": VERSION}}})
        elif method in ("notifications/initialized", "initialized"):
            pass
        elif method == "tools/list":
            _send({"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS}})
        elif method == "tools/call":
            p = req.get("params", {})
            ten = p.get("name")
            try:
                f = HAM.get(ten)
                if not f:
                    raise LoiGoi("không có công cụ tên '%s'" % ten)
                out = f(p.get("arguments") or {})
                body = json.dumps(out, ensure_ascii=False, indent=1)
                if len(body) > 190000:
                    body = body[:190000] + "\n…(cắt bớt)"
                _send({"jsonrpc": "2.0", "id": mid,
                       "result": {"content": [{"type": "text", "text": body}]}})
            except LoiGoi as e:
                _send({"jsonrpc": "2.0", "id": mid, "result": {
                    "content": [{"type": "text", "text": "Lỗi: %s" % e}],
                    "isError": True}})
            except Exception as e:            # noqa: BLE001 — không để server chết
                _send({"jsonrpc": "2.0", "id": mid, "result": {
                    "content": [{"type": "text", "text": "Lỗi bất ngờ: %r" % e}],
                    "isError": True}})
        elif mid is not None:
            _send({"jsonrpc": "2.0", "id": mid,
                   "error": {"code": -32601, "message": "method không hỗ trợ: %s" % method}})


if __name__ == "__main__":
    main()
