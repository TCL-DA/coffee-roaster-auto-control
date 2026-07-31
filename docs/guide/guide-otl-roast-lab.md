# guide-otl-roast-lab — OTL Roast Lab (app rang & phân tích roast log)

App chạy thật: nối máy rang, phân tích roast log real-time. Có thêm chế độ máy rang ảo
để test firmware ở nhà khi không có tủ điện — nạp profile → "firmware ảo" chạy đúng nguyên
lý [`calibProgram()`](include/Program.h#L782) bằng Python → model nhiệt đóng vòng kín → xem
calib có kéo BT bám profile không. Có expose Modbus slave (map
[`include/Modbus_Slave.h`](include/Modbus_Slave.h)) để Artisan/HMI thật nối vào xem.

- Mã nguồn: [`tools/otl_roast_lab.py`](tools/otl_roast_lab.py)
- Exe: `tools/dist/OTL Roast Lab.exe` · build: `python -m PyInstaller tools/OTLRoastLab.spec`
- Phong cách: customtkinter (Apple), đồ thị matplotlib.

## Chạy từ nguồn

```bash
pip install customtkinter matplotlib pyserial pymodbus
python tools/otl_roast_lab.py
```

## Luồng dùng

1. **Nạp profile…** → chọn CSV Roaster Scope (cùng format SD firmware:
   `Time1 Time2 ET BT Event Air Burner Drum VacFlag VacSP`; mốc TP/DE/FCS/DROP đọc từ
   dòng header `CHARGE:.. TP:.. DRYe:.. FCs:.. DROP:..`).
2. **▶ Charge** → seed BT/ET = mốc CHARGE, bắt đầu vòng kín. Chọn tốc độ x1–x20.
3. Xem đồ thị: BT profile (nét đứt xám) vs BT thực (xanh), Gas/Air. Cột phải: số liệu
   thời gian thực + Gas (FF) vs Gas (calib) để thấy lượng bù.

## Firmware ảo — khớp calibProgram()

- FF: air/gas/drum/vacuum lấy thẳng từ profile theo giây (`lastTimeSD = timeRoast`).
- Chỉ bù gas **sau TP** (`progStep > STP_TP`). Deadband ±1.0°C (`clRangeBt`), siết
  ±0.6°C từ FCS. Ngoài deadband: mỗi 10s tính `calibGas = |ΔBT|/5`, `bù = calibGas×5%`,
  kẹp theo pha (Tp/De/Fcs). Bù **CỘNG lên FF mỗi giây** (cố ý — duy trì lực bù, không tích lũy).
- Tham số calib + model nhiệt chỉnh ở tab **Config**.

## Module BT vật lý (48_RS485_RTU_BT_SIMU)

App **tự dò cổng Silicon Labs CP210x** và **tự nối lúc mở** (cổng bận thì im lặng,
bật tay bằng switch "Nối" trên header). Khi mô phỏng chạy, BT model được lái thẳng
ra module bằng bộ lệnh `1/2/5/9` (+0.1/0.2/0.5/1.0°C) và `q/w/e/r` (giảm) @9600 —
firmware thật đọc BT đó qua RS485, không cần cặp nhiệt. Header hiển thị BT module
đọc từ echo `BT:xx` (độ phân giải 1°C).

Lưu ý: chỉ MỘT app được giữ cổng — đóng BT Serial Tester / Serial Monitor trước.

## Modbus slave (Artisan)

Bật switch **Modbus** trên header, chọn cổng COM + ID + baud. Tool đóng vai slave RTU,
đẩy BT(0)/ET(1) ×10, Air(2)/Gas(3)/Drum(4) ×1, Vacuum(21), START(17) — Artisan PC nối vào
đọc như máy thật. Cần `pymodbus` (đã bundle trong exe).

## Lưu ý

- **Model nhiệt mặc định là rough**: `gas_equilib=35%` chỉ cân bằng ở 210–220°C
  ([analysis-roaster-thermal.md](docs/analysis/analysis-roaster-thermal.md)); ở nhiệt thấp,
  gas profile 10–30% sẽ làm BT tụt trong model → lệch lớn. Đây là chuyện **tune model**,
  không phải lỗi calib. Chỉnh `gas_equilib / gas_sens / heatloss` trong Config cho khớp máy.
- Đây là **mô phỏng thuần** (calib bằng Python) → test NGUYÊN LÝ + chỉnh tham số offline.
  Muốn test đúng binary thật thì dùng chế độ BRIDGE của
  [`tools/sim/virtual_roaster.py`](tools/sim/virtual_roaster.py) (HIL, cần STM32 + 2 RS485).
