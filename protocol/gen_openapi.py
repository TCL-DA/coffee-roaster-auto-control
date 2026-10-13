# -*- coding: utf-8 -*-
"""Sinh đặc tả OpenAPI cho API v1 của app OTL Roast Lab — TỪ pc_link.json.

Vì sao phải SINH chứ không viết tay: dải giá trị của từng lệnh (gas 0..100,
sv 0..3000, vac 90..250…) đã nằm trong pc_link.json và đang được dùng cho cả
firmware, Python lẫn giao diện. Chép tay sang tài liệu là có ngày lệch — mà lệch
dải trong tài liệu thì người viết client sẽ tin theo tài liệu, rồi gửi số ngoài
dải xuống một cái máy đang có lửa.

Gọi từ gen_pc_link.py; đừng chạy riêng.
"""
import json

NL = "\n"


def _mo_ta_lenh(wr):
    return NL.join(
        "  * `%s` — %s  [%g..%g, đơn vị kỹ thuật]" % (
            f["key"], f.get("desc", ""), f["min"] / f.get("scale", 1),
            f["max"] / f.get("scale", 1))
        for f in wr["fields"])


def _mo_ta_doc(rd):
    return NL.join("  * `%s` — %s" % (f["key"], f.get("desc", "")) for f in rd["fields"])


def _mo_ta_cfg(cfg):
    """Mô tả các $M có hợp đồng đơn vị/default đặc biệt."""
    out = []
    for idx_s, p in cfg.get("params", {}).items():
        idx = int(idx_s)
        lo, hi = cfg["min"][idx - 1], cfg["max"][idx - 1]
        out.append("  * `M%d` `%s` — %s; thô %d..%d; mặc định %s" % (
            idx, p.get("name", ""), p.get("desc", ""), lo, hi,
            p.get("default", "không khai báo")))
    return NL.join(out)


def _q(ten, mo_ta, kieu="string", bat_buoc=False):
    """Một tham số truy vấn. Tên phải TRÙNG tên handler đọc trong roast_lab_hmi.py —
    tài liệu ghi `query=` mà app đọc `q=` thì client gửi xong không lọc gì cả và
    tưởng kho rỗng."""
    return {"name": ten, "in": "query", "required": bat_buoc,
            "description": mo_ta, "schema": {"type": kieu}}


def _op(tag, tom_tat, mo_ta, scope, body=None, params=None):
    d = {
        "tags": [tag],
        "summary": tom_tat,
        "description": mo_ta,
        "security": [{"BearerAuth": []}],
        "responses": {
            "200": {"description": "OK",
                    "content": {"application/json": {"schema": {"type": "object"}}}},
            "401": {"description": "thiếu hoặc sai khoá API / PIN web"},
            "403": {"description": "khoá API không có phạm vi `%s`" % scope},
            "429": {"description": "gọi quá nhiều — bị hãm"},
        },
    }
    if params:
        d["parameters"] = params
    if body:
        d["requestBody"] = {"required": True,
                            "content": {"application/json": {"schema": body}}}
    return d


