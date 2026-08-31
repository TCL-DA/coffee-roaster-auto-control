# Scale Simulator — mô phỏng cân cho máy rang OTL-06ALS

App desktop giả lập **đầu cân Bluetooth/Serial** của máy rang, để test firmware
mà không cần đấu cân thật vào tủ điện.

Nó bắn liên tục khung dữ liệu ra cổng COM đúng như cân thật:

```
GS,    61.45,kg<CR><LF>
```

Firmware đọc khung này trong `include/ScaleFeeder.h`, quy ra `netW100` (×100 kg)
rồi dùng cho auto-loader (hút cà lên trống).

## Làm được gì

- Chọn cổng COM + baud (cân thật của máy chạy **2400**).
- Đặt trọng lượng, tăng/giảm từng nấc, nhảy nhanh tới một mức.
- **Mô phỏng hút**: cân tụt dần theo tốc độ đặt → test đúng đường auto-cut của firmware.
- Hiện **rorKG** (tốc độ hút, kg/phút) có lọc Kalman giống firmware, để đối chiếu số máy đọc được.
- Đếm số khung đã gửi, xem khung đang bắn.
- Giao diện Liquid Glass, tự đổi sáng/tối.

## Chạy bằng Python

```bash
pip install -r requirements.txt
python scale_simulator.py
```

Cần Python 3.9 trở lên (bản gốc build trên 3.11).

## Build ra file .exe

```bash
pip install pyinstaller
python -m PyInstaller ScaleSimulator.spec
```

Xong thì file nằm ở `dist/ScaleSimulator.exe`.

**Lưu ý build:** `customtkinter` bắt buộc phải `collect_all` (spec đã làm sẵn) vì nó
cần kèm mấy file theme `.json`; thiếu là chạy exe lên báo lỗi thiếu asset. Nếu app
đang mở mà build lại thì Windows khoá file exe (`WinError 5`) — đóng app trước.

Muốn build bằng dòng lệnh thay vì spec:

```bash
python -m PyInstaller --onefile --windowed --name ScaleSimulator \
    --icon scale_icon.ico \
    --add-data "scale_icon.ico;." \
    --collect-all customtkinter \
    scale_simulator.py
```

## Nối vào máy rang thế nào

Hai cách:

1. **Cáp USB-Serial thật** — cắm vào đúng cổng cân trên board máy rang (RS232/TTL tuỳ đấu nối).
2. **Cặp COM ảo** (com0com, HHD Virtual Serial Port) — simulator bắn vào COM ảo,
   phần mềm test đọc đầu bên kia. Cách này chỉ test được phần mềm PC, không test được firmware.

Nhớ khớp **baud** hai đầu. Máy rang OTL dùng **2400** cho cân
(`SCALE_SERIAL_BAUD` trong `include/Config.h`).

## File trong gói

| File | Việc |
|---|---|
| `scale_simulator.py` | toàn bộ mã nguồn, 1 file |
| `ScaleSimulator.spec` | cấu hình build PyInstaller (đường dẫn đã sửa thành tương đối) |
| `scale_icon.ico` / `.png` | icon, sinh từ `tools/make_icon.py` của dự án |
| `requirements.txt` | thư viện cần cài |
