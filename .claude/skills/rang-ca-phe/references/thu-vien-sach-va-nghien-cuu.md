# Thư viện sách và nghiên cứu rang cà phê

Đây là bản đồ tra cứu, không phải bản sao nội dung sách. Chỉ trích dẫn điều đã đọc được từ bản hợp pháp/cục bộ; sách mới chỉ có metadata thì dùng để chỉ hướng đọc, không gán kết luận cho tác giả.

## Sách và tài liệu có toàn văn cục bộ

Kho: `F:/Project/112_Quanly/135_TaiLieu_Rang_VanHanh_AnToan/06_Rang-ca-phe/`. Tìm chữ trong lớp gương `_md/06_Rang-ca-phe/`, nhưng mở PDF gốc khi cần hình, biểu đồ, trang hoặc khi OCR đáng ngờ.

| Tài liệu | Bản trong kho | Dùng cho | Giới hạn |
|---|---|---|---|
| Scott Rao, *The Coffee Roaster's Companion* (bản dịch VI) | 47 trang; bản gốc 2014, bản VI Q1/2023, ISBN 978-604-304-596-3 | nhân xanh, truyền nhiệt, thiết kế máy, lập mẻ, consistency, sample roast, cupping | quan điểm thực hành của tác giả; các tỷ lệ/RoR là heuristic, không phải định luật |
| James Hoffmann, *The World Atlas of Coffee* (bản dịch VI) | 328 trang; bản trích không xác nhận edition/năm, nội dung có số liệu khoảng 2013 | loài/giống, sơ chế, thương mại và bản đồ vùng trồng | dữ liệu vùng/mùa vụ có thể cũ; kiểm tra WCR/ICO/nguồn tại origin |
| Lương Hồng Quang, bài giảng công nghệ chế biến cà phê | 12 trang, 21/06/2011 | chuỗi trái → nhân, thuật ngữ, sàng, rang/xay | bài giảng ngắn, không thay tiêu chuẩn thử nghiệm |
| Bühler/Petroncini, A. Wetzel, slide công nghệ rang | 32 trang, 01/2009 | góc nhìn công nghiệp, truyền nhiệt, quá trình và thiết bị | slide hãng; tách dữ liệu kỹ thuật khỏi marketing |
| SCA CVA 2023 form và SCA HQJ roast log | form/PDF và DOCX | đánh giá và ghi mẻ | kiểm tra phiên bản SCA hiện hành trước khi gọi là “chuẩn mới nhất” |

`Sach__COMPAION-ban-scan-chua-xac-minh.pdf` không có lớp text đáng tin và chưa xác minh danh tính; không trích làm căn cứ chỉ vì tên file.

## Danh mục sách chuyên ngành chưa có toàn văn trong kho

Metadata gốc: `F:/Research/Coffee-Roasting/indexes/book_catalog.csv`.

- Scott Rao: *Coffee Roasting: Best Practices*.
- Rob Hoos: *Modulating the Flavor Profile of Coffee*, *Airflow and Coffee*, *Tipping and its Avoidance*, *Cultivar*, *Exploring the Dark Side*.
- Andrea Illy & Rinantonio Viani (eds.): *Espresso Coffee: The Science of Quality*, 2nd ed.
- Gerhard A. Jansen: *Coffee Roasting: Magic, Art, Science*.
- Roast Magazine: *The Book of Roast*.

