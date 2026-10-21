# Rà soát giao diện xuyên suốt quy trình rang — 08/09/2026

## Phạm vi và bằng chứng

Rà bản nguồn `OTL Roast Lab.html`, đối chiếu `tools/otl_link.py`, `tools/roast_lab_hmi.py`, `tools/roast_db.py` khi cần hiểu dữ liệu/lệnh. Các chặng: kết nối → chọn hồ sơ/công thức → làm nóng/chờ nạp → rang và điều khiển → xả/làm nguội → tổng kết/lưu → mẻ kế tiếp/lịch sử.

Bản HTML kiểm tra có SHA256 `9EAE0E541863CDF8EE3932420D0F2E1A5553188CCD8DF0406CCB9821D6581B05`, thời điểm sửa trên đĩa 08/09/2026 10:23:23. Đây là đánh giá bản nguồn trong Chromium với cầu máy giả, chưa chứng minh hành vi của EXE/WebView2 hoặc máy rang thật.

Áp dụng quy tắc Open Design từ `F:/Project/open-design/craft/`: `state-coverage.md`, `form-validation.md`, `accessibility-baseline.md`, `typography-hierarchy.md`. Đối chiếu `2026-09-07-design-spec.md` và mirror `design-web/Rang - Sua lai.dc.html`. Chỉ dùng tài nguyên thiết kế, không chạy engine Open Design. Không sửa app, firmware hay bộ kiểm; không tạo ảnh/video bàn giao, không gửi lệnh phần cứng.

Phân việc: Astra high kiểm lỗi chuyển trạng thái/lệnh; Sol high kiểm hậu mẻ và dữ liệu; Luna high kiểm tính nhất quán và hộp thoại; agent chính đối chiếu bằng chứng, chạy hồi quy và tái hiện độc lập một số lỗi. Không coi số lượng reviewer là bằng chứng đúng.

P1: ưu tiên xử lý trước vì có thể khiến trạng thái/ý định điều khiển sai hoặc làm hỏng tính liên tục của mẻ. P2: ảnh hưởng thao tác, dữ liệu hoặc khả năng phục hồi. P3: nhất quán ngôn ngữ/trình bày. Mức ưu tiên không phải khẳng định đã xảy ra sự cố trên phần cứng.

## Lỗi đã tái hiện ở đầu và giữa mẻ

### RF-01 · P1 — Mất kết nối có thể tự chốt mẻ khi tới thời gian mục tiêu

- **Nguồn:** `OTL Roast Lab.html:6704` (`roastTick`), `6756` (chốt kho).
- **Tái hiện:** mẻ máy đang RUNNING, thời gian bằng `ROAST_SECS - 1`; chuyển kết nối sang `error`, chạy một nhịp đồng hồ.
- **Kết quả:** app chuyển DONE và gọi `db_batch_finish` một lần dù không gửi lệnh xả. Nguyên nhân là mất `dsLive()` khiến nhánh đồng hồ mô phỏng hoạt động trên mẻ máy.
- **Tác động:** màn hình báo hết mẻ trong khi chưa biết máy đã xả; mất tính liên tục của giám sát và bản ghi.
- **Chấp nhận sửa:** phân biệt nguồn mẻ với tình trạng kết nối. Mẻ thật mất kết nối giữ trạng thái chưa xác định/đang rang, không tự chốt theo đồng hồ mô phỏng; nối lại phải tiếp tục đúng mẻ.

### RF-02 · P1 — Báo hoàn tất khi lệnh xả mới được xếp hàng

- **Nguồn:** `OTL Roast Lab.html:6031`, `6051`, `5593`; `tools/otl_link.py:424`; `tools/roast_lab_hmi.py:579`.
- **Tái hiện:** PC_Link ở step 8, `drop=false`; cầu trả `{ok:true,status:'queued'}` cho `cmdDrop()`. Sau đó đưa thêm snapshot vẫn ở step 8.
- **Kết quả:** app chuyển DONE và chốt kho ngay khi queued; snapshot chưa đổi khiến app trở lại RUNNING và gọi mở mẻ lần nữa.
- **Tác động:** thông báo xả/hoàn tất đi trước trạng thái máy; có thể cắt một lần rang thành nhiều bản ghi. Backend còn xử lý kho/tiến độ khi chốt, nên đây không chỉ là nhãn sai.
- **Chấp nhận sửa:** có trạng thái chờ xác nhận xả; chỉ chốt một lần khi trạng thái máy đủ xác nhận. Kiểm queued lâu, snapshot trễ, từ chối và mất kết nối. Không sửa bộ kiểm để tiếp tục yêu cầu DONE ngay sau queued.

