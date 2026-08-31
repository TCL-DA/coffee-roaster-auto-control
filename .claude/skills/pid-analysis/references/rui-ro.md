# Rủi ro & lỗi đã phát hiện — PID_Airflow

Rà code ngày 2026-07-30. **R1, R2, R3, R5 ĐÃ SỬA ngày 2026-07-30; R4 theo dõi; R6 còn lại (cố ý
tách riêng). Firmware build OK, CHƯA NẠP MÁY THẬT.** Mỗi mục ghi triệu chứng để đối chiếu với hiện
tượng máy thật, chứ không chỉ nhận xét code.

Trạng thái: 🔴 chưa quyết · 🟡 đã chốt phương án, chưa code · 🟢 đã code

---

## R1 · Chú thích lệch code — deadband 🟢 ĐÃ SỬA 2026-07-30

Ba chỗ trong file ghi **±5 Pa** nhưng hằng số là **3,0**:
- header dòng 6-8: *"Vacuum thấp hơn SP > 5Pa: tăng airflow 1%"*
- ngay dòng khai báo 49: `const float AIR_DEADBAND = 3.0f;   // ±5 Pa`

Nguy hiểm vì đây đúng loại chú thích người ta tin mà không kiểm: thợ đọc "5 Pa" rồi kết luận sai về
độ chính xác đạt được, hoặc chỉnh setpoint theo giả định lệch.

Header còn ghi *"Tự học và cập nhật FF table khi ổn định 10s"* — cái này **đúng**, giữ nguyên.

## R2 · `ffFind` chấp nhận rộng hơn `FF_SP_MATCH` 🟢 ĐÃ SỬA 2026-07-30

```cpp
float bestDist = FF_SP_MATCH + 1.0f;          // = 4.0
for (...) if (d < bestDist) { bestDist = d; best = i; }
```

Biến `bestDist` vừa làm **ngưỡng chấp nhận** vừa làm **giá trị nhỏ nhất đang giữ**. Khởi tạo
`FF_SP_MATCH + 1` nên entry cách tới **3,999 Pa** vẫn được nhận, dù tài liệu và tên hằng số nói
"≤ 3 Pa → cùng entry".

Hệ quả: hai setpoint cách nhau 3,5 Pa bị gộp làm một entry, mức gió của chúng bị trung bình với nhau.
Ảnh hưởng nhỏ nhưng làm bảng FF mờ hơn dự tính, và làm sai phép tính "coverage" (50 entry × 3 Pa).

Sửa đúng: `float bestDist = FF_SP_MATCH;` rồi so `d <= bestDist`, hoặc tách riêng biến ngưỡng và
biến khoảng-nhỏ-nhất.

## R3 · Factory tune quét 101 bước nhưng bảng chỉ chứa 50 entry 🟢 ĐÃ SỬA 2026-07-30 (bảng 60 + bước 2 = 51 bước; thêm báo mã khi đầy)

`FT_AIR_START=0 → FT_AIR_END=100` bước 1 → **101 bước**, mà `FF_MAX_ENTRIES = 50`.

`ffLearn` khi bảng đầy thì **lặng lẽ bỏ qua**:

```cpp
if (i < 0) {
    if (ffMapSize < FF_MAX_ENTRIES) { ffMap[ffMapSize++] = {sp, air, 1}; ffDirty = true; ... }
    return;                       // ← đầy thì return, KHÔNG báo gì
}
```

**Triệu chứng máy thật:** chạy factory tune 5 phút, báo xong 100 %, nhưng bảng FF **chỉ có dữ liệu
vùng gió thấp**; tới vùng gió cao thì `ffLookup` rơi về ước lượng tuyến tính `sp × 100/120` → snap sai
→ đổi sang setpoint cao là gió nhảy lệch rồi phải bò rất lâu.

Có một cơ chế giảm nhẹ: các bước gió liền nhau thường cho Pa cách nhau < 4 Pa nên bị **gộp** vào cùng
entry thay vì thêm mới, nên bảng không nhất thiết đầy sau 50 bước. Nhưng đó là may, không phải thiết kế
— máy nào có dải áp rộng (quạt mạnh, lưới thoáng) thì 50 entry đầy trước khi quét xong.

