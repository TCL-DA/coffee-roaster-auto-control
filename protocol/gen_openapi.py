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
        "  * `%s` — %s  [%s..%s]" % (f["key"], f.get("desc", ""), f.get("min"), f.get("max"))
        for f in wr["fields"])


def _mo_ta_doc(rd):
    return NL.join("  * `%s` — %s" % (f["key"], f.get("desc", "")) for f in rd["fields"])


def _op(tag, tom_tat, mo_ta, scope, body=None):
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
        + "Tác nhân tự động PHẢI khai `agent=1` và nhấp `hb` mỗi giây: im quá "
        + str(tmo) + " giây là firmware nhả quyền về HMI và kêu còi. Cờ `agent` "
        "CÀI THEN — khai 1 rồi thì không hạ về 0 giữa phiên để né watchdog."
        + NL + NL + "Các lệnh:" + NL + _mo_ta_lenh(wr))

    mo_ta_snapshot = ("Ảnh chụp máy rang lúc này: nhiệt, RoR, mức gas/gió/trống, "
                      "bước quy trình." + NL + NL + "Các trường:" + NL + _mo_ta_doc(rd))

    paths = {
        "/api/v1/snapshot": {"get": _op("Đọc", "Trạng thái máy lúc này", mo_ta_snapshot, "read")},
        "/api/v1/profiles": {"get": _op("Đọc", "Danh sách hồ sơ rang", "", "read")},
        "/api/v1/batches": {"get": _op("Đọc", "Các mẻ đã rang", "", "read")},
        "/api/v1/batch_curve": {"get": _op(
            "Đọc", "Đường cong một mẻ", "Tham số truy vấn `?id=<mã mẻ>`.", "read")},
        "/api/v1/mc_read": {"get": _op(
            "Cấu hình", "Đọc 52 tham số $M từ máy",
            "Mỗi tham số một lượt hỏi-đáp qua khối handshake.", "read")},
        "/api/v1/mc_write": {"post": _op(
            "Cấu hình", "Ghi tham số $M xuống máy",
            "Firmware TỰ KIỂM DẢI lần nữa và TỪ CHỐI khi máy đang bận (đang rang · "
            "mồi lửa · làm nóng · còn lửa). Từ chối chứ KHÔNG kẹp im lặng: kẹp thì "
            "thợ tưởng đã đặt 500 mà máy chạy 300.", "config",
            {"type": "object", "required": ["items"],
             "properties": {"items": {
                 "type": "array",
                 "description": "danh sách [tên, số $M, giá trị]",
                 "items": {"type": "array"}}}})},
        "/api/v1/write": {"post": _op(
            "Lái máy", "Gửi một lệnh xuống máy rang", mo_ta_write, "control",
            {"type": "object", "required": ["name", "value"],
             "properties": {
                 "name": {"type": "string", "enum": [f["key"] for f in wr["fields"]]},
                 "value": {"type": "integer"}}})},
        "/api/v1/begin_batch": {"post": _op("Lái máy", "Mở một mẻ mới", "", "control")},
    }

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
