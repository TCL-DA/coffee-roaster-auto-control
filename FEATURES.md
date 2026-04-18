# Coffee Roaster Auto Control - Tính Năng Chi Tiết

## 📋 Tổng Quan

Hệ thống điều khiển tự động cho máy rang cà phê được xây dựng trên **STM32F103RC** sử dụng **Arduino Framework** và **PlatformIO**. Hệ thống cung cấp điều khiển nhiệt độ, lưu lượng không khí, tốc độ trống, công suất gas và ghi log dữ liệu.

---

## 🔧 Các Tính Năng Chính

### 1. **Đọc Cảm Biến Nhiệt Độ**
- **Nhiệt độ BT (Bean Temperature - Nhiệt độ hạt)**
  - Đọc từ cảm biến thermocouple/RTD qua protocol Modbus
  - Cập nhật thường xuyên trong vòng lặp chính
  - Được lọc qua bộ lọc Kalman để giảm nhiễu
  
- **Nhiệt độ ET (Environment Temperature - Nhiệt độ môi trường)**
  - Đọc từ cảm biến riêng biệt
  - Dùng để điều chỉnh hành vi của máy dựa trên điều kiện môi trường
  - Cũng được lọc Kalman

**Các chỉ tiêu theo dõi:**
- Nhiệt độ lúc Charge (bắt đầu nạp hạt)
- Nhiệt độ TP (Turning Point - điểm gốc)
- Nhiệt độ Yellow (màu vàng)
- Nhiệt độ FCS (First Crack Signal - tín hiệu nứt lần đầu)
- Nhiệt độ Drop (giảm hạt)

---

### 2. **Điều Khiển Áp Suất Chân Không Tự Động (Auto Vacuum PID)**

Hệ thống tự động điều chỉnh lưu lượng không khí (airflow) để duy trì áp suất chân không ổn định trong buồng rang theo setpoint cài đặt.

#### **Cách Hoạt Động (Step Controller)**
- Đo áp suất chân không liên tục (`Diff_Air`, Pa), so sánh với setpoint
- `error > +5 Pa` → tăng airflow 1%
- `error < -5 Pa` → giảm airflow 1%
- `|error| ≤ 5 Pa` → giữ nguyên (deadband ±5 Pa, tránh dao động liên tục)
- Mỗi bước điều chỉnh chờ **2 giây** để quan sát kết quả trước khi bước tiếp
- **Damping**: nếu áp suất đang tự hướng về setpoint → không bước thêm, tránh overshoot

#### **Bộ Nhớ Thông Minh (Feed-Forward Table)**
- Tự học và ghi nhớ đặc tính máy theo thời gian (tối đa 50 cặp `Vacuum Pa → Air%`)
- Khi đổi setpoint → nhảy ngay về vùng Air% đã học, rút ngắn thời gian ổn định
- Ổn định ±5 Pa liên tục 10 giây → tự cập nhật bộ nhớ (moving average)
- Dữ liệu lưu trên thẻ SD (`/pid_ff.txt`), không mất khi tắt máy

#### **Cài Đặt Ban Đầu (Factory Auto-Tune)**
- Bấm 1 nút trên HMI → máy tự động hiệu chỉnh toàn bộ dải airflow 0–100%
- Thời gian: **~5 phút**, hiển thị tiến độ trực tiếp trên màn hình (0–100%)
- Chỉ cần thực hiện 1 lần sau khi lắp đặt, hoặc khi máy thay đổi cấu hình lọc
- Quy trình: hạ airflow về 0% ngay → chờ 15s → quét từng bước 1% → lưu SD tự động

#### **Thông Số Kỹ Thuật**
| Tham số | Giá trị |
|--------|---------|
| Deadband | ±5 Pa |
| Bước điều chỉnh | 1% |
| Cooldown mỗi bước | 2s |
| Tự học sau ổn định | 10s |
| FF Table tối đa | 50 entries |
| HMI kích hoạt tune | 40032 |
| HMI tiến độ tune | 40125 |

---

### 3. **Điều Khiển Gas (Burner Control)**

#### **Slew Rate Limiter (Hạn chế tốc độ thay đổi)**
- **Khi khởi động (boot):**
  - Snap về giá trị `gasPercent` thực tế (tránh ramp từ 0)
  - Tránh tình trạng state bị lỗi thời

- **Khi relay gas tắt (`START_GAS_BTN_R == 0`):**
  - Ngay lập tức snap về `gasPercent`
  - Không để state bị lỗi thời khi bật lại