def gen_openapi(s):
    wr, rd = s["write"], s["read"]
    cfg = s.get("config") or {}
    fs = s.get("failsafe") or {}
    tmo = fs.get("agent_timeout_s", 3)

    mo_ta_write = (
        "⚠ ĐỘNG VÀO LỬA VÀ CƠ CẤU. Cần phạm vi `control`." + NL + NL
        + "Tác nhân cần mở lease sau khi thợ bật PC control trên HMI. App quản lý "
        "`agent` và `hb`; API cấm tác nhân tự ghi hai ô này. Tác nhân im quá 20 giây "
        "hoặc lease hết hạn thì app ngừng heartbeat; firmware nhả quyền sau "
        + str(tmo) + " giây."
        + NL + NL + "Giá trị gửi là đơn vị kỹ thuật: sv dùng °C, scale_tg dùng kg, "
        "gas/air/drum dùng %. status=queued chỉ xác nhận xếp hàng, chưa xác nhận "
        "firmware hay cơ cấu đã thực hiện. value trong phản hồi là số thanh ghi, "
        "engineering_value là giá trị đã quy đổi. Đọc lại snapshot để theo dõi."
        + NL + NL + "Các lệnh:" + NL + _mo_ta_lenh(wr))

    mo_ta_snapshot = ("Ảnh chụp máy rang lúc này: nhiệt, RoR, mức gas/gió/trống, "
                      "bước quy trình." + NL + NL + "Các trường:" + NL + _mo_ta_doc(rd))

    # Bộ lọc lịch sử mẻ — DÙNG CHUNG cho danh sách và số đếm. Hai bên lệch bộ lọc
    # là ra cảnh "trang 1 có 50 dòng mà tổng ghi 0".
    loc_me = [_q("q", "từ khoá tìm trong mã mẻ · tên hồ sơ · tên thợ; kho so bằng "
                      "chữ đã bỏ dấu nên gõ có dấu hay không đều khớp"),
              _q("from", "từ ngày `YYYY-MM-DD`, so trên `started_at`"),
              _q("to", "đến ngày `YYYY-MM-DD`")]

    mo_ta_batches = (
        "Lọc CHẠY DƯỚI KHO rồi mới phân trang, nên tìm được cả mẻ cũ chứ không chỉ "
        "trang đầu. `n` là số dòng mỗi trang (kho tự kẹp 1..500), `offset` là số "
        "dòng bỏ qua — trang kế = `offset + n`." + NL + NL
        + "`batches` là `null` khi CHƯA ĐỌC ĐƯỢC kho (kho chưa mở hoặc tham số sai "
          "kiểu), khác hẳn `[]` là đọc được mà không mẻ nào khớp. Đừng lấy số dòng "
          "của một trang làm tổng — dùng `/api/v1/batches_count`.")

    mo_ta_count = (
        "Tổng số mẻ khớp bộ lọc, CÙNG bộ tham số với `/api/v1/batches` nhưng không "
        "phân trang." + NL + NL
        + "`count` là `null` khi chưa đếm được (kho chưa mở hoặc lỗi đọc); `0` "
          "nghĩa là đếm được và không mẻ nào khớp. Hai chuyện khác nhau, đừng gộp.")

    paths = {
        "/api/v1/snapshot": {"get": _op("Đọc", "Trạng thái máy lúc này", mo_ta_snapshot, "read")},
        "/api/v1/profiles": {"get": _op("Đọc", "Danh sách hồ sơ rang", "", "read")},
        "/api/v1/batches": {"get": _op(
            "Đọc", "Các mẻ đã rang", mo_ta_batches, "read",
            params=[_q("n", "số dòng mỗi trang (mặc định 50, kho kẹp 1..500)", "integer"),
                    _q("offset", "bỏ qua bao nhiêu dòng đầu (mặc định 0)", "integer")] + loc_me)},
        "/api/v1/batches_count": {"get": _op(
            "Đọc", "Đếm mẻ khớp bộ lọc", mo_ta_count, "read", params=loc_me)},
        "/api/v1/batch_curve": {"get": _op(
            "Đọc", "Đường cong một mẻ",
            "Trả `curve` dạng mảng cột (`t`, `bt`, `et`, `ror`, `gas`, `air`, `drum`); "
            "`null` khi không có mẻ đó.", "read",
            params=[_q("id", "mã mẻ lấy từ `/api/v1/batches`", "integer", True)])},
        "/api/v1/batch_stats": {"get": _op(
            "Đọc", "Thống kê một mẻ",
            "Trả `stats`: mốc TP/DE/FCs/Drop, thời gian từng pha, DTR, RoR đỉnh. "
            "`null` khi kho chưa mở hoặc không tính được.", "read",
            params=[_q("id", "mã mẻ", "integer", True)])},
        "/api/v1/batches_curves": {"get": _op(
            "Đọc", "Đường cong NHIỀU mẻ để so chồng",
            "Trả `curves` dạng `{\"<mã mẻ>\": curve}`. Tối đa 6 mẻ — thừa thì bị bỏ "
            "lặng lẽ; mã hỏng cũng bị bỏ, nên hãy đối chiếu khoá trả về với danh "
            "sách đã gửi.", "read",
            params=[_q("ids", "các mã mẻ ngăn bằng dấu phẩy, ví dụ `12,15,18`", "string", True)])},
        "/api/v1/state": {"get": _op(
            "Đọc", "Trạng thái/thiết lập lưu tại app",
            "Đường DUY NHẤT không đòi xác thực, vì trang web phải mượn giao diện "
            "trước khi đăng nhập — nhưng khi CHƯA có token thì chỉ trả phần TRANG "
            "TRÍ (theme, màu, ngôn ngữ, hình nền). Có token mới trả trọn `state`.",
            "read")},
        "/api/v1/audit": {"get": _op(
            "Đọc", "Nhật ký hash-chain và huy hiệu toàn vẹn",
            "Trả `tail` (300 mục cuối) và `verify` — kết quả kiểm chuỗi băm.", "read")},
        "/api/v1/oplog": {"get": _op(
            "Đọc", "Nhật ký vận hành", "Trả `lines` — 400 dòng cuối.", "read")},
        "/api/v1/lease": {"get": _op(
            "Đọc", "Lượt lái đang mở",
            "Ai đang cầm lái, còn bao nhiêu giây, và LUẬT đang áp (trần phút, bước "
            "nhảy mỗi lệnh, số lệnh mỗi phút). Chỉ ĐỌC — không gia hạn gì.", "read")},
        "/api/v1/lease_open": {"post": _op(
            "Lái máy", "Xin lượt lái cho tác nhân tự động",
            "Chỉ mở được khi thợ đã bật PC control TRÊN HMI bằng tay. Một lúc chỉ "
            "một tác nhân. Hết hạn là tự rụng, phải xin lại.", "control",
            {"type": "object", "properties": {
                "phut": {"type": "number", "description": "xin bao nhiêu phút; app kẹp theo trần lease"}}})},
        "/api/v1/lease_beat": {"post": _op(
            "Lái máy", "Nhấp nhịp giữ lượt lái",
            "Xác nhận tác nhân CÒN SỐNG và trả về trạng thái lượt lái. Mọi request "
            "mang khoá đang cầm lái đều tính là một nhịp, nên đường này chỉ cần khi "
            "tác nhân im lâu mà vẫn muốn giữ quyền." + NL + NL
            + "⚠ Đừng chạy luồng nền nhấp đều đặn: nhịp giả vờ tác nhân còn sống "
              "trong khi nó đã treo, phá đúng cái van an toàn nhả quyền về HMI.",
            "control")},
        "/api/v1/lease_close": {"post": _op(
            "Lái máy", "Trả quyền lái về cho thợ",
            "Token của thợ đóng được lượt lái của BẤT KỲ tác nhân nào.", "control",
            {"type": "object", "properties": {"ly_do": {"type": "string"}}})},
        "/api/v1/write": {"post": _op(
            "Lái máy", "Gửi một lệnh xuống máy rang", mo_ta_write, "control",
            {"type": "object", "required": ["name", "value"],
             "properties": {
                 "name": {"type": "string", "enum": [f["key"] for f in wr["fields"] if f["key"] not in ("hb", "agent")]},
                 "value": {"type": "number", "description": "giá trị đơn vị kỹ thuật, không phải số thanh ghi"}}})},
        "/api/v1/begin_batch": {"post": _op("Lái máy", "Mở một mẻ mới", "", "control")},
    }

    # /api/v1/state là đường DUY NHẤT app cho qua cổng token, nên đừng để tài liệu
    # doạ 401/403 ở đây — người viết client sẽ đi tìm khoá cho một đường không đòi.
    _state = paths["/api/v1/state"]["get"]
    _state["security"] = []
    for ma in ("401", "403"):
        _state["responses"].pop(ma, None)

    if cfg:
        # Số $M lấy THẲNG từ pc_link.json. Không đặt mặc định 52: firmware mở thêm
        # $M mà tài liệu vẫn ghi 52 thì người viết client tin theo tài liệu và
        # không bao giờ chạm tới tham số mới ($M53 = tự động mở cửa xả).
        n_M = int(cfg["count"])
        paths["/api/v1/mc_read"] = {"get": _op(
            "Cấu hình", "Đọc %d tham số $M từ máy" % n_M,
            "Mỗi tham số một lượt hỏi-đáp qua khối handshake. Không cần tham số; "
            "kết quả cfg dùng tên M1..M%d, giá trị nguyên thô HMI." % n_M
            + NL + NL + _mo_ta_cfg(cfg), "read")}
        paths["/api/v1/mc_write"] = {"post": _op(
            "Cấu hình", "Ghi tham số $M xuống máy",
            "Firmware TỰ KIỂM DẢI lần nữa và TỪ CHỐI khi máy đang bận (đang rang · "
            "mồi lửa · làm nóng · còn lửa). Từ chối chứ KHÔNG kẹp im lặng: kẹp thì "
            "thợ tưởng đã đặt 500 mà máy chạy 300. API kiểm toàn bộ danh sách trước khi ghi; "
            "mỗi số $M xuất hiện một lần trong dải 1..%d, giá trị nguyên 0..65535. "
            "Dừng ở lỗi đầu tiên; ok chỉ đúng khi ghi hết. count là số đã ghi; errors "
            "giữ lý do; not_attempted liệt kê phần chưa ghi. Không hoàn tác các tham "
            "số đã ghi thành công. M23 nhận số thô ×10 °C (1800 = 180,0°C), tối đa "
            "3000. Firmware chỉ báo OK sau khi HMI xác nhận ghi." % n_M
            + NL + NL + _mo_ta_cfg(cfg), "config",
            {"type": "object", "required": ["items"],
             "properties": {"items": {
                 "type": "array",
                 "minItems": 1, "maxItems": n_M,
                 "description": "danh sách [tên, số $M (1..%d), giá trị nguyên thô HMI]" % n_M,
                 "items": {"type": "array"}}}})}

    for suffix, summary in (
            ("assistant_skills", "Danh sách skill nghiệp vụ"),
            ("assistant_skill", "Đọc một skill theo tên"),
            ("assistant_capabilities", "Các công cụ và chế độ quyền trợ lý")):
        paths["/api/v1/" + suffix] = {"get": _op("Trợ lý", summary, "Chỉ đọc; không cấp quyền cho agent.", "read")}
    paths["/api/v1/assistant_skill"]["get"]["parameters"] = [
        _q("name", "tên skill lấy từ `/api/v1/assistant_skills`", "string", True)]
    paths["/api/v1/assistant"] = {"post": _op(
        "Trợ lý", "Chat và theo dõi trợ lý trên LAN",
        "Chỉ token người dùng PIN web được gọi, khóa API máy bị từ chối. "
        "Phiên web chỉ đọc. Cấu hình, cấp quyền và duyệt thao tác nằm tại cầu desktop Master. "
        "chat trả trạng thái ngay; thăm dò bằng action=state. request_id trong payload chống gửi trùng.",
        "read", {"type": "object", "required": ["action"], "properties": {
            "action": {"type": "string", "enum": ["state", "chat", "pause", "resume", "clear"]},
            "payload": {"type": "object"}}})}

    mo_ta_chung = (
        "API điều khiển máy rang cà phê OTL." + NL + NL
        + "**Xác thực:** `Authorization: Bearer <khoá>`. Khoá API tạo trong app "
        "(chỉ tài khoản master), mỗi khoá có PHẠM VI riêng: `read` · `config` · "
        "`control`." + NL + NL
        + "**An toàn:** luật nằm ở firmware và ở API, KHÔNG ở phía client — ai cũng "
        "gọi thẳng HTTP được, nên luật đặt ở client là luật tự nguyện. Firmware kiểm "
        "dải mọi lệnh, khoá ghi cấu hình khi máy bận, và nhả quyền về HMI khi tác "
        "nhân tự động mất tín hiệu." + NL + NL
        + "Xem docs/plan/plan-mcp-api-extension.md.")
    if cfg:
        mo_ta_chung += (NL + NL + "Khối cấu hình $M: %d tham số (1..%d)."
                        % (cfg["count"], cfg["count"]))

    oas = {
        "openapi": "3.0.3",
        "info": {"title": "OTL Roast Lab — API v1",
                 "version": "1.0.0-pcl%d" % s["version"],
                 "description": mo_ta_chung},
        "servers": [{"url": "http://<máy-chạy-app>:8555",
                     "description": "Cổng LAN của app (mặc định 8555)"}],
        "components": {"securitySchemes": {"BearerAuth": {
            "type": "http", "scheme": "bearer",
            "description": "Khoá API dạng `otl_…`, hoặc token lấy từ PIN web"}}},
        "security": [{"BearerAuth": []}],
        "tags": [{"name": "Đọc", "description": "phạm vi read"},
                 {"name": "Cấu hình", "description": "phạm vi config"},
                 {"name": "Lái máy", "description": "phạm vi control — động vào lửa"}],
        "paths": paths,
    }
    return json.dumps(oas, ensure_ascii=False, indent=2) + NL
