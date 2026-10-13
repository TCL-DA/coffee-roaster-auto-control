# Luật từ sách thiết kế — chỉ mục

Thêm ngày 11/10/2026 bằng skill `book-to-skill` (chế độ "sinh từ bản phân tích có sẵn", gộp vào skill này thay vì tạo skill riêng).
Ba nguồn đã đọc 100% trong `F:\Project\112_Quanly\Book\Design\`.

| Nguồn | Loại | Độ tin | File |
|---|---|---|---|
| Norman, *The Design of Everyday Things* (2013) | Sách đầy đủ, 7 chương | Cao | [norman-doet.md](norman-doet.md) |
| Hollifield, *A High Performance HMI* (ISA 2012) | Bài báo 27 trang (không phải Handbook) | Cao cho HMI | [hollifield-hphmi.md](hollifield-hphmi.md) |
| *Refactoring UI* — bản tóm tắt Bookey | Tóm tắt, bị cắt 3 trang | Thấp | [refactoring-ui-tomtat.md](refactoring-ui-tomtat.md) |

- **Tra luật**: `python scripts/search.py "<từ khoá>" --domain book` — 66 luật trong `data/design-books.csv` (64 từ sách + 2 luật cấm của chủ máy: `no-edge-accent-stripe`, `active-state-fill-not-underline`),
  mỗi luật có Platform (HMI/Web/App/All), Do / Don't, ghi chú OTL, nguồn (chương/trang), mức độ.
- **Soát nhanh một màn**: [cheatsheet.md](cheatsheet.md) — luật "khi X → làm Y", cây quyết định báo động, phân cấp L1–L4, ngưỡng, dấu hiệu xấu.
- **Thứ tự ưu tiên khi mâu thuẫn**: chuẩn của chủ máy (bộ áo OTL, UI-LOCK, luật HMI đã chốt) > Hollifield (cho HMI) > Norman > bản tóm tắt Refactoring UI > gợi ý chung của skill.

## Thuật ngữ

- **Activity-centered design** — thiết kế theo hoạt động (rang một mẻ), không theo thiết bị (Norman ch4, ch6)
- **Affordance** — quan hệ khả năng hành động giữa vật và người (Norman ch1)
- **Analog indicator** — chỉ báo dải: vùng báo động xám, vùng mong muốn xanh nhạt, con trỏ tam giác (Hollifield p10)
- **Capture slip** — chuỗi quen nuốt chuỗi ít dùng khi các bước đầu giống nhau (Norman ch5)
- **Conceptual model / System image** — mô hình người dùng tự dựng / mọi thứ họ thấy được về hệ thống (Norman ch1)
- **Description-similarity slip** — làm đúng thao tác lên vật sai vì trông giống nhau (Norman ch5)
- **Display hierarchy L1–L4** — tổng quan · điều khiển cụm · chi tiết · hỗ trợ (Hollifield p18)
- **Feedforward** — thông tin cho biết làm được gì trước khi làm (Norman ch2)
- **Forcing function** — interlock / lock-in / lockout (Norman ch4)
- **Gulf of Execution / Evaluation** — khoảng cách "làm thế nào" / "đã xảy ra gì" (Norman ch2)
- **Mapping (natural)** — bố trí điều khiển khớp vật bị điều khiển (Norman ch1, ch3)
- **Mode error** — cùng điều khiển khác nghĩa theo chế độ không thấy rõ (Norman ch5)
- **Poka-yoke** — chống sai bằng đồ gá/ràng buộc (Norman ch5)
- **Sensibility check** — máy tự kiểm giá trị có hợp lý không (Norman ch5)
- **Signifier** — dấu hiệu cảm nhận được chỉ chỗ và cách hành động (Norman ch1, ch4)
- **Slip / Mistake** — làm sai khi mục tiêu đúng / mục tiêu-kế hoạch sai (Norman ch5)
- **Swiss cheese model** — tai nạn khi các lỗ của nhiều lớp phòng vệ thẳng hàng (Norman ch5)
