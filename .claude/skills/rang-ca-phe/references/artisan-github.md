# Kho phản hồi Artisan GitHub

Kho dữ liệu cục bộ nằm ở:

- `tools/roast_skills/artisan-issues/SKILL.md`: quy tắc đọc và giới hạn áp dụng.
- `tools/roast_skills/artisan-issues/data/issues.jsonl`: issue đã lọc, gồm mô tả,
  phiên bản/trạng thái/nhãn nếu người dùng ghi trong issue và liên kết gốc.
- `tools/roast_skills/artisan-issues/data/comments.jsonl`: bình luận issue sau
  khi đợt tải hoàn tất.
- `tools/roast_skills/artisan-issues/data/manifest.json`: phạm vi và thống kê
  của snapshot.

Khi tra cứu bằng Read/Grep, tìm theo số issue, tên thiết bị, phiên bản Artisan,
`Modbus`, `PID`, `serial`, `Aillio`, `Probat`, `temperature`, `crash` hoặc cụm
triệu chứng. Giữ liên kết `html_url` để người đọc mở lại toàn bộ ngữ cảnh.

Tách rõ mô tả của người báo lỗi, phản hồi trong bình luận và suy luận áp dụng
cho OTL. Issue công khai không thay thế firmware, manual, log hoặc phép đo OTL.
Không lấy ngưỡng an toàn, trình tự gas/lửa, giới hạn nhiệt hay hành vi điều
khiển từ Artisan để áp dụng trực tiếp cho OTL.

Snapshot chỉ bao gồm GitHub Issues trong 2016–2026; không bao gồm pull request,
Discussions, email hỗ trợ hoặc các kênh phản hồi khác. Nếu manifest ghi 0 cho
2025 hoặc 2026, đó là kết quả truy vấn API tại thời điểm tải.

