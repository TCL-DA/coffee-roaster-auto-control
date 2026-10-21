# Tự động hóa OTL Serial Terminal qua API và MCP

## Phạm vi

Ứng dụng giữ một kết nối serial tại một thời điểm. API và giao diện dùng chung
chủ sở hữu cổng. AI có thể quét và chọn cổng, cấu hình, mở, gửi TX, theo dõi RX,
đổi cấu hình và đóng cổng. RX là dữ liệu nhận từ thiết bị, không phải một lệnh
gửi ra thiết bị. Quét cổng không tự động mở cổng hay gửi gói thăm dò.

Thông tin thiết bị gồm các trường hệ điều hành cung cấp: device, name,
description, hwid, vid, pid, serial_number, manufacturer, product, location,
interface. Trường không có dữ liệu trả về null. Danh sách cổng không chứng minh
cổng đang rảnh và không xác định baudrate của thiết bị bên ngoài.

## Tiêu chí nghiệm thu

- API có thao tác tương ứng cho quét cổng, cấu hình, mở/đóng, TX và RX; MCP gọi
  đúng API và báo lỗi có nội dung khi app từ chối.
- Giao diện phản ánh kết nối/cấu hình do API thay đổi. Không thao tác Tkinter
  từ thread HTTP. Thao tác GUI và API không mở hai kết nối cùng cổng.
- Dữ liệu TX nhị phân giữ nguyên byte; không báo thành công toàn bộ khi chỉ
  ghi được một phần. Timeout ghi không được tự động gửi lại lệnh.
- Tham số không hợp lệ bị từ chối trước khi đổi trạng thái thiết bị.
- Bộ đệm có giới hạn; con trỏ chỉ rõ dữ liệu bị mất do tràn và phiên app thay đổi.
- Chờ RX với bộ lọc không bị đánh thức thành công chỉ vì có TX.
- API cục bộ có xác thực cho tự động hóa; MCP cùng tài khoản Windows tự lấy
  khóa, không yêu cầu chép khóa vào hội thoại.
- Kiểm thử thao tác bằng serial giả qua HTTP và MCP thực tế. Chạy thử EXE trên
  cổng HTTP riêng; không gửi dữ liệu thử nghiệm tới máy đang nối COM.
- Build EXE và cập nhật đường dẫn shortcut, giữ bản cũ dự phòng.

## Tài liệu tham chiếu

- [Thông tin cổng của pySerial](https://pyserial.readthedocs.io/en/latest/tools.html).
- [Cấu hình và thao tác serial](https://pyserial.readthedocs.io/en/latest/pyserial_api.html).
- [Cấu hình MCP của Codex](https://developers.openai.com/codex/mcp).

Mẫu JSON `mcpServers` dành cho Claude Desktop; Codex dùng bảng
`mcp_servers` trong TOML. Không dùng chung hai định dạng.
