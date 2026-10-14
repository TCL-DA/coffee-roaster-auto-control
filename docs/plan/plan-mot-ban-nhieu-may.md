# Kế hoạch: một firmware + một giao diện HMI cho mọi biến thể máy rang

Rev 4 · 13/10/2026 · trạng thái: **đã chốt 13 câu ở §9, chờ duyệt để bắt đầu R0** (chưa sửa code, chưa nạp thiết bị)

## 1. Mục tiêu và phạm vi

Một bản firmware và một nguồn HMI dùng chung cho mọi máy. Thợ lắp đặt chọn cấu hình máy trên một màn ẩn
(phải đăng nhập Master) lúc giao máy. Không phải dựng firmware riêng cho từng khách.

| Tuỳ chọn | Có | Không |
|---|---|---|
| VR (biến trở vật lý) — **3 mức** | **VR 2**: núm vặn gas + gió · **VR 3**: núm vặn gas + gió + trống. Nút +/− trên HMI vẫn giữ làm đường dự phòng (chuyển nguồn sang HMI) | chỉnh bằng nút +/− trên HMI |
| Vacuum (cảm biến áp hút + PID gió) | hiện áp hút, cài PID | ẩn hết |
| Loader (nạp liệu tự động) | màn và nút loader; **không cân thì nạp theo thời gian** | ẩn |
| Cân | hiện khối lượng; có loader thì nạp theo cân | ẩn |
| Module relay ngoài (Modbus ID 7) | relay qua module RS485 | relay trên board (GPIO) |
| Panel | DOP-110WS (có cổng mạng: web, VNC, Modbus TCP) | DOP-110CS (không cổng mạng) |
| **Cỡ máy** | 6 · 12 · 15 · 30 kg — chọn cỡ thì nạp bộ tham số mặc định của cỡ đó, thợ tinh chỉnh bằng `$M` | — |
| Đốt khói (afterburner) | chạy máy trạng thái `abStep`, hiện trên HMI | bỏ qua, ẩn |
| Tách đá (destoner) | chạy bước tách đá sau làm nguội | bỏ qua, ẩn |
| Khuấy / quạt khay nguội | hai relay riêng, hai nút riêng | chung một relay, một nút |
| Loại đầu đốt (chỉ gas) | thường hoặc premix — ô 29 có sẵn, chuyển vào màn Cấu hình máy | — |

Loader và cân **độc lập**: cả 4 kiểu ghép đều hợp lệ. Tổng cộng 3 (VR) × 2⁷ = **384 cấu hình** × 2 loại đầu đốt
× 4 cỡ × 2 model panel, từ **1 nguồn firmware + 1 nguồn .dpa**. Nguồn nhiệt chỉ có gas.

**App Roast Lab và web** cũng theo cấu hình: board gửi `MC_OPT` qua PC_Link, app / web tự ẩn phần máy không có. Làm cùng R0.

**Phần cứng cố định ở mọi máy** (không phải tuỳ chọn): board V400 (⇒ một file firmware duy nhất); gió điều khiển bằng
0–10 V; trống điều khiển bằng biến tần RS485 (ID 4); đồng hồ nhiệt BT/ET RS485 (ID 1, 2). Biến tần gió chỉ nối RS485
(ID 5) ở máy có vacuum, để đọc cảm biến áp hút qua ngõ ACI.

Ngoài phạm vi: board V300/V350, mạch an toàn gas.

## 2. Hiện trạng (đo ngày 13/10/2026)

| Phần | Hiện trạng | Hệ quả |
|---|---|---|
| Firmware | Công tắc **lúc dựng** trong `include/Config.h:55-64` (`MACHINE_HAS_VACUUM_SENSOR`, `_SCALE_FEEDER`, `_AIR_INVERTER`, `_IO_RELAY_MODULE`…) và `MACHINE_VR_SOURCE_FROM_HMI` | Mỗi kiểu máy một bản dựng |
| Firmware | Đã có tiền lệ chọn **lúc chạy**: loại đầu đốt (ô 29), `$M33` bật auto-loader, `$M47` bật PID vacuum | Cách làm đã chạy thật, mở rộng được |
| HMI | v28 bản LO83 cho máy 30 kg không VR, 110WS. Z52 đã ẩn địa chỉ web khi panel không có mạng | Có sẵn cơ chế ẩn theo bit |
| HMI | 110CS và 110WS cùng 1024×600. Đổi model = sửa 2 chỗ trong file (`ModelName` + chuỗi model) | Sinh 2 bản bằng script, bố cục không xê dịch |
| Panel thật | Không đọc coil `{Link2}B` cho ẩn / hiện / khoá | Phải dùng ô `$` nội bộ |

