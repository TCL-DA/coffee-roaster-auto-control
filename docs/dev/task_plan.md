# Task: Nâng UX cho các tính năng CÓ SẴN của OTL Roast Lab

> Lập bằng skill **ai-maestro/planning** (mẫu 3 file). Trục: làm **cái đã có** dễ dùng
> hơn cho thợ rang — KHÔNG thêm module kinh doanh. Chi tiết diễn giải:
> `docs/plan/plan-nangcap-gd5-gd8.md`. Kiểm kê: `findings.md`.

## Goal
Thợ chạy máy 16h/ngày thấy app **dễ chịu, nhanh, ít mỏi** — theo đúng cách họ thật sự
đứng máy (mắt ở trống, tay bận, đứng xa, xưởng ồn-chói). Đo bằng: rang được **mà ít
phải dán mắt/chạm vào panel**, thợ mới cầm là chạy.

## Phases (mỗi phase nâng TÍNH NĂNG ĐÃ CÓ, không đẻ module mới)

- [ ] **Phase 1 — Chốt nền** (bắt buộc trước): test máy thật · commit toàn bộ (PUBLIC_KEY,
      GĐ4/5, âm thanh, plan). Không nâng trên nền chưa vững.

- [ ] **Phase 2 — GĐ5 Tai thay mắt** (nâng tab RANG + mở rộng ÂM đã có)
  - [ ] Âm mốc rang riêng cho TP/khô/FCs/crack sau/tới-xả (mở rộng `snd()` đã có)
  - [ ] Giọng nói tiếng Việt báo mốc + đếm ngược (Web Speech API, không thư viện)
  - [ ] Chuông báo động khác hẳn khi RoR gãy / nhiệt vọt / mất kết nối giữa mẻ
  - [ ] Nhịp "tick" theo RoR (bật/tắt riêng) + chỉnh âm lượng/tắt từng loại

- [ ] **Phase 3 — GĐ6 Nhìn-lướt-từ-xa** (nâng hiển thị tab RANG + Tổng quan)
  - [ ] Phóng to số BT/RoR (token `--fs-*`), đọc từ 1–2m
  - [ ] RoR đổi màu theo vùng (xanh/vàng/đỏ) + chữ/biểu tượng cho mù màu
  - [ ] Đếm ngược tới mốc kế + thanh tiến trình mẻ
  - [ ] Chế độ "màn to" 1 chạm (chỉ BT·RoR·phase·đồng hồ)
  - [ ] Nút tăng sáng-tương phản nhanh / dịu màn ca tối

- [ ] **Phase 4 — GĐ7 Ít chạm & tha lỗi** (nâng luồng thao tác đã có)
  - [ ] Luồng mẻ 1 chạm (gộp preheat→charge→chạy) + gợi ý mẻ kế back-to-back
  - [ ] Nút to hợp găng + vùng chạm nới rộng + chống double-tap
  - [ ] Cử chỉ: vuốt đổi tab / vuốt đóng modal / giữ-để-xác-nhận
  - [ ] Thanh tác vụ nhanh bám đáy (Bắt đầu/Xả/Mẻ mới) ở mọi tab
  - [ ] Hoàn tác thao tác lỡ + xác nhận CHỈ ở việc nguy hiểm

- [ ] **Phase 5 — GĐ8 Thoải mái & dễ học** (nâng phần cá nhân hoá/trợ giúp đã có)
  - [ ] Hồ sơ theo thợ (theme/âm/bố cục/tay thuận trái-phải) qua state.json
  - [ ] Chế độ "mới tập": nâng `data-help` thành tour + nhắc bước + khoá nút nguy hiểm
  - [ ] Chế độ tập trung khi rang (ẩn nhiễu, chống chạm nhầm)
  - [ ] Cỡ chữ lớn tuỳ chọn + màu thân thiện mù màu + tự dịu chói theo giờ

## Decisions
| Decision | Rationale | Date |
|----------|-----------|------|
| Kế hoạch lấy UX làm trục, bỏ hướng tính năng KD | Chủ máy không ưng bản cũ (kho FULL/cloud/P&L/AI) | 2026-07-24 |
| Chỉ nâng tính năng CÓ SẴN, không đẻ module mới | Yêu cầu chủ máy: "các tính năng có sẵn trong app" | 2026-07-24 |
| Thứ tự Nghe→Nhìn→Chạm→Thoải mái | Theo đúng thứ tự giác quan thợ đứng máy | 2026-07-24 |
| Dùng Web Speech + Web Audio (không thư viện) | Giữ 1-file HTML, offline, WebView2 có sẵn | 2026-07-24 |
| Kho/cloud/P&L/AI tách riêng, KHÔNG vào 4 GĐ này | Chúng là tính năng KD, không phải trải nghiệm | 2026-07-24 |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| (chưa có) | | |