- **Khi relay gas bật (`START_GAS_BTN_R == 1`):**
  - **Giảm tốc độ:** tối đa 100%/10s (10 ms/%)
  - **Tăng tốc độ:** tối đa 100%/5s (20 ms/%)
  - Được tính toán dựa trên delta thời gian thực tế

#### **Output DAC (Digital-to-Analog Converter)**
- **DAC cho Gas:** địa chỉ I2C `0x61` (MCP4725)
  - Chuyển đổi: `gasPercent` → DAC value (0-4095)
  - Giới hạn bởi `maxGasSet_R` từ HMI: `DAC = (gasPercent × 4095 × maxGasSet_R) / 10000`
  
- **DAC cho Airflow:** địa chỉ I2C `0x60` (MCP4725)
  - Chuyển đổi: `airflowPercent` → DAC value (0-4095)

---

### 4. **Điều Khiển Tốc độ Trống (Drum Speed Control)**
- **Nguồn tín hiệu:** 
  - `SOURCE_AI_VR`: từ potentiometer (analog pin CH2)
  - `SOURCE_AI_PC`: từ HMI/PC qua Modbus
  - `SOURCE_AI_AUTO`: từ profile SD (tự động) khi rang tự động

- **Xử lý tín hiệu:**
  - Đọc ADC thô
  - Làm mịn bằng low-pass filter (exponential averaging)
  - Ánh xạ thành phần trăm 0-100%

- **Output:** Ghi vào tần số biến tần qua Modbus

---

### 5. **Điều Khiển Relay và I/O Số**

#### **8 Kênh Relay Chính:**
1. **CH1 - Gas (Khí gas):** START_GAS_BTN_R
2. **CH2 - Cooling (Làm lạnh):** COOLING_BTN_R
3. **CH3 - Charge (Nạp hạt):** CHARGE_BTN_R
4. **CH4 - Drop (Giảm hạt):** DROP_BTN_R
5. **CH5 - Escape (Xả khí):** ESCAPE_BTN_R
6. **CH6 - Afterburner (Lò phụ):** AB_BTN_R
7. **CH7 - Destoner (Tách đá):** DESTONER_BTN_R
8. **CH8 - Feeder (Nạp liệu):** FEEDER_BTN_R

#### **Đọc trạng thái:**
- **Gas Signal:** `gasSignal = !READ_CH1` (đọc feedback từ relay gas)
- Cơ chế để kiểm tra relay gas có đóng hay không

---

### 6. **Ghi Nhật Ký Dữ Liệu Rang (Roast Logging)**

#### **Dữ Liệu lưu trữ:**
- **Hồ sơ rang (Roast Profile):**
  - `BT_CHARGE_SAVE`: Nhiệt độ BT lúc Charge
  - `BT_TP_SAVE`: Nhiệt độ BT lúc Turning Point
  - `BT_YELLOW_SAVE`: Nhiệt độ BT lúc Yellow
  - `BT_FCS_SAVE`: Nhiệt độ BT lúc First Crack
  - `BT_DROP_SAVE`: Nhiệt độ BT lúc Drop

- **Thời gian các giai đoạn:**
  - `TIME_TP_SAVE, TIME_TP_MIN_SAVE, TIME_TP_SEC_SAVE`: Thời gian TP
  - `TIME_YELLOW_SAVE, TIME_YELLOW_MIN_SAVE, TIME_YELLOW_SEC_SAVE`: Thời gian Yellow
  - `TIME_FCS_SAVE, TIME_FCS_MIN_SAVE, TIME_FCS_SEC_SAVE`: Thời gian FCS
  - `TIME_DROP_SAVE, TIME_DROP_MIN_SAVE, TIME_DROP_SEC_SAVE`: Thời gian Drop
  - `TIME_DEV_SAVE, TIME_DEV_MIN_SAVE, TIME_DEV_SEC_SAVE`: Thời gian DEV

- **Thống kê:**
  - `PER_DEV_SAVE`: Phần trăm độ lệch
  - Dự đoán thời gian Yellow/FCS

#### **Lưu trữ:**
- Ghi vào thẻ SD
- Tệp log: dữ liệu rang lịch sử
- Tải cấu hình PID từ SD khi khởi động: `pidLoadFromSD()`

---

### 7. **Điều Khiển Cân (Scale/Feeder Weight)**
- **Đọc trọng lượng:** từ cảm biến cân qua Modbus
- **Biến tính toán:**
  - `difNetW`: Hiệu số giữa tổng cân và target
  - `dif`: Căn chỉnh độ lệch khi cân
  
