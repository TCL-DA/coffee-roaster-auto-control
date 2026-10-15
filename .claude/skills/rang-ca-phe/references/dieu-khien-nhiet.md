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

## 7. Bộ giải đề chuỗi mốc qua panel — MPC trên bản sao số (15/10/2026)

`tools/hong_qua_panel.py` (`GiaiDe`, `chay_de`, `cham_alog`) + `tools/ban_sao_so_may_dien.py` (mô hình 1 giây, tham số
`ban_sao_so_may_dien.json`). Cùng MỘT vòng lái cho máy thật (`Panel` + `ArtisanThat`) và dry-run (`PanelAo` + `ArtisanAo`).

```
Mỗi giây: đọc panel ($60 BT, $61 ET, $96 buồng, $1, $13, $21, $40)
  → bộ quan sát 5 mô hình (độ nhạy 0,76 … 1,01 °C/%) · bù trễ chết 2 s (đọc panel + lệnh panel→board→VX4)
  → chọn mô hình khớp máy nhất: sai số dự báo VÒNG HỞ 15 s với đúng lệnh đã ra (EWMA)
  → thử ~1 800–2 500 kế hoạch 150 s: giữ · đổi mức ở τ · CHẠY hết cỡ rồi hãm ở τ · 1 xung / 2 xung ngắn tính trước
  → chọn kế hoạch xong mốc sớm nhất mà BT dự báo KHÔNG vượt mốc quá lề (0,5 °C; mốc thấp 0,8; đang giữ 0,9) theo chiều đang đi
Lớp an toàn riêng (bộ giải không ghi đè): BT > 245 · ET > 255 · mất số panel > 5 s · Artisan mất số / ngừng ghi > 10 s
  · mã $40 cảnh báo / lỗi · cờ PC control bật · màn ≠ màn rang · quá 12 phút ⇒ TẮT Lệnh nhiệt.
```

**Bài học 15/10 (đã mắc — không lặp lại):**
- ⛔ **Không giản đồ Artisan = bài không tính.** Trước lệnh nhiệt đầu tiên Artisan phải ĐANG GHI, kiểm đủ 3 điều: START vô hiệu ·
  đồng hồ chạy · có đường ET/BT. UIA đọc ô đồng hồ (QLCDNumber) ra "0" ⇒ phải so ẢNH ô đồng hồ. Ảnh lấy bằng **PrintWindow**,
  không chụp màn hình: chủ máy đang dùng VS Code che Artisan ⇒ ảnh chụp màn hình đứng yên ⇒ báo nhầm "đồng hồ đứng", lượt 2 bị
  dừng ở 75 s. Bước làm nóng / về điều kiện đầu cũng phải có giản đồ riêng.
- Artisan 4.0.2 có thể **ẩn thanh nút** (View → Controls tắt) ⇒ UIA không thấy ON/OFF/START — bật lại bằng menu UIA
  (ExpandCollapse + Invoke). Bị thu nhỏ ⇒ Qt không vẽ ⇒ khôi phục bằng WindowPattern.
- **Máy ngấm nông khác máy ngấm sâu.** 14/10 tối: BT ≈ SV − 25. 15/10 sáng sau 18 phút ngấm (40 → 55 %): BT ≈ buồng − 58 lúc 55 %
  (thân lồng còn thiếu nhiệt). Tham số học hôm trước dự báo lệch dần; học lại trên log hôm nay (ngấm + lượt 1) ⇒ dự báo 120 s
  MAE 1,50 → 1,22 °C. Mức giữ thật 15/10: 170 → 11 % · 190 → 32–34 % · 210 → 56–57 % · 230 → 76 % · 200 → 39–40 % · 180 → 17 %.
- **Tích phân lệch cân bằng chỉ khi đang giữ gần mốc** (đúng bài học PI 14/10). Lượt 1: offset tích phân cả lúc chuyển mốc ⇒ trôi
  −10 °C, bão hoà ⇒ dự báo mốc 150 sai ⇒ để TẮT 90 s rồi mới hãm ⇒ lố xuống 2,3 °C.
