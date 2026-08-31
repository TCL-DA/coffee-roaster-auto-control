---
name: profile-analyze
description: Đọc và phân tích file profile rang (.txt hoặc .csv) từ SD card. Vẽ timeline text, kiểm tra tính hợp lệ dữ liệu, so sánh curve thực tế vs mục tiêu.
allowed-tools: Read, Bash
---

Phân tích file profile rang cà phê từ SD card của máy OTL-06ALS.

## Input

Argument là tên file hoặc số slot: `/profile-analyze 3` hoặc `/profile-analyze 3.txt`

Tìm file tại:
- `3.txt` — format cũ (raw data)
- `3.csv` — format mới (Artisan CSV)

Nếu không có argument, liệt kê tất cả file profile có trên SD (nếu truy cập được) hoặc hỏi user.

## Bước 1 — Đọc file

**Format `.txt`:**
```
R<time>,<BT>,<ET>,<Air>,<Gas>,<Drum>,<RoR>,<VacFlag>,<VacSP>E
P<ChargeBT>,<TP_BT>,<TP_time>,<DE_BT>,<DE_time>,<FCS_BT>,<FCS_time>,<DEV_BT>,<DEV_time>,<DROP_BT>,<DROP_time>E
```
- Nhiệt độ: ×10 (1850 = 185.0°C)
- Thời gian: giây

**Format `.csv`:**
Header dòng 1: milestones (CHARGE, TP, DRYe, FCs, DROP)
Header dòng 2: cột (Time1, Time2, ET, BT, Event, Drum%, Airflow%, Burner%, ...)
Dữ liệu: tab-separated

## Bước 2 — Kiểm tra tính hợp lệ

Với mỗi bản ghi dữ liệu, kiểm tra:

| Trường | Range hợp lệ | Cảnh báo nếu |
|--------|-------------|-------------|
| BT | 500–2500 (50–250°C) | < 500 hoặc > 2500 |
| ET | 500–3500 (50–350°C) | < 500 hoặc > 3500 |
| Air% | 0–100 | < 0 hoặc > 100 |
| Gas% | 0–100 | < 0 hoặc > 100 |
| Drum% | 0–100 | < 0 hoặc > 100 |
| RoR | -950–950 | ngoài range |
| Time | tăng dần | giảm hoặc lặp |

Báo cáo:
- Số bản ghi hợp lệ / tổng số
- Các điểm dữ liệu bất thường (time, giá trị)
- Khoảng trống dữ liệu (missing seconds)

## Bước 3 — Phân tích milestones

Từ Properties line hoặc CSV header, trích:
- CHARGE: nhiệt độ BT lúc nạp cà phê
- TP (Turning Point): BT, thời gian
- DRYe (Yellow/Dry end): BT, thời gian
- FCs (First Crack Start): BT, thời gian
- DROP: BT, thời gian

Tính:
- **Drying phase**: CHARGE → TP → DRYe (thời gian, delta BT)
- **Maillard phase**: DRYe → FCs (thời gian, delta BT)
- **Development phase**: FCs → DROP (thời gian, %)
- **Total roast time**: CHARGE → DROP

Đánh giá theo chuẩn rang specialty coffee:
- Development ratio: 15–25% là tốt (< 15% under-developed, > 25% over-developed)
- Total time: 8–15 phút thường gặp

## Bước 4 — Vẽ curve BT dạng text

Vẽ biểu đồ nhiệt độ BT theo thời gian (ASCII art):

```
°C  |
250 |                                              * DROP
    |                                         *
230 |                                    * FCs
    |                              *
210 |                         * DRYe
    |                   *
190 |             * TP
    |        *
170 |   *
    | *
150 +--+----+----+----+----+----+----+----+----+-> min
    0  1    2    3    4    5    6    7    8    9
```

Scale trục Y: từ min(BT) đến max(BT), bước 10°C
Scale trục X: thời gian phút, bước 1 phút
Đánh dấu milestones bằng ký tự đặc biệt

## Bước 5 — Phân tích Vacuum (nếu có VacFlag)

Nếu profile có cột VacFlag/VacSP:
- Liệt kê các khoảng thời gian bật PID vacuum (VacFlag=1)
- Setpoint vacuum ở từng giai đoạn
- Nhận xét về chiến lược airflow (manual vs PID)

## Bước 6 — So sánh Gas profile

Vẽ Gas% theo thời gian (text):
- Xác định các bước tăng/giảm gas chính
- Tính tốc độ thay đổi gas (nếu auto): bình thường hay đột ngột?
- Cảnh báo nếu gas > 95% kéo dài (nguy cơ quá nhiệt)

## Bước 7 — Tổng kết

```
📋 PROFILE RANG #X

⏱  Tổng thời gian rang: X phút X giây
🌡  CHARGE: X°C
📍 Milestones:
   TP    : X°C @ X:XX
   Yellow: X°C @ X:XX
   FCs   : X°C @ X:XX
   DROP  : X°C @ X:XX

📊 Phân tích phase:
   Drying (CHARGE→Yellow): X phút (X%)
   Maillard (Yellow→FCs):  X phút (X%)
   Development (FCs→DROP): X phút (X%) ← [tốt/thiếu/thừa]

⚠️  Vấn đề phát hiện:
   - [nếu có]

💡 Gợi ý:
   - [nếu development ratio ngoài 15-25%]
   - [nếu có bất thường dữ liệu]
```
