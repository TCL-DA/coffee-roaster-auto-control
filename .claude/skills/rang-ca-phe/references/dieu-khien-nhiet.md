# Điều khiển nhiệt rang — giáo trình của OTL Hồng (Pink)

Rút từ lần tự lái máy rang ĐIỆN VX4 ngày 14/10/2026: chủ máy cho toàn quyền nhiệt / gió / trống 60 phút, lồng trống, mục tiêu giữ BT 200 °C.
Số liệu là đo THẬT; mỗi lần lái phải bổ sung thêm số mới vào cuối file.

## 1. Mô hình nhiệt máy điện (chuỗi trễ)

```
'Nhiệt %' ──(firmware)──> SV đồng hồ VX4 = 130 + 2,2 × Nhiệt% (°C) ──(PID VX4, điện trở)──> nhiệt BUỒNG
   ──(gió mang nhiệt, trễ)──> ET (khí) ──(truyền vào hạt / thành lồng)──> BT (hạt)
```

- Mỗi khâu là một bậc trễ. Đổi Nhiệt % thì BT phản ứng **chậm vài chục giây tới hơn 1 phút**. Vì vậy phải điều khiển theo **BT DỰ BÁO** (BT + RoR × τ), không theo BT hiện tại.
- VX4 bám SV tốt: Nhiệt 50 % ⇒ SV 240 °C, đo được nhiệt buồng 239,9 °C.
- **Gió là "máy hút nhiệt"**: gió 85 % khi tắt nhiệt làm BT nguội ~40 °C/phút (187 → 108 °C trong ~2 phút). Gió cao cần Nhiệt % cao hơn để giữ cùng một BT.
- **Mở cửa nạp** khi lồng đang nóng: BT −5 °C, ET −11 °C trong ~10 s (khí lạnh lọt vào). Lúc charge thật còn có thêm hạt nguội — đó là điểm TP.

## 1b. ⭐ Mô hình ĐÚNG — đo được khi có nhiệt BUỒNG (14/10 19:39–19:41, `tools/otl_link.py` cfg `doc_buong`)

| Khâu | Số đo |
|---|---|
| Nhiệt % → SV | SV = 130 + 2,2 × Nhiệt % |
| SV → BUỒNG | VX4 bám SV trong **10–15 s**, lệch ±3 °C, gần như không vọt — tầng nhanh, KHÔNG phải nguồn dao động |
| BUỒNG → ET | ET ≈ buồng − 15…22 °C |
| ET → BT | BT ≈ ET − 3…12 °C, trễ thêm vài giây |
| **Tổng (gió 85 %, lồng trống, máy đã ngấm)** | **BT ≈ SV − 25 °C** ⇒ BT 200 °C ≈ SV 225–228 ≈ **Nhiệt 43–45 %** |

- Hệ **NHANH** (BT theo Nhiệt % trong ~20–30 s). Mọi lần vọt lố trước đó là do bộ lái dự báo 1 phút (TAU 0,8–1,3) trên một hệ nhanh → bù quá tay. Đừng dùng dự báo RoR dài.
- Có thêm một **tầng chậm**: thân lồng ngấm nhiệt hàng chục phút, BT trôi +0,5 °C/phút dù Nhiệt % đứng yên. Bù bằng tích phân chậm (`tools/vong_ngoai_bt.py`: mỗi 30 s, Nhiệt % += 0,4 × (đích − BT), kẹp ±3).
- Bảng mục 2 dưới đây đo lúc thân máy CHƯA ngấm — chỉ dùng tham khảo khi máy còn nguội; khi máy đã nóng dùng **BT ≈ SV − 25**.
- **Gió tối thiểu máy này: 50 Hz** (chủ máy 14/10) = 33,3 % ⇒ không đặt gió dưới **34 %** (dải 45–60 Hz).

## 1c. Dùng NHIỀU yếu tố (chủ máy dặn 14/10: "nên dùng thật nhiều yếu tố để hiểu về nhiệt trong máy rang")

Chỉ nhìn BT + RoR + Nhiệt % thì mô hình lệch (bảng cân bằng trôi theo độ ngấm của thân lồng). Mô hình đúng phải có:
nguồn nhiệt (Nhiệt %, SV, **buồng VX4**, trễ buồng–SV) · khí (ET, RoR ET, buồng − ET) · hạt / lồng (BT, RoR BT, ET − BT,
**trí nhớ nhiệt**: thân lồng đã nung bao lâu, nhiệt trung bình 5–10 phút trước) · cơ cấu (gió Hz, trống Hz, cửa nạp / xả) ·
bối cảnh (lồng trống / có hạt, khối lượng mẻ, nhiệt môi trường). Việc tiếp: hồi quy dự báo BT +15 / +30 / +60 s từ log 1 giây,
kiểm trên đoạn log chưa dùng để huấn luyện, thay bảng cân bằng.

