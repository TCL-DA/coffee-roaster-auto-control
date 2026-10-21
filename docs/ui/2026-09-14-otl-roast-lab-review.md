# Review OTL Roast Lab — 14/09/2026

## Kết luận chính

OTL Roast Lab đã đạt mức tốt về bố cục HMI, thao tác cảm ứng và ngôn ngữ của quy trình rang. Màn Rang thể hiện đúng các đối tượng người vận hành cần nhìn: BT, ET, RoR, DE, FCs, DROP, gas, gió, trống, đường mục tiêu và mẻ nền. Tuy nhiên bản hiện tại **chưa nên coi là sẵn sàng xác nhận trên máy thật** vì còn các lỗi P1 ở ranh giới giữa trạng thái giao diện, hàng đợi lệnh và trạng thái máy.

Review này chỉ đọc mã và chạy mô phỏng/bộ kiểm; không nối máy, không phát lệnh nạp/xả và không kiểm chứng cơ cấu thật.

## Phạm vi và phương pháp

- Bản được review: `OTL Roast Lab.html` cùng cầu Python và kho dữ liệu hiện hành.
- Luồng rang đối chiếu: chọn hồ sơ → làm nóng → nạp → TP → DE → FCs → phát triển → DROP → làm nguội/tổng kết.
- Nguyên tắc rang: tách quan sát, giả thuyết và khuyến nghị; không coi một nhiệt độ hay tỷ lệ phát triển là “chuẩn” cho mọi hạt/máy.
- Open Design: hierarchy, state coverage, contrast, accessibility, form validation, motion và Laws of UX.
- Chuẩn tham chiếu ngoài: [WCAG 2.2 — Contrast Minimum](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum), [W3C H44 — liên kết label với control](https://www.w3.org/WAI/WCAG22/Techniques/html/H44), [ISA-101 — HMI cho công nghiệp](https://www.isa.org/standards-and-publications/isa-standards/isa-standards-committees/isa101).
- Bộ kiểm: chạy 30 file `tools/test_ui_*.py`. Sau khi chạy lại hai bài kiểm bị lỗi console bằng UTF-8: 28 bài đạt; 1 bài phát hiện lỗi tương phản thật; 1 bài đỏ vì hợp đồng test cũ không khớp nhãn ngày mới.

## Điểm đang làm tốt

1. **Thứ bậc màn Rang đúng việc.** Các số BT/ET/thời gian và ba điều khiển gas–gió–trống tạo thành hai cụm đọc rõ; dải TP–DE–FCs–DEV–DROP biến tiến trình rang thành một chuỗi dễ quét thay vì một bảng số rời rạc.
2. **Điều khiển hệ trọng có ma sát hợp lý.** Xả liệu/kết thúc mẻ dùng thao tác giữ, có tiến trình và câu hướng dẫn; bài kiểm giữ nút, nhả sớm, kéo ra ngoài và nhiều ngón đều đạt.
3. **Màn cảm ứng được chăm kỹ.** Bố cục sáu tab, các hộp thoại và thanh thao tác không tràn/chồng ở 1920×1080, 1366×768 và 1280×800; mục tiêu chạm 44 px trở lên được kiểm tự động.
4. **Đường rang dự kiến có giá trị chuyên môn.** DE, FCs, DROP, giờ mốc, RoR tại mốc, mẻ nền và cảnh báo kế hoạch giúp thợ đọc quan hệ giữa nhiệt, thời gian và năng lượng; không chỉ trang trí một curve đẹp.
5. **Trạng thái mất kết nối trên phần hiển thị đã rõ.** Các số máy được xoá về “—”, không giữ số cũ; nút bị khoá có giải thích thay vì chỉ mờ đi.
6. **Hệ thống thị giác có tính riêng.** IBM Plex, bảng màu Than hồng và cách dùng typography/mono tạo đúng cảm giác công cụ xưởng, không giống dashboard mẫu chung.

## Phát hiện cần xử lý

### RF-01 · P1 — Mất kết nối giữa mẻ có thể làm app tự chốt mẻ cục bộ

- **Bằng chứng:** `dsLive()` chỉ đúng khi `DS.state==='connected'`; `roastTick()` chỉ ngừng đếm khi `dsLive()` đúng. Khi kết nối rơi, đồng hồ cục bộ chạy tiếp và tới `ROAST_SECS` sẽ gọi thẳng `finishRoast()` (`OTL Roast Lab.html:6760`, `8671–8677`).
- **Tác động:** app có thể hiện DONE, đóng bản ghi và tổng kết trong khi máy vẫn đang rang hoặc chưa mở cửa xả. Đây là sai lệch trạng thái vận hành, dễ làm thợ hiểu nhầm hơn một lỗi lưu lịch sử thông thường.
- **Chấp nhận sửa:** mất telemetry/stale khi đang rang phải vào trạng thái gián đoạn riêng, giữ nguyên mốc cuối đã xác nhận và không tự chốt/xả. Chỉ tiếp tục khi máy xác nhận lại cùng mẻ; nếu không thì cho thợ chọn phục hồi hoặc đóng `INTERRUPTED`.

### RF-02 · P1 — “Đã xếp hàng” đang được coi là “máy đã thực hiện” khi xả

- **Bằng chứng:** cầu trả `{ok:true,status:'queued'}` ngay khi thêm lệnh vào `_pending` (`tools/otl_link.py:439–444`). `machCmd()` đổi trạng thái thành `queued` nhưng vẫn trả `true`; `cmdDrop()` và `autoDrop()` lập tức gọi `finishRoast()` (`OTL Roast Lab.html:7740–7763`, `7936–7966`).
- **Tác động:** thông báo/tổng kết có thể đi trước cơ cấu; snapshot trễ hoặc lệnh không tới máy có thể tách một mẻ thật thành trạng thái DONE sai.
- **Chấp nhận sửa:** thêm trạng thái `DROP_PENDING`; chỉ chốt một lần sau khi snapshot/cờ máy xác nhận cửa xả hoặc bước DROP. Có timeout, mất kết nối và từ chối rõ; không tự gửi lặp vô hạn.

### RF-03 · P1 — Đổi hồ sơ không huỷ ý định tự nạp của hồ sơ trước

- **Bằng chứng:** `loadProfile()` đặt lại nhiệt, mốc và dữ liệu mẻ nhưng không xoá `R._autoCharge` (`OTL Roast Lab.html:8851–8903`). `chkChargeReady()` sẽ dùng cờ này để tự gọi `cmdCharge()` khi BT chạm nhiệt của hồ sơ mới (`8973–8988`).
- **Tác động:** một quyết định nạp dành cho hồ sơ A có thể được thực hiện theo nhiệt hồ sơ B.
- **Chấp nhận sửa:** đổi hồ sơ phải huỷ chờ tự nạp hoặc yêu cầu xác nhận lại, nêu rõ tên hồ sơ và nhiệt nạp mới. Trạng thái đang chờ và nút huỷ phải nhìn thấy được.

### RF-04 · P1 — Tự xả thất bại vẫn khoá các lần xử lý tiếp theo

- **Bằng chứng:** khi BT vượt ngưỡng, `R._dropFired=true` được đặt trước khi `autoDrop()` hoàn tất; nhánh lệnh bị từ chối/throw không trả cờ về (`OTL Roast Lab.html:8964–8968`).
- **Tác động:** cơ chế tự xả của app ngừng tham gia cho phần còn lại của mẻ sau một lỗi gửi lệnh.
- **Chấp nhận sửa:** tách `pending`, `confirmed`, `failed`; lỗi phải để lại cảnh báo bền và đường xử lý có kiểm soát. Không tự thử lại vô hạn.

### RF-05 · P1 — Khối lượng thật sau mẻ không điều chỉnh giao dịch kho/tiến độ đơn

- **Bằng chứng:** `finishRoast()` không gửi `charge_kg` trong summary (`OTL Roast Lab.html:8731–8737`), nên `_inv_on_finish()` dùng định mức cấu hình để trừ kho và cộng tiến độ (`tools/roast_lab_hmi.py:674–694`). Sau đó `db_batch_set_weight()` chỉ sửa cột `batches.charge_kg`, không điều chỉnh ledger/đơn.
- **Tác động:** lịch sử mẻ có thể ghi 3 kg nhưng kho vẫn trừ 6 kg và đơn vẫn cộng sản lượng suy từ 6 kg.
- **Chấp nhận sửa:** thu khối lượng đầu vào trước khi chốt, hoặc tạo giao dịch điều chỉnh idempotent gắn với `batch_id` khi sửa/xoá khối lượng. Kiểm lại không được trừ/cộng hai lần.

### RF-06 · P1 — Chi tiết mẻ và “Rang lại” chưa dùng định danh bền vững

- **Bằng chứng:** `openBatch()` không có request token/sequence nên phản hồi cũ có thể ghi đè modal mới (`OTL Roast Lab.html:4935–4963`). `uxProfileForBatch()` và `uxRoastAgain()` tìm hồ sơ bằng `name` (`11640`, `11657–11662`).
- **Tác động:** mở nhanh A rồi B có thể ghép tiêu đề B với dữ liệu/QC của A; hai hồ sơ trùng tên có thể chuẩn bị sai profile cho mẻ kế.
- **Chấp nhận sửa:** mọi tải chi tiết phải gắn generation/request id và bỏ phản hồi cũ. “Rang lại” dùng ID hồ sơ bền vững; dữ liệu cũ mơ hồ phải yêu cầu thợ chọn.

### RF-07 · P2 — Thiếu kiểm tra BT hữu hạn trước khi định dạng

- **Bằng chứng:** `const bt=DS.snap?DS.snap.bt:0`; nếu snapshot tồn tại nhưng thiếu/null/chuỗi ở `bt`, các lệnh `bt.toFixed(1)` có thể ném lỗi (`OTL Roast Lab.html:8620–8653`).
- **Tác động:** nút BẮT ĐẦU có thể im lặng hoặc ném lỗi đúng lúc dữ liệu máy mới kết nối/chưa đủ trường.
- **Chấp nhận sửa:** chỉ so nhiệt và gọi `toFixed` khi `Number.isFinite(Number(bt))`; nếu chưa có BT thì hiện “Đang chờ dữ liệu nhiệt hạt” và không mở mẻ.

### RF-08 · P2 — Hợp đồng ghi chú và dữ liệu form sau mẻ chưa thống nhất

- **Bằng chứng:** UI cho nhập 2.000 ký tự (`OTL Roast Lab.html:11257`) nhưng kho cắt còn 400 mà vẫn trả `ok:true` (`tools/inventory_db.py:478–496`). `uxDoneNoteSave()` gọi `uxDoneRender()` trong `finally`; khi focus đã sang nút Lưu, `uxDoneRender()` có thể ghi đè ô kg bằng giá trị cũ (`OTL Roast Lab.html:11669–11677`, `11700–11706`).
- **Tác động:** mất dữ liệu im lặng hoặc xoá phần kg đang soạn nhưng chưa lưu.
- **Chấp nhận sửa:** thống nhất giới hạn UI/backend và từ chối có thông báo thay vì cắt chuỗi. Giữ draft độc lập cho kg/ghi chú qua mọi trạng thái lưu thành công/thất bại.

### RF-09 · P2 — Phần lớn hộp thoại và ô hồ sơ thiếu semantics truy cập

- **Bằng chứng:** chỉ hộp Giới thiệu có `role="dialog" aria-modal="true"`; `profedit`, `napedit`, `askbox`, `batchDetail`, `khoForm`, `batchCompare` và các overlay khác không có vai trò/tên modal. Các ô hồ sơ dùng `<span class="pel">` cạnh `<input>` nhưng không có `label for`, `aria-label` hoặc `aria-labelledby` (`OTL Roast Lab.html:4284–4514`). Escape đã được bổ sung, nhưng quản lý focus/trap/restore chưa đồng nhất.
- **Tác động:** trình đọc màn hình và điều khiển bằng giọng nói không xác định chắc ô “Nhiệt DE”, “FCs”, “Mẻ nạp”…; phím Tab có thể thoát ra nền app khi modal mở. Đây là lỗi quan hệ name/role, không phải sở thích thiết kế. W3C yêu cầu control có tên/vai trò xác định được và mô tả `label[for]` là cách chuẩn để liên kết nhãn với ô nhập.
- **Chấp nhận sửa:** chuẩn hoá một modal shell dùng `dialog` hoặc role tương đương, có `aria-modal`, `aria-labelledby`, focus đầu vào, trap và restore. Đổi nhãn visible thành `<label for>` hoặc nối `aria-labelledby` cho toàn bộ form.

### RF-10 · P2 — Số BT trên viên trạng thái không đạt tương phản nền sáng

- **Bằng chứng:** `#batchPill .bp-bt` dùng `--accent-txt`; bài kiểm đo “182°” cỡ 16 px đạt 3,23:1 trên cả sáu tab ở nền sáng (`OTL Roast Lab.html:2076`, `6856`, `11897`). WCAG 2.2 yêu cầu 4,5:1 cho chữ thường.
- **Tác động:** số BT nhỏ nhưng quan trọng bị yếu trên màn sáng/xưởng nhiều ánh sáng.
- **Chấp nhận sửa:** dùng token BT ink đủ ≥4,5:1 ở mọi accent/theme; thêm test theo từng bảng màu thay vì chỉ một màu mặc định.

### RF-11 · P3 — Bài kiểm nhãn ngày đã lệch khỏi hợp đồng giao diện mới

- **Bằng chứng:** UI hiện “Từ ngày (ngày/tháng/năm)” và “Đến ngày (ngày/tháng/năm)” (`OTL Roast Lab.html:11355–11363`), nhưng test chỉ chấp nhận chuỗi literal `dd/mm/yyyy` (`tools/test_ui_overview_history.py:130–135`).
- **Tác động:** pipeline đỏ dù nhãn hiện tại vẫn diễn đạt đúng thứ tự ngày; làm giảm độ tin cậy của bộ kiểm.
- **Chấp nhận sửa:** chốt một copy duy nhất trong đặc tả rồi cho test kiểm đúng hợp đồng đó. Nếu ưu tiên ngắn gọn, dùng `dd/mm/yyyy` ở cả Việt/Anh; nếu ưu tiên thuần Việt, sửa test chấp nhận “ngày/tháng/năm”.

## Thứ tự bàn giao đề xuất

1. Sửa RF-01 đến RF-04 trước, vì cùng một lớp trạng thái lệnh/máy và ảnh hưởng trực tiếp đến niềm tin của người vận hành.
2. Sửa RF-05 và RF-06 để giữ tính toàn vẹn mẻ, kho, đơn và profile.
3. Sửa RF-07/08, sau đó chuẩn hoá modal/form RF-09.
4. Chốt màu BT RF-10 và hợp đồng nhãn ngày RF-11.
5. Chạy lại toàn bộ `test_ui_*`, bổ sung ca queued lâu, snapshot stale/mất BT, đổi hồ sơ khi đang arm tự nạp, lệnh auto-drop bị từ chối, A-chậm/B-nhanh, tên hồ sơ trùng và giao dịch kg idempotent.

## Tiêu chí trước khi thử máy thật

- Không trạng thái DONE nào xuất hiện nếu chưa có xác nhận DROP hoặc quyết định đóng mẻ gián đoạn rõ ràng.
- Mất link/stale không tự tiến đồng hồ, không tự chốt, không tự gửi lại lệnh.
- Mọi lệnh hệ trọng phân biệt được `queued`, `confirmed`, `failed`, `timeout`.
- Đổi hồ sơ xoá sạch ý định tự động của hồ sơ cũ.
- Kho, đơn và mẻ dùng cùng một khối lượng có nguồn gốc rõ.
- Kiểm interlock gas, flame supervision, watchdog, E-stop và quyền HMI độc lập với app; review này không thay kiểm thử an toàn tại máy.

