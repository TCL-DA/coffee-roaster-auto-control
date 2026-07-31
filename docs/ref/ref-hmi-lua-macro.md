# Lua Macro HMI Delta (DIAScreen / DOPSoft)

Tham chiếu hàm Lua macro cho HMI Delta dòng DOP, dùng cho dự án OTL-06ALS.
Nguồn: manual Lua Delta (đối chiếu khi cần). Control Block / thanh ghi điều khiển: xem [ref-hmi-delta-dop.md](ref-hmi-delta-dop.md).

## Quy ước địa chỉ

- `$n` = bộ nhớ nội bộ (volatile), word, dải `$0`–`$65535` → dùng `mem.inter.*`.
- `$Mn` = bộ nhớ tĩnh (giữ qua mất điện), dải `$M0`–`$M1023` → dùng `mem.static.*` (API **giống hệt** `mem.inter`).
- Chuỗi chiếm nhiều word: 1 word = 2 ký tự ASCII → tên 16 ký tự = 8 word.
- Biến **không được nil** khi đem dùng, nil làm Lua **dừng giữa chừng** (dòng sau không chạy).

---

## `mem.inter` / `mem.static` — đọc/ghi bộ nhớ HMI

`mem.inter.*` cho `$n`, `mem.static.*` cho `$Mn` (cùng tham số, chỉ khác vùng nhớ).

| Hàm | Mô tả |
|-----|-------|
| `mem.inter.Read(idx [,"signed"])` | đọc 1 word (mặc định unsigned) |
| `mem.inter.Write(idx, val)` | ghi 1 word |
| `mem.inter.ReadDW(idx [,"signed"])` | đọc double word ($idx~$idx+1) |
| `mem.inter.WriteDW(idx, val)` | ghi double word |
| `mem.inter.ReadFloat(idx)` / `WriteFloat(idx, f)` | float 32-bit (2 word) |
| `mem.inter.ReadDouble(idx)` / `WriteDouble(idx, d)` | double 64-bit (4 word) |
| `mem.inter.ReadBit(w, b)` | đọc bit b của word w ($w.b) |
| `mem.inter.WriteBit(w, b, val)` | ghi bit ($w.b = val) |
| `mem.inter.ReadAscii(idx, len)` | đọc chuỗi ASCII dài len ký tự |
| `mem.inter.WriteAscii(idx, str, len)` | **ghi chuỗi ASCII** vào $idx |

```lua
-- word
v1 = mem.inter.Read(100)            -- v1 = $100
mem.inter.Write(100, v1 + 100)
vs = mem.inter.Read(101, "signed")  -- $101 dạng có dấu

-- bit ($1.15)
b1 = mem.inter.ReadBit(1, 15)
mem.inter.WriteBit(1, 15, 0)

-- chuỗi: ghi "abcd" vào $100~$101 rồi đọc lại
str = "abcd"
mem.inter.WriteAscii(100, str, string.len(str))
str2 = mem.inter.ReadAscii(100, 4)
```

> Đọc/ghi qua TAG (tên biến) thì dùng `link.*` thay vì index số.

---

## `account` — tài khoản / đăng nhập

| Hàm | Trả về | Mô tả |
|-----|--------|-------|
| `account.GetCurrentLogin()` | `ret, name, level` | tài khoản đang đăng nhập (ret 1 = OK) |
| `account.Login(name, pwd)` | `ret` | đăng nhập (1 = OK) |
| `account.Add(name, pwd, level)` | `ret` | thêm tài khoản |
| `account.Delete(name)` | `ret` | xóa tài khoản |
| `account.ChangeName(old, new)` | `ret` | đổi tên |
| `account.ChangePassword(name, newPwd)` | `ret` | đổi mật khẩu |
| `account.ChangeLevel(name, newLevel)` | `ret` | đổi cấp |
| `account.GetPassword(name)` | `ret, password` | lấy mật khẩu |
| `account.GetLevel(name)` | `ret, level` | lấy cấp |
| `account.IsExist(name)` | `bExist` | có tồn tại không (1 = có) |

