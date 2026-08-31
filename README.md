<p align="center">
  <img src="assets/banner/otl-roaster-banner.png" alt="OTL Roaster — Coffee Roaster Auto Control" width="100%">
</p>

<p align="center">
  <a href="https://github.com/TCL-DA/coffee-roaster-auto-control/actions/workflows/release.yml"><img alt="Release" src="https://github.com/TCL-DA/coffee-roaster-auto-control/actions/workflows/release.yml/badge.svg"></a>
  <a href="https://github.com/TCL-DA/coffee-roaster-auto-control/actions/workflows/smoke-stacks.yml"><img alt="Smoke test" src="https://github.com/TCL-DA/coffee-roaster-auto-control/actions/workflows/smoke-stacks.yml/badge.svg"></a>
  <a href="https://github.com/TCL-DA/coffee-roaster-auto-control/actions/workflows/check-asset-sync.yml"><img alt="Asset sync" src="https://github.com/TCL-DA/coffee-roaster-auto-control/actions/workflows/check-asset-sync.yml/badge.svg"></a>
</p>

<p align="center">
  <img alt="MCU" src="https://img.shields.io/badge/MCU-STM32F103RC-FC2424?style=flat-square">
  <img alt="Framework" src="https://img.shields.io/badge/framework-Arduino-37B6FF?style=flat-square">
  <img alt="Build" src="https://img.shields.io/badge/build-PlatformIO-FF7043?style=flat-square">
  <img alt="Flash" src="https://img.shields.io/badge/flash-256%20KB-555?style=flat-square">
  <img alt="RAM" src="https://img.shields.io/badge/RAM-48%20KB-555?style=flat-square">
</p>

<h1 align="center">Coffee Roaster Auto Control</h1>

<p align="center">
  Firmware chạy máy rang cà phê công nghiệp <b>OTL</b><br>
  <sub>Firmware for OTL industrial coffee roasters · <a href="https://www.otlpro.com/">O Tesla Industry Co., Ltd</a></sub>
</p>

---

## Máy này làm gì

Người vận hành đổ hạt vào rồi bấm chạy. Từ đó tới lúc cà phê ra khay, **máy tự lo**:
mồi lửa, nạp liệu theo cân, giữ đường rang bám theo mẻ mẫu, xả khi tới điểm, làm mát
và đốt nốt khói.

<p align="center">
  <img src="assets/banner/otl-roast-curve.png" alt="Đường rang một mẻ và các mốc firmware can thiệp" width="100%">
</p>

<p align="center"><sub>
Đường trắng là nhiệt độ hạt — con số người thợ nhìn. Cam là nhiệt khí thải.
Xanh là tốc độ tăng nhiệt, đã lọc nhiễu. Năm mốc dọc là những chỗ firmware ra quyết định.
</sub></p>

### Một mẻ đi qua những bước nào

| Mốc | Xảy ra chuyện gì | Máy làm gì |
|:--|:--|:--|
| **Làm nóng** | Lồng rang còn nguội | Mồi lửa, đưa nhiệt lên mức đặt rồi giữ ở đó chờ mẻ |
| **NẠP** | Hạt đổ vào, nhiệt tụt mạnh | Cân đúng khối lượng rồi mở cửa nạp |
| **TP** | Nhiệt chạm đáy và quay đầu lên | Mốc để tính toàn bộ phần còn lại của mẻ |
| **DE** | Hạt chuyển màu | Bắt đầu bám sát đường rang mẫu |
| **FCs** | Nổ lần một | Giai đoạn quyết định vị ngon — chỉnh gas sát hơn |
| **XẢ** | Tới điểm dừng | Mở cửa xả, chạy quạt làm mát, đốt nốt khói |

> [!NOTE]
> Máy dùng **một firmware duy nhất cho mọi cỡ**. Máy nào có gì thì khai trong
> [`include/Config.h`](include/Config.h) — không tách nhánh riêng cho từng model.

---

## Ai điều khiển được máy

Ba đường cùng nói chuyện với firmware một lúc. Firmware phân xử, và giữ chốt an toàn
bất kể ai ra lệnh.