- **Tính năng Feeder (Nạp liệu):**
  - `feederTimer`: Đếm thời gian hoạt động
  - `feederTimerEn`: Bật/tắt timer feeder
  - `fillerTi`: Thời gian tự động tắt fill
  - `cleanFeederTi`: Thời gian hút sạch cà phê
  - `delCyFeederTi`: Xóa cycle feeder

---

### 8. **Quản lý Program Rang (Program Management)**

#### **Các giai đoạn rang:**
- **STP_DATA**: Chuẩn bị dữ liệu
- **STP_COOL_DOWN**: Làm lạnh
- **STP_GAS**: Khởi động gas
- **STP_CHECK**: Kiểm tra
- **STP_CHARGE**: Nạp hạt
- **STP_TP**: Turning Point
- **STP_YELLOW**: Giai đoạn vàng
- **STP_FCS**: First Crack Signal
- **STP_DEV**: Phát triển
- **STP_DROP**: Giảm hạt

#### **Auto-Loader (Nạp tự động):**
- `aLoaderStep`: Bước trong quá trình nạp tự động
- Trạng thái:
  - `STP_NONE_LOADER`: Không nạp
  - `STP_ON_LOADER`: Đang nạp
  - `STP_WAIT_LOADER`: Chờ
  - `STP_FAIL_LOADER`: Lỗi
  - `STP_OK_LOADER`: Thành công

#### **Cooling & Afterburner:**
- `coolStep`: Giai đoạn làm lạnh
- `abStep`: Giai đoạn lò phụ
- `coolTimerEn, coolTimer`: Timer làm lạnh
- `abTimerEn, abTimer`: Timer lò phụ

---

### 9. **Giao Tiếp Modbus**

#### **Modbus Master (Đọc từ cảm biến):**
- **Các node:**
  - `nodeBT`: Đọc BT từ cảm biến
  - `nodeET`: Đọc ET từ cảm biến
  - `nodeHMI`: Giao tiếp với HMI
  - `nodeAir`: Điều khiển airflow
  - `nodeDrum`: Điều khiển trống
  - `nodeIORelay`: Điều khiển relay I/O

#### **Modbus Slave (Nhận lệnh từ HMI):**
- Cấu hình bằng `ModbusSlaveConfig()`
- Xử lý trong `handle_Modbus_Slave()`
- Hỗ trợ:
  - Đọc/ghi coil (bit)
  - Đọc/ghi register (16-bit)

#### **Cấu hình RS485:**
- `ModbusRS485Config()`: Khởi tạo UART và tốc độ
- Sử dụng UART4 (hoặc UART2 tùy theo version)

---

### 10. **Quản lý Thời Gian và Timer**

#### **Timer chính:**
- `timeRoast`: Thời gian rang (phút, giây)
- `chargeTimer`: Timer charge
- `dropTimer`: Timer drop
- `coolTimer`: Timer cooling
- `escapeTimer`: Timer escape
- `abTimer`: Timer afterburner
- `destonerTimer`: Timer destoner
- `feederTimer`: Timer feeder
- `buzzerTimer`: Timer buzzer
- `waitDropcloseTi`: Timer chờ drop tắt
- `fillerTi`: Timer tự động tắt fill

#### **Timer cập nhật tần số:**
- `drumHzTimer`: Cập nhật Drum Hz
- `airHzTimer`: Cập nhật Airflow Hz
- `gasTimer`: Cập nhật Gas

#### **Timer khác:**
- `updateNetWTi`: Cập nhật netWeight
- `cleanFeederTi`: Hút sạch feeder
- `delCyFeederTi`: Xóa cycle feeder

---

### 11. **Xử Lý Lỗi (Error Handling)**

#### **Biến lỗi:**
- `errorCount`: Đếm số lỗi
- Reset về 0 mỗi loop (xóa lỗi cũ)

#### **Kiểm tra lỗi:**
- `checkError()`: Kiểm tra lỗi khi khởi động
- Có thể:
  - Kiểm tra kết nối cảm biến
  - Kiểm tra SD card
  - Kiểm tra Modbus
  - Kiểm tra DAC

---

### 12. **Cấu hình Analog Input/Output**

#### **Analog Input (ADC):**
- `CH1_ANALOG`: Airflow từ potentiometer
- `CH2_ANALOG`: Drum speed từ potentiometer
- `CH3_ANALOG`: Gas control từ potentiometer