## 3. Cơ sở chuẩn

- Chỉ thị Máy 2006/42/EC Phụ lục I §1.2.2 (cơ cấu điều khiển rõ ràng, không gây nhầm), §1.7.4 (sổ tay ghi cấu hình).
  Từ 20/01/2027 thay bằng Quy định (EU) 2023/1230.
- EN ISO 13849-1, EN 746-2: đổi cấu hình **không được** làm yếu chức năng an toàn. Chốt mồi hụt 75 s, giám sát lửa,
  watchdog vẫn chạy y nguyên ở mọi tổ hợp.
- EN ISO 9241-110 (phù hợp nhiệm vụ, tự mô tả): không hiện điều khiển máy không có. VDI/VDE 3850 Blatt 3 (màn cảm ứng).
- EN 60204-1 §10 + EN 60073: màu nút và đèn giữ nguyên ở mọi biến thể.
- IEC 62443-4-2 / CRA: chỉ Master đổi được cấu hình, mọi lần đổi đều ghi nhật ký.

## 4. Thiết kế

### 4.1 Ô cấu hình máy `MC_OPT` (một word, bitmask)

| Bit | Ý nghĩa |
|---|---|
| 0 | VR gas + gió |
| 1 | VR trống (chỉ hợp lệ khi bit 0 = 1 ⇒ VR 3) |
| 2 | Có vacuum |
| 3 | Có loader |
| 4 | Có cân |
| 5 | Có module relay ngoài (ID 7) |
| 6–8 | Cỡ máy: 0 = 6 kg · 1 = 12 kg · 2 = 15 kg · 3 = 30 kg (còn chỗ cho cỡ mới) |
| 9 | Có đốt khói (afterburner) |
| 10 | Có tách đá (destoner) |
| 11 | Khuấy và quạt khay nguội chạy relay riêng (0 = chung một relay) |
| 12–14 | Để dành |
| 15 | Đã cấu hình (0 = máy chưa cấu hình) |

- Lưu trong khối `$M` của HMI (panel nhớ qua tắt/bật), board đọc qua bắt tay `$M` sẵn có. Thêm 1 ô ⇒ firmware
  và HMI phải **nạp thành cặp**, như đợt `$M54–61`.
- `bit15 = 0` (máy mới xuất xưởng, hoặc máy đã giao vừa lên bản mới): **chặn rang**. Board không bật gas, không nhận
  Start; HMI mở thẳng màn Cấu hình máy. Thợ không thể quên cấu hình. ⚠ Lên bản mới cho máy đã giao thì thợ phải cấu hình
  ngay tại chỗ — ghi rõ trong hướng dẫn nạp.
- Chọn cỡ máy ⇒ board nạp bộ tham số mặc định của cỡ đó (preheat, PID, nạp liệu, nhiệt xả…) vào khối `$M`, **chỉ khi
  thợ bấm "Nạp mặc định cỡ máy"** — đổi tuỳ chọn khác không được ghi đè tham số thợ đã tinh chỉnh.
  Bộ mặc định lấy từ cấu hình các máy đã giao (`docs/config/`), đối chiếu từng số trước khi dùng.
- Tổ hợp vô lý thì board **từ chối** và báo mã cảnh báo, không chạy nửa vời. Ví dụ: bit 1 (VR trống) bật mà bit 0 tắt.
- Loader không cân: hút hết **số giây cài** trên màn loader thì dừng. Loader có cân: nạp theo khối lượng như hiện nay.

### 4.2 Firmware

- Dựng **đủ mọi tính năng** trong một bản. `MACHINE_HAS_*` trong `Config.h` thành "trần phần cứng".
  Thêm hàm `mcHas(OPT_x)` đọc `MC_OPT` lúc chạy.
- Tuỳ chọn tắt ⇒ **không hỏi** thiết bị đó trên RS485. Như vậy không sinh lỗi mất kết nối giả, và vòng lặp nhanh hơn.
- VR 2: gas + gió đọc chân analog, trống lấy từ HMI. VR 3: cả ba đọc chân analog. Không VR: cả ba lấy từ HMI như hiện nay.
  Mọi mức VR đều chuyển được nguồn sang HMI (nút +/−) làm đường dự phòng khi núm hỏng.
