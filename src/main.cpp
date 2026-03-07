// Định nghĩa các thư viện cần thiết
#include <Arduino.h>
#include <HardwareSerial.h>
#include <ModbusMaster.h>
#include <Wire.h>
#include <Adafruit_MCP4725.h>
#include <ModbusRTU.h>  // Modbus slave ESP MTlab
#include <SPI.h>
#include <SD.h>
#include "STM32TimerInterrupt.h"
#include <SimpleKalmanFilter.h>

// Kiểm tra nền tảng STM32
#if !( defined(STM32F0) || defined(STM32F1) || defined(STM32F2) || defined(STM32F3)  ||defined(STM32F4) || defined(STM32F7) || \
  defined(STM32L0) || defined(STM32L1) || defined(STM32L4) || defined(STM32H7)  ||defined(STM32G0) || defined(STM32G4) || \
  defined(STM32WB) || defined(STM32MP1) || defined(STM32L5) )
  #error Code này chỉ chạy trên nền tảng STM32! Kiểm tra Tools->Board.
#endif

// Định nghĩa các file header
#include "Define.h"
#include "IOConfig.h"
#include "AnalogConfig.h"
#include "ScaleFeeder.h"
#include "Modbus_Slave.h"
#include "Modbus_Master.h"
#include "Program.h"

// Khai báo các hàm
void debug();

// Hàm setup - khởi tạo các cấu hình
void setup() {
  SerialComputer.begin(9600);  // Khởi tạo Serial
  ConfigIO();                  // Cấu hình IO
  analogConfig();              // Cấu hình analog
  ModbusRS485Config();         // Cấu hình Modbus RS485
  configTimer();               // Cấu hình Timer
  checkError();                // Kiểm tra lỗi
  rwMemHMI();                  // Đọc setup từ HMI
  ModbusSlaveConfig();         // Cấu hình Modbus Slave
  reset_update();              // Reset các giá trị ban đầu
}

// Hàm loop - chạy liên tục
void loop() {
  timeMillis = millis();       // Lấy thời gian hiện tại

  // Xử lý liên tục
  analogIn();                  // Đọc giá trị analog input
  analogOut();                 // Ghi giá trị analog output
  readTempET();                // Đọc nhiệt độ ET
  readTempBT();                // Đọc nhiệt độ BT
  if (chDrumFlag) {            // Nếu có tín hiệu trống
    readWriteDrumINV();        // Đọc ghi biến tần trống
  }

  if(chAirFlag){              // Nếu có tín hiệu gió
    readUnder();              // Đọc cảm biến chênh lệch không khí  
    readWriteAirINV_PID();    // Đọc ghi biến tần gió, hệ PID
  }
  handle_Modbus_Slave();       // Xử lý Modbus Slave
  readScale();                // Đọc cân

  // Xử lý điều kiện
  rwHMICoil();                 // Đọc ghi bit HMI
  rwMemHMI();                  // Đọc ghi biến $M HMI
  rwHMI_1();                   // Đọc ghi biến 4xxxx HMI (40001-40047)
  rwHMI_2();                   // Đọc ghi biến 4xxxx HMI (40060-40085)
  if(chIORelayFlag){
    rwIORelayCoil();          // Đọc ghi coil I/O Relay
  }
  // Chương trình chính
  programScan();               // Quét chương trình

  // Điều khiển IO
  controlIO();                 // Điều khiển IO

  // Tính thời gian thực thi
  calTime = millis() - timeMillis;
  if (enDebug) debug();        // Nếu bật debug, in thông tin
  errorCount = 0;              // Reset bộ đếm lỗi
}

// Hàm debug - hiển thị thông tin trạng thái hệ thống
void debug() {
  SerialComputer.print("Runtime: " + String(calTime) + " ms");

  // Hiển thị trạng thái các timer nếu được kích hoạt
  if (feederTimerEn) SerialComputer.print(" | Feeder: " + String(feederTimer));
  if (chargeTimerEn) SerialComputer.print(" | Charge: " + String(chargeTimer));
  if (dropTimerEn) SerialComputer.print(" | Drop: " + String(dropTimer));
  if (abTimerEn) SerialComputer.print(" | AB: " + String(abTimer));
  if (coolTimerEn) SerialComputer.print(" | Cool: " + String(coolTimer));
  if (escapeTimerEn) SerialComputer.print(" | Escape: " + String(escapeTimer));
  if (destonerTimerEn) SerialComputer.print(" | Destoner: " + String(destonerTimer));
  if (timeRoastEn) SerialComputer.print(" | Roast: " + String(timeRoast));
  if (calSdMillis > 0) SerialComputer.print(" | CalSD: " + String(calSdMillis));
  if (waitDropcloseTiEn > 0) SerialComputer.print(" | WaitDropClose: " + String(waitDropcloseTi));
  if (fillerTiEn > 0) SerialComputer.print(" | Filler: " + String(fillerTi));

  // Hiển thị trạng thái các phần trăm điều khiển
  SerialComputer.print(" | maxPT: " + String(maxPT_R));
  SerialComputer.print(" | minPT: " + String(minPT_R));
  // SerialComputer.print(" | autoFill_Time_R: " + String(autoFill_Time_R));
  // SerialComputer.print(" | autoFill_R: " + String(autoFill_R));
  // SerialComputer.print(" | fillerTiEn: " + String(fillerTiEn));
  // SerialComputer.print(" | fillerTi: " + String(fillerTi));
  // SerialComputer.print(" | difLow_R: " + String(difLow_R));
  // SerialComputer.print(" | vacuumTraction_R: " + String(vacuumTraction_R));

  SerialComputer.println(); // Xuống dòng
}
