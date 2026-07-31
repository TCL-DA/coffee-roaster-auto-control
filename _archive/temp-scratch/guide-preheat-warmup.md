# Làm nóng máy rang thủ công (không dùng Preheat)

## Thông số cơ bản

- Nhiệt độ charge: 160-200°C (tùy sản phẩm)
- ET mục tiêu trước charge: 230-260°C
- ET-BT gap lý tưởng: +20 đến +40°C

---

## Quy trình đề xuất

### Bước 1: Bật trống + gió trước
- Bật trống ở tốc độ rang bình thường
- Gió khoảng 30-40% để lưu thông khí

### Bước 2: Bật lửa
- Bật đầu đốt ở **60-70% công suất**
- Không bật 100% ngay — tránh nhiệt không đều, làm nóng quá nhanh một phía

### Bước 3: Theo dõi ET
- ET (nhiệt độ khí thải) phản ánh nhanh hơn BT
- Mục tiêu: ET đạt **230-260°C** trước khi charge
- Lý do: sau khi đổ cà phê vào, ET sẽ giảm mạnh do hạt hấp thụ nhiệt

### Bước 4: Theo dõi BT
- BT cần đạt **160-200°C ± 5°C** trước khi charge (tùy sản phẩm)
- Nên để BT **ổn định 3-5 phút** tại nhiệt độ charge mong muốn trước khi charge
- Không charge khi BT còn đang tăng

### Bước 5: Kiểm tra ET-BT gap
- ET - BT nên khoảng **+20 đến +40°C** lúc charge
- Nếu gap quá nhỏ (<5°C) → máy chưa đủ nhiệt đều
- Nếu gap quá lớn (>40°C) → giảm lửa, chờ cân bằng

---

## Dấu hiệu máy đã sẵn sàng

✅ BT ổn định tại nhiệt độ charge trong 3-5 phút
✅ ET khoảng 240-270°C
✅ ET-BT gap dương và ổn định
✅ RoR BT gần 1-3°C/phút (không còn tăng nhanh)

## Không charge khi

❌ BT còn đang tăng nhanh (RoR > 15°C/phút)
❌ ET-BT gap đang thay đổi nhiều

---

## Lưu ý vận hành

- Nên rang liên tiếp các mẻ, **nghỉ không quá 20 phút** giữa các mẻ
- Mẻ đầu ngày nên để máy làm nóng lâu hơn các mẻ tiếp theo

---

## Ngưỡng an toàn bắt buộc (firmware tự động xử lý)

| Cảm biến | Ngưỡng | Hành động tự động |
|---------|--------|-----------------|
| BT (nhiệt độ trong lồng rang) | > 250°C | Tắt lửa ngay lập tức, báo lỗi 401 lên HMI |
| ET (nhiệt độ khí thải) | > 350°C | Tắt lửa ngay lập tức, báo lỗi 264 lên HMI |

- Firmware kiểm tra mỗi giây, không phụ thuộc trạng thái vận hành
- Khi thấy mã **401** hoặc **264** trên màn hình HMI → kiểm tra ngay, không rang tiếp cho đến khi xác định nguyên nhân