### RF-03 · P1 — Đổi hồ sơ vẫn giữ chờ tự nạp của hồ sơ cũ

- **Nguồn:** `OTL Roast Lab.html:6868` (`loadProfile`), `6984` (`chkChargeReady`).
- **Tái hiện:** gài chờ nạp cho hồ sơ A ở 180°C; đổi sang hồ sơ B ở 160°C; đưa BT lên 160°C.
- **Kết quả:** `_autoCharge` không bị hủy và app gửi `charge=1` theo nhiệt B dù chưa xác nhận bắt đầu B.
- **Tác động:** ý định nạp cho một hồ sơ tự chuyển sang hồ sơ khác.
- **Chấp nhận sửa:** đổi hồ sơ phải hủy chờ hoặc yêu cầu xác nhận lại rõ tên hồ sơ/nhiệt nạp. Trạng thái đang chờ và thao tác hủy phải nhìn thấy được.

### RF-04 · P1 — Tự xả thất bại một lần thì cờ đã xả vẫn bị giữ

- **Nguồn:** `OTL Roast Lab.html:6967`, `6044`.
- **Tái hiện:** đặt ngưỡng xả 195°C; cầu từ chối lệnh với `{ok:false}` ở BT 200°C; đưa BT lên 201°C.
- **Kết quả:** `_dropFired=true` từ trước kết quả gửi, không được phục hồi; không có lần gửi tiếp, app vẫn RUNNING.
- **Tác động:** cơ chế tự xả của app không còn hoạt động cho phần còn lại của mẻ sau một lần lỗi; không kết luận cơ chế độc lập của firmware cũng mất tác dụng.
- **Chấp nhận sửa:** phân biệt đang gửi/đã xác nhận/thất bại; thất bại phải có cảnh báo bền và cách xử lý rõ hoặc thử lại có kiểm soát. Không tự động gửi lặp vô hạn.

### RF-05 · P2 — Bắt đầu khi mất kết nối mở mẻ cục bộ qua cầu máy

- **Nguồn:** `OTL Roast Lab.html:2947`, `6639`, `6689`.
- **Tái hiện:** đã chọn hồ sơ, cầu desktop tồn tại nhưng `DS.state='error'`; bấm trực tiếp nút BẮT ĐẦU.
- **Kết quả:** nút vẫn bật; app chuyển RUNNING, gọi `link_begin_batch` một lần, không gửi nạp. Agent chính đã tái hiện bằng cú bấm nút, không chỉ gọi hàm.
- **Chấp nhận sửa:** khi đang dùng cầu máy nhưng chưa có dữ liệu, chặn mở mẻ và chỉ đường nối lại. Mô phỏng phải là chế độ có chủ ý, không phải nhánh rơi xuống khi lỗi kết nối.

### RF-06 · P2 — Snapshot thiếu BT làm nút BẮT ĐẦU ném lỗi JavaScript

- **Nguồn:** `OTL Roast Lab.html:6683`.
- **Tái hiện:** connected/pclink, `pc_control=true`, chưa có lửa, snapshot thiếu `bt`; bấm BẮT ĐẦU.
- **Kết quả:** `Cannot read properties of undefined (reading 'toFixed')`; không có phản hồi phục hồi cho thao tác. Agent chính đã tái hiện lại bằng nút thật trong trình duyệt.
- **Chấp nhận sửa:** BT phải hữu hạn trước mọi xử lý nhiệt; hiển thị chờ dữ liệu thay vì ném lỗi. Bao phủ thiếu trường, null và dữ liệu không hợp lệ, cả khi có/không có lửa.

### RF-07 · P2 — Tổng quan đồng thời cảnh báo chưa sẵn sàng và báo “Sẵn sàng nạp”