#### **Ánh xạ:**
- `CH1AInMax, CH2AInMax, CH3AInMax`: Giá trị ADC tối đa
- Công thức: `value% = (ADC_raw / ADCmax) × 100`

#### **Low-pass Filter:**
- Hệ số mịn: `alpha`
- Công thức: `smoothed = alpha × raw + (1 - alpha) × smoothed_old`

---

### 13. **Ghi nhật ký và Debug**

#### **Debug output:**
- `enDebug`: Bật/tắt chế độ debug
- `SerialComputer`: Kênh serial với PC
- Thông tin debug:
  - Loop time: `calTime`
  - Các timer đang chạy
  - Thời gian xử lý SD

#### **Hiển thị:**
```
Loop: 45ms | Feeder: 120 | Charge: 300 | Drop: 1500 | Roast: 480 | CalSD: 150
```

---

### 14. **Cấu hình Bộ Nhớ HMI**

#### **Mảng bộ nhớ:**
- `iMemHMI[60]`: Bộ nhớ 16-bit từ HMI (register I)
- `iMemHMI_CP[60]`: Bản sao cấu hình cũ

- `dAddress[200]`: Địa chỉ 40xxx (register data)
- `dAddress_CP[200]`: Bản sao cũ

- `cAddress[200]`: Coil (bit)
- `cAddress_CP[200]`: Bản sao cũ

#### **Hàm quản lý:**
- `rwMemHMI()`: Đọc/ghi bộ nhớ HMI
- `rwHMI_1()`: Đọc/ghi HMI page 1
- `rwHMI_2()`: Đọc/ghi HMI page 2
- `rwHMICoil()`: Đọc/ghi coil

---

### 15. **Điều khiển Biến Tần (Inverter)**

#### **Drum Inverter:**
- `readWriteDrumINV()`: Đọc/ghi tốc độ trống
- Chỉ hoạt động khi `chDrumFlag == true`
- Gửi tần số điều khiển qua Modbus

#### **Air Inverter (PID điều khiển):**
- `readWriteAirINV_PID()`: Đọc/ghi lưu lượng không khí với PID
- Chỉ hoạt động khi `chAirFlag == true`
- Gửi tần số PID-controlled qua Modbus

#### **Read Underflow (Đọc dữ liệu cuộn dưới):**
- `readUnder()`: Đọc trạng thái cuộn dưới

---

### 16. **Chế độ Điều khiển Airflow**

#### **Các nguồn điều khiển:**
- `SOURCE_AI_VR`: Potentiometer tay quay (Voltage input)
- `SOURCE_AI_PC`: Điều khiển từ PC/HMI
- `SOURCE_AI_AUTO`: Từ SD profile (khi rang tự động)

#### **Flag điều khiển:**
- `vacuumSetFlag_R`: Kích hoạt chế độ PID setpoint
- `vacuumSetpoint_R`: Giá trị setpoint (Pa)
- `autoVacPIDEn`: Bật PID áp suất tự động
- `autoVacSP`: Setpoint từ profile SD

---

### 17. **Tính toán Thống kê Rang**

#### **Biến dự đoán:**
- `timeYelTemp`: Dự đoán thời gian Yellow
- `timeFcsTemp`: Dự đoán thời gian FCS
- `timeDevTemp`: Tính toán Development time
- `deviTemp`: Độ lệch nhiệt độ

#### **Calibration Gas Auto:**
- `calibGasProgramEn`: Bật/tắt calibration gas program
- `calibGas`: Hệ số hiệu chỉnh gas
- `deviTemp`: Độ lệch nhiệt độ
- `numIncGas`: Giá trị tăng gas
- `clRangeBt`: Clearance để auto gas

---

### 18. **Nhiệm vụ Nền (Background Tasks)**

#### **PID Self-Tune Task:**
- `pidSelfTuneTask()`: Xử lý self-tune airflow ngoài ISR (Interrupt Service Routine)
- Tránh timeout nếu xử lý trong interrupt

#### **PID SD Task:**
- `pidSDTask()`: Lưu FF table vào SD (non-blocking)
- Chỉ ghi khi `ffDirty == true`
- Sử dụng command queue: `sdPendingCmd`

#### **Program Scan:**
- `programScan()`: Quét trạng thái program
- Cập nhật các timer
- Kiểm tra điều kiện chuyển giai đoạn

---

### 19. **Khởi tạo Hệ thống (Setup)**