- **Mốc dưới mức Lệnh-bật-0 %** (SV 130 °C mà BT cân bằng vẫn ~160 °C): không giữ được bằng Nhiệt % — chỉ bằng xung ngắn TÍNH
  TRƯỚC trên mô hình (1–2 xung 2–6 s, nghỉ 6–24 s). Số thật: xung 9 s ở buồng 97 °C ⇒ BT +6 °C sau 18 s; TẮT Lệnh ⇒ nguội
  −11 °C/phút quanh 150. Khi đang ở chế độ này KHÔNG khoá Lệnh lúc "đang giữ" (khoá làm xung kéo thành 12 s).
- **Đang giữ trong dải: chỉ tinh chỉnh Nhiệt ±4 %, cấm đảo Lệnh / chạy 100 %.** Lề lố 0,3 quá chặt so với nấc 1 % (≈ 0,8–0,9 °C)
  ⇒ bộ giải TẮT 6 s ngay tại mốc ⇒ BT rơi khỏi dải ⇒ đếm lại từ đầu, chu kỳ không dứt (giáo trình mục 3: đặt mức rồi để VX4 giữ).
- **Chưa kế hoạch nào xong trong tầm nhìn mà còn cách mốc > 8 °C ⇒ CHẠY hết cỡ** (lên 100 %, xuống TẮT Lệnh). Không thì bộ giải
  đứng yên ở mức giữ cũ (180 → 150 đứng 17 % suốt 96 s trên bản sao số).
- Ngân sách 10 phút rất sát: 7 lần giữ × 30 s = 210 s; chuyển 7 đoạn ≈ 60–90 s mỗi đoạn. Đạt được chỉ khi hãm muộn nhất có thể
  mà không lố — tức là phải có mô hình dự báo, không thể dùng luật ngưỡng.

## 7b. Bài GIÓ — Nhiệt khoá, chỉ lái gió (15/10/2026, `hong_qua_panel.py giu_bt_gio`)
- Máy điện VX4 giữ BUỒNG theo Nhiệt % (75 % ⇒ buồng ~295 °C, đo $96). Khi đó **gió là bộ CỘNG nhiệt**, không phải bộ hút nhiệt:
  gió 100 đưa nhiều khí nóng hơn qua lồng ⇒ BT lên nhanh hơn; gió 50 chậm hơn nhưng VẪN lên (khác mục 1: gió hút nhiệt khi TẮT nhiệt).
- Số đo (`F:/Artisan/Profile/OTL-Hong/du-lieu_1510_gio/do75.csv`): 75 %, gió 100, lồng vừa nguội ⇒ BT 125 → 196 trong ~2 phút
  (~15 °C/ph ở 196). Hạ 100 → 50 ở BT 197,7 ⇒ quán tính +6,6 °C trong 30 s, rồi RoR ~1,5 trong ~30 s, sau đó ổn ~2,6 °C/ph ở 205.
  Nâng 50 → 100 ở 206,6 ⇒ RoR ~6 sau trễ ~10 s. Độ nhạy ≈ 0,07–0,10 °C/ph cho mỗi 1 % gió.
- **Giới hạn vật lý:** gió tối thiểu 50 vẫn trôi lên ⇒ không giữ đứng 200. Chỉ qua được luật "± 1,5 liên tục ≥ 60 s cuối" khi độ trôi
  gió 50 quanh 200 (r50) ≤ ~2,6 °C/ph (dải 3 °C đi hết trong 60 s ⇒ ≤ 3; trừ lề nhiễu). Vì gió chỉ TĂNG TỐC được, chiến lược đúng là
  "đến MUỘN rồi dùng gió đuổi": xuất phát sao cho quỹ đạo tự nhiên ở gió 50 hơi chậm; đến sớm là lố không cứu được.