- **Nguồn:** `OTL Roast Lab.html:9261`, `9268`, `9277`, `9331`.
- **Tái hiện:** hồ sơ đặt 180°C, BT 220°C. Dòng hướng dẫn báo BT cao hơn ngưỡng nhưng bước 1 hiện “Đã đủ nhiệt · 220/180°C”, bước 3 hiện “Sẵn sàng nạp”. Với BT trong ngưỡng nhưng PC control tắt, bước 3 vẫn báo sẵn sàng. Với trạng thái error còn snapshot cũ, bước 1 báo chưa có dữ liệu nhưng bước 3 vẫn sẵn sàng.
- **Nguyên nhân:** `hot` chỉ kiểm cận dưới nhiệt và dùng snapshot, không dùng cùng điều kiện sẵn sàng với hướng dẫn.
- **Chấp nhận sửa:** dùng cùng kết quả kiểm điều kiện cho hướng dẫn và ba bước. Trạng thái quá nhiệt, mất kết nối, chưa có quyền điều khiển không được hiện sẵn sàng nạp.

## Hộp thoại chuẩn bị hồ sơ/công thức

### RF-08 · P2 — Hộp thoại thiếu nhãn truy cập và quản lý bàn phím

- **Nguồn:** `OTL Roast Lab.html:3727`, `3732`, `3769`, `3771`, `3887`.
- **Tái hiện:** mở tạo hồ sơ; focus không chuyển vào hộp thoại, Escape không đóng. Root thiếu `role="dialog"` và ngữ nghĩa modal. Input dùng chữ trong `span`, không có label liên kết hoặc tên ARIA; agent chính xác nhận ở toàn bộ 13 input của hộp hồ sơ. Luna xác nhận thêm ở công thức nạp.
- **Tác động:** người dùng bàn phím hoặc công cụ đọc màn hình khó xác định ô đang nhập và thoát hộp thoại.
- **Chấp nhận sửa:** có tên hộp thoại, label đúng cho input, đưa/giữ/trả focus hợp lý. Escape đóng khi không có thay đổi; có dữ liệu chưa lưu phải bảo vệ dữ liệu theo quy ước nhất quán.

### RF-09 · P3 — Đổi sang tiếng Anh nhưng hộp sửa vẫn trộn tiếng Việt và thuật ngữ cũ

- **Nguồn:** `OTL Roast Lab.html:3727`, `3769`.
- **Tái hiện:** đổi `LANG='en'`, áp ngôn ngữ, mở hồ sơ/công thức. Vẫn thấy “Sửa hồ sơ”, “Nhiệt charge”, “Hủy”, “Lưu”; công thức còn “Gas / Burner”, “Gió / Airflow”.
- **Chấp nhận sửa:** toàn bộ nội dung hộp thoại đổi theo ngôn ngữ; bản Việt dùng “Nhiệt nạp”, “Mức gas”, “Lượng gió” theo đặc tả. Kiểm cả hộp mở sau khi đổi ngôn ngữ.

## Tổng kết, lưu dữ liệu, lịch sử và mẻ kế tiếp

### RF-10 · P1 — Khối lượng nhập sau mẻ không điều chỉnh lượng đã trừ kho/tiến độ đơn

- **Nguồn:** `OTL Roast Lab.html:6755`, `9528`; `tools/roast_lab_hmi.py:597`, `815`; `tools/roast_db.py:271`.
- **Tái hiện:** cấu hình định mức 6 kg, có lô đang dùng/đơn phù hợp; chốt mẻ qua luồng hiện tại, sau đó lưu khối lượng thực 3 kg. Sol kiểm trên DB tạm theo luồng `_inv_on_finish`.
- **Kết quả:** mẻ ghi 3 kg nhưng giao dịch kho vẫn -6 kg; với hao hụt định mức 15%, đơn được cộng 5,1 kg. `finishRoast` không gửi khối lượng; backend dùng định mức ngay lúc chốt, còn lưu kg sau đó chỉ cập nhật bảng mẻ.
- **Tác động:** lịch sử mẻ và kho/tiến độ đơn không cùng một khối lượng. Mức ảnh hưởng tới báo cáo phụ thuộc nơi lấy số liệu.
- **Chấp nhận sửa:** xác định rõ số ước lượng và số thực; nhập khối lượng trước khi chốt hoặc có giao dịch điều chỉnh theo đúng ID mẻ khi lưu/sửa/xóa. Thử lại không được trừ/cộng hai lần. Bao phủ trường hợp không có lô/đơn.