```mermaid
flowchart LR
    subgraph OP["Người điều khiển"]
        HMI["Màn hình cảm ứng<br/>tại máy"]
        APP["Ứng dụng PC<br/>OTL Roast Lab"]
        ART["Artisan<br/>ghi nhật ký mẻ"]
    end

    subgraph FW["Firmware STM32F103RC"]
        PROG["Trình tự rang"]
        HEAT["Bộ làm nóng"]
        PIDA["PID gió"]
        ROR["Tốc độ tăng nhiệt<br/>+ lọc nhiễu"]
    end

    subgraph FIELD["Máy"]
        TEMP["Đầu dò nhiệt<br/>hạt và khí thải"]
        BURN["Đầu đốt gas"]
        FAN["Biến tần gió"]
        DRUM["Biến tần lồng"]
        CYL["Xi-lanh nạp,<br/>xả, thoát"]
        SCALE["Cân nạp liệu"]
    end

    SD[("Thẻ SD<br/>hồ sơ + nhật ký")]

    HMI  <--> PROG
    APP  <--> PROG
    ART  <--> PROG

    TEMP --> ROR --> PROG
    PROG --> HEAT --> BURN
    PROG --> PIDA --> FAN
    PROG --> DRUM
    PROG --> CYL
    SCALE --> PROG
    PROG <--> SD

    classDef op fill:#37B6FF,stroke:#0B7FC4,color:#04202F
    classDef fw fill:#1F2430,stroke:#37B6FF,color:#E8ECF3
    classDef fd fill:#2A2020,stroke:#FC2424,color:#F5E9E9
    class HMI,APP,ART op
    class PROG,HEAT,PIDA,ROR fw
    class TEMP,BURN,FAN,DRUM,CYL,SCALE fd
```

---

## Bắt tay vào việc

```bash
pio run -e genericSTM32F103RC                  # build
pio run -e genericSTM32F103RC --target upload  # nạp qua ST-Link
pio run -e genericSTM32F103RC --target size    # xem RAM/Flash còn bao nhiêu
pio device monitor --baud 9600                 # đọc log debug
```

> [!IMPORTANT]
> **RAM mới là thứ chật, không phải Flash.** Bo mạch có 48 KB RAM và riêng các mảng
> ghi dữ liệu mẻ đã ăn gần hết. Thêm mảng nào cũng phải chạy `--target size` xem còn
> dư không — chi tiết trong [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Mã nguồn nằm ở đâu

Mỗi hệ phụ một file header, đọc tên là biết nó lo phần nào.

| File | Lo việc gì |
|:--|:--|
| [`Config.h`](include/Config.h) | **Máy này có gì** — bật tắt từng tuỳ chọn lúc build |
| [`Define.h`](include/Define.h) | Biến toàn cục, chân cắm, địa chỉ truyền thông |
| [`Program.h`](include/Program.h) | Trình tự rang — trái tim của firmware |
| `Preheat*.h` | Làm nóng máy, hai kiểu chọn lúc build |
| [`PID_Airflow.h`](include/PID_Airflow.h) | Giữ áp hút ổn định, có bảng bù và tự chỉnh |
| [`RoR_Control.h`](include/RoR_Control.h) | Tính tốc độ tăng nhiệt, lọc nhiễu cảm biến |
| `Modbus_*.h` | Nói chuyện với màn hình, thiết bị trên bus, và Artisan |
| `PC_Link*.h` | Cầu nối sang ứng dụng máy tính |
| [`ScaleFeeder.h`](include/ScaleFeeder.h) | Đọc cân, nạp liệu tự học |

<details>
<summary><b>Cây thư mục đầy đủ</b></summary>

```
include/     module firmware — mỗi hệ phụ một header
src/         điểm vào chương trình
protocol/    định nghĩa cầu nối, sinh ra cho firmware / Python / JS
tools/       tiện ích chạy trên máy tính — máy rang ảo, tester serial,
             bộ sinh màn hình HMI, chuyển tài liệu sang Markdown
docs/        hồ sơ cấu hình từng máy, tài liệu tra cứu, kế hoạch
html/        trang offline — mô phỏng, hướng dẫn, bản nháp giao diện
assets/      logo, icon, ảnh bitmap cho màn hình
data/        nội dung thẻ SD
```

</details>

---

## Đọc thêm

| Tài liệu | Nội dung |
|:--|:--|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Bản đồ module, ngân sách bộ nhớ, nhịp vòng điều khiển |
| [FEATURES.md](FEATURES.md) | Mô tả từng tính năng |
| [CLAUDE.md](CLAUDE.md) | Quy ước, giới hạn phần cứng, luật an toàn khi sửa code |
| [docs/](docs/) | Hồ sơ cấu hình từng máy, ghi chú cân chỉnh, tài liệu tra cứu |

---

## An toàn

> [!WARNING]
> Firmware này điều khiển **gas, lửa và bộ phận chuyển động**. Hai luật không được phá:
>
> **1. Không gọi SD, Modbus, Serial hay `delay()` trong ISR.**
> `timerPoll_1000ms()` chạy trong ngắt. Đặt cờ rồi xử lý ở `loop()`.
>
> **2. Chạy [release-check](.claude/skills/release-check/) trước khi nạp máy khách.**
> Kiểm cờ debug đã tắt, giới hạn gas hợp lý, các mốc thời gian đúng.

---

<p align="center">
  <sub><b>O Tesla Industry Co., Ltd</b> — máy rang cà phê công nghiệp<br>
  <a href="https://www.otlpro.com/">otlpro.com</a></sub>
</p>
