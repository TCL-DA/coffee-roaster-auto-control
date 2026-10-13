# Nguồn tài liệu và độ tin cậy

Kho chính: `F:/Project/112_Quanly/135_TaiLieu_Rang_VanHanh_AnToan`.

Kho nghiên cứu mở: `F:/Research/Coffee-Roasting`. Đọc `README.md`, `BAO_CAO_TONG_QUAN.md` và [thu-vien-sach-va-nghien-cuu.md](thu-vien-sach-va-nghien-cuu.md) trước khi tra catalog/toàn văn. Kho có nhiều định dạng và bản trùng; số file không đồng nghĩa số nghiên cứu độc lập. Các đợt 14–15 chưa chắc đã được nhập vào chỉ mục SQLite tổng.

Kho transcript PROBAT: `F:/Project/100_OTL_06ALS - CMS - Cacao/artifacts/probat-youtube-corpus-20260914`. Đọc `README.md`, lọc `manifest.csv` rồi mở `transcripts/<video_id>.txt`. Đây là snapshot 171 mục của kênh PROBAT Global ngày 14/09/2026, không tự bao gồm video đăng sau ngày đó. Kho đa nền tảng (Probat USA, Probat Indonesia, bên thứ ba, Bilibili, Vimeo, LinkedIn, probat.com) ở `F:\Research\Coffee-Roasting\probat\`; bản tổng hợp đã đưa vào skill và độ phủ xem `probat-nguon-danh-muc.md`.

Kho transcript Mill City Roasters: `F:/Project/100_OTL_06ALS - CMS - Cacao/_external/mill-city-roasters`. Đọc `README.md`, lọc `manifest.csv` rồi mở `transcripts/<video_id>.txt`; độ phủ và giới hạn xem [mill-city-roasters.md](mill-city-roasters.md).

Đọc `README.md` và `_md/INDEX.md` trước. `_md` dùng để tìm kiếm; hình, sơ đồ, kích thước, vị trí linh kiện hoặc OCR đáng ngờ phải mở file gốc. Không sửa lớp `_md` sinh tự động.

## Ưu tiên nguồn

1. An toàn/lắp đặt/bảo trì/hiệu chỉnh: manual phát hành đúng model/serial và quy định nơi lắp.
2. Hành vi firmware/app: source, schema và test hiện tại; tài liệu cũ chỉ chỉ dẫn.
3. Khoa học/chiến lược: Scott Rao, James Hoffmann, Bühler/Petroncini và bài giảng; con số là giả thuyết cần kiểm chứng.
   Với câu hỏi cần bằng chứng khoa học, dùng kho `F:/Research/Coffee-Roasting` và ưu tiên nghiên cứu/standard phù hợp hơn sách thực hành.
4. Đánh giá: dùng SCA-102/103/104/105 và form CVA hiện hành khi có; form CVA 2023/HQJ cục bộ là snapshot để tham khảo. Physical Assessment hiện vẫn dựa hệ green grading 2004, còn SCA-110 đang phát triển khi soát 24/09/2026. Luôn ghép với màu/hao hụt/cupping thực tế.
5. Đối chiếu máy: Loring, Probatone 60, Probat R1500, G-240; hiểu kiến trúc nhưng không bê ngưỡng/sequence sang OTL.
6. Video/web PROBAT (tóm lược trong các file `probat-*.md`): dùng để hiểu cách kỹ sư/roaster giải thích hệ thống và tìm chủ đề; thông số quyết định thiết kế phải đối chiếu manual hoặc đo kiểm. Video kỹ thuật viên Probat USA đáng tin cho logic chẩn đoán hơn video đại lý; video thăm roastery chủ yếu là lời chứng thực.

## Bản đồ

- `01_Huong-dan-su-dung-OTL`: OTL-03/120, cấu tạo và thao tác.
- `02_An-toan`: R01–R18, tiếp địa 400 V, lắp đặt/PPE.
- `03_Van-hanh-Quy-trinh`: manual/auto, preheat, auto-loader, alarm/fault.
- `04_Bao-tri-Ve-sinh`: vệ sinh, giờ chạy, phiếu bảo dưỡng.
- `05_Chinh-may-Dau-dot`: afterburner, premix, SIT 845, gas flow, khe trống.
- `06_Rang-ca-phe`: sách, công nghệ, profile, RoR, SCA.
- `07_Tham-khao-hang-khac`: Loring và Probat.

Sách và nghiên cứu: [thu-vien-sach-va-nghien-cuu.md](thu-vien-sach-va-nghien-cuu.md). Nhân xanh, phân hạng, kho, truy xuất và nguồn chính thức: [nhan-xanh-va-thu-mua.md](nhan-xanh-va-thu-mua.md).

## Giới hạn

- Rao là bản dịch; thuật ngữ quyết định kỹ thuật nên kiểm tra bản gốc.
- World Atlas chủ yếu về xuất xứ; dùng hiểu giống/sơ chế, không dùng như cookbook.
- `Sach__COMPAION-ban-scan-chua-xac-minh` không có text đáng tin; chưa xem scan thì không trích làm căn cứ.
- Bản EN–VI có thể trùng; mâu thuẫn thì ưu tiên bản gốc/revision đã xác minh.
- Profile nội bộ chỉ đại diện máy, probe, hạt và ngày rang tương ứng.
- Kho PROBAT Global có 158 transcript YouTube, 3 transcript ASR và 10 video không phát hiện lời nói. Bilibili phần lớn là bản lồng phụ đề Trung của video YouTube tiếng Anh; phụ đề tự động Indonesia sai nhiều số liệu. Auto-caption có thể sai thuật ngữ, tên máy, tiếng Đức và con số; luôn xem `caption_status`, `track_type` và ngôn ngữ trong `manifest.csv`.

Khi dẫn chứng, tách **theo manual**, **theo tài liệu rang**, và **suy luận từ dữ liệu**; nêu tên tài liệu/phần/trang cho quyết định có rủi ro hoặc con số.
