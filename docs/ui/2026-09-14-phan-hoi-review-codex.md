# Phản hồi dev (Claude) — review OTL Roast Lab 14/09/2026

Review gốc của Codex: [2026-09-14-otl-roast-lab-review.md](2026-09-14-otl-roast-lab-review.md).
Phân vai theo `AGENTS.md`: Codex review, Claude viết code. Mỗi phát hiện đã được **soát lại
trên code trước khi sửa**. Cả 11 mục đều khớp bằng chứng, không bác mục nào. Chỗ nào làm lệch
tiêu chí chấp nhận thì ghi rõ lý do ở mục tương ứng.

Sao lưu trước khi sửa: `docs/ui/backup/OTL Roast Lab.pre-codex-review-0914.html`.

## Tóm tắt

| Mục | Kết luận | Đã làm | Bộ kiểm giữ |
|---|---|---|---|
| RF-01 | Đúng | Mẻ máy thật mất kết nối: app không tự đếm, không tự chốt. Nối lại thì bám tiếp; đồng hồ máy lùi thì đóng mẻ cũ **GIÁN ĐOẠN**. Giữ "Kết thúc mẻ" lúc mất kết nối thì hỏi đóng GIÁN ĐOẠN | `test_ui_review_0914` · `test_inventory_rebase` |
| RF-02 | Đúng, **nặng hơn review tả** | `queued` → chờ máy báo cờ `drop` (hạn 10 giây) mới chốt; chặn bấm lại lúc đang chờ; chặn **mẻ ma** (xem mục Phát hiện thêm) | `test_ui_review_0914` · `test_ui_autodrop` · `test_ui_compat_roast` |
| RF-03 | Đúng | Chờ tự nạp thành **lời hẹn gắn hồ sơ** `{số, tên, nhiệt nạp}`; đổi hồ sơ/đổi nhiệt nạp là huỷ; dòng "Đang chờ TỰ NẠP … chạm để HỦY" trên màn chờ | `test_ui_review_0914` · `test_ui_personalization` |
| RF-04 | Đúng | Tự xả hỏng: trả cờ, thử lại cách 5 giây, **trần 3 lần**, băng đỏ bền | `test_ui_review_0914` |
| RF-05 | Đúng | Sửa kg sau mẻ → `rebase_batch` chỉnh kho + đơn theo **chênh lệch**, idempotent; sổ `order_credits` chống cộng đơn hai lần | `test_inventory_rebase` |
| RF-06 | Đúng, **làm khác tiêu chí** | Chống phản hồi cũ đè hộp chi tiết mẻ (cả `bdCupList`); "Rang lại" khoá theo cặp (số hồ sơ, tên), trùng tên thì bắt thợ chọn | `test_ui_review_0914` |
| RF-07 | Đúng | BT không phải số hữu hạn → báo "Đang chờ số nhiệt hạt (BT)", không mở mẻ; vá luôn chỗ chấm mốc tay cùng loại lỗi | `test_ui_review_0914` |
| RF-08 | Đúng | Ô ghi chú 400 ký tự khớp kho; kho **từ chối** thay vì cắt lặng; ô kg giữ nháp khi lưu ghi chú | `test_ui_review_0914` · `test_inventory_rebase` · `test_ui_workflow` |
| RF-09 | Đúng, **làm khác tiêu chí** | Gắn `role=dialog`/`alertdialog`, `aria-modal`, `aria-labelledby` cho mọi `.overlay`; ô hồ sơ/công thức có tên; tiêu điểm vào–ra + Tab xoay vòng | `test_ui_review_0914` |
| RF-10 | Đúng | `.bp-bt` dùng `--bt-ink` | `test_ui_review_0914` · `test_ui_colors_fonts` |
| RF-11 | Đúng — sửa **bộ kiểm**, không sửa app | Chốt hợp đồng nhãn "ngày/tháng/năm" (đổi có chủ ý, có ghi lý do trong code); ghi vào đặc tả thiết kế | `test_ui_overview_history` |

## Chi tiết và chỗ lệch tiêu chí

**RF-01.** Tiêu chí có ý "cho thợ chọn phục hồi hoặc đóng INTERRUPTED". Bản vá không dựng hộp
"phục hồi" riêng: nối lại mà đồng hồ máy không lùi thì app **tự bám tiếp đúng mẻ đó**. Đó chính
là phục hồi, và không bắt thợ bấm gì giữa lúc hạt đang cháy. Đường đóng tay đi qua nút thợ vốn
sẽ bấm (giữ "Kết thúc mẻ"), có hộp hỏi. Mẻ gián đoạn:
- vẫn trừ kho (hạt đã vào trống)
- **không** cộng tiến độ đơn
- không ghi đè curve mẫu của hồ sơ
- không cho làm hồ sơ chuẩn
- tiêu đề tổng kết là "⚡ Mẻ gián đoạn" chứ không phải "✓ Mẻ hoàn tất"

**RF-02.** Nguồn xác nhận:
- pclink: bit `drop` trong khối cờ; progStep rời dải CHARGE..DROP cũng chốt, qua nhánh sẵn có của `applyMachine`
- tương thích: đọc lại thanh ghi lệnh 15

Hạn 10 giây lấy theo `CONFIRM_WAIT` có sẵn (cờ về đường vòng HMI 1,5–2,5 giây). Hết hạn:
- băng đỏ bền
- băng lệnh thanh đầu chuyển `timeout`
- mẻ **vẫn mở**
- lệnh tay **không** tự gửi lại

Không tách thêm trạng thái `failed/timeout` cho mọi lệnh máy: băng lệnh `uxCommand` đã có đủ
`sending/queued/confirmed/failed/timeout`, chỉ nối lệnh xả vào đó.