## 2. Số đo lồng trống, gió 85 %, trống 85 % (47 Hz)

| Nhiệt % | BT | RoR BT | Ghi chú |
|---|---|---|---|
| 50 | 132 → 156 °C | 42 → 5 °C/phút (tiệm cận) | 50 % KHÔNG đủ đưa BT tới 200 °C |
| 80 | ~169 °C | ~19 °C/phút | |
| 100 | 169 → 187 °C | 15–20 °C/phút | |
| 60 | 187,6 → 182,9 °C | âm | 60 % không giữ nổi 187 °C |
| 72 (thử bậc 19:19:49) | 189 → 214,8 °C sau 3 phút, còn +3 °C/phút | | cân bằng ~218–220 °C |
| **~65 (mô hình)** | **200 °C** | ~0 | nội suy 50 % → ~160 °C và 72 % → ~219 °C: **+1 % ≈ +2,7 °C BT cân bằng**; I tự học ra 63,8–66,5 % |

## 3. Bộ giữ BT — `tools/lai_may.py`

```
nhiệt% = KP × (đích − (BT + RoR × TAU)) + I         chỉnh mỗi 4 s
I += KI × (đích − BT_dự_báo)   CHỈ khi |đích − BT| < 10 °C và lệnh chưa bão hoà
KP 0,8 · TAU 0,8 phút · KI 0,15 · chỉnh mỗi 12 s, bước ±4 % · I0 = mức giữ từ MÔ HÌNH (biến môi trường I0)
Làm nóng: đặt I0 theo bảng mục 2 (200 °C ≈ 65 %) rồi để PI tinh chỉnh; ổn định ±2 °C, |RoR| < 1,5 trong 3 phút ⇒ in "SAN SANG NAP".
```

Tham số đổi khi đang chạy qua `lenh.txt` (`kp 0.8`, `tau 1.5`, `ki 0.05`, `dich 210`, `giu off`, `gas 70`, `air 60`, `drum 70`, `ignite 1`, `charge 1`…).

**Bài học chỉnh PI (đã mắc):**
- KP 1,6 + tích phân theo sai số HIỆN TẠI khi còn xa đích ⇒ I cộng dồn đúng lúc dự báo sắp vọt ⇒ nhiệt dao động 59 ↔ 100 %. Sửa: tích theo sai số DỰ BÁO, chỉ gần đích, KP 1,0.
- ⛔ **KHÔNG dùng `ror_bt` của firmware để điều khiển** (19:27): nó TRỄ 30–40 s và có lúc NGƯỢC DẤU (BT đang +35 °C/phút mà báo −15) → bộ lái tăng nhiệt đúng lúc đang vọt → BT 197 → 215 °C, cắt an toàn. Hiệu hai điểm 30 s thì nhiễu (−1,7 → +23 trong 8 s). Dùng **độ dốc hồi quy tuyến tính 20 s** (`tools/lai_may.py`).
- ⛔ **Đừng giật SV VX4 mỗi vài giây**: VX4 có PID riêng; đổi SV liên tục làm điện trở nung / ngắt dồn dập → BT có những đợt vọt ±15 °C trong 30–40 s (19:20 và 19:27). Chỉnh mỗi 12 s, mỗi lần tối đa ±4 %.
- Bộ lái đã TỰ CẮT an toàn đúng lúc (BT > đích + 15) — giữ ngưỡng này. Nhưng cắt về 0 với gió 85 % làm BT rơi 40–49 °C/phút → lại
  phải nung lại từ thấp: dao động lớn hơn. (Cải tiến: ngưỡng mềm = hạ về I − 20 %, chỉ về 0 khi ET > 255 / BT > đích + 25.)
- ⭐ **Máy điện VX4: ĐỪNG lái liên tục.** Mỗi lần TĂNG Nhiệt % là SV nhảy, PID VX4 cho điện trở chạy hết công suất → nhiệt vọt
  lố 30–40 s sau. Cách đúng khi làm nóng / giữ: **đặt thẳng mức cân bằng từ mô hình** (200 °C ≈ 65 %) rồi để VX4 tự giữ buồng;
  chỉ tinh chỉnh ±1 % mỗi 2–3 phút khi lệch quá ±3 °C. (14/10 19:30: chuyển sang cách này sau 3 lần PI làm vọt / cắt.)