### RF-11 · P1 — Mở nhanh hai mẻ ghép tiêu đề mẻ B với dữ liệu và nơi lưu ghi chú của mẻ A

- **Nguồn:** `OTL Roast Lab.html:4093`, `4102`, `4116`, `4122`, `4151`.
- **Tái hiện:** mở mẻ A có phản hồi chậm 140 ms, đóng rồi mở mẻ B có phản hồi nhanh. Cầu giả trả kết quả A sau B.
- **Kết quả:** tiêu đề `#B-0002` nhưng thống kê vẫn 10:01/191°C của A và `BD_CUP.id=1`. Hàm `openBatch` không kiểm lượt yêu cầu trước khi cập nhật phần còn lại của hộp thoại.
- **Tác động:** có thể đọc sai đường cong/thống kê và lưu QC hoặc ghi chú vào mẻ khác với mã đang nhìn thấy.
- **Chấp nhận sửa:** mọi dữ liệu, tiêu đề và ID lưu cùng một mẻ; bỏ kết quả cũ khi đóng/chuyển mẻ. Chưa tải xong phải khóa thao tác lưu phụ thuộc dữ liệu. Kiểm A chậm/B nhanh và đóng hộp thoại giữa lượt tải.

### RF-12 · P2 — Lưu ghi chú xóa khối lượng đang nhập chưa lưu

- **Nguồn:** `OTL Roast Lab.html:9519`, `9545`.
- **Tái hiện:** ở tổng kết nhập 6,50 kg nhưng chưa bấm lưu khối lượng; nhập ghi chú rồi bấm Lưu ghi chú.
- **Kết quả:** ô kg trở thành rỗng khi giá trị kg đã lưu trước đó là null. `finally` gọi `uxDoneRender`; ô kg lúc này không còn focus nên bị ghi đè bởi giá trị cũ trong `c.kg`.
- **Chấp nhận sửa:** giữ riêng dữ liệu người dùng đang sửa; lưu ghi chú không ghi đè ô khối lượng. Kiểm cả ghi chú lưu thành công/thất bại và chuyển focus bằng chuột/bàn phím.

### RF-13 · P2 — Ghi chú được phép nhập 2.000 ký tự nhưng chỉ lưu 400

- **Nguồn:** `OTL Roast Lab.html:9135`, `9549`; `tools/inventory_db.py:478`.
- **Tái hiện:** gửi ghi chú 1.000 ký tự từ hợp đồng ô nhập cho phép tối đa 2.000.
- **Kết quả:** backend trả ok nhưng DB chỉ giữ 400 ký tự (`[:400]`); UI báo thành công và xóa nội dung ô nhập. Sol xác nhận bằng DB tạm; agent chính đối chiếu đoạn cắt chuỗi.
- **Chấp nhận sửa:** thống nhất giới hạn UI/backend hoặc báo lỗi validation rõ; không cắt dữ liệu im lặng. Kiểm 400, 401 và 2.000 ký tự, giữ nội dung khi bị từ chối.

### RF-14 · P1 — “Rang lại” có thể chọn sai hồ sơ khi tên trùng

- **Nguồn:** `OTL Roast Lab.html:4688`, `9485`, `9502`; `tools/roast_db.py:236`.
- **Tái hiện:** tạo hai hồ sơ cùng tên nhưng khác thông số; mẻ lịch sử thuộc hồ sơ thứ hai (`prof_no=2`); bấm Rang lại.
- **Kết quả:** hàm tìm bằng tên lấy phần tử đầu tiên, `R.profNo=1`.
- **Tác động:** lần rang tiếp theo được chuẩn bị với thông số/đường cong hồ sơ khác. Không khẳng định máy đã thực thi những thông số đó trong phép thử này.
- **Chấp nhận sửa:** dùng định danh hồ sơ bền vững, không dùng tên hoặc chỉ số có thể đổi làm khóa duy nhất. Dữ liệu cũ không xác định được duy nhất phải cho người dùng chọn, không âm thầm lấy bản đầu. Kiểm trùng tên, đổi tên, xóa và đổi thứ tự.

