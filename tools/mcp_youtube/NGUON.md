# Nguồn & giấy phép — MCP `otl-youtube` bản 2.0

Bản 2.0 gộp việc của **5 dự án mã nguồn mở** vào chung một server. Không chép
nguyên khối repo nào vào đây: hai thư viện thì cài qua `pip` và gọi như thư viện,
ba cái còn lại thì **viết lại cách làm** cho hợp kiểu của server này (tên hàm tiếng
Việt, lỗi báo bằng tiếng Việt, ưu tiên tiết kiệm hạn mức API).

Giấy phép của cả năm đều cho phép dùng lại trong dự án riêng, kèm điều kiện giữ
ghi công. Trang này chính là chỗ ghi công đó — **đừng xoá**, repo này để PUBLIC.

---

## Lấy gì ở đâu

| Dự án | Giấy phép | Cách dùng | Thành công cụ nào |
|---|---|---|---|
| [google-api-python-client](https://github.com/googleapis/google-api-python-client) | Apache-2.0 | Cài qua pip, gọi thẳng | Nền của mọi công cụ nói chuyện với YouTube |
| [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api) | MIT © 2018 Jonas Depoix | Cài qua pip, gọi thẳng | `youtube_loi_thoai` |
| [ytstudio-cli](https://github.com/jdwit/ytstudio-cli) | MIT © 2026 Jelmer de Wit | Viết lại cách làm | `youtube_thay_hang_loat`, `youtube_phu_de`, `youtube_danh_sach_phat` |
| [youtube-studio-mcp](https://github.com/i1s-abhishek/youtube-studio-mcp) | MIT © 2026 Abhishek Pandey | Viết lại cách làm | `youtube_anh_bia`, `youtube_tra_loi_binh_luan` |
| [python-youtube](https://github.com/sns-sdks/python-youtube) | MIT © 2020 sns-sdks | Cài qua pip, gọi thẳng | `youtube_tim_cong_khai` |

---

## Chỗ cố ý làm khác bản gốc

Ghi lại để sau này ai đọc bản gốc rồi thắc mắc "sao không giống" thì biết là cố ý.

**1. Quét video bằng playlist chứ không bằng `search`**
`ytstudio-cli` tìm video của kênh bằng `search().list(forMine=True)`. Lệnh `search`
của YouTube tốn **100 đơn vị hạn mức mỗi lần gọi**, trong khi cả ngày chỉ có 10.000.
Kênh 82 video phải gọi 2 lần là mất 200 đơn vị chỉ để liệt kê. Bản này đi qua
playlist "uploads" như `youtube_video` vẫn làm — **1 đơn vị mỗi lần gọi**, rẻ hơn 100 lần.

**2. `youtube_thay_hang_loat` mặc định KHÔNG ghi**
Bản gốc cũng có `--execute`, nhưng ở đây siết chặt hơn: phải truyền hẳn
`thuc_thi=true`, và có trần `so_luong` (mặc định 20) để lỡ tay cũng không sửa sạch
cả kênh. Mỗi video ghi tốn 50 đơn vị — sửa 100 video là 5.000, hết nửa hạn mức ngày.

**3. Lấy lời thoại bằng hai đường khác nhau**
- `youtube_loi_thoai` (youtube-transcript-api): **không cần OAuth**, chạy được cả khi
  token hỏng, và chạy được trên video của người khác. Đây là đường nên dùng.
- `youtube_phu_de` (Data API): đọc đúng bản phụ đề đã tải lên kênh, kể cả bản nháp
  chưa công khai. Nhưng cần quyền `youtube.force-ssl`, mà bản phụ đề máy tự nghe
  thì YouTube hay khoá không cho tải.

**4. Không mở đăng video và xoá video**
`ytstudio-cli` và mấy repo automation đều làm được hai việc này. Server này **cố ý
không mở** — xem phần đầu `server.py`.

**5. Lỗi của Google dịch sang tiếng Việt**
Hai lỗi hay gặp nhất mà thông báo gốc nói rất khó hiểu: hết hạn mức ngày
(`quotaExceeded`) và token thiếu quyền (`insufficientPermissions`). Hàm
`_dich_loi_google()` bắt hai cái đó và nói thẳng phải làm gì.

---

## Thư viện cần cài

Xem [requirements.txt](requirements.txt).

```bash
pip install -r tools/mcp_youtube/requirements.txt
```

Thiếu thư viện nào thì công cụ liên quan tự báo đúng câu lệnh cần chạy, các công cụ
còn lại vẫn chạy bình thường.