- Bắt đầu với I0 = mức giữ ước lượng (bảng mục 2) để bớt vọt lố.

## 4. Đường lái và an toàn

- Đọc: COM13, PC_Link 57600, `tools/otl_link.py`. Ghi: chỉ khi HMI bật **"Điều khiển từ PC"** (cờ `pc_control` 0x40). Chỉ người được bật; agent chỉ được chạm công tắc đó qua VNC khi chủ máy đã cho quyền lái.
- ⛔ **Không dừng / khởi động lại bộ lái giữa chừng**: đứt nhịp tim ⇒ firmware báo `pc_lost` và **TỰ TẮT Lệnh nhiệt**. Đổi tham số qua `lenh.txt`. Lỡ tắt thì gửi `ignite 1`, rồi kiểm cờ `gas` (0x02) trên log.
- Ngưỡng tự hạ nhiệt về 0: ET > 255 °C, BT > đích + 15 °C, mất số liệu > 5 s, hết thời gian chủ máy cho.
- Kiểm bằng **số và cờ** từ board, không chụp ảnh. Trả màn HMI về màn chính (chạm "Vận hành") để chủ máy quan sát.
- Hết lượt lái: hạ nhiệt về 0 hoặc mức chủ máy dặn, `agent_close`, báo lại tóm tắt + đường dẫn log.

## 5. Học cách chủ máy rang

`OTL_PORT=COM13 python tools/quan_sat_rang.py <thư mục> [phút]` — CHỈ ĐỌC: log mỗi giây, `thao_tac.csv` (mỗi lần người đổi
gas/gió/trống/nút, kèm BT/ET/RoR/bước mẻ), `moc.csv` (Charge, TP, DE, FCs, DEV, Drop). Không chạy cùng lúc với `lai_may.py`
(chung cổng COM13). Sau mẻ: rút ra quy tắc "ở mốc/nhiệt nào chủ máy đổi gì, bao nhiêu" để Hồng tập lặp lại.

## 6. Nhật ký lái (bổ sung mỗi lần)

| Ngày | Máy | Việc | Kết quả / bài học |
|---|---|---|---|
| 14/10/2026 | Điện VX4, lồng trống | Giữ BT 200 °C chỉ bằng Nhiệt % | Mục 1–3. Log: `scratchpad/lai_1410/log.csv` của phiên 14/10 |
| 14/10/2026 | Điện VX4, lồng trống, gió 85 trống 85 | Đề chuỗi mốc 170→190→210→230→200→180→150 (`tools/chuoi_moc_bt.py`), tự chấm | **57/100** (vọt lố 34,3/40 · thời gian 2,3/30 · ổn định 17,1/20 · thao tác 3/10). Xong 19 phút 14 s (hạn 10 phút; tới phút 10 mới xong 4/7 mốc). Không lố ở 6/7 mốc (lố lớn nhất 1,0 / 0,5 °C); mốc 150 lố 1,7 °C. Nhiệt % giữ khớp mô hình ((T−114)/0,39−130)/2,2 trong ±3 %: 170→5–7, 190→31, 210→54, 230→73, 200→37–38, 180→18. **Bài học:** (1) chậm vì chuyển CHẠY→GIỮ quá sớm (dự báo 30 s, còn cách mốc 9–15 °C) rồi đặt cân bằng −4 % và tích phân bước 1 %/16 s ⇒ đuôi bò 96–147 s mỗi mốc, cộng 624 s; (2) mốc dưới ~165 °C không lái bằng xung bật/tắt Lệnh nhiệt: mỗi xung VX4 nung hết cỡ ⇒ BT dao động 152↔159 suốt 3 phút, mất 186 s; (3) khởi động lại bộ giải giữa chừng (vi phạm luật cứng) làm mất lịch sử độ dốc ⇒ 7 s đầu dốc = 0, xung nhiệt đến muộn ⇒ lố 1,7 °C. Lần sau: nhận diện đáp ứng bậc (100 % / tắt / 0 %+Lệnh bật) → bản sao số → tối ưu thời điểm chuyển trên mô phỏng (dự toán ≤ 540 s) → kiểm trước → làm một lượt. Log: `scratchpad/de_1410_nop/log.csv`, ảnh `cham_diem_giandoo.png` |