Các đầu sách nhân xanh nên bổ sung hợp pháp vào catalog khi tìm được edition/URL chính thức: Ryan Brown, *Dear Coffee Buyer*; Chris Kornman, *Green Coffee*; ITC, [*The Coffee Guide*, 4th ed.](https://www.intracen.org/sites/default/files/uploadedFiles/intracenorg/Content/Publications/ITC_Coffee_4th_Report_20210930_web_pages.pdf) (bản miễn phí chính thức). Không tìm hoặc lưu bản lậu. Khi chưa có toàn văn, chỉ được nói “catalog ghi chủ đề”, không viết “tác giả kết luận”.

## Kho nghiên cứu mở

Kho `F:/Research/Coffee-Roasting` là nguồn chính cho câu hỏi khoa học, không chỉ hai sách phổ thông.

- `README.md` và `BAO_CAO_TONG_QUAN.md`: phạm vi, cảnh báo và bộ đọc cốt lõi.
- `search/master_catalog.sqlite`: catalog hợp nhất; `search/all_text_fts.sqlite`: chỉ mục toàn văn đã nhập.
- `indexes/master_sources.csv`: danh mục nguồn lớn; `indexes/book_catalog.csv`: sách; `indexes/manufacturer_software_catalog.csv`: tài liệu hãng/phần mềm.
- `documents/curated/` và `documents/curated_round2/`: bộ nghiên cứu ưu tiên về profile–cảm quan, màu, heat/mass transfer, digital twin, origin/processing, storage và an toàn.
- `fulltext/round14_20260920/`, `DANH_MUC_DOT_14.md`, `DANH_MUC_DOT_15.md`: các đợt toàn văn mới chưa chắc đã nhập chỉ mục tổng.
- `BAO_CAO_DOT_*.md`: nhật ký thu thập, giấy phép, trùng lặp và giới hạn từng đợt.

Snapshot gần nhất ghi hơn 2.900 nguồn trong catalog chính và hàng trăm toàn văn, nhưng số lượng file không đồng nghĩa số nghiên cứu độc lập: có bản trùng DOI/nội dung, PDF/XML của cùng bài và tài liệu chưa thẩm định. Luôn khử trùng theo DOI/tiêu đề/tác giả, đọc phương pháp và phân biệt review, thí nghiệm, dataset, manual, marketing.

## Định tuyến câu hỏi

| Câu hỏi | Điểm bắt đầu |
|---|---|
| Profile, màu, development, cảm quan | `BAO_CAO_TONG_QUAN.md`; `documents/curated/CORE-001` đến `CORE-004` |
| Truyền nhiệt/ẩm, porosity, chuyển động hạt, probe | `documents/curated_round2/R2-001` đến `R2-004`; tìm `heat mass transfer`, `PEPT`, `thermophysical` |
| Nguồn gốc/sơ chế/tiền chất hương | `R2-009`, `R2-012`, `R2-020`; World Atlas; ITC/WCR |
| Bảo quản/ageing/degassing | `R2-013`, `R2-014`; các đợt 14–15; ITC Coffee Guide |
| Lỗi rang/volatile markers | báo cáo tổng quan và đợt 15; phải đọc correction đi kèm bài gốc |
| Màu/ảnh/NIR/cảm biến khí | `BAO_CAO_DOT_7.md`, datasets Kaggle và nghiên cứu NIR; không coi nhãn cộng đồng là chuẩn Agtron |
| PID, digital twin, AI | `BAO_CAO_DOT_2.md`, `R2-006`, `R2-008`, dataset/repo có license; không thay safety firmware |
| An toàn, phát thải, phơi nhiễm | NIOSH, EPA AP-42, FDA/Codex và manual đúng model; không suy từ sách rang |

## Cách tổng hợp bằng chứng

1. Bắt đầu từ câu hỏi có thể kiểm chứng, không tìm một con số “chuẩn” chung.
2. Ưu tiên standard/manual đúng phiên bản, rồi systematic review hoặc nghiên cứu phù hợp, sau đó mới sách/video/kinh nghiệm.
3. Ghi máy, cỡ mẻ, hạt, probe, protocol, cỡ mẫu và kết quả cảm quan của nghiên cứu; đánh dấu điều kiện không khớp OTL.
4. Tách kết quả hóa học, vật lý và cảm quan. Một marker hay màu không tự chứng minh chất lượng.
5. Kiểm tra correction/retraction, DOI, license và bản trùng. Nêu tên tài liệu/phần/trang cho con số quan trọng.
6. Chuyển kết luận thành thử nghiệm nhỏ trên OTL với biến giữ nguyên, tiêu chí dừng và cupping mù.

Không tuyên bố đã “đọc toàn bộ kho” nếu chỉ tra catalog hoặc báo cáo đợt. Không biến quan điểm của Rao/Hoos hay nội dung hãng thành đồng thuận khoa học nếu chưa có đối chứng độc lập.