- Relay: bit 5 bật thì lệnh relay đi qua module ID 7, tắt thì đi GPIO trên board.
- Mạch an toàn gas **không phụ thuộc** `MC_OPT`.
- Đo Flash / RAM sau dựng: RAM phải dưới 88 %.

### 4.3 HMI (một nguồn .dpa)

- Macro chép `MC_OPT` sang các bit `$` nội bộ (vùng trống ghi ở sổ lỗi tuần, mục P). Từng phần tử ẩn / hiện **và khoá** theo bit.
  Chỉ ẩn thì vẫn bấm được qua nút tắt hoặc chuyển màn.
- Phần theo tuỳ chọn:
  - VR: ô nào đang theo núm vặn thì hiện số núm kèm nhãn "Núm vặn" và làm mờ +/−; bấm "Điều khiển trên HMI" thì +/− dùng lại.
    VR 2 chỉ áp cho gas và gió, ô trống vẫn dùng +/−.
  - Vacuum: số áp hút, cài PID, đồ thị.
  - Loader: nút, màn, cảnh báo.
  - Cân: số cân, nạp theo cân.
  - Panel không mạng: ẩn web / VNC (đã có Z52).
- **Màn Cấu hình máy** (Master, máy phải đứng yên): 4 ô gạt + bảng tóm tắt. Lưu bằng giữ 1 s; đổi xong board khởi động lại phần ngoại vi.
- Cấu hình đang dùng hiện ở màn Cài đặt (chỉ đọc) để thợ vận hành và thợ bảo trì thấy máy đang chạy kiểu nào.

### 4.4 Dựng hai model panel

Script lấy 1 nguồn .dpa ⇒ bản 110WS và bản 110CS (sửa 2 chỗ model) ⇒ biên dịch cả hai bằng `dpa_build`
⇒ hai thư mục nạp có tên model rõ ràng. Không sửa tay bản 110CS.

## 5. Yêu cầu và cách kiểm

| Mã | Yêu cầu | Tiêu chí đạt | Cách kiểm |
|---|---|---|---|
| Y-01 | 1 firmware chạy được mọi tổ hợp `MC_OPT` | 48 cấu hình khởi động, rang hết mẻ AUTO | Board ảo: 48 cấu hình × bài khởi động + mẻ AUTO; bộ 9 bài đủ cho 8 cấu hình phủ từng cặp tuỳ chọn |
| Y-02 | Tuỳ chọn tắt thì không hỏi thiết bị | 0 lượt Modbus tới slave bị tắt | Đếm gói trên bus |
| Y-03 | Không lỗi mất kết nối giả | 0 cảnh báo thiết bị khi tuỳ chọn tắt | Chạy 30 phút / tổ hợp |
| Y-04 | An toàn gas không đổi | Chốt 75 s → 414 + huỷ mẻ ở mọi tổ hợp | Bàn thử thật, 4 tổ hợp đại diện |
| Y-05 | HMI không lộ điều khiển máy không có | 0 phần tử nhìn thấy hoặc bấm được ngoài cấu hình | Soi điểm ảnh + bấm thử mọi nút |
| Y-06 | Chỉ Master đổi cấu hình, có nhật ký | Thợ không vào được; mỗi lần đổi ghi 1 dòng | Thử 2 tài khoản |
| Y-07 | Máy cũ lên bản mới giữ hành vi | `bit15 = 0` ⇒ như bản trước | So log trước / sau |
| Y-08 | Tổ hợp vô lý bị từ chối | Mã cảnh báo rõ, không chạy | Ghi từng tổ hợp vô lý |
| Y-09 | Hai model panel từ một nguồn | 110CS mở được trong DIAScreen, biên dịch đạt, bố cục khớp từng điểm ảnh | `dpa_build` × 2 + so ảnh |
| Y-10 | Tài nguyên board | RAM < 88 %, Flash < 90 % | `memory-check` |

## 6. Gói phát hành (mỗi gói tự bán được)

