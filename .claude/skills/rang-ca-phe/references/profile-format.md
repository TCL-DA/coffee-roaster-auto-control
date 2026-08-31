# Hồ sơ rang trên app OTL Roast Lab — cấu hình & lưu CSV

## 1. Cấu hình 1 hồ sơ (object hiện tại)

Nguồn: `OTL Roast Lab.html`, hàm `newProfile()` (~dòng 2926). Hồ sơ là **thẻ công thức gọn**, KHÔNG chứa mốc DE/FCs/DEV chi tiết (các mốc đó app tự dò lúc rang thật, lưu vào log mẻ SQLite).

| Trường | Kiểu | Ý nghĩa | Mặc định |
|--------|------|---------|----------|
| `name` | text | Tên hồ sơ | "Hồ sơ mới" |
| `roast` | chọn | Mức rang (Rang nhạt/vừa/đậm) | `loadRoasts()[0]` |
| `chargeT` | °C | Nhiệt nạp mẻ (charge) | 160 |
| `temp` | °C | Nhiệt đích / xả (drop) | 200 |
| `time` | mm:ss | Tổng thời gian rang | "12:00" |
| `notes` | text | Ghi chú (origin · process · flavor) | "" |
| `roaster` | text | Người rang (từ tài khoản) | tên session |
| `date` | dd/mm/yyyy | Ngày tạo | hôm nay |
| `color` | hex | Màu nhãn UI | xoay vòng palette |

## 2. Xuất file ra thư mục — mỗi hồ sơ 3 tệp (ĐÃ code)

**Nguồn thật (canonical) vẫn là `profiles.json`** (ghi tạm→thay, `roast_lab_hmi.py:874`). Ngoài json, mỗi lần lưu app **xuất kèm** các tệp dễ đọc vào **gốc `prof_dir`** (thư mục hồ sơ người dùng chọn) qua `prof_write_files()` ([roast_lab_hmi.py:787](../../../tools/roast_lab_hmi.py)) + `prof_export_pdf()`. Hàm sinh nội dung nằm ở [OTL Roast Lab.html](../../../OTL%20Roast%20Lab.html) `profDiskWrite()`.

**Mỗi hồ sơ CÓ CURVE = 3 tệp** (tên = `{slot} - {name}` đã lọc ký tự cấm `\ / : * ? " < > |` → `-`):

| Tệp | Hàm sinh | Công dụng |
|-----|----------|-----------|
| `{i} - name.csv` | `profCsvMachine()` | **Chương trình máy + rang** — cột y hệt `sdLogWrite()` firmware (`Time1/Time2/ET/BT/Event/Air/Burner/Drum/VacFlag/VacSP`), header có mốc + `MaxGas`. |
| `{i} - name.alog` | `profAlog()` | **Profile Artisan native** — Python dict repr (`ast.literal_eval` được): `timex/temp1(ET)/temp2(BT)` mỗi giây 1 mẫu, `timeindex=[CHARGE,DRYe,FCs,FCe,SCs,SCe,DROP,COOL]`. Artisan mở & lưu lại thẳng. |
| `pdf/{...}.pdf` | `prof_export_pdf()` (Python/matplotlib) | **Xem ngay trên điện thoại** — phiếu thông số + đồ thị curve. |

Kèm 1 file **index** chung mọi hồ sơ: `profiles.csv` (`profCsvIndex()`), header **tiếng Anh** `slot,name,notes,roast,chargeT,dropT,time,date,roaster,curve`, cờ curve `YES/NO`, UTF-8 có BOM.

Hồ sơ **chưa rang mẻ nào** (không có curve) → chỉ vào `profiles.csv` + phiếu PDF (không có `.csv`/`.alog` curve).

### Nguyên tắc giữ an toàn
- Ghi **tạm rồi thay** (`.tmp` → `os.replace`) để không có file cụt; chặn path traversal (`os.path.basename`).
- localStorage = **cache** hằng ngày; `profiles.json` + tệp xuất trong thư mục là bản **bền, copy/chia sẻ** được. Web LAN đọc **chung** `profiles.json`.
- **Log mẻ thực tế KHÔNG đụng** — vẫn ở SQLite `batches.db` (bằng chứng sản xuất). Các tệp trên chỉ là **công thức + curve mục tiêu** xuất ra cho người/Artisan/điện thoại đọc.

### Liên quan
- `[[project_sd_auto_pclink]]` (hồ sơ app), `[[project_web_clone]]` (web đọc chung), `[[project_gd123_done]]` (log mẻ SQLite).