**RF-06.** Hồ sơ hiện **chưa có mã bền**. Chúng sống trong localStorage + `profiles.json` +
CSV protocol máy, nên thêm trường ID là đổi định dạng lưu ở ba nơi, cần một đợt riêng. Bản vá
khoá theo cặp (số hồ sơ, tên) mà mẻ đã ghi lúc mở:
- cặp khớp → dùng hồ sơ đó
- lệch số nhưng tên chỉ khớp **một** hồ sơ → dùng hồ sơ đó (thợ đã xếp lại thứ tự)
- khớp từ hai hồ sơ trở lên → **mơ hồ**, báo thợ chọn trong thư viện, không tự nạp gì

Tiêu chí an toàn "dữ liệu cũ mơ hồ phải yêu cầu thợ chọn" đạt; phần "ID bền vững" để đợt sau.

**RF-09.** Gắn ngữ nghĩa bằng một hàm chung (`a11yHopThoai`, chạy lại khi DOM đổi) thay vì
sửa tay 15 khối markup, để hộp dựng sau cũng ăn. Nhãn nối bằng `aria-labelledby`, không đổi
`<span>` thành `<label for>`: đổi sang label thì chạm vào nhãn là đưa tiêu điểm vào ô, dễ bung
bàn phím hệ điều hành trên màn cảm ứng.

Mở hộp thì tiêu điểm vào **khung hộp** chứ không vào ô nhập đầu tiên, cùng lý do bàn phím cảm
ứng. Bàn phím số, bàn phím chữ và bảng chọn cố ý để ngoài: tiêu điểm phải ở lại ô đang nhập.

## Phát hiện thêm khi sửa (ngoài review)

1. **Mẻ ma ở pclink.** Chốt mẻ ngay khi lệnh xả `queued`. Nhịp snapshot sau, progStep còn
   trong dải rang (cờ về trễ), nên `applyMachine` gọi `startRoast()` và **mở luôn một mẻ mới**.
   Vá bằng `_machHoldoff`: sau khi chốt, chỉ tự vào mẻ khi đã thấy máy rời dải một lần.
2. `bdCupList` cùng lỗi phản hồi cũ đè hộp mới như `openBatch`.
3. Lúc tới nhiệt nạp, lời hẹn còn được so lại với hồ sơ/nhiệt nạp đang nạp (lưới thứ hai).
   Đổi nhiệt nạp bằng tay cũng huỷ lời hẹn.
4. Soi ảnh bắt được hai lỗi hiển thị do chính đợt vá sinh ra, đều đã sửa:
   - toast trùng chữ với băng đỏ, che đồ thị
   - tổng kết mẻ gián đoạn vẫn mang "✓ Mẻ hoàn tất" xanh

## Bẫy của bộ kiểm (không phải lỗi app)

Playwright `page.evaluate(...)` mà biểu thức **trả về promise đang chờ hộp hỏi**
(`startRoast()`, `cmdDrop()`) thì Chromium headless-shell báo `Target crashed`.

Đã tái hiện **y hệt trên bản sao lưu trước khi vá**, nên đây là tật môi trường. Cách tránh:
gọi kiểu bắn-rồi-quên `() => { startRoast(); }`, sau đó bấm nút trong hộp.

## Còn treo

- **Chưa thử máy thật.** Cần đo trên máy: cờ `drop` về sau bao lâu ở cả pclink lẫn tương thích,
  để chốt hạn `DROP_CONFIRM_MS`.
- ID bền cho hồ sơ (RF-06 phần gốc): đợt riêng, đổi định dạng lưu.
- Mẻ chốt **trước** đợt vá không có sổ `order_credits`: sửa kg chỉ chỉnh kho, không chỉnh đơn.
- Interlock gas, giám sát lửa, watchdog, E-stop độc lập app: ngoài phạm vi đợt này, đúng như review ghi.

## Kiểm thử

Chạy 14/09/2026, lần cuối là **sau cả đợt thợ rang dùng thử cùng ngày**:

- **Trọn bộ `tools/test_ui_*.py`: 31/31 ĐẠT.**
- Bộ kiểm mới `test_ui_review_0914.py`: ĐẠT (dựng đúng tình huống từng RF rồi đo hành vi).
- Bộ kiểm mới `test_inventory_rebase.py`: 19/19 ĐẠT.
- `test_otl_link` ĐẠT · `test_api_scope` exit 0 · `test_mcp_roaster` **BỎ QUA** vì app không
  chạy ở cổng 8555, nên không tính là đạt.
- `node --check` trên mọi khối `<script>`: sạch.

Bộ kiểm sửa theo **hợp đồng mới**. Không nới luật nào:

| Bộ kiểm | Sửa gì |
|---|---|
| `test_ui_compat_roast` | Stub đọc lại thanh ghi drop như máy thật |
| `test_ui_personalization` | `_autoCharge` nay là object lời hẹn |
| `test_ui_overview_history` | Hợp đồng nhãn "ngày/tháng/năm" |
| `test_ui_hold_confirm` | Xoá lời chờ xả và cờ lạc quan giữa các kịch bản độc lập |
| `test_ui_match_reference` | Nút Tăng nhiệt nay ở chú giải thanh đầu |

⚠ `test_ui_hold_confirm` mục `#btnEscape` vẫn **chập chờn**:
- Chạy riêng 3 lần thì 2 lần đỏ.
- Lần chạy trọn bộ cuối cùng thì ĐẠT.
- Lỗi này có từ 11/09, chưa tìm ra gốc. Đợt vá không đụng tới cơ chế giữ nút.

**Chưa chạy trên máy rang thật.**