| Gói | Tên thương mại | Nội dung | Dựa trên |
|---|---|---|---|
| **R0** | Một bản cho mọi máy 110WS | `MC_OPT` trong firmware + màn Cấu hình máy + ẩn / hiện mọi tuỳ chọn trên 110WS, app và web; cỡ 30 kg. **Máy đầu tiên: máy 30 kg đang làm** — chưa đạt nghiệm thu R0 trước ngày giao thì giao LO84 | LO84 |
| **R0.1** | Thêm cỡ 6 / 12 / 15 kg | Bảng mặc định theo cỡ (chủ máy duyệt từng số) + nút "Nạp mặc định cỡ máy" | R0 |
| **R1** | Bản panel kinh tế 110CS | Script sinh bản 110CS, ẩn mạng, thử trên panel 110CS thật | R0 |
| **R2** | Tự nhận thiết bị | Board dò RS485 lúc khởi động, gợi ý cấu hình, cảnh báo khi lệch (có thiết bị mà đang tắt, hoặc ngược lại) | R0 |

Dừng ở R0 vẫn giao được mọi máy dùng 110WS. Rủi ro còn lại khi dừng ở R0: máy 110CS vẫn phải dùng bản HMI riêng như hiện nay.

## 7. Kiểm thử và nghiệm thu

1. Mô phỏng: panel ảo + board ảo, 48 cấu hình chạy bài khởi động + mẻ AUTO; 8 cấu hình phủ từng cặp tuỳ chọn chạy đủ 9 bài;
   soi điểm ảnh 5 trạng thái mỗi cấu hình.
2. Bàn thử thật (HMI + board, không tải), 5 cấu hình đại diện: tất cả tắt · tất cả bật (VR 3) · VR 2 · loader không cân ·
   loader + cân + relay ngoài.
   Mỗi tổ hợp rang 1 mẻ AUTO + 1 mẻ thường.
3. Biên bản nghiệm thu từng gói, kèm số phiên bản firmware / HMI và ghi chú phát hành.

## 8. Rủi ro (FMEA rút gọn)

| Rủi ro | Hậu quả | Biện pháp |
|---|---|---|
| Chọn sai cỡ máy ⇒ nạp tham số cỡ khác | Preheat / PID sai, mồi lửa lệch | Nạp mặc định cỡ phải giữ 1 s + hiện cỡ và các số chính trước khi ghi; biên bản giao máy ghi cỡ |
| Bộ mặc định theo cỡ lấy sai số từ máy cũ | Máy mới chạy sai ngay từ đầu | Đối chiếu từng số với `docs/config/` + hồ sơ máy đã giao; chủ máy duyệt bảng trước khi đưa vào firmware |
| Máy đã giao lên bản mới bị chặn rang | Khách dừng máy | Chỉ nạp khi có thợ tại chỗ; hướng dẫn nạp có bước cấu hình |
| Thợ chọn sai cấu hình lúc giao máy | Máy có vacuum mà tắt PID ⇒ hút sai | R2 cảnh báo lệch; cấu hình hiện ở màn Cài đặt; biên bản giao máy ghi cấu hình |
| Firmware và HMI lệch số `$M` | Đọc nhầm ô | Nạp thành cặp; board kiểm phiên bản HMI lúc bắt tay |
| RAM vượt khi gộp mọi tính năng | Treo board | Đo sau mỗi bước; tính năng nặng giữ cờ lúc dựng |
| Ẩn mà không khoá | Bấm trúng lệnh thiết bị không có | Y-05 kiểm cả bấm, không chỉ nhìn |
| Đổi cấu hình giữa mẻ | Mất điều khiển | Chỉ đổi khi máy đứng yên |

## 9. Đã chốt với chủ máy (13/10/2026)

1. **VR có 2 bản:** VR 2 = núm vặn gas + gió; VR 3 = gas + gió + trống. Giữ nút +/− trên HMI làm đường dự phòng.
2. **Loader không cân** nạp theo thời gian; loader và cân là hai tuỳ chọn độc lập.
3. **Module relay ngoài (ID 7)** là tuỳ chọn thứ 5.
4. Xưởng **có panel 110CS** để thử R1.
5. Thứ tự **R0 → R1 → R2**.

6. **Máy chưa cấu hình: chặn rang**, bắt cấu hình.
7. **Loader không cân** dừng khi hết số giây cài.
8. **Gió luôn 0–10 V; trống luôn RS485.** Máy có vacuum đọc áp hút qua ACI của biến tần gió (RS485, ID 5) như hiện nay.
   BT/ET luôn RS485. Board chỉ V400.
9. **Mọi cỡ 6 / 12 / 15 / 30 kg:** chọn cỡ trên màn Cấu hình máy, nạp bộ mặc định của cỡ, thợ tinh chỉnh bằng `$M`.