#### **Thứ tự khởi tạo:**
1. `SerialComputer.begin(9600)`: Khởi tạo serial debug
2. `ConfigIO()`: Cấu hình I/O pins
3. `analogConfig()`: Cấu hình DAC
4. `ModbusRS485Config()`: Cấu hình Modbus RS485
5. `configTimer()`: Cấu hình timer interrupt
6. `checkError()`: Kiểm tra lỗi khởi động
7. `rwMemHMI()`: Đọc bộ nhớ HMI
8. `ModbusSlaveConfig()`: Cấu hình Modbus Slave
9. `pidLoadFromSD()`: Tải FF table từ SD
10. `reset_update()`: Reset và cập nhật trạng thái

---

### 20. **Vòng Lặp Chính (Main Loop)**

#### **Thứ tự xử lý:**
1. Lấy thời gian hiện tại: `timeMillis = millis()`
2. Đọc dữ liệu analog
3. Ghi output analog
4. Đọc nhiệt độ BT, ET
5. Điều khiển tốc độ trống (nếu enabled)
6. Điều khiển lưu lượng không khí (nếu enabled)
7. Xử lý Modbus Slave
8. Đọc cân
9. Đọc/ghi coil HMI
10. Đọc/ghi bộ nhớ HMI
11. Đọc/ghi HMI page 1, 2
12. Điều khiển relay I/O (nếu enabled)
13. Quét program
14. Điều khiển I/O
15. Tính thời gian xử lý: `calTime = millis() - timeMillis`
16. Debug output (nếu enabled)
17. Reset errorCount
18. Xử lý self-tune ngoài ISR
19. Xử lý lưu SD

---

## 📊 Sơ Đồ Luồng Dữ Liệu

```
Cảm biến (BT, ET, Pressure, Weight)
        ↓
    Đọc Modbus
        ↓
    Lọc Kalman
        ↓
    PID Airflow Control / Step Controller
        ↓
    FF Table Lookup / Learn
        ↓
    Slew Rate Limiter (Gas)
        ↓
    DAC Output (Gas, Airflow)
        ↓
    Relay / Inverter Control
        ↓
    Ghi SD Log
        ↓
    Gửi HMI
```

---

## 🔌 Các Thư Viện Sử Dụng

| Thư viện | Mục đích |
|---------|---------|
| `Arduino.h` | Framework chính |
| `HardwareSerial` | UART communication |
| `ModbusMaster` | Master Modbus RTU |
| `Wire.h` | I2C communication |
| `Adafruit_MCP4725` | DAC control |
| `ModbusRTU` | Modbus slave (ESP) |
| `SPI.h` | SD card SPI |
| `SD.h` | SD card reading/writing |
| `STM32TimerInterrupt` | Timer interrupt |
| `SimpleKalmanFilter` | Sensor filtering |

---

## ⚙️ Cấu hình Phần Cứng

| Chức năng | Chân | Ghi chú |
|----------|-----|--------|
| Serial1 (HMI) | USART1 | 9600 baud |
| Serial2 (Modbus) | UART4 | 19200 baud |
| Serial4 (Debug) | UART4 | 9600 baud |
| I2C SDA | PB7 | DAC control |
| I2C SCL | PB6 | DAC control |
| SPI (SD) | PA5-7, PC4 | SD card |
| ADC CH1 | PA0 | Airflow potentiometer |
| ADC CH2 | PA1 | Drum potentiometer |
| ADC CH3 | PA2 | Gas potentiometer |
| Relay 1-8 | PC0-7 | Output pins |

---

## 📝 Ghi Chú Quan Trọng

1. **Safety First**: Gas control luôn có slew rate limiter để tránh thay đổi đột ngột
2. **Learning System**: FF table tự học từ kinh nghiệm để cải thiện điều khiển
3. **Non-blocking SD**: Sử dụng task queue để tránh timeout khi lưu SD
4. **Modular Design**: Mỗi chức năng tách biệt trong file header riêng
5. **Error Counting**: Mỗi loop reset errorCount để theo dõi lỗi thực thời

---

## 🚀 Các Tính Năng Tương Lai

- Advanced PID tuning algorithm
- ROR (Rate of Rise) control
- Adaptive burner control based on bean temperature curve
- AI-assisted profile optimization
- Automatic roast profile recommendation

---

**Phiên bản**: v1.1.0 - Gas slew rate, Auto airflow PID, SD log fixes  
**Tác giả**: TCL-DA  
**Cập nhật lần cuối**: 2025-02