- Mô phỏng `GiuBTGio` (mô hình r50 = (Teq − BT)/τ + kg·(gió − 50)): r50(200) 3,1–4 ⇒ vào dải lúc 266–275 s ⇒ TRƯỢT. Lượt thật chưa làm.
- Giả thuyết cần đo: lồng ngấm ít (nung nhanh bằng gió 100 từ lồng nguội, thả gió 50 lúc BT ~192) ⇒ r50 ở 200 thấp hơn ngấm chậm.

- **Đo trên máy 15/10 chiều (trống 100, anh đổi 85 → 100):** gió 50 quanh 195–206 trôi **~3,6 °C/ph** (`OTL-Hong 2026-10-15 1339.alog`,
  t 120 → 300 s: 195,4 → 206,2). Dải ± 1,5 đi hết trong ~50 s ⇒ luật "giữ 200 ≥ 60 s cuối" KHÔNG làm được bằng gió ở 75 %/trống 100.
- **⛔ Cú vọt nung lại (bài học đắt nhất, mất 2 lượt):** START khi buồng còn dưới SV (buồng 157–232 °C sau bước nguội) ⇒ VX4 nung hết
  cỡ ~90 s ⇒ BT lên 30–55 °C/ph, gió 50 không hãm nổi ⇒ BT 152 → 215 trong ~2 phút (1348.alog), 187 → 215 trong 57 s (1354.alog,
  tự cắt an toàn BT > 215). Gió chỉ là phanh yếu (~0,05–0,07 °C/ph mỗi 1 %). **Điều kiện đầu phải gồm BUỒNG ≥ ~290 (đã chạm SV)**,
  không chỉ BT; bước chuẩn bị phải nung tới khi buồng chạm SV rồi mới tính điểm START theo BT (`chuan_bi_gio` hiện chỉ nhìn BT — cần sửa).
- Bậc thang LÊN 195 → 200 → 205 (30 s mỗi mốc) thuận chiều trôi: gió 50 cố định đi qua mỗi dải 3 °C trong 45–55 s. Lượt 1339 (chạy cho
  đề giữ 200) chấm theo bậc thang: 195 vào 98 s ra 144 s (46 s) · 200 166 → 221 s (55 s) · 205 256 → 300 s (44 s) ⇒ 3/3.

## 6. Nhật ký lái (bổ sung mỗi lần)

