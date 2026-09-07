# MCP server máy rang OTL — tầng ĐỌC

Cho AI đọc máy rang để **phân tích**: trạng thái, hồ sơ, lịch sử mẻ, đường cong, tham số `$M`.

**Không có công cụ nào lái máy.** File `server.py` không có đường mã nào gửi lệnh xuống máy,
và có thêm danh sách đường được phép gọi (`CHO_PHEP`) làm chốt thứ hai bên cạnh phạm vi của
khoá API. Muốn AI lái máy thì phải qua tầng T2 với đủ 5 điều kiện trong
[kế hoạch](../../docs/plan/plan-mcp-api-extension.md) — không phải bằng cách thêm một dòng vào đây.

## Cần gì

1. App **OTL Roast Lab đang chạy** (nó là chỗ giữ cầu Modbus tới máy).
2. Một **khoá API phạm vi `read`**:

```bash
python tools/otl_apikey_cli.py add "MCP doc may rang" read
```

Khoá hiện **đúng một lần** — chép ngay.

## Đăng ký với Claude Code

Thêm vào `~/.claude.json`, mục `mcpServers`:

```json
"otl-roaster": {
  "command": "python",
  "args": ["F:\\Project\\100_OTL_06ALS - CMS - Cacao\\tools\\mcp_roaster\\server.py"],
  "env": {
    "OTL_API_KEY": "otl_…",
    "OTL_API_BASE": "http://127.0.0.1:8555"
  }
}
```

> Ghi thẳng vào JSON, **đừng** dùng `claude mcp add` trong Git Bash — nó biến `/c` thành `C:/`
> làm hỏng config (đã dính một lần với MCP Excel).

Máy khác trong xưởng thì đổi `OTL_API_BASE` thành `http://<ip-máy-chạy-app>:8555`.

## Công cụ

| Công cụ | Làm gì |
|---|---|
| `roaster_kiem_tra` | có nối được app không, khoá dùng được không — gọi trước khi báo lỗi |
| `roaster_trang_thai` | nhiệt BT/ET, RoR, gas/gió/trống, bước quy trình |
| `roaster_ho_so` | danh sách hồ sơ rang |
| `roaster_danh_sach_me` | các mẻ gần đây |
| `roaster_duong_cong_me` | đường cong một mẻ |
| `roaster_thong_ke_me` | mốc TP/DE/FCs/Drop, thời gian từng pha |
| `roaster_so_me` | **so nhiều mẻ** — tìm mẻ lệch khỏi nhóm |
| `roaster_cau_hinh_may` | đọc 52 tham số `$M` (chậm: mỗi tham số một lượt hỏi-đáp) |

## Khi hỏng

Mọi lỗi đều nói **lý do đọc được**, không phải mã số:

- *"không nối được app… App OTL Roast Lab có đang chạy không?"* → mở app.
- *"thiếu hoặc sai OTL_API_KEY"* → khoá sai, hoặc app chưa nạp khoá mới (chờ ~2 giây).
- *"khoá API không có phạm vi 'read'"* → tạo lại khoá với `read`.
- `roaster_trang_thai` trả `state: error, err: could not open port COM…` → app chạy nhưng
  **chưa nối được máy rang**. Đó là chuyện của cáp/cổng COM, không phải lỗi MCP.

## Kiểm

```bash
python tools/test_mcp_roaster.py     # cần app đang chạy; tự tạo và tự xoá khoá thử
```
