# ref-loader-autolearn — Auto-Loader tự học `dif` (máy 30kg cacao)

Tài liệu tham chiếu cho hệ thống **auto-loader** (hút cà từ phễu nguồn lên lồng rang) và cơ chế **tự học `dif`** (lượng cắt feeder sớm để bù coast). Cập nhật: **2026-06-24**.

> Bản chất: feeder/cửa xả đóng KHÔNG tức thời → sau khi ra lệnh cắt, cà vẫn rơi thêm một lượng (**coast**). Phải cắt **sớm** trước đích một khoảng `dif` ≈ coast. `dif` được **tự học** theo điểm vận hành `(cân, tốc độ hút)`.

---

## 1. Tham số cấu hình (Config.h)

| Macro | Giá trị | Đơn vị / ý nghĩa |
|-------|---------|------------------|
| `FEEDER_DIF_MAX` | **25** | ×10 kg → trần `dif` = **2.5 kg** (coast máy này ~1.3–1.6kg) |
| `FEEDER_CFG_MAX` | 48 | số ô tối đa trong bảng học |
| `FEEDER_ADAPT_GAIN` | 30 | ×100 → EMA kéo 0.30/mẻ về `dif` đúng |
| `FEEDER_W_BUCKET` | 5 | kg — bước lưới snap theo cân |
| `FEEDER_ROR_BUCKET10` | 25 | ×10 → bước lưới ror = 2.5 kg/phút |
| `FEEDER_TKG_DEFAULT` | 190 | ×10 ms/kg — CHỈ dùng làm mồi khi bảng rỗng |
| `FEEDER_SEED_WKG` | 100 | kg — cân tham chiếu nội suy bảng mặc định |
| `FEEDER_STABLE_ROR` | 20 | ×100 → 0.2 kg/phút: ngưỡng coi cân ĐỨNG YÊN |
| `FEEDER_SETTLE_MIN_MS` | 1500 | ms — chờ tối thiểu sau cắt cho cà lắng |
| `FEEDER_SETTLE_TMO` | 15 | giây — timeout chờ ổn định |
| `FEEDER_OFFSET_MAX100` | 30 | ×100 → trần offset lực hút (0.30kg) |
| `FEEDER_WSTART_DELAY_MS` | 3000 | ms — chờ rồi mới chốt wStart + đo offset |
| `LOADER_CSV_MAX` | 400 | số dòng log tối đa giữ |
| `MACHINE_BATCH_KG` / `LOADER_MIN_BATCH_PCT` | 30 / 80 | ngưỡng cho auto-loader chạy khi rang AUTO |

**Bộ lọc ror cân (Define.h):** `SimpleKalmanFilter rorKGKalmanFilter(1, 1, 0.7)` + cửa sổ **1 giây** (hệ số ×6), trần **60 kg/phút** (clamp ±600 trước Kalman).

---

## 2. Thuật toán

### Lúc hút — chọn `dif` & cắt (Program.h `programScan`)
1. `rorMag = |rorKG|`; `loaderQuantize(cân, rorMag)` → snap về ô lưới `(qw, qr10)`.
2. `loaderCfgFind` ô khớp đúng → nếu trống dùng `loaderCfgNearest` (ô học gần nhất); bảng rỗng → công thức `rorMag×feederTkg×wStart/60000000` làm mồi.
3. Kẹp `dif100` ∈ `[0, FEEDER_DIF_MAX×10]`.
4. **Cắt** khi `netW100 ≤ difNetW×10 + dif100 + suctionOffset100` (so ở ×100 cho mượt 0.01kg).

### Sau cắt — học (Program.h `loaderAdapt`)
1. Chờ lắng: `elapsed ≥ SETTLE_MIN_MS && |rorKG| ≤ STABLE_ROR`, hoặc hết `SETTLE_TMO`.
2. `err = final − target` (>0 = hút thiếu). `score = 10 − |err|×10`. OK = score ≥ 9.0 (lệch ≤0.09kg).
3. **Chỉ học khi THẤT BẠI** (deadband): OK thì giữ nguyên. `difReal = dif − err`.
   - Ô mới + còn chỗ → tạo (n=1).
   - **Bảng đầy → thay ô `cfgN` nhỏ nhất** (eviction) → không bao giờ ngừng học.
   - Ô cũ → EMA gain 0.30 kéo về `difReal`, n++.
