---
name: vietnamese-comments
description: Dùng khi thêm hoặc sửa chú thích, tài liệu, hướng dẫn cấu hình, hoặc text mô tả trong source của dự án OTL-06ALS. Mục tiêu là giữ chú thích tiếng Việt có dấu, đúng encoding UTF-8, và không làm hỏng chuỗi debug tiếng Anh.
allowed-tools: Read, Grep, Edit, MultiEdit, Bash
---

# Vietnamese Comments

Áp dụng playbook này khi thay đổi comment, tài liệu dự án, hoặc phần mô tả cấu hình trong firmware OTL-06ALS.

## Quy tắc bắt buộc

- Chú thích code và tài liệu dự án phải viết bằng tiếng Việt có dấu.
- Lưu file bằng UTF-8 để tiếng Việt hiển thị đúng trong editor và khi build.
- Không chuyển chú thích tiếng Việt sang không dấu nếu người dùng không yêu cầu.
- Không để text bị lỗi font/mojibake, ví dụ `Äiá»u khiá»ƒn`, `Cáº¥u hÃ¬nh`, `máº¡ch`.
- Giữ tên biến, macro, tên file, tên thanh ghi Modbus, và chuỗi debug runtime bằng tiếng Anh trừ khi người dùng yêu cầu khác.
- Chuỗi debug in qua serial vẫn theo quy tắc dự án: tiếng Anh và phải được gate bằng `if(enDebug)`.

## Cách viết chú thích

- Chú thích giải thích mục đích, đơn vị, địa chỉ Modbus, điều kiện an toàn, hoặc lý do tồn tại của logic.
- Không chú thích lại điều hiển nhiên từ tên biến.
- Với cấu hình máy, ghi rõ:
  - `1` nghĩa là có lắp hoặc bật chức năng.
  - `0` nghĩa là không lắp hoặc bỏ qua luồng chính liên quan.
  - đơn vị đo nếu có: độ C x10, Pa, %, baudrate, Modbus ID, địa chỉ thanh ghi.
- Với Modbus, phân biệt rõ:
  - `Modbus ID` là địa chỉ slave của thiết bị.
  - `register address` là địa chỉ thanh ghi đọc/ghi.
  - HMI Delta thường ghi tài liệu địa chỉ 1-based, còn lời gọi Modbus trong code dùng 0-based khi có dạng `*_W - 1`.

## Kiểm tra sau khi sửa

1. Search nhanh các dấu hiệu lỗi font:

```bash
rg -n "Ã|Ä|Æ|áº|á»|Â|â€”|â€“|â†" include src AGENTS.md .claude/skills
```

2. Nếu sửa firmware hoặc file header được include vào build, chạy PlatformIO theo quy tắc dự án.
3. Khi báo lại, nói rõ đã giữ UTF-8 và có build hay không.
