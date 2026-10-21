# Đồng bộ MCP và API với Roast Lab hiện tại — 08/09/2026

## Yêu cầu và phân vai

Người dùng yêu cầu đọc sâu phiên Roast Lab của Claude và cập nhật MCP/API vào Roast Lab. Codex điều phối, phân tích và kiểm tra; Claude viết/sửa code. Đây là công việc cập nhật trong repository, chưa cấp quyền điều khiển máy, tạo khóa thật, gửi thư, flash hoặc triển khai dịch vụ ra mạng.

Lịch sử Roast Lab chính: phiên Claude `5e5832c5-c0d7-45df-a16a-72bc8b9654ea`. Giao diện mới nhất đã có cử chỉ kéo, giữ xác nhận 500 ms và EXE 15:19. Firmware sau đó đã mở khối cấu hình tới M53, trong khi mô tả MCP/API còn nói 52. Các hiệu ứng giao diện không cần biến thành lệnh MCP.

## Phạm vi triển khai đã xác định

1. Đồng bộ số tham số cấu hình MCP/OpenAPI với nguồn PC_Link sinh sẵn; không ghi cứng 52. M53 là auto escape: 1 bật chuỗi tự động, 0 chỉ làm nguội khi firmware có công tắc. Quyền config, khóa máy bận và kiểm dải firmware vẫn giữ. Schema idx phải phản ánh phạm vi hiện tại; kiểm M53 qua HTTP và MCP giả.
2. MCP đọc lịch sử phải chuyển số lượng, từ khóa, khoảng ngày và offset xuống API trước khi phân trang. Thêm endpoint đọc số mẻ qua hàm `db_batch_count` có sẵn, dùng cùng bộ lọc; tổng số không được là số dòng trên trang. Giữ tương thích lời gọi chỉ có `so_luong`. Công bố công cụ đọc số mẻ nếu có ích; không tự mở quyền ghi.
3. Nối API đếm mẻ vào cầu web nếu thiếu để Roast Lab web và desktop dùng chung số tổng. Không sửa HTML/UI đang khóa; cầu web nằm ngoài HTML phải xác minh vị trí trước khi sửa.
4. OpenAPI phải mô tả các endpoint mà MCP thật sự dùng: trạng thái, hồ sơ, danh sách/đếm/thống kê/đường cong/so sánh mẻ, cấu hình, state/audit/oplog, lease mở/nhịp/đóng, write và các endpoint trợ lý đang có. Mô tả query, body và scope phải đúng backend. Phân biệt queued với máy đã thực hiện. Sinh lại OpenAPI từ generator, không sửa tay artefact.
5. README MCP ghi rõ khả năng mới, cách dùng bộ lọc/số tổng/M53 và cách cập nhật app. Không công bố công cụ chưa tồn tại.

Không bổ sung đường ghi khối lượng/ghi chú từ MCP trong đợt này: báo cáo RF-10 và RF-13 đã chỉ ra vấn đề đối soát kho và cắt chuỗi cần một đợt xử lý dữ liệu riêng. Không sửa RF-01..14, hiệu ứng, thanh đầu, firmware hay thiết lập tài khoản chỉ vì chúng có trong lịch sử.

## Kiểm thử chấp nhận

- Giữ `protocol/gen_pc_link.py --check` đạt.
- HTTP/MCP giả: M53 đọc/ghi với khóa phù hợp, chỉ-đọc không ghi được; công cụ config/lái mặc định không xuất hiện; không bỏ khóa khi máy bận.
- Kho SQLite tạm trên 100 mẻ: lọc trước phân trang; trang kế không trùng; đếm đúng cùng bộ lọc; không dùng 50 dòng đầu làm tổng; dữ liệu rỗng hợp lệ và lỗi đếm phải phân biệt.
- Biên đầu vào MCP: số lượng/offset không âm hoặc kiểu sai, query tiếng Việt, ngày nếu có validation hiện hành. Lỗi trả theo hợp đồng, không ném traceback hoặc làm server chết.
- OpenAPI phủ các route MCP dùng, tên query/body đúng handler và không quảng cáo route chưa triển khai.
- Chạy các bộ kiểm `test_config_api_mcp.py`, `test_telemetry_control_mcp.py`, `test_roast_history_search.py` cùng bộ kiểm mới liên quan. Chỉ dùng server giả/DB tạm, không chạy các bộ kiểm tự ghi gas hoặc tạo khóa trên app thật cổng 8555.

## Trạng thái nền trước sửa

Codex đã chạy: kiểm nguồn PC_Link đạt; cấu hình HTTP/MCP 3 phép thử đạt; telemetry/control MCP giả 6 phép thử đạt. Chưa có thay đổi code trong đợt cập nhật tại thời điểm viết kế hoạch này.

## Kết quả đào sâu lịch sử

- Ngày 06/09, người dùng yêu cầu xây MCP/API/extension để AI có thể điều khiển app rồi cho phép triển khai (phiên `848288c6…`).
- Ngày 07/09, người dùng yêu cầu bổ sung khả năng điều khiển MCP sau khi biết API có nhưng MCP chỉ đọc (phiên `4bfef77a…`). Tầng lái có cờ bật riêng và lease là yêu cầu đã chốt, phải giữ nguyên.
- Phiên Roast Lab `5e5832c5…` ngày 08/09 chủ yếu sửa giao diện/cử chỉ và đồng bộ bản web, sau đó đổi giữ xác nhận xuống 500 ms. Không có bằng chứng người dùng đã hủy hoặc thu hẹp tầng điều khiển MCP.
- Phiên firmware `3ad286cf…` ngày 08/09 chốt M53: 1 tự động escape, 0 chỉ làm nguội. `pc_link.json` đã tăng count lên 53, nhưng phần mô tả và bảng tham số app chưa theo hết.
- Không thấy yêu cầu đã chốt mở thêm API ghi khối lượng. Các vấn đề RF-10/RF-13 tiếp tục nằm trong đợt xử lý dữ liệu riêng.
- Cầu web `db_batch_count` nằm trong HTML đang có khóa sửa UI, không phải file JavaScript độc lập. API/MCP có thể dùng endpoint đếm mới ngay; đồng bộ cầu web và ô M53 cần sửa tối thiểu HTML bởi Claude, theo khóa UI, không liên quan thay đổi thanh đầu đang được người dùng yêu cầu tạm hoãn.