| Ngày | Máy | Việc | Kết quả / bài học |
|---|---|---|---|
| 14/10/2026 | Điện VX4, lồng trống | Giữ BT 200 °C chỉ bằng Nhiệt % | Mục 1–3. Log: `scratchpad/lai_1410/log.csv` của phiên 14/10 |
| 14/10/2026 | Điện VX4, lồng trống, gió 85 trống 85 | Đề chuỗi mốc 170→190→210→230→200→180→150 (`tools/chuoi_moc_bt.py`), tự chấm | **57/100** (vọt lố 34,3/40 · thời gian 2,3/30 · ổn định 17,1/20 · thao tác 3/10). Xong 19 phút 14 s (hạn 10 phút; tới phút 10 mới xong 4/7 mốc). Không lố ở 6/7 mốc (lố lớn nhất 1,0 / 0,5 °C); mốc 150 lố 1,7 °C. Nhiệt % giữ khớp mô hình ((T−114)/0,39−130)/2,2 trong ±3 %: 170→5–7, 190→31, 210→54, 230→73, 200→37–38, 180→18. **Bài học:** (1) chậm vì chuyển CHẠY→GIỮ quá sớm (dự báo 30 s, còn cách mốc 9–15 °C) rồi đặt cân bằng −4 % và tích phân bước 1 %/16 s ⇒ đuôi bò 96–147 s mỗi mốc, cộng 624 s; (2) mốc dưới ~165 °C không lái bằng xung bật/tắt Lệnh nhiệt: mỗi xung VX4 nung hết cỡ ⇒ BT dao động 152↔159 suốt 3 phút, mất 186 s; (3) khởi động lại bộ giải giữa chừng (vi phạm luật cứng) làm mất lịch sử độ dốc ⇒ 7 s đầu dốc = 0, xung nhiệt đến muộn ⇒ lố 1,7 °C. Lần sau: nhận diện đáp ứng bậc (100 % / tắt / 0 %+Lệnh bật) → bản sao số → tối ưu thời điểm chuyển trên mô phỏng (dự toán ≤ 540 s) → kiểm trước → làm một lượt. Log: `scratchpad/de_1410_nop/log.csv`, ảnh `cham_diem_giandoo.png` |
| 15/10/2026 | Điện VX4, lồng trống, gió 85 trống 85, ngấm 18 phút (40 → 55 %) | Đề chuỗi mốc qua panel ($M36/$1), bộ giải MPC `hong_qua_panel.py`, chấm từ `.alog` (luật cứng cấm lố > 1,5 °C) | Điều kiện đầu mọi lượt: BT 200 ± 1,5 ổn định (Nhiệt 44–45 %), có giản đồ riêng (0918 / 0935 / 0959). **Lượt 1** `0905.alog`: 6/7 mốc trong 553 s, mốc 150 TRƯỢT (lố xuống 2,3, hết 12 phút) — offset tích phân lúc chuyển mốc trôi −10 °C. **Lượt 2** `0932.alog`: dừng ở 75 s — kiểm "đồng hồ đứng" báo nhầm vì chụp màn hình bị VS Code che (đổi sang PrintWindow); không tính. **Lượt 2b** `0946.alog`: 6/7, lố lớn nhất 0,1, mốc 150 chưa xong lúc hết 12 phút; mốc 190 mất 128 s vì TẮT Lệnh ngay tại mốc. **Lượt 3** `1009.alog`: **7/7 mốc, KHÔNG vọt lố** (lên 0,2 / xuống 0,8), tổng **11:24** (hạn 10:00) — 170 102 s · 190 79 · 210 90 · 230 130 · 200 75 · 180 73 · 150 135 (2 xung tính trước). Chưa đạt chỉ vì thời gian. Lần sau: mốc 230 (130 s) và 210 (90 s) là chỗ gỡ giờ — hãm muộn hơn khi đi lên; mốc 150 không nhanh hơn được nhiều (nguội TẮT −16 °C/phút từ 180 ⇒ ~105 s + 30 s giữ). Mục 7. Log: `scratchpad/that_1510/` phiên 15/10 |
| 15/10/2026 chiều | Điện VX4, lồng trống, trống 85 | Đề 2: Nhiệt khoá 75 %, chỉ gió 50–100 %, giữ BT 200 (5 phút/lượt, ≤ 3 lượt) | **Chưa lượt nào.** 13:18 bước ngấm có giản đồ tự dừng TRƯỚC lệnh nhiệt đầu: Artisan "Modbus Error: failed to connect" (COM13 bị `platformio device monitor` giữ) ⇒ lớp kiểm điểm ảnh `dang_ghi` chặn đúng; `kiem()` báo "LCD có số" sai vì ân hạn 10 s ⇒ đã sửa. Luật mới: không chiếm màn hình anh (không restore / menu). Vật lý bài gió: mục 7b. |
| 15/10/2026 13:38–13:56 | Điện VX4, lồng trống, trống 100 | Đề 2 gió (Nhiệt 75 % khoá, gió 50–100): L1–L2 đề giữ 200 ≥ 60 s; L3 đề bậc thang 195/200/205 × 30 s | L1 `1339.alog` trượt (vào dải 166 s, BT cuối 205,8, lố 5,9; trôi gió 50 ~3,6 °C/ph) — chấm theo bậc thang thì 3/3. L2 `1348.alog` trượt (START buồng 157 ⇒ vọt tới 215, cắt an toàn 273 s). L3 `1354.alog` trượt (START buồng 220 ⇒ vọt 187 → 215 trong 57 s, cắt an toàn). Bài học: điều kiện đầu phải có buồng ≥ 290 (mục 7b). |