```lua
ret, name, level = account.GetCurrentLogin()
if ret == 1 then
    -- get success: dùng name, level
end
```

> `level` liên hệ **System Control b8–b11 "Set user level"** (W40057) — xem [ref-hmi-delta-dop.md](ref-hmi-delta-dop.md).

---

## `screen` — màn hình

| Hàm | Trả về | Mô tả |
|-----|--------|-------|
| `screen.Open(id)` | `ret` | mở màn id (1 = OK) |
| `screen.CloseSub(id)` | `ret` | đóng sub-screen |
| `screen.IsOpened(id)` | `1/0` | màn id có đang mở |
| `screen.Capture(diskID)` | `ret` | chụp màn ra ảnh (USB=2, SD=3) |

```lua
ret = screen.Open(1)        -- chuyển sang màn 1
if screen.IsOpened(2) == 1 then ... end
```

---

## `sys` — hệ thống

| Hàm | Mô tả |
|-----|-------|
| `sys.Sleep(ms)` | delay (ms) |
| `sys.GetTick()` | tick hiện tại (ms) — đo khoảng thời gian |
| `sys.BuzzerOn(1/0)` | bật/tắt buzzer |
| `sys.GetInterParam("NAME")` | đọc tham số hệ thống (xem danh sách dưới) |
| `sys.GetDate()` → `year,month,day,week` | ngày (week 0=CN..6=T7) |
| `sys.GetDateString()` | "2018/10/03" |
| `sys.GetTime()` → `h,m,s` | giờ |
| `sys.GetTimeString()` | "08:51:20" |
| `sys.GetDays(y,m,d)` / `sys.ToDate(days)` | đổi ngày ↔ số ngày từ 1970 |
| `sys.GetSecs(h,m,s)` / `sys.ToTime(secs)` | đổi giờ ↔ giây |

**`sys.GetInterParam` — tham số hay dùng:** `ACCOUNT` (tên login), `ACCOUNT_LEVEL`, `TP_X`/`TP_Y` (chạm), `BATTERY_VOLTAGE`, `SD_STATUS`, `USB_STATUS`, `FW_VERSION1/2`, `ALARM_COUNT`, `NET1_IP1..4`, `NET_MAC1..3`, `EMS_STATUS`, `PROGRAM_STATUS`, `KEY_CHAR`...

```lua
-- lấy tên login (cách 2, ngoài account.GetCurrentLogin)
userName, ret = sys.GetInterParam("ACCOUNT")
mem.inter.WriteAscii(100, userName, string.len(userName))
```

---

## `string` — chuỗi

`string.len(s)`, `string.format(fmt, ...)` (`%d %s %X %c %f`), `string.split(s, sep)` → table, `string.find(s, pat)` → vị trí, `string.sub(s, i [,j])`, `string.rep(s, n)`, `string.trim(s)`, `string.reverse(s)`, `string.byte(s, i [,j])`, `string.char(...)`, `string.upper/lower`, `string.gmatch` (regex).

```lua
v = string.format("Ex: %d, %X, %s, %3.3f", 10, 15, "AB", 12.35)  -- "Ex: 10, F, AB, 12.350"
t = string.split("John,Andy,Mike", ",")   -- t[1]="John"...
```

---

## `math` — toán

Số học cơ bản + `math.abs/exp/log/sqrt/pow/modf/min/max/random/randomseed/pi`, lượng giác `sin/cos/tan/asin/acos/atan/atan2` (+ `sinh/cosh/tanh`), đổi góc `math.rad/deg`.

**Bitwise (quan trọng cho xử lý word):** `math.band`, `math.bor`, `math.bxor`, `math.bnot`, `math.lshift(v,n)`, `math.rshift(v,n)`.

```lua
math.randomseed(sys.GetTick())
v = math.random(0, 1000)
w1 = math.band(math.rshift(dw, 16), 0xFFFF)   -- tách word cao
```

