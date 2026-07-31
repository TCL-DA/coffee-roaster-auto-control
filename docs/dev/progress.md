# Progress — Session log

## 2026-07-24
- Cài skill `ai-maestro/planning` (npx claude-code-templates) → `.claude/skills/planning`.
- Lập 3 file kế hoạch (task_plan / findings / progress) theo mẫu skill.
- Chốt hướng: nâng UX cho TÍNH NĂNG CÓ SẴN (không thêm module KD) — chủ máy không ưng
  bản kế hoạch cũ (kho FULL/cloud/P&L/AI).
- Kiểm kê xong tính năng hiện có + tài sản tái dùng (Web Audio đã có, Web Speech, tokens,
  bus sự kiện, data-help) → findings.md.
- Bản kế hoạch cải tiến TỪNG tính năng có sẵn: xem bảng "Cải tiến theo tính năng" dưới +
  docs/plan/plan-nangcap-gd5-gd8.md.

### Cải tiến theo TỪNG tính năng có sẵn (bảng trình chủ máy)
| Tính năng đã có | Cải tiến UX đề xuất | Phase |
|---|---|---|
| Tab Rang — số BT/ET/RoR | Phóng to đọc-từ-xa; màn-to 1 chạm | 3 |
| Tab Rang — mốc TP/DE/FCs/DROP | Âm + giọng nói báo mốc; đếm ngược mốc kế | 2,3 |
| Tab Rang — RoR | Đổi màu theo vùng + nhịp tick theo RoR | 2,3 |
| Tab Rang — nút máy | Nút to hợp găng; thanh tác vụ nhanh bám đáy | 4 |
| Banner FAULT | Chuông báo động khác hẳn tiếng thường | 2 |
| Luồng bắt đầu/xả mẻ | Gộp 1 chạm + gợi ý mẻ kế; hoàn tác | 4 |
| Âm chạm (mới) | Mở rộng: âm mốc/hành động, chỉnh âm lượng | 2 |
| Theme (accent+sáng/tối) | Hồ sơ theo thợ; dịu chói ca tối; cỡ chữ lớn | 3,5 |
| data-help (chú thích nút) | Nâng thành tour + chế độ "mới tập" | 5 |
| Tab Lịch sử / Hồ sơ | Ít chạm hơn; cử chỉ vuốt; nhập nhanh | 4 |
| i18n / bố cục | Tay thuận trái-phải; nhất quán trí-nhớ-cơ | 4,5 |

## Việc dở (nền, phải xong trước Phase 2)
- [ ] Test máy thật (GĐ4/5 + âm thanh)
- [ ] Commit toàn bộ lên nhánh feat/roast-lab-datasource
- [ ] Build exe (đã build thử 2026-07-24, chạy OK qua web probe)

## Feature: Chỉ báo ĐẦU ĐỐT (gasSignal → cờ flame) — 2026-07-24
- Dữ liệu ĐÃ có sẵn: `gasSignal` (IOConfig.h) → cờ PC_Link `flame` bit 7 → snapshot
  `d.flags.flame`. Chỉ cần HIỆN lên UI (không đụng firmware).
- Thêm badge `.flamebadge` (SVG lửa #i-ignite, không emoji) ở: tab Rang (dưới Burner%)
  + panel Preheat (header). Hàm `flameShow()` gọi trong `applyMachine` + `phRender`.
- 5 trạng thái: Có lửa (xanh) · Không lửa khi gas bật (đỏ nháy) · Mồi hụt (đỏ) · Tắt (mờ)
  · ẩn khi không nối PC_Link (compat/demo — trung thực).
- Review: code→design→code. Sửa design: thêm `prefers-reduced-motion` cho blink.
- Test: 6/6 assert Playwright PASS, 0 lỗi JS.

## Feature: CÀI ĐẶT MÁY (tham số firmware $M1..$M52) — 2026-07-25 (ĐANG DỞ)
**Bối cảnh:** các register `$M1..$M52` (Define.h dòng 628-678) là config nội bộ HMI
(timer xi-lanh, gas, pha rang, cân, hút, làm nóng, biến tần...). App nối firmware qua
PC_Link CHỈ chở dữ liệu live (đọc 100-121 / ghi 140-160) — KHÔNG có khối config này.
→ Muốn app ghi thẳng xuống máy phải để **firmware mở thêm khối config trong PC_Link**
(việc firmware, chưa làm/flash được phiên này).

**Đã làm (app-side, chạy độc lập):**
- Trang **"Cài đặt máy"** trong Cài đặt (subnav data-sub=maycfg, icon #i-config). Data-driven
  từ `MACHINE_GROUPS` (50 tham số / 7 nhóm) trong HTML: [key, addr$M, nhãn, đơn vị, min, max, dec, default].
- Render nhóm + input số tabular-nums + hiện $M + dải min-max; `mcEdit`/`_mcClamp` kẹp;
  `mcMarkDirty` tô viền warn ô đã đổi.
- **Lưu/Mở FILE cấu hình** (`cai-dat-may.json` trong thư mục hồ sơ) — backup/khôi phục/chuyển
  máy. Api `machine_cfg_save`/`machine_cfg_load` (roast_lab_hmi.py) + web endpoint + shim.
- Nút **Đọc/Ghi máy** (`mc_read`/`mc_write`) nối sẵn, firmware chưa hỗ trợ thì báo rõ
  "firmware chưa hỗ trợ khối cấu hình qua PC_Link" (trung thực, giống xử firmware cũ).
- localStorage `otl_machine_cfg` cache. i18n sub.maycfg (vi/en).
- **Test PASS:** UI 50 param/7 nhóm/clamp/dirty (Playwright, 0 lỗi JS) + Python save/load
  file + mc_read/write fallback (test_maycfg.py trong scratchpad).

**Cải tiến lần 1 — MỚI LÀM 2/3 (còn dở):**
- [x] Ẩn thanh "Lưu/Áp dụng" chung khi ở trang maycfg (id `setfoot` + toggle trong gotoSub) — ĐÃ ÁP DỤNG.
- [ ] Toolbar bỏ emoji 💾📂 → SVG #i-file (edit bị huỷ, CHƯA áp) + thêm `#mcCount` đếm ô đã đổi.
- [ ] Input MC readonly + tap mở **NUMPAD to** (glove-friendly) — CHƯA làm. Cách: `mcOpenNumpad(k)`
  set `npTarget='__mc:'+k`, dùng modal #numpad + buildNumPad(npKey); mở rộng hàm `okNumpad`
  (bản gán ở ~dòng 5050) bắt sentinel `__mc:` → `_mcClamp` → ghi MC.cur[k] + cập nhật input + dirty.

**CÒN LẠI (thứ tự sáng mai):**
1. Xong cải tiến 1 (numpad + toolbar icon + mcCount).
2. Review code + review design (chụp Playwright lại).
3. Cải tiến 2: ô tìm/lọc nhảy tới param + đếm "đã đổi" + tuỳ chọn "chỉ ghi ô đã đổi".
4. (nền chung) test máy thật · commit · rebuild exe.

> Trạng thái code: 2 sửa của cải tiến 1 đã áp là hợp lệ, feature chạy được. Chưa build lại exe sau feature maycfg.

## Test results
- inventory_db 28/28 · Api wiring 15/15 · sound PASS · flame 6/6 · maycfg UI+Py PASS · exe boot OK (web probe GĐ4/5).
