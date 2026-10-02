# API và MCP lái BT Serial Tester — giả lập đầu đo BT để test HMI

Khi **BT Serial Tester** chạy, app tự mở API tại `http://127.0.0.1:8777`.
API chỉ nghe trên máy cục bộ và **không mở cổng COM lần thứ hai** — app vẫn
giữ COM3, GUI vẫn bấm tay được như thường.

> **Vì sao phải nhúng vào app:** cổng COM là tài nguyên độc quyền. Tiến trình
> thứ hai gọi `serial.Serial('COM3')` sẽ lỗi `PermissionError`. Muốn vừa dùng
> GUI vừa cho máy lái thì chỉ còn đường này.

## Để làm gì

Đẩy BT giả lập qua các mốc rang (Charge → DE → FCs → Drop) để **thử HMI mà
máy vẫn nguội, không đốt lửa**. Vòng kín:

```
bt_dat 196  →  firmware STM32 đọc RS485  →  ghi $M lên HMI
            →  đọc lại bằng Modbus TCP 502 của panel
            →  hoặc chụp màn bằng VNC 5900
```

## Các đường HTTP

| Đường | Thân | Trả về |
|---|---|---|
| `GET /api/v1/status` | — | `cong_mo`, `cong`, `baud`, `bt_thiet_bi`, `dang_replay`, `bu_bt` |
| `POST /api/v1/port` | `{"action": "open"}` | mở/đóng cổng COM — `open` · `close` |
| `POST /api/v1/set` | `{"bt": 185.5}` | đặt BT **tuyệt đối** (°C) |
| `POST /api/v1/nudge` | `{"deg": -2.5}` | dời BT **tương đối** (°C) |
| `POST /api/v1/replay` | `{"action": "start"}` | `start` · `stop` · `reset` |

Mọi request cần `Authorization: Bearer <token>`; token dùng chung với OTL
Serial Terminal (cùng máy, cùng người dùng, cùng phạm vi 127.0.0.1).

### Trần an toàn

Firmware thật đang nghe đầu kia, một bước nhảy vô lý làm RoR vọt và có thể
kích logic cắt gas. Nên:

- `bt` phải trong **0–300 °C**;
- mỗi lần dời tối đa **50 °C** — lệch hơn thì chia nhỏ ra.

### Mã lỗi (để tác nhân tự động rẽ nhánh)

`chua_mo_cong` · `chua_biet_bt` · `buoc_qua_lon` · `ngoai_dai` · `mo_cong_that_bai` ·
`thieu_tham_so` · `sai_kieu` · `hanh_dong_la` · `sai_token` · `ui_ban`

> `chua_biet_bt`: cổng đã mở nhưng app chưa đọc được dòng `BT:xx.xx` nào.
> Chờ một nhịp rồi gọi lại.

## Dùng bằng CLI

```bash
python tools/bt_api.py trangthai
python tools/bt_api.py cong open
python tools/bt_api.py dat 185.0
python tools/bt_api.py doi -2.5
python tools/bt_api.py replay start
```

## Cấu hình MCP

```json
{
  "mcpServers": {
    "otl-bt-sim": {
      "command": "python",
      "args": ["F:/Project/100_OTL_06ALS - CMS - Cacao/tools/mcp_bt_sim/server.py"],
      "env": {
        "OTL_BT_API_BASE": "http://127.0.0.1:8777"
      }
    }
  }
}
```

Năm công cụ: `bt_trang_thai` · `bt_cong` · `bt_dat` · `bt_doi` · `bt_replay`.

⚠ Thêm/đổi công cụ thì **phải khởi động lại Claude Code** mới nạp — MCP đọc danh sách
công cụ một lần lúc khởi động.

## Kiểm

```bash
python tools/test_bt_control.py
```

Dựng một App giả bắt chước Tk (`after()` + luồng UI) rồi chạy cả server lẫn
MCP thật trên đó — không cần cắm phần cứng. **33 phép thử**.

Đã chạy thật trên máy 02/10: API mở COM3 → gửi +0,1 °C → board echo `BT:180.10`
→ app đọc về `bt_thiet_bi: 180.1`.