---

## `table` — bảng/mảng

`table.count(t)`, `table.insert(t [,pos], val)`, `table.remove(t, pos)`, `table.sort(t [,cmp])`, `table.concat(t, sep [,i [,j]])`, lặp `for k,v in pairs(t) do`.

```lua
t = {3,2,5,1,4}
table.sort(t)                                 -- {1,2,3,4,5}
table.sort(t, function(a,b) return a>b end)   -- giảm dần
```

---

## `convert` / `text`

- `convert.ToNum(str)` → `dVal, ret` — chuỗi → số (chấp nhận " -1.23 ", "-2.8E-3").
- `convert.IntToFloat(intVal)` — bit-pattern int → float.
- `text.GbkToUtf8(strGBK, len)` → `utf8_len, utf8_string`.

---

## `draw` — vẽ

`color` = giá trị **RGB565** dạng thập phân (0–65535). Mọi hàm trả `ret` (1 = OK, 0 = lỗi).

| Hàm | Tham số | Mô tả |
|-----|---------|-------|
| `draw.Point(x, y, color)` | x,y = toạ độ | vẽ 1 điểm |
| `draw.Line(x1, y1, x2, y2, color, penWidth)` | điểm đầu→cuối, penWidth = bề rộng nét | vẽ đường thẳng |
| `draw.Rect(x, y, w, h, color)` | x,y = góc **trên-trái**; w,h = rộng,cao | vẽ hình chữ nhật |
| `draw.Ellipse(x, y, w, h, color)` | x,y = **tâm**; w,h = rộng,cao | vẽ ellipse |
| `draw.Clear()` | (không có) | xóa toàn bộ hình đã vẽ |
| `draw.SetAntialiasing(flag)` | flag: 1 = bật, 0 = tắt khử răng cưa | bật khử răng cưa cho nét mượt hơn |

```lua
draw.SetAntialiasing(1)              -- bật khử răng cưa cho mượt
ret = draw.Line(1, 1, 100, 100, 53388, 5)   -- đường hồng (RGB565 #53388), nét 5
ret = draw.Rect(50, 50, 100, 20, 53388)      -- chữ nhật từ góc (50,50), 100×20
ret = draw.Ellipse(50, 50, 100, 100, 53388)  -- ellipse tâm (50,50), 100×100
draw.Clear()                         -- xóa hết
```

> Lưu ý toạ độ gốc khác nhau: `Rect` lấy **góc trên-trái**, `Ellipse` lấy **tâm**.

---

## Cú pháp Lua nền (ghi nhớ nhanh)

- Gán: `bool=true/false`, `int=13`, `double=13.6`, `string="abc"`, `nil`.
- Điều kiện: `if .. then .. elseif .. else .. end`; toán tử `== ~= <= >= < >`, `and` `or`.
- Switch: bảng hàm `case = { [1]=function() .. end }; if case[No] then case[No]() end`.
- Lặp: `for i=1,3 do .. end` (bước `-0.25` được), `while .. do .. end`, `repeat .. until(cond)`, `break`.
- Hàm nhiều giá trị: `function f() return a,b end` → `x,y = f()`.
- Gọi module khác: `require "Proc001"`.

---

## Ví dụ áp dụng dự án

### Show tên tài khoản login lên `$5000`
Phía HMI: ô **Character/ASCII Display** trỏ `$5000`, độ dài đủ (vd 8 word = 16 ký tự).
Đặt làm **Background/Cycle macro** để luôn cập nhật:

```lua
-- Cập nhật tên login lên $5000
ret, name, level = account.GetCurrentLogin()
if ret == 1 then
    mem.inter.WriteAscii(5000, name, string.len(name))   -- có người login → ghi tên
else
    mem.inter.WriteAscii(5000, "--------", 8)             -- chưa login → gạch
end
```

> Cách khác lấy tên: `name, ret = sys.GetInterParam("ACCOUNT")` rồi `WriteAscii` y vậy.