**Đề xuất** (cần chủ máy chốt): nâng `FF_MAX_ENTRIES` lên ≥ 110 — tốn thêm `60 × 12 byte ≈ 720 B` RAM
tĩnh, phải kiểm ngưỡng RAM (`[[reference_ram_threshold]]`, nguy hiểm khi > 88 %); **hoặc** tăng
`FT_AIR_STEP` lên 2 (51 bước, tune còn ~2 phút 40); **hoặc** ít nhất báo lỗi ra HMI khi bảng đầy giữa
lúc tune, thay vì báo xong 100 % như không có gì.

## R4 · Buffer stack ~1,2 KB trong hai hàm SD 🟡 THEO DÕI — bảng 60 entry → ~1,5 KB; RAM tĩnh sau build 81,4%

```cpp
char buf[FF_MAX_ENTRIES * 24 + 32];   // _ffSaveNow: 1232 byte
char buf[FF_MAX_ENTRIES * 24 + 4];    // _ffLoadNow: 1204 byte
```

Trên STM32F103RC (48 KB RAM) thì 1,2 KB stack trong một hàm là đáng kể, nhất là khi hàm được gọi từ
`loop()` cùng lúc thư viện SD cũng đang dùng stack riêng. Hiện chưa thấy tràn, nhưng **nếu nâng
`FF_MAX_ENTRIES` theo R3 thì buffer phình theo** — 110 entry → ~2,7 KB. Hai việc đó phải xét cùng nhau.

Cách tránh: ghi/đọc theo từng dòng thay vì dựng cả file trong RAM. Đổi lại là nhiều lần gọi thư viện SD
hơn, chậm hơn — nên chỉ làm nếu R3 được chốt theo hướng nâng trần.

## R5 · `tunePercent` dùng chung với tiến trình sấy lồng 🟢 ĐÃ SỬA 2026-07-30 (trọng tài ở programScan)

`tunePercent` là ô tiến trình đẩy lên HMI. Factory tune ghi vào nó (`PID_Airflow.h:298, 372, 382`),
mà **sấy lồng cũng ghi** (`Preheat.h` 6 chỗ, `Preheat_PID.h` 2 chỗ).

Hiện tại chưa chắc xung đột vì `preheat()` chỉ chạy khi `START_BTN_R == 0`, còn factory tune bấm từ HMI
— nhưng **không có gì chặn hai cái cùng chạy**. Nếu trùng, thanh tiến trình trên HMI nhảy qua nhảy lại
giữa hai nguồn, thợ không biết đang xem cái nào.

**Đề xuất:** chặn cứng — `pidFactoryTuneStart()` từ chối nếu đang sấy lồng, và `preheat()` từ chối nếu
`ftState != FT_IDLE`. Rẻ và dứt điểm.

## R6 · Chú thích tiếng Việt bị lỗi encoding 🔴 CHƯA — cố ý để riêng, xem ghi chú cuối mục

Toàn bộ chú thích trong `PID_Airflow.h` đang là **UTF-8 bị đọc theo cp1252 rồi lưu lại** (double
encoding): `â€”` thay cho `—`, `Â±` thay cho `±`, `Ä‘` thay cho `đ`. Dòng cuối file thậm chí thành
`#endif // PID_AIRFLOW_H♥`.

Không ảnh hưởng biên dịch (chỉ là chú thích) nhưng làm file khó đọc và khiến mọi lần sửa nội dung tiếng
Việt trong đó sinh diff khổng lồ.

**Cách xử lý:** sửa encoding **thành một commit riêng, không lẫn thay đổi logic** — nếu không thì thay
đổi thật bị chôn trong biển diff. Theo skill `vietnamese-comments`. Cùng bệnh với
`Modbus_Master.h:385, 628-629` (đã thấy `thay Ä‘á»•i`, `báº¥m Báº¬T`) nên có thể làm một lượt.

---

## Cách dùng file này

Chủ máy đọc, chốt từng mục (đổi 🔴 → 🟡 kèm quyết định) rồi mới code. R3 và R5 đã làm (hai mục nguy hiểm nhất). Còn **R6** — sửa encoding cả file, cố ý
chưa làm để không chôn thay đổi logic vào biển diff; nên làm thành commit riêng, cùng lượt với
`Modbus_Master.h`.