10. **Thêm 3 tuỳ chọn:** đốt khói, tách đá, khuấy / quạt khay nguội riêng.
11. **Nguồn nhiệt chỉ gas** (thường / premix); loại đầu đốt chuyển vào màn Cấu hình máy.
12. **App và web tự ẩn theo cấu hình**, làm cùng R0.
13. **Máy đầu tiên dùng bản chung: máy 30 kg đang làm.**

Còn chờ: chủ máy duyệt Rev 4 để bắt đầu R0.

## 10. Tiến độ

**13/10/2026 — R0 bước 1 (firmware) xong trên mô phỏng, CHƯA nạp board, CHƯA commit:**

- `include/MachineOpt.h` (dữ liệu + hàm hỏi `optXxx()`, chốt `$M62` khi máy đứng yên),
  `include/MachineOptService.h` (chặn rang khi chưa cấu hình, mã 422 / 423, xoá đếm lỗi thiết bị đã bỏ).
- Khung `rwMemHMI` 61 → 62 ô; `$M62` thêm vào `protocol/pc_link.json` (chỉ đọc, min > max) và sinh lại 3 phía.
- Đổi sang chọn lúc chạy: VR (gas + gió / trống) · vacuum · loader (không cân ⇒ hết `feederSet_R` giây là nạp xong) ·
  cân · relay ngoài · đốt khói · tách đá · khuấy relay riêng (cần relay ngoài). Bỏ `MACHINE_VR_SOURCE_FROM_HMI`.
- Relay gas chặn cứng ở `controlIO()` khi chưa cấu hình.
- Dựng: RAM 73,2 % (35 980 / 49 152 B), Flash 43,0 % (112 596 / 262 144 B).
- Kiểm: `tools/fw_sim/test_mc_opt.py` trên trọn hệ (HMIApp LO80 + board ảo firmware thật) **16/16 mục đạt**
  (C1 chưa cấu hình · C2 30 kg trơn không hỏi ID 5 / 7 · C3 đủ bộ có hỏi · C4 vô lý ⇒ 423 giữ cũ · C5 đổi khi có lửa ⇒ chờ).
  `test_stt_queue` đạt, `test_otl_link` đạt, bản đồ PC_Link 3 phía khớp.

⛔ **Không nạp bản firmware này lên board khi HMI chưa có ô `$M62`**: panel cũ đọc `$M62` = 0 ⇒ máy bị chặn rang.

Còn lại của R0: màn Cấu hình máy + ẩn / hiện trên HMI (nối `vrUseHmi`), app / web đọc `$M62`, thử bàn thật 5 cấu hình.

**13/10/2026 — R0 bước 2 (HMI) + bước 3 (app / web) xong trên mô phỏng, CHƯA nạp, CHƯA commit:**

- Firmware thêm `$M63` (núm hỏng → điều khiển trên HMI, áp ngay cả giữa mẻ); khung `rwMemHMI` 63 ô (bộ đệm 64).
  RAM 73,2 %, Flash 43,0 %. `test_mc_opt` 16/16.
- HMI bước Z55 `113_HMI\…\_script\ui_cau_hinh.py` (gắn vào `ui_zoom.py` sau Z54): màn 36 "Cấu hình máy" (9 thẻ, bản nháp
  `$450..$458`, nút Lưu hỏi lại, Lua kiểm rồi ghi `$M62`), ô "Cấu hình" màn 9 (ẩn với công nhân), khoá theo cấu hình 29 công tắc
  + 9 nút ± (khoá gộp `$464..$466`), dải "Máy chưa cấu hình" màn 2, cảnh báo 422 / 423, công tắc I/O vẽ lại V7 (19 cái, sửa
  tương phản 2,74 → ≥ 3 : 1 có sẵn từ trước).
- Bản dựng đầy đủ từ nguồn: `R0-1013-ZOOM85.dpa` (phát hành) + `nap\T-R0-1013-LO85.dpa` (bàn thử).
  Kiểm trên LO85: `thu_cau_hinh_emu` 19/19 (trọn hệ, board ảo firmware thật) · `soi_cau_hinh_emu` 10/10 (điểm ảnh, VI + EN) ·
  bộ 9 bài hồi quy 159/159 mục.
- App: thiết bị + thẻ áp hút theo `$M62`; `test_ui_mc_opt` 8/8 + 4 bài UI cũ đạt. Web LAN dùng chung HTML.

Còn lại của R0: nạp firmware + LO85 THÀNH CẶP lên bàn thử, thử 5 cấu hình (mục 7), build EXE app, commit.
