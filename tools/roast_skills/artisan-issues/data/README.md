# Kho issue Artisan

Đây là snapshot dữ liệu công khai từ [artisan-roaster-scope/artisan](https://github.com/artisan-roaster-scope/artisan).

- `issues.jsonl`: 706 GitHub Issue trong khoảng 2016–2026; pull request bị loại.
- `comments.jsonl`: 2.492 bình luận của 672 issue; không có bình luận mồ côi.
- `manifest.json`: thời điểm tải, phạm vi, số lượng và thống kê theo năm.

Tải/cập nhật bằng:

```powershell
python tools/download_artisan_issues.py --pause 0.2
python tools/download_artisan_issues.py --comments-only --pause 0.2
```

Đợt tải bình luận dùng endpoint comment của cả repository để giảm số request,
sau đó lọc theo các issue đã lưu. Nếu GitHub hết hạn mức, chạy lại
`--comments-only` sau khi hạn mức được cấp lại; file đã ghi được giữ nguyên.

Năm 2025 và 2026 không có GitHub Issue công khai trong snapshot API này. Kết
quả đó không bao gồm Discussions, pull request, email hỗ trợ hoặc các kênh
phản hồi khác của Artisan.