## Thứ tự bàn giao đề xuất

Tổng cộng **14 phát hiện: 7 P1, 6 P2, 1 P3**. Các lỗi được tách theo hành vi và tiêu chí sửa; RF-12 và RF-13 đều là mất dữ liệu form nhưng có nguyên nhân khác nhau.

1. Astra cung cấp ca tái hiện/tiêu chí cho RF-01 đến RF-04; Claude xử lý nguồn mẻ, chuyển trạng thái, xác nhận lệnh và chờ tự nạp. Bao gồm RF-05/06 vì dùng chung cổng bắt đầu.
2. Claude xử lý định danh và vòng đời dữ liệu hậu mẻ: RF-10/11/14, rồi RF-12/13. Sol phân tích hợp đồng dữ liệu và kế hoạch thay đổi; nếu người dùng giao GPT trực tiếp lập trình thì ưu tiên Sol.
3. Sửa điều kiện sẵn sàng RF-07 và hộp thoại RF-08/09. Luna kiểm hồi quy các tiêu chí đã chốt.

Reviewer đưa bằng chứng và tiêu chí; dev có quyền bác bỏ hoặc đưa phương án khác bằng bằng chứng. Đây là tài liệu sẵn để bàn giao, chưa có trao đổi trực tiếp với Claude trong phiên này.

## Kết quả hồi quy và giới hạn

Agent chính chạy trực tiếp 10 bộ kiểm hiện có, tất cả trả mã thoát 0:

| Bộ kiểm | Phạm vi |
|---|---|
| `tools/test_ui_workflow.py` | Hồ sơ, trạng thái kho, xác nhận lệnh, tổng kết và sở thích |
| `tools/test_ui_autodrop.py` | Ngưỡng tự xả và cửa xả đã mở |
| `tools/test_ui_touch_hold.py` | Sự kiện chạm, nhiều ngón, hủy cử chỉ, giữ xác nhận |
| `tools/test_ui_roast_columns.py` | Cột, điều khiển, cuộn/thu gọn thiết bị phụ |
| `tools/test_ui_hold_confirm.py` | Giữ 1 giây, nhả sớm, kéo ra, chặn thoát khi rang |
| `tools/test_ui_step_accel.py` | Chạm ±1, giữ tăng bậc, giới hạn lệnh và vạch máy |
| `tools/test_ui_compat_roast.py` | Luồng chế độ tương thích |
| `tools/test_ui_overview_history.py` | Tổng quan, lịch sử, giới thiệu |
| `tools/test_ui_dialog_layout.py` | Hình học 10 hộp thoại, vị trí thông báo lệnh |
| `tools/test_ui_consistency.py` | 6 tab, 7 trang cài đặt, sáng/tối, dữ liệu mất kết nối |

Kiểm bổ sung nút làm nguội bằng cầu giả: bật rồi tắt phát đúng `cool=1`, `cool=0`; lệnh bị từ chối giữ nút tắt và thông báo trạng thái failed. Đây chỉ là hợp đồng UI/lệnh, chưa kiểm quạt hoặc thời gian làm nguội thực tế.

Luna báo kiểm bổ sung bố cục ở 1280×720 và 1366×768 không thấy tràn/đè. Kết quả đạt của bộ kiểm cũ không phủ định các lỗi trên: chúng thiếu các ca từ chối/queued lâu/mất kết nối ở ranh giới thời gian, đổi hồ sơ khi đã gài tự nạp, điều kiện sẵn sàng mâu thuẫn, tải chi tiết sai thứ tự và lưu các ô hậu mẻ độc lập. Một số bộ kiểm gọi hàm/ép trạng thái trực tiếp; không được coi là đã kiểm toàn bộ hành trình thao tác trên EXE thật.

Không build firmware vì không sửa firmware. Không tuyên bố xác nhận khả năng điều khiển gas, cơ cấu xả hay làm nguội trên phần cứng; việc này cần dữ liệu/kiểm thử phần cứng sau bản sửa.