4. Ghi `loaderCfgSave()` + 1 dòng `loaderLogEvent()`.

---

## 3. File trên thẻ SD (tên 8.3 bắt buộc — SD lib 1.2.4)

- **`loadcfg.csv`** — bảng học. Cột `wKg,rorKgMin,dif,n`. Xoá file này = học lại từ seed.
- **`loader.csv`** — log mỗi mẻ. Cột `STT,s,wStart,batch,set,secHut,rorKG,dif,offset,target,final,err,score,result,difOld,difNew`. Header chỉ ghi khi file rỗng (`f.size()==0`).

---

## 4. Chế độ DEBUG (gate `enDebug`, mặc định TẮT)

Bật `enDebug=1` → bấm loader → tự in ra SerialComputer (9600), 1 dòng/giây, tắt 10s sau khi loader off (giữ tới khi log xong).

```
LDR t=12 btn=1 vld=1 w=2787 set=300 dN=21 raw=-4440 ror=-4410 dif=126 thr=336 wS=3208 ph=0 arm=1 stp=0 cfg=48
LDR >>> AUTO-CUT (normal path, will settle+log)
LDR >>> LOG: result=OK score=98 set=300 err=2 final=212 batch100=2998 secHut=43
```
Sự kiện chẩn lỗi: `CLEAN-FEEDER (NO LOG)` (phễu nhẹ), `LOG FAIL: SD.open ... FAILED` (thẻ lỗi).

⚠️ In ~95ms/giây ở 9600 → jitter cắt ~0.08kg → **đừng đánh giá độ chính xác khi debug ON.**

---

## 5. Giới hạn đã biết (quan trọng)

- **Trần chính xác phần cứng ≈ ±0.1 kg.** Cửa xả đóng **500–700ms** (chỉ ON/OFF, không điều tốc), riêng dao động thời gian đóng đã tạo ~±0.15kg coast ngẫu nhiên. Phần mềm KHÔNG phá nổi trần này — muốn hơn cần thêm van trim nhanh (<100ms).
- **coast ≈ 1.46 ± 0.09 kg**, phụ thuộc **ror** & **mức-cắt**, **KHÔNG phụ thuộc cân đầu**. (Hạt cà là biến số → ror là proxy hữu ích nhưng nhiễu.)
- **Mẻ TÍ HON 2–3kg hỏng cố hữu:** sau bấm loader, 7s sau cửa mới mở → mẻ nhỏ cà chỉ chảy ~2–3s → ror không kịp ramp → OVER tới −1.2kg. Mẻ ≥5kg thì OK. Cần hướng riêng cho mẻ nhỏ (dif không dựa ror tức thời).
- **Offset lực hút 100–300g KHÔNG được bù** (động cơ kéo cân giảm → offset âm bị `if(off<0)off=0` ép về 0 — giữ nguyên theo yêu cầu). Học `dif` tự nuốt phần trung bình.
- **Thẻ SD phải tốt:** thẻ lỗi → `SD.open` thất bại âm thầm → không ghi được loadcfg/loader.csv. Dùng thẻ chính hãng, format FAT32.

---

## 6. Tinh chỉnh khi cần

| Triệu chứng | Chỉnh |
|-------------|-------|
| Mẻ ngắn OVER nhiều | ror đang trễ → tăng q Kalman / giảm cửa sổ (đang 0.7 / 1s là nhanh nhất hợp lý) |
| ror nhảy quá | giảm q (nhưng coi chừng mẻ ngắn trễ lại) |
| OVER/UNDER lặp ở cùng ô | EMA chậm → tăng `FEEDER_ADAPT_GAIN` |
| Bảng đầy ô rác | tự eviction; hoặc xoá thủ công loadcfg.csv |
| Chờ lâu sau cắt | hạ yêu cầu settle: tăng `FEEDER_STABLE_ROR` (giảm chính xác) |

> Bộ nhớ liên quan: `project_loader_dif_tuning` (lịch sử Phase 1–5 + session 2026-06-24).
