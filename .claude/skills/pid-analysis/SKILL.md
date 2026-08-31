---
name: pid-analysis
description: Bộ điều khiển AIRFLOW theo áp hút (vacuum) của máy rang OTL — module include/PID_Airflow.h. Gồm 3 lớp chạy chồng nhau: step controller có cooldown động, bảng feed-forward tự học lưu SD (/pid_ff.txt), và factory auto-tune quét 0→100%. Skill giữ kiến trúc, bảng hằng số thật, quy trình chẩn đoán và danh sách rủi ro đã phát hiện. Dùng bất cứ khi nào nói tới "PID airflow", "PID_Airflow.h", "áp hút", "vacuum", "Diff_Air", "gió không ổn định", "airflow dao động", "quạt hút giật", "bảng FF", "pid_ff.txt", "factory tune", "auto tune gió", "snap buffer", "deadband gió", "vacuumSetpoint", "tunePercent", hay khi cần chỉnh/đọc/gỡ lỗi bất kỳ thứ gì liên quan tới điều khiển gió theo áp hút — kể cả khi không nhắc chữ "PID".
allowed-tools: Read, Grep, Bash
---

Module `include/PID_Airflow.h` (538 dòng) điều khiển **% gió theo áp hút đo được**, không phải theo
nhiệt độ. Tên có chữ "PID" nhưng **không có Kp/Ki/Kd** — chính hàm `pidShowHMI()` để trống và ghi rõ
*"step controller — không có Kp/Ki/Kd"*. Đây là **step controller + feed-forward tự học**, cách gọi
khác hẳn PID cổ điển; đừng đi tìm hệ số PID trong đó.

## Ba lớp chạy chồng nhau

Hiểu sai lớp nào đang lái là chẩn đoán sai toàn bộ:

```
① STEP CONTROLLER    pidAirflowUpdate()   mỗi loop, từ analogIn()
   lệch quá deadband → nhích 1 %, rồi NGHỈ theo cooldown động

② BẢNG FEED-FORWARD  ffLookup / ffLearn   nhớ "áp này thì bao nhiêu % gió"
   đổi setpoint nhiều → nhảy thẳng tới mức đã học; ổn định 10 s → học lại

③ FACTORY AUTO-TUNE  _ftTick()            quét 0→100 %, dựng lại cả bảng
   đang chạy thì ① NGƯNG hoàn toàn (pidAirflowUpdate return ngay)
```

**Quyền ưu tiên:** `ftState != FT_IDLE` là lớp ③ giữ trọn quyền, lớp ① không chạm airflow. Lớp ②
học trong lúc ① đang lái, và bị **xoá sạch** khi ③ bắt đầu quét (`ffMapSize = 0`).

## Tài nguyên

| File | Nội dung | Khi nào đọc |
|------|----------|-------------|
| [references/kien-truc.md](references/kien-truc.md) | 3 lớp chi tiết, máy trạng thái `ftState`, luồng snap khi đổi setpoint, 8 điểm nối vào firmware | Cần hiểu module hoạt động thế nào |
| [references/tham-so.md](references/tham-so.md) | Bảng hằng số THẬT kèm dòng code, ý nghĩa, và hệ quả khi đổi từng cái | Chỉnh tham số, tính thời gian hội tụ |
| [references/rui-ro.md](references/rui-ro.md) | 6 rủi ro/lỗi đã phát hiện khi rà code — **việc còn mở** | Gió dao động, bảng FF thiếu, trước khi sửa |

## Quy trình chẩn đoán khi gió không ổn định

Theo thứ tự này, vì lớp dưới sai thì lớp trên chỉnh mấy cũng vô nghĩa:

1. **Xác định lớp nào đang lái.** `ftState` có phải `FT_IDLE`? `vacuumSetFlag_R` có bằng 1? Không
   bật cờ đó thì cả module nằm im và gió do biến trở/PC/SD quyết định — không phải lỗi PID.
2. **Đọc bảng FF thật** trên thẻ: `/pid_ff.txt`. Dòng đầu là `SNAPBUF:` rồi tới các dòng
   `Pa,Air%,count`. Bảng rỗng hoặc lệch xa thực tế thì snap sai chiều, gió lồng lên rồi tụt.
3. **Đối chiếu deadband với nhiễu cảm biến.** `AIR_DEADBAND` phải lớn hơn nhiễu còn lại sau Kalman,
   không thì controller đuổi theo nhiễu và nhích qua nhích lại mãi.
4. **Tính tốc độ nhích thật** từ cooldown động (xem [tham-so.md](references/tham-so.md)) — đây là chỗ
   hay bị hiểu sai nhất: **1 % mỗi 1,5–3 giây**, không phải 1 % mỗi loop.
5. **Soát các rủi ro đã biết** trong [rui-ro.md](references/rui-ro.md) trước khi kết luận là tuning sai.

## Ba điều dễ hiểu sai nhất

- **"1 %/loop" là SAI.** Có `stepCooldownMs`: mỗi bước 1 % xong thì nghỉ **3000 ms** khi gần setpoint,
  **1500 ms** khi lệch ≥ 30 Pa, nội suy tuyến tính ở giữa. Vòng loop ~130 ms nhưng phần lớn các vòng
  đó không nhích gì. Nghĩa là **tốc độ tối đa ~0,67 %/giây** — đi 30 % mất khoảng 45 giây.
- **Chú thích trong file đã lệch code.** Header và dòng khai báo ghi `±5 Pa` nhưng
  `AIR_DEADBAND = 3.0f`. Tin code, đừng tin chú thích — xem [rui-ro.md](references/rui-ro.md) R1.
- **Snap chỉ chạy khi setpoint đổi > 30 Pa.** Đổi nhẹ hơn thì cố ý **không** snap, để step controller
  bò tới từ từ. Nên "đổi setpoint mà gió không nhảy" là đúng thiết kế, không phải lỗi.

## Trước khi sửa file này

- File đang có **chú thích bị lỗi encoding** (UTF-8 bị đọc theo cp1252 rồi lưu lại). Sửa nội dung
  tiếng Việt trong đó thì theo skill `vietnamese-comments`, và đừng "sửa nhân tiện" cả file trong cùng
  một lần vá — dễ lẫn thay đổi thật vào một biển diff encoding.
- `pidSelfTuneTick()` được gọi từ **ngoài ISR** (`pidSelfTuneTask()` trong `loop()`), ISR chỉ set cờ
  `selfTuneTickEn`. Giữ đúng kiểu đó: không Modbus/SD/`delay()` trong ISR — xem `[[feedback_isr_no_modbus]]`.
- Ghi SD đi qua `sdPendingCmd` + `pidSDTask()` cũng vì lý do trên. Đừng gọi `_ffSaveNow()` trực tiếp.
- Build kiểm RAM bằng skill `flash-build`: hai hàm SD dùng buffer stack ~1,2 KB mỗi hàm, mà
  STM32F103RC chỉ có 48 KB — xem `[[reference_ram_threshold]]`.
